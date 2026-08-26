#!/usr/bin/env python3

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import re
import shutil
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

EXPERIMENT_ID = "CODEX-EXP-009-P0"
PASS_STATUS = "DATA_READY_OPTIONS_TRADE_FLOW_SANDBOX"
FAIL_STATUS = "FAIL_OPTIONS_TRADE_FLOW_DATA_NOT_READY"
TARDIS_VERSION = "4.2.1"
DATES = (
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)
CURRENCIES = ("BTC", "ETH")
WINDOW_MINUTES = (1, 5, 15, 30)
GRID_START_MINUTE = 30
GRID_END_MINUTE = 23 * 60 + 49
GRID_COUNT = 1400
MIN_SUPPORT = 1120
MIN_RUN = 120
REQUIRED_COLUMNS = {
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "id",
    "side",
    "price",
    "amount",
}
ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs" / "CODEX_EXP009_P0_PREREGISTRATION.md"
OUT_ROOT = ROOT / "evidence" / "codex" / "exp009_p0_options_trade_flow"
RAW_DIR = OUT_ROOT / "raw"
MANIFEST_PATH = OUT_ROOT / "OPTIONS_TRADES_ACQUISITION_MANIFEST.json"
AUDIT_PATH = OUT_ROOT / "OPTIONS_TRADE_FLOW_P0_AUDIT.json"
BASE_URL = "https://datasets.tardis.dev/v1/deribit/trades"
SYMBOL_RE = re.compile(
    r"^(BTC|ETH)[-_](\d{1,2}[A-Z]{3}\d{2})[-_]([0-9]+(?:\.[0-9]+)?)[-_]([CP])$",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_write(path: Path, obj) -> None:
    raw = (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    path.write_bytes(raw)


def day_start_us(day: str) -> int:
    dt = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1_000_000)


def grid_times(day: str):
    start = day_start_us(day)
    return [
        start + m * 60 * 1_000_000
        for m in range(GRID_START_MINUTE, GRID_END_MINUTE + 1)
    ]


def parse_symbol(symbol: str):
    m = SYMBOL_RE.match((symbol or "").strip().upper())
    if not m:
        return None
    currency, expiry_text, strike_text, cp = m.groups()
    expiry = datetime.strptime(expiry_text, "%d%b%y").replace(tzinfo=timezone.utc)
    strike = float(strike_text)
    if not math.isfinite(strike) or strike <= 0:
        return None
    return {
        "currency": currency,
        "expiration": int(expiry.timestamp() * 1_000_000),
        "strike": strike,
        "type": "call" if cp.upper() == "C" else "put",
    }


def classify_currency(symbol: str):
    x = parse_symbol(symbol)
    return None if x is None else x["currency"]


def required_int(value, field):
    if value is None or value == "":
        raise ValueError(f"missing {field}")
    return int(value)


def positive_float(value, field):
    if value is None or value == "":
        raise ValueError(f"missing {field}")
    x = float(value)
    if not math.isfinite(x) or x <= 0:
        raise ValueError(f"invalid positive {field}")
    return x


def parse_trade(raw):
    symbol_meta = parse_symbol(raw.get("symbol", ""))
    if symbol_meta is None:
        symbol = (raw.get("symbol") or "").upper()
        if symbol.startswith("BTC-") or symbol.startswith("BTC_") or symbol.startswith("ETH-") or symbol.startswith("ETH_"):
            raise ValueError("malformed BTC/ETH option symbol")
        return None
    side = (raw.get("side") or "").strip().lower()
    if side not in {"buy", "sell"}:
        raise ValueError("invalid side")
    trade_id = (raw.get("id") or "").strip()
    if not trade_id:
        raise ValueError("missing trade id")
    return {
        **symbol_meta,
        "symbol": raw["symbol"],
        "timestamp": required_int(raw.get("timestamp"), "timestamp"),
        "local_timestamp": required_int(raw.get("local_timestamp"), "local_timestamp"),
        "id": trade_id,
        "side": side,
        "price": positive_float(raw.get("price"), "price"),
        "amount": positive_float(raw.get("amount"), "amount"),
    }


def source_url(day):
    y, m, d = day.split("-")
    return f"{BASE_URL}/{y}/{m}/{d}/OPTIONS.csv.gz"


def acquire_one(day: str, dest: Path):
    try:
        import tardis_dev
        from tardis_dev import download_datasets
    except Exception as exc:
        raise RuntimeError(f"tardis-dev import failure: {exc}") from exc
    actual = getattr(tardis_dev, "__version__", None)
    if actual != TARDIS_VERSION:
        raise RuntimeError(
            f"tardis-dev version must be {TARDIS_VERSION}, got {actual}"
        )
    if dest.exists():
        raise RuntimeError(f"refusing existing raw artifact: {dest}")
    staging = RAW_DIR / ("staging_" + day)
    if staging.exists():
        raise RuntimeError(f"refusing existing staging directory: {staging}")
    staging.mkdir()
    try:
        next_day = (
            datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")
        download_datasets(
            exchange="deribit",
            data_types=["trades"],
            symbols=["OPTIONS"],
            from_date=day,
            to_date=next_day,
            api_key="",
            download_dir=str(staging),
            concurrency=1,
            skip_if_exists=False,
        )
        files = list(staging.glob("*.csv.gz"))
        if len(files) != 1:
            raise RuntimeError(
                f"expected exactly one downloaded gzip, found {len(files)}"
            )
        os.replace(files[0], dest)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def flow_support(trades, t_us):
    out = {}
    for w in WINDOW_MINUTES:
        lo = t_us - w * 60 * 1_000_000
        xs = [r for r in trades if lo <= r["local_timestamp"] < t_us]
        buy = [r for r in xs if r["side"] == "buy"]
        sell = [r for r in xs if r["side"] == "sell"]
        call = [r for r in xs if r["type"] == "call"]
        put = [r for r in xs if r["type"] == "put"]
        buy_amt = sum(r["amount"] for r in buy)
        sell_amt = sum(r["amount"] for r in sell)
        call_amt = sum(r["amount"] for r in call)
        put_amt = sum(r["amount"] for r in put)
        total_amt = buy_amt + sell_amt
        total_count = len(xs)
        cp_amt = call_amt + put_amt
        out[w] = {
            "trade_count": total_count,
            "buy_amount": buy_amt,
            "sell_amount": sell_amt,
            "amount_imbalance_defined": total_amt > 0,
            "count_imbalance_defined": total_count > 0,
            "call_put_imbalance_defined": cp_amt > 0,
            "complete": (
                total_count > 0
                and total_amt > 0
                and cp_amt > 0
            ),
        }
    return out


def audit_day(path: Path, day: str):
    start = day_start_us(day)
    end = start + 86_400_000_000
    grids = grid_times(day)
    by_currency = {c: deque() for c in CURRENCIES}
    stats = {
        c: {
            "trade_count": 0,
            "buy_count": 0,
            "sell_count": 0,
            "call_count": 0,
            "put_count": 0,
            "total_positive_amount": 0.0,
            "w1": 0,
            "w5": 0,
            "w15": 0,
            "w30": 0,
            "all": 0,
            "run": 0,
            "longest": 0,
            "first": None,
            "last": None,
        }
        for c in CURRENCIES
    }
    row_count = 0
    malformed = 0
    outside = 0
    last_local = None
    monotonic = True
    min_local = None
    max_local = None
    duplicate_exact = 0
    duplicate_conflict = 0
    seen_ids = {}
    grid_i = 0

    def evaluate_until(limit_us, inclusive=False):
        nonlocal grid_i
        while grid_i < len(grids) and (
            grids[grid_i] <= limit_us if inclusive else grids[grid_i] < limit_us
        ):
            t = grids[grid_i]
            cutoff = t - 30 * 60 * 1_000_000
            for c in CURRENCIES:
                q = by_currency[c]
                while q and q[0]["local_timestamp"] < cutoff:
                    q.popleft()
                support = flow_support(list(q), t)
                st = stats[c]
                st["w1"] += int(support[1]["complete"])
                st["w5"] += int(support[5]["complete"])
                st["w15"] += int(support[15]["complete"])
                st["w30"] += int(support[30]["complete"])
                complete = all(support[w]["complete"] for w in WINDOW_MINUTES)
                st["all"] += int(complete)
                if complete:
                    st["run"] += 1
                    st["longest"] = max(st["longest"], st["run"])
                    iso = datetime.fromtimestamp(
                        t / 1_000_000, tz=timezone.utc
                    ).isoformat()
                    st["first"] = st["first"] or iso
                    st["last"] = iso
                else:
                    st["run"] = 0
            grid_i += 1

    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        if not REQUIRED_COLUMNS.issubset(columns):
            return {
                "date": day,
                "schema_ok": False,
                "missing_columns": sorted(REQUIRED_COLUMNS - columns),
                "pass": False,
            }
        for raw in reader:
            row_count += 1
            try:
                local = int(raw.get("local_timestamp", ""))
            except Exception:
                malformed += 1
                continue
            if last_local is not None and local < last_local:
                monotonic = False
            evaluate_until(local, inclusive=True)
            last_local = local
            min_local = local if min_local is None else min(min_local, local)
            max_local = local if max_local is None else max(max_local, local)
            if not (start <= local < end):
                outside += 1
                continue
            try:
                parsed = parse_trade(raw)
            except Exception:
                symbol = (raw.get("symbol") or "").upper()
                if symbol.startswith(("BTC-", "BTC_", "ETH-", "ETH_")):
                    malformed += 1
                continue
            if parsed is None:
                continue
            econ = (
                parsed["symbol"], parsed["timestamp"], parsed["local_timestamp"],
                parsed["side"], parsed["price"], parsed["amount"],
                parsed["type"], parsed["expiration"], parsed["strike"],
            )
            tid = parsed["id"]
            if tid in seen_ids:
                if seen_ids[tid] == econ:
                    duplicate_exact += 1
                    continue
                duplicate_conflict += 1
                continue
            seen_ids[tid] = econ
            c = parsed["currency"]
            by_currency[c].append(parsed)
            st = stats[c]
            st["trade_count"] += 1
            st[parsed["side"] + "_count"] += 1
            st[parsed["type"] + "_count"] += 1
            st["total_positive_amount"] += parsed["amount"]

    evaluate_until(10**30, inclusive=True)
    currency = {}
    for c in CURRENCIES:
        st = stats[c]
        currency[c] = {
            "eligible_minutes": GRID_COUNT,
            "minutes_with_1m_trade": st["w1"],
            "minutes_with_5m_trade": st["w5"],
            "minutes_with_15m_trade": st["w15"],
            "minutes_with_30m_trade": st["w30"],
            "complete_all_window_minutes": st["all"],
            "complete_support_fraction": st["all"] / GRID_COUNT,
            "longest_consecutive_complete_minutes": st["longest"],
            "first_complete_minute": st["first"],
            "last_complete_minute": st["last"],
            "trade_count": st["trade_count"],
            "buy_count": st["buy_count"],
            "sell_count": st["sell_count"],
            "call_count": st["call_count"],
            "put_count": st["put_count"],
            "total_positive_amount": st["total_positive_amount"],
            "support_80pct_pass": st["all"] >= MIN_SUPPORT,
            "run_120min_pass": st["longest"] >= MIN_RUN,
        }
    checks = {
        "schema_ok": True,
        "local_timestamp_nondecreasing": monotonic,
        "no_outside_day_rows": outside == 0,
        "no_malformed_btc_eth_rows": malformed == 0,
        "no_conflicting_duplicate_trade_ids": duplicate_conflict == 0,
        "btc_present": currency["BTC"]["trade_count"] > 0,
        "eth_present": currency["ETH"]["trade_count"] > 0,
        "btc_support": (
            currency["BTC"]["support_80pct_pass"]
            and currency["BTC"]["run_120min_pass"]
        ),
        "eth_support": (
            currency["ETH"]["support_80pct_pass"]
            and currency["ETH"]["run_120min_pass"]
        ),
    }
    return {
        "date": day,
        "row_count": row_count,
        "min_local_timestamp": min_local,
        "max_local_timestamp": max_local,
        "malformed_btc_eth_rows": malformed,
        "outside_requested_day_rows": outside,
        "exact_duplicate_trade_ids": duplicate_exact,
        "conflicting_duplicate_trade_ids": duplicate_conflict,
        "currency": currency,
        "checks": checks,
        "pass": all(checks.values()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=str(ROOT))
    ap.add_argument("--no-acquire", action="store_true")
    args = ap.parse_args()
    if Path(args.workspace).resolve() != ROOT.resolve():
        raise RuntimeError("workspace must equal repository root")
    if any(d.startswith("2026-08") for d in DATES):
        raise RuntimeError("SEALED_AUGUST_DATE_IN_FROZEN_LIST")
    if not PREREG.exists():
        raise RuntimeError("missing EXP009 preregistration")
    if OUT_ROOT.exists() and not args.no_acquire:
        raise RuntimeError(f"refusing to overwrite existing output: {OUT_ROOT}")
    if not args.no_acquire:
        OUT_ROOT.mkdir(parents=True)
        RAW_DIR.mkdir()
    elif not RAW_DIR.exists():
        raise RuntimeError("missing frozen raw directory")

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "provider": "Tardis",
        "exchange": "deribit",
        "data_type": "trades",
        "symbol": "OPTIONS",
        "tardis_dev_version": TARDIS_VERSION,
        "preregistration_sha256": sha256_file(PREREG),
        "dates": list(DATES),
        "sealed_august_opened": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
        "entries": [],
    }
    acquisition_ok = True
    acquisition_error = None
    if not args.no_acquire:
        for day in DATES:
            dest = RAW_DIR / f"deribit_trades_{day}_OPTIONS.csv.gz"
            try:
                acquire_one(day, dest)
                manifest["entries"].append({
                    "date": day,
                    "path": str(dest.relative_to(ROOT)),
                    "source_url": source_url(day),
                    "bytes": dest.stat().st_size,
                    "sha256": sha256_file(dest),
                    "acquired_at_utc": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as exc:
                acquisition_ok = False
                acquisition_error = f"{type(exc).__name__}: {exc}"
                break
        manifest["acquisition_ok"] = acquisition_ok
        manifest["acquisition_error"] = acquisition_error
        canonical_write(MANIFEST_PATH, manifest)
    else:
        manifest = json.loads(MANIFEST_PATH.read_text())
        acquisition_ok = bool(manifest.get("acquisition_ok"))
        acquisition_error = manifest.get("acquisition_error")

    audits = []
    hashes_ok = True
    if acquisition_ok:
        by_day = {e["date"]: e for e in manifest["entries"]}
        for day in DATES:
            e = by_day.get(day)
            if not e:
                hashes_ok = False
                break
            path = ROOT / e["path"]
            if not path.exists() or sha256_file(path) != e["sha256"]:
                hashes_ok = False
                break
            audits.append(audit_day(path, day))

    all_pass = (
        acquisition_ok
        and hashes_ok
        and len(audits) == len(DATES)
        and all(x.get("pass") for x in audits)
    )
    status = PASS_STATUS if all_pass else FAIL_STATUS
    audit = {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "acquisition_ok": acquisition_ok,
        "acquisition_error": acquisition_error,
        "raw_hashes_verified": hashes_ok,
        "all_five_days_pass": all_pass,
        "days": audits,
        "sealed_august_opened": False,
        "target_scored": False,
        "future_return_inspected": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
    }
    canonical_write(AUDIT_PATH, audit)
    print(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "acquisition_ok": acquisition_ok,
        "raw_hashes_verified": hashes_ok,
        "all_five_days_pass": all_pass,
        "sealed_august_opened": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
        "manifest": str(MANIFEST_PATH.relative_to(ROOT)),
        "audit": str(AUDIT_PATH.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()

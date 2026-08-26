#!/usr/bin/env python3

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

EXPERIMENT_ID = "CODEX-EXP-008-P0"
PASS_STATUS = "DATA_READY_OPTIONS_SURFACE_SANDBOX"
FAIL_STATUS = "FAIL_OPTIONS_SURFACE_DATA_NOT_READY"
TARDIS_VERSION = "4.2.1"
DATES = (
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)
CURRENCIES = ("BTC", "ETH")
GRID_START_MINUTE = 30
GRID_END_MINUTE = 23 * 60 + 49
GRID_COUNT = 1400
STALE_US = 300 * 1_000_000
MIN_SUPPORT = 1120
MIN_RUN = 120
REQUIRED_COLUMNS = {
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "type",
    "strike_price",
    "expiration",
    "open_interest",
    "mark_iv",
    "underlying_price",
    "delta",
}
ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs" / "CODEX_EXP008_P0_PREREGISTRATION.md"
IMPL_FREEZE = ROOT / "docs" / "CODEX_EXP008_P0_IMPLEMENTATION_FREEZE.md"
OUT_ROOT = ROOT / "evidence" / "codex" / "exp008_p0_options_surface"
RAW_DIR = OUT_ROOT / "raw"
MANIFEST_PATH = OUT_ROOT / "OPTIONS_ACQUISITION_MANIFEST.json"
AUDIT_PATH = OUT_ROOT / "OPTIONS_SURFACE_P0_AUDIT.json"
BASE_URL = "https://datasets.tardis.dev/v1/deribit/options_chain"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_write(path: Path, obj) -> None:
    raw = (json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    path.write_bytes(raw)


def day_start_us(day: str) -> int:
    dt = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1_000_000)


def grid_times(day: str):
    start = day_start_us(day)
    return [start + m * 60 * 1_000_000 for m in range(GRID_START_MINUTE, GRID_END_MINUTE + 1)]


def classify_currency(symbol: str):
    u = symbol.upper()
    for c in CURRENCIES:
        if u.startswith(c + "-") or u.startswith(c + "_"):
            return c
    return None


def parse_required_int(value: str, field: str):
    if value is None or value == "":
        raise ValueError(f"missing required integer {field}")
    return int(value)


def parse_required_float(value: str, field: str):
    if value is None or value == "":
        raise ValueError(f"missing required float {field}")
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"non-finite required float {field}")
    return x


def parse_optional_float(value: str, field: str):
    if value is None or value == "":
        return None
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"non-finite optional float {field}")
    return x


def parse_row(row):
    symbol = row["symbol"]
    currency = classify_currency(symbol)
    if currency is None:
        return None
    typ = (row["type"] or "").strip().lower()
    if typ not in {"call", "put"}:
        raise ValueError("invalid option type")
    return {
        "currency": currency,
        "symbol": symbol,
        "timestamp": parse_required_int(row["timestamp"], "timestamp"),
        "local_timestamp": parse_required_int(row["local_timestamp"], "local_timestamp"),
        "type": typ,
        "strike": parse_required_float(row["strike_price"], "strike_price"),
        "expiration": parse_required_int(row["expiration"], "expiration"),
        "open_interest": parse_optional_float(row["open_interest"], "open_interest"),
        "mark_iv": parse_optional_float(row["mark_iv"], "mark_iv"),
        "underlying_price": parse_optional_float(row["underlying_price"], "underlying_price"),
        "delta": parse_optional_float(row["delta"], "delta"),
    }


def choose_expiry(expiries, t_us, target_days, lo, hi):
    candidates = []
    for exp in expiries:
        dte = (exp - t_us) / 86_400_000_000
        if lo <= dte <= hi:
            candidates.append((abs(dte - target_days), exp))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]))
    return candidates[0][1]


def expiry_surface(rows):
    under = [r["underlying_price"] for r in rows if r["underlying_price"] is not None and r["underlying_price"] > 0]
    if not under:
        return None
    s = median(under)
    strikes = sorted({r["strike"] for r in rows if r["strike"] > 0})
    if not strikes:
        return None
    atm_strike = min(strikes, key=lambda k: (abs(math.log(k / s)), k))
    atm_call = [r for r in rows if r["strike"] == atm_strike and r["type"] == "call"]
    atm_put = [r for r in rows if r["strike"] == atm_strike and r["type"] == "put"]
    if not atm_call or not atm_put:
        return None
    call_iv = atm_call[0]["mark_iv"]
    put_iv = atm_put[0]["mark_iv"]
    if call_iv is None or put_iv is None:
        return None
    atm_iv = 0.5 * (call_iv + put_iv)

    def pick_delta(typ, target):
        cand = []
        for r in rows:
            if r["type"] != typ or r["delta"] is None:
                continue
            dist = abs(r["delta"] - target)
            if dist <= 0.05:
                cand.append((dist, abs(math.log(r["strike"] / s)), r["strike"], r))
        if not cand:
            return None
        cand.sort(key=lambda x: (x[0], x[1], x[2]))
        return cand[0][3]

    c25 = pick_delta("call", 0.25)
    p25 = pick_delta("put", -0.25)
    if c25 is None or p25 is None or c25["mark_iv"] is None or p25["mark_iv"] is None:
        return None

    put_oi = sum(r["open_interest"] for r in rows if r["type"] == "put" and r["open_interest"] is not None and r["open_interest"] > 0)
    call_oi = sum(r["open_interest"] for r in rows if r["type"] == "call" and r["open_interest"] is not None and r["open_interest"] > 0)
    denom = put_oi + call_oi
    if denom <= 0:
        return None
    return {
        "atm": atm_iv,
        "rr": c25["mark_iv"] - p25["mark_iv"],
        "bf": 0.5 * (c25["mark_iv"] + p25["mark_iv"]) - atm_iv,
        "oi": (put_oi - call_oi) / denom,
    }


def surface_at(state, currency, t_us):
    fresh = [r for r in state[currency].values() if t_us - STALE_US <= r["local_timestamp"] < t_us]
    by_exp = {}
    for r in fresh:
        if r["expiration"] > t_us:
            by_exp.setdefault(r["expiration"], []).append(r)
    e7 = choose_expiry(by_exp, t_us, 7, 5, 9)
    e30 = choose_expiry(by_exp, t_us, 30, 25, 35)
    if e7 is None or e30 is None:
        return {"anchors": False, "atm": False, "delta": False, "oi": False, "all": False}
    s7 = expiry_surface(by_exp[e7])
    s30 = expiry_surface(by_exp[e30])
    if s7 is None or s30 is None:
        return {"anchors": True, "atm": False, "delta": False, "oi": False, "all": False}
    vals = [s7["atm"], s7["rr"], s7["bf"], s7["oi"], s30["atm"], s30["rr"], s30["bf"], s30["oi"], s30["atm"] - s7["atm"]]
    ok = all(math.isfinite(float(v)) for v in vals)
    return {"anchors": True, "atm": True, "delta": True, "oi": True, "all": ok}


def audit_day(path: Path, day: str):
    start = day_start_us(day)
    end = start + 86_400_000_000
    grids = grid_times(day)
    state = {"BTC": {}, "ETH": {}}
    counts = {c: {"anchors": 0, "atm": 0, "delta": 0, "oi": 0, "all": 0, "longest_run": 0, "current_run": 0, "first": None, "last": None} for c in CURRENCIES}
    row_count = 0
    btc_rows = 0
    eth_rows = 0
    malformed = 0
    outside = 0
    monotonic = True
    last_local = None
    dup_exact = 0
    dup_conflict = 0
    dup_ts = None
    dup_bucket = {}
    grid_i = 0
    min_local = None
    max_local = None
    schema_ok = True

    def eval_until(limit_us, inclusive=False):
        nonlocal grid_i
        while grid_i < len(grids) and (grids[grid_i] <= limit_us if inclusive else grids[grid_i] < limit_us):
            t = grids[grid_i]
            for c in CURRENCIES:
                s = surface_at(state, c, t)
                for k in ("anchors", "atm", "delta", "oi", "all"):
                    counts[c][k] += int(s[k])
                if s["all"]:
                    counts[c]["current_run"] += 1
                    counts[c]["longest_run"] = max(counts[c]["longest_run"], counts[c]["current_run"])
                    iso = datetime.fromtimestamp(t / 1_000_000, tz=timezone.utc).isoformat()
                    counts[c]["first"] = counts[c]["first"] or iso
                    counts[c]["last"] = iso
                else:
                    counts[c]["current_run"] = 0
            grid_i += 1

    with gzip.open(path, "rt", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        schema_ok = REQUIRED_COLUMNS.issubset(columns)
        if not schema_ok:
            return {"date": day, "schema_ok": False, "missing_columns": sorted(REQUIRED_COLUMNS - columns), "pass": False}
        for raw in reader:
            row_count += 1
            try:
                local = int(raw["local_timestamp"])
            except Exception:
                malformed += 1
                continue
            if last_local is not None and local < last_local:
                monotonic = False
            eval_until(local, inclusive=True)
            last_local = local
            min_local = local if min_local is None else min(min_local, local)
            max_local = local if max_local is None else max(max_local, local)
            if not (start <= local < end):
                outside += 1
                continue
            key_tuple = tuple((k, raw.get(k, "")) for k in sorted(raw.keys()))
            if dup_ts != local:
                dup_ts = local
                dup_bucket = {}
            sym = raw.get("symbol", "")
            if sym in dup_bucket:
                if dup_bucket[sym] == key_tuple:
                    dup_exact += 1
                else:
                    dup_conflict += 1
            else:
                dup_bucket[sym] = key_tuple
            try:
                parsed = parse_row(raw)
            except Exception:
                if classify_currency(sym) is not None:
                    malformed += 1
                continue
            if parsed is None:
                continue
            if parsed["currency"] == "BTC":
                btc_rows += 1
            else:
                eth_rows += 1
            state[parsed["currency"]][parsed["symbol"]] = parsed

    eval_until(10**30, inclusive=True)
    currency = {}
    for c in CURRENCIES:
        all_n = counts[c]["all"]
        currency[c] = {
            "eligible_minutes": GRID_COUNT,
            "both_expiry_anchors_minutes": counts[c]["anchors"],
            "atm_both_anchors_minutes": counts[c]["atm"],
            "delta25_both_anchors_minutes": counts[c]["delta"],
            "oi_both_anchors_minutes": counts[c]["oi"],
            "all_nine_minutes": all_n,
            "all_nine_fraction": all_n / GRID_COUNT,
            "longest_consecutive_all_nine_minutes": counts[c]["longest_run"],
            "first_all_nine_minute": counts[c]["first"],
            "last_all_nine_minute": counts[c]["last"],
            "support_80pct_pass": all_n >= MIN_SUPPORT,
            "run_120min_pass": counts[c]["longest_run"] >= MIN_RUN,
        }
    checks = {
        "schema_ok": schema_ok,
        "local_timestamp_nondecreasing": monotonic,
        "no_outside_day_rows": outside == 0,
        "no_malformed_btc_eth_rows": malformed == 0,
        "no_conflicting_duplicates": dup_conflict == 0,
        "btc_present": btc_rows > 0,
        "eth_present": eth_rows > 0,
        "btc_support": currency["BTC"]["support_80pct_pass"] and currency["BTC"]["run_120min_pass"],
        "eth_support": currency["ETH"]["support_80pct_pass"] and currency["ETH"]["run_120min_pass"],
    }
    return {
        "date": day,
        "row_count": row_count,
        "btc_rows": btc_rows,
        "eth_rows": eth_rows,
        "min_local_timestamp": min_local,
        "max_local_timestamp": max_local,
        "malformed_btc_eth_rows": malformed,
        "outside_requested_day_rows": outside,
        "exact_duplicate_rows": dup_exact,
        "conflicting_duplicate_rows": dup_conflict,
        "currency": currency,
        "checks": checks,
        "pass": all(checks.values()),
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
    if getattr(tardis_dev, "__version__", None) != TARDIS_VERSION:
        raise RuntimeError(f"tardis-dev version must be {TARDIS_VERSION}, got {getattr(tardis_dev, '__version__', None)}")
    if dest.exists():
        raise RuntimeError(f"refusing existing raw artifact: {dest}")
    staging = RAW_DIR / ("staging_" + day)
    if staging.exists():
        raise RuntimeError(f"refusing existing staging directory: {staging}")
    staging.mkdir()
    try:
        next_day = (datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        download_datasets(
            exchange="deribit",
            data_types=["options_chain"],
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
            raise RuntimeError(f"expected exactly one downloaded gzip, found {len(files)}")
        os.replace(files[0], dest)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=str(ROOT))
    ap.add_argument("--no-acquire", action="store_true", help="audit already frozen raw files only")
    args = ap.parse_args()
    workspace = Path(args.workspace).resolve()
    if workspace != ROOT.resolve():
        raise RuntimeError("workspace must equal repository root")
    if any(d.startswith("2026-08") for d in DATES):
        raise RuntimeError("SEALED_AUGUST_DATE_IN_FROZEN_LIST")
    if not PREREG.exists() or not IMPL_FREEZE.exists():
        raise RuntimeError("missing frozen preregistration documents")
    if OUT_ROOT.exists() and not args.no_acquire:
        raise RuntimeError(f"refusing to overwrite existing EXP008-P0 output: {OUT_ROOT}")
    if not args.no_acquire:
        OUT_ROOT.mkdir(parents=True)
        RAW_DIR.mkdir()
    elif not RAW_DIR.exists():
        raise RuntimeError("no frozen raw directory to audit")

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "provider": "Tardis",
        "exchange": "deribit",
        "data_type": "options_chain",
        "symbol": "OPTIONS",
        "tardis_dev_version": TARDIS_VERSION,
        "preregistration_sha256": sha256_file(PREREG),
        "implementation_freeze_sha256": sha256_file(IMPL_FREEZE),
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
            dest = RAW_DIR / f"deribit_options_chain_{day}_OPTIONS.csv.gz"
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
        if not MANIFEST_PATH.exists():
            raise RuntimeError("missing frozen acquisition manifest")
        manifest = json.loads(MANIFEST_PATH.read_text())
        acquisition_ok = bool(manifest.get("acquisition_ok"))
        acquisition_error = manifest.get("acquisition_error")

    audits = []
    raw_hashes_ok = True
    if acquisition_ok:
        by_day = {e["date"]: e for e in manifest["entries"]}
        for day in DATES:
            e = by_day.get(day)
            if not e:
                raw_hashes_ok = False
                break
            path = ROOT / e["path"]
            if not path.exists() or sha256_file(path) != e["sha256"]:
                raw_hashes_ok = False
                break
            audits.append(audit_day(path, day))

    all_days_pass = acquisition_ok and raw_hashes_ok and len(audits) == len(DATES) and all(a.get("pass") for a in audits)
    status = PASS_STATUS if all_days_pass else FAIL_STATUS
    audit = {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "acquisition_ok": acquisition_ok,
        "acquisition_error": acquisition_error,
        "raw_hashes_verified": raw_hashes_ok,
        "days": audits,
        "all_five_days_pass": all_days_pass,
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
        "raw_hashes_verified": raw_hashes_ok,
        "all_five_days_pass": all_days_pass,
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

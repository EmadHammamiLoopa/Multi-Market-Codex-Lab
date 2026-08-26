#!/usr/bin/env python3

import csv
import gzip
import hashlib
import json
import math
import re
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

EXPERIMENT_ID = "CODEX-EXP-010-P0"
PASS_STATUS = "DATA_READY_UNIFIED_OPTIONS_TRADE_FLOW_SANDBOX"
FAIL_STATUS = "FAIL_UNIFIED_OPTIONS_TRADE_FLOW_DATA_NOT_READY"
DATES = (
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)
WINDOW_MINUTES = (1, 5, 15, 30)
GRID_START_MINUTE = 30
GRID_END_MINUTE = 23 * 60 + 49
GRID_COUNT = 1400
MIN_SUPPORT = 1120
MIN_RUN = 120
CURRENCIES = ("BTC", "ETH")
EXPECTED_HASHES = {
    "2026-03-01": "34835b3e3a022fac0e7270b3e1aca643b01e63b3bbffdab50c99c70dea9af6ba",
    "2026-04-01": "175b24f76bceb68b68c8b6caa04682cb4523bc2e5becc39c41fcf92456a1b605",
    "2026-05-01": "287aaf1a1c62b597c1d46f9f408eef9a0d7c1a73d47ef9edb809f9dc53adda78",
    "2026-06-01": "6076038bb1c07ed4e70a5ca696e04213a5e7e9ab9bfa835360764901925fc6a7",
    "2026-07-01": "02be481f94ac9b66dd43c9f185488b0c2af8f0517f7538d30c6dea565f866bc2",
}
ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "docs" / "CODEX_EXP010_P0_PREREGISTRATION.md"
RAW_ROOT = ROOT / "evidence" / "codex" / "exp009_p0_options_trade_flow" / "raw"
OUT_ROOT = ROOT / "evidence" / "codex" / "exp010_p0_unified_options_trade_flow"
AUDIT_PATH = OUT_ROOT / "UNIFIED_OPTIONS_TRADE_FLOW_P0_AUDIT.json"

STANDARD_RE = re.compile(
    r"^(BTC|ETH)[-_](\d{1,2}[A-Z]{3}\d{2})[-_]([0-9]+(?:\.[0-9]+)?)[-_]([CP])$",
    re.I,
)
USDC_RE = re.compile(
    r"^(BTC|ETH)_USDC[-_](\d{1,2}[A-Z]{3}\d{2})[-_]([0-9]+(?:\.[0-9]+)?)[-_]([CP])$",
    re.I,
)
REQUIRED_COLUMNS = {
    "exchange", "symbol", "timestamp", "local_timestamp", "id", "side", "price", "amount"
}


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
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1_000_000)


def grid_times(day: str):
    start = day_start_us(day)
    return [start + m * 60 * 1_000_000 for m in range(GRID_START_MINUTE, GRID_END_MINUTE + 1)]


def parse_symbol(symbol: str):
    u = (symbol or "").strip().upper()
    family = None
    m = USDC_RE.match(u)
    if m:
        family = "usdc_linear"
    else:
        m = STANDARD_RE.match(u)
        if m:
            family = "standard"
    if not m:
        return None
    currency, expiry_text, strike_text, cp = m.groups()
    expiry = datetime.strptime(expiry_text, "%d%b%y").replace(tzinfo=timezone.utc)
    strike = float(strike_text)
    if not math.isfinite(strike) or strike <= 0:
        return None
    return {
        "currency": currency,
        "family": family,
        "expiration": int(expiry.timestamp() * 1_000_000),
        "strike": strike,
        "type": "call" if cp.upper() == "C" else "put",
    }


def parse_trade(raw):
    meta = parse_symbol(raw.get("symbol", ""))
    if meta is None:
        return None
    side = (raw.get("side") or "").strip().lower()
    if side not in {"buy", "sell"}:
        raise ValueError("invalid side")
    tid = (raw.get("id") or "").strip()
    if not tid:
        raise ValueError("missing trade id")
    timestamp = int(raw.get("timestamp", ""))
    local_timestamp = int(raw.get("local_timestamp", ""))
    price = float(raw.get("price", ""))
    amount = float(raw.get("amount", ""))
    if not math.isfinite(price) or price <= 0:
        raise ValueError("invalid price")
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("invalid amount")
    return {
        **meta,
        "symbol": raw["symbol"],
        "timestamp": timestamp,
        "local_timestamp": local_timestamp,
        "id": tid,
        "side": side,
        "price": price,
        "amount": amount,
    }


def audit_day(path: Path, day: str):
    start = day_start_us(day)
    end = start + 86_400_000_000
    grids = grid_times(day)
    queues = {c: deque() for c in CURRENCIES}
    stats = {
        c: {
            "trade_count": 0,
            "standard_trade_count": 0,
            "usdc_linear_trade_count": 0,
            "w1": 0, "w5": 0, "w15": 0, "w30": 0,
            "all": 0, "run": 0, "longest": 0,
        }
        for c in CURRENCIES
    }
    row_count = 0
    eligible_parse_errors = 0
    outside = 0
    monotonic = True
    last_local = None
    seen_ids = {}
    duplicate_exact = 0
    duplicate_conflict = 0
    grid_i = 0

    def evaluate_until(limit_us, inclusive=False):
        nonlocal grid_i
        while grid_i < len(grids) and (grids[grid_i] <= limit_us if inclusive else grids[grid_i] < limit_us):
            t = grids[grid_i]
            cutoff = t - 30 * 60 * 1_000_000
            for c in CURRENCIES:
                q = queues[c]
                while q and q[0]["local_timestamp"] < cutoff:
                    q.popleft()
                present = {}
                for w in WINDOW_MINUTES:
                    lo = t - w * 60 * 1_000_000
                    present[w] = any(lo <= x["local_timestamp"] < t for x in q)
                    stats[c][f"w{w}"] += int(present[w])
                complete = all(present.values())
                stats[c]["all"] += int(complete)
                if complete:
                    stats[c]["run"] += 1
                    stats[c]["longest"] = max(stats[c]["longest"], stats[c]["run"])
                else:
                    stats[c]["run"] = 0
            grid_i += 1

    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        if not REQUIRED_COLUMNS.issubset(columns):
            return {"date": day, "schema_ok": False, "missing_columns": sorted(REQUIRED_COLUMNS - columns), "pass": False}
        for raw in reader:
            row_count += 1
            try:
                local = int(raw.get("local_timestamp", ""))
            except Exception:
                continue
            if last_local is not None and local < last_local:
                monotonic = False
            evaluate_until(local, inclusive=True)
            last_local = local
            if not (start <= local < end):
                outside += 1
                continue
            symbol_meta = parse_symbol(raw.get("symbol", ""))
            if symbol_meta is None:
                continue
            try:
                parsed = parse_trade(raw)
            except Exception:
                eligible_parse_errors += 1
                continue
            econ = (
                parsed["symbol"], parsed["timestamp"], parsed["local_timestamp"],
                parsed["side"], parsed["price"], parsed["amount"], parsed["family"],
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
            queues[c].append(parsed)
            stats[c]["trade_count"] += 1
            stats[c][parsed["family"] + "_trade_count"] += 1

    evaluate_until(10**30, inclusive=True)
    currency = {}
    for c in CURRENCIES:
        st = stats[c]
        currency[c] = {
            "eligible_minutes": GRID_COUNT,
            "trade_count": st["trade_count"],
            "standard_trade_count": st["standard_trade_count"],
            "usdc_linear_trade_count": st["usdc_linear_trade_count"],
            "minutes_with_1m_trade": st["w1"],
            "minutes_with_5m_trade": st["w5"],
            "minutes_with_15m_trade": st["w15"],
            "minutes_with_30m_trade": st["w30"],
            "complete_all_window_minutes": st["all"],
            "complete_support_fraction": st["all"] / GRID_COUNT,
            "longest_consecutive_complete_minutes": st["longest"],
            "support_80pct_pass": st["all"] >= MIN_SUPPORT,
            "run_120min_pass": st["longest"] >= MIN_RUN,
        }
    checks = {
        "schema_ok": True,
        "local_timestamp_nondecreasing": monotonic,
        "no_outside_day_rows": outside == 0,
        "no_eligible_parse_errors": eligible_parse_errors == 0,
        "no_conflicting_duplicate_trade_ids": duplicate_conflict == 0,
        "btc_present": currency["BTC"]["trade_count"] > 0,
        "eth_present": currency["ETH"]["trade_count"] > 0,
        "btc_support": currency["BTC"]["support_80pct_pass"] and currency["BTC"]["run_120min_pass"],
        "eth_support": currency["ETH"]["support_80pct_pass"] and currency["ETH"]["run_120min_pass"],
    }
    return {
        "date": day,
        "row_count": row_count,
        "eligible_parse_errors": eligible_parse_errors,
        "outside_requested_day_rows": outside,
        "exact_duplicate_trade_ids": duplicate_exact,
        "conflicting_duplicate_trade_ids": duplicate_conflict,
        "currency": currency,
        "checks": checks,
        "pass": all(checks.values()),
    }


def main():
    if not PREREG.exists():
        raise RuntimeError("missing EXP010 preregistration")
    if any(d.startswith("2026-08") for d in DATES):
        raise RuntimeError("SEALED_AUGUST_DATE_IN_FROZEN_LIST")
    if OUT_ROOT.exists():
        raise RuntimeError(f"refusing to overwrite existing output: {OUT_ROOT}")
    OUT_ROOT.mkdir(parents=True)

    days = []
    hashes_ok = True
    observed_hashes = {}
    for day in DATES:
        path = RAW_ROOT / f"deribit_trades_{day}_OPTIONS.csv.gz"
        if not path.exists():
            hashes_ok = False
            break
        actual = sha256_file(path)
        observed_hashes[day] = actual
        if actual != EXPECTED_HASHES[day]:
            hashes_ok = False
            break
        days.append(audit_day(path, day))

    all_pass = hashes_ok and len(days) == len(DATES) and all(x.get("pass") for x in days)
    audit = {
        "experiment_id": EXPERIMENT_ID,
        "status": PASS_STATUS if all_pass else FAIL_STATUS,
        "raw_hashes_verified": hashes_ok,
        "observed_hashes": observed_hashes,
        "all_five_days_pass": all_pass,
        "days": days,
        "sealed_august_opened": False,
        "network_accessed": False,
        "target_scored": False,
        "future_return_inspected": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
    }
    canonical_write(AUDIT_PATH, audit)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()

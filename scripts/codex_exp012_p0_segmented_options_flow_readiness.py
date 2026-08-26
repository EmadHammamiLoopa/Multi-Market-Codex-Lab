#!/usr/bin/env python3

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import median

import numpy as np

from multimarket.codex_exp004_headroom import feature_path
from multimarket.codex_research import assert_unsealed_path, sha256_file
from multimarket.v23_phase0dl_score import _load_day

EXPERIMENT_ID = "CODEX-EXP-012-P0"
PASS_STATUS = "DATA_READY_SEGMENTED_BTC_OPTIONS_FLOW_SANDBOX"
FAIL_STATUS = "FAIL_SEGMENTED_BTC_OPTIONS_FLOW_DATA_NOT_READY"
INVALID_STATUS = "INVALID"

DATES = tuple(date(2026, m, 1) for m in range(3, 8))
SYMBOL = "BTCUSDT"
GRID_START_MINUTE = 30
GRID_END_MINUTE = 23 * 60 + 49
GRID_COUNT = 1400
MIN_SUPPORT = 1120
MIN_RUN = 120
ATM_LOG_MONEYNESS = 0.025
NUMERIC_BOUNDARY_ABS_TOL = 1e-12
SHORT_DTE_DAYS = 7.0
MEDIUM_DTE_DAYS = 30.0
WINDOW_MINUTES = (1, 5, 15, 30)
SEGMENTS = (
    "atm_short",
    "atm_medium",
    "otm_call_short",
    "otm_call_medium",
    "otm_put_short",
    "otm_put_medium",
)

RAW_ROOT = Path("evidence/codex/exp009_p0_options_trade_flow/raw")
RAW_SHA256 = {
    date(2026, 3, 1): "34835b3e3a022fac0e7270b3e1aca643b01e63b3bbffdab50c99c70dea9af6ba",
    date(2026, 4, 1): "175b24f76bceb68b68c8b6caa04682cb4523bc2e5becc39c41fcf92456a1b605",
    date(2026, 5, 1): "287aaf1a1c62b597c1d46f9f408eef9a0d7c1a73d47ef9edb809f9dc53adda78",
    date(2026, 6, 1): "6076038bb1c07ed4e70a5ca696e04213a5e7e9ab9bfa835360764901925fc6a7",
    date(2026, 7, 1): "02be481f94ac9b66dd43c9f185488b0c2af8f0517f7538d30c6dea565f866bc2",
}
EXP011_RESULT = Path("evidence/codex/exp011_p1_result/BTC_OPTIONS_TRADE_FLOW_TIMING.json")
EXP011_RESULT_SHA256 = "ba203504d413c59a6ac09cc4f622d7c10554bd62c34b8eb0736202d27c917826"
OUT = Path("evidence/codex/exp012_p0_segmented_options_flow/SEGMENTED_OPTIONS_FLOW_P0_AUDIT.json")

STANDARD_RE = re.compile(
    r"^BTC[-_](\d{1,2}[A-Z]{3}\d{2})[-_]([0-9]+(?:\.[0-9]+)?)[-_]([CP])$",
    re.I,
)
USDC_RE = re.compile(
    r"^BTC_USDC[-_](\d{1,2}[A-Z]{3}\d{2})[-_]([0-9]+(?:\.[0-9]+)?)[-_]([CP])$",
    re.I,
)
REQUIRED_COLUMNS = {
    "exchange", "symbol", "timestamp", "local_timestamp", "id", "side", "price", "amount"
}


@dataclass(frozen=True)
class Trade:
    symbol: str
    family: str
    option_type: str
    expiration_us: int
    strike: float
    local_timestamp: int
    timestamp: int
    trade_id: str
    side: str
    amount: float
    price: float
    underlying_mid: float
    reference_age_ms: float
    moneyness_bucket: str
    maturity_bucket: str
    segment: str | None


def raw_path(day: date) -> Path:
    return RAW_ROOT / f"deribit_trades_{day.isoformat()}_OPTIONS.csv.gz"


def day_start_us(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1_000_000)


def grid_times(day: date) -> list[int]:
    start = day_start_us(day)
    return [start + m * 60_000_000 for m in range(GRID_START_MINUTE, GRID_END_MINUTE + 1)]


def parse_symbol(symbol: str):
    u = (symbol or "").strip().upper()
    family = None
    m = USDC_RE.fullmatch(u)
    if m:
        family = "usdc_linear"
    else:
        m = STANDARD_RE.fullmatch(u)
        if m:
            family = "standard"
    if not m:
        return None
    expiry_text, strike_text, cp = m.groups()
    expiry = datetime.strptime(expiry_text, "%d%b%y").replace(tzinfo=timezone.utc)
    strike = float(strike_text)
    if not math.isfinite(strike) or strike <= 0:
        return None
    return family, int(expiry.timestamp() * 1_000_000), strike, ("call" if cp.upper() == "C" else "put")


def classify_moneyness(option_type: str, strike: float, underlying: float) -> str:
    m = math.log(strike / underlying)
    abs_m = abs(m)
    # The scientific boundary remains exactly 0.025.  The isclose clause
    # only absorbs floating-point reconstruction error when K/S was
    # generated from exp(±0.025); it is not a wider economic bucket.
    at_boundary = math.isclose(
        abs_m,
        ATM_LOG_MONEYNESS,
        rel_tol=0.0,
        abs_tol=NUMERIC_BOUNDARY_ABS_TOL,
    )
    if abs_m < ATM_LOG_MONEYNESS or at_boundary:
        return "atm"
    if option_type == "call" and m > ATM_LOG_MONEYNESS:
        return "otm_call"
    if option_type == "put" and m < -ATM_LOG_MONEYNESS:
        return "otm_put"
    return "other_moneyness"


def classify_maturity(expiration_us: int, local_timestamp: int) -> str:
    dte = (expiration_us - local_timestamp) / 86_400_000_000.0
    if dte <= 0:
        return "invalid_expired"
    if dte <= SHORT_DTE_DAYS:
        return "short"
    if dte <= MEDIUM_DTE_DAYS:
        return "medium"
    return "longer_than_30d"


def segment_name(moneyness: str, maturity: str) -> str | None:
    if moneyness == "atm" and maturity in {"short", "medium"}:
        return f"atm_{maturity}"
    if moneyness == "otm_call" and maturity in {"short", "medium"}:
        return f"otm_call_{maturity}"
    if moneyness == "otm_put" and maturity in {"short", "medium"}:
        return f"otm_put_{maturity}"
    return None


def percentile(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    return float(np.quantile(np.asarray(xs, dtype=np.float64), q))


def causal_reference(phase, u: int):
    idx = int(np.searchsorted(phase.ts, u, side="left")) - 1
    if idx < 0:
        return None
    if not bool(phase.book_valid[idx]):
        return None
    mid = float(phase.mid[idx])
    if not math.isfinite(mid) or mid <= 0:
        return None
    ts = int(phase.ts[idx])
    if ts >= u:
        raise RuntimeError("equal/future Phase-L reference")
    return mid, (u - ts) / 1000.0


def load_and_classify(workspace: Path, feature_dir: Path, day: date):
    rp = workspace / raw_path(day)
    if sha256_file(rp) != RAW_SHA256[day]:
        raise RuntimeError(f"raw hash mismatch {day}")
    phase_path = feature_path(feature_dir, SYMBOL, day)
    phase = _load_day(phase_path, day)

    start = day_start_us(day)
    end = start + 86_400_000_000
    rows = 0
    parse_errors = 0
    outside = 0
    duplicate_exact = 0
    duplicate_conflict = 0
    missing_reference = 0
    valid_vanilla = 0
    invalid_expired = 0
    last_local = None
    monotonic = True
    seen: dict[str, tuple] = {}
    trades: list[Trade] = []
    family = Counter()
    money = Counter()
    maturity = Counter()
    segments = Counter()
    reference_ages: list[float] = []

    with gzip.open(rp, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = set(reader.fieldnames or [])
        if not REQUIRED_COLUMNS.issubset(cols):
            raise RuntimeError(f"schema mismatch {day}")
        for raw in reader:
            rows += 1
            try:
                local = int(raw.get("local_timestamp", ""))
            except Exception:
                parse_errors += 1
                continue
            if last_local is not None and local < last_local:
                monotonic = False
            last_local = local
            if not (start <= local < end):
                outside += 1
                continue
            meta = parse_symbol(raw.get("symbol", ""))
            if meta is None:
                continue
            valid_vanilla += 1
            try:
                fam, exp_us, strike, typ = meta
                side = (raw.get("side") or "").strip().lower()
                if side not in {"buy", "sell"}:
                    raise ValueError("bad side")
                tid = (raw.get("id") or "").strip()
                if not tid:
                    raise ValueError("missing id")
                ts = int(raw.get("timestamp", ""))
                amount = float(raw.get("amount", ""))
                price = float(raw.get("price", ""))
                if not math.isfinite(amount) or amount <= 0:
                    raise ValueError("bad amount")
                if not math.isfinite(price) or price <= 0:
                    raise ValueError("bad price")
            except Exception:
                parse_errors += 1
                continue
            econ = (raw["symbol"], ts, local, side, amount, price)
            if tid in seen:
                if seen[tid] == econ:
                    duplicate_exact += 1
                    continue
                duplicate_conflict += 1
                continue
            seen[tid] = econ

            ref = causal_reference(phase, local)
            if ref is None:
                missing_reference += 1
                continue
            underlying, age_ms = ref
            mb = classify_moneyness(typ, strike, underlying)
            db = classify_maturity(exp_us, local)
            if db == "invalid_expired":
                invalid_expired += 1
                continue
            seg = segment_name(mb, db)
            tr = Trade(
                symbol=str(raw["symbol"]), family=fam, option_type=typ,
                expiration_us=exp_us, strike=strike, local_timestamp=local,
                timestamp=ts, trade_id=tid, side=side, amount=amount, price=price,
                underlying_mid=underlying, reference_age_ms=age_ms,
                moneyness_bucket=mb, maturity_bucket=db, segment=seg,
            )
            trades.append(tr)
            family[fam] += 1
            money[mb] += 1
            maturity[db] += 1
            if seg:
                segments[seg] += 1
            reference_ages.append(age_ms)

    timestamps = [x.local_timestamp for x in trades]
    run = longest = 0
    n_support = 0
    for t in grid_times(day):
        hi = bisect.bisect_left(timestamps, t)
        lo = bisect.bisect_left(timestamps, t - 60_000_000, 0, hi)
        ok = hi > lo
        if ok:
            n_support += 1
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    integrity_checks = {
        "raw_hash_verified": True,
        "phase_l_structurally_valid": True,
        "local_timestamp_nondecreasing": monotonic,
        "no_outside_day_rows": outside == 0,
        "zero_eligible_parse_errors": parse_errors == 0,
        "zero_conflicting_trade_ids": duplicate_conflict == 0,
        "zero_expired_btc_vanilla_trades": invalid_expired == 0,
        "strictly_earlier_phase_reference_for_all_used_trades": True,
    }
    readiness_checks = {
        "support_80pct": n_support >= MIN_SUPPORT,
        "run_120min": longest >= MIN_RUN,
        "all_six_segments_exist": all(segments[s] > 0 for s in SEGMENTS),
    }
    return {
        "date": day.isoformat(),
        "raw_rows": rows,
        "valid_btc_vanilla_rows_before_reference_gate": valid_vanilla,
        "classified_trades": len(trades),
        "missing_or_invalid_causal_reference": missing_reference,
        "invalid_expired_trades": invalid_expired,
        "eligible_parse_errors": parse_errors,
        "outside_requested_day_rows": outside,
        "exact_duplicate_trade_ids": duplicate_exact,
        "conflicting_duplicate_trade_ids": duplicate_conflict,
        "family_counts": dict(sorted(family.items())),
        "moneyness_counts": dict(sorted(money.items())),
        "maturity_counts": dict(sorted(maturity.items())),
        "segment_counts": {s: int(segments[s]) for s in SEGMENTS},
        "outside_six_segment_count": int(len(trades) - sum(segments.values())),
        "constructable_minutes": n_support,
        "constructable_fraction": n_support / GRID_COUNT,
        "longest_consecutive_constructable_minutes": longest,
        "reference_age_ms": {
            "min": min(reference_ages) if reference_ages else None,
            "median": median(reference_ages) if reference_ages else None,
            "p95": percentile(reference_ages, 0.95),
            "max": max(reference_ages) if reference_ages else None,
        },
        "integrity_checks": integrity_checks,
        "readiness_checks": readiness_checks,
        "integrity_pass": all(integrity_checks.values()),
        "readiness_pass": all(readiness_checks.values()),
        "pass": all(integrity_checks.values()) and all(readiness_checks.values()),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Frozen CODEX-EXP-012-P0 segmented BTC options-flow readiness audit")
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--feature-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args(argv)

    workspace = args.workspace.resolve()
    output = workspace / args.output
    assert_unsealed_path(output)
    partial = output.with_suffix(output.suffix + ".partial")
    if output.exists() or partial.exists():
        raise RuntimeError("EXP012 output already exists")

    exp011 = workspace / EXP011_RESULT
    if sha256_file(exp011) != EXP011_RESULT_SHA256:
        raise RuntimeError("EXP011 result SHA mismatch")

    days = [load_and_classify(workspace, args.feature_dir, d) for d in DATES]
    integrity_pass = all(x["integrity_pass"] for x in days)
    readiness_pass = all(x["readiness_pass"] for x in days)
    invariants = {
        "exp011_result_sha256_verified": True,
        "all_five_option_raw_hashes_verified": True,
        "btc_only": True,
        "only_march_to_july_loaded": True,
        "atm_log_moneyness_boundary_exact_0_025": ATM_LOG_MONEYNESS == 0.025,
        "atm_numeric_boundary_tolerance_only_1e_12": NUMERIC_BOUNDARY_ABS_TOL == 1e-12,
        "maturity_boundaries_exact_7_and_30_days": SHORT_DTE_DAYS == 7.0 and MEDIUM_DTE_DAYS == 30.0,
        "flow_windows_frozen_1_5_15_30": WINDOW_MINUTES == (1, 5, 15, 30),
        "decision_grid_0030_to_2349": GRID_START_MINUTE == 30 and GRID_END_MINUTE == 23 * 60 + 49,
        "strict_underlying_reference_before_trade": True,
        "network_accessed": False,
        "sealed_august_opened": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
    }
    if not integrity_pass or not all(invariants.values()):
        status = INVALID_STATUS
    elif readiness_pass:
        status = PASS_STATUS
    else:
        status = FAIL_STATUS

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "days": days,
        "all_five_days_integrity_pass": integrity_pass,
        "all_five_days_readiness_pass": readiness_pass,
        "all_five_days_pass": integrity_pass and readiness_pass,
        "invariants": invariants,
        "network_accessed": False,
        "sealed_august_opened": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    partial.replace(output)
    print(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "all_five_days_integrity_pass": integrity_pass,
        "all_five_days_readiness_pass": readiness_pass,
        "sealed_august_opened": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

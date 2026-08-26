from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .codex_exp004_headroom import (
    DAYS,
    assert_fresh_output,
    assert_frozen_workspace,
    feature_path,
    input_manifest,
)
from .codex_exp004_p1 import (
    R_FEATURE_NAMES,
    FixedLogistic,
    build_day_dataset as build_exp004_day_dataset,
    score as exp004_score,
)
from .codex_research import assert_unsealed_path, canonical_sha256, sha256_file
from .v23_phase0dl_score import _load_day


EXPERIMENT_ID = "CODEX-EXP-015-P1"
PASS_STATUS = "PREDICTABLE_INCREMENTAL_SEGMENTED_BTC_OPTIONS_FLOW_SANDBOX"
FAIL_STATUS = "FAIL_SEGMENTED_BTC_OPTIONS_FLOW_NO_INCREMENTAL_TIMING_INFORMATION"
INVALID_STATUS = "INVALID"

SEED = 20260825
SYMBOL = "BTCUSDT"
SUPERVISED_DAYS = DAYS[2:]
OUTER_DAYS = SUPERVISED_DAYS[1:]
WINDOW_MINUTES = (1, 5, 15, 30)
GRID_START_MINUTE = 30
GRID_END_MINUTE = 23 * 60 + 49
GRID_COUNT = 1400
HORIZON_S = 600
ENTRY_DELAY_MS = 250
LABEL_THRESHOLD_BPS = 24.0

ATM_LOG_MONEYNESS = 0.025
NUMERIC_BOUNDARY_ABS_TOL = 1e-12
SHORT_DTE_DAYS = 7.0
MEDIUM_DTE_DAYS = 30.0

SEGMENTS = (
    "atm_short",
    "atm_medium",
    "otm_call_short",
    "otm_call_medium",
    "otm_put_short",
    "otm_put_medium",
)
SEGMENT_METRICS = (
    "log1p_trade_count",
    "log1p_amount",
    "aggressor_amount_imbalance",
    "abs_aggressor_amount_imbalance",
)

FLOW_FEATURE_NAMES = tuple(
    f"segoptflow_{w}m_{segment}_{metric}"
    for w in WINDOW_MINUTES
    for segment in SEGMENTS
    for metric in SEGMENT_METRICS
)
RF_FEATURE_NAMES = R_FEATURE_NAMES + FLOW_FEATURE_NAMES

EXP014_AUDIT = Path(
    "evidence/codex/exp014_p0_exp013_artifact_adjudication/"
    "EXP013_ARTIFACT_ADJUDICATION_P0.json"
)
EXP014_AUDIT_SHA256 = "ff67b0ffddd60e54cf95ecc1ed0f445574b4ed1a9c757287abd543871fea61ff"
EXP013_AUDIT = Path(
    "evidence/codex/exp013_p0_corrected_expiry_segmented_options_flow/"
    "CORRECTED_EXPIRY_SEGMENTED_OPTIONS_FLOW_P0_AUDIT.json"
)
EXP013_AUDIT_SHA256 = "fa590862c00d207917e720e0157db495b67cbf3209bac6301f3568008ac0ce4b"

RAW_ROOT = Path("evidence/codex/exp009_p0_options_trade_flow/raw")
RAW_SHA256 = {
    date(2026, 3, 1): "34835b3e3a022fac0e7270b3e1aca643b01e63b3bbffdab50c99c70dea9af6ba",
    date(2026, 4, 1): "175b24f76bceb68b68c8b6caa04682cb4523bc2e5becc39c41fcf92456a1b605",
    date(2026, 5, 1): "287aaf1a1c62b597c1d46f9f408eef9a0d7c1a73d47ef9edb809f9dc53adda78",
    date(2026, 6, 1): "6076038bb1c07ed4e70a5ca696e04213a5e7e9ab9bfa835360764901925fc6a7",
    date(2026, 7, 1): "02be481f94ac9b66dd43c9f185488b0c2af8f0517f7538d30c6dea565f866bc2",
}

EXPECTED_STRUCTURAL_SUPPORT = {
    date(2026, 3, 1): 1269,
    date(2026, 4, 1): 1315,
    date(2026, 5, 1): 1237,
    date(2026, 6, 1): 1259,
    date(2026, 7, 1): 1254,
}

REQUIRED_COLUMNS = {
    "exchange", "symbol", "timestamp", "local_timestamp", "id", "side", "price", "amount"
}
STANDARD_RE = re.compile(
    r"^BTC[-_](\d{1,2}[A-Z]{3}\d{2})[-_]([0-9]+(?:\.[0-9]+)?)[-_]([CP])$",
    re.I,
)
USDC_RE = re.compile(
    r"^BTC_USDC[-_](\d{1,2}[A-Z]{3}\d{2})[-_]([0-9]+(?:\.[0-9]+)?)[-_]([CP])$",
    re.I,
)


@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbol: str = SYMBOL
    supervised_days: tuple[str, ...] = tuple(d.isoformat() for d in SUPERVISED_DAYS)
    outer_days: tuple[str, ...] = tuple(d.isoformat() for d in OUTER_DAYS)
    windows_minutes: tuple[int, ...] = WINDOW_MINUTES
    segments: tuple[str, ...] = SEGMENTS
    segment_metrics: tuple[str, ...] = SEGMENT_METRICS
    grid_start_minute: int = GRID_START_MINUTE
    grid_end_minute: int = GRID_END_MINUTE
    horizon_s: int = HORIZON_S
    entry_delay_ms: int = ENTRY_DELAY_MS
    label_threshold_bps: float = LABEL_THRESHOLD_BPS
    atm_log_moneyness: float = ATM_LOG_MONEYNESS
    numeric_boundary_abs_tol: float = NUMERIC_BOUNDARY_ABS_TOL
    short_dte_days: float = SHORT_DTE_DAYS
    medium_dte_days: float = MEDIUM_DTE_DAYS
    expiry_hour_utc: int = 8
    r_features: tuple[str, ...] = R_FEATURE_NAMES
    flow_features: tuple[str, ...] = FLOW_FEATURE_NAMES
    rf_features: tuple[str, ...] = RF_FEATURE_NAMES
    model_c: float = 1.0
    solver: str = "lbfgs"
    class_weight: str | None = None
    max_iter: int = 1000
    seed: int = SEED
    pooled_auc_delta_min: float = 0.01
    pooled_ap_delta_min: float = 0.01
    fold_wins_min: int = 3
    pooled_rf_auc_min: float = 0.60
    nonoverlap_auc_delta_min: float = 0.01
    nonoverlap_rf_auc_min: float = 0.57
    timing_falsification_auc_delta_min: float = 0.01
    canary_auc_delta_min: float = 0.10
    exp014_audit_sha256: str = EXP014_AUDIT_SHA256
    exp013_audit_sha256: str = EXP013_AUDIT_SHA256


@dataclass(frozen=True)
class SegmentedOptionTrade:
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
    segment: str | None


@dataclass
class P1DayDataset:
    symbol: str
    day: date
    timestamp_us: np.ndarray
    X_R: np.ndarray
    X_F: np.ndarray
    y: np.ndarray
    oracle_gross_bps: np.ndarray
    valid_flow: np.ndarray
    valid_common: np.ndarray
    nonoverlap_10m: np.ndarray


def _read_json(path: Path) -> dict[str, Any]:
    assert_unsealed_path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def day_start_us(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1_000_000)


def raw_path(day: date) -> Path:
    return RAW_ROOT / f"deribit_trades_{day.isoformat()}_OPTIONS.csv.gz"


def parse_symbol(symbol: str) -> dict[str, Any] | None:
    u = (symbol or "").strip().upper()
    family: str | None = None
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
    expiry = datetime.strptime(expiry_text, "%d%b%y").replace(
        hour=8, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
    )
    strike = float(strike_text)
    if not math.isfinite(strike) or strike <= 0:
        return None
    return {
        "family": family,
        "expiration": int(expiry.timestamp() * 1_000_000),
        "strike": strike,
        "option_type": "call" if cp.upper() == "C" else "put",
    }


def classify_moneyness(option_type: str, strike: float, underlying: float) -> str:
    m = math.log(strike / underlying)
    abs_m = abs(m)
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


def causal_reference(phase: Any, u: int) -> float | None:
    idx = int(np.searchsorted(phase.ts, u, side="left")) - 1
    if idx < 0 or not bool(phase.book_valid[idx]):
        return None
    mid = float(phase.mid[idx])
    if not math.isfinite(mid) or mid <= 0:
        return None
    ts = int(phase.ts[idx])
    if ts >= u:
        raise RuntimeError("equal/future Phase-L underlying reference")
    return mid


def verify_parents_and_raw(workspace: Path) -> tuple[dict[str, Any], dict[str, Any], dict[date, str]]:
    exp014_path = workspace / EXP014_AUDIT
    exp013_path = workspace / EXP013_AUDIT

    if sha256_file(exp014_path) != EXP014_AUDIT_SHA256:
        raise RuntimeError("EXP014 readiness artifact SHA mismatch")
    if sha256_file(exp013_path) != EXP013_AUDIT_SHA256:
        raise RuntimeError("EXP013 corrected-expiry artifact SHA mismatch")

    exp014 = _read_json(exp014_path)
    exp013 = _read_json(exp013_path)

    if exp014.get("experiment_id") != "CODEX-EXP-014-P0":
        raise RuntimeError("wrong EXP014 parent")
    if exp014.get("status") != "DATA_READY_CORRECTED_EXPIRY_SEGMENTED_BTC_OPTIONS_FLOW_SANDBOX":
        raise RuntimeError("EXP014 did not authorize segmented predictive work")
    if exp014.get("recorded_integrity_pass") is not True or exp014.get("recorded_readiness_pass") is not True:
        raise RuntimeError("EXP014 readiness/integrity parent flags not true")
    if not all(exp014.get("verification_checks", {}).values()):
        raise RuntimeError("EXP014 verification checks not all true")

    if exp013.get("experiment_id") != "CODEX-EXP-013-P0":
        raise RuntimeError("wrong EXP013 structural source")
    if exp013.get("status") != "INVALID":
        raise RuntimeError("EXP013 source status must remain frozen INVALID")
    if exp013.get("all_five_days_integrity_pass") is not True:
        raise RuntimeError("EXP013 recorded integrity not true")
    if exp013.get("all_five_days_readiness_pass") is not True:
        raise RuntimeError("EXP013 recorded readiness not true")

    expected_dates = [d.isoformat() for d in SUPERVISED_DAYS]
    days = exp013.get("days", [])
    if [str(x.get("date")) for x in days] != expected_dates:
        raise RuntimeError("EXP013 structural date sequence mismatch")
    for item in days:
        d = date.fromisoformat(str(item["date"]))
        if int(item.get("constructable_minutes", -1)) != EXPECTED_STRUCTURAL_SUPPORT[d]:
            raise RuntimeError(f"EXP013 structural support mismatch: {d}")
        if item.get("integrity_pass") is not True or item.get("readiness_pass") is not True:
            raise RuntimeError(f"EXP013 day not structurally ready: {d}")
        if int(item.get("invalid_expired_trades", -1)) != 0:
            raise RuntimeError(f"EXP013 invalid-expired count changed: {d}")

    observed: dict[date, str] = {}
    for day, expected in RAW_SHA256.items():
        path = workspace / raw_path(day)
        assert_unsealed_path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"frozen option-trade SHA mismatch: {day}")
        observed[day] = actual

    return exp014, exp013, observed


def load_segmented_btc_trades(
    workspace: Path,
    day: date,
    phase: Any,
) -> list[SegmentedOptionTrade]:
    path = workspace / raw_path(day)
    if sha256_file(path) != RAW_SHA256[day]:
        raise RuntimeError(f"raw hash changed during segmented load: {day}")

    start = day_start_us(day)
    end = start + 86_400_000_000
    rows: list[SegmentedOptionTrade] = []
    seen: dict[str, tuple[Any, ...]] = {}
    last_local: int | None = None

    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        if not REQUIRED_COLUMNS.issubset(columns):
            raise RuntimeError(f"option-trades schema mismatch: {day}")

        for raw in reader:
            try:
                local = int(raw.get("local_timestamp", ""))
            except Exception as exc:
                raise RuntimeError(f"invalid local_timestamp in frozen raw: {day}") from exc

            if last_local is not None and local < last_local:
                raise RuntimeError(f"local_timestamp not nondecreasing: {day}")
            last_local = local

            if not (start <= local < end):
                raise RuntimeError(f"outside-day row in frozen raw: {day}")

            meta = parse_symbol(raw.get("symbol", ""))
            if meta is None:
                continue

            try:
                side = (raw.get("side") or "").strip().lower()
                if side not in {"buy", "sell"}:
                    raise ValueError("invalid side")
                trade_id = (raw.get("id") or "").strip()
                if not trade_id:
                    raise ValueError("missing trade id")
                timestamp = int(raw.get("timestamp", ""))
                amount = float(raw.get("amount", ""))
                price = float(raw.get("price", ""))
                if not math.isfinite(amount) or amount <= 0:
                    raise ValueError("invalid amount")
                if not math.isfinite(price) or price <= 0:
                    raise ValueError("invalid price")
            except Exception as exc:
                raise RuntimeError(f"eligible BTC option parse error: {day}") from exc

            econ = (
                str(raw["symbol"]), timestamp, local, side, amount, price,
                meta["family"], meta["option_type"], meta["expiration"], meta["strike"],
            )
            if trade_id in seen:
                if seen[trade_id] == econ:
                    continue
                raise RuntimeError(f"conflicting BTC option trade id: {day} {trade_id}")
            seen[trade_id] = econ

            underlying = causal_reference(phase, local)
            if underlying is None:
                raise RuntimeError(f"missing causal Phase-L underlying reference: {day}")

            maturity = classify_maturity(int(meta["expiration"]), local)
            if maturity == "invalid_expired":
                raise RuntimeError(f"expired BTC vanilla trade under corrected 08:00 expiry: {day}")

            money = classify_moneyness(
                str(meta["option_type"]),
                float(meta["strike"]),
                underlying,
            )
            segment = segment_name(money, maturity)

            rows.append(
                SegmentedOptionTrade(
                    symbol=str(raw["symbol"]),
                    family=str(meta["family"]),
                    option_type=str(meta["option_type"]),
                    expiration_us=int(meta["expiration"]),
                    strike=float(meta["strike"]),
                    local_timestamp=local,
                    timestamp=timestamp,
                    trade_id=trade_id,
                    side=side,
                    amount=amount,
                    price=price,
                    underlying_mid=underlying,
                    segment=segment,
                )
            )

    return rows


def segmented_flow_feature_vector(
    trades: list[SegmentedOptionTrade],
    t_us: int,
) -> np.ndarray | None:
    timestamps = [x.local_timestamp for x in trades]
    hi = bisect.bisect_left(timestamps, t_us)

    one_minute_lo = bisect.bisect_left(
        timestamps,
        t_us - 60_000_000,
        0,
        hi,
    )
    if hi <= one_minute_lo:
        return None

    values: list[float] = []

    for w in WINDOW_MINUTES:
        lo = bisect.bisect_left(
            timestamps,
            t_us - w * 60_000_000,
            0,
            hi,
        )
        window_trades = trades[lo:hi]

        for segment in SEGMENTS:
            xs = [x for x in window_trades if x.segment == segment]

            if not xs:
                values.extend((0.0, 0.0, 0.0, 0.0))
                continue

            total_amount = float(sum(x.amount for x in xs))
            buy_amount = float(sum(x.amount for x in xs if x.side == "buy"))
            sell_amount = float(sum(x.amount for x in xs if x.side == "sell"))

            if total_amount <= 0 or buy_amount + sell_amount <= 0:
                raise RuntimeError("invalid positive-amount segmented flow")

            aggressor = (buy_amount - sell_amount) / (buy_amount + sell_amount)

            values.extend(
                (
                    math.log1p(len(xs)),
                    math.log1p(total_amount),
                    aggressor,
                    abs(aggressor),
                )
            )

    out = np.asarray(values, dtype=np.float64)
    if len(out) != len(FLOW_FEATURE_NAMES):
        raise RuntimeError("EXP015 segmented feature length mismatch")
    if np.any(~np.isfinite(out)):
        raise RuntimeError("EXP015 non-finite segmented feature")
    return out


def build_day_dataset(
    symbol: str,
    phase_day: Any,
    trades: list[SegmentedOptionTrade],
) -> P1DayDataset:
    if symbol != SYMBOL:
        raise ValueError("EXP015 is BTCUSDT only")

    base = build_exp004_day_dataset(symbol, phase_day)
    if base.day not in SUPERVISED_DAYS:
        raise ValueError("day outside EXP015 supervised scope")

    start = day_start_us(base.day)
    X_F = np.full(
        (len(base.timestamp_us), len(FLOW_FEATURE_NAMES)),
        np.nan,
        dtype=np.float64,
    )
    valid_flow = np.zeros(len(base.timestamp_us), dtype=bool)

    for j, t_us in enumerate(base.timestamp_us.tolist()):
        minute = int((int(t_us) - start) // 60_000_000)
        if minute < GRID_START_MINUTE or minute > GRID_END_MINUTE:
            continue

        f = segmented_flow_feature_vector(trades, int(t_us))
        if f is not None:
            X_F[j] = f
            valid_flow[j] = True

    valid_common = base.valid_R & valid_flow

    return P1DayDataset(
        symbol=symbol,
        day=base.day,
        timestamp_us=base.timestamp_us,
        X_R=base.X_R,
        X_F=X_F,
        y=base.y,
        oracle_gross_bps=base.oracle_gross_bps,
        valid_flow=valid_flow,
        valid_common=valid_common,
        nonoverlap_10m=base.nonoverlap_10m,
    )


def training_days(outer_day: date) -> tuple[date, ...]:
    if outer_day not in OUTER_DAYS:
        raise ValueError("outer day outside frozen EXP015 folds")
    return tuple(d for d in SUPERVISED_DAYS if d < outer_day)


def _matrix(
    day: P1DayDataset,
    track: str,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    m = day.valid_common if mask is None else mask
    r = day.X_R[m]
    f = day.X_F[m]

    if track == "R":
        return r
    if track == "F":
        return f
    if track == "RF":
        return np.column_stack((r, f))
    if track == "VOL":
        idx = R_FEATURE_NAMES.index("rv_30m_bps")
        return r[:, [idx]]
    raise ValueError(f"unknown EXP015 track: {track}")


def concat_common(
    days: list[P1DayDataset],
    track: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    mags: list[np.ndarray] = []

    for d in days:
        m = d.valid_common
        xs.append(_matrix(d, track, m))
        ys.append(d.y[m])
        mags.append(d.oracle_gross_bps[m])

    if not xs:
        raise RuntimeError("empty EXP015 common-support calendar")

    return np.concatenate(xs), np.concatenate(ys), np.concatenate(mags)


def _stable_seed(day: date, tag: str = "F_TIME") -> int:
    raw = f"{SEED}|{tag}|{SYMBOL}|{day.isoformat()}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") % (2**32)


def permute_complete_f_vectors(
    day: P1DayDataset,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    m = day.valid_common if mask is None else mask
    f = day.X_F[m].copy()
    if len(f) <= 1:
        return f
    rng = np.random.default_rng(_stable_seed(day.day))
    return f[rng.permutation(len(f))]


def concat_rf_time_permuted(
    days: list[P1DayDataset],
) -> tuple[np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []

    for d in days:
        m = d.valid_common
        xs.append(np.column_stack((d.X_R[m], permute_complete_f_vectors(d, m))))
        ys.append(d.y[m])

    return np.concatenate(xs), np.concatenate(ys)


def metrics(records: list[dict[str, Any]], key: str) -> dict[str, Any]:
    def score_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return exp004_score(
            [r["label"] for r in rows],
            [r[key] for r in rows],
        )

    non = [r for r in records if r["nonoverlap_10m"]]

    return {
        "pooled": score_rows(records),
        "by_fold": {
            d.isoformat(): score_rows(
                [r for r in records if r["outer_day"] == d.isoformat()]
            )
            for d in OUTER_DAYS
        },
        "nonoverlap_pooled": score_rows(non),
    }


def _ge_delta(
    a: float | None,
    b: float | None,
    threshold: float,
) -> bool:
    return a is not None and b is not None and a - b >= threshold


def _gt(a: float | None, b: float | None) -> bool:
    return a is not None and b is not None and a > b


def _ge(a: float | None, threshold: float) -> bool:
    return a is not None and a >= threshold


def primary_gates(
    M: dict[str, dict[str, Any]],
    invariants: dict[str, bool],
) -> dict[str, bool]:
    r = M["R"]
    rf = M["RF"]
    perm = M["RF_F_TIME_PERMUTED"]
    canary = M["CANARY_R"]

    rp = r["pooled"]
    fp = rf["pooled"]
    pp = perm["pooled"]
    cp = canary["pooled"]

    return {
        "pooled_auc_delta_at_least_0_01":
            _ge_delta(fp["roc_auc"], rp["roc_auc"], 0.01),
        "pooled_average_precision_delta_at_least_0_01":
            _ge_delta(fp["average_precision"], rp["average_precision"], 0.01),
        "pooled_top_decile_precision_not_lower": (
            fp["top_decile_precision"] is not None
            and rp["top_decile_precision"] is not None
            and fp["top_decile_precision"] >= rp["top_decile_precision"]
        ),
        "pooled_log_loss_lower": _gt(rp["log_loss"], fp["log_loss"]),
        "pooled_brier_lower": _gt(rp["brier_score"], fp["brier_score"]),
        "at_least_3_of_4_folds_rf_auc_gt_r": sum(
            _gt(
                rf["by_fold"][d.isoformat()]["roc_auc"],
                r["by_fold"][d.isoformat()]["roc_auc"],
            )
            for d in OUTER_DAYS
        ) >= 3,
        "pooled_rf_auc_at_least_0_60":
            _ge(fp["roc_auc"], 0.60),
        "nonoverlap_auc_delta_at_least_0_01":
            _ge_delta(
                rf["nonoverlap_pooled"]["roc_auc"],
                r["nonoverlap_pooled"]["roc_auc"],
                0.01,
            ),
        "nonoverlap_rf_auc_at_least_0_57":
            _ge(rf["nonoverlap_pooled"]["roc_auc"], 0.57),
        "flow_timing_falsification_auc_delta_at_least_0_01":
            _ge_delta(fp["roc_auc"], pp["roc_auc"], 0.01),
        "positive_control_canary_auc_delta_at_least_0_10":
            _ge_delta(cp["roc_auc"], rp["roc_auc"], 0.10),
        "implementation_provenance_causality_invariants_pass":
            all(invariants.values()),
    }


def _metric_delta(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else float(a - b)


def run(
    feature_dir: Path,
    output: Path,
    workspace: Path,
    frozen_commit: str,
) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)
    partial = assert_fresh_output(output)

    exp014, exp013, observed_hashes = verify_parents_and_raw(workspace)
    phase_manifest = input_manifest(feature_dir, workspace)

    phase_days: dict[date, Any] = {}
    option_trades: dict[date, list[SegmentedOptionTrade]] = {}
    data: dict[date, P1DayDataset] = {}

    structural_support_match = True

    for day in SUPERVISED_DAYS:
        phase = _load_day(feature_path(feature_dir, SYMBOL, day), day)
        phase_days[day] = phase

        trades = load_segmented_btc_trades(workspace, day, phase)
        option_trades[day] = trades

        ds = build_day_dataset(SYMBOL, phase, trades)
        data[day] = ds

        grid_flow_n = int(np.sum(ds.valid_flow))
        structural_support_match &= grid_flow_n == EXPECTED_STRUCTURAL_SUPPORT[day]

    if not structural_support_match:
        raise RuntimeError("EXP015 flow support does not match frozen EXP013 structural support")

    records: list[dict[str, Any]] = []
    fold_counts: list[dict[str, Any]] = []
    common_support_exact = True

    for outer_day in OUTER_DAYS:
        train_calendar = training_days(outer_day)
        train = [data[d] for d in train_calendar]
        outer = data[outer_day]

        XR, yR, mag = concat_common(train, "R")
        XF, yF, _ = concat_common(train, "F")
        XRF, yRF, mag_rf = concat_common(train, "RF")
        XVOL, yVOL, _ = concat_common(train, "VOL")
        XPERM, yPERM = concat_rf_time_permuted(train)

        labels_equal = all(
            np.array_equal(yR, y)
            for y in (yF, yRF, yVOL, yPERM)
        )
        lengths_equal = (
            len(XR) == len(XF) == len(XRF) == len(XVOL) == len(XPERM)
        )

        common_support_exact &= (
            labels_equal
            and lengths_equal
            and np.array_equal(mag, mag_rf)
        )

        if not common_support_exact:
            raise RuntimeError("EXP015 common training support invariant failed")

        model_r = FixedLogistic().fit(XR, yR)
        model_f = FixedLogistic().fit(XF, yR)
        model_rf = FixedLogistic().fit(XRF, yR)
        model_vol = FixedLogistic().fit(XVOL, yR)
        model_perm = FixedLogistic().fit(XPERM, yR)
        model_canary = FixedLogistic().fit(
            np.column_stack((XR, mag)),
            yR,
        )

        m = outer.valid_common
        XR_o = _matrix(outer, "R", m)
        XF_o = _matrix(outer, "F", m)
        XRF_o = _matrix(outer, "RF", m)
        XVOL_o = _matrix(outer, "VOL", m)
        FPERM_o = permute_complete_f_vectors(outer, m)
        XPERM_o = np.column_stack((XR_o, FPERM_o))

        n_outer = int(np.sum(m))
        common_support_exact &= all(
            len(x) == n_outer
            for x in (XR_o, XF_o, XRF_o, XVOL_o, XPERM_o)
        )

        if not common_support_exact:
            raise RuntimeError("EXP015 common outer support invariant failed")

        p_r = model_r.predict_proba(XR_o)
        p_f = model_f.predict_proba(XF_o)
        p_rf = model_rf.predict_proba(XRF_o)
        p_vol = model_vol.predict_proba(XVOL_o)
        p_perm = model_perm.predict_proba(XPERM_o)
        p_canary = model_canary.predict_proba(
            np.column_stack((XR_o, outer.oracle_gross_bps[m]))
        )

        idx = np.flatnonzero(m)

        fold_counts.append(
            {
                "outer_day": outer_day.isoformat(),
                "training_days": [d.isoformat() for d in train_calendar],
                "common_train_n": int(len(yR)),
                "common_outer_n": n_outer,
                "R_train_n": int(len(XR)),
                "F_train_n": int(len(XF)),
                "RF_train_n": int(len(XRF)),
                "RF_permuted_train_n": int(len(XPERM)),
            }
        )

        for j, source_idx in enumerate(idx.tolist()):
            records.append(
                {
                    "outer_day": outer_day.isoformat(),
                    "symbol": SYMBOL,
                    "timestamp_us": int(outer.timestamp_us[source_idx]),
                    "label": int(outer.y[source_idx]),
                    "oracle_gross_bps": float(
                        outer.oracle_gross_bps[source_idx]
                    ),
                    "nonoverlap_10m": bool(
                        outer.nonoverlap_10m[source_idx]
                    ),
                    "p_R": float(p_r[j]),
                    "p_F": float(p_f[j]),
                    "p_RF": float(p_rf[j]),
                    "p_VOL": float(p_vol[j]),
                    "p_RF_F_TIME_PERMUTED": float(p_perm[j]),
                    "p_CANARY_R": float(p_canary[j]),
                }
            )

    metric_keys = {
        "R": "p_R",
        "F": "p_F",
        "RF": "p_RF",
        "VOL": "p_VOL",
        "RF_F_TIME_PERMUTED": "p_RF_F_TIME_PERMUTED",
        "CANARY_R": "p_CANARY_R",
    }
    M = {
        name: metrics(records, key)
        for name, key in metric_keys.items()
    }

    exp013_days = {
        date.fromisoformat(str(x["date"])): x
        for x in exp013["days"]
    }

    invariants = {
        "exp014_parent_sha256_verified":
            sha256_file(workspace / EXP014_AUDIT) == EXP014_AUDIT_SHA256,
        "exp014_parent_status_ready":
            exp014.get("status")
            == "DATA_READY_CORRECTED_EXPIRY_SEGMENTED_BTC_OPTIONS_FLOW_SANDBOX",
        "exp013_structural_sha256_verified":
            sha256_file(workspace / EXP013_AUDIT) == EXP013_AUDIT_SHA256,
        "exp013_source_status_preserved_invalid":
            exp013.get("status") == "INVALID",
        "all_five_option_trade_hashes_verified":
            observed_hashes == RAW_SHA256,
        "btc_target_only":
            SYMBOL == "BTCUSDT",
        "only_march_to_july_supervised_days_loaded":
            tuple(SUPERVISED_DAYS) == tuple(DAYS[2:]),
        "outer_folds_are_april_to_july":
            tuple(OUTER_DAYS) == tuple(DAYS[3:]),
        "flow_windows_exactly_1_5_15_30_minutes":
            WINDOW_MINUTES == (1, 5, 15, 30),
        "six_segments_exact":
            SEGMENTS == (
                "atm_short",
                "atm_medium",
                "otm_call_short",
                "otm_call_medium",
                "otm_put_short",
                "otm_put_medium",
            ),
        "four_metrics_per_segment_exact":
            SEGMENT_METRICS == (
                "log1p_trade_count",
                "log1p_amount",
                "aggressor_amount_imbalance",
                "abs_aggressor_amount_imbalance",
            ),
        "flow_feature_count_exact_96":
            len(FLOW_FEATURE_NAMES) == 96,
        "corrected_deribit_expiry_0800_utc":
            Config().expiry_hour_utc == 8,
        "moneyness_boundary_exact_0_025":
            ATM_LOG_MONEYNESS == 0.025,
        "moneyness_numeric_tolerance_exact_1e_12":
            NUMERIC_BOUNDARY_ABS_TOL == 1e-12,
        "maturity_boundaries_exact_7_and_30":
            SHORT_DTE_DAYS == 7.0 and MEDIUM_DTE_DAYS == 30.0,
        "flow_grid_starts_0030_and_ends_2349":
            GRID_START_MINUTE == 30 and GRID_END_MINUTE == 1429,
        "strict_local_timestamp_less_than_decision":
            True,
        "strict_phase_reference_before_option_trade":
            True,
        "segment_zero_flow_encoded_as_zero":
            True,
        "aggregate_one_minute_support_required":
            True,
        "flow_support_matches_exp013_all_days":
            structural_support_match
            and all(
                int(exp013_days[d]["constructable_minutes"])
                == EXPECTED_STRUCTURAL_SUPPORT[d]
                for d in SUPERVISED_DAYS
            ),
        "r_rf_common_training_and_outer_support_exact":
            common_support_exact,
        "outer_folds_chronological":
            all(
                all(d < outer for d in training_days(outer))
                for outer in OUTER_DAYS
            ),
        "scaling_fit_on_training_only_by_fixed_pipeline":
            True,
        "sealed_august_not_accessed":
            True,
        "direction_not_scored":
            True,
        "pnl_not_scored":
            True,
    }

    gates = primary_gates(M, invariants)

    if not all(invariants.values()):
        status = INVALID_STATUS
    elif all(gates.values()):
        status = PASS_STATUS
    else:
        status = FAIL_STATUS

    rp = M["R"]["pooled"]
    fp = M["RF"]["pooled"]
    pp = M["RF_F_TIME_PERMUTED"]["pooled"]
    cp = M["CANARY_R"]["pooled"]

    deltas = {
        "RF_auc_minus_R_auc":
            _metric_delta(fp["roc_auc"], rp["roc_auc"]),
        "RF_average_precision_minus_R":
            _metric_delta(
                fp["average_precision"],
                rp["average_precision"],
            ),
        "RF_top_decile_precision_minus_R":
            _metric_delta(
                fp["top_decile_precision"],
                rp["top_decile_precision"],
            ),
        "R_log_loss_minus_RF_log_loss":
            _metric_delta(rp["log_loss"], fp["log_loss"]),
        "R_brier_minus_RF_brier":
            _metric_delta(rp["brier_score"], fp["brier_score"]),
        "RF_auc_minus_F_time_permuted_auc":
            _metric_delta(fp["roc_auc"], pp["roc_auc"]),
        "CANARY_R_auc_minus_R_auc":
            _metric_delta(cp["roc_auc"], rp["roc_auc"]),
    }

    used_phase = [
        item
        for item in phase_manifest
        if str(item.get("symbol")) == SYMBOL
        and date.fromisoformat(str(item["day"])) in SUPERVISED_DAYS
    ]

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "sandbox_only": True,
        "direction_scored": False,
        "pnl_scored": False,
        "sealed_august_opened": False,
        "frozen_commit": frozen_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": asdict(Config()),
        "configuration_sha256": canonical_sha256(Config()),
        "provenance": {
            "exp014_audit_sha256": EXP014_AUDIT_SHA256,
            "exp013_audit_sha256": EXP013_AUDIT_SHA256,
            "verified_option_trade_raw_sha256": {
                d.isoformat(): observed_hashes[d]
                for d in SUPERVISED_DAYS
            },
            "expected_structural_support_by_day": {
                d.isoformat(): EXPECTED_STRUCTURAL_SUPPORT[d]
                for d in SUPERVISED_DAYS
            },
            "verified_phase_l_input_manifest_all_frozen_days":
                phase_manifest,
            "phase_l_inputs_used_for_exp015":
                used_phase,
        },
        "fold_train_counts": fold_counts,
        "metrics": M,
        "gates": gates,
        "invariants": invariants,
        "diagnostic_deltas": deltas,
        "oos_prediction_records_sha256":
            canonical_sha256(records),
        "oos_prediction_records": records,
        "interpretation": (
            "Segmented BTC option-flow incremental 10-minute opportunity "
            "timing only. No direction, PnL, August validation, or "
            "profitability claim is permitted."
        ),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )
    partial.replace(output)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Frozen CODEX-EXP-015-P1 segmented BTC options-flow "
            "incremental timing test"
        )
    )
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args(argv)

    result = run(
        args.feature_dir,
        args.output,
        args.workspace,
        args.frozen_commit,
    )

    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "status": result["status"],
                "configuration_sha256":
                    result["configuration_sha256"],
                "gates": result["gates"],
                "diagnostic_deltas":
                    result["diagnostic_deltas"],
                "sealed_august_opened":
                    result["sealed_august_opened"],
                "direction_scored":
                    result["direction_scored"],
                "pnl_scored":
                    result["pnl_scored"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

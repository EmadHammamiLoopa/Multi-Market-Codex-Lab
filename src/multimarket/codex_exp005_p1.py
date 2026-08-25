from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .codex_exp004_headroom import (
    DAYS,
    SYMBOLS,
    assert_fresh_output,
    assert_frozen_workspace,
    feature_path,
    input_manifest,
)
from .codex_exp004_p1 import (
    R_FEATURE_NAMES,
    FixedLogistic,
    build_day_dataset as build_exp004_day_dataset,
    metrics as exp004_metrics,
)
from .codex_exp005_acquire import DatasetRequest
from .codex_exp005_audit import parse_timestamp_us
from .codex_research import assert_unsealed_path, canonical_sha256, sha256_file
from .v23_phase0dl_score import _load_day


EXPERIMENT_ID = "CODEX-EXP-005-P1"
SEED = 20260825
OUTER_DAYS = DAYS[2:]
DECISION_STEP_S = 60
HORIZON_S = 600
ENTRY_DELAY_MS = 250
LABEL_THRESHOLD_BPS = 24.0
MAX_STALENESS_S = 30
MAX_STALENESS_US = MAX_STALENESS_S * 1_000_000
MINUTE_US = 60_000_000

PARENT_AUDIT_SHA256 = "b151aba2455ee237acf34da76d257b6f8d1a221166cffdbe967851315482ef52"
PARENT_AUDIT_CONFIG_SHA256 = "26493155132bec2d2252335bb3380f0ccd84aec933acb7f8a114040d1538ba9a"
P0_ACQUISITION_MANIFEST = Path("evidence/codex/exp005_p0_acquisition/ACQUISITION_MANIFEST.json")
P0_AUDIT_ARTIFACT = Path("evidence/codex/exp005_p0_audit/DERIVATIVES_STATE_AUDIT.json")

OI_FEATURE_NAMES = (
    "oi_log",
    "oi_log_change_1m",
    "oi_log_change_5m",
    "oi_log_change_15m",
    "oi_log_change_30m",
    "oi_log_z_5m",
    "oi_log_z_30m",
)
PREMIUM_FEATURE_NAMES = (
    "premium_bps",
    "premium_change_1m",
    "premium_change_5m",
    "premium_change_15m",
    "premium_change_30m",
    "premium_z_30m",
)
FUNDING_FEATURE_NAMES = (
    "funding_rate",
    "funding_change_previous_distinct",
)
D_FEATURE_NAMES = OI_FEATURE_NAMES + PREMIUM_FEATURE_NAMES + FUNDING_FEATURE_NAMES
RD_FEATURE_NAMES = R_FEATURE_NAMES + D_FEATURE_NAMES
SIGNED_D_FEATURES = (
    "oi_log_change_1m",
    "oi_log_change_5m",
    "oi_log_change_15m",
    "oi_log_change_30m",
    "premium_change_1m",
    "premium_change_5m",
    "premium_change_15m",
    "premium_change_30m",
    "funding_change_previous_distinct",
)

OI_SLICE = slice(0, len(OI_FEATURE_NAMES))
PREMIUM_SLICE = slice(len(OI_FEATURE_NAMES), len(OI_FEATURE_NAMES) + len(PREMIUM_FEATURE_NAMES))
FUNDING_SLICE = slice(len(OI_FEATURE_NAMES) + len(PREMIUM_FEATURE_NAMES), len(D_FEATURE_NAMES))


@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbols: tuple[str, ...] = SYMBOLS
    days: tuple[str, ...] = tuple(d.isoformat() for d in DAYS)
    outer_days: tuple[str, ...] = tuple(d.isoformat() for d in OUTER_DAYS)
    decision_step_s: int = DECISION_STEP_S
    horizon_s: int = HORIZON_S
    entry_delay_ms: int = ENTRY_DELAY_MS
    label_threshold_bps: float = LABEL_THRESHOLD_BPS
    r_features: tuple[str, ...] = R_FEATURE_NAMES
    d_features: tuple[str, ...] = D_FEATURE_NAMES
    rd_features: tuple[str, ...] = RD_FEATURE_NAMES
    signed_d_features: tuple[str, ...] = SIGNED_D_FEATURES
    max_derivatives_staleness_s: int = MAX_STALENESS_S
    oi_change_lookbacks_min: tuple[int, ...] = (1, 5, 15, 30)
    oi_zscore_windows_min: tuple[int, ...] = (5, 30)
    premium_change_lookbacks_min: tuple[int, ...] = (1, 5, 15, 30)
    premium_zscore_windows_min: tuple[int, ...] = (30,)
    trailing_zscore_grid: str = "inclusive 1-minute grid from t-window through t; population std"
    oi_zscore_domain: str = "log open interest"
    funding_change_rule: str = "current funding minus immediately previous distinct native funding state"
    availability_clock: str = "local_timestamp only"
    model_c: float = 1.0
    solver: str = "lbfgs"
    class_weight: str | None = None
    max_iter: int = 1000
    seed: int = SEED
    pooled_auc_delta_min: float = 0.01
    pooled_ap_delta_min: float = 0.01
    nonoverlap_auc_delta_min: float = 0.01
    timing_falsification_auc_delta_min: float = 0.01
    canary_auc_delta_min: float = 0.10
    parent_audit_sha256: str = PARENT_AUDIT_SHA256
    parent_audit_configuration_sha256: str = PARENT_AUDIT_CONFIG_SHA256


@dataclass
class DerivativeDayState:
    symbol: str
    day: date
    open_interest_ts: np.ndarray
    open_interest: np.ndarray
    funding_ts: np.ndarray
    funding_rate: np.ndarray
    funding_delta_previous_distinct: np.ndarray
    mark_ts: np.ndarray
    mark_price: np.ndarray
    index_ts: np.ndarray
    index_price: np.ndarray
    raw_sha256: str


@dataclass
class P1DayDataset:
    symbol: str
    day: date
    timestamp_us: np.ndarray
    X_R: np.ndarray
    X_D: np.ndarray
    y: np.ndarray
    oracle_gross_bps: np.ndarray
    valid_common: np.ndarray
    nonoverlap_10m: np.ndarray


def _parse_float(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def _sorted_updates(ts: list[int], values: list[float]) -> tuple[np.ndarray, np.ndarray]:
    if len(ts) != len(values):
        raise ValueError("timestamp/value length mismatch")
    if not ts:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.float64)
    t = np.asarray(ts, dtype=np.int64)
    v = np.asarray(values, dtype=np.float64)
    order = np.argsort(t, kind="stable")
    return t[order], v[order]


def _funding_delta_from_previous_distinct(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    out = np.full(len(values), np.nan, dtype=np.float64)
    if len(values) == 0:
        return out
    current = float(values[0])
    previous_distinct: float | None = None
    current_delta = float("nan")
    for i, value in enumerate(values.tolist()):
        value = float(value)
        if value != current:
            previous_distinct = current
            current = value
            current_delta = current - previous_distinct
        out[i] = current_delta
    return out


def load_derivative_day(path: Path, symbol: str, day: date) -> DerivativeDayState:
    if symbol not in SYMBOLS or day not in DAYS:
        raise ValueError("symbol/day outside frozen EXP005-P1")
    assert_unsealed_path(path)
    required = {"local_timestamp", "open_interest", "funding_rate", "mark_price", "index_price"}

    oi_ts: list[int] = []
    oi: list[float] = []
    funding_ts: list[int] = []
    funding: list[float] = []
    mark_ts: list[int] = []
    mark: list[float] = []
    index_ts: list[int] = []
    index: list[float] = []

    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or ())
        missing = sorted(required - columns)
        if missing:
            raise RuntimeError(f"missing frozen derivatives columns {missing}: {path}")
        # `timestamp` is intentionally ignored. D availability is local_timestamp only.
        for row in reader:
            local = parse_timestamp_us(row.get("local_timestamp", ""))
            oi_value = _parse_float(row.get("open_interest"))
            if oi_value is not None:
                oi_ts.append(local)
                oi.append(oi_value)
            funding_value = _parse_float(row.get("funding_rate"))
            if funding_value is not None:
                funding_ts.append(local)
                funding.append(funding_value)
            mark_value = _parse_float(row.get("mark_price"))
            if mark_value is not None:
                mark_ts.append(local)
                mark.append(mark_value)
            index_value = _parse_float(row.get("index_price"))
            if index_value is not None:
                index_ts.append(local)
                index.append(index_value)

    oi_t, oi_v = _sorted_updates(oi_ts, oi)
    f_t, f_v = _sorted_updates(funding_ts, funding)
    m_t, m_v = _sorted_updates(mark_ts, mark)
    i_t, i_v = _sorted_updates(index_ts, index)
    if min(len(oi_t), len(f_t), len(m_t), len(i_t)) == 0:
        raise RuntimeError(f"required derivatives state absent: {path}")

    return DerivativeDayState(
        symbol=symbol,
        day=day,
        open_interest_ts=oi_t,
        open_interest=oi_v,
        funding_ts=f_t,
        funding_rate=f_v,
        funding_delta_previous_distinct=_funding_delta_from_previous_distinct(f_v),
        mark_ts=m_t,
        mark_price=m_v,
        index_ts=i_t,
        index_price=i_v,
        raw_sha256=sha256_file(path),
    )


def lookup_state(
    update_ts: np.ndarray,
    update_values: np.ndarray,
    query_ts: np.ndarray | int,
    *,
    max_staleness_us: int = MAX_STALENESS_US,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    q = np.asarray(query_ts, dtype=np.int64)
    flat = q.reshape(-1)
    idx = np.searchsorted(update_ts, flat, side="right") - 1
    values = np.full(len(flat), np.nan, dtype=np.float64)
    sources = np.full(len(flat), -1, dtype=np.int64)
    valid = idx >= 0
    if np.any(valid):
        loc = np.flatnonzero(valid)
        ridx = idx[loc]
        source = update_ts[ridx]
        candidate = update_values[ridx]
        causal = source <= flat[loc]
        fresh = (flat[loc] - source) <= max_staleness_us
        finite = np.isfinite(candidate)
        keep = causal & fresh & finite
        good_loc = loc[keep]
        good_idx = ridx[keep]
        values[good_loc] = update_values[good_idx]
        sources[good_loc] = update_ts[good_idx]
        valid[:] = False
        valid[good_loc] = True
    shape = q.shape
    return values.reshape(shape), sources.reshape(shape), valid.reshape(shape)


def lag_lookup_times(t_us: int, lookbacks_min: tuple[int, ...] = (1, 5, 15, 30)) -> np.ndarray:
    return np.asarray([t_us - m * MINUTE_US for m in lookbacks_min], dtype=np.int64)


def trailing_grid_times(t_us: int, window_min: int) -> np.ndarray:
    if window_min <= 0:
        raise ValueError("window must be positive")
    return t_us - np.arange(window_min, -1, -1, dtype=np.int64) * MINUTE_US


def _zscore_current(values: np.ndarray) -> float | None:
    values = np.asarray(values, dtype=np.float64)
    if len(values) < 2 or np.any(~np.isfinite(values)):
        return None
    std = float(np.std(values))
    if not np.isfinite(std) or std <= 0:
        return None
    return float((values[-1] - float(np.mean(values))) / std)


def _oi_at(state: DerivativeDayState, query: np.ndarray | int) -> tuple[np.ndarray, np.ndarray]:
    values, _, valid = lookup_state(state.open_interest_ts, state.open_interest, query)
    valid = valid & np.isfinite(values) & (values > 0)
    out = np.full(values.shape, np.nan, dtype=np.float64)
    out[valid] = np.log(values[valid])
    return out, valid


def _premium_at(state: DerivativeDayState, query: np.ndarray | int) -> tuple[np.ndarray, np.ndarray]:
    mark, _, mv = lookup_state(state.mark_ts, state.mark_price, query)
    index, _, iv = lookup_state(state.index_ts, state.index_price, query)
    valid = mv & iv & np.isfinite(mark) & np.isfinite(index) & (mark > 0) & (index > 0)
    out = np.full(mark.shape, np.nan, dtype=np.float64)
    out[valid] = 10_000.0 * (mark[valid] / index[valid] - 1.0)
    return out, valid


def d_feature_vector(state: DerivativeDayState, t_us: int) -> np.ndarray | None:
    current_oi, cv = _oi_at(state, np.asarray([t_us], dtype=np.int64))
    lag_times = lag_lookup_times(t_us)
    lag_oi, lv = _oi_at(state, lag_times)
    if not bool(cv[0]) or not bool(np.all(lv)):
        return None
    oi_now = float(current_oi[0])
    oi_changes = [oi_now - float(x) for x in lag_oi.tolist()]

    oi_z: list[float] = []
    for window in (5, 30):
        history, hv = _oi_at(state, trailing_grid_times(t_us, window))
        if not bool(np.all(hv)):
            return None
        z = _zscore_current(history)
        if z is None:
            return None
        oi_z.append(z)

    current_premium, pv = _premium_at(state, np.asarray([t_us], dtype=np.int64))
    lag_premium, plv = _premium_at(state, lag_times)
    if not bool(pv[0]) or not bool(np.all(plv)):
        return None
    premium_now = float(current_premium[0])
    premium_changes = [premium_now - float(x) for x in lag_premium.tolist()]
    premium_history, phv = _premium_at(state, trailing_grid_times(t_us, 30))
    if not bool(np.all(phv)):
        return None
    premium_z = _zscore_current(premium_history)
    if premium_z is None:
        return None

    funding, _, fv = lookup_state(state.funding_ts, state.funding_rate, np.asarray([t_us], dtype=np.int64))
    funding_delta, _, fdv = lookup_state(
        state.funding_ts,
        state.funding_delta_previous_distinct,
        np.asarray([t_us], dtype=np.int64),
    )
    if not bool(fv[0]) or not bool(fdv[0]):
        return None

    values = np.asarray(
        [
            oi_now,
            *oi_changes,
            *oi_z,
            premium_now,
            *premium_changes,
            premium_z,
            float(funding[0]),
            float(funding_delta[0]),
        ],
        dtype=np.float64,
    )
    if len(values) != len(D_FEATURE_NAMES) or np.any(~np.isfinite(values)):
        return None
    return values


def build_day_dataset(symbol: str, phase_day: Any, derivative_state: DerivativeDayState) -> P1DayDataset:
    base = build_exp004_day_dataset(symbol, phase_day)
    if derivative_state.symbol != symbol or derivative_state.day != base.day:
        raise RuntimeError("derivatives/Phase-L symbol-day mismatch")
    X_D = np.full((len(base.timestamp_us), len(D_FEATURE_NAMES)), np.nan, dtype=np.float64)
    valid_D = np.zeros(len(base.timestamp_us), dtype=bool)
    for j, t_us in enumerate(base.timestamp_us.tolist()):
        if not base.valid_R[j]:
            continue
        d = d_feature_vector(derivative_state, int(t_us))
        if d is not None:
            X_D[j] = d
            valid_D[j] = True
    valid_common = base.valid_R & valid_D
    return P1DayDataset(
        symbol=symbol,
        day=base.day,
        timestamp_us=base.timestamp_us,
        X_R=base.X_R,
        X_D=X_D,
        y=base.y,
        oracle_gross_bps=base.oracle_gross_bps,
        valid_common=valid_common,
        nonoverlap_10m=base.nonoverlap_10m,
    )


def training_days(outer_day: date) -> tuple[date, ...]:
    if outer_day not in OUTER_DAYS:
        raise ValueError("outer day outside frozen folds")
    return tuple(day for day in DAYS if day < outer_day)


def _matrix(day: P1DayDataset, track: str, mask: np.ndarray | None = None) -> np.ndarray:
    m = day.valid_common if mask is None else mask
    r = day.X_R[m]
    d = day.X_D[m]
    if track == "R":
        return r
    if track == "D":
        return d
    if track == "RD":
        return np.column_stack((r, d))
    if track == "ROI":
        return np.column_stack((r, d[:, OI_SLICE]))
    if track == "RPREMIUM":
        return np.column_stack((r, d[:, PREMIUM_SLICE]))
    if track == "RFUNDING":
        return np.column_stack((r, d[:, FUNDING_SLICE]))
    if track == "VOL":
        idx = R_FEATURE_NAMES.index("rv_30m_bps")
        return r[:, [idx]]
    raise ValueError(f"unknown track: {track}")


def concat_common(days: list[P1DayDataset], track: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    mags: list[np.ndarray] = []
    for day in days:
        m = day.valid_common
        xs.append(_matrix(day, track, m))
        ys.append(day.y[m])
        mags.append(day.oracle_gross_bps[m])
    if not xs:
        raise RuntimeError("empty common-support calendar")
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(mags)


def _stable_seed(symbol: str, day: date, tag: str = "D_TIME") -> int:
    raw = f"{SEED}|{tag}|{symbol}|{day.isoformat()}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") % (2**32)


def permute_complete_d_vectors(day: P1DayDataset, mask: np.ndarray | None = None) -> np.ndarray:
    m = day.valid_common if mask is None else mask
    d = day.X_D[m].copy()
    if len(d) <= 1:
        return d
    rng = np.random.default_rng(_stable_seed(day.symbol, day.day))
    return d[rng.permutation(len(d))]


def concat_rd_time_permuted(days: list[P1DayDataset]) -> tuple[np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    for day in days:
        m = day.valid_common
        xs.append(np.column_stack((day.X_R[m], permute_complete_d_vectors(day, m))))
        ys.append(day.y[m])
    return np.concatenate(xs), np.concatenate(ys)


def _metric_delta(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else float(a - b)


def primary_gates(metrics: dict[str, dict[str, Any]], invariants: dict[str, bool]) -> dict[str, bool]:
    r = metrics["R"]
    rd = metrics["RD"]
    perm = metrics["RD_D_TIME_PERMUTED"]
    canary = metrics["CANARY_R"]
    rp = r["pooled"]
    dp = rd["pooled"]
    pp = perm["pooled"]
    cp = canary["pooled"]

    def ge_delta(a: float | None, b: float | None, threshold: float) -> bool:
        return a is not None and b is not None and a - b >= threshold

    def gt_value(a: float | None, b: float | None) -> bool:
        return a is not None and b is not None and a > b

    gates = {
        "pooled_auc_delta_at_least_0_01": ge_delta(dp["roc_auc"], rp["roc_auc"], 0.01),
        "pooled_average_precision_delta_at_least_0_01": ge_delta(
            dp["average_precision"], rp["average_precision"], 0.01
        ),
        "pooled_top_decile_precision_not_lower": (
            dp["top_decile_precision"] is not None
            and rp["top_decile_precision"] is not None
            and dp["top_decile_precision"] >= rp["top_decile_precision"]
        ),
        "pooled_log_loss_lower": (
            dp["log_loss"] is not None and rp["log_loss"] is not None and dp["log_loss"] < rp["log_loss"]
        ),
        "at_least_4_of_5_folds_rd_auc_gt_r": sum(
            gt_value(rd["by_fold"][d.isoformat()]["roc_auc"], r["by_fold"][d.isoformat()]["roc_auc"])
            for d in OUTER_DAYS
        ) >= 4,
        "btc_rd_auc_gt_r": gt_value(rd["by_symbol"]["BTCUSDT"]["roc_auc"], r["by_symbol"]["BTCUSDT"]["roc_auc"]),
        "eth_rd_auc_gt_r": gt_value(rd["by_symbol"]["ETHUSDT"]["roc_auc"], r["by_symbol"]["ETHUSDT"]["roc_auc"]),
        "nonoverlap_auc_delta_at_least_0_01": ge_delta(
            rd["nonoverlap_pooled"]["roc_auc"], r["nonoverlap_pooled"]["roc_auc"], 0.01
        ),
        "derivatives_timing_falsification_auc_delta_at_least_0_01": ge_delta(
            dp["roc_auc"], pp["roc_auc"], 0.01
        ),
        "positive_control_canary_auc_delta_at_least_0_10": ge_delta(
            cp["roc_auc"], rp["roc_auc"], 0.10
        ),
        "implementation_provenance_causality_invariants_pass": all(invariants.values()),
    }
    return gates


def _read_json(path: Path) -> dict[str, Any]:
    assert_unsealed_path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def verify_parent_inputs(workspace: Path, raw_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[tuple[str, date], str]]:
    audit_path = workspace / P0_AUDIT_ARTIFACT
    acquisition_path = workspace / P0_ACQUISITION_MANIFEST
    if sha256_file(audit_path) != PARENT_AUDIT_SHA256:
        raise RuntimeError("EXP005-P0 audit artifact SHA-256 mismatch")
    audit = _read_json(audit_path)
    if audit.get("status") != "DATA_READY_SANDBOX":
        raise RuntimeError("EXP005-P0 parent is not DATA_READY_SANDBOX")
    if audit.get("configuration_sha256") != PARENT_AUDIT_CONFIG_SHA256:
        raise RuntimeError("EXP005-P0 audit configuration mismatch")
    if audit.get("sealed_august_opened") is not False:
        raise RuntimeError("parent audit reports sealed August access")

    acquisition = _read_json(acquisition_path)
    if acquisition.get("file_count") != 14 or acquisition.get("sealed_august_opened") is not False:
        raise RuntimeError("invalid frozen EXP005 acquisition manifest")

    expected: dict[tuple[str, date], str] = {}
    for item in acquisition.get("files", []):
        symbol = str(item["symbol"])
        day = date.fromisoformat(str(item["day"]))
        if symbol not in SYMBOLS or day not in DAYS:
            raise RuntimeError("acquisition manifest escapes frozen symbol/day scope")
        key = (symbol, day)
        if key in expected:
            raise RuntimeError("duplicate acquisition manifest symbol-day")
        expected[key] = str(item["sha256"])
    if len(expected) != 14:
        raise RuntimeError("acquisition manifest must contain exactly 14 unique symbol-days")

    for symbol in SYMBOLS:
        for day in DAYS:
            path = DatasetRequest(symbol, day).output_path(raw_root)
            if not path.exists():
                raise FileNotFoundError(path)
            if sha256_file(path) != expected[(symbol, day)]:
                raise RuntimeError(f"raw derivatives SHA-256 mismatch: {symbol} {day}")
    return audit, acquisition, expected


def provenance_payload(
    feature_manifest: dict[str, Any],
    acquisition_manifest: dict[str, Any],
    raw_hashes: dict[tuple[str, date], str],
) -> dict[str, Any]:
    return {
        "parent_audit_artifact_sha256": PARENT_AUDIT_SHA256,
        "parent_audit_configuration_sha256": PARENT_AUDIT_CONFIG_SHA256,
        "feature_input_manifest": feature_manifest,
        "derivatives_acquisition_manifest": acquisition_manifest,
        "verified_raw_derivatives_sha256": {
            f"{symbol}|{day.isoformat()}": raw_hashes[(symbol, day)]
            for symbol in SYMBOLS
            for day in DAYS
        },
    }


def run(
    feature_dir: Path,
    raw_root: Path,
    output: Path,
    workspace: Path,
    frozen_commit: str,
) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)
    partial = assert_fresh_output(output)
    raw_root = raw_root if raw_root.is_absolute() else workspace / raw_root

    parent_audit, acquisition, raw_hashes = verify_parent_inputs(workspace, raw_root)
    phase_manifest = input_manifest(feature_dir, workspace)

    data: dict[tuple[str, date], P1DayDataset] = {}
    for symbol in SYMBOLS:
        for day in DAYS:
            phase = _load_day(feature_path(feature_dir, symbol, day), day)
            raw_path = DatasetRequest(symbol, day).output_path(raw_root)
            derivative_state = load_derivative_day(raw_path, symbol, day)
            if derivative_state.raw_sha256 != raw_hashes[(symbol, day)]:
                raise RuntimeError("raw derivative hash changed between verification and load")
            data[(symbol, day)] = build_day_dataset(symbol, phase, derivative_state)

    records: list[dict[str, Any]] = []
    fold_counts: list[dict[str, Any]] = []
    common_support_exact = True

    for outer_day in OUTER_DAYS:
        train_calendar = training_days(outer_day)
        for symbol in SYMBOLS:
            train = [data[(symbol, day)] for day in train_calendar]
            outer = data[(symbol, outer_day)]

            XR, yR, mag = concat_common(train, "R")
            XRD, yRD, mag_rd = concat_common(train, "RD")
            XD, yD, _ = concat_common(train, "D")
            XOI, yOI, _ = concat_common(train, "ROI")
            XP, yP, _ = concat_common(train, "RPREMIUM")
            XF, yF, _ = concat_common(train, "RFUNDING")
            XV, yV, _ = concat_common(train, "VOL")
            XPERM, yPERM = concat_rd_time_permuted(train)

            labels_equal = all(
                np.array_equal(yR, y)
                for y in (yRD, yD, yOI, yP, yF, yV, yPERM)
            )
            common_support_exact &= labels_equal and len(XR) == len(XRD) == len(XPERM)
            if not common_support_exact:
                raise RuntimeError("common training support invariant failed")
            if not np.array_equal(mag, mag_rd):
                raise RuntimeError("common-support future magnitude mismatch")

            model_r = FixedLogistic().fit(XR, yR)
            model_rd = FixedLogistic().fit(XRD, yR)
            model_d = FixedLogistic().fit(XD, yR)
            model_oi = FixedLogistic().fit(XOI, yR)
            model_premium = FixedLogistic().fit(XP, yR)
            model_funding = FixedLogistic().fit(XF, yR)
            model_vol = FixedLogistic().fit(XV, yR)
            model_perm = FixedLogistic().fit(XPERM, yR)
            model_canary = FixedLogistic().fit(np.column_stack((XR, mag)), yR)

            m = outer.valid_common
            XR_o = _matrix(outer, "R", m)
            XRD_o = _matrix(outer, "RD", m)
            XD_o = _matrix(outer, "D", m)
            XOI_o = _matrix(outer, "ROI", m)
            XP_o = _matrix(outer, "RPREMIUM", m)
            XF_o = _matrix(outer, "RFUNDING", m)
            XV_o = _matrix(outer, "VOL", m)
            D_perm_o = permute_complete_d_vectors(outer, m)
            XPERM_o = np.column_stack((XR_o, D_perm_o))

            n_outer = int(np.sum(m))
            common_support_exact &= all(
                len(x) == n_outer
                for x in (XR_o, XRD_o, XD_o, XOI_o, XP_o, XF_o, XV_o, XPERM_o)
            )
            if not common_support_exact:
                raise RuntimeError("common outer support invariant failed")

            p_r = model_r.predict_proba(XR_o)
            p_rd = model_rd.predict_proba(XRD_o)
            p_d = model_d.predict_proba(XD_o)
            p_oi = model_oi.predict_proba(XOI_o)
            p_premium = model_premium.predict_proba(XP_o)
            p_funding = model_funding.predict_proba(XF_o)
            p_vol = model_vol.predict_proba(XV_o)
            p_perm = model_perm.predict_proba(XPERM_o)
            p_canary = model_canary.predict_proba(
                np.column_stack((XR_o, outer.oracle_gross_bps[m]))
            )

            signed_positions = [
                len(R_FEATURE_NAMES) + D_FEATURE_NAMES.index(name) for name in SIGNED_D_FEATURES
            ]
            sign_X = XRD_o.copy()
            sign_X[:, signed_positions] *= -1.0
            p_sign = model_rd.predict_proba(sign_X)

            idx = np.flatnonzero(m)
            fold_counts.append(
                {
                    "outer_day": outer_day.isoformat(),
                    "symbol": symbol,
                    "training_days": [d.isoformat() for d in train_calendar],
                    "common_train_n": int(len(yR)),
                    "common_outer_n": n_outer,
                    "R_train_n": int(len(XR)),
                    "RD_train_n": int(len(XRD)),
                    "RD_permuted_train_n": int(len(XPERM)),
                }
            )
            for j, source_idx in enumerate(idx.tolist()):
                records.append(
                    {
                        "outer_day": outer_day.isoformat(),
                        "symbol": symbol,
                        "timestamp_us": int(outer.timestamp_us[source_idx]),
                        "label": int(outer.y[source_idx]),
                        "oracle_gross_bps": float(outer.oracle_gross_bps[source_idx]),
                        "nonoverlap_10m": bool(outer.nonoverlap_10m[source_idx]),
                        "p_R": float(p_r[j]),
                        "p_RD": float(p_rd[j]),
                        "p_D": float(p_d[j]),
                        "p_R_OI": float(p_oi[j]),
                        "p_R_PREMIUM": float(p_premium[j]),
                        "p_R_FUNDING": float(p_funding[j]),
                        "p_VOL": float(p_vol[j]),
                        "p_RD_D_TIME_PERMUTED": float(p_perm[j]),
                        "p_CANARY_R": float(p_canary[j]),
                        "p_SIGN_D": float(p_sign[j]),
                    }
                )

    metric_keys = {
        "R": "p_R",
        "RD": "p_RD",
        "D": "p_D",
        "R_OI": "p_R_OI",
        "R_PREMIUM": "p_R_PREMIUM",
        "R_FUNDING": "p_R_FUNDING",
        "VOL": "p_VOL",
        "RD_D_TIME_PERMUTED": "p_RD_D_TIME_PERMUTED",
        "CANARY_R": "p_CANARY_R",
        "SIGN_D": "p_SIGN_D",
    }
    M = {name: exp004_metrics(records, key) for name, key in metric_keys.items()}

    invariants = {
        "parent_audit_sha256_verified": True,
        "parent_audit_data_ready": parent_audit.get("status") == "DATA_READY_SANDBOX",
        "all_14_raw_derivatives_hashes_verified": len(raw_hashes) == 14,
        "sealed_august_not_accessed": True,
        "availability_clock_local_timestamp_only": Config().availability_clock == "local_timestamp only",
        "max_staleness_is_30_seconds": MAX_STALENESS_S == 30,
        "predicted_funding_rate_excluded": "predicted_funding_rate" not in D_FEATURE_NAMES,
        "r_rd_common_training_and_outer_support_exact": common_support_exact,
        "outer_folds_chronological": all(all(d < o for d in training_days(o)) for o in OUTER_DAYS),
    }
    gates = primary_gates(M, invariants)
    if not all(invariants.values()):
        status = "INVALID"
    elif all(gates.values()):
        status = "PREDICTABLE_INCREMENTAL_DERIVATIVES_SANDBOX"
    else:
        status = "FAIL_DERIVATIVES_NO_INCREMENTAL_TIMING_INFORMATION"

    rp = M["R"]["pooled"]
    dp = M["RD"]["pooled"]
    perm = M["RD_D_TIME_PERMUTED"]["pooled"]
    canary = M["CANARY_R"]["pooled"]
    sign = M["SIGN_D"]["pooled"]
    deltas = {
        "RD_auc_minus_R_auc": _metric_delta(dp["roc_auc"], rp["roc_auc"]),
        "RD_average_precision_minus_R": _metric_delta(dp["average_precision"], rp["average_precision"]),
        "RD_top_decile_precision_minus_R": _metric_delta(dp["top_decile_precision"], rp["top_decile_precision"]),
        "R_log_loss_minus_RD_log_loss": _metric_delta(rp["log_loss"], dp["log_loss"]),
        "RD_auc_minus_D_time_permuted_auc": _metric_delta(dp["roc_auc"], perm["roc_auc"]),
        "CANARY_R_auc_minus_R_auc": _metric_delta(canary["roc_auc"], rp["roc_auc"]),
        "SIGN_D_auc_minus_RD_auc": _metric_delta(sign["roc_auc"], dp["roc_auc"]),
    }

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
        "provenance": provenance_payload(phase_manifest, acquisition, raw_hashes),
        "fold_train_counts": fold_counts,
        "metrics": M,
        "gates": gates,
        "invariants": invariants,
        "diagnostic_deltas": deltas,
        "oos_prediction_records_sha256": canonical_sha256(records),
        "oos_prediction_records": records,
        "interpretation": (
            "Incremental opportunity-timing predictability only. No direction, executable PnL, "
            "prospective validation, August access, or live-money readiness."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    partial.replace(output)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Frozen CODEX-EXP-005-P1 incremental derivatives test")
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args(argv)
    result = run(args.feature_dir, args.raw_root, args.output, args.workspace, args.frozen_commit)
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "status": result["status"],
                "R_pooled_auc": result["metrics"]["R"]["pooled"]["roc_auc"],
                "RD_pooled_auc": result["metrics"]["RD"]["pooled"]["roc_auc"],
                "RD_auc_minus_R_auc": result["diagnostic_deltas"]["RD_auc_minus_R_auc"],
                "RD_auc_minus_D_time_permuted_auc": result["diagnostic_deltas"]["RD_auc_minus_D_time_permuted_auc"],
                "all_primary_gates_pass": all(result["gates"].values()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

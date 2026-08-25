from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

from .codex_exp004_headroom import (
    DAYS,
    SYMBOLS,
    assert_fresh_output,
    assert_frozen_workspace,
    executable_fixed_horizon,
    feature_path,
    input_manifest,
)
from .codex_research import canonical_sha256
from .v23_phase0dl_score import BLOCKS, DayData, _load_day

EXPERIMENT_ID = "CODEX-EXP-004-P1"
GRID_US = 250_000
DECISION_STEP_S = 60
DECISION_STEP_ROWS = DECISION_STEP_S * 1_000_000 // GRID_US
HORIZON_S = 600
HORIZON_ROWS = HORIZON_S * 1_000_000 // GRID_US
ENTRY_STEPS = 1
LABEL_THRESHOLD_BPS = 24.0
SEED = 20260825

OUTER_DAYS = DAYS[2:]
FOLDS = tuple(
    (outer.isoformat(), tuple(day.isoformat() for day in DAYS if day < outer))
    for outer in OUTER_DAYS
)

RETURN_LOOKBACK_MIN = (1, 3, 5, 10, 30)
RV_WINDOWS_MIN = (5, 15, 30)
SPREAD_MEAN_MIN = (1, 5)
RANGE_WINDOWS_MIN = (5, 15, 30)

R_FEATURE_NAMES = (
    *(f"ret_{m}m_bps" for m in RETURN_LOOKBACK_MIN),
    *(f"abs_ret_{m}m_bps" for m in RETURN_LOOKBACK_MIN),
    *(f"rv_{m}m_bps" for m in RV_WINDOWS_MIN),
    "spread_bps",
    *(f"spread_mean_{m}m_bps" for m in SPREAD_MEAN_MIN),
    *(f"range_{m}m_bps" for m in RANGE_WINDOWS_MIN),
    *(f"range_position_{m}m" for m in RANGE_WINDOWS_MIN),
)

RL2_CURRENT_NAMES = (
    "microprice_minus_mid_bps",
    "obi_l1",
    "obi_l5",
    "obi_l10",
    "ofi_l1_1s",
    "ofi_l1_3s",
    "mlofi_l5_1s",
    "mlofi_l5_3s",
    "trade_qty_imbalance_1s",
    "trade_qty_imbalance_3s",
    "trade_count_imbalance_1s",
    "trade_count_imbalance_3s",
    "log_bid_depth_l5",
    "log_ask_depth_l5",
)
RL2_ROLL_NAMES = (
    "obi_l5",
    "ofi_l1_1s",
    "trade_qty_imbalance_1s",
)
RL2_EXTRA_NAMES = (
    *RL2_CURRENT_NAMES,
    *(name for base in RL2_ROLL_NAMES for name in (f"{base}_mean_1m", f"{base}_std_1m")),
)
RL2_FEATURE_NAMES = R_FEATURE_NAMES + RL2_EXTRA_NAMES

SIGNED_R_FEATURES = tuple(f"ret_{m}m_bps" for m in RETURN_LOOKBACK_MIN)

PRIMARY_GATES = {
    "pooled_auc_min": 0.60,
    "pooled_ap_prevalence_multiple_min": 1.30,
    "pooled_brier_skill_min_exclusive": 0.0,
    "pooled_top_decile_lift_min": 1.50,
    "folds_auc_gt_055_min": 4,
    "folds_top_decile_lift_gt_1_min": 4,
    "symbol_auc_min": 0.57,
    "symbol_top_decile_lift_min": 1.25,
    "nonoverlap_pooled_auc_min": 0.57,
    "nonoverlap_top_decile_lift_min": 1.25,
}
RL2_INCREMENTAL_GATES = {
    "auc_delta_min": 0.01,
    "average_precision_delta_min": 0.01,
    "top_decile_precision_not_lower": True,
}
DIAGNOSTIC_GATES = {
    "real_auc_minus_time_placebo_min": 0.03,
    "future_canary_auc_minus_real_min": 0.10,
}


@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbols: tuple[str, ...] = SYMBOLS
    days: tuple[str, ...] = tuple(day.isoformat() for day in DAYS)
    outer_days: tuple[str, ...] = tuple(day.isoformat() for day in OUTER_DAYS)
    folds: tuple[tuple[str, tuple[str, ...]], ...] = FOLDS
    decision_step_s: int = DECISION_STEP_S
    entry_steps: int = ENTRY_STEPS
    horizon_s: int = HORIZON_S
    label_threshold_bps: float = LABEL_THRESHOLD_BPS
    r_features: tuple[str, ...] = R_FEATURE_NAMES
    rl2_features: tuple[str, ...] = RL2_FEATURE_NAMES
    signed_r_features: tuple[str, ...] = SIGNED_R_FEATURES
    model: tuple[tuple[str, Any], ...] = (
        ("standard_scaler", True),
        ("logistic_c", 1.0),
        ("penalty", "l2"),
        ("solver", "lbfgs"),
        ("class_weight", None),
        ("max_iter", 1000),
        ("seed", SEED),
    )
    primary_gates: tuple[tuple[str, float | int], ...] = tuple(PRIMARY_GATES.items())
    rl2_incremental_gates: tuple[tuple[str, float | bool], ...] = tuple(RL2_INCREMENTAL_GATES.items())
    diagnostic_gates: tuple[tuple[str, float], ...] = tuple(DIAGNOSTIC_GATES.items())


@dataclass
class DayDataset:
    symbol: str
    day: date
    timestamp_us: np.ndarray
    X_R: np.ndarray
    X_RL2: np.ndarray
    y: np.ndarray
    oracle_gross_bps: np.ndarray
    valid_R: np.ndarray
    valid_RL2: np.ndarray
    nonoverlap_10m: np.ndarray


class FixedLogistic:
    def __init__(self) -> None:
        self.scaler = StandardScaler()
        self.model = LogisticRegression(
            C=1.0,
            penalty="l2",
            solver="lbfgs",
            class_weight=None,
            max_iter=1000,
            random_state=SEED,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> "FixedLogistic":
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.int8)
        if X.ndim != 2 or len(X) != len(y) or len(X) < 2:
            raise RuntimeError("invalid training matrix")
        if np.unique(y).size != 2:
            raise RuntimeError("training labels contain only one class")
        z = self.scaler.fit_transform(X)
        self.model.fit(z, y)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        return self.model.predict_proba(self.scaler.transform(X))[:, 1]


def _l2_positions() -> dict[str, int]:
    return {name: i for i, name in enumerate(BLOCKS["L2"])}


def _spread_bps(day: DayData) -> np.ndarray:
    out = np.full(len(day.mid), np.nan, dtype=np.float64)
    ok = (
        day.book_valid
        & np.isfinite(day.bid)
        & np.isfinite(day.ask)
        & np.isfinite(day.mid)
        & (day.bid > 0)
        & (day.ask > 0)
        & (day.mid > 0)
    )
    out[ok] = 10_000.0 * (day.ask[ok] - day.bid[ok]) / day.mid[ok]
    return out


def _window_is_valid(mask: np.ndarray, start: int, end: int) -> bool:
    return start >= 0 and end < len(mask) and bool(np.all(mask[start : end + 1]))


def _rv_from_minute_mids(mid: np.ndarray, current: int, window_min: int) -> float:
    step = DECISION_STEP_ROWS
    idx = current - np.arange(window_min, -1, -1, dtype=np.int64) * step
    values = mid[idx]
    returns = np.diff(np.log(values))
    return float(10_000.0 * np.sqrt(np.sum(returns * returns)))


def _range_features(mid: np.ndarray, current: int, window_min: int) -> tuple[float, float]:
    rows = window_min * DECISION_STEP_ROWS
    values = mid[current - rows : current + 1]
    lo = float(np.min(values))
    hi = float(np.max(values))
    if lo <= 0 or not np.isfinite(lo) or not np.isfinite(hi):
        raise RuntimeError("invalid trailing price range")
    range_bps = float(10_000.0 * np.log(hi / lo))
    if hi == lo:
        position = 0.5
    else:
        position = float((mid[current] - lo) / (hi - lo))
    return range_bps, position


def _build_r_features(day: DayData, current: int, spread: np.ndarray) -> np.ndarray | None:
    max_rows = max(RETURN_LOOKBACK_MIN + RV_WINDOWS_MIN + SPREAD_MEAN_MIN + RANGE_WINDOWS_MIN) * DECISION_STEP_ROWS
    start = current - max_rows
    if not _window_is_valid(day.book_valid, start, current):
        return None
    if not np.all(np.isfinite(day.mid[start : current + 1])) or np.any(day.mid[start : current + 1] <= 0):
        return None
    if not np.all(np.isfinite(spread[current - max(SPREAD_MEAN_MIN) * DECISION_STEP_ROWS : current + 1])):
        return None

    values: list[float] = []
    returns: list[float] = []
    for minutes in RETURN_LOOKBACK_MIN:
        lag = current - minutes * DECISION_STEP_ROWS
        ret = float(10_000.0 * np.log(day.mid[current] / day.mid[lag]))
        returns.append(ret)
    values.extend(returns)
    values.extend(abs(value) for value in returns)

    for minutes in RV_WINDOWS_MIN:
        values.append(_rv_from_minute_mids(day.mid, current, minutes))

    values.append(float(spread[current]))
    for minutes in SPREAD_MEAN_MIN:
        rows = minutes * DECISION_STEP_ROWS
        values.append(float(np.mean(spread[current - rows : current + 1])))

    ranges: list[float] = []
    positions: list[float] = []
    for minutes in RANGE_WINDOWS_MIN:
        range_bps, position = _range_features(day.mid, current, minutes)
        ranges.append(range_bps)
        positions.append(position)
    values.extend(ranges)
    values.extend(positions)

    result = np.asarray(values, dtype=np.float64)
    if len(result) != len(R_FEATURE_NAMES) or not np.all(np.isfinite(result)):
        return None
    return result


def _build_rl2_extras(day: DayData, current: int, positions: dict[str, int]) -> np.ndarray | None:
    one_minute = DECISION_STEP_ROWS
    start = current - one_minute
    if start < 0 or not bool(np.all(day.valid["L2"][start : current + 1])):
        return None
    X = day.X["L2"]
    required = tuple(dict.fromkeys(RL2_CURRENT_NAMES + RL2_ROLL_NAMES))
    cols = [positions[name] for name in required]
    if not np.all(np.isfinite(X[start : current + 1, cols])):
        return None

    values = [float(X[current, positions[name]]) for name in RL2_CURRENT_NAMES]
    for name in RL2_ROLL_NAMES:
        series = X[start : current + 1, positions[name]].astype(np.float64, copy=False)
        values.extend((float(np.mean(series)), float(np.std(series, ddof=0))))
    result = np.asarray(values, dtype=np.float64)
    if len(result) != len(RL2_EXTRA_NAMES) or not np.all(np.isfinite(result)):
        return None
    return result


def build_day_dataset(symbol: str, day: DayData) -> DayDataset:
    if symbol not in SYMBOLS:
        raise ValueError("symbol outside frozen P1")
    if day.day not in DAYS:
        raise ValueError("day outside frozen P1")
    decisions = np.arange(0, len(day.ts), DECISION_STEP_ROWS, dtype=np.int64)
    outcomes = executable_fixed_horizon(day, decisions, HORIZON_S)
    label_valid = outcomes["valid"] & np.isfinite(outcomes["oracle_gross_bps"])
    oracle = outcomes["oracle_gross_bps"].astype(np.float64, copy=False)
    y = (oracle >= LABEL_THRESHOLD_BPS).astype(np.int8)

    spread = _spread_bps(day)
    positions = _l2_positions()
    X_R = np.full((len(decisions), len(R_FEATURE_NAMES)), np.nan, dtype=np.float64)
    X_RL2 = np.full((len(decisions), len(RL2_FEATURE_NAMES)), np.nan, dtype=np.float64)
    valid_R = np.zeros(len(decisions), dtype=bool)
    valid_RL2 = np.zeros(len(decisions), dtype=bool)

    for j, current in enumerate(decisions.tolist()):
        if not label_valid[j]:
            continue
        r = _build_r_features(day, current, spread)
        if r is None:
            continue
        X_R[j] = r
        valid_R[j] = True
        extras = _build_rl2_extras(day, current, positions)
        if extras is None:
            continue
        X_RL2[j] = np.concatenate((r, extras))
        valid_RL2[j] = True

    minute_number = decisions // DECISION_STEP_ROWS
    nonoverlap = (minute_number % (HORIZON_S // DECISION_STEP_S)) == 0
    return DayDataset(
        symbol=symbol,
        day=day.day,
        timestamp_us=day.ts[decisions].astype(np.int64),
        X_R=X_R,
        X_RL2=X_RL2,
        y=y,
        oracle_gross_bps=oracle,
        valid_R=valid_R,
        valid_RL2=valid_RL2,
        nonoverlap_10m=nonoverlap,
    )


def _concat_days(datasets: list[DayDataset], track: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if track not in {"R", "RL2"}:
        raise ValueError("unknown track")
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    mags: list[np.ndarray] = []
    for dataset in datasets:
        valid = dataset.valid_R if track == "R" else dataset.valid_RL2
        X = dataset.X_R if track == "R" else dataset.X_RL2
        xs.append(X[valid])
        ys.append(dataset.y[valid])
        mags.append(dataset.oracle_gross_bps[valid])
    if not xs:
        width = len(R_FEATURE_NAMES) if track == "R" else len(RL2_FEATURE_NAMES)
        return np.empty((0, width)), np.empty(0, dtype=np.int8), np.empty(0)
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(mags)


def _stable_day_seed(symbol: str, day: date) -> int:
    raw = f"{SEED}|{symbol}|{day.isoformat()}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") % (2**32)


def _permuted_train_labels(datasets: list[DayDataset], track: str) -> np.ndarray:
    parts: list[np.ndarray] = []
    for dataset in datasets:
        valid = dataset.valid_R if track == "R" else dataset.valid_RL2
        labels = dataset.y[valid].copy()
        rng = np.random.default_rng(_stable_day_seed(dataset.symbol, dataset.day))
        parts.append(labels[rng.permutation(len(labels))])
    return np.concatenate(parts) if parts else np.empty(0, dtype=np.int8)


def _calibration_diagnostic(y: np.ndarray, p: np.ndarray) -> dict[str, float | None]:
    if len(y) < 10 or np.unique(y).size != 2:
        return {"intercept": None, "slope": None}
    clipped = np.clip(p, 1e-6, 1 - 1e-6)
    logit = np.log(clipped / (1.0 - clipped)).reshape(-1, 1)
    model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
    model.fit(logit, y)
    return {"intercept": float(model.intercept_[0]), "slope": float(model.coef_[0, 0])}


def _top_fraction(y: np.ndarray, p: np.ndarray, fraction: float) -> tuple[float | None, float | None]:
    if len(y) == 0:
        return None, None
    prevalence = float(np.mean(y))
    k = max(1, int(math.ceil(len(y) * fraction)))
    order = np.argsort(-p, kind="mergesort")[:k]
    precision = float(np.mean(y[order]))
    lift = float(precision / prevalence) if prevalence > 0 else None
    return precision, lift


def score_probabilities(y: np.ndarray, p: np.ndarray) -> dict[str, Any]:
    y = np.asarray(y, dtype=np.int8)
    p = np.asarray(p, dtype=np.float64)
    finite = np.isfinite(p)
    y = y[finite]
    p = p[finite]
    prevalence = float(np.mean(y)) if len(y) else None
    if len(y) == 0 or np.unique(y).size != 2:
        return {
            "n": int(len(y)),
            "prevalence": prevalence,
            "roc_auc": None,
            "average_precision": None,
            "average_precision_over_prevalence": None,
            "brier_score": None,
            "brier_skill_score": None,
            "log_loss": None,
            "top_decile_precision": None,
            "top_decile_lift": None,
            "top_quintile_precision": None,
            "top_quintile_lift": None,
            "calibration": {"intercept": None, "slope": None},
        }
    auc = float(roc_auc_score(y, p))
    ap = float(average_precision_score(y, p))
    brier = float(brier_score_loss(y, p))
    baseline_brier = float(np.mean((y - prevalence) ** 2))
    brier_skill = float(1.0 - brier / baseline_brier) if baseline_brier > 0 else None
    dec_precision, dec_lift = _top_fraction(y, p, 0.10)
    quint_precision, quint_lift = _top_fraction(y, p, 0.20)
    return {
        "n": int(len(y)),
        "prevalence": prevalence,
        "roc_auc": auc,
        "average_precision": ap,
        "average_precision_over_prevalence": float(ap / prevalence) if prevalence > 0 else None,
        "brier_score": brier,
        "brier_skill_score": brier_skill,
        "log_loss": float(log_loss(y, np.clip(p, 1e-12, 1 - 1e-12))),
        "top_decile_precision": dec_precision,
        "top_decile_lift": dec_lift,
        "top_quintile_precision": quint_precision,
        "top_quintile_lift": quint_lift,
        "calibration": _calibration_diagnostic(y, p),
    }


def _variant_metrics(records: list[dict[str, Any]], probability_key: str) -> dict[str, Any]:
    def score(subset: list[dict[str, Any]]) -> dict[str, Any]:
        return score_probabilities(
            np.asarray([row["label"] for row in subset], dtype=np.int8),
            np.asarray([row[probability_key] for row in subset], dtype=np.float64),
        )

    pooled = score(records)
    by_symbol = {symbol: score([row for row in records if row["symbol"] == symbol]) for symbol in SYMBOLS}
    by_fold = {outer.isoformat(): score([row for row in records if row["outer_day"] == outer.isoformat()]) for outer in OUTER_DAYS}
    nonoverlap = [row for row in records if row["nonoverlap_10m"]]
    return {
        "pooled": pooled,
        "by_symbol": by_symbol,
        "by_fold": by_fold,
        "nonoverlap_pooled": score(nonoverlap),
        "nonoverlap_by_symbol": {
            symbol: score([row for row in nonoverlap if row["symbol"] == symbol])
            for symbol in SYMBOLS
        },
    }


def _absolute_gates(metrics: dict[str, Any]) -> dict[str, bool]:
    pooled = metrics["pooled"]
    folds = metrics["by_fold"]
    symbols = metrics["by_symbol"]
    nonoverlap = metrics["nonoverlap_pooled"]

    def ge(value: float | None, threshold: float) -> bool:
        return value is not None and value >= threshold

    def gt(value: float | None, threshold: float) -> bool:
        return value is not None and value > threshold

    gates = {
        "pooled_auc_at_least_0_60": ge(pooled["roc_auc"], PRIMARY_GATES["pooled_auc_min"]),
        "pooled_ap_at_least_1_30x_prevalence": ge(
            pooled["average_precision_over_prevalence"],
            PRIMARY_GATES["pooled_ap_prevalence_multiple_min"],
        ),
        "pooled_brier_skill_positive": gt(
            pooled["brier_skill_score"], PRIMARY_GATES["pooled_brier_skill_min_exclusive"]
        ),
        "pooled_top_decile_lift_at_least_1_50": ge(
            pooled["top_decile_lift"], PRIMARY_GATES["pooled_top_decile_lift_min"]
        ),
        "at_least_4_of_5_folds_auc_gt_0_55": sum(
            gt(value["roc_auc"], 0.55) for value in folds.values()
        ) >= PRIMARY_GATES["folds_auc_gt_055_min"],
        "at_least_4_of_5_folds_top_decile_lift_gt_1": sum(
            gt(value["top_decile_lift"], 1.0) for value in folds.values()
        ) >= PRIMARY_GATES["folds_top_decile_lift_gt_1_min"],
        "both_symbols_auc_at_least_0_57": all(
            ge(symbols[symbol]["roc_auc"], PRIMARY_GATES["symbol_auc_min"])
            for symbol in SYMBOLS
        ),
        "both_symbols_top_decile_lift_at_least_1_25": all(
            ge(
                symbols[symbol]["top_decile_lift"],
                PRIMARY_GATES["symbol_top_decile_lift_min"],
            )
            for symbol in SYMBOLS
        ),
        "nonoverlap_pooled_auc_at_least_0_57": ge(
            nonoverlap["roc_auc"], PRIMARY_GATES["nonoverlap_pooled_auc_min"]
        ),
        "nonoverlap_top_decile_lift_at_least_1_25": ge(
            nonoverlap["top_decile_lift"],
            PRIMARY_GATES["nonoverlap_top_decile_lift_min"],
        ),
    }
    return gates


def _fit_real_and_diagnostics(
    train_days: list[DayDataset], outer: DayDataset
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    Xr_train, yr_train, mag_train = _concat_days(train_days, "R")
    Xrl2_train, yrl2_train, _ = _concat_days(train_days, "RL2")

    r_outer_mask = outer.valid_R
    rl2_outer_mask = outer.valid_RL2
    Xr_outer = outer.X_R[r_outer_mask]
    Xrl2_outer = outer.X_RL2[rl2_outer_mask]

    r_model = FixedLogistic().fit(Xr_train, yr_train)
    rl2_model = FixedLogistic().fit(Xrl2_train, yrl2_train)

    vol_idx = R_FEATURE_NAMES.index("rv_30m_bps")
    vol_model = FixedLogistic().fit(Xr_train[:, [vol_idx]], yr_train)

    permuted = _permuted_train_labels(train_days, "R")
    placebo_model = FixedLogistic().fit(Xr_train, permuted)

    canary_model = FixedLogistic().fit(
        np.column_stack((Xr_train, mag_train)), yr_train
    )

    real_r = r_model.predict_proba(Xr_outer)
    real_rl2 = rl2_model.predict_proba(Xrl2_outer)
    vol = vol_model.predict_proba(Xr_outer[:, [vol_idx]])
    placebo = placebo_model.predict_proba(Xr_outer)
    canary = canary_model.predict_proba(
        np.column_stack((Xr_outer, outer.oracle_gross_bps[r_outer_mask]))
    )

    signed_idx = [R_FEATURE_NAMES.index(name) for name in SIGNED_R_FEATURES]
    sign_X = Xr_outer.copy()
    sign_X[:, signed_idx] *= -1.0
    sign = r_model.predict_proba(sign_X)

    probabilities = {
        "R": real_r,
        "RL2": real_rl2,
        "VOL": vol,
        "PLACEBO_R": placebo,
        "CANARY_R": canary,
        "SIGN_R": sign,
    }
    return probabilities, rl2_outer_mask


def run(feature_dir: Path, output: Path, workspace: Path, frozen_commit: str) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)
    partial = assert_fresh_output(output)
    manifest = input_manifest(feature_dir, workspace)

    datasets: dict[tuple[str, date], DayDataset] = {}
    for symbol in SYMBOLS:
        for day in DAYS:
            raw = _load_day(feature_path(feature_dir, symbol, day), day)
            datasets[(symbol, day)] = build_day_dataset(symbol, raw)

    records: list[dict[str, Any]] = []
    fold_train_counts: list[dict[str, Any]] = []

    for outer_day in OUTER_DAYS:
        train_calendar = [day for day in DAYS if day < outer_day]
        for symbol in SYMBOLS:
            train_days = [datasets[(symbol, day)] for day in train_calendar]
            outer = datasets[(symbol, outer_day)]
            probabilities, rl2_outer_mask = _fit_real_and_diagnostics(train_days, outer)
            r_mask = outer.valid_R
            r_indices = np.flatnonzero(r_mask)
            rl2_indices = np.flatnonzero(rl2_outer_mask)
            rl2_lookup = {int(idx): j for j, idx in enumerate(rl2_indices.tolist())}

            Xr_train, yr_train, _ = _concat_days(train_days, "R")
            Xrl2_train, yrl2_train, _ = _concat_days(train_days, "RL2")
            fold_train_counts.append(
                {
                    "outer_day": outer_day.isoformat(),
                    "symbol": symbol,
                    "train_days": [day.isoformat() for day in train_calendar],
                    "R_train_n": int(len(yr_train)),
                    "R_train_prevalence": float(np.mean(yr_train)),
                    "RL2_train_n": int(len(yrl2_train)),
                    "RL2_train_prevalence": float(np.mean(yrl2_train)),
                    "R_outer_n": int(np.sum(r_mask)),
                    "RL2_outer_n": int(np.sum(rl2_outer_mask)),
                }
            )

            for j, idx in enumerate(r_indices.tolist()):
                row = {
                    "outer_day": outer_day.isoformat(),
                    "symbol": symbol,
                    "timestamp_us": int(outer.timestamp_us[idx]),
                    "label": int(outer.y[idx]),
                    "oracle_gross_bps": float(outer.oracle_gross_bps[idx]),
                    "nonoverlap_10m": bool(outer.nonoverlap_10m[idx]),
                    "p_R": float(probabilities["R"][j]),
                    "p_VOL": float(probabilities["VOL"][j]),
                    "p_PLACEBO_R": float(probabilities["PLACEBO_R"][j]),
                    "p_CANARY_R": float(probabilities["CANARY_R"][j]),
                    "p_SIGN_R": float(probabilities["SIGN_R"][j]),
                    "p_RL2": None,
                }
                if idx in rl2_lookup:
                    row["p_RL2"] = float(probabilities["RL2"][rl2_lookup[idx]])
                records.append(row)

    variants = {
        "R": "p_R",
        "VOL": "p_VOL",
        "PLACEBO_R": "p_PLACEBO_R",
        "CANARY_R": "p_CANARY_R",
        "SIGN_R": "p_SIGN_R",
    }
    metrics = {name: _variant_metrics(records, key) for name, key in variants.items()}
    rl2_records = [row for row in records if row["p_RL2"] is not None]
    metrics["RL2"] = _variant_metrics(rl2_records, "p_RL2")

    r_gates = _absolute_gates(metrics["R"])
    rl2_gates = _absolute_gates(metrics["RL2"])

    r_pool = metrics["R"]["pooled"]
    rl2_pool = metrics["RL2"]["pooled"]
    placebo_pool = metrics["PLACEBO_R"]["pooled"]
    canary_pool = metrics["CANARY_R"]["pooled"]
    sign_pool = metrics["SIGN_R"]["pooled"]

    rl2_incremental = {
        "auc_delta_at_least_0_01": (
            rl2_pool["roc_auc"] is not None
            and r_pool["roc_auc"] is not None
            and rl2_pool["roc_auc"] - r_pool["roc_auc"] >= RL2_INCREMENTAL_GATES["auc_delta_min"]
        ),
        "average_precision_delta_at_least_0_01": (
            rl2_pool["average_precision"] is not None
            and r_pool["average_precision"] is not None
            and rl2_pool["average_precision"] - r_pool["average_precision"]
            >= RL2_INCREMENTAL_GATES["average_precision_delta_min"]
        ),
        "top_decile_precision_not_lower": (
            rl2_pool["top_decile_precision"] is not None
            and r_pool["top_decile_precision"] is not None
            and rl2_pool["top_decile_precision"] >= r_pool["top_decile_precision"]
        ),
    }

    time_delta = (
        float(r_pool["roc_auc"] - placebo_pool["roc_auc"])
        if r_pool["roc_auc"] is not None and placebo_pool["roc_auc"] is not None
        else None
    )
    canary_delta = (
        float(canary_pool["roc_auc"] - r_pool["roc_auc"])
        if canary_pool["roc_auc"] is not None and r_pool["roc_auc"] is not None
        else None
    )
    sign_improves_all = all(
        sign_pool[key] is not None
        and r_pool[key] is not None
        and sign_pool[key] > r_pool[key]
        for key in ("roc_auc", "average_precision", "top_decile_lift")
    )
    diagnostic_gates = {
        "real_auc_exceeds_time_placebo_by_at_least_0_03": (
            time_delta is not None
            and time_delta >= DIAGNOSTIC_GATES["real_auc_minus_time_placebo_min"]
        ),
        "future_canary_auc_improves_by_at_least_0_10": (
            canary_delta is not None
            and canary_delta >= DIAGNOSTIC_GATES["future_canary_auc_minus_real_min"]
        ),
        "signed_feature_inversion_does_not_improve_all_primary_discrimination_metrics": not sign_improves_all,
    }
    diagnostics_pass = all(diagnostic_gates.values())
    r_pass = all(r_gates.values())
    rl2_absolute_pass = all(rl2_gates.values())
    rl2_incremental_pass = all(rl2_incremental.values())

    if diagnostics_pass and r_pass:
        status = "PREDICTABLE_SANDBOX_R"
    elif diagnostics_pass and (not r_pass) and rl2_absolute_pass and rl2_incremental_pass:
        status = "PREDICTABLE_SANDBOX_RL2_ONLY"
    else:
        status = "FAIL_OPPORTUNITY_NOT_PREDICTABLE"

    prediction_digest = canonical_sha256(records)
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "sandbox_only": True,
        "direction_scored": False,
        "pnl_scored": False,
        "frozen_commit": frozen_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": asdict(Config()),
        "configuration_sha256": canonical_sha256(Config()),
        "input_manifest": manifest,
        "fold_train_counts": fold_train_counts,
        "metrics": metrics,
        "gates": {
            "R_absolute": r_gates,
            "RL2_absolute": rl2_gates,
            "RL2_incremental": rl2_incremental,
            "diagnostics": diagnostic_gates,
            "R_pass": r_pass,
            "RL2_absolute_pass": rl2_absolute_pass,
            "RL2_incremental_pass": rl2_incremental_pass,
            "diagnostics_pass": diagnostics_pass,
        },
        "diagnostic_deltas": {
            "R_auc_minus_time_placebo_auc": time_delta,
            "future_canary_auc_minus_R_auc": canary_delta,
            "sign_inversion_improves_all_primary_discrimination_metrics": sign_improves_all,
        },
        "oos_prediction_records_sha256": prediction_digest,
        "oos_prediction_records": records,
        "interpretation": (
            "P1 tests opportunity occurrence only. A predictive PASS is consumed-sandbox ranking evidence, "
            "not direction, executable PnL, validation, or permission to open August."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    partial.write_text(encoded, encoding="utf-8")
    partial.replace(output)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Frozen CODEX-EXP-004-P1 10-minute opportunity predictability experiment"
    )
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args(argv)
    result = run(args.feature_dir, args.output, args.workspace, args.frozen_commit)
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "status": result["status"],
                "R_pooled_auc": result["metrics"]["R"]["pooled"]["roc_auc"],
                "R_pooled_average_precision": result["metrics"]["R"]["pooled"]["average_precision"],
                "R_top_decile_lift": result["metrics"]["R"]["pooled"]["top_decile_lift"],
                "RL2_pooled_auc": result["metrics"]["RL2"]["pooled"]["roc_auc"],
                "diagnostics_pass": result["gates"]["diagnostics_pass"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

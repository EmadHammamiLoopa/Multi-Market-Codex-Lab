from __future__ import annotations

import argparse
import json
import math
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

from .codex_research import (
    EXPERIMENT_ID,
    SANDBOX_DAYS,
    ResearchSealError,
    assert_unsealed_day,
    assert_unsealed_path,
    canonical_sha256,
    sha256_file,
)
from .v23_phase0dl_score import BLOCKS, DayData, _load_day


SYMBOLS = ("BTCUSDT", "ETHUSDT")
TRACKS = ("L0", "L2")
HORIZONS_S = (10, 30)
REGULARIZATION_C = (0.1, 1.0)
PROBABILITY_THRESHOLDS = (0.55, 0.65, 0.75, 0.85, 0.95)
COSTS_BPS = (8.0, 10.0, 12.0)
PRIMARY_COST_BPS = 8.0
STRESS_COST_BPS = 12.0
GRID_S = 0.25
ENTRY_STEPS = 1
TRAIN_STRIDE = 4
MIN_INNER_TRADES = 20
RANDOM_SEED = 20260825


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str = EXPERIMENT_ID
    symbols: tuple[str, ...] = SYMBOLS
    days: tuple[str, ...] = tuple(day.isoformat() for day in SANDBOX_DAYS)
    tracks: tuple[str, ...] = TRACKS
    horizons_s: tuple[int, ...] = HORIZONS_S
    regularization_c: tuple[float, ...] = REGULARIZATION_C
    probability_thresholds: tuple[float, ...] = PROBABILITY_THRESHOLDS
    costs_bps: tuple[float, ...] = COSTS_BPS
    primary_cost_bps: float = PRIMARY_COST_BPS
    stress_cost_bps: float = STRESS_COST_BPS
    grid_s: float = GRID_S
    entry_steps: int = ENTRY_STEPS
    training_stride: int = TRAIN_STRIDE
    minimum_inner_trades: int = MIN_INNER_TRADES
    random_seed: int = RANDOM_SEED


@dataclass(frozen=True)
class ExecutableOutcomes:
    valid: np.ndarray
    entry_index: np.ndarray
    exit_index: np.ndarray
    long_gross_bps: np.ndarray
    short_gross_bps: np.ndarray
    long_positive: np.ndarray
    short_positive: np.ndarray


@dataclass
class CalibratedSideModel:
    scaler: Any
    base: Any
    calibrator: Any
    positive_mean_net_bps: float
    nonpositive_mean_net_bps: float

    def forecast(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        transformed = self.scaler.transform(X)
        base_logit = self.base.decision_function(transformed).reshape(-1, 1)
        probability = self.calibrator.predict_proba(base_logit)[:, 1]
        utility = (
            probability * self.positive_mean_net_bps
            + (1.0 - probability) * self.nonpositive_mean_net_bps
        )
        return probability, utility


@dataclass
class ModelPair:
    long: CalibratedSideModel
    short: CalibratedSideModel


def executable_outcomes(
    day: DayData,
    block: str,
    horizon_s: int,
    *,
    primary_cost_bps: float = PRIMARY_COST_BPS,
    entry_steps: int = ENTRY_STEPS,
    grid_s: float = GRID_S,
) -> ExecutableOutcomes:
    assert_unsealed_day(day.day, allowed=SANDBOX_DAYS)
    if block not in BLOCKS:
        raise ValueError(f"unknown feature block: {block}")
    horizon_steps = int(round(horizon_s / grid_s))
    if horizon_steps <= 0 or not math.isclose(horizon_steps * grid_s, horizon_s):
        raise ValueError("horizon must be a positive multiple of the feature grid")
    n = len(day.ts)
    row = np.arange(n, dtype=np.int64)
    entry = row + int(entry_steps)
    exit_ = entry + horizon_steps
    safe_entry = np.minimum(entry, max(n - 1, 0))
    safe_exit = np.minimum(exit_, max(n - 1, 0))
    valid = day.valid[block].copy()
    valid &= exit_ < n
    if n:
        valid &= day.book_valid[safe_entry] & day.book_valid[safe_exit]
    long_gross = np.full(n, np.nan, dtype=np.float64)
    short_gross = np.full(n, np.nan, dtype=np.float64)
    idx = np.flatnonzero(valid)
    if len(idx):
        e = entry[idx]
        x = exit_[idx]
        long_gross[idx] = 10_000.0 * np.log(day.bid[x] / day.ask[e])
        short_gross[idx] = 10_000.0 * np.log(day.bid[e] / day.ask[x])
    valid &= np.isfinite(long_gross) & np.isfinite(short_gross)
    long_positive = valid & ((long_gross - primary_cost_bps) > 0.0)
    short_positive = valid & ((short_gross - primary_cost_bps) > 0.0)
    return ExecutableOutcomes(
        valid=valid,
        entry_index=entry,
        exit_index=exit_,
        long_gross_bps=long_gross,
        short_gross_bps=short_gross,
        long_positive=long_positive,
        short_positive=short_positive,
    )


def split_calibration_selection(
    outcomes: ExecutableOutcomes,
    *,
    horizon_s: int,
    n_rows: int,
    entry_steps: int = ENTRY_STEPS,
    grid_s: float = GRID_S,
) -> tuple[np.ndarray, np.ndarray]:
    """Split an inner day and purge calibration labels crossing the midpoint."""

    midpoint = n_rows // 2
    span = int(entry_steps) + int(round(horizon_s / grid_s))
    row = np.arange(n_rows, dtype=np.int64)
    calibration = np.flatnonzero(outcomes.valid & ((row + span) < midpoint))
    selection = np.flatnonzero(outcomes.valid & (row >= midpoint))
    return calibration, selection


def greedy_nonoverlap(indices: np.ndarray, *, horizon_s: int) -> np.ndarray:
    span = ENTRY_STEPS + int(round(horizon_s / GRID_S))
    chosen: list[int] = []
    next_allowed = -1
    for raw in indices.tolist():
        index = int(raw)
        if index >= next_allowed:
            chosen.append(index)
            next_allowed = index + span
    return np.asarray(chosen, dtype=np.int64)


def _max_drawdown(values: np.ndarray) -> float:
    if not len(values):
        return 0.0
    equity = np.cumsum(values)
    peaks = np.maximum.accumulate(np.concatenate(([0.0], equity)))[:-1]
    return float(np.max(peaks - equity))


def _economic_metrics(gross: np.ndarray, cost_bps: float) -> dict[str, Any]:
    net = gross - float(cost_bps)
    profit = float(net[net > 0].sum()) if np.any(net > 0) else 0.0
    loss = float(-net[net < 0].sum()) if np.any(net < 0) else 0.0
    total = float(net.sum())
    drawdown = _max_drawdown(net)
    return {
        "trades": int(len(net)),
        "gross_bps_trade": float(gross.mean()) if len(gross) else 0.0,
        "net_bps_trade": float(net.mean()) if len(net) else 0.0,
        "total_net_bps": total,
        "profit_factor": profit / loss if loss > 0 else (float("inf") if profit > 0 else 0.0),
        "max_drawdown_bps": drawdown,
        "pnl_to_drawdown": total / drawdown if drawdown > 0 else (float("inf") if total > 0 else 0.0),
        "worst_trade_bps": float(net.min()) if len(net) else 0.0,
        "net_values_bps": net.tolist(),
    }


def score_probabilistic_actions(
    day: DayData,
    outcomes: ExecutableOutcomes,
    indices: np.ndarray,
    long_probability: np.ndarray,
    short_probability: np.ndarray,
    long_utility: np.ndarray,
    short_utility: np.ndarray,
    *,
    probability_threshold: float,
    horizon_s: int,
) -> dict[str, Any]:
    if not (
        len(indices)
        == len(long_probability)
        == len(short_probability)
        == len(long_utility)
        == len(short_utility)
    ):
        raise ValueError("forecast arrays must align with indices")
    finite = (
        np.isfinite(long_probability)
        & np.isfinite(short_probability)
        & np.isfinite(long_utility)
        & np.isfinite(short_utility)
    )
    long_ok = finite & (long_probability >= probability_threshold) & (long_utility > 0.0)
    short_ok = finite & (short_probability >= probability_threshold) & (short_utility > 0.0)
    direction = np.zeros(len(indices), dtype=np.int8)
    direction[long_ok & (~short_ok | (long_utility > short_utility))] = 1
    direction[short_ok & (~long_ok | (short_utility > long_utility))] = -1
    candidate_local = np.flatnonzero(direction)
    chosen_global = greedy_nonoverlap(indices[candidate_local], horizon_s=horizon_s)
    position = {int(global_index): local for local, global_index in enumerate(indices.tolist())}
    chosen_local = np.asarray([position[int(index)] for index in chosen_global], dtype=np.int64)
    chosen_direction = direction[chosen_local]
    gross = np.where(
        chosen_direction > 0,
        outcomes.long_gross_bps[chosen_global],
        outcomes.short_gross_bps[chosen_global],
    )
    costs = {str(int(cost)): _economic_metrics(gross, cost) for cost in COSTS_BPS}
    hours = (day.ts[chosen_global] // 3_600_000_000).astype(np.int64) if len(chosen_global) else np.empty(0, dtype=np.int64)
    primary_net = gross - PRIMARY_COST_BPS
    hour_pnl: dict[str, float] = {}
    for hour, pnl in zip(hours.tolist(), primary_net.tolist()):
        key = str(int(hour))
        hour_pnl[key] = hour_pnl.get(key, 0.0) + float(pnl)
    costs["8"]["active_hours"] = len(hour_pnl)
    costs["8"]["positive_active_hour_fraction"] = (
        float(np.mean(np.asarray(list(hour_pnl.values())) > 0.0)) if hour_pnl else 0.0
    )
    return {
        "probability_threshold": probability_threshold,
        "candidate_rows": int(len(candidate_local)),
        "directions": {"long": int(np.sum(chosen_direction > 0)), "short": int(np.sum(chosen_direction < 0))},
        "signal_indices": chosen_global.tolist(),
        "signal_timestamp_us": day.ts[chosen_global].astype(np.int64).tolist(),
        "gross_values_bps": gross.tolist(),
        "hour_pnl_8bps": hour_pnl,
        "costs": costs,
    }


def calibration_metrics(y: np.ndarray, probability: np.ndarray, *, bins: int = 10) -> dict[str, Any]:
    if len(y) != len(probability):
        raise ValueError("labels and probabilities must align")
    if not len(y):
        return {"rows": 0, "brier": None, "log_loss": None, "ece": None, "prevalence": None, "bins": []}
    labels = y.astype(np.float64)
    p = np.clip(probability.astype(np.float64), 1e-12, 1.0 - 1e-12)
    edges = np.linspace(0.0, 1.0, bins + 1)
    bin_rows: list[dict[str, Any]] = []
    ece = 0.0
    for i in range(bins):
        member = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= edges[i + 1])
        count = int(member.sum())
        if not count:
            continue
        confidence = float(p[member].mean())
        observed = float(labels[member].mean())
        ece += (count / len(labels)) * abs(confidence - observed)
        bin_rows.append({"lower": float(edges[i]), "upper": float(edges[i + 1]), "rows": count, "mean_probability": confidence, "observed_rate": observed})
    return {
        "rows": int(len(labels)),
        "brier": float(np.mean((p - labels) ** 2)),
        "log_loss": float(-np.mean(labels * np.log(p) + (1.0 - labels) * np.log(1.0 - p))),
        "ece": float(ece),
        "prevalence": float(labels.mean()),
        "bins": bin_rows,
    }


def _training_rows(days: Sequence[DayData], block: str, horizon_s: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    feature_rows: list[np.ndarray] = []
    long_labels: list[np.ndarray] = []
    short_labels: list[np.ndarray] = []
    long_net: list[np.ndarray] = []
    short_net: list[np.ndarray] = []
    for day in days:
        outcomes = executable_outcomes(day, block, horizon_s)
        idx = np.flatnonzero(outcomes.valid)[::TRAIN_STRIDE]
        feature_rows.append(day.X[block][idx])
        long_labels.append(outcomes.long_positive[idx].astype(np.int8))
        short_labels.append(outcomes.short_positive[idx].astype(np.int8))
        long_net.append(outcomes.long_gross_bps[idx] - PRIMARY_COST_BPS)
        short_net.append(outcomes.short_gross_bps[idx] - PRIMARY_COST_BPS)
    return (
        np.concatenate(feature_rows),
        np.concatenate(long_labels),
        np.concatenate(short_labels),
        np.concatenate(long_net),
        np.concatenate(short_net),
    )


def _fit_side(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_calibration: np.ndarray,
    y_calibration: np.ndarray,
    calibration_net_bps: np.ndarray,
    *,
    c_value: float,
) -> CalibratedSideModel:
    if len(np.unique(y_train)) != 2 or len(np.unique(y_calibration)) != 2:
        raise ValueError("training and calibration slices must each contain both classes")
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    transformed_train = scaler.fit_transform(X_train)
    base = LogisticRegression(
        C=float(c_value),
        class_weight="balanced",
        max_iter=300,
        random_state=RANDOM_SEED,
        solver="lbfgs",
    )
    base.fit(transformed_train, y_train)
    calibration_logit = base.decision_function(scaler.transform(X_calibration)).reshape(-1, 1)
    calibrator = LogisticRegression(C=1_000_000.0, max_iter=200, random_state=RANDOM_SEED, solver="lbfgs")
    calibrator.fit(calibration_logit, y_calibration)
    positive_mean = float(calibration_net_bps[y_calibration == 1].mean())
    nonpositive_mean = float(calibration_net_bps[y_calibration == 0].mean())
    return CalibratedSideModel(scaler, base, calibrator, positive_mean, nonpositive_mean)


def _fit_pair(
    train_days: Sequence[DayData],
    inner_day: DayData,
    block: str,
    horizon_s: int,
    c_value: float,
) -> tuple[ModelPair, ExecutableOutcomes, np.ndarray, np.ndarray]:
    X_train, y_long, y_short, _, _ = _training_rows(train_days, block, horizon_s)
    outcomes = executable_outcomes(inner_day, block, horizon_s)
    calibration_idx, selection_idx = split_calibration_selection(outcomes, horizon_s=horizon_s, n_rows=len(inner_day.ts))
    calibration_idx = calibration_idx[::TRAIN_STRIDE]
    X_calibration = inner_day.X[block][calibration_idx]
    long_net = outcomes.long_gross_bps[calibration_idx] - PRIMARY_COST_BPS
    short_net = outcomes.short_gross_bps[calibration_idx] - PRIMARY_COST_BPS
    long_model = _fit_side(X_train, y_long, X_calibration, outcomes.long_positive[calibration_idx].astype(np.int8), long_net, c_value=c_value)
    short_model = _fit_side(X_train, y_short, X_calibration, outcomes.short_positive[calibration_idx].astype(np.int8), short_net, c_value=c_value)
    return ModelPair(long_model, short_model), outcomes, calibration_idx, selection_idx


def _inner_survives(score: dict[str, Any]) -> bool:
    primary = score["costs"]["8"]
    stress = score["costs"]["12"]
    return bool(
        primary["trades"] >= MIN_INNER_TRADES
        and primary["net_bps_trade"] > 0.0
        and primary["total_net_bps"] > 0.0
        and primary["profit_factor"] > 1.0
        and stress["net_bps_trade"] > 0.0
        and stress["total_net_bps"] > 0.0
    )


def _selection_key(candidate: dict[str, Any]) -> tuple[float, float, float, int, float, int]:
    primary = candidate["selection_score"]["costs"]["8"]
    return (
        float(primary["net_bps_trade"]),
        float(primary["total_net_bps"]),
        float(primary["profit_factor"]),
        -int(candidate["horizon_s"]),
        float(candidate["probability_threshold"]),
        -int(round(float(candidate["c_value"]) * 10)),
    )


def select_configuration(train_days: Sequence[DayData], inner_day: DayData, block: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    candidates_tested = 0
    survivors: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for horizon_s in HORIZONS_S:
        for c_value in REGULARIZATION_C:
            try:
                models, outcomes, calibration_idx, selection_idx = _fit_pair(train_days, inner_day, block, horizon_s, c_value)
            except ValueError as exc:
                invalid.append({"horizon_s": horizon_s, "c_value": c_value, "reason": str(exc)})
                continue
            X_selection = inner_day.X[block][selection_idx]
            p_long, u_long = models.long.forecast(X_selection)
            p_short, u_short = models.short.forecast(X_selection)
            for threshold in PROBABILITY_THRESHOLDS:
                candidates_tested += 1
                score = score_probabilistic_actions(
                    inner_day,
                    outcomes,
                    selection_idx,
                    p_long,
                    p_short,
                    u_long,
                    u_short,
                    probability_threshold=threshold,
                    horizon_s=horizon_s,
                )
                if _inner_survives(score):
                    survivors.append(
                        {
                            "block": block,
                            "horizon_s": horizon_s,
                            "c_value": c_value,
                            "probability_threshold": threshold,
                            "models": models,
                            "calibration_rows": int(len(calibration_idx)),
                            "selection_rows": int(len(selection_idx)),
                            "selection_score": score,
                        }
                    )
    if not survivors:
        return None, {"tested": candidates_tested, "survivors": 0, "invalid_models": invalid, "reason": "NO_CONFIGURATION"}
    best = max(survivors, key=_selection_key)
    public = {key: value for key, value in best.items() if key != "models"}
    return best, {"tested": candidates_tested, "survivors": len(survivors), "selected": public, "invalid_models": invalid}


def score_outer(day: DayData, selected: dict[str, Any]) -> dict[str, Any]:
    block = str(selected["block"])
    horizon_s = int(selected["horizon_s"])
    outcomes = executable_outcomes(day, block, horizon_s)
    idx = np.flatnonzero(outcomes.valid)
    X = day.X[block][idx]
    models: ModelPair = selected["models"]
    p_long, u_long = models.long.forecast(X)
    p_short, u_short = models.short.forecast(X)
    score = score_probabilistic_actions(
        day,
        outcomes,
        idx,
        p_long,
        p_short,
        u_long,
        u_short,
        probability_threshold=float(selected["probability_threshold"]),
        horizon_s=horizon_s,
    )
    score["calibration"] = {
        "long": calibration_metrics(outcomes.long_positive[idx], p_long),
        "short": calibration_metrics(outcomes.short_positive[idx], p_short),
    }
    score["configuration"] = {
        "block": block,
        "horizon_s": horizon_s,
        "c_value": float(selected["c_value"]),
        "probability_threshold": float(selected["probability_threshold"]),
    }
    return score


def _pool_outer(folds: Sequence[dict[str, Any]], key: str) -> dict[str, Any]:
    cost_values: dict[str, list[float]] = {"8": [], "10": [], "12": []}
    fold_expectancy: list[float | None] = []
    positive_profit_by_day: list[float] = []
    active_hour_values: dict[str, float] = {}
    valid_folds = 0
    for fold in folds:
        outer = fold.get(key)
        if not outer:
            fold_expectancy.append(None)
            positive_profit_by_day.append(0.0)
            continue
        valid_folds += 1
        fold_expectancy.append(float(outer["costs"]["8"]["net_bps_trade"]))
        for cost in cost_values:
            cost_values[cost].extend(float(value) for value in outer["costs"][cost]["net_values_bps"])
        day_net = np.asarray(outer["costs"]["8"]["net_values_bps"], dtype=np.float64)
        positive_profit_by_day.append(float(day_net[day_net > 0].sum()) if np.any(day_net > 0) else 0.0)
        for hour, pnl in outer["hour_pnl_8bps"].items():
            key_hour = f"{fold['evaluation_day']}T{int(hour):02d}"
            active_hour_values[key_hour] = active_hour_values.get(key_hour, 0.0) + float(pnl)
    metrics = {}
    for cost, values in cost_values.items():
        net = np.asarray(values, dtype=np.float64)
        gross = net + float(cost)
        metrics[cost] = _economic_metrics(gross, float(cost))
    total_positive = sum(positive_profit_by_day)
    max_day_share = max(positive_profit_by_day, default=0.0) / total_positive if total_positive > 0 else 1.0
    primary = metrics["8"]
    primary["active_hours"] = len(active_hour_values)
    primary["positive_active_hour_fraction"] = (
        float(np.mean(np.asarray(list(active_hour_values.values())) > 0.0)) if active_hour_values else 0.0
    )
    return {
        "valid_configuration_folds": valid_folds,
        "fold_expectancy_8bps": fold_expectancy,
        "positive_expectancy_folds_8bps": sum(value is not None and value > 0.0 for value in fold_expectancy),
        "maximum_positive_profit_day_share": max_day_share,
        "costs": metrics,
    }


def _structural_pass(pool: dict[str, Any]) -> bool:
    fold_values = pool["fold_expectancy_8bps"]
    primary = pool["costs"]["8"]
    stress = pool["costs"]["12"]
    return bool(
        pool["valid_configuration_folds"] == 5
        and pool["positive_expectancy_folds_8bps"] >= 4
        and primary["net_bps_trade"] >= 1.0
        and primary["total_net_bps"] > 0.0
        and primary["profit_factor"] >= 1.25
        and primary["pnl_to_drawdown"] >= 2.0
        and primary["trades"] >= 100
        and primary["positive_active_hour_fraction"] >= 0.55
        and stress["net_bps_trade"] > 0.0
        and stress["total_net_bps"] > 0.0
        and all(value is not None and value >= -2.0 for value in fold_values)
        and pool["maximum_positive_profit_day_share"] <= 0.50
    )


def score_symbol(days: Sequence[DayData], symbol: str) -> dict[str, Any]:
    if tuple(day.day for day in days) != SANDBOX_DAYS:
        raise ResearchSealError("loaded days do not exactly match the frozen sandbox sequence")
    folds: list[dict[str, Any]] = []
    for eval_index in range(2, 7):
        train_days = days[: eval_index - 1]
        inner_day = days[eval_index - 1]
        outer_day = days[eval_index]
        fold: dict[str, Any] = {
            "fold": eval_index - 1,
            "base_training_days": [day.day.isoformat() for day in train_days],
            "inner_calibration_selection_day": inner_day.day.isoformat(),
            "evaluation_day": outer_day.day.isoformat(),
        }
        for block, prefix in (("L0", "l0"), ("L2", "l2")):
            selected, audit = select_configuration(train_days, inner_day, block)
            fold[f"{prefix}_selection"] = audit
            if selected is not None:
                fold[f"{prefix}_outer"] = score_outer(outer_day, selected)
        folds.append(fold)
        print(symbol, outer_day.day.isoformat(), "L0=", "l0_outer" in fold, "L2=", "l2_outer" in fold, flush=True)
    l0_pool = _pool_outer(folds, "l0_outer")
    l2_pool = _pool_outer(folds, "l2_outer")
    l0_pass = _structural_pass(l0_pool)
    l2_structural = _structural_pass(l2_pool)
    incremental = bool(
        l2_structural
        and l2_pool["costs"]["8"]["net_bps_trade"] > l0_pool["costs"]["8"]["net_bps_trade"]
        and l2_pool["costs"]["8"]["total_net_bps"] > l0_pool["costs"]["8"]["total_net_bps"]
    )
    passed = bool(l2_structural and incremental)
    return {
        "symbol": symbol,
        "folds": folds,
        "l0_pooled": l0_pool,
        "l2_pooled": l2_pool,
        "l0_structural_pass": l0_pass,
        "l2_structural_pass": l2_structural,
        "incremental_information_pass": incremental,
        "sandbox_pass": passed,
        "status": "PASS_SANDBOX" if passed else "FAIL",
    }


def required_input_paths(feature_dir: Path, config: ExperimentConfig) -> list[tuple[str, date, Path]]:
    paths: list[tuple[str, date, Path]] = []
    for symbol in config.symbols:
        for raw_day in config.days:
            day = date.fromisoformat(raw_day)
            assert_unsealed_day(day, allowed=SANDBOX_DAYS)
            path = feature_dir / symbol / f"{day.isoformat()}_FEATURES250.csv"
            assert_unsealed_path(path)
            paths.append((symbol, day, path))
    return paths


def input_manifest(feature_dir: Path, config: ExperimentConfig, *, hash_files: bool = True) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    for symbol, day, path in required_input_paths(feature_dir, config):
        if not path.is_file():
            missing.append(str(path))
            records.append({"symbol": symbol, "day": day.isoformat(), "path": str(path), "exists": False})
            continue
        record = {"symbol": symbol, "day": day.isoformat(), "path": str(path), "exists": True, "bytes": path.stat().st_size}
        if hash_files:
            record["sha256"] = sha256_file(path)
        records.append(record)
    return records, missing


def _git_state() -> dict[str, Any]:
    repository = Path(__file__).resolve().parents[2]
    try:
        git_args = ["git", "-c", f"safe.directory={repository}"]
        commit = subprocess.check_output(git_args + ["rev-parse", "HEAD"], cwd=repository, text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(git_args + ["status", "--porcelain"], cwd=repository, text=True, stderr=subprocess.DEVNULL).strip())
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        head_path = repository / ".git" / "HEAD"
        try:
            head = head_path.read_text(encoding="utf-8").strip()
            if head.startswith("ref: "):
                commit = (repository / ".git" / head[5:]).read_text(encoding="utf-8").strip()
            else:
                commit = head
        except OSError:
            commit = None
        return {"commit": commit, "dirty": None}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    return value


def write_artifact(output_dir: Path, payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = output_dir / f"{EXPERIMENT_ID}_{stamp}.json"
    assert_unsealed_path(path)
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return path


def run(feature_dir: Path, output_dir: Path, *, check_inputs_only: bool = False) -> tuple[int, Path, dict[str, Any]]:
    config = ExperimentConfig()
    config_dict = asdict(config)
    manifest, missing = input_manifest(feature_dir, config, hash_files=False)
    if not missing:
        manifest, missing = input_manifest(feature_dir, config, hash_files=True)
    base_payload: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "evidence_scope": "SANDBOX_DEVELOPMENT_ONLY",
        "sealed_periods_analytically_opened": False,
        "config": config_dict,
        "config_sha256": canonical_sha256(config_dict),
        "input_manifest": manifest,
        "git": _git_state(),
        "runtime": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__},
    }
    if missing:
        base_payload.update({"status": "NOT_RUN_MISSING_INPUT", "missing_inputs": missing, "result": None})
        artifact = write_artifact(output_dir, base_payload)
        return 2, artifact, base_payload
    if check_inputs_only:
        base_payload.update({"status": "INPUT_CHECK_PASS", "result": None})
        artifact = write_artifact(output_dir, base_payload)
        return 0, artifact, base_payload
    results = []
    for symbol in config.symbols:
        loaded = []
        for raw_day in config.days:
            day = date.fromisoformat(raw_day)
            assert_unsealed_day(day, allowed=SANDBOX_DAYS)
            path = feature_dir / symbol / f"{raw_day}_FEATURES250.csv"
            assert_unsealed_path(path)
            loaded.append(_load_day(path, day))
        results.append(score_symbol(loaded, symbol))
    any_pass = any(result["sandbox_pass"] for result in results)
    base_payload.update({"status": "PASS_SANDBOX" if any_pass else "FAIL", "result": {"symbols": results, "any_symbol_pass": any_pass}})
    artifact = write_artifact(output_dir, base_payload)
    return (0 if any_pass else 1), artifact, base_payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CODEX-EXP-001 calibrated executable-net sandbox runner; rejects all sealed dates")
    parser.add_argument("--feature-dir", default="evidence/v23/phase0dl_features250")
    parser.add_argument("--output-dir", default="evidence/codex")
    parser.add_argument("--check-inputs", action="store_true")
    args = parser.parse_args(argv)
    try:
        code, artifact, payload = run(Path(args.feature_dir), Path(args.output_dir), check_inputs_only=args.check_inputs)
    except ResearchSealError as exc:
        print(f"INVALID_SEALED_PERIOD: {exc}", file=sys.stderr)
        return 3
    print(f"{payload['status']} artifact={artifact}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

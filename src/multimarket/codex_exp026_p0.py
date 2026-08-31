from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import sklearn

from .codex_exp004_headroom import (
    ENTRY_STEPS,
    GRID_US,
    assert_frozen_workspace,
    executable_fixed_horizon,
)
from .codex_exp004_p1 import (
    DECISION_STEP_ROWS,
    HORIZON_S,
    LABEL_THRESHOLD_BPS,
    R_FEATURE_NAMES,
    FixedLogistic,
    build_day_dataset,
)
from .codex_exp022_p1 import _verify_training_inputs
from .codex_exp023_p0 import (
    adjudicate_invariants,
    normalize_json_safe,
    validate_builtin_bool_invariants,
)
from .codex_research import canonical_sha256, sha256_file
from .v23_phase0dl_score import DayData, _load_day


EXPERIMENT_ID = "CODEX-EXP-026-P0"
PASS_STATUS = "DIRECTION_EXECUTION_PIPELINE_READY_FOR_FRESH_PROSPECTIVE_VALIDATION"
FAIL_STATUS = "FAIL_DIRECTION_EXECUTION_PIPELINE_NOT_READY"
INVALID_STATUS = "INVALID"

PREREGISTRATION_COMMIT = "d92c19f2277817806534de214be42a4a90db7420"
PREREGISTRATION_REL = "docs/CODEX_EXP026_P0_DIRECTION_EXECUTION_READINESS.md"
PREREGISTRATION_SHA256 = "7c2cdfa7f1b595b5ff59b930a28b32770e5bd3818f5d9e8fb2909e8a6ad089f9"
PARENT_RESULT_REL = (
    "evidence/codex/exp024_p1_fresh_prospective_ranking_confirmation/"
    "PROSPECTIVE_RANKING_CONFIRMATION.json"
)
PARENT_RESULT_SHA256 = "0fda20d127e51e8ad792c6b949889f88b59e75ab98b437fd04ead285970e5c10"
PARENT_EXPERIMENT_ID = "CODEX-EXP-024-P1"
PARENT_STATUS = "PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED"

SYMBOL = "BTCUSDT"
HISTORICAL_DAYS = tuple(date(2026, month, 1) for month in range(1, 8))
HISTORICAL_DAY_STRINGS = tuple(day.isoformat() for day in HISTORICAL_DAYS)
AUTHORIZED_FEATURE_ROOT = Path("/home/emadh/Multi-Market/evidence/v23/phase0dl_features250")
FOLDS = (
    (HISTORICAL_DAYS[:3], HISTORICAL_DAYS[3]),
    (HISTORICAL_DAYS[:4], HISTORICAL_DAYS[4]),
    (HISTORICAL_DAYS[:5], HISTORICAL_DAYS[5]),
    (HISTORICAL_DAYS[:6], HISTORICAL_DAYS[6]),
)

OPPORTUNITY_FEATURE = "rv_30m_bps"
VOL_INDEX = R_FEATURE_NAMES.index(OPPORTUNITY_FEATURE)
DIRECTION_FEATURE_NAMES = (
    "ret_1m_bps",
    "ret_3m_bps",
    "ret_5m_bps",
    "ret_10m_bps",
    "ret_30m_bps",
    "rv_30m_bps",
    "spread_bps",
)
DIRECTION_INDICES = tuple(R_FEATURE_NAMES.index(name) for name in DIRECTION_FEATURE_NAMES)
RET_10M_INDEX = DIRECTION_FEATURE_NAMES.index("ret_10m_bps")
CANDIDATES = ("A", "B", "C")
SIMPLICITY_ORDER = ("B", "C", "A")
OPPORTUNITY_QUANTILE = 0.90
OPPORTUNITY_QUANTILE_METHOD = "higher"
DIRECTION_THRESHOLD = 0.5
PRIMARY_COST_BPS = 14.0
STRESS_COST_BPS = 20.0
DECISION_STEP_US = 60_000_000
ENTRY_DELAY_US = 250_000
HOLDING_DURATION_US = 600_000_000
HORIZON_STEPS = int(round(HORIZON_S * 1_000_000 / GRID_US))
DAY_US = 86_400_000_000

AUG30_ANALYTICALLY_OPENED = False
SEP01_OR_LATER_OPENED = False
NETWORK_ACCESSED = False


class ProtocolViolation(RuntimeError):
    """A provenance, semantics, causality, or sealed-data invariant failed."""


class SelectionReadinessFailure(RuntimeError):
    """A clean historical support or selection inability."""


@dataclass
class DirectionDay:
    day: date
    timestamp_us: np.ndarray
    entry_timestamp_us: np.ndarray
    exit_timestamp_us: np.ndarray
    X_direction: np.ndarray
    rv_30m_bps: np.ndarray
    ret_10m_bps: np.ndarray
    opportunity_label: np.ndarray
    long_preferred: np.ndarray
    long_gross_bps: np.ndarray
    short_gross_bps: np.ndarray
    common_support: np.ndarray
    parent_support_exact: bool


@dataclass
class ExecutionEvaluation:
    metrics: dict[str, Any]
    net_bps: np.ndarray
    entry_timestamp_us: np.ndarray
    exit_timestamp_us: np.ndarray


@dataclass
class CoreSelection:
    days: dict[date, DirectionDay]
    folds: list[dict[str, Any]]
    private_folds: list[dict[str, Any]]
    selected_candidate: str
    candidate_selection: dict[str, Any]
    final_models: dict[str, Any]


@dataclass(frozen=True)
class RunWriteResult:
    payload: dict[str, Any]
    output_sha256: str


STATIC_INVARIANT_NAMES = (
    "no_protocol_violation_detected",
    "preregistration_sha_verified",
    "parent_result_sha_and_status_verified",
    "historical_input_provenance_verified",
    "exact_jan_jul_historical_calendar",
    "exactly_four_expanding_folds",
    "candidate_set_exactly_A_B_C",
    "opportunity_feature_exactly_rv_30m_bps",
    "direction_feature_list_exact",
    "decision_step_exactly_60s",
    "entry_delay_exactly_250ms",
    "holding_duration_exactly_600s",
    "primary_cost_exactly_14bp",
    "stress_cost_exactly_20bp",
    "trigger_quantile_exactly_0_90_higher",
    "aug30_analytically_opened_false",
    "sep01_or_later_opened_false",
    "network_accessed_false",
    "no_leverage_stop_loss_take_profit_sizing_or_posthoc_filter",
)
EXECUTION_INVARIANT_NAMES = (
    "historical_common_support_equals_parent_valid_R",
    "every_fold_trigger_training_probabilities_only",
    "no_validation_derived_threshold",
    "nonoverlap_accounting_consistent",
    "no_position_overlap",
    "exposure_fraction_finite_and_bounded",
    "executed_trade_timing_exact",
)
READINESS_INVARIANT_NAMES = (
    "historical_selection_pipeline_completed",
    "exactly_one_candidate_selected",
    "all_four_folds_scored_for_each_candidate",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def scientific_configuration() -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "symbol": SYMBOL,
        "historical_days": list(HISTORICAL_DAY_STRINGS),
        "folds": [
            {
                "train_dates": [day.isoformat() for day in train],
                "validation_date": validation.isoformat(),
            }
            for train, validation in FOLDS
        ],
        "opportunity_feature": OPPORTUNITY_FEATURE,
        "direction_features": list(DIRECTION_FEATURE_NAMES),
        "candidates": list(CANDIDATES),
        "decision_step_rows": DECISION_STEP_ROWS,
        "decision_step_us": DECISION_STEP_US,
        "grid_us": GRID_US,
        "entry_steps": ENTRY_STEPS,
        "entry_delay_us": ENTRY_DELAY_US,
        "horizon_s": HORIZON_S,
        "horizon_steps": HORIZON_STEPS,
        "opportunity_label_threshold_bps": LABEL_THRESHOLD_BPS,
        "opportunity_trigger_quantile": OPPORTUNITY_QUANTILE,
        "opportunity_trigger_quantile_method": OPPORTUNITY_QUANTILE_METHOD,
        "direction_probability_threshold": DIRECTION_THRESHOLD,
        "primary_incremental_cost_bps": PRIMARY_COST_BPS,
        "stress_incremental_cost_bps": STRESS_COST_BPS,
        "model": {
            "scaler": "StandardScaler",
            "estimator": "LogisticRegression",
            "C": 1.0,
            "penalty": "l2",
            "solver": "lbfgs",
            "class_weight": None,
            "max_iter": 1000,
            "random_state": 20260825,
        },
        "execution": {
            "flat_only": True,
            "pyramiding": False,
            "leverage": False,
            "stop_loss": False,
            "take_profit": False,
            "position_sizing_optimization": False,
            "post_hoc_filtering": False,
            "spread_crossing_in_gross_return": True,
            "slippage_bps_per_side_inside_primary_incremental_cost": 2.0,
            "round_trip_fee_bps_inside_primary_incremental_cost": 10.0,
        },
    }


SCIENTIFIC_CONFIGURATION_SHA256 = canonical_sha256(scientific_configuration())


def frozen_timing_invariants() -> dict[str, bool]:
    invariants = {
        "decision_step_exactly_60s": bool(
            DECISION_STEP_ROWS * GRID_US == DECISION_STEP_US
        ),
        "entry_delay_exactly_250ms": bool(
            ENTRY_STEPS * GRID_US == ENTRY_DELAY_US and ENTRY_STEPS == 1
        ),
        "holding_duration_exactly_600s": bool(
            HORIZON_S * 1_000_000 % GRID_US == 0
            and HORIZON_S * 1_000_000 // GRID_US == HORIZON_STEPS == 2400
        ),
    }
    validate_builtin_bool_invariants(invariants)
    return invariants


def verify_frozen_references(workspace: Path) -> dict[str, Any]:
    preregistration = workspace / PREREGISTRATION_REL
    parent_result = workspace / PARENT_RESULT_REL
    if sha256_file(preregistration) != PREREGISTRATION_SHA256:
        raise ProtocolViolation("preregistration SHA-256 mismatch")
    if sha256_file(parent_result) != PARENT_RESULT_SHA256:
        raise ProtocolViolation("parent result SHA-256 mismatch")
    with parent_result.open("r", encoding="utf-8") as handle:
        parent = json.load(handle)
    if parent.get("experiment_id") != PARENT_EXPERIMENT_ID:
        raise ProtocolViolation("parent experiment identity mismatch")
    if parent.get("status") != PARENT_STATUS:
        raise ProtocolViolation("parent result status mismatch")
    return {
        "preregistration": {
            "commit": PREREGISTRATION_COMMIT,
            "path": PREREGISTRATION_REL,
            "sha256": PREREGISTRATION_SHA256,
        },
        "parent_result": {
            "experiment_id": PARENT_EXPERIMENT_ID,
            "path": PARENT_RESULT_REL,
            "sha256": PARENT_RESULT_SHA256,
            "status": PARENT_STATUS,
        },
    }


def authorized_feature_path(day: date) -> Path:
    if type(day) is not date or day not in HISTORICAL_DAYS:
        raise ProtocolViolation("day outside exact Jan-Jul historical calendar")
    return AUTHORIZED_FEATURE_ROOT / SYMBOL / f"{day.isoformat()}_FEATURES250.csv"


def _concat(days: Sequence[DirectionDay], field: str) -> np.ndarray:
    parts = [np.asarray(getattr(day, field))[day.common_support] for day in days]
    if not parts or any(len(part) == 0 for part in parts):
        raise SelectionReadinessFailure(f"insufficient historical support for {field}")
    return np.concatenate(parts)


def build_direction_day(day: DayData) -> DirectionDay:
    if day.day not in HISTORICAL_DAYS:
        raise ProtocolViolation("attempted to build unauthorized historical day")
    frozen = build_day_dataset(SYMBOL, day)
    decisions = np.arange(0, len(day.ts), DECISION_STEP_ROWS, dtype=np.int64)
    outcomes = executable_fixed_horizon(day, decisions, HORIZON_S)
    reconstructed = (
        np.asarray(outcomes["valid"], dtype=bool)
        & np.isfinite(outcomes["long_gross_bps"])
        & np.isfinite(outcomes["short_gross_bps"])
        & np.isfinite(outcomes["oracle_gross_bps"])
        & np.all(np.isfinite(frozen.X_R), axis=1)
    )
    parent_support_exact = bool(np.array_equal(reconstructed, frozen.valid_R))
    if not parent_support_exact:
        raise ProtocolViolation(
            f"EXP026 reconstructed support differs from parent valid_R: {day.day}"
        )
    support = np.asarray(frozen.valid_R, dtype=bool).copy()
    if not np.array_equal(frozen.timestamp_us, day.ts[decisions]):
        raise ProtocolViolation("parent decision timestamps differ from frozen 60s grid")

    entry_indices = np.asarray(outcomes["entry_index"], dtype=np.int64)
    exit_indices = np.asarray(outcomes["exit_index"], dtype=np.int64)
    entry_ts = np.full(len(decisions), -1, dtype=np.int64)
    exit_ts = np.full(len(decisions), -1, dtype=np.int64)
    bounded = (entry_indices < len(day.ts)) & (exit_indices < len(day.ts))
    entry_ts[bounded] = day.ts[entry_indices[bounded]]
    exit_ts[bounded] = day.ts[exit_indices[bounded]]
    if np.any(entry_indices[support] - decisions[support] != ENTRY_STEPS):
        raise ProtocolViolation("entry index is not exactly decision + one grid row")
    if np.any(exit_indices[support] - entry_indices[support] != HORIZON_STEPS):
        raise ProtocolViolation("exit index is not exactly entry + 600 seconds")
    if np.any(entry_ts[support] - frozen.timestamp_us[support] != ENTRY_DELAY_US):
        raise ProtocolViolation("entry timestamp latency mismatch")
    if np.any(exit_ts[support] - entry_ts[support] != HOLDING_DURATION_US):
        raise ProtocolViolation("holding-duration timestamp mismatch")

    X_direction = frozen.X_R[:, DIRECTION_INDICES].astype(float, copy=True)
    if np.any(~np.isfinite(X_direction[support])):
        raise ProtocolViolation("direction features narrowed parent valid_R support")
    long_gross = np.asarray(outcomes["long_gross_bps"], dtype=float)
    short_gross = np.asarray(outcomes["short_gross_bps"], dtype=float)
    return DirectionDay(
        day=day.day,
        timestamp_us=frozen.timestamp_us.astype(np.int64, copy=False),
        entry_timestamp_us=entry_ts,
        exit_timestamp_us=exit_ts,
        X_direction=X_direction,
        rv_30m_bps=frozen.X_R[:, VOL_INDEX].astype(float, copy=False),
        ret_10m_bps=X_direction[:, RET_10M_INDEX],
        opportunity_label=frozen.y.astype(np.int8, copy=False),
        long_preferred=(long_gross > short_gross).astype(np.int8),
        long_gross_bps=long_gross,
        short_gross_bps=short_gross,
        common_support=support,
        parent_support_exact=parent_support_exact,
    )


def candidate_b_direction(ret_10m_bps: np.ndarray) -> np.ndarray:
    return np.asarray(ret_10m_bps, dtype=float) >= 0.0


def candidate_c_direction(ret_10m_bps: np.ndarray) -> np.ndarray:
    return ~candidate_b_direction(ret_10m_bps)


def direction_label(long_bps: np.ndarray, short_bps: np.ndarray) -> np.ndarray:
    return (np.asarray(long_bps, float) > np.asarray(short_bps, float)).astype(np.int8)


def training_probability_trigger(training_probabilities: np.ndarray) -> float:
    probabilities = np.asarray(training_probabilities, dtype=float)
    if probabilities.ndim != 1 or len(probabilities) == 0:
        raise SelectionReadinessFailure("empty training probabilities")
    if np.any(~np.isfinite(probabilities)):
        raise ProtocolViolation("non-finite training probability")
    return float(
        np.quantile(
            probabilities,
            OPPORTUNITY_QUANTILE,
            method=OPPORTUNITY_QUANTILE_METHOD,
        )
    )


def _fit_readiness_logistic(
    X: np.ndarray,
    y: np.ndarray,
    *,
    context: str,
) -> FixedLogistic:
    matrix = np.asarray(X, dtype=float)
    raw_labels = np.asarray(y)
    if matrix.ndim != 2:
        raise ProtocolViolation(f"{context}: training matrix must be two-dimensional")
    if raw_labels.ndim != 1 or len(matrix) != len(raw_labels):
        raise ProtocolViolation(f"{context}: training matrix/label shape mismatch")
    if np.any(~np.isfinite(matrix)):
        raise ProtocolViolation(f"{context}: non-finite training feature")
    try:
        numeric_labels = raw_labels.astype(float, copy=False)
    except (TypeError, ValueError) as error:
        raise ProtocolViolation(f"{context}: training labels must be numeric") from error
    if np.any(~np.isfinite(numeric_labels)):
        raise ProtocolViolation(f"{context}: non-finite training label")
    if np.any((numeric_labels != 0.0) & (numeric_labels != 1.0)):
        raise ProtocolViolation(
            f"{context}: training labels must be exactly binary {{0,1}}"
        )
    labels = numeric_labels.astype(np.int8, copy=False)
    if len(labels) < 2 or np.unique(labels).size != 2:
        raise SelectionReadinessFailure(
            f"{context}: training labels lack both classes"
        )
    return FixedLogistic().fit(matrix, labels)


def profit_factor_diagnostic(net_bps: np.ndarray, *, prefix: str = "") -> dict[str, Any]:
    values = np.asarray(net_bps, dtype=float)
    if np.any(~np.isfinite(values)):
        raise ProtocolViolation("non-finite net return in profit-factor calculation")
    gains = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    key = f"{prefix}profit_factor"
    if losses > 0:
        return {
            key: float(gains / losses),
            f"{key}_infinite": False,
            f"{key}_undefined": False,
        }
    if gains > 0:
        return {key: None, f"{key}_infinite": True, f"{key}_undefined": False}
    return {key: None, f"{key}_infinite": False, f"{key}_undefined": True}


def _profit_factor_order_value(diagnostic: Mapping[str, Any], *, prefix: str = "") -> float:
    key = f"{prefix}profit_factor"
    if diagnostic[f"{key}_infinite"]:
        return math.inf
    if diagnostic[f"{key}_undefined"]:
        return -math.inf
    return float(diagnostic[key])


def maximum_drawdown_bps(net_bps: np.ndarray) -> float:
    values = np.asarray(net_bps, dtype=float)
    if np.any(~np.isfinite(values)):
        raise ProtocolViolation("non-finite net return in drawdown calculation")
    if len(values) == 0:
        return 0.0
    cumulative = np.concatenate(([0.0], np.cumsum(values)))
    peaks = np.maximum.accumulate(cumulative)
    return float(np.max(peaks - cumulative))


def execute_nonoverlapping(
    day: DirectionDay,
    opportunity_probability: np.ndarray,
    trigger: float,
    choose_long: np.ndarray,
) -> ExecutionEvaluation:
    probability = np.asarray(opportunity_probability, dtype=float)
    directions = np.asarray(choose_long, dtype=bool)
    if probability.shape != day.common_support.shape or directions.shape != probability.shape:
        raise ValueError("execution inputs must match decision rows")
    eligible = day.common_support & np.isfinite(probability) & (probability >= trigger)
    eligible_indices = np.flatnonzero(eligible)
    gross: list[float] = []
    net: list[float] = []
    stress: list[float] = []
    entries: list[int] = []
    exits: list[int] = []
    long_count = 0
    ignored = 0
    open_until_us: int | None = None
    for index in eligible_indices.tolist():
        decision_us = int(day.timestamp_us[index])
        if open_until_us is not None and decision_us < open_until_us:
            ignored += 1
            continue
        entry_us = int(day.entry_timestamp_us[index])
        exit_us = int(day.exit_timestamp_us[index])
        if entry_us - decision_us != ENTRY_DELAY_US:
            raise ProtocolViolation("executed entry is not t+250ms")
        if exit_us - entry_us != HOLDING_DURATION_US:
            raise ProtocolViolation("executed hold is not exactly 600s")
        selected_gross = (
            day.long_gross_bps[index] if directions[index] else day.short_gross_bps[index]
        )
        if not math.isfinite(float(selected_gross)):
            raise ProtocolViolation("non-finite executable return on common support")
        value = float(selected_gross)
        gross.append(value)
        net.append(value - PRIMARY_COST_BPS)
        stress.append(value - STRESS_COST_BPS)
        entries.append(entry_us)
        exits.append(exit_us)
        long_count += int(directions[index])
        open_until_us = exit_us

    net_array = np.asarray(net, dtype=float)
    entry_array = np.asarray(entries, dtype=np.int64)
    exit_array = np.asarray(exits, dtype=np.int64)
    executed = len(net)
    no_overlap = bool(executed < 2 or np.all(entry_array[1:] >= exit_array[:-1]))
    accounting = bool(len(eligible_indices) == executed + ignored)
    exact_holds = bool(
        executed == 0 or np.all(exit_array - entry_array == HOLDING_DURATION_US)
    )
    if not accounting or not no_overlap or not exact_holds:
        raise ProtocolViolation("non-overlap execution accounting/timing mismatch")
    exposure = float((executed * HOLDING_DURATION_US) / DAY_US)
    if not math.isfinite(exposure) or not 0.0 <= exposure <= 1.0:
        raise ProtocolViolation("invalid exposure fraction")
    metrics: dict[str, Any] = {
        "eligible_signal_count": int(len(eligible_indices)),
        "executed_nonoverlapping_trade_count": int(executed),
        "ignored_eligible_signals_while_open": int(ignored),
        "long_count": int(long_count),
        "short_count": int(executed - long_count),
        "gross_total_bps": float(np.sum(gross)),
        "net_total_bps_at_14bp": float(np.sum(net_array)),
        "mean_net_bps_per_trade": float(np.mean(net_array)) if executed else None,
        "median_net_bps_per_trade": float(np.median(net_array)) if executed else None,
        "win_rate": float(np.mean(net_array > 0)) if executed else None,
        **profit_factor_diagnostic(net_array),
        "maximum_drawdown_cumulative_net_bps": maximum_drawdown_bps(net_array),
        "exposure_fraction": exposure,
        "stress_total_bps_at_20bp": float(np.sum(stress)),
        "nonoverlap_accounting_consistent": accounting,
        "no_position_overlap": no_overlap,
        "executed_trade_timing_exact": exact_holds,
    }
    return ExecutionEvaluation(metrics, net_array, entry_array, exit_array)


def _fit_fold(train_days: Sequence[DirectionDay], validation: DirectionDay) -> dict[str, Any]:
    train_rv = _concat(train_days, "rv_30m_bps").reshape(-1, 1)
    train_opportunity_y = _concat(train_days, "opportunity_label").astype(np.int8)
    opportunity_model = _fit_readiness_logistic(
        train_rv,
        train_opportunity_y,
        context="fold opportunity model",
    )
    training_probabilities = opportunity_model.predict_proba(train_rv)
    trigger = training_probability_trigger(training_probabilities)

    train_direction_X = _concat(train_days, "X_direction")
    train_direction_y = _concat(train_days, "long_preferred").astype(np.int8)
    direction_model = _fit_readiness_logistic(
        train_direction_X,
        train_direction_y,
        context="fold Candidate A direction model",
    )
    support = validation.common_support
    validation_probability = np.full(len(support), np.nan, dtype=float)
    validation_probability[support] = opportunity_model.predict_proba(
        validation.rv_30m_bps[support].reshape(-1, 1)
    )
    a_probability = np.full(len(support), np.nan, dtype=float)
    a_probability[support] = direction_model.predict_proba(validation.X_direction[support])
    choices = {
        "A": a_probability >= DIRECTION_THRESHOLD,
        "B": candidate_b_direction(validation.ret_10m_bps),
        "C": candidate_c_direction(validation.ret_10m_bps),
    }
    evaluations = {
        candidate: execute_nonoverlapping(
            validation, validation_probability, trigger, choices[candidate]
        )
        for candidate in CANDIDATES
    }
    return {
        "trigger_threshold": trigger,
        "trigger_quantile": OPPORTUNITY_QUANTILE,
        "trigger_quantile_method": OPPORTUNITY_QUANTILE_METHOD,
        "trigger_source": "training_probabilities_only",
        "validation_probabilities_used_for_trigger": False,
        "training_probability_count": int(len(training_probabilities)),
        "validation_common_support_count": int(np.sum(support)),
        "candidates": evaluations,
    }


def select_candidate(folds: Sequence[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    if len(folds) != 4:
        raise SelectionReadinessFailure("candidate selection requires exactly four folds")
    diagnostics: dict[str, Any] = {}
    keys: dict[str, tuple[float, int, float, float, int]] = {}
    simplicity = {name: len(SIMPLICITY_ORDER) - i for i, name in enumerate(SIMPLICITY_ORDER)}
    for candidate in CANDIDATES:
        evaluations = [fold["candidates"][candidate] for fold in folds]
        if any(item.metrics["executed_nonoverlapping_trade_count"] == 0 for item in evaluations):
            raise SelectionReadinessFailure(
                f"candidate {candidate} has a validation fold with zero executed trades"
            )
        per_fold = [
            float(item.metrics["net_total_bps_at_14bp"])
            / int(item.metrics["executed_nonoverlapping_trade_count"])
            for item in evaluations
        ]
        pooled = np.concatenate([item.net_bps for item in evaluations])
        pooled_pf = profit_factor_diagnostic(pooled, prefix="pooled_")
        positive_folds = int(sum(item.metrics["net_total_bps_at_14bp"] > 0 for item in evaluations))
        pooled_drawdown = maximum_drawdown_bps(pooled)
        primary = float(np.median(np.asarray(per_fold, dtype=float)))
        diagnostics[candidate] = {
            "median_validation_fold_net_bps_per_trade": primary,
            "validation_fold_net_bps_per_trade": per_fold,
            "positive_total_net_folds": positive_folds,
            **pooled_pf,
            "pooled_maximum_drawdown_bps": pooled_drawdown,
            "simplicity_rank": SIMPLICITY_ORDER.index(candidate) + 1,
            "profit_factor_tie_break_semantics": (
                "positive gain with zero loss ranks as +infinity; zero-gain/zero-loss "
                "is undefined and ranks below finite values"
            ),
        }
        keys[candidate] = (
            primary,
            positive_folds,
            _profit_factor_order_value(pooled_pf, prefix="pooled_"),
            -pooled_drawdown,
            simplicity[candidate],
        )
    selected = max(CANDIDATES, key=lambda name: keys[name])
    return selected, {
        "primary_statistic": "median validation-fold net_bps_per_trade",
        "tie_break_order": [
            "more positive-total-net folds",
            "higher pooled profit factor",
            "lower pooled maximum drawdown bps",
            "simpler candidate B then C then A",
        ],
        "candidates": diagnostics,
        "selected_candidate": selected,
    }


def _model_record(model: FixedLogistic) -> dict[str, Any]:
    return {
        "scaler_mean": model.scaler.mean_.tolist(),
        "scaler_scale": model.scaler.scale_.tolist(),
        "coefficient": model.model.coef_[0].tolist(),
        "intercept": float(model.model.intercept_[0]),
        "classes": model.model.classes_.tolist(),
        "hyperparameters": scientific_configuration()["model"],
    }


def historical_selection_core(days: Mapping[date, DirectionDay]) -> CoreSelection:
    if tuple(sorted(days)) != HISTORICAL_DAYS:
        raise ProtocolViolation("historical day mapping is not exact Jan-Jul calendar")
    public_folds: list[dict[str, Any]] = []
    private_folds: list[dict[str, Any]] = []
    for fold_index, (train_dates, validation_date) in enumerate(FOLDS, start=1):
        fitted = _fit_fold([days[day] for day in train_dates], days[validation_date])
        private_folds.append(fitted)
        public_folds.append(
            {
                "fold": fold_index,
                "train_dates": [day.isoformat() for day in train_dates],
                "validation_date": validation_date.isoformat(),
                "trigger_threshold": fitted["trigger_threshold"],
                "trigger_quantile": fitted["trigger_quantile"],
                "trigger_quantile_method": fitted["trigger_quantile_method"],
                "trigger_source": fitted["trigger_source"],
                "validation_probabilities_used_for_trigger": fitted[
                    "validation_probabilities_used_for_trigger"
                ],
                "training_probability_count": fitted["training_probability_count"],
                "validation_common_support_count": fitted["validation_common_support_count"],
                "candidates": {
                    candidate: fitted["candidates"][candidate].metrics
                    for candidate in CANDIDATES
                },
            }
        )
    selected, diagnostic = select_candidate(private_folds)
    all_days = [days[day] for day in HISTORICAL_DAYS]
    all_rv = _concat(all_days, "rv_30m_bps").reshape(-1, 1)
    all_y = _concat(all_days, "opportunity_label").astype(np.int8)
    opportunity_model = _fit_readiness_logistic(
        all_rv,
        all_y,
        context="final Jan-Jul opportunity model",
    )
    final_trigger = training_probability_trigger(opportunity_model.predict_proba(all_rv))
    final_models: dict[str, Any] = {
        "opportunity_model": _model_record(opportunity_model),
        "final_historical_probability_trigger": final_trigger,
        "trigger_source": "full_Jan_Jul_training_probabilities_only",
        "trigger_quantile": OPPORTUNITY_QUANTILE,
        "trigger_quantile_method": OPPORTUNITY_QUANTILE_METHOD,
        "selected_direction_candidate": selected,
    }
    if selected == "A":
        model = _fit_readiness_logistic(
            _concat(all_days, "X_direction"),
            _concat(all_days, "long_preferred").astype(np.int8),
            context="final Jan-Jul Candidate A direction model",
        )
        final_models["direction_model"] = _model_record(model)
    else:
        final_models["direction_rule"] = (
            "ret_10m_bps >= 0 -> LONG" if selected == "B" else "ret_10m_bps >= 0 -> SHORT"
        )
    return CoreSelection(
        dict(days), public_folds, private_folds, selected, diagnostic, final_models
    )


def _static_invariants(
    *, references_verified: bool, provenance_verified: bool, protocol_clean: bool
) -> dict[str, bool]:
    execution = scientific_configuration()["execution"]
    values = {
        "no_protocol_violation_detected": bool(protocol_clean),
        "preregistration_sha_verified": bool(references_verified),
        "parent_result_sha_and_status_verified": bool(references_verified),
        "historical_input_provenance_verified": bool(provenance_verified),
        "exact_jan_jul_historical_calendar": bool(
            HISTORICAL_DAY_STRINGS
            == tuple(f"2026-{month:02d}-01" for month in range(1, 8))
        ),
        "exactly_four_expanding_folds": bool(
            len(FOLDS) == 4
            and all(
                train == HISTORICAL_DAYS[: index + 3]
                and validation == HISTORICAL_DAYS[index + 3]
                for index, (train, validation) in enumerate(FOLDS)
            )
        ),
        "candidate_set_exactly_A_B_C": bool(CANDIDATES == ("A", "B", "C")),
        "opportunity_feature_exactly_rv_30m_bps": bool(OPPORTUNITY_FEATURE == "rv_30m_bps"),
        "direction_feature_list_exact": bool(
            DIRECTION_FEATURE_NAMES
            == (
                "ret_1m_bps", "ret_3m_bps", "ret_5m_bps", "ret_10m_bps",
                "ret_30m_bps", "rv_30m_bps", "spread_bps",
            )
        ),
        **frozen_timing_invariants(),
        "primary_cost_exactly_14bp": bool(PRIMARY_COST_BPS == 14.0),
        "stress_cost_exactly_20bp": bool(STRESS_COST_BPS == 20.0),
        "trigger_quantile_exactly_0_90_higher": bool(
            OPPORTUNITY_QUANTILE == 0.90 and OPPORTUNITY_QUANTILE_METHOD == "higher"
        ),
        "aug30_analytically_opened_false": bool(AUG30_ANALYTICALLY_OPENED is False),
        "sep01_or_later_opened_false": bool(SEP01_OR_LATER_OPENED is False),
        "network_accessed_false": bool(NETWORK_ACCESSED is False),
        "no_leverage_stop_loss_take_profit_sizing_or_posthoc_filter": bool(
            execution["leverage"] is False
            and execution["stop_loss"] is False
            and execution["take_profit"] is False
            and execution["position_sizing_optimization"] is False
            and execution["post_hoc_filtering"] is False
        ),
    }
    validate_builtin_bool_invariants(values)
    return values


def build_readiness_invariants(
    core: CoreSelection | None,
    *,
    references_verified: bool,
    provenance_verified: bool,
    protocol_clean: bool,
    pipeline_completed: bool,
) -> dict[str, bool]:
    folds = core.folds if core is not None else []
    metrics = [item for fold in folds for item in fold.get("candidates", {}).values()]
    evaluated = bool(pipeline_completed and core is not None)
    values = _static_invariants(
        references_verified=references_verified,
        provenance_verified=provenance_verified,
        protocol_clean=protocol_clean,
    )
    values.update(
        {
            "execution_invariants_evaluated": bool(evaluated),
            "historical_common_support_equals_parent_valid_R": bool(
                evaluated
                and tuple(sorted(core.days)) == HISTORICAL_DAYS
                and all(day.parent_support_exact is True for day in core.days.values())
            ),
            "every_fold_trigger_training_probabilities_only": bool(
                evaluated
                and len(folds) == 4
                and all(fold.get("trigger_source") == "training_probabilities_only" for fold in folds)
            ),
            "no_validation_derived_threshold": bool(
                evaluated
                and len(folds) == 4
                and all(fold.get("validation_probabilities_used_for_trigger") is False for fold in folds)
            ),
            "nonoverlap_accounting_consistent": bool(
                evaluated
                and bool(metrics)
                and all(
                    item.get("eligible_signal_count")
                    == item.get("executed_nonoverlapping_trade_count")
                    + item.get("ignored_eligible_signals_while_open")
                    and item.get("nonoverlap_accounting_consistent") is True
                    for item in metrics
                )
            ),
            "no_position_overlap": bool(
                evaluated and bool(metrics)
                and all(item.get("no_position_overlap") is True for item in metrics)
            ),
            "exposure_fraction_finite_and_bounded": bool(
                evaluated
                and bool(metrics)
                and all(
                    type(item.get("exposure_fraction")) is float
                    and math.isfinite(item["exposure_fraction"])
                    and 0.0 <= item["exposure_fraction"] <= 1.0
                    for item in metrics
                )
            ),
            "executed_trade_timing_exact": bool(
                evaluated and bool(metrics)
                and all(item.get("executed_trade_timing_exact") is True for item in metrics)
            ),
            "historical_selection_pipeline_completed": bool(pipeline_completed),
            "exactly_one_candidate_selected": bool(
                evaluated and core.selected_candidate in CANDIDATES
            ),
            "all_four_folds_scored_for_each_candidate": bool(
                evaluated
                and len(folds) == 4
                and all(tuple(fold.get("candidates", {}).keys()) == CANDIDATES for fold in folds)
            ),
        }
    )
    validate_builtin_bool_invariants(values)
    return values


def invariant_groups() -> dict[str, list[str]]:
    return {
        "static_protocol_and_provenance": list(STATIC_INVARIANT_NAMES),
        "evaluated_execution": ["execution_invariants_evaluated", *EXECUTION_INVARIANT_NAMES],
        "readiness": list(READINESS_INVARIANT_NAMES),
    }


def adjudicate_readiness(invariants: Mapping[str, Any]) -> str:
    try:
        checked = validate_builtin_bool_invariants(invariants)
    except Exception as error:
        raise ProtocolViolation("invalid invariant type") from error
    required = set(STATIC_INVARIANT_NAMES) | set(EXECUTION_INVARIANT_NAMES) | set(
        READINESS_INVARIANT_NAMES
    ) | {"execution_invariants_evaluated"}
    if set(checked) != required:
        raise ProtocolViolation("invariant names differ from frozen readiness schema")
    if not adjudicate_invariants({name: checked[name] for name in STATIC_INVARIANT_NAMES}):
        return INVALID_STATUS
    if not checked["historical_selection_pipeline_completed"]:
        return FAIL_STATUS
    if not checked["execution_invariants_evaluated"]:
        return INVALID_STATUS
    if not adjudicate_invariants({name: checked[name] for name in EXECUTION_INVARIANT_NAMES}):
        return INVALID_STATUS
    return (
        PASS_STATUS
        if adjudicate_invariants({name: checked[name] for name in READINESS_INVARIANT_NAMES})
        else FAIL_STATUS
    )


def _git(workspace: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=workspace, capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


def _is_ancestor(workspace: Path, ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise ProtocolViolation(
            f"git ancestry check failed with return code {completed.returncode}: "
            f"{completed.stderr.strip()}"
        )
    return bool(completed.returncode == 0)


def _input_manifest_with_roles(manifest: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_day = {str(row["day"]): row for row in manifest}
    if tuple(sorted(by_day)) != HISTORICAL_DAY_STRINGS:
        raise ProtocolViolation("historical provenance manifest calendar mismatch")
    records: list[dict[str, Any]] = []
    for day in HISTORICAL_DAYS:
        row = dict(by_day[day.isoformat()])
        row["split_roles"] = [
            {
                "fold": index,
                "role": (
                    "train" if day in train else "validation" if day == validation else "unused"
                ),
            }
            for index, (train, validation) in enumerate(FOLDS, start=1)
        ]
        records.append(row)
    return records


def _load_historical_days(manifest: Sequence[Mapping[str, Any]]) -> dict[date, DirectionDay]:
    rows = {str(row["day"]): row for row in manifest}
    result: dict[date, DirectionDay] = {}
    for day in HISTORICAL_DAYS:
        expected = authorized_feature_path(day)
        if Path(str(rows[day.isoformat()]["path"])) != expected:
            raise ProtocolViolation("historical manifest path differs from frozen explicit path")
        result[day] = build_direction_day(_load_day(expected, day))
    return result


def _public_core(core: CoreSelection) -> dict[str, Any]:
    return {
        "folds": core.folds,
        "candidate_selection": core.candidate_selection,
        "selected_candidate": core.selected_candidate,
        "final_models": core.final_models,
    }


def _fresh_output(output: Path) -> Path:
    part = Path(f"{output}.part")
    if output.exists():
        raise FileExistsError(f"result already exists: {output}")
    if part.exists():
        raise FileExistsError(f"partial result already exists: {part}")
    output.parent.mkdir(parents=True, exist_ok=True)
    return part


def _encode_payload(payload: Mapping[str, Any]) -> bytes:
    validate_builtin_bool_invariants(payload["invariants"])
    normalized = normalize_json_safe(payload)
    return (
        json.dumps(normalized, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def _write_once(output: Path, payload: Mapping[str, Any]) -> str:
    part = _fresh_output(output)
    encoded = _encode_payload(payload)
    descriptor = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(part, output)
    return hashlib.sha256(encoded).hexdigest()


def run_historical_selection(
    workspace: Path,
    frozen_commit: str,
    output: Path,
    *,
    argv: Sequence[str] | None = None,
) -> RunWriteResult:
    _fresh_output(output)
    started = _utc_now()
    run_id = f"CODEX-RUN-EXP026-{started.replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:8]}"
    config = scientific_configuration()
    references: dict[str, Any] | None = None
    manifest: list[dict[str, Any]] = []
    core: CoreSelection | None = None
    references_verified = False
    provenance_verified = False
    protocol_clean = True
    pipeline_completed = False
    failure_reason: str | None = None
    status = INVALID_STATUS
    try:
        assert_frozen_workspace(workspace, frozen_commit)
        if not _is_ancestor(workspace, PREREGISTRATION_COMMIT, frozen_commit):
            raise ProtocolViolation("preregistration commit is not an ancestor")
        references = verify_frozen_references(workspace)
        references_verified = True
        manifest = _input_manifest_with_roles(
            _verify_training_inputs(AUTHORIZED_FEATURE_ROOT, workspace)
        )
        provenance_verified = True
        core = historical_selection_core(_load_historical_days(manifest))
        pipeline_completed = True
    except SelectionReadinessFailure as error:
        failure_reason = str(error)
    except Exception as error:
        protocol_clean = False
        failure_reason = f"{type(error).__name__}: {error}"

    invariants = build_readiness_invariants(
        core,
        references_verified=references_verified,
        provenance_verified=provenance_verified,
        protocol_clean=protocol_clean,
        pipeline_completed=pipeline_completed,
    )
    status = adjudicate_readiness(invariants)
    tracked_dirty = bool(_git(workspace, "status", "--porcelain", "--untracked-files=no"))
    payload: dict[str, Any] = {
        "run_id": run_id,
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "failure_reason": failure_reason,
        "started_at_utc": started,
        "finished_at_utc": _utc_now(),
        "execution_mode": "historical-selection",
        "command_argv": list(argv if argv is not None else sys.argv),
        "frozen_git_commit": frozen_commit,
        "tracked_tree_dirty": tracked_dirty,
        "environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "numpy_version": np.__version__,
            "scikit_learn_version": sklearn.__version__,
        },
        "references": references,
        "scientific_configuration": config,
        "scientific_configuration_sha256": canonical_sha256(config),
        "historical_input_manifest": manifest,
        "feature_columns": {
            "opportunity": [OPPORTUNITY_FEATURE],
            "direction": list(DIRECTION_FEATURE_NAMES),
        },
        "model_hyperparameters_and_seed": config["model"],
        "execution_semantics": {
            "latency_us": ENTRY_DELAY_US,
            "entry": "decision t plus exactly one 250ms row; executable ask LONG/bid SHORT",
            "exit": "entry plus exactly 600 seconds; executable bid LONG/ask SHORT",
            "fees_bps_round_trip": 10.0,
            "slippage_bps_per_side": 2.0,
            "primary_incremental_cost_bps": PRIMARY_COST_BPS,
            "stress_incremental_cost_bps": STRESS_COST_BPS,
            "queue_model": "single flat position; signals before actual exit are ignored",
        },
        "historical_selection": _public_core(core) if core is not None else None,
        "invariants": invariants,
        "invariant_groups": invariant_groups(),
        "invariant_adjudication": {
            "static_false": INVALID_STATUS,
            "clean_incomplete_pipeline": FAIL_STATUS,
            "evaluated_execution_false": INVALID_STATUS,
            "readiness_false_after_evaluation": FAIL_STATUS,
            "all_required_true": PASS_STATUS,
        },
        "sealed_future_data_assertions": {
            "AUG30_ANALYTICALLY_OPENED": AUG30_ANALYTICALLY_OPENED,
            "SEP01_OR_LATER_OPENED": SEP01_OR_LATER_OPENED,
            "NETWORK_ACCESSED": NETWORK_ACCESSED,
        },
        "output_sha256": None,
        "output_sha256_semantics": "computed and reported after atomic write; not self-embedded",
    }
    digest = _write_once(output, payload)
    return RunWriteResult(normalize_json_safe(payload), digest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CODEX-EXP-026-P0 historical readiness")
    parser.add_argument("--mode", choices=("historical-selection",), required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    effective_argv = list(argv) if argv is not None else sys.argv[1:]
    result = run_historical_selection(
        args.workspace, args.frozen_commit, args.output, argv=effective_argv
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "output_sha256": result.output_sha256,
                "status": result.payload["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if result.payload["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

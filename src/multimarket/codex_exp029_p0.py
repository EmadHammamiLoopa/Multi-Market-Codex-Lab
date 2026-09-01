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
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import sklearn
from sklearn.metrics import average_precision_score, roc_auc_score

from .codex_exp004_headroom import (
    ENTRY_STEPS,
    GRID_US,
    executable_fixed_horizon,
)
from .codex_exp004_p1 import (
    DECISION_STEP_ROWS,
    HORIZON_S as FROZEN_HORIZON_S,
    LABEL_THRESHOLD_BPS as FROZEN_LABEL_THRESHOLD_BPS,
    R_FEATURE_NAMES,
    FixedLogistic,
    build_day_dataset,
)
from .codex_exp022_p1 import _verify_training_inputs as _verify_parent_training_inputs
from .codex_exp023_p0 import normalize_json_safe, validate_builtin_bool_invariants
from .codex_research import canonical_sha256, sha256_file
from .v23_phase0dl_score import DayData, _load_day


EXPERIMENT_ID = "CODEX-EXP-029-P0"
PASS_STATUS = "CAUSAL_RANK_OPPORTUNITY_POLICY_READY_FOR_DIRECTION_DEVELOPMENT"
FAIL_STATUS = "FAIL_CAUSAL_RANK_OPPORTUNITY_POLICY_NOT_READY"
INVALID_STATUS = "INVALID"

PREREG_REL = "docs/CODEX_EXP029_P0_CAUSAL_RANK_OPPORTUNITY_READINESS.md"
PREREG_SHA256 = "1a75f35578babd2afc251945f2d332648b0e581ac1bd3dc312e42a6c80cd401a"
PREREG_COMMIT = "04cdbc643a5207ec9105ae82ab5658bb16b0169d"

EXP024_RESULT_REL = (
    "evidence/codex/exp024_p1_fresh_prospective_ranking_confirmation/"
    "PROSPECTIVE_RANKING_CONFIRMATION.json"
)
EXP024_IMPLEMENTATION_COMMIT = "cdffc6d7556a2258e59f3a63e0e11419b47e5e5c"
EXP024_RESULT_COMMIT = "4669be4234b808286108c288f7a6eb7b3742f268"
EXP024_RESULT_SHA256 = "0fda20d127e51e8ad792c6b949889f88b59e75ab98b437fd04ead285970e5c10"
EXP024_EXPERIMENT_ID = "CODEX-EXP-024-P1"
EXP024_STATUS = "PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED"

EXP028_RESULT_REL = (
    "evidence/codex/exp028_p0_abstention_aware_direction_readiness/"
    "HISTORICAL_SELECTION.json"
)
EXP028_RESULT_COMMIT = "09e04a5cd6203110bdfb0e774b09e79242e542db"
EXP028_RESULT_SHA256 = "32053a61b7a7e181857d9838d902551b4249f12e96fa1af4967cd18aa28385e1"
EXP028_EXPERIMENT_ID = "CODEX-EXP-028-P0"
EXP028_STATUS = "FAIL_ABSTENTION_AWARE_DIRECTION_PIPELINE_NOT_READY"

SYMBOL = "BTCUSDT"
HISTORICAL_DAYS = tuple(date(2026, month, 1) for month in range(1, 8))
HISTORICAL_DAY_STRINGS = tuple(day.isoformat() for day in HISTORICAL_DAYS)
AUTHORIZED_FEATURE_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/v23/phase0dl_features250"
)
FOLDS = (
    (HISTORICAL_DAYS[:3], HISTORICAL_DAYS[3]),
    (HISTORICAL_DAYS[:4], HISTORICAL_DAYS[4]),
    (HISTORICAL_DAYS[:5], HISTORICAL_DAYS[5]),
    (HISTORICAL_DAYS[:6], HISTORICAL_DAYS[6]),
)

OPPORTUNITY_FEATURE = "rv_30m_bps"
VOL_INDEX = R_FEATURE_NAMES.index(OPPORTUNITY_FEATURE)
REFERENCE_WINDOW_SIZE = 1399
GATE_QUANTILE = 0.90
QUANTILE_METHOD = "higher"
DECISION_STEP_S = 60
ENTRY_DELAY_MS = 250
HORIZON_S = 600
LABEL_THRESHOLD_BPS = 24.0
MIN_SUPPORT_N = 1200
MIN_POSITIVES = 10
MIN_NEGATIVES = 100
NULL_QUANTILE = 0.95
NULL_SHIFT_STEP_ROWS = 30

ENTRY_DELAY_US = ENTRY_DELAY_MS * 1_000
HOLDING_DURATION_US = HORIZON_S * 1_000_000
DECISION_STEP_US = DECISION_STEP_S * 1_000_000
DAY_US = 86_400_000_000
HORIZON_STEPS = HOLDING_DURATION_US // GRID_US

AUG30_ANALYTICALLY_OPENED = False
SEP01_OR_LATER_OPENED = False
NETWORK_ACCESSED = False
DIRECTION_SCORED = False
PNL_SCORED = False
LEVERAGE_SCORED = False

PRIMARY_GATE_NAMES = (
    "gate_01_all_protocol_and_causality_invariants_pass",
    "gate_02_all_four_validation_folds_processed",
    "gate_03_every_fold_minimum_support_satisfied",
    "gate_04_pooled_causal_rank_auc_at_least_0_60",
    "gate_05_pooled_causal_rank_ap_over_prevalence_at_least_1_50",
    "gate_06_pooled_causal_gate_lift_at_least_1_50",
    "gate_07_at_least_three_fold_gate_lifts_gt_1",
    "gate_08_observed_auc_strictly_above_temporal_null_q95",
    "gate_09_auc_empirical_p_at_most_0_05",
    "gate_10_observed_ap_strictly_above_temporal_null_q95",
    "gate_11_ap_empirical_p_at_most_0_05",
    "gate_12_at_least_three_active_folds",
)

STATIC_INVARIANT_NAMES = (
    "no_protocol_violation_detected",
    "preregistration_sha_verified",
    "exp024_result_sha_and_status_verified",
    "exp028_result_sha_and_status_verified",
    "frozen_lineage_ancestry_verified",
    "historical_input_provenance_verified",
    "exact_jan_jul_historical_calendar",
    "exactly_four_expanding_folds",
    "opportunity_feature_exactly_rv_30m_bps",
    "opportunity_model_configuration_exact",
    "decision_step_exactly_60s",
    "entry_delay_exactly_250ms",
    "holding_duration_exactly_600s",
    "opportunity_label_threshold_exactly_24bp",
    "reference_window_exactly_1399",
    "gate_quantile_exactly_0_90_higher",
    "temporal_null_exactly_fold_preserving_step_30",
    "aug30_analytically_opened_false",
    "sep01_or_later_opened_false",
    "network_accessed_false",
    "direction_scored_false",
    "pnl_scored_false",
    "leverage_scored_false",
    "no_arbitrary_data_or_network_interface",
)

EVALUATED_INVARIANT_NAMES = (
    "historical_pipeline_evaluated",
    "historical_common_support_equals_parent_valid_R",
    "validation_rows_unique_and_chronological",
    "training_models_fit_on_training_rows_only",
    "initial_reference_is_last_1399_training_scores",
    "reference_length_always_1399",
    "current_score_excluded_before_decision",
    "future_scores_never_enter_past_references",
    "eligibility_uses_probability_vs_causal_threshold",
    "fold_preserving_temporal_null",
    "same_shift_applied_to_every_fold",
    "occupancy_accounting_consistent",
    "occupancy_has_no_overlap",
    "occupancy_timing_exact",
    "result_payload_json_safe",
    "one_shot_preconditions_verified",
)


class ProtocolViolation(RuntimeError):
    """A frozen design, provenance, causality, or sealed-data rule failed."""


class DevelopmentReadinessFailure(RuntimeError):
    """A clean historical support/readiness condition could not be satisfied."""


@dataclass(frozen=True)
class OpportunityDay:
    day: date
    timestamp_us: np.ndarray
    rv_30m_bps: np.ndarray
    opportunity_label: np.ndarray
    common_support: np.ndarray
    parent_support_exact: bool


@dataclass(frozen=True)
class CausalRankResult:
    rank: np.ndarray
    threshold: np.ndarray
    eligible: np.ndarray
    initial_reference: np.ndarray
    final_reference: np.ndarray
    reference_lengths: np.ndarray


@dataclass(frozen=True)
class OccupancyResult:
    eligible_signal_count: int
    executed_nonoverlapping_opportunity_count: int
    ignored_eligible_signals_while_occupied: int
    exposure_fraction: float
    state: str
    entry_timestamp_us: np.ndarray
    exit_timestamp_us: np.ndarray
    accounting_consistent: bool
    no_position_overlap: bool
    timing_exact: bool


@dataclass(frozen=True)
class FoldEvaluation:
    fold: int
    train_dates: tuple[str, ...]
    validation_date: str
    training_probability_count: int
    validation_common_support_count: int
    timestamp_us: np.ndarray
    label: np.ndarray
    raw_probability: np.ndarray
    causal_rank: np.ndarray
    threshold: np.ndarray
    eligible: np.ndarray
    causal_rank_metrics: dict[str, Any]
    raw_probability_metrics: dict[str, Any]
    causal_gate_metrics: dict[str, Any]
    occupancy: OccupancyResult
    support_sufficient: bool
    threshold_summary: dict[str, float]
    model_record: dict[str, Any]
    causal_invariants: dict[str, bool]


@dataclass(frozen=True)
class DevelopmentCore:
    days: dict[date, OpportunityDay]
    folds: tuple[FoldEvaluation, ...]
    pooled_causal_rank_metrics: dict[str, Any]
    pooled_raw_probability_metrics: dict[str, Any]
    pooled_causal_gate_metrics: dict[str, Any]
    raw_score_continuity: dict[str, float]
    temporal_null: dict[str, Any]
    active_fold_count: int
    total_eligible_signals: int
    total_executed_nonoverlapping_opportunities: int
    oof_records: list[dict[str, Any]]


@dataclass(frozen=True)
class RunWriteResult:
    payload: dict[str, Any]
    output_sha256: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def model_configuration() -> dict[str, Any]:
    return {
        "preprocessing": "StandardScaler",
        "estimator": "LogisticRegression",
        "C": 1.0,
        "penalty": "l2",
        "solver": "lbfgs",
        "class_weight": None,
        "max_iter": 1000,
        "random_state": 20260825,
    }


def scientific_configuration() -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "scientific_role": "historical_development_readiness_only",
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
        "model": model_configuration(),
        "decision_step_s": DECISION_STEP_S,
        "decision_step_rows": DECISION_STEP_ROWS,
        "grid_us": GRID_US,
        "entry_delay_ms": ENTRY_DELAY_MS,
        "entry_steps": ENTRY_STEPS,
        "horizon_s": HORIZON_S,
        "horizon_steps": HORIZON_STEPS,
        "label_threshold_bps": LABEL_THRESHOLD_BPS,
        "causal_rank_policy": {
            "reference_window_size": REFERENCE_WINDOW_SIZE,
            "reference_initialization": "last_1399_chronological_training_scores",
            "gate_quantile": GATE_QUANTILE,
            "quantile_method": QUANTILE_METHOD,
            "rank_tie_side": "right",
            "current_score_inserted_after_decision": True,
        },
        "support": {
            "minimum_n_per_fold": MIN_SUPPORT_N,
            "minimum_positives_per_fold": MIN_POSITIVES,
            "minimum_negatives_per_fold": MIN_NEGATIVES,
        },
        "temporal_null": {
            "fold_preserving": True,
            "shift_step_rows": NULL_SHIFT_STEP_ROWS,
            "same_shift_for_every_fold": True,
            "null_quantile": NULL_QUANTILE,
            "quantile_method": QUANTILE_METHOD,
            "empirical_p_plus_one_correction": True,
        },
        "occupancy": {
            "direction_independent": True,
            "flat_only": True,
            "pyramiding": False,
            "entry_delay_us": ENTRY_DELAY_US,
            "holding_duration_us": HOLDING_DURATION_US,
            "decision_at_t_plus_600s_is_blocked": True,
            "economic_returns_calculated": False,
        },
        "primary_gates": list(PRIMARY_GATE_NAMES),
    }


SCIENTIFIC_CONFIGURATION_SHA256 = canonical_sha256(scientific_configuration())


def runtime_guards() -> dict[str, bool]:
    guards = {
        "AUG30_ANALYTICALLY_OPENED": AUG30_ANALYTICALLY_OPENED,
        "SEP01_OR_LATER_OPENED": SEP01_OR_LATER_OPENED,
        "NETWORK_ACCESSED": NETWORK_ACCESSED,
        "DIRECTION_SCORED": DIRECTION_SCORED,
        "PNL_SCORED": PNL_SCORED,
        "LEVERAGE_SCORED": LEVERAGE_SCORED,
    }
    validate_builtin_bool_invariants(guards)
    if any(guards.values()):
        raise ProtocolViolation("a frozen sealed-data or prohibited-analysis guard is true")
    return guards


def frozen_timing_invariants() -> dict[str, bool]:
    values = {
        "decision_step_exactly_60s": bool(
            DECISION_STEP_ROWS * GRID_US == DECISION_STEP_US
        ),
        "entry_delay_exactly_250ms": bool(
            ENTRY_STEPS == 1 and ENTRY_STEPS * GRID_US == ENTRY_DELAY_US
        ),
        "holding_duration_exactly_600s": bool(
            FROZEN_HORIZON_S == HORIZON_S
            and HOLDING_DURATION_US % GRID_US == 0
            and HORIZON_STEPS == 2400
        ),
    }
    validate_builtin_bool_invariants(values)
    return values


def authorized_feature_path(day: date) -> Path:
    if type(day) is not date or day not in HISTORICAL_DAYS:
        raise ProtocolViolation("day outside exact authorized Jan-Jul calendar")
    return AUTHORIZED_FEATURE_ROOT / SYMBOL / f"{day.isoformat()}_FEATURES250.csv"


def _strict_binary_labels(
    values: np.ndarray | Sequence[Any],
    *,
    context: str,
) -> np.ndarray:
    raw = np.asarray(values)
    if raw.ndim != 1:
        raise ProtocolViolation(f"{context}: labels must be one-dimensional")
    try:
        numeric = raw.astype(float, copy=False)
    except (TypeError, ValueError) as error:
        raise ProtocolViolation(f"{context}: labels must be numeric") from error
    if np.any(~np.isfinite(numeric)):
        raise ProtocolViolation(f"{context}: labels must be finite")
    if np.any((numeric != 0.0) & (numeric != 1.0)):
        raise ProtocolViolation(f"{context}: labels must be exactly binary {{0,1}}")
    return numeric.astype(np.int8, copy=False)


def _fit_readiness_logistic(
    X: np.ndarray,
    y: np.ndarray,
    *,
    context: str,
) -> FixedLogistic:
    matrix = np.asarray(X, dtype=float)
    if matrix.ndim != 2:
        raise ProtocolViolation(f"{context}: training matrix must be two-dimensional")
    labels = _strict_binary_labels(y, context=context)
    if len(matrix) != len(labels):
        raise ProtocolViolation(f"{context}: training matrix/label length mismatch")
    if np.any(~np.isfinite(matrix)):
        raise ProtocolViolation(f"{context}: non-finite training feature")
    if len(labels) < 2 or np.unique(labels).size != 2:
        raise DevelopmentReadinessFailure(
            f"{context}: training labels lack both classes"
        )
    return FixedLogistic().fit(matrix, labels)


def causal_rolling_rank(
    training_probabilities: np.ndarray | Sequence[float],
    validation_probabilities: np.ndarray | Sequence[float],
) -> CausalRankResult:
    training = np.asarray(training_probabilities, dtype=float)
    validation = np.asarray(validation_probabilities, dtype=float)
    if training.ndim != 1 or validation.ndim != 1:
        raise ProtocolViolation("probability inputs must be one-dimensional")
    if len(training) < REFERENCE_WINDOW_SIZE:
        raise DevelopmentReadinessFailure(
            "training support cannot initialize exact 1399-score reference"
        )
    if np.any(~np.isfinite(training)) or np.any(~np.isfinite(validation)):
        raise ProtocolViolation("probabilities must be finite")
    if np.any((training < 0.0) | (training > 1.0)) or np.any(
        (validation < 0.0) | (validation > 1.0)
    ):
        raise ProtocolViolation("probabilities must lie in [0,1]")

    initial = training[-REFERENCE_WINDOW_SIZE:].copy()
    reference: deque[float] = deque(
        (float(value) for value in initial), maxlen=REFERENCE_WINDOW_SIZE
    )
    ranks = np.empty(len(validation), dtype=float)
    thresholds = np.empty(len(validation), dtype=float)
    eligible = np.empty(len(validation), dtype=bool)
    lengths = np.empty(len(validation), dtype=np.int64)

    for index, probability in enumerate(validation.tolist()):
        if len(reference) != REFERENCE_WINDOW_SIZE:
            raise ProtocolViolation("causal reference length changed before decision")
        prior = np.fromiter(reference, dtype=float, count=REFERENCE_WINDOW_SIZE)
        if len(prior) != REFERENCE_WINDOW_SIZE:
            raise ProtocolViolation("causal reference materialization length mismatch")
        threshold = float(
            np.quantile(prior, GATE_QUANTILE, method=QUANTILE_METHOD)
        )
        rank = float(
            np.searchsorted(np.sort(prior), probability, side="right")
            / REFERENCE_WINDOW_SIZE
        )
        is_eligible = bool(probability >= threshold)

        thresholds[index] = threshold
        ranks[index] = rank
        eligible[index] = is_eligible
        lengths[index] = len(reference)

        reference.append(float(probability))
        if len(reference) != REFERENCE_WINDOW_SIZE:
            raise ProtocolViolation("causal reference length changed after update")

    final = np.fromiter(reference, dtype=float, count=REFERENCE_WINDOW_SIZE)
    if np.any(lengths != REFERENCE_WINDOW_SIZE):
        raise ProtocolViolation("causal reference was not exactly length 1399")
    return CausalRankResult(
        rank=ranks,
        threshold=thresholds,
        eligible=eligible,
        initial_reference=initial,
        final_reference=final,
        reference_lengths=lengths,
    )


def causal_rank_invariants(
    training_probabilities: np.ndarray,
    validation_probabilities: np.ndarray,
    result: CausalRankResult,
) -> dict[str, bool]:
    training = np.asarray(training_probabilities, dtype=float)
    validation = np.asarray(validation_probabilities, dtype=float)
    expected_final = np.concatenate((training, validation))[-REFERENCE_WINDOW_SIZE:]
    values = {
        "initial_reference_is_last_1399_training_scores": bool(
            np.array_equal(
                result.initial_reference,
                training[-REFERENCE_WINDOW_SIZE:],
            )
        ),
        "reference_length_always_1399": bool(
            len(result.initial_reference) == REFERENCE_WINDOW_SIZE
            and len(result.final_reference) == REFERENCE_WINDOW_SIZE
            and np.all(result.reference_lengths == REFERENCE_WINDOW_SIZE)
        ),
        "current_score_excluded_before_decision": bool(
            len(validation) == 0
            or (
                result.threshold[0]
                == float(
                    np.quantile(
                        training[-REFERENCE_WINDOW_SIZE:],
                        GATE_QUANTILE,
                        method=QUANTILE_METHOD,
                    )
                )
                and result.rank[0]
                == float(
                    np.searchsorted(
                        np.sort(training[-REFERENCE_WINDOW_SIZE:]),
                        validation[0],
                        side="right",
                    )
                    / REFERENCE_WINDOW_SIZE
                )
            )
        ),
        "future_scores_never_enter_past_references": bool(
            np.array_equal(result.final_reference, expected_final)
        ),
        "eligibility_uses_probability_vs_causal_threshold": bool(
            np.array_equal(result.eligible, validation >= result.threshold)
        ),
    }
    validate_builtin_bool_invariants(values)
    if not all(values.values()):
        raise ProtocolViolation("causal rolling-rank invariant failed")
    return values


def ranking_metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    y = _strict_binary_labels(labels, context="ranking metrics")
    values = np.asarray(scores, dtype=float)
    if values.ndim != 1 or len(values) != len(y):
        raise ProtocolViolation("ranking labels/scores shape mismatch")
    if np.any(~np.isfinite(values)):
        raise ProtocolViolation("ranking scores must be finite")
    n = int(len(y))
    positives = int(np.sum(y == 1))
    negatives = int(np.sum(y == 0))
    prevalence = float(positives / n) if n else None
    both_classes = positives > 0 and negatives > 0
    auc = float(roc_auc_score(y, values)) if both_classes else None
    ap = float(average_precision_score(y, values)) if both_classes else None
    ap_over_prevalence = (
        float(ap / prevalence)
        if ap is not None and prevalence is not None and prevalence > 0.0
        else None
    )
    return {
        "n": n,
        "positives": positives,
        "negatives": negatives,
        "prevalence": prevalence,
        "roc_auc": auc,
        "average_precision": ap,
        "average_precision_over_prevalence": ap_over_prevalence,
    }


def causal_gate_metrics(labels: np.ndarray, eligible: np.ndarray) -> dict[str, Any]:
    y = _strict_binary_labels(labels, context="causal gate metrics")
    selected = np.asarray(eligible)
    if selected.ndim != 1 or len(selected) != len(y) or selected.dtype != np.bool_:
        raise ProtocolViolation("causal eligibility must be a matching boolean vector")
    n = int(len(y))
    positives = int(np.sum(y == 1))
    prevalence = float(positives / n) if n else None
    eligible_count = int(np.sum(selected))
    eligible_positive_count = int(np.sum(y[selected] == 1))
    precision = (
        float(eligible_positive_count / eligible_count) if eligible_count else None
    )
    lift = (
        float(precision / prevalence)
        if precision is not None and prevalence is not None and prevalence > 0.0
        else None
    )
    return {
        "eligible_signal_count": eligible_count,
        "eligible_fraction": float(eligible_count / n) if n else 0.0,
        "eligible_positive_count": eligible_positive_count,
        "eligible_precision": precision,
        "eligible_lift": lift,
    }


def occupancy_support(
    decision_timestamp_us: np.ndarray,
    eligible: np.ndarray,
) -> OccupancyResult:
    timestamps = np.asarray(decision_timestamp_us)
    selected = np.asarray(eligible)
    if timestamps.ndim != 1 or selected.ndim != 1 or len(timestamps) != len(selected):
        raise ProtocolViolation("occupancy inputs must be matching one-dimensional arrays")
    if selected.dtype != np.bool_:
        raise ProtocolViolation("occupancy eligibility must be boolean")
    try:
        timestamps = timestamps.astype(np.int64, copy=False)
    except (TypeError, ValueError) as error:
        raise ProtocolViolation("occupancy timestamps must be integral") from error
    if len(timestamps) > 1 and not bool(np.all(np.diff(timestamps) > 0)):
        raise ProtocolViolation("occupancy timestamps must be unique and chronological")

    eligible_indices = np.flatnonzero(selected)
    executed_decisions: list[int] = []
    entries: list[int] = []
    exits: list[int] = []
    ignored = 0
    open_until_us: int | None = None
    for index in eligible_indices.tolist():
        decision_us = int(timestamps[index])
        if open_until_us is not None and decision_us < open_until_us:
            ignored += 1
            continue
        entry_us = decision_us + ENTRY_DELAY_US
        exit_us = entry_us + HOLDING_DURATION_US
        executed_decisions.append(decision_us)
        entries.append(entry_us)
        exits.append(exit_us)
        open_until_us = exit_us

    entry_array = np.asarray(entries, dtype=np.int64)
    exit_array = np.asarray(exits, dtype=np.int64)
    decision_array = np.asarray(executed_decisions, dtype=np.int64)
    executed = int(len(entry_array))
    accounting = bool(len(eligible_indices) == executed + ignored)
    no_overlap = bool(executed < 2 or np.all(entry_array[1:] >= exit_array[:-1]))
    timing_exact = bool(
        executed == 0
        or (
            np.all(entry_array - decision_array == ENTRY_DELAY_US)
            and np.all(exit_array - entry_array == HOLDING_DURATION_US)
        )
    )
    if not accounting or not no_overlap or not timing_exact:
        raise ProtocolViolation("occupancy accounting or timing invariant failed")
    exposure = float(executed * HOLDING_DURATION_US / DAY_US)
    if not math.isfinite(exposure) or not 0.0 <= exposure <= 1.0:
        raise ProtocolViolation("occupancy exposure is invalid")
    state = "ACTIVE" if executed >= 1 else "ABSTENTION"
    return OccupancyResult(
        eligible_signal_count=int(len(eligible_indices)),
        executed_nonoverlapping_opportunity_count=executed,
        ignored_eligible_signals_while_occupied=int(ignored),
        exposure_fraction=exposure,
        state=state,
        entry_timestamp_us=entry_array,
        exit_timestamp_us=exit_array,
        accounting_consistent=accounting,
        no_position_overlap=no_overlap,
        timing_exact=timing_exact,
    )


def support_is_sufficient(metrics: Mapping[str, Any]) -> bool:
    return bool(
        metrics.get("n", 0) >= MIN_SUPPORT_N
        and metrics.get("positives", 0) >= MIN_POSITIVES
        and metrics.get("negatives", 0) >= MIN_NEGATIVES
    )


def eligible_fold_preserving_shifts(
    fold_lengths: Sequence[int],
) -> np.ndarray:
    lengths = tuple(int(value) for value in fold_lengths)
    if len(lengths) != 4 or any(value <= 0 for value in lengths):
        raise ProtocolViolation("temporal null requires four non-empty folds")
    upper = min(lengths)
    shifts = [
        k
        for k in range(NULL_SHIFT_STEP_ROWS, upper, NULL_SHIFT_STEP_ROWS)
        if all(k < n and min(k, n - k) >= NULL_SHIFT_STEP_ROWS for n in lengths)
    ]
    return np.asarray(shifts, dtype=np.int64)


def fold_preserving_shift(
    fold_labels: Sequence[np.ndarray],
    k: int,
) -> tuple[np.ndarray, ...]:
    labels = tuple(
        _strict_binary_labels(values, context="temporal-null fold")
        for values in fold_labels
    )
    eligible = eligible_fold_preserving_shifts([len(values) for values in labels])
    if type(k) is not int or k == 0 or k not in set(eligible.tolist()):
        raise ProtocolViolation("ineligible fold-preserving circular shift")
    return tuple(np.roll(values, k) for values in labels)


def higher_quantile(values: np.ndarray, q: float) -> float:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or len(array) == 0 or np.any(~np.isfinite(array)):
        raise ProtocolViolation("quantile values must be finite and non-empty")
    return float(np.quantile(array, q, method="higher"))


def empirical_one_sided_p(null_values: np.ndarray, observed: float) -> float:
    values = np.asarray(null_values, dtype=float)
    if values.ndim != 1 or len(values) == 0 or np.any(~np.isfinite(values)):
        raise ProtocolViolation("empirical null values must be finite and non-empty")
    if not math.isfinite(float(observed)):
        raise ProtocolViolation("observed metric must be finite")
    return float((1 + np.sum(values >= observed)) / (1 + len(values)))


def temporal_null(
    fold_labels: Sequence[np.ndarray],
    fold_causal_ranks: Sequence[np.ndarray],
) -> dict[str, Any]:
    labels = tuple(
        _strict_binary_labels(values, context="temporal-null labels")
        for values in fold_labels
    )
    scores = tuple(np.asarray(values, dtype=float) for values in fold_causal_ranks)
    if len(labels) != 4 or len(scores) != 4:
        raise ProtocolViolation("temporal null requires exactly four folds")
    if any(
        score.ndim != 1
        or len(score) != len(label)
        or np.any(~np.isfinite(score))
        for score, label in zip(scores, labels)
    ):
        raise ProtocolViolation("temporal-null fold shape mismatch")
    observed_labels = np.concatenate(labels)
    observed_scores = np.concatenate(scores)
    observed = ranking_metrics(observed_labels, observed_scores)
    if observed["roc_auc"] is None or observed["average_precision"] is None:
        raise DevelopmentReadinessFailure("pooled temporal-null support lacks both classes")
    shifts = eligible_fold_preserving_shifts([len(values) for values in labels])
    if len(shifts) == 0:
        raise DevelopmentReadinessFailure("no eligible fold-preserving temporal shifts")
    auc_values: list[float] = []
    ap_values: list[float] = []
    for shift in shifts.tolist():
        shifted = fold_preserving_shift(labels, int(shift))
        metric = ranking_metrics(np.concatenate(shifted), observed_scores)
        if metric["roc_auc"] is None or metric["average_precision"] is None:
            raise ProtocolViolation("temporal shift unexpectedly lost binary support")
        auc_values.append(float(metric["roc_auc"]))
        ap_values.append(float(metric["average_precision"]))
    auc_array = np.asarray(auc_values, dtype=float)
    ap_array = np.asarray(ap_values, dtype=float)
    return {
        "number_of_shifts": int(len(shifts)),
        "eligible_shifts": shifts.tolist(),
        "shift_step_rows": NULL_SHIFT_STEP_ROWS,
        "same_shift_within_every_fold": True,
        "fold_preserving": True,
        "auc_null_q95": higher_quantile(auc_array, NULL_QUANTILE),
        "ap_null_q95": higher_quantile(ap_array, NULL_QUANTILE),
        "auc_empirical_one_sided_p": empirical_one_sided_p(
            auc_array, float(observed["roc_auc"])
        ),
        "ap_empirical_one_sided_p": empirical_one_sided_p(
            ap_array, float(observed["average_precision"])
        ),
    }


def _concat_support(days: Sequence[OpportunityDay], field: str) -> np.ndarray:
    parts: list[np.ndarray] = []
    for day in days:
        values = np.asarray(getattr(day, field))
        if values.shape != day.common_support.shape:
            raise ProtocolViolation(f"{field} does not match parent support shape")
        part = values[day.common_support]
        if len(part) == 0:
            raise DevelopmentReadinessFailure(f"empty training support for {field}")
        parts.append(part)
    if not parts:
        raise DevelopmentReadinessFailure(f"no training days for {field}")
    return np.concatenate(parts)


def _model_record(model: FixedLogistic) -> dict[str, Any]:
    return {
        "scaler_mean": model.scaler.mean_.tolist(),
        "scaler_scale": model.scaler.scale_.tolist(),
        "coefficient": model.model.coef_[0].tolist(),
        "intercept": float(model.model.intercept_[0]),
        "classes": model.model.classes_.tolist(),
        "hyperparameters": model_configuration(),
    }


def evaluate_fold(
    fold_number: int,
    train_days: Sequence[OpportunityDay],
    validation_day: OpportunityDay,
) -> FoldEvaluation:
    if fold_number not in (1, 2, 3, 4):
        raise ProtocolViolation("fold number outside exact four-fold design")
    expected_train, expected_validation = FOLDS[fold_number - 1]
    if tuple(item.day for item in train_days) != expected_train:
        raise ProtocolViolation("fold training calendar differs from frozen expansion")
    if validation_day.day != expected_validation:
        raise ProtocolViolation("fold validation day differs from frozen chronology")
    for item in (*train_days, validation_day):
        support_timestamps = item.timestamp_us[item.common_support]
        if len(support_timestamps) > 1 and not bool(
            np.all(np.diff(support_timestamps) > 0)
        ):
            raise ProtocolViolation("historical common support is not chronological")
    training_rv = _concat_support(train_days, "rv_30m_bps").reshape(-1, 1)
    training_label = _concat_support(train_days, "opportunity_label")
    model = _fit_readiness_logistic(
        training_rv,
        training_label,
        context=f"fold {fold_number} opportunity model",
    )
    training_probability = model.predict_proba(training_rv)

    support = np.asarray(validation_day.common_support, dtype=bool)
    timestamps = validation_day.timestamp_us[support].astype(np.int64, copy=False)
    labels = _strict_binary_labels(
        validation_day.opportunity_label[support],
        context=f"fold {fold_number} validation labels",
    )
    validation_rv = validation_day.rv_30m_bps[support].reshape(-1, 1)
    if len(timestamps) == 0:
        raise DevelopmentReadinessFailure(f"fold {fold_number} has no common support")
    if len(timestamps) > 1 and not bool(np.all(np.diff(timestamps) > 0)):
        raise ProtocolViolation("validation common support is not chronological")
    probability = model.predict_proba(validation_rv)
    causal = causal_rolling_rank(training_probability, probability)
    causal_checks = causal_rank_invariants(training_probability, probability, causal)
    rank_metric = ranking_metrics(labels, causal.rank)
    raw_metric = ranking_metrics(labels, probability)
    gate_metric = causal_gate_metrics(labels, causal.eligible)
    occupancy = occupancy_support(timestamps, causal.eligible)
    summary = {
        "first": float(causal.threshold[0]),
        "median": float(np.median(causal.threshold)),
        "minimum": float(np.min(causal.threshold)),
        "maximum": float(np.max(causal.threshold)),
        "last": float(causal.threshold[-1]),
    }
    return FoldEvaluation(
        fold=fold_number,
        train_dates=tuple(item.day.isoformat() for item in train_days),
        validation_date=validation_day.day.isoformat(),
        training_probability_count=int(len(training_probability)),
        validation_common_support_count=int(len(timestamps)),
        timestamp_us=timestamps,
        label=labels,
        raw_probability=probability,
        causal_rank=causal.rank,
        threshold=causal.threshold,
        eligible=causal.eligible,
        causal_rank_metrics=rank_metric,
        raw_probability_metrics=raw_metric,
        causal_gate_metrics=gate_metric,
        occupancy=occupancy,
        support_sufficient=support_is_sufficient(rank_metric),
        threshold_summary=summary,
        model_record=_model_record(model),
        causal_invariants=causal_checks,
    )


def historical_development_core(
    days: Mapping[date, OpportunityDay],
) -> DevelopmentCore:
    if tuple(sorted(days)) != HISTORICAL_DAYS:
        raise ProtocolViolation("historical day mapping is not exact Jan-Jul calendar")
    folds: list[FoldEvaluation] = []
    for index, (train_dates, validation_date) in enumerate(FOLDS, start=1):
        folds.append(
            evaluate_fold(
                index,
                [days[day] for day in train_dates],
                days[validation_date],
            )
        )
    if len(folds) != 4:
        raise ProtocolViolation("not all four expanding folds were processed")

    pooled_labels = np.concatenate([fold.label for fold in folds])
    pooled_rank = np.concatenate([fold.causal_rank for fold in folds])
    pooled_raw = np.concatenate([fold.raw_probability for fold in folds])
    pooled_eligible = np.concatenate([fold.eligible for fold in folds])
    rank_metric = ranking_metrics(pooled_labels, pooled_rank)
    raw_metric = ranking_metrics(pooled_labels, pooled_raw)
    gate_metric = causal_gate_metrics(pooled_labels, pooled_eligible)
    null = temporal_null(
        [fold.label for fold in folds],
        [fold.causal_rank for fold in folds],
    )
    if rank_metric["roc_auc"] is None or rank_metric["average_precision"] is None:
        raise DevelopmentReadinessFailure("pooled validation support lacks both classes")
    if raw_metric["roc_auc"] is None or raw_metric["average_precision"] is None:
        raise DevelopmentReadinessFailure("pooled raw-score support lacks both classes")
    records: list[dict[str, Any]] = []
    for fold in folds:
        for timestamp, label, probability, rank, threshold, eligible in zip(
            fold.timestamp_us.tolist(),
            fold.label.tolist(),
            fold.raw_probability.tolist(),
            fold.causal_rank.tolist(),
            fold.threshold.tolist(),
            fold.eligible.tolist(),
        ):
            records.append(
                {
                    "fold": fold.fold,
                    "timestamp_us": int(timestamp),
                    "opportunity_label": int(label),
                    "raw_probability": float(probability),
                    "causal_rank": float(rank),
                    "causal_threshold": float(threshold),
                    "eligible": bool(eligible),
                }
            )
    return DevelopmentCore(
        days=dict(days),
        folds=tuple(folds),
        pooled_causal_rank_metrics=rank_metric,
        pooled_raw_probability_metrics=raw_metric,
        pooled_causal_gate_metrics=gate_metric,
        raw_score_continuity={
            "causal_rank_auc_minus_raw_probability_auc": float(
                rank_metric["roc_auc"] - raw_metric["roc_auc"]
            ),
            "causal_rank_ap_minus_raw_probability_ap": float(
                rank_metric["average_precision"] - raw_metric["average_precision"]
            ),
        },
        temporal_null=null,
        active_fold_count=int(sum(fold.occupancy.state == "ACTIVE" for fold in folds)),
        total_eligible_signals=int(
            sum(fold.occupancy.eligible_signal_count for fold in folds)
        ),
        total_executed_nonoverlapping_opportunities=int(
            sum(
                fold.occupancy.executed_nonoverlapping_opportunity_count
                for fold in folds
            )
        ),
        oof_records=records,
    )


def build_primary_gates(
    core: DevelopmentCore | None,
    *,
    invariants_pass: bool,
) -> dict[str, bool]:
    if type(invariants_pass) is not bool:
        raise ProtocolViolation("invariants_pass must be exact built-in bool")
    folds = core.folds if core is not None else ()
    rank = core.pooled_causal_rank_metrics if core is not None else {}
    gate = core.pooled_causal_gate_metrics if core is not None else {}
    null = core.temporal_null if core is not None else {}
    auc = rank.get("roc_auc")
    ap = rank.get("average_precision")
    gates = {
        PRIMARY_GATE_NAMES[0]: bool(invariants_pass),
        PRIMARY_GATE_NAMES[1]: bool(core is not None and len(folds) == 4),
        PRIMARY_GATE_NAMES[2]: bool(
            core is not None
            and len(folds) == 4
            and all(fold.support_sufficient for fold in folds)
        ),
        PRIMARY_GATE_NAMES[3]: bool(auc is not None and auc >= 0.60),
        PRIMARY_GATE_NAMES[4]: bool(
            rank.get("average_precision_over_prevalence") is not None
            and rank["average_precision_over_prevalence"] >= 1.50
        ),
        PRIMARY_GATE_NAMES[5]: bool(
            gate.get("eligible_lift") is not None and gate["eligible_lift"] >= 1.50
        ),
        PRIMARY_GATE_NAMES[6]: bool(
            core is not None
            and sum(
                fold.causal_gate_metrics.get("eligible_lift") is not None
                and fold.causal_gate_metrics["eligible_lift"] > 1.00
                for fold in folds
            )
            >= 3
        ),
        PRIMARY_GATE_NAMES[7]: bool(
            auc is not None
            and null.get("auc_null_q95") is not None
            and auc > null["auc_null_q95"]
        ),
        PRIMARY_GATE_NAMES[8]: bool(
            null.get("auc_empirical_one_sided_p") is not None
            and null["auc_empirical_one_sided_p"] <= 0.05
        ),
        PRIMARY_GATE_NAMES[9]: bool(
            ap is not None
            and null.get("ap_null_q95") is not None
            and ap > null["ap_null_q95"]
        ),
        PRIMARY_GATE_NAMES[10]: bool(
            null.get("ap_empirical_one_sided_p") is not None
            and null["ap_empirical_one_sided_p"] <= 0.05
        ),
        PRIMARY_GATE_NAMES[11]: bool(
            core is not None and core.active_fold_count >= 3
        ),
    }
    validate_builtin_bool_invariants(gates)
    if tuple(gates) != PRIMARY_GATE_NAMES:
        raise ProtocolViolation("primary gate schema differs from frozen 12 gates")
    return gates


def _static_invariants(
    *,
    protocol_clean: bool,
    prereg_verified: bool,
    exp024_verified: bool,
    exp028_verified: bool,
    lineage_verified: bool,
    provenance_verified: bool,
) -> dict[str, bool]:
    timing = frozen_timing_invariants()
    exact_model = model_configuration() == {
        "preprocessing": "StandardScaler",
        "estimator": "LogisticRegression",
        "C": 1.0,
        "penalty": "l2",
        "solver": "lbfgs",
        "class_weight": None,
        "max_iter": 1000,
        "random_state": 20260825,
    }
    guards = runtime_guards()
    values = {
        "no_protocol_violation_detected": bool(protocol_clean),
        "preregistration_sha_verified": bool(prereg_verified),
        "exp024_result_sha_and_status_verified": bool(exp024_verified),
        "exp028_result_sha_and_status_verified": bool(exp028_verified),
        "frozen_lineage_ancestry_verified": bool(lineage_verified),
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
        "opportunity_feature_exactly_rv_30m_bps": bool(
            OPPORTUNITY_FEATURE == "rv_30m_bps"
        ),
        "opportunity_model_configuration_exact": bool(exact_model),
        "decision_step_exactly_60s": timing["decision_step_exactly_60s"],
        "entry_delay_exactly_250ms": timing["entry_delay_exactly_250ms"],
        "holding_duration_exactly_600s": timing["holding_duration_exactly_600s"],
        "opportunity_label_threshold_exactly_24bp": bool(
            LABEL_THRESHOLD_BPS == FROZEN_LABEL_THRESHOLD_BPS == 24.0
        ),
        "reference_window_exactly_1399": bool(REFERENCE_WINDOW_SIZE == 1399),
        "gate_quantile_exactly_0_90_higher": bool(
            GATE_QUANTILE == 0.90 and QUANTILE_METHOD == "higher"
        ),
        "temporal_null_exactly_fold_preserving_step_30": bool(
            NULL_SHIFT_STEP_ROWS == 30 and NULL_QUANTILE == 0.95
        ),
        "aug30_analytically_opened_false": bool(
            guards["AUG30_ANALYTICALLY_OPENED"] is False
        ),
        "sep01_or_later_opened_false": bool(
            guards["SEP01_OR_LATER_OPENED"] is False
        ),
        "network_accessed_false": bool(guards["NETWORK_ACCESSED"] is False),
        "direction_scored_false": bool(guards["DIRECTION_SCORED"] is False),
        "pnl_scored_false": bool(guards["PNL_SCORED"] is False),
        "leverage_scored_false": bool(guards["LEVERAGE_SCORED"] is False),
        "no_arbitrary_data_or_network_interface": bool(
            tuple(action.dest for action in build_parser()._actions)
            == ("help", "mode", "workspace", "frozen_commit", "output")
        ),
    }
    validate_builtin_bool_invariants(values)
    return values


def build_invariants(
    core: DevelopmentCore | None,
    *,
    protocol_clean: bool,
    prereg_verified: bool,
    exp024_verified: bool,
    exp028_verified: bool,
    lineage_verified: bool,
    provenance_verified: bool,
    pipeline_completed: bool,
    output_preconditions_verified: bool,
) -> dict[str, bool]:
    values = _static_invariants(
        protocol_clean=protocol_clean,
        prereg_verified=prereg_verified,
        exp024_verified=exp024_verified,
        exp028_verified=exp028_verified,
        lineage_verified=lineage_verified,
        provenance_verified=provenance_verified,
    )
    folds = core.folds if core is not None else ()
    evaluated = bool(pipeline_completed and core is not None and len(folds) == 4)
    occupancy = [fold.occupancy for fold in folds]
    values.update(
        {
            "historical_pipeline_evaluated": bool(evaluated),
            "historical_common_support_equals_parent_valid_R": bool(
                evaluated
                and tuple(sorted(core.days)) == HISTORICAL_DAYS
                and all(day.parent_support_exact is True for day in core.days.values())
            ),
            "validation_rows_unique_and_chronological": bool(
                evaluated
                and all(
                    len(fold.timestamp_us) < 2
                    or np.all(np.diff(fold.timestamp_us) > 0)
                    for fold in folds
                )
            ),
            "training_models_fit_on_training_rows_only": bool(
                evaluated
                and all(
                    fold.train_dates
                    == tuple(day.isoformat() for day in FOLDS[fold.fold - 1][0])
                    and fold.validation_date
                    == FOLDS[fold.fold - 1][1].isoformat()
                    for fold in folds
                )
            ),
            "initial_reference_is_last_1399_training_scores": bool(
                evaluated
                and all(
                    fold.causal_invariants[
                        "initial_reference_is_last_1399_training_scores"
                    ]
                    is True
                    for fold in folds
                )
            ),
            "reference_length_always_1399": bool(
                evaluated
                and all(
                    fold.causal_invariants["reference_length_always_1399"] is True
                    for fold in folds
                )
            ),
            "current_score_excluded_before_decision": bool(
                evaluated
                and all(
                    fold.causal_invariants["current_score_excluded_before_decision"]
                    is True
                    for fold in folds
                )
            ),
            "future_scores_never_enter_past_references": bool(
                evaluated
                and all(
                    fold.causal_invariants[
                        "future_scores_never_enter_past_references"
                    ]
                    is True
                    for fold in folds
                )
            ),
            "eligibility_uses_probability_vs_causal_threshold": bool(
                evaluated
                and all(
                    fold.causal_invariants[
                        "eligibility_uses_probability_vs_causal_threshold"
                    ]
                    is True
                    for fold in folds
                )
            ),
            "fold_preserving_temporal_null": bool(
                evaluated and core.temporal_null.get("fold_preserving") is True
            ),
            "same_shift_applied_to_every_fold": bool(
                evaluated
                and core.temporal_null.get("same_shift_within_every_fold") is True
            ),
            "occupancy_accounting_consistent": bool(
                evaluated and all(item.accounting_consistent is True for item in occupancy)
            ),
            "occupancy_has_no_overlap": bool(
                evaluated and all(item.no_position_overlap is True for item in occupancy)
            ),
            "occupancy_timing_exact": bool(
                evaluated and all(item.timing_exact is True for item in occupancy)
            ),
            "result_payload_json_safe": bool(protocol_clean),
            "one_shot_preconditions_verified": bool(output_preconditions_verified),
        }
    )
    validate_builtin_bool_invariants(values)
    required = set(STATIC_INVARIANT_NAMES) | set(EVALUATED_INVARIANT_NAMES)
    if set(values) != required:
        raise ProtocolViolation("invariant schema differs from frozen EXP029 design")
    return values


def adjudicate_status(
    invariants: Mapping[str, Any],
    gates: Mapping[str, Any],
    *,
    pipeline_completed: bool,
    clean_readiness_failure: bool,
) -> str:
    try:
        checked_invariants = validate_builtin_bool_invariants(invariants)
        checked_gates = validate_builtin_bool_invariants(gates)
    except Exception as error:
        raise ProtocolViolation("invariants and gates require exact built-in bools") from error
    if set(checked_invariants) != set(STATIC_INVARIANT_NAMES) | set(
        EVALUATED_INVARIANT_NAMES
    ):
        raise ProtocolViolation("invariant names differ from frozen EXP029 schema")
    if tuple(checked_gates) != PRIMARY_GATE_NAMES:
        raise ProtocolViolation("gate names differ from frozen EXP029 schema")
    if type(pipeline_completed) is not bool or type(clean_readiness_failure) is not bool:
        raise ProtocolViolation("adjudication state must use exact built-in bools")
    if not all(checked_invariants[name] for name in STATIC_INVARIANT_NAMES):
        return INVALID_STATUS
    if clean_readiness_failure and not pipeline_completed:
        return FAIL_STATUS
    if not pipeline_completed:
        return INVALID_STATUS
    if not all(checked_invariants[name] for name in EVALUATED_INVARIANT_NAMES):
        return INVALID_STATUS
    return PASS_STATUS if all(checked_gates.values()) else FAIL_STATUS


def build_opportunity_day(day: DayData) -> OpportunityDay:
    if day.day not in HISTORICAL_DAYS:
        raise ProtocolViolation("attempted to build unauthorized historical day")
    frozen = build_day_dataset(SYMBOL, day)
    decisions = np.arange(0, len(day.ts), DECISION_STEP_ROWS, dtype=np.int64)
    outcomes = executable_fixed_horizon(day, decisions, HORIZON_S)
    reconstructed_support = (
        np.asarray(outcomes["valid"], dtype=bool)
        & np.isfinite(outcomes["oracle_gross_bps"])
        & np.all(np.isfinite(frozen.X_R), axis=1)
    )
    support = np.asarray(frozen.valid_R, dtype=bool)
    parent_support_exact = bool(np.array_equal(reconstructed_support, support))
    if not parent_support_exact:
        raise ProtocolViolation("EXP029 support differs from frozen parent valid_R")
    if not np.array_equal(frozen.timestamp_us, day.ts[decisions]):
        raise ProtocolViolation("decision timestamps differ from frozen 60-second grid")
    entry = np.asarray(outcomes["entry_index"], dtype=np.int64)
    exit_ = np.asarray(outcomes["exit_index"], dtype=np.int64)
    if np.any(entry[support] - decisions[support] != ENTRY_STEPS):
        raise ProtocolViolation("target entry is not decision plus one 250ms row")
    if np.any(exit_[support] - entry[support] != HORIZON_STEPS):
        raise ProtocolViolation("target exit is not entry plus 600 seconds")
    if np.any(day.ts[entry[support]] - day.ts[decisions[support]] != ENTRY_DELAY_US):
        raise ProtocolViolation("target entry timestamp is not t+250ms")
    if np.any(day.ts[exit_[support]] - day.ts[entry[support]] != HOLDING_DURATION_US):
        raise ProtocolViolation("target exit timestamp is not entry+600s")
    expected_label = (
        np.asarray(outcomes["oracle_gross_bps"], dtype=float)
        >= LABEL_THRESHOLD_BPS
    ).astype(np.int8)
    if not np.array_equal(expected_label[support], frozen.y[support]):
        raise ProtocolViolation("opportunity label differs from frozen parent target")
    rv = frozen.X_R[:, VOL_INDEX].astype(float, copy=False)
    if np.any(~np.isfinite(rv[support])):
        raise ProtocolViolation("rv_30m_bps is non-finite on frozen parent support")
    support_timestamps = frozen.timestamp_us[support]
    if len(support_timestamps) > 1 and not bool(
        np.all(np.diff(support_timestamps) > 0)
    ):
        raise ProtocolViolation("parent common support is not unique and chronological")
    return OpportunityDay(
        day=day.day,
        timestamp_us=frozen.timestamp_us.astype(np.int64, copy=False),
        rv_30m_bps=rv,
        opportunity_label=frozen.y.astype(np.int8, copy=False),
        common_support=support,
        parent_support_exact=parent_support_exact,
    )


def _git(workspace: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
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
            f"git ancestry check failed ({completed.returncode}): "
            f"{completed.stderr.strip()}"
        )
    return bool(completed.returncode == 0)


def assert_frozen_workspace(workspace: Path, frozen_commit: str) -> None:
    if type(frozen_commit) is not str or len(frozen_commit) != 40:
        raise ProtocolViolation("full 40-character frozen commit required")
    try:
        int(frozen_commit, 16)
    except ValueError as error:
        raise ProtocolViolation("frozen commit must be hexadecimal") from error
    if _git(workspace, "rev-parse", "HEAD") != frozen_commit:
        raise ProtocolViolation("frozen implementation commit mismatch")
    if _git(workspace, "status", "--porcelain", "--untracked-files=no"):
        raise ProtocolViolation("tracked worktree is dirty")
    for ancestor in (
        PREREG_COMMIT,
        EXP024_IMPLEMENTATION_COMMIT,
        EXP024_RESULT_COMMIT,
        EXP028_RESULT_COMMIT,
    ):
        if not _is_ancestor(workspace, ancestor, frozen_commit):
            raise ProtocolViolation(f"frozen lineage commit is not an ancestor: {ancestor}")


def verify_frozen_references(workspace: Path) -> dict[str, Any]:
    prereg = workspace / PREREG_REL
    exp024_path = workspace / EXP024_RESULT_REL
    exp028_path = workspace / EXP028_RESULT_REL
    if sha256_file(prereg) != PREREG_SHA256:
        raise ProtocolViolation("EXP029 preregistration SHA-256 mismatch")
    if sha256_file(exp024_path) != EXP024_RESULT_SHA256:
        raise ProtocolViolation("EXP024 result SHA-256 mismatch")
    if sha256_file(exp028_path) != EXP028_RESULT_SHA256:
        raise ProtocolViolation("EXP028 result SHA-256 mismatch")
    with exp024_path.open("r", encoding="utf-8") as handle:
        exp024 = json.load(handle)
    with exp028_path.open("r", encoding="utf-8") as handle:
        exp028 = json.load(handle)
    if exp024.get("experiment_id") != EXP024_EXPERIMENT_ID:
        raise ProtocolViolation("EXP024 result experiment identity mismatch")
    if exp024.get("status") != EXP024_STATUS:
        raise ProtocolViolation("EXP024 result status mismatch")
    if exp028.get("experiment_id") != EXP028_EXPERIMENT_ID:
        raise ProtocolViolation("EXP028 result experiment identity mismatch")
    if exp028.get("status") != EXP028_STATUS:
        raise ProtocolViolation("EXP028 result status mismatch")
    return {
        "preregistration": {
            "path": PREREG_REL,
            "commit": PREREG_COMMIT,
            "sha256": PREREG_SHA256,
        },
        "exp024_parent": {
            "experiment_id": EXP024_EXPERIMENT_ID,
            "implementation_commit": EXP024_IMPLEMENTATION_COMMIT,
            "result_commit": EXP024_RESULT_COMMIT,
            "result_path": EXP024_RESULT_REL,
            "result_sha256": EXP024_RESULT_SHA256,
            "status": EXP024_STATUS,
        },
        "exp028_parent": {
            "experiment_id": EXP028_EXPERIMENT_ID,
            "result_commit": EXP028_RESULT_COMMIT,
            "result_path": EXP028_RESULT_REL,
            "result_sha256": EXP028_RESULT_SHA256,
            "status": EXP028_STATUS,
        },
    }


def _verify_historical_inputs(workspace: Path) -> list[dict[str, Any]]:
    manifest = _verify_parent_training_inputs(AUTHORIZED_FEATURE_ROOT, workspace)
    by_day = {str(item["day"]): dict(item) for item in manifest}
    if tuple(sorted(by_day)) != HISTORICAL_DAY_STRINGS:
        raise ProtocolViolation("historical input manifest calendar mismatch")
    result: list[dict[str, Any]] = []
    for day in HISTORICAL_DAYS:
        record = by_day[day.isoformat()]
        expected_path = authorized_feature_path(day)
        if Path(str(record.get("path"))) != expected_path:
            raise ProtocolViolation("historical input path differs from exact frozen path")
        if type(record.get("bytes")) is not int or record["bytes"] <= 0:
            raise ProtocolViolation("historical input byte size is invalid")
        digest = record.get("sha256")
        if type(digest) is not str or len(digest) != 64:
            raise ProtocolViolation("historical input SHA-256 is invalid")
        record["split_roles"] = [
            {
                "fold": index,
                "role": (
                    "train"
                    if day in train
                    else "validation"
                    if day == validation
                    else "unused"
                ),
            }
            for index, (train, validation) in enumerate(FOLDS, start=1)
        ]
        result.append(record)
    return result


def _load_historical_days(
    manifest: Sequence[Mapping[str, Any]],
) -> dict[date, OpportunityDay]:
    records = {str(item["day"]): item for item in manifest}
    if tuple(sorted(records)) != HISTORICAL_DAY_STRINGS:
        raise ProtocolViolation("load manifest is not exact Jan-Jul")
    loaded: dict[date, OpportunityDay] = {}
    for day in HISTORICAL_DAYS:
        path = authorized_feature_path(day)
        if Path(str(records[day.isoformat()]["path"])) != path:
            raise ProtocolViolation("load path differs from exact authorized path")
        loaded[day] = build_opportunity_day(_load_day(path, day))
    return loaded


def _occupancy_public(value: OccupancyResult) -> dict[str, Any]:
    return {
        "eligible_signal_count": value.eligible_signal_count,
        "executed_nonoverlapping_opportunity_count": (
            value.executed_nonoverlapping_opportunity_count
        ),
        "ignored_eligible_signals_while_occupied": (
            value.ignored_eligible_signals_while_occupied
        ),
        "exposure_fraction": value.exposure_fraction,
        "state": value.state,
        "entry_timestamp_us": value.entry_timestamp_us.tolist(),
        "exit_timestamp_us": value.exit_timestamp_us.tolist(),
        "accounting_consistent": value.accounting_consistent,
        "no_position_overlap": value.no_position_overlap,
        "timing_exact": value.timing_exact,
    }


def _fold_public(fold: FoldEvaluation) -> dict[str, Any]:
    return {
        "fold": fold.fold,
        "train_dates": list(fold.train_dates),
        "validation_date": fold.validation_date,
        "training_probability_count": fold.training_probability_count,
        "validation_common_support_count": fold.validation_common_support_count,
        "support_sufficient": fold.support_sufficient,
        "causal_rank_metrics": fold.causal_rank_metrics,
        "raw_probability_metrics_non_gating": fold.raw_probability_metrics,
        "causal_gate_metrics": fold.causal_gate_metrics,
        "occupancy_support": _occupancy_public(fold.occupancy),
        "threshold_summary": fold.threshold_summary,
        "opportunity_model": fold.model_record,
        "causal_invariants": fold.causal_invariants,
    }


def _public_core(core: DevelopmentCore) -> dict[str, Any]:
    return {
        "folds": [_fold_public(fold) for fold in core.folds],
        "pooled_causal_rank_metrics": core.pooled_causal_rank_metrics,
        "pooled_raw_probability_metrics_non_gating": (
            core.pooled_raw_probability_metrics
        ),
        "raw_score_continuity_non_gating": core.raw_score_continuity,
        "pooled_causal_gate_metrics": core.pooled_causal_gate_metrics,
        "temporal_null": core.temporal_null,
        "active_fold_count": core.active_fold_count,
        "total_eligible_signals": core.total_eligible_signals,
        "total_executed_nonoverlapping_opportunities": (
            core.total_executed_nonoverlapping_opportunities
        ),
        "oof_validation_records": core.oof_records,
        "oof_record_sha256": canonical_sha256(core.oof_records),
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
    validate_builtin_bool_invariants(payload["primary_gates"])
    guards = validate_builtin_bool_invariants(payload["runtime_guards"])
    if any(guards.values()):
        raise ProtocolViolation("result runtime guards are not all false")
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
    try:
        directory_descriptor = os.open(output.parent, os.O_RDONLY)
    except OSError:
        directory_descriptor = None
    if directory_descriptor is not None:
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    return hashlib.sha256(encoded).hexdigest()


def _all_false_gates() -> dict[str, bool]:
    return {name: False for name in PRIMARY_GATE_NAMES}


def run_historical_development(
    workspace: Path,
    frozen_commit: str,
    output: Path,
    *,
    argv: Sequence[str] | None = None,
) -> RunWriteResult:
    _fresh_output(output)
    started = _utc_now()
    run_id = (
        f"CODEX-RUN-EXP029-{started.replace(':', '').replace('-', '')}-"
        f"{uuid.uuid4().hex[:8]}"
    )
    references: dict[str, Any] | None = None
    manifest: list[dict[str, Any]] = []
    core: DevelopmentCore | None = None
    prereg_verified = False
    exp024_verified = False
    exp028_verified = False
    lineage_verified = False
    provenance_verified = False
    protocol_clean = True
    pipeline_completed = False
    clean_readiness_failure = False
    failure_reason: str | None = None
    try:
        assert_frozen_workspace(workspace, frozen_commit)
        lineage_verified = True
        references = verify_frozen_references(workspace)
        prereg_verified = True
        exp024_verified = True
        exp028_verified = True
        manifest = _verify_historical_inputs(workspace)
        provenance_verified = True
        core = historical_development_core(_load_historical_days(manifest))
        pipeline_completed = True
    except DevelopmentReadinessFailure as error:
        clean_readiness_failure = True
        failure_reason = str(error)
    except Exception as error:
        protocol_clean = False
        failure_reason = f"{type(error).__name__}: {error}"

    invariants = build_invariants(
        core,
        protocol_clean=protocol_clean,
        prereg_verified=prereg_verified,
        exp024_verified=exp024_verified,
        exp028_verified=exp028_verified,
        lineage_verified=lineage_verified,
        provenance_verified=provenance_verified,
        pipeline_completed=pipeline_completed,
        output_preconditions_verified=True,
    )
    evaluated_invariants_pass = bool(
        pipeline_completed
        and all(invariants[name] for name in STATIC_INVARIANT_NAMES)
        and all(invariants[name] for name in EVALUATED_INVARIANT_NAMES)
    )
    gates = (
        build_primary_gates(core, invariants_pass=evaluated_invariants_pass)
        if core is not None
        else _all_false_gates()
    )
    status = adjudicate_status(
        invariants,
        gates,
        pipeline_completed=pipeline_completed,
        clean_readiness_failure=clean_readiness_failure,
    )
    payload: dict[str, Any] = {
        "run_id": run_id,
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "failure_reason": failure_reason,
        "started_at_utc": started,
        "finished_at_utc": _utc_now(),
        "execution_mode": "historical-development",
        "command_argv": list(argv if argv is not None else sys.argv),
        "frozen_git_commit": frozen_commit,
        "tracked_tree_dirty": bool(
            _git(workspace, "status", "--porcelain", "--untracked-files=no")
        ),
        "environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "numpy_version": np.__version__,
            "scikit_learn_version": sklearn.__version__,
        },
        "references": references,
        "scientific_configuration": scientific_configuration(),
        "scientific_configuration_sha256": SCIENTIFIC_CONFIGURATION_SHA256,
        "historical_input_manifest": manifest,
        "feature_columns": [OPPORTUNITY_FEATURE],
        "model_hyperparameters_and_seed": model_configuration(),
        "target_and_occupancy_semantics": {
            "target": "any-direction executable opportunity at least 24bp",
            "decision_step_s": DECISION_STEP_S,
            "entry_delay_ms": ENTRY_DELAY_MS,
            "opportunity_horizon_s": HORIZON_S,
            "occupancy_only": True,
            "economic_evaluation": False,
        },
        "historical_development": _public_core(core) if core is not None else None,
        "primary_gates": gates,
        "invariants": invariants,
        "invariant_groups": {
            "static_protocol_and_provenance": list(STATIC_INVARIANT_NAMES),
            "evaluated_causality_and_execution": list(EVALUATED_INVARIANT_NAMES),
        },
        "runtime_guards": runtime_guards(),
        "output_sha256": None,
        "output_sha256_semantics": (
            "computed and reported after atomic write; not recursively embedded"
        ),
    }
    digest = _write_once(output, payload)
    return RunWriteResult(normalize_json_safe(payload), digest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CODEX-EXP-029-P0 causal-rank historical development readiness"
    )
    parser.add_argument(
        "--mode", choices=("historical-development",), required=True
    )
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    effective_argv = list(argv) if argv is not None else sys.argv[1:]
    result = run_historical_development(
        args.workspace,
        args.frozen_commit,
        args.output,
        argv=effective_argv,
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

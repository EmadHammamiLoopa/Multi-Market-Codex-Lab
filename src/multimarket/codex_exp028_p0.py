from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import sklearn

from . import codex_exp026_p0 as exp026
from .codex_research import canonical_sha256, sha256_file


EXPERIMENT_ID = "CODEX-EXP-028-P0"
PASS_STATUS = "ABSTENTION_AWARE_DIRECTION_PIPELINE_READY_FOR_FRESH_PROSPECTIVE_VALIDATION"
FAIL_STATUS = "FAIL_ABSTENTION_AWARE_DIRECTION_PIPELINE_NOT_READY"
INVALID_STATUS = "INVALID"

PREREGISTRATION_COMMIT = "07918d88db4e77a9c608243b9629774d43ee8d7f"
PREREGISTRATION_REL = "docs/CODEX_EXP028_P0_ABSTENTION_AWARE_DIRECTION_READINESS.md"
PREREGISTRATION_SHA256 = "0140f1187e6937b565f544b6f92b06b15b1ce601004ad87229223a4d64e9b901"
EXP026_FAIL_COMMIT = "5796b1dd15ceb773b9be05ce8d1fed46bb0298cc"
EXP026_IMPLEMENTATION_COMMIT = "18b192db45ece0fdc4d2f2ddb81ffbd2acdc7a50"
PARENT_RESULT_REL = (
    "evidence/codex/exp026_p0_direction_execution_readiness/"
    "HISTORICAL_SELECTION.json"
)
PARENT_RESULT_SHA256 = "b852a1c28957411efab259b12b7b68d941fa4850f39c489fd96de752bdb26e27"
PARENT_EXPERIMENT_ID = "CODEX-EXP-026-P0"
PARENT_STATUS = "FAIL_DIRECTION_EXECUTION_PIPELINE_NOT_READY"

SYMBOL = exp026.SYMBOL
HISTORICAL_DAYS = exp026.HISTORICAL_DAYS
HISTORICAL_DAY_STRINGS = exp026.HISTORICAL_DAY_STRINGS
AUTHORIZED_FEATURE_ROOT = exp026.AUTHORIZED_FEATURE_ROOT
FOLDS = exp026.FOLDS
OPPORTUNITY_FEATURE = exp026.OPPORTUNITY_FEATURE
DIRECTION_FEATURE_NAMES = exp026.DIRECTION_FEATURE_NAMES
CANDIDATES = exp026.CANDIDATES
SIMPLICITY_ORDER = exp026.SIMPLICITY_ORDER
OPPORTUNITY_QUANTILE = exp026.OPPORTUNITY_QUANTILE
OPPORTUNITY_QUANTILE_METHOD = exp026.OPPORTUNITY_QUANTILE_METHOD
DIRECTION_THRESHOLD = exp026.DIRECTION_THRESHOLD
PRIMARY_COST_BPS = exp026.PRIMARY_COST_BPS
STRESS_COST_BPS = exp026.STRESS_COST_BPS
DECISION_STEP_US = exp026.DECISION_STEP_US
ENTRY_DELAY_US = exp026.ENTRY_DELAY_US
HOLDING_DURATION_US = exp026.HOLDING_DURATION_US
MIN_ACTIVE_FOLDS = 3
ACTIVE = "ACTIVE"
ABSTENTION = "ABSTENTION"

AUG30_ANALYTICALLY_OPENED = False
SEP01_OR_LATER_OPENED = False
NETWORK_ACCESSED = False

ProtocolViolation = exp026.ProtocolViolation
SelectionReadinessFailure = exp026.SelectionReadinessFailure
DirectionDay = exp026.DirectionDay
ExecutionEvaluation = exp026.ExecutionEvaluation
RunWriteResult = exp026.RunWriteResult


@dataclass
class CoreSelection:
    days: dict[date, DirectionDay]
    folds: list[dict[str, Any]]
    private_folds: list[dict[str, Any]]
    fold_states: tuple[str, ...]
    active_fold_count: int
    selection_feasible: bool
    selected_candidate: str | None
    candidate_selection: dict[str, Any] | None
    final_models: dict[str, Any] | None
    readiness_failure_reason: str | None


STATIC_INVARIANT_NAMES = (
    "no_protocol_violation_detected",
    "preregistration_sha_verified",
    "exp026_parent_sha_status_and_commit_verified",
    "frozen_lineage_ancestry_verified",
    "historical_input_provenance_verified",
    "exact_jan_jul_historical_calendar",
    "exactly_four_expanding_folds",
    "candidate_set_exactly_A_B_C",
    "opportunity_configuration_unchanged",
    "direction_configuration_unchanged",
    "trigger_quantile_exactly_0_90_higher",
    "execution_timing_and_costs_unchanged",
    "aug30_analytically_opened_false",
    "sep01_or_later_opened_false",
    "network_accessed_false",
    "no_leverage_sl_tp_sizing_posthoc_or_threshold_rescue",
)
EXECUTION_INVARIANT_NAMES = (
    "all_four_folds_processed",
    "historical_common_support_equals_parent_valid_R",
    "every_fold_trigger_training_probabilities_only",
    "no_validation_derived_threshold",
    "active_abstention_pattern_identical_across_candidates",
    "abstention_representation_exact",
    "nonoverlap_accounting_consistent",
    "no_position_overlap",
    "exposure_fraction_finite_and_bounded",
    "executed_trade_timing_exact",
)
READINESS_INVARIANT_NAMES = (
    "historical_selection_pipeline_completed",
    "at_least_three_active_folds",
    "exactly_one_candidate_selected",
    "final_jan_jul_parameters_recorded",
    "final_trigger_from_full_jan_jul_training_probabilities_only",
    "final_direction_freeze_matches_selected_candidate",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def scientific_configuration() -> dict[str, Any]:
    config = json.loads(json.dumps(exp026.scientific_configuration()))
    config["experiment_id"] = EXPERIMENT_ID
    config["abstention_aware_selection"] = {
        "fold_states": [ACTIVE, ABSTENTION],
        "active_definition": "at least one executed non-overlapping trade",
        "abstention_definition": "zero executed trades",
        "minimum_active_folds": MIN_ACTIVE_FOLDS,
        "selection_uses_active_folds_only": True,
        "abstention_is_not_synthetic_zero_per_trade": True,
        "tie_break_simplicity_order": list(SIMPLICITY_ORDER),
    }
    return config


SCIENTIFIC_CONFIGURATION_SHA256 = canonical_sha256(scientific_configuration())


def authorized_feature_path(day: date) -> Path:
    return exp026.authorized_feature_path(day)


def candidate_b_direction(values: np.ndarray) -> np.ndarray:
    return exp026.candidate_b_direction(values)


def candidate_c_direction(values: np.ndarray) -> np.ndarray:
    return exp026.candidate_c_direction(values)


def direction_label(long_bps: np.ndarray, short_bps: np.ndarray) -> np.ndarray:
    return exp026.direction_label(long_bps, short_bps)


def training_probability_trigger(probabilities: np.ndarray) -> float:
    return exp026.training_probability_trigger(probabilities)


def _fit_readiness_logistic(
    X: np.ndarray, y: np.ndarray, *, context: str
) -> exp026.FixedLogistic:
    return exp026._fit_readiness_logistic(X, y, context=context)


def execute_nonoverlapping(
    day: DirectionDay,
    opportunity_probability: np.ndarray,
    trigger: float,
    choose_long: np.ndarray,
) -> ExecutionEvaluation:
    return exp026.execute_nonoverlapping(
        day, opportunity_probability, trigger, choose_long
    )


def _fit_fold(
    train_days: Sequence[DirectionDay], validation: DirectionDay
) -> dict[str, Any]:
    return exp026._fit_fold(train_days, validation)


def _fold_state(fitted: Mapping[str, Any]) -> str:
    if tuple(fitted.get("candidates", {}).keys()) != CANDIDATES:
        raise ProtocolViolation("fold candidate set differs from exact A/B/C")
    counts: list[int] = []
    for candidate in CANDIDATES:
        evaluation = fitted["candidates"][candidate]
        count = evaluation.metrics.get("executed_nonoverlapping_trade_count")
        if type(count) is not int or count < 0 or len(evaluation.net_bps) != count:
            raise ProtocolViolation("invalid executed-trade count in fold")
        counts.append(count)
    if len(set(counts)) != 1:
        raise ProtocolViolation("ACTIVE/ABSTENTION schedule differs across A/B/C")
    return ACTIVE if counts[0] >= 1 else ABSTENTION


def _reported_fold_metrics(
    evaluation: ExecutionEvaluation, state: str
) -> dict[str, Any]:
    metrics = dict(evaluation.metrics)
    count = metrics["executed_nonoverlapping_trade_count"]
    metrics["state"] = state
    metrics["realized_total_pnl_bps_at_14bp"] = float(
        metrics["net_total_bps_at_14bp"]
    )
    metrics["net_bps_per_trade"] = (
        float(metrics["net_total_bps_at_14bp"]) / count if count else None
    )
    if state == ABSTENTION:
        exact = (
            count == 0
            and len(evaluation.net_bps) == 0
            and metrics["eligible_signal_count"] == 0
            and metrics["gross_total_bps"] == 0.0
            and metrics["net_total_bps_at_14bp"] == 0.0
            and metrics["realized_total_pnl_bps_at_14bp"] == 0.0
            and metrics["stress_total_bps_at_20bp"] == 0.0
            and metrics["exposure_fraction"] == 0.0
            and metrics["net_bps_per_trade"] is None
            and metrics["mean_net_bps_per_trade"] is None
            and metrics["median_net_bps_per_trade"] is None
        )
        if not exact:
            raise ProtocolViolation("ABSTENTION metrics are not exact zero/undefined form")
    elif state != ACTIVE or count < 1:
        raise ProtocolViolation("invalid fold state")
    return metrics


def selection_is_feasible(states: Sequence[str]) -> bool:
    if len(states) != 4 or any(state not in (ACTIVE, ABSTENTION) for state in states):
        raise ProtocolViolation("feasibility requires exactly four valid fold states")
    return bool(sum(state == ACTIVE for state in states) >= MIN_ACTIVE_FOLDS)


def select_candidate(
    folds: Sequence[Mapping[str, Any]],
) -> tuple[str, dict[str, Any]]:
    if len(folds) != 4:
        raise ProtocolViolation("selection requires exactly four processed folds")
    states = tuple(str(fold.get("state")) for fold in folds)
    if not selection_is_feasible(states):
        raise SelectionReadinessFailure("fewer than three ACTIVE validation folds")
    active_folds = [fold for fold in folds if fold["state"] == ACTIVE]
    diagnostics: dict[str, Any] = {}
    keys: dict[str, tuple[float, int, float, float, int]] = {}
    simplicity = {
        name: len(SIMPLICITY_ORDER) - index
        for index, name in enumerate(SIMPLICITY_ORDER)
    }
    for candidate in CANDIDATES:
        evaluations = [fold["candidates"][candidate] for fold in active_folds]
        if any(
            item.metrics["executed_nonoverlapping_trade_count"] < 1
            for item in evaluations
        ):
            raise ProtocolViolation("ACTIVE fold contains zero-trade candidate")
        per_fold = [
            float(item.metrics["net_total_bps_at_14bp"])
            / int(item.metrics["executed_nonoverlapping_trade_count"])
            for item in evaluations
        ]
        pooled = np.concatenate([item.net_bps for item in evaluations])
        pooled_pf = exp026.profit_factor_diagnostic(pooled, prefix="pooled_")
        positive_folds = int(
            sum(item.metrics["net_total_bps_at_14bp"] > 0 for item in evaluations)
        )
        pooled_drawdown = exp026.maximum_drawdown_bps(pooled)
        primary = float(np.median(np.asarray(per_fold, dtype=float)))
        diagnostics[candidate] = {
            "active_fold_count": len(active_folds),
            "abstention_fold_count": 4 - len(active_folds),
            "active_validation_fold_net_bps_per_trade": per_fold,
            "median_active_validation_fold_net_bps_per_trade": primary,
            "positive_total_net_active_folds": positive_folds,
            **pooled_pf,
            "pooled_active_fold_trade_count": int(len(pooled)),
            "pooled_active_fold_maximum_drawdown_bps": pooled_drawdown,
            "abstention_folds_excluded_from_ranking": True,
            "simplicity_rank": SIMPLICITY_ORDER.index(candidate) + 1,
        }
        keys[candidate] = (
            primary,
            positive_folds,
            exp026._profit_factor_order_value(pooled_pf, prefix="pooled_"),
            -pooled_drawdown,
            simplicity[candidate],
        )
    selected = max(CANDIDATES, key=lambda name: keys[name])
    return selected, {
        "primary_statistic": "median ACTIVE validation-fold net_bps_per_trade",
        "active_fold_count": len(active_folds),
        "abstention_fold_count": 4 - len(active_folds),
        "abstention_folds_excluded": True,
        "tie_break_order": [
            "more ACTIVE folds with positive total net bps",
            "higher pooled profit factor over executed ACTIVE-fold trades",
            "lower pooled maximum drawdown over executed ACTIVE-fold trades",
            "simpler candidate B then C then A",
        ],
        "candidates": diagnostics,
        "selected_candidate": selected,
    }


def freeze_final_parameters(
    days: Mapping[date, DirectionDay], selected_candidate: str
) -> dict[str, Any]:
    if tuple(sorted(days)) != HISTORICAL_DAYS:
        raise ProtocolViolation("final freeze calendar differs from exact Jan-Jul")
    if selected_candidate not in CANDIDATES:
        raise ProtocolViolation("final freeze candidate is not A/B/C")
    ordered = [days[day] for day in HISTORICAL_DAYS]
    all_rv = exp026._concat(ordered, "rv_30m_bps").reshape(-1, 1)
    all_opportunity_y = exp026._concat(ordered, "opportunity_label")
    opportunity_model = _fit_readiness_logistic(
        all_rv,
        all_opportunity_y,
        context="final Jan-Jul opportunity model",
    )
    training_probabilities = opportunity_model.predict_proba(all_rv)
    final_trigger = training_probability_trigger(training_probabilities)
    result: dict[str, Any] = {
        "selected_direction_candidate": selected_candidate,
        "opportunity_model": exp026._model_record(opportunity_model),
        "opportunity_training_support_count": int(len(all_rv)),
        "final_historical_probability_trigger": final_trigger,
        "trigger_source": "full_Jan_Jul_training_probabilities_only",
        "trigger_probability_support_count": int(len(training_probabilities)),
        "trigger_quantile": OPPORTUNITY_QUANTILE,
        "trigger_quantile_method": OPPORTUNITY_QUANTILE_METHOD,
        "training_dates": list(HISTORICAL_DAY_STRINGS),
    }
    if selected_candidate == "A":
        X_direction = exp026._concat(ordered, "X_direction")
        y_direction = exp026._concat(ordered, "long_preferred")
        model = _fit_readiness_logistic(
            X_direction,
            y_direction,
            context="final Jan-Jul Candidate A direction model",
        )
        result["direction_model"] = exp026._model_record(model)
        result["direction_training_support_count"] = int(len(X_direction))
        result["direction_rule"] = None
    else:
        result["direction_model"] = None
        result["direction_training_support_count"] = None
        result["direction_rule"] = (
            "ret_10m_bps >= 0 -> LONG; else SHORT"
            if selected_candidate == "B"
            else "ret_10m_bps >= 0 -> SHORT; else LONG"
        )
    return result


def historical_selection_core(days: Mapping[date, DirectionDay]) -> CoreSelection:
    if tuple(sorted(days)) != HISTORICAL_DAYS:
        raise ProtocolViolation("historical day mapping is not exact Jan-Jul calendar")
    public_folds: list[dict[str, Any]] = []
    private_folds: list[dict[str, Any]] = []
    states: list[str] = []
    for fold_number, (train_dates, validation_date) in enumerate(FOLDS, start=1):
        fitted = _fit_fold([days[day] for day in train_dates], days[validation_date])
        state = _fold_state(fitted)
        states.append(state)
        private_folds.append({**fitted, "state": state})
        public_folds.append(
            {
                "fold": fold_number,
                "train_dates": [day.isoformat() for day in train_dates],
                "validation_date": validation_date.isoformat(),
                "state": state,
                "trigger_threshold": fitted["trigger_threshold"],
                "trigger_quantile": fitted["trigger_quantile"],
                "trigger_quantile_method": fitted["trigger_quantile_method"],
                "trigger_source": fitted["trigger_source"],
                "validation_probabilities_used_for_trigger": fitted[
                    "validation_probabilities_used_for_trigger"
                ],
                "training_probability_count": fitted["training_probability_count"],
                "validation_common_support_count": fitted[
                    "validation_common_support_count"
                ],
                "candidates": {
                    candidate: _reported_fold_metrics(
                        fitted["candidates"][candidate], state
                    )
                    for candidate in CANDIDATES
                },
            }
        )
    state_tuple = tuple(states)
    active_count = int(sum(state == ACTIVE for state in state_tuple))
    feasible = selection_is_feasible(state_tuple)
    if not feasible:
        return CoreSelection(
            dict(days),
            public_folds,
            private_folds,
            state_tuple,
            active_count,
            False,
            None,
            None,
            None,
            f"active_fold_count={active_count} is below required {MIN_ACTIVE_FOLDS}",
        )
    selected, diagnostic = select_candidate(private_folds)
    final_models = freeze_final_parameters(days, selected)
    return CoreSelection(
        dict(days),
        public_folds,
        private_folds,
        state_tuple,
        active_count,
        True,
        selected,
        diagnostic,
        final_models,
        None,
    )


def verify_frozen_references(workspace: Path) -> dict[str, Any]:
    preregistration = workspace / PREREGISTRATION_REL
    parent_result = workspace / PARENT_RESULT_REL
    if sha256_file(preregistration) != PREREGISTRATION_SHA256:
        raise ProtocolViolation("EXP028 preregistration SHA-256 mismatch")
    if sha256_file(parent_result) != PARENT_RESULT_SHA256:
        raise ProtocolViolation("EXP026 result artifact SHA-256 mismatch")
    with parent_result.open("r", encoding="utf-8") as handle:
        parent = json.load(handle)
    if parent.get("experiment_id") != PARENT_EXPERIMENT_ID:
        raise ProtocolViolation("EXP026 parent experiment identity mismatch")
    if parent.get("status") != PARENT_STATUS:
        raise ProtocolViolation("EXP026 parent status mismatch")
    if parent.get("frozen_git_commit") != EXP026_IMPLEMENTATION_COMMIT:
        raise ProtocolViolation("EXP026 frozen implementation commit mismatch")
    return {
        "preregistration": {
            "commit": PREREGISTRATION_COMMIT,
            "path": PREREGISTRATION_REL,
            "sha256": PREREGISTRATION_SHA256,
        },
        "exp026_parent": {
            "experiment_id": PARENT_EXPERIMENT_ID,
            "fail_commit": EXP026_FAIL_COMMIT,
            "implementation_commit": EXP026_IMPLEMENTATION_COMMIT,
            "path": PARENT_RESULT_REL,
            "sha256": PARENT_RESULT_SHA256,
            "status": PARENT_STATUS,
        },
    }


def _static_invariants(
    *,
    references_verified: bool,
    lineage_verified: bool,
    provenance_verified: bool,
    protocol_clean: bool,
) -> dict[str, bool]:
    upstream = exp026.scientific_configuration()
    current = scientific_configuration()
    values = {
        "no_protocol_violation_detected": bool(protocol_clean),
        "preregistration_sha_verified": bool(references_verified),
        "exp026_parent_sha_status_and_commit_verified": bool(references_verified),
        "frozen_lineage_ancestry_verified": bool(lineage_verified),
        "historical_input_provenance_verified": bool(provenance_verified),
        "exact_jan_jul_historical_calendar": bool(
            HISTORICAL_DAYS == exp026.HISTORICAL_DAYS
            and len(HISTORICAL_DAYS) == 7
        ),
        "exactly_four_expanding_folds": bool(FOLDS == exp026.FOLDS and len(FOLDS) == 4),
        "candidate_set_exactly_A_B_C": bool(CANDIDATES == ("A", "B", "C")),
        "opportunity_configuration_unchanged": bool(
            all(
                current[key] == upstream[key]
                for key in (
                    "symbol", "opportunity_feature", "decision_step_rows",
                    "decision_step_us", "grid_us", "entry_steps", "entry_delay_us",
                    "horizon_s", "horizon_steps", "opportunity_label_threshold_bps",
                    "opportunity_trigger_quantile", "opportunity_trigger_quantile_method",
                    "model",
                )
            )
        ),
        "direction_configuration_unchanged": bool(
            current["direction_features"] == upstream["direction_features"]
            and current["candidates"] == upstream["candidates"]
            and current["direction_probability_threshold"]
            == upstream["direction_probability_threshold"]
        ),
        "trigger_quantile_exactly_0_90_higher": bool(
            OPPORTUNITY_QUANTILE == 0.90
            and OPPORTUNITY_QUANTILE_METHOD == "higher"
        ),
        "execution_timing_and_costs_unchanged": bool(
            DECISION_STEP_US == 60_000_000
            and ENTRY_DELAY_US == 250_000
            and HOLDING_DURATION_US == 600_000_000
            and PRIMARY_COST_BPS == 14.0
            and STRESS_COST_BPS == 20.0
        ),
        "aug30_analytically_opened_false": bool(AUG30_ANALYTICALLY_OPENED is False),
        "sep01_or_later_opened_false": bool(SEP01_OR_LATER_OPENED is False),
        "network_accessed_false": bool(NETWORK_ACCESSED is False),
        "no_leverage_sl_tp_sizing_posthoc_or_threshold_rescue": bool(
            current["execution"]["leverage"] is False
            and current["execution"]["stop_loss"] is False
            and current["execution"]["take_profit"] is False
            and current["execution"]["position_sizing_optimization"] is False
            and current["execution"]["post_hoc_filtering"] is False
            and current["opportunity_trigger_quantile"] == 0.90
        ),
    }
    exp026.validate_builtin_bool_invariants(values)
    return values


def build_readiness_invariants(
    core: CoreSelection | None,
    *,
    references_verified: bool,
    lineage_verified: bool,
    provenance_verified: bool,
    protocol_clean: bool,
    pipeline_completed: bool,
) -> dict[str, bool]:
    values = _static_invariants(
        references_verified=references_verified,
        lineage_verified=lineage_verified,
        provenance_verified=provenance_verified,
        protocol_clean=protocol_clean,
    )
    evaluated = bool(pipeline_completed and core is not None)
    folds = core.folds if core is not None else []
    metrics = [item for fold in folds for item in fold.get("candidates", {}).values()]
    abstention_metrics = [
        item
        for fold in folds
        if fold.get("state") == ABSTENTION
        for item in fold.get("candidates", {}).values()
    ]
    values.update(
        {
            "execution_invariants_evaluated": bool(evaluated),
            "all_four_folds_processed": bool(evaluated and len(folds) == 4),
            "historical_common_support_equals_parent_valid_R": bool(
                evaluated
                and tuple(sorted(core.days)) == HISTORICAL_DAYS
                and all(day.parent_support_exact is True for day in core.days.values())
            ),
            "every_fold_trigger_training_probabilities_only": bool(
                evaluated
                and all(fold.get("trigger_source") == "training_probabilities_only" for fold in folds)
            ),
            "no_validation_derived_threshold": bool(
                evaluated
                and all(fold.get("validation_probabilities_used_for_trigger") is False for fold in folds)
            ),
            "active_abstention_pattern_identical_across_candidates": bool(
                evaluated
                and all(
                    all(item.get("state") == fold.get("state") for item in fold["candidates"].values())
                    for fold in folds
                )
            ),
            "abstention_representation_exact": bool(
                evaluated
                and all(
                    item["executed_nonoverlapping_trade_count"] == 0
                    and item["realized_total_pnl_bps_at_14bp"] == 0.0
                    and item["exposure_fraction"] == 0.0
                    and item["net_bps_per_trade"] is None
                    and item["mean_net_bps_per_trade"] is None
                    and item["median_net_bps_per_trade"] is None
                    for item in abstention_metrics
                )
            ),
            "nonoverlap_accounting_consistent": bool(
                evaluated
                and bool(metrics)
                and all(
                    item["eligible_signal_count"]
                    == item["executed_nonoverlapping_trade_count"]
                    + item["ignored_eligible_signals_while_open"]
                    and item["nonoverlap_accounting_consistent"] is True
                    for item in metrics
                )
            ),
            "no_position_overlap": bool(
                evaluated and bool(metrics)
                and all(item["no_position_overlap"] is True for item in metrics)
            ),
            "exposure_fraction_finite_and_bounded": bool(
                evaluated
                and bool(metrics)
                and all(
                    type(item["exposure_fraction"]) is float
                    and math.isfinite(item["exposure_fraction"])
                    and 0.0 <= item["exposure_fraction"] <= 1.0
                    for item in metrics
                )
            ),
            "executed_trade_timing_exact": bool(
                evaluated and bool(metrics)
                and all(item["executed_trade_timing_exact"] is True for item in metrics)
            ),
            "historical_selection_pipeline_completed": bool(pipeline_completed),
            "at_least_three_active_folds": bool(
                evaluated and core.active_fold_count >= MIN_ACTIVE_FOLDS
            ),
            "exactly_one_candidate_selected": bool(
                evaluated
                and core.selected_candidate in CANDIDATES
                and core.selection_feasible
            ),
            "final_jan_jul_parameters_recorded": bool(
                evaluated and core.final_models is not None
            ),
            "final_trigger_from_full_jan_jul_training_probabilities_only": bool(
                evaluated
                and core.final_models is not None
                and core.final_models.get("trigger_source")
                == "full_Jan_Jul_training_probabilities_only"
                and core.final_models.get("trigger_quantile") == 0.90
                and core.final_models.get("trigger_quantile_method") == "higher"
            ),
            "final_direction_freeze_matches_selected_candidate": bool(
                evaluated
                and core.final_models is not None
                and core.final_models.get("selected_direction_candidate")
                == core.selected_candidate
                and (
                    (core.selected_candidate == "A" and core.final_models.get("direction_model") is not None)
                    or (
                        core.selected_candidate in ("B", "C")
                        and core.final_models.get("direction_model") is None
                        and type(core.final_models.get("direction_rule")) is str
                    )
                )
            ),
        }
    )
    exp026.validate_builtin_bool_invariants(values)
    return values


def invariant_groups() -> dict[str, list[str]]:
    return {
        "static_protocol_and_provenance": list(STATIC_INVARIANT_NAMES),
        "evaluated_execution": ["execution_invariants_evaluated", *EXECUTION_INVARIANT_NAMES],
        "readiness": list(READINESS_INVARIANT_NAMES),
    }


def adjudicate_readiness(invariants: Mapping[str, Any]) -> str:
    try:
        checked = exp026.validate_builtin_bool_invariants(invariants)
    except Exception as error:
        raise ProtocolViolation("invalid invariant type") from error
    required = set(STATIC_INVARIANT_NAMES) | set(EXECUTION_INVARIANT_NAMES) | set(
        READINESS_INVARIANT_NAMES
    ) | {"execution_invariants_evaluated"}
    if set(checked) != required:
        raise ProtocolViolation("invariant names differ from frozen EXP028 schema")
    if not exp026.adjudicate_invariants(
        {name: checked[name] for name in STATIC_INVARIANT_NAMES}
    ):
        return INVALID_STATUS
    if not checked["historical_selection_pipeline_completed"]:
        return FAIL_STATUS
    if not checked["execution_invariants_evaluated"]:
        return INVALID_STATUS
    if not exp026.adjudicate_invariants(
        {name: checked[name] for name in EXECUTION_INVARIANT_NAMES}
    ):
        return INVALID_STATUS
    return (
        PASS_STATUS
        if exp026.adjudicate_invariants(
            {name: checked[name] for name in READINESS_INVARIANT_NAMES}
        )
        else FAIL_STATUS
    )


def _public_core(core: CoreSelection) -> dict[str, Any]:
    return {
        "folds": core.folds,
        "fold_states": list(core.fold_states),
        "active_fold_count": core.active_fold_count,
        "abstention_fold_count": 4 - core.active_fold_count,
        "selection_feasible": core.selection_feasible,
        "selected_candidate": core.selected_candidate,
        "candidate_selection": core.candidate_selection,
        "final_models": core.final_models,
        "readiness_failure_reason": core.readiness_failure_reason,
    }


def _verify_training_inputs(feature_root: Path, workspace: Path) -> list[dict[str, Any]]:
    if feature_root != AUTHORIZED_FEATURE_ROOT:
        raise ProtocolViolation("historical feature root differs from frozen EXP026 root")
    return exp026._verify_training_inputs(feature_root, workspace)


def _load_historical_days(manifest: Sequence[Mapping[str, Any]]) -> dict[date, DirectionDay]:
    return exp026._load_historical_days(manifest)


def _input_manifest_with_roles(
    manifest: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return exp026._input_manifest_with_roles(manifest)


def _is_ancestor(workspace: Path, ancestor: str, descendant: str) -> bool:
    return exp026._is_ancestor(workspace, ancestor, descendant)


def _fresh_output(output: Path) -> Path:
    return exp026._fresh_output(output)


def _write_once(output: Path, payload: Mapping[str, Any]) -> str:
    return exp026._write_once(output, payload)


def run_historical_selection(
    workspace: Path,
    frozen_commit: str,
    output: Path,
    *,
    argv: Sequence[str] | None = None,
) -> RunWriteResult:
    _fresh_output(output)
    started = _utc_now()
    run_id = f"CODEX-RUN-EXP028-{started.replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:8]}"
    config = scientific_configuration()
    references: dict[str, Any] | None = None
    manifest: list[dict[str, Any]] = []
    core: CoreSelection | None = None
    references_verified = False
    lineage_verified = False
    provenance_verified = False
    protocol_clean = True
    pipeline_completed = False
    failure_reason: str | None = None
    try:
        exp026.assert_frozen_workspace(workspace, frozen_commit)
        if not _is_ancestor(workspace, PREREGISTRATION_COMMIT, frozen_commit):
            raise ProtocolViolation("EXP028 preregistration commit is not an ancestor")
        if not _is_ancestor(workspace, EXP026_FAIL_COMMIT, frozen_commit):
            raise ProtocolViolation("EXP026 frozen FAIL commit is not an ancestor")
        lineage_verified = True
        references = verify_frozen_references(workspace)
        references_verified = True
        manifest = _input_manifest_with_roles(
            _verify_training_inputs(AUTHORIZED_FEATURE_ROOT, workspace)
        )
        provenance_verified = True
        core = historical_selection_core(_load_historical_days(manifest))
        pipeline_completed = True
        failure_reason = core.readiness_failure_reason
    except SelectionReadinessFailure as error:
        failure_reason = str(error)
    except Exception as error:
        protocol_clean = False
        failure_reason = f"{type(error).__name__}: {error}"

    invariants = build_readiness_invariants(
        core,
        references_verified=references_verified,
        lineage_verified=lineage_verified,
        provenance_verified=provenance_verified,
        protocol_clean=protocol_clean,
        pipeline_completed=pipeline_completed,
    )
    status = adjudicate_readiness(invariants)
    tracked_dirty = bool(
        exp026._git(workspace, "status", "--porcelain", "--untracked-files=no")
    )
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
        "upstream_exp026_configuration_sha256": exp026.SCIENTIFIC_CONFIGURATION_SHA256,
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
            "decision_at_t_plus_600s_blocked_until_t_plus_600_25s": True,
            "primary_incremental_cost_bps": PRIMARY_COST_BPS,
            "stress_incremental_cost_bps": STRESS_COST_BPS,
            "flat_only": True,
            "pyramiding": False,
        },
        "historical_selection": _public_core(core) if core is not None else None,
        "invariants": invariants,
        "invariant_groups": invariant_groups(),
        "sealed_future_data_assertions": {
            "AUG30_ANALYTICALLY_OPENED": AUG30_ANALYTICALLY_OPENED,
            "SEP01_OR_LATER_OPENED": SEP01_OR_LATER_OPENED,
            "NETWORK_ACCESSED": NETWORK_ACCESSED,
        },
        "output_sha256": None,
        "output_sha256_semantics": "computed and reported after atomic write; not self-embedded",
    }
    digest = _write_once(output, payload)
    return RunWriteResult(exp026.normalize_json_safe(payload), digest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CODEX-EXP-028-P0 historical readiness")
    parser.add_argument("--mode", choices=("historical-selection",), required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    effective_argv = list(argv) if argv is not None else sys.argv[1:]
    result = run_historical_selection(
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

from __future__ import annotations

import contextlib
import inspect
import io
import json
import math
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from multimarket import codex_exp026_p0 as exp026
from multimarket import codex_exp028_p0 as p0
from multimarket.codex_exp004_p1 import R_FEATURE_NAMES
from multimarket.v23_phase0dl_score import DayData


WORKSPACE = Path(__file__).resolve().parents[1]


def direction_day(day: date = p0.HISTORICAL_DAYS[0], n: int = 12) -> p0.DirectionDay:
    decisions = np.arange(n, dtype=np.int64) * p0.DECISION_STEP_US
    entries = decisions + p0.ENTRY_DELAY_US
    exits = entries + p0.HOLDING_DURATION_US
    features = np.column_stack(
        [np.linspace(-2.0 + column, 2.0 + column, n) for column in range(7)]
    )
    return p0.DirectionDay(
        day=day,
        timestamp_us=decisions,
        entry_timestamp_us=entries,
        exit_timestamp_us=exits,
        X_direction=features,
        rv_30m_bps=features[:, 5],
        ret_10m_bps=features[:, 3],
        opportunity_label=(np.arange(n) % 2).astype(np.int8),
        long_preferred=(np.arange(n) % 2).astype(np.int8),
        long_gross_bps=np.full(n, 30.0),
        short_gross_bps=np.full(n, 5.0),
        common_support=np.ones(n, dtype=bool),
        parent_support_exact=True,
    )


def evaluation(net_values: list[float]) -> p0.ExecutionEvaluation:
    net = np.asarray(net_values, dtype=float)
    count = len(net)
    metrics = {
        "eligible_signal_count": count,
        "executed_nonoverlapping_trade_count": count,
        "ignored_eligible_signals_while_open": 0,
        "long_count": count,
        "short_count": 0,
        "gross_total_bps": float(np.sum(net + p0.PRIMARY_COST_BPS)),
        "net_total_bps_at_14bp": float(np.sum(net)),
        "mean_net_bps_per_trade": float(np.mean(net)) if count else None,
        "median_net_bps_per_trade": float(np.median(net)) if count else None,
        "win_rate": float(np.mean(net > 0)) if count else None,
        **exp026.profit_factor_diagnostic(net),
        "maximum_drawdown_cumulative_net_bps": exp026.maximum_drawdown_bps(net),
        "exposure_fraction": float(count * p0.HOLDING_DURATION_US / exp026.DAY_US),
        "stress_total_bps_at_20bp": float(np.sum(net - 6.0)),
        "nonoverlap_accounting_consistent": True,
        "no_position_overlap": True,
        "executed_trade_timing_exact": True,
    }
    entries = np.arange(count, dtype=np.int64) * 700_000_000 + p0.ENTRY_DELAY_US
    return p0.ExecutionEvaluation(metrics, net, entries, entries + p0.HOLDING_DURATION_US)


def fitted_fold(
    state: str,
    values: dict[str, list[float]] | None = None,
) -> dict[str, object]:
    if values is None:
        values = {
            candidate: ([1.0] if state == p0.ACTIVE else [])
            for candidate in p0.CANDIDATES
        }
    return {
        "trigger_threshold": 0.75,
        "trigger_quantile": 0.90,
        "trigger_quantile_method": "higher",
        "trigger_source": "training_probabilities_only",
        "validation_probabilities_used_for_trigger": False,
        "training_probability_count": 10,
        "validation_common_support_count": 3,
        "candidates": {
            candidate: evaluation(values[candidate]) for candidate in p0.CANDIDATES
        },
    }


def private_folds(
    states: tuple[str, ...],
    candidate_values: dict[str, list[float]] | None = None,
) -> list[dict[str, object]]:
    result = []
    active_index = 0
    for state in states:
        if state == p0.ACTIVE:
            values = (
                {
                    candidate: [candidate_values[candidate][active_index]]
                    for candidate in p0.CANDIDATES
                }
                if candidate_values is not None
                else None
            )
            active_index += 1
        else:
            values = {candidate: [] for candidate in p0.CANDIDATES}
        result.append({**fitted_fold(state, values), "state": state})
    return result


def core_for_states(states: tuple[str, ...], selected: str | None = "B") -> p0.CoreSelection:
    days = {day: direction_day(day, 3) for day in p0.HISTORICAL_DAYS}
    private = private_folds(states)
    public = []
    for number, ((train, validation), fold) in enumerate(
        zip(p0.FOLDS, private), start=1
    ):
        state = fold["state"]
        public.append(
            {
                "fold": number,
                "train_dates": [day.isoformat() for day in train],
                "validation_date": validation.isoformat(),
                "state": state,
                "trigger_threshold": fold["trigger_threshold"],
                "trigger_quantile": 0.90,
                "trigger_quantile_method": "higher",
                "trigger_source": "training_probabilities_only",
                "validation_probabilities_used_for_trigger": False,
                "training_probability_count": 10,
                "validation_common_support_count": 3,
                "candidates": {
                    candidate: p0._reported_fold_metrics(
                        fold["candidates"][candidate], state
                    )
                    for candidate in p0.CANDIDATES
                },
            }
        )
    active_count = states.count(p0.ACTIVE)
    feasible = active_count >= p0.MIN_ACTIVE_FOLDS
    chosen = selected if feasible else None
    final = None
    diagnostic = None
    if chosen is not None:
        final = {
            "selected_direction_candidate": chosen,
            "final_historical_probability_trigger": 0.8,
            "trigger_source": "full_Jan_Jul_training_probabilities_only",
            "trigger_quantile": 0.90,
            "trigger_quantile_method": "higher",
            "direction_model": {"coefficient": [1.0]} if chosen == "A" else None,
            "direction_rule": (
                None
                if chosen == "A"
                else "ret_10m_bps >= 0 -> LONG; else SHORT"
                if chosen == "B"
                else "ret_10m_bps >= 0 -> SHORT; else LONG"
            ),
        }
        diagnostic = {"selected_candidate": chosen}
    return p0.CoreSelection(
        days=days,
        folds=public,
        private_folds=private,
        fold_states=states,
        active_fold_count=active_count,
        selection_feasible=feasible,
        selected_candidate=chosen,
        candidate_selection=diagnostic,
        final_models=final,
        readiness_failure_reason=(None if feasible else "insufficient ACTIVE folds"),
    )


def passing_invariants() -> dict[str, bool]:
    names = {
        *p0.STATIC_INVARIANT_NAMES,
        *p0.EXECUTION_INVARIANT_NAMES,
        *p0.READINESS_INVARIANT_NAMES,
        "execution_invariants_evaluated",
    }
    return {name: True for name in names}


def manifest() -> list[dict[str, object]]:
    return [
        {
            "symbol": p0.SYMBOL,
            "day": day.isoformat(),
            "path": str(p0.authorized_feature_path(day)),
            "bytes": 123,
            "sha256": "a" * 64,
            "frozen_provenance_match": True,
        }
        for day in p0.HISTORICAL_DAYS
    ]


class IdentityAndAccessTests(unittest.TestCase):
    def test_exact_preregistration_commit_and_sha(self) -> None:
        self.assertEqual(
            p0.PREREGISTRATION_COMMIT,
            "07918d88db4e77a9c608243b9629774d43ee8d7f",
        )
        self.assertEqual(
            p0.PREREGISTRATION_SHA256,
            "0140f1187e6937b565f544b6f92b06b15b1ce601004ad87229223a4d64e9b901",
        )
        result = p0.verify_frozen_references(WORKSPACE)
        self.assertEqual(result["preregistration"]["sha256"], p0.PREREGISTRATION_SHA256)

    def test_exact_exp026_parent_fail_artifact(self) -> None:
        result = p0.verify_frozen_references(WORKSPACE)["exp026_parent"]
        self.assertEqual(
            result["sha256"],
            "b852a1c28957411efab259b12b7b68d941fa4850f39c489fd96de752bdb26e27",
        )
        self.assertEqual(result["status"], "FAIL_DIRECTION_EXECUTION_PIPELINE_NOT_READY")
        self.assertEqual(result["implementation_commit"], p0.EXP026_IMPLEMENTATION_COMMIT)

    def test_exact_status_vocabulary(self) -> None:
        self.assertEqual(
            p0.PASS_STATUS,
            "ABSTENTION_AWARE_DIRECTION_PIPELINE_READY_FOR_FRESH_PROSPECTIVE_VALIDATION",
        )
        self.assertEqual(
            p0.FAIL_STATUS, "FAIL_ABSTENTION_AWARE_DIRECTION_PIPELINE_NOT_READY"
        )
        self.assertEqual(p0.INVALID_STATUS, "INVALID")

    def test_exact_jan_jul_allowlist(self) -> None:
        self.assertEqual(
            p0.HISTORICAL_DAYS,
            tuple(date(2026, month, 1) for month in range(1, 8)),
        )
        self.assertEqual(p0.AUTHORIZED_FEATURE_ROOT, exp026.AUTHORIZED_FEATURE_ROOT)

    def test_aug30_rejected_before_open(self) -> None:
        with mock.patch.object(Path, "open") as opened:
            with self.assertRaises(p0.ProtocolViolation):
                p0.authorized_feature_path(date(2026, 8, 30))
            opened.assert_not_called()

    def test_sep01_and_later_rejected_before_open(self) -> None:
        with mock.patch.object(Path, "open") as opened:
            for forbidden in (date(2026, 9, 1), date(2027, 1, 1)):
                with self.assertRaises(p0.ProtocolViolation):
                    p0.authorized_feature_path(forbidden)
            opened.assert_not_called()

    def test_no_network_acquisition_or_arbitrary_data_interface(self) -> None:
        source = inspect.getsource(p0)
        for forbidden in (
            "requests", "websocket", "urllib", "--date", "--feature-root", "glob("
        ):
            self.assertNotIn(forbidden, source)
        destinations = {action.dest for action in p0.build_parser()._actions}
        self.assertEqual(
            destinations, {"help", "mode", "workspace", "frozen_commit", "output"}
        )


class ScientificSemanticsTests(unittest.TestCase):
    def test_opportunity_configuration_is_unchanged(self) -> None:
        current = p0.scientific_configuration()
        parent = exp026.scientific_configuration()
        for key in (
            "symbol", "opportunity_feature", "decision_step_rows", "decision_step_us",
            "grid_us", "entry_steps", "entry_delay_us", "horizon_s", "horizon_steps",
            "opportunity_label_threshold_bps", "opportunity_trigger_quantile",
            "opportunity_trigger_quantile_method", "model",
        ):
            self.assertEqual(current[key], parent[key])

    def test_candidate_abc_definitions_are_unchanged(self) -> None:
        self.assertEqual(p0.CANDIDATES, ("A", "B", "C"))
        self.assertEqual(p0.DIRECTION_FEATURE_NAMES, exp026.DIRECTION_FEATURE_NAMES)
        values = np.asarray([-1.0, 0.0, 1.0])
        np.testing.assert_array_equal(
            p0.candidate_b_direction(values), [False, True, True]
        )
        np.testing.assert_array_equal(
            p0.candidate_c_direction(values), [True, False, False]
        )
        np.testing.assert_array_equal(
            p0.direction_label([2.0, 1.0], [1.0, 1.0]), [1, 0]
        )

    def test_training_trigger_uses_higher(self) -> None:
        values = np.asarray([0.1, 0.2, 0.8])
        with mock.patch.object(exp026.np, "quantile", wraps=np.quantile) as quantile:
            self.assertEqual(p0.training_probability_trigger(values), 0.8)
        self.assertEqual(quantile.call_args.kwargs["method"], "higher")
        self.assertEqual(quantile.call_args.args[1], 0.90)

    def test_candidate_a_strict_binary_guard_accepts_binary(self) -> None:
        model = p0._fit_readiness_logistic(
            np.arange(4, dtype=float).reshape(-1, 1),
            np.asarray([0, 1, 0, 1]),
            context="Candidate A",
        )
        self.assertIsInstance(model, exp026.FixedLogistic)

    def test_one_class_candidate_a_is_clean_readiness_failure(self) -> None:
        for labels in ([0, 0, 0], [1, 1, 1]):
            with self.subTest(labels=labels), self.assertRaises(
                p0.SelectionReadinessFailure
            ):
                p0._fit_readiness_logistic(
                    np.arange(3, dtype=float).reshape(-1, 1),
                    np.asarray(labels),
                    context="Candidate A",
                )

    def test_malformed_nonbinary_nonfinite_labels_are_protocol_violations(self) -> None:
        cases = (
            (np.ones((2, 1)), np.asarray([[0], [1]])),
            (np.ones((2, 1)), np.asarray([0, 2])),
            (np.ones((2, 1)), np.asarray([-1, 1])),
            (np.ones((3, 1)), np.asarray([0.0, 0.5, 1.0])),
            (np.ones((3, 1)), np.asarray([0.0, math.nan, 1.0])),
        )
        for X, y in cases:
            with self.subTest(y=y), self.assertRaises(p0.ProtocolViolation):
                p0._fit_readiness_logistic(X, y, context="Candidate A")


class FoldStateTests(unittest.TestCase):
    def test_active_fold_has_at_least_one_executed_trade(self) -> None:
        fold = fitted_fold(p0.ACTIVE)
        self.assertEqual(p0._fold_state(fold), p0.ACTIVE)
        self.assertGreater(
            fold["candidates"]["A"].metrics["executed_nonoverlapping_trade_count"],
            0,
        )

    def test_abstention_fold_has_zero_executed_trades(self) -> None:
        fold = fitted_fold(p0.ABSTENTION)
        self.assertEqual(p0._fold_state(fold), p0.ABSTENTION)
        self.assertEqual(
            fold["candidates"]["B"].metrics["executed_nonoverlapping_trade_count"],
            0,
        )

    def test_abstention_metrics_are_zero_and_undefined_exactly(self) -> None:
        metrics = p0._reported_fold_metrics(evaluation([]), p0.ABSTENTION)
        self.assertEqual(metrics["realized_total_pnl_bps_at_14bp"], 0.0)
        self.assertEqual(metrics["exposure_fraction"], 0.0)
        self.assertIsNone(metrics["net_bps_per_trade"])
        self.assertIsNone(metrics["mean_net_bps_per_trade"])
        self.assertIsNone(metrics["median_net_bps_per_trade"])

    def test_abstention_not_converted_to_synthetic_zero_observation(self) -> None:
        metrics = p0._reported_fold_metrics(evaluation([]), p0.ABSTENTION)
        self.assertIsNone(metrics["net_bps_per_trade"])
        self.assertNotEqual(metrics["net_bps_per_trade"], 0.0)

    def test_active_abstention_pattern_must_match_across_candidates(self) -> None:
        fold = fitted_fold(p0.ACTIVE)
        fold["candidates"]["C"] = evaluation([])
        with self.assertRaises(p0.ProtocolViolation):
            p0._fold_state(fold)

    def test_four_active_folds_are_feasible(self) -> None:
        self.assertTrue(p0.selection_is_feasible((p0.ACTIVE,) * 4))

    def test_exactly_three_active_folds_are_feasible(self) -> None:
        self.assertTrue(
            p0.selection_is_feasible((p0.ACTIVE,) * 3 + (p0.ABSTENTION,))
        )

    def test_exactly_two_active_folds_are_cleanly_infeasible(self) -> None:
        states = (p0.ACTIVE, p0.ABSTENTION, p0.ACTIVE, p0.ABSTENTION)
        self.assertFalse(p0.selection_is_feasible(states))
        with self.assertRaises(p0.SelectionReadinessFailure):
            p0.select_candidate(private_folds(states))

    def test_all_four_folds_processed_even_when_first_abstains(self) -> None:
        states = (p0.ABSTENTION, p0.ACTIVE, p0.ACTIVE, p0.ACTIVE)
        fitted = [fitted_fold(state) for state in states]
        days = {day: direction_day(day, 3) for day in p0.HISTORICAL_DAYS}
        with mock.patch.object(
            p0, "_fit_fold", side_effect=fitted
        ) as fit, mock.patch.object(
            p0,
            "freeze_final_parameters",
            return_value={
                "selected_direction_candidate": "B",
                "trigger_source": "full_Jan_Jul_training_probabilities_only",
                "trigger_quantile": 0.90,
                "trigger_quantile_method": "higher",
                "direction_model": None,
                "direction_rule": "ret_10m_bps >= 0 -> LONG; else SHORT",
            },
        ):
            core = p0.historical_selection_core(days)
        self.assertEqual(fit.call_count, 4)
        self.assertEqual(core.fold_states, states)
        self.assertTrue(core.selection_feasible)

    def test_two_active_core_is_clean_fail_without_final_refit(self) -> None:
        states = (p0.ACTIVE, p0.ABSTENTION, p0.ACTIVE, p0.ABSTENTION)
        days = {day: direction_day(day, 3) for day in p0.HISTORICAL_DAYS}
        with mock.patch.object(
            p0, "_fit_fold", side_effect=[fitted_fold(state) for state in states]
        ), mock.patch.object(p0, "freeze_final_parameters") as freeze:
            core = p0.historical_selection_core(days)
        freeze.assert_not_called()
        self.assertFalse(core.selection_feasible)
        self.assertEqual(core.active_fold_count, 2)
        self.assertIsNone(core.selected_candidate)


class ActiveOnlySelectionTests(unittest.TestCase):
    STATES = (p0.ACTIVE, p0.ABSTENTION, p0.ACTIVE, p0.ACTIVE)

    def test_primary_statistic_and_median_use_active_folds_only(self) -> None:
        values = {
            "A": [1.0, 3.0, 5.0],
            "B": [0.0, 0.0, 0.0],
            "C": [-1.0, -1.0, -1.0],
        }
        selected, diagnostic = p0.select_candidate(
            private_folds(self.STATES, values)
        )
        self.assertEqual(selected, "A")
        candidate = diagnostic["candidates"]["A"]
        self.assertEqual(
            candidate["active_validation_fold_net_bps_per_trade"],
            [1.0, 3.0, 5.0],
        )
        self.assertEqual(
            candidate["median_active_validation_fold_net_bps_per_trade"], 3.0
        )

    def test_abstention_excluded_from_positive_fold_tie_break(self) -> None:
        values = {
            "A": [1.0, -1.0, 1.0],
            "B": [0.0, 0.0, 0.0],
            "C": [-1.0] * 3,
        }
        _, diagnostic = p0.select_candidate(private_folds(self.STATES, values))
        self.assertEqual(
            diagnostic["candidates"]["A"]["positive_total_net_active_folds"], 2
        )
        self.assertEqual(diagnostic["candidates"]["A"]["active_fold_count"], 3)

    def test_pooled_profit_factor_uses_active_trades_only(self) -> None:
        values = {
            "A": [2.0, -1.0, 1.0],
            "B": [0.0] * 3,
            "C": [-1.0] * 3,
        }
        _, diagnostic = p0.select_candidate(private_folds(self.STATES, values))
        candidate = diagnostic["candidates"]["A"]
        self.assertEqual(candidate["pooled_active_fold_trade_count"], 3)
        self.assertEqual(candidate["pooled_profit_factor"], 3.0)

    def test_drawdown_uses_executed_active_trades_only(self) -> None:
        values = {
            "A": [2.0, -3.0, 1.0],
            "B": [0.0] * 3,
            "C": [-1.0] * 3,
        }
        _, diagnostic = p0.select_candidate(private_folds(self.STATES, values))
        expected = exp026.maximum_drawdown_bps(np.asarray([2.0, -3.0, 1.0]))
        self.assertEqual(
            diagnostic["candidates"]["A"][
                "pooled_active_fold_maximum_drawdown_bps"
            ],
            expected,
        )

    def test_simplicity_tie_break_is_b_then_c_then_a(self) -> None:
        values = {candidate: [1.0, 1.0, 1.0] for candidate in p0.CANDIDATES}
        selected, diagnostic = p0.select_candidate(
            private_folds(self.STATES, values)
        )
        self.assertEqual(selected, "B")
        self.assertEqual(
            diagnostic["tie_break_order"][-1], "simpler candidate B then C then A"
        )


class ExecutionAndSupportTests(unittest.TestCase):
    def test_t_plus_600_decision_is_blocked_until_t_plus_600_25(self) -> None:
        day = direction_day(n=12)
        result = p0.execute_nonoverlapping(
            day, np.ones(12), 0.5, np.ones(12, bool)
        )
        self.assertEqual(result.metrics["executed_nonoverlapping_trade_count"], 2)
        self.assertEqual(result.metrics["ignored_eligible_signals_while_open"], 10)
        self.assertEqual(result.entry_timestamp_us[1], 660_250_000)

    def test_direction_choices_share_identical_opportunity_schedule(self) -> None:
        day = direction_day(n=20)
        probability = np.ones(20)
        choices = (
            np.ones(20, dtype=bool),
            np.zeros(20, dtype=bool),
            (np.arange(20) % 2 == 0),
        )
        results = [
            p0.execute_nonoverlapping(day, probability, 0.5, choice)
            for choice in choices
        ]
        for result in results[1:]:
            for key in (
                "eligible_signal_count",
                "executed_nonoverlapping_trade_count",
                "ignored_eligible_signals_while_open",
            ):
                self.assertEqual(result.metrics[key], results[0].metrics[key])
            np.testing.assert_array_equal(
                result.entry_timestamp_us, results[0].entry_timestamp_us
            )
            np.testing.assert_array_equal(
                result.exit_timestamp_us, results[0].exit_timestamp_us
            )

    def test_exact_14bp_and_20bp_costs(self) -> None:
        result = p0.execute_nonoverlapping(
            direction_day(n=1), [1.0], 0.5, [True]
        )
        self.assertEqual(result.metrics["net_total_bps_at_14bp"], 16.0)
        self.assertEqual(result.metrics["stress_total_bps_at_20bp"], 10.0)

    def test_no_position_overlap(self) -> None:
        result = p0.execute_nonoverlapping(
            direction_day(n=20), np.ones(20), 0.5, np.ones(20, bool)
        )
        self.assertTrue(result.metrics["no_position_overlap"])
        self.assertTrue(
            np.all(result.entry_timestamp_us[1:] >= result.exit_timestamp_us[:-1])
        )

    def test_exact_parent_support_equivalence_is_reused(self) -> None:
        n = 2642
        ts = np.arange(n, dtype=np.int64) * exp026.GRID_US
        raw = DayData(
            p0.HISTORICAL_DAYS[0],
            ts,
            np.ones(n),
            np.ones(n) * 1.01,
            np.ones(n) * 1.005,
            np.ones(n, bool),
            {},
            {},
        )
        decisions = np.arange(0, n, exp026.DECISION_STEP_ROWS, dtype=np.int64)
        support = np.zeros(len(decisions), dtype=bool)
        support[0] = True
        X = np.full((len(decisions), len(R_FEATURE_NAMES)), np.nan)
        X[support] = 1.0
        frozen = SimpleNamespace(
            timestamp_us=ts[decisions],
            X_R=X,
            valid_R=support,
            y=np.zeros(len(decisions), dtype=np.int8),
        )
        long = np.full(len(decisions), np.nan)
        short = np.full(len(decisions), np.nan)
        oracle = np.full(len(decisions), np.nan)
        long[support], short[support], oracle[support] = 2.0, 1.0, 2.0
        outcomes = {
            "valid": support,
            "long_gross_bps": long,
            "short_gross_bps": short,
            "oracle_gross_bps": oracle,
            "entry_index": decisions + exp026.ENTRY_STEPS,
            "exit_index": decisions + exp026.ENTRY_STEPS + exp026.HORIZON_STEPS,
        }
        with mock.patch.object(
            exp026, "build_day_dataset", return_value=frozen
        ), mock.patch.object(
            exp026, "executable_fixed_horizon", return_value=outcomes
        ):
            adapted = exp026.build_direction_day(raw)
        np.testing.assert_array_equal(adapted.common_support, support)
        self.assertIs(adapted.parent_support_exact, True)


class FinalFreezeTests(unittest.TestCase):
    class FakeModel:
        def predict_proba(self, X):
            return np.linspace(0.1, 0.9, len(X))

    def _days(self) -> dict[date, p0.DirectionDay]:
        return {day: direction_day(day, 4) for day in p0.HISTORICAL_DAYS}

    def test_final_trigger_uses_full_jan_jul_training_probabilities_only(self) -> None:
        contexts: list[str] = []
        seen: list[int] = []

        def fit(X, y, *, context):
            contexts.append(context)
            return self.FakeModel()

        def trigger(values):
            seen.append(len(values))
            return 0.7

        with mock.patch.object(
            p0, "_fit_readiness_logistic", side_effect=fit
        ), mock.patch.object(
            p0, "training_probability_trigger", side_effect=trigger
        ), mock.patch.object(
            exp026, "_model_record", return_value={"frozen": True}
        ):
            result = p0.freeze_final_parameters(self._days(), "B")
        self.assertEqual(contexts, ["final Jan-Jul opportunity model"])
        self.assertEqual(seen, [28])
        self.assertEqual(result["opportunity_training_support_count"], 28)
        self.assertEqual(
            result["trigger_source"], "full_Jan_Jul_training_probabilities_only"
        )

    def test_final_candidate_a_refit_occurs_once_after_opportunity_fit(self) -> None:
        contexts: list[str] = []

        def fit(X, y, *, context):
            contexts.append(context)
            return self.FakeModel()

        with mock.patch.object(
            p0, "_fit_readiness_logistic", side_effect=fit
        ), mock.patch.object(
            p0, "training_probability_trigger", return_value=0.7
        ), mock.patch.object(
            exp026, "_model_record", return_value={"frozen": True}
        ):
            result = p0.freeze_final_parameters(self._days(), "A")
        self.assertEqual(
            contexts,
            [
                "final Jan-Jul opportunity model",
                "final Jan-Jul Candidate A direction model",
            ],
        )
        self.assertEqual(contexts.count("final Jan-Jul Candidate A direction model"), 1)
        self.assertIsNotNone(result["direction_model"])
        self.assertIsNone(result["direction_rule"])

    def test_final_b_is_exact_deterministic_rule_without_direction_refit(self) -> None:
        contexts: list[str] = []

        def fit(X, y, *, context):
            contexts.append(context)
            return self.FakeModel()

        with mock.patch.object(
            p0, "_fit_readiness_logistic", side_effect=fit
        ), mock.patch.object(
            p0, "training_probability_trigger", return_value=0.7
        ), mock.patch.object(
            exp026, "_model_record", return_value={"frozen": True}
        ):
            result = p0.freeze_final_parameters(self._days(), "B")
        self.assertEqual(contexts, ["final Jan-Jul opportunity model"])
        self.assertIsNone(result["direction_model"])
        self.assertEqual(
            result["direction_rule"], "ret_10m_bps >= 0 -> LONG; else SHORT"
        )

    def test_final_c_is_exact_deterministic_rule_without_direction_refit(self) -> None:
        contexts: list[str] = []

        def fit(X, y, *, context):
            contexts.append(context)
            return self.FakeModel()

        with mock.patch.object(
            p0, "_fit_readiness_logistic", side_effect=fit
        ), mock.patch.object(
            p0, "training_probability_trigger", return_value=0.7
        ), mock.patch.object(
            exp026, "_model_record", return_value={"frozen": True}
        ):
            result = p0.freeze_final_parameters(self._days(), "C")
        self.assertEqual(contexts, ["final Jan-Jul opportunity model"])
        self.assertIsNone(result["direction_model"])
        self.assertEqual(
            result["direction_rule"], "ret_10m_bps >= 0 -> SHORT; else LONG"
        )


class AdjudicationTests(unittest.TestCase):
    def test_pass_adjudication(self) -> None:
        self.assertEqual(p0.adjudicate_readiness(passing_invariants()), p0.PASS_STATUS)

    def test_clean_active_fold_count_below_three_is_fail(self) -> None:
        core = core_for_states(
            (p0.ACTIVE, p0.ABSTENTION, p0.ACTIVE, p0.ABSTENTION)
        )
        invariants = p0.build_readiness_invariants(
            core,
            references_verified=True,
            lineage_verified=True,
            provenance_verified=True,
            protocol_clean=True,
            pipeline_completed=True,
        )
        self.assertEqual(p0.adjudicate_readiness(invariants), p0.FAIL_STATUS)

    def test_provenance_causality_and_future_violations_are_invalid(self) -> None:
        for name in (
            "preregistration_sha_verified",
            "historical_input_provenance_verified",
            "no_protocol_violation_detected",
            "aug30_analytically_opened_false",
        ):
            invariants = passing_invariants()
            invariants[name] = False
            self.assertEqual(p0.adjudicate_readiness(invariants), p0.INVALID_STATUS)
        invariants = passing_invariants()
        invariants["no_position_overlap"] = False
        self.assertEqual(p0.adjudicate_readiness(invariants), p0.INVALID_STATUS)

    def test_invalid_invariant_type_never_passes(self) -> None:
        invariants = passing_invariants()
        invariants["network_accessed_false"] = np.bool_(True)
        with self.assertRaises(p0.ProtocolViolation):
            p0.adjudicate_readiness(invariants)


class OutputAndRunTests(unittest.TestCase):
    def _run(self, directory: str, core_effect) -> p0.RunWriteResult:
        days = {day: direction_day(day, 3) for day in p0.HISTORICAL_DAYS}
        with mock.patch.object(
            exp026, "assert_frozen_workspace"
        ), mock.patch.object(
            p0, "_is_ancestor", return_value=True
        ), mock.patch.object(
            p0, "verify_frozen_references", return_value={"verified": True}
        ), mock.patch.object(
            p0, "_verify_training_inputs", return_value=manifest()
        ), mock.patch.object(
            p0, "_load_historical_days", return_value=days
        ), mock.patch.object(
            p0, "historical_selection_core", side_effect=core_effect
        ), mock.patch.object(exp026, "_git", return_value=""):
            return p0.run_historical_selection(
                Path(directory),
                "f" * 40,
                Path(directory) / "result.json",
                argv=["--mode", "historical-selection"],
            )

    def test_existing_final_output_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            output.write_text("immutable", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                p0._fresh_output(output)

    def test_existing_part_output_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            Path(f"{output}.part").write_text("partial", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                p0._fresh_output(output)

    def test_synthetic_full_pass_run_is_json_safe(self) -> None:
        core = core_for_states((p0.ACTIVE,) * 4)
        with tempfile.TemporaryDirectory() as directory:
            result = self._run(directory, lambda _: core)
        self.assertEqual(result.payload["status"], p0.PASS_STATUS)
        self.assertEqual(len(result.output_sha256), 64)
        json.dumps(result.payload, allow_nan=False, sort_keys=True)
        self.assertTrue(
            all(type(value) is bool for value in result.payload["invariants"].values())
        )

    def test_synthetic_clean_fail_preserves_provenance_invariants(self) -> None:
        core = core_for_states(
            (p0.ACTIVE, p0.ABSTENTION, p0.ACTIVE, p0.ABSTENTION)
        )
        with tempfile.TemporaryDirectory() as directory:
            result = self._run(directory, lambda _: core)
        self.assertEqual(result.payload["status"], p0.FAIL_STATUS)
        for name in (
            "no_protocol_violation_detected",
            "preregistration_sha_verified",
            "exp026_parent_sha_status_and_commit_verified",
            "frozen_lineage_ancestry_verified",
            "historical_input_provenance_verified",
        ):
            self.assertIs(result.payload["invariants"][name], True)

    def test_one_class_readiness_failure_run_is_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self._run(
                directory,
                p0.SelectionReadinessFailure(
                    "Candidate A training labels lack both classes"
                ),
            )
        self.assertEqual(result.payload["status"], p0.FAIL_STATUS)
        self.assertIs(
            result.payload["invariants"]["no_protocol_violation_detected"], True
        )

    def test_unexpected_runtime_error_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self._run(directory, RuntimeError("unexpected numerical error"))
        self.assertEqual(result.payload["status"], p0.INVALID_STATUS)
        self.assertIs(
            result.payload["invariants"]["no_protocol_violation_detected"], False
        )


class MainCliSmokeTests(unittest.TestCase):
    ARGV = [
        "--mode",
        "historical-selection",
        "--workspace",
        "/synthetic/workspace",
        "--frozen-commit",
        "f" * 40,
        "--output",
        "/synthetic/result.json",
    ]

    def _invoke(self, status: str):
        fake = p0.RunWriteResult({"status": status}, "d" * 64)
        stream = io.StringIO()
        with mock.patch.object(
            p0, "run_historical_selection", return_value=fake
        ) as run, contextlib.redirect_stdout(stream):
            code = p0.main(self.ARGV)
        return code, json.loads(stream.getvalue()), run

    def test_main_forwards_exact_paths_commit_and_effective_argv(self) -> None:
        code, output, run = self._invoke(p0.PASS_STATUS)
        self.assertEqual(code, 0)
        run.assert_called_once_with(
            Path("/synthetic/workspace"),
            "f" * 40,
            Path("/synthetic/result.json"),
            argv=self.ARGV,
        )
        self.assertEqual(
            set(output), {"output", "output_sha256", "status"}
        )
        self.assertEqual(output["output"], "/synthetic/result.json")
        self.assertEqual(output["output_sha256"], "d" * 64)
        self.assertEqual(output["status"], p0.PASS_STATUS)

    def test_main_pass_returns_zero(self) -> None:
        code, _, _ = self._invoke(p0.PASS_STATUS)
        self.assertEqual(code, 0)

    def test_main_fail_returns_one(self) -> None:
        code, output, _ = self._invoke(p0.FAIL_STATUS)
        self.assertEqual(code, 1)
        self.assertEqual(output["status"], p0.FAIL_STATUS)

    def test_main_invalid_returns_one(self) -> None:
        code, output, _ = self._invoke(p0.INVALID_STATUS)
        self.assertEqual(code, 1)
        self.assertEqual(output["status"], p0.INVALID_STATUS)


if __name__ == "__main__":
    unittest.main()

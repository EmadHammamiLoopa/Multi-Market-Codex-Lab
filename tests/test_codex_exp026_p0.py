from __future__ import annotations

import inspect
import json
import math
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from multimarket import codex_exp026_p0 as p0
from multimarket.codex_exp004_p1 import R_FEATURE_NAMES, _r_features, _spread
from multimarket.v23_phase0dl_score import DayData


WORKSPACE = Path(__file__).resolve().parents[1]


def synthetic_direction_day(day: date = p0.HISTORICAL_DAYS[0], n: int = 12) -> p0.DirectionDay:
    decision = np.arange(n, dtype=np.int64) * p0.DECISION_STEP_US
    entry = decision + p0.ENTRY_DELAY_US
    exit_ = entry + p0.HOLDING_DURATION_US
    features = np.column_stack(
        [np.linspace(-2.0 + column, 2.0 + column, n) for column in range(7)]
    )
    long_gross = np.full(n, 30.0)
    short_gross = np.full(n, 5.0)
    return p0.DirectionDay(
        day=day,
        timestamp_us=decision,
        entry_timestamp_us=entry,
        exit_timestamp_us=exit_,
        X_direction=features,
        rv_30m_bps=features[:, 5],
        ret_10m_bps=features[:, 3],
        opportunity_label=(np.arange(n) % 2).astype(np.int8),
        long_preferred=(np.arange(n) % 2).astype(np.int8),
        long_gross_bps=long_gross,
        short_gross_bps=short_gross,
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
        **p0.profit_factor_diagnostic(net),
        "maximum_drawdown_cumulative_net_bps": p0.maximum_drawdown_bps(net),
        "exposure_fraction": float(count * p0.HOLDING_DURATION_US / p0.DAY_US),
        "stress_total_bps_at_20bp": float(np.sum(net - 6.0)),
        "nonoverlap_accounting_consistent": True,
        "no_position_overlap": True,
        "executed_trade_timing_exact": True,
    }
    entries = np.arange(count, dtype=np.int64) * 700_000_000 + p0.ENTRY_DELAY_US
    return p0.ExecutionEvaluation(metrics, net, entries, entries + p0.HOLDING_DURATION_US)


def selection_folds(values: dict[str, list[float]]) -> list[dict[str, object]]:
    return [
        {
            "candidates": {
                candidate: evaluation([values[candidate][fold]])
                for candidate in p0.CANDIDATES
            }
        }
        for fold in range(4)
    ]


def passing_invariants() -> dict[str, bool]:
    names = {
        *p0.STATIC_INVARIANT_NAMES,
        *p0.EXECUTION_INVARIANT_NAMES,
        *p0.READINESS_INVARIANT_NAMES,
        "execution_invariants_evaluated",
    }
    return {name: True for name in names}


def passing_core() -> p0.CoreSelection:
    days = {day: synthetic_direction_day(day, 3) for day in p0.HISTORICAL_DAYS}
    folds = []
    private = []
    for index, (train, validation) in enumerate(p0.FOLDS, start=1):
        candidates = {candidate: evaluation([1.0]) for candidate in p0.CANDIDATES}
        private.append({"candidates": candidates})
        folds.append(
            {
                "fold": index,
                "train_dates": [day.isoformat() for day in train],
                "validation_date": validation.isoformat(),
                "trigger_threshold": 0.75,
                "trigger_quantile": 0.90,
                "trigger_quantile_method": "higher",
                "trigger_source": "training_probabilities_only",
                "validation_probabilities_used_for_trigger": False,
                "training_probability_count": 10,
                "validation_common_support_count": 3,
                "candidates": {
                    candidate: candidates[candidate].metrics for candidate in p0.CANDIDATES
                },
            }
        )
    return p0.CoreSelection(
        days=days,
        folds=folds,
        private_folds=private,
        selected_candidate="B",
        candidate_selection={"selected_candidate": "B"},
        final_models={"selected_direction_candidate": "B"},
    )


def synthetic_manifest() -> list[dict[str, object]]:
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


class FrozenIdentityTests(unittest.TestCase):
    def test_exact_status_vocabulary(self) -> None:
        self.assertEqual(
            p0.PASS_STATUS,
            "DIRECTION_EXECUTION_PIPELINE_READY_FOR_FRESH_PROSPECTIVE_VALIDATION",
        )
        self.assertEqual(p0.FAIL_STATUS, "FAIL_DIRECTION_EXECUTION_PIPELINE_NOT_READY")
        self.assertEqual(p0.INVALID_STATUS, "INVALID")

    def test_preregistration_and_parent_hash_status(self) -> None:
        result = p0.verify_frozen_references(WORKSPACE)
        self.assertEqual(result["preregistration"]["sha256"], p0.PREREGISTRATION_SHA256)
        self.assertEqual(result["parent_result"]["sha256"], p0.PARENT_RESULT_SHA256)
        self.assertEqual(result["parent_result"]["status"], p0.PARENT_STATUS)

    def test_exact_historical_calendar_folds_and_paths(self) -> None:
        self.assertEqual(
            p0.HISTORICAL_DAY_STRINGS,
            tuple(f"2026-{month:02d}-01" for month in range(1, 8)),
        )
        self.assertEqual(len(p0.FOLDS), 4)
        for index, (train, validation) in enumerate(p0.FOLDS):
            self.assertEqual(train, p0.HISTORICAL_DAYS[: index + 3])
            self.assertEqual(validation, p0.HISTORICAL_DAYS[index + 3])
        self.assertEqual(
            p0.authorized_feature_path(date(2026, 1, 1)),
            p0.AUTHORIZED_FEATURE_ROOT / "BTCUSDT" / "2026-01-01_FEATURES250.csv",
        )

    def test_aug30_and_sep_future_rejected_before_open(self) -> None:
        with mock.patch.object(Path, "open") as opened:
            for forbidden in (date(2026, 8, 30), date(2026, 9, 1), date(2030, 1, 1)):
                with self.assertRaises(p0.ProtocolViolation):
                    p0.authorized_feature_path(forbidden)
            opened.assert_not_called()

    def test_ancestor_return_code_zero_accepted_one_rejected(self) -> None:
        with mock.patch.object(
            p0.subprocess, "run", return_value=SimpleNamespace(returncode=0, stderr="")
        ):
            self.assertTrue(p0._is_ancestor(Path("/synthetic"), "a", "b"))
        with mock.patch.object(
            p0.subprocess, "run", return_value=SimpleNamespace(returncode=1, stderr="")
        ):
            self.assertFalse(p0._is_ancestor(Path("/synthetic"), "a", "b"))
        with mock.patch.object(
            p0.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=128, stderr="bad revision"),
        ):
            with self.assertRaises(p0.ProtocolViolation):
                p0._is_ancestor(Path("/synthetic"), "a", "b")

    def test_cli_has_only_restricted_arguments(self) -> None:
        destinations = {action.dest for action in p0.build_parser()._actions}
        self.assertEqual(
            destinations, {"help", "mode", "workspace", "frozen_commit", "output"}
        )
        parsed = p0.build_parser().parse_args(
            [
                "--mode", "historical-selection", "--workspace", "/tmp/w",
                "--frozen-commit", "a" * 40, "--output", "/tmp/o.json",
            ]
        )
        self.assertEqual(parsed.mode, "historical-selection")

    def test_no_network_or_acquisition_interface(self) -> None:
        source = inspect.getsource(p0)
        for forbidden in ("requests", "websocket", "urllib", "--date", "--feature-root", "glob("):
            self.assertNotIn(forbidden, source)
        self.assertFalse(p0.NETWORK_ACCESSED)
        self.assertFalse(p0.AUG30_ANALYTICALLY_OPENED)
        self.assertFalse(p0.SEP01_OR_LATER_OPENED)


class FrozenScientificSemanticsTests(unittest.TestCase):
    def test_configuration_and_model_parameters_exact(self) -> None:
        config = p0.scientific_configuration()
        self.assertEqual(config["symbol"], "BTCUSDT")
        self.assertEqual(config["opportunity_feature"], "rv_30m_bps")
        self.assertEqual(config["candidates"], ["A", "B", "C"])
        self.assertEqual(
            config["model"],
            {
                "scaler": "StandardScaler", "estimator": "LogisticRegression",
                "C": 1.0, "penalty": "l2", "solver": "lbfgs",
                "class_weight": None, "max_iter": 1000, "random_state": 20260825,
            },
        )
        self.assertEqual(p0.SCIENTIFIC_CONFIGURATION_SHA256, p0.canonical_sha256(config))

    def test_direction_feature_list_and_candidates_exact(self) -> None:
        self.assertEqual(
            p0.DIRECTION_FEATURE_NAMES,
            (
                "ret_1m_bps", "ret_3m_bps", "ret_5m_bps", "ret_10m_bps",
                "ret_30m_bps", "rv_30m_bps", "spread_bps",
            ),
        )
        self.assertEqual(
            tuple(R_FEATURE_NAMES[index] for index in p0.DIRECTION_INDICES),
            p0.DIRECTION_FEATURE_NAMES,
        )

    def test_candidate_b_c_rules_and_direction_label_tie(self) -> None:
        returns = np.asarray([-1.0, 0.0, 1.0])
        np.testing.assert_array_equal(p0.candidate_b_direction(returns), [False, True, True])
        np.testing.assert_array_equal(p0.candidate_c_direction(returns), [True, False, False])
        np.testing.assert_array_equal(
            p0.direction_label(np.asarray([2.0, 1.0]), np.asarray([1.0, 1.0])),
            [1, 0],
        )

    def test_timing_is_derived_from_frozen_constants(self) -> None:
        self.assertEqual(p0.DECISION_STEP_ROWS * p0.GRID_US, 60_000_000)
        self.assertEqual(p0.ENTRY_STEPS * p0.GRID_US, 250_000)
        self.assertEqual(p0.HORIZON_S * 1_000_000 // p0.GRID_US, 2400)
        timing = p0.frozen_timing_invariants()
        self.assertTrue(all(timing.values()))
        self.assertTrue(all(type(value) is bool for value in timing.values()))

    def test_frozen_r_features_do_not_use_future_mutation(self) -> None:
        n = 7202
        mid = np.exp(np.linspace(0.0, 0.01, n)) * 100.0
        day = DayData(
            p0.HISTORICAL_DAYS[0], np.arange(n) * p0.GRID_US,
            mid - 0.01, mid + 0.01, mid.copy(), np.ones(n, bool), {}, {},
        )
        current = 7200
        before = _r_features(day, current, _spread(day))
        day.mid[current + 1] *= 100.0
        day.bid[current + 1] *= 100.0
        day.ask[current + 1] *= 100.0
        after = _r_features(day, current, _spread(day))
        np.testing.assert_array_equal(before, after)

    def test_quantile_uses_method_higher(self) -> None:
        values = np.asarray([0.1, 0.2, 0.8])
        with mock.patch.object(p0.np, "quantile", wraps=np.quantile) as quantile:
            result = p0.training_probability_trigger(values)
        self.assertEqual(result, 0.8)
        self.assertEqual(quantile.call_args.kwargs["method"], "higher")
        self.assertEqual(quantile.call_args.args[1], 0.90)

    def test_fold_trigger_receives_training_probabilities_not_validation(self) -> None:
        class FakeModel:
            def fit(self, X, y):
                return self

            def predict_proba(self, X):
                return np.linspace(0.1, 0.9, len(X))

        train = [synthetic_direction_day(p0.HISTORICAL_DAYS[0], 4)]
        validation = synthetic_direction_day(p0.HISTORICAL_DAYS[3], 3)
        seen: list[int] = []

        def trigger(values):
            seen.append(len(values))
            return 0.5

        with mock.patch.object(p0, "FixedLogistic", FakeModel), mock.patch.object(
            p0, "training_probability_trigger", side_effect=trigger
        ):
            fold = p0._fit_fold(train, validation)
        self.assertEqual(seen, [4])
        self.assertEqual(fold["trigger_source"], "training_probabilities_only")
        self.assertIs(fold["validation_probabilities_used_for_trigger"], False)

    def test_binary_labels_are_validated_before_int8_coercion(self) -> None:
        X3 = np.arange(3, dtype=float).reshape(-1, 1)
        for labels in ([0, 0, 0], [1, 1, 1]):
            with self.subTest(labels=labels), self.assertRaises(p0.SelectionReadinessFailure):
                p0._fit_readiness_logistic(X3, np.asarray(labels), context="test")
        accepted = p0._fit_readiness_logistic(
            np.arange(4, dtype=float).reshape(-1, 1),
            np.asarray([0, 1, 0, 1]),
            context="test",
        )
        self.assertIsInstance(accepted, p0.FixedLogistic)
        invalid = (
            np.asarray([0, 2]),
            np.asarray([-1, 1]),
            np.asarray([0.0, 0.5, 1.0]),
            np.asarray([0.0, math.nan, 1.0]),
        )
        for labels in invalid:
            with self.subTest(labels=labels), self.assertRaises(p0.ProtocolViolation):
                p0._fit_readiness_logistic(
                    np.arange(len(labels), dtype=float).reshape(-1, 1),
                    labels,
                    context="test",
                )

    def test_one_class_fold_opportunity_labels_are_clean_readiness_failure(self) -> None:
        train = synthetic_direction_day(n=4)
        train.opportunity_label[:] = 0
        with self.assertRaisesRegex(
            p0.SelectionReadinessFailure, "fold opportunity model.*lack both classes"
        ):
            p0._fit_fold([train], synthetic_direction_day(p0.HISTORICAL_DAYS[3], 3))

    def test_one_class_candidate_a_labels_are_clean_readiness_failure(self) -> None:
        train = synthetic_direction_day(n=4)
        train.opportunity_label[:] = [0, 1, 0, 1]
        train.long_preferred[:] = 0
        with self.assertRaisesRegex(
            p0.SelectionReadinessFailure, "Candidate A.*lack both classes"
        ):
            p0._fit_fold([train], synthetic_direction_day(p0.HISTORICAL_DAYS[3], 3))

    def test_malformed_or_nonfinite_training_inputs_are_protocol_violations(self) -> None:
        with self.assertRaises(p0.ProtocolViolation):
            p0._fit_readiness_logistic(np.ones(3), np.asarray([0, 1, 0]), context="x")
        with self.assertRaises(p0.ProtocolViolation):
            p0._fit_readiness_logistic(
                np.asarray([[1.0], [math.nan]]), np.asarray([0, 1]), context="x"
            )
        with self.assertRaises(p0.ProtocolViolation):
            p0._fit_readiness_logistic(np.ones((2, 1)), np.asarray([[0], [1]]), context="x")

    def test_all_exp026_model_fits_use_readiness_guard(self) -> None:
        source = inspect.getsource(p0)
        self.assertEqual(source.count("FixedLogistic().fit("), 1)
        self.assertGreaterEqual(source.count("_fit_readiness_logistic("), 5)

    def test_t_plus_600_signal_remains_blocked_until_t_plus_600_25(self) -> None:
        day = synthetic_direction_day(n=12)
        result = p0.execute_nonoverlapping(day, np.ones(12), 0.5, np.ones(12, bool))
        self.assertEqual(result.metrics["eligible_signal_count"], 12)
        self.assertEqual(result.metrics["executed_nonoverlapping_trade_count"], 2)
        self.assertEqual(result.metrics["ignored_eligible_signals_while_open"], 10)
        self.assertEqual(result.entry_timestamp_us[1], 660_250_000)
        np.testing.assert_array_equal(
            result.exit_timestamp_us - result.entry_timestamp_us,
            np.full(2, 600_000_000),
        )

    def test_primary_and_stress_costs_exact(self) -> None:
        result = p0.execute_nonoverlapping(
            synthetic_direction_day(n=1), np.ones(1), 0.5, np.ones(1, bool)
        )
        self.assertEqual(result.metrics["gross_total_bps"], 30.0)
        self.assertEqual(result.metrics["net_total_bps_at_14bp"], 16.0)
        self.assertEqual(result.metrics["stress_total_bps_at_20bp"], 10.0)

    def test_no_leverage_sl_tp_or_sizing_controls(self) -> None:
        execution = p0.scientific_configuration()["execution"]
        for key in (
            "leverage", "stop_loss", "take_profit", "position_sizing_optimization",
            "post_hoc_filtering", "pyramiding",
        ):
            self.assertIs(execution[key], False)


class SupportEquivalenceTests(unittest.TestCase):
    @staticmethod
    def fixture(parent_support: np.ndarray) -> tuple[DayData, SimpleNamespace, dict[str, np.ndarray]]:
        n = 2642
        ts = np.arange(n, dtype=np.int64) * p0.GRID_US
        day = DayData(
            p0.HISTORICAL_DAYS[0], ts, np.ones(n), np.ones(n) * 1.01,
            np.ones(n) * 1.005, np.ones(n, bool), {}, {},
        )
        decisions = np.arange(0, n, p0.DECISION_STEP_ROWS, dtype=np.int64)
        rows = len(decisions)
        X = np.full((rows, len(R_FEATURE_NAMES)), np.nan)
        X[parent_support] = 1.0
        frozen = SimpleNamespace(
            timestamp_us=ts[decisions], X_R=X, valid_R=parent_support,
            y=np.zeros(rows, dtype=np.int8),
        )
        valid = parent_support.copy()
        long = np.full(rows, np.nan)
        short = np.full(rows, np.nan)
        oracle = np.full(rows, np.nan)
        long[valid], short[valid], oracle[valid] = 2.0, 1.0, 2.0
        outcomes = {
            "valid": valid,
            "long_gross_bps": long,
            "short_gross_bps": short,
            "oracle_gross_bps": oracle,
            "entry_index": decisions + p0.ENTRY_STEPS,
            "exit_index": decisions + p0.ENTRY_STEPS + p0.HORIZON_STEPS,
        }
        return day, frozen, outcomes

    def test_reconstructed_support_exactly_equals_parent_valid_r(self) -> None:
        support = np.zeros(12, dtype=bool)
        support[0] = True
        day, frozen, outcomes = self.fixture(support)
        with mock.patch.object(p0, "build_day_dataset", return_value=frozen), mock.patch.object(
            p0, "executable_fixed_horizon", return_value=outcomes
        ):
            adapted = p0.build_direction_day(day)
        np.testing.assert_array_equal(adapted.common_support, support)
        self.assertIs(adapted.parent_support_exact, True)

    def test_support_narrowing_or_widening_is_protocol_violation(self) -> None:
        support = np.zeros(12, dtype=bool)
        support[0] = True
        day, frozen, outcomes = self.fixture(support)
        outcomes["valid"] = np.zeros(12, dtype=bool)
        with mock.patch.object(p0, "build_day_dataset", return_value=frozen), mock.patch.object(
            p0, "executable_fixed_horizon", return_value=outcomes
        ):
            with self.assertRaises(p0.ProtocolViolation):
                p0.build_direction_day(day)


class CandidateSelectionAndJsonTests(unittest.TestCase):
    def test_candidate_selection_simplicity_tie_break(self) -> None:
        values = {candidate: [1.0, 1.0, 1.0, 1.0] for candidate in p0.CANDIDATES}
        selected, diagnostic = p0.select_candidate(selection_folds(values))
        self.assertEqual(selected, "B")
        self.assertEqual(diagnostic["tie_break_order"][-1], "simpler candidate B then C then A")

    def test_positive_fold_tie_break_precedes_profit_factor(self) -> None:
        selected, _ = p0.select_candidate(
            selection_folds(
                {
                    "A": [-1.0, 0.0, 0.0, 1.0],
                    "B": [0.0, 0.0, 0.0, 0.0],
                    "C": [-1.0, -1.0, -1.0, -1.0],
                }
            )
        )
        self.assertEqual(selected, "A")

    def test_profit_factor_and_drawdown_tie_breaks_are_applied(self) -> None:
        selected, _ = p0.select_candidate(
            selection_folds(
                {
                    "A": [-1.0, -1.0, 2.0, 2.0],
                    "B": [-3.0, -1.0, 2.0, 10.0],
                    "C": [-2.0, -2.0, 1.0, 1.0],
                }
            )
        )
        self.assertEqual(selected, "B")
        selected, _ = p0.select_candidate(
            selection_folds(
                {
                    "A": [-1.0, -1.0, 2.0, 2.0],
                    "B": [-1.0, 2.0, -1.0, 2.0],
                    "C": [-2.0, -2.0, 1.0, 1.0],
                }
            )
        )
        self.assertEqual(selected, "B")

    def test_profit_factor_finite_infinite_and_undefined_are_json_safe(self) -> None:
        finite = p0.profit_factor_diagnostic(np.asarray([2.0, -1.0]))
        self.assertEqual(finite["profit_factor"], 2.0)
        self.assertIs(finite["profit_factor_infinite"], False)
        infinite = p0.profit_factor_diagnostic(np.asarray([2.0, 1.0]))
        self.assertIsNone(infinite["profit_factor"])
        self.assertIs(infinite["profit_factor_infinite"], True)
        self.assertIs(infinite["profit_factor_undefined"], False)
        undefined = p0.profit_factor_diagnostic(np.asarray([0.0, 0.0]))
        self.assertIsNone(undefined["profit_factor"])
        self.assertIs(undefined["profit_factor_infinite"], False)
        self.assertIs(undefined["profit_factor_undefined"], True)
        json.dumps({"finite": finite, "infinite": infinite, "undefined": undefined}, allow_nan=False)

    def test_json_normalizes_numpy_scalars_and_rejects_nonfinite(self) -> None:
        safe = p0.normalize_json_safe(
            {"b": np.bool_(True), "i": np.int64(2), "f": np.float64(1.5)}
        )
        self.assertEqual(safe, {"b": True, "i": 2, "f": 1.5})
        json.dumps(safe, allow_nan=False)
        for value in (math.nan, math.inf, np.float64(-math.inf)):
            with self.assertRaises(Exception):
                p0.normalize_json_safe({"bad": value})


class InvariantAdjudicationTests(unittest.TestCase):
    def test_all_protocol_execution_and_readiness_true_is_pass(self) -> None:
        self.assertEqual(p0.adjudicate_readiness(passing_invariants()), p0.PASS_STATUS)

    def test_clean_selection_failure_with_provenance_intact_is_fail(self) -> None:
        invariants = passing_invariants()
        invariants["historical_selection_pipeline_completed"] = False
        invariants["exactly_one_candidate_selected"] = False
        invariants["all_four_folds_scored_for_each_candidate"] = False
        invariants["execution_invariants_evaluated"] = False
        for name in p0.EXECUTION_INVARIANT_NAMES:
            invariants[name] = False
        self.assertEqual(p0.adjudicate_readiness(invariants), p0.FAIL_STATUS)

    def test_provenance_causality_or_future_violation_is_invalid(self) -> None:
        for name in (
            "preregistration_sha_verified", "historical_input_provenance_verified",
            "no_protocol_violation_detected", "aug30_analytically_opened_false",
        ):
            invariants = passing_invariants()
            invariants[name] = False
            self.assertEqual(p0.adjudicate_readiness(invariants), p0.INVALID_STATUS)
        invariants = passing_invariants()
        invariants["no_position_overlap"] = False
        self.assertEqual(p0.adjudicate_readiness(invariants), p0.INVALID_STATUS)

    def test_missing_or_numpy_bool_invariant_never_passes(self) -> None:
        missing = passing_invariants()
        missing.pop("network_accessed_false")
        with self.assertRaises(p0.ProtocolViolation):
            p0.adjudicate_readiness(missing)
        wrong = passing_invariants()
        wrong["network_accessed_false"] = np.bool_(True)
        with self.assertRaises(p0.ProtocolViolation):
            p0.adjudicate_readiness(wrong)

    def test_built_readiness_invariants_are_exact_builtin_bool(self) -> None:
        invariants = p0.build_readiness_invariants(
            passing_core(), references_verified=True, provenance_verified=True,
            protocol_clean=True, pipeline_completed=True,
        )
        self.assertTrue(all(type(value) is bool for value in invariants.values()))
        self.assertEqual(p0.adjudicate_readiness(invariants), p0.PASS_STATUS)


class OutputAndRunRecordTests(unittest.TestCase):
    def _run_with_core_effect(self, directory: str, effect) -> p0.RunWriteResult:
        core = passing_core()
        with mock.patch.object(p0, "assert_frozen_workspace"), mock.patch.object(
            p0, "_is_ancestor", return_value=True
        ), mock.patch.object(
            p0, "verify_frozen_references", return_value={"verified": True}
        ), mock.patch.object(
            p0, "_verify_training_inputs", return_value=synthetic_manifest()
        ), mock.patch.object(
            p0, "_load_historical_days", return_value=core.days
        ), mock.patch.object(
            p0, "historical_selection_core", side_effect=effect
        ), mock.patch.object(p0, "_git", return_value=""):
            return p0.run_historical_selection(
                Path(directory), "f" * 40, Path(directory) / "result.json",
                argv=["--mode", "historical-selection"],
            )

    def test_one_shot_output_refuses_existing_final_and_part(self) -> None:
        payload = {"invariants": passing_invariants(), "value": np.int64(1)}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            digest = p0._write_once(output, payload)
            self.assertEqual(len(digest), 64)
            with self.assertRaises(FileExistsError):
                p0._write_once(output, payload)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            Path(f"{output}.part").write_text("occupied", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                p0._write_once(output, payload)

    def test_synthetic_full_run_record_has_provenance_and_json_safe_pass(self) -> None:
        core = passing_core()
        with tempfile.TemporaryDirectory() as directory:
            result = self._run_with_core_effect(directory, lambda _: core)
        payload = result.payload
        self.assertEqual(payload["status"], p0.PASS_STATUS)
        for key in (
            "run_id", "started_at_utc", "finished_at_utc", "frozen_git_commit",
            "tracked_tree_dirty", "command_argv", "environment",
            "scientific_configuration", "scientific_configuration_sha256",
            "historical_input_manifest", "model_hyperparameters_and_seed",
            "execution_semantics", "historical_selection", "invariants",
            "sealed_future_data_assertions",
        ):
            self.assertIn(key, payload)
        self.assertEqual(len(payload["historical_input_manifest"]), 7)
        self.assertIsNone(payload["output_sha256"])
        self.assertEqual(len(result.output_sha256), 64)
        self.assertTrue(all(type(value) is bool for value in payload["invariants"].values()))
        json.dumps(payload, sort_keys=True, allow_nan=False)

    def test_clean_core_selection_failure_produces_fail_with_provenance_true(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = self._run_with_core_effect(
                directory, p0.SelectionReadinessFailure("one-class historical support")
            )
        self.assertEqual(result.payload["status"], p0.FAIL_STATUS)
        invariants = result.payload["invariants"]
        for name in (
            "no_protocol_violation_detected", "preregistration_sha_verified",
            "parent_result_sha_and_status_verified", "historical_input_provenance_verified",
        ):
            self.assertIs(invariants[name], True)
        self.assertIs(invariants["historical_selection_pipeline_completed"], False)

    def test_unexpected_runtime_and_protocol_errors_produce_invalid(self) -> None:
        for error in (
            RuntimeError("unexpected numerical error"), p0.ProtocolViolation("causality")
        ):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                result = self._run_with_core_effect(directory, error)
                self.assertEqual(result.payload["status"], p0.INVALID_STATUS)
                self.assertIs(
                    result.payload["invariants"]["no_protocol_violation_detected"], False
                )


if __name__ == "__main__":
    unittest.main()

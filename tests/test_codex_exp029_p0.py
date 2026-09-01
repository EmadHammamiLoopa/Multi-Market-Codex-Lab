from __future__ import annotations

import ast
import hashlib
import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from multimarket import codex_exp029_p0 as p0


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE = WORKSPACE / "src/multimarket/codex_exp029_p0.py"
PREREG = WORKSPACE / p0.PREREG_REL


def make_day(day: date, *, n: int = 8, start_us: int = 0) -> p0.OpportunityDay:
    timestamp = start_us + np.arange(n, dtype=np.int64) * p0.DECISION_STEP_US
    return p0.OpportunityDay(
        day=day,
        timestamp_us=timestamp,
        rv_30m_bps=np.linspace(1.0, 2.0, n),
        opportunity_label=(np.arange(n) % 2).astype(np.int8),
        common_support=np.ones(n, dtype=bool),
        parent_support_exact=True,
    )


def good_rank_metrics() -> dict[str, object]:
    return {
        "n": 1200,
        "positives": 120,
        "negatives": 1080,
        "prevalence": 0.1,
        "roc_auc": 0.8,
        "average_precision": 0.3,
        "average_precision_over_prevalence": 3.0,
    }


def make_fold(
    number: int,
    *,
    lift: float | None = 2.0,
    active: bool = True,
    support: bool = True,
) -> p0.FoldEvaluation:
    train, validation = p0.FOLDS[number - 1]
    timestamp = np.asarray([number * 1_000_000, number * 1_000_000 + 60_000_000])
    eligible = np.asarray([True, False]) if active else np.asarray([False, False])
    occupancy = p0.occupancy_support(timestamp, eligible)
    causal_checks = {
        "initial_reference_is_last_1399_training_scores": True,
        "reference_length_always_1399": True,
        "current_score_excluded_before_decision": True,
        "future_scores_never_enter_past_references": True,
        "eligibility_uses_probability_vs_causal_threshold": True,
    }
    p0.validate_builtin_bool_invariants(causal_checks)
    return p0.FoldEvaluation(
        fold=number,
        train_dates=tuple(day.isoformat() for day in train),
        validation_date=validation.isoformat(),
        training_probability_count=4197,
        validation_common_support_count=1200,
        timestamp_us=timestamp,
        label=np.asarray([1, 0], dtype=np.int8),
        raw_probability=np.asarray([0.9, 0.1]),
        causal_rank=np.asarray([0.95, 0.05]),
        threshold=np.asarray([0.8, 0.8]),
        eligible=eligible,
        causal_rank_metrics=good_rank_metrics(),
        raw_probability_metrics=good_rank_metrics(),
        causal_gate_metrics={
            "eligible_signal_count": int(np.sum(eligible)),
            "eligible_fraction": float(np.mean(eligible)),
            "eligible_positive_count": int(active),
            "eligible_precision": 1.0 if active else None,
            "eligible_lift": lift,
        },
        occupancy=occupancy,
        support_sufficient=support,
        threshold_summary={
            "first": 0.8,
            "median": 0.8,
            "minimum": 0.8,
            "maximum": 0.8,
            "last": 0.8,
        },
        model_record={"hyperparameters": p0.model_configuration()},
        causal_invariants=causal_checks,
    )


def make_core(
    *,
    lifts: tuple[float | None, ...] = (2.0, 2.0, 2.0, 2.0),
    active: tuple[bool, ...] = (True, True, True, True),
    support: tuple[bool, ...] = (True, True, True, True),
) -> p0.DevelopmentCore:
    folds = tuple(
        make_fold(i + 1, lift=lifts[i], active=active[i], support=support[i])
        for i in range(4)
    )
    days = {day: make_day(day, start_us=index * p0.DAY_US) for index, day in enumerate(p0.HISTORICAL_DAYS)}
    return p0.DevelopmentCore(
        days=days,
        folds=folds,
        pooled_causal_rank_metrics=good_rank_metrics(),
        pooled_raw_probability_metrics={**good_rank_metrics(), "roc_auc": 0.75, "average_precision": 0.25},
        pooled_causal_gate_metrics={
            "eligible_signal_count": 100,
            "eligible_fraction": 0.08333333333333333,
            "eligible_positive_count": 20,
            "eligible_precision": 0.2,
            "eligible_lift": 2.0,
        },
        raw_score_continuity={
            "causal_rank_auc_minus_raw_probability_auc": 0.05,
            "causal_rank_ap_minus_raw_probability_ap": 0.05,
        },
        temporal_null={
            "number_of_shifts": 39,
            "eligible_shifts": list(range(30, 1200, 30)),
            "shift_step_rows": 30,
            "same_shift_within_every_fold": True,
            "fold_preserving": True,
            "auc_null_q95": 0.7,
            "ap_null_q95": 0.2,
            "auc_empirical_one_sided_p": 0.025,
            "ap_empirical_one_sided_p": 0.025,
        },
        active_fold_count=int(sum(active)),
        total_eligible_signals=int(sum(f.occupancy.eligible_signal_count for f in folds)),
        total_executed_nonoverlapping_opportunities=int(
            sum(f.occupancy.executed_nonoverlapping_opportunity_count for f in folds)
        ),
        oof_records=[],
    )


def all_true_invariants() -> dict[str, bool]:
    return {
        name: True
        for name in (*p0.STATIC_INVARIANT_NAMES, *p0.EVALUATED_INVARIANT_NAMES)
    }


def minimal_payload() -> dict[str, object]:
    return {
        "experiment_id": p0.EXPERIMENT_ID,
        "status": p0.PASS_STATUS,
        "invariants": {"synthetic": True},
        "primary_gates": {"synthetic": True},
        "runtime_guards": p0.runtime_guards(),
    }


class FrozenIdentityTests(unittest.TestCase):
    def test_01_frozen_constants_exact(self) -> None:
        self.assertEqual(p0.EXPERIMENT_ID, "CODEX-EXP-029-P0")
        self.assertEqual(p0.REFERENCE_WINDOW_SIZE, 1399)
        self.assertEqual(p0.GATE_QUANTILE, 0.90)
        self.assertEqual(p0.QUANTILE_METHOD, "higher")
        self.assertEqual(p0.DECISION_STEP_S, 60)
        self.assertEqual(p0.ENTRY_DELAY_MS, 250)
        self.assertEqual(p0.HORIZON_S, 600)
        self.assertEqual(p0.LABEL_THRESHOLD_BPS, 24.0)
        self.assertEqual((p0.MIN_SUPPORT_N, p0.MIN_POSITIVES, p0.MIN_NEGATIVES), (1200, 10, 100))
        self.assertEqual((p0.NULL_QUANTILE, p0.NULL_SHIFT_STEP_ROWS), (0.95, 30))

    def test_02_preregistration_path_hash_and_commit_exact(self) -> None:
        self.assertEqual(
            p0.PREREG_COMMIT, "04cdbc643a5207ec9105ae82ab5658bb16b0169d"
        )
        self.assertEqual(
            hashlib.sha256(PREREG.read_bytes()).hexdigest(), p0.PREREG_SHA256
        )

    def test_03_parent_lineage_constants_exact(self) -> None:
        self.assertEqual(p0.EXP024_IMPLEMENTATION_COMMIT, "cdffc6d7556a2258e59f3a63e0e11419b47e5e5c")
        self.assertEqual(p0.EXP024_RESULT_COMMIT, "4669be4234b808286108c288f7a6eb7b3742f268")
        self.assertEqual(p0.EXP024_RESULT_SHA256, "0fda20d127e51e8ad792c6b949889f88b59e75ab98b437fd04ead285970e5c10")
        self.assertEqual(p0.EXP028_RESULT_COMMIT, "09e04a5cd6203110bdfb0e774b09e79242e542db")
        self.assertEqual(p0.EXP028_RESULT_SHA256, "32053a61b7a7e181857d9838d902551b4249f12e96fa1af4967cd18aa28385e1")

    def test_04_status_vocabulary_exact(self) -> None:
        self.assertEqual(p0.PASS_STATUS, "CAUSAL_RANK_OPPORTUNITY_POLICY_READY_FOR_DIRECTION_DEVELOPMENT")
        self.assertEqual(p0.FAIL_STATUS, "FAIL_CAUSAL_RANK_OPPORTUNITY_POLICY_NOT_READY")
        self.assertEqual(p0.INVALID_STATUS, "INVALID")

    def test_05_model_hyperparameters_exact(self) -> None:
        self.assertEqual(
            p0.model_configuration(),
            {
                "preprocessing": "StandardScaler",
                "estimator": "LogisticRegression",
                "C": 1.0,
                "penalty": "l2",
                "solver": "lbfgs",
                "class_weight": None,
                "max_iter": 1000,
                "random_state": 20260825,
            },
        )
        self.assertEqual(p0.OPPORTUNITY_FEATURE, "rv_30m_bps")

    def test_06_four_expanding_folds_exact(self) -> None:
        self.assertEqual(len(p0.FOLDS), 4)
        for i, (train, validation) in enumerate(p0.FOLDS):
            self.assertEqual(train, p0.HISTORICAL_DAYS[: i + 3])
            self.assertEqual(validation, p0.HISTORICAL_DAYS[i + 3])

    def test_07_authorized_calendar_exact(self) -> None:
        self.assertEqual(
            p0.HISTORICAL_DAY_STRINGS,
            tuple(f"2026-{month:02d}-01" for month in range(1, 8)),
        )
        for day in p0.HISTORICAL_DAYS:
            self.assertEqual(
                p0.authorized_feature_path(day),
                p0.AUTHORIZED_FEATURE_ROOT / "BTCUSDT" / f"{day}_FEATURES250.csv",
            )

    def test_08_timing_derives_from_frozen_helpers(self) -> None:
        self.assertEqual(p0.DECISION_STEP_ROWS * p0.GRID_US, 60_000_000)
        self.assertEqual(p0.ENTRY_STEPS * p0.GRID_US, 250_000)
        self.assertEqual(p0.HORIZON_STEPS, 2400)
        self.assertTrue(all(p0.frozen_timing_invariants().values()))

    def test_09_runtime_guards_exact_builtin_false(self) -> None:
        guards = p0.runtime_guards()
        self.assertEqual(
            tuple(guards),
            (
                "AUG30_ANALYTICALLY_OPENED",
                "SEP01_OR_LATER_OPENED",
                "NETWORK_ACCESSED",
                "DIRECTION_SCORED",
                "PNL_SCORED",
                "LEVERAGE_SCORED",
            ),
        )
        self.assertTrue(all(type(value) is bool and value is False for value in guards.values()))


class AccessAndStaticSafetyTests(unittest.TestCase):
    def test_10_aug30_rejected_before_open(self) -> None:
        with patch.object(Path, "open") as opened:
            with self.assertRaises(p0.ProtocolViolation):
                p0.authorized_feature_path(date(2026, 8, 30))
            opened.assert_not_called()

    def test_11_sep01_and_later_rejected_before_open(self) -> None:
        with patch.object(Path, "open") as opened:
            for day in (date(2026, 9, 1), date(2027, 1, 1)):
                with self.assertRaises(p0.ProtocolViolation):
                    p0.authorized_feature_path(day)
            opened.assert_not_called()

    def test_12_cli_has_no_arbitrary_data_interface(self) -> None:
        actions = tuple(action.dest for action in p0.build_parser()._actions)
        self.assertEqual(actions, ("help", "mode", "workspace", "frozen_commit", "output"))
        self.assertNotIn("date", actions)
        self.assertNotIn("feature_root", actions)
        self.assertNotIn("raw", actions)

    def test_13_cli_rejects_unsupported_mode(self) -> None:
        with self.assertRaises(SystemExit):
            p0.build_parser().parse_args(
                ["--mode", "execute", "--workspace", ".", "--frozen-commit", "a" * 40, "--output", "x"]
            )

    def test_14_no_network_or_acquisition_import(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertTrue({"socket", "requests", "urllib", "websockets", "aiohttp"}.isdisjoint(imported))

    def test_15_no_direction_or_economic_machinery(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        function_names = {
            node.name.lower()
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        forbidden_fragments = (
            "candidate_a",
            "candidate_b",
            "candidate_c",
            "profit_factor",
            "drawdown",
            "position_size",
            "stop_loss",
            "take_profit",
        )
        self.assertFalse(any(fragment in name for name in function_names for fragment in forbidden_fragments))
        self.assertNotIn("codex_exp026_p0", SOURCE.read_text(encoding="utf-8"))
        self.assertNotIn("codex_exp028_p0", SOURCE.read_text(encoding="utf-8"))


class CausalRankTests(unittest.TestCase):
    def setUp(self) -> None:
        self.training = np.linspace(0.0, 1.0, 1500)

    def test_16_reference_initial_size_exactly_1399(self) -> None:
        result = p0.causal_rolling_rank(self.training, [0.5, 0.6])
        self.assertEqual(len(result.initial_reference), 1399)
        np.testing.assert_array_equal(result.reference_lengths, [1399, 1399])

    def test_17_initialization_uses_last_1399_training_scores(self) -> None:
        result = p0.causal_rolling_rank(self.training, [0.5])
        np.testing.assert_array_equal(result.initial_reference, self.training[-1399:])
        self.assertNotEqual(result.initial_reference[0], self.training[0])

    def test_18_current_score_cannot_affect_own_threshold(self) -> None:
        low = p0.causal_rolling_rank(self.training, [0.0])
        high = p0.causal_rolling_rank(self.training, [1.0])
        self.assertEqual(low.threshold[0], high.threshold[0])

    def test_19_current_score_excluded_from_own_rank_reference(self) -> None:
        value = 0.5
        result = p0.causal_rolling_rank(self.training, [value])
        prior = np.sort(self.training[-1399:])
        expected = np.searchsorted(prior, value, side="right") / 1399.0
        self.assertEqual(result.rank[0], expected)

    def test_20_score_enters_reference_only_after_decision(self) -> None:
        value = 0.123456
        result = p0.causal_rolling_rank(self.training, [value])
        np.testing.assert_array_equal(
            result.final_reference,
            np.concatenate((self.training[-1398:], [value])),
        )

    def test_21_reference_remains_exact_length(self) -> None:
        result = p0.causal_rolling_rank(self.training, np.linspace(0.1, 0.9, 100))
        self.assertEqual(len(result.final_reference), 1399)
        self.assertTrue(np.all(result.reference_lengths == 1399))

    def test_22_threshold_matches_higher_quantile(self) -> None:
        result = p0.causal_rolling_rank(self.training, [0.5])
        expected = np.quantile(self.training[-1399:], 0.90, method="higher")
        self.assertEqual(result.threshold[0], expected)

    def test_23_rank_matches_searchsorted_right(self) -> None:
        result = p0.causal_rolling_rank(self.training, [0.75])
        expected = np.searchsorted(np.sort(self.training[-1399:]), 0.75, side="right") / 1399.0
        self.assertEqual(result.rank[0], expected)

    def test_24_duplicate_tie_handling_exact(self) -> None:
        training = np.full(1399, 0.5)
        result = p0.causal_rolling_rank(training, [0.5])
        self.assertEqual(result.threshold[0], 0.5)
        self.assertEqual(result.rank[0], 1.0)
        self.assertTrue(result.eligible[0])

    def test_25_eligibility_uses_probability_not_rank_cutoff(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("is_eligible = bool(probability >= threshold)", source)
        self.assertNotIn("rank >= GATE_QUANTILE", source)

    def test_26_exact_threshold_is_eligible(self) -> None:
        reference = self.training[-1399:]
        threshold = float(np.quantile(reference, 0.90, method="higher"))
        result = p0.causal_rolling_rank(self.training, [threshold])
        self.assertTrue(result.eligible[0])

    def test_27_future_mutation_does_not_change_past_outputs(self) -> None:
        validation = np.asarray([0.1, 0.2, 0.3, 0.4])
        changed = validation.copy()
        changed[3] = 0.99
        first = p0.causal_rolling_rank(self.training, validation)
        second = p0.causal_rolling_rank(self.training, changed)
        np.testing.assert_array_equal(first.threshold[:3], second.threshold[:3])
        np.testing.assert_array_equal(first.rank[:3], second.rank[:3])
        np.testing.assert_array_equal(first.eligible[:3], second.eligible[:3])

    def test_28_changing_current_score_does_not_change_preinsertion_threshold(self) -> None:
        first = p0.causal_rolling_rank(self.training, [0.2, 0.3])
        second = p0.causal_rolling_rank(self.training, [0.8, 0.3])
        self.assertEqual(first.threshold[0], second.threshold[0])

    def test_29_earlier_score_can_affect_later_threshold(self) -> None:
        initial = np.concatenate(([1.0], np.zeros(1259), np.ones(139)))
        self.assertEqual(len(initial), 1399)
        low = p0.causal_rolling_rank(initial, [0.0, 0.5])
        high = p0.causal_rolling_rank(initial, [1.0, 0.5])
        self.assertEqual(low.threshold[0], high.threshold[0])
        self.assertNotEqual(low.threshold[1], high.threshold[1])

    def test_30_insufficient_initial_reference_is_clean_failure(self) -> None:
        with self.assertRaises(p0.DevelopmentReadinessFailure):
            p0.causal_rolling_rank(np.zeros(1398), [0.5])

    def test_31_nonfinite_probability_is_protocol_violation(self) -> None:
        with self.assertRaises(p0.ProtocolViolation):
            p0.causal_rolling_rank(self.training, [np.nan])


class OccupancyTests(unittest.TestCase):
    def test_32_occupancy_schedule_entry_and_exit_exact(self) -> None:
        result = p0.occupancy_support(np.asarray([0], dtype=np.int64), np.asarray([True]))
        np.testing.assert_array_equal(result.entry_timestamp_us, [250_000])
        np.testing.assert_array_equal(result.exit_timestamp_us, [600_250_000])
        self.assertTrue(result.timing_exact)

    def test_33_decision_at_t_plus_600s_remains_blocked(self) -> None:
        timestamps = np.asarray([0, 600_000_000], dtype=np.int64)
        result = p0.occupancy_support(timestamps, np.asarray([True, True]))
        self.assertEqual(result.executed_nonoverlapping_opportunity_count, 1)
        self.assertEqual(result.ignored_eligible_signals_while_occupied, 1)

    def test_34_next_decision_after_actual_exit_can_execute(self) -> None:
        timestamps = np.asarray([0, 600_250_000], dtype=np.int64)
        result = p0.occupancy_support(timestamps, np.asarray([True, True]))
        self.assertEqual(result.executed_nonoverlapping_opportunity_count, 2)
        self.assertEqual(result.ignored_eligible_signals_while_occupied, 0)

    def test_35_active_and_abstention_exact(self) -> None:
        active = p0.occupancy_support(np.asarray([0]), np.asarray([True]))
        abstention = p0.occupancy_support(np.asarray([0]), np.asarray([False]))
        self.assertEqual(active.state, "ACTIVE")
        self.assertEqual(abstention.state, "ABSTENTION")
        self.assertEqual(abstention.exposure_fraction, 0.0)

    def test_36_flat_only_accounting_and_no_overlap(self) -> None:
        timestamps = np.arange(21, dtype=np.int64) * 60_000_000
        result = p0.occupancy_support(timestamps, np.ones(21, dtype=bool))
        self.assertEqual(
            result.eligible_signal_count,
            result.executed_nonoverlapping_opportunity_count
            + result.ignored_eligible_signals_while_occupied,
        )
        self.assertTrue(result.accounting_consistent)
        self.assertTrue(result.no_position_overlap)
        self.assertTrue(np.all(result.entry_timestamp_us[1:] >= result.exit_timestamp_us[:-1]))


class MetricAndNullTests(unittest.TestCase):
    def test_37_auc_ap_and_ratio_match_sklearn(self) -> None:
        y = np.asarray([0, 1, 0, 1, 1, 0])
        score = np.asarray([0.1, 0.9, 0.2, 0.8, 0.7, 0.3])
        metric = p0.ranking_metrics(y, score)
        self.assertEqual(metric["roc_auc"], roc_auc_score(y, score))
        self.assertEqual(metric["average_precision"], average_precision_score(y, score))
        self.assertEqual(metric["average_precision_over_prevalence"], metric["average_precision"] / metric["prevalence"])

    def test_38_fold_and_pooled_metric_construction(self) -> None:
        y1, s1 = np.asarray([0, 1]), np.asarray([0.1, 0.9])
        y2, s2 = np.asarray([1, 0]), np.asarray([0.8, 0.2])
        pooled = p0.ranking_metrics(np.concatenate((y1, y2)), np.concatenate((s1, s2)))
        self.assertEqual(pooled["n"], 4)
        self.assertEqual(p0.ranking_metrics(y1, s1)["roc_auc"], 1.0)
        self.assertEqual(p0.ranking_metrics(y2, s2)["average_precision"], 1.0)

    def test_39_causal_gate_precision_and_lift(self) -> None:
        metric = p0.causal_gate_metrics(
            np.asarray([1, 0, 1, 0, 0]),
            np.asarray([True, True, False, False, False]),
        )
        self.assertEqual(metric["eligible_signal_count"], 2)
        self.assertEqual(metric["eligible_positive_count"], 1)
        self.assertEqual(metric["eligible_precision"], 0.5)
        self.assertEqual(metric["eligible_lift"], 1.25)

    def test_40_zero_eligible_is_explicit_undefined(self) -> None:
        metric = p0.causal_gate_metrics(np.asarray([0, 1]), np.asarray([False, False]))
        self.assertEqual(metric["eligible_signal_count"], 0)
        self.assertEqual(metric["eligible_fraction"], 0.0)
        self.assertIsNone(metric["eligible_precision"])
        self.assertIsNone(metric["eligible_lift"])

    def test_41_valid_shift_set_exact(self) -> None:
        np.testing.assert_array_equal(
            p0.eligible_fold_preserving_shifts([120, 120, 120, 120]),
            [30, 60, 90],
        )

    def test_42_zero_shift_rejected(self) -> None:
        labels = [np.tile([0, 1], 60) for _ in range(4)]
        with self.assertRaises(p0.ProtocolViolation):
            p0.fold_preserving_shift(labels, 0)

    def test_43_too_small_shift_rejected(self) -> None:
        labels = [np.tile([0, 1], 60) for _ in range(4)]
        with self.assertRaises(p0.ProtocolViolation):
            p0.fold_preserving_shift(labels, 15)

    def test_44_folds_never_mix_under_shift(self) -> None:
        labels = [
            np.asarray(([0] * (60 + i)) + ([1] * (60 - i)), dtype=np.int8)
            for i in range(4)
        ]
        shifted = p0.fold_preserving_shift(labels, 30)
        for original, result in zip(labels, shifted):
            np.testing.assert_array_equal(result, np.roll(original, 30))

    def test_45_same_k_applied_to_every_fold_per_replicate(self) -> None:
        labels = [np.tile([0, 1], 60).astype(np.int8) for _ in range(4)]
        scores = [np.linspace(0.0, 1.0, 120) for _ in range(4)]
        calls: list[int] = []
        original = p0.fold_preserving_shift

        def wrapped(values: object, k: int) -> tuple[np.ndarray, ...]:
            calls.append(k)
            return original(values, k)

        with patch.object(p0, "fold_preserving_shift", side_effect=wrapped):
            result = p0.temporal_null(labels, scores)
        self.assertEqual(calls, [30, 60, 90])
        self.assertEqual(result["number_of_shifts"], 3)
        self.assertTrue(result["same_shift_within_every_fold"])

    def test_46_q95_uses_higher_method(self) -> None:
        values = np.asarray([0.1, 0.2, 0.3, 0.4])
        self.assertEqual(
            p0.higher_quantile(values, 0.95),
            np.quantile(values, 0.95, method="higher"),
        )

    def test_47_empirical_p_plus_one_formula(self) -> None:
        null = np.asarray([0.1, 0.2, 0.3, 0.4])
        expected = (1 + 2) / (1 + 4)
        self.assertEqual(p0.empirical_one_sided_p(null, 0.3), expected)


class ModelAndSupportTests(unittest.TestCase):
    def test_48_model_fit_one_class_is_clean_failure(self) -> None:
        with self.assertRaises(p0.DevelopmentReadinessFailure):
            p0._fit_readiness_logistic(np.ones((3, 1)), np.asarray([0, 0, 0]), context="synthetic")

    def test_49_model_fit_nonbinary_is_protocol_violation(self) -> None:
        with self.assertRaises(p0.ProtocolViolation):
            p0._fit_readiness_logistic(np.ones((2, 1)), np.asarray([0, 2]), context="synthetic")

    def test_50_model_fit_nonfinite_is_protocol_violation(self) -> None:
        with self.assertRaises(p0.ProtocolViolation):
            p0._fit_readiness_logistic(np.ones((3, 1)), np.asarray([0.0, np.nan, 1.0]), context="synthetic")

    def test_51_fold_model_scores_training_before_validation(self) -> None:
        train = [
            make_day(day, n=500, start_us=index * p0.DAY_US)
            for index, day in enumerate(p0.HISTORICAL_DAYS[:3])
        ]
        validation = make_day(p0.HISTORICAL_DAYS[3], n=4, start_us=3 * p0.DAY_US)
        calls: list[int] = []

        class FakeModel:
            def predict_proba(self, X: np.ndarray) -> np.ndarray:
                calls.append(len(X))
                values = np.asarray(X, dtype=float)[:, 0]
                lo, hi = float(np.min(values)), float(np.max(values))
                return np.full(len(values), 0.5) if hi == lo else (values - lo) / (hi - lo)

        with patch.object(p0, "_fit_readiness_logistic", return_value=FakeModel()), patch.object(
            p0, "_model_record", return_value={"synthetic": True}
        ):
            result = p0.evaluate_fold(1, train, validation)
        self.assertEqual(calls, [1500, 4])
        self.assertEqual(result.training_probability_count, 1500)

    def test_52_parent_support_equivalence_success(self) -> None:
        raw = SimpleNamespace(
            day=p0.HISTORICAL_DAYS[0],
            ts=np.arange(3000, dtype=np.int64) * p0.GRID_US,
        )
        decisions = np.arange(0, len(raw.ts), p0.DECISION_STEP_ROWS)
        rows = len(decisions)
        X = np.full((rows, len(p0.R_FEATURE_NAMES)), np.nan)
        valid = np.zeros(rows, dtype=bool)
        valid[1] = True
        X[1] = 1.0
        frozen = SimpleNamespace(
            timestamp_us=raw.ts[decisions],
            X_R=X,
            valid_R=valid,
            y=np.zeros(rows, dtype=np.int8),
        )
        oracle = np.full(rows, np.nan)
        oracle[1] = 0.0
        outcomes = {
            "valid": valid.copy(),
            "oracle_gross_bps": oracle,
            "entry_index": decisions + 1,
            "exit_index": decisions + 1 + 2400,
        }
        with patch.object(p0, "build_day_dataset", return_value=frozen), patch.object(
            p0, "executable_fixed_horizon", return_value=outcomes
        ):
            built = p0.build_opportunity_day(raw)
        self.assertIs(built.parent_support_exact, True)
        np.testing.assert_array_equal(built.common_support, valid)

    def test_53_parent_support_mismatch_is_protocol_violation(self) -> None:
        raw = SimpleNamespace(day=p0.HISTORICAL_DAYS[0], ts=np.arange(481, dtype=np.int64) * p0.GRID_US)
        decisions = np.arange(0, len(raw.ts), p0.DECISION_STEP_ROWS)
        rows = len(decisions)
        frozen = SimpleNamespace(
            timestamp_us=raw.ts[decisions],
            X_R=np.ones((rows, len(p0.R_FEATURE_NAMES))),
            valid_R=np.ones(rows, dtype=bool),
            y=np.zeros(rows, dtype=np.int8),
        )
        outcomes = {
            "valid": np.zeros(rows, dtype=bool),
            "oracle_gross_bps": np.zeros(rows),
            "entry_index": decisions + 1,
            "exit_index": decisions + 2401,
        }
        with patch.object(p0, "build_day_dataset", return_value=frozen), patch.object(
            p0, "executable_fixed_horizon", return_value=outcomes
        ), self.assertRaises(p0.ProtocolViolation):
            p0.build_opportunity_day(raw)

    def test_54_wrong_fold_chronology_is_protocol_violation(self) -> None:
        training = [make_day(day, n=500) for day in p0.HISTORICAL_DAYS[:3]]
        training[0] = make_day(p0.HISTORICAL_DAYS[1], n=500)
        with self.assertRaises(p0.ProtocolViolation):
            p0.evaluate_fold(1, training, make_day(p0.HISTORICAL_DAYS[3], n=4))


class GateAndAdjudicationTests(unittest.TestCase):
    def test_55_all_twelve_gates_required_for_pass(self) -> None:
        core = make_core()
        gates = p0.build_primary_gates(core, invariants_pass=True)
        self.assertEqual(tuple(gates), p0.PRIMARY_GATE_NAMES)
        self.assertEqual(len(gates), 12)
        self.assertTrue(all(gates.values()))
        self.assertEqual(
            p0.adjudicate_status(all_true_invariants(), gates, pipeline_completed=True, clean_readiness_failure=False),
            p0.PASS_STATUS,
        )

    def test_56_flipping_each_gate_prevents_pass(self) -> None:
        base = {name: True for name in p0.PRIMARY_GATE_NAMES}
        for name in p0.PRIMARY_GATE_NAMES:
            changed = dict(base)
            changed[name] = False
            self.assertEqual(
                p0.adjudicate_status(all_true_invariants(), changed, pipeline_completed=True, clean_readiness_failure=False),
                p0.FAIL_STATUS,
                name,
            )

    def test_57_clean_support_failure_is_fail(self) -> None:
        invariants = all_true_invariants()
        for name in p0.EVALUATED_INVARIANT_NAMES:
            invariants[name] = False
        status = p0.adjudicate_status(
            invariants,
            {name: False for name in p0.PRIMARY_GATE_NAMES},
            pipeline_completed=False,
            clean_readiness_failure=True,
        )
        self.assertEqual(status, p0.FAIL_STATUS)

    def test_58_protocol_or_causality_failure_is_invalid(self) -> None:
        invariants = all_true_invariants()
        invariants["no_protocol_violation_detected"] = False
        self.assertEqual(
            p0.adjudicate_status(invariants, {name: False for name in p0.PRIMARY_GATE_NAMES}, pipeline_completed=False, clean_readiness_failure=False),
            p0.INVALID_STATUS,
        )

    def test_59_evaluated_causality_failure_is_invalid(self) -> None:
        invariants = all_true_invariants()
        invariants["future_scores_never_enter_past_references"] = False
        self.assertEqual(
            p0.adjudicate_status(invariants, {name: True for name in p0.PRIMARY_GATE_NAMES}, pipeline_completed=True, clean_readiness_failure=False),
            p0.INVALID_STATUS,
        )

    def test_60_non_builtin_bool_invariant_rejected(self) -> None:
        invariants = all_true_invariants()
        invariants["reference_length_always_1399"] = np.bool_(True)
        with self.assertRaises(p0.ProtocolViolation):
            p0.adjudicate_status(invariants, {name: True for name in p0.PRIMARY_GATE_NAMES}, pipeline_completed=True, clean_readiness_failure=False)

    def test_61_support_threshold_boundary_exact(self) -> None:
        self.assertTrue(
            p0.support_is_sufficient(
                {"n": 1200, "positives": 10, "negatives": 100}
            )
        )
        for metric in (
            {"n": 1199, "positives": 10, "negatives": 100},
            {"n": 1200, "positives": 9, "negatives": 100},
            {"n": 1200, "positives": 10, "negatives": 99},
        ):
            self.assertFalse(p0.support_is_sufficient(metric))

    def test_62_fewer_than_three_active_folds_is_scientific_fail(self) -> None:
        core = make_core(active=(True, True, False, False))
        gates = p0.build_primary_gates(core, invariants_pass=True)
        self.assertIs(gates[p0.PRIMARY_GATE_NAMES[11]], False)
        self.assertEqual(
            p0.adjudicate_status(
                all_true_invariants(),
                gates,
                pipeline_completed=True,
                clean_readiness_failure=False,
            ),
            p0.FAIL_STATUS,
        )


class JsonAndOneShotTests(unittest.TestCase):
    def test_63_json_rejects_nan(self) -> None:
        payload = minimal_payload()
        payload["bad"] = float("nan")
        with self.assertRaises(Exception):
            p0._encode_payload(payload)

    def test_64_numpy_scalars_normalized_safely(self) -> None:
        payload = minimal_payload()
        payload["numpy"] = {"bool": np.bool_(True), "int": np.int64(2), "float": np.float64(0.5)}
        encoded = p0._encode_payload(payload)
        parsed = json.loads(encoded)
        self.assertEqual(parsed["numpy"], {"bool": True, "int": 2, "float": 0.5})

    def test_65_existing_final_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"
            output.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                p0._write_once(output, minimal_payload())
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve")

    def test_66_existing_part_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"
            part = Path(f"{output}.part")
            part.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                p0._write_once(output, minimal_payload())
            self.assertEqual(part.read_text(encoding="utf-8"), "preserve")

    def test_67_atomic_first_write_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"
            digest = p0._write_once(output, minimal_payload())
            self.assertTrue(output.is_file())
            self.assertFalse(Path(f"{output}.part").exists())
            self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), digest)
            json.loads(output.read_text(encoding="utf-8"))


class CliAndRunClassificationTests(unittest.TestCase):
    def _main_status(self, status: str) -> tuple[int, dict[str, object], Mock]:
        result = p0.RunWriteResult({"status": status}, "d" * 64)
        argv = [
            "--mode", "historical-development",
            "--workspace", "/synthetic/workspace",
            "--frozen-commit", "a" * 40,
            "--output", "/synthetic/result.json",
        ]
        stream = io.StringIO()
        with patch.object(p0, "run_historical_development", return_value=result) as runner, redirect_stdout(stream):
            code = p0.main(argv)
        return code, json.loads(stream.getvalue()), runner

    def test_68_main_forwards_exact_arguments_and_argv(self) -> None:
        code, output, runner = self._main_status(p0.PASS_STATUS)
        self.assertEqual(code, 0)
        runner.assert_called_once_with(
            Path("/synthetic/workspace"),
            "a" * 40,
            Path("/synthetic/result.json"),
            argv=[
                "--mode", "historical-development",
                "--workspace", "/synthetic/workspace",
                "--frozen-commit", "a" * 40,
                "--output", "/synthetic/result.json",
            ],
        )
        self.assertEqual(set(output), {"output", "output_sha256", "status"})

    def test_69_main_pass_returns_zero(self) -> None:
        code, output, _ = self._main_status(p0.PASS_STATUS)
        self.assertEqual(code, 0)
        self.assertEqual(output["status"], p0.PASS_STATUS)

    def test_70_main_fail_returns_one(self) -> None:
        code, output, _ = self._main_status(p0.FAIL_STATUS)
        self.assertEqual(code, 1)
        self.assertEqual(output["status"], p0.FAIL_STATUS)

    def test_71_main_invalid_returns_one(self) -> None:
        code, output, _ = self._main_status(p0.INVALID_STATUS)
        self.assertEqual(code, 1)
        self.assertEqual(output["status"], p0.INVALID_STATUS)

    def test_72_clean_run_failure_preserves_provenance_and_is_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "synthetic.json"
            with patch.object(p0, "assert_frozen_workspace"), patch.object(
                p0, "verify_frozen_references", return_value={"synthetic": True}
            ), patch.object(
                p0, "_verify_historical_inputs", return_value=[]
            ), patch.object(
                p0, "_load_historical_days", return_value={}
            ), patch.object(
                p0,
                "historical_development_core",
                side_effect=p0.DevelopmentReadinessFailure("clean support failure"),
            ), patch.object(p0, "_git", return_value=""):
                result = p0.run_historical_development(
                    Path(tmp), "a" * 40, output, argv=["synthetic"]
                )
            self.assertEqual(result.payload["status"], p0.FAIL_STATUS)
            invariants = result.payload["invariants"]
            self.assertIs(invariants["no_protocol_violation_detected"], True)
            self.assertIs(invariants["preregistration_sha_verified"], True)
            self.assertIs(invariants["exp024_result_sha_and_status_verified"], True)
            self.assertIs(invariants["exp028_result_sha_and_status_verified"], True)
            self.assertIs(invariants["historical_input_provenance_verified"], True)

    def test_73_unexpected_runtime_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "synthetic.json"
            with patch.object(p0, "assert_frozen_workspace"), patch.object(
                p0, "verify_frozen_references", side_effect=RuntimeError("unexpected")
            ), patch.object(p0, "_git", return_value=""):
                result = p0.run_historical_development(
                    Path(tmp), "a" * 40, output, argv=["synthetic"]
                )
            self.assertEqual(result.payload["status"], p0.INVALID_STATUS)
            self.assertIs(result.payload["invariants"]["no_protocol_violation_detected"], False)

    def test_74_synthetic_full_pass_run_is_json_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "synthetic.json"
            core = make_core()
            with patch.object(p0, "assert_frozen_workspace"), patch.object(
                p0, "verify_frozen_references", return_value={"synthetic": True}
            ), patch.object(
                p0, "_verify_historical_inputs", return_value=[]
            ), patch.object(
                p0, "_load_historical_days", return_value=core.days
            ), patch.object(
                p0, "historical_development_core", return_value=core
            ), patch.object(p0, "_git", return_value=""):
                result = p0.run_historical_development(
                    Path(tmp), "a" * 40, output, argv=["synthetic"]
                )
            self.assertEqual(result.payload["status"], p0.PASS_STATUS)
            self.assertTrue(all(type(value) is bool for value in result.payload["invariants"].values()))
            self.assertTrue(all(result.payload["invariants"].values()))
            self.assertTrue(all(result.payload["primary_gates"].values()))
            parsed = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(parsed["status"], p0.PASS_STATUS)


if __name__ == "__main__":
    unittest.main()

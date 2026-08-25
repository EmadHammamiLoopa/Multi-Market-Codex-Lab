from __future__ import annotations

import math
import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np

from multimarket.codex_exp001 import (
    _fit_side,
    calibration_metrics,
    executable_outcomes,
    greedy_nonoverlap,
    run,
    score_probabilistic_actions,
    split_calibration_selection,
)
from multimarket.codex_research import ResearchSealError
from multimarket.v23_phase0dl_score import BLOCKS, DayData


def synthetic_day(*, day: date = date(2026, 1, 1), rows: int = 100) -> DayData:
    ts = np.arange(rows, dtype=np.int64) * 250_000
    bid = np.linspace(100.0, 101.0, rows)
    ask = bid + 0.02
    mid = (bid + ask) / 2.0
    valid = np.ones(rows, dtype=bool)
    features = {
        block: np.zeros((rows, len(names)), dtype=np.float32)
        for block, names in BLOCKS.items()
    }
    return DayData(day, ts, bid, ask, mid, valid.copy(), {block: valid.copy() for block in BLOCKS}, features)


class ExecutableOutcomeTests(unittest.TestCase):
    def test_touch_returns_use_delayed_entry_and_future_exit(self) -> None:
        day = synthetic_day(rows=12)
        outcomes = executable_outcomes(day, "L0", 1, primary_cost_bps=8.0)
        expected_long = 10_000.0 * math.log(day.bid[5] / day.ask[1])
        expected_short = 10_000.0 * math.log(day.bid[1] / day.ask[5])
        self.assertEqual(int(outcomes.entry_index[0]), 1)
        self.assertEqual(int(outcomes.exit_index[0]), 5)
        self.assertAlmostEqual(float(outcomes.long_gross_bps[0]), expected_long, places=12)
        self.assertAlmostEqual(float(outcomes.short_gross_bps[0]), expected_short, places=12)
        self.assertEqual(bool(outcomes.long_positive[0]), expected_long > 8.0)
        self.assertEqual(bool(outcomes.short_positive[0]), expected_short > 8.0)

    def test_invalid_entry_or_exit_book_excludes_row(self) -> None:
        day = synthetic_day(rows=12)
        day.book_valid[5] = False
        outcomes = executable_outcomes(day, "L0", 1)
        self.assertFalse(bool(outcomes.valid[0]))

    def test_day_end_labels_are_excluded(self) -> None:
        day = synthetic_day(rows=12)
        outcomes = executable_outcomes(day, "L0", 1)
        self.assertFalse(bool(outcomes.valid[-1]))
        self.assertFalse(bool(outcomes.valid[-5]))

    def test_sealed_day_fails_before_scoring(self) -> None:
        day = synthetic_day(day=date(2026, 8, 1))
        with self.assertRaises(ResearchSealError):
            executable_outcomes(day, "L0", 1)

    def test_split_purges_calibration_outcomes_crossing_midpoint(self) -> None:
        day = synthetic_day(rows=100)
        outcomes = executable_outcomes(day, "L0", 1)
        calibration, selection = split_calibration_selection(outcomes, horizon_s=1, n_rows=100)
        self.assertLessEqual(int(calibration.max()), 44)
        self.assertGreaterEqual(int(selection.min()), 50)
        self.assertTrue(set(calibration.tolist()).isdisjoint(selection.tolist()))

    def test_nonoverlap_includes_latency_and_horizon(self) -> None:
        chosen = greedy_nonoverlap(np.asarray([0, 1, 4, 5, 6, 10]), horizon_s=1)
        np.testing.assert_array_equal(chosen, np.asarray([0, 5, 10]))


class DecisionAndReportingTests(unittest.TestCase):
    def test_logistic_and_platt_adapter_produces_finite_forecasts(self) -> None:
        rng = np.random.default_rng(20260825)
        X_train = rng.normal(size=(200, 3))
        y_train = (X_train[:, 0] + 0.2 * X_train[:, 1] > 0.0).astype(np.int8)
        X_calibration = rng.normal(size=(100, 3))
        y_calibration = (X_calibration[:, 0] + 0.2 * X_calibration[:, 1] > 0.0).astype(np.int8)
        net = np.where(y_calibration == 1, 3.0, -2.0)
        model = _fit_side(
            X_train,
            y_train,
            X_calibration,
            y_calibration,
            net,
            c_value=0.1,
        )
        probability, utility = model.forecast(X_calibration[:5])
        self.assertTrue(np.all(np.isfinite(probability)))
        self.assertTrue(np.all((probability >= 0.0) & (probability <= 1.0)))
        self.assertTrue(np.all(np.isfinite(utility)))

    def test_equal_action_utilities_abstain(self) -> None:
        day = synthetic_day(rows=12)
        outcomes = executable_outcomes(day, "L0", 1)
        score = score_probabilistic_actions(
            day,
            outcomes,
            np.asarray([0]),
            np.asarray([0.9]),
            np.asarray([0.9]),
            np.asarray([1.0]),
            np.asarray([1.0]),
            probability_threshold=0.55,
            horizon_s=1,
        )
        self.assertEqual(score["costs"]["8"]["trades"], 0)

    def test_nonfinite_probability_abstains(self) -> None:
        day = synthetic_day(rows=12)
        outcomes = executable_outcomes(day, "L0", 1)
        score = score_probabilistic_actions(
            day,
            outcomes,
            np.asarray([0]),
            np.asarray([np.nan]),
            np.asarray([0.99]),
            np.asarray([1.0]),
            np.asarray([1.0]),
            probability_threshold=0.55,
            horizon_s=1,
        )
        self.assertEqual(score["costs"]["8"]["trades"], 0)

    def test_calibration_metrics_are_finite_and_binned(self) -> None:
        metrics = calibration_metrics(np.asarray([0, 0, 1, 1]), np.asarray([0.1, 0.2, 0.8, 0.9]), bins=2)
        self.assertEqual(metrics["rows"], 4)
        self.assertTrue(math.isfinite(metrics["brier"]))
        self.assertTrue(math.isfinite(metrics["log_loss"]))
        self.assertTrue(math.isfinite(metrics["ece"]))
        self.assertEqual(len(metrics["bins"]), 2)

    def test_empty_calibration_metrics_are_explicit(self) -> None:
        metrics = calibration_metrics(np.asarray([], dtype=np.int8), np.asarray([], dtype=float))
        self.assertEqual(metrics["rows"], 0)
        self.assertIsNone(metrics["brier"])

    def test_missing_inputs_produce_not_run_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            code, artifact, payload = run(root / "missing", root / "output", check_inputs_only=True)
            self.assertEqual(code, 2)
            self.assertEqual(payload["status"], "NOT_RUN_MISSING_INPUT")
            self.assertEqual(len(payload["missing_inputs"]), 14)
            self.assertTrue(artifact.is_file())
            self.assertNotIn("result", payload["missing_inputs"])


if __name__ == "__main__":
    unittest.main()

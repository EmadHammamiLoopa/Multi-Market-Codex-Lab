import unittest
from datetime import date

import numpy as np

from src.multimarket.codex_exp018_p1 import (
    AUG_FEATURE_SHA256,
    Config,
    ExecutionState,
    EXP017_RESULT_SHA256,
    EXPERIMENT_ID,
    FAIL_STATUS,
    PASS_STATUS,
    SEED,
    SYMBOL,
    TRAIN_DAYS,
    VALIDATION_DAY,
    VOL_FEATURE,
    _delta,
    _ge,
    _gt,
    _stable_seed,
    invalid_payload,
)


class Exp018P1Tests(unittest.TestCase):
    def test_identity_scope_and_parent_hashes(self):
        self.assertEqual(EXPERIMENT_ID, "CODEX-EXP-018-P1")
        self.assertEqual(SYMBOL, "BTCUSDT")
        self.assertEqual(VALIDATION_DAY, date(2026, 8, 1))
        self.assertEqual(
            TRAIN_DAYS,
            tuple(date(2026, m, 1) for m in range(1, 8)),
        )
        self.assertEqual(VOL_FEATURE, "rv_30m_bps")
        self.assertEqual(
            EXP017_RESULT_SHA256,
            "97c76a19a34971c7cef9eb01ad6c5b39d4e2c9885ed39a41054adef397ce4561",
        )
        self.assertEqual(
            AUG_FEATURE_SHA256,
            "62c72f13f7176d9b4d9bdb69ad940cdcc56858698d64b4a061cecbb4a09ec5f5",
        )

    def test_frozen_model_and_gate_thresholds(self):
        c = Config()
        self.assertEqual(c.model_c, 1.0)
        self.assertEqual(c.solver, "lbfgs")
        self.assertIsNone(c.class_weight)
        self.assertEqual(c.max_iter, 1000)
        self.assertEqual(c.seed, 20260825)
        self.assertEqual(c.auc_min, 0.60)
        self.assertEqual(c.ap_over_prevalence_min, 1.30)
        self.assertEqual(c.top_decile_lift_min, 1.50)
        self.assertEqual(c.nonoverlap_auc_min, 0.57)
        self.assertEqual(c.nonoverlap_top_decile_lift_min, 1.25)
        self.assertEqual(c.timing_placebo_auc_delta_min, 0.03)
        self.assertEqual(c.canary_auc_delta_min, 0.10)

    def test_target_semantics_frozen(self):
        c = Config()
        self.assertEqual(c.decision_step_s, 60)
        self.assertEqual(c.entry_delay_ms, 250)
        self.assertEqual(c.horizon_s, 600)
        self.assertEqual(c.label_threshold_bps, 24.0)

    def test_placebo_seed_is_deterministic_and_day_specific(self):
        a = _stable_seed(date(2026, 1, 1))
        b = _stable_seed(date(2026, 1, 1))
        c = _stable_seed(date(2026, 2, 1))
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertGreaterEqual(a, 0)
        self.assertLess(a, 2**32)

    def test_placebo_permutation_preserves_class_count(self):
        y = np.array([0, 1, 0, 1, 1, 0, 0, 1], dtype=np.int8)
        rng = np.random.default_rng(_stable_seed(date(2026, 3, 1)))
        yp = y[rng.permutation(len(y))]
        self.assertEqual(int(y.sum()), int(yp.sum()))
        self.assertCountEqual(y.tolist(), yp.tolist())

    def test_gate_helpers(self):
        self.assertTrue(_ge(0.60, 0.60))
        self.assertFalse(_ge(0.599, 0.60))
        self.assertFalse(_ge(None, 0.60))
        self.assertTrue(_gt(0.0001, 0.0))
        self.assertFalse(_gt(0.0, 0.0))
        self.assertEqual(_delta(0.65, 0.60), 0.05)
        self.assertIsNone(_delta(None, 0.60))

    def test_status_literals_exact(self):
        self.assertEqual(
            PASS_STATUS,
            "INDEPENDENT_VOLATILITY_REGIME_PREDICTABILITY_CONFIRMED",
        )
        self.assertEqual(
            FAIL_STATUS,
            "FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED",
        )

    def test_invalid_payload_before_aug_open_is_truthful(self):
        state = ExecutionState(
            sealed_aug1_analytically_opened=False,
            target_scored=False,
            model_fit=True,
            auc_scored=False,
        )
        r = invalid_payload(
            RuntimeError("hash mismatch"),
            "a" * 40,
            state,
        )
        self.assertEqual(r["status"], "INVALID")
        self.assertFalse(r["sealed_aug1_analytically_opened"])
        self.assertFalse(r["target_scored"])
        self.assertTrue(r["model_fit"])
        self.assertFalse(r["auc_scored"])
        self.assertFalse(r["older_august_holdout_opened"])
        self.assertFalse(r["direction_scored"])
        self.assertFalse(r["pnl_scored"])
        self.assertFalse(r["network_accessed"])

    def test_invalid_payload_after_aug_open_is_truthful(self):
        state = ExecutionState(
            sealed_aug1_analytically_opened=True,
            target_scored=True,
            model_fit=True,
            auc_scored=True,
        )
        r = invalid_payload(
            ValueError("metric failure"),
            "b" * 40,
            state,
        )
        self.assertTrue(r["sealed_aug1_analytically_opened"])
        self.assertTrue(r["target_scored"])
        self.assertTrue(r["model_fit"])
        self.assertTrue(r["auc_scored"])

    def test_no_older_august_dates_in_config(self):
        c = Config()
        self.assertEqual(c.validation_day, "2026-08-01")
        self.assertNotIn("2026-08-04", c.training_days)
        self.assertNotIn("2026-08-23", c.training_days)


if __name__ == "__main__":
    unittest.main()

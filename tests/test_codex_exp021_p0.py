import unittest
from datetime import date

import numpy as np

from multimarket.codex_exp021_p0 import (
    CLIP_EPS,
    Config,
    EXP019_RESULT_SHA256,
    EXP020_RESULT_SHA256,
    EXPERIMENT_ID,
    NO_READY_STATUS,
    OOF_DAYS,
    OUTER_DAYS,
    READY_STATUS,
    VOL_FEATURE,
    _logit,
    _sigmoid,
    apply_intercept,
    fit_intercept_delta,
    readiness,
)


class Exp021P0Tests(unittest.TestCase):
    def test_identity_scope_and_parent_hashes(self):
        c = Config()
        self.assertEqual(EXPERIMENT_ID, "CODEX-EXP-021-P0")
        self.assertEqual(VOL_FEATURE, "rv_30m_bps")
        self.assertEqual(
            OUTER_DAYS,
            tuple(date(2026, m, 1) for m in range(4, 8)),
        )
        self.assertEqual(
            OOF_DAYS,
            tuple(date(2026, m, 1) for m in range(3, 7)),
        )
        self.assertEqual(
            EXP020_RESULT_SHA256,
            "cbbe2bd8a148b556cb0670b7a5adb4f49aef677e85ef77b8c4bea01a53e69249",
        )
        self.assertEqual(
            EXP019_RESULT_SHA256,
            "a6d55db8e938a0c9b80f3e39117c07fd85e0316d408b159f6bd421ffa7920def",
        )
        self.assertEqual(c.min_improved_folds, 3)
        self.assertEqual(c.auc_tolerance, 1e-12)

    def test_logit_sigmoid_roundtrip(self):
        p = np.array([0.001, 0.2, 0.5, 0.8, 0.999])
        q = _sigmoid(_logit(p))
        np.testing.assert_allclose(p, q, rtol=0, atol=1e-12)

    def test_clipping_is_frozen(self):
        p = np.array([0.0, 1.0])
        z = _logit(p)
        self.assertTrue(np.all(np.isfinite(z)))
        self.assertAlmostEqual(_sigmoid(z)[0], CLIP_EPS, places=12)
        self.assertAlmostEqual(_sigmoid(z)[1], 1 - CLIP_EPS, places=12)

    def test_intercept_delta_matches_history_prevalence(self):
        p = np.array([0.05, 0.1, 0.2, 0.4, 0.7, 0.8])
        y = np.array([0, 0, 0, 1, 1, 1], dtype=np.int8)
        delta = fit_intercept_delta(p, y)
        q = apply_intercept(p, delta)
        self.assertAlmostEqual(
            float(np.mean(q)),
            float(np.mean(y)),
            places=12,
        )

    def test_intercept_preserves_order(self):
        p = np.array([0.1, 0.2, 0.4, 0.9])
        q = apply_intercept(p, -1.5)
        self.assertTrue(
            np.array_equal(
                np.argsort(p, kind="mergesort"),
                np.argsort(q, kind="mergesort"),
            )
        )

    def test_readiness_selects_only_ready_candidate(self):
        folds = [
            {
                "platt_slope": 1.0,
                "metrics": {},
            }
            for _ in range(4)
        ]
        aggregate = {
            "tracks": {
                "RAW": {
                    "aggregate_brier_score": 0.20,
                    "aggregate_log_loss": 0.50,
                    "aggregate_fold_normalized_brier_skill": -0.1,
                },
                "ROLLING_OOF_INTERCEPT": {
                    "aggregate_brier_score": 0.18,
                    "aggregate_log_loss": 0.45,
                    "aggregate_fold_normalized_brier_skill": 0.05,
                    "folds_brier_improved_vs_raw": 3,
                    "folds_logloss_improved_vs_raw": 3,
                    "folds_auc_preserved": 4,
                },
                "ROLLING_OOF_PLATT": {
                    "aggregate_brier_score": 0.21,
                    "aggregate_log_loss": 0.49,
                    "aggregate_fold_normalized_brier_skill": -0.02,
                    "folds_brier_improved_vs_raw": 2,
                    "folds_logloss_improved_vs_raw": 2,
                    "folds_auc_preserved": 4,
                },
            }
        }
        r, selected, status = readiness(folds, aggregate)
        self.assertTrue(r["ROLLING_OOF_INTERCEPT"]["ready"])
        self.assertFalse(r["ROLLING_OOF_PLATT"]["ready"])
        self.assertEqual(selected, "ROLLING_OOF_INTERCEPT")
        self.assertEqual(status, READY_STATUS)

    def test_readiness_no_candidate(self):
        folds = [{"platt_slope": 1.0, "metrics": {}} for _ in range(4)]
        aggregate = {
            "tracks": {
                "RAW": {
                    "aggregate_brier_score": 0.20,
                    "aggregate_log_loss": 0.50,
                    "aggregate_fold_normalized_brier_skill": 0.0,
                },
                "ROLLING_OOF_INTERCEPT": {
                    "aggregate_brier_score": 0.21,
                    "aggregate_log_loss": 0.51,
                    "aggregate_fold_normalized_brier_skill": -0.1,
                    "folds_brier_improved_vs_raw": 1,
                    "folds_logloss_improved_vs_raw": 1,
                    "folds_auc_preserved": 4,
                },
                "ROLLING_OOF_PLATT": {
                    "aggregate_brier_score": 0.22,
                    "aggregate_log_loss": 0.52,
                    "aggregate_fold_normalized_brier_skill": -0.2,
                    "folds_brier_improved_vs_raw": 1,
                    "folds_logloss_improved_vs_raw": 1,
                    "folds_auc_preserved": 4,
                },
            }
        }
        _, selected, status = readiness(folds, aggregate)
        self.assertIsNone(selected)
        self.assertEqual(status, NO_READY_STATUS)

    def test_platt_nonpositive_slope_blocks_readiness(self):
        folds = [
            {"platt_slope": 1.0, "metrics": {}},
            {"platt_slope": 0.5, "metrics": {}},
            {"platt_slope": 0.0, "metrics": {}},
            {"platt_slope": 1.2, "metrics": {}},
        ]
        aggregate = {
            "tracks": {
                "RAW": {
                    "aggregate_brier_score": 0.20,
                    "aggregate_log_loss": 0.50,
                    "aggregate_fold_normalized_brier_skill": 0.0,
                },
                "ROLLING_OOF_INTERCEPT": {
                    "aggregate_brier_score": 0.21,
                    "aggregate_log_loss": 0.51,
                    "aggregate_fold_normalized_brier_skill": -0.1,
                    "folds_brier_improved_vs_raw": 1,
                    "folds_logloss_improved_vs_raw": 1,
                    "folds_auc_preserved": 4,
                },
                "ROLLING_OOF_PLATT": {
                    "aggregate_brier_score": 0.18,
                    "aggregate_log_loss": 0.45,
                    "aggregate_fold_normalized_brier_skill": 0.05,
                    "folds_brier_improved_vs_raw": 4,
                    "folds_logloss_improved_vs_raw": 4,
                    "folds_auc_preserved": 4,
                },
            }
        }
        r, selected, status = readiness(folds, aggregate)
        self.assertFalse(
            r["ROLLING_OOF_PLATT"]["checks"][
                "platt_slope_positive_all_4_folds"
            ]
        )
        self.assertFalse(r["ROLLING_OOF_PLATT"]["ready"])
        self.assertIsNone(selected)
        self.assertEqual(status, NO_READY_STATUS)


if __name__ == "__main__":
    unittest.main()

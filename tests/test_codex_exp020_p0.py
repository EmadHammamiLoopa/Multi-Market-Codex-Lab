import inspect
import unittest
from datetime import date

import numpy as np

from multimarket.codex_exp020_p0 import (
    Config,
    DAYS,
    EXP019_OOS_SHA256,
    EXP019_RESULT_SHA256,
    EXPERIMENT_ID,
    N_PERMUTATIONS,
    OUTER_DAYS,
    STATUS,
    VOL_FEATURE,
    _average_ranks,
    _corr,
    _perm_seed,
    _prior_shift_correct,
    main,
)


class Exp020P0Tests(unittest.TestCase):
    def test_identity_scope_and_status(self):
        c = Config()
        self.assertEqual(EXPERIMENT_ID, "CODEX-EXP-020-P0")
        self.assertEqual(
            STATUS,
            "DIAGNOSTIC_COMPLETE_VOLATILITY_FALSIFICATION_AND_CALIBRATION",
        )
        self.assertEqual(VOL_FEATURE, "rv_30m_bps")
        self.assertEqual(N_PERMUTATIONS, 200)
        self.assertEqual(
            DAYS,
            tuple(date(2026, m, 1) for m in range(1, 8)),
        )
        self.assertEqual(
            OUTER_DAYS,
            tuple(date(2026, m, 1) for m in range(3, 8)),
        )
        self.assertFalse(c.direction_scored)
        self.assertFalse(c.pnl_scored)
        self.assertFalse(c.older_august_holdout_opened)
        self.assertFalse(c.network_accessed)

    def test_parent_hashes_exact(self):
        self.assertEqual(
            EXP019_RESULT_SHA256,
            "a6d55db8e938a0c9b80f3e39117c07fd85e0316d408b159f6bd421ffa7920def",
        )
        self.assertEqual(
            EXP019_OOS_SHA256,
            "3be80f4e869fe1138f9e395fb382d6b854cbcffe20ff70608a47c4bf286c3b23",
        )

    def test_average_ranks_with_ties(self):
        x = np.array([30.0, 10.0, 20.0, 20.0])
        r = _average_ranks(x)
        np.testing.assert_allclose(
            r,
            np.array([4.0, 1.0, 2.5, 2.5]),
        )

    def test_rank_correlation_identical_monotonic_order(self):
        a = np.array([0.1, 0.2, 0.4, 0.9])
        b = np.array([0.01, 0.03, 0.2, 0.8])
        ra = _average_ranks(a)
        rb = _average_ranks(b)
        self.assertAlmostEqual(_corr(ra, rb), 1.0, places=12)

    def test_permutation_seed_deterministic_replicate_specific(self):
        a = _perm_seed(date(2026, 3, 1), 0)
        b = _perm_seed(date(2026, 3, 1), 0)
        c = _perm_seed(date(2026, 3, 1), 1)
        d = _perm_seed(date(2026, 4, 1), 0)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotEqual(a, d)

    def test_prior_shift_identity_when_prevalence_equal(self):
        p = np.array([0.01, 0.2, 0.8])
        q = _prior_shift_correct(p, 0.2, 0.2)
        np.testing.assert_allclose(p, q)

    def test_prior_shift_lower_target_reduces_probabilities(self):
        p = np.array([0.1, 0.3, 0.7])
        q = _prior_shift_correct(p, 0.2, 0.01)
        self.assertTrue(np.all(q < p))
        self.assertTrue(np.all((q > 0) & (q < 1)))

    def test_main_has_no_aug_feature_argument_literal(self):
        source = inspect.getsource(main)
        self.assertNotIn("--aug-feature", source)
        self.assertIn("--feature-dir", source)
        self.assertIn("--output", source)

    def test_config_marks_diagnostic_only_guards(self):
        c = Config()
        self.assertEqual(c.experiment_id, EXPERIMENT_ID)
        self.assertEqual(c.n_test_feature_permutations, 200)
        self.assertEqual(c.seed, 20260827)


if __name__ == "__main__":
    unittest.main()

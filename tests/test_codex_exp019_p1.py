import tempfile
import unittest
from datetime import date
from pathlib import Path

from multimarket.codex_exp018_p1 import Config as Exp018Config
from multimarket.codex_exp019_p1 import (
    AUG_FEATURE_SHA256,
    AUTHORIZED_AUG_PATH,
    CODEX_RESEARCH_PARENT_BLOB_SHA,
    Config,
    EXP017_RESULT_SHA256,
    EXP018_RESULT_SHA256,
    EXPERIMENT_ID,
    FAIL_STATUS,
    PASS_STATUS,
    TRAIN_DAYS,
    VALIDATION_DAY,
    VOL_FEATURE,
    opaque_sha256_exact_authorized_aug,
)


class Exp019P1Tests(unittest.TestCase):
    def test_identity_and_exact_authorized_scope(self):
        self.assertEqual(EXPERIMENT_ID, "CODEX-EXP-019-P1")
        self.assertEqual(VALIDATION_DAY, date(2026, 8, 1))
        self.assertEqual(
            TRAIN_DAYS,
            tuple(date(2026, m, 1) for m in range(1, 8)),
        )
        self.assertEqual(VOL_FEATURE, "rv_30m_bps")
        self.assertEqual(
            AUTHORIZED_AUG_PATH,
            Path(
                "/home/emadh/Multi-Market/evidence/codex/"
                "exp017_aug1_phase_l_derived/BTCUSDT/"
                "2026-08-01_FEATURES250.csv"
            ),
        )

    def test_frozen_lineage_hashes(self):
        self.assertEqual(
            EXP017_RESULT_SHA256,
            "97c76a19a34971c7cef9eb01ad6c5b39d4e2c9885ed39a41054adef397ce4561",
        )
        self.assertEqual(
            EXP018_RESULT_SHA256,
            "4d48612201f5597b5e6b9a0ed423f0fd131bdc31473d11238c96149749748f44",
        )
        self.assertEqual(
            AUG_FEATURE_SHA256,
            "62c72f13f7176d9b4d9bdb69ad940cdcc56858698d64b4a061cecbb4a09ec5f5",
        )
        self.assertEqual(
            CODEX_RESEARCH_PARENT_BLOB_SHA,
            "5c09b8f6f5b1cf35daaccd2d5a99c8ceacc3806f",
        )

    def test_scientific_config_matches_exp018(self):
        old = Exp018Config()
        new = Config()

        shared = (
            "symbol",
            "training_days",
            "validation_day",
            "decision_step_s",
            "entry_delay_ms",
            "horizon_s",
            "label_threshold_bps",
            "primary_feature",
            "r_features",
            "model_c",
            "solver",
            "class_weight",
            "max_iter",
            "seed",
            "auc_min",
            "ap_over_prevalence_min",
            "brier_skill_strictly_positive",
            "top_decile_lift_min",
            "nonoverlap_auc_min",
            "nonoverlap_top_decile_lift_min",
            "timing_placebo_auc_delta_min",
            "canary_auc_delta_min",
            "exp017_result_sha256",
            "aug_feature_sha256",
        )

        for name in shared:
            self.assertEqual(
                getattr(new, name),
                getattr(old, name),
                msg=name,
            )

    def test_status_mapping_unchanged(self):
        self.assertEqual(
            PASS_STATUS,
            "INDEPENDENT_VOLATILITY_REGIME_PREDICTABILITY_CONFIRMED",
        )
        self.assertEqual(
            FAIL_STATUS,
            "FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED",
        )

    def test_non_authorized_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "2026-08-01_FEATURES250.csv"
            p.write_bytes(b"dummy")

            with self.assertRaisesRegex(
                RuntimeError,
                "unauthorized Aug validation path",
            ):
                opaque_sha256_exact_authorized_aug(p)

    def test_no_other_august_date_authorized(self):
        for day in (4, 5, 10, 23):
            p = Path(
                f"/home/emadh/Multi-Market/evidence/codex/"
                f"exp017_aug1_phase_l_derived/BTCUSDT/"
                f"2026-08-{day:02d}_FEATURES250.csv"
            )
            self.assertNotEqual(
                p,
                AUTHORIZED_AUG_PATH,
            )

    def test_exact_scientific_thresholds(self):
        c = Config()
        self.assertEqual(c.auc_min, 0.60)
        self.assertEqual(c.ap_over_prevalence_min, 1.30)
        self.assertEqual(c.top_decile_lift_min, 1.50)
        self.assertEqual(c.nonoverlap_auc_min, 0.57)
        self.assertEqual(c.nonoverlap_top_decile_lift_min, 1.25)
        self.assertEqual(c.timing_placebo_auc_delta_min, 0.03)
        self.assertEqual(c.canary_auc_delta_min, 0.10)


if __name__ == "__main__":
    unittest.main()

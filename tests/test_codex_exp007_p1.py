from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np

from multimarket.codex_exp004_headroom import assert_fresh_output
from multimarket.codex_exp004_p1 import FixedLogistic
from multimarket.codex_exp007_p1 import (
    Config,
    OUTER_DAYS,
    P1DayDataset,
    REQUIRED_DVOL_CANDLES,
    SUPERVISED_DAYS,
    V_FEATURE_NAMES,
    concat_common,
    dvol_feature_vector,
    dvol_required_timestamps_ms,
    permute_complete_v_vectors,
    primary_gates,
    training_days,
)
from multimarket.codex_research import ResearchSealError, assert_unsealed_path, canonical_sha256


class Exp007P1Tests(unittest.TestCase):
    def _day(self, symbol: str = "BTCUSDT", day: date = date(2026, 4, 1)) -> P1DayDataset:
        n = 8
        return P1DayDataset(
            symbol=symbol,
            day=day,
            timestamp_us=np.arange(n, dtype=np.int64) * 60_000_000,
            X_R=np.arange(n * 3, dtype=float).reshape(n, 3),
            X_V=(100 + np.arange(n * len(V_FEATURE_NAMES), dtype=float)).reshape(n, len(V_FEATURE_NAMES)),
            y=np.asarray([0, 1, 0, 1, 0, 1, 0, 1], dtype=np.int8),
            oracle_gross_bps=np.asarray([1, 30, 2, 40, 3, 50, 4, 60], dtype=float),
            valid_common=np.asarray([True, True, False, True, True, True, False, True]),
            nonoverlap_10m=np.asarray([True, False, False, False, False, True, False, False]),
        )

    def test_required_dvol_grid_is_strictly_past_and_31_minutes(self) -> None:
        t_us = 1_800_000_000
        q = dvol_required_timestamps_ms(t_us)
        self.assertEqual(len(q), REQUIRED_DVOL_CANDLES)
        self.assertEqual(q[0], t_us // 1000 - 60_000)
        self.assertEqual(q[-1], t_us // 1000 - 31 * 60_000)
        self.assertTrue(np.all(q < t_us // 1000))

    def test_dvol_feature_vector_uses_exact_31_candles_and_no_fill(self) -> None:
        t_us = 10_000_000_000
        required = dvol_required_timestamps_ms(t_us)
        rows = {}
        # Make close values increase toward decision time so all transforms are finite and deterministic.
        for i, ts in enumerate(required.tolist()):
            close = 100.0 - i * 0.1
            rows[int(ts)] = (close - 0.02, close + 0.05, close - 0.05, close)
        v = dvol_feature_vector(rows, t_us)
        self.assertIsNotNone(v)
        self.assertEqual(len(v), len(V_FEATURE_NAMES))
        self.assertTrue(np.all(np.isfinite(v)))

        broken = dict(rows)
        broken.pop(int(required[7]))
        self.assertIsNone(dvol_feature_vector(broken, t_us))

    def test_common_support_is_identical_for_r_v_and_rv(self) -> None:
        day = self._day()
        xr, yr, mr = concat_common([day], "R")
        xv, yv, mv = concat_common([day], "V")
        xrv, yrv, mrv = concat_common([day], "RV")
        self.assertEqual(len(xr), int(day.valid_common.sum()))
        self.assertEqual(len(xv), len(xr))
        self.assertEqual(len(xrv), len(xr))
        np.testing.assert_array_equal(yr, yv)
        np.testing.assert_array_equal(yr, yrv)
        np.testing.assert_array_equal(mr, mv)
        np.testing.assert_array_equal(mr, mrv)
        np.testing.assert_array_equal(xrv[:, : day.X_R.shape[1]], xr)
        np.testing.assert_array_equal(xrv[:, day.X_R.shape[1] :], xv)

    def test_complete_v_vector_permutation_preserves_rows(self) -> None:
        day = self._day()
        original = day.X_V[day.valid_common]
        permuted = permute_complete_v_vectors(day)
        self.assertEqual(original.shape, permuted.shape)
        self.assertEqual(sorted(map(tuple, original.tolist())), sorted(map(tuple, permuted.tolist())))
        self.assertFalse(np.array_equal(original, permuted))

    def test_permutation_is_deterministic_and_symbol_day_scoped(self) -> None:
        a = self._day("BTCUSDT", date(2026, 4, 1))
        b = self._day("BTCUSDT", date(2026, 5, 1))
        np.testing.assert_array_equal(permute_complete_v_vectors(a), permute_complete_v_vectors(a))
        self.assertFalse(np.array_equal(permute_complete_v_vectors(a), permute_complete_v_vectors(b)))

    def test_outer_folds_are_exactly_april_to_july_and_chronological(self) -> None:
        self.assertEqual(tuple(d.month for d in SUPERVISED_DAYS), (3, 4, 5, 6, 7))
        self.assertEqual(tuple(d.month for d in OUTER_DAYS), (4, 5, 6, 7))
        for outer in OUTER_DAYS:
            train = training_days(outer)
            self.assertTrue(train)
            self.assertTrue(all(day < outer for day in train))
            self.assertNotIn(outer, train)

    def test_scaler_is_fit_on_training_only(self) -> None:
        X_train = np.asarray([[0.0], [1.0], [2.0], [3.0]])
        y_train = np.asarray([0, 0, 1, 1], dtype=np.int8)
        X_outer = np.asarray([[1000.0], [2000.0]])
        model = FixedLogistic().fit(X_train, y_train)
        self.assertAlmostEqual(float(model.scaler.mean_[0]), float(np.mean(X_train[:, 0])))
        self.assertNotAlmostEqual(float(model.scaler.mean_[0]), float(np.mean(np.concatenate((X_train[:, 0], X_outer[:, 0])))))
        self.assertEqual(len(model.predict_proba(X_outer)), len(X_outer))

    def test_configuration_hash_is_deterministic_and_frozen(self) -> None:
        cfg = Config()
        self.assertEqual(cfg.availability_lag_s, 60)
        self.assertEqual(cfg.max_dvol_lookback_min, 30)
        self.assertEqual(cfg.required_dvol_candles, 31)
        self.assertEqual(cfg.v_features, V_FEATURE_NAMES)
        self.assertEqual(canonical_sha256(cfg), canonical_sha256(cfg))

    def test_august_paths_are_rejected(self) -> None:
        with self.assertRaises(ResearchSealError):
            assert_unsealed_path(Path("evidence/codex/exp007/2026-08-01.json"))

    def test_fresh_output_refuses_existing_final_and_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "result.json"
            final.write_text("{}", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                assert_fresh_output(final)
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "result.json"
            partial = final.with_name(final.name + ".part")
            partial.write_text("partial", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                assert_fresh_output(final)

    def test_primary_gates_require_every_preregistered_condition(self) -> None:
        def m(auc, ap, td, ll, brier):
            return {
                "pooled": {
                    "roc_auc": auc,
                    "average_precision": ap,
                    "top_decile_precision": td,
                    "log_loss": ll,
                    "brier_score": brier,
                },
                "by_fold": {d.isoformat(): {"roc_auc": auc} for d in OUTER_DAYS},
                "by_symbol": {
                    "BTCUSDT": {"roc_auc": auc},
                    "ETHUSDT": {"roc_auc": auc},
                },
                "nonoverlap_pooled": {"roc_auc": auc},
            }

        metrics = {
            "R": m(0.60, 0.30, 0.40, 0.65, 0.21),
            "RV": m(0.62, 0.32, 0.41, 0.64, 0.20),
            "RV_V_TIME_PERMUTED": m(0.60, 0.30, 0.40, 0.66, 0.22),
            "CANARY_R": m(0.75, 0.50, 0.60, 0.40, 0.12),
        }
        gates = primary_gates(metrics, {"ok": True})
        self.assertTrue(all(gates.values()))

        metrics["RV"]["pooled"]["brier_score"] = 0.22
        gates = primary_gates(metrics, {"ok": True})
        self.assertFalse(gates["pooled_brier_lower"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np

from multimarket.codex_exp004_headroom import assert_fresh_output
from multimarket.codex_exp004_p1 import FixedLogistic
from multimarket.codex_exp005_p1 import (
    Config,
    D_FEATURE_NAMES,
    MAX_STALENESS_US,
    P1DayDataset,
    SIGNED_D_FEATURES,
    concat_common,
    lag_lookup_times,
    lookup_state,
    permute_complete_d_vectors,
    primary_gates,
    provenance_payload,
    trailing_grid_times,
    training_days,
    _funding_delta_from_previous_distinct,
    _zscore_current,
)
from multimarket.codex_research import ResearchSealError, assert_unsealed_path, canonical_sha256


class Exp005P1Tests(unittest.TestCase):
    def _day(self, symbol: str = "BTCUSDT", day: date = date(2026, 3, 1)) -> P1DayDataset:
        n = 6
        return P1DayDataset(
            symbol=symbol,
            day=day,
            timestamp_us=np.arange(n, dtype=np.int64) * 60_000_000,
            X_R=np.arange(n * 3, dtype=float).reshape(n, 3),
            X_D=(100 + np.arange(n * len(D_FEATURE_NAMES), dtype=float)).reshape(n, len(D_FEATURE_NAMES)),
            y=np.asarray([0, 1, 0, 1, 0, 1], dtype=np.int8),
            oracle_gross_bps=np.asarray([1, 30, 2, 40, 3, 50], dtype=float),
            valid_common=np.asarray([True, True, False, True, True, True]),
            nonoverlap_10m=np.asarray([True, False, False, False, False, True]),
        )

    def test_lookup_never_uses_future_local_timestamp(self) -> None:
        ts = np.asarray([100, 200, 300], dtype=np.int64)
        values = np.asarray([1.0, 2.0, 3.0])
        out, source, valid = lookup_state(ts, values, np.asarray([50, 100, 199, 200, 299]))
        self.assertFalse(valid[0])
        np.testing.assert_array_equal(source[1:], np.asarray([100, 100, 200, 200]))
        query = np.asarray([50, 100, 199, 200, 299])
        self.assertTrue(np.all(source[valid] <= query[valid]))
        self.assertTrue(np.isnan(out[0]))

    def test_staleness_over_30_seconds_is_invalid(self) -> None:
        ts = np.asarray([0], dtype=np.int64)
        values = np.asarray([1.0])
        q = np.asarray([MAX_STALENESS_US, MAX_STALENESS_US + 1], dtype=np.int64)
        _, _, valid = lookup_state(ts, values, q)
        np.testing.assert_array_equal(valid, np.asarray([True, False]))

    def test_lag_lookup_times_are_exactly_past_only(self) -> None:
        t = 10_000_000_000
        q = lag_lookup_times(t)
        np.testing.assert_array_equal(
            q,
            np.asarray([t - 60_000_000, t - 300_000_000, t - 900_000_000, t - 1_800_000_000]),
        )
        self.assertTrue(np.all(q < t))

    def test_trailing_zscore_grid_ends_at_current_time(self) -> None:
        t = 10_000_000_000
        q = trailing_grid_times(t, 5)
        self.assertEqual(q[-1], t)
        self.assertEqual(q[0], t - 5 * 60_000_000)
        self.assertTrue(np.all(q <= t))
        self.assertEqual(len(q), 6)

    def test_zscore_rejects_zero_variance(self) -> None:
        self.assertIsNone(_zscore_current(np.ones(6)))
        z = _zscore_current(np.asarray([1.0, 2.0, 3.0]))
        self.assertIsNotNone(z)

    def test_predicted_funding_is_excluded(self) -> None:
        self.assertNotIn("predicted_funding_rate", D_FEATURE_NAMES)
        self.assertNotIn("predicted_funding_rate", SIGNED_D_FEATURES)

    def test_august_paths_are_rejected(self) -> None:
        with self.assertRaises(ResearchSealError):
            assert_unsealed_path(Path("data/raw/BTCUSDT/2026-08-01.csv.gz"))

    def test_common_support_is_identical_for_r_and_rd(self) -> None:
        day = self._day()
        xr, yr, mr = concat_common([day], "R")
        xrd, yrd, mrd = concat_common([day], "RD")
        self.assertEqual(len(xr), int(day.valid_common.sum()))
        self.assertEqual(len(xrd), len(xr))
        np.testing.assert_array_equal(yr, yrd)
        np.testing.assert_array_equal(mr, mrd)
        np.testing.assert_array_equal(xr, day.X_R[day.valid_common])
        np.testing.assert_array_equal(xrd[:, : day.X_R.shape[1]], xr)

    def test_complete_d_vector_permutation_preserves_rows_not_columns(self) -> None:
        day = self._day()
        original = day.X_D[day.valid_common]
        permuted = permute_complete_d_vectors(day)
        self.assertEqual(original.shape, permuted.shape)
        original_rows = sorted(map(tuple, original.tolist()))
        permuted_rows = sorted(map(tuple, permuted.tolist()))
        self.assertEqual(original_rows, permuted_rows)
        self.assertFalse(np.array_equal(original, permuted))
        self.assertTrue(all(tuple(row) in original_rows for row in permuted.tolist()))

    def test_permutation_is_deterministic_and_symbol_day_scoped(self) -> None:
        a = self._day("BTCUSDT", date(2026, 3, 1))
        b = self._day("BTCUSDT", date(2026, 4, 1))
        np.testing.assert_array_equal(permute_complete_d_vectors(a), permute_complete_d_vectors(a))
        self.assertFalse(np.array_equal(permute_complete_d_vectors(a), permute_complete_d_vectors(b)))

    def test_funding_change_uses_previous_distinct_state(self) -> None:
        values = np.asarray([0.01, 0.01, 0.02, 0.02, 0.015, 0.015])
        out = _funding_delta_from_previous_distinct(values)
        self.assertTrue(np.isnan(out[0]))
        self.assertTrue(np.isnan(out[1]))
        self.assertAlmostEqual(out[2], 0.01)
        self.assertAlmostEqual(out[3], 0.01)
        self.assertAlmostEqual(out[4], -0.005)
        self.assertAlmostEqual(out[5], -0.005)

    def test_outer_folds_are_strictly_chronological(self) -> None:
        for outer in (date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1), date(2026, 6, 1), date(2026, 7, 1)):
            train = training_days(outer)
            self.assertTrue(train)
            self.assertTrue(all(day < outer for day in train))
            self.assertNotIn(outer, train)

    def test_scaler_is_fit_on_training_matrix_only(self) -> None:
        X_train = np.asarray([[0.0], [1.0], [2.0], [3.0]])
        y_train = np.asarray([0, 0, 1, 1], dtype=np.int8)
        X_outer = np.asarray([[1000.0], [2000.0]])
        model = FixedLogistic().fit(X_train, y_train)
        self.assertAlmostEqual(float(model.scaler.mean_[0]), float(np.mean(X_train[:, 0])))
        self.assertNotAlmostEqual(float(model.scaler.mean_[0]), float(np.mean(np.concatenate((X_train[:, 0], X_outer[:, 0])))))
        p = model.predict_proba(X_outer)
        self.assertEqual(len(p), len(X_outer))

    def test_nonoverlap_schedule_is_inherited_from_frozen_exp004_dataset(self) -> None:
        day = self._day()
        self.assertEqual(day.nonoverlap_10m.dtype, np.bool_)
        self.assertEqual(len(day.nonoverlap_10m), len(day.timestamp_us))

    def test_configuration_hash_is_deterministic_and_covers_frozen_rules(self) -> None:
        cfg = Config()
        self.assertEqual(cfg.max_derivatives_staleness_s, 30)
        self.assertEqual(cfg.availability_clock, "local_timestamp only")
        self.assertEqual(cfg.d_features, D_FEATURE_NAMES)
        self.assertEqual(canonical_sha256(cfg), canonical_sha256(cfg))

    def test_provenance_payload_embeds_feature_manifest_and_all_raw_hashes(self) -> None:
        feature_manifest = {"sealed": True, "files": [{"sha256": "feature"}]}
        acquisition = {"file_count": 14, "sealed_august_opened": False}
        raw = {
            (symbol, day): canonical_sha256({"symbol": symbol, "day": day.isoformat()})
            for symbol in ("BTCUSDT", "ETHUSDT")
            for day in tuple(date(2026, month, 1) for month in range(1, 8))
        }
        out = provenance_payload(feature_manifest, acquisition, raw)
        self.assertEqual(out["feature_input_manifest"], feature_manifest)
        self.assertEqual(out["derivatives_acquisition_manifest"], acquisition)
        self.assertEqual(len(out["verified_raw_derivatives_sha256"]), 14)
        self.assertEqual(set(out["verified_raw_derivatives_sha256"].values()), set(raw.values()))

    def test_fresh_output_refuses_existing_final_and_partial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "result.json"
            final.write_text("{}", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                assert_fresh_output(final)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "result.json"
            partial = final.with_name(final.name + ".part")
            partial.write_text("partial", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                assert_fresh_output(final)

    def test_primary_gates_require_all_preregistered_conditions(self) -> None:
        def m(auc, ap, td, ll):
            return {
                "pooled": {
                    "roc_auc": auc,
                    "average_precision": ap,
                    "top_decile_precision": td,
                    "log_loss": ll,
                },
                "by_fold": {
                    d: {"roc_auc": auc}
                    for d in ("2026-03-01", "2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01")
                },
                "by_symbol": {
                    "BTCUSDT": {"roc_auc": auc},
                    "ETHUSDT": {"roc_auc": auc},
                },
                "nonoverlap_pooled": {"roc_auc": auc},
            }

        metrics = {
            "R": m(0.60, 0.30, 0.40, 0.65),
            "RD": m(0.62, 0.32, 0.41, 0.64),
            "RD_D_TIME_PERMUTED": m(0.60, 0.30, 0.40, 0.66),
            "CANARY_R": m(0.75, 0.50, 0.60, 0.40),
        }
        gates = primary_gates(metrics, {"ok": True})
        self.assertTrue(all(gates.values()))
        metrics["RD"]["pooled"]["roc_auc"] = 0.605
        gates = primary_gates(metrics, {"ok": True})
        self.assertFalse(gates["pooled_auc_delta_at_least_0_01"])


if __name__ == "__main__":
    unittest.main()

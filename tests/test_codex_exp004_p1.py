from __future__ import annotations

import unittest
from datetime import datetime, timezone

import numpy as np

from multimarket.codex_exp004_p1 import (
    DAYS,
    DECISION_STEP_ROWS,
    FixedLogistic,
    R_FEATURE_NAMES,
    _final_status,
    _permuted,
    _r_features,
    _spread,
    build_day_dataset,
    gates,
    score,
)
from multimarket.v23_phase0dl_score import BLOCKS, DayData

GRID_US = 250_000


def synthetic_day(rows: int = 15000, day=DAYS[0]) -> DayData:
    start = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1_000_000)
    ts = start + np.arange(rows, dtype=np.int64) * GRID_US
    mid = 100.0 * np.exp(np.arange(rows, dtype=np.float64) * 0.000002)
    bid = mid * (1 - 0.00005)
    ask = mid * (1 + 0.00005)
    valid = np.ones(rows, dtype=bool)
    names = BLOCKS["L2"]
    X2 = np.zeros((rows, len(names)), dtype=np.float32)
    pos = {name: i for i, name in enumerate(names)}
    for name in names:
        X2[:, pos[name]] = np.linspace(-0.2, 0.2, rows, dtype=np.float32)
    return DayData(
        day,
        ts,
        bid,
        ask,
        mid,
        valid,
        {"L0": valid.copy(), "L1": valid.copy(), "L2": valid.copy()},
        {"L0": X2[:, :11], "L1": X2[:, :26], "L2": X2},
    )


class Exp004P1Tests(unittest.TestCase):
    def test_regime_features_are_causal(self) -> None:
        day = synthetic_day()
        current = 9000
        left = _r_features(day, current, _spread(day))
        self.assertIsNotNone(left)
        changed = synthetic_day()
        changed.mid[current + 1 :] *= 3.0
        changed.bid[current + 1 :] *= 3.0
        changed.ask[current + 1 :] *= 3.0
        right = _r_features(changed, current, _spread(changed))
        np.testing.assert_allclose(left, right)

    def test_complete_lookback_is_required(self) -> None:
        day = synthetic_day()
        current = 9000
        day.book_valid[current - 100] = False
        self.assertIsNone(_r_features(day, current, _spread(day)))

    def test_dataset_uses_one_minute_grid_and_ten_minute_nonoverlap(self) -> None:
        dataset = build_day_dataset("BTCUSDT", synthetic_day())
        np.testing.assert_array_equal(
            np.diff(dataset.timestamp_us),
            np.full(len(dataset.timestamp_us) - 1, 60_000_000),
        )
        positions = np.flatnonzero(dataset.nonoverlap_10m)
        self.assertTrue(np.all(np.diff(positions) == 10))

    def test_target_is_exactly_24bp_oracle_threshold(self) -> None:
        dataset = build_day_dataset("BTCUSDT", synthetic_day())
        finite = np.isfinite(dataset.oracle_gross_bps)
        np.testing.assert_array_equal(
            dataset.y[finite],
            (dataset.oracle_gross_bps[finite] >= 24.0).astype(np.int8),
        )

    def test_r_and_rl2_feature_widths_are_frozen(self) -> None:
        dataset = build_day_dataset("BTCUSDT", synthetic_day())
        self.assertEqual(dataset.X_R.shape[1], len(R_FEATURE_NAMES))
        self.assertGreater(dataset.X_RL2.shape[1], dataset.X_R.shape[1])

    def test_fixed_logistic_scaler_is_fit_only_on_supplied_training_rows(self) -> None:
        X = np.asarray([[0.0], [2.0], [4.0], [6.0]])
        y = np.asarray([0, 0, 1, 1])
        model = FixedLogistic().fit(X, y)
        self.assertAlmostEqual(float(model.scaler.mean_[0]), 3.0)
        _ = model.predict_proba(np.asarray([[1000.0]]))
        self.assertAlmostEqual(float(model.scaler.mean_[0]), 3.0)

    def test_time_permutation_is_deterministic_and_preserves_class_count(self) -> None:
        a = build_day_dataset("BTCUSDT", synthetic_day(day=DAYS[0]))
        b = build_day_dataset("BTCUSDT", synthetic_day(day=DAYS[1]))
        left = _permuted([a, b])
        right = _permuted([a, b])
        np.testing.assert_array_equal(left, right)
        original = np.concatenate([a.y[a.valid_R], b.y[b.valid_R]])
        self.assertEqual(int(left.sum()), int(original.sum()))

    def test_probability_metrics_reward_correct_ranking(self) -> None:
        y = np.asarray([0, 0, 0, 0, 1, 1, 1, 1], dtype=np.int8)
        good = score(
            y,
            np.asarray([0.01, 0.05, 0.10, 0.20, 0.80, 0.90, 0.95, 0.99]),
        )
        bad = score(
            y,
            np.asarray([0.99, 0.95, 0.90, 0.80, 0.20, 0.10, 0.05, 0.01]),
        )
        self.assertGreater(good["roc_auc"], bad["roc_auc"])
        self.assertGreater(good["average_precision"], bad["average_precision"])
        self.assertGreater(good["top_decile_lift"], bad["top_decile_lift"])

    def test_primary_gate_requires_all_frozen_conditions(self) -> None:
        pooled = {
            "roc_auc": 0.61,
            "average_precision_over_prevalence": 1.31,
            "brier_skill_score": 0.01,
            "top_decile_lift": 1.51,
        }
        fold_good = {"roc_auc": 0.56, "top_decile_lift": 1.01}
        symbol_good = {"roc_auc": 0.58, "top_decile_lift": 1.26}
        non = {"roc_auc": 0.58, "top_decile_lift": 1.26}
        m = {
            "pooled": pooled,
            "by_fold": {d.isoformat(): dict(fold_good) for d in DAYS[2:]},
            "by_symbol": {
                "BTCUSDT": dict(symbol_good),
                "ETHUSDT": dict(symbol_good),
            },
            "nonoverlap_pooled": non,
        }
        self.assertTrue(all(gates(m).values()))
        m["pooled"]["roc_auc"] = 0.599
        self.assertFalse(gates(m)["pooled_auc_at_least_0_60"])

    def test_final_status_allows_preregistered_rl2_only_when_r_final_fails(self) -> None:
        self.assertEqual(
            _final_status(
                rpass=True,
                r_dpass=False,
                lpass=True,
                ipass=True,
                l_dpass=True,
            ),
            "PREDICTABLE_SANDBOX_RL2_ONLY",
        )
        self.assertEqual(
            _final_status(
                rpass=True,
                r_dpass=True,
                lpass=True,
                ipass=True,
                l_dpass=True,
            ),
            "PREDICTABLE_SANDBOX_R",
        )
        self.assertEqual(
            _final_status(
                rpass=False,
                r_dpass=False,
                lpass=True,
                ipass=False,
                l_dpass=True,
            ),
            "FAIL_OPPORTUNITY_NOT_PREDICTABLE",
        )


if __name__ == "__main__":
    unittest.main()

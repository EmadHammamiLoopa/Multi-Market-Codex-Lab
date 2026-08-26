import math
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace

import numpy as np

from multimarket.codex_exp015_p1 import (
    ATM_LOG_MONEYNESS,
    EXPECTED_STRUCTURAL_SUPPORT,
    EXPERIMENT_ID,
    FLOW_FEATURE_NAMES,
    GRID_END_MINUTE,
    GRID_START_MINUTE,
    MEDIUM_DTE_DAYS,
    NUMERIC_BOUNDARY_ABS_TOL,
    OUTER_DAYS,
    SEGMENTS,
    SEGMENT_METRICS,
    SHORT_DTE_DAYS,
    SUPERVISED_DAYS,
    WINDOW_MINUTES,
    P1DayDataset,
    SegmentedOptionTrade,
    causal_reference,
    classify_maturity,
    classify_moneyness,
    parse_symbol,
    permute_complete_f_vectors,
    segment_name,
    segmented_flow_feature_vector,
    training_days,
)


class Exp015P1Tests(unittest.TestCase):
    def trade(
        self,
        t,
        *,
        segment="atm_short",
        side="buy",
        amount=2.0,
        typ="call",
    ):
        return SegmentedOptionTrade(
            symbol="BTC-27MAR26-100000-C",
            family="standard",
            option_type=typ,
            expiration_us=t + 5 * 86_400_000_000,
            strike=100000.0,
            local_timestamp=t,
            timestamp=t - 100,
            trade_id=f"id-{t}-{segment}-{side}-{amount}",
            side=side,
            amount=amount,
            price=0.1,
            underlying_mid=100000.0,
            segment=segment,
        )

    def test_experiment_identity_and_dates(self):
        self.assertEqual(EXPERIMENT_ID, "CODEX-EXP-015-P1")
        self.assertEqual(
            tuple(d.isoformat() for d in SUPERVISED_DAYS),
            (
                "2026-03-01",
                "2026-04-01",
                "2026-05-01",
                "2026-06-01",
                "2026-07-01",
            ),
        )
        self.assertEqual(
            tuple(d.isoformat() for d in OUTER_DAYS),
            (
                "2026-04-01",
                "2026-05-01",
                "2026-06-01",
                "2026-07-01",
            ),
        )
        self.assertFalse(any(d.month == 8 for d in SUPERVISED_DAYS))

    def test_frozen_representation_dimensions(self):
        self.assertEqual(WINDOW_MINUTES, (1, 5, 15, 30))
        self.assertEqual(len(SEGMENTS), 6)
        self.assertEqual(len(SEGMENT_METRICS), 4)
        self.assertEqual(len(FLOW_FEATURE_NAMES), 96)
        self.assertEqual(GRID_START_MINUTE, 30)
        self.assertEqual(GRID_END_MINUTE, 23 * 60 + 49)

    def test_frozen_structural_support_counts(self):
        self.assertEqual(
            {d.isoformat(): EXPECTED_STRUCTURAL_SUPPORT[d] for d in SUPERVISED_DAYS},
            {
                "2026-03-01": 1269,
                "2026-04-01": 1315,
                "2026-05-01": 1237,
                "2026-06-01": 1259,
                "2026-07-01": 1254,
            },
        )

    def test_standard_and_usdc_expiry_is_0800_utc(self):
        for symbol in (
            "BTC-27MAR26-100000-C",
            "BTC_USDC-27MAR26-100000-P",
        ):
            x = parse_symbol(symbol)
            self.assertIsNotNone(x)
            expiry = datetime.fromtimestamp(
                x["expiration"] / 1_000_000,
                tz=timezone.utc,
            )
            self.assertEqual(
                expiry.isoformat(),
                "2026-03-27T08:00:00+00:00",
            )

    def test_non_btc_or_non_option_rejected(self):
        self.assertIsNone(parse_symbol("ETH-27MAR26-3000-C"))
        self.assertIsNone(parse_symbol("BTC-PERPETUAL"))
        self.assertIsNone(parse_symbol("BTC-27MAR26-100000"))

    def test_moneyness_boundaries(self):
        s = 100.0
        self.assertEqual(ATM_LOG_MONEYNESS, 0.025)
        self.assertEqual(NUMERIC_BOUNDARY_ABS_TOL, 1e-12)

        k_hi = s * math.exp(0.025)
        k_lo = s * math.exp(-0.025)

        self.assertEqual(
            classify_moneyness("call", k_hi, s),
            "atm",
        )
        self.assertEqual(
            classify_moneyness("put", k_lo, s),
            "atm",
        )

        self.assertEqual(
            classify_moneyness(
                "call",
                s * math.exp(0.025 + 1e-9),
                s,
            ),
            "otm_call",
        )
        self.assertEqual(
            classify_moneyness(
                "put",
                s * math.exp(-(0.025 + 1e-9)),
                s,
            ),
            "otm_put",
        )

    def test_maturity_boundaries(self):
        self.assertEqual(SHORT_DTE_DAYS, 7.0)
        self.assertEqual(MEDIUM_DTE_DAYS, 30.0)

        u = 1_000_000_000_000
        day_us = 86_400_000_000

        self.assertEqual(
            classify_maturity(u + 7 * day_us, u),
            "short",
        )
        self.assertEqual(
            classify_maturity(u + 7 * day_us + 1, u),
            "medium",
        )
        self.assertEqual(
            classify_maturity(u + 30 * day_us, u),
            "medium",
        )
        self.assertEqual(
            classify_maturity(u + 30 * day_us + 1, u),
            "longer_than_30d",
        )
        self.assertEqual(
            classify_maturity(u, u),
            "invalid_expired",
        )

    def test_six_segment_mapping(self):
        self.assertEqual(
            segment_name("atm", "short"),
            "atm_short",
        )
        self.assertEqual(
            segment_name("atm", "medium"),
            "atm_medium",
        )
        self.assertEqual(
            segment_name("otm_call", "short"),
            "otm_call_short",
        )
        self.assertEqual(
            segment_name("otm_call", "medium"),
            "otm_call_medium",
        )
        self.assertEqual(
            segment_name("otm_put", "short"),
            "otm_put_short",
        )
        self.assertEqual(
            segment_name("otm_put", "medium"),
            "otm_put_medium",
        )
        self.assertIsNone(
            segment_name("other_moneyness", "short")
        )
        self.assertIsNone(
            segment_name("atm", "longer_than_30d")
        )

    def test_causal_underlying_is_strictly_earlier(self):
        phase = SimpleNamespace(
            ts=np.asarray([1000, 1250, 1500], dtype=np.int64),
            mid=np.asarray([100.0, 101.0, 102.0]),
            book_valid=np.asarray([True, True, True]),
        )
        self.assertEqual(
            causal_reference(phase, 1500),
            101.0,
        )
        self.assertIsNone(
            causal_reference(
                SimpleNamespace(
                    ts=np.asarray([1000], dtype=np.int64),
                    mid=np.asarray([100.0]),
                    book_valid=np.asarray([True]),
                ),
                1000,
            )
        )

    def test_trade_exactly_at_decision_is_not_causal_support(self):
        t = 2_000_000_000_000
        self.assertIsNone(
            segmented_flow_feature_vector(
                [self.trade(t)],
                t,
            )
        )

    def test_one_minute_lower_boundary_is_included(self):
        t = 2_000_000_000_000
        f = segmented_flow_feature_vector(
            [self.trade(t - 60_000_000)],
            t,
        )
        self.assertIsNotNone(f)
        self.assertEqual(len(f), 96)

    def test_no_aggregate_one_minute_flow_means_no_support(self):
        t = 2_000_000_000_000
        self.assertIsNone(
            segmented_flow_feature_vector(
                [self.trade(t - 60_000_001)],
                t,
            )
        )

    def test_empty_segments_are_structural_zero(self):
        t = 2_000_000_000_000
        f = segmented_flow_feature_vector(
            [
                self.trade(
                    t - 30_000_000,
                    segment="atm_short",
                    side="buy",
                    amount=2.0,
                )
            ],
            t,
        )

        self.assertIsNotNone(f)
        self.assertEqual(len(f), 96)

        # First window, first segment = the one trade.
        self.assertAlmostEqual(f[0], math.log1p(1))
        self.assertAlmostEqual(f[1], math.log1p(2.0))
        self.assertEqual(f[2], 1.0)
        self.assertEqual(f[3], 1.0)

        # First window, second segment is absent -> all zeros.
        self.assertTrue(np.array_equal(f[4:8], np.zeros(4)))

    def test_signed_and_absolute_aggressor_by_segment(self):
        t = 2_000_000_000_000
        f = segmented_flow_feature_vector(
            [
                self.trade(
                    t - 20_000_000,
                    segment="atm_short",
                    side="buy",
                    amount=3.0,
                ),
                self.trade(
                    t - 10_000_000,
                    segment="atm_short",
                    side="sell",
                    amount=1.0,
                ),
            ],
            t,
        )
        self.assertIsNotNone(f)
        self.assertAlmostEqual(f[2], 0.5)
        self.assertAlmostEqual(f[3], 0.5)

    def test_feature_order_is_window_segment_metric(self):
        self.assertEqual(
            FLOW_FEATURE_NAMES[0],
            "segoptflow_1m_atm_short_log1p_trade_count",
        )
        self.assertEqual(
            FLOW_FEATURE_NAMES[3],
            "segoptflow_1m_atm_short_abs_aggressor_amount_imbalance",
        )
        self.assertEqual(
            FLOW_FEATURE_NAMES[4],
            "segoptflow_1m_atm_medium_log1p_trade_count",
        )
        self.assertEqual(
            FLOW_FEATURE_NAMES[24],
            "segoptflow_5m_atm_short_log1p_trade_count",
        )
        self.assertEqual(
            FLOW_FEATURE_NAMES[-1],
            "segoptflow_30m_otm_put_medium_abs_aggressor_amount_imbalance",
        )

    def test_training_days_are_expanding_and_chronological(self):
        self.assertEqual(
            training_days(date(2026, 4, 1)),
            (date(2026, 3, 1),),
        )
        self.assertEqual(
            training_days(date(2026, 7, 1)),
            (
                date(2026, 3, 1),
                date(2026, 4, 1),
                date(2026, 5, 1),
                date(2026, 6, 1),
            ),
        )

    def test_permutation_moves_complete_96d_vectors_as_blocks(self):
        n = 8
        X_F = np.arange(n * 96, dtype=float).reshape(n, 96)
        ds = P1DayDataset(
            symbol="BTCUSDT",
            day=date(2026, 5, 1),
            timestamp_us=np.arange(n, dtype=np.int64),
            X_R=np.zeros((n, 2), dtype=float),
            X_F=X_F.copy(),
            y=np.zeros(n, dtype=np.int64),
            oracle_gross_bps=np.zeros(n, dtype=float),
            valid_common=np.ones(n, dtype=bool),
            nonoverlap_10m=np.ones(n, dtype=bool),
        )

        out = permute_complete_f_vectors(ds)
        self.assertEqual(out.shape, (n, 96))

        source_rows = {tuple(row.tolist()) for row in X_F}
        out_rows = {tuple(row.tolist()) for row in out}
        self.assertEqual(source_rows, out_rows)


if __name__ == "__main__":
    unittest.main()

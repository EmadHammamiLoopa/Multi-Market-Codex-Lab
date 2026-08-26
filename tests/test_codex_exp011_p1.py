import unittest
from datetime import date

import numpy as np

from multimarket.codex_exp011_p1 import (
    EXPERIMENT_ID,
    FLOW_FEATURE_NAMES,
    GRID_END_MINUTE,
    GRID_START_MINUTE,
    OUTER_DAYS,
    RAW_SHA256,
    SUPERVISED_DAYS,
    WINDOW_MINUTES,
    OptionTrade,
    flow_feature_vector,
    parse_symbol,
    training_days,
)


class Exp011P1Tests(unittest.TestCase):
    def trade(self, t, *, side="buy", typ="call", amount=2.0):
        return OptionTrade(
            symbol="BTC-27MAR26-100000-C" if typ == "call" else "BTC-27MAR26-100000-P",
            family="standard",
            option_type=typ,
            local_timestamp=t,
            timestamp=t - 100,
            trade_id=f"id-{t}-{side}-{typ}-{amount}",
            side=side,
            amount=amount,
            price=0.1,
        )

    def test_experiment_identity_and_dates(self):
        self.assertEqual(EXPERIMENT_ID, "CODEX-EXP-011-P1")
        self.assertEqual(
            tuple(d.isoformat() for d in SUPERVISED_DAYS),
            ("2026-03-01", "2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01"),
        )
        self.assertEqual(
            tuple(d.isoformat() for d in OUTER_DAYS),
            ("2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01"),
        )
        self.assertFalse(any(d.month == 8 for d in SUPERVISED_DAYS))

    def test_frozen_windows_grid_and_feature_count(self):
        self.assertEqual(WINDOW_MINUTES, (1, 5, 15, 30))
        self.assertEqual(GRID_START_MINUTE, 30)
        self.assertEqual(GRID_END_MINUTE, 23 * 60 + 49)
        self.assertEqual(len(FLOW_FEATURE_NAMES), 24)
        self.assertEqual(len(RAW_SHA256), 5)

    def test_standard_btc_symbol(self):
        x = parse_symbol("BTC-27MAR26-100000-C")
        self.assertIsNotNone(x)
        self.assertEqual(x["currency"], "BTC")
        self.assertEqual(x["family"], "standard")
        self.assertEqual(x["option_type"], "call")

    def test_usdc_btc_symbol(self):
        x = parse_symbol("BTC_USDC-27MAR26-100000-P")
        self.assertIsNotNone(x)
        self.assertEqual(x["currency"], "BTC")
        self.assertEqual(x["family"], "usdc_linear")
        self.assertEqual(x["option_type"], "put")

    def test_non_vanilla_or_non_option_symbol_rejected(self):
        self.assertIsNone(parse_symbol("BTC-PERPETUAL"))
        self.assertIsNone(parse_symbol("BTC_USDC-PERPETUAL"))

    def test_trade_exactly_at_t_is_not_causal(self):
        t = 2_000_000_000_000
        self.assertIsNone(flow_feature_vector([self.trade(t)], t))

    def test_trade_inside_one_minute_supports_all_nested_windows(self):
        t = 2_000_000_000_000
        f = flow_feature_vector([self.trade(t - 30_000_000)], t)
        self.assertIsNotNone(f)
        self.assertEqual(f.shape, (24,))
        self.assertTrue(np.all(np.isfinite(f)))

    def test_trade_at_lower_one_minute_boundary_is_included(self):
        t = 2_000_000_000_000
        f = flow_feature_vector([self.trade(t - 60_000_000)], t)
        self.assertIsNotNone(f)

    def test_only_older_trade_fails_one_minute_support(self):
        t = 2_000_000_000_000
        self.assertIsNone(flow_feature_vector([self.trade(t - 120_000_000)], t))

    def test_signed_and_absolute_aggressor_imbalance(self):
        t = 2_000_000_000_000
        trades = [
            self.trade(t - 10_000_000, side="buy", amount=3.0),
            self.trade(t - 20_000_000, side="sell", amount=1.0),
        ]
        f = flow_feature_vector(trades, t)
        self.assertIsNotNone(f)
        # First window features: logN, logA, signed aggressor, abs aggressor, call/put, abs call/put.
        self.assertAlmostEqual(float(f[2]), 0.5)
        self.assertAlmostEqual(float(f[3]), 0.5)

    def test_call_put_imbalance(self):
        t = 2_000_000_000_000
        trades = [
            self.trade(t - 10_000_000, typ="call", amount=3.0),
            self.trade(t - 20_000_000, typ="put", amount=1.0),
        ]
        f = flow_feature_vector(trades, t)
        self.assertIsNotNone(f)
        self.assertAlmostEqual(float(f[4]), 0.5)
        self.assertAlmostEqual(float(f[5]), 0.5)

    def test_expanding_training_days(self):
        self.assertEqual(training_days(date(2026, 4, 1)), (date(2026, 3, 1),))
        self.assertEqual(
            training_days(date(2026, 7, 1)),
            (date(2026, 3, 1), date(2026, 4, 1), date(2026, 5, 1), date(2026, 6, 1)),
        )


if __name__ == "__main__":
    unittest.main()

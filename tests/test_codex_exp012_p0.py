import math
import unittest
from types import SimpleNamespace

import numpy as np

from scripts.codex_exp012_p0_segmented_options_flow_readiness import (
    ATM_LOG_MONEYNESS,
    DATES,
    GRID_COUNT,
    GRID_END_MINUTE,
    GRID_START_MINUTE,
    MEDIUM_DTE_DAYS,
    NUMERIC_BOUNDARY_ABS_TOL,
    SEGMENTS,
    SHORT_DTE_DAYS,
    WINDOW_MINUTES,
    causal_reference,
    classify_maturity,
    classify_moneyness,
    parse_symbol,
    segment_name,
)


class Exp012P0Tests(unittest.TestCase):
    def test_frozen_scope(self):
        self.assertEqual(tuple(d.isoformat() for d in DATES), (
            "2026-03-01", "2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01"
        ))
        self.assertFalse(any(d.month == 8 for d in DATES))
        self.assertEqual(WINDOW_MINUTES, (1, 5, 15, 30))
        self.assertEqual(GRID_START_MINUTE, 30)
        self.assertEqual(GRID_END_MINUTE, 23 * 60 + 49)
        self.assertEqual(GRID_COUNT, 1400)

    def test_frozen_boundaries(self):
        self.assertEqual(ATM_LOG_MONEYNESS, 0.025)
        self.assertEqual(NUMERIC_BOUNDARY_ABS_TOL, 1e-12)
        self.assertEqual(SHORT_DTE_DAYS, 7.0)
        self.assertEqual(MEDIUM_DTE_DAYS, 30.0)
        self.assertEqual(len(SEGMENTS), 6)

    def test_standard_and_usdc_symbols(self):
        a = parse_symbol("BTC-27MAR26-100000-C")
        b = parse_symbol("BTC_USDC-27MAR26-100000-P")
        self.assertEqual(a[0], "standard")
        self.assertEqual(a[3], "call")
        self.assertEqual(b[0], "usdc_linear")
        self.assertEqual(b[3], "put")

    def test_non_btc_or_non_option_rejected(self):
        self.assertIsNone(parse_symbol("ETH-27MAR26-3000-C"))
        self.assertIsNone(parse_symbol("BTC-PERPETUAL"))
        self.assertIsNone(parse_symbol("BTC-27MAR26-100000"))

    def test_atm_boundary_inclusive(self):
        s = 100.0
        k_hi = s * math.exp(0.025)
        k_lo = s * math.exp(-0.025)
        self.assertEqual(classify_moneyness("call", k_hi, s), "atm")
        self.assertEqual(classify_moneyness("put", k_lo, s), "atm")

    def test_just_outside_atm_boundary_remains_otm(self):
        s = 100.0
        k_call = s * math.exp(0.025 + 1e-9)
        k_put = s * math.exp(-(0.025 + 1e-9))
        self.assertEqual(classify_moneyness("call", k_call, s), "otm_call")
        self.assertEqual(classify_moneyness("put", k_put, s), "otm_put")

    def test_otm_and_itm_classification(self):
        s = 100.0
        self.assertEqual(classify_moneyness("call", 110.0, s), "otm_call")
        self.assertEqual(classify_moneyness("put", 90.0, s), "otm_put")
        self.assertEqual(classify_moneyness("call", 90.0, s), "other_moneyness")
        self.assertEqual(classify_moneyness("put", 110.0, s), "other_moneyness")

    def test_maturity_boundaries(self):
        u = 1_000_000_000_000
        day_us = 86_400_000_000
        self.assertEqual(classify_maturity(u + 7 * day_us, u), "short")
        self.assertEqual(classify_maturity(u + 7 * day_us + 1, u), "medium")
        self.assertEqual(classify_maturity(u + 30 * day_us, u), "medium")
        self.assertEqual(classify_maturity(u + 30 * day_us + 1, u), "longer_than_30d")
        self.assertEqual(classify_maturity(u, u), "invalid_expired")

    def test_six_segment_mapping(self):
        self.assertEqual(segment_name("atm", "short"), "atm_short")
        self.assertEqual(segment_name("atm", "medium"), "atm_medium")
        self.assertEqual(segment_name("otm_call", "short"), "otm_call_short")
        self.assertEqual(segment_name("otm_call", "medium"), "otm_call_medium")
        self.assertEqual(segment_name("otm_put", "short"), "otm_put_short")
        self.assertEqual(segment_name("otm_put", "medium"), "otm_put_medium")
        self.assertIsNone(segment_name("other_moneyness", "short"))
        self.assertIsNone(segment_name("atm", "longer_than_30d"))

    def test_causal_reference_uses_strictly_earlier_row(self):
        phase = SimpleNamespace(
            ts=np.asarray([1000, 1250, 1500], dtype=np.int64),
            mid=np.asarray([100.0, 101.0, 102.0]),
            book_valid=np.asarray([True, True, True]),
        )
        mid, age = causal_reference(phase, 1500)
        self.assertEqual(mid, 101.0)
        self.assertEqual(age, 0.25)

    def test_causal_reference_rejects_missing_prior_row(self):
        phase = SimpleNamespace(
            ts=np.asarray([1000], dtype=np.int64),
            mid=np.asarray([100.0]),
            book_valid=np.asarray([True]),
        )
        self.assertIsNone(causal_reference(phase, 1000))

    def test_causal_reference_requires_valid_book(self):
        phase = SimpleNamespace(
            ts=np.asarray([1000, 1250], dtype=np.int64),
            mid=np.asarray([100.0, 101.0]),
            book_valid=np.asarray([False, True]),
        )
        self.assertIsNone(causal_reference(phase, 1100))


if __name__ == "__main__":
    unittest.main()

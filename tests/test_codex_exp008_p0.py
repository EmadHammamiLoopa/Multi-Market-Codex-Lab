import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "codex_exp008_p0_options_surface_audit_final.py"
SPEC = importlib.util.spec_from_file_location("exp008_final", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load EXP008 final runner")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def row(symbol, typ, strike, exp, t, *, iv=0.60, delta=0.25, oi=10.0, under=100.0):
    return {
        "currency": "BTC" if symbol.startswith("BTC") else "ETH",
        "symbol": symbol,
        "timestamp": t - 1,
        "local_timestamp": t,
        "type": typ,
        "strike": float(strike),
        "expiration": int(exp),
        "open_interest": oi,
        "mark_iv": iv,
        "underlying_price": under,
        "delta": delta,
    }


class Exp008P0Tests(unittest.TestCase):
    def test_frozen_dates_exclude_august(self):
        self.assertEqual(mod.DATES, (
            "2026-03-01",
            "2026-04-01",
            "2026-05-01",
            "2026-06-01",
            "2026-07-01",
        ))
        self.assertFalse(any(d.startswith("2026-08") for d in mod.DATES))

    def test_grid_is_exactly_1400_minutes(self):
        g = mod.grid_times("2026-03-01")
        self.assertEqual(len(g), 1400)
        self.assertEqual(g[1] - g[0], 60_000_000)

    def test_support_threshold_is_frozen_80_percent(self):
        self.assertEqual(mod.GRID_COUNT, 1400)
        self.assertEqual(mod.MIN_SUPPORT, 1120)
        self.assertEqual(mod.MIN_RUN, 120)

    def test_source_url_never_points_to_august_for_frozen_dates(self):
        for d in mod.DATES:
            url = mod.source_url(d)
            self.assertIn("deribit/options_chain", url)
            self.assertTrue(url.endswith("/OPTIONS.csv.gz"))
            self.assertNotIn("/08/", url)

    def test_currency_classification_is_own_underlying_only(self):
        self.assertEqual(mod.classify_currency("BTC-27MAR26-100000-C"), "BTC")
        self.assertEqual(mod.classify_currency("ETH-27MAR26-4000-P"), "ETH")
        self.assertIsNone(mod.classify_currency("SOL-27MAR26-100-C"))

    def test_expiry_anchor_tie_chooses_earlier(self):
        t = 1_000_000_000_000
        day = 86_400_000_000
        e6 = t + 6 * day
        e8 = t + 8 * day
        self.assertEqual(mod.choose_expiry({e6: [], e8: []}, t, 7, 5, 9), e6)

    def test_strict_causality_excludes_row_at_decision_time(self):
        t = 2_000_000_000_000
        day = 86_400_000_000
        e7 = t + 7 * day
        e30 = t + 30 * day
        state = {"BTC": {}, "ETH": {}}
        for exp, suffix in ((e7, "7"), (e30, "30")):
            state["BTC"][f"BTC-{suffix}-ATM-C"] = row(f"BTC-{suffix}-ATM-C", "call", 100, exp, t, iv=.60, delta=.50)
            state["BTC"][f"BTC-{suffix}-ATM-P"] = row(f"BTC-{suffix}-ATM-P", "put", 100, exp, t, iv=.62, delta=-.50)
            state["BTC"][f"BTC-{suffix}-25C"] = row(f"BTC-{suffix}-25C", "call", 120, exp, t, iv=.65, delta=.25)
            state["BTC"][f"BTC-{suffix}-25P"] = row(f"BTC-{suffix}-25P", "put", 80, exp, t, iv=.70, delta=-.25)
        s = mod.surface_at(state, "BTC", t)
        self.assertFalse(s["anchors"])
        self.assertFalse(s["all"])

    def test_300_second_staleness_boundary_is_inclusive(self):
        t = 2_000_000_000_000
        day = 86_400_000_000
        e7 = t + 7 * day
        e30 = t + 30 * day
        state = {"BTC": {}, "ETH": {}}
        seen = t - mod.STALE_US
        for exp, suffix in ((e7, "7"), (e30, "30")):
            state["BTC"][f"BTC-{suffix}-ATM-C"] = row(f"BTC-{suffix}-ATM-C", "call", 100, exp, seen, iv=.60, delta=.50)
            state["BTC"][f"BTC-{suffix}-ATM-P"] = row(f"BTC-{suffix}-ATM-P", "put", 100, exp, seen, iv=.62, delta=-.50)
            state["BTC"][f"BTC-{suffix}-25C"] = row(f"BTC-{suffix}-25C", "call", 120, exp, seen, iv=.65, delta=.25)
            state["BTC"][f"BTC-{suffix}-25P"] = row(f"BTC-{suffix}-25P", "put", 80, exp, seen, iv=.70, delta=-.25)
        s = mod.surface_at(state, "BTC", t)
        self.assertTrue(s["anchors"])
        self.assertTrue(s["atm"])
        self.assertTrue(s["delta"])
        self.assertTrue(s["oi"])
        self.assertTrue(s["all"])

    def test_decomposed_support_does_not_hide_delta_failure(self):
        t = 2_000_000_000_000
        day = 86_400_000_000
        e7 = t + 7 * day
        e30 = t + 30 * day
        state = {"BTC": {}, "ETH": {}}
        seen = t - 1_000_000
        for exp, suffix in ((e7, "7"), (e30, "30")):
            state["BTC"][f"BTC-{suffix}-ATM-C"] = row(f"BTC-{suffix}-ATM-C", "call", 100, exp, seen, iv=.60, delta=.50)
            state["BTC"][f"BTC-{suffix}-ATM-P"] = row(f"BTC-{suffix}-ATM-P", "put", 100, exp, seen, iv=.62, delta=-.50)
            state["BTC"][f"BTC-{suffix}-25C"] = row(f"BTC-{suffix}-25C", "call", 120, exp, seen, iv=.65, delta=.40)
            state["BTC"][f"BTC-{suffix}-25P"] = row(f"BTC-{suffix}-25P", "put", 80, exp, seen, iv=.70, delta=-.40)
        s = mod.surface_at(state, "BTC", t)
        self.assertTrue(s["anchors"])
        self.assertTrue(s["atm"])
        self.assertFalse(s["delta"])
        self.assertTrue(s["oi"])
        self.assertFalse(s["all"])

    def test_atm_does_not_fall_through_to_second_best_strike(self):
        t = 2_000_000_000_000
        day = 86_400_000_000
        e7 = t + 7 * day
        e30 = t + 30 * day
        state = {"BTC": {}, "ETH": {}}
        seen = t - 1_000_000
        for exp, suffix in ((e7, "7"), (e30, "30")):
            state["BTC"][f"BTC-{suffix}-ATM-C"] = row(f"BTC-{suffix}-ATM-C", "call", 100, exp, seen, iv=.60, delta=.50)
            # Missing put exactly at 100. A complete pair exists at 105 but must not rescue ATM.
            state["BTC"][f"BTC-{suffix}-105C"] = row(f"BTC-{suffix}-105C", "call", 105, exp, seen, iv=.61, delta=.45)
            state["BTC"][f"BTC-{suffix}-105P"] = row(f"BTC-{suffix}-105P", "put", 105, exp, seen, iv=.63, delta=-.45)
            state["BTC"][f"BTC-{suffix}-25C"] = row(f"BTC-{suffix}-25C", "call", 120, exp, seen, iv=.65, delta=.25)
            state["BTC"][f"BTC-{suffix}-25P"] = row(f"BTC-{suffix}-25P", "put", 80, exp, seen, iv=.70, delta=-.25)
        s = mod.surface_at(state, "BTC", t)
        self.assertTrue(s["anchors"])
        self.assertFalse(s["atm"])
        self.assertFalse(s["all"])


if __name__ == "__main__":
    unittest.main()

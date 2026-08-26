import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "codex_exp009_p0_options_trade_flow.py"
SPEC = importlib.util.spec_from_file_location("exp009", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load EXP009 runner")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class Exp009P0Tests(unittest.TestCase):
    def test_frozen_dates_exclude_august(self):
        self.assertEqual(
            mod.DATES,
            (
                "2026-03-01",
                "2026-04-01",
                "2026-05-01",
                "2026-06-01",
                "2026-07-01",
            ),
        )
        self.assertFalse(any(d.startswith("2026-08") for d in mod.DATES))

    def test_grid_is_1400_minutes(self):
        grid = mod.grid_times("2026-03-01")
        self.assertEqual(len(grid), 1400)
        self.assertEqual(grid[1] - grid[0], 60_000_000)

    def test_support_gates_are_frozen(self):
        self.assertEqual(mod.MIN_SUPPORT, 1120)
        self.assertEqual(mod.MIN_RUN, 120)
        self.assertEqual(mod.WINDOW_MINUTES, (1, 5, 15, 30))

    def test_source_url_is_trades_options_and_not_august(self):
        for day in mod.DATES:
            url = mod.source_url(day)
            self.assertIn("/deribit/trades/", url)
            self.assertTrue(url.endswith("/OPTIONS.csv.gz"))
            self.assertNotIn("/08/", url)

    def test_symbol_parser(self):
        btc = mod.parse_symbol("BTC-27MAR26-100000-C")
        eth = mod.parse_symbol("ETH-27MAR26-4000-P")
        self.assertEqual(btc["currency"], "BTC")
        self.assertEqual(btc["type"], "call")
        self.assertEqual(eth["currency"], "ETH")
        self.assertEqual(eth["type"], "put")
        self.assertIsNone(mod.parse_symbol("SOL-27MAR26-100-C"))

    def test_trade_at_t_is_not_causal(self):
        t = 2_000_000_000_000
        trade = {
            "local_timestamp": t,
            "side": "buy",
            "type": "call",
            "amount": 1.0,
        }
        s = mod.flow_support([trade], t)
        self.assertFalse(s[1]["complete"])
        self.assertFalse(s[30]["complete"])

    def test_trade_at_1m_boundary_is_included(self):
        t = 2_000_000_000_000
        trade = {
            "local_timestamp": t - 60_000_000,
            "side": "buy",
            "type": "call",
            "amount": 1.0,
        }
        s = mod.flow_support([trade], t)
        self.assertTrue(s[1]["complete"])
        self.assertTrue(s[5]["complete"])
        self.assertTrue(s[15]["complete"])
        self.assertTrue(s[30]["complete"])

    def test_older_than_1m_but_inside_5m(self):
        t = 2_000_000_000_000
        trade = {
            "local_timestamp": t - 120_000_000,
            "side": "sell",
            "type": "put",
            "amount": 2.0,
        }
        s = mod.flow_support([trade], t)
        self.assertFalse(s[1]["complete"])
        self.assertTrue(s[5]["complete"])
        self.assertTrue(s[15]["complete"])
        self.assertTrue(s[30]["complete"])

    def test_parse_trade_rejects_bad_side(self):
        raw = {
            "symbol": "BTC-27MAR26-100000-C",
            "timestamp": "1",
            "local_timestamp": "2",
            "id": "abc",
            "side": "unknown",
            "price": "1.5",
            "amount": "2",
        }
        with self.assertRaises(ValueError):
            mod.parse_trade(raw)

    def test_parse_trade_rejects_nonpositive_amount(self):
        raw = {
            "symbol": "BTC-27MAR26-100000-C",
            "timestamp": "1",
            "local_timestamp": "2",
            "id": "abc",
            "side": "buy",
            "price": "1.5",
            "amount": "0",
        }
        with self.assertRaises(ValueError):
            mod.parse_trade(raw)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "codex_exp010_p0_unified_options_trade_flow.py"
SPEC = importlib.util.spec_from_file_location("exp010", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class Exp010P0Tests(unittest.TestCase):
    def test_standard_symbol(self):
        x = mod.parse_symbol("BTC-27MAR26-100000-C")
        self.assertEqual(x["currency"], "BTC")
        self.assertEqual(x["family"], "standard")
        self.assertEqual(x["type"], "call")

    def test_usdc_symbols(self):
        b = mod.parse_symbol("BTC_USDC-6MAR26-63000-P")
        e = mod.parse_symbol("ETH_USDC-27MAR26-1400-P")
        self.assertEqual(b["currency"], "BTC")
        self.assertEqual(b["family"], "usdc_linear")
        self.assertEqual(e["currency"], "ETH")
        self.assertEqual(e["family"], "usdc_linear")

    def test_other_underlying_rejected(self):
        self.assertIsNone(mod.parse_symbol("SOL_USDC-27MAR26-100-P"))

    def test_grid_and_gates_frozen(self):
        self.assertEqual(len(mod.grid_times("2026-03-01")), 1400)
        self.assertEqual(mod.WINDOW_MINUTES, (1, 5, 15, 30))
        self.assertEqual(mod.MIN_SUPPORT, 1120)
        self.assertEqual(mod.MIN_RUN, 120)

    def test_august_absent(self):
        self.assertFalse(any(d.startswith("2026-08") for d in mod.DATES))


if __name__ == "__main__":
    unittest.main()

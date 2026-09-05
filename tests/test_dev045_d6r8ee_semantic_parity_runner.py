from __future__ import annotations

import csv
import gzip
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np

from multimarket import dev045_d6r8ee_semantic_parity_runner as r


TRADE_HEADER = ("exchange", "symbol", "timestamp", "local_timestamp", "id", "side", "price", "amount")
DEPTH_HEADER = ("exchange", "symbol", "timestamp", "local_timestamp", "is_snapshot", "side", "price", "amount")


def _write(path: Path, header: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


class TestD6R8EESemanticParityRunner(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path]:
        trades = root / "trades.csv.gz"
        depth = root / "depth.csv.gz"
        _write(
            trades,
            TRADE_HEADER,
            (
                ("binance-futures", "BTCUSDT", "1000", "1000", "1", "buy", "100.0", "0.1"),
                ("binance-futures", "BTCUSDT", "1100", "1200", "2", "sell", "100.1", "0.2"),
            ),
        )
        _write(
            depth,
            DEPTH_HEADER,
            (
                ("binance-futures", "BTCUSDT", "900", "900", "true", "bid", "99.9", "1.0"),
                ("binance-futures", "BTCUSDT", "900", "900", "true", "ask", "100.1", "1.0"),
                ("binance-futures", "BTCUSDT", "1200", "1300", "false", "bid", "99.8", "2.0"),
                ("binance-futures", "BTCUSDT", "1300", "1400", "false", "ask", "100.2", "2.0"),
            ),
        )
        return trades, depth

    def test_actual_three_way_synthetic_parity(self) -> None:
        if importlib.util.find_spec("hftbacktest") is None:
            self.skipTest("hftbacktest not installed in generic environment")
        with tempfile.TemporaryDirectory() as td:
            trades, depth = self._fixture(Path(td))
            result = r.synthetic_self_test(trades, depth)
            self.assertGreater(result.rows, 0)
            self.assertEqual(result.dtype_itemsize, 64)
            self.assertTrue(result.upstream_old_equal)
            self.assertTrue(result.upstream_v2_equal)
            self.assertTrue(result.old_v2_equal)

    def test_semantic_identity_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            trades, _ = self._fixture(Path(td))
            actual = r.inspect_semantic_identity(trades, 3)
            wrong = r.SemanticIdentity(actual.rows + 1, actual.decompressed_bytes, actual.decompressed_sha256, actual.first_local_timestamp_us, actual.last_local_timestamp_us)
            with self.assertRaisesRegex(r.D6R8EEError, "semantic_identity"):
                r.assert_expected_semantic_identity(actual, wrong)

    def test_exact_nan_equal_and_mismatch(self) -> None:
        dtype = np.dtype([("ev", "<u8"), ("px", "<f8")], align=True)
        a = np.zeros(2, dtype=dtype)
        b = np.zeros(2, dtype=dtype)
        a[0]["px"] = np.nan
        b[0]["px"] = np.nan
        self.assertTrue(r._fieldwise_exact_nan_equal(a, b))
        b[1]["px"] = 1.0
        self.assertFalse(r._fieldwise_exact_nan_equal(a, b))

    def test_real_successor_is_closed(self) -> None:
        self.assertFalse(r.REAL_SUCCESSOR_EXECUTION_AUTHORIZED)
        with self.assertRaisesRegex(r.D6R8EEError, "real_successor_execution_closed"):
            r.run_real_successor()

    def test_module_has_no_real_raw_binding(self) -> None:
        source = Path(r.__file__).read_text(encoding="utf-8")
        self.assertNotIn("/home/emadh/Multi-Market/data", source)
        self.assertNotIn("ATTEMPT_STARTED", source)
        self.assertNotIn("dev045_d6r8eb", source)


if __name__ == "__main__":
    unittest.main()

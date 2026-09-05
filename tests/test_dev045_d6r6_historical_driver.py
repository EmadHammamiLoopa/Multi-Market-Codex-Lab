from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import tempfile
import unittest

import numpy as np

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r5_memmap_contract as m5
from multimarket import dev045_d6r6_historical_driver as d


ROOT = Path(__file__).resolve().parents[1]
IMPL_PATH = (
    ROOT
    / "src"
    / "multimarket"
    / "dev045_d6r6_historical_driver.py"
)


def _hft_available() -> bool:
    try:
        import hftbacktest  # noqa: F401
    except ImportError:
        return False
    return True


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            digest.update(block)

    return digest.hexdigest()


def _write_synthetic_npy(path: Path) -> None:
    import hftbacktest as h

    dtype = np.dtype(list(m5.EVENT_DTYPE_DESCR))

    data = np.lib.format.open_memmap(
        path,
        mode="w+",
        dtype=dtype,
        shape=(4,),
    )

    try:
        data[:] = np.zeros(4, dtype=dtype)

        def ev(base: int, side: int) -> int:
            return int(
                base
                | h.EXCH_EVENT
                | h.LOCAL_EVENT
                | side
            )

        rows = (
            (
                ev(h.DEPTH_EVENT, h.BUY_EVENT),
                1_000_000_000,
                1_010_000_000,
                100.0,
                10.0,
            ),
            (
                ev(h.DEPTH_EVENT, h.SELL_EVENT),
                1_100_000_000,
                1_110_000_000,
                100.1,
                8.0,
            ),
            (
                ev(h.TRADE_EVENT, h.SELL_EVENT),
                2_000_000_000,
                2_010_000_000,
                100.0,
                0.010,
            ),
            (
                ev(h.DEPTH_EVENT, h.SELL_EVENT),
                3_000_000_000,
                3_010_000_000,
                100.1,
                7.5,
            ),
        )

        for i, (flag, exch, local, px, qty) in enumerate(rows):
            data[i]["ev"] = flag
            data[i]["exch_ts"] = exch
            data[i]["local_ts"] = local
            data[i]["px"] = px
            data[i]["qty"] = qty

        data.flush()

    finally:
        mmap = getattr(data, "_mmap", None)
        if mmap is not None:
            mmap.close()


class TestD6R6HistoricalDriver(unittest.TestCase):
    def test_execution_surfaces_are_closed(self):
        self.assertIs(d.CANONICAL_JAN_OPEN_ENABLED, False)
        self.assertIs(
            d.CANONICAL_JAN_HFTBACKTEST_INGESTION_ENABLED,
            False,
        )
        self.assertIs(
            d.HISTORICAL_POLICY_REPLAY_ENABLED,
            False,
        )
        self.assertIs(d.HISTORICAL_PNL_ENABLED, False)
        self.assertIs(
            d.ECONOMIC_ARENA_EXECUTION_ENABLED,
            False,
        )
        self.assertIs(d.CANONICAL_PNL_WRITE_ENABLED, False)
        self.assertIs(d.NETWORK_ACQUISITION_ENABLED, False)
        self.assertIs(d.LIVE_TRADING_AUTHORIZED, False)
        self.assertIs(d.SYNTHETIC_MEMMAP_ONLY, True)

    def test_driver_has_no_canonical_open_or_policy_dependency(self):
        text = IMPL_PATH.read_text(encoding="utf-8")

        self.assertNotIn("open_canonical_jan", text)
        self.assertNotIn(
            "/home/emadh/Multi-Market/runtime/",
            text,
        )
        self.assertNotIn("dev045_m3_policy", text)
        self.assertNotIn("policy_decision", text)
        self.assertNotIn("maintenance_intent", text)
        self.assertNotIn("dev045_m6_economic_arena", text)

        tree = ast.parse(text)

        imported = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(
                    alias.name for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")

        self.assertFalse(
            any("requests" in name for name in imported)
        )
        self.assertFalse(
            any("urllib" in name for name in imported)
        )
        self.assertFalse(
            any("railway" in name.lower() for name in imported)
        )

    def test_invalid_source_fails_closed_before_hft(self):
        with self.assertRaises(
            d.HistoricalMemmapBindingError
        ):
            d._build_lifetime_safe_binding(object())

    @unittest.skipUnless(
        _hft_available(),
        "patched hftbacktest not installed in generic environment",
    )
    def test_synthetic_memmap_ingestion_and_lifetime_order(self):
        import hftbacktest as h

        self.assertEqual(h.__version__, "2.4.4")

        with tempfile.TemporaryDirectory(
            prefix="dev045_d6r6b_"
        ) as td:
            path = Path(td) / "synthetic_events.npy"

            _write_synthetic_npy(path)

            expected_sha = _sha256(path)
            expected_bytes = path.stat().st_size

            source = adapter._open_verified_file(
                path,
                expected_sha256=expected_sha,
                expected_bytes=expected_bytes,
                expected_rows=4,
            )

            mmap_ref = source.data

            self.assertIsInstance(
                source.data,
                np.memmap,
            )
            self.assertFalse(source.data.flags.writeable)
            self.assertEqual(source.data.mode, "r")
            self.assertEqual(
                source.data.dtype,
                h.event_dtype,
            )
            self.assertFalse(source._closed)

            binding = d._build_lifetime_safe_binding(
                source
            )

            self.assertEqual(
                binding.lifecycle,
                [
                    "memmap_opened_verified",
                    "asset_registered",
                    "backtest_built",
                ],
            )

            self.assertFalse(source._closed)
            self.assertFalse(mmap_ref._mmap.closed)

            wakeups = []
            guard = 0

            while True:
                guard += 1

                if guard > 16:
                    self.fail("feed_wakeup_guard")

                rc = int(
                    binding.bt.wait_next_feed(
                        False,
                        10_000_000_000,
                    )
                )

                if rc == 1:
                    break

                self.assertEqual(rc, 2)

                wakeups.append(
                    int(binding.bt.current_timestamp)
                )

            # hftbacktest returns rc=1 at terminal EndOfData rather
            # than reporting the final applied feed as another rc=2
            # wakeup.  Prove the final row was nevertheless consumed
            # by checking its resulting ask quantity below.
            self.assertEqual(
                wakeups,
                [
                    1_010_000_000,
                    1_110_000_000,
                    2_010_000_000,
                ],
            )

            depth = binding.bt.depth(0)

            self.assertAlmostEqual(
                float(depth.best_ask_qty),
                7.5,
                places=12,
            )

            # mmap remains alive for the complete hftbacktest lifetime.
            self.assertFalse(source._closed)
            self.assertFalse(mmap_ref._mmap.closed)

            binding.close()

            self.assertEqual(
                binding.lifecycle,
                [
                    "memmap_opened_verified",
                    "asset_registered",
                    "backtest_built",
                    "backtest_closed",
                    "memmap_closed",
                ],
            )

            self.assertTrue(binding._closed)
            self.assertTrue(source._closed)
            self.assertTrue(mmap_ref._mmap.closed)

            # Closing is idempotent and cannot reverse lifetime order.
            binding.close()

            self.assertEqual(
                binding.lifecycle[-2:],
                [
                    "backtest_closed",
                    "memmap_closed",
                ],
            )


if __name__ == "__main__":
    unittest.main()

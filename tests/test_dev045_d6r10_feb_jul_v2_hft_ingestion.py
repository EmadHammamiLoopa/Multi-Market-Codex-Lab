from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

import numpy as np

from multimarket import dev045_d6r10_feb_jul_v2_hft_ingestion as d
from multimarket import dev045_d6r5_memmap_contract as m5


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _write_synthetic(path: Path) -> None:
    import hftbacktest as h
    dtype = np.dtype(list(m5.EVENT_DTYPE_DESCR))
    data = np.lib.format.open_memmap(path, mode="w+", dtype=dtype, shape=(4,))
    try:
        data[:] = np.zeros(4, dtype=dtype)
        def ev(base: int, side: int) -> int:
            return int(base | h.EXCH_EVENT | h.LOCAL_EVENT | side)
        rows = (
            (ev(h.DEPTH_EVENT, h.BUY_EVENT), 1_000_000_000, 1_010_000_000, 100.0, 10.0),
            (ev(h.DEPTH_EVENT, h.SELL_EVENT), 1_100_000_000, 1_110_000_000, 100.1, 8.0),
            (ev(h.TRADE_EVENT, h.SELL_EVENT), 2_000_000_000, 2_010_000_000, 100.0, 0.01),
            (ev(h.DEPTH_EVENT, h.SELL_EVENT), 3_000_000_000, 3_010_000_000, 100.1, 7.5),
        )
        for i, (flag, exch, local, px, qty) in enumerate(rows):
            data[i]["ev"] = flag
            data[i]["exch_ts"] = exch
            data[i]["local_ts"] = local
            data[i]["px"] = px
            data[i]["qty"] = qty
        data.flush()
    finally:
        mm = getattr(data, "_mmap", None)
        if mm is not None:
            mm.close()


class TestD6R10(unittest.TestCase):
    def test_scope_and_order(self):
        self.assertEqual(d.PARENT_D6R9B_HEAD, "7635f57c0bf4e7c92379bcb1846d5fa105160103")
        self.assertEqual(d.MODE, "FEED_ONLY_NO_STRATEGY")
        self.assertEqual(tuple(x.day for x in d.DAY_SPECS), (
            "2026-02-01", "2026-03-01", "2026-04-01",
            "2026-05-01", "2026-06-01", "2026-07-01",
        ))

    def test_resource_guards(self):
        self.assertEqual(d.HFTBACKTEST_VERSION, "2.4.4")
        self.assertEqual(d.MIN_MEMAVAILABLE_BYTES, 8_442_945_536)
        self.assertEqual(d.RSS_ABORT_BYTES, 10 * 1024**3)
        self.assertEqual(d.HEARTBEAT_EVERY_WAKEUPS, 100_000)

    def test_frozen_output_identities(self):
        expected = {
            "2026-02-01": (179_584_138, 11_493_385_088, "d757d2ac32a29b0ac587323e115779c466068c6c0eba4270226b9c4109254cbc"),
            "2026-03-01": (150_979_263, 9_662_673_088, "9e6a8b61d05e1a4938e17ffa7969241affc7c06c1d0836188e3a882c363f2d99"),
            "2026-04-01": (132_829_759, 8_501_104_832, "de7e0471e63631394981b301bb461d679192c37eb6241d4d8073cf0640eca7f7"),
            "2026-05-01": (108_328_169, 6_933_003_072, "9433dfb498070dd5dd3e8ab1633c2f19551844f2ddf0d451e120119365bb04a3"),
            "2026-06-01": (172_540_697, 11_042_604_864, "ac97ad27c9d58b3b3e249547b8ae7c74cf2ebfde07965103bd9c8c05d0df1160"),
            "2026-07-01": (181_084_390, 11_589_401_216, "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f"),
        }
        for spec in d.DAY_SPECS:
            self.assertEqual((spec.rows, spec.bytes, spec.sha256), expected[spec.day])

    def test_synthetic_feed_only(self):
        import hftbacktest as h
        self.assertEqual(h.__version__, "2.4.4")
        with tempfile.TemporaryDirectory(prefix="dev045_d6r10_") as td:
            path = Path(td) / "synthetic.npy"
            _write_synthetic(path)
            spec = d.DaySpec("synthetic", path, 4, path.stat().st_size, _sha256(path), path, "unused")
            result = d._ingest(spec, heartbeat=False)
            self.assertEqual(result["source_sha256"], spec.sha256)
            self.assertEqual(result["terminal_rc"], 1)
            self.assertGreater(result["market_wakeups"], 0)
            self.assertLess(result["best_bid_tick"], result["best_ask_tick"])
            self.assertEqual(result["position"], 0.0)
            self.assertEqual(result["working_order_count"], 0)
            self.assertEqual(result["lifecycle"][-2:], ["backtest_closed", "memmap_closed"])


if __name__ == "__main__":
    unittest.main()

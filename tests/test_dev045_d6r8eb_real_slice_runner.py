from __future__ import annotations

import gzip
from pathlib import Path
import tempfile
import unittest

from multimarket import dev045_d6r8e_real_slice_parity_contract as c
from multimarket import dev045_d6r8eb_real_slice_runner as r


class TestD6R8EBRunner(unittest.TestCase):
    def test_runner_is_exactly_locked_to_contract(self):
        self.assertEqual(r.TRADE_SLICE.name, 'trades_BTCUSDT_2026-01-01_0000_0010.csv.gz')
        self.assertEqual(r.DEPTH_SLICE.name, 'depth_BTCUSDT_2026-01-01_0000_0010.csv.gz')
        self.assertEqual(c.D6R8EB_CANONICAL_ATTEMPTS, 1)
        self.assertIs(c.RERUN_AFTER_CANONICAL_RESULT_ALLOWED, False)
        self.assertIs(c.OLD_CONVERTER_RERUN_AUTHORIZED, False)
        self.assertIs(c.UPSTREAM_ORACLE_RERUN_AUTHORIZED, False)

    def test_deterministic_gzip_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / 'a.gz'
            p2 = Path(td) / 'b.gz'
            lines = [b'a,b\n', b'1,2\n', b'3,4\n']
            r._write_deterministic_gzip(p1, lines)
            r._write_deterministic_gzip(p2, lines)
            self.assertEqual(r._sha256(p1), r._sha256(p2))
            with gzip.open(p1, 'rb') as fh:
                self.assertEqual(fh.read(), b''.join(lines))

    def test_slice_extractor_preserves_selected_row_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / 'src.csv.gz'
            dst = Path(td) / 'dst.csv.gz'
            header = b'exchange,symbol,timestamp,local_timestamp,id,side,price,amount\n'
            before = b'x,BTCUSDT,1,1767225599999999,1,buy,1,1\n'
            in1 = b'x,BTCUSDT,2,1767225600000000,2,buy,2,2\n'
            in2 = b'x,BTCUSDT,3,1767226199999999,3,sell,3,3\n'
            stop = b'x,BTCUSDT,4,1767226200000000,4,buy,4,4\n'
            with gzip.open(src, 'wb') as fh:
                fh.write(header + before + in1 + in2 + stop)
            meta = r._extract_slice(src, dst)
            self.assertEqual(meta['selected_rows'], 2)
            self.assertEqual(meta['rows_before_window'], 1)
            self.assertEqual(meta['scanned_rows_until_stop'], 4)
            with gzip.open(dst, 'rb') as fh:
                self.assertEqual(fh.read(), header + in1 + in2)

    def test_real_surfaces_are_not_opened_by_import_or_tests(self):
        self.assertFalse(c.RAW_SLICE_OPEN_AUTHORIZED_NOW)
        self.assertFalse(c.JAN_FULL_DAY_OPEN_AUTHORIZED)
        self.assertFalse(c.RAW_FEB_TO_JUL_OPEN_AUTHORIZED)
        self.assertFalse(c.RUN_112_REPLAYS_AUTHORIZED)
        self.assertFalse(c.LIVE_TRADING_AUTHORIZED)


if __name__ == '__main__':
    unittest.main()

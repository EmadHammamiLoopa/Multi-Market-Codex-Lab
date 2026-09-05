import unittest

from multimarket import dev045_d6r5_memmap_contract as c


class TestDev045D6R5MemmapContract(unittest.TestCase):
    def test_identity_is_exact_and_jan_only(self):
        self.assertEqual(c.EXPERIMENT_ID, "DEV045-D6R5A")
        self.assertEqual(c.CONTRACT_ID, "DEV045-D6R5-JAN-MEMMAP-ADAPTER-V1")
        self.assertEqual(
            c.PARENT_HEAD, "cd9cc4aaf7ab873a1b57af2876e3aaadca3aff14"
        )
        self.assertEqual(c.EXCHANGE, "binance-futures")
        self.assertEqual(c.SYMBOL, "BTCUSDT")
        self.assertEqual(c.DAY, "2026-01-01")
        self.assertEqual(
            c.CANONICAL_NPY_PATH,
            "/home/emadh/Multi-Market/runtime/dev045_d6r4b/output/"
            "BTCUSDT_2026-01-01.npy",
        )
        self.assertEqual(
            c.CANONICAL_NPY_SHA256,
            "8f0a4fbd56ecdc261dbe2041ce138a09456423074925d495272716219a1d4da1",
        )
        self.assertEqual(c.CANONICAL_NPY_BYTES, 4_116_142_528)
        self.assertEqual(c.CANONICAL_NPY_ROWS, 64_314_723)

    def test_dtype_and_bounded_read_contract_are_exact(self):
        self.assertEqual(
            c.EVENT_DTYPE_DESCR,
            (
                ("ev", "<u8"),
                ("exch_ts", "<i8"),
                ("local_ts", "<i8"),
                ("px", "<f8"),
                ("qty", "<f8"),
                ("order_id", "<u8"),
                ("ival", "<i8"),
                ("fval", "<f8"),
            ),
        )
        self.assertEqual(
            c.EVENT_FIELDS,
            (
                "ev",
                "exch_ts",
                "local_ts",
                "px",
                "qty",
                "order_id",
                "ival",
                "fval",
            ),
        )
        self.assertEqual(c.EVENT_ITEMSIZE, 64)
        self.assertEqual(c.EVENT_NDIM, 1)
        self.assertEqual(c.NP_LOAD_MMAP_MODE, "r")
        self.assertIs(c.NP_LOAD_ALLOW_PICKLE, False)
        self.assertEqual(c.PRODUCTION_CHUNK_ROWS, 500_000)
        self.assertGreater(c.HASH_BLOCK_BYTES, 0)
        self.assertLessEqual(c.HASH_BLOCK_BYTES, 8 * 1024 * 1024)

    def test_closed_surfaces_remain_closed(self):
        closed = (
            c.OPEN_RAW_CSV_AUTHORIZED,
            c.RERUN_CONVERTER_AUTHORIZED,
            c.WRITE_CANONICAL_NPY_AUTHORIZED,
            c.WHOLE_FILE_MATERIALIZATION_AUTHORIZED,
            c.SORT_OR_REORDER_AUTHORIZED,
            c.OTHER_DAY_OPEN_AUTHORIZED,
            c.FEB_TO_JUL_OPEN_AUTHORIZED,
            c.AUG_OPEN_AUTHORIZED,
            c.SEP_PLUS_OPEN_AUTHORIZED,
            c.NON_BTC_OPEN_AUTHORIZED,
            c.POLICY_EXECUTION_AUTHORIZED,
            c.HISTORICAL_PNL_AUTHORIZED,
            c.ECONOMIC_ARENA_AUTHORIZED,
            c.NETWORK_ACQUISITION_AUTHORIZED,
            c.RAILWAY_AUTHORIZED,
            c.LIVE_TRADING_AUTHORIZED,
        )
        self.assertEqual(closed, (False,) * len(closed))
        self.assertEqual(
            c.NEXT_AFTER_CONTRACT_CI,
            "IMPLEMENT_D6R5B_READ_ONLY_MEMMAP_ADAPTER",
        )


if __name__ == "__main__":
    unittest.main()

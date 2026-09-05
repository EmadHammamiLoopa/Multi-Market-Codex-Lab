from __future__ import annotations

import unittest

from multimarket import dev045_d6r8ec_semantic_slice_identity_contract as a
from multimarket import dev045_d6r8ed_semantic_real_parity_contract as c


class TestD6R8EDSemanticRealParityContract(unittest.TestCase):
    def test_parent_and_history(self) -> None:
        self.assertEqual(c.PARENT_HEAD, "4d86b93ab083c78446c6ad8a19877cc607b8be0a")
        self.assertTrue(c.D6R2B_REMAINS_HISTORICAL_PASS)
        self.assertTrue(c.D6R8EB_REMAINS_FROZEN_FAIL)
        self.assertFalse(c.D6R8EB_RERUN_AUTHORIZED)

    def test_semantic_identity_matches_d6r8ec(self) -> None:
        names = (
            "TRADE_RAW_BYTES", "TRADE_RAW_SHA256", "DEPTH_RAW_BYTES", "DEPTH_RAW_SHA256",
            "WINDOW_START_LOCAL_TIMESTAMP_US", "WINDOW_END_LOCAL_TIMESTAMP_US",
            "TRADE_SEMANTIC_ROWS", "TRADE_SEMANTIC_BYTES", "TRADE_DECOMPRESSED_SHA256",
            "TRADE_FIRST_LOCAL_TIMESTAMP_US", "TRADE_LAST_LOCAL_TIMESTAMP_US",
            "DEPTH_SEMANTIC_ROWS", "DEPTH_SEMANTIC_BYTES", "DEPTH_DECOMPRESSED_SHA256",
            "DEPTH_FIRST_LOCAL_TIMESTAMP_US", "DEPTH_LAST_LOCAL_TIMESTAMP_US",
            "DEPTH_SNAPSHOT_BATCHES", "DEPTH_SNAPSHOT_ROWS", "DEPTH_ENDS_INSIDE_SNAPSHOT_BATCH",
        )
        for name in names:
            self.assertEqual(getattr(c, name), getattr(a, name))
        self.assertFalse(c.COMPRESSED_GZIP_SHA_IS_PARITY_GATE)

    def test_three_way_same_slice_parity_is_required(self) -> None:
        self.assertTrue(c.SAME_PHYSICAL_SLICE_FILES_REQUIRED)
        self.assertEqual(c.PARITY_MODE, "FIELDWISE_EXACT_NAN_EQUAL")
        self.assertEqual(c.PAIRWISE_PARITY_REQUIRED, ("upstream_vs_old", "upstream_vs_v2", "old_vs_v2"))
        self.assertFalse(c.FLOAT_TOLERANCE_ALLOWED)
        self.assertFalse(c.POST_CONVERSION_SORT_ALLOWED)
        self.assertFalse(c.ROW_REORDERING_ALLOWED)
        self.assertEqual(c.PARITY_ITEMSIZE_REQUIRED, 64)

    def test_frozen_converter_bindings(self) -> None:
        self.assertEqual(c.V2_IMPLEMENTATION_COMMIT, "3d304429a825d50bf3b0f292632fc35e7a92a947")
        self.assertEqual(c.V2_PRODUCTION_INITIAL_CHUNK_ROWS, 250_000)
        self.assertEqual(c.V2_MERGE_FAN_IN, 8)
        self.assertFalse(c.V2_TUNING_CHANGE_ALLOWED)
        self.assertEqual(c.OLD_IMPLEMENTATION_SHA256, "8f79ec81c664f1762a87bfcf8757564abbe2d7f5fd89b1c83fc78de0ac4b94ac")
        self.assertEqual(c.OLD_PRODUCTION_CHUNK_ROWS, 500_000)
        self.assertFalse(c.OLD_IMPLEMENTATION_CHANGE_ALLOWED)
        self.assertEqual(c.HFTBACKTEST_VERSION, "2.4.4")
        self.assertEqual(c.UPSTREAM_COMMIT, "a244a14250b42d97fc305569c93c4117cd5e1dff")
        self.assertEqual(c.UPSTREAM_TARDIS_CONVERTER_GIT_BLOB, "1ca038895d30f320561d6b28ffa13c1d788ea6bf")

    def test_one_new_successor_attempt_is_separate(self) -> None:
        self.assertEqual(c.SUCCESSOR_EXECUTION_ID, "DEV045-D6R8EF")
        self.assertEqual(c.SUCCESSOR_CANONICAL_ATTEMPTS, 1)
        self.assertTrue(c.FIRST_SUCCESSOR_RESULT_FROZEN_PASS_OR_FAIL)
        self.assertFalse(c.SUCCESSOR_RERUN_AFTER_RESULT_ALLOWED)
        self.assertNotIn("d6r8eb", c.SUCCESSOR_ATTEMPT_MARKER_PATH)
        self.assertNotIn("d6r8eb", c.SUCCESSOR_EVIDENCE_PATH)

    def test_contract_executes_nothing(self) -> None:
        closed = (
            c.RAW_FILE_CONTENT_OPEN_AUTHORIZED_NOW,
            c.SEMANTIC_SLICE_REEXTRACTION_AUTHORIZED_NOW,
            c.UPSTREAM_REAL_EXECUTION_AUTHORIZED_NOW,
            c.OLD_CONVERTER_REAL_EXECUTION_AUTHORIZED_NOW,
            c.V2_REAL_EXECUTION_AUTHORIZED_NOW,
            c.JAN_FULL_DAY_OPEN_AUTHORIZED,
            c.RAW_FEB_TO_JUL_OPEN_AUTHORIZED,
            c.CONVERSION_FEB_TO_JUL_AUTHORIZED,
            c.RUN_112_REPLAYS_AUTHORIZED,
            c.POLICY_EXECUTION_AUTHORIZED,
            c.HISTORICAL_PNL_AUTHORIZED,
            c.ECONOMIC_ARENA_AUTHORIZED,
            c.AUG_OPEN_AUTHORIZED,
            c.SEP_PLUS_OPEN_AUTHORIZED,
            c.NON_BTC_OPEN_AUTHORIZED,
            c.NETWORK_ACQUISITION_AUTHORIZED,
            c.RAILWAY_AUTHORIZED,
            c.LIVE_TRADING_AUTHORIZED,
        )
        self.assertTrue(all(value is False for value in closed))
        self.assertTrue(c.D6R8EE_SYNTHETIC_RUNNER_IMPLEMENTATION_REQUIRED)
        self.assertEqual(c.NEXT_AFTER_D6R8ED_CI, "D6R8EE_IMPLEMENT_SEMANTIC_REAL_PARITY_RUNNER_SYNTHETIC_ONLY")


if __name__ == "__main__":
    unittest.main()

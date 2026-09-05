from __future__ import annotations

import json
from pathlib import Path
import unittest

from multimarket import dev045_d6r8ec_semantic_slice_identity_contract as c

ROOT = Path(__file__).resolve().parents[1]


class TestD6R8ECSemanticSliceIdentityContract(unittest.TestCase):
    def test_parent_and_history_are_preserved(self) -> None:
        self.assertEqual(c.PARENT_HEAD, "4390605f0050bdbbf49058f41a52e954fbc3af7a")
        self.assertTrue(c.D6R2B_REMAINS_HISTORICAL_PASS)
        self.assertTrue(c.D6R8EB_REMAINS_FROZEN_FAIL)
        self.assertFalse(c.D6R8EB_RERUN_AUTHORIZED)
        self.assertFalse(c.D6R2B_COMPRESSED_HASH_REINTERPRETED)

    def test_exact_d4_jan_raw_lineage(self) -> None:
        rows = {}
        for line in (ROOT / c.D4_MANIFEST_PATH).read_text(encoding="utf-8").splitlines()[1:]:
            kind, day, size, sha, rel = line.split("\t")
            if day == c.DAY:
                rows[kind] = (int(size), sha, rel)
        self.assertEqual(
            rows["trades"],
            (c.TRADE_RAW_BYTES, c.TRADE_RAW_SHA256, c.TRADE_RELATIVE_PATH),
        )
        self.assertEqual(
            rows["incremental_book_L2"],
            (c.DEPTH_RAW_BYTES, c.DEPTH_RAW_SHA256, c.DEPTH_RELATIVE_PATH),
        )

    def test_forensic_semantic_payload_is_frozen_without_v2_output(self) -> None:
        evidence = json.loads((ROOT / c.FORENSIC_EVIDENCE_PATH).read_text(encoding="utf-8"))
        self.assertEqual(evidence["root_cause"], c.FORENSIC_ROOT_CAUSE_REQUIRED)
        self.assertFalse(evidence["logical_payload_identity_proven"])
        self.assertFalse(evidence["gzip_representation_only_mismatch_proven"])
        self.assertFalse(evidence["real_converter_executed"])
        self.assertEqual(evidence["current_slices"]["trades"]["data_rows"], c.TRADE_SEMANTIC_ROWS)
        self.assertEqual(evidence["current_slices"]["trades"]["decompressed_length"], c.TRADE_SEMANTIC_BYTES)
        self.assertEqual(evidence["current_slices"]["trades"]["decompressed_sha256"], c.TRADE_DECOMPRESSED_SHA256)
        self.assertEqual(evidence["current_slices"]["depth"]["data_rows"], c.DEPTH_SEMANTIC_ROWS)
        self.assertEqual(evidence["current_slices"]["depth"]["decompressed_length"], c.DEPTH_SEMANTIC_BYTES)
        self.assertEqual(evidence["current_slices"]["depth"]["decompressed_sha256"], c.DEPTH_DECOMPRESSED_SHA256)
        self.assertFalse(c.V2_WAS_EXECUTED_IN_D6R8EB)
        self.assertTrue(c.NO_V2_OUTCOME_WAS_AVAILABLE_WHEN_SEMANTIC_DIGESTS_WERE_FROZEN)

    def test_semantic_identity_does_not_depend_on_gzip_container(self) -> None:
        self.assertFalse(c.COMPRESSED_GZIP_SHA_IS_SEMANTIC_IDENTITY)
        required = set(c.SUCCESSOR_SEMANTIC_IDENTITY_COMPONENTS)
        self.assertIn("d4_exact_raw_file_sha256_and_bytes", required)
        self.assertIn("exact_selected_row_bytes_and_order", required)
        self.assertIn("exact_decompressed_payload_sha256_and_length", required)
        self.assertIn("exact_depth_snapshot_structure", required)

    def test_old_d6r2b_output_is_not_silent_successor_oracle(self) -> None:
        self.assertFalse(c.D6R2B_OUTPUT_SHA_AS_SOLE_SUCCESSOR_ORACLE_ALLOWED)
        self.assertEqual(
            c.SUCCESSOR_PARITY_ARCHITECTURE,
            "SAME_SEMANTIC_SLICE_V2_VS_FROZEN_OLD_CONVERTER_AND_UPSTREAM_ORACLE",
        )
        self.assertFalse(c.OLD_CONVERTER_RERUN_AUTHORIZED_NOW)
        self.assertFalse(c.UPSTREAM_ORACLE_RERUN_AUTHORIZED_NOW)
        self.assertFalse(c.V2_REAL_EXECUTION_AUTHORIZED_NOW)

    def test_contract_opens_nothing(self) -> None:
        self.assertEqual(c.STATUS, "FROZEN_CONTRACT_ONLY")
        closed = (
            c.RAW_FILE_CONTENT_OPEN_AUTHORIZED,
            c.SEMANTIC_SLICE_REEXTRACTION_AUTHORIZED,
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
        self.assertEqual(
            c.NEXT_AFTER_D6R8EC_CI,
            "FREEZE_D6R8ED_NEW_SEMANTIC_REAL_PARITY_CONTRACT",
        )


if __name__ == "__main__":
    unittest.main()

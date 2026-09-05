from __future__ import annotations

import json
from pathlib import Path
import unittest

from multimarket import dev045_d6r8c_bounded_converter_redesign_contract as redesign
from multimarket import dev045_d6r8_structurally_bounded_converter as v2
from multimarket import dev045_d6r8e_real_slice_parity_contract as c

ROOT = Path(__file__).resolve().parents[1]


class TestD6R8ERealSliceParityContract(unittest.TestCase):
    def test_exact_parent_and_v2_contract(self):
        self.assertEqual(c.PARENT_HEAD, "3d304429a825d50bf3b0f292632fc35e7a92a947")
        self.assertEqual(c.D6R2A_COMMIT, "8b81db69ddb211caf3f45b95c4e1f0026acebeda")
        self.assertEqual(c.D6R2B_COMMIT, "4ff70ec50e39da432a70bf0444907f536586ed3e")
        self.assertEqual(v2.PRODUCTION_INITIAL_CHUNK_ROWS, 250_000)
        self.assertEqual(v2.MERGE_FAN_IN, 8)
        self.assertEqual(v2.PRODUCTION_TUNING, v2._Tuning())
        self.assertIs(redesign.WHOLE_FILE_MMAP_ALLOWED, False)

    def test_exact_raw_paths_and_window(self):
        self.assertEqual(c.RAW_ROOT, "/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw")
        self.assertEqual(c.TRADE_RELATIVE_PATH, "trades/BTCUSDT/2026-01-01.csv.gz")
        self.assertEqual(c.DEPTH_RELATIVE_PATH, "incremental_book_L2/BTCUSDT/2026-01-01.csv.gz")
        self.assertEqual(c.SELECTION_FIELD, "local_timestamp")
        self.assertEqual(c.WINDOW_START_LOCAL_TIMESTAMP_US, 1_767_225_600_000_000)
        self.assertEqual(c.WINDOW_END_LOCAL_TIMESTAMP_US, 1_767_226_200_000_000)
        self.assertEqual(c.WINDOW_DURATION_SECONDS, 600)
        self.assertIs(c.WINDOW_EXTENSION_ALLOWED, False)
        self.assertIs(c.WINDOW_SHRINK_ALLOWED, False)

    def test_d6r2b_evidence_is_exact_oracle(self):
        evidence = json.loads((ROOT / c.D6R2B_EVIDENCE_PATH).read_text(encoding="utf-8"))
        self.assertEqual(evidence["experiment_id"], "DEV045-D6R2B")
        self.assertEqual(evidence["status"], c.D6R2B_REQUIRED_STATUS)
        self.assertEqual(evidence["canonical_attempt"], c.D6R2B_CANONICAL_ATTEMPT)
        self.assertEqual(evidence["scope"]["window_start_us"], c.WINDOW_START_LOCAL_TIMESTAMP_US)
        self.assertEqual(evidence["scope"]["window_end_us"], c.WINDOW_END_LOCAL_TIMESTAMP_US)
        self.assertEqual(evidence["slice"]["trades"]["selected_rows"], c.TRADE_SELECTED_ROWS)
        self.assertEqual(evidence["slice"]["trades"]["sha256"], c.TRADE_SLICE_SHA256)
        self.assertEqual(evidence["slice"]["depth"]["selected_rows"], c.DEPTH_SELECTED_ROWS)
        self.assertEqual(evidence["slice"]["depth"]["sha256"], c.DEPTH_SLICE_SHA256)
        self.assertIs(evidence["slice"]["depth"]["ends_inside_snapshot_batch"], False)
        self.assertEqual(evidence["bounded"]["base_event_rows"], c.FROZEN_OLD_BASE_EVENT_ROWS)
        self.assertEqual(evidence["bounded"]["final_event_rows"], c.FROZEN_OLD_FINAL_EVENT_ROWS)
        self.assertEqual(evidence["bounded"]["implementation_output_sha256"], c.FROZEN_OLD_OUTPUT_SHA256)
        self.assertIs(evidence["parity"]["pass"], True)

    def test_slice_identity_is_fully_frozen(self):
        self.assertEqual(c.TRADE_SELECTED_ROWS, 13_073)
        self.assertEqual(c.DEPTH_SELECTED_ROWS, 483_149)
        self.assertEqual(c.TRADE_SLICE_SHA256, "a7595b2d6ce750eaf032f8f693683a42c008bd59a2cd3d7035928c39da2a4e0d")
        self.assertEqual(c.DEPTH_SLICE_SHA256, "e52a325096ddad2ac28b4f299d1e522f61e9e1dc50a7275d75e07833e4ba2848")
        self.assertIs(c.DEPTH_FIRST_SELECTED_IS_SNAPSHOT, True)
        self.assertEqual(c.DEPTH_SNAPSHOT_BATCHES, 1)
        self.assertEqual(c.DEPTH_SNAPSHOT_ROWS, 2_002)
        self.assertIs(c.DEPTH_ENDS_INSIDE_SNAPSHOT_BATCH, False)

    def test_frozen_real_oracle_output(self):
        self.assertEqual(c.FROZEN_OLD_BASE_EVENT_ROWS, 496_224)
        self.assertEqual(c.FROZEN_OLD_FINAL_EVENT_ROWS, 503_934)
        self.assertEqual(c.FROZEN_OLD_OUTPUT_ITEMSIZE, 64)
        self.assertEqual(c.FROZEN_OLD_OUTPUT_SHA256, "60ebc2aec273976c12526f7c49159d005368388a0f9d5993af269cc9753ffaf7")
        self.assertEqual(c.FROZEN_OLD_PARITY_MODE, "FIELDWISE_EXACT_NAN_EQUAL")
        self.assertIs(c.OLD_CONVERTER_RERUN_AUTHORIZED, False)
        self.assertIs(c.UPSTREAM_ORACLE_RERUN_AUTHORIZED, False)

    def test_one_shot_v2_execution_is_preregistered(self):
        self.assertEqual(c.D6R8EB_EXECUTION_MODE, "V2_ONLY_AGAINST_FROZEN_D6R2B_ORACLE")
        self.assertEqual(c.D6R8EB_CANONICAL_ATTEMPTS, 1)
        self.assertIs(c.FIRST_RESULT_FROZEN_PASS_OR_FAIL, True)
        self.assertIs(c.RERUN_AFTER_CANONICAL_RESULT_ALLOWED, False)
        self.assertIs(c.PRODUCTION_TUNING_REQUIRED, True)
        self.assertEqual(c.V2_RUNTIME_RSS_ABORT_BYTES, 6_442_450_944)
        self.assertEqual(c.MIN_MEMAVAILABLE_BYTES, 8_589_934_592)

    def test_contract_opens_nothing(self):
        self.assertEqual(c.STATUS, "FROZEN_CONTRACT_ONLY")
        closed = (
            c.RAW_SLICE_OPEN_AUTHORIZED_NOW,
            c.V2_REAL_SLICE_EXECUTION_AUTHORIZED_NOW,
            c.JAN_FULL_DAY_OPEN_AUTHORIZED,
            c.RERUN_D6R4B_JAN_CONVERSION_AUTHORIZED,
            c.RERUN_D6R5C_JAN_VALIDATION_AUTHORIZED,
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
        self.assertIs(c.D6R8EB_AFTER_D6R8EA_CI_GREEN, True)
        self.assertEqual(c.NEXT_AFTER_D6R8EA_CI, "D6R8EB_ONE_SHOT_V2_REAL_10MIN_PARITY")


if __name__ == "__main__":
    unittest.main()

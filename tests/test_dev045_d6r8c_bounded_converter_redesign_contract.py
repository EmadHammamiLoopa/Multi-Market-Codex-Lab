from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from multimarket import dev045_d6r8b_memory_scaling_audit as audit
from multimarket import dev045_d6r8c_bounded_converter_redesign_contract as c

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


class TestD6R8CRedesignContract(unittest.TestCase):
    def test_exact_parent_and_old_converter_identity(self):
        self.assertEqual(c.PARENT_HEAD, "4a7df3e85f4cf495ebe244fceb03c14996d933c7")
        self.assertEqual(audit.STATUS, c.PARENT_AUDIT_REQUIRED_STATUS)
        self.assertIs(audit.STRUCTURAL_REDESIGN_REQUIRED, True)
        self.assertEqual(_sha256(c.FROZEN_OLD_CONVERTER_PATH), c.FROZEN_OLD_CONVERTER_SHA256)
        self.assertIs(c.OLD_CONVERTER_EDIT_AUTHORIZED, False)

    def test_frozen_structural_bounds(self):
        self.assertEqual(c.PRODUCTION_INITIAL_CHUNK_ROWS, 250_000)
        self.assertEqual(c.MERGE_FAN_IN, 8)
        self.assertEqual(c.MERGE_INPUT_WINDOW_ROWS, 16_384)
        self.assertEqual(c.MERGE_OUTPUT_BUFFER_ROWS, 65_536)
        self.assertEqual(c.CORRECTED_INPUT_WINDOW_ROWS, 32_768)
        self.assertEqual(c.FINAL_OUTPUT_BUFFER_ROWS, 65_536)
        self.assertEqual(c.VALIDATION_WINDOW_ROWS, 65_536)
        self.assertEqual(c.MAX_ACTIVE_RUN_READERS, 8)
        self.assertIs(c.WHOLE_FILE_MMAP_ALLOWED, False)
        self.assertIs(c.FINAL_OUTPUT_FULL_SHAPE_MEMMAP_ALLOWED, False)

    def test_sort_and_event_semantics_are_frozen(self):
        self.assertEqual(c.SORT_KEYS["exchange"], ("exch_ts", "source_seq"))
        self.assertEqual(c.SORT_KEYS["local"], ("local_ts", "source_seq"))
        self.assertEqual(c.EVENT_ITEMSIZE_BYTES, 64)
        self.assertEqual(c.TEMP_RECORD_ITEMSIZE_BYTES, 72)
        self.assertEqual(c.HFTBACKTEST_VERSION, "2.4.4")
        self.assertEqual(c.BASE_LATENCY_NS, 0)
        self.assertIn("same_timestamp_pair_requires_same_source_seq", c.CORRECTED_EVENT_INVARIANTS)
        self.assertIn("atomic_replace_only_after_all_postconditions_pass", c.FINALIZATION_INVARIANTS)

    def test_memory_gate_is_fixed_not_month_scaled(self):
        self.assertEqual(c.MIN_MEMAVAILABLE_BYTES, 8_589_934_592)
        self.assertEqual(c.RUNTIME_RSS_ABORT_BYTES, 6_442_450_944)
        self.assertIs(c.SWAP_COUNTS_TOWARD_MEMORY_GATE, False)
        self.assertIs(c.RESOURCE_RECHECK_IMMEDIATELY_BEFORE_CANONICAL_ATTEMPT, True)
        self.assertEqual(c.MIN_NOFILE_SOFT, 128)
        self.assertEqual(c.MIN_NOFILE_HARD, 128)

    def test_frozen_raw_metadata_and_scratch_gate(self):
        expected = {
            "2026-02-01": 127_721_761_664,
            "2026-03-01": 110_464_539_904,
            "2026-04-01": 99_783_158_784,
            "2026-05-01": 83_889_901_184,
            "2026-06-01": 123_101_446_784,
            "2026-07-01": 127_303_192_704,
        }
        self.assertEqual(c.FROZEN_SCRATCH_REQUIREMENTS, expected)
        self.assertEqual(c.MAX_FEB_JUL_REQUIRED_SCRATCH_BYTES, 127_721_761_664)
        self.assertEqual(c.SCRATCH_BYTES_PER_FROZEN_RAW_ROW, 640)
        self.assertEqual(c.SCRATCH_FIXED_RESERVE_BYTES, 17_179_869_184)

    def test_hierarchical_merge_is_actually_bounded(self):
        inv = set(c.HIERARCHICAL_MERGE_INVARIANTS)
        self.assertIn("each_group_has_at_most_8_input_runs", inv)
        self.assertIn("each_input_run_reader_holds_at_most_16384_rows", inv)
        self.assertIn("merge_heap_has_at_most_one_head_per_active_run", inv)
        self.assertIn("merge_output_buffer_holds_at_most_65536_temp_records", inv)
        self.assertIn("repeat_until_exactly_one_exchange_run_and_one_local_run", inv)
        self.assertEqual(c.RUN_READER_MECHANISM, "NPY_HEADER_PLUS_SEQUENTIAL_NP_FROMFILE_WINDOWS")
        self.assertEqual(c.MERGE_ALGORITHM, "FIXED_FAN_IN_HIERARCHICAL_EXTERNAL_MERGE")

    def test_future_parity_gates_are_preregistered(self):
        self.assertEqual(c.D6R8D_SCOPE, "SYNTHETIC_ONLY")
        self.assertIn("fixtures_force_more_than_8_runs", c.D6R8D_SYNTHETIC_REQUIREMENTS)
        self.assertIn("fixtures_force_at_least_3_hierarchical_merge_levels", c.D6R8D_SYNTHETIC_REQUIREMENTS)
        self.assertIn("fieldwise_exact_nan_equal", c.D6R8E_REAL_SLICE_REQUIREMENTS)
        self.assertIn("v2_peak_rss_recorded", c.D6R8E_REAL_SLICE_REQUIREMENTS)
        self.assertIn("old_full_day_jan_not_rerun", c.D6R8E_REAL_SLICE_REQUIREMENTS)

    def test_design_only_and_all_execution_surfaces_closed(self):
        self.assertEqual(c.STATUS, "FROZEN_DESIGN_ONLY")
        self.assertEqual(c.CANONICAL_ATTEMPT_COUNT, 0)
        closed = (
            c.RAW_DATA_OPEN_AUTHORIZED,
            c.JAN_CANONICAL_NPY_OPEN_AUTHORIZED,
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
        self.assertEqual(c.NEXT_AFTER_D6R8C_CI, "D6R8D_IMPLEMENT_V2_SYNTHETIC_ONLY")


if __name__ == "__main__":
    unittest.main()

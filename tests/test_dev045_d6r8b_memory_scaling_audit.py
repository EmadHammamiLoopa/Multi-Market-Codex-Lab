from __future__ import annotations

import hashlib
import math
from pathlib import Path
import unittest

from multimarket import dev045_d6r8b_memory_scaling_audit as c

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


class TestD6R8BMemoryScalingAudit(unittest.TestCase):
    def test_exact_parent_and_frozen_sources(self):
        self.assertEqual(c.PARENT_HEAD, "09bc05a9bd5625251c178386ed5fbae0f8955318")
        self.assertEqual(_sha256(c.CONVERTER_PATH), c.CONVERTER_SHA256)
        self.assertEqual(_sha256(c.D6R4B_EVIDENCE_PATH), c.D6R4B_EVIDENCE_SHA256)
        self.assertEqual(_sha256(c.D6R5C_EVIDENCE_PATH), c.D6R5C_EVIDENCE_SHA256)

    def test_jan_reference_arithmetic_is_exact(self):
        self.assertEqual(c.JAN_TEMP_AXIS_PAYLOAD_BYTES, 4_583_971_872)
        self.assertEqual(c.JAN_DUAL_SORT_PAYLOAD_BYTES, 9_167_943_744)
        self.assertEqual(c.JAN_OUTPUT_DATA_BYTES, 4_116_142_272)
        self.assertEqual(c.JAN_OUTPUT_FILE_BYTES, 4_116_142_528)
        self.assertEqual(
            2 * math.ceil(c.JAN_BASE_EVENT_ROWS / c.PRODUCTION_CHUNK_ROWS),
            c.JAN_TEMP_SORT_RUNS_TOTAL,
        )
        self.assertEqual(c.JAN_RUNS_PER_AXIS * 2, c.JAN_TEMP_SORT_RUNS_TOTAL)

    def test_static_findings_match_converter_source(self):
        source = (ROOT / c.CONVERTER_PATH).read_text(encoding="utf-8")
        self.assertIn("self.exchange_paths: list[Path] = []", source)
        self.assertIn("self.local_paths: list[Path] = []", source)
        self.assertIn("np.load(path, mmap_mode=\"r\", allow_pickle=False)", source)
        self.assertIn("_MergedRunStream(exchange_paths, \"exch_ts\")", source)
        self.assertIn("_MergedRunStream(local_paths, \"local_ts\")", source)
        self.assertIn("np.lib.format.open_memmap(", source)
        self.assertIn("data = np.load(path, mmap_mode=\"r\", allow_pickle=False)", source)
        self.assertGreaterEqual(source.count("_corrected_events("), 3)

    def test_chunking_does_not_make_later_mappings_chunk_bounded(self):
        self.assertIn("csv_rows_retained_at_most_chunk_rows", c.CODE_PROVEN_BOUNDED)
        self.assertIn("two_complete_temp_sort_datasets_are_spilled", c.CODE_PROVEN_DAY_SCALING)
        self.assertIn(
            "corrected_events_opens_exchange_and_local_run_sets_simultaneously",
            c.CODE_PROVEN_DAY_SCALING,
        )
        self.assertIn(
            "final_validation_keeps_full_output_memmap_open_while_scanning_chunks",
            c.CODE_PROVEN_DAY_SCALING,
        )
        self.assertIs(c.CURRENT_CONVERTER_STRUCTURALLY_MEMORY_BOUNDED_BY_CHUNK_ROWS, False)

    def test_diagnosis_does_not_overclaim_exact_peak_cause(self):
        self.assertIs(c.EXACT_JAN_RSS_ATTRIBUTION_PROVEN, False)
        self.assertIs(c.JAN_RSS_IS_CONSISTENT_WITH_DAY_SIZED_MMAP_RESIDENCY, True)
        self.assertIs(c.D6R5C_RSS_IS_CONSISTENT_WITH_FULL_OUTPUT_MMAP_RESIDENCY, True)
        self.assertIs(c.KERNEL_PAGE_RESIDENCY_EXACT_CONTRIBUTION_PROVEN, False)
        self.assertIs(c.NUMPY_ALLOCATOR_HIGH_WATER_EXACT_CONTRIBUTION_PROVEN, False)

    def test_upstream_converter_not_production_memory_driver(self):
        self.assertIs(c.UPSTREAM_TARDIS_CONVERTER_CALLED_IN_PRODUCTION, False)
        self.assertIs(
            c.UPSTREAM_CONVERTER_INTERMEDIATE_ARRAYS_ARE_PRODUCTION_RSS_DRIVER,
            False,
        )

    def test_redesign_is_required_before_feb_jul(self):
        self.assertEqual(c.STATUS, "PASS_STATIC_AUDIT_REDESIGN_REQUIRED")
        self.assertIs(c.STRUCTURAL_REDESIGN_REQUIRED, True)
        self.assertIs(c.CURRENT_CONVERTER_AS_IS_FEB_TO_JUL_AUTHORIZED, False)
        required = set(c.D6R8C_REQUIRED_PROPERTIES)
        self.assertIn("cap_simultaneously_live_merge_runs_or_use_hierarchical_fan_in", required)
        self.assertIn("use_bounded_window_readers_for_large_run_payloads", required)
        self.assertIn("write_final_npy_payload_through_bounded_output_buffer", required)
        self.assertIn(
            "validate_final_output_with_windowed_mappings_that_are_closed_per_window",
            required,
        )
        self.assertIn(
            "derive_resource_gate_from_structural_memory_bound_not_month_row_ratio",
            required,
        )

    def test_all_execution_surfaces_remain_closed(self):
        values = (
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
        self.assertTrue(all(value is False for value in values))


if __name__ == "__main__":
    unittest.main()

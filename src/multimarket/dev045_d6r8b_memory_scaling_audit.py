from __future__ import annotations

EXPERIMENT_ID = "DEV045-D6R8B"
CONTRACT_ID = "DEV045-D6R8B-BOUNDED-CONVERTER-MEMORY-SCALING-AUDIT-V1"
SCHEMA_VERSION = "dev045-d6r8b-bounded-converter-memory-scaling-audit-v1"
STATUS = "PASS_STATIC_AUDIT_REDESIGN_REQUIRED"

PARENT_BRANCH = "research/dev045-m6-personal-trading-entry-abstention-gate-v1"
PARENT_HEAD = "09bc05a9bd5625251c178386ed5fbae0f8955318"

CONVERTER_PATH = "src/multimarket/dev045_d6r_bounded_converter.py"
CONVERTER_SHA256 = "8f79ec81c664f1762a87bfcf8757564abbe2d7f5fd89b1c83fc78de0ac4b94ac"

D6R4B_EVIDENCE_PATH = "evidence/dev045_d6r4b_jan01_full_day_conversion.json"
D6R4B_EVIDENCE_SHA256 = "a90f450d6c846d81e95a720e70804d76ad99d39501421508b9199e007d09b579"
D6R5C_EVIDENCE_PATH = "evidence/dev045_d6r5c_jan_memmap_validation.json"
D6R5C_EVIDENCE_SHA256 = "79fa94de273c1ced6bf3a6a752331c8026056cbe5dabf22299f43b229cdeddf3"

PRODUCTION_CHUNK_ROWS = 500_000
TEMP_RECORD_ITEMSIZE_BYTES = 72
EVENT_ITEMSIZE_BYTES = 64
JAN_BASE_EVENT_ROWS = 63_666_276
JAN_FINAL_EVENT_ROWS = 64_314_723
JAN_TEMP_SORT_RUNS_TOTAL = 256
JAN_RUNS_PER_AXIS = 128
JAN_TEMP_AXIS_PAYLOAD_BYTES = JAN_BASE_EVENT_ROWS * TEMP_RECORD_ITEMSIZE_BYTES
JAN_DUAL_SORT_PAYLOAD_BYTES = 2 * JAN_TEMP_AXIS_PAYLOAD_BYTES
JAN_OUTPUT_DATA_BYTES = JAN_FINAL_EVENT_ROWS * EVENT_ITEMSIZE_BYTES
JAN_OUTPUT_FILE_BYTES = 4_116_142_528
JAN_CONVERSION_PEAK_RSS_BYTES = 9_946_800_128
JAN_PRECHECK_MEMAVAILABLE_BYTES = 10_097_618_944
JAN_READ_ONLY_VALIDATION_PEAK_RSS_BYTES = 4_221_472_768

# Code-proven bounded allocations/lifetimes. Exact Python-object overhead for CSV
# strings is not statically knowable, but the number of retained CSV rows is.
CODE_PROVEN_BOUNDED = (
    "csv_rows_retained_at_most_chunk_rows",
    "run_builder_temp_buffer_at_most_chunk_rows",
    "per_flush_lexsort_index_at_most_chunk_rows",
    "per_flush_sorted_record_copy_at_most_chunk_rows",
    "snapshot_bid_buffer_at_most_chunk_rows",
    "snapshot_ask_buffer_at_most_chunk_rows",
    "sha256_userspace_buffer_is_one_mib",
)

# Code-proven structures whose live mapping/metadata scale with total day rows or
# run count rather than only with chunk_rows.
CODE_PROVEN_DAY_SCALING = (
    "exchange_sort_run_count_scales_with_total_rows",
    "local_sort_run_count_scales_with_total_rows",
    "two_complete_temp_sort_datasets_are_spilled",
    "merged_run_stream_opens_every_run_for_an_axis",
    "corrected_events_opens_exchange_and_local_run_sets_simultaneously",
    "corrected_events_full_merge_is_traversed_twice",
    "final_output_is_created_as_full_shape_writable_memmap",
    "final_validation_keeps_full_output_memmap_open_while_scanning_chunks",
)

SMALL_BUT_SCALING_METADATA = (
    "exchange_path_list",
    "local_path_list",
    "merge_arrays_list",
    "merge_heap_one_head_per_run",
    "open_file_descriptor_count",
)

# Production convert_tardis is the project's own bounded converter. The frozen
# hftbacktest tardis.convert surface was used as a parity oracle, not called by
# the production full-day conversion path.
UPSTREAM_TARDIS_CONVERTER_CALLED_IN_PRODUCTION = False
UPSTREAM_CONVERTER_INTERMEDIATE_ARRAYS_ARE_PRODUCTION_RSS_DRIVER = False

# Static diagnosis: these mappings create a day-size-dependent resident-set
# risk. Static inspection does not prove which pages were resident at the exact
# ru_maxrss instant; Linux reclaim/writeback behavior is empirical.
PRIMARY_STRUCTURAL_RSS_RISK = (
    "all_run_memmaps_live_during_kway_corrected_merge",
    "full_shape_output_writable_memmap",
    "full_file_read_only_memmap_during_validation",
)
EXACT_JAN_RSS_ATTRIBUTION_PROVEN = False
JAN_RSS_IS_CONSISTENT_WITH_DAY_SIZED_MMAP_RESIDENCY = True
D6R5C_RSS_IS_CONSISTENT_WITH_FULL_OUTPUT_MMAP_RESIDENCY = True

CSV_PYTHON_OBJECT_OVERHEAD_EXACT_BYTES_PROVEN = False
CSV_PYTHON_OBJECT_OVERHEAD_IS_CHUNK_BOUNDED = True
NUMPY_ALLOCATOR_HIGH_WATER_EXACT_CONTRIBUTION_PROVEN = False
KERNEL_PAGE_RESIDENCY_EXACT_CONTRIBUTION_PROVEN = False

CURRENT_CONVERTER_STRUCTURALLY_MEMORY_BOUNDED_BY_CHUNK_ROWS = False
CURRENT_CONVERTER_AS_IS_FEB_TO_JUL_AUTHORIZED = False
STRUCTURAL_REDESIGN_REQUIRED = True

# D6R8C design requirements. The exact fan-in/window constants are deliberately
# not chosen by this static audit; they must be frozen in the redesign contract.
D6R8C_REQUIRED_PROPERTIES = (
    "preserve_exact_sort_key_timestamp_then_source_seq",
    "cap_simultaneously_live_merge_runs_or_use_hierarchical_fan_in",
    "use_bounded_window_readers_for_large_run_payloads",
    "do_not_keep_full_output_writable_mapping_live_while_touching_whole_file",
    "write_final_npy_payload_through_bounded_output_buffer",
    "preserve_exact_npy_dtype_shape_and_event_semantics",
    "validate_final_output_with_windowed_mappings_that_are_closed_per_window",
    "preserve_cross_window_exchange_and_local_order_checks",
    "keep_streaming_sha256_bounded",
    "derive_resource_gate_from_structural_memory_bound_not_month_row_ratio",
    "prove_synthetic_and_real_slice_parity_before_any_new_full_day",
)

D6R8C_MAY_REUSE_EXISTING_JAN_CANONICAL_READ_ONLY = False
RERUN_D6R4B_JAN_CONVERSION_AUTHORIZED = False
RERUN_D6R5C_JAN_VALIDATION_AUTHORIZED = False
RAW_FEB_TO_JUL_OPEN_AUTHORIZED = False
CONVERSION_FEB_TO_JUL_AUTHORIZED = False
RUN_112_REPLAYS_AUTHORIZED = False
POLICY_EXECUTION_AUTHORIZED = False
HISTORICAL_PNL_AUTHORIZED = False
ECONOMIC_ARENA_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False
RAILWAY_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

NEXT_AFTER_D6R8B_CI = "FREEZE_D6R8C_STRUCTURALLY_BOUNDED_CONVERTER_REDESIGN_CONTRACT"

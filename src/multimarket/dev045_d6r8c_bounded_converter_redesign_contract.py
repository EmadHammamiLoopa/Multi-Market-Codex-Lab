from __future__ import annotations

EXPERIMENT_ID = "DEV045-D6R8C"
CONTRACT_ID = "DEV045-D6R8C-STRUCTURALLY-BOUNDED-CONVERTER-REDESIGN-V1"
SCHEMA_VERSION = "dev045-d6r8c-structurally-bounded-converter-redesign-contract-v1"
STATUS = "FROZEN_DESIGN_ONLY"

PARENT_BRANCH = "research/dev045-m6-bounded-converter-memory-scaling-audit"
PARENT_HEAD = "4a7df3e85f4cf495ebe244fceb03c14996d933c7"
PARENT_AUDIT_MODULE = "multimarket.dev045_d6r8b_memory_scaling_audit"
PARENT_AUDIT_REQUIRED_STATUS = "PASS_STATIC_AUDIT_REDESIGN_REQUIRED"

FROZEN_OLD_CONVERTER_PATH = "src/multimarket/dev045_d6r_bounded_converter.py"
FROZEN_OLD_CONVERTER_SHA256 = "8f79ec81c664f1762a87bfcf8757564abbe2d7f5fd89b1c83fc78de0ac4b94ac"
V2_IMPLEMENTATION_PATH = "src/multimarket/dev045_d6r8_structurally_bounded_converter.py"
OLD_CONVERTER_EDIT_AUTHORIZED = False

# Exact event/sort semantics remain unchanged.
TEMP_RECORD_ITEMSIZE_BYTES = 72
EVENT_ITEMSIZE_BYTES = 64
SORT_KEYS = {
    "exchange": ("exch_ts", "source_seq"),
    "local": ("local_ts", "source_seq"),
}
EVENT_FIELDS = (
    "ev",
    "exch_ts",
    "local_ts",
    "px",
    "qty",
    "order_id",
    "ival",
    "fval",
)
HFTBACKTEST_VERSION = "2.4.4"
BASE_LATENCY_NS = 0

# Frozen production bounds. Test fixtures may use smaller values only.
PRODUCTION_INITIAL_CHUNK_ROWS = 250_000
MERGE_FAN_IN = 8
MERGE_INPUT_WINDOW_ROWS = 16_384
MERGE_OUTPUT_BUFFER_ROWS = 65_536
CORRECTED_INPUT_WINDOW_ROWS = 32_768
FINAL_OUTPUT_BUFFER_ROWS = 65_536
VALIDATION_WINDOW_ROWS = 65_536
SHA256_BLOCK_BYTES = 1_048_576
MAX_ACTIVE_RUN_READERS = MERGE_FAN_IN

# No whole-file memmap is allowed anywhere in V2. Initial per-chunk np.save is
# permitted because the array is bounded by PRODUCTION_INITIAL_CHUNK_ROWS.
WHOLE_FILE_MMAP_ALLOWED = False
RUN_READER_MECHANISM = "NPY_HEADER_PLUS_SEQUENTIAL_NP_FROMFILE_WINDOWS"
MERGE_ALGORITHM = "FIXED_FAN_IN_HIERARCHICAL_EXTERNAL_MERGE"
MERGE_AXIS_ORDER = ("exchange", "local")
INTERMEDIATE_NPY_VERSION = (1, 0)
FINAL_NPY_VERSION = (1, 0)
FINAL_WRITER_MECHANISM = "SEQUENTIAL_NPY_HEADER_PLUS_BOUNDED_PAYLOAD_WRITES"
FINAL_OUTPUT_FULL_SHAPE_MEMMAP_ALLOWED = False
VALIDATION_MECHANISM = "SEQUENTIAL_NPY_WINDOWS_WITH_CROSS_WINDOW_STATE"

# Intermediate merge groups know their exact output row count from input NPY
# headers. A group is written to a new file, fsync/close succeeds, then only the
# consumed group inputs are unlinked. Repeat until one run remains per axis.
HIERARCHICAL_MERGE_INVARIANTS = (
    "each_group_has_at_most_8_input_runs",
    "each_input_run_reader_holds_at_most_16384_rows",
    "merge_heap_has_at_most_one_head_per_active_run",
    "merge_output_buffer_holds_at_most_65536_temp_records",
    "merge_key_is_timestamp_then_source_seq",
    "group_output_shape_equals_sum_of_input_shapes",
    "group_inputs_deleted_only_after_output_closed_successfully",
    "repeat_until_exactly_one_exchange_run_and_one_local_run",
)

# Corrected-event semantics are identical to the frozen converter. The two final
# axis runs are traversed twice using bounded readers: pass 1 counts final rows;
# pass 2 writes final NPY payload. No full-file mapping is used in either pass.
CORRECTED_EVENT_INVARIANTS = (
    "same_timestamp_pair_requires_same_source_seq",
    "equal_exchange_and_local_timestamps_emit_one_event_with_both_flags",
    "otherwise_emit_exchange_or_local_clock_event_in_frozen_order",
    "final_row_count_first_pass_only",
    "second_pass_must_write_exactly_first_pass_row_count",
)

# Final output remains in scratch until header, payload, validation and SHA256
# all succeed. Only then is it atomically promoted with os.replace. Therefore a
# failed validation cannot leave a destination canonical file behind.
FINALIZATION_INVARIANTS = (
    "output_destination_must_not_exist_before_start",
    "scratch_and_output_must_share_device",
    "partial_final_stays_in_scratch_until_validated_and_hashed",
    "validate_dtype_fields_itemsize_latency_and_event_order_in_windows",
    "preserve_cross_window_exchange_timestamp_state",
    "preserve_cross_window_local_timestamp_state",
    "sha256_is_streaming_and_bounded",
    "atomic_replace_only_after_all_postconditions_pass",
    "scratch_cleanup_on_success_or_failure",
)

# Fixed memory gates. They are deliberately independent of month/day row count.
# The 8 GiB preflight is a conservative operational gate, not a claim that V2
# needs 8 GiB. The structural design plus later synthetic/real-slice evidence
# must demonstrate much lower bounded RSS before a new full-day attempt.
GIB = 1024 ** 3
MIN_MEMAVAILABLE_BYTES = 8 * GIB
RUNTIME_RSS_ABORT_BYTES = 6 * GIB
SWAP_COUNTS_TOWARD_MEMORY_GATE = False
RESOURCE_RECHECK_IMMEDIATELY_BEFORE_CANONICAL_ATTEMPT = True
RSS_SAMPLE_POINTS = (
    "after_each_csv_chunk",
    "after_each_initial_run_flush",
    "after_each_merge_output_buffer_flush",
    "after_each_merge_group",
    "after_each_corrected_output_buffer_flush",
    "after_each_validation_window",
)

# File-descriptor gate is also row-count independent because at most fan-in run
# readers plus one writer and small fixed control files are simultaneously live.
MIN_NOFILE_SOFT = 128
MIN_NOFILE_HARD = 128

# Scratch is allowed to scale with total rows because it is disk, not resident
# process memory. The frozen conservative bound is derived structurally:
# base rows B <= about 2*raw rows R (raw event plus at most two clear records per
# snapshot batch); corrected rows F <= 2*B. Worst large-payload coexistence is
# two final 72-byte axis runs plus a 64-byte final output, <=272*B <=~544*R.
# We freeze 640 bytes/raw-row plus 16 GiB fixed reserve to cover NPY headers,
# transient group duplication and bookkeeping without relying on Jan ratios.
SCRATCH_BYTES_PER_FROZEN_RAW_ROW = 640
SCRATCH_FIXED_RESERVE_BYTES = 16 * GIB
FROZEN_RAW_ROWS = {
    "2026-02-01": 172_721_707,
    "2026-03-01": 145_757_298,
    "2026-04-01": 129_067_640,
    "2026-05-01": 104_234_425,
    "2026-06-01": 165_502_465,
    "2026-07-01": 172_067_693,
}


def required_scratch_bytes(raw_rows: int) -> int:
    if isinstance(raw_rows, bool) or not isinstance(raw_rows, int) or raw_rows <= 0:
        raise ValueError("raw_rows")
    return raw_rows * SCRATCH_BYTES_PER_FROZEN_RAW_ROW + SCRATCH_FIXED_RESERVE_BYTES


FROZEN_SCRATCH_REQUIREMENTS = {
    day: required_scratch_bytes(rows) for day, rows in FROZEN_RAW_ROWS.items()
}
MAX_FEB_JUL_REQUIRED_SCRATCH_BYTES = max(FROZEN_SCRATCH_REQUIREMENTS.values())

# D6R8D implements V2 but is synthetic-only. D6R8E must separately freeze exact
# D6R2B 10-minute Jan paths/hashes before it may reopen that already-approved
# real slice. New full-day data stays closed until implementation + synthetic
# parity + real-slice parity + resource preflight all pass.
D6R8D_SCOPE = "SYNTHETIC_ONLY"
D6R8E_SCOPE = "EXACT_D6R2B_10MIN_JAN_SLICE_ONLY_AFTER_SEPARATE_PATH_HASH_FREEZE"
D6R8D_SYNTHETIC_REQUIREMENTS = (
    "fieldwise_exact_nan_equal_against_frozen_old_converter",
    "exact_npy_sha_parity_where_header_contract_matches",
    "fixtures_force_more_than_8_runs",
    "fixtures_force_at_least_3_hierarchical_merge_levels",
    "parity_across_multiple_small_chunk_sizes",
    "rss_guard_exercised_without_trigger",
    "failure_cleanup_and_atomic_promotion_tests",
)
D6R8E_REAL_SLICE_REQUIREMENTS = (
    "exact_old_and_v2_base_row_count",
    "exact_old_and_v2_final_row_count",
    "fieldwise_exact_nan_equal",
    "exact_output_sha256_if_npy_header_equivalence_is_proven",
    "v2_peak_rss_recorded",
    "old_full_day_jan_not_rerun",
)

# D6R8C is design-only and opens no market data.
CANONICAL_ATTEMPT_COUNT = 0
RAW_DATA_OPEN_AUTHORIZED = False
JAN_CANONICAL_NPY_OPEN_AUTHORIZED = False
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

NEXT_AFTER_D6R8C_CI = "D6R8D_IMPLEMENT_V2_SYNTHETIC_ONLY"

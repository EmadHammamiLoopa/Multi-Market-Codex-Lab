from __future__ import annotations


AMENDMENT_ID = (
    "DEV045-D6R-BOUNDED-CONVERTER-V1"
)

PARENT_HEAD = (
    "cdb69569d3b7804d2a8b64a5950fc038597a218d"
)


# ------------------------------------------------------------------
# Frozen D6B result. It remains FAIL.
# D6R does not reinterpret or rerun D6B.
# ------------------------------------------------------------------

D6B_ARTIFACT_PATH = (
    "evidence/dev045_d6b_jan01_converter_preflight.json"
)

D6B_ARTIFACT_SHA256 = (
    "5e9df322620921d72b8546c08007a9c"
    "05d640e12b620fc070c12a1a3bf0fe3f1"
)

D6B_STATUS = "FAIL"
D6B_PREFLIGHT_STATUS = "PASS"
D6B_MEMORY_GATE_PASS = False

D6B_FAILURE_CLASS = (
    "RESOURCE_FEASIBILITY_ONLY"
)

D6B_CONVERTER_EXECUTED = False

OLD_D6C_WHOLE_DAY_PATH_AUTHORIZED = False
D6B_RERUN_ALLOWED = False
D6B_GATE_RELAXATION_ALLOWED = False


# ------------------------------------------------------------------
# Frozen upstream oracle.
# ------------------------------------------------------------------

HFTBACKTEST_VERSION = "2.4.4"

HFTBACKTEST_UPSTREAM_COMMIT = (
    "a244a14250b42d97fc305569c93c4117cd5e1dff"
)

UPSTREAM_TARDIS_GIT_BLOB = (
    "1ca038895d30f320561d6b28ffa13c1d788ea6bf"
)

UPSTREAM_VALIDATION_GIT_BLOB = (
    "60c6ca3458f16417e41deb3d86c40e9df3df5d7c"
)

UPSTREAM_TYPES_GIT_BLOB = (
    "4bb565d4023fe25ded069b9e12c262a7a34e4c22"
)

EVENT_DTYPE_ITEMSIZE_BYTES = 64

EVENT_DTYPE_FIELDS = (
    "ev",
    "exch_ts",
    "local_ts",
    "px",
    "qty",
    "order_id",
    "ival",
    "fval",
)


# ------------------------------------------------------------------
# Existing project lineage remains frozen.
# ------------------------------------------------------------------

FEED_MODULE_GIT_BLOB = (
    "8bf7d620ce54cfa0ef759e9f8a866cea39570bc8"
)

M4_ADAPTER_GIT_BLOB = (
    "7f6a321b4512dd1ec1edf94c79416e176ee75e1c"
)


# ------------------------------------------------------------------
# Amendment rationale.
# ------------------------------------------------------------------

AMENDMENT_REASON = (
    "WHOLE_DAY_CONVERTER_RESOURCE_INFEASIBLE"
)

AMENDMENT_CHANGES_MARKET_SEMANTICS = False
AMENDMENT_CHANGES_POLICY_SEMANTICS = False
AMENDMENT_CHANGES_FEES = False
AMENDMENT_CHANGES_LATENCY = False
AMENDMENT_CHANGES_ECONOMIC_GATES = False

AMENDMENT_IS_MEMORY_EXECUTION_PATH_ONLY = True


# ------------------------------------------------------------------
# Exact raw conversion semantics to preserve.
# ------------------------------------------------------------------

INPUT_FILE_ORDER = (
    "trades",
    "incremental_book_L2",
)

TIMESTAMP_SCALE_US_TO_NS = 1000

BASE_LATENCY = 0
SNAPSHOT_MODE = "process"

TRADE_SIDE_BUY = "BUY_EVENT|TRADE_EVENT"
TRADE_SIDE_SELL = "SELL_EVENT|TRADE_EVENT"

DEPTH_SIDE_BID = "BUY_EVENT|DEPTH_EVENT"
DEPTH_SIDE_ASK = "SELL_EVENT|DEPTH_EVENT"

DEPTH_ZERO_QTY_PRESERVED = True

SNAPSHOT_BATCH_STATE_MUST_CROSS_CHUNK_BOUNDARIES = True

SNAPSHOT_FLUSH_ORDER = (
    "BID_CLEAR",
    "BID_SNAPSHOT_ROWS",
    "ASK_CLEAR",
    "ASK_SNAPSHOT_ROWS",
    "CURRENT_NON_SNAPSHOT_DEPTH_ROW",
)

SNAPSHOT_CLEAR_TIMESTAMP_SOURCE = (
    "FIRST_SNAPSHOT_ROW_OF_SIDE"
)

SNAPSHOT_CLEAR_PRICE_SOURCE = (
    "LAST_SNAPSHOT_ROW_OF_SIDE"
)

SNAPSHOT_CLEAR_QTY = 0.0


# ------------------------------------------------------------------
# Source sequence contract.
#
# Upstream tardis.convert first appends ALL trades,
# then converted depth events. Stable mergesort preserves
# this original sequence for equal timestamp keys.
# ------------------------------------------------------------------

SOURCE_SEQUENCE_REQUIRED = True

SOURCE_SEQUENCE_DOMAIN = (
    "MONOTONIC_UINT64"
)

SOURCE_SEQUENCE_ORDER = (
    "ALL_CONVERTED_TRADE_EVENTS_FIRST_"
    "THEN_ALL_CONVERTED_DEPTH_EVENTS"
)

SOURCE_SEQUENCE_WRITTEN_TO_FINAL_OUTPUT = False

SOURCE_SEQUENCE_TEMPORARY_SIDECAR_ONLY = True


# ------------------------------------------------------------------
# Bounded-memory implementation.
# ------------------------------------------------------------------

PRODUCTION_RAW_CHUNK_ROWS = 500_000

TEST_CHUNK_OVERRIDE_ALLOWED = True
TEST_CHUNK_MIN_ROWS = 1

WHOLE_DAY_POLARS_READ_ALLOWED = False
WHOLE_DAY_NUMPY_PREALLOCATION_ALLOWED = False

STREAM_GZIP_CSV_ALLOWED = True

TEMP_RUN_FORMAT = "NUMPY_NPY"

TEMP_SORT_RECORD_FIELDS = (
    "source_seq",
    "ev",
    "exch_ts",
    "local_ts",
    "px",
    "qty",
    "order_id",
    "ival",
    "fval",
)

EXCHANGE_SORT_KEYS = (
    "exch_ts",
    "source_seq",
)

LOCAL_SORT_KEYS = (
    "local_ts",
    "source_seq",
)

EXTERNAL_STABLE_SORT_REQUIRED = True

SORT_TIE_BREAKER_IS_SOURCE_SEQUENCE = True


# ------------------------------------------------------------------
# correct_local_timestamp parity.
#
# D5B already proved local_ts >= exch_ts for every raw row.
# base_latency is frozen at zero.
# Therefore upstream correction must be identity.
# ------------------------------------------------------------------

NEGATIVE_RAW_LATENCY_ALLOWED = False

LOCAL_TIMESTAMP_CORRECTION_MODE = (
    "IDENTITY_ASSERT_NONNEGATIVE"
)


# ------------------------------------------------------------------
# Exact correct_event_order parity.
#
# Two globally sorted streams are merged using the frozen
# upstream branch logic. source_seq is used only to recreate
# stable ordering inside equal timestamp groups.
# ------------------------------------------------------------------

FINAL_ORDER_ALGORITHM = (
    "UPSTREAM_CORRECT_EVENT_ORDER_EXACT"
)

FINAL_MERGE_REQUIRES_TWO_GLOBAL_STREAMS = True

EXCHANGE_STREAM_GLOBAL_ORDER = (
    "exch_ts_then_source_seq"
)

LOCAL_STREAM_GLOBAL_ORDER = (
    "local_ts_then_source_seq"
)

EXACT_TIMESTAMP_PAIR_REQUIRES_SAME_SOURCE_SEQ = True

EXCH_EVENT_FLAG_SEMANTICS_PRESERVED = True
LOCAL_EVENT_FLAG_SEMANTICS_PRESERVED = True


# ------------------------------------------------------------------
# Disk-backed final output.
# ------------------------------------------------------------------

FINAL_OUTPUT_FORMAT = (
    "NUMPY_NPY_EVENT_DTYPE"
)

FINAL_OUTPUT_DISK_BACKED = True
FINAL_OUTPUT_MEMORY_MAP_COMPATIBLE = True

FINAL_OUTPUT_CONTAINS_SOURCE_SEQ = False

FINAL_OUTPUT_TWO_PASS_MERGE = True

FIRST_MERGE_PASS_COUNTS_ROWS = True
SECOND_MERGE_PASS_WRITES_ROWS = True

FINAL_OUTPUT_MUST_PASS_M4_VALIDATE_EVENTS = True

FINAL_OUTPUT_MUST_MATCH_EVENT_DTYPE_FIELDS = True
FINAL_OUTPUT_MUST_MATCH_EVENT_DTYPE_ITEMSIZE = True

FINAL_OUTPUT_FILE_NOT_COMMITTED_TO_GIT = True

FINAL_OUTPUT_SHA256_EVIDENCE_REQUIRED = True


# ------------------------------------------------------------------
# Parity gates before any full-day bounded conversion.
# ------------------------------------------------------------------

SYNTHETIC_ORACLE_PARITY_REQUIRED = True

SYNTHETIC_PARITY_COMPARISON = (
    "FIELDWISE_EXACT_NAN_EQUAL"
)

SYNTHETIC_FIXTURE_REQUIREMENTS = (
    "TRADE_BUY_SELL",
    "DEPTH_BID_ASK",
    "ZERO_QTY_DELETE",
    "SOD_SNAPSHOT",
    "SNAPSHOT_CROSSES_CHUNK_BOUNDARY",
    "DUPLICATE_TIMESTAMPS",
    "OUT_OF_ORDER_EXCHANGE_TIMESTAMP",
    "NONDECREASING_LOCAL_TIMESTAMP",
    "EQUAL_EXCH_LOCAL_PAIR",
)

SYNTHETIC_PARITY_MUST_TEST_MULTIPLE_CHUNK_SIZES = True

SYNTHETIC_TEST_CHUNK_SIZES = (
    1,
    2,
    3,
    7,
)


# Fixed real parity slice. Selection is temporal only.
REAL_PARITY_REQUIRED = True

REAL_PARITY_DAY = "2026-01-01"
REAL_PARITY_SYMBOL = "BTCUSDT"

REAL_PARITY_WINDOW_START_SECONDS = 0
REAL_PARITY_WINDOW_END_SECONDS = 600

REAL_PARITY_SELECTION_USES_PNL = False
REAL_PARITY_SELECTION_USES_POLICY_RESULT = False

REAL_PARITY_INPUTS = (
    "trades/BTCUSDT/2026-01-01.csv.gz",
    "incremental_book_L2/BTCUSDT/2026-01-01.csv.gz",
)

REAL_PARITY_ORACLE = (
    "FROZEN_UPSTREAM_TARDIS_CONVERT"
)

REAL_PARITY_COMPARISON = (
    "FIELDWISE_EXACT_NAN_EQUAL"
)

REAL_PARITY_MUST_END_OUTSIDE_SNAPSHOT_BATCH = True


# ------------------------------------------------------------------
# Full-day bounded canary remains closed until all parity gates pass.
# ------------------------------------------------------------------

FULL_DAY_CANARY_DAY = "2026-01-01"

FULL_DAY_BOUNDED_CONVERSION_REQUIRES = (
    "IMPLEMENTATION_FROZEN_GREEN",
    "SYNTHETIC_ORACLE_PARITY_FROZEN_GREEN",
    "REAL_10MIN_ORACLE_PARITY_FROZEN_GREEN",
    "RESOURCE_PREFLIGHT_FROZEN_GREEN",
)

FULL_DAY_BOUNDED_CONVERSION_AUTHORIZED_NOW = False


# Resource gates for later full-day execution.
RESOURCE_PREFLIGHT_REQUIRED = True

RESOURCE_PREFLIGHT_MEMORY_RULE = (
    "MEMAVAILABLE_GTE_4X_PEAK_PROCESS_RSS_"
    "FROM_FIXED_REAL_PARITY_SLICE"
)

RESOURCE_PREFLIGHT_DISK_RULE = (
    "FREE_SCRATCH_BYTES_GTE_6X_"
    "BASE_EVENT_BUFFER_BYTES"
)

RESOURCE_PREFLIGHT_SWAP_COUNTS_AS_MEMORY = False


# ------------------------------------------------------------------
# Explicitly closed surfaces.
# ------------------------------------------------------------------

NETWORK_MARKET_DATA_ACQUISITION_ALLOWED = False

RAW_BYTES_MODIFICATION_ALLOWED = False

AUG01_ALLOWED = False
SEP_PLUS_ALLOWED = False
NON_BTC_ALLOWED = False

POLICY_EXECUTION_ALLOWED = False
M01_M08_EXECUTION_ALLOWED = False

HISTORICAL_POLICY_REPLAY_ALLOWED = False
HISTORICAL_PNL_ALLOWED = False

ECONOMIC_ARENA_ALLOWED = False
CANONICAL_PNL_WRITE_ALLOWED = False

RAILWAY_ALLOWED = False
LIVE_TRADING_ALLOWED = False

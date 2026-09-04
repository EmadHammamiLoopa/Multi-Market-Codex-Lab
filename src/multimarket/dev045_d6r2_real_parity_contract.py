from __future__ import annotations


CONTRACT_ID = (
    "DEV045-D6R2-REAL-10MIN-PARITY-V1"
)

PARENT_BRANCH = (
    "research/dev045-m6-bounded-converter-synthetic-parity"
)

PARENT_HEAD = (
    "c0647ef3ad32db199401643aa0324fe3e12133b8"
)


# ------------------------------------------------------------------
# Frozen canonical synthetic parity prerequisite.
# ------------------------------------------------------------------

D6R1B_ARTIFACT_PATH = (
    "evidence/dev045_d6r1b_canonical_synthetic_parity.json"
)

D6R1B_ARTIFACT_SHA256 = (
    "3788b76b48b98efc4b1d9491d35c6c7"
    "f5620de8308fc017f2d16942027168fdd"
)

D6R1B_STATUS = "PASS"
D6R1B_CANONICAL_ATTEMPT = 1

D6R1B_REQUIRED_CHUNKS = (
    1,
    2,
    3,
    7,
)


# ------------------------------------------------------------------
# Frozen bounded implementation.
# ------------------------------------------------------------------

IMPLEMENTATION_PATH = (
    "src/multimarket/dev045_d6r_bounded_converter.py"
)

IMPLEMENTATION_SHA256 = (
    "8f79ec81c664f1762a87bfcf8757564a"
    "bbe2d7f5fd89b1c83fc78de0ac4b94ac"
)

IMPLEMENTATION_TEST_PATH = (
    "tests/test_dev045_d6r_bounded_converter.py"
)

IMPLEMENTATION_TEST_SHA256 = (
    "861a0f18e13933d800790e96629779bc3"
    "6a2b0163e422ce5918de07cd2b0a7d4"
)

PRODUCTION_CHUNK_ROWS = 500_000


# ------------------------------------------------------------------
# Frozen raw lineage.
# ------------------------------------------------------------------

D4_MANIFEST_PATH = (
    "evidence/dev045_d4_raw_provenance.tsv"
)

D4_MANIFEST_SHA256 = (
    "7fa6cf76ee8c6da98c5758756c887f0f"
    "b7b4d2e5eaf6b0e9f87551dce9981c12"
)

D5B_ARTIFACT_PATH = (
    "evidence/dev045_d5b_full_stream_integrity.json"
)

D5B_ARTIFACT_SHA256 = (
    "51af9bbf48d36de43ee7ce8337f6ef77"
    "2cd74c555c1bc2f85db485d3d463d96a"
)

D5B_REQUIRED_STATUS = "PASS"
D5B_REQUIRED_TOTAL_VIOLATIONS = 0


RAW_ROOT = (
    "/home/emadh/Multi-Market/data/"
    "v23_phase0dl_l2_raw"
)

EXCHANGE = "binance-futures"
SYMBOL = "BTCUSDT"
DAY = "2026-01-01"

TRADE_RELATIVE_PATH = (
    "trades/BTCUSDT/2026-01-01.csv.gz"
)

DEPTH_RELATIVE_PATH = (
    "incremental_book_L2/BTCUSDT/2026-01-01.csv.gz"
)


# ------------------------------------------------------------------
# Fixed real parity window.
#
# Selection is by local_timestamp only.
# The interval is left-inclusive, right-exclusive.
# No PnL/model/policy information selected this window.
# ------------------------------------------------------------------

WINDOW_START_UTC = (
    "2026-01-01T00:00:00Z"
)

WINDOW_END_UTC = (
    "2026-01-01T00:10:00Z"
)

WINDOW_START_LOCAL_TIMESTAMP_US = (
    1_767_225_600_000_000
)

WINDOW_END_LOCAL_TIMESTAMP_US = (
    1_767_226_200_000_000
)

WINDOW_DURATION_SECONDS = 600

SELECTION_FIELD = "local_timestamp"
SELECTION_LEFT_INCLUSIVE = True
SELECTION_RIGHT_EXCLUSIVE = True

SELECTION_USES_EXCHANGE_TIMESTAMP = False
SELECTION_USES_PNL = False
SELECTION_USES_POLICY_RESULT = False
SELECTION_USES_MODEL_OUTPUT = False
SELECTION_USES_FUTURE_DATA = False

WINDOW_EXTENSION_ALLOWED = False
WINDOW_SHRINK_ALLOWED = False


# ------------------------------------------------------------------
# Extraction semantics.
# ------------------------------------------------------------------

EXTRACTION_MODE = (
    "SEQUENTIAL_GZIP_CSV_STREAM"
)

PHYSICAL_LOCAL_TIMESTAMP_MONOTONIC_REQUIRED = True

ROW_KEEP_RULE = (
    "WINDOW_START_US_LE_LOCAL_TIMESTAMP_LT_WINDOW_END_US"
)

STOP_AT_FIRST_LOCAL_TIMESTAMP_GTE_WINDOW_END = True

ORIGINAL_HEADER_PRESERVED = True
ORIGINAL_ROW_TEXT_PRESERVED = True
ORIGINAL_ROW_ORDER_PRESERVED = True

TRADE_HEADER = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "id",
    "side",
    "price",
    "amount",
)

DEPTH_HEADER = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "is_snapshot",
    "side",
    "price",
    "amount",
)

TEMP_SLICE_FORMAT = "CSV_GZIP"
TEMP_GZIP_MTIME = 0

TEMP_SLICE_FILES_COMMITTED = False

TRADE_SLICE_NONEMPTY_REQUIRED = True
DEPTH_SLICE_NONEMPTY_REQUIRED = True

SLICE_EXCHANGE_REQUIRED = EXCHANGE
SLICE_SYMBOL_REQUIRED = SYMBOL


# ------------------------------------------------------------------
# Snapshot boundary gate.
#
# The time window is immutable.
# If it ends inside a snapshot batch, parity execution FAILS.
# We do not extend the slice to make it pass.
# ------------------------------------------------------------------

DEPTH_INITIAL_SNAPSHOT_REQUIRED = True

DEPTH_INITIAL_SNAPSHOT_MUST_BEGIN_AT_FIRST_DEPTH_ROW = True

DEPTH_AT_LEAST_ONE_SNAPSHOT_ROW_REQUIRED = True

DEPTH_END_OUTSIDE_SNAPSHOT_BATCH_REQUIRED = True

TRAILING_SNAPSHOT_CAUSES_FAIL = True

WINDOW_MAY_NOT_BE_EXTENDED_FOR_SNAPSHOT = True


# ------------------------------------------------------------------
# Frozen upstream oracle.
# ------------------------------------------------------------------

HFTBACKTEST_VERSION = "2.4.4"

HFTBACKTEST_UPSTREAM_COMMIT = (
    "a244a14250b42d97fc305569c93c4117cd5e1dff"
)

UPSTREAM_TARDIS_CONVERTER_GIT_BLOB = (
    "1ca038895d30f320561d6b28ffa13c1d788ea6bf"
)

ORACLE_CONVERTER = (
    "hftbacktest.data.utils.tardis.convert"
)

ORACLE_FILE_ORDER = (
    "trades",
    "incremental_book_L2",
)

ORACLE_OUTPUT_FILENAME = None

ORACLE_BASE_LATENCY = 0
ORACLE_SNAPSHOT_MODE = "process"

ORACLE_BUFFER_SIZE_RULE = (
    "TRADE_ROWS_PLUS_DEPTH_ROWS_PLUS_"
    "2X_SNAPSHOT_BATCHES_PLUS_32"
)

ORACLE_SNAPSHOT_BUFFER_SIZE_RULE = (
    "MAX_MAX_SNAPSHOT_SIDE_ROWS_PLUS_16_OR_1024"
)

ORACLE_NETWORK_ACQUISITION_ALLOWED = False


# ------------------------------------------------------------------
# Frozen bounded candidate.
# ------------------------------------------------------------------

BOUNDED_CONVERTER = (
    "multimarket.dev045_d6r_bounded_converter.convert_tardis"
)

BOUNDED_CHUNK_ROWS = PRODUCTION_CHUNK_ROWS

BOUNDED_OUTPUT_FORMAT = "NUMPY_NPY_EVENT_DTYPE"
BOUNDED_OUTPUT_DISK_BACKED = True

BOUNDED_SCRATCH_DIRECTORY = (
    "FRESH_TEMPORARY_DIRECTORY"
)

BOUNDED_NETWORK_ACQUISITION_ALLOWED = False


# ------------------------------------------------------------------
# Process isolation.
#
# Oracle and bounded conversions execute in separate fresh Python
# subprocesses to avoid cross-contamination of memory measurements.
# ------------------------------------------------------------------

ORACLE_EXECUTION_PROCESS = (
    "FRESH_PYTHON_SUBPROCESS"
)

BOUNDED_EXECUTION_PROCESS = (
    "FRESH_PYTHON_SUBPROCESS"
)

ORACLE_ARRAY_TEMP_NPY_ALLOWED = True

ORACLE_TEMP_NPY_IS_NOT_CONVERTER_OUTPUT = True


# ------------------------------------------------------------------
# Bounded resource observation.
#
# This does not yet authorize a full day.
# It only records an empirical bounded-converter peak RSS from the
# fixed real parity slice for the later separately frozen resource gate.
# ------------------------------------------------------------------

PEAK_RSS_MEASUREMENT_REQUIRED = True

PEAK_RSS_TARGET = (
    "BOUNDED_CONVERTER_FRESH_SUBPROCESS"
)

PEAK_RSS_SOURCE = (
    "resource.getrusage(resource.RUSAGE_SELF).ru_maxrss"
)

PEAK_RSS_PLATFORM = "LINUX"
PEAK_RSS_SOURCE_UNIT = "KIB"

PEAK_RSS_BYTES_RULE = (
    "RUSAGE_MAXRSS_X_1024"
)

ORACLE_PEAK_RSS_IS_RESOURCE_GATE_INPUT = False
BOUNDED_PEAK_RSS_IS_RESOURCE_GATE_INPUT = True

PEAK_RSS_OBSERVATION_AUTHORIZES_FULL_DAY = False


# ------------------------------------------------------------------
# Exact parity gate.
# ------------------------------------------------------------------

PARITY_REQUIRED = True

PARITY_COMPARISON = (
    "FIELDWISE_EXACT_NAN_EQUAL"
)

PARITY_ROW_REORDERING_ALLOWED = False
PARITY_FLOAT_TOLERANCE_ALLOWED = False

PARITY_REQUIRED_FIELDS = (
    "ev",
    "exch_ts",
    "local_ts",
    "px",
    "qty",
    "order_id",
    "ival",
    "fval",
)

PARITY_SHAPE_EQUAL_REQUIRED = True
PARITY_DTYPE_EQUAL_REQUIRED = True
PARITY_ITEMSIZE_REQUIRED = 64

ORACLE_OUTPUT_SHA256_RECORDED = True
BOUNDED_OUTPUT_SHA256_RECORDED = True

SLICE_TRADE_SHA256_RECORDED = True
SLICE_DEPTH_SHA256_RECORDED = True


# ------------------------------------------------------------------
# First-result freeze discipline.
# ------------------------------------------------------------------

CANONICAL_REAL_PARITY_ATTEMPTS = 1

FIRST_RESULT_FROZEN_PASS_OR_FAIL = True
REAL_PARITY_RERUN_AFTER_RESULT_ALLOWED = False

RESULT_EVIDENCE_PATH = (
    "evidence/dev045_d6r2b_real_10min_parity.json"
)


# ------------------------------------------------------------------
# Even a PASS does NOT authorize full-day conversion directly.
# A separately frozen resource preflight is mandatory next.
# ------------------------------------------------------------------

FULL_DAY_CONVERSION_AUTHORIZED_NOW = False

REAL_PARITY_PASS_NEXT_GATE = (
    "FREEZE_FULL_DAY_RESOURCE_PREFLIGHT_CONTRACT"
)

RESOURCE_PREFLIGHT_REQUIRED_AFTER_REAL_PARITY = True


# ------------------------------------------------------------------
# Explicit closed surfaces.
# ------------------------------------------------------------------

RAW_BYTES_MODIFICATION_ALLOWED = False

OTHER_REAL_WINDOWS_ALLOWED = False
OTHER_DAYS_ALLOWED = False

AUG01_ALLOWED = False
SEP_PLUS_ALLOWED = False
NON_BTC_ALLOWED = False

POLICY_EXECUTION_ALLOWED = False
M01_M08_EXECUTION_ALLOWED = False

HISTORICAL_POLICY_REPLAY_ALLOWED = False
HISTORICAL_PNL_ALLOWED = False

ECONOMIC_ARENA_ALLOWED = False
CANONICAL_PNL_WRITE_ALLOWED = False

NETWORK_MARKET_DATA_ACQUISITION_ALLOWED = False

RAILWAY_ALLOWED = False
LIVE_TRADING_ALLOWED = False


# D6R2A freezes this contract only.
REAL_RAW_CONTENT_OPEN_AUTHORIZED_BY_D6R2A = False
REAL_PARITY_EXECUTION_AUTHORIZED_BY_D6R2A = False

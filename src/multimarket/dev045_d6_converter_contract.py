from __future__ import annotations


CONTRACT_ID = (
    "DEV045-D6-CONVERTER-VALIDATION-V1"
)

PARENT_HEAD = (
    "d8d9935579b703d10107435d9d14c3be0be49654"
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


# Frozen project-side converter lineage.
FEED_MODULE_PATH = (
    "src/multimarket/dev045_m6_tardis_feed.py"
)

FEED_MODULE_GIT_BLOB = (
    "8bf7d620ce54cfa0ef759e9f8a866cea39570bc8"
)

FEED_TEST_GIT_BLOB = (
    "21b7d01db28da4924dec13aa611dd87f0bdcb76f"
)

M4_ADAPTER_GIT_BLOB = (
    "7f6a321b4512dd1ec1edf94c79416e176ee75e1c"
)

PATCH_SCRIPT_GIT_BLOB = (
    "3b839a2b87d3399d573db5777a7db030e579b291"
)


# Exact upstream simulator/converter identity.
HFTBACKTEST_VERSION = "2.4.4"

HFTBACKTEST_UPSTREAM_COMMIT = (
    "a244a14250b42d97fc305569c93c4117cd5e1dff"
)

UPSTREAM_TARDIS_PATH = (
    "py-hftbacktest/"
    "hftbacktest/data/utils/tardis.py"
)

UPSTREAM_TARDIS_GIT_BLOB = (
    "1ca038895d30f320561d6b28ffa13c1d788ea6bf"
)

M1_PATCHSET = (
    "ISSUE_312_EXACT_QTY_CLEANUP,"
    "ISSUE_316_PARTIAL_LOCAL_ACCOUNTING"
)

TARDIS_CONVERTER_CHANGED_BY_M1_PATCH = False


# Exact real-data canary.
CANARY_DAY = "2026-01-01"
CANARY_SYMBOL = "BTCUSDT"
CANARY_EXCHANGE = "binance-futures"

CANARY_SELECTION_REASON = (
    "MINIMUM_D5B_TOTAL_ROWS_RESOURCE_SAFETY_ONLY"
)

CANARY_SELECTED_FROM_ECONOMIC_RESULT = False
CANARY_PNL_CONSULTED = False


# Exact converter call semantics already implemented
# by dev045_m6_tardis_feed.convert_day().
INPUT_ORDER = (
    "trades",
    "incremental_book_L2",
)

SNAPSHOT_MODE = "process"
BASE_LATENCY = 0
OUTPUT_FILENAME = None

NETWORK_ACQUISITION_ALLOWED = False
RAW_BYTES_MODIFICATION_ALLOWED = False


# Upstream event dtype at the frozen commit:
# 8 aligned 8-byte fields = 64 bytes/event.
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

EVENT_DTYPE_ITEMSIZE_BYTES = 64


# D6B is preflight/resource feasibility only.
D6B_CONVERTER_EXECUTION_ALLOWED = False

D6B_RAW_SCOPE = (
    ("trades", "BTCUSDT", CANARY_DAY),
    ("incremental_book_L2", "BTCUSDT", CANARY_DAY),
)

D6B_REQUIRE_FEED_PREFLIGHT = True

D6B_REQUIRE_BUFFER_SIZE_MEASUREMENT = True
D6B_REQUIRE_SNAPSHOT_BUFFER_MEASUREMENT = True

D6B_REQUIRE_MACHINE_MEMORY_MEASUREMENT = True

# Engineering safety margin, not an economic gate.
# Converter allocates the event buffer plus Polars
# frames and temporary structured arrays.
MEMORY_SAFETY_MULTIPLIER = 4

D6B_REQUIRE_AVAILABLE_MEMORY_GTE = (
    "MEMORY_SAFETY_MULTIPLIER_X_"
    "MANDATORY_EVENT_PREALLOCATION"
)


# D6C may execute only after frozen D6B PASS.
D6C_REQUIRES_FROZEN_D6B_PASS = True
D6C_REAL_CONVERTER_EXECUTION_ALLOWED = True

D6C_REAL_SCOPE = D6B_RAW_SCOPE

D6C_IN_MEMORY_ONLY = True
D6C_NPZ_WRITE_ALLOWED = False

D6C_REQUIRE_M4_EVENT_VALIDATION = True
D6C_REQUIRE_NONEMPTY_OUTPUT = True

D6C_REQUIRE_TRADE_EVENT = True
D6C_REQUIRE_DEPTH_SNAPSHOT_EVENT = True

D6C_REQUIRE_LOCAL_GTE_EXCHANGE = True
D6C_REQUIRE_LOCAL_TIMESTAMP_CANARY_DAY = True

D6C_REQUIRE_EVENT_DTYPE_FIELDS = True
D6C_REQUIRE_EVENT_DTYPE_ITEMSIZE = True


# With snapshot_mode=process, converter output is
# raw trades + depth rows plus at most two clear
# events per snapshot batch.
D6C_OUTPUT_ROW_LOWER_BOUND = (
    "TRADES_ROWS_PLUS_DEPTH_ROWS"
)

D6C_OUTPUT_ROW_UPPER_BOUND = (
    "TRADES_ROWS_PLUS_DEPTH_ROWS_PLUS_"
    "2_X_SNAPSHOT_BATCHES"
)


# D6 is technical validation only.
HFTBACKTEST_POLICY_EXECUTION_ALLOWED = False
M01_M08_EXECUTION_ALLOWED = False

HISTORICAL_POLICY_REPLAY_ALLOWED = False
HISTORICAL_PNL_ALLOWED = False

ECONOMIC_ARENA_ALLOWED = False
CANONICAL_PNL_WRITE_ALLOWED = False

AUG01_ALLOWED = False
SEP_PLUS_ALLOWED = False
NON_BTC_ALLOWED = False

RAILWAY_ALLOWED = False
LIVE_TRADING_ALLOWED = False

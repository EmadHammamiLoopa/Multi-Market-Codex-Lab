from __future__ import annotations


CONTRACT_ID = "DEV045-D5-FULL-STREAM-INTEGRITY-V1"

PARENT_HEAD = (
    "47d45f011c15f9d37089bf2627228a524a63e1cf"
)

D4_MANIFEST_PATH = (
    "evidence/dev045_d4_raw_provenance.tsv"
)

D4_MANIFEST_SHA256 = (
    "7fa6cf76ee8c6da98c5758756c887f0f"
    "b7b4d2e5eaf6b0e9f87551dce9981c12"
)


EXPECTED_EXCHANGE = "binance-futures"
EXPECTED_SYMBOL = "BTCUSDT"

EXPECTED_DAYS = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)

EXPECTED_KINDS = (
    "trades",
    "incremental_book_L2",
)

EXPECTED_FILE_COUNT = 14

EXPECTED_STREAMS = tuple(
    (kind, day)
    for day in EXPECTED_DAYS
    for kind in EXPECTED_KINDS
)


EXPECTED_HEADERS = {
    "trades": (
        "exchange",
        "symbol",
        "timestamp",
        "local_timestamp",
        "id",
        "side",
        "price",
        "amount",
    ),
    "incremental_book_L2": (
        "exchange",
        "symbol",
        "timestamp",
        "local_timestamp",
        "is_snapshot",
        "side",
        "price",
        "amount",
    ),
}

EXPECTED_FIELD_COUNT = 8

ALLOWED_SIDES = {
    "trades": frozenset(
        {
            "buy",
            "sell",
        }
    ),
    "incremental_book_L2": frozenset(
        {
            "bid",
            "ask",
        }
    ),
}


# Numeric/content semantics.
REQUIRE_FINITE_PRICE = True
REQUIRE_FINITE_AMOUNT = True

TRADES_PRICE_RULE = ">0"
TRADES_AMOUNT_RULE = ">0"

DEPTH_PRICE_RULE = ">0"
DEPTH_AMOUNT_RULE = ">=0"

DEPTH_ZERO_AMOUNT_ALLOWED = True
DEPTH_ZERO_AMOUNT_MEANING = "LEVEL_DELETE_OR_REMOVE"


# Timestamp semantics.
REQUIRE_INTEGER_TIMESTAMPS = True
REQUIRE_POSITIVE_TIMESTAMPS = True

# For every row:
# local_timestamp must not precede exchange timestamp.
REQUIRE_LOCAL_GTE_EXCHANGE = True

# File order must be causal by local observation time.
# Equality is allowed.
REQUIRE_LOCAL_TIMESTAMP_NONDECREASING = True

# IMPORTANT:
# Exchange timestamps themselves are NOT required to be monotonic.
REQUIRE_EXCHANGE_TIMESTAMP_NONDECREASING = False

# The UTC date derived from exchange timestamp must match
# the frozen manifest day.
REQUIRE_EXCHANGE_UTC_DAY_MATCH = True


# Depth-specific semantics.
DEPTH_SNAPSHOT_DOMAIN = frozenset(
    {
        "true",
        "false",
    }
)

REQUIRE_DEPTH_SNAPSHOT_BOOLEAN = True
REQUIRE_DEPTH_AT_LEAST_ONE_SNAPSHOT_PER_FILE = True


# Structural semantics.
REQUIRE_NONEMPTY_FILE = True
REQUIRE_EXACT_HEADER = True
REQUIRE_EXACT_FIELD_COUNT = True
REQUIRE_GZIP_READ_TO_EOF = True
REQUIRE_NO_SYMLINK = True

# D4 provenance remains authoritative.
REQUIRE_D4_BYTE_SIZE_IDENTITY = True
REQUIRE_D4_SHA256_IDENTITY = True


# Explicitly NOT D5 integrity gates.
REQUIRE_TRADE_ID_UNIQUENESS = False
REQUIRE_ROW_UNIQUENESS = False
REQUIRE_EXCHANGE_TIMESTAMP_MONOTONICITY = False

# These may be studied later, but cannot be silently
# introduced into D5 after seeing full-stream results.
NON_GATES = (
    "trade_id_uniqueness",
    "row_uniqueness",
    "exchange_timestamp_monotonicity",
    "economic_performance",
    "fill_quality",
    "policy_pnl",
)


# Scope containment.
FULL_SCAN_MAY_OPEN_ONLY_FROZEN_D4_STREAMS = True
AUG01_ALLOWED = False
SEP_PLUS_ALLOWED = False
NON_BTC_ALLOWED = False
NETWORK_MARKET_DATA_ACQUISITION_ALLOWED = False

TARDIS_CONVERTER_ALLOWED = False
HFTBACKTEST_ALLOWED = False
HISTORICAL_POLICY_REPLAY_ALLOWED = False
HISTORICAL_PNL_ALLOWED = False
ECONOMIC_ARENA_ALLOWED = False
CANONICAL_PNL_WRITE_ALLOWED = False
RAILWAY_ALLOWED = False
LIVE_TRADING_ALLOWED = False


# D5B execution discipline.
D5B_CANONICAL_FULL_SCAN = True

D5B_FAILURE_POLICY = (
    "FREEZE_FIRST_RESULT_AND_FIX_ONLY_A_PREDECLARED_"
    "IMPLEMENTATION_OR_CONTRACT_BUG_WITH_EXPLICIT_LINEAGE"
)


# D5A observations are descriptive only.
D5A_SAMPLE_ROWS_PER_FILE = 256
D5A_DEPTH_ZERO_AMOUNT_ROWS_OBSERVED = 114

D5A_ZERO_AMOUNT_COUNT_IS_ACCEPTANCE_THRESHOLD = False
D5A_ZERO_AMOUNT_COUNT_IS_EXPECTED_FULL_COUNT = False

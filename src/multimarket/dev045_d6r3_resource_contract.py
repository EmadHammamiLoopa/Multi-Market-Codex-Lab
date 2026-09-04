from __future__ import annotations


CONTRACT_ID = (
    "DEV045-D6R3-FULL-DAY-RESOURCE-PREFLIGHT-V1"
)

PARENT_BRANCH = (
    "research/dev045-m6-real-10min-parity"
)

PARENT_HEAD = (
    "4ff70ec50e39da432a70bf0444907f536586ed3e"
)


# ------------------------------------------------------------------
# Frozen real-parity prerequisite.
# ------------------------------------------------------------------

D6R2B_ARTIFACT_PATH = (
    "evidence/dev045_d6r2b_real_10min_parity.json"
)

D6R2B_ARTIFACT_SHA256 = (
    "bf4fe15cf1af2b1c90beef39c4d337fe"
    "4676411209b4e6ba4034c97b6ff90ca1"
)

D6R2B_STATUS = "PASS"
D6R2B_CANONICAL_ATTEMPT = 1
D6R2B_EXACT_PARITY_PASS = True

BOUNDED_REAL_SLICE_PEAK_RSS_BYTES = 451_440_640

BOUNDED_REAL_SLICE_PEAK_RSS_GIB = (
    BOUNDED_REAL_SLICE_PEAK_RSS_BYTES
    / (1024 ** 3)
)


# ------------------------------------------------------------------
# Frozen Jan-01 geometry.
#
# D6B remains a frozen FAIL for the OLD whole-day in-memory path.
# Only its already-frozen preflight counts are reused.
# ------------------------------------------------------------------

D6B_ARTIFACT_PATH = (
    "evidence/dev045_d6b_jan01_converter_preflight.json"
)

D6B_ARTIFACT_SHA256 = (
    "5e9df322620921d72b8546c08007a9c05"
    "d640e12b620fc070c12a1a3bf0fe3f1"
)

D6B_STATUS_REMAINS = "FAIL"

FULL_DAY = "2026-01-01"
FULL_DAY_SYMBOL = "BTCUSDT"

FULL_DAY_TRADE_ROWS = 1_056_983
FULL_DAY_DEPTH_ROWS = 62_609_291
FULL_DAY_DEPTH_SNAPSHOT_BATCHES = 1

EVENT_DTYPE_ITEMSIZE_BYTES = 64

# One bid clear + one ask clear per processed snapshot batch.
FULL_DAY_BASE_EVENT_ROWS = (
    FULL_DAY_TRADE_ROWS
    + FULL_DAY_DEPTH_ROWS
    + 2 * FULL_DAY_DEPTH_SNAPSHOT_BATCHES
)

assert FULL_DAY_BASE_EVENT_ROWS == 63_666_276

FULL_DAY_BASE_EVENT_BUFFER_BYTES = (
    FULL_DAY_BASE_EVENT_ROWS
    * EVENT_DTYPE_ITEMSIZE_BYTES
)

assert FULL_DAY_BASE_EVENT_BUFFER_BYTES == 4_074_641_664


# ------------------------------------------------------------------
# Frozen bounded implementation geometry.
# ------------------------------------------------------------------

IMPLEMENTATION_PATH = (
    "src/multimarket/dev045_d6r_bounded_converter.py"
)

IMPLEMENTATION_SHA256 = (
    "8f79ec81c664f1762a87bfcf8757564a"
    "bbe2d7f5fd89b1c83fc78de0ac4b94ac"
)

PRODUCTION_CHUNK_ROWS = 500_000

EXPECTED_RUN_PAIRS = 128
EXPECTED_TEMPORARY_SORT_RUNS = 256

FILE_DESCRIPTOR_HEADROOM = 64
REQUIRED_NOFILE_SOFT = 320


# ------------------------------------------------------------------
# Memory gate inherited from frozen D6R0.
#
# MemAvailable >= 4 x measured real-slice bounded peak RSS.
# Swap does not count.
# ------------------------------------------------------------------

MEMORY_SAFETY_MULTIPLIER = 4

REQUIRED_AVAILABLE_MEMORY_BYTES = (
    MEMORY_SAFETY_MULTIPLIER
    * BOUNDED_REAL_SLICE_PEAK_RSS_BYTES
)

assert REQUIRED_AVAILABLE_MEMORY_BYTES == 1_805_762_560

MEMORY_PROBE_SOURCE = "/proc/meminfo"
MEMORY_PROBE_FIELD = "MemAvailable"

SWAP_COUNTS_AS_AVAILABLE_MEMORY = False

MEMORY_GATE_RULE = (
    "MEMAVAILABLE_BYTES_GTE_1805762560"
)


# ------------------------------------------------------------------
# Scratch-disk gate inherited from frozen D6R0.
#
# free scratch bytes >= 6 x base event buffer bytes.
# ------------------------------------------------------------------

SCRATCH_SAFETY_MULTIPLIER = 6

REQUIRED_SCRATCH_FREE_BYTES = (
    SCRATCH_SAFETY_MULTIPLIER
    * FULL_DAY_BASE_EVENT_BUFFER_BYTES
)

assert REQUIRED_SCRATCH_FREE_BYTES == 24_447_849_984

SCRATCH_FILESYSTEM_PROBE_PATH = (
    "/home/emadh/Multi-Market"
)

FULL_DAY_SCRATCH_MUST_USE_PROBED_FILESYSTEM = True
FULL_DAY_OUTPUT_MUST_USE_PROBED_FILESYSTEM = True

DISK_GATE_RULE = (
    "FREE_BYTES_GTE_24447849984"
)


# ------------------------------------------------------------------
# File-descriptor gate.
#
# Full Jan produces 128 exchange and 128 local sorted runs.
# 64 descriptors of explicit engineering headroom are required.
# ------------------------------------------------------------------

NOFILE_PROBE = "resource.RLIMIT_NOFILE"

NOFILE_GATE_RULE = (
    "SOFT_NOFILE_GTE_320"
)


# ------------------------------------------------------------------
# Machine diagnostics.
#
# CPU is diagnostic only and is not capped.
# ------------------------------------------------------------------

RECORD_CPU_COUNT = True
RECORD_CPU_AFFINITY_COUNT = True

RECORD_MEMTOTAL = True
RECORD_MEMAVAILABLE = True
RECORD_SWAPFREE = True

RECORD_DISK_TOTAL = True
RECORD_DISK_FREE = True

RECORD_NOFILE_SOFT = True
RECORD_NOFILE_HARD = True

CPU_CAP_ALLOWED = False
USE_AVAILABLE_MACHINE_CPU_CAPACITY = True


# ------------------------------------------------------------------
# Canonical D6R3B resource execution.
# ------------------------------------------------------------------

RESOURCE_PREFLIGHT_CANONICAL_ATTEMPTS = 1

RESOURCE_PREFLIGHT_OPENS_RAW_DATA = False
RESOURCE_PREFLIGHT_RUNS_CONVERTER = False

RESOURCE_PREFLIGHT_RUNS_POLICY = False
RESOURCE_PREFLIGHT_COMPUTES_PNL = False

RESOURCE_PREFLIGHT_RESULT_PATH = (
    "evidence/dev045_d6r3b_full_day_resource_preflight.json"
)

FIRST_RESOURCE_RESULT_FROZEN_PASS_OR_FAIL = True


# ------------------------------------------------------------------
# All gates are mandatory.
# ------------------------------------------------------------------

REQUIRED_GATES = (
    "MEMORY",
    "SCRATCH_DISK",
    "NOFILE",
)

ALL_REQUIRED_GATES_MUST_PASS = True


# ------------------------------------------------------------------
# PASS only authorizes freezing the full-day execution contract.
# ------------------------------------------------------------------

FULL_DAY_CONVERSION_AUTHORIZED_NOW = False

RESOURCE_PASS_NEXT_GATE = (
    "FREEZE_JAN01_FULL_DAY_BOUNDED_CONVERSION_CONTRACT"
)


# ------------------------------------------------------------------
# Closed surfaces.
# ------------------------------------------------------------------

RAW_CONTENT_OPEN_ALLOWED = False
FULL_DAY_CONVERTER_RUN_ALLOWED = False

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

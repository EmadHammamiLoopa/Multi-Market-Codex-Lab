from __future__ import annotations

from pathlib import Path


EXPERIMENT_ID = "DEV045-D6R12"
CONTRACT_ID = "DEV045-D6R12-MEMORY-ATTRIBUTED-REAL-DIAGNOSTIC-DESIGN-V1"
SCHEMA_VERSION = "dev045-d6r12-memory-attributed-real-diagnostic-v1"
STAGE_MODE = "DESIGN_CONTRACT_SYNTHETIC_TESTS_ONLY"
FUTURE_EXECUTION_MODE = "FEED_ONLY_NO_STRATEGY_BOUNDED_DIAGNOSTIC"

D6R10_EXECUTION_CODE_HEAD = "0f2129e1cc0f8b75377fb0fb01b01857b24ab18c"
D6R10_FROZEN_FAILURE_HEAD = "50663457ca3e12506160025ccd045bf9abeec197"
D6R11_IMPLEMENTATION_PASS_HEAD = "22f20b506c9d1a52fae523a758e29588df33161b"
D6R11_FROZEN_PASS_HEAD = "9b342a6e08fe51771a7125e823d76c927b1c3d7d"

D6R11_FREEZE_MANIFEST_PATH = "evidence/dev045_d6r11_memory_attribution_freeze.json"
D6R11_FREEZE_MANIFEST_SHA256 = (
    "aa9128a7c0fbfbec94912a70bfbba21b04822fec9d94b837fa6179486ec03327"
)
D6R10_EVIDENCE_PATH = "evidence/dev045_d6r10_2026-02-01.json"
D6R10_EVIDENCE_SHA256 = (
    "83c648793d28c570fa1e1deee104eb6212464054786b95747f27bf3c88414c90"
)
D6R10_ATTEMPT_MARKER_SHA256 = (
    "9346106a92cb35f8681bfef7ba06b46ad719c9e55a93e833bd96ab68992b3ebb"
)
D6R10_HEARTBEAT_SHA256 = (
    "62ff826a0bc480cc321ce47b4dde57d9c8227968ede039c103aac94d8140cec3"
)

DAY = "2026-02-01"
SYMBOL = "BTCUSDT"
EXCHANGE = "binance-futures"
SOURCE_PATH = Path(
    "/home/emadh/Multi-Market/runtime/dev045_d6r9a/output/"
    "BTCUSDT_2026-02-01.npy"
)
SOURCE_ROWS = 179_584_138
SOURCE_BYTES = 11_493_385_088
SOURCE_SHA256 = "d757d2ac32a29b0ac587323e115779c466068c6c0eba4270226b9c4109254cbc"

OLD_D6R10_ABORT_ERROR = "D6R10Error: rss_abort:2026-02-01:10808320000"
OLD_D6R10_ABORT_BYTES = 10_808_320_000
OLD_D6R10_LAST_HEARTBEAT_WAKEUPS = 6_500_000
OLD_D6R10_LAST_HEARTBEAT_RSS_BYTES = 10_693_107_712

BOUNDED_WAKEUP_TARGET = 7_500_000
WAKEUP_CAPTURE_INTERVAL = 250_000
FIRST_WAKEUP_CAPTURE = 1
SPECIFIC_WAKEUP_CAPTURES = (
    6_000_000,
    6_250_000,
    6_500_000,
    6_750_000,
    7_000_000,
    7_250_000,
    7_500_000,
)
BOUNDED_TARGET_TERMINAL_REASON = "BOUNDED_WAKEUP_TARGET_REACHED"
TARGET_OVERSHOOT_ERROR = "BOUNDED_WAKEUP_TARGET_OVERSHOT"

LIFECYCLE_CAPTURE_POINTS = (
    "before_source_open",
    "after_verified_memmap_open",
    "after_hftbacktest_binding_creation",
    "immediately_before_close",
    "after_backtest_close",
    "after_memmap_close",
)

MEMORY_STATUS_FIELDS = (
    "VmRSS",
    "RssAnon",
    "RssFile",
    "RssShmem",
    "VmSize",
    "VmData",
    "VmSwap",
)
MEMORY_SYSTEM_FIELDS = ("MemAvailable",)
MEMORY_SMAPS_ROLLUP_FIELDS = (
    "Rss",
    "Pss",
    "Pss_Anon",
    "Pss_File",
    "Private_Clean",
    "Private_Dirty",
    "Shared_Clean",
    "Shared_Dirty",
    "Anonymous",
    "Swap",
)
MEMORY_DERIVED_FIELDS = (
    "resident_components_bytes",
    "rss_decomposition_delta_bytes",
)

# This gate is inherited unchanged from D6R10's pre-execution convention. It is
# not a traversal-time abort threshold. Runtime MemAvailable remains diagnostic.
PREEXEC_MIN_MEMAVAILABLE_BYTES = 8_442_945_536
RUNTIME_MEMAVAILABLE_ABORT_THRESHOLD_BYTES = None

# Baseline-relative process swap growth is a candidate runtime hard guard: it
# detects the process beginning to swap without selecting an absolute memory
# limit from the failed run. Its final use still requires execution preflight.
RUNTIME_ABORT_ON_PROCESS_SWAP_GROWTH = True
PROCESS_SWAP_GROWTH_BASELINE = "before_source_open_VmSwap"

# No hindsight-derived replacement threshold is authorized. Total RSS remains a
# diagnostic field. Anonymous growth is measured; a justified hard limit must
# be frozen during the separate execution preflight before any real attempt.
TOTAL_RSS_ABORT_THRESHOLD_BYTES = None
ANONYMOUS_RSS_ABORT_THRESHOLD_BYTES = None
ANONYMOUS_GROWTH_PREFLIGHT_REQUIRED = True

FUTURE_RUNTIME_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r12")
FUTURE_EVIDENCE_PATH = Path("evidence/dev045_d6r12_2026-02-01.json")
FUTURE_ATTEMPT_MARKER_NAME = "ATTEMPT_STARTED.json"
FUTURE_ATTEMPT_POLICY = "ONE_SHOT_CONSUMED_NEVER_RERUN"
D6R10_RUNTIME_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r10")

MEMMAP_OWNER_MUST_OUTLIVE_BACKTEST = True
BACKTEST_MUST_CLOSE_BEFORE_MEMMAP_CLOSE = True
REQUIRED_CLOSE_ORDER = ("backtest_closed", "memmap_closed")

FUTURE_EVIDENCE_REQUIRED_FIELDS = (
    "experiment_id",
    "schema_version",
    "canonical_attempt",
    "day",
    "source_path",
    "source_sha256",
    "source_rows",
    "source_bytes",
    "source_content_opened",
    "bounded_wakeup_target",
    "bounded_wakeup_reached",
    "market_wakeups",
    "terminal_reason",
    "memory_snapshots",
    "peak_vm_rss_bytes",
    "peak_rss_anon_bytes",
    "peak_rss_file_bytes",
    "peak_rss_shmem_bytes",
    "minimum_memavailable_bytes",
    "peak_vm_swap_bytes",
    "old_d6r10_abort_bytes",
    "old_d6r10_last_heartbeat_wakeups",
    "crossed_old_failure_region",
    "full_day_attempted",
    "full_day_validated",
    "canonical_npy_written",
    "raw_csv_opened",
    "converter_rerun",
    "orders",
    "policy_execution",
    "historical_pnl",
    "economic_arena",
    "aug_opened",
    "sep_plus_opened",
    "non_btc_opened",
    "network_acquisition",
    "railway_touched",
    "live_trading_authorized",
)

CANONICAL_EXECUTION_AUTHORIZED = False
CANONICAL_DATA_OPEN_AUTHORIZED = False
HFTBACKTEST_CANONICAL_RUN_AUTHORIZED = False
FULL_DAY_ATTEMPT_AUTHORIZED = False
FULL_DAY_VALIDATION_AUTHORIZED = False
CANONICAL_NPY_WRITE_AUTHORIZED = False
RAW_CSV_OPEN_AUTHORIZED = False
CONVERTER_RERUN_AUTHORIZED = False
ORDER_SUBMISSION_AUTHORIZED = False
ORDER_CANCEL_AUTHORIZED = False
POLICY_EXECUTION_AUTHORIZED = False
HISTORICAL_PNL_AUTHORIZED = False
ECONOMIC_ARENA_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False
RAILWAY_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

PROHIBITED_EXECUTION_FLAGS = (
    CANONICAL_EXECUTION_AUTHORIZED,
    CANONICAL_DATA_OPEN_AUTHORIZED,
    HFTBACKTEST_CANONICAL_RUN_AUTHORIZED,
    FULL_DAY_ATTEMPT_AUTHORIZED,
    FULL_DAY_VALIDATION_AUTHORIZED,
    CANONICAL_NPY_WRITE_AUTHORIZED,
    RAW_CSV_OPEN_AUTHORIZED,
    CONVERTER_RERUN_AUTHORIZED,
    ORDER_SUBMISSION_AUTHORIZED,
    ORDER_CANCEL_AUTHORIZED,
    POLICY_EXECUTION_AUTHORIZED,
    HISTORICAL_PNL_AUTHORIZED,
    ECONOMIC_ARENA_AUTHORIZED,
    AUG_OPEN_AUTHORIZED,
    SEP_PLUS_OPEN_AUTHORIZED,
    NON_BTC_OPEN_AUTHORIZED,
    NETWORK_ACQUISITION_AUTHORIZED,
    RAILWAY_AUTHORIZED,
    LIVE_TRADING_AUTHORIZED,
)

NEXT_STAGE = "DEV045-D6R12_REAL_DIAGNOSTIC_EXECUTION_PREFLIGHT"

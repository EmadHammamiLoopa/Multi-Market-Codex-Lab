from __future__ import annotations

from typing import Sequence


EXPERIMENT_ID = "DEV045-D6R14"
SCHEMA_VERSION = "dev045-d6r14-memory-policy-feed-bound-design-v1"
STAGE_MODE = "DESIGN_ONLY_NOT_EXECUTED"

PARENT_D6R13_FREEZE_HEAD = "7f528866769e1aab6d55ed8c2aec794cacb2418e"
PARENT_D6R13_FREEZE_MANIFEST_PATH = (
    "evidence/dev045_d6r13_consumed_eod_failure_freeze.json"
)
PARENT_D6R13_FREEZE_MANIFEST_SHA256 = (
    "f66f728026b9541d81d756d186efe1704812148595eb68d404adc6cb9922ff97"
)

D6R12_RERUN_FORBIDDEN = True
D6R13_RERUN_FORBIDDEN = True
D6R13_ATTEMPT_CONSUMED = True
D6R13_EXECUTION_STATUS = "FAIL"
D6R13_FAILURE_CLASS = "END_OF_DATA_BEFORE_DESIGNED_TARGET"
D6R13_DIAGNOSTIC_QUESTION_ANSWERED = True
ADDITIONAL_BOUNDED_MEMORY_DIAGNOSTIC_REQUIRED = False

D6R13_DESIGNED_TARGET_WAKEUPS = 7_500_000
D6R13_OBSERVED_END_OF_DATA_WAKEUPS = 7_139_910
D6R13_TARGET_SHORTFALL_WAKEUPS = 360_090

OLD_D6R10_TOTAL_RSS_ABORT_BYTES = 10_737_418_240
D6R13_FIRST_CAPTURE_ABOVE_OLD_RSS_ABORT_WAKEUPS = 6_750_000

D6R13_AFTER_BINDING_RSS_ANON_BYTES = 67_280_896
D6R13_TERMINAL_RSS_ANON_BYTES = 76_292_096
D6R13_OBSERVED_ANON_GROWTH_BYTES = (
    D6R13_TERMINAL_RSS_ANON_BYTES - D6R13_AFTER_BINDING_RSS_ANON_BYTES
)

D6R13_6750000_VM_RSS_BYTES = 11_030_495_232
D6R13_6750000_RSS_FILE_BYTES = 10_954_207_232
D6R13_6750000_RSS_ANON_BYTES = 76_288_000
D6R13_6750000_VM_SWAP_BYTES = 0
D6R13_6750000_FILE_BACKED_FRACTION = (
    D6R13_6750000_RSS_FILE_BYTES / D6R13_6750000_VM_RSS_BYTES
)

D6R13_TERMINAL_VM_RSS_BYTES = 11_654_348_800
D6R13_TERMINAL_RSS_FILE_BYTES = 11_578_056_704
D6R13_TERMINAL_VM_SWAP_BYTES = 0
D6R13_TERMINAL_MEMAVAILABLE_BYTES = 12_190_806_016
D6R13_TERMINAL_FILE_BACKED_FRACTION = (
    D6R13_TERMINAL_RSS_FILE_BYTES / D6R13_TERMINAL_VM_RSS_BYTES
)

D6R13_AFTER_MEMMAP_CLOSE_VM_RSS_BYTES = 161_947_648

# Evidence-backed policy:
# Total RSS is deliberately NOT a runtime abort metric because D6R13
# directly showed >99% file-backed residency after crossing D6R10's
# old total-RSS threshold, with zero swap and stable anonymous RSS.
TOTAL_RSS_ABORT_THRESHOLD_BYTES = None

# Preserve the already-established pre-execution capacity gate.
PREEXEC_MIN_MEMAVAILABLE_BYTES = 8_442_945_536

# Runtime emergency floor. This is intentionally well below both the
# pre-execution gate and every D6R13 observed MemAvailable snapshot.
RUNTIME_MEMAVAILABLE_ABORT_THRESHOLD_BYTES = 4_294_967_296

# Swap growth remains a hard process-pressure signal.
RUNTIME_ABORT_ON_PROCESS_SWAP_GROWTH = True

# D6R13 observed only ~9 MB anonymous growth after binding through EOD.
# 512 MiB gives >50x observed headroom while still detecting a genuine
# anonymous-memory runaway.
ANONYMOUS_GROWTH_ABORT_THRESHOLD_BYTES = 536_870_912
ANONYMOUS_GROWTH_BASELINE = "after_hftbacktest_binding_creation"

NATURAL_END_OF_DATA_IS_VALID_TERMINAL = True
FIXED_WAKEUP_TARGET_REQUIRED = False
EXPECTED_SUCCESS_TERMINAL_REASON = "NATURAL_END_OF_DATA"
EXPECTED_CLOSE_LIFECYCLE_SUFFIX = ("backtest_closed", "memmap_closed")

REAL_EXECUTION_ENABLED = False
CANONICAL_DATA_OPEN_AUTHORIZED = False
HFTBACKTEST_CANONICAL_RUN_AUTHORIZED = False
FULL_DAY_ATTEMPT_AUTHORIZED = False
MAR_TO_JUL_AUTHORIZED = False
HISTORICAL_PNL_AUTHORIZED = False
POLICY_EXECUTION_AUTHORIZED = False
ORDER_SUBMISSION_AUTHORIZED = False
ORDER_CANCEL_AUTHORIZED = False
CONVERTER_RERUN_AUTHORIZED = False
RAW_CSV_OPEN_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False
RAILWAY_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

EXECUTION_AUTHORIZATION_FLAGS = (
    REAL_EXECUTION_ENABLED,
    CANONICAL_DATA_OPEN_AUTHORIZED,
    HFTBACKTEST_CANONICAL_RUN_AUTHORIZED,
    FULL_DAY_ATTEMPT_AUTHORIZED,
    MAR_TO_JUL_AUTHORIZED,
    HISTORICAL_PNL_AUTHORIZED,
    POLICY_EXECUTION_AUTHORIZED,
    ORDER_SUBMISSION_AUTHORIZED,
    ORDER_CANCEL_AUTHORIZED,
    CONVERTER_RERUN_AUTHORIZED,
    RAW_CSV_OPEN_AUTHORIZED,
    AUG_OPEN_AUTHORIZED,
    SEP_PLUS_OPEN_AUTHORIZED,
    NON_BTC_OPEN_AUTHORIZED,
    NETWORK_ACQUISITION_AUTHORIZED,
    RAILWAY_AUTHORIZED,
    LIVE_TRADING_AUTHORIZED,
)

NEXT_STAGE = "DEV045-D6R15_FULL_DAY_INGESTION_SUCCESSOR_DESIGN_ONLY"


def _nonnegative_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(name)
    return value


def memory_abort_reason(
    *,
    baseline_swap_bytes: int,
    current_swap_bytes: int,
    baseline_rss_anon_bytes: int,
    current_rss_anon_bytes: int,
    current_memavailable_bytes: int,
) -> str | None:
    baseline_swap = _nonnegative_int("baseline_swap_bytes", baseline_swap_bytes)
    current_swap = _nonnegative_int("current_swap_bytes", current_swap_bytes)
    baseline_anon = _nonnegative_int(
        "baseline_rss_anon_bytes", baseline_rss_anon_bytes
    )
    current_anon = _nonnegative_int(
        "current_rss_anon_bytes", current_rss_anon_bytes
    )
    memavailable = _nonnegative_int(
        "current_memavailable_bytes", current_memavailable_bytes
    )

    if RUNTIME_ABORT_ON_PROCESS_SWAP_GROWTH and current_swap > baseline_swap:
        return "PROCESS_SWAP_GROWTH"

    anonymous_growth = max(0, current_anon - baseline_anon)
    if anonymous_growth > ANONYMOUS_GROWTH_ABORT_THRESHOLD_BYTES:
        return "ANONYMOUS_RSS_GROWTH"

    if memavailable < RUNTIME_MEMAVAILABLE_ABORT_THRESHOLD_BYTES:
        return "SYSTEM_MEMAVAILABLE_BELOW_FLOOR"

    return None


def classify_feed_terminal(
    *,
    end_of_data: bool,
    market_wakeups: int,
    hard_safety_abort_reason: str | None,
    position: float,
    working_order_count: int,
    source_unchanged: bool,
    lifecycle: Sequence[str],
) -> str:
    wakeups = _nonnegative_int("market_wakeups", market_wakeups)
    orders = _nonnegative_int("working_order_count", working_order_count)

    if hard_safety_abort_reason is not None:
        return f"FAIL_SAFETY_ABORT:{hard_safety_abort_reason}"

    if not end_of_data:
        return "NOT_TERMINAL"

    if wakeups == 0:
        return "FAIL_EMPTY_FEED"

    if position != 0.0 or orders != 0:
        return "FAIL_TERMINAL_EXECUTION_STATE"

    if not source_unchanged:
        return "FAIL_SOURCE_CHANGED"

    if tuple(lifecycle[-2:]) != EXPECTED_CLOSE_LIFECYCLE_SUFFIX:
        return "FAIL_CLOSE_ORDER"

    return "PASS_NATURAL_END_OF_DATA"

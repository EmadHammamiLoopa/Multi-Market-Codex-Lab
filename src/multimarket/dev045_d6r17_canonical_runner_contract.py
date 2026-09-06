from __future__ import annotations

from dataclasses import dataclass

from multimarket import (
    dev045_d6r17_direct_action_driver_bridge as bridge,
)
from multimarket import (
    dev045_d6r17_direct_action_support as support,
)
from multimarket import (
    dev045_d6r17_real_historical_economic_driver_contract as parent,
)
from multimarket import dev045_m6_economic_arena as m6


EXPERIMENT_ID = "DEV045-D6R17"

CONTRACT_ID = (
    "DEV045-D6R17-CANONICAL-RUNNER-CONTRACT-V1"
)

SCHEMA_VERSION = (
    "dev045-d6r17-canonical-runner-contract-v1"
)

PARENT_HEAD = (
    "2207f60015506a2988aeb8aa659c6cace0a0c033"
)

AUTHORIZATION_ENV = parent.AUTHORIZATION_ENV
AUTHORIZATION_TOKEN = parent.AUTHORIZATION_TOKEN

DAY_ORDER = tuple(
    parent.AUTHORIZED_DAYS
)

POLICY_ORDER = tuple(
    parent.POLICY_IDS
)

SCENARIO_ORDER = tuple(
    parent.SCENARIOS
)

EXPECTED_DAY_COUNT = 7
EXPECTED_POLICIES_PER_DAY = 8
EXPECTED_SCENARIOS_PER_POLICY = 2
EXPECTED_REPLAYS_PER_DAY = 16
EXPECTED_TOTAL_REPLAYS = 112

BASE_ONLY_DAYS = tuple(
    support.BASE_ONLY_DAYS
)

DIRECT_SUPPORT_DAYS = tuple(
    support.DIRECT_SUPPORT_DAYS
)

DIRECT_SUPPORT_POLICIES = (
    "M06",
    "M07",
)

# ----------------------------------------------------------
# Canonical source lifecycle — future execution only.
# ----------------------------------------------------------

SOURCE_OPEN_METHOD = (
    "D6R5__OPEN_VERIFIED_FILE_WITH_D6R17_DAY_SPEC"
)

FULL_SHA256_BEFORE_MEMMAP_REQUIRED = True
SOURCE_READ_ONLY_REQUIRED = True

OPEN_SOURCE_ONCE_PER_DAY = True
KEEP_SOURCE_OPEN_FOR_ALL_16_REPLAYS = True
CLOSE_SOURCE_AFTER_ALL_16_REPLAYS = True

SOURCE_OPEN_COUNT_PER_DAY = 1
SOURCE_CLOSE_COUNT_PER_DAY = 1

PROCESS_ONE_DAY_AT_A_TIME = True

# ----------------------------------------------------------
# Frozen support lifecycle.
# ----------------------------------------------------------

JAN_MAR_SUPPORT_MAPPING = "EMPTY"
APR_JUL_SUPPORT_MAPPING = "M06_AND_M07_EXACT_ONLY"

M06_DIRECTION_SOURCE = "DEV044_T0E_T10A_ACTION"
M07_DIRECTION_SOURCE = "DEV044_T0E_T05A_ACTION"

EXACT_TIMESTAMP_ONLY = True

MISSING_EXACT_ROW_SEMANTIC = "FALLBACK_TO_M02"
EXPLICIT_ZERO_SEMANTIC = "FROZEN_ABSTAIN"

PROBABILITY_FORWARD_FILL = False
PROBABILITY_INTERPOLATION = False
PROBABILITY_BACKFILL = False
PROBABILITY_RECONSTRUCTION = False
LEGACY_STATE_REMATERIALIZATION = False
A0_REFIT = False
A0_RETRAIN = False

# ----------------------------------------------------------
# Replay ordering / multiplicity.
# ----------------------------------------------------------

REPLAY_ORDER = tuple(
    (
        day,
        policy_id,
        scenario,
    )
    for day in DAY_ORDER
    for policy_id in POLICY_ORDER
    for scenario in SCENARIO_ORDER
)

POLICY_MAJOR_THEN_SCENARIO = True
PRIMARY_BEFORE_STRESS = True

ALL_112_REPLAYS_REQUIRED = True
RANKING_BEFORE_COMPLETE_MATRIX = False

# ----------------------------------------------------------
# Raw fill preservation.
#
# The frozen full-day replay already accounts fills into
# replay.cycles, but M6.run_economic_arena() requires the raw
# FillRecords again.
#
# Future canonical runner therefore MUST capture each
# event.fill from kernel.bound_fills before bt.close().
# ----------------------------------------------------------

RAW_FILL_CAPTURE_REQUIRED = True

RAW_FILL_CAPTURE_SOURCE = (
    "DirectActionContinuousHistoricalPolicyKernel.bound_fills"
)

CAPTURE_BEFORE_BACKTEST_CLOSE = True

CAPTURE_ONLY_FILL_EVENTS = True

RAW_FILL_COUNT_MUST_EQUAL_REPLAY_TOTAL_FILL_COUNT = True

REACCOUNT_PARITY_REQUIRED = True

REACCOUNT_FUNCTION = (
    "dev045_m6_economic_arena.account_fill_bucket"
)

REACCOUNT_CYCLES_MUST_EQUAL_REPLAY_CYCLES = True

M6_FINAL_ENTRYPOINT = (
    "dev045_m6_economic_arena.run_economic_arena"
)

M6_FINAL_CALL_ONLY_AFTER_112 = True

PRIMARY_FILL_STREAM_COMPLETE_REQUIRED = True
STRESS_FILL_STREAM_COMPLETE_REQUIRED = True
AUDIT_MATRIX_COMPLETE_REQUIRED = True

# ----------------------------------------------------------
# Integrity and attempt semantics.
# ----------------------------------------------------------

STOP_ON_EXECUTION_INTEGRITY_FAILURE = True
STOP_ON_ECONOMIC_NONPASS = False

FIRST_HISTORICAL_OUTPUT_IS_EVIDENCE = True

ATTEMPT_CONSUMED_AFTER_FIRST_HISTORICAL_OUTPUT = True

AUTOMATIC_RETRY = False
RERUN_AFTER_ATTEMPT_CONSUMPTION = False
TUNING_AFTER_FIRST_OUTPUT = False

FAILURE_EVIDENCE_REQUIRED = True
SUCCESS_EVIDENCE_REQUIRED = True

PER_DAY_EVIDENCE_REQUIRED = True
PER_DAY_RANKING_FORBIDDEN = True

FINAL_ARENA_REQUIRES_ALL_DAYS_COMPLETE = True

# ----------------------------------------------------------
# Current contract stage: every execution surface CLOSED.
# ----------------------------------------------------------

CANONICAL_SOURCE_OPEN_ENABLED = False
CANONICAL_SOURCE_HASH_ENABLED = False

HFTBACKTEST_EXECUTION_ENABLED = False
POLICY_EXECUTION_ENABLED = False
HISTORICAL_PNL_ENABLED = False
ECONOMIC_ARENA_EXECUTION_ENABLED = False

CANONICAL_RESULT_WRITE_ENABLED = False

NETWORK_ACQUISITION_ENABLED = False
RAILWAY_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

RUNNER_IMPLEMENTATION_AUTHORIZED = False
CANONICAL_EXECUTION_AUTHORIZED = False


@dataclass(frozen=True)
class DayPlan:
    day: str
    support_mode: str
    replay_count: int
    source_open_count: int
    source_close_count: int


DAY_PLANS = tuple(
    DayPlan(
        day=day,
        support_mode=(
            JAN_MAR_SUPPORT_MAPPING
            if day in BASE_ONLY_DAYS
            else APR_JUL_SUPPORT_MAPPING
        ),
        replay_count=EXPECTED_REPLAYS_PER_DAY,
        source_open_count=SOURCE_OPEN_COUNT_PER_DAY,
        source_close_count=SOURCE_CLOSE_COUNT_PER_DAY,
    )
    for day in DAY_ORDER
)


def expected_day_replays(
    day: str,
) -> tuple[
    tuple[str, str, str],
    ...
]:
    if day not in DAY_ORDER:
        raise RuntimeError(
            "unauthorized_day"
        )

    return tuple(
        x
        for x in REPLAY_ORDER
        if x[0] == day
    )


def expected_support_keys(
    day: str,
) -> tuple[str, ...]:
    if day in BASE_ONLY_DAYS:
        return ()

    if day in DIRECT_SUPPORT_DAYS:
        return DIRECT_SUPPORT_POLICIES

    raise RuntimeError(
        "unknown_support_day"
    )


def validate_contract() -> None:
    parent.validate_contract()

    if DAY_ORDER != (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    ):
        raise RuntimeError(
            "day_order"
        )

    if POLICY_ORDER != (
        "M01",
        "M02",
        "M03",
        "M04",
        "M05",
        "M06",
        "M07",
        "M08",
    ):
        raise RuntimeError(
            "policy_order"
        )

    if SCENARIO_ORDER != (
        "Q0_PRIMARY_250_250",
        "Q0_STRESS_500_500",
    ):
        raise RuntimeError(
            "scenario_order"
        )

    if len(DAY_PLANS) != EXPECTED_DAY_COUNT:
        raise RuntimeError(
            "day_count"
        )

    if len(REPLAY_ORDER) != EXPECTED_TOTAL_REPLAYS:
        raise RuntimeError(
            "replay_count"
        )

    if EXPECTED_TOTAL_REPLAYS != 112:
        raise RuntimeError(
            "expected_total"
        )

    if any(
        len(
            expected_day_replays(day)
        )
        != EXPECTED_REPLAYS_PER_DAY
        for day in DAY_ORDER
    ):
        raise RuntimeError(
            "day_replay_count"
        )

    if any(
        expected_support_keys(day)
        != ()
        for day in BASE_ONLY_DAYS
    ):
        raise RuntimeError(
            "base_support"
        )

    if any(
        expected_support_keys(day)
        != ("M06", "M07")
        for day in DIRECT_SUPPORT_DAYS
    ):
        raise RuntimeError(
            "direct_support"
        )

    if M06_DIRECTION_SOURCE != (
        "DEV044_T0E_T10A_ACTION"
    ):
        raise RuntimeError(
            "m06_source"
        )

    if M07_DIRECTION_SOURCE != (
        "DEV044_T0E_T05A_ACTION"
    ):
        raise RuntimeError(
            "m07_source"
        )

    if not all(
        (
            FULL_SHA256_BEFORE_MEMMAP_REQUIRED,
            SOURCE_READ_ONLY_REQUIRED,
            OPEN_SOURCE_ONCE_PER_DAY,
            KEEP_SOURCE_OPEN_FOR_ALL_16_REPLAYS,
            CLOSE_SOURCE_AFTER_ALL_16_REPLAYS,
            PROCESS_ONE_DAY_AT_A_TIME,
            EXACT_TIMESTAMP_ONLY,
            POLICY_MAJOR_THEN_SCENARIO,
            PRIMARY_BEFORE_STRESS,
            ALL_112_REPLAYS_REQUIRED,
            RAW_FILL_CAPTURE_REQUIRED,
            CAPTURE_BEFORE_BACKTEST_CLOSE,
            CAPTURE_ONLY_FILL_EVENTS,
            RAW_FILL_COUNT_MUST_EQUAL_REPLAY_TOTAL_FILL_COUNT,
            REACCOUNT_PARITY_REQUIRED,
            REACCOUNT_CYCLES_MUST_EQUAL_REPLAY_CYCLES,
            M6_FINAL_CALL_ONLY_AFTER_112,
            PRIMARY_FILL_STREAM_COMPLETE_REQUIRED,
            STRESS_FILL_STREAM_COMPLETE_REQUIRED,
            AUDIT_MATRIX_COMPLETE_REQUIRED,
            STOP_ON_EXECUTION_INTEGRITY_FAILURE,
            FIRST_HISTORICAL_OUTPUT_IS_EVIDENCE,
            ATTEMPT_CONSUMED_AFTER_FIRST_HISTORICAL_OUTPUT,
            FAILURE_EVIDENCE_REQUIRED,
            SUCCESS_EVIDENCE_REQUIRED,
            PER_DAY_EVIDENCE_REQUIRED,
            PER_DAY_RANKING_FORBIDDEN,
            FINAL_ARENA_REQUIRES_ALL_DAYS_COMPLETE,
        )
    ):
        raise RuntimeError(
            "required_guard"
        )

    if any(
        (
            PROBABILITY_FORWARD_FILL,
            PROBABILITY_INTERPOLATION,
            PROBABILITY_BACKFILL,
            PROBABILITY_RECONSTRUCTION,
            LEGACY_STATE_REMATERIALIZATION,
            A0_REFIT,
            A0_RETRAIN,
            STOP_ON_ECONOMIC_NONPASS,
            RANKING_BEFORE_COMPLETE_MATRIX,
            AUTOMATIC_RETRY,
            RERUN_AFTER_ATTEMPT_CONSUMPTION,
            TUNING_AFTER_FIRST_OUTPUT,
            CANONICAL_SOURCE_OPEN_ENABLED,
            CANONICAL_SOURCE_HASH_ENABLED,
            HFTBACKTEST_EXECUTION_ENABLED,
            POLICY_EXECUTION_ENABLED,
            HISTORICAL_PNL_ENABLED,
            ECONOMIC_ARENA_EXECUTION_ENABLED,
            CANONICAL_RESULT_WRITE_ENABLED,
            NETWORK_ACQUISITION_ENABLED,
            RAILWAY_ENABLED,
            LIVE_TRADING_AUTHORIZED,
            AUG_OPEN_AUTHORIZED,
            SEP_PLUS_OPEN_AUTHORIZED,
            NON_BTC_OPEN_AUTHORIZED,
            RUNNER_IMPLEMENTATION_AUTHORIZED,
            CANONICAL_EXECUTION_AUTHORIZED,
        )
    ):
        raise RuntimeError(
            "closed_surface_open"
        )

    if (
        M6_FINAL_ENTRYPOINT
        != "dev045_m6_economic_arena.run_economic_arena"
    ):
        raise RuntimeError(
            "m6_entrypoint"
        )

    if (
        REACCOUNT_FUNCTION
        != "dev045_m6_economic_arena.account_fill_bucket"
    ):
        raise RuntimeError(
            "reaccount_function"
        )

    if (
        tuple(m6.SCENARIOS)
        != SCENARIO_ORDER
    ):
        raise RuntimeError(
            "m6_scenario_identity"
        )

    if tuple(
        bridge.ADAPTER_POLICIES
    ) != DIRECT_SUPPORT_POLICIES:
        raise RuntimeError(
            "bridge_policy_identity"
        )


__all__ = [
    "EXPERIMENT_ID",
    "CONTRACT_ID",
    "SCHEMA_VERSION",
    "PARENT_HEAD",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "DAY_ORDER",
    "POLICY_ORDER",
    "SCENARIO_ORDER",
    "EXPECTED_REPLAYS_PER_DAY",
    "EXPECTED_TOTAL_REPLAYS",
    "BASE_ONLY_DAYS",
    "DIRECT_SUPPORT_DAYS",
    "DIRECT_SUPPORT_POLICIES",
    "REPLAY_ORDER",
    "DAY_PLANS",
    "RAW_FILL_CAPTURE_REQUIRED",
    "M6_FINAL_ENTRYPOINT",
    "expected_day_replays",
    "expected_support_keys",
    "validate_contract",
]

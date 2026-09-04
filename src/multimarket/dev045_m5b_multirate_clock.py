from __future__ import annotations

from dataclasses import dataclass

from multimarket.dev044_t0_strategy_contract import StrategyState
from multimarket.dev045_m5a_a0_support_semantics import (
    A0_EXACT_SUPPORT_DAYS,
    A0_UNAVAILABLE_DAYS,
    AUTHORIZED_DAYS,
    A0LegacySupport,
    ExactA0ScoreIndex,
    M5ASupportError,
    resolve_joint_support,
)

EXPERIMENT_ID = "DEV045-M5B"
DESIGN_VERSION = "multirate-maker-second-a0-minute-v1"

BASE_MAKER_DECISION_STEP_US = 1_000_000
ADAPTER_CANDIDATE_STEP_US = 60_000_000

BASE_MAKER_PHASE_US = 0
ADAPTER_PHASE_US = 0

MARKET_EVENT = "MARKET_EVENT"
BASE_MAKER_DECISION_EPOCH = "BASE_MAKER_DECISION_EPOCH"
LEGACY_ADAPTER_DECISION_EPOCH = "LEGACY_ADAPTER_DECISION_EPOCH"

MODE_BASE_ONLY = "BASE_ONLY"
MODE_NO_ALPHA_UPDATE = "NO_ALPHA_UPDATE"
MODE_APPLY_ADAPTER = "APPLY_ADAPTER"
MODE_FALLBACK_TO_M02 = "FALLBACK_TO_M02"

MARKET_EVENT_TRIGGERS_POLICY_EVALUATION = False
INTERMEDIATE_SECOND_QUERIES_A0 = False
INTERMEDIATE_SECOND_MEANS_A0_UNAVAILABLE = False
INTERMEDIATE_SECOND_CLEARS_ADAPTER = False

PROBABILITY_FORWARD_FILL_ENABLED = False
PROBABILITY_INTERPOLATION_ENABLED = False
PROBABILITY_BACKFILL_ENABLED = False
PROBABILITY_CARRY_ENABLED = False
A0_REFIT_ENABLED = False
A0_RETRAIN_ENABLED = False
FUTURE_INFORMATION_ENABLED = False

HISTORICAL_FILE_IO_ENABLED = False
HISTORICAL_REPLAY_EXECUTION_ENABLED = False
HISTORICAL_PNL_ENABLED = False
CANONICAL_PNL_WRITE_ENABLED = False
LIVE_TRADING_AUTHORIZED = False


class M5BClockError(RuntimeError):
    pass


@dataclass(frozen=True)
class AdapterClockResolution:
    day: str
    timestamp_us: int
    mode: str
    support: A0LegacySupport | None

    def __post_init__(self) -> None:
        if self.day not in AUTHORIZED_DAYS:
            raise M5BClockError("unauthorized_day")

        if int(self.timestamp_us) < 0:
            raise M5BClockError("negative_timestamp")

        allowed = {
            MODE_BASE_ONLY,
            MODE_NO_ALPHA_UPDATE,
            MODE_APPLY_ADAPTER,
            MODE_FALLBACK_TO_M02,
        }

        if self.mode not in allowed:
            raise M5BClockError("unknown_mode")

        if self.mode == MODE_APPLY_ADAPTER:
            if self.support is None or not self.support.available:
                raise M5BClockError("apply_without_joint_support")

        elif self.mode == MODE_FALLBACK_TO_M02:
            if self.support is None or self.support.available:
                raise M5BClockError("fallback_without_unavailable_support")

        else:
            if self.support is not None:
                raise M5BClockError("support_attached_to_nonadapter_mode")


def _timestamp(timestamp_us: int) -> int:
    t = int(timestamp_us)

    if t < 0:
        raise M5BClockError("negative_timestamp")

    return t


def is_base_maker_decision_epoch(timestamp_us: int) -> bool:
    t = _timestamp(timestamp_us)

    return (
        (t - BASE_MAKER_PHASE_US)
        % BASE_MAKER_DECISION_STEP_US
        == 0
    )


def is_adapter_candidate_epoch(
    *,
    day: str,
    timestamp_us: int,
) -> bool:
    if day not in AUTHORIZED_DAYS:
        raise M5BClockError("unauthorized_day")

    t = _timestamp(timestamp_us)

    if day in A0_UNAVAILABLE_DAYS:
        return False

    if day not in A0_EXACT_SUPPORT_DAYS:
        raise M5BClockError("support_calendar")

    return (
        (t - ADAPTER_PHASE_US)
        % ADAPTER_CANDIDATE_STEP_US
        == 0
    )


def validate_a0_index_clock(
    index: ExactA0ScoreIndex,
) -> None:
    if index.day not in A0_EXACT_SUPPORT_DAYS:
        raise M5BClockError("a0_index_day")

    for point in index.points:
        t = int(point.timestamp_us)

        if (
            (t - ADAPTER_PHASE_US)
            % ADAPTER_CANDIDATE_STEP_US
            != 0
        ):
            raise M5BClockError(
                "a0_point_not_exact_minute"
            )


def scheduled_clock_kind(
    *,
    day: str,
    timestamp_us: int,
) -> str:
    if day not in AUTHORIZED_DAYS:
        raise M5BClockError("unauthorized_day")

    t = _timestamp(timestamp_us)

    if is_adapter_candidate_epoch(
        day=day,
        timestamp_us=t,
    ):
        return LEGACY_ADAPTER_DECISION_EPOCH

    if is_base_maker_decision_epoch(t):
        return BASE_MAKER_DECISION_EPOCH

    return MARKET_EVENT


def resolve_adapter_clock(
    *,
    day: str,
    timestamp_us: int,
    a0_index: ExactA0ScoreIndex | None,
    causal_legacy_state: StrategyState | None,
) -> AdapterClockResolution:
    """Resolve M06/M07 alpha-clock behavior at one base maker epoch.

    Exact-minute Apr-Jul candidate epochs query M5A joint support.

    Intermediate exact-second epochs deliberately do NOT query A0 and do NOT
    interpret the lack of an A0 row as unavailable support.
    """
    if day not in AUTHORIZED_DAYS:
        raise M5BClockError("unauthorized_day")

    t = _timestamp(timestamp_us)

    if not is_base_maker_decision_epoch(t):
        raise M5BClockError(
            "adapter_clock_resolution_requires_base_epoch"
        )

    if day in A0_UNAVAILABLE_DAYS:
        if a0_index is not None:
            raise M5BClockError(
                "a0_index_on_frozen_unavailable_day"
            )

        return AdapterClockResolution(
            day=day,
            timestamp_us=t,
            mode=MODE_BASE_ONLY,
            support=None,
        )

    if not is_adapter_candidate_epoch(
        day=day,
        timestamp_us=t,
    ):
        # Critical M5B semantic:
        # this second is not an A0 decision epoch.
        # Do not query, fill, clear, or manufacture A0.
        return AdapterClockResolution(
            day=day,
            timestamp_us=t,
            mode=MODE_NO_ALPHA_UPDATE,
            support=None,
        )

    if a0_index is not None:
        validate_a0_index_clock(a0_index)

        if a0_index.day != day:
            raise M5BClockError(
                "a0_index_day_mismatch"
            )

    try:
        support = resolve_joint_support(
            day=day,
            decision_timestamp_us=t,
            a0_index=a0_index,
            causal_legacy_state=causal_legacy_state,
        )
    except M5ASupportError as exc:
        raise M5BClockError(
            f"m5a_support:{exc}"
        ) from exc

    if support.available:
        mode = MODE_APPLY_ADAPTER
    else:
        mode = MODE_FALLBACK_TO_M02

    return AdapterClockResolution(
        day=day,
        timestamp_us=t,
        mode=mode,
        support=support,
    )


def market_event_policy_evaluation_allowed() -> bool:
    return MARKET_EVENT_TRIGGERS_POLICY_EVALUATION

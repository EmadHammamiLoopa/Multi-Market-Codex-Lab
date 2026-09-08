from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from multimarket import (
    dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0,
)
from multimarket import (
    dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1,
)
from multimarket import (
    dev045_d6r26a_p2_r13a_dual_stream_eof_memory_amendment as r13a,
)
from multimarket import (
    dev045_d6r26a_p2_r15_sequential_lane_real_engine_preexecution as r15,
)
from multimarket import (
    dev045_d6r26a_p2_r16_canonical_row_parquet_serializer_preexecution as r16,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R17"
DESIGN_VERSION = "feed-bound-shared-feature-cache-preexecution-v1"
PARENT_R16_HEAD = "6c37c3b7486c5cbd306bcb6b17583cde4e48175e"

FEED_BOUND_SCHEDULER_FROZEN = True
SHARED_DAY_FEATURE_CACHE_CONTRACT_FROZEN = True

# Exact D6R14/D6R15 anti-regression.
NATURAL_END_OF_DATA_IS_VALID_TERMINAL = True
EXPECTED_SUCCESS_TERMINAL_REASON = "NATURAL_END_OF_DATA"
FIXED_EVENT_TARGET = None
FIXED_WAKEUP_TARGET = None
REFERENCE_WAKEUP_COUNT_IS_STOP_CONDITION = False
NOMINAL_DAY_END_IS_STOP_CONDITION = False
LAST_OBSERVED_LOCAL_FEED_TIMESTAMP_IS_DECISION_BOUND = True
DECISION_AT_EXACT_LAST_FEED_TIMESTAMP_ALLOWED = True
DECISION_AFTER_LAST_FEED_TIMESTAMP_FORBIDDEN = True

# Existing P2 EOF semantics.
END_OF_SOURCE_CANDIDATES_RETAINED_WITH_CENSORING = True
CENSORED_MAPS_TO_NO_FILL = False

# Performance contract. The ~180M-row raw source may be traversed for feature
# extraction once per opened day, never once for each of the 40 lanes.
RAW_FEATURE_PASSES_PER_DAY = 1
PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN = True
FEATURE_CACHE_SHARED_ACROSS_ALL_40_LANES = True
FEATURE_CACHE_CANDIDATE_GRID_CASES = 8
FEATURE_CACHE_FEATURE_COUNT = 25
FEATURE_CACHE_VALUE_DTYPE = np.dtype("<f8")
FEATURE_CACHE_MAX_BYTES = 256 * 1024 * 1024
DENSE_NUMPY_CACHE_REQUIRED = True
PYTHON_OBJECT_CACHE_FOR_REAL_DAY_FORBIDDEN = True

NOMINAL_DAY_NS = 86_400_000_000_000

PREEXECUTION_ONLY = True
HISTORICAL_FILE_IO_AUTHORIZED = False
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
SIMULATOR_IMPORT_AUTHORIZED = False
CANDIDATE_SIMULATION_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False


class FeedBoundScheduleError(RuntimeError):
    pass


@dataclass(frozen=True)
class FeedBounds:
    nominal_day_start_local_ns: int
    nominal_day_end_exclusive_local_ns: int
    first_observed_local_ns: int
    last_observed_local_ns: int
    feed_end_exclusive_local_ns: int


@dataclass(frozen=True)
class FeatureCacheLayout:
    decision_count: int
    candidate_grid_cases: int
    feature_count: int
    value_bytes: int
    decision_timestamp_bytes: int
    bbo_tick_bytes: int
    total_bytes: int


def derive_feed_bounds(
    events: np.ndarray,
    *,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
) -> FeedBounds:
    """
    O(1) feed-bound derivation after the already-frozen once/day source
    validation. Never scans the full 180M-row array merely to find EOF.
    """
    a = np.asarray(events)

    if a.ndim != 1 or a.size <= 0:
        raise FeedBoundScheduleError("source_empty")

    if a.dtype.names is None or "local_ts" not in a.dtype.names:
        raise FeedBoundScheduleError("local_ts_field")

    start = int(nominal_day_start_local_ns)
    nominal_end = int(nominal_day_end_exclusive_local_ns)

    if start < 0 or nominal_end <= start:
        raise FeedBoundScheduleError("nominal_day_bounds")

    first_local = int(a[0]["local_ts"])
    last_local = int(a[-1]["local_ts"])

    if first_local < start:
        raise FeedBoundScheduleError(
            f"feed_before_nominal_day:{first_local}:{start}"
        )

    if last_local < first_local:
        raise FeedBoundScheduleError("feed_terminal_regression")

    if last_local >= nominal_end:
        raise FeedBoundScheduleError(
            f"feed_after_nominal_day:{last_local}:{nominal_end}"
        )

    if last_local == np.iinfo(np.int64).max:
        raise FeedBoundScheduleError("feed_end_overflow")

    # Exclusive bound makes a decision exactly at the final observed feed
    # timestamp legal while guaranteeing no decision after actual EOF.
    feed_end_exclusive = last_local + 1

    return FeedBounds(
        nominal_day_start_local_ns=start,
        nominal_day_end_exclusive_local_ns=nominal_end,
        first_observed_local_ns=first_local,
        last_observed_local_ns=last_local,
        feed_end_exclusive_local_ns=feed_end_exclusive,
    )


def build_phase_decisions(
    *,
    bounds: FeedBounds,
    phase: int,
) -> tuple[int, ...]:
    epochs = r1.decision_epochs_for_lane(
        day_start_local_ns=bounds.nominal_day_start_local_ns,
        day_end_local_ns=bounds.feed_end_exclusive_local_ns,
        phase=int(phase),
    )

    if any(
        int(ts) > int(bounds.last_observed_local_ns)
        for ts in epochs
    ):
        raise FeedBoundScheduleError(
            "decision_after_feed_end"
        )

    return epochs


def build_shared_decision_grid(
    *,
    bounds: FeedBounds,
) -> tuple[int, ...]:
    """
    Union of all five phase cohorts.

    This is the once/day feature-extraction grid shared by all BID/ASK ×
    distance lanes. No side/distance duplicates are introduced here.
    """
    by_phase = tuple(
        build_phase_decisions(
            bounds=bounds,
            phase=int(phase),
        )
        for phase in p0.LANE_PHASE_OFFSETS_S
    )

    flattened = tuple(
        sorted(
            ts
            for phase_epochs in by_phase
            for ts in phase_epochs
        )
    )

    if len(flattened) != len(set(flattened)):
        raise FeedBoundScheduleError(
            "phase_decision_duplicate"
        )

    expected = tuple(
        range(
            bounds.nominal_day_start_local_ns
            + r1.FEATURE_WARMUP_NS,
            bounds.feed_end_exclusive_local_ns,
            p0.DECISION_STEP_NS,
        )
    )

    if flattened != expected:
        raise FeedBoundScheduleError(
            "phase_union_not_exact_one_second_grid"
        )

    if flattened and flattened[-1] > bounds.last_observed_local_ns:
        raise FeedBoundScheduleError(
            "shared_grid_after_feed_end"
        )

    return flattened


def feature_cache_layout(
    *,
    decision_count: int,
) -> FeatureCacheLayout:
    n = int(decision_count)

    if n < 0:
        raise FeedBoundScheduleError("decision_count")

    # 8 candidate side×distance cases × 25 float64 feature values.
    value_bytes = (
        n
        * FEATURE_CACHE_CANDIDATE_GRID_CASES
        * FEATURE_CACHE_FEATURE_COUNT
        * FEATURE_CACHE_VALUE_DTYPE.itemsize
    )

    # One int64 decision timestamp and two int64 BBO ticks per second.
    decision_timestamp_bytes = n * 8
    bbo_tick_bytes = n * 2 * 8

    total = (
        value_bytes
        + decision_timestamp_bytes
        + bbo_tick_bytes
    )

    if total > FEATURE_CACHE_MAX_BYTES:
        raise FeedBoundScheduleError(
            f"feature_cache_too_large:{total}"
        )

    return FeatureCacheLayout(
        decision_count=n,
        candidate_grid_cases=FEATURE_CACHE_CANDIDATE_GRID_CASES,
        feature_count=FEATURE_CACHE_FEATURE_COUNT,
        value_bytes=value_bytes,
        decision_timestamp_bytes=decision_timestamp_bytes,
        bbo_tick_bytes=bbo_tick_bytes,
        total_bytes=total,
    )


def validate_r17_contract() -> None:
    r13a.validate_r13a_contract()
    r15.validate_r15_contract()
    r16.validate_r16_contract()

    if PARENT_R16_HEAD != (
        "6c37c3b7486c5cbd306bcb6b17583cde4e48175e"
    ):
        raise FeedBoundScheduleError("parent")

    if EXPECTED_SUCCESS_TERMINAL_REASON != "NATURAL_END_OF_DATA":
        raise FeedBoundScheduleError(
            "terminal_reason"
        )

    if FIXED_EVENT_TARGET is not None:
        raise FeedBoundScheduleError(
            "fixed_event_target"
        )

    if FIXED_WAKEUP_TARGET is not None:
        raise FeedBoundScheduleError(
            "fixed_wakeup_target"
        )

    if RAW_FEATURE_PASSES_PER_DAY != 1:
        raise FeedBoundScheduleError(
            "raw_feature_pass_count"
        )

    if FEATURE_CACHE_CANDIDATE_GRID_CASES != 8:
        raise FeedBoundScheduleError(
            "candidate_grid_cases"
        )

    if FEATURE_CACHE_FEATURE_COUNT != 25:
        raise FeedBoundScheduleError(
            "feature_count"
        )

    # Full nominal 24h grid must remain well below the frozen 256MiB budget.
    max_nominal_decisions = len(
        range(
            r1.FEATURE_WARMUP_NS,
            NOMINAL_DAY_NS,
            p0.DECISION_STEP_NS,
        )
    )

    layout = feature_cache_layout(
        decision_count=max_nominal_decisions,
    )

    if layout.total_bytes >= FEATURE_CACHE_MAX_BYTES:
        raise FeedBoundScheduleError(
            "nominal_cache_budget"
        )

    required = (
        FEED_BOUND_SCHEDULER_FROZEN,
        SHARED_DAY_FEATURE_CACHE_CONTRACT_FROZEN,
        NATURAL_END_OF_DATA_IS_VALID_TERMINAL,
        not REFERENCE_WAKEUP_COUNT_IS_STOP_CONDITION,
        not NOMINAL_DAY_END_IS_STOP_CONDITION,
        LAST_OBSERVED_LOCAL_FEED_TIMESTAMP_IS_DECISION_BOUND,
        DECISION_AT_EXACT_LAST_FEED_TIMESTAMP_ALLOWED,
        DECISION_AFTER_LAST_FEED_TIMESTAMP_FORBIDDEN,
        END_OF_SOURCE_CANDIDATES_RETAINED_WITH_CENSORING,
        not CENSORED_MAPS_TO_NO_FILL,
        PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN,
        FEATURE_CACHE_SHARED_ACROSS_ALL_40_LANES,
        DENSE_NUMPY_CACHE_REQUIRED,
        PYTHON_OBJECT_CACHE_FOR_REAL_DAY_FORBIDDEN,
        PREEXECUTION_ONLY,
        r13a.NATURAL_END_OF_SOURCE_IS_VALID_TERMINAL,
        r15.END_OF_SOURCE_CANDIDATES_RETAINED_WITH_CENSORING,
    )

    if not all(required):
        raise FeedBoundScheduleError(
            "required_guard"
        )

    forbidden = (
        HISTORICAL_FILE_IO_AUTHORIZED,
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        SIMULATOR_IMPORT_AUTHORIZED,
        CANDIDATE_SIMULATION_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
    )

    if any(forbidden):
        raise FeedBoundScheduleError(
            "execution_surface_open"
        )


__all__ = [
    "FeedBounds",
    "FeatureCacheLayout",
    "derive_feed_bounds",
    "build_phase_decisions",
    "build_shared_decision_grid",
    "feature_cache_layout",
    "validate_r17_contract",
]

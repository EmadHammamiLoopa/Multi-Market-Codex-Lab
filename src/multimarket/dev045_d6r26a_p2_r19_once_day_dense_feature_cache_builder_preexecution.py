from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from multimarket import (
    dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0,
)
from multimarket import (
    dev045_d6r26a_p1_synthetic_candidate_labeler as p1,
)
from multimarket import (
    dev045_d6r26a_p2_jan_jul_consumed_development_label_design as p2,
)
from multimarket import (
    dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1,
)
from multimarket import (
    dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b,
)
from multimarket import (
    dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9,
)
from multimarket import (
    dev045_d6r26a_p2_r10_bounded_feature_accumulator_freeze as r10,
)
from multimarket import (
    dev045_d6r26a_p2_r13_streaming_raw_decoder_preexecution as r13,
)
from multimarket import (
    dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17,
)
from multimarket import (
    dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R19"
DESIGN_VERSION = "once-day-dense-feature-cache-builder-preexecution-v1"
PARENT_R18_HEAD = "e6aa3eabd3a34e4f0fff5fec0192624d1d65a941"

ONCE_DAY_DENSE_FEATURE_CACHE_BUILDER_FROZEN = True
R13_LOCAL_STREAM_SEMANTICS_BOUND = True
R10_BOUNDED_FEATURE_ACCUMULATOR_BOUND = True
R17_REQUESTED_FEED_BOUND_GRID_BOUND = True
R18_DENSE_CACHE_CONSUMER_BOUND = True

RAW_EVENT_PASSES_PER_DAY = 1
EXCHANGE_MIDPOINT_PASS_FOR_FEATURE_CACHE = False
PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN = True
CACHE_SHARED_ACROSS_40_LANES = True

# R17 is the requested canonical one-second grid.
# P2 eligibility additionally requires a valid local BBO and a complete
# 30-second causal history. Requested epochs before that support exists are
# pre-candidate epochs, not rows that are created and then silently dropped.
REQUESTED_GRID_MAY_BEGIN_BEFORE_ACTUAL_FEATURE_SUPPORT = True
CACHE_CONTAINS_ELIGIBLE_CANDIDATE_EPOCHS_ONLY = True
LEADING_PREELIGIBLE_EPOCHS_AUDITED_NOT_DROPPED_ROWS = True
INELIGIBILITY_AFTER_FIRST_ELIGIBLE_EPOCH_FAILS_CLOSED = True
POST_ELIGIBILITY_MISSING_FEATURE_ROWS_FORBIDDEN = True

P2_ATTEMPT_CONSUMED = False
PREEXECUTION_ONLY = True
HISTORICAL_FILE_IO_AUTHORIZED = False
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_CANDIDATE_SIMULATION_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

_ELIGIBILITY_ERRORS_BEFORE_FIRST_SUCCESS = {
    "book_support_missing",
    "feature_warmup",
    "current_l5_support",
}


class OnceDayFeatureCacheError(RuntimeError):
    pass


@dataclass(frozen=True)
class FeatureCacheBuildSummary:
    requested_decision_count: int
    leading_preeligible_count: int
    eligible_decision_count: int
    first_requested_local_ns: int
    first_eligible_local_ns: int
    last_eligible_local_ns: int
    raw_event_pass_count: int


@dataclass(frozen=True)
class FeatureCacheBuildResult:
    bounds: r17.FeedBounds
    cache: r18.DenseFeatureCache
    summary: FeatureCacheBuildSummary


def _validate_event_surface(events: np.ndarray) -> np.ndarray:
    a = np.asarray(events)

    if a.ndim != 1 or a.size <= 0:
        raise OnceDayFeatureCacheError("event_array")

    if a.dtype.names is None:
        raise OnceDayFeatureCacheError("event_dtype")

    required = {
        "ev",
        "exch_ts",
        "local_ts",
        "px",
        "qty",
    }

    if not required.issubset(set(a.dtype.names)):
        raise OnceDayFeatureCacheError("event_fields")

    return a


def _case_matrix(
    *,
    accumulator: r10.RollingFeatureAccumulator,
    latest_book: r8b.BookObservation,
    decision_local_ns: int,
) -> np.ndarray:
    decision = int(decision_local_ns)

    matrix = np.empty(
        (
            r18.CANDIDATE_GRID_CASE_COUNT,
            len(r8b.FEATURE_NAMES),
        ),
        dtype=r17.FEATURE_CACHE_VALUE_DTYPE,
    )

    for case_index, (side, distance) in enumerate(
        r18.CANDIDATE_GRID
    ):
        candidate = p1.CandidateSpec(
            side=side,
            distance_ticks=int(distance),
            decision_local_ns=decision,
            best_bid_tick=int(
                latest_book.best_bid.price_tick
            ),
            best_ask_tick=int(
                latest_book.best_ask.price_tick
            ),
        )

        feature_vector = accumulator.compute(
            candidate=candidate,
        )

        if feature_vector.support != p2.CANDIDATE_ELIGIBILITY:
            raise OnceDayFeatureCacheError(
                "feature_support"
            )

        if tuple(feature_vector.values) != tuple(
            r8b.FEATURE_NAMES
        ):
            raise OnceDayFeatureCacheError(
                "feature_order"
            )

        if tuple(
            feature_vector.observable_local_ns
        ) != tuple(r8b.FEATURE_NAMES):
            raise OnceDayFeatureCacheError(
                "feature_observable_order"
            )

        if any(
            int(
                feature_vector.observable_local_ns[
                    name
                ]
            )
            != decision
            for name in r8b.FEATURE_NAMES
        ):
            raise OnceDayFeatureCacheError(
                "feature_observable_time"
            )

        matrix[
            case_index,
            :,
        ] = np.asarray(
            [
                float(feature_vector.values[name])
                for name in r8b.FEATURE_NAMES
            ],
            dtype=r17.FEATURE_CACHE_VALUE_DTYPE,
        )

    if not bool(np.isfinite(matrix).all()):
        raise OnceDayFeatureCacheError(
            "feature_nonfinite"
        )

    return matrix


def build_once_day_dense_feature_cache(
    events: np.ndarray,
    *,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
) -> FeatureCacheBuildResult:
    """
    One sequential raw-event pass.

    R17 supplies the requested one-second feed-bound grid. This builder begins
    cache materialization only at the first requested epoch satisfying the
    exact R10/P2 feature-support contract.

    Once eligibility has started, every remaining requested epoch MUST
    materialize successfully; there is no mid-day silent row dropping.
    """
    a = _validate_event_surface(events)

    bounds = r17.derive_feed_bounds(
        a,
        nominal_day_start_local_ns=int(
            nominal_day_start_local_ns
        ),
        nominal_day_end_exclusive_local_ns=int(
            nominal_day_end_exclusive_local_ns
        ),
    )

    requested = r17.build_shared_decision_grid(
        bounds=bounds,
    )

    if not requested:
        raise OnceDayFeatureCacheError(
            "requested_decision_grid_empty"
        )

    decoder = r13.LocalStreamingDecoder()
    accumulator = r10.RollingFeatureAccumulator()

    latest_book: r8b.BookObservation | None = None

    requested_index = 0
    leading_preeligible = 0

    out_decisions: np.ndarray | None = None
    out_bids: np.ndarray | None = None
    out_asks: np.ndarray | None = None
    out_values: np.ndarray | None = None

    out_index = 0
    first_eligible_requested_index: int | None = None

    def process_decision(decision: int) -> None:
        nonlocal leading_preeligible
        nonlocal out_decisions
        nonlocal out_bids
        nonlocal out_asks
        nonlocal out_values
        nonlocal out_index
        nonlocal first_eligible_requested_index

        if latest_book is None:
            if first_eligible_requested_index is None:
                leading_preeligible += 1
                return

            raise OnceDayFeatureCacheError(
                "book_missing_after_eligibility"
            )

        try:
            matrix = _case_matrix(
                accumulator=accumulator,
                latest_book=latest_book,
                decision_local_ns=int(decision),
            )
        except r10.BoundedFeatureAccumulatorError as exc:
            reason = str(exc)

            if (
                first_eligible_requested_index is None
                and reason
                in _ELIGIBILITY_ERRORS_BEFORE_FIRST_SUCCESS
            ):
                leading_preeligible += 1
                return

            raise OnceDayFeatureCacheError(
                f"feature_failure_after_eligibility:"
                f"{decision}:{reason}"
            ) from exc

        if first_eligible_requested_index is None:
            first_eligible_requested_index = (
                requested_index
            )

            remaining = (
                len(requested)
                - first_eligible_requested_index
            )

            out_decisions = np.empty(
                remaining,
                dtype="<i8",
            )
            out_bids = np.empty(
                remaining,
                dtype="<i8",
            )
            out_asks = np.empty(
                remaining,
                dtype="<i8",
            )
            out_values = np.empty(
                (
                    remaining,
                    r18.CANDIDATE_GRID_CASE_COUNT,
                    len(r8b.FEATURE_NAMES),
                ),
                dtype=r17.FEATURE_CACHE_VALUE_DTYPE,
            )

        assert out_decisions is not None
        assert out_bids is not None
        assert out_asks is not None
        assert out_values is not None

        out_decisions[out_index] = int(decision)
        out_bids[out_index] = int(
            latest_book.best_bid.price_tick
        )
        out_asks[out_index] = int(
            latest_book.best_ask.price_tick
        )
        out_values[out_index, :, :] = matrix

        out_index += 1

    def process_before(local_ns: int) -> None:
        nonlocal requested_index

        while (
            requested_index < len(requested)
            and int(requested[requested_index])
            < int(local_ns)
        ):
            process_decision(
                int(requested[requested_index])
            )
            requested_index += 1

    def ingest_group(
        group: r13.LocalGroupEmission,
    ) -> None:
        nonlocal latest_book
        nonlocal requested_index

        process_before(
            int(group.local_ns)
        )

        r13.feed_group_to_accumulator(
            accumulator=accumulator,
            emission=group,
        )

        if group.books:
            latest_book = group.books[-1]

        if (
            requested_index < len(requested)
            and int(requested[requested_index])
            == int(group.local_ns)
        ):
            process_decision(
                int(requested[requested_index])
            )
            requested_index += 1

    # The only full raw-event pass performed by this builder.
    for row in a:
        emissions = decoder.feed(row)

        for group in emissions:
            ingest_group(group)

    final_emissions = decoder.finish()

    for group in final_emissions:
        ingest_group(group)

    while requested_index < len(requested):
        process_decision(
            int(requested[requested_index])
        )
        requested_index += 1

    if first_eligible_requested_index is None:
        raise OnceDayFeatureCacheError(
            "no_eligible_feature_decision"
        )

    assert out_decisions is not None
    assert out_bids is not None
    assert out_asks is not None
    assert out_values is not None

    expected_eligible = (
        len(requested)
        - first_eligible_requested_index
    )

    if out_index != expected_eligible:
        raise OnceDayFeatureCacheError(
            f"eligible_count:{out_index}:"
            f"{expected_eligible}"
        )

    expected_decisions = np.asarray(
        requested[
            first_eligible_requested_index:
        ],
        dtype="<i8",
    )

    if not np.array_equal(
        out_decisions,
        expected_decisions,
    ):
        raise OnceDayFeatureCacheError(
            "eligible_grid_identity"
        )

    if leading_preeligible != first_eligible_requested_index:
        raise OnceDayFeatureCacheError(
            "leading_preeligible_count"
        )

    out_decisions.setflags(write=False)
    out_bids.setflags(write=False)
    out_asks.setflags(write=False)
    out_values.setflags(write=False)

    cache = r18.DenseFeatureCache(
        decision_local_ns=out_decisions,
        best_bid_tick=out_bids,
        best_ask_tick=out_asks,
        values=out_values,
    )

    r18.validate_dense_feature_cache(
        cache
    )

    summary = FeatureCacheBuildSummary(
        requested_decision_count=len(requested),
        leading_preeligible_count=(
            leading_preeligible
        ),
        eligible_decision_count=(
            cache.decision_count
        ),
        first_requested_local_ns=int(
            requested[0]
        ),
        first_eligible_local_ns=int(
            cache.decision_local_ns[0]
        ),
        last_eligible_local_ns=int(
            cache.decision_local_ns[-1]
        ),
        raw_event_pass_count=1,
    )

    return FeatureCacheBuildResult(
        bounds=bounds,
        cache=cache,
        summary=summary,
    )


def lane_decisions_from_cache(
    *,
    cache: r18.DenseFeatureCache,
    lane: r1.LaneSpec,
    day_start_local_ns: int,
) -> tuple[int, ...]:
    r18.validate_dense_feature_cache(
        cache
    )

    if lane.side not in p0.CANDIDATE_SIDES:
        raise OnceDayFeatureCacheError(
            "lane_side"
        )

    if int(lane.distance_ticks) not in (
        p0.CANDIDATE_DISTANCE_TICKS
    ):
        raise OnceDayFeatureCacheError(
            "lane_distance"
        )

    if int(lane.phase) not in (
        p0.LANE_PHASE_OFFSETS_S
    ):
        raise OnceDayFeatureCacheError(
            "lane_phase"
        )

    decisions = tuple(
        int(ts)
        for ts in cache.decision_local_ns
        if p1.lane_phase(
            day_start_local_ns=int(
                day_start_local_ns
            ),
            decision_local_ns=int(ts),
        )
        == int(lane.phase)
    )

    p1.assert_lane_isolation(
        decisions
    )

    return decisions


_EVENT_DTYPE = np.dtype(
    [
        ("ev", "<u8"),
        ("exch_ts", "<i8"),
        ("local_ts", "<i8"),
        ("px", "<f8"),
        ("qty", "<f8"),
    ]
)


def make_synthetic_feature_fixture() -> np.ndarray:
    """
    Synthetic local-only feature stream.

    First complete book is at 1s, so the requested 30s epoch is intentionally
    preeligible while 31s has the full causal 30-second history. This is the
    anti-regression case that exposed the R17/R10 boundary.
    """
    rows: list[
        tuple[int, int, int, float, float]
    ] = []

    snapshot = (
        r9.LOCAL_EVENT
        | r9.DEPTH_SNAPSHOT_EVENT
    )

    for level, qty in enumerate(
        (5.0, 4.0, 3.0, 2.0, 1.0)
    ):
        rows.append(
            (
                snapshot | r9.BUY_EVENT,
                900_000_000,
                1_000_000_000,
                100.0 - 0.1 * level,
                qty,
            )
        )

    for level, qty in enumerate(
        (6.0, 5.0, 4.0, 3.0, 2.0)
    ):
        rows.append(
            (
                snapshot | r9.SELL_EVENT,
                900_000_000,
                1_000_000_000,
                100.1 + 0.1 * level,
                qty,
            )
        )

    bid_depth = (
        r9.LOCAL_EVENT
        | r9.DEPTH_EVENT
        | r9.BUY_EVENT
    )

    ask_depth = (
        r9.LOCAL_EVENT
        | r9.DEPTH_EVENT
        | r9.SELL_EVENT
    )

    buy_trade = (
        r9.LOCAL_EVENT
        | r9.TRADE_EVENT
        | r9.BUY_EVENT
    )

    sell_trade = (
        r9.LOCAL_EVENT
        | r9.TRADE_EVENT
        | r9.SELL_EVENT
    )

    k = 0

    for local_ns in range(
        1_250_000_000,
        47_500_000_001,
        250_000_000,
    ):
        bid_qty = (
            5.0
            + 0.1 * ((k % 5) + 1)
        )
        ask_qty = (
            6.0
            + 0.1 * (((k + 2) % 5) + 1)
        )

        rows.append(
            (
                bid_depth,
                local_ns - 10_000_000,
                local_ns,
                100.0,
                bid_qty,
            )
        )

        rows.append(
            (
                ask_depth,
                local_ns - 9_000_000,
                local_ns,
                100.1,
                ask_qty,
            )
        )

        if local_ns % 1_000_000_000 == 0:
            trade_local = (
                local_ns + 50_000_000
            )

            rows.append(
                (
                    buy_trade
                    if (k // 4) % 2 == 0
                    else sell_trade,
                    trade_local
                    - 5_000_000,
                    trade_local,
                    100.1
                    if (k // 4) % 2 == 0
                    else 100.0,
                    0.05
                    + 0.01 * ((k // 4) % 3),
                )
            )

        k += 1

    rows.sort(
        key=lambda x: (
            x[2],
            x[1],
        )
    )

    out = np.zeros(
        len(rows),
        dtype=_EVENT_DTYPE,
    )

    for i, row in enumerate(rows):
        out[i]["ev"] = row[0]
        out[i]["exch_ts"] = row[1]
        out[i]["local_ts"] = row[2]
        out[i]["px"] = row[3]
        out[i]["qty"] = row[4]

    return out


def validate_r19_contract() -> None:
    r10.validate_r10_contract()
    r17.validate_r17_contract()
    r18.validate_r18_contract()

    if PARENT_R18_HEAD != (
        "e6aa3eabd3a34e4f0fff5fec0192624d1d65a941"
    ):
        raise OnceDayFeatureCacheError(
            "parent"
        )

    if RAW_EVENT_PASSES_PER_DAY != 1:
        raise OnceDayFeatureCacheError(
            "raw_pass_count"
        )

    required = (
        ONCE_DAY_DENSE_FEATURE_CACHE_BUILDER_FROZEN,
        R13_LOCAL_STREAM_SEMANTICS_BOUND,
        R10_BOUNDED_FEATURE_ACCUMULATOR_BOUND,
        R17_REQUESTED_FEED_BOUND_GRID_BOUND,
        R18_DENSE_CACHE_CONSUMER_BOUND,
        not EXCHANGE_MIDPOINT_PASS_FOR_FEATURE_CACHE,
        PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN,
        CACHE_SHARED_ACROSS_40_LANES,
        REQUESTED_GRID_MAY_BEGIN_BEFORE_ACTUAL_FEATURE_SUPPORT,
        CACHE_CONTAINS_ELIGIBLE_CANDIDATE_EPOCHS_ONLY,
        LEADING_PREELIGIBLE_EPOCHS_AUDITED_NOT_DROPPED_ROWS,
        INELIGIBILITY_AFTER_FIRST_ELIGIBLE_EPOCH_FAILS_CLOSED,
        POST_ELIGIBILITY_MISSING_FEATURE_ROWS_FORBIDDEN,
        P2_ATTEMPT_CONSUMED is False,
        PREEXECUTION_ONLY,
        p2.MISSING_FEATURE_ROWS_DROPPED is False,
        p2.CANDIDATE_ELIGIBILITY
        == (
            "VALID_LOCAL_BBO_AND_30S_CAUSAL_"
            "FEATURE_HISTORY_AT_DECISION_EPOCH"
        ),
        r17.RAW_FEATURE_PASSES_PER_DAY == 1,
        r17.PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN,
        r17.FEATURE_CACHE_SHARED_ACROSS_ALL_40_LANES,
    )

    if not all(required):
        raise OnceDayFeatureCacheError(
            "required_guard"
        )

    forbidden = (
        HISTORICAL_FILE_IO_AUTHORIZED,
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_CANDIDATE_SIMULATION_AUTHORIZED,
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
        raise OnceDayFeatureCacheError(
            "execution_surface_open"
        )


__all__ = [
    "FeatureCacheBuildResult",
    "FeatureCacheBuildSummary",
    "build_once_day_dense_feature_cache",
    "lane_decisions_from_cache",
    "make_synthetic_feature_fixture",
    "validate_r19_contract",
]

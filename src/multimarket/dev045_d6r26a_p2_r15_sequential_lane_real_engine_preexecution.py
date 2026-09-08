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
    dev045_d6r26a_p2_r5_real_engine_binding_prehistorical as r5,
)
from multimarket import (
    dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b,
)
from multimarket import (
    dev045_d6r26a_p2_r10_bounded_feature_accumulator_freeze as r10,
)
from multimarket import (
    dev045_d6r26a_p2_r11_synthetic_real_engine_lane_lifecycle as r11,
)
from multimarket import (
    dev045_d6r26a_p2_r12_one_day_lane_driver_preexecution as r12,
)
from multimarket import (
    dev045_d6r26a_p2_r13_streaming_raw_decoder_preexecution as r13,
)
from multimarket import (
    dev045_d6r26a_p2_r13a_dual_stream_eof_memory_amendment as r13a,
)
from multimarket import (
    dev045_d6r26a_p2_r14_synthetic_candidate_grid_real_engine_preexecution as r14,
)
from multimarket import dev045_m4_adapter as m4


EXPERIMENT_ID = "DEV045-D6R26A-P2-R15"
DESIGN_VERSION = "sequential-lane-real-engine-preexecution-v1"
PARENT_R14_HEAD = "7f95b3f4e4173e0118d486681075f01f6c6b85e7"

SYNTHETIC_REAL_ENGINE_ONLY = True
SEQUENTIAL_SAME_ENGINE_LANE_FROZEN = True

SEQUENTIAL_DECISION_LOCAL_NS = (
    31_000_000_000,
    36_000_000_000,
    41_000_000_000,
)
CANDIDATES_PER_SYNTHETIC_LANE = 3

DECISION_SPACING_NS = p0.MAX_CANDIDATE_LIFETIME_NS
PREVIOUS_TERMINAL_BEFORE_NEXT_PLACEMENT = True
EQUAL_TIMESTAMP_TERMINAL_THEN_PLACEMENT = True

R11_CANCEL_LATENCY_FIX_BOUND = True
R13A_DUAL_STREAM_BOUND = True
R14_SIDE_GRID_ENGINE_BOUND = True

NATURAL_END_OF_SOURCE_IS_VALID_TERMINAL = True
FIXED_EVENT_TARGET = None
FIXED_WAKEUP_TARGET = None
TOTAL_RSS_ABORT_THRESHOLD_BYTES = None
TOTAL_RSS_IS_BOUNDEDNESS_GATE = False

END_OF_SOURCE_CANDIDATES_RETAINED_WITH_CENSORING = True
CENSORED_MAPS_TO_NO_FILL = False

PREEXECUTION_ONLY = True
HISTORICAL_FILE_IO_AUTHORIZED = False
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
CANONICAL_HISTORICAL_RUN_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False


class SequentialLaneError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScheduledCandidate:
    candidate: p1.CandidateSpec
    feature_vector: r8b.FeatureVector


@dataclass(frozen=True)
class SequentialCandidateResult:
    candidate: p1.CandidateSpec
    feature_vector: r8b.FeatureVector
    order_id: int
    placement_outcome: str
    final_status: int
    ack_latency_triplet: tuple[int, int, int]
    cancel_latency_triplet: tuple[int, int, int]
    cancel_request_local_ns: int
    terminal_local_ns: int


@dataclass(frozen=True)
class SequentialLaneResult:
    side: str
    distance_ticks: int
    candidates: tuple[SequentialCandidateResult, ...]


def make_sequential_fixture() -> np.ndarray:
    h = r11._imports()
    base = r11.make_lifecycle_fixture(with_fill=False)

    extra_rows: list[tuple[int, int, int, float, float]] = []

    depth_ask = int(
        h.EXCH_EVENT
        | h.LOCAL_EVENT
        | h.DEPTH_EVENT
        | h.SELL_EVENT
    )

    # Extend well beyond the third candidate's 46s terminal.
    for k, local_ns in enumerate(
        range(
            38_000_000_000,
            48_000_000_000,
            500_000_000,
        )
    ):
        qty = 6.0 + (0.1 if k % 2 else 0.0)
        extra_rows.append(
            (
                depth_ask,
                local_ns - 10_000_000,
                local_ns,
                100.1,
                qty,
            )
        )

    extra = np.zeros(len(extra_rows), dtype=base.dtype)

    for i, (ev, exch, local, px, qty) in enumerate(extra_rows):
        r11._row(
            extra,
            i,
            ev=ev,
            exch_ns=exch,
            local_ns=local,
            px=px,
            qty=qty,
        )

    data = np.concatenate((base, extra))
    order = np.lexsort(
        (
            data["exch_ts"],
            data["local_ts"],
        )
    )
    data = data[order]

    m4.validate_events(data)
    return data


def _make_scheduled_candidate(
    *,
    latest_book: r8b.BookObservation,
    accumulator: r10.RollingFeatureAccumulator,
    side: str,
    distance_ticks: int,
    decision_local_ns: int,
) -> ScheduledCandidate:
    candidate = p1.CandidateSpec(
        side=side,
        distance_ticks=int(distance_ticks),
        decision_local_ns=int(decision_local_ns),
        best_bid_tick=int(latest_book.best_bid.price_tick),
        best_ask_tick=int(latest_book.best_ask.price_tick),
    )

    features = accumulator.compute(candidate=candidate)

    p1.validate_feature_observability(
        decision_local_ns=int(decision_local_ns),
        feature_observable_local_ns=features.observable_local_ns,
    )

    return ScheduledCandidate(
        candidate=candidate,
        feature_vector=features,
    )


def build_streaming_schedule(
    data: np.ndarray,
    *,
    side: str,
    distance_ticks: int,
) -> tuple[ScheduledCandidate, ...]:
    decoder = r13a.DualStreamingDecoder()
    accumulator = r10.RollingFeatureAccumulator()

    decisions = tuple(SEQUENTIAL_DECISION_LOCAL_NS)
    next_index = 0

    latest_book: r8b.BookObservation | None = None
    scheduled: list[ScheduledCandidate] = []

    def capture_before(local_ns: int) -> None:
        nonlocal next_index

        while (
            next_index < len(decisions)
            and decisions[next_index] < int(local_ns)
        ):
            if latest_book is None:
                raise SequentialLaneError(
                    "decision_book_missing_before_group"
                )

            scheduled.append(
                _make_scheduled_candidate(
                    latest_book=latest_book,
                    accumulator=accumulator,
                    side=side,
                    distance_ticks=distance_ticks,
                    decision_local_ns=decisions[next_index],
                )
            )
            next_index += 1

    def ingest_group(group: r13.LocalGroupEmission) -> None:
        nonlocal latest_book, next_index

        capture_before(group.local_ns)

        r13.feed_group_to_accumulator(
            accumulator=accumulator,
            emission=group,
        )

        if group.books:
            latest_book = group.books[-1]

        if (
            next_index < len(decisions)
            and decisions[next_index] == group.local_ns
        ):
            if latest_book is None:
                raise SequentialLaneError(
                    "decision_book_missing_at_group"
                )

            scheduled.append(
                _make_scheduled_candidate(
                    latest_book=latest_book,
                    accumulator=accumulator,
                    side=side,
                    distance_ticks=distance_ticks,
                    decision_local_ns=decisions[next_index],
                )
            )
            next_index += 1

    for row in data:
        emitted = decoder.feed(row)

        for group in emitted.local_groups:
            ingest_group(group)

    final = decoder.finish()

    for group in final.local_groups:
        ingest_group(group)

    if next_index != len(decisions):
        if latest_book is None:
            raise SequentialLaneError(
                "final_decision_book_missing"
            )

        while next_index < len(decisions):
            scheduled.append(
                _make_scheduled_candidate(
                    latest_book=latest_book,
                    accumulator=accumulator,
                    side=side,
                    distance_ticks=distance_ticks,
                    decision_local_ns=decisions[next_index],
                )
            )
            next_index += 1

    if len(scheduled) != CANDIDATES_PER_SYNTHETIC_LANE:
        raise SequentialLaneError(
            "schedule_cardinality"
        )

    if tuple(
        x.candidate.decision_local_ns
        for x in scheduled
    ) != decisions:
        raise SequentialLaneError(
            "schedule_decision_identity"
        )

    return tuple(scheduled)


def run_sequential_lane(
    *,
    side: str,
    distance_ticks: int = 0,
) -> SequentialLaneResult:
    if side not in p0.CANDIDATE_SIDES:
        raise SequentialLaneError("side")

    if int(distance_ticks) not in p0.CANDIDATE_DISTANCE_TICKS:
        raise SequentialLaneError("distance")

    r5.verify_engine_identity()

    data = make_sequential_fixture()

    schedule = build_streaming_schedule(
        data,
        side=side,
        distance_ticks=int(distance_ticks),
    )

    h, bt = r11._new_backtest(data)

    results: list[SequentialCandidateResult] = []

    try:
        r11._initialize_clock(bt)

        for index, scheduled in enumerate(schedule):
            candidate = scheduled.candidate
            decision = int(candidate.decision_local_ns)

            if int(bt.current_timestamp) > decision:
                raise SequentialLaneError(
                    f"decision_already_passed:{index}:"
                    f"{bt.current_timestamp}:{decision}"
                )

            if int(bt.current_timestamp) < decision:
                r11._advance_to(bt, decision)

            if int(bt.current_timestamp) != decision:
                raise SequentialLaneError(
                    "decision_timestamp"
                )

            # After candidate zero, this equality proves the previous
            # cancel response completed exactly at the next decision.
            if index > 0:
                previous = results[-1]

                if previous.terminal_local_ns != decision:
                    raise SequentialLaneError(
                        "previous_terminal_not_next_decision"
                    )

                if (
                    previous.final_status
                    != p1.HFT_CANCELED
                ):
                    raise SequentialLaneError(
                        "previous_order_not_terminal"
                    )

            depth = bt.depth(0)

            if (
                int(depth.best_bid_tick)
                != candidate.best_bid_tick
                or int(depth.best_ask_tick)
                != candidate.best_ask_tick
            ):
                raise SequentialLaneError(
                    "engine_feature_bbo_mismatch"
                )

            order_id = (
                71500
                + (100 if side == "ASK" else 0)
                + index
            )

            submit_rc = r14._submit_candidate(
                h=h,
                bt=bt,
                candidate=candidate,
                order_id=order_id,
            )

            if submit_rc != 0:
                raise SequentialLaneError(
                    f"submit_rc:{index}:{submit_rc}"
                )

            order = bt.orders(0).get(order_id)

            if order is None:
                raise SequentialLaneError(
                    "order_missing_after_ack"
                )

            placement = p1.classify_gtx_placement_status(
                int(order.status)
            )

            if placement != p1.POST_ONLY_ACCEPTED:
                raise SequentialLaneError(
                    f"placement:{index}:{placement}"
                )

            ack_raw = bt.order_latency(0)

            if ack_raw is None:
                raise SequentialLaneError(
                    "ack_latency_missing"
                )

            ack_latency = tuple(map(int, ack_raw))

            expected_ack = (
                decision,
                decision + p0.ENTRY_LATENCY_NS,
                decision
                + p0.ENTRY_LATENCY_NS
                + p0.RESPONSE_LATENCY_NS,
            )

            if ack_latency != expected_ack:
                raise SequentialLaneError(
                    f"ack_latency:{index}:{ack_latency}"
                )

            cancel_request = (
                decision
                + p0.MAX_CANDIDATE_LIFETIME_NS
                - p0.ENTRY_LATENCY_NS
                - p0.RESPONSE_LATENCY_NS
            )

            terminal = (
                decision
                + p0.MAX_CANDIDATE_LIFETIME_NS
            )

            # No event-count/wakeup-count stopping condition.
            while int(bt.current_timestamp) < cancel_request:
                timeout = (
                    cancel_request
                    - int(bt.current_timestamp)
                )

                wait_rc = int(
                    bt.wait_next_feed(
                        True,
                        timeout,
                    )
                )

                if wait_rc == 1:
                    break

                if wait_rc not in (0, 2, 3):
                    raise SequentialLaneError(
                        f"wait_rc:{index}:{wait_rc}"
                    )

                if wait_rc == 3:
                    order = bt.orders(0).get(order_id)

                    if order is None:
                        raise SequentialLaneError(
                            "order_missing_on_response"
                        )

                    fill = r11._capture_fill_response(
                        bt,
                        order,
                    )

                    if fill is not None:
                        raise SequentialLaneError(
                            "unexpected_fill_in_no_fill_lane"
                        )

                if wait_rc == 0:
                    break

            order = bt.orders(0).get(order_id)

            if (
                order is None
                or int(order.status)
                not in (
                    p1.HFT_NEW,
                    p1.HFT_PARTIALLY_FILLED,
                )
            ):
                raise SequentialLaneError(
                    "order_not_working_pre_cancel"
                )

            r11._advance_to(
                bt,
                cancel_request,
            )

            if int(bt.current_timestamp) != cancel_request:
                raise SequentialLaneError(
                    "cancel_request_clock"
                )

            cancel_rc = int(
                bt.cancel(
                    0,
                    order_id,
                    True,
                )
            )

            if cancel_rc != 0:
                raise SequentialLaneError(
                    f"cancel_rc:{index}:{cancel_rc}"
                )

            order = bt.orders(0).get(order_id)

            if (
                order is None
                or int(order.status) != p1.HFT_CANCELED
            ):
                raise SequentialLaneError(
                    "cancel_not_terminal"
                )

            if int(bt.current_timestamp) != terminal:
                raise SequentialLaneError(
                    f"terminal_clock:{index}:"
                    f"{bt.current_timestamp}:{terminal}"
                )

            cancel_raw = bt.order_latency(0)

            if cancel_raw is None:
                raise SequentialLaneError(
                    "cancel_latency_missing"
                )

            cancel_latency = tuple(
                map(int, cancel_raw)
            )

            # Exact R11 correction: first field remains the
            # original NEW request local timestamp.
            expected_cancel = (
                decision,
                cancel_request + p0.ENTRY_LATENCY_NS,
                terminal,
            )

            if cancel_latency != expected_cancel:
                raise SequentialLaneError(
                    f"cancel_latency:{index}:"
                    f"{cancel_latency}"
                )

            results.append(
                SequentialCandidateResult(
                    candidate=candidate,
                    feature_vector=scheduled.feature_vector,
                    order_id=order_id,
                    placement_outcome=placement,
                    final_status=int(order.status),
                    ack_latency_triplet=ack_latency,
                    cancel_latency_triplet=cancel_latency,
                    cancel_request_local_ns=cancel_request,
                    terminal_local_ns=terminal,
                )
            )

    finally:
        close_rc = int(bt.close())

        if close_rc != 0:
            raise SequentialLaneError(
                f"bt_close_rc:{close_rc}"
            )

    return SequentialLaneResult(
        side=side,
        distance_ticks=int(distance_ticks),
        candidates=tuple(results),
    )


def eof_fill_label_probe() -> tuple[p1.FillHorizonLabel, ...]:
    """
    Pure anti-regression probe.

    Candidate remains in the dataset near EOF. Horizons that are not fully
    observable are CENSORED, never silently dropped and never converted to
    NOT_FILLED.
    """
    candidate = p1.CandidateSpec(
        side="BID",
        distance_ticks=0,
        decision_local_ns=46_000_000_000,
        best_bid_tick=1000,
        best_ask_tick=1001,
    )

    observed_through = 47_000_000_000

    return tuple(
        p1.fill_horizon_label(
            candidate=candidate,
            fills=(),
            horizon_ns=int(horizon),
            source_exchange_observed_through_ns=observed_through,
            placement_outcome=p1.POST_ONLY_ACCEPTED,
        )
        for horizon in p0.FILL_HORIZONS_NS
    )


def validate_r15_contract() -> None:
    r11.validate_r11_contract()
    r12.validate_r12_contract()
    r13a.validate_r13a_contract()
    r14.validate_r14_contract()

    if PARENT_R14_HEAD != (
        "7f95b3f4e4173e0118d486681075f01f6c6b85e7"
    ):
        raise SequentialLaneError("parent")

    if SEQUENTIAL_DECISION_LOCAL_NS != (
        31_000_000_000,
        36_000_000_000,
        41_000_000_000,
    ):
        raise SequentialLaneError(
            "decision_schedule"
        )

    if any(
        b - a != p0.MAX_CANDIDATE_LIFETIME_NS
        for a, b in zip(
            SEQUENTIAL_DECISION_LOCAL_NS,
            SEQUENTIAL_DECISION_LOCAL_NS[1:],
        )
    ):
        raise SequentialLaneError(
            "decision_spacing"
        )

    p1.assert_lane_isolation(
        SEQUENTIAL_DECISION_LOCAL_NS
    )

    required = (
        SYNTHETIC_REAL_ENGINE_ONLY,
        SEQUENTIAL_SAME_ENGINE_LANE_FROZEN,
        PREVIOUS_TERMINAL_BEFORE_NEXT_PLACEMENT,
        EQUAL_TIMESTAMP_TERMINAL_THEN_PLACEMENT,
        R11_CANCEL_LATENCY_FIX_BOUND,
        R13A_DUAL_STREAM_BOUND,
        R14_SIDE_GRID_ENGINE_BOUND,
        NATURAL_END_OF_SOURCE_IS_VALID_TERMINAL,
        END_OF_SOURCE_CANDIDATES_RETAINED_WITH_CENSORING,
        not CENSORED_MAPS_TO_NO_FILL,
        PREEXECUTION_ONLY,
        r11.CANCEL_LATENCY_FIRST_FIELD_IS_ORIGINAL_ORDER_LOCAL_TIMESTAMP,
        r13a.NATURAL_END_OF_SOURCE_IS_VALID_TERMINAL,
        r13a.FINAL_TIMESTAMP_GROUP_FLUSH_REQUIRED,
    )

    if not all(required):
        raise SequentialLaneError(
            "required_guard"
        )

    if FIXED_EVENT_TARGET is not None:
        raise SequentialLaneError(
            "fixed_event_target"
        )

    if FIXED_WAKEUP_TARGET is not None:
        raise SequentialLaneError(
            "fixed_wakeup_target"
        )

    if TOTAL_RSS_ABORT_THRESHOLD_BYTES is not None:
        raise SequentialLaneError(
            "rss_abort_gate"
        )

    if TOTAL_RSS_IS_BOUNDEDNESS_GATE:
        raise SequentialLaneError(
            "rss_boundedness_gate"
        )

    forbidden = (
        HISTORICAL_FILE_IO_AUTHORIZED,
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        CANONICAL_HISTORICAL_RUN_AUTHORIZED,
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
        raise SequentialLaneError(
            "execution_surface_open"
        )


__all__ = [
    "SequentialLaneResult",
    "build_streaming_schedule",
    "eof_fill_label_probe",
    "make_sequential_fixture",
    "run_sequential_lane",
    "validate_r15_contract",
]

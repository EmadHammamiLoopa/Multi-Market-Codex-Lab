from __future__ import annotations

from dataclasses import dataclass
import math

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
    dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9,
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
from multimarket import dev045_m4_adapter as m4


EXPERIMENT_ID = "DEV045-D6R26A-P2-R14"
DESIGN_VERSION = "synthetic-candidate-grid-real-engine-preexecution-v1"
PARENT_R13A_HEAD = "37b45cdfcd36e40149b549c0d611c514a3d91f51"

SYNTHETIC_REAL_ENGINE_ONLY = True
CANDIDATE_GRID_REAL_ENGINE_PREEXECUTION_FROZEN = True

R11_EXACT_ENGINE_LIFECYCLE_BOUND = True
R12_40_LANE_ORCHESTRATION_BOUND = True
R13A_BOUNDED_DUAL_STREAM_BOUND = True

CANDIDATE_GRID = tuple(
    (side, int(distance))
    for side in p0.CANDIDATE_SIDES
    for distance in p0.CANDIDATE_DISTANCE_TICKS
)
CANDIDATE_GRID_CASE_COUNT = 8
PHASE_COUNT = len(p0.LANE_PHASE_OFFSETS_S)
CANONICAL_LANES_PER_DAY = 40

# Fill mechanics are probed symmetrically at the BBO. Deeper-distance cases
# are still submitted through the exact engine and terminated by exact cancel.
FILL_PROBE_GRID = (
    ("BID", 0),
    ("ASK", 0),
)

DECISION_LOCAL_NS = r11.DECISION_LOCAL_NS
CANCEL_REQUEST_LOCAL_NS = r11.CANCEL_REQUEST_LOCAL_NS
CANDIDATE_TERMINAL_BOUNDARY_NS = r11.CANDIDATE_TERMINAL_BOUNDARY_NS

NO_FIXED_EVENT_TARGET = True
NO_FIXED_WAKEUP_TARGET = True
NATURAL_END_OF_SOURCE_RULE_BOUND = True
TOTAL_RSS_NOT_BOUNDEDNESS_GATE = True

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


class CandidateGridRealEngineError(RuntimeError):
    pass


@dataclass(frozen=True)
class CandidateGridResult:
    side: str
    distance_ticks: int
    with_fill: bool
    candidate: p1.CandidateSpec
    feature_vector: r8b.FeatureVector
    placement_outcome: str
    fills: tuple[p1.FillObservation, ...]
    labels: r8b.LabelBundle
    final_status: int
    final_local_ns: int
    canceled_at_boundary: bool
    ack_latency_triplet: tuple[int, int, int]
    cancel_latency_triplet: tuple[int, int, int] | None
    source_exchange_observed_through_ns: int


def _validate_case(
    *,
    side: str,
    distance_ticks: int,
    with_fill: bool,
) -> None:
    if side not in p0.CANDIDATE_SIDES:
        raise CandidateGridRealEngineError("candidate_side")

    if int(distance_ticks) not in p0.CANDIDATE_DISTANCE_TICKS:
        raise CandidateGridRealEngineError("candidate_distance")

    if with_fill and (side, int(distance_ticks)) not in FILL_PROBE_GRID:
        raise CandidateGridRealEngineError(
            "fill_probe_only_at_bbo"
        )


def _ask_fill_fixture() -> np.ndarray:
    base = r11.make_lifecycle_fixture(with_fill=False)
    h = r11._imports()

    extra = np.zeros(2, dtype=base.dtype)

    buy_trade = int(
        h.EXCH_EVENT
        | h.LOCAL_EVENT
        | h.TRADE_EVENT
        | h.BUY_EVENT
    )

    # Exact mirror of R11 BID fill probe:
    # consume displayed queue at best ask, then fill own 0.001.
    r11._row(
        extra,
        0,
        ev=buy_trade,
        exch_ns=31_600_000_000,
        local_ns=31_610_000_000,
        px=100.1,
        qty=6.0,
    )
    r11._row(
        extra,
        1,
        ev=buy_trade,
        exch_ns=31_800_000_000,
        local_ns=31_810_000_000,
        px=100.1,
        qty=p0.CANDIDATE_ORDER_QTY,
    )

    out = np.concatenate((base, extra))
    order = np.lexsort((out["exch_ts"], out["local_ts"]))
    out = out[order]

    m4.validate_events(out)
    return out


def make_grid_fixture(
    *,
    side: str,
    distance_ticks: int,
    with_fill: bool,
) -> np.ndarray:
    _validate_case(
        side=side,
        distance_ticks=distance_ticks,
        with_fill=with_fill,
    )

    if side == "BID":
        return r11.make_lifecycle_fixture(
            with_fill=with_fill,
        )

    if with_fill:
        return _ask_fill_fixture()

    return r11.make_lifecycle_fixture(with_fill=False)


def _ingest_local_emissions(
    *,
    accumulator: r10.RollingFeatureAccumulator,
    emissions: tuple[r13.LocalGroupEmission, ...],
) -> r8b.BookObservation | None:
    latest: r8b.BookObservation | None = None

    for emission in emissions:
        r13.feed_group_to_accumulator(
            accumulator=accumulator,
            emission=emission,
        )

        if emission.books:
            latest = emission.books[-1]

    return latest


def _stream_context(
    data: np.ndarray,
    *,
    side: str,
    distance_ticks: int,
) -> tuple[
    p1.CandidateSpec,
    r8b.FeatureVector,
    tuple[p1.MidObservation, ...],
    int,
]:
    # Feature side is causal and ends exactly at decision local time.
    causal = data[data["local_ts"] <= DECISION_LOCAL_NS]

    decoder = r13a.DualStreamingDecoder()
    accumulator = r10.RollingFeatureAccumulator()
    latest_book: r8b.BookObservation | None = None

    for row in causal:
        emitted = decoder.feed(row)

        book = _ingest_local_emissions(
            accumulator=accumulator,
            emissions=emitted.local_groups,
        )
        if book is not None:
            latest_book = book

    final = decoder.finish()

    book = _ingest_local_emissions(
        accumulator=accumulator,
        emissions=final.local_groups,
    )
    if book is not None:
        latest_book = book

    if latest_book is None:
        raise CandidateGridRealEngineError(
            "decision_book_missing"
        )

    candidate = p1.CandidateSpec(
        side=side,
        distance_ticks=int(distance_ticks),
        decision_local_ns=DECISION_LOCAL_NS,
        best_bid_tick=int(latest_book.best_bid.price_tick),
        best_ask_tick=int(latest_book.best_ask.price_tick),
    )

    features = accumulator.compute(candidate=candidate)

    # Synthetic fixture only: materialize the short midpoint sequence solely
    # to prove exact R9 parity and frozen label semantics. Historical real
    # execution remains required to consume the R13A iterator incrementally.
    midpoints = tuple(
        r13a.iter_exchange_midpoints(data)
    )

    if midpoints != r9.decode_exchange_midpoints(data):
        raise CandidateGridRealEngineError(
            "exchange_stream_r9_parity"
        )

    observed_through = int(np.max(data["exch_ts"]))

    return (
        candidate,
        features,
        midpoints,
        observed_through,
    )


def _submit_candidate(
    *,
    h,
    bt,
    candidate: p1.CandidateSpec,
    order_id: int,
) -> int:
    if candidate.side == "BID":
        return int(
            bt.submit_buy_order(
                0,
                order_id,
                candidate.price,
                float(candidate.qty),
                h.GTX,
                h.LIMIT,
                True,
            )
        )

    return int(
        bt.submit_sell_order(
            0,
            order_id,
            candidate.price,
            float(candidate.qty),
            h.GTX,
            h.LIMIT,
            True,
        )
    )


def run_grid_case(
    *,
    side: str,
    distance_ticks: int,
    with_fill: bool,
) -> CandidateGridResult:
    _validate_case(
        side=side,
        distance_ticks=distance_ticks,
        with_fill=with_fill,
    )

    r5.verify_engine_identity()

    data = make_grid_fixture(
        side=side,
        distance_ticks=distance_ticks,
        with_fill=with_fill,
    )

    (
        candidate,
        features,
        midpoints,
        observed_through,
    ) = _stream_context(
        data,
        side=side,
        distance_ticks=distance_ticks,
    )

    h, bt = r11._new_backtest(data)

    order_id = (
        71400
        + (100 if side == "ASK" else 0)
        + int(distance_ticks)
    )

    fills: list[p1.FillObservation] = []
    canceled = False
    placement: str | None = None
    ack_latency: tuple[int, int, int] | None = None
    cancel_latency: tuple[int, int, int] | None = None

    try:
        r11._initialize_clock(bt)
        r11._advance_to(bt, DECISION_LOCAL_NS)

        depth = bt.depth(0)

        if (
            int(depth.best_bid_tick) != candidate.best_bid_tick
            or int(depth.best_ask_tick) != candidate.best_ask_tick
        ):
            raise CandidateGridRealEngineError(
                "engine_feature_bbo_mismatch"
            )

        submit_rc = _submit_candidate(
            h=h,
            bt=bt,
            candidate=candidate,
            order_id=order_id,
        )

        if submit_rc != 0:
            raise CandidateGridRealEngineError(
                f"submit_rc:{side}:{distance_ticks}:{submit_rc}"
            )

        order = bt.orders(0).get(order_id)

        if order is None:
            raise CandidateGridRealEngineError(
                "order_missing_after_ack"
            )

        placement = p1.classify_gtx_placement_status(
            int(order.status)
        )

        if placement != p1.POST_ONLY_ACCEPTED:
            raise CandidateGridRealEngineError(
                f"placement:{side}:{distance_ticks}:{placement}"
            )

        latency_raw = bt.order_latency(0)

        if latency_raw is None:
            raise CandidateGridRealEngineError(
                "ack_latency_missing"
            )

        ack_latency = tuple(map(int, latency_raw))

        expected_ack = (
            DECISION_LOCAL_NS,
            DECISION_LOCAL_NS + p0.ENTRY_LATENCY_NS,
            DECISION_LOCAL_NS
            + p0.ENTRY_LATENCY_NS
            + p0.RESPONSE_LATENCY_NS,
        )

        if ack_latency != expected_ack:
            raise CandidateGridRealEngineError(
                f"ack_latency:{ack_latency}"
            )

        # No event-count or wakeup-count target exists here. Candidate
        # lifecycle is bounded only by its frozen 5-second terminal clock.
        while int(bt.current_timestamp) < CANCEL_REQUEST_LOCAL_NS:
            timeout = (
                CANCEL_REQUEST_LOCAL_NS
                - int(bt.current_timestamp)
            )

            wait_rc = int(
                bt.wait_next_feed(True, timeout)
            )

            if wait_rc == 1:
                break

            if wait_rc not in (0, 2, 3):
                raise CandidateGridRealEngineError(
                    f"wait_rc:{wait_rc}"
                )

            if wait_rc == 3:
                order = bt.orders(0).get(order_id)

                if order is None:
                    raise CandidateGridRealEngineError(
                        "order_missing_on_response"
                    )

                fill = r11._capture_fill_response(
                    bt,
                    order,
                )

                if fill is not None:
                    fills.append(fill)

                if int(order.status) == p1.HFT_FILLED:
                    break

            if wait_rc == 0:
                break

        order = bt.orders(0).get(order_id)

        if order is None:
            raise CandidateGridRealEngineError(
                "order_missing_preterminal"
            )

        if int(order.status) in (
            p1.HFT_NEW,
            p1.HFT_PARTIALLY_FILLED,
        ):
            r11._advance_to(
                bt,
                CANCEL_REQUEST_LOCAL_NS,
            )

            cancel_request_local_ns = int(
                bt.current_timestamp
            )

            if (
                cancel_request_local_ns
                != CANCEL_REQUEST_LOCAL_NS
            ):
                raise CandidateGridRealEngineError(
                    "cancel_request_timestamp"
                )

            cancel_rc = int(
                bt.cancel(
                    0,
                    order_id,
                    True,
                )
            )

            if cancel_rc != 0:
                raise CandidateGridRealEngineError(
                    f"cancel_rc:{cancel_rc}"
                )

            canceled = True
            order = bt.orders(0).get(order_id)

            if (
                order is None
                or int(order.status) != p1.HFT_CANCELED
            ):
                raise CandidateGridRealEngineError(
                    "cancel_not_terminal"
                )

            if (
                int(bt.current_timestamp)
                != CANDIDATE_TERMINAL_BOUNDARY_NS
            ):
                raise CandidateGridRealEngineError(
                    "cancel_terminal_boundary"
                )

            cancel_raw = bt.order_latency(0)

            if cancel_raw is None:
                raise CandidateGridRealEngineError(
                    "cancel_latency_missing"
                )

            cancel_latency = tuple(
                map(int, cancel_raw)
            )

            expected_cancel = (
                DECISION_LOCAL_NS,
                CANCEL_REQUEST_LOCAL_NS
                + p0.ENTRY_LATENCY_NS,
                CANDIDATE_TERMINAL_BOUNDARY_NS,
            )

            if cancel_latency != expected_cancel:
                raise CandidateGridRealEngineError(
                    f"cancel_latency:{cancel_latency}"
                )

        final_status = int(order.status)
        final_local_ns = int(bt.current_timestamp)

    finally:
        close_rc = int(bt.close())

        if close_rc != 0:
            raise CandidateGridRealEngineError(
                f"bt_close_rc:{close_rc}"
            )

    if ack_latency is None or placement is None:
        raise CandidateGridRealEngineError(
            "case_not_initialized"
        )

    labels = r8b.build_label_bundle(
        candidate=candidate,
        fills=tuple(fills),
        midpoints=midpoints,
        source_exchange_observed_through_ns=observed_through,
        placement_outcome=placement,
    )

    return CandidateGridResult(
        side=side,
        distance_ticks=int(distance_ticks),
        with_fill=bool(with_fill),
        candidate=candidate,
        feature_vector=features,
        placement_outcome=placement,
        fills=tuple(fills),
        labels=labels,
        final_status=final_status,
        final_local_ns=final_local_ns,
        canceled_at_boundary=canceled,
        ack_latency_triplet=ack_latency,
        cancel_latency_triplet=cancel_latency,
        source_exchange_observed_through_ns=observed_through,
    )


def validate_r14_contract() -> None:
    r5.validate_r5_contract()
    r11.validate_r11_contract()
    r12.validate_r12_contract()
    r13a.validate_r13a_contract()

    if PARENT_R13A_HEAD != (
        "37b45cdfcd36e40149b549c0d611c514a3d91f51"
    ):
        raise CandidateGridRealEngineError("parent")

    expected_grid = tuple(
        (side, int(distance))
        for side in ("BID", "ASK")
        for distance in (0, 1, 2, 4)
    )

    if CANDIDATE_GRID != expected_grid:
        raise CandidateGridRealEngineError(
            "candidate_grid"
        )

    if CANDIDATE_GRID_CASE_COUNT != 8:
        raise CandidateGridRealEngineError(
            "grid_case_count"
        )

    if PHASE_COUNT != 5:
        raise CandidateGridRealEngineError(
            "phase_count"
        )

    if CANONICAL_LANES_PER_DAY != 40:
        raise CandidateGridRealEngineError(
            "lanes_per_day"
        )

    if r12.LANES_PER_DAY != 40:
        raise CandidateGridRealEngineError(
            "r12_lanes_per_day"
        )

    required = (
        SYNTHETIC_REAL_ENGINE_ONLY,
        CANDIDATE_GRID_REAL_ENGINE_PREEXECUTION_FROZEN,
        R11_EXACT_ENGINE_LIFECYCLE_BOUND,
        R12_40_LANE_ORCHESTRATION_BOUND,
        R13A_BOUNDED_DUAL_STREAM_BOUND,
        NO_FIXED_EVENT_TARGET,
        NO_FIXED_WAKEUP_TARGET,
        NATURAL_END_OF_SOURCE_RULE_BOUND,
        TOTAL_RSS_NOT_BOUNDEDNESS_GATE,
        PREEXECUTION_ONLY,
        r11.CANCEL_LATENCY_FIRST_FIELD_IS_ORIGINAL_ORDER_LOCAL_TIMESTAMP,
        r13a.NATURAL_END_OF_SOURCE_IS_VALID_TERMINAL,
        r13a.FINAL_TIMESTAMP_GROUP_FLUSH_REQUIRED,
        r13a.FIXED_EVENT_TARGET is None,
        r13a.FIXED_WAKEUP_TARGET is None,
        r13a.TOTAL_RSS_ABORT_THRESHOLD_BYTES is None,
        not r13a.TOTAL_RSS_IS_BOUNDEDNESS_GATE,
    )

    if not all(required):
        raise CandidateGridRealEngineError(
            "required_guard"
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
        raise CandidateGridRealEngineError(
            "execution_surface_open"
        )


__all__ = [
    "CANDIDATE_GRID",
    "CandidateGridResult",
    "make_grid_fixture",
    "run_grid_case",
    "validate_r14_contract",
]

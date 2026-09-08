from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Iterator, Sequence

from multimarket import (
    dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0,
)
from multimarket import (
    dev045_d6r26a_p1_synthetic_candidate_labeler as p1,
)
from multimarket import (
    dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1,
)
from multimarket import (
    dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4,
)
from multimarket import (
    dev045_d6r26a_p2_r8a_real_hooks_writer_preexecution as r8a,
)
from multimarket import (
    dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b,
)
from multimarket import (
    dev045_d6r26a_p2_r11_synthetic_real_engine_lane_lifecycle as r11,
)
from multimarket import (
    dev045_d6r26a_p2_r14_synthetic_candidate_grid_real_engine_preexecution as r14,
)
from multimarket import (
    dev045_d6r26a_p2_r15_sequential_lane_real_engine_preexecution as r15,
)
from multimarket import (
    dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18,
)
from multimarket import (
    dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19,
)
from multimarket import (
    dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R21"
DESIGN_VERSION = "generic-lane-executor-preexecution-v1"
PARENT_R20_HEAD = "eded22d1df87c3f5c3ef8b31c769052b61b377c6"

GENERIC_LANE_EXECUTOR_FROZEN = True

R20_SHARED_DAY_CONTEXT_BOUND = True
R19_ELIGIBLE_LANE_SCHEDULE_BOUND = True
R15_SEQUENTIAL_SAME_ENGINE_BOUND = True
R11_CANCEL_LATENCY_FIX_BOUND = True
R18_CANONICAL_MATERIALIZER_BOUND = True
R8A_LANE_ENGINE_HANDLE_BOUND = True

FRESH_ENGINE_PER_LANE_REQUIRED = True
ONE_ENGINE_FOR_ALL_CANDIDATES_IN_LANE = True
NO_OVERLAPPING_CANDIDATES = True

GTX_LIMIT_BLOCKING_SUBMIT = True

# Do not trust cumulative-vs-delta interpretation of a wrapper field.
# Each fill quantity is reconstructed from leaves_qty change.
FILL_QTY_FROM_REMAINING_LEAVES_DELTA = True
DIRECT_EXEC_QTY_ACCUMULATION_FORBIDDEN = True

MARKOUTS_USE_R20_FILE_BACKED_INDEX = True
FULL_MIDPOINT_HISTORY_MATERIALIZATION_FORBIDDEN = True
PER_CANDIDATE_RAW_MIDPOINT_SCAN_FORBIDDEN = True
PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN = True

NATURAL_EOF_BEFORE_CANDIDATE_TERMINAL_IS_VALID = True
FIXED_EVENT_TARGET = None
FIXED_WAKEUP_TARGET = None

P2_ATTEMPT_CONSUMED = False

PREEXECUTION_ONLY = True
SYNTHETIC_REAL_ENGINE_PROBES_AUTHORIZED = True
SYNTHETIC_TEMP_ARTIFACT_WRITE_AUTHORIZED = True

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

ORDER_ID_BASE = 72_100_000


class GenericLaneExecutorError(RuntimeError):
    pass


@dataclass(frozen=True)
class GenericLaneExecutionSummary:
    artifact: r4.LaneArtifact
    candidate_count: int
    accepted_count: int
    rejected_at_arrival_count: int
    censored_before_placement_count: int
    fill_event_count: int
    filled_candidate_count: int
    canceled_candidate_count: int
    eof_censored_candidate_count: int
    first_decision_local_ns: int
    last_decision_local_ns: int


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
                int(order_id),
                float(candidate.price),
                float(candidate.qty),
                h.GTX,
                h.LIMIT,
                True,
            )
        )

    return int(
        bt.submit_sell_order(
            0,
            int(order_id),
            float(candidate.price),
            float(candidate.qty),
            h.GTX,
            h.LIMIT,
            True,
        )
    )


def _advance_to(
    bt,
    target_local_ns: int,
) -> None:
    target = int(target_local_ns)
    now = int(bt.current_timestamp)

    if now > target:
        raise GenericLaneExecutorError(
            f"advance_past_target:{now}:{target}"
        )

    if now == target:
        return

    rc = int(
        bt.elapse(
            target - now
        )
    )

    if rc != 0:
        raise GenericLaneExecutorError(
            f"elapse_rc:{rc}:{target}"
        )

    if int(bt.current_timestamp) != target:
        raise GenericLaneExecutorError(
            f"elapse_timestamp:"
            f"{bt.current_timestamp}:{target}"
        )


def _initialize_fresh_engine(
    *,
    bt,
    first_decision_local_ns: int,
) -> None:
    first_decision = int(
        first_decision_local_ns
    )

    if first_decision <= 0:
        raise GenericLaneExecutorError(
            "first_decision"
        )

    rc = int(
        bt.wait_next_feed(
            False,
            first_decision,
        )
    )

    if rc != 2:
        raise GenericLaneExecutorError(
            f"initial_feed_rc:{rc}"
        )

    now = int(
        bt.current_timestamp
    )

    if now > first_decision:
        raise GenericLaneExecutorError(
            f"first_feed_after_decision:"
            f"{now}:{first_decision}"
        )


def _candidate_from_cache(
    *,
    context: r20.DayContextBuildResult,
    lane: r1.LaneSpec,
    decision_local_ns: int,
) -> p1.CandidateSpec:
    cache = context.feature_cache
    decision = int(
        decision_local_ns
    )

    import numpy as np

    index = int(
        np.searchsorted(
            cache.decision_local_ns,
            decision,
            side="left",
        )
    )

    if (
        index >= cache.decision_count
        or int(
            cache.decision_local_ns[
                index
            ]
        )
        != decision
    ):
        raise GenericLaneExecutorError(
            f"cache_decision_missing:{decision}"
        )

    candidate = p1.CandidateSpec(
        side=lane.side,
        distance_ticks=int(
            lane.distance_ticks
        ),
        decision_local_ns=decision,
        best_bid_tick=int(
            cache.best_bid_tick[
                index
            ]
        ),
        best_ask_tick=int(
            cache.best_ask_tick[
                index
            ]
        ),
    )

    # This also proves exact side/distance feature availability.
    r18.lookup_feature_vector(
        cache=cache,
        candidate=candidate,
    )

    return candidate


def _markout_label_from_index(
    *,
    candidate: p1.CandidateSpec,
    fills: Sequence[p1.FillObservation],
    index: r20.MidpointIndexHandle,
    horizon_ns: int,
) -> p1.MarkoutLabel:
    horizon = int(
        horizon_ns
    )

    if horizon not in p0.MARKOUT_HORIZONS_NS:
        raise GenericLaneExecutorError(
            "markout_horizon"
        )

    ordered = tuple(
        sorted(
            fills,
            key=lambda x: (
                int(
                    x.exchange_execution_ns
                ),
                int(
                    x.local_response_ns
                ),
            ),
        )
    )

    total_fill_qty = sum(
        float(x.qty)
        for x in ordered
    )

    if (
        total_fill_qty
        > float(candidate.qty)
        + 1e-12
    ):
        raise GenericLaneExecutorError(
            "fill_qty_exceeds_candidate"
        )

    cutoff = (
        int(candidate.decision_local_ns)
        + int(
            p1.MARKOUT_FILL_INCLUSION_HORIZON_NS
        )
    )

    included = tuple(
        fill
        for fill in ordered
        if int(
            fill.exchange_execution_ns
        )
        <= cutoff
    )

    if not included:
        return p1.MarkoutLabel(
            horizon_ns=horizon,
            status=(
                p1.MARKOUT_NOT_APPLICABLE_NO_FILL
            ),
            value_bps=None,
            included_fill_count=0,
            included_fill_qty=0.0,
        )

    weighted = 0.0
    qty_total = 0.0

    for fill in included:
        target = (
            int(
                fill.exchange_execution_ns
            )
            + horizon
        )

        mid = r20.midpoint_asof(
            index=index,
            target_exchange_ns=target,
        )

        if mid is None:
            return p1.MarkoutLabel(
                horizon_ns=horizon,
                status=p1.MARKOUT_CENSORED,
                value_bps=None,
                included_fill_count=(
                    len(included)
                ),
                included_fill_qty=sum(
                    float(x.qty)
                    for x in included
                ),
            )

        value = p1.fill_markout_bps(
            side=candidate.side,
            fill_price=float(
                fill.price
            ),
            future_mid=float(mid),
        )

        weighted += (
            float(fill.qty)
            * float(value)
        )

        qty_total += float(
            fill.qty
        )

    if qty_total <= 0.0:
        raise GenericLaneExecutorError(
            "markout_zero_qty"
        )

    return p1.MarkoutLabel(
        horizon_ns=horizon,
        status=p1.MARKOUT_OBSERVED,
        value_bps=(
            weighted
            / qty_total
        ),
        included_fill_count=(
            len(included)
        ),
        included_fill_qty=qty_total,
    )


def build_label_bundle_from_index(
    *,
    candidate: p1.CandidateSpec,
    fills: Sequence[p1.FillObservation],
    index: r20.MidpointIndexHandle,
    placement_outcome: str,
) -> r8b.LabelBundle:
    if index.closed:
        raise GenericLaneExecutorError(
            "midpoint_index_closed"
        )

    observed_through = int(
        index.source_exchange_observed_through_ns
    )

    fill_labels = tuple(
        p1.fill_horizon_label(
            candidate=candidate,
            fills=fills,
            horizon_ns=int(
                horizon
            ),
            source_exchange_observed_through_ns=(
                observed_through
            ),
            placement_outcome=(
                placement_outcome
            ),
        )
        for horizon in p0.FILL_HORIZONS_NS
    )

    markout_labels = tuple(
        _markout_label_from_index(
            candidate=candidate,
            fills=fills,
            index=index,
            horizon_ns=int(
                horizon
            ),
        )
        for horizon in p0.MARKOUT_HORIZONS_NS
    )

    return r8b.LabelBundle(
        fill_labels=fill_labels,
        markout_labels=markout_labels,
    )


def _capture_fill_from_leaves_delta(
    *,
    bt,
    order,
    previous_remaining_qty: float,
) -> tuple[
    p1.FillObservation | None,
    float,
]:
    status = int(
        order.status
    )

    previous = float(
        previous_remaining_qty
    )

    leaves = float(
        order.leaves_qty
    )

    tolerance = 1e-12

    if leaves < -tolerance:
        raise GenericLaneExecutorError(
            "negative_leaves_qty"
        )

    if leaves > previous + tolerance:
        raise GenericLaneExecutorError(
            f"leaves_increased:"
            f"{previous}:{leaves}"
        )

    if status not in (
        p1.HFT_PARTIALLY_FILLED,
        p1.HFT_FILLED,
    ):
        return (
            None,
            max(0.0, leaves),
        )

    delta = (
        previous
        - leaves
    )

    if delta <= tolerance:
        raise GenericLaneExecutorError(
            f"nonpositive_fill_delta:"
            f"{previous}:{leaves}"
        )

    if delta > previous + tolerance:
        raise GenericLaneExecutorError(
            "fill_delta_exceeds_remaining"
        )

    fill = p1.FillObservation(
        exchange_execution_ns=int(
            order.exch_timestamp
        ),
        local_response_ns=int(
            bt.current_timestamp
        ),
        qty=float(delta),
        price=(
            float(
                order.exec_price_tick
            )
            * float(
                p0.TICK_SIZE
            )
        ),
    )

    return (
        fill,
        max(0.0, leaves),
    )


def _execute_candidate(
    *,
    engine: r8a.LaneEngineHandle,
    candidate: p1.CandidateSpec,
    order_id: int,
    context: r20.DayContextBuildResult,
) -> tuple[
    r18.CandidateExecutionRecord,
    int,
    bool,
    bool,
]:
    h = (
        engine.hftbacktest_module
    )
    bt = engine.backtest

    decision = int(
        candidate.decision_local_ns
    )

    _advance_to(
        bt,
        decision,
    )

    depth = bt.depth(0)

    if (
        int(
            depth.best_bid_tick
        )
        != int(
            candidate.best_bid_tick
        )
        or int(
            depth.best_ask_tick
        )
        != int(
            candidate.best_ask_tick
        )
    ):
        raise GenericLaneExecutorError(
            f"engine_cache_bbo_mismatch:"
            f"{decision}"
        )

    submit_rc = _submit_candidate(
        h=h,
        bt=bt,
        candidate=candidate,
        order_id=order_id,
    )

    if submit_rc != 0:
        raise GenericLaneExecutorError(
            f"submit_rc:"
            f"{decision}:{submit_rc}"
        )

    order = (
        bt.orders(0).get(
            order_id
        )
    )

    if order is None:
        raise GenericLaneExecutorError(
            f"order_missing_after_submit:"
            f"{decision}"
        )

    placement = (
        p1.classify_gtx_placement_status(
            int(order.status)
        )
    )

    if placement not in p0.PLACEMENT_OUTCOMES:
        raise GenericLaneExecutorError(
            f"placement_outcome:"
            f"{placement}"
        )

    # A successful blocking placement response should have exact frozen
    # 250ms entry + 250ms response timing unless placement is still censored.
    latency_raw = (
        bt.order_latency(0)
    )

    if (
        placement
        != p1.CENSORED_BEFORE_PLACEMENT_OUTCOME
    ):
        if latency_raw is None:
            raise GenericLaneExecutorError(
                "placement_latency_missing"
            )

        latency = tuple(
            map(
                int,
                latency_raw,
            )
        )

        expected = (
            decision,
            decision
            + p0.ENTRY_LATENCY_NS,
            decision
            + p0.ENTRY_LATENCY_NS
            + p0.RESPONSE_LATENCY_NS,
        )

        if latency != expected:
            raise GenericLaneExecutorError(
                f"placement_latency:"
                f"{decision}:{latency}"
            )

    fills: list[
        p1.FillObservation
    ] = []

    remaining_qty = float(
        candidate.qty
    )

    canceled = False

    if placement == p1.POST_ONLY_ACCEPTED:
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

        while int(
            bt.current_timestamp
        ) < cancel_request:
            timeout = (
                cancel_request
                - int(
                    bt.current_timestamp
                )
            )

            wait_rc = int(
                bt.wait_next_feed(
                    True,
                    timeout,
                )
            )

            if wait_rc == 1:
                break

            if wait_rc not in (
                0,
                2,
                3,
            ):
                raise GenericLaneExecutorError(
                    f"wait_rc:"
                    f"{decision}:{wait_rc}"
                )

            if wait_rc == 3:
                order = (
                    bt.orders(0).get(
                        order_id
                    )
                )

                if order is None:
                    raise GenericLaneExecutorError(
                        "order_missing_on_response"
                    )

                (
                    fill,
                    remaining_qty,
                ) = (
                    _capture_fill_from_leaves_delta(
                        bt=bt,
                        order=order,
                        previous_remaining_qty=(
                            remaining_qty
                        ),
                    )
                )

                if fill is not None:
                    fills.append(
                        fill
                    )

                if (
                    int(order.status)
                    == p1.HFT_FILLED
                ):
                    break

            if wait_rc == 0:
                # Natural source EOF is not a candidate failure.
                break

        order = (
            bt.orders(0).get(
                order_id
            )
        )

        if order is None:
            raise GenericLaneExecutorError(
                "order_missing_preterminal"
            )

        status = int(
            order.status
        )

        if status in (
            p1.HFT_NEW,
            p1.HFT_PARTIALLY_FILLED,
        ):
            _advance_to(
                bt,
                cancel_request,
            )

            if int(
                bt.current_timestamp
            ) != cancel_request:
                raise GenericLaneExecutorError(
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
                raise GenericLaneExecutorError(
                    f"cancel_rc:"
                    f"{decision}:{cancel_rc}"
                )

            canceled = True

            order = (
                bt.orders(0).get(
                    order_id
                )
            )

            if (
                order is None
                or int(
                    order.status
                )
                != p1.HFT_CANCELED
            ):
                raise GenericLaneExecutorError(
                    "cancel_not_terminal"
                )

            if int(
                bt.current_timestamp
            ) != terminal:
                raise GenericLaneExecutorError(
                    f"cancel_terminal_clock:"
                    f"{decision}:"
                    f"{bt.current_timestamp}:"
                    f"{terminal}"
                )

            cancel_raw = (
                bt.order_latency(0)
            )

            if cancel_raw is None:
                raise GenericLaneExecutorError(
                    "cancel_latency_missing"
                )

            cancel_latency = tuple(
                map(
                    int,
                    cancel_raw,
                )
            )

            expected_cancel = (
                decision,
                cancel_request
                + p0.ENTRY_LATENCY_NS,
                terminal,
            )

            if (
                cancel_latency
                != expected_cancel
            ):
                raise GenericLaneExecutorError(
                    f"cancel_latency:"
                    f"{decision}:"
                    f"{cancel_latency}"
                )

        elif status == p1.HFT_FILLED:
            if (
                remaining_qty
                > 1e-12
            ):
                raise GenericLaneExecutorError(
                    f"filled_with_remaining:"
                    f"{remaining_qty}"
                )

        else:
            raise GenericLaneExecutorError(
                f"unexpected_terminal_status:"
                f"{decision}:{status}"
            )

    labels = (
        build_label_bundle_from_index(
            candidate=candidate,
            fills=tuple(fills),
            index=(
                context.midpoint_index
            ),
            placement_outcome=placement,
        )
    )

    eof_censored = any(
        item.state == p1.CENSORED
        for item in labels.fill_labels
    ) or any(
        item.status
        == p1.MARKOUT_CENSORED
        for item in labels.markout_labels
    )

    record = (
        r18.CandidateExecutionRecord(
            candidate=candidate,
            placement_outcome=placement,
            labels=labels,
        )
    )

    return (
        record,
        len(fills),
        canceled,
        bool(eof_censored),
    )


def execute_and_materialize_lane(
    *,
    engine: r8a.LaneEngineHandle,
    source: r1.FrozenSourceIdentity,
    lane: r1.LaneSpec,
    day_start_local_ns: int,
    context: r20.DayContextBuildResult,
    output_root: Path,
) -> GenericLaneExecutionSummary:
    if P2_ATTEMPT_CONSUMED:
        raise GenericLaneExecutorError(
            "attempt_consumed"
        )

    if context.midpoint_index.closed:
        raise GenericLaneExecutorError(
            "midpoint_index_closed"
        )

    decisions = (
        r19.lane_decisions_from_cache(
            cache=context.feature_cache,
            lane=lane,
            day_start_local_ns=int(
                day_start_local_ns
            ),
        )
    )

    if not decisions:
        raise GenericLaneExecutorError(
            f"lane_no_eligible_decisions:"
            f"{lane.lane_id}"
        )

    p1.assert_lane_isolation(
        decisions
    )

    _initialize_fresh_engine(
        bt=engine.backtest,
        first_decision_local_ns=(
            decisions[0]
        ),
    )

    accepted_count = 0
    rejected_count = 0
    censored_count = 0
    fill_event_count = 0
    filled_candidate_count = 0
    canceled_candidate_count = 0
    eof_censored_candidate_count = 0

    def records() -> Iterator[
        r18.CandidateExecutionRecord
    ]:
        nonlocal accepted_count
        nonlocal rejected_count
        nonlocal censored_count
        nonlocal fill_event_count
        nonlocal filled_candidate_count
        nonlocal canceled_candidate_count
        nonlocal eof_censored_candidate_count

        previous_decision: (
            int | None
        ) = None

        for index, decision in enumerate(
            decisions
        ):
            candidate = (
                _candidate_from_cache(
                    context=context,
                    lane=lane,
                    decision_local_ns=(
                        decision
                    ),
                )
            )

            if (
                previous_decision
                is not None
            ):
                if (
                    int(decision)
                    - previous_decision
                    < p0.MAX_CANDIDATE_LIFETIME_NS
                ):
                    raise GenericLaneExecutorError(
                        "lane_candidate_overlap"
                    )

            (
                record,
                fill_count,
                canceled,
                eof_censored,
            ) = _execute_candidate(
                engine=engine,
                candidate=candidate,
                order_id=(
                    ORDER_ID_BASE
                    + index
                ),
                context=context,
            )

            placement = (
                record.placement_outcome
            )

            if (
                placement
                == p1.POST_ONLY_ACCEPTED
            ):
                accepted_count += 1

            elif (
                placement
                == p1.POST_ONLY_REJECTED_AT_ARRIVAL
            ):
                rejected_count += 1

            elif (
                placement
                == p1.CENSORED_BEFORE_PLACEMENT_OUTCOME
            ):
                censored_count += 1

            else:
                raise GenericLaneExecutorError(
                    "placement_counter"
                )

            fill_event_count += (
                fill_count
            )

            if fill_count > 0:
                filled_candidate_count += 1

            if canceled:
                canceled_candidate_count += 1

            if eof_censored:
                eof_censored_candidate_count += 1

            yield record

            previous_decision = int(
                decision
            )

    artifact = (
        r18.materialize_lane_partition(
            source=source,
            lane=lane,
            day_start_local_ns=int(
                day_start_local_ns
            ),
            feed_bounds=context.bounds,
            feature_cache=(
                context.feature_cache
            ),
            records=records(),
            output_root=Path(
                output_root
            ),
        )
    )

    candidate_count = len(
        decisions
    )

    if (
        int(artifact.row_count)
        != candidate_count
    ):
        raise GenericLaneExecutorError(
            f"artifact_row_count:"
            f"{artifact.row_count}:"
            f"{candidate_count}"
        )

    if (
        accepted_count
        + rejected_count
        + censored_count
        != candidate_count
    ):
        raise GenericLaneExecutorError(
            "placement_count"
        )

    return GenericLaneExecutionSummary(
        artifact=artifact,
        candidate_count=(
            candidate_count
        ),
        accepted_count=(
            accepted_count
        ),
        rejected_at_arrival_count=(
            rejected_count
        ),
        censored_before_placement_count=(
            censored_count
        ),
        fill_event_count=(
            fill_event_count
        ),
        filled_candidate_count=(
            filled_candidate_count
        ),
        canceled_candidate_count=(
            canceled_candidate_count
        ),
        eof_censored_candidate_count=(
            eof_censored_candidate_count
        ),
        first_decision_local_ns=int(
            decisions[0]
        ),
        last_decision_local_ns=int(
            decisions[-1]
        ),
    )


def _synthetic_lane(
    *,
    side: str = "BID",
    distance_ticks: int = 0,
    phase: int = 1,
) -> r1.LaneSpec:
    matches = [
        lane
        for lane in (
            r1.build_materialization_plan()
        )
        if (
            lane.side == side
            and int(
                lane.distance_ticks
            )
            == int(
                distance_ticks
            )
            and int(
                lane.phase
            )
            == int(
                phase
            )
        )
    ]

    if not matches:
        raise GenericLaneExecutorError(
            "synthetic_lane_missing"
        )

    return matches[0]


def _synthetic_source(
    lane: r1.LaneSpec,
) -> r1.FrozenSourceIdentity:
    digest = hashlib.sha256(
        (
            "DEV045-D6R26A-P2-R21:"
            + lane.lane_id
        ).encode(
            "ascii"
        )
    ).hexdigest()

    return r1.FrozenSourceIdentity(
        day=lane.day,
        path=(
            "/synthetic/"
            "dev045_d6r26a_p2_r21.npy"
        ),
        bytes=1,
        sha256=digest,
    )


def run_synthetic_no_fill_lane(
    *,
    output_root: Path,
    scratch_root: Path,
) -> GenericLaneExecutionSummary:
    data = (
        r15.make_sequential_fixture()
    )

    context = (
        r20.build_once_day_context(
            data,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=(
                100_000_000_000
            ),
            scratch_root=Path(
                scratch_root
            ),
        )
    )

    h, bt = r11._new_backtest(
        data
    )

    engine = r8a.LaneEngineHandle(
        hftbacktest_module=h,
        backtest=bt,
    )

    lane = _synthetic_lane(
        side="BID",
        distance_ticks=0,
        phase=1,
    )

    source = (
        _synthetic_source(
            lane
        )
    )

    try:
        return execute_and_materialize_lane(
            engine=engine,
            source=source,
            lane=lane,
            day_start_local_ns=0,
            context=context,
            output_root=Path(
                output_root
            ),
        )

    finally:
        r8a.close_engine_impl(
            engine
        )

        r20.close_midpoint_index(
            context.midpoint_index
        )


def run_synthetic_fill_lane(
    *,
    output_root: Path,
    scratch_root: Path,
) -> GenericLaneExecutionSummary:
    data = r14.make_grid_fixture(
        side="BID",
        distance_ticks=0,
        with_fill=True,
    )

    context = (
        r20.build_once_day_context(
            data,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=(
                100_000_000_000
            ),
            scratch_root=Path(
                scratch_root
            ),
        )
    )

    h, bt = r11._new_backtest(
        data
    )

    engine = r8a.LaneEngineHandle(
        hftbacktest_module=h,
        backtest=bt,
    )

    lane = _synthetic_lane(
        side="BID",
        distance_ticks=0,
        phase=1,
    )

    source = (
        _synthetic_source(
            lane
        )
    )

    try:
        return execute_and_materialize_lane(
            engine=engine,
            source=source,
            lane=lane,
            day_start_local_ns=0,
            context=context,
            output_root=Path(
                output_root
            ),
        )

    finally:
        r8a.close_engine_impl(
            engine
        )

        r20.close_midpoint_index(
            context.midpoint_index
        )


def validate_r21_contract() -> None:
    r11.validate_r11_contract()
    r14.validate_r14_contract()
    r15.validate_r15_contract()
    r18.validate_r18_contract()
    r19.validate_r19_contract()
    r20.validate_r20_contract()

    if PARENT_R20_HEAD != (
        "eded22d1df87c3f5c3ef8b31c769052b61b377c6"
    ):
        raise GenericLaneExecutorError(
            "parent"
        )

    if ORDER_ID_BASE <= 0:
        raise GenericLaneExecutorError(
            "order_id_base"
        )

    required = (
        GENERIC_LANE_EXECUTOR_FROZEN,
        R20_SHARED_DAY_CONTEXT_BOUND,
        R19_ELIGIBLE_LANE_SCHEDULE_BOUND,
        R15_SEQUENTIAL_SAME_ENGINE_BOUND,
        R11_CANCEL_LATENCY_FIX_BOUND,
        R18_CANONICAL_MATERIALIZER_BOUND,
        R8A_LANE_ENGINE_HANDLE_BOUND,
        FRESH_ENGINE_PER_LANE_REQUIRED,
        ONE_ENGINE_FOR_ALL_CANDIDATES_IN_LANE,
        NO_OVERLAPPING_CANDIDATES,
        GTX_LIMIT_BLOCKING_SUBMIT,
        FILL_QTY_FROM_REMAINING_LEAVES_DELTA,
        not DIRECT_EXEC_QTY_ACCUMULATION_FORBIDDEN
        is False,
        MARKOUTS_USE_R20_FILE_BACKED_INDEX,
        FULL_MIDPOINT_HISTORY_MATERIALIZATION_FORBIDDEN,
        PER_CANDIDATE_RAW_MIDPOINT_SCAN_FORBIDDEN,
        PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN,
        NATURAL_EOF_BEFORE_CANDIDATE_TERMINAL_IS_VALID,
        P2_ATTEMPT_CONSUMED is False,
        PREEXECUTION_ONLY,
        SYNTHETIC_REAL_ENGINE_PROBES_AUTHORIZED,
        SYNTHETIC_TEMP_ARTIFACT_WRITE_AUTHORIZED,
        r11.CANCEL_LATENCY_FIRST_FIELD_IS_ORIGINAL_ORDER_LOCAL_TIMESTAMP,
        r20.COMBINED_RAW_EVENT_PASSES_PER_DAY == 1,
        r20.SECOND_RAW_PASS_FOR_MIDPOINTS_FORBIDDEN,
        r20.PER_LANE_RAW_MIDPOINT_RESCAN_FORBIDDEN,
        r19.PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN,
    )

    if not all(required):
        raise GenericLaneExecutorError(
            "required_guard"
        )

    if FIXED_EVENT_TARGET is not None:
        raise GenericLaneExecutorError(
            "fixed_event_target"
        )

    if FIXED_WAKEUP_TARGET is not None:
        raise GenericLaneExecutorError(
            "fixed_wakeup_target"
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
        raise GenericLaneExecutorError(
            "execution_surface_open"
        )


__all__ = [
    "GenericLaneExecutionSummary",
    "build_label_bundle_from_index",
    "execute_and_materialize_lane",
    "run_synthetic_fill_lane",
    "run_synthetic_no_fill_lane",
    "validate_r21_contract",
]

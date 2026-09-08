from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1
from multimarket import dev045_d6r26a_p2_r5_real_engine_binding_prehistorical as r5
from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b
from multimarket import dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9
from multimarket import dev045_d6r26a_p2_r10_bounded_feature_accumulator_freeze as r10
from multimarket import dev045_m4_adapter as m4

EXPERIMENT_ID = "DEV045-D6R26A-P2-R11"
DESIGN_VERSION = "synthetic-real-engine-candidate-lane-lifecycle-v1"
PARENT_R10_HEAD = "84eabe7dcc7e57da3be18b3cc21404f2d3899a53"

SYNTHETIC_REAL_ENGINE_ONLY = True
REAL_ENGINE_LANE_LIFECYCLE_FROZEN = True
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

DECISION_LOCAL_NS = 31_000_000_000
CANDIDATE_TERMINAL_BOUNDARY_NS = DECISION_LOCAL_NS + p0.MAX_CANDIDATE_LIFETIME_NS
CANCEL_REQUEST_LOCAL_NS = (
    CANDIDATE_TERMINAL_BOUNDARY_NS
    - p0.ENTRY_LATENCY_NS
    - p0.RESPONSE_LATENCY_NS
)
ORDER_ID = 71101


class RealEngineLaneLifecycleError(RuntimeError):
    pass


@dataclass(frozen=True)
class LaneLifecycleResult:
    candidate: p1.CandidateSpec
    feature_vector: r8b.FeatureVector
    placement_outcome: str
    fills: tuple[p1.FillObservation, ...]
    labels: r8b.LabelBundle
    final_status: int
    final_local_ns: int
    canceled_at_boundary: bool
    order_latency_triplet: tuple[int, int, int] | None
    source_exchange_observed_through_ns: int


def _imports():
    import hftbacktest as h
    return h


def _row(a, i, *, ev, exch_ns, local_ns, px, qty):
    a[i]["ev"] = int(ev)
    a[i]["exch_ts"] = int(exch_ns)
    a[i]["local_ts"] = int(local_ns)
    a[i]["px"] = float(px)
    a[i]["qty"] = float(qty)


def make_lifecycle_fixture(*, with_fill: bool) -> np.ndarray:
    h = _imports()
    rows: list[tuple[int, int, int, float, float]] = []
    snap_base = int(h.EXCH_EVENT | h.LOCAL_EVENT | h.DEPTH_SNAPSHOT_EVENT)
    exch0 = 900_000_000
    local0 = 1_000_000_000
    for level, qty in enumerate((5.0, 4.0, 3.0, 2.0, 1.0)):
        rows.append((snap_base | int(h.BUY_EVENT), exch0, local0, 100.0 - 0.1 * level, qty))
    for level, qty in enumerate((6.0, 5.0, 4.0, 3.0, 2.0)):
        rows.append((snap_base | int(h.SELL_EVENT), exch0, local0, 100.1 + 0.1 * level, qty))

    depth_ask = int(h.EXCH_EVENT | h.LOCAL_EVENT | h.DEPTH_EVENT | h.SELL_EVENT)
    for second in range(2, 32):
        local = second * 1_000_000_000
        rows.append((depth_ask, local - 10_000_000, local, 100.1, 6.0))

    if with_fill:
        sell_trade = int(h.EXCH_EVENT | h.LOCAL_EVENT | h.TRADE_EVENT | h.SELL_EVENT)
        rows.append((sell_trade, 31_600_000_000, 31_610_000_000, 100.0, 5.0))
        rows.append((sell_trade, 31_800_000_000, 31_810_000_000, 100.0, 0.001))

    for k, local in enumerate(range(32_500_000_000, 38_000_000_000, 500_000_000)):
        qty = 6.0 + (0.1 if k % 2 else 0.0)
        rows.append((depth_ask, local - 10_000_000, local, 100.1, qty))

    rows.sort(key=lambda x: (x[2], x[1]))
    a = np.zeros(len(rows), dtype=h.event_dtype)
    for i, (ev, exch, local, px, qty) in enumerate(rows):
        _row(a, i, ev=ev, exch_ns=exch, local_ns=local, px=px, qty=qty)
    m4.validate_events(a)
    return a


def _feature_vector_at_decision(
    data: np.ndarray,
    *,
    side: str,
    distance_ticks: int,
) -> tuple[p1.CandidateSpec, r8b.FeatureVector]:
    causal = data[data["local_ts"] <= DECISION_LOCAL_NS]
    decoded = r9.decode_local_history(causal)
    if not decoded.books:
        raise RealEngineLaneLifecycleError("feature_books_missing")
    current = decoded.books[-1]
    candidate = p1.CandidateSpec(
        side=side,
        distance_ticks=int(distance_ticks),
        decision_local_ns=DECISION_LOCAL_NS,
        best_bid_tick=int(current.best_bid.price_tick),
        best_ask_tick=int(current.best_ask.price_tick),
    )
    acc = r10.RollingFeatureAccumulator()
    stream = [(x.local_ns, 0, n, x) for n, x in enumerate(decoded.books)] + [
        (x.local_ns, 1, n, x) for n, x in enumerate(decoded.flows)
    ]
    for _, kind, _, item in sorted(stream, key=lambda x: (x[0], x[1], x[2])):
        if kind == 0:
            acc.ingest_book(item)
        else:
            acc.ingest_flow(item)
    return candidate, acc.compute(candidate=candidate)


def _new_backtest(data: np.ndarray):
    h = _imports()
    asset = m4.build_asset(
        data,
        queue_model="risk_adverse",
        entry_latency_ns=p0.ENTRY_LATENCY_NS,
        response_latency_ns=p0.RESPONSE_LATENCY_NS,
        maker_fee=0.0,
        taker_fee=0.0,
    )
    return h, h.HashMapMarketDepthBacktest([asset])


def _initialize_clock(bt) -> None:
    rc = int(bt.wait_next_feed(False, 2_000_000_000))
    if rc != 2:
        raise RealEngineLaneLifecycleError(f"initial_feed_rc:{rc}")
    if int(bt.current_timestamp) != 1_000_000_000:
        raise RealEngineLaneLifecycleError(f"initial_timestamp:{bt.current_timestamp}")


def _advance_to(bt, target_local_ns: int) -> None:
    target = int(target_local_ns)
    now = int(bt.current_timestamp)
    if now > target:
        raise RealEngineLaneLifecycleError(f"advance_past_target:{now}:{target}")
    if now == target:
        return
    rc = int(bt.elapse(target - now))
    if rc != 0:
        raise RealEngineLaneLifecycleError(f"elapse_rc:{rc}:{target}")
    if int(bt.current_timestamp) != target:
        raise RealEngineLaneLifecycleError(f"elapse_timestamp:{bt.current_timestamp}:{target}")


def _capture_fill_response(bt, order) -> p1.FillObservation | None:
    status = int(order.status)
    if status not in (p1.HFT_PARTIALLY_FILLED, p1.HFT_FILLED):
        return None
    qty = float(order.exec_qty)
    if qty <= 0.0:
        raise RealEngineLaneLifecycleError("nonpositive_fill_response")
    return p1.FillObservation(
        exchange_execution_ns=int(order.exch_timestamp),
        local_response_ns=int(bt.current_timestamp),
        qty=qty,
        price=float(order.exec_price_tick) * float(p0.TICK_SIZE),
    )


def run_synthetic_lane(*, with_fill: bool, distance_ticks: int = 0) -> LaneLifecycleResult:
    r5.verify_engine_identity()
    data = make_lifecycle_fixture(with_fill=with_fill)
    candidate, features = _feature_vector_at_decision(
        data,
        side="BID",
        distance_ticks=int(distance_ticks),
    )
    midpoints = r9.decode_exchange_midpoints(data)
    observed_through = int(np.max(data["exch_ts"]))
    h, bt = _new_backtest(data)
    fills: list[p1.FillObservation] = []
    canceled = False
    placement: str | None = None
    latency: tuple[int, int, int] | None = None
    try:
        _initialize_clock(bt)
        _advance_to(bt, DECISION_LOCAL_NS)
        depth = bt.depth(0)
        if int(depth.best_bid_tick) != candidate.best_bid_tick or int(depth.best_ask_tick) != candidate.best_ask_tick:
            raise RealEngineLaneLifecycleError("engine_feature_bbo_mismatch")
        rc = int(
            bt.submit_buy_order(
                0,
                ORDER_ID,
                candidate.price,
                float(candidate.qty),
                h.GTX,
                h.LIMIT,
                True,
            )
        )
        if rc != 0:
            raise RealEngineLaneLifecycleError(f"submit_rc:{rc}")
        order = bt.orders(0).get(ORDER_ID)
        if order is None:
            raise RealEngineLaneLifecycleError("order_missing_after_ack")
        placement = p1.classify_gtx_placement_status(int(order.status))
        if placement != p1.POST_ONLY_ACCEPTED:
            raise RealEngineLaneLifecycleError(f"placement:{placement}")
        latency_raw = bt.order_latency(0)
        if latency_raw is None:
            raise RealEngineLaneLifecycleError("ack_latency_missing")
        latency = tuple(map(int, latency_raw))
        if latency != (
            DECISION_LOCAL_NS,
            DECISION_LOCAL_NS + p0.ENTRY_LATENCY_NS,
            DECISION_LOCAL_NS + p0.ENTRY_LATENCY_NS + p0.RESPONSE_LATENCY_NS,
        ):
            raise RealEngineLaneLifecycleError(f"ack_latency:{latency}")

        while int(bt.current_timestamp) < CANCEL_REQUEST_LOCAL_NS:
            timeout = CANCEL_REQUEST_LOCAL_NS - int(bt.current_timestamp)
            wait_rc = int(bt.wait_next_feed(True, timeout))
            if wait_rc == 1:
                break
            if wait_rc not in (0, 2, 3):
                raise RealEngineLaneLifecycleError(f"wait_rc:{wait_rc}")
            if wait_rc == 3:
                order = bt.orders(0).get(ORDER_ID)
                if order is None:
                    raise RealEngineLaneLifecycleError("order_missing_on_response")
                fill = _capture_fill_response(bt, order)
                if fill is not None:
                    fills.append(fill)
                if int(order.status) == p1.HFT_FILLED:
                    break
            if wait_rc == 0:
                break

        order = bt.orders(0).get(ORDER_ID)
        if order is None:
            raise RealEngineLaneLifecycleError("order_missing_preterminal")
        if int(order.status) in (p1.HFT_NEW, p1.HFT_PARTIALLY_FILLED):
            _advance_to(bt, CANCEL_REQUEST_LOCAL_NS)
            cancel_rc = int(bt.cancel(0, ORDER_ID, True))
            if cancel_rc != 0:
                raise RealEngineLaneLifecycleError(f"cancel_rc:{cancel_rc}")
            canceled = True
            order = bt.orders(0).get(ORDER_ID)
            if order is None or int(order.status) != p1.HFT_CANCELED:
                raise RealEngineLaneLifecycleError("cancel_not_terminal")
            if int(bt.current_timestamp) != CANDIDATE_TERMINAL_BOUNDARY_NS:
                raise RealEngineLaneLifecycleError(
                    f"cancel_boundary:{bt.current_timestamp}:{CANDIDATE_TERMINAL_BOUNDARY_NS}"
                )
            cancel_latency_raw = bt.order_latency(0)
            if cancel_latency_raw is None:
                raise RealEngineLaneLifecycleError("cancel_latency_missing")
            cancel_latency = tuple(map(int, cancel_latency_raw))
            if cancel_latency != (
                CANCEL_REQUEST_LOCAL_NS,
                CANCEL_REQUEST_LOCAL_NS + p0.ENTRY_LATENCY_NS,
                CANDIDATE_TERMINAL_BOUNDARY_NS,
            ):
                raise RealEngineLaneLifecycleError(f"cancel_latency:{cancel_latency}")
        final_status = int(order.status)
        final_local_ns = int(bt.current_timestamp)
    finally:
        close_rc = int(bt.close())
        if close_rc != 0:
            raise RealEngineLaneLifecycleError(f"bt_close_rc:{close_rc}")

    labels = r8b.build_label_bundle(
        candidate=candidate,
        fills=tuple(fills),
        midpoints=midpoints,
        source_exchange_observed_through_ns=observed_through,
        placement_outcome=placement,
    )
    return LaneLifecycleResult(
        candidate=candidate,
        feature_vector=features,
        placement_outcome=placement,
        fills=tuple(fills),
        labels=labels,
        final_status=final_status,
        final_local_ns=final_local_ns,
        canceled_at_boundary=canceled,
        order_latency_triplet=latency,
        source_exchange_observed_through_ns=observed_through,
    )


def validate_r11_contract() -> None:
    r10.validate_r10_contract()
    r9.validate_r9_contract()
    r8b.validate_r8b_contract()
    r5.validate_r5_contract()
    if PARENT_R10_HEAD != "84eabe7dcc7e57da3be18b3cc21404f2d3899a53":
        raise RealEngineLaneLifecycleError("parent")
    if DECISION_LOCAL_NS != 31_000_000_000:
        raise RealEngineLaneLifecycleError("decision")
    if CANCEL_REQUEST_LOCAL_NS != 35_500_000_000:
        raise RealEngineLaneLifecycleError("cancel_request")
    if CANDIDATE_TERMINAL_BOUNDARY_NS != 36_000_000_000:
        raise RealEngineLaneLifecycleError("terminal_boundary")
    if not SYNTHETIC_REAL_ENGINE_ONLY or not REAL_ENGINE_LANE_LIFECYCLE_FROZEN:
        raise RealEngineLaneLifecycleError("scope")
    forbidden = (
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
        raise RealEngineLaneLifecycleError("execution_surface_open")


__all__ = [
    "LaneLifecycleResult",
    "make_lifecycle_fixture",
    "run_synthetic_lane",
    "validate_r11_contract",
]

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Mapping, Sequence

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1
from multimarket import dev045_d6r26a_p2_jan_jul_consumed_development_label_design as p2
from multimarket import dev045_d6r26a_p2_r8a_real_hooks_writer_preexecution as r8a


EXPERIMENT_ID = "DEV045-D6R26A-P2-R8B"
DESIGN_VERSION = "feature-label-executor-freeze-v1"
PARENT_R8A_HEAD = "abcfd786e5c8345b9857310f98e5e7e856d75815"
DATA_ROLE = "CONSUMED_DEVELOPMENT"

FEATURE_LABEL_EXECUTOR_FROZEN = True
PURE_SYNTHETIC_CONTRACT_ONLY = True
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
NETWORK_ACQUISITION_AUTHORIZED = False

FEATURE_WARMUP_NS = p2.FEATURE_WARMUP_NS
FEATURE_SUPPORT_REQUIRED_DEPTH_LEVELS = 5
WINDOW_LEFT_OPEN_RIGHT_CLOSED = True
BOOK_SAME_LOCAL_TS_POLICY = "FINAL_POST_MARKET_STATE_ONE_OBSERVATION_PER_LOCAL_NS"
FEATURE_TIMESTAMP_POLICY = "DECISION_LOCAL_NS_AFTER_ALL_LOCAL_MARKET_EVENTS_AT_THAT_TIMESTAMP"
BBO_OFI_SIGN_CONVENTION = "POSITIVE_BUY_PRESSURE"
TRADE_IMBALANCE_SIGN_CONVENTION = "POSITIVE_AGGRESSIVE_BUY"
ADD_IMBALANCE_SIGN_CONVENTION = "POSITIVE_BID_ADD"
CANCEL_IMBALANCE_SIGN_CONVENTION = "POSITIVE_ASK_CANCEL"
REALIZED_VOL_UNIT = "BPS_UNANNUALIZED_SQRT_SUM_SQUARED_LOG_MID_RETURNS"
MICROPRICE_EQUALS_VAMP_BBO_BY_DEFINITION = True
QUEUE_AHEAD_EQUALS_DISPLAYED_QTY_BY_FROZEN_ESTIMATE = True

FEATURE_NAMES = tuple(
    feature
    for family in p0.LOCAL_FEATURE_FAMILIES.values()
    for feature in family
)

FEATURE_DEFINITIONS: Mapping[str, str] = {
    "spread_ticks": "best_ask_tick - best_bid_tick",
    "microprice_minus_mid_bps": "10000 * (microprice_bbo - mid_bbo) / mid_bbo; microprice_bbo=(best_bid_px*best_ask_qty + best_ask_px*best_bid_qty)/(best_bid_qty+best_ask_qty)",
    "vamp_bbo_minus_mid_bps": "identical_to_microprice_minus_mid_bps_by_frozen_standard_vamp_bbo_definition",
    "vamp_l5_minus_mid_bps": "10000 * (sum_i1..5(bid_px_i*ask_qty_i + ask_px_i*bid_qty_i)/sum_i1..5(bid_qty_i+ask_qty_i) - mid_bbo) / mid_bbo",
    "l1_obi": "(best_bid_qty-best_ask_qty)/(best_bid_qty+best_ask_qty)",
    "l5_obi": "(sum_bid_qty_l1_l5-sum_ask_qty_l1_l5)/(sum_bid_qty_l1_l5+sum_ask_qty_l1_l5)",
    "bbo_ofi_1s": "sum_cont_bbo_ofi_transitions_over_(t-1s,t]_with_anchor_asof_t-1s_in_base_asset_qty",
    "bbo_ofi_5s": "sum_cont_bbo_ofi_transitions_over_(t-5s,t]_with_anchor_asof_t-5s_in_base_asset_qty",
    "trade_imbalance_1s": "(aggressive_buy_qty-aggressive_sell_qty)/(aggressive_buy_qty+aggressive_sell_qty)_over_(t-1s,t];zero_if_no_trades",
    "trade_imbalance_5s": "(aggressive_buy_qty-aggressive_sell_qty)/(aggressive_buy_qty+aggressive_sell_qty)_over_(t-5s,t];zero_if_no_trades",
    "add_imbalance_1s": "(bid_add_qty-ask_add_qty)/(bid_add_qty+ask_add_qty)_over_(t-1s,t];zero_if_no_adds",
    "cancel_imbalance_1s": "(ask_cancel_qty-bid_cancel_qty)/(ask_cancel_qty+bid_cancel_qty)_over_(t-1s,t];zero_if_no_cancels",
    "ofi_acceleration_1s_vs_5s": "bbo_ofi_1s/1.0 - bbo_ofi_5s/5.0_in_base_asset_qty_per_second",
    "same_side_depth_change_250ms": "current_best_depth_qty_on_candidate_side - best_depth_qty_on_candidate_side_asof_t-250ms",
    "opposite_side_depth_change_250ms": "current_best_depth_qty_opposite_candidate_side - best_depth_qty_opposite_side_asof_t-250ms",
    "spread_change_1s": "current_spread_ticks - spread_ticks_asof_t-1s",
    "realized_vol_1s": "10000*sqrt(sum(log(mid_j/mid_j-1)^2))_using_anchor_asof_t-1s_plus_all_coalesced_bbo_states_in_(t-1s,t]",
    "realized_vol_5s": "10000*sqrt(sum(log(mid_j/mid_j-1)^2))_using_anchor_asof_t-5s_plus_all_coalesced_bbo_states_in_(t-5s,t]",
    "realized_vol_30s": "10000*sqrt(sum(log(mid_j/mid_j-1)^2))_using_anchor_asof_t-30s_plus_all_coalesced_bbo_states_in_(t-30s,t]",
    "candidate_side_sign": "+1_BID_-1_ASK",
    "candidate_distance_ticks": "frozen_candidate_distance_ticks",
    "displayed_qty_at_candidate_price": "visible_decision_book_qty_at_exact_candidate_price_on_candidate_side;zero_if_absent",
    "estimated_queue_ahead_qty_from_decision_book": "equal_to_displayed_qty_at_candidate_price_under_risk_adverse_join-behind-visible-queue_estimate",
    "own_best_depth_qty": "best_depth_qty_on_candidate_side_at_decision",
    "opposite_best_depth_qty": "best_depth_qty_opposite_candidate_side_at_decision",
}

FEATURE_DEFINITION_SHA256 = "cafe4cc9ff73e92f9d0a6b1c786a3a59769939afdd503fa3146bd262ea3dba92"


class FeatureLabelExecutorError(RuntimeError):
    pass


def _finite(name: str, value: object) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise FeatureLabelExecutorError(name) from exc
    if not math.isfinite(x):
        raise FeatureLabelExecutorError(name)
    return x


def _ns(name: str, value: object) -> int:
    if isinstance(value, bool):
        raise FeatureLabelExecutorError(name)
    try:
        x = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise FeatureLabelExecutorError(name) from exc
    if x < 0 or x != value:
        raise FeatureLabelExecutorError(name)
    return x


@dataclass(frozen=True)
class BookLevel:
    price_tick: int
    qty: float

    def __post_init__(self) -> None:
        if isinstance(self.price_tick, bool) or int(self.price_tick) <= 0:
            raise FeatureLabelExecutorError("book_level_tick")
        if _finite("book_level_qty", self.qty) <= 0.0:
            raise FeatureLabelExecutorError("book_level_qty")


@dataclass(frozen=True)
class BookObservation:
    local_ns: int
    exchange_ns: int
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]

    def __post_init__(self) -> None:
        local = _ns("book_local_ns", self.local_ns)
        exchange = _ns("book_exchange_ns", self.exchange_ns)
        if local < exchange:
            raise FeatureLabelExecutorError("book_negative_feed_latency")
        if not self.bids or not self.asks:
            raise FeatureLabelExecutorError("book_empty_side")
        bid_ticks = tuple(int(x.price_tick) for x in self.bids)
        ask_ticks = tuple(int(x.price_tick) for x in self.asks)
        if bid_ticks != tuple(sorted(bid_ticks, reverse=True)) or len(set(bid_ticks)) != len(bid_ticks):
            raise FeatureLabelExecutorError("bid_order")
        if ask_ticks != tuple(sorted(ask_ticks)) or len(set(ask_ticks)) != len(ask_ticks):
            raise FeatureLabelExecutorError("ask_order")
        if bid_ticks[0] >= ask_ticks[0]:
            raise FeatureLabelExecutorError("crossed_book")

    @property
    def best_bid(self) -> BookLevel:
        return self.bids[0]

    @property
    def best_ask(self) -> BookLevel:
        return self.asks[0]

    @property
    def mid_price(self) -> float:
        return 0.5 * (self.best_bid.price_tick + self.best_ask.price_tick) * float(p0.TICK_SIZE)

    @property
    def spread_ticks(self) -> int:
        return int(self.best_ask.price_tick) - int(self.best_bid.price_tick)


@dataclass(frozen=True)
class FlowObservation:
    local_ns: int
    exchange_ns: int
    kind: str
    side: str
    qty: float

    def __post_init__(self) -> None:
        local = _ns("flow_local_ns", self.local_ns)
        exchange = _ns("flow_exchange_ns", self.exchange_ns)
        if local < exchange:
            raise FeatureLabelExecutorError("flow_negative_feed_latency")
        if self.kind not in ("TRADE", "ADD", "CANCEL"):
            raise FeatureLabelExecutorError("flow_kind")
        if self.kind == "TRADE":
            if self.side not in ("BUY", "SELL"):
                raise FeatureLabelExecutorError("trade_side")
        elif self.side not in p0.CANDIDATE_SIDES:
            raise FeatureLabelExecutorError("book_flow_side")
        if _finite("flow_qty", self.qty) <= 0.0:
            raise FeatureLabelExecutorError("flow_qty")


@dataclass(frozen=True)
class FeatureVector:
    values: Mapping[str, float]
    observable_local_ns: Mapping[str, int]
    support: str


@dataclass(frozen=True)
class LabelBundle:
    fill_labels: tuple[p1.FillHorizonLabel, ...]
    markout_labels: tuple[p1.MarkoutLabel, ...]


def feature_definition_sha256() -> str:
    payload = json.dumps(
        dict(FEATURE_DEFINITIONS),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_book_history(books: Sequence[BookObservation]) -> tuple[BookObservation, ...]:
    ordered = tuple(books)
    if not ordered:
        raise FeatureLabelExecutorError("book_history_empty")
    if any(b.local_ns <= a.local_ns for a, b in zip(ordered, ordered[1:])):
        raise FeatureLabelExecutorError("book_history_not_strict_local")
    return ordered


def validate_flow_history(flows: Sequence[FlowObservation]) -> tuple[FlowObservation, ...]:
    ordered = tuple(flows)
    if any(b.local_ns < a.local_ns for a, b in zip(ordered, ordered[1:])):
        raise FeatureLabelExecutorError("flow_history_not_monotone_local")
    return ordered


def book_asof(*, books: Sequence[BookObservation], target_local_ns: int) -> BookObservation:
    ordered = validate_book_history(books)
    target = _ns("book_asof_target", target_local_ns)
    times = [x.local_ns for x in ordered]
    index = bisect_right(times, target) - 1
    if index < 0:
        raise FeatureLabelExecutorError("book_asof_missing")
    return ordered[index]


def _window_books(
    *,
    books: Sequence[BookObservation],
    start_local_ns: int,
    end_local_ns: int,
) -> tuple[BookObservation, ...]:
    ordered = validate_book_history(books)
    start = _ns("window_start", start_local_ns)
    end = _ns("window_end", end_local_ns)
    if end < start:
        raise FeatureLabelExecutorError("window_bounds")
    anchor = book_asof(books=ordered, target_local_ns=start)
    tail = tuple(x for x in ordered if start < x.local_ns <= end)
    return (anchor,) + tail


def _window_flows(
    *,
    flows: Sequence[FlowObservation],
    start_local_ns: int,
    end_local_ns: int,
) -> tuple[FlowObservation, ...]:
    ordered = validate_flow_history(flows)
    start = _ns("flow_window_start", start_local_ns)
    end = _ns("flow_window_end", end_local_ns)
    if end < start:
        raise FeatureLabelExecutorError("flow_window_bounds")
    return tuple(x for x in ordered if start < x.local_ns <= end)


def _ratio_diff(a: float, b: float) -> float:
    denominator = float(a) + float(b)
    if denominator <= 0.0:
        return 0.0
    return (float(a) - float(b)) / denominator


def _mid(book: BookObservation) -> float:
    mid = float(book.mid_price)
    if mid <= 0.0:
        raise FeatureLabelExecutorError("mid_price")
    return mid


def microprice_bbo(book: BookObservation) -> float:
    bid = book.best_bid
    ask = book.best_ask
    denominator = float(bid.qty) + float(ask.qty)
    if denominator <= 0.0:
        raise FeatureLabelExecutorError("microprice_depth")
    bid_px = float(bid.price_tick) * float(p0.TICK_SIZE)
    ask_px = float(ask.price_tick) * float(p0.TICK_SIZE)
    return (bid_px * float(ask.qty) + ask_px * float(bid.qty)) / denominator


def vamp_l5(book: BookObservation) -> float:
    if len(book.bids) < FEATURE_SUPPORT_REQUIRED_DEPTH_LEVELS or len(book.asks) < FEATURE_SUPPORT_REQUIRED_DEPTH_LEVELS:
        raise FeatureLabelExecutorError("l5_depth_support")
    bids = book.bids[:FEATURE_SUPPORT_REQUIRED_DEPTH_LEVELS]
    asks = book.asks[:FEATURE_SUPPORT_REQUIRED_DEPTH_LEVELS]
    numerator = 0.0
    denominator = 0.0
    for bid, ask in zip(bids, asks):
        bid_px = float(bid.price_tick) * float(p0.TICK_SIZE)
        ask_px = float(ask.price_tick) * float(p0.TICK_SIZE)
        numerator += bid_px * float(ask.qty) + ask_px * float(bid.qty)
        denominator += float(bid.qty) + float(ask.qty)
    if denominator <= 0.0:
        raise FeatureLabelExecutorError("vamp_l5_depth")
    return numerator / denominator


def bbo_ofi_transition(previous: BookObservation, current: BookObservation) -> float:
    pb0 = int(previous.best_bid.price_tick)
    pb1 = int(current.best_bid.price_tick)
    qb0 = float(previous.best_bid.qty)
    qb1 = float(current.best_bid.qty)
    pa0 = int(previous.best_ask.price_tick)
    pa1 = int(current.best_ask.price_tick)
    qa0 = float(previous.best_ask.qty)
    qa1 = float(current.best_ask.qty)

    bid_component = (qb1 if pb1 >= pb0 else 0.0) - (qb0 if pb1 <= pb0 else 0.0)
    ask_component = -(qa1 if pa1 <= pa0 else 0.0) + (qa0 if pa1 >= pa0 else 0.0)
    return bid_component + ask_component


def bbo_ofi(*, books: Sequence[BookObservation], decision_local_ns: int, window_ns: int) -> float:
    decision = _ns("ofi_decision", decision_local_ns)
    window = _ns("ofi_window", window_ns)
    if window <= 0 or decision < window:
        raise FeatureLabelExecutorError("ofi_window")
    series = _window_books(books=books, start_local_ns=decision - window, end_local_ns=decision)
    return sum(bbo_ofi_transition(a, b) for a, b in zip(series, series[1:]))


def trade_imbalance(*, flows: Sequence[FlowObservation], decision_local_ns: int, window_ns: int) -> float:
    decision = _ns("trade_decision", decision_local_ns)
    window = _ns("trade_window", window_ns)
    selected = _window_flows(flows=flows, start_local_ns=decision - window, end_local_ns=decision)
    buy = sum(float(x.qty) for x in selected if x.kind == "TRADE" and x.side == "BUY")
    sell = sum(float(x.qty) for x in selected if x.kind == "TRADE" and x.side == "SELL")
    return _ratio_diff(buy, sell)


def add_imbalance_1s(*, flows: Sequence[FlowObservation], decision_local_ns: int) -> float:
    decision = _ns("add_decision", decision_local_ns)
    selected = _window_flows(flows=flows, start_local_ns=decision - 1_000_000_000, end_local_ns=decision)
    bid = sum(float(x.qty) for x in selected if x.kind == "ADD" and x.side == "BID")
    ask = sum(float(x.qty) for x in selected if x.kind == "ADD" and x.side == "ASK")
    return _ratio_diff(bid, ask)


def cancel_imbalance_1s(*, flows: Sequence[FlowObservation], decision_local_ns: int) -> float:
    decision = _ns("cancel_decision", decision_local_ns)
    selected = _window_flows(flows=flows, start_local_ns=decision - 1_000_000_000, end_local_ns=decision)
    bid = sum(float(x.qty) for x in selected if x.kind == "CANCEL" and x.side == "BID")
    ask = sum(float(x.qty) for x in selected if x.kind == "CANCEL" and x.side == "ASK")
    return _ratio_diff(ask, bid)


def realized_vol_bps(*, books: Sequence[BookObservation], decision_local_ns: int, window_ns: int) -> float:
    decision = _ns("vol_decision", decision_local_ns)
    window = _ns("vol_window", window_ns)
    series = _window_books(books=books, start_local_ns=decision - window, end_local_ns=decision)
    mids = tuple(_mid(x) for x in series)
    squared = 0.0
    for before, after in zip(mids, mids[1:]):
        squared += math.log(after / before) ** 2
    return 10_000.0 * math.sqrt(squared)


def depth_delta_to_flow(
    *,
    local_ns: int,
    exchange_ns: int,
    side: str,
    before_qty: float,
    after_qty: float,
) -> FlowObservation | None:
    if side not in p0.CANDIDATE_SIDES:
        raise FeatureLabelExecutorError("depth_delta_side")
    before = _finite("depth_before_qty", before_qty)
    after = _finite("depth_after_qty", after_qty)
    if before < 0.0 or after < 0.0:
        raise FeatureLabelExecutorError("depth_delta_qty")
    delta = after - before
    if math.isclose(delta, 0.0, rel_tol=0.0, abs_tol=1e-15):
        return None
    if delta > 0.0:
        return FlowObservation(local_ns, exchange_ns, "ADD", side, delta)
    return FlowObservation(local_ns, exchange_ns, "CANCEL", side, -delta)


def trade_to_flow(
    *,
    local_ns: int,
    exchange_ns: int,
    aggressor_side: str,
    qty: float,
) -> FlowObservation:
    return FlowObservation(local_ns, exchange_ns, "TRADE", aggressor_side, qty)


def _visible_qty(book: BookObservation, *, side: str, price_tick: int) -> float:
    levels = book.bids if side == "BID" else book.asks
    for level in levels:
        if int(level.price_tick) == int(price_tick):
            return float(level.qty)
    return 0.0


def _best_depth(book: BookObservation, *, side: str) -> float:
    if side == "BID":
        return float(book.best_bid.qty)
    if side == "ASK":
        return float(book.best_ask.qty)
    raise FeatureLabelExecutorError("best_depth_side")


def compute_features(
    *,
    candidate: p1.CandidateSpec,
    books: Sequence[BookObservation],
    flows: Sequence[FlowObservation],
) -> FeatureVector:
    decision = int(candidate.decision_local_ns)
    if decision < FEATURE_WARMUP_NS:
        raise FeatureLabelExecutorError("feature_warmup")

    ordered_books = validate_book_history(books)
    validate_flow_history(flows)
    current = book_asof(books=ordered_books, target_local_ns=decision)
    anchor_30s = book_asof(books=ordered_books, target_local_ns=decision - FEATURE_WARMUP_NS)
    del anchor_30s

    if len(current.bids) < FEATURE_SUPPORT_REQUIRED_DEPTH_LEVELS or len(current.asks) < FEATURE_SUPPORT_REQUIRED_DEPTH_LEVELS:
        raise FeatureLabelExecutorError("current_l5_support")

    mid = _mid(current)
    micro = microprice_bbo(current)
    vamp5 = vamp_l5(current)
    sum_bid5 = sum(float(x.qty) for x in current.bids[:5])
    sum_ask5 = sum(float(x.qty) for x in current.asks[:5])

    ofi1 = bbo_ofi(books=ordered_books, decision_local_ns=decision, window_ns=1_000_000_000)
    ofi5 = bbo_ofi(books=ordered_books, decision_local_ns=decision, window_ns=5_000_000_000)

    prior250 = book_asof(books=ordered_books, target_local_ns=decision - 250_000_000)
    prior1s = book_asof(books=ordered_books, target_local_ns=decision - 1_000_000_000)

    side = candidate.side
    opposite = "ASK" if side == "BID" else "BID"
    displayed = _visible_qty(current, side=side, price_tick=candidate.price_tick)

    values = {
        "spread_ticks": float(current.spread_ticks),
        "microprice_minus_mid_bps": 10_000.0 * (micro - mid) / mid,
        "vamp_bbo_minus_mid_bps": 10_000.0 * (micro - mid) / mid,
        "vamp_l5_minus_mid_bps": 10_000.0 * (vamp5 - mid) / mid,
        "l1_obi": _ratio_diff(float(current.best_bid.qty), float(current.best_ask.qty)),
        "l5_obi": _ratio_diff(sum_bid5, sum_ask5),
        "bbo_ofi_1s": ofi1,
        "bbo_ofi_5s": ofi5,
        "trade_imbalance_1s": trade_imbalance(flows=flows, decision_local_ns=decision, window_ns=1_000_000_000),
        "trade_imbalance_5s": trade_imbalance(flows=flows, decision_local_ns=decision, window_ns=5_000_000_000),
        "add_imbalance_1s": add_imbalance_1s(flows=flows, decision_local_ns=decision),
        "cancel_imbalance_1s": cancel_imbalance_1s(flows=flows, decision_local_ns=decision),
        "ofi_acceleration_1s_vs_5s": ofi1 - ofi5 / 5.0,
        "same_side_depth_change_250ms": _best_depth(current, side=side) - _best_depth(prior250, side=side),
        "opposite_side_depth_change_250ms": _best_depth(current, side=opposite) - _best_depth(prior250, side=opposite),
        "spread_change_1s": float(current.spread_ticks - prior1s.spread_ticks),
        "realized_vol_1s": realized_vol_bps(books=ordered_books, decision_local_ns=decision, window_ns=1_000_000_000),
        "realized_vol_5s": realized_vol_bps(books=ordered_books, decision_local_ns=decision, window_ns=5_000_000_000),
        "realized_vol_30s": realized_vol_bps(books=ordered_books, decision_local_ns=decision, window_ns=30_000_000_000),
        "candidate_side_sign": float(candidate.side_sign),
        "candidate_distance_ticks": float(candidate.distance_ticks),
        "displayed_qty_at_candidate_price": displayed,
        "estimated_queue_ahead_qty_from_decision_book": displayed,
        "own_best_depth_qty": _best_depth(current, side=side),
        "opposite_best_depth_qty": _best_depth(current, side=opposite),
    }

    if tuple(values) != FEATURE_NAMES:
        raise FeatureLabelExecutorError("feature_order")
    if any(not math.isfinite(float(x)) for x in values.values()):
        raise FeatureLabelExecutorError("feature_nonfinite")
    if values["microprice_minus_mid_bps"] != values["vamp_bbo_minus_mid_bps"]:
        raise FeatureLabelExecutorError("bbo_vamp_equivalence")
    if values["displayed_qty_at_candidate_price"] != values["estimated_queue_ahead_qty_from_decision_book"]:
        raise FeatureLabelExecutorError("queue_display_equivalence")

    observable = {name: decision for name in FEATURE_NAMES}
    p1.validate_feature_observability(
        decision_local_ns=decision,
        feature_observable_local_ns=observable,
    )

    return FeatureVector(
        values=values,
        observable_local_ns=observable,
        support=p2.CANDIDATE_ELIGIBILITY,
    )


def build_label_bundle(
    *,
    candidate: p1.CandidateSpec,
    fills: Sequence[p1.FillObservation],
    midpoints: Sequence[p1.MidObservation],
    source_exchange_observed_through_ns: int,
    placement_outcome: str,
) -> LabelBundle:
    fill_labels = tuple(
        p1.fill_horizon_label(
            candidate=candidate,
            fills=fills,
            horizon_ns=horizon,
            source_exchange_observed_through_ns=source_exchange_observed_through_ns,
            placement_outcome=placement_outcome,
        )
        for horizon in p0.FILL_HORIZONS_NS
    )
    markout_labels = tuple(
        p1.candidate_markout_label(
            candidate=candidate,
            fills=fills,
            midpoints=midpoints,
            horizon_ns=horizon,
            source_exchange_observed_through_ns=source_exchange_observed_through_ns,
            fill_inclusion_horizon_ns=p1.MARKOUT_FILL_INCLUSION_HORIZON_NS,
        )
        for horizon in p0.MARKOUT_HORIZONS_NS
    )
    return LabelBundle(fill_labels=fill_labels, markout_labels=markout_labels)


def validate_r8b_contract() -> None:
    r8a.validate_r8a_contract()
    p0.validate_design_contract()
    p1.validate_p1_contract()
    p2.validate_design_contract()

    if PARENT_R8A_HEAD != "abcfd786e5c8345b9857310f98e5e7e856d75815":
        raise FeatureLabelExecutorError("parent")
    if DATA_ROLE != "CONSUMED_DEVELOPMENT":
        raise FeatureLabelExecutorError("data_role")
    if len(FEATURE_NAMES) != 25 or tuple(FEATURE_DEFINITIONS) != FEATURE_NAMES:
        raise FeatureLabelExecutorError("feature_identity")
    if feature_definition_sha256() != FEATURE_DEFINITION_SHA256:
        raise FeatureLabelExecutorError("feature_definition_sha256")
    if FEATURE_WARMUP_NS != 30_000_000_000 or FEATURE_SUPPORT_REQUIRED_DEPTH_LEVELS != 5:
        raise FeatureLabelExecutorError("feature_support")
    if not all((FEATURE_LABEL_EXECUTOR_FROZEN, PURE_SYNTHETIC_CONTRACT_ONLY, WINDOW_LEFT_OPEN_RIGHT_CLOSED, MICROPRICE_EQUALS_VAMP_BBO_BY_DEFINITION, QUEUE_AHEAD_EQUALS_DISPLAYED_QTY_BY_FROZEN_ESTIMATE)):
        raise FeatureLabelExecutorError("required_semantic_guard")
    if p0.MARKOUT_ORIGIN != "EXCHANGE_EXECUTION_TIME" or p1.FILL_HORIZON_ORIGIN != "DECISION_LOCAL_TIME":
        raise FeatureLabelExecutorError("label_time_origin")

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
        NETWORK_ACQUISITION_AUTHORIZED,
    )
    if any(forbidden):
        raise FeatureLabelExecutorError("execution_surface_open")


__all__ = [
    "BookLevel",
    "BookObservation",
    "FlowObservation",
    "FeatureVector",
    "LabelBundle",
    "FEATURE_NAMES",
    "FEATURE_DEFINITIONS",
    "FEATURE_DEFINITION_SHA256",
    "feature_definition_sha256",
    "book_asof",
    "microprice_bbo",
    "vamp_l5",
    "bbo_ofi_transition",
    "bbo_ofi",
    "trade_imbalance",
    "add_imbalance_1s",
    "cancel_imbalance_1s",
    "realized_vol_bps",
    "depth_delta_to_flow",
    "trade_to_flow",
    "compute_features",
    "build_label_bundle",
    "validate_r8b_contract",
]

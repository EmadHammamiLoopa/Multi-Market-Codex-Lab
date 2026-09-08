from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Mapping, Sequence

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b

EXPERIMENT_ID = "DEV045-D6R26A-P2-R9"
DESIGN_VERSION = "raw-event-decoder-freeze-v1"
PARENT_R8B_HEAD = "24030d3b677449fa48042881ffb189233a7121ce"
UPSTREAM_HFTBACKTEST_HEAD = "a244a14250b42d97fc305569c93c4117cd5e1dff"

# Exact hftbacktest 2.4.4 event identities at the frozen upstream commit.
DEPTH_EVENT = 1
TRADE_EVENT = 2
DEPTH_CLEAR_EVENT = 3
DEPTH_SNAPSHOT_EVENT = 4
DEPTH_BBO_EVENT = 5
ADD_ORDER_EVENT = 10
CANCEL_ORDER_EVENT = 11
MODIFY_ORDER_EVENT = 12
FILL_EVENT = 13
EXCH_EVENT = 1 << 31
LOCAL_EVENT = 1 << 30
BUY_EVENT = 1 << 29
SELL_EVENT = 1 << 28
EVENT_KIND_MASK = 0xFF

RAW_EVENT_DECODER_FROZEN = True
PURE_SYNTHETIC_CONTRACT_ONLY = True
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

DECODER_DEFINITIONS: Mapping[str, str] = {
    "event_kind_mask": "ev & 0xFF",
    "local_filter": "(ev & LOCAL_EVENT) == LOCAL_EVENT",
    "exchange_filter": "(ev & EXCH_EVENT) == EXCH_EVENT",
    "supported_depth_types": "DEPTH_EVENT=1;DEPTH_CLEAR_EVENT=3;DEPTH_SNAPSHOT_EVENT=4",
    "trade_type": "TRADE_EVENT=2",
    "ignored_l2_parity_types": "DEPTH_BBO_EVENT=5;ADD_ORDER_EVENT=10;CANCEL_ORDER_EVENT=11;MODIFY_ORDER_EVENT=12;FILL_EVENT=13",
    "side_flags": "BUY_EVENT=1<<29;SELL_EVENT=1<<28;both_or_neither_invalid_for_sided_depth_or_trade",
    "price_tick": "round(px/TICK_SIZE); require finite positive aligned price",
    "qty_lot": "round(qty/LOT_SIZE); qty_lot==0 removes level; else store raw qty",
    "bid_clear_finite": "remove bid ticks >= round(clear_upto_price/TICK_SIZE)",
    "ask_clear_finite": "remove ask ticks <= round(clear_upto_price/TICK_SIZE)",
    "sided_clear_nonfinite": "clear entire named side",
    "unsided_clear": "clear both sides",
    "snapshot_flow": "snapshot updates book but emits no ADD/CANCEL flow",
    "clear_flow": "clear updates book but emits no ADD/CANCEL flow",
    "depth_event_flow": "only DEPTH_EVENT absolute-qty delta emits ADD/CANCEL flow",
    "trade_flow": "TRADE_EVENT emits aggressive BUY/SELL flow; does not mutate L2 book",
    "local_group": "process LOCAL_EVENT rows in input order; require nondecreasing local_ts; emit at most one final post-market BookObservation per local_ns",
    "local_book_exchange_ns": "max exch_ts among rows in emitted local_ns group",
    "exchange_group": "process EXCH_EVENT depth rows in input order; require nondecreasing exch_ts; emit one MidObservation after each exchange_ns group that changed a valid book",
    "bbo_event_policy": "DEPTH_BBO_EVENT ignored to mirror exact a244a142 L2 Local processor",
    "unknown_event_policy": "unknown low-byte event type fails closed",
    "flow_same_timestamp": "preserve source row order; FlowObservation local_ns may tie",
}
DECODER_DEFINITION_SHA256 = "50ddc5f01872cb6155d7ea3f8adc8e040a95407249657e2c891859d4921fdd58"

IGNORED_L2_EVENT_TYPES = {
    DEPTH_BBO_EVENT,
    ADD_ORDER_EVENT,
    CANCEL_ORDER_EVENT,
    MODIFY_ORDER_EVENT,
    FILL_EVENT,
}
SUPPORTED_EVENT_TYPES = {
    DEPTH_EVENT,
    TRADE_EVENT,
    DEPTH_CLEAR_EVENT,
    DEPTH_SNAPSHOT_EVENT,
    *IGNORED_L2_EVENT_TYPES,
}


class RawEventDecoderError(RuntimeError):
    pass


@dataclass(frozen=True)
class DecodedHistory:
    books: tuple[r8b.BookObservation, ...]
    flows: tuple[r8b.FlowObservation, ...]


@dataclass
class _BookState:
    bids: dict[int, float]
    asks: dict[int, float]

    @classmethod
    def empty(cls) -> "_BookState":
        return cls({}, {})

    def valid(self) -> bool:
        return bool(self.bids and self.asks and max(self.bids) < min(self.asks))

    def observation(self, *, local_ns: int, exchange_ns: int) -> r8b.BookObservation:
        if not self.valid():
            raise RawEventDecoderError("book_not_valid")
        bids = tuple(
            r8b.BookLevel(tick, qty)
            for tick, qty in sorted(self.bids.items(), reverse=True)
            if qty > 0.0
        )
        asks = tuple(
            r8b.BookLevel(tick, qty)
            for tick, qty in sorted(self.asks.items())
            if qty > 0.0
        )
        return r8b.BookObservation(
            local_ns=int(local_ns),
            exchange_ns=int(exchange_ns),
            bids=bids,
            asks=asks,
        )


def decoder_definition_sha256() -> str:
    payload = json.dumps(
        dict(DECODER_DEFINITIONS),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _event_kind(ev: int) -> int:
    return int(ev) & EVENT_KIND_MASK


def _has_flag(ev: int, flag: int) -> bool:
    return (int(ev) & int(flag)) == int(flag)


def _side(ev: int, *, required: bool) -> str | None:
    buy = _has_flag(ev, BUY_EVENT)
    sell = _has_flag(ev, SELL_EVENT)
    if buy and sell:
        raise RawEventDecoderError("event_both_sides")
    if buy:
        return "BID"
    if sell:
        return "ASK"
    if required:
        raise RawEventDecoderError("event_side_missing")
    return None


def _aggressor_side(ev: int) -> str:
    side = _side(ev, required=True)
    return "BUY" if side == "BID" else "SELL"


def _aligned_tick(px: float) -> int:
    x = float(px)
    if not math.isfinite(x) or x <= 0.0:
        raise RawEventDecoderError("event_price")
    scaled = x / float(p0.TICK_SIZE)
    tick = int(math.floor(scaled + 0.5))
    if not math.isclose(scaled, tick, rel_tol=0.0, abs_tol=1e-8):
        raise RawEventDecoderError("event_price_not_tick_aligned")
    return tick


def _qty_lot(qty: float) -> int:
    q = float(qty)
    if not math.isfinite(q) or q < 0.0:
        raise RawEventDecoderError("event_qty")
    scaled = q / float(p0.LOT_SIZE)
    return int(math.floor(scaled + 0.5))


def _validate_event_array(events: np.ndarray) -> np.ndarray:
    a = np.asarray(events)
    required = {"ev", "exch_ts", "local_ts", "px", "qty"}
    if a.ndim != 1 or not a.dtype.names or not required.issubset(a.dtype.names):
        raise RawEventDecoderError("event_array_schema")
    return a


def _set_depth_level(
    state: _BookState,
    *,
    side: str,
    price_tick: int,
    qty: float,
    emit_flow: bool,
    local_ns: int,
    exchange_ns: int,
) -> r8b.FlowObservation | None:
    book = state.bids if side == "BID" else state.asks
    before = float(book.get(int(price_tick), 0.0))
    q = float(qty)
    if _qty_lot(q) == 0:
        book.pop(int(price_tick), None)
        after = 0.0
    else:
        book[int(price_tick)] = q
        after = q
    if not emit_flow:
        return None
    return r8b.depth_delta_to_flow(
        local_ns=int(local_ns),
        exchange_ns=int(exchange_ns),
        side=side,
        before_qty=before,
        after_qty=after,
    )


def _clear_depth(state: _BookState, *, side: str | None, px: float) -> None:
    if side is None:
        state.bids.clear()
        state.asks.clear()
        return
    book = state.bids if side == "BID" else state.asks
    x = float(px)
    if not math.isfinite(x):
        book.clear()
        return
    tick = _aligned_tick(x)
    if side == "BID":
        for key in tuple(book):
            if key >= tick:
                del book[key]
    else:
        for key in tuple(book):
            if key <= tick:
                del book[key]


def _process_depth_row(
    state: _BookState,
    row,
    *,
    timestamp_domain: str,
    emit_flow: bool,
) -> r8b.FlowObservation | None:
    ev = int(row["ev"])
    kind = _event_kind(ev)
    local_ns = int(row["local_ts"])
    exchange_ns = int(row["exch_ts"])

    if kind == DEPTH_CLEAR_EVENT:
        _clear_depth(state, side=_side(ev, required=False), px=float(row["px"]))
        return None
    if kind not in (DEPTH_EVENT, DEPTH_SNAPSHOT_EVENT):
        raise RawEventDecoderError("not_depth_row")
    side = _side(ev, required=True)
    tick = _aligned_tick(float(row["px"]))
    return _set_depth_level(
        state,
        side=side,
        price_tick=tick,
        qty=float(row["qty"]),
        emit_flow=bool(emit_flow and kind == DEPTH_EVENT and timestamp_domain == "LOCAL"),
        local_ns=local_ns,
        exchange_ns=exchange_ns,
    )


def decode_local_history(events: np.ndarray) -> DecodedHistory:
    a = _validate_event_array(events)
    state = _BookState.empty()
    books: list[r8b.BookObservation] = []
    flows: list[r8b.FlowObservation] = []

    current_local: int | None = None
    group_exchange_max = 0
    group_market_changed = False
    last_local = -1

    def flush() -> None:
        nonlocal group_market_changed
        if current_local is not None and group_market_changed and state.valid():
            books.append(
                state.observation(
                    local_ns=current_local,
                    exchange_ns=group_exchange_max,
                )
            )
        group_market_changed = False

    for row in a:
        ev = int(row["ev"])
        kind = _event_kind(ev)
        if kind not in SUPPORTED_EVENT_TYPES:
            raise RawEventDecoderError(f"unknown_event_kind:{kind}")
        if not _has_flag(ev, LOCAL_EVENT):
            continue
        local_ns = int(row["local_ts"])
        exchange_ns = int(row["exch_ts"])
        if local_ns < 0 or exchange_ns < 0 or local_ns < exchange_ns:
            raise RawEventDecoderError("event_timestamp")
        if local_ns < last_local:
            raise RawEventDecoderError("local_timestamp_regression")
        if current_local is None:
            current_local = local_ns
        elif local_ns != current_local:
            flush()
            current_local = local_ns
            group_exchange_max = 0
        last_local = local_ns
        group_exchange_max = max(group_exchange_max, exchange_ns)

        if kind in (DEPTH_EVENT, DEPTH_CLEAR_EVENT, DEPTH_SNAPSHOT_EVENT):
            flow = _process_depth_row(state, row, timestamp_domain="LOCAL", emit_flow=True)
            if flow is not None:
                flows.append(flow)
            group_market_changed = True
        elif kind == TRADE_EVENT:
            flows.append(
                r8b.trade_to_flow(
                    local_ns=local_ns,
                    exchange_ns=exchange_ns,
                    aggressor_side=_aggressor_side(ev),
                    qty=float(row["qty"]),
                )
            )
        elif kind in IGNORED_L2_EVENT_TYPES:
            # Exact L2 Local processor parity: these event types are not applied.
            continue

    flush()
    r8b.validate_book_history(books)
    r8b.validate_flow_history(flows)
    return DecodedHistory(tuple(books), tuple(flows))


def decode_exchange_midpoints(events: np.ndarray) -> tuple[r8b.p1.MidObservation, ...]:
    a = _validate_event_array(events)
    state = _BookState.empty()
    out: list[r8b.p1.MidObservation] = []
    current_exchange: int | None = None
    group_changed = False
    last_exchange = -1

    def flush() -> None:
        nonlocal group_changed
        if current_exchange is not None and group_changed and state.valid():
            out.append(
                r8b.p1.MidObservation(
                    exchange_ns=current_exchange,
                    best_bid_tick=max(state.bids),
                    best_ask_tick=min(state.asks),
                )
            )
        group_changed = False

    for row in a:
        ev = int(row["ev"])
        kind = _event_kind(ev)
        if kind not in SUPPORTED_EVENT_TYPES:
            raise RawEventDecoderError(f"unknown_event_kind:{kind}")
        if not _has_flag(ev, EXCH_EVENT):
            continue
        exchange_ns = int(row["exch_ts"])
        if exchange_ns < 0:
            raise RawEventDecoderError("exchange_timestamp")
        if exchange_ns < last_exchange:
            raise RawEventDecoderError("exchange_timestamp_regression")
        if current_exchange is None:
            current_exchange = exchange_ns
        elif exchange_ns != current_exchange:
            flush()
            current_exchange = exchange_ns
        last_exchange = exchange_ns
        if kind in (DEPTH_EVENT, DEPTH_CLEAR_EVENT, DEPTH_SNAPSHOT_EVENT):
            _process_depth_row(state, row, timestamp_domain="EXCHANGE", emit_flow=False)
            group_changed = True
        elif kind in (TRADE_EVENT, *IGNORED_L2_EVENT_TYPES):
            continue

    flush()
    return tuple(out)


def validate_r9_contract() -> None:
    r8b.validate_r8b_contract()
    if PARENT_R8B_HEAD != "24030d3b677449fa48042881ffb189233a7121ce":
        raise RawEventDecoderError("parent")
    if UPSTREAM_HFTBACKTEST_HEAD != "a244a14250b42d97fc305569c93c4117cd5e1dff":
        raise RawEventDecoderError("upstream")
    expected_constants = (1, 2, 3, 4, 5, 10, 11, 12, 13, 1 << 31, 1 << 30, 1 << 29, 1 << 28)
    observed_constants = (
        DEPTH_EVENT, TRADE_EVENT, DEPTH_CLEAR_EVENT, DEPTH_SNAPSHOT_EVENT,
        DEPTH_BBO_EVENT, ADD_ORDER_EVENT, CANCEL_ORDER_EVENT, MODIFY_ORDER_EVENT,
        FILL_EVENT, EXCH_EVENT, LOCAL_EVENT, BUY_EVENT, SELL_EVENT,
    )
    if observed_constants != expected_constants:
        raise RawEventDecoderError("event_constant_identity")
    if decoder_definition_sha256() != DECODER_DEFINITION_SHA256:
        raise RawEventDecoderError("decoder_definition_sha256")
    if not RAW_EVENT_DECODER_FROZEN or not PURE_SYNTHETIC_CONTRACT_ONLY:
        raise RawEventDecoderError("decoder_freeze")
    forbidden = (
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
        raise RawEventDecoderError("execution_surface_open")


__all__ = [
    "DecodedHistory",
    "DECODER_DEFINITIONS",
    "DECODER_DEFINITION_SHA256",
    "decoder_definition_sha256",
    "decode_local_history",
    "decode_exchange_midpoints",
    "validate_r9_contract",
]

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9
from multimarket import dev045_d6r26a_p2_r13_streaming_raw_decoder_preexecution as r13
from multimarket import dev045_d6r26a_p2_r13a_dual_stream_eof_memory_amendment as r13a
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p3_fused_full_context_kernel_architecture_freeze as r27p3

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P4"
DESIGN_VERSION = "compiled-dual-book-state-kernel-preexecution-v1"
PARENT_R27P3_HEAD = "85e48a50853a5d222540ae06e7301941392b32d6"

ACCELERATOR_FAMILY = "NUMBA_JIT"
COMPILED_DUAL_BOOK_STATE_FOUNDATION = True
LOCAL_AND_EXCHANGE_BOOKS_IN_ONE_COMPILED_PASS = True
TOP5_LOCAL_BOOK_SURFACE_EXACT_PARITY_REQUIRED = True
EXCHANGE_MIDPOINT_EXACT_PARITY_REQUIRED = True
ACTIVE_LEVEL_COUNT_PARITY_REQUIRED = True
UNKNOWN_EVENT_FAIL_CLOSED = True
TIMESTAMP_REGRESSION_FAIL_CLOSED = True
CLEAR_AND_SNAPSHOT_SEMANTICS_FROZEN = True
TRADE_DOES_NOT_MUTATE_BOOK_FROZEN = True
IGNORED_EVENT_POLICY_FROZEN = True
SOURCE_ORDER_WITHIN_GROUP_FROZEN = True
FINAL_GROUP_FLUSH_REQUIRED = True

# R27P4 is still synthetic/preexecution. It does not yet replace the R20
# rolling-feature accumulator or authorize historical execution.
FULL_CONTEXT_REPLACEMENT_AUTHORIZED = False
REAL_HISTORICAL_BENCHMARK_AUTHORIZED = False
FULL_JAN_JUL_RERUN_AUTHORIZED = False
DURABLE_CONTEXT_WRITE_AUTHORIZED = False
P2_ATTEMPT_CONSUMED = False
SIMULATOR_LANE_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

TOP_DEPTH_LEVELS = 5


class R27P4Error(RuntimeError):
    pass


@dataclass(frozen=True)
class DualBookKernelResult:
    local_ns: np.ndarray
    local_exchange_ns: np.ndarray
    bid_ticks: np.ndarray
    bid_qty: np.ndarray
    ask_ticks: np.ndarray
    ask_qty: np.ndarray
    local_bid_level_count: np.ndarray
    local_ask_level_count: np.ndarray
    midpoint_exchange_ns: np.ndarray
    midpoint_tick_sum: np.ndarray
    local_active_level_count: int
    exchange_active_level_count: int


def _load_numba():
    try:
        from numba import njit, types
        from numba.typed import Dict
    except Exception as exc:
        raise R27P4Error("numba_unavailable") from exc
    return njit, types, Dict


def build_dual_book_kernel():
    njit, types, Dict = _load_numba()

    event_mask = int(r9.EVENT_KIND_MASK)
    local_flag = int(r9.LOCAL_EVENT)
    exch_flag = int(r9.EXCH_EVENT)
    buy_flag = int(r9.BUY_EVENT)
    sell_flag = int(r9.SELL_EVENT)

    depth = int(r9.DEPTH_EVENT)
    trade = int(r9.TRADE_EVENT)
    clear = int(r9.DEPTH_CLEAR_EVENT)
    snapshot = int(r9.DEPTH_SNAPSHOT_EVENT)
    ignored = tuple(sorted(int(x) for x in r9.IGNORED_L2_EVENT_TYPES))
    supported = tuple(sorted(int(x) for x in r9.SUPPORTED_EVENT_TYPES))
    tick_size = float(p0.TICK_SIZE)
    lot_size = float(p0.LOT_SIZE)

    @njit(cache=False)
    def _kind_supported(kind):
        for x in supported:
            if kind == x:
                return True
        return False

    @njit(cache=False)
    def _kind_ignored(kind):
        for x in ignored:
            if kind == x:
                return True
        return False

    @njit(cache=False)
    def _side(ev, required):
        buy = (ev & buy_flag) == buy_flag
        sell = (ev & sell_flag) == sell_flag
        if buy and sell:
            return 0
        if buy:
            return 1
        if sell:
            return -1
        if required:
            return 0
        return 2

    @njit(cache=False)
    def _aligned_tick(px):
        if not math.isfinite(px) or px <= 0.0:
            return -1
        scaled = px / tick_size
        tick = int(math.floor(scaled + 0.5))
        if abs(scaled - tick) > 1e-8:
            return -1
        return tick

    @njit(cache=False)
    def _qty_lot(qty):
        if not math.isfinite(qty) or qty < 0.0:
            return -1
        return int(math.floor(qty / lot_size + 0.5))

    @njit(cache=False)
    def _set_level(bids, asks, side, tick, qty):
        if _qty_lot(qty) < 0:
            return 1
        book = bids if side == 1 else asks
        if _qty_lot(qty) == 0:
            if tick in book:
                del book[tick]
        else:
            book[tick] = qty
        return 0

    @njit(cache=False)
    def _clear_book(bids, asks, side, px):
        if side == 2:
            bids.clear(); asks.clear(); return 0
        book = bids if side == 1 else asks
        if not math.isfinite(px):
            book.clear(); return 0
        tick = _aligned_tick(px)
        if tick < 0:
            return 1
        keys = list(book.keys())
        if side == 1:
            for key in keys:
                if key >= tick:
                    del book[key]
        else:
            for key in keys:
                if key <= tick:
                    del book[key]
        return 0

    @njit(cache=False)
    def _valid(bids, asks):
        if len(bids) == 0 or len(asks) == 0:
            return False
        best_bid = -9223372036854775807
        best_ask = 9223372036854775807
        for k in bids.keys():
            if k > best_bid:
                best_bid = k
        for k in asks.keys():
            if k < best_ask:
                best_ask = k
        return best_bid < best_ask

    @njit(cache=False)
    def _top5(book, descending, out_ticks, out_qty, row):
        for j in range(TOP_DEPTH_LEVELS):
            out_ticks[row, j] = 0
            out_qty[row, j] = 0.0
        for k, q in book.items():
            if q <= 0.0:
                continue
            insert = TOP_DEPTH_LEVELS
            for j in range(TOP_DEPTH_LEVELS):
                existing = out_ticks[row, j]
                if existing == 0 or (descending and k > existing) or ((not descending) and k < existing):
                    insert = j
                    break
            if insert < TOP_DEPTH_LEVELS:
                for j in range(TOP_DEPTH_LEVELS - 1, insert, -1):
                    out_ticks[row, j] = out_ticks[row, j - 1]
                    out_qty[row, j] = out_qty[row, j - 1]
                out_ticks[row, insert] = k
                out_qty[row, insert] = q

    @njit(cache=False)
    def kernel(ev, exch_ts, local_ts, px, qty):
        n = ev.size
        local_out_ns = np.empty(n, dtype=np.int64)
        local_out_exch = np.empty(n, dtype=np.int64)
        bid_ticks = np.empty((n, TOP_DEPTH_LEVELS), dtype=np.int64)
        bid_qty = np.empty((n, TOP_DEPTH_LEVELS), dtype=np.float64)
        ask_ticks = np.empty((n, TOP_DEPTH_LEVELS), dtype=np.int64)
        ask_qty = np.empty((n, TOP_DEPTH_LEVELS), dtype=np.float64)
        bid_counts = np.empty(n, dtype=np.int64)
        ask_counts = np.empty(n, dtype=np.int64)
        midpoint_ns = np.empty(n, dtype=np.int64)
        midpoint_sum = np.empty(n, dtype=np.int64)

        lb = Dict.empty(types.int64, types.float64)
        la = Dict.empty(types.int64, types.float64)
        eb = Dict.empty(types.int64, types.float64)
        ea = Dict.empty(types.int64, types.float64)

        local_count = 0
        mid_count = 0
        current_local = -1
        current_exchange = -1
        local_group_exchange_max = 0
        local_changed = False
        exchange_changed = False
        last_local = -1
        last_exchange = -1
        error = 0

        def flush_local():
            nonlocal local_count, local_changed
            if current_local >= 0 and local_changed and _valid(lb, la):
                local_out_ns[local_count] = current_local
                local_out_exch[local_count] = local_group_exchange_max
                _top5(lb, True, bid_ticks, bid_qty, local_count)
                _top5(la, False, ask_ticks, ask_qty, local_count)
                bid_counts[local_count] = len(lb)
                ask_counts[local_count] = len(la)
                local_count += 1
            local_changed = False

        def flush_exchange():
            nonlocal mid_count, exchange_changed
            if current_exchange >= 0 and exchange_changed and _valid(eb, ea):
                bb = -9223372036854775807
                aa = 9223372036854775807
                for k in eb.keys():
                    if k > bb:
                        bb = k
                for k in ea.keys():
                    if k < aa:
                        aa = k
                midpoint_ns[mid_count] = current_exchange
                midpoint_sum[mid_count] = bb + aa
                mid_count += 1
            exchange_changed = False

        for i in range(n):
            e = int(ev[i]); kind = e & event_mask
            if not _kind_supported(kind):
                error = 1; break

            if (e & local_flag) == local_flag:
                lts = int(local_ts[i]); ets = int(exch_ts[i])
                if lts < 0 or ets < 0 or lts < ets:
                    error = 2; break
                if lts < last_local:
                    error = 3; break
                if current_local < 0:
                    current_local = lts
                elif lts != current_local:
                    flush_local(); current_local = lts; local_group_exchange_max = 0
                last_local = lts
                if ets > local_group_exchange_max:
                    local_group_exchange_max = ets
                if kind == depth or kind == clear or kind == snapshot:
                    side = _side(e, kind != clear)
                    if side == 0:
                        error = 4; break
                    if kind == clear:
                        if _clear_book(lb, la, side, float(px[i])) != 0:
                            error = 5; break
                    else:
                        tick = _aligned_tick(float(px[i]))
                        if tick < 0:
                            error = 5; break
                        if _set_level(lb, la, side, tick, float(qty[i])) != 0:
                            error = 6; break
                    local_changed = True
                elif kind == trade or _kind_ignored(kind):
                    pass

            if (e & exch_flag) == exch_flag:
                ets = int(exch_ts[i])
                if ets < 0:
                    error = 7; break
                if ets < last_exchange:
                    error = 8; break
                if current_exchange < 0:
                    current_exchange = ets
                elif ets != current_exchange:
                    flush_exchange(); current_exchange = ets
                last_exchange = ets
                if kind == depth or kind == clear or kind == snapshot:
                    side = _side(e, kind != clear)
                    if side == 0:
                        error = 9; break
                    if kind == clear:
                        if _clear_book(eb, ea, side, float(px[i])) != 0:
                            error = 10; break
                    else:
                        tick = _aligned_tick(float(px[i]))
                        if tick < 0:
                            error = 10; break
                        if _set_level(eb, ea, side, tick, float(qty[i])) != 0:
                            error = 11; break
                    exchange_changed = True
                elif kind == trade or _kind_ignored(kind):
                    pass

        if error == 0:
            flush_local(); flush_exchange()

        return (
            local_out_ns[:local_count], local_out_exch[:local_count],
            bid_ticks[:local_count], bid_qty[:local_count],
            ask_ticks[:local_count], ask_qty[:local_count],
            bid_counts[:local_count], ask_counts[:local_count],
            midpoint_ns[:mid_count], midpoint_sum[:mid_count],
            len(lb) + len(la), len(eb) + len(ea), error,
        )

    return kernel


def run_dual_book_kernel(events: np.ndarray, *, kernel=None) -> DualBookKernelResult:
    a = r9._validate_event_array(events)
    k = build_dual_book_kernel() if kernel is None else kernel
    out = k(a["ev"], a["exch_ts"], a["local_ts"], a["px"], a["qty"])
    error = int(out[12])
    reasons = {
        1: "unknown_event_kind", 2: "local_timestamp", 3: "local_timestamp_regression",
        4: "local_side", 5: "local_price", 6: "local_qty", 7: "exchange_timestamp",
        8: "exchange_timestamp_regression", 9: "exchange_side", 10: "exchange_price", 11: "exchange_qty",
    }
    if error:
        raise R27P4Error(reasons.get(error, f"kernel_error:{error}"))
    arrays = [np.asarray(x) for x in out[:10]]
    for x in arrays:
        x.setflags(write=False)
    return DualBookKernelResult(
        local_ns=arrays[0], local_exchange_ns=arrays[1], bid_ticks=arrays[2], bid_qty=arrays[3],
        ask_ticks=arrays[4], ask_qty=arrays[5], local_bid_level_count=arrays[6], local_ask_level_count=arrays[7],
        midpoint_exchange_ns=arrays[8], midpoint_tick_sum=arrays[9],
        local_active_level_count=int(out[10]), exchange_active_level_count=int(out[11]),
    )


def _reference_surface(events: np.ndarray) -> DualBookKernelResult:
    local_decoder = r13.LocalStreamingDecoder()
    exchange_decoder = r13a.ExchangeStreamingDecoder()
    local_groups = []
    mids = []
    for row in r9._validate_event_array(events):
        local_groups.extend(local_decoder.feed(row))
        mids.extend(exchange_decoder.feed(row))
    local_groups.extend(local_decoder.finish())
    mids.extend(exchange_decoder.finish())

    books = [g.books[-1] for g in local_groups if g.books]
    n = len(books)
    local_ns = np.asarray([b.local_ns for b in books], dtype="<i8")
    local_ex = np.asarray([b.exchange_ns for b in books], dtype="<i8")
    bt = np.zeros((n, TOP_DEPTH_LEVELS), dtype="<i8")
    bq = np.zeros((n, TOP_DEPTH_LEVELS), dtype="<f8")
    at = np.zeros((n, TOP_DEPTH_LEVELS), dtype="<i8")
    aq = np.zeros((n, TOP_DEPTH_LEVELS), dtype="<f8")
    bc = np.zeros(n, dtype="<i8"); ac = np.zeros(n, dtype="<i8")
    for i, book in enumerate(books):
        bc[i] = len(book.bids); ac[i] = len(book.asks)
        for j, level in enumerate(book.bids[:TOP_DEPTH_LEVELS]):
            bt[i, j] = int(level.price_tick); bq[i, j] = float(level.qty)
        for j, level in enumerate(book.asks[:TOP_DEPTH_LEVELS]):
            at[i, j] = int(level.price_tick); aq[i, j] = float(level.qty)
    mn = np.asarray([m.exchange_ns for m in mids], dtype="<i8")
    ms = np.asarray([m.best_bid_tick + m.best_ask_tick for m in mids], dtype="<i8")
    for x in (local_ns, local_ex, bt, bq, at, aq, bc, ac, mn, ms):
        x.setflags(write=False)
    return DualBookKernelResult(
        local_ns, local_ex, bt, bq, at, aq, bc, ac, mn, ms,
        int(local_decoder._state.bids.__len__() + local_decoder._state.asks.__len__()),
        int(exchange_decoder.active_level_count),
    )


def assert_dual_book_parity(events: np.ndarray, *, kernel=None) -> None:
    expected = _reference_surface(events)
    observed = run_dual_book_kernel(events, kernel=kernel)
    names = (
        "local_ns", "local_exchange_ns", "bid_ticks", "bid_qty", "ask_ticks", "ask_qty",
        "local_bid_level_count", "local_ask_level_count", "midpoint_exchange_ns", "midpoint_tick_sum",
    )
    for name in names:
        if not np.array_equal(getattr(expected, name), getattr(observed, name)):
            raise R27P4Error(f"parity:{name}")
    if expected.local_active_level_count != observed.local_active_level_count:
        raise R27P4Error("parity:local_active_level_count")
    if expected.exchange_active_level_count != observed.exchange_active_level_count:
        raise R27P4Error("parity:exchange_active_level_count")


def validate_r27p4_contract() -> None:
    r27p3.validate_r27p3_contract()
    r20.validate_r20_contract()
    if PARENT_R27P3_HEAD != "85e48a50853a5d222540ae06e7301941392b32d6":
        raise R27P4Error("parent")
    if ACCELERATOR_FAMILY != "NUMBA_JIT" or TOP_DEPTH_LEVELS != 5:
        raise R27P4Error("identity")
    required = (
        COMPILED_DUAL_BOOK_STATE_FOUNDATION, LOCAL_AND_EXCHANGE_BOOKS_IN_ONE_COMPILED_PASS,
        TOP5_LOCAL_BOOK_SURFACE_EXACT_PARITY_REQUIRED, EXCHANGE_MIDPOINT_EXACT_PARITY_REQUIRED,
        ACTIVE_LEVEL_COUNT_PARITY_REQUIRED, UNKNOWN_EVENT_FAIL_CLOSED, TIMESTAMP_REGRESSION_FAIL_CLOSED,
        CLEAR_AND_SNAPSHOT_SEMANTICS_FROZEN, TRADE_DOES_NOT_MUTATE_BOOK_FROZEN,
        IGNORED_EVENT_POLICY_FROZEN, SOURCE_ORDER_WITHIN_GROUP_FROZEN, FINAL_GROUP_FLUSH_REQUIRED,
        not FULL_CONTEXT_REPLACEMENT_AUTHORIZED, not REAL_HISTORICAL_BENCHMARK_AUTHORIZED,
        not FULL_JAN_JUL_RERUN_AUTHORIZED, not DURABLE_CONTEXT_WRITE_AUTHORIZED,
    )
    if not all(required):
        raise R27P4Error("required_guard")
    forbidden = (
        P2_ATTEMPT_CONSUMED, SIMULATOR_LANE_AUTHORIZED, ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED, MODEL_FIT_AUTHORIZED, PNL_AUTHORIZED,
        AUG_OPEN_AUTHORIZED, SEP_PLUS_OPEN_AUTHORIZED, NON_BTC_OPEN_AUTHORIZED,
    )
    if any(forbidden):
        raise R27P4Error("execution_surface_open")


__all__ = [
    "DualBookKernelResult", "assert_dual_book_parity", "build_dual_book_kernel",
    "run_dual_book_kernel", "validate_r27p4_contract",
]

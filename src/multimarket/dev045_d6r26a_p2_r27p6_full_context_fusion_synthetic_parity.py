from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1
from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b
from multimarket import dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9
from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
from multimarket import dev045_d6r26a_p2_r27p3_fused_full_context_kernel_architecture_freeze as r27p3
from multimarket import dev045_d6r26a_p2_r27p4_compiled_dual_book_state_kernel_preexecution as r27p4
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P6"
DESIGN_VERSION = "full-context-fusion-synthetic-parity-v1"
PARENT_R27P5_HEAD = "7bb6d72231200e429986a7ffa18bd958e9e4d38a"

ACCELERATOR_FAMILY = "NUMBA_JIT"
ONE_COMPILED_RAW_EVENT_PASS = True
PYTHON_RAW_EVENT_LOOP_FORBIDDEN = True
PYTHON_REFERENCE_DECODER_FOR_ACCELERATED_PATH_FORBIDDEN = True
COMPILED_BOOK_STATE_BOUND = True
COMPILED_FLOW_EXTRACTION_BOUND = True
COMPILED_ROLLING_FEATURE_KERNEL_BOUND = True
EXACT_R20_DAY_CONTEXT_PARITY_REQUIRED = True
FILE_BACKED_MIDPOINT_SURFACE_REQUIRED = True
RAW_EVENT_PASS_COUNT = 1

# This stage proves full synthetic parity only. Real historical benchmark and
# durable publication remain closed until a later successor.
SYNTHETIC_FULL_CONTEXT_PARITY_ONLY = True
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

CASE_COUNT = 8
TOP_DEPTH_LEVELS = 5


class R27P6Error(RuntimeError):
    pass


@dataclass(frozen=True)
class FusedRawSurface:
    book_local_ns: np.ndarray
    bid_ticks: np.ndarray
    bid_qty: np.ndarray
    ask_ticks: np.ndarray
    ask_qty: np.ndarray
    candidate_qty: np.ndarray
    flow_local_ns: np.ndarray
    flow_code: np.ndarray
    flow_qty: np.ndarray
    midpoint_exchange_ns: np.ndarray
    midpoint_tick_sum: np.ndarray
    source_exchange_observed_through_ns: int


def _load_numba():
    try:
        from numba import njit, types
        from numba.typed import Dict
    except Exception as exc:
        raise R27P6Error("numba_unavailable") from exc
    return njit, types, Dict


def build_fused_raw_kernel():
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
    distances = tuple(int(x) for x in p0.CANDIDATE_DISTANCE_TICKS)

    @njit(cache=False)
    def kind_supported(kind):
        for x in supported:
            if kind == x:
                return True
        return False

    @njit(cache=False)
    def kind_ignored(kind):
        for x in ignored:
            if kind == x:
                return True
        return False

    @njit(cache=False)
    def side_code(ev, required):
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
    def aligned_tick(px):
        if not math.isfinite(px) or px <= 0.0:
            return -1
        scaled = px / tick_size
        tick = int(math.floor(scaled + 0.5))
        if abs(scaled - tick) > 1e-8:
            return -1
        return tick

    @njit(cache=False)
    def qty_lot(qty):
        if not math.isfinite(qty) or qty < 0.0:
            return -1
        return int(math.floor(qty / lot_size + 0.5))

    @njit(cache=False)
    def clear_book(bids, asks, side, px):
        if side == 2:
            bids.clear(); asks.clear(); return 0
        book = bids if side == 1 else asks
        if not math.isfinite(px):
            book.clear(); return 0
        tick = aligned_tick(px)
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
    def valid_book(bids, asks):
        if len(bids) == 0 or len(asks) == 0:
            return False
        best_bid = -9223372036854775807
        best_ask = 9223372036854775807
        for key in bids.keys():
            if key > best_bid:
                best_bid = key
        for key in asks.keys():
            if key < best_ask:
                best_ask = key
        return best_bid < best_ask

    @njit(cache=False)
    def best_ticks(bids, asks):
        best_bid = -9223372036854775807
        best_ask = 9223372036854775807
        for key in bids.keys():
            if key > best_bid:
                best_bid = key
        for key in asks.keys():
            if key < best_ask:
                best_ask = key
        return best_bid, best_ask

    @njit(cache=False)
    def top5(book, descending, out_ticks, out_qty, row):
        for j in range(TOP_DEPTH_LEVELS):
            out_ticks[row, j] = 0
            out_qty[row, j] = 0.0
        for key, qty in book.items():
            if qty <= 0.0:
                continue
            insert = TOP_DEPTH_LEVELS
            for j in range(TOP_DEPTH_LEVELS):
                existing = out_ticks[row, j]
                if existing == 0 or (descending and key > existing) or ((not descending) and key < existing):
                    insert = j
                    break
            if insert < TOP_DEPTH_LEVELS:
                for j in range(TOP_DEPTH_LEVELS - 1, insert, -1):
                    out_ticks[row, j] = out_ticks[row, j - 1]
                    out_qty[row, j] = out_qty[row, j - 1]
                out_ticks[row, insert] = key
                out_qty[row, insert] = qty

    @njit(cache=False)
    def kernel(ev, exch_ts, local_ts, px, qty):
        n = ev.size
        book_ns = np.empty(n, dtype=np.int64)
        bt = np.empty((n, TOP_DEPTH_LEVELS), dtype=np.int64)
        bq = np.empty((n, TOP_DEPTH_LEVELS), dtype=np.float64)
        at = np.empty((n, TOP_DEPTH_LEVELS), dtype=np.int64)
        aq = np.empty((n, TOP_DEPTH_LEVELS), dtype=np.float64)
        candidate_qty = np.empty((n, CASE_COUNT), dtype=np.float64)

        flow_ns = np.empty(n, dtype=np.int64)
        flow_code = np.empty(n, dtype=np.int8)
        flow_qty = np.empty(n, dtype=np.float64)

        midpoint_ns = np.empty(n, dtype=np.int64)
        midpoint_sum = np.empty(n, dtype=np.int64)

        lb = Dict.empty(types.int64, types.float64)
        la = Dict.empty(types.int64, types.float64)
        eb = Dict.empty(types.int64, types.float64)
        ea = Dict.empty(types.int64, types.float64)

        book_count = 0
        flow_count = 0
        midpoint_count = 0
        current_local = -1
        current_exchange = -1
        local_changed = False
        exchange_changed = False
        last_local = -1
        last_exchange = -1
        observed_exchange = -1
        error = 0

        def flush_local():
            nonlocal book_count, local_changed
            if current_local >= 0 and local_changed and valid_book(lb, la):
                book_ns[book_count] = current_local
                top5(lb, True, bt, bq, book_count)
                top5(la, False, at, aq, book_count)
                best_bid, best_ask = best_ticks(lb, la)
                for j in range(4):
                    tick = best_bid - distances[j]
                    candidate_qty[book_count, j] = lb[tick] if tick in lb else 0.0
                for j in range(4):
                    tick = best_ask + distances[j]
                    candidate_qty[book_count, j + 4] = la[tick] if tick in la else 0.0
                book_count += 1
            local_changed = False

        def flush_exchange():
            nonlocal midpoint_count, exchange_changed
            if current_exchange >= 0 and exchange_changed and valid_book(eb, ea):
                best_bid, best_ask = best_ticks(eb, ea)
                midpoint_ns[midpoint_count] = current_exchange
                midpoint_sum[midpoint_count] = best_bid + best_ask
                midpoint_count += 1
            exchange_changed = False

        for i in range(n):
            e = int(ev[i])
            kind = e & event_mask
            ets_all = int(exch_ts[i])
            if ets_all < 0:
                error = 1; break
            if ets_all > observed_exchange:
                observed_exchange = ets_all
            if not kind_supported(kind):
                error = 2; break

            if (e & local_flag) == local_flag:
                lts = int(local_ts[i])
                ets = ets_all
                if lts < 0 or lts < ets:
                    error = 3; break
                if lts < last_local:
                    error = 4; break
                if current_local < 0:
                    current_local = lts
                elif lts != current_local:
                    flush_local()
                    current_local = lts
                last_local = lts

                if kind == depth or kind == clear or kind == snapshot:
                    side = side_code(e, kind != clear)
                    if side == 0:
                        error = 5; break
                    if kind == clear:
                        if clear_book(lb, la, side, float(px[i])) != 0:
                            error = 6; break
                    else:
                        tick = aligned_tick(float(px[i]))
                        q = float(qty[i])
                        qlot = qty_lot(q)
                        if tick < 0:
                            error = 6; break
                        if qlot < 0:
                            error = 7; break
                        book = lb if side == 1 else la
                        before = float(book[tick]) if tick in book else 0.0
                        after = 0.0
                        if qlot == 0:
                            if tick in book:
                                del book[tick]
                        else:
                            book[tick] = q
                            after = q
                        if kind == depth:
                            delta = after - before
                            if abs(delta) > 1e-15:
                                flow_ns[flow_count] = lts
                                if delta > 0.0:
                                    flow_code[flow_count] = r27p5.FLOW_ADD_BID if side == 1 else r27p5.FLOW_ADD_ASK
                                    flow_qty[flow_count] = delta
                                else:
                                    flow_code[flow_count] = r27p5.FLOW_CANCEL_BID if side == 1 else r27p5.FLOW_CANCEL_ASK
                                    flow_qty[flow_count] = -delta
                                flow_count += 1
                    local_changed = True
                elif kind == trade:
                    side = side_code(e, True)
                    q = float(qty[i])
                    if side == 0:
                        error = 8; break
                    if not math.isfinite(q) or q <= 0.0:
                        error = 9; break
                    flow_ns[flow_count] = lts
                    flow_code[flow_count] = r27p5.FLOW_TRADE_BUY if side == 1 else r27p5.FLOW_TRADE_SELL
                    flow_qty[flow_count] = q
                    flow_count += 1
                elif kind_ignored(kind):
                    pass

            if (e & exch_flag) == exch_flag:
                ets = ets_all
                if ets < last_exchange:
                    error = 10; break
                if current_exchange < 0:
                    current_exchange = ets
                elif ets != current_exchange:
                    flush_exchange()
                    current_exchange = ets
                last_exchange = ets

                if kind == depth or kind == clear or kind == snapshot:
                    side = side_code(e, kind != clear)
                    if side == 0:
                        error = 11; break
                    if kind == clear:
                        if clear_book(eb, ea, side, float(px[i])) != 0:
                            error = 12; break
                    else:
                        tick = aligned_tick(float(px[i]))
                        q = float(qty[i])
                        qlot = qty_lot(q)
                        if tick < 0:
                            error = 12; break
                        if qlot < 0:
                            error = 13; break
                        book = eb if side == 1 else ea
                        if qlot == 0:
                            if tick in book:
                                del book[tick]
                        else:
                            book[tick] = q
                    exchange_changed = True
                elif kind == trade or kind_ignored(kind):
                    pass

        if error == 0:
            flush_local()
            flush_exchange()

        return (
            book_ns[:book_count], bt[:book_count], bq[:book_count], at[:book_count], aq[:book_count],
            candidate_qty[:book_count], flow_ns[:flow_count], flow_code[:flow_count], flow_qty[:flow_count],
            midpoint_ns[:midpoint_count], midpoint_sum[:midpoint_count], observed_exchange, error,
        )

    return kernel


def run_fused_raw_surface(events: np.ndarray, *, kernel=None) -> FusedRawSurface:
    a = r9._validate_event_array(events)
    k = build_fused_raw_kernel() if kernel is None else kernel
    out = k(a["ev"], a["exch_ts"], a["local_ts"], a["px"], a["qty"])
    error = int(out[12])
    reasons = {
        1: "source_exchange_timestamp",
        2: "unknown_event_kind",
        3: "local_timestamp",
        4: "local_timestamp_regression",
        5: "local_side",
        6: "local_price",
        7: "local_qty",
        8: "trade_side",
        9: "trade_qty",
        10: "exchange_timestamp_regression",
        11: "exchange_side",
        12: "exchange_price",
        13: "exchange_qty",
    }
    if error:
        raise R27P6Error(reasons.get(error, f"kernel_error:{error}"))

    arrays = [np.asarray(x) for x in out[:11]]
    for array in arrays:
        array.setflags(write=False)

    return FusedRawSurface(
        book_local_ns=arrays[0],
        bid_ticks=arrays[1],
        bid_qty=arrays[2],
        ask_ticks=arrays[3],
        ask_qty=arrays[4],
        candidate_qty=arrays[5],
        flow_local_ns=arrays[6],
        flow_code=arrays[7],
        flow_qty=arrays[8],
        midpoint_exchange_ns=arrays[9],
        midpoint_tick_sum=arrays[10],
        source_exchange_observed_through_ns=int(out[11]),
    )


def _feature_surface(raw: FusedRawSurface) -> r27p5.CompactFeatureSurface:
    return r27p5.CompactFeatureSurface(
        book_local_ns=raw.book_local_ns,
        bid_ticks=raw.bid_ticks,
        bid_qty=raw.bid_qty,
        ask_ticks=raw.ask_ticks,
        ask_qty=raw.ask_qty,
        candidate_qty=raw.candidate_qty,
        flow_local_ns=raw.flow_local_ns,
        flow_code=raw.flow_code,
        flow_qty=raw.flow_qty,
    )


def build_fused_day_context(
    events: np.ndarray,
    *,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
    scratch_root: Path,
    midpoint_index_name: str = "exchange_midpoints.bin",
    raw_kernel=None,
    feature_kernel=None,
) -> r20.DayContextBuildResult:
    a = r19._validate_event_surface(events)
    bounds = r17.derive_feed_bounds(
        a,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
    )
    requested = np.asarray(r17.build_shared_decision_grid(bounds=bounds), dtype="<i8")
    if requested.size <= 0:
        raise R27P6Error("requested_decision_grid_empty")

    raw = run_fused_raw_surface(a, kernel=raw_kernel)
    compiled = r27p5.run_compiled_feature_kernel(
        _feature_surface(raw),
        requested,
        kernel=feature_kernel,
    )

    decisions = np.asarray(compiled.decision_local_ns, dtype="<i8")
    bids = np.asarray(compiled.best_bid_tick, dtype="<i8")
    asks = np.asarray(compiled.best_ask_tick, dtype="<i8")
    values = np.asarray(compiled.values, dtype=r17.FEATURE_CACHE_VALUE_DTYPE)
    for array in (decisions, bids, asks, values):
        array.setflags(write=False)

    cache = r18.DenseFeatureCache(
        decision_local_ns=decisions,
        best_bid_tick=bids,
        best_ask_tick=asks,
        values=values,
    )
    r18.validate_dense_feature_cache(cache)

    first_eligible_index = int(compiled.leading_preeligible_count)
    if first_eligible_index < 0 or first_eligible_index >= int(requested.size):
        raise R27P6Error("leading_preeligible_count")
    if cache.decision_count != int(requested.size) - first_eligible_index:
        raise R27P6Error("eligible_count")

    summary = r19.FeatureCacheBuildSummary(
        requested_decision_count=int(requested.size),
        leading_preeligible_count=first_eligible_index,
        eligible_decision_count=cache.decision_count,
        first_requested_local_ns=int(requested[0]),
        first_eligible_local_ns=int(cache.decision_local_ns[0]),
        last_eligible_local_ns=int(cache.decision_local_ns[-1]),
        raw_event_pass_count=1,
    )

    spool = r20._MidpointSpool(
        scratch_root=Path(scratch_root),
        index_name=midpoint_index_name,
    )
    try:
        for exchange_ns, tick_sum in zip(raw.midpoint_exchange_ns, raw.midpoint_tick_sum):
            ts = int(exchange_ns)
            total = int(tick_sum)
            if total <= 0:
                raise R27P6Error("midpoint_tick_sum")
            # MidObservation requires bid/ask ticks; only their sum is persisted
            # by R20. Split deterministically while preserving exact sum.
            bid = total // 2
            ask = total - bid
            if bid <= 0 or ask <= bid:
                # This split is only a transport helper into the frozen R20
                # spool; real midpoint validity was already established by the
                # compiled book state. For odd sums ask=bid+1; for even sums use
                # an adjacent pair preserving the sum.
                bid = (total - 1) // 2
                ask = total - bid
            midpoint = p1.MidObservation(
                exchange_ns=ts,
                best_bid_tick=bid,
                best_ask_tick=ask,
            )
            spool.append(midpoint)
        index = spool.finish(
            source_exchange_observed_through_ns=raw.source_exchange_observed_through_ns
        )
    except Exception:
        spool.abort()
        raise

    return r20.DayContextBuildResult(
        bounds=bounds,
        feature_cache=cache,
        feature_summary=summary,
        midpoint_index=index,
        raw_event_pass_count=1,
    )


def assert_full_context_synthetic_parity(
    events: np.ndarray,
    *,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
    reference_scratch_root: Path,
    candidate_scratch_root: Path,
) -> None:
    reference = r20.build_once_day_context(
        events,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
        scratch_root=Path(reference_scratch_root),
    )
    candidate = build_fused_day_context(
        events,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
        scratch_root=Path(candidate_scratch_root),
    )
    try:
        r27p0.assert_exact_context_parity(reference, candidate)
    finally:
        r20.close_midpoint_index(reference.midpoint_index)
        r20.close_midpoint_index(candidate.midpoint_index)


def validate_r27p6_contract() -> None:
    r27p3.validate_r27p3_contract()
    r27p4.validate_r27p4_contract()
    r27p5.validate_r27p5_contract()
    if PARENT_R27P5_HEAD != "7bb6d72231200e429986a7ffa18bd958e9e4d38a":
        raise R27P6Error("parent")
    if ACCELERATOR_FAMILY != "NUMBA_JIT":
        raise R27P6Error("accelerator_family")
    if RAW_EVENT_PASS_COUNT != 1:
        raise R27P6Error("raw_event_pass_count")
    required = (
        ONE_COMPILED_RAW_EVENT_PASS,
        PYTHON_RAW_EVENT_LOOP_FORBIDDEN,
        PYTHON_REFERENCE_DECODER_FOR_ACCELERATED_PATH_FORBIDDEN,
        COMPILED_BOOK_STATE_BOUND,
        COMPILED_FLOW_EXTRACTION_BOUND,
        COMPILED_ROLLING_FEATURE_KERNEL_BOUND,
        EXACT_R20_DAY_CONTEXT_PARITY_REQUIRED,
        FILE_BACKED_MIDPOINT_SURFACE_REQUIRED,
        SYNTHETIC_FULL_CONTEXT_PARITY_ONLY,
        not REAL_HISTORICAL_BENCHMARK_AUTHORIZED,
        not FULL_JAN_JUL_RERUN_AUTHORIZED,
        not DURABLE_CONTEXT_WRITE_AUTHORIZED,
    )
    if not all(required):
        raise R27P6Error("required_guard")
    forbidden = (
        P2_ATTEMPT_CONSUMED,
        SIMULATOR_LANE_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
    )
    if any(forbidden):
        raise R27P6Error("execution_surface_open")


__all__ = [
    "FusedRawSurface",
    "assert_full_context_synthetic_parity",
    "build_fused_day_context",
    "build_fused_raw_kernel",
    "run_fused_raw_surface",
    "validate_r27p6_contract",
]

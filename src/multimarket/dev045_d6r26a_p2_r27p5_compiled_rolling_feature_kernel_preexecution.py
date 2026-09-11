from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b
from multimarket import dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9
from multimarket import dev045_d6r26a_p2_r13_streaming_raw_decoder_preexecution as r13
from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r27p3_fused_full_context_kernel_architecture_freeze as r27p3
from multimarket import dev045_d6r26a_p2_r27p4_compiled_dual_book_state_kernel_preexecution as r27p4

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P5"
DESIGN_VERSION = "compiled-rolling-feature-kernel-preexecution-v1"
PARENT_R27P4_HEAD = "bc231aa8559eafb14eaacc49abfe81f07e6d9680"

ACCELERATOR_FAMILY = "NUMBA_JIT"
COMPILED_ROLLING_FEATURE_FOUNDATION = True
EXACT_25_FEATURE_PARITY_REQUIRED = True
EXACT_8_CASE_MATRIX_PARITY_REQUIRED = True
EXACT_TIMESTAMP_WINDOW_BOUNDARIES_REQUIRED = True
WINDOW_LEFT_OPEN_RIGHT_CLOSED = True
FEATURE_WARMUP_EXACT = True
CURRENT_L5_SUPPORT_EXACT = True
RECENT_BOOK_ASOF_250MS_EXACT = True
RECENT_BOOK_ASOF_1S_EXACT = True
ROLLING_SUM_ADD_SUBTRACT_ORDER_PRESERVED = True
CANDIDATE_VISIBLE_QTY_EXACT = True
FLOAT64_OUTPUT_REQUIRED = True

# R27P5 proves the compiled feature semantics over an exact compact reference
# surface. Fusion into the R27P4 raw-event state machine is a later successor.
RAW_EVENT_FUSION_COMPLETE = False
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

FEATURE_COUNT = 25
CASE_COUNT = 8
DISTANCES = (0, 1, 2, 4)

FLOW_TRADE_BUY = 1
FLOW_TRADE_SELL = 2
FLOW_ADD_BID = 3
FLOW_ADD_ASK = 4
FLOW_CANCEL_BID = 5
FLOW_CANCEL_ASK = 6


class R27P5Error(RuntimeError):
    pass


@dataclass(frozen=True)
class CompactFeatureSurface:
    book_local_ns: np.ndarray
    bid_ticks: np.ndarray
    bid_qty: np.ndarray
    ask_ticks: np.ndarray
    ask_qty: np.ndarray
    candidate_qty: np.ndarray
    flow_local_ns: np.ndarray
    flow_code: np.ndarray
    flow_qty: np.ndarray


@dataclass(frozen=True)
class CompiledFeatureResult:
    decision_local_ns: np.ndarray
    best_bid_tick: np.ndarray
    best_ask_tick: np.ndarray
    values: np.ndarray
    leading_preeligible_count: int


def _load_numba():
    try:
        from numba import njit
    except Exception as exc:
        raise R27P5Error("numba_unavailable") from exc
    return njit


def _flow_code(flow: r8b.FlowObservation) -> int:
    key = (flow.kind, flow.side)
    mapping = {
        ("TRADE", "BUY"): FLOW_TRADE_BUY,
        ("TRADE", "SELL"): FLOW_TRADE_SELL,
        ("ADD", "BID"): FLOW_ADD_BID,
        ("ADD", "ASK"): FLOW_ADD_ASK,
        ("CANCEL", "BID"): FLOW_CANCEL_BID,
        ("CANCEL", "ASK"): FLOW_CANCEL_ASK,
    }
    try:
        return int(mapping[key])
    except KeyError as exc:
        raise R27P5Error(f"flow_code:{key}") from exc


def build_compact_reference_surface(events: np.ndarray) -> CompactFeatureSurface:
    a = r9._validate_event_array(events)
    decoder = r13.LocalStreamingDecoder()
    books: list[r8b.BookObservation] = []
    flows: list[r8b.FlowObservation] = []

    for row in a:
        for group in decoder.feed(row):
            if group.books:
                books.append(group.books[-1])
            flows.extend(group.flows)
    for group in decoder.finish():
        if group.books:
            books.append(group.books[-1])
        flows.extend(group.flows)

    if not books:
        raise R27P5Error("book_surface_empty")

    n = len(books)
    book_ns = np.empty(n, dtype="<i8")
    bt = np.zeros((n, 5), dtype="<i8")
    bq = np.zeros((n, 5), dtype="<f8")
    at = np.zeros((n, 5), dtype="<i8")
    aq = np.zeros((n, 5), dtype="<f8")
    cq = np.zeros((n, CASE_COUNT), dtype="<f8")

    for i, book in enumerate(books):
        book_ns[i] = int(book.local_ns)
        for j, level in enumerate(book.bids[:5]):
            bt[i, j] = int(level.price_tick)
            bq[i, j] = float(level.qty)
        for j, level in enumerate(book.asks[:5]):
            at[i, j] = int(level.price_tick)
            aq[i, j] = float(level.qty)

        for case_index, (side, distance) in enumerate(r18.CANDIDATE_GRID):
            tick = (
                int(book.best_bid.price_tick) - int(distance)
                if side == "BID"
                else int(book.best_ask.price_tick) + int(distance)
            )
            levels = book.bids if side == "BID" else book.asks
            visible = 0.0
            for level in levels:
                if int(level.price_tick) == tick:
                    visible = float(level.qty)
                    break
            cq[i, case_index] = visible

    m = len(flows)
    flow_ns = np.empty(m, dtype="<i8")
    flow_code = np.empty(m, dtype=np.int8)
    flow_qty = np.empty(m, dtype="<f8")
    for i, flow in enumerate(flows):
        flow_ns[i] = int(flow.local_ns)
        flow_code[i] = _flow_code(flow)
        flow_qty[i] = float(flow.qty)

    for x in (book_ns, bt, bq, at, aq, cq, flow_ns, flow_code, flow_qty):
        x.setflags(write=False)

    return CompactFeatureSurface(
        book_local_ns=book_ns,
        bid_ticks=bt,
        bid_qty=bq,
        ask_ticks=at,
        ask_qty=aq,
        candidate_qty=cq,
        flow_local_ns=flow_ns,
        flow_code=flow_code,
        flow_qty=flow_qty,
    )


def build_feature_kernel():
    njit = _load_numba()
    tick_size = float(p0.TICK_SIZE)
    warmup_ns = 30_000_000_000
    case_count = CASE_COUNT
    feature_count = FEATURE_COUNT

    @njit(cache=False)
    def ratio(a, b):
        den = a + b
        if den <= 0.0:
            return 0.0
        return (a - b) / den

    @njit(cache=False)
    def asof_index(times, count, target):
        lo = 0
        hi = count
        while lo < hi:
            mid = (lo + hi) // 2
            if times[mid] <= target:
                lo = mid + 1
            else:
                hi = mid
        return lo - 1

    @njit(cache=False)
    def ofi_transition(bt, bq, at, aq, before, after):
        pb0 = bt[before, 0]
        pb1 = bt[after, 0]
        qb0 = bq[before, 0]
        qb1 = bq[after, 0]
        pa0 = at[before, 0]
        pa1 = at[after, 0]
        qa0 = aq[before, 0]
        qa1 = aq[after, 0]
        bid_component = (qb1 if pb1 >= pb0 else 0.0) - (qb0 if pb1 <= pb0 else 0.0)
        ask_component = -(qa1 if pa1 <= pa0 else 0.0) + (qa0 if pa1 >= pa0 else 0.0)
        return bid_component + ask_component

    @njit(cache=False)
    def kernel(book_ns, bt, bq, at, aq, candidate_qty, flow_ns, flow_code, flow_qty, requested):
        nbooks = book_ns.size
        nflows = flow_ns.size
        nreq = requested.size

        transition_ofi = np.zeros(nbooks, dtype=np.float64)
        transition_vol = np.zeros(nbooks, dtype=np.float64)

        out_dec = np.empty(nreq, dtype=np.int64)
        out_bid = np.empty(nreq, dtype=np.int64)
        out_ask = np.empty(nreq, dtype=np.int64)
        out_values = np.empty((nreq, case_count, feature_count), dtype=np.float64)

        book_ingest = 0
        flow_ingest = 0
        out_count = 0
        leading = 0
        first_eligible = False
        error = 0

        ofi1 = 0.0
        ofi5 = 0.0
        vol1 = 0.0
        vol5 = 0.0
        vol30 = 0.0
        ofi1_head = 1
        ofi5_head = 1
        vol1_head = 1
        vol5_head = 1
        vol30_head = 1

        tb1 = 0.0; ts1 = 0.0; tb5 = 0.0; ts5 = 0.0
        ab1 = 0.0; aa1 = 0.0; cb1 = 0.0; ca1 = 0.0
        tb1_head = 0; ts1_head = 0; tb5_head = 0; ts5_head = 0
        ab1_head = 0; aa1_head = 0; cb1_head = 0; ca1_head = 0

        for ri in range(nreq):
            decision = int(requested[ri])

            while book_ingest < nbooks and int(book_ns[book_ingest]) <= decision:
                if book_ingest > 0:
                    val = ofi_transition(bt, bq, at, aq, book_ingest - 1, book_ingest)
                    before_mid = 0.5 * float(bt[book_ingest - 1, 0] + at[book_ingest - 1, 0]) * tick_size
                    after_mid = 0.5 * float(bt[book_ingest, 0] + at[book_ingest, 0]) * tick_size
                    sq = math.log(after_mid / before_mid) ** 2
                    transition_ofi[book_ingest] = val
                    transition_vol[book_ingest] = sq
                    ofi1 += val; ofi5 += val
                    vol1 += sq; vol5 += sq; vol30 += sq
                book_ingest += 1

            while flow_ingest < nflows and int(flow_ns[flow_ingest]) <= decision:
                code = int(flow_code[flow_ingest])
                q = float(flow_qty[flow_ingest])
                if code == FLOW_TRADE_BUY:
                    tb1 += q; tb5 += q
                elif code == FLOW_TRADE_SELL:
                    ts1 += q; ts5 += q
                elif code == FLOW_ADD_BID:
                    ab1 += q
                elif code == FLOW_ADD_ASK:
                    aa1 += q
                elif code == FLOW_CANCEL_BID:
                    cb1 += q
                elif code == FLOW_CANCEL_ASK:
                    ca1 += q
                else:
                    error = 1
                    break
                flow_ingest += 1
            if error != 0:
                break

            if book_ingest <= 0:
                if first_eligible:
                    error = 2; break
                leading += 1
                continue

            current = book_ingest - 1
            if decision - int(book_ns[0]) < warmup_ns:
                if first_eligible:
                    error = 3; break
                leading += 1
                continue

            l5_ok = True
            for j in range(5):
                if int(bt[current, j]) <= 0 or int(at[current, j]) <= 0 or float(bq[current, j]) <= 0.0 or float(aq[current, j]) <= 0.0:
                    l5_ok = False
                    break
            if not l5_ok:
                if first_eligible:
                    error = 4; break
                leading += 1
                continue

            first_eligible = True

            cutoff1 = decision - 1_000_000_000
            cutoff5 = decision - 5_000_000_000
            cutoff30 = decision - 30_000_000_000

            while ofi1_head < book_ingest and int(book_ns[ofi1_head]) <= cutoff1:
                ofi1 -= transition_ofi[ofi1_head]; ofi1_head += 1
            while ofi5_head < book_ingest and int(book_ns[ofi5_head]) <= cutoff5:
                ofi5 -= transition_ofi[ofi5_head]; ofi5_head += 1
            while vol1_head < book_ingest and int(book_ns[vol1_head]) <= cutoff1:
                vol1 -= transition_vol[vol1_head]; vol1_head += 1
            while vol5_head < book_ingest and int(book_ns[vol5_head]) <= cutoff5:
                vol5 -= transition_vol[vol5_head]; vol5_head += 1
            while vol30_head < book_ingest and int(book_ns[vol30_head]) <= cutoff30:
                vol30 -= transition_vol[vol30_head]; vol30_head += 1

            while tb1_head < flow_ingest and int(flow_ns[tb1_head]) <= cutoff1:
                if int(flow_code[tb1_head]) == FLOW_TRADE_BUY: tb1 -= float(flow_qty[tb1_head])
                tb1_head += 1
            while ts1_head < flow_ingest and int(flow_ns[ts1_head]) <= cutoff1:
                if int(flow_code[ts1_head]) == FLOW_TRADE_SELL: ts1 -= float(flow_qty[ts1_head])
                ts1_head += 1
            while tb5_head < flow_ingest and int(flow_ns[tb5_head]) <= cutoff5:
                if int(flow_code[tb5_head]) == FLOW_TRADE_BUY: tb5 -= float(flow_qty[tb5_head])
                tb5_head += 1
            while ts5_head < flow_ingest and int(flow_ns[ts5_head]) <= cutoff5:
                if int(flow_code[ts5_head]) == FLOW_TRADE_SELL: ts5 -= float(flow_qty[ts5_head])
                ts5_head += 1
            while ab1_head < flow_ingest and int(flow_ns[ab1_head]) <= cutoff1:
                if int(flow_code[ab1_head]) == FLOW_ADD_BID: ab1 -= float(flow_qty[ab1_head])
                ab1_head += 1
            while aa1_head < flow_ingest and int(flow_ns[aa1_head]) <= cutoff1:
                if int(flow_code[aa1_head]) == FLOW_ADD_ASK: aa1 -= float(flow_qty[aa1_head])
                aa1_head += 1
            while cb1_head < flow_ingest and int(flow_ns[cb1_head]) <= cutoff1:
                if int(flow_code[cb1_head]) == FLOW_CANCEL_BID: cb1 -= float(flow_qty[cb1_head])
                cb1_head += 1
            while ca1_head < flow_ingest and int(flow_ns[ca1_head]) <= cutoff1:
                if int(flow_code[ca1_head]) == FLOW_CANCEL_ASK: ca1 -= float(flow_qty[ca1_head])
                ca1_head += 1

            prior250 = asof_index(book_ns, book_ingest, decision - 250_000_000)
            prior1s = asof_index(book_ns, book_ingest, decision - 1_000_000_000)
            if prior250 < 0 or prior1s < 0:
                error = 5; break

            best_bid_tick = int(bt[current, 0])
            best_ask_tick = int(at[current, 0])
            best_bid_qty = float(bq[current, 0])
            best_ask_qty = float(aq[current, 0])
            spread = best_ask_tick - best_bid_tick
            mid = 0.5 * float(best_bid_tick + best_ask_tick) * tick_size
            den_micro = best_bid_qty + best_ask_qty
            micro = ((float(best_bid_tick) * tick_size * best_ask_qty) + (float(best_ask_tick) * tick_size * best_bid_qty)) / den_micro

            vamp_num = 0.0
            vamp_den = 0.0
            bid5 = 0.0
            ask5 = 0.0
            for j in range(5):
                bqty = float(bq[current, j]); aqty = float(aq[current, j])
                vamp_num += float(bt[current, j]) * tick_size * aqty + float(at[current, j]) * tick_size * bqty
                vamp_den += bqty + aqty
                bid5 += bqty; ask5 += aqty
            vamp5 = vamp_num / vamp_den

            prior250_bid_qty = float(bq[prior250, 0])
            prior250_ask_qty = float(aq[prior250, 0])
            prior1_spread = int(at[prior1s, 0]) - int(bt[prior1s, 0])

            for case_index in range(case_count):
                is_bid = case_index < 4
                distance = DISTANCES[case_index if is_bid else case_index - 4]
                side_sign = 1.0 if is_bid else -1.0
                displayed = float(candidate_qty[current, case_index])
                own_best = best_bid_qty if is_bid else best_ask_qty
                opp_best = best_ask_qty if is_bid else best_bid_qty
                prior_same = prior250_bid_qty if is_bid else prior250_ask_qty
                prior_opp = prior250_ask_qty if is_bid else prior250_bid_qty

                out_values[out_count, case_index, 0] = float(spread)
                out_values[out_count, case_index, 1] = 10_000.0 * (micro - mid) / mid
                out_values[out_count, case_index, 2] = 10_000.0 * (micro - mid) / mid
                out_values[out_count, case_index, 3] = 10_000.0 * (vamp5 - mid) / mid
                out_values[out_count, case_index, 4] = ratio(best_bid_qty, best_ask_qty)
                out_values[out_count, case_index, 5] = ratio(bid5, ask5)
                out_values[out_count, case_index, 6] = ofi1
                out_values[out_count, case_index, 7] = ofi5
                out_values[out_count, case_index, 8] = ratio(tb1, ts1)
                out_values[out_count, case_index, 9] = ratio(tb5, ts5)
                out_values[out_count, case_index, 10] = ratio(ab1, aa1)
                out_values[out_count, case_index, 11] = ratio(ca1, cb1)
                out_values[out_count, case_index, 12] = ofi1 - ofi5 / 5.0
                out_values[out_count, case_index, 13] = own_best - prior_same
                out_values[out_count, case_index, 14] = opp_best - prior_opp
                out_values[out_count, case_index, 15] = float(spread - prior1_spread)
                out_values[out_count, case_index, 16] = 10_000.0 * math.sqrt(max(0.0, vol1))
                out_values[out_count, case_index, 17] = 10_000.0 * math.sqrt(max(0.0, vol5))
                out_values[out_count, case_index, 18] = 10_000.0 * math.sqrt(max(0.0, vol30))
                out_values[out_count, case_index, 19] = side_sign
                out_values[out_count, case_index, 20] = float(distance)
                out_values[out_count, case_index, 21] = displayed
                out_values[out_count, case_index, 22] = displayed
                out_values[out_count, case_index, 23] = own_best
                out_values[out_count, case_index, 24] = opp_best

            out_dec[out_count] = decision
            out_bid[out_count] = best_bid_tick
            out_ask[out_count] = best_ask_tick
            out_count += 1

        if error == 0 and not first_eligible:
            error = 6

        return out_dec[:out_count], out_bid[:out_count], out_ask[:out_count], out_values[:out_count], leading, error

    return kernel


def run_compiled_feature_kernel(
    surface: CompactFeatureSurface,
    requested_decisions: np.ndarray,
    *,
    kernel=None,
) -> CompiledFeatureResult:
    requested = np.asarray(requested_decisions, dtype="<i8")
    if requested.ndim != 1 or requested.size <= 0:
        raise R27P5Error("requested_decisions")
    if requested.size > 1 and bool(np.any(requested[1:] <= requested[:-1])):
        raise R27P5Error("requested_not_strict")

    k = build_feature_kernel() if kernel is None else kernel
    out = k(
        surface.book_local_ns,
        surface.bid_ticks,
        surface.bid_qty,
        surface.ask_ticks,
        surface.ask_qty,
        surface.candidate_qty,
        surface.flow_local_ns,
        surface.flow_code,
        surface.flow_qty,
        requested,
    )
    error = int(out[5])
    reasons = {
        1: "flow_code",
        2: "book_missing_after_eligibility",
        3: "warmup_failure_after_eligibility",
        4: "l5_failure_after_eligibility",
        5: "recent_book_asof_missing",
        6: "no_eligible_feature_decision",
    }
    if error:
        raise R27P5Error(reasons.get(error, f"kernel_error:{error}"))

    arrays = [np.asarray(x) for x in out[:4]]
    for x in arrays:
        x.setflags(write=False)
    return CompiledFeatureResult(
        decision_local_ns=arrays[0],
        best_bid_tick=arrays[1],
        best_ask_tick=arrays[2],
        values=arrays[3],
        leading_preeligible_count=int(out[4]),
    )


def build_synthetic_compiled_feature_result(
    events: np.ndarray,
    *,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
    kernel=None,
) -> CompiledFeatureResult:
    a = r19._validate_event_surface(events)
    bounds = r17.derive_feed_bounds(
        a,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
    )
    requested = np.asarray(r17.build_shared_decision_grid(bounds=bounds), dtype="<i8")
    surface = build_compact_reference_surface(a)
    return run_compiled_feature_kernel(surface, requested, kernel=kernel)


def assert_exact_feature_parity(
    events: np.ndarray,
    *,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
    kernel=None,
) -> None:
    reference = r19.build_once_day_dense_feature_cache(
        events,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
    )
    candidate = build_synthetic_compiled_feature_result(
        events,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
        kernel=kernel,
    )

    if candidate.leading_preeligible_count != reference.summary.leading_preeligible_count:
        raise R27P5Error("leading_preeligible_count")
    pairs = (
        ("decision_local_ns", reference.cache.decision_local_ns, candidate.decision_local_ns),
        ("best_bid_tick", reference.cache.best_bid_tick, candidate.best_bid_tick),
        ("best_ask_tick", reference.cache.best_ask_tick, candidate.best_ask_tick),
        ("feature_values", reference.cache.values, candidate.values),
    )
    for name, expected, observed in pairs:
        if expected.dtype != observed.dtype:
            raise R27P5Error(f"{name}_dtype")
        if expected.shape != observed.shape:
            raise R27P5Error(f"{name}_shape")
        if not np.array_equal(expected, observed):
            raise R27P5Error(f"{name}_values")


def validate_r27p5_contract() -> None:
    r27p3.validate_r27p3_contract()
    r27p4.validate_r27p4_contract()
    if PARENT_R27P4_HEAD != "bc231aa8559eafb14eaacc49abfe81f07e6d9680":
        raise R27P5Error("parent")
    if ACCELERATOR_FAMILY != "NUMBA_JIT":
        raise R27P5Error("accelerator_family")
    if FEATURE_COUNT != len(r8b.FEATURE_NAMES) or FEATURE_COUNT != 25:
        raise R27P5Error("feature_count")
    if CASE_COUNT != r18.CANDIDATE_GRID_CASE_COUNT or CASE_COUNT != 8:
        raise R27P5Error("case_count")
    if tuple(int(x) for x in p0.CANDIDATE_DISTANCE_TICKS) != DISTANCES:
        raise R27P5Error("distance_identity")

    required = (
        COMPILED_ROLLING_FEATURE_FOUNDATION,
        EXACT_25_FEATURE_PARITY_REQUIRED,
        EXACT_8_CASE_MATRIX_PARITY_REQUIRED,
        EXACT_TIMESTAMP_WINDOW_BOUNDARIES_REQUIRED,
        WINDOW_LEFT_OPEN_RIGHT_CLOSED,
        FEATURE_WARMUP_EXACT,
        CURRENT_L5_SUPPORT_EXACT,
        RECENT_BOOK_ASOF_250MS_EXACT,
        RECENT_BOOK_ASOF_1S_EXACT,
        ROLLING_SUM_ADD_SUBTRACT_ORDER_PRESERVED,
        CANDIDATE_VISIBLE_QTY_EXACT,
        FLOAT64_OUTPUT_REQUIRED,
        not RAW_EVENT_FUSION_COMPLETE,
        not FULL_CONTEXT_REPLACEMENT_AUTHORIZED,
        not REAL_HISTORICAL_BENCHMARK_AUTHORIZED,
        not FULL_JAN_JUL_RERUN_AUTHORIZED,
    )
    if not all(required):
        raise R27P5Error("required_guard")

    forbidden = (
        DURABLE_CONTEXT_WRITE_AUTHORIZED,
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
        raise R27P5Error("execution_surface_open")


__all__ = [
    "CompactFeatureSurface",
    "CompiledFeatureResult",
    "assert_exact_feature_parity",
    "build_compact_reference_surface",
    "build_feature_kernel",
    "build_synthetic_compiled_feature_result",
    "run_compiled_feature_kernel",
    "validate_r27p5_contract",
]

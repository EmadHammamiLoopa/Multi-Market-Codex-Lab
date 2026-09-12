from __future__ import annotations

from dataclasses import dataclass
import inspect
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p9_cpython313_float_sum_parity_amendment as r27p9
from multimarket import dev045_d6r26a_p2_r27p18_corrected_5m_speed_benchmark_preexecution as r27p18
from multimarket import dev045_d6r26a_p2_r27p20_file_backed_bounded_memory_synthetic_preflight as r27p20


EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P21"
DESIGN_VERSION = "file-backed-fused-raw-kernel-synthetic-parity-v1"
PARENT_R27P20_HEAD = "dd5b28ce3d9b7225645563364bce6eebb73aae11"

ARCHITECTURE = "R27P6_SEMANTICS_CALLER_PROVIDED_FILE_BACKED_RAW_OUTPUTS"
ONE_COMPILED_RAW_EVENT_PASS = True
RAW_EVENT_PASS_COUNT = 1
CALLER_PROVIDED_OUTPUT_BUFFERS = True
RAW_BUFFER_COUNT = len(r27p20.RAW_BUFFER_SPECS)
BYTES_PER_EVENT = r27p20.EXPECTED_BYTES_PER_EVENT
ANONYMOUS_FULL_N_RAW_OUTPUT_ALLOCATION = False
R27P6_RAW_SEMANTICS_REWRITE_COMPLETE = True
EXACT_RAW_BYTE_PARITY_REQUIRED = True
EXACT_CORRECTED_25_FEATURE_CONTEXT_PARITY_REQUIRED = True
EXACT_MIDPOINT_BYTES_REQUIRED = True
R27P9_L5_AMENDMENT_REQUIRED = True
R27P16_R10_VOLATILITY_AMENDMENT_REQUIRED = True

SYNTHETIC_ONLY = True
REAL_HISTORICAL_OPEN_AUTHORIZED = False
SOURCE_REHASH_AUTHORIZED = False
DURABLE_CONTEXT_WRITE_AUTHORIZED = False
SIMULATOR_LANE_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
FULL_JAN_JUL_RERUN_AUTHORIZED = False
P2_ATTEMPT_CONSUMED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED = False
FULL_DAY_BOUNDED_MEMORY_PROVEN = False
CANONICAL_EXECUTION_READY = False
READINESS_BLOCKER = "FULL_DAY_RSS_BOUND_NOT_YET_PROVEN"

CASE_COUNT = r27p6.CASE_COUNT
TOP_DEPTH_LEVELS = r27p6.TOP_DEPTH_LEVELS


class R27P21Error(RuntimeError):
    pass


@dataclass
class FileBackedRawRun:
    buffers: dict[str, np.memmap]
    book_count: int
    flow_count: int
    midpoint_count: int
    observed_exchange: int
    error: int

    def kernel_tuple(self):
        b = self.buffers
        return (
            b["book_local_ns"][: self.book_count],
            b["bid_ticks"][: self.book_count],
            b["bid_qty"][: self.book_count],
            b["ask_ticks"][: self.book_count],
            b["ask_qty"][: self.book_count],
            b["candidate_qty"][: self.book_count],
            b["flow_local_ns"][: self.flow_count],
            b["flow_code"][: self.flow_count],
            b["flow_qty"][: self.flow_count],
            b["midpoint_exchange_ns"][: self.midpoint_count],
            b["midpoint_tick_sum"][: self.midpoint_count],
            int(self.observed_exchange),
            int(self.error),
        )


@dataclass(frozen=True)
class SyntheticParityResult:
    raw_buffer_count: int
    raw_event_pass_count: int
    raw_byte_parity: bool
    corrected_context_parity: bool
    midpoint_byte_parity: bool
    reference_digest: r27p0.ContextDigest
    candidate_digest: r27p0.ContextDigest
    l5_changed_cells: int
    volatility_changed_cells: int


def _load_numba():
    try:
        from numba import njit, types
        from numba.typed import Dict
    except Exception as exc:
        raise R27P21Error("numba_unavailable") from exc
    return njit, types, Dict


def build_file_backed_raw_kernel():
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
            bids.clear()
            asks.clear()
            return 0
        book = bids if side == 1 else asks
        if not math.isfinite(px):
            book.clear()
            return 0
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
        for key, value in book.items():
            if value <= 0.0:
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
                out_qty[row, insert] = value

    @njit(cache=False)
    def kernel(
        ev,
        exch_ts,
        local_ts,
        px,
        qty,
        book_ns,
        bt,
        bq,
        at,
        aq,
        candidate_qty,
        flow_ns,
        flow_code,
        flow_qty,
        midpoint_ns,
        midpoint_sum,
    ):
        n = ev.size

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
                error = 1
                break
            if ets_all > observed_exchange:
                observed_exchange = ets_all
            if not kind_supported(kind):
                error = 2
                break

            if (e & local_flag) == local_flag:
                lts = int(local_ts[i])
                ets = ets_all
                if lts < 0 or lts < ets:
                    error = 3
                    break
                if lts < last_local:
                    error = 4
                    break
                if current_local < 0:
                    current_local = lts
                elif lts != current_local:
                    flush_local()
                    current_local = lts
                last_local = lts

                if kind == depth or kind == clear or kind == snapshot:
                    side = side_code(e, kind != clear)
                    if side == 0:
                        error = 5
                        break
                    if kind == clear:
                        if clear_book(lb, la, side, float(px[i])) != 0:
                            error = 6
                            break
                    else:
                        tick = aligned_tick(float(px[i]))
                        q = float(qty[i])
                        qlot = qty_lot(q)
                        if tick < 0:
                            error = 6
                            break
                        if qlot < 0:
                            error = 7
                            break
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
                        error = 8
                        break
                    if not math.isfinite(q) or q <= 0.0:
                        error = 9
                        break
                    flow_ns[flow_count] = lts
                    flow_code[flow_count] = r27p5.FLOW_TRADE_BUY if side == 1 else r27p5.FLOW_TRADE_SELL
                    flow_qty[flow_count] = q
                    flow_count += 1
                elif kind_ignored(kind):
                    pass

            if (e & exch_flag) == exch_flag:
                ets = ets_all
                if ets < last_exchange:
                    error = 10
                    break
                if current_exchange < 0:
                    current_exchange = ets
                elif ets != current_exchange:
                    flush_exchange()
                    current_exchange = ets
                last_exchange = ets

                if kind == depth or kind == clear or kind == snapshot:
                    side = side_code(e, kind != clear)
                    if side == 0:
                        error = 11
                        break
                    if kind == clear:
                        if clear_book(eb, ea, side, float(px[i])) != 0:
                            error = 12
                            break
                    else:
                        tick = aligned_tick(float(px[i]))
                        q = float(qty[i])
                        qlot = qty_lot(q)
                        if tick < 0:
                            error = 12
                            break
                        if qlot < 0:
                            error = 13
                            break
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

        return book_count, flow_count, midpoint_count, observed_exchange, error

    return kernel


def _ordered_buffers(buffers: dict[str, np.ndarray]):
    return tuple(buffers[spec.name] for spec in r27p20.RAW_BUFFER_SPECS)


def _validate_buffer_contract(buffers: dict[str, np.ndarray], rows: int) -> None:
    expected_names = tuple(spec.name for spec in r27p20.RAW_BUFFER_SPECS)
    if tuple(buffers) != expected_names:
        raise R27P21Error("buffer_names")
    for spec in r27p20.RAW_BUFFER_SPECS:
        array = buffers[spec.name]
        if array.dtype != np.dtype(spec.dtype):
            raise R27P21Error(f"buffer_dtype:{spec.name}")
        if array.shape != (int(rows),) + tuple(spec.trailing_shape):
            raise R27P21Error(f"buffer_shape:{spec.name}")


def _run_target_kernel_from_columns(
    ev,
    exch_ts,
    local_ts,
    px,
    qty,
    *,
    root: Path,
    kernel=None,
) -> FileBackedRawRun:
    n = int(ev.size)
    if n <= 0:
        raise R27P21Error("rows")
    buffers = r27p20.allocate_file_backed_buffers(Path(root), n)
    try:
        _validate_buffer_contract(buffers, n)
        k = build_file_backed_raw_kernel() if kernel is None else kernel
        book_count, flow_count, midpoint_count, observed_exchange, error = k(
            ev,
            exch_ts,
            local_ts,
            px,
            qty,
            *_ordered_buffers(buffers),
        )
        counts = (int(book_count), int(flow_count), int(midpoint_count))
        if any(value < 0 or value > n for value in counts):
            raise R27P21Error("count_bounds")
        return FileBackedRawRun(
            buffers=buffers,
            book_count=counts[0],
            flow_count=counts[1],
            midpoint_count=counts[2],
            observed_exchange=int(observed_exchange),
            error=int(error),
        )
    except Exception:
        r27p20.close_file_backed_buffers(buffers)
        raise


def make_r27p6_signature_adapter(root: Path, *, kernel=None):
    target_kernel = build_file_backed_raw_kernel() if kernel is None else kernel
    holder: list[FileBackedRawRun] = []

    def adapter(ev, exch_ts, local_ts, px, qty):
        if holder:
            raise R27P21Error("adapter_reused")
        run = _run_target_kernel_from_columns(
            ev,
            exch_ts,
            local_ts,
            px,
            qty,
            root=Path(root),
            kernel=target_kernel,
        )
        holder.append(run)
        return run.kernel_tuple()

    return adapter, holder


def close_adapter_runs(holder: list[FileBackedRawRun]) -> None:
    while holder:
        run = holder.pop()
        r27p20.close_file_backed_buffers(run.buffers)


def _assert_raw_tuple_exact(reference, candidate) -> None:
    if int(reference[11]) != int(candidate[11]):
        raise R27P21Error("observed_exchange")
    if int(reference[12]) != int(candidate[12]):
        raise R27P21Error("error_code")
    for index, spec in enumerate(r27p20.RAW_BUFFER_SPECS):
        a = np.asarray(reference[index])
        b = np.asarray(candidate[index])
        if a.dtype != b.dtype or a.dtype != np.dtype(spec.dtype):
            raise R27P21Error(f"raw_dtype:{spec.name}")
        if a.shape != b.shape:
            raise R27P21Error(f"raw_shape:{spec.name}")
        if a.tobytes(order="C") != b.tobytes(order="C"):
            raise R27P21Error(f"raw_bytes:{spec.name}")


def run_synthetic_raw_parity_probe() -> None:
    validate_r27p21_contract()
    fixture = r20.make_synthetic_dual_context_fixture()
    a = r9._validate_event_array(fixture)
    reference_kernel = r27p6.build_fused_raw_kernel()
    target_kernel = build_file_backed_raw_kernel()
    reference = reference_kernel(a["ev"], a["exch_ts"], a["local_ts"], a["px"], a["qty"])
    with TemporaryDirectory(prefix="dev045_r27p21_raw_") as root:
        run = _run_target_kernel_from_columns(
            a["ev"],
            a["exch_ts"],
            a["local_ts"],
            a["px"],
            a["qty"],
            root=Path(root) / "buffers",
            kernel=target_kernel,
        )
        try:
            candidate = run.kernel_tuple()
            _assert_raw_tuple_exact(reference, candidate)
            if run.book_count != int(np.asarray(reference[0]).shape[0]):
                raise R27P21Error("book_count")
            if run.flow_count != int(np.asarray(reference[6]).shape[0]):
                raise R27P21Error("flow_count")
            if run.midpoint_count != int(np.asarray(reference[9]).shape[0]):
                raise R27P21Error("midpoint_count")
        finally:
            r27p20.close_file_backed_buffers(run.buffers)


def run_synthetic_corrected_context_parity_probe() -> SyntheticParityResult:
    validate_r27p21_contract()
    fixture = r20.make_synthetic_dual_context_fixture()
    reference_raw_kernel = r27p6.build_fused_raw_kernel()
    target_raw_kernel = build_file_backed_raw_kernel()
    base_feature_kernel = r27p5.build_feature_kernel()
    l5_amendment_kernel = r27p9.build_l5_obi_amendment_kernel()

    reference = None
    candidate = None
    holder: list[FileBackedRawRun] = []
    with TemporaryDirectory(prefix="dev045_r27p21_context_") as root:
        root_path = Path(root)
        adapter, holder = make_r27p6_signature_adapter(
            root_path / "candidate_raw_buffers",
            kernel=target_raw_kernel,
        )
        try:
            reference, ref_l5, ref_vol = r27p18.build_corrected_fused_day_context(
                fixture,
                nominal_day_start_local_ns=0,
                nominal_day_end_exclusive_local_ns=100_000_000_000,
                scratch_root=root_path / "reference_context",
                raw_kernel=reference_raw_kernel,
                base_feature_kernel=base_feature_kernel,
                l5_amendment_kernel=l5_amendment_kernel,
            )
            candidate, cand_l5, cand_vol = r27p18.build_corrected_fused_day_context(
                fixture,
                nominal_day_start_local_ns=0,
                nominal_day_end_exclusive_local_ns=100_000_000_000,
                scratch_root=root_path / "candidate_context",
                raw_kernel=adapter,
                base_feature_kernel=base_feature_kernel,
                l5_amendment_kernel=l5_amendment_kernel,
            )
            r27p0.assert_exact_context_parity(reference, candidate)
            reference_digest = r27p0.digest_day_context(reference)
            candidate_digest = r27p0.digest_day_context(candidate)
            if reference_digest != candidate_digest:
                raise R27P21Error("context_digest")
            midpoint_byte_parity = bool(
                reference.midpoint_index.sha256 == candidate.midpoint_index.sha256
                and reference.midpoint_index.bytes == candidate.midpoint_index.bytes
            )
            if not midpoint_byte_parity:
                raise R27P21Error("midpoint_bytes")
            if ref_l5 != cand_l5:
                raise R27P21Error("l5_changed_cells")
            if ref_vol != cand_vol:
                raise R27P21Error("volatility_changed_cells")
            if reference.raw_event_pass_count != 1 or candidate.raw_event_pass_count != 1:
                raise R27P21Error("raw_event_pass_count")
            return SyntheticParityResult(
                raw_buffer_count=RAW_BUFFER_COUNT,
                raw_event_pass_count=1,
                raw_byte_parity=True,
                corrected_context_parity=True,
                midpoint_byte_parity=True,
                reference_digest=reference_digest,
                candidate_digest=candidate_digest,
                l5_changed_cells=int(cand_l5),
                volatility_changed_cells=int(cand_vol),
            )
        finally:
            if reference is not None and not reference.midpoint_index.closed:
                r20.close_midpoint_index(reference.midpoint_index)
            if candidate is not None and not candidate.midpoint_index.closed:
                r20.close_midpoint_index(candidate.midpoint_index)
            close_adapter_runs(holder)


def validate_r27p21_contract() -> None:
    r27p20.validate_r27p20_contract()
    r27p18.validate_r27p18_contract()
    if PARENT_R27P20_HEAD != "dd5b28ce3d9b7225645563364bce6eebb73aae11":
        raise R27P21Error("parent")
    if RAW_BUFFER_COUNT != 11 or BYTES_PER_EVENT != 265:
        raise R27P21Error("raw_capacity_identity")
    if RAW_EVENT_PASS_COUNT != 1:
        raise R27P21Error("raw_event_pass_count")
    source = inspect.getsource(build_file_backed_raw_kernel)
    if "np.empty(" in source:
        raise R27P21Error("anonymous_full_n_raw_allocation")

    required = (
        ONE_COMPILED_RAW_EVENT_PASS,
        CALLER_PROVIDED_OUTPUT_BUFFERS,
        not ANONYMOUS_FULL_N_RAW_OUTPUT_ALLOCATION,
        R27P6_RAW_SEMANTICS_REWRITE_COMPLETE,
        EXACT_RAW_BYTE_PARITY_REQUIRED,
        EXACT_CORRECTED_25_FEATURE_CONTEXT_PARITY_REQUIRED,
        EXACT_MIDPOINT_BYTES_REQUIRED,
        R27P9_L5_AMENDMENT_REQUIRED,
        R27P16_R10_VOLATILITY_AMENDMENT_REQUIRED,
        SYNTHETIC_ONLY,
        not FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not CANONICAL_EXECUTION_READY,
    )
    if not all(required):
        raise R27P21Error("required_guard")

    forbidden = (
        REAL_HISTORICAL_OPEN_AUTHORIZED,
        SOURCE_REHASH_AUTHORIZED,
        DURABLE_CONTEXT_WRITE_AUTHORIZED,
        SIMULATOR_LANE_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        FULL_JAN_JUL_RERUN_AUTHORIZED,
        P2_ATTEMPT_CONSUMED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED,
    )
    if any(forbidden):
        raise R27P21Error("execution_surface_open")
    if READINESS_BLOCKER != "FULL_DAY_RSS_BOUND_NOT_YET_PROVEN":
        raise R27P21Error("readiness_blocker")


__all__ = [
    "build_file_backed_raw_kernel",
    "close_adapter_runs",
    "make_r27p6_signature_adapter",
    "run_synthetic_corrected_context_parity_probe",
    "run_synthetic_raw_parity_probe",
    "validate_r27p21_contract",
]

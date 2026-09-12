from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p21_file_backed_fused_raw_kernel_synthetic_parity as r27p21
from multimarket import dev045_d6r26a_p2_r27p28_windowed_file_backed_synthetic_preflight as r27p28


EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P29"
DESIGN_VERSION = "stateful-windowed-raw-kernel-synthetic-parity-v1"
PARENT_R27P28_HEAD = "0792fd992870081a9880a37aa6f5a0e05ffe41f3"
PARENT_R27P28_CI_RUN = 34715145539
PARENT_R27P28_CI_JOB = 103610947812
PARENT_R27P28_CI_CONCLUSION = "success"

ARCHITECTURE = "STATEFUL_INPUT_CHUNKS_INDEPENDENT_BOUNDED_OUTPUT_WINDOWS"
STATEFUL_BOOKS_CARRIED_ACROSS_CHUNKS = True
PENDING_TIMESTAMP_STATE_CARRIED_ACROSS_CHUNKS = True
NO_SYNTHETIC_FLUSH_AT_CHUNK_BOUNDARY = True
FINAL_FLUSH_ONLY_ON_FINAL_CHUNK = True
INDEPENDENT_BOOK_FLOW_MIDPOINT_OUTPUT_OFFSETS = True
BOUNDED_OUTPUT_MAPPING_REQUIRED = True
FULL_FILE_OUTPUT_MAPPING_FOR_TARGET_ARCHITECTURE = False
EXACT_RAW_BYTE_PARITY_REQUIRED = True
EXACT_COUNTS_REQUIRED = True
EXACT_ERROR_CODE_REQUIRED = True
EXACT_OBSERVED_EXCHANGE_REQUIRED = True
ONE_LOGICAL_EVENT_PASS_REQUIRED = True
RAW_BUFFER_COUNT = r27p28.RAW_BUFFER_COUNT
BYTES_PER_EVENT = r27p28.BYTES_PER_EVENT
DEFAULT_INPUT_CHUNK_ROWS = r27p28.DEFAULT_WINDOW_ROWS
BOOK_EXTRA_FINAL_SLOT = 1
MIDPOINT_EXTRA_FINAL_SLOT = 1
FLOW_EXTRA_FINAL_SLOT = 0

STATEFUL_RAW_KERNEL_WINDOWING_COMPLETE = True
FULL_CORRECTED_CONTEXT_WINDOWING_COMPLETE = False
FULL_DAY_BOUNDED_MEMORY_PROVEN = False
GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN = False
CANONICAL_EXECUTION_READY = False
READINESS_BLOCKER = "WINDOWED_RAW_PARITY_NOT_YET_FROZEN_AND_DOWNSTREAM_CONTEXT_NOT_YET_WINDOWED"

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

BOOK_NAMES = (
    "book_local_ns",
    "bid_ticks",
    "bid_qty",
    "ask_ticks",
    "ask_qty",
    "candidate_qty",
)
FLOW_NAMES = (
    "flow_local_ns",
    "flow_code",
    "flow_qty",
)
MIDPOINT_NAMES = (
    "midpoint_exchange_ns",
    "midpoint_tick_sum",
)


class R27P29Error(RuntimeError):
    pass


@dataclass(frozen=True)
class StatefulRawRun:
    paths: dict[str, Path]
    rows: int
    input_chunk_rows: int
    input_chunk_count: int
    book_count: int
    flow_count: int
    midpoint_count: int
    observed_exchange: int
    error: int
    max_active_output_mapped_bytes: int


@dataclass(frozen=True)
class StatefulParityCase:
    input_chunk_rows: int
    input_chunk_count: int
    book_count: int
    flow_count: int
    midpoint_count: int
    observed_exchange: int
    error: int
    max_active_output_mapped_bytes: int
    exact_raw_bytes: bool


@dataclass(frozen=True)
class StatefulParityResult:
    rows: int
    raw_buffer_count: int
    bytes_per_event: int
    cases: tuple[StatefulParityCase, ...]


def _spec_by_name(name: str):
    for spec in r27p20_specs():
        if spec.name == name:
            return spec
    raise R27P29Error(f"unknown_spec:{name}")


def r27p20_specs():
    return r27p28.r27p20.RAW_BUFFER_SPECS


def _row_bytes(spec) -> int:
    trailing = int(np.prod(spec.trailing_shape or (1,), dtype=np.int64))
    return int(np.dtype(spec.dtype).itemsize) * trailing


def _shape(rows: int, spec) -> tuple[int, ...]:
    return (int(rows),) + tuple(spec.trailing_shape)


def _map_named_window(
    paths: dict[str, Path],
    names: tuple[str, ...],
    *,
    row_start: int,
    row_count: int,
) -> dict[str, np.memmap]:
    start = int(row_start)
    count = int(row_count)
    if start < 0 or count <= 0:
        raise R27P29Error("window_bounds")
    mapped: dict[str, np.memmap] = {}
    try:
        for name in names:
            spec = _spec_by_name(name)
            path = Path(paths[name])
            row_bytes = _row_bytes(spec)
            required_end = (start + count) * row_bytes
            if required_end > path.stat().st_size:
                raise R27P29Error(f"window_exceeds_file:{name}")
            mapped[name] = np.memmap(
                path,
                mode="r+",
                dtype=np.dtype(spec.dtype),
                offset=start * row_bytes,
                shape=_shape(count, spec),
            )
        return mapped
    except Exception:
        _close_named_window(mapped)
        raise


def _close_named_window(buffers: dict[str, np.memmap]) -> None:
    for array in buffers.values():
        array.flush()
        mm = getattr(array, "_mmap", None)
        if mm is not None:
            mm.close()


def _group_bytes(names: tuple[str, ...], rows: int) -> int:
    count = int(rows)
    return sum(_row_bytes(_spec_by_name(name)) * count for name in names)


def _make_books():
    _, types, Dict = r27p21._load_numba()
    return (
        Dict.empty(types.int64, types.float64),
        Dict.empty(types.int64, types.float64),
        Dict.empty(types.int64, types.float64),
        Dict.empty(types.int64, types.float64),
    )


def build_stateful_windowed_raw_kernel():
    njit, _, _ = r27p21._load_numba()

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
    top_depth_levels = int(r27p21.TOP_DEPTH_LEVELS)

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
        for j in range(top_depth_levels):
            out_ticks[row, j] = 0
            out_qty[row, j] = 0.0
        for key, value in book.items():
            if value <= 0.0:
                continue
            insert = top_depth_levels
            for j in range(top_depth_levels):
                existing = out_ticks[row, j]
                if existing == 0 or (descending and key > existing) or ((not descending) and key < existing):
                    insert = j
                    break
            if insert < top_depth_levels:
                for j in range(top_depth_levels - 1, insert, -1):
                    out_ticks[row, j] = out_ticks[row, j - 1]
                    out_qty[row, j] = out_qty[row, j - 1]
                out_ticks[row, insert] = key
                out_qty[row, insert] = value

    @njit(cache=False)
    def emit_local(lb, la, current_local, book_ns, bt, bq, at, aq, candidate_qty, row):
        book_ns[row] = current_local
        top5(lb, True, bt, bq, row)
        top5(la, False, at, aq, row)
        best_bid, best_ask = best_ticks(lb, la)
        for j in range(4):
            tick = best_bid - distances[j]
            candidate_qty[row, j] = lb[tick] if tick in lb else 0.0
        for j in range(4):
            tick = best_ask + distances[j]
            candidate_qty[row, j + 4] = la[tick] if tick in la else 0.0

    @njit(cache=False)
    def emit_midpoint(eb, ea, current_exchange, midpoint_ns, midpoint_sum, row):
        best_bid, best_ask = best_ticks(eb, ea)
        midpoint_ns[row] = current_exchange
        midpoint_sum[row] = best_bid + best_ask

    @njit(cache=False)
    def kernel(
        ev,
        exch_ts,
        local_ts,
        px,
        qty,
        final_chunk,
        lb,
        la,
        eb,
        ea,
        current_local,
        current_exchange,
        local_changed,
        exchange_changed,
        last_local,
        last_exchange,
        observed_exchange,
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
        book_count = 0
        flow_count = 0
        midpoint_count = 0
        error = 0
        n = ev.size

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
                    if current_local >= 0 and local_changed and valid_book(lb, la):
                        if book_count >= book_ns.size:
                            error = 101
                            break
                        emit_local(lb, la, current_local, book_ns, bt, bq, at, aq, candidate_qty, book_count)
                        book_count += 1
                    local_changed = False
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
                                if flow_count >= flow_ns.size:
                                    error = 102
                                    break
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
                    if flow_count >= flow_ns.size:
                        error = 102
                        break
                    flow_ns[flow_count] = lts
                    flow_code[flow_count] = r27p5.FLOW_TRADE_BUY if side == 1 else r27p5.FLOW_TRADE_SELL
                    flow_qty[flow_count] = q
                    flow_count += 1
                elif kind_ignored(kind):
                    pass

            if error != 0:
                break

            if (e & exch_flag) == exch_flag:
                ets = ets_all
                if ets < last_exchange:
                    error = 10
                    break
                if current_exchange < 0:
                    current_exchange = ets
                elif ets != current_exchange:
                    if current_exchange >= 0 and exchange_changed and valid_book(eb, ea):
                        if midpoint_count >= midpoint_ns.size:
                            error = 103
                            break
                        emit_midpoint(eb, ea, current_exchange, midpoint_ns, midpoint_sum, midpoint_count)
                        midpoint_count += 1
                    exchange_changed = False
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

        if error == 0 and final_chunk:
            if current_local >= 0 and local_changed and valid_book(lb, la):
                if book_count >= book_ns.size:
                    error = 101
                else:
                    emit_local(lb, la, current_local, book_ns, bt, bq, at, aq, candidate_qty, book_count)
                    book_count += 1
                    local_changed = False
            else:
                local_changed = False

            if error == 0:
                if current_exchange >= 0 and exchange_changed and valid_book(eb, ea):
                    if midpoint_count >= midpoint_ns.size:
                        error = 103
                    else:
                        emit_midpoint(eb, ea, current_exchange, midpoint_ns, midpoint_sum, midpoint_count)
                        midpoint_count += 1
                        exchange_changed = False
                else:
                    exchange_changed = False

        return (
            book_count,
            flow_count,
            midpoint_count,
            current_local,
            current_exchange,
            local_changed,
            exchange_changed,
            last_local,
            last_exchange,
            observed_exchange,
            error,
        )

    return kernel


def _map_output_groups(
    paths: dict[str, Path],
    *,
    rows: int,
    chunk_count: int,
    final_chunk: bool,
    book_start: int,
    flow_start: int,
    midpoint_start: int,
):
    n = int(rows)
    m = int(chunk_count)
    if n <= 0 or m <= 0:
        raise R27P29Error("mapping_bounds")

    book_remaining = n - int(book_start)
    flow_remaining = n - int(flow_start)
    midpoint_remaining = n - int(midpoint_start)
    if min(book_remaining, flow_remaining, midpoint_remaining) <= 0:
        raise R27P29Error("output_capacity_exhausted_before_input")

    book_need = m + (BOOK_EXTRA_FINAL_SLOT if final_chunk else 0)
    flow_need = m + (FLOW_EXTRA_FINAL_SLOT if final_chunk else 0)
    midpoint_need = m + (MIDPOINT_EXTRA_FINAL_SLOT if final_chunk else 0)

    book_cap = min(book_remaining, max(1, book_need))
    flow_cap = min(flow_remaining, max(1, flow_need))
    midpoint_cap = min(midpoint_remaining, max(1, midpoint_need))

    book = _map_named_window(paths, BOOK_NAMES, row_start=book_start, row_count=book_cap)
    try:
        flow = _map_named_window(paths, FLOW_NAMES, row_start=flow_start, row_count=flow_cap)
    except Exception:
        _close_named_window(book)
        raise
    try:
        midpoint = _map_named_window(paths, MIDPOINT_NAMES, row_start=midpoint_start, row_count=midpoint_cap)
    except Exception:
        _close_named_window(flow)
        _close_named_window(book)
        raise

    active_bytes = (
        _group_bytes(BOOK_NAMES, book_cap)
        + _group_bytes(FLOW_NAMES, flow_cap)
        + _group_bytes(MIDPOINT_NAMES, midpoint_cap)
    )
    return book, flow, midpoint, active_bytes


def _close_output_groups(book, flow, midpoint) -> None:
    _close_named_window(midpoint)
    _close_named_window(flow)
    _close_named_window(book)


def run_stateful_windowed_raw_from_columns(
    ev,
    exch_ts,
    local_ts,
    px,
    qty,
    *,
    root: Path,
    input_chunk_rows: int = DEFAULT_INPUT_CHUNK_ROWS,
    kernel=None,
) -> StatefulRawRun:
    n = int(ev.size)
    width = int(input_chunk_rows)
    if n <= 0:
        raise R27P29Error("rows")
    if width <= 0:
        raise R27P29Error("input_chunk_rows")
    if not (exch_ts.size == local_ts.size == px.size == qty.size == n):
        raise R27P29Error("column_lengths")

    paths = r27p28.prepare_full_capacity_files(Path(root), n)
    k = build_stateful_windowed_raw_kernel() if kernel is None else kernel
    lb, la, eb, ea = _make_books()

    current_local = -1
    current_exchange = -1
    local_changed = False
    exchange_changed = False
    last_local = -1
    last_exchange = -1
    observed_exchange = -1
    error = 0

    book_total = 0
    flow_total = 0
    midpoint_total = 0
    chunk_count = 0
    max_active = 0

    start = 0
    while start < n and error == 0:
        stop = min(n, start + width)
        m = stop - start
        final_chunk = stop == n
        book, flow, midpoint, active = _map_output_groups(
            paths,
            rows=n,
            chunk_count=m,
            final_chunk=final_chunk,
            book_start=book_total,
            flow_start=flow_total,
            midpoint_start=midpoint_total,
        )
        max_active = max(max_active, int(active))
        try:
            out = k(
                ev[start:stop],
                exch_ts[start:stop],
                local_ts[start:stop],
                px[start:stop],
                qty[start:stop],
                final_chunk,
                lb,
                la,
                eb,
                ea,
                current_local,
                current_exchange,
                local_changed,
                exchange_changed,
                last_local,
                last_exchange,
                observed_exchange,
                book["book_local_ns"],
                book["bid_ticks"],
                book["bid_qty"],
                book["ask_ticks"],
                book["ask_qty"],
                book["candidate_qty"],
                flow["flow_local_ns"],
                flow["flow_code"],
                flow["flow_qty"],
                midpoint["midpoint_exchange_ns"],
                midpoint["midpoint_tick_sum"],
            )
        finally:
            _close_output_groups(book, flow, midpoint)

        (
            book_count,
            flow_count,
            midpoint_count,
            current_local,
            current_exchange,
            local_changed,
            exchange_changed,
            last_local,
            last_exchange,
            observed_exchange,
            error,
        ) = out

        book_total += int(book_count)
        flow_total += int(flow_count)
        midpoint_total += int(midpoint_count)
        chunk_count += 1
        start = stop

    if any(value < 0 or value > n for value in (book_total, flow_total, midpoint_total)):
        raise R27P29Error("count_bounds")
    if int(error) >= 100:
        raise R27P29Error(f"window_capacity_error:{int(error)}")

    return StatefulRawRun(
        paths=paths,
        rows=n,
        input_chunk_rows=width,
        input_chunk_count=chunk_count,
        book_count=book_total,
        flow_count=flow_total,
        midpoint_count=midpoint_total,
        observed_exchange=int(observed_exchange),
        error=int(error),
        max_active_output_mapped_bytes=max_active,
    )


def _read_group_arrays(run: StatefulRawRun):
    counts = {
        "book_local_ns": run.book_count,
        "bid_ticks": run.book_count,
        "bid_qty": run.book_count,
        "ask_ticks": run.book_count,
        "ask_qty": run.book_count,
        "candidate_qty": run.book_count,
        "flow_local_ns": run.flow_count,
        "flow_code": run.flow_count,
        "flow_qty": run.flow_count,
        "midpoint_exchange_ns": run.midpoint_count,
        "midpoint_tick_sum": run.midpoint_count,
    }
    arrays: list[np.ndarray] = []
    for spec in r27p20_specs():
        count = int(counts[spec.name])
        if count == 0:
            arrays.append(np.empty((0,) + tuple(spec.trailing_shape), dtype=np.dtype(spec.dtype)))
            continue
        mapped = np.memmap(
            run.paths[spec.name],
            mode="r",
            dtype=np.dtype(spec.dtype),
            shape=_shape(count, spec),
        )
        try:
            arrays.append(np.array(mapped, copy=True))
        finally:
            mm = getattr(mapped, "_mmap", None)
            if mm is not None:
                mm.close()
    return tuple(arrays) + (int(run.observed_exchange), int(run.error))


def run_synthetic_stateful_raw_parity_probe(
    chunk_rows_cases: tuple[int, ...] = (1, 2, 3, 5, 7),
) -> StatefulParityResult:
    validate_r27p29_contract()
    if not chunk_rows_cases or any(int(x) <= 0 for x in chunk_rows_cases):
        raise R27P29Error("chunk_rows_cases")

    fixture = r20.make_synthetic_dual_context_fixture()
    a = r9._validate_event_array(fixture)
    n = int(a.shape[0])
    reference_kernel = r27p6.build_fused_raw_kernel()
    reference = reference_kernel(a["ev"], a["exch_ts"], a["local_ts"], a["px"], a["qty"])
    target_kernel = build_stateful_windowed_raw_kernel()

    cases: list[StatefulParityCase] = []
    with TemporaryDirectory(prefix="dev045_r27p29_") as root:
        root_path = Path(root)
        for width in chunk_rows_cases:
            run = run_stateful_windowed_raw_from_columns(
                a["ev"],
                a["exch_ts"],
                a["local_ts"],
                a["px"],
                a["qty"],
                root=root_path / f"chunk_{int(width)}",
                input_chunk_rows=int(width),
                kernel=target_kernel,
            )
            candidate = _read_group_arrays(run)
            r27p21._assert_raw_tuple_exact(reference, candidate)
            if run.book_count != int(np.asarray(reference[0]).shape[0]):
                raise R27P29Error("book_count")
            if run.flow_count != int(np.asarray(reference[6]).shape[0]):
                raise R27P29Error("flow_count")
            if run.midpoint_count != int(np.asarray(reference[9]).shape[0]):
                raise R27P29Error("midpoint_count")
            if run.observed_exchange != int(reference[11]):
                raise R27P29Error("observed_exchange")
            if run.error != int(reference[12]):
                raise R27P29Error("error_code")
            expected_chunks = int(math.ceil(n / int(width)))
            if run.input_chunk_count != expected_chunks:
                raise R27P29Error("input_chunk_count")
            theoretical_bound = min(n, int(width)) * BYTES_PER_EVENT + 248
            if run.max_active_output_mapped_bytes > theoretical_bound:
                raise R27P29Error("active_mapping_bound")
            cases.append(
                StatefulParityCase(
                    input_chunk_rows=int(width),
                    input_chunk_count=run.input_chunk_count,
                    book_count=run.book_count,
                    flow_count=run.flow_count,
                    midpoint_count=run.midpoint_count,
                    observed_exchange=run.observed_exchange,
                    error=run.error,
                    max_active_output_mapped_bytes=run.max_active_output_mapped_bytes,
                    exact_raw_bytes=True,
                )
            )

    return StatefulParityResult(
        rows=n,
        raw_buffer_count=RAW_BUFFER_COUNT,
        bytes_per_event=BYTES_PER_EVENT,
        cases=tuple(cases),
    )


def validate_r27p29_contract() -> None:
    r27p28.validate_r27p28_contract()
    if PARENT_R27P28_HEAD != "0792fd992870081a9880a37aa6f5a0e05ffe41f3":
        raise R27P29Error("parent")
    if PARENT_R27P28_CI_RUN != 34715145539 or PARENT_R27P28_CI_JOB != 103610947812:
        raise R27P29Error("parent_ci_identity")
    if PARENT_R27P28_CI_CONCLUSION != "success":
        raise R27P29Error("parent_ci_conclusion")
    if RAW_BUFFER_COUNT != 11 or BYTES_PER_EVENT != 265:
        raise R27P29Error("raw_capacity_identity")
    if DEFAULT_INPUT_CHUNK_ROWS <= 0:
        raise R27P29Error("chunk_rows")
    if tuple(spec.name for spec in r27p20_specs()) != BOOK_NAMES + FLOW_NAMES + MIDPOINT_NAMES:
        raise R27P29Error("buffer_group_identity")

    required = (
        STATEFUL_BOOKS_CARRIED_ACROSS_CHUNKS,
        PENDING_TIMESTAMP_STATE_CARRIED_ACROSS_CHUNKS,
        NO_SYNTHETIC_FLUSH_AT_CHUNK_BOUNDARY,
        FINAL_FLUSH_ONLY_ON_FINAL_CHUNK,
        INDEPENDENT_BOOK_FLOW_MIDPOINT_OUTPUT_OFFSETS,
        BOUNDED_OUTPUT_MAPPING_REQUIRED,
        not FULL_FILE_OUTPUT_MAPPING_FOR_TARGET_ARCHITECTURE,
        EXACT_RAW_BYTE_PARITY_REQUIRED,
        EXACT_COUNTS_REQUIRED,
        EXACT_ERROR_CODE_REQUIRED,
        EXACT_OBSERVED_EXCHANGE_REQUIRED,
        ONE_LOGICAL_EVENT_PASS_REQUIRED,
        STATEFUL_RAW_KERNEL_WINDOWING_COMPLETE,
        SYNTHETIC_ONLY,
        not FULL_CORRECTED_CONTEXT_WINDOWING_COMPLETE,
        not FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not CANONICAL_EXECUTION_READY,
    )
    if not all(required):
        raise R27P29Error("required_guard")

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
        raise R27P29Error("execution_surface_open")
    if READINESS_BLOCKER != "WINDOWED_RAW_PARITY_NOT_YET_FROZEN_AND_DOWNSTREAM_CONTEXT_NOT_YET_WINDOWED":
        raise R27P29Error("readiness_blocker")


__all__ = [
    "StatefulParityCase",
    "StatefulParityResult",
    "StatefulRawRun",
    "build_stateful_windowed_raw_kernel",
    "run_stateful_windowed_raw_from_columns",
    "run_synthetic_stateful_raw_parity_probe",
    "validate_r27p29_contract",
]

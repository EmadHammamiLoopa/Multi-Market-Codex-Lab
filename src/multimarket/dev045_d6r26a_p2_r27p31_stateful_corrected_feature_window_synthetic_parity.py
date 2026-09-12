from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p6a_full_context_fusion_midpoint_transport as r27p6a
from multimarket import dev045_d6r26a_p2_r27p9_cpython313_float_sum_parity_amendment as r27p9
from multimarket import dev045_d6r26a_p2_r27p16_r10_rolling_volatility_parity_amendment as r27p16
from multimarket import dev045_d6r26a_p2_r27p18_corrected_5m_speed_benchmark_preexecution as r27p18
from multimarket import dev045_d6r26a_p2_r27p30_windowed_raw_corrected_context_synthetic_parity as r27p30


EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P31"
DESIGN_VERSION = "stateful-corrected-feature-window-synthetic-parity-v1"
PARENT_R27P30_HEAD = "64fe4292c06bb19df5117f5a474f099fe7f513ca"
PARENT_R27P30_CI_RUN = 34718235901
PARENT_R27P30_CI_JOB = 103619204229
PARENT_R27P30_CI_CONCLUSION = "success"
PARENT_R27P30_TEST_COUNT = 4

ARCHITECTURE = "STATEFUL_DECISION_CHUNKS_FILE_BACKED_CORRECTED_FEATURE_OUTPUT"
FEATURE_COUNT = r27p5.FEATURE_COUNT
CASE_COUNT = r27p5.CASE_COUNT
OUTPUT_BYTES_PER_ELIGIBLE_DECISION = 8 + 8 + 8 + CASE_COUNT * FEATURE_COUNT * 8
DEFAULT_DECISION_CHUNK_ROWS = 64

STATEFUL_ROLLING_FEATURE_STATE_CARRIED_ACROSS_CHUNKS = True
CORRECTED_L5_WRITTEN_INLINE = True
CORRECTED_R10_VOLATILITY_WRITTEN_INLINE = True
CPYTHON313_L5_COMPENSATED_SUM_BOUND = True
CPYTHON_R10_TRANSITION_SQ_BOUND = True
FULL_DAY_O_N_TRANSITION_ARRAYS_ELIMINATED = True
AMENDMENT_FULL_VALUES_COPY_ELIMINATED = True
FULL_DAY_RAM_OUTPUT_ARRAYS_ELIMINATED = True
BOUNDED_OUTPUT_MAPPING_REQUIRED = True
FINAL_OUTPUT_FILE_BACKED = True
EXACT_CORRECTED_CONTEXT_PARITY_REQUIRED = True
EXACT_CONTEXT_DIGEST_REQUIRED = True
ROLLING_ADD_SUBTRACT_ORDER_PRESERVED = True
PREELIGIBLE_CORRECTED_VOLATILITY_ADVANCE_FORBIDDEN = True

# R27P31 bounds the feature-output residency and eliminates the known O(full-day)
# transition/copy allocations. It does not yet prove that the full raw input files
# can be consumed under the 12 GiB July RSS ceiling. A later successor must bind
# raw-input mapping/release and measure the composed pipeline.
RAW_INPUT_BOUNDED_WINDOW_MAPPING_COMPLETE = False
TIME_WINDOW_DENSITY_RSS_BOUND_PROVEN = False
FULL_DAY_BOUNDED_MEMORY_PROVEN = False
GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN = False
CANONICAL_EXECUTION_READY = False
READINESS_BLOCKER = "RAW_INPUT_MAPPING_AND_COMPOSED_PIPELINE_RSS_NOT_YET_PROVEN"

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


class R27P31Error(RuntimeError):
    pass


@dataclass(frozen=True)
class FeatureState:
    book_ingest: int = 0
    flow_ingest: int = 0
    leading: int = 0
    first_eligible: bool = False
    ofi1: float = 0.0
    ofi5: float = 0.0
    ofi1_head: int = 1
    ofi5_head: int = 1
    tb1: float = 0.0
    ts1: float = 0.0
    tb5: float = 0.0
    ts5: float = 0.0
    ab1: float = 0.0
    aa1: float = 0.0
    cb1: float = 0.0
    ca1: float = 0.0
    tb1_head: int = 0
    ts1_head: int = 0
    tb5_head: int = 0
    ts5_head: int = 0
    ab1_head: int = 0
    aa1_head: int = 0
    cb1_head: int = 0
    ca1_head: int = 0
    vol_ingest: int = 0
    vol1: float = 0.0
    vol5: float = 0.0
    vol30: float = 0.0
    vol1_head: int = 1
    vol5_head: int = 1
    vol30_head: int = 1


@dataclass
class FileBackedFeatureResult:
    compiled: r27p5.CompiledFeatureResult
    paths: dict[str, Path]
    requested_count: int
    eligible_count: int
    decision_chunk_rows: int
    decision_chunk_count: int
    max_active_output_mapped_bytes: int
    max_transition_sq_rows: int
    closed: bool = False


@dataclass(frozen=True)
class FeatureParityCase:
    decision_chunk_rows: int
    decision_chunk_count: int
    eligible_count: int
    leading_preeligible_count: int
    max_active_output_mapped_bytes: int
    max_transition_sq_rows: int
    exact_context_parity: bool
    exact_context_digest: bool


@dataclass(frozen=True)
class FeatureParityProbe:
    requested_count: int
    reference_l5_changed_cells: int
    reference_volatility_changed_cells: int
    reference_digest: r27p0.ContextDigest
    cases: tuple[FeatureParityCase, ...]


def _load_numba():
    try:
        from numba import njit
    except Exception as exc:
        raise R27P31Error("numba_unavailable") from exc
    return njit


def prepare_feature_files(root: Path, requested_count: int) -> dict[str, Path]:
    n = int(requested_count)
    if n <= 0:
        raise R27P31Error("requested_count")
    target = Path(root)
    target.mkdir(parents=True, exist_ok=False)
    specs = (
        ("decision_local_ns", np.dtype("<i8"), ()),
        ("best_bid_tick", np.dtype("<i8"), ()),
        ("best_ask_tick", np.dtype("<i8"), ()),
        ("values", np.dtype("<f8"), (CASE_COUNT, FEATURE_COUNT)),
    )
    paths: dict[str, Path] = {}
    for name, dtype, trailing in specs:
        row_bytes = int(dtype.itemsize) * int(np.prod(trailing or (1,), dtype=np.int64))
        path = target / f"{name}.bin"
        with path.open("wb") as handle:
            handle.truncate(n * row_bytes)
        paths[name] = path
    return paths


def _map_feature_output_window(paths: dict[str, Path], *, row_start: int, row_count: int):
    start = int(row_start)
    count = int(row_count)
    if start < 0 or count <= 0:
        raise R27P31Error("output_window")
    mapped: dict[str, np.memmap] = {}
    specs = (
        ("decision_local_ns", np.dtype("<i8"), ()),
        ("best_bid_tick", np.dtype("<i8"), ()),
        ("best_ask_tick", np.dtype("<i8"), ()),
        ("values", np.dtype("<f8"), (CASE_COUNT, FEATURE_COUNT)),
    )
    try:
        for name, dtype, trailing in specs:
            row_bytes = int(dtype.itemsize) * int(np.prod(trailing or (1,), dtype=np.int64))
            path = Path(paths[name])
            if (start + count) * row_bytes > path.stat().st_size:
                raise R27P31Error(f"output_window_exceeds_file:{name}")
            mapped[name] = np.memmap(
                path,
                mode="r+",
                dtype=dtype,
                offset=start * row_bytes,
                shape=(count,) + tuple(trailing),
            )
        return mapped
    except Exception:
        _close_mappings(mapped)
        raise


def _close_mappings(mapped: dict[str, np.memmap]) -> None:
    for array in mapped.values():
        array.flush()
        mm = getattr(array, "_mmap", None)
        if mm is not None:
            mm.close()


def _cpython_transition_sq_window(
    surface: r27p5.CompactFeatureSurface,
    *,
    start: int,
    end: int,
) -> np.ndarray:
    lo = int(start)
    hi = int(end)
    if lo < 0 or hi < lo or hi > int(surface.book_local_ns.size):
        raise R27P31Error("transition_sq_bounds")
    out = np.empty(hi - lo, dtype=np.float64)
    tick = float(p0.TICK_SIZE)
    bt = np.asarray(surface.bid_ticks)
    at = np.asarray(surface.ask_ticks)
    for j, i in enumerate(range(lo, hi)):
        if i == 0:
            out[j] = 0.0
            continue
        before_mid = 0.5 * float(int(bt[i - 1, 0]) + int(at[i - 1, 0])) * tick
        after_mid = 0.5 * float(int(bt[i, 0]) + int(at[i, 0])) * tick
        if before_mid <= 0.0 or after_mid <= 0.0:
            raise R27P31Error("mid_price")
        out[j] = math.log(after_mid / before_mid) ** 2
    return out


def _state_args(s: FeatureState):
    return (
        s.book_ingest,
        s.flow_ingest,
        s.leading,
        s.first_eligible,
        s.ofi1,
        s.ofi5,
        s.ofi1_head,
        s.ofi5_head,
        s.tb1,
        s.ts1,
        s.tb5,
        s.ts5,
        s.ab1,
        s.aa1,
        s.cb1,
        s.ca1,
        s.tb1_head,
        s.ts1_head,
        s.tb5_head,
        s.ts5_head,
        s.ab1_head,
        s.aa1_head,
        s.cb1_head,
        s.ca1_head,
        s.vol_ingest,
        s.vol1,
        s.vol5,
        s.vol30,
        s.vol1_head,
        s.vol5_head,
        s.vol30_head,
    )


def _state_from_kernel(out) -> FeatureState:
    return FeatureState(
        book_ingest=int(out[2]),
        flow_ingest=int(out[3]),
        leading=int(out[4]),
        first_eligible=bool(out[5]),
        ofi1=float(out[6]),
        ofi5=float(out[7]),
        ofi1_head=int(out[8]),
        ofi5_head=int(out[9]),
        tb1=float(out[10]),
        ts1=float(out[11]),
        tb5=float(out[12]),
        ts5=float(out[13]),
        ab1=float(out[14]),
        aa1=float(out[15]),
        cb1=float(out[16]),
        ca1=float(out[17]),
        tb1_head=int(out[18]),
        ts1_head=int(out[19]),
        tb5_head=int(out[20]),
        ts5_head=int(out[21]),
        ab1_head=int(out[22]),
        aa1_head=int(out[23]),
        cb1_head=int(out[24]),
        ca1_head=int(out[25]),
        vol_ingest=int(out[26]),
        vol1=float(out[27]),
        vol5=float(out[28]),
        vol30=float(out[29]),
        vol1_head=int(out[30]),
        vol5_head=int(out[31]),
        vol30_head=int(out[32]),
    )


def build_stateful_corrected_feature_kernel():
    njit = _load_numba()
    tick_size = float(p0.TICK_SIZE)
    distances = tuple(int(x) for x in r27p5.DISTANCES)

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
    def compensated_sum5(row):
        hi = float(row[0])
        lo = 0.0
        for j in range(1, 5):
            x = float(row[j])
            t = hi + x
            if abs(hi) >= abs(x):
                lo += (hi - t) + x
            else:
                lo += (x - t) + hi
            hi = t
        if lo != 0.0 and math.isfinite(lo):
            hi += lo
        return hi

    @njit(cache=False)
    def kernel(
        book_ns,
        bt,
        bq,
        at,
        aq,
        candidate_qty,
        flow_ns,
        flow_code,
        flow_qty,
        requested,
        transition_sq,
        sq_offset,
        final_chunk,
        out_dec,
        out_bid,
        out_ask,
        out_values,
        book_ingest,
        flow_ingest,
        leading,
        first_eligible,
        ofi1,
        ofi5,
        ofi1_head,
        ofi5_head,
        tb1,
        ts1,
        tb5,
        ts5,
        ab1,
        aa1,
        cb1,
        ca1,
        tb1_head,
        ts1_head,
        tb5_head,
        ts5_head,
        ab1_head,
        aa1_head,
        cb1_head,
        ca1_head,
        vol_ingest,
        vol1,
        vol5,
        vol30,
        vol1_head,
        vol5_head,
        vol30_head,
    ):
        nbooks = book_ns.size
        nflows = flow_ns.size
        out_count = 0
        error = 0

        for ri in range(requested.size):
            decision = int(requested[ri])

            while book_ingest < nbooks and int(book_ns[book_ingest]) <= decision:
                if book_ingest > 0:
                    val = ofi_transition(bt, bq, at, aq, book_ingest - 1, book_ingest)
                    ofi1 += val
                    ofi5 += val
                book_ingest += 1

            while flow_ingest < nflows and int(flow_ns[flow_ingest]) <= decision:
                code = int(flow_code[flow_ingest])
                q = float(flow_qty[flow_ingest])
                if code == r27p5.FLOW_TRADE_BUY:
                    tb1 += q
                    tb5 += q
                elif code == r27p5.FLOW_TRADE_SELL:
                    ts1 += q
                    ts5 += q
                elif code == r27p5.FLOW_ADD_BID:
                    ab1 += q
                elif code == r27p5.FLOW_ADD_ASK:
                    aa1 += q
                elif code == r27p5.FLOW_CANCEL_BID:
                    cb1 += q
                elif code == r27p5.FLOW_CANCEL_ASK:
                    ca1 += q
                else:
                    error = 1
                    break
                flow_ingest += 1
            if error != 0:
                break

            if book_ingest <= 0:
                if first_eligible:
                    error = 2
                    break
                leading += 1
                continue

            current = book_ingest - 1
            if decision - int(book_ns[0]) < 30_000_000_000:
                if first_eligible:
                    error = 3
                    break
                leading += 1
                continue

            l5_ok = True
            for j in range(5):
                if (
                    int(bt[current, j]) <= 0
                    or int(at[current, j]) <= 0
                    or float(bq[current, j]) <= 0.0
                    or float(aq[current, j]) <= 0.0
                ):
                    l5_ok = False
                    break
            if not l5_ok:
                if first_eligible:
                    error = 4
                    break
                leading += 1
                continue

            first_eligible = True
            cutoff1 = decision - 1_000_000_000
            cutoff5 = decision - 5_000_000_000
            cutoff30 = decision - 30_000_000_000

            while ofi1_head < book_ingest and int(book_ns[ofi1_head]) <= cutoff1:
                ofi1 -= ofi_transition(bt, bq, at, aq, ofi1_head - 1, ofi1_head)
                ofi1_head += 1
            while ofi5_head < book_ingest and int(book_ns[ofi5_head]) <= cutoff5:
                ofi5 -= ofi_transition(bt, bq, at, aq, ofi5_head - 1, ofi5_head)
                ofi5_head += 1

            while tb1_head < flow_ingest and int(flow_ns[tb1_head]) <= cutoff1:
                if int(flow_code[tb1_head]) == r27p5.FLOW_TRADE_BUY:
                    tb1 -= float(flow_qty[tb1_head])
                tb1_head += 1
            while ts1_head < flow_ingest and int(flow_ns[ts1_head]) <= cutoff1:
                if int(flow_code[ts1_head]) == r27p5.FLOW_TRADE_SELL:
                    ts1 -= float(flow_qty[ts1_head])
                ts1_head += 1
            while tb5_head < flow_ingest and int(flow_ns[tb5_head]) <= cutoff5:
                if int(flow_code[tb5_head]) == r27p5.FLOW_TRADE_BUY:
                    tb5 -= float(flow_qty[tb5_head])
                tb5_head += 1
            while ts5_head < flow_ingest and int(flow_ns[ts5_head]) <= cutoff5:
                if int(flow_code[ts5_head]) == r27p5.FLOW_TRADE_SELL:
                    ts5 -= float(flow_qty[ts5_head])
                ts5_head += 1
            while ab1_head < flow_ingest and int(flow_ns[ab1_head]) <= cutoff1:
                if int(flow_code[ab1_head]) == r27p5.FLOW_ADD_BID:
                    ab1 -= float(flow_qty[ab1_head])
                ab1_head += 1
            while aa1_head < flow_ingest and int(flow_ns[aa1_head]) <= cutoff1:
                if int(flow_code[aa1_head]) == r27p5.FLOW_ADD_ASK:
                    aa1 -= float(flow_qty[aa1_head])
                aa1_head += 1
            while cb1_head < flow_ingest and int(flow_ns[cb1_head]) <= cutoff1:
                if int(flow_code[cb1_head]) == r27p5.FLOW_CANCEL_BID:
                    cb1 -= float(flow_qty[cb1_head])
                cb1_head += 1
            while ca1_head < flow_ingest and int(flow_ns[ca1_head]) <= cutoff1:
                if int(flow_code[ca1_head]) == r27p5.FLOW_CANCEL_ASK:
                    ca1 -= float(flow_qty[ca1_head])
                ca1_head += 1

            # Exact R27P16/R10 corrected volatility semantics. The corrected
            # volatility state is not advanced during preeligible decisions.
            while vol_ingest < book_ingest:
                if vol_ingest > 0:
                    pos = vol_ingest - sq_offset
                    if pos < 0 or pos >= transition_sq.size:
                        error = 7
                        break
                    z = float(transition_sq[pos])
                    vol1 += z
                    vol5 += z
                    vol30 += z
                vol_ingest += 1
            if error != 0:
                break

            while vol1_head < vol_ingest and int(book_ns[vol1_head]) <= cutoff1:
                pos = vol1_head - sq_offset
                if pos < 0 or pos >= transition_sq.size:
                    error = 7
                    break
                vol1 -= float(transition_sq[pos])
                vol1_head += 1
            if error != 0:
                break
            while vol5_head < vol_ingest and int(book_ns[vol5_head]) <= cutoff5:
                pos = vol5_head - sq_offset
                if pos < 0 or pos >= transition_sq.size:
                    error = 7
                    break
                vol5 -= float(transition_sq[pos])
                vol5_head += 1
            if error != 0:
                break
            while vol30_head < vol_ingest and int(book_ns[vol30_head]) <= cutoff30:
                pos = vol30_head - sq_offset
                if pos < 0 or pos >= transition_sq.size:
                    error = 7
                    break
                vol30 -= float(transition_sq[pos])
                vol30_head += 1
            if error != 0:
                break

            prior250 = asof_index(book_ns, book_ingest, decision - 250_000_000)
            prior1s = asof_index(book_ns, book_ingest, decision - 1_000_000_000)
            if prior250 < 0 or prior1s < 0:
                error = 5
                break

            if out_count >= out_dec.size:
                error = 8
                break

            best_bid_tick = int(bt[current, 0])
            best_ask_tick = int(at[current, 0])
            best_bid_qty = float(bq[current, 0])
            best_ask_qty = float(aq[current, 0])
            spread = best_ask_tick - best_bid_tick
            mid = 0.5 * float(best_bid_tick + best_ask_tick) * tick_size
            den_micro = best_bid_qty + best_ask_qty
            micro = (
                (float(best_bid_tick) * tick_size * best_ask_qty)
                + (float(best_ask_tick) * tick_size * best_bid_qty)
            ) / den_micro

            vamp_num = 0.0
            vamp_den = 0.0
            for j in range(5):
                bqty = float(bq[current, j])
                aqty = float(aq[current, j])
                vamp_num += (
                    float(bt[current, j]) * tick_size * aqty
                    + float(at[current, j]) * tick_size * bqty
                )
                vamp_den += bqty + aqty
            vamp5 = vamp_num / vamp_den

            bid5 = compensated_sum5(bq[current])
            ask5 = compensated_sum5(aq[current])
            l5_obi = ratio(bid5, ask5)
            prior250_bid_qty = float(bq[prior250, 0])
            prior250_ask_qty = float(aq[prior250, 0])
            prior1_spread = int(at[prior1s, 0]) - int(bt[prior1s, 0])

            for case_index in range(CASE_COUNT):
                is_bid = case_index < 4
                distance = distances[case_index if is_bid else case_index - 4]
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
                out_values[out_count, case_index, 5] = l5_obi
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

        if error == 0 and final_chunk and not first_eligible:
            error = 6

        return (
            out_count,
            error,
            book_ingest,
            flow_ingest,
            leading,
            first_eligible,
            ofi1,
            ofi5,
            ofi1_head,
            ofi5_head,
            tb1,
            ts1,
            tb5,
            ts5,
            ab1,
            aa1,
            cb1,
            ca1,
            tb1_head,
            ts1_head,
            tb5_head,
            ts5_head,
            ab1_head,
            aa1_head,
            cb1_head,
            ca1_head,
            vol_ingest,
            vol1,
            vol5,
            vol30,
            vol1_head,
            vol5_head,
            vol30_head,
        )

    return kernel


def _open_result_prefix(paths: dict[str, Path], eligible_count: int):
    n = int(eligible_count)
    if n <= 0:
        raise R27P31Error("eligible_count")
    arrays = {
        "decision_local_ns": np.memmap(paths["decision_local_ns"], mode="r", dtype="<i8", shape=(n,)),
        "best_bid_tick": np.memmap(paths["best_bid_tick"], mode="r", dtype="<i8", shape=(n,)),
        "best_ask_tick": np.memmap(paths["best_ask_tick"], mode="r", dtype="<i8", shape=(n,)),
        "values": np.memmap(paths["values"], mode="r", dtype="<f8", shape=(n, CASE_COUNT, FEATURE_COUNT)),
    }
    for array in arrays.values():
        array.setflags(write=False)
    return arrays


def close_feature_result(result: FileBackedFeatureResult) -> None:
    if result.closed:
        raise R27P31Error("feature_result_closed")
    for array in (
        result.compiled.decision_local_ns,
        result.compiled.best_bid_tick,
        result.compiled.best_ask_tick,
        result.compiled.values,
    ):
        mm = getattr(array, "_mmap", None)
        if mm is not None:
            mm.close()
    result.closed = True


def run_stateful_corrected_feature_surface(
    surface: r27p5.CompactFeatureSurface,
    requested_decisions: np.ndarray,
    *,
    root: Path,
    decision_chunk_rows: int = DEFAULT_DECISION_CHUNK_ROWS,
    kernel=None,
) -> FileBackedFeatureResult:
    requested = np.asarray(requested_decisions, dtype="<i8")
    if requested.ndim != 1 or requested.size <= 0:
        raise R27P31Error("requested")
    if requested.size > 1 and bool(np.any(requested[1:] <= requested[:-1])):
        raise R27P31Error("requested_not_strict")
    width = int(decision_chunk_rows)
    if width <= 0:
        raise R27P31Error("decision_chunk_rows")

    paths = prepare_feature_files(Path(root), int(requested.size))
    k = build_stateful_corrected_feature_kernel() if kernel is None else kernel
    state = FeatureState()
    output_total = 0
    chunk_count = 0
    max_active = 0
    max_sq_rows = 0

    start = 0
    while start < int(requested.size):
        stop = min(int(requested.size), start + width)
        chunk = requested[start:stop]
        final_chunk = stop == int(requested.size)

        target_book_ingest = int(np.searchsorted(surface.book_local_ns, int(chunk[-1]), side="right"))
        sq_start = min(
            int(state.vol_ingest),
            int(state.vol1_head),
            int(state.vol5_head),
            int(state.vol30_head),
        )
        sq_start = max(0, min(sq_start, target_book_ingest))
        transition_sq = _cpython_transition_sq_window(
            surface,
            start=sq_start,
            end=target_book_ingest,
        )
        max_sq_rows = max(max_sq_rows, int(transition_sq.size))

        mapped = _map_feature_output_window(
            paths,
            row_start=output_total,
            row_count=int(chunk.size),
        )
        max_active = max(max_active, int(chunk.size) * OUTPUT_BYTES_PER_ELIGIBLE_DECISION)
        try:
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
                chunk,
                transition_sq,
                int(sq_start),
                final_chunk,
                mapped["decision_local_ns"],
                mapped["best_bid_tick"],
                mapped["best_ask_tick"],
                mapped["values"],
                *_state_args(state),
            )
        finally:
            _close_mappings(mapped)

        wrote = int(out[0])
        error = int(out[1])
        if error != 0:
            reasons = {
                1: "flow_code",
                2: "book_missing_after_eligibility",
                3: "warmup_failure_after_eligibility",
                4: "l5_failure_after_eligibility",
                5: "recent_book_asof_missing",
                6: "no_eligible_feature_decision",
                7: "transition_sq_window",
                8: "output_window_capacity",
            }
            raise R27P31Error(reasons.get(error, f"kernel_error:{error}"))
        if wrote < 0 or wrote > int(chunk.size):
            raise R27P31Error("written_count")

        output_total += wrote
        state = _state_from_kernel(out)
        chunk_count += 1
        start = stop

    arrays = _open_result_prefix(paths, output_total)
    compiled = r27p5.CompiledFeatureResult(
        decision_local_ns=arrays["decision_local_ns"],
        best_bid_tick=arrays["best_bid_tick"],
        best_ask_tick=arrays["best_ask_tick"],
        values=arrays["values"],
        leading_preeligible_count=int(state.leading),
    )
    if output_total != int(requested.size) - int(state.leading):
        close = FileBackedFeatureResult(
            compiled=compiled,
            paths=paths,
            requested_count=int(requested.size),
            eligible_count=output_total,
            decision_chunk_rows=width,
            decision_chunk_count=chunk_count,
            max_active_output_mapped_bytes=max_active,
            max_transition_sq_rows=max_sq_rows,
        )
        close_feature_result(close)
        raise R27P31Error("eligible_count_identity")

    return FileBackedFeatureResult(
        compiled=compiled,
        paths=paths,
        requested_count=int(requested.size),
        eligible_count=output_total,
        decision_chunk_rows=width,
        decision_chunk_count=chunk_count,
        max_active_output_mapped_bytes=max_active,
        max_transition_sq_rows=max_sq_rows,
    )


def _candidate_context_from_feature_result(
    *,
    result: FileBackedFeatureResult,
    requested: np.ndarray,
    bounds,
    raw: r27p6.FusedRawSurface,
    scratch_root: Path,
) -> r20.DayContextBuildResult:
    compiled = result.compiled
    cache = r18.DenseFeatureCache(
        decision_local_ns=compiled.decision_local_ns,
        best_bid_tick=compiled.best_bid_tick,
        best_ask_tick=compiled.best_ask_tick,
        values=compiled.values,
    )
    r18.validate_dense_feature_cache(cache)
    summary = r19.FeatureCacheBuildSummary(
        requested_decision_count=int(requested.size),
        leading_preeligible_count=int(compiled.leading_preeligible_count),
        eligible_decision_count=int(cache.decision_count),
        first_requested_local_ns=int(requested[0]),
        first_eligible_local_ns=int(cache.decision_local_ns[0]),
        last_eligible_local_ns=int(cache.decision_local_ns[-1]),
        raw_event_pass_count=1,
    )
    midpoint = r27p6a._write_midpoint_index(
        exchange_ns=raw.midpoint_exchange_ns,
        mid_tick_sum=raw.midpoint_tick_sum,
        source_exchange_observed_through_ns=raw.source_exchange_observed_through_ns,
        scratch_root=Path(scratch_root),
        index_name="exchange_midpoints.bin",
    )
    return r20.DayContextBuildResult(
        bounds=bounds,
        feature_cache=cache,
        feature_summary=summary,
        midpoint_index=midpoint,
        raw_event_pass_count=1,
    )


def run_synthetic_feature_parity_probe(
    chunk_rows_cases: tuple[int, ...] = (1, 3, 7),
) -> FeatureParityProbe:
    validate_r27p31_contract()
    if not chunk_rows_cases or any(int(x) <= 0 for x in chunk_rows_cases):
        raise R27P31Error("chunk_rows_cases")

    fixture = r20.make_synthetic_dual_context_fixture()
    raw_kernel = r27p6.build_fused_raw_kernel()
    base_feature_kernel = r27p5.build_feature_kernel()
    l5_kernel = r27p9.build_l5_obi_amendment_kernel()
    target_kernel = build_stateful_corrected_feature_kernel()

    reference = None
    with TemporaryDirectory(prefix="dev045_r27p31_") as root:
        root_path = Path(root)
        reference, ref_l5, ref_vol = r27p18.build_corrected_fused_day_context(
            fixture,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
            scratch_root=root_path / "reference",
            raw_kernel=raw_kernel,
            base_feature_kernel=base_feature_kernel,
            l5_amendment_kernel=l5_kernel,
        )
        reference_digest = r27p0.digest_day_context(reference)

        a = r19._validate_event_surface(fixture)
        bounds = r17.derive_feed_bounds(
            a,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
        )
        requested = np.asarray(r17.build_shared_decision_grid(bounds=bounds), dtype="<i8")
        raw = r27p6.run_fused_raw_surface(a, kernel=raw_kernel)
        surface = r27p18._compact_from_raw(raw)

        cases: list[FeatureParityCase] = []
        try:
            for width in chunk_rows_cases:
                result = run_stateful_corrected_feature_surface(
                    surface,
                    requested,
                    root=root_path / f"feature_{int(width)}",
                    decision_chunk_rows=int(width),
                    kernel=target_kernel,
                )
                candidate = None
                try:
                    candidate = _candidate_context_from_feature_result(
                        result=result,
                        requested=requested,
                        bounds=bounds,
                        raw=raw,
                        scratch_root=root_path / f"midpoint_{int(width)}",
                    )
                    r27p0.assert_exact_context_parity(reference, candidate)
                    candidate_digest = r27p0.digest_day_context(candidate)
                    if candidate_digest != reference_digest:
                        raise R27P31Error("context_digest")
                    expected_chunks = int(math.ceil(int(requested.size) / int(width)))
                    if result.decision_chunk_count != expected_chunks:
                        raise R27P31Error("decision_chunk_count")
                    if result.max_active_output_mapped_bytes > min(int(width), int(requested.size)) * OUTPUT_BYTES_PER_ELIGIBLE_DECISION:
                        raise R27P31Error("output_mapping_bound")
                    cases.append(
                        FeatureParityCase(
                            decision_chunk_rows=int(width),
                            decision_chunk_count=int(result.decision_chunk_count),
                            eligible_count=int(result.eligible_count),
                            leading_preeligible_count=int(result.compiled.leading_preeligible_count),
                            max_active_output_mapped_bytes=int(result.max_active_output_mapped_bytes),
                            max_transition_sq_rows=int(result.max_transition_sq_rows),
                            exact_context_parity=True,
                            exact_context_digest=True,
                        )
                    )
                finally:
                    if candidate is not None and not candidate.midpoint_index.closed:
                        r20.close_midpoint_index(candidate.midpoint_index)
                    close_feature_result(result)
        finally:
            if reference is not None and not reference.midpoint_index.closed:
                r20.close_midpoint_index(reference.midpoint_index)

    return FeatureParityProbe(
        requested_count=int(requested.size),
        reference_l5_changed_cells=int(ref_l5),
        reference_volatility_changed_cells=int(ref_vol),
        reference_digest=reference_digest,
        cases=tuple(cases),
    )


def validate_r27p31_contract() -> None:
    r27p30.validate_r27p30_contract()
    r27p16.validate_r27p16_contract()
    if PARENT_R27P30_HEAD != "64fe4292c06bb19df5117f5a474f099fe7f513ca":
        raise R27P31Error("parent")
    if PARENT_R27P30_CI_RUN != 34718235901 or PARENT_R27P30_CI_JOB != 103619204229:
        raise R27P31Error("parent_ci_identity")
    if PARENT_R27P30_CI_CONCLUSION != "success" or PARENT_R27P30_TEST_COUNT != 4:
        raise R27P31Error("parent_ci_result")
    if FEATURE_COUNT != 25 or CASE_COUNT != 8:
        raise R27P31Error("feature_shape_identity")
    if OUTPUT_BYTES_PER_ELIGIBLE_DECISION != 1624:
        raise R27P31Error("output_bytes_per_decision")

    required = (
        STATEFUL_ROLLING_FEATURE_STATE_CARRIED_ACROSS_CHUNKS,
        CORRECTED_L5_WRITTEN_INLINE,
        CORRECTED_R10_VOLATILITY_WRITTEN_INLINE,
        CPYTHON313_L5_COMPENSATED_SUM_BOUND,
        CPYTHON_R10_TRANSITION_SQ_BOUND,
        FULL_DAY_O_N_TRANSITION_ARRAYS_ELIMINATED,
        AMENDMENT_FULL_VALUES_COPY_ELIMINATED,
        FULL_DAY_RAM_OUTPUT_ARRAYS_ELIMINATED,
        BOUNDED_OUTPUT_MAPPING_REQUIRED,
        FINAL_OUTPUT_FILE_BACKED,
        EXACT_CORRECTED_CONTEXT_PARITY_REQUIRED,
        EXACT_CONTEXT_DIGEST_REQUIRED,
        ROLLING_ADD_SUBTRACT_ORDER_PRESERVED,
        PREELIGIBLE_CORRECTED_VOLATILITY_ADVANCE_FORBIDDEN,
        SYNTHETIC_ONLY,
        not RAW_INPUT_BOUNDED_WINDOW_MAPPING_COMPLETE,
        not TIME_WINDOW_DENSITY_RSS_BOUND_PROVEN,
        not FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not CANONICAL_EXECUTION_READY,
    )
    if not all(required):
        raise R27P31Error("required_guard")

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
        raise R27P31Error("execution_surface_open")
    if READINESS_BLOCKER != "RAW_INPUT_MAPPING_AND_COMPOSED_PIPELINE_RSS_NOT_YET_PROVEN":
        raise R27P31Error("readiness_blocker")


__all__ = [
    "FeatureParityCase",
    "FeatureParityProbe",
    "FeatureState",
    "FileBackedFeatureResult",
    "build_stateful_corrected_feature_kernel",
    "close_feature_result",
    "prepare_feature_files",
    "run_stateful_corrected_feature_surface",
    "run_synthetic_feature_parity_probe",
    "validate_r27p31_contract",
]

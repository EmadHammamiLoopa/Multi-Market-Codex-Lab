from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np

from multimarket import dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P1"
DESIGN_VERSION = "numba-kernel-foundation-preexecution-v1"
PARENT_R27P0_HEAD = "fdf26a3d562ae65b20721161601c0b25de388b21"

IMPLEMENTATION = "NUMBA_JIT"
REFERENCE_IMPLEMENTATION = r27p0.REFERENCE_IMPLEMENTATION
MIN_ACCEPTED_SPEEDUP = r27p0.MIN_ACCEPTED_SPEEDUP

NUMBA_KERNEL_FOUNDATION_ONLY = True
FULL_CONTEXT_REPLACEMENT_AUTHORIZED = False
REAL_HISTORICAL_BENCHMARK_AUTHORIZED = False
FULL_JAN_JUL_RERUN_AUTHORIZED = False
P2_ATTEMPT_CONSUMED = False
SIMULATOR_LANE_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False


class R27P1Error(RuntimeError):
    pass


@dataclass(frozen=True)
class ScanSummary:
    row_count: int
    local_rows: int
    exchange_rows: int
    depth_rows: int
    trade_rows: int
    ignored_rows: int
    last_local_ns: int
    last_exchange_ns: int


def _python_scan(events: np.ndarray) -> ScanSummary:
    a = r9._validate_event_array(events)
    local_rows = exchange_rows = depth_rows = trade_rows = ignored_rows = 0
    last_local = -1
    last_exchange = -1
    for row in a:
        ev = int(row["ev"])
        kind = r9._event_kind(ev)
        if kind not in r9.SUPPORTED_EVENT_TYPES:
            raise R27P1Error(f"unknown_event_kind:{kind}")
        if r9._has_flag(ev, r9.LOCAL_EVENT):
            local_rows += 1
            local_ns = int(row["local_ts"])
            if local_ns < last_local:
                raise R27P1Error("local_timestamp_regression")
            last_local = local_ns
        if r9._has_flag(ev, r9.EXCH_EVENT):
            exchange_rows += 1
            exchange_ns = int(row["exch_ts"])
            if exchange_ns < last_exchange:
                raise R27P1Error("exchange_timestamp_regression")
            last_exchange = exchange_ns
        if kind in (r9.DEPTH_EVENT, r9.DEPTH_CLEAR_EVENT, r9.DEPTH_SNAPSHOT_EVENT):
            depth_rows += 1
        elif kind == r9.TRADE_EVENT:
            trade_rows += 1
        else:
            ignored_rows += 1
    return ScanSummary(int(a.size), local_rows, exchange_rows, depth_rows, trade_rows, ignored_rows, last_local, last_exchange)


def _load_numba():
    try:
        from numba import njit
    except Exception as exc:
        raise R27P1Error("numba_unavailable") from exc
    return njit


def build_numba_scan_kernel():
    njit = _load_numba()
    supported = tuple(sorted(int(x) for x in r9.SUPPORTED_EVENT_TYPES))
    local_flag = int(r9.LOCAL_EVENT)
    exch_flag = int(r9.EXCH_EVENT)
    mask = int(r9.EVENT_KIND_MASK)
    depth = int(r9.DEPTH_EVENT)
    clear = int(r9.DEPTH_CLEAR_EVENT)
    snapshot = int(r9.DEPTH_SNAPSHOT_EVENT)
    trade = int(r9.TRADE_EVENT)

    @njit(cache=False)
    def kernel(ev, exch_ts, local_ts):
        local_rows = 0
        exchange_rows = 0
        depth_rows = 0
        trade_rows = 0
        ignored_rows = 0
        last_local = -1
        last_exchange = -1
        error = 0
        for i in range(ev.size):
            e = int(ev[i])
            kind = e & mask
            ok = False
            for item in supported:
                if kind == item:
                    ok = True
                    break
            if not ok:
                error = 1
                break
            if (e & local_flag) == local_flag:
                local_rows += 1
                ts = int(local_ts[i])
                if ts < last_local:
                    error = 2
                    break
                last_local = ts
            if (e & exch_flag) == exch_flag:
                exchange_rows += 1
                ts = int(exch_ts[i])
                if ts < last_exchange:
                    error = 3
                    break
                last_exchange = ts
            if kind == depth or kind == clear or kind == snapshot:
                depth_rows += 1
            elif kind == trade:
                trade_rows += 1
            else:
                ignored_rows += 1
        return (ev.size, local_rows, exchange_rows, depth_rows, trade_rows, ignored_rows, last_local, last_exchange, error)
    return kernel


def numba_scan(events: np.ndarray, *, kernel=None) -> ScanSummary:
    a = r9._validate_event_array(events)
    k = build_numba_scan_kernel() if kernel is None else kernel
    result = k(a["ev"], a["exch_ts"], a["local_ts"])
    error = int(result[8])
    if error == 1:
        raise R27P1Error("unknown_event_kind")
    if error == 2:
        raise R27P1Error("local_timestamp_regression")
    if error == 3:
        raise R27P1Error("exchange_timestamp_regression")
    return ScanSummary(*(int(x) for x in result[:8]))


def assert_scan_parity(events: np.ndarray, *, kernel=None) -> None:
    expected = _python_scan(events)
    observed = numba_scan(events, kernel=kernel)
    if observed != expected:
        raise R27P1Error(f"scan_parity:{expected!r}:{observed!r}")


def benchmark_scan(events: np.ndarray, *, repetitions: int = 3) -> tuple[float, float, float]:
    a = r9._validate_event_array(events)
    if repetitions < 1:
        raise R27P1Error("repetitions")
    kernel = build_numba_scan_kernel()
    _ = numba_scan(a, kernel=kernel)
    assert_scan_parity(a, kernel=kernel)
    py = []
    nb = []
    for _ in range(repetitions):
        t0 = perf_counter(); _python_scan(a); py.append(perf_counter() - t0)
        t0 = perf_counter(); numba_scan(a, kernel=kernel); nb.append(perf_counter() - t0)
    py_best = min(py)
    nb_best = min(nb)
    if nb_best <= 0.0:
        raise R27P1Error("numba_elapsed")
    return py_best, nb_best, py_best / nb_best


def validate_r27p1_contract() -> None:
    r27p0.validate_r27p0_contract()
    if PARENT_R27P0_HEAD != "fdf26a3d562ae65b20721161601c0b25de388b21":
        raise R27P1Error("parent")
    if IMPLEMENTATION != "NUMBA_JIT":
        raise R27P1Error("implementation")
    if MIN_ACCEPTED_SPEEDUP != 10.0:
        raise R27P1Error("speedup_gate")
    required = (NUMBA_KERNEL_FOUNDATION_ONLY, not FULL_CONTEXT_REPLACEMENT_AUTHORIZED, not REAL_HISTORICAL_BENCHMARK_AUTHORIZED, not FULL_JAN_JUL_RERUN_AUTHORIZED)
    if not all(required):
        raise R27P1Error("required_guard")
    forbidden = (P2_ATTEMPT_CONSUMED, SIMULATOR_LANE_AUTHORIZED, ATTEMPT_MARKER_WRITE_AUTHORIZED, CANONICAL_LABEL_WRITE_AUTHORIZED, MODEL_FIT_AUTHORIZED, PNL_AUTHORIZED, AUG_OPEN_AUTHORIZED, SEP_PLUS_OPEN_AUTHORIZED, NON_BTC_OPEN_AUTHORIZED)
    if any(forbidden):
        raise R27P1Error("execution_surface_open")


__all__ = ["ScanSummary", "assert_scan_parity", "benchmark_scan", "build_numba_scan_kernel", "numba_scan", "validate_r27p1_contract"]

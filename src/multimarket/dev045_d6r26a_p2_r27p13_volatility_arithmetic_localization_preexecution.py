from __future__ import annotations

from dataclasses import dataclass
import math
import os

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P13"
DESIGN_VERSION = "volatility-arithmetic-localization-preexecution-v1"
PARENT_R27P12_FREEZE_HEAD = "2ac0536c3259ade4c05cb75566667e278a6b5850"
AUTH_ENV = "DEV045_D6R26A_P2_R27P13_AUTHORIZE"
AUTH_TOKEN = "YES_REAL_5M_VOLATILITY_ARITHMETIC_LOCALIZATION"
PREFIX_ROWS = 5_000_000
SOURCE_DAY = "2026-01-01"
SOURCE_PATH = r27p2.SOURCE_PATH
SOURCE_ROWS = r27p2.SOURCE_ROWS
SOURCE_BYTES = r27p2.SOURCE_BYTES
SOURCE_SHA256 = r27p2.SOURCE_SHA256
SOURCE_DAY_START_NS = r27p2.SOURCE_DAY_START_NS
SOURCE_DAY_END_EXCLUSIVE_NS = r27p2.SOURCE_DAY_END_EXCLUSIVE_NS

R27P12_FIRST_VOL1_DECISION_INDEX = 4104
R27P12_FIRST_VOL5_DECISION_INDEX = 4107
R27P12_VOL_EXPECTED = 0.022749725154012572
R27P12_VOL_OBSERVED = 0.022749725154012565

REAL_HISTORICAL_DIAGNOSTIC_AUTHORIZED = True
ONE_FROZEN_SOURCE_ONLY = True
PREFIX_ONLY = True
REFERENCE_CONTEXT_REBUILD = False
NO_TIMING = True
NO_SPEED_GATE = True
P2_ATTEMPT_CONSUMED = False
FULL_JAN_JUL_RERUN_AUTHORIZED = False
SIMULATOR_LANE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED = False


class R27P13Error(RuntimeError):
    pass


@dataclass(frozen=True)
class LayerDiff:
    mismatch_count: int
    first_index: int | None
    expected: float | None
    observed: float | None
    max_abs_diff: float


@dataclass(frozen=True)
class ArithmeticReport:
    transition_sq: LayerDiff
    rolling_vol1: LayerDiff
    rolling_vol5: LayerDiff
    rolling_vol30: LayerDiff
    transform_vol1: LayerDiff
    transform_vol5: LayerDiff
    transform_vol30: LayerDiff
    root_layer: str
    decision_count: int
    book_count: int


def real_diagnostic_authorized(environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(AUTH_ENV) == AUTH_TOKEN


def _diff(a: np.ndarray, b: np.ndarray) -> LayerDiff:
    x = np.asarray(a, dtype=np.float64)
    y = np.asarray(b, dtype=np.float64)
    if x.shape != y.shape:
        raise R27P13Error("shape")
    mask = np.not_equal(x, y)
    count = int(np.count_nonzero(mask))
    if not count:
        return LayerDiff(0, None, None, None, 0.0)
    idx = int(np.flatnonzero(mask)[0])
    return LayerDiff(count, idx, float(x[idx]), float(y[idx]), float(np.max(np.abs(x[mask] - y[mask]))))


def _build_numba_arithmetic_kernel():
    try:
        from numba import njit
    except Exception as exc:
        raise R27P13Error("numba_unavailable") from exc
    tick = float(p0.TICK_SIZE)

    @njit(cache=False)
    def kernel(book_ns, bt, at, requested):
        nbooks = book_ns.size
        nreq = requested.size
        sq = np.zeros(nbooks, dtype=np.float64)
        out1 = np.zeros(nreq, dtype=np.float64)
        out5 = np.zeros(nreq, dtype=np.float64)
        out30 = np.zeros(nreq, dtype=np.float64)
        fin1 = np.zeros(nreq, dtype=np.float64)
        fin5 = np.zeros(nreq, dtype=np.float64)
        fin30 = np.zeros(nreq, dtype=np.float64)
        ingest = 0
        h1 = 1; h5 = 1; h30 = 1
        v1 = 0.0; v5 = 0.0; v30 = 0.0
        for ri in range(nreq):
            decision = int(requested[ri])
            while ingest < nbooks and int(book_ns[ingest]) <= decision:
                if ingest > 0:
                    before_mid = 0.5 * float(bt[ingest - 1, 0] + at[ingest - 1, 0]) * tick
                    after_mid = 0.5 * float(bt[ingest, 0] + at[ingest, 0]) * tick
                    z = math.log(after_mid / before_mid) ** 2
                    sq[ingest] = z
                    v1 += z; v5 += z; v30 += z
                ingest += 1
            c1 = decision - 1_000_000_000
            c5 = decision - 5_000_000_000
            c30 = decision - 30_000_000_000
            while h1 < ingest and int(book_ns[h1]) <= c1:
                v1 -= sq[h1]; h1 += 1
            while h5 < ingest and int(book_ns[h5]) <= c5:
                v5 -= sq[h5]; h5 += 1
            while h30 < ingest and int(book_ns[h30]) <= c30:
                v30 -= sq[h30]; h30 += 1
            out1[ri] = v1; out5[ri] = v5; out30[ri] = v30
            fin1[ri] = 10000.0 * math.sqrt(max(0.0, v1))
            fin5[ri] = 10000.0 * math.sqrt(max(0.0, v5))
            fin30[ri] = 10000.0 * math.sqrt(max(0.0, v30))
        return sq, out1, out5, out30, fin1, fin5, fin30

    return kernel


def _python_arithmetic(book_ns: np.ndarray, bt: np.ndarray, at: np.ndarray, requested: np.ndarray):
    tick = float(p0.TICK_SIZE)
    nbooks = int(book_ns.size)
    sq = np.zeros(nbooks, dtype=np.float64)
    for i in range(1, nbooks):
        before_mid = 0.5 * float(int(bt[i - 1, 0]) + int(at[i - 1, 0])) * tick
        after_mid = 0.5 * float(int(bt[i, 0]) + int(at[i, 0])) * tick
        sq[i] = math.log(after_mid / before_mid) ** 2

    nreq = int(requested.size)
    out1 = np.zeros(nreq, dtype=np.float64); out5 = np.zeros(nreq, dtype=np.float64); out30 = np.zeros(nreq, dtype=np.float64)
    ingest = 0; h1 = 1; h5 = 1; h30 = 1
    v1 = 0.0; v5 = 0.0; v30 = 0.0
    for ri, raw_decision in enumerate(requested):
        decision = int(raw_decision)
        while ingest < nbooks and int(book_ns[ingest]) <= decision:
            if ingest > 0:
                z = float(sq[ingest]); v1 += z; v5 += z; v30 += z
            ingest += 1
        c1 = decision - 1_000_000_000; c5 = decision - 5_000_000_000; c30 = decision - 30_000_000_000
        while h1 < ingest and int(book_ns[h1]) <= c1:
            v1 -= float(sq[h1]); h1 += 1
        while h5 < ingest and int(book_ns[h5]) <= c5:
            v5 -= float(sq[h5]); h5 += 1
        while h30 < ingest and int(book_ns[h30]) <= c30:
            v30 -= float(sq[h30]); h30 += 1
        out1[ri] = v1; out5[ri] = v5; out30[ri] = v30
    return sq, out1, out5, out30


def _python_transform(v: np.ndarray) -> np.ndarray:
    return np.asarray([10000.0 * math.sqrt(max(0.0, float(x))) for x in v], dtype=np.float64)


def diagnose(events: np.ndarray) -> ArithmeticReport:
    a = r19._validate_event_surface(events)
    prefix = a[:PREFIX_ROWS]
    bounds = r17.derive_feed_bounds(prefix, nominal_day_start_local_ns=SOURCE_DAY_START_NS, nominal_day_end_exclusive_local_ns=SOURCE_DAY_END_EXCLUSIVE_NS)
    requested = np.asarray(r17.build_shared_decision_grid(bounds=bounds), dtype="<i8")
    raw = r27p6.run_fused_raw_surface(prefix)
    book_ns = raw.book_local_ns; bt = raw.bid_ticks; at = raw.ask_ticks

    py_sq, py1, py5, py30 = _python_arithmetic(book_ns, bt, at, requested)
    k = _build_numba_arithmetic_kernel()
    nb_sq, nb1, nb5, nb30, nbf1, nbf5, nbf30 = k(book_ns, bt, at, requested)

    d_sq = _diff(py_sq, nb_sq)
    d1 = _diff(py1, nb1); d5 = _diff(py5, nb5); d30 = _diff(py30, nb30)
    t1 = _diff(_python_transform(nb1), nbf1)
    t5 = _diff(_python_transform(nb5), nbf5)
    t30 = _diff(_python_transform(nb30), nbf30)

    if d_sq.mismatch_count:
        root = "TRANSITION_LOG_SQUARE_ARITHMETIC"
    elif d1.mismatch_count or d5.mismatch_count or d30.mismatch_count:
        root = "ROLLING_ADD_SUBTRACT_ARITHMETIC"
    elif t1.mismatch_count or t5.mismatch_count or t30.mismatch_count:
        root = "SQRT_TRANSFORM_ARITHMETIC"
    else:
        root = "NOT_REPRODUCED_IN_ARITHMETIC_ISOLATION"
    return ArithmeticReport(d_sq, d1, d5, d30, t1, t5, t30, root, int(requested.size), int(book_ns.size))


def _show(name: str, d: LayerDiff) -> None:
    print(f"R27P13_LAYER={name} MISMATCH_COUNT={d.mismatch_count} FIRST_INDEX={d.first_index} EXPECTED={d.expected!r} OBSERVED={d.observed!r} MAX_ABS_DIFF={d.max_abs_diff!r}")


def run_real_localization(environ: dict[str, str] | None = None) -> ArithmeticReport:
    validate_r27p13_contract()
    if not real_diagnostic_authorized(environ):
        raise R27P13Error("authorization")
    r27p2._validate_preattempt_state()
    events = r27p2._verify_source_identity()
    try:
        if bool(events.flags.writeable):
            raise R27P13Error("source_writeable")
        report = diagnose(events)
    finally:
        mm = getattr(events, "_mmap", None)
        if mm is not None:
            mm.close()
    print(f"R27P13_SOURCE_IDENTITY=PASS DAY={SOURCE_DAY} ROWS={SOURCE_ROWS} BYTES={SOURCE_BYTES} SHA256={SOURCE_SHA256}")
    print(f"R27P13_PREFIX_ROWS={PREFIX_ROWS}")
    print(f"R27P13_BOOK_COUNT={report.book_count}")
    print(f"R27P13_REQUESTED_DECISION_COUNT={report.decision_count}")
    _show("TRANSITION_SQ", report.transition_sq)
    _show("ROLLING_VOL1", report.rolling_vol1); _show("ROLLING_VOL5", report.rolling_vol5); _show("ROLLING_VOL30", report.rolling_vol30)
    _show("TRANSFORM_VOL1", report.transform_vol1); _show("TRANSFORM_VOL5", report.transform_vol5); _show("TRANSFORM_VOL30", report.transform_vol30)
    print(f"R27P13_ROOT_LAYER={report.root_layer}")
    print("R27P13_REFERENCE_CONTEXT_REBUILD=NO")
    print("R27P12_RERUN=NO")
    print("R27P13_TIMING_PERFORMED=NO")
    print("R27P13_SPEED_GATE_RUN=NO")
    print("P2_ATTEMPT_CONSUMED=NO")
    print("FULL_JAN_JUL_RERUN=NO")
    print("SIMULATOR_RUN=NO")
    print("MODEL_FIT=NO")
    print("PNL=NO")
    print("MARKET_RAW_ARCHIVE_OPENED=NO")
    return report


def validate_r27p13_contract() -> None:
    if PARENT_R27P12_FREEZE_HEAD != "2ac0536c3259ade4c05cb75566667e278a6b5850":
        raise R27P13Error("parent")
    if PREFIX_ROWS != 5_000_000 or REFERENCE_CONTEXT_REBUILD:
        raise R27P13Error("scope")
    required = (REAL_HISTORICAL_DIAGNOSTIC_AUTHORIZED, ONE_FROZEN_SOURCE_ONLY, PREFIX_ONLY, NO_TIMING, NO_SPEED_GATE)
    if not all(required):
        raise R27P13Error("required_guard")
    forbidden = (P2_ATTEMPT_CONSUMED, FULL_JAN_JUL_RERUN_AUTHORIZED, SIMULATOR_LANE_AUTHORIZED, MODEL_FIT_AUTHORIZED, PNL_AUTHORIZED, LIVE_TRADING_AUTHORIZED, AUG_OPEN_AUTHORIZED, SEP_PLUS_OPEN_AUTHORIZED, NON_BTC_OPEN_AUTHORIZED, MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED)
    if any(forbidden):
        raise R27P13Error("execution_surface_open")


def main() -> int:
    try:
        run_real_localization()
    except Exception as exc:
        print(f"R27P13_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("R27P12_RERUN=NO")
        print("P2_ATTEMPT_CONSUMED=NO")
        print("MARKET_RAW_ARCHIVE_OPENED=NO")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

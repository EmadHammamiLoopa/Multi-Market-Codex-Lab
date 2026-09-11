from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p8_real_prefix_parity_localization_preexecution as r27p8

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P9"
DESIGN_VERSION = "cpython313-float-sum-parity-amendment-v1"
PARENT_R27P8_HEAD = "f1f8110e1b73fb52073c3b742b32364ee3e70af9"

CPYTHON_REFERENCE_VERSION = "3.13"
CPYTHON_FLOAT_SUM_ALGORITHM = "NEUMAIER_COMPENSATED_SUM"
AMENDED_FEATURE_NAME = "l5_obi"
AMENDED_FEATURE_INDEX = 5
AMENDED_FEATURE_COUNT = 1
EXACT_OTHER_FEATURE_BYTES_REQUIRED = True
REAL_HISTORICAL_BENCHMARK_AUTHORIZED = False
REAL_HISTORICAL_DIAGNOSTIC_AUTHORIZED = False
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


class R27P9Error(RuntimeError):
    pass


@dataclass(frozen=True)
class AmendmentAudit:
    changed_cells: int
    changed_feature_indices: tuple[int, ...]
    other_feature_bytes_equal: bool


def cpython313_sum5(values: np.ndarray) -> float:
    a = np.asarray(values, dtype=np.float64)
    if a.shape != (5,):
        raise R27P9Error("sum5_shape")
    hi = float(a[0])
    lo = 0.0
    for x0 in a[1:]:
        x = float(x0)
        t = hi + x
        if abs(hi) >= abs(x):
            lo += (hi - t) + x
        else:
            lo += (x - t) + hi
        hi = t
    if lo and math.isfinite(lo):
        hi += lo
    return float(hi)


def _load_numba():
    try:
        from numba import njit
    except Exception as exc:
        raise R27P9Error("numba_unavailable") from exc
    return njit


def build_l5_obi_amendment_kernel():
    njit = _load_numba()

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
    def kernel(book_ns, bid_qty, ask_qty, decisions, values):
        out = values.copy()
        nbooks = book_ns.size
        for i in range(decisions.size):
            current = asof_index(book_ns, nbooks, int(decisions[i]))
            if current < 0:
                return out, 1
            bid5 = compensated_sum5(bid_qty[current])
            ask5 = compensated_sum5(ask_qty[current])
            l5 = ratio(bid5, ask5)
            for case_index in range(out.shape[1]):
                out[i, case_index, AMENDED_FEATURE_INDEX] = l5
        return out, 0

    return kernel


def run_amended_feature_kernel(
    surface: r27p5.CompactFeatureSurface,
    requested_decisions: np.ndarray,
    *,
    base_kernel=None,
    amendment_kernel=None,
) -> r27p5.CompiledFeatureResult:
    base = r27p5.run_compiled_feature_kernel(
        surface,
        requested_decisions,
        kernel=base_kernel,
    )
    k = build_l5_obi_amendment_kernel() if amendment_kernel is None else amendment_kernel
    values, error = k(
        surface.book_local_ns,
        surface.bid_qty,
        surface.ask_qty,
        base.decision_local_ns,
        base.values,
    )
    if int(error) != 0:
        raise R27P9Error("book_asof_missing")
    corrected = np.asarray(values, dtype=np.float64)
    corrected.setflags(write=False)
    return r27p5.CompiledFeatureResult(
        decision_local_ns=base.decision_local_ns,
        best_bid_tick=base.best_bid_tick,
        best_ask_tick=base.best_ask_tick,
        values=corrected,
        leading_preeligible_count=base.leading_preeligible_count,
    )


def audit_amendment(
    before: r27p5.CompiledFeatureResult,
    after: r27p5.CompiledFeatureResult,
) -> AmendmentAudit:
    if before.values.shape != after.values.shape or before.values.dtype != after.values.dtype:
        raise R27P9Error("value_surface_identity")
    mismatch = np.not_equal(before.values, after.values)
    coords = np.argwhere(mismatch)
    indices = tuple(sorted({int(row[2]) for row in coords})) if coords.size else ()
    before_other = np.delete(before.values, AMENDED_FEATURE_INDEX, axis=2)
    after_other = np.delete(after.values, AMENDED_FEATURE_INDEX, axis=2)
    return AmendmentAudit(
        changed_cells=int(np.count_nonzero(mismatch)),
        changed_feature_indices=indices,
        other_feature_bytes_equal=bool(np.array_equal(before_other, after_other)),
    )


def validate_r27p9_contract() -> None:
    r27p8.validate_r27p8_contract()
    if PARENT_R27P8_HEAD != "f1f8110e1b73fb52073c3b742b32364ee3e70af9":
        raise R27P9Error("parent")
    if CPYTHON_REFERENCE_VERSION != "3.13":
        raise R27P9Error("cpython_version")
    if CPYTHON_FLOAT_SUM_ALGORITHM != "NEUMAIER_COMPENSATED_SUM":
        raise R27P9Error("sum_algorithm")
    if AMENDED_FEATURE_NAME != r8b.FEATURE_NAMES[AMENDED_FEATURE_INDEX]:
        raise R27P9Error("feature_identity")
    if AMENDED_FEATURE_COUNT != 1 or not EXACT_OTHER_FEATURE_BYTES_REQUIRED:
        raise R27P9Error("amendment_scope")
    forbidden = (
        REAL_HISTORICAL_BENCHMARK_AUTHORIZED,
        REAL_HISTORICAL_DIAGNOSTIC_AUTHORIZED,
        FULL_JAN_JUL_RERUN_AUTHORIZED,
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
        raise R27P9Error("execution_surface_open")


__all__ = [
    "AMENDED_FEATURE_INDEX",
    "AMENDED_FEATURE_NAME",
    "AmendmentAudit",
    "audit_amendment",
    "build_l5_obi_amendment_kernel",
    "cpython313_sum5",
    "run_amended_feature_kernel",
    "validate_r27p9_contract",
]

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P14"
DESIGN_VERSION = "cpython-volatility-parity-amendment-v1"
PARENT_R27P13_FREEZE_HEAD = "22b630e1469b56014d08e651a575edf980497869"

CPYTHON_REFERENCE_VERSION = "3.13"
ROOT_CAUSE_LAYER = "TRANSITION_LOG_SQUARE_ARITHMETIC"
AMENDED_FEATURE_INDICES = (16, 17, 18)
AMENDED_FEATURE_NAMES = tuple(r8b.FEATURE_NAMES[i] for i in AMENDED_FEATURE_INDICES)
WINDOWS_NS = (1_000_000_000, 5_000_000_000, 30_000_000_000)
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
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED = False


class R27P14Error(RuntimeError):
    pass


@dataclass(frozen=True)
class AmendmentAudit:
    changed_cells: int
    changed_feature_indices: tuple[int, ...]
    other_feature_bytes_equal: bool


def _precompute_cpython_transition_sq(surface: r27p5.CompactFeatureSurface) -> np.ndarray:
    book_ns = np.asarray(surface.book_local_ns)
    bt = np.asarray(surface.bid_ticks)
    at = np.asarray(surface.ask_ticks)
    if book_ns.ndim != 1 or bt.shape != at.shape or bt.ndim != 2 or bt.shape[0] != book_ns.size:
        raise R27P14Error("book_surface")
    tick = float(p0.TICK_SIZE)
    sq = np.zeros(book_ns.size, dtype=np.float64)
    for i in range(1, int(book_ns.size)):
        before_mid = 0.5 * float(int(bt[i - 1, 0]) + int(at[i - 1, 0])) * tick
        after_mid = 0.5 * float(int(bt[i, 0]) + int(at[i, 0])) * tick
        if before_mid <= 0.0 or after_mid <= 0.0:
            raise R27P14Error("mid_price")
        sq[i] = math.log(after_mid / before_mid) ** 2
    sq.setflags(write=False)
    return sq


def _cpython_realized_vol_for_decisions(
    *,
    book_ns: np.ndarray,
    transition_sq: np.ndarray,
    decisions: np.ndarray,
    window_ns: int,
) -> np.ndarray:
    times = np.asarray(book_ns, dtype=np.int64)
    sq = np.asarray(transition_sq, dtype=np.float64)
    dec = np.asarray(decisions, dtype=np.int64)
    if times.ndim != 1 or sq.shape != times.shape or dec.ndim != 1:
        raise R27P14Error("surface")
    out = np.empty(dec.size, dtype=np.float64)
    window = int(window_ns)
    for di, raw_decision in enumerate(dec):
        decision = int(raw_decision)
        start = decision - window
        anchor = int(np.searchsorted(times, start, side="right")) - 1
        end = int(np.searchsorted(times, decision, side="right")) - 1
        if anchor < 0 or end < anchor:
            raise R27P14Error("book_asof_missing")
        squared = 0.0
        for i in range(anchor + 1, end + 1):
            squared += float(sq[i])
        out[di] = 10_000.0 * math.sqrt(squared)
    out.setflags(write=False)
    return out


def apply_volatility_amendment(
    surface: r27p5.CompactFeatureSurface,
    base: r27p5.CompiledFeatureResult,
) -> r27p5.CompiledFeatureResult:
    sq = _precompute_cpython_transition_sq(surface)
    decisions = np.asarray(base.decision_local_ns, dtype=np.int64)
    corrected = np.asarray(base.values, dtype=np.float64).copy()
    for feature_index, window in zip(AMENDED_FEATURE_INDICES, WINDOWS_NS):
        values = _cpython_realized_vol_for_decisions(
            book_ns=surface.book_local_ns,
            transition_sq=sq,
            decisions=decisions,
            window_ns=window,
        )
        for case_index in range(corrected.shape[1]):
            corrected[:, case_index, feature_index] = values
    corrected.setflags(write=False)
    return r27p5.CompiledFeatureResult(
        decision_local_ns=base.decision_local_ns,
        best_bid_tick=base.best_bid_tick,
        best_ask_tick=base.best_ask_tick,
        values=corrected,
        leading_preeligible_count=base.leading_preeligible_count,
    )


def audit_amendment(before: r27p5.CompiledFeatureResult, after: r27p5.CompiledFeatureResult) -> AmendmentAudit:
    if before.values.shape != after.values.shape or before.values.dtype != after.values.dtype:
        raise R27P14Error("value_surface_identity")
    mismatch = np.not_equal(before.values, after.values)
    coords = np.argwhere(mismatch)
    indices = tuple(sorted({int(row[2]) for row in coords})) if coords.size else ()
    keep = [i for i in range(before.values.shape[2]) if i not in AMENDED_FEATURE_INDICES]
    other_equal = bool(np.array_equal(before.values[:, :, keep], after.values[:, :, keep]))
    return AmendmentAudit(
        changed_cells=int(np.count_nonzero(mismatch)),
        changed_feature_indices=indices,
        other_feature_bytes_equal=other_equal,
    )


def validate_r27p14_contract() -> None:
    if PARENT_R27P13_FREEZE_HEAD != "22b630e1469b56014d08e651a575edf980497869":
        raise R27P14Error("parent")
    if CPYTHON_REFERENCE_VERSION != "3.13" or ROOT_CAUSE_LAYER != "TRANSITION_LOG_SQUARE_ARITHMETIC":
        raise R27P14Error("root_cause")
    if AMENDED_FEATURE_INDICES != (16, 17, 18):
        raise R27P14Error("feature_indices")
    if AMENDED_FEATURE_NAMES != ("realized_vol_1s", "realized_vol_5s", "realized_vol_30s"):
        raise R27P14Error("feature_names")
    if WINDOWS_NS != (1_000_000_000, 5_000_000_000, 30_000_000_000):
        raise R27P14Error("windows")
    if not EXACT_OTHER_FEATURE_BYTES_REQUIRED:
        raise R27P14Error("other_feature_guard")
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
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED,
    )
    if any(forbidden):
        raise R27P14Error("execution_surface_open")


__all__ = [
    "AMENDED_FEATURE_INDICES",
    "AMENDED_FEATURE_NAMES",
    "AmendmentAudit",
    "apply_volatility_amendment",
    "audit_amendment",
    "validate_r27p14_contract",
]

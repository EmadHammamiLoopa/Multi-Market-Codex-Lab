from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P16"
DESIGN_VERSION = "r10-rolling-volatility-parity-amendment-v1"
PARENT_R27P15_FAILURE_FREEZE_HEAD = "3c3dc535b6805af828cacd01f2ae2db617bee66e"

CPYTHON_REFERENCE_VERSION = "3.13"
REFERENCE_SEMANTICS = "R10_ROLLING_FEATURE_ACCUMULATOR"
SUPERSEDES_R27P14_BATCH_WINDOW_AMENDMENT = True
AMENDED_FEATURE_INDICES = (16, 17, 18)
AMENDED_FEATURE_NAMES = tuple(r8b.FEATURE_NAMES[i] for i in AMENDED_FEATURE_INDICES)
WINDOWS_NS = (1_000_000_000, 5_000_000_000, 30_000_000_000)
EXACT_OTHER_FEATURE_BYTES_REQUIRED = True
ELIGIBLE_DECISIONS_ONLY = True
PREELIGIBLE_ADVANCE_FORBIDDEN = True

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


class R27P16Error(RuntimeError):
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
        raise R27P16Error("book_surface")
    tick = float(p0.TICK_SIZE)
    sq = np.zeros(book_ns.size, dtype=np.float64)
    for i in range(1, int(book_ns.size)):
        before_mid = 0.5 * float(int(bt[i - 1, 0]) + int(at[i - 1, 0])) * tick
        after_mid = 0.5 * float(int(bt[i, 0]) + int(at[i, 0])) * tick
        if before_mid <= 0.0 or after_mid <= 0.0:
            raise R27P16Error("mid_price")
        sq[i] = math.log(after_mid / before_mid) ** 2
    sq.setflags(write=False)
    return sq


def _r10_rolling_volatility_for_eligible_decisions(
    *,
    book_ns: np.ndarray,
    transition_sq: np.ndarray,
    decisions: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    times = np.asarray(book_ns, dtype=np.int64)
    sq = np.asarray(transition_sq, dtype=np.float64)
    dec = np.asarray(decisions, dtype=np.int64)
    if times.ndim != 1 or sq.shape != times.shape or dec.ndim != 1:
        raise R27P16Error("surface")
    if dec.size == 0:
        raise R27P16Error("decisions_empty")
    if np.any(dec[1:] < dec[:-1]):
        raise R27P16Error("decision_regression")

    out1 = np.empty(dec.size, dtype=np.float64)
    out5 = np.empty(dec.size, dtype=np.float64)
    out30 = np.empty(dec.size, dtype=np.float64)

    ingest = 0
    h1 = 1
    h5 = 1
    h30 = 1
    v1 = 0.0
    v5 = 0.0
    v30 = 0.0
    nbooks = int(times.size)

    for di, raw_decision in enumerate(dec):
        decision = int(raw_decision)

        while ingest < nbooks and int(times[ingest]) <= decision:
            if ingest > 0:
                z = float(sq[ingest])
                v1 += z
                v5 += z
                v30 += z
            ingest += 1

        cutoff1 = decision - WINDOWS_NS[0]
        cutoff5 = decision - WINDOWS_NS[1]
        cutoff30 = decision - WINDOWS_NS[2]

        while h1 < ingest and int(times[h1]) <= cutoff1:
            v1 -= float(sq[h1])
            h1 += 1
        while h5 < ingest and int(times[h5]) <= cutoff5:
            v5 -= float(sq[h5])
            h5 += 1
        while h30 < ingest and int(times[h30]) <= cutoff30:
            v30 -= float(sq[h30])
            h30 += 1

        out1[di] = 10_000.0 * math.sqrt(max(0.0, v1))
        out5[di] = 10_000.0 * math.sqrt(max(0.0, v5))
        out30[di] = 10_000.0 * math.sqrt(max(0.0, v30))

    out1.setflags(write=False)
    out5.setflags(write=False)
    out30.setflags(write=False)
    return out1, out5, out30


def apply_r10_volatility_amendment(
    surface: r27p5.CompactFeatureSurface,
    base: r27p5.CompiledFeatureResult,
) -> r27p5.CompiledFeatureResult:
    sq = _precompute_cpython_transition_sq(surface)
    decisions = np.asarray(base.decision_local_ns, dtype=np.int64)
    vol1, vol5, vol30 = _r10_rolling_volatility_for_eligible_decisions(
        book_ns=surface.book_local_ns,
        transition_sq=sq,
        decisions=decisions,
    )

    corrected = np.asarray(base.values, dtype=np.float64).copy()
    for feature_index, values in zip(AMENDED_FEATURE_INDICES, (vol1, vol5, vol30)):
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
        raise R27P16Error("value_surface_identity")
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


def validate_r27p16_contract() -> None:
    if PARENT_R27P15_FAILURE_FREEZE_HEAD != "3c3dc535b6805af828cacd01f2ae2db617bee66e":
        raise R27P16Error("parent")
    if CPYTHON_REFERENCE_VERSION != "3.13":
        raise R27P16Error("cpython_version")
    if REFERENCE_SEMANTICS != "R10_ROLLING_FEATURE_ACCUMULATOR":
        raise R27P16Error("reference_semantics")
    if not SUPERSEDES_R27P14_BATCH_WINDOW_AMENDMENT:
        raise R27P16Error("supersession")
    if AMENDED_FEATURE_INDICES != (16, 17, 18):
        raise R27P16Error("feature_indices")
    if AMENDED_FEATURE_NAMES != ("realized_vol_1s", "realized_vol_5s", "realized_vol_30s"):
        raise R27P16Error("feature_names")
    if WINDOWS_NS != (1_000_000_000, 5_000_000_000, 30_000_000_000):
        raise R27P16Error("windows")
    if not EXACT_OTHER_FEATURE_BYTES_REQUIRED or not ELIGIBLE_DECISIONS_ONLY or not PREELIGIBLE_ADVANCE_FORBIDDEN:
        raise R27P16Error("semantic_guard")

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
        raise R27P16Error("execution_surface_open")


__all__ = [
    "AMENDED_FEATURE_INDICES",
    "AMENDED_FEATURE_NAMES",
    "AmendmentAudit",
    "apply_r10_volatility_amendment",
    "audit_amendment",
    "validate_r27p16_contract",
]

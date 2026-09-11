from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np

from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P6A"
DESIGN_VERSION = "full-context-fusion-midpoint-transport-v1"
PARENT_R27P6_HEAD = "24d1455617650f24f7c2ed3fcd88c0a836df38e0"

EXACT_STRUCTURED_MIDPOINT_BYTES = True
NO_SYNTHETIC_BID_ASK_RECONSTRUCTION = True
FILE_BACKED_MIDPOINT_SURFACE_REQUIRED = True
RAW_EVENT_PASS_COUNT = 1

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


class R27P6AError(RuntimeError):
    pass


def _write_midpoint_index(
    *,
    exchange_ns: np.ndarray,
    mid_tick_sum: np.ndarray,
    source_exchange_observed_through_ns: int,
    scratch_root: Path,
    index_name: str,
) -> r20.MidpointIndexHandle:
    root = Path(scratch_root)
    if not index_name or "/" in index_name or "\\" in index_name or index_name in (".", ".."):
        raise R27P6AError("midpoint_index_name")
    root.mkdir(parents=True, exist_ok=True)
    final = root / index_name
    temp = root / (index_name + ".tmp")
    if final.exists():
        raise R27P6AError(f"midpoint_index_exists:{final}")
    if temp.exists():
        raise R27P6AError(f"midpoint_temp_exists:{temp}")

    times = np.asarray(exchange_ns, dtype="<i8")
    sums = np.asarray(mid_tick_sum, dtype="<i8")
    if times.ndim != 1 or sums.ndim != 1 or times.shape != sums.shape or times.size <= 0:
        raise R27P6AError("midpoint_shape")
    if bool(np.any(times < 0)):
        raise R27P6AError("midpoint_exchange_negative")
    if times.size > 1 and bool(np.any(times[1:] <= times[:-1])):
        raise R27P6AError("midpoint_exchange_not_strict")
    if bool(np.any(sums <= 0)):
        raise R27P6AError("midpoint_tick_sum")

    observed_through = int(source_exchange_observed_through_ns)
    if observed_through < int(times[-1]):
        raise R27P6AError("midpoint_observed_through")

    records = np.empty(times.size, dtype=r20.MIDPOINT_RECORD_DTYPE)
    records["exchange_ns"] = times
    records["mid_tick_sum"] = sums
    raw = records.tobytes(order="C")
    expected_bytes = int(times.size) * r20.MIDPOINT_RECORD_BYTES
    if len(raw) != expected_bytes:
        raise R27P6AError("midpoint_bytes")

    digest = hashlib.sha256(raw).hexdigest()
    with temp.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    if int(temp.stat().st_size) != expected_bytes:
        temp.unlink(missing_ok=True)
        raise R27P6AError("midpoint_temp_bytes")
    os.replace(temp, final)
    r20._fsync_directory(final.parent)

    mm = np.memmap(
        final,
        dtype=r20.MIDPOINT_RECORD_DTYPE,
        mode="r",
        shape=(int(times.size),),
    )
    if bool(mm.flags.writeable):
        raise R27P6AError("midpoint_index_writeable")

    return r20.MidpointIndexHandle(
        path=final,
        records=mm,
        count=int(times.size),
        bytes=expected_bytes,
        sha256=digest,
        source_exchange_observed_through_ns=observed_through,
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
        raise R27P6AError("requested_decision_grid_empty")

    raw = r27p6.run_fused_raw_surface(a, kernel=raw_kernel)
    compact = r27p5.CompactFeatureSurface(
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
    compiled = r27p5.run_compiled_feature_kernel(compact, requested, kernel=feature_kernel)

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
        raise R27P6AError("leading_preeligible_count")
    if cache.decision_count != int(requested.size) - first_eligible_index:
        raise R27P6AError("eligible_count")

    summary = r19.FeatureCacheBuildSummary(
        requested_decision_count=int(requested.size),
        leading_preeligible_count=first_eligible_index,
        eligible_decision_count=cache.decision_count,
        first_requested_local_ns=int(requested[0]),
        first_eligible_local_ns=int(cache.decision_local_ns[0]),
        last_eligible_local_ns=int(cache.decision_local_ns[-1]),
        raw_event_pass_count=1,
    )

    index = _write_midpoint_index(
        exchange_ns=raw.midpoint_exchange_ns,
        mid_tick_sum=raw.midpoint_tick_sum,
        source_exchange_observed_through_ns=raw.source_exchange_observed_through_ns,
        scratch_root=Path(scratch_root),
        index_name=midpoint_index_name,
    )

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


def validate_r27p6a_contract() -> None:
    r27p6.validate_r27p6_contract()
    if PARENT_R27P6_HEAD != "24d1455617650f24f7c2ed3fcd88c0a836df38e0":
        raise R27P6AError("parent")
    if RAW_EVENT_PASS_COUNT != 1:
        raise R27P6AError("raw_event_pass_count")
    required = (
        EXACT_STRUCTURED_MIDPOINT_BYTES,
        NO_SYNTHETIC_BID_ASK_RECONSTRUCTION,
        FILE_BACKED_MIDPOINT_SURFACE_REQUIRED,
        not REAL_HISTORICAL_BENCHMARK_AUTHORIZED,
        not FULL_JAN_JUL_RERUN_AUTHORIZED,
        not DURABLE_CONTEXT_WRITE_AUTHORIZED,
    )
    if not all(required):
        raise R27P6AError("required_guard")
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
        raise R27P6AError("execution_surface_open")


__all__ = [
    "assert_full_context_synthetic_parity",
    "build_fused_day_context",
    "validate_r27p6a_contract",
]

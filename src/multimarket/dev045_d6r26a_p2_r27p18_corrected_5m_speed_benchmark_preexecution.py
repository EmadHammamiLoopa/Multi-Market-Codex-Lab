from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

import numpy as np

from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p6a_full_context_fusion_midpoint_transport as r27p6a
from multimarket import dev045_d6r26a_p2_r27p9_cpython313_float_sum_parity_amendment as r27p9
from multimarket import dev045_d6r26a_p2_r27p11_amended_bounded_speed_benchmark_preexecution as r27p11
from multimarket import dev045_d6r26a_p2_r27p16_r10_rolling_volatility_parity_amendment as r27p16

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P18"
DESIGN_VERSION = "corrected-5m-speed-benchmark-preexecution-v1"
PARENT_R27P17_FREEZE_HEAD = "49217fb20d0aa372ed77ae746c3fca3b1fb6ca13"

AUTH_ENV = "DEV045_D6R26A_P2_R27P18_AUTHORIZE"
AUTH_TOKEN = "YES_CORRECTED_REAL_5M_SPEED_BENCHMARK_PREATTEMPT"

SOURCE_DAY = r27p11.SOURCE_DAY
SOURCE_PATH = r27p11.SOURCE_PATH
SOURCE_ROWS = r27p11.SOURCE_ROWS
SOURCE_BYTES = r27p11.SOURCE_BYTES
SOURCE_SHA256 = r27p11.SOURCE_SHA256
SOURCE_DAY_START_NS = r27p11.SOURCE_DAY_START_NS
SOURCE_DAY_END_EXCLUSIVE_NS = r27p11.SOURCE_DAY_END_EXCLUSIVE_NS

PREFIX_ROWS = 5_000_000
GATE_PREFIX_ROWS = PREFIX_ROWS
MAX_BENCHMARK_ROWS = PREFIX_ROWS
MIN_ACCEPTED_SPEEDUP = r27p0.MIN_ACCEPTED_SPEEDUP

REFERENCE_IMPLEMENTATION = r27p0.REFERENCE_IMPLEMENTATION
CANDIDATE_IMPLEMENTATION = "R27P6A_PLUS_R27P9_L5_PLUS_R27P16_R10_VOLATILITY"

REAL_HISTORICAL_BENCHMARK_AUTHORIZED = True
REAL_HISTORICAL_BENCHMARK_REQUIRES_EXPLICIT_AUTHORIZATION = True
BENCHMARK_SCOPE_ONE_FROZEN_SOURCE_ONLY = True
BENCHMARK_PREFIX_ONLY = True
FULL_CONTEXT_OVER_BOUNDED_PREFIX_ONLY = True
FULL_DAY_CONTEXT_BUILD_AUTHORIZED = False
EXACT_CONTEXT_PARITY_REQUIRED = True
EXACT_MIDPOINT_BYTES_REQUIRED = True
R27P9_L5_AMENDMENT_REQUIRED = True
R27P16_VOLATILITY_AMENDMENT_REQUIRED = True
JIT_COMPILE_TIME_EXCLUDED = True
PARITY_COMPARISON_EXCLUDED_FROM_TIMING = True
DIGEST_COMPUTATION_EXCLUDED_FROM_TIMING = True
SOURCE_READ_ONLY_REQUIRED = True
EPHEMERAL_SCRATCH_ONLY = True
BENCHMARK_MANIFEST_WRITE_AUTHORIZED = False

R27P17_RERUN_AUTHORIZED = False
R27P15_RERUN_AUTHORIZED = False
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


class R27P18Error(RuntimeError):
    pass


@dataclass(frozen=True)
class SpeedBenchmark:
    prefix_rows: int
    reference_seconds: float
    candidate_seconds: float
    speedup: float
    parity: bool
    l5_changed_cells: int
    volatility_changed_cells: int
    reference_digest: r27p0.ContextDigest
    candidate_digest: r27p0.ContextDigest


@dataclass(frozen=True)
class BenchmarkRun:
    experiment_id: str
    design_version: str
    source_day: str
    source_rows: int
    source_bytes: int
    source_sha256: str
    observation: SpeedBenchmark
    min_accepted_speedup: float
    gate_pass: bool
    p2_attempt_consumed: bool


def real_benchmark_authorized(environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(AUTH_ENV) == AUTH_TOKEN


def _require_real_benchmark_authorized(environ: dict[str, str] | None = None) -> None:
    if not real_benchmark_authorized(environ):
        raise R27P18Error("authorization")


def _close_source_memmap(events: np.ndarray) -> None:
    mm = getattr(events, "_mmap", None)
    if mm is not None:
        mm.close()


def _compact_from_raw(raw: r27p6.FusedRawSurface) -> r27p5.CompactFeatureSurface:
    return r27p5.CompactFeatureSurface(
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


def build_corrected_fused_day_context(
    events: np.ndarray,
    *,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
    scratch_root: Path,
    midpoint_index_name: str = "exchange_midpoints.bin",
    raw_kernel=None,
    base_feature_kernel=None,
    l5_amendment_kernel=None,
) -> tuple[r20.DayContextBuildResult, int, int]:
    a = r19._validate_event_surface(events)
    bounds = r17.derive_feed_bounds(
        a,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
    )
    requested = np.asarray(r17.build_shared_decision_grid(bounds=bounds), dtype="<i8")
    if requested.size <= 0:
        raise R27P18Error("requested_decision_grid_empty")

    raw = r27p6.run_fused_raw_surface(a, kernel=raw_kernel)
    surface = _compact_from_raw(raw)

    base = r27p5.run_compiled_feature_kernel(surface, requested, kernel=base_feature_kernel)
    l5 = r27p9.run_amended_feature_kernel(
        surface,
        requested,
        base_kernel=base_feature_kernel,
        amendment_kernel=l5_amendment_kernel,
    )
    l5_audit = r27p9.audit_amendment(base, l5)
    if not l5_audit.other_feature_bytes_equal:
        raise R27P18Error("l5_other_feature_bytes_changed")
    if any(index != r27p9.AMENDED_FEATURE_INDEX for index in l5_audit.changed_feature_indices):
        raise R27P18Error("l5_amendment_scope")

    corrected = r27p16.apply_r10_volatility_amendment(surface, l5)
    vol_audit = r27p16.audit_amendment(l5, corrected)
    if not vol_audit.other_feature_bytes_equal:
        raise R27P18Error("volatility_other_feature_bytes_changed")
    if any(index not in r27p16.AMENDED_FEATURE_INDICES for index in vol_audit.changed_feature_indices):
        raise R27P18Error("volatility_amendment_scope")

    decisions = np.asarray(corrected.decision_local_ns, dtype="<i8")
    bids = np.asarray(corrected.best_bid_tick, dtype="<i8")
    asks = np.asarray(corrected.best_ask_tick, dtype="<i8")
    values = np.asarray(corrected.values, dtype=r17.FEATURE_CACHE_VALUE_DTYPE)
    for array in (decisions, bids, asks, values):
        array.setflags(write=False)

    cache = r18.DenseFeatureCache(
        decision_local_ns=decisions,
        best_bid_tick=bids,
        best_ask_tick=asks,
        values=values,
    )
    r18.validate_dense_feature_cache(cache)

    first_eligible_index = int(corrected.leading_preeligible_count)
    if first_eligible_index < 0 or first_eligible_index >= int(requested.size):
        raise R27P18Error("leading_preeligible_count")
    if cache.decision_count != int(requested.size) - first_eligible_index:
        raise R27P18Error("eligible_count")

    summary = r19.FeatureCacheBuildSummary(
        requested_decision_count=int(requested.size),
        leading_preeligible_count=first_eligible_index,
        eligible_decision_count=cache.decision_count,
        first_requested_local_ns=int(requested[0]),
        first_eligible_local_ns=int(cache.decision_local_ns[0]),
        last_eligible_local_ns=int(cache.decision_local_ns[-1]),
        raw_event_pass_count=1,
    )

    index = r27p6a._write_midpoint_index(
        exchange_ns=raw.midpoint_exchange_ns,
        mid_tick_sum=raw.midpoint_tick_sum,
        source_exchange_observed_through_ns=raw.source_exchange_observed_through_ns,
        scratch_root=Path(scratch_root),
        index_name=midpoint_index_name,
    )

    return (
        r20.DayContextBuildResult(
            bounds=bounds,
            feature_cache=cache,
            feature_summary=summary,
            midpoint_index=index,
            raw_event_pass_count=1,
        ),
        int(l5_audit.changed_cells),
        int(vol_audit.changed_cells),
    )


def _build_warmed_candidate_kernels():
    raw_kernel = r27p6.build_fused_raw_kernel()
    base_feature_kernel = r27p5.build_feature_kernel()
    l5_amendment_kernel = r27p9.build_l5_obi_amendment_kernel()
    fixture = r20.make_synthetic_dual_context_fixture()
    with TemporaryDirectory(prefix="dev045_r27p18_warm_") as root:
        context, _, _ = build_corrected_fused_day_context(
            fixture,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
            scratch_root=Path(root),
            raw_kernel=raw_kernel,
            base_feature_kernel=base_feature_kernel,
            l5_amendment_kernel=l5_amendment_kernel,
        )
        r20.close_midpoint_index(context.midpoint_index)
    return raw_kernel, base_feature_kernel, l5_amendment_kernel


def benchmark_loaded_prefix(
    events: np.ndarray,
    *,
    prefix_rows: int,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
    scratch_root: Path,
    raw_kernel=None,
    base_feature_kernel=None,
    l5_amendment_kernel=None,
) -> SpeedBenchmark:
    a = np.asarray(events)
    if a.ndim != 1 or a.size <= 0:
        raise R27P18Error("events")
    n = int(prefix_rows)
    if n != PREFIX_ROWS or n > int(a.size):
        raise R27P18Error("prefix_rows")

    prefix = a[:n]
    root = Path(scratch_root)
    reference = None
    candidate = None
    try:
        t0 = perf_counter()
        reference = r20.build_once_day_context(
            prefix,
            nominal_day_start_local_ns=int(nominal_day_start_local_ns),
            nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
            scratch_root=root / "reference",
        )
        reference_seconds = perf_counter() - t0

        t0 = perf_counter()
        candidate, l5_changed_cells, volatility_changed_cells = build_corrected_fused_day_context(
            prefix,
            nominal_day_start_local_ns=int(nominal_day_start_local_ns),
            nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
            scratch_root=root / "candidate",
            raw_kernel=raw_kernel,
            base_feature_kernel=base_feature_kernel,
            l5_amendment_kernel=l5_amendment_kernel,
        )
        candidate_seconds = perf_counter() - t0

        if reference_seconds <= 0.0 or candidate_seconds <= 0.0:
            raise R27P18Error("elapsed")

        r27p0.assert_exact_context_parity(reference, candidate)
        reference_digest = r27p0.digest_day_context(reference)
        candidate_digest = r27p0.digest_day_context(candidate)
        if reference_digest != candidate_digest:
            raise R27P18Error("context_digest")
        if (
            reference.midpoint_index.sha256 != candidate.midpoint_index.sha256
            or reference.midpoint_index.bytes != candidate.midpoint_index.bytes
        ):
            raise R27P18Error("midpoint_bytes")

        return SpeedBenchmark(
            prefix_rows=n,
            reference_seconds=float(reference_seconds),
            candidate_seconds=float(candidate_seconds),
            speedup=float(reference_seconds / candidate_seconds),
            parity=True,
            l5_changed_cells=int(l5_changed_cells),
            volatility_changed_cells=int(volatility_changed_cells),
            reference_digest=reference_digest,
            candidate_digest=candidate_digest,
        )
    finally:
        if reference is not None and not reference.midpoint_index.closed:
            r20.close_midpoint_index(reference.midpoint_index)
        if candidate is not None and not candidate.midpoint_index.closed:
            r20.close_midpoint_index(candidate.midpoint_index)


def run_real_benchmark(*, environ: dict[str, str] | None = None) -> BenchmarkRun:
    validate_r27p18_contract()
    _require_real_benchmark_authorized(environ)
    r27p2._validate_preattempt_state()
    events = r27p2._verify_source_identity()
    try:
        if bool(events.flags.writeable):
            raise R27P18Error("source_writeable")
        raw_kernel, base_feature_kernel, l5_amendment_kernel = _build_warmed_candidate_kernels()
        with TemporaryDirectory(prefix="dev045_r27p18_real_") as root:
            observation = benchmark_loaded_prefix(
                events,
                prefix_rows=PREFIX_ROWS,
                nominal_day_start_local_ns=SOURCE_DAY_START_NS,
                nominal_day_end_exclusive_local_ns=SOURCE_DAY_END_EXCLUSIVE_NS,
                scratch_root=Path(root),
                raw_kernel=raw_kernel,
                base_feature_kernel=base_feature_kernel,
                l5_amendment_kernel=l5_amendment_kernel,
            )
    finally:
        _close_source_memmap(events)

    gate_pass = bool(observation.speedup >= MIN_ACCEPTED_SPEEDUP)
    result = BenchmarkRun(
        experiment_id=EXPERIMENT_ID,
        design_version=DESIGN_VERSION,
        source_day=SOURCE_DAY,
        source_rows=SOURCE_ROWS,
        source_bytes=SOURCE_BYTES,
        source_sha256=SOURCE_SHA256,
        observation=observation,
        min_accepted_speedup=float(MIN_ACCEPTED_SPEEDUP),
        gate_pass=gate_pass,
        p2_attempt_consumed=False,
    )

    print(f"R27P18_SOURCE_IDENTITY=PASS DAY={SOURCE_DAY} ROWS={SOURCE_ROWS} BYTES={SOURCE_BYTES} SHA256={SOURCE_SHA256}")
    print(f"R27P18_PREFIX_ROWS={observation.prefix_rows}")
    print(f"R27P18_REFERENCE_SECONDS={observation.reference_seconds:.6f}")
    print(f"R27P18_CANDIDATE_SECONDS={observation.candidate_seconds:.6f}")
    print(f"R27P18_SPEEDUP={observation.speedup:.3f}")
    print("R27P18_EXACT_CONTEXT_PARITY=PASS")
    print(f"R27P18_L5_AMENDMENT_CHANGED_CELLS={observation.l5_changed_cells}")
    print(f"R27P18_VOLATILITY_AMENDMENT_CHANGED_CELLS={observation.volatility_changed_cells}")
    print(f"R27P18_MIN_REQUIRED_SPEEDUP={MIN_ACCEPTED_SPEEDUP:.1f}")
    print(f"R27P18_SPEED_GATE={'PASS' if gate_pass else 'FAIL'}")
    print("JIT_COMPILE_TIME_EXCLUDED=YES")
    print("PARITY_COMPARISON_EXCLUDED_FROM_TIMING=YES")
    print("DIGEST_COMPUTATION_EXCLUDED_FROM_TIMING=YES")
    print("BENCHMARK_MANIFEST_WRITTEN=NO")
    print("P2_ATTEMPT_CONSUMED=NO")
    print("FULL_JAN_JUL_RERUN=NO")
    print("SIMULATOR_RUN=NO")
    print("MODEL_FIT=NO")
    print("PNL=NO")
    print("MARKET_RAW_ARCHIVE_OPENED=NO")
    return result


def validate_r27p18_contract() -> None:
    r27p16.validate_r27p16_contract()
    r27p9.validate_r27p9_contract()
    if PARENT_R27P17_FREEZE_HEAD != "49217fb20d0aa372ed77ae746c3fca3b1fb6ca13":
        raise R27P18Error("parent")
    if PREFIX_ROWS != 5_000_000 or GATE_PREFIX_ROWS != PREFIX_ROWS or MAX_BENCHMARK_ROWS != PREFIX_ROWS:
        raise R27P18Error("prefix")
    if MIN_ACCEPTED_SPEEDUP != r27p0.MIN_ACCEPTED_SPEEDUP:
        raise R27P18Error("speed_gate")
    if CANDIDATE_IMPLEMENTATION != "R27P6A_PLUS_R27P9_L5_PLUS_R27P16_R10_VOLATILITY":
        raise R27P18Error("candidate_identity")

    required = (
        REAL_HISTORICAL_BENCHMARK_AUTHORIZED,
        REAL_HISTORICAL_BENCHMARK_REQUIRES_EXPLICIT_AUTHORIZATION,
        BENCHMARK_SCOPE_ONE_FROZEN_SOURCE_ONLY,
        BENCHMARK_PREFIX_ONLY,
        FULL_CONTEXT_OVER_BOUNDED_PREFIX_ONLY,
        EXACT_CONTEXT_PARITY_REQUIRED,
        EXACT_MIDPOINT_BYTES_REQUIRED,
        R27P9_L5_AMENDMENT_REQUIRED,
        R27P16_VOLATILITY_AMENDMENT_REQUIRED,
        JIT_COMPILE_TIME_EXCLUDED,
        PARITY_COMPARISON_EXCLUDED_FROM_TIMING,
        DIGEST_COMPUTATION_EXCLUDED_FROM_TIMING,
        SOURCE_READ_ONLY_REQUIRED,
        EPHEMERAL_SCRATCH_ONLY,
        not FULL_DAY_CONTEXT_BUILD_AUTHORIZED,
        not BENCHMARK_MANIFEST_WRITE_AUTHORIZED,
    )
    if not all(required):
        raise R27P18Error("required_guard")

    forbidden = (
        R27P17_RERUN_AUTHORIZED,
        R27P15_RERUN_AUTHORIZED,
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
        raise R27P18Error("execution_surface_open")


def main() -> int:
    try:
        result = run_real_benchmark()
    except Exception as exc:
        print(f"R27P18_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("P2_ATTEMPT_CONSUMED=NO")
        print("FULL_JAN_JUL_RERUN=NO")
        print("MARKET_RAW_ARCHIVE_OPENED=NO")
        return 2
    if not result.gate_pass:
        print("R27P18_RESULT=FAIL REASON=speed_gate")
        return 3
    print("R27P18_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

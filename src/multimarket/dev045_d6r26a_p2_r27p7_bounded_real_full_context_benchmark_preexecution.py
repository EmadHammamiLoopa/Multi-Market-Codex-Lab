from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

import numpy as np

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p6a_full_context_fusion_midpoint_transport as r27p6a

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P7"
DESIGN_VERSION = "bounded-real-full-context-benchmark-preexecution-v1"
PARENT_R27P6A_HEAD = "c67934077bd04351030e321f99717b37c2e1c096"

AUTH_ENV = "DEV045_D6R26A_P2_R27P7_AUTHORIZE"
AUTH_TOKEN = "YES_BOUNDED_JAN_FULL_CONTEXT_BENCHMARK_PREATTEMPT"

SOURCE_DAY = r27p2.SOURCE_DAY
SOURCE_PATH = r27p2.SOURCE_PATH
SOURCE_ROWS = r27p2.SOURCE_ROWS
SOURCE_BYTES = r27p2.SOURCE_BYTES
SOURCE_SHA256 = r27p2.SOURCE_SHA256
SOURCE_DAY_START_NS = 1_767_225_600_000_000_000
SOURCE_DAY_END_EXCLUSIVE_NS = 1_767_312_000_000_000_000

PREFIX_ROWS = r27p2.PREFIX_ROWS
GATE_PREFIX_ROWS = r27p2.GATE_PREFIX_ROWS
MAX_BENCHMARK_ROWS = GATE_PREFIX_ROWS
MIN_ACCEPTED_SPEEDUP = r27p0.MIN_ACCEPTED_SPEEDUP

REFERENCE_IMPLEMENTATION = r27p0.REFERENCE_IMPLEMENTATION
CANDIDATE_IMPLEMENTATION = "R27P6A_NUMBA_FUSED_FULL_CONTEXT"

REAL_HISTORICAL_BENCHMARK_AUTHORIZED = True
REAL_HISTORICAL_BENCHMARK_REQUIRES_EXPLICIT_AUTHORIZATION = True
BENCHMARK_SCOPE_ONE_FROZEN_SOURCE_ONLY = True
BENCHMARK_PREFIX_ONLY = True
FULL_CONTEXT_OVER_BOUNDED_PREFIX_ONLY = True
FULL_DAY_CONTEXT_BUILD_AUTHORIZED = False
EXACT_R20_CONTEXT_PARITY_REQUIRED = True
EXACT_MIDPOINT_BYTES_REQUIRED = True
JIT_COMPILE_TIME_EXCLUDED = True
SOURCE_READ_ONLY_REQUIRED = True
EPHEMERAL_SCRATCH_ONLY = True
BENCHMARK_MANIFEST_WRITE_AUTHORIZED = False

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


class R27P7Error(RuntimeError):
    pass


@dataclass(frozen=True)
class FullContextBenchmark:
    prefix_rows: int
    reference_seconds: float
    candidate_seconds: float
    speedup: float
    parity: bool
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
    prefixes: tuple[FullContextBenchmark, ...]
    gate_prefix_rows: int
    min_accepted_speedup: float
    observed_gate_speedup: float
    gate_pass: bool
    p2_attempt_consumed: bool


def real_benchmark_authorized(environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(AUTH_ENV) == AUTH_TOKEN


def _require_real_benchmark_authorized(
    environ: dict[str, str] | None = None,
) -> None:
    if not real_benchmark_authorized(environ):
        raise R27P7Error("authorization")


def _close_source_memmap(events: np.ndarray) -> None:
    mm = getattr(events, "_mmap", None)
    if mm is not None:
        mm.close()


def _build_warmed_candidate_kernels():
    raw_kernel = r27p6.build_fused_raw_kernel()
    feature_kernel = r27p5.build_feature_kernel()
    fixture = r20.make_synthetic_dual_context_fixture()
    with TemporaryDirectory(prefix="dev045_r27p7_warm_") as root:
        context = r27p6a.build_fused_day_context(
            fixture,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
            scratch_root=Path(root),
            raw_kernel=raw_kernel,
            feature_kernel=feature_kernel,
        )
        r20.close_midpoint_index(context.midpoint_index)
    return raw_kernel, feature_kernel


def benchmark_loaded_prefix(
    events: np.ndarray,
    *,
    prefix_rows: int,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
    scratch_root: Path,
    raw_kernel=None,
    feature_kernel=None,
) -> FullContextBenchmark:
    a = np.asarray(events)
    if a.ndim != 1 or a.size <= 0:
        raise R27P7Error("events")
    n = int(prefix_rows)
    if n <= 0 or n > int(a.size) or n > MAX_BENCHMARK_ROWS:
        raise R27P7Error("prefix_rows")

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
        candidate = r27p6a.build_fused_day_context(
            prefix,
            nominal_day_start_local_ns=int(nominal_day_start_local_ns),
            nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
            scratch_root=root / "candidate",
            raw_kernel=raw_kernel,
            feature_kernel=feature_kernel,
        )
        candidate_seconds = perf_counter() - t0

        if reference_seconds <= 0.0 or candidate_seconds <= 0.0:
            raise R27P7Error("elapsed")

        r27p0.assert_exact_context_parity(reference, candidate)
        reference_digest = r27p0.digest_day_context(reference)
        candidate_digest = r27p0.digest_day_context(candidate)
        if reference_digest != candidate_digest:
            raise R27P7Error("context_digest")
        if (
            reference.midpoint_index.sha256 != candidate.midpoint_index.sha256
            or reference.midpoint_index.bytes != candidate.midpoint_index.bytes
        ):
            raise R27P7Error("midpoint_bytes")

        return FullContextBenchmark(
            prefix_rows=n,
            reference_seconds=float(reference_seconds),
            candidate_seconds=float(candidate_seconds),
            speedup=float(reference_seconds / candidate_seconds),
            parity=True,
            reference_digest=reference_digest,
            candidate_digest=candidate_digest,
        )
    finally:
        if reference is not None and not reference.midpoint_index.closed:
            r20.close_midpoint_index(reference.midpoint_index)
        if candidate is not None and not candidate.midpoint_index.closed:
            r20.close_midpoint_index(candidate.midpoint_index)


def run_real_benchmark(
    *,
    environ: dict[str, str] | None = None,
) -> BenchmarkRun:
    validate_r27p7_contract()
    # Authorization is checked before any pre-attempt filesystem probe,
    # source stat/hash, mmap open, JIT warm-up, or scratch creation.
    _require_real_benchmark_authorized(environ)

    r27p2._validate_preattempt_state()
    events = r27p2._verify_source_identity()
    try:
        if bool(events.flags.writeable):
            raise R27P7Error("source_writeable")
        raw_kernel, feature_kernel = _build_warmed_candidate_kernels()

        with TemporaryDirectory(prefix="dev045_r27p7_real_") as root:
            observations = tuple(
                benchmark_loaded_prefix(
                    events,
                    prefix_rows=n,
                    nominal_day_start_local_ns=SOURCE_DAY_START_NS,
                    nominal_day_end_exclusive_local_ns=SOURCE_DAY_END_EXCLUSIVE_NS,
                    scratch_root=Path(root) / str(n),
                    raw_kernel=raw_kernel,
                    feature_kernel=feature_kernel,
                )
                for n in PREFIX_ROWS
            )
    finally:
        _close_source_memmap(events)

    gate = next(item for item in observations if item.prefix_rows == GATE_PREFIX_ROWS)
    gate_pass = bool(gate.speedup >= MIN_ACCEPTED_SPEEDUP)
    result = BenchmarkRun(
        experiment_id=EXPERIMENT_ID,
        design_version=DESIGN_VERSION,
        source_day=SOURCE_DAY,
        source_rows=SOURCE_ROWS,
        source_bytes=SOURCE_BYTES,
        source_sha256=SOURCE_SHA256,
        prefixes=observations,
        gate_prefix_rows=GATE_PREFIX_ROWS,
        min_accepted_speedup=float(MIN_ACCEPTED_SPEEDUP),
        observed_gate_speedup=float(gate.speedup),
        gate_pass=gate_pass,
        p2_attempt_consumed=False,
    )

    print(
        f"R27P7_SOURCE_IDENTITY=PASS ROWS={SOURCE_ROWS} "
        f"BYTES={SOURCE_BYTES} SHA256={SOURCE_SHA256}"
    )
    for item in observations:
        print(
            f"R27P7_PREFIX={item.prefix_rows} "
            f"R20_S={item.reference_seconds:.6f} "
            f"R27P6A_S={item.candidate_seconds:.6f} "
            f"SPEEDUP={item.speedup:.3f} PARITY=PASS"
        )
    print(f"R27P7_GATE_SPEEDUP={gate.speedup:.3f}")
    print(f"R27P7_MIN_REQUIRED_SPEEDUP={MIN_ACCEPTED_SPEEDUP:.1f}")
    print(f"R27P7_FULL_CONTEXT_GATE={'PASS' if gate_pass else 'FAIL'}")
    print("BENCHMARK_MANIFEST_WRITTEN=NO")
    print("P2_ATTEMPT_CONSUMED=NO")
    print("FULL_JAN_JUL_RERUN=NO")
    print("SIMULATOR_RUN=NO")
    print("MODEL_FIT=NO")
    print("PNL=NO")
    return result


def validate_r27p7_contract() -> None:
    r27p0.validate_r27p0_contract()
    r27p2.validate_r27p2_contract()
    r27p6a.validate_r27p6a_contract()

    if PARENT_R27P6A_HEAD != "c67934077bd04351030e321f99717b37c2e1c096":
        raise R27P7Error("parent")
    if (
        SOURCE_DAY != r27p2.SOURCE_DAY
        or SOURCE_PATH != r27p2.SOURCE_PATH
        or SOURCE_ROWS != r27p2.SOURCE_ROWS
        or SOURCE_BYTES != r27p2.SOURCE_BYTES
        or SOURCE_SHA256 != r27p2.SOURCE_SHA256
    ):
        raise R27P7Error("source_identity")
    if PREFIX_ROWS != r27p2.PREFIX_ROWS or GATE_PREFIX_ROWS != PREFIX_ROWS[-1]:
        raise R27P7Error("prefix_plan")
    if MAX_BENCHMARK_ROWS != GATE_PREFIX_ROWS:
        raise R27P7Error("max_rows")
    if MIN_ACCEPTED_SPEEDUP != 10.0:
        raise R27P7Error("speedup_gate")
    if r27p6a.REAL_HISTORICAL_BENCHMARK_AUTHORIZED is not False:
        raise R27P7Error("r27p6a_historical_surface_changed")

    required = (
        REAL_HISTORICAL_BENCHMARK_AUTHORIZED,
        REAL_HISTORICAL_BENCHMARK_REQUIRES_EXPLICIT_AUTHORIZATION,
        BENCHMARK_SCOPE_ONE_FROZEN_SOURCE_ONLY,
        BENCHMARK_PREFIX_ONLY,
        FULL_CONTEXT_OVER_BOUNDED_PREFIX_ONLY,
        not FULL_DAY_CONTEXT_BUILD_AUTHORIZED,
        EXACT_R20_CONTEXT_PARITY_REQUIRED,
        EXACT_MIDPOINT_BYTES_REQUIRED,
        JIT_COMPILE_TIME_EXCLUDED,
        SOURCE_READ_ONLY_REQUIRED,
        EPHEMERAL_SCRATCH_ONLY,
        not BENCHMARK_MANIFEST_WRITE_AUTHORIZED,
        not FULL_JAN_JUL_RERUN_AUTHORIZED,
        not DURABLE_CONTEXT_WRITE_AUTHORIZED,
    )
    if not all(required):
        raise R27P7Error("required_guard")

    forbidden = (
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
    )
    if any(forbidden):
        raise R27P7Error("execution_surface_open")


def main() -> int:
    try:
        result = run_real_benchmark()
    except Exception as exc:
        print(f"R27P7_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("BENCHMARK_MANIFEST_WRITTEN=NO")
        print("P2_ATTEMPT_CONSUMED=NO")
        print("FULL_JAN_JUL_RERUN=NO")
        print("SIMULATOR_RUN=NO")
        print("MODEL_FIT=NO")
        print("PNL=NO")
        return 2
    return 0 if result.gate_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AUTH_ENV",
    "AUTH_TOKEN",
    "BenchmarkRun",
    "FullContextBenchmark",
    "GATE_PREFIX_ROWS",
    "MIN_ACCEPTED_SPEEDUP",
    "PREFIX_ROWS",
    "SOURCE_BYTES",
    "SOURCE_DAY",
    "SOURCE_PATH",
    "SOURCE_ROWS",
    "SOURCE_SHA256",
    "benchmark_loaded_prefix",
    "real_benchmark_authorized",
    "run_real_benchmark",
    "validate_r27p7_contract",
]

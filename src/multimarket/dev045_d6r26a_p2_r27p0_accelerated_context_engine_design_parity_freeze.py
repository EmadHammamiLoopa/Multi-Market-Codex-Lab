from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from time import perf_counter
from typing import Callable

import numpy as np

from multimarket import (
    dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P0"
DESIGN_VERSION = "accelerated-context-engine-design-parity-freeze-v1"
PARENT_R26P1_HEAD = "9b6b130a9663f5803c5a986fc22746cb5507fd0b"

REFERENCE_IMPLEMENTATION = "R20_PYTHON_REFERENCE"
ACCELERATION_CANDIDATES = ("NUMBA_JIT", "RUST_PYO3")
MIN_ACCEPTED_SPEEDUP = 10.0

EXACT_OUTPUT_PARITY_REQUIRED = True
BOUNDS_PARITY_REQUIRED = True
FEATURE_SUMMARY_PARITY_REQUIRED = True
DECISION_ARRAY_PARITY_REQUIRED = True
BID_ARRAY_PARITY_REQUIRED = True
ASK_ARRAY_PARITY_REQUIRED = True
FEATURE_VALUES_PARITY_REQUIRED = True
MIDPOINT_RECORD_PARITY_REQUIRED = True
MIDPOINT_METADATA_PARITY_REQUIRED = True
RAW_EVENT_PASS_COUNT_PARITY_REQUIRED = True

ONE_CAUSAL_RAW_EVENT_PASS_REQUIRED = True
LOCAL_GROUP_ORDERING_FROZEN = True
EXCHANGE_GROUP_ORDERING_FROZEN = True
EOF_SEMANTICS_FROZEN = True
FEATURE_WARMUP_AND_ELIGIBILITY_FROZEN = True
MIDPOINT_LAYOUT_FROZEN = True
MARKOUT_ASOF_RULE_FROZEN = True

BOUNDED_SYNTHETIC_BENCHMARK_ONLY = True
REAL_HISTORICAL_BENCHMARK_REQUIRES_SEPARATE_AUTHORIZATION = True
FULL_JAN_JUL_RERUN_FORBIDDEN_IN_R27P0 = True
R26P1_PARTIAL_RESIDUE_PRESERVE_REQUIRED = True
R26P1_PARTIAL_RESIDUE_REUSE_FORBIDDEN = True

P2_ATTEMPT_CONSUMED = False
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_SOURCE_REHASH_AUTHORIZED = False
SIMULATOR_LANE_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False


class R27P0ParityError(RuntimeError):
    pass


@dataclass(frozen=True)
class ContextDigest:
    decision_sha256: str
    best_bid_sha256: str
    best_ask_sha256: str
    feature_values_sha256: str
    midpoint_sha256: str
    midpoint_count: int
    midpoint_bytes: int
    source_exchange_observed_through_ns: int
    raw_event_pass_count: int


@dataclass(frozen=True)
class BenchmarkObservation:
    implementation: str
    event_count: int
    elapsed_seconds: float

    @property
    def events_per_second(self) -> float:
        if self.elapsed_seconds <= 0.0:
            raise R27P0ParityError("benchmark_elapsed")
        if self.event_count <= 0:
            raise R27P0ParityError("benchmark_event_count")
        return float(self.event_count) / float(self.elapsed_seconds)


def _array_sha256(array: np.ndarray) -> str:
    a = np.asarray(array)
    if not a.flags.c_contiguous:
        a = np.ascontiguousarray(a)
    digest = hashlib.sha256()
    digest.update(str(a.dtype).encode("ascii"))
    digest.update(b"|")
    digest.update(repr(tuple(int(x) for x in a.shape)).encode("ascii"))
    digest.update(b"|")
    digest.update(memoryview(a).cast("B"))
    return digest.hexdigest()


def digest_day_context(context: r20.DayContextBuildResult) -> ContextDigest:
    cache = context.feature_cache
    index = context.midpoint_index
    if index.closed:
        raise R27P0ParityError("midpoint_index_closed")
    return ContextDigest(
        decision_sha256=_array_sha256(cache.decision_local_ns),
        best_bid_sha256=_array_sha256(cache.best_bid_tick),
        best_ask_sha256=_array_sha256(cache.best_ask_tick),
        feature_values_sha256=_array_sha256(cache.values),
        midpoint_sha256=str(index.sha256),
        midpoint_count=int(index.count),
        midpoint_bytes=int(index.bytes),
        source_exchange_observed_through_ns=int(
            index.source_exchange_observed_through_ns
        ),
        raw_event_pass_count=int(context.raw_event_pass_count),
    )


def assert_exact_context_parity(
    reference: r20.DayContextBuildResult,
    candidate: r20.DayContextBuildResult,
) -> None:
    if reference.bounds != candidate.bounds:
        raise R27P0ParityError("bounds")
    if reference.feature_summary != candidate.feature_summary:
        raise R27P0ParityError("feature_summary")

    pairs = (
        (
            "decision_local_ns",
            reference.feature_cache.decision_local_ns,
            candidate.feature_cache.decision_local_ns,
        ),
        (
            "best_bid_tick",
            reference.feature_cache.best_bid_tick,
            candidate.feature_cache.best_bid_tick,
        ),
        (
            "best_ask_tick",
            reference.feature_cache.best_ask_tick,
            candidate.feature_cache.best_ask_tick,
        ),
        (
            "feature_values",
            reference.feature_cache.values,
            candidate.feature_cache.values,
        ),
    )
    for name, expected, observed in pairs:
        if expected.dtype != observed.dtype:
            raise R27P0ParityError(f"{name}_dtype")
        if expected.shape != observed.shape:
            raise R27P0ParityError(f"{name}_shape")
        if not np.array_equal(expected, observed):
            raise R27P0ParityError(f"{name}_values")

    left = reference.midpoint_index
    right = candidate.midpoint_index
    if left.closed or right.closed:
        raise R27P0ParityError("midpoint_closed")
    if left.records.dtype != right.records.dtype:
        raise R27P0ParityError("midpoint_dtype")
    if left.records.shape != right.records.shape:
        raise R27P0ParityError("midpoint_shape")
    if not np.array_equal(left.records, right.records):
        raise R27P0ParityError("midpoint_records")
    if int(left.count) != int(right.count):
        raise R27P0ParityError("midpoint_count")
    if int(left.bytes) != int(right.bytes):
        raise R27P0ParityError("midpoint_bytes")
    if str(left.sha256) != str(right.sha256):
        raise R27P0ParityError("midpoint_sha256")
    if int(left.source_exchange_observed_through_ns) != int(
        right.source_exchange_observed_through_ns
    ):
        raise R27P0ParityError("midpoint_observed_through")
    if int(reference.raw_event_pass_count) != int(candidate.raw_event_pass_count):
        raise R27P0ParityError("raw_event_pass_count")

    if digest_day_context(reference) != digest_day_context(candidate):
        raise R27P0ParityError("context_digest")


def benchmark_builder_once(
    *,
    implementation: str,
    builder: Callable[..., r20.DayContextBuildResult],
    events: np.ndarray,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
    scratch_root: Path,
) -> tuple[BenchmarkObservation, r20.DayContextBuildResult]:
    start = perf_counter()
    context = builder(
        events,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(
            nominal_day_end_exclusive_local_ns
        ),
        scratch_root=Path(scratch_root),
    )
    elapsed = perf_counter() - start
    observation = BenchmarkObservation(
        implementation=str(implementation),
        event_count=int(np.asarray(events).size),
        elapsed_seconds=float(elapsed),
    )
    _ = observation.events_per_second
    return observation, context


def speedup(
    *,
    reference: BenchmarkObservation,
    candidate: BenchmarkObservation,
) -> float:
    if reference.event_count != candidate.event_count:
        raise R27P0ParityError("benchmark_event_count_mismatch")
    return candidate.events_per_second / reference.events_per_second


def require_speedup_gate(
    *,
    reference: BenchmarkObservation,
    candidate: BenchmarkObservation,
) -> float:
    observed = speedup(reference=reference, candidate=candidate)
    if observed < MIN_ACCEPTED_SPEEDUP:
        raise R27P0ParityError(
            f"speedup_gate:{observed:.6f}:{MIN_ACCEPTED_SPEEDUP:.6f}"
        )
    return observed


def validate_r27p0_contract() -> None:
    r20.validate_r20_contract()

    if PARENT_R26P1_HEAD != "9b6b130a9663f5803c5a986fc22746cb5507fd0b":
        raise R27P0ParityError("parent")
    if REFERENCE_IMPLEMENTATION != "R20_PYTHON_REFERENCE":
        raise R27P0ParityError("reference")
    if ACCELERATION_CANDIDATES != ("NUMBA_JIT", "RUST_PYO3"):
        raise R27P0ParityError("candidate_set")
    if MIN_ACCEPTED_SPEEDUP != 10.0:
        raise R27P0ParityError("speedup_gate")

    required = (
        EXACT_OUTPUT_PARITY_REQUIRED,
        BOUNDS_PARITY_REQUIRED,
        FEATURE_SUMMARY_PARITY_REQUIRED,
        DECISION_ARRAY_PARITY_REQUIRED,
        BID_ARRAY_PARITY_REQUIRED,
        ASK_ARRAY_PARITY_REQUIRED,
        FEATURE_VALUES_PARITY_REQUIRED,
        MIDPOINT_RECORD_PARITY_REQUIRED,
        MIDPOINT_METADATA_PARITY_REQUIRED,
        RAW_EVENT_PASS_COUNT_PARITY_REQUIRED,
        ONE_CAUSAL_RAW_EVENT_PASS_REQUIRED,
        LOCAL_GROUP_ORDERING_FROZEN,
        EXCHANGE_GROUP_ORDERING_FROZEN,
        EOF_SEMANTICS_FROZEN,
        FEATURE_WARMUP_AND_ELIGIBILITY_FROZEN,
        MIDPOINT_LAYOUT_FROZEN,
        MARKOUT_ASOF_RULE_FROZEN,
        BOUNDED_SYNTHETIC_BENCHMARK_ONLY,
        REAL_HISTORICAL_BENCHMARK_REQUIRES_SEPARATE_AUTHORIZATION,
        FULL_JAN_JUL_RERUN_FORBIDDEN_IN_R27P0,
        R26P1_PARTIAL_RESIDUE_PRESERVE_REQUIRED,
        R26P1_PARTIAL_RESIDUE_REUSE_FORBIDDEN,
    )
    if not all(required):
        raise R27P0ParityError("required_guard")

    if r20.MIDPOINT_RECORD_BYTES != 16:
        raise R27P0ParityError("midpoint_record_bytes")
    if r20.MIDPOINT_BUFFER_ROWS != 65_536:
        raise R27P0ParityError("midpoint_buffer_rows")

    forbidden = (
        P2_ATTEMPT_CONSUMED,
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_SOURCE_REHASH_AUTHORIZED,
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
        raise R27P0ParityError("execution_surface_open")


__all__ = [
    "ACCELERATION_CANDIDATES",
    "BenchmarkObservation",
    "ContextDigest",
    "DESIGN_VERSION",
    "EXPERIMENT_ID",
    "MIN_ACCEPTED_SPEEDUP",
    "P2_ATTEMPT_CONSUMED",
    "R27P0ParityError",
    "assert_exact_context_parity",
    "benchmark_builder_once",
    "digest_day_context",
    "require_speedup_gate",
    "speedup",
    "validate_r27p0_contract",
]

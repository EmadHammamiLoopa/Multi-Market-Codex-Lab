from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p9_cpython313_float_sum_parity_amendment as r27p9
from multimarket import dev045_d6r26a_p2_r27p18_corrected_5m_speed_benchmark_preexecution as r27p18
from multimarket import dev045_d6r26a_p2_r27p29_stateful_windowed_raw_synthetic_parity as r27p29


EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P30"
DESIGN_VERSION = "windowed-raw-corrected-context-synthetic-parity-v1"
PARENT_R27P29_HEAD = "ee53aa5f9fc597e253d73ddbcf1f241a8bd1c9cb"
PARENT_R27P29_CI_RUN = 34716655575
PARENT_R27P29_CI_JOB = 103615006481
PARENT_R27P29_CI_CONCLUSION = "success"
PARENT_R27P29_TEST_COUNT = 4

ARCHITECTURE = "R27P29_WINDOWED_RAW_ADAPTER_INTO_R27P18_CORRECTED_CONTEXT"
WINDOWED_RAW_SEMANTICS_INTEGRATED = True
EXACT_CORRECTED_25_FEATURE_CONTEXT_PARITY_REQUIRED = True
EXACT_CONTEXT_DIGEST_REQUIRED = True
EXACT_MIDPOINT_BYTES_REQUIRED = True
EXACT_L5_CHANGED_CELLS_REQUIRED = True
EXACT_VOLATILITY_CHANGED_CELLS_REQUIRED = True
ONE_LOGICAL_RAW_EVENT_PASS_REQUIRED = True
SYNTHETIC_RAW_REHYDRATION_FOR_PARITY_ONLY = True
DEFAULT_PARITY_CHUNK_ROWS = 3

# This stage proves integration semantics only. R27P18 still consumes an in-memory
# raw surface after the R27P29 bounded producer is rehydrated for the tiny fixture.
# Therefore full-day bounded downstream residency is intentionally NOT claimed.
DOWNSTREAM_FULL_DAY_BOUNDED_CONTEXT_COMPLETE = False
FULL_DAY_BOUNDED_MEMORY_PROVEN = False
GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN = False
CANONICAL_EXECUTION_READY = False
READINESS_BLOCKER = "DOWNSTREAM_CONTEXT_RESIDENCY_NOT_YET_BOUNDED_FOR_FULL_DAY"

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


class R27P30Error(RuntimeError):
    pass


@dataclass(frozen=True)
class CorrectedContextParityResult:
    chunk_rows: int
    input_chunk_count: int
    max_active_output_mapped_bytes: int
    raw_adapter_call_count: int
    exact_context_parity: bool
    exact_context_digest: bool
    exact_midpoint_bytes: bool
    l5_changed_cells: int
    volatility_changed_cells: int
    reference_digest: r27p0.ContextDigest
    candidate_digest: r27p0.ContextDigest


def make_r27p6_signature_adapter(
    root: Path,
    *,
    input_chunk_rows: int = DEFAULT_PARITY_CHUNK_ROWS,
    kernel=None,
):
    target_kernel = r27p29.build_stateful_windowed_raw_kernel() if kernel is None else kernel
    calls: list[r27p29.StatefulRawRun] = []

    def adapter(ev, exch_ts, local_ts, px, qty):
        call_index = len(calls)
        run = r27p29.run_stateful_windowed_raw_from_columns(
            ev,
            exch_ts,
            local_ts,
            px,
            qty,
            root=Path(root) / f"raw_call_{call_index}",
            input_chunk_rows=int(input_chunk_rows),
            kernel=target_kernel,
        )
        if run.error != 0:
            raise R27P30Error(f"raw_error:{run.error}")
        calls.append(run)
        # Synthetic parity bridge only: copy the compact written prefixes back
        # into exact arrays matching the historical R27P6 kernel signature.
        return r27p29._read_group_arrays(run)

    return adapter, calls


def run_synthetic_corrected_context_parity_probe(
    chunk_rows: int = DEFAULT_PARITY_CHUNK_ROWS,
) -> CorrectedContextParityResult:
    validate_r27p30_contract()
    width = int(chunk_rows)
    if width <= 0:
        raise R27P30Error("chunk_rows")

    fixture = r20.make_synthetic_dual_context_fixture()
    reference_raw_kernel = r27p6.build_fused_raw_kernel()
    target_raw_kernel = r27p29.build_stateful_windowed_raw_kernel()
    base_feature_kernel = r27p5.build_feature_kernel()
    l5_amendment_kernel = r27p9.build_l5_obi_amendment_kernel()

    reference = None
    candidate = None
    with TemporaryDirectory(prefix="dev045_r27p30_") as root:
        root_path = Path(root)
        adapter, calls = make_r27p6_signature_adapter(
            root_path / "candidate_raw",
            input_chunk_rows=width,
            kernel=target_raw_kernel,
        )
        try:
            reference, ref_l5, ref_vol = r27p18.build_corrected_fused_day_context(
                fixture,
                nominal_day_start_local_ns=0,
                nominal_day_end_exclusive_local_ns=100_000_000_000,
                scratch_root=root_path / "reference_context",
                raw_kernel=reference_raw_kernel,
                base_feature_kernel=base_feature_kernel,
                l5_amendment_kernel=l5_amendment_kernel,
            )
            candidate, cand_l5, cand_vol = r27p18.build_corrected_fused_day_context(
                fixture,
                nominal_day_start_local_ns=0,
                nominal_day_end_exclusive_local_ns=100_000_000_000,
                scratch_root=root_path / "candidate_context",
                raw_kernel=adapter,
                base_feature_kernel=base_feature_kernel,
                l5_amendment_kernel=l5_amendment_kernel,
            )

            if len(calls) != 1:
                raise R27P30Error("raw_adapter_call_count")
            raw_run = calls[0]
            if raw_run.error != 0:
                raise R27P30Error("raw_error")

            r27p0.assert_exact_context_parity(reference, candidate)
            reference_digest = r27p0.digest_day_context(reference)
            candidate_digest = r27p0.digest_day_context(candidate)
            if reference_digest != candidate_digest:
                raise R27P30Error("context_digest")
            midpoint_equal = bool(
                reference.midpoint_index.sha256 == candidate.midpoint_index.sha256
                and reference.midpoint_index.bytes == candidate.midpoint_index.bytes
            )
            if not midpoint_equal:
                raise R27P30Error("midpoint_bytes")
            if int(ref_l5) != int(cand_l5):
                raise R27P30Error("l5_changed_cells")
            if int(ref_vol) != int(cand_vol):
                raise R27P30Error("volatility_changed_cells")
            if reference.raw_event_pass_count != 1 or candidate.raw_event_pass_count != 1:
                raise R27P30Error("raw_event_pass_count")

            return CorrectedContextParityResult(
                chunk_rows=width,
                input_chunk_count=int(raw_run.input_chunk_count),
                max_active_output_mapped_bytes=int(raw_run.max_active_output_mapped_bytes),
                raw_adapter_call_count=1,
                exact_context_parity=True,
                exact_context_digest=True,
                exact_midpoint_bytes=True,
                l5_changed_cells=int(cand_l5),
                volatility_changed_cells=int(cand_vol),
                reference_digest=reference_digest,
                candidate_digest=candidate_digest,
            )
        finally:
            if reference is not None and not reference.midpoint_index.closed:
                r20.close_midpoint_index(reference.midpoint_index)
            if candidate is not None and not candidate.midpoint_index.closed:
                r20.close_midpoint_index(candidate.midpoint_index)


def validate_r27p30_contract() -> None:
    r27p29.validate_r27p29_contract()
    r27p18.validate_r27p18_contract()
    if PARENT_R27P29_HEAD != "ee53aa5f9fc597e253d73ddbcf1f241a8bd1c9cb":
        raise R27P30Error("parent")
    if PARENT_R27P29_CI_RUN != 34716655575 or PARENT_R27P29_CI_JOB != 103615006481:
        raise R27P30Error("parent_ci_identity")
    if PARENT_R27P29_CI_CONCLUSION != "success" or PARENT_R27P29_TEST_COUNT != 4:
        raise R27P30Error("parent_ci_result")
    if DEFAULT_PARITY_CHUNK_ROWS <= 0:
        raise R27P30Error("default_chunk_rows")

    required = (
        WINDOWED_RAW_SEMANTICS_INTEGRATED,
        EXACT_CORRECTED_25_FEATURE_CONTEXT_PARITY_REQUIRED,
        EXACT_CONTEXT_DIGEST_REQUIRED,
        EXACT_MIDPOINT_BYTES_REQUIRED,
        EXACT_L5_CHANGED_CELLS_REQUIRED,
        EXACT_VOLATILITY_CHANGED_CELLS_REQUIRED,
        ONE_LOGICAL_RAW_EVENT_PASS_REQUIRED,
        SYNTHETIC_RAW_REHYDRATION_FOR_PARITY_ONLY,
        SYNTHETIC_ONLY,
        not DOWNSTREAM_FULL_DAY_BOUNDED_CONTEXT_COMPLETE,
        not FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not CANONICAL_EXECUTION_READY,
    )
    if not all(required):
        raise R27P30Error("required_guard")

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
        raise R27P30Error("execution_surface_open")
    if READINESS_BLOCKER != "DOWNSTREAM_CONTEXT_RESIDENCY_NOT_YET_BOUNDED_FOR_FULL_DAY":
        raise R27P30Error("readiness_blocker")


__all__ = [
    "CorrectedContextParityResult",
    "make_r27p6_signature_adapter",
    "run_synthetic_corrected_context_parity_probe",
    "validate_r27p30_contract",
]

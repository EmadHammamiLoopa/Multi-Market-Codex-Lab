from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p19_canonical_materialization_readiness_preflight as r27p19


EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P20"
DESIGN_VERSION = "file-backed-bounded-memory-synthetic-preflight-v1"
PARENT_R27P19_HEAD = "11e78f1d0ba8de8ed14cffd49460c2d2dd84fb51"

ARCHITECTURE = "CALLER_PROVIDED_FILE_BACKED_RAW_SURFACES"
NUMBA_MEMMAP_WRITE_COMPATIBILITY_REQUIRED = True
EXACT_BUFFER_BYTES_REQUIRED = True
EXACT_DTYPE_AND_SHAPE_REQUIRED = True
CALLER_PROVIDED_OUTPUT_BUFFERS_REQUIRED = True
ANONYMOUS_FULL_N_OUTPUT_ALLOCATION_FOR_TARGET_ARCHITECTURE = False
ONE_COMPILED_PASS_COMPATIBLE = True
R27P6_RAW_SEMANTICS_REWRITE_COMPLETE = False
FULL_DAY_BOUNDED_MEMORY_PROVEN = False
CANONICAL_EXECUTION_READY = False
READINESS_BLOCKER = "R27P6_RAW_KERNEL_NOT_YET_REWRITTEN_FOR_FILE_BACKED_OUTPUTS"

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

CASE_COUNT = r27p6.CASE_COUNT
TOP_DEPTH_LEVELS = r27p6.TOP_DEPTH_LEVELS


class R27P20Error(RuntimeError):
    pass


@dataclass(frozen=True)
class BufferSpec:
    name: str
    dtype: str
    trailing_shape: tuple[int, ...]


RAW_BUFFER_SPECS = (
    BufferSpec("book_local_ns", "<i8", ()),
    BufferSpec("bid_ticks", "<i8", (TOP_DEPTH_LEVELS,)),
    BufferSpec("bid_qty", "<f8", (TOP_DEPTH_LEVELS,)),
    BufferSpec("ask_ticks", "<i8", (TOP_DEPTH_LEVELS,)),
    BufferSpec("ask_qty", "<f8", (TOP_DEPTH_LEVELS,)),
    BufferSpec("candidate_qty", "<f8", (CASE_COUNT,)),
    BufferSpec("flow_local_ns", "<i8", ()),
    BufferSpec("flow_code", "|i1", ()),
    BufferSpec("flow_qty", "<f8", ()),
    BufferSpec("midpoint_exchange_ns", "<i8", ()),
    BufferSpec("midpoint_tick_sum", "<i8", ()),
)

EXPECTED_BYTES_PER_EVENT = r27p19.FUSED_RAW_CAPACITY_BYTES_PER_EVENT


def _load_numba():
    try:
        from numba import njit
    except Exception as exc:
        raise R27P20Error("numba_unavailable") from exc
    return njit


def raw_capacity_bytes(rows: int) -> int:
    value = int(rows)
    if value < 0:
        raise R27P20Error("negative_rows")
    return value * EXPECTED_BYTES_PER_EVENT


def _shape(rows: int, spec: BufferSpec) -> tuple[int, ...]:
    return (int(rows),) + tuple(spec.trailing_shape)


def allocate_in_memory_buffers(rows: int) -> dict[str, np.ndarray]:
    n = int(rows)
    if n <= 0:
        raise R27P20Error("rows")
    return {
        spec.name: np.empty(_shape(n, spec), dtype=np.dtype(spec.dtype))
        for spec in RAW_BUFFER_SPECS
    }


def allocate_file_backed_buffers(root: Path, rows: int) -> dict[str, np.memmap]:
    n = int(rows)
    if n <= 0:
        raise R27P20Error("rows")
    target = Path(root)
    target.mkdir(parents=True, exist_ok=False)
    out: dict[str, np.memmap] = {}
    for spec in RAW_BUFFER_SPECS:
        out[spec.name] = np.memmap(
            target / f"{spec.name}.bin",
            mode="w+",
            dtype=np.dtype(spec.dtype),
            shape=_shape(n, spec),
        )
    return out


def close_file_backed_buffers(buffers: dict[str, np.memmap]) -> None:
    for array in buffers.values():
        array.flush()
        mm = getattr(array, "_mmap", None)
        if mm is not None:
            mm.close()


def build_synthetic_fill_kernel():
    njit = _load_numba()

    @njit(cache=False)
    def kernel(
        book_local_ns,
        bid_ticks,
        bid_qty,
        ask_ticks,
        ask_qty,
        candidate_qty,
        flow_local_ns,
        flow_code,
        flow_qty,
        midpoint_exchange_ns,
        midpoint_tick_sum,
    ):
        n = book_local_ns.size
        for i in range(n):
            book_local_ns[i] = 1_000_000_000 + i * 100
            flow_local_ns[i] = 2_000_000_000 + i * 101
            flow_code[i] = (i % 6) + 1
            flow_qty[i] = (i + 1) * 0.125
            midpoint_exchange_ns[i] = 3_000_000_000 + i * 103
            midpoint_tick_sum[i] = 200_001 + i * 2
            for j in range(bid_ticks.shape[1]):
                bid_ticks[i, j] = 100_000 - i - j
                bid_qty[i, j] = (i + 1) * (j + 1) * 0.01
                ask_ticks[i, j] = 100_001 + i + j
                ask_qty[i, j] = (i + 1) * (j + 1) * 0.02
            for j in range(candidate_qty.shape[1]):
                candidate_qty[i, j] = (i + 1) * (j + 1) * 0.03125
        return n

    return kernel


def _ordered_args(buffers: dict[str, np.ndarray]):
    return tuple(buffers[spec.name] for spec in RAW_BUFFER_SPECS)


def fill_buffers(buffers: dict[str, np.ndarray], *, kernel=None) -> int:
    k = build_synthetic_fill_kernel() if kernel is None else kernel
    return int(k(*_ordered_args(buffers)))


def assert_exact_buffer_parity(
    reference: dict[str, np.ndarray], candidate: dict[str, np.ndarray]
) -> None:
    for spec in RAW_BUFFER_SPECS:
        a = np.asarray(reference[spec.name])
        b = np.asarray(candidate[spec.name])
        if a.dtype != np.dtype(spec.dtype) or b.dtype != np.dtype(spec.dtype):
            raise R27P20Error(f"dtype:{spec.name}")
        if a.shape != b.shape:
            raise R27P20Error(f"shape:{spec.name}")
        if a.tobytes(order="C") != b.tobytes(order="C"):
            raise R27P20Error(f"bytes:{spec.name}")


def run_synthetic_memmap_compatibility_probe(rows: int = 257) -> None:
    validate_r27p20_contract()
    kernel = build_synthetic_fill_kernel()
    reference = allocate_in_memory_buffers(rows)
    reference_count = fill_buffers(reference, kernel=kernel)
    with TemporaryDirectory(prefix="dev045_r27p20_") as root:
        candidate = allocate_file_backed_buffers(Path(root) / "buffers", rows)
        try:
            candidate_count = fill_buffers(candidate, kernel=kernel)
            if reference_count != rows or candidate_count != rows:
                raise R27P20Error("fill_count")
            assert_exact_buffer_parity(reference, candidate)
            for spec in RAW_BUFFER_SPECS:
                array = candidate[spec.name]
                if not isinstance(array, np.memmap):
                    raise R27P20Error(f"not_memmap:{spec.name}")
                expected = int(np.prod(array.shape, dtype=np.int64)) * int(array.dtype.itemsize)
                if Path(array.filename).stat().st_size != expected:
                    raise R27P20Error(f"file_size:{spec.name}")
        finally:
            close_file_backed_buffers(candidate)


def validate_r27p20_contract() -> None:
    r27p19.validate_r27p19_contract()
    r27p6.validate_r27p6_contract()
    if PARENT_R27P19_HEAD != "11e78f1d0ba8de8ed14cffd49460c2d2dd84fb51":
        raise R27P20Error("parent")
    if EXPECTED_BYTES_PER_EVENT != 265:
        raise R27P20Error("bytes_per_event")
    if sum(np.dtype(spec.dtype).itemsize * int(np.prod(spec.trailing_shape or (1,))) for spec in RAW_BUFFER_SPECS) != 265:
        raise R27P20Error("buffer_specs")
    required = (
        NUMBA_MEMMAP_WRITE_COMPATIBILITY_REQUIRED,
        EXACT_BUFFER_BYTES_REQUIRED,
        EXACT_DTYPE_AND_SHAPE_REQUIRED,
        CALLER_PROVIDED_OUTPUT_BUFFERS_REQUIRED,
        not ANONYMOUS_FULL_N_OUTPUT_ALLOCATION_FOR_TARGET_ARCHITECTURE,
        ONE_COMPILED_PASS_COMPATIBLE,
        SYNTHETIC_ONLY,
        not R27P6_RAW_SEMANTICS_REWRITE_COMPLETE,
        not FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not CANONICAL_EXECUTION_READY,
    )
    if not all(required):
        raise R27P20Error("required_guard")
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
        raise R27P20Error("execution_surface_open")
    if READINESS_BLOCKER != "R27P6_RAW_KERNEL_NOT_YET_REWRITTEN_FOR_FILE_BACKED_OUTPUTS":
        raise R27P20Error("readiness_blocker")


__all__ = [
    "RAW_BUFFER_SPECS",
    "allocate_file_backed_buffers",
    "allocate_in_memory_buffers",
    "assert_exact_buffer_parity",
    "build_synthetic_fill_kernel",
    "fill_buffers",
    "raw_capacity_bytes",
    "run_synthetic_memmap_compatibility_probe",
    "validate_r27p20_contract",
]

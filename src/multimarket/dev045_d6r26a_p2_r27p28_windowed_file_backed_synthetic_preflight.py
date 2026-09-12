from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from multimarket import dev045_d6r26a_p2_r27p20_file_backed_bounded_memory_synthetic_preflight as r27p20


EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P28"
DESIGN_VERSION = "windowed-file-backed-output-synthetic-preflight-v1"
PARENT_R27P27_RESULT_HEAD = "30c645f3fba1eda011c8f5ca6f96a3721052a7aa"
PARENT_R27P27_CLASSIFICATION = "SCIENTIFIC_MEMORY_FAIL"
PARENT_R27P27_PEAK_RSS_BYTES = 12_888_293_376
PARENT_R27P27_EXCESS_BYTES = 3_391_488
R27P27_RERUN_AUTHORIZED = False

ARCHITECTURE = "FULL_CAPACITY_FILES_BOUNDED_ROW_WINDOW_MAPPINGS"
WINDOWED_OUTPUT_MAPPING_REQUIRED = True
FULL_FILE_MEMMAP_FOR_TARGET_ARCHITECTURE = False
EXACT_BUFFER_BYTES_REQUIRED = True
EXACT_DTYPE_AND_SHAPE_REQUIRED = True
FULL_CAPACITY_FILE_SIZE_REQUIRED = True
SEQUENTIAL_WINDOW_RELEASE_REQUIRED = True
DEFAULT_WINDOW_ROWS = 262_144
RAW_BUFFER_COUNT = len(r27p20.RAW_BUFFER_SPECS)
BYTES_PER_EVENT = r27p20.EXPECTED_BYTES_PER_EVENT

STATEFUL_RAW_KERNEL_WINDOWING_COMPLETE = False
FULL_DAY_BOUNDED_MEMORY_PROVEN = False
GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN = False
CANONICAL_EXECUTION_READY = False
READINESS_BLOCKER = "STATEFUL_RAW_KERNEL_NOT_YET_WINDOWED"

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


class R27P28Error(RuntimeError):
    pass


@dataclass(frozen=True)
class WindowedProbeResult:
    rows: int
    window_rows: int
    window_count: int
    raw_buffer_count: int
    bytes_per_event: int
    total_capacity_bytes: int
    max_active_mapped_bytes: int
    exact_buffer_bytes: bool
    exact_dtypes_and_shapes: bool
    full_capacity_file_sizes: bool


def _row_bytes(spec) -> int:
    trailing = int(np.prod(spec.trailing_shape or (1,), dtype=np.int64))
    return int(np.dtype(spec.dtype).itemsize) * trailing


def _shape(rows: int, spec) -> tuple[int, ...]:
    return (int(rows),) + tuple(spec.trailing_shape)


def _full_file_bytes(rows: int, spec) -> int:
    return int(rows) * _row_bytes(spec)


def prepare_full_capacity_files(root: Path, rows: int) -> dict[str, Path]:
    n = int(rows)
    if n <= 0:
        raise R27P28Error("rows")
    target = Path(root)
    target.mkdir(parents=True, exist_ok=False)
    paths: dict[str, Path] = {}
    for spec in r27p20.RAW_BUFFER_SPECS:
        path = target / f"{spec.name}.bin"
        with path.open("wb") as handle:
            handle.truncate(_full_file_bytes(n, spec))
        paths[spec.name] = path
    return paths


def map_row_window(
    paths: dict[str, Path],
    *,
    row_start: int,
    row_count: int,
) -> dict[str, np.memmap]:
    start = int(row_start)
    count = int(row_count)
    if start < 0 or count <= 0:
        raise R27P28Error("window_bounds")
    out: dict[str, np.memmap] = {}
    try:
        for spec in r27p20.RAW_BUFFER_SPECS:
            if spec.name not in paths:
                raise R27P28Error(f"missing_path:{spec.name}")
            row_bytes = _row_bytes(spec)
            path = Path(paths[spec.name])
            required_end = (start + count) * row_bytes
            if required_end > path.stat().st_size:
                raise R27P28Error(f"window_exceeds_file:{spec.name}")
            out[spec.name] = np.memmap(
                path,
                mode="r+",
                dtype=np.dtype(spec.dtype),
                offset=start * row_bytes,
                shape=_shape(count, spec),
            )
        return out
    except Exception:
        close_window(out)
        raise


def close_window(buffers: dict[str, np.memmap]) -> None:
    for array in buffers.values():
        array.flush()
        mm = getattr(array, "_mmap", None)
        if mm is not None:
            mm.close()


def _ordered_args(buffers: dict[str, np.ndarray]):
    return tuple(buffers[spec.name] for spec in r27p20.RAW_BUFFER_SPECS)


def build_window_fill_kernel():
    njit = r27p20._load_numba()

    @njit(cache=False)
    def kernel(
        global_row_start,
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
            g = global_row_start + i
            book_local_ns[i] = 1_000_000_000 + g * 100
            flow_local_ns[i] = 2_000_000_000 + g * 101
            flow_code[i] = (g % 6) + 1
            flow_qty[i] = (g + 1) * 0.125
            midpoint_exchange_ns[i] = 3_000_000_000 + g * 103
            midpoint_tick_sum[i] = 200_001 + g * 2
            for j in range(bid_ticks.shape[1]):
                bid_ticks[i, j] = 100_000 - g - j
                bid_qty[i, j] = (g + 1) * (j + 1) * 0.01
                ask_ticks[i, j] = 100_001 + g + j
                ask_qty[i, j] = (g + 1) * (j + 1) * 0.02
            for j in range(candidate_qty.shape[1]):
                candidate_qty[i, j] = (g + 1) * (j + 1) * 0.03125
        return n

    return kernel


def fill_windowed(
    paths: dict[str, Path],
    *,
    rows: int,
    window_rows: int = DEFAULT_WINDOW_ROWS,
    kernel=None,
) -> tuple[int, int]:
    n = int(rows)
    width = int(window_rows)
    if n <= 0:
        raise R27P28Error("rows")
    if width <= 0:
        raise R27P28Error("window_rows")
    k = build_window_fill_kernel() if kernel is None else kernel
    total = 0
    windows = 0
    start = 0
    while start < n:
        count = min(width, n - start)
        mapped = map_row_window(paths, row_start=start, row_count=count)
        try:
            wrote = int(k(start, *_ordered_args(mapped)))
            if wrote != count:
                raise R27P28Error("window_fill_count")
        finally:
            close_window(mapped)
        total += count
        windows += 1
        start += count
    return total, windows


def _assert_files_exact(reference: dict[str, np.ndarray], paths: dict[str, Path]) -> None:
    for spec in r27p20.RAW_BUFFER_SPECS:
        a = np.asarray(reference[spec.name])
        expected_size = int(a.nbytes)
        path = Path(paths[spec.name])
        if path.stat().st_size != expected_size:
            raise R27P28Error(f"file_size:{spec.name}")
        b = np.memmap(path, mode="r", dtype=np.dtype(spec.dtype), shape=a.shape)
        try:
            if b.dtype != a.dtype or b.shape != a.shape:
                raise R27P28Error(f"dtype_shape:{spec.name}")
            if a.tobytes(order="C") != b.tobytes(order="C"):
                raise R27P28Error(f"bytes:{spec.name}")
        finally:
            mm = getattr(b, "_mmap", None)
            if mm is not None:
                mm.close()


def run_synthetic_windowed_parity_probe(
    rows: int = 509,
    window_rows: int = 73,
) -> WindowedProbeResult:
    validate_r27p28_contract()
    n = int(rows)
    width = int(window_rows)
    if n <= 0 or width <= 0:
        raise R27P28Error("probe_bounds")

    reference = r27p20.allocate_in_memory_buffers(n)
    reference_count = r27p20.fill_buffers(reference)
    if reference_count != n:
        raise R27P28Error("reference_fill_count")

    with TemporaryDirectory(prefix="dev045_r27p28_") as root:
        paths = prepare_full_capacity_files(Path(root) / "windowed", n)
        wrote, windows = fill_windowed(paths, rows=n, window_rows=width)
        if wrote != n:
            raise R27P28Error("target_fill_count")
        _assert_files_exact(reference, paths)
        expected_windows = int(math.ceil(n / width))
        if windows != expected_windows:
            raise R27P28Error("window_count")
        full_sizes_ok = all(
            Path(paths[spec.name]).stat().st_size == _full_file_bytes(n, spec)
            for spec in r27p20.RAW_BUFFER_SPECS
        )
        if not full_sizes_ok:
            raise R27P28Error("full_capacity_file_sizes")

        return WindowedProbeResult(
            rows=n,
            window_rows=width,
            window_count=windows,
            raw_buffer_count=RAW_BUFFER_COUNT,
            bytes_per_event=BYTES_PER_EVENT,
            total_capacity_bytes=n * BYTES_PER_EVENT,
            max_active_mapped_bytes=min(n, width) * BYTES_PER_EVENT,
            exact_buffer_bytes=True,
            exact_dtypes_and_shapes=True,
            full_capacity_file_sizes=True,
        )


def validate_r27p28_contract() -> None:
    r27p20.validate_r27p20_contract()
    if PARENT_R27P27_RESULT_HEAD != "30c645f3fba1eda011c8f5ca6f96a3721052a7aa":
        raise R27P28Error("parent_result_head")
    if PARENT_R27P27_CLASSIFICATION != "SCIENTIFIC_MEMORY_FAIL":
        raise R27P28Error("parent_classification")
    if PARENT_R27P27_PEAK_RSS_BYTES != 12_888_293_376:
        raise R27P28Error("parent_peak")
    if PARENT_R27P27_EXCESS_BYTES != 3_391_488:
        raise R27P28Error("parent_excess")
    if R27P27_RERUN_AUTHORIZED:
        raise R27P28Error("parent_rerun")
    if RAW_BUFFER_COUNT != 11 or BYTES_PER_EVENT != 265:
        raise R27P28Error("raw_capacity_identity")
    if DEFAULT_WINDOW_ROWS <= 0:
        raise R27P28Error("default_window_rows")

    required = (
        WINDOWED_OUTPUT_MAPPING_REQUIRED,
        not FULL_FILE_MEMMAP_FOR_TARGET_ARCHITECTURE,
        EXACT_BUFFER_BYTES_REQUIRED,
        EXACT_DTYPE_AND_SHAPE_REQUIRED,
        FULL_CAPACITY_FILE_SIZE_REQUIRED,
        SEQUENTIAL_WINDOW_RELEASE_REQUIRED,
        SYNTHETIC_ONLY,
        not STATEFUL_RAW_KERNEL_WINDOWING_COMPLETE,
        not FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not CANONICAL_EXECUTION_READY,
    )
    if not all(required):
        raise R27P28Error("required_guard")

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
        raise R27P28Error("execution_surface_open")
    if READINESS_BLOCKER != "STATEFUL_RAW_KERNEL_NOT_YET_WINDOWED":
        raise R27P28Error("readiness_blocker")


__all__ = [
    "WindowedProbeResult",
    "build_window_fill_kernel",
    "close_window",
    "fill_windowed",
    "map_row_window",
    "prepare_full_capacity_files",
    "run_synthetic_windowed_parity_probe",
    "validate_r27p28_contract",
]

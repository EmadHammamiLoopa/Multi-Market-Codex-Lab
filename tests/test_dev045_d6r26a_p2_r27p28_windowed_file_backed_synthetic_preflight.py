from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r27p28_windowed_file_backed_synthetic_preflight as r


def test_contract_is_synthetic_only_and_preserves_parent_failure() -> None:
    r.validate_r27p28_contract()
    assert r.EXPERIMENT_ID == "DEV045-D6R26A-P2-R27P28"
    assert r.PARENT_R27P27_RESULT_HEAD == "30c645f3fba1eda011c8f5ca6f96a3721052a7aa"
    assert r.PARENT_R27P27_CLASSIFICATION == "SCIENTIFIC_MEMORY_FAIL"
    assert r.PARENT_R27P27_PEAK_RSS_BYTES == 12_888_293_376
    assert r.PARENT_R27P27_EXCESS_BYTES == 3_391_488
    assert r.R27P27_RERUN_AUTHORIZED is False
    assert r.BYTES_PER_EVENT == 265
    assert r.RAW_BUFFER_COUNT == 11
    assert r.SYNTHETIC_ONLY is True
    assert r.REAL_HISTORICAL_OPEN_AUTHORIZED is False
    assert r.P2_ATTEMPT_CONSUMED is False
    assert r.STATEFUL_RAW_KERNEL_WINDOWING_COMPLETE is False
    assert r.FULL_DAY_BOUNDED_MEMORY_PROVEN is False
    assert r.CANONICAL_EXECUTION_READY is False


def test_windowed_probe_is_exact_across_multiple_windows() -> None:
    result = r.run_synthetic_windowed_parity_probe(rows=509, window_rows=73)
    assert result.rows == 509
    assert result.window_rows == 73
    assert result.window_count == 7
    assert result.raw_buffer_count == 11
    assert result.bytes_per_event == 265
    assert result.total_capacity_bytes == 509 * 265
    assert result.max_active_mapped_bytes == 73 * 265
    assert result.exact_buffer_bytes is True
    assert result.exact_dtypes_and_shapes is True
    assert result.full_capacity_file_sizes is True
    assert result.max_active_mapped_bytes < result.total_capacity_bytes


def test_window_offsets_preserve_global_row_semantics() -> None:
    with TemporaryDirectory(prefix="dev045_r27p28_test_") as root:
        paths = r.prepare_full_capacity_files(Path(root) / "buffers", 19)
        wrote, windows = r.fill_windowed(paths, rows=19, window_rows=5)
        assert wrote == 19
        assert windows == 4

        book = np.memmap(paths["book_local_ns"], mode="r", dtype=np.dtype("<i8"), shape=(19,))
        flow = np.memmap(paths["flow_local_ns"], mode="r", dtype=np.dtype("<i8"), shape=(19,))
        code = np.memmap(paths["flow_code"], mode="r", dtype=np.dtype("|i1"), shape=(19,))
        try:
            assert int(book[0]) == 1_000_000_000
            assert int(book[4]) == 1_000_000_400
            assert int(book[5]) == 1_000_000_500
            assert int(book[18]) == 1_000_001_800
            assert int(flow[5]) == 2_000_000_505
            assert int(code[5]) == 6
            assert int(code[6]) == 1
        finally:
            for array in (book, flow, code):
                mm = getattr(array, "_mmap", None)
                if mm is not None:
                    mm.close()


def test_full_capacity_files_exist_without_full_file_mapping() -> None:
    rows = 31
    with TemporaryDirectory(prefix="dev045_r27p28_size_") as root:
        paths = r.prepare_full_capacity_files(Path(root) / "buffers", rows)
        assert set(paths) == {spec.name for spec in r.r27p20.RAW_BUFFER_SPECS}
        for spec in r.r27p20.RAW_BUFFER_SPECS:
            expected = rows * np.dtype(spec.dtype).itemsize * int(np.prod(spec.trailing_shape or (1,)))
            assert paths[spec.name].stat().st_size == expected

        mapped = r.map_row_window(paths, row_start=7, row_count=3)
        try:
            for spec in r.r27p20.RAW_BUFFER_SPECS:
                assert mapped[spec.name].shape == (3,) + tuple(spec.trailing_shape)
        finally:
            r.close_window(mapped)


def test_invalid_windows_are_rejected() -> None:
    with TemporaryDirectory(prefix="dev045_r27p28_invalid_") as root:
        paths = r.prepare_full_capacity_files(Path(root) / "buffers", 10)
        with pytest.raises(r.R27P28Error, match="window_bounds"):
            r.map_row_window(paths, row_start=-1, row_count=1)
        with pytest.raises(r.R27P28Error, match="window_bounds"):
            r.map_row_window(paths, row_start=0, row_count=0)
        with pytest.raises(r.R27P28Error, match="window_exceeds_file"):
            r.map_row_window(paths, row_start=9, row_count=2)


def test_execution_surfaces_remain_closed() -> None:
    assert r.REAL_HISTORICAL_OPEN_AUTHORIZED is False
    assert r.SOURCE_REHASH_AUTHORIZED is False
    assert r.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r.SIMULATOR_LANE_AUTHORIZED is False
    assert r.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r.P2_ATTEMPT_CONSUMED is False
    assert r.MODEL_FIT_AUTHORIZED is False
    assert r.PNL_AUTHORIZED is False
    assert r.AUG_OPEN_AUTHORIZED is False
    assert r.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r.NON_BTC_OPEN_AUTHORIZED is False
    assert r.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False

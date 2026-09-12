from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r27p20_file_backed_bounded_memory_synthetic_preflight as r


def test_contract_and_capacity_identity():
    r.validate_r27p20_contract()
    assert r.EXPECTED_BYTES_PER_EVENT == 265
    assert r.raw_capacity_bytes(0) == 0
    assert r.raw_capacity_bytes(1) == 265
    assert r.raw_capacity_bytes(181_084_390) == 47_987_363_350
    with pytest.raises(r.R27P20Error, match="negative_rows"):
        r.raw_capacity_bytes(-1)


def test_file_backed_shapes_dtypes_and_file_sizes():
    rows = 17
    with TemporaryDirectory(prefix="dev045_r27p20_test_") as root:
        buffers = r.allocate_file_backed_buffers(Path(root) / "buffers", rows)
        try:
            assert tuple(buffers) == tuple(spec.name for spec in r.RAW_BUFFER_SPECS)
            for spec in r.RAW_BUFFER_SPECS:
                array = buffers[spec.name]
                assert isinstance(array, np.memmap)
                assert array.dtype == np.dtype(spec.dtype)
                assert array.shape == (rows,) + spec.trailing_shape
                expected = int(np.prod(array.shape, dtype=np.int64)) * array.dtype.itemsize
                assert Path(array.filename).stat().st_size == expected
        finally:
            r.close_file_backed_buffers(buffers)


def test_numba_writes_memmaps_with_exact_byte_parity():
    r.run_synthetic_memmap_compatibility_probe(rows=257)


def test_execution_surfaces_are_closed():
    assert r.SYNTHETIC_ONLY is True
    assert r.REAL_HISTORICAL_OPEN_AUTHORIZED is False
    assert r.SOURCE_REHASH_AUTHORIZED is False
    assert r.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r.SIMULATOR_LANE_AUTHORIZED is False
    assert r.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r.P2_ATTEMPT_CONSUMED is False
    assert r.FULL_DAY_BOUNDED_MEMORY_PROVEN is False
    assert r.CANONICAL_EXECUTION_READY is False
    assert r.READINESS_BLOCKER == "R27P6_RAW_KERNEL_NOT_YET_REWRITTEN_FOR_FILE_BACKED_OUTPUTS"

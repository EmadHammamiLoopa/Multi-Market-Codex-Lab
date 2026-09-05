from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
from pathlib import Path
import tempfile
from typing import Iterable

import numpy as np

from multimarket import dev045_d6r8ed_semantic_real_parity_contract as c

REAL_SUCCESSOR_EXECUTION_AUTHORIZED = False


class D6R8EEError(RuntimeError):
    pass


@dataclass(frozen=True)
class SemanticIdentity:
    rows: int
    decompressed_bytes: int
    decompressed_sha256: str
    first_local_timestamp_us: int | None
    last_local_timestamp_us: int | None


@dataclass(frozen=True)
class ThreeWayParityResult:
    rows: int
    dtype_itemsize: int
    upstream_old_equal: bool
    upstream_v2_equal: bool
    old_v2_equal: bool


def _iter_gzip_lines(path: Path) -> Iterable[bytes]:
    with gzip.open(path, "rb") as fh:
        for line in fh:
            yield line


def inspect_semantic_identity(path: Path, local_timestamp_index: int) -> SemanticIdentity:
    digest = hashlib.sha256()
    decompressed_bytes = 0
    rows = 0
    first_ts = None
    last_ts = None
    for line_no, raw in enumerate(_iter_gzip_lines(path)):
        digest.update(raw)
        decompressed_bytes += len(raw)
        if line_no == 0:
            continue
        parts = raw.rstrip(b"\r\n").split(b",")
        if local_timestamp_index >= len(parts):
            raise D6R8EEError("row_width")
        ts = int(parts[local_timestamp_index])
        if first_ts is None:
            first_ts = ts
        last_ts = ts
        rows += 1
    return SemanticIdentity(
        rows=rows,
        decompressed_bytes=decompressed_bytes,
        decompressed_sha256=digest.hexdigest(),
        first_local_timestamp_us=first_ts,
        last_local_timestamp_us=last_ts,
    )


def assert_expected_semantic_identity(actual: SemanticIdentity, expected: SemanticIdentity) -> None:
    if actual != expected:
        raise D6R8EEError(f"semantic_identity:{actual!r}:{expected!r}")


def _fieldwise_exact_nan_equal(left: np.ndarray, right: np.ndarray) -> bool:
    if left.shape != right.shape or left.dtype != right.dtype:
        return False
    if left.dtype.names is None or right.dtype.names is None:
        return np.array_equal(left, right, equal_nan=True)
    for field in left.dtype.names:
        l = left[field]
        r = right[field]
        if left.dtype[field].kind == "f":
            if not np.array_equal(l, r, equal_nan=True):
                return False
        elif not np.array_equal(l, r):
            return False
    return True


def compare_three_way(upstream: np.ndarray, old: np.ndarray, v2: np.ndarray) -> ThreeWayParityResult:
    if upstream.dtype.itemsize != c.PARITY_ITEMSIZE_REQUIRED:
        raise D6R8EEError("upstream_itemsize")
    if old.dtype.itemsize != c.PARITY_ITEMSIZE_REQUIRED:
        raise D6R8EEError("old_itemsize")
    if v2.dtype.itemsize != c.PARITY_ITEMSIZE_REQUIRED:
        raise D6R8EEError("v2_itemsize")
    uo = _fieldwise_exact_nan_equal(upstream, old)
    uv = _fieldwise_exact_nan_equal(upstream, v2)
    ov = _fieldwise_exact_nan_equal(old, v2)
    if not (uo and uv and ov):
        raise D6R8EEError(f"three_way_parity:{uo}:{uv}:{ov}")
    return ThreeWayParityResult(
        rows=len(upstream),
        dtype_itemsize=upstream.dtype.itemsize,
        upstream_old_equal=uo,
        upstream_v2_equal=uv,
        old_v2_equal=ov,
    )


def run_three_way_on_same_slice(trades: Path, depth: Path, work_root: Path) -> ThreeWayParityResult:
    import hftbacktest as h
    from hftbacktest.data.utils import tardis
    from multimarket import dev045_d6r_bounded_converter as old
    from multimarket import dev045_d6r8_structurally_bounded_converter as v2

    if h.__version__ != c.HFTBACKTEST_VERSION:
        raise D6R8EEError(f"hftbacktest_version:{h.__version__}")
    work_root.mkdir(parents=True, exist_ok=True)
    old_scratch = work_root / "old_scratch"
    v2_scratch = work_root / "v2_scratch"
    old_scratch.mkdir()
    v2_scratch.mkdir()
    old_out = work_root / "old.npy"
    v2_out = work_root / "v2.npy"

    upstream = tardis.convert(
        [str(trades), str(depth)],
        output_filename=None,
        buffer_size=128,
        ss_buffer_size=64,
        base_latency=c.UPSTREAM_BASE_LATENCY,
        snapshot_mode=c.UPSTREAM_SNAPSHOT_MODE,
    )
    old.convert_tardis(
        trades,
        depth,
        old_out,
        chunk_rows=old.PRODUCTION_CHUNK_ROWS,
        scratch_dir=old_scratch,
    )
    v2.convert_tardis(trades, depth, v2_out, scratch_dir=v2_scratch)

    old_arr = np.load(old_out, allow_pickle=False)
    v2_arr = np.load(v2_out, allow_pickle=False)
    return compare_three_way(upstream, old_arr, v2_arr)


def synthetic_self_test(trades: Path, depth: Path) -> ThreeWayParityResult:
    with tempfile.TemporaryDirectory(prefix="dev045_d6r8ee_") as td:
        return run_three_way_on_same_slice(trades, depth, Path(td))


def run_real_successor(*_: object, **__: object) -> None:
    if not REAL_SUCCESSOR_EXECUTION_AUTHORIZED:
        raise D6R8EEError("real_successor_execution_closed")
    raise D6R8EEError("real_successor_execution_requires_d6r8ef_authorization")

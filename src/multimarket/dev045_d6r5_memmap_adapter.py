from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Iterator

import numpy as np

from multimarket import dev045_d6r5_memmap_contract as c


class MemmapAdapterError(RuntimeError):
    pass


@dataclass
class CanonicalJanMemmap:
    path: Path
    data: np.memmap
    sha256: str
    _closed: bool = False

    def iter_chunks(self, *, chunk_rows: int = c.PRODUCTION_CHUNK_ROWS) -> Iterator[np.memmap]:
        if self._closed:
            raise MemmapAdapterError("memmap_closed")
        if isinstance(chunk_rows, bool) or not isinstance(chunk_rows, int):
            raise MemmapAdapterError("chunk_rows")
        if chunk_rows <= 0 or chunk_rows > c.PRODUCTION_CHUNK_ROWS:
            raise MemmapAdapterError("chunk_rows")

        for start in range(0, len(self.data), chunk_rows):
            stop = min(start + chunk_rows, len(self.data))
            chunk = self.data[start:stop]
            if not isinstance(chunk, np.memmap):
                raise MemmapAdapterError("chunk_not_memmap")
            if chunk.dtype != _expected_dtype():
                raise MemmapAdapterError(f"chunk_dtype:{chunk.dtype}")
            if chunk.dtype.names != c.EVENT_FIELDS:
                raise MemmapAdapterError(f"chunk_fields:{chunk.dtype.names}")
            if chunk.dtype.itemsize != c.EVENT_ITEMSIZE:
                raise MemmapAdapterError(f"chunk_itemsize:{chunk.dtype.itemsize}")
            if chunk.flags.writeable:
                raise MemmapAdapterError("chunk_writeable")
            if np.any(chunk["local_ts"] < chunk["exch_ts"]):
                raise MemmapAdapterError("negative_feed_latency")
            yield chunk

    def close(self) -> None:
        if self._closed:
            return
        mmap = getattr(self.data, "_mmap", None)
        if mmap is not None:
            mmap.close()
        self._closed = True

    def __enter__(self) -> "CanonicalJanMemmap":
        if self._closed:
            raise MemmapAdapterError("memmap_closed")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def _expected_dtype() -> np.dtype:
    return np.dtype(list(c.EVENT_DTYPE_DESCR))


def _stream_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(c.HASH_BLOCK_BYTES)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _stat_identity(path: Path) -> tuple[int, int, int, int]:
    st = path.stat()
    return (int(st.st_dev), int(st.st_ino), int(st.st_size), int(st.st_mtime_ns))


def _open_verified_file(
    path: Path,
    *,
    expected_sha256: str,
    expected_bytes: int,
    expected_rows: int,
) -> CanonicalJanMemmap:
    path = Path(path)
    if not path.is_file():
        raise MemmapAdapterError("canonical_missing")
    if path.suffix != ".npy":
        raise MemmapAdapterError("canonical_suffix")

    before = _stat_identity(path)
    if before[2] != int(expected_bytes):
        raise MemmapAdapterError(f"canonical_bytes:{before[2]}")

    observed_sha256 = _stream_sha256(path)
    if observed_sha256 != expected_sha256:
        raise MemmapAdapterError(f"canonical_sha256:{observed_sha256}")

    try:
        data = np.load(path, mmap_mode=c.NP_LOAD_MMAP_MODE, allow_pickle=c.NP_LOAD_ALLOW_PICKLE)
    except Exception as exc:
        raise MemmapAdapterError("canonical_open") from exc

    try:
        after = _stat_identity(path)
        if after != before:
            raise MemmapAdapterError("canonical_changed_during_open")
        if not isinstance(data, np.memmap):
            raise MemmapAdapterError("canonical_not_memmap")
        if data.flags.writeable:
            raise MemmapAdapterError("canonical_writeable")
        if data.ndim != c.EVENT_NDIM:
            raise MemmapAdapterError(f"canonical_ndim:{data.ndim}")
        if len(data) != int(expected_rows):
            raise MemmapAdapterError(f"canonical_rows:{len(data)}")
        if data.dtype != _expected_dtype():
            raise MemmapAdapterError(f"canonical_dtype:{data.dtype}")
        if data.dtype.names != c.EVENT_FIELDS:
            raise MemmapAdapterError(f"canonical_fields:{data.dtype.names}")
        if data.dtype.itemsize != c.EVENT_ITEMSIZE:
            raise MemmapAdapterError(f"canonical_itemsize:{data.dtype.itemsize}")
    except Exception:
        mmap = getattr(data, "_mmap", None)
        if mmap is not None:
            mmap.close()
        raise

    return CanonicalJanMemmap(path=path, data=data, sha256=observed_sha256)


def open_canonical_jan() -> CanonicalJanMemmap:
    """Open the sole D6R5 canonical Jan artifact as a verified read-only memmap."""
    return _open_verified_file(
        Path(c.CANONICAL_NPY_PATH),
        expected_sha256=c.CANONICAL_NPY_SHA256,
        expected_bytes=c.CANONICAL_NPY_BYTES,
        expected_rows=c.CANONICAL_NPY_ROWS,
    )

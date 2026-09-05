from __future__ import annotations

import hashlib
import inspect
from pathlib import Path
import tempfile
import unittest

import numpy as np

from multimarket import dev045_d6r5_memmap_adapter as a
from multimarket import dev045_d6r5_memmap_contract as c


class TestDev045D6R5MemmapAdapter(unittest.TestCase):
    def _fixture(self, root: Path, rows: int = 5) -> tuple[Path, str]:
        dtype = np.dtype(list(c.EVENT_DTYPE_DESCR))
        path = root / "fixture.npy"
        data = np.lib.format.open_memmap(path, mode="w+", dtype=dtype, shape=(rows,))
        try:
            for i in range(rows):
                data[i] = (1, i, i, 100.0 + i, 1.0, 0, 0, 0.0)
            data.flush()
        finally:
            mmap = getattr(data, "_mmap", None)
            if mmap is not None:
                mmap.close()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return path, digest

    def test_verified_open_is_read_only_memmap_and_exact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, digest = self._fixture(root)
            handle = a._open_verified_file(
                path,
                expected_sha256=digest,
                expected_bytes=path.stat().st_size,
                expected_rows=5,
            )
            try:
                self.assertIsInstance(handle.data, np.memmap)
                self.assertFalse(handle.data.flags.writeable)
                self.assertEqual(handle.data.dtype, np.dtype(list(c.EVENT_DTYPE_DESCR)))
                self.assertEqual(handle.sha256, digest)
            finally:
                handle.close()

    def test_chunks_are_bounded_views_in_physical_order(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, digest = self._fixture(root, rows=5)
            with a._open_verified_file(
                path,
                expected_sha256=digest,
                expected_bytes=path.stat().st_size,
                expected_rows=5,
            ) as handle:
                chunks = list(handle.iter_chunks(chunk_rows=2))
                self.assertEqual([len(x) for x in chunks], [2, 2, 1])
                self.assertTrue(all(isinstance(x, np.memmap) for x in chunks))
                self.assertTrue(all(not x.flags.writeable for x in chunks))
                self.assertEqual(
                    [int(x) for chunk in chunks for x in chunk["exch_ts"]],
                    [0, 1, 2, 3, 4],
                )

    def test_chunk_limit_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, digest = self._fixture(root)
            with a._open_verified_file(
                path,
                expected_sha256=digest,
                expected_bytes=path.stat().st_size,
                expected_rows=5,
            ) as handle:
                with self.assertRaisesRegex(a.MemmapAdapterError, "chunk_rows"):
                    list(handle.iter_chunks(chunk_rows=c.PRODUCTION_CHUNK_ROWS + 1))

    def test_wrong_sha_and_size_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, digest = self._fixture(root)
            with self.assertRaisesRegex(a.MemmapAdapterError, "canonical_bytes"):
                a._open_verified_file(
                    path,
                    expected_sha256=digest,
                    expected_bytes=path.stat().st_size + 1,
                    expected_rows=5,
                )
            with self.assertRaisesRegex(a.MemmapAdapterError, "canonical_sha256"):
                a._open_verified_file(
                    path,
                    expected_sha256="0" * 64,
                    expected_bytes=path.stat().st_size,
                    expected_rows=5,
                )

    def test_negative_latency_fails_on_bounded_chunk(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path, _ = self._fixture(root)
            data = np.load(path, mmap_mode="r+")
            try:
                data[3]["exch_ts"] = 10
                data[3]["local_ts"] = 9
                data.flush()
            finally:
                mmap = getattr(data, "_mmap", None)
                if mmap is not None:
                    mmap.close()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            with a._open_verified_file(
                path,
                expected_sha256=digest,
                expected_bytes=path.stat().st_size,
                expected_rows=5,
            ) as handle:
                with self.assertRaisesRegex(a.MemmapAdapterError, "negative_feed_latency"):
                    list(handle.iter_chunks(chunk_rows=2))

    def test_supported_public_entrypoint_has_no_path_argument(self):
        sig = inspect.signature(a.open_canonical_jan)
        self.assertEqual(tuple(sig.parameters), ())

    def test_source_has_no_converter_raw_or_whole_array_materialization_path(self):
        source = inspect.getsource(a)
        self.assertNotIn("convert_tardis", source)
        self.assertNotIn("gzip", source)
        self.assertNotIn("csv", source)
        self.assertNotIn("np.asarray(", source)
        self.assertNotIn("np.array(", source)
        self.assertNotIn("np.concatenate(", source)
        self.assertNotIn("np.sort(", source)
        self.assertNotIn("np.argsort(", source)
        self.assertIn("mmap_mode=c.NP_LOAD_MMAP_MODE", source)
        self.assertIn("allow_pickle=c.NP_LOAD_ALLOW_PICKLE", source)


if __name__ == "__main__":
    unittest.main()

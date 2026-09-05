from __future__ import annotations

import gzip
import json
from pathlib import Path
import tempfile
import unittest

from multimarket import dev045_d6r2_real_parity_contract as d6r2
from multimarket.dev045_d6r8eb_slice_identity_forensics import (
    GzipForensicsError,
    inspect_gzip_slice,
    logical_payload_equal,
)


ROOT = Path(__file__).resolve().parents[1]
FORENSIC_EVIDENCE = (
    ROOT / "evidence/dev045_d6r8eb_slice_identity_forensics.json"
)
D6R2_EVIDENCE = ROOT / "evidence/dev045_d6r2b_real_10min_parity.json"


def _write_gzip(
    path: Path,
    payload: bytes,
    *,
    filename: str,
    compresslevel: int,
) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(
            filename=filename,
            mode="wb",
            fileobj=raw,
            compresslevel=compresslevel,
            mtime=0,
        ) as target:
            target.write(payload)


class TestD6R8EBSliceIdentityForensics(unittest.TestCase):
    def test_inspection_reports_exact_logical_and_container_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            payload = b"a,b\n1,2\n3,4\n"
            path = Path(td) / "slice.csv.gz"
            _write_gzip(path, payload, filename="", compresslevel=9)

            result = inspect_gzip_slice(path)

            self.assertEqual(result.compressed_length, path.stat().st_size)
            self.assertEqual(result.decompressed_length, len(payload))
            self.assertEqual(result.data_rows, 2)
            self.assertEqual(bytes.fromhex(result.csv_header_hex), b"a,b\n")
            self.assertEqual(
                bytes.fromhex(result.first_data_row_hex or ""), b"1,2\n"
            )
            self.assertEqual(
                bytes.fromhex(result.last_data_row_hex or ""), b"3,4\n"
            )
            self.assertEqual(result.lf_lines, 3)
            self.assertEqual(result.crlf_lines, 0)
            self.assertEqual(result.cr_lines, 0)
            self.assertEqual(result.unterminated_lines, 0)
            self.assertEqual(
                result.gzip_header.raw_hex, "1f8b08000000000002ff"
            )
            self.assertEqual(result.gzip_header.compression_method, 8)
            self.assertEqual(result.gzip_header.flags, 0)
            self.assertEqual(result.gzip_header.mtime, 0)
            self.assertEqual(result.gzip_header.xfl, 2)
            self.assertEqual(result.gzip_header.os_byte, 255)
            self.assertIsNone(result.gzip_header.filename_hex)
            self.assertTrue(result.trailer_crc32_valid)
            self.assertTrue(result.trailer_isize_valid)

    def test_container_hash_can_change_with_identical_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            payload = b"a,b\n1,2\n3,4\n"
            left_path = Path(td) / "left.gz"
            right_path = Path(td) / "right.gz"
            _write_gzip(left_path, payload, filename="", compresslevel=1)
            _write_gzip(
                right_path,
                payload,
                filename="embedded.csv",
                compresslevel=9,
            )

            left = inspect_gzip_slice(left_path)
            right = inspect_gzip_slice(right_path)

            self.assertNotEqual(
                left.compressed_sha256, right.compressed_sha256
            )
            self.assertNotEqual(
                left.gzip_header.raw_hex, right.gzip_header.raw_hex
            )
            self.assertTrue(logical_payload_equal(left, right))

    def test_logical_payload_change_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            left_path = Path(td) / "left.gz"
            right_path = Path(td) / "right.gz"
            _write_gzip(
                left_path,
                b"a,b\n1,2\n",
                filename="",
                compresslevel=9,
            )
            _write_gzip(
                right_path,
                b"a,b\n1,3\n",
                filename="",
                compresslevel=9,
            )

            self.assertFalse(
                logical_payload_equal(
                    inspect_gzip_slice(left_path),
                    inspect_gzip_slice(right_path),
                )
            )

    def test_non_gzip_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "not-gzip.gz"
            path.write_bytes(b"not gzip")

            with self.assertRaisesRegex(
                GzipForensicsError, "truncated_gzip_header"
            ):
                inspect_gzip_slice(path)

    def test_d6r2_froze_container_hashes_but_not_payload_hashes(self) -> None:
        evidence = json.loads(D6R2_EVIDENCE.read_text(encoding="utf-8"))

        for kind in ("trades", "depth"):
            frozen = evidence["slice"][kind]
            self.assertIn("sha256", frozen)
            self.assertNotIn("decompressed_sha256", frozen)
            self.assertNotIn("decompressed_length", frozen)
            self.assertNotIn("gzip_header_hex", frozen)

        self.assertEqual(d6r2.TEMP_GZIP_MTIME, 0)
        self.assertFalse(hasattr(d6r2, "TEMP_GZIP_COMPRESSLEVEL"))
        self.assertFalse(hasattr(d6r2, "TEMP_GZIP_FILENAME"))
        self.assertFalse(hasattr(d6r2, "TEMP_GZIP_OS_BYTE"))

    def test_forensic_evidence_is_fail_closed(self) -> None:
        evidence = json.loads(FORENSIC_EVIDENCE.read_text(encoding="utf-8"))

        self.assertEqual(
            evidence["root_cause"],
            "FROZEN_D6R2_SLICE_HASH_SEMANTICS_UNRECOVERABLE",
        )
        self.assertFalse(evidence["logical_payload_identity_proven"])
        self.assertFalse(
            evidence["gzip_representation_only_mismatch_proven"]
        )
        self.assertTrue(evidence["d6r8eb_remains_frozen_fail"])
        self.assertFalse(evidence["successor_execution_gate_justified"])
        self.assertFalse(evidence["real_raw_files_content_opened"])
        self.assertFalse(evidence["real_converter_executed"])
        self.assertFalse(evidence["policy_replay_run"])
        self.assertFalse(evidence["pnl_computed"])

    def test_module_has_no_canonical_runtime_or_raw_data_binding(self) -> None:
        source = (
            ROOT
            / "src/multimarket/dev045_d6r8eb_slice_identity_forensics.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("/home/emadh/Multi-Market", source)
        self.assertNotIn("dev045_d6r8eb_real_slice_runner", source)
        self.assertNotIn("hftbacktest", source)
        self.assertNotIn("convert_tardis", source)


if __name__ == "__main__":
    unittest.main()

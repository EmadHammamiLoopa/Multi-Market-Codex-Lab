from __future__ import annotations

import ast
import json
import mmap
import os
from pathlib import Path
import tempfile
import unittest

from multimarket import dev045_d6r11_memory_attribution as a
from multimarket import dev045_d6r11_memory_attribution_contract as c


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = ROOT / "src/multimarket/dev045_d6r11_memory_attribution.py"

STATUS = """\
Name:\tpython
VmSize:\t  10000 kB
VmRSS:\t    7000 kB
RssAnon:\t4000 kB
RssFile:\t2500 kB
RssShmem:\t 500 kB
VmData:\t   6000 kB
VmSwap:\t     10 kB
Threads:\t1
"""

SMAPS_ROLLUP = """\
00400000-7fffffffffff ---p 00000000 00:00 0 [rollup]
Rss:                7000 kB
Pss:                6500 kB
Pss_Anon:           4000 kB
Pss_File:           2000 kB
Private_Clean:       100 kB
Private_Dirty:      3900 kB
Shared_Clean:       2500 kB
Shared_Dirty:        500 kB
Anonymous:          4000 kB
Swap:                 10 kB
"""


class TestD6R11MemoryAttribution(unittest.TestCase):
    def test_kib_to_bytes_is_exact_and_rejects_invalid_values(self):
        self.assertEqual(a.kib_to_bytes(0), 0)
        self.assertEqual(a.kib_to_bytes(1), 1024)
        self.assertEqual(a.kib_to_bytes(10_553_047), 10_806_320_128)
        for value in (-1, True, 1.0, "1"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(a.MemoryAttributionError, "kib_value"):
                    a.kib_to_bytes(value)  # type: ignore[arg-type]

    def test_status_parsing_and_rss_attribution(self):
        parsed = a.parse_proc_status(STATUS)
        self.assertEqual(parsed.vm_rss_bytes, 7000 * 1024)
        self.assertEqual(parsed.rss_anon_bytes, 4000 * 1024)
        self.assertEqual(parsed.rss_file_bytes, 2500 * 1024)
        self.assertEqual(parsed.rss_shmem_bytes, 500 * 1024)
        self.assertEqual(parsed.vm_size_bytes, 10000 * 1024)
        self.assertEqual(parsed.vm_data_bytes, 6000 * 1024)
        self.assertEqual(parsed.vm_swap_bytes, 10 * 1024)
        self.assertEqual(parsed.resident_components_bytes, parsed.vm_rss_bytes)
        self.assertEqual(parsed.rss_decomposition_delta_bytes, 0)
        self.assertIs(parsed.rss_decomposition_exact, True)

    def test_decomposition_mismatch_is_exposed_not_hidden(self):
        parsed = a.parse_proc_status(STATUS.replace("RssFile:\t2500", "RssFile:\t2400"))
        self.assertEqual(parsed.rss_decomposition_delta_bytes, 100 * 1024)
        self.assertIs(parsed.rss_decomposition_exact, False)
        self.assertEqual(parsed.to_dict()["rss_decomposition_delta_bytes"], 100 * 1024)

    def test_optional_status_fields_may_be_absent(self):
        minimal = "\n".join(
            ("VmRSS: 7 kB", "RssAnon: 4 kB", "RssFile: 2 kB", "RssShmem: 1 kB")
        )
        parsed = a.parse_proc_status(minimal)
        self.assertIsNone(parsed.vm_size_bytes)
        self.assertIsNone(parsed.vm_data_bytes)
        self.assertIsNone(parsed.vm_swap_bytes)

    def test_missing_duplicate_and_malformed_status_fail_closed(self):
        cases = {
            "missing": STATUS.replace("RssFile:\t2500 kB\n", ""),
            "duplicate": STATUS + "VmRSS: 7000 kB\n",
            "malformed": STATUS.replace("VmRSS:\t    7000 kB", "VmRSS: seven kB"),
            "negative": STATUS.replace("RssAnon:\t4000 kB", "RssAnon: -1 kB"),
            "unit": STATUS.replace("RssShmem:\t 500 kB", "RssShmem: 500 MB"),
        }
        expected = {
            "missing": "status_missing:RssFile",
            "duplicate": "status_duplicate:VmRSS",
            "malformed": "status_malformed:VmRSS",
            "negative": "status_malformed:RssAnon",
            "unit": "status_malformed:RssShmem",
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(a.MemoryAttributionError, expected[name]):
                    a.parse_proc_status(text)

    def test_memavailable_is_required_and_converted(self):
        self.assertEqual(a.parse_proc_meminfo("MemTotal: 9 kB\nMemAvailable: 8 kB\n"), 8192)
        with self.assertRaisesRegex(a.MemoryAttributionError, "meminfo_missing:MemAvailable"):
            a.parse_proc_meminfo("MemTotal: 9 kB\n")
        with self.assertRaisesRegex(a.MemoryAttributionError, "meminfo_duplicate:MemAvailable"):
            a.parse_proc_meminfo("MemAvailable: 8 kB\nMemAvailable: 7 kB\n")

    def test_smaps_rollup_parses_supported_fields_and_allows_optional_absence(self):
        parsed = a.parse_smaps_rollup(SMAPS_ROLLUP)
        self.assertEqual(parsed.rss_bytes, 7000 * 1024)
        self.assertEqual(parsed.pss_bytes, 6500 * 1024)
        self.assertEqual(parsed.pss_anon_bytes, 4000 * 1024)
        self.assertEqual(parsed.pss_file_bytes, 2000 * 1024)
        self.assertEqual(parsed.private_dirty_bytes, 3900 * 1024)
        self.assertEqual(parsed.shared_clean_bytes, 2500 * 1024)

        minimal = a.parse_smaps_rollup("Rss: 2 kB\nPss: 1 kB\n")
        self.assertIsNone(minimal.pss_anon_bytes)
        self.assertIsNone(minimal.pss_file_bytes)
        self.assertIsNone(minimal.swap_bytes)

        with self.assertRaisesRegex(a.MemoryAttributionError, "smaps_rollup_missing:Pss"):
            a.parse_smaps_rollup("Rss: 2 kB\n")
        with self.assertRaisesRegex(a.MemoryAttributionError, "smaps_rollup_duplicate:Rss"):
            a.parse_smaps_rollup("Rss: 2 kB\nPss: 1 kB\nRss: 2 kB\n")

    def test_snapshot_capture_and_serialization_are_deterministic(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r11_snapshot_") as td:
            root = Path(td)
            status = root / "status"
            meminfo = root / "meminfo"
            smaps = root / "smaps_rollup"
            status.write_text(STATUS, encoding="ascii")
            meminfo.write_text("MemAvailable: 12345 kB\n", encoding="ascii")
            smaps.write_text(SMAPS_ROLLUP, encoding="ascii")

            snapshot = a.capture_memory_snapshot(
                status_path=status,
                meminfo_path=meminfo,
                smaps_rollup_path=smaps,
                captured_at_utc="2026-09-06T00:00:00+00:00",
            )
            payload = json.loads(a.serialize_snapshot(snapshot))
            self.assertEqual(payload["experiment_id"], c.EXPERIMENT_ID)
            self.assertEqual(payload["schema_version"], c.SCHEMA_VERSION)
            self.assertEqual(payload["unit"], "bytes")
            self.assertEqual(payload["attribution"]["total_rss_bytes"], 7000 * 1024)
            self.assertEqual(payload["attribution"]["file_backed_resident_bytes"], 2500 * 1024)
            self.assertEqual(payload["attribution"]["anonymous_resident_bytes"], 4000 * 1024)
            self.assertEqual(payload["system"]["MemAvailable_bytes"], 12345 * 1024)
            self.assertTrue(payload["smaps_rollup_available"])
            self.assertIsNone(payload["canonical_abort_threshold_bytes"])
            for key in (
                "canonical_data_opened",
                "d6r10_rerun",
                "hftbacktest_executed",
                "policy_execution_run",
                "historical_pnl_computed",
                "converter_rerun",
            ):
                self.assertIs(payload[key], False)

    def test_unavailable_smaps_rollup_is_optional(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r11_optional_") as td:
            root = Path(td)
            status = root / "status"
            meminfo = root / "meminfo"
            status.write_text(STATUS, encoding="ascii")
            meminfo.write_text("MemAvailable: 1 kB\n", encoding="ascii")
            snapshot = a.capture_memory_snapshot(
                status_path=status,
                meminfo_path=meminfo,
                smaps_rollup_path=root / "absent",
                captured_at_utc="2026-09-06T00:00:00+00:00",
            )
            self.assertIsNone(snapshot.smaps_rollup)

    @unittest.skipUnless(Path(c.PROC_STATUS_PATH).is_file(), "Linux procfs unavailable")
    def test_live_proc_snapshot_is_attributed_without_market_data(self):
        snapshot = a.capture_memory_snapshot()
        self.assertGreater(snapshot.total_rss_bytes, 0)
        self.assertGreaterEqual(snapshot.anonymous_resident_bytes, 0)
        self.assertGreaterEqual(snapshot.file_backed_resident_bytes, 0)
        self.assertGreater(snapshot.mem_available_bytes, 0)

    @unittest.skipUnless(Path(c.PROC_SMAPS_PATH).is_file(), "Linux smaps unavailable")
    def test_small_synthetic_mmap_has_file_backed_residency(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r11_mmap_") as td:
            path = Path(td) / "synthetic.bin"
            size = 2 * 1024 * 1024
            with path.open("wb") as handle:
                handle.truncate(size)
            with path.open("rb") as handle:
                mapped = mmap.mmap(handle.fileno(), length=0, access=mmap.ACCESS_READ)
                try:
                    page_size = mmap.PAGESIZE
                    checksum = 0
                    for offset in range(0, size, page_size):
                        checksum ^= mapped[offset]
                    self.assertEqual(checksum, 0)
                    observed = a.capture_file_mapping_residency(path)
                    self.assertGreaterEqual(observed.mapping_count, 1)
                    self.assertGreater(observed.rss_bytes, 0)
                    self.assertGreater(observed.pss_bytes, 0)
                    self.assertEqual(
                        observed.rss_bytes,
                        observed.private_resident_bytes + observed.shared_resident_bytes,
                    )
                finally:
                    mapped.close()

    def test_file_mapping_parser_is_exact_and_fails_closed(self):
        text = """\
1000-2000 r--s 00000000 00:01 1 /tmp/a\\040file
Rss: 8 kB
Pss: 4 kB
Shared_Clean: 8 kB
Shared_Dirty: 0 kB
Private_Clean: 0 kB
Private_Dirty: 0 kB
2000-3000 rw-p 00000000 00:00 0 [heap]
Rss: 1 kB
Pss: 1 kB
"""
        observed = a.parse_file_mapping_residency(text, Path("/tmp/a file"))
        self.assertEqual(observed.mapping_count, 1)
        self.assertEqual(observed.rss_bytes, 8192)
        self.assertEqual(observed.pss_bytes, 4096)
        with self.assertRaisesRegex(a.MemoryAttributionError, "file_mapping_missing"):
            a.parse_file_mapping_residency(text, Path("/tmp/other"))

    def test_module_has_no_market_data_or_execution_surface(self):
        source = IMPLEMENTATION.read_text(encoding="utf-8")
        self.assertNotIn(".npy", source)
        self.assertNotIn("/home/emadh", source)
        self.assertNotIn("dev045_d6r10_feb_jul_v2_hft_ingestion", source)
        self.assertNotIn("open_canonical", source)
        self.assertNotIn("convert_tardis", source)
        self.assertNotIn("tardis", source.lower())

        imported: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        self.assertFalse(any("hftbacktest" in name for name in imported))
        self.assertFalse(any("policy" in name for name in imported))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest

from multimarket import dev045_d6r11_memory_attribution as memory
from multimarket import dev045_d6r13_real_diagnostic_successor_preflight as p
from multimarket import dev045_d6r13_real_diagnostic_successor_preflight_contract as c


def _snapshot(memavailable: int = 12_000_000_000) -> memory.MemorySnapshot:
    process = memory.ProcessMemorySnapshot(
        vm_rss_bytes=10,
        rss_anon_bytes=4,
        rss_file_bytes=6,
        rss_shmem_bytes=0,
        vm_size_bytes=20,
        vm_data_bytes=3,
        vm_swap_bytes=0,
    )
    return memory.MemorySnapshot(
        process=process,
        mem_available_bytes=memavailable,
        captured_at_utc="2026-09-06T00:00:00Z",
        smaps_rollup=None,
    )


class TestD6R13SuccessorPreflight(unittest.TestCase):
    def test_contract_is_design_only_and_fresh(self):
        self.assertEqual(c.EXPERIMENT_ID, "DEV045-D6R13")
        self.assertEqual(c.PARENT_FREEZE_HEAD, "4e27c8f9b9403bffcdc866e83ef7b3e79e03ee28")
        self.assertIs(c.D6R12_RERUN_FORBIDDEN, True)
        self.assertIs(c.REAL_EXECUTION_ENABLED, False)
        self.assertEqual(c.PROHIBITED_EXECUTION_FLAGS, (False,) * len(c.PROHIBITED_EXECUTION_FLAGS))
        self.assertEqual(c.SOURCE_PREFLIGHT_ACCESS, "STAT_ONLY")
        self.assertIn("dev045_d6r13", str(c.RUNTIME_ROOT))
        self.assertNotIn("dev045_d6r12/2026-02-01", str(c.RUNTIME_ROOT))

    def test_source_stat_helper_never_opens_or_hashes_source(self):
        source = inspect.getsource(p._verify_source_stat_only)
        self.assertIn("os.stat", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("sha256", source)
        self.assertNotIn("read", source)

    def test_small_hash_rejects_source_path(self):
        with self.assertRaisesRegex(p.D6R13PreflightError, "source_hash_forbidden"):
            p._sha256_small(c.SOURCE_PATH)

    def test_preexec_memory_threshold_is_preserved(self):
        from multimarket import dev045_d6r12_memory_attributed_real_diagnostic as design
        self.assertIsNone(design.preexecution_failure_reason(_snapshot(c.PREEXEC_MIN_MEMAVAILABLE_BYTES)))
        self.assertIsNotNone(design.preexecution_failure_reason(_snapshot(c.PREEXEC_MIN_MEMAVAILABLE_BYTES - 1)))

    def test_no_real_parent_or_child_entrypoint_exists_in_preflight_design(self):
        module_source = inspect.getsource(p)
        self.assertNotIn("run_real_parent", module_source)
        self.assertNotIn("run_real_child", module_source)
        self.assertNotIn("open_source", module_source)
        self.assertNotIn("wait_next_feed", module_source)

    def test_launcher_smoke_remains_fixed_module_and_noncanonical(self):
        from multimarket import dev045_d6r13_child_launch_successor as launcher
        result = launcher.run_smoke_parent()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.payload["status"], "PASS")
        self.assertEqual(result.payload["resolved_module_name"], c.CHILD_MODULE_NAME)
        self.assertFalse(result.payload["source_content_opened"])
        self.assertFalse(result.payload["attempt_marker_created"])
        self.assertFalse(result.payload["hftbacktest_canonical_run"])


if __name__ == "__main__":
    unittest.main()

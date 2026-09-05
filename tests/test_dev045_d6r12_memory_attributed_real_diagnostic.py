from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from multimarket import dev045_d6r11_memory_attribution as memory
from multimarket import dev045_d6r12_memory_attributed_real_diagnostic as d
from multimarket import dev045_d6r12_memory_attributed_real_diagnostic_contract as c


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = ROOT / "src/multimarket/dev045_d6r12_memory_attributed_real_diagnostic.py"


def _snapshot(
    *,
    vm_rss: int,
    rss_anon: int,
    rss_file: int,
    rss_shmem: int = 0,
    memavailable: int = 20_000_000_000,
    vm_swap: int | None = 0,
    captured_at: str = "2026-09-06T00:00:00+00:00",
) -> memory.MemorySnapshot:
    return memory.MemorySnapshot(
        captured_at_utc=captured_at,
        pid=123,
        process=memory.ProcessMemory(
            vm_rss_bytes=vm_rss,
            rss_anon_bytes=rss_anon,
            rss_file_bytes=rss_file,
            rss_shmem_bytes=rss_shmem,
            vm_size_bytes=30_000_000_000,
            vm_data_bytes=2_000_000_000,
            vm_swap_bytes=vm_swap,
        ),
        mem_available_bytes=memavailable,
        smaps_rollup=None,
    )


class TestD6R12MemoryAttributedRealDiagnostic(unittest.TestCase):
    def test_snapshot_schedule_is_exact_and_bounded(self):
        schedule = d.wakeup_snapshot_schedule()
        self.assertEqual(schedule[0], 1)
        self.assertEqual(schedule[1], 250_000)
        self.assertEqual(schedule[-1], 7_500_000)
        self.assertEqual(len(schedule), 31)
        self.assertEqual(len(schedule), len(set(schedule)))
        self.assertTrue(all(point <= c.BOUNDED_WAKEUP_TARGET for point in schedule))
        self.assertTrue(all(point in schedule for point in c.SPECIFIC_WAKEUP_CAPTURES))

    def test_snapshot_due_semantics_and_overshoot_fail_closed(self):
        self.assertFalse(d.snapshot_due_at_wakeup(0))
        self.assertTrue(d.snapshot_due_at_wakeup(1))
        self.assertFalse(d.snapshot_due_at_wakeup(249_999))
        self.assertTrue(d.snapshot_due_at_wakeup(250_000))
        self.assertTrue(d.snapshot_due_at_wakeup(c.BOUNDED_WAKEUP_TARGET))
        with self.assertRaisesRegex(d.D6R12DesignError, c.TARGET_OVERSHOOT_ERROR):
            d.snapshot_due_at_wakeup(c.BOUNDED_WAKEUP_TARGET + 1)

    def test_crossing_and_deliberate_bounded_terminal_reason(self):
        before = d.evaluate_wakeup_progress(6_500_000)
        crossed = d.evaluate_wakeup_progress(6_500_001)
        terminal = d.evaluate_wakeup_progress(7_500_000)
        self.assertFalse(before.crossed_old_failure_region)
        self.assertTrue(crossed.crossed_old_failure_region)
        self.assertFalse(crossed.bounded_wakeup_reached)
        self.assertIsNone(crossed.terminal_reason)
        self.assertTrue(terminal.crossed_old_failure_region)
        self.assertTrue(terminal.bounded_wakeup_reached)
        self.assertEqual(terminal.terminal_reason, c.BOUNDED_TARGET_TERMINAL_REASON)
        with self.assertRaisesRegex(d.D6R12DesignError, c.TARGET_OVERSHOOT_ERROR):
            d.evaluate_wakeup_progress(7_500_001)

    def test_snapshot_serialization_preserves_attribution(self):
        snapshot = _snapshot(
            vm_rss=9_000,
            rss_anon=2_000,
            rss_file=6_500,
            rss_shmem=500,
            memavailable=12_000,
            vm_swap=10,
        )
        sample = d.DiagnosticMemorySample("market_wakeup_6500000", 6_500_000, snapshot)
        payload = json.loads(d.serialize_memory_samples([sample]))
        self.assertEqual(len(payload), 1)
        observed = payload[0]
        self.assertEqual(observed["capture_point"], "market_wakeup_6500000")
        self.assertEqual(observed["market_wakeups"], 6_500_000)
        self.assertEqual(observed["process"]["VmRSS_bytes"], 9_000)
        self.assertEqual(observed["process"]["RssAnon_bytes"], 2_000)
        self.assertEqual(observed["process"]["RssFile_bytes"], 6_500)
        self.assertEqual(observed["process"]["RssShmem_bytes"], 500)
        self.assertEqual(observed["process"]["resident_components_bytes"], 9_000)
        self.assertEqual(observed["process"]["rss_decomposition_delta_bytes"], 0)
        self.assertEqual(observed["system"]["MemAvailable_bytes"], 12_000)
        self.assertFalse(observed["smaps_rollup_available"])

    def test_peak_and_minimum_summary_calculations(self):
        samples = (
            d.DiagnosticMemorySample(
                "before_source_open",
                None,
                _snapshot(vm_rss=100, rss_anon=60, rss_file=40, memavailable=1000, vm_swap=0),
            ),
            d.DiagnosticMemorySample(
                "market_wakeup_7500000",
                7_500_000,
                _snapshot(
                    vm_rss=900,
                    rss_anon=150,
                    rss_file=700,
                    rss_shmem=50,
                    memavailable=700,
                    vm_swap=20,
                ),
            ),
        )
        summary = d.summarize_memory_samples(samples)
        self.assertEqual(
            summary.to_dict(),
            {
                "peak_vm_rss_bytes": 900,
                "peak_rss_anon_bytes": 150,
                "peak_rss_file_bytes": 700,
                "peak_rss_shmem_bytes": 50,
                "minimum_memavailable_bytes": 700,
                "peak_vm_swap_bytes": 20,
            },
        )

    def test_procfs_attribution_failure_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r12_procfs_") as td:
            root = Path(td)
            status = root / "status"
            meminfo = root / "meminfo"
            status.write_text(
                "VmRSS: 5 kB\nRssAnon: 2 kB\nRssShmem: 0 kB\n",
                encoding="ascii",
            )
            meminfo.write_text("MemAvailable: 10 kB\n", encoding="ascii")
            with self.assertRaisesRegex(memory.MemoryAttributionError, "status_missing:RssFile"):
                memory.capture_memory_snapshot(
                    status_path=status,
                    meminfo_path=meminfo,
                    smaps_rollup_path=None,
                )

    def test_preexecution_memavailable_gate_is_inherited(self):
        below = _snapshot(
            vm_rss=100,
            rss_anon=60,
            rss_file=40,
            memavailable=c.PREEXEC_MIN_MEMAVAILABLE_BYTES - 1,
        )
        exact = _snapshot(
            vm_rss=100,
            rss_anon=60,
            rss_file=40,
            memavailable=c.PREEXEC_MIN_MEMAVAILABLE_BYTES,
        )
        self.assertEqual(
            d.preexecution_failure_reason(below),
            "PREEXEC_MEMAVAILABLE_BELOW_MINIMUM",
        )
        self.assertIsNone(d.preexecution_failure_reason(exact))

    def test_runtime_memavailable_is_measured_but_does_not_abort(self):
        baseline = _snapshot(vm_rss=100, rss_anon=60, rss_file=40, vm_swap=0)
        low_available = _snapshot(
            vm_rss=10_000,
            rss_anon=100,
            rss_file=9_900,
            memavailable=c.PREEXEC_MIN_MEMAVAILABLE_BYTES - 1,
            vm_swap=0,
        )
        sample = d.DiagnosticMemorySample("market_wakeup_250000", 250_000, low_available)
        self.assertEqual(
            d.summarize_memory_samples([sample]).minimum_memavailable_bytes,
            c.PREEXEC_MIN_MEMAVAILABLE_BYTES - 1,
        )
        self.assertIsNone(d.hard_safety_abort_reason(baseline, low_available))
        runtime_source = inspect.getsource(d.hard_safety_abort_reason)
        self.assertNotIn("mem_available", runtime_source)
        self.assertNotIn("PREEXEC_MIN_MEMAVAILABLE_BYTES", runtime_source)

    def test_runtime_swap_growth_is_a_baseline_relative_candidate_guard(self):
        baseline = _snapshot(vm_rss=100, rss_anon=60, rss_file=40, vm_swap=3)
        swapped = _snapshot(vm_rss=200, rss_anon=100, rss_file=100, vm_swap=1)
        grown = _snapshot(vm_rss=200, rss_anon=100, rss_file=100, vm_swap=4)
        self.assertIsNone(d.hard_safety_abort_reason(baseline, swapped))
        self.assertEqual(
            d.hard_safety_abort_reason(baseline, grown),
            "PROCESS_SWAP_GROWTH",
        )

    def test_total_rss_and_file_residency_alone_do_not_abort(self):
        baseline = _snapshot(vm_rss=100, rss_anon=60, rss_file=40, vm_swap=0)
        file_resident = _snapshot(
            vm_rss=50_000_000_000,
            rss_anon=60,
            rss_file=49_999_999_940,
            memavailable=1,
            vm_swap=0,
        )
        self.assertIsNone(d.hard_safety_abort_reason(baseline, file_resident))
        safety_source = inspect.getsource(d.hard_safety_abort_reason)
        self.assertNotIn("vm_rss", safety_source)
        self.assertNotIn("mem_available", safety_source)
        self.assertNotIn("OLD_D6R10_ABORT_BYTES", safety_source)

    def test_missing_required_diagnostic_status_field_fails_closed(self):
        incomplete = _snapshot(vm_rss=100, rss_anon=60, rss_file=40, vm_swap=None)
        with self.assertRaisesRegex(d.D6R12DesignError, "status_field_missing:VmSwap"):
            d.summarize_memory_samples(
                [d.DiagnosticMemorySample("before_source_open", None, incomplete)]
            )

    def test_attempt_marker_semantics_are_one_shot(self):
        self.assertEqual(d.attempt_state(marker_exists=False, evidence_exists=False), "FRESH")
        for marker, evidence in ((True, False), (False, True), (True, True)):
            with self.subTest(marker=marker, evidence=evidence):
                self.assertEqual(
                    d.attempt_state(marker_exists=marker, evidence_exists=evidence),
                    "CONSUMED_NO_RERUN",
                )

    def test_closed_evidence_flags_are_all_false(self):
        flags = d.closed_evidence_flags()
        self.assertEqual(set(flags), {
            "full_day_attempted",
            "full_day_validated",
            "canonical_npy_written",
            "raw_csv_opened",
            "converter_rerun",
            "orders",
            "policy_execution",
            "historical_pnl",
            "economic_arena",
            "aug_opened",
            "sep_plus_opened",
            "non_btc_opened",
            "network_acquisition",
            "railway_touched",
            "live_trading_authorized",
        })
        self.assertTrue(all(value is False for value in flags.values()))

    def test_design_helper_has_no_canonical_execution_entrypoint(self):
        source = IMPLEMENTATION.read_text(encoding="utf-8")
        self.assertNotIn("hftbacktest", source)
        self.assertNotIn("np.load", source)
        self.assertNotIn("open_verified_file", source)
        self.assertNotIn("SOURCE_PATH", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("argparse", source)

        tree = ast.parse(source)
        function_names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }
        self.assertNotIn("main", function_names)
        self.assertNotIn("run", function_names)
        self.assertNotIn("run_sequence", function_names)


if __name__ == "__main__":
    unittest.main()

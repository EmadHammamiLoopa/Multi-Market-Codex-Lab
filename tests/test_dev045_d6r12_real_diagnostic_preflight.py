from __future__ import annotations

import hashlib
import inspect
import json
import mmap
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from multimarket import dev045_d6r11_memory_attribution as memory
from multimarket import dev045_d6r12_memory_attributed_real_diagnostic as design
from multimarket import dev045_d6r12_real_diagnostic_preflight as p
from multimarket import dev045_d6r12_real_diagnostic_preflight_contract as c


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _snapshot(
    *,
    vm_rss: int = 100,
    rss_anon: int = 60,
    rss_file: int = 40,
    memavailable: int = 20_000_000_000,
    vm_swap: int | None = 0,
    timestamp: str = "2026-09-06T00:00:00+00:00",
) -> memory.MemorySnapshot:
    return memory.MemorySnapshot(
        captured_at_utc=timestamp,
        pid=123,
        process=memory.ProcessMemory(
            vm_rss_bytes=vm_rss,
            rss_anon_bytes=rss_anon,
            rss_file_bytes=rss_file,
            rss_shmem_bytes=0,
            vm_size_bytes=1_000,
            vm_data_bytes=500,
            vm_swap_bytes=vm_swap,
        ),
        mem_available_bytes=memavailable,
        smaps_rollup=None,
    )


def _write_bytes(path: Path, payload: bytes) -> tuple[Path, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path, hashlib.sha256(payload).hexdigest()


def _synthetic_preflight(root: Path) -> tuple[p.PreflightConfig, p.PreflightDependencies]:
    source = root / "synthetic_source.npy"
    with source.open("wb") as handle:
        handle.truncate(128)

    lineage_payload = {
        "status": "PASS",
        "output_sha256": "a" * 64,
        "output_header": {"rows": 2, "output_bytes": 128},
    }
    lineage, lineage_sha = _write_bytes(
        root / "lineage.json",
        (json.dumps(lineage_payload, sort_keys=True) + "\n").encode(),
    )
    design_freeze, design_freeze_sha = _write_bytes(root / "design_freeze.json", b"design\n")
    d6r11_freeze, d6r11_freeze_sha = _write_bytes(root / "d6r11.json", b"d6r11\n")
    d6r10_evidence, d6r10_evidence_sha = _write_bytes(root / "d6r10.json", b"d6r10\n")
    d6r10_marker, d6r10_marker_sha = _write_bytes(root / "d6r10_marker.json", b"marker\n")
    d6r10_heartbeat, d6r10_heartbeat_sha = _write_bytes(
        root / "d6r10_heartbeat.json", b"heartbeat\n"
    )

    config = p.PreflightConfig(
        repo_root=root,
        source_path=source,
        source_rows=2,
        source_bytes=128,
        source_sha256="a" * 64,
        source_lineage_evidence_path=lineage,
        source_lineage_evidence_sha256=lineage_sha,
        design_freeze_manifest_path=design_freeze,
        design_freeze_manifest_sha256=design_freeze_sha,
        d6r11_freeze_manifest_path=d6r11_freeze,
        d6r11_freeze_manifest_sha256=d6r11_freeze_sha,
        d6r10_evidence_path=d6r10_evidence,
        d6r10_evidence_sha256=d6r10_evidence_sha,
        d6r10_attempt_marker_path=d6r10_marker,
        d6r10_attempt_marker_sha256=d6r10_marker_sha,
        d6r10_heartbeat_path=d6r10_heartbeat,
        d6r10_heartbeat_sha256=d6r10_heartbeat_sha,
        runtime_root=root / "runtime" / "dev045_d6r12" / "synthetic",
        attempt_marker_path=root / "runtime" / "dev045_d6r12" / "synthetic" / "ATTEMPT_STARTED.json",
        evidence_path=root / "synthetic_evidence.json",
    )
    deps = p.PreflightDependencies(
        verify_git_lineage_and_cleanliness=lambda _: None,
        installed_hftbacktest_version=lambda: "2.4.4",
        capture_memory=_snapshot,
    )
    return config, deps


class _FakeMmap:
    def __init__(self, events: list[object]):
        self.events = events
        self.madvise_calls: list[int] = []

    def madvise(self, advice: int) -> None:
        self.madvise_calls.append(advice)
        self.events.append(("madvise", advice))


class _FakeSource:
    def __init__(self, events: list[object]):
        self.events = events
        self.data = SimpleNamespace(_mmap=_FakeMmap(events))
        self._closed = False
        self.close_calls = 0

    def close(self) -> None:
        if self._closed:
            return
        self.close_calls += 1
        self.events.append("memmap_close")
        self._closed = True


class _FakeBacktest:
    def __init__(self, events: list[object], feed_results: list[int] | None = None):
        self.events = events
        self.feed_results = list(feed_results or [])
        self.wait_calls = 0
        self.current_timestamp = 0
        self.close_calls = 0

    def wait_next_feed(self, include_order_response: bool, timeout: int) -> int:
        self.wait_calls += 1
        rc = self.feed_results.pop(0) if self.feed_results else 2
        if rc == 2:
            self.current_timestamp += 1_000
        return rc

    def position(self, asset_no: int) -> float:
        return 0.0

    def orders(self, asset_no: int) -> dict[object, object]:
        return {}

    def close(self) -> int:
        self.close_calls += 1
        self.events.append("backtest_close")
        return 0


class _FakeBinding:
    def __init__(
        self,
        source: _FakeSource,
        events: list[object],
        feed_results: list[int] | None = None,
    ):
        self.source = source
        self.bt = _FakeBacktest(events, feed_results)
        self.lifecycle = ["memmap_opened_verified", "asset_registered", "backtest_built"]
        self._closed = False


class TestD6R12RealDiagnosticPreflight(unittest.TestCase):
    def test_preflight_uses_stat_only_and_returns_no_content_open(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r12_preflight_") as td:
            config, deps = _synthetic_preflight(Path(td))
            original_open = Path.open

            def guarded_open(path: Path, *args, **kwargs):
                if path.resolve(strict=False) == config.source_path.resolve(strict=False):
                    raise AssertionError("source_content_opened")
                return original_open(path, *args, **kwargs)

            with mock.patch.object(Path, "open", guarded_open):
                result = p.run_preflight(config, deps)
            self.assertTrue(result.source_stat_verified)
            self.assertTrue(result.source_lineage_verified)
            self.assertFalse(result.source_content_opened)
            self.assertFalse(result.source_content_sha_verified)
            self.assertEqual(result.attempt_state, "FRESH")
            self.assertFalse(result.to_dict()["attempt_marker_created"])

    def test_preflight_memavailable_gate_is_separate_and_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r12_preflight_mem_") as td:
            config, deps = _synthetic_preflight(Path(td))
            low = p.PreflightDependencies(
                deps.verify_git_lineage_and_cleanliness,
                deps.installed_hftbacktest_version,
                lambda: _snapshot(memavailable=c.PREEXEC_MIN_MEMAVAILABLE_BYTES - 1),
            )
            with self.assertRaisesRegex(p.D6R12PreflightError, "PREEXEC_MEMAVAILABLE"):
                p.run_preflight(config, low)

    def test_preflight_rejects_missing_vmswap_and_wrong_hft_version(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r12_preflight_fields_") as td:
            config, deps = _synthetic_preflight(Path(td))
            missing_swap = p.PreflightDependencies(
                deps.verify_git_lineage_and_cleanliness,
                deps.installed_hftbacktest_version,
                lambda: _snapshot(vm_swap=None),
            )
            with self.assertRaisesRegex(design.D6R12DesignError, "VmSwap"):
                p.run_preflight(config, missing_swap)

            wrong_version = p.PreflightDependencies(
                deps.verify_git_lineage_and_cleanliness,
                lambda: "2.4.5",
                deps.capture_memory,
            )
            with self.assertRaisesRegex(p.D6R12PreflightError, "hftbacktest_version:2.4.5"):
                p.run_preflight(config, wrong_version)

    def test_preflight_source_size_and_lineage_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r12_preflight_source_") as td:
            config, deps = _synthetic_preflight(Path(td))
            bad_size = p.PreflightConfig(**{**config.__dict__, "source_bytes": 129})
            with self.assertRaisesRegex(p.D6R12PreflightError, "source_bytes:128"):
                p.run_preflight(bad_size, deps)

            bad_sha = p.PreflightConfig(**{**config.__dict__, "source_sha256": "b" * 64})
            with self.assertRaisesRegex(p.D6R12PreflightError, "source_lineage_sha256"):
                p.run_preflight(bad_sha, deps)

    def test_one_shot_state_blocks_existing_marker_without_writing(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r12_preflight_attempt_") as td:
            config, deps = _synthetic_preflight(Path(td))
            config.attempt_marker_path.parent.mkdir(parents=True)
            config.attempt_marker_path.write_text("existing\n")
            with self.assertRaisesRegex(p.D6R12PreflightError, "CONSUMED_NO_RERUN"):
                p.run_preflight(config, deps)
            self.assertEqual(config.attempt_marker_path.read_text(), "existing\n")

    def test_exact_token_is_required_but_contract_lock_still_blocks(self):
        with self.assertRaisesRegex(p.D6R12PreflightError, "authorization_token"):
            p.require_execution_authorization({})
        with self.assertRaisesRegex(p.D6R12PreflightError, "authorization_token"):
            p.require_execution_authorization({c.AUTHORIZATION_ENV: "wrong"})
        with self.assertRaisesRegex(p.D6R12PreflightError, "execution_disabled_by_contract"):
            p.require_execution_authorization({c.AUTHORIZATION_ENV: c.AUTHORIZATION_TOKEN})
        with mock.patch.object(p, "run_preflight") as preflight:
            with self.assertRaisesRegex(p.D6R12PreflightError, "execution_disabled_by_contract"):
                p.run_real_parent({c.AUTHORIZATION_ENV: c.AUTHORIZATION_TOKEN})
            preflight.assert_not_called()

    def test_synthetic_bounded_child_stops_exactly_and_splits_close_snapshots(self):
        events: list[object] = []
        heartbeats: list[dict[str, object]] = []
        source = _FakeSource(events)
        binding = _FakeBinding(source, events)
        deps = p.BoundedDiagnosticDependencies(
            capture_memory=_snapshot,
            open_source=lambda: source,
            build_binding=lambda observed: binding,
            source_identity=lambda: (1, 2, 128, 3),
            persist_heartbeat=lambda payload: (
                heartbeats.append(payload),
                events.append(("capture", payload["capture_point"])),
            ),
        )
        outcome = p.run_bounded_diagnostic(deps, target=4, capture_interval=2)
        self.assertEqual(outcome.market_wakeups, 4)
        self.assertEqual(outcome.terminal_reason, c.BOUNDED_TARGET_TERMINAL_REASON)
        self.assertEqual(binding.bt.wait_calls, 4)
        self.assertEqual(binding.bt.close_calls, 1)
        self.assertEqual(source.close_calls, 1)
        self.assertEqual(
            outcome.lifecycle[-2:],
            ("backtest_closed", "memmap_closed"),
        )
        self.assertEqual(source.data._mmap.madvise_calls, [mmap.MADV_SEQUENTIAL])
        self.assertLess(events.index("backtest_close"), events.index(("capture", "after_backtest_close")))
        self.assertLess(events.index(("capture", "after_backtest_close")), events.index("memmap_close"))
        self.assertLess(events.index("memmap_close"), events.index(("capture", "after_memmap_close")))
        self.assertEqual(heartbeats[-1]["capture_point"], "after_memmap_close")

        p.close_with_separate_snapshots(
            binding,
            lambda point: design.DiagnosticMemorySample(point, 4, _snapshot()),
        )
        self.assertEqual(binding.bt.close_calls, 1)
        self.assertEqual(source.close_calls, 1)

    def test_end_of_data_before_target_fails_and_still_closes_in_order(self):
        events: list[object] = []
        source = _FakeSource(events)
        binding = _FakeBinding(source, events, [2, 1])
        deps = p.BoundedDiagnosticDependencies(
            capture_memory=_snapshot,
            open_source=lambda: source,
            build_binding=lambda observed: binding,
            source_identity=lambda: (1, 2, 128, 3),
            persist_heartbeat=lambda payload: None,
        )
        with self.assertRaisesRegex(p.D6R12PreflightError, "end_of_data_before_target:1:4"):
            p.run_bounded_diagnostic(deps, target=4, capture_interval=2)
        self.assertEqual(binding.bt.close_calls, 1)
        self.assertEqual(source.close_calls, 1)
        self.assertEqual(binding.lifecycle[-2:], ["backtest_closed", "memmap_closed"])

    def test_post_open_attribution_failure_still_closes_memmap(self):
        events: list[object] = []
        source = _FakeSource(events)
        capture_calls = 0

        def capture_memory() -> memory.MemorySnapshot:
            nonlocal capture_calls
            capture_calls += 1
            if capture_calls == 2:
                raise memory.MemoryAttributionError("synthetic procfs failure")
            return _snapshot()

        deps = p.BoundedDiagnosticDependencies(
            capture_memory=capture_memory,
            open_source=lambda: source,
            build_binding=lambda observed: self.fail("binding must not be built"),
            source_identity=lambda: (1, 2, 128, 3),
            persist_heartbeat=lambda payload: None,
        )
        with self.assertRaisesRegex(memory.MemoryAttributionError, "procfs failure"):
            p.run_bounded_diagnostic(deps, target=2, capture_interval=1)
        self.assertEqual(source.close_calls, 1)
        self.assertEqual(events[-1], "memmap_close")

    def test_failed_close_attempt_is_not_retried_or_double_closed(self):
        events: list[object] = []
        source = _FakeSource(events)
        binding = _FakeBinding(source, events)
        binding.bt.close = mock.Mock(side_effect=RuntimeError("synthetic close failure"))
        capture = lambda point: design.DiagnosticMemorySample(point, None, _snapshot())

        with self.assertRaisesRegex(RuntimeError, "synthetic close failure"):
            p.close_with_separate_snapshots(binding, capture)
        self.assertEqual(binding.bt.close.call_count, 1)
        self.assertEqual(source.close_calls, 0)

        with self.assertRaisesRegex(p.D6R12PreflightError, "backtest_close_incomplete"):
            p.close_with_separate_snapshots(binding, capture)
        self.assertEqual(binding.bt.close.call_count, 1)
        self.assertEqual(source.close_calls, 0)

    def test_runtime_rss_file_and_memavailable_do_not_abort(self):
        events: list[object] = []
        source = _FakeSource(events)
        binding = _FakeBinding(source, events)
        high_file_low_available = lambda: _snapshot(
            vm_rss=50_000_000_000,
            rss_anon=100,
            rss_file=49_999_999_900,
            memavailable=1,
            vm_swap=0,
        )
        deps = p.BoundedDiagnosticDependencies(
            capture_memory=high_file_low_available,
            open_source=lambda: source,
            build_binding=lambda observed: binding,
            source_identity=lambda: (1, 2, 128, 3),
            persist_heartbeat=lambda payload: None,
        )
        outcome = p.run_bounded_diagnostic(deps, target=2, capture_interval=1)
        self.assertEqual(outcome.market_wakeups, 2)
        self.assertEqual(outcome.summary.peak_rss_file_bytes, 49_999_999_900)
        self.assertEqual(outcome.summary.minimum_memavailable_bytes, 1)

    def test_runtime_vmswap_growth_is_baseline_relative(self):
        events: list[object] = []
        source = _FakeSource(events)
        binding = _FakeBinding(source, events)
        capture_count = 0

        def capture_memory() -> memory.MemorySnapshot:
            nonlocal capture_count
            capture_count += 1
            return _snapshot(vm_swap=5 if capture_count <= 3 else 6)

        deps = p.BoundedDiagnosticDependencies(
            capture_memory=capture_memory,
            open_source=lambda: source,
            build_binding=lambda observed: binding,
            source_identity=lambda: (1, 2, 128, 3),
            persist_heartbeat=lambda payload: None,
        )
        with self.assertRaisesRegex(p.D6R12PreflightError, "PROCESS_SWAP_GROWTH"):
            p.run_bounded_diagnostic(deps, target=2, capture_interval=1)
        self.assertEqual(binding.lifecycle[-2:], ["backtest_closed", "memmap_closed"])

    def test_atomic_heartbeat_contains_required_metrics_and_history(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r12_heartbeat_") as td:
            path = Path(td) / "MEMORY_HEARTBEAT.json"
            sample = design.DiagnosticMemorySample("market_wakeup_1", 1, _snapshot())
            payload = p.build_memory_heartbeat([sample], current_timestamp_ns=1234)
            p.atomic_write_json(path, payload)
            observed = json.loads(path.read_text())
            self.assertEqual(observed["market_wakeups"], 1)
            self.assertEqual(observed["current_timestamp_ns"], 1234)
            for field in (
                "VmRSS_bytes",
                "RssAnon_bytes",
                "RssFile_bytes",
                "RssShmem_bytes",
                "VmSize_bytes",
                "VmData_bytes",
                "VmSwap_bytes",
                "resident_components_bytes",
                "rss_decomposition_delta_bytes",
                "MemAvailable_bytes",
                "current_summary",
                "memory_snapshots",
                "updated_at_utc",
            ):
                self.assertIn(field, observed)
            self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_parent_failure_evidence_retains_latest_heartbeat(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r12_parent_") as td:
            root = Path(td)
            marker = root / "runtime" / "ATTEMPT_STARTED.json"
            heartbeat = root / "runtime" / "MEMORY_HEARTBEAT.json"
            evidence = root / "evidence.json"
            sample = design.DiagnosticMemorySample(
                "after_verified_memmap_open",
                None,
                _snapshot(),
            )
            p.atomic_write_json(
                heartbeat,
                p.build_memory_heartbeat([sample], current_timestamp_ns=None),
            )
            expected_heartbeat_sha = _sha256(heartbeat)
            result = p.run_parent_attempt(
                marker_path=marker,
                evidence_path=evidence,
                heartbeat_path=heartbeat,
                child_runner=lambda: p.ChildProcessResult(1, "", "synthetic failure"),
            )
            self.assertTrue(marker.is_file())
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["child_return_code"], 1)
            self.assertIn("synthetic failure", result["child_stderr_tail"])
            self.assertEqual(result["latest_heartbeat_sha256"], expected_heartbeat_sha)
            self.assertEqual(len(result["memory_snapshots"]), 1)
            self.assertTrue(result["source_content_opened"])
            with self.assertRaisesRegex(p.D6R12PreflightError, "CONSUMED_NO_RERUN"):
                p.run_parent_attempt(
                    marker_path=marker,
                    evidence_path=evidence,
                    heartbeat_path=heartbeat,
                    child_runner=lambda: p.ChildProcessResult(0, "{}\n", ""),
                )

    def test_one_shot_marker_creation_is_exclusive_and_never_overwrites(self):
        with tempfile.TemporaryDirectory(prefix="dev045_d6r12_marker_") as td:
            marker = Path(td) / "ATTEMPT_STARTED.json"
            p.create_one_shot_marker(marker, {"attempt": 1})
            original = marker.read_bytes()
            with self.assertRaisesRegex(p.D6R12PreflightError, "attempt_marker_exists"):
                p.create_one_shot_marker(marker, {"attempt": 2})
            self.assertEqual(marker.read_bytes(), original)

    def test_parent_rejects_false_success_semantics(self):
        payload = {
            "bounded_wakeup_reached": False,
            "market_wakeups": c.BOUNDED_WAKEUP_TARGET - 1,
        }
        with self.assertRaisesRegex(p.D6R12PreflightError, "child_success_invariant"):
            p._validate_child_success_payload(payload)

    def test_preflight_source_check_has_no_content_read_or_hash(self):
        source = inspect.getsource(p._verify_source_stat_only)
        self.assertIn("os.stat", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("sha256", source)
        self.assertNotIn("read", source)

    def test_execution_source_has_no_policy_order_or_pnl_surface(self):
        source = inspect.getsource(p)
        self.assertNotIn("submit_", source)
        self.assertNotIn("cancel_", source)
        self.assertNotIn("dev045_m3_policy", source)
        self.assertNotIn("economic_arena", source)
        self.assertNotIn("calculate_pnl", source)
        self.assertNotIn("RSS_ABORT_BYTES", source)
        runtime_guard = inspect.getsource(design.hard_safety_abort_reason)
        self.assertNotIn("MIN_MEMAVAILABLE_BYTES", runtime_guard)
        self.assertNotIn("mem_available", runtime_guard)
        self.assertNotIn("vm_rss", runtime_guard)


if __name__ == "__main__":
    unittest.main()

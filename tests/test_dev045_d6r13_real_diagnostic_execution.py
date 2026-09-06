from __future__ import annotations

import unittest

from multimarket import dev045_d6r11_memory_attribution as memory
from multimarket import dev045_d6r13_real_diagnostic_execution as execution
from multimarket import dev045_d6r13_real_diagnostic_execution_contract as c


def _snapshot() -> memory.MemorySnapshot:
    return memory.MemorySnapshot(
        captured_at_utc="2026-09-06T00:00:00Z",
        pid=12345,
        process=memory.ProcessMemory(
            vm_rss_bytes=100,
            rss_anon_bytes=40,
            rss_file_bytes=60,
            rss_shmem_bytes=0,
            vm_size_bytes=200,
            vm_data_bytes=30,
            vm_swap_bytes=0,
        ),
        mem_available_bytes=12_000_000_000,
        smaps_rollup=None,
    )


class _Source:
    def __init__(self) -> None:
        self._closed = False
        self.data = object()

    def close(self) -> None:
        self._closed = True


class _BT:
    def __init__(self) -> None:
        self.current_timestamp = 0
        self.wakeups = 0
        self.close_calls = 0

    def wait_next_feed(self, _include_order_resp: bool, _timeout: int) -> int:
        self.wakeups += 1
        self.current_timestamp = self.wakeups * 1000
        return 2

    def position(self, _asset: int) -> float:
        return 0.0

    def orders(self, _asset: int) -> dict[object, object]:
        return {}

    def close(self) -> int:
        self.close_calls += 1
        return 0


class _Binding:
    def __init__(self, source: _Source) -> None:
        self.source = source
        self.bt = _BT()
        self.lifecycle: list[str] = []
        self._closed = False


class TestD6R13RealDiagnosticExecution(unittest.TestCase):
    def test_contract_remains_closed(self):
        self.assertIs(c.REAL_EXECUTION_ENABLED, False)
        self.assertEqual(c.PROHIBITED_EXECUTION_FLAGS, (False,) * len(c.PROHIBITED_EXECUTION_FLAGS))
        self.assertIs(c.D6R12_RERUN_FORBIDDEN, True)
        self.assertIs(c.D6R12_DIAGNOSTIC_QUESTION_ANSWERED, False)
        self.assertEqual(c.BOUNDED_WAKEUP_TARGET, 7_500_000)
        self.assertEqual(c.WAKEUP_CAPTURE_INTERVAL, 250_000)

    def test_child_command_uses_fixed_module_name(self):
        command = execution.child_command(smoke=False)
        self.assertEqual(command[1:3], ["-m", c.CHILD_MODULE_NAME])
        self.assertNotIn("__main__", command)
        self.assertEqual(command[-1], c.CHILD_FLAG)

    def test_module_level_child_resolution_smoke_is_noncanonical(self):
        result = execution.run_child_resolution_smoke()
        self.assertEqual(result.returncode, 0)
        payload = result.payload
        self.assertEqual(payload["runtime_name"], "__main__")
        self.assertEqual(payload["resolved_module_name"], c.CHILD_MODULE_NAME)
        self.assertFalse(payload["canonical_data_opened"])
        self.assertFalse(payload["attempt_marker_created"])
        self.assertFalse(payload["heartbeat_created"])
        self.assertFalse(payload["hftbacktest_canonical_run"])

    def test_authorization_cannot_open_execution_during_implementation_stage(self):
        with self.assertRaisesRegex(execution.D6R13ExecutionError, "authorization_token"):
            execution.require_execution_authorization({})
        with self.assertRaisesRegex(execution.D6R13ExecutionError, "execution_disabled_by_contract"):
            execution.require_execution_authorization({c.AUTHORIZATION_ENV: c.AUTHORIZATION_TOKEN})

    def test_synthetic_bounded_traversal_stops_exactly_and_closes_in_order(self):
        source = _Source()
        binding = _Binding(source)
        heartbeats: list[dict[str, object]] = []
        identity = (1, 2, 3, 4)
        deps = execution.BoundedDependencies(
            capture_memory=_snapshot,
            open_source=lambda: source,
            build_binding=lambda observed: binding if observed is source else None,
            source_identity=lambda: identity,
            persist_heartbeat=lambda payload: heartbeats.append(payload),
        )
        outcome = execution.run_bounded_diagnostic(deps, target=4, capture_interval=2)
        self.assertEqual(outcome.market_wakeups, 4)
        self.assertEqual(outcome.terminal_reason, c.BOUNDED_TARGET_TERMINAL_REASON)
        self.assertEqual(binding.bt.wakeups, 4)
        self.assertEqual(binding.bt.close_calls, 1)
        self.assertTrue(source._closed)
        self.assertTrue(binding._closed)
        self.assertEqual(outcome.lifecycle[-2:], ("backtest_closed", "memmap_closed"))
        self.assertEqual(outcome.position, 0.0)
        self.assertEqual(outcome.working_order_count, 0)
        points = [sample.capture_point for sample in outcome.memory_samples]
        self.assertIn("market_wakeup_1", points)
        self.assertIn("market_wakeup_2", points)
        self.assertIn("market_wakeup_4", points)
        self.assertIn("after_backtest_close", points)
        self.assertIn("after_memmap_close", points)
        self.assertGreaterEqual(len(heartbeats), len(outcome.memory_samples))

    def test_evidence_uses_d6r13_identity_and_closed_economic_flags(self):
        source = _Source()
        binding = _Binding(source)
        deps = execution.BoundedDependencies(
            capture_memory=_snapshot,
            open_source=lambda: source,
            build_binding=lambda _source: binding,
            source_identity=lambda: (1, 2, 3, 4),
            persist_heartbeat=lambda _payload: None,
        )
        payload = execution.run_bounded_diagnostic(deps, target=2, capture_interval=1).to_evidence_dict()
        self.assertEqual(payload["experiment_id"], "DEV045-D6R13")
        self.assertTrue(payload["bounded_wakeup_reached"] is False)  # canonical target remains 7.5M
        self.assertFalse(payload["orders"])
        self.assertFalse(payload["policy_execution"])
        self.assertFalse(payload["historical_pnl"])
        self.assertFalse(payload["full_day_attempted"])


if __name__ == "__main__":
    unittest.main()

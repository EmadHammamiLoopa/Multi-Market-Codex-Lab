from __future__ import annotations

import unittest

from multimarket import dev045_d6r11_memory_attribution as memory
from multimarket import dev045_d6r15_full_day_contract as c
from multimarket import dev045_d6r15_full_day_execution as x


def safe_snapshot(
    *,
    swap: int = 0,
    anon: int = 70_000_000,
    file_rss: int = 80_000_000,
    available: int = 12_000_000_000,
) -> memory.MemorySnapshot:
    process = memory.ProcessMemory(
        vm_rss_bytes=(
            anon + file_rss
        ),
        rss_anon_bytes=anon,
        rss_file_bytes=file_rss,
        rss_shmem_bytes=0,
        vm_size_bytes=12_000_000_000,
        vm_data_bytes=anon,
        vm_swap_bytes=swap,
    )

    return memory.MemorySnapshot(
        captured_at_utc=(
            "2026-09-06T00:00:00+00:00"
        ),
        pid=12345,
        process=process,
        mem_available_bytes=available,
        smaps_rollup=None,
    )


class FakeSource:
    def __init__(self) -> None:
        self.data = object()
        self._closed = False

    def close(self) -> None:
        self._closed = True


class FakeBT:
    def __init__(
        self,
        timestamps: list[int],
    ) -> None:
        self.timestamps = list(
            timestamps
        )
        self.index = 0
        self.current_timestamp = 0
        self.closed = False

    def wait_next_feed(
        self,
        include_order_resp: bool,
        timeout_ns: int,
    ) -> int:
        del include_order_resp
        del timeout_ns

        if self.index >= len(
            self.timestamps
        ):
            return 1

        self.current_timestamp = (
            self.timestamps[self.index]
        )

        self.index += 1

        return 2

    def position(
        self,
        asset_no: int,
    ) -> float:
        del asset_no
        return 0.0

    def orders(
        self,
        asset_no: int,
    ) -> dict[int, object]:
        del asset_no
        return {}

    def close(self) -> int:
        self.closed = True
        return 0


class FakeBinding:
    def __init__(
        self,
        source: FakeSource,
        timestamps: list[int],
    ) -> None:
        self.source = source
        self.bt = FakeBT(
            timestamps
        )
        self.lifecycle = [
            "memmap_opened_verified",
            "asset_registered",
            "backtest_built",
        ]
        self._closed = False


class TestD6R15FullDay(unittest.TestCase):
    def test_parent_lineage_and_memory_policy(self) -> None:
        self.assertEqual(
            c.PARENT_D6R14_FREEZE_HEAD,
            "82123ef416b97a9caa239ea80da5a9d1887ed552",
        )

        self.assertEqual(
            c.PARENT_D6R14_FREEZE_MANIFEST_SHA256,
            "63a1979e8c4ed61d2d28a9b17f5459ecdb1d8afd2abc78e56d79030625d9401b",
        )

        self.assertTrue(
            c.D6R12_RERUN_FORBIDDEN
        )

        self.assertTrue(
            c.D6R13_RERUN_FORBIDDEN
        )

        self.assertTrue(
            c.D6R13_DIAGNOSTIC_QUESTION_ANSWERED
        )

        self.assertFalse(
            c.ADDITIONAL_BOUNDED_MEMORY_DIAGNOSTIC_REQUIRED
        )

        self.assertIsNone(
            c.TOTAL_RSS_ABORT_THRESHOLD_BYTES
        )

        self.assertTrue(
            c.RUNTIME_ABORT_ON_PROCESS_SWAP_GROWTH
        )

    def test_reference_eod_is_post_terminal_not_stop_target(self) -> None:
        self.assertEqual(
            c.REFERENCE_EOD_WAKEUPS,
            7_139_910,
        )

        self.assertEqual(
            c.REFERENCE_LAST_TIMESTAMP_NS,
            1_769_990_399_913_791_000,
        )

        self.assertIsNone(
            c.FIXED_WAKEUP_STOP_TARGET
        )

        self.assertTrue(
            c.NATURAL_END_OF_DATA_IS_VALID_TERMINAL
        )

    def test_authorization_surface_is_exact(self) -> None:
        self.assertEqual(
            c.AUTHORIZED_EXECUTION_FLAGS,
            (True,)
            * len(
                c.AUTHORIZED_EXECUTION_FLAGS
            ),
        )

        self.assertEqual(
            c.PROHIBITED_EXECUTION_FLAGS,
            (False,)
            * len(
                c.PROHIBITED_EXECUTION_FLAGS
            ),
        )

        self.assertTrue(
            c.FULL_DAY_ATTEMPT_AUTHORIZED
        )

        self.assertTrue(
            c.FULL_DAY_VALIDATION_AUTHORIZED
        )

        self.assertFalse(
            c.MAR_TO_JUL_AUTHORIZED
        )

        self.assertFalse(
            c.HISTORICAL_PNL_AUTHORIZED
        )

        self.assertFalse(
            c.POLICY_EXECUTION_AUTHORIZED
        )

        self.assertFalse(
            c.ORDER_SUBMISSION_AUTHORIZED
        )

        self.assertFalse(
            c.CANONICAL_NPY_WRITE_AUTHORIZED
        )

    def test_exact_token_required(self) -> None:
        with self.assertRaisesRegex(
            x.D6R15ExecutionError,
            "authorization_token",
        ):
            x.require_execution_authorization(
                {}
            )

        with self.assertRaisesRegex(
            x.D6R15ExecutionError,
            "authorization_token",
        ):
            x.require_execution_authorization(
                {
                    c.AUTHORIZATION_ENV:
                    "WRONG"
                }
            )

        x.require_execution_authorization(
            {
                c.AUTHORIZATION_ENV:
                c.AUTHORIZATION_TOKEN
            }
        )

    def test_child_module_never_uses_runtime_name(self) -> None:
        command = x.child_command()

        self.assertEqual(
            command[1],
            "-m",
        )

        self.assertEqual(
            command[2],
            c.CHILD_MODULE_NAME,
        )

        self.assertNotIn(
            "__main__",
            command,
        )

    def test_child_resolution_smoke_is_noncanonical(self) -> None:
        result = x.run_child_resolution_smoke()

        self.assertEqual(
            result["status"],
            "PASS",
        )

        self.assertFalse(
            result["canonical_data_opened"]
        )

        self.assertFalse(
            result["full_day_attempted"]
        )

        self.assertFalse(
            result["hftbacktest_canonical_run"]
        )

    def test_synthetic_natural_eod_success(self) -> None:
        source = FakeSource()
        binding_holder = {}
        heartbeats: list[
            dict[str, object]
        ] = []

        def build_binding(
            observed_source: FakeSource,
        ) -> FakeBinding:
            binding = FakeBinding(
                observed_source,
                [100, 200, 300],
            )
            binding_holder["binding"] = (
                binding
            )
            return binding

        identity = (
            1,
            2,
            3,
            4,
        )

        deps = x.FullDayDependencies(
            capture_memory=(
                lambda: safe_snapshot()
            ),
            open_source=(
                lambda: source
            ),
            build_binding=(
                build_binding
            ),
            source_identity=(
                lambda: identity
            ),
            persist_heartbeat=(
                heartbeats.append
            ),
        )

        outcome = x.run_full_day_feed(
            deps,
            capture_interval=2,
            reference_wakeups=3,
            reference_last_timestamp_ns=300,
        )

        self.assertEqual(
            outcome.market_wakeups,
            3,
        )

        self.assertEqual(
            outcome.last_timestamp_ns,
            300,
        )

        self.assertEqual(
            outcome.terminal_classification,
            "PASS_NATURAL_END_OF_DATA",
        )

        self.assertEqual(
            outcome.position,
            0.0,
        )

        self.assertEqual(
            outcome.working_order_count,
            0,
        )

        self.assertTrue(
            outcome.source_unchanged
        )

        self.assertEqual(
            outcome.lifecycle[-2:],
            (
                "backtest_closed",
                "memmap_closed",
            ),
        )

        self.assertTrue(
            source._closed
        )

        self.assertTrue(
            heartbeats
        )

    def test_reference_mismatch_fails_closed_and_closes(self) -> None:
        source = FakeSource()

        deps = x.FullDayDependencies(
            capture_memory=(
                lambda: safe_snapshot()
            ),
            open_source=(
                lambda: source
            ),
            build_binding=(
                lambda observed_source:
                FakeBinding(
                    observed_source,
                    [100, 200, 300],
                )
            ),
            source_identity=(
                lambda: (
                    1,
                    2,
                    3,
                    4,
                )
            ),
            persist_heartbeat=(
                lambda payload: None
            ),
        )

        with self.assertRaisesRegex(
            x.D6R15ExecutionError,
            "reference_eod_wakeup_mismatch",
        ):
            x.run_full_day_feed(
                deps,
                capture_interval=2,
                reference_wakeups=4,
                reference_last_timestamp_ns=300,
            )

        self.assertTrue(
            source._closed
        )

    def test_swap_growth_fails_closed(self) -> None:
        source = FakeSource()

        snapshots = [
            safe_snapshot(swap=0),
            safe_snapshot(swap=0),
            safe_snapshot(swap=0),
            safe_snapshot(swap=4096),
        ]

        def capture_memory() -> memory.MemorySnapshot:
            if snapshots:
                return snapshots.pop(0)

            return safe_snapshot(
                swap=4096
            )

        deps = x.FullDayDependencies(
            capture_memory=(
                capture_memory
            ),
            open_source=(
                lambda: source
            ),
            build_binding=(
                lambda observed_source:
                FakeBinding(
                    observed_source,
                    [100],
                )
            ),
            source_identity=(
                lambda: (
                    1,
                    2,
                    3,
                    4,
                )
            ),
            persist_heartbeat=(
                lambda payload: None
            ),
        )

        with self.assertRaisesRegex(
            x.D6R15ExecutionError,
            "PROCESS_SWAP_GROWTH",
        ):
            x.run_full_day_feed(
                deps,
                capture_interval=1,
                reference_wakeups=1,
                reference_last_timestamp_ns=100,
            )

        self.assertTrue(
            source._closed
        )

    def test_closed_surfaces(self) -> None:
        flags = x.closed_surface_flags()

        self.assertTrue(
            flags["full_day_attempted"]
        )

        self.assertTrue(
            flags["full_day_validation"]
        )

        for key in (
            "mar_to_jul_opened",
            "historical_pnl",
            "policy_execution",
            "orders",
            "order_submission",
            "order_cancel",
            "converter_rerun",
            "raw_csv_opened",
            "canonical_npy_written",
            "aug_opened",
            "sep_plus_opened",
            "non_btc_opened",
            "network_acquisition",
            "railway_touched",
            "live_trading",
        ):
            self.assertFalse(
                flags[key],
                key,
            )


if __name__ == "__main__":
    unittest.main()

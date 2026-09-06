from __future__ import annotations

import json
import unittest

from multimarket import dev045_d6r11_memory_attribution as memory
from multimarket import dev045_d6r16_mar_jul_contract as c
from multimarket import dev045_d6r16_mar_jul_execution as x


def safe_snapshot(
    *,
    swap: int = 0,
    anon: int = 70_000_000,
    file_rss: int = 80_000_000,
    available: int = 12_000_000_000,
) -> memory.MemorySnapshot:
    return memory.MemorySnapshot(
        captured_at_utc="2026-09-06T00:00:00+00:00",
        pid=123,
        process=memory.ProcessMemory(
            vm_rss_bytes=anon + file_rss,
            rss_anon_bytes=anon,
            rss_file_bytes=file_rss,
            rss_shmem_bytes=0,
            vm_size_bytes=12_000_000_000,
            vm_data_bytes=anon,
            vm_swap_bytes=swap,
        ),
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
    def __init__(self, timestamps: list[int]) -> None:
        self.timestamps = list(timestamps)
        self.index = 0
        self.current_timestamp = 0

    def wait_next_feed(
        self,
        include_order_resp: bool,
        timeout_ns: int,
    ) -> int:
        del include_order_resp, timeout_ns

        if self.index >= len(self.timestamps):
            return 1

        self.current_timestamp = self.timestamps[self.index]
        self.index += 1
        return 2

    def position(self, asset_no: int) -> float:
        del asset_no
        return 0.0

    def orders(self, asset_no: int) -> dict[int, object]:
        del asset_no
        return {}

    def close(self) -> int:
        return 0


class FakeBinding:
    def __init__(
        self,
        source: FakeSource,
        timestamps: list[int],
    ) -> None:
        self.source = source
        self.bt = FakeBT(timestamps)
        self.lifecycle = [
            "memmap_opened_verified",
            "asset_registered",
            "backtest_built",
        ]
        self._closed = False


class TestD6R16(unittest.TestCase):
    def test_exact_sequence(self) -> None:
        self.assertEqual(
            c.SEQUENCE_DAYS,
            (
                "2026-03-01",
                "2026-04-01",
                "2026-05-01",
                "2026-06-01",
                "2026-07-01",
            ),
        )
        self.assertTrue(c.FEB01_RERUN_FORBIDDEN)
        self.assertTrue(c.D6R15_RERUN_FORBIDDEN)

    def test_no_guessed_terminal_reference(self) -> None:
        self.assertIsNone(c.FIXED_WAKEUP_STOP_TARGET)
        self.assertFalse(
            c.PREKNOWN_WAKEUP_REFERENCE_REQUIRED
        )
        self.assertFalse(
            c.PREKNOWN_LAST_TIMESTAMP_REQUIRED
        )
        self.assertTrue(
            c.NATURAL_END_OF_DATA_IS_VALID_TERMINAL
        )

    def test_memory_policy(self) -> None:
        self.assertIsNone(
            c.TOTAL_RSS_ABORT_THRESHOLD_BYTES
        )
        self.assertTrue(
            c.RUNTIME_ABORT_ON_PROCESS_SWAP_GROWTH
        )
        self.assertEqual(
            c.ANONYMOUS_GROWTH_ABORT_THRESHOLD_BYTES,
            536_870_912,
        )

    def test_authorization_surface(self) -> None:
        self.assertEqual(
            c.AUTHORIZED_EXECUTION_FLAGS,
            (True,) * len(c.AUTHORIZED_EXECUTION_FLAGS),
        )
        self.assertEqual(
            c.PROHIBITED_EXECUTION_FLAGS,
            (False,) * len(c.PROHIBITED_EXECUTION_FLAGS),
        )
        self.assertFalse(c.FEB01_OPEN_AUTHORIZED)
        self.assertFalse(c.HISTORICAL_PNL_AUTHORIZED)
        self.assertFalse(c.POLICY_EXECUTION_AUTHORIZED)
        self.assertFalse(c.ORDER_SUBMISSION_AUTHORIZED)

    def test_exact_token_required(self) -> None:
        with self.assertRaisesRegex(
            x.D6R16ExecutionError,
            "authorization_token",
        ):
            x.require_execution_authorization({})

        x.require_execution_authorization(
            {
                c.AUTHORIZATION_ENV:
                    c.AUTHORIZATION_TOKEN
            }
        )

    def test_child_module_resolution(self) -> None:
        command = x.child_command(
            "2026-03-01"
        )
        self.assertEqual(command[1], "-m")
        self.assertEqual(
            command[2],
            c.CHILD_MODULE_NAME,
        )
        self.assertNotIn("__main__", command)

        smoke = x.run_child_resolution_smoke()
        self.assertEqual(smoke["status"], "PASS")
        self.assertFalse(smoke["canonical_data_opened"])
        self.assertFalse(smoke["mar_to_jul_opened"])

    def test_frozen_lineage_witness_identity(
        self,
    ) -> None:
        for spec in c.DAY_SPECS:
            x.verify_lineage_witness(spec)

    def test_frozen_witness_blob_identities(
        self,
    ) -> None:
        self.assertEqual(
            x._git_blob_sha1(
                c.D6R9B_AUTHORIZATION_PATH
            ),
            c.D6R9B_AUTHORIZATION_GIT_BLOB_SHA1,
        )

        self.assertEqual(
            x._git_blob_sha1(
                c.D6R10_LINEAGE_WITNESS_PATH
            ),
            c.D6R10_LINEAGE_WITNESS_GIT_BLOB_SHA1,
        )

    def test_lineage_witness_amendment(self) -> None:
        payload = json.loads(
            c.LINEAGE_WITNESS_AMENDMENT_PATH.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            payload["verification_mode"],
            c.LINEAGE_WITNESS_MODE,
        )
        self.assertIs(
            payload["original_daily_json_recovered"],
            c.ORIGINAL_D6R9B_DAILY_EVIDENCE_RECOVERED,
        )
        self.assertIs(
            payload["original_daily_json_reconstructed"],
            c.ORIGINAL_D6R9B_DAILY_EVIDENCE_RECONSTRUCTED,
        )

        identities = payload["immutable_identities"]
        self.assertEqual(
            identities["d6r9b_authorization"]["git_blob_sha1"],
            c.D6R9B_AUTHORIZATION_GIT_BLOB_SHA1,
        )
        self.assertEqual(
            identities["d6r10_dayspec_witness"]["git_blob_sha1"],
            c.D6R10_LINEAGE_WITNESS_GIT_BLOB_SHA1,
        )

        amendment_by_day = {
            item["day"]: item
            for item in payload["day_specs"]
        }
        self.assertEqual(
            tuple(amendment_by_day),
            c.SEQUENCE_DAYS,
        )

        for spec in c.DAY_SPECS:
            item = amendment_by_day[spec.day]
            self.assertEqual(item["canonical_npy_path"], str(spec.path))
            self.assertEqual(item["canonical_npy_rows"], spec.rows)
            self.assertEqual(item["canonical_npy_bytes"], spec.bytes)
            self.assertEqual(item["canonical_npy_sha256"], spec.sha256)
            self.assertEqual(
                item["expected_original_daily_json_path"],
                str(spec.lineage_evidence),
            )
            self.assertEqual(
                item["expected_original_daily_json_sha256"],
                spec.lineage_evidence_sha256,
            )

    def test_sequence_plan_all_fresh(self) -> None:
        self.assertEqual(
            x.sequence_plan(
                ("FRESH",) * 5
            ),
            ("RUN_FRESH",) * 5,
        )

    def test_sequence_plan_prefix_pass_resume(self) -> None:
        self.assertEqual(
            x.sequence_plan(
                (
                    "FROZEN_PASS",
                    "FROZEN_PASS",
                    "FRESH",
                    "FRESH",
                    "FRESH",
                )
            ),
            (
                "SKIP_FROZEN_PASS",
                "SKIP_FROZEN_PASS",
                "RUN_FRESH",
                "RUN_FRESH",
                "RUN_FRESH",
            ),
        )

        with self.assertRaisesRegex(
            x.D6R16ExecutionError,
            "sequence_contains_consumed_nonpass",
        ):
            x.sequence_plan(
                (
                    "FRESH",
                    "CONSUMED_NONPASS",
                    "FRESH",
                    "FRESH",
                    "FRESH",
                )
            )

    def test_synthetic_full_day_natural_eod(self) -> None:
        spec = c.DAY_SPECS[0]
        source = FakeSource()
        heartbeats: list[dict[str, object]] = []

        identity = (1, 2, 3, 4)

        deps = x.FullDayDependencies(
            capture_memory=lambda: safe_snapshot(),
            open_source=lambda: source,
            build_binding=lambda observed_source: FakeBinding(
                observed_source,
                [100, 200, 300],
            ),
            source_identity=lambda: identity,
            persist_heartbeat=heartbeats.append,
        )

        outcome = x.run_full_day_feed(
            spec,
            deps,
            capture_interval=2,
        )

        self.assertEqual(
            outcome.market_wakeups,
            3,
        )
        self.assertEqual(
            outcome.first_timestamp_ns,
            100,
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
            outcome.lifecycle[-2:],
            (
                "backtest_closed",
                "memmap_closed",
            ),
        )
        self.assertTrue(source._closed)
        self.assertTrue(heartbeats)

    def test_swap_growth_fails_closed(self) -> None:
        spec = c.DAY_SPECS[0]
        source = FakeSource()

        snapshots = [
            safe_snapshot(swap=0),
            safe_snapshot(swap=0),
            safe_snapshot(swap=0),
            safe_snapshot(swap=4096),
        ]

        def capture() -> memory.MemorySnapshot:
            if snapshots:
                return snapshots.pop(0)
            return safe_snapshot(swap=4096)

        deps = x.FullDayDependencies(
            capture_memory=capture,
            open_source=lambda: source,
            build_binding=lambda observed_source: FakeBinding(
                observed_source,
                [100],
            ),
            source_identity=lambda: (1, 2, 3, 4),
            persist_heartbeat=lambda payload: None,
        )

        with self.assertRaisesRegex(
            x.D6R16ExecutionError,
            "PROCESS_SWAP_GROWTH",
        ):
            x.run_full_day_feed(
                spec,
                deps,
                capture_interval=1,
            )

        self.assertTrue(source._closed)

    def test_stop_on_first_fail(self) -> None:
        calls: list[str] = []
        persisted: list[dict[str, object]] = []

        def runner(spec: c.DaySpec) -> bool:
            calls.append(spec.day)
            return len(calls) < 2

        ok = x.execute_sequence(
            state_getter=lambda spec: "FRESH",
            day_runner=runner,
            persist_summary=persisted.append,
        )

        self.assertFalse(ok)
        self.assertEqual(
            calls,
            [
                "2026-03-01",
                "2026-04-01",
            ],
        )
        self.assertEqual(
            persisted[-1]["status"],
            "FAIL_STOPPED",
        )

    def test_closed_surfaces(self) -> None:
        flags = x.closed_surface_flags()

        for key, value in flags.items():
            self.assertFalse(value, key)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from multimarket import dev045_d6r14_memory_policy as p


class TestD6R14MemoryPolicy(unittest.TestCase):
    def test_parent_and_consumed_lineage_are_frozen(self) -> None:
        self.assertEqual(
            p.PARENT_D6R13_FREEZE_HEAD,
            "7f528866769e1aab6d55ed8c2aec794cacb2418e",
        )
        self.assertEqual(
            p.PARENT_D6R13_FREEZE_MANIFEST_SHA256,
            "f66f728026b9541d81d756d186efe1704812148595eb68d404adc6cb9922ff97",
        )
        self.assertTrue(p.D6R12_RERUN_FORBIDDEN)
        self.assertTrue(p.D6R13_RERUN_FORBIDDEN)
        self.assertTrue(p.D6R13_ATTEMPT_CONSUMED)
        self.assertTrue(p.D6R13_DIAGNOSTIC_QUESTION_ANSWERED)
        self.assertFalse(p.ADDITIONAL_BOUNDED_MEMORY_DIAGNOSTIC_REQUIRED)

    def test_d6r13_eod_identity(self) -> None:
        self.assertEqual(p.D6R13_DESIGNED_TARGET_WAKEUPS, 7_500_000)
        self.assertEqual(p.D6R13_OBSERVED_END_OF_DATA_WAKEUPS, 7_139_910)
        self.assertEqual(p.D6R13_TARGET_SHORTFALL_WAKEUPS, 360_090)

    def test_d6r13_crossed_old_total_rss_guard_with_file_backing(self) -> None:
        self.assertGreater(
            p.D6R13_6750000_VM_RSS_BYTES,
            p.OLD_D6R10_TOTAL_RSS_ABORT_BYTES,
        )
        self.assertGreater(p.D6R13_6750000_FILE_BACKED_FRACTION, 0.99)
        self.assertEqual(p.D6R13_6750000_VM_SWAP_BYTES, 0)
        self.assertLess(p.D6R13_6750000_RSS_ANON_BYTES, 100_000_000)

    def test_total_rss_is_not_a_runtime_abort_metric(self) -> None:
        self.assertIsNone(p.TOTAL_RSS_ABORT_THRESHOLD_BYTES)
        reason = p.memory_abort_reason(
            baseline_swap_bytes=0,
            current_swap_bytes=0,
            baseline_rss_anon_bytes=p.D6R13_AFTER_BINDING_RSS_ANON_BYTES,
            current_rss_anon_bytes=p.D6R13_TERMINAL_RSS_ANON_BYTES,
            current_memavailable_bytes=p.D6R13_TERMINAL_MEMAVAILABLE_BYTES,
        )
        self.assertIsNone(reason)

    def test_swap_growth_is_hard_abort(self) -> None:
        self.assertEqual(
            p.memory_abort_reason(
                baseline_swap_bytes=0,
                current_swap_bytes=4096,
                baseline_rss_anon_bytes=70_000_000,
                current_rss_anon_bytes=70_000_000,
                current_memavailable_bytes=12_000_000_000,
            ),
            "PROCESS_SWAP_GROWTH",
        )

    def test_anonymous_growth_is_hard_abort(self) -> None:
        baseline = 70_000_000
        self.assertEqual(
            p.memory_abort_reason(
                baseline_swap_bytes=0,
                current_swap_bytes=0,
                baseline_rss_anon_bytes=baseline,
                current_rss_anon_bytes=(
                    baseline
                    + p.ANONYMOUS_GROWTH_ABORT_THRESHOLD_BYTES
                    + 1
                ),
                current_memavailable_bytes=12_000_000_000,
            ),
            "ANONYMOUS_RSS_GROWTH",
        )

    def test_system_memory_floor_is_hard_abort(self) -> None:
        self.assertEqual(
            p.memory_abort_reason(
                baseline_swap_bytes=0,
                current_swap_bytes=0,
                baseline_rss_anon_bytes=70_000_000,
                current_rss_anon_bytes=70_000_000,
                current_memavailable_bytes=(
                    p.RUNTIME_MEMAVAILABLE_ABORT_THRESHOLD_BYTES - 1
                ),
            ),
            "SYSTEM_MEMAVAILABLE_BELOW_FLOOR",
        )

    def test_natural_eod_is_success_not_fixed_target_failure(self) -> None:
        result = p.classify_feed_terminal(
            end_of_data=True,
            market_wakeups=7_139_910,
            hard_safety_abort_reason=None,
            position=0.0,
            working_order_count=0,
            source_unchanged=True,
            lifecycle=(
                "memmap_opened_verified",
                "asset_registered",
                "backtest_built",
                "backtest_closed",
                "memmap_closed",
            ),
        )
        self.assertEqual(result, "PASS_NATURAL_END_OF_DATA")
        self.assertTrue(p.NATURAL_END_OF_DATA_IS_VALID_TERMINAL)
        self.assertFalse(p.FIXED_WAKEUP_TARGET_REQUIRED)

    def test_empty_eod_is_not_success(self) -> None:
        self.assertEqual(
            p.classify_feed_terminal(
                end_of_data=True,
                market_wakeups=0,
                hard_safety_abort_reason=None,
                position=0.0,
                working_order_count=0,
                source_unchanged=True,
                lifecycle=("backtest_closed", "memmap_closed"),
            ),
            "FAIL_EMPTY_FEED",
        )

    def test_close_order_is_required(self) -> None:
        self.assertEqual(
            p.classify_feed_terminal(
                end_of_data=True,
                market_wakeups=1,
                hard_safety_abort_reason=None,
                position=0.0,
                working_order_count=0,
                source_unchanged=True,
                lifecycle=("memmap_closed", "backtest_closed"),
            ),
            "FAIL_CLOSE_ORDER",
        )

    def test_design_cannot_execute(self) -> None:
        self.assertEqual(p.STAGE_MODE, "DESIGN_ONLY_NOT_EXECUTED")
        self.assertFalse(any(p.EXECUTION_AUTHORIZATION_FLAGS))


if __name__ == "__main__":
    unittest.main()

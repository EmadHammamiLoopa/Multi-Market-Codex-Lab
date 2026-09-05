from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from multimarket import dev045_d6r6_historical_binding_contract as d6r6
from multimarket import dev045_d6r12_memory_attributed_real_diagnostic_contract as c


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class TestD6R12MemoryAttributedRealDiagnosticContract(unittest.TestCase):
    def test_identity_and_frozen_lineage_are_exact(self):
        self.assertEqual(c.EXPERIMENT_ID, "DEV045-D6R12")
        self.assertEqual(
            c.CONTRACT_ID,
            "DEV045-D6R12-MEMORY-ATTRIBUTED-REAL-DIAGNOSTIC-DESIGN-V1",
        )
        self.assertEqual(c.D6R10_EXECUTION_CODE_HEAD, "0f2129e1cc0f8b75377fb0fb01b01857b24ab18c")
        self.assertEqual(c.D6R10_FROZEN_FAILURE_HEAD, "50663457ca3e12506160025ccd045bf9abeec197")
        self.assertEqual(c.D6R11_IMPLEMENTATION_PASS_HEAD, "22f20b506c9d1a52fae523a758e29588df33161b")
        self.assertEqual(c.D6R11_FROZEN_PASS_HEAD, "9b342a6e08fe51771a7125e823d76c927b1c3d7d")
        self.assertEqual(c.STAGE_MODE, "DESIGN_CONTRACT_SYNTHETIC_TESTS_ONLY")

    def test_frozen_evidence_hashes_are_exact(self):
        self.assertEqual(
            _sha256(ROOT / c.D6R11_FREEZE_MANIFEST_PATH),
            c.D6R11_FREEZE_MANIFEST_SHA256,
        )
        self.assertEqual(
            _sha256(ROOT / c.D6R10_EVIDENCE_PATH),
            c.D6R10_EVIDENCE_SHA256,
        )
        freeze = json.loads((ROOT / c.D6R11_FREEZE_MANIFEST_PATH).read_text())
        self.assertEqual(freeze["status"], "FROZEN_PASS")
        self.assertEqual(freeze["design_head"], c.D6R11_IMPLEMENTATION_PASS_HEAD)
        self.assertEqual(
            c.D6R10_ATTEMPT_MARKER_SHA256,
            "9346106a92cb35f8681bfef7ba06b46ad719c9e55a93e833bd96ab68992b3ebb",
        )
        self.assertEqual(
            c.D6R10_HEARTBEAT_SHA256,
            "62ff826a0bc480cc321ce47b4dde57d9c8227968ede039c103aac94d8140cec3",
        )

    def test_feb_identity_is_frozen_as_metadata_only(self):
        self.assertEqual(c.DAY, "2026-02-01")
        self.assertEqual(c.SYMBOL, "BTCUSDT")
        self.assertEqual(c.EXCHANGE, "binance-futures")
        self.assertEqual(c.SOURCE_ROWS, 179_584_138)
        self.assertEqual(c.SOURCE_BYTES, 11_493_385_088)
        self.assertEqual(c.SOURCE_SHA256, "d757d2ac32a29b0ac587323e115779c466068c6c0eba4270226b9c4109254cbc")

    def test_bounded_target_and_old_failure_region_are_exact(self):
        self.assertEqual(c.OLD_D6R10_ABORT_BYTES, 10_808_320_000)
        self.assertEqual(c.OLD_D6R10_LAST_HEARTBEAT_WAKEUPS, 6_500_000)
        self.assertEqual(c.OLD_D6R10_LAST_HEARTBEAT_RSS_BYTES, 10_693_107_712)
        self.assertEqual(c.BOUNDED_WAKEUP_TARGET, 7_500_000)
        self.assertEqual(c.WAKEUP_CAPTURE_INTERVAL, 250_000)
        self.assertGreater(c.BOUNDED_WAKEUP_TARGET, c.OLD_D6R10_LAST_HEARTBEAT_WAKEUPS)
        self.assertEqual(c.BOUNDED_TARGET_TERMINAL_REASON, "BOUNDED_WAKEUP_TARGET_REACHED")
        self.assertIn(c.BOUNDED_WAKEUP_TARGET, c.SPECIFIC_WAKEUP_CAPTURES)

    def test_safety_fields_are_attributed_without_replacement_rss_limit(self):
        self.assertEqual(c.PREEXEC_MIN_MEMAVAILABLE_BYTES, 8_442_945_536)
        self.assertIsNone(c.RUNTIME_MEMAVAILABLE_ABORT_THRESHOLD_BYTES)
        self.assertIs(c.RUNTIME_ABORT_ON_PROCESS_SWAP_GROWTH, True)
        self.assertEqual(c.PROCESS_SWAP_GROWTH_BASELINE, "before_source_open_VmSwap")
        self.assertIsNone(c.TOTAL_RSS_ABORT_THRESHOLD_BYTES)
        self.assertIsNone(c.ANONYMOUS_RSS_ABORT_THRESHOLD_BYTES)
        self.assertIs(c.ANONYMOUS_GROWTH_PREFLIGHT_REQUIRED, True)
        self.assertEqual(
            c.MEMORY_DERIVED_FIELDS,
            ("resident_components_bytes", "rss_decomposition_delta_bytes"),
        )

    def test_future_namespace_is_distinct_and_attempt_is_one_shot(self):
        self.assertNotEqual(c.FUTURE_RUNTIME_ROOT, c.D6R10_RUNTIME_ROOT)
        self.assertIn("dev045_d6r12", str(c.FUTURE_RUNTIME_ROOT))
        self.assertEqual(c.FUTURE_ATTEMPT_MARKER_NAME, "ATTEMPT_STARTED.json")
        self.assertEqual(c.FUTURE_ATTEMPT_POLICY, "ONE_SHOT_CONSUMED_NEVER_RERUN")

    def test_close_order_remains_frozen(self):
        self.assertIs(c.MEMMAP_OWNER_MUST_OUTLIVE_BACKTEST, True)
        self.assertIs(c.BACKTEST_MUST_CLOSE_BEFORE_MEMMAP_CLOSE, True)
        self.assertEqual(c.REQUIRED_CLOSE_ORDER, ("backtest_closed", "memmap_closed"))
        self.assertEqual(
            d6r6.REQUIRED_LIFETIME_ORDER[-2:],
            ("close_backtest", "close_memmap"),
        )

    def test_future_evidence_schema_contains_required_fields(self):
        required = {
            "bounded_wakeup_target",
            "bounded_wakeup_reached",
            "memory_snapshots",
            "peak_vm_rss_bytes",
            "peak_rss_anon_bytes",
            "peak_rss_file_bytes",
            "peak_rss_shmem_bytes",
            "minimum_memavailable_bytes",
            "peak_vm_swap_bytes",
            "crossed_old_failure_region",
            "full_day_attempted",
            "live_trading_authorized",
        }
        self.assertTrue(required.issubset(c.FUTURE_EVIDENCE_REQUIRED_FIELDS))

    def test_all_execution_and_market_access_surfaces_are_closed(self):
        self.assertEqual(c.PROHIBITED_EXECUTION_FLAGS, (False,) * len(c.PROHIBITED_EXECUTION_FLAGS))
        self.assertEqual(c.NEXT_STAGE, "DEV045-D6R12_REAL_DIAGNOSTIC_EXECUTION_PREFLIGHT")


if __name__ == "__main__":
    unittest.main()

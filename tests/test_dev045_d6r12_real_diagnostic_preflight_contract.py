from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from multimarket import dev045_d6r12_memory_attributed_real_diagnostic_contract as design
from multimarket import dev045_d6r12_real_diagnostic_preflight_contract as c


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class TestD6R12RealDiagnosticPreflightContract(unittest.TestCase):
    def test_identity_and_parent_are_exact(self):
        self.assertEqual(c.EXPERIMENT_ID, "DEV045-D6R12")
        self.assertEqual(
            c.PREFLIGHT_ID,
            "DEV045-D6R12-REAL-DIAGNOSTIC-EXECUTION-PREFLIGHT-V1",
        )
        self.assertEqual(c.PARENT_HEAD, "544dba4a2428e957049a46edb15d3558826f4ab7")
        self.assertEqual(c.DESIGN_HEAD, "2aa65ad0cbfe3fdceaa4b76550ec14a35f25fe97")
        self.assertEqual(c.STAGE_MODE, "PREFLIGHT_AND_SYNTHETIC_EXECUTION_WRAPPER_ONLY")

    def test_frozen_repository_artifact_hashes_are_exact(self):
        pairs = (
            (c.DESIGN_FREEZE_MANIFEST_PATH, c.DESIGN_FREEZE_MANIFEST_SHA256),
            (c.D6R11_FREEZE_MANIFEST_PATH, c.D6R11_FREEZE_MANIFEST_SHA256),
            (c.D6R10_EVIDENCE_PATH, c.D6R10_EVIDENCE_SHA256),
        )
        for relative, expected in pairs:
            self.assertEqual(_sha256(ROOT / relative), expected)
        self.assertEqual(
            c.D6R10_ATTEMPT_MARKER_SHA256,
            "9346106a92cb35f8681bfef7ba06b46ad719c9e55a93e833bd96ab68992b3ebb",
        )
        self.assertEqual(
            c.D6R10_HEARTBEAT_SHA256,
            "62ff826a0bc480cc321ce47b4dde57d9c8227968ede039c103aac94d8140cec3",
        )

    def test_source_and_lineage_metadata_are_exact(self):
        self.assertEqual(c.DAY, "2026-02-01")
        self.assertEqual(c.SOURCE_ROWS, 179_584_138)
        self.assertEqual(c.SOURCE_BYTES, 11_493_385_088)
        self.assertEqual(c.SOURCE_SHA256, "d757d2ac32a29b0ac587323e115779c466068c6c0eba4270226b9c4109254cbc")
        self.assertEqual(
            c.SOURCE_LINEAGE_EVIDENCE_SHA256,
            "54afd16ca610b76de0658d68764b661335fcda23e3ae3ca4ce4de93c57c199d9",
        )
        self.assertEqual(c.SOURCE_PREFLIGHT_ACCESS, "STAT_ONLY")
        self.assertIs(c.SOURCE_CONTENT_HASH_DEFERRED_TO_AUTHORIZED_VERIFIED_MEMMAP_OPEN, True)

    def test_frozen_memory_and_bounded_semantics_are_unchanged(self):
        self.assertEqual(c.HFTBACKTEST_VERSION, "2.4.4")
        self.assertEqual(c.BOUNDED_WAKEUP_TARGET, 7_500_000)
        self.assertEqual(c.WAKEUP_CAPTURE_INTERVAL, 250_000)
        self.assertEqual(c.PREEXEC_MIN_MEMAVAILABLE_BYTES, 8_442_945_536)
        self.assertIsNone(c.RUNTIME_MEMAVAILABLE_ABORT_THRESHOLD_BYTES)
        self.assertIsNone(c.TOTAL_RSS_ABORT_THRESHOLD_BYTES)
        self.assertIsNone(c.ANONYMOUS_RSS_ABORT_THRESHOLD_BYTES)
        self.assertIs(c.RUNTIME_ABORT_ON_PROCESS_SWAP_GROWTH, True)

    def test_authorization_token_and_enabled_bit_are_exact(self):
        self.assertEqual(c.AUTHORIZATION_ENV, "DEV045_D6R12_AUTHORIZE")
        self.assertEqual(c.AUTHORIZATION_TOKEN, "YES_FEB01_BOUNDED_MEMORY_DIAGNOSTIC")
        self.assertIs(c.REAL_EXECUTION_ENABLED, True)

    def test_runtime_and_evidence_namespaces_are_fresh_and_distinct(self):
        self.assertNotEqual(c.RUNTIME_ROOT.parent, c.D6R10_RUNTIME_ROOT)
        self.assertEqual(c.ATTEMPT_MARKER_PATH.name, "ATTEMPT_STARTED.json")
        self.assertEqual(c.MEMORY_HEARTBEAT_PATH.name, "MEMORY_HEARTBEAT.json")
        self.assertEqual(c.EVIDENCE_PATH, Path("evidence/dev045_d6r12_2026-02-01.json"))

    def test_frozen_close_order_and_closed_surfaces_remain_exact(self):
        self.assertIs(design.BACKTEST_MUST_CLOSE_BEFORE_MEMMAP_CLOSE, True)
        self.assertEqual(design.REQUIRED_CLOSE_ORDER, ("backtest_closed", "memmap_closed"))
        self.assertEqual(c.PROHIBITED_EXECUTION_FLAGS, (False,) * len(c.PROHIBITED_EXECUTION_FLAGS))
        self.assertEqual(design.PROHIBITED_EXECUTION_FLAGS, (False,) * len(design.PROHIBITED_EXECUTION_FLAGS))


if __name__ == "__main__":
    unittest.main()

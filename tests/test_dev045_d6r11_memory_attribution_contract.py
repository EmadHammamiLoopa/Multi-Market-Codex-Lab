from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from multimarket import dev045_d6r11_memory_attribution_contract as c


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class TestD6R11MemoryAttributionContract(unittest.TestCase):
    def test_successor_identity_and_frozen_parent_are_exact(self):
        self.assertEqual(c.EXPERIMENT_ID, "DEV045-D6R11")
        self.assertEqual(
            c.CONTRACT_ID,
            "DEV045-D6R11-MEMORY-ATTRIBUTION-SUCCESSOR-V1",
        )
        self.assertEqual(c.SCHEMA_VERSION, "dev045-d6r11-memory-attribution-v1")
        self.assertEqual(c.MODE, "NON_CANONICAL_SYNTHETIC_MEMORY_ATTRIBUTION_ONLY")
        self.assertEqual(c.PARENT_HEAD, "50663457ca3e12506160025ccd045bf9abeec197")
        self.assertEqual(
            c.D6R10_EXECUTION_CODE_HEAD,
            "0f2129e1cc0f8b75377fb0fb01b01857b24ab18c",
        )

    def test_frozen_d6r10_evidence_is_byte_identical_and_failed(self):
        path = ROOT / c.D6R10_EVIDENCE_PATH
        self.assertEqual(_sha256(path), c.D6R10_EVIDENCE_SHA256)
        evidence = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(evidence["experiment_id"], "DEV045-D6R10")
        self.assertEqual(evidence["status"], "FAIL")
        self.assertEqual(evidence["source_bytes"], 11_493_385_088)
        self.assertEqual(
            evidence["child_stderr_tail"].splitlines()[-1],
            "D6R10Error: rss_abort:2026-02-01:10808320000",
        )
        self.assertEqual(
            c.D6R10_ATTEMPT_MARKER_SHA256,
            "9346106a92cb35f8681bfef7ba06b46ad719c9e55a93e833bd96ab68992b3ebb",
        )
        self.assertEqual(
            c.D6R10_HEARTBEAT_SHA256,
            "62ff826a0bc480cc321ce47b4dde57d9c8227968ede039c103aac94d8140cec3",
        )
        self.assertEqual(c.D6R10_STATUS, "FROZEN_FAIL")
        self.assertIs(c.D6R10_RERUN_AUTHORIZED, False)

    def test_units_fields_and_attribution_sources_are_frozen(self):
        self.assertEqual(c.KIB_TO_BYTES, 1024)
        self.assertEqual(
            c.REQUIRED_STATUS_FIELDS,
            ("VmRSS", "RssAnon", "RssFile", "RssShmem"),
        )
        self.assertEqual(c.OPTIONAL_STATUS_FIELDS, ("VmSize", "VmData", "VmSwap"))
        self.assertEqual(c.REQUIRED_MEMINFO_FIELDS, ("MemAvailable",))
        self.assertEqual(c.REQUIRED_SMAPS_ROLLUP_FIELDS, ("Rss", "Pss"))
        self.assertEqual(
            c.RSS_DECOMPOSITION,
            "VmRSS - (RssAnon + RssFile + RssShmem)",
        )
        self.assertEqual(c.FILE_BACKED_RESIDENT_SOURCE, "RssFile")
        self.assertEqual(c.ANONYMOUS_RESIDENT_SOURCE, "RssAnon")
        self.assertEqual(c.TOTAL_RSS_SOURCE, "VmRSS")
        self.assertEqual(c.SYSTEM_AVAILABLE_SOURCE, "MemAvailable")
        self.assertIsNone(c.CANONICAL_ABORT_THRESHOLD_BYTES)

    def test_execution_surfaces_stay_closed_and_lifecycle_is_preserved(self):
        self.assertEqual(c.PROHIBITED_EXECUTION_FLAGS, (False,) * len(c.PROHIBITED_EXECUTION_FLAGS))
        self.assertEqual(c.FUTURE_MODE, "FEED_ONLY_NO_STRATEGY")
        self.assertIs(c.MEMMAP_OWNER_MUST_OUTLIVE_BACKTEST, True)
        self.assertIs(c.BACKTEST_MUST_CLOSE_BEFORE_MEMMAP_CLOSE, True)


if __name__ == "__main__":
    unittest.main()

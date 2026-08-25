from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from multimarket.codex_research import (
    SANDBOX_DAYS,
    ResearchSealError,
    assert_unsealed_day,
    assert_unsealed_path,
    canonical_sha256,
    sha256_file,
)


class CodexResearchContractTests(unittest.TestCase):
    def test_frozen_sandbox_days_are_allowed(self) -> None:
        for day in SANDBOX_DAYS:
            assert_unsealed_day(day, allowed=SANDBOX_DAYS)

    def test_every_sealed_boundary_is_rejected(self) -> None:
        sealed = [date(2026, 8, 1), *(date(2026, 8, day) for day in range(4, 24))]
        for day in sealed:
            with self.subTest(day=day), self.assertRaises(ResearchSealError):
                assert_unsealed_day(day)

    def test_neighboring_unsealed_days_are_not_globally_rejected(self) -> None:
        for day in (date(2026, 7, 31), date(2026, 8, 2), date(2026, 8, 3), date(2026, 8, 24)):
            assert_unsealed_day(day)

    def test_day_outside_frozen_experiment_set_is_rejected(self) -> None:
        with self.assertRaises(ResearchSealError):
            assert_unsealed_day(date(2025, 12, 1), allowed=SANDBOX_DAYS)

    def test_path_naming_a_sealed_day_is_rejected_before_open(self) -> None:
        with self.assertRaises(ResearchSealError):
            assert_unsealed_path(Path("unopened") / "2026-08-04_FEATURES250.csv")

    def test_invalid_date_like_text_does_not_raise(self) -> None:
        assert_unsealed_path("reports/2026-99-99-note.json")

    def test_canonical_hash_does_not_depend_on_mapping_order(self) -> None:
        self.assertEqual(canonical_sha256({"a": 1, "b": [2, 3]}), canonical_sha256({"b": [2, 3], "a": 1}))

    def test_file_hash_rejects_sealed_name(self) -> None:
        with self.assertRaises(ResearchSealError):
            sha256_file("2026-08-01.csv")

    def test_file_hash_is_content_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "allowed.bin"
            target.write_bytes(b"codex-research")
            self.assertEqual(
                sha256_file(target),
                "c96701d5a5f7440ea731bf30468446df441516aec99e843c0c4a9e4c49b5a60d",
            )


if __name__ == "__main__":
    unittest.main()

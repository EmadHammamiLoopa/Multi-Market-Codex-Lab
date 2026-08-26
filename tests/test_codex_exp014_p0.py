import copy
import json
import unittest
from pathlib import Path

from scripts.codex_exp014_p0_exp013_artifact_adjudication import (
    EXPECTED_DATES,
    FAIL_STATUS,
    INVALID_STATUS,
    PARENT_PATH,
    PARENT_SHA256,
    PASS_STATUS,
    POSITIVE_INVARIANTS,
    SCIENTIFIC_GUARDS,
    adjudicate,
    sha256_file,
)


class Exp014P0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent_path = Path(PARENT_PATH)
        cls.parent = json.loads(cls.parent_path.read_text(encoding="utf-8"))

    def test_frozen_parent_hash_exact(self):
        self.assertEqual(sha256_file(self.parent_path), PARENT_SHA256)

    def test_frozen_dates_exact(self):
        self.assertEqual(
            tuple(d["date"] for d in self.parent["days"]),
            EXPECTED_DATES,
        )

    def test_actual_frozen_exp013_artifact_adjudicates_pass(self):
        result = adjudicate(copy.deepcopy(self.parent), PARENT_SHA256)
        self.assertEqual(result["status"], PASS_STATUS)
        self.assertEqual(result["source_status_preserved"], "INVALID")
        self.assertTrue(result["recorded_integrity_pass"])
        self.assertTrue(result["recorded_readiness_pass"])

    def test_tampered_hash_is_invalid(self):
        result = adjudicate(copy.deepcopy(self.parent), "0" * 64)
        self.assertEqual(result["status"], INVALID_STATUS)
        self.assertFalse(result["verification_checks"]["parent_sha256_exact"])

    def test_parent_status_must_remain_invalid(self):
        parent = copy.deepcopy(self.parent)
        parent["status"] = PASS_STATUS
        result = adjudicate(parent, PARENT_SHA256)
        self.assertEqual(result["status"], INVALID_STATUS)

    def test_every_positive_invariant_requires_true(self):
        for key in POSITIVE_INVARIANTS:
            with self.subTest(key=key):
                parent = copy.deepcopy(self.parent)
                parent["invariants"][key] = False
                result = adjudicate(parent, PARENT_SHA256)
                self.assertEqual(result["status"], INVALID_STATUS)

    def test_every_invariant_guard_requires_false(self):
        for key in SCIENTIFIC_GUARDS:
            with self.subTest(key=key):
                parent = copy.deepcopy(self.parent)
                parent["invariants"][key] = True
                result = adjudicate(parent, PARENT_SHA256)
                self.assertEqual(result["status"], INVALID_STATUS)

    def test_every_top_level_guard_requires_false(self):
        for key in SCIENTIFIC_GUARDS:
            with self.subTest(key=key):
                parent = copy.deepcopy(self.parent)
                parent[key] = True
                result = adjudicate(parent, PARENT_SHA256)
                self.assertEqual(result["status"], INVALID_STATUS)

    def test_integrity_false_is_invalid(self):
        parent = copy.deepcopy(self.parent)
        parent["all_five_days_integrity_pass"] = False
        parent["all_five_days_pass"] = False
        parent["days"][0]["integrity_pass"] = False
        parent["days"][0]["pass"] = False
        parent["days"][0]["integrity_checks"]["raw_hash_verified"] = False
        result = adjudicate(parent, PARENT_SHA256)
        self.assertEqual(result["status"], INVALID_STATUS)

    def test_readiness_false_maps_to_frozen_fail(self):
        parent = copy.deepcopy(self.parent)
        parent["all_five_days_readiness_pass"] = False
        parent["all_five_days_pass"] = False
        parent["days"][0]["readiness_pass"] = False
        parent["days"][0]["pass"] = False
        parent["days"][0]["readiness_checks"]["run_120min"] = False
        result = adjudicate(parent, PARENT_SHA256)
        self.assertEqual(result["status"], FAIL_STATUS)

    def test_unexpected_date_is_invalid(self):
        parent = copy.deepcopy(self.parent)
        parent["days"][0]["date"] = "2026-08-01"
        result = adjudicate(parent, PARENT_SHA256)
        self.assertEqual(result["status"], INVALID_STATUS)

    def test_output_guards_and_no_recompute_flags_are_false(self):
        result = adjudicate(copy.deepcopy(self.parent), PARENT_SHA256)
        for key in SCIENTIFIC_GUARDS:
            self.assertIs(result[key], False)
        self.assertIs(result["raw_market_data_read"], False)
        self.assertIs(result["phase_l_read"], False)
        self.assertIs(result["market_metrics_recomputed"], False)


if __name__ == "__main__":
    unittest.main()

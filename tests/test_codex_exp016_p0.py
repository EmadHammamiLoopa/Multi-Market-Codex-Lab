import tempfile
import unittest
from pathlib import Path

from scripts.codex_exp016_p0_sealed_august_manifest import (
    DATES,
    EXPERIMENT_ID,
    PASS_STATUS,
    SYMBOL,
    capture_manifest,
    expected_paths,
)


class Exp016P0Tests(unittest.TestCase):
    def test_identity_and_exact_dates(self):
        self.assertEqual(EXPERIMENT_ID, "CODEX-EXP-016-P0")
        self.assertEqual(SYMBOL, "BTCUSDT")
        self.assertEqual(len(DATES), 21)
        self.assertEqual(len(set(DATES)), 21)
        self.assertEqual(DATES[0], "2026-08-01")
        self.assertEqual(DATES[1], "2026-08-04")
        self.assertEqual(DATES[-1], "2026-08-23")
        self.assertNotIn("2026-08-02", DATES)
        self.assertNotIn("2026-08-03", DATES)
        self.assertNotIn("2026-08-24", DATES)

    def test_expected_paths_are_btc_features250_only(self):
        root = Path("/tmp/features")
        pairs = expected_paths(root)
        self.assertEqual(len(pairs), 21)
        for d, p in pairs:
            self.assertEqual(
                p,
                root / "BTCUSDT" / f"{d}_FEATURES250.csv",
            )

    def test_missing_file_set_is_invalid_without_hashing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = capture_manifest(root)
            self.assertEqual(result["status"], "INVALID")
            self.assertEqual(result["files"], [])
            self.assertFalse(
                result["checks"]["all_expected_files_exist_before_hashing"]
            )

    def test_complete_dummy_set_captures_hashes_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "BTCUSDT"
            folder.mkdir(parents=True)

            for i, d in enumerate(DATES):
                (folder / f"{d}_FEATURES250.csv").write_bytes(
                    f"opaque-bytes-{i}".encode("ascii")
                )

            result = capture_manifest(root)

            self.assertEqual(result["status"], PASS_STATUS)
            self.assertEqual(len(result["files"]), 21)
            self.assertEqual(
                tuple(x["date"] for x in result["files"]),
                DATES,
            )
            self.assertTrue(all(result["checks"].values()))
            self.assertEqual(len(result["manifest_sha256"]), 64)

            for item in result["files"]:
                self.assertEqual(len(item["sha256"]), 64)
                self.assertGreater(item["size_bytes"], 0)

            self.assertTrue(result["august_files_opened_for_provenance_only"])
            self.assertFalse(result["csv_parsed"])
            self.assertFalse(result["row_count_inspected"])
            self.assertFalse(result["timestamp_inspected"])
            self.assertFalse(result["market_values_inspected"])
            self.assertFalse(result["features_scored"])
            self.assertFalse(result["target_scored"])
            self.assertFalse(result["model_fit"])
            self.assertFalse(result["auc_scored"])
            self.assertFalse(result["direction_scored"])
            self.assertFalse(result["pnl_scored"])
            self.assertFalse(result["network_accessed"])


if __name__ == "__main__":
    unittest.main()

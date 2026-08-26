import tempfile
import unittest
from pathlib import Path

from scripts.codex_exp016_p0_sealed_august_manifest import (
    DATA_TYPES,
    DAY,
    EXPERIMENT_ID,
    PASS_STATUS,
    SYMBOL,
    capture_manifest,
    expected_paths,
)


class Exp016P0Tests(unittest.TestCase):
    def test_identity_and_exact_scope(self):
        self.assertEqual(EXPERIMENT_ID, "CODEX-EXP-016-P0")
        self.assertEqual(SYMBOL, "BTCUSDT")
        self.assertEqual(DAY, "2026-08-01")
        self.assertEqual(
            DATA_TYPES,
            ("incremental_book_L2", "trades"),
        )

    def test_expected_paths_are_two_raw_aug1_files_only(self):
        root = Path("/tmp/raw")
        pairs = expected_paths(root)
        self.assertEqual(
            pairs,
            [
                (
                    "incremental_book_L2",
                    root
                    / "incremental_book_L2"
                    / "BTCUSDT"
                    / "2026-08-01.csv.gz",
                ),
                (
                    "trades",
                    root
                    / "trades"
                    / "BTCUSDT"
                    / "2026-08-01.csv.gz",
                ),
            ],
        )

    def test_missing_raw_set_is_invalid_without_hashing(self):
        with tempfile.TemporaryDirectory() as td:
            result = capture_manifest(Path(td))
            self.assertEqual(result["status"], "INVALID")
            self.assertEqual(result["files"], [])
            self.assertFalse(
                result["checks"][
                    "all_expected_files_exist_before_hashing"
                ]
            )
            self.assertFalse(
                result[
                    "august_raw_files_opened_for_provenance_only"
                ]
            )

    def test_complete_dummy_raw_set_hashes_bytes_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for i, data_type in enumerate(DATA_TYPES):
                folder = root / data_type / SYMBOL
                folder.mkdir(parents=True)
                (folder / f"{DAY}.csv.gz").write_bytes(
                    f"opaque-gzip-bytes-{i}".encode("ascii")
                )

            result = capture_manifest(root)

            self.assertEqual(result["status"], PASS_STATUS)
            self.assertEqual(len(result["files"]), 2)
            self.assertTrue(all(result["checks"].values()))
            self.assertEqual(len(result["manifest_sha256"]), 64)

            self.assertEqual(
                tuple(x["data_type"] for x in result["files"]),
                DATA_TYPES,
            )

            for item in result["files"]:
                self.assertEqual(item["day"], DAY)
                self.assertEqual(item["symbol"], SYMBOL)
                self.assertEqual(len(item["sha256"]), 64)
                self.assertGreater(item["size_bytes"], 0)

            self.assertTrue(
                result[
                    "august_raw_files_opened_for_provenance_only"
                ]
            )
            for key in (
                "gzip_decompressed",
                "csv_parsed",
                "header_inspected",
                "row_count_inspected",
                "timestamp_inspected",
                "market_values_inspected",
                "features_generated",
                "features_scored",
                "target_scored",
                "model_fit",
                "auc_scored",
                "direction_scored",
                "pnl_scored",
                "network_accessed",
            ):
                self.assertIs(result[key], False)


if __name__ == "__main__":
    unittest.main()

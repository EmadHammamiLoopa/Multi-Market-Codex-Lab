import tempfile
import unittest
from pathlib import Path

from scripts.codex_exp017_p0_aug1_phase_l_generation import (
    DAY,
    EXPECTED_ROWS,
    FEATURE_HEADER,
    EXP016_ARTIFACT_SHA256,
    EXPERIMENT_ID,
    GRID_US,
    RAW_SHA256,
    SOURCE_BLOBS,
    SYMBOL,
    TOOL_ORDER,
    count_rows_and_grid,
    day_bounds_us,
    derived_paths,
    invalid_result_from_exception,
    parse_features_stderr,
    raw_paths,
)


class Exp017P0Tests(unittest.TestCase):
    def test_identity_scope_and_parent(self):
        self.assertEqual(EXPERIMENT_ID, "CODEX-EXP-017-P0")
        self.assertEqual(DAY, "2026-08-01")
        self.assertEqual(SYMBOL, "BTCUSDT")
        self.assertEqual(EXPECTED_ROWS, 345_600)
        self.assertEqual(GRID_US, 250_000)
        self.assertEqual(
            EXP016_ARTIFACT_SHA256,
            "0c95efcccc235ad4115200b0bc476c3881e8af05711e9716bb9c8d2c782f0782",
        )

    def test_exact_frozen_raw_hashes(self):
        self.assertEqual(
            RAW_SHA256,
            {
                "incremental_book_L2":
                    "bc7b4e6206bdbd893da75d035f63128b518ed34f3dd6490da71f96c72fe2a4cc",
                "trades":
                    "27622702d5e33e6d374ec3d6f9040e8d7550ca9229641bccb6289d64256e4afe",
            },
        )

    def test_exact_tool_order_and_source_blobs(self):
        self.assertEqual(
            TOOL_ORDER,
            (
                "depth250",
                "flow250",
                "trade250",
                "snapshot_scan",
                "features250",
            ),
        )
        self.assertEqual(len(SOURCE_BLOBS), 5)
        self.assertEqual(
            SOURCE_BLOBS["tools/v23_phase0dl_features250.cpp"],
            "f76d4c374b38bf3d9ab1322ced2cfae26fa72142",
        )

    def test_day_bounds_are_exact_utc_day(self):
        start, end = day_bounds_us()
        self.assertEqual(end - start, 86_400_000_000)
        self.assertEqual(end - GRID_US, start + 345_599 * GRID_US)

    def test_raw_paths_exact(self):
        root = Path("/tmp/raw")
        paths = raw_paths(root)
        self.assertEqual(
            paths["incremental_book_L2"],
            root / "incremental_book_L2" / "BTCUSDT" / "2026-08-01.csv.gz",
        )
        self.assertEqual(
            paths["trades"],
            root / "trades" / "BTCUSDT" / "2026-08-01.csv.gz",
        )

    def test_derived_paths_exact(self):
        root = Path("/tmp/derived")
        paths = derived_paths(root)
        self.assertEqual(
            paths["book250"],
            root / "BTCUSDT" / "2026-08-01_BOOK250.csv",
        )
        self.assertEqual(
            paths["flow250"],
            root / "BTCUSDT" / "2026-08-01_FLOW250.csv",
        )
        self.assertEqual(
            paths["trade250"],
            root / "BTCUSDT" / "2026-08-01_TRADE250.csv",
        )
        self.assertEqual(
            paths["snapshots"],
            root / "BTCUSDT" / "2026-08-01_SNAPSHOTS.csv",
        )
        self.assertEqual(
            paths["features250"],
            root / "BTCUSDT" / "2026-08-01_FEATURES250.csv",
        )

    def test_parse_features_stderr(self):
        s = (
            "rows=345600 book_valid=340000 l0_valid=339000 "
            "l1_valid=338000 l2_valid=338000 snapshot_groups=7 "
            "snapshot_masked_bins=7 unknown_trades=0 "
            "unknown_qty=0 violations=0"
        )
        d = parse_features_stderr(s)
        self.assertEqual(d["rows"], 345600)
        self.assertEqual(d["violations"], 0)
        self.assertEqual(d["unknown_trades"], 0)
        self.assertEqual(d["snapshot_groups"], 7)

    def test_count_rows_and_grid_dummy(self):
        start, _ = day_bounds_us()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "dummy.csv"
            p.write_text(
                "local_timestamp_us,x\n"
                f"{start},1\n"
                f"{start + GRID_US},2\n"
                f"{start + 2 * GRID_US},3\n",
                encoding="utf-8",
            )
            r = count_rows_and_grid(p)
            self.assertEqual(r["rows"], 3)
            self.assertEqual(r["first_timestamp_us"], start)
            self.assertEqual(r["last_timestamp_us"], start + 2 * GRID_US)
            self.assertTrue(r["grid_250ms_exact"])

    def test_exact_frozen_feature_header_is_full_schema(self):
        self.assertTrue(FEATURE_HEADER.startswith(
            "local_timestamp_us,best_bid,best_ask,mid,book_valid,"
        ))
        self.assertTrue(FEATURE_HEADER.endswith(
            "mlofi_l5_1s_x_spread_bps"
        ))
        self.assertEqual(len(FEATURE_HEADER.split(",")), 51)

    def test_invalid_result_preserves_observed_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = derived_paths(root)["book250"]
            p.parent.mkdir(parents=True)
            p.write_text("opaque-derived", encoding="utf-8")

            r = invalid_result_from_exception(
                RuntimeError("boom"),
                root,
            )

            self.assertEqual(r["status"], "INVALID")
            self.assertEqual(r["failure_type"], "RuntimeError")
            self.assertEqual(r["failure_message"], "boom")
            self.assertIn("book250", r["observed_derived_artifacts"])
            self.assertTrue(r["august_raw_gzip_decompressed"])
            self.assertTrue(r["august_raw_csv_parsed_by_frozen_tools"])
            self.assertFalse(r["features_generated"])
            self.assertFalse(r["target_scored"])
            self.assertFalse(r["model_fit"])
            self.assertFalse(r["auc_scored"])
            self.assertFalse(r["direction_scored"])
            self.assertFalse(r["pnl_scored"])

    def test_count_rows_detects_bad_grid(self):
        start, _ = day_bounds_us()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "dummy.csv"
            p.write_text(
                "local_timestamp_us,x\n"
                f"{start},1\n"
                f"{start + GRID_US + 1},2\n",
                encoding="utf-8",
            )
            r = count_rows_and_grid(p)
            self.assertFalse(r["grid_250ms_exact"])


if __name__ == "__main__":
    unittest.main()

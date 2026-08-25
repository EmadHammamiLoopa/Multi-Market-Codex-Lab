from __future__ import annotations

import gzip
import hashlib
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np

from multimarket.codex_exp005_acquire import (
    DAYS,
    DatasetRequest,
    build_manifest_payload,
    download_one,
    frozen_requests,
)
from multimarket.codex_exp005_audit import (
    _git_ignored,
    _parse_numeric,
    asof_indices,
    asof_values,
    classify_schema,
    decision_coverage,
    deterministic_order_and_deduplicate,
    gap_stats,
    parse_timestamp_us,
    readiness,
)
from multimarket.codex_research import ResearchSealError


class NeverNetworkClient:
    def stream(self, *args, **kwargs):
        raise AssertionError("network must not be used for an existing raw file")


class Exp005Tests(unittest.TestCase):
    def test_frozen_request_count_is_14(self) -> None:
        reqs = frozen_requests()
        self.assertEqual(len(reqs), 14)
        self.assertEqual({r.symbol for r in reqs}, {"BTCUSDT", "ETHUSDT"})
        self.assertEqual({r.day for r in reqs}, set(DAYS))

    def test_rejects_unfrozen_symbol(self) -> None:
        with self.assertRaises(ValueError):
            DatasetRequest("XRPUSDT", DAYS[0]).validate()

    def test_rejects_unfrozen_date_before_path_or_url(self) -> None:
        request = DatasetRequest("BTCUSDT", date(2026, 8, 1))
        with self.assertRaises(ResearchSealError):
            _ = request.url
        with self.assertRaises(ResearchSealError):
            _ = request.output_path(Path("/tmp/raw"))

    def test_destination_is_deterministic(self) -> None:
        request = DatasetRequest("BTCUSDT", DAYS[0])
        expected = Path(
            "/tmp/raw/binance-futures/derivative_ticker/BTCUSDT/2026-01-01.csv.gz"
        )
        self.assertEqual(request.output_path(Path("/tmp/raw")), expected)

    def test_url_is_deterministic(self) -> None:
        request = DatasetRequest("ETHUSDT", DAYS[1])
        self.assertEqual(
            request.url,
            "https://datasets.tardis.dev/v1/binance-futures/derivative_ticker/2026/02/01/ETHUSDT.csv.gz",
        )

    def test_schema_prefers_local_timestamp(self) -> None:
        schema, resolved = classify_schema(
            (
                "exchange",
                "symbol",
                "timestamp",
                "local_timestamp",
                "open_interest",
                "funding_rate",
                "mark_price",
                "index_price",
            )
        )
        self.assertEqual(schema.availability_timestamp, "local_timestamp")
        self.assertEqual(schema.event_timestamp, "timestamp")
        self.assertEqual(schema.open_interest, "PRESENT_NATIVE")
        self.assertEqual(schema.premium, "DERIVABLE_CAUSALLY")
        self.assertEqual(resolved["local_timestamp"], "local_timestamp")

    def test_schema_falls_back_to_exchange_timestamp(self) -> None:
        schema, _ = classify_schema(("timestamp", "open_interest"))
        self.assertEqual(schema.availability_timestamp, "timestamp")
        self.assertEqual(schema.premium, "ABSENT")

    def test_timestamp_parser_accepts_microseconds_and_iso(self) -> None:
        self.assertEqual(parse_timestamp_us("1609459200000000"), 1609459200000000)
        self.assertEqual(
            parse_timestamp_us("2021-01-01T00:00:00Z"), 1609459200000000
        )

    def test_blank_numeric_is_missing_not_malformed(self) -> None:
        value, malformed = _parse_numeric("")
        self.assertTrue(np.isnan(value))
        self.assertFalse(malformed)
        value, malformed = _parse_numeric("not-a-number")
        self.assertTrue(np.isnan(value))
        self.assertTrue(malformed)

    def test_exact_duplicate_rows_are_removed_but_distinct_same_timestamp_rows_remain(self) -> None:
        ts = np.asarray([100, 100, 100, 200], dtype=np.int64)
        rows = [
            {"x": "a"},
            {"x": "a"},
            {"x": "b"},
            {"x": "c"},
        ]
        out_ts, out_rows, duplicates = deterministic_order_and_deduplicate(ts, rows)
        np.testing.assert_array_equal(out_ts, np.asarray([100, 100, 200]))
        self.assertEqual([row["x"] for row in out_rows], ["a", "b", "c"])
        self.assertEqual(duplicates, 1)

    def test_ordering_sorts_timestamp_regressions_without_future_values(self) -> None:
        ts = np.asarray([300, 100, 200], dtype=np.int64)
        rows = [{"x": "c"}, {"x": "a"}, {"x": "b"}]
        out_ts, out_rows, duplicates = deterministic_order_and_deduplicate(ts, rows)
        np.testing.assert_array_equal(out_ts, np.asarray([100, 200, 300]))
        self.assertEqual([row["x"] for row in out_rows], ["a", "b", "c"])
        self.assertEqual(duplicates, 0)

    def test_gap_statistics(self) -> None:
        stats = gap_stats(np.asarray([0, 10, 30, 60], dtype=np.int64))
        self.assertEqual(stats["longest_us"], 30)
        self.assertAlmostEqual(stats["median_us"], 20.0)

    def test_asof_alignment_is_past_only(self) -> None:
        records = np.asarray([100, 200, 400], dtype=np.int64)
        decisions = np.asarray([50, 100, 199, 200, 399, 400, 401], dtype=np.int64)
        idx = asof_indices(records, decisions)
        np.testing.assert_array_equal(idx, np.asarray([-1, 0, 0, 1, 1, 2, 2]))
        valid = idx >= 0
        self.assertTrue(np.all(records[idx[valid]] <= decisions[valid]))

    def test_sparse_native_state_carries_forward_past_only(self) -> None:
        update_ts = np.asarray([100, 300], dtype=np.int64)
        update_values = np.asarray([1.0, 2.0], dtype=np.float64)
        decisions = np.asarray([50, 100, 200, 299, 300, 400], dtype=np.int64)
        values, source_ts = asof_values(update_ts, update_values, decisions)
        self.assertTrue(np.isnan(values[0]))
        np.testing.assert_allclose(values[1:], np.asarray([1, 1, 1, 2, 2], float))
        valid = source_ts >= 0
        self.assertTrue(np.all(source_ts[valid] <= decisions[valid]))

    def test_decision_coverage_uses_latest_native_update(self) -> None:
        updates = np.asarray([100, 300], dtype=np.int64)
        decisions = np.asarray([50, 100, 200, 300, 400], dtype=np.int64)
        coverage = decision_coverage(updates, decisions)
        self.assertEqual(coverage["covered"], 4)
        self.assertAlmostEqual(coverage["fraction"], 0.8)

    def test_decision_coverage_can_enforce_staleness(self) -> None:
        updates = np.asarray([0], dtype=np.int64)
        decisions = np.asarray([0, 10, 20], dtype=np.int64)
        coverage = decision_coverage(updates, decisions, max_staleness_us=10)
        self.assertEqual(coverage["covered"], 2)

    def test_manifest_payload_preserves_sha256_records(self) -> None:
        records = [
            {
                "symbol": "BTCUSDT",
                "day": "2026-01-01",
                "sha256": "a" * 64,
                "bytes": 123,
            }
        ]
        payload = build_manifest_payload("b" * 40, records)
        self.assertEqual(payload["files"][0]["sha256"], "a" * 64)
        self.assertEqual(payload["file_count"], 1)
        self.assertFalse(payload["sealed_august_opened"])

    def test_existing_raw_file_is_not_overwritten_or_redownloaded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            request = DatasetRequest("BTCUSDT", DAYS[0])
            target = request.output_path(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = (
                "exchange,symbol,timestamp,local_timestamp,open_interest\n"
                "binance-futures,BTCUSDT,1767225600000000,1767225600000100,100\n"
            )
            with gzip.open(target, "wt", encoding="utf-8") as handle:
                handle.write(raw)
            before = target.read_bytes()
            expected_sha = hashlib.sha256(before).hexdigest()
            result = download_one(request, root, client=NeverNetworkClient())
            after = target.read_bytes()
            self.assertEqual(before, after)
            self.assertEqual(result["status"], "EXISTING_VALID")
            self.assertEqual(result["sha256"], expected_sha)

    def _ready_audits(self, premium: bool = True) -> list[dict]:
        audits = []
        for symbol in ("BTCUSDT", "ETHUSDT"):
            for day in DAYS:
                audits.append(
                    {
                        "symbol": symbol,
                        "day": day.isoformat(),
                        "schema": {
                            "availability_timestamp": "local_timestamp",
                            "open_interest": "PRESENT_NATIVE",
                            "premium": "DERIVABLE_CAUSALLY" if premium else "ABSENT",
                        },
                        "malformed_nonblank_numeric_fraction": 0.0,
                        "fields": {
                            "open_interest": {
                                "decision_coverage_no_staleness_limit": {
                                    "fraction": 0.99
                                }
                            }
                        },
                        "premium": (
                            {
                                "decision_coverage_no_staleness_limit": {
                                    "fraction": 0.99
                                }
                            }
                            if premium
                            else None
                        ),
                    }
                )
        return audits

    def test_readiness_data_ready_when_all_core_and_premium_pass(self) -> None:
        out = readiness(self._ready_audits(premium=True), raw_ignored=True)
        self.assertEqual(out["status"], "DATA_READY_SANDBOX")

    def test_readiness_partial_if_core_passes_but_premium_absent(self) -> None:
        out = readiness(self._ready_audits(premium=False), raw_ignored=True)
        self.assertEqual(out["status"], "PARTIAL_DATA_READY")

    def test_readiness_fails_if_raw_directory_not_ignored(self) -> None:
        out = readiness(self._ready_audits(premium=True), raw_ignored=False)
        self.assertEqual(out["status"], "FAIL_DERIVATIVES_DATA_NOT_READY")

    def test_gitignore_helper_detects_exp005_raw_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
            (workspace / ".gitignore").write_text(
                "data/codex_exp005_derivatives_raw/\n", encoding="utf-8"
            )
            raw_root = workspace / "data/codex_exp005_derivatives_raw"
            raw_root.mkdir(parents=True)
            (raw_root / "sentinel.bin").write_bytes(b"x")
            self.assertTrue(_git_ignored(workspace, raw_root))


if __name__ == "__main__":
    unittest.main()

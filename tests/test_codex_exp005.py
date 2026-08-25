from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np

from multimarket.codex_exp005_acquire import DAYS, DatasetRequest, frozen_requests
from multimarket.codex_exp005_audit import (
    asof_indices,
    classify_schema,
    decision_coverage,
    deterministic_deduplicate,
    gap_stats,
    parse_timestamp_us,
    readiness,
)
from multimarket.codex_research import ResearchSealError


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
        expected = Path("/tmp/raw/binance-futures/derivative_ticker/BTCUSDT/2026-01-01.csv.gz")
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
                "exchange", "symbol", "timestamp", "local_timestamp", "open_interest",
                "funding_rate", "mark_price", "index_price",
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
        self.assertEqual(parse_timestamp_us("2021-01-01T00:00:00Z"), 1609459200000000)

    def test_deduplicate_last_file_order_record_wins(self) -> None:
        ts = np.asarray([100, 100, 200], dtype=np.int64)
        rows = [{"x": "a"}, {"x": "b"}, {"x": "c"}]
        out_ts, out_rows, duplicates = deterministic_deduplicate(ts, rows)
        np.testing.assert_array_equal(out_ts, np.asarray([100, 200]))
        self.assertEqual([r["x"] for r in out_rows], ["b", "c"])
        self.assertEqual(duplicates, 1)

    def test_deduplicate_sorts_regressions_without_future_values(self) -> None:
        ts = np.asarray([300, 100, 200], dtype=np.int64)
        rows = [{"x": "c"}, {"x": "a"}, {"x": "b"}]
        out_ts, out_rows, _ = deterministic_deduplicate(ts, rows)
        np.testing.assert_array_equal(out_ts, np.asarray([100, 200, 300]))
        self.assertEqual([r["x"] for r in out_rows], ["a", "b", "c"])

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

    def test_decision_coverage_respects_value_validity(self) -> None:
        records = np.asarray([100, 200, 300], dtype=np.int64)
        decisions = np.asarray([100, 150, 200, 250, 300], dtype=np.int64)
        values = np.asarray([True, False, True])
        coverage = decision_coverage(records, decisions, values)
        self.assertEqual(coverage["covered"], 3)
        self.assertAlmostEqual(coverage["fraction"], 0.6)

    def test_decision_coverage_can_enforce_staleness(self) -> None:
        records = np.asarray([0], dtype=np.int64)
        decisions = np.asarray([0, 10, 20], dtype=np.int64)
        coverage = decision_coverage(records, decisions, np.asarray([True]), max_staleness_us=10)
        self.assertEqual(coverage["covered"], 2)

    def test_readiness_data_ready_when_all_core_and_premium_pass(self) -> None:
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
                            "premium": "DERIVABLE_CAUSALLY",
                        },
                        "malformed_or_nonfinite_numeric_fraction": 0.0,
                        "fields": {
                            "open_interest": {
                                "decision_coverage_no_staleness_limit": {"fraction": 0.99}
                            }
                        },
                        "premium": {
                            "decision_coverage_no_staleness_limit": {"fraction": 0.99}
                        },
                    }
                )
        out = readiness(audits, raw_ignored=True)
        self.assertEqual(out["status"], "DATA_READY_SANDBOX")

    def test_readiness_partial_if_core_passes_but_premium_absent(self) -> None:
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
                            "premium": "ABSENT",
                        },
                        "malformed_or_nonfinite_numeric_fraction": 0.0,
                        "fields": {
                            "open_interest": {
                                "decision_coverage_no_staleness_limit": {"fraction": 0.99}
                            }
                        },
                        "premium": None,
                    }
                )
        out = readiness(audits, raw_ignored=True)
        self.assertEqual(out["status"], "PARTIAL_DATA_READY")

    def test_readiness_fails_if_raw_directory_not_ignored(self) -> None:
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
                            "premium": "DERIVABLE_CAUSALLY",
                        },
                        "malformed_or_nonfinite_numeric_fraction": 0.0,
                        "fields": {
                            "open_interest": {
                                "decision_coverage_no_staleness_limit": {"fraction": 0.99}
                            }
                        },
                        "premium": {
                            "decision_coverage_no_staleness_limit": {"fraction": 0.99}
                        },
                    }
                )
        out = readiness(audits, raw_ignored=False)
        self.assertEqual(out["status"], "FAIL_DERIVATIVES_DATA_NOT_READY")


if __name__ == "__main__":
    unittest.main()

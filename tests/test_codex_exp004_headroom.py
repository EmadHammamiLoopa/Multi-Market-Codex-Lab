from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

from multimarket.codex_exp004_headroom import (
    DAYS,
    HORIZONS_S,
    KEY_HEADROOM_BPS,
    STRONG_HEADROOM_BPS,
    assert_fresh_output,
    executable_fixed_horizon,
    evaluate_model_worthiness,
    feature_path,
    scheduled_indices,
    summarize_outcomes,
)
from multimarket.codex_research import ResearchSealError
from multimarket.v23_phase0dl_score import DayData

GRID_US = 250_000


def synthetic_day(rows: int = 20000) -> DayData:
    day = DAYS[0]
    start = int(
        datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp()
        * 1_000_000
    )
    ts = start + np.arange(rows, dtype=np.int64) * GRID_US
    mid = 100.0 * np.exp(np.arange(rows, dtype=np.float64) * 0.000001)
    bid = mid * (1.0 - 0.00005)
    ask = mid * (1.0 + 0.00005)
    valid = np.ones(rows, dtype=bool)
    return DayData(
        day,
        ts,
        bid,
        ask,
        mid,
        valid,
        {"L0": valid.copy(), "L1": valid.copy(), "L2": valid.copy()},
        {
            "L0": np.empty((rows, 0)),
            "L1": np.empty((rows, 0)),
            "L2": np.empty((rows, 0)),
        },
    )


class HeadroomAuditTests(unittest.TestCase):
    def test_entry_and_exit_are_exact(self) -> None:
        day = synthetic_day()
        indices = np.asarray([0, 240, 480], dtype=np.int64)
        result = executable_fixed_horizon(day, indices, 60)
        np.testing.assert_array_equal(result["entry_index"], indices + 1)
        np.testing.assert_array_equal(result["exit_index"], indices + 1 + 240)

    def test_touch_semantics_and_oracle(self) -> None:
        day = synthetic_day()
        result = executable_fixed_horizon(day, np.asarray([0], dtype=np.int64), 60)
        e = 1
        x = 241
        expected_long = 10000.0 * np.log(day.bid[x] / day.ask[e])
        expected_short = 10000.0 * np.log(day.bid[e] / day.ask[x])
        self.assertAlmostEqual(result["long_gross_bps"][0], expected_long)
        self.assertAlmostEqual(result["short_gross_bps"][0], expected_short)
        self.assertAlmostEqual(
            result["oracle_gross_bps"][0], max(expected_long, expected_short)
        )

    def test_dense_schedule_is_exactly_one_minute(self) -> None:
        day = synthetic_day()
        idx = scheduled_indices(day, horizon_s=300, schedule="dense_1m")
        self.assertTrue(np.all(np.diff(idx) == 240))

    def test_nonoverlap_schedule_matches_horizon(self) -> None:
        day = synthetic_day()
        idx = scheduled_indices(day, horizon_s=300, schedule="nonoverlap")
        self.assertTrue(np.all(np.diff(idx) == 1200))

    def test_day_boundary_crossing_is_invalid(self) -> None:
        day = synthetic_day(rows=1000)
        indices = np.asarray([999], dtype=np.int64)
        result = executable_fixed_horizon(day, indices, 60)
        self.assertFalse(result["valid"][0])

    def test_invalid_decision_entry_or_exit_book_is_rejected(self) -> None:
        day = synthetic_day()
        day.book_valid[0] = False
        result = executable_fixed_horizon(day, np.asarray([0], dtype=np.int64), 60)
        self.assertFalse(result["valid"][0])

        day = synthetic_day()
        day.book_valid[1] = False
        result = executable_fixed_horizon(day, np.asarray([0], dtype=np.int64), 60)
        self.assertFalse(result["valid"][0])

        day = synthetic_day()
        day.book_valid[241] = False
        result = executable_fixed_horizon(day, np.asarray([0], dtype=np.int64), 60)
        self.assertFalse(result["valid"][0])

    def test_sealed_and_outside_days_are_rejected_before_path_use(self) -> None:
        with self.assertRaises(ResearchSealError):
            feature_path(Path("/tmp/features"), "BTCUSDT", date(2026, 8, 1))
        with self.assertRaises(ResearchSealError):
            feature_path(Path("/tmp/features"), "BTCUSDT", date(2026, 8, 4))
        with self.assertRaises(ResearchSealError):
            feature_path(Path("/tmp/features"), "BTCUSDT", date(2025, 12, 1))

    def test_existing_output_or_partial_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output = root / "result.json"
            output.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                assert_fresh_output(output)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output = root / "result.json"
            partial = root / "result.json.part"
            partial.write_text("partial", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                assert_fresh_output(output)

    def test_threshold_counts_are_deterministic(self) -> None:
        outcomes = {
            "valid": np.ones(4, dtype=bool),
            "long_gross_bps": np.asarray([1.0, 25.0, -4.0, 50.0]),
            "short_gross_bps": np.asarray([2.0, -1.0, 37.0, 5.0]),
            "oracle_gross_bps": np.asarray([2.0, 25.0, 37.0, 50.0]),
        }
        summary = summarize_outcomes(outcomes)
        self.assertEqual(
            summary["headroom"][str(int(KEY_HEADROOM_BPS))]["count"], 3
        )
        self.assertEqual(
            summary["headroom"][str(int(STRONG_HEADROOM_BPS))]["count"], 2
        )
        self.assertAlmostEqual(
            summary["headroom"][str(int(KEY_HEADROOM_BPS))]["fraction"], 0.75
        )

    def test_model_worthiness_uses_nonoverlap_only_and_shortest_eligible(self) -> None:
        rows = []
        for horizon_s in HORIZONS_S:
            for symbol in ("BTCUSDT", "ETHUSDT"):
                for day in DAYS:
                    for schedule in ("dense_1m", "nonoverlap"):
                        key_count = (
                            10
                            if schedule == "nonoverlap" and horizon_s in (300, 600)
                            else 0
                        )
                        strong_count = (
                            5
                            if schedule == "nonoverlap" and horizon_s in (300, 600)
                            else 0
                        )
                        summary = {
                            "valid_decisions": 100,
                            "headroom": {
                                str(int(KEY_HEADROOM_BPS)): {
                                    "count": key_count,
                                    "fraction": key_count / 100,
                                },
                                str(int(STRONG_HEADROOM_BPS)): {
                                    "count": strong_count,
                                    "fraction": strong_count / 100,
                                },
                            },
                        }
                        rows.append(
                            {
                                "symbol": symbol,
                                "day": day.isoformat(),
                                "horizon_s": horizon_s,
                                "schedule": schedule,
                                "summary": summary,
                            }
                        )
        result = evaluate_model_worthiness(rows)
        self.assertEqual(result["eligible_horizons_s"], [300, 600])
        self.assertEqual(result["selected_shortest_eligible_horizon_s"], 300)
        self.assertEqual(result["status"], "MODEL_WORTHY_SANDBOX")


if __name__ == "__main__":
    unittest.main()

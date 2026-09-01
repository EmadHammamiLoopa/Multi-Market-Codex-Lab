from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import math
import unittest

import numpy as np

from multimarket import dev030_first_passage as fp
from multimarket.codex_exp004_headroom import executable_fixed_horizon
from multimarket.v23_phase0dl_score import DayData


@dataclass
class SyntheticDay:
    ts: np.ndarray
    bid: np.ndarray
    ask: np.ndarray
    book_valid: np.ndarray


def synthetic_day(
    rows: int = 16,
    *,
    start_us: int = 0,
    bid: float = 100.0,
    ask: float = 100.1,
) -> SyntheticDay:
    return SyntheticDay(
        ts=start_us + np.arange(rows, dtype=np.int64) * fp.GRID_US,
        bid=np.full(rows, bid, dtype=np.float64),
        ask=np.full(rows, ask, dtype=np.float64),
        book_valid=np.ones(rows, dtype=bool),
    )


def clone_day(day: SyntheticDay) -> SyntheticDay:
    return SyntheticDay(
        ts=day.ts.copy(),
        bid=day.bid.copy(),
        ask=day.ask.copy(),
        book_valid=day.book_valid.copy(),
    )


def target(
    day: SyntheticDay,
    *,
    decision_index: int = 0,
    horizon_seconds: float = 1.0,
    barrier_bps: float = 20.0,
) -> dict[str, object]:
    return fp.label_first_passage_targets(
        day,
        np.asarray([decision_index], dtype=np.int64),
        horizon_seconds=horizon_seconds,
        barrier_bps=barrier_bps,
    )[0]


class FirstPassageLabelTests(unittest.TestCase):
    def test_long_first(self) -> None:
        day = synthetic_day()
        day.bid[3] = 100.5
        day.ask[3] = 100.6
        result = target(day)

        self.assertEqual(result["label"], fp.LONG_FIRST)
        self.assertIs(result["target_valid"], True)
        self.assertIsNone(result["invalid_reason"])
        self.assertIs(result["same_row_ambiguous"], False)

    def test_short_first(self) -> None:
        day = synthetic_day()
        day.bid[2] = 99.4
        day.ask[2] = 99.5
        result = target(day)

        self.assertEqual(result["label"], fp.SHORT_FIRST)
        self.assertIs(result["target_valid"], True)

    def test_none_requires_complete_valid_no_touch_path(self) -> None:
        result = target(synthetic_day(), barrier_bps=100.0)

        self.assertEqual(result["label"], fp.NONE)
        self.assertIs(result["target_valid"], True)
        self.assertIsNone(result["invalid_reason"])
        self.assertIsNone(result["time_to_first_barrier_ms"])
        self.assertIsNone(result["barrier_reached_timestamp_us"])

    def test_barrier_equality_counts_as_reached(self) -> None:
        day = synthetic_day(bid=99.9, ask=100.0)
        exact_bid = 100.2
        exact_barrier = 10_000.0 * math.log(exact_bid / day.ask[1])
        day.bid[2] = exact_bid
        day.ask[2] = 100.3

        result = target(day, barrier_bps=exact_barrier)

        self.assertEqual(result["label"], fp.LONG_FIRST)
        self.assertEqual(result["barrier_reached_timestamp_us"], int(day.ts[2]))

    def test_exact_horizon_endpoint_is_included(self) -> None:
        day = synthetic_day(rows=8)
        # Decision 0, entry 1, one-second inclusive horizon endpoint 5.
        day.bid[5] = 100.5
        day.ask[5] = 100.6

        result = target(day)

        self.assertEqual(result["label"], fp.LONG_FIRST)
        self.assertEqual(result["barrier_reached_timestamp_us"], int(day.ts[5]))
        self.assertEqual(result["time_to_first_barrier_ms"], 1000.0)

    def test_quote_after_horizon_cannot_change_result(self) -> None:
        day = synthetic_day(rows=8)
        original = target(day, barrier_bps=100.0)
        mutated = clone_day(day)
        mutated.bid[6] = 110.0
        mutated.ask[6] = 110.1

        self.assertEqual(target(mutated, barrier_bps=100.0), original)
        self.assertEqual(original["label"], fp.NONE)

    def test_entry_is_exactly_t_plus_250ms_and_decision_quote_is_unused(self) -> None:
        day = synthetic_day()
        day.bid[0] = 1_000.0
        day.ask[0] = 1.0  # Deliberately crossed; the decision quote is not entry.
        result = target(day, barrier_bps=100.0)

        self.assertEqual(result["entry_timestamp_us"], int(day.ts[0] + fp.GRID_US))
        self.assertEqual(result["label"], fp.NONE)
        self.assertIs(result["target_valid"], True)

    def test_invalid_entry_quotes_are_rejected(self) -> None:
        cases = (
            (math.nan, 100.1),
            (100.0, math.inf),
            (0.0, 100.1),
            (-1.0, 100.1),
            (100.0, 0.0),
        )
        for bid, ask in cases:
            with self.subTest(bid=bid, ask=ask):
                day = synthetic_day()
                day.bid[1] = bid
                day.ask[1] = ask
                result = target(day)
                self.assertIs(result["target_valid"], False)
                self.assertIsNone(result["label"])
                self.assertEqual(result["invalid_reason"], fp.INVALID_ENTRY_QUOTE)

        day = synthetic_day()
        day.book_valid[1] = False
        result = target(day)
        self.assertEqual(result["invalid_reason"], fp.INVALID_ENTRY_QUOTE)

    def test_invalid_quote_anywhere_in_full_future_path_rejects_target(self) -> None:
        day = synthetic_day()
        day.bid[2] = 100.5
        day.ask[2] = 100.6  # A touch occurs before the invalid later row.
        day.book_valid[4] = False

        result = target(day)

        self.assertIs(result["target_valid"], False)
        self.assertIsNone(result["label"])
        self.assertEqual(result["invalid_reason"], fp.INVALID_PATH_QUOTE)

    def test_nonfinite_or_nonpositive_future_quote_is_invalid(self) -> None:
        for value in (math.nan, math.inf, 0.0, -1.0):
            with self.subTest(value=value):
                day = synthetic_day()
                day.bid[3] = value
                result = target(day)
                self.assertEqual(result["invalid_reason"], fp.INVALID_PATH_QUOTE)
                self.assertIsNone(result["label"])

    def test_crossed_book_is_invalid(self) -> None:
        day = synthetic_day()
        day.bid[3] = 100.2
        day.ask[3] = 100.0

        result = target(day, barrier_bps=1_000.0)

        self.assertIs(result["target_valid"], False)
        self.assertIsNone(result["label"])
        self.assertEqual(result["invalid_reason"], fp.INVALID_CROSSED_BOOK)

    def test_missing_interior_grid_row_is_invalid_without_fill(self) -> None:
        day = synthetic_day(rows=8)
        missing = 3
        day.ts = np.delete(day.ts, missing)
        day.bid = np.delete(day.bid, missing)
        day.ask = np.delete(day.ask, missing)
        day.book_valid = np.delete(day.book_valid, missing)

        result = target(day)

        self.assertEqual(result["invalid_reason"], fp.INVALID_PATH_GRID)
        self.assertIsNone(result["label"])

    def test_missing_entry_is_invalid_without_forward_or_backward_fill(self) -> None:
        day = synthetic_day(rows=8)
        missing = 1
        day.ts = np.delete(day.ts, missing)
        day.bid = np.delete(day.bid, missing)
        day.ask = np.delete(day.ask, missing)
        day.book_valid = np.delete(day.book_valid, missing)

        result = target(day)

        self.assertEqual(result["invalid_reason"], fp.INVALID_ENTRY_TIMESTAMP)
        self.assertIsNone(result["label"])

    def test_missing_horizon_endpoint_is_invalid(self) -> None:
        day = synthetic_day(rows=5)

        result = target(day)

        self.assertEqual(result["invalid_reason"], fp.INVALID_HORIZON_TIMESTAMP)
        self.assertIsNone(result["label"])

    def test_day_boundary_crossing_is_invalid_even_if_rows_exist(self) -> None:
        start = fp.DAY_US - 2 * fp.GRID_US
        day = synthetic_day(rows=8, start_us=start)

        result = target(day)

        self.assertEqual(result["invalid_reason"], fp.INVALID_DAY_BOUNDARY)
        self.assertIs(result["target_valid"], False)
        self.assertIsNone(result["label"])

    def test_same_row_ambiguity_has_exact_invalid_representation(self) -> None:
        day = synthetic_day(bid=99.0, ask=101.0)
        # Positive symmetric touches on one row imply malformed crossed prices;
        # the engine must preserve the dedicated ambiguity diagnostic.
        day.bid[2] = 102.0
        day.ask[2] = 98.0

        result = target(day, barrier_bps=50.0)

        self.assertIsNone(result["label"])
        self.assertIs(result["target_valid"], False)
        self.assertEqual(result["invalid_reason"], "same_row_ambiguous")
        self.assertIs(result["same_row_ambiguous"], True)
        self.assertIsNone(result["time_to_first_barrier_ms"])
        self.assertIsNone(result["long_max_favorable_excursion_bps"])

    def test_every_invalid_reason_keeps_label_null_not_none_enum(self) -> None:
        invalid_results: list[dict[str, object]] = []

        entry_invalid = synthetic_day()
        entry_invalid.book_valid[1] = False
        invalid_results.append(target(entry_invalid))

        path_invalid = synthetic_day()
        path_invalid.book_valid[2] = False
        invalid_results.append(target(path_invalid))

        crossed = synthetic_day()
        crossed.bid[3], crossed.ask[3] = 100.2, 100.0
        invalid_results.append(target(crossed, barrier_bps=1_000.0))

        for result in invalid_results:
            self.assertIs(result["target_valid"], False)
            self.assertIsNone(result["label"])
            self.assertNotEqual(result["label"], fp.NONE)

    def test_mfe_and_mae_are_executable_and_hand_calculated(self) -> None:
        day = synthetic_day(bid=99.0, ask=101.0)
        day.bid[2], day.ask[2] = 102.0, 103.0
        day.bid[3], day.ask[3] = 97.0, 98.0
        result = target(day, barrier_bps=1_000.0)

        long_path = 10_000.0 * np.log(day.bid[1:6] / day.ask[1])
        short_path = 10_000.0 * np.log(day.bid[1] / day.ask[1:6])
        self.assertAlmostEqual(
            result["long_max_favorable_excursion_bps"],
            max(0.0, float(long_path.max())),
        )
        self.assertAlmostEqual(
            result["long_max_adverse_excursion_bps"],
            max(0.0, -float(long_path.min())),
        )
        self.assertAlmostEqual(
            result["short_max_favorable_excursion_bps"],
            max(0.0, float(short_path.max())),
        )
        self.assertAlmostEqual(
            result["short_max_adverse_excursion_bps"],
            max(0.0, -float(short_path.min())),
        )

    def test_entry_spread_is_executable_log_bps(self) -> None:
        day = synthetic_day(bid=99.0, ask=101.0)
        result = target(day, barrier_bps=1_000.0)

        self.assertAlmostEqual(
            result["entry_spread_bps"], 10_000.0 * math.log(101.0 / 99.0)
        )

    def test_touch_time_is_measured_from_entry(self) -> None:
        day = synthetic_day()
        day.bid[4], day.ask[4] = 100.5, 100.6

        result = target(day)

        self.assertEqual(result["label"], fp.LONG_FIRST)
        self.assertEqual(result["time_to_first_barrier_ms"], 750.0)
        self.assertEqual(result["barrier_reached_timestamp_us"], int(day.ts[4]))

    def test_later_decision_mutation_cannot_change_earlier_target(self) -> None:
        day = synthetic_day(rows=20)
        decisions = np.asarray([0, 8], dtype=np.int64)
        original = fp.label_first_passage_targets(
            day, decisions, horizon_seconds=1.0, barrier_bps=100.0
        )
        mutated = clone_day(day)
        mutated.bid[9:14] = 110.0
        mutated.ask[9:14] = 110.1
        changed = fp.label_first_passage_targets(
            mutated, decisions, horizon_seconds=1.0, barrier_bps=100.0
        )

        self.assertEqual(changed[0], original[0])
        self.assertNotEqual(changed[1], original[1])

    def test_input_arrays_are_not_mutated(self) -> None:
        day = synthetic_day()
        before = clone_day(day)
        target(day)

        np.testing.assert_array_equal(day.ts, before.ts)
        np.testing.assert_array_equal(day.bid, before.bid)
        np.testing.assert_array_equal(day.ask, before.ask)
        np.testing.assert_array_equal(day.book_valid, before.book_valid)


class FrozenHelperEquivalenceTests(unittest.TestCase):
    def test_horizon_end_arithmetic_matches_executable_fixed_horizon(self) -> None:
        rows = 245
        ts = np.arange(rows, dtype=np.int64) * fp.GRID_US
        mid = 100.0 * np.exp(np.arange(rows, dtype=np.float64) * 0.000002)
        bid = mid * 0.9999
        ask = mid * 1.0001
        valid = np.ones(rows, dtype=bool)
        day = DayData(
            date(1970, 1, 1),
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

        frozen = executable_fixed_horizon(day, np.asarray([0], dtype=np.int64), 60)
        result = fp.label_first_passage_targets(
            day,
            np.asarray([0], dtype=np.int64),
            horizon_seconds=60,
            barrier_bps=1_000_000.0,
        )[0]
        long_path, short_path = fp._executable_path_bps(
            day.bid[1:242], day.ask[1:242]
        )

        self.assertIs(result["target_valid"], True)
        self.assertAlmostEqual(long_path[-1], frozen["long_gross_bps"][0])
        self.assertAlmostEqual(short_path[-1], frozen["short_gross_bps"][0])


class PublicContractTests(unittest.TestCase):
    def test_public_records_are_finite_json_safe_builtin_scalars(self) -> None:
        valid_day = synthetic_day()
        invalid_day = clone_day(valid_day)
        invalid_day.book_valid[2] = False
        ambiguous_day = synthetic_day(bid=99.0, ask=101.0)
        ambiguous_day.bid[2], ambiguous_day.ask[2] = 102.0, 98.0

        records = [
            target(valid_day, barrier_bps=100.0),
            target(invalid_day),
            target(ambiguous_day, barrier_bps=50.0),
        ]
        json.dumps(records, allow_nan=False)

        for record in records:
            for value in record.values():
                self.assertIn(type(value), (str, int, float, bool, type(None)))
                if type(value) is float:
                    self.assertTrue(math.isfinite(value))

    def test_fixed_latency_and_positive_aligned_configuration(self) -> None:
        day = synthetic_day()
        with self.assertRaisesRegex(ValueError, "exactly 250 ms"):
            fp.label_first_passage_targets(
                day, [0], horizon_seconds=1, barrier_bps=20, latency_ms=500
            )
        for horizon in (0, -1, math.nan, 0.1):
            with self.subTest(horizon=horizon), self.assertRaises(ValueError):
                fp.label_first_passage_targets(
                    day, [0], horizon_seconds=horizon, barrier_bps=20
                )
        for barrier in (0, -1, math.nan, math.inf):
            with self.subTest(barrier=barrier), self.assertRaises(ValueError):
                fp.label_first_passage_targets(
                    day, [0], horizon_seconds=1, barrier_bps=barrier
                )

    def test_labeler_has_no_filesystem_or_network_interface(self) -> None:
        public = set(fp.__all__)
        self.assertEqual(
            public,
            {
                "GRID_US",
                "LATENCY_MS",
                "LONG_FIRST",
                "SHORT_FIRST",
                "NONE",
                "label_first_passage_targets",
            },
        )
        self.assertFalse(hasattr(fp, "main"))
        self.assertFalse(hasattr(fp, "load_day"))


if __name__ == "__main__":
    unittest.main()

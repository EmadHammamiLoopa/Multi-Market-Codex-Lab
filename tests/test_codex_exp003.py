from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np

from multimarket.codex_exp003 import (
    DAYS,
    FUTURE_CANARY_LEAD_US,
    GAP_BREAK_US,
    GRID_US,
    MAX_BOOK_AGE_US,
    PRIMARY_DELAY_US,
    SOURCE_FEATURE_NAMES,
    STRESS_DELAY_US,
    TRACKS,
    BookSeries,
    Exp003Day,
    ExternalFeatures,
    ResearchSealError,
    TradeSeries,
    TrainOnlyStandardizer,
    assemble_tracks,
    build_external_features,
    diagnostic_transform,
    evaluate_diagnostic_suite,
    executable_outcomes,
    external_paths,
    inject_future_leak_canary,
    load_book_snapshot_5,
    load_trades,
    roc_auc,
    score_symbol,
    split_calibration_selection,
)
from multimarket.codex_exp003_acquire import DatasetRequest, frozen_requests
from multimarket.v23_phase0dl_score import BLOCKS, DayData


def epoch_us(day: date = DAYS[0]) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp() * 1_000_000)


def book_series(
    local: np.ndarray,
    *,
    exchange: np.ndarray | None = None,
    mid: np.ndarray | None = None,
    valid: np.ndarray | None = None,
) -> BookSeries:
    local = np.asarray(local, dtype=np.int64)
    exchange = local.copy() if exchange is None else np.asarray(exchange, dtype=np.int64)
    mid = 100.0 + np.arange(len(local)) * 0.01 if mid is None else np.asarray(mid, dtype=np.float64)
    valid = np.ones(len(local), dtype=bool) if valid is None else np.asarray(valid, dtype=bool)
    breaks = np.ones(len(local), dtype=bool)
    if len(local) > 1:
        breaks[1:] = (np.diff(local) > GAP_BREAK_US) | (~valid[1:]) | (~valid[:-1])
    segment = np.cumsum(breaks, dtype=np.int64)
    squared = np.zeros(len(local), dtype=np.float64)
    if len(local) > 1:
        same = valid[1:] & valid[:-1] & (segment[1:] == segment[:-1])
        returns = np.zeros(len(local) - 1, dtype=np.float64)
        returns[same] = np.log(mid[1:][same] / mid[:-1][same])
        squared[1:] = returns * returns
    return BookSeries(
        local,
        exchange,
        mid,
        np.full(len(local), 1.0),
        np.linspace(-0.2, 0.2, len(local)),
        np.linspace(-0.1, 0.1, len(local)),
        valid,
        segment,
        np.concatenate(([0.0], np.cumsum(squared))),
        {"synthetic": True},
    )


def trade_series(
    local: np.ndarray,
    *,
    side: np.ndarray | None = None,
    amount: np.ndarray | None = None,
    exchange: np.ndarray | None = None,
) -> TradeSeries:
    local = np.asarray(local, dtype=np.int64)
    side = np.ones(len(local), dtype=np.int8) if side is None else np.asarray(side, dtype=np.int8)
    amount = np.ones(len(local), dtype=np.float64) if amount is None else np.asarray(amount, dtype=np.float64)
    exchange = local.copy() if exchange is None else np.asarray(exchange, dtype=np.int64)
    buy = np.where(side > 0, amount, 0.0)
    sell = np.where(side < 0, amount, 0.0)
    prefix = lambda values: np.concatenate(([0], np.cumsum(values)))
    return TradeSeries(
        local,
        exchange,
        side,
        amount,
        prefix(buy).astype(np.float64),
        prefix(sell).astype(np.float64),
        prefix((side > 0).astype(np.int64)).astype(np.int64),
        prefix((side < 0).astype(np.int64)).astype(np.int64),
        {"synthetic": True},
    )


def causal_fixture(rows: int = 100) -> tuple[np.ndarray, np.ndarray, np.ndarray, BookSeries, TradeSeries]:
    start = epoch_us()
    decision = start + np.arange(rows, dtype=np.int64) * GRID_US
    local = start + np.arange(rows, dtype=np.int64) * GRID_US
    mid = 100.0 * np.exp(np.arange(rows) * 0.00001)
    book = book_series(local, mid=mid)
    trades = trade_series(local, side=np.where(np.arange(rows) % 2 == 0, 1, -1))
    return decision, mid.copy(), np.ones(rows, dtype=bool), book, trades


def synthetic_exp003_day(day: date, rows: int = 120) -> Exp003Day:
    start = epoch_us(day)
    ts = start + np.arange(rows, dtype=np.int64) * GRID_US
    mid = 100.0 + np.sin(np.arange(rows) / 3.0)
    bid, ask = mid - 0.01, mid + 0.01
    values = {}
    names = {}
    valid = {}
    widths = {"X0": len(BLOCKS["L2"]), "X1": len(BLOCKS["L2"]) + 17, "X2": len(BLOCKS["L2"]) + 17, "XALL": len(BLOCKS["L2"]) + 34}
    for track, width in widths.items():
        values[track] = np.tile(np.arange(width, dtype=np.float32), (rows, 1))
        base_names = tuple(f"f{i}" for i in range(len(BLOCKS["L2"])))
        if track == "X0":
            names[track] = base_names
        elif track == "X1":
            names[track] = base_names + tuple(f"binance_spot__{name}" for name in SOURCE_FEATURE_NAMES)
        elif track == "X2":
            names[track] = base_names + tuple(f"bybit_linear_perpetual__{name}" for name in SOURCE_FEATURE_NAMES)
        else:
            names[track] = (
                base_names
                + tuple(f"binance_spot__{name}" for name in SOURCE_FEATURE_NAMES)
                + tuple(f"bybit_linear_perpetual__{name}" for name in SOURCE_FEATURE_NAMES)
            )
        valid[track] = np.ones(rows, dtype=bool)
    return Exp003Day(
        day,
        ts,
        bid,
        ask,
        mid,
        np.ones(rows, dtype=bool),
        valid,
        values,
        names,
        {"binance": ts - PRIMARY_DELAY_US, "bybit": ts - PRIMARY_DELAY_US},
        {"binance": np.full(rows, PRIMARY_DELAY_US), "bybit": np.full(rows, PRIMARY_DELAY_US)},
        {},
    )


class TimestampCausalityTests(unittest.TestCase):
    def test_tardis_parsers_preserve_local_order_and_atomic_book_state(self) -> None:
        start = epoch_us()
        book_header = ["exchange", "symbol", "timestamp", "local_timestamp"]
        for level in range(5):
            book_header.extend(
                [
                    f"asks[{level}].price",
                    f"asks[{level}].amount",
                    f"bids[{level}].price",
                    f"bids[{level}].amount",
                ]
            )

        def book_row(local_ts: int, best_ask: float, exchange_ts: int) -> list[object]:
            row: list[object] = ["binance", "BTCUSDT", exchange_ts, local_ts]
            for level in range(5):
                row.extend([best_ask + level, 10 + level, 99 - level, 11 + level])
            return row

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            book_path = root / "book.csv"
            with book_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(book_header)
                writer.writerow(book_row(start + 1_000_000, 101.0, start + 900_000))
                writer.writerow(book_row(start + 1_000_000, 100.5, start + 800_000))
                writer.writerow(book_row(start + 1_250_000, 100.75, start + 700_000))
            parsed = load_book_snapshot_5(
                book_path, exchange="binance", symbol="BTCUSDT", day=DAYS[0]
            )
            self.assertEqual(len(parsed.local_timestamp_us), 2)
            self.assertEqual(parsed.audit["duplicate_local_rows_collapsed"], 1)
            self.assertAlmostEqual(parsed.mid[0], 99.75)
            self.assertEqual(parsed.audit["exchange_timestamp_regressions"], 1)

            trade_path = root / "trades.csv"
            with trade_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    ["exchange", "symbol", "timestamp", "local_timestamp", "id", "side", "price", "amount"]
                )
                writer.writerow(["binance", "BTCUSDT", start, start + 1, "a", "buy", 100, 2])
                writer.writerow(["binance", "BTCUSDT", start + 2, start + 3, "a", "buy", 100, 2])
            parsed_trades = load_trades(
                trade_path, exchange="binance", symbol="BTCUSDT", day=DAYS[0]
            )
            self.assertEqual(len(parsed_trades.local_timestamp_us), 1)
            self.assertEqual(parsed_trades.audit["duplicate_trade_ids_removed"], 1)

    def test_asof_join_never_selects_future_local_timestamp(self) -> None:
        decision, target, target_valid, book, trades = causal_fixture()
        result = build_external_features(decision, target, target_valid, book, trades)
        cutoff = decision - PRIMARY_DELAY_US
        self.assertTrue(np.all(result.source_local_timestamp_us[result.valid] <= cutoff[result.valid]))
        self.assertEqual(result.audit["local_timestamp_eligibility_violations"], 0)

    def test_exact_500ms_delay_is_enforced(self) -> None:
        decision, target, target_valid, book, trades = causal_fixture()
        result = build_external_features(decision, target, target_valid, book, trades)
        self.assertTrue(np.all(result.source_age_us[result.valid] >= PRIMARY_DELAY_US))
        self.assertTrue(np.any(result.source_age_us[result.valid] == PRIMARY_DELAY_US))

    def test_stale_book_is_invalid(self) -> None:
        decision, target, target_valid, book, trades = causal_fixture()
        short_book = book_series(book.local_timestamp_us[:20], mid=book.mid[:20])
        short_trades = trade_series(
            trades.local_timestamp_us[:20], side=trades.side[:20], amount=trades.amount[:20]
        )
        late_decision = decision + 30_000_000
        result = build_external_features(
            late_decision, target, target_valid, short_book, short_trades
        )
        self.assertFalse(np.any(result.valid))

    def test_exchange_timestamps_cannot_override_local_ordering(self) -> None:
        decision, target, target_valid, book, trades = causal_fixture()
        reversed_exchange = book.exchange_timestamp_us[::-1].copy()
        altered = book_series(book.local_timestamp_us, exchange=reversed_exchange, mid=book.mid)
        trade_exchange = trades.exchange_timestamp_us[::-1].copy()
        altered_trades = trade_series(
            trades.local_timestamp_us,
            side=trades.side,
            amount=trades.amount,
            exchange=trade_exchange,
        )
        left = build_external_features(decision, target, target_valid, book, trades)
        right = build_external_features(decision, target, target_valid, altered, altered_trades)
        np.testing.assert_array_equal(left.valid, right.valid)
        np.testing.assert_allclose(left.values, right.values, equal_nan=True)

    def test_no_forward_fill_through_outage(self) -> None:
        start = epoch_us()
        before = start + np.arange(20, dtype=np.int64) * GRID_US
        after = before[-1] + GAP_BREAK_US + GRID_US + np.arange(20, dtype=np.int64) * GRID_US
        local = np.concatenate((before, after))
        book = book_series(local)
        decision = after + PRIMARY_DELAY_US
        target = 100.0 + np.arange(len(after)) * 0.01
        result = build_external_features(
            decision,
            target,
            np.ones(len(target), dtype=bool),
            book,
            trade_series(local),
        )
        # The first three seconds after a new segment cannot borrow pre-gap anchors.
        self.assertFalse(np.any(result.valid[:12]))

    def test_quantity_normalization_is_causal(self) -> None:
        decision, target, target_valid, book, trades = causal_fixture()
        cutoff_row = 60
        future_ts = decision[-1] + GRID_US
        changed = trade_series(
            np.append(trades.local_timestamp_us, future_ts),
            side=np.append(trades.side, 1),
            amount=np.append(trades.amount, 1e12),
        )
        left = build_external_features(decision, target, target_valid, book, trades)
        right = build_external_features(decision, target, target_valid, book, changed)
        np.testing.assert_allclose(left.values[:cutoff_row], right.values[:cutoff_row], equal_nan=True)

    def test_future_canary_is_explicit_and_cannot_enter_primary(self) -> None:
        decision, target, target_valid, book, trades = causal_fixture()
        with self.assertRaises(ResearchSealError):
            build_external_features(
                decision, target, target_valid, book, trades, delay_us=-FUTURE_CANARY_LEAD_US
            )
        canary = build_external_features(
            decision,
            target,
            target_valid,
            book,
            trades,
            delay_us=-FUTURE_CANARY_LEAD_US,
            canary=True,
        )
        self.assertTrue(canary.audit["future_canary"])
        self.assertTrue(np.any(canary.source_local_timestamp_us[canary.valid] > decision[canary.valid]))

    def test_extra_delay_stress_is_stricter(self) -> None:
        decision, target, target_valid, book, trades = causal_fixture()
        primary = build_external_features(decision, target, target_valid, book, trades)
        stress = build_external_features(
            decision, target, target_valid, book, trades, delay_us=STRESS_DELAY_US
        )
        self.assertTrue(np.all(stress.source_age_us[stress.valid] >= STRESS_DELAY_US))
        self.assertLessEqual(int(stress.valid.sum()), int(primary.valid.sum()))


class SplitAndSealTests(unittest.TestCase):
    def test_day_boundary_labels_are_purged(self) -> None:
        day = synthetic_exp003_day(DAYS[0], rows=100)
        outcomes = executable_outcomes(day, "XALL", 10)
        span = 1 + 10_000_000 // GRID_US
        self.assertFalse(np.any(outcomes.valid[-span:]))
        calibration, selection = split_calibration_selection(outcomes, horizon_s=10, n_rows=100)
        self.assertTrue(np.all(calibration + span < 50))
        self.assertTrue(np.all(selection >= 50))

    def test_sealed_date_is_rejected_before_open(self) -> None:
        with self.assertRaises(ResearchSealError):
            external_paths(Path("unopened"), "binance", "BTCUSDT", date(2026, 8, 1))

    def test_frozen_download_set_contains_only_first_days_jan_to_jul(self) -> None:
        requests = frozen_requests()
        self.assertEqual(len(requests), 56)
        self.assertTrue(all(request.day in DAYS for request in requests))
        self.assertTrue(all(request.day.day == 1 for request in requests))
        sample = DatasetRequest("bybit", "trades", "ETHUSDT", DAYS[-1])
        self.assertEqual(
            sample.url,
            "https://datasets.tardis.dev/v1/bybit/trades/2026/07/01/ETHUSDT.csv.gz",
        )

    def test_outer_day_is_never_passed_to_selection(self) -> None:
        days = [synthetic_exp003_day(day) for day in DAYS]
        calls: list[tuple[tuple[date, ...], date, str]] = []

        def fake_select(train, inner, track):
            calls.append((tuple(item.day for item in train), inner.day, track))
            return {"track": track}, {"tested": 0, "eligible": 1}

        with patch("multimarket.codex_exp003.select_configuration", side_effect=fake_select), patch(
            "multimarket.codex_exp003.score_outer", return_value={"costs": {}}
        ):
            score_symbol(days, "BTCUSDT")
        self.assertEqual(len(calls), 5 * len(TRACKS))
        for fold_index in range(5):
            expected_inner = DAYS[fold_index + 1]
            expected_outer = DAYS[fold_index + 2]
            for train, inner, _ in calls[fold_index * len(TRACKS) : (fold_index + 1) * len(TRACKS)]:
                self.assertEqual(inner, expected_inner)
                self.assertNotIn(expected_outer, train)
                self.assertTrue(all(day < inner for day in train))


class ModelAndDiagnosticTests(unittest.TestCase):
    def test_roc_auc_handles_ties_and_perfect_ranking(self) -> None:
        self.assertAlmostEqual(roc_auc(np.asarray([0, 0, 1, 1]), np.asarray([0.1, 0.2, 0.8, 0.9])), 1.0)
        self.assertAlmostEqual(roc_auc(np.asarray([0, 1]), np.asarray([0.5, 0.5])), 0.5)

    def test_scaler_is_fit_on_train_only(self) -> None:
        X_train = np.asarray([[0.0], [1.0], [2.0], [3.0]])
        X_cal = np.asarray([[100.0], [101.0], [102.0], [103.0]])
        scaler = TrainOnlyStandardizer().fit(X_train)
        self.assertAlmostEqual(float(scaler.mean_[0]), 1.5)
        self.assertNotAlmostEqual(float(scaler.mean_[0]), float(np.vstack((X_train, X_cal)).mean()))
        self.assertGreater(float(scaler.transform(X_cal)[0, 0]), 80.0)

    def test_tracks_use_identical_common_support(self) -> None:
        rows = 20
        start = epoch_us()
        ts = start + np.arange(rows) * GRID_US
        base = DayData(
            DAYS[0],
            ts,
            np.full(rows, 99.0),
            np.full(rows, 101.0),
            np.full(rows, 100.0),
            np.ones(rows, dtype=bool),
            {"L0": np.ones(rows, dtype=bool), "L1": np.ones(rows, dtype=bool), "L2": np.ones(rows, dtype=bool)},
            {
                "L0": np.zeros((rows, len(BLOCKS["L0"])), dtype=np.float32),
                "L1": np.zeros((rows, len(BLOCKS["L1"])), dtype=np.float32),
                "L2": np.zeros((rows, len(BLOCKS["L2"])), dtype=np.float32),
            },
        )
        spot_valid = np.ones(rows, dtype=bool)
        spot_valid[3] = False
        bybit_valid = np.ones(rows, dtype=bool)
        bybit_valid[7] = False
        def ext(valid):
            return ExternalFeatures(
                SOURCE_FEATURE_NAMES,
                np.zeros((rows, len(SOURCE_FEATURE_NAMES)), dtype=np.float32),
                valid,
                ts - PRIMARY_DELAY_US,
                np.full(rows, PRIMARY_DELAY_US),
                {},
            )
        day = assemble_tracks(base, ext(spot_valid), ext(bybit_valid))
        for track in TRACKS[1:]:
            np.testing.assert_array_equal(day.valid["X0"], day.valid[track])
        self.assertFalse(day.valid["XALL"][3])
        self.assertFalse(day.valid["XALL"][7])

    def test_timestamp_permutation_and_sign_time_placebos_do_not_touch_x0(self) -> None:
        day = synthetic_exp003_day(DAYS[0], rows=300)
        day.X["XALL"][:, len(BLOCKS["L2"]) :] += np.arange(300, dtype=np.float32)[:, None]
        original_x0 = day.X["X0"].copy()
        permuted = diagnostic_transform(day, "XALL", "timestamp_permutation")
        signed = diagnostic_transform(day, "XALL", "sign_placebo")
        timed = diagnostic_transform(day, "XALL", "time_placebo")
        np.testing.assert_array_equal(permuted.X["X0"], original_x0)
        np.testing.assert_array_equal(signed.X["X0"], original_x0)
        np.testing.assert_array_equal(timed.X["X0"], original_x0)
        self.assertFalse(np.array_equal(permuted.X["XALL"], day.X["XALL"]))
        self.assertFalse(np.array_equal(signed.X["XALL"], day.X["XALL"]))
        self.assertFalse(np.any(timed.valid["XALL"][:240]))

    def test_future_target_canary_is_isolated_and_invalidates_tail(self) -> None:
        day = synthetic_exp003_day(DAYS[0], rows=120)
        original_width = day.X["XALL"].shape[1]
        canary = inject_future_leak_canary(day)
        self.assertEqual(canary.X["XALL"].shape[1], original_width + 1)
        self.assertEqual(canary.X["X0"].shape[1], day.X["X0"].shape[1])
        self.assertEqual(canary.feature_names["XALL"][-1], "CANARY_ONLY__future_target_return_10s_bps")
        self.assertFalse(np.any(canary.valid["XALL"][-41:]))

    def test_diagnostic_suite_requires_canary_and_rejects_placebo_pass(self) -> None:
        primary = {
            "gate_result": {"pass": True},
            "pools": {"XALL": {"mean_outer_roc_auc": {"long": 0.55, "short": 0.56}}},
        }
        kinds = [
            "DIAGNOSTIC_250MS",
            "STRESS_1000MS",
            "TIMESTAMP_PERMUTATION",
            "SIGN_PLACEBO",
            "TIME_PLACEBO",
            "FUTURE_LEAK_CANARY",
        ]
        diagnostics = []
        for kind in kinds:
            diagnostics.append(
                {
                    "run_kind": kind,
                    "pools": {
                        "XALL": {
                            "mean_outer_roc_auc": {
                                "long": 0.60 if kind == "FUTURE_LEAK_CANARY" else 0.50,
                                "short": 0.56,
                            }
                        }
                    },
                    "diagnostic_counterfactual_gate_result": {"pass": False},
                }
            )
        verdict = evaluate_diagnostic_suite(primary, diagnostics)
        self.assertTrue(verdict["diagnostic_suite_pass"])
        self.assertTrue(verdict["final_pass"])
        diagnostics[2]["diagnostic_counterfactual_gate_result"]["pass"] = True
        self.assertFalse(evaluate_diagnostic_suite(primary, diagnostics)["final_pass"])


if __name__ == "__main__":
    unittest.main()

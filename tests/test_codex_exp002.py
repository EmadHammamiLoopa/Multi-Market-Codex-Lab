from __future__ import annotations

import math
import unittest
from pathlib import Path

import numpy as np

from multimarket.codex_exp002 import (
    BookDay,
    Candidate,
    ExperimentSealError,
    PRIMARY_LATENCY_US,
    QueueEvent,
    assert_allowed_day,
    assert_allowed_path,
    candidate_window_within_day,
    fit_models,
    replay_queue,
    select_threshold,
    simulate_variant,
)


def _book(rows: int = 80) -> BookDay:
    timestamp = np.arange(rows, dtype=np.int64) * 250_000
    bid = np.full(rows, 100.0)
    ask = np.full(rows, 101.0)
    bid_qty = np.full(rows, 1.0)
    ask_qty = np.full(rows, 1.0)
    mid = np.full(rows, 100.5)
    return BookDay(timestamp, bid, ask, bid_qty, ask_qty, mid, np.ones(rows, dtype=bool))


def _candidate(*events: QueueEvent) -> Candidate:
    return Candidate(
        day="2026-01-01",
        symbol="BTCUSDT",
        decision_us=0,
        decision_index=0,
        side=1,
        limit_price=100.0,
        order_size=0.001,
        features=np.zeros(8),
        trade_events=list(events),
    )


class Exp002Tests(unittest.TestCase):
    def test_event_at_or_before_arrival_is_not_observable_fill(self) -> None:
        replay = replay_queue(
            initial_queue=0.0,
            order_size=1.0,
            arrival_us=250_000,
            timeout_request_us=1_000_000,
            response_latency_us=250_000,
            events=[
                QueueEvent(200_000, "trade", 2.0),
                QueueEvent(250_000, "trade", 2.0),
                QueueEvent(300_000, "trade", 1.0),
            ],
        )
        self.assertEqual(replay.first_fill_us, 300_000)
        self.assertEqual(replay.fill_quantity, 1.0)

    def test_risk_averse_queue_ignores_cancellation_credit(self) -> None:
        events = [QueueEvent(300_000, "cancel", 10.0), QueueEvent(400_000, "trade", 1.0)]
        primary = replay_queue(
            initial_queue=5.0,
            order_size=1.0,
            arrival_us=250_000,
            timeout_request_us=1_000_000,
            response_latency_us=250_000,
            events=events,
            cancellation_credit=0.0,
        )
        diagnostic = replay_queue(
            initial_queue=5.0,
            order_size=1.0,
            arrival_us=250_000,
            timeout_request_us=1_000_000,
            response_latency_us=250_000,
            events=events,
            cancellation_credit=0.5,
        )
        self.assertFalse(primary.filled)
        self.assertTrue(diagnostic.filled)

    def test_queue_fill_occurs_only_after_ahead_quantity_is_traded(self) -> None:
        replay = replay_queue(
            initial_queue=5.0,
            order_size=1.0,
            arrival_us=250_000,
            timeout_request_us=1_000_000,
            response_latency_us=250_000,
            events=[QueueEvent(300_000, "trade", 3.0), QueueEvent(400_000, "trade", 3.0)],
        )
        self.assertEqual(replay.first_fill_us, 400_000)
        self.assertEqual(replay.full_fill_us, 400_000)
        self.assertEqual(replay.trade_quantity, 6.0)

    def test_partial_fill_requests_cancel_and_honors_response_latency(self) -> None:
        replay = replay_queue(
            initial_queue=0.0,
            order_size=1.0,
            arrival_us=250_000,
            timeout_request_us=2_000_000,
            response_latency_us=250_000,
            events=[
                QueueEvent(500_000, "trade", 0.25),
                QueueEvent(600_000, "trade", 0.25),
                QueueEvent(800_000, "trade", 1.0),
            ],
        )
        self.assertEqual(replay.fill_quantity, 0.5)
        self.assertEqual(replay.first_fill_us, 500_000)
        self.assertEqual(replay.effective_cancel_us, 750_000)
        self.assertIsNone(replay.full_fill_us)

    def test_markout_clock_starts_at_simulated_fill(self) -> None:
        book = _book()
        book.bid_qty[:] = 0.0
        book.mid[4] = 110.0
        book.mid[6] = 102.0
        result = simulate_variant(
            _candidate(QueueEvent(500_000, "trade", 0.001)),
            book,
            np.empty(0, dtype=np.int64),
            latency_us=PRIMARY_LATENCY_US,
            cancellation_credit=0.0,
        )
        self.assertEqual(result["status"], "full_fill")
        self.assertEqual(result["first_fill_us"], 500_000)
        self.assertAlmostEqual(result["markout_1s_bps"], 200.0)

    def test_price_touch_or_cross_without_trade_never_fills(self) -> None:
        book = _book()
        book.ask[2:] = 99.0
        result = simulate_variant(
            _candidate(),
            book,
            np.empty(0, dtype=np.int64),
            latency_us=PRIMARY_LATENCY_US,
            cancellation_credit=0.0,
        )
        self.assertEqual(result["status"], "timeout_cancel")
        self.assertEqual(result["fill_quantity"], 0.0)

    def test_snapshot_reset_cancels_unobservable_queue(self) -> None:
        result = simulate_variant(
            _candidate(QueueEvent(500_000, "trade", 1.0)),
            _book(),
            np.asarray([400_000], dtype=np.int64),
            latency_us=PRIMARY_LATENCY_US,
            cancellation_credit=0.0,
        )
        self.assertEqual(result["status"], "snapshot_cancel")
        self.assertEqual(result["fill_quantity"], 0.0)

    def test_latency_changes_arrival_and_excludes_earlier_trade(self) -> None:
        book = _book()
        book.bid_qty[:] = 0.0
        candidate = _candidate(QueueEvent(400_000, "trade", 0.001))
        fast = simulate_variant(
            candidate,
            book,
            np.empty(0, dtype=np.int64),
            latency_us=250_000,
            cancellation_credit=0.0,
        )
        slow = simulate_variant(
            candidate,
            book,
            np.empty(0, dtype=np.int64),
            latency_us=500_000,
            cancellation_credit=0.0,
        )
        self.assertEqual(fast["status"], "full_fill")
        self.assertEqual(slow["status"], "timeout_cancel")

    def test_day_boundary_purge_uses_slowest_complete_execution_span(self) -> None:
        day_start = 1_000_000_000_000
        self.assertTrue(candidate_window_within_day(day_start + 1_000_000, day_start))
        self.assertFalse(candidate_window_within_day(day_start + 86_390_000_000, day_start))

    def test_sealed_period_is_rejected(self) -> None:
        with self.assertRaises(ExperimentSealError):
            assert_allowed_day("2026-08-01")
        with self.assertRaises(ExperimentSealError):
            assert_allowed_path(Path("/home/emadh/Multi-Market/data/2026-08-01.csv.gz"))

    def test_depth_ratio_is_reported_for_resting_order(self) -> None:
        result = simulate_variant(
            _candidate(QueueEvent(500_000, "trade", 1.001)),
            _book(),
            np.empty(0, dtype=np.int64),
            latency_us=PRIMARY_LATENCY_US,
            cancellation_credit=0.0,
        )
        self.assertTrue(math.isclose(result["depth_ratio"], 0.001))

    def test_low_capacity_models_and_inner_cutoff_smoke(self) -> None:
        rng = np.random.default_rng(20260825)
        candidates: list[Candidate] = []
        for index in range(600):
            candidate = _candidate()
            candidate.features = rng.normal(size=8)
            filled = index % 3 == 0
            gross = 10.0 + 0.1 * candidate.features[2] if filled else None
            candidate.variants["risk250"] = {
                "fill_quantity": 0.001 if filled else 0.0,
                "gross_bps": gross,
                "primary_net_bps": gross - 6.0 if filled else None,
                "primary_net_usd": 0.00004 if filled else 0.0,
            }
            candidates.append(candidate)
        models = fit_models(candidates)
        probability, gross, expected = models.predict(candidates)
        threshold, audit = select_threshold(candidates, expected)
        self.assertEqual(len(probability), 600)
        self.assertTrue(np.all(np.isfinite(gross)))
        self.assertIn(threshold, (0.0, 0.10, 0.25))
        self.assertEqual(len(audit), 3)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import math

import pytest

from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1
from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b
from multimarket import dev045_d6r26a_p2_r10_bounded_feature_accumulator_freeze as r10


def _book(local_ns: int, i: int) -> r8b.BookObservation:
    ask0 = 1002 if i % 7 == 0 else 1001
    bid_qty = 5.0 + (i % 5) * 0.25
    ask_qty = 6.0 + (i % 3) * 0.20
    bids = tuple(r8b.BookLevel(1000 - j, bid_qty + j * 0.1) for j in range(5))
    asks = tuple(r8b.BookLevel(ask0 + j, ask_qty + j * 0.1) for j in range(5))
    return r8b.BookObservation(
        local_ns=local_ns,
        exchange_ns=max(0, local_ns - 1_000_000),
        bids=bids,
        asks=asks,
    )


def _history():
    books = tuple(_book(i * 100_000_000, i) for i in range(311))
    flows = []
    for i in range(1, 156):
        ts = i * 200_000_000
        flows.append(
            r8b.FlowObservation(
                ts,
                max(0, ts - 1_000_000),
                "TRADE",
                "BUY" if i % 2 else "SELL",
                0.1 + (i % 4) * 0.01,
            )
        )
        if i % 3 == 0:
            flows.append(r8b.FlowObservation(ts, max(0, ts - 900_000), "ADD", "BID", 0.05))
        if i % 5 == 0:
            flows.append(r8b.FlowObservation(ts, max(0, ts - 800_000), "CANCEL", "ASK", 0.04))
    return books, tuple(flows)


def test_r10_contract_stays_preexecution():
    r10.validate_r10_contract()
    assert r10.BOUNDED_ROLLING_FEATURE_ACCUMULATOR_FROZEN is True
    assert r10.MAX_FEATURE_WINDOW_NS == 30_000_000_000
    assert r10.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r10.SIMULATOR_IMPORT_AUTHORIZED is False
    assert r10.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r10.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r10.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r10.MODEL_FIT_AUTHORIZED is False
    assert r10.PNL_AUTHORIZED is False


def test_bounded_accumulator_matches_r8b_batch_reference():
    books, flows = _history()
    decision = 31_000_000_000
    candidate = p1.CandidateSpec(
        side="BID",
        distance_ticks=1,
        decision_local_ns=decision,
        best_bid_tick=books[-1].best_bid.price_tick,
        best_ask_tick=books[-1].best_ask.price_tick,
    )

    reference = r8b.compute_features(candidate=candidate, books=books, flows=flows)

    acc = r10.RollingFeatureAccumulator()
    stream = [(b.local_ns, 0, b) for b in books] + [(f.local_ns, 1, f) for f in flows]
    for _, kind, item in sorted(stream, key=lambda x: (x[0], x[1])):
        if kind == 0:
            acc.ingest_book(item)
        else:
            acc.ingest_flow(item)

    observed = acc.compute(candidate=candidate)
    assert tuple(observed.values) == tuple(reference.values)
    for name in reference.values:
        assert math.isclose(
            observed.values[name],
            reference.values[name],
            rel_tol=1e-12,
            abs_tol=1e-12,
        ), name
    assert observed.observable_local_ns == reference.observable_local_ns
    assert observed.support == reference.support

    counts = acc.bounded_counts()
    assert counts["recent_books"] <= 12
    assert counts["ofi_5s"] <= 51
    assert counts["vol_30s"] <= 301
    assert counts["trade_5s"] <= 26


def test_left_open_window_drops_exact_cutoff():
    acc = r10._RollingSum(1_000_000_000)
    acc.add(1_000_000_000, 2.0)
    acc.add(1_000_000_001, 3.0)
    assert acc.advance(2_000_000_000) == 3.0


def test_future_observation_ingested_fails_closed():
    acc = r10.RollingFeatureAccumulator()
    for i in range(302):
        acc.ingest_book(_book(i * 100_000_000, i))
    candidate = p1.CandidateSpec(
        side="ASK",
        distance_ticks=0,
        decision_local_ns=30_000_000_000,
        best_bid_tick=1000,
        best_ask_tick=1001,
    )
    with pytest.raises(r10.BoundedFeatureAccumulatorError, match="future_observation_ingested"):
        acc.compute(candidate=candidate)


def test_decision_regression_fails_closed():
    books, flows = _history()
    acc = r10.RollingFeatureAccumulator()
    stream = [(b.local_ns, 0, b) for b in books if b.local_ns <= 31_000_000_000] + [
        (f.local_ns, 1, f) for f in flows if f.local_ns <= 31_000_000_000
    ]
    for _, kind, item in sorted(stream, key=lambda x: (x[0], x[1])):
        (acc.ingest_book if kind == 0 else acc.ingest_flow)(item)
    c1 = p1.CandidateSpec("BID", 0, 31_000_000_000, 1000, books[-1].best_ask.price_tick)
    acc.compute(candidate=c1)
    c0 = p1.CandidateSpec("BID", 0, 30_000_000_000, 1000, 1001)
    with pytest.raises(r10.BoundedFeatureAccumulatorError, match="decision_regression"):
        acc.compute(candidate=c0)

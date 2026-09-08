from __future__ import annotations

import math

import numpy as np
import pytest

from multimarket import (
    dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0,
)
from multimarket import (
    dev045_d6r26a_p1_synthetic_candidate_labeler as p1,
)
from multimarket import (
    dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b,
)
from multimarket import (
    dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9,
)
from multimarket import (
    dev045_d6r26a_p2_r10_bounded_feature_accumulator_freeze as r10,
)
from multimarket import (
    dev045_d6r26a_p2_r13_streaming_raw_decoder_preexecution as r13,
)


EVENT_DTYPE = np.dtype(
    [
        ("ev", "<u8"),
        ("exch_ts", "<i8"),
        ("local_ts", "<i8"),
        ("px", "<f8"),
        ("qty", "<f8"),
    ]
)


def _fixture() -> np.ndarray:
    rows = []

    snapshot = r9.LOCAL_EVENT | r9.DEPTH_SNAPSHOT_EVENT

    for level, qty in enumerate((5.0, 4.0, 3.0, 2.0, 1.0)):
        rows.append(
            (
                snapshot | r9.BUY_EVENT,
                900_000_000,
                1_000_000_000,
                100.0 - 0.1 * level,
                qty,
            )
        )

    for level, qty in enumerate((6.0, 5.0, 4.0, 3.0, 2.0)):
        rows.append(
            (
                snapshot | r9.SELL_EVENT,
                900_000_000,
                1_000_000_000,
                100.1 + 0.1 * level,
                qty,
            )
        )

    ask_depth = (
        r9.LOCAL_EVENT
        | r9.DEPTH_EVENT
        | r9.SELL_EVENT
    )

    bid_depth = (
        r9.LOCAL_EVENT
        | r9.DEPTH_EVENT
        | r9.BUY_EVENT
    )

    for second in range(2, 33):
        local = second * 1_000_000_000

        rows.append(
            (
                ask_depth,
                local - 10_000_000,
                local,
                100.1,
                6.0 + (0.1 if second % 2 else 0.0),
            )
        )

        if second % 3 == 0:
            rows.append(
                (
                    bid_depth,
                    local - 9_000_000,
                    local,
                    100.0,
                    5.0 + 0.1 * (second % 4),
                )
            )

    rows.append(
        (
            r9.LOCAL_EVENT
            | r9.TRADE_EVENT
            | r9.BUY_EVENT,
            30_490_000_000,
            30_500_000_000,
            100.1,
            0.125,
        )
    )

    rows.append(
        (
            r9.LOCAL_EVENT
            | r9.TRADE_EVENT
            | r9.SELL_EVENT,
            30_690_000_000,
            30_700_000_000,
            100.0,
            0.075,
        )
    )

    rows.sort(key=lambda x: (x[2], x[1]))

    out = np.zeros(len(rows), dtype=EVENT_DTYPE)

    for i, row in enumerate(rows):
        out[i]["ev"] = row[0]
        out[i]["exch_ts"] = row[1]
        out[i]["local_ts"] = row[2]
        out[i]["px"] = row[3]
        out[i]["qty"] = row[4]

    return out


def test_r13_contract_is_strictly_preexecution():
    r13.validate_r13_contract()

    assert r13.PREEXECUTION_ONLY is True
    assert r13.R9_EXACT_DECODER_SEMANTICS_BOUND is True
    assert r13.R10_BOUNDED_ACCUMULATOR_BOUND is True
    assert r13.DECISION_AFTER_LOCAL_GROUP_FLUSH_REQUIRED is True

    assert r13.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r13.SIMULATOR_IMPORT_AUTHORIZED is False
    assert r13.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r13.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r13.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r13.MODEL_FIT_AUTHORIZED is False
    assert r13.PNL_AUTHORIZED is False


def test_streaming_decoder_is_exact_r9_batch_parity():
    data = _fixture()

    expected = r9.decode_local_history(data)
    observed = r13.decode_local_streaming(data)

    assert observed == expected


def test_streaming_group_output_drives_r10_with_batch_feature_parity():
    data = _fixture()

    batch = r9.decode_local_history(data)

    decision = 31_000_000_000
    current = r8b.book_asof(
        books=batch.books,
        target_local_ns=decision,
    )

    candidate = p1.CandidateSpec(
        side="BID",
        distance_ticks=0,
        decision_local_ns=decision,
        best_bid_tick=int(current.best_bid.price_tick),
        best_ask_tick=int(current.best_ask.price_tick),
    )

    expected = r8b.compute_features(
        candidate=candidate,
        books=batch.books,
        flows=batch.flows,
    )

    accumulator = r10.RollingFeatureAccumulator()

    for emission in r13.iter_local_groups(data):
        if emission.local_ns > decision:
            break

        r13.feed_group_to_accumulator(
            accumulator=accumulator,
            emission=emission,
        )

    observed = accumulator.compute(
        candidate=candidate,
    )

    assert observed.support == expected.support
    assert tuple(observed.values) == tuple(expected.values)

    for name in expected.values:
        assert math.isclose(
            float(observed.values[name]),
            float(expected.values[name]),
            rel_tol=0.0,
            abs_tol=1e-12,
        )

    assert observed.observable_local_ns == (
        expected.observable_local_ns
    )


def test_decision_timestamp_group_is_complete_before_emission():
    data = _fixture()

    groups = list(r13.iter_local_groups(data))

    times = [group.local_ns for group in groups]
    assert times == sorted(times)
    assert len(times) == len(set(times))

    group_31 = next(
        group
        for group in groups
        if group.local_ns == 31_000_000_000
    )

    assert len(group_31.books) == 1
    assert group_31.books[0].local_ns == 31_000_000_000


def test_streaming_decoder_fails_closed_on_timestamp_regression():
    data = _fixture().copy()

    decoder = r13.LocalStreamingDecoder()

    first = data[0].copy()
    decoder.feed(first)

    bad = first.copy()
    bad["local_ts"] = 500_000_000
    bad["exch_ts"] = 400_000_000

    with pytest.raises(
        r13.StreamingRawDecoderError,
        match="local_timestamp_regression",
    ):
        decoder.feed(bad)


def test_streaming_decoder_fails_closed_on_unknown_event():
    data = _fixture()

    bad = data[0].copy()
    bad["ev"] = r9.LOCAL_EVENT | 99

    decoder = r13.LocalStreamingDecoder()

    with pytest.raises(
        r13.StreamingRawDecoderError,
        match="unknown_event_kind:99",
    ):
        decoder.feed(bad)

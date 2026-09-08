from __future__ import annotations

import numpy as np
import pytest

from multimarket import (
    dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9,
)
from multimarket import (
    dev045_d6r26a_p2_r13_streaming_raw_decoder_preexecution as r13,
)
from multimarket import (
    dev045_d6r26a_p2_r13a_dual_stream_eof_memory_amendment as r13a,
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


def _row(ev, exch, local, px, qty):
    return (
        int(ev),
        int(exch),
        int(local),
        float(px),
        float(qty),
    )


def _dual_fixture() -> np.ndarray:
    both = r9.EXCH_EVENT | r9.LOCAL_EVENT

    rows = [
        _row(
            both | r9.DEPTH_SNAPSHOT_EVENT | r9.BUY_EVENT,
            900_000_000,
            1_000_000_000,
            100.0,
            5.0,
        ),
        _row(
            both | r9.DEPTH_SNAPSHOT_EVENT | r9.SELL_EVENT,
            900_000_000,
            1_000_000_000,
            100.1,
            6.0,
        ),
        # Same timestamp depth updates must coalesce in source order.
        _row(
            both | r9.DEPTH_EVENT | r9.BUY_EVENT,
            1_900_000_000,
            2_000_000_000,
            100.0,
            5.5,
        ),
        _row(
            both | r9.DEPTH_EVENT | r9.BUY_EVENT,
            1_900_000_000,
            2_000_000_000,
            100.0,
            5.75,
        ),
        _row(
            both | r9.TRADE_EVENT | r9.BUY_EVENT,
            1_950_000_000,
            2_050_000_000,
            100.1,
            0.25,
        ),
        _row(
            both | r9.DEPTH_EVENT | r9.SELL_EVENT,
            2_900_000_000,
            3_000_000_000,
            100.1,
            6.5,
        ),
    ]

    return np.array(rows, dtype=EVENT_DTYPE)


def test_r13a_contract_freezes_previous_failure_guards():
    r13a.validate_r13a_contract()

    assert r13a.NATURAL_END_OF_SOURCE_IS_VALID_TERMINAL is True
    assert r13a.FINAL_TIMESTAMP_GROUP_FLUSH_REQUIRED is True
    assert r13a.FIXED_EVENT_TARGET is None
    assert r13a.FIXED_WAKEUP_TARGET is None

    assert r13a.TOTAL_RSS_ABORT_THRESHOLD_BYTES is None
    assert r13a.TOTAL_RSS_IS_BOUNDEDNESS_GATE is False

    assert (
        r13a.INTERNAL_STATE_BOUND_TO_ACTIVE_BOOK_AND_CURRENT_GROUP
        is True
    )
    assert (
        r13a.FULL_HISTORY_MATERIALIZATION_IN_REAL_PATH_FORBIDDEN
        is True
    )

    assert r13a.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r13a.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r13a.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r13a.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r13a.MODEL_FIT_AUTHORIZED is False
    assert r13a.PNL_AUTHORIZED is False


def test_exchange_streaming_is_exact_r9_batch_parity():
    data = _dual_fixture()

    expected = r9.decode_exchange_midpoints(data)
    observed = r13a.decode_exchange_streaming(data)

    assert observed == expected


def test_dual_stream_local_side_remains_exact_r13_r9_parity():
    data = _dual_fixture()

    expected = r9.decode_local_history(data)

    books = []
    flows = []

    decoder = r13a.DualStreamingDecoder()

    for row in data:
        emitted = decoder.feed(row)

        for group in emitted.local_groups:
            books.extend(group.books)
            flows.extend(group.flows)

    final = decoder.finish()

    for group in final.local_groups:
        books.extend(group.books)
        flows.extend(group.flows)

    observed = r9.DecodedHistory(
        books=tuple(books),
        flows=tuple(flows),
    )

    assert observed == expected


def test_natural_eof_flushes_final_local_and_exchange_groups():
    both = r9.EXCH_EVENT | r9.LOCAL_EVENT

    data = np.array(
        [
            _row(
                both | r9.DEPTH_SNAPSHOT_EVENT | r9.BUY_EVENT,
                900_000_000,
                1_000_000_000,
                100.0,
                5.0,
            ),
            _row(
                both | r9.DEPTH_SNAPSHOT_EVENT | r9.SELL_EVENT,
                900_000_000,
                1_000_000_000,
                100.1,
                6.0,
            ),
        ],
        dtype=EVENT_DTYPE,
    )

    decoder = r13a.DualStreamingDecoder()

    for row in data:
        emitted = decoder.feed(row)
        assert emitted.local_groups == ()
        assert emitted.exchange_midpoints == ()

    # Natural iterator/source exhaustion is sufficient. No event quota,
    # wakeup quota, reference EOD count, or synthetic stop target is required.
    final = decoder.finish()

    assert len(final.local_groups) == 1
    assert len(final.local_groups[0].books) == 1
    assert final.local_groups[0].local_ns == 1_000_000_000

    assert len(final.exchange_midpoints) == 1
    assert final.exchange_midpoints[0].exchange_ns == 900_000_000


def test_exchange_timestamp_regression_fails_closed():
    both = r9.EXCH_EVENT | r9.LOCAL_EVENT

    good = np.array(
        [
            _row(
                both | r9.DEPTH_SNAPSHOT_EVENT | r9.BUY_EVENT,
                1_000_000_000,
                1_100_000_000,
                100.0,
                5.0,
            )
        ],
        dtype=EVENT_DTYPE,
    )[0]

    bad = good.copy()
    bad["exch_ts"] = 900_000_000
    bad["local_ts"] = 1_200_000_000

    decoder = r13a.ExchangeStreamingDecoder()
    decoder.feed(good)

    with pytest.raises(
        r13a.DualStreamingDecoderError,
        match="exchange_timestamp_regression",
    ):
        decoder.feed(bad)


def test_long_stream_does_not_accumulate_output_history():
    both = r9.EXCH_EVENT | r9.LOCAL_EVENT

    n_updates = 20_000
    data = np.zeros(n_updates + 2, dtype=EVENT_DTYPE)

    data[0] = _row(
        both | r9.DEPTH_SNAPSHOT_EVENT | r9.BUY_EVENT,
        900_000_000,
        1_000_000_000,
        100.0,
        5.0,
    )
    data[1] = _row(
        both | r9.DEPTH_SNAPSHOT_EVENT | r9.SELL_EVENT,
        900_000_000,
        1_000_000_000,
        100.1,
        6.0,
    )

    for i in range(n_updates):
        exch = 1_000_000_000 + i * 1_000_000
        local = exch + 100_000_000
        qty = 5.0 if i % 2 == 0 else 5.1

        data[i + 2] = _row(
            both | r9.DEPTH_EVENT | r9.BUY_EVENT,
            exch,
            local,
            100.0,
            qty,
        )

    decoder = r13a.DualStreamingDecoder()

    max_local_group_flows = 0
    max_local_levels = 0
    max_exchange_levels = 0

    for row in data:
        decoder.feed(row)

        max_local_group_flows = max(
            max_local_group_flows,
            len(decoder.local._group_flows),
        )
        max_local_levels = max(
            max_local_levels,
            len(decoder.local._state.bids)
            + len(decoder.local._state.asks),
        )
        max_exchange_levels = max(
            max_exchange_levels,
            decoder.exchange.active_level_count,
        )

    decoder.finish()

    # We repeatedly update the same two active BBO levels. State therefore
    # stays tied to the live book/current group, not to 20k elapsed outputs.
    assert max_local_levels <= 2
    assert max_exchange_levels <= 2
    assert max_local_group_flows <= 1

    assert not hasattr(decoder.exchange, "_out")
    assert not hasattr(decoder.exchange, "_midpoints")


def test_unknown_event_kind_still_fails_closed():
    bad = np.array(
        [
            _row(
                r9.EXCH_EVENT | r9.LOCAL_EVENT | 99,
                1_000_000_000,
                1_100_000_000,
                100.0,
                1.0,
            )
        ],
        dtype=EVENT_DTYPE,
    )[0]

    decoder = r13a.ExchangeStreamingDecoder()

    with pytest.raises(
        r13a.DualStreamingDecoderError,
        match="unknown_event_kind:99",
    ):
        decoder.feed(bad)


def test_parent_r13_final_group_behavior_remains_available():
    data = _dual_fixture()

    # R13 remains immutable semantic parent; amendment does not replace it.
    expected = r9.decode_local_history(data)
    observed = r13.decode_local_streaming(data)

    assert observed == expected

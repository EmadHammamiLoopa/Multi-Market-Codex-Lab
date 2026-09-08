from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9

EVENT_DTYPE = np.dtype(
    [
        ("ev", "u8"),
        ("exch_ts", "i8"),
        ("local_ts", "i8"),
        ("px", "f8"),
        ("qty", "f8"),
        ("order_id", "u8"),
        ("ival", "i8"),
        ("fval", "f8"),
    ],
    align=True,
)


def _row(ev, exch, local, px, qty):
    return (int(ev), int(exch), int(local), float(px), float(qty), 0, 0, 0.0)


def _snapshot_rows(exch=1_000_000_000, local=1_010_000_000):
    flags = r9.EXCH_EVENT | r9.LOCAL_EVENT | r9.DEPTH_SNAPSHOT_EVENT
    rows = []
    for i, qty in enumerate((5.0, 4.0, 3.0, 2.0, 1.0)):
        rows.append(_row(flags | r9.BUY_EVENT, exch, local, 100.0 - 0.1 * i, qty))
    for i, qty in enumerate((6.0, 5.0, 4.0, 3.0, 2.0)):
        rows.append(_row(flags | r9.SELL_EVENT, exch, local, 100.1 + 0.1 * i, qty))
    return rows


def test_r9_contract_and_definition_hash():
    r9.validate_r9_contract()
    assert r9.DECODER_DEFINITION_SHA256 == "50ddc5f01872cb6155d7ea3f8adc8e040a95407249657e2c891859d4921fdd58"
    assert r9.decoder_definition_sha256() == r9.DECODER_DEFINITION_SHA256
    assert r9.RAW_EVENT_DECODER_FROZEN is True
    assert r9.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r9.SIMULATOR_IMPORT_AUTHORIZED is False
    assert r9.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r9.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r9.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r9.PNL_AUTHORIZED is False


def test_snapshot_depth_trade_and_bbo_parity():
    rows = _snapshot_rows()
    depth_flags = r9.EXCH_EVENT | r9.LOCAL_EVENT | r9.DEPTH_EVENT | r9.BUY_EVENT
    trade_flags = r9.EXCH_EVENT | r9.LOCAL_EVENT | r9.TRADE_EVENT | r9.BUY_EVENT
    bbo_flags = r9.EXCH_EVENT | r9.LOCAL_EVENT | r9.DEPTH_BBO_EVENT | r9.BUY_EVENT
    rows += [
        _row(depth_flags, 2_000_000_000, 2_010_000_000, 100.0, 7.0),
        _row(trade_flags, 2_000_000_100, 2_010_000_000, 100.1, 0.25),
        # Must be ignored by exact L2 Local parity.
        _row(bbo_flags, 2_000_000_200, 2_010_000_000, 101.0, 999.0),
    ]
    data = np.array(rows, dtype=EVENT_DTYPE)
    decoded = r9.decode_local_history(data)
    assert len(decoded.books) == 2
    assert decoded.books[0].best_bid.price_tick == 1000
    assert decoded.books[1].best_bid.price_tick == 1000
    assert decoded.books[1].best_bid.qty == 7.0
    assert decoded.books[1].best_ask.price_tick == 1001
    assert len(decoded.flows) == 2
    assert decoded.flows[0].kind == "ADD"
    assert decoded.flows[0].side == "BID"
    assert decoded.flows[0].qty == 2.0
    assert decoded.flows[1].kind == "TRADE"
    assert decoded.flows[1].side == "BUY"
    assert decoded.flows[1].qty == 0.25


def test_depth_zero_removes_level_and_emits_cancel():
    rows = _snapshot_rows()
    flags = r9.EXCH_EVENT | r9.LOCAL_EVENT | r9.DEPTH_EVENT | r9.BUY_EVENT
    rows.append(_row(flags, 2_000_000_000, 2_010_000_000, 100.0, 0.0))
    decoded = r9.decode_local_history(np.array(rows, dtype=EVENT_DTYPE))
    assert decoded.books[-1].best_bid.price_tick == 999
    assert decoded.flows[-1].kind == "CANCEL"
    assert decoded.flows[-1].side == "BID"
    assert decoded.flows[-1].qty == 5.0


def test_clear_and_snapshot_rebuild_emit_no_false_flow():
    rows = _snapshot_rows()
    clear = r9.EXCH_EVENT | r9.LOCAL_EVENT | r9.DEPTH_CLEAR_EVENT | r9.SELL_EVENT
    snap = r9.EXCH_EVENT | r9.LOCAL_EVENT | r9.DEPTH_SNAPSHOT_EVENT | r9.SELL_EVENT
    t_ex = 2_000_000_000
    t_local = 2_010_000_000
    rows.append(_row(clear, t_ex, t_local, float("inf"), 0.0))
    for i, qty in enumerate((8.0, 7.0, 6.0, 5.0, 4.0)):
        rows.append(_row(snap, t_ex + i + 1, t_local, 100.1 + 0.1 * i, qty))
    decoded = r9.decode_local_history(np.array(rows, dtype=EVENT_DTYPE))
    assert len(decoded.books) == 2
    assert decoded.books[-1].best_ask.qty == 8.0
    assert decoded.flows == ()


def test_exchange_midpoint_series_is_exchange_time_not_local_time():
    rows = _snapshot_rows(exch=1_000_000_000, local=1_500_000_000)
    flags = r9.EXCH_EVENT | r9.LOCAL_EVENT | r9.DEPTH_EVENT | r9.BUY_EVENT
    rows.append(_row(flags, 2_000_000_000, 2_500_000_000, 100.0, 8.0))
    mids = r9.decode_exchange_midpoints(np.array(rows, dtype=EVENT_DTYPE))
    assert len(mids) == 2
    assert mids[0].exchange_ns == 1_000_000_000
    assert mids[1].exchange_ns == 2_000_000_000
    assert mids[0].best_bid_tick == 1000
    assert mids[0].best_ask_tick == 1001


def test_unknown_event_kind_fails_closed():
    rows = _snapshot_rows()
    unknown = r9.EXCH_EVENT | r9.LOCAL_EVENT | r9.BUY_EVENT | 99
    rows.append(_row(unknown, 2_000_000_000, 2_010_000_000, 100.0, 1.0))
    data = np.array(rows, dtype=EVENT_DTYPE)
    with pytest.raises(r9.RawEventDecoderError, match="unknown_event_kind:99"):
        r9.decode_local_history(data)


def test_local_timestamp_regression_fails_closed():
    rows = _snapshot_rows(exch=2_000_000_000, local=2_010_000_000)
    flags = r9.EXCH_EVENT | r9.LOCAL_EVENT | r9.TRADE_EVENT | r9.SELL_EVENT
    rows.append(_row(flags, 1_500_000_000, 1_510_000_000, 100.0, 1.0))
    with pytest.raises(r9.RawEventDecoderError, match="local_timestamp_regression"):
        r9.decode_local_history(np.array(rows, dtype=EVENT_DTYPE))

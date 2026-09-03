from __future__ import annotations

import gzip
from pathlib import Path

import numpy as np
import pytest

from multimarket import dev045_m1_parity as p


def test_event_fixture_validates():
    data=p.make_risk_averse_partial_fixture()
    assert p.validate_events(data) is True
    assert np.all(data["local_ts"]>=data["exch_ts"])


def test_risk_adverse_touch_cancel_trade_partial_full():
    import hftbacktest as h

    r=p.run_partial_sequence(queue_model="risk_adverse")

    accepted=r["accepted"]
    assert accepted.status==h.NEW
    assert accepted.exec_qty==pytest.approx(0.0)
    assert accepted.leaves_qty==pytest.approx(p.ORDER_QTY)

    after_first=r["after_cancel_and_trade5"]
    # Cancellation-only decrease cannot move Q0 ahead; first 5-unit trade
    # consumes only half of original 10-unit queue ahead.
    assert after_first.status==h.NEW
    assert after_first.exec_qty==pytest.approx(0.0)
    assert after_first.leaves_qty==pytest.approx(p.ORDER_QTY)

    partial=r["after_trade6"]
    assert partial.status==h.PARTIALLY_FILLED
    assert partial.exec_qty==pytest.approx(1.0)
    assert partial.leaves_qty==pytest.approx(1.0)
    full=r["after_trade1"]
    assert full.status==h.FILLED
    assert full.exec_qty==pytest.approx(1.0)
    assert full.leaves_qty==pytest.approx(0.0)
    assert r["position"]==pytest.approx(2.0)
    assert r["fee"]==pytest.approx(0.0)




def test_passive_fill_uses_maker_fee_hook():
    r=p.run_maker_fee_probe(maker_fee=0.001,taker_fee=0.0)
    assert r["position"]==pytest.approx(p.ORDER_QTY)
    # A positive nonzero fee with taker fee fixed to zero proves that the
    # passive fill was classified internally under the maker fee schedule.
    assert r["fee"]>0.0


def test_log_prob_is_deterministic():
    a=p.run_partial_sequence(queue_model="log_prob")
    b=p.run_partial_sequence(queue_model="log_prob")
    assert a==b


def test_no_partial_bound_is_callable_and_deterministic():
    a=p.run_no_partial_sequence()
    b=p.run_no_partial_sequence()
    assert a==b


def test_primary_latency_constants_frozen():
    assert p.DIAGNOSTIC_LATENCY_NS==100_000_000
    assert p.PRIMARY_LATENCY_NS==250_000_000
    assert p.STRESS_LATENCY_NS==500_000_000


def test_markout_sign_convention():
    buy_good=p.signed_markout_bps(side=1,fill_price=100.0,reference_mid=101.0)
    buy_bad=p.signed_markout_bps(side=1,fill_price=100.0,reference_mid=99.0)
    sell_good=p.signed_markout_bps(side=-1,fill_price=100.0,reference_mid=99.0)
    assert buy_good>0
    assert buy_bad<0
    assert sell_good>0


def _write_gz(path:Path,rows):
    with gzip.open(path,"wt",encoding="utf-8",newline="") as h:
        h.write("\n".join(rows)+"\n")


def test_official_tardis_converter_trades_before_depth(tmp_path):
    from hftbacktest.data.utils.tardis import convert
    from hftbacktest.data.validation import validate_event_order
    import hftbacktest as h

    trades=tmp_path/"trades.csv.gz"
    depth=tmp_path/"depth.csv.gz"

    _write_gz(trades,[
        "exchange,symbol,timestamp,local_timestamp,id,side,price,amount",
        "binance-futures,BTCUSDT,1000000,1010000,1,sell,100.0,1.0",
    ])
    _write_gz(depth,[
        "exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount",
        "binance-futures,BTCUSDT,900000,910000,true,bid,100.0,10.0",
        "binance-futures,BTCUSDT,900000,910000,true,ask,100.1,8.0",
        "binance-futures,BTCUSDT,1000000,1020000,false,bid,100.0,9.0",
    ])

    data=convert(
        [str(trades),str(depth)],
        buffer_size=100,
        ss_buffer_size=100,
        base_latency=0,
        snapshot_mode="process",
    )

    assert data.dtype==h.event_dtype
    assert len(data)>=3
    assert np.all(data["local_ts"]>=data["exch_ts"])
    validate_event_order(data)

    base=(data["ev"] & np.uint64(0xff))
    assert np.any(base==h.TRADE_EVENT)
    assert np.any(base==h.DEPTH_SNAPSHOT_EVENT)

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

PRIMARY_LATENCY_NS=250_000_000
DIAGNOSTIC_LATENCY_NS=100_000_000
STRESS_LATENCY_NS=500_000_000
TICK_SIZE=0.1
LOT_SIZE=0.001
ORDER_PRICE=100.0
ORDER_QTY=2.0
QUEUE_AHEAD_QTY=10.0

class M1ParityError(RuntimeError):
    pass

@dataclass(frozen=True)
class OrderSnapshot:
    status:int
    exec_qty:float
    leaves_qty:float
    exch_timestamp:int
    local_timestamp:int

def _imports():
    import numpy as np
    import hftbacktest as h
    return np,h

def event_dtype():
    np,h=_imports()
    return h.event_dtype

def _ev(*,base:int,side:int):
    _,h=_imports()
    return int(base|h.EXCH_EVENT|h.LOCAL_EVENT|side)

def make_initial_snapshot():
    np,h=_imports()
    a=np.zeros(2,dtype=h.event_dtype)
    # Snapshot is earlier than all replay events.  Local timestamp is strictly
    # later than exchange timestamp to preserve positive feed latency.
    a[0]["ev"]=_ev(base=h.DEPTH_SNAPSHOT_EVENT,side=h.BUY_EVENT)
    a[0]["exch_ts"]=100_000_000
    a[0]["local_ts"]=110_000_000
    a[0]["px"]=ORDER_PRICE
    a[0]["qty"]=QUEUE_AHEAD_QTY

    a[1]["ev"]=_ev(base=h.DEPTH_SNAPSHOT_EVENT,side=h.SELL_EVENT)
    a[1]["exch_ts"]=100_000_000
    a[1]["local_ts"]=110_000_000
    a[1]["px"]=ORDER_PRICE+0.1
    a[1]["qty"]=8.0
    return a

def _row(a,i,*,base,side,exch_ns,local_ns,px,qty):
    _,h=_imports()
    a[i]["ev"]=_ev(base=base,side=side)
    a[i]["exch_ts"]=int(exch_ns)
    a[i]["local_ts"]=int(local_ns)
    a[i]["px"]=float(px)
    a[i]["qty"]=float(qty)

def make_risk_averse_partial_fixture():
    np,h=_imports()
    a=np.zeros(7,dtype=h.event_dtype)

    # Local clock becomes active at ~1s.  This unrelated ask update does not
    # touch or consume the bid queue.
    _row(a,0,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=1_000_000_000,local_ns=1_010_000_000,
         px=ORDER_PRICE+0.1,qty=8.0)

    # Cancellation/depletion-only bid reduction.  Q0 Risk-Adverse must not
    # advance our queue position from this book-size decrease.
    _row(a,1,base=h.DEPTH_EVENT,side=h.BUY_EVENT,
         exch_ns=1_500_000_000,local_ns=1_510_000_000,
         px=ORDER_PRICE,qty=5.0)

    # First sell trade at our price: consumes 5 of the original 10 ahead.
    _row(a,2,base=h.TRADE_EVENT,side=h.SELL_EVENT,
         exch_ns=2_000_000_000,local_ns=2_010_000_000,
         px=ORDER_PRICE,qty=5.0)

    # Second sell trade: after remaining queue-ahead is consumed, 1 unit is
    # available to our 2-unit order -> PARTIAL under PartialFillExchange.
    _row(a,3,base=h.TRADE_EVENT,side=h.SELL_EVENT,
         exch_ns=2_500_000_000,local_ns=2_510_000_000,
         px=ORDER_PRICE,qty=6.0)

    # Third sell trade fills remaining 1 unit.
    _row(a,4,base=h.TRADE_EVENT,side=h.SELL_EVENT,
         exch_ns=3_000_000_000,local_ns=3_010_000_000,
         px=ORDER_PRICE,qty=1.0)

    # Markout reference updates, purely for plumbing tests.
    _row(a,5,base=h.DEPTH_EVENT,side=h.BUY_EVENT,
         exch_ns=4_000_000_000,local_ns=4_010_000_000,
         px=99.9,qty=7.0)
    _row(a,6,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=4_000_000_000,local_ns=4_010_000_000,
         px=100.0,qty=7.0)
    return a

def validate_events(data):
    np,h=_imports()
    from hftbacktest.data.validation import validate_event_order
    a=np.asarray(data,dtype=h.event_dtype)
    if len(a)==0:
        raise M1ParityError("empty_events")
    if np.any(a["local_ts"]<a["exch_ts"]):
        raise M1ParityError("negative_feed_latency")
    validate_event_order(a)
    return True

def build_asset(data,*,queue_model:str="risk_adverse",partial:bool=True,
                entry_latency_ns:int=PRIMARY_LATENCY_NS,
                response_latency_ns:int=PRIMARY_LATENCY_NS,
                maker_fee:float=0.0,
                taker_fee:float=0.0):
    _,h=_imports()
    b=(
        h.BacktestAsset()
        .data([data])
        .initial_snapshot(make_initial_snapshot())
        .linear_asset(1.0)
        .constant_order_latency(int(entry_latency_ns),int(response_latency_ns))
    )
    if queue_model=="risk_adverse":
        b=b.risk_adverse_queue_model()
    elif queue_model=="log_prob":
        b=b.log_prob_queue_model()
    else:
        raise M1ParityError("queue_model")

    b=b.partial_fill_exchange() if partial else b.no_partial_fill_exchange()
    b=(
        b.trading_value_fee_model(float(maker_fee),float(taker_fee))
        .tick_size(TICK_SIZE)
        .lot_size(LOT_SIZE)
    )
    return b


def _advance_to(bt,target_ns:int):
    now=int(bt.current_timestamp)
    target=int(target_ns)
    if target<now:
        raise M1ParityError(f"checkpoint_in_past:{target}:{now}")
    if target==now:
        return
    rc=bt.elapse(target-now)
    if rc!=0:
        raise M1ParityError(f"checkpoint_elapse:{target}:rc={rc}")

def _snap(order)->OrderSnapshot:
    return OrderSnapshot(
        status=int(order.status),
        exec_qty=float(order.exec_qty),
        leaves_qty=float(order.leaves_qty),
        exch_timestamp=int(order.exch_timestamp),
        local_timestamp=int(order.local_timestamp),
    )

def run_partial_sequence(*,queue_model:str="risk_adverse",
                         entry_latency_ns:int=PRIMARY_LATENCY_NS,
                         response_latency_ns:int=PRIMARY_LATENCY_NS):
    _,h=_imports()
    data=make_risk_averse_partial_fixture()
    validate_events(data)
    bt=h.HashMapMarketDepthBacktest([
        build_asset(
            data,
            queue_model=queue_model,
            partial=True,
            entry_latency_ns=entry_latency_ns,
            response_latency_ns=response_latency_ns,
        )
    ])
    out={}
    try:
        # Process the first market event, then submit a passive order at BBO.
        if bt.elapse(1_100_000_000)!=0:
            raise M1ParityError("early_end")
        rc=bt.submit_buy_order(0,1,ORDER_PRICE,ORDER_QTY,h.GTC,h.LIMIT,False)
        if rc!=0:
            raise M1ParityError("submit_rc")
        bt.wait_order_response(0,1,2_000_000_000)
        order=bt.orders(0).get(1)
        if order is None:
            raise M1ParityError("order_missing_after_submit")
        out["accepted"]=_snap(order)

        # Checkpoints are absolute simulator-local timestamps.  wait_order_response
        # changes current_timestamp, so relative elapse chains are not used.
        _advance_to(bt,2_100_000_000)
        order=bt.orders(0).get(1)
        out["after_cancel_and_trade5"]=_snap(order)

        _advance_to(bt,2_600_000_000)
        order=bt.orders(0).get(1)
        out["after_trade6"]=_snap(order)

        _advance_to(bt,3_100_000_000)
        order=bt.orders(0).get(1)
        out["after_trade1"]=_snap(order)
        out["position"]=float(bt.position(0))
        out["fee"]=float(bt.state_values(0).fee)
        return out
    finally:
        bt.close()

def run_no_partial_sequence():
    _,h=_imports()
    data=make_risk_averse_partial_fixture()
    validate_events(data)
    bt=h.HashMapMarketDepthBacktest([
        build_asset(data,queue_model="risk_adverse",partial=False)
    ])
    try:
        bt.elapse(1_100_000_000)
        bt.submit_buy_order(0,1,ORDER_PRICE,ORDER_QTY,h.GTC,h.LIMIT,False)
        bt.wait_order_response(0,1,2_000_000_000)
        _advance_to(bt,3_100_000_000)
        order=bt.orders(0).get(1)
        if order is None:
            raise M1ParityError("order_missing_no_partial")
        return _snap(order)
    finally:
        bt.close()

def signed_markout_bps(*,side:int,fill_price:float,reference_mid:float)->float:
    if not (math.isfinite(fill_price) and fill_price>0 and
            math.isfinite(reference_mid) and reference_mid>0):
        raise M1ParityError("markout_input")
    if side not in (1,-1):
        raise M1ParityError("markout_side")
    return float(side*10_000.0*math.log(reference_mid/fill_price))


def run_maker_fee_probe(*,maker_fee:float=0.001,taker_fee:float=0.0):
    # Python Order does not expose the engine's internal maker flag.  We verify
    # classification through the fee model instead: a passive fill must use the
    # nonzero maker fee while taker fee is fixed to zero.
    _,h=_imports()
    data=make_risk_averse_partial_fixture()
    validate_events(data)
    bt=h.HashMapMarketDepthBacktest([
        build_asset(
            data,
            queue_model="risk_adverse",
            partial=True,
            maker_fee=float(maker_fee),
            taker_fee=float(taker_fee),
        )
    ])
    try:
        bt.elapse(1_100_000_000)
        rc=bt.submit_buy_order(0,1,ORDER_PRICE,ORDER_QTY,h.GTC,h.LIMIT,False)
        if rc!=0:
            raise M1ParityError("maker_probe_submit")
        bt.wait_order_response(0,1,2_000_000_000)
        _advance_to(bt,3_100_000_000)
        order=bt.orders(0).get(1)
        if order is None:
            raise M1ParityError("maker_probe_order_missing")
        return {
            "status":int(order.status),
            "position":float(bt.position(0)),
            "fee":float(bt.state_values(0).fee),
            "maker_fee":float(maker_fee),
            "taker_fee":float(taker_fee),
        }
    finally:
        bt.close()

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
    a=np.zeros(8,dtype=h.event_dtype)

    # Local clock becomes active at ~1s. This unrelated ask update does not
    # touch or consume the bid queue.
    _row(a,0,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=1_000_000_000,local_ns=1_010_000_000,
         px=ORDER_PRICE+0.1,qty=8.0)

    # From here market events are intentionally 1.5s apart. The largest frozen
    # round trip is 500ms entry + 500ms response = 1.0s, so acceptance cannot
    # collide with or consume the next market event in the primary parity
    # fixture. Equal-timestamp ordering is tested separately below.
    #
    # Cancellation/depletion-only bid reduction. In hftbacktest 2.4.4,
    # RiskAdverseQueueModel clamps q_ahead to min(previous_q_ahead,new_depth).
    _row(a,1,base=h.DEPTH_EVENT,side=h.BUY_EVENT,
         exch_ns=2_500_000_000,local_ns=2_510_000_000,
         px=ORDER_PRICE,qty=5.0)

    # First sell trade consumes the 5 ahead -> q_ahead == 0 -> no fill.
    _row(a,2,base=h.TRADE_EVENT,side=h.SELL_EVENT,
         exch_ns=4_000_000_000,local_ns=4_010_000_000,
         px=ORDER_PRICE,qty=5.0)

    # Next sell trade makes q_ahead=-1 -> partial fill 1 of 2.
    _row(a,3,base=h.TRADE_EVENT,side=h.SELL_EVENT,
         exch_ns=5_500_000_000,local_ns=5_510_000_000,
         px=ORDER_PRICE,qty=1.0)

    # Next sell trade fills the remaining exact 1 unit.
    _row(a,4,base=h.TRADE_EVENT,side=h.SELL_EVENT,
         exch_ns=7_000_000_000,local_ns=7_010_000_000,
         px=ORDER_PRICE,qty=1.0)

    # Regression sentinel for hftbacktest issue #312. After the exact final
    # fill above, a later same-price trade must be harmless.
    _row(a,5,base=h.TRADE_EVENT,side=h.SELL_EVENT,
         exch_ns=8_500_000_000,local_ns=8_510_000_000,
         px=ORDER_PRICE,qty=1.0)

    # Markout reference updates, purely for plumbing tests.
    _row(a,6,base=h.DEPTH_EVENT,side=h.BUY_EVENT,
         exch_ns=10_000_000_000,local_ns=10_010_000_000,
         px=99.9,qty=7.0)
    _row(a,7,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=10_000_000_000,local_ns=10_010_000_000,
         px=100.0,qty=7.0)
    return a


def make_acceptance_tie_fixture():
    """Fixture whose next local feed ties a 500ms+500ms order round-trip."""
    np,h=_imports()
    a=np.zeros(3,dtype=h.event_dtype)
    _row(a,0,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=1_000_000_000,local_ns=1_010_000_000,
         px=ORDER_PRICE+0.1,qty=8.0)
    # Submit at local 1.010s. With 500ms entry + 500ms response, the acceptance
    # response is local 2.010s, exactly equal to this row's local timestamp.
    _row(a,1,base=h.DEPTH_EVENT,side=h.BUY_EVENT,
         exch_ns=2_000_000_000,local_ns=2_010_000_000,
         px=ORDER_PRICE,qty=9.0)
    _row(a,2,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=3_000_000_000,local_ns=3_010_000_000,
         px=ORDER_PRICE+0.1,qty=7.0)
    return a


def run_acceptance_tie_probe():
    _,h=_imports()
    data=make_acceptance_tie_fixture()
    validate_events(data)
    bt=h.HashMapMarketDepthBacktest([
        build_asset(
            data,
            queue_model="risk_adverse",
            partial=True,
            entry_latency_ns=STRESS_LATENCY_NS,
            response_latency_ns=STRESS_LATENCY_NS,
        )
    ])
    try:
        first=_next_market_feed(bt)
        _,lat=_submit_and_wait(bt,h)
        after_submit_ts=int(bt.current_timestamp)
        next_feed=_next_market_feed(bt)
        return {
            "first_feed_ts":first,
            "order_latency":lat,
            "after_submit_ts":after_submit_ts,
            "next_feed_ts":next_feed,
        }
    finally:
        bt.close()

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


def _snap(order)->OrderSnapshot:
    return OrderSnapshot(
        status=int(order.status),
        exec_qty=float(order.exec_qty),
        leaves_qty=float(order.leaves_qty),
        exch_timestamp=int(order.exch_timestamp),
        local_timestamp=int(order.local_timestamp),
    )

def _next_market_feed(bt):
    rc=bt.wait_next_feed(False,10_000_000_000)
    if rc!=2:
        raise M1ParityError(f"next_feed_rc:{rc}")
    return int(bt.current_timestamp)

def _observe_order_response_or_timeout(bt,*,timeout_ns:int=500_000_000):
    # hftbacktest binding semantics:
    #   0 = timeout, 1 = end, 2 = market feed, 3 = order response.
    # Primary synthetic market feeds are 1.5s apart and response latency is
    # <=500ms, so this 500ms response window cannot consume the next market
    # feed. Equal-timestamp scheduler behavior is tested in a dedicated probe.
    rc=bt.wait_next_feed(True,int(timeout_ns))
    if rc not in (0,3):
        raise M1ParityError(f"response_window_rc:{rc}")
    return int(rc)

def _submit_and_wait(bt,h):
    rc=bt.submit_buy_order(0,1,ORDER_PRICE,ORDER_QTY,h.GTC,h.LIMIT,True)
    if rc!=0:
        raise M1ParityError(f"submit_wait_rc:{rc}")
    order=bt.orders(0).get(1)
    if order is None:
        raise M1ParityError("order_missing_after_submit")
    lat=bt.order_latency(0)
    if lat is None:
        raise M1ParityError("order_latency_missing")
    req,exch,resp=(int(lat[0]),int(lat[1]),int(lat[2]))
    return order,(req,exch,resp)

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
        out["first_feed_ts"]=_next_market_feed(bt)
        order,lat=_submit_and_wait(bt,h)
        out["accepted"]=_snap(order)
        out["order_latency"]=lat

        out["cancel_feed_ts"]=_next_market_feed(bt)
        out["cancel_response_rc"]=_observe_order_response_or_timeout(bt)
        out["after_cancel"]=_snap(bt.orders(0).get(1))

        out["trade5_feed_ts"]=_next_market_feed(bt)
        out["trade5_response_rc"]=_observe_order_response_or_timeout(bt)
        out["after_trade5"]=_snap(bt.orders(0).get(1))

        out["trade1a_feed_ts"]=_next_market_feed(bt)
        out["trade1a_response_rc"]=_observe_order_response_or_timeout(bt)
        out["after_trade1a"]=_snap(bt.orders(0).get(1))

        out["trade1b_feed_ts"]=_next_market_feed(bt)
        out["trade1b_response_rc"]=_observe_order_response_or_timeout(bt)
        out["after_trade1b"]=_snap(bt.orders(0).get(1))

        # Consume the post-fill regression trade.  A correct PartialFillExchange
        # has removed the fully-filled order and emits no response here.
        out["post_fill_trade_ts"]=_next_market_feed(bt)
        out["post_fill_response_rc"]=_observe_order_response_or_timeout(bt)
        out["after_post_fill_trade"]=_snap(bt.orders(0).get(1))

        # Independent response-ledger truth.  exec_qty is per fill response in
        # hftbacktest; summing the two observed fill chunks is the authoritative
        # executed quantity for this fixture and must equal engine accounting.
        out["ledger_fill_qty"]=float(
            out["after_trade1a"].exec_qty + out["after_trade1b"].exec_qty
        )
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
        _next_market_feed(bt)
        _submit_and_wait(bt,h)
        _next_market_feed(bt)  # cancellation
        _observe_order_response_or_timeout(bt)
        _next_market_feed(bt)  # trade5 -> q_ahead == 0
        _observe_order_response_or_timeout(bt)
        _next_market_feed(bt)  # trade1 -> q_ahead < 0 => full under NoPartialFill
        _observe_order_response_or_timeout(bt)
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
    # Python Order does not expose the engine's internal maker flag.  Verify
    # classification through the fee model: passive fills must use maker fee.
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
        _next_market_feed(bt)
        _submit_and_wait(bt,h)
        _next_market_feed(bt)  # cancellation
        _observe_order_response_or_timeout(bt)
        _next_market_feed(bt)  # trade5 -> no fill
        _observe_order_response_or_timeout(bt)
        _next_market_feed(bt)  # trade1 -> partial
        _observe_order_response_or_timeout(bt)
        _next_market_feed(bt)  # trade1 -> full
        _observe_order_response_or_timeout(bt)
        _next_market_feed(bt)  # post-fill regression trade (#312 sentinel)
        _observe_order_response_or_timeout(bt)
        order=bt.orders(0).get(1)
        if order is None:
            raise M1ParityError("maker_probe_order_missing")
        return {
            "status":int(order.status),
            "position":float(bt.position(0)),
            "fee":float(bt.state_values(0).fee),
            "expected_maker_fee":float(ORDER_PRICE*ORDER_QTY*maker_fee),
            "maker_fee":float(maker_fee),
            "taker_fee":float(taker_fee),
        }
    finally:
        bt.close()



def make_cancel_latency_fixture():
    """A trade before cancel reaches the exchange must still be able to fill."""
    np,h=_imports()
    a=np.zeros(3,dtype=h.event_dtype)

    # Activate the local clock without touching the bid queue.
    _row(a,0,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=1_000_000_000,local_ns=1_010_000_000,
         px=ORDER_PRICE+0.1,qty=8.0)

    # With PRIMARY 250ms entry/response latency, submit acceptance returns at
    # local 1.510s. A cancel issued immediately then reaches the exchange at
    # 1.760s. This trade occurs at exchange 1.700s and therefore MUST still be
    # eligible to fill the resting order.
    _row(a,1,base=h.TRADE_EVENT,side=h.SELL_EVENT,
         exch_ns=1_700_000_000,local_ns=1_710_000_000,
         px=ORDER_PRICE,qty=QUEUE_AHEAD_QTY+ORDER_QTY)

    # Later harmless feed keeps the replay alive beyond fill/cancel responses.
    _row(a,2,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=2_500_000_000,local_ns=2_510_000_000,
         px=ORDER_PRICE+0.1,qty=7.0)
    return a


def run_cancel_latency_probe():
    _,h=_imports()
    data=make_cancel_latency_fixture()
    validate_events(data)
    bt=h.HashMapMarketDepthBacktest([
        build_asset(
            data,
            queue_model="risk_adverse",
            partial=True,
            entry_latency_ns=PRIMARY_LATENCY_NS,
            response_latency_ns=PRIMARY_LATENCY_NS,
        )
    ])
    try:
        first_feed_ts=_next_market_feed(bt)
        accepted,submit_latency=_submit_and_wait(bt,h)
        cancel_request_local_ts=int(bt.current_timestamp)

        rc=bt.cancel(0,1,False)
        if rc!=0:
            raise M1ParityError(f"cancel_submit_rc:{rc}")

        trade_feed_ts=_next_market_feed(bt)
        fill_response_rc=_observe_order_response_or_timeout(bt)
        order=bt.orders(0).get(1)
        if order is None:
            raise M1ParityError("order_missing_after_precancel_fill")

        return {
            "first_feed_ts":first_feed_ts,
            "accepted":_snap(accepted),
            "submit_latency":submit_latency,
            "cancel_request_local_ts":cancel_request_local_ts,
            "cancel_exchange_arrival_ts":cancel_request_local_ts+PRIMARY_LATENCY_NS,
            "trade_exchange_ts":1_700_000_000,
            "trade_feed_ts":trade_feed_ts,
            "cancel_submit_rc":int(rc),
            "fill_response_rc":int(fill_response_rc),
            "after_precancel_trade":_snap(order),
            "position":float(bt.position(0)),
            "fee":float(bt.state_values(0).fee),
        }
    finally:
        bt.close()

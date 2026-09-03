from __future__ import annotations

from dataclasses import dataclass
import math

from multimarket.dev044_t0_strategy_contract import LONG, SHORT
from multimarket import dev045_m3_policy as p

PRIMARY_LATENCY_NS=250_000_000
DIAGNOSTIC_LATENCY_NS=100_000_000
STRESS_LATENCY_NS=500_000_000

BID_ORDER_ID=4101
ASK_ORDER_ID=4102
REPLACEMENT_ORDER_ID=4103
FLATTEN_ORDER_ID=4901

class M4AdapterError(RuntimeError):
    pass

@dataclass(frozen=True)
class ReplayOrderView:
    order_id:int
    status:int
    side:int
    price_tick:int
    exec_price_tick:int
    exec_qty:float
    leaves_qty:float
    exch_timestamp:int
    local_timestamp:int


def _imports():
    import numpy as np
    import hftbacktest as h
    return np,h


def _ev(*,base:int,side:int)->int:
    _,h=_imports()
    return int(base|h.EXCH_EVENT|h.LOCAL_EVENT|side)


def _row(a,i,*,base,side,exch_ns,local_ns,px,qty):
    a[i]["ev"]=_ev(base=base,side=side)
    a[i]["exch_ts"]=int(exch_ns)
    a[i]["local_ts"]=int(local_ns)
    a[i]["px"]=float(px)
    a[i]["qty"]=float(qty)


def make_initial_snapshot():
    np,h=_imports()
    a=np.zeros(4,dtype=h.event_dtype)
    rows=(
        (h.BUY_EVENT,99.9,1.0),
        (h.BUY_EVENT,100.0,10.0),
        (h.SELL_EVENT,100.1,8.0),
        (h.SELL_EVENT,100.2,1.0),
    )
    for i,(side,px,qty) in enumerate(rows):
        a[i]["ev"]=_ev(base=h.DEPTH_SNAPSHOT_EVENT,side=side)
        a[i]["exch_ts"]=100_000_000
        a[i]["local_ts"]=110_000_000
        a[i]["px"]=px
        a[i]["qty"]=qty
    return a


def make_fill_fixture():
    np,h=_imports()
    a=np.zeros(4,dtype=h.event_dtype)
    # Activates local clock without touching the bid queue.
    _row(a,0,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=1_000_000_000,local_ns=1_010_000_000,
         px=100.1,qty=8.0)
    # RiskAdverse initial q_ahead=10. This trade makes it exactly zero: no fill.
    _row(a,1,base=h.TRADE_EVENT,side=h.SELL_EVENT,
         exch_ns=3_000_000_000,local_ns=3_010_000_000,
         px=100.0,qty=10.0)
    # One-lot M3 order: next sell trade crosses q_ahead below zero and fills.
    _row(a,2,base=h.TRADE_EVENT,side=h.SELL_EVENT,
         exch_ns=5_000_000_000,local_ns=5_010_000_000,
         px=100.0,qty=0.001)
    # Keeps replay alive for order response / forced flatten.
    _row(a,3,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=8_000_000_000,local_ns=8_010_000_000,
         px=100.1,qty=8.0)
    return a


def make_cancel_replace_fixture():
    np,h=_imports()
    a=np.zeros(2,dtype=h.event_dtype)
    _row(a,0,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=1_000_000_000,local_ns=1_010_000_000,
         px=100.1,qty=8.0)
    _row(a,1,base=h.DEPTH_EVENT,side=h.SELL_EVENT,
         exch_ns=8_000_000_000,local_ns=8_010_000_000,
         px=100.1,qty=8.0)
    return a


def validate_events(data)->None:
    np,h=_imports()
    from hftbacktest.data.validation import validate_event_order
    a=np.asarray(data,dtype=h.event_dtype)
    if len(a)==0:
        raise M4AdapterError("empty_events")
    if np.any(a["local_ts"]<a["exch_ts"]):
        raise M4AdapterError("negative_feed_latency")
    validate_event_order(a)


def build_asset(
    data,
    *,
    queue_model:str="risk_adverse",
    entry_latency_ns:int=PRIMARY_LATENCY_NS,
    response_latency_ns:int=PRIMARY_LATENCY_NS,
    maker_fee:float=0.0,
    taker_fee:float=0.0,
):
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
        raise M4AdapterError("queue_model")
    return (
        b.partial_fill_exchange()
        .trading_value_fee_model(float(maker_fee),float(taker_fee))
        .tick_size(p.TICK_SIZE)
        .lot_size(p.LOT_SIZE)
    )


def _view(order)->ReplayOrderView:
    return ReplayOrderView(
        order_id=int(order.order_id),
        status=int(order.status),
        side=int(order.side),
        price_tick=int(order.price_tick),
        exec_price_tick=int(order.exec_price_tick),
        exec_qty=float(order.exec_qty),
        leaves_qty=float(order.leaves_qty),
        exch_timestamp=int(order.exch_timestamp),
        local_timestamp=int(order.local_timestamp),
    )


def _next_feed(bt)->int:
    rc=int(bt.wait_next_feed(False,10_000_000_000))
    if rc!=2:
        raise M4AdapterError(f"next_feed_rc:{rc}")
    return int(bt.current_timestamp)


def _response_or_timeout(bt,*,timeout_ns:int=600_000_000)->int:
    rc=int(bt.wait_next_feed(True,int(timeout_ns)))
    if rc not in (0,3):
        raise M4AdapterError(f"response_rc:{rc}")
    return rc


def policy_book(*,inventory:float=0.0,inventory_age_s:float=0.0)->p.MarketState:
    return p.MarketState(
        best_bid_tick=1000,
        best_ask_tick=1001,
        bid_depth_qty={999:1.0,1000:10.0},
        ask_depth_qty={1001:8.0,1002:1.0},
        inventory=float(inventory),
        inventory_age_s=float(inventory_age_s),
    )


def validate_passive_target(*,side:str,target_tick:int,best_bid_tick:int,best_ask_tick:int)->None:
    t=int(target_tick)
    bid=int(best_bid_tick)
    ask=int(best_ask_tick)
    if bid>=ask:
        raise M4AdapterError("crossed_book")
    if side=="bid":
        if t>bid or t>=ask:
            raise M4AdapterError("bid_not_passive")
    elif side=="ask":
        if t<ask or t<=bid:
            raise M4AdapterError("ask_not_passive")
    else:
        raise M4AdapterError("side")


def submit_passive(
    bt,
    h,
    *,
    side:str,
    order_id:int,
    decision:p.PolicyDecision,
    wait:bool=True,
)->ReplayOrderView:
    depth=bt.depth(0)
    best_bid_tick=int(depth.best_bid_tick)
    best_ask_tick=int(depth.best_ask_tick)

    if side=="bid":
        if not decision.bid_enabled or decision.bid_target_tick is None:
            raise M4AdapterError("bid_disabled")
        tick=int(decision.bid_target_tick)
        qty=float(decision.bid_size)
    elif side=="ask":
        if not decision.ask_enabled or decision.ask_target_tick is None:
            raise M4AdapterError("ask_disabled")
        tick=int(decision.ask_target_tick)
        qty=float(decision.ask_size)
    else:
        raise M4AdapterError("side")

    validate_passive_target(
        side=side,
        target_tick=tick,
        best_bid_tick=best_bid_tick,
        best_ask_tick=best_ask_tick,
    )
    if qty<=0:
        raise M4AdapterError("nonpositive_qty")

    price=float(tick)*p.TICK_SIZE
    if side=="bid":
        rc=bt.submit_buy_order(0,int(order_id),price,qty,h.GTC,h.LIMIT,bool(wait))
    else:
        rc=bt.submit_sell_order(0,int(order_id),price,qty,h.GTC,h.LIMIT,bool(wait))
    if int(rc)!=0:
        raise M4AdapterError(f"submit_rc:{rc}")

    order=bt.orders(0).get(int(order_id))
    if order is None:
        raise M4AdapterError("submitted_order_missing")
    return _view(order)


def cancel_working(bt,*,order_id:int,wait:bool=True)->ReplayOrderView:
    rc=bt.cancel(0,int(order_id),bool(wait))
    if int(rc)!=0:
        raise M4AdapterError(f"cancel_rc:{rc}")
    order=bt.orders(0).get(int(order_id))
    if order is None:
        raise M4AdapterError("canceled_order_missing")
    return _view(order)


def submit_forced_flatten(
    bt,
    h,
    *,
    direction:int,
    qty:float,
    order_id:int=FLATTEN_ORDER_ID,
    wait:bool=True,
)->ReplayOrderView:
    q=float(qty)
    if not math.isfinite(q) or q<=0:
        raise M4AdapterError("flatten_qty")
    depth=bt.depth(0)
    if direction==SHORT:
        # Market order ignores limit price in PartialFillExchange, but pass the
        # current executable best bid as an auditable local request price.
        px=float(depth.best_bid)
        rc=bt.submit_sell_order(0,int(order_id),px,q,h.GTC,h.MARKET,bool(wait))
    elif direction==LONG:
        px=float(depth.best_ask)
        rc=bt.submit_buy_order(0,int(order_id),px,q,h.GTC,h.MARKET,bool(wait))
    else:
        raise M4AdapterError("flatten_direction")
    if int(rc)!=0:
        raise M4AdapterError(f"flatten_rc:{rc}")
    order=bt.orders(0).get(int(order_id))
    if order is None:
        raise M4AdapterError("flatten_order_missing")
    return _view(order)


def run_maker_fill_probe(
    *,
    latency_ns:int=PRIMARY_LATENCY_NS,
    maker_fee:float=0.001,
    taker_fee:float=0.002,
)->dict:
    _,h=_imports()
    data=make_fill_fixture()
    validate_events(data)
    bt=h.HashMapMarketDepthBacktest([
        build_asset(
            data,
            entry_latency_ns=latency_ns,
            response_latency_ns=latency_ns,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
        )
    ])
    try:
        first=_next_feed(bt)
        decision=p.policy_decision("M01",policy_book())
        accepted=submit_passive(
            bt,h,side="bid",order_id=BID_ORDER_ID,decision=decision,wait=True
        )

        trade10=_next_feed(bt)
        no_fill_rc=_response_or_timeout(bt)
        after_trade10=_view(bt.orders(0).get(BID_ORDER_ID))

        trade_lot=_next_feed(bt)
        fill_rc=_response_or_timeout(bt)
        filled=_view(bt.orders(0).get(BID_ORDER_ID))
        position=float(bt.position(0))
        fee=float(bt.state_values(0).fee)
        expected_fee=100.0*p.BASE_ORDER_QTY*float(maker_fee)
        return {
            "first_feed_ts":first,
            "trade10_ts":trade10,
            "trade_lot_ts":trade_lot,
            "accepted":accepted,
            "no_fill_rc":no_fill_rc,
            "after_trade10":after_trade10,
            "fill_rc":fill_rc,
            "filled":filled,
            "position":position,
            "ledger_fill_qty":float(filled.exec_qty),
            "fee":fee,
            "expected_maker_fee":expected_fee,
        }
    finally:
        bt.close()


def run_cancel_replace_probe()->dict:
    _,h=_imports()
    data=make_cancel_replace_fixture()
    validate_events(data)
    bt=h.HashMapMarketDepthBacktest([build_asset(data)])
    try:
        _next_feed(bt)
        d0=p.policy_decision("M01",policy_book())
        accepted=submit_passive(
            bt,h,side="bid",order_id=BID_ORDER_ID,decision=d0,wait=True
        )

        d1=p.policy_decision("M02",policy_book(inventory=0.001))
        intent1=p.maintenance_intent(
            "M02","bid",accepted.price_tick,d1,
            best_bid_tick=1000,best_ask_tick=1001,
        )
        if intent1.action!="CANCEL" or not intent1.cancel or intent1.submit:
            raise M4AdapterError("phase1_not_cancel_only")

        canceled=cancel_working(bt,order_id=BID_ORDER_ID,wait=True)

        intent2=p.maintenance_intent(
            "M02","bid",None,d1,
            best_bid_tick=1000,best_ask_tick=1001,
        )
        if intent2.action!="SUBMIT" or intent2.cancel or not intent2.submit:
            raise M4AdapterError("phase2_not_submit_only")

        replacement=submit_passive(
            bt,h,side="bid",order_id=REPLACEMENT_ORDER_ID,decision=d1,wait=True
        )
        return {
            "accepted":accepted,
            "phase1":intent1,
            "canceled":canceled,
            "phase2":intent2,
            "replacement":replacement,
            "position":float(bt.position(0)),
        }
    finally:
        bt.close()


def run_forced_flatten_probe(
    *,
    maker_fee:float=0.001,
    taker_fee:float=0.002,
)->dict:
    _,h=_imports()
    data=make_fill_fixture()
    validate_events(data)
    bt=h.HashMapMarketDepthBacktest([
        build_asset(data,maker_fee=maker_fee,taker_fee=taker_fee)
    ])
    try:
        _next_feed(bt)
        d0=p.policy_decision("M01",policy_book())
        submit_passive(
            bt,h,side="bid",order_id=BID_ORDER_ID,decision=d0,wait=True
        )
        _next_feed(bt)
        _response_or_timeout(bt)
        _next_feed(bt)
        _response_or_timeout(bt)

        maker_order=_view(bt.orders(0).get(BID_ORDER_ID))
        before=float(bt.position(0))
        if abs(before-p.BASE_ORDER_QTY)>1e-12:
            raise M4AdapterError(f"unexpected_preflatten_position:{before}")

        decision=p.policy_decision(
            "M02",
            policy_book(inventory=before,inventory_age_s=p.INVENTORY_TIMEOUT_S),
        )
        if not decision.force_flatten:
            raise M4AdapterError("flatten_not_requested")

        flat=submit_forced_flatten(
            bt,h,
            direction=decision.flatten_direction,
            qty=decision.flatten_qty,
            wait=True,
        )
        after=float(bt.position(0))
        fee=float(bt.state_values(0).fee)
        expected_fee=(
            float(maker_order.exec_price_tick)*p.TICK_SIZE*p.BASE_ORDER_QTY*maker_fee
            + float(flat.exec_price_tick)*p.TICK_SIZE*p.BASE_ORDER_QTY*taker_fee
        )
        return {
            "maker_order":maker_order,
            "position_before":before,
            "decision":decision,
            "flatten_order":flat,
            "position_after":after,
            "fee":fee,
            "expected_total_fee":float(expected_fee),
        }
    finally:
        bt.close()

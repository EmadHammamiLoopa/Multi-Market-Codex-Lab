from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import math

from multimarket.dev044_t0_strategy_contract import (
    ABSTAIN,
    LONG,
    SHORT,
    A0_GATE_THRESHOLD,
    StrategyState,
    core_action,
)

POLICY_IDS=(
    "M01","M02","M03","M04","M05","M06","M07","M08",
)
POLICY_NAMES={
    "M01":"SYM_JOIN",
    "M02":"INVENTORY_RESERVATION",
    "M03":"L1_OBI_SKEW",
    "M04":"MICROPRICE_SKEW",
    "M05":"TOXICITY_VETO",
    "M06":"T10A_OFI_MAKER_ADAPTER",
    "M07":"T05A_REVERSAL_MAKER_ADAPTER",
    "M08":"QUEUE_PRESERVE_HYSTERESIS",
}

TICK_SIZE=0.1
LOT_SIZE=0.001
BASE_ORDER_QTY=0.001
DISPLAYED_FRACTION=0.01
INVENTORY_UNIT=0.001
INVENTORY_CAP=0.003
INVENTORY_TIMEOUT_S=60.0
MAX_SHIFT_TICKS=2
OBI_T1=0.25
OBI_T2=0.50
TFI_RETREAT=0.60
TFI_DISABLE=0.80

class M3PolicyError(RuntimeError):
    pass

@dataclass(frozen=True)
class MarketState:
    best_bid_tick:int
    best_ask_tick:int
    bid_depth_qty:Mapping[int,float]
    ask_depth_qty:Mapping[int,float]
    inventory:float=0.0
    inventory_age_s:float=0.0
    aggressive_buy_qty_1s:float=0.0
    aggressive_sell_qty_1s:float=0.0
    legacy_state:StrategyState|None=None
    a0_p_touch:float=0.0

@dataclass(frozen=True)
class PolicyDecision:
    policy_id:str
    bid_target_tick:int|None
    ask_target_tick:int|None
    bid_size:float
    ask_size:float
    bid_enabled:bool
    ask_enabled:bool
    reference_shift_ticks:int
    force_flatten:bool
    flatten_direction:int
    flatten_qty:float

@dataclass(frozen=True)
class MaintenanceIntent:
    action:str
    cancel:bool
    submit:bool
    submit_tick:int|None
    submit_qty:float

@dataclass(frozen=True)
class TerminalPlan:
    cancel_bid:bool
    cancel_ask:bool
    flatten_direction:int
    flatten_qty:float


def _finite(x:float,name:str)->float:
    z=float(x)
    if not math.isfinite(z):
        raise M3PolicyError(f"nonfinite:{name}")
    return z


def _validate_market(s:MarketState)->None:
    if int(s.best_bid_tick)>=int(s.best_ask_tick):
        raise M3PolicyError("crossed_or_locked_book")
    inv=_finite(s.inventory,"inventory")
    if abs(inv)>INVENTORY_CAP+1e-12:
        raise M3PolicyError("inventory_cap_breached")
    age=_finite(s.inventory_age_s,"inventory_age_s")
    if age<0:
        raise M3PolicyError("negative_inventory_age")
    for name,v in (
        ("aggressive_buy_qty_1s",s.aggressive_buy_qty_1s),
        ("aggressive_sell_qty_1s",s.aggressive_sell_qty_1s),
    ):
        if _finite(v,name)<0:
            raise M3PolicyError(f"negative:{name}")
    p=_finite(s.a0_p_touch,"a0_p_touch")
    if p<0 or p>1:
        raise M3PolicyError("a0_probability")
    for side,m in (("bid",s.bid_depth_qty),("ask",s.ask_depth_qty)):
        for k,v in m.items():
            int(k)
            q=_finite(v,f"{side}_depth")
            if q<0:
                raise M3PolicyError(f"negative_{side}_depth")


def _clip_shift(x:int)->int:
    return max(-MAX_SHIFT_TICKS,min(MAX_SHIFT_TICKS,int(x)))


def inventory_shift_ticks(inventory:float)->int:
    inv=_finite(inventory,"inventory")
    units=abs(inv)/INVENTORY_UNIT
    mag=2 if units>=2.0-1e-12 else (1 if units>=1.0-1e-12 else 0)
    if inv>0:
        return -mag
    if inv<0:
        return mag
    return 0


def l1_obi(s:MarketState)->float:
    b=float(s.bid_depth_qty.get(int(s.best_bid_tick),0.0))
    a=float(s.ask_depth_qty.get(int(s.best_ask_tick),0.0))
    den=b+a
    if den<=0:
        return 0.0
    return (b-a)/den


def obi_shift_ticks(s:MarketState)->int:
    x=l1_obi(s)
    ax=abs(x)
    mag=0 if ax<OBI_T1 else (1 if ax<OBI_T2 else 2)
    return mag if x>0 else (-mag if x<0 else 0)


def microprice_shift_ticks(s:MarketState)->int:
    bq=float(s.bid_depth_qty.get(int(s.best_bid_tick),0.0))
    aq=float(s.ask_depth_qty.get(int(s.best_ask_tick),0.0))
    den=bq+aq
    if den<=0:
        return 0
    bid=float(s.best_bid_tick)*TICK_SIZE
    ask=float(s.best_ask_tick)*TICK_SIZE
    mid=(bid+ask)/2.0
    micro=(ask*bq+bid*aq)/den
    return _clip_shift(int(round((micro-mid)/TICK_SIZE)))


def trade_flow_imbalance(s:MarketState)->float:
    b=float(s.aggressive_buy_qty_1s)
    a=float(s.aggressive_sell_qty_1s)
    den=b+a
    return 0.0 if den<=0 else (b-a)/den


def quote_size(displayed_qty:float)->float:
    q=_finite(displayed_qty,"displayed_qty")
    if q<0:
        raise M3PolicyError("negative_displayed_qty")
    proposed=min(BASE_ORDER_QTY,DISPLAYED_FRACTION*q)
    if proposed+1e-15<LOT_SIZE:
        return 0.0
    # Wave-1 cap is itself one lot, so any executable proposal is exactly 1 lot.
    return BASE_ORDER_QTY


def _passive_targets(s:MarketState,shift:int)->tuple[int,int]:
    # The frozen M2 contract forbids inside-spread improvement. A signed fair-
    # value shift therefore retreats only the adverse side and never improves
    # the favorable side through the spread.
    sh=_clip_shift(shift)
    bid=int(s.best_bid_tick)+(sh if sh<0 else 0)
    ask=int(s.best_ask_tick)+(sh if sh>0 else 0)
    if bid>=int(s.best_ask_tick):
        bid=int(s.best_ask_tick)-1
    if ask<=int(s.best_bid_tick):
        ask=int(s.best_bid_tick)+1
    return bid,ask


def _retreat(bid:int,ask:int,*,bid_ticks:int=0,ask_ticks:int=0)->tuple[int,int]:
    return int(bid)-max(0,int(bid_ticks)),int(ask)+max(0,int(ask_ticks))


def _legacy_direction(s:MarketState,core_id:str)->int:
    if s.legacy_state is None or float(s.a0_p_touch)<A0_GATE_THRESHOLD:
        return ABSTAIN
    return int(core_action(core_id,s.legacy_state))


def policy_decision(policy_id:str,s:MarketState)->PolicyDecision:
    if policy_id not in POLICY_IDS:
        raise M3PolicyError("unknown_policy")
    _validate_market(s)

    inv=float(s.inventory)
    force_flat=abs(inv)>1e-15 and float(s.inventory_age_s)>=INVENTORY_TIMEOUT_S
    if force_flat:
        return PolicyDecision(
            policy_id=policy_id,
            bid_target_tick=None,
            ask_target_tick=None,
            bid_size=0.0,
            ask_size=0.0,
            bid_enabled=False,
            ask_enabled=False,
            reference_shift_ticks=0,
            force_flatten=True,
            flatten_direction=SHORT if inv>0 else LONG,
            flatten_qty=abs(inv),
        )

    inv_shift=inventory_shift_ticks(inv)
    shift=0 if policy_id=="M01" else inv_shift

    if policy_id=="M03":
        shift=_clip_shift(inv_shift+obi_shift_ticks(s))
    elif policy_id in ("M04","M05"):
        shift=_clip_shift(inv_shift+microprice_shift_ticks(s))

    bid,ask=_passive_targets(s,shift)

    if policy_id=="M05":
        tfi=trade_flow_imbalance(s)
        if tfi>=TFI_RETREAT:
            bid,ask=_retreat(bid,ask,ask_ticks=1)
        elif tfi<=-TFI_RETREAT:
            bid,ask=_retreat(bid,ask,bid_ticks=1)

    if policy_id=="M06":
        d=_legacy_direction(s,"T10")
        if d==LONG:
            bid,ask=_retreat(bid,ask,ask_ticks=1)
        elif d==SHORT:
            bid,ask=_retreat(bid,ask,bid_ticks=1)
    elif policy_id=="M07":
        d=_legacy_direction(s,"T05")
        if d==LONG:
            bid,ask=_retreat(bid,ask,ask_ticks=1)
        elif d==SHORT:
            bid,ask=_retreat(bid,ask,bid_ticks=1)

    bid_enabled=inv<INVENTORY_CAP-1e-12
    ask_enabled=inv>-INVENTORY_CAP+1e-12

    if policy_id=="M05":
        tfi=trade_flow_imbalance(s)
        if tfi>=TFI_DISABLE:
            ask_enabled=False
        elif tfi<=-TFI_DISABLE:
            bid_enabled=False

    bqty=float(s.bid_depth_qty.get(int(bid),0.0))
    aqty=float(s.ask_depth_qty.get(int(ask),0.0))
    bsize=quote_size(bqty) if bid_enabled else 0.0
    asize=quote_size(aqty) if ask_enabled else 0.0
    bid_enabled=bool(bid_enabled and bsize>0)
    ask_enabled=bool(ask_enabled and asize>0)

    return PolicyDecision(
        policy_id=policy_id,
        bid_target_tick=int(bid) if bid_enabled else None,
        ask_target_tick=int(ask) if ask_enabled else None,
        bid_size=float(bsize),
        ask_size=float(asize),
        bid_enabled=bid_enabled,
        ask_enabled=ask_enabled,
        reference_shift_ticks=int(shift),
        force_flatten=False,
        flatten_direction=ABSTAIN,
        flatten_qty=0.0,
    )


def maintenance_intent(
    policy_id:str,
    side:str,
    working_tick:int|None,
    decision:PolicyDecision,
    *,
    best_bid_tick:int,
    best_ask_tick:int,
)->MaintenanceIntent:
    if policy_id!=decision.policy_id:
        raise M3PolicyError("policy_decision_mismatch")
    if side not in ("bid","ask"):
        raise M3PolicyError("side")

    enabled=decision.bid_enabled if side=="bid" else decision.ask_enabled
    target=decision.bid_target_tick if side=="bid" else decision.ask_target_tick
    qty=decision.bid_size if side=="bid" else decision.ask_size

    if working_tick is not None:
        w=int(working_tick)
        marketable=(side=="bid" and w>=int(best_ask_tick)) or (
            side=="ask" and w<=int(best_bid_tick)
        )
        if marketable or not enabled:
            return MaintenanceIntent("CANCEL",True,False,None,0.0)
        if target is None:
            return MaintenanceIntent("CANCEL",True,False,None,0.0)
        if w==int(target):
            return MaintenanceIntent("KEEP",False,False,None,0.0)
        if policy_id=="M08" and abs(w-int(target))<2:
            return MaintenanceIntent("KEEP",False,False,None,0.0)
        # Cancel first. Submission is deliberately forbidden in the same intent.
        return MaintenanceIntent("CANCEL",True,False,None,0.0)

    if not enabled or target is None or qty<=0:
        return MaintenanceIntent("NONE",False,False,None,0.0)
    return MaintenanceIntent("SUBMIT",False,True,int(target),float(qty))


def terminal_plan(*,inventory:float,working_bid:bool,working_ask:bool)->TerminalPlan:
    inv=_finite(inventory,"inventory")
    if abs(inv)>INVENTORY_CAP+1e-12:
        raise M3PolicyError("inventory_cap_breached")
    direction=ABSTAIN
    qty=0.0
    if inv>1e-15:
        direction=SHORT
        qty=inv
    elif inv<-1e-15:
        direction=LONG
        qty=-inv
    return TerminalPlan(
        cancel_bid=bool(working_bid),
        cancel_ask=bool(working_ask),
        flatten_direction=direction,
        flatten_qty=float(qty),
    )


def validate_registry()->None:
    if tuple(POLICY_NAMES)!=POLICY_IDS:
        raise M3PolicyError("registry_order")
    if len(POLICY_IDS)!=8:
        raise M3PolicyError("policy_count")

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

import math

ABSTAIN=0
SHORT=-1
LONG=1

CORE_IDS=tuple(f"T{i:02d}" for i in range(1,17))
CANDIDATE_IDS=tuple(x for cid in CORE_IDS for x in (f"{cid}U",f"{cid}A"))
A0_GATE_THRESHOLD=0.50

class T0ContractError(RuntimeError):
    pass

@dataclass(frozen=True)
class StrategyState:
    # price / trend
    ret_8_bps: float = 0.0
    ret_32_bps: float = 0.0
    ema_fast_minus_slow_bps: float = 0.0
    breakout_up_bps: float = 0.0
    breakout_down_bps: float = 0.0
    rv_ratio_8_to_32: float = 1.0
    price_z_32: float = 0.0

    # fair value / book
    microprice_disp_bps: float = 0.0
    price_minus_fair_bps: float = 0.0
    obi_l1: float = 0.0
    obi_l5: float = 0.0
    obi_l20: float = 0.0
    weighted_obi: float = 0.0

    # flow
    ofi_1s: float = 0.0
    ofi_16s: float = 0.0
    ofi_32s: float = 0.0
    trade_imbalance_1s: float = 0.0
    trade_imbalance_16s: float = 0.0
    depletion_pressure: float = 0.0
    cancellation_pressure: float = 0.0

    # event-time / resilience
    event_intensity_1s: float = 0.0
    event_intensity_8s: float = 0.0
    liquidity_shock_direction: int = 0
    liquidity_recovery_fraction: float = 0.0

    # round-number / regime
    mid_price: float = 0.0
    round_level: float = 0.0
    round_distance_bps: float = math.inf
    toxicity: float = 0.0
    spread_bps: float = 0.0


def _finite_state(s: StrategyState) -> None:
    for name,value in vars(s).items():
        if name=="liquidity_shock_direction":
            if value not in (-1,0,1):
                raise T0ContractError("shock_direction")
            continue
        if not math.isfinite(float(value)):
            raise T0ContractError(f"nonfinite:{name}")


def _sgn(x: float, eps: float=0.0) -> int:
    x=float(x)
    if x>eps:return LONG
    if x<-eps:return SHORT
    return ABSTAIN


def _agree(*votes:int)->int:
    nz=[int(v) for v in votes if int(v)!=ABSTAIN]
    if not nz or len(nz)!=len(votes):
        return ABSTAIN
    return nz[0] if all(v==nz[0] for v in nz) else ABSTAIN


def t01(s:StrategyState)->int:
    return _agree(_sgn(s.ret_8_bps),_sgn(s.ret_32_bps))


def t02(s:StrategyState)->int:
    return _sgn(s.ema_fast_minus_slow_bps,0.5)


def t03(s:StrategyState)->int:
    up=float(s.breakout_up_bps)
    dn=float(s.breakout_down_bps)
    if up>=1.0 and dn<1.0:return LONG
    if dn>=1.0 and up<1.0:return SHORT
    return ABSTAIN


def t04(s:StrategyState)->int:
    if float(s.rv_ratio_8_to_32)<1.25:
        return ABSTAIN
    return _sgn(s.ret_32_bps,1.0)


def t05(s:StrategyState)->int:
    z=float(s.price_z_32)
    if z<=-1.5:return LONG
    if z>=1.5:return SHORT
    return ABSTAIN


def t06(s:StrategyState)->int:
    return _sgn(s.microprice_disp_bps,0.5)


def t07(s:StrategyState)->int:
    d=float(s.price_minus_fair_bps)
    if d>=1.0 and float(s.obi_l1)<=0.0:return SHORT
    if d<=-1.0 and float(s.obi_l1)>=0.0:return LONG
    return ABSTAIN


def t08(s:StrategyState)->int:
    return _sgn(s.obi_l1,0.20)


def t09(s:StrategyState)->int:
    return _agree(
        _sgn(s.obi_l5,0.05),
        _sgn(s.obi_l20,0.05),
        _sgn(s.weighted_obi,0.05),
    )


def t10(s:StrategyState)->int:
    return _agree(
        _sgn(s.ofi_1s,0.05),
        _sgn(s.ofi_16s,0.05),
        _sgn(s.ofi_32s,0.05),
    )


def t11(s:StrategyState)->int:
    return _agree(
        _sgn(s.trade_imbalance_1s,0.10),
        _sgn(s.trade_imbalance_16s,0.10),
    )


def t12(s:StrategyState)->int:
    return _agree(
        _sgn(s.depletion_pressure,0.10),
        _sgn(s.cancellation_pressure,0.10),
    )


def t13(s:StrategyState)->int:
    return _agree(
        _sgn(s.event_intensity_1s,0.05),
        _sgn(s.event_intensity_8s,0.05),
    )


def t14(s:StrategyState)->int:
    d=int(s.liquidity_shock_direction)
    if d==0:return ABSTAIN
    # continuation only when recovery is incomplete
    if float(s.liquidity_recovery_fraction)<0.50:
        return d
    return ABSTAIN


def t15(s:StrategyState)->int:
    # nearest $100 BTC round level supplied causally by materializer.
    if float(s.round_distance_bps)>5.0:
        return ABSTAIN
    if float(s.mid_price)<float(s.round_level) and float(s.trade_imbalance_16s)>=0.10:
        return LONG
    if float(s.mid_price)>float(s.round_level) and float(s.trade_imbalance_16s)<=-0.10:
        return SHORT
    return ABSTAIN


def t16(s:StrategyState)->int:
    votes=(
        _sgn(s.ret_32_bps,1.0),
        _sgn(s.weighted_obi,0.05),
        _sgn(s.trade_imbalance_16s,0.10),
    )
    longs=sum(v==LONG for v in votes)
    shorts=sum(v==SHORT for v in votes)
    if max(longs,shorts)<2:
        return ABSTAIN
    # fixed veto only; never reverses the vote
    if float(s.toxicity)>=0.80 or float(s.spread_bps)>=5.0:
        return ABSTAIN
    return LONG if longs>shorts else SHORT


CORE_RULES:Mapping[str,Callable[[StrategyState],int]]={
    "T01":t01,"T02":t02,"T03":t03,"T04":t04,
    "T05":t05,"T06":t06,"T07":t07,"T08":t08,
    "T09":t09,"T10":t10,"T11":t11,"T12":t12,
    "T13":t13,"T14":t14,"T15":t15,"T16":t16,
}


def core_action(core_id:str,state:StrategyState)->int:
    if tuple(CORE_RULES)!=CORE_IDS:
        raise T0ContractError("registry_order")
    if core_id not in CORE_RULES:
        raise T0ContractError("unknown_core")
    _finite_state(state)
    out=int(CORE_RULES[core_id](state))
    if out not in (ABSTAIN,SHORT,LONG):
        raise T0ContractError("invalid_action")
    return out


def candidate_action(candidate_id:str,state:StrategyState,*,a0_p_touch:float)->int:
    if candidate_id not in CANDIDATE_IDS:
        raise T0ContractError("unknown_candidate")
    p=float(a0_p_touch)
    if not math.isfinite(p) or p<0.0 or p>1.0:
        raise T0ContractError("a0_probability")
    core_id=candidate_id[:3]
    ungated=core_action(core_id,state)
    if candidate_id.endswith("U"):
        return ungated
    if candidate_id.endswith("A"):
        return ungated if p>=A0_GATE_THRESHOLD else ABSTAIN
    raise T0ContractError("candidate_suffix")


def validate_registry()->None:
    if tuple(CORE_RULES)!=CORE_IDS:
        raise T0ContractError("core_registry_order")
    if len(CORE_IDS)!=16 or len(CANDIDATE_IDS)!=32:
        raise T0ContractError("candidate_count")
    expected=tuple(x for cid in CORE_IDS for x in (f"{cid}U",f"{cid}A"))
    if CANDIDATE_IDS!=expected:
        raise T0ContractError("candidate_registry")

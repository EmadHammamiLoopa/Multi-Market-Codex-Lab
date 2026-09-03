from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import math
import numpy as np

from . import dev044_t0_strategy_contract as contract

GRID_US=250_000
LOOKBACK_S=32
LOOKBACK_STEPS=LOOKBACK_S*4
EMA_FAST_TAU_S=4.0
EMA_SLOW_TAU_S=32.0
ROUND_STEP_USD=100.0
EPS=1e-12

RAW_REQUIRED=("S05","S06","S21","S30","S31","S32")

class StateMaterializationError(RuntimeError):
    pass

@dataclass(frozen=True)
class StateMaterializationResult:
    state:contract.StrategyState
    readiness:dict[str,bool]
    blockers:tuple[str,...]


def _as1(name:str,x)->np.ndarray:
    a=np.asarray(x,dtype=np.float64)
    if a.ndim!=1:
        raise StateMaterializationError(f"{name}_not_1d")
    return a


def _exact_pos(ts:np.ndarray,t:int)->int:
    i=int(np.searchsorted(ts,int(t),side="left"))
    if i>=len(ts) or int(ts[i])!=int(t):
        raise StateMaterializationError(f"timestamp_missing:{t}")
    return i


def _window(ts:np.ndarray,end_idx:int,seconds:int,*,include_current:bool=True)->np.ndarray:
    n=int(seconds*4)
    stop=end_idx+1 if include_current else end_idx
    width=n+1 if include_current else n
    start=stop-width
    if start<0:
        raise StateMaterializationError(f"insufficient_history:{seconds}")
    idx=np.arange(start,stop,dtype=np.int64)
    if len(idx)<2:
        raise StateMaterializationError("window_too_short")
    expected=np.arange(ts[idx[0]],ts[idx[-1]]+GRID_US,GRID_US,dtype=np.int64)
    if not np.array_equal(ts[idx],expected):
        raise StateMaterializationError("non_250ms_window")
    return idx


def _ret_bps(mid:np.ndarray,i:int,seconds:int)->float:
    j=i-int(seconds*4)
    if j<0 or mid[i]<=0 or mid[j]<=0:
        raise StateMaterializationError("return_history")
    return float(10000*np.log(mid[i]/mid[j]))


def _ewm_last(values:np.ndarray,tau_s:float)->float:
    x=np.asarray(values,dtype=np.float64)
    if len(x)==0 or np.any(~np.isfinite(x)):
        raise StateMaterializationError("ewm_values")
    alpha=1.0-math.exp(-0.25/float(tau_s))
    z=float(x[0])
    for v in x[1:]:
        z=alpha*float(v)+(1.0-alpha)*z
    return z


def _ema_displacement_bps(mid:np.ndarray,i:int)->float:
    idx=_window(np.arange(len(mid),dtype=np.int64)*GRID_US,i,32,include_current=True)
    vals=mid[idx]
    if np.any(~np.isfinite(vals)) or np.any(vals<=0):
        raise StateMaterializationError("ema_mid")
    f=_ewm_last(vals,EMA_FAST_TAU_S)
    s=_ewm_last(vals,EMA_SLOW_TAU_S)
    m=float(mid[i])
    return float(10000*(f-s)/m)


def _breakout(mid:np.ndarray,i:int)->tuple[float,float]:
    idx=_window(np.arange(len(mid),dtype=np.int64)*GRID_US,i,32,include_current=False)
    vals=mid[idx]
    cur=float(mid[i])
    if np.any(~np.isfinite(vals)) or np.any(vals<=0) or cur<=0:
        raise StateMaterializationError("breakout_mid")
    hi=float(np.max(vals));lo=float(np.min(vals))
    up=max(0.0,float(10000*np.log(cur/hi)))
    dn=max(0.0,float(10000*np.log(lo/cur)))
    return up,dn


def _rv_ratio(mid:np.ndarray,i:int)->float:
    def rv(sec:int)->float:
        idx=_window(np.arange(len(mid),dtype=np.int64)*GRID_US,i,sec,include_current=True)
        vals=mid[idx]
        if np.any(vals<=0) or np.any(~np.isfinite(vals)):
            raise StateMaterializationError("rv_mid")
        r=10000*np.diff(np.log(vals))
        return float(np.sqrt(np.mean(r*r))) if len(r) else 0.0
    r8=rv(8);r32=rv(32)
    return float(r8/(r32+EPS))


def _price_z32(mid:np.ndarray,i:int)->float:
    idx=_window(np.arange(len(mid),dtype=np.int64)*GRID_US,i,32,include_current=False)
    x=np.log(mid[idx])
    cur=math.log(float(mid[i]))
    mu=float(np.mean(x));sd=float(np.std(x,ddof=0))
    return float((cur-mu)/(sd+EPS))


def _trailing_mean(arr:np.ndarray,i:int,seconds:int)->float:
    idx=_window(np.arange(len(arr),dtype=np.int64)*GRID_US,i,seconds,include_current=True)
    vals=arr[idx]
    if np.any(~np.isfinite(vals)):
        raise StateMaterializationError("trailing_mean_values")
    return float(np.mean(vals))


def _source_array(source:Mapping[str,Sequence[float]],name:str,n:int)->np.ndarray:
    if name not in source:
        raise StateMaterializationError(f"source_missing:{name}")
    a=np.asarray(source[name],dtype=np.float64)
    if a.shape!=(n,) or np.any(~np.isfinite(a)):
        raise StateMaterializationError(f"source_shape_or_finite:{name}")
    return a


def _raw_row(raw:Mapping[str,np.ndarray]|None,name:str,row:int)->np.ndarray|None:
    if raw is None or name not in raw:
        return None
    a=np.asarray(raw[name],dtype=np.float64)
    if a.ndim!=2 or row<0 or row>=len(a) or np.any(~np.isfinite(a[row])):
        raise StateMaterializationError(f"raw_shape_or_finite:{name}")
    return a[row]


def _round_state(mid:float)->tuple[float,float]:
    level=round(float(mid)/ROUND_STEP_USD)*ROUND_STEP_USD
    dist=float(abs(10000*math.log(float(mid)/float(level)))) if level>0 else 1_000_000.0
    return float(level),dist


def _raw_t09(raw,row:int)->tuple[float,float]|None:
    s05=_raw_row(raw,"S05",row)
    s06=_raw_row(raw,"S06",row)
    if s05 is None or s06 is None:
        return None
    if len(s05)!=7 or len(s06)!=2:
        raise StateMaterializationError("t09_raw_width")
    # DEV032 S05 Ls=[1,2,3,5,10,20,50], S06 f0=inverse-bp weighted OBI.
    return float(s05[5]),float(s06[0])


def _raw_t12(raw,row:int)->tuple[float,float]|None:
    s21=_raw_row(raw,"S21",row)
    if s21 is None:
        return None
    if len(s21)!=8:
        raise StateMaterializationError("t12_raw_width")
    # S21 order: type insert/delete/replenish/deplete × near/deep.
    cancellation=float(np.mean(s21[2:4]))
    depletion=float(np.mean(s21[6:8]))
    return depletion,cancellation


def _raw_t13(raw,row:int)->tuple[float,float]|None:
    s30=_raw_row(raw,"S30",row)
    s31=_raw_row(raw,"S31",row)
    if s30 is None or s31 is None:
        return None
    if len(s30)!=6 or len(s31)!=6:
        raise StateMaterializationError("t13_raw_width")
    # S30 f0/f1 = bid-add vs ask-add imbalance at tau 1/8.
    # S31 f0/f1 = ask-remove vs bid-remove imbalance at tau 1/8.
    # Both conventions are positive for bullish pressure.
    return float(0.5*(s30[0]+s31[0])),float(0.5*(s30[1]+s31[1]))


def _raw_t14(raw,row:int)->tuple[int,float]|None:
    s32=_raw_row(raw,"S32",row)
    if s32 is None:
        return None
    if len(s32)!=4:
        raise StateMaterializationError("t14_raw_width")
    brec,arec,bage,aage=(float(x) for x in s32)
    if bage>=32.0 and aage>=32.0:
        return 0,0.0
    if bage<aage:
        return contract.SHORT,brec
    if aage<bage:
        return contract.LONG,arec
    return 0,0.0


def materialize_state(
    *,
    timestamps_us,
    mid,
    source:Mapping[str,Sequence[float]],
    decision_timestamp_us:int,
    raw:Mapping[str,np.ndarray]|None=None,
    raw_row:int|None=None,
    toxicity:float|None=None,
)->StateMaterializationResult:
    ts=np.asarray(timestamps_us,dtype=np.int64)
    m=_as1("mid",mid)
    if len(ts)!=len(m) or len(ts)<2 or np.any(np.diff(ts)!=GRID_US):
        raise StateMaterializationError("grid")
    if np.any(~np.isfinite(m)) or np.any(m<=0):
        raise StateMaterializationError("mid_values")
    i=_exact_pos(ts,int(decision_timestamp_us))

    micro=_source_array(source,"microprice_minus_mid_bps",len(ts))
    obi1=_source_array(source,"obi_l1",len(ts))
    obi5=_source_array(source,"obi_l5",len(ts))
    spread=_source_array(source,"spread_bps",len(ts))
    tqi1=_source_array(source,"trade_qty_imbalance_1s",len(ts))

    ret8=_ret_bps(m,i,8)
    ret32=_ret_bps(m,i,32)
    ema=_ema_displacement_bps(m,i)
    bout_up,bout_dn=_breakout(m,i)
    rv=_rv_ratio(m,i)
    z=_price_z32(m,i)
    trade16=_trailing_mean(tqi1,i,16)

    level,round_dist=_round_state(float(m[i]))

    row=int(raw_row) if raw_row is not None else -1
    t09=_raw_t09(raw,row) if row>=0 else None
    t12=_raw_t12(raw,row) if row>=0 else None
    t13=_raw_t13(raw,row) if row>=0 else None
    t14=_raw_t14(raw,row) if row>=0 else None

    blockers=[]
    readiness={cid:True for cid in contract.CORE_IDS}

    if t09 is None:
        readiness["T09"]=False;blockers.append("T09_DEV032_RAW_REQUIRED")
        obi20=weighted=0.0
    else:
        obi20,weighted=t09

    # T10 deliberately remains blocked until a normalized 1s/16s/32s raw-flow
    # transform is frozen. Do not substitute raw S15 magnitudes.
    readiness["T10"]=False
    blockers.append("T10_NORMALIZED_FLOW_RULE_PENDING")

    if t12 is None:
        readiness["T12"]=False;blockers.append("T12_DEV032_RAW_REQUIRED")
        depletion=cancellation=0.0
    else:
        depletion,cancellation=t12

    if t13 is None:
        readiness["T13"]=False;blockers.append("T13_DEV032_RAW_REQUIRED")
        inten1=inten8=0.0
    else:
        inten1,inten8=t13

    if t14 is None:
        readiness["T14"]=False;blockers.append("T14_DEV032_RAW_REQUIRED")
        shock_dir=0;recovery=0.0
    else:
        shock_dir,recovery=t14

    if toxicity is None:
        readiness["T16"]=False
        blockers.append("T16_TOXICITY_LINEAGE_PENDING")
        tox=0.0
    else:
        tox=float(toxicity)
        if not math.isfinite(tox) or tox<0.0 or tox>1.0:
            raise StateMaterializationError("toxicity_value")

    state=contract.StrategyState(
        ret_8_bps=ret8,
        ret_32_bps=ret32,
        ema_fast_minus_slow_bps=ema,
        breakout_up_bps=bout_up,
        breakout_down_bps=bout_dn,
        rv_ratio_8_to_32=rv,
        price_z_32=z,
        microprice_disp_bps=float(micro[i]),
        price_minus_fair_bps=float(-micro[i]),
        obi_l1=float(obi1[i]),
        obi_l5=float(obi5[i]),
        obi_l20=float(obi20),
        weighted_obi=float(weighted),
        ofi_1s=0.0,
        ofi_16s=0.0,
        ofi_32s=0.0,
        trade_imbalance_1s=float(tqi1[i]),
        trade_imbalance_16s=trade16,
        depletion_pressure=float(depletion),
        cancellation_pressure=float(cancellation),
        event_intensity_1s=float(inten1),
        event_intensity_8s=float(inten8),
        liquidity_shock_direction=int(shock_dir),
        liquidity_recovery_fraction=float(recovery),
        mid_price=float(m[i]),
        round_level=level,
        round_distance_bps=round_dist,
        toxicity=tox,
        spread_bps=float(spread[i]),
    )

    # StrategyState's own fail-closed validation is authoritative.
    contract.core_action("T01",state)
    return StateMaterializationResult(state,readiness,tuple(blockers))


def assert_t1_ready(result:StateMaterializationResult)->None:
    missing=[cid for cid in contract.CORE_IDS if not result.readiness.get(cid,False)]
    if missing:
        raise StateMaterializationError("t1_not_ready:"+",".join(missing))

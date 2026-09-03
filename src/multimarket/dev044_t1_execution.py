from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import math
import numpy as np

from . import dev044_t0_strategy_contract as contract

GRID_US=250_000
HORIZON_SECONDS=1800
BARRIER_BPS=32.0
PRIMARY_ENTRY_LATENCY_MS=250
PRIMARY_RESPONSE_LATENCY_MS=250
LATENCY_STRESS_ENTRY_MS=500
LATENCY_STRESS_RESPONSE_MS=500

EXIT_TP="TP"
EXIT_SL="SL"
EXIT_HORIZON="HORIZON"

class T1ExecutionError(RuntimeError):
    pass

@dataclass(frozen=True)
class DirectedTrade:
    candidate_id:str
    day:str
    action:int
    decision_timestamp_us:int
    entry_timestamp_us:int
    barrier_touch_timestamp_us:int|None
    exit_timestamp_us:int
    entry_price:float
    exit_price:float
    gross_bps:float
    exit_reason:str

@dataclass(frozen=True)
class CandidateExecution:
    candidate_id:str
    trades:tuple[DirectedTrade,...]
    ignored_overlap_actions:int
    execution_integrity_failures:int
    emitted_actions:int

def _exact_pos(ts:np.ndarray,target:int)->int|None:
    i=int(np.searchsorted(ts,int(target),side="left"))
    return i if i<len(ts) and int(ts[i])==int(target) else None

def _validate_day_arrays(day):
    ts=np.asarray(day.ts,dtype=np.int64)
    bid=np.asarray(day.bid,dtype=np.float64)
    ask=np.asarray(day.ask,dtype=np.float64)
    valid=np.asarray(day.book_valid,dtype=bool)
    if any(x.ndim!=1 for x in (ts,bid,ask,valid)):
        raise T1ExecutionError("day_shape")
    if not (len(ts)==len(bid)==len(ask)==len(valid)):
        raise T1ExecutionError("day_length")
    if len(ts)==0 or np.any(np.diff(ts)!=GRID_US):
        raise T1ExecutionError("day_grid")
    return ts,bid,ask,valid

def _quotes_ok(bid:np.ndarray,ask:np.ndarray,valid:np.ndarray)->bool:
    return bool(
        np.all(valid)
        and np.all(np.isfinite(bid))
        and np.all(np.isfinite(ask))
        and np.all(bid>0)
        and np.all(ask>0)
        and np.all(bid<=ask)
    )

def _latency_us(ms:int)->int:
    x=int(ms)*1000
    if x<=0 or x%GRID_US!=0:
        raise T1ExecutionError("latency_grid")
    return x

def _one_trade(
    *,
    candidate_id:str,
    day_name:str,
    day,
    decision_timestamp_us:int,
    action:int,
    entry_latency_ms:int,
    response_latency_ms:int,
    horizon_seconds:int=HORIZON_SECONDS,
    barrier_bps:float=BARRIER_BPS,
)->DirectedTrade:
    if action not in (contract.LONG,contract.SHORT):
        raise T1ExecutionError("nonactive_action")
    if candidate_id not in contract.CANDIDATE_IDS:
        raise T1ExecutionError("candidate_id")
    if int(horizon_seconds)!=HORIZON_SECONDS or not math.isclose(float(barrier_bps),BARRIER_BPS,rel_tol=0,abs_tol=1e-12):
        raise T1ExecutionError("geometry_not_frozen")

    ts,bid,ask,valid=_validate_day_arrays(day)
    entry_us=int(decision_timestamp_us)+_latency_us(entry_latency_ms)
    horizon_us=entry_us+int(horizon_seconds)*1_000_000
    forced_exit_us=horizon_us+_latency_us(response_latency_ms)

    ei=_exact_pos(ts,entry_us)
    hi=_exact_pos(ts,horizon_us)
    fi=_exact_pos(ts,forced_exit_us)
    if ei is None or hi is None or fi is None:
        raise T1ExecutionError("required_timestamp_missing")
    if not (ei<=hi<=fi):
        raise T1ExecutionError("timestamp_order")

    # DEV030/DEV041 lineage is deliberately conservative: a decision is
    # executable only when the full entry-through-horizon quote path is exact
    # and valid. The response quote used for realized exit must also be valid.
    if not _quotes_ok(bid[ei:hi+1],ask[ei:hi+1],valid[ei:hi+1]):
        raise T1ExecutionError("path_quote_invalid")
    if not _quotes_ok(bid[fi:fi+1],ask[fi:fi+1],valid[fi:fi+1]):
        raise T1ExecutionError("forced_response_quote_invalid")

    entry_price=float(ask[ei]) if action==contract.LONG else float(bid[ei])
    if action==contract.LONG:
        path=10_000.0*np.log(bid[ei:hi+1]/entry_price)
    else:
        path=10_000.0*np.log(entry_price/ask[ei:hi+1])

    tp=np.flatnonzero(path>=float(barrier_bps))
    sl=np.flatnonzero(path<=-float(barrier_bps))
    ti=int(tp[0]) if len(tp) else None
    si=int(sl[0]) if len(sl) else None

    if ti is None and si is None:
        touch_ts=None
        exit_ts=forced_exit_us
        xi=fi
        reason=EXIT_HORIZON
    else:
        if si is None or (ti is not None and ti<si):
            rel=ti
            reason=EXIT_TP
        elif ti is None or si<ti:
            rel=si
            reason=EXIT_SL
        else:
            raise T1ExecutionError("same_row_tp_sl")
        touch_index=ei+int(rel)
        touch_ts=int(ts[touch_index])
        exit_ts=touch_ts+_latency_us(response_latency_ms)
        xi=_exact_pos(ts,exit_ts)
        if xi is None:
            raise T1ExecutionError("response_timestamp_missing")
        if not _quotes_ok(bid[xi:xi+1],ask[xi:xi+1],valid[xi:xi+1]):
            raise T1ExecutionError("response_quote_invalid")

    exit_price=float(bid[xi]) if action==contract.LONG else float(ask[xi])
    if action==contract.LONG:
        gross=float(10_000.0*np.log(exit_price/entry_price))
    else:
        gross=float(10_000.0*np.log(entry_price/exit_price))
    if not math.isfinite(gross):
        raise T1ExecutionError("gross_nonfinite")

    return DirectedTrade(
        candidate_id=candidate_id,
        day=day_name,
        action=int(action),
        decision_timestamp_us=int(decision_timestamp_us),
        entry_timestamp_us=entry_us,
        barrier_touch_timestamp_us=touch_ts,
        exit_timestamp_us=int(exit_ts),
        entry_price=entry_price,
        exit_price=exit_price,
        gross_bps=gross,
        exit_reason=reason,
    )

def execute_candidate_day(
    *,
    candidate_id:str,
    day_name:str,
    day,
    decisions:Sequence[int],
    actions:Sequence[int],
    entry_latency_ms:int=PRIMARY_ENTRY_LATENCY_MS,
    response_latency_ms:int=PRIMARY_RESPONSE_LATENCY_MS,
)->CandidateExecution:
    if candidate_id not in contract.CANDIDATE_IDS:
        raise T1ExecutionError("candidate_id")
    d=np.asarray(decisions,dtype=np.int64)
    a=np.asarray(actions,dtype=np.int8)
    if d.ndim!=1 or a.ndim!=1 or len(d)!=len(a) or len(d)==0:
        raise T1ExecutionError("action_shape")
    if np.any(np.diff(d)<=0):
        raise T1ExecutionError("decision_order")
    if np.any(~np.isin(a,(contract.ABSTAIN,contract.LONG,contract.SHORT))):
        raise T1ExecutionError("action_value")

    trades=[]
    ignored=0
    failures=0
    emitted=int(np.sum(a!=contract.ABSTAIN))
    flat_after=-1
    for t,act in zip(d.tolist(),a.tolist()):
        if int(act)==contract.ABSTAIN:
            continue
        if int(t)<flat_after:
            ignored+=1
            continue
        try:
            tr=_one_trade(
                candidate_id=candidate_id,
                day_name=day_name,
                day=day,
                decision_timestamp_us=int(t),
                action=int(act),
                entry_latency_ms=int(entry_latency_ms),
                response_latency_ms=int(response_latency_ms),
            )
        except T1ExecutionError:
            failures+=1
            continue
        trades.append(tr)
        flat_after=int(tr.exit_timestamp_us)

    return CandidateExecution(
        candidate_id=candidate_id,
        trades=tuple(trades),
        ignored_overlap_actions=int(ignored),
        execution_integrity_failures=int(failures),
        emitted_actions=emitted,
    )

def profit_factor(values)->float:
    x=np.asarray(values,dtype=np.float64)
    pos=float(np.sum(x[x>0]))
    neg=float(np.sum(x[x<0]))
    if neg==0:
        return float("inf") if pos>0 else 0.0
    return float(pos/abs(neg))

def max_drawdown_by_exit(trades:Sequence[DirectedTrade],net_bps:Sequence[float])->float:
    if len(trades)!=len(net_bps):
        raise T1ExecutionError("drawdown_shape")
    order=sorted(range(len(trades)),key=lambda i:(trades[i].exit_timestamp_us,trades[i].decision_timestamp_us))
    vals=np.asarray([float(net_bps[i]) for i in order],dtype=np.float64)
    eq=np.concatenate(([0.0],np.cumsum(vals)))
    peak=np.maximum.accumulate(eq)
    return float(np.max(peak-eq))

def economics(trades:Sequence[DirectedTrade],cost_bps:float)->dict:
    if cost_bps<0:
        raise T1ExecutionError("negative_cost")
    if not trades:
        return {
            "accepted_trades":0,"accepted_long":0,"accepted_short":0,
            "mean_gross_bps":None,"mean_net_bps":None,"total_net_bps":0.0,
            "profit_factor":0.0,"positive_days":0,"per_day":[],
            "loo_mean_net_bps":[],"positive_day_concentration":1.0,
            "max_drawdown_bps":0.0,"median_daily_net_bps":0.0,
        }
    gross=np.asarray([t.gross_bps for t in trades],dtype=np.float64)
    net=gross-float(cost_bps)
    days=tuple(dict.fromkeys(t.day for t in trades))
    per=[]
    positive=[]
    for day in days:
        idx=[i for i,t in enumerate(trades) if t.day==day]
        vals=net[idx]
        total=float(np.sum(vals))
        per.append({"day":day,"trades":len(idx),"net_bps":total,"positive":bool(total>0)})
        positive.append(max(0.0,total))
    pos_total=float(sum(positive))
    concentration=float(max(positive)/pos_total) if pos_total>0 else 1.0
    loo=[]
    for omit in days:
        vals=np.asarray([net[i] for i,t in enumerate(trades) if t.day!=omit],dtype=np.float64)
        loo.append({"omitted_day":omit,"mean_net_bps":float(np.mean(vals)) if len(vals) else None})
    return {
        "accepted_trades":int(len(trades)),
        "accepted_long":int(sum(t.action==contract.LONG for t in trades)),
        "accepted_short":int(sum(t.action==contract.SHORT for t in trades)),
        "mean_gross_bps":float(np.mean(gross)),
        "mean_net_bps":float(np.mean(net)),
        "total_net_bps":float(np.sum(net)),
        "profit_factor":profit_factor(net),
        "positive_days":int(sum(x["positive"] for x in per)),
        "per_day":per,
        "loo_mean_net_bps":loo,
        "positive_day_concentration":concentration,
        "max_drawdown_bps":max_drawdown_by_exit(trades,net),
        "median_daily_net_bps":float(np.median([x["net_bps"] for x in per])),
    }

def aligned_block_totals(
    trades:Sequence[DirectedTrade],
    *,
    cost_bps:float,
    days:Sequence[str],
    block_hours:int=4,
)->np.ndarray:
    if 24%int(block_hours)!=0:
        raise T1ExecutionError("block_hours")
    blocks_per_day=24//int(block_hours)
    out=np.zeros(len(days)*blocks_per_day,dtype=np.float64)
    day_pos={d:i for i,d in enumerate(days)}
    for t in trades:
        if t.day not in day_pos:
            raise T1ExecutionError("block_day")
        hour=int((t.decision_timestamp_us//3_600_000_000)%24)
        block=hour//int(block_hours)
        out[day_pos[t.day]*blocks_per_day+block]+=float(t.gross_bps)-float(cost_bps)
    return out

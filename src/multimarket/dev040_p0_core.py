from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

LATENCIES_MS=(250,500,1000)
HOLD_SECONDS=120
ACTION_ABSTAIN=0
ACTION_SHORT=1
ACTION_LONG=2

class P0Error(RuntimeError):
    pass

@dataclass(frozen=True)
class TradeAudit:
    action_index:int
    action:int
    decision_timestamp_us:int
    entry_timestamp_us:int
    exit_timestamp_us:int
    entry_index:int
    exit_index:int
    entry_spread_bps:float
    exit_spread_bps:float

def _exact_position(ts:np.ndarray,target:int)->int:
    i=int(np.searchsorted(ts,int(target),side="left"))
    if i>=len(ts) or int(ts[i])!=int(target):
        raise P0Error(f"timestamp_missing:{target}")
    return i

def _spread_bps(bid:float,ask:float)->float:
    if not np.isfinite(bid) or not np.isfinite(ask) or bid<=0 or ask<=0 or ask<bid:
        raise P0Error("invalid_quote")
    mid=0.5*(bid+ask)
    if mid<=0:
        raise P0Error("invalid_mid")
    return float(10000.0*(ask-bid)/mid)

def flat_only_audit(
    *,
    decision_timestamps_us,
    actions,
    raw_timestamps_us,
    bid,
    ask,
    book_valid,
    latency_ms:int,
)->tuple[tuple[TradeAudit,...],int]:
    if int(latency_ms) not in LATENCIES_MS:
        raise P0Error("latency_not_frozen")

    dts=np.asarray(decision_timestamps_us,dtype=np.int64)
    a=np.asarray(actions,dtype=np.int8)
    ts=np.asarray(raw_timestamps_us,dtype=np.int64)
    b=np.asarray(bid,dtype=np.float64)
    q=np.asarray(ask,dtype=np.float64)
    valid=np.asarray(book_valid,dtype=bool)

    if dts.ndim!=1 or a.ndim!=1 or len(dts)!=len(a):
        raise P0Error("action_shape")
    if ts.ndim!=1 or any(x.ndim!=1 for x in (b,q,valid)):
        raise P0Error("raw_shape")
    if not (len(ts)==len(b)==len(q)==len(valid)):
        raise P0Error("raw_length")
    if len(ts)==0 or np.any(np.diff(ts)<=0):
        raise P0Error("raw_chronology")
    if np.any(~np.isin(a,(0,1,2))):
        raise P0Error("action_domain")

    lat_us=int(latency_ms)*1000
    hold_us=HOLD_SECONDS*1_000_000

    out=[]
    ignored=0
    flat_after=-1

    for i,(dt,act) in enumerate(zip(dts.tolist(),a.tolist(),strict=True)):
        if int(act)==ACTION_ABSTAIN:
            continue
        if int(dt)<flat_after:
            ignored+=1
            continue

        entry_ts=int(dt)+lat_us
        exit_ts=entry_ts+hold_us+lat_us
        ei=_exact_position(ts,entry_ts)
        xi=_exact_position(ts,exit_ts)

        if not bool(valid[ei]) or not bool(valid[xi]):
            raise P0Error(f"book_invalid:{dt}:{latency_ms}")

        esp=_spread_bps(float(b[ei]),float(q[ei]))
        xsp=_spread_bps(float(b[xi]),float(q[xi]))

        out.append(TradeAudit(
            action_index=int(i),
            action=int(act),
            decision_timestamp_us=int(dt),
            entry_timestamp_us=entry_ts,
            exit_timestamp_us=exit_ts,
            entry_index=ei,
            exit_index=xi,
            entry_spread_bps=esp,
            exit_spread_bps=xsp,
        ))
        flat_after=exit_ts

    return tuple(out),int(ignored)

def public_summary(trades:Sequence[TradeAudit],ignored:int,total_actions:int):
    longs=sum(int(t.action==ACTION_LONG) for t in trades)
    shorts=sum(int(t.action==ACTION_SHORT) for t in trades)
    entry_spreads=np.asarray([t.entry_spread_bps for t in trades],dtype=np.float64)
    exit_spreads=np.asarray([t.exit_spread_bps for t in trades],dtype=np.float64)

    if len(trades)==0:
        raise P0Error("no_trades")
    if not np.all(np.isfinite(entry_spreads)) or not np.all(np.isfinite(exit_spreads)):
        raise P0Error("nonfinite_spread")
    if np.any(entry_spreads<0) or np.any(exit_spreads<0):
        raise P0Error("negative_spread")

    return {
        "raw_action_count":int(total_actions),
        "accepted_flat_only_trades":int(len(trades)),
        "ignored_overlap_actions":int(ignored),
        "long_trades":int(longs),
        "short_trades":int(shorts),
        "entry_spread_finite_nonnegative":True,
        "exit_spread_finite_nonnegative":True,
        "first_decision_timestamp_us":int(trades[0].decision_timestamp_us),
        "last_decision_timestamp_us":int(trades[-1].decision_timestamp_us),
        "first_entry_timestamp_us":int(trades[0].entry_timestamp_us),
        "last_exit_timestamp_us":int(trades[-1].exit_timestamp_us),
    }

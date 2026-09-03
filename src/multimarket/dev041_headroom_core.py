from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from . import dev030_first_passage as fp

HORIZONS_SECONDS=(60,120,300,600,900,1800)
BARRIERS_BPS=(8,12,16,24,32)
C1_COST_BPS=10.0
C2_COST_BPS=16.0

class HeadroomError(RuntimeError):
    pass

@dataclass(frozen=True)
class Candidate:
    candidate_id:str
    horizon_seconds:int
    barrier_bps:int

CANDIDATES=tuple(
    Candidate(f"H{h}_B{b}",h,b)
    for h in HORIZONS_SECONDS
    for b in BARRIERS_BPS
)
BY_ID={c.candidate_id:c for c in CANDIDATES}

@dataclass(frozen=True)
class OracleTrade:
    day:str
    side:str
    decision_timestamp_us:int
    entry_timestamp_us:int
    touch_timestamp_us:int
    response_exit_timestamp_us:int
    nominal_barrier_bps:float
    touch_gross_bps:float
    barrier_overshoot_bps:float
    realized_gross_bps:float
    execution_leakage_bps:float
    time_to_first_barrier_ms:float

def registry():
    return [
        {
            "candidate_id":c.candidate_id,
            "horizon_seconds":c.horizon_seconds,
            "barrier_bps":c.barrier_bps,
        }
        for c in CANDIDATES
    ]

def _profit_factor(values:np.ndarray)->float:
    pos=float(np.sum(values[values>0]))
    neg=float(np.sum(values[values<0]))
    if neg==0:
        return float("inf") if pos>0 else 0.0
    return float(pos/abs(neg))

def _max_drawdown(values:np.ndarray)->float:
    eq=np.concatenate(([0.0],np.cumsum(values,dtype=np.float64)))
    peaks=np.maximum.accumulate(eq)
    return float(np.max(peaks-eq))

def _max_losing_streak(values:np.ndarray)->int:
    best=cur=0
    for v in values.tolist():
        if v<0:
            cur+=1
            best=max(best,cur)
        else:
            cur=0
    return int(best)

def _day_stats(values:np.ndarray)->dict[str,Any]:
    return {
        "mean":float(np.mean(values)),
        "median":float(np.median(values)),
        "total":float(np.sum(values)),
        "pf":_profit_factor(values),
        "win_rate":float(np.mean(values>0)),
        "max_drawdown":_max_drawdown(values),
        "max_losing_streak":_max_losing_streak(values),
    }

def records_summary(records:Sequence[Mapping[str,Any]]):
    valid=invalid=longs=shorts=none=amb=0
    times=[]
    long_times=[]
    short_times=[]
    for r in records:
        if r.get("target_valid") is True:
            valid+=1
            lab=r.get("label")
            if lab==fp.LONG_FIRST:
                longs+=1
                t=float(r["time_to_first_barrier_ms"])
                times.append(t);long_times.append(t)
            elif lab==fp.SHORT_FIRST:
                shorts+=1
                t=float(r["time_to_first_barrier_ms"])
                times.append(t);short_times.append(t)
            elif lab==fp.NONE:
                none+=1
            else:
                raise HeadroomError("unknown_valid_label")
        else:
            invalid+=1
            if r.get("same_row_ambiguous") is True:
                amb+=1
    touch=longs+shorts
    def tstats(v):
        if not v:
            return {"median_ms":None,"p90_ms":None}
        a=np.asarray(v,dtype=np.float64)
        return {
            "median_ms":float(np.median(a)),
            "p90_ms":float(np.quantile(a,0.90,method="higher")),
        }
    return {
        "valid_decisions":valid,
        "invalid_decisions":invalid,
        "long_first_count":longs,
        "short_first_count":shorts,
        "none_count":none,
        "ambiguity_count":amb,
        "clean_touch_count":touch,
        "clean_touch_prevalence":float(touch/valid) if valid else None,
        "time_to_first_passage":tstats(times),
        "long_time_to_first_passage":tstats(long_times),
        "short_time_to_first_passage":tstats(short_times),
    }

def oracle_trades_from_records(
    day:str,
    records:Sequence[Mapping[str,Any]],
    *,
    raw_timestamps_us,
    bid,
    ask,
    book_valid,
    response_latency_ms:int=250,
):
    if int(response_latency_ms)!=250:
        raise HeadroomError("response_latency_not_frozen")
    ts=np.asarray(raw_timestamps_us,dtype=np.int64)
    b=np.asarray(bid,dtype=np.float64)
    a=np.asarray(ask,dtype=np.float64)
    valid=np.asarray(book_valid,dtype=bool)
    if ts.ndim!=1 or b.ndim!=1 or a.ndim!=1 or valid.ndim!=1:
        raise HeadroomError("raw_shape")
    if not (len(ts)==len(b)==len(a)==len(valid)):
        raise HeadroomError("raw_length")
    if len(ts)==0 or np.any(np.diff(ts)<=0):
        raise HeadroomError("raw_chronology")

    def pos(target:int)->int:
        i=int(np.searchsorted(ts,int(target),side="left"))
        if i>=len(ts) or int(ts[i])!=int(target):
            raise HeadroomError(f"raw_timestamp_missing:{target}")
        return i

    out=[]
    response_unavailable=0
    for r in records:
        if r.get("target_valid") is not True:
            continue
        lab=r.get("label")
        if lab not in (fp.LONG_FIRST,fp.SHORT_FIRST):
            continue

        touch_ts=int(r["barrier_reached_timestamp_us"])
        entry_ts=int(r["entry_timestamp_us"])
        response_ts=touch_ts+int(response_latency_ms)*1000

        try:
            ei=pos(entry_ts)
            ti=pos(touch_ts)
            ri=pos(response_ts)
        except HeadroomError:
            response_unavailable+=1
            continue

        if not bool(valid[ei]) or not bool(valid[ti]) or not bool(valid[ri]):
            response_unavailable+=1
            continue

        vals=(float(b[ei]),float(a[ei]),float(b[ti]),float(a[ti]),float(b[ri]),float(a[ri]))
        if any((not np.isfinite(v) or v<=0) for v in vals):
            response_unavailable+=1
            continue
        if float(b[ei])>float(a[ei]) or float(b[ti])>float(a[ti]) or float(b[ri])>float(a[ri]):
            response_unavailable+=1
            continue

        if lab==fp.LONG_FIRST:
            touch_gross=float(10000.0*np.log(float(b[ti])/float(a[ei])))
            realized=float(10000.0*np.log(float(b[ri])/float(a[ei])))
            side="LONG"
        else:
            touch_gross=float(10000.0*np.log(float(b[ei])/float(a[ti])))
            realized=float(10000.0*np.log(float(b[ei])/float(a[ri])))
            side="SHORT"

        barrier=float(r["barrier_bps"])
        if touch_gross+1e-10 < barrier:
            raise HeadroomError("touch_gross_below_barrier")

        out.append(OracleTrade(
            day=day,
            side=side,
            decision_timestamp_us=int(r["decision_timestamp_us"]),
            entry_timestamp_us=entry_ts,
            touch_timestamp_us=touch_ts,
            response_exit_timestamp_us=response_ts,
            nominal_barrier_bps=barrier,
            touch_gross_bps=touch_gross,
            barrier_overshoot_bps=float(touch_gross-barrier),
            realized_gross_bps=realized,
            execution_leakage_bps=float(touch_gross-realized),
            time_to_first_barrier_ms=float(r["time_to_first_barrier_ms"]),
        ))
    return tuple(out),int(response_unavailable)

def flat_only(trades:Sequence[OracleTrade]):
    ordered=sorted(trades,key=lambda t:(t.decision_timestamp_us,t.exit_timestamp_us,t.side))
    accepted=[]
    ignored=0
    flat_after=-1
    for t in ordered:
        if t.decision_timestamp_us<flat_after:
            ignored+=1
            continue
        accepted.append(t)
        flat_after=t.response_exit_timestamp_us
    return tuple(accepted),int(ignored)

def execution_decomposition(trades:Sequence[OracleTrade]):
    if not trades:
        raise HeadroomError("no_trades")
    touch=np.asarray([t.touch_gross_bps for t in trades],dtype=np.float64)
    overshoot=np.asarray([t.barrier_overshoot_bps for t in trades],dtype=np.float64)
    leakage=np.asarray([t.execution_leakage_bps for t in trades],dtype=np.float64)
    realized=np.asarray([t.realized_gross_bps for t in trades],dtype=np.float64)
    def stats(a):
        return {
            "mean":float(np.mean(a)),
            "median":float(np.median(a)),
            "p90":float(np.quantile(a,0.90,method="higher")),
        }
    return {
        "nominal_barrier_bps":float(trades[0].nominal_barrier_bps),
        "touch_gross_bps":stats(touch),
        "barrier_overshoot_bps":stats(overshoot),
        "execution_leakage_bps":stats(leakage),
        "fraction_leakage_positive":float(np.mean(leakage>0)),
        "fraction_leakage_negative":float(np.mean(leakage<0)),
        "realized_gross_bps":stats(realized),
    }

def economics(trades:Sequence[OracleTrade],cost_bps:float):
    if not trades:
        raise HeadroomError("no_trades")
    gross=np.asarray([t.realized_gross_bps for t in trades],dtype=np.float64)
    net=gross-float(cost_bps)
    days=tuple(dict.fromkeys(t.day for t in trades))
    per_day=[]
    positive_contrib=[]
    for d in days:
        vals=np.asarray([net[i] for i,t in enumerate(trades) if t.day==d],dtype=np.float64)
        rec=_day_stats(vals)
        rec.update({"day":d,"trades":int(len(vals)),"positive":bool(rec["total"]>0)})
        per_day.append(rec)
        positive_contrib.append(max(0.0,float(rec["total"])))
    loo=[]
    for omit in days:
        vals=np.asarray([net[i] for i,t in enumerate(trades) if t.day!=omit],dtype=np.float64)
        loo.append({
            "omitted_day":omit,
            "mean_net_bps":float(np.mean(vals)) if len(vals) else None,
        })
    pos_total=float(sum(positive_contrib))
    concentration=float(max(positive_contrib)/pos_total) if pos_total>0 else None
    return {
        "trade_count":int(len(trades)),
        "trades_per_day":float(len(trades)/len(days)),
        "mean_gross_bps":float(np.mean(gross)),
        "median_gross_bps":float(np.median(gross)),
        "total_gross_bps":float(np.sum(gross)),
        "gross_pf":_profit_factor(gross),
        "gross_win_rate":float(np.mean(gross>0)),
        "cost_bps":float(cost_bps),
        "mean_net_bps":float(np.mean(net)),
        "median_net_bps":float(np.median(net)),
        "total_net_bps":float(np.sum(net)),
        "net_pf":_profit_factor(net),
        "net_win_rate":float(np.mean(net>0)),
        "max_drawdown_bps":_max_drawdown(net),
        "max_losing_streak":_max_losing_streak(net),
        "positive_days":int(sum(x["positive"] for x in per_day)),
        "per_day":per_day,
        "leave_one_day_out":loo,
        "minimum_daily_net_bps":float(min(x["total"] for x in per_day)),
        "median_daily_net_bps":float(np.median([x["total"] for x in per_day])),
        "minimum_loo_mean_net_bps":float(min(x["mean_net_bps"] for x in loo)),
        "max_positive_day_contribution_fraction":concentration,
    }

def eligibility(record:Mapping[str,Any])->tuple[bool,dict[str,bool]]:
    s=record["support"]
    a=record["activity"]
    c1=record["c1"]
    c2=record["c2"]
    gates={
        "valid_support_ge_6000":int(s["valid_decisions"])>=6000,
        "accepted_oracle_trades_ge_100":int(a["accepted_oracle_trades"])>=100,
        "trades_all_7_days":len(c1["per_day"])==7 and all(int(x["trades"])>0 for x in c1["per_day"]),
        "long_oracle_positive":int(a["long_oracle_trades"])>0,
        "short_oracle_positive":int(a["short_oracle_trades"])>0,
        "touch_prevalence_ge_002":float(s["clean_touch_prevalence"])>=0.02,
        "c1_mean_net_gt_0":float(c1["mean_net_bps"])>0,
        "c1_total_net_gt_0":float(c1["total_net_bps"])>0,
        "c1_positive_days_ge_6":int(c1["positive_days"])>=6,
        "c1_all_loo_positive":all(float(x["mean_net_bps"])>0 for x in c1["leave_one_day_out"]),
        "c2_mean_net_gt_0":float(c2["mean_net_bps"])>0,
        "c2_total_net_gt_0":float(c2["total_net_bps"])>0,
        "c2_positive_days_ge_5":int(c2["positive_days"])>=5,
        "c2_all_loo_positive":all(float(x["mean_net_bps"])>0 for x in c2["leave_one_day_out"]),
        "c1_concentration_le_040":(
            c1["max_positive_day_contribution_fraction"] is not None
            and float(c1["max_positive_day_contribution_fraction"])<=0.40
        ),
        "c2_concentration_le_040":(
            c2["max_positive_day_contribution_fraction"] is not None
            and float(c2["max_positive_day_contribution_fraction"])<=0.40
        ),
    }
    return bool(all(gates.values())),gates

def rank(records:Sequence[Mapping[str,Any]]):
    eligible=[r for r in records if r["eligible"]]
    return sorted(
        eligible,
        key=lambda r:(
            -float(r["c2"]["minimum_daily_net_bps"]),
            -float(r["c2"]["median_daily_net_bps"]),
            -float(r["c2"]["total_net_bps"]),
            -float(r["c2"]["minimum_loo_mean_net_bps"]),
            -float(r["activity"]["oracle_trades_per_day"]),
            int(r["horizon_seconds"]),
            -int(r["barrier_bps"]),
            str(r["candidate_id"]),
        ),
    )

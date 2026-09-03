from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

ACTION_SHORT=1
ACTION_LONG=2

class P1Error(RuntimeError):
    pass

@dataclass(frozen=True)
class TradeEconomic:
    day:str
    action:int
    decision_timestamp_us:int
    entry_timestamp_us:int
    exit_timestamp_us:int
    entry_price:float
    exit_price:float
    entry_spread_bps:float
    exit_spread_bps:float
    gross_bps:float

def gross_bps(action:int,entry_bid:float,entry_ask:float,exit_bid:float,exit_ask:float)->float:
    vals=(entry_bid,entry_ask,exit_bid,exit_ask)
    if any((not np.isfinite(v) or v<=0) for v in vals):
        raise P1Error("invalid_price")
    if action==ACTION_LONG:
        return float(10000.0*np.log(exit_bid/entry_ask))
    if action==ACTION_SHORT:
        return float(10000.0*np.log(entry_bid/exit_ask))
    raise P1Error("invalid_action")

def _profit_factor(values:np.ndarray)->float:
    pos=float(np.sum(values[values>0]))
    neg=float(np.sum(values[values<0]))
    if neg==0.0:
        return float("inf") if pos>0 else 0.0
    return float(pos/abs(neg))

def _max_drawdown(values:np.ndarray)->float:
    eq=np.concatenate(([0.0],np.cumsum(values,dtype=np.float64)))
    peaks=np.maximum.accumulate(eq)
    return float(np.max(peaks-eq))

def _max_losing_streak(values:np.ndarray)->int:
    best=cur=0
    for v in values.tolist():
        if float(v)<0:
            cur+=1
            best=max(best,cur)
        else:
            cur=0
    return int(best)

def scenario_metrics(trades:Sequence[TradeEconomic],*,fee_roundtrip_bps:float,slippage_per_side_bps:float):
    if len(trades)==0:
        raise P1Error("no_trades")
    gross=np.asarray([t.gross_bps for t in trades],dtype=np.float64)
    if not np.all(np.isfinite(gross)):
        raise P1Error("nonfinite_gross")
    net=gross-float(fee_roundtrip_bps)-2.0*float(slippage_per_side_bps)
    days=tuple(dict.fromkeys(t.day for t in trades))
    per_day=[]
    positive_contrib=[]
    for d in days:
        vals=np.asarray([net[i] for i,t in enumerate(trades) if t.day==d],dtype=np.float64)
        s=float(np.sum(vals))
        per_day.append({"day":d,"trades":int(len(vals)),"net_bps":s,"positive":bool(s>0)})
        positive_contrib.append(max(0.0,s))
    total_pos=float(sum(positive_contrib))
    concentration=float(max(positive_contrib)/total_pos) if total_pos>0 else None
    cumulative_gross=np.concatenate(([0.0],np.cumsum(gross,dtype=np.float64)))
    cumulative_net=np.concatenate(([0.0],np.cumsum(net,dtype=np.float64)))
    return {
        "trade_count":int(len(trades)),
        "trades_per_day_mean":float(len(trades)/len(days)),
        "mean_gross_bps":float(np.mean(gross)),
        "median_gross_bps":float(np.median(gross)),
        "total_gross_bps":float(np.sum(gross)),
        "gross_win_rate":float(np.mean(gross>0)),
        "gross_profit_factor":_profit_factor(gross),
        "fee_roundtrip_bps":float(fee_roundtrip_bps),
        "slippage_per_side_bps":float(slippage_per_side_bps),
        "mean_net_bps":float(np.mean(net)),
        "median_net_bps":float(np.median(net)),
        "total_net_bps":float(np.sum(net)),
        "net_win_rate":float(np.mean(net>0)),
        "profit_factor":_profit_factor(net),
        "max_drawdown_bps":_max_drawdown(net),
        "max_consecutive_losing_trades":_max_losing_streak(net),
        "positive_days":int(sum(x["positive"] for x in per_day)),
        "per_day":per_day,
        "mean_day_net_bps":float(np.mean([x["net_bps"] for x in per_day])),
        "median_day_net_bps":float(np.median([x["net_bps"] for x in per_day])),
        "min_day_net_bps":float(np.min([x["net_bps"] for x in per_day])),
        "max_day_net_bps":float(np.max([x["net_bps"] for x in per_day])),
        "max_positive_day_contribution_fraction":concentration,
        "roundtrip_cost_break_even_bps":float(np.mean(gross)),
        "max_extra_slippage_per_side_bps":float(max(0.0,(float(np.mean(gross))-float(fee_roundtrip_bps))/2.0)),
        "sum_positive_gross_bps":float(np.sum(gross[gross>0])),
        "sum_positive_net_bps":float(np.sum(net[net>0])),
        "sum_negative_net_bps":float(np.sum(net[net<0])),
        "cumulative_gross_bps_curve":[float(v) for v in cumulative_gross.tolist()],
        "cumulative_net_bps_curve":[float(v) for v in cumulative_net.tolist()],
    }

def classify(primary:dict,lat500_gross_mean:float)->tuple[str,dict[str,bool],str]:
    gates={
        "accepted_trades_ge_100":int(primary["trade_count"])>=100,
        "all_four_days_present":len(primary["per_day"])==4 and all(int(x["trades"])>0 for x in primary["per_day"]),
        "mean_gross_gt_0":float(primary["mean_gross_bps"])>0.0,
        "mean_net_gt_0":float(primary["mean_net_bps"])>0.0,
        "profit_factor_gt_1_05":float(primary["profit_factor"])>1.05,
        "positive_days_ge_3":int(primary["positive_days"])>=3,
        "total_net_gt_0":float(primary["total_net_bps"])>0.0,
        "drawdown_below_positive_profit":float(primary["max_drawdown_bps"])<float(primary["sum_positive_gross_bps"]),
        "lat500_mean_gross_gt_0":float(lat500_gross_mean)>0.0,
        "positive_day_concentration_le_060":(
            primary["max_positive_day_contribution_fraction"] is not None
            and float(primary["max_positive_day_contribution_fraction"])<=0.60
        ),
    }
    if not gates["mean_gross_gt_0"]:
        taxonomy="F0_NO_GROSS_EXECUTABLE_EDGE"
    elif not gates["mean_net_gt_0"]:
        taxonomy="F1_GROSS_POSITIVE_COSTS_KILL_EDGE"
    elif not all(gates.values()):
        taxonomy="F2_NET_POSITIVE_BUT_UNSTABLE"
    else:
        taxonomy="PASS"
    status="DEV040_P1_ECONOMIC_BASELINE_PASS" if all(gates.values()) else "DEV040_P1_ECONOMIC_BASELINE_FAIL"
    return status,gates,taxonomy

from __future__ import annotations

import numpy as np

from multimarket import dev030_first_passage as fp
from multimarket import dev041_headroom_core as core
from multimarket import dev041_headroom_harness as harness
from multimarket import dev041_headroom_runner as runner

def test_registry_exact_30():
    assert len(core.CANDIDATES)==30
    assert core.HORIZONS_SECONDS==(60,120,300,600,900,1800)
    assert core.BARRIERS_BPS==(8,12,16,24,32)
    assert core.CANDIDATES[0].candidate_id=="H60_B8"
    assert core.CANDIDATES[-1].candidate_id=="H1800_B32"

def test_records_summary():
    rows=[
        {
            "target_valid":True,"label":fp.LONG_FIRST,
            "time_to_first_barrier_ms":1000.0,
        },
        {
            "target_valid":True,"label":fp.SHORT_FIRST,
            "time_to_first_barrier_ms":2000.0,
        },
        {"target_valid":True,"label":fp.NONE},
        {
            "target_valid":False,"label":None,
            "same_row_ambiguous":True,
        },
    ]
    z=core.records_summary(rows)
    assert z["valid_decisions"]==3
    assert z["invalid_decisions"]==1
    assert z["long_first_count"]==1
    assert z["short_first_count"]==1
    assert z["none_count"]==1
    assert z["ambiguity_count"]==1
    assert z["clean_touch_prevalence"]==2/3

def test_oracle_trade_uses_actual_executable_touch_return():
    ts=np.array([0,250_000,500_000,750_000],dtype=np.int64)
    bid=np.array([99.9,100.0,100.9,101.1])
    ask=np.array([100.0,100.1,101.0,101.2])
    rec=[{
        "target_valid":True,
        "label":fp.LONG_FIRST,
        "barrier_reached_timestamp_us":750_000,
        "entry_timestamp_us":250_000,
        "decision_timestamp_us":0,
        "barrier_bps":100.0,
        "time_to_first_barrier_ms":500.0,
    }]
    valid=np.ones(len(ts),dtype=bool)
    trades,unavailable=core.oracle_trades_from_records(
        "2026-01-01",rec,
        raw_timestamps_us=ts,bid=bid,ask=ask,book_valid=valid,
        response_latency_ms=250,
    )
    assert unavailable==1  # touch at 750ms -> response at 1000ms is missing
    assert len(trades)==0

def _ot(day,side,decision,entry,touch,response,touch_gross,realized):
    return core.OracleTrade(
        day,side,decision,entry,touch,response,16.0,touch_gross,
        touch_gross-16.0,realized,touch_gross-realized,
        float(touch-entry)/1000.0,
    )

def test_response_latency_execution_decomposition():
    ts=np.array([0,250_000,500_000,750_000,1_000_000],dtype=np.int64)
    bid=np.array([99.9,100.0,100.9,101.1,100.8])
    ask=np.array([100.0,100.1,101.0,101.2,100.9])
    valid=np.ones(len(ts),dtype=bool)
    rec=[{
        "target_valid":True,
        "label":fp.LONG_FIRST,
        "barrier_reached_timestamp_us":750_000,
        "entry_timestamp_us":250_000,
        "decision_timestamp_us":0,
        "barrier_bps":90.0,
        "time_to_first_barrier_ms":500.0,
    }]
    trades,unavailable=core.oracle_trades_from_records(
        "2026-01-01",rec,
        raw_timestamps_us=ts,bid=bid,ask=ask,book_valid=valid,
        response_latency_ms=250,
    )
    assert unavailable==0
    assert len(trades)==1
    t=trades[0]
    touch=10000*np.log(101.1/100.1)
    realized=10000*np.log(100.8/100.1)
    assert abs(t.touch_gross_bps-touch)<1e-12
    assert abs(t.realized_gross_bps-realized)<1e-12
    assert abs(t.barrier_overshoot_bps-(touch-90.0))<1e-12
    assert abs(t.execution_leakage_bps-(touch-realized))<1e-12
    z=core.execution_decomposition(trades)
    assert z["fraction_leakage_positive"]==1.0

def test_flat_only_uses_response_exit():
    t1=_ot("2026-01-01","LONG",0,250_000,8_000_000,10_000_000,20,18)
    t2=_ot("2026-01-01","SHORT",9_000_000,9_250_000,9_500_000,9_750_000,20,19)
    t3=_ot("2026-01-01","LONG",11_000_000,11_250_000,11_500_000,12_000_000,20,20)
    accepted,ignored=core.flat_only((t1,t2,t3))
    assert accepted==(t1,t3)
    assert ignored==1

def _seven_day_trades(gross):
    out=[]
    for d in range(1,8):
        day=f"2026-0{d}-01"
        for k in range(20):
            decision=d*1_000_000_000+k*2_000_000
            entry=decision+250_000
            touch=decision+750_000
            response=decision+1_000_000
            out.append(_ot(
                day,"LONG" if k%2==0 else "SHORT",
                decision,entry,touch,response,gross,gross,
            ))
    return tuple(out)

def test_economics_and_eligibility():
    trades=_seven_day_trades(40.0)
    gross=core.economics(trades,0)
    c1=core.economics(trades,10)
    c2=core.economics(trades,16)
    rec={
        "candidate_id":"H60_B32",
        "horizon_seconds":60,
        "barrier_bps":32,
        "support":{
            "valid_decisions":7000,
            "clean_touch_prevalence":0.20,
        },
        "activity":{
            "accepted_oracle_trades":len(trades),
            "oracle_trades_per_day":20.0,
            "long_oracle_trades":70,
            "short_oracle_trades":70,
        },
        "gross":gross,"c1":c1,"c2":c2,
    }
    eligible,gates=core.eligibility(rec)
    assert eligible
    assert all(gates.values())

def test_rank_prefers_loo_before_frequency():
    def make(cid,h,b,daily,total,loo,freq):
        c2={
            "minimum_daily_net_bps":daily,
            "median_daily_net_bps":daily,
            "total_net_bps":total,
            "minimum_loo_mean_net_bps":loo,
        }
        return {
            "candidate_id":cid,"horizon_seconds":h,"barrier_bps":b,
            "eligible":True,"c2":c2,
            "activity":{"oracle_trades_per_day":freq},
        }
    a=make("H60_B24",60,24,100,1000,5,100)
    b=make("H120_B32",120,32,100,1000,10,10)
    ranked=core.rank((a,b))
    assert ranked[0]["candidate_id"]=="H120_B32"

def test_forward_guards_false():
    assert not any(runner.FORWARD_GUARDS.values())

def test_harness_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)

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
    trades=core.oracle_trades_from_records(
        "2026-01-01",rec,raw_timestamps_us=ts,bid=bid,ask=ask
    )
    assert len(trades)==1
    expected=10000*np.log(101.1/100.1)
    assert abs(trades[0].gross_bps-expected)<1e-12

def test_flat_only_overlap():
    t1=core.OracleTrade("2026-01-01","LONG",0,250_000,10_000_000,20,9750)
    t2=core.OracleTrade("2026-01-01","SHORT",5_000_000,5_250_000,8_000_000,20,2750)
    t3=core.OracleTrade("2026-01-01","LONG",11_000_000,11_250_000,12_000_000,20,750)
    accepted,ignored=core.flat_only((t1,t2,t3))
    assert accepted==(t1,t3)
    assert ignored==1

def _seven_day_trades(gross):
    out=[]
    for d in range(1,8):
        day=f"2026-0{d}-01"
        for k in range(20):
            out.append(core.OracleTrade(
                day,"LONG" if k%2==0 else "SHORT",
                d*1_000_000_000+k*2_000_000,
                d*1_000_000_000+k*2_000_000+250_000,
                d*1_000_000_000+k*2_000_000+1_000_000,
                gross,
                750.0,
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

def test_rank_prefers_stronger_min_daily_c2():
    def make(cid,h,b,daily):
        c2={
            "minimum_daily_net_bps":daily,
            "median_daily_net_bps":daily,
            "total_net_bps":daily*7,
            "minimum_loo_mean_net_bps":daily/20,
        }
        return {
            "candidate_id":cid,"horizon_seconds":h,"barrier_bps":b,
            "eligible":True,"c2":c2,
            "activity":{"oracle_trades_per_day":20.0},
        }
    a=make("H60_B24",60,24,100)
    b=make("H120_B32",120,32,120)
    ranked=core.rank((a,b))
    assert ranked[0]["candidate_id"]=="H120_B32"

def test_forward_guards_false():
    assert not any(runner.FORWARD_GUARDS.values())

def test_harness_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)

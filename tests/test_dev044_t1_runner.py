from __future__ import annotations

from types import SimpleNamespace
import numpy as np

from multimarket import dev044_t0_strategy_contract as c
from multimarket import dev044_t0f_gate_bootstrap as g
from multimarket import dev044_t1_execution as e
from multimarket import dev044_t1_runner as r


def test_frozen_parent_identities():
    assert r.T0E_MANIFEST_BYTES==23401
    assert r.T0E_MANIFEST_SHA256=="66864b5e90f3c5ca7d53b5a149cdcb65223eac04c04e68511fc998a0efcb84e8"
    assert set(r.ACTION_IDENTITIES)==set(r.DAYS)
    assert r.DAYS==("2026-04-01","2026-05-01","2026-06-01","2026-07-01")


def test_ranking_key_follows_t0f_priority():
    a=g.EconomicMetrics(
        candidate_id="T01U",
        execution_integrity_failures=0,
        accepted_trades=100,
        accepted_by_day=(25,25,25,25),
        accepted_long=50,
        accepted_short=50,
        pooled_primary_net_expectancy_bps=2.0,
        primary_profit_factor=1.2,
        positive_days=4,
        loo_primary_net_expectancy_bps=(1.0,1.0,1.0,1.0),
        positive_day_concentration=0.4,
        max_drawdown_bps=100.0,
        stress_cost_net_expectancy_bps=0.5,
        latency_stress_net_expectancy_bps=0.5,
        median_daily_primary_net_bps=10.0,
    )
    b=g.EconomicMetrics(**{**a.__dict__,
        "candidate_id":"T02U",
        "loo_primary_net_expectancy_bps":(2.0,2.0,2.0,2.0),
    })
    assert r._ranking_key(b)<r._ranking_key(a)


def test_exact_four_day_metrics_includes_zero_trade_days():
    trade=SimpleNamespace(day="2026-04-01",gross_bps=20.0)
    by_day,daily,loo,conc=r._exact_four_day_metrics((trade,),10.0)
    assert by_day==(1,0,0,0)
    assert daily==(10.0,0.0,0.0,0.0)
    assert loo[0]==0.0
    assert conc==1.0


def test_paired_bootstrap_is_deterministic():
    a=np.arange(24,dtype=float)
    u=np.zeros(24,dtype=float)
    x=r._paired_ci(a,u,seed=7,reps=200)
    y=r._paired_ci(a,u,seed=7,reps=200)
    assert x==y
    assert x["ci95_low"]<=x["mean_block_delta_bps"]<=x["ci95_high"]


def test_execution_shell_constants_match_t0f():
    assert e.HORIZON_SECONDS==1800
    assert e.BARRIER_BPS==32.0
    assert e.PRIMARY_ENTRY_LATENCY_MS==250
    assert e.PRIMARY_RESPONSE_LATENCY_MS==250
    assert e.LATENCY_STRESS_ENTRY_MS==500
    assert e.LATENCY_STRESS_RESPONSE_MS==500
    assert g.PRIMARY_COST_BPS_RT==10.0
    assert g.STRESS_COST_BPS_RT==16.0

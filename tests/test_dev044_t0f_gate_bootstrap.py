from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev044_t0_strategy_contract as c
from multimarket import dev044_t0f_gate_bootstrap as g


def test_mechanical_gate_thresholds():
    assert g.mechanical_eligible(
        g.MechanicalSupport("T04A",333,(109,52,61,111))
    )
    assert not g.mechanical_eligible(
        g.MechanicalSupport("T12A",91,(2,3,30,56))
    )
    assert not g.mechanical_eligible(
        g.MechanicalSupport("T03U",23,(4,1,12,6))
    )
    assert not g.mechanical_eligible(
        g.MechanicalSupport("T06U",0,(0,0,0,0))
    )


def good_metrics(cid="T01U"):
    return g.EconomicMetrics(
        candidate_id=cid,
        execution_integrity_failures=0,
        accepted_trades=80,
        accepted_by_day=(20,20,20,20),
        accepted_long=40,
        accepted_short=40,
        pooled_primary_net_expectancy_bps=2.0,
        primary_profit_factor=1.20,
        positive_days=4,
        loo_primary_net_expectancy_bps=(1.1,1.2,1.3,1.4),
        positive_day_concentration=0.40,
        max_drawdown_bps=100.0,
        stress_cost_net_expectancy_bps=0.5,
        latency_stress_net_expectancy_bps=0.4,
        median_daily_primary_net_bps=10.0,
    )


def test_all_economic_gates_can_pass():
    x=good_metrics()
    r=g.economic_gate_results(x)
    assert all(r.values())
    assert g.economic_eligible(x)


@pytest.mark.parametrize(
    "field,value,key",
    [
        ("execution_integrity_failures",1,"execution_integrity"),
        ("accepted_trades",39,"accepted_trades_pooled"),
        ("accepted_long",9,"accepted_long"),
        ("accepted_short",9,"accepted_short"),
        ("pooled_primary_net_expectancy_bps",0.0,"primary_net_positive"),
        ("primary_profit_factor",1.09,"primary_profit_factor"),
        ("positive_days",2,"positive_days"),
        ("positive_day_concentration",0.61,"positive_day_concentration"),
        ("max_drawdown_bps",321.0,"max_drawdown"),
        ("stress_cost_net_expectancy_bps",0.0,"stress_cost_positive"),
        ("latency_stress_net_expectancy_bps",0.0,"latency_stress_positive"),
    ],
)
def test_individual_economic_gate_failures(field,value,key):
    x=good_metrics()
    d=x.__dict__.copy()
    d[field]=value
    if field in ("accepted_long","accepted_short"):
        # preserve side-sum invariant.
        other="accepted_short" if field=="accepted_long" else "accepted_long"
        d[other]=80-value
    y=g.EconomicMetrics(**d)
    assert g.economic_gate_results(y)[key] is False
    assert not g.economic_eligible(y)


def test_each_day_and_loo_gates():
    d=good_metrics().__dict__.copy()
    d["accepted_by_day"]=(4,20,20,36)
    y=g.EconomicMetrics(**d)
    assert g.economic_gate_results(y)["accepted_trades_each_day"] is False

    d=good_metrics().__dict__.copy()
    d["loo_primary_net_expectancy_bps"]=(1.0,0.0,1.0,1.0)
    y=g.EconomicMetrics(**d)
    assert g.economic_gate_results(y)["all_loo_positive"] is False


def test_ranking_tuple_prefers_stronger_min_loo():
    a=good_metrics("T01U")
    d=a.__dict__.copy()
    d["candidate_id"]="T02U"
    d["loo_primary_net_expectancy_bps"]=(2.0,2.0,2.0,2.0)
    b=g.EconomicMetrics(**d)
    assert g.ranking_tuple(b)[:-1] > g.ranking_tuple(a)[:-1]


def test_maxstat_requires_full_32_family():
    with pytest.raises(g.T0FGateError):
        g.block_maxstat_test({"T01U":[0.0]*24},reps=10)


def test_maxstat_is_deterministic_and_bounded():
    rng=np.random.default_rng(123)
    x={}
    for j,cid in enumerate(c.CANDIDATE_IDS):
        vals=rng.normal(0,1,24)
        if cid=="T01U":
            vals=vals+2.0
        x[cid]=vals
    r1=g.block_maxstat_test(x,reps=200,seed=7)
    r2=g.block_maxstat_test(x,reps=200,seed=7)
    assert r1==r2
    assert r1["candidate_ids"]==list(c.CANDIDATE_IDS)
    assert 0.0<r1["family_max_fwer_p"]<=1.0
    assert all(0.0<p<=1.0 for p in r1["fwer_pvalues"].values())


def test_constants_frozen():
    assert g.PRIMARY_COST_BPS_RT==10.0
    assert g.STRESS_COST_BPS_RT==16.0
    assert g.BLOCK_HOURS==4
    assert g.TOTAL_BLOCKS==24
    assert g.BOOTSTRAP_REPS==20_000
    assert g.BOOTSTRAP_SEED==440044
    assert g.FAMILY_ALPHA==0.05

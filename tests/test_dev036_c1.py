from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev036_c1_core as core
from multimarket import dev036_c1_runner as runner
from multimarket import dev036_c1_harness as harness

def _fold(fid,n,touch_n,seed):
    rng=np.random.default_rng(seed)
    y=np.zeros(n,dtype=np.int8)
    idx=np.arange(touch_n)
    y[idx]=1+(idx%2)
    pt=np.clip(rng.uniform(0.05,0.8,size=n),0,1)
    prior=0.5
    p3=np.clip(rng.uniform(0.35,0.65,size=n),0,1)
    p45=np.clip(0.5+(p3-0.5)*1.15,0.01,0.99)
    prev=np.array([0.8,0.1,0.1],dtype=float)
    return core.fold_composition(
        fold_id=fid,y3=y,training_prevalence=prev,
        p_touch=pt,training_p_long=prior,p3_long=p3,btc45_long=p45
    )

def test_compose_shapes_and_probability_sums():
    y=np.array([0,1,2,0],dtype=np.int8)
    c0,c1,c2,c3=core.compose_systems(
        y3=y,training_prevalence=np.array([.5,.25,.25]),
        p_touch=np.array([.1,.8,.9,.2]),training_p_long=.5,
        p3_long=np.array([.4,.6,.7,.3]),btc45_long=np.array([.45,.65,.75,.35])
    )
    for z in (c0,c1,c2,c3):
        assert z.shape==(4,3)
        assert np.allclose(z.sum(axis=1),1.0)

def test_comparison_contract():
    folds=(
        _fold(1,156,156,1),
        _fold(2,64,64,2),
        _fold(3,121,121,3),
        _fold(4,218,218,4),
    )
    z=core.comparison(folds,base_field="c2",test_field="c3")
    assert len(z["fold_log_loss_improvement"])==4
    assert len(z["leave_one_fold_out_log_loss_improvement"])==4

def test_temporal_null_exact_length_and_shifts():
    folds=(
        _fold(1,156,156,1),
        _fold(2,64,64,2),
        _fold(3,121,121,3),
        _fold(4,218,218,4),
    )
    z=core.directional_touch_temporal_null(folds,seed=7,replicates=19)
    assert len(z["shift_tuples"])==19
    assert len(z["null_delta_ll_32"])==19
    bounds=((10,146),(10,54),(10,111),(10,208))
    for row in z["shift_tuples"]:
        assert all(lo<=v<=hi for v,(lo,hi) in zip(row,bounds,strict=True))

def test_status_preexecution_failure():
    z={"pooled_log_loss_improvement":1,"pooled_brier_improvement":1,
       "pooled_macro_ap_improvement":1,"positive_fold_log_loss_improvements":4,
       "all_loo_log_loss_improvement_positive":True}
    n={"q95":0.1,"empirical_p":0.01}
    assert core.classify(reproduction_ok=False,vs_c2=z,vs_c1=z,null=n)==core.STATUS_PREEXEC

def test_primary_gate_failure():
    a={"pooled_log_loss_improvement":0.01,"pooled_brier_improvement":0.01,
       "pooled_macro_ap_improvement":0.01,"positive_fold_log_loss_improvements":4,
       "all_loo_log_loss_improvement_positive":True}
    n={"q95":0.02,"empirical_p":0.01}
    assert core.classify(reproduction_ok=True,vs_c2=a,vs_c1=a,null=n)==core.STATUS_FAIL_PRIMARY

def test_overall_gate_failure():
    primary={"pooled_log_loss_improvement":0.03,"pooled_brier_improvement":0.01,
       "pooled_macro_ap_improvement":0.01,"positive_fold_log_loss_improvements":4,
       "all_loo_log_loss_improvement_positive":True}
    overall=dict(primary);overall["pooled_brier_improvement"]=-0.01
    n={"q95":0.02,"empirical_p":0.01}
    assert core.classify(reproduction_ok=True,vs_c2=primary,vs_c1=overall,null=n)==core.STATUS_FAIL_OVERALL

def test_eligible_gate():
    z={"pooled_log_loss_improvement":0.03,"pooled_brier_improvement":0.01,
       "pooled_macro_ap_improvement":0.01,"positive_fold_log_loss_improvements":4,
       "all_loo_log_loss_improvement_positive":True}
    n={"q95":0.02,"empirical_p":0.01}
    assert core.classify(reproduction_ok=True,vs_c2=z,vs_c1=z,null=n)==core.STATUS_ELIGIBLE

def test_forward_guards_false():
    assert not any(runner.FORWARD_GUARDS.values())

def test_process_pool_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)

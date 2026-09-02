from __future__ import annotations

import numpy as np

from multimarket import dev037_p0_r1_coverage_core as core
from multimarket import dev037_p0_r1_coverage_harness as harness
from multimarket import dev037_p0_r1_coverage_runner as runner

def test_threshold_uses_prior_scores_only():
    warm=np.array([0.,1.,2.,3.,4.])
    scores=np.array([100.,0.])
    pl=np.array([.8,.2])
    thresholds,actions=core.rolling_quantile_actions(
        scores=scores,p_long=pl,warm_scores=warm,window=120
    )
    assert thresholds[0]==4.0
    # first score 100 is only available for second threshold.
    # With method="higher", q80([0,1,2,3,4,100]) is still 4.0.
    expected_second=float(np.quantile(
        np.array([0.,1.,2.,3.,4.,100.]),
        0.80,
        method="higher",
    ))
    assert thresholds[1]==expected_second
    assert thresholds[1]==4.0
    assert actions[0]==2
    assert actions[1]==0

def test_warm_start_truncated_to_window():
    warm=np.arange(1000,dtype=float)
    scores=np.linspace(0,1,20)
    pl=np.full(20,.8)
    r=core.summarize(scores=scores,p_long=pl,warm_scores=warm,window=120)
    assert r.warm_start_count==120
    assert len(r.thresholds)==20

def test_rolling60_length():
    a=np.zeros(100,dtype=np.int8)
    a[::5]=1
    z=core.rolling60_coverage(a)
    assert len(z)==41

def test_feasible_contract():
    scores=np.linspace(0,1,1000)
    pl=np.where(np.arange(1000)%2==0,.7,.3)
    warm=np.linspace(0,1,720)
    r=core.summarize(scores=scores,p_long=pl,warm_scores=warm,window=120)
    assert r.action_count>0
    assert r.abstain_count>0

def test_rank_controllers_deterministic():
    records={}
    for w,err in [(120,.01),(360,.02),(720,.03)]:
        arr=[]
        for i in range(24):
            r=core.ControllerResult(
                window=w,
                thresholds=np.array([.5]),
                actions=np.array([1,2,0,0,0],dtype=np.int8),
                coverage=.2,
                action_count=2,
                abstain_count=3,
                long_count=1,
                short_count=1,
                coverage_abs_error=err,
                rolling60_coverage=np.array([.2]),
                mean_abs_rolling60_error=err,
                max_abs_rolling60_error=err,
                rolling60_outside_count=0,
                action_state_switches=2,
                warm_start_count=w,
            )
            arr.append(r)
        records[w]=arr
    ranked,stats=core.rank_controllers(records)
    assert ranked==[120,360,720]
    assert set(stats)=={120,360,720}

def test_forward_guards_false_and_smoke():
    assert not any(runner.FORWARD_GUARDS.values())
    assert harness.process_pool_smoke(2)==(1,4,9,16)

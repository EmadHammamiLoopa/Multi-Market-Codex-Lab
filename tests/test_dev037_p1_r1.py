from __future__ import annotations

import numpy as np

from multimarket import dev037_policy_core as policy
from multimarket import dev037_p1_r1_core as core
from multimarket import dev037_p1_r1_harness as harness
from multimarket import dev037_p1_r1_runner as runner

def _fold(fid,pid,y,actions):
    y=np.asarray(y,dtype=np.int8)
    a=np.asarray(actions,dtype=np.int8)
    return {
        "fold_id":fid,
        "policy_id":pid,
        "y3":y,
        "actions":a,
        "metrics":policy.action_metrics(y,a),
    }

def test_policy_family_exact():
    assert core.POLICY_IDS==("S0","S1","S2","S5")
    assert core.CHALLENGER_IDS==("S1","S2","S5")

def test_compare_and_practical_rate():
    base=[];cand=[]
    for fid in range(1,5):
        y=np.tile(np.array([0,1,2,0,1,2,0,1,2,0],dtype=np.int8),20)
        a0=np.zeros(len(y),dtype=np.int8)
        ac=np.zeros(len(y),dtype=np.int8)
        # same acted count, challenger correct on more rows
        a0[:40]=np.where(np.arange(40)%2==0,1,2)
        ac[:40]=y[:40]
        ac[ac==0]=1
        base.append(_fold(fid,"S0",y,a0))
        cand.append(_fold(fid,"S1",y,ac))
    z=core.compare(base,cand)
    assert z["pooled_delta_action_precision"]>0
    assert z["pooled_delta_correct_action_rate"]>0
    assert len(z["fold_delta_action_precision"])==4
    assert len(z["leave_one_fold_out_delta_action_precision"])==4

def test_survivor_gate_requires_correct_rate():
    comp={
        "pooled_delta_action_precision":.03,
        "pooled_delta_correct_action_rate":.01,
        "positive_fold_deltas":4,
        "all_loo_delta_positive":True,
    }
    null={"max_stat_q95":.02,"max_stat_fwer_empirical_p":.01}
    assert core.is_survivor(comp,null)
    comp2=dict(comp)
    comp2["pooled_delta_correct_action_rate"]=0.0
    assert not core.is_survivor(comp2,null)

def test_joint_null_shape_and_legal_shifts():
    by={}
    for pid in core.POLICY_IDS:
        fs=[]
        for fid in range(1,5):
            n=100
            y=np.tile(np.array([0,1,2,0,1],dtype=np.int8),20)
            a=np.zeros(n,dtype=np.int8)
            a[::5]=1
            a[1::5]=2
            fs.append(_fold(fid,pid,y,a))
        by[pid]=tuple(fs)
    z=core.joint_max_stat_null(by,seed=7,replicates=17)
    assert len(z["max_stat_null"])==17
    assert len(z["shift_tuples"])==17
    assert set(z["per_candidate"])=={"S1","S2","S5"}
    for row in z["shift_tuples"]:
        assert all(30<=v<=70 for v in row)

def test_rank_prefers_lower_p():
    common={
        "comparison":{
            "minimum_fold_delta_action_precision":.03,
            "median_fold_delta_action_precision":.04,
            "pooled_delta_action_precision":.05,
            "pooled_delta_correct_action_rate":.01,
            "candidate_pooled_metrics":{"false_actions_per_all_rows":.1},
        },
        "survivor":True,
    }
    records={
        "S1":{**common,"null":{"max_stat_fwer_empirical_p":.03}},
        "S2":{**common,"null":{"max_stat_fwer_empirical_p":.02}},
        "S5":{**common,"null":{"max_stat_fwer_empirical_p":.01}},
    }
    assert core.rank(records)==["S5","S2","S1"]

def test_forward_guards_false_and_smoke():
    assert not any(runner.FORWARD_GUARDS.values())
    assert harness.process_pool_smoke(2)==(1,4,9,16)

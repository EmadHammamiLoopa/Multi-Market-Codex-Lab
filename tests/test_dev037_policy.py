from __future__ import annotations

import numpy as np

from multimarket import dev037_policy_core as core
from multimarket import dev037_policy_harness as harness
from multimarket import dev037_policy_runner as runner

def _fold(pid,fid,y,score,pl,threshold):
    a=core.actions_from_score(score=score,threshold=threshold,p_long=pl)
    return core.PolicyFold(
        fold_id=fid,policy_id=pid,threshold=threshold,
        scores=np.asarray(score,dtype=float),actions=a,
        y3=np.asarray(y,dtype=np.int8),
        metrics=core.action_metrics(y,a),
    )

def test_percentile_mapping_and_scores():
    pt=np.array([.1,.2,.3,.4,.5])
    pl=np.array([.5,.55,.6,.7,.9])
    rt=core.empirical_percentile_reference(pt)
    rd=core.empirical_percentile_reference(core.direction_confidence(pl))
    z=core.score_bundle(p_touch=pt,p_long=pl,touch_reference=rt,dir_reference=rd)
    assert set(["S0","S1","S2","S3","S4"]).issubset(z)
    assert np.all((z["r_touch"]>0)&(z["r_touch"]<=1))
    assert np.all((z["r_dir"]>0)&(z["r_dir"]<=1))

def test_q80_higher():
    x=np.arange(10,dtype=float)
    assert core.threshold_q80(x)==8.0

def test_action_semantics_and_metrics():
    y=np.array([0,1,2,0,2,1],dtype=np.int8)
    score=np.array([.1,.9,.8,.2,.95,.85])
    pl=np.array([.2,.2,.8,.8,.8,.2])
    a=core.actions_from_score(score=score,threshold=.8,p_long=pl)
    m=core.action_metrics(y,a)
    assert m["action_count"]==4
    assert m["correct_action_count"]==4
    assert m["action_precision"]==1.0
    assert m["abstain_count"]==2

def test_none_action_counts_false():
    y=np.array([0,1,2,0],dtype=np.int8)
    a=np.array([1,1,2,2],dtype=np.int8)
    m=core.action_metrics(y,a)
    assert m["correct_action_count"]==2
    assert m["false_action_count"]==2
    assert m["fraction_actions_on_true_none"]==0.5

def test_operational_guards():
    folds=[]
    for fid in range(1,5):
        n=100
        y=np.tile(np.array([0,1,2,0,0],dtype=np.int8),20)
        score=np.linspace(0,1,n)
        pl=np.where(np.arange(n)%2==0,.7,.3)
        folds.append(_fold("S0",fid,y,score,pl,.8))
    g=core.operational_guards(folds)
    assert all(g.values())

def test_compare_and_loo():
    base=[];cand=[]
    for fid in range(1,5):
        y=np.tile(np.array([0,1,2,0,1,2,0,0,1,2],dtype=np.int8),20)
        n=len(y)
        pl=np.where(y==1,.2,.8)
        sb=np.zeros(n);sc=np.zeros(n)
        sb[:40]=1
        sc[:40]=1
        # degrade base by flipping direction confidence sign for some active rows
        plb=pl.copy()
        plb[:10]=1-plb[:10]
        base.append(_fold("S0",fid,y,sb,plb,.5))
        cand.append(_fold("S2",fid,y,sc,pl,.5))
    z=core.compare_to_s0(base,cand)
    assert z["pooled_delta_action_precision"]>0
    assert len(z["fold_delta_action_precision"])==4
    assert len(z["leave_one_fold_out_delta_action_precision"])==4

def test_joint_null_lengths_and_shift_bounds():
    by={}
    for pid in core.POLICY_IDS:
        fs=[]
        for fid in range(1,5):
            n=100
            y=np.tile(np.array([0,1,2,0,1],dtype=np.int8),20)
            score=np.linspace(0,1,n)
            pl=np.where(np.arange(n)%2==0,.7,.3)
            fs.append(_fold(pid,fid,y,score,pl,.8))
        by[pid]=tuple(fs)
    z=core.joint_temporal_max_stat_null(by,seed=7,replicates=17)
    assert len(z["shift_tuples"])==17
    assert len(z["max_stat_null"])==17
    for row in z["shift_tuples"]:
        assert all(30<=v<=70 for v in row)

def test_survivor_gate():
    comp={
        "pooled_delta_action_precision":.03,
        "positive_fold_deltas":4,
        "all_loo_delta_positive":True,
    }
    guards={
        "pooled_coverage_ge_010":True,
        "pooled_coverage_le_030":True,
        "every_fold_coverage_ge_005":True,
        "every_fold_coverage_le_040":True,
        "long_and_short_every_fold":True,
    }
    null={"max_stat_q95":.02,"max_stat_fwer_empirical_p":.01}
    assert core.is_survivor(comparison=comp,guards=guards,nullrec=null)

def test_forward_guards_false_and_smoke():
    assert not any(runner.FORWARD_GUARDS.values())
    assert harness.process_pool_smoke(2)==(1,4,9,16)

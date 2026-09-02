from __future__ import annotations

import numpy as np

from multimarket import dev038a_p1_core as core
from multimarket import dev038a_p1_harness as harness
from multimarket import dev038a_p1_runner as runner

def _fold(fid,cid,y,p):
    y=np.asarray(y,dtype=np.int8)
    p=np.asarray(p,dtype=float)
    return {
        "fold_id":fid,
        "candidate_id":cid,
        "y":y,
        "p":p,
        "metrics":core.metrics(y,p),
    }

def test_candidate_family_exact():
    assert core.CANDIDATE_IDS==("A0","A1","A2","A3","A4")
    assert core.CHALLENGER_IDS==("A1","A2","A3","A4")

def test_metrics_top_decile():
    y=np.array([0,0,0,0,0,0,0,0,1,1],dtype=np.int8)
    p=np.arange(10,dtype=float)/10
    m=core.metrics(y,p)
    assert m["top_decile_count"]==1
    assert m["top_decile_touch_count"]==1
    assert m["top_decile_precision"]==1.0

def test_compare_and_loo_positive():
    base=[];cand=[]
    for fid in range(1,5):
        y=np.tile(np.array([0,0,0,1,0,1],dtype=np.int8),30)
        pb=np.linspace(.1,.9,len(y))
        pc=pb.copy()
        pc[y==1]+=0.2
        pc=np.clip(pc,0,1)
        base.append(_fold(fid,"A0",y,pb))
        cand.append(_fold(fid,"A1",y,pc))
    z=core.compare(base,cand)
    assert z["pooled_delta_ap"]>0
    assert z["positive_fold_deltas"]==4
    assert z["all_loo_delta_positive"]

def test_survivor_requires_calibration():
    comp={
        "pooled_delta_ap":.02,
        "positive_fold_deltas":4,
        "all_loo_delta_positive":True,
        "base_pooled_metrics":{"brier":.2,"log_loss":.5},
        "candidate_pooled_metrics":{"brier":.19,"log_loss":.49},
    }
    null={"max_stat_q95":.01,"max_stat_fwer_empirical_p":.01}
    assert core.is_survivor(comp,null)
    bad=dict(comp)
    bad["candidate_pooled_metrics"]={"brier":.21,"log_loss":.49}
    assert not core.is_survivor(bad,null)

def test_joint_null_shape():
    by={}
    for cid in core.CANDIDATE_IDS:
        fs=[]
        for fid in range(1,5):
            y=np.tile(np.array([0,0,1,0,1],dtype=np.int8),20)
            p=np.linspace(.1,.9,len(y))
            if cid!="A0":
                p=np.clip(p+0.001,0,1)
            fs.append(_fold(fid,cid,y,p))
        by[cid]=tuple(fs)
    z=core.joint_max_stat_null(by,seed=7,replicates=17)
    assert len(z["max_stat_null"])==17
    assert len(z["shift_tuples"])==17
    assert set(z["per_candidate"])=={"A1","A2","A3","A4"}
    for row in z["shift_tuples"]:
        assert all(30<=x<=70 for x in row)

def test_rank_prefers_lower_p():
    common={
        "comparison":{
            "minimum_fold_delta_ap":.02,
            "median_fold_delta_ap":.03,
            "pooled_delta_ap":.04,
            "candidate_pooled_metrics":{"brier":.1,"log_loss":.3},
        },
        "survivor":True,
    }
    records={
        "A1":{**common,"null":{"max_stat_fwer_empirical_p":.04}},
        "A2":{**common,"null":{"max_stat_fwer_empirical_p":.03}},
        "A3":{**common,"null":{"max_stat_fwer_empirical_p":.02}},
        "A4":{**common,"null":{"max_stat_fwer_empirical_p":.01}},
    }
    assert core.rank(records)==["A4","A3","A2","A1"]

def test_guards_false_and_smoke():
    assert not any(runner.FORWARD_GUARDS.values())
    assert harness.process_pool_smoke(2)==(1,4,9,16)

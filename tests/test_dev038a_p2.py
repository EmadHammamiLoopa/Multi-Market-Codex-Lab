from __future__ import annotations

import numpy as np

from multimarket import dev037_policy_core as policy
from multimarket import dev038a_p2_core as core
from multimarket import dev038a_p2_harness as harness
from multimarket import dev038a_p2_runner as runner

def _fold(fid,y,actions):
    y=np.asarray(y,dtype=np.int8)
    a=np.asarray(actions,dtype=np.int8)
    return {
        "fold_id":fid,
        "y3":y,
        "actions":a,
        "metrics":policy.action_metrics(y,a),
    }

def test_family_exact():
    assert core.CONTROLLER_IDS==("C0","C1","C2")
    assert core.CHALLENGER_IDS==("C1","C2")
    assert core.WINDOW_BY_ID=={"C0":120,"C1":360,"C2":720}

def test_compare_preservation_and_false_action_metrics():
    base=[]
    cand=[]
    for fid in range(1,5):
        y=np.tile(np.array([0,1,2,0,1,2,0,1,2,0],dtype=np.int8),20)
        a0=np.zeros(len(y),dtype=np.int8)
        ac=np.zeros(len(y),dtype=np.int8)
        # Base acts on many NONE/wrong rows.
        a0[:60]=1
        # Candidate acts less, with at least as many correct actions.
        idx=np.where(y!=0)[0][:45]
        ac[idx]=y[idx]
        base.append(_fold(fid,y,a0))
        cand.append(_fold(fid,y,ac))

    z=core.compare(base,cand)
    assert z["pooled_delta_action_precision"]>0
    assert z["pooled_delta_correct_action_rate"]>=0
    assert z["pooled_delta_false_action_rate"]<0
    assert z["pooled_delta_action_on_none_fraction"]<0
    assert len(z["leave_one_fold_out_delta_action_precision"])==4

def test_survivor_requires_all_practical_gates():
    comp={
        "pooled_delta_action_precision":0.03,
        "pooled_delta_correct_action_rate":0.0,
        "pooled_delta_false_action_rate":-0.01,
        "pooled_delta_action_on_none_fraction":-0.05,
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
    null={"max_stat_q95":0.02,"max_stat_fwer_empirical_p":0.01}
    assert core.is_survivor(comp,guards,null)

    bad=dict(comp)
    bad["pooled_delta_correct_action_rate"]=-1e-12
    assert not core.is_survivor(bad,guards,null)

    bad=dict(comp)
    bad["pooled_delta_action_on_none_fraction"]=0.0
    assert not core.is_survivor(bad,guards,null)

def test_joint_null_shape_and_legal_shifts():
    by={}
    for cid in core.CONTROLLER_IDS:
        fs=[]
        for fid in range(1,5):
            y=np.tile(np.array([0,1,2,0,1],dtype=np.int8),20)
            a=np.zeros(len(y),dtype=np.int8)
            a[::5]=1
            a[1::5]=2
            fs.append(_fold(fid,y,a))
        by[cid]=tuple(fs)

    z=core.joint_max_stat_null(by,seed=7,replicates=17)
    assert len(z["max_stat_null"])==17
    assert len(z["shift_tuples"])==17
    assert set(z["per_candidate"])=={"C1","C2"}
    for row in z["shift_tuples"]:
        assert all(30<=v<=70 for v in row)

def test_rank_prefers_lower_p_then_smaller_window():
    common={
        "comparison":{
            "minimum_fold_delta_action_precision":0.03,
            "median_fold_delta_action_precision":0.04,
            "pooled_delta_action_precision":0.05,
            "pooled_delta_correct_action_rate":0.01,
            "candidate_pooled_metrics":{"fraction_actions_on_true_none":0.20},
        },
        "survivor":True,
    }
    records={
        "C1":{**common,"null":{"max_stat_fwer_empirical_p":0.01}},
        "C2":{**common,"null":{"max_stat_fwer_empirical_p":0.01}},
    }
    assert core.rank(records)==["C1","C2"]

def test_forward_guards_and_stop_rule_identity():
    assert not any(runner.FORWARD_GUARDS.values())
    assert runner.DEV038A_P1_SHA=="16292d1f730561427a4623a052441f3ab20db0a96eeefac06b6f0a0391c5e549"
    assert harness.process_pool_smoke(2)==(1,4,9,16)

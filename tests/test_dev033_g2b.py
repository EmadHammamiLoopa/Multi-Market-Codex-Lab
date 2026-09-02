from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import numpy as np
import pytest

from multimarket import dev030_direction_dataset as dd
from multimarket import dev033_g2a_materialize as g2a
from multimarket import dev033_g2b_core as core
from multimarket import dev033_g2b_runner as runner

DAYS=dd.HISTORICAL_DAYS

def _per_day(width:int,seed:int):
    rng=np.random.default_rng(seed)
    out={}
    for i,d in enumerate(DAYS):
        n=30+i
        ts=np.arange(n,dtype=np.int64)+i*1000
        y=(np.arange(n)%2).astype(np.int8)
        x=rng.normal(size=(n,width))
        # weak deterministic signal
        x[:,0]+=y*.15
        out[d]=(x,y,ts)
    return out

def _fake_base_from_candidate(c):
    folds=[]
    for f in c.folds:
        folds.append(SimpleNamespace(
            fold_id=f.fold_id,
            timestamps_us=f.timestamps_us,
            y_true=f.labels,
            y_pred=f.predictions,
            metrics={"balanced_accuracy_at_0_5":f.metrics["balanced_accuracy"]},
        ))
    return tuple(folds)

def test_fit_candidate_four_folds_and_frozen_c_grid():
    c=core.fit_candidate("G2C01",_per_day(31,1))
    assert len(c.folds)==4
    assert c.feature_count==31
    assert all(f.selected_c in core.C_GRID for f in c.folds)
    assert all(len(f.inner_c_ledger)==4 for f in c.folds)

def test_compare_alignment_and_loo():
    base=core.fit_candidate("BASE",_per_day(23,2))
    cand=core.fit_candidate("G2C01",_per_day(31,3))
    # force exact labels/timestamps by both generators already sharing support
    bfolds=_fake_base_from_candidate(base)
    z=core.compare(bfolds,cand)
    assert len(z["fold_delta_balanced_accuracy"])==4
    assert len(z["leave_one_fold_out_delta_balanced_accuracy"])==4
    assert 0.0<=z["predicted_minority_fraction"]<=0.5

def test_joint_null_serializes_all_24_vectors():
    base=core.fit_candidate("BASE",_per_day(23,4))
    bfolds=_fake_base_from_candidate(base)
    candidates={}
    for i,cid in enumerate(g2a.CANDIDATE_IDS):
        candidates[cid]=core.fit_candidate(cid,_per_day(24+(i%3),10+i))
    z=core.joint_max_stat_null(
        bfolds,candidates,seed=123,replicates=19
    )
    assert z["replicates"]==19
    assert z["candidate_ids"]==list(g2a.CANDIDATE_IDS)
    assert len(z["shift_tuples"])==19
    assert len(z["max_stat_null"])==19
    assert tuple(z["candidate_null_vectors"])==g2a.CANDIDATE_IDS
    assert all(len(z["candidate_null_vectors"][cid])==19 for cid in g2a.CANDIDATE_IDS)

def test_null_completeness_rejects_missing_vector():
    z={
        "replicates":1999,
        "candidate_ids":list(g2a.CANDIDATE_IDS),
        "shift_tuples":[[1,1,1,1]]*1999,
        "max_stat_null":[0.0]*1999,
        "candidate_null_vectors":{cid:[0.0]*1999 for cid in g2a.CANDIDATE_IDS},
        "per_candidate":{cid:{} for cid in g2a.CANDIDATE_IDS},
    }
    runner._validate_null_completeness(z)
    del z["candidate_null_vectors"]["G2C24"]
    with pytest.raises(runner.G2BRunnerError) as e:
        runner._validate_null_completeness(z)
    assert e.value.reason=="null_candidate_vector_membership"

def test_classification_contract():
    fake=SimpleNamespace(pooled_metrics={"balanced_accuracy":0.57})
    comp={
        "pooled_delta_balanced_accuracy":0.03,
        "positive_fold_deltas":4,
        "all_loo_delta_positive":True,
        "candidate_fold_ba_gt_0_50":4,
        "both_classes_predicted_all_folds":True,
        "predicted_minority_fraction":0.20,
    }
    n={"max_stat_q95":0.02,"max_stat_fwer_empirical_p":0.04}
    assert core.classify(fake,comp,n)==core.STATUS_SURVIVOR
    n2={"max_stat_q95":0.04,"max_stat_fwer_empirical_p":0.10}
    assert core.classify(fake,comp,n2)==core.STATUS_INCONCLUSIVE
    comp2=dict(comp);comp2["positive_fold_deltas"]=2
    assert core.classify(fake,comp2,n2)==core.STATUS_REJECTED

def test_runner_guards_and_worker_cap():
    assert not any(runner.FORWARD_GUARDS.values())
    assert runner._normalize_workers(99)==12
    assert runner._normalize_workers(0)==1
    expected_output = (
        "dev033_g2b_r1_layered_temporal_screen_v1"
        if runner.EXPERIMENT_ID == "DEV033-G2B-R1"
        else "dev033_g2b_layered_temporal_screen_v1"
    )
    assert runner.REAL_OUTPUT_DIRECTORY.name == expected_output

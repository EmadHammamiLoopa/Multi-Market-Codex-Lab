from __future__ import annotations

from types import SimpleNamespace
import numpy as np
import pytest

from multimarket import dev030_direction_dataset as dd
from multimarket import dev034_g3a_core as g3
from multimarket import dev034_g3b_r1_core as core
from multimarket import dev034_g3b_r1_loader as loader
from multimarket import dev034_g3b_r1_runner as runner
from multimarket import dev034_g3b_r1_harness as harness

DAYS=dd.HISTORICAL_DAYS

def _per_day(width:int,seed:int):
    rng=np.random.default_rng(seed)
    counts=[40,44,48,52,56,60,64]
    out={}
    for i,d in enumerate(DAYS):
        n=counts[i]
        ts=np.arange(n,dtype=np.int64)+i*1000
        y=(np.arange(n)%2).astype(np.int8)
        x=rng.normal(size=(n,width))
        x[:,0]+=0.20*y
        out[d]=(x,y,ts)
    return out

def test_identity_and_reserved_output():
    assert runner.EXPERIMENT_ID=="DEV034-G3B-R1"
    assert runner.REAL_OUTPUT_DIRECTORY.name=="dev034_g3b_r1_common_support_screen_v1"
    assert runner.ARTIFACT_FILENAME=="DEV034_G3B_R1_COMMON_SUPPORT_SCREEN_RESULT.json"
    assert not any(runner.FORWARD_GUARDS.values())

def test_fit_candidate_uses_four_folds_and_fixed_c_grid():
    z=core.fit_candidate("P3_COMMON_SUPPORT_REFIT",_per_day(23,1))
    assert len(z.folds)==4
    assert z.feature_count==23
    assert all(f.selected_c in core.C_GRID for f in z.folds)
    assert all(len(f.inner_c_ledger)==4 for f in z.folds)

def test_compare_requires_exact_matched_support():
    b=core.fit_candidate("P3_COMMON_SUPPORT_REFIT",_per_day(23,2))
    c=core.fit_candidate("G3C01",_per_day(24,3))
    z=core.compare(b,c)
    assert len(z["fold_delta_balanced_accuracy"])==4
    assert len(z["leave_one_fold_out_delta_balanced_accuracy"])==4
    bad=list(c.folds)
    f=bad[0]
    bad[0]=core.FoldResult(
        f.fold_id,f.selected_c,f.timestamps_us+1,f.labels,f.probabilities,
        f.predictions,f.metrics,f.inner_c_ledger,f.prediction_sha256
    )
    c2=core.CandidateResult(c.candidate_id,c.feature_count,tuple(bad),c.pooled_metrics)
    with pytest.raises(core.G3BR1Error,match="support_alignment"):
        core.compare(b,c2)

def test_joint_null_has_exact_16_vectors():
    b=core.fit_candidate("P3_COMMON_SUPPORT_REFIT",_per_day(23,4))
    cands={}
    for i,cid in enumerate(g3.CANDIDATE_IDS):
        cands[cid]=core.fit_candidate(cid,_per_day(24+(i%4),10+i))
    z=core.joint_max_stat_null(b,cands,seed=123,replicates=19)
    assert z["candidate_ids"]==list(g3.CANDIDATE_IDS)
    assert len(z["shift_tuples"])==19
    assert len(z["max_stat_null"])==19
    assert tuple(z["candidate_null_vectors"])==g3.CANDIDATE_IDS
    assert all(len(z["candidate_null_vectors"][cid])==19 for cid in g3.CANDIDATE_IDS)

def test_null_order_fails_closed():
    b=core.fit_candidate("P3_COMMON_SUPPORT_REFIT",_per_day(23,5))
    cands={}
    ids=list(g3.CANDIDATE_IDS)
    for i,cid in enumerate(reversed(ids)):
        cands[cid]=core.fit_candidate(cid,_per_day(24,30+i))
    with pytest.raises(core.G3BR1Error,match="null_candidate_order"):
        core.joint_max_stat_null(b,cands,seed=1,replicates=3)

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

def test_subset_exact_is_deterministic_and_label_guarded():
    ots=np.array([10,20,30,40],dtype=np.int64)
    oy=np.array([0,1,0,1],dtype=np.int8)
    x=np.arange(4*23,dtype=float).reshape(4,23)
    t=np.array([20,40],dtype=np.int64)
    y=np.array([1,1],dtype=np.int8)
    got=loader._subset_exact(ots,oy,x,t,y)
    assert np.array_equal(got,x[[1,3]])
    with pytest.raises(loader.G3BR1LoaderError,match="common_support_label_mismatch"):
        loader._subset_exact(ots,oy,x,t,np.array([0,1],dtype=np.int8))

def test_candidate_width_contract_registry():
    expected={
        "G3C01":24,"G3C02":26,"G3C03":28,"G3C04":28,
        "G3C05":26,"G3C06":26,"G3C07":26,"G3C08":28,
        "G3C09":27,"G3C10":27,"G3C11":33,"G3C12":29,
        "G3C13":27,"G3C14":34,"G3C15":40,"G3C16":45,
    }
    assert {cid:23+g3.BY_ID[cid]["feature_count"] for cid in g3.CANDIDATE_IDS}==expected

def test_runner_worker_cap_and_null_completeness():
    assert runner._normalize_workers(99)==12
    assert runner._normalize_workers(0)==1
    z={
        "replicates":1999,
        "candidate_ids":list(g3.CANDIDATE_IDS),
        "shift_tuples":[[10,10,10,10]]*1999,
        "max_stat_null":[0.0]*1999,
        "candidate_null_vectors":{cid:[0.0]*1999 for cid in g3.CANDIDATE_IDS},
        "per_candidate":{cid:{} for cid in g3.CANDIDATE_IDS},
    }
    runner._validate_null_completeness(z)
    del z["candidate_null_vectors"]["G3C16"]
    with pytest.raises(runner.G3BR1RunnerError,match="null_candidate_vector_membership"):
        runner._validate_null_completeness(z)

def test_process_pool_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)

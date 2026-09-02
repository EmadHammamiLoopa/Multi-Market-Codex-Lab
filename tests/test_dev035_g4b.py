from __future__ import annotations

from types import SimpleNamespace
import numpy as np
import pytest

from multimarket import dev030_direction_dataset as dd
from multimarket import dev035_g4b_core as core
from multimarket import dev035_g4b_loader as loader
from multimarket import dev035_g4b_runner as runner
from multimarket import dev035_g4b_harness as harness

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
        x[:,0]+=0.25*y
        out[d]=(x,y,ts)
    return out

def test_frozen_identity_and_widths():
    assert runner.EXPERIMENT_ID=="DEV035-G4B"
    assert core.CANDIDATE_IDS==("G4C01","G4C02","G4C03")
    assert loader.CANDIDATE_WIDTH=={
        "G4C01":56,
        "G4C02":71,
        "G4C03":88,
    }
    assert not any(runner.FORWARD_GUARDS.values())

def test_fit_candidate_base_uses_four_folds_and_fixed_c_grid():
    z=core.fit_candidate("BTC45_PROMOTED_BASE_REFIT",_per_day(45,1))
    assert z.feature_count==45
    assert len(z.folds)==4
    assert all(f.selected_c in core.C_GRID for f in z.folds)
    assert all(len(f.inner_c_ledger)==4 for f in z.folds)

def test_compare_requires_exact_support_and_labels():
    b=core.fit_candidate("BTC45_PROMOTED_BASE_REFIT",_per_day(45,2))
    c=core.fit_candidate("G4C01",_per_day(56,3))
    z=core.compare(b,c)
    assert len(z["fold_delta_balanced_accuracy"])==4
    assert len(z["leave_one_fold_out_delta_balanced_accuracy"])==4

    bad=list(c.folds)
    f=bad[0]
    bad[0]=core.FoldResult(
        f.fold_id,f.selected_c,f.timestamps_us+1,f.labels,f.probabilities,
        f.predictions,f.metrics,f.inner_c_ledger,f.prediction_sha256,
    )
    c2=core.CandidateResult(c.candidate_id,c.feature_count,tuple(bad),c.pooled_metrics)
    with pytest.raises(core.G4BError,match="support_alignment"):
        core.compare(b,c2)

def test_joint_null_exact_three_candidate_vectors():
    b=core.fit_candidate("BTC45_PROMOTED_BASE_REFIT",_per_day(45,4))
    cands={
        "G4C01":core.fit_candidate("G4C01",_per_day(56,11)),
        "G4C02":core.fit_candidate("G4C02",_per_day(71,12)),
        "G4C03":core.fit_candidate("G4C03",_per_day(88,13)),
    }
    z=core.joint_max_stat_null(b,cands,seed=123,replicates=19)
    assert z["candidate_ids"]==["G4C01","G4C02","G4C03"]
    assert len(z["shift_tuples"])==19
    assert len(z["max_stat_null"])==19
    assert all(len(z["candidate_null_vectors"][cid])==19 for cid in core.CANDIDATE_IDS)

def test_null_wrong_order_fails_closed():
    b=core.fit_candidate("BTC45_PROMOTED_BASE_REFIT",_per_day(45,5))
    cands={
        "G4C02":core.fit_candidate("G4C02",_per_day(71,21)),
        "G4C01":core.fit_candidate("G4C01",_per_day(56,22)),
        "G4C03":core.fit_candidate("G4C03",_per_day(88,23)),
    }
    with pytest.raises(core.G4BError,match="null_candidate_order"):
        core.joint_max_stat_null(b,cands,seed=1,replicates=3)

def test_g4_survivor_gate_contract():
    fake=SimpleNamespace(pooled_metrics={"balanced_accuracy":0.61})
    comp={
        "pooled_delta_balanced_accuracy":0.02,
        "positive_fold_deltas":4,
        "all_loo_delta_positive":True,
        "candidate_fold_ba_gt_0_50":4,
        "both_classes_predicted_all_folds":True,
        "predicted_minority_fraction":0.20,
    }
    n={"max_stat_q95":0.015,"max_stat_fwer_empirical_p":0.04}
    assert core.classify(fake,comp,n)==core.STATUS_SURVIVOR

    fake_low=SimpleNamespace(pooled_metrics={"balanced_accuracy":0.589})
    assert core.classify(fake_low,comp,n)==core.STATUS_INCONCLUSIVE

    comp_small=dict(comp)
    comp_small["pooled_delta_balanced_accuracy"]=0.014
    assert core.classify(fake,comp_small,n)==core.STATUS_INCONCLUSIVE

def test_rank_survivors_prefers_frozen_lexicographic_rule():
    rows=[
        {
            "candidate_id":"G4C02","status":core.STATUS_SURVIVOR,
            "added_feature_count":26,
            "null":{"max_stat_fwer_empirical_p":0.01},
            "comparison_vs_btc45":{
                "minimum_fold_delta_balanced_accuracy":0.02,
                "median_fold_delta_balanced_accuracy":0.03,
                "pooled_delta_balanced_accuracy":0.04,
            },
        },
        {
            "candidate_id":"G4C01","status":core.STATUS_SURVIVOR,
            "added_feature_count":11,
            "null":{"max_stat_fwer_empirical_p":0.01},
            "comparison_vs_btc45":{
                "minimum_fold_delta_balanced_accuracy":0.02,
                "median_fold_delta_balanced_accuracy":0.03,
                "pooled_delta_balanced_accuracy":0.04,
            },
        },
    ]
    assert [z["candidate_id"] for z in runner._rank_survivors(rows)]==["G4C01","G4C02"]

def test_only_rank_one_would_advance():
    rows=[
        {
            "candidate_id":"G4C03","status":core.STATUS_SURVIVOR,
            "added_feature_count":43,
            "null":{"max_stat_fwer_empirical_p":0.02},
            "comparison_vs_btc45":{
                "minimum_fold_delta_balanced_accuracy":0.03,
                "median_fold_delta_balanced_accuracy":0.04,
                "pooled_delta_balanced_accuracy":0.05,
            },
        },
        {
            "candidate_id":"G4C02","status":core.STATUS_SURVIVOR,
            "added_feature_count":26,
            "null":{"max_stat_fwer_empirical_p":0.01},
            "comparison_vs_btc45":{
                "minimum_fold_delta_balanced_accuracy":0.02,
                "median_fold_delta_balanced_accuracy":0.04,
                "pooled_delta_balanced_accuracy":0.05,
            },
        },
    ]
    ranked=runner._rank_survivors(rows)
    advanced=[ranked[0]["candidate_id"]] if ranked else []
    assert advanced==["G4C02"]

def test_metric_contract_has_per_class():
    y=np.array([0,0,1,1],dtype=np.int8)
    p=np.array([0.1,0.8,0.7,0.9],dtype=float)
    z=core.metrics(y,p)
    assert set(z["per_class"])=={"SHORT","LONG"}

def test_null_completeness_validator():
    z={
        "replicates":1999,
        "candidate_ids":["G4C01","G4C02","G4C03"],
        "shift_tuples":[[10,10,10,10]]*1999,
        "max_stat_null":[0.0]*1999,
        "candidate_null_vectors":{cid:[0.0]*1999 for cid in core.CANDIDATE_IDS},
    }
    runner._validate_null_completeness(z)
    z["candidate_null_vectors"]["G4C03"]=z["candidate_null_vectors"]["G4C03"][:-1]
    with pytest.raises(runner.G4BRunnerError,match="null_candidate_vector_length"):
        runner._validate_null_completeness(z)

def test_worker_cap():
    assert runner._normalize_workers(99)==8
    assert runner._normalize_workers(0)==1

def test_process_pool_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)

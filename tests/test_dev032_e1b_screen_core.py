from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from multimarket import dev032_e1b_screen_core as core
from multimarket import dev032_e1b_loader as loader

def _days():
    start=date(2026,1,1)
    return tuple(start+timedelta(days=31*i) for i in range(7))

def _folds(days):
    return (
        core.FoldSpec(1,(days[0],days[1],days[2]),days[3]),
        core.FoldSpec(2,(days[0],days[1],days[2],days[3]),days[4]),
        core.FoldSpec(3,(days[0],days[1],days[2],days[3],days[4]),days[5]),
        core.FoldSpec(4,(days[0],days[1],days[2],days[3],days[4],days[5]),days[6]),
    )

def _make_rep(seed=1, width=3, signal=0.7):
    rng=np.random.default_rng(seed)
    days=_days()
    out={}
    base_ts=1_700_000_000_000_000
    cursor=0
    for j,d in enumerate(days):
        n=80 if j<3 else 60
        y=np.asarray([(i+j)%2 for i in range(n)],dtype=np.int8)
        x=rng.normal(size=(n,width))
        x[:,0]+=signal*(2*y-1)
        ts=np.arange(base_ts+cursor,base_ts+cursor+n,dtype=np.int64)
        cursor+=1000
        out[d]=core.DayMatrix(d,ts,y,x)
    return out,_folds(days)

def test_probability_metrics_and_fit_are_deterministic():
    per_day,folds=_make_rep(seed=10)
    a=core.fit_representation(per_day,folds,"R")
    b=core.fit_representation(per_day,folds,"R")
    assert a.pooled_metrics==b.pooled_metrics
    assert [f.selected_c for f in a.folds]==[f.selected_c for f in b.folds]
    assert [f.prediction_sha256 for f in a.folds]==[f.prediction_sha256 for f in b.folds]

def test_compare_to_baseline_requires_matched_support():
    base_days,folds=_make_rep(seed=1,signal=0.2)
    cand_days,_=_make_rep(seed=2,signal=1.0)
    first_validation=folds[0].validation_day
    z=cand_days[first_validation]
    shifted=z.timestamps_us.copy()
    shifted[0]+=1
    cand_days[first_validation]=core.DayMatrix(
        z.day,shifted,z.labels,z.values
    )
    b=core.fit_representation(base_days,folds,"B")
    c=core.fit_representation(cand_days,folds,"C")
    with pytest.raises(core.E1BScreenError,match="matched_support"):
        core.compare_to_baseline(b,c)

def test_temporal_null_is_seed_deterministic():
    base_days,folds=_make_rep(seed=4,signal=0.2)
    c1_days,_=_make_rep(seed=5,signal=0.6)
    c2_days,_=_make_rep(seed=6,signal=0.8)

    # Copy baseline support/labels to candidate values so support is exactly matched.
    for src in (c1_days,c2_days):
        for d in base_days:
            src[d]=core.DayMatrix(
                d,base_days[d].timestamps_us,base_days[d].labels,src[d].values
            )

    b=core.fit_representation(base_days,folds,"B00")
    c1=core.fit_representation(c1_days,folds,"P04")
    c2=core.fit_representation(c2_days,folds,"P05")
    candidates={"P04":c1,"P05":c2}

    n1=core.temporal_max_stat_null(b,candidates,seed=123,replicates=99)
    n2=core.temporal_max_stat_null(b,candidates,seed=123,replicates=99)
    assert n1==n2
    assert len(n1["max_stat_null"])==99
    assert n1["candidate_ids"]==["P04","P05"]
    assert 0.0 < n1["per_candidate"]["P04"]["max_stat_fwer_empirical_p"] <= 1.0

def test_classification_gates():
    dummy=core.RepresentationResult(
        "P04",24,(),
        {"roc_auc":0.60}
    )
    comp={
        "pooled_auc_delta":0.05,
        "positive_fold_auc_deltas":4,
        "candidate_fold_auc_gt_0_5":4,
        "all_loo_auc_delta_positive":True,
    }
    null={
        "max_stat_q95":0.03,
        "max_stat_fwer_empirical_p":0.02,
    }
    assert core.classify_candidate(dummy,comp,null)==core.STATUS_STRONG
    null2=dict(null,max_stat_fwer_empirical_p=0.2)
    assert core.classify_candidate(dummy,comp,null2)==core.STATUS_INCONCLUSIVE
    comp2=dict(comp,positive_fold_auc_deltas=2)
    assert core.classify_candidate(dummy,comp2,null)==core.STATUS_REJECTED

def test_loader_primary_registry_is_exact():
    assert len(loader.PRIMARY_IDS)==34
    assert loader.PRIMARY_IDS[0]=="P02"
    assert loader.PRIMARY_IDS[-1]=="P35"
    assert set(loader.PRIMARY_IDS)==set(loader.FAMILY_BY_PRIMARY)
    assert len(loader.STANDALONE_IDS)==34

def test_stack_rejects_nonfinite():
    per_day,folds=_make_rep(seed=7)
    d=next(iter(per_day))
    z=per_day[d]
    bad=z.values.copy()
    bad[0,0]=np.nan
    per_day[d]=core.DayMatrix(d,z.timestamps_us,z.labels,bad)
    with pytest.raises(core.E1BScreenError,match="day_nonfinite"):
        core.fit_representation(per_day,folds,"BAD")

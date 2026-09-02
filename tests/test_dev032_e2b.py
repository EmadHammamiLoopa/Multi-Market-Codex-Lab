from __future__ import annotations

from datetime import date
import numpy as np
import pytest

from multimarket import dev032_e1b_screen_core as e1
from multimarket import dev032_e2b_loader as loader
from multimarket import dev032_e2b_screen_core as core

DAYS=tuple(date(2026,m,1) for m in range(1,8))

def _days(width,seed=1):
    rng=np.random.default_rng(seed)
    out={}
    for i,d in enumerate(DAYS):
        n=30+i
        ts=np.arange(n,dtype=np.int64)+i*1000
        y=(np.arange(n)%2).astype(np.int8)
        x=rng.normal(size=(n,width))
        out[d]=e1.DayMatrix(d,ts,y,x)
    return out

def _folds():
    return (
        e1.FoldSpec(1,DAYS[:3],DAYS[3]),
        e1.FoldSpec(2,DAYS[:4],DAYS[4]),
        e1.FoldSpec(3,DAYS[:5],DAYS[5]),
        e1.FoldSpec(4,DAYS[:6],DAYS[6]),
    )

def test_parent_mapping_exact():
    assert loader.PARENT_BY_REFINEMENT=={
        "E2R01":"P07","E2R02":"P07","E2R03":"P09","E2R04":"P09",
        "E2R05":"P13","E2R06":"P13","E2R07":"P17","E2R08":"P21",
        "E2R09":"P35","E2R10":"P32",
    }

def test_ordinary_refinement_fit():
    base=_days(23,1)
    extra=_days(6,2)
    # force labels/support exact
    extra={d:e1.DayMatrix(d,base[d].timestamps_us,base[d].labels,extra[d].values) for d in DAYS}
    r=core.fit_refinement(base,extra,_folds(),"E2R02",core.TransformSpec("ordinary"))
    assert len(r.folds)==4
    assert r.feature_count==29
    assert np.isfinite(r.pooled_metrics["roc_auc"])

def test_pca_and_svd_fit_train_only_shapes():
    base=_days(23,3)
    raw20=_days(20,4)
    raw40=_days(40,5)
    raw20={d:e1.DayMatrix(d,base[d].timestamps_us,base[d].labels,raw20[d].values) for d in DAYS}
    raw40={d:e1.DayMatrix(d,base[d].timestamps_us,base[d].labels,raw40[d].values) for d in DAYS}
    p=core.fit_refinement(base,raw20,_folds(),"E2R05",core.TransformSpec("pca",5))
    s=core.fit_refinement(base,raw40,_folds(),"E2R06",core.TransformSpec("svd",5))
    assert p.feature_count==28
    assert s.feature_count==28
    assert len(p.folds)==len(s.folds)==4

def test_compare_parent_relative():
    base=_days(23,6)
    extra=_days(3,7)
    extra={d:e1.DayMatrix(d,base[d].timestamps_us,base[d].labels,extra[d].values) for d in DAYS}
    parent=e1.fit_representation(base,_folds(),"PXX")
    cand=core.fit_refinement(base,extra,_folds(),"E2RXX",core.TransformSpec("ordinary"))
    c=core.compare(parent,cand)
    assert len(c["fold_auc_delta"])==4
    assert len(c["leave_one_fold_out_auc_delta"])==4

def test_classification_logic():
    fake=type("F",(),{"pooled_metrics":{"roc_auc":0.60},"folds":[]})()
    comp={
        "pooled_auc_delta":0.06,
        "positive_fold_auc_deltas":4,
        "all_loo_auc_delta_positive":True,
        "candidate_fold_auc_gt_0_5":4,
    }
    n={"max_stat_q95":0.05,"max_stat_fwer_empirical_p":0.04}
    assert core.classify(fake,comp,n,0.54)==core.STATUS_SURVIVOR
    n2={"max_stat_q95":0.07,"max_stat_fwer_empirical_p":0.08}
    assert core.classify(fake,comp,n2,0.54)==core.STATUS_INCONCLUSIVE
    comp2=dict(comp);comp2["positive_fold_auc_deltas"]=2
    assert core.classify(fake,comp2,n2,0.54)==core.STATUS_REJECTED

def test_parent_relative_null_contract_small():
    base=_days(23,8)
    e1x=_days(2,9);e2x=_days(2,10)
    e1x={d:e1.DayMatrix(d,base[d].timestamps_us,base[d].labels,e1x[d].values) for d in DAYS}
    e2x={d:e1.DayMatrix(d,base[d].timestamps_us,base[d].labels,e2x[d].values) for d in DAYS}
    parent=e1.fit_representation(base,_folds(),"P07")
    c1=core.fit_refinement(base,e1x,_folds(),"E2R01",core.TransformSpec("ordinary"))
    c2=core.fit_refinement(base,e2x,_folds(),"E2R02",core.TransformSpec("ordinary"))
    z=core.parent_relative_max_stat_null(
        {"P07":parent},
        {"E2R01":c1,"E2R02":c2},
        {"E2R01":"P07","E2R02":"P07"},
        seed=123,replicates=19,
    )
    assert z["replicates"]==19
    assert len(z["shift_tuples"])==19
    assert len(z["max_stat_null"])==19
    assert set(z["per_candidate"])=={"E2R01","E2R02"}

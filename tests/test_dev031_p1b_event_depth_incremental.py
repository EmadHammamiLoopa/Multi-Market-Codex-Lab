from __future__ import annotations
from datetime import date
from pathlib import Path
import numpy as np
import pytest
from multimarket import dev031_p1b_event_depth_incremental as p

def test_identity_and_guards():
    assert p.EXPERIMENT_ID=="DEV031-P1B"
    assert p.DESIGN_VERSION=="event-depth-incremental-direction-v1"
    assert p.C_GRID==(0.01,0.1,1.0,10.0)
    assert not any(p.FORWARD_GUARDS.values())

def test_probability_metrics_basic():
    y=np.array([0,0,1,1],dtype=np.int8)
    prob=np.array([0.1,0.3,0.7,0.9])
    m=p.probability_metrics(y,prob)
    assert m["support"]==4
    assert m["roc_auc"]==pytest.approx(1.0)
    assert m["balanced_accuracy_at_0_5"]==pytest.approx(1.0)

def test_probability_first_selection_prefers_valid_grid():
    x=np.array([[-2],[-1],[1],[2],[-1.5],[1.5]],dtype=float)
    y=np.array([0,0,1,1,0,1],dtype=np.int8)
    c,ledger=p.select_c(x[:4],y[:4],x[4:],y[4:])
    assert c in p.C_GRID
    assert len(ledger)==4
    assert all(set(z)=={"C","binary_log_loss","brier","roc_auc"} for z in ledger)

def _day(d,n,seed):
    rng=np.random.default_rng(seed)
    y=np.array(([0,1]*((n+1)//2))[:n],dtype=np.int8)
    x0=rng.normal(size=(n,23))
    x1=np.column_stack([x0,rng.normal(size=(n,26))])
    start=int(date(d.year,d.month,d.day).strftime("%s")) if False else 0
    base=(d.toordinal()*86400)*1_000_000
    ts=base+np.arange(n,dtype=np.int64)*60_000_000
    return p.DayData(d,ts,y,x0,x1)

def test_fit_representation_same_support():
    days={}
    sizes=[20,20,20,20,20,20,20]
    for d,n,i in zip(p.dd.HISTORICAL_DAYS,sizes,range(7)):
        days[d]=_day(d,n,i+1)
    c0=p.fit_rep(days,"C0")
    c1=p.fit_rep(days,"C1")
    for a,b in zip(c0.folds,c1.folds,strict=True):
        assert np.array_equal(a.ts,b.ts)
        assert np.array_equal(a.y,b.y)

def test_comparison_gate_fields():
    days={d:_day(d,24,i+10) for i,d in enumerate(p.dd.HISTORICAL_DAYS)}
    c0=p.fit_rep(days,"C0"); c1=p.fit_rep(days,"C1")
    comp=p.comparison(c0,c1)
    expected={
      "pooled_log_loss_better","pooled_brier_better","pooled_auc_better",
      "pooled_c1_auc_at_least_056","at_least_3_of_4_fold_log_loss_improve",
      "at_least_3_of_4_fold_brier_improve","at_least_3_of_4_fold_auc_improve",
      "at_least_3_of_4_fold_c1_auc_gt_050","loo_log_loss_positive",
      "loo_brier_positive","loo_auc_positive","probability_noncollapsed",
    }
    assert set(comp["precheck_gates"])==expected

def test_temporal_null_shift_contract():
    days={d:_day(d,64,i+20) for i,d in enumerate(p.dd.HISTORICAL_DAYS)}
    c0=p.fit_rep(days,"C0"); c1=p.fit_rep(days,"C1")
    comp=p.comparison(c0,c1)
    comp["pooled_log_loss_improvement"]=0.01
    n=p.temporal_null(c0,c1,comp)
    assert n["eligible_shifts"][0]==10
    assert n["eligible_shifts"][-1]==54

def test_canonical_guard_before_data(tmp_path):
    with pytest.raises(p.P1BError) as exc:
        p.run_p1b(execution_commit="0"*40,output_directory=tmp_path/"x",require_canonical_output=True)
    assert exc.value.reason=="noncanonical_output_directory"

def test_write_once(tmp_path):
    out=tmp_path/"out"
    r=p._write(out,{"x":1})
    assert r.artifact_path.is_file()
    with pytest.raises(p.P1BError) as exc:
        p._write(out,{"x":1})
    assert exc.value.reason=="output_directory_already_exists"

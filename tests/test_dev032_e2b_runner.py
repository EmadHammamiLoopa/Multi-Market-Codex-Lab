from __future__ import annotations

from dataclasses import replace
import numpy as np
import pytest

from multimarket import dev032_e1b_screen_core as e1
from multimarket import dev032_e2b_harness as harness
from multimarket import dev032_e2b_runner as runner

def _fold(fid:int,rep:str):
    ts=np.arange(30,dtype=np.int64)+fid*100
    y=(np.arange(30)%2).astype(np.int8)
    p=np.linspace(.1,.9,30)
    m=e1.probability_metrics(y,p)
    return e1.FoldPrediction(
        fold_id=fid,representation=rep,selected_c=.1,
        timestamps_us=ts,labels=y,probabilities=p,metrics=m,
        inner_c_ledger=({"C":.1,"binary_log_loss":m["binary_log_loss"],"brier":m["brier"],"roc_auc":m["roc_auc"]},),
        prediction_sha256=e1.prediction_sha256(fid,rep,ts,y,p),
    )

def _rep(rep:str):
    folds=tuple(_fold(i,rep) for i in range(1,5))
    y=np.concatenate([f.labels for f in folds])
    p=np.concatenate([f.probabilities for f in folds])
    return e1.RepresentationResult(rep,23,folds,e1.probability_metrics(y,p))

def test_reproduction_gate_exact_pass():
    cur=_rep("B00")
    frozen={
        "pooled_metrics":dict(cur.pooled_metrics),
        "folds":[
            {
                "fold_id":f.fold_id,
                "selected_C":f.selected_c,
                "prediction_sha256":f.prediction_sha256,
            }
            for f in cur.folds
        ],
    }
    z=runner._verify_rep_reproduction(rep_id="B00",current=cur,frozen=frozen)
    assert z["pass"] is True
    assert len(z["folds"])==4

def test_reproduction_gate_hash_mismatch_fails():
    cur=_rep("B00")
    frozen={
        "pooled_metrics":dict(cur.pooled_metrics),
        "folds":[
            {
                "fold_id":f.fold_id,
                "selected_C":f.selected_c,
                "prediction_sha256":("0"*64 if i==0 else f.prediction_sha256),
            }
            for i,f in enumerate(cur.folds)
        ],
    }
    with pytest.raises(runner.E2BRunnerError) as e:
        runner._verify_rep_reproduction(rep_id="B00",current=cur,frozen=frozen)
    assert e.value.reason=="reproduction_prediction_hash"

def test_worker_cap_and_forward_guards():
    assert runner._normalize_workers(100)==10
    assert runner._normalize_workers(0)==1
    assert not any(runner.FORWARD_GUARDS.values())
    assert runner.REAL_OUTPUT_DIRECTORY.name=="dev032_e2b_adaptive_refinement_screen_v1"

def test_family_mapping_complete():
    assert tuple(runner.FAMILY_BY_REFINEMENT)==tuple(f"E2R{i:02d}" for i in range(1,11))
    assert len(set(runner.FAMILY_BY_REFINEMENT.values()))==7

def test_harness_process_pool_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)

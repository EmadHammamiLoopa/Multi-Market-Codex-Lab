from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from . import dev030_p4_touch_composition as p4

NULL_SEED=20260902
NULL_REPLICATES=1999

STATUS_ELIGIBLE="ELIGIBLE_FOR_POLICY_COMPOSITION_DEVELOPMENT"
STATUS_FAIL_PRIMARY="FAIL_PROMOTED_DIRECTION_NO_COMPOSITION_INCREMENT"
STATUS_FAIL_OVERALL="FAIL_PROMOTED_DIRECTION_IMPROVES_P3_BUT_COMPOSITION_NOT_USEFUL"
STATUS_PREEXEC="PREEXECUTION_REPRODUCTION_FAILURE_NO_RESULT"

class C1Error(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class FoldComposition:
    fold_id:int
    labels:np.ndarray
    c0:np.ndarray
    c1:np.ndarray
    c2:np.ndarray
    c3:np.ndarray
    metrics_c0:dict[str,Any]
    metrics_c1:dict[str,Any]
    metrics_c2:dict[str,Any]
    metrics_c3:dict[str,Any]

def compose_systems(*,y3,training_prevalence,p_touch,training_p_long,p3_long,btc45_long):
    y=np.asarray(y3,dtype=np.int8)
    pt=np.asarray(p_touch,dtype=np.float64)
    p3=np.asarray(p3_long,dtype=np.float64)
    p45=np.asarray(btc45_long,dtype=np.float64)
    if not (len(y)==len(pt)==len(p3)==len(p45)):
        raise C1Error("composition_length")
    if np.asarray(training_prevalence).shape!=(3,):
        raise C1Error("training_prevalence_shape")
    c0=np.tile(np.asarray(training_prevalence,dtype=np.float64),(len(y),1))
    c1=p4.compose_probabilities(pt,np.full(len(y),float(training_p_long),dtype=np.float64))
    c2=p4.compose_probabilities(pt,p3)
    c3=p4.compose_probabilities(pt,p45)
    return c0,c1,c2,c3

def fold_composition(*,fold_id,y3,training_prevalence,p_touch,training_p_long,p3_long,btc45_long):
    c0,c1,c2,c3=compose_systems(
        y3=y3,
        training_prevalence=training_prevalence,
        p_touch=p_touch,
        training_p_long=training_p_long,
        p3_long=p3_long,
        btc45_long=btc45_long,
    )
    y=np.asarray(y3,dtype=np.int8)
    return FoldComposition(
        int(fold_id),y,c0,c1,c2,c3,
        p4.multiclass_probability_metrics(y,c0),
        p4.multiclass_probability_metrics(y,c1),
        p4.multiclass_probability_metrics(y,c2),
        p4.multiclass_probability_metrics(y,c3),
    )

def _pooled(folds:Sequence[FoldComposition],field:str,indices:Sequence[int]|None=None):
    if indices is None:
        indices=tuple(range(len(folds)))
    y=np.concatenate([folds[i].labels for i in indices])
    p=np.concatenate([getattr(folds[i],field) for i in indices])
    return p4.multiclass_probability_metrics(y,p)

def comparison(folds:Sequence[FoldComposition],*,base_field:str,test_field:str):
    if len(folds)!=4:
        raise C1Error("fold_count")
    fold_improvements=[]
    for f in folds:
        mb=p4.multiclass_probability_metrics(f.labels,getattr(f,base_field))
        mt=p4.multiclass_probability_metrics(f.labels,getattr(f,test_field))
        fold_improvements.append(float(mb["multiclass_log_loss"]-mt["multiclass_log_loss"]))

    pb=_pooled(folds,base_field)
    pt=_pooled(folds,test_field)

    loo=[]
    for omitted in range(4):
        idx=[i for i in range(4) if i!=omitted]
        mb=_pooled(folds,base_field,idx)
        mt=_pooled(folds,test_field,idx)
        loo.append(float(mb["multiclass_log_loss"]-mt["multiclass_log_loss"]))

    return {
        "pooled_log_loss_improvement":float(pb["multiclass_log_loss"]-pt["multiclass_log_loss"]),
        "pooled_brier_improvement":float(pb["multiclass_brier"]-pt["multiclass_brier"]),
        "pooled_macro_ap_improvement":float(pt["macro_ovr_average_precision"]-pb["macro_ovr_average_precision"]),
        "fold_log_loss_improvement":[float(v) for v in fold_improvements],
        "positive_fold_log_loss_improvements":int(sum(v>0 for v in fold_improvements)),
        "leave_one_fold_out_log_loss_improvement":[float(v) for v in loo],
        "all_loo_log_loss_improvement_positive":bool(all(v>0 for v in loo)),
        "minimum_fold_log_loss_improvement":float(min(fold_improvements)),
        "median_fold_log_loss_improvement":float(np.median(fold_improvements)),
        "base_pooled_metrics":pb,
        "test_pooled_metrics":pt,
    }

def directional_touch_temporal_null(
    folds:Sequence[FoldComposition],
    *,
    seed:int=NULL_SEED,
    replicates:int=NULL_REPLICATES,
):
    if len(folds)!=4:
        raise C1Error("null_fold_count")
    rng=np.random.default_rng(seed)
    legal=[]
    expected=(156,64,121,218)
    for f,n in zip(folds,expected,strict=True):
        touch=np.flatnonzero(f.labels!=0)
        if len(touch)!=n:
            raise C1Error("null_touch_support",f"{f.fold_id}:{len(touch)}")
        vals=np.arange(10,n-9,dtype=np.int64)
        if len(vals)==0:
            raise C1Error("null_shift_empty",str(f.fold_id))
        legal.append(vals)

    observed=comparison(folds,base_field="c2",test_field="c3")["pooled_log_loss_improvement"]
    null=np.empty(replicates,dtype=np.float64)
    shifts=[]

    for r in range(replicates):
        selected=[int(legal[i][rng.integers(0,len(legal[i]))]) for i in range(4)]
        shifts.append(selected)
        ys=[]
        c2=[]
        c3=[]
        for i,f in enumerate(folds):
            y=f.labels.copy()
            touch=np.flatnonzero(y!=0)
            directional=y[touch].copy()
            y[touch]=np.roll(directional,selected[i])
            ys.append(y)
            c2.append(f.c2)
            c3.append(f.c3)
        y=np.concatenate(ys)
        p2=np.concatenate(c2)
        p3=np.concatenate(c3)
        m2=p4.multiclass_probability_metrics(y,p2)
        m3=p4.multiclass_probability_metrics(y,p3)
        null[r]=float(m2["multiclass_log_loss"]-m3["multiclass_log_loss"])

    q95=float(np.quantile(null,0.95,method="higher"))
    empirical=float((1+int(np.sum(null>=observed)))/(replicates+1))
    return {
        "seed":int(seed),
        "replicates":int(replicates),
        "shift_tuples":shifts,
        "null_delta_ll_32":null.tolist(),
        "q95":q95,
        "empirical_p":empirical,
        "observed_delta_ll_32":float(observed),
        "observed_minus_q95":float(observed-q95),
    }

def classify(*,reproduction_ok:bool,vs_c2:dict[str,Any],vs_c1:dict[str,Any],null:dict[str,Any]):
    if not reproduction_ok:
        return STATUS_PREEXEC

    primary=(
        vs_c2["pooled_log_loss_improvement"]>0
        and vs_c2["pooled_brier_improvement"]>0
        and vs_c2["pooled_macro_ap_improvement"]>0
        and vs_c2["positive_fold_log_loss_improvements"]>=3
        and vs_c2["all_loo_log_loss_improvement_positive"]
        and vs_c2["pooled_log_loss_improvement"]>float(null["q95"])
        and float(null["empirical_p"])<=0.05
    )
    if not primary:
        return STATUS_FAIL_PRIMARY

    overall=(
        vs_c1["pooled_log_loss_improvement"]>0
        and vs_c1["pooled_brier_improvement"]>0
        and vs_c1["pooled_macro_ap_improvement"]>0
        and vs_c1["positive_fold_log_loss_improvements"]>=3
        and vs_c1["all_loo_log_loss_improvement_positive"]
    )
    if not overall:
        return STATUS_FAIL_OVERALL

    return STATUS_ELIGIBLE

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,brier_score_loss,f1_score,log_loss,
    matthews_corrcoef,roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

from . import dev032_e1b_screen_core as e1

EXPERIMENT_ID="DEV032-E2B"
DESIGN_VERSION="wave2-adaptive-parent-relative-screen-v1"

C_GRID=(0.01,0.1,1.0,10.0)
RANDOM_STATE=20260825
NULL_SEED=20260902
NULL_REPLICATES=1999

STATUS_SURVIVOR="ADAPTIVE_REFINEMENT_SURVIVOR"
STATUS_INCONCLUSIVE="ADAPTIVE_REFINEMENT_INCONCLUSIVE"
STATUS_REJECTED="ADAPTIVE_REFINEMENT_REJECTED"

class E2BScreenError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class TransformSpec:
    kind:str
    components:int=0

@dataclass(frozen=True)
class FitResult:
    representation:str
    feature_count:int
    folds:tuple[e1.FoldPrediction,...]
    pooled_metrics:dict[str,Any]

def _metrics(y,p):
    y=np.asarray(y,dtype=np.int8);p=np.asarray(p,dtype=np.float64)
    pred=(p>=0.5).astype(np.int8)
    return {
        "support":int(len(y)),
        "long_count":int(np.sum(y==1)),
        "short_count":int(np.sum(y==0)),
        "binary_log_loss":float(log_loss(y,np.column_stack((1-p,p)),labels=[0,1])),
        "brier":float(brier_score_loss(y,p)),
        "roc_auc":float(roc_auc_score(y,p)),
        "balanced_accuracy_at_0_5":float(balanced_accuracy_score(y,pred)),
        "macro_f1_at_0_5":float(f1_score(y,pred,average="macro",zero_division=0)),
        "mcc_at_0_5":float(matthews_corrcoef(y,pred)),
    }

def _model(c):
    return LogisticRegression(
        C=float(c),solver="lbfgs",l1_ratio=0.0,class_weight=None,
        max_iter=1000,fit_intercept=True,random_state=RANDOM_STATE,
    )

def _stack(per_day,days):
    return e1.stack_days(per_day,days)

def _fit_transform(kind:str,raw_fit,raw_other):
    sf=StandardScaler()
    a=sf.fit_transform(raw_fit)
    b=sf.transform(raw_other)
    if kind=="pca":
        tr=PCA(n_components=5,svd_solver="full",whiten=False)
    elif kind=="svd":
        tr=TruncatedSVD(n_components=5,algorithm="randomized",n_iter=7,random_state=20260902)
    else:
        raise E2BScreenError("unknown_transform_kind",kind)
    return tr.fit_transform(a),tr.transform(b)

def _compose(base_fit,extra_fit,base_other,extra_other,spec:TransformSpec):
    if spec.kind=="ordinary":
        return np.concatenate([base_fit,extra_fit],axis=1),np.concatenate([base_other,extra_other],axis=1)
    ef,eo=_fit_transform(spec.kind,extra_fit,extra_other)
    return np.concatenate([base_fit,ef],axis=1),np.concatenate([base_other,eo],axis=1)

def fit_refinement(
    base_days:Mapping[date,e1.DayMatrix],
    raw_extra_days:Mapping[date,e1.DayMatrix],
    folds:Sequence[e1.FoldSpec],
    representation:str,
    spec:TransformSpec,
)->FitResult:
    results=[]
    for fold in folds:
        inner_val=fold.train_days[-1]
        inner_fit=fold.train_days[:-1]

        bif,yif,_=_stack(base_days,inner_fit)
        biv,yiv,_=_stack(base_days,(inner_val,))
        eif,eyif,_=_stack(raw_extra_days,inner_fit)
        eiv,eyiv,_=_stack(raw_extra_days,(inner_val,))
        if not np.array_equal(yif,eyif) or not np.array_equal(yiv,eyiv):
            raise E2BScreenError("inner_label_mismatch",representation)

        cif,civ=_compose(bif,eif,biv,eiv,spec)
        ledger=[]
        for c in C_GRID:
            sc=StandardScaler();a=sc.fit_transform(cif);b=sc.transform(civ)
            m=_model(c);m.fit(a,yif);p=m.predict_proba(b)[:,1]
            q=_metrics(yiv,p)
            ledger.append({"C":float(c),"binary_log_loss":q["binary_log_loss"],"brier":q["brier"],"roc_auc":q["roc_auc"]})
        win=sorted(ledger,key=lambda q:(q["binary_log_loss"],q["brier"],-q["roc_auc"],q["C"]))[0]

        bt,yt,_=_stack(base_days,fold.train_days)
        bv,yv,tv=_stack(base_days,(fold.validation_day,))
        et,eyt,_=_stack(raw_extra_days,fold.train_days)
        ev,eyv,_=_stack(raw_extra_days,(fold.validation_day,))
        if not np.array_equal(yt,eyt) or not np.array_equal(yv,eyv):
            raise E2BScreenError("outer_label_mismatch",representation)

        ct,cv=_compose(bt,et,bv,ev,spec)
        sc=StandardScaler();a=sc.fit_transform(ct);b=sc.transform(cv)
        m=_model(win["C"]);m.fit(a,yt);p=m.predict_proba(b)[:,1]
        results.append(e1.FoldPrediction(
            fold_id=fold.fold_id,representation=representation,selected_c=float(win["C"]),
            timestamps_us=tv,labels=yv,probabilities=p,metrics=_metrics(yv,p),
            inner_c_ledger=tuple(ledger),
            prediction_sha256=e1.prediction_sha256(fold.fold_id,representation,tv,yv,p),
        ))
    y=np.concatenate([z.labels for z in results]);p=np.concatenate([z.probabilities for z in results])
    width=base_days[next(iter(base_days))].values.shape[1] + (5 if spec.kind in ("pca","svd") else raw_extra_days[next(iter(raw_extra_days))].values.shape[1])
    return FitResult(representation,int(width),tuple(results),_metrics(y,p))

def compare(parent:FitResult|e1.RepresentationResult,candidate:FitResult)->dict[str,Any]:
    fold_delta=[]
    for p,c in zip(parent.folds,candidate.folds,strict=True):
        if p.fold_id!=c.fold_id or not np.array_equal(p.timestamps_us,c.timestamps_us) or not np.array_equal(p.labels,c.labels):
            raise E2BScreenError("matched_parent_support")
        fold_delta.append(float(c.metrics["roc_auc"]-p.metrics["roc_auc"]))
    loo=[]
    for omitted in range(4):
        y=np.concatenate([parent.folds[i].labels for i in range(4) if i!=omitted])
        pp=np.concatenate([parent.folds[i].probabilities for i in range(4) if i!=omitted])
        pc=np.concatenate([candidate.folds[i].probabilities for i in range(4) if i!=omitted])
        loo.append(float(roc_auc_score(y,pc)-roc_auc_score(y,pp)))
    return {
        "pooled_auc_delta":float(candidate.pooled_metrics["roc_auc"]-parent.pooled_metrics["roc_auc"]),
        "fold_auc_delta":fold_delta,
        "positive_fold_auc_deltas":int(sum(x>0 for x in fold_delta)),
        "candidate_fold_auc_gt_0_5":int(sum(f.metrics["roc_auc"]>0.5 for f in candidate.folds)),
        "leave_one_fold_out_auc_delta":loo,
        "all_loo_auc_delta_positive":bool(all(x>0 for x in loo)),
        "worst_fold_auc":float(min(f.metrics["roc_auc"] for f in candidate.folds)),
        "pooled_log_loss_improvement":float(parent.pooled_metrics["binary_log_loss"]-candidate.pooled_metrics["binary_log_loss"]),
        "pooled_brier_improvement":float(parent.pooled_metrics["brier"]-candidate.pooled_metrics["brier"]),
    }

def parent_relative_max_stat_null(
    parents:Mapping[str,e1.RepresentationResult],
    candidates:Mapping[str,FitResult],
    parent_by_candidate:Mapping[str,str],
    *,
    seed:int=NULL_SEED,
    replicates:int=NULL_REPLICATES,
)->dict[str,Any]:
    ids=tuple(candidates)
    rng=np.random.default_rng(seed)
    fold_sizes=[len(next(iter(candidates.values())).folds[i].labels) for i in range(4)]
    legal=[np.arange(10,n-9,dtype=np.int64) for n in fold_sizes]
    shift_tuples=[]
    null={rid:np.empty(replicates,dtype=np.float64) for rid in ids}
    maxnull=np.empty(replicates,dtype=np.float64)
    observed={rid:float(candidates[rid].pooled_metrics["roc_auc"]-parents[parent_by_candidate[rid]].pooled_metrics["roc_auc"]) for rid in ids}
    for r in range(replicates):
        shifts=[int(legal[i][rng.integers(0,len(legal[i]))]) for i in range(4)]
        shift_tuples.append(shifts)
        row=[]
        for rid in ids:
            par=parents[parent_by_candidate[rid]];cand=candidates[rid]
            y=np.concatenate([np.roll(par.folds[i].labels,shifts[i]) for i in range(4)])
            pp=np.concatenate([f.probabilities for f in par.folds])
            pc=np.concatenate([f.probabilities for f in cand.folds])
            d=float(roc_auc_score(y,pc)-roc_auc_score(y,pp))
            null[rid][r]=d;row.append(d)
        maxnull[r]=max(row)
    q95=float(np.quantile(maxnull,0.95,method="higher"))
    per={}
    for rid in ids:
        obs=observed[rid]
        per[rid]={
            "observed_parent_relative_auc_delta":obs,
            "raw_empirical_p":float((1+int(np.sum(null[rid]>=obs)))/(1+replicates)),
            "max_stat_fwer_empirical_p":float((1+int(np.sum(maxnull>=obs)))/(1+replicates)),
            "max_stat_q95":q95,
            "observed_minus_q95":float(obs-q95),
        }
    return {
        "seed":seed,"replicates":replicates,"candidate_ids":list(ids),
        "fold_sizes":fold_sizes,"shift_tuples":shift_tuples,
        "max_stat_null":maxnull.tolist(),"max_stat_q95":q95,"per_candidate":per,
    }

def classify(candidate:FitResult,comp:Mapping[str,Any],null_rec:Mapping[str,Any],baseline_auc:float)->str:
    auc=float(candidate.pooled_metrics["roc_auc"])
    stable=(comp["pooled_auc_delta"]>0 and comp["positive_fold_auc_deltas"]>=3 and comp["all_loo_auc_delta_positive"])
    strong=(stable and auc>baseline_auc and auc>=0.56 and comp["candidate_fold_auc_gt_0_5"]>=3 and comp["pooled_auc_delta"]>null_rec["max_stat_q95"] and null_rec["max_stat_fwer_empirical_p"]<=0.05)
    if strong:return STATUS_SURVIVOR
    if stable:return STATUS_INCONCLUSIVE
    return STATUS_REJECTED

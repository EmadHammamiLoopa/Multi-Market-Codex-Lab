from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import struct
from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

from . import dev030_direction_dataset as dd

C_GRID=(0.01,0.1,1.0,10.0)
THRESHOLD=0.5
RANDOM_STATE=20260825
NULL_SEED=20260902
NULL_REPLICATES=1999
CANDIDATE_IDS=("G4C01","G4C02","G4C03")

STATUS_SURVIVOR="G4_LAYER_SURVIVOR"
STATUS_INCONCLUSIVE="G4_LAYER_INCONCLUSIVE"
STATUS_REJECTED="G4_LAYER_REJECTED"

class G4BError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class FoldResult:
    fold_id:int
    selected_c:float
    timestamps_us:np.ndarray
    labels:np.ndarray
    probabilities:np.ndarray
    predictions:np.ndarray
    metrics:dict[str,Any]
    inner_c_ledger:tuple[dict[str,Any],...]
    prediction_sha256:str

@dataclass(frozen=True)
class CandidateResult:
    candidate_id:str
    feature_count:int
    folds:tuple[FoldResult,...]
    pooled_metrics:dict[str,Any]

def metrics(y,p):
    y=np.asarray(y,dtype=np.int8)
    p=np.asarray(p,dtype=np.float64)
    pred=(p>=THRESHOLD).astype(np.int8)
    if len(y)!=len(p) or len(y)==0:
        raise G4BError("metric_length")
    if not np.all(np.isfinite(p)):
        raise G4BError("metric_nonfinite")
    cm=np.zeros((2,2),dtype=np.int64)
    for a,b in zip(y,pred,strict=True):
        cm[int(a),int(b)]+=1
    counts=np.bincount(pred,minlength=2)
    precision,recall,f1,support=precision_recall_fscore_support(
        y,pred,labels=[0,1],zero_division=0
    )
    return {
        "support":int(len(y)),
        "long_count":int(np.sum(y==1)),
        "short_count":int(np.sum(y==0)),
        "predicted_long_count":int(counts[1]),
        "predicted_short_count":int(counts[0]),
        "balanced_accuracy":float(balanced_accuracy_score(y,pred)),
        "macro_f1":float(f1_score(y,pred,average="macro",zero_division=0)),
        "mcc":float(matthews_corrcoef(y,pred)),
        "roc_auc_diagnostic":float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,
        "confusion_matrix_short_long":cm.tolist(),
        "per_class":{
            "SHORT":{"precision":float(precision[0]),"recall":float(recall[0]),"f1":float(f1[0]),"support":int(support[0])},
            "LONG":{"precision":float(precision[1]),"recall":float(recall[1]),"f1":float(f1[1]),"support":int(support[1])},
        },
    }

def _model(c):
    if float(c) not in C_GRID:
        raise G4BError("C_not_frozen")
    return LogisticRegression(
        C=float(c),solver="lbfgs",l1_ratio=0.0,class_weight=None,
        max_iter=1000,fit_intercept=True,random_state=RANDOM_STATE,
    )

def _stack(per_day:Mapping[date,tuple[np.ndarray,np.ndarray,np.ndarray]],days:Sequence[date]):
    xs=[];ys=[];ts=[]
    for d in days:
        x,y,t=per_day[d]
        xs.append(np.asarray(x,dtype=np.float64))
        ys.append(np.asarray(y,dtype=np.int8))
        ts.append(np.asarray(t,dtype=np.int64))
    x=np.concatenate(xs);y=np.concatenate(ys);t=np.concatenate(ts)
    if len(t) and np.any(np.diff(t)<=0):
        raise G4BError("stack_chronology")
    if not np.all(np.isfinite(x)):
        raise G4BError("stack_nonfinite")
    if not np.all(np.isin(y,(0,1))):
        raise G4BError("stack_labels")
    return x,y,t

def select_c(xfit,yfit,xval,yval):
    ledger=[]
    for c in C_GRID:
        scaler=StandardScaler()
        a=scaler.fit_transform(xfit)
        b=scaler.transform(xval)
        m=_model(c);m.fit(a,yfit)
        p=m.predict_proba(b)[:,1]
        q=metrics(yval,p)
        ledger.append({"C":float(c),"balanced_accuracy":q["balanced_accuracy"],"macro_f1":q["macro_f1"]})
    selected=sorted(ledger,key=lambda z:(-z["balanced_accuracy"],-z["macro_f1"],z["C"]))[0]
    return float(selected["C"]),tuple(ledger)

def prediction_sha256(cid,fold_id,ts,y,pred,p):
    h=hashlib.sha256(b"DEV035-G4B-PREDICTION-V1\0")
    h.update(str(cid).encode("ascii"));h.update(struct.pack(">I",int(fold_id)))
    for t,a,b,q in zip(np.asarray(ts,dtype=np.int64),np.asarray(y,dtype=np.int8),np.asarray(pred,dtype=np.int8),np.asarray(p,dtype=np.float64),strict=True):
        h.update(struct.pack(">qbbd",int(t),int(a),int(b),float(q)))
    return h.hexdigest()

def fit_candidate(cid,per_day,folds=dd.OUTER_FOLDS):
    out=[];feature_count=None
    for outer in folds:
        inner_val=outer.train_days[-1]
        inner_fit=outer.train_days[:-1]
        xif,yif,_=_stack(per_day,inner_fit)
        xiv,yiv,_=_stack(per_day,(inner_val,))
        c,ledger=select_c(xif,yif,xiv,yiv)
        xt,yt,_=_stack(per_day,outer.train_days)
        xv,yv,tv=_stack(per_day,(outer.validation_day,))
        if feature_count is None:
            feature_count=int(xt.shape[1])
        elif feature_count!=int(xt.shape[1]):
            raise G4BError("feature_count_drift",cid)
        scaler=StandardScaler();a=scaler.fit_transform(xt);b=scaler.transform(xv)
        m=_model(c);m.fit(a,yt)
        p=m.predict_proba(b)[:,1];pred=(p>=THRESHOLD).astype(np.int8)
        out.append(FoldResult(
            int(outer.fold_id),c,tv,yv,p,pred,metrics(yv,p),ledger,
            prediction_sha256(cid,outer.fold_id,tv,yv,pred,p),
        ))
    folds_t=tuple(out)
    y=np.concatenate([f.labels for f in folds_t]);p=np.concatenate([f.probabilities for f in folds_t])
    return CandidateResult(cid,int(feature_count),folds_t,metrics(y,p))

def _aligned(base,cand):
    if len(base.folds)!=4 or len(cand.folds)!=4:
        raise G4BError("fold_count")
    for b,c in zip(base.folds,cand.folds,strict=True):
        if b.fold_id!=c.fold_id:
            raise G4BError("fold_id_alignment")
        if not np.array_equal(b.timestamps_us,c.timestamps_us):
            raise G4BError("support_alignment")
        if not np.array_equal(b.labels,c.labels):
            raise G4BError("label_alignment")

def compare(base,cand):
    _aligned(base,cand)
    fold_delta=[float(c.metrics["balanced_accuracy"]-b.metrics["balanced_accuracy"]) for b,c in zip(base.folds,cand.folds,strict=True)]
    loo=[]
    for omitted in range(4):
        y=np.concatenate([cand.folds[i].labels for i in range(4) if i!=omitted])
        cp=np.concatenate([cand.folds[i].predictions for i in range(4) if i!=omitted])
        bp=np.concatenate([base.folds[i].predictions for i in range(4) if i!=omitted])
        loo.append(float(balanced_accuracy_score(y,cp)-balanced_accuracy_score(y,bp)))
    total=int(cand.pooled_metrics["support"])
    minority=min(int(cand.pooled_metrics["predicted_long_count"]),int(cand.pooled_metrics["predicted_short_count"]))/total
    return {
        "pooled_delta_balanced_accuracy":float(cand.pooled_metrics["balanced_accuracy"]-base.pooled_metrics["balanced_accuracy"]),
        "fold_delta_balanced_accuracy":fold_delta,
        "positive_fold_deltas":int(sum(v>0 for v in fold_delta)),
        "candidate_fold_ba_gt_0_50":int(sum(f.metrics["balanced_accuracy"]>0.50 for f in cand.folds)),
        "both_classes_predicted_all_folds":bool(all(f.metrics["predicted_long_count"]>0 and f.metrics["predicted_short_count"]>0 for f in cand.folds)),
        "predicted_minority_fraction":float(minority),
        "leave_one_fold_out_delta_balanced_accuracy":loo,
        "all_loo_delta_positive":bool(all(v>0 for v in loo)),
        "worst_fold_balanced_accuracy":float(min(f.metrics["balanced_accuracy"] for f in cand.folds)),
        "median_fold_delta_balanced_accuracy":float(np.median(fold_delta)),
        "minimum_fold_delta_balanced_accuracy":float(min(fold_delta)),
    }

def joint_max_stat_null(base,candidates,*,seed=NULL_SEED,replicates=NULL_REPLICATES):
    ids=tuple(candidates)
    if ids!=CANDIDATE_IDS:
        raise G4BError("null_candidate_order")
    for cid in ids:_aligned(base,candidates[cid])
    rng=np.random.default_rng(seed)
    legal=[]
    for f in base.folds:
        n=len(f.labels);vals=np.arange(10,n-9,dtype=np.int64)
        if len(vals)==0:raise G4BError("null_legal_shift_empty",str(f.fold_id))
        legal.append(vals)
    observed={cid:float(candidates[cid].pooled_metrics["balanced_accuracy"]-base.pooled_metrics["balanced_accuracy"]) for cid in ids}
    null={cid:np.empty(replicates,dtype=np.float64) for cid in ids}
    maxnull=np.empty(replicates,dtype=np.float64);shifts=[]
    bp=np.concatenate([f.predictions for f in base.folds])
    for r in range(replicates):
        sh=[int(legal[i][rng.integers(0,len(legal[i]))]) for i in range(4)]
        shifts.append(sh)
        y=np.concatenate([np.roll(base.folds[i].labels,sh[i]) for i in range(4)])
        bba=float(balanced_accuracy_score(y,bp));row=[]
        for cid in ids:
            cp=np.concatenate([f.predictions for f in candidates[cid].folds])
            d=float(balanced_accuracy_score(y,cp)-bba)
            null[cid][r]=d;row.append(d)
        maxnull[r]=max(row)
    q95=float(np.quantile(maxnull,0.95,method="higher"))
    per={}
    for cid in ids:
        obs=observed[cid]
        per[cid]={
            "observed_delta_balanced_accuracy":obs,
            "raw_empirical_p":float((1+int(np.sum(null[cid]>=obs)))/(replicates+1)),
            "max_stat_fwer_empirical_p":float((1+int(np.sum(maxnull>=obs)))/(replicates+1)),
            "max_stat_q95":q95,
            "observed_minus_q95":float(obs-q95),
        }
    return {
        "seed":int(seed),"replicates":int(replicates),"candidate_ids":list(ids),
        "shift_tuples":shifts,
        "candidate_null_vectors":{cid:null[cid].tolist() for cid in ids},
        "max_stat_null":maxnull.tolist(),"max_stat_q95":q95,"per_candidate":per,
    }

def classify(cand,comp,nullrec):
    ba=float(cand.pooled_metrics["balanced_accuracy"])
    delta=float(comp["pooled_delta_balanced_accuracy"])
    stable=delta>0 and comp["positive_fold_deltas"]>=3 and comp["all_loo_delta_positive"]
    strong=(
        stable and ba>=0.59 and delta>=0.015
        and comp["candidate_fold_ba_gt_0_50"]>=3
        and comp["both_classes_predicted_all_folds"]
        and comp["predicted_minority_fraction"]>=0.10
        and delta>float(nullrec["max_stat_q95"])
        and float(nullrec["max_stat_fwer_empirical_p"])<=0.05
    )
    if strong:return STATUS_SURVIVOR
    if stable:return STATUS_INCONCLUSIVE
    return STATUS_REJECTED

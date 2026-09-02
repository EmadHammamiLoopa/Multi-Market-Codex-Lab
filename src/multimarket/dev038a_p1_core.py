from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss, log_loss

CANDIDATE_IDS=("A0","A1","A2","A3","A4")
CHALLENGER_IDS=("A1","A2","A3","A4")
NULL_SEED=20260903
NULL_REPLICATES=1999

class P1Error(RuntimeError):
    pass

def metrics(y_true,p):
    y=np.asarray(y_true,dtype=np.int8)
    p=np.asarray(p,dtype=np.float64)
    if y.ndim!=1 or p.ndim!=1 or len(y)!=len(p) or len(y)==0:
        raise P1Error("metric_shape")
    if len(np.unique(y))!=2:
        raise P1Error("metric_classes")
    if not np.all(np.isfinite(p)) or np.any((p<0)|(p>1)):
        raise P1Error("metric_probability")
    prevalence=float(np.mean(y))
    order=np.argsort(-p,kind="mergesort")
    k=max(1,int(np.ceil(0.10*len(y))))
    top=order[:k]
    top_precision=float(np.mean(y[top]))
    return {
        "support":int(len(y)),
        "touch_count":int(np.sum(y==1)),
        "none_count":int(np.sum(y==0)),
        "touch_prevalence":prevalence,
        "average_precision":float(average_precision_score(y,p)),
        "roc_auc":float(roc_auc_score(y,p)),
        "brier":float(brier_score_loss(y,p)),
        "log_loss":float(log_loss(y,np.column_stack((1-p,p)),labels=[0,1])),
        "top_decile_count":int(k),
        "top_decile_touch_count":int(np.sum(y[top]==1)),
        "top_decile_precision":top_precision,
        "top_decile_lift_vs_prevalence":float(top_precision/prevalence) if prevalence>0 else None,
    }

def pooled_metrics(folds:Sequence[dict]):
    y=np.concatenate([np.asarray(f["y"],dtype=np.int8) for f in folds])
    p=np.concatenate([np.asarray(f["p"],dtype=np.float64) for f in folds])
    out=metrics(y,p)
    top_touch=sum(int(f["metrics"]["top_decile_touch_count"]) for f in folds)
    top_n=sum(int(f["metrics"]["top_decile_count"]) for f in folds)
    prev=float(np.mean(y))
    top_prec=float(top_touch/top_n)
    out["top_decile_count"]=int(top_n)
    out["top_decile_touch_count"]=int(top_touch)
    out["top_decile_precision"]=top_prec
    out["top_decile_lift_vs_prevalence"]=float(top_prec/prev) if prev>0 else None
    return out

def compare(base:Sequence[dict],cand:Sequence[dict]):
    if len(base)!=4 or len(cand)!=4:
        raise P1Error("fold_count")
    fold_delta=[]
    for b,c in zip(base,cand,strict=True):
        if b["fold_id"]!=c["fold_id"] or not np.array_equal(b["y"],c["y"]):
            raise P1Error("fold_alignment")
        fold_delta.append(float(c["metrics"]["average_precision"]-b["metrics"]["average_precision"]))
    bp=pooled_metrics(base)
    cp=pooled_metrics(cand)
    loo=[]
    for omit in range(4):
        b=pooled_metrics([f for i,f in enumerate(base) if i!=omit])
        c=pooled_metrics([f for i,f in enumerate(cand) if i!=omit])
        loo.append(float(c["average_precision"]-b["average_precision"]))
    return {
        "pooled_delta_ap":float(cp["average_precision"]-bp["average_precision"]),
        "fold_delta_ap":[float(x) for x in fold_delta],
        "positive_fold_deltas":int(sum(x>0 for x in fold_delta)),
        "minimum_fold_delta_ap":float(min(fold_delta)),
        "median_fold_delta_ap":float(np.median(fold_delta)),
        "leave_one_fold_out_delta_ap":[float(x) for x in loo],
        "all_loo_delta_positive":bool(all(x>0 for x in loo)),
        "base_pooled_metrics":bp,
        "candidate_pooled_metrics":cp,
    }

def joint_max_stat_null(candidate_folds:Mapping[str,Sequence[dict]],*,seed=NULL_SEED,replicates=NULL_REPLICATES):
    if tuple(candidate_folds)!=CANDIDATE_IDS:
        raise P1Error("candidate_order")
    base_labels=[np.asarray(f["y"],dtype=np.int8) for f in candidate_folds["A0"]]
    preds={cid:[np.asarray(f["p"],dtype=np.float64) for f in candidate_folds[cid]] for cid in CANDIDATE_IDS}
    legal=[np.arange(30,len(y)-29,dtype=np.int64) for y in base_labels]
    if any(len(v)==0 for v in legal):
        raise P1Error("legal_shift_empty")
    observed={cid:compare(candidate_folds["A0"],candidate_folds[cid])["pooled_delta_ap"] for cid in CHALLENGER_IDS}
    rng=np.random.default_rng(seed)
    null={cid:np.empty(replicates,dtype=np.float64) for cid in CHALLENGER_IDS}
    maxnull=np.empty(replicates,dtype=np.float64)
    shifts=[]
    for r in range(replicates):
        sh=[int(legal[i][rng.integers(0,len(legal[i]))]) for i in range(4)]
        shifts.append(sh)
        shifted=[np.roll(base_labels[i],sh[i]) for i in range(4)]
        y=np.concatenate(shifted)
        bap=float(average_precision_score(y,np.concatenate(preds["A0"])))
        row=[]
        for cid in CHALLENGER_IDS:
            ap=float(average_precision_score(y,np.concatenate(preds[cid])))
            d=float(ap-bap)
            null[cid][r]=d
            row.append(d)
        maxnull[r]=max(row)
    q95=float(np.quantile(maxnull,0.95,method="higher"))
    per={}
    for cid in CHALLENGER_IDS:
        obs=float(observed[cid])
        per[cid]={
            "observed_delta_ap":obs,
            "max_stat_q95":q95,
            "observed_minus_q95":float(obs-q95),
            "raw_empirical_p":float((1+int(np.sum(null[cid]>=obs)))/(replicates+1)),
            "max_stat_fwer_empirical_p":float((1+int(np.sum(maxnull>=obs)))/(replicates+1)),
        }
    return {
        "seed":int(seed),
        "replicates":int(replicates),
        "shift_tuples":shifts,
        "candidate_null_vectors":{k:v.tolist() for k,v in null.items()},
        "max_stat_null":maxnull.tolist(),
        "max_stat_q95":q95,
        "per_candidate":per,
    }

def is_survivor(comp:dict[str,Any],nullrec:dict[str,Any]):
    bp=comp["base_pooled_metrics"]
    cp=comp["candidate_pooled_metrics"]
    return bool(
        comp["pooled_delta_ap"]>=0.015
        and comp["positive_fold_deltas"]>=3
        and comp["all_loo_delta_positive"]
        and cp["brier"]<=bp["brier"]
        and cp["log_loss"]<=bp["log_loss"]
        and comp["pooled_delta_ap"]>float(nullrec["max_stat_q95"])
        and float(nullrec["max_stat_fwer_empirical_p"])<=0.05
    )

def rank(records:Mapping[str,dict[str,Any]]):
    complexity={"A1":1,"A2":2,"A3":3,"A4":4}
    survivors=[cid for cid in CHALLENGER_IDS if records[cid]["survivor"]]
    return sorted(
        survivors,
        key=lambda cid:(
            float(records[cid]["null"]["max_stat_fwer_empirical_p"]),
            -float(records[cid]["comparison"]["minimum_fold_delta_ap"]),
            -float(records[cid]["comparison"]["median_fold_delta_ap"]),
            -float(records[cid]["comparison"]["pooled_delta_ap"]),
            float(records[cid]["comparison"]["candidate_pooled_metrics"]["brier"]),
            float(records[cid]["comparison"]["candidate_pooled_metrics"]["log_loss"]),
            complexity[cid],
            cid,
        )
    )

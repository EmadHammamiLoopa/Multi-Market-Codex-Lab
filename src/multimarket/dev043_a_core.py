from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

CANDIDATE_IDS=(
    "A0_TOUCH_PRICE_LOGIT",
    "A1_TOUCH_PRESSURE_LOGIT",
    "A2_TOUCH_COMBINED_HGB",
)
NULL_REPLICATES=1999
NULL_SEED=20260903
MIN_SHIFT_POSITIONS=60

class StageAError(RuntimeError):
    pass

def make_estimator(candidate_id:str):
    if candidate_id in CANDIDATE_IDS[:2]:
        return Pipeline([
            ("scale",StandardScaler()),
            ("model",LogisticRegression(
                solver="lbfgs",
                penalty="l2",
                C=1.0,
                max_iter=3000,
                class_weight=None,
            )),
        ])
    if candidate_id=="A2_TOUCH_COMBINED_HGB":
        return HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=200,
            max_leaf_nodes=15,
            max_depth=None,
            min_samples_leaf=20,
            l2_regularization=1.0,
            max_bins=255,
            categorical_features=None,
            class_weight=None,
            early_stopping=False,
            monotonic_cst=None,
            random_state=20260903,
        )
    raise StageAError(f"unknown_candidate:{candidate_id}")

def touch_probability(model,X)->np.ndarray:
    p=np.asarray(model.predict_proba(X),dtype=np.float64)
    classes=np.asarray(model.classes_,dtype=np.int64)
    if p.ndim!=2 or p.shape[1]!=2 or set(classes.tolist())!={0,1}:
        raise StageAError(f"probability_schema:{classes.tolist()}")
    pos={int(c):i for i,c in enumerate(classes.tolist())}
    out=p[:,pos[1]]
    if np.any(~np.isfinite(out)) or np.any(out<0) or np.any(out>1):
        raise StageAError("probability_values")
    return out

def metrics(y_true,p_touch):
    y=np.asarray(y_true,dtype=np.int8)
    p=np.asarray(p_touch,dtype=np.float64)
    if len(y)==0 or p.shape!=(len(y),):
        raise StageAError("metric_shape")
    if set(np.unique(y).tolist())!={0,1}:
        raise StageAError("metric_requires_both_classes")
    prev=float(np.mean(y))
    pred=(p>=0.5).astype(np.int8)
    ap=float(average_precision_score(y,p))
    return {
        "support":int(len(y)),
        "touch_count":int(np.sum(y==1)),
        "none_count":int(np.sum(y==0)),
        "touch_prevalence":prev,
        "touch_average_precision":ap,
        "ap_lift_over_prevalence":float(ap-prev),
        "roc_auc":float(roc_auc_score(y,p)),
        "brier":float(brier_score_loss(y,p)),
        "prior_brier":float(prev*(1.0-prev)),
        "log_loss":float(log_loss(y,np.column_stack((1.0-p,p)),labels=[0,1])),
        "balanced_accuracy":float(balanced_accuracy_score(y,pred)),
        "confusion_matrix":confusion_matrix(y,pred,labels=[0,1]).tolist(),
    }

def pooled_and_fold_metrics(folds:Sequence[Mapping[str,Any]]):
    pooled_y=np.concatenate([np.asarray(f["y"],dtype=np.int8) for f in folds])
    pooled_p=np.concatenate([np.asarray(f["p_touch"],dtype=np.float64) for f in folds])
    pooled=metrics(pooled_y,pooled_p)
    per=[]
    for f in folds:
        m=metrics(f["y"],f["p_touch"])
        per.append({"fold_id":int(f["fold_id"]),"validation_day":f["validation_day"],**m})
    loo=[]
    for omit in range(len(folds)):
        yy=np.concatenate([np.asarray(f["y"],dtype=np.int8) for i,f in enumerate(folds) if i!=omit])
        pp=np.concatenate([np.asarray(f["p_touch"],dtype=np.float64) for i,f in enumerate(folds) if i!=omit])
        m=metrics(yy,pp)
        loo.append({
            "omitted_fold_id":int(folds[omit]["fold_id"]),
            "ap_lift_over_prevalence":float(m["ap_lift_over_prevalence"]),
            "touch_average_precision":float(m["touch_average_precision"]),
            "touch_prevalence":float(m["touch_prevalence"]),
        })
    return pooled,per,loo

def joint_temporal_max_stat_null(
    *,
    candidate_folds:Mapping[str,Sequence[Mapping[str,Any]]],
    replicates:int=NULL_REPLICATES,
    seed:int=NULL_SEED,
):
    if tuple(candidate_folds)!=CANDIDATE_IDS:
        raise StageAError("candidate_order")
    if any(len(candidate_folds[cid])!=4 for cid in CANDIDATE_IDS):
        raise StageAError("fold_count")

    reference=candidate_folds[CANDIDATE_IDS[0]]
    fold_lengths=[len(np.asarray(f["y"])) for f in reference]
    for i,n in enumerate(fold_lengths):
        if n<=2*MIN_SHIFT_POSITIONS:
            raise StageAError(f"fold_too_short:{i}:{n}")
        refy=np.asarray(reference[i]["y"],dtype=np.int8)
        for cid in CANDIDATE_IDS[1:]:
            cur=candidate_folds[cid][i]
            if not np.array_equal(np.asarray(cur["y"],dtype=np.int8),refy):
                raise StageAError(f"label_misalignment:{cid}:{i}")
            if len(np.asarray(cur["p_touch"]))!=n:
                raise StageAError(f"probability_length:{cid}:{i}")

    pooled_y=np.concatenate([np.asarray(f["y"],dtype=np.int8) for f in reference])
    pooled_prev=float(np.mean(pooled_y))

    observed={}
    for cid in CANDIDATE_IDS:
        pooled_p=np.concatenate([np.asarray(f["p_touch"],dtype=np.float64) for f in candidate_folds[cid]])
        observed[cid]=float(average_precision_score(pooled_y,pooled_p)-pooled_prev)

    legal=[np.arange(MIN_SHIFT_POSITIONS,n-MIN_SHIFT_POSITIONS+1,dtype=np.int64) for n in fold_lengths]
    rng=np.random.default_rng(int(seed))
    maxnull=np.empty(int(replicates),dtype=np.float64)
    shifts=[]

    for r in range(int(replicates)):
        s=tuple(int(legal[i][rng.integers(0,len(legal[i]))]) for i in range(4))
        shifts.append(s)
        shifted_y=np.concatenate([
            np.roll(np.asarray(reference[i]["y"],dtype=np.int8),s[i])
            for i in range(4)
        ])
        row=[]
        for cid in CANDIDATE_IDS:
            pooled_p=np.concatenate([
                np.asarray(candidate_folds[cid][i]["p_touch"],dtype=np.float64)
                for i in range(4)
            ])
            row.append(float(average_precision_score(shifted_y,pooled_p)-pooled_prev))
        maxnull[r]=max(row)

    q95=float(np.quantile(maxnull,0.95,method="higher"))
    per={}
    for cid in CANDIDATE_IDS:
        obs=observed[cid]
        p=float((1+int(np.sum(maxnull>=obs)))/(int(replicates)+1))
        per[cid]={
            "observed_ap_lift":obs,
            "joint_max_stat_q95":q95,
            "observed_minus_q95":float(obs-q95),
            "max_stat_fwer_empirical_p":p,
            "passes_joint_null":bool(obs>q95 and p<=0.05),
        }
    return {
        "seed":int(seed),
        "replicates":int(replicates),
        "minimum_shift_positions":int(MIN_SHIFT_POSITIONS),
        "joint_max_stat_q95":q95,
        "shift_tuples":[list(x) for x in shifts],
        "max_stat_null":maxnull.tolist(),
        "per_candidate":per,
    }

def eligibility(record:Mapping[str,Any],null_record:Mapping[str,Any]):
    pooled=record["pooled"]
    per=record["per_fold"]
    loo=record["leave_one_fold_out"]
    gates={
        "four_outer_folds":len(per)==4,
        "pooled_ap_gt_prevalence":float(pooled["touch_average_precision"])>float(pooled["touch_prevalence"]),
        "pooled_ap_lift_ge_005":float(pooled["ap_lift_over_prevalence"])>=0.05,
        "positive_ap_lift_ge_3_folds":sum(float(x["ap_lift_over_prevalence"])>0 for x in per)>=3,
        "all_loo_ap_lifts_positive":len(loo)==4 and all(float(x["ap_lift_over_prevalence"])>0 for x in loo),
        "pooled_roc_auc_gt_060":float(pooled["roc_auc"])>0.60,
        "pooled_brier_better_than_prior":float(pooled["brier"])<float(pooled["prior_brier"]),
        "fwer_p_le_005":float(null_record["max_stat_fwer_empirical_p"])<=0.05,
        "observed_ap_lift_gt_joint_q95":float(null_record["observed_ap_lift"])>float(null_record["joint_max_stat_q95"]),
    }
    return bool(all(gates.values())),gates

def rank(records:Mapping[str,Mapping[str,Any]]):
    complexity={cid:i for i,cid in enumerate(CANDIDATE_IDS)}
    eligible=[cid for cid in CANDIDATE_IDS if records[cid]["eligible"]]
    return sorted(eligible,key=lambda cid:(
        -min(float(x["ap_lift_over_prevalence"]) for x in records[cid]["per_fold"]),
        -float(records[cid]["pooled"]["ap_lift_over_prevalence"]),
        -min(float(x["ap_lift_over_prevalence"]) for x in records[cid]["leave_one_fold_out"]),
        -float(records[cid]["pooled"]["roc_auc"]),
        float(records[cid]["pooled"]["brier"]),
        complexity[cid],
        cid,
    ))

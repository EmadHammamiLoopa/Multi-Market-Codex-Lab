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
    "B0_DIR_PRICE_LOGIT",
    "B1_DIR_PRESSURE_LOGIT",
    "B2_DIR_COMBINED_HGB",
)
NULL_REPLICATES=1999
NULL_SEED=20260903
MIN_SHIFT_POSITIONS=60

# Stage-B binary coding:
# 0 = SHORT_FIRST
# 1 = LONG_FIRST
DIR_SHORT=0
DIR_LONG=1

class StageBError(RuntimeError):
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
    if candidate_id=="B2_DIR_COMBINED_HGB":
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
    raise StageBError(f"unknown_candidate:{candidate_id}")

def long_probability(model,X)->np.ndarray:
    raw=np.asarray(model.predict_proba(X),dtype=np.float64)
    classes=np.asarray(model.classes_,dtype=np.int64)
    if raw.ndim!=2 or raw.shape[1]!=2 or set(classes.tolist())!={0,1}:
        raise StageBError(f"probability_schema:{classes.tolist()}")
    pos={int(c):i for i,c in enumerate(classes.tolist())}
    p=raw[:,pos[DIR_LONG]]
    if np.any(~np.isfinite(p)) or np.any(p<0) or np.any(p>1):
        raise StageBError("probability_values")
    return p

def prior_log_loss_from_labels(y_true)->float:
    y=np.asarray(y_true,dtype=np.int8)
    if len(y)==0 or set(np.unique(y).tolist())!={0,1}:
        raise StageBError("prior_loss_requires_both_classes")
    p=float(np.mean(y))
    eps=1e-15
    p=min(max(p,eps),1-eps)
    return float(-(p*np.log(p)+(1-p)*np.log(1-p)))

def metrics(y_true,p_long):
    y=np.asarray(y_true,dtype=np.int8)
    p=np.asarray(p_long,dtype=np.float64)
    if len(y)==0 or p.shape!=(len(y),):
        raise StageBError("metric_shape")
    if set(np.unique(y).tolist())!={0,1}:
        raise StageBError("metric_requires_both_classes")

    pred=(p>=0.5).astype(np.int8)
    prev_long=float(np.mean(y))
    ba=float(balanced_accuracy_score(y,pred))
    ap_long=float(average_precision_score(y,p))
    ap_short=float(average_precision_score(1-y,1-p))

    return {
        "support":int(len(y)),
        "long_count":int(np.sum(y==1)),
        "short_count":int(np.sum(y==0)),
        "long_prevalence":prev_long,
        "balanced_accuracy":ba,
        "balanced_accuracy_lift_over_050":float(ba-0.50),
        "roc_auc":float(roc_auc_score(y,p)),
        "brier":float(brier_score_loss(y,p)),
        "log_loss":float(log_loss(y,np.column_stack((1-p,p)),labels=[0,1])),
        "prior_log_loss":prior_log_loss_from_labels(y),
        "ap_long":ap_long,
        "ap_short":ap_short,
        "macro_ap":float((ap_long+ap_short)/2.0),
        "confusion_matrix":confusion_matrix(y,pred,labels=[0,1]).tolist(),
    }

def pooled_and_fold_metrics(folds:Sequence[Mapping[str,Any]]):
    pooled_y=np.concatenate([np.asarray(f["y"],dtype=np.int8) for f in folds])
    pooled_p=np.concatenate([np.asarray(f["p_long"],dtype=np.float64) for f in folds])
    pooled=metrics(pooled_y,pooled_p)

    per=[]
    for f in folds:
        m=metrics(f["y"],f["p_long"])
        per.append({
            "fold_id":int(f["fold_id"]),
            "validation_day":f["validation_day"],
            **m,
        })

    loo=[]
    for omit in range(len(folds)):
        yy=np.concatenate([
            np.asarray(f["y"],dtype=np.int8)
            for i,f in enumerate(folds) if i!=omit
        ])
        pp=np.concatenate([
            np.asarray(f["p_long"],dtype=np.float64)
            for i,f in enumerate(folds) if i!=omit
        ])
        m=metrics(yy,pp)
        loo.append({
            "omitted_fold_id":int(folds[omit]["fold_id"]),
            "balanced_accuracy":float(m["balanced_accuracy"]),
            "balanced_accuracy_lift_over_050":float(m["balanced_accuracy_lift_over_050"]),
            "roc_auc":float(m["roc_auc"]),
        })
    return pooled,per,loo

def joint_temporal_max_stat_null(
    *,
    candidate_folds:Mapping[str,Sequence[Mapping[str,Any]]],
    replicates:int=NULL_REPLICATES,
    seed:int=NULL_SEED,
):
    if tuple(candidate_folds)!=CANDIDATE_IDS:
        raise StageBError("candidate_order")
    if any(len(candidate_folds[cid])!=4 for cid in CANDIDATE_IDS):
        raise StageBError("fold_count")

    reference=candidate_folds[CANDIDATE_IDS[0]]
    lengths=[len(np.asarray(f["y"])) for f in reference]

    for i,n in enumerate(lengths):
        if n<=2*MIN_SHIFT_POSITIONS:
            raise StageBError(f"fold_too_short:{i}:{n}")
        refy=np.asarray(reference[i]["y"],dtype=np.int8)
        if set(np.unique(refy).tolist())!={0,1}:
            raise StageBError(f"fold_missing_class:{i}")
        for cid in CANDIDATE_IDS[1:]:
            cur=candidate_folds[cid][i]
            if not np.array_equal(np.asarray(cur["y"],dtype=np.int8),refy):
                raise StageBError(f"label_misalignment:{cid}:{i}")
            if len(np.asarray(cur["p_long"]))!=n:
                raise StageBError(f"probability_length:{cid}:{i}")

    pooled_y=np.concatenate([np.asarray(f["y"],dtype=np.int8) for f in reference])

    observed={}
    for cid in CANDIDATE_IDS:
        pooled_p=np.concatenate([
            np.asarray(f["p_long"],dtype=np.float64)
            for f in candidate_folds[cid]
        ])
        pred=(pooled_p>=0.5).astype(np.int8)
        observed[cid]=float(balanced_accuracy_score(pooled_y,pred)-0.50)

    legal=[
        np.arange(MIN_SHIFT_POSITIONS,n-MIN_SHIFT_POSITIONS+1,dtype=np.int64)
        for n in lengths
    ]
    rng=np.random.default_rng(int(seed))
    maxnull=np.empty(int(replicates),dtype=np.float64)
    shifts=[]

    for r in range(int(replicates)):
        s=tuple(
            int(legal[i][rng.integers(0,len(legal[i]))])
            for i in range(4)
        )
        shifts.append(s)
        shifted_y=np.concatenate([
            np.roll(np.asarray(reference[i]["y"],dtype=np.int8),s[i])
            for i in range(4)
        ])

        row=[]
        for cid in CANDIDATE_IDS:
            pooled_p=np.concatenate([
                np.asarray(candidate_folds[cid][i]["p_long"],dtype=np.float64)
                for i in range(4)
            ])
            pred=(pooled_p>=0.5).astype(np.int8)
            row.append(float(balanced_accuracy_score(shifted_y,pred)-0.50))
        maxnull[r]=max(row)

    q95=float(np.quantile(maxnull,0.95,method="higher"))
    per={}
    for cid in CANDIDATE_IDS:
        obs=observed[cid]
        p=float((1+int(np.sum(maxnull>=obs)))/(int(replicates)+1))
        per[cid]={
            "observed_ba_lift":obs,
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
        "both_classes_every_validation_fold":len(per)==4 and all(
            int(x["long_count"])>0 and int(x["short_count"])>0 for x in per
        ),
        "pooled_balanced_accuracy_gt_055":float(pooled["balanced_accuracy"])>0.55,
        "pooled_roc_auc_gt_060":float(pooled["roc_auc"])>0.60,
        "positive_ba_lift_ge_3_folds":sum(
            float(x["balanced_accuracy_lift_over_050"])>0 for x in per
        )>=3,
        "all_loo_balanced_accuracy_gt_050":len(loo)==4 and all(
            float(x["balanced_accuracy"])>0.50 for x in loo
        ),
        "pooled_log_loss_better_than_prior":float(pooled["log_loss"])<float(pooled["prior_log_loss"]),
        "fwer_p_le_005":float(null_record["max_stat_fwer_empirical_p"])<=0.05,
        "observed_ba_lift_gt_joint_q95":float(null_record["observed_ba_lift"])>float(null_record["joint_max_stat_q95"]),
    }
    return bool(all(gates.values())),gates

def rank(records:Mapping[str,Mapping[str,Any]]):
    complexity={cid:i for i,cid in enumerate(CANDIDATE_IDS)}
    eligible=[cid for cid in CANDIDATE_IDS if records[cid]["eligible"]]
    return sorted(eligible,key=lambda cid:(
        -min(float(x["balanced_accuracy_lift_over_050"]) for x in records[cid]["per_fold"]),
        -float(records[cid]["pooled"]["balanced_accuracy"]),
        -min(float(x["balanced_accuracy"]) for x in records[cid]["leave_one_fold_out"]),
        -float(records[cid]["pooled"]["roc_auc"]),
        float(records[cid]["pooled"]["log_loss"]),
        complexity[cid],
        cid,
    ))

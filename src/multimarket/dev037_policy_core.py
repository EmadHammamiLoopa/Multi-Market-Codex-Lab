from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

POLICY_IDS=("S0","S1","S2","S3","S4","S5")
CHALLENGER_IDS=("S1","S2","S3","S4","S5")

POLICY_NAMES={
    "S0":"TOUCH_ONLY_SELECTIVE",
    "S1":"DIRECTION_CONFIDENCE_SELECTIVE",
    "S2":"PRODUCT_JOINT_SELECTIVE",
    "S3":"BALANCED_MIN_PERCENTILE",
    "S4":"GEOMETRIC_BALANCED_PERCENTILE",
    "S5":"META_CORRECTNESS_FILTER",
}

ACTION_ABSTAIN=0
ACTION_SHORT=1
ACTION_LONG=2

TARGET_COVERAGE_QUANTILE=0.80
NULL_SEED=20260902
NULL_REPLICATES=1999

STATUS_SURVIVOR="DEV037_POLICY_SURVIVOR"
STATUS_REJECTED="DEV037_POLICY_REJECTED"

class Dev037Error(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class PolicyFold:
    fold_id:int
    policy_id:str
    threshold:float
    scores:np.ndarray
    actions:np.ndarray
    y3:np.ndarray
    metrics:dict[str,Any]

def _vec(x,name):
    z=np.asarray(x,dtype=np.float64)
    if z.ndim!=1 or len(z)==0 or not np.all(np.isfinite(z)):
        raise Dev037Error("invalid_vector",name)
    return z

def direction_confidence(p_long):
    p=_vec(p_long,"p_long")
    if np.any((p<0)|(p>1)):
        raise Dev037Error("p_long_range")
    return 2.0*np.abs(p-0.5)

def empirical_percentile_reference(train_values):
    x=np.sort(_vec(train_values,"train_values"))
    return x

def empirical_percentile_map(reference,values):
    ref=np.asarray(reference,dtype=np.float64)
    v=_vec(values,"values")
    if ref.ndim!=1 or len(ref)==0 or not np.all(np.isfinite(ref)):
        raise Dev037Error("invalid_percentile_reference")
    # right-continuous empirical CDF, in (0,1]
    return np.searchsorted(ref,v,side="right").astype(np.float64)/float(len(ref))

def score_bundle(*,p_touch,p_long,touch_reference=None,dir_reference=None):
    pt=_vec(p_touch,"p_touch")
    pl=_vec(p_long,"p_long")
    if len(pt)!=len(pl):
        raise Dev037Error("score_length")
    if np.any((pt<0)|(pt>1)) or np.any((pl<0)|(pl>1)):
        raise Dev037Error("probability_range")
    d=direction_confidence(pl)
    if touch_reference is None:
        touch_reference=empirical_percentile_reference(pt)
    if dir_reference is None:
        dir_reference=empirical_percentile_reference(d)
    rt=empirical_percentile_map(touch_reference,pt)
    rd=empirical_percentile_map(dir_reference,d)
    return {
        "S0":pt,
        "S1":d,
        "S2":pt*d,
        "S3":np.minimum(rt,rd),
        "S4":np.sqrt(rt*rd),
        "r_touch":rt,
        "r_dir":rd,
        "direction_confidence":d,
    }

def meta_features(*,p_touch,p_long,touch_reference,dir_reference):
    b=score_bundle(
        p_touch=p_touch,p_long=p_long,
        touch_reference=touch_reference,dir_reference=dir_reference
    )
    pt=np.asarray(p_touch,dtype=np.float64)
    d=b["direction_confidence"]
    return np.column_stack((
        pt,
        d,
        pt*d,
        b["r_touch"],
        b["r_dir"],
        np.minimum(b["r_touch"],b["r_dir"]),
    ))

def threshold_q80(scores):
    s=_vec(scores,"threshold_scores")
    return float(np.quantile(s,TARGET_COVERAGE_QUANTILE,method="higher"))

def actions_from_score(*,score,threshold,p_long):
    s=_vec(score,"score")
    p=_vec(p_long,"p_long")
    if len(s)!=len(p):
        raise Dev037Error("action_length")
    out=np.full(len(s),ACTION_ABSTAIN,dtype=np.int8)
    active=s>=float(threshold)
    out[active & (p<0.5)]=ACTION_SHORT
    out[active & (p>=0.5)]=ACTION_LONG
    return out

def action_metrics(y3,actions):
    y=np.asarray(y3,dtype=np.int8)
    a=np.asarray(actions,dtype=np.int8)
    if y.ndim!=1 or a.ndim!=1 or len(y)!=len(a) or len(y)==0:
        raise Dev037Error("metric_shape")
    if not np.all(np.isin(y,(0,1,2))) or not np.all(np.isin(a,(0,1,2))):
        raise Dev037Error("metric_labels")

    active=a!=ACTION_ABSTAIN
    n=int(len(y))
    act=int(np.sum(active))
    abstain=n-act
    correct_mask=active & (a==y) & (y!=0)
    correct=int(np.sum(correct_mask))
    false=act-correct
    coverage=float(act/n)
    precision=float(correct/act) if act else 0.0

    long_mask=a==ACTION_LONG
    short_mask=a==ACTION_SHORT
    long_n=int(np.sum(long_mask))
    short_n=int(np.sum(short_mask))
    long_correct=int(np.sum(long_mask & (y==2)))
    short_correct=int(np.sum(short_mask & (y==1)))

    acted_touch=active & (y!=0)
    acted_touch_n=int(np.sum(acted_touch))
    acted_touch_correct=int(np.sum(acted_touch & (a==y)))
    none_actions=int(np.sum(active & (y==0)))

    return {
        "support":n,
        "action_count":act,
        "abstain_count":abstain,
        "coverage":coverage,
        "correct_action_count":correct,
        "false_action_count":false,
        "action_precision":precision,
        "selective_risk":float(1.0-precision) if act else 1.0,
        "correct_actions_per_all_rows":float(correct/n),
        "false_actions_per_all_rows":float(false/n),
        "long_action_count":long_n,
        "short_action_count":short_n,
        "long_short_action_ratio":float(long_n/short_n) if short_n else None,
        "long_action_precision":float(long_correct/long_n) if long_n else None,
        "short_action_precision":float(short_correct/short_n) if short_n else None,
        "acted_touch_count":acted_touch_n,
        "acted_touch_direction_accuracy":(
            float(acted_touch_correct/acted_touch_n) if acted_touch_n else None
        ),
        "none_action_count":none_actions,
        "fraction_actions_on_true_none":float(none_actions/act) if act else None,
    }

def pooled_metrics(folds:Sequence[PolicyFold]):
    if not folds:
        raise Dev037Error("empty_folds")
    y=np.concatenate([f.y3 for f in folds])
    a=np.concatenate([f.actions for f in folds])
    return action_metrics(y,a)

def compare_to_s0(s0_folds:Sequence[PolicyFold],cand_folds:Sequence[PolicyFold]):
    if len(s0_folds)!=4 or len(cand_folds)!=4:
        raise Dev037Error("comparison_fold_count")
    fold_delta=[]
    for b,c in zip(s0_folds,cand_folds,strict=True):
        if b.fold_id!=c.fold_id or not np.array_equal(b.y3,c.y3):
            raise Dev037Error("comparison_alignment")
        fold_delta.append(float(c.metrics["action_precision"]-b.metrics["action_precision"]))
    bpool=pooled_metrics(s0_folds)
    cpool=pooled_metrics(cand_folds)
    loo=[]
    for omitted in range(4):
        b=pooled_metrics([f for i,f in enumerate(s0_folds) if i!=omitted])
        c=pooled_metrics([f for i,f in enumerate(cand_folds) if i!=omitted])
        loo.append(float(c["action_precision"]-b["action_precision"]))
    return {
        "pooled_delta_action_precision":float(cpool["action_precision"]-bpool["action_precision"]),
        "fold_delta_action_precision":[float(v) for v in fold_delta],
        "positive_fold_deltas":int(sum(v>0 for v in fold_delta)),
        "leave_one_fold_out_delta_action_precision":[float(v) for v in loo],
        "all_loo_delta_positive":bool(all(v>0 for v in loo)),
        "minimum_fold_delta_action_precision":float(min(fold_delta)),
        "median_fold_delta_action_precision":float(np.median(fold_delta)),
        "base_pooled_metrics":bpool,
        "candidate_pooled_metrics":cpool,
    }

def operational_guards(folds:Sequence[PolicyFold]):
    if len(folds)!=4:
        raise Dev037Error("guard_fold_count")
    pool=pooled_metrics(folds)
    fold_cov=[float(f.metrics["coverage"]) for f in folds]
    both_actions=all(
        f.metrics["long_action_count"]>0 and f.metrics["short_action_count"]>0
        for f in folds
    )
    return {
        "pooled_coverage_ge_010":pool["coverage"]>=0.10,
        "pooled_coverage_le_030":pool["coverage"]<=0.30,
        "every_fold_coverage_ge_005":all(v>=0.05 for v in fold_cov),
        "every_fold_coverage_le_040":all(v<=0.40 for v in fold_cov),
        "long_and_short_every_fold":bool(both_actions),
    }

def joint_temporal_max_stat_null(
    policy_folds:Mapping[str,Sequence[PolicyFold]],
    *,
    seed:int=NULL_SEED,
    replicates:int=NULL_REPLICATES,
):
    if tuple(policy_folds)!=POLICY_IDS:
        raise Dev037Error("null_policy_order")
    for pid in POLICY_IDS:
        if len(policy_folds[pid])!=4:
            raise Dev037Error("null_fold_count",pid)

    rng=np.random.default_rng(seed)
    legal=[]
    for f in policy_folds["S0"]:
        n=len(f.y3)
        vals=np.arange(30,n-29,dtype=np.int64)
        if len(vals)==0:
            raise Dev037Error("null_legal_shift_empty",str(f.fold_id))
        legal.append(vals)

    obs={
        pid:compare_to_s0(policy_folds["S0"],policy_folds[pid])["pooled_delta_action_precision"]
        for pid in CHALLENGER_IDS
    }
    null={pid:np.empty(replicates,dtype=np.float64) for pid in CHALLENGER_IDS}
    maxnull=np.empty(replicates,dtype=np.float64)
    shifts=[]

    fixed_actions={
        pid:[np.asarray(f.actions,dtype=np.int8) for f in policy_folds[pid]]
        for pid in POLICY_IDS
    }
    base_labels=[np.asarray(f.y3,dtype=np.int8) for f in policy_folds["S0"]]

    for r in range(replicates):
        sh=[int(legal[i][rng.integers(0,len(legal[i]))]) for i in range(4)]
        shifts.append(sh)
        shifted=[np.roll(base_labels[i],sh[i]) for i in range(4)]
        b_y=np.concatenate(shifted)
        b_a=np.concatenate(fixed_actions["S0"])
        bprec=action_metrics(b_y,b_a)["action_precision"]
        row=[]
        for pid in CHALLENGER_IDS:
            a=np.concatenate(fixed_actions[pid])
            prec=action_metrics(b_y,a)["action_precision"]
            d=float(prec-bprec)
            null[pid][r]=d
            row.append(d)
        maxnull[r]=max(row)

    q95=float(np.quantile(maxnull,0.95,method="higher"))
    per={}
    for pid in CHALLENGER_IDS:
        observed=obs[pid]
        per[pid]={
            "observed_delta_action_precision":float(observed),
            "raw_empirical_p":float((1+int(np.sum(null[pid]>=observed)))/(replicates+1)),
            "max_stat_fwer_empirical_p":float((1+int(np.sum(maxnull>=observed)))/(replicates+1)),
            "max_stat_q95":q95,
            "observed_minus_q95":float(observed-q95),
        }
    return {
        "seed":int(seed),
        "replicates":int(replicates),
        "policy_ids":list(POLICY_IDS),
        "challenger_ids":list(CHALLENGER_IDS),
        "shift_tuples":shifts,
        "candidate_null_vectors":{pid:null[pid].tolist() for pid in CHALLENGER_IDS},
        "max_stat_null":maxnull.tolist(),
        "max_stat_q95":q95,
        "per_candidate":per,
    }

def is_survivor(*,comparison,guards,nullrec):
    return bool(
        comparison["pooled_delta_action_precision"]>=0.02
        and comparison["positive_fold_deltas"]>=3
        and comparison["all_loo_delta_positive"]
        and all(guards.values())
        and comparison["pooled_delta_action_precision"]>float(nullrec["max_stat_q95"])
        and float(nullrec["max_stat_fwer_empirical_p"])<=0.05
    )

def survivor_ranking(records:Mapping[str,dict[str,Any]]):
    complexity={"S1":1,"S2":2,"S3":3,"S4":4,"S5":5}
    survivors=[pid for pid in CHALLENGER_IDS if records[pid]["survivor"]]
    return sorted(
        survivors,
        key=lambda pid:(
            float(records[pid]["null"]["max_stat_fwer_empirical_p"]),
            -float(records[pid]["comparison"]["minimum_fold_delta_action_precision"]),
            -float(records[pid]["comparison"]["median_fold_delta_action_precision"]),
            -float(records[pid]["comparison"]["pooled_delta_action_precision"]),
            float(records[pid]["comparison"]["candidate_pooled_metrics"]["false_actions_per_all_rows"]),
            complexity[pid],
            pid,
        )
    )

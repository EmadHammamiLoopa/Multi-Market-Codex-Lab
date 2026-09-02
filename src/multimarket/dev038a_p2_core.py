from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

CONTROLLER_IDS=("C0","C1","C2")
CHALLENGER_IDS=("C1","C2")
WINDOW_BY_ID={"C0":120,"C1":360,"C2":720}
NULL_SEED=20260903
NULL_REPLICATES=1999

class P2Error(RuntimeError):
    pass

def _pool(fs:Sequence[dict]):
    support=sum(int(f["metrics"]["support"]) for f in fs)
    actions=sum(int(f["metrics"]["action_count"]) for f in fs)
    correct=sum(int(f["metrics"]["correct_action_count"]) for f in fs)
    false=sum(int(f["metrics"]["false_action_count"]) for f in fs)
    none_actions=sum(int(f["metrics"]["none_action_count"]) for f in fs)
    return {
        "support":support,
        "action_count":actions,
        "correct_action_count":correct,
        "false_action_count":false,
        "none_action_count":none_actions,
        "action_precision":float(correct/actions) if actions else 0.0,
        "correct_actions_per_all_rows":float(correct/support),
        "false_actions_per_all_rows":float(false/support),
        "fraction_actions_on_true_none":float(none_actions/actions) if actions else None,
    }

def compare(base_folds:Sequence[dict],cand_folds:Sequence[dict]):
    if len(base_folds)!=4 or len(cand_folds)!=4:
        raise P2Error("fold_count")
    fold_delta=[]
    for b,c in zip(base_folds,cand_folds,strict=True):
        if b["fold_id"]!=c["fold_id"]:
            raise P2Error("fold_alignment")
        if not np.array_equal(np.asarray(b["y3"]),np.asarray(c["y3"])):
            raise P2Error("label_alignment")
        fold_delta.append(float(c["metrics"]["action_precision"]-b["metrics"]["action_precision"]))

    bpool=_pool(base_folds)
    cpool=_pool(cand_folds)

    loo=[]
    for omit in range(4):
        b=_pool([f for i,f in enumerate(base_folds) if i!=omit])
        c=_pool([f for i,f in enumerate(cand_folds) if i!=omit])
        loo.append(float(c["action_precision"]-b["action_precision"]))

    return {
        "pooled_delta_action_precision":float(cpool["action_precision"]-bpool["action_precision"]),
        "pooled_delta_correct_action_rate":float(
            cpool["correct_actions_per_all_rows"]-bpool["correct_actions_per_all_rows"]
        ),
        "pooled_delta_false_action_rate":float(
            cpool["false_actions_per_all_rows"]-bpool["false_actions_per_all_rows"]
        ),
        "pooled_delta_action_on_none_fraction":float(
            cpool["fraction_actions_on_true_none"]-bpool["fraction_actions_on_true_none"]
        ),
        "fold_delta_action_precision":[float(x) for x in fold_delta],
        "positive_fold_deltas":int(sum(x>0 for x in fold_delta)),
        "minimum_fold_delta_action_precision":float(min(fold_delta)),
        "median_fold_delta_action_precision":float(np.median(fold_delta)),
        "leave_one_fold_out_delta_action_precision":[float(x) for x in loo],
        "all_loo_delta_positive":bool(all(x>0 for x in loo)),
        "base_pooled_metrics":bpool,
        "candidate_pooled_metrics":cpool,
    }

def operational_guards(folds:Sequence[dict]):
    if len(folds)!=4:
        raise P2Error("guard_fold_count")
    pool=_pool(folds)
    fold_cov=[float(f["metrics"]["coverage"]) for f in folds]
    both_actions=all(
        int(f["metrics"]["long_action_count"])>0
        and int(f["metrics"]["short_action_count"])>0
        for f in folds
    )
    return {
        "pooled_coverage_ge_010":float(sum(f["metrics"]["action_count"] for f in folds)/sum(f["metrics"]["support"] for f in folds))>=0.10,
        "pooled_coverage_le_030":float(sum(f["metrics"]["action_count"] for f in folds)/sum(f["metrics"]["support"] for f in folds))<=0.30,
        "every_fold_coverage_ge_005":all(v>=0.05 for v in fold_cov),
        "every_fold_coverage_le_040":all(v<=0.40 for v in fold_cov),
        "long_and_short_every_fold":bool(both_actions),
    }

def joint_max_stat_null(controller_folds:Mapping[str,Sequence[dict]],*,seed=NULL_SEED,replicates=NULL_REPLICATES):
    if tuple(controller_folds)!=CONTROLLER_IDS:
        raise P2Error("controller_order")

    for cid in CONTROLLER_IDS:
        if len(controller_folds[cid])!=4:
            raise P2Error("null_fold_count")

    rng=np.random.default_rng(seed)
    base_labels=[np.asarray(f["y3"],dtype=np.int8) for f in controller_folds["C0"]]
    actions={
        cid:[np.asarray(f["actions"],dtype=np.int8) for f in controller_folds[cid]]
        for cid in CONTROLLER_IDS
    }

    legal=[]
    for y in base_labels:
        vals=np.arange(30,len(y)-29,dtype=np.int64)
        if len(vals)==0:
            raise P2Error("null_legal_shift_empty")
        legal.append(vals)

    def precision(y,a):
        active=a!=0
        act=int(np.sum(active))
        correct=int(np.sum(active & (a==y) & (y!=0)))
        return float(correct/act) if act else 0.0

    observed={
        cid:compare(controller_folds["C0"],controller_folds[cid])["pooled_delta_action_precision"]
        for cid in CHALLENGER_IDS
    }

    null={cid:np.empty(replicates,dtype=np.float64) for cid in CHALLENGER_IDS}
    maxnull=np.empty(replicates,dtype=np.float64)
    shifts=[]

    for r in range(replicates):
        sh=[int(legal[i][rng.integers(0,len(legal[i]))]) for i in range(4)]
        shifts.append(sh)
        shifted=[np.roll(base_labels[i],sh[i]) for i in range(4)]
        y=np.concatenate(shifted)
        bprec=precision(y,np.concatenate(actions["C0"]))
        row=[]
        for cid in CHALLENGER_IDS:
            d=float(precision(y,np.concatenate(actions[cid]))-bprec)
            null[cid][r]=d
            row.append(d)
        maxnull[r]=max(row)

    q95=float(np.quantile(maxnull,0.95,method="higher"))
    per={}
    for cid in CHALLENGER_IDS:
        obs=float(observed[cid])
        per[cid]={
            "observed_delta_action_precision":obs,
            "max_stat_q95":q95,
            "observed_minus_q95":float(obs-q95),
            "raw_empirical_p":float((1+int(np.sum(null[cid]>=obs)))/(replicates+1)),
            "max_stat_fwer_empirical_p":float((1+int(np.sum(maxnull>=obs)))/(replicates+1)),
        }

    return {
        "seed":int(seed),
        "replicates":int(replicates),
        "controller_ids":list(CONTROLLER_IDS),
        "challenger_ids":list(CHALLENGER_IDS),
        "shift_tuples":shifts,
        "candidate_null_vectors":{k:v.tolist() for k,v in null.items()},
        "max_stat_null":maxnull.tolist(),
        "max_stat_q95":q95,
        "per_candidate":per,
    }

def is_survivor(comp:dict[str,Any],guards:dict[str,bool],nullrec:dict[str,Any]):
    return bool(
        comp["pooled_delta_action_precision"]>=0.02
        and comp["pooled_delta_correct_action_rate"]>=0.0
        and comp["pooled_delta_false_action_rate"]<0.0
        and comp["pooled_delta_action_on_none_fraction"]<0.0
        and comp["positive_fold_deltas"]>=3
        and comp["all_loo_delta_positive"]
        and all(bool(v) for v in guards.values())
        and comp["pooled_delta_action_precision"]>float(nullrec["max_stat_q95"])
        and float(nullrec["max_stat_fwer_empirical_p"])<=0.05
    )

def rank(records:Mapping[str,dict[str,Any]]):
    survivors=[cid for cid in CHALLENGER_IDS if records[cid]["survivor"]]
    return sorted(
        survivors,
        key=lambda cid:(
            float(records[cid]["null"]["max_stat_fwer_empirical_p"]),
            -float(records[cid]["comparison"]["minimum_fold_delta_action_precision"]),
            -float(records[cid]["comparison"]["median_fold_delta_action_precision"]),
            -float(records[cid]["comparison"]["pooled_delta_action_precision"]),
            -float(records[cid]["comparison"]["pooled_delta_correct_action_rate"]),
            float(records[cid]["comparison"]["candidate_pooled_metrics"]["fraction_actions_on_true_none"]),
            WINDOW_BY_ID[cid],
            cid,
        ),
    )

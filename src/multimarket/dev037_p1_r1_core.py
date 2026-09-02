from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

POLICY_IDS=("S0","S1","S2","S5")
CHALLENGER_IDS=("S1","S2","S5")
NULL_SEED=20260902
NULL_REPLICATES=1999

class P1R1Error(RuntimeError):
    pass

def compare(base_folds:Sequence[dict],cand_folds:Sequence[dict]):
    if len(base_folds)!=4 or len(cand_folds)!=4:
        raise P1R1Error("fold_count")
    fold_delta=[]
    for b,c in zip(base_folds,cand_folds,strict=True):
        if b["fold_id"]!=c["fold_id"]:
            raise P1R1Error("fold_alignment")
        fold_delta.append(float(c["metrics"]["action_precision"]-b["metrics"]["action_precision"]))

    def pool(fs):
        support=sum(int(f["metrics"]["support"]) for f in fs)
        actions=sum(int(f["metrics"]["action_count"]) for f in fs)
        correct=sum(int(f["metrics"]["correct_action_count"]) for f in fs)
        false=sum(int(f["metrics"]["false_action_count"]) for f in fs)
        return {
            "support":support,
            "action_count":actions,
            "correct_action_count":correct,
            "false_action_count":false,
            "action_precision":float(correct/actions) if actions else 0.0,
            "correct_actions_per_all_rows":float(correct/support),
            "false_actions_per_all_rows":float(false/support),
        }

    bpool=pool(base_folds)
    cpool=pool(cand_folds)
    loo=[]
    for omit in range(4):
        b=pool([f for i,f in enumerate(base_folds) if i!=omit])
        c=pool([f for i,f in enumerate(cand_folds) if i!=omit])
        loo.append(float(c["action_precision"]-b["action_precision"]))

    return {
        "pooled_delta_action_precision":float(cpool["action_precision"]-bpool["action_precision"]),
        "pooled_delta_correct_action_rate":float(
            cpool["correct_actions_per_all_rows"]-bpool["correct_actions_per_all_rows"]
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

def joint_max_stat_null(policy_folds:Mapping[str,Sequence[dict]],*,seed=NULL_SEED,replicates=NULL_REPLICATES):
    if tuple(policy_folds)!=POLICY_IDS:
        raise P1R1Error("policy_order")
    rng=np.random.default_rng(seed)

    # labels shared by all policies per fold; actions fixed
    base_labels=[np.asarray(f["y3"],dtype=np.int8) for f in policy_folds["S0"]]
    actions={pid:[np.asarray(f["actions"],dtype=np.int8) for f in policy_folds[pid]] for pid in POLICY_IDS}
    legal=[np.arange(30,len(y)-29,dtype=np.int64) for y in base_labels]

    def precision(y,a):
        active=a!=0
        act=int(np.sum(active))
        correct=int(np.sum(active & (a==y) & (y!=0)))
        return float(correct/act) if act else 0.0

    observed={pid:compare(policy_folds["S0"],policy_folds[pid])["pooled_delta_action_precision"]
              for pid in CHALLENGER_IDS}

    null={pid:np.empty(replicates,dtype=np.float64) for pid in CHALLENGER_IDS}
    maxnull=np.empty(replicates,dtype=np.float64)
    shifts=[]

    for r in range(replicates):
        sh=[int(legal[i][rng.integers(0,len(legal[i]))]) for i in range(4)]
        shifts.append(sh)
        shifted=[np.roll(base_labels[i],sh[i]) for i in range(4)]
        y=np.concatenate(shifted)
        bprec=precision(y,np.concatenate(actions["S0"]))
        row=[]
        for pid in CHALLENGER_IDS:
            d=float(precision(y,np.concatenate(actions[pid]))-bprec)
            null[pid][r]=d
            row.append(d)
        maxnull[r]=max(row)

    q95=float(np.quantile(maxnull,0.95,method="higher"))
    per={}
    for pid in CHALLENGER_IDS:
        obs=float(observed[pid])
        per[pid]={
            "observed_delta_action_precision":obs,
            "max_stat_q95":q95,
            "observed_minus_q95":float(obs-q95),
            "raw_empirical_p":float((1+int(np.sum(null[pid]>=obs)))/(replicates+1)),
            "max_stat_fwer_empirical_p":float((1+int(np.sum(maxnull>=obs)))/(replicates+1)),
        }
    return {
        "seed":int(seed),
        "replicates":int(replicates),
        "shift_tuples":shifts,
        "max_stat_null":maxnull.tolist(),
        "candidate_null_vectors":{k:v.tolist() for k,v in null.items()},
        "max_stat_q95":q95,
        "per_candidate":per,
    }

def is_survivor(comp:dict[str,Any],nullrec:dict[str,Any]):
    return bool(
        comp["pooled_delta_action_precision"]>=0.02
        and comp["pooled_delta_correct_action_rate"]>0
        and comp["positive_fold_deltas"]>=3
        and comp["all_loo_delta_positive"]
        and comp["pooled_delta_action_precision"]>float(nullrec["max_stat_q95"])
        and float(nullrec["max_stat_fwer_empirical_p"])<=0.05
    )

def rank(records:Mapping[str,dict[str,Any]]):
    complexity={"S1":1,"S2":2,"S5":3}
    survivors=[pid for pid in CHALLENGER_IDS if records[pid]["survivor"]]
    return sorted(
        survivors,
        key=lambda pid:(
            float(records[pid]["null"]["max_stat_fwer_empirical_p"]),
            -float(records[pid]["comparison"]["minimum_fold_delta_action_precision"]),
            -float(records[pid]["comparison"]["median_fold_delta_action_precision"]),
            -float(records[pid]["comparison"]["pooled_delta_action_precision"]),
            -float(records[pid]["comparison"]["pooled_delta_correct_action_rate"]),
            float(records[pid]["comparison"]["candidate_pooled_metrics"]["false_actions_per_all_rows"]),
            complexity[pid],
            pid,
        ),
    )

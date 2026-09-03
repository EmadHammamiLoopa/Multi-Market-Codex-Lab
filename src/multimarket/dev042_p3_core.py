from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from . import dev030_first_passage as fp

CANDIDATE_IDS=(
    "C0_PRICE_LOGIT",
    "C1_OFI_LOGIT",
    "C2_PRESSURE_CAPACITY_LOGIT",
    "C3_COMBINED_LOGIT",
    "C4_COMBINED_HGB",
)
CLASS_NONE=0
CLASS_LONG=1
CLASS_SHORT=2
CLASS_ORDER=(CLASS_NONE,CLASS_LONG,CLASS_SHORT)
C1_COST_BPS=10.0
C2_COST_BPS=16.0
NULL_REPLICATES=1999
NULL_SEED=20260903
MIN_SHIFT_POSITIONS=60

class P3Error(RuntimeError):
    pass

@dataclass(frozen=True)
class ExecutedTrade:
    day:str
    side:str
    decision_timestamp_us:int
    entry_timestamp_us:int
    exit_timestamp_us:int
    exit_reason:str
    gross_bps:float

def label_code(record:Mapping[str,Any])->int|None:
    if record.get("target_valid") is not True:
        return None
    if record.get("same_row_ambiguous") is not False:
        return None
    lab=record.get("label")
    if lab==fp.NONE:return CLASS_NONE
    if lab==fp.LONG_FIRST:return CLASS_LONG
    if lab==fp.SHORT_FIRST:return CLASS_SHORT
    raise P3Error("unknown_target_label")

def make_estimator(candidate_id:str):
    if candidate_id in CANDIDATE_IDS[:4]:
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
    if candidate_id=="C4_COMBINED_HGB":
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
    raise P3Error(f"unknown_candidate:{candidate_id}")

def action_from_probabilities(probabilities,classes)->np.ndarray:
    p=np.asarray(probabilities,dtype=np.float64)
    cls=np.asarray(classes,dtype=np.int64)
    if p.ndim!=2 or len(cls)!=p.shape[1] or set(cls.tolist())!=set(CLASS_ORDER):
        raise P3Error("probability_schema")
    if np.any(~np.isfinite(p)) or np.any(p<0) or np.any(p>1):
        raise P3Error("probability_values")
    pos={int(c):i for i,c in enumerate(cls.tolist())}
    ordered=p[:,[pos[CLASS_NONE],pos[CLASS_LONG],pos[CLASS_SHORT]]]
    out=np.zeros(len(p),dtype=np.int8)
    for i,row in enumerate(ordered):
        m=float(np.max(row))
        winners=np.flatnonzero(row==m)
        if len(winners)!=1:
            out[i]=CLASS_NONE
        else:
            out[i]=np.int8((CLASS_NONE,CLASS_LONG,CLASS_SHORT)[int(winners[0])])
    return out

def classification_metrics(y_true,probabilities,actions):
    y=np.asarray(y_true,dtype=np.int8)
    p=np.asarray(probabilities,dtype=np.float64)
    a=np.asarray(actions,dtype=np.int8)
    if len(y)==0 or p.shape!=(len(y),3) or a.shape!=(len(y),):
        raise P3Error("classification_shape")
    pred=np.argmax(p,axis=1).astype(np.int8)
    pr,rc,f1,_=precision_recall_fscore_support(
        y,pred,labels=list(CLASS_ORDER),zero_division=0
    )
    ap={}
    for c,name in zip(CLASS_ORDER,("NONE","LONG_FIRST","SHORT_FIRST"),strict=True):
        truth=(y==c).astype(np.int8)
        ap[name]=float(average_precision_score(truth,p[:,c]))
    return {
        "support":int(len(y)),
        "confusion_matrix":confusion_matrix(y,pred,labels=list(CLASS_ORDER)).tolist(),
        "macro_f1":float(f1_score(y,pred,labels=list(CLASS_ORDER),average="macro",zero_division=0)),
        "balanced_accuracy":float(balanced_accuracy_score(y,pred)),
        "log_loss":float(log_loss(y,p,labels=list(CLASS_ORDER))),
        "per_class":{
            name:{"precision":float(pr[i]),"recall":float(rc[i]),"f1":float(f1[i]),"average_precision":ap[name]}
            for i,name in enumerate(("NONE","LONG_FIRST","SHORT_FIRST"))
        },
        "macro_ovr_average_precision":float(np.mean(list(ap.values()))),
        "action_coverage":float(np.mean(a!=CLASS_NONE)),
        "long_actions":int(np.sum(a==CLASS_LONG)),
        "short_actions":int(np.sum(a==CLASS_SHORT)),
        "abstain_actions":int(np.sum(a==CLASS_NONE)),
    }

def _exact_pos(ts:np.ndarray,target:int)->int:
    i=int(np.searchsorted(ts,int(target),side="left"))
    if i>=len(ts) or int(ts[i])!=int(target):
        raise P3Error(f"execution_timestamp_missing:{target}")
    return i

def execute_actions(
    *,
    day:str,
    actions,
    records:Sequence[Mapping[str,Any]],
    raw_timestamps_us,
    bid,
    ask,
    book_valid,
):
    a=np.asarray(actions,dtype=np.int8)
    if len(a)!=len(records):
        raise P3Error("action_record_length")
    ts=np.asarray(raw_timestamps_us,dtype=np.int64)
    b=np.asarray(bid,dtype=np.float64)
    s=np.asarray(ask,dtype=np.float64)
    valid=np.asarray(book_valid,dtype=bool)
    if not (len(ts)==len(b)==len(s)==len(valid)) or np.any(np.diff(ts)<=0):
        raise P3Error("raw_execution_schema")

    candidates=[]
    for action,r in zip(a.tolist(),records,strict=True):
        if action==CLASS_NONE:
            continue
        if action not in (CLASS_LONG,CLASS_SHORT):
            raise P3Error("unknown_action")
        if label_code(r) is None:
            raise P3Error("action_on_invalid_target_support")

        entry=int(r["entry_timestamp_us"])
        lab=r["label"]
        if lab==fp.NONE:
            event="FORCED_HORIZON"
            exit_ts=entry+1_800_000_000+250_000
        else:
            same_direction=(
                (action==CLASS_LONG and lab==fp.LONG_FIRST)
                or (action==CLASS_SHORT and lab==fp.SHORT_FIRST)
            )
            event="TP" if same_direction else "SL"
            exit_ts=int(r["barrier_reached_timestamp_us"])+250_000

        ei=_exact_pos(ts,entry)
        xi=_exact_pos(ts,exit_ts)
        if not (valid[ei] and valid[xi]):
            raise P3Error("execution_invalid_book")
        vals=(float(b[ei]),float(s[ei]),float(b[xi]),float(s[xi]))
        if any((not np.isfinite(v) or v<=0) for v in vals):
            raise P3Error("execution_invalid_quote")
        if b[ei]>s[ei] or b[xi]>s[xi]:
            raise P3Error("execution_crossed_book")

        if action==CLASS_LONG:
            gross=float(10000*np.log(float(b[xi])/float(s[ei])))
            side="LONG"
        else:
            gross=float(10000*np.log(float(b[ei])/float(s[xi])))
            side="SHORT"

        candidates.append(ExecutedTrade(
            day=day,
            side=side,
            decision_timestamp_us=int(r["decision_timestamp_us"]),
            entry_timestamp_us=entry,
            exit_timestamp_us=exit_ts,
            exit_reason=event,
            gross_bps=gross,
        ))

    ordered=sorted(candidates,key=lambda t:(t.decision_timestamp_us,t.exit_timestamp_us,t.side))
    accepted=[]
    ignored=0
    flat_after=-1
    for t in ordered:
        if t.decision_timestamp_us<flat_after:
            ignored+=1
            continue
        accepted.append(t)
        flat_after=t.exit_timestamp_us
    return tuple(accepted),int(ignored)

def _pf(v):
    v=np.asarray(v,dtype=np.float64)
    pos=float(np.sum(v[v>0]));neg=float(np.sum(v[v<0]))
    if neg==0:return float("inf") if pos>0 else 0.0
    return float(pos/abs(neg))

def _max_dd(v):
    v=np.asarray(v,dtype=np.float64)
    eq=np.concatenate(([0.0],np.cumsum(v)))
    peak=np.maximum.accumulate(eq)
    return float(np.max(peak-eq))

def _max_losing_streak(v):
    best=cur=0
    for x in np.asarray(v,dtype=np.float64).tolist():
        if x<0:cur+=1;best=max(best,cur)
        else:cur=0
    return int(best)

def economics(trades:Sequence[ExecutedTrade],cost_bps:float,fold_order:Sequence[str]):
    if not trades:
        return {
            "trade_count":0,"mean_net_bps":None,"total_net_bps":0.0,"net_pf":0.0,
            "net_win_rate":None,"max_drawdown_bps":0.0,"max_losing_streak":0,
            "per_fold":[],"positive_folds":0,"minimum_fold_mean_net_bps":None,
            "median_fold_mean_net_bps":None,"leave_one_fold_out":[],
            "minimum_loo_mean_net_bps":None,"max_positive_fold_contribution_fraction":None,
        }
    gross=np.asarray([t.gross_bps for t in trades],dtype=np.float64)
    net=gross-float(cost_bps)
    per=[]
    positive=[]
    for d in fold_order:
        vals=np.asarray([net[i] for i,t in enumerate(trades) if t.day==d],dtype=np.float64)
        mean=float(np.mean(vals)) if len(vals) else None
        total=float(np.sum(vals)) if len(vals) else 0.0
        per.append({"fold":d,"trades":int(len(vals)),"mean_net_bps":mean,"total_net_bps":total})
        positive.append(max(0.0,total))
    loo=[]
    for omit in fold_order:
        vals=np.asarray([net[i] for i,t in enumerate(trades) if t.day!=omit],dtype=np.float64)
        loo.append({"omitted_fold":omit,"mean_net_bps":float(np.mean(vals)) if len(vals) else None})
    pos_total=float(sum(positive))
    conc=float(max(positive)/pos_total) if pos_total>0 else None
    fold_means=[x["mean_net_bps"] for x in per if x["mean_net_bps"] is not None]
    return {
        "trade_count":int(len(trades)),
        "mean_gross_bps":float(np.mean(gross)),
        "median_gross_bps":float(np.median(gross)),
        "total_gross_bps":float(np.sum(gross)),
        "cost_bps":float(cost_bps),
        "mean_net_bps":float(np.mean(net)),
        "median_net_bps":float(np.median(net)),
        "total_net_bps":float(np.sum(net)),
        "net_pf":_pf(net),
        "net_win_rate":float(np.mean(net>0)),
        "max_drawdown_bps":_max_dd(net),
        "max_losing_streak":_max_losing_streak(net),
        "per_fold":per,
        "positive_folds":int(sum(x["total_net_bps"]>0 for x in per)),
        "minimum_fold_mean_net_bps":float(min(fold_means)) if fold_means else None,
        "median_fold_mean_net_bps":float(np.median(fold_means)) if fold_means else None,
        "leave_one_fold_out":loo,
        "minimum_loo_mean_net_bps":float(min(x["mean_net_bps"] for x in loo if x["mean_net_bps"] is not None)),
        "max_positive_fold_contribution_fraction":conc,
    }

def absolute_eligibility(record:Mapping[str,Any]):
    c1=record["c1"];c2=record["c2"];activity=record["activity"]
    per=c2.get("per_fold",[]);loo=c2.get("leave_one_fold_out",[])
    coverage=float(record["classification"]["action_coverage"])
    gates={
        "four_outer_folds_completed":len(per)==4,
        "zero_execution_invalid":int(activity.get("execution_invalid",0))==0,
        "accepted_trades_ge_100":int(activity["accepted_trades"])>=100,
        "trades_every_fold":len(per)==4 and all(int(x["trades"])>0 for x in per),
        "long_trades_positive":int(activity["long_trades"])>0,
        "short_trades_positive":int(activity["short_trades"])>0,
        "c2_mean_net_gt_0":c2.get("mean_net_bps") is not None and float(c2["mean_net_bps"])>0,
        "c2_total_net_gt_0":float(c2.get("total_net_bps",0.0))>0,
        "c2_pf_gt_105":float(c2.get("net_pf",0.0))>1.05,
        "c2_positive_folds_ge_3":int(c2.get("positive_folds",0))>=3,
        "c2_min_fold_mean_gt_minus_2":c2.get("minimum_fold_mean_net_bps") is not None and float(c2["minimum_fold_mean_net_bps"])>-2.0,
        "c2_all_loo_positive":len(loo)==4 and all(x.get("mean_net_bps") is not None and float(x["mean_net_bps"])>0 for x in loo),
        "c1_mean_net_gt_0":c1.get("mean_net_bps") is not None and float(c1["mean_net_bps"])>0,
        "c1_total_net_gt_0":float(c1.get("total_net_bps",0.0))>0,
        "c2_concentration_le_060":c2.get("max_positive_fold_contribution_fraction") is not None and float(c2["max_positive_fold_contribution_fraction"])<=0.60,
        "coverage_in_005_080":coverage>=0.05 and coverage<=0.80,
    }
    return bool(all(gates.values())),gates

def rank(records:Mapping[str,Mapping[str,Any]]):
    complexity={cid:i for i,cid in enumerate(CANDIDATE_IDS)}
    eligible=[cid for cid in CANDIDATE_IDS if records[cid]["eligible"]]
    return sorted(eligible,key=lambda cid:(
        -float(records[cid]["c2"]["minimum_fold_mean_net_bps"]),
        -float(records[cid]["c2"]["median_fold_mean_net_bps"]),
        -float(records[cid]["c2"]["mean_net_bps"]),
        -float(records[cid]["c2"]["minimum_loo_mean_net_bps"]),
        -float(records[cid]["c2"]["net_pf"]),
        -float(records[cid]["c2"]["total_net_bps"]),
        complexity[cid],
        cid,
    ))


def joint_temporal_max_stat_null(
    *,
    observed_records:Mapping[str,Mapping[str,Any]],
    fold_actions:Mapping[str,Sequence[np.ndarray]],
    fold_evaluators:Sequence[Any],
    seed:int=NULL_SEED,
    replicates:int=NULL_REPLICATES,
):
    if tuple(fold_actions)!=CANDIDATE_IDS:
        raise P3Error("null_candidate_order")
    if len(fold_evaluators)!=4:
        raise P3Error("null_fold_count")
    for cid in CANDIDATE_IDS:
        if len(fold_actions[cid])!=4:
            raise P3Error("null_candidate_fold_count")

    fold_lengths=[len(np.asarray(fold_actions[CANDIDATE_IDS[0]][i])) for i in range(4)]
    for i,n in enumerate(fold_lengths):
        if n<=2*MIN_SHIFT_POSITIONS:
            raise P3Error(f"null_fold_too_short:{i}:{n}")
        for cid in CANDIDATE_IDS:
            if len(np.asarray(fold_actions[cid][i]))!=n:
                raise P3Error("null_fold_alignment")

    observed={}
    for cid in CANDIDATE_IDS:
        val=observed_records[cid]["c2"].get("mean_net_bps")
        if val is None:
            observed[cid]=float("-inf")
        else:
            observed[cid]=float(val)

    legal=[
        np.arange(MIN_SHIFT_POSITIONS,n-MIN_SHIFT_POSITIONS+1,dtype=np.int64)
        for n in fold_lengths
    ]
    rng=np.random.default_rng(int(seed))
    maxnull=np.empty(int(replicates),dtype=np.float64)
    per_candidate={cid:np.empty(int(replicates),dtype=np.float64) for cid in CANDIDATE_IDS}
    shift_tuples=[]

    for r in range(int(replicates)):
        shifts=tuple(
            int(legal[i][rng.integers(0,len(legal[i]))])
            for i in range(4)
        )
        shift_tuples.append(shifts)
        row=[]
        for cid in CANDIDATE_IDS:
            trades=[]
            for i in range(4):
                shifted=np.roll(np.asarray(fold_actions[cid][i],dtype=np.int8),shifts[i])
                fold_trades=fold_evaluators[i](shifted)
                trades.extend(fold_trades)
            econ=economics(tuple(trades),C2_COST_BPS,[f"FOLD{i+1}" for i in range(4)])
            m=econ.get("mean_net_bps")
            stat=float(m) if m is not None else float("-inf")
            per_candidate[cid][r]=stat
            row.append(stat)
        maxnull[r]=max(row)

    q95=float(np.quantile(maxnull,0.95,method="higher"))
    per={}
    for cid in CANDIDATE_IDS:
        obs=observed[cid]
        p=float((1+int(np.sum(maxnull>=obs)))/(int(replicates)+1))
        per[cid]={
            "observed_mean_c2_net_bps":obs,
            "joint_max_stat_q95":q95,
            "observed_minus_q95":float(obs-q95),
            "max_stat_fwer_empirical_p":p,
            "passes_joint_null":bool(obs>q95 and p<=0.05),
        }

    return {
        "seed":int(seed),
        "replicates":int(replicates),
        "minimum_shift_positions":int(MIN_SHIFT_POSITIONS),
        "shift_tuples":[list(x) for x in shift_tuples],
        "max_stat_null":maxnull.tolist(),
        "joint_max_stat_q95":q95,
        "per_candidate":per,
    }

def final_eligibility(record:Mapping[str,Any],null_record:Mapping[str,Any]):
    absolute_ok,gates=absolute_eligibility(record)
    null_gates={
        "observed_c2_mean_gt_joint_q95":(
            float(null_record["observed_mean_c2_net_bps"])
            > float(null_record["joint_max_stat_q95"])
        ),
        "fwer_p_le_005":float(null_record["max_stat_fwer_empirical_p"])<=0.05,
    }
    all_gates={**gates,**null_gates}
    return bool(absolute_ok and all(null_gates.values())),all_gates

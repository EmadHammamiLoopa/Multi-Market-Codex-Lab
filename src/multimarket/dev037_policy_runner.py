from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from . import dev030_direction_dataset as dd
from . import dev030_p4_touch_composition as p4
from . import dev034_g3b_r1_core as g3core
from . import dev036_c1_loader as c1loader
from . import dev036_c1_runner as c1runner
from . import dev037_policy_core as core

EXPERIMENT_ID="DEV037-P1"
DESIGN_VERSION="joint-selective-trading-policy-screen-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev037_p1_joint_selective_policy_v1"
)
ARTIFACT_FILENAME="DEV037_P1_JOINT_SELECTIVE_POLICY_RESULT.json"

FORWARD_GUARDS={
    "aug30_reused":False,
    "sep01_or_later_opened":False,
    "railway_opened":False,
    "archive_bucket_opened":False,
    "abundant_love_opened":False,
    "pnl_run":False,
    "fees_scored":False,
    "slippage_scored":False,
    "position_sizing_run":False,
    "leverage_run":False,
    "threshold_search_run":False,
}

class Dev037RunnerError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

def _sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _array_hash(domain:str,ts,values):
    h=hashlib.sha256(domain.encode("ascii")+b"\0")
    t=np.asarray(ts,dtype=np.int64)
    v=np.asarray(values,dtype=np.float64)
    if len(t)!=len(v): raise Dev037RunnerError("hash_length")
    for a,b in zip(t.tolist(),v.tolist(),strict=True):
        h.update(np.asarray(a,dtype=">i8").tobytes())
        h.update(np.asarray(b,dtype=">f8").tobytes())
    return h.hexdigest()

def _stack_touch(e,days):
    xs=[];ys=[];ts=[]
    for d in days:
        z=e.per_day[d]
        xs.append(z.t2.s1_values);ys.append(z.t2.labels);ts.append(z.t2.timestamps_us)
    return np.concatenate(xs),np.concatenate(ys),np.concatenate(ts)

def _stack_direction(e,days):
    xs=[];ys=[];ts=[]
    for d in days:
        z=e.per_day[d]
        m=z.direction_mask
        xs.append(z.btc45_x[m]);ys.append(z.direction_y);ts.append(z.t2.timestamps_us[m])
    return np.concatenate(xs),np.concatenate(ys),np.concatenate(ts)

def _fit_touch_predict(e,fit_days,score_day,tag):
    if len(fit_days)<2:
        raise Dev037RunnerError("touch_fit_days_too_short")
    inner_fit=fit_days[:-1]
    inner_val=(fit_days[-1],)
    xif,yif,_=_stack_touch(e,inner_fit)
    xiv,yiv,_=_stack_touch(e,inner_val)
    xt,yt,_=_stack_touch(e,fit_days)
    z=e.per_day[score_day]
    res=p4.fit_probability_fold(
        fold_id=int(tag),representation="S1",
        x_inner_fit=xif,y_inner_fit=yif,
        x_inner_validation=xiv,y_inner_validation=yiv,
        x_outer_train=xt,y_outer_train=yt,
        x_outer_validation=z.t2.s1_values,y_outer_validation=z.t2.labels,
        validation_timestamps_us=z.t2.timestamps_us,
    )
    return res

def _fit_btc45_predict(e,fit_days,score_day):
    if len(fit_days)<2:
        raise Dev037RunnerError("direction_fit_days_too_short")
    xif,yif,_=_stack_direction(e,fit_days[:-1])
    xiv,yiv,_=_stack_direction(e,(fit_days[-1],))
    selected,ledger=g3core.select_c(xif,yif,xiv,yiv)
    xt,yt,_=_stack_direction(e,fit_days)
    scaler=StandardScaler()
    model=g3core._model(selected)
    model.fit(scaler.fit_transform(xt),yt)
    z=e.per_day[score_day]
    p_all=model.predict_proba(scaler.transform(z.btc45_x))[:,1]
    return {
        "selected_C":float(selected),
        "inner_c_ledger":list(ledger),
        "p_long":p_all,
    }

def _oof_training_predictions(e,outer):
    train_days=tuple(outer.train_days)
    if len(train_days)<3:
        raise Dev037RunnerError("outer_train_too_short")
    pts=[];pls=[];ys=[];tss=[];ledger=[]
    for idx in range(2,len(train_days)):
        day=train_days[idx]
        fit_days=train_days[:idx]
        touch=_fit_touch_predict(e,fit_days,day,1000+outer.fold_id*10+idx)
        direction=_fit_btc45_predict(e,fit_days,day)
        z=e.per_day[day]
        pt=np.asarray(touch.p_touch,dtype=np.float64)
        pl=np.asarray(direction["p_long"],dtype=np.float64)
        if not (len(pt)==len(pl)==len(z.y3)):
            raise Dev037RunnerError("oof_alignment",day.isoformat())
        pts.append(pt);pls.append(pl);ys.append(z.y3);tss.append(z.t2.timestamps_us)
        ledger.append({
            "prediction_day":day.isoformat(),
            "fit_days":[d.isoformat() for d in fit_days],
            "touch_selected_C":float(touch.selected_c),
            "btc45_selected_C":float(direction["selected_C"]),
            "rows":int(len(z.y3)),
            "touch":int(np.sum(z.t2.labels==1)),
            "none":int(np.sum(z.t2.labels==0)),
            "p_touch_sha256":_array_hash("DEV037-OOF-PTOUCH",z.t2.timestamps_us,pt),
            "p_long_sha256":_array_hash("DEV037-OOF-PLONG",z.t2.timestamps_us,pl),
        })
    return {
        "p_touch":np.concatenate(pts),
        "p_long":np.concatenate(pls),
        "y3":np.concatenate(ys),
        "timestamps_us":np.concatenate(tss),
        "ledger":ledger,
    }

def _validation_predictions(e,outer,touch_fold):
    expected=c1runner._direction_expected_hashes(e.g3b_payload,"BTC45")
    d=c1runner._fit_direction_fold(e,"BTC45",outer)
    if d["actual_prediction_sha256"]!=expected[outer.fold_id]:
        raise Dev037RunnerError("btc45_validation_reproduction",str(outer.fold_id))
    z=e.per_day[outer.validation_day]
    if not np.array_equal(z.t2.timestamps_us,touch_fold.timestamps_us):
        raise Dev037RunnerError("validation_touch_alignment",str(outer.fold_id))
    return np.asarray(touch_fold.p_touch,dtype=np.float64),np.asarray(d["all_row_probabilities"],dtype=np.float64)

def _meta_target(y3,p_long):
    y=np.asarray(y3,dtype=np.int8)
    p=np.asarray(p_long,dtype=np.float64)
    pred=np.where(p>=0.5,core.ACTION_LONG,core.ACTION_SHORT).astype(np.int8)
    return ((pred==y)&(y!=0)).astype(np.int8)

def _meta_model(x,y):
    scaler=StandardScaler()
    a=scaler.fit_transform(np.asarray(x,dtype=np.float64))
    m=LogisticRegression(
        C=1.0,solver="lbfgs",l1_ratio=0.0,class_weight=None,
        max_iter=1000,fit_intercept=True,random_state=20260825,
    )
    m.fit(a,np.asarray(y,dtype=np.int8))
    return scaler,m

def _make_fold_policies(e,outer,touch_fold):
    oof=_oof_training_predictions(e,outer)
    vpt,vpl=_validation_predictions(e,outer,touch_fold)
    z=e.per_day[outer.validation_day]

    touch_ref=core.empirical_percentile_reference(oof["p_touch"])
    dir_ref=core.empirical_percentile_reference(core.direction_confidence(oof["p_long"]))

    train_scores=core.score_bundle(
        p_touch=oof["p_touch"],p_long=oof["p_long"],
        touch_reference=touch_ref,dir_reference=dir_ref,
    )
    val_scores=core.score_bundle(
        p_touch=vpt,p_long=vpl,
        touch_reference=touch_ref,dir_reference=dir_ref,
    )

    thresholds={pid:core.threshold_q80(train_scores[pid]) for pid in ("S0","S1","S2","S3","S4")}

    xmeta=core.meta_features(
        p_touch=oof["p_touch"],p_long=oof["p_long"],
        touch_reference=touch_ref,dir_reference=dir_ref,
    )
    ymeta=_meta_target(oof["y3"],oof["p_long"])
    scaler,model=_meta_model(xmeta,ymeta)
    train_s5=model.predict_proba(scaler.transform(xmeta))[:,1]
    xval=core.meta_features(
        p_touch=vpt,p_long=vpl,
        touch_reference=touch_ref,dir_reference=dir_ref,
    )
    val_s5=model.predict_proba(scaler.transform(xval))[:,1]
    thresholds["S5"]=core.threshold_q80(train_s5)
    val_scores["S5"]=val_s5

    folds={}
    for pid in core.POLICY_IDS:
        actions=core.actions_from_score(score=val_scores[pid],threshold=thresholds[pid],p_long=vpl)
        folds[pid]=core.PolicyFold(
            fold_id=int(outer.fold_id),policy_id=pid,threshold=float(thresholds[pid]),
            scores=np.asarray(val_scores[pid],dtype=np.float64),
            actions=actions,y3=np.asarray(z.y3,dtype=np.int8),
            metrics=core.action_metrics(z.y3,actions),
        )
    return folds,{
        "fold_id":int(outer.fold_id),
        "validation_day":outer.validation_day.isoformat(),
        "oof_rows":int(len(oof["y3"])),
        "oof_start_day":oof["ledger"][0]["prediction_day"],
        "oof_end_day":oof["ledger"][-1]["prediction_day"],
        "oof_ledger":oof["ledger"],
        "thresholds":{k:float(v) for k,v in thresholds.items()},
        "meta_positive_count":int(np.sum(ymeta==1)),
        "meta_negative_count":int(np.sum(ymeta==0)),
    }

def run_dev037(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True):
    if any(FORWARD_GUARDS.values()):
        raise Dev037RunnerError("forward_guard")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise Dev037RunnerError("execution_commit")
    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise Dev037RunnerError("noncanonical_output")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY:
        raise Dev037RunnerError("canonical_requires_real")
    if out.exists() or out.is_symlink():
        raise Dev037RunnerError("output_exists")

    e=c1loader.load_c1()
    t2={d:e.per_day[d].t2 for d in dd.HISTORICAL_DAYS}
    touch=p4.fit_t2(t2)

    by_policy={pid:[] for pid in core.POLICY_IDS}
    fold_ledgers=[]
    for outer,touch_fold in zip(dd.OUTER_FOLDS,touch.s1_folds,strict=True):
        folds,ledger=_make_fold_policies(e,outer,touch_fold)
        fold_ledgers.append(ledger)
        for pid in core.POLICY_IDS:
            by_policy[pid].append(folds[pid])
    by_policy={pid:tuple(v) for pid,v in by_policy.items()}

    null=core.joint_temporal_max_stat_null(by_policy)
    records={}
    for pid in core.POLICY_IDS:
        pooled=core.pooled_metrics(by_policy[pid])
        guards=core.operational_guards(by_policy[pid])
        rec={
            "policy_id":pid,
            "policy_name":core.POLICY_NAMES[pid],
            "pooled_metrics":pooled,
            "operational_guards":guards,
            "folds":[{
                "fold_id":int(f.fold_id),
                "threshold":float(f.threshold),
                "metrics":dict(f.metrics),
                "action_sha256":_array_hash(
                    f"DEV037-ACTION-{pid}",
                    e.per_day[dd.OUTER_FOLDS[f.fold_id-1].validation_day].t2.timestamps_us,
                    f.actions.astype(np.float64),
                ),
            } for f in by_policy[pid]],
        }
        if pid!="S0":
            comp=core.compare_to_s0(by_policy["S0"],by_policy[pid])
            nrec=null["per_candidate"][pid]
            survivor=core.is_survivor(comparison=comp,guards=guards,nullrec=nrec)
            rec["comparison_vs_s0"]=comp
            rec["null"]=nrec
            rec["survivor"]=bool(survivor)
        records[pid]=rec

    rank=core.survivor_ranking({
        pid:{
            "comparison":records[pid]["comparison_vs_s0"],
            "null":records[pid]["null"],
            "survivor":records[pid]["survivor"],
        } for pid in core.CHALLENGER_IDS
    })
    s0_usable=all(records["S0"]["operational_guards"].values())
    if rank:
        terminal="DEV037_POLICY_SURVIVOR_FOUND"
        advanced=[rank[0]]
    elif s0_usable:
        terminal="DEV037_NO_CHALLENGER_SURVIVOR_RETAIN_TOUCH_ONLY_POLICY"
        advanced=["S0"]
    else:
        terminal="DEV037_POLICY_FAMILY_NOT_OPERATIONALLY_USABLE"
        advanced=[]

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":terminal,
        "parents":{
            "dev036_c1":{
                "path":"/home/emadh/Multi-Market/evidence/dev036_c1_promoted_direction_composition_v1/DEV036_C1_PROMOTED_DIRECTION_COMPOSITION_RESULT.json",
                "sha256":"9278e4c1ef8868b77e2c45a3cd4bcf93a87c99a77fcbf925a12842b3731708b4",
                "bytes":98670,
            }
        },
        "common_support":{
            "rows":9849,"touch":1341,"none":8508,
            "support_sha256":c1loader.COMMON_SUPPORT_SHA,
            "validation_rows":5628,
        },
        "policy_ids":list(core.POLICY_IDS),
        "target_coverage_quantile":core.TARGET_COVERAGE_QUANTILE,
        "oof_training_ledgers":fold_ledgers,
        "policy_records":records,
        "joint_temporal_null":null,
        "survivor_ranking":rank,
        "advanced_policy":advanced,
        "forward_guards":dict(FORWARD_GUARDS),
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists(): raise Dev037RunnerError("staging_exists")
    staging.mkdir(parents=True)
    try:
        final=staging/ARTIFACT_FILENAME
        with final.open("xb") as h:
            h.write(content);h.flush();os.fsync(h.fileno())
        os.replace(staging,out)
    except BaseException:
        if staging.exists(): shutil.rmtree(staging,ignore_errors=True)
        raise
    final=out/ARTIFACT_FILENAME
    return {
        "artifact_path":str(final),"artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),"status":terminal,
        "advanced_policy":advanced,
    }

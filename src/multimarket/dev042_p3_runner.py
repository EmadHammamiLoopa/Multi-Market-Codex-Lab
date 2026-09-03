from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev030_first_passage as fp
from . import dev042_p1_materialization as mat
from . import dev042_p3_core as core

EXPERIMENT_ID="DEV042-P3"
DESIGN_VERSION="h1800-b32-five-candidate-oof-economic-null-screen-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev042_p3_predictive_screen_v1"
)
ARTIFACT_FILENAME="DEV042_P3_PREDICTIVE_SCREEN_RESULT.json"

P0_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev042_p0_feature_schema_audit_v1/"
    "DEV042_P0_FEATURE_SCHEMA_AUDIT_RESULT.json"
)
P0_SHA="d9259a53d24492f478615c986ed73981f052d483a764935a8dfd68d17212b882"
P0_BYTES=12989

P2_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev042_p2_no_result_preflight_v1/"
    "DEV042_P2_NO_RESULT_PREFLIGHT_RESULT.json"
)
P2_SHA="7a9f190323430d357e3febef16edfd9e5a8971342265c3f24a01d5797f00c6dd"
P2_BYTES=5606

FORWARD_GUARDS={
    "sep01_plus_opened":False,
    "other_market_opened":False,
    "candidate_added":False,
    "hyperparameter_search":False,
    "threshold_search":False,
    "controller_search":False,
    "target_geometry_changed":False,
    "null_redesigned":False,
    "gate_weakened":False,
}

class RunnerError(RuntimeError):
    pass

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _verify_parent(path:Path,sha:str,bytes_:int,name:str):
    if not path.is_file():
        raise RunnerError(f"{name}_missing")
    if path.stat().st_size!=bytes_ or _sha(path)!=sha:
        raise RunnerError(f"{name}_identity")

def _sanitize(x):
    if isinstance(x,float) and math.isinf(x):
        return "INF"
    if isinstance(x,dict):
        return {k:_sanitize(v) for k,v in x.items()}
    if isinstance(x,list):
        return [_sanitize(v) for v in x]
    return x

def _canonical_probabilities(model,X):
    raw=np.asarray(model.predict_proba(X),dtype=np.float64)
    classes=np.asarray(model.classes_,dtype=np.int64)
    pos={int(c):i for i,c in enumerate(classes.tolist())}
    if set(pos)!=set(core.CLASS_ORDER):
        raise RunnerError(f"model_classes:{classes.tolist()}")
    return raw[:,[pos[c] for c in core.CLASS_ORDER]]

def _load_materialized():
    days=tuple(dd.load_authorized_days())
    if tuple(x.day for x in days)!=dd.HISTORICAL_DAYS:
        raise RunnerError("calendar")
    out={}
    raw={}
    for day in days:
        z=mat.materialize_day(day)
        mat.verify_frozen_support(z)
        out[day.day]=z
        raw[day.day]=day
    return out,raw

def _target_support(day,z):
    raw_ts=np.asarray(day.ts,dtype=np.int64)
    positions=np.searchsorted(raw_ts,z.timestamps_us)
    if not np.array_equal(raw_ts[positions],z.timestamps_us):
        raise RunnerError("target_raw_alignment")
    records=fp.label_first_passage_targets(
        day,positions,horizon_seconds=1800,barrier_bps=32,latency_ms=250
    )
    keep=[]
    y=[]
    kept_records=[]
    for i,r in enumerate(records):
        code=core.label_code(r)
        if code is None:
            continue
        keep.append(i)
        y.append(code)
        kept_records.append(r)
    idx=np.asarray(keep,dtype=np.int64)
    yy=np.asarray(y,dtype=np.int8)
    if len(idx)==0 or len(idx)!=len(yy):
        raise RunnerError("empty_target_support")
    return idx,yy,tuple(kept_records)

def _matrix(z,cid):
    return np.asarray(mat.candidate_matrix(z,cid),dtype=np.float64)

def _build_fold_data(materialized,raw_days):
    target={}
    for d in dd.HISTORICAL_DAYS:
        target[d]=_target_support(raw_days[d],materialized[d])
    return target

def _fit_candidate_fold(cid,fold,materialized,target):
    train_X=[]
    train_y=[]
    for d in fold.train_days:
        idx,y,_=target[d]
        X=_matrix(materialized[d],cid)[idx]
        train_X.append(X);train_y.append(y)
    Xtr=np.concatenate(train_X,axis=0)
    ytr=np.concatenate(train_y,axis=0)

    vidx,yv,records=target[fold.validation_day]
    Xv=_matrix(materialized[fold.validation_day],cid)[vidx]
    ts=np.asarray(materialized[fold.validation_day].timestamps_us,dtype=np.int64)[vidx]

    if set(np.unique(ytr).tolist())!=set(core.CLASS_ORDER):
        raise RunnerError(f"train_missing_class:{cid}:{fold.fold_id}")
    if set(np.unique(yv).tolist())!=set(core.CLASS_ORDER):
        raise RunnerError(f"validation_missing_class:{cid}:{fold.fold_id}")

    model=core.make_estimator(cid)
    model.fit(Xtr,ytr)
    p=_canonical_probabilities(model,Xv)
    actions=core.action_from_probabilities(p,core.CLASS_ORDER)
    metrics=core.classification_metrics(yv,p,actions)

    return {
        "fold_id":int(fold.fold_id),
        "validation_day":fold.validation_day.isoformat(),
        "support":int(len(yv)),
        "timestamps_us":ts,
        "y":yv,
        "records":records,
        "probabilities":p,
        "actions":actions,
        "classification":metrics,
    }

def _execute_fold(day,fold_record,actions):
    trades,ignored=core.execute_actions(
        day=f"FOLD{fold_record['fold_id']}",
        actions=actions,
        records=fold_record["records"],
        raw_timestamps_us=day.ts,
        bid=day.bid,
        ask=day.ask,
        book_valid=day.book_valid,
    )
    return trades,ignored

def _pooled_classification(folds):
    y=np.concatenate([f["y"] for f in folds])
    p=np.concatenate([f["probabilities"] for f in folds],axis=0)
    a=np.concatenate([f["actions"] for f in folds])
    return core.classification_metrics(y,p,a)

def _candidate_record(cid,folds,raw_days):
    trades=[]
    ignored=0
    raw_actions=0
    long_trades=short_trades=0
    exit_counts={"TP":0,"SL":0,"FORCED_HORIZON":0}

    for f in folds:
        day=raw_days[dd.HISTORICAL_DAYS[int(f["fold_id"])+2]]
        raw_actions+=int(np.sum(f["actions"]!=core.CLASS_NONE))
        t,ig=_execute_fold(day,f,f["actions"])
        trades.extend(t);ignored+=ig

    trades=tuple(trades)
    for t in trades:
        long_trades+=int(t.side=="LONG")
        short_trades+=int(t.side=="SHORT")
        exit_counts[t.exit_reason]+=1

    fold_order=[f"FOLD{i}" for i in range(1,5)]
    c1=core.economics(trades,core.C1_COST_BPS,fold_order)
    c2=core.economics(trades,core.C2_COST_BPS,fold_order)
    classification=_pooled_classification(folds)

    return {
        "candidate_id":cid,
        "classification":classification,
        "activity":{
            "raw_actions":int(raw_actions),
            "accepted_trades":int(len(trades)),
            "ignored_overlap_actions":int(ignored),
            "long_trades":int(long_trades),
            "short_trades":int(short_trades),
            "tp_exits":int(exit_counts["TP"]),
            "sl_exits":int(exit_counts["SL"]),
            "forced_horizon_exits":int(exit_counts["FORCED_HORIZON"]),
            "execution_invalid":0,
        },
        "c1":c1,
        "c2":c2,
        "folds":[
            {
                "fold_id":f["fold_id"],
                "validation_day":f["validation_day"],
                "support":f["support"],
                "classification":f["classification"],
            }
            for f in folds
        ],
    }

def _null_evaluators(candidate_folds,raw_days):
    evaluators=[]
    for i in range(4):
        fold_id=i+1
        day=raw_days[dd.HISTORICAL_DAYS[i+3]]
        # Records are identical across candidates because common support and target support are identical.
        reference=candidate_folds[core.CANDIDATE_IDS[0]][i]
        def make_eval(day=day,ref=reference):
            def evaluate(actions):
                trades,_=core.execute_actions(
                    day=f"FOLD{ref['fold_id']}",
                    actions=actions,
                    records=ref["records"],
                    raw_timestamps_us=day.ts,
                    bid=day.bid,
                    ask=day.ask,
                    book_valid=day.book_valid,
                )
                return trades
            return evaluate
        evaluators.append(make_eval())
    return tuple(evaluators)

def run(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True):
    if any(FORWARD_GUARDS.values()):
        raise RunnerError("forbidden_activity_guard")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise RunnerError("execution_commit")

    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise RunnerError("noncanonical_output")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY:
        raise RunnerError("canonical_requires_real")
    if out.exists() or out.is_symlink():
        raise RunnerError("output_exists")

    _verify_parent(P0_ARTIFACT,P0_SHA,P0_BYTES,"p0")
    _verify_parent(P2_ARTIFACT,P2_SHA,P2_BYTES,"p2")

    materialized,raw_days=_load_materialized()
    target=_build_fold_data(materialized,raw_days)

    candidate_folds={}
    records={}
    for cid in core.CANDIDATE_IDS:
        folds=tuple(
            _fit_candidate_fold(cid,fold,materialized,target)
            for fold in dd.OUTER_FOLDS
        )
        candidate_folds[cid]=folds
        records[cid]=_candidate_record(cid,folds,raw_days)

    null=core.joint_temporal_max_stat_null(
        observed_records=records,
        fold_actions={
            cid:tuple(f["actions"] for f in candidate_folds[cid])
            for cid in core.CANDIDATE_IDS
        },
        fold_evaluators=_null_evaluators(candidate_folds,raw_days),
    )

    for cid in core.CANDIDATE_IDS:
        final,gates=core.final_eligibility(records[cid],null["per_candidate"][cid])
        records[cid]["null"]=null["per_candidate"][cid]
        records[cid]["eligibility_gates"]=gates
        records[cid]["eligible"]=bool(final)

    ranking=core.rank(records)
    advanced=ranking[:1]
    status=(
        f"DEV042_PREDICTIVE_SURVIVOR_{advanced[0]}"
        if advanced else
        "DEV042_NO_PREDICTIVE_SURVIVOR_FOR_H1800_B32"
    )

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "target":{"horizon_seconds":1800,"barrier_bps":32,"entry_latency_ms":250,"response_latency_ms":250},
        "candidate_ids":list(core.CANDIDATE_IDS),
        "outer_folds":[
            {
                "fold_id":int(f.fold_id),
                "train_days":[d.isoformat() for d in f.train_days],
                "validation_day":f.validation_day.isoformat(),
            }
            for f in dd.OUTER_FOLDS
        ],
        "candidate_records":records,
        "joint_temporal_null":null,
        "eligible_candidates":[cid for cid in core.CANDIDATE_IDS if records[cid]["eligible"]],
        "survivor_ranking":ranking,
        "advanced_candidate":advanced,
        "cost_envelopes_bps":{"C1":10.0,"C2":16.0},
        "forward_guards":dict(FORWARD_GUARDS),
        "sep01_plus_remains_sealed":True,
        "other_markets_remain_sealed":True,
    }

    content=(json.dumps(_sanitize(payload),sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists():
        raise RunnerError("staging_exists")
    staging.mkdir(parents=True)
    try:
        final=staging/ARTIFACT_FILENAME
        with final.open("xb") as h:
            h.write(content);h.flush();os.fsync(h.fileno())
        os.replace(staging,out)
    except BaseException:
        if staging.exists():shutil.rmtree(staging,ignore_errors=True)
        raise

    final=out/ARTIFACT_FILENAME
    return {
        "artifact_path":str(final),
        "artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),
        "status":status,
        "eligible_candidates":[cid for cid in core.CANDIDATE_IDS if records[cid]["eligible"]],
        "advanced_candidate":advanced,
    }

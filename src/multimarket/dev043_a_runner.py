from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev030_first_passage as fp
from . import dev042_p1_materialization as mat
from . import dev043_p0_core as decomp
from . import dev043_a_core as core

EXPERIMENT_ID="DEV043-A"
DESIGN_VERSION="event-conditioned-touch-stage-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev043_a_touch_screen_v1"
)
ARTIFACT_FILENAME="DEV043_A_TOUCH_SCREEN_RESULT.json"

P0_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev043_p0_parent_schema_audit_v1/"
    "DEV043_P0_PARENT_SCHEMA_AUDIT_RESULT.json"
)
P0_BYTES=6387
P0_SHA="5d6b704dba88f43a681a73d9cca637bdb3f8d565ec96aaf389ee46302a15bf3e"

FORWARD_GUARDS={
    "sep01_plus_opened":False,
    "other_market_opened":False,
    "candidate_added":False,
    "hyperparameter_search":False,
    "threshold_search":False,
    "calibration_layer":False,
    "target_changed":False,
    "null_redesigned":False,
    "gate_weakened":False,
}

class RunnerError(RuntimeError):
    pass

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def _verify_parent():
    if not P0_ARTIFACT.is_file():
        raise RunnerError("p0_missing")
    if P0_ARTIFACT.stat().st_size!=P0_BYTES or _sha(P0_ARTIFACT)!=P0_SHA:
        raise RunnerError("p0_identity")
    x=json.loads(P0_ARTIFACT.read_text(encoding="utf-8"))
    if x.get("status")!="DEV043_P0_PARENT_SCHEMA_AUDIT_PASS":
        raise RunnerError("p0_status")

def _candidate_matrix(z,cid):
    if cid=="A0_TOUCH_PRICE_LOGIT":
        return np.asarray(z.X0,dtype=np.float64)
    if cid=="A1_TOUCH_PRESSURE_LOGIT":
        return np.asarray(z.X2,dtype=np.float64)
    if cid=="A2_TOUCH_COMBINED_HGB":
        return np.asarray(z.X3,dtype=np.float64)
    raise RunnerError(f"unknown_candidate:{cid}")

def _target_for_day(day,z):
    raw_ts=np.asarray(day.ts,dtype=np.int64)
    pos=np.searchsorted(raw_ts,z.timestamps_us)
    if not np.array_equal(raw_ts[pos],z.timestamps_us):
        raise RunnerError(f"raw_alignment:{z.date}")
    records=fp.label_first_passage_targets(
        day,pos,horizon_seconds=1800,barrier_bps=32,latency_ms=250
    )
    if len(records)!=len(z.timestamps_us):
        raise RunnerError(f"record_count:{z.date}")
    keep=[]
    y=[]
    for i,r in enumerate(records):
        d=decomp.decompose_record(r)
        if not d.valid:
            continue
        if d.stage_a_event not in (decomp.EVENT_NONE,decomp.EVENT_TOUCH):
            raise RunnerError("stage_a_label")
        keep.append(i)
        y.append(int(d.stage_a_event))
    idx=np.asarray(keep,dtype=np.int64)
    yy=np.asarray(y,dtype=np.int8)
    if len(idx)==0 or set(np.unique(yy).tolist())!={0,1}:
        raise RunnerError(f"stage_a_support:{z.date}")
    return idx,yy

def _load():
    days=tuple(dd.load_authorized_days())
    if tuple(x.day for x in days)!=dd.HISTORICAL_DAYS:
        raise RunnerError("calendar")
    materialized={}
    raw={}
    target={}
    for day in days:
        z=mat.materialize_day(day)
        mat.verify_frozen_support(z)
        materialized[day.day]=z
        raw[day.day]=day
        target[day.day]=_target_for_day(day,z)
    return materialized,raw,target

def _fit_fold(cid,fold,materialized,target):
    train_X=[]
    train_y=[]
    for d in fold.train_days:
        idx,y=target[d]
        train_X.append(_candidate_matrix(materialized[d],cid)[idx])
        train_y.append(y)
    Xtr=np.concatenate(train_X,axis=0)
    ytr=np.concatenate(train_y)

    vidx,yv=target[fold.validation_day]
    Xv=_candidate_matrix(materialized[fold.validation_day],cid)[vidx]
    ts=np.asarray(materialized[fold.validation_day].timestamps_us,dtype=np.int64)[vidx]

    if set(np.unique(ytr).tolist())!={0,1}:
        raise RunnerError(f"train_class:{cid}:{fold.fold_id}")
    if set(np.unique(yv).tolist())!={0,1}:
        raise RunnerError(f"validation_class:{cid}:{fold.fold_id}")

    model=core.make_estimator(cid)
    model.fit(Xtr,ytr)
    p=core.touch_probability(model,Xv)

    return {
        "fold_id":int(fold.fold_id),
        "validation_day":fold.validation_day.isoformat(),
        "timestamps_us":ts,
        "y":yv,
        "p_touch":p,
    }

def run(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True):
    if any(FORWARD_GUARDS.values()):
        raise RunnerError("forbidden_guard")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise RunnerError("execution_commit")

    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise RunnerError("noncanonical_output")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY:
        raise RunnerError("canonical_requires_real")
    if out.exists() or out.is_symlink():
        raise RunnerError("output_exists")

    _verify_parent()
    materialized,raw,target=_load()

    candidate_folds={}
    records={}

    for cid in core.CANDIDATE_IDS:
        folds=tuple(
            _fit_fold(cid,fold,materialized,target)
            for fold in dd.OUTER_FOLDS
        )
        candidate_folds[cid]=folds

    for i in range(4):
        ref=candidate_folds[core.CANDIDATE_IDS[0]][i]
        for cid in core.CANDIDATE_IDS[1:]:
            cur=candidate_folds[cid][i]
            if not np.array_equal(cur["timestamps_us"],ref["timestamps_us"]):
                raise RunnerError(f"timestamp_misalignment:{cid}:{i+1}")
            if not np.array_equal(cur["y"],ref["y"]):
                raise RunnerError(f"label_misalignment:{cid}:{i+1}")

    null=core.joint_temporal_max_stat_null(candidate_folds=candidate_folds)

    for cid in core.CANDIDATE_IDS:
        pooled,per,loo=core.pooled_and_fold_metrics(candidate_folds[cid])
        rec={
            "candidate_id":cid,
            "pooled":pooled,
            "per_fold":per,
            "leave_one_fold_out":loo,
            "null":null["per_candidate"][cid],
        }
        eligible,gates=core.eligibility(rec,rec["null"])
        rec["eligibility_gates"]=gates
        rec["eligible"]=bool(eligible)
        records[cid]=rec

    ranking=core.rank(records)
    advanced=ranking[:1]
    status=(
        f"DEV043_A_TOUCH_SURVIVOR_{advanced[0]}"
        if advanced else
        "DEV043_A_NO_TOUCH_SURVIVOR"
    )

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "target":{
            "horizon_seconds":1800,
            "barrier_bps":32,
            "stage":"TOUCH_VS_NONE",
        },
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
        "parent_p0":{
            "bytes":P0_BYTES,
            "sha256":P0_SHA,
        },
        "forward_guards":dict(FORWARD_GUARDS),
        "sep01_plus_remains_sealed":True,
        "other_markets_remain_sealed":True,
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
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
        if staging.exists():
            shutil.rmtree(staging,ignore_errors=True)
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

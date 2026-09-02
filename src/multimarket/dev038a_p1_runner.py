from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev030_p4_touch_composition as p4
from . import dev038a_p0_core as p0core
from . import dev038a_p1_core as core

EXPERIMENT_ID="DEV038-A-P1"
DESIGN_VERSION="joint-opportunity-representation-screen-v1"

P0_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev038a_p0_common_support_v1/"
    "DEV038A_P0_COMMON_SUPPORT_RESULT.json"
)
P0_SHA="fd4639c003c4888a7316386b4ddb0031bf9bfb59d1d05afe0dc3fcb08b1ea6a5"
P0_BYTES=8464

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev038a_p1_joint_screen_v1"
)
ARTIFACT_FILENAME="DEV038A_P1_JOINT_SCREEN_RESULT.json"

FORWARD_GUARDS={
    "candidate_specific_support_used":False,
    "target_geometry_tuned":False,
    "model_family_changed":False,
    "pnl_run":False,
    "fees_run":False,
    "slippage_run":False,
    "forward_data_opened":False,
}

class RunnerError(RuntimeError):
    pass

def _sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _load_parent():
    if not P0_ARTIFACT.is_file():
        raise RunnerError("p0_parent_missing")
    if _sha(P0_ARTIFACT)!=P0_SHA or P0_ARTIFACT.stat().st_size!=P0_BYTES:
        raise RunnerError("p0_parent_identity")
    x=json.loads(P0_ARTIFACT.read_text(encoding="utf-8"))
    if x.get("status")!="DEV038A_P0_COMMON_SUPPORT_PASS":
        raise RunnerError("p0_parent_status")
    return x

def _candidate_datasets():
    loaded=tuple(dd.load_authorized_days())
    if tuple(x.day for x in loaded)!=dd.HISTORICAL_DAYS:
        raise RunnerError("calendar")
    out={cid:{} for cid,_,_ in p0core.CANDIDATES}
    for cid,w,b in p0core.CANDIDATES:
        for daydata in loaded:
            ds=dd.build_candidate_day(
                daydata,target=p0core.TARGET,window_seconds=w,block=b
            )
            out[cid][daydata.day]=ds
    return out

def _common_ledger(parent):
    return {
        dd.date.fromisoformat(d["date"]) if hasattr(dd,"date") else None: d
        for d in parent["common_support"]["per_day"]
    }

def _map_common(parent,candidates):
    per={cid:{} for cid,_,_ in p0core.CANDIDATES}
    for cid,_,_ in p0core.CANDIDATES:
        for day in dd.HISTORICAL_DAYS:
            per[cid][day]=p0core.build_audit_day(cid,candidates[cid][day])
    common=p0core.common_support(per)
    expected={d["date"]:d for d in parent["common_support"]["per_day"]}
    for day in dd.HISTORICAL_DAYS:
        ts,y=common[day]
        e=expected[day.isoformat()]
        if len(ts)!=int(e["rows"]):
            raise RunnerError(f"common_rows_{day}")
        if p0core.support_sha(ts)!=e["support_sha256"]:
            raise RunnerError(f"common_sha_{day}")
        if int(np.sum(y==1))!=int(e["touch"]) or int(np.sum(y==0))!=int(e["none"]):
            raise RunnerError(f"common_label_counts_{day}")
    return common

def _matrix_on_common(ds,common_ts):
    ts_all=np.asarray(ds.decision_timestamps_us,dtype=np.int64)
    pos={int(t):i for i,t in enumerate(ts_all.tolist())}
    idx=np.asarray([pos[int(t)] for t in common_ts],dtype=np.int64)
    x=np.asarray(ds.s1_values,dtype=np.float64)[idx]
    if not np.all(np.isfinite(x)):
        raise RunnerError("nonfinite_common_matrix")
    return x

def _stack(mats,labels,days):
    x=np.concatenate([mats[d] for d in days])
    y=np.concatenate([labels[d] for d in days]).astype(np.int8,copy=False)
    ts=np.concatenate([labels[d][1] if False else np.array([],dtype=np.int64) for d in []])
    return x,y

def _fit_fold(cid,outer,mats,labels,timestamps):
    inner_val=outer.train_days[-1]
    inner_fit=outer.train_days[:-1]
    xif=np.concatenate([mats[d] for d in inner_fit])
    yif=np.concatenate([labels[d] for d in inner_fit])
    xiv=mats[inner_val]
    yiv=labels[inner_val]
    xt=np.concatenate([mats[d] for d in outer.train_days])
    yt=np.concatenate([labels[d] for d in outer.train_days])
    xv=mats[outer.validation_day]
    yv=labels[outer.validation_day]
    ts=timestamps[outer.validation_day]
    r=p4.fit_probability_fold(
        fold_id=int(outer.fold_id),
        representation="S1",
        x_inner_fit=xif,y_inner_fit=yif,
        x_inner_validation=xiv,y_inner_validation=yiv,
        x_outer_train=xt,y_outer_train=yt,
        x_outer_validation=xv,y_outer_validation=yv,
        validation_timestamps_us=ts,
    )
    m=core.metrics(yv,r.p_touch)
    return {
        "fold_id":int(outer.fold_id),
        "validation_day":outer.validation_day.isoformat(),
        "selected_C":float(r.selected_c),
        "y":np.asarray(yv,dtype=np.int8),
        "p":np.asarray(r.p_touch,dtype=np.float64),
        "metrics":m,
        "prediction_sha256":r.prediction_sha256,
        "inner_c_ledger":[dict(x) for x in r.inner_c_ledger],
    }

def _serialize_fold(f):
    return {
        "fold_id":f["fold_id"],
        "validation_day":f["validation_day"],
        "selected_C":f["selected_C"],
        "metrics":dict(f["metrics"]),
        "prediction_sha256":f["prediction_sha256"],
        "inner_c_ledger":f["inner_c_ledger"],
    }

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

    parent=_load_parent()
    candidates=_candidate_datasets()
    common=_map_common(parent,candidates)
    timestamps={d:common[d][0] for d in dd.HISTORICAL_DAYS}
    labels={d:common[d][1] for d in dd.HISTORICAL_DAYS}

    mats={cid:{} for cid,_,_ in p0core.CANDIDATES}
    for cid,_,_ in p0core.CANDIDATES:
        for d in dd.HISTORICAL_DAYS:
            mats[cid][d]=_matrix_on_common(candidates[cid][d],timestamps[d])
            if len(mats[cid][d])!=len(labels[d]):
                raise RunnerError("matrix_label_length")

    folds={cid:[] for cid in core.CANDIDATE_IDS}
    for cid in core.CANDIDATE_IDS:
        for outer in dd.OUTER_FOLDS:
            folds[cid].append(_fit_fold(cid,outer,mats[cid],labels,timestamps))
        folds[cid]=tuple(folds[cid])

    null=core.joint_max_stat_null(folds)
    records={}
    for cid in core.CANDIDATE_IDS:
        rec={
            "candidate_id":cid,
            "pooled_metrics":core.pooled_metrics(folds[cid]),
            "folds":[_serialize_fold(f) for f in folds[cid]],
        }
        if cid!="A0":
            comp=core.compare(folds["A0"],folds[cid])
            nrec=null["per_candidate"][cid]
            rec["comparison_vs_a0"]=comp
            rec["null"]=nrec
            rec["survivor"]=bool(core.is_survivor(comp,nrec))
        records[cid]=rec

    ranked=core.rank({
        cid:{
            "comparison":records[cid]["comparison_vs_a0"],
            "null":records[cid]["null"],
            "survivor":records[cid]["survivor"],
        } for cid in core.CHALLENGER_IDS
    })
    if ranked:
        status="DEV038A_P1_DEVELOPMENT_SURVIVOR_FOUND"
        advanced=[ranked[0]]
    else:
        status="DEV038A_P1_NO_CHALLENGER_SURVIVOR_RETAIN_A0"
        advanced=["A0"]

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "parent_p0":{"path":str(P0_ARTIFACT),"sha256":P0_SHA,"bytes":P0_BYTES},
        "candidate_ids":list(core.CANDIDATE_IDS),
        "challenger_ids":list(core.CHALLENGER_IDS),
        "common_support":{
            "rows":int(parent["common_support"]["rows"]),
            "per_day":parent["common_support"]["per_day"],
        },
        "candidate_records":records,
        "joint_temporal_null":null,
        "survivor_ranking":ranked,
        "advanced_candidate":advanced,
        "forward_guards":dict(FORWARD_GUARDS),
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
        if staging.exists(): shutil.rmtree(staging,ignore_errors=True)
        raise
    final=out/ARTIFACT_FILENAME
    return {
        "artifact_path":str(final),
        "artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),
        "status":status,
        "advanced_candidate":advanced,
    }

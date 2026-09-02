from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev038a_p0_core as core

EXPERIMENT_ID="DEV038-A-P0"
DESIGN_VERSION="opportunity-filter-common-support-audit-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev038a_p0_common_support_v1"
)
ARTIFACT_FILENAME="DEV038A_P0_COMMON_SUPPORT_RESULT.json"

FORWARD_GUARDS={
    "model_fit_run":False,
    "predictive_metric_run":False,
    "pnl_run":False,
    "fees_run":False,
    "slippage_run":False,
    "forward_data_opened":False,
}

class P0Error(RuntimeError):
    pass

def _sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def run(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True):
    if any(FORWARD_GUARDS.values()):
        raise P0Error("forward_guard")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise P0Error("execution_commit")
    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise P0Error("noncanonical_output")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY:
        raise P0Error("canonical_requires_real")
    if out.exists() or out.is_symlink():
        raise P0Error("output_exists")

    manifest=dd.verify_input_manifest()
    loaded=tuple(dd.load_authorized_days())
    if tuple(d.day for d in loaded)!=dd.HISTORICAL_DAYS:
        raise P0Error("calendar")

    per={cid:{} for cid,_,_ in core.CANDIDATES}
    for cid,w,b in core.CANDIDATES:
        key=dd.CandidateKey(core.TARGET,w,b)
        for daydata in loaded:
            ds=dd.build_candidate_day(
                daydata,target=core.TARGET,window_seconds=w,block=b
            )
            if ds.key!=key:
                raise P0Error("candidate_key")
            per[cid][daydata.day]=core.build_audit_day(cid,ds)

    common=core.common_support(per)
    candidate_public={}
    incumbent_total=0
    common_total=0

    for cid,w,b in core.CANDIDATES:
        days=[]
        total=0
        for day in dd.HISTORICAL_DAYS:
            z=per[cid][day]
            total+=len(z.valid_labels)
            days.append({
                "date":day.isoformat(),
                "valid_rows":int(len(z.valid_labels)),
                "touch":int(np.sum(z.valid_labels==1)),
                "none":int(np.sum(z.valid_labels==0)),
                "support_sha256":core.support_sha(z.valid_timestamps_us),
            })
        candidate_public[cid]={
            "window_seconds":w,
            "block":b,
            "feature_count":int(per[cid][dd.HISTORICAL_DAYS[0]].feature_count),
            "raw_lookback_ns":int(per[cid][dd.HISTORICAL_DAYS[0]].raw_lookback_ns),
            "aggregate_valid_rows":int(total),
            "per_day":days,
        }
        if cid=="A0":
            incumbent_total=total

    common_days=[]
    for day in dd.HISTORICAL_DAYS:
        ts,y=common[day]
        common_total+=len(y)
        common_days.append({
            "date":day.isoformat(),
            "rows":int(len(y)),
            "touch":int(np.sum(y==1)),
            "none":int(np.sum(y==0)),
            "support_sha256":core.support_sha(ts),
        })

    retained=float(common_total/incumbent_total)
    validation_ok=True
    training_ok=True
    for fold in dd.OUTER_FOLDS:
        vy=common[fold.validation_day][1]
        ty=np.concatenate([common[d][1] for d in fold.train_days])
        validation_ok &= len(np.unique(vy))==2
        training_ok &= len(np.unique(ty))==2

    feasible=(
        retained>=0.90
        and validation_ok
        and training_ok
    )
    status=(
        "DEV038A_P0_COMMON_SUPPORT_PASS"
        if feasible else
        "DEV038A_P0_COMMON_SUPPORT_FAIL"
    )

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "target":{"symbol":"BTCUSDT","target_id":"A","horizon_seconds":120,"barrier_bps":16},
        "candidate_order":[cid for cid,_,_ in core.CANDIDATES],
        "candidates":candidate_public,
        "common_support":{
            "rows":int(common_total),
            "incumbent_a0_rows":int(incumbent_total),
            "retained_fraction_vs_a0":retained,
            "per_day":common_days,
        },
        "gates":{
            "retained_fraction_ge_090":bool(retained>=0.90),
            "all_outer_validation_folds_both_classes":bool(validation_ok),
            "all_outer_training_folds_both_classes":bool(training_ok),
        },
        "authorized_input_manifest":[
            {"date":m.day.isoformat(),"sha256":m.sha256,"bytes":int(m.bytes)}
            for m in manifest
        ],
        "forward_guards":dict(FORWARD_GUARDS),
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists():
        raise P0Error("staging_exists")
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
    }

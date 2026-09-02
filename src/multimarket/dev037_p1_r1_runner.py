from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev036_c1_loader as c1loader
from . import dev037_policy_core as policy
from . import dev037_p0_r1_coverage_core as coverage
from . import dev037_p0_r1_coverage_runner as r1runner
from . import dev037_p1_r1_core as core

EXPERIMENT_ID="DEV037-P1-R1"
DESIGN_VERSION="four-policy-w120-correctness-screen-v1"
W=120
POLICIES=core.POLICY_IDS

R2_ARTIFACT=Path("/home/emadh/Multi-Market/evidence/dev037_p0_r2_operationally_pruned_controller_v1/DEV037_P0_R2_OPERATIONALLY_PRUNED_CONTROLLER_RESULT.json")
R2_SHA="494122f1aea64fb2a4c956d674330d9a400709656f0e116187d6fa2fefaa3336"
R2_BYTES=27056

REAL_OUTPUT_DIRECTORY=Path("/home/emadh/Multi-Market/evidence/dev037_p1_r1_four_policy_w120_correctness_v1")
ARTIFACT_FILENAME="DEV037_P1_R1_FOUR_POLICY_W120_CORRECTNESS_RESULT.json"

FORWARD_GUARDS={
    "w360_correctness_scored":False,
    "w720_correctness_scored":False,
    "s3_correctness_scored":False,
    "s4_correctness_scored":False,
    "pnl_run":False,
    "fees_run":False,
    "slippage_run":False,
    "position_sizing_run":False,
    "leverage_run":False,
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

def _action_hash(pid:str,fid:int,actions):
    h=hashlib.sha256(f"DEV037-P1-R1-ACTION-{pid}-F{fid}".encode()+b"\0")
    h.update(np.asarray(actions,dtype=np.int8).tobytes())
    return h.hexdigest()

def _load_r2():
    if not R2_ARTIFACT.is_file():
        raise RunnerError("r2_parent_missing")
    if _sha(R2_ARTIFACT)!=R2_SHA or R2_ARTIFACT.stat().st_size!=R2_BYTES:
        raise RunnerError("r2_parent_identity")
    x=json.loads(R2_ARTIFACT.read_text(encoding="utf-8"))
    if x.get("status")!="DEV037_P0_R2_CONTROLLER_SELECTED":
        raise RunnerError("r2_parent_status")
    if x.get("selected_controller_window")!=120:
        raise RunnerError("r2_parent_controller")
    return x

def _fold_records(e,r2):
    by={pid:[] for pid in POLICIES}
    reproduction=[]
    for outer in dd.OUTER_FOLDS:
        z=r1runner._fold_score_streams(e,outer)
        y3=np.asarray(e.per_day[outer.validation_day].y3,dtype=np.int8)
        fold_repro={"fold_id":int(outer.fold_id),"validation_day":outer.validation_day.isoformat(),"policies":{}}
        for pid in POLICIES:
            rr=coverage.summarize(
                scores=z["validation_scores"][pid],
                p_long=z["validation_p_long"],
                warm_scores=z["train_scores"][pid],
                window=W,
            )
            parent=r2["folds"][outer.fold_id-1]["controllers"]["120"][pid]
            exact=(
                int(rr.action_count)==int(parent["action_count"])
                and int(rr.abstain_count)==int(parent["abstain_count"])
                and int(rr.long_count)==int(parent["long_count"])
                and int(rr.short_count)==int(parent["short_count"])
                and float(rr.coverage)==float(parent["coverage"])
                and bool(coverage.feasible(rr))==bool(parent["operationally_feasible"])
            )
            fold_repro["policies"][pid]={
                "reproduced":bool(exact),
                "coverage":float(rr.coverage),
                "action_count":int(rr.action_count),
                "abstain_count":int(rr.abstain_count),
                "long_count":int(rr.long_count),
                "short_count":int(rr.short_count),
            }
            if not exact:
                raise RunnerError(f"operational_reproduction_failure_F{outer.fold_id}_{pid}")
            metrics=policy.action_metrics(y3,rr.actions)
            by[pid].append({
                "fold_id":int(outer.fold_id),
                "validation_day":outer.validation_day.isoformat(),
                "y3":y3,
                "actions":np.asarray(rr.actions,dtype=np.int8),
                "metrics":metrics,
                "action_sha256":_action_hash(pid,outer.fold_id,rr.actions),
            })
        reproduction.append(fold_repro)
    return {k:tuple(v) for k,v in by.items()},reproduction

def _serialize_fold(f):
    return {
        "fold_id":int(f["fold_id"]),
        "validation_day":f["validation_day"],
        "metrics":dict(f["metrics"]),
        "action_sha256":f["action_sha256"],
    }

def _pooled_metrics(fs):
    y=np.concatenate([f["y3"] for f in fs])
    a=np.concatenate([f["actions"] for f in fs])
    return policy.action_metrics(y,a)

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

    r2=_load_r2()
    e=c1loader.load_c1()
    by,reproduction=_fold_records(e,r2)

    null=core.joint_max_stat_null(by)
    records={}
    for pid in POLICIES:
        rec={
            "policy_id":pid,
            "pooled_metrics":_pooled_metrics(by[pid]),
            "folds":[_serialize_fold(f) for f in by[pid]],
        }
        if pid!="S0":
            comp=core.compare(by["S0"],by[pid])
            nrec=null["per_candidate"][pid]
            rec["comparison_vs_s0"]=comp
            rec["null"]=nrec
            rec["survivor"]=bool(core.is_survivor(comp,nrec))
        records[pid]=rec

    ranked=core.rank({
        pid:{
            "comparison":records[pid]["comparison_vs_s0"],
            "null":records[pid]["null"],
            "survivor":records[pid]["survivor"],
        } for pid in core.CHALLENGER_IDS
    })
    if ranked:
        status="DEV037_P1_R1_POLICY_SURVIVOR_FOUND"
        advanced=[ranked[0]]
    else:
        status="DEV037_P1_R1_NO_CHALLENGER_SURVIVOR_RETAIN_S0"
        advanced=["S0"]

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "parents":{"r2":{"path":str(R2_ARTIFACT),"sha256":R2_SHA,"bytes":R2_BYTES,"selected_controller_window":120}},
        "policy_ids":list(POLICIES),
        "challenger_ids":list(core.CHALLENGER_IDS),
        "controller_window":120,
        "operational_reproduction":reproduction,
        "policy_records":records,
        "joint_temporal_null":null,
        "survivor_ranking":ranked,
        "advanced_policy":advanced,
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
        if staging.exists():
            shutil.rmtree(staging,ignore_errors=True)
        raise

    final=out/ARTIFACT_FILENAME
    return {
        "artifact_path":str(final),
        "artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),
        "status":status,
        "advanced_policy":advanced,
    }

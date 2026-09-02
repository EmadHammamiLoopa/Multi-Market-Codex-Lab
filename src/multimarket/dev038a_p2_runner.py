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
from . import dev038a_p2_core as core

EXPERIMENT_ID="DEV038-A-P2"
DESIGN_VERSION="final-controller-correctness-screen-v1"

R2_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev037_p0_r2_operationally_pruned_controller_v1/"
    "DEV037_P0_R2_OPERATIONALLY_PRUNED_CONTROLLER_RESULT.json"
)
R2_SHA="494122f1aea64fb2a4c956d674330d9a400709656f0e116187d6fa2fefaa3336"
R2_BYTES=27056

DEV037_P1_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev037_p1_r1_four_policy_w120_correctness_v1/"
    "DEV037_P1_R1_FOUR_POLICY_W120_CORRECTNESS_RESULT.json"
)
DEV037_P1_SHA="9a9ade5fbc9e564f192786e75551277174907afad26c76a927099e7d859f0cee"
DEV037_P1_BYTES=236045

DEV038A_P1_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev038a_p1_joint_screen_v1/"
    "DEV038A_P1_JOINT_SCREEN_RESULT.json"
)
DEV038A_P1_SHA="16292d1f730561427a4623a052441f3ab20db0a96eeefac06b6f0a0391c5e549"
DEV038A_P1_BYTES=287084

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev038a_p2_final_controller_correctness_v1"
)
ARTIFACT_FILENAME="DEV038A_P2_FINAL_CONTROLLER_CORRECTNESS_RESULT.json"

FORWARD_GUARDS={
    "sep01_plus_opened":False,
    "aug30_reused_as_fresh":False,
    "pnl_run":False,
    "fees_run":False,
    "slippage_run":False,
    "position_sizing_run":False,
    "leverage_run":False,
    "model_family_changed":False,
    "opportunity_representation_changed":False,
    "direction_logic_changed":False,
    "target_geometry_changed":False,
    "quantile_changed":False,
}

class RunnerError(RuntimeError):
    pass

def _sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _load_parent(path:Path,sha:str,nbytes:int,status:str):
    if not path.is_file():
        raise RunnerError(f"parent_missing:{path.name}")
    if _sha(path)!=sha or path.stat().st_size!=nbytes:
        raise RunnerError(f"parent_identity:{path.name}")
    x=json.loads(path.read_text(encoding="utf-8"))
    if x.get("status")!=status:
        raise RunnerError(f"parent_status:{path.name}:{x.get('status')}")
    return x

def _action_hash(cid:str,fid:int,actions):
    h=hashlib.sha256(f"DEV038-A-P2-ACTION-{cid}-F{fid}".encode()+b"\0")
    h.update(np.asarray(actions,dtype=np.int8).tobytes())
    return h.hexdigest()

def _threshold_summary(thresholds):
    t=np.asarray(thresholds,dtype=np.float64)
    return {
        "first":float(t[0]),
        "last":float(t[-1]),
        "min":float(np.min(t)),
        "median":float(np.median(t)),
        "max":float(np.max(t)),
    }

def _fold_records(e,r2):
    by={cid:[] for cid in core.CONTROLLER_IDS}
    reproduction=[]

    for outer in dd.OUTER_FOLDS:
        z=r1runner._fold_score_streams(e,outer)
        y3=np.asarray(e.per_day[outer.validation_day].y3,dtype=np.int8)

        if len(y3)!=int(z["validation_rows"]):
            raise RunnerError(f"validation_length_F{outer.fold_id}")

        fold_repro={
            "fold_id":int(outer.fold_id),
            "validation_day":outer.validation_day.isoformat(),
            "controllers":{},
        }

        for cid in core.CONTROLLER_IDS:
            w=core.WINDOW_BY_ID[cid]
            rr=coverage.summarize(
                scores=z["validation_scores"]["S0"],
                p_long=z["validation_p_long"],
                warm_scores=z["train_scores"]["S0"],
                window=w,
            )

            parent=r2["folds"][outer.fold_id-1]["controllers"][str(w)]["S0"]
            exact=(
                int(rr.action_count)==int(parent["action_count"])
                and int(rr.abstain_count)==int(parent["abstain_count"])
                and int(rr.long_count)==int(parent["long_count"])
                and int(rr.short_count)==int(parent["short_count"])
                and float(rr.coverage)==float(parent["coverage"])
                and bool(coverage.feasible(rr))==bool(parent["operationally_feasible"])
            )
            if not exact:
                raise RunnerError(f"r2_operational_reproduction_failure_F{outer.fold_id}_{cid}")

            metrics=policy.action_metrics(y3,rr.actions)
            fold_repro["controllers"][cid]={
                "window":int(w),
                "reproduced":True,
                "coverage":float(rr.coverage),
                "action_count":int(rr.action_count),
                "abstain_count":int(rr.abstain_count),
                "long_count":int(rr.long_count),
                "short_count":int(rr.short_count),
            }

            by[cid].append({
                "fold_id":int(outer.fold_id),
                "validation_day":outer.validation_day.isoformat(),
                "y3":y3,
                "actions":np.asarray(rr.actions,dtype=np.int8),
                "metrics":metrics,
                "threshold_summary":_threshold_summary(rr.thresholds),
                "mean_abs_rolling60_error":float(rr.mean_abs_rolling60_error),
                "max_abs_rolling60_error":float(rr.max_abs_rolling60_error),
                "rolling60_outside_count":int(rr.rolling60_outside_count),
                "action_state_switches":int(rr.action_state_switches),
                "warm_start_count":int(rr.warm_start_count),
                "action_sha256":_action_hash(cid,outer.fold_id,rr.actions),
            })

        reproduction.append(fold_repro)

    return {k:tuple(v) for k,v in by.items()},reproduction

def _pooled_metrics(fs):
    y=np.concatenate([f["y3"] for f in fs])
    a=np.concatenate([f["actions"] for f in fs])
    return policy.action_metrics(y,a)

def _serialize_fold(f):
    return {
        "fold_id":int(f["fold_id"]),
        "validation_day":f["validation_day"],
        "metrics":dict(f["metrics"]),
        "threshold_summary":dict(f["threshold_summary"]),
        "mean_abs_rolling60_error":float(f["mean_abs_rolling60_error"]),
        "max_abs_rolling60_error":float(f["max_abs_rolling60_error"]),
        "rolling60_outside_count":int(f["rolling60_outside_count"]),
        "action_state_switches":int(f["action_state_switches"]),
        "warm_start_count":int(f["warm_start_count"]),
        "action_sha256":f["action_sha256"],
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

    r2=_load_parent(
        R2_ARTIFACT,R2_SHA,R2_BYTES,"DEV037_P0_R2_CONTROLLER_SELECTED"
    )
    d37=_load_parent(
        DEV037_P1_ARTIFACT,DEV037_P1_SHA,DEV037_P1_BYTES,
        "DEV037_P1_R1_NO_CHALLENGER_SURVIVOR_RETAIN_S0"
    )
    d38=_load_parent(
        DEV038A_P1_ARTIFACT,DEV038A_P1_SHA,DEV038A_P1_BYTES,
        "DEV038A_P1_NO_CHALLENGER_SURVIVOR_RETAIN_A0"
    )

    if r2.get("selected_controller_window")!=120:
        raise RunnerError("r2_selected_window")
    if d37.get("advanced_policy")!=["S0"]:
        raise RunnerError("dev037_advanced_policy")
    if d38.get("advanced_candidate")!=["A0"]:
        raise RunnerError("dev038a_p1_advanced_candidate")

    e=c1loader.load_c1()
    by,reproduction=_fold_records(e,r2)

    null=core.joint_max_stat_null(by)
    records={}

    for cid in core.CONTROLLER_IDS:
        rec={
            "controller_id":cid,
            "window":int(core.WINDOW_BY_ID[cid]),
            "pooled_metrics":_pooled_metrics(by[cid]),
            "operational_guards":core.operational_guards(by[cid]),
            "folds":[_serialize_fold(f) for f in by[cid]],
        }

        if cid!="C0":
            comp=core.compare(by["C0"],by[cid])
            nrec=null["per_candidate"][cid]
            rec["comparison_vs_c0"]=comp
            rec["null"]=nrec
            rec["survivor"]=bool(
                core.is_survivor(comp,rec["operational_guards"],nrec)
            )

        records[cid]=rec

    ranked=core.rank({
        cid:{
            "comparison":records[cid]["comparison_vs_c0"],
            "null":records[cid]["null"],
            "survivor":records[cid]["survivor"],
        }
        for cid in core.CHALLENGER_IDS
    })

    if ranked:
        status="DEV038A_P2_CONTROLLER_SURVIVOR_FOUND"
        advanced=[ranked[0]]
    else:
        status="DEV038A_P2_NO_CONTROLLER_SURVIVOR_RETAIN_W120"
        advanced=["C0"]

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "project_objective":"personal_investment_profitability_with_auditable_controls",
        "development_only":True,
        "predictive_search_closes_after_this_experiment":True,
        "parents":{
            "dev037_p0_r2":{
                "path":str(R2_ARTIFACT),"sha256":R2_SHA,"bytes":R2_BYTES,
            },
            "dev037_p1_r1":{
                "path":str(DEV037_P1_ARTIFACT),"sha256":DEV037_P1_SHA,"bytes":DEV037_P1_BYTES,
            },
            "dev038a_p1":{
                "path":str(DEV038A_P1_ARTIFACT),"sha256":DEV038A_P1_SHA,"bytes":DEV038A_P1_BYTES,
            },
        },
        "frozen_components":{
            "opportunity_representation":"A0_PRICE32",
            "direction":"BTC45",
            "policy":"S0_TOUCH_ONLY_SELECTIVE",
            "target_quantile":0.80,
            "horizon_seconds":120,
            "barrier_bps":16,
        },
        "controller_ids":list(core.CONTROLLER_IDS),
        "challenger_ids":list(core.CHALLENGER_IDS),
        "window_by_id":{k:int(v) for k,v in core.WINDOW_BY_ID.items()},
        "operational_reproduction":reproduction,
        "controller_records":records,
        "joint_temporal_null":null,
        "survivor_ranking":ranked,
        "advanced_controller":advanced,
        "forward_guards":dict(FORWARD_GUARDS),
        "permanent_stop_rule":{
            "further_controller_search":False,
            "further_quantile_search":False,
            "new_feature_search":False,
            "new_model_family_search":False,
            "meta_filter_rescue":False,
            "target_geometry_tuning":False,
        },
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists():
        raise RunnerError("staging_exists")
    staging.mkdir(parents=True)
    try:
        final=staging/ARTIFACT_FILENAME
        with final.open("xb") as h:
            h.write(content)
            h.flush()
            os.fsync(h.fileno())
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
        "advanced_controller":advanced,
    }

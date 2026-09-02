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
from . import dev037_policy_runner as p1runner
from . import dev037_p0_r1_coverage_core as core

EXPERIMENT_ID="DEV037-P0-R1"
DESIGN_VERSION="adaptive-label-free-coverage-controller-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev037_p0_r1_adaptive_coverage_controller_v1"
)
ARTIFACT_FILENAME="DEV037_P0_R1_ADAPTIVE_COVERAGE_CONTROLLER_RESULT.json"

FORWARD_GUARDS={
    "validation_correctness_inspected":False,
    "action_precision_calculated":False,
    "correct_action_count_calculated":False,
    "false_action_count_calculated":False,
    "temporal_null_run":False,
    "survivor_classification_run":False,
    "pnl_run":False,
    "fees_run":False,
    "slippage_run":False,
    "forward_data_opened":False,
}

class R1RunnerError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

def _sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _fold_score_streams(e,outer):
    oof=p1runner._oof_training_predictions(e,outer)

    # Validation components are generated exactly as in DEV037-P1 lineage,
    # but validation labels are not used here.
    # Touch validation probabilities:
    t2={d:e.per_day[d].t2 for d in dd.HISTORICAL_DAYS}
    from . import dev030_p4_touch_composition as p4
    touch=p4.fit_t2(t2)
    touch_fold=touch.s1_folds[outer.fold_id-1]
    vpt=np.asarray(touch_fold.p_touch,dtype=np.float64)

    direction=p1runner._validation_predictions(e,outer,touch_fold)[1]
    vpl=np.asarray(direction,dtype=np.float64)

    touch_ref=policy.empirical_percentile_reference(oof["p_touch"])
    dir_ref=policy.empirical_percentile_reference(policy.direction_confidence(oof["p_long"]))

    train_scores=policy.score_bundle(
        p_touch=oof["p_touch"],p_long=oof["p_long"],
        touch_reference=touch_ref,dir_reference=dir_ref,
    )
    val_scores=policy.score_bundle(
        p_touch=vpt,p_long=vpl,
        touch_reference=touch_ref,dir_reference=dir_ref,
    )

    xmeta=policy.meta_features(
        p_touch=oof["p_touch"],p_long=oof["p_long"],
        touch_reference=touch_ref,dir_reference=dir_ref,
    )
    ymeta=p1runner._meta_target(oof["y3"],oof["p_long"])
    scaler,model=p1runner._meta_model(xmeta,ymeta)
    train_s5=model.predict_proba(scaler.transform(xmeta))[:,1]
    xval=policy.meta_features(
        p_touch=vpt,p_long=vpl,
        touch_reference=touch_ref,dir_reference=dir_ref,
    )
    val_s5=model.predict_proba(scaler.transform(xval))[:,1]

    train_scores["S5"]=train_s5
    val_scores["S5"]=val_s5

    return {
        "oof":oof,
        "train_scores":train_scores,
        "validation_scores":val_scores,
        "validation_p_long":vpl,
        "validation_rows":int(len(vpl)),
        "meta_positive_count":int(np.sum(ymeta==1)),
        "meta_negative_count":int(np.sum(ymeta==0)),
    }

def _public_result(r:core.ControllerResult):
    t=np.asarray(r.thresholds,dtype=np.float64)
    return {
        "window":int(r.window),
        "coverage":float(r.coverage),
        "action_count":int(r.action_count),
        "abstain_count":int(r.abstain_count),
        "long_count":int(r.long_count),
        "short_count":int(r.short_count),
        "coverage_abs_error":float(r.coverage_abs_error),
        "threshold_summary":{
            "first":float(t[0]),
            "last":float(t[-1]),
            "min":float(np.min(t)),
            "median":float(np.median(t)),
            "max":float(np.max(t)),
        },
        "mean_abs_rolling60_error":float(r.mean_abs_rolling60_error),
        "max_abs_rolling60_error":float(r.max_abs_rolling60_error),
        "rolling60_outside_count":int(r.rolling60_outside_count),
        "action_state_switches":int(r.action_state_switches),
        "warm_start_count":int(r.warm_start_count),
        "operationally_feasible":bool(core.feasible(r)),
    }

def run_r1(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True):
    if any(FORWARD_GUARDS.values()):
        raise R1RunnerError("forbidden_activity_guard")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise R1RunnerError("execution_commit")
    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise R1RunnerError("noncanonical_output")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY:
        raise R1RunnerError("canonical_requires_real")
    if out.exists() or out.is_symlink():
        raise R1RunnerError("output_exists")

    e=c1loader.load_c1()
    records={w:[] for w in core.WINDOWS}
    fold_public=[]

    for outer in dd.OUTER_FOLDS:
        z=_fold_score_streams(e,outer)
        fold_rec={
            "fold_id":int(outer.fold_id),
            "validation_day":outer.validation_day.isoformat(),
            "oof_rows":int(len(z["oof"]["p_touch"])),
            "validation_rows":int(z["validation_rows"]),
            "meta_positive_count":int(z["meta_positive_count"]),
            "meta_negative_count":int(z["meta_negative_count"]),
            "controllers":{},
        }
        for w in core.WINDOWS:
            fold_rec["controllers"][str(w)]={}
            for pid in policy.POLICY_IDS:
                r=core.summarize(
                    scores=z["validation_scores"][pid],
                    p_long=z["validation_p_long"],
                    warm_scores=z["train_scores"][pid],
                    window=w,
                )
                records[w].append(r)
                fold_rec["controllers"][str(w)][pid]=_public_result(r)
        fold_public.append(fold_rec)

    ranked,ranking_stats=core.rank_controllers(records)
    if ranked:
        status="DEV037_P0_R1_ADAPTIVE_CONTROLLER_SELECTED"
        selected=int(ranked[0])
    else:
        status="DEV037_P0_R1_NO_CONTROLLER_OPERATIONALLY_FEASIBLE"
        selected=None

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "parent_dev036_c1":{
            "sha256":"9278e4c1ef8868b77e2c45a3cd4bcf93a87c99a77fcbf925a12842b3731708b4",
            "bytes":98670,
        },
        "policy_ids":list(policy.POLICY_IDS),
        "controller_windows":list(core.WINDOWS),
        "target_quantile":core.TARGET_QUANTILE,
        "target_coverage":core.TARGET_COVERAGE,
        "folds":fold_public,
        "controller_ranking":[int(x) for x in ranked],
        "controller_ranking_stats":{
            str(w):{
                "mean_abs_coverage_error":float(v[0]),
                "worst_abs_coverage_error":float(v[1]),
                "mean_abs_rolling60_error":float(v[2]),
                "rolling60_outside_count":int(v[3]),
                "window":int(v[4]),
            }
            for w,v in ranking_stats.items()
        },
        "selected_controller_window":selected,
        "forward_guards":dict(FORWARD_GUARDS),
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists():
        raise R1RunnerError("staging_exists")
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
        "selected_controller_window":selected,
    }

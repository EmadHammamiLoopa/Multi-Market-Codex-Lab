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
from . import dev037_p0_r1_coverage_core as r1core
from . import dev037_p0_r1_coverage_runner as r1runner

EXPERIMENT_ID="DEV037-P0-R2"
DESIGN_VERSION="operationally-pruned-adaptive-controller-v1"
RETAINED_POLICY_IDS=("S0","S1","S2","S5")
WINDOWS=(120,360,720)

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev037_p0_r2_operationally_pruned_controller_v1"
)
ARTIFACT_FILENAME="DEV037_P0_R2_OPERATIONALLY_PRUNED_CONTROLLER_RESULT.json"

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

class R2Error(RuntimeError):
    pass

def _sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _public(r):
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
            "first":float(t[0]),"last":float(t[-1]),
            "min":float(np.min(t)),"median":float(np.median(t)),"max":float(np.max(t)),
        },
        "mean_abs_rolling60_error":float(r.mean_abs_rolling60_error),
        "max_abs_rolling60_error":float(r.max_abs_rolling60_error),
        "rolling60_outside_count":int(r.rolling60_outside_count),
        "action_state_switches":int(r.action_state_switches),
        "warm_start_count":int(r.warm_start_count),
        "operationally_feasible":bool(r1core.feasible(r)),
    }

def _rank(records):
    feasible=[w for w in WINDOWS if all(r1core.feasible(r) for r in records[w])]
    def stats(w):
        rs=records[w]
        return (
            float(np.mean([r.coverage_abs_error for r in rs])),
            float(np.max([r.coverage_abs_error for r in rs])),
            float(np.mean([r.mean_abs_rolling60_error for r in rs])),
            int(np.sum([r.rolling60_outside_count for r in rs])),
            int(w),
        )
    ranked=sorted(feasible,key=stats)
    return ranked,{w:stats(w) for w in WINDOWS}

def run_r2(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True):
    if any(FORWARD_GUARDS.values()):
        raise R2Error("forbidden_activity_guard")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise R2Error("execution_commit")
    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise R2Error("noncanonical_output")
    if out.exists() or out.is_symlink():
        raise R2Error("output_exists")

    e=c1loader.load_c1()
    records={w:[] for w in WINDOWS}
    folds=[]

    for outer in dd.OUTER_FOLDS:
        z=r1runner._fold_score_streams(e,outer)
        rec={
            "fold_id":int(outer.fold_id),
            "validation_day":outer.validation_day.isoformat(),
            "oof_rows":int(len(z["oof"]["p_touch"])),
            "validation_rows":int(z["validation_rows"]),
            "controllers":{},
        }
        for w in WINDOWS:
            rec["controllers"][str(w)]={}
            for pid in RETAINED_POLICY_IDS:
                r=r1core.summarize(
                    scores=z["validation_scores"][pid],
                    p_long=z["validation_p_long"],
                    warm_scores=z["train_scores"][pid],
                    window=w,
                )
                records[w].append(r)
                rec["controllers"][str(w)][pid]=_public(r)
        folds.append(rec)

    ranked,stats=_rank(records)
    if ranked:
        status="DEV037_P0_R2_CONTROLLER_SELECTED"
        selected=int(ranked[0])
    else:
        status="DEV037_P0_R2_NO_CONTROLLER_OPERATIONALLY_FEASIBLE"
        selected=None

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "retained_policy_ids":list(RETAINED_POLICY_IDS),
        "removed_policy_ids":["S3","S4"],
        "controller_windows":list(WINDOWS),
        "target_quantile":0.80,
        "target_coverage":0.20,
        "folds":folds,
        "controller_ranking":[int(x) for x in ranked],
        "controller_ranking_stats":{
            str(w):{
                "mean_abs_coverage_error":float(v[0]),
                "worst_abs_coverage_error":float(v[1]),
                "mean_abs_rolling60_error":float(v[2]),
                "rolling60_outside_count":int(v[3]),
                "window":int(v[4]),
            } for w,v in stats.items()
        },
        "selected_controller_window":selected,
        "forward_guards":dict(FORWARD_GUARDS),
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
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
        "selected_controller_window":selected,
    }

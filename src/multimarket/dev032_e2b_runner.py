from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any

import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

from . import dev032_e1b_loader as e1loader
from . import dev032_e1b_screen_core as e1
from . import dev032_e2b_loader as loader
from . import dev032_e2b_screen_core as core

EXPERIMENT_ID="DEV032-E2B"
DESIGN_VERSION="wave2-adaptive-parent-relative-screen-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev032_e2b_adaptive_refinement_screen_v1"
)
ARTIFACT_FILENAME="DEV032_E2B_ADAPTIVE_REFINEMENT_SCREEN_RESULT.json"

FORWARD_GUARDS={
    "aug01_opened":False,
    "aug30_opened":False,
    "sep01_or_later_opened":False,
    "railway_opened":False,
    "archive_bucket_opened":False,
    "abundant_love_opened":False,
    "downloads_or_acquisition_run":False,
    "e1a_rerun":False,
    "e1b_rerun":False,
    "e2a_rerun":False,
    "pnl_run":False,
    "threshold_optimization_run":False,
    "calibration_rescue_run":False,
    "class_weight_search_run":False,
    "alternate_model_family_run":False,
    "feature_subset_search_run":False,
    "component_count_tuning_run":False,
}

INCONCLUSIVE_PARENT_IDS=(
    "P21","P35","P13","P02","P14","P07","P32",
    "P09","P06","P05","P08","P04","P17","P20",
)

FAMILY_BY_REFINEMENT={
    "E2R01":"queue_depth_imbalance",
    "E2R02":"queue_depth_imbalance",
    "E2R03":"microprice_fair_value",
    "E2R04":"microprice_fair_value",
    "E2R05":"multilevel_stationary_order_flow",
    "E2R06":"multilevel_stationary_order_flow",
    "E2R07":"book_geometry",
    "E2R08":"event_pressure_transition",
    "E2R09":"temporal_shape",
    "E2R10":"resilience_recovery",
}

class E2BRunnerError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _normalize_workers(v:int)->int:
    try:
        x=int(v)
    except (TypeError,ValueError) as exc:
        raise E2BRunnerError("max_workers_invalid") from exc
    return max(1,min(x,10))

def _fit_parent(evidence:loader.LoadedEvidence,parent_id:str)->e1.RepresentationResult:
    return e1.fit_representation(
        loader.parent_days(evidence,parent_id),
        loader.outer_folds(),
        parent_id,
    )

def _fit_baseline(evidence:loader.LoadedEvidence)->e1.RepresentationResult:
    return e1.fit_representation(loader.baseline_days(evidence),loader.outer_folds(),"B00")

def _fit_refinement_worker(
    rid:str,
    base_days:dict,
    raw_days:dict,
    folds:tuple,
)->core.FitResult:
    spec=core.TransformSpec(
        "pca" if rid=="E2R05" else "svd" if rid=="E2R06" else "ordinary",
        5 if rid in ("E2R05","E2R06") else 0,
    )
    with threadpool_limits(limits=1):
        return core.fit_refinement(base_days,raw_days,folds,rid,spec)

def _frozen_rep_record(e1b:dict[str,Any],rep_id:str)->dict[str,Any]:
    if rep_id=="B00":
        return e1b["baseline"]
    rows=[r for r in e1b["leaderboard"] if r["candidate_id"]==rep_id]
    if len(rows)!=1:
        raise E2BRunnerError("frozen_parent_row_not_unique",rep_id)
    return rows[0]

def _verify_rep_reproduction(
    *,
    rep_id:str,
    current:e1.RepresentationResult,
    frozen:dict[str,Any],
)->dict[str,Any]:
    ff=frozen["folds"]
    if len(ff)!=4 or len(current.folds)!=4:
        raise E2BRunnerError("reproduction_fold_count",rep_id)
    folds=[]
    for got,exp in zip(current.folds,ff,strict=True):
        if int(got.fold_id)!=int(exp["fold_id"]):
            raise E2BRunnerError("reproduction_fold_id",rep_id)
        if got.prediction_sha256!=exp["prediction_sha256"]:
            raise E2BRunnerError("reproduction_prediction_hash",f"{rep_id}:fold{got.fold_id}")
        if float(got.selected_c)!=float(exp["selected_C"]):
            raise E2BRunnerError("reproduction_selected_c",f"{rep_id}:fold{got.fold_id}")
        folds.append({
            "fold_id":int(got.fold_id),
            "selected_C":float(got.selected_c),
            "prediction_sha256":got.prediction_sha256,
            "reproduced":True,
        })
    for metric in ("roc_auc","binary_log_loss","brier"):
        actual=float(current.pooled_metrics[metric])
        expected=float(frozen["pooled_metrics"][metric])
        if not np.isclose(actual,expected,rtol=0.0,atol=1e-15):
            raise E2BRunnerError("reproduction_pooled_metric",f"{rep_id}:{metric}")
    return {"representation":rep_id,"pass":True,"folds":folds}

def _public_rep(result)->dict[str,Any]:
    return {
        "representation":result.representation,
        "feature_count":int(result.feature_count),
        "pooled_metrics":dict(result.pooled_metrics),
        "folds":[
            {
                "fold_id":int(f.fold_id),
                "selected_C":float(f.selected_c),
                "support":int(len(f.labels)),
                "long_count":int(np.sum(f.labels==1)),
                "short_count":int(np.sum(f.labels==0)),
                "metrics":dict(f.metrics),
                "prediction_sha256":f.prediction_sha256,
                "inner_c_ledger":list(f.inner_c_ledger),
            }
            for f in result.folds
        ],
    }

def _leaderboard(
    *,
    b00:e1.RepresentationResult,
    parents:dict[str,e1.RepresentationResult],
    candidates:dict[str,core.FitResult],
    null:dict[str,Any],
)->list[dict[str,Any]]:
    rows=[]
    for rid,cand in candidates.items():
        pid=loader.PARENT_BY_REFINEMENT[rid]
        pcomp=core.compare(parents[pid],cand)
        bcomp=core.compare(b00,cand)
        nrec=null["per_candidate"][rid]
        status=core.classify(cand,pcomp,nrec,float(b00.pooled_metrics["roc_auc"]))
        rows.append({
            "refinement_id":rid,
            "parent_candidate_id":pid,
            "family":FAMILY_BY_REFINEMENT[rid],
            "status":status,
            "feature_count":int(cand.feature_count),
            "pooled_metrics":dict(cand.pooled_metrics),
            "comparison_vs_parent":pcomp,
            "comparison_vs_b00":bcomp,
            "null":dict(nrec),
            "folds":[
                {
                    "fold_id":int(f.fold_id),
                    "selected_C":float(f.selected_c),
                    "metrics":dict(f.metrics),
                    "prediction_sha256":f.prediction_sha256,
                    "inner_c_ledger":list(f.inner_c_ledger),
                }
                for f in cand.folds
            ],
        })
    rank={
        core.STATUS_SURVIVOR:0,
        core.STATUS_INCONCLUSIVE:1,
        core.STATUS_REJECTED:2,
    }
    rows.sort(key=lambda r:(
        rank[r["status"]],
        r["null"]["max_stat_fwer_empirical_p"],
        -r["comparison_vs_parent"]["pooled_auc_delta"],
        -r["comparison_vs_parent"]["worst_fold_auc"],
        r["feature_count"],
        r["refinement_id"],
    ))
    return rows

def run_e2b(
    *,
    execution_commit:str,
    output_directory:Path=REAL_OUTPUT_DIRECTORY,
    require_canonical_output:bool=True,
    max_workers:int=10,
)->dict[str,Any]:
    output=Path(output_directory)
    if require_canonical_output and output!=REAL_OUTPUT_DIRECTORY:
        raise E2BRunnerError("noncanonical_output_directory")
    if not require_canonical_output and output==REAL_OUTPUT_DIRECTORY:
        raise E2BRunnerError("canonical_output_requires_real_mode")
    if output.exists() or output.is_symlink():
        raise E2BRunnerError("output_directory_already_exists")
    if any(FORWARD_GUARDS.values()):
        raise E2BRunnerError("runtime_guard_violation")
    if (
        not isinstance(execution_commit,str)
        or len(execution_commit)!=40
        or any(c not in "0123456789abcdef" for c in execution_commit)
    ):
        raise E2BRunnerError("execution_commit_must_be_full_sha")

    evidence=loader.load_evidence()
    e1b=evidence.e1b_manifest

    frozen_inconclusive=[
        r["candidate_id"] for r in e1b["leaderboard"]
        if r["status"]==e1.STATUS_INCONCLUSIVE
    ]
    if set(frozen_inconclusive)!=set(INCONCLUSIVE_PARENT_IDS) or len(frozen_inconclusive)!=14:
        raise E2BRunnerError("frozen_inconclusive_parent_universe")

    b00=_fit_baseline(evidence)
    reproduction=[
        _verify_rep_reproduction(
            rep_id="B00",current=b00,frozen=_frozen_rep_record(e1b,"B00")
        )
    ]

    parents={}
    for pid in loader.ACTIVE_PARENT_IDS:
        current=_fit_parent(evidence,pid)
        parents[pid]=current
        reproduction.append(
            _verify_rep_reproduction(
                rep_id=pid,current=current,frozen=_frozen_rep_record(e1b,pid)
            )
        )

    base_days=loader.baseline_days(evidence)
    folds=loader.outer_folds()
    workers=_normalize_workers(max_workers)

    raw_days={rid:loader.refinement_raw_days(evidence,rid) for rid in loader.REFINEMENT_IDS}
    candidates={}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        fs={
            rid:pool.submit(_fit_refinement_worker,rid,base_days,raw_days[rid],folds)
            for rid in loader.REFINEMENT_IDS
        }
        for rid in loader.REFINEMENT_IDS:
            candidates[rid]=fs[rid].result()

    null=core.parent_relative_max_stat_null(
        parents,candidates,loader.PARENT_BY_REFINEMENT,
        seed=core.NULL_SEED,replicates=core.NULL_REPLICATES,
    )
    leaderboard=_leaderboard(b00=b00,parents=parents,candidates=candidates,null=null)

    survivors=[r for r in leaderboard if r["status"]==core.STATUS_SURVIVOR]
    advanced=[]
    seen=set()
    for row in survivors:
        fam=row["family"]
        if fam in seen: continue
        advanced.append(row["refinement_id"]);seen.add(fam)
        if len(advanced)==3: break

    frozen_anchor_rows=[
        r for r in e1b["leaderboard"]
        if r["candidate_id"] in INCONCLUSIVE_PARENT_IDS
    ]

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "environment":{
            "python":sys.version.split()[0],
            "numpy":np.__version__,
            "scikit_learn":sklearn.__version__,
            "max_workers":workers,
            "inner_threads_per_worker":1,
        },
        "parent_e2a":{
            "path":str(loader.E2A_ARTIFACT),
            "sha256":loader.E2A_SHA256,
            "bytes":loader.E2A_BYTES,
        },
        "parent_e1b":{
            "path":str(loader.E1B_ARTIFACT),
            "sha256":loader.E1B_SHA256,
            "bytes":loader.E1B_BYTES,
        },
        "reproduction_gate":{
            "pass":True,
            "representations":reproduction,
        },
        "frozen_inconclusive_parent_anchors":frozen_anchor_rows,
        "baseline":_public_rep(b00),
        "active_parents":{pid:_public_rep(parents[pid]) for pid in loader.ACTIVE_PARENT_IDS},
        "refinement_ids":list(loader.REFINEMENT_IDS),
        "refinement_count":len(loader.REFINEMENT_IDS),
        "parent_by_refinement":dict(loader.PARENT_BY_REFINEMENT),
        "null":{
            "seed":null["seed"],
            "replicates":null["replicates"],
            "candidate_ids":null["candidate_ids"],
            "fold_sizes":null["fold_sizes"],
            "max_stat_q95":null["max_stat_q95"],
            "per_candidate":null["per_candidate"],
            "max_stat_null":null["max_stat_null"],
            "shift_tuples":null["shift_tuples"],
        },
        "leaderboard":leaderboard,
        "adaptive_refinement_survivors":[r["refinement_id"] for r in survivors],
        "advanced_mechanisms":advanced,
        "forward_guards":dict(FORWARD_GUARDS),
        "interpretation":(
            "adaptive BTC Jan-Jul Wave-2 parent-relative refinement screen on reused "
            "development data; even a survivor requires independent historical replication "
            "before any Sep-01+ forward confirmation or economic evaluation"
        ),
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode("utf-8")
    staging=output.parent/f".{output.name}.part-{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise E2BRunnerError("staging_directory_preexists")
    staging.mkdir(parents=True)
    try:
        p=staging/ARTIFACT_FILENAME
        with p.open("xb") as f:
            f.write(content);f.flush();os.fsync(f.fileno())
        os.replace(staging,output)
    except BaseException:
        if staging.exists(): shutil.rmtree(staging,ignore_errors=True)
        raise

    final=output/ARTIFACT_FILENAME
    return {
        "artifact_path":str(final),
        "artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),
        "adaptive_refinement_survivors":[r["refinement_id"] for r in survivors],
        "advanced_mechanisms":advanced,
    }

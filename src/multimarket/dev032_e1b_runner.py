from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
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

from . import dev031_p1b_event_depth_incremental as p1b
from . import dev032_e1b_loader as loader
from . import dev032_e1b_screen_core as core

EXPERIMENT_ID="DEV032-E1B"
DESIGN_VERSION="broad-predictive-screen-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev032_e1b_broad_predictive_screen_v1"
)
ARTIFACT_FILENAME="DEV032_E1B_BROAD_PREDICTIVE_SCREEN_RESULT.json"

FORWARD_GUARDS={
    "aug01_opened":False,
    "aug30_opened":False,
    "sep01_or_later_opened":False,
    "railway_opened":False,
    "archive_bucket_opened":False,
    "abundant_love_opened":False,
    "downloads_or_acquisition_run":False,
    "raw_e1a_rematerialization_run":False,
    "pnl_run":False,
    "threshold_optimization_run":False,
    "calibration_rescue_run":False,
    "feature_subset_search_run":False,
    "alternate_model_family_run":False,
}

class E1BRunnerError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None)->None:
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def _fit_rep(
    evidence:loader.LoadedEvidence,
    representation:str,
)->core.RepresentationResult:
    folds=loader.outer_folds()
    if representation=="B00":
        days=loader.baseline_days(evidence)
    else:
        days=loader.primary_candidate_days(evidence,representation)
    with threadpool_limits(limits=1):
        return core.fit_representation(days,folds,representation)

def _public_rep(result:core.RepresentationResult)->dict[str,Any]:
    return {
        "representation":result.representation,
        "feature_count":result.feature_count,
        "pooled_metrics":dict(result.pooled_metrics),
        "folds":[
            {
                "fold_id":f.fold_id,
                "selected_C":f.selected_c,
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

def _verify_p1b_reproduction(
    evidence:loader.LoadedEvidence,
    b00:core.RepresentationResult,
    p02:core.RepresentationResult,
)->dict[str,Any]:
    frozen=evidence.p1b_manifest
    out=[]
    for rep_name,current,frozen_key in (
        ("C0",b00,"c0"),
        ("C1",p02,"c1"),
    ):
        ff=frozen[frozen_key]["folds"]
        if len(ff)!=4:
            raise E1BRunnerError("p1b_fold_count",rep_name)
        for got,expected in zip(current.folds,ff,strict=True):
            actual=p1b.prediction_sha256(
                got.fold_id,
                rep_name,
                got.timestamps_us,
                got.labels,
                got.probabilities,
            )
            if actual!=expected["prediction_sha256"]:
                raise E1BRunnerError(
                    "p1b_prediction_reproduction",
                    f"{rep_name}:fold{got.fold_id}",
                )
            if abs(float(got.selected_c)-float(expected["selected_C"]))>0.0:
                raise E1BRunnerError(
                    "p1b_selected_c_reproduction",
                    f"{rep_name}:fold{got.fold_id}",
                )
            out.append({
                "representation":rep_name,
                "fold_id":got.fold_id,
                "prediction_sha256":actual,
                "reproduced":True,
            })

    for rep_name,current,frozen_key in (
        ("C0",b00,"c0"),
        ("C1",p02,"c1"),
    ):
        expected=frozen[frozen_key]["pooled"]
        for metric in ("roc_auc","binary_log_loss","brier"):
            if not np.isclose(
                float(current.pooled_metrics[metric]),
                float(expected[metric]),
                rtol=0.0,
                atol=1e-15,
            ):
                raise E1BRunnerError(
                    "p1b_pooled_metric_reproduction",
                    f"{rep_name}:{metric}",
                )
    return {"pass":True,"folds":out}

def _verify_p3_reproduction()->dict[str,Any]:
    _manifest,days=p1b.load_days()
    result=p1b.reproduce_p3(days)
    if result.get("pass") is not True:
        raise E1BRunnerError("p3_reproduction_failed")
    return result

def run_e1b(
    *,
    execution_commit:str,
    output_directory:Path=REAL_OUTPUT_DIRECTORY,
    require_canonical_output:bool=True,
    max_workers:int=20,
)->dict[str,Any]:
    output=Path(output_directory)
    if require_canonical_output and output!=REAL_OUTPUT_DIRECTORY:
        raise E1BRunnerError("noncanonical_output_directory")
    if not require_canonical_output and output==REAL_OUTPUT_DIRECTORY:
        raise E1BRunnerError("canonical_output_requires_real_mode")
    if output.exists() or output.is_symlink():
        raise E1BRunnerError("output_directory_already_exists")
    if any(FORWARD_GUARDS.values()):
        raise E1BRunnerError("runtime_guard_violation")
    if (
        not isinstance(execution_commit,str)
        or len(execution_commit)!=40
        or any(ch not in "0123456789abcdef" for ch in execution_commit)
    ):
        raise E1BRunnerError("execution_commit_must_be_full_sha")

    evidence=loader.load_evidence()
    p3_reproduction=_verify_p3_reproduction()

    b00=_fit_rep(evidence,"B00")
    p02=_fit_rep(evidence,"P02")
    p1b_reproduction=_verify_p1b_reproduction(evidence,b00,p02)

    ids=loader.PRIMARY_IDS
    workers=max(1,min(int(max_workers),20))
    candidates:dict[str,core.RepresentationResult]={"P02":p02}

    remaining=[sid for sid in ids if sid!="P02"]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={sid:pool.submit(_fit_rep,evidence,sid) for sid in remaining}
        for sid in remaining:
            candidates[sid]=futures[sid].result()

    # Restore deterministic preregistered order regardless of completion order.
    candidates={sid:candidates[sid] for sid in ids}

    null=core.temporal_max_stat_null(
        b00,
        candidates,
        seed=core.NULL_SEED,
        replicates=core.NULL_REPLICATES,
    )
    legacy=core.legacy_common_shift_audit(b00,candidates)
    leaderboard=core.leaderboard_rows(
        b00,
        candidates,
        null,
        family_by_candidate=loader.FAMILY_BY_PRIMARY,
    )

    strong=[x for x in leaderboard if x["status"]==core.STATUS_STRONG]
    advanced=[]
    seen_families=set()
    for row in strong:
        family=row["family"]
        if family in seen_families:
            continue
        advanced.append(row["candidate_id"])
        seen_families.add(family)
        if len(advanced)==3:
            break

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
        "parent_e1a":{
            "path":str(loader.E1A_ARTIFACT),
            "sha256":loader.E1A_SHA256,
            "bytes":loader.E1A_BYTES,
        },
        "parent_p1b":{
            "path":str(loader.P1B_ARTIFACT),
            "sha256":loader.P1B_SHA256,
            "bytes":loader.P1B_BYTES,
            "terminal_status":"FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE",
        },
        "p3_reproduction":p3_reproduction,
        "p1b_reproduction":p1b_reproduction,
        "baseline":_public_rep(b00),
        "primary_candidate_ids":list(ids),
        "primary_candidate_count":len(ids),
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
        "legacy_common_shift_audit":legacy,
        "leaderboard":leaderboard,
        "strong_screening_survivors":[
            row["candidate_id"] for row in strong
        ],
        "advanced_mechanisms":advanced,
        "forward_guards":dict(FORWARD_GUARDS),
        "interpretation":(
            "development-only BTC Jan-Jul broad ranking screen; any survivor "
            "remains exploratory and requires independent historical replication "
            "before any Sep-01+ forward confirmation"
        ),
    }

    content=(
        json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)
        +"\n"
    ).encode("utf-8")

    staging=output.parent/f".{output.name}.part-{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise E1BRunnerError("staging_directory_preexists")
    staging.mkdir(parents=True)
    try:
        artifact=staging/ARTIFACT_FILENAME
        with artifact.open("xb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(staging,output)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging,ignore_errors=True)
        raise

    final=output/ARTIFACT_FILENAME
    return {
        "artifact_path":str(final),
        "artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),
        "strong_screening_survivors":[
            row["candidate_id"] for row in strong
        ],
        "advanced_mechanisms":advanced,
    }

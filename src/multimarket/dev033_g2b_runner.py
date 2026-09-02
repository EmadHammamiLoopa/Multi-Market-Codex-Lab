from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any

import numpy as np
from threadpoolctl import threadpool_limits

from . import dev030_direction_dataset as dd
from . import dev030_p6_m2_direction as p6
from . import dev033_g2a_materialize as g2a
from . import dev033_g2b_core as core
from . import dev033_g2b_loader as loader

EXPERIMENT_ID="DEV033-G2B"
DESIGN_VERSION="layered-temporal-incremental-screen-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev033_g2b_layered_temporal_screen_v1"
)
ARTIFACT_FILENAME="DEV033_G2B_LAYERED_TEMPORAL_SCREEN_RESULT.json"

FORWARD_GUARDS={
    "aug01_new_analysis_opened":False,
    "aug30_new_analysis_opened":False,
    "sep01_or_later_opened":False,
    "railway_opened":False,
    "archive_bucket_opened":False,
    "abundant_love_opened":False,
    "downloads_or_acquisition_run":False,
    "pnl_run":False,
    "threshold_optimization_run":False,
    "calibration_rescue_run":False,
    "feature_subset_search_run":False,
    "alternate_model_family_search_run":False,
}

FAMILY_BY_CANDIDATE={
    r["candidate_id"]:r["family_id"] for r in g2a.REGISTRY
}

class G2BRunnerError(RuntimeError):
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
    try:x=int(v)
    except Exception as exc: raise G2BRunnerError("max_workers_invalid") from exc
    return max(1,min(x,12))

def _base_reproduction(e:loader.LoadedG2B):
    try:
        m1=p6.reconstruct_frozen_m1(e.p3_per_day)
    except p6.P6Error as exc:
        raise G2BRunnerError("p3_reproduction_failed",f"{exc.reason}: {exc}") from exc
    if tuple(f.support for f in m1.folds)!=(159,64,126,224):
        raise G2BRunnerError("p3_fold_support")
    expected_c={1:10.0,2:10.0,3:0.1,4:0.01}
    expected_h={
        1:"e03d233bff936b49a0452994497f32ca5ecbe52c1f490d855fe8d06dbfa9dcf4",
        2:"cd2cba0a6dcf3591ec9848b78e31aef796dad15d371bbecb8517aa2507340bdd",
        3:"19f9acf70b0065a307c0373952cad350339768607a156c9307e5192503bb1f31",
        4:"b05ee6e926d6a943e1fc89828eb3801af0863fa270bc2e5db5ed7cd93e9a4b66",
    }
    for f in m1.folds:
        if f.prediction_sha256!=expected_h[f.fold_id]:
            raise G2BRunnerError("p3_prediction_hash",str(f.fold_id))
    # p6 reconstruction already enforces C via p4 reproduction; retain explicit public contract.
    if not np.isclose(
        float(m1.pooled_metrics["balanced_accuracy_at_0_5"]),
        0.5419424831488764,rtol=0.0,atol=5e-10,
    ):
        raise G2BRunnerError("p3_pooled_ba")
    return m1,expected_c,expected_h

def _candidate_per_day(e:loader.LoadedG2B,cid:str):
    return {
        d:loader.candidate_day_matrix(e,d,cid)
        for d in dd.HISTORICAL_DAYS
    }

def _fit_worker(cid,per_day):
    with threadpool_limits(limits=1):
        return core.fit_candidate(cid,per_day)

def _candidate_public(c:core.CandidateResult):
    return {
        "candidate_id":c.candidate_id,
        "feature_count":int(c.feature_count),
        "pooled_metrics":dict(c.pooled_metrics),
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
            for f in c.folds
        ],
    }

def _base_public(m1,expected_c,expected_h):
    return {
        "experiment_id":"DEV030-P3",
        "configuration":"A/120s/16bp/32s/PRICE/S1",
        "feature_count":23,
        "pooled_metrics":dict(m1.pooled_metrics),
        "folds":[
            {
                "fold_id":int(f.fold_id),
                "support":int(f.support),
                "selected_C":float(expected_c[f.fold_id]),
                "prediction_sha256":expected_h[f.fold_id],
                "metrics":dict(f.metrics),
                "support_sha256":f.support_sha256,
                "label_sha256":f.label_sha256,
            }
            for f in m1.folds
        ],
    }

def _validate_null_completeness(null):
    if null["replicates"]!=1999: raise G2BRunnerError("null_replicates")
    if null["candidate_ids"]!=list(g2a.CANDIDATE_IDS): raise G2BRunnerError("null_candidate_order")
    if len(null["shift_tuples"])!=1999: raise G2BRunnerError("null_shift_tuple_count")
    if len(null["max_stat_null"])!=1999: raise G2BRunnerError("null_maxstat_count")
    if tuple(null["candidate_null_vectors"])!=g2a.CANDIDATE_IDS:
        raise G2BRunnerError("null_candidate_vector_membership")
    for cid in g2a.CANDIDATE_IDS:
        if len(null["candidate_null_vectors"][cid])!=1999:
            raise G2BRunnerError("null_candidate_vector_length",cid)
    if tuple(null["per_candidate"])!=g2a.CANDIDATE_IDS:
        raise G2BRunnerError("null_summary_membership")

def _rank_rows(rows):
    rank={core.STATUS_SURVIVOR:0,core.STATUS_INCONCLUSIVE:1,core.STATUS_REJECTED:2}
    return sorted(rows,key=lambda r:(
        rank[r["status"]],
        float(r["null"]["max_stat_fwer_empirical_p"]),
        -float(r["comparison_vs_p3"]["minimum_fold_delta_balanced_accuracy"]),
        -float(r["comparison_vs_p3"]["median_fold_delta_balanced_accuracy"]),
        -float(r["comparison_vs_p3"]["pooled_delta_balanced_accuracy"]),
        int(g2a.BY_ID[r["candidate_id"]]["window_seconds"]),
        r["candidate_id"],
    ))

def run_g2b(
    *,
    execution_commit:str,
    output_directory:Path=REAL_OUTPUT_DIRECTORY,
    require_canonical_output:bool=True,
    max_workers:int=12,
):
    if any(FORWARD_GUARDS.values()):
        raise G2BRunnerError("runtime_guard_violation")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise G2BRunnerError("execution_commit")
    output=Path(output_directory)
    if require_canonical_output and output!=REAL_OUTPUT_DIRECTORY:
        raise G2BRunnerError("noncanonical_output_directory")
    if not require_canonical_output and output==REAL_OUTPUT_DIRECTORY:
        raise G2BRunnerError("canonical_output_requires_real_mode")
    if output.exists() or output.is_symlink():
        raise G2BRunnerError("output_directory_already_exists")

    e=loader.load_g2b()
    m1,expected_c,expected_h=_base_reproduction(e)

    per={cid:_candidate_per_day(e,cid) for cid in g2a.CANDIDATE_IDS}
    workers=_normalize_workers(max_workers)
    candidates={}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        fs={cid:pool.submit(_fit_worker,cid,per[cid]) for cid in g2a.CANDIDATE_IDS}
        for cid in g2a.CANDIDATE_IDS:
            candidates[cid]=fs[cid].result()

    comparisons={
        cid:core.compare(m1.folds,candidates[cid])
        for cid in g2a.CANDIDATE_IDS
    }

    null=core.joint_max_stat_null(
        m1.folds,candidates,seed=core.NULL_SEED,replicates=core.NULL_REPLICATES
    )
    _validate_null_completeness(null)

    rows=[]
    for cid in g2a.CANDIDATE_IDS:
        nrec=null["per_candidate"][cid]
        status=core.classify(candidates[cid],comparisons[cid],nrec)
        rows.append({
            "candidate_id":cid,
            "family_id":FAMILY_BY_CANDIDATE[cid],
            "window_seconds":int(g2a.BY_ID[cid]["window_seconds"]),
            "status":status,
            "comparison_vs_p3":comparisons[cid],
            "null":dict(nrec),
            **_candidate_public(candidates[cid]),
        })
    leaderboard=_rank_rows(rows)
    survivors=[r for r in leaderboard if r["status"]==core.STATUS_SURVIVOR]

    advanced=[]
    used=set()
    for row in survivors:
        fam=row["family_id"]
        if fam in used: continue
        advanced.append(row["candidate_id"]);used.add(fam)
        if len(advanced)==3: break

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "parent_g2a":{
            "path":str(loader.G2A_ARTIFACT),
            "sha256":loader.G2A_SHA256,
            "bytes":loader.G2A_BYTES,
        },
        "parent_p3":{
            "path":str(loader.P3_ARTIFACT),
            "sha256":loader.P3_SHA256,
        },
        "p3_reproduction_gate":{
            "pass":True,
            "base":_base_public(m1,expected_c,expected_h),
        },
        "candidate_count":24,
        "candidate_ids":list(g2a.CANDIDATE_IDS),
        "candidate_registry":g2a.public_registry(),
        "null":null,
        "leaderboard":leaderboard,
        "layer_survivors":[r["candidate_id"] for r in survivors],
        "advanced_layers":advanced,
        "forward_guards":dict(FORWARD_GUARDS),
        "interpretation":(
            "all 24 frozen G2 temporal additions were tested as incremental layers "
            "on the frozen DEV030-P3 direction success under the permanent layered "
            "search governance; only G2_LAYER_SURVIVOR may alter the base"
        ),
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=output.parent/f".{output.name}.part-{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise G2BRunnerError("staging_preexists")
    staging.mkdir(parents=True)
    try:
        p=staging/ARTIFACT_FILENAME
        with p.open("xb") as h:
            h.write(content);h.flush();os.fsync(h.fileno())
        os.replace(staging,output)
    except BaseException:
        if staging.exists():shutil.rmtree(staging,ignore_errors=True)
        raise
    final=output/ARTIFACT_FILENAME
    return {
        "artifact_path":str(final),
        "artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),
        "layer_survivors":[r["candidate_id"] for r in survivors],
        "advanced_layers":advanced,
    }

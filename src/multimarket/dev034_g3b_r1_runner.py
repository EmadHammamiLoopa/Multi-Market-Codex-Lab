from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np
from threadpoolctl import threadpool_limits

from . import dev030_direction_dataset as dd
from . import dev034_g3a_core as g3
from . import dev034_g3b_r1_core as core
from . import dev034_g3b_r1_loader as loader

EXPERIMENT_ID="DEV034-G3B-R1"
DESIGN_VERSION="matched-common-support-volatility-context-screen-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev034_g3b_r1_common_support_screen_v1"
)
ARTIFACT_FILENAME="DEV034_G3B_R1_COMMON_SUPPORT_SCREEN_RESULT.json"

FORWARD_GUARDS={
    "aug01_new_analysis_opened":False,
    "aug30_reused":False,
    "sep01_or_later_opened":False,
    "railway_opened":False,
    "archive_bucket_opened":False,
    "abundant_love_opened":False,
    "downloads_or_acquisition_run":False,
    "pnl_run":False,
    "threshold_optimization_run":False,
    "calibration_rescue_run":False,
    "feature_subset_search_run":False,
    "pca_svd_run":False,
    "interaction_expansion_run":False,
    "alternate_model_family_search_run":False,
    "candidate_specific_support_shrink":False,
}

EXPECTED_DAY_COUNTS={
    "2026-01-01":(4,3,1),
    "2026-02-01":(422,200,222),
    "2026-03-01":(356,160,196),
    "2026-04-01":(156,85,71),
    "2026-05-01":(64,40,24),
    "2026-06-01":(121,55,66),
    "2026-07-01":(218,122,96),
}
EXPECTED_VALIDATION_COUNTS={
    1:(156,85,71),
    2:(64,40,24),
    3:(121,55,66),
    4:(218,122,96),
}

class G3BR1RunnerError(RuntimeError):
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
    except Exception as exc:
        raise G3BR1RunnerError("max_workers_invalid") from exc
    return max(1,min(x,12))

def _per_day_base(e):
    return {d:loader.base_day_matrix(e,d) for d in dd.HISTORICAL_DAYS}

def _per_day_candidate(e,cid):
    return {d:loader.candidate_day_matrix(e,d,cid) for d in dd.HISTORICAL_DAYS}

def _fit_worker(cid,per_day):
    with threadpool_limits(limits=1):
        return core.fit_candidate(cid,per_day)

def _validate_support_contract(per_day):
    for d in dd.HISTORICAL_DAYS:
        x,y,ts=per_day[d]
        n,l,s=EXPECTED_DAY_COUNTS[d.isoformat()]
        if (len(y),int(np.sum(y==1)),int(np.sum(y==0)))!=(n,l,s):
            raise G3BR1RunnerError("day_support_contract",d.isoformat())
        if len(ts)!=n or x.shape[0]!=n:
            raise G3BR1RunnerError("day_shape_contract",d.isoformat())
    pooled=np.concatenate([per_day[d][1] for d in dd.HISTORICAL_DAYS])
    if (len(pooled),int(np.sum(pooled==1)),int(np.sum(pooled==0)))!=(1341,665,676):
        raise G3BR1RunnerError("campaign_support_contract")

def _validate_fitted_support(c):
    if len(c.folds)!=4:
        raise G3BR1RunnerError("fit_fold_count",c.candidate_id)
    pooled=[]
    for f in c.folds:
        expected=EXPECTED_VALIDATION_COUNTS[f.fold_id]
        got=(len(f.labels),int(np.sum(f.labels==1)),int(np.sum(f.labels==0)))
        if got!=expected:
            raise G3BR1RunnerError("validation_support_contract",f"{c.candidate_id}:{f.fold_id}:{got}")
        pooled.append(f.labels)
    y=np.concatenate(pooled)
    if (len(y),int(np.sum(y==1)),int(np.sum(y==0)))!=(559,302,257):
        raise G3BR1RunnerError("pooled_validation_contract",c.candidate_id)

def _public_result(c):
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

def _validate_null_completeness(null):
    if null["replicates"]!=1999:
        raise G3BR1RunnerError("null_replicates")
    if null["candidate_ids"]!=list(g3.CANDIDATE_IDS):
        raise G3BR1RunnerError("null_candidate_order")
    if len(null["shift_tuples"])!=1999 or len(null["max_stat_null"])!=1999:
        raise G3BR1RunnerError("null_length")
    if tuple(null["candidate_null_vectors"])!=g3.CANDIDATE_IDS:
        raise G3BR1RunnerError("null_candidate_vector_membership")
    if tuple(null["per_candidate"])!=g3.CANDIDATE_IDS:
        raise G3BR1RunnerError("null_summary_membership")
    for cid in g3.CANDIDATE_IDS:
        if len(null["candidate_null_vectors"][cid])!=1999:
            raise G3BR1RunnerError("null_candidate_vector_length",cid)

def _rank_survivors(rows):
    survivors=[r for r in rows if r["status"]==core.STATUS_SURVIVOR]
    return sorted(survivors,key=lambda r:(
        float(r["null"]["max_stat_fwer_empirical_p"]),
        -float(r["comparison_vs_common_p3"]["minimum_fold_delta_balanced_accuracy"]),
        -float(r["comparison_vs_common_p3"]["median_fold_delta_balanced_accuracy"]),
        -float(r["comparison_vs_common_p3"]["pooled_delta_balanced_accuracy"]),
        int(g3.BY_ID[r["candidate_id"]]["feature_count"]),
        r["candidate_id"],
    ))

def run_g3b_r1(
    *,
    execution_commit:str,
    output_directory:Path=REAL_OUTPUT_DIRECTORY,
    require_canonical_output:bool=True,
    max_workers:int=12,
):
    if any(FORWARD_GUARDS.values()):
        raise G3BR1RunnerError("runtime_guard_violation")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise G3BR1RunnerError("execution_commit")
    output=Path(output_directory)
    if require_canonical_output and output!=REAL_OUTPUT_DIRECTORY:
        raise G3BR1RunnerError("noncanonical_output_directory")
    if not require_canonical_output and output==REAL_OUTPUT_DIRECTORY:
        raise G3BR1RunnerError("canonical_output_requires_real_mode")
    if output.exists() or output.is_symlink():
        raise G3BR1RunnerError("output_directory_already_exists")

    e=loader.load_g3b_r1()

    base_per=_per_day_base(e)
    _validate_support_contract(base_per)
    base=core.fit_candidate("P3_COMMON_SUPPORT_REFIT",base_per)
    _validate_fitted_support(base)
    if int(base.feature_count)!=23:
        raise G3BR1RunnerError("base_feature_count")

    candidates={}
    workers=_normalize_workers(max_workers)
    per={cid:_per_day_candidate(e,cid) for cid in g3.CANDIDATE_IDS}
    for cid in g3.CANDIDATE_IDS:
        _validate_support_contract(per[cid])
        expected=23+int(g3.BY_ID[cid]["feature_count"])
        if any(x.shape[1]!=expected for x,_,_ in per[cid].values()):
            raise G3BR1RunnerError("candidate_width_contract",cid)

    with ProcessPoolExecutor(max_workers=workers) as pool:
        fs={cid:pool.submit(_fit_worker,cid,per[cid]) for cid in g3.CANDIDATE_IDS}
        for cid in g3.CANDIDATE_IDS:
            candidates[cid]=fs[cid].result()
            _validate_fitted_support(candidates[cid])

    comparisons={cid:core.compare(base,candidates[cid]) for cid in g3.CANDIDATE_IDS}
    null=core.joint_max_stat_null(
        base,candidates,seed=core.NULL_SEED,replicates=core.NULL_REPLICATES
    )
    _validate_null_completeness(null)

    rows=[]
    for cid in g3.CANDIDATE_IDS:
        nrec=null["per_candidate"][cid]
        status=core.classify(candidates[cid],comparisons[cid],nrec)
        rows.append({
            "candidate_id":cid,
            "name":g3.BY_ID[cid]["name"],
            "added_feature_count":int(g3.BY_ID[cid]["feature_count"]),
            "status":status,
            "comparison_vs_common_p3":comparisons[cid],
            "null":dict(nrec),
            **_public_result(candidates[cid]),
        })

    ranked=_rank_survivors(rows)
    advanced=[r["candidate_id"] for r in ranked[:3]]

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "parent_p3":{
            "path":str(loader.P3_ARTIFACT),
            "sha256":loader.P3_SHA256,
        },
        "parent_g3a_r1":{
            "path":str(loader.G3A_R1_ARTIFACT),
            "sha256":loader.G3A_R1_SHA256,
            "bytes":loader.G3A_R1_BYTES,
        },
        "common_support":{
            "rows":1341,
            "long":665,
            "short":676,
            "support_sha256":loader.EXPECTED_SUPPORT_SHA,
            "label_sha256":loader.EXPECTED_LABEL_SHA,
            "full_r_sha256":loader.EXPECTED_FULL_R_SHA,
        },
        "pooled_outer_validation":{
            "rows":559,
            "long":302,
            "short":257,
        },
        "base_comparator":{
            "identity":"P3_COMMON_SUPPORT_REFIT",
            "upstream_lineage":"DEV030-P3 A/120s/16bp/32s/PRICE/S1",
            **_public_result(base),
        },
        "candidate_count":16,
        "candidate_ids":list(g3.CANDIDATE_IDS),
        "candidate_registry":g3.public_registry(),
        "null":null,
        "leaderboard":rows,
        "layer_survivors":[r["candidate_id"] for r in rows if r["status"]==core.STATUS_SURVIVOR],
        "advanced_layers":advanced,
        "forward_guards":dict(FORWARD_GUARDS),
        "interpretation":(
            "all 16 frozen G3 opportunity/volatility context blocks were tested "
            "against a support-matched P3 PRICE32/S1 refit comparator on the exact "
            "frozen DEV034-G3A-R1 common support"
        ),
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=output.parent/f".{output.name}.part-{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise G3BR1RunnerError("staging_preexists")
    staging.mkdir(parents=True)
    try:
        p=staging/ARTIFACT_FILENAME
        with p.open("xb") as h:
            h.write(content);h.flush();os.fsync(h.fileno())
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
        "layer_survivors":payload["layer_survivors"],
        "advanced_layers":advanced,
    }

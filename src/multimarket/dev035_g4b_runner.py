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
from . import dev035_g4b_core as core
from . import dev035_g4b_loader as loader

EXPERIMENT_ID="DEV035-G4B"
DESIGN_VERSION="eth-cross-asset-microstructure-incremental-screen-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev035_g4b_eth_cross_asset_screen_v1"
)
ARTIFACT_FILENAME="DEV035_G4B_ETH_CROSS_ASSET_SCREEN_RESULT.json"

FORWARD_GUARDS={
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
    "interaction_search_run":False,
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

class G4BRunnerError(RuntimeError):
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
    except Exception as exc:raise G4BRunnerError("max_workers_invalid") from exc
    return max(1,min(x,8))

def _fit_worker(cid,per_day):
    with threadpool_limits(limits=1):
        return core.fit_candidate(cid,per_day)

def _validate_support_contract(per_day):
    for d in dd.HISTORICAL_DAYS:
        x,y,ts=per_day[d]
        n,l,s=EXPECTED_DAY_COUNTS[d.isoformat()]
        if (len(y),int(np.sum(y==1)),int(np.sum(y==0)))!=(n,l,s):
            raise G4BRunnerError("day_support_contract",d.isoformat())
        if x.shape[0]!=n or len(ts)!=n:
            raise G4BRunnerError("day_shape_contract",d.isoformat())
    y=np.concatenate([per_day[d][1] for d in dd.HISTORICAL_DAYS])
    if (len(y),int(np.sum(y==1)),int(np.sum(y==0)))!=(1341,665,676):
        raise G4BRunnerError("campaign_support_contract")

def _validate_fitted_support(c):
    if len(c.folds)!=4:
        raise G4BRunnerError("fit_fold_count",c.candidate_id)
    pooled=[]
    for f in c.folds:
        got=(len(f.labels),int(np.sum(f.labels==1)),int(np.sum(f.labels==0)))
        if got!=EXPECTED_VALIDATION_COUNTS[f.fold_id]:
            raise G4BRunnerError("validation_support_contract",f"{c.candidate_id}:{f.fold_id}:{got}")
        pooled.append(f.labels)
    y=np.concatenate(pooled)
    if (len(y),int(np.sum(y==1)),int(np.sum(y==0)))!=(559,302,257):
        raise G4BRunnerError("pooled_validation_contract",c.candidate_id)

def _public_result(c,*,include_validation_rows:bool=False):
    folds=[]
    for f in c.folds:
        rec={
            "fold_id":int(f.fold_id),
            "selected_C":float(f.selected_c),
            "support":int(len(f.labels)),
            "long_count":int(np.sum(f.labels==1)),
            "short_count":int(np.sum(f.labels==0)),
            "metrics":dict(f.metrics),
            "prediction_sha256":f.prediction_sha256,
            "inner_c_ledger":list(f.inner_c_ledger),
        }
        if include_validation_rows:
            rec["validation_timestamps_us"]=[int(v) for v in f.timestamps_us.tolist()]
            rec["validation_labels"]=[int(v) for v in f.labels.tolist()]
        folds.append(rec)
    return {
        "candidate_id":c.candidate_id,
        "feature_count":int(c.feature_count),
        "pooled_metrics":dict(c.pooled_metrics),
        "folds":folds,
    }

def _rank_survivors(rows):
    survivors=[r for r in rows if r["status"]==core.STATUS_SURVIVOR]
    return sorted(survivors,key=lambda r:(
        float(r["null"]["max_stat_fwer_empirical_p"]),
        -float(r["comparison_vs_btc45"]["minimum_fold_delta_balanced_accuracy"]),
        -float(r["comparison_vs_btc45"]["median_fold_delta_balanced_accuracy"]),
        -float(r["comparison_vs_btc45"]["pooled_delta_balanced_accuracy"]),
        int(r["added_feature_count"]),
        r["candidate_id"],
    ))

def _validate_null_completeness(null):
    if null["replicates"]!=1999:raise G4BRunnerError("null_replicates")
    if tuple(null["candidate_ids"])!=core.CANDIDATE_IDS:raise G4BRunnerError("null_candidate_order")
    if len(null["shift_tuples"])!=1999 or len(null["max_stat_null"])!=1999:
        raise G4BRunnerError("null_length")
    if tuple(null["candidate_null_vectors"])!=core.CANDIDATE_IDS:
        raise G4BRunnerError("null_candidate_vector_membership")
    for cid in core.CANDIDATE_IDS:
        if len(null["candidate_null_vectors"][cid])!=1999:
            raise G4BRunnerError("null_candidate_vector_length",cid)

def run_g4b(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True,max_workers:int=8):
    if any(FORWARD_GUARDS.values()):
        raise G4BRunnerError("runtime_guard_violation")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise G4BRunnerError("execution_commit")
    output=Path(output_directory)
    if require_canonical_output and output!=REAL_OUTPUT_DIRECTORY:
        raise G4BRunnerError("noncanonical_output_directory")
    if not require_canonical_output and output==REAL_OUTPUT_DIRECTORY:
        raise G4BRunnerError("canonical_output_requires_real_mode")
    if output.exists() or output.is_symlink():
        raise G4BRunnerError("output_directory_already_exists")

    e=loader.load_g4b()

    base_names=loader.base_feature_names(e)
    if len(base_names)!=45:
        raise G4BRunnerError("base_feature_name_count")

    base_per={d:loader.base_day_matrix(e,d) for d in dd.HISTORICAL_DAYS}
    _validate_support_contract(base_per)
    base=core.fit_candidate("BTC45_PROMOTED_BASE_REFIT",base_per)
    _validate_fitted_support(base)
    if base.feature_count!=45:
        raise G4BRunnerError("base_feature_count")

    candidate_per={}
    for cid in core.CANDIDATE_IDS:
        per={d:loader.candidate_day_matrix(e,d,cid) for d in dd.HISTORICAL_DAYS}
        _validate_support_contract(per)
        expected=loader.CANDIDATE_WIDTH[cid]
        if any(x.shape[1]!=expected for x,_,_ in per.values()):
            raise G4BRunnerError("candidate_width_contract",cid)
        candidate_per[cid]=per

    candidates={}
    workers=_normalize_workers(max_workers)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        fs={cid:pool.submit(_fit_worker,cid,candidate_per[cid]) for cid in core.CANDIDATE_IDS}
        for cid in core.CANDIDATE_IDS:
            candidates[cid]=fs[cid].result()
            _validate_fitted_support(candidates[cid])

    comparisons={cid:core.compare(base,candidates[cid]) for cid in core.CANDIDATE_IDS}
    null=core.joint_max_stat_null(base,candidates,seed=core.NULL_SEED,replicates=core.NULL_REPLICATES)
    _validate_null_completeness(null)

    names={
        "G4C01":"ETH_L0_STATIC_STATE",
        "G4C02":"ETH_L1_EVENT_FLOW",
        "G4C03":"ETH_L2_FULL_MICROSTRUCTURE",
    }
    rows=[]
    for cid in core.CANDIDATE_IDS:
        status=core.classify(candidates[cid],comparisons[cid],null["per_candidate"][cid])
        rows.append({
            "candidate_id":cid,
            "name":names[cid],
            "added_feature_count":loader.CANDIDATE_WIDTH[cid]-45,
            "status":status,
            "comparison_vs_btc45":comparisons[cid],
            "null":dict(null["per_candidate"][cid]),
            "feature_names":list(loader.candidate_feature_names(e,cid)),
            **_public_result(candidates[cid]),
        })

    ranked=_rank_survivors(rows)
    advanced=[ranked[0]["candidate_id"]] if ranked else []

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "parent_g3b_r1":{
            "path":str(loader.G3B_R1_ARTIFACT),
            "sha256":loader.G3B_R1_SHA256,
            "bytes":loader.G3B_R1_BYTES,
        },
        "common_support":{
            "rows":1341,"long":665,"short":676,
            "support_sha256":loader.EXPECTED_SUPPORT_SHA,
            "label_sha256":loader.EXPECTED_LABEL_SHA,
        },
        "pooled_outer_validation":{"rows":559,"long":302,"short":257},
        "base_feature_names":list(base_names),
        "base_comparator":{
            "identity":"BTC45_PROMOTED_BASE_REFIT",
            **_public_result(base,include_validation_rows=True),
        },
        "candidate_count":3,
        "candidate_ids":list(core.CANDIDATE_IDS),
        "candidate_widths":dict(loader.CANDIDATE_WIDTH),
        "eth_file_sha256":dict(loader.ETH_SHA256),
        "null":null,
        "leaderboard":rows,
        "layer_survivors":[r["candidate_id"] for r in rows if r["status"]==core.STATUS_SURVIVOR],
        "survivor_ranking":[
            {
                "rank":i+1,
                "candidate_id":r["candidate_id"],
                "max_stat_fwer_empirical_p":float(r["null"]["max_stat_fwer_empirical_p"]),
                "minimum_fold_delta_balanced_accuracy":float(r["comparison_vs_btc45"]["minimum_fold_delta_balanced_accuracy"]),
                "median_fold_delta_balanced_accuracy":float(r["comparison_vs_btc45"]["median_fold_delta_balanced_accuracy"]),
                "pooled_delta_balanced_accuracy":float(r["comparison_vs_btc45"]["pooled_delta_balanced_accuracy"]),
                "added_feature_count":int(r["added_feature_count"]),
            }
            for i,r in enumerate(ranked)
        ],
        "advanced_layers":advanced,
        "forward_guards":dict(FORWARD_GUARDS),
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"
").encode()
    staging=output.parent/f".{output.name}.part-{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise G4BRunnerError("staging_preexists")
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
        "layer_survivors":payload["layer_survivors"],
        "advanced_layers":advanced,
    }

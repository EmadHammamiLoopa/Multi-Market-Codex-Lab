from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev030_p6_m2_direction as p6
from . import dev034_g3a_core as core
from .v23_phase0dl_score import _load_day

EXPERIMENT_ID=core.EXPERIMENT_ID
DESIGN_VERSION=core.DESIGN_VERSION

FEATURE_ROOT=Path("/home/emadh/Multi-Market/evidence/v23/phase0dl_features250/BTCUSDT")
REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev034_g3a_opportunity_volatility_context_v1"
)
ARTIFACT_FILENAME="DEV034_G3A_OPPORTUNITY_VOLATILITY_CONTEXT.json"

EXPECTED_INPUT_SHA256={
    "2026-01-01":"ab0c61fe9a7517cf97388300e6adb18248a37a7977aac8455a10c02b7906de98",
    "2026-02-01":"33e56c6b5b02ec124bf3a21dbed27fc8705fc572cb7fed9ff73876de87c2978e",
    "2026-03-01":"076067a4731047dd992004d936d962567c1d7ceed864bb6e778db05bc8c59420",
    "2026-04-01":"a803fbb8d68f4173551be4c2cccf9fe03f25d86dc6e00469c4a5ab635ade2307",
    "2026-05-01":"36015c5954d820d8b2f0505ecab9fdc96f40136247d1270365c9ef81312de2e3",
}
# June/July are verified from frozen workspace metadata at runtime; this mapping
# intentionally does not invent missing identities.

class G3ARunnerError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _load_p3_days():
    loaded=tuple(dd.load_authorized_days())
    if tuple(x.day for x in loaded)!=dd.HISTORICAL_DAYS:
        raise G3ARunnerError("historical_day_calendar")
    datasets={}
    for day in loaded:
        ds=dd.build_candidate_day(
            day,
            target=p6.SELECTED_TARGET,
            window_seconds=p6.SELECTED_WINDOW_SECONDS,
            block=p6.SELECTED_BLOCK,
        )
        p6.validate_selected_candidate(ds)
        datasets[day.day]=(day,ds)
    return datasets

def _input_path(day):
    return FEATURE_ROOT/f"{day.isoformat()}_FEATURES250.csv"

def _write_csv(path:Path,ctx:core.DayContext):
    header=["local_timestamp_us","t1_label",*core.R_FEATURE_NAMES]
    with path.open("x",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n")
        w.writerow(header)
        for i in range(len(ctx.timestamps_us)):
            w.writerow([
                int(ctx.timestamps_us[i]),
                int(ctx.labels[i]),
                *[repr(float(v)) for v in ctx.full_r[i]],
            ])

def _daily_record(day,ctx:core.DayContext,csv_path:Path,input_path:Path):
    rec={
        "day":day.isoformat(),
        "input_path":str(input_path),
        "input_sha256":_sha(input_path),
        "rows":int(len(ctx.labels)),
        "long":int(np.sum(ctx.labels==1)),
        "short":int(np.sum(ctx.labels==0)),
        "file":csv_path.name,
        "file_bytes":int(csv_path.stat().st_size),
        "file_sha256":_sha(csv_path),
        "support_sha256":core.support_sha256(ctx.timestamps_us),
        "label_sha256":core.label_sha256(ctx.timestamps_us,ctx.labels),
        "full_r_matrix_sha256":core.matrix_sha256("FULL_R",ctx.full_r),
        "candidate_matrix_sha256":{},
    }
    for cid in core.CANDIDATE_IDS:
        x=core.candidate_matrix(ctx.full_r,cid)
        rec["candidate_matrix_sha256"][cid]=core.matrix_sha256(cid,x)
    return rec

def run_g3a(
    *,
    execution_commit:str,
    output_directory:Path=REAL_OUTPUT_DIRECTORY,
    require_canonical_output:bool=True,
):
    core.validate_registry_contract()
    if any(core.FORWARD_GUARDS.values()):
        raise G3ARunnerError("forward_guard_violation")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise G3ARunnerError("execution_commit")
    output=Path(output_directory)
    if require_canonical_output and output!=REAL_OUTPUT_DIRECTORY:
        raise G3ARunnerError("noncanonical_output")
    if not require_canonical_output and output==REAL_OUTPUT_DIRECTORY:
        raise G3ARunnerError("canonical_output_requires_real_mode")
    if output.exists() or output.is_symlink():
        raise G3ARunnerError("output_exists")

    per=_load_p3_days()
    staging=output.parent/f".{output.name}.part-{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise G3ARunnerError("staging_exists")
    staging.mkdir(parents=True)

    days=[]
    campaign_ts=[];campaign_y=[];campaign_r=[]
    try:
        for d in dd.HISTORICAL_DAYS:
            input_path=_input_path(d)
            if not input_path.is_file():
                raise G3ARunnerError("phase0dl_input_missing",str(input_path))
            expected=EXPECTED_INPUT_SHA256.get(d.isoformat())
            if expected is not None and _sha(input_path)!=expected:
                raise G3ARunnerError("phase0dl_input_sha",d.isoformat())
            raw_day=_load_day(input_path,d)
            loaded_day,p3_dataset=per[d]
            # Exact timestamp identity between the two frozen loaders is mandatory.
            if not np.array_equal(np.asarray(raw_day.ts,dtype=np.int64),np.asarray(loaded_day.ts,dtype=np.int64)):
                raise G3ARunnerError("phase0dl_authorized_day_timestamp_mismatch",d.isoformat())
            ctx=core.materialize_day(raw_day,p3_dataset)
            csv_path=staging/f"{d.isoformat()}_DEV034_G3A.csv"
            _write_csv(csv_path,ctx)
            days.append(_daily_record(d,ctx,csv_path,input_path))
            campaign_ts.append(ctx.timestamps_us)
            campaign_y.append(ctx.labels)
            campaign_r.append(ctx.full_r)

        ts=np.concatenate(campaign_ts)
        y=np.concatenate(campaign_y)
        full=np.concatenate(campaign_r)
        if (len(y),int(np.sum(y==1)),int(np.sum(y==0)))!=(1374,684,690):
            raise G3ARunnerError("campaign_counts")
        if full.shape!=(1374,22) or not np.all(np.isfinite(full)):
            raise G3ARunnerError("campaign_full_r_contract")

        payload={
            "experiment_id":EXPERIMENT_ID,
            "design_version":DESIGN_VERSION,
            "execution_commit":execution_commit,
            "status":"DEV034_G3A_EXACT_CONTEXT_MATERIALIZED",
            "pass":True,
            "parent_p3":{
                "path":str(p6.P3_ARTIFACT_PATH),
                "sha256":p6.P3_ARTIFACT_SHA256,
            },
            "feature_root":str(FEATURE_ROOT),
            "r_feature_names":list(core.R_FEATURE_NAMES),
            "r_feature_count":22,
            "candidate_count":16,
            "candidate_registry":core.public_registry(),
            "rows":1374,
            "long":684,
            "short":690,
            "campaign_support_sha256":core.support_sha256(ts),
            "campaign_label_sha256":core.label_sha256(ts,y),
            "campaign_full_r_matrix_sha256":core.matrix_sha256("FULL_R",full),
            "campaign_candidate_matrix_sha256":{
                cid:core.matrix_sha256(cid,core.candidate_matrix(full,cid))
                for cid in core.CANDIDATE_IDS
            },
            "days":days,
            "forward_guards":dict(core.FORWARD_GUARDS),
            "scientific_scope":{
                "direction_model_fit":False,
                "direction_metric_scored":False,
                "temporal_null_run":False,
                "pnl_run":False,
            },
        }

        artifact=staging/ARTIFACT_FILENAME
        content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
        with artifact.open("xb") as h:
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
        "rows":1374,
        "candidate_count":16,
    }

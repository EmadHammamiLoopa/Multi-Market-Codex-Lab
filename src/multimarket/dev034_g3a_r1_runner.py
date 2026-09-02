from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev030_p6_m2_direction as p6
from . import dev034_g3a_core as g3
from . import dev034_g3a_r1_core as r1
from . import dev034_g3a_runner as parent
from .v23_phase0dl_score import _load_day

EXPERIMENT_ID=r1.EXPERIMENT_ID
DESIGN_VERSION=r1.DESIGN_VERSION

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev034_g3a_r1_common_support_context_v1"
)
ARTIFACT_FILENAME="DEV034_G3A_R1_COMMON_SUPPORT_CONTEXT.json"

class G3AR1RunnerError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _write_day(path:Path,day:r1.EligibleDay):
    header=["local_timestamp_us","t1_label",*g3.R_FEATURE_NAMES]
    with path.open("x",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n")
        w.writerow(header)
        for i in range(len(day.labels)):
            w.writerow([
                int(day.timestamps_us[i]),
                int(day.labels[i]),
                *[repr(float(v)) for v in day.full_r[i]],
            ])

def run_g3a_r1(
    *,
    execution_commit:str,
    output_directory:Path=REAL_OUTPUT_DIRECTORY,
    require_canonical_output:bool=True,
):
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise G3AR1RunnerError("execution_commit")
    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise G3AR1RunnerError("noncanonical_output")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY:
        raise G3AR1RunnerError("canonical_requires_real_mode")
    if out.exists() or out.is_symlink():
        raise G3AR1RunnerError("output_exists")
    if any(r1.FORWARD_GUARDS.values()):
        raise G3AR1RunnerError("forward_guard")

    per=parent._load_p3_days()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists() or staging.is_symlink():
        raise G3AR1RunnerError("staging_exists")
    staging.mkdir(parents=True)

    eligible={}
    original_ts=[];original_y=[]
    common_ts=[];common_y=[];common_r=[]
    exclusions=[]
    day_records=[]

    try:
        for d in dd.HISTORICAL_DAYS:
            input_path=parent.FEATURE_ROOT/f"{d.isoformat()}_FEATURES250.csv"
            expected=parent.EXPECTED_INPUT_SHA256[d.isoformat()]
            if not input_path.is_file() or _sha(input_path)!=expected:
                raise G3AR1RunnerError("input_identity",d.isoformat())
            raw=_load_day(input_path,d)
            auth,ds=per[d]
            if not np.array_equal(np.asarray(raw.ts,dtype=np.int64),np.asarray(auth.ts,dtype=np.int64)):
                raise G3AR1RunnerError("full_grid_mismatch",d.isoformat())

            _,oy,ots=p6._t1_rows(ds)
            original_ts.append(np.asarray(ots,dtype=np.int64))
            original_y.append(np.asarray(oy,dtype=np.int8))

            ed=r1.derive_common_support(raw,ds)
            eligible[d.isoformat()]=ed
            exclusions.extend(ed.exclusions)

            fp=staging/f"{d.isoformat()}_DEV034_G3A_R1.csv"
            _write_day(fp,ed)

            rec={
                "day":d.isoformat(),
                "input_path":str(input_path),
                "input_sha256":expected,
                "original_rows":int(len(oy)),
                "eligible_rows":int(len(ed.labels)),
                "eligible_long":int(np.sum(ed.labels==1)),
                "eligible_short":int(np.sum(ed.labels==0)),
                "file":fp.name,
                "file_bytes":int(fp.stat().st_size),
                "file_sha256":_sha(fp),
                "support_sha256":g3.support_sha256(ed.timestamps_us),
                "label_sha256":g3.label_sha256(ed.timestamps_us,ed.labels),
                "full_r_matrix_sha256":g3.matrix_sha256("FULL_R",ed.full_r),
                "candidate_matrix_sha256":{
                    cid:g3.matrix_sha256(cid,g3.candidate_matrix(ed.full_r,cid))
                    for cid in g3.CANDIDATE_IDS
                },
                "excluded_rows":[e.__dict__ for e in ed.exclusions],
            }
            day_records.append(rec)
            common_ts.append(ed.timestamps_us)
            common_y.append(ed.labels)
            common_r.append(ed.full_r)

        r1.validate_frozen_common_support(eligible)

        ots=np.concatenate(original_ts)
        oy=np.concatenate(original_y)
        ts=np.concatenate(common_ts)
        y=np.concatenate(common_y)
        full=np.concatenate(common_r)

        payload={
            "experiment_id":EXPERIMENT_ID,
            "design_version":DESIGN_VERSION,
            "execution_commit":execution_commit,
            "status":"DEV034_G3A_R1_COMMON_SUPPORT_MATERIALIZED",
            "pass":True,
            "parent_p3":{
                "path":str(p6.P3_ARTIFACT_PATH),
                "sha256":p6.P3_ARTIFACT_SHA256,
            },
            "parent_g3a_status":"PREEXECUTION_INFEASIBLE_NO_RESULT",
            "feature_root":str(parent.FEATURE_ROOT),
            "r_feature_names":list(g3.R_FEATURE_NAMES),
            "candidate_count":16,
            "candidate_registry":g3.public_registry(),
            "original_support":{
                "rows":1374,
                "long":684,
                "short":690,
                "support_sha256":g3.support_sha256(ots),
                "label_sha256":g3.label_sha256(ots,oy),
            },
            "common_support":{
                "rows":r1.EXPECTED_ROWS,
                "long":r1.EXPECTED_LONG,
                "short":r1.EXPECTED_SHORT,
                "support_sha256":g3.support_sha256(ts),
                "label_sha256":g3.label_sha256(ts,y),
                "full_r_matrix_sha256":g3.matrix_sha256("FULL_R",full),
                "candidate_matrix_sha256":{
                    cid:g3.matrix_sha256(cid,g3.candidate_matrix(full,cid))
                    for cid in g3.CANDIDATE_IDS
                },
            },
            "excluded_count":len(exclusions),
            "exclusion_reason_counts":r1.EXPECTED_REASON_COUNTS,
            "exclusion_ledger":[e.__dict__ for e in exclusions],
            "days":day_records,
            "forward_guards":dict(r1.FORWARD_GUARDS),
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
        "rows":r1.EXPECTED_ROWS,
        "excluded":r1.EXPECTED_EXCLUDED,
        "candidate_count":16,
    }

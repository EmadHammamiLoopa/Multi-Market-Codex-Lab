from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev042_p0_feature_core as core

EXPERIMENT_ID="DEV042-P0"
DESIGN_VERSION="feature-schema-common-support-audit-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev042_p0_feature_schema_audit_v1"
)
ARTIFACT_FILENAME="DEV042_P0_FEATURE_SCHEMA_AUDIT_RESULT.json"

FORWARD_GUARDS={
    "labels_constructed":False,
    "model_fit":False,
    "economic_output_calculated":False,
    "sep01_plus_opened":False,
    "other_market_opened":False,
}

class RunnerError(RuntimeError):
    pass

def _sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _minute_view(day):
    idx=dd.exact_minute_decision_indices(day.ts)
    ts=np.asarray(day.ts,dtype=np.int64)[idx]
    mid=np.asarray(day.mid,dtype=np.float64)[idx]
    book=np.asarray(day.book_valid,dtype=bool)[idx]
    l1=np.asarray(day.valid["L1"],dtype=bool)[idx]
    l2=np.asarray(day.valid["L2"],dtype=bool)[idx]
    full=np.asarray(day.X["L2"],dtype=np.float64)[idx]
    if full.shape!=(len(ts),len(dd.SOURCE_FEATURE_ORDER)):
        raise RunnerError("minute_feature_shape")
    source={
        name:full[:,j]
        for j,name in enumerate(dd.SOURCE_FEATURE_ORDER)
    }
    return ts,mid,book,l1,l2,source

def _audit_day(day):
    ts,mid,book,l1,l2,source=_minute_view(day)
    if len(ts)!=1440:
        raise RunnerError(f"minute_count:{day.day}:{len(ts)}")

    f0_valid=np.zeros(len(ts),dtype=bool)
    f1_valid=np.zeros(len(ts),dtype=bool)
    f2_valid=np.zeros(len(ts),dtype=bool)
    common_rows=[]
    invalid_reasons={"F0":0,"F1":0,"F2":0}

    for i,t in enumerate(ts.tolist()):
        f0,f1,f2=core.build_feature_families(
            decision_timestamp_us=int(t),
            minute_timestamps_us=ts,
            mid=mid,
            book_valid=book,
            l1_valid=l1,
            l2_valid=l2,
            source=source,
        )
        f0_valid[i]=f0 is not None
        f1_valid[i]=f1 is not None
        f2_valid[i]=f2 is not None
        invalid_reasons["F0"]+=int(f0 is None)
        invalid_reasons["F1"]+=int(f1 is None)
        invalid_reasons["F2"]+=int(f2 is None)
        if f0 is not None and f1 is not None and f2 is not None:
            if not (np.all(np.isfinite(f0)) and np.all(np.isfinite(f1)) and np.all(np.isfinite(f2))):
                raise RunnerError("nonfinite_common_feature")
            common_rows.append((int(t),f0,f1,f2))

    common=f0_valid & f1_valid & f2_valid
    common_ts=ts[common]
    if len(common_ts)==0:
        raise RunnerError(f"empty_common:{day.day}")
    if not np.array_equal(common_ts,np.asarray([x[0] for x in common_rows],dtype=np.int64)):
        raise RunnerError("common_row_order")
    if np.any(np.diff(common_ts)<=0):
        raise RunnerError("common_timestamp_order")

    return {
        "date":day.day.isoformat(),
        "minute_decisions":1440,
        "native_f0_support":int(np.sum(f0_valid)),
        "native_f1_support":int(np.sum(f1_valid)),
        "native_f2_support":int(np.sum(f2_valid)),
        "common_support":int(np.sum(common)),
        "common_support_retention":float(np.mean(common)),
        "common_support_sha256":dd.support_sha256(common_ts),
        "first_common_timestamp_us":int(common_ts[0]),
        "last_common_timestamp_us":int(common_ts[-1]),
        "invalid_counts":invalid_reasons,
        "all_common_features_finite":True,
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

    manifest=dd.verify_input_manifest()
    days=dd.load_authorized_days()
    if tuple(x.day for x in days)!=dd.HISTORICAL_DAYS:
        raise RunnerError("calendar")

    per_day=[_audit_day(d) for d in days]
    pooled_decisions=sum(x["minute_decisions"] for x in per_day)
    pooled_common=sum(x["common_support"] for x in per_day)
    retention=float(pooled_common/pooled_decisions)

    dimensions={
        "C0_PRICE_LOGIT":len(core.F0_NAMES),
        "C1_OFI_LOGIT":len(core.F1_NAMES),
        "C2_PRESSURE_CAPACITY_LOGIT":len(core.F2_NAMES),
        "C3_COMBINED_LOGIT":len(core.COMBINED_NAMES),
        "C4_COMBINED_HGB":len(core.COMBINED_NAMES),
    }
    expected_dims={
        "C0_PRICE_LOGIT":15,
        "C1_OFI_LOGIT":60,
        "C2_PRESSURE_CAPACITY_LOGIT":51,
        "C3_COMBINED_LOGIT":111,
        "C4_COMBINED_HGB":111,
    }

    checks={
        "manifest_seven_days":len(manifest)==7,
        "calendar_exact":[x.day for x in manifest]==list(dd.HISTORICAL_DAYS),
        "dimensions_exact":dimensions==expected_dims,
        "every_day_1440":all(x["minute_decisions"]==1440 for x in per_day),
        "common_nonempty_every_day":all(x["common_support"]>0 for x in per_day),
        "pooled_common_retention_ge_090":retention>=0.90,
        "all_common_features_finite":all(x["all_common_features_finite"] for x in per_day),
        "all_forward_guards_false":not any(FORWARD_GUARDS.values()),
    }
    status=(
        "DEV042_P0_FEATURE_SCHEMA_AUDIT_PASS"
        if all(checks.values())
        else "DEV042_P0_COMMON_SUPPORT_RETENTION_FAIL"
        if not checks["pooled_common_retention_ge_090"]
        else "DEV042_P0_FEATURE_SCHEMA_AUDIT_FAIL"
    )

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "symbol":"BTCUSDT",
        "days":[d.isoformat() for d in dd.HISTORICAL_DAYS],
        "source_manifest":[
            {"date":x.day.isoformat(),"path":str(x.path),"sha256":x.sha256,"bytes":x.bytes}
            for x in manifest
        ],
        "feature_dimensions":dimensions,
        "feature_names":{
            "F0":list(core.F0_NAMES),
            "F1":list(core.F1_NAMES),
            "F2":list(core.F2_NAMES),
            "COMBINED":list(core.COMBINED_NAMES),
        },
        "feature_name_sha256":{
            "F0":core.feature_name_sha256(core.F0_NAMES),
            "F1":core.feature_name_sha256(core.F1_NAMES),
            "F2":core.feature_name_sha256(core.F2_NAMES),
            "COMBINED":core.feature_name_sha256(core.COMBINED_NAMES),
        },
        "max_raw_lookback_seconds":{
            "F0":1800,
            "F1":1801,
            "F2":901,
            "GLOBAL":1801,
        },
        "per_day":per_day,
        "pooled":{
            "minute_decisions":int(pooled_decisions),
            "common_support":int(pooled_common),
            "common_support_retention":retention,
        },
        "checks":checks,
        "forward_guards":dict(FORWARD_GUARDS),
        "explicit_no_result_guarantee":{
            "labels":False,
            "model_fit":False,
            "classification_metrics":False,
            "economic_metrics":False,
            "sep01_plus_access":False,
            "other_market_access":False,
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
            h.write(content);h.flush();os.fsync(h.fileno())
        os.replace(staging,out)
    except BaseException:
        if staging.exists():shutil.rmtree(staging,ignore_errors=True)
        raise

    final=out/ARTIFACT_FILENAME
    return {
        "artifact_path":str(final),
        "artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),
        "status":status,
        "common_support_retention":retention,
    }

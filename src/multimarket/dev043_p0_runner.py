from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev030_first_passage as fp
from . import dev042_p0_feature_core as fcore
from . import dev042_p1_materialization as mat
from . import dev043_p0_core as core

EXPERIMENT_ID="DEV043-P0"
DESIGN_VERSION="event-conditioned-parent-schema-audit-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev043_p0_parent_schema_audit_v1"
)
ARTIFACT_FILENAME="DEV043_P0_PARENT_SCHEMA_AUDIT_RESULT.json"

DEV041_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev041_p2_model_free_headroom_v1/"
    "DEV041_P2_MODEL_FREE_HEADROOM_RESULT.json"
)
DEV041_BYTES=429239
DEV041_SHA="542117791966f9049cb49e5b578d7857b3e1178f44be83172c7edfac56244a15"

DEV042_P0_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev042_p0_feature_schema_audit_v1/"
    "DEV042_P0_FEATURE_SCHEMA_AUDIT_RESULT.json"
)
DEV042_P0_BYTES=12989
DEV042_P0_SHA="d9259a53d24492f478615c986ed73981f052d483a764935a8dfd68d17212b882"

DEV042_P3_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev042_p3_predictive_screen_v1/"
    "DEV042_P3_PREDICTIVE_SCREEN_RESULT.json"
)
DEV042_P3_BYTES=155134
DEV042_P3_SHA="bdb411e8536d94bb21deca5bfb7f31998023dacd727c27c3a67993b0bc07ac3f"

FORWARD_GUARDS={
    "sep01_plus_opened":False,
    "other_market_opened":False,
    "model_fit":False,
    "probabilities_calculated":False,
    "classification_metrics_calculated":False,
    "economics_calculated":False,
    "null_calculated":False,
    "class_counts_serialized":False,
    "class_prevalence_serialized":False,
}

class AuditError(RuntimeError):
    pass

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def _verify_artifact(path:Path,bytes_:int,sha:str,name:str):
    if not path.is_file():
        raise AuditError(f"{name}_missing")
    if path.stat().st_size!=bytes_:
        raise AuditError(f"{name}_bytes")
    if _sha(path)!=sha:
        raise AuditError(f"{name}_sha")

def _verify_semantic_parents():
    d41=json.loads(DEV041_ARTIFACT.read_text(encoding="utf-8"))
    if d41.get("status")!="DEV041_HEADROOM_SURVIVOR_H1800_B32":
        raise AuditError("dev041_status")
    if d41.get("advanced_candidate")!=["H1800_B32"]:
        raise AuditError("dev041_advanced")

    d42=json.loads(DEV042_P3_ARTIFACT.read_text(encoding="utf-8"))
    if d42.get("status")!="DEV042_NO_PREDICTIVE_SURVIVOR_FOR_H1800_B32":
        raise AuditError("dev042_p3_status")
    if d42.get("advanced_candidate")!=[]:
        raise AuditError("dev042_p3_advanced")

def _day_audit(day):
    z=mat.materialize_day(day)
    support_sha=mat.verify_frozen_support(z)

    raw_ts=np.asarray(day.ts,dtype=np.int64)
    pos=np.searchsorted(raw_ts,z.timestamps_us)
    if not np.array_equal(raw_ts[pos],z.timestamps_us):
        raise AuditError(f"raw_alignment:{z.date}")

    records=fp.label_first_passage_targets(
        day,
        pos,
        horizon_seconds=1800,
        barrier_bps=32,
        latency_ms=250,
    )
    if len(records)!=len(z.timestamps_us):
        raise AuditError(f"record_count:{z.date}")

    all_factorization=True
    stage_b_subset=True
    invalid_excluded=True
    schema_ok=True
    timestamp_ok=True

    for ts,r in zip(z.timestamps_us.tolist(),records,strict=True):
        if int(r.get("decision_timestamp_us",-1))!=int(ts):
            timestamp_ok=False

        if r.get("horizon_seconds")!=1800 or r.get("barrier_bps")!=32:
            schema_ok=False

        inv=core.factorization_invariants(r)
        if not all(inv.values()):
            all_factorization=False

        d=core.decompose_record(r)
        if d.stage_b_direction is not None and d.stage_a_event!=core.EVENT_TOUCH:
            stage_b_subset=False

        if not d.valid and (d.stage_a_event is not None or d.stage_b_direction is not None):
            invalid_excluded=False

    return {
        "date":z.date,
        "common_support_rows":int(len(z.timestamps_us)),
        "common_support_sha256":support_sha,
        "feature_shapes":{
            "C0_PRICE_LOGIT":[int(z.X0.shape[0]),int(z.X0.shape[1])],
            "C1_OFI_LOGIT":[int(z.X1.shape[0]),int(z.X1.shape[1])],
            "C2_PRESSURE_CAPACITY_LOGIT":[int(z.X2.shape[0]),int(z.X2.shape[1])],
            "C3_COMBINED_LOGIT":[int(z.X3.shape[0]),int(z.X3.shape[1])],
            "C4_COMBINED_HGB":[int(z.X4.shape[0]),int(z.X4.shape[1])],
        },
        "target_record_count_matches_common_support":bool(len(records)==len(z.timestamps_us)),
        "target_geometry_schema_valid":bool(schema_ok),
        "target_timestamp_alignment_valid":bool(timestamp_ok),
        "factorization_invariants_all_pass":bool(all_factorization),
        "stage_b_support_subset_of_touch":bool(stage_b_subset),
        "invalid_and_ambiguous_excluded_from_both_stages":bool(invalid_excluded),
        "all_feature_matrices_finite":bool(
            all(np.all(np.isfinite(x)) for x in (z.X0,z.X1,z.X2,z.X3,z.X4))
        ),
        "c3_c4_identical":bool(np.array_equal(z.X3,z.X4)),
    }

def run(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True):
    if any(FORWARD_GUARDS.values()):
        raise AuditError("forbidden_guard")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise AuditError("execution_commit")

    out=Path(output_directory)
    if require_canonical_output and out!=REAL_OUTPUT_DIRECTORY:
        raise AuditError("noncanonical_output")
    if not require_canonical_output and out==REAL_OUTPUT_DIRECTORY:
        raise AuditError("canonical_requires_real")
    if out.exists() or out.is_symlink():
        raise AuditError("output_exists")

    _verify_artifact(DEV041_ARTIFACT,DEV041_BYTES,DEV041_SHA,"dev041")
    _verify_artifact(DEV042_P0_ARTIFACT,DEV042_P0_BYTES,DEV042_P0_SHA,"dev042_p0")
    _verify_artifact(DEV042_P3_ARTIFACT,DEV042_P3_BYTES,DEV042_P3_SHA,"dev042_p3")
    _verify_semantic_parents()

    manifest=dd.verify_input_manifest()
    days=dd.load_authorized_days()

    if len(manifest)!=7 or len(days)!=7:
        raise AuditError("seven_days")
    if tuple(d.day for d in days)!=dd.HISTORICAL_DAYS:
        raise AuditError("calendar")

    per_day=[_day_audit(day) for day in days]

    dimensions={
        "C0_PRICE_LOGIT":len(fcore.F0_NAMES),
        "C1_OFI_LOGIT":len(fcore.F1_NAMES),
        "C2_PRESSURE_CAPACITY_LOGIT":len(fcore.F2_NAMES),
        "C3_COMBINED_LOGIT":len(fcore.COMBINED_NAMES),
        "C4_COMBINED_HGB":len(fcore.COMBINED_NAMES),
    }

    checks={
        "dev041_parent_identity":True,
        "dev042_p0_parent_identity":True,
        "dev042_p3_parent_identity":True,
        "semantic_parent_statuses":True,
        "seven_exact_days":True,
        "dimensions_exact":dimensions=={
            "C0_PRICE_LOGIT":15,
            "C1_OFI_LOGIT":60,
            "C2_PRESSURE_CAPACITY_LOGIT":51,
            "C3_COMBINED_LOGIT":111,
            "C4_COMBINED_HGB":111,
        },
        "every_day_common_support_1409":all(x["common_support_rows"]==1409 for x in per_day),
        "every_day_target_count_matches":all(x["target_record_count_matches_common_support"] for x in per_day),
        "every_day_target_schema_valid":all(x["target_geometry_schema_valid"] for x in per_day),
        "every_day_target_timestamp_aligned":all(x["target_timestamp_alignment_valid"] for x in per_day),
        "every_day_factorization_valid":all(x["factorization_invariants_all_pass"] for x in per_day),
        "stage_b_always_subset_of_touch":all(x["stage_b_support_subset_of_touch"] for x in per_day),
        "invalid_ambiguous_excluded":all(x["invalid_and_ambiguous_excluded_from_both_stages"] for x in per_day),
        "all_features_finite":all(x["all_feature_matrices_finite"] for x in per_day),
        "c3_c4_identical":all(x["c3_c4_identical"] for x in per_day),
        "all_forward_guards_false":not any(FORWARD_GUARDS.values()),
    }

    status=(
        "DEV043_P0_PARENT_SCHEMA_AUDIT_PASS"
        if all(checks.values())
        else "DEV043_P0_PARENT_SCHEMA_AUDIT_FAIL"
    )

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "execution_commit":execution_commit,
        "status":status,
        "symbol":"BTCUSDT",
        "target":{"horizon_seconds":1800,"barrier_bps":32,"entry_latency_ms":250},
        "parent_identities":{
            "DEV041":{"bytes":DEV041_BYTES,"sha256":DEV041_SHA},
            "DEV042_P0":{"bytes":DEV042_P0_BYTES,"sha256":DEV042_P0_SHA},
            "DEV042_P3":{"bytes":DEV042_P3_BYTES,"sha256":DEV042_P3_SHA},
        },
        "feature_dimensions":dimensions,
        "per_day":per_day,
        "checks":checks,
        "forward_guards":dict(FORWARD_GUARDS),
        "explicit_no_result_guarantee":{
            "touch_count":False,
            "none_count":False,
            "touch_prevalence":False,
            "long_count":False,
            "short_count":False,
            "conditional_direction_prevalence":False,
            "ambiguity_count":False,
            "model_fit":False,
            "probabilities":False,
            "classification_metrics":False,
            "economics":False,
            "null":False,
            "ranking":False,
            "survivor":False,
            "sep01_plus_access":False,
            "other_market_access":False,
        },
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=out.parent/f".{out.name}.part-{os.getpid()}"
    if staging.exists():
        raise AuditError("staging_exists")
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
    }

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Mapping

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev031_p1a_event_depth_materialize as p1a
from . import dev032_e1a_feature_core as fc
from . import dev032_e1a_materialize as mat
from .v23_phase0dl_score import _load_day

EXPERIMENT_ID="DEV032-E1A"
DESIGN_VERSION="wave1-full-materialization-v1"
STATUS_PASS="DEV032_WAVE1_EXACT_SUPPORT_MATERIALIZED"

P1A_MANIFEST=Path(
    "/home/emadh/Multi-Market/evidence/dev031_p1a_event_depth_materialization_v1/"
    "DEV031_P1A_EVENT_DEPTH_MATERIALIZATION.json"
)
P1A_SHA256="a8a4f89262b9f01e76fc10a1b9c54ac28dd7faec3180a1a0fac19499eb9467d8"
RAW_ROOT=p1a.RAW_ROOT
TOOL_REL=Path("tools/dev032_e1a_raw_features.cpp")

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev032_e1a_wave1_materialization_v1"
)
MANIFEST_FILENAME="DEV032_E1A_WAVE1_MATERIALIZATION.json"

FORWARD_GUARDS={
    "aug01_opened":False,
    "aug30_opened":False,
    "sep01_or_later_opened":False,
    "railway_opened":False,
    "archive_bucket_opened":False,
    "abundant_love_opened":False,
    "downloads_or_acquisition_run":False,
    "predictive_fit_run":False,
    "predictive_metric_run":False,
    "pnl_run":False,
}

class E1ARunnerError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class DayBundle:
    day:date
    ts:np.ndarray
    y:np.ndarray
    strategies:dict[str,np.ndarray]
    raw_stderr:str

@dataclass(frozen=True)
class ArtifactWriteResult:
    output_directory:Path
    artifact_path:Path
    artifact_sha256:str
    artifact_bytes:int

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _compile_tool(workspace:Path,build_dir:Path)->Path:
    root=Path(workspace).resolve()
    source=root/TOOL_REL
    if not source.is_file():
        raise E1ARunnerError("extractor_source_missing",str(source))
    cxx=shutil.which("g++")
    if cxx is None:
        raise E1ARunnerError("gpp_missing")
    build=Path(build_dir)
    build.mkdir(parents=True,exist_ok=True)
    exe=build/"dev032_e1a_raw_features"
    stamp=build/"dev032_e1a_raw_features.source.sha256"
    source_sha=_sha(source)
    if exe.is_file() and stamp.is_file() and stamp.read_text().strip()==source_sha:
        return exe
    p=subprocess.run(
        [cxx,"-std=c++17","-O3","-DNDEBUG",str(source),"-lz","-o",str(exe)],
        capture_output=True,text=True,
    )
    if p.returncode!=0:
        raise E1ARunnerError("extractor_compile_failed",p.stderr)
    stamp.write_text(source_sha+"\n")
    return exe

def _write_support(path:Path,ts:np.ndarray)->None:
    with Path(path).open("w",encoding="utf-8",newline="") as h:
        h.write("local_timestamp_us\n")
        for t in np.asarray(ts,dtype=np.int64).tolist():
            h.write(f"{int(t)}\n")

def _verify_preconditions(workspace:Path):
    if any(FORWARD_GUARDS.values()):
        raise E1ARunnerError("runtime_guard_violation")
    if fc.strategy_feature_counts()!={
      "S00":23,"S01":26,"S02":49,"S03":12,
      "S04":1,"S05":7,"S06":2,"S07":7,
      "S08":5,"S09":5,"S10":4,
      "S11":10,"S12":20,"S13":4,"S14":10,"S15":40,
      "S16":2,"S17":2,"S18":4,"S19":4,"S20":6,
      "S21":8,"S22":6,"S23":4,"S24":16,
      "S25":12,"S26":8,"S27":8,"S28":8,
      "S29":16,"S30":6,"S31":6,
      "S32":4,"S33":4,"S34":15,"S35":24,
    }:
        raise E1ARunnerError("strategy_registry_drift")
    p0a,_p2c,p3=p1a.verify_artifacts()
    raw_manifest=p1a.verify_raw_manifest_against_p0a(p0a)
    supports,agg_manifest,contract=p1a.build_selected_p3_support()
    p1a.reconcile_p3_support_contract(contract,p3)
    if _sha(P1A_MANIFEST)!=P1A_SHA256:
        raise E1ARunnerError("p1a_manifest_sha256_mismatch")
    return p0a,p3,supports,agg_manifest,contract,raw_manifest

def _load_p1a_controls()->dict[date,tuple[np.ndarray,np.ndarray,np.ndarray,np.ndarray]]:
    if not P1A_MANIFEST.is_file():
        raise E1ARunnerError("p1a_manifest_missing",str(P1A_MANIFEST))
    if _sha(P1A_MANIFEST)!=P1A_SHA256:
        raise E1ARunnerError("p1a_manifest_sha256_mismatch")
    manifest=json.loads(P1A_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("status")!="EVENT_DEPTH_EXACT_P3_SUPPORT_MATERIALIZED" or manifest.get("pass") is not True:
        raise E1ARunnerError("p1a_terminal_status")
    if manifest.get("p3_support_contract_reproduced_exactly") is not True:
        raise E1ARunnerError("p1a_support_contract")

    price=tuple(manifest["feature_names"]["price"])
    event=tuple(manifest["feature_names"]["event_depth"])
    if len(price)!=23 or len(event)!=26:
        raise E1ARunnerError("p1a_feature_count")

    root=P1A_MANIFEST.parent
    out={}
    for rec in manifest["days"]:
        d=date.fromisoformat(rec["day"])
        path=root/rec["file"]
        if not path.is_file():
            raise E1ARunnerError("p1a_day_file_missing",d.isoformat())
        if _sha(path)!=rec["file_sha256"] or int(path.stat().st_size)!=int(rec["file_bytes"]):
            raise E1ARunnerError("p1a_day_file_identity",d.isoformat())
        with path.open("r",encoding="utf-8",newline="") as h:
            rows=list(csv.reader(h))
        expected=("local_timestamp_us","t1_label")+price+event
        if not rows or tuple(rows[0])!=expected:
            raise E1ARunnerError("p1a_day_header",d.isoformat())
        body=rows[1:]
        ts=np.asarray([int(x[0]) for x in body],dtype=np.int64)
        y=np.asarray([int(x[1]) for x in body],dtype=np.int8)
        x=np.asarray([[float(v) for v in row[2:]] for row in body],dtype=np.float64)
        if x.shape!=(len(ts),49) or not np.all(np.isfinite(x)):
            raise E1ARunnerError("p1a_day_matrix",d.isoformat())
        if dd.support_sha256(ts)!=rec["support_sha256"]:
            raise E1ARunnerError("p1a_day_support",d.isoformat())
        if not np.all(np.isin(y,(0,1))):
            raise E1ARunnerError("p1a_day_labels",d.isoformat())
        out[d]=(ts,y,x[:,:23],x[:,23:])
    if tuple(out)!=dd.HISTORICAL_DAYS:
        raise E1ARunnerError("p1a_day_calendar")
    return out

def _s03_for_day(day:date,support_ts:np.ndarray)->np.ndarray:
    entry={x.day:x for x in dd.verify_input_manifest()}[day]
    day_obj=_load_day(entry.path,day)
    target=next(
        x for x in dd.FROZEN_TARGETS
        if x.target_id=="A" and x.horizon_seconds==120 and x.barrier_bps==16
    )
    c=dd.build_candidate_day(
        day_obj,target=target,window_seconds=32,block="PRICE_BOOK"
    )
    ts=np.asarray(c.decision_timestamps_us,dtype=np.int64)
    index={int(t):i for i,t in enumerate(ts.tolist())}
    rows=[]
    for t in np.asarray(support_ts,dtype=np.int64).tolist():
        if int(t) not in index:
            raise E1ARunnerError("s03_support_timestamp_missing",f"{day}@{t}")
        i=index[int(t)]
        if not bool(c.s0_valid[i]):
            raise E1ARunnerError("s03_invalid_on_exact_support",f"{day}@{t}")
        rows.append(np.asarray(c.s0_values[i],dtype=np.float64))
    x=np.asarray(rows,dtype=np.float64)
    if x.shape!=(len(support_ts),12) or not np.all(np.isfinite(x)):
        raise E1ARunnerError("s03_matrix_shape_or_finite",day.isoformat())
    return x

def _raw_for_day(
    *,
    exe:Path,
    day:date,
    support_ts:np.ndarray,
    temp_dir:Path,
)->tuple[dict[str,np.ndarray],str]:
    support=Path(temp_dir)/f"{day.isoformat()}_support.csv"
    output=Path(temp_dir)/f"{day.isoformat()}_raw278.csv"
    _write_support(support,support_ts)
    raw=RAW_ROOT/f"{day.isoformat()}.csv.gz"
    p=subprocess.run(
        [str(exe),str(raw),str(support),str(output)],
        capture_output=True,text=True,
    )
    if p.returncode!=0:
        raise E1ARunnerError(
            "raw_extractor_failed",
            f"{day} rc={p.returncode} stderr={p.stderr}",
        )
    try:
        values=mat.parse_raw_extractor_csv(output,support_ts)
    except mat.E1AMaterializationError as exc:
        raise E1ARunnerError(
            "raw_extractor_contract_failed",
            f"{day} {exc.reason}: {exc}",
        ) from exc
    return values,p.stderr.strip()

def materialize_days(
    *,
    workspace:Path,
    supports:Mapping[date,p1a.DaySupport],
    temp_dir:Path,
    max_workers:int=2,
)->dict[date,DayBundle]:
    controls=_load_p1a_controls()
    exe=_compile_tool(workspace,Path(workspace)/".build"/"dev032_e1a")
    tmp=Path(temp_dir)
    tmp.mkdir(parents=True,exist_ok=True)

    # S03 derives from already-frozen 250 ms aggregated input and is cheap enough
    # to build serially before the heavy raw-L2 pass.
    s03={}
    for d in dd.HISTORICAL_DAYS:
        s03[d]=_s03_for_day(d,supports[d].timestamps_us)

    def one(d:date)->DayBundle:
        sup=supports[d]
        ts,y,s00,s01=controls[d]
        if not np.array_equal(ts,sup.timestamps_us):
            raise E1ARunnerError("p1a_p3_support_mismatch",d.isoformat())
        if not np.array_equal(y,sup.labels):
            raise E1ARunnerError("p1a_p3_label_mismatch",d.isoformat())
        raw,stderr=_raw_for_day(
            exe=exe,day=d,support_ts=ts,temp_dir=tmp
        )
        vals={}
        vals["S00"]=s00
        vals["S01"]=s01
        vals["S02"]=np.concatenate([s00,s01],axis=1)
        vals["S03"]=s03[d]
        for sid in mat.RAW_IDS:
            vals[sid]=raw[sid]
        # Exact order + widths + finite checks, but day counts are validated
        # again only after concatenating the full campaign.
        bundle=mat.assemble_bundle(ts,y,vals,require_full_campaign_counts=False)
        return DayBundle(
            d,bundle.support.timestamps_us,bundle.support.labels,
            {m.strategy_id:m.values for m in bundle.matrices},stderr
        )

    out={}
    workers=max(1,min(int(max_workers),2))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs={pool.submit(one,d):d for d in dd.HISTORICAL_DAYS}
        for fut in as_completed(futs):
            d=futs[fut]
            out[d]=fut.result()
    return {d:out[d] for d in dd.HISTORICAL_DAYS}

def _full_campaign_bundle(days:Mapping[date,DayBundle])->mat.MaterializedBundle:
    ts=np.concatenate([days[d].ts for d in dd.HISTORICAL_DAYS])
    y=np.concatenate([days[d].y for d in dd.HISTORICAL_DAYS])
    vals={
        sid:np.concatenate([days[d].strategies[sid] for d in dd.HISTORICAL_DAYS],axis=0)
        for sid in mat.ALL_IDS
    }
    return mat.assemble_bundle(ts,y,vals,require_full_campaign_counts=True)

def _write_day_csv(path:Path,day:DayBundle)->None:
    header=["local_timestamp_us","t1_label"]
    for sid in mat.ALL_IDS:
        header.extend(mat.expected_feature_names(sid))
    with Path(path).open("w",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n")
        w.writerow(header)
        for i in range(len(day.ts)):
            row=[str(int(day.ts[i])),str(int(day.y[i]))]
            for sid in mat.ALL_IDS:
                row.extend(format(float(v),".17g") for v in day.strategies[sid][i])
            w.writerow(row)

def _canonical(payload:Mapping[str,Any])->bytes:
    return (
        json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)
        +"\n"
    ).encode("utf-8")

def run_e1a(
    *,
    workspace:Path,
    execution_commit:str,
    output_directory:Path=REAL_OUTPUT_DIRECTORY,
    require_canonical_output:bool=True,
    max_workers:int=2,
)->ArtifactWriteResult:
    workspace=Path(workspace).resolve()
    output=Path(output_directory)
    if require_canonical_output and output!=REAL_OUTPUT_DIRECTORY:
        raise E1ARunnerError("noncanonical_output_directory")
    if not require_canonical_output and output==REAL_OUTPUT_DIRECTORY:
        raise E1ARunnerError("canonical_output_requires_real_mode")
    if output.exists() or output.is_symlink():
        raise E1ARunnerError("output_directory_already_exists")
    if (
        not isinstance(execution_commit,str)
        or len(execution_commit)!=40
        or any(ch not in "0123456789abcdef" for ch in execution_commit)
    ):
        raise E1ARunnerError("execution_commit_must_be_full_sha")

    p0a,p3,supports,agg_manifest,contract,raw_manifest=_verify_preconditions(workspace)

    with tempfile.TemporaryDirectory(prefix="dev032_e1a_") as td:
        days=materialize_days(
            workspace=workspace,supports=supports,temp_dir=Path(td),
            max_workers=max_workers,
        )
        full=_full_campaign_bundle(days)

        staging=output.parent/f".{output.name}.part-{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise E1ARunnerError("staging_directory_preexists")
        staging.mkdir(parents=True)
        try:
            day_records=[]
            for d in dd.HISTORICAL_DAYS:
                z=days[d]
                p=staging/f"{d.isoformat()}_DEV032_E1A.csv"
                _write_day_csv(p,z)
                day_records.append({
                    "day":d.isoformat(),
                    "rows":int(len(z.ts)),
                    "long":int(np.sum(z.y==1)),
                    "short":int(np.sum(z.y==0)),
                    "support_sha256":mat.support_sha256(z.ts),
                    "label_sha256":mat.label_sha256(z.ts,z.y),
                    "file":p.name,
                    "file_sha256":_sha(p),
                    "file_bytes":int(p.stat().st_size),
                    "raw_extractor_stderr":z.raw_stderr,
                    "strategy_matrix_sha256":{
                        sid:mat.matrix_sha256(sid,z.strategies[sid])
                        for sid in mat.ALL_IDS
                    },
                })

            manifest=mat.public_manifest(full)
            manifest.update({
                "experiment_id":EXPERIMENT_ID,
                "design_version":DESIGN_VERSION,
                "status":STATUS_PASS,
                "pass":True,
                "execution_commit":execution_commit,
                "selected_configuration":{
                    "symbol":"BTCUSDT",
                    "task":"DIRECTION_GIVEN_TOUCH",
                    "target_id":"A",
                    "horizon_seconds":120,
                    "barrier_bps":16,
                    "window_seconds":32,
                    "strategies":36,
                    "raw_derived_columns":278,
                },
                "provenance":{
                    "p0a_artifact":{
                        "path":str(p1a.P0A_ARTIFACT),
                        "sha256":p1a.P0A_SHA256,
                    },
                    "p1a_artifact":{
                        "path":str(P1A_MANIFEST),
                        "sha256":P1A_SHA256,
                    },
                    "p3_artifact":{
                        "path":str(p1a.P3_ARTIFACT),
                        "sha256":p1a.P3_SHA256,
                    },
                    "extractor_source":str(TOOL_REL),
                    "extractor_source_sha256":_sha(workspace/TOOL_REL),
                    "aggregated_input_manifest":[
                        {
                            "day":x.day.isoformat(),
                            "path":str(x.path),
                            "sha256":x.sha256,
                            "bytes":int(x.bytes),
                        } for x in agg_manifest
                    ],
                    "raw_manifest":list(raw_manifest),
                },
                "p3_support_contract_reproduced_exactly":True,
                "p3_support_contract":contract,
                "days":day_records,
                "forward_guards":dict(FORWARD_GUARDS),
                "scientific_interpretation":(
                    "all 36 preregistered DEV032 Wave-1 strategy representations "
                    "were materialized on exact frozen P3 T1 support; no model was "
                    "fit and no predictive or economic claim is made"
                ),
            })
            content=_canonical(manifest)
            mp=staging/MANIFEST_FILENAME
            with mp.open("xb") as h:
                h.write(content);h.flush();os.fsync(h.fileno())
            os.replace(staging,output)
        except BaseException:
            if staging.exists():
                shutil.rmtree(staging,ignore_errors=True)
            raise

    artifact=output/MANIFEST_FILENAME
    return ArtifactWriteResult(
        output,artifact,_sha(artifact),int(artifact.stat().st_size)
    )

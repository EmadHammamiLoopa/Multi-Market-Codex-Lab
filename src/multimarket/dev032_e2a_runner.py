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
from . import dev032_e2a_materialize as mat

EXPERIMENT_ID="DEV032-E2A"
DESIGN_VERSION="wave2-adaptive-refinement-materialization-v1"
STATUS_PASS="DEV032_E2_WAVE2_EXACT_SUPPORT_MATERIALIZED"

E1A_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev032_e1a_wave1_materialization_v1/"
    "DEV032_E1A_WAVE1_MATERIALIZATION.json"
)
E1A_SHA256="76e1c97e8b9a899bc27f3193316cbfc85efba8b0a7aa037d4c46fcc6a8be4a50"
E1A_BYTES=44689

RAW_ROOT=p1a.RAW_ROOT
TOOL_REL=Path("tools/dev032_e2a_raw_features.cpp")

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev032_e2a_wave2_materialization_v1"
)
MANIFEST_FILENAME="DEV032_E2A_WAVE2_MATERIALIZATION.json"

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
    "pca_fit_run":False,
    "svd_fit_run":False,
    "pnl_run":False,
}

class E2ARunnerError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class DaySupport:
    day:date
    ts:np.ndarray
    y:np.ndarray

@dataclass(frozen=True)
class DayBundle:
    day:date
    ts:np.ndarray
    y:np.ndarray
    refinements:dict[str,np.ndarray]
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
        raise E2ARunnerError("extractor_source_missing",str(source))
    cxx=shutil.which("g++")
    if cxx is None:
        raise E2ARunnerError("gpp_missing")
    build=Path(build_dir)
    build.mkdir(parents=True,exist_ok=True)
    exe=build/"dev032_e2a_raw_features"
    stamp=build/"dev032_e2a_raw_features.source.sha256"
    source_sha=_sha(source)
    if exe.is_file() and stamp.is_file() and stamp.read_text().strip()==source_sha:
        return exe
    p=subprocess.run(
        [cxx,"-std=c++17","-O3","-DNDEBUG",str(source),"-lz","-o",str(exe)],
        capture_output=True,text=True,
    )
    if p.returncode!=0:
        raise E2ARunnerError("extractor_compile_failed",p.stderr)
    stamp.write_text(source_sha+"\n")
    return exe

def _load_e1a_support_and_verify()->tuple[dict[date,DaySupport],dict[str,Any]]:
    if not E1A_ARTIFACT.is_file():
        raise E2ARunnerError("e1a_artifact_missing",str(E1A_ARTIFACT))
    if int(E1A_ARTIFACT.stat().st_size)!=E1A_BYTES or _sha(E1A_ARTIFACT)!=E1A_SHA256:
        raise E2ARunnerError("e1a_artifact_identity")
    m=json.loads(E1A_ARTIFACT.read_text(encoding="utf-8"))
    if m.get("status")!="DEV032_WAVE1_EXACT_SUPPORT_MATERIALIZED" or m.get("pass") is not True:
        raise E2ARunnerError("e1a_terminal_status")
    if int(m.get("rows",-1))!=1374 or int(m.get("long",-1))!=684 or int(m.get("short",-1))!=690:
        raise E2ARunnerError("e1a_campaign_counts")
    if any(m.get("forward_guards",{}).values()):
        raise E2ARunnerError("e1a_forward_guard")
    root=E1A_ARTIFACT.parent
    supports={}
    for rec in m.get("days",[]):
        d=date.fromisoformat(rec["day"])
        path=root/rec["file"]
        if not path.is_file():
            raise E2ARunnerError("e1a_day_file_missing",d.isoformat())
        if _sha(path)!=rec["file_sha256"] or int(path.stat().st_size)!=int(rec["file_bytes"]):
            raise E2ARunnerError("e1a_day_file_identity",d.isoformat())
        with path.open("r",encoding="utf-8",newline="") as h:
            r=csv.reader(h)
            try: header=next(r)
            except StopIteration as exc:
                raise E2ARunnerError("e1a_day_empty",d.isoformat()) from exc
            if tuple(header[:2])!=("local_timestamp_us","t1_label"):
                raise E2ARunnerError("e1a_day_header",d.isoformat())
            body=list(r)
        ts=np.asarray([int(x[0]) for x in body],dtype=np.int64)
        y=np.asarray([int(x[1]) for x in body],dtype=np.int8)
        if mat.support_sha256(ts)=="" or len(ts)!=int(rec["rows"]):
            raise E2ARunnerError("e1a_day_support_invalid",d.isoformat())
        if not np.all(np.isin(y,(0,1))):
            raise E2ARunnerError("e1a_day_labels_invalid",d.isoformat())
        # Cross-check E1A's own frozen support/label hashes using E1A hash functions.
        from . import dev032_e1a_materialize as e1mat
        if e1mat.support_sha256(ts)!=rec["support_sha256"]:
            raise E2ARunnerError("e1a_day_support_hash",d.isoformat())
        if e1mat.label_sha256(ts,y)!=rec["label_sha256"]:
            raise E2ARunnerError("e1a_day_label_hash",d.isoformat())
        supports[d]=DaySupport(d,ts,y)
    if tuple(supports)!=dd.HISTORICAL_DAYS:
        raise E2ARunnerError("e1a_day_calendar")
    return supports,m

def _verify_raw_manifest(e1a_manifest:Mapping[str,Any])->tuple[dict[str,Any],...]:
    frozen={date.fromisoformat(x["day"]):x for x in e1a_manifest["provenance"]["raw_manifest"]}
    if tuple(sorted(frozen))!=dd.HISTORICAL_DAYS:
        raise E2ARunnerError("e1a_raw_calendar")
    def one(d:date)->dict[str,Any]:
        p=RAW_ROOT/f"{d.isoformat()}.csv.gz"
        rec=frozen[d]
        if str(p)!=str(rec["path"]):
            raise E2ARunnerError("raw_path_mismatch",d.isoformat())
        if not p.is_file():
            raise E2ARunnerError("raw_file_missing",str(p))
        b=int(p.stat().st_size)
        h=_sha(p)
        if b!=int(rec["bytes"]):
            raise E2ARunnerError("raw_bytes_mismatch",d.isoformat())
        if h!=str(rec["sha256"]):
            raise E2ARunnerError("raw_sha256_mismatch",d.isoformat())
        return {"day":d.isoformat(),"path":str(p),"bytes":b,"sha256":h}
    by={}
    with ThreadPoolExecutor(max_workers=7) as pool:
        fs={pool.submit(one,d):d for d in dd.HISTORICAL_DAYS}
        for f in as_completed(fs):
            by[fs[f]]=f.result()
    return tuple(by[d] for d in dd.HISTORICAL_DAYS)

def _write_support(path:Path,ts:np.ndarray)->None:
    with Path(path).open("w",encoding="utf-8",newline="") as h:
        h.write("local_timestamp_us\n")
        for t in np.asarray(ts,dtype=np.int64).tolist():
            h.write(f"{int(t)}\n")

def _extract_day(*,exe:Path,sup:DaySupport,temp_dir:Path)->DayBundle:
    support=Path(temp_dir)/f"{sup.day.isoformat()}_support.csv"
    output=Path(temp_dir)/f"{sup.day.isoformat()}_e2a130.csv"
    _write_support(support,sup.ts)
    raw=RAW_ROOT/f"{sup.day.isoformat()}.csv.gz"
    p=subprocess.run([str(exe),str(raw),str(support),str(output)],capture_output=True,text=True)
    if p.returncode!=0:
        raise E2ARunnerError("raw_extractor_failed",f"{sup.day} rc={p.returncode} stderr={p.stderr}")
    try:
        vals=mat.parse_extractor_csv(output,sup.ts)
    except mat.E2AMaterializationError as exc:
        raise E2ARunnerError("raw_extractor_contract_failed",f"{sup.day} {exc.reason}: {exc}") from exc
    bundle=mat.assemble_bundle(sup.ts,sup.y,vals)
    return DayBundle(
        sup.day,bundle.support.timestamps_us,bundle.support.labels,
        {m.refinement_id:m.values for m in bundle.matrices},
        p.stderr.strip(),
    )

def materialize_days(
    *,
    workspace:Path,
    supports:Mapping[date,DaySupport],
    temp_dir:Path,
    max_workers:int=2,
)->dict[date,DayBundle]:
    exe=_compile_tool(workspace,Path(workspace)/".build"/"dev032_e2a")
    workers=max(1,min(int(max_workers),2))
    out={}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        fs={pool.submit(_extract_day,exe=exe,sup=supports[d],temp_dir=temp_dir):d for d in dd.HISTORICAL_DAYS}
        for f in as_completed(fs):
            out[fs[f]]=f.result()
    return {d:out[d] for d in dd.HISTORICAL_DAYS}

def _campaign(days:Mapping[date,DayBundle])->mat.MaterializedBundle:
    ts=np.concatenate([days[d].ts for d in dd.HISTORICAL_DAYS])
    y=np.concatenate([days[d].y for d in dd.HISTORICAL_DAYS])
    vals={
        rid:np.concatenate([days[d].refinements[rid] for d in dd.HISTORICAL_DAYS],axis=0)
        for rid in mat.REFINEMENT_IDS
    }
    return mat.assemble_bundle(ts,y,vals,require_full_campaign_counts=True)

def _write_day(path:Path,z:DayBundle)->None:
    header=["local_timestamp_us","t1_label"]
    for rid in mat.REFINEMENT_IDS:
        header.extend(mat.expected_feature_names(rid))
    with Path(path).open("w",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n");w.writerow(header)
        for i in range(len(z.ts)):
            row=[str(int(z.ts[i])),str(int(z.y[i]))]
            for rid in mat.REFINEMENT_IDS:
                row.extend(format(float(v),".17g") for v in z.refinements[rid][i])
            w.writerow(row)

def _canonical(x:Mapping[str,Any])->bytes:
    return (json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode("utf-8")

def run_e2a(
    *,
    workspace:Path,
    execution_commit:str,
    output_directory:Path=REAL_OUTPUT_DIRECTORY,
    require_canonical_output:bool=True,
    max_workers:int=2,
)->ArtifactWriteResult:
    if any(FORWARD_GUARDS.values()) or any(mat.FORWARD_GUARDS.values()):
        raise E2ARunnerError("runtime_guard_violation")
    mat.validate_registry()
    workspace=Path(workspace).resolve()
    output=Path(output_directory)
    if require_canonical_output and output!=REAL_OUTPUT_DIRECTORY:
        raise E2ARunnerError("noncanonical_output_directory")
    if not require_canonical_output and output==REAL_OUTPUT_DIRECTORY:
        raise E2ARunnerError("canonical_output_requires_real_mode")
    if output.exists() or output.is_symlink():
        raise E2ARunnerError("output_directory_already_exists")
    if (
        not isinstance(execution_commit,str) or len(execution_commit)!=40
        or any(c not in "0123456789abcdef" for c in execution_commit)
    ):
        raise E2ARunnerError("execution_commit_must_be_full_sha")

    supports,e1a=_load_e1a_support_and_verify()
    raw_manifest=_verify_raw_manifest(e1a)

    with tempfile.TemporaryDirectory(prefix="dev032_e2a_") as td:
        days=materialize_days(
            workspace=workspace,supports=supports,temp_dir=Path(td),
            max_workers=max_workers,
        )
        full=_campaign(days)

        staging=output.parent/f".{output.name}.part-{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise E2ARunnerError("staging_directory_preexists")
        staging.mkdir(parents=True)
        try:
            day_records=[]
            for d in dd.HISTORICAL_DAYS:
                z=days[d]
                p=staging/f"{d.isoformat()}_DEV032_E2A.csv"
                _write_day(p,z)
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
                    "refinement_matrix_sha256":{
                        rid:mat.matrix_sha256(rid,z.refinements[rid])
                        for rid in mat.REFINEMENT_IDS
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
                    "parent_anchors":14,
                    "adaptive_refinements":10,
                    "raw_materialized_columns":130,
                    "pca_fit_run":False,
                    "svd_fit_run":False,
                },
                "parent_e1a":{
                    "path":str(E1A_ARTIFACT),
                    "sha256":E1A_SHA256,
                    "bytes":E1A_BYTES,
                },
                "formula_freeze":{
                    "path":"docs/DEV032_E2A_FORMULAS.md",
                    "pca_components":5,
                    "svd_components":5,
                    "svd_random_state":20260902,
                },
                "provenance":{
                    "extractor_source":str(TOOL_REL),
                    "extractor_source_sha256":_sha(workspace/TOOL_REL),
                    "raw_manifest":list(raw_manifest),
                },
                "days":day_records,
                "forward_guards":dict(FORWARD_GUARDS),
                "scientific_interpretation":(
                    "ten preregistered adaptive Wave-2 refinement representations "
                    "were materialized on exact frozen DEV032-E1A support; no PCA/SVD "
                    "or predictive model was fit and no predictive/economic claim is made"
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
    return ArtifactWriteResult(output,artifact,_sha(artifact),int(artifact.stat().st_size))

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
from . import dev032_e1a_materialize as e1mat
from . import dev033_g2a_materialize as mat

EXPERIMENT_ID="DEV033-G2A"
DESIGN_VERSION="layered-raw-temporal-materialization-v1"
STATUS_PASS="DEV033_G2_LAYERED_TEMPORAL_EXACT_SUPPORT_MATERIALIZED"

E1A_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev032_e1a_wave1_materialization_v1/"
    "DEV032_E1A_WAVE1_MATERIALIZATION.json"
)
E1A_SHA256="76e1c97e8b9a899bc27f3193316cbfc85efba8b0a7aa037d4c46fcc6a8be4a50"
E1A_BYTES=44689

RAW_ROOT=p1a.RAW_ROOT
TOOL_REL=Path("tools/dev033_g2a_raw_temporal.cpp")

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev033_g2a_layered_temporal_materialization_v1"
)
MANIFEST_FILENAME="DEV033_G2A_LAYERED_TEMPORAL_MATERIALIZATION.json"

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
    "null_run":False,
    "pnl_run":False,
}

class G2ARunnerError(RuntimeError):
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
    values:dict[str,np.ndarray]
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
    source=Path(workspace).resolve()/TOOL_REL
    if not source.is_file():
        raise G2ARunnerError("extractor_source_missing",str(source))
    cxx=shutil.which("g++")
    if cxx is None:
        raise G2ARunnerError("gpp_missing")
    build=Path(build_dir);build.mkdir(parents=True,exist_ok=True)
    exe=build/"dev033_g2a_raw_temporal"
    stamp=build/"dev033_g2a_raw_temporal.source.sha256"
    source_sha=_sha(source)
    if exe.is_file() and stamp.is_file() and stamp.read_text().strip()==source_sha:
        return exe
    p=subprocess.run(
        [cxx,"-std=c++17","-O3","-DNDEBUG",str(source),"-lz","-o",str(exe)],
        capture_output=True,text=True,
    )
    if p.returncode!=0:
        raise G2ARunnerError("extractor_compile_failed",p.stderr)
    stamp.write_text(source_sha+"\n",encoding="utf-8")
    return exe

def _load_e1a_support()->tuple[dict[date,DaySupport],dict[str,Any]]:
    if not E1A_ARTIFACT.is_file():
        raise G2ARunnerError("e1a_artifact_missing")
    if int(E1A_ARTIFACT.stat().st_size)!=E1A_BYTES or _sha(E1A_ARTIFACT)!=E1A_SHA256:
        raise G2ARunnerError("e1a_artifact_identity")
    m=json.loads(E1A_ARTIFACT.read_text(encoding="utf-8"))
    if m.get("status")!="DEV032_WAVE1_EXACT_SUPPORT_MATERIALIZED" or m.get("pass") is not True:
        raise G2ARunnerError("e1a_terminal_status")
    if (m.get("rows"),m.get("long"),m.get("short"))!=(1374,684,690):
        raise G2ARunnerError("e1a_campaign_counts")
    if any(m.get("forward_guards",{}).values()):
        raise G2ARunnerError("e1a_forward_guard")
    root=E1A_ARTIFACT.parent
    out={}
    for rec in m["days"]:
        d=date.fromisoformat(rec["day"])
        p=root/rec["file"]
        if not p.is_file() or int(p.stat().st_size)!=int(rec["file_bytes"]) or _sha(p)!=rec["file_sha256"]:
            raise G2ARunnerError("e1a_day_identity",d.isoformat())
        with p.open("r",encoding="utf-8",newline="") as h:
            r=csv.reader(h);header=next(r);rows=list(r)
        if tuple(header[:2])!=("local_timestamp_us","t1_label"):
            raise G2ARunnerError("e1a_day_header",d.isoformat())
        ts=np.asarray([int(x[0]) for x in rows],dtype=np.int64)
        y=np.asarray([int(x[1]) for x in rows],dtype=np.int8)
        if e1mat.support_sha256(ts)!=rec["support_sha256"]:
            raise G2ARunnerError("e1a_support_hash",d.isoformat())
        if e1mat.label_sha256(ts,y)!=rec["label_sha256"]:
            raise G2ARunnerError("e1a_label_hash",d.isoformat())
        out[d]=DaySupport(d,ts,y)
    if tuple(out)!=dd.HISTORICAL_DAYS:
        raise G2ARunnerError("e1a_calendar")
    return out,m

def _verify_raw_manifest(e1a:Mapping[str,Any])->tuple[dict[str,Any],...]:
    frozen={date.fromisoformat(x["day"]):x for x in e1a["provenance"]["raw_manifest"]}
    if tuple(sorted(frozen))!=dd.HISTORICAL_DAYS:
        raise G2ARunnerError("raw_calendar")
    def one(d:date):
        p=RAW_ROOT/f"{d.isoformat()}.csv.gz";rec=frozen[d]
        if str(p)!=str(rec["path"]) or not p.is_file():
            raise G2ARunnerError("raw_path",d.isoformat())
        b=int(p.stat().st_size);h=_sha(p)
        if b!=int(rec["bytes"]) or h!=rec["sha256"]:
            raise G2ARunnerError("raw_identity",d.isoformat())
        return {"day":d.isoformat(),"path":str(p),"bytes":b,"sha256":h}
    by={}
    with ThreadPoolExecutor(max_workers=7) as pool:
        fs={pool.submit(one,d):d for d in dd.HISTORICAL_DAYS}
        for f in as_completed(fs):by[fs[f]]=f.result()
    return tuple(by[d] for d in dd.HISTORICAL_DAYS)

def _write_support(path:Path,ts:np.ndarray):
    with path.open("w",encoding="utf-8") as h:
        h.write("local_timestamp_us\n")
        for t in ts.tolist():h.write(f"{int(t)}\n")

def _extract_day(exe:Path,sup:DaySupport,temp:Path)->DayBundle:
    sp=temp/f"{sup.day}_support.csv";op=temp/f"{sup.day}_g2a.csv"
    _write_support(sp,sup.ts)
    raw=RAW_ROOT/f"{sup.day.isoformat()}.csv.gz"
    p=subprocess.run([str(exe),str(raw),str(sp),str(op)],capture_output=True,text=True)
    if p.returncode!=0:
        raise G2ARunnerError("extractor_failed",f"{sup.day} rc={p.returncode} {p.stderr}")
    vals=mat.parse_extractor_csv(op,sup.ts)
    return DayBundle(sup.day,sup.ts,sup.y,vals,p.stderr.strip())

def _write_day(path:Path,z:DayBundle):
    header=["local_timestamp_us","t1_label"]
    for cid in mat.CANDIDATE_IDS:header.extend(mat.expected_feature_names(cid))
    with path.open("w",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n");w.writerow(header)
        for i in range(len(z.ts)):
            row=[str(int(z.ts[i])),str(int(z.y[i]))]
            for cid in mat.CANDIDATE_IDS:
                row.extend(format(float(v),".17g") for v in z.values[cid][i])
            w.writerow(row)

def _canonical(x:Mapping[str,Any])->bytes:
    return (json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

def run_g2a(
    *,
    workspace:Path,
    execution_commit:str,
    output_directory:Path=REAL_OUTPUT_DIRECTORY,
    require_canonical_output:bool=True,
    max_workers:int=2,
)->ArtifactWriteResult:
    if any(FORWARD_GUARDS.values()):
        raise G2ARunnerError("runtime_guard_violation")
    output=Path(output_directory)
    if require_canonical_output and output!=REAL_OUTPUT_DIRECTORY:
        raise G2ARunnerError("noncanonical_output_directory")
    if not require_canonical_output and output==REAL_OUTPUT_DIRECTORY:
        raise G2ARunnerError("canonical_output_requires_real_mode")
    if output.exists() or output.is_symlink():
        raise G2ARunnerError("output_directory_already_exists")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise G2ARunnerError("execution_commit")

    supports,e1a=_load_e1a_support()
    raw_manifest=_verify_raw_manifest(e1a)
    exe=_compile_tool(Path(workspace),Path(workspace)/".build"/"dev033_g2a")

    with tempfile.TemporaryDirectory(prefix="dev033_g2a_") as td:
        temp=Path(td);days={}
        workers=max(1,min(int(max_workers),2))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            fs={pool.submit(_extract_day,exe,supports[d],temp):d for d in dd.HISTORICAL_DAYS}
            for f in as_completed(fs):days[fs[f]]=f.result()
        days={d:days[d] for d in dd.HISTORICAL_DAYS}

        ts=np.concatenate([days[d].ts for d in dd.HISTORICAL_DAYS])
        y=np.concatenate([days[d].y for d in dd.HISTORICAL_DAYS])
        values={
            cid:np.concatenate([days[d].values[cid] for d in dd.HISTORICAL_DAYS],axis=0)
            for cid in mat.CANDIDATE_IDS
        }
        full=mat.validate_full_campaign(ts,y,values)

        staging=output.parent/f".{output.name}.part-{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise G2ARunnerError("staging_preexists")
        staging.mkdir(parents=True)
        try:
            day_records=[]
            for d in dd.HISTORICAL_DAYS:
                z=days[d];p=staging/f"{d.isoformat()}_DEV033_G2A.csv"
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
                    "extractor_stderr":z.raw_stderr,
                    "candidate_matrix_sha256":{
                        cid:mat.matrix_sha256(cid,z.values[cid])
                        for cid in mat.CANDIDATE_IDS
                    },
                })

            manifest={
                "experiment_id":EXPERIMENT_ID,
                "design_version":DESIGN_VERSION,
                "status":STATUS_PASS,
                "pass":True,
                "execution_commit":execution_commit,
                "rows":1374,"long":684,"short":690,
                "support_sha256":mat.support_sha256(ts),
                "label_sha256":mat.label_sha256(ts,y),
                "candidate_count":24,
                "total_materialized_columns":mat.TOTAL_COLUMNS,
                "candidate_registry":mat.public_registry(),
                "candidate_matrix_sha256":{
                    cid:mat.matrix_sha256(cid,full[cid].values)
                    for cid in mat.CANDIDATE_IDS
                },
                "parent_direction_success":{
                    "experiment_id":"DEV030-P3",
                    "configuration":"A/120s/16bp/32s/PRICE/S1",
                    "artifact":"/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/DEV030_P3_CAMPAIGN1_RESULT.json",
                    "artifact_sha256":"f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e",
                },
                "parent_e1a_support":{
                    "path":str(E1A_ARTIFACT),
                    "sha256":E1A_SHA256,
                    "bytes":E1A_BYTES,
                },
                "formula_freeze":"docs/DEV033_G2A_FORMULAS.md",
                "provenance":{
                    "extractor_source":str(TOOL_REL),
                    "extractor_source_sha256":_sha(Path(workspace)/TOOL_REL),
                    "raw_manifest":list(raw_manifest),
                },
                "days":day_records,
                "forward_guards":dict(FORWARD_GUARDS),
                "scientific_interpretation":(
                    "24 preregistered temporal microstructure additions were materialized "
                    "on exact frozen P3/E1A support; no predictive model, metric, null, "
                    "forward holdout, or economic evaluation was run"
                ),
            }
            mp=staging/MANIFEST_FILENAME
            content=_canonical(manifest)
            with mp.open("xb") as h:
                h.write(content);h.flush();os.fsync(h.fileno())
            os.replace(staging,output)
        except BaseException:
            if staging.exists():shutil.rmtree(staging,ignore_errors=True)
            raise

    artifact=output/MANIFEST_FILENAME
    return ArtifactWriteResult(output,artifact,_sha(artifact),int(artifact.stat().st_size))

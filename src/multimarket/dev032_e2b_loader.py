from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev032_e1a_materialize as e1mat
from . import dev032_e1b_loader as e1loader
from . import dev032_e1b_screen_core as e1core
from . import dev032_e2a_materialize as e2mat

E2A_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev032_e2a_wave2_materialization_v1/"
    "DEV032_E2A_WAVE2_MATERIALIZATION.json"
)
E2A_SHA256="3c26614f576af4e52b2d52f237e2e939cd79a988238022076ddcdbf57d06b89c"
E2A_BYTES=15261

E1B_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev032_e1b_r1_broad_predictive_screen_v1/"
    "DEV032_E1B_BROAD_PREDICTIVE_SCREEN_RESULT.json"
)
E1B_SHA256="af223d3f97b85ae1c929f81b3ec71e892477b9b26e719638acb05ae153578b95"
E1B_BYTES=287823

REFINEMENT_IDS=e2mat.REFINEMENT_IDS
PARENT_BY_REFINEMENT=e2mat.PARENT_BY_REFINEMENT
ACTIVE_PARENT_IDS=("P07","P09","P13","P17","P21","P32","P35")

class E2BLoaderError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class LoadedEvidence:
    e1b_manifest:dict[str,Any]
    e2a_manifest:dict[str,Any]
    e1_evidence:e1loader.LoadedEvidence
    refinement_days:dict[str,dict[date,e1core.DayMatrix]]

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _load_json(path:Path,sha:str,size:int)->dict[str,Any]:
    if not path.is_file(): raise E2BLoaderError("artifact_missing",str(path))
    if int(path.stat().st_size)!=size: raise E2BLoaderError("artifact_bytes_mismatch",str(path))
    if _sha(path)!=sha: raise E2BLoaderError("artifact_sha256_mismatch",str(path))
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise E2BLoaderError("artifact_not_object",str(path))
    return x

def _expected_header()->list[str]:
    h=["local_timestamp_us","t1_label"]
    for rid in REFINEMENT_IDS:
        h.extend(e2mat.expected_feature_names(rid))
    return h

def _offsets()->dict[str,tuple[int,int]]:
    out={};pos=2
    for rid in REFINEMENT_IDS:
        n=e2mat.FEATURE_COUNTS[rid]
        out[rid]=(pos,pos+n);pos+=n
    if pos!=132: raise E2BLoaderError("e2a_header_width")
    return out

def load_evidence()->LoadedEvidence:
    e1=e1loader.load_evidence()
    e1b=_load_json(E1B_ARTIFACT,E1B_SHA256,E1B_BYTES)
    e2a=_load_json(E2A_ARTIFACT,E2A_SHA256,E2A_BYTES)

    if e1b.get("experiment_id")!="DEV032-E1B": raise E2BLoaderError("e1b_experiment_id")
    if e1b.get("execution_commit")!="6cf6757aeaed07e899973353585d9b031230f4b6":
        raise E2BLoaderError("e1b_execution_commit")
    if len(e1b.get("leaderboard",[]))!=34: raise E2BLoaderError("e1b_leaderboard_count")
    if e1b.get("strong_screening_survivors")!=[]: raise E2BLoaderError("e1b_survivor_state")

    if e2a.get("experiment_id")!="DEV032-E2A": raise E2BLoaderError("e2a_experiment_id")
    if e2a.get("status")!="DEV032_E2_WAVE2_EXACT_SUPPORT_MATERIALIZED" or e2a.get("pass") is not True:
        raise E2BLoaderError("e2a_terminal_status")
    if (e2a.get("rows"),e2a.get("long"),e2a.get("short"))!=(1374,684,690):
        raise E2BLoaderError("e2a_counts")
    if any(e2a.get("forward_guards",{}).values()): raise E2BLoaderError("e2a_forward_guard")

    refs=e2a.get("refinements",[])
    if [r.get("refinement_id") for r in refs]!=list(REFINEMENT_IDS):
        raise E2BLoaderError("e2a_refinement_order")
    for r in refs:
        rid=r["refinement_id"]
        if r.get("parent_candidate_id")!=PARENT_BY_REFINEMENT[rid]:
            raise E2BLoaderError("e2a_parent_mapping",rid)

    days=e2a.get("days",[])
    if [date.fromisoformat(x["day"]) for x in days] != list(dd.HISTORICAL_DAYS):
        raise E2BLoaderError("e2a_calendar")

    hdr=_expected_header();off=_offsets()
    by={rid:{} for rid in REFINEMENT_IDS}
    root=E2A_ARTIFACT.parent

    for rec in days:
        d=date.fromisoformat(rec["day"])
        p=root/rec["file"]
        if not p.is_file() or int(p.stat().st_size)!=int(rec["file_bytes"]) or _sha(p)!=rec["file_sha256"]:
            raise E2BLoaderError("e2a_day_identity",d.isoformat())
        with p.open("r",encoding="utf-8",newline="") as f:
            r=csv.reader(f)
            try: actual=next(r)
            except StopIteration as exc: raise E2BLoaderError("e2a_day_empty",d.isoformat()) from exc
            rows=list(r)
        if actual!=hdr: raise E2BLoaderError("e2a_day_header",d.isoformat())
        if len(rows)!=rec["rows"]: raise E2BLoaderError("e2a_day_rows",d.isoformat())
        ts=np.asarray([int(z[0]) for z in rows],dtype=np.int64)
        y=np.asarray([int(z[1]) for z in rows],dtype=np.int8)

        base=e1.strategy_days["S00"][d]
        if not np.array_equal(ts,base.timestamps_us): raise E2BLoaderError("e1a_e2a_support",d.isoformat())
        if not np.array_equal(y,base.labels): raise E2BLoaderError("e1a_e2a_labels",d.isoformat())

        for rid,(a,b) in off.items():
            x=np.asarray([[float(v) for v in row[a:b]] for row in rows],dtype=np.float64)
            e2mat.validate_matrix(rid,x,rows=len(ts))
            if e2mat.matrix_sha256(rid,x)!=rec["refinement_matrix_sha256"][rid]:
                raise E2BLoaderError("e2a_matrix_hash",f"{d}:{rid}")
            by[rid][d]=e1core.DayMatrix(d,ts,y,x)

    return LoadedEvidence(e1b,e2a,e1,by)

def baseline_days(e:LoadedEvidence)->dict[date,e1core.DayMatrix]:
    return e1loader.baseline_days(e.e1_evidence)

def parent_days(e:LoadedEvidence,parent_id:str)->dict[date,e1core.DayMatrix]:
    if parent_id not in ACTIVE_PARENT_IDS:
        raise E2BLoaderError("unknown_parent",parent_id)
    return e1loader.primary_candidate_days(e.e1_evidence,parent_id)

def refinement_raw_days(e:LoadedEvidence,rid:str)->dict[date,e1core.DayMatrix]:
    if rid not in REFINEMENT_IDS:
        raise E2BLoaderError("unknown_refinement",rid)
    return e.refinement_days[rid]

def ordinary_refinement_days(e:LoadedEvidence,rid:str)->dict[date,e1core.DayMatrix]:
    if rid in ("E2R05","E2R06"):
        raise E2BLoaderError("transform_refinement_requires_pipeline",rid)
    extra=refinement_raw_days(e,rid)
    base=baseline_days(e)
    out={}
    for d in dd.HISTORICAL_DAYS:
        a=base[d];b=extra[d]
        if not np.array_equal(a.timestamps_us,b.timestamps_us) or not np.array_equal(a.labels,b.labels):
            raise E2BLoaderError("refinement_support_mismatch",rid)
        out[d]=e1core.DayMatrix(d,a.timestamps_us,a.labels,np.concatenate([a.values,b.values],axis=1))
    return out

def outer_folds():
    return e1loader.outer_folds()

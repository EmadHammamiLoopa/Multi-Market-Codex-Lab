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
from . import dev030_p6_m2_direction as p6
from . import dev033_g2a_materialize as g2a

G2A_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev033_g2a_layered_temporal_materialization_v1/"
    "DEV033_G2A_LAYERED_TEMPORAL_MATERIALIZATION.json"
)
G2A_SHA256="3336c70912bd0de0928a9fded04f3d7153fcd2df46dd2ed3d1b942a2c98922c6"
G2A_BYTES=104750

P3_ARTIFACT=p6.P3_ARTIFACT_PATH
P3_SHA256=p6.P3_ARTIFACT_SHA256

class G2BLoaderError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class DayLayer:
    day:date
    timestamps_us:np.ndarray
    labels:np.ndarray
    values_by_candidate:dict[str,np.ndarray]

@dataclass(frozen=True)
class LoadedG2B:
    g2a_manifest:dict[str,Any]
    p3_payload:dict[str,Any]
    p3_per_day:dict[date,dd.CandidateDayDataset]
    layer_days:dict[date,DayLayer]

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _verified_json(path:Path,sha:str,size:int|None=None)->dict[str,Any]:
    if not path.is_file():
        raise G2BLoaderError("artifact_missing",str(path))
    if size is not None and int(path.stat().st_size)!=int(size):
        raise G2BLoaderError("artifact_bytes",str(path))
    if _sha(path)!=sha:
        raise G2BLoaderError("artifact_sha256",str(path))
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict):
        raise G2BLoaderError("artifact_not_object",str(path))
    return x

def _load_p3_days()->dict[date,dd.CandidateDayDataset]:
    loaded=tuple(dd.load_authorized_days())
    if tuple(x.day for x in loaded)!=dd.HISTORICAL_DAYS:
        raise G2BLoaderError("historical_day_calendar")
    per={}
    for day in loaded:
        dataset=dd.build_candidate_day_dataset(
            day,
            p6.SELECTED_KEY,
            p6.SELECTED_SPEC,
        )
        p6.validate_selected_candidate(dataset)
        per[day.day]=dataset
    if tuple(per)!=dd.HISTORICAL_DAYS:
        raise G2BLoaderError("p3_day_order")
    return per

def _expected_header():
    h=["local_timestamp_us","t1_label"]
    for cid in g2a.CANDIDATE_IDS:
        h.extend(g2a.expected_feature_names(cid))
    return h

def _offsets():
    out={};pos=2
    for cid in g2a.CANDIDATE_IDS:
        n=g2a.BY_ID[cid]["feature_count"]
        out[cid]=(pos,pos+n);pos+=n
    if pos!=2522:
        raise G2BLoaderError("g2a_width_contract")
    return out

def _p3_day_rows(dataset:dd.CandidateDayDataset):
    x,y,ts=p6._t1_rows(dataset)
    return np.asarray(x,dtype=np.float64),np.asarray(y,dtype=np.int8),np.asarray(ts,dtype=np.int64)

def load_g2b()->LoadedG2B:
    g=_verified_json(G2A_ARTIFACT,G2A_SHA256,G2A_BYTES)
    p3=_verified_json(P3_ARTIFACT,P3_SHA256,None)

    if g.get("experiment_id")!="DEV033-G2A":
        raise G2BLoaderError("g2a_experiment_id")
    if g.get("status")!="DEV033_G2_LAYERED_TEMPORAL_EXACT_SUPPORT_MATERIALIZED" or g.get("pass") is not True:
        raise G2BLoaderError("g2a_terminal_status")
    if (g.get("rows"),g.get("long"),g.get("short"))!=(1374,684,690):
        raise G2BLoaderError("g2a_counts")
    if g.get("candidate_count")!=24 or g.get("total_materialized_columns")!=2520:
        raise G2BLoaderError("g2a_registry_counts")
    if any(g.get("forward_guards",{}).values()):
        raise G2BLoaderError("g2a_forward_guard")
    if g.get("candidate_registry")!=g2a.public_registry():
        raise G2BLoaderError("g2a_registry")

    per=_load_p3_days()
    header=_expected_header();off=_offsets();root=G2A_ARTIFACT.parent
    layer_days={}
    for rec in g["days"]:
        d=date.fromisoformat(rec["day"])
        p=root/rec["file"]
        if not p.is_file() or int(p.stat().st_size)!=int(rec["file_bytes"]) or _sha(p)!=rec["file_sha256"]:
            raise G2BLoaderError("g2a_day_identity",d.isoformat())
        rows=[]
        with p.open("r",encoding="utf-8",newline="") as h:
            r=csv.reader(h)
            try: actual=next(r)
            except StopIteration as exc: raise G2BLoaderError("g2a_day_empty",d.isoformat()) from exc
            if actual!=header: raise G2BLoaderError("g2a_day_header",d.isoformat())
            rows=list(r)
        if len(rows)!=int(rec["rows"]):
            raise G2BLoaderError("g2a_day_rows",d.isoformat())
        ts=np.asarray([int(z[0]) for z in rows],dtype=np.int64)
        y=np.asarray([int(z[1]) for z in rows],dtype=np.int8)
        bx,by,bts=_p3_day_rows(per[d])
        if not np.array_equal(ts,bts) or not np.array_equal(y,by):
            raise G2BLoaderError("g2a_p3_support_label_mismatch",d.isoformat())
        vals={}
        for cid,(a,b) in off.items():
            x=np.asarray([[float(v) for v in row[a:b]] for row in rows],dtype=np.float64)
            g2a.validate_matrix(cid,x,rows=len(ts))
            if g2a.matrix_sha256(cid,x)!=rec["candidate_matrix_sha256"][cid]:
                raise G2BLoaderError("g2a_matrix_hash",f"{d}:{cid}")
            vals[cid]=x
        layer_days[d]=DayLayer(d,ts,y,vals)
    if tuple(layer_days)!=dd.HISTORICAL_DAYS:
        raise G2BLoaderError("g2a_calendar")
    return LoadedG2B(g,p3,per,layer_days)

def base_day_matrix(e:LoadedG2B,d:date):
    return _p3_day_rows(e.p3_per_day[d])

def candidate_day_matrix(e:LoadedG2B,d:date,cid:str):
    if cid not in g2a.CANDIDATE_IDS:
        raise G2BLoaderError("unknown_candidate",cid)
    bx,y,ts=base_day_matrix(e,d)
    layer=e.layer_days[d]
    if not np.array_equal(ts,layer.timestamps_us) or not np.array_equal(y,layer.labels):
        raise G2BLoaderError("candidate_day_alignment",f"{d}:{cid}")
    return np.concatenate([bx,layer.values_by_candidate[cid]],axis=1),y,ts

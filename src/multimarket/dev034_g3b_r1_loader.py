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
from . import dev030_p4_touch_composition as p4
from . import dev034_g3a_core as g3

G3A_R1_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev034_g3a_r1_common_support_context_v1/"
    "DEV034_G3A_R1_COMMON_SUPPORT_CONTEXT.json"
)
G3A_R1_SHA256="43f4460d6990846218f3d0618a261d3852d3a198a50420ff05afbc97c832425e"
G3A_R1_BYTES=28890

P3_ARTIFACT=p6.P3_ARTIFACT_PATH
P3_SHA256=p6.P3_ARTIFACT_SHA256

EXPECTED_SUPPORT_SHA="caa61e84281061d00e4244e4f9b30ed2096e5acb95df9906aa7de0f28750ab75"
EXPECTED_LABEL_SHA="fcb1b8f6c5f7994ca8c611cb3381146f401be7623ef36ae316a9a2e477a83385"
EXPECTED_FULL_R_SHA="b98239fdf22de77a476c7d4b13d4a677c06de101faedd42cbf8e11da0b145763"

class G3BR1LoaderError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class DayContext:
    day:date
    timestamps_us:np.ndarray
    labels:np.ndarray
    full_r:np.ndarray

@dataclass(frozen=True)
class LoadedG3BR1:
    g3a_r1_manifest:dict[str,Any]
    p3_payload:dict[str,Any]
    p3_per_day:dict[date,dd.CandidateDayDataset]
    contexts:dict[date,DayContext]

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _verified_json(path:Path,sha:str,size:int|None=None)->dict[str,Any]:
    if not path.is_file():
        raise G3BR1LoaderError("artifact_missing",str(path))
    if size is not None and int(path.stat().st_size)!=int(size):
        raise G3BR1LoaderError("artifact_bytes",str(path))
    if _sha(path)!=sha:
        raise G3BR1LoaderError("artifact_sha256",str(path))
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict):
        raise G3BR1LoaderError("artifact_not_object",str(path))
    return x

def _load_p3_days()->dict[date,dd.CandidateDayDataset]:
    loaded=tuple(dd.load_authorized_days())
    if tuple(x.day for x in loaded)!=dd.HISTORICAL_DAYS:
        raise G3BR1LoaderError("historical_day_calendar")
    per={}
    for day in loaded:
        dataset=dd.build_candidate_day(
            day,
            target=p6.SELECTED_TARGET,
            window_seconds=p6.SELECTED_WINDOW_SECONDS,
            block=p6.SELECTED_BLOCK,
        )
        p6.validate_selected_candidate(dataset)
        per[day.day]=dataset
    if tuple(per)!=dd.HISTORICAL_DAYS:
        raise G3BR1LoaderError("p3_day_order")
    return per

def _p3_rows(dataset):
    x,y,ts=p6._t1_rows(dataset)
    return (
        np.asarray(x,dtype=np.float64),
        np.asarray(y,dtype=np.int8),
        np.asarray(ts,dtype=np.int64),
    )

def _subset_exact(original_ts,original_y,base_x,target_ts,target_y):
    pos=np.searchsorted(original_ts,target_ts)
    if np.any(pos<0) or np.any(pos>=len(original_ts)):
        raise G3BR1LoaderError("common_support_not_subset")
    if not np.array_equal(original_ts[pos],target_ts):
        raise G3BR1LoaderError("common_support_timestamp_mismatch")
    if not np.array_equal(original_y[pos],target_y):
        raise G3BR1LoaderError("common_support_label_mismatch")
    out=base_x[pos]
    if out.shape!=(len(target_ts),23) or not np.all(np.isfinite(out)):
        raise G3BR1LoaderError("common_base_shape")
    return out

def load_g3b_r1()->LoadedG3BR1:
    g=_verified_json(G3A_R1_ARTIFACT,G3A_R1_SHA256,G3A_R1_BYTES)
    p3=_verified_json(P3_ARTIFACT,P3_SHA256,None)
    p4.validate_p3_selected_survivor(p3)

    if g.get("experiment_id")!="DEV034-G3A-R1":
        raise G3BR1LoaderError("g3a_r1_experiment_id")
    if g.get("status")!="DEV034_G3A_R1_COMMON_SUPPORT_MATERIALIZED" or g.get("pass") is not True:
        raise G3BR1LoaderError("g3a_r1_terminal_status")
    if g.get("candidate_count")!=16 or g.get("candidate_registry")!=g3.public_registry():
        raise G3BR1LoaderError("g3a_r1_registry")
    if any(g.get("forward_guards",{}).values()):
        raise G3BR1LoaderError("g3a_r1_forward_guard")

    common=g.get("common_support",{})
    if (common.get("rows"),common.get("long"),common.get("short"))!=(1341,665,676):
        raise G3BR1LoaderError("g3a_r1_common_counts")
    if common.get("support_sha256")!=EXPECTED_SUPPORT_SHA:
        raise G3BR1LoaderError("g3a_r1_support_sha")
    if common.get("label_sha256")!=EXPECTED_LABEL_SHA:
        raise G3BR1LoaderError("g3a_r1_label_sha")
    if common.get("full_r_matrix_sha256")!=EXPECTED_FULL_R_SHA:
        raise G3BR1LoaderError("g3a_r1_full_r_sha")

    per=_load_p3_days()
    contexts={}
    root=G3A_R1_ARTIFACT.parent
    expected_header=["local_timestamp_us","t1_label",*g3.R_FEATURE_NAMES]

    for rec in g.get("days",[]):
        d=date.fromisoformat(rec["day"])
        p=root/rec["file"]
        if not p.is_file() or p.stat().st_size!=int(rec["file_bytes"]) or _sha(p)!=rec["file_sha256"]:
            raise G3BR1LoaderError("g3a_r1_day_identity",d.isoformat())
        with p.open("r",encoding="utf-8",newline="") as h:
            r=csv.reader(h)
            try:
                header=next(r)
            except StopIteration as exc:
                raise G3BR1LoaderError("g3a_r1_day_empty",d.isoformat()) from exc
            if header!=expected_header:
                raise G3BR1LoaderError("g3a_r1_day_header",d.isoformat())
            rows=list(r)
        if len(rows)!=int(rec["eligible_rows"]):
            raise G3BR1LoaderError("g3a_r1_day_rows",d.isoformat())
        ts=np.asarray([int(z[0]) for z in rows],dtype=np.int64)
        y=np.asarray([int(z[1]) for z in rows],dtype=np.int8)
        full=np.asarray([[float(v) for v in z[2:]] for z in rows],dtype=np.float64)
        if full.shape!=(len(ts),22) or not np.all(np.isfinite(full)):
            raise G3BR1LoaderError("g3a_r1_day_full_r",d.isoformat())
        if g3.support_sha256(ts)!=rec["support_sha256"]:
            raise G3BR1LoaderError("g3a_r1_day_support_sha",d.isoformat())
        if g3.label_sha256(ts,y)!=rec["label_sha256"]:
            raise G3BR1LoaderError("g3a_r1_day_label_sha",d.isoformat())
        if g3.matrix_sha256("FULL_R",full)!=rec["full_r_matrix_sha256"]:
            raise G3BR1LoaderError("g3a_r1_day_full_r_sha",d.isoformat())
        bx,by,bts=_p3_rows(per[d])
        _subset_exact(bts,by,bx,ts,y)
        contexts[d]=DayContext(d,ts,y,full)

    if tuple(contexts)!=dd.HISTORICAL_DAYS:
        raise G3BR1LoaderError("g3a_r1_calendar")

    ts=np.concatenate([contexts[d].timestamps_us for d in dd.HISTORICAL_DAYS])
    y=np.concatenate([contexts[d].labels for d in dd.HISTORICAL_DAYS])
    full=np.concatenate([contexts[d].full_r for d in dd.HISTORICAL_DAYS])
    if g3.support_sha256(ts)!=EXPECTED_SUPPORT_SHA:
        raise G3BR1LoaderError("campaign_support_sha")
    if g3.label_sha256(ts,y)!=EXPECTED_LABEL_SHA:
        raise G3BR1LoaderError("campaign_label_sha")
    if g3.matrix_sha256("FULL_R",full)!=EXPECTED_FULL_R_SHA:
        raise G3BR1LoaderError("campaign_full_r_sha")

    return LoadedG3BR1(g,p3,per,contexts)

def base_day_matrix(e:LoadedG3BR1,d:date):
    bx,by,bts=_p3_rows(e.p3_per_day[d])
    ctx=e.contexts[d]
    common=_subset_exact(bts,by,bx,ctx.timestamps_us,ctx.labels)
    return common,ctx.labels,ctx.timestamps_us

def candidate_day_matrix(e:LoadedG3BR1,d:date,cid:str):
    if cid not in g3.CANDIDATE_IDS:
        raise G3BR1LoaderError("unknown_candidate",cid)
    bx,y,ts=base_day_matrix(e,d)
    ctx=e.contexts[d]
    z=g3.candidate_matrix(ctx.full_r,cid)
    expected_hash=e.g3a_r1_manifest["days"][dd.HISTORICAL_DAYS.index(d)]["candidate_matrix_sha256"][cid]
    if g3.matrix_sha256(cid,z)!=expected_hash:
        raise G3BR1LoaderError("candidate_matrix_hash",f"{d}:{cid}")
    return np.concatenate([bx,z],axis=1),y,ts


def base_feature_names(e:LoadedG3BR1)->tuple[str,...]:
    names=None
    for d in dd.HISTORICAL_DAYS:
        current=tuple(str(v) for v in e.p3_per_day[d].s1_feature_names)
        if len(current)!=23:
            raise G3BR1LoaderError("base_feature_name_count",d.isoformat())
        if names is None:
            names=current
        elif current!=names:
            raise G3BR1LoaderError("base_feature_name_order_drift",d.isoformat())
    if names is None:
        raise G3BR1LoaderError("base_feature_names_missing")
    return names

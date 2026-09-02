from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from . import codex_exp004_p1 as exp004
from . import dev030_direction_dataset as dd
from . import dev030_p4_touch_composition as p4
from . import dev034_g3a_r1_core as r1

P4_ARTIFACT=p4.REAL_OUTPUT_DIRECTORY/p4.ARTIFACT_FILENAME
P4_SHA256="8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16"

G3B_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev034_g3b_r1_common_support_screen_v1/"
    "DEV034_G3B_R1_COMMON_SUPPORT_SCREEN_RESULT.json"
)
G3B_SHA256="16200a1595d9472fe488740c0ab63e013b65824298ef1cb0b8856322416a8167"
G3B_BYTES=873268

COMMON_SUPPORT_SHA="dc89f3012341bd771591693b03af00b86f64f95aa4f7db4e9dc65b7e0e7f7b3f"

class C1LoaderError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class DayData:
    day:date
    t2:p4.T2DayDataset
    y3:np.ndarray
    r22:np.ndarray
    p3_x:np.ndarray
    btc45_x:np.ndarray
    direction_y:np.ndarray
    direction_mask:np.ndarray

@dataclass(frozen=True)
class LoadedC1:
    p4_payload:dict[str,Any]
    g3b_payload:dict[str,Any]
    per_day:dict[date,DayData]

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _json(path:Path,sha:str,size:int|None=None):
    if not path.is_file(): raise C1LoaderError("artifact_missing",str(path))
    if size is not None and path.stat().st_size!=size: raise C1LoaderError("artifact_bytes",str(path))
    if _sha(path)!=sha: raise C1LoaderError("artifact_sha",str(path))
    return json.loads(path.read_text(encoding="utf-8"))

def _three_class(candidate,original_t2,keep):
    all_y=p4.three_class_labels(candidate,original_t2)
    return np.asarray(all_y,dtype=np.int8)[keep]

def load_c1()->LoadedC1:
    p4_payload=_json(P4_ARTIFACT,P4_SHA256)
    if p4_payload.get("status")!="FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE":
        raise C1LoaderError("p4_status")
    if p4_payload.get("t2",{}).get("eligible_for_composition") is not True:
        raise C1LoaderError("p4_t2_not_eligible")

    g3b=_json(G3B_ARTIFACT,G3B_SHA256,G3B_BYTES)
    if g3b.get("layer_survivors")!=["G3C16"] or g3b.get("advanced_layers")!=["G3C16"]:
        raise C1LoaderError("g3c16_identity")

    raw_days=tuple(dd.load_authorized_days())
    if tuple(x.day for x in raw_days)!=dd.HISTORICAL_DAYS:
        raise C1LoaderError("calendar")

    out={}
    campaign_ts=[]
    for raw in raw_days:
        d=raw.day
        cand=dd.build_candidate_day(
            raw,target=p4.SELECTED_TARGET,
            window_seconds=p4.SELECTED_WINDOW_SECONDS,
            block=p4.SELECTED_BLOCK,
        )
        original=p4.build_t2_day(cand)
        raw_ts=np.asarray(raw.ts,dtype=np.int64)
        pos=np.searchsorted(raw_ts,original.timestamps_us)
        if not np.array_equal(raw_ts[pos],original.timestamps_us):
            raise C1LoaderError("raw_alignment",d.isoformat())
        spread=exp004._spread(raw)

        keep=[]
        rrows=[]
        for j,current in enumerate(pos.tolist()):
            reason=r1._reason(raw,int(current),spread)
            if reason=="VALID":
                v=np.asarray(exp004._r_features(raw,int(current),spread),dtype=np.float64)
                if v.shape!=(22,) or not np.all(np.isfinite(v)):
                    raise C1LoaderError("r_vector",d.isoformat())
                keep.append(j);rrows.append(v)

        keep=np.asarray(keep,dtype=np.int64)
        if len(keep)!=1407:
            raise C1LoaderError("day_common_support",f"{d}:{len(keep)}")

        ts=np.asarray(original.timestamps_us,dtype=np.int64)[keep]
        y2=np.asarray(original.labels,dtype=np.int8)[keep]
        s0=np.asarray(original.s0_values,dtype=np.float64)[keep]
        s1=np.asarray(original.s1_values,dtype=np.float64)[keep]
        r22=np.vstack(rrows)
        y3=_three_class(cand,original,keep)
        touch=(y2==p4.T2_TOUCH)
        direction_y=(y3[touch]-1).astype(np.int8)

        filtered=p4.T2DayDataset(
            day=d,timestamps_us=ts,labels=y2,
            s0_values=s0,s1_values=s1,
            s0_feature_names=original.s0_feature_names,
            s1_feature_names=original.s1_feature_names,
            valid_mask_on_candidate=np.ones(len(ts),dtype=bool),
            support_sha256=dd.support_sha256(ts),
            touch_count=int(np.sum(touch)),
            none_count=int(np.sum(~touch)),
        )
        out[d]=DayData(
            d,filtered,y3,r22,s1,np.concatenate([s1,r22],axis=1),
            direction_y,touch
        )
        campaign_ts.append(ts)

    allts=np.concatenate(campaign_ts)
    if dd.support_sha256(allts)!=COMMON_SUPPORT_SHA:
        raise C1LoaderError("campaign_support_sha")
    if tuple(out)!=dd.HISTORICAL_DAYS:
        raise C1LoaderError("day_order")
    return LoadedC1(p4_payload,g3b,out)

def direction_per_day(e:LoadedC1,which:str):
    if which not in ("P3","BTC45"): raise C1LoaderError("direction_kind")
    out={}
    for d in dd.HISTORICAL_DAYS:
        z=e.per_day[d]
        x=z.p3_x if which=="P3" else z.btc45_x
        out[d]=(x[z.direction_mask],z.direction_y,z.t2.timestamps_us[z.direction_mask])
    return out

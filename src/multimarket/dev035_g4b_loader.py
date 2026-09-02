from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev034_g3a_core as g3
from . import dev034_g3b_r1_loader as g3loader
from .v23_phase0dl_score import _load_day, L0_NAMES, L1_EXTRA_NAMES, L2_EXTRA_NAMES

G3B_R1_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev034_g3b_r1_common_support_screen_v1/"
    "DEV034_G3B_R1_COMMON_SUPPORT_SCREEN_RESULT.json"
)
G3B_R1_SHA256="16200a1595d9472fe488740c0ab63e013b65824298ef1cb0b8856322416a8167"
G3B_R1_BYTES=873268

ETH_ROOT=Path(
    "/home/emadh/Multi-Market/evidence/v23/phase0dl_features250/ETHUSDT"
)

ETH_SHA256={
    "2026-01-01":"036f300bbe31f1ccbe4ec52362060870cf6c644a44c8f8b5fd30e79749a39359",
    "2026-02-01":"cbac5c6b624930774bd60f3a50383f2551303e3ba5de3648275a362b69e5a643",
    "2026-03-01":"006aaa3879fb3051bb241f73cd8b1e1af6e647ea95577e5f2d004fb7cce05187",
    "2026-04-01":"54dfa0cf9cb45e869c531db6e082bbb09fa0d819973fd29642be1b68c5691256",
    "2026-05-01":"a7e96f52a91f303296ff579d8f72ec206aedb1b1d5227c7472db641b5a5c9fa5",
    "2026-06-01":"7753c43fed7574520ac8583e413a57116779aa636ca6fb71026ddf8d86420c1c",
    "2026-07-01":"38e8853ba2a777293fa0cd645af5c709cdf9b4faeeaa57941cd37021d675b57d",
}

EXPECTED_SUPPORT_SHA=g3loader.EXPECTED_SUPPORT_SHA
EXPECTED_LABEL_SHA=g3loader.EXPECTED_LABEL_SHA

CANDIDATE_BLOCK={
    "G4C01":"L0",
    "G4C02":"L1",
    "G4C03":"L2",
}

CANDIDATE_WIDTH={
    "G4C01":56,
    "G4C02":71,
    "G4C03":88,
}

ETH_BLOCK_NAMES={
    "L0":tuple(L0_NAMES),
    "L1":tuple(L0_NAMES)+tuple(L1_EXTRA_NAMES),
    "L2":tuple(L0_NAMES)+tuple(L1_EXTRA_NAMES)+tuple(L2_EXTRA_NAMES),
}

class G4BLoaderError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class LoadedG4B:
    g3b_payload:dict[str,Any]
    g3_loaded:g3loader.LoadedG3BR1
    eth_days:dict[date,Any]

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def _verified_json(path:Path,sha:str,size:int)->dict[str,Any]:
    if not path.is_file():
        raise G4BLoaderError("artifact_missing",str(path))
    if int(path.stat().st_size)!=int(size):
        raise G4BLoaderError("artifact_bytes",str(path))
    if _sha(path)!=sha:
        raise G4BLoaderError("artifact_sha256",str(path))
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict):
        raise G4BLoaderError("artifact_not_object",str(path))
    return x

def load_g4b()->LoadedG4B:
    g3b=_verified_json(G3B_R1_ARTIFACT,G3B_R1_SHA256,G3B_R1_BYTES)

    if g3b.get("experiment_id")!="DEV034-G3B-R1":
        raise G4BLoaderError("g3b_experiment_id")
    if g3b.get("layer_survivors")!=["G3C16"]:
        raise G4BLoaderError("g3b_survivor_identity")
    if g3b.get("advanced_layers")!=["G3C16"]:
        raise G4BLoaderError("g3b_advanced_identity")

    row=next(
        (z for z in g3b.get("leaderboard",[]) if z.get("candidate_id")=="G3C16"),
        None,
    )
    if row is None or row.get("status")!="G3_LAYER_SURVIVOR":
        raise G4BLoaderError("g3c16_status")
    if int(row.get("feature_count",-1))!=45:
        raise G4BLoaderError("g3c16_feature_count")

    common=g3b.get("common_support",{})
    if (common.get("rows"),common.get("long"),common.get("short"))!=(1341,665,676):
        raise G4BLoaderError("g3b_common_counts")
    if common.get("support_sha256")!=EXPECTED_SUPPORT_SHA:
        raise G4BLoaderError("g3b_support_sha")
    if common.get("label_sha256")!=EXPECTED_LABEL_SHA:
        raise G4BLoaderError("g3b_label_sha")

    g3e=g3loader.load_g3b_r1()

    eth={}
    for d in dd.HISTORICAL_DAYS:
        day=d.isoformat()
        p=ETH_ROOT/f"{day}_FEATURES250.csv"
        if not p.is_file():
            raise G4BLoaderError("eth_file_missing",day)
        if _sha(p)!=ETH_SHA256[day]:
            raise G4BLoaderError("eth_file_sha",day)
        x=_load_day(p,d)

        base_x,y,ts=base_day_matrix_from_g3(g3e,d)
        pos=np.searchsorted(np.asarray(x.ts,dtype=np.int64),ts)
        if np.any(pos<0) or np.any(pos>=len(x.ts)):
            raise G4BLoaderError("eth_alignment_bounds",day)
        if not np.array_equal(np.asarray(x.ts,dtype=np.int64)[pos],ts):
            raise G4BLoaderError("eth_alignment_timestamp",day)

        for block in ("L0","L1","L2"):
            valid=np.asarray(x.valid[block],dtype=bool)[pos]
            z=np.asarray(x.X[block][pos],dtype=np.float64)
            if not np.all(valid):
                raise G4BLoaderError("eth_support_loss",f"{day}:{block}")
            if not np.all(np.isfinite(z)):
                raise G4BLoaderError("eth_nonfinite",f"{day}:{block}")

        eth[d]=x

    if tuple(eth)!=dd.HISTORICAL_DAYS:
        raise G4BLoaderError("eth_calendar")

    return LoadedG4B(g3b,g3e,eth)

def base_feature_names(e:LoadedG4B)->tuple[str,...]:
    p3=tuple(g3loader.base_feature_names(e.g3_loaded))
    r=tuple(g3.R_FEATURE_NAMES)
    out=p3+r
    if len(out)!=45 or len(set(out))!=45:
        # Prefix R names in serialization if natural names collide with P3.
        out=p3+tuple(f"BTC_R::{name}" for name in r)
    if len(out)!=45 or len(set(out))!=45:
        raise G4BLoaderError("base_feature_names")
    return out

def base_day_matrix_from_g3(g3e:g3loader.LoadedG3BR1,d:date):
    p3,y,ts=g3loader.base_day_matrix(g3e,d)
    full=np.asarray(g3e.contexts[d].full_r,dtype=np.float64)
    if full.shape!=(len(y),22):
        raise G4BLoaderError("g3_full_r_shape",d.isoformat())
    x=np.concatenate([p3,full],axis=1)
    if x.shape!=(len(y),45) or not np.all(np.isfinite(x)):
        raise G4BLoaderError("btc45_shape",d.isoformat())
    return x,y,ts

def base_day_matrix(e:LoadedG4B,d:date):
    return base_day_matrix_from_g3(e.g3_loaded,d)

def candidate_feature_names(e:LoadedG4B,cid:str)->tuple[str,...]:
    if cid not in CANDIDATE_BLOCK:
        raise G4BLoaderError("unknown_candidate",cid)
    block=CANDIDATE_BLOCK[cid]
    return base_feature_names(e)+tuple(f"ETH::{n}" for n in ETH_BLOCK_NAMES[block])

def candidate_day_matrix(e:LoadedG4B,d:date,cid:str):
    if cid not in CANDIDATE_BLOCK:
        raise G4BLoaderError("unknown_candidate",cid)
    bx,y,ts=base_day_matrix(e,d)
    eth=e.eth_days[d]
    pos=np.searchsorted(np.asarray(eth.ts,dtype=np.int64),ts)
    block=CANDIDATE_BLOCK[cid]
    valid=np.asarray(eth.valid[block],dtype=bool)[pos]
    z=np.asarray(eth.X[block][pos],dtype=np.float64)
    if not np.all(valid):
        raise G4BLoaderError("candidate_support_loss",f"{d}:{cid}")
    x=np.concatenate([bx,z],axis=1)
    if x.shape!=(len(y),CANDIDATE_WIDTH[cid]) or not np.all(np.isfinite(x)):
        raise G4BLoaderError("candidate_shape",f"{d}:{cid}:{x.shape}")
    return x,y,ts

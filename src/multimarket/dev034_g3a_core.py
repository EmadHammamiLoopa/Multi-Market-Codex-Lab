from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import struct
from typing import Any, Mapping, Sequence

import numpy as np

from . import codex_exp004_p1 as exp004
from . import dev030_direction_dataset as dd
from . import dev030_p6_m2_direction as p6

EXPERIMENT_ID="DEV034-G3A"
DESIGN_VERSION="opportunity-volatility-context-materialization-v1"

R_FEATURE_NAMES=tuple(exp004.R_FEATURE_NAMES)
if len(R_FEATURE_NAMES)!=22:
    raise RuntimeError("frozen R feature count drift")

SIGNED_RETURNS=tuple(f"ret_{m}m_bps" for m in exp004.RETURN_LOOKBACK_MIN)
ABS_RETURNS=tuple(f"abs_ret_{m}m_bps" for m in exp004.RETURN_LOOKBACK_MIN)
RV_NAMES=tuple(f"rv_{m}m_bps" for m in exp004.RV_WINDOWS_MIN)
SPREAD_NAMES=("spread_bps",)+tuple(f"spread_mean_{m}m_bps" for m in exp004.SPREAD_MEAN_MIN)
RANGE_NAMES=tuple(f"range_{m}m_bps" for m in exp004.RANGE_WINDOWS_MIN)
RANGE_POSITION_NAMES=tuple(f"range_position_{m}m" for m in exp004.RANGE_WINDOWS_MIN)

REGISTRY=(
    ("G3C01","EXACT_EXP024_RV30",("rv_30m_bps",)),
    ("G3C02","RV_TERM_STRUCTURE",RV_NAMES),
    ("G3C03","ABS_RETURN_TERM_STRUCTURE",ABS_RETURNS),
    ("G3C04","SIGNED_RETURN_TERM_STRUCTURE",SIGNED_RETURNS),
    ("G3C05","SPREAD_REGIME",SPREAD_NAMES),
    ("G3C06","RANGE_TERM_STRUCTURE",RANGE_NAMES),
    ("G3C07","RANGE_POSITION_TERM_STRUCTURE",RANGE_POSITION_NAMES),
    ("G3C08","SHORT_VOLATILITY_STATE",(
        "abs_ret_1m_bps","abs_ret_3m_bps","abs_ret_5m_bps","rv_5m_bps","range_5m_bps",
    )),
    ("G3C09","MEDIUM_VOLATILITY_STATE",(
        "abs_ret_5m_bps","abs_ret_10m_bps","rv_15m_bps","range_15m_bps",
    )),
    ("G3C10","LONG_VOLATILITY_STATE",(
        "abs_ret_10m_bps","abs_ret_30m_bps","rv_30m_bps","range_30m_bps",
    )),
    ("G3C11","SIGNED_PLUS_ABSOLUTE_RETURN_STATE",SIGNED_RETURNS+ABS_RETURNS),
    ("G3C12","VOLATILITY_PLUS_RANGE_STATE",RV_NAMES+RANGE_NAMES),
    ("G3C13","OPPORTUNITY_REGIME_CORE",(
        "rv_30m_bps","abs_ret_30m_bps","range_30m_bps","spread_mean_5m_bps",
    )),
    ("G3C14","MAGNITUDE_CONTEXT",ABS_RETURNS+RV_NAMES+RANGE_NAMES),
    ("G3C15","UNSIGNED_FULL_R_CONTEXT",tuple(n for n in R_FEATURE_NAMES if n not in SIGNED_RETURNS)),
    ("G3C16","FULL_FROZEN_R_CONTEXT",R_FEATURE_NAMES),
)

CANDIDATE_IDS=tuple(x[0] for x in REGISTRY)
BY_ID={
    cid:{
        "candidate_id":cid,
        "name":name,
        "feature_names":tuple(features),
        "feature_count":len(features),
    }
    for cid,name,features in REGISTRY
}
R_POS={name:i for i,name in enumerate(R_FEATURE_NAMES)}

if CANDIDATE_IDS!=tuple(f"G3C{i:02d}" for i in range(1,17)):
    raise RuntimeError("candidate order drift")
if len(set(CANDIDATE_IDS))!=16:
    raise RuntimeError("candidate id duplication")
for cid in CANDIDATE_IDS:
    names=BY_ID[cid]["feature_names"]
    if not names or len(set(names))!=len(names):
        raise RuntimeError(f"invalid candidate feature list: {cid}")
    missing=[n for n in names if n not in R_POS]
    if missing:
        raise RuntimeError(f"unknown R feature in {cid}: {missing}")

FORWARD_GUARDS={
    "aug01_new_analysis_opened":False,
    "aug30_reused":False,
    "sep01_or_later_opened":False,
    "railway_opened":False,
    "archive_bucket_opened":False,
    "abundant_love_opened":False,
    "downloads_or_acquisition_run":False,
    "direction_model_fit":False,
    "direction_metric_scored":False,
    "temporal_null_run":False,
    "pnl_run":False,
}

class G3AError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class DayContext:
    day:date
    timestamps_us:np.ndarray
    labels:np.ndarray
    full_r:np.ndarray

def public_registry()->list[dict[str,Any]]:
    return [
        {
            "candidate_id":cid,
            "name":BY_ID[cid]["name"],
            "feature_names":list(BY_ID[cid]["feature_names"]),
            "feature_count":int(BY_ID[cid]["feature_count"]),
        }
        for cid in CANDIDATE_IDS
    ]

def support_sha256(ts:np.ndarray)->str:
    return dd.support_sha256(np.asarray(ts,dtype=np.int64))

def label_sha256(ts:np.ndarray,y:np.ndarray)->str:
    return p6.label_sha256(np.asarray(ts,dtype=np.int64),np.asarray(y,dtype=np.int8))

def matrix_sha256(namespace:str,x:np.ndarray)->str:
    a=np.asarray(x,dtype=np.float64)
    if a.ndim!=2 or not np.all(np.isfinite(a)):
        raise G3AError("matrix_invalid",namespace)
    h=hashlib.sha256(b"DEV034-G3A-MATRIX-V1\0")
    h.update(namespace.encode("ascii"))
    h.update(struct.pack(">QQ",int(a.shape[0]),int(a.shape[1])))
    h.update(a.astype(">f8",copy=False).tobytes(order="C"))
    return h.hexdigest()

def candidate_matrix(full_r:np.ndarray,cid:str)->np.ndarray:
    if cid not in BY_ID:
        raise G3AError("unknown_candidate",cid)
    a=np.asarray(full_r,dtype=np.float64)
    if a.ndim!=2 or a.shape[1]!=len(R_FEATURE_NAMES):
        raise G3AError("full_r_shape",cid)
    cols=[R_POS[n] for n in BY_ID[cid]["feature_names"]]
    out=a[:,cols]
    if out.shape!=(len(a),BY_ID[cid]["feature_count"]) or not np.all(np.isfinite(out)):
        raise G3AError("candidate_matrix_invalid",cid)
    return out

def _decision_row_indices(day:Any,timestamps_us:np.ndarray)->np.ndarray:
    day_ts=np.asarray(day.ts,dtype=np.int64)
    target=np.asarray(timestamps_us,dtype=np.int64)
    pos=np.searchsorted(day_ts,target)
    if np.any(pos<0) or np.any(pos>=len(day_ts)):
        raise G3AError("timestamp_out_of_day")
    if not np.array_equal(day_ts[pos],target):
        raise G3AError("timestamp_not_exact_250ms_grid")
    if np.any(pos % exp004.DECISION_STEP_ROWS != 0):
        raise G3AError("timestamp_not_exact_minute_grid")
    return pos.astype(np.int64,copy=False)

def extract_full_r(day:Any,timestamps_us:np.ndarray)->np.ndarray:
    idx=_decision_row_indices(day,timestamps_us)
    spread=exp004._spread(day)
    out=np.empty((len(idx),len(R_FEATURE_NAMES)),dtype=np.float64)
    for j,current in enumerate(idx.tolist()):
        values=exp004._r_features(day,int(current),spread)
        if values is None:
            raise G3AError("r_context_invalid_on_p3_support",f"{day.day}:{int(timestamps_us[j])}")
        values=np.asarray(values,dtype=np.float64)
        if values.shape!=(len(R_FEATURE_NAMES),) or not np.all(np.isfinite(values)):
            raise G3AError("r_context_nonfinite_or_width",f"{day.day}:{int(timestamps_us[j])}")
        out[j]=values
    return out

def materialize_day(day:Any,dataset:dd.CandidateDayDataset)->DayContext:
    p6.validate_selected_candidate(dataset)
    _,y,ts=p6._t1_rows(dataset)
    ts=np.asarray(ts,dtype=np.int64)
    y=np.asarray(y,dtype=np.int8)
    full=extract_full_r(day,ts)
    if len(ts)!=len(y) or len(ts)!=len(full):
        raise G3AError("support_length_mismatch",str(day.day))
    return DayContext(day.day,ts,y,full)

def validate_registry_contract()->None:
    if len(R_FEATURE_NAMES)!=22 or len(CANDIDATE_IDS)!=16:
        raise G3AError("registry_count")
    expected={
        "G3C01":1,"G3C02":3,"G3C03":5,"G3C04":5,"G3C05":3,"G3C06":3,
        "G3C07":3,"G3C08":5,"G3C09":4,"G3C10":4,"G3C11":10,"G3C12":6,
        "G3C13":4,"G3C14":11,"G3C15":17,"G3C16":22,
    }
    actual={cid:BY_ID[cid]["feature_count"] for cid in CANDIDATE_IDS}
    if actual!=expected:
        raise G3AError("registry_widths",str(actual))

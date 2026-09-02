from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from typing import Any, Mapping

import numpy as np

EXPERIMENT_ID="DEV033-G2A"
DESIGN_VERSION="layered-raw-temporal-materialization-v1"

FAMILY_CHANNELS={
    "T01":("l1_queue_imbalance",),
    "T02":("depth_imbalance_l1","depth_imbalance_l5","depth_imbalance_l10","depth_imbalance_l20"),
    "T03":("microdisp_l1_bps","microdisp_l5_bps","microdisp_l10_bps","microdisp_l20_bps"),
    "T04":tuple(f"mlofi_rank_{i:02d}" for i in range(1,11)),
    "T05":("qtyshare_BI","qtyshare_BD","qtyshare_BR","qtyshare_BP","qtyshare_AI","qtyshare_AD","qtyshare_AR","qtyshare_AP"),
    "T06":("countshare_BI","countshare_BD","countshare_BR","countshare_BP","countshare_AI","countshare_AD","countshare_AR","countshare_AP"),
    "T07":("bid_slope_l10","ask_slope_l10","slope_diff_l10","near_far_depth_diff","mean_bid_gap_l10","mean_ask_gap_l10"),
    "T08":("bid_depth_recovery","ask_depth_recovery","depth_recovery_diff","spread_recovery"),
}
WINDOWS=(8,16,32)

CANDIDATE_IDS=tuple(f"G2C{i:02d}" for i in range(1,25))

def candidate_registry()->tuple[dict[str,Any],...]:
    rows=[]
    n=0
    for window in WINDOWS:
        for family,channels in FAMILY_CHANNELS.items():
            n+=1
            cid=f"G2C{n:02d}"
            rows.append({
                "candidate_id":cid,
                "family_id":family,
                "window_seconds":window,
                "channels":list(channels),
                "feature_count":window*len(channels),
            })
    if tuple(r["candidate_id"] for r in rows)!=CANDIDATE_IDS:
        raise RuntimeError("candidate_registry_order")
    return tuple(rows)

REGISTRY=candidate_registry()
BY_ID={r["candidate_id"]:r for r in REGISTRY}

def expected_feature_names(candidate_id:str)->tuple[str,...]:
    if candidate_id not in BY_ID:
        raise KeyError(candidate_id)
    r=BY_ID[candidate_id]
    out=[]
    for k in range(r["window_seconds"]):
        for channel in r["channels"]:
            out.append(f"{candidate_id}__bin{k:02d}__{channel}")
    return tuple(out)

def total_materialized_columns()->int:
    return sum(int(r["feature_count"]) for r in REGISTRY)

TOTAL_COLUMNS=total_materialized_columns()

@dataclass(frozen=True)
class CandidateMatrix:
    candidate_id:str
    feature_names:tuple[str,...]
    values:np.ndarray

class G2AMaterializationError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

def validate_support(timestamps_us:Any,labels:Any)->tuple[np.ndarray,np.ndarray]:
    ts=np.asarray(timestamps_us)
    y=np.asarray(labels)
    if ts.ndim!=1 or ts.dtype.kind not in "iu":
        raise G2AMaterializationError("support_timestamps")
    if y.ndim!=1 or y.dtype.kind not in "iu":
        raise G2AMaterializationError("support_labels")
    if len(ts)==0 or len(ts)!=len(y):
        raise G2AMaterializationError("support_length")
    ts=ts.astype(np.int64,copy=False)
    y=y.astype(np.int8,copy=False)
    if np.any(np.diff(ts)<=0):
        raise G2AMaterializationError("support_chronology")
    if not np.all(np.isin(y,(0,1))):
        raise G2AMaterializationError("support_binary_labels")
    return ts,y

def validate_matrix(candidate_id:str,values:Any,*,rows:int)->CandidateMatrix:
    if candidate_id not in BY_ID:
        raise G2AMaterializationError("unknown_candidate",candidate_id)
    x=np.asarray(values,dtype=np.float64)
    names=expected_feature_names(candidate_id)
    if x.shape!=(rows,len(names)):
        raise G2AMaterializationError(
            "candidate_matrix_shape",
            f"{candidate_id} expected={(rows,len(names))} actual={x.shape}",
        )
    if not np.all(np.isfinite(x)):
        raise G2AMaterializationError("candidate_matrix_nonfinite",candidate_id)
    return CandidateMatrix(candidate_id,names,x)

def support_sha256(timestamps_us:Any)->str:
    ts=np.asarray(timestamps_us,dtype=np.int64)
    h=hashlib.sha256(b"DEV033-G2A-SUPPORT-V1\0")
    h.update(struct.pack(">Q",len(ts)))
    for t in ts.tolist():
        h.update(struct.pack(">q",int(t)))
    return h.hexdigest()

def label_sha256(timestamps_us:Any,labels:Any)->str:
    ts=np.asarray(timestamps_us,dtype=np.int64)
    y=np.asarray(labels,dtype=np.int8)
    h=hashlib.sha256(b"DEV033-G2A-LABELS-V1\0")
    h.update(struct.pack(">Q",len(ts)))
    for t,v in zip(ts.tolist(),y.tolist(),strict=True):
        h.update(struct.pack(">qb",int(t),int(v)))
    return h.hexdigest()

def matrix_sha256(candidate_id:str,values:Any)->str:
    x=np.asarray(values,dtype=np.float64)
    h=hashlib.sha256(b"DEV033-G2A-MATRIX-V1\0")
    h.update(candidate_id.encode("ascii"))
    h.update(struct.pack(">QQ",x.shape[0],x.shape[1]))
    h.update(x.astype(">f8",copy=False).tobytes(order="C"))
    return h.hexdigest()

def validate_full_campaign(
    timestamps_us:Any,
    labels:Any,
    values_by_candidate:Mapping[str,Any],
)->dict[str,CandidateMatrix]:
    ts,y=validate_support(timestamps_us,labels)
    if (len(ts),int(np.sum(y==1)),int(np.sum(y==0)))!=(1374,684,690):
        raise G2AMaterializationError("campaign_counts")
    if tuple(values_by_candidate)!=CANDIDATE_IDS:
        raise G2AMaterializationError("candidate_membership_order")
    return {
        cid:validate_matrix(cid,values_by_candidate[cid],rows=len(ts))
        for cid in CANDIDATE_IDS
    }

assert len(REGISTRY)==24
assert TOTAL_COLUMNS==(
    8+32+32+80+64+64+48+32+
    16+64+64+160+128+128+96+64+
    32+128+128+320+256+256+192+128
)

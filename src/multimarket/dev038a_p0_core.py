from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Mapping

import numpy as np

from . import dev030_direction_dataset as dd

TARGET=next(t for t in dd.FROZEN_TARGETS if t.target_id=="A")
CANDIDATES=(
    ("A0",32,"PRICE"),
    ("A1",32,"PRICE_BOOK"),
    ("A2",32,"PRICE_BOOK_FLOW"),
    ("A3",32,"PRICE_BOOK_FLOW_DYNAMICS"),
    ("A4",60,"PRICE_BOOK_FLOW_DYNAMICS"),
)

@dataclass(frozen=True)
class CandidateAuditDay:
    candidate_id:str
    day:date
    valid_timestamps_us:np.ndarray
    valid_labels:np.ndarray
    feature_count:int
    raw_lookback_ns:int

def _t2_valid(dataset:dd.CandidateDayDataset):
    n=len(dataset.decision_timestamps_us)
    common=np.asarray(dataset.common_valid,dtype=bool)
    future=np.asarray(dataset.target_future_boundary_valid,dtype=bool)
    valid=np.zeros(n,dtype=bool)
    labels=np.full(n,-1,dtype=np.int8)
    for i,record in enumerate(dataset.target_records):
        mapped,_=dd.map_t1_record(record)
        if record["target_valid"] is True and future[i]:
            valid[i]=True
            labels[i]=1 if mapped in (dd.T1_LONG,dd.T1_SHORT) else 0
    mask=common & valid
    ts=np.asarray(dataset.decision_timestamps_us,dtype=np.int64)[mask]
    y=labels[mask]
    if len(ts)==0 or len(ts)!=len(y) or not np.all(np.isin(y,(0,1))):
        raise RuntimeError("invalid_t2_support")
    return ts,y

def build_audit_day(candidate_id:str,dataset:dd.CandidateDayDataset):
    spec={cid:(w,b) for cid,w,b in CANDIDATES}[candidate_id]
    w,b=spec
    if dataset.key.target!=TARGET or dataset.key.window_seconds!=w or dataset.key.block!=b:
        raise RuntimeError("candidate_identity")
    ts,y=_t2_valid(dataset)
    feature_count=len(dataset.s1_feature_names)
    raw_lookback_ns=(
        int(w)*1_000_000_000
        + int(dd.sf.block_internal_lookback_ns(b))
    )
    return CandidateAuditDay(candidate_id,dataset.day,ts,y,feature_count,raw_lookback_ns)

def common_support(per_candidate:Mapping[str,Mapping[date,CandidateAuditDay]]):
    if tuple(per_candidate)!=tuple(cid for cid,_,_ in CANDIDATES):
        raise RuntimeError("candidate_order")
    out={}
    for day in dd.HISTORICAL_DAYS:
        sets=[set(map(int,per_candidate[cid][day].valid_timestamps_us.tolist())) for cid,_,_ in CANDIDATES]
        common=sorted(set.intersection(*sets))
        ts=np.asarray(common,dtype=np.int64)
        if len(ts)==0:
            raise RuntimeError("empty_common_support")
        labels=None
        for cid,_,_ in CANDIDATES:
            z=per_candidate[cid][day]
            pos={int(t):i for i,t in enumerate(z.valid_timestamps_us.tolist())}
            yy=np.asarray([z.valid_labels[pos[int(t)]] for t in ts],dtype=np.int8)
            if labels is None:
                labels=yy
            elif not np.array_equal(labels,yy):
                raise RuntimeError("label_mismatch_on_common_support")
        out[day]=(ts,labels)
    return out

def support_sha(ts):
    return dd.support_sha256(np.asarray(ts,dtype=np.int64))

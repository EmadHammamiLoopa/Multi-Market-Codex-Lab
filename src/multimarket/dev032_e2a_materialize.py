from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

EXPERIMENT_ID="DEV032-E2A"
DESIGN_VERSION="wave2-adaptive-refinement-materialization-v1"

EXPECTED_TOTAL_ROWS=1374
EXPECTED_LONG=684
EXPECTED_SHORT=690

REFINEMENT_IDS=tuple(f"E2R{i:02d}" for i in range(1,11))
FEATURE_COUNTS={
    "E2R01":14,
    "E2R02":6,
    "E2R03":10,
    "E2R04":6,
    "E2R05":20,
    "E2R06":40,
    "E2R07":6,
    "E2R08":8,
    "E2R09":8,
    "E2R10":12,
}
PARENT_BY_REFINEMENT={
    "E2R01":"P07",
    "E2R02":"P07",
    "E2R03":"P09",
    "E2R04":"P09",
    "E2R05":"P13",
    "E2R06":"P13",
    "E2R07":"P17",
    "E2R08":"P21",
    "E2R09":"P35",
    "E2R10":"P32",
}
TOTAL_RAW_COLUMNS=sum(FEATURE_COUNTS.values())

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

class E2AMaterializationError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class SupportLabels:
    timestamps_us:np.ndarray
    labels:np.ndarray

@dataclass(frozen=True)
class RefinementMatrix:
    refinement_id:str
    feature_names:tuple[str,...]
    values:np.ndarray

@dataclass(frozen=True)
class MaterializedBundle:
    support:SupportLabels
    matrices:tuple[RefinementMatrix,...]

def validate_registry()->None:
    if tuple(FEATURE_COUNTS)!=REFINEMENT_IDS:
        raise E2AMaterializationError("refinement_registry_order")
    if tuple(PARENT_BY_REFINEMENT)!=REFINEMENT_IDS:
        raise E2AMaterializationError("parent_registry_order")
    if len(FEATURE_COUNTS)!=10 or TOTAL_RAW_COLUMNS!=130:
        raise E2AMaterializationError("refinement_registry_count")
    if any(v<=0 for v in FEATURE_COUNTS.values()):
        raise E2AMaterializationError("refinement_feature_count")

def expected_feature_names(rid:str)->tuple[str,...]:
    if rid not in FEATURE_COUNTS:
        raise E2AMaterializationError("unknown_refinement_id",rid)
    return tuple(f"{rid}__f{i:02d}" for i in range(FEATURE_COUNTS[rid]))

def _support(timestamps_us:Any,labels:Any)->SupportLabels:
    ts=np.asarray(timestamps_us)
    y=np.asarray(labels)
    if ts.ndim!=1 or ts.dtype.kind not in "iu":
        raise E2AMaterializationError("support_timestamps_must_be_integer_1d")
    if y.ndim!=1 or y.dtype.kind not in "iu":
        raise E2AMaterializationError("labels_must_be_integer_1d")
    ts=ts.astype(np.int64,copy=False)
    y=y.astype(np.int8,copy=False)
    if len(ts)!=len(y):
        raise E2AMaterializationError("support_label_length_mismatch")
    if len(ts)==0 or np.any(np.diff(ts)<=0):
        raise E2AMaterializationError("support_not_unique_chronological")
    if not np.all(np.isin(y,(0,1))):
        raise E2AMaterializationError("labels_not_binary")
    return SupportLabels(ts,y)

def support_sha256(ts:Any)->str:
    a=np.asarray(ts,dtype=np.int64)
    h=hashlib.sha256(b"DEV032-E2A-SUPPORT-V1\0")
    h.update(a.astype(">i8",copy=False).tobytes(order="C"))
    return h.hexdigest()

def label_sha256(ts:Any,labels:Any)->str:
    t=np.asarray(ts,dtype=np.int64)
    y=np.asarray(labels,dtype=np.int8)
    h=hashlib.sha256(b"DEV032-E2A-LABEL-V1\0")
    h.update(t.astype(">i8",copy=False).tobytes(order="C"))
    h.update(y.tobytes(order="C"))
    return h.hexdigest()

def matrix_sha256(rid:str,values:Any)->str:
    x=np.asarray(values,dtype=np.float64)
    h=hashlib.sha256(b"DEV032-E2A-MATRIX-V1\0")
    h.update(rid.encode("ascii"))
    h.update(x.astype(">f8",copy=False).tobytes(order="C"))
    return h.hexdigest()

def validate_matrix(rid:str,values:Any,*,rows:int)->RefinementMatrix:
    names=expected_feature_names(rid)
    x=np.asarray(values,dtype=np.float64)
    if x.ndim!=2:
        raise E2AMaterializationError("refinement_matrix_not_2d",rid)
    if x.shape!=(rows,len(names)):
        raise E2AMaterializationError(
            "refinement_matrix_shape",
            f"{rid} expected={(rows,len(names))} actual={x.shape}",
        )
    if not np.all(np.isfinite(x)):
        raise E2AMaterializationError("refinement_matrix_nonfinite",rid)
    return RefinementMatrix(rid,names,x)

def assemble_bundle(
    timestamps_us:Any,
    labels:Any,
    refinement_values:Mapping[str,Any],
    *,
    require_full_campaign_counts:bool=False,
)->MaterializedBundle:
    validate_registry()
    if any(FORWARD_GUARDS.values()):
        raise E2AMaterializationError("runtime_guard_violation")
    sup=_support(timestamps_us,labels)
    if tuple(refinement_values)!=REFINEMENT_IDS:
        raise E2AMaterializationError("refinement_order_or_membership_mismatch")
    if require_full_campaign_counts:
        if len(sup.timestamps_us)!=EXPECTED_TOTAL_ROWS:
            raise E2AMaterializationError("campaign_support_count_mismatch")
        if int(np.sum(sup.labels==1))!=EXPECTED_LONG:
            raise E2AMaterializationError("campaign_long_count_mismatch")
        if int(np.sum(sup.labels==0))!=EXPECTED_SHORT:
            raise E2AMaterializationError("campaign_short_count_mismatch")
    mats=tuple(
        validate_matrix(rid,refinement_values[rid],rows=len(sup.timestamps_us))
        for rid in REFINEMENT_IDS
    )
    return MaterializedBundle(sup,mats)

def write_fixture_csv(
    path:Path,
    timestamps_us:Sequence[int],
    values:Mapping[str,Any],
)->None:
    ts=np.asarray(timestamps_us,dtype=np.int64)
    if ts.ndim!=1 or len(ts)==0 or np.any(np.diff(ts)<=0):
        raise E2AMaterializationError("support_not_unique_chronological")
    if tuple(values)!=REFINEMENT_IDS:
        raise E2AMaterializationError("refinement_order_or_membership_mismatch")
    mats={rid:validate_matrix(rid,values[rid],rows=len(ts)) for rid in REFINEMENT_IDS}
    header=["local_timestamp_us","feature_valid"]
    for rid in REFINEMENT_IDS:
        header.extend(mats[rid].feature_names)
    with Path(path).open("w",encoding="utf-8",newline="") as h:
        w=csv.writer(h,lineterminator="\n")
        w.writerow(header)
        for i,t in enumerate(ts.tolist()):
            row=[str(int(t)),"1"]
            for rid in REFINEMENT_IDS:
                row.extend(format(float(v),".17g") for v in mats[rid].values[i])
            w.writerow(row)

def parse_extractor_csv(path:Path,expected_timestamps_us:Any)->dict[str,np.ndarray]:
    ts=np.asarray(expected_timestamps_us,dtype=np.int64)
    header=["local_timestamp_us","feature_valid"]
    for rid in REFINEMENT_IDS:
        header.extend(expected_feature_names(rid))
    offsets={}
    pos=2
    for rid in REFINEMENT_IDS:
        n=FEATURE_COUNTS[rid]
        offsets[rid]=(pos,pos+n)
        pos+=n
    by={rid:[] for rid in REFINEMENT_IDS}
    got=[]
    with Path(path).open("r",encoding="utf-8",newline="") as h:
        r=csv.reader(h)
        try:
            actual=next(r)
        except StopIteration as exc:
            raise E2AMaterializationError("extractor_empty") from exc
        if tuple(actual)!=tuple(header):
            raise E2AMaterializationError("extractor_header_mismatch")
        for row in r:
            if len(row)!=len(header):
                raise E2AMaterializationError("extractor_row_width")
            got.append(int(row[0]))
            if row[1]!="1":
                raise E2AMaterializationError("extractor_feature_invalid",row[0])
            for rid,(a,b) in offsets.items():
                by[rid].append([float(v) for v in row[a:b]])
    got=np.asarray(got,dtype=np.int64)
    if not np.array_equal(got,ts):
        raise E2AMaterializationError("extractor_support_mismatch")
    return {
        rid:validate_matrix(rid,np.asarray(by[rid],dtype=np.float64),rows=len(ts)).values
        for rid in REFINEMENT_IDS
    }

def public_manifest(bundle:MaterializedBundle)->dict[str,Any]:
    return {
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "rows":int(len(bundle.support.timestamps_us)),
        "long":int(np.sum(bundle.support.labels==1)),
        "short":int(np.sum(bundle.support.labels==0)),
        "support_sha256":support_sha256(bundle.support.timestamps_us),
        "label_sha256":label_sha256(bundle.support.timestamps_us,bundle.support.labels),
        "refinements":[
            {
                "refinement_id":m.refinement_id,
                "parent_candidate_id":PARENT_BY_REFINEMENT[m.refinement_id],
                "feature_count":len(m.feature_names),
                "feature_names":list(m.feature_names),
                "matrix_sha256":matrix_sha256(m.refinement_id,m.values),
            }
            for m in bundle.matrices
        ],
        "forward_guards":dict(FORWARD_GUARDS),
    }

def canonical_json_bytes(payload:Mapping[str,Any])->bytes:
    return (
        json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)
        +"\n"
    ).encode("utf-8")

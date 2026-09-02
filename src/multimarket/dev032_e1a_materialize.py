from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from . import dev032_e1a_feature_core as fc

EXPERIMENT_ID = "DEV032-E1A"
DESIGN_VERSION = "wave1-materialization-contract-v1"

EXPECTED_TOTAL_ROWS = 1374
EXPECTED_LONG = 684
EXPECTED_SHORT = 690

CONTROL_IDS = ("S00","S01","S02","S03")
RAW_IDS = tuple(f"S{i:02d}" for i in range(4,36))
ALL_IDS = tuple(f"S{i:02d}" for i in range(36))

FORWARD_GUARDS = {
    "aug01_opened": False,
    "aug30_opened": False,
    "sep01_or_later_opened": False,
    "railway_opened": False,
    "archive_bucket_opened": False,
    "abundant_love_opened": False,
    "predictive_fit_run": False,
    "predictive_metric_run": False,
    "pnl_run": False,
}

class E1AMaterializationError(RuntimeError):
    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class SupportLabels:
    timestamps_us: np.ndarray
    labels: np.ndarray

@dataclass(frozen=True)
class StrategyMatrix:
    strategy_id: str
    feature_names: tuple[str,...]
    values: np.ndarray

@dataclass(frozen=True)
class MaterializedBundle:
    support: SupportLabels
    matrices: tuple[StrategyMatrix,...]

def _as_support(timestamps_us: Any, labels: Any) -> SupportLabels:
    ts=np.asarray(timestamps_us)
    y=np.asarray(labels)
    if ts.ndim!=1 or ts.dtype.kind not in "iu":
        raise E1AMaterializationError("support_timestamps_must_be_integer_1d")
    if y.ndim!=1 or y.dtype.kind not in "iu":
        raise E1AMaterializationError("labels_must_be_integer_1d")
    if len(ts)!=len(y):
        raise E1AMaterializationError("support_label_length_mismatch")
    ts=ts.astype(np.int64,copy=False)
    y=y.astype(np.int8,copy=False)
    if len(ts)==0 or np.any(np.diff(ts)<=0):
        raise E1AMaterializationError("support_not_unique_chronological")
    if not np.all(np.isin(y,(0,1))):
        raise E1AMaterializationError("labels_not_binary")
    return SupportLabels(ts,y)

def support_sha256(ts: Any) -> str:
    a=np.asarray(ts,dtype=np.int64)
    h=hashlib.sha256(b"DEV032-E1A-SUPPORT-V1\0")
    h.update(a.astype(">i8",copy=False).tobytes(order="C"))
    return h.hexdigest()

def label_sha256(ts: Any, labels: Any) -> str:
    t=np.asarray(ts,dtype=np.int64)
    y=np.asarray(labels,dtype=np.int8)
    h=hashlib.sha256(b"DEV032-E1A-LABEL-V1\0")
    h.update(t.astype(">i8",copy=False).tobytes(order="C"))
    h.update(y.tobytes(order="C"))
    return h.hexdigest()

def matrix_sha256(strategy_id: str, values: Any) -> str:
    x=np.asarray(values,dtype=np.float64)
    h=hashlib.sha256(b"DEV032-E1A-MATRIX-V1\0")
    h.update(strategy_id.encode("ascii"))
    h.update(x.astype(">f8",copy=False).tobytes(order="C"))
    return h.hexdigest()

def expected_feature_names(strategy_id: str) -> tuple[str,...]:
    counts=fc.strategy_feature_counts()
    if strategy_id not in counts:
        raise E1AMaterializationError("unknown_strategy_id",strategy_id)
    return tuple(f"{strategy_id}__f{i:02d}" for i in range(counts[strategy_id]))

def validate_matrix(strategy_id: str, values: Any, *, rows: int) -> StrategyMatrix:
    names=expected_feature_names(strategy_id)
    x=np.asarray(values,dtype=np.float64)
    if x.ndim!=2:
        raise E1AMaterializationError("strategy_matrix_not_2d",strategy_id)
    if x.shape!=(rows,len(names)):
        raise E1AMaterializationError(
            "strategy_matrix_shape",
            f"{strategy_id} expected={(rows,len(names))} actual={x.shape}",
        )
    if not np.all(np.isfinite(x)):
        raise E1AMaterializationError("strategy_matrix_nonfinite",strategy_id)
    return StrategyMatrix(strategy_id,names,x)

def assemble_bundle(
    timestamps_us: Any,
    labels: Any,
    strategy_values: Mapping[str,Any],
    *,
    require_full_campaign_counts: bool=False,
) -> MaterializedBundle:
    if any(FORWARD_GUARDS.values()):
        raise E1AMaterializationError("runtime_guard_violation")
    support=_as_support(timestamps_us,labels)
    if tuple(strategy_values.keys())!=ALL_IDS:
        raise E1AMaterializationError("strategy_order_or_membership_mismatch")
    if require_full_campaign_counts:
        if len(support.timestamps_us)!=EXPECTED_TOTAL_ROWS:
            raise E1AMaterializationError("campaign_support_count_mismatch")
        if int(np.sum(support.labels==1))!=EXPECTED_LONG:
            raise E1AMaterializationError("campaign_long_count_mismatch")
        if int(np.sum(support.labels==0))!=EXPECTED_SHORT:
            raise E1AMaterializationError("campaign_short_count_mismatch")
    matrices=tuple(
        validate_matrix(sid,strategy_values[sid],rows=len(support.timestamps_us))
        for sid in ALL_IDS
    )
    return MaterializedBundle(support,matrices)

def write_raw_extractor_fixture_csv(
    path: Path,
    timestamps_us: Sequence[int],
    raw_strategy_values: Mapping[str,Any],
) -> None:
    if tuple(raw_strategy_values.keys())!=RAW_IDS:
        raise E1AMaterializationError("raw_strategy_order_or_membership_mismatch")
    ts=np.asarray(timestamps_us,dtype=np.int64)
    if ts.ndim!=1 or len(ts)==0 or np.any(np.diff(ts)<=0):
        raise E1AMaterializationError("support_not_unique_chronological")
    mats={sid:validate_matrix(sid,raw_strategy_values[sid],rows=len(ts)) for sid in RAW_IDS}
    header=["local_timestamp_us","feature_valid"]
    for sid in RAW_IDS:
        header.extend(mats[sid].feature_names)
    with Path(path).open("w",encoding="utf-8",newline="") as handle:
        w=csv.writer(handle,lineterminator="\n")
        w.writerow(header)
        for i,t in enumerate(ts.tolist()):
            row=[str(int(t)),"1"]
            for sid in RAW_IDS:
                row.extend(format(float(v),".17g") for v in mats[sid].values[i])
            w.writerow(row)

def parse_raw_extractor_csv(path: Path, expected_timestamps_us: Any) -> dict[str,np.ndarray]:
    ts=np.asarray(expected_timestamps_us,dtype=np.int64)
    expected_header=["local_timestamp_us","feature_valid"]
    for sid in RAW_IDS:
        expected_header.extend(expected_feature_names(sid))
    by_sid={sid:[] for sid in RAW_IDS}
    got_ts=[]
    with Path(path).open("r",encoding="utf-8",newline="") as handle:
        r=csv.reader(handle)
        try:
            header=next(r)
        except StopIteration as exc:
            raise E1AMaterializationError("raw_extractor_empty") from exc
        if tuple(header)!=tuple(expected_header):
            raise E1AMaterializationError("raw_extractor_header_mismatch")
        offsets={}
        pos=2
        for sid in RAW_IDS:
            n=len(expected_feature_names(sid))
            offsets[sid]=(pos,pos+n); pos+=n
        for row in r:
            if len(row)!=len(expected_header):
                raise E1AMaterializationError("raw_extractor_row_width")
            got_ts.append(int(row[0]))
            if row[1]!="1":
                raise E1AMaterializationError("raw_extractor_feature_invalid",row[0])
            for sid,(a,b) in offsets.items():
                by_sid[sid].append([float(x) for x in row[a:b]])
    got=np.asarray(got_ts,dtype=np.int64)
    if not np.array_equal(got,ts):
        raise E1AMaterializationError("raw_extractor_support_mismatch")
    out={}
    for sid in RAW_IDS:
        out[sid]=validate_matrix(sid,np.asarray(by_sid[sid],dtype=np.float64),rows=len(ts)).values
    return out

def public_manifest(bundle: MaterializedBundle) -> dict[str,Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "rows": int(len(bundle.support.timestamps_us)),
        "long": int(np.sum(bundle.support.labels==1)),
        "short": int(np.sum(bundle.support.labels==0)),
        "support_sha256": support_sha256(bundle.support.timestamps_us),
        "label_sha256": label_sha256(bundle.support.timestamps_us,bundle.support.labels),
        "strategies": [
            {
                "strategy_id": m.strategy_id,
                "feature_count": len(m.feature_names),
                "feature_names": list(m.feature_names),
                "matrix_sha256": matrix_sha256(m.strategy_id,m.values),
            }
            for m in bundle.matrices
        ],
        "forward_guards": dict(FORWARD_GUARDS),
    }

def canonical_json_bytes(payload: Mapping[str,Any]) -> bytes:
    return (
        json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)
        + "\n"
    ).encode("utf-8")

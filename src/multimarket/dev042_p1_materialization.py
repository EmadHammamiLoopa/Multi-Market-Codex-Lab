from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev042_p0_feature_core as p0

P0_ARTIFACT_SHA256="d9259a53d24492f478615c986ed73981f052d483a764935a8dfd68d17212b882"
P0_ARTIFACT_BYTES=12989

EXPECTED_COMMON_SUPPORT_SHA256={
    "2026-01-01":"a1ff0a85368724426a9ff9666d998984178ef0427d919644c078351af4c29382",
    "2026-02-01":"1b87e100ef77817ef707bb460fb8a9f53895f7d6511f489fb238e3c6afd0b715",
    "2026-03-01":"551569f597c63c8f818fd14386b921d131ee2a207b37410ac718d99de0138954",
    "2026-04-01":"0d3c2729cfe4ceca7ebbd02252bcc81077e3f53d9d955a3bd2c52a9cb65b346b",
    "2026-05-01":"2a3062b8edf4da5aa3c6fc54badab5e5176c25d4bfdf4b7c37b5b3431a494e60",
    "2026-06-01":"a334b098c9fb3557a22259195df2fa9650cebc4198d0d7e2c7dc609936805372",
    "2026-07-01":"09a954c73b4bc6d30159ec47c019e197fe5d8e18ea7a6625a985202bf8fcf6e2",
}

class MaterializationError(RuntimeError):
    pass

@dataclass(frozen=True)
class MaterializedDay:
    date:str
    timestamps_us:np.ndarray
    X0:np.ndarray
    X1:np.ndarray
    X2:np.ndarray
    X3:np.ndarray
    X4:np.ndarray

    def assert_common_support(self):
        n=len(self.timestamps_us)
        expected=((n,15),(n,60),(n,51),(n,111),(n,111))
        observed=(self.X0.shape,self.X1.shape,self.X2.shape,self.X3.shape,self.X4.shape)
        if observed!=expected:
            raise MaterializationError(f"shape_contract:{observed}")
        if np.any(np.diff(self.timestamps_us)<=0):
            raise MaterializationError("timestamp_order")
        for x in (self.X0,self.X1,self.X2,self.X3,self.X4):
            if np.any(~np.isfinite(x)):
                raise MaterializationError("nonfinite_matrix")
        if not np.array_equal(self.X3,self.X4):
            raise MaterializationError("combined_matrix_mismatch")

def _minute_view(day):
    idx=dd.exact_minute_decision_indices(day.ts)
    ts=np.asarray(day.ts,dtype=np.int64)[idx]
    mid=np.asarray(day.mid,dtype=np.float64)[idx]
    book=np.asarray(day.book_valid,dtype=bool)[idx]
    l1=np.asarray(day.valid["L1"],dtype=bool)[idx]
    l2=np.asarray(day.valid["L2"],dtype=bool)[idx]
    full=np.asarray(day.X["L2"],dtype=np.float64)[idx]
    source={name:full[:,j] for j,name in enumerate(dd.SOURCE_FEATURE_ORDER)}
    return ts,mid,book,l1,l2,source

def materialize_day(day)->MaterializedDay:
    ts,mid,book,l1,l2,source=_minute_view(day)
    rows=[]
    for t in ts.tolist():
        f0,f1,f2=p0.build_feature_families(
            decision_timestamp_us=int(t),
            minute_timestamps_us=ts,
            mid=mid,
            book_valid=book,
            l1_valid=l1,
            l2_valid=l2,
            source=source,
        )
        if f0 is None or f1 is None or f2 is None:
            continue
        combined=np.concatenate((f0,f1[15:],f2))
        if combined.shape!=(111,):
            raise MaterializationError("combined_shape")
        rows.append((int(t),f0,f1,f2,combined))

    if not rows:
        raise MaterializationError("empty_common_support")

    out=MaterializedDay(
        date=day.day.isoformat(),
        timestamps_us=np.asarray([r[0] for r in rows],dtype=np.int64),
        X0=np.vstack([r[1] for r in rows]).astype(np.float64,copy=False),
        X1=np.vstack([r[2] for r in rows]).astype(np.float64,copy=False),
        X2=np.vstack([r[3] for r in rows]).astype(np.float64,copy=False),
        X3=np.vstack([r[4] for r in rows]).astype(np.float64,copy=False),
        X4=np.vstack([r[4] for r in rows]).astype(np.float64,copy=True),
    )
    out.assert_common_support()
    return out

def verify_frozen_support(day:MaterializedDay):
    expected=EXPECTED_COMMON_SUPPORT_SHA256.get(day.date)
    if expected is None:
        raise MaterializationError(f"unexpected_day:{day.date}")
    observed=dd.support_sha256(day.timestamps_us)
    if observed!=expected:
        raise MaterializationError(f"support_hash:{day.date}:{observed}")
    if len(day.timestamps_us)!=1409:
        raise MaterializationError(f"support_count:{day.date}:{len(day.timestamps_us)}")
    return observed

def candidate_matrix(day:MaterializedDay,candidate_id:str)->np.ndarray:
    if candidate_id=="C0_PRICE_LOGIT":return day.X0
    if candidate_id=="C1_OFI_LOGIT":return day.X1
    if candidate_id=="C2_PRESSURE_CAPACITY_LOGIT":return day.X2
    if candidate_id=="C3_COMBINED_LOGIT":return day.X3
    if candidate_id=="C4_COMBINED_HGB":return day.X4
    raise MaterializationError(f"unknown_candidate:{candidate_id}")

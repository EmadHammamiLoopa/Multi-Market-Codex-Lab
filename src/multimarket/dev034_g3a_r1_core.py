from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np

from . import codex_exp004_p1 as exp004
from . import dev030_p6_m2_direction as p6
from . import dev034_g3a_core as g3

EXPERIMENT_ID="DEV034-G3A-R1"
DESIGN_VERSION="common-full-r-support-materialization-v1"

EXPECTED_ROWS=1341
EXPECTED_LONG=665
EXPECTED_SHORT=676
EXPECTED_EXCLUDED=33
EXPECTED_REASON_COUNTS={
    "START_OF_DAY_30M_BOUNDARY":30,
    "BOOK_INVALID_IN_30M_HISTORY":3,
}
EXPECTED_DAY_COUNTS={
    "2026-01-01":4,
    "2026-02-01":422,
    "2026-03-01":356,
    "2026-04-01":156,
    "2026-05-01":64,
    "2026-06-01":121,
    "2026-07-01":218,
}
EXPECTED_OUTER_COUNTS={
    "2026-04-01":(156,85,71),
    "2026-05-01":(64,40,24),
    "2026-06-01":(121,55,66),
    "2026-07-01":(218,122,96),
}
EXPECTED_NONBOUNDARY_UTC={
    "2026-02-01T00:30:00+00:00",
    "2026-06-01T00:30:00+00:00",
    "2026-07-01T00:30:00+00:00",
}

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

class G3AR1Error(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class Exclusion:
    day:str
    timestamp_us:int
    utc:str
    label:int
    reason:str

@dataclass(frozen=True)
class EligibleDay:
    day:str
    timestamps_us:np.ndarray
    labels:np.ndarray
    full_r:np.ndarray
    exclusions:tuple[Exclusion,...]

def _reason(raw:Any,current:int,spread:np.ndarray)->str:
    maxm=max(
        exp004.RETURN_LOOKBACK_MIN
        + exp004.RV_WINDOWS_MIN
        + exp004.SPREAD_MEAN_MIN
        + exp004.RANGE_WINDOWS_MIN
    )
    start=current-maxm*exp004.DECISION_STEP_ROWS
    spread_start=current-max(exp004.SPREAD_MEAN_MIN)*exp004.DECISION_STEP_ROWS

    if start<0:
        return "START_OF_DAY_30M_BOUNDARY"
    if not bool(np.all(raw.book_valid[start:current+1])):
        return "BOOK_INVALID_IN_30M_HISTORY"

    mids=np.asarray(raw.mid[start:current+1],dtype=float)
    if np.any(~np.isfinite(mids)) or np.any(mids<=0):
        return "MID_INVALID_IN_30M_HISTORY"

    if spread_start<0:
        return "START_OF_DAY_5M_SPREAD_BOUNDARY"
    if np.any(~np.isfinite(spread[spread_start:current+1])):
        return "SPREAD_INVALID_IN_5M_HISTORY"

    r=exp004._r_features(raw,current,spread)
    if r is None:
        return "OTHER_FROZEN_R_HELPER_FAILURE"
    r=np.asarray(r,dtype=float)
    if r.shape!=(22,) or not np.all(np.isfinite(r)):
        return "R_VECTOR_WIDTH_OR_FINITE_FAILURE"
    return "VALID"

def derive_common_support(raw:Any,dataset:Any)->EligibleDay:
    _,y,ts=p6._t1_rows(dataset)
    y=np.asarray(y,dtype=np.int8)
    ts=np.asarray(ts,dtype=np.int64)
    day_ts=np.asarray(raw.ts,dtype=np.int64)
    pos=np.searchsorted(day_ts,ts)
    if np.any(pos<0) or np.any(pos>=len(day_ts)) or not np.array_equal(day_ts[pos],ts):
        raise G3AR1Error("exact_timestamp_alignment")

    spread=exp004._spread(raw)
    keep=[]
    rows=[]
    exclusions=[]
    for j,current in enumerate(pos.tolist()):
        reason=_reason(raw,int(current),spread)
        if reason=="VALID":
            r=exp004._r_features(raw,int(current),spread)
            if r is None:
                raise G3AR1Error("helper_inconsistent")
            keep.append(j)
            rows.append(np.asarray(r,dtype=np.float64))
        else:
            dt=datetime.fromtimestamp(int(ts[j])/1_000_000,tz=timezone.utc)
            exclusions.append(Exclusion(
                day=str(raw.day),
                timestamp_us=int(ts[j]),
                utc=dt.isoformat(),
                label=int(y[j]),
                reason=reason,
            ))
    idx=np.asarray(keep,dtype=np.int64)
    full=np.vstack(rows) if rows else np.empty((0,22),dtype=np.float64)
    if full.shape!=(len(idx),22) or not np.all(np.isfinite(full)):
        raise G3AR1Error("eligible_full_r_shape")
    return EligibleDay(
        day=str(raw.day),
        timestamps_us=ts[idx],
        labels=y[idx],
        full_r=full,
        exclusions=tuple(exclusions),
    )

def validate_frozen_common_support(days:dict[str,EligibleDay])->None:
    if set(days)!=set(EXPECTED_DAY_COUNTS):
        raise G3AR1Error("day_set")
    rows=sum(len(v.labels) for v in days.values())
    longs=sum(int(np.sum(v.labels==1)) for v in days.values())
    shorts=sum(int(np.sum(v.labels==0)) for v in days.values())
    if (rows,longs,shorts)!=(EXPECTED_ROWS,EXPECTED_LONG,EXPECTED_SHORT):
        raise G3AR1Error("campaign_counts",f"{rows}/{longs}/{shorts}")
    for d,n in EXPECTED_DAY_COUNTS.items():
        if len(days[d].labels)!=n:
            raise G3AR1Error("day_count",f"{d}:{len(days[d].labels)}")
    all_ex=[e for v in days.values() for e in v.exclusions]
    if len(all_ex)!=EXPECTED_EXCLUDED:
        raise G3AR1Error("excluded_count",str(len(all_ex)))
    from collections import Counter
    rc=Counter(e.reason for e in all_ex)
    if dict(rc)!=EXPECTED_REASON_COUNTS:
        raise G3AR1Error("reason_counts",str(dict(rc)))
    nonb={e.utc for e in all_ex if e.reason!="START_OF_DAY_30M_BOUNDARY"}
    if nonb!=EXPECTED_NONBOUNDARY_UTC:
        raise G3AR1Error("nonboundary_rows",str(sorted(nonb)))
    for d,(n,l,s) in EXPECTED_OUTER_COUNTS.items():
        v=days[d]
        got=(len(v.labels),int(np.sum(v.labels==1)),int(np.sum(v.labels==0)))
        if got!=(n,l,s):
            raise G3AR1Error("outer_counts",f"{d}:{got}")
    if any(FORWARD_GUARDS.values()):
        raise G3AR1Error("forward_guard")

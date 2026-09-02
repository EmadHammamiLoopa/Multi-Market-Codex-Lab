from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

WINDOWS=(120,360,720)
TARGET_QUANTILE=0.80
TARGET_COVERAGE=0.20

class R1Error(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class ControllerResult:
    window:int
    thresholds:np.ndarray
    actions:np.ndarray
    coverage:float
    action_count:int
    abstain_count:int
    long_count:int
    short_count:int
    coverage_abs_error:float
    rolling60_coverage:np.ndarray
    mean_abs_rolling60_error:float
    max_abs_rolling60_error:float
    rolling60_outside_count:int
    action_state_switches:int
    warm_start_count:int

def rolling_quantile_actions(*,scores,p_long,warm_scores,window:int):
    if int(window) not in WINDOWS:
        raise R1Error("window_not_frozen")
    s=np.asarray(scores,dtype=np.float64)
    p=np.asarray(p_long,dtype=np.float64)
    warm=np.asarray(warm_scores,dtype=np.float64)
    if s.ndim!=1 or p.ndim!=1 or warm.ndim!=1:
        raise R1Error("shape")
    if len(s)!=len(p) or len(s)==0 or len(warm)==0:
        raise R1Error("length")
    if not np.all(np.isfinite(s)) or not np.all(np.isfinite(p)) or not np.all(np.isfinite(warm)):
        raise R1Error("nonfinite")
    if np.any((p<0)|(p>1)):
        raise R1Error("p_long_range")

    buf=deque(warm[-int(window):].tolist(),maxlen=int(window))
    thresholds=np.empty(len(s),dtype=np.float64)
    actions=np.zeros(len(s),dtype=np.int8)

    for i,(score,pl) in enumerate(zip(s.tolist(),p.tolist(),strict=True)):
        ref=np.asarray(buf,dtype=np.float64)
        if len(ref)==0:
            raise R1Error("empty_reference",str(i))
        threshold=float(np.quantile(ref,TARGET_QUANTILE,method="higher"))
        thresholds[i]=threshold
        if float(score)>=threshold:
            actions[i]=2 if float(pl)>=0.5 else 1
        buf.append(float(score))

    return thresholds,actions

def rolling60_coverage(actions):
    a=np.asarray(actions,dtype=np.int8)
    active=(a!=0).astype(np.float64)
    if len(a)<60:
        return np.asarray([],dtype=np.float64)
    return np.convolve(active,np.ones(60,dtype=np.float64),mode="valid")/60.0

def summarize(*,scores,p_long,warm_scores,window:int):
    thresholds,actions=rolling_quantile_actions(
        scores=scores,p_long=p_long,warm_scores=warm_scores,window=window
    )
    n=len(actions)
    act=int(np.sum(actions!=0))
    abstain=n-act
    long_n=int(np.sum(actions==2))
    short_n=int(np.sum(actions==1))
    coverage=float(act/n)
    roll=rolling60_coverage(actions)
    if len(roll):
        err=np.abs(roll-TARGET_COVERAGE)
        mean_err=float(np.mean(err))
        max_err=float(np.max(err))
        outside=int(np.sum((roll<0.10)|(roll>0.30)))
    else:
        mean_err=max_err=0.0
        outside=0
    switches=int(np.sum(actions[1:]!=actions[:-1])) if n>1 else 0
    return ControllerResult(
        window=int(window),
        thresholds=thresholds,
        actions=actions,
        coverage=coverage,
        action_count=act,
        abstain_count=abstain,
        long_count=long_n,
        short_count=short_n,
        coverage_abs_error=float(abs(coverage-TARGET_COVERAGE)),
        rolling60_coverage=roll,
        mean_abs_rolling60_error=mean_err,
        max_abs_rolling60_error=max_err,
        rolling60_outside_count=outside,
        action_state_switches=switches,
        warm_start_count=int(min(len(warm_scores),int(window))),
    )

def feasible(result:ControllerResult):
    return bool(
        result.coverage>=0.10
        and result.coverage<=0.30
        and result.action_count>0
        and result.abstain_count>0
        and result.long_count>0
        and result.short_count>0
        and np.all(np.isfinite(result.thresholds))
    )

def rank_controllers(records:Mapping[int,Sequence[ControllerResult]]):
    for w in WINDOWS:
        if w not in records:
            raise R1Error("missing_window",str(w))
        if len(records[w])!=24:
            raise R1Error("record_count",f"{w}:{len(records[w])}")
    feasible_windows=[
        w for w in WINDOWS
        if all(feasible(r) for r in records[w])
    ]
    def stats(w):
        rs=records[w]
        return (
            float(np.mean([r.coverage_abs_error for r in rs])),
            float(np.max([r.coverage_abs_error for r in rs])),
            float(np.mean([r.mean_abs_rolling60_error for r in rs])),
            int(np.sum([r.rolling60_outside_count for r in rs])),
            int(w),
        )
    ranked=sorted(feasible_windows,key=stats)
    return ranked,{w:stats(w) for w in WINDOWS}

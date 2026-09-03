from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np

GRID_US=250_000
VPIN_BUCKETS=50
CALIBRATION_BLOCK_SECONDS=1800
EPS=1e-12

class T0CError(RuntimeError):
    pass


def normalized_mlofi(flow_250ms:Sequence[float], end_index:int, seconds:int)->float:
    x=np.asarray(flow_250ms,dtype=np.float64)
    if x.ndim!=1 or np.any(~np.isfinite(x)):
        raise T0CError("flow_shape_or_finite")
    width=int(seconds*4)
    stop=int(end_index)+1
    start=stop-width
    if start<0:
        raise T0CError(f"flow_history:{seconds}")
    w=x[start:stop]
    den=float(np.sum(np.abs(w)))
    if den<=EPS:
        return 0.0
    out=float(np.sum(w)/den)
    if not math.isfinite(out) or out < -1.000000000001 or out > 1.000000000001:
        raise T0CError("normalized_flow_range")
    return float(np.clip(out,-1.0,1.0))


def t10_triplet(flow_250ms:Sequence[float], end_index:int)->tuple[float,float,float]:
    return (
        normalized_mlofi(flow_250ms,end_index,1),
        normalized_mlofi(flow_250ms,end_index,16),
        normalized_mlofi(flow_250ms,end_index,32),
    )


def calibrate_vpin_bucket_volume(
    timestamps_us:Sequence[int],
    buy_qty_250ms:Sequence[float],
    sell_qty_250ms:Sequence[float],
)->float:
    ts=np.asarray(timestamps_us,dtype=np.int64)
    b=np.asarray(buy_qty_250ms,dtype=np.float64)
    s=np.asarray(sell_qty_250ms,dtype=np.float64)
    if ts.ndim!=1 or b.shape!=ts.shape or s.shape!=ts.shape or len(ts)==0:
        raise T0CError("calibration_shape")
    if np.any(np.diff(ts)!=GRID_US):
        raise T0CError("calibration_grid")
    if np.any(~np.isfinite(b)) or np.any(~np.isfinite(s)) or np.any(b<0) or np.any(s<0):
        raise T0CError("calibration_volume_values")

    block_us=int(CALIBRATION_BLOCK_SECONDS*1_000_000)
    block_id=(ts-ts[0])//block_us
    vols=[]
    for k in np.unique(block_id):
        mask=block_id==k
        v=float(np.sum(b[mask]+s[mask]))
        if v>0:
            vols.append(v)
    if len(vols)<3:
        raise T0CError("calibration_blocks")
    median_30m=float(np.median(np.asarray(vols,dtype=np.float64)))
    bucket=median_30m/float(VPIN_BUCKETS)
    if not math.isfinite(bucket) or bucket<=0:
        raise T0CError("bucket_volume")
    return bucket


@dataclass(frozen=True)
class VPINSeries:
    timestamps_us:np.ndarray
    toxicity:np.ndarray
    completed_buckets:np.ndarray
    bucket_volume:float
    rolling_buckets:int=VPIN_BUCKETS

    def validate(self)->None:
        ts=np.asarray(self.timestamps_us,dtype=np.int64)
        x=np.asarray(self.toxicity,dtype=np.float64)
        n=np.asarray(self.completed_buckets,dtype=np.int64)
        if ts.ndim!=1 or x.shape!=ts.shape or n.shape!=ts.shape:
            raise T0CError("vpin_shape")
        finite=np.isfinite(x)
        if np.any(x[finite]<0) or np.any(x[finite]>1):
            raise T0CError("vpin_range")
        if np.any(n<0) or np.any(np.diff(n)<0):
            raise T0CError("vpin_bucket_count")


def vpin_series(
    timestamps_us:Sequence[int],
    buy_qty_250ms:Sequence[float],
    sell_qty_250ms:Sequence[float],
    *,
    bucket_volume:float,
    rolling_buckets:int=VPIN_BUCKETS,
)->VPINSeries:
    ts=np.asarray(timestamps_us,dtype=np.int64)
    buy=np.asarray(buy_qty_250ms,dtype=np.float64)
    sell=np.asarray(sell_qty_250ms,dtype=np.float64)
    if ts.ndim!=1 or buy.shape!=ts.shape or sell.shape!=ts.shape or len(ts)==0:
        raise T0CError("vpin_input_shape")
    if np.any(np.diff(ts)!=GRID_US):
        raise T0CError("vpin_grid")
    if np.any(~np.isfinite(buy)) or np.any(~np.isfinite(sell)) or np.any(buy<0) or np.any(sell<0):
        raise T0CError("vpin_input_values")
    V=float(bucket_volume)
    rb=int(rolling_buckets)
    if not math.isfinite(V) or V<=0 or rb<=0:
        raise T0CError("vpin_parameters")

    tox=np.full(len(ts),np.nan,dtype=np.float64)
    nb=np.zeros(len(ts),dtype=np.int64)
    bucket_buy=0.0
    bucket_sell=0.0
    bucket_filled=0.0
    imbalances=[]

    for i in range(len(ts)):
        total=float(buy[i]+sell[i])
        if total>0:
            frac_buy=float(buy[i]/total)
            remaining=total
            while remaining>EPS:
                room=V-bucket_filled
                take=min(room,remaining)
                bucket_buy+=take*frac_buy
                bucket_sell+=take*(1.0-frac_buy)
                bucket_filled+=take
                remaining-=take
                if bucket_filled>=V-EPS:
                    imb=abs(bucket_buy-bucket_sell)/V
                    imbalances.append(float(np.clip(imb,0.0,1.0)))
                    bucket_buy=0.0
                    bucket_sell=0.0
                    bucket_filled=0.0
        nb[i]=len(imbalances)
        if len(imbalances)>=rb:
            tox[i]=float(np.mean(imbalances[-rb:]))

    out=VPINSeries(ts,tox,nb,V,rb)
    out.validate()
    return out


def toxicity_at(vpin:VPINSeries,index:int)->float|None:
    i=int(index)
    if i<0 or i>=len(vpin.timestamps_us):
        raise T0CError("toxicity_index")
    x=float(vpin.toxicity[i])
    if not math.isfinite(x):
        return None
    return x

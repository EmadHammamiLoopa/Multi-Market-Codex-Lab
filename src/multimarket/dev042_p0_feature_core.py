from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import hashlib
import numpy as np

PRICE_LAGS_S=(60,180,300,600,900,1800)
PRICE_RV_WINDOWS_S=(300,900,1800)
PRICE_RANGE_WINDOWS_S=(300,900,1800)
PRICE_CONTRASTS=((60,300),(300,900),(900,1800))

OFI_SOURCES=(
    "ofi_l1_1s",
    "mlofi_l5_1s",
    "mlofi_l10_1s",
    "trade_qty_imbalance_1s",
    "trade_count_imbalance_1s",
)
OFI_WINDOWS_S=(60,300,900,1800)

PRESSURE_TEMPORAL_SOURCES=(
    "spread_bps",
    "microprice_minus_mid_bps",
    "depth_log_imbalance_l5",
    "pressure_capacity_l5",
    "replenish_support_norm_l5",
    "liquidity_fragility_l5",
)
PRESSURE_WINDOWS_S=(60,300,900)

EPS=1e-12
MINUTE_US=60_000_000

class FeatureError(RuntimeError):
    pass

def price_feature_names()->tuple[str,...]:
    out=[]
    out.extend(f"price_ret_bps_{x}s" for x in PRICE_LAGS_S)
    out.extend(f"price_rv_bps_{x}s" for x in PRICE_RV_WINDOWS_S)
    out.extend(f"price_range_bps_{x}s" for x in PRICE_RANGE_WINDOWS_S)
    out.extend(f"price_momentum_contrast_{a}_{b}" for a,b in PRICE_CONTRASTS)
    return tuple(out)

def ofi_addition_names()->tuple[str,...]:
    out=[]
    for src in OFI_SOURCES:
        out.append(f"{src}__last")
        for w in OFI_WINDOWS_S:
            out.append(f"{src}__mean_{w}s")
            out.append(f"{src}__std_{w}s")
    return tuple(out)

def pressure_snapshot_names()->tuple[str,...]:
    return (
        "spread_bps",
        "microprice_minus_mid_bps",
        "obi_l1",
        "obi_l5",
        "obi_l10",
        "depth_log_imbalance_l5",
        "depth_log_imbalance_l10",
        "bid_depth_concentration_log",
        "ask_depth_concentration_log",
        "pressure_capacity_l5",
        "pressure_capacity_l10",
        "replenish_support_norm_l5",
        "replenishment_imbalance",
        "depletion_imbalance",
        "liquidity_fragility_l5",
    )

def pressure_temporal_names()->tuple[str,...]:
    out=[]
    for src in PRESSURE_TEMPORAL_SOURCES:
        for w in PRESSURE_WINDOWS_S:
            out.append(f"{src}__mean_{w}s")
            out.append(f"{src}__std_{w}s")
    return tuple(out)

F0_NAMES=price_feature_names()
F1_NAMES=F0_NAMES+ofi_addition_names()
F2_NAMES=pressure_snapshot_names()+pressure_temporal_names()
COMBINED_NAMES=F0_NAMES+ofi_addition_names()+F2_NAMES

def feature_name_sha256(names)->str:
    h=hashlib.sha256(b"DEV042-FEATURE-NAMES-V1\0")
    for x in names:
        h.update(str(x).encode());h.update(b"\0")
    return h.hexdigest()

@dataclass(frozen=True)
class FeatureRow:
    timestamp_us:int
    f0:np.ndarray
    f1:np.ndarray
    f2:np.ndarray

def _pos(ts:np.ndarray,target:int)->int|None:
    i=int(np.searchsorted(ts,int(target),side="left"))
    if i>=len(ts) or int(ts[i])!=int(target):
        return None
    return i

def _window_positions(ts:np.ndarray,end_us:int,window_s:int)->np.ndarray|None:
    start=end_us-int(window_s)*1_000_000
    vals=np.arange(start,end_us+1,MINUTE_US,dtype=np.int64)
    idx=[]
    for t in vals.tolist():
        p=_pos(ts,t)
        if p is None:
            return None
        idx.append(p)
    return np.asarray(idx,dtype=np.int64)

def _std(x):
    return float(np.std(np.asarray(x,dtype=np.float64),ddof=0))

def build_feature_row(
    *,
    decision_timestamp_us:int,
    minute_timestamps_us,
    mid,
    book_valid,
    l1_valid,
    l2_valid,
    source:Mapping[str,np.ndarray],
)->FeatureRow|None:
    ts=np.asarray(minute_timestamps_us,dtype=np.int64)
    mid=np.asarray(mid,dtype=np.float64)
    book=np.asarray(book_valid,dtype=bool)
    l1=np.asarray(l1_valid,dtype=bool)
    l2=np.asarray(l2_valid,dtype=bool)
    if not (len(ts)==len(mid)==len(book)==len(l1)==len(l2)):
        raise FeatureError("length_mismatch")
    if len(ts)==0 or np.any(np.diff(ts)<=0):
        raise FeatureError("timestamp_order")

    d=int(decision_timestamp_us)
    p=_pos(ts,d)
    if p is None:
        return None

    # F0
    rets={}
    for lag in PRICE_LAGS_S:
        q=_pos(ts,d-lag*1_000_000)
        if q is None or not (book[p] and book[q]):
            return None
        if not (np.isfinite(mid[p]) and np.isfinite(mid[q]) and mid[p]>0 and mid[q]>0):
            return None
        rets[lag]=float(10000*np.log(mid[p]/mid[q]))

    f0=list(rets[x] for x in PRICE_LAGS_S)
    for w in PRICE_RV_WINDOWS_S:
        idx=_window_positions(ts,d,w)
        if idx is None or not np.all(book[idx]) or len(idx)<2:
            return None
        vals=mid[idx]
        if np.any(~np.isfinite(vals)) or np.any(vals<=0):
            return None
        one=10000*np.log(vals[1:]/vals[:-1])
        f0.append(_std(one))
    for w in PRICE_RANGE_WINDOWS_S:
        idx=_window_positions(ts,d,w)
        if idx is None or not np.all(book[idx]):
            return None
        vals=mid[idx]
        if np.any(~np.isfinite(vals)) or np.any(vals<=0):
            return None
        f0.append(float(10000*np.log(np.max(vals)/np.min(vals))))
    for a,b in PRICE_CONTRASTS:
        f0.append(float(rets[a]-rets[b]))
    f0a=np.asarray(f0,dtype=np.float64)
    if len(f0a)!=15 or np.any(~np.isfinite(f0a)):
        return None

    # F1 OFI additions
    ofi=[]
    for src in OFI_SOURCES:
        arr=np.asarray(source[src],dtype=np.float64)
        if len(arr)!=len(ts):
            raise FeatureError("source_length")
        if not l1[p] or not np.isfinite(arr[p]):
            return None
        ofi.append(float(arr[p]))
        for w in OFI_WINDOWS_S:
            idx=_window_positions(ts,d,w)
            if idx is None or not np.all(l1[idx]):
                return None
            vals=arr[idx]
            if np.any(~np.isfinite(vals)):
                return None
            ofi.extend((float(np.mean(vals)),_std(vals)))
    ofia=np.asarray(ofi,dtype=np.float64)
    if len(ofia)!=45 or np.any(~np.isfinite(ofia)):
        return None
    f1a=np.concatenate((f0a,ofia))

    # F2 snapshot primitives
    required=(
        "spread_bps","microprice_minus_mid_bps","obi_l1","obi_l5","obi_l10",
        "log_bid_depth_l5","log_ask_depth_l5","log_bid_depth_l10","log_ask_depth_l10",
        "ofi_l1_1s","bid_replenish_l5_1s","ask_replenish_l5_1s",
        "bid_deplete_l5_1s","ask_deplete_l5_1s",
    )
    if not l2[p]:
        return None
    vals={k:float(np.asarray(source[k],dtype=np.float64)[p]) for k in required}
    if any(not np.isfinite(v) for v in vals.values()):
        return None
    B5=np.expm1(vals["log_bid_depth_l5"]);A5=np.expm1(vals["log_ask_depth_l5"])
    B10=np.expm1(vals["log_bid_depth_l10"]);A10=np.expm1(vals["log_ask_depth_l10"])
    if min(B5,A5,B10,A10)<0:
        return None
    O=vals["ofi_l1_1s"]
    BR=vals["bid_replenish_l5_1s"];AR=vals["ask_replenish_l5_1s"]
    BD=vals["bid_deplete_l5_1s"];AD=vals["ask_deplete_l5_1s"]
    derived={
        "spread_bps":vals["spread_bps"],
        "microprice_minus_mid_bps":vals["microprice_minus_mid_bps"],
        "obi_l1":vals["obi_l1"],
        "obi_l5":vals["obi_l5"],
        "obi_l10":vals["obi_l10"],
        "depth_log_imbalance_l5":vals["log_bid_depth_l5"]-vals["log_ask_depth_l5"],
        "depth_log_imbalance_l10":vals["log_bid_depth_l10"]-vals["log_ask_depth_l10"],
        "bid_depth_concentration_log":vals["log_bid_depth_l5"]-vals["log_bid_depth_l10"],
        "ask_depth_concentration_log":vals["log_ask_depth_l5"]-vals["log_ask_depth_l10"],
        "pressure_capacity_l5":max(O,0)/(A5+EPS)-max(-O,0)/(B5+EPS),
        "pressure_capacity_l10":max(O,0)/(A10+EPS)-max(-O,0)/(B10+EPS),
        "replenish_support_norm_l5":(BR+AD-AR-BD)/(B5+A5+EPS),
        "replenishment_imbalance":(BR-AR)/(BR+AR+EPS),
        "depletion_imbalance":(AD-BD)/(AD+BD+EPS),
        "liquidity_fragility_l5":vals["spread_bps"]/(1+np.log1p(B5+A5)),
    }
    f2=[derived[k] for k in pressure_snapshot_names()]

    for src in PRESSURE_TEMPORAL_SOURCES:
        for w in PRESSURE_WINDOWS_S:
            idx=_window_positions(ts,d,w)
            if idx is None or not np.all(l2[idx]):
                return None
            series=[]
            for j in idx.tolist():
                sv={k:float(np.asarray(source[k],dtype=np.float64)[j]) for k in required}
                if any(not np.isfinite(v) for v in sv.values()):
                    return None
                b5=np.expm1(sv["log_bid_depth_l5"]);a5=np.expm1(sv["log_ask_depth_l5"])
                if min(b5,a5)<0:
                    return None
                oo=sv["ofi_l1_1s"];br=sv["bid_replenish_l5_1s"];ar=sv["ask_replenish_l5_1s"]
                bd=sv["bid_deplete_l5_1s"];ad=sv["ask_deplete_l5_1s"]
                if src=="spread_bps": x=sv["spread_bps"]
                elif src=="microprice_minus_mid_bps": x=sv["microprice_minus_mid_bps"]
                elif src=="depth_log_imbalance_l5": x=sv["log_bid_depth_l5"]-sv["log_ask_depth_l5"]
                elif src=="pressure_capacity_l5": x=max(oo,0)/(a5+EPS)-max(-oo,0)/(b5+EPS)
                elif src=="replenish_support_norm_l5": x=(br+ad-ar-bd)/(b5+a5+EPS)
                elif src=="liquidity_fragility_l5": x=sv["spread_bps"]/(1+np.log1p(b5+a5))
                else: raise FeatureError("pressure_source")
                series.append(float(x))
            arr=np.asarray(series,dtype=np.float64)
            if np.any(~np.isfinite(arr)):
                return None
            f2.extend((float(np.mean(arr)),_std(arr)))
    f2a=np.asarray(f2,dtype=np.float64)
    if len(f2a)!=51 or np.any(~np.isfinite(f2a)):
        return None

    return FeatureRow(d,f0a,f1a,f2a)

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

EPS=1e-12
EVENT_ALPHABET=("BI","BD","BR","BP","AI","AD","AR","AP")

@dataclass(frozen=True)
class Snapshot:
    bid_prices:np.ndarray
    bid_qty:np.ndarray
    ask_prices:np.ndarray
    ask_qty:np.ndarray

@dataclass(frozen=True)
class Event:
    event_class:str
    rank:int
    dq:float

def _finite(a,reason):
    z=np.asarray(a,dtype=np.float64)
    if z.ndim!=1 or np.any(~np.isfinite(z)):
        raise ValueError(reason)
    return z

def validate_snapshot(s:Snapshot,min_levels:int=50):
    bp=_finite(s.bid_prices,"bid_prices")
    bq=_finite(s.bid_qty,"bid_qty")
    ap=_finite(s.ask_prices,"ask_prices")
    aq=_finite(s.ask_qty,"ask_qty")
    if min(map(len,(bp,bq,ap,aq)))<min_levels: raise ValueError("depth")
    if np.any(bq<0) or np.any(aq<0): raise ValueError("qty")
    if np.any(np.diff(bp)>=0) or np.any(np.diff(ap)<=0): raise ValueError("order")
    if ap[0]<=bp[0]: raise ValueError("cross")
    return bp,bq,ap,aq

def imbalance(x:float,y:float)->float:
    den=float(x)+float(y)
    return 0.0 if den<=0 else float((x-y)/den)

def l1_queue_imbalance(s:Snapshot)->np.ndarray:
    _,bq,_,aq=validate_snapshot(s)
    return np.asarray([imbalance(bq[0],aq[0])])

def multiscale_depth_imbalance(s:Snapshot)->np.ndarray:
    _,bq,_,aq=validate_snapshot(s)
    return np.asarray([
        imbalance(float(np.sum(bq[:L])),float(np.sum(aq[:L])))
        for L in (1,5,10,20)
    ])

def microprice_displacement(s:Snapshot)->np.ndarray:
    bp,bq,ap,aq=validate_snapshot(s)
    mid=(bp[0]+ap[0])/2.0
    out=[]
    for L in (1,5,10,20):
        B=float(np.sum(bq[:L]));A=float(np.sum(aq[:L]));den=A+B
        micro=mid if den<=0 else (ap[0]*B+bp[0]*A)/den
        out.append(10000.0*(micro-mid)/mid)
    return np.asarray(out)

def _ols(x,y):
    x=np.asarray(x,dtype=np.float64);y=np.asarray(y,dtype=np.float64)
    xc=x-np.mean(x);den=float(np.dot(xc,xc))
    return 0.0 if den<=0 else float(np.dot(xc,y-np.mean(y))/den)

def book_geometry(s:Snapshot)->np.ndarray:
    bp,bq,ap,aq=validate_snapshot(s)
    mid=(bp[0]+ap[0])/2.0
    bd=10000*np.abs(bp[:10]-mid)/mid
    ad=10000*np.abs(ap[:10]-mid)/mid
    bs=_ols(bd,np.log1p(bq[:10]))
    ass=_ols(ad,np.log1p(aq[:10]))
    bnf=float(np.sum(bq[:10])/max(np.sum(bq[:50]),EPS))
    anf=float(np.sum(aq[:10])/max(np.sum(aq[:50]),EPS))
    bg=10000*(bp[:10][:-1]-bp[:10][1:])/mid
    ag=10000*(ap[:10][1:]-ap[:10][:-1])/mid
    return np.asarray([bs,ass,bs-ass,bnf-anf,float(np.mean(bg)),float(np.mean(ag))])

def mlofi_top10(events:Sequence[Event])->np.ndarray:
    out=np.zeros(10,dtype=np.float64)
    den=np.zeros(10,dtype=np.float64)
    for e in events:
        if e.event_class not in EVENT_ALPHABET: raise ValueError("event_class")
        if not 1<=int(e.rank)<=10: continue
        j=int(e.rank)-1
        sign=1.0 if EVENT_ALPHABET.index(e.event_class)<4 else -1.0
        out[j]+=sign*float(e.dq)
        den[j]+=abs(float(e.dq))
    return np.divide(out,den,out=np.zeros_like(out),where=den>0)

def event_qty_share(events:Sequence[Event])->np.ndarray:
    qty=np.zeros(8,dtype=np.float64)
    idx={c:i for i,c in enumerate(EVENT_ALPHABET)}
    for e in events:
        if e.event_class not in idx: raise ValueError("event_class")
        qty[idx[e.event_class]]+=abs(float(e.dq))
    den=float(np.sum(qty))
    return qty/den if den>0 else qty

def event_count_share(events:Sequence[Event])->np.ndarray:
    cnt=np.zeros(8,dtype=np.float64)
    idx={c:i for i,c in enumerate(EVENT_ALPHABET)}
    for e in events:
        if e.event_class not in idx: raise ValueError("event_class")
        cnt[idx[e.event_class]]+=1.0
    den=float(np.sum(cnt))
    return cnt/den if den>0 else cnt

def flatten_bins(rows:Iterable[Sequence[float]],channels:int)->np.ndarray:
    a=np.asarray(list(rows),dtype=np.float64)
    if a.ndim!=2 or a.shape[1]!=channels or np.any(~np.isfinite(a)):
        raise ValueError("bin_matrix")
    return a.reshape(-1)

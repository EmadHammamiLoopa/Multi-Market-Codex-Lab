from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping, Sequence

import numpy as np

EPS = 1e-12
EVENT_ALPHABET = ("BI","BD","BR","BP","AI","AD","AR","AP")
LEVELS = (1,2,3,5,10,20,50)
TAUS_SECONDS = (1.0,8.0)
TIME_BANDS = ((0.0,1.0),(1.0,4.0),(4.0,16.0),(16.0,32.0))

STRATEGY_IDS = tuple(f"S{i:02d}" for i in range(36))

class E1AFeatureError(ValueError):
    def __init__(self, reason: str, detail: str | None = None):
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class BookSide:
    prices: np.ndarray
    quantities: np.ndarray

@dataclass(frozen=True)
class BookSnapshot:
    bids: BookSide
    asks: BookSide

@dataclass(frozen=True)
class TimedEvent:
    age_seconds: float
    event_class: str

def _finite_1d(values, *, reason: str) -> np.ndarray:
    a=np.asarray(values,dtype=np.float64)
    if a.ndim!=1 or len(a)==0: raise E1AFeatureError(reason)
    if not np.all(np.isfinite(a)): raise E1AFeatureError(reason)
    return a

def imbalance(b: float, a: float) -> float:
    b=float(b); a=float(a)
    if not math.isfinite(b) or not math.isfinite(a) or b<0 or a<0:
        raise E1AFeatureError("invalid_nonnegative_pair")
    d=b+a
    return 0.0 if d<=0 else (b-a)/d

def log_ratio(b: float, a: float) -> float:
    b=float(b); a=float(a)
    if not math.isfinite(b) or not math.isfinite(a) or b<0 or a<0:
        raise E1AFeatureError("invalid_nonnegative_pair")
    return math.log((b+EPS)/(a+EPS))

def validate_book(book: BookSnapshot, *, min_levels: int=1) -> tuple[np.ndarray,np.ndarray,np.ndarray,np.ndarray]:
    bp=_finite_1d(book.bids.prices,reason="invalid_bid_prices")
    bq=_finite_1d(book.bids.quantities,reason="invalid_bid_quantities")
    ap=_finite_1d(book.asks.prices,reason="invalid_ask_prices")
    aq=_finite_1d(book.asks.quantities,reason="invalid_ask_quantities")
    if len(bp)!=len(bq) or len(ap)!=len(aq): raise E1AFeatureError("book_length_mismatch")
    if len(bp)<min_levels or len(ap)<min_levels: raise E1AFeatureError("insufficient_depth")
    if np.any(bq<0) or np.any(aq<0): raise E1AFeatureError("negative_quantity")
    if np.any(np.diff(bp)>=0): raise E1AFeatureError("bids_not_strictly_descending")
    if np.any(np.diff(ap)<=0): raise E1AFeatureError("asks_not_strictly_ascending")
    if not (bp[0]>0 and ap[0]>bp[0]): raise E1AFeatureError("crossed_or_invalid_book")
    return bp,bq,ap,aq

def mid_spread(book: BookSnapshot) -> tuple[float,float,float]:
    bp,bq,ap,aq=validate_book(book)
    del bq,aq
    mid=(bp[0]+ap[0])/2.0
    spread=ap[0]-bp[0]
    spread_bps=10000.0*spread/mid
    return mid,spread,spread_bps

def cumulative_depth_imbalance(book: BookSnapshot, levels: Sequence[int]=LEVELS) -> np.ndarray:
    max_l=max(levels); bp,bq,ap,aq=validate_book(book,min_levels=max_l); del bp,ap
    return np.asarray([imbalance(float(np.sum(bq[:L])),float(np.sum(aq[:L]))) for L in levels],dtype=np.float64)

def cumulative_log_depth_ratio(book: BookSnapshot, levels: Sequence[int]=LEVELS) -> np.ndarray:
    max_l=max(levels); bp,bq,ap,aq=validate_book(book,min_levels=max_l); del bp,ap
    return np.asarray([log_ratio(float(np.sum(bq[:L])),float(np.sum(aq[:L]))) for L in levels],dtype=np.float64)

def distance_weighted_obi(book: BookSnapshot, *, levels: int=50) -> np.ndarray:
    bp,bq,ap,aq=validate_book(book,min_levels=levels)
    mid,_,_=mid_spread(book)
    bd=10000*np.abs(bp[:levels]-mid)/mid
    ad=10000*np.abs(ap[:levels]-mid)/mid
    wi_b=1.0/(1.0+bd); wi_a=1.0/(1.0+ad)
    we_b=np.exp(-bd/10.0); we_a=np.exp(-ad/10.0)
    return np.asarray([
      imbalance(float(np.dot(wi_b,bq[:levels])),float(np.dot(wi_a,aq[:levels]))),
      imbalance(float(np.dot(we_b,bq[:levels])),float(np.dot(we_a,aq[:levels]))),
    ],dtype=np.float64)

def generalized_microprice(book: BookSnapshot, levels: Sequence[int]=(1,5,10,20,50)) -> tuple[np.ndarray,np.ndarray]:
    max_l=max(levels); bp,bq,ap,aq=validate_book(book,min_levels=max_l)
    mid,_,spread_bps=mid_spread(book)
    disp=[]; norm=[]
    for L in levels:
        B=float(np.sum(bq[:L])); A=float(np.sum(aq[:L])); den=A+B
        micro=mid if den<=0 else (ap[0]*B+bp[0]*A)/den
        x=10000.0*(micro-mid)/mid
        disp.append(x)
        norm.append(x/spread_bps if spread_bps>0 else 0.0)
    return np.asarray(disp),np.asarray(norm)

def _ols_slope(x: np.ndarray,y: np.ndarray)->float:
    if len(x)!=len(y) or len(x)<2: raise E1AFeatureError("slope_input")
    xc=x-np.mean(x); den=float(np.dot(xc,xc))
    if den<=0:return 0.0
    return float(np.dot(xc,y-np.mean(y))/den)

def book_slope(book: BookSnapshot, *, levels: int) -> np.ndarray:
    bp,bq,ap,aq=validate_book(book,min_levels=levels)
    mid,_,_=mid_spread(book)
    bd=10000*np.abs(bp[:levels]-mid)/mid
    ad=10000*np.abs(ap[:levels]-mid)/mid
    return np.asarray([_ols_slope(bd,np.log1p(bq[:levels])),_ols_slope(ad,np.log1p(aq[:levels]))])

def slope_convexity(book: BookSnapshot) -> np.ndarray:
    s20=book_slope(book,levels=20); s50=book_slope(book,levels=50)
    bp,bq,ap,aq=validate_book(book,min_levels=50); del bp,ap
    bc=float(np.sum(bq[:10]))/max(float(np.sum(bq[:50])),EPS)
    ac=float(np.sum(aq[:10]))/max(float(np.sum(aq[:50])),EPS)
    return np.asarray([s20[0]-s20[1],s50[0]-s50[1],bc,ac])

def price_gap_asymmetry(book: BookSnapshot) -> np.ndarray:
    bp,bq,ap,aq=validate_book(book,min_levels=50); del bq,aq
    mid,_,_=mid_spread(book)
    bg=10000*(bp[:-1]-bp[1:])/mid
    ag=10000*(ap[1:]-ap[:-1])/mid
    return np.asarray([bg[0]-ag[0],bg[1]-ag[1],np.mean(bg[:9])-np.mean(ag[:9]),np.mean(bg[:49])-np.mean(ag[:49])])

def depth_centroid_entropy(book: BookSnapshot) -> np.ndarray:
    bp,bq,ap,aq=validate_book(book,min_levels=50)
    mid,_,_=mid_spread(book)
    bd=10000*np.abs(bp[:50]-mid)/mid; ad=10000*np.abs(ap[:50]-mid)/mid
    wb=bq[:50]/max(float(np.sum(bq[:50])),EPS); wa=aq[:50]/max(float(np.sum(aq[:50])),EPS)
    cb=float(np.dot(wb,bd)); ca=float(np.dot(wa,ad))
    hb=-float(np.sum(np.where(wb>0,wb*np.log(wb),0.0)))/math.log(50)
    ha=-float(np.sum(np.where(wa>0,wa*np.log(wa),0.0)))/math.log(50)
    return np.asarray([cb,ca,ca-cb,hb,ha,hb-ha])

def event_transition_contrasts(events: Sequence[str]) -> np.ndarray:
    idx={x:i for i,x in enumerate(EVENT_ALPHABET)}
    counts=np.zeros((8,8),dtype=np.float64)
    for a,b in zip(events[:-1],events[1:]):
        if a not in idx or b not in idx: raise E1AFeatureError("invalid_event_class")
        counts[idx[a],idx[b]]+=1
    out=[]
    for i in range(8):
        den=float(np.sum(counts[i]))
        if den<=0:
            out.extend((0.0,0.0)); continue
        p=counts[i]/den
        bid=float(np.sum(p[:4])); ask=float(np.sum(p[4:]))
        add=float(p[0]+p[2]+p[4]+p[6]); rem=float(p[1]+p[3]+p[5]+p[7])
        out.extend((bid-ask,add-rem))
    return np.asarray(out)

def interarrival_moments(times_seconds: Sequence[float]) -> np.ndarray:
    t=np.asarray(times_seconds,dtype=np.float64)
    if t.ndim!=1 or np.any(~np.isfinite(t)): raise E1AFeatureError("invalid_event_times")
    if len(t)<2:return np.asarray([32.0,0.0,0.0])
    t=np.sort(t); d=np.diff(t)
    if np.any(d<0): raise E1AFeatureError("invalid_event_interarrival")
    mean=float(np.mean(d)); std=float(np.std(d))
    return np.asarray([mean,std,0.0 if mean<=0 else std/mean])

def burstiness_fano(times_seconds: Sequence[float]) -> np.ndarray:
    m=interarrival_moments(times_seconds); mean,std=float(m[0]),float(m[1])
    B=0.0 if mean+std<=0 else (std-mean)/(std+mean)
    t=np.asarray(times_seconds,dtype=np.float64)
    bins=np.histogram(t,bins=np.linspace(0,32,9))[0].astype(float)
    bm=float(np.mean(bins)); fano=0.0 if bm<=0 else float(np.var(bins)/bm)
    return np.asarray([B,fano])

def exponential_intensities(ages_seconds: Sequence[float], taus: Sequence[float]=TAUS_SECONDS) -> np.ndarray:
    a=np.asarray(ages_seconds,dtype=np.float64)
    if a.ndim!=1 or np.any(~np.isfinite(a)) or np.any(a<0) or np.any(a>32):
        raise E1AFeatureError("invalid_event_ages")
    return np.asarray([float(np.sum(np.exp(-a/tau))) for tau in taus])

def multiscale_intensity_ratios(counts: Mapping[float,float]) -> np.ndarray:
    for w in (1.0,4.0,16.0,32.0):
        if w not in counts or counts[w]<0: raise E1AFeatureError("invalid_multiscale_counts")
    i1=float(counts[1.0])/1.0; i4=float(counts[4.0])/4.0
    i16=float(counts[16.0])/16.0; i32=float(counts[32.0])/32.0
    return np.asarray([min(32.0,i1/(i16+EPS)),min(32.0,i4/(i32+EPS))])

def cosine_or_zero(a: Sequence[float],b: Sequence[float])->float:
    a=np.asarray(a,dtype=np.float64); b=np.asarray(b,dtype=np.float64)
    if a.shape!=b.shape or a.ndim!=1: raise E1AFeatureError("cosine_shape")
    den=float(np.linalg.norm(a)*np.linalg.norm(b))
    return 0.0 if den<=0 else float(np.dot(a,b)/den)

def stationary_flow_temporal_shape(vectors: Sequence[Sequence[float]]) -> np.ndarray:
    if len(vectors)!=4: raise E1AFeatureError("temporal_shape_band_count")
    vs=[np.asarray(x,dtype=np.float64) for x in vectors]
    if any(x.shape!=(10,) or np.any(~np.isfinite(x)) for x in vs): raise E1AFeatureError("temporal_shape_vector")
    totals=[float(np.sum(x)) for x in vs]
    norms=[float(np.sum(np.abs(x))) for x in vs]
    cos=[cosine_or_zero(vs[i],vs[i+1]) for i in range(3)]
    near_deep=[float(np.sum(x[:3])-np.sum(x[7:10])) for x in vs]
    return np.asarray(totals+norms+cos+near_deep)

def event_pressure_temporal_shape(pressures: np.ndarray) -> np.ndarray:
    p=np.asarray(pressures,dtype=np.float64)
    if p.shape!=(4,4) or np.any(~np.isfinite(p)): raise E1AFeatureError("pressure_shape")
    # rows=time bands, cols=insert/delete/replenish/deplete
    mids=np.asarray([0.5,2.5,10.0,24.0])
    base=p.reshape(-1)
    extras=[]
    for j in range(4):
        extras.append(float(p[0,j]-p[3,j]))
        extras.append(_ols_slope(mids,p[:,j]))
    return np.concatenate([base,np.asarray(extras)])

def strategy_feature_counts() -> dict[str,int]:
    return {
      "S00":23,"S01":26,"S02":49,"S03":13,
      "S04":1,"S05":7,"S06":2,"S07":7,
      "S08":5,"S09":5,"S10":4,
      "S11":10,"S12":20,"S13":4,"S14":10,"S15":40,
      "S16":2,"S17":2,"S18":4,"S19":4,"S20":6,
      "S21":8,"S22":6,"S23":4,"S24":16,
      "S25":12,"S26":8,"S27":8,"S28":8,
      "S29":16,"S30":6,"S31":6,
      "S32":4,"S33":4,"S34":15,"S35":24,
    }

def validate_strategy_registry() -> None:
    counts=strategy_feature_counts()
    if tuple(counts)!=STRATEGY_IDS: raise E1AFeatureError("strategy_registry_order")
    if len(counts)!=36 or any(v<=0 for v in counts.values()): raise E1AFeatureError("strategy_registry_count")

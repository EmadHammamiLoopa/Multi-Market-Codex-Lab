from __future__ import annotations

import math
from typing import Sequence

import numpy as np

EPS=1e-12
BAND_MIDS=np.asarray([0.5,2.5,10.0,24.0],dtype=np.float64)
MOMENTUM_LOG2_H=np.asarray([0.0,2.0,4.0,5.0],dtype=np.float64)

class E2AFeatureError(ValueError):
    pass

def _finite1(x:Sequence[float],n:int|None=None)->np.ndarray:
    a=np.asarray(x,dtype=np.float64)
    if a.ndim!=1 or (n is not None and a.shape!=(n,)) or not np.all(np.isfinite(a)):
        raise E2AFeatureError("invalid_vector")
    return a

def _slope(x:Sequence[float],y:Sequence[float])->float:
    a=_finite1(x); b=_finite1(y)
    if len(a)!=len(b) or len(a)<2:
        return 0.0
    xc=a-np.mean(a)
    den=float(np.dot(xc,xc))
    return 0.0 if den<=0 else float(np.dot(xc,b-np.mean(b))/den)

def queue_spread_state(obi7:Sequence[float],spread_bps:float)->np.ndarray:
    q=_finite1(obi7,7)
    s=float(spread_bps)
    if not math.isfinite(s) or s<=0:
        raise E2AFeatureError("invalid_spread")
    z=math.log1p(s)
    out=[]
    for v in q:
        out.extend((float(v),float(v)*z))
    return np.asarray(out,dtype=np.float64)

def queue_event_persistence(current_q:float,history_q:Sequence[float],history_t:Sequence[float])->np.ndarray:
    q=_finite1(history_q)
    t=_finite1(history_t)
    if len(q)!=len(t):
        raise E2AFeatureError("history_length")
    cq=float(current_q)
    if not math.isfinite(cq):
        raise E2AFeatureError("current_q")
    if len(q)==0:
        return np.asarray([cq,cq,0.0,0.0,0.0,0.0])
    mean=float(np.mean(q)); std=float(np.std(q))
    sign=np.sign(q); csign=np.sign(cq)
    same=float(np.mean((sign==csign)&(sign!=0)&(csign!=0)))
    persist=0.0 if len(q)<2 else float(np.mean(sign[1:]==sign[:-1]))
    sl=_slope(t,q) if len(np.unique(t))>=2 else 0.0
    return np.asarray([cq,mean,std,same,persist,sl])

def microprice_queue_interaction(norm_micro5:Sequence[float],obi5:Sequence[float])->np.ndarray:
    m=_finite1(norm_micro5,5); q=_finite1(obi5,5)
    out=[]
    for a,b in zip(m,q):
        out.extend((float(a),float(a*b)))
    return np.asarray(out)

def microprice_acceleration_curvature(band_means:Sequence[float])->np.ndarray:
    m=_finite1(band_means,4)
    d01=float(m[0]-m[1]); d12=float(m[1]-m[2]); d23=float(m[2]-m[3])
    c=float(np.polyfit(BAND_MIDS,m,2)[0])
    return np.asarray([d01,d12,d23,d01-d12,d12-d23,c])

def depth_dispersion(prices:Sequence[float],qty:Sequence[float],mid:float)->tuple[float,float]:
    p=_finite1(prices,50); q=_finite1(qty,50)
    m=float(mid)
    if not math.isfinite(m) or m<=0 or np.any(q<0) or float(np.sum(q))<=0:
        raise E2AFeatureError("invalid_depth")
    w=q/float(np.sum(q))
    d=10000.0*np.abs(p-m)/m
    mu=float(np.dot(w,d))
    var=float(np.dot(w,(d-mu)**2))
    return var,math.sqrt(max(var,0.0))

def depth_dispersion_block(
    bid_prices:Sequence[float],bid_qty:Sequence[float],
    ask_prices:Sequence[float],ask_qty:Sequence[float],mid:float,
)->np.ndarray:
    bv,bs=depth_dispersion(bid_prices,bid_qty,mid)
    av,ass=depth_dispersion(ask_prices,ask_qty,mid)
    return np.asarray([bv,av,av-bv,bs,ass,ass-bs])

PRESSURE_SIGN={
    "BI":1,"BR":1,"AD":1,"AP":1,
    "AI":-1,"AR":-1,"BD":-1,"BP":-1,
}

def event_run_length_persistence(states:Sequence[str],ages_seconds:Sequence[float])->np.ndarray:
    if len(states)!=len(ages_seconds):
        raise E2AFeatureError("state_age_length")
    if len(states)==0:
        return np.asarray([0,0,0,0,0,0,0,32],dtype=np.float64)
    ages=_finite1(ages_seconds)
    if np.any(ages<0) or np.any(ages>32):
        raise E2AFeatureError("age_range")
    try:
        signs=np.asarray([PRESSURE_SIGN[s] for s in states],dtype=np.int8)
    except KeyError as exc:
        raise E2AFeatureError("state") from exc

    current_state=states[-1]
    state_run=1
    for s in reversed(states[:-1]):
        if s!=current_state: break
        state_run+=1

    current_sign=int(signs[-1])
    sign_run=1
    for s in reversed(signs[:-1]):
        if int(s)!=current_sign: break
        sign_run+=1

    runs=[]
    run_signs=[]
    start=0
    for i in range(1,len(signs)+1):
        if i==len(signs) or signs[i]!=signs[start]:
            runs.append(i-start)
            run_signs.append(int(signs[start]))
            start=i
    maxrun=float(max(runs))
    meanrun=float(np.mean(runs))
    trans=0.0 if len(signs)<2 else float(np.mean(signs[1:]==signs[:-1]))
    fracpos=float(np.mean(signs>0))
    signed=(sum(r for r,s in zip(runs,run_signs) if s>0)-sum(r for r,s in zip(runs,run_signs) if s<0))/max(float(sum(runs)),EPS)

    since_change=32.0
    if len(signs)>=2:
        for i in range(len(signs)-2,-1,-1):
            if signs[i]!=signs[-1]:
                since_change=float(ages[i]-ages[-1]) if ages[i]>=ages[-1] else float(ages[-1]-ages[i])
                break
    return np.asarray([state_run,sign_run,maxrun,meanrun,trans,fracpos,signed,np.clip(since_change,0,32)],dtype=np.float64)

def signed_event_time_momentum(
    event_ages:Sequence[float],
    event_signs:Sequence[int],
    absdq:Sequence[float],
)->np.ndarray:
    a=_finite1(event_ages); s=np.asarray(event_signs,dtype=np.int8); q=_finite1(absdq)
    if len(a)!=len(s) or len(a)!=len(q) or np.any(a<0) or np.any(a>32) or np.any(q<0):
        raise E2AFeatureError("momentum_input")
    if not np.all(np.isin(s,(-1,1))):
        raise E2AFeatureError("momentum_sign")
    vals=[]
    for w in (1.0,4.0,16.0,32.0):
        mask=a<=w
        den=float(np.sum(q[mask]))
        vals.append(0.0 if den<=0 else float(np.sum(s[mask]*q[mask])/den))
    v=np.asarray(vals)
    slope=_slope(MOMENTUM_LOG2_H,v)
    return np.asarray([v[0],v[1],v[2],v[3],v[0]-v[1],v[1]-v[2],v[2]-v[3],slope])

def recovery_curve_block(
    r1:float,r4:float,r16:float,rcurrent:float,age:float,
)->np.ndarray:
    vals=np.asarray([r1,r4,r16,rcurrent],dtype=np.float64)
    if not np.all(np.isfinite(vals)) or not math.isfinite(age):
        raise E2AFeatureError("recovery_input")
    vals=np.clip(vals,-1,2)
    age=float(np.clip(age,0,32))
    xs=[1.0,4.0,16.0]
    ys=[float(vals[0]),float(vals[1]),float(vals[2])]
    if all(abs(age-x)>1e-12 for x in xs):
        xs.append(age); ys.append(float(vals[3]))
    else:
        idx=min(range(3),key=lambda i:abs(xs[i]-age))
        ys[idx]=float(vals[3])
    sl=_slope(xs,ys)
    return np.asarray([vals[0],vals[1],vals[2],vals[3],sl,age])

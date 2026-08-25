from __future__ import annotations

import argparse, hashlib, json, math
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler

from .codex_exp004_headroom import DAYS, SYMBOLS, assert_fresh_output, assert_frozen_workspace, executable_fixed_horizon, feature_path, input_manifest
from .codex_research import canonical_sha256
from .v23_phase0dl_score import BLOCKS, DayData, _load_day

EXPERIMENT_ID = "CODEX-EXP-004-P1"
GRID_US = 250_000
DECISION_STEP_S = 60
DECISION_STEP_ROWS = 240
HORIZON_S = 600
LABEL_THRESHOLD_BPS = 24.0
SEED = 20260825
OUTER_DAYS = DAYS[2:]
RETURN_LOOKBACK_MIN = (1,3,5,10,30)
RV_WINDOWS_MIN = (5,15,30)
SPREAD_MEAN_MIN = (1,5)
RANGE_WINDOWS_MIN = (5,15,30)

R_FEATURE_NAMES = (
    *(f"ret_{m}m_bps" for m in RETURN_LOOKBACK_MIN),
    *(f"abs_ret_{m}m_bps" for m in RETURN_LOOKBACK_MIN),
    *(f"rv_{m}m_bps" for m in RV_WINDOWS_MIN),
    "spread_bps",
    *(f"spread_mean_{m}m_bps" for m in SPREAD_MEAN_MIN),
    *(f"range_{m}m_bps" for m in RANGE_WINDOWS_MIN),
    *(f"range_position_{m}m" for m in RANGE_WINDOWS_MIN),
)
RL2_CURRENT_NAMES = (
    "microprice_minus_mid_bps","obi_l1","obi_l5","obi_l10","ofi_l1_1s","ofi_l1_3s",
    "mlofi_l5_1s","mlofi_l5_3s","trade_qty_imbalance_1s","trade_qty_imbalance_3s",
    "trade_count_imbalance_1s","trade_count_imbalance_3s","log_bid_depth_l5","log_ask_depth_l5",
)
RL2_ROLL_NAMES = ("obi_l5","ofi_l1_1s","trade_qty_imbalance_1s")
RL2_EXTRA_NAMES = RL2_CURRENT_NAMES + tuple(x for n in RL2_ROLL_NAMES for x in (f"{n}_mean_1m",f"{n}_std_1m"))
RL2_FEATURE_NAMES = R_FEATURE_NAMES + RL2_EXTRA_NAMES
SIGNED_R_FEATURES = tuple(f"ret_{m}m_bps" for m in RETURN_LOOKBACK_MIN)

@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbols: tuple[str,...] = SYMBOLS
    days: tuple[str,...] = tuple(d.isoformat() for d in DAYS)
    outer_days: tuple[str,...] = tuple(d.isoformat() for d in OUTER_DAYS)
    horizon_s: int = HORIZON_S
    decision_step_s: int = DECISION_STEP_S
    label_threshold_bps: float = LABEL_THRESHOLD_BPS
    r_features: tuple[str,...] = R_FEATURE_NAMES
    rl2_features: tuple[str,...] = RL2_FEATURE_NAMES
    model_c: float = 1.0
    solver: str = "lbfgs"
    class_weight: str | None = None
    max_iter: int = 1000
    seed: int = SEED

@dataclass
class DayDataset:
    symbol: str
    day: date
    timestamp_us: np.ndarray
    X_R: np.ndarray
    X_RL2: np.ndarray
    y: np.ndarray
    oracle_gross_bps: np.ndarray
    valid_R: np.ndarray
    valid_RL2: np.ndarray
    nonoverlap_10m: np.ndarray

class FixedLogistic:
    def __init__(self):
        self.scaler = StandardScaler()
        self.model = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", class_weight=None, max_iter=1000, random_state=SEED)
    def fit(self,X,y):
        X=np.asarray(X,float); y=np.asarray(y,np.int8)
        if len(X)<2 or np.unique(y).size!=2: raise RuntimeError("invalid training labels")
        self.model.fit(self.scaler.fit_transform(X),y); return self
    def predict_proba(self,X):
        return self.model.predict_proba(self.scaler.transform(np.asarray(X,float)))[:,1]

def _l2_pos(): return {n:i for i,n in enumerate(BLOCKS["L2"])}

def _spread(day):
    out=np.full(len(day.mid),np.nan)
    ok=day.book_valid & np.isfinite(day.bid)&np.isfinite(day.ask)&np.isfinite(day.mid)&(day.bid>0)&(day.ask>0)&(day.mid>0)
    out[ok]=10000*(day.ask[ok]-day.bid[ok])/day.mid[ok]
    return out

def _full(mask,start,end): return start>=0 and end<len(mask) and bool(np.all(mask[start:end+1]))

def _rv(mid,current,m):
    idx=current-np.arange(m,-1,-1,dtype=np.int64)*DECISION_STEP_ROWS
    r=np.diff(np.log(mid[idx])); return float(10000*np.sqrt(np.sum(r*r)))

def _range(mid,current,m):
    rows=m*DECISION_STEP_ROWS; v=mid[current-rows:current+1]; lo=float(v.min()); hi=float(v.max())
    return float(10000*np.log(hi/lo)), (0.5 if hi==lo else float((mid[current]-lo)/(hi-lo)))

def _r_features(day,current,spread):
    maxm=max(RETURN_LOOKBACK_MIN+RV_WINDOWS_MIN+SPREAD_MEAN_MIN+RANGE_WINDOWS_MIN); start=current-maxm*DECISION_STEP_ROWS
    if not _full(day.book_valid,start,current): return None
    mids=day.mid[start:current+1]
    if np.any(~np.isfinite(mids)) or np.any(mids<=0): return None
    s0=current-max(SPREAD_MEAN_MIN)*DECISION_STEP_ROWS
    if np.any(~np.isfinite(spread[s0:current+1])): return None
    rets=[float(10000*np.log(day.mid[current]/day.mid[current-m*DECISION_STEP_ROWS])) for m in RETURN_LOOKBACK_MIN]
    vals=rets+[abs(x) for x in rets]+[_rv(day.mid,current,m) for m in RV_WINDOWS_MIN]+[float(spread[current])]
    vals += [float(np.mean(spread[current-m*DECISION_STEP_ROWS:current+1])) for m in SPREAD_MEAN_MIN]
    rp=[_range(day.mid,current,m) for m in RANGE_WINDOWS_MIN]; vals += [x[0] for x in rp]+[x[1] for x in rp]
    a=np.asarray(vals,float); return a if len(a)==len(R_FEATURE_NAMES) and np.all(np.isfinite(a)) else None

def _rl2_extras(day,current,pos):
    start=current-DECISION_STEP_ROWS
    if start<0 or not np.all(day.valid["L2"][start:current+1]): return None
    X=day.X["L2"]; names=tuple(dict.fromkeys(RL2_CURRENT_NAMES+RL2_ROLL_NAMES)); cols=[pos[n] for n in names]
    if np.any(~np.isfinite(X[start:current+1,cols])): return None
    vals=[float(X[current,pos[n]]) for n in RL2_CURRENT_NAMES]
    for n in RL2_ROLL_NAMES:
        s=X[start:current+1,pos[n]].astype(float,copy=False); vals += [float(np.mean(s)),float(np.std(s))]
    a=np.asarray(vals,float); return a if len(a)==len(RL2_EXTRA_NAMES) and np.all(np.isfinite(a)) else None

def build_day_dataset(symbol,day):
    decisions=np.arange(0,len(day.ts),DECISION_STEP_ROWS,dtype=np.int64)
    out=executable_fixed_horizon(day,decisions,HORIZON_S); label_valid=out["valid"] & np.isfinite(out["oracle_gross_bps"])
    oracle=out["oracle_gross_bps"].astype(float,copy=False); y=(oracle>=LABEL_THRESHOLD_BPS).astype(np.int8)
    spread=_spread(day); pos=_l2_pos(); XR=np.full((len(decisions),len(R_FEATURE_NAMES)),np.nan); XL=np.full((len(decisions),len(RL2_FEATURE_NAMES)),np.nan)
    vr=np.zeros(len(decisions),bool); vl=np.zeros(len(decisions),bool)
    for j,current in enumerate(decisions.tolist()):
        if not label_valid[j]: continue
        r=_r_features(day,current,spread)
        if r is None: continue
        XR[j]=r; vr[j]=True
        e=_rl2_extras(day,current,pos)
        if e is not None: XL[j]=np.concatenate((r,e)); vl[j]=True
    minute=decisions//DECISION_STEP_ROWS
    return DayDataset(symbol,day.day,day.ts[decisions].astype(np.int64),XR,XL,y,oracle,vr,vl,(minute%10)==0)

def _concat(days,track):
    xs=[]; ys=[]; mags=[]
    for d in days:
        m=d.valid_R if track=="R" else d.valid_RL2; X=d.X_R if track=="R" else d.X_RL2
        xs.append(X[m]); ys.append(d.y[m]); mags.append(d.oracle_gross_bps[m])
    return np.concatenate(xs),np.concatenate(ys),np.concatenate(mags)

def _stable_seed(symbol,day): return int.from_bytes(hashlib.sha256(f"{SEED}|{symbol}|{day}".encode()).digest()[:8],"big")%(2**32)
def _permuted(days):
    parts=[]
    for d in days:
        y=d.y[d.valid_R].copy(); rng=np.random.default_rng(_stable_seed(d.symbol,d.day.isoformat())); parts.append(y[rng.permutation(len(y))])
    return np.concatenate(parts)

def _top(y,p,f):
    prev=float(np.mean(y)); k=max(1,int(math.ceil(len(y)*f))); idx=np.argsort(-p,kind="mergesort")[:k]; prec=float(np.mean(y[idx])); return prec,(prec/prev if prev>0 else None)
def _cal(y,p):
    if len(y)<10 or np.unique(y).size!=2:return {"intercept":None,"slope":None}
    z=np.log(np.clip(p,1e-6,1-1e-6)/(1-np.clip(p,1e-6,1-1e-6))).reshape(-1,1); m=LogisticRegression(C=1e6,solver="lbfgs",max_iter=1000).fit(z,y)
    return {"intercept":float(m.intercept_[0]),"slope":float(m.coef_[0,0])}
def score(y,p):
    y=np.asarray(y,np.int8); p=np.asarray(p,float); ok=np.isfinite(p); y=y[ok]; p=p[ok]; prev=float(np.mean(y)) if len(y) else None
    if len(y)==0 or np.unique(y).size!=2:return {"n":int(len(y)),"prevalence":prev,"roc_auc":None,"average_precision":None,"average_precision_over_prevalence":None,"brier_score":None,"brier_skill_score":None,"log_loss":None,"top_decile_precision":None,"top_decile_lift":None,"top_quintile_precision":None,"top_quintile_lift":None,"calibration":{"intercept":None,"slope":None}}
    auc=float(roc_auc_score(y,p)); ap=float(average_precision_score(y,p)); b=float(brier_score_loss(y,p)); base=float(np.mean((y-prev)**2)); d1,l1=_top(y,p,.1); d2,l2=_top(y,p,.2)
    return {"n":int(len(y)),"prevalence":prev,"roc_auc":auc,"average_precision":ap,"average_precision_over_prevalence":ap/prev if prev>0 else None,"brier_score":b,"brier_skill_score":1-b/base if base>0 else None,"log_loss":float(log_loss(y,np.clip(p,1e-12,1-1e-12))),"top_decile_precision":d1,"top_decile_lift":l1,"top_quintile_precision":d2,"top_quintile_lift":l2,"calibration":_cal(y,p)}
def metrics(records,key):
    def s(rows):return score([r["label"] for r in rows],[r[key] for r in rows])
    non=[r for r in records if r["nonoverlap_10m"]]
    return {"pooled":s(records),"by_symbol":{z:s([r for r in records if r["symbol"]==z]) for z in SYMBOLS},"by_fold":{d.isoformat():s([r for r in records if r["outer_day"]==d.isoformat()]) for d in OUTER_DAYS},"nonoverlap_pooled":s(non)}
def gates(m):
    ge=lambda v,t:v is not None and v>=t; gt=lambda v,t:v is not None and v>t; p=m["pooled"]; f=m["by_fold"]; s=m["by_symbol"]; n=m["nonoverlap_pooled"]
    return {"pooled_auc_at_least_0_60":ge(p["roc_auc"],.60),"pooled_ap_at_least_1_30x_prevalence":ge(p["average_precision_over_prevalence"],1.30),"pooled_brier_skill_positive":gt(p["brier_skill_score"],0),"pooled_top_decile_lift_at_least_1_50":ge(p["top_decile_lift"],1.50),"at_least_4_of_5_folds_auc_gt_0_55":sum(gt(x["roc_auc"],.55) for x in f.values())>=4,"at_least_4_of_5_folds_top_decile_lift_gt_1":sum(gt(x["top_decile_lift"],1) for x in f.values())>=4,"both_symbols_auc_at_least_0_57":all(ge(s[z]["roc_auc"],.57) for z in SYMBOLS),"both_symbols_top_decile_lift_at_least_1_25":all(ge(s[z]["top_decile_lift"],1.25) for z in SYMBOLS),"nonoverlap_pooled_auc_at_least_0_57":ge(n["roc_auc"],.57),"nonoverlap_top_decile_lift_at_least_1_25":ge(n["top_decile_lift"],1.25)}

def run(feature_dir,output,workspace,frozen_commit):
    assert_frozen_workspace(workspace,frozen_commit); partial=assert_fresh_output(output); manifest=input_manifest(feature_dir,workspace)
    data={}
    for symbol in SYMBOLS:
        for day in DAYS:data[(symbol,day)]=build_day_dataset(symbol,_load_day(feature_path(feature_dir,symbol,day),day))
    records=[]; train_counts=[]
    for outer_day in OUTER_DAYS:
        train_calendar=[d for d in DAYS if d<outer_day]
        for symbol in SYMBOLS:
            train=[data[(symbol,d)] for d in train_calendar]; outer=data[(symbol,outer_day)]
            XR,yR,mag=_concat(train,"R"); XL,yL,_=_concat(train,"RL2")
            r=FixedLogistic().fit(XR,yR); l=FixedLogistic().fit(XL,yL); vi=R_FEATURE_NAMES.index("rv_30m_bps"); vol=FixedLogistic().fit(XR[:,[vi]],yR); plac=FixedLogistic().fit(XR,_permuted(train)); can=FixedLogistic().fit(np.column_stack((XR,mag)),yR)
            rm=outer.valid_R; lm=outer.valid_RL2; ridx=np.flatnonzero(rm); lidx=np.flatnonzero(lm); lookup={int(x):j for j,x in enumerate(lidx.tolist())}
            XRO=outer.X_R[rm]; probr=r.predict_proba(XRO); probv=vol.predict_proba(XRO[:,[vi]]); probp=plac.predict_proba(XRO); probc=can.predict_proba(np.column_stack((XRO,outer.oracle_gross_bps[rm])))
            signed=[R_FEATURE_NAMES.index(n) for n in SIGNED_R_FEATURES]; signX=XRO.copy(); signX[:,signed]*=-1; probs=r.predict_proba(signX); probl=l.predict_proba(outer.X_RL2[lm])
            train_counts.append({"outer_day":outer_day.isoformat(),"symbol":symbol,"R_train_n":int(len(yR)),"RL2_train_n":int(len(yL)),"R_outer_n":int(rm.sum()),"RL2_outer_n":int(lm.sum())})
            for j,idx in enumerate(ridx.tolist()):
                rec={"outer_day":outer_day.isoformat(),"symbol":symbol,"timestamp_us":int(outer.timestamp_us[idx]),"label":int(outer.y[idx]),"oracle_gross_bps":float(outer.oracle_gross_bps[idx]),"nonoverlap_10m":bool(outer.nonoverlap_10m[idx]),"p_R":float(probr[j]),"p_VOL":float(probv[j]),"p_PLACEBO_R":float(probp[j]),"p_CANARY_R":float(probc[j]),"p_SIGN_R":float(probs[j]),"p_RL2":None}
                if idx in lookup:rec["p_RL2"]=float(probl[lookup[idx]])
                records.append(rec)
    M={k:metrics(records,v) for k,v in {"R":"p_R","VOL":"p_VOL","PLACEBO_R":"p_PLACEBO_R","CANARY_R":"p_CANARY_R","SIGN_R":"p_SIGN_R"}.items()}
    common=[r for r in records if r["p_RL2"] is not None]; M["R_COMMON_RL2"]=metrics(common,"p_R"); M["RL2"]=metrics(common,"p_RL2")
    rg=gates(M["R"]); lg=gates(M["RL2"]); rp=M["R"]["pooled"]; rc=M["R_COMMON_RL2"]["pooled"]; lp=M["RL2"]["pooled"]; pp=M["PLACEBO_R"]["pooled"]; cp=M["CANARY_R"]["pooled"]; sp=M["SIGN_R"]["pooled"]
    inc={"auc_delta_at_least_0_01":lp["roc_auc"] is not None and rc["roc_auc"] is not None and lp["roc_auc"]-rc["roc_auc"]>=.01,"average_precision_delta_at_least_0_01":lp["average_precision"] is not None and rc["average_precision"] is not None and lp["average_precision"]-rc["average_precision"]>=.01,"top_decile_precision_not_lower":lp["top_decile_precision"] is not None and rc["top_decile_precision"] is not None and lp["top_decile_precision"]>=rc["top_decile_precision"]}
    td=rp["roc_auc"]-pp["roc_auc"] if rp["roc_auc"] is not None and pp["roc_auc"] is not None else None; cd=cp["roc_auc"]-rp["roc_auc"] if cp["roc_auc"] is not None and rp["roc_auc"] is not None else None
    sign_all=all(sp[k] is not None and rp[k] is not None and sp[k]>rp[k] for k in ("roc_auc","average_precision","top_decile_lift")); dg={"real_auc_exceeds_time_placebo_by_at_least_0_03":td is not None and td>=.03,"future_canary_auc_improves_by_at_least_0_10":cd is not None and cd>=.10,"signed_feature_inversion_does_not_improve_all_primary_discrimination_metrics":not sign_all}
    rpass=all(rg.values()); lpass=all(lg.values()); ipass=all(inc.values()); dpass=all(dg.values()); status="PREDICTABLE_SANDBOX_R" if dpass and rpass else ("PREDICTABLE_SANDBOX_RL2_ONLY" if dpass and (not rpass) and lpass and ipass else "FAIL_OPPORTUNITY_NOT_PREDICTABLE")
    payload={"experiment_id":EXPERIMENT_ID,"status":status,"sandbox_only":True,"direction_scored":False,"pnl_scored":False,"frozen_commit":frozen_commit,"executed_at_utc":datetime.now(timezone.utc).isoformat(),"configuration":asdict(Config()),"configuration_sha256":canonical_sha256(Config()),"input_manifest":manifest,"fold_train_counts":train_counts,"metrics":M,"gates":{"R_absolute":rg,"RL2_absolute":lg,"RL2_incremental_common_support":inc,"diagnostics":dg,"R_pass":rpass,"RL2_absolute_pass":lpass,"RL2_incremental_pass":ipass,"diagnostics_pass":dpass},"diagnostic_deltas":{"R_auc_minus_time_placebo_auc":td,"future_canary_auc_minus_R_auc":cd,"sign_inversion_improves_all_primary_discrimination_metrics":sign_all},"oos_prediction_records_sha256":canonical_sha256(records),"oos_prediction_records":records,"interpretation":"Opportunity occurrence only; no direction, PnL, validation, or August access."}
    output.parent.mkdir(parents=True,exist_ok=True); partial.write_text(json.dumps(payload,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8"); partial.replace(output); return payload

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--feature-dir",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--workspace",type=Path,required=True); p.add_argument("--frozen-commit",required=True); a=p.parse_args(argv); r=run(a.feature_dir,a.output,a.workspace,a.frozen_commit); print(json.dumps({"experiment_id":r["experiment_id"],"status":r["status"],"R_pooled_auc":r["metrics"]["R"]["pooled"]["roc_auc"],"R_top_decile_lift":r["metrics"]["R"]["pooled"]["top_decile_lift"],"RL2_pooled_auc":r["metrics"]["RL2"]["pooled"]["roc_auc"],"diagnostics_pass":r["gates"]["diagnostics_pass"]},indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())

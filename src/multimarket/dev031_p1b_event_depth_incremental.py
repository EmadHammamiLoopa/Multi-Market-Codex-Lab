from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv, hashlib, json, os, struct, sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    log_loss,brier_score_loss,roc_auc_score,balanced_accuracy_score,
    f1_score,matthews_corrcoef,precision_recall_fscore_support,confusion_matrix,
)

from . import dev030_direction_dataset as dd
from . import dev030_p3_direction as p3

EXPERIMENT_ID="DEV031-P1B"
DESIGN_VERSION="event-depth-incremental-direction-v1"
STATUS_FAIL="FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE"
STATUS_NULL_FAIL="FAIL_EVENT_DEPTH_DIRECTION_TEMPORAL_NULL"
STATUS_PASS="ELIGIBLE_EVENT_DEPTH_INCREMENTAL_DIRECTION_INFORMATION"

P1A_ROOT=Path("/home/emadh/Multi-Market/evidence/dev031_p1a_event_depth_materialization_v1")
P1A_MANIFEST=P1A_ROOT/"DEV031_P1A_EVENT_DEPTH_MATERIALIZATION.json"
P1A_SHA256="a8a4f89262b9f01e76fc10a1b9c54ac28dd7faec3180a1a0fac19499eb9467d8"
P3_ARTIFACT=Path("/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/DEV030_P3_CAMPAIGN1_RESULT.json")
P3_SHA256="f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e"

REAL_OUTPUT_DIRECTORY=Path("/home/emadh/Multi-Market/evidence/dev031_p1b_event_depth_incremental_v1")
ARTIFACT_FILENAME="DEV031_P1B_EVENT_DEPTH_INCREMENTAL_RESULT.json"

C_GRID=(0.01,0.1,1.0,10.0)
RANDOM_STATE=20260825
THRESHOLD=0.5
EXPECTED_P3_C={1:10.0,2:10.0,3:0.1,4:0.01}
EXPECTED_P3_HASH={
1:"e03d233bff936b49a0452994497f32ca5ecbe52c1f490d855fe8d06dbfa9dcf4",
2:"cd2cba0a6dcf3591ec9848b78e31aef796dad15d371bbecb8517aa2507340bdd",
3:"19f9acf70b0065a307c0373952cad350339768607a156c9307e5192503bb1f31",
4:"b05ee6e926d6a943e1fc89828eb3801af0863fa270bc2e5db5ed7cd93e9a4b66",
}
FORWARD_GUARDS={
"raw_l2_reopened":False,"aug01_opened":False,"aug30_opened":False,
"sep01_or_later_opened":False,"railway_opened":False,"archive_bucket_opened":False,
"abundant_love_opened":False,"exp024_filter_or_feature_used":False,
"p4_composition_run":False,"pnl_run":False,"threshold_optimization_run":False,
"feature_subset_search_run":False,"alternate_model_family_run":False,
}

class P1BError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason); super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class DayData:
    day:date; ts:np.ndarray; y:np.ndarray; c0:np.ndarray; c1:np.ndarray

@dataclass(frozen=True)
class FoldResult:
    fold_id:int; representation:str; selected_c:float; support:int; long_count:int; short_count:int
    metrics:dict[str,Any]; ts:np.ndarray; y:np.ndarray; p:np.ndarray; pred:np.ndarray
    support_sha256:str; label_sha256:str; prediction_sha256:str
    inner_c_ledger:tuple[dict[str,Any],...]

@dataclass(frozen=True)
class RepresentationResult:
    representation:str; folds:tuple[FoldResult,...]; pooled_metrics:dict[str,Any]

@dataclass(frozen=True)
class ArtifactWriteResult:
    output_directory:Path; artifact_path:Path; artifact_sha256:str; artifact_bytes:int

def _sha(path:Path)->str:
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()

def _load_json(path:Path,sha:str)->dict[str,Any]:
    if not path.is_file(): raise P1BError("artifact_missing",str(path))
    if _sha(path)!=sha: raise P1BError("artifact_sha256_mismatch",str(path))
    x=json.loads(path.read_text())
    if not isinstance(x,dict): raise P1BError("artifact_not_object")
    return x

def probability_metrics(y:Any,p:Any)->dict[str,Any]:
    y=np.asarray(y,dtype=np.int8); p=np.asarray(p,dtype=np.float64)
    if y.ndim!=1 or p.ndim!=1 or len(y)!=len(p) or len(y)==0: raise P1BError("metric_shape")
    if set(np.unique(y).tolist())!={0,1}: raise P1BError("metric_classes")
    if not np.all(np.isfinite(p)) or not np.all((p>=0)&(p<=1)): raise P1BError("metric_probability")
    pred=(p>=THRESHOLD).astype(np.int8)
    pr,re,f1,sup=precision_recall_fscore_support(y,pred,labels=[0,1],zero_division=0)
    return {
      "support":int(len(y)),"long_count":int(np.sum(y==1)),"short_count":int(np.sum(y==0)),
      "binary_log_loss":float(log_loss(y,np.column_stack((1-p,p)),labels=[0,1])),
      "brier":float(brier_score_loss(y,p)),"roc_auc":float(roc_auc_score(y,p)),
      "balanced_accuracy_at_0_5":float(balanced_accuracy_score(y,pred)),
      "macro_f1_at_0_5":float(f1_score(y,pred,average="macro",zero_division=0)),
      "mcc_at_0_5":float(matthews_corrcoef(y,pred)),
      "short":{"precision":float(pr[0]),"recall":float(re[0]),"f1":float(f1[0]),"support":int(sup[0])},
      "long":{"precision":float(pr[1]),"recall":float(re[1]),"f1":float(f1[1]),"support":int(sup[1])},
      "confusion_matrix_short_long_at_0_5":confusion_matrix(y,pred,labels=[0,1]).astype(int).tolist(),
    }

def label_sha256(ts:Any,y:Any)->str:
    ts=np.asarray(ts,dtype=np.int64); y=np.asarray(y,dtype=np.int8)
    h=hashlib.sha256(b"DEV031-P1B-LABEL-V1\0")
    h.update(struct.pack(">Q",len(ts)))
    for t,v in zip(ts.tolist(),y.tolist(),strict=True): h.update(struct.pack(">qb",int(t),int(v)))
    return h.hexdigest()

def prediction_sha256(fold_id:int,rep:str,ts:Any,y:Any,p:Any)->str:
    ts=np.asarray(ts,dtype=np.int64); y=np.asarray(y,dtype=np.int8); p=np.asarray(p,dtype=np.float64)
    h=hashlib.sha256(b"DEV031-P1B-OOF-PREDICTION-V1\0")
    h.update(f"{fold_id}|{rep}".encode())
    for t,v,q in zip(ts.tolist(),y.tolist(),p.tolist(),strict=True): h.update(struct.pack(">qbd",int(t),int(v),float(q)))
    return h.hexdigest()

def load_days()->tuple[dict[str,Any],dict[date,DayData]]:
    m=_load_json(P1A_MANIFEST,P1A_SHA256)
    if m.get("status")!="EVENT_DEPTH_EXACT_P3_SUPPORT_MATERIALIZED" or m.get("pass") is not True:
        raise P1BError("p1a_terminal_status")
    if m.get("p3_support_contract_reproduced_exactly") is not True: raise P1BError("p1a_support_contract")
    price=tuple(m["feature_names"]["price"]); event=tuple(m["feature_names"]["event_depth"])
    if len(price)!=23 or len(event)!=26: raise P1BError("feature_count")
    out={}
    for rec in m["days"]:
        d=date.fromisoformat(rec["day"]); path=P1A_ROOT/rec["file"]
        if _sha(path)!=rec["file_sha256"] or path.stat().st_size!=rec["file_bytes"]: raise P1BError("day_file_identity",d.isoformat())
        with path.open(newline="") as f:
            r=csv.reader(f); header=tuple(next(r)); rows=list(r)
        expected=("local_timestamp_us","t1_label")+price+event
        if header!=expected: raise P1BError("day_header",d.isoformat())
        ts=np.asarray([int(x[0]) for x in rows],dtype=np.int64)
        y=np.asarray([int(x[1]) for x in rows],dtype=np.int8)
        x=np.asarray([[float(v) for v in x[2:]] for x in rows],dtype=np.float64)
        if x.shape!=(len(ts),49) or not np.all(np.isfinite(x)): raise P1BError("day_matrix",d.isoformat())
        if dd.support_sha256(ts)!=rec["support_sha256"]: raise P1BError("day_support",d.isoformat())
        if not np.all(np.isin(y,(0,1))): raise P1BError("day_labels",d.isoformat())
        out[d]=DayData(d,ts,y,x[:,:23],x)
    if tuple(out)!=dd.HISTORICAL_DAYS: raise P1BError("day_calendar")
    return m,out

def _stack(per_day:Mapping[date,DayData],days:Sequence[date],rep:str):
    vals=[]; ys=[]; ts=[]
    for d in days:
        z=per_day[d]; vals.append(z.c0 if rep=="C0" else z.c1); ys.append(z.y); ts.append(z.ts)
    x=np.concatenate(vals); y=np.concatenate(ys); t=np.concatenate(ts)
    if len(t) and np.any(np.diff(t)<=0): raise P1BError("stack_chronology")
    return x,y,t

def _new(C:float)->LogisticRegression:
    return LogisticRegression(C=C,solver="lbfgs",l1_ratio=0.0,class_weight=None,max_iter=1000,fit_intercept=True,random_state=RANDOM_STATE)

def select_c(xf,yf,xv,yv):
    led=[]
    for C in C_GRID:
        s=StandardScaler(); a=s.fit_transform(xf); b=s.transform(xv)
        m=_new(C); m.fit(a,yf); p=m.predict_proba(b)[:,1]; q=probability_metrics(yv,p)
        led.append({"C":C,"binary_log_loss":q["binary_log_loss"],"brier":q["brier"],"roc_auc":q["roc_auc"]})
    z=sorted(led,key=lambda q:(q["binary_log_loss"],q["brier"],-q["roc_auc"],q["C"]))[0]
    return float(z["C"]),tuple(led)

def fit_fold(per_day,fold,rep):
    iv=fold.train_days[-1]; iff=fold.train_days[:-1]
    xif,yif,_=_stack(per_day,iff,rep); xiv,yiv,_=_stack(per_day,(iv,),rep)
    xt,yt,_=_stack(per_day,fold.train_days,rep); xv,yv,tv=_stack(per_day,(fold.validation_day,),rep)
    C,ledger=select_c(xif,yif,xiv,yiv)
    s=StandardScaler(); a=s.fit_transform(xt); b=s.transform(xv); m=_new(C); m.fit(a,yt)
    p=m.predict_proba(b)[:,1]; pred=(p>=0.5).astype(np.int8)
    return FoldResult(fold.fold_id,rep,C,len(yv),int(np.sum(yv==1)),int(np.sum(yv==0)),
      probability_metrics(yv,p),tv,yv,p,pred,dd.support_sha256(tv),label_sha256(tv,yv),
      prediction_sha256(fold.fold_id,rep,tv,yv,p),ledger)

def fit_rep(per_day,rep):
    fs=tuple(fit_fold(per_day,f,rep) for f in dd.OUTER_FOLDS)
    y=np.concatenate([f.y for f in fs]); p=np.concatenate([f.p for f in fs])
    return RepresentationResult(rep,fs,probability_metrics(y,p))

def reproduce_p3(per_day):
    spec=p3.CandidateSpec("A",120,16,32,"PRICE")
    result=[]
    for fold in dd.OUTER_FOLDS:
        xt,yt,_=_stack(per_day,fold.train_days,"C0"); xv,yv,tv=_stack(per_day,(fold.validation_day,),"C0")
        C=EXPECTED_P3_C[fold.fold_id]; s=StandardScaler(); a=s.fit_transform(xt); b=s.transform(xv)
        m=_new(C); m.fit(a,yt); p=m.predict_proba(b)[:,1]; pred=(p>=0.5).astype(np.int8)
        actual=p3.prediction_sha256(spec=spec,representation="S1",fold_id=fold.fold_id,timestamps_us=tv,y_true=yv,y_pred=pred,p_long=p)
        result.append({"fold_id":fold.fold_id,"selected_C":C,"expected":EXPECTED_P3_HASH[fold.fold_id],"actual":actual,"reproduced":actual==EXPECTED_P3_HASH[fold.fold_id]})
    return {"pass":all(x["reproduced"] for x in result),"folds":result}

def comparison(c0,c1):
    for a,b in zip(c0.folds,c1.folds,strict=True):
        if not np.array_equal(a.ts,b.ts) or not np.array_equal(a.y,b.y): raise P1BError("matched_support")
    pm0=c0.pooled_metrics; pm1=c1.pooled_metrics
    fll=[]; fb=[]; fa=[]
    for a,b in zip(c0.folds,c1.folds,strict=True):
        fll.append(a.metrics["binary_log_loss"]-b.metrics["binary_log_loss"])
        fb.append(a.metrics["brier"]-b.metrics["brier"])
        fa.append(b.metrics["roc_auc"]-a.metrics["roc_auc"])
    loo_ll=[]; loo_b=[]; loo_a=[]
    for o in range(4):
        y=np.concatenate([c0.folds[i].y for i in range(4) if i!=o])
        p0=np.concatenate([c0.folds[i].p for i in range(4) if i!=o]); p1=np.concatenate([c1.folds[i].p for i in range(4) if i!=o])
        a=probability_metrics(y,p0); b=probability_metrics(y,p1)
        loo_ll.append(a["binary_log_loss"]-b["binary_log_loss"]); loo_b.append(a["brier"]-b["brier"]); loo_a.append(b["roc_auc"]-a["roc_auc"])
    gates={
      "pooled_log_loss_better":pm0["binary_log_loss"]>pm1["binary_log_loss"],
      "pooled_brier_better":pm0["brier"]>pm1["brier"],
      "pooled_auc_better":pm1["roc_auc"]>pm0["roc_auc"],
      "pooled_c1_auc_at_least_056":pm1["roc_auc"]>=0.56,
      "at_least_3_of_4_fold_log_loss_improve":sum(x>0 for x in fll)>=3,
      "at_least_3_of_4_fold_brier_improve":sum(x>0 for x in fb)>=3,
      "at_least_3_of_4_fold_auc_improve":sum(x>0 for x in fa)>=3,
      "at_least_3_of_4_fold_c1_auc_gt_050":sum(f.metrics["roc_auc"]>0.5 for f in c1.folds)>=3,
      "loo_log_loss_positive":all(x>0 for x in loo_ll),"loo_brier_positive":all(x>0 for x in loo_b),"loo_auc_positive":all(x>0 for x in loo_a),
      "probability_noncollapsed":all(np.any(f.p>0)&np.any(f.p<1) for f in c1.folds),
    }
    return {"pooled_log_loss_improvement":pm0["binary_log_loss"]-pm1["binary_log_loss"],"pooled_brier_improvement":pm0["brier"]-pm1["brier"],
      "pooled_auc_delta":pm1["roc_auc"]-pm0["roc_auc"],"fold_log_loss_improvement":fll,"fold_brier_improvement":fb,"fold_auc_delta":fa,
      "leave_one_fold_out_log_loss_improvement":loo_ll,"leave_one_fold_out_brier_improvement":loo_b,"leave_one_fold_out_auc_delta":loo_a,
      "precheck_gates":gates,"precheck_pass":all(gates.values())}

def temporal_null(c0,c1,comp):
    sizes=[len(f.y) for f in c0.folds]; shifts=tuple(k for k in range(1,min(sizes)) if all(min(k,n-k)>=10 for n in sizes))
    p0=np.concatenate([f.p for f in c0.folds]); p1=np.concatenate([f.p for f in c1.folds]); vals=[]
    for k in shifts:
        y=np.concatenate([np.roll(f.y,k) for f in c0.folds])
        a=probability_metrics(y,p0); b=probability_metrics(y,p1); vals.append(a["binary_log_loss"]-b["binary_log_loss"])
    obs=comp["pooled_log_loss_improvement"]; q95=float(np.quantile(vals,0.95,method="higher")); ep=(1+sum(x>=obs for x in vals))/(1+len(vals))
    return {"eligible_shifts":list(shifts),"null_log_loss_improvement":vals,"q95":q95,"empirical_p":ep,"observed":obs,"pass":bool(obs>q95 and ep<=0.05)}

def _fold_public(f):
    return {"fold_id":f.fold_id,"selected_C":f.selected_c,"support":f.support,"long_count":f.long_count,"short_count":f.short_count,
      "metrics":f.metrics,"support_sha256":f.support_sha256,"label_sha256":f.label_sha256,"prediction_sha256":f.prediction_sha256,
      "inner_c_ledger":list(f.inner_c_ledger)}

def _write(output,payload):
    if output.exists() or output.is_symlink(): raise P1BError("output_directory_already_exists")
    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    output.mkdir(); final=output/ARTIFACT_FILENAME; final.write_bytes(content)
    return ArtifactWriteResult(output,final,hashlib.sha256(content).hexdigest(),len(content))

def run_p1b(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True)->ArtifactWriteResult:
    output=Path(output_directory)
    if require_canonical_output and output!=REAL_OUTPUT_DIRECTORY: raise P1BError("noncanonical_output_directory")
    if not require_canonical_output and output==REAL_OUTPUT_DIRECTORY: raise P1BError("canonical_output_requires_real_mode")
    if any(FORWARD_GUARDS.values()): raise P1BError("runtime_guard_violation")
    if len(execution_commit)!=40: raise P1BError("execution_commit")
    p1a,days=load_days(); p3a=_load_json(P3_ARTIFACT,P3_SHA256)
    if p1a["provenance"]["p3_artifact"]["sha256"]!=P3_SHA256: raise P1BError("p1a_p3_provenance")
    repro=reproduce_p3(days)
    if repro["pass"] is not True: raise P1BError("frozen_p3_reproduction_failed")
    c0=fit_rep(days,"C0"); c1=fit_rep(days,"C1"); comp=comparison(c0,c1)
    null=temporal_null(c0,c1,comp) if comp["precheck_pass"] else None
    status=STATUS_PASS if (null and null["pass"]) else (STATUS_NULL_FAIL if comp["precheck_pass"] else STATUS_FAIL)
    payload={"experiment_id":EXPERIMENT_ID,"design_version":DESIGN_VERSION,"status":status,"execution_commit":execution_commit,
      "environment":{"python":sys.version.split()[0],"numpy":np.__version__,"scikit_learn":sklearn.__version__},
      "p1a_artifact":{"path":str(P1A_MANIFEST),"sha256":P1A_SHA256},"p3_artifact":{"path":str(P3_ARTIFACT),"sha256":P3_SHA256},
      "p3_reproduction":repro,"c0":{"feature_count":23,"folds":[_fold_public(x) for x in c0.folds],"pooled":c0.pooled_metrics},
      "c1":{"feature_count":49,"folds":[_fold_public(x) for x in c1.folds],"pooled":c1.pooled_metrics},
      "comparison":comp,"temporal_null":null or {"status":"NOT_RUN_PRECHECK_FAILED"},"forward_guards":dict(FORWARD_GUARDS)}
    return _write(output,payload)

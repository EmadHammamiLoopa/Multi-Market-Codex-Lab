from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

import numpy as np
from sklearn.preprocessing import StandardScaler

from . import dev030_direction_dataset as dd
from . import dev030_p4_touch_composition as p4
from . import dev034_g3b_r1_core as g3core
from . import dev036_c1_core as core
from . import dev036_c1_loader as loader

EXPERIMENT_ID="DEV036-C1"
DESIGN_VERSION="promoted-direction-composition-confirmation-v1"

REAL_OUTPUT_DIRECTORY=Path(
    "/home/emadh/Multi-Market/evidence/dev036_c1_promoted_direction_composition_v1"
)
ARTIFACT_FILENAME="DEV036_C1_PROMOTED_DIRECTION_COMPOSITION_RESULT.json"

FORWARD_GUARDS={
    "aug30_reused":False,
    "sep01_or_later_opened":False,
    "railway_opened":False,
    "archive_bucket_opened":False,
    "abundant_love_opened":False,
    "pnl_run":False,
    "exp024_gate_run":False,
    "threshold_optimization_run":False,
    "calibration_rescue_run":False,
    "composition_weight_tuning_run":False,
}

class C1RunnerError(RuntimeError):
    def __init__(self,reason:str,detail:str|None=None):
        self.reason=str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

def _sha(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()

def _stack_direction(per_day,days):
    xs=[];ys=[];ts=[]
    for d in days:
        x,y,t=per_day[d]
        xs.append(x);ys.append(y);ts.append(t)
    return np.concatenate(xs),np.concatenate(ys),np.concatenate(ts)

def _direction_expected_hashes(g3b,which):
    if which=="P3":
        rows=g3b["base_comparator"]["folds"]
    else:
        row=next(z for z in g3b["leaderboard"] if z["candidate_id"]=="G3C16")
        rows=row["folds"]
    return {int(z["fold_id"]):z["prediction_sha256"] for z in rows}

def _fit_direction_fold(e,which,outer):
    per=loader.direction_per_day(e,which)
    inner_val=outer.train_days[-1]
    inner_fit=outer.train_days[:-1]

    xif,yif,_=_stack_direction(per,inner_fit)
    xiv,yiv,_=_stack_direction(per,(inner_val,))
    selected,ledger=g3core.select_c(xif,yif,xiv,yiv)

    xt,yt,_=_stack_direction(per,outer.train_days)
    xv_touch,yv_touch,tv_touch=_stack_direction(per,(outer.validation_day,))

    scaler=StandardScaler()
    a=scaler.fit_transform(xt)
    model=g3core._model(selected)
    model.fit(a,yt)

    p_touch=model.predict_proba(scaler.transform(xv_touch))[:,1]
    pred=(p_touch>=g3core.THRESHOLD).astype(np.int8)
    cid="P3_COMMON_SUPPORT_REFIT" if which=="P3" else "G3C16"
    actual=g3core.prediction_sha256(cid,outer.fold_id,tv_touch,yv_touch,pred,p_touch)

    all_x=(
        e.per_day[outer.validation_day].p3_x
        if which=="P3"
        else e.per_day[outer.validation_day].btc45_x
    )
    p_all=model.predict_proba(scaler.transform(all_x))[:,1]

    return {
        "fold_id":int(outer.fold_id),
        "selected_C":float(selected),
        "inner_c_ledger":list(ledger),
        "touch_timestamps_us":tv_touch,
        "touch_labels":yv_touch,
        "touch_probabilities":p_touch,
        "actual_prediction_sha256":actual,
        "all_row_probabilities":p_all,
    }

def _training_prevalence(e,days):
    y3=np.concatenate([e.per_day[d].y3 for d in days])
    counts=np.asarray([np.sum(y3==i) for i in (0,1,2)],dtype=np.float64)
    return counts/counts.sum()

def _training_direction_prior(e,days):
    y=np.concatenate([e.per_day[d].direction_y for d in days])
    return float(np.mean(y==1))

def _public_metrics(f):
    return {
        "fold_id":f.fold_id,
        "support":int(len(f.labels)),
        "metrics_c0":f.metrics_c0,
        "metrics_c1":f.metrics_c1,
        "metrics_c2":f.metrics_c2,
        "metrics_c3":f.metrics_c3,
    }

def run_c1(*,execution_commit:str,output_directory:Path=REAL_OUTPUT_DIRECTORY,require_canonical_output:bool=True):
    if any(FORWARD_GUARDS.values()): raise C1RunnerError("forward_guard")
    if len(execution_commit)!=40 or any(c not in "0123456789abcdef" for c in execution_commit):
        raise C1RunnerError("execution_commit")
    output=Path(output_directory)
    if require_canonical_output and output!=REAL_OUTPUT_DIRECTORY: raise C1RunnerError("noncanonical_output")
    if not require_canonical_output and output==REAL_OUTPUT_DIRECTORY: raise C1RunnerError("canonical_requires_real")
    if output.exists() or output.is_symlink(): raise C1RunnerError("output_exists")

    e=loader.load_c1()
    t2_per={d:e.per_day[d].t2 for d in dd.HISTORICAL_DAYS}
    touch=p4.fit_t2(t2_per)

    expected_p3=_direction_expected_hashes(e.g3b_payload,"P3")
    expected_45=_direction_expected_hashes(e.g3b_payload,"BTC45")

    folds=[]
    reproduction=[]
    for outer,touch_fold in zip(dd.OUTER_FOLDS,touch.s1_folds,strict=True):
        p3f=_fit_direction_fold(e,"P3",outer)
        p45f=_fit_direction_fold(e,"BTC45",outer)

        p3_ok=p3f["actual_prediction_sha256"]==expected_p3[outer.fold_id]
        p45_ok=p45f["actual_prediction_sha256"]==expected_45[outer.fold_id]
        reproduction.append({
            "fold_id":int(outer.fold_id),
            "p3_expected":expected_p3[outer.fold_id],
            "p3_actual":p3f["actual_prediction_sha256"],
            "p3_reproduced":bool(p3_ok),
            "g3c16_expected":expected_45[outer.fold_id],
            "g3c16_actual":p45f["actual_prediction_sha256"],
            "g3c16_reproduced":bool(p45_ok),
            "p3_selected_C":p3f["selected_C"],
            "g3c16_selected_C":p45f["selected_C"],
        })
        if not (p3_ok and p45_ok):
            raise C1RunnerError("direction_prediction_reproduction_failure",str(outer.fold_id))

        day=e.per_day[outer.validation_day]
        if not np.array_equal(day.t2.timestamps_us,touch_fold.timestamps_us):
            raise C1RunnerError("touch_validation_alignment",str(outer.fold_id))

        folds.append(core.fold_composition(
            fold_id=outer.fold_id,
            y3=day.y3,
            training_prevalence=_training_prevalence(e,outer.train_days),
            p_touch=touch_fold.p_touch,
            training_p_long=_training_direction_prior(e,outer.train_days),
            p3_long=p3f["all_row_probabilities"],
            btc45_long=p45f["all_row_probabilities"],
        ))

    folds=tuple(folds)
    vs_c2=core.comparison(folds,base_field="c2",test_field="c3")
    vs_c1=core.comparison(folds,base_field="c1",test_field="c3")
    null=core.directional_touch_temporal_null(folds)
    reproduction_ok=all(z["p3_reproduced"] and z["g3c16_reproduced"] for z in reproduction)
    status=core.classify(reproduction_ok=reproduction_ok,vs_c2=vs_c2,vs_c1=vs_c1,null=null)

    pooled={
        k:core._pooled(folds,k)
        for k in ("c0","c1","c2","c3")
    }

    payload={
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "status":status,
        "execution_commit":execution_commit,
        "parents":{
            "p4":{"path":str(loader.P4_ARTIFACT),"sha256":loader.P4_SHA256},
            "g3b_r1":{"path":str(loader.G3B_ARTIFACT),"sha256":loader.G3B_SHA256,"bytes":loader.G3B_BYTES},
        },
        "common_support":{
            "rows":9849,"touch":1341,"none":8508,
            "support_sha256":loader.COMMON_SUPPORT_SHA,
            "pooled_validation":{"rows":5628,"touch":559,"none":5069},
        },
        "touch_refit":{
            "identity":"P4_S1_SUPPORT_MATCHED_REFIT",
            "folds":[{
                "fold_id":int(f.fold_id),"selected_C":float(f.selected_c),
                "support":int(f.support),"touch_count":int(f.touch_count),"none_count":int(f.none_count),
                "prediction_sha256":f.prediction_sha256,
                "inner_c_ledger":list(f.inner_c_ledger),
                "metrics":dict(f.metrics),
            } for f in touch.s1_folds],
            "pooled":dict(touch.s1_pooled),
        },
        "direction_reproduction":reproduction,
        "composition_folds":[_public_metrics(f) for f in folds],
        "pooled_system_metrics":pooled,
        "comparison_c3_vs_c2":vs_c2,
        "comparison_c3_vs_c1":vs_c1,
        "temporal_null_c3_vs_c2":null,
        "eligible_for_policy_composition_development":status==core.STATUS_ELIGIBLE,
        "forward_guards":dict(FORWARD_GUARDS),
    }

    content=(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    staging=output.parent/f".{output.name}.part-{os.getpid()}"
    if staging.exists(): raise C1RunnerError("staging_exists")
    staging.mkdir(parents=True)
    try:
        final=staging/ARTIFACT_FILENAME
        with final.open("xb") as h:
            h.write(content);h.flush();os.fsync(h.fileno())
        os.replace(staging,output)
    except BaseException:
        if staging.exists(): shutil.rmtree(staging,ignore_errors=True)
        raise

    final=output/ARTIFACT_FILENAME
    return {
        "artifact_path":str(final),"artifact_sha256":_sha(final),
        "artifact_bytes":int(final.stat().st_size),"status":status,
    }

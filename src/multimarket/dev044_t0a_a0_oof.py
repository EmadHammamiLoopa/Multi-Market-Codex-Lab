from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
from typing import Mapping, Sequence

import numpy as np

from . import dev030_direction_dataset as dd
from . import dev042_p1_materialization as mat
from . import dev043_a_core as core
from . import dev043_a_runner as a_runner

EXPERIMENT_ID="DEV044-T0A-A0"
DESIGN_VERSION="a0-oof-score-replay-identity-v1"

A0_ID="A0_TOUCH_PRICE_LOGIT"

FROZEN_A_ARTIFACT=Path(
    "/home/emadh/Multi-Market/evidence/dev043_a_touch_screen_v1/"
    "DEV043_A_TOUCH_SCREEN_RESULT.json"
)
FROZEN_A_BYTES=89918
FROZEN_A_SHA256="38ee159618a1ed13727eb6a86df83b93c92c2aad50251fcfb1618d890efd2eb7"
FROZEN_A_STATUS="DEV043_A_TOUCH_SURVIVOR_A0_TOUCH_PRICE_LOGIT"

EXPECTED_POOLED={
    "support":5516,
    "touch_count":2683,
    "none_count":2833,
    "touch_prevalence":0.48640319071791155,
    "touch_average_precision":0.6519588168911605,
    "ap_lift_over_prevalence":0.16555562617324898,
    "roc_auc":0.6685251651144681,
    "brier":0.23346678523374584,
    "prior_brier":0.2498151267773465,
    "log_loss":0.6702005066176944,
    "balanced_accuracy":0.6304782211776729,
}
EXPECTED_PER_FOLD_AP_LIFT=(
    0.12917408394875396,
    0.1372403369595171,
    0.13636550823951282,
    0.1253127610143313,
)
EXPECTED_LOO_AP_LIFT=(
    0.17236840292020228,
    0.13691291981405296,
    0.17513748303524612,
    0.1659043840772374,
)

METRIC_ATOL=1e-12

class A0ReplayError(RuntimeError):
    pass

@dataclass(frozen=True)
class A0FoldScores:
    fold_id:int
    validation_day:str
    timestamps_us:np.ndarray
    y_touch:np.ndarray
    p_touch:np.ndarray

    def validate(self)->None:
        ts=np.asarray(self.timestamps_us,dtype=np.int64)
        y=np.asarray(self.y_touch,dtype=np.int8)
        p=np.asarray(self.p_touch,dtype=np.float64)
        if len(ts)==0 or y.shape!=(len(ts),) or p.shape!=(len(ts),):
            raise A0ReplayError("fold_shape")
        if np.any(np.diff(ts)<=0):
            raise A0ReplayError("timestamp_order")
        if not np.all(np.isin(y,(0,1))):
            raise A0ReplayError("target_values")
        if np.any(~np.isfinite(p)) or np.any(p<0) or np.any(p>1):
            raise A0ReplayError("probability_values")


def _sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            h.update(b)
    return h.hexdigest()


def verify_frozen_a_artifact()->Mapping:
    if not FROZEN_A_ARTIFACT.is_file():
        raise A0ReplayError("frozen_a_missing")
    if FROZEN_A_ARTIFACT.stat().st_size!=FROZEN_A_BYTES:
        raise A0ReplayError("frozen_a_bytes")
    if _sha(FROZEN_A_ARTIFACT)!=FROZEN_A_SHA256:
        raise A0ReplayError("frozen_a_sha")
    x=json.loads(FROZEN_A_ARTIFACT.read_text(encoding="utf-8"))
    if x.get("status")!=FROZEN_A_STATUS:
        raise A0ReplayError("frozen_a_status")
    if x.get("advanced_candidate")!=[A0_ID]:
        raise A0ReplayError("frozen_a_survivor")
    return x


def _load_inputs():
    days=tuple(dd.load_authorized_days())
    if tuple(x.day for x in days)!=dd.HISTORICAL_DAYS:
        raise A0ReplayError("calendar")
    materialized={}
    target={}
    for day in days:
        z=mat.materialize_day(day)
        mat.verify_frozen_support(z)
        materialized[day.day]=z
        target[day.day]=a_runner._target_for_day(day,z)
    return materialized,target


def replay_fold(fold,materialized,target)->A0FoldScores:
    train_X=[]
    train_y=[]
    for d in fold.train_days:
        idx,y=target[d]
        train_X.append(np.asarray(materialized[d].X0,dtype=np.float64)[idx])
        train_y.append(np.asarray(y,dtype=np.int8))
    Xtr=np.concatenate(train_X,axis=0)
    ytr=np.concatenate(train_y)

    vidx,yv=target[fold.validation_day]
    z=materialized[fold.validation_day]
    Xv=np.asarray(z.X0,dtype=np.float64)[vidx]
    ts=np.asarray(z.timestamps_us,dtype=np.int64)[vidx]

    if set(np.unique(ytr).tolist())!={0,1}:
        raise A0ReplayError("train_classes")
    if set(np.unique(yv).tolist())!={0,1}:
        raise A0ReplayError("validation_classes")

    model=core.make_estimator(A0_ID)
    model.fit(Xtr,ytr)
    p=core.touch_probability(model,Xv)

    out=A0FoldScores(
        int(fold.fold_id),
        fold.validation_day.isoformat(),
        ts,
        np.asarray(yv,dtype=np.int8),
        np.asarray(p,dtype=np.float64),
    )
    out.validate()
    return out


def replay_all()->tuple[A0FoldScores,...]:
    verify_frozen_a_artifact()
    materialized,target=_load_inputs()
    folds=tuple(replay_fold(f,materialized,target) for f in dd.OUTER_FOLDS)
    verify_metric_identity(folds)
    return folds


def _metric_folds(folds:Sequence[A0FoldScores]):
    return tuple({
        "fold_id":f.fold_id,
        "validation_day":f.validation_day,
        "timestamps_us":f.timestamps_us,
        "y":f.y_touch,
        "p_touch":f.p_touch,
    } for f in folds)


def verify_metric_identity(folds:Sequence[A0FoldScores])->dict:
    if len(folds)!=4:
        raise A0ReplayError("fold_count")
    for f in folds:f.validate()
    pooled,per,loo=core.pooled_and_fold_metrics(_metric_folds(folds))

    for k,v in EXPECTED_POOLED.items():
        got=pooled.get(k)
        if isinstance(v,int):
            if int(got)!=v:
                raise A0ReplayError(f"pooled_identity:{k}:{got}:{v}")
        else:
            if not np.isclose(float(got),float(v),rtol=0.0,atol=METRIC_ATOL):
                raise A0ReplayError(f"pooled_identity:{k}:{got}:{v}")

    got_per=tuple(float(x["ap_lift_over_prevalence"]) for x in per)
    got_loo=tuple(float(x["ap_lift_over_prevalence"]) for x in loo)
    if not np.allclose(got_per,EXPECTED_PER_FOLD_AP_LIFT,rtol=0.0,atol=METRIC_ATOL):
        raise A0ReplayError(f"per_fold_identity:{got_per}")
    if not np.allclose(got_loo,EXPECTED_LOO_AP_LIFT,rtol=0.0,atol=METRIC_ATOL):
        raise A0ReplayError(f"loo_identity:{got_loo}")

    return {"pooled":pooled,"per_fold":per,"leave_one_fold_out":loo}


def support_sha256(folds:Sequence[A0FoldScores])->str:
    h=hashlib.sha256(b"DEV044-T0A-A0-OOF-SUPPORT-V1\0")
    for f in folds:
        h.update(int(f.fold_id).to_bytes(2,"big",signed=False))
        h.update(np.asarray(f.timestamps_us,dtype=">i8").tobytes(order="C"))
    return h.hexdigest()


def score_sha256(folds:Sequence[A0FoldScores])->str:
    h=hashlib.sha256(b"DEV044-T0A-A0-OOF-SCORES-V1\0")
    for f in folds:
        h.update(int(f.fold_id).to_bytes(2,"big",signed=False))
        h.update(np.asarray(f.timestamps_us,dtype=">i8").tobytes(order="C"))
        h.update(np.asarray(f.p_touch,dtype=">f8").tobytes(order="C"))
    return h.hexdigest()


def public_manifest(folds:Sequence[A0FoldScores])->dict:
    metrics=verify_metric_identity(folds)
    return {
        "experiment_id":EXPERIMENT_ID,
        "design_version":DESIGN_VERSION,
        "source_survivor":A0_ID,
        "gate_threshold":0.50,
        "folds":[{
            "fold_id":f.fold_id,
            "validation_day":f.validation_day,
            "rows":int(len(f.timestamps_us)),
            "touch":int(np.sum(f.y_touch==1)),
            "none":int(np.sum(f.y_touch==0)),
        } for f in folds],
        "pooled_metrics":metrics["pooled"],
        "support_sha256":support_sha256(folds),
        "score_sha256":score_sha256(folds),
        "frozen_a_parent":{
            "bytes":FROZEN_A_BYTES,
            "sha256":FROZEN_A_SHA256,
            "status":FROZEN_A_STATUS,
        },
        "sep01_plus_opened":False,
        "other_market_opened":False,
        "pnl_run":False,
    }

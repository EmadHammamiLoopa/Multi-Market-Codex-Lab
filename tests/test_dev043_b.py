from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline

from multimarket import dev043_b_core as core
from multimarket import dev043_b_harness as harness
from multimarket import dev043_b_runner as runner

def test_candidate_registry_and_fixed_estimators():
    assert core.CANDIDATE_IDS==(
        "B0_DIR_PRICE_LOGIT",
        "B1_DIR_PRESSURE_LOGIT",
        "B2_DIR_COMBINED_HGB",
    )
    for cid in core.CANDIDATE_IDS[:2]:
        m=core.make_estimator(cid)
        assert isinstance(m,Pipeline)
        lr=m.named_steps["model"]
        assert lr.solver=="lbfgs"
        assert lr.C==1.0
        assert lr.max_iter==3000
        assert lr.class_weight is None

    h=core.make_estimator("B2_DIR_COMBINED_HGB")
    assert isinstance(h,HistGradientBoostingClassifier)
    assert h.learning_rate==0.05
    assert h.max_iter==200
    assert h.max_leaf_nodes==15
    assert h.max_depth is None
    assert h.min_samples_leaf==20
    assert h.l2_regularization==1.0
    assert h.max_bins==255
    assert h.early_stopping is False
    assert h.monotonic_cst is None
    assert h.random_state==20260903

def test_long_probability_reorders_classes():
    class M:
        classes_=np.array([1,0],dtype=np.int64)
        def predict_proba(self,X):
            return np.array([[0.8,0.2],[0.3,0.7]],dtype=float)
    p=core.long_probability(M(),np.zeros((2,1)))
    assert np.allclose(p,[0.8,0.3])

def test_metrics_perfect_direction():
    y=np.array([0,0,1,1],dtype=np.int8)
    p=np.array([0.05,0.1,0.9,0.95],dtype=float)
    m=core.metrics(y,p)
    assert m["long_count"]==2
    assert m["short_count"]==2
    assert m["balanced_accuracy"]==1.0
    assert m["balanced_accuracy_lift_over_050"]==0.5
    assert m["roc_auc"]==1.0
    assert m["log_loss"]<m["prior_log_loss"]
    assert m["macro_ap"]==1.0

def _fold(fid,y,p):
    return {
        "fold_id":fid,
        "validation_day":f"F{fid}",
        "y":np.asarray(y,dtype=np.int8),
        "p_long":np.asarray(p,dtype=float),
    }

def test_pooled_fold_and_loo_metrics():
    folds=tuple(
        _fold(i+1,[0,0,1,1],[0.1,0.2,0.8,0.9])
        for i in range(4)
    )
    pooled,per,loo=core.pooled_and_fold_metrics(folds)
    assert pooled["balanced_accuracy"]==1.0
    assert len(per)==4
    assert len(loo)==4
    assert all(x["balanced_accuracy"]>0.5 for x in loo)

def test_joint_null_shape_and_shared_labels():
    n=130
    y=np.array(([0,1]*65),dtype=np.int8)
    candidates={}
    for j,cid in enumerate(core.CANDIDATE_IDS):
        folds=[]
        for i in range(4):
            p=np.linspace(0.05,0.95,n)
            if j==1:
                p=p[::-1]
            folds.append({
                "fold_id":i+1,
                "validation_day":f"F{i+1}",
                "y":y.copy(),
                "p_long":p.copy(),
            })
        candidates[cid]=tuple(folds)

    z=core.joint_temporal_max_stat_null(
        candidate_folds=candidates,
        replicates=7,
        seed=20260903,
    )
    assert z["replicates"]==7
    assert len(z["shift_tuples"])==7
    assert all(len(x)==4 for x in z["shift_tuples"])
    assert len(z["max_stat_null"])==7
    assert set(z["per_candidate"])==set(core.CANDIDATE_IDS)

def test_eligibility_and_ranking_contract():
    base={
        "pooled":{
            "balanced_accuracy":0.62,
            "roc_auc":0.66,
            "log_loss":0.64,
            "prior_log_loss":0.69,
        },
        "per_fold":[
            {"balanced_accuracy_lift_over_050":0.06,"long_count":10,"short_count":10},
            {"balanced_accuracy_lift_over_050":0.07,"long_count":10,"short_count":10},
            {"balanced_accuracy_lift_over_050":0.08,"long_count":10,"short_count":10},
            {"balanced_accuracy_lift_over_050":0.09,"long_count":10,"short_count":10},
        ],
        "leave_one_fold_out":[
            {"balanced_accuracy":0.60},
            {"balanced_accuracy":0.61},
            {"balanced_accuracy":0.62},
            {"balanced_accuracy":0.63},
        ],
    }
    null={
        "observed_ba_lift":0.12,
        "joint_max_stat_q95":0.04,
        "max_stat_fwer_empirical_p":0.01,
    }
    ok,g=core.eligibility(base,null)
    assert ok and all(g.values())

    records={}
    for i,cid in enumerate(core.CANDIDATE_IDS):
        rec={
            "pooled":dict(base["pooled"]),
            "per_fold":[dict(x) for x in base["per_fold"]],
            "leave_one_fold_out":[dict(x) for x in base["leave_one_fold_out"]],
            "eligible":True,
        }
        if i==0:
            rec["per_fold"][0]["balanced_accuracy_lift_over_050"]=0.20
        records[cid]=rec

    assert core.rank(records)[0]=="B0_DIR_PRICE_LOGIT"

def test_runner_parent_and_support_contract_frozen():
    assert runner.A_BYTES==89918
    assert runner.A_SHA=="38ee159618a1ed13727eb6a86df83b93c92c2aad50251fcfb1618d890efd2eb7"
    assert runner.A_SURVIVOR=="A0_TOUCH_PRICE_LOGIT"
    assert runner.FORWARD_GUARDS["predicted_touch_used_for_stage_b_support"] is False
    assert not any(runner.FORWARD_GUARDS.values())

def test_harness_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)

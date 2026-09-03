from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline

from multimarket import dev030_first_passage as fp
from multimarket import dev042_p3_core as core
from multimarket import dev042_p3_harness as harness

def test_candidate_registry_and_fixed_estimators():
    assert core.CANDIDATE_IDS==(
        "C0_PRICE_LOGIT","C1_OFI_LOGIT","C2_PRESSURE_CAPACITY_LOGIT",
        "C3_COMBINED_LOGIT","C4_COMBINED_HGB",
    )
    for cid in core.CANDIDATE_IDS[:4]:
        m=core.make_estimator(cid)
        assert isinstance(m,Pipeline)
        lr=m.named_steps["model"]
        assert lr.C==1.0
        assert lr.max_iter==3000
        assert lr.solver=="lbfgs"
        assert lr.class_weight is None
    h=core.make_estimator("C4_COMBINED_HGB")
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

def test_argmax_action_and_tie_abstention():
    p=np.array([
        [0.7,0.2,0.1],
        [0.1,0.8,0.1],
        [0.1,0.2,0.7],
        [0.4,0.4,0.2],
        [0.2,0.4,0.4],
    ])
    a=core.action_from_probabilities(p,[0,1,2])
    assert a.tolist()==[0,1,2,0,0]

def _record(decision,entry,label,touch=None):
    return {
        "decision_timestamp_us":decision,
        "entry_timestamp_us":entry,
        "label":label,
        "target_valid":True,
        "invalid_reason":None,
        "same_row_ambiguous":False,
        "barrier_reached_timestamp_us":touch,
    }

def _raw_day():
    ts=np.arange(0,5_000_000,250_000,dtype=np.int64)
    bid=np.full(len(ts),100.0)
    ask=np.full(len(ts),100.1)
    valid=np.ones(len(ts),dtype=bool)
    # LONG TP response at 1.25s -> bid 101
    bid[np.where(ts==1_250_000)[0][0]]=101.0
    ask[np.where(ts==1_250_000)[0][0]]=101.1
    # SHORT TP response at 2.75s -> ask 99
    bid[np.where(ts==2_750_000)[0][0]]=98.9
    ask[np.where(ts==2_750_000)[0][0]]=99.0
    return ts,bid,ask,valid

def test_execute_tp_sl_and_flat_only():
    ts,bid,ask,valid=_raw_day()
    records=(
        _record(0,250_000,fp.LONG_FIRST,1_000_000),
        _record(500_000,750_000,fp.LONG_FIRST,1_000_000),
        _record(2_000_000,2_250_000,fp.SHORT_FIRST,2_500_000),
    )
    actions=np.array([core.CLASS_LONG,core.CLASS_SHORT,core.CLASS_SHORT],dtype=np.int8)
    trades,ignored=core.execute_actions(
        day="FOLD1",actions=actions,records=records,
        raw_timestamps_us=ts,bid=bid,ask=ask,book_valid=valid,
    )
    assert ignored==1
    assert len(trades)==2
    assert trades[0].exit_reason=="TP"
    assert trades[0].side=="LONG"
    assert trades[0].exit_timestamp_us==1_250_000
    assert trades[1].exit_reason=="TP"
    assert trades[1].side=="SHORT"
    assert trades[1].exit_timestamp_us==2_750_000

def test_opposite_barrier_is_sl():
    ts,bid,ask,valid=_raw_day()
    rec=(_record(2_000_000,2_250_000,fp.SHORT_FIRST,2_500_000),)
    trades,ignored=core.execute_actions(
        day="FOLD1",actions=np.array([core.CLASS_LONG]),records=rec,
        raw_timestamps_us=ts,bid=bid,ask=ask,book_valid=valid,
    )
    assert ignored==0
    assert len(trades)==1
    assert trades[0].exit_reason=="SL"
    assert trades[0].side=="LONG"

def _good_trade(fold,k,gross=25.0):
    return core.ExecutedTrade(
        day=fold,side="LONG" if k%2==0 else "SHORT",
        decision_timestamp_us=k*2_000_000,
        entry_timestamp_us=k*2_000_000+250_000,
        exit_timestamp_us=k*2_000_000+1_000_000,
        exit_reason="TP",gross_bps=gross,
    )

def test_economics_and_absolute_gates():
    trades=tuple(
        _good_trade(f"FOLD{f}",k+100*f,25.0)
        for f in range(1,5) for k in range(30)
    )
    c1=core.economics(trades,10.0,[f"FOLD{i}" for i in range(1,5)])
    c2=core.economics(trades,16.0,[f"FOLD{i}" for i in range(1,5)])
    rec={
        "classification":{"action_coverage":0.2},
        "activity":{"execution_invalid":0,"accepted_trades":120,"long_trades":60,"short_trades":60},
        "c1":c1,"c2":c2,
    }
    ok,g=core.absolute_eligibility(rec)
    assert ok
    assert all(g.values())

def test_joint_null_shared_shift_and_fwer_shape():
    n=130
    fold_actions={
        cid:tuple(np.where(np.arange(n)%3==0,core.CLASS_LONG,core.CLASS_NONE).astype(np.int8) for _ in range(4))
        for cid in core.CANDIDATE_IDS
    }
    observed={
        cid:{"c2":{"mean_net_bps":10.0}}
        for cid in core.CANDIDATE_IDS
    }
    def evaluator(actions,fold="FOLD1"):
        idx=np.flatnonzero(np.asarray(actions)!=core.CLASS_NONE)
        return tuple(
            core.ExecutedTrade(
                day=fold,side="LONG",decision_timestamp_us=int(i),
                entry_timestamp_us=int(i)+1,exit_timestamp_us=int(i)+2,
                exit_reason="TP",gross_bps=20.0,
            )
            for i in idx[:10]
        )
    evals=tuple(
        (lambda fold: (lambda actions: evaluator(actions,fold)))(f"FOLD{i}")
        for i in range(1,5)
    )
    z=core.joint_temporal_max_stat_null(
        observed_records=observed,
        fold_actions=fold_actions,
        fold_evaluators=evals,
        seed=20260903,
        replicates=5,
    )
    assert z["replicates"]==5
    assert len(z["shift_tuples"])==5
    assert all(len(x)==4 for x in z["shift_tuples"])
    assert len(z["max_stat_null"])==5
    assert set(z["per_candidate"])==set(core.CANDIDATE_IDS)

def test_harness_smoke():
    assert harness.process_pool_smoke(2)==(1,4,9,16)

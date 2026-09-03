from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev044_t0_strategy_contract as c
from multimarket import dev044_t0e_support_audit as a


def rich_state():
    return c.StrategyState(
        ret_8_bps=3.0,
        ret_32_bps=4.0,
        ema_fast_minus_slow_bps=1.0,
        breakout_up_bps=2.0,
        breakout_down_bps=0.0,
        rv_ratio_8_to_32=1.5,
        price_z_32=-2.0,
        microprice_disp_bps=1.0,
        price_minus_fair_bps=-2.0,
        obi_l1=0.3,
        obi_l5=0.3,
        obi_l20=0.3,
        weighted_obi=0.3,
        ofi_1s=0.3,
        ofi_16s=0.3,
        ofi_32s=0.3,
        trade_imbalance_1s=0.3,
        trade_imbalance_16s=0.3,
        depletion_pressure=0.3,
        cancellation_pressure=0.3,
        event_intensity_1s=0.3,
        event_intensity_8s=0.3,
        liquidity_shock_direction=1,
        liquidity_recovery_fraction=0.2,
        mid_price=9998.0,
        round_level=10000.0,
        round_distance_bps=2.0,
        toxicity=0.1,
        spread_bps=1.0,
    )


def test_actions_u_a_pair_above_gate():
    core,cand=a._actions_for_state(rich_state(),0.50,toxicity_available=True)
    assert len(core)==16
    assert len(cand)==32
    for i in range(16):
        assert cand[2*i]==core[i]
        assert cand[2*i+1]==core[i]


def test_actions_a_suppressed_below_gate():
    core,cand=a._actions_for_state(rich_state(),0.49,toxicity_available=True)
    for i in range(16):
        assert cand[2*i]==core[i]
        assert cand[2*i+1]==c.ABSTAIN


def test_t16_unavailable_is_abstain_without_affecting_other_cores():
    core_av,cand_av=a._actions_for_state(rich_state(),0.8,toxicity_available=True)
    core_no,cand_no=a._actions_for_state(rich_state(),0.8,toxicity_available=False)
    assert core_no[:15]==core_av[:15]
    assert cand_no[:30]==cand_av[:30]
    assert core_no[15]==c.ABSTAIN
    assert cand_no[30]==c.ABSTAIN
    assert cand_no[31]==c.ABSTAIN


def test_summary_counts():
    core=np.asarray([
        [1,0]+[0]*14,
        [-1,1]+[0]*14,
        [0,-1]+[0]*14,
    ],dtype=np.int8)
    cand=np.zeros((3,32),dtype=np.int8)
    cand[:,0]=np.asarray([1,-1,0],dtype=np.int8)
    cand[:,1]=np.asarray([1,0,0],dtype=np.int8)
    p=np.asarray([0.8,0.2,0.4],dtype=np.float64)
    tox=np.asarray([True,False,True],dtype=bool)
    out=a._summary_counts(core,cand,p,tox)
    assert out["rows"]==3
    assert out["a0_gate_pass_rows"]==1
    assert out["a0_gate_fail_rows"]==2
    assert out["toxicity_available_rows"]==2
    assert out["toxicity_unavailable_rows"]==1
    assert out["core"]["T01"]=={
        "ready":3,"unavailable":0,
        "long":1,"short":1,"abstain":1,"active":2,
    }
    assert out["candidates"]["T01U"]=={
        "ready":3,"unavailable":0,
        "long":1,"short":1,"abstain":1,"active":2,
    }
    assert out["candidates"]["T01A"]=={
        "ready":3,"unavailable":0,
        "long":1,"short":0,"abstain":2,"active":1,
    }


def test_frozen_parent_constants():
    assert a.VPIN_BUCKET_VOLUME==pytest.approx(45.56983)
    assert a.T0D_ARTIFACT_BYTES==1314
    assert a.T0D_ARTIFACT_SHA256=="c0cf0362f2f4a0559ff28c95e72824f5a8e5fa34a20394c33fe71f263f88143c"
    assert a.APR_JUL==(
        __import__("datetime").date(2026,4,1),
        __import__("datetime").date(2026,5,1),
        __import__("datetime").date(2026,6,1),
        __import__("datetime").date(2026,7,1),
    )


def test_required_source_fields_are_frozen_phase0dl_fields():
    missing=[x for x in a.REQUIRED_SOURCE_FIELDS if x not in a.dd.SOURCE_FEATURE_ORDER]
    assert missing==[]


def test_registry_widths():
    assert len(c.CORE_IDS)==16
    assert len(c.CANDIDATE_IDS)==32


def test_trade_qty_imbalance_reconstructed_from_trade250():
    n=8
    ts=np.arange(n,dtype=np.int64)*250_000
    trade=a.TradeDay(
        timestamps_us=ts,
        buy_qty=np.asarray([1,0,1,0, 0,0,0,0],dtype=float),
        sell_qty=np.asarray([0,1,0,1, 0,0,0,0],dtype=float),
    )
    x=a._trade_qty_imbalance_1s(trade)
    # At row 3 the latest four bins are exactly balanced.
    assert x[3]==pytest.approx(0.0)
    # Empty four-bin window is neutral by the frozen Phase0DL semantics.
    assert x[7]==pytest.approx(0.0)
    assert np.all(np.isfinite(x))
    assert np.all(x>=-1.0)
    assert np.all(x<=1.0)


def test_readiness_mask_forces_only_unavailable_strategy_to_abstain():
    s=rich_state()
    ready={cid:True for cid in c.CORE_IDS}
    ready["T11"]=False
    core,cand=a._actions_for_state(
        s,0.9,toxicity_available=True,readiness=ready
    )
    assert core[10]==c.ABSTAIN
    assert cand[20]==c.ABSTAIN
    assert cand[21]==c.ABSTAIN
    # Neighboring strategy remains evaluated normally.
    assert core[9]==c.LONG


def test_summary_reports_strategy_specific_unavailability():
    core=np.zeros((2,16),dtype=np.int8)
    cand=np.zeros((2,32),dtype=np.int8)
    p=np.asarray([0.6,0.4])
    tox=np.asarray([True,True])
    ready=np.ones((2,16),dtype=bool)
    ready[1,10]=False
    out=a._summary_counts(core,cand,p,tox,ready)
    assert out["core"]["T11"]["ready"]==1
    assert out["core"]["T11"]["unavailable"]==1
    assert out["candidates"]["T11U"]["ready"]==1
    assert out["candidates"]["T11A"]["unavailable"]==1

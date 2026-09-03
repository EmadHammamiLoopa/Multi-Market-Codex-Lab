from __future__ import annotations

import dataclasses
import math

import pytest

from multimarket import dev044_t0_strategy_contract as c


def S(**kwargs):
    return c.StrategyState(**kwargs)


def test_registry():
    c.validate_registry()
    assert len(c.CORE_IDS)==16
    assert len(c.CANDIDATE_IDS)==32
    assert c.CANDIDATE_IDS[0]=="T01U"
    assert c.CANDIDATE_IDS[1]=="T01A"
    assert c.CANDIDATE_IDS[-1]=="T16A"
    assert c.A0_GATE_THRESHOLD==0.50


@pytest.mark.parametrize(
    "cid,state,expected",
    [
        ("T01",S(ret_8_bps=2,ret_32_bps=4),c.LONG),
        ("T01",S(ret_8_bps=-2,ret_32_bps=-4),c.SHORT),
        ("T01",S(ret_8_bps=2,ret_32_bps=-4),c.ABSTAIN),

        ("T02",S(ema_fast_minus_slow_bps=0.6),c.LONG),
        ("T02",S(ema_fast_minus_slow_bps=-0.6),c.SHORT),
        ("T02",S(ema_fast_minus_slow_bps=0.4),c.ABSTAIN),

        ("T03",S(breakout_up_bps=1.2),c.LONG),
        ("T03",S(breakout_down_bps=1.2),c.SHORT),
        ("T03",S(breakout_up_bps=1.2,breakout_down_bps=1.2),c.ABSTAIN),

        ("T04",S(rv_ratio_8_to_32=1.3,ret_32_bps=2),c.LONG),
        ("T04",S(rv_ratio_8_to_32=1.2,ret_32_bps=2),c.ABSTAIN),

        ("T05",S(price_z_32=-1.6),c.LONG),
        ("T05",S(price_z_32=1.6),c.SHORT),

        ("T06",S(microprice_disp_bps=0.6),c.LONG),
        ("T06",S(microprice_disp_bps=-0.6),c.SHORT),

        ("T07",S(price_minus_fair_bps=1.2,obi_l1=-0.1),c.SHORT),
        ("T07",S(price_minus_fair_bps=-1.2,obi_l1=0.1),c.LONG),
        ("T07",S(price_minus_fair_bps=1.2,obi_l1=0.1),c.ABSTAIN),

        ("T08",S(obi_l1=0.21),c.LONG),
        ("T08",S(obi_l1=-0.21),c.SHORT),

        ("T09",S(obi_l5=0.2,obi_l20=0.2,weighted_obi=0.2),c.LONG),
        ("T09",S(obi_l5=0.2,obi_l20=-0.2,weighted_obi=0.2),c.ABSTAIN),

        ("T10",S(ofi_1s=-0.2,ofi_16s=-0.2,ofi_32s=-0.2),c.SHORT),
        ("T11",S(trade_imbalance_1s=0.2,trade_imbalance_16s=0.2),c.LONG),
        ("T12",S(depletion_pressure=-0.2,cancellation_pressure=-0.2),c.SHORT),
        ("T13",S(event_intensity_1s=0.2,event_intensity_8s=0.2),c.LONG),

        ("T14",S(liquidity_shock_direction=1,liquidity_recovery_fraction=0.4),c.LONG),
        ("T14",S(liquidity_shock_direction=1,liquidity_recovery_fraction=0.6),c.ABSTAIN),

        ("T15",S(mid_price=9998,round_level=10000,round_distance_bps=2,trade_imbalance_16s=0.2),c.LONG),
        ("T15",S(mid_price=10002,round_level=10000,round_distance_bps=2,trade_imbalance_16s=-0.2),c.SHORT),
        ("T15",S(mid_price=9998,round_level=10000,round_distance_bps=6,trade_imbalance_16s=0.2),c.ABSTAIN),

        ("T16",S(ret_32_bps=2,weighted_obi=0.2,trade_imbalance_16s=-0.2,toxicity=0.2,spread_bps=1),c.LONG),
        ("T16",S(ret_32_bps=2,weighted_obi=0.2,trade_imbalance_16s=-0.2,toxicity=0.9,spread_bps=1),c.ABSTAIN),
    ],
)
def test_core_rules(cid,state,expected):
    assert c.core_action(cid,state)==expected


@pytest.mark.parametrize("cid",c.CORE_IDS)
def test_u_a_identical_above_gate(cid):
    # rich state gives each rule a deterministic result, including abstention.
    s=S(
        ret_8_bps=3,ret_32_bps=4,ema_fast_minus_slow_bps=1,
        breakout_up_bps=2,rv_ratio_8_to_32=1.5,price_z_32=-2,
        microprice_disp_bps=1,price_minus_fair_bps=-2,
        obi_l1=0.3,obi_l5=0.3,obi_l20=0.3,weighted_obi=0.3,
        ofi_1s=0.3,ofi_16s=0.3,ofi_32s=0.3,
        trade_imbalance_1s=0.3,trade_imbalance_16s=0.3,
        depletion_pressure=0.3,cancellation_pressure=0.3,
        event_intensity_1s=0.3,event_intensity_8s=0.3,
        liquidity_shock_direction=1,liquidity_recovery_fraction=0.2,
        mid_price=9998,round_level=10000,round_distance_bps=2,
        toxicity=0.2,spread_bps=1,
    )
    u=c.candidate_action(f"{cid}U",s,a0_p_touch=0.0)
    a=c.candidate_action(f"{cid}A",s,a0_p_touch=0.50)
    assert a==u


@pytest.mark.parametrize("cid",c.CORE_IDS)
def test_a_gate_is_only_difference(cid):
    s=S(
        ret_8_bps=3,ret_32_bps=4,ema_fast_minus_slow_bps=1,
        breakout_up_bps=2,rv_ratio_8_to_32=1.5,price_z_32=-2,
        microprice_disp_bps=1,price_minus_fair_bps=-2,
        obi_l1=0.3,obi_l5=0.3,obi_l20=0.3,weighted_obi=0.3,
        ofi_1s=0.3,ofi_16s=0.3,ofi_32s=0.3,
        trade_imbalance_1s=0.3,trade_imbalance_16s=0.3,
        depletion_pressure=0.3,cancellation_pressure=0.3,
        event_intensity_1s=0.3,event_intensity_8s=0.3,
        liquidity_shock_direction=1,liquidity_recovery_fraction=0.2,
        mid_price=9998,round_level=10000,round_distance_bps=2,
        toxicity=0.2,spread_bps=1,
    )
    u=c.candidate_action(f"{cid}U",s,a0_p_touch=0.0)
    a=c.candidate_action(f"{cid}A",s,a0_p_touch=0.499999999)
    assert a==c.ABSTAIN
    assert u==c.core_action(cid,s)


def test_gate_boundary_is_inclusive():
    s=S(obi_l1=0.3)
    assert c.candidate_action("T08A",s,a0_p_touch=0.50)==c.LONG
    assert c.candidate_action("T08A",s,a0_p_touch=math.nextafter(0.50,0.0))==c.ABSTAIN


def test_invalid_probability_fails_closed():
    with pytest.raises(c.T0ContractError):
        c.candidate_action("T01A",S(),a0_p_touch=float("nan"))
    with pytest.raises(c.T0ContractError):
        c.candidate_action("T01A",S(),a0_p_touch=-0.1)
    with pytest.raises(c.T0ContractError):
        c.candidate_action("T01A",S(),a0_p_touch=1.1)


def test_invalid_state_fails_closed():
    with pytest.raises(c.T0ContractError):
        c.core_action("T01",S(ret_8_bps=float("nan")))


def test_bad_shock_direction_fails_closed():
    with pytest.raises(c.T0ContractError):
        c.core_action("T14",S(liquidity_shock_direction=2))


def test_state_is_frozen():
    s=S()
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.obi_l1=1.0

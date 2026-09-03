from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev044_t0_strategy_contract as c
from multimarket import dev044_t0b_state_materializer as m


def fixture():
    n=220
    ts=np.arange(n,dtype=np.int64)*250_000
    mid=10000.0*np.exp(np.linspace(0,0.001,n))
    source={
        "microprice_minus_mid_bps":np.full(n,0.8),
        "obi_l1":np.full(n,0.30),
        "obi_l5":np.full(n,0.20),
        "spread_bps":np.full(n,1.0),
        "trade_qty_imbalance_1s":np.full(n,0.25),
    }
    raw={
        "S05":np.zeros((1,7),dtype=np.float64),
        "S06":np.zeros((1,2),dtype=np.float64),
        "S21":np.zeros((1,8),dtype=np.float64),
        "S30":np.zeros((1,6),dtype=np.float64),
        "S31":np.zeros((1,6),dtype=np.float64),
        "S32":np.zeros((1,4),dtype=np.float64),
    }
    raw["S05"][0,5]=0.22
    raw["S06"][0,0]=0.18
    # delete near/deep, deplete near/deep
    raw["S21"][0,2:4]=[0.2,0.4]
    raw["S21"][0,6:8]=[0.6,0.2]
    # add and remove pressure both bullish at tau 1 / 8
    raw["S30"][0,0:2]=[0.4,0.2]
    raw["S31"][0,0:2]=[0.2,0.4]
    # latest ask-side depth shock is more recent -> bullish, recovery .3
    raw["S32"][0]=[0.7,0.3,10.0,2.0]
    return ts,mid,source,raw


def test_materializer_direct_and_raw_mapping():
    ts,mid,source,raw=fixture()
    out=m.materialize_state(
        timestamps_us=ts,
        mid=mid,
        source=source,
        decision_timestamp_us=int(ts[-1]),
        raw=raw,
        raw_row=0,
        toxicity=None,
    )
    s=out.state
    assert s.ret_8_bps>0
    assert s.ret_32_bps>0
    assert np.isfinite(s.ema_fast_minus_slow_bps)
    assert np.isfinite(s.rv_ratio_8_to_32)
    assert np.isfinite(s.price_z_32)
    assert s.microprice_disp_bps==pytest.approx(0.8)
    assert s.price_minus_fair_bps==pytest.approx(-0.8)
    assert s.obi_l20==pytest.approx(0.22)
    assert s.weighted_obi==pytest.approx(0.18)
    assert s.trade_imbalance_16s==pytest.approx(0.25)
    assert s.cancellation_pressure==pytest.approx(0.30)
    assert s.depletion_pressure==pytest.approx(0.40)
    assert s.event_intensity_1s==pytest.approx(0.30)
    assert s.event_intensity_8s==pytest.approx(0.30)
    assert s.liquidity_shock_direction==c.LONG
    assert s.liquidity_recovery_fraction==pytest.approx(0.3)
    assert s.round_level%100==0
    assert out.readiness["T09"] is True
    assert out.readiness["T12"] is True
    assert out.readiness["T13"] is True
    assert out.readiness["T14"] is True
    assert out.readiness["T10"] is False
    assert out.readiness["T16"] is False
    assert "T10_NORMALIZED_FLOW_RULE_PENDING" in out.blockers
    assert "T16_TOXICITY_LINEAGE_PENDING" in out.blockers


def test_t14_bid_shock_is_short():
    ts,mid,source,raw=fixture()
    raw["S32"][0]=[0.25,0.9,1.0,10.0]
    out=m.materialize_state(
        timestamps_us=ts,mid=mid,source=source,
        decision_timestamp_us=int(ts[-1]),raw=raw,raw_row=0,toxicity=0.1,
    )
    assert out.state.liquidity_shock_direction==c.SHORT
    assert out.state.liquidity_recovery_fraction==pytest.approx(0.25)


def test_no_recent_t14_shock_abstains():
    ts,mid,source,raw=fixture()
    raw["S32"][0]=[0.7,0.3,32.0,32.0]
    out=m.materialize_state(
        timestamps_us=ts,mid=mid,source=source,
        decision_timestamp_us=int(ts[-1]),raw=raw,raw_row=0,toxicity=0.1,
    )
    assert out.state.liquidity_shock_direction==0
    assert out.state.liquidity_recovery_fraction==0.0


def test_without_raw_fails_closed_only_for_raw_dependent_plus_t10_t16():
    ts,mid,source,_=fixture()
    out=m.materialize_state(
        timestamps_us=ts,mid=mid,source=source,
        decision_timestamp_us=int(ts[-1]),raw=None,raw_row=None,toxicity=None,
    )
    for cid in ("T09","T10","T12","T13","T14","T16"):
        assert out.readiness[cid] is False
    for cid in ("T01","T02","T03","T04","T05","T06","T07","T08","T11","T15"):
        assert out.readiness[cid] is True


def test_assert_t1_ready_fails_on_blockers():
    ts,mid,source,raw=fixture()
    out=m.materialize_state(
        timestamps_us=ts,mid=mid,source=source,
        decision_timestamp_us=int(ts[-1]),raw=raw,raw_row=0,toxicity=None,
    )
    with pytest.raises(m.StateMaterializationError) as e:
        m.assert_t1_ready(out)
    assert "T10" in str(e.value)
    assert "T16" in str(e.value)


def test_exact_32s_prior_window_excludes_current_and_has_128_rows():
    n=140
    ts=np.arange(n,dtype=np.int64)*250_000
    idx=m._window(ts,n-1,32,include_current=False)
    assert len(idx)==128
    assert idx[-1]==n-2
    assert idx[0]==n-129


def test_32s_inclusive_rv_window_has_129_points():
    n=140
    ts=np.arange(n,dtype=np.int64)*250_000
    idx=m._window(ts,n-1,32,include_current=True)
    assert len(idx)==129
    assert idx[-1]==n-1
    assert idx[0]==n-129


def test_toxicity_validation():
    ts,mid,source,raw=fixture()
    with pytest.raises(m.StateMaterializationError):
        m.materialize_state(
            timestamps_us=ts,mid=mid,source=source,
            decision_timestamp_us=int(ts[-1]),raw=raw,raw_row=0,toxicity=1.2,
        )

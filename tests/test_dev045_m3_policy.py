from __future__ import annotations

import pytest

from multimarket.dev044_t0_strategy_contract import StrategyState, LONG, SHORT, ABSTAIN
from multimarket import dev045_m3_policy as m


def book(**kw):
    d=dict(
        best_bid_tick=1000,
        best_ask_tick=1001,
        bid_depth_qty={998:1.0,999:1.0,1000:1.0},
        ask_depth_qty={1001:1.0,1002:1.0,1003:1.0},
        inventory=0.0,
        inventory_age_s=0.0,
        aggressive_buy_qty_1s=0.0,
        aggressive_sell_qty_1s=0.0,
        legacy_state=None,
        a0_p_touch=0.0,
    )
    d.update(kw)
    return m.MarketState(**d)


def test_registry_exactly_eight():
    m.validate_registry()
    assert m.POLICY_IDS==("M01","M02","M03","M04","M05","M06","M07","M08")


def test_m01_symmetric_join():
    d=m.policy_decision("M01",book())
    assert (d.bid_target_tick,d.ask_target_tick)==(1000,1001)
    assert d.bid_size==pytest.approx(0.001)
    assert d.ask_size==pytest.approx(0.001)


def test_size_is_one_percent_capped_and_fail_closed_below_one_lot():
    assert m.quote_size(1.0)==pytest.approx(0.001)
    assert m.quote_size(0.10)==pytest.approx(0.001)
    assert m.quote_size(0.099)==0.0


def test_m02_inventory_reservation_retreats_risk_side_only():
    long1=m.policy_decision("M02",book(inventory=0.001))
    assert long1.reference_shift_ticks==-1
    assert (long1.bid_target_tick,long1.ask_target_tick)==(999,1001)

    short2=m.policy_decision("M02",book(inventory=-0.002))
    assert short2.reference_shift_ticks==2
    assert (short2.bid_target_tick,short2.ask_target_tick)==(1000,1003)


def test_inventory_caps_disable_exposure_increasing_side():
    longcap=m.policy_decision("M02",book(inventory=0.003))
    assert not longcap.bid_enabled
    assert longcap.ask_enabled
    shortcap=m.policy_decision("M02",book(inventory=-0.003))
    assert shortcap.bid_enabled
    assert not shortcap.ask_enabled


def test_m03_obi_shift_is_bounded_and_causal_l1():
    s=book(
        bid_depth_qty={998:1.0,999:1.0,1000:0.9},
        ask_depth_qty={1001:0.1,1002:1.0,1003:1.0},
    )
    d=m.policy_decision("M03",s)
    assert m.l1_obi(s)==pytest.approx(0.8)
    assert d.reference_shift_ticks==2
    assert (d.bid_target_tick,d.ask_target_tick)==(1000,1003)


def test_m04_microprice_skew_never_improves_inside_spread():
    s=book(
        bid_depth_qty={998:1.0,999:1.0,1000:0.9},
        ask_depth_qty={1001:0.1,1002:1.0,1003:1.0},
    )
    d=m.policy_decision("M04",s)
    assert d.reference_shift_ticks>0
    assert d.bid_target_tick==s.best_bid_tick
    assert d.ask_target_tick>=s.best_ask_tick


def test_m05_toxicity_retreat_and_veto_adverse_side():
    s=book(aggressive_buy_qty_1s=9.0,aggressive_sell_qty_1s=1.0)
    d=m.policy_decision("M05",s)
    assert m.trade_flow_imbalance(s)==pytest.approx(0.8)
    assert not d.ask_enabled
    assert d.bid_enabled


def test_m06_reuses_exact_t10_and_a0_gate():
    legacy=StrategyState(ofi_1s=1.0,ofi_16s=1.0,ofi_32s=1.0)
    open_gate=m.policy_decision("M06",book(legacy_state=legacy,a0_p_touch=0.50))
    closed_gate=m.policy_decision("M06",book(legacy_state=legacy,a0_p_touch=0.49))
    assert open_gate.ask_target_tick==1002
    assert closed_gate.ask_target_tick==1001


def test_m07_reuses_exact_t05_reversal_and_a0_gate():
    # Frozen T05: z >= +1.5 => SHORT, therefore retreat bid.
    legacy=StrategyState(price_z_32=2.0)
    d=m.policy_decision("M07",book(legacy_state=legacy,a0_p_touch=0.50))
    assert d.bid_target_tick==999
    assert d.ask_target_tick==1001


def test_inventory_timeout_forces_flatten_and_disables_quotes():
    d=m.policy_decision("M04",book(inventory=0.001,inventory_age_s=60.0))
    assert d.force_flatten
    assert not d.bid_enabled and not d.ask_enabled
    assert d.flatten_direction==SHORT
    assert d.flatten_qty==pytest.approx(0.001)


def test_cancel_replace_is_two_phase_never_simultaneous():
    d=m.policy_decision("M02",book(inventory=0.001))
    first=m.maintenance_intent(
        "M02","bid",1000,d,best_bid_tick=1000,best_ask_tick=1001
    )
    assert first.action=="CANCEL"
    assert first.cancel and not first.submit

    after_cancel=m.maintenance_intent(
        "M02","bid",None,d,best_bid_tick=1000,best_ask_tick=1001
    )
    assert after_cancel.action=="SUBMIT"
    assert not after_cancel.cancel and after_cancel.submit
    assert after_cancel.submit_tick==999


def test_unchanged_quote_keeps_queue_position():
    d=m.policy_decision("M01",book())
    x=m.maintenance_intent(
        "M01","bid",1000,d,best_bid_tick=1000,best_ask_tick=1001
    )
    assert x.action=="KEEP"
    assert not x.cancel and not x.submit


def test_m08_preserves_queue_for_one_tick_target_change():
    d=m.policy_decision("M08",book(inventory=0.001))
    assert d.bid_target_tick==999
    x=m.maintenance_intent(
        "M08","bid",1000,d,best_bid_tick=1000,best_ask_tick=1001
    )
    assert x.action=="KEEP"


def test_m08_reprices_at_two_ticks():
    d=m.policy_decision("M08",book(inventory=0.002))
    assert d.bid_target_tick==998
    x=m.maintenance_intent(
        "M08","bid",1000,d,best_bid_tick=1000,best_ask_tick=1001
    )
    assert x.action=="CANCEL"
    assert x.cancel and not x.submit


def test_marketable_working_order_is_canceled_fail_closed():
    d=m.policy_decision("M08",book())
    x=m.maintenance_intent(
        "M08","bid",1001,d,best_bid_tick=1000,best_ask_tick=1001
    )
    assert x.action=="CANCEL"
    assert x.cancel and not x.submit


def test_terminal_plan_cancels_and_flattens_executably():
    p=m.terminal_plan(inventory=-0.002,working_bid=True,working_ask=True)
    assert p.cancel_bid and p.cancel_ask
    assert p.flatten_direction==LONG
    assert p.flatten_qty==pytest.approx(0.002)


def test_invalid_book_and_inventory_fail_closed():
    with pytest.raises(m.M3PolicyError):
        m.policy_decision("M01",book(best_bid_tick=1001,best_ask_tick=1001))
    with pytest.raises(m.M3PolicyError):
        m.policy_decision("M01",book(inventory=0.004))

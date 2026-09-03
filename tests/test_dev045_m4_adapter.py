from __future__ import annotations

import pytest

from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as a


def test_passive_target_guard_rejects_inside_or_crossing():
    with pytest.raises(a.M4AdapterError):
        a.validate_passive_target(
            side="bid",target_tick=1001,best_bid_tick=1000,best_ask_tick=1001
        )
    with pytest.raises(a.M4AdapterError):
        a.validate_passive_target(
            side="ask",target_tick=1000,best_bid_tick=1000,best_ask_tick=1001
        )


def test_maker_fill_updates_inventory_and_fee_conservatively():
    import hftbacktest as h
    r=a.run_maker_fill_probe()
    assert r["accepted"].status==h.NEW
    assert r["accepted"].price_tick==1000
    assert r["no_fill_rc"]==0
    assert r["after_trade10"].status==h.NEW
    assert r["after_trade10"].exec_qty==pytest.approx(0.0)
    assert r["fill_rc"]==3
    assert r["filled"].status==h.FILLED
    assert r["filled"].exec_qty==pytest.approx(p.BASE_ORDER_QTY)
    assert r["position"]==pytest.approx(r["ledger_fill_qty"])
    assert r["position"]==pytest.approx(p.BASE_ORDER_QTY)
    assert r["fee"]==pytest.approx(r["expected_maker_fee"])


def test_maker_fill_adapter_is_stable_at_frozen_latency_profiles():
    for ns in (
        a.DIAGNOSTIC_LATENCY_NS,
        a.PRIMARY_LATENCY_NS,
        a.STRESS_LATENCY_NS,
    ):
        r=a.run_maker_fill_probe(latency_ns=ns)
        assert r["position"]==pytest.approx(p.BASE_ORDER_QTY)
        assert r["filled"].leaves_qty==pytest.approx(0.0)


def test_cancel_then_replace_is_two_phase_on_real_replay_engine():
    from hftbacktest.order import CANCELED, NEW
    r=a.run_cancel_replace_probe()
    assert r["phase1"].action=="CANCEL"
    assert r["phase1"].cancel and not r["phase1"].submit
    assert r["canceled"].status==CANCELED
    assert r["phase2"].action=="SUBMIT"
    assert not r["phase2"].cancel and r["phase2"].submit
    assert r["replacement"].status==NEW
    assert r["replacement"].price_tick==999
    assert r["position"]==pytest.approx(0.0)


def test_forced_flatten_executes_taker_and_returns_position_to_zero():
    import hftbacktest as h
    r=a.run_forced_flatten_probe()
    assert r["maker_order"].status==h.FILLED
    assert r["position_before"]==pytest.approx(p.BASE_ORDER_QTY)
    assert r["decision"].force_flatten
    assert r["decision"].flatten_direction==-1
    assert r["flatten_order"].status==h.FILLED
    assert r["flatten_order"].order_id==a.FLATTEN_ORDER_ID
    assert r["position_after"]==pytest.approx(0.0)
    assert r["fee"]==pytest.approx(r["expected_total_fee"])


def test_fixture_has_positive_feed_latency_and_valid_event_order():
    a.validate_events(a.make_fill_fixture())
    a.validate_events(a.make_cancel_replace_fixture())

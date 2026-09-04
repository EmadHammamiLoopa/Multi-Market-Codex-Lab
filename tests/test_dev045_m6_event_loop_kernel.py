from __future__ import annotations

import pytest

from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m6_economic_arena as m6
from multimarket.dev045_m6_event_loop_kernel import (
    CANONICAL_PNL_WRITE_ENABLED,
    ECONOMIC_ARENA_EXECUTION_ENABLED,
    HISTORICAL_FILE_IO_ENABLED,
    HISTORICAL_PNL_ENABLED,
    HISTORICAL_REPLAY_EXECUTION_ENABLED,
    LIVE_TRADING_AUTHORIZED,
    NETWORK_ACQUISITION_ENABLED,
    SYNTHETIC_ONLY,
    EventLoopKernelError,
    TradeFlowWindow,
    run_synthetic_kernel_probe,
)


def test_execution_surfaces_closed():
    assert SYNTHETIC_ONLY is True

    assert HISTORICAL_FILE_IO_ENABLED is False
    assert HISTORICAL_REPLAY_EXECUTION_ENABLED is False
    assert HISTORICAL_PNL_ENABLED is False
    assert ECONOMIC_ARENA_EXECUTION_ENABLED is False
    assert CANONICAL_PNL_WRITE_ENABLED is False
    assert NETWORK_ACQUISITION_ENABLED is False
    assert LIVE_TRADING_AUTHORIZED is False


def test_trade_flow_window_is_local_and_causal():
    w = TradeFlowWindow.empty()

    w.add(
        local_timestamp_ns=1_000_000_000,
        side=1,
        qty=2.0,
    )

    w.add(
        local_timestamp_ns=1_500_000_000,
        side=-1,
        qty=3.0,
    )

    buy, sell = w.quantities(
        current_local_timestamp_ns=1_500_000_000
    )

    assert buy == pytest.approx(2.0)
    assert sell == pytest.approx(3.0)

    buy, sell = w.quantities(
        current_local_timestamp_ns=2_100_000_000
    )

    assert buy == pytest.approx(0.0)
    assert sell == pytest.approx(3.0)


def test_trade_flow_rejects_future_state():
    w = TradeFlowWindow.empty()

    w.add(
        local_timestamp_ns=2_000_000_000,
        side=1,
        qty=1.0,
    )

    with pytest.raises(
        EventLoopKernelError,
        match="future_trade_in_flow_window",
    ):
        w.quantities(
            current_local_timestamp_ns=1_500_000_000
        )


def test_m02_primary_actual_kernel_flat_to_flat():
    r = run_synthetic_kernel_probe(
        policy_id="M02",
        day="2026-01-01",
        scenario=m6.PRIMARY_SCENARIO,
    )

    assert r.terminal_flat is True
    assert r.terminal_position == pytest.approx(0.0)

    assert r.maker_fill.fill is not None
    assert r.taker_fill.fill is not None

    assert r.maker_fill.fill.liquidity == "MAKER"
    assert r.taker_fill.fill.liquidity == "TAKER"

    assert r.maker_fill.fill.qty == pytest.approx(
        p.BASE_ORDER_QTY
    )

    assert r.taker_fill.fill.qty == pytest.approx(
        p.BASE_ORDER_QTY
    )

    assert r.maker_exchange_execution_ns < (
        r.maker_local_response_ns
    )

    assert r.first_nonzero_inventory_local_ns == (
        r.maker_local_response_ns
    )

    assert r.flatten_decision_local_ns > (
        r.first_nonzero_inventory_local_ns
    )

    age = (
        r.flatten_decision_local_ns
        - r.first_nonzero_inventory_local_ns
    ) / 1_000_000_000.0

    assert age >= p.INVENTORY_TIMEOUT_S
    assert age < p.INVENTORY_TIMEOUT_S + 1.0

    assert r.flatten_response_local_ns > (
        r.flatten_decision_local_ns
    )

    assert r.cancel_requests >= 1
    assert r.submit_requests >= 2

    assert r.market_wakeups >= 3
    assert r.response_wakeups >= 3
    assert r.policy_epochs >= 60


def test_m02_stress_latency_actual_kernel_flat_to_flat():
    r = run_synthetic_kernel_probe(
        policy_id="M02",
        day="2026-01-01",
        scenario=m6.STRESS_SCENARIO,
    )

    assert r.terminal_flat is True
    assert r.terminal_position == pytest.approx(0.0)

    age = (
        r.flatten_decision_local_ns
        - r.first_nonzero_inventory_local_ns
    ) / 1_000_000_000.0

    assert age >= p.INVENTORY_TIMEOUT_S
    assert age < p.INVENTORY_TIMEOUT_S + 1.0


def test_m01_common_kernel_path_is_supported():
    r = run_synthetic_kernel_probe(
        policy_id="M01",
        day="2026-01-01",
        scenario=m6.PRIMARY_SCENARIO,
    )

    assert r.terminal_flat is True
    assert r.terminal_position == pytest.approx(0.0)

    assert r.maker_fill.fill is not None
    assert r.taker_fill.fill is not None


@pytest.mark.parametrize(
    "policy_id",
    ("M03", "M04", "M05", "M06", "M07", "M08"),
)
def test_d2_refuses_policy_specific_layer_before_d3(
    policy_id,
):
    with pytest.raises(
        EventLoopKernelError,
        match="d2_probe_policy_scope",
    ):
        run_synthetic_kernel_probe(
            policy_id=policy_id,
            day="2026-01-01",
            scenario=m6.PRIMARY_SCENARIO,
        )


def test_frozen_one_lot_maker_contract():
    assert p.LOT_SIZE == pytest.approx(0.001)
    assert p.BASE_ORDER_QTY == pytest.approx(0.001)

    assert p.quote_size(100.0) == pytest.approx(
        p.BASE_ORDER_QTY
    )

    assert p.quote_size(0.01) == 0.0

from __future__ import annotations

import pytest

from multimarket.dev045_m6_event_loop_contract import (
    ADAPTER_POLICY_DECISION,
    A0_SUPPORT_CLOCK_DOMAIN,
    BASE_POLICY_DECISION,
    CANCEL_PENDING,
    FILL_ACCOUNTING_CLOCK_DOMAIN,
    HISTORICAL_FILE_IO_ENABLED,
    HISTORICAL_PNL_ENABLED,
    HISTORICAL_REPLAY_EXECUTION_ENABLED,
    INVENTORY_AGE_CLOCK_DOMAIN,
    LIVE_TRADING_AUTHORIZED,
    LOCAL_MARKET,
    LOCAL_ORDER_RESPONSE,
    M6_FILL_TIMESTAMP_DOMAIN,
    NETWORK_ACQUISITION_ENABLED,
    POLICY_CLOCK_DOMAIN,
    CancelReplaceGate,
    EventLoopContractError,
    FillClockBinding,
    InventoryClock,
    LocalWakeup,
    ResponseLedger,
    frozen_driver_boundary,
    is_adapter_policy_epoch_local,
    is_base_policy_epoch_local,
    local_ns_to_us,
    next_base_policy_epoch_after,
    ordered_local_wakeups,
    policy_epoch_kind_local,
    validate_policy_timer_wakeup,
)


def test_execution_surfaces_remain_closed():
    assert HISTORICAL_FILE_IO_ENABLED is False
    assert HISTORICAL_REPLAY_EXECUTION_ENABLED is False
    assert HISTORICAL_PNL_ENABLED is False
    assert NETWORK_ACQUISITION_ENABLED is False
    assert LIVE_TRADING_AUTHORIZED is False


def test_clock_domains_are_explicit_and_separate():
    assert POLICY_CLOCK_DOMAIN == "LOCAL_STRATEGY_TIME"
    assert A0_SUPPORT_CLOCK_DOMAIN == "LOCAL_STRATEGY_TIME"
    assert INVENTORY_AGE_CLOCK_DOMAIN == (
        "LOCAL_POSITION_KNOWLEDGE_TIME"
    )

    assert FILL_ACCOUNTING_CLOCK_DOMAIN == (
        "EXCHANGE_EXECUTION_TIME"
    )

    assert M6_FILL_TIMESTAMP_DOMAIN == (
        "EXCHANGE_EXECUTION_TIME"
    )


def test_ns_to_us_requires_exact_microsecond_alignment():
    assert local_ns_to_us(60_000_000_000) == 60_000_000

    with pytest.raises(
        EventLoopContractError,
        match="local_clock_not_microsecond_aligned",
    ):
        local_ns_to_us(60_000_000_001)


@pytest.mark.parametrize(
    ("local_ns", "expected"),
    (
        (0, True),
        (250_000_000, False),
        (999_999_000, False),
        (1_000_000_000, True),
        (1_250_000_000, False),
        (59_000_000_000, True),
        (60_000_000_000, True),
    ),
)
def test_base_policy_epoch_uses_local_clock(
    local_ns,
    expected,
):
    assert is_base_policy_epoch_local(local_ns) is expected


@pytest.mark.parametrize(
    ("local_ns", "expected"),
    (
        (59_000_000_000, False),
        (59_999_999_000, False),
        (60_000_000_000, True),
        (60_000_001_000, False),
        (61_000_000_000, False),
        (120_000_000_000, True),
    ),
)
def test_apr_adapter_epoch_uses_exact_local_minute(
    local_ns,
    expected,
):
    assert is_adapter_policy_epoch_local(
        day="2026-04-01",
        local_timestamp_ns=local_ns,
    ) is expected


def test_exchange_timestamp_cannot_manufacture_adapter_epoch():
    # Exchange execution happened exactly on the minute.
    exch_ns = 60_000_000_000

    # Strategy did not receive the information until 200us later.
    local_ns = 60_000_200_000

    assert exch_ns % 60_000_000_000 == 0

    assert is_adapter_policy_epoch_local(
        day="2026-04-01",
        local_timestamp_ns=local_ns,
    ) is False


def test_jan_mar_never_have_adapter_epoch():
    for day in (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
    ):
        assert is_adapter_policy_epoch_local(
            day=day,
            local_timestamp_ns=60_000_000_000,
        ) is False


def test_policy_epoch_kind_prefers_adapter_on_minute():
    assert policy_epoch_kind_local(
        day="2026-04-01",
        local_timestamp_ns=60_000_000_000,
    ) == ADAPTER_POLICY_DECISION

    assert policy_epoch_kind_local(
        day="2026-04-01",
        local_timestamp_ns=61_000_000_000,
    ) == BASE_POLICY_DECISION

    assert policy_epoch_kind_local(
        day="2026-04-01",
        local_timestamp_ns=61_250_000_000,
    ) is None


def test_next_base_epoch_is_strictly_next_second():
    assert next_base_policy_epoch_after(0) == 1_000_000_000
    assert next_base_policy_epoch_after(
        1_000_000_000
    ) == 2_000_000_000
    assert next_base_policy_epoch_after(
        1_000_000_001
    ) == 2_000_000_000


def test_same_local_timestamp_order_market_response_policy():
    xs = ordered_local_wakeups(
        (
            LocalWakeup(
                60_000_000_000,
                ADAPTER_POLICY_DECISION,
                0,
            ),
            LocalWakeup(
                60_000_000_000,
                LOCAL_ORDER_RESPONSE,
                7,
            ),
            LocalWakeup(
                60_000_000_000,
                LOCAL_MARKET,
                3,
            ),
        )
    )

    assert tuple(x.kind for x in xs) == (
        LOCAL_MARKET,
        LOCAL_ORDER_RESPONSE,
        ADAPTER_POLICY_DECISION,
    )


def test_policy_timer_validation_is_local_grid_only():
    validate_policy_timer_wakeup(
        day="2026-04-01",
        wakeup=LocalWakeup(
            60_000_000_000,
            ADAPTER_POLICY_DECISION,
        ),
    )

    with pytest.raises(
        EventLoopContractError,
        match="policy_timer_off_grid",
    ):
        validate_policy_timer_wakeup(
            day="2026-04-01",
            wakeup=LocalWakeup(
                60_250_000_000,
                BASE_POLICY_DECISION,
            ),
        )


def test_inventory_age_starts_at_local_response_not_exchange_fill():
    clock = InventoryClock.flat()

    exchange_fill_ns = 10_000_000_000
    local_response_ns = 10_250_000_000

    FillClockBinding(
        local_response_timestamp_ns=local_response_ns,
        exchange_execution_timestamp_ns=exchange_fill_ns,
    )

    clock = clock.observe_local_position(
        new_position=0.001,
        local_response_timestamp_ns=local_response_ns,
    )

    # At exchange fill +60s, local strategy has known inventory only 59.75s.
    assert clock.age_seconds(
        current_local_timestamp_ns=70_000_000_000,
    ) == pytest.approx(59.75)

    # Exact 60s timeout is based on local knowledge.
    assert clock.age_seconds(
        current_local_timestamp_ns=70_250_000_000,
    ) == pytest.approx(60.0)


def test_same_sign_partial_fill_keeps_original_inventory_clock():
    clock = InventoryClock.flat()

    clock = clock.observe_local_position(
        new_position=0.001,
        local_response_timestamp_ns=10_250_000_000,
    )

    clock = clock.observe_local_position(
        new_position=0.002,
        local_response_timestamp_ns=11_250_000_000,
    )

    assert clock.position == pytest.approx(0.002)
    assert clock.nonzero_since_local_ns == 10_250_000_000


def test_flat_resets_inventory_clock():
    clock = InventoryClock.flat()

    clock = clock.observe_local_position(
        new_position=-0.001,
        local_response_timestamp_ns=10_250_000_000,
    )

    clock = clock.observe_local_position(
        new_position=0.0,
        local_response_timestamp_ns=20_250_000_000,
    )

    assert clock.position == 0.0
    assert clock.nonzero_since_local_ns is None
    assert clock.age_seconds(
        current_local_timestamp_ns=100_000_000_000,
    ) == 0.0


def test_inventory_sign_flip_without_flat_fails_closed():
    clock = InventoryClock.flat()

    clock = clock.observe_local_position(
        new_position=0.001,
        local_response_timestamp_ns=10_000_000_000,
    )

    with pytest.raises(
        EventLoopContractError,
        match="inventory_sign_flip_without_flat",
    ):
        clock.observe_local_position(
            new_position=-0.001,
            local_response_timestamp_ns=11_000_000_000,
        )


def test_fill_clock_requires_exchange_not_after_local_response():
    FillClockBinding(
        local_response_timestamp_ns=10_250_000_000,
        exchange_execution_timestamp_ns=10_000_000_000,
    )

    with pytest.raises(
        EventLoopContractError,
        match="exchange_fill_after_local_response",
    ):
        FillClockBinding(
            local_response_timestamp_ns=10_000_000_000,
            exchange_execution_timestamp_ns=10_250_000_000,
        )


def test_response_ledger_consumes_each_response_once():
    ledger = ResponseLedger.empty()

    ledger = ledger.consume(1)
    ledger = ledger.consume(2)

    assert ledger.consumed_response_sequences == frozenset(
        (1, 2)
    )

    with pytest.raises(
        EventLoopContractError,
        match="duplicate_order_response_consumption",
    ):
        ledger.consume(2)


def test_response_dedup_is_not_price_qty_timestamp_based():
    # Two real response wakeups are distinct even if every execution field
    # outside the driver sequence would happen to be equal.
    ledger = ResponseLedger.empty()
    ledger = ledger.consume(100)
    ledger = ledger.consume(101)

    assert len(ledger.consumed_response_sequences) == 2


def test_cancel_response_required_before_replacement():
    gate = CancelReplaceGate.working(4101)

    gate = gate.request_cancel_for_replacement(
        replacement_tick=999,
        replacement_qty=0.001,
    )

    assert gate.cancel_state == CANCEL_PENDING
    assert gate.replacement_authorized is False

    with pytest.raises(
        EventLoopContractError,
        match="replacement_before_cancel_response",
    ):
        gate.record_replacement_submit(
            new_order_id=4103,
        )

    gate = gate.receive_cancel_response(
        order_id=4101,
    )

    assert gate.replacement_authorized is True

    gate = gate.record_replacement_submit(
        new_order_id=4103,
    )

    assert gate.working_order_id == 4103
    assert gate.replacement_authorized is False


def test_wrong_cancel_response_order_fails_closed():
    gate = CancelReplaceGate.working(4101)

    gate = gate.request_cancel_for_replacement(
        replacement_tick=999,
        replacement_qty=0.001,
    )

    with pytest.raises(
        EventLoopContractError,
        match="cancel_response_order_mismatch",
    ):
        gate.receive_cancel_response(
            order_id=9999,
        )


def test_frozen_driver_boundary_is_closed():
    x = frozen_driver_boundary()

    assert x.policy_clock_domain == "LOCAL_STRATEGY_TIME"
    assert x.a0_clock_domain == "LOCAL_STRATEGY_TIME"

    assert x.fill_accounting_clock_domain == (
        "EXCHANGE_EXECUTION_TIME"
    )

    assert x.market_event_is_policy_epoch is False
    assert x.probability_carry_enabled is False
    assert x.response_tuple_dedup_enabled is False

    assert x.historical_file_io_enabled is False
    assert x.historical_replay_execution_enabled is False
    assert x.historical_pnl_enabled is False

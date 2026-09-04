from __future__ import annotations

from datetime import datetime, timezone
import math

import pytest

from multimarket import dev045_m3_policy as p
from multimarket.dev045_m4_adapter import ReplayOrderView
from multimarket.dev045_m4_m6_binding import (
    FILL,
    NO_FILL,
    HFT_BUY,
    HFT_SELL,
    HFT_NEW,
    HFT_FILLED,
    HFT_CANCELED,
    HFT_PARTIALLY_FILLED,
    M4M6BindingError,
    ReplayStateView,
    bind_execution,
    bind_passive_execution,
    bind_forced_flatten_execution,
    bind_forced_flatten_from_state_delta,
)
from multimarket.dev045_m5_fee_amendment import (
    PRIMARY_MAKER_RATE,
    PRIMARY_TAKER_RATE,
)
from multimarket.dev045_m5_prereg import AUTHORIZED_DAYS
from multimarket.dev045_m6_economic_arena import (
    PRIMARY_SCENARIO,
    account_fill_bucket,
)


def ns(day: str, hour: int = 0, second: int = 0) -> int:
    dt = datetime.fromisoformat(day).replace(
        hour=hour,
        minute=0,
        second=second,
        tzinfo=timezone.utc,
    )
    return int(dt.timestamp() * 1_000_000_000)


def view(
    *,
    day: str,
    side: int,
    status: int,
    exec_qty: float,
    exec_price_tick: int,
    leaves_qty: float,
    order_id: int = 4101,
    second: int = 0,
) -> ReplayOrderView:
    ts = ns(day, second=second)
    return ReplayOrderView(
        order_id=order_id,
        status=status,
        side=side,
        price_tick=exec_price_tick if exec_price_tick > 0 else 1_000_000,
        exec_price_tick=exec_price_tick,
        exec_qty=exec_qty,
        leaves_qty=leaves_qty,
        exch_timestamp=ts,
        local_timestamp=ts + 250_000_000,
    )


def test_pinned_hft_order_constants_match_binding_when_available() -> None:
    h = pytest.importorskip("hftbacktest.order")
    assert h.BUY == HFT_BUY == 1
    assert h.SELL == HFT_SELL == -1
    assert h.NEW == HFT_NEW == 1
    assert h.FILLED == HFT_FILLED == 3
    assert h.CANCELED == HFT_CANCELED == 4
    assert h.PARTIALLY_FILLED == HFT_PARTIALLY_FILLED == 5


def test_no_fill_remains_explicit_and_is_not_silently_dropped() -> None:
    day = AUTHORIZED_DAYS[0]
    event = bind_passive_execution(
        view(
            day=day,
            side=HFT_BUY,
            status=HFT_NEW,
            exec_qty=0.0,
            exec_price_tick=0,
            leaves_qty=p.BASE_ORDER_QTY,
        ),
        policy_id="M01",
        day=day,
    )
    assert event.kind == NO_FILL
    assert event.fill is None
    assert event.exec_qty == 0.0
    assert event.executed_quote_notional == 0.0
    assert event.liquidity == "MAKER"
    assert event.side == "BUY"


def test_identical_m4_view_binds_deterministically() -> None:
    day = AUTHORIZED_DAYS[0]
    v = view(
        day=day,
        side=HFT_BUY,
        status=HFT_FILLED,
        exec_qty=p.BASE_ORDER_QTY,
        exec_price_tick=1_000_000,
        leaves_qty=0.0,
    )
    a = bind_passive_execution(v, policy_id="M01", day=day)
    b = bind_passive_execution(v, policy_id="M01", day=day)
    assert a == b


def test_maker_fill_preserves_side_qty_price_and_quote_notional() -> None:
    day = AUTHORIZED_DAYS[0]
    event = bind_passive_execution(
        view(
            day=day,
            side=HFT_BUY,
            status=HFT_FILLED,
            exec_qty=p.BASE_ORDER_QTY,
            exec_price_tick=1_000_000,
            leaves_qty=0.0,
        ),
        policy_id="M02",
        day=day,
    )

    assert event.kind == FILL
    assert event.fill is not None
    assert event.fill.side == "BUY"
    assert event.fill.liquidity == "MAKER"
    assert event.fill.qty == pytest.approx(p.BASE_ORDER_QTY)
    assert event.fill.price == pytest.approx(1_000_000 * p.TICK_SIZE)

    independent_notional = (
        float(event.fill.qty) * float(event.fill.price)
    )
    assert event.executed_quote_notional == pytest.approx(
        independent_notional
    )


def test_direct_taker_view_binding_is_forbidden() -> None:
    day = AUTHORIZED_DAYS[0]
    v = view(
        day=day,
        side=HFT_SELL,
        status=HFT_FILLED,
        exec_qty=p.BASE_ORDER_QTY,
        exec_price_tick=1_001_000,
        leaves_qty=0.0,
        order_id=4901,
        second=1,
    )
    with pytest.raises(
        M4M6BindingError,
        match="taker_requires_state_delta",
    ):
        bind_forced_flatten_execution(
            v,
            policy_id="M02",
            day=day,
        )


def test_forced_flatten_state_delta_preserves_taker_sell() -> None:
    day = AUTHORIZED_DAYS[0]
    q = p.BASE_ORDER_QTY

    v = view(
        day=day,
        side=HFT_SELL,
        status=HFT_FILLED,
        exec_qty=q,
        exec_price_tick=1_001_000,
        leaves_qty=0.0,
        order_id=4901,
        second=1,
    )

    before = ReplayStateView(
        position=q,
        balance=-100.0,
        fee=100.0 * PRIMARY_MAKER_RATE,
        num_trades=1,
        trading_volume=q,
        trading_value=100.0,
    )
    after = ReplayStateView(
        position=0.0,
        balance=0.1,
        fee=(
            100.0 * PRIMARY_MAKER_RATE
            + 100.1 * PRIMARY_TAKER_RATE
        ),
        num_trades=2,
        trading_volume=2.0 * q,
        trading_value=200.1,
    )

    event = bind_forced_flatten_from_state_delta(
        v,
        before=before,
        after=after,
        policy_id="M02",
        day=day,
    )

    assert event.kind == FILL
    assert event.fill is not None
    assert event.side == "SELL"
    assert event.fill.side == "SELL"
    assert event.liquidity == "TAKER"
    assert event.fill.liquidity == "TAKER"
    assert event.fill.qty == pytest.approx(q)
    assert event.fill.price == pytest.approx(100_100.0)
    assert event.executed_quote_notional == pytest.approx(100.1)



def test_bound_maker_plus_taker_cycle_uses_frozen_m6_fee_roles() -> None:
    day = AUTHORIZED_DAYS[0]
    q = p.BASE_ORDER_QTY

    entry = bind_passive_execution(
        view(
            day=day,
            side=HFT_BUY,
            status=HFT_FILLED,
            exec_qty=q,
            exec_price_tick=1_000_000,
            leaves_qty=0.0,
            order_id=4101,
            second=0,
        ),
        policy_id="M03",
        day=day,
    )

    before = ReplayStateView(
        position=q,
        balance=-100.0,
        fee=100.0 * PRIMARY_MAKER_RATE,
        num_trades=1,
        trading_volume=q,
        trading_value=100.0,
    )
    after = ReplayStateView(
        position=0.0,
        balance=0.1,
        fee=(
            100.0 * PRIMARY_MAKER_RATE
            + 100.1 * PRIMARY_TAKER_RATE
        ),
        num_trades=2,
        trading_volume=2.0 * q,
        trading_value=200.1,
    )

    exit_ = bind_forced_flatten_from_state_delta(
        view(
            day=day,
            side=HFT_SELL,
            status=HFT_FILLED,
            exec_qty=q,
            exec_price_tick=1_001_000,
            leaves_qty=0.0,
            order_id=4901,
            second=1,
        ),
        before=before,
        after=after,
        policy_id="M03",
        day=day,
    )

    assert entry.fill is not None
    assert exit_.fill is not None

    cycle = account_fill_bucket(
        [entry.fill, exit_.fill],
        scenario=PRIMARY_SCENARIO,
    )[0]

    expected_fee = (
        entry.executed_quote_notional * PRIMARY_MAKER_RATE
        + exit_.executed_quote_notional * PRIMARY_TAKER_RATE
    )

    assert cycle.fees == pytest.approx(expected_fee)
    assert cycle.maker_notional == pytest.approx(
        entry.executed_quote_notional
    )
    assert cycle.taker_notional == pytest.approx(
        exit_.executed_quote_notional
    )


def test_multilevel_taker_uses_full_state_delta_not_last_order_fill() -> None:
    day = AUTHORIZED_DAYS[0]

    # Inventory 0.003 is within the frozen M3 cap. The forced market sell
    # executes 0.002 at 100000 and 0.001 at 99900. The final OrderView
    # exposes only the last 0.001 execution, while state deltas preserve
    # the full 0.003 / 299.9 quote-notional execution.
    before = ReplayStateView(
        position=0.003,
        balance=-300.0,
        fee=0.06,
        num_trades=3,
        trading_volume=0.003,
        trading_value=300.0,
    )
    after = ReplayStateView(
        position=0.0,
        balance=-0.1,
        fee=0.06 + 299.9 * PRIMARY_TAKER_RATE,
        num_trades=5,
        trading_volume=0.006,
        trading_value=599.9,
    )

    event = bind_forced_flatten_from_state_delta(
        view(
            day=day,
            side=HFT_SELL,
            status=HFT_FILLED,
            exec_qty=0.001,
            exec_price_tick=999_000,
            leaves_qty=0.0,
            order_id=4901,
            second=2,
        ),
        before=before,
        after=after,
        policy_id="M04",
        day=day,
    )

    assert event.fill is not None
    assert event.exec_qty == pytest.approx(0.003)
    assert event.fill.qty == pytest.approx(0.003)
    assert event.executed_quote_notional == pytest.approx(299.9)
    assert event.fill.price == pytest.approx(299.9 / 0.003)

    # Proves we did not accidentally account only the final 0.001 fill.
    assert event.exec_qty > 0.001
    assert event.executed_quote_notional > 99.9


def test_taker_state_delta_cash_conservation_fails_closed() -> None:
    day = AUTHORIZED_DAYS[0]
    q = p.BASE_ORDER_QTY

    before = ReplayStateView(
        position=q,
        balance=-100.0,
        fee=0.02,
        num_trades=1,
        trading_volume=q,
        trading_value=100.0,
    )
    bad_after = ReplayStateView(
        position=0.0,
        balance=0.0,
        fee=0.07,
        num_trades=2,
        trading_volume=2.0 * q,
        trading_value=200.1,
    )

    with pytest.raises(
        M4M6BindingError,
        match="flatten_cash_conservation",
    ):
        bind_forced_flatten_from_state_delta(
            view(
                day=day,
                side=HFT_SELL,
                status=HFT_FILLED,
                exec_qty=q,
                exec_price_tick=1_001_000,
                leaves_qty=0.0,
                order_id=4901,
                second=1,
            ),
            before=before,
            after=bad_after,
            policy_id="M03",
            day=day,
        )



def test_partial_fill_maps_to_fill_without_changing_quantity() -> None:
    day = AUTHORIZED_DAYS[1]
    q = p.BASE_ORDER_QTY / 2.0
    event = bind_passive_execution(
        view(
            day=day,
            side=HFT_BUY,
            status=HFT_PARTIALLY_FILLED,
            exec_qty=q,
            exec_price_tick=1_000_000,
            leaves_qty=q,
        ),
        policy_id="M04",
        day=day,
    )
    assert event.kind == FILL
    assert event.fill is not None
    assert event.fill.qty == pytest.approx(q)


@pytest.mark.parametrize(
    "bad_qty",
    [float("nan"), float("inf"), -0.001],
)
def test_nonfinite_or_negative_execution_quantity_fails_closed(
    bad_qty: float,
) -> None:
    day = AUTHORIZED_DAYS[0]
    with pytest.raises(M4M6BindingError, match="exec_qty"):
        bind_passive_execution(
            view(
                day=day,
                side=HFT_BUY,
                status=HFT_FILLED,
                exec_qty=bad_qty,
                exec_price_tick=1_000_000,
                leaves_qty=0.0,
            ),
            policy_id="M01",
            day=day,
        )


def test_unknown_side_fails_closed() -> None:
    day = AUTHORIZED_DAYS[0]
    with pytest.raises(M4M6BindingError, match="side"):
        bind_passive_execution(
            view(
                day=day,
                side=0,
                status=HFT_FILLED,
                exec_qty=p.BASE_ORDER_QTY,
                exec_price_tick=1_000_000,
                leaves_qty=0.0,
            ),
            policy_id="M01",
            day=day,
        )


def test_quantity_without_fill_status_fails_closed() -> None:
    day = AUTHORIZED_DAYS[0]
    with pytest.raises(
        M4M6BindingError,
        match="qty_without_fill_status",
    ):
        bind_passive_execution(
            view(
                day=day,
                side=HFT_BUY,
                status=HFT_NEW,
                exec_qty=p.BASE_ORDER_QTY,
                exec_price_tick=1_000_000,
                leaves_qty=0.0,
            ),
            policy_id="M01",
            day=day,
        )


def test_filled_status_with_nonzero_leaves_fails_closed() -> None:
    day = AUTHORIZED_DAYS[0]
    with pytest.raises(
        M4M6BindingError,
        match="filled_with_leaves",
    ):
        bind_passive_execution(
            view(
                day=day,
                side=HFT_BUY,
                status=HFT_FILLED,
                exec_qty=p.BASE_ORDER_QTY / 2.0,
                exec_price_tick=1_000_000,
                leaves_qty=p.BASE_ORDER_QTY / 2.0,
            ),
            policy_id="M01",
            day=day,
        )


def test_timestamp_day_mismatch_fails_closed() -> None:
    day = AUTHORIZED_DAYS[0]
    other_day = AUTHORIZED_DAYS[1]

    with pytest.raises(
        M4M6BindingError,
        match="timestamp_day_mismatch",
    ):
        bind_execution(
            view(
                day=other_day,
                side=HFT_BUY,
                status=HFT_FILLED,
                exec_qty=p.BASE_ORDER_QTY,
                exec_price_tick=1_000_000,
                leaves_qty=0.0,
            ),
            policy_id="M01",
            day=day,
            liquidity="MAKER",
        )


def test_unauthorized_liquidity_and_day_fail_closed() -> None:
    day = AUTHORIZED_DAYS[0]
    v = view(
        day=day,
        side=HFT_BUY,
        status=HFT_FILLED,
        exec_qty=p.BASE_ORDER_QTY,
        exec_price_tick=1_000_000,
        leaves_qty=0.0,
    )

    with pytest.raises(M4M6BindingError, match="liquidity"):
        bind_execution(
            v,
            policy_id="M01",
            day=day,
            liquidity="UNKNOWN",
        )

    with pytest.raises(M4M6BindingError, match="authorized_day"):
        bind_execution(
            v,
            policy_id="M01",
            day="2026-08-01",
            liquidity="MAKER",
        )

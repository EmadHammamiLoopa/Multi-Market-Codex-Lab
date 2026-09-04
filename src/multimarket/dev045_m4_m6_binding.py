from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math

from multimarket import dev045_m3_policy as p
from multimarket.dev045_m4_adapter import ReplayOrderView
from multimarket.dev045_m5_prereg import AUTHORIZED_DAYS
from multimarket.dev045_m6_economic_arena import FillRecord


# Frozen hftbacktest 2.4.4 order constants from pinned upstream identity
# a244a14250b42d97fc305569c93c4117cd5e1dff.
HFT_BUY = 1
HFT_SELL = -1

HFT_NEW = 1
HFT_FILLED = 3
HFT_CANCELED = 4
HFT_PARTIALLY_FILLED = 5

FILL = "FILL"
NO_FILL = "NO_FILL"

MAKER = "MAKER"
TAKER = "TAKER"


class M4M6BindingError(RuntimeError):
    pass


@dataclass(frozen=True)
class BoundReplayEvent:
    kind: str
    policy_id: str
    day: str
    order_id: int
    timestamp_ns: int
    side: str
    liquidity: str
    exec_qty: float
    exec_price_tick: int
    executed_quote_notional: float
    fill: FillRecord | None


@dataclass(frozen=True)
class ReplayStateView:
    position: float
    balance: float
    fee: float
    num_trades: int
    trading_volume: float
    trading_value: float


def _exact_int(name: str, value: object, *, minimum: int | None = None) -> int:
    if isinstance(value, bool):
        raise M4M6BindingError(name)
    try:
        ivalue = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise M4M6BindingError(name) from exc
    try:
        equal = bool(ivalue == value)
    except Exception as exc:
        raise M4M6BindingError(name) from exc
    if not equal:
        raise M4M6BindingError(name)
    if minimum is not None and ivalue < minimum:
        raise M4M6BindingError(name)
    return ivalue


def _finite(name: str, value: object) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise M4M6BindingError(name) from exc
    if not math.isfinite(x):
        raise M4M6BindingError(name)
    return x


def _finite_nonnegative(name: str, value: object) -> float:
    x = _finite(name, value)
    if x < 0.0:
        raise M4M6BindingError(name)
    return x


def snapshot_state_values(values: object) -> ReplayStateView:
    try:
        position = values.position
        balance = values.balance
        fee = values.fee
        num_trades = values.num_trades
        trading_volume = values.trading_volume
        trading_value = values.trading_value
    except AttributeError as exc:
        raise M4M6BindingError("state_values") from exc

    return ReplayStateView(
        position=_finite("state_position", position),
        balance=_finite("state_balance", balance),
        fee=_finite("state_fee", fee),
        num_trades=_exact_int("state_num_trades", num_trades, minimum=0),
        trading_volume=_finite_nonnegative(
            "state_trading_volume", trading_volume
        ),
        trading_value=_finite_nonnegative(
            "state_trading_value", trading_value
        ),
    )


def _timestamp_day(timestamp_ns: int) -> str:
    try:
        dt = datetime.fromtimestamp(
            int(timestamp_ns) / 1_000_000_000,
            tz=timezone.utc,
        )
    except (OverflowError, OSError, ValueError) as exc:
        raise M4M6BindingError("timestamp_ns") from exc
    return dt.date().isoformat()


def _side_name(side: int) -> str:
    if side == HFT_BUY:
        return "BUY"
    if side == HFT_SELL:
        return "SELL"
    raise M4M6BindingError("side")


def bind_execution(
    view: ReplayOrderView,
    *,
    policy_id: str,
    day: str,
    liquidity: str,
) -> BoundReplayEvent:
    """
    Deterministically bind one M4 execution-response view into an explicit
    binding event. NO_FILL is retained as an event and is never silently
    discarded.

    Maker/taker role is supplied by the frozen replay path:
      passive M3 order -> MAKER
      forced executable flatten -> TAKER

    The binding does not infer liquidity from price or PnL.
    """
    if not isinstance(view, ReplayOrderView):
        raise M4M6BindingError("view")

    if policy_id not in p.POLICY_IDS:
        raise M4M6BindingError("policy_id")
    if day not in AUTHORIZED_DAYS:
        raise M4M6BindingError("authorized_day")
    if liquidity not in (MAKER, TAKER):
        raise M4M6BindingError("liquidity")
    if liquidity == TAKER:
        raise M4M6BindingError("taker_requires_state_delta")

    order_id = _exact_int("order_id", view.order_id, minimum=1)
    status = _exact_int("status", view.status, minimum=0)
    side_raw = _exact_int("side", view.side)
    side = _side_name(side_raw)

    timestamp_ns = _exact_int(
        "exch_timestamp",
        view.exch_timestamp,
        minimum=0,
    )
    _exact_int(
        "local_timestamp",
        view.local_timestamp,
        minimum=0,
    )

    if _timestamp_day(timestamp_ns) != day:
        raise M4M6BindingError("timestamp_day_mismatch")

    qty = _finite_nonnegative("exec_qty", view.exec_qty)
    leaves_qty = _finite_nonnegative("leaves_qty", view.leaves_qty)

    exec_price_tick = _exact_int(
        "exec_price_tick",
        view.exec_price_tick,
    )

    if qty == 0.0:
        if status not in (HFT_NEW, HFT_CANCELED):
            raise M4M6BindingError("unexpected_no_fill_status")

        return BoundReplayEvent(
            kind=NO_FILL,
            policy_id=policy_id,
            day=day,
            order_id=order_id,
            timestamp_ns=timestamp_ns,
            side=side,
            liquidity=liquidity,
            exec_qty=0.0,
            exec_price_tick=exec_price_tick,
            executed_quote_notional=0.0,
            fill=None,
        )

    if status not in (HFT_FILLED, HFT_PARTIALLY_FILLED):
        raise M4M6BindingError("qty_without_fill_status")

    if exec_price_tick <= 0:
        raise M4M6BindingError("exec_price_tick")

    if status == HFT_FILLED and leaves_qty > 1e-12:
        raise M4M6BindingError("filled_with_leaves")

    price = float(exec_price_tick) * float(p.TICK_SIZE)
    if not math.isfinite(price) or price <= 0.0:
        raise M4M6BindingError("price")

    quote_notional = qty * price
    if not math.isfinite(quote_notional) or quote_notional <= 0.0:
        raise M4M6BindingError("quote_notional")

    fill = FillRecord(
        policy_id=policy_id,
        day=day,
        timestamp_ns=timestamp_ns,
        side=side,
        qty=qty,
        price=price,
        liquidity=liquidity,
    )

    # Independent conservation check at the binding boundary.
    if not math.isclose(
        float(fill.qty) * float(fill.price),
        quote_notional,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise M4M6BindingError("notional_conservation")

    return BoundReplayEvent(
        kind=FILL,
        policy_id=policy_id,
        day=day,
        order_id=order_id,
        timestamp_ns=timestamp_ns,
        side=side,
        liquidity=liquidity,
        exec_qty=qty,
        exec_price_tick=exec_price_tick,
        executed_quote_notional=quote_notional,
        fill=fill,
    )


def bind_passive_execution(
    view: ReplayOrderView,
    *,
    policy_id: str,
    day: str,
) -> BoundReplayEvent:
    return bind_execution(
        view,
        policy_id=policy_id,
        day=day,
        liquidity=MAKER,
    )


def bind_forced_flatten_execution(
    view: ReplayOrderView,
    *,
    policy_id: str,
    day: str,
) -> BoundReplayEvent:
    """
    Deliberately forbidden for historical accounting.

    A PartialFillExchange MARKET order can execute across multiple depth
    levels. The final ReplayOrderView contains the most recent execution
    quantity/price, while the simulator state contains the full execution
    ledger. Therefore a taker flatten must bind through state deltas.
    """
    raise M4M6BindingError("taker_requires_state_delta")


def bind_forced_flatten_from_state_delta(
    view: ReplayOrderView,
    *,
    before: ReplayStateView,
    after: ReplayStateView,
    policy_id: str,
    day: str,
) -> BoundReplayEvent:
    """
    Bind one synchronous forced MARKET flatten from simulator state deltas.

    `before` must be captured immediately before submit_forced_flatten and
    `after` immediately after its waited response. Multiple price-level fills
    inside that single MARKET request are conservatively aggregated into one
    exact-VWAP M6 FillRecord. This preserves total executed quantity, cash,
    notional, and frozen taker-fee economics.
    """
    if not isinstance(view, ReplayOrderView):
        raise M4M6BindingError("view")
    if not isinstance(before, ReplayStateView):
        raise M4M6BindingError("before_state")
    if not isinstance(after, ReplayStateView):
        raise M4M6BindingError("after_state")

    if policy_id not in p.POLICY_IDS:
        raise M4M6BindingError("policy_id")
    if day not in AUTHORIZED_DAYS:
        raise M4M6BindingError("authorized_day")

    order_id = _exact_int("order_id", view.order_id, minimum=1)
    status = _exact_int("status", view.status, minimum=0)
    side_raw = _exact_int("side", view.side)
    side = _side_name(side_raw)

    timestamp_ns = _exact_int(
        "exch_timestamp",
        view.exch_timestamp,
        minimum=0,
    )
    _exact_int(
        "local_timestamp",
        view.local_timestamp,
        minimum=0,
    )

    if _timestamp_day(timestamp_ns) != day:
        raise M4M6BindingError("timestamp_day_mismatch")

    if status != HFT_FILLED:
        raise M4M6BindingError("flatten_not_filled")

    leaves_qty = _finite_nonnegative("leaves_qty", view.leaves_qty)
    if leaves_qty > 1e-12:
        raise M4M6BindingError("flatten_nonzero_leaves")

    final_exec_qty = _finite_nonnegative("exec_qty", view.exec_qty)
    final_exec_price_tick = _exact_int(
        "exec_price_tick",
        view.exec_price_tick,
    )
    if final_exec_qty <= 0.0:
        raise M4M6BindingError("flatten_final_exec_qty")
    if final_exec_price_tick <= 0:
        raise M4M6BindingError("flatten_final_exec_price_tick")

    # Revalidate snapshots even when callers constructed ReplayStateView
    # directly rather than via snapshot_state_values().
    b_position = _finite("before_position", before.position)
    a_position = _finite("after_position", after.position)
    b_balance = _finite("before_balance", before.balance)
    a_balance = _finite("after_balance", after.balance)
    b_fee = _finite("before_fee", before.fee)
    a_fee = _finite("after_fee", after.fee)

    b_trades = _exact_int(
        "before_num_trades", before.num_trades, minimum=0
    )
    a_trades = _exact_int(
        "after_num_trades", after.num_trades, minimum=0
    )

    b_volume = _finite_nonnegative(
        "before_trading_volume", before.trading_volume
    )
    a_volume = _finite_nonnegative(
        "after_trading_volume", after.trading_volume
    )
    b_value = _finite_nonnegative(
        "before_trading_value", before.trading_value
    )
    a_value = _finite_nonnegative(
        "after_trading_value", after.trading_value
    )

    qty = a_volume - b_volume
    quote_notional = a_value - b_value
    trade_count_delta = a_trades - b_trades
    fee_delta = a_fee - b_fee

    if not math.isfinite(qty) or qty <= 0.0:
        raise M4M6BindingError("flatten_volume_delta")
    if not math.isfinite(quote_notional) or quote_notional <= 0.0:
        raise M4M6BindingError("flatten_value_delta")
    if trade_count_delta <= 0:
        raise M4M6BindingError("flatten_trade_count_delta")
    if fee_delta < -1e-12:
        raise M4M6BindingError("flatten_fee_delta")

    # The final OrderView is one of the internal executions. It may be
    # smaller than the aggregate MARKET quantity, but never larger.
    if final_exec_qty > qty + 1e-12:
        raise M4M6BindingError("final_exec_exceeds_ledger_delta")

    side_sign = 1.0 if side == "BUY" else -1.0

    position_delta = a_position - b_position
    expected_position_delta = side_sign * qty
    if not math.isclose(
        position_delta,
        expected_position_delta,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise M4M6BindingError("flatten_position_conservation")

    cash_delta = a_balance - b_balance
    expected_cash_delta = -side_sign * quote_notional
    if not math.isclose(
        cash_delta,
        expected_cash_delta,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise M4M6BindingError("flatten_cash_conservation")

    price = quote_notional / qty
    if not math.isfinite(price) or price <= 0.0:
        raise M4M6BindingError("flatten_vwap")

    fill = FillRecord(
        policy_id=policy_id,
        day=day,
        timestamp_ns=timestamp_ns,
        side=side,
        qty=qty,
        price=price,
        liquidity=TAKER,
    )

    if not math.isclose(
        float(fill.qty) * float(fill.price),
        quote_notional,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise M4M6BindingError("flatten_notional_conservation")

    return BoundReplayEvent(
        kind=FILL,
        policy_id=policy_id,
        day=day,
        order_id=order_id,
        timestamp_ns=timestamp_ns,
        side=side,
        liquidity=TAKER,
        exec_qty=qty,
        exec_price_tick=final_exec_price_tick,
        executed_quote_notional=quote_notional,
        fill=fill,
    )

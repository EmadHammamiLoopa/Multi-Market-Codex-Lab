from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

import pytest

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r19_response_batch_replacement_driver as d6r19
from multimarket import dev045_d6r20_residual_flatten_driver as d6r20
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_event_loop_contract as contract
from multimarket import dev045_m6_event_loop_kernel as d2
from multimarket import dev045_m6_policy_integration as integration
from multimarket.dev044_t0_strategy_contract import LONG, SHORT


DAY = "2026-01-01"
SCENARIO = "Q0_PRIMARY_250_250"
DAY_START_NS = integration.day_start_ns(DAY)


class FakeHft:
    GTC = 0
    LIMIT = 0
    MARKET = 1


@dataclass
class FakeOrder:
    order_id: int
    side: int
    price_tick: int
    status: int = d2.HFT_NEW
    req: int = d2.HFT_NONE
    exec_price_tick: int = 0
    exec_qty: float = 0.0
    leaves_qty: float = p.BASE_ORDER_QTY
    exch_timestamp: int = DAY_START_NS
    local_timestamp: int = DAY_START_NS


@dataclass
class FakeStateValues:
    position: float = 0.0
    balance: float = 0.0
    fee: float = 0.0
    num_trades: int = 0
    trading_volume: float = 0.0
    trading_value: float = 0.0


class FakeDepth:
    best_bid_tick = 1000
    best_ask_tick = 1001
    best_bid = best_bid_tick * p.TICK_SIZE
    best_ask = best_ask_tick * p.TICK_SIZE

    def bid_qty_at_tick(self, tick: int) -> float:
        return 10.0 if 990 <= int(tick) <= self.best_bid_tick else 0.0

    def ask_qty_at_tick(self, tick: int) -> float:
        return 10.0 if self.best_ask_tick <= int(tick) <= 1010 else 0.0


class FakeBacktest:
    def __init__(self, *, position: float) -> None:
        self._depth = FakeDepth()
        self._orders: dict[int, FakeOrder] = {}
        self._state = FakeStateValues(position=float(position))
        self.current_timestamp = DAY_START_NS + 61_000_000_000
        self.events: list[tuple] = []
        self.cancel_calls = 0
        self.request_overlaps = 0
        self.forced_submit_calls = 0

    def depth(self, asset_no: int) -> FakeDepth:
        assert asset_no == d2.ASSET_NO
        return self._depth

    def orders(self, asset_no: int) -> dict[int, FakeOrder]:
        assert asset_no == d2.ASSET_NO
        return self._orders

    def position(self, asset_no: int) -> float:
        assert asset_no == d2.ASSET_NO
        return float(self._state.position)

    def state_values(self, asset_no: int) -> FakeStateValues:
        assert asset_no == d2.ASSET_NO
        return self._state

    def cancel(self, asset_no: int, order_id: int, wait: bool) -> int:
        assert asset_no == d2.ASSET_NO
        assert wait is False
        order = self._orders[int(order_id)]

        if order.req != d2.HFT_NONE:
            self.request_overlaps += 1
            return 10

        order.req = 99
        self.cancel_calls += 1
        self.events.append(("cancel_request", int(order_id)))
        return 0

    def acknowledge_cancel(self, order: FakeOrder) -> None:
        order.status = d2.HFT_CANCELED
        order.req = d2.HFT_NONE
        order.local_timestamp = int(self.current_timestamp)
        self.events.append(("cancel_response", int(order.order_id)))

    def apply_maker_execution(
        self,
        order: FakeOrder,
        *,
        qty: float,
        filled: bool,
    ) -> None:
        q = float(qty)
        assert q > 0.0
        assert q <= order.leaves_qty + 1e-12

        side_sign = 1.0 if order.side == 1 else -1.0
        price = float(order.price_tick) * p.TICK_SIZE
        quote = q * price

        self._state.position += side_sign * q
        self._state.balance -= side_sign * quote
        self._state.num_trades += 1
        self._state.trading_volume += q
        self._state.trading_value += quote

        order.leaves_qty -= q
        order.exec_qty = q
        order.exec_price_tick = int(order.price_tick)
        order.status = d2.HFT_FILLED if filled else d2.HFT_PARTIALLY_FILLED
        order.req = d2.HFT_NONE if filled else 99
        order.exch_timestamp = int(self.current_timestamp - 1)
        order.local_timestamp = int(self.current_timestamp)
        self.events.append(
            (
                "maker_execution_local_state",
                "bid" if order.side == 1 else "ask",
                q,
                float(self._state.position),
            )
        )

    def _submit_market(
        self,
        *,
        order_id: int,
        side: int,
        price: float,
        qty: float,
        order_type: int,
        wait: bool,
    ) -> int:
        assert order_type == FakeHft.MARKET
        assert wait is True
        q = float(qty)
        pre_submit_position = float(self._state.position)
        self.forced_submit_calls += 1
        self.events.append(
            (
                "forced_taker_submit",
                pre_submit_position,
                int(side),
                q,
                int(order_id),
            )
        )

        side_sign = 1.0 if int(side) == 1 else -1.0
        quote = q * float(price)
        self._state.position += side_sign * q
        self._state.balance -= side_sign * quote
        self._state.fee += quote * 0.002
        self._state.num_trades += 1
        self._state.trading_volume += q
        self._state.trading_value += quote

        tick = int(round(float(price) / p.TICK_SIZE))
        self._orders[int(order_id)] = FakeOrder(
            order_id=int(order_id),
            side=int(side),
            price_tick=tick,
            status=d2.HFT_FILLED,
            exec_price_tick=tick,
            exec_qty=q,
            leaves_qty=0.0,
            exch_timestamp=int(self.current_timestamp),
            local_timestamp=int(self.current_timestamp),
        )
        self.events.append(
            ("forced_taker_filled", float(self._state.position))
        )
        return 0

    def submit_sell_order(
        self,
        asset_no: int,
        order_id: int,
        price: float,
        qty: float,
        tif: int,
        order_type: int,
        wait: bool,
    ) -> int:
        assert asset_no == d2.ASSET_NO
        return self._submit_market(
            order_id=order_id,
            side=-1,
            price=price,
            qty=qty,
            order_type=order_type,
            wait=wait,
        )

    def submit_buy_order(
        self,
        asset_no: int,
        order_id: int,
        price: float,
        qty: float,
        tif: int,
        order_type: int,
        wait: bool,
    ) -> int:
        assert asset_no == d2.ASSET_NO
        return self._submit_market(
            order_id=order_id,
            side=1,
            price=price,
            qty=qty,
            order_type=order_type,
            wait=wait,
        )


class FlattenTraceMixin:
    def _bind_new_execution(self, *, slot, raw, local_response_ns: int) -> None:
        super()._bind_new_execution(
            slot=slot,
            raw=raw,
            local_response_ns=local_response_ns,
        )
        self.bt.events.append(
            (
                "maker_fill_bound",
                slot.side,
                self.bt.position(d2.ASSET_NO),
                self.inventory_clock.position,
            )
        )

    def _execute_unique_flatten(self, *, direction: int, qty: float) -> None:
        self.bt.events.append(
            (
                "execute_unique_flatten",
                self.bt.position(d2.ASSET_NO),
                int(direction),
                float(qty),
            )
        )
        return super()._execute_unique_flatten(
            direction=direction,
            qty=qty,
        )


class FrozenD6R19FlattenHarness(
    FlattenTraceMixin,
    d6r19.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel,
):
    pass


class D6R20FlattenHarness(
    FlattenTraceMixin,
    d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel,
):
    pass


def make_kernel(kernel_type, *, initial_position: float, working_side: str):
    bt = FakeBacktest(position=initial_position)
    kernel = kernel_type(
        bt=bt,
        h=FakeHft,
        policy_id="M02",
        day=DAY,
        scenario=SCENARIO,
        terminal_source_local_ns=DAY_START_NS + 100_000_000_000,
        direct_index=None,
    )
    kernel.inventory_clock = contract.InventoryClock(
        position=float(initial_position),
        nonzero_since_local_ns=bt.current_timestamp - 61_000_000_000,
    )
    kernel.first_nonzero_inventory_local_ns = (
        bt.current_timestamp - 61_000_000_000
    )

    order = FakeOrder(
        order_id=10_001 if working_side == "bid" else 10_002,
        side=1 if working_side == "bid" else -1,
        price_tick=1000 if working_side == "bid" else 1001,
    )
    bt._orders[order.order_id] = order
    slot = kernel._slot(working_side)
    slot.order_id = order.order_id
    slot.last_leaves_qty = p.BASE_ORDER_QTY

    # This is the real frozen policy-trigger and cancel-latch path.
    kernel._evaluate_policy_epoch(local_timestamp_ns=bt.current_timestamp)

    assert kernel.force_decision is not None
    assert kernel.force_decision.force_flatten is True
    assert kernel.force_decision.flatten_direction == (
        SHORT if initial_position > 0.0 else LONG
    )
    assert kernel.force_decision.flatten_qty == pytest.approx(
        abs(initial_position)
    )
    assert order.req != d2.HFT_NONE
    assert bt.cancel_calls == 1
    assert bt.forced_submit_calls == 0
    return kernel, bt, order


def process_maker_fill_and_clear(
    kernel,
    bt: FakeBacktest,
    order: FakeOrder,
    *,
    qty: float,
) -> None:
    bt.current_timestamp += 250_000_000
    bt.apply_maker_execution(order, qty=qty, filled=True)
    kernel._process_response_batch(local_response_ns=bt.current_timestamp)
    assert kernel._all_quote_slots_clear() is True
    assert bt.position(0) == pytest.approx(kernel.inventory_clock.position)


def taker_events(kernel):
    return [
        event
        for event in kernel.bound_fills
        if event.kind == binding.FILL and event.liquidity == binding.TAKER
    ]


def test_d6r19_exact_completed_flatten_nonflat_reproduction_and_d6r20_fix():
    old, old_bt, old_bid = make_kernel(
        FrozenD6R19FlattenHarness,
        initial_position=0.001,
        working_side="bid",
    )
    old_decision = old.force_decision
    process_maker_fill_and_clear(old, old_bt, old_bid, qty=0.001)

    assert old_decision is not None
    assert old_bt.position(0) == pytest.approx(0.002)
    assert old.inventory_clock.position == pytest.approx(0.002)

    with pytest.raises(
        base.RealHistoricalDriverError,
        match="completed_flatten_nonflat",
    ):
        old._maybe_execute_forced_flatten()

    assert old_bt.events[-3:] == [
        ("execute_unique_flatten", pytest.approx(0.002), SHORT, pytest.approx(0.001)),
        ("forced_taker_submit", pytest.approx(0.002), -1, pytest.approx(0.001), 4901),
        ("forced_taker_filled", pytest.approx(0.001)),
    ]
    assert old_bt.position(0) == pytest.approx(0.001)

    new, new_bt, new_bid = make_kernel(
        D6R20FlattenHarness,
        initial_position=0.001,
        working_side="bid",
    )
    process_maker_fill_and_clear(new, new_bt, new_bid, qty=0.001)

    assert new_bt.position(0) == pytest.approx(0.002)
    assert new.inventory_clock.position == pytest.approx(0.002)
    new._maybe_execute_forced_flatten()

    assert new_bt.events[-3:] == [
        ("execute_unique_flatten", pytest.approx(0.002), SHORT, pytest.approx(0.002)),
        ("forced_taker_submit", pytest.approx(0.002), -1, pytest.approx(0.002), 4901),
        ("forced_taker_filled", pytest.approx(0.0)),
    ]
    assert new_bt.position(0) == pytest.approx(0.0)
    assert new.inventory_clock.position == pytest.approx(0.0)
    assert len(taker_events(new)) == 1
    assert len(new.flatten_order_ids) == 1
    assert new.flatten_order_ids == [m4.FLATTEN_ORDER_ID]


def test_a_residual_increased_same_sign_uses_current_quantity():
    kernel, bt, bid = make_kernel(
        D6R20FlattenHarness,
        initial_position=0.001,
        working_side="bid",
    )
    process_maker_fill_and_clear(kernel, bt, bid, qty=0.001)
    kernel._maybe_execute_forced_flatten()

    submit = [event for event in bt.events if event[0] == "forced_taker_submit"]
    assert submit == [("forced_taker_submit", pytest.approx(0.002), -1, pytest.approx(0.002), 4901)]
    assert bt.position(0) == pytest.approx(0.0)


def test_b_residual_decreased_same_sign_uses_current_quantity():
    kernel, bt, ask = make_kernel(
        D6R20FlattenHarness,
        initial_position=0.002,
        working_side="ask",
    )
    process_maker_fill_and_clear(kernel, bt, ask, qty=0.001)
    kernel._maybe_execute_forced_flatten()

    submit = [event for event in bt.events if event[0] == "forced_taker_submit"]
    assert submit == [("forced_taker_submit", pytest.approx(0.001), -1, pytest.approx(0.001), 4901)]
    assert bt.position(0) == pytest.approx(0.0)


def test_c_residual_naturally_zero_submits_no_taker_and_invents_no_fill():
    kernel, bt, ask = make_kernel(
        D6R20FlattenHarness,
        initial_position=0.001,
        working_side="ask",
    )
    process_maker_fill_and_clear(kernel, bt, ask, qty=0.001)
    fills_before = tuple(kernel.bound_fills)
    kernel._maybe_execute_forced_flatten()

    assert bt.position(0) == pytest.approx(0.0)
    assert kernel.inventory_clock == contract.InventoryClock.flat()
    assert bt.forced_submit_calls == 0
    assert tuple(kernel.bound_fills) == fills_before
    assert taker_events(kernel) == []
    assert kernel.flatten_order_ids == []
    assert kernel.completed_forced_flattens == 1
    assert kernel.force_decision is None


def test_d_residual_sign_reversal_uses_current_sign_and_quantity():
    kernel, bt, ask = make_kernel(
        D6R20FlattenHarness,
        initial_position=0.0005,
        working_side="ask",
    )
    original = kernel.force_decision
    assert original is not None
    assert original.flatten_direction == SHORT
    assert original.flatten_qty == pytest.approx(0.0005)

    bt.current_timestamp += 250_000_000
    bt.apply_maker_execution(ask, qty=0.0005, filled=False)
    kernel._process_response_batch(local_response_ns=bt.current_timestamp)
    assert bt.position(0) == pytest.approx(0.0)
    assert kernel.inventory_clock == contract.InventoryClock.flat()
    kernel._maybe_execute_forced_flatten()
    assert bt.forced_submit_calls == 0

    bt.current_timestamp += 250_000_000
    bt.apply_maker_execution(ask, qty=0.0005, filled=True)
    kernel._process_response_batch(local_response_ns=bt.current_timestamp)
    assert bt.position(0) == pytest.approx(-0.0005)
    assert kernel.inventory_clock.position == pytest.approx(-0.0005)
    kernel._maybe_execute_forced_flatten()

    submit = [event for event in bt.events if event[0] == "forced_taker_submit"]
    assert submit == [("forced_taker_submit", pytest.approx(-0.0005), 1, pytest.approx(0.0005), 4901)]
    assert bt.position(0) == pytest.approx(0.0)
    assert kernel.inventory_clock == contract.InventoryClock.flat()


def test_e_unchanged_residual_matches_decision_direction_and_quantity():
    kernel, bt, bid = make_kernel(
        D6R20FlattenHarness,
        initial_position=0.001,
        working_side="bid",
    )
    decision = kernel.force_decision
    bt.current_timestamp += 250_000_000
    bt.acknowledge_cancel(bid)
    kernel._process_response_batch(local_response_ns=bt.current_timestamp)
    kernel._maybe_execute_forced_flatten()

    assert decision is not None
    submit = [event for event in bt.events if event[0] == "forced_taker_submit"]
    assert submit[0][2] == decision.flatten_direction == SHORT
    assert submit[0][3] == pytest.approx(decision.flatten_qty)
    assert submit[0][3] == pytest.approx(0.001)
    assert bt.position(0) == pytest.approx(0.0)


def test_f_and_g_quote_clearance_required_without_cancel_request_overlap():
    kernel, bt, bid = make_kernel(
        D6R20FlattenHarness,
        initial_position=0.001,
        working_side="bid",
    )
    decision = kernel.force_decision
    assert decision is not None

    kernel._maybe_execute_forced_flatten()
    kernel._force_cancel_quotes(decision)
    kernel._maybe_execute_forced_flatten()

    assert kernel.bid.order_id == bid.order_id
    assert bt.cancel_calls == 1
    assert bt.request_overlaps == 0
    assert bt.forced_submit_calls == 0


@pytest.mark.parametrize(
    ("initial_position", "side", "maker_qty", "expected_pre", "expected_side"),
    (
        (0.001, "bid", 0.001, 0.002, -1),
        (0.002, "ask", 0.001, 0.001, -1),
    ),
)
def test_h_and_i_exactly_one_taker_uses_unique_path_and_frozen_accounting(
    initial_position,
    side,
    maker_qty,
    expected_pre,
    expected_side,
):
    kernel, bt, order = make_kernel(
        D6R20FlattenHarness,
        initial_position=initial_position,
        working_side=side,
    )
    process_maker_fill_and_clear(kernel, bt, order, qty=maker_qty)
    kernel._maybe_execute_forced_flatten()
    kernel._maybe_execute_forced_flatten()

    assert bt.forced_submit_calls == 1
    assert len(kernel.flatten_order_ids) == 1
    assert kernel.next_flatten_order_id == m4.FLATTEN_ORDER_ID + 1
    submit = [event for event in bt.events if event[0] == "forced_taker_submit"]
    assert submit[0][1] == pytest.approx(expected_pre)
    assert submit[0][2] == expected_side
    assert submit[0][3] == pytest.approx(abs(expected_pre))

    takers = taker_events(kernel)
    assert len(takers) == 1
    assert takers[0].fill is not None
    assert takers[0].fill.liquidity == binding.TAKER
    assert takers[0].fill.qty == pytest.approx(abs(expected_pre))
    assert bt.position(0) == pytest.approx(0.0)
    assert kernel.inventory_clock.position == pytest.approx(0.0)


def test_nonfinite_execution_time_residual_fails_closed_without_submit():
    kernel, bt, bid = make_kernel(
        D6R20FlattenHarness,
        initial_position=0.001,
        working_side="bid",
    )
    bt.current_timestamp += 250_000_000
    bt.acknowledge_cancel(bid)
    kernel._process_response_batch(local_response_ns=bt.current_timestamp)
    bt._state.position = float("nan")

    with pytest.raises(
        base.RealHistoricalDriverError,
        match="force_flatten_residual_position_nonfinite",
    ):
        kernel._maybe_execute_forced_flatten()

    assert bt.forced_submit_calls == 0


def test_j_d6r19_response_batch_fix_is_inherited_unchanged():
    assert issubclass(
        d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel,
        d6r19.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel,
    )
    assert (
        d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel._process_response_batch
        is d6r19.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel._process_response_batch
    )


def test_k_terminal_shutdown_method_is_not_overridden():
    assert (
        d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel._advance_terminal_shutdown
        is base.ContinuousHistoricalPolicyKernel._advance_terminal_shutdown
    )
    text = Path(d6r20.__file__).read_text(encoding="utf-8")
    assert "def _advance_terminal_shutdown" not in text


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    payload = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(payload).hexdigest()


def test_frozen_lineage_blobs_are_exact():
    root = Path(__file__).resolve().parents[1]
    expected = {
        "src/multimarket/dev045_d6r19_response_batch_replacement_driver.py": (
            "5aaf880795f796d5086b3b86a6e7dde0fd7f56ed"
        ),
        "src/multimarket/dev045_d6r19_canonical_runner.py": (
            "9b714066955ddbd637c4d3dd5f94eccbd257cb2c"
        ),
        "src/multimarket/dev045_d6r18_canonical_runner.py": (
            "f8d81680ef75a3095f57bada6e01664391e69b72"
        ),
        "src/multimarket/dev045_d6r18_fresh_replacement_driver.py": (
            "adc432f36814a1ccf1b2dd63219f5826c604753e"
        ),
        "src/multimarket/dev045_m6_event_loop_kernel.py": (
            "93a865b5a7a81da139b60fe220f5106f98832c7e"
        ),
        "src/multimarket/dev045_m4_adapter.py": (
            "7f6a321b4512dd1ec1edf94c79416e176ee75e1c"
        ),
        "src/multimarket/dev045_m3_policy.py": (
            "256644726f8478d2b76105bce97e5f2c536cabf6"
        ),
        "src/multimarket/dev045_m6_economic_arena.py": (
            "75e2ebe55d830202d3dfeb41382783c2fc670bc8"
        ),
        "src/multimarket/dev045_d6r17_real_historical_economic_driver.py": (
            "06383d2f6c0bb0b2ba4fc7b44cf82d219094f0ab"
        ),
    }
    assert {path: git_blob(root / path) for path in expected} == expected


def test_d6r20_execution_surfaces_are_closed_and_no_canonical_runner_exists():
    assert d6r20.EXPERIMENT_ID == "DEV045-D6R20"
    assert d6r20.CANONICAL_RUNNER_IMPLEMENTED is False
    assert d6r20.CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert d6r20.CANONICAL_ATTEMPT_CONSUMED is False
    assert d6r20.AUTOMATIC_RETRY is False
    assert d6r20.CANONICAL_PNL_WRITE_ENABLED is False
    assert d6r20.NETWORK_ACQUISITION_ENABLED is False
    assert d6r20.RAILWAY_ENABLED is False
    assert d6r20.LIVE_TRADING_AUTHORIZED is False
    assert not Path(
        "src/multimarket/dev045_d6r20_canonical_runner.py"
    ).exists()

    text = Path(d6r20.__file__).read_text(encoding="utf-8")
    assert "self.bt.position" in text
    assert "decision.flatten_direction" not in text
    assert "decision.flatten_qty" not in text
    assert "submit_forced_flatten" not in text
    assert "bind_forced_flatten_from_state_delta" not in text
    assert "while " not in text
    assert "run_full_day(" not in text

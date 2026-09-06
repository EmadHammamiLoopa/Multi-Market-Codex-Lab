from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

import pytest

from multimarket import dev045_d6r17_direct_action_driver_bridge as frozen
from multimarket import dev045_d6r17_direct_action_support as direct
from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r18_fresh_replacement_driver as d
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m6_event_loop_kernel as d2
from multimarket import dev045_m6_policy_integration as d3


SCENARIO = "Q0_PRIMARY_250_250"
DAY = "2026-01-01"


class FakeHft:
    GTC = 0
    LIMIT = 0


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
    exch_timestamp: int = 0
    local_timestamp: int = 0


class FakeDepth:
    def __init__(self) -> None:
        self.set_book(1000, 1001)

    def set_book(self, best_bid_tick: int, best_ask_tick: int) -> None:
        assert best_bid_tick < best_ask_tick

        self.best_bid_tick = int(best_bid_tick)
        self.best_ask_tick = int(best_ask_tick)
        self.best_bid = self.best_bid_tick * p.TICK_SIZE
        self.best_ask = self.best_ask_tick * p.TICK_SIZE

        self.bid_qty = {
            tick: 10.0
            for tick in range(self.best_bid_tick - 4, self.best_bid_tick + 1)
        }
        self.ask_qty = {
            tick: 10.0
            for tick in range(self.best_ask_tick, self.best_ask_tick + 5)
        }

    def bid_qty_at_tick(self, tick: int) -> float:
        return float(self.bid_qty.get(int(tick), 0.0))

    def ask_qty_at_tick(self, tick: int) -> float:
        return float(self.ask_qty.get(int(tick), 0.0))


class FakeBacktest:
    def __init__(self) -> None:
        self._depth = FakeDepth()
        self._orders: dict[int, FakeOrder] = {}
        self._position = 0.0
        self.current_timestamp = 1_000_000_000
        self.events: list[tuple] = []
        self.request_overlaps = 0
        self.duplicate_working_sides = 0

    def depth(self, asset_no: int) -> FakeDepth:
        assert asset_no == d2.ASSET_NO
        return self._depth

    def orders(self, asset_no: int) -> dict[int, FakeOrder]:
        assert asset_no == d2.ASSET_NO
        return self._orders

    def position(self, asset_no: int) -> float:
        assert asset_no == d2.ASSET_NO
        return self._position

    def set_book(self, best_bid_tick: int, best_ask_tick: int) -> None:
        self._depth.set_book(best_bid_tick, best_ask_tick)

    def cancel(self, asset_no: int, order_id: int, wait: bool) -> int:
        assert asset_no == d2.ASSET_NO
        assert wait is False

        order = self._orders[int(order_id)]

        if order.req != d2.HFT_NONE:
            self.request_overlaps += 1
            return 10

        order.req = 99
        self.events.append(("cancel_request", int(order_id)))
        return 0

    def acknowledge_cancel(self, order_id: int) -> None:
        order = self._orders[int(order_id)]
        order.status = d2.HFT_CANCELED
        order.req = d2.HFT_NONE
        order.local_timestamp = int(self.current_timestamp)
        self.events.append(("cancel_response", int(order_id)))

    def _submit(self, order_id: int, side: int, price: float, qty: float) -> int:
        price_tick = int(round(float(price) / p.TICK_SIZE))

        active_same_side = [
            order
            for order in self._orders.values()
            if order.side == side
            and order.status in (d2.HFT_NEW, d2.HFT_PARTIALLY_FILLED)
        ]

        if active_same_side:
            self.duplicate_working_sides += 1
            return 10

        self._orders[int(order_id)] = FakeOrder(
            order_id=int(order_id),
            side=int(side),
            price_tick=price_tick,
            leaves_qty=float(qty),
            local_timestamp=int(self.current_timestamp),
        )
        self.events.append(("submit", int(side), int(order_id), price_tick))
        return 0

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
        assert wait is False
        return self._submit(order_id, 1, price, qty)

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
        assert wait is False
        return self._submit(order_id, -1, price, qty)


class TracingFreshKernel(d.FreshReplacementContinuousHistoricalPolicyKernel):
    def _fresh_policy_decision(
        self,
        *,
        local_timestamp_ns: int,
    ) -> p.PolicyDecision:
        self.bt.events.append(("fresh_policy", int(local_timestamp_ns)))
        return super()._fresh_policy_decision(
            local_timestamp_ns=local_timestamp_ns
        )


def make_fresh_kernel(
    *,
    policy_id: str = "M01",
    day: str = DAY,
    direct_index: direct.DirectActionIndex | None = None,
) -> tuple[TracingFreshKernel, FakeBacktest]:
    bt = FakeBacktest()
    kernel = TracingFreshKernel(
        bt=bt,
        h=FakeHft,
        policy_id=policy_id,
        day=day,
        scenario=SCENARIO,
        terminal_source_local_ns=10_000_000_000,
        direct_index=direct_index,
    )
    return kernel, bt


def make_frozen_kernel() -> tuple[
    frozen.DirectActionContinuousHistoricalPolicyKernel,
    FakeBacktest,
]:
    bt = FakeBacktest()
    kernel = frozen.DirectActionContinuousHistoricalPolicyKernel(
        bt=bt,
        h=FakeHft,
        policy_id="M01",
        day=DAY,
        scenario=SCENARIO,
        terminal_source_local_ns=10_000_000_000,
        direct_index=None,
    )
    return kernel, bt


def state_decision(kernel, local_timestamp_ns: int | None = None):
    now = (
        int(kernel.bt.current_timestamp)
        if local_timestamp_ns is None
        else int(local_timestamp_ns)
    )
    state = kernel._dynamic_market_state(local_timestamp_ns=now)
    return p.policy_decision(kernel.policy_id, state)


def seed_working(kernel, *, side: str, tick: int, order_id: int = 10_001):
    numeric_side = 1 if side == "bid" else -1
    order = FakeOrder(
        order_id=order_id,
        side=numeric_side,
        price_tick=int(tick),
    )
    kernel.bt._orders[order_id] = order

    slot = kernel._slot(side)
    slot.order_id = order_id
    slot.last_leaves_qty = p.BASE_ORDER_QTY
    return order


def replacement_cycle(
    kernel,
    bt: FakeBacktest,
    *,
    side: str,
    working_tick: int,
    response_book: tuple[int, int],
) -> tuple[p.PolicyDecision, FakeOrder]:
    order = seed_working(kernel, side=side, tick=working_tick)
    old_decision = state_decision(kernel)

    kernel._maintain_side(side=side, decision=old_decision)
    assert order.req != d2.HFT_NONE

    bt.set_book(*response_book)
    bt.current_timestamp += 250_000_000
    bt.acknowledge_cancel(order.order_id)
    return old_decision, order


def assert_slot_passive(kernel, side: str) -> None:
    slot = kernel._slot(side)
    assert slot.order_id is not None

    order = kernel.bt.orders(d2.ASSET_NO)[slot.order_id]
    depth = kernel.bt.depth(d2.ASSET_NO)

    m4.validate_passive_target(
        side=side,
        target_tick=order.price_tick,
        best_bid_tick=depth.best_bid_tick,
        best_ask_tick=depth.best_ask_tick,
    )


def test_execution_surfaces_and_attempt_stay_closed():
    assert d.EXPERIMENT_ID == "DEV045-D6R18"
    assert d.CANONICAL_SOURCE_OPEN_IMPLEMENTED is False
    assert d.CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert d.CANONICAL_ATTEMPT_CONSUMED is False
    assert d.AUTOMATIC_RETRY is False
    assert d.CANONICAL_PNL_WRITE_ENABLED is False
    assert d.NETWORK_ACQUISITION_ENABLED is False
    assert d.RAILWAY_ENABLED is False
    assert d.LIVE_TRADING_AUTHORIZED is False
    assert d.AUG_OPEN_AUTHORIZED is False
    assert d.SEP_PLUS_OPEN_AUTHORIZED is False
    assert d.NON_BTC_OPEN_AUTHORIZED is False


def test_stale_ask_defect_reproduced_in_frozen_d6r17():
    kernel, bt = make_frozen_kernel()
    old_decision, order = replacement_cycle(
        kernel,
        bt,
        side="ask",
        working_tick=1002,
        response_book=(1001, 1002),
    )

    assert old_decision.ask_target_tick == 1001
    assert old_decision.ask_target_tick <= bt.depth(0).best_bid_tick
    assert kernel.ask.pending_replacement is old_decision

    with pytest.raises(m4.M4AdapterError, match="ask_not_passive"):
        kernel._process_response_batch(
            local_response_ns=bt.current_timestamp
        )

    assert order.status == d2.HFT_CANCELED


def test_a_stale_ask_is_recomputed_from_current_book():
    kernel, bt = make_fresh_kernel()
    old_decision, order = replacement_cycle(
        kernel,
        bt,
        side="ask",
        working_tick=1002,
        response_book=(1001, 1002),
    )

    assert old_decision.ask_target_tick == 1001
    assert old_decision.ask_target_tick <= bt.depth(0).best_bid_tick
    assert kernel.ask.replacement_required is True
    assert kernel.ask.pending_replacement is None
    assert "pending_replacement" not in vars(kernel.ask)

    with pytest.raises(
        d.FreshReplacementError,
        match="stale_pending_replacement_forbidden",
    ):
        kernel.ask.pending_replacement = old_decision

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    assert order.status == d2.HFT_CANCELED
    assert kernel.fresh_replacement_evaluations == 1
    assert_slot_passive(kernel, "ask")

    replacement = bt.orders(0)[kernel.ask.order_id]
    assert replacement.price_tick == 1002
    assert replacement.price_tick != old_decision.ask_target_tick


def test_b_stale_bid_is_recomputed_from_current_book():
    kernel, bt = make_fresh_kernel()
    old_decision, _ = replacement_cycle(
        kernel,
        bt,
        side="bid",
        working_tick=999,
        response_book=(999, 1000),
    )

    assert old_decision.bid_target_tick == 1000
    assert old_decision.bid_target_tick >= bt.depth(0).best_ask_tick

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    assert kernel.fresh_replacement_evaluations == 1
    assert_slot_passive(kernel, "bid")

    replacement = bt.orders(0)[kernel.bid.order_id]
    assert replacement.price_tick == 999
    assert replacement.price_tick != old_decision.bid_target_tick


def test_c_cancel_response_precedes_fresh_calculation_and_submit():
    kernel, bt = make_fresh_kernel()
    replacement_cycle(
        kernel,
        bt,
        side="ask",
        working_tick=1002,
        response_book=(1001, 1002),
    )

    assert [event[0] for event in bt.events] == [
        "cancel_request",
        "cancel_response",
    ]

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    assert [event[0] for event in bt.events] == [
        "cancel_request",
        "cancel_response",
        "fresh_policy",
        "submit",
    ]


@pytest.mark.parametrize("blocker", ("shutdown", "forced_flatten"))
def test_d_shutdown_or_forced_flatten_blocks_pending_replacement(blocker):
    kernel, bt = make_fresh_kernel()
    _, order = replacement_cycle(
        kernel,
        bt,
        side="ask",
        working_tick=1002,
        response_book=(1001, 1002),
    )

    if blocker == "shutdown":
        kernel.terminal_shutdown_started = True
    else:
        kernel.force_decision = p.PolicyDecision(
            policy_id="M01",
            bid_target_tick=None,
            ask_target_tick=None,
            bid_size=0.0,
            ask_size=0.0,
            bid_enabled=False,
            ask_enabled=False,
            reference_shift_ticks=0,
            force_flatten=True,
            flatten_direction=-1,
            flatten_qty=p.BASE_ORDER_QTY,
        )

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    assert order.status == d2.HFT_CANCELED
    assert kernel.ask.order_id is None
    assert kernel.ask.replacement_required is False
    assert kernel.fresh_replacement_evaluations == 0
    assert [event[0] for event in bt.events].count("submit") == 0


def test_e_unchanged_book_matches_frozen_intended_target():
    kernel, bt = make_fresh_kernel()
    old_decision = state_decision(kernel)
    order = seed_working(kernel, side="ask", tick=1002)

    kernel._maintain_side(side="ask", decision=old_decision)
    bt.current_timestamp += 250_000_000
    bt.acknowledge_cancel(order.order_id)
    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    replacement = bt.orders(0)[kernel.ask.order_id]
    assert replacement.price_tick == old_decision.ask_target_tick
    assert replacement.leaves_qty == pytest.approx(old_decision.ask_size)
    assert_slot_passive(kernel, "ask")


def test_f_fresh_policy_can_disable_replacement_without_submit():
    kernel, bt = make_fresh_kernel(policy_id="M05")
    old_decision = state_decision(kernel)
    order = seed_working(kernel, side="ask", tick=1002)

    assert old_decision.ask_enabled is True
    kernel._maintain_side(side="ask", decision=old_decision)

    bt.current_timestamp += 250_000_000
    kernel.flow.add(
        local_timestamp_ns=bt.current_timestamp,
        side=1,
        qty=1.0,
    )
    bt.acknowledge_cancel(order.order_id)
    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    assert kernel.fresh_replacement_evaluations == 1
    assert kernel.ask.order_id is None
    assert [event[0] for event in bt.events].count("submit") == 0


def test_f_repeated_moving_cancel_replace_stress_and_terminal_clear():
    kernel, bt = make_fresh_kernel()
    seed_working(kernel, side="bid", tick=999, order_id=10_001)
    seed_working(kernel, side="ask", tick=1003, order_id=10_002)

    current_bid = 1000
    current_ask = 1001

    for cycle, direction in enumerate((1, 1, -1, -1, 1, -1), start=1):
        maintenance_book = (
            current_bid + direction,
            current_ask + direction,
        )
        bt.set_book(*maintenance_book)
        bt.current_timestamp += 1_000_000_000

        decision = state_decision(kernel)
        before_cancels = kernel.cancel_requests

        kernel._maintain_side(side="bid", decision=decision)
        kernel._maintain_side(side="ask", decision=decision)

        assert kernel.cancel_requests == before_cancels + 2

        # Re-maintenance during the cancel flight cannot overlap requests.
        kernel._maintain_side(side="bid", decision=decision)
        kernel._maintain_side(side="ask", decision=decision)
        assert kernel.cancel_requests == before_cancels + 2

        bid_oid = kernel.bid.order_id
        ask_oid = kernel.ask.order_id
        assert bid_oid is not None
        assert ask_oid is not None

        response_book = (
            maintenance_book[0] + direction,
            maintenance_book[1] + direction,
        )
        bt.set_book(*response_book)
        bt.current_timestamp += 250_000_000
        bt.acknowledge_cancel(bid_oid)
        bt.acknowledge_cancel(ask_oid)

        submits_before = kernel.submit_requests
        kernel._process_response_batch(local_response_ns=bt.current_timestamp)

        assert kernel.submit_requests == submits_before + 2
        assert_slot_passive(kernel, "bid")
        assert_slot_passive(kernel, "ask")
        assert kernel.bid.order_id != kernel.ask.order_id
        assert kernel.bid.replacement_required is False
        assert kernel.ask.replacement_required is False
        assert bt.request_overlaps == 0
        assert bt.duplicate_working_sides == 0
        assert bt.position(0) == pytest.approx(0.0)
        assert kernel.inventory_clock.position == pytest.approx(0.0)
        assert kernel.bound_fills == []

        current_bid, current_ask = response_book

    bt.current_timestamp = kernel.terminal_shutdown_cutoff_ns
    kernel._begin_terminal_shutdown(local_timestamp_ns=bt.current_timestamp)

    assert kernel.terminal_shutdown_started is True
    assert kernel.bid.replacement_required is False
    assert kernel.ask.replacement_required is False

    terminal_bid_oid = kernel.bid.order_id
    terminal_ask_oid = kernel.ask.order_id
    assert terminal_bid_oid is not None
    assert terminal_ask_oid is not None

    bt.acknowledge_cancel(terminal_bid_oid)
    bt.acknowledge_cancel(terminal_ask_oid)
    kernel._process_response_batch(local_response_ns=bt.current_timestamp)
    kernel._advance_terminal_shutdown()

    assert kernel.terminal_shutdown_quiescent is True
    assert kernel.bid.order_id is None
    assert kernel.ask.order_id is None
    assert kernel._all_quote_slots_clear() is True
    assert bt.position(0) == pytest.approx(0.0)
    assert bt.request_overlaps == 0
    assert bt.duplicate_working_sides == 0


def test_response_refresh_preserves_direct_action_state_without_support_query():
    day = "2026-04-01"
    idx = direct.DirectActionIndex(
        day=day,
        policy_id="M06",
        points=(),
    )
    kernel, bt = make_fresh_kernel(
        policy_id="M06",
        day=day,
        direct_index=idx,
    )
    kernel.active_adapter_direction = 1
    bt.current_timestamp = d3.day_start_ns(day) + 61_250_000_000

    decision = kernel._fresh_policy_decision(
        local_timestamp_ns=bt.current_timestamp
    )

    assert decision.policy_id == "M06"
    assert decision.ask_target_tick == bt.depth(0).best_ask_tick + 1
    assert kernel.active_adapter_direction == 1
    assert kernel.direct_action_queries == 0
    assert kernel.adapter_candidate_epochs == 0
    assert kernel.a0_index is None
    assert kernel.legacy_index is None


def test_same_timestamp_response_precedes_exact_minute_support_update():
    day = "2026-04-01"
    minute_us = d3.day_start_ns(day) // 1_000 + 60_000_000
    idx = direct.DirectActionIndex(
        day=day,
        policy_id="M06",
        points=(
            direct.DirectActionPoint(
                timestamp_us=minute_us,
                direction=-1,
                ready=True,
            ),
        ),
    )
    kernel, bt = make_fresh_kernel(
        policy_id="M06",
        day=day,
        direct_index=idx,
    )
    kernel.active_adapter_direction = 1
    bt.current_timestamp = minute_us * 1_000

    response_decision = kernel._fresh_policy_decision(
        local_timestamp_ns=bt.current_timestamp
    )

    # A response is processed before the frozen policy timer at an equal
    # timestamp.  It sees the previously resolved direction and invents no
    # early support query.
    assert response_decision.ask_target_tick == bt.depth(0).best_ask_tick + 1
    assert kernel.active_adapter_direction == 1
    assert kernel.direct_action_queries == 0

    kernel._evaluate_policy_epoch(local_timestamp_ns=bt.current_timestamp)

    assert kernel.active_adapter_direction == -1
    assert kernel.direct_action_queries == 1
    assert kernel.direct_action_rows_found == 1
    assert kernel.direct_action_missing_rows == 0


def test_synthetic_hft_integration_reaches_terminal_clear(tmp_path):
    np = pytest.importorskip("numpy")
    pytest.importorskip("hftbacktest")

    first = d3._policy_fixture(DAY)
    second = first.copy()
    second["exch_ts"] += 80_000_000_000
    second["local_ts"] += 80_000_000_000
    data = np.concatenate((first, second))

    path = tmp_path / "synthetic_d6r18_two_cycle.npy"
    np.save(path, data, allow_pickle=False)

    source = adapter._open_verified_file(
        path,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        expected_bytes=int(path.stat().st_size),
        expected_rows=len(data),
    )

    try:
        result = d.run_bound_verified_replay(
            source,
            policy_id="M02",
            day=DAY,
            scenario=SCENARIO,
            direct_index=None,
            initial_snapshot=d3._policy_initial_snapshot(),
        )

        replay = result.replay
        assert replay.natural_end_of_data is True
        assert replay.terminal_flat is True
        assert replay.terminal_position == pytest.approx(0.0)
        assert replay.terminal_working_quote_slots == 0
        assert replay.terminal_shutdown_started is True
        assert replay.terminal_shutdown_quiescent is True
        assert replay.audit.execution_integrity_failures == 0
        assert replay.forced_flatten_count >= 2
        assert source._closed is False
    finally:
        source.close()

    assert source._closed is True


def test_successor_has_no_canonical_source_opener_or_quote_clipping():
    text = Path(d.__file__).read_text(encoding="utf-8")

    for token in (
        "_open_verified_file(",
        "open_verified_day_source(",
        "np.load(",
        "numpy.load(",
        "requests.",
        "urllib.",
        "httpx.",
    ):
        assert token not in text

    assert "slot.pending_replacement = replacement" not in text
    assert "pending_replacement: p.PolicyDecision" not in text
    assert "replacement_required" in text
    assert "validate_passive_target" not in text

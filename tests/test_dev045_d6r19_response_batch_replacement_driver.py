from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path

import pytest

from multimarket import dev045_d6r17_direct_action_support as direct
from multimarket import dev045_d6r18_fresh_replacement_driver as d6r18
from multimarket import dev045_d6r19_response_batch_replacement_driver as d6r19
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m6_event_loop_contract as contract
from multimarket import dev045_m6_event_loop_kernel as d2
from multimarket import dev045_m6_policy_integration as integration


DAY = "2026-01-01"
SCENARIO = "Q0_PRIMARY_250_250"


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
        self.best_bid_tick = 1000
        self.best_ask_tick = 1001
        self.best_bid = self.best_bid_tick * p.TICK_SIZE
        self.best_ask = self.best_ask_tick * p.TICK_SIZE

    def bid_qty_at_tick(self, tick: int) -> float:
        return 10.0 if 990 <= int(tick) <= self.best_bid_tick else 0.0

    def ask_qty_at_tick(self, tick: int) -> float:
        return 10.0 if self.best_ask_tick <= int(tick) <= 1010 else 0.0


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
        return float(self._position)

    def cancel(self, asset_no: int, order_id: int, wait: bool) -> int:
        assert asset_no == d2.ASSET_NO
        assert wait is False
        order = self._orders[int(order_id)]

        if order.req != d2.HFT_NONE:
            self.request_overlaps += 1
            return 10

        order.req = 99
        self.events.append(("cancel_request", order.side, int(order_id)))
        return 0

    def acknowledge_cancel(self, order_id: int) -> None:
        order = self._orders[int(order_id)]
        order.status = d2.HFT_CANCELED
        order.req = d2.HFT_NONE
        order.local_timestamp = int(self.current_timestamp)
        self.events.append(("cancel_response", order.side, int(order_id)))

    def _submit(self, order_id: int, side: int, price: float, qty: float) -> int:
        active_same_side = [
            order
            for order in self._orders.values()
            if int(order.side) == int(side)
            and int(order.status) in (
                int(d2.HFT_NEW),
                int(d2.HFT_PARTIALLY_FILLED),
            )
        ]

        if active_same_side:
            self.duplicate_working_sides += 1
            return 10

        tick = int(round(float(price) / p.TICK_SIZE))
        self._orders[int(order_id)] = FakeOrder(
            order_id=int(order_id),
            side=int(side),
            price_tick=tick,
            leaves_qty=float(qty),
            local_timestamp=int(self.current_timestamp),
        )
        side_name = "bid" if int(side) == 1 else "ask"
        self.events.append(("submit", side_name, int(order_id), tick))
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


class ResponseBatchHarnessMixin:
    """Trace batch ordering while preserving InventoryClock transitions."""

    _response_refresh_side: str | None = None

    def _bind_new_execution(self, *, slot, raw, local_response_ns: int) -> None:
        leaves = float(raw.leaves_qty)
        delta = float(slot.last_leaves_qty) - leaves

        if delta <= 1e-15:
            slot.last_leaves_qty = leaves
            return

        self.bt.events.append(("bind_fill", slot.side, delta))
        self.bound_fills.append((slot.side, delta))
        slot.last_leaves_qty = leaves

        # The fake reproduces the frozen causal operation: the clock observes
        # the local position only when the execution response is bound.
        self.inventory_clock = self.inventory_clock.observe_local_position(
            new_position=self.bt.position(d2.ASSET_NO),
            local_response_timestamp_ns=local_response_ns,
        )
        self.maker_local_response_ns = int(local_response_ns)
        self.bt.events.append(
            ("inventory_sync", float(self.inventory_clock.position))
        )

    def _handle_fresh_replacement(self, *, side: str, local_response_ns: int):
        self._response_refresh_side = side
        try:
            return super()._handle_fresh_replacement(
                side=side,
                local_response_ns=local_response_ns,
            )
        finally:
            self._response_refresh_side = None

    def _fresh_policy_decision(self, *, local_timestamp_ns: int):
        coherent = math.isclose(
            self.bt.position(d2.ASSET_NO),
            self.inventory_clock.position,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        self.bt.events.append(
            (
                "fresh_policy",
                self._response_refresh_side,
                coherent,
                self.bid.order_id,
                self.ask.order_id,
            )
        )
        decision = super()._fresh_policy_decision(
            local_timestamp_ns=local_timestamp_ns
        )
        self.last_fresh_decision = decision
        return decision

    def _maybe_execute_forced_flatten(self) -> None:
        # Isolate the ordering contract; inherited force selection and quote
        # cancellation still run, while no synthetic taker fill is invented.
        self.bt.events.append(("forced_flatten_ready",))


class FrozenD6R18Harness(
    ResponseBatchHarnessMixin,
    d6r18.FreshReplacementContinuousHistoricalPolicyKernel,
):
    pass


class D6R19Harness(
    ResponseBatchHarnessMixin,
    d6r19.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel,
):
    pass


def make_kernel(
    kernel_type=D6R19Harness,
    *,
    policy_id: str = "M01",
    day: str = DAY,
    direct_index: direct.DirectActionIndex | None = None,
):
    bt = FakeBacktest()
    kernel = kernel_type(
        bt=bt,
        h=FakeHft,
        policy_id=policy_id,
        day=day,
        scenario=SCENARIO,
        terminal_source_local_ns=100_000_000_000,
        direct_index=direct_index,
    )
    return kernel, bt


def seed_working(kernel, *, side: str, order_id: int, tick: int) -> FakeOrder:
    order = FakeOrder(
        order_id=int(order_id),
        side=1 if side == "bid" else -1,
        price_tick=int(tick),
    )
    kernel.bt._orders[order.order_id] = order
    slot = kernel._slot(side)
    slot.order_id = order.order_id
    slot.last_leaves_qty = p.BASE_ORDER_QTY
    return order


def current_decision(kernel) -> p.PolicyDecision:
    state = kernel._dynamic_market_state(
        local_timestamp_ns=kernel.bt.current_timestamp
    )
    return p.policy_decision(kernel.policy_id, state)


def request_replacement(kernel, *, side: str) -> FakeOrder:
    tick = 999 if side == "bid" else 1002
    order_id = 10_001 if side == "bid" else 10_002
    order = seed_working(kernel, side=side, order_id=order_id, tick=tick)
    kernel._request_cancel(
        slot=kernel._slot(side),
        replacement=current_decision(kernel),
    )
    return order


def mark_execution(
    bt: FakeBacktest,
    order: FakeOrder,
    *,
    status: int,
    leaves_qty: float,
) -> None:
    order.status = int(status)
    order.req = int(d2.HFT_NONE)
    order.leaves_qty = float(leaves_qty)
    order.exec_qty = p.BASE_ORDER_QTY - float(leaves_qty)
    order.exec_price_tick = int(order.price_tick)
    order.exch_timestamp = int(bt.current_timestamp - 1)
    order.local_timestamp = int(bt.current_timestamp)


def relevant_order(events: list[tuple]) -> list[tuple]:
    return [
        event
        for event in events
        if event[0] in (
            "bind_fill",
            "inventory_sync",
            "fresh_policy",
            "submit",
        )
    ]


def test_d6r18_exact_inventory_clock_mismatch_reproduction_and_d6r19_fix():
    old, old_bt = make_kernel(FrozenD6R18Harness)
    old_bid = request_replacement(old, side="bid")
    old_ask = seed_working(old, side="ask", order_id=10_002, tick=1001)
    old_bt.current_timestamp += 250_000_000
    old_bt.acknowledge_cancel(old_bid.order_id)
    old_bt._position = -p.BASE_ORDER_QTY
    mark_execution(old_bt, old_ask, status=d2.HFT_FILLED, leaves_qty=0.0)

    assert old.inventory_clock.position == pytest.approx(0.0)
    assert old_bt.position(0) == pytest.approx(-p.BASE_ORDER_QTY)

    with pytest.raises(
        d2.EventLoopKernelError,
        match="local_inventory_clock_mismatch",
    ):
        old._process_response_batch(local_response_ns=old_bt.current_timestamp)

    # Frozen D6R18 reaches the BID refresh while incoherent and never gets to
    # the ASK execution that would have synchronized the inventory clock.
    assert relevant_order(old_bt.events) == [
        ("fresh_policy", "bid", False, None, old_ask.order_id),
    ]
    assert old.bound_fills == []

    new, new_bt = make_kernel(D6R19Harness)
    new_bid = request_replacement(new, side="bid")
    new_ask = seed_working(new, side="ask", order_id=10_002, tick=1001)
    new_bt.current_timestamp += 250_000_000
    new_bt.acknowledge_cancel(new_bid.order_id)
    new_bt._position = -p.BASE_ORDER_QTY
    mark_execution(new_bt, new_ask, status=d2.HFT_FILLED, leaves_qty=0.0)

    new._process_response_batch(local_response_ns=new_bt.current_timestamp)

    events = relevant_order(new_bt.events)
    assert [event[0] for event in events] == [
        "bind_fill",
        "inventory_sync",
        "fresh_policy",
        "submit",
    ]
    assert events[0][1] == "ask"
    assert events[1][1] == pytest.approx(-p.BASE_ORDER_QTY)
    assert events[2][1:3] == ("bid", True)
    assert new_bt.position(0) == pytest.approx(new.inventory_clock.position)
    assert new.fresh_replacement_evaluations == 1


def test_a_symmetric_ask_replacement_waits_for_bid_fill_binding():
    kernel, bt = make_kernel()
    bid = seed_working(kernel, side="bid", order_id=10_001, tick=1000)
    ask = request_replacement(kernel, side="ask")
    bt.current_timestamp += 250_000_000
    bt._position = p.BASE_ORDER_QTY
    mark_execution(bt, bid, status=d2.HFT_FILLED, leaves_qty=0.0)
    bt.acknowledge_cancel(ask.order_id)

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    events = relevant_order(bt.events)
    assert [event[0] for event in events] == [
        "bind_fill",
        "inventory_sync",
        "fresh_policy",
        "submit",
    ]
    assert events[0][1] == "bid"
    assert events[2][1:3] == ("ask", True)


def test_b_both_side_execution_deltas_bind_before_any_refresh():
    kernel, bt = make_kernel()
    bid = seed_working(kernel, side="bid", order_id=10_001, tick=1000)
    ask = seed_working(kernel, side="ask", order_id=10_002, tick=1001)
    bt.current_timestamp += 250_000_000
    mark_execution(
        bt,
        bid,
        status=d2.HFT_PARTIALLY_FILLED,
        leaves_qty=0.0005,
    )
    mark_execution(
        bt,
        ask,
        status=d2.HFT_PARTIALLY_FILLED,
        leaves_qty=0.0005,
    )

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    assert relevant_order(bt.events) == [
        ("bind_fill", "bid", pytest.approx(0.0005)),
        ("inventory_sync", pytest.approx(0.0)),
        ("bind_fill", "ask", pytest.approx(0.0005)),
        ("inventory_sync", pytest.approx(0.0)),
    ]
    assert len(kernel.bound_fills) == 2
    assert kernel.fresh_replacement_evaluations == 0


def test_c_both_canceled_slots_clear_before_first_fresh_evaluation():
    kernel, bt = make_kernel()
    bid = request_replacement(kernel, side="bid")
    ask = request_replacement(kernel, side="ask")
    bt.current_timestamp += 250_000_000
    bt.acknowledge_cancel(bid.order_id)
    bt.acknowledge_cancel(ask.order_id)

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    fresh_events = [event for event in bt.events if event[0] == "fresh_policy"]
    assert [event[1] for event in fresh_events] == ["bid", "ask"]
    assert fresh_events[0][2:] == (True, None, None)
    assert kernel.bid.order_id is not None
    assert kernel.ask.order_id is not None
    assert kernel.bid.replacement_required is False
    assert kernel.ask.replacement_required is False


def test_d_fill_wins_and_discards_same_side_replacement_intent():
    kernel, bt = make_kernel()
    bid = request_replacement(kernel, side="bid")
    bt.current_timestamp += 250_000_000
    bt._position = p.BASE_ORDER_QTY
    mark_execution(bt, bid, status=d2.HFT_FILLED, leaves_qty=0.0)

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    assert [event[0] for event in relevant_order(bt.events)] == [
        "bind_fill",
        "inventory_sync",
    ]
    assert kernel.bid.order_id is None
    assert kernel.bid.replacement_required is False
    assert kernel.fresh_replacement_evaluations == 0


def test_e_batch_fill_can_trigger_force_flatten_before_maker_replacement():
    kernel, bt = make_kernel(policy_id="M02")
    kernel.inventory_clock = contract.InventoryClock(
        position=p.BASE_ORDER_QTY,
        nonzero_since_local_ns=1_000_000_000,
    )
    bt._position = p.BASE_ORDER_QTY
    bid = seed_working(kernel, side="bid", order_id=10_001, tick=1000)
    ask = request_replacement(kernel, side="ask")
    bt.current_timestamp = 62_000_000_000
    bt._position = 2 * p.BASE_ORDER_QTY
    mark_execution(bt, bid, status=d2.HFT_FILLED, leaves_qty=0.0)
    bt.acknowledge_cancel(ask.order_id)

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    assert kernel.last_fresh_decision.force_flatten is True
    assert kernel.force_decision is kernel.last_fresh_decision
    assert ("forced_flatten_ready",) in bt.events
    assert not [event for event in bt.events if event[0] == "submit"]


def test_f_terminal_shutdown_blocks_post_batch_replacement():
    kernel, bt = make_kernel()
    bid = request_replacement(kernel, side="bid")
    bt.current_timestamp += 250_000_000
    bt.acknowledge_cancel(bid.order_id)
    kernel.terminal_shutdown_started = True

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    assert kernel.bid.order_id is None
    assert kernel.bid.replacement_required is False
    assert kernel.fresh_replacement_evaluations == 0
    assert not [event for event in bt.events if event[0] == "submit"]


def test_g_no_fill_cancel_preserves_d6r18_fresh_replacement_semantics():
    kernel, bt = make_kernel()
    bid = request_replacement(kernel, side="bid")
    bt.current_timestamp += 250_000_000
    bt.acknowledge_cancel(bid.order_id)

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    assert [event[0] for event in bt.events] == [
        "cancel_request",
        "cancel_response",
        "fresh_policy",
        "submit",
    ]
    replacement = bt.orders(0)[kernel.bid.order_id]
    m4.validate_passive_target(
        side="bid",
        target_tick=replacement.price_tick,
        best_bid_tick=bt.depth(0).best_bid_tick,
        best_ask_tick=bt.depth(0).best_ask_tick,
    )


@pytest.mark.parametrize(
    ("policy_id", "active_direction"),
    (("M06", 1), ("M07", -1)),
)
def test_h_adapter_response_refresh_uses_only_active_direction(
    policy_id: str,
    active_direction: int,
):
    day = "2026-04-01"
    index = direct.DirectActionIndex(day=day, policy_id=policy_id, points=())
    kernel, bt = make_kernel(
        policy_id=policy_id,
        day=day,
        direct_index=index,
    )
    kernel.active_adapter_direction = active_direction
    order = request_replacement(kernel, side="bid")
    bt.current_timestamp = integration.day_start_ns(day) + 61_250_000_000
    bt.acknowledge_cancel(order.order_id)

    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    assert kernel.active_adapter_direction == active_direction
    assert kernel.direct_action_queries == 0
    assert kernel.adapter_candidate_epochs == 0
    assert kernel.a0_index is None
    assert kernel.legacy_index is None
    text = Path(d6r19.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "direct_index.exact",
        "_evaluate_policy_epoch(",
        "forward_fill",
        "backfill",
        "interpolate",
        "a0_index =",
        "legacy_index =",
    ):
        assert forbidden not in text


def test_i_no_request_overlap_duplicate_slot_or_replace_before_ack():
    kernel, bt = make_kernel()
    bid = seed_working(kernel, side="bid", order_id=10_001, tick=999)
    ask = seed_working(kernel, side="ask", order_id=10_002, tick=1002)
    decision = current_decision(kernel)

    for _ in range(2):
        kernel._maintain_side(side="bid", decision=decision)
        kernel._maintain_side(side="ask", decision=decision)

    assert kernel.cancel_requests == 2
    assert bt.request_overlaps == 0
    assert not [event for event in bt.events if event[0] == "submit"]

    bt.current_timestamp += 250_000_000
    bt.acknowledge_cancel(bid.order_id)
    bt.acknowledge_cancel(ask.order_id)
    kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    names = [event[0] for event in bt.events]
    assert max(i for i, name in enumerate(names) if name == "cancel_response") < min(
        i for i, name in enumerate(names) if name == "fresh_policy"
    )
    assert bt.request_overlaps == 0
    assert bt.duplicate_working_sides == 0
    assert kernel.bid.order_id is not None
    assert kernel.ask.order_id is not None
    assert kernel.bid.order_id != kernel.ask.order_id


def test_every_response_refresh_is_guarded_by_inventory_coherence():
    kernel, bt = make_kernel()
    bid = request_replacement(kernel, side="bid")
    bt.current_timestamp += 250_000_000
    bt.acknowledge_cancel(bid.order_id)
    bt._position = p.BASE_ORDER_QTY

    with pytest.raises(
        d2.EventLoopKernelError,
        match="local_inventory_clock_mismatch",
    ):
        kernel._process_response_batch(local_response_ns=bt.current_timestamp)

    # The successor refuses to paper over missing execution binding.
    assert kernel.inventory_clock.position == pytest.approx(0.0)
    assert kernel.fresh_replacement_evaluations == 0
    assert not [event for event in bt.events if event[0] == "fresh_policy"]


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    payload = f"blob {len(data)}\0".encode() + data
    return hashlib.sha1(payload).hexdigest()


def test_frozen_scientific_files_remain_exact():
    root = Path(__file__).resolve().parents[1]
    expected = {
        "src/multimarket/dev045_d6r18_fresh_replacement_driver.py": (
            "adc432f36814a1ccf1b2dd63219f5826c604753e"
        ),
        "src/multimarket/dev045_d6r18_canonical_runner.py": (
            "f8d81680ef75a3095f57bada6e01664391e69b72"
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
    }

    assert {
        relative: git_blob(root / relative)
        for relative in expected
    } == expected


def test_d6r19_has_no_canonical_runner_or_execution_surface():
    assert d6r19.EXPERIMENT_ID == "DEV045-D6R19"
    assert d6r19.CANONICAL_RUNNER_IMPLEMENTED is False
    assert d6r19.CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert d6r19.CANONICAL_ATTEMPT_CONSUMED is False
    assert d6r19.AUTOMATIC_RETRY is False
    assert d6r19.CANONICAL_PNL_WRITE_ENABLED is False
    assert d6r19.NETWORK_ACQUISITION_ENABLED is False
    assert d6r19.RAILWAY_ENABLED is False
    assert d6r19.LIVE_TRADING_AUTHORIZED is False
    assert d6r19.AUG_OPEN_AUTHORIZED is False
    assert d6r19.SEP_PLUS_OPEN_AUTHORIZED is False
    assert d6r19.NON_BTC_OPEN_AUTHORIZED is False

    text = Path(d6r19.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "np.load(",
        "numpy.load(",
        "open_verified_day_source(",
        "run_economic_arena(",
        "run_full_day(",
        "PolicyDecision | None",
        "pending_replacement = replacement",
    ):
        assert forbidden not in text

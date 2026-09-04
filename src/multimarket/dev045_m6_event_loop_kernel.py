from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import math

from hftbacktest.order import (
    NONE as HFT_NONE,
    NEW as HFT_NEW,
    EXPIRED as HFT_EXPIRED,
    FILLED as HFT_FILLED,
    CANCELED as HFT_CANCELED,
    PARTIALLY_FILLED as HFT_PARTIALLY_FILLED,
)

from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_economic_arena as m6
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket import dev045_m6_historical_orchestration as orch


EXPERIMENT_ID = "DEV045-D2"
DESIGN_VERSION = "actual-hft-event-loop-kernel-synthetic-v1"

HISTORICAL_FILE_IO_ENABLED = False
HISTORICAL_REPLAY_EXECUTION_ENABLED = False
HISTORICAL_PNL_ENABLED = False
ECONOMIC_ARENA_EXECUTION_ENABLED = False
CANONICAL_PNL_WRITE_ENABLED = False
NETWORK_ACQUISITION_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

SYNTHETIC_ONLY = True

ASSET_NO = 0

ORDER_ID_START = 100_000
MAX_ORDER_ID = 900_000

TRADE_FLOW_WINDOW_NS = 1_000_000_000
DEPTH_RETREAT_TICKS = 3


class EventLoopKernelError(RuntimeError):
    pass


def _finite(name: str, value: object) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EventLoopKernelError(name) from exc

    if not math.isfinite(x):
        raise EventLoopKernelError(name)

    return x


def _day_start_ns(day: str) -> int:
    if day not in p.AUTHORIZED_DAYS if hasattr(p, "AUTHORIZED_DAYS") else ():
        pass

    dt = datetime.fromisoformat(day).replace(
        tzinfo=timezone.utc
    )

    return int(dt.timestamp() * 1_000_000_000)


@dataclass
class TradeFlowWindow:
    events: deque[tuple[int, int, float]]

    @classmethod
    def empty(cls) -> "TradeFlowWindow":
        return cls(deque())

    def add(
        self,
        *,
        local_timestamp_ns: int,
        side: int,
        qty: float,
    ) -> None:
        t = int(local_timestamp_ns)
        q = _finite("trade_qty", qty)

        if t < 0:
            raise EventLoopKernelError("trade_timestamp")

        if q <= 0.0:
            raise EventLoopKernelError("trade_qty")

        if side not in (1, -1):
            raise EventLoopKernelError("trade_side")

        self.events.append((t, int(side), q))

    def quantities(
        self,
        *,
        current_local_timestamp_ns: int,
    ) -> tuple[float, float]:
        now = int(current_local_timestamp_ns)

        if now < 0:
            raise EventLoopKernelError("flow_now")

        lower = now - TRADE_FLOW_WINDOW_NS

        while self.events and self.events[0][0] < lower:
            self.events.popleft()

        buy = 0.0
        sell = 0.0

        for t, side, qty in self.events:
            if t > now:
                raise EventLoopKernelError(
                    "future_trade_in_flow_window"
                )

            if side == 1:
                buy += qty
            else:
                sell += qty

        return buy, sell


@dataclass
class SideSlot:
    side: str
    order_id: int | None = None
    last_leaves_qty: float = 0.0
    pending_replacement: p.PolicyDecision | None = None

    def active(self) -> bool:
        return self.order_id is not None


@dataclass(frozen=True)
class SyntheticKernelResult:
    policy_id: str
    day: str
    scenario: str

    maker_fill: binding.BoundReplayEvent
    taker_fill: binding.BoundReplayEvent

    maker_local_response_ns: int
    maker_exchange_execution_ns: int

    first_nonzero_inventory_local_ns: int
    flatten_decision_local_ns: int
    flatten_response_local_ns: int

    market_wakeups: int
    response_wakeups: int
    policy_epochs: int

    cancel_requests: int
    submit_requests: int

    terminal_position: float
    terminal_flat: bool


class ActualEventLoopKernel:
    """
    Real hftbacktest event-loop kernel over in-memory synthetic events.

    It deliberately does NOT:
      - open historical raw files;
      - invoke Tardis conversion;
      - execute M6 economic arena;
      - compute historical PnL.

    D2 proves the execution scheduler and lifecycle against the patched
    simulator before the historical feed is connected.
    """

    def __init__(
        self,
        *,
        bt,
        h,
        policy_id: str,
        day: str,
        scenario: str,
    ) -> None:
        if policy_id not in p.POLICY_IDS:
            raise EventLoopKernelError("policy_id")

        if day not in m6.AUTHORIZED_DAYS if hasattr(m6, "AUTHORIZED_DAYS") else ():
            pass

        self.bt = bt
        self.h = h
        self.policy_id = policy_id
        self.day = day
        self.scenario = scenario

        self.flow = TradeFlowWindow.empty()
        self.inventory_clock = d1.InventoryClock.flat()
        self.response_ledger = d1.ResponseLedger.empty()

        self.bid = SideSlot("bid")
        self.ask = SideSlot("ask")

        self.next_order_id = ORDER_ID_START

        self.bound_fills: list[binding.BoundReplayEvent] = []

        self.market_wakeups = 0
        self.response_wakeups = 0
        self.policy_epochs = 0

        self.cancel_requests = 0
        self.submit_requests = 0

        self.response_sequence = 0

        self.force_decision: p.PolicyDecision | None = None
        self.flatten_done = False
        self.flatten_response_local_ns: int | None = None
        self.flatten_decision_local_ns: int | None = None

        self.first_nonzero_inventory_local_ns: int | None = None
        self.maker_local_response_ns: int | None = None

    def _new_order_id(self) -> int:
        oid = int(self.next_order_id)

        if oid >= MAX_ORDER_ID:
            raise EventLoopKernelError("order_id_exhausted")

        self.next_order_id += 1
        return oid

    def _slot(self, side: str) -> SideSlot:
        if side == "bid":
            return self.bid
        if side == "ask":
            return self.ask
        raise EventLoopKernelError("side")

    def _capture_last_trades(self) -> None:
        trades = self.bt.last_trades(ASSET_NO)

        try:
            for trade in trades:
                ev = int(trade["ev"])

                if (
                    ev & self.h.TRADE_EVENT
                ) != self.h.TRADE_EVENT:
                    continue

                if (ev & self.h.BUY_EVENT) == self.h.BUY_EVENT:
                    side = 1
                elif (
                    ev & self.h.SELL_EVENT
                ) == self.h.SELL_EVENT:
                    side = -1
                else:
                    raise EventLoopKernelError(
                        "trade_side_bits"
                    )

                self.flow.add(
                    local_timestamp_ns=int(
                        trade["local_ts"]
                    ),
                    side=side,
                    qty=float(trade["qty"]),
                )
        finally:
            self.bt.clear_last_trades(ASSET_NO)

    def _dynamic_market_state(
        self,
        *,
        local_timestamp_ns: int,
    ) -> p.MarketState:
        depth = self.bt.depth(ASSET_NO)

        best_bid = int(depth.best_bid_tick)
        best_ask = int(depth.best_ask_tick)

        if best_bid <= 0 or best_ask <= best_bid:
            raise EventLoopKernelError(
                "invalid_local_book"
            )

        bid_depth: dict[int, float] = {}
        ask_depth: dict[int, float] = {}

        for tick in range(
            best_bid - DEPTH_RETREAT_TICKS,
            best_bid + 1,
        ):
            if tick > 0:
                bid_depth[tick] = float(
                    depth.bid_qty_at_tick(tick)
                )

        for tick in range(
            best_ask,
            best_ask + DEPTH_RETREAT_TICKS + 1,
        ):
            ask_depth[tick] = float(
                depth.ask_qty_at_tick(tick)
            )

        buy_1s, sell_1s = self.flow.quantities(
            current_local_timestamp_ns=local_timestamp_ns
        )

        inventory = float(self.bt.position(ASSET_NO))

        if not math.isclose(
            inventory,
            self.inventory_clock.position,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise EventLoopKernelError(
                "local_inventory_clock_mismatch"
            )

        age = self.inventory_clock.age_seconds(
            current_local_timestamp_ns=local_timestamp_ns
        )

        return p.MarketState(
            best_bid_tick=best_bid,
            best_ask_tick=best_ask,
            bid_depth_qty=bid_depth,
            ask_depth_qty=ask_depth,
            inventory=inventory,
            inventory_age_s=age,
            aggressive_buy_qty_1s=buy_1s,
            aggressive_sell_qty_1s=sell_1s,
            legacy_state=None,
            a0_p_touch=0.0,
        )

    def _submit_side(
        self,
        *,
        side: str,
        decision: p.PolicyDecision,
    ) -> None:
        slot = self._slot(side)

        if slot.order_id is not None:
            raise EventLoopKernelError(
                "submit_with_existing_slot"
            )

        oid = self._new_order_id()

        view = m4.submit_passive(
            self.bt,
            self.h,
            side=side,
            order_id=oid,
            decision=decision,
            wait=False,
        )

        if view.order_id != oid:
            raise EventLoopKernelError(
                "submitted_order_identity"
            )

        slot.order_id = oid

        if side == "bid":
            slot.last_leaves_qty = float(
                decision.bid_size
            )
        else:
            slot.last_leaves_qty = float(
                decision.ask_size
            )

        slot.pending_replacement = None

        self.submit_requests += 1

    def _request_cancel(
        self,
        *,
        slot: SideSlot,
        replacement: p.PolicyDecision | None,
    ) -> None:
        if slot.order_id is None:
            raise EventLoopKernelError(
                "cancel_empty_slot"
            )

        order = self.bt.orders(ASSET_NO).get(
            int(slot.order_id)
        )

        if order is None:
            raise EventLoopKernelError(
                "cancel_order_missing"
            )

        if int(order.req) != int(HFT_NONE):
            raise EventLoopKernelError(
                "cancel_request_overlap"
            )

        if int(order.status) not in (
            int(HFT_NEW),
            int(HFT_PARTIALLY_FILLED),
        ):
            raise EventLoopKernelError(
                "cancel_inactive_order"
            )

        rc = int(
            self.bt.cancel(
                ASSET_NO,
                int(slot.order_id),
                False,
            )
        )

        if rc != 0:
            raise EventLoopKernelError(
                f"cancel_rc:{rc}"
            )

        slot.pending_replacement = replacement
        self.cancel_requests += 1

    def _maintain_side(
        self,
        *,
        side: str,
        decision: p.PolicyDecision,
    ) -> None:
        slot = self._slot(side)

        if slot.order_id is None:
            intent = p.maintenance_intent(
                self.policy_id,
                side,
                None,
                decision,
                best_bid_tick=decision.bid_target_tick
                if decision.bid_target_tick is not None
                else self.bt.depth(ASSET_NO).best_bid_tick,
                best_ask_tick=decision.ask_target_tick
                if decision.ask_target_tick is not None
                else self.bt.depth(ASSET_NO).best_ask_tick,
            )

            if intent.submit:
                self._submit_side(
                    side=side,
                    decision=decision,
                )
            return

        raw = self.bt.orders(ASSET_NO).get(
            int(slot.order_id)
        )

        if raw is None:
            raise EventLoopKernelError(
                "working_order_missing"
            )

        # Never overlap a request.
        if int(raw.req) != int(HFT_NONE):
            return

        if int(raw.status) not in (
            int(HFT_NEW),
            int(HFT_PARTIALLY_FILLED),
        ):
            return

        depth = self.bt.depth(ASSET_NO)

        intent = p.maintenance_intent(
            self.policy_id,
            side,
            int(raw.price_tick),
            decision,
            best_bid_tick=int(depth.best_bid_tick),
            best_ask_tick=int(depth.best_ask_tick),
        )

        if intent.action == "KEEP":
            return

        if intent.action == "CANCEL":
            replacement = None

            if side == "bid":
                if (
                    decision.bid_enabled
                    and decision.bid_target_tick is not None
                    and decision.bid_size > 0.0
                ):
                    replacement = decision
            else:
                if (
                    decision.ask_enabled
                    and decision.ask_target_tick is not None
                    and decision.ask_size > 0.0
                ):
                    replacement = decision

            self._request_cancel(
                slot=slot,
                replacement=replacement,
            )
            return

        if intent.action == "NONE":
            return

        raise EventLoopKernelError(
            f"unexpected_maintenance:{intent.action}"
        )

    def _bind_new_execution(
        self,
        *,
        slot: SideSlot,
        raw,
        local_response_ns: int,
    ) -> None:
        leaves = float(raw.leaves_qty)

        if leaves > slot.last_leaves_qty + 1e-12:
            raise EventLoopKernelError(
                "leaves_quantity_increased"
            )

        executed_delta = (
            float(slot.last_leaves_qty) - leaves
        )

        if executed_delta <= 1e-15:
            slot.last_leaves_qty = leaves
            return

        view = m4._view(raw)

        # For the frozen one-lot maker order contract, the current execution
        # view must conserve the exact reduction in leaves quantity.
        if not math.isclose(
            float(view.exec_qty),
            executed_delta,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise EventLoopKernelError(
                "maker_response_execution_delta_mismatch"
            )

        event = binding.bind_passive_execution(
            view,
            policy_id=self.policy_id,
            day=self.day,
        )

        if event.kind != binding.FILL:
            raise EventLoopKernelError(
                "positive_delta_without_fill"
            )

        self.bound_fills.append(event)

        slot.last_leaves_qty = leaves

        new_position = float(
            self.bt.position(ASSET_NO)
        )

        old_zero = abs(
            self.inventory_clock.position
        ) < 1e-15

        self.inventory_clock = (
            self.inventory_clock.observe_local_position(
                new_position=new_position,
                local_response_timestamp_ns=local_response_ns,
            )
        )

        if (
            old_zero
            and abs(new_position) > 1e-15
            and self.first_nonzero_inventory_local_ns
            is None
        ):
            self.first_nonzero_inventory_local_ns = (
                int(local_response_ns)
            )

        if event.fill is not None:
            self.maker_local_response_ns = int(
                local_response_ns
            )

    def _process_response_batch(
        self,
        *,
        local_response_ns: int,
    ) -> None:
        self.response_sequence += 1
        seq = int(self.response_sequence)

        for slot in (self.bid, self.ask):
            if slot.order_id is None:
                continue

            raw = self.bt.orders(ASSET_NO).get(
                int(slot.order_id)
            )

            if raw is None:
                raise EventLoopKernelError(
                    "response_order_missing"
                )

            status = int(raw.status)
            req = int(raw.req)

            if status in (
                int(HFT_PARTIALLY_FILLED),
                int(HFT_FILLED),
            ):
                self._bind_new_execution(
                    slot=slot,
                    raw=raw,
                    local_response_ns=local_response_ns,
                )

            if status == int(HFT_FILLED):
                # A fill wins over any stale replacement request.
                slot.order_id = None
                slot.pending_replacement = None
                slot.last_leaves_qty = 0.0
                continue

            if (
                status
                in (
                    int(HFT_CANCELED),
                    int(HFT_EXPIRED),
                )
                and req == int(HFT_NONE)
            ):
                replacement = slot.pending_replacement

                slot.order_id = None
                slot.pending_replacement = None
                slot.last_leaves_qty = 0.0

                if (
                    replacement is not None
                    and self.force_decision is None
                ):
                    self._submit_side(
                        side=slot.side,
                        decision=replacement,
                    )

        self.response_ledger = (
            self.response_ledger.consume(seq)
        )

    def _all_quote_slots_clear(self) -> bool:
        return (
            self.bid.order_id is None
            and self.ask.order_id is None
        )

    def _force_cancel_quotes(
        self,
        decision: p.PolicyDecision,
    ) -> None:
        self.force_decision = decision

        for slot in (self.bid, self.ask):
            slot.pending_replacement = None

            if slot.order_id is None:
                continue

            raw = self.bt.orders(ASSET_NO).get(
                int(slot.order_id)
            )

            if raw is None:
                raise EventLoopKernelError(
                    "flatten_cancel_order_missing"
                )

            if int(raw.req) != int(HFT_NONE):
                # Existing request must finish first; no overlap.
                continue

            if int(raw.status) in (
                int(HFT_NEW),
                int(HFT_PARTIALLY_FILLED),
            ):
                self._request_cancel(
                    slot=slot,
                    replacement=None,
                )

    def _maybe_execute_forced_flatten(self) -> None:
        if self.flatten_done:
            return

        decision = self.force_decision

        if decision is None:
            return

        if not self._all_quote_slots_clear():
            return

        position = float(
            self.bt.position(ASSET_NO)
        )

        if abs(position) <= 1e-15:
            self.flatten_done = True
            self.inventory_clock = d1.InventoryClock.flat()
            self.flatten_response_local_ns = int(
                self.bt.current_timestamp
            )
            return

        before = binding.snapshot_state_values(
            self.bt.state_values(ASSET_NO)
        )

        view = m4.submit_forced_flatten(
            self.bt,
            self.h,
            direction=decision.flatten_direction,
            qty=decision.flatten_qty,
            wait=True,
        )

        after = binding.snapshot_state_values(
            self.bt.state_values(ASSET_NO)
        )

        event = (
            binding.bind_forced_flatten_from_state_delta(
                view,
                before=before,
                after=after,
                policy_id=self.policy_id,
                day=self.day,
            )
        )

        if event.kind != binding.FILL:
            raise EventLoopKernelError(
                "flatten_fill_missing"
            )

        self.bound_fills.append(event)

        response_local_ns = int(
            self.bt.current_timestamp
        )

        self.inventory_clock = (
            self.inventory_clock.observe_local_position(
                new_position=float(
                    self.bt.position(ASSET_NO)
                ),
                local_response_timestamp_ns=response_local_ns,
            )
        )

        self.flatten_response_local_ns = (
            response_local_ns
        )
        self.flatten_done = True

    def _evaluate_policy_epoch(
        self,
        *,
        local_timestamp_ns: int,
    ) -> None:
        self.policy_epochs += 1

        state = self._dynamic_market_state(
            local_timestamp_ns=local_timestamp_ns
        )

        decision = p.policy_decision(
            self.policy_id,
            state,
        )

        if decision.force_flatten:
            if self.flatten_decision_local_ns is None:
                self.flatten_decision_local_ns = int(
                    local_timestamp_ns
                )

            self._force_cancel_quotes(decision)
            self._maybe_execute_forced_flatten()
            return

        self._maintain_side(
            side="bid",
            decision=decision,
        )

        self._maintain_side(
            side="ask",
            decision=decision,
        )

    def run(self) -> SyntheticKernelResult:
        # Initialize at first strategy-visible market event.
        rc = int(
            self.bt.wait_next_feed(
                True,
                10_000_000_000,
            )
        )

        if rc != 2:
            raise EventLoopKernelError(
                f"initial_feed_rc:{rc}"
            )

        self.market_wakeups += 1
        self._capture_last_trades()

        next_policy_ns = d1.next_base_policy_epoch_after(
            int(self.bt.current_timestamp)
        )

        max_steps = 100_000

        for _ in range(max_steps):
            if self.flatten_done:
                break

            now = int(self.bt.current_timestamp)

            if now > next_policy_ns:
                raise EventLoopKernelError(
                    "policy_epoch_skipped"
                )

            timeout = next_policy_ns - now

            rc = int(
                self.bt.wait_next_feed(
                    True,
                    int(timeout),
                )
            )

            now = int(self.bt.current_timestamp)

            if rc == 1:
                raise EventLoopKernelError(
                    "end_of_data_before_terminal_flat"
                )

            if rc == 2:
                self.market_wakeups += 1
                self._capture_last_trades()

            elif rc == 3:
                self.response_wakeups += 1

                self._process_response_batch(
                    local_response_ns=now
                )

                self._maybe_execute_forced_flatten()

                if self.flatten_done:
                    break

            elif rc == 0:
                pass

            else:
                raise EventLoopKernelError(
                    f"unexpected_wait_rc:{rc}"
                )

            if now > next_policy_ns:
                raise EventLoopKernelError(
                    "wake_after_policy_target"
                )

            if now == next_policy_ns:
                self._evaluate_policy_epoch(
                    local_timestamp_ns=now
                )

                if self.flatten_done:
                    break

                next_policy_ns += d1.BASE_MAKER_STEP_NS

        else:
            raise EventLoopKernelError(
                "kernel_step_limit"
            )

        if not self.flatten_done:
            raise EventLoopKernelError(
                "terminal_flatten_not_completed"
            )

        terminal_position = float(
            self.bt.position(ASSET_NO)
        )

        if abs(terminal_position) > 1e-12:
            raise EventLoopKernelError(
                "terminal_position_nonzero"
            )

        fills = [
            x
            for x in self.bound_fills
            if x.kind == binding.FILL
        ]

        makers = [
            x
            for x in fills
            if x.liquidity == binding.MAKER
        ]

        takers = [
            x
            for x in fills
            if x.liquidity == binding.TAKER
        ]

        if len(makers) != 1:
            raise EventLoopKernelError(
                f"maker_fill_count:{len(makers)}"
            )

        if len(takers) != 1:
            raise EventLoopKernelError(
                f"taker_fill_count:{len(takers)}"
            )

        if self.first_nonzero_inventory_local_ns is None:
            raise EventLoopKernelError(
                "inventory_clock_never_started"
            )

        if self.flatten_decision_local_ns is None:
            raise EventLoopKernelError(
                "flatten_decision_missing"
            )

        if self.flatten_response_local_ns is None:
            raise EventLoopKernelError(
                "flatten_response_missing"
            )

        if self.maker_local_response_ns is None:
            raise EventLoopKernelError(
                "maker_local_response_missing"
            )

        return SyntheticKernelResult(
            policy_id=self.policy_id,
            day=self.day,
            scenario=self.scenario,
            maker_fill=makers[0],
            taker_fill=takers[0],
            maker_local_response_ns=(
                self.maker_local_response_ns
            ),
            maker_exchange_execution_ns=int(
                makers[0].timestamp_ns
            ),
            first_nonzero_inventory_local_ns=(
                self.first_nonzero_inventory_local_ns
            ),
            flatten_decision_local_ns=(
                self.flatten_decision_local_ns
            ),
            flatten_response_local_ns=(
                self.flatten_response_local_ns
            ),
            market_wakeups=self.market_wakeups,
            response_wakeups=self.response_wakeups,
            policy_epochs=self.policy_epochs,
            cancel_requests=self.cancel_requests,
            submit_requests=self.submit_requests,
            terminal_position=terminal_position,
            terminal_flat=True,
        )


def _synthetic_kernel_fixture(day: str):
    import numpy as np
    import hftbacktest as h

    if day not in (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    ):
        raise EventLoopKernelError("authorized_day")

    base = m4.make_fill_fixture().copy()

    # Extend the final non-trading keepalive so exact 1-second strategy
    # timers can advance beyond the 60-second inventory timeout.
    base[3]["exch_ts"] = 70_000_000_000
    base[3]["local_ts"] = 70_010_000_000

    dt = datetime.fromisoformat(day).replace(
        tzinfo=timezone.utc
    )

    offset_ns = int(
        dt.timestamp() * 1_000_000_000
    )

    base["exch_ts"] += offset_ns
    base["local_ts"] += offset_ns

    data = np.asarray(
        base,
        dtype=h.event_dtype,
    )

    m4.validate_events(data)
    return data


def _build_kernel_asset(
    data,
    *,
    scenario: str,
):
    import hftbacktest as h

    cfg = orch.scenario_config(scenario)

    asset = (
        h.BacktestAsset()
        .data([data])
        .initial_snapshot(
            m4.make_initial_snapshot()
        )
        .linear_asset(1.0)
        .constant_order_latency(
            int(cfg.entry_latency_ns),
            int(cfg.response_latency_ns),
        )
        .risk_adverse_queue_model()
        .partial_fill_exchange()
        .trading_value_fee_model(
            float(cfg.maker_fee),
            float(cfg.taker_fee),
        )
        .tick_size(p.TICK_SIZE)
        .lot_size(p.LOT_SIZE)
        .last_trades_capacity(4096)
    )

    return asset


def run_synthetic_kernel_probe(
    *,
    policy_id: str = "M02",
    day: str = "2026-01-01",
    scenario: str = m6.PRIMARY_SCENARIO,
) -> SyntheticKernelResult:
    if policy_id not in ("M01", "M02"):
        # D2 proves the actual engine/lifecycle kernel first.
        # Multi-rate M06/M07 and the remaining policy-specific semantics
        # are connected in the next driver layer.
        raise EventLoopKernelError(
            "d2_probe_policy_scope"
        )

    import hftbacktest as h

    data = _synthetic_kernel_fixture(day)

    asset = _build_kernel_asset(
        data,
        scenario=scenario,
    )

    bt = h.HashMapMarketDepthBacktest(
        [asset]
    )

    try:
        kernel = ActualEventLoopKernel(
            bt=bt,
            h=h,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
        )

        return kernel.run()

    finally:
        bt.close()


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "HISTORICAL_FILE_IO_ENABLED",
    "HISTORICAL_REPLAY_EXECUTION_ENABLED",
    "HISTORICAL_PNL_ENABLED",
    "ECONOMIC_ARENA_EXECUTION_ENABLED",
    "CANONICAL_PNL_WRITE_ENABLED",
    "NETWORK_ACQUISITION_ENABLED",
    "LIVE_TRADING_AUTHORIZED",
    "SYNTHETIC_ONLY",
    "TRADE_FLOW_WINDOW_NS",
    "EventLoopKernelError",
    "TradeFlowWindow",
    "SideSlot",
    "SyntheticKernelResult",
    "ActualEventLoopKernel",
    "run_synthetic_kernel_probe",
]

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from multimarket import dev045_m5b_multirate_clock as m5b
from multimarket.dev045_m5_prereg import AUTHORIZED_DAYS


EXPERIMENT_ID = "DEV045-D1"
DESIGN_VERSION = "historical-event-loop-local-clock-lifecycle-v1"

# ---------------------------------------------------------------------------
# Clock-domain binding
# ---------------------------------------------------------------------------

POLICY_CLOCK_DOMAIN = "LOCAL_STRATEGY_TIME"
A0_SUPPORT_CLOCK_DOMAIN = "LOCAL_STRATEGY_TIME"
INVENTORY_AGE_CLOCK_DOMAIN = "LOCAL_POSITION_KNOWLEDGE_TIME"

FILL_ACCOUNTING_CLOCK_DOMAIN = "EXCHANGE_EXECUTION_TIME"
M6_FILL_TIMESTAMP_DOMAIN = "EXCHANGE_EXECUTION_TIME"

BASE_MAKER_STEP_NS = 1_000_000_000
ADAPTER_STEP_NS = 60_000_000_000

# M5B works in microseconds because its frozen lineage is local_timestamp_us.
NS_PER_US = 1_000

# At an identical local timestamp, causal strategy-visible ordering is:
#
# 1. local market data
# 2. local order response
# 3. policy timer / decision
#
# This matches the pinned hftbacktest event ordering where LocalData precedes
# LocalOrder, and the driver evaluates policy only after processing all
# local-visible events at the decision timestamp.
LOCAL_MARKET_PRIORITY = 0
LOCAL_ORDER_RESPONSE_PRIORITY = 1
POLICY_DECISION_PRIORITY = 2

LOCAL_MARKET = "LOCAL_MARKET"
LOCAL_ORDER_RESPONSE = "LOCAL_ORDER_RESPONSE"
BASE_POLICY_DECISION = "BASE_POLICY_DECISION"
ADAPTER_POLICY_DECISION = "ADAPTER_POLICY_DECISION"

CANCEL_NONE = "NONE"
CANCEL_PENDING = "CANCEL_PENDING"
REPLACEMENT_READY = "REPLACEMENT_READY"

# ---------------------------------------------------------------------------
# Closed execution surfaces
# ---------------------------------------------------------------------------

HISTORICAL_FILE_IO_ENABLED = False
HISTORICAL_REPLAY_EXECUTION_ENABLED = False
HISTORICAL_PNL_ENABLED = False
ECONOMIC_ARENA_EXECUTION_ENABLED = False
CANONICAL_PNL_WRITE_ENABLED = False
NETWORK_ACQUISITION_ENABLED = False
LIVE_TRADING_AUTHORIZED = False


class EventLoopContractError(RuntimeError):
    pass


def _finite(name: str, value: object) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EventLoopContractError(name) from exc

    if not math.isfinite(x):
        raise EventLoopContractError(name)

    return x


def _ns(name: str, value: object) -> int:
    if isinstance(value, bool):
        raise EventLoopContractError(name)

    try:
        x = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EventLoopContractError(name) from exc

    try:
        exact = bool(x == value)
    except Exception as exc:
        raise EventLoopContractError(name) from exc

    if not exact or x < 0:
        raise EventLoopContractError(name)

    return x


def _day(day: str) -> str:
    if day not in AUTHORIZED_DAYS:
        raise EventLoopContractError("unauthorized_day")
    return day


def local_ns_to_us(local_timestamp_ns: int) -> int:
    """
    Convert the strategy-local simulator clock to the frozen A0/M5B clock.

    Historical Tardis timestamps are microsecond-origin timestamps converted
    to nanoseconds. Policy/A0 epochs therefore require exact microsecond
    alignment and never use exchange timestamps.
    """
    t = _ns("local_timestamp_ns", local_timestamp_ns)

    if t % NS_PER_US != 0:
        raise EventLoopContractError("local_clock_not_microsecond_aligned")

    return t // NS_PER_US


def is_base_policy_epoch_local(local_timestamp_ns: int) -> bool:
    t_us = local_ns_to_us(local_timestamp_ns)
    return m5b.is_base_maker_decision_epoch(t_us)


def is_adapter_policy_epoch_local(
    *,
    day: str,
    local_timestamp_ns: int,
) -> bool:
    _day(day)
    t_us = local_ns_to_us(local_timestamp_ns)

    return m5b.is_adapter_candidate_epoch(
        day=day,
        timestamp_us=t_us,
    )


def policy_epoch_kind_local(
    *,
    day: str,
    local_timestamp_ns: int,
) -> str | None:
    """
    Classify only strategy-local timer epochs.

    Market events are deliberately not policy decisions.
    """
    _day(day)
    t = _ns("local_timestamp_ns", local_timestamp_ns)

    if is_adapter_policy_epoch_local(
        day=day,
        local_timestamp_ns=t,
    ):
        return ADAPTER_POLICY_DECISION

    if is_base_policy_epoch_local(t):
        return BASE_POLICY_DECISION

    return None


def next_base_policy_epoch_after(local_timestamp_ns: int) -> int:
    """
    Strictly next exact local 1-second epoch.

    If called at exactly 12:00:01.000, returns 12:00:02.000.
    """
    t = _ns("local_timestamp_ns", local_timestamp_ns)
    return ((t // BASE_MAKER_STEP_NS) + 1) * BASE_MAKER_STEP_NS


@dataclass(frozen=True)
class LocalWakeup:
    local_timestamp_ns: int
    kind: str
    sequence: int = 0

    def __post_init__(self) -> None:
        _ns("local_timestamp_ns", self.local_timestamp_ns)

        if self.kind not in (
            LOCAL_MARKET,
            LOCAL_ORDER_RESPONSE,
            BASE_POLICY_DECISION,
            ADAPTER_POLICY_DECISION,
        ):
            raise EventLoopContractError("wakeup_kind")

        if int(self.sequence) < 0:
            raise EventLoopContractError("wakeup_sequence")

    @property
    def priority(self) -> int:
        if self.kind == LOCAL_MARKET:
            return LOCAL_MARKET_PRIORITY

        if self.kind == LOCAL_ORDER_RESPONSE:
            return LOCAL_ORDER_RESPONSE_PRIORITY

        return POLICY_DECISION_PRIORITY


def ordered_local_wakeups(
    wakeups: Iterable[LocalWakeup],
) -> tuple[LocalWakeup, ...]:
    """
    Deterministic same-timestamp ordering.

    A policy decision always sees local market data and local order responses
    already processed at the same strategy-local timestamp.
    """
    xs = tuple(wakeups)

    return tuple(
        sorted(
            xs,
            key=lambda x: (
                int(x.local_timestamp_ns),
                int(x.priority),
                int(x.sequence),
            ),
        )
    )


def validate_policy_timer_wakeup(
    *,
    day: str,
    wakeup: LocalWakeup,
) -> None:
    _day(day)

    expected = policy_epoch_kind_local(
        day=day,
        local_timestamp_ns=wakeup.local_timestamp_ns,
    )

    if expected is None:
        raise EventLoopContractError("policy_timer_off_grid")

    if wakeup.kind != expected:
        raise EventLoopContractError("policy_timer_kind_mismatch")


# ---------------------------------------------------------------------------
# Inventory knowledge clock
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InventoryClock:
    position: float
    nonzero_since_local_ns: int | None

    def __post_init__(self) -> None:
        p = _finite("position", self.position)

        if abs(p) < 1e-15:
            if self.nonzero_since_local_ns is not None:
                raise EventLoopContractError(
                    "flat_inventory_with_active_clock"
                )
        else:
            if self.nonzero_since_local_ns is None:
                raise EventLoopContractError(
                    "nonflat_inventory_without_clock"
                )

            _ns(
                "nonzero_since_local_ns",
                self.nonzero_since_local_ns,
            )

    @classmethod
    def flat(cls) -> "InventoryClock":
        return cls(
            position=0.0,
            nonzero_since_local_ns=None,
        )

    def observe_local_position(
        self,
        *,
        new_position: float,
        local_response_timestamp_ns: int,
    ) -> "InventoryClock":
        """
        Inventory age begins when the strategy-local state learns it is nonzero.

        It does NOT begin at exchange execution time, because the strategy
        cannot causally act on a fill before the local response is received.
        """
        old = _finite("old_position", self.position)
        new = _finite("new_position", new_position)
        t = _ns(
            "local_response_timestamp_ns",
            local_response_timestamp_ns,
        )

        old_zero = abs(old) < 1e-15
        new_zero = abs(new) < 1e-15

        if old_zero and new_zero:
            return InventoryClock.flat()

        if old_zero and not new_zero:
            return InventoryClock(
                position=new,
                nonzero_since_local_ns=t,
            )

        if not old_zero and new_zero:
            return InventoryClock.flat()

        # A direct sign flip without observing flat would violate the
        # flat-to-flat accounting lifecycle.
        if old * new < 0.0:
            raise EventLoopContractError(
                "inventory_sign_flip_without_flat"
            )

        assert self.nonzero_since_local_ns is not None

        if t < self.nonzero_since_local_ns:
            raise EventLoopContractError(
                "inventory_clock_time_reversal"
            )

        return InventoryClock(
            position=new,
            nonzero_since_local_ns=self.nonzero_since_local_ns,
        )

    def age_seconds(
        self,
        *,
        current_local_timestamp_ns: int,
    ) -> float:
        now = _ns(
            "current_local_timestamp_ns",
            current_local_timestamp_ns,
        )

        if abs(self.position) < 1e-15:
            return 0.0

        assert self.nonzero_since_local_ns is not None

        if now < self.nonzero_since_local_ns:
            raise EventLoopContractError(
                "inventory_age_before_known_fill"
            )

        return (
            now - self.nonzero_since_local_ns
        ) / 1_000_000_000.0


# ---------------------------------------------------------------------------
# Fill-response consumption
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResponseLedger:
    """
    The event loop assigns one strictly increasing sequence to each local
    order-response wakeup.

    Fill deduplication is response-sequence based, NOT inferred from
    price/qty/timestamp tuples. Two legitimate partial fills may have equal
    price, qty, and exchange timestamp and must not be collapsed.
    """

    consumed_response_sequences: frozenset[int]

    @classmethod
    def empty(cls) -> "ResponseLedger":
        return cls(frozenset())

    def consume(
        self,
        response_sequence: int,
    ) -> "ResponseLedger":
        seq = int(response_sequence)

        if seq < 0:
            raise EventLoopContractError(
                "negative_response_sequence"
            )

        if seq in self.consumed_response_sequences:
            raise EventLoopContractError(
                "duplicate_order_response_consumption"
            )

        return ResponseLedger(
            self.consumed_response_sequences | {seq}
        )


@dataclass(frozen=True)
class FillClockBinding:
    """
    Separate causal and economic timestamps.

    local_response_timestamp_ns:
        when the strategy learns of the fill and local inventory changes.

    exchange_execution_timestamp_ns:
        frozen M4->M6 economic FillRecord timestamp.
    """

    local_response_timestamp_ns: int
    exchange_execution_timestamp_ns: int

    def __post_init__(self) -> None:
        local = _ns(
            "local_response_timestamp_ns",
            self.local_response_timestamp_ns,
        )
        exch = _ns(
            "exchange_execution_timestamp_ns",
            self.exchange_execution_timestamp_ns,
        )

        if exch > local:
            raise EventLoopContractError(
                "exchange_fill_after_local_response"
            )


# ---------------------------------------------------------------------------
# Cancel -> response -> replacement gate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CancelReplaceGate:
    working_order_id: int | None
    cancel_state: str
    canceled_order_id: int | None
    replacement_tick: int | None
    replacement_qty: float

    def __post_init__(self) -> None:
        if self.cancel_state not in (
            CANCEL_NONE,
            CANCEL_PENDING,
            REPLACEMENT_READY,
        ):
            raise EventLoopContractError(
                "cancel_state"
            )

        if self.working_order_id is not None:
            if int(self.working_order_id) <= 0:
                raise EventLoopContractError(
                    "working_order_id"
                )

        if self.canceled_order_id is not None:
            if int(self.canceled_order_id) <= 0:
                raise EventLoopContractError(
                    "canceled_order_id"
                )

        qty = _finite(
            "replacement_qty",
            self.replacement_qty,
        )

        if qty < 0.0:
            raise EventLoopContractError(
                "replacement_qty"
            )

    @classmethod
    def working(
        cls,
        order_id: int,
    ) -> "CancelReplaceGate":
        if int(order_id) <= 0:
            raise EventLoopContractError("order_id")

        return cls(
            working_order_id=int(order_id),
            cancel_state=CANCEL_NONE,
            canceled_order_id=None,
            replacement_tick=None,
            replacement_qty=0.0,
        )

    def request_cancel_for_replacement(
        self,
        *,
        replacement_tick: int,
        replacement_qty: float,
    ) -> "CancelReplaceGate":
        if self.cancel_state != CANCEL_NONE:
            raise EventLoopContractError(
                "cancel_already_in_progress"
            )

        if self.working_order_id is None:
            raise EventLoopContractError(
                "cancel_without_working_order"
            )

        tick = int(replacement_tick)
        qty = _finite(
            "replacement_qty",
            replacement_qty,
        )

        if tick <= 0:
            raise EventLoopContractError(
                "replacement_tick"
            )

        if qty <= 0.0:
            raise EventLoopContractError(
                "replacement_qty"
            )

        return CancelReplaceGate(
            working_order_id=self.working_order_id,
            cancel_state=CANCEL_PENDING,
            canceled_order_id=self.working_order_id,
            replacement_tick=tick,
            replacement_qty=qty,
        )

    @property
    def replacement_authorized(self) -> bool:
        return self.cancel_state == REPLACEMENT_READY

    def receive_cancel_response(
        self,
        *,
        order_id: int,
    ) -> "CancelReplaceGate":
        if self.cancel_state != CANCEL_PENDING:
            raise EventLoopContractError(
                "unexpected_cancel_response"
            )

        if self.canceled_order_id != int(order_id):
            raise EventLoopContractError(
                "cancel_response_order_mismatch"
            )

        return CancelReplaceGate(
            working_order_id=None,
            cancel_state=REPLACEMENT_READY,
            canceled_order_id=self.canceled_order_id,
            replacement_tick=self.replacement_tick,
            replacement_qty=self.replacement_qty,
        )

    def record_replacement_submit(
        self,
        *,
        new_order_id: int,
    ) -> "CancelReplaceGate":
        if not self.replacement_authorized:
            raise EventLoopContractError(
                "replacement_before_cancel_response"
            )

        if int(new_order_id) <= 0:
            raise EventLoopContractError(
                "new_order_id"
            )

        return CancelReplaceGate.working(
            int(new_order_id)
        )


# ---------------------------------------------------------------------------
# Structural driver contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriverBoundaryContract:
    policy_clock_domain: str = POLICY_CLOCK_DOMAIN
    a0_clock_domain: str = A0_SUPPORT_CLOCK_DOMAIN
    inventory_age_clock_domain: str = INVENTORY_AGE_CLOCK_DOMAIN
    fill_accounting_clock_domain: str = FILL_ACCOUNTING_CLOCK_DOMAIN

    market_event_is_policy_epoch: bool = False
    probability_carry_enabled: bool = False
    response_tuple_dedup_enabled: bool = False

    historical_file_io_enabled: bool = False
    historical_replay_execution_enabled: bool = False
    historical_pnl_enabled: bool = False


def frozen_driver_boundary() -> DriverBoundaryContract:
    return DriverBoundaryContract()

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Mapping

from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_economic_arena as m6

from multimarket.dev045_m5_fee_amendment import (
    PRIMARY_MAKER_RATE,
    PRIMARY_TAKER_RATE,
    STRESS_MAKER_RATE,
    STRESS_TAKER_RATE,
)

from multimarket.dev045_m5_prereg import AUTHORIZED_DAYS


# This phase is deliberately synthetic-only.
#
# Historical file conversion is frozen separately in
# dev045_m6_tardis_feed.py.
#
# The purpose here is to prove exact in-memory wiring:
#
# M3 policy
#   -> M4 patched simulator
#   -> M4/M6 binding
#   -> M6 FillRecord / ReplayAudit / flat-to-flat accounting.
#
# No filesystem historical feed is opened by this module.
HISTORICAL_FILE_IO_ENABLED = False
HISTORICAL_ARENA_EXECUTION_ENABLED = False
CANONICAL_PNL_WRITE_ENABLED = False
LIVE_TRADING_AUTHORIZED = False


class HistoricalOrchestrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReplayScenarioConfig:
    scenario: str
    queue_model: str
    entry_latency_ns: int
    response_latency_ns: int
    maker_fee: float
    taker_fee: float


@dataclass(frozen=True)
class FrozenReplayPlan:
    policy_ids: tuple[str, ...]
    days: tuple[str, ...]
    scenarios: tuple[str, ...]
    day_replays: int
    blocks_per_day: int
    blocks_per_policy: int


@dataclass(frozen=True)
class SyntheticPolicyReplay:
    policy_id: str
    day: str
    scenario: str
    maker_event: binding.BoundReplayEvent
    taker_event: binding.BoundReplayEvent
    audit: m6.ReplayAudit
    cycles: tuple[m6.CycleRecord, ...]
    simulator_fee: float
    terminal_position: float


def scenario_config(scenario: str) -> ReplayScenarioConfig:
    if scenario == m6.PRIMARY_SCENARIO:
        return ReplayScenarioConfig(
            scenario=scenario,
            queue_model="risk_adverse",
            entry_latency_ns=m4.PRIMARY_LATENCY_NS,
            response_latency_ns=m4.PRIMARY_LATENCY_NS,
            maker_fee=float(PRIMARY_MAKER_RATE),
            taker_fee=float(PRIMARY_TAKER_RATE),
        )

    if scenario == m6.STRESS_SCENARIO:
        return ReplayScenarioConfig(
            scenario=scenario,
            queue_model="risk_adverse",
            entry_latency_ns=m4.STRESS_LATENCY_NS,
            response_latency_ns=m4.STRESS_LATENCY_NS,
            maker_fee=float(STRESS_MAKER_RATE),
            taker_fee=float(STRESS_TAKER_RATE),
        )

    raise HistoricalOrchestrationError("scenario")


def frozen_replay_plan() -> FrozenReplayPlan:
    policy_ids = tuple(p.POLICY_IDS)
    days = tuple(AUTHORIZED_DAYS)
    scenarios = (
        m6.PRIMARY_SCENARIO,
        m6.STRESS_SCENARIO,
    )

    if policy_ids != (
        "M01",
        "M02",
        "M03",
        "M04",
        "M05",
        "M06",
        "M07",
        "M08",
    ):
        raise HistoricalOrchestrationError("policy_family")

    if days != (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    ):
        raise HistoricalOrchestrationError("authorized_days")

    day_replays = len(policy_ids) * len(days) * len(scenarios)

    return FrozenReplayPlan(
        policy_ids=policy_ids,
        days=days,
        scenarios=scenarios,
        day_replays=day_replays,
        blocks_per_day=6,
        blocks_per_policy=42,
    )


def _validate_identity(
    *,
    policy_id: str,
    day: str,
    scenario: str,
) -> ReplayScenarioConfig:
    if policy_id not in p.POLICY_IDS:
        raise HistoricalOrchestrationError("policy_id")

    if day not in AUTHORIZED_DAYS:
        raise HistoricalOrchestrationError("authorized_day")

    return scenario_config(scenario)


def _synthetic_fixture_for_day(day: str):
    if day not in AUTHORIZED_DAYS:
        raise HistoricalOrchestrationError("authorized_day")

    data = m4.make_fill_fixture().copy()

    day_start = datetime.fromisoformat(day).replace(
        tzinfo=timezone.utc
    )
    offset_ns = int(day_start.timestamp() * 1_000_000_000)

    data["exch_ts"] += offset_ns
    data["local_ts"] += offset_ns

    m4.validate_events(data)
    return data


def _require_close(
    name: str,
    actual: float,
    expected: float,
    *,
    abs_tol: float = 1e-12,
) -> None:
    if not math.isclose(
        float(actual),
        float(expected),
        rel_tol=1e-12,
        abs_tol=float(abs_tol),
    ):
        raise HistoricalOrchestrationError(
            f"{name}:{actual}:{expected}"
        )


def run_synthetic_policy_cycle(
    *,
    policy_id: str,
    day: str = "2026-01-01",
    scenario: str = m6.PRIMARY_SCENARIO,
) -> SyntheticPolicyReplay:
    """
    Prove one exact flat-to-flat synthetic lifecycle through the frozen stack.

    This function intentionally creates its events from M4's synthetic fixture.
    It never opens historical files.

    Lifecycle:

      1. neutral M3 policy emits passive bid;
      2. RiskAdverse queue consumes displayed q_ahead;
      3. next sell trade fills one maker lot;
      4. 60-second inventory timeout is presented to the same frozen policy;
      5. policy requests executable MARKET flatten;
      6. taker fill is bound from simulator state deltas;
      7. M6 accounts exactly one flat-to-flat cycle;
      8. simulator fee and M6 fee must independently agree.
    """
    cfg = _validate_identity(
        policy_id=policy_id,
        day=day,
        scenario=scenario,
    )

    import hftbacktest as h

    data = _synthetic_fixture_for_day(day)

    asset = m4.build_asset(
        data,
        queue_model=cfg.queue_model,
        entry_latency_ns=cfg.entry_latency_ns,
        response_latency_ns=cfg.response_latency_ns,
        maker_fee=cfg.maker_fee,
        taker_fee=cfg.taker_fee,
    )

    bt = h.HashMapMarketDepthBacktest([asset])

    try:
        # First synthetic depth event activates the replay clock.
        m4._next_feed(bt)

        initial_state = m4.policy_book()
        decision = p.policy_decision(policy_id, initial_state)

        if decision.force_flatten:
            raise HistoricalOrchestrationError(
                "unexpected_initial_flatten"
            )

        if (
            not decision.bid_enabled
            or decision.bid_target_tick != 1000
            or decision.bid_size != p.BASE_ORDER_QTY
        ):
            raise HistoricalOrchestrationError(
                "synthetic_passive_bid_contract"
            )

        accepted = m4.submit_passive(
            bt,
            h,
            side="bid",
            order_id=m4.BID_ORDER_ID,
            decision=decision,
            wait=True,
        )

        if accepted.status != h.NEW:
            raise HistoricalOrchestrationError(
                "passive_order_not_new"
            )

        # q_ahead=10 at bid 100.0. First sell trade consumes exactly q_ahead.
        m4._next_feed(bt)
        m4._response_or_timeout(bt)

        after_q_ahead = m4._view(
            bt.orders(0).get(m4.BID_ORDER_ID)
        )

        if (
            after_q_ahead.status != h.NEW
            or abs(after_q_ahead.exec_qty) > 1e-15
        ):
            raise HistoricalOrchestrationError(
                "risk_adverse_touch_contract"
            )

        # Next sell trade of one M3 lot fills the passive maker order.
        m4._next_feed(bt)
        m4._response_or_timeout(bt)

        maker_view = m4._view(
            bt.orders(0).get(m4.BID_ORDER_ID)
        )

        maker_event = binding.bind_passive_execution(
            maker_view,
            policy_id=policy_id,
            day=day,
        )

        if maker_event.kind != binding.FILL:
            raise HistoricalOrchestrationError(
                "maker_fill_missing"
            )

        if maker_event.fill is None:
            raise HistoricalOrchestrationError(
                "maker_fill_record_missing"
            )

        if maker_event.fill.liquidity != binding.MAKER:
            raise HistoricalOrchestrationError(
                "maker_liquidity_role"
            )

        position_before_flatten = float(bt.position(0))

        _require_close(
            "maker_position",
            position_before_flatten,
            p.BASE_ORDER_QTY,
        )

        # Present frozen timeout condition to the same policy.
        timeout_state = m4.policy_book(
            inventory=position_before_flatten,
            inventory_age_s=p.INVENTORY_TIMEOUT_S,
        )

        timeout_decision = p.policy_decision(
            policy_id,
            timeout_state,
        )

        if not timeout_decision.force_flatten:
            raise HistoricalOrchestrationError(
                "timeout_flatten_not_requested"
            )

        if timeout_decision.flatten_direction >= 0:
            raise HistoricalOrchestrationError(
                "long_inventory_flatten_direction"
            )

        _require_close(
            "flatten_qty",
            timeout_decision.flatten_qty,
            position_before_flatten,
        )

        before = binding.snapshot_state_values(
            bt.state_values(0)
        )

        flatten_view = m4.submit_forced_flatten(
            bt,
            h,
            direction=timeout_decision.flatten_direction,
            qty=timeout_decision.flatten_qty,
            wait=True,
        )

        after = binding.snapshot_state_values(
            bt.state_values(0)
        )

        taker_event = (
            binding.bind_forced_flatten_from_state_delta(
                flatten_view,
                before=before,
                after=after,
                policy_id=policy_id,
                day=day,
            )
        )

        if taker_event.kind != binding.FILL:
            raise HistoricalOrchestrationError(
                "taker_fill_missing"
            )

        if taker_event.fill is None:
            raise HistoricalOrchestrationError(
                "taker_fill_record_missing"
            )

        if taker_event.fill.liquidity != binding.TAKER:
            raise HistoricalOrchestrationError(
                "taker_liquidity_role"
            )

        terminal_position = float(bt.position(0))

        _require_close(
            "terminal_position",
            terminal_position,
            0.0,
        )

        fills = (
            maker_event.fill,
            taker_event.fill,
        )

        cycles = tuple(
            m6.account_fill_bucket(
                fills,
                scenario=scenario,
            )
        )

        if len(cycles) != 1:
            raise HistoricalOrchestrationError(
                "flat_to_flat_cycle_count"
            )

        cycle = cycles[0]

        if cycle.fill_count != 2:
            raise HistoricalOrchestrationError(
                "cycle_fill_count"
            )

        if cycle.maker_notional <= 0.0:
            raise HistoricalOrchestrationError(
                "maker_notional"
            )

        if cycle.taker_notional <= 0.0:
            raise HistoricalOrchestrationError(
                "taker_notional"
            )

        simulator_fee = float(after.fee)

        _require_close(
            "m6_simulator_fee_identity",
            cycle.fees,
            simulator_fee,
            abs_tol=1e-15,
        )

        audit = m6.ReplayAudit(
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            execution_integrity_failures=0,
            terminal_flat=True,
        )

        return SyntheticPolicyReplay(
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            maker_event=maker_event,
            taker_event=taker_event,
            audit=audit,
            cycles=cycles,
            simulator_fee=simulator_fee,
            terminal_position=terminal_position,
        )

    finally:
        bt.close()


def run_synthetic_family_probe(
    *,
    day: str = "2026-01-01",
    scenario: str = m6.PRIMARY_SCENARIO,
) -> Mapping[str, SyntheticPolicyReplay]:
    if day not in AUTHORIZED_DAYS:
        raise HistoricalOrchestrationError(
            "authorized_day"
        )

    scenario_config(scenario)

    out: dict[str, SyntheticPolicyReplay] = {}

    for policy_id in p.POLICY_IDS:
        out[policy_id] = run_synthetic_policy_cycle(
            policy_id=policy_id,
            day=day,
            scenario=scenario,
        )

    if tuple(out) != tuple(p.POLICY_IDS):
        raise HistoricalOrchestrationError(
            "family_order"
        )

    return out


__all__ = [
    "HISTORICAL_FILE_IO_ENABLED",
    "HISTORICAL_ARENA_EXECUTION_ENABLED",
    "CANONICAL_PNL_WRITE_ENABLED",
    "LIVE_TRADING_AUTHORIZED",
    "HistoricalOrchestrationError",
    "ReplayScenarioConfig",
    "FrozenReplayPlan",
    "SyntheticPolicyReplay",
    "scenario_config",
    "frozen_replay_plan",
    "run_synthetic_policy_cycle",
    "run_synthetic_family_probe",
]

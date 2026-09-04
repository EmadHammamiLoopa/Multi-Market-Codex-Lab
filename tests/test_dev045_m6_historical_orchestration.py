from __future__ import annotations

import math

import pytest

from multimarket import dev045_m3_policy as p
from multimarket import dev045_m6_economic_arena as m6
from multimarket import dev045_m6_historical_orchestration as o

from multimarket.dev045_m5_fee_amendment import (
    PRIMARY_MAKER_RATE,
    PRIMARY_TAKER_RATE,
    STRESS_MAKER_RATE,
    STRESS_TAKER_RATE,
)


def test_execution_surfaces_remain_closed():
    assert o.HISTORICAL_FILE_IO_ENABLED is False
    assert o.HISTORICAL_ARENA_EXECUTION_ENABLED is False
    assert o.CANONICAL_PNL_WRITE_ENABLED is False
    assert o.LIVE_TRADING_AUTHORIZED is False


def test_frozen_replay_plan_is_exact_preregistered_matrix():
    plan = o.frozen_replay_plan()

    assert plan.policy_ids == tuple(p.POLICY_IDS)
    assert plan.days == (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    )

    assert plan.scenarios == (
        m6.PRIMARY_SCENARIO,
        m6.STRESS_SCENARIO,
    )

    assert plan.day_replays == 8 * 7 * 2
    assert plan.blocks_per_day == 6
    assert plan.blocks_per_policy == 42


def test_primary_scenario_identity():
    cfg = o.scenario_config(m6.PRIMARY_SCENARIO)

    assert cfg.queue_model == "risk_adverse"
    assert cfg.entry_latency_ns == 250_000_000
    assert cfg.response_latency_ns == 250_000_000
    assert cfg.maker_fee == PRIMARY_MAKER_RATE
    assert cfg.taker_fee == PRIMARY_TAKER_RATE


def test_stress_scenario_identity():
    cfg = o.scenario_config(m6.STRESS_SCENARIO)

    assert cfg.queue_model == "risk_adverse"
    assert cfg.entry_latency_ns == 500_000_000
    assert cfg.response_latency_ns == 500_000_000
    assert cfg.maker_fee == STRESS_MAKER_RATE
    assert cfg.taker_fee == STRESS_TAKER_RATE


def _assert_family(results, scenario):
    assert tuple(results) == tuple(p.POLICY_IDS)

    for policy_id, result in results.items():
        assert result.policy_id == policy_id
        assert result.day == "2026-01-01"
        assert result.scenario == scenario

        assert result.maker_event.fill is not None
        assert result.taker_event.fill is not None

        assert result.maker_event.fill.liquidity == "MAKER"
        assert result.taker_event.fill.liquidity == "TAKER"

        assert result.maker_event.fill.side == "BUY"
        assert result.taker_event.fill.side == "SELL"

        assert result.audit.policy_id == policy_id
        assert result.audit.day == "2026-01-01"
        assert result.audit.scenario == scenario
        assert result.audit.execution_integrity_failures == 0
        assert result.audit.terminal_flat is True

        assert result.terminal_position == pytest.approx(0.0)

        assert len(result.cycles) == 1
        cycle = result.cycles[0]

        assert cycle.policy_id == policy_id
        assert cycle.day == "2026-01-01"
        assert cycle.fill_count == 2
        assert cycle.maker_notional > 0
        assert cycle.taker_notional > 0

        assert cycle.fees == pytest.approx(
            result.simulator_fee,
            abs=1e-15,
        )

        assert math.isfinite(cycle.cash_pnl_before_fees)
        assert math.isfinite(cycle.fees)
        assert math.isfinite(cycle.net_pnl)
        assert math.isfinite(cycle.net_bps)


def test_all_eight_policies_primary_wire_end_to_end():
    results = o.run_synthetic_family_probe(
        scenario=m6.PRIMARY_SCENARIO
    )
    _assert_family(results, m6.PRIMARY_SCENARIO)


def test_all_eight_policies_stress_wire_end_to_end():
    results = o.run_synthetic_family_probe(
        scenario=m6.STRESS_SCENARIO
    )
    _assert_family(results, m6.STRESS_SCENARIO)


def test_unauthorized_day_fails_closed():
    with pytest.raises(
        o.HistoricalOrchestrationError,
        match="authorized_day",
    ):
        o.run_synthetic_policy_cycle(
            policy_id="M01",
            day="2026-08-01",
            scenario=m6.PRIMARY_SCENARIO,
        )


def test_unknown_scenario_fails_closed():
    with pytest.raises(
        o.HistoricalOrchestrationError,
        match="scenario",
    ):
        o.run_synthetic_policy_cycle(
            policy_id="M01",
            day="2026-01-01",
            scenario="NOT_FROZEN",
        )

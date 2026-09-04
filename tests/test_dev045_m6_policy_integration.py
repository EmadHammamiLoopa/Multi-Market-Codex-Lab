from __future__ import annotations

from dataclasses import replace

import pytest

from multimarket import dev045_m3_policy as p
from multimarket import dev045_m5a_a0_support_semantics as m5a
from multimarket import dev045_m5b_multirate_clock as m5b
from multimarket import dev045_m6_economic_arena as m6
from multimarket.dev044_t0_strategy_contract import (
    ABSTAIN,
    LONG,
    SHORT,
)
from multimarket import dev045_m6_policy_integration as d3


def _market_state(
    *,
    inventory: float = 0.0,
    age: float = 0.0,
) -> p.MarketState:
    return p.MarketState(
        best_bid_tick=1000,
        best_ask_tick=1003,
        bid_depth_qty={
            997: 10.0,
            998: 10.0,
            999: 10.0,
            1000: 20.0,
        },
        ask_depth_qty={
            1003: 1.0,
            1004: 10.0,
            1005: 10.0,
            1006: 10.0,
        },
        inventory=inventory,
        inventory_age_s=age,
        aggressive_buy_qty_1s=0.0,
        aggressive_sell_qty_1s=0.0,
        legacy_state=None,
        a0_p_touch=0.0,
    )


def _minute_ns(day: str) -> int:
    return (
        d3.day_start_ns(day)
        + 60_000_000_000
    )


def _minute_us(day: str) -> int:
    return (
        d3.day_start_us(day)
        + 60_000_000
    )


def _trace_at(
    result: d3.PolicyIntegrationResult,
    timestamp_ns: int,
):
    rows = tuple(
        x
        for x in result.trace
        if x.local_timestamp_ns
        == timestamp_ns
    )

    assert len(rows) == 1
    return rows[0]


def test_execution_surfaces_closed():
    assert d3.SYNTHETIC_ONLY is True

    assert d3.HISTORICAL_FILE_IO_ENABLED is False
    assert d3.HISTORICAL_REPLAY_EXECUTION_ENABLED is False
    assert d3.HISTORICAL_PNL_ENABLED is False

    assert d3.ECONOMIC_ARENA_EXECUTION_ENABLED is False
    assert d3.CANONICAL_PNL_WRITE_ENABLED is False
    assert d3.NETWORK_ACQUISITION_ENABLED is False
    assert d3.LIVE_TRADING_AUTHORIZED is False

    assert m5b.PROBABILITY_CARRY_ENABLED is False
    assert m5b.PROBABILITY_FORWARD_FILL_ENABLED is False

    assert "p_touch" not in (
        d3.DecisionTrace.__dataclass_fields__
    )


@pytest.mark.parametrize(
    "policy_id",
    ("M06", "M07"),
)
@pytest.mark.parametrize(
    "direction",
    (LONG, SHORT, ABSTAIN),
)
def test_adapter_direction_helper_matches_frozen_m3_exactly(
    policy_id,
    direction,
):
    state = _market_state()

    legacy = d3.synthetic_legacy_state(
        policy_id=policy_id,
        direction=direction,
    )

    support = m5a.A0LegacySupport.available_at(
        60_000_000,
        0.75,
        legacy,
    )

    active = d3.adapter_direction_from_support(
        policy_id=policy_id,
        support=support,
    )

    assert active == direction

    integrated = (
        d3.decision_from_active_adapter_direction(
            policy_id=policy_id,
            state=state,
            active_direction=active,
        )
    )

    frozen = m5a.decision_at_epoch(
        policy_id=policy_id,
        state=state,
        support=support,
    )

    assert (
        m5a.behavior_signature(integrated)
        == m5a.behavior_signature(frozen)
    )


@pytest.mark.parametrize(
    "policy_id",
    p.POLICY_IDS,
)
def test_all_eight_policies_primary_flat_to_flat(
    policy_id,
):
    result = d3.run_policy_probe(
        policy_id=policy_id,
        day="2026-01-01",
        scenario=m6.PRIMARY_SCENARIO,
    )

    r = result.kernel

    assert r.policy_id == policy_id
    assert r.terminal_flat is True
    assert r.terminal_position == pytest.approx(0.0)

    assert r.maker_fill.fill is not None
    assert r.taker_fill.fill is not None

    assert r.maker_fill.fill.liquidity == "MAKER"
    assert r.taker_fill.fill.liquidity == "TAKER"

    assert r.maker_fill.fill.qty == pytest.approx(
        p.BASE_ORDER_QTY
    )

    assert r.taker_fill.fill.qty == pytest.approx(
        p.BASE_ORDER_QTY
    )

    assert r.flatten_decision_local_ns > (
        r.first_nonzero_inventory_local_ns
    )

    age = (
        r.flatten_decision_local_ns
        - r.first_nonzero_inventory_local_ns
    ) / 1_000_000_000.0

    assert age >= p.INVENTORY_TIMEOUT_S
    assert age < p.INVENTORY_TIMEOUT_S + 1.0

    assert r.cancel_requests >= 1
    assert r.submit_requests >= 1
    assert r.policy_epochs >= 60


@pytest.mark.parametrize(
    "policy_id",
    p.POLICY_IDS,
)
def test_all_eight_policies_stress_flat_to_flat(
    policy_id,
):
    result = d3.run_policy_probe(
        policy_id=policy_id,
        day="2026-01-01",
        scenario=m6.STRESS_SCENARIO,
    )

    r = result.kernel

    assert r.terminal_flat is True
    assert r.terminal_position == pytest.approx(0.0)

    assert r.maker_fill.fill is not None
    assert r.taker_fill.fill is not None


def test_m03_uses_dynamic_simulator_l1_obi():
    result = d3.run_policy_probe(
        policy_id="M03",
    )

    first = result.trace[0]

    assert first.best_bid_tick == 1000
    assert first.best_ask_tick == 1003

    assert first.l1_obi == pytest.approx(
        (20.0 - 1.0) / (20.0 + 1.0)
    )

    assert first.decision.reference_shift_ticks == 2
    assert first.decision.bid_target_tick == 1000
    assert first.decision.ask_target_tick == 1005


def test_m04_uses_dynamic_simulator_microprice():
    result = d3.run_policy_probe(
        policy_id="M04",
    )

    first = result.trace[0]

    assert first.microprice_shift_ticks == 1
    assert first.decision.reference_shift_ticks == 1

    assert first.decision.bid_target_tick == 1000
    assert first.decision.ask_target_tick == 1004


def test_m05_uses_only_causal_one_second_trade_flow():
    result = d3.run_policy_probe(
        policy_id="M05",
    )

    before = result.trace[0]

    assert before.trade_flow_imbalance == pytest.approx(
        0.0
    )

    flow_rows = tuple(
        x
        for x in result.trace
        if x.trade_flow_imbalance <= -0.80
    )

    assert len(flow_rows) >= 1

    first_flow = flow_rows[0]

    assert first_flow.local_timestamp_ns == (
        d3.day_start_ns("2026-01-01")
        + 3_000_000_000
    )

    assert first_flow.decision.bid_enabled is False

    later = tuple(
        x
        for x in result.trace
        if x.local_timestamp_ns
        >= (
            d3.day_start_ns("2026-01-01")
            + 4_000_000_000
        )
        and not x.decision.force_flatten
    )

    assert later
    assert all(
        x.trade_flow_imbalance == pytest.approx(0.0)
        for x in later
    )


def test_m08_queue_preserve_hysteresis_is_exact():
    state = _market_state(
        inventory=0.001,
    )

    d08 = p.policy_decision(
        "M08",
        state,
    )

    d02 = p.policy_decision(
        "M02",
        state,
    )

    assert d08.bid_target_tick == 999
    assert d02.bid_target_tick == 999

    keep = p.maintenance_intent(
        "M08",
        "bid",
        1000,
        d08,
        best_bid_tick=1000,
        best_ask_tick=1003,
    )

    cancel = p.maintenance_intent(
        "M02",
        "bid",
        1000,
        d02,
        best_bid_tick=1000,
        best_ask_tick=1003,
    )

    assert keep.action == "KEEP"
    assert keep.cancel is False

    assert cancel.action == "CANCEL"
    assert cancel.cancel is True


@pytest.mark.parametrize(
    "policy_id",
    ("M06", "M07"),
)
@pytest.mark.parametrize(
    "day",
    (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
    ),
)
def test_jan_mar_m06_m07_are_base_only(
    policy_id,
    day,
):
    result = d3.run_policy_probe(
        policy_id=policy_id,
        day=day,
    )

    nonflat_modes = {
        row.adapter_mode
        for row in result.trace
        if not row.decision.force_flatten
    }

    assert nonflat_modes == {
        m5b.MODE_BASE_ONLY
    }

    assert result.adapter_candidate_epochs == 0
    assert result.legacy_state_queries == 0
    assert result.exact_minute_identity_checks == 0

    assert all(
        row.active_adapter_direction == ABSTAIN
        for row in result.trace
    )


@pytest.mark.parametrize(
    "policy_id",
    ("M06", "M07"),
)
def test_apr_joint_support_applies_adapter_then_no_alpha_update(
    policy_id,
):
    day = "2026-04-01"

    a0, legacy = (
        d3.synthetic_joint_support_inputs(
            policy_id=policy_id,
            day=day,
            direction=LONG,
            p_touch=0.75,
        )
    )

    result = d3.run_policy_probe(
        policy_id=policy_id,
        day=day,
        a0_index=a0,
        legacy_index=legacy,
    )

    minute = _trace_at(
        result,
        _minute_ns(day),
    )

    second_after = _trace_at(
        result,
        _minute_ns(day)
        + 1_000_000_000,
    )

    assert minute.adapter_mode == (
        m5b.MODE_APPLY_ADAPTER
    )

    assert minute.active_adapter_direction == LONG

    assert minute.decision.ask_target_tick == 1004

    assert second_after.adapter_mode == (
        m5b.MODE_NO_ALPHA_UPDATE
    )

    # Direction execution-state persists; probability does not.
    assert (
        second_after.active_adapter_direction
        == LONG
    )

    assert second_after.decision.ask_target_tick == 1004

    assert result.adapter_candidate_epochs == 1
    assert result.legacy_state_queries == 1
    assert result.exact_minute_identity_checks == 1


def test_intermediate_seconds_never_query_a0(
    monkeypatch,
):
    day = "2026-04-01"

    a0, legacy = (
        d3.synthetic_joint_support_inputs(
            policy_id="M06",
            day=day,
            direction=LONG,
        )
    )

    calls = []

    original = m5a.ExactA0ScoreIndex.exact

    def counted(self, timestamp_us):
        calls.append(int(timestamp_us))
        return original(
            self,
            timestamp_us,
        )

    monkeypatch.setattr(
        m5a.ExactA0ScoreIndex,
        "exact",
        counted,
    )

    result = d3.run_policy_probe(
        policy_id="M06",
        day=day,
        a0_index=a0,
        legacy_index=legacy,
    )

    assert calls == [
        _minute_us(day)
    ]

    assert result.legacy_state_queries == 1

    intermediate = tuple(
        row
        for row in result.trace
        if (
            row.local_timestamp_ns
            > _minute_ns(day)
            and
            row.local_timestamp_ns
            < _minute_ns(day)
            + 3_000_000_000
        )
    )

    assert intermediate
    assert all(
        row.adapter_mode
        == m5b.MODE_NO_ALPHA_UPDATE
        for row in intermediate
        if not row.decision.force_flatten
    )


def test_missing_exact_a0_row_falls_back_to_m02():
    day = "2026-04-01"

    # Legitimate A0 index exists, but only at the next exact minute.
    a0 = m5a.ExactA0ScoreIndex(
        day=day,
        points=(
            m5a.A0ScorePoint(
                d3.day_start_us(day)
                + 120_000_000,
                0.75,
            ),
        ),
    )

    legacy = d3.SyntheticLegacyStateIndex(
        day=day,
        points=(
            d3.SyntheticLegacyStatePoint(
                _minute_us(day),
                d3.synthetic_legacy_state(
                    policy_id="M06",
                    direction=LONG,
                ),
            ),
        ),
    )

    result = d3.run_policy_probe(
        policy_id="M06",
        day=day,
        a0_index=a0,
        legacy_index=legacy,
    )

    minute = _trace_at(
        result,
        _minute_ns(day),
    )

    assert minute.adapter_mode == (
        m5b.MODE_FALLBACK_TO_M02
    )

    assert minute.active_adapter_direction == ABSTAIN
    assert minute.decision.ask_target_tick == 1003

    assert result.exact_minute_identity_checks == 1


def test_missing_causal_legacy_state_falls_back_to_m02():
    day = "2026-04-01"

    a0, _ = (
        d3.synthetic_joint_support_inputs(
            policy_id="M07",
            day=day,
            direction=LONG,
        )
    )

    legacy = d3.SyntheticLegacyStateIndex(
        day=day,
        points=(),
    )

    result = d3.run_policy_probe(
        policy_id="M07",
        day=day,
        a0_index=a0,
        legacy_index=legacy,
    )

    minute = _trace_at(
        result,
        _minute_ns(day),
    )

    assert minute.adapter_mode == (
        m5b.MODE_FALLBACK_TO_M02
    )

    assert minute.active_adapter_direction == ABSTAIN
    assert minute.decision.ask_target_tick == 1003

    assert result.legacy_state_queries == 1
    assert result.exact_minute_identity_checks == 1


def test_low_probability_does_not_create_adapter_direction():
    day = "2026-04-01"

    a0, legacy = (
        d3.synthetic_joint_support_inputs(
            policy_id="M06",
            day=day,
            direction=LONG,
            p_touch=0.25,
        )
    )

    result = d3.run_policy_probe(
        policy_id="M06",
        day=day,
        a0_index=a0,
        legacy_index=legacy,
    )

    minute = _trace_at(
        result,
        _minute_ns(day),
    )

    assert minute.adapter_mode == (
        m5b.MODE_APPLY_ADAPTER
    )

    assert minute.active_adapter_direction == ABSTAIN
    assert minute.decision.ask_target_tick == 1003

    assert result.exact_minute_identity_checks == 1


def test_adapter_inputs_rejected_for_nonadapter_policy():
    a0, legacy = (
        d3.synthetic_joint_support_inputs(
            policy_id="M06",
        )
    )

    with pytest.raises(
        d3.PolicyIntegrationError,
        match="adapter_input_for_nonadapter_policy",
    ):
        d3.run_policy_probe(
            policy_id="M03",
            day="2026-04-01",
            a0_index=a0,
            legacy_index=legacy,
        )

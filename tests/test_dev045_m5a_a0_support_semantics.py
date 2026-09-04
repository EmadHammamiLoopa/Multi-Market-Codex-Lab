from __future__ import annotations

import pytest

from multimarket.dev044_t0_strategy_contract import StrategyState
from multimarket.dev045_m3_policy import MarketState
from multimarket.dev045_m5a_a0_support_semantics import (
    A0_EXACT_SUPPORT_DAYS,
    A0_UNAVAILABLE_DAYS,
    AUTHORIZED_DAYS,
    A0LegacySupport,
    A0ScorePoint,
    ExactA0ScoreIndex,
    FUTURE_INFORMATION_ENABLED,
    HISTORICAL_FILE_IO_ENABLED,
    HISTORICAL_PNL_ENABLED,
    HISTORICAL_REPLAY_EXECUTION_ENABLED,
    LIVE_TRADING_AUTHORIZED,
    MARKET_EVENT,
    MARKET_EVENT_REEVALUATES_POLICY,
    M3_COMPATIBILITY_SENTINEL,
    M3_COMPATIBILITY_SENTINEL_IS_PREDICTION,
    MODEL_SELECTION,
    POLICY_DECISION_EPOCH,
    PROBABILITY_BACKFILL_ENABLED,
    PROBABILITY_FORWARD_FILL_ENABLED,
    PROBABILITY_INTERPOLATION_ENABLED,
    PROMOTION_GATE,
    RESCUE_AUTHORIZATION,
    DIAGNOSTIC_ONLY,
    M5ASupportError,
    behavior_signature,
    bind_support_to_m3,
    decision_at_epoch,
    resolve_joint_support,
)


def _legacy_state() -> StrategyState:
    return StrategyState(
        ret_8_bps=0.0,
        ret_32_bps=0.0,
        ema_fast_minus_slow_bps=0.0,
        breakout_up_bps=0.0,
        breakout_down_bps=0.0,
        rv_ratio_8_to_32=1.0,
        price_z_32=0.0,
        microprice_disp_bps=0.0,
        price_minus_fair_bps=0.0,
        obi_l1=0.0,
        obi_l5=0.0,
        obi_l20=0.0,
        weighted_obi=0.0,
        ofi_1s=0.0,
        ofi_16s=0.0,
        ofi_32s=0.0,
        trade_imbalance_1s=0.0,
        trade_imbalance_16s=0.0,
        depletion_pressure=0.0,
        cancellation_pressure=0.0,
        event_intensity_1s=0.0,
        event_intensity_8s=0.0,
        liquidity_shock_direction=0,
        liquidity_recovery_fraction=0.0,
        mid_price=100.0,
        round_level=100.0,
        round_distance_bps=0.0,
        toxicity=0.0,
        spread_bps=1.0,
    )


def _depth_case(case: int):
    ticks = range(994, 1009)

    if case == 0:
        bid = {t: 10.0 for t in ticks}
        ask = {t: 10.0 for t in ticks}
    elif case == 1:
        bid = {t: 0.2 + (t % 5) * 0.5 for t in ticks}
        ask = {t: 8.0 - (t % 5) * 0.7 for t in ticks}
    elif case == 2:
        bid = {t: 12.0 - (t % 4) * 2.0 for t in ticks}
        ask = {t: 0.3 + (t % 4) * 0.4 for t in ticks}
    else:
        raise AssertionError(case)

    return bid, ask


def _market_state(inventory: float, age: float, depth_case: int) -> MarketState:
    bid, ask = _depth_case(depth_case)

    return MarketState(
        best_bid_tick=1000,
        best_ask_tick=1002,
        bid_depth_qty=bid,
        ask_depth_qty=ask,
        inventory=inventory,
        inventory_age_s=age,
        aggressive_buy_qty_1s=0.7,
        aggressive_sell_qty_1s=0.3,
        legacy_state=None,
        a0_p_touch=0.0,
    )


def test_execution_surfaces_remain_closed():
    assert HISTORICAL_FILE_IO_ENABLED is False
    assert HISTORICAL_REPLAY_EXECUTION_ENABLED is False
    assert HISTORICAL_PNL_ENABLED is False
    assert FUTURE_INFORMATION_ENABLED is False
    assert LIVE_TRADING_AUTHORIZED is False

    assert PROBABILITY_FORWARD_FILL_ENABLED is False
    assert PROBABILITY_INTERPOLATION_ENABLED is False
    assert PROBABILITY_BACKFILL_ENABLED is False

    assert MARKET_EVENT_REEVALUATES_POLICY is False


def test_frozen_support_calendar_is_exact():
    assert AUTHORIZED_DAYS == (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    )

    assert A0_UNAVAILABLE_DAYS == (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
    )

    assert A0_EXACT_SUPPORT_DAYS == (
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    )


def test_exact_index_never_forward_fills_or_interpolates():
    idx = ExactA0ScoreIndex(
        day="2026-04-01",
        points=(
            A0ScorePoint(1_000_000, 0.61),
            A0ScorePoint(1_250_000, 0.72),
            A0ScorePoint(2_000_000, 0.83),
        ),
    )

    assert idx.exact(1_000_000) == 0.61
    assert idx.exact(1_250_000) == 0.72
    assert idx.exact(2_000_000) == 0.83

    assert idx.exact(999_999) is None
    assert idx.exact(1_000_001) is None
    assert idx.exact(1_125_000) is None
    assert idx.exact(1_999_999) is None
    assert idx.exact(2_000_001) is None


@pytest.mark.parametrize("day", A0_UNAVAILABLE_DAYS)
def test_jan_mar_are_explicitly_unavailable(day):
    out = resolve_joint_support(
        day=day,
        decision_timestamp_us=10_000,
        a0_index=None,
        causal_legacy_state=_legacy_state(),
    )

    assert out.available is False
    assert out.p_touch is None
    assert out.legacy_state is None


def test_jan_mar_reject_injected_a0_index():
    idx = ExactA0ScoreIndex(
        day="2026-04-01",
        points=(A0ScorePoint(10_000, 0.9),),
    )

    with pytest.raises(M5ASupportError, match="a0_index_for_frozen_unavailable_day"):
        resolve_joint_support(
            day="2026-01-01",
            decision_timestamp_us=10_000,
            a0_index=idx,
            causal_legacy_state=_legacy_state(),
        )


def test_joint_support_requires_exact_a0_and_causal_state():
    idx = ExactA0ScoreIndex(
        day="2026-04-01",
        points=(
            A0ScorePoint(10_000, 0.51),
            A0ScorePoint(20_000, 0.73),
        ),
    )

    no_exact = resolve_joint_support(
        day="2026-04-01",
        decision_timestamp_us=15_000,
        a0_index=idx,
        causal_legacy_state=_legacy_state(),
    )

    assert no_exact.available is False
    assert no_exact.p_touch is None
    assert no_exact.legacy_state is None

    no_state = resolve_joint_support(
        day="2026-04-01",
        decision_timestamp_us=10_000,
        a0_index=idx,
        causal_legacy_state=None,
    )

    assert no_state.available is False
    assert no_state.p_touch is None
    assert no_state.legacy_state is None

    valid = resolve_joint_support(
        day="2026-04-01",
        decision_timestamp_us=10_000,
        a0_index=idx,
        causal_legacy_state=_legacy_state(),
    )

    assert valid.available is True
    assert valid.p_touch == 0.51
    assert valid.legacy_state is not None


def test_half_valid_support_is_forbidden():
    with pytest.raises(M5ASupportError, match="half_valid_support"):
        A0LegacySupport(
            decision_timestamp_us=1,
            available=True,
            p_touch=0.7,
            legacy_state=None,
        )

    with pytest.raises(M5ASupportError, match="half_valid_support"):
        A0LegacySupport(
            decision_timestamp_us=1,
            available=False,
            p_touch=0.7,
            legacy_state=_legacy_state(),
        )


def test_m3_unavailable_boundary_uses_nonsemantic_sentinel_only():
    base = _market_state(0.0, 0.0, 0)
    support = A0LegacySupport.unavailable(123)

    bound = bind_support_to_m3(base, support)

    assert support.available is False
    assert support.p_touch is None
    assert support.legacy_state is None

    assert bound.legacy_state is None
    assert bound.a0_p_touch == M3_COMPATIBILITY_SENTINEL
    assert M3_COMPATIBILITY_SENTINEL == 0.0
    assert M3_COMPATIBILITY_SENTINEL_IS_PREDICTION is False


def test_market_event_cannot_trigger_policy_evaluation():
    state = _market_state(0.0, 0.0, 0)
    support = A0LegacySupport.unavailable(123)

    with pytest.raises(
        M5ASupportError,
        match="policy_evaluation_forbidden_on_market_event",
    ):
        decision_at_epoch(
            policy_id="M06",
            state=state,
            support=support,
            clock_kind=MARKET_EVENT,
        )

    decision_at_epoch(
        policy_id="M06",
        state=state,
        support=support,
        clock_kind=POLICY_DECISION_EPOCH,
    )


@pytest.mark.parametrize(
    "inventory",
    (-0.003, -0.002, -0.001, 0.0, 0.001, 0.002, 0.003),
)
@pytest.mark.parametrize(
    "age",
    (0.0, 1.0, 59.999, 60.0, 120.0),
)
@pytest.mark.parametrize("depth_case", (0, 1, 2))
@pytest.mark.parametrize("adapter_policy", ("M06", "M07"))
def test_unavailable_adapter_is_behaviorally_identical_to_m02(
    inventory,
    age,
    depth_case,
    adapter_policy,
):
    state = _market_state(inventory, age, depth_case)
    support = A0LegacySupport.unavailable(999)

    base = decision_at_epoch(
        policy_id="M02",
        state=state,
        support=support,
    )

    adapter = decision_at_epoch(
        policy_id=adapter_policy,
        state=state,
        support=support,
    )

    assert behavior_signature(adapter) == behavior_signature(base)


def test_diagnostic_is_frozen_non_promotional():
    assert DIAGNOSTIC_ONLY is True
    assert PROMOTION_GATE is False
    assert MODEL_SELECTION is False
    assert RESCUE_AUTHORIZATION is False

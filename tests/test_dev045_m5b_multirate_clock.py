from __future__ import annotations

import pytest

from multimarket.dev044_t0_strategy_contract import StrategyState
from multimarket.dev045_m5a_a0_support_semantics import (
    A0ScorePoint,
    ExactA0ScoreIndex,
)
from multimarket.dev045_m5b_multirate_clock import (
    ADAPTER_CANDIDATE_STEP_US,
    BASE_MAKER_DECISION_STEP_US,
    BASE_MAKER_DECISION_EPOCH,
    LEGACY_ADAPTER_DECISION_EPOCH,
    MARKET_EVENT,
    MODE_APPLY_ADAPTER,
    MODE_BASE_ONLY,
    MODE_FALLBACK_TO_M02,
    MODE_NO_ALPHA_UPDATE,
    PROBABILITY_BACKFILL_ENABLED,
    PROBABILITY_CARRY_ENABLED,
    PROBABILITY_FORWARD_FILL_ENABLED,
    PROBABILITY_INTERPOLATION_ENABLED,
    INTERMEDIATE_SECOND_CLEARS_ADAPTER,
    INTERMEDIATE_SECOND_MEANS_A0_UNAVAILABLE,
    INTERMEDIATE_SECOND_QUERIES_A0,
    HISTORICAL_FILE_IO_ENABLED,
    HISTORICAL_PNL_ENABLED,
    HISTORICAL_REPLAY_EXECUTION_ENABLED,
    LIVE_TRADING_AUTHORIZED,
    M5BClockError,
    is_adapter_candidate_epoch,
    is_base_maker_decision_epoch,
    market_event_policy_evaluation_allowed,
    resolve_adapter_clock,
    scheduled_clock_kind,
    validate_a0_index_clock,
)


def _state() -> StrategyState:
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


def _index():
    return ExactA0ScoreIndex(
        day="2026-04-01",
        points=(
            A0ScorePoint(60_000_000, 0.75),
            A0ScorePoint(180_000_000, 0.25),
        ),
    )


def test_execution_surfaces_closed():
    assert HISTORICAL_FILE_IO_ENABLED is False
    assert HISTORICAL_REPLAY_EXECUTION_ENABLED is False
    assert HISTORICAL_PNL_ENABLED is False
    assert LIVE_TRADING_AUTHORIZED is False

    assert PROBABILITY_FORWARD_FILL_ENABLED is False
    assert PROBABILITY_INTERPOLATION_ENABLED is False
    assert PROBABILITY_BACKFILL_ENABLED is False
    assert PROBABILITY_CARRY_ENABLED is False


def test_frozen_multirate_steps():
    assert BASE_MAKER_DECISION_STEP_US == 1_000_000
    assert ADAPTER_CANDIDATE_STEP_US == 60_000_000


@pytest.mark.parametrize(
    ("timestamp_us", "expected"),
    (
        (0, True),
        (250_000, False),
        (999_999, False),
        (1_000_000, True),
        (1_250_000, False),
        (59_000_000, True),
        (60_000_000, True),
        (61_000_000, True),
    ),
)
def test_base_maker_clock_exact_seconds(
    timestamp_us,
    expected,
):
    assert (
        is_base_maker_decision_epoch(timestamp_us)
        is expected
    )


@pytest.mark.parametrize(
    ("timestamp_us", "expected"),
    (
        (0, True),
        (1_000_000, False),
        (59_000_000, False),
        (60_000_000, True),
        (61_000_000, False),
        (119_000_000, False),
        (120_000_000, True),
    ),
)
def test_apr_adapter_candidates_are_exact_minutes(
    timestamp_us,
    expected,
):
    assert is_adapter_candidate_epoch(
        day="2026-04-01",
        timestamp_us=timestamp_us,
    ) is expected


@pytest.mark.parametrize(
    "day",
    (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
    ),
)
def test_jan_mar_have_no_adapter_candidate_clock(day):
    assert is_adapter_candidate_epoch(
        day=day,
        timestamp_us=60_000_000,
    ) is False


def test_clock_kinds_are_separate():
    assert scheduled_clock_kind(
        day="2026-04-01",
        timestamp_us=60_000_000,
    ) == LEGACY_ADAPTER_DECISION_EPOCH

    assert scheduled_clock_kind(
        day="2026-04-01",
        timestamp_us=61_000_000,
    ) == BASE_MAKER_DECISION_EPOCH

    assert scheduled_clock_kind(
        day="2026-04-01",
        timestamp_us=61_250_000,
    ) == MARKET_EVENT


def test_market_event_never_triggers_policy_evaluation():
    assert market_event_policy_evaluation_allowed() is False


def test_a0_index_clock_must_be_exact_minute():
    validate_a0_index_clock(_index())

    bad = ExactA0ScoreIndex(
        day="2026-04-01",
        points=(
            A0ScorePoint(60_250_000, 0.5),
        ),
    )

    with pytest.raises(
        M5BClockError,
        match="a0_point_not_exact_minute",
    ):
        validate_a0_index_clock(bad)


def test_exact_minute_with_joint_support_applies_adapter():
    out = resolve_adapter_clock(
        day="2026-04-01",
        timestamp_us=60_000_000,
        a0_index=_index(),
        causal_legacy_state=_state(),
    )

    assert out.mode == MODE_APPLY_ADAPTER
    assert out.support is not None
    assert out.support.available is True
    assert out.support.p_touch == 0.75


def test_intermediate_second_is_no_alpha_update_not_fallback():
    out = resolve_adapter_clock(
        day="2026-04-01",
        timestamp_us=61_000_000,
        a0_index=_index(),
        causal_legacy_state=None,
    )

    assert out.mode == MODE_NO_ALPHA_UPDATE
    assert out.support is None

    assert INTERMEDIATE_SECOND_QUERIES_A0 is False
    assert INTERMEDIATE_SECOND_MEANS_A0_UNAVAILABLE is False
    assert INTERMEDIATE_SECOND_CLEARS_ADAPTER is False


def test_no_probability_carry_from_previous_minute():
    first = resolve_adapter_clock(
        day="2026-04-01",
        timestamp_us=60_000_000,
        a0_index=_index(),
        causal_legacy_state=_state(),
    )

    next_second = resolve_adapter_clock(
        day="2026-04-01",
        timestamp_us=61_000_000,
        a0_index=_index(),
        causal_legacy_state=None,
    )

    assert first.support is not None
    assert first.support.p_touch == 0.75

    assert next_second.mode == MODE_NO_ALPHA_UPDATE
    assert next_second.support is None


def test_missing_exact_support_at_candidate_minute_falls_back():
    out = resolve_adapter_clock(
        day="2026-04-01",
        timestamp_us=120_000_000,
        a0_index=_index(),
        causal_legacy_state=_state(),
    )

    assert out.mode == MODE_FALLBACK_TO_M02
    assert out.support is not None
    assert out.support.available is False
    assert out.support.p_touch is None
    assert out.support.legacy_state is None


def test_missing_causal_state_at_supported_minute_falls_back():
    out = resolve_adapter_clock(
        day="2026-04-01",
        timestamp_us=60_000_000,
        a0_index=_index(),
        causal_legacy_state=None,
    )

    assert out.mode == MODE_FALLBACK_TO_M02
    assert out.support is not None
    assert out.support.available is False


@pytest.mark.parametrize(
    "day",
    (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
    ),
)
def test_jan_mar_are_base_only(day):
    out = resolve_adapter_clock(
        day=day,
        timestamp_us=61_000_000,
        a0_index=None,
        causal_legacy_state=_state(),
    )

    assert out.mode == MODE_BASE_ONLY
    assert out.support is None


def test_non_second_adapter_resolution_is_forbidden():
    with pytest.raises(
        M5BClockError,
        match="requires_base_epoch",
    ):
        resolve_adapter_clock(
            day="2026-04-01",
            timestamp_us=60_250_000,
            a0_index=_index(),
            causal_legacy_state=_state(),
        )

from __future__ import annotations

from datetime import datetime, timezone
import math
from pathlib import Path

import pytest

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r23_ulp_aware_flatten_cash_conservation as f
from multimarket import dev045_d6r23_ulp_aware_flatten_cash_qualification as q
from multimarket import dev045_m4_m6_binding as binding
from multimarket.dev045_m4_adapter import ReplayOrderView


def ns(day: str, hour: int, minute: int, second: int) -> int:
    dt = datetime.fromisoformat(day).replace(
        hour=hour,
        minute=minute,
        second=second,
        tzinfo=timezone.utc,
    )
    return int(dt.timestamp() * 1_000_000_000)


def forensic_view() -> ReplayOrderView:
    return ReplayOrderView(
        order_id=5126,
        status=binding.HFT_FILLED,
        side=binding.HFT_BUY,
        price_tick=768001,
        exec_price_tick=768001,
        exec_qty=0.001,
        leaves_qty=0.0,
        exch_timestamp=1769977847750000000,
        local_timestamp=1769977847500000000,
    )


def forensic_before() -> binding.ReplayStateView:
    return binding.ReplayStateView(
        position=-0.001,
        balance=-91.63360000000398,
        fee=486.9617741999963,
        num_trades=23039,
        trading_volume=23.341000000005522,
        trading_value=1824175.2845999955,
    )


def forensic_after() -> binding.ReplayStateView:
    return binding.ReplayStateView(
        position=0.0,
        balance=-168.43370000000397,
        fee=487.0001742499963,
        num_trades=23040,
        trading_volume=23.342000000005523,
        trading_value=1824252.0846999956,
    )


def test_exact_identity_and_frozen_forensic_lineage():
    assert f.PARENT_D6R22_FREEZE_HEAD == (
        "883a4af9ee4ded6319d68a5306412342c1f6e217"
    )
    assert f.D6R22_RESULT_SHA256 == (
        "a8b55ee5fd5decb3a026393baccad54aa24f1d7d92dfb2a9060b4833def4ccae"
    )
    lineage = q.validate_d6r22_frozen_lineage()
    assert lineage["classification"] == f.D6R22_CLASSIFICATION
    assert lineage["abs_cash_residual"] > lineage["original_effective_tolerance"]
    assert lineage["abs_cash_residual"] < lineage["endpoint_ulp_budget"]
    q.validate_contract()


def test_semantic_change_scope_is_exactly_one_guard():
    assert f.BINDING_GUARD_CHANGE_SCOPE == "FLATTEN_CASH_CONSERVATION_ONLY"
    assert f.ULP_AWARE_FALLBACK_ENABLED is True
    assert f.ULP_MULTIPLIER == 1.0
    assert f.EXECUTION_SEMANTICS_CHANGED is False
    assert f.STRATEGY_SEMANTICS_CHANGED is False
    assert f.FEE_SEMANTICS_CHANGED is False
    assert f.ECONOMIC_ACCOUNTING_CHANGED is False
    assert f.RETRY_SEMANTICS_CHANGED is False
    assert f.AUTOMATIC_RETRY is False
    assert f.LIVE_TRADING_AUTHORIZED is False


def test_forensic_real_failure_is_rejected_by_frozen_binding():
    with pytest.raises(
        binding.M4M6BindingError,
        match="flatten_cash_conservation",
    ):
        f.FROZEN_BIND_FORCED_FLATTEN(
            forensic_view(),
            before=forensic_before(),
            after=forensic_after(),
            policy_id="M01",
            day="2026-02-01",
        )


def test_forensic_real_failure_is_inside_exact_one_ulp_budget():
    d = f.cash_conservation_decision(
        forensic_view(),
        before=forensic_before(),
        after=forensic_after(),
    )

    assert d.cash_delta == pytest.approx(
        -76.80009999999999, rel=0.0, abs=0.0
    )
    assert d.expected_cash_delta == pytest.approx(
        -76.80010000010952, rel=0.0, abs=0.0
    )
    assert d.abs_residual == pytest.approx(
        1.0953726814477704e-10, rel=0.0, abs=0.0
    )
    assert d.original_effective_tolerance == pytest.approx(
        7.680010000010953e-11, rel=0.0, abs=0.0
    )
    assert d.endpoint_ulp_budget == pytest.approx(
        4.657039198718849e-10, rel=0.0, abs=0.0
    )
    assert d.allowed_tolerance == d.endpoint_ulp_budget
    assert d.accepted_by_original_tolerance is False
    assert d.accepted_by_ulp_fallback is True
    assert d.abs_residual / d.endpoint_ulp_budget == pytest.approx(
        0.23520795825577492, rel=0.0, abs=1e-16
    )


def test_ulp_aware_binding_accepts_forensic_case_without_changing_fill_economics():
    sink = []
    event = f.bind_forced_flatten_from_state_delta_ulp_aware(
        forensic_view(),
        before=forensic_before(),
        after=forensic_after(),
        policy_id="M01",
        day="2026-02-01",
        diagnostic_sink=sink,
    )

    assert event.kind == binding.FILL
    assert event.side == "BUY"
    assert event.liquidity == binding.TAKER
    assert event.fill is not None
    assert event.fill.qty == pytest.approx(
        0.0010000000000012221, rel=0.0, abs=1e-15
    )
    assert event.executed_quote_notional == pytest.approx(
        76.80010000010952, rel=0.0, abs=1e-12
    )
    assert event.fill.price == pytest.approx(
        event.executed_quote_notional / event.fill.qty,
        rel=1e-15,
        abs=0.0,
    )
    assert len(sink) == 1
    assert sink[0]["accepted_by_ulp_fallback"] is True


def test_true_cash_mismatch_still_fails_closed_far_above_ulp_budget():
    before = forensic_before()
    after = binding.ReplayStateView(
        position=0.0,
        balance=-168.40,
        fee=487.0001742499963,
        num_trades=23040,
        trading_volume=23.342000000005523,
        trading_value=1824252.0846999956,
    )

    d = f.cash_conservation_decision(
        forensic_view(), before=before, after=after
    )
    assert d.abs_residual > 0.03
    assert d.abs_residual > d.allowed_tolerance * 1_000_000
    assert d.accepted_by_ulp_fallback is False

    with pytest.raises(
        binding.M4M6BindingError,
        match="flatten_cash_conservation",
    ):
        f.bind_forced_flatten_from_state_delta_ulp_aware(
            forensic_view(),
            before=before,
            after=after,
            policy_id="M01",
            day="2026-02-01",
        )


def test_non_cash_binding_errors_pass_through_unchanged():
    bad_after = binding.ReplayStateView(
        position=0.0,
        balance=-168.43370000000397,
        fee=487.0001742499963,
        num_trades=23039,
        trading_volume=23.342000000005523,
        trading_value=1824252.0846999956,
    )
    with pytest.raises(
        binding.M4M6BindingError,
        match="flatten_trade_count_delta",
    ):
        f.bind_forced_flatten_from_state_delta_ulp_aware(
            forensic_view(),
            before=forensic_before(),
            after=bad_after,
            policy_id="M01",
            day="2026-02-01",
        )


def test_context_manager_restores_exact_frozen_binding():
    original = base.binding.bind_forced_flatten_from_state_delta
    sink = []
    with f.use_ulp_aware_flatten_binding(diagnostic_sink=sink):
        assert base.binding.bind_forced_flatten_from_state_delta is not original
        event = base.binding.bind_forced_flatten_from_state_delta(
            forensic_view(),
            before=forensic_before(),
            after=forensic_after(),
            policy_id="M01",
            day="2026-02-01",
        )
        assert event.fill is not None
    assert base.binding.bind_forced_flatten_from_state_delta is original
    assert len(sink) == 1


def test_kernel_is_exact_q8_successor():
    assert issubclass(
        f.UlpAwareFlattenCashContinuousHistoricalPolicyKernel,
        f.q8.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel,
    )


def test_qualification_is_closed_and_virgin_during_implementation(monkeypatch):
    monkeypatch.delenv(q.AUTHORIZATION_ENV, raising=False)
    assert q.QUALIFICATION_AUTHORIZED_BY_DEFAULT is False
    assert q.QUALIFICATION_ATTEMPT_CONSUMED is False
    assert q.AUTOMATIC_RETRY is False
    assert q.RERUN_AFTER_ATTEMPT_CONSUMPTION is False
    assert q.ECONOMIC_ARENA_AUTHORIZED is False
    assert q.LIVE_TRADING_AUTHORIZED is False
    assert q.RESULT_PATH.exists() is False
    assert q.FAILURE_PATH.exists() is False
    assert q.RESULT_ROOT.exists() is False
    with pytest.raises(q.D6R23QualificationError, match="execution_gate_closed"):
        q._require_authorization(
            authorization_token=q.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )


def test_implementation_guards_prove_no_real_execution_or_economics():
    assert q.REAL_HISTORICAL_EXECUTION_DURING_IMPLEMENTATION is False
    assert q.HISTORICAL_SOURCE_OPENED_DURING_IMPLEMENTATION is False
    assert q.HISTORICAL_SOURCE_HASHED_DURING_IMPLEMENTATION is False
    assert q.ECONOMIC_ARENA_EXECUTED_DURING_IMPLEMENTATION is False
    assert q.D6R22_RERUN_DURING_IMPLEMENTATION is False
    assert q.D6R21_RERUN_DURING_IMPLEMENTATION is False
    assert q.Q8_RERUN_DURING_IMPLEMENTATION is False


def test_runner_has_no_economic_arena_call_or_retry_path():
    source = Path(q.__file__).read_text(encoding="utf-8")
    fix_source = Path(f.__file__).read_text(encoding="utf-8")
    assert "run_economic_arena(" not in source
    assert "run_economic_arena(" not in fix_source
    assert "ULP_MULTIPLIER = 1.0" in fix_source
    assert "AUTOMATIC_RETRY = False" in fix_source
    assert "FLATTEN_CASH_CONSERVATION_ONLY" in fix_source

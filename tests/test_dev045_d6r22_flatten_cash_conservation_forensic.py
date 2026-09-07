from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r22_flatten_cash_conservation_forensic as f
from multimarket import dev045_d6r22_flatten_cash_conservation_forensic_runner as r
from multimarket import dev045_m4_m6_binding as binding


def state(*, position, balance, fee, trades, volume, value):
    return binding.ReplayStateView(
        position=position,
        balance=balance,
        fee=fee,
        num_trades=trades,
        trading_volume=volume,
        trading_value=value,
    )


def view(*, side=binding.HFT_SELL):
    return SimpleNamespace(
        order_id=4901,
        status=binding.HFT_FILLED,
        side=side,
        exec_qty=0.001,
        exec_price_tick=1_001_000,
        leaves_qty=0.0,
        exch_timestamp=1769990400000000000,
        local_timestamp=1769990400250000000,
    )


def test_exact_identity_and_target():
    assert f.EXPERIMENT_ID == "DEV045-D6R22-FORENSIC"
    assert f.PARENT_FAILURE_FREEZE_HEAD == (
        "cbbbb0572f3408a787272bd06db4bba276500049"
    )
    assert f.D6R21_EXECUTION_HEAD == (
        "8c0043bb6359fa37147e36fd68c3c2d72243f902"
    )
    assert f.D6R21_FAILURE_SHA256 == (
        "adbbdd39800145121f860ed584641d00e71add896ab5a98defbf8431a914a3c1"
    )
    assert r.TARGET_DAY == "2026-02-01"
    assert r.TARGET_POLICY == "M01"
    assert r.TARGET_SCENARIO == "Q0_PRIMARY_250_250"


def test_frozen_failure_lineage_and_contract():
    lineage = r.validate_frozen_failure_lineage()
    assert lineage["freeze_status"] == "CANONICAL_CONSUMED_FAILURE_FROZEN"
    assert lineage["completed_replays"] == 16
    assert lineage["exception_message"] == "flatten_cash_conservation"
    assert math.isclose(
        lineage["jan_max_replay_trading_value_ulp"],
        1.1641532182693481e-10,
        rel_tol=0.0,
        abs_tol=0.0,
    )
    r.validate_contract()


def test_no_semantic_change_guards():
    assert f.EXECUTION_SEMANTICS_CHANGED is False
    assert f.STRATEGY_SEMANTICS_CHANGED is False
    assert f.BINDING_SEMANTICS_CHANGED is False
    assert f.TOLERANCE_CHANGED is False
    assert f.ECONOMIC_ACCOUNTING_CHANGED is False
    assert f.FLATTEN_RETRY_ENABLED is False
    assert f.AUTOMATIC_RETRY is False
    assert f.LIVE_TRADING_AUTHORIZED is False
    assert r.FORENSIC_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert r.FORENSIC_ATTEMPT_CONSUMED is False
    assert r.AUTOMATIC_RETRY is False
    assert r.RERUN_AFTER_ATTEMPT_CONSUMPTION is False
    assert r.TOLERANCE_CHANGE_AUTHORIZED is False
    assert r.BINDING_CHANGE_AUTHORIZED is False
    assert r.ECONOMIC_ARENA_AUTHORIZED is False
    assert r.LIVE_TRADING_AUTHORIZED is False


def test_authorization_closed_by_default(monkeypatch):
    monkeypatch.delenv(r.AUTHORIZATION_ENV, raising=False)
    with pytest.raises(r.D6R22ForensicError, match="execution_gate_closed"):
        r._require_authorization(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )
    with pytest.raises(r.D6R22ForensicError, match="authorization_environment"):
        r._require_authorization(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )


def test_known_float_subtraction_case_exceeds_original_tolerance_but_is_within_endpoint_ulp_budget():
    before = state(
        position=0.001,
        balance=123456.789,
        fee=1.0,
        trades=10_000,
        volume=500.0,
        value=694000.0,
    )
    after = state(
        position=0.0,
        balance=123556.8890000001,
        fee=1.1,
        trades=10_001,
        volume=500.001,
        value=694100.1,
    )

    d = f.cash_conservation_diagnostics(
        view(side=binding.HFT_SELL),
        before=before,
        after=after,
    )

    assert d["position_conservation_isclose"] is True
    assert d["original_cash_isclose"] is False
    assert d["abs_cash_residual"] == pytest.approx(
        1.1641532182693481e-10,
        rel=0.0,
        abs=0.0,
    )
    assert d["original_effective_tolerance"] < d["abs_cash_residual"]
    assert d["endpoint_ulp_budget"] > d["abs_cash_residual"]
    assert d["abs_residual_over_endpoint_ulp_budget"] < 1.0
    assert d["before_trading_value_ulp"] == pytest.approx(
        f.JAN_MAX_REPLAY_TRADING_VALUE_ULP,
        rel=0.0,
        abs=0.0,
    )


def test_true_cash_mismatch_is_far_larger_than_ulp_budget():
    before = state(
        position=0.001,
        balance=123456.789,
        fee=1.0,
        trades=10_000,
        volume=500.0,
        value=694000.0,
    )
    after = state(
        position=0.0,
        balance=123556.90,
        fee=1.1,
        trades=10_001,
        volume=500.001,
        value=694100.1,
    )

    d = f.cash_conservation_diagnostics(
        view(side=binding.HFT_SELL),
        before=before,
        after=after,
    )

    assert d["original_cash_isclose"] is False
    assert d["abs_cash_residual"] > 0.01
    assert d["abs_residual_over_endpoint_ulp_budget"] > 1_000_000.0


def test_observer_captures_specific_original_exception_and_restores_binding():
    before = state(
        position=0.001,
        balance=123456.789,
        fee=1.0,
        trades=10_000,
        volume=500.0,
        value=694000.0,
    )
    after = state(
        position=0.0,
        balance=123556.8890000001,
        fee=1.1,
        trades=10_001,
        volume=500.001,
        value=694100.1,
    )

    original = base.binding.bind_forced_flatten_from_state_delta
    sink = []

    with f.observe_flatten_cash_binding(
        sink=sink,
        context_factory=lambda: {"marker": "context"},
    ):
        with pytest.raises(binding.M4M6BindingError, match="flatten_cash_conservation"):
            base.binding.bind_forced_flatten_from_state_delta(
                view(side=binding.HFT_SELL),
                before=before,
                after=after,
                policy_id="M01",
                day="2026-02-01",
            )

    assert base.binding.bind_forced_flatten_from_state_delta is original
    assert len(sink) == 1
    record = sink[0]
    assert record["original_exception_message"] == "flatten_cash_conservation"
    assert record["marker"] == "context"
    assert record["execution_semantics_changed"] is False
    assert record["binding_semantics_changed"] is False
    assert record["tolerance_changed"] is False


def test_observer_does_not_swallow_unrelated_binding_error():
    bad_before = state(
        position=0.001,
        balance=0.0,
        fee=0.0,
        trades=1,
        volume=1.0,
        value=100.0,
    )
    bad_after = state(
        position=0.0,
        balance=100.0,
        fee=0.0,
        trades=1,
        volume=1.001,
        value=200.0,
    )
    sink = []

    with f.observe_flatten_cash_binding(sink=sink):
        with pytest.raises(binding.M4M6BindingError, match="flatten_trade_count_delta"):
            base.binding.bind_forced_flatten_from_state_delta(
                view(side=binding.HFT_SELL),
                before=bad_before,
                after=bad_after,
                policy_id="M01",
                day="2026-02-01",
            )

    assert sink == []


def test_forensic_kernel_inherits_exact_q8_execution_kernel():
    assert issubclass(
        f.FlattenCashConservationForensicKernel,
        f.q8.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel,
    )


def test_future_result_surface_is_virgin_during_implementation():
    assert r.RESULT_PATH.exists() is False
    assert r.FAILURE_PATH.exists() is False
    assert r.RESULT_ROOT.exists() is False


def test_runner_source_never_calls_economic_arena_and_has_no_tolerance_edit():
    source = Path(r.__file__).read_text(encoding="utf-8")
    forensic_source = Path(f.__file__).read_text(encoding="utf-8")
    assert "run_economic_arena(" not in source
    assert "run_economic_arena(" not in forensic_source
    assert "rel_tol=1e-12" in forensic_source
    assert "abs_tol=1e-12" in forensic_source
    assert "TOLERANCE_CHANGED = False" in forensic_source
    assert "FLATTEN_RETRY_ENABLED = False" in forensic_source

from __future__ import annotations

from pathlib import Path

import pytest

from multimarket import dev045_d6r21_canonical_runner as d6r21
from multimarket import dev045_d6r23_ulp_aware_flatten_cash_conservation as d6r23
from multimarket import dev045_d6r24_canonical_ulp_aware_runner as r


def test_exact_identity_and_parent_freeze():
    assert r.EXPERIMENT_ID == "DEV045-D6R24"
    assert r.DESIGN_VERSION == (
        "canonical-historical-economic-runner-q8-d6r23-ulp-aware-v1"
    )
    assert r.PARENT_Q1_FREEZE_HEAD == (
        "a62518c15fe08bc028771ef016abb88eebb91130"
    )
    assert r.D6R23_IMPLEMENTATION_HEAD == (
        "a73884294249f77b405f9b0620405f9ed9e3b2fb"
    )


def test_frozen_q1_lineage_is_semantic_qualification_pass():
    lineage = r.validate_d6r23_q1_frozen_lineage()
    assert lineage["classification"] == (
        "SEMANTIC_QUALIFICATION_PASS_POST_VALIDATION_ARTIFACTIZATION_FAILURE"
    )
    assert lineage["semantic_qualification_pass"] is True
    assert lineage["ulp_fallback_observed"] is True
    assert lineage["correct_cycle_count_expression"] == "len(replay.cycles)"
    assert lineage["q1_rerun_authorized"] is False


def test_canonical_matrix_is_exact_d6r21_112_contract():
    assert r.DAY_ORDER == tuple(d6r21.DAY_ORDER)
    assert r.POLICY_ORDER == tuple(d6r21.POLICY_ORDER)
    assert r.SCENARIO_ORDER == tuple(d6r21.SCENARIO_ORDER)
    assert r.REPLAY_ORDER == tuple(d6r21.REPLAY_ORDER)
    assert len(r.DAY_ORDER) == 7
    assert len(r.POLICY_ORDER) == 8
    assert len(r.SCENARIO_ORDER) == 2
    assert len(r.REPLAY_ORDER) == 112
    assert r.EXPECTED_TOTAL_REPLAYS == 112


def test_exact_d6r23_kernel_on_q8_lineage():
    assert r.HISTORICAL_KERNEL is (
        d6r23.UlpAwareFlattenCashContinuousHistoricalPolicyKernel
    )
    assert issubclass(r.HISTORICAL_KERNEL, d6r21.HISTORICAL_KERNEL)
    assert r.Q8_REPLAY_VALIDATOR is d6r21.Q8_REPLAY_VALIDATOR


def test_only_d6r23_cash_guard_semantic_changes():
    assert d6r23.BINDING_GUARD_CHANGE_SCOPE == "FLATTEN_CASH_CONSERVATION_ONLY"
    assert d6r23.ULP_AWARE_FALLBACK_ENABLED is True
    assert d6r23.ULP_MULTIPLIER == 1.0
    assert d6r23.EXECUTION_SEMANTICS_CHANGED is False
    assert d6r23.STRATEGY_SEMANTICS_CHANGED is False
    assert d6r23.FEE_SEMANTICS_CHANGED is False
    assert d6r23.ECONOMIC_ACCOUNTING_CHANGED is False
    assert d6r23.RETRY_SEMANTICS_CHANGED is False
    assert d6r23.AUTOMATIC_RETRY is False
    assert d6r23.LIVE_TRADING_AUTHORIZED is False


def test_attempt_and_environment_guards():
    assert r.CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert r.CANONICAL_ATTEMPT_CONSUMED is False
    assert r.AUTOMATIC_RETRY is False
    assert r.RERUN_AFTER_ATTEMPT_CONSUMPTION is False
    assert r.TUNING_AFTER_FIRST_OUTPUT is False
    assert r.FIRST_HISTORICAL_REPLAY_ENTRY_CONSUMES is True
    assert r.PRE_REPLAY_SOURCE_SHA_FAILURE_CONSUMES is False
    assert r.PRE_REPLAY_SOURCE_OPEN_FAILURE_CONSUMES is False
    assert r.PRE_REPLAY_SUPPORT_FAILURE_CONSUMES is False
    assert r.PRE_REPLAY_VALIDATION_FAILURE_CONSUMES is False
    assert r.NETWORK_ACQUISITION_ENABLED is False
    assert r.RAILWAY_ENABLED is False
    assert r.LIVE_TRADING_AUTHORIZED is False
    assert r.AUG_OPEN_AUTHORIZED is False
    assert r.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r.NON_BTC_OPEN_AUTHORIZED is False


def test_implementation_phase_has_zero_historical_or_economic_execution():
    assert r.REAL_HISTORICAL_EXECUTION_DURING_IMPLEMENTATION is False
    assert r.HISTORICAL_SOURCE_OPENED_DURING_IMPLEMENTATION is False
    assert r.HISTORICAL_SOURCE_HASHED_DURING_IMPLEMENTATION is False
    assert r.ECONOMIC_ARENA_EXECUTED_DURING_IMPLEMENTATION is False
    assert r.D6R23_Q1_RERUN_DURING_IMPLEMENTATION is False
    assert r.D6R22_RERUN_DURING_IMPLEMENTATION is False
    assert r.D6R21_RERUN_DURING_IMPLEMENTATION is False
    assert r.Q8_RERUN_DURING_IMPLEMENTATION is False


def test_authorization_is_closed_by_default(monkeypatch):
    monkeypatch.delenv(r.AUTHORIZATION_ENV, raising=False)
    with pytest.raises(r.CanonicalRunnerError, match="execution_gate_closed"):
        r._require_authorization(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )
    with pytest.raises(r.CanonicalRunnerError, match="authorization_environment"):
        r._require_authorization(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )


def test_result_surface_is_virgin_during_implementation():
    assert r.FINAL_RESULT_PATH.exists() is False
    assert r.FAILURE_RESULT_PATH.exists() is False
    assert r.RESULT_ROOT.exists() is False


def test_day_evidence_paths_are_d6r24_specific():
    assert r.day_evidence_path("2026-01-01").name == (
        "2026-01-01_DEV045_D6R24_DAY_RESULT.json"
    )
    with pytest.raises(r.CanonicalRunnerError, match="day_evidence_day"):
        r.day_evidence_path("2026-08-01")


def test_serialization_regression_for_q1_invalid_attribute_is_closed():
    source = Path(r.__file__).read_text(encoding="utf-8")
    assert "replay.completed_cycle_count" not in source
    assert r.Q1_INVALID_COMPLETED_CYCLE_ATTRIBUTE_ALLOWED is False
    assert r.CORRECT_CYCLE_COUNT_EXPRESSION == "len(replay.cycles)"


def test_runner_never_invokes_predecessor_canonical_or_qualification_replay():
    source = Path(r.__file__).read_text(encoding="utf-8")
    assert "d6r21.run_full_canonical_arena(" not in source
    assert "run_target_qualification(" not in source
    assert "run_target_forensic(" not in source
    assert source.count("m6.run_economic_arena(") == 1


def test_json_normalization_and_success_write_contract():
    assert r.JSON_NORMALIZATION_BEFORE_SUCCESS_WRITE is True
    assert r.POST_WRITE_SEMANTIC_ASSERTIONS_ALLOWED is False
    normalized = r._json_normalize({"x": (1, 2), "y": {"a": True}})
    assert normalized == {"x": [1, 2], "y": {"a": True}}


def test_runner_contract_is_green_without_real_execution():
    r.validate_runner_contract()

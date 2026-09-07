from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from multimarket import dev045_d6r20_q3_real_engine_qualification as q3
from multimarket import dev045_d6r20_q4_real_engine_qualification as q4
from multimarket import dev045_d6r20_q4_scheduler_reconciled_driver as driver


DAY_JAN = "2026-01-01"
DAY_APR = "2026-04-01"
PRIMARY = "Q0_PRIMARY_250_250"


def _authorize(monkeypatch) -> None:
    monkeypatch.setenv(q4.AUTHORIZATION_ENV, q4.AUTHORIZATION_TOKEN)


def _configure_result_surface(monkeypatch, tmp_path: Path, suffix: str):
    root = tmp_path / f"q4-{suffix}"
    monkeypatch.setattr(q4, "RESULT_ROOT", root)
    monkeypatch.setattr(
        q4,
        "SUCCESS_RESULT_PATH",
        root / "DEV045_D6R20_Q4_QUALIFICATION_RESULT.json",
    )
    monkeypatch.setattr(
        q4,
        "FAILURE_RESULT_PATH",
        root / "DEV045_D6R20_Q4_QUALIFICATION_FAILURE.json",
    )
    return root


def _diagnostics(day: str, policy_id: str, scenario: str):
    return q4.ReplayExecutionDiagnostics(
        day=day,
        policy_id=policy_id,
        scenario=scenario,
        market_wakeups=1,
        response_wakeups=1,
        policy_epochs=1,
        submit_requests=0,
        cancel_requests=0,
        maker_fill_count=0,
        taker_fill_count=0,
        total_fill_count=0,
        forced_flatten_count=0,
        flatten_order_id_count=0,
        terminal_position=0.0,
        terminal_flat=True,
        terminal_working_quote_slots=0,
        terminal_shutdown_started=True,
        terminal_shutdown_quiescent=True,
        adapter_candidate_epochs=0,
        direct_action_queries=0,
        direct_action_rows_found=0,
        direct_action_missing_rows=0,
        direct_action_explicit_abstains=0,
        simulator_inventory_clock_match=True,
        final_inventory_clock_flat=True,
        quote_slots_clear=True,
        pending_replacement_absent=True,
        forced_flatten_lifecycle_complete=True,
        flatten_order_ids_unique=True,
        request_overlap_invariant=True,
        duplicate_working_side_invariant=True,
        post_shutdown_replacement_absent=True,
    )


def _prepare_top_level(monkeypatch, tmp_path: Path, suffix: str):
    _configure_result_surface(monkeypatch, tmp_path, suffix)
    _authorize(monkeypatch)
    monkeypatch.setattr(
        q4,
        "validate_repository_preflight",
        lambda: q4.RepositoryIdentity(
            branch=q4.EXPECTED_BRANCH,
            head="a" * 40,
            remote_ref=q4.EXPECTED_REMOTE_REF,
            remote_head="a" * 40,
            tracked_worktree_clean=True,
            permitted_untracked_paths=(),
            d6r20_driver_blob=q4.D6R20_DRIVER_BLOB,
            m4_m6_binding_blob=q4.M4_M6_BINDING_BLOB,
            v2_patch_sha256=q4.V2_PATCH_SHA256,
            d6r20_canonical_runner_absent=True,
            d6r21_canonical_runner_absent=True,
            result_surface_virgin=True,
        ),
    )
    monkeypatch.setattr(q4, "validate_qualification_contract", lambda: None)
    monkeypatch.setattr(q4, "_hftbacktest_module", lambda: object())
    monkeypatch.setattr(
        q4,
        "validate_runtime_identity",
        lambda h: q4.RuntimeIdentity(
            q4.HFTBACKTEST_VERSION,
            q4.HFTBACKTEST_BINARY_SHA256,
            True,
        ),
    )


def test_q4_closed_and_exact_authorization_has_no_q3_fallback(monkeypatch):
    assert q4.EXPERIMENT_ID == "DEV045-D6R20-Q4"
    assert q4.DESIGN_VERSION == (
        "real-hftbacktest-v2-blocking-wait-policy-clock-"
        "reconciliation-qualification-v1"
    )
    assert q4.AUTHORIZATION_ENV == "DEV045_D6R20_Q4_AUTHORIZE"
    assert q4.AUTHORIZATION_TOKEN == (
        "YES_REAL_HFTBACKTEST_V2_EXECUTION_QUALIFICATION_D6R20_Q4"
    )
    assert q4.QUALIFICATION_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert q4.REAL_HISTORICAL_QUALIFICATION_EXECUTED is False
    assert q4.Q1_RERUN_AUTHORIZED is False
    assert q4.Q2_RERUN_AUTHORIZED is False
    assert q4.Q3_RERUN_AUTHORIZED is False

    monkeypatch.setenv(q3.AUTHORIZATION_ENV, q3.AUTHORIZATION_TOKEN)

    with pytest.raises(q4.QualificationError, match="authorization_environment"):
        q4._require_authorization(
            authorization_token=q4.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    _authorize(monkeypatch)
    q4._require_authorization(
        authorization_token=q4.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )


def test_q4_preserves_exact_q3_matrix_and_corrected_validator():
    q4.validate_qualification_contract()
    assert q4.QUALIFICATION_PLAN == q3.QUALIFICATION_PLAN
    assert len(q4.QUALIFICATION_PLAN) == 20
    assert len(q4._day_plan(DAY_JAN)) == 16
    assert len(q4._day_plan(DAY_APR)) == 4
    assert q4.HISTORICAL_KERNEL is (
        driver.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
    )
    assert q4._validate_completed_replay is q3._validate_completed_replay
    assert q4._order_values_tuple is q3._order_values_tuple


def test_q4_runtime_accepts_only_frozen_v2_binary(monkeypatch, tmp_path):
    package = tmp_path / "hftbacktest"
    package.mkdir()
    init = package / "__init__.py"
    init.write_text("", encoding="utf-8")
    (package / "_hftbacktest.synthetic.so").write_bytes(b"synthetic")
    module = SimpleNamespace(__version__="2.4.4", __file__=str(init))

    monkeypatch.setattr(
        q4,
        "_stream_sha256",
        lambda path: q4.OLD_HFTBACKTEST_BINARY_SHA256,
    )

    with pytest.raises(q4.QualificationError, match="hftbacktest_binary_sha256"):
        q4.validate_runtime_identity(module)

    monkeypatch.setattr(
        q4,
        "_stream_sha256",
        lambda path: q4.HFTBACKTEST_BINARY_SHA256,
    )
    assert q4.validate_runtime_identity(module).verified is True


def test_q3_failure_is_frozen_byte_identically():
    path = (
        Path(__file__).resolve().parents[1]
        / "evidence/dev045_d6r20_q3_real_engine_qualification_failure.json"
    )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "81b1f88608d9096ba004516152ea18a86ea0055c5f0953314984284d512c27b3"
    )


def test_q4_result_surface_is_isolated_and_overwrite_refused(
    monkeypatch,
    tmp_path,
):
    assert str(q4.RESULT_ROOT).endswith(
        "dev045_d6r20_q4_real_engine_qualification_v1"
    )
    root = _configure_result_surface(monkeypatch, tmp_path, "overwrite")
    root.mkdir()
    q4.FAILURE_RESULT_PATH.write_text("{}\n", encoding="utf-8")

    with pytest.raises(q4.QualificationError, match="qualification_failure_exists"):
        q4._require_virgin_result_surface()


def test_q4_repository_branch_and_remote_fail_closed(monkeypatch, tmp_path):
    _configure_result_surface(monkeypatch, tmp_path, "preflight")
    monkeypatch.setattr(q4, "_current_branch", lambda: "wrong")

    with pytest.raises(q4.QualificationError, match="repository_branch"):
        q4.validate_repository_preflight()

    monkeypatch.setattr(q4, "_current_branch", lambda: q4.EXPECTED_BRANCH)
    monkeypatch.setattr(q4, "_worktree_status", lambda: ())
    monkeypatch.setattr(q4, "_current_head", lambda: "a" * 40)
    monkeypatch.setattr(q4, "_remote_head", lambda: "b" * 40)

    with pytest.raises(q4.QualificationError, match="repository_remote_mismatch"):
        q4.validate_repository_preflight()


def test_q4_primary_exception_survives_close_failure(monkeypatch):
    primary = RuntimeError("policy_epoch_skipped")

    class Backtest:
        def close(self):
            return 23

    class Kernel:
        def __init__(self, **kwargs):
            pass

        def run_full_day(self):
            raise primary

    monkeypatch.setattr(q4, "HISTORICAL_KERNEL", Kernel)
    monkeypatch.setattr(
        q4,
        "_hftbacktest_module",
        lambda: SimpleNamespace(HashMapMarketDepthBacktest=lambda assets: Backtest()),
    )
    monkeypatch.setattr(
        q4.base,
        "_build_asset_from_verified_source",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(q4.bridge, "validate_direct_index", lambda **kwargs: None)

    with pytest.raises(RuntimeError) as captured:
        q4.run_bound_verified_qualification_replay(
            SimpleNamespace(data=[{"local_ts": 30}]),
            policy_id="M01",
            day=DAY_JAN,
            scenario=PRIMARY,
            direct_index=None,
        )

    assert captured.value is primary


def test_q4_success_only_after_exact_20(monkeypatch, tmp_path):
    _prepare_top_level(monkeypatch, tmp_path, "success")

    def run_day(*, day, on_replay_start, on_replay_complete, **kwargs):
        for replay_day, policy_id, scenario in q4._day_plan(day):
            on_replay_start(replay_day, policy_id, scenario)
            on_replay_complete(_diagnostics(replay_day, policy_id, scenario))
        return ()

    monkeypatch.setattr(q4, "run_qualification_day_from_disk", run_day)
    payload = q4.run_real_engine_qualification(
        authorization_token=q4.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )
    assert payload["status"] == "REAL_ENGINE_QUALIFICATION_PASS"
    assert payload["replay_count"] == 20
    assert payload["january_replays"] == 16
    assert payload["april_replays"] == 4
    assert payload["canonical_attempt_consumed"] is False
    assert payload["economic_arena_called"] is False
    assert payload["strategy_ranking_performed"] is False


def test_q4_failure_is_noncanonical_and_no_retry(monkeypatch, tmp_path):
    _prepare_top_level(monkeypatch, tmp_path, "failure")
    primary = RuntimeError("unexpected_execution_failure")

    def fail(*, day, on_replay_start, **kwargs):
        on_replay_start(*q4._day_plan(day)[0])
        raise primary

    monkeypatch.setattr(q4, "run_qualification_day_from_disk", fail)

    with pytest.raises(RuntimeError) as captured:
        q4.run_real_engine_qualification(
            authorization_token=q4.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert captured.value is primary
    failure = json.loads(q4.FAILURE_RESULT_PATH.read_text(encoding="utf-8"))
    assert failure["canonical_attempt_consumed"] is False
    assert failure["economic_arena_called"] is False
    assert failure["strategy_ranking_performed"] is False
    assert failure["economic_conclusion"] == "UNAVAILABLE"
    assert failure["automatic_retry"] is False


def test_q4_has_no_canonical_or_economic_call_surface():
    source = Path(q4.__file__).read_text(encoding="utf-8")
    assert not hasattr(q4, "run_economic_arena")
    assert not hasattr(q4, "rank_candidates")
    assert "run_" + "economic_arena" not in source
    assert "replay." + "cycles" not in source
    assert q4.CANONICAL_ECONOMIC_ATTEMPT is False
    assert q4.CANONICAL_ATTEMPT_CONSUMED is False
    assert q4.ECONOMIC_ARENA_EXECUTED is False
    assert q4.LIVE_TRADING_AUTHORIZED is False

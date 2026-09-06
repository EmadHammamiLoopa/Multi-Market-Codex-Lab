from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from multimarket import dev045_d6r17_direct_action_driver_bridge as d6r17
from multimarket import dev045_d6r18_fresh_replacement_driver as d6r18
from multimarket import dev045_d6r19_response_batch_replacement_driver as d6r19
from multimarket import dev045_d6r20_q2_real_engine_qualification as q
from multimarket import dev045_d6r20_residual_flatten_driver as d6r20
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket.dev044_t0_strategy_contract import LONG, SHORT


DAY_JAN = "2026-01-01"
DAY_APR = "2026-04-01"
PRIMARY = "Q0_PRIMARY_250_250"
V2_ENGINE_TEST_ENABLED = os.environ.get("DEV045_Q2_V2_ENGINE_TEST") == "1"


def authorize(monkeypatch) -> None:
    monkeypatch.setenv(q.AUTHORIZATION_ENV, q.AUTHORIZATION_TOKEN)


def configure_result_surface(monkeypatch, tmp_path: Path, suffix="default"):
    root = tmp_path / f"q2-{suffix}"
    monkeypatch.setattr(q, "RESULT_ROOT", root)
    monkeypatch.setattr(
        q,
        "SUCCESS_RESULT_PATH",
        root / "DEV045_D6R20_Q2_QUALIFICATION_RESULT.json",
    )
    monkeypatch.setattr(
        q,
        "FAILURE_RESULT_PATH",
        root / "DEV045_D6R20_Q2_QUALIFICATION_FAILURE.json",
    )
    return root


def make_diagnostics(day: str, policy_id: str, scenario: str):
    return q.ReplayExecutionDiagnostics(
        day=day,
        policy_id=policy_id,
        scenario=scenario,
        market_wakeups=10,
        response_wakeups=5,
        policy_epochs=3,
        submit_requests=2,
        cancel_requests=2,
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


def make_completed_runtime():
    audit = SimpleNamespace(
        policy_id="M01",
        day=DAY_JAN,
        scenario=PRIMARY,
        execution_integrity_failures=0,
        terminal_flat=True,
    )
    replay = SimpleNamespace(
        policy_id="M01",
        day=DAY_JAN,
        scenario=PRIMARY,
        audit=audit,
        natural_end_of_data=True,
        market_wakeups=10,
        response_wakeups=5,
        policy_epochs=3,
        submit_requests=2,
        cancel_requests=2,
        maker_fill_count=0,
        taker_fill_count=0,
        total_fill_count=0,
        forced_flatten_count=0,
        flatten_order_ids=(),
        terminal_position=0.0,
        terminal_flat=True,
        terminal_working_quote_slots=0,
        terminal_shutdown_started=True,
        terminal_shutdown_quiescent=True,
        terminal_source_local_ns=30,
        terminal_shutdown_cutoff_ns=10,
        terminal_shutdown_start_ns=20,
        adapter_candidate_epochs=0,
    )
    kernel = SimpleNamespace(
        bid=SimpleNamespace(
            order_id=None,
            pending_replacement=None,
            replacement_required=False,
        ),
        ask=SimpleNamespace(
            order_id=None,
            pending_replacement=None,
            replacement_required=False,
        ),
        force_decision=None,
        flatten_done=False,
        flatten_decision_local_ns=None,
        flatten_response_local_ns=None,
        inventory_clock=SimpleNamespace(
            position=0.0,
            nonzero_since_local_ns=None,
        ),
        bound_fills=[],
        flatten_order_ids=[],
        completed_forced_flattens=0,
        direct_action_queries=0,
        direct_action_rows_found=0,
        direct_action_missing_rows=0,
        direct_action_explicit_abstains=0,
    )

    class Backtest:
        def position(self, asset_no):
            assert asset_no == 0
            return 0.0

        def orders(self, asset_no):
            assert asset_no == 0
            return {}

    return Backtest(), kernel, replay


def make_taker_event(order_id: int):
    fill = binding.FillRecord(
        policy_id="M01",
        day=DAY_JAN,
        timestamp_ns=order_id,
        side="BUY",
        qty=0.001,
        price=100.0,
        liquidity=binding.TAKER,
    )
    return binding.BoundReplayEvent(
        kind=binding.FILL,
        policy_id="M01",
        day=DAY_JAN,
        order_id=order_id,
        timestamp_ns=order_id,
        side="BUY",
        liquidity=binding.TAKER,
        exec_qty=0.001,
        exec_price_tick=1000,
        executed_quote_notional=0.1,
        fill=fill,
    )


def test_q2_closed_and_noncanonical_by_default():
    assert q.EXPERIMENT_ID == "DEV045-D6R20-Q2"
    assert q.DESIGN_VERSION == (
        "real-hftbacktest-v2-multifill-accounting-qualification-v1"
    )
    assert q.QUALIFICATION_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert q.REAL_HISTORICAL_QUALIFICATION_EXECUTED is False
    assert q.Q1_RERUN_AUTHORIZED is False
    assert q.CANONICAL_RUNNER_IMPLEMENTED is False
    assert q.CANONICAL_ECONOMIC_ATTEMPT is False
    assert q.CANONICAL_ATTEMPT_CONSUMED is False
    assert q.ECONOMIC_ARENA_EXECUTED is False
    assert q.STRATEGY_RANKING_PERFORMED is False
    assert q.AUTOMATIC_RETRY is False
    assert q.LIVE_TRADING_AUTHORIZED is False


def test_exact_q2_authorization_has_no_q1_fallback(monkeypatch):
    assert q.AUTHORIZATION_ENV == "DEV045_D6R20_Q2_AUTHORIZE"
    assert q.AUTHORIZATION_TOKEN == (
        "YES_REAL_HFTBACKTEST_V2_EXECUTION_QUALIFICATION_D6R20_Q2"
    )
    monkeypatch.delenv(q.AUTHORIZATION_ENV, raising=False)
    monkeypatch.setenv(
        "DEV045_D6R20_Q1_AUTHORIZE",
        "YES_REAL_HFTBACKTEST_EXECUTION_QUALIFICATION_D6R20_Q1",
    )

    with pytest.raises(q.QualificationError, match="execution_gate_closed"):
        q._require_authorization(
            authorization_token=q.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )

    with pytest.raises(q.QualificationError, match="authorization_environment"):
        q._require_authorization(
            authorization_token=q.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    authorize(monkeypatch)
    q._require_authorization(
        authorization_token=q.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )


def test_exact_20_replay_matrix_and_scope():
    q.validate_qualification_contract()
    assert q.QUALIFICATION_DAY_ORDER == (DAY_JAN, DAY_APR)
    assert q.JANUARY_POLICIES == (
        "M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08"
    )
    assert q.APRIL_POLICIES == ("M06", "M07")
    assert q.SCENARIO_ORDER == (
        "Q0_PRIMARY_250_250",
        "Q0_STRESS_500_500",
    )
    assert len(q.QUALIFICATION_PLAN) == 20
    assert len(q._day_plan(DAY_JAN)) == 16
    assert len(q._day_plan(DAY_APR)) == 4
    assert all(day in (DAY_JAN, DAY_APR) for day, _, _ in q.QUALIFICATION_PLAN)


def test_q2_uses_exact_d6r20_kernel_and_forbids_prior_kernels(monkeypatch):
    assert q.HISTORICAL_KERNEL is (
        d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
    )

    for forbidden in (
        d6r19.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel,
        d6r18.FreshReplacementContinuousHistoricalPolicyKernel,
        d6r17.DirectActionContinuousHistoricalPolicyKernel,
    ):
        monkeypatch.setattr(q, "HISTORICAL_KERNEL", forbidden)

        with pytest.raises(q.QualificationError, match="d6r20_kernel_binding"):
            q.validate_qualification_contract()


def _runtime_module(tmp_path: Path):
    package = tmp_path / "hftbacktest"
    package.mkdir()
    init = package / "__init__.py"
    init.write_text("", encoding="utf-8")
    artifact = package / "_hftbacktest.synthetic.so"
    artifact.write_bytes(b"synthetic")
    return SimpleNamespace(__version__="2.4.4", __file__=str(init)), artifact


def test_old_runtime_sha_is_rejected(monkeypatch, tmp_path):
    module, _artifact = _runtime_module(tmp_path)
    monkeypatch.setattr(
        q,
        "_stream_sha256",
        lambda path: q.OLD_HFTBACKTEST_BINARY_SHA256,
    )

    with pytest.raises(q.QualificationError, match="hftbacktest_binary_sha256"):
        q.validate_runtime_identity(module)


def test_v2_runtime_sha_is_accepted(monkeypatch, tmp_path):
    module, _artifact = _runtime_module(tmp_path)
    monkeypatch.setattr(
        q,
        "_stream_sha256",
        lambda path: q.HFTBACKTEST_BINARY_SHA256,
    )
    identity = q.validate_runtime_identity(module)
    assert identity == q.RuntimeIdentity(
        "2.4.4",
        "5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752",
        True,
    )


def configure_clean_repository(monkeypatch, tmp_path):
    configure_result_surface(monkeypatch, tmp_path, "preflight")
    monkeypatch.setattr(q, "_current_branch", lambda: q.EXPECTED_BRANCH)
    monkeypatch.setattr(q, "_current_head", lambda: "a" * 40)
    monkeypatch.setattr(q, "_remote_head", lambda: "a" * 40)
    monkeypatch.setattr(
        q,
        "_worktree_status",
        lambda: ("?? evidence/dev045_d6r9a_feb01_full_day_v2.json",),
    )

    def blob(path):
        if Path(path) == q.D6R20_DRIVER_PATH:
            return q.D6R20_DRIVER_BLOB
        if Path(path) == q.M4_M6_BINDING_PATH:
            return q.M4_M6_BINDING_BLOB
        raise AssertionError(path)

    monkeypatch.setattr(q, "_git_blob", blob)
    monkeypatch.setattr(q, "_stream_sha256", lambda path: q.V2_PATCH_SHA256)
    monkeypatch.setattr(
        q,
        "D6R20_CANONICAL_RUNNER_PATH",
        tmp_path / "absent-d6r20-canonical.py",
    )
    monkeypatch.setattr(
        q,
        "D6R21_CANONICAL_RUNNER_PATH",
        tmp_path / "absent-d6r21-canonical.py",
    )


def test_repository_preflight_accepts_only_exact_clean_q2(monkeypatch, tmp_path):
    configure_clean_repository(monkeypatch, tmp_path)
    identity = q.validate_repository_preflight()
    assert identity.branch == q.EXPECTED_BRANCH
    assert identity.head == identity.remote_head
    assert identity.d6r20_driver_blob == q.D6R20_DRIVER_BLOB
    assert identity.m4_m6_binding_blob == q.M4_M6_BINDING_BLOB
    assert identity.v2_patch_sha256 == q.V2_PATCH_SHA256
    assert identity.d6r20_canonical_runner_absent is True
    assert identity.d6r21_canonical_runner_absent is True


@pytest.mark.parametrize(
    ("condition", "message"),
    (
        ("branch", "repository_branch"),
        ("remote", "repository_remote_mismatch"),
        ("tracked", "repository_worktree_dirty_or_unexpected"),
        ("untracked", "repository_worktree_dirty_or_unexpected"),
    ),
)
def test_repository_preflight_fails_closed(monkeypatch, tmp_path, condition, message):
    configure_clean_repository(monkeypatch, tmp_path)

    if condition == "branch":
        monkeypatch.setattr(q, "_current_branch", lambda: "wrong")
    elif condition == "remote":
        monkeypatch.setattr(q, "_remote_head", lambda: "b" * 40)
    elif condition == "tracked":
        monkeypatch.setattr(q, "_worktree_status", lambda: (" M tracked.py",))
    else:
        monkeypatch.setattr(q, "_worktree_status", lambda: ("?? unexpected",))

    with pytest.raises(q.QualificationError, match=message):
        q.validate_repository_preflight()


def test_repository_preflight_rejects_identity_and_canonical_drift(
    monkeypatch,
    tmp_path,
):
    configure_clean_repository(monkeypatch, tmp_path)
    monkeypatch.setattr(q, "_stream_sha256", lambda path: "f" * 64)
    with pytest.raises(q.QualificationError, match="v2_patch_sha256"):
        q.validate_repository_preflight()

    configure_clean_repository(monkeypatch, tmp_path)
    canonical = tmp_path / "d6r21-canonical.py"
    canonical.write_text("forbidden\n", encoding="utf-8")
    monkeypatch.setattr(q, "D6R21_CANONICAL_RUNNER_PATH", canonical)
    with pytest.raises(q.QualificationError, match="d6r21_canonical_runner_exists"):
        q.validate_repository_preflight()


def test_q2_result_surface_is_isolated_and_overwrite_refused(monkeypatch, tmp_path):
    assert str(q.RESULT_ROOT).endswith(
        "dev045_d6r20_q2_real_engine_qualification_v1"
    )
    assert "q1_real_engine" not in str(q.RESULT_ROOT)
    root = configure_result_surface(monkeypatch, tmp_path, "overwrite")
    root.mkdir()
    q.SUCCESS_RESULT_PATH.write_text("{}\n", encoding="utf-8")

    with pytest.raises(q.QualificationError, match="qualification_result_exists"):
        q._require_virgin_result_surface()

    with pytest.raises(q.QualificationError, match="result_exists"):
        q._write_json_new(q.SUCCESS_RESULT_PATH, {})


def test_january_support_unused_and_april_support_exact(monkeypatch):
    calls = []
    indices = {"M06": object(), "M07": object()}

    def load(*, day):
        calls.append(day)
        return indices

    monkeypatch.setattr(q.d6r19_runner, "load_frozen_day_support", load)
    assert q.load_qualification_support(day=DAY_JAN) == {}
    assert q.load_qualification_support(day=DAY_APR) == indices
    assert calls == [DAY_APR]
    assert q.support.POLICY_TO_CORE_COLUMN["M06"][2] == "T10A_ACTION"
    assert q.support.POLICY_TO_CORE_COLUMN["M07"][2] == "T05A_ACTION"
    assert q.support.FORWARD_FILL_ENABLED is False
    assert q.support.BACKFILL_ENABLED is False
    assert q.support.INTERPOLATION_ENABLED is False
    assert q.support.A0_REFIT_ENABLED is False


def test_january_and_april_runtime_support_accounting():
    bt, kernel, replay = make_completed_runtime()
    replay.policy_id = replay.audit.policy_id = "M06"
    result = q._validate_completed_replay(bt=bt, kernel=kernel, replay=replay)
    assert result.direct_action_queries == 0

    kernel.direct_action_queries = 1
    kernel.direct_action_missing_rows = 1
    with pytest.raises(q.QualificationError, match="january_direct_action_support_used"):
        q._validate_completed_replay(bt=bt, kernel=kernel, replay=replay)

    replay.day = replay.audit.day = DAY_APR
    kernel.direct_action_queries = 3
    kernel.direct_action_rows_found = 2
    kernel.direct_action_missing_rows = 1
    kernel.direct_action_explicit_abstains = 1
    result = q._validate_completed_replay(bt=bt, kernel=kernel, replay=replay)
    assert result.direct_action_queries == 3
    assert result.direct_action_rows_found + result.direct_action_missing_rows == 3


@pytest.mark.parametrize(
    ("completed", "order_ids"),
    ((0, (4901,)), (1, (4901, 4902))),
)
def test_terminal_flatten_count_semantics_preserved(completed, order_ids):
    bt, kernel, replay = make_completed_runtime()
    kernel.bound_fills = [make_taker_event(order_id) for order_id in order_ids]
    kernel.flatten_order_ids = list(order_ids)
    kernel.completed_forced_flattens = completed
    replay.taker_fill_count = len(order_ids)
    replay.total_fill_count = len(order_ids)
    replay.forced_flatten_count = completed
    replay.flatten_order_ids = order_ids
    result = q._validate_completed_replay(bt=bt, kernel=kernel, replay=replay)
    assert result.flatten_order_id_count == len(order_ids)


def test_terminal_diagnostic_timestamps_are_not_active_state():
    bt, kernel, replay = make_completed_runtime()
    kernel.flatten_decision_local_ns = 15
    kernel.flatten_response_local_ns = 29
    result = q._validate_completed_replay(bt=bt, kernel=kernel, replay=replay)
    assert result.forced_flatten_lifecycle_complete is True


@pytest.mark.parametrize(
    ("attribute", "value"),
    (("force_decision", object()), ("flatten_done", True)),
)
def test_active_force_state_and_flatten_done_still_fail(attribute, value):
    bt, kernel, replay = make_completed_runtime()
    setattr(kernel, attribute, value)
    with pytest.raises(
        q.QualificationError,
        match="forced_flatten_lifecycle_incomplete",
    ):
        q._validate_completed_replay(bt=bt, kernel=kernel, replay=replay)


def test_primary_replay_exception_survives_close_failure(monkeypatch):
    lifecycle = []
    primary = RuntimeError("completed_flatten_nonflat")

    class Backtest:
        def close(self):
            lifecycle.append("close")
            return 17

    class Kernel:
        def __init__(self, **kwargs):
            lifecycle.append("kernel")

        def run_full_day(self):
            lifecycle.append("failure")
            raise primary

    monkeypatch.setattr(q, "HISTORICAL_KERNEL", Kernel)
    monkeypatch.setattr(
        q,
        "_hftbacktest_module",
        lambda: SimpleNamespace(HashMapMarketDepthBacktest=lambda assets: Backtest()),
    )
    monkeypatch.setattr(q.base, "_build_asset_from_verified_source", lambda *a, **k: object())
    monkeypatch.setattr(q.bridge, "validate_direct_index", lambda **kwargs: None)

    with pytest.raises(RuntimeError) as captured:
        q.run_bound_verified_qualification_replay(
            SimpleNamespace(data=[{"local_ts": 30}]),
            policy_id="M01",
            day=DAY_JAN,
            scenario=PRIMARY,
            direct_index=None,
        )

    assert captured.value is primary
    assert lifecycle == ["kernel", "failure", "close"]


def _event_row(h, array, index, *, side, timestamp, price, qty):
    array[index]["ev"] = int(
        h.DEPTH_EVENT | h.EXCH_EVENT | h.LOCAL_EVENT | side
    )
    array[index]["exch_ts"] = timestamp
    array[index]["local_ts"] = timestamp
    array[index]["px"] = price
    array[index]["qty"] = qty


def _build_v2_multilevel_backtest(h, *, flatten_direction):
    import numpy as np

    start = int(
        datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
        * 1_000_000_000
    )
    if flatten_direction == LONG:
        bids = ((100.0, 0.003),)
        asks = ((100.1, 0.001), (100.2, 0.001), (100.3, 0.001))
        seed_direction = SHORT
        expected_position = -0.003
    else:
        bids = ((100.3, 0.001), (100.2, 0.001), (100.1, 0.001))
        asks = ((100.4, 0.003),)
        seed_direction = LONG
        expected_position = 0.003

    rows = tuple((h.BUY_EVENT, *row) for row in bids) + tuple(
        (h.SELL_EVENT, *row) for row in asks
    )
    initial = np.zeros(len(rows), dtype=h.event_dtype)
    for index, (side, price, qty) in enumerate(rows):
        initial[index]["ev"] = int(
            h.DEPTH_SNAPSHOT_EVENT | h.EXCH_EVENT | h.LOCAL_EVENT | side
        )
        initial[index]["exch_ts"] = start
        initial[index]["local_ts"] = start
        initial[index]["px"] = price
        initial[index]["qty"] = qty

    data = np.zeros(2, dtype=h.event_dtype)
    _event_row(
        h,
        data,
        0,
        side=h.SELL_EVENT,
        timestamp=start + 1_000_000_000,
        price=120.0,
        qty=1.0,
    )
    _event_row(
        h,
        data,
        1,
        side=h.SELL_EVENT,
        timestamp=start + 10_000_000_000,
        price=120.0,
        qty=1.0,
    )
    asset = (
        h.BacktestAsset()
        .data([data])
        .initial_snapshot(initial)
        .linear_asset(1.0)
        .constant_order_latency(0, 0)
        .risk_adverse_queue_model()
        .partial_fill_exchange()
        .trading_value_fee_model(0.0, 0.002)
        .tick_size(p.TICK_SIZE)
        .lot_size(p.LOT_SIZE)
    )
    bt = h.HashMapMarketDepthBacktest([asset])
    assert int(bt.wait_next_feed(False, 2_000_000_000)) == 2
    seed = m4.submit_forced_flatten(
        bt,
        h,
        direction=seed_direction,
        qty=0.003,
        order_id=7001,
        wait=True,
    )
    assert seed.status == h.FILLED
    assert math.isclose(bt.position(0), expected_position, abs_tol=1e-12)
    return bt, start


def _require_v2_test_engine():
    if not V2_ENGINE_TEST_ENABLED:
        pytest.skip("explicit isolated V2 synthetic engine runtime required")

    import hftbacktest as h

    assert importlib.metadata.version("hftbacktest") == "2.4.4"
    binaries = tuple(
        Path(h.__file__).resolve().parent.glob("_hftbacktest*.so")
    )
    assert len(binaries) == 1
    observed = hashlib.sha256(binaries[0].read_bytes()).hexdigest()
    expected = os.environ.get("DEV045_Q2_TEST_ENGINE_SHA256")
    if expected:
        assert observed == expected
    return h


@pytest.mark.parametrize(
    ("flatten_direction", "pre_position", "position_delta", "final_price"),
    ((LONG, -0.003, 0.003, 100.3), (SHORT, 0.003, -0.003, 100.1)),
)
def test_v2_multilevel_d6r20_m4_binding_end_to_end(
    flatten_direction,
    pre_position,
    position_delta,
    final_price,
):
    h = _require_v2_test_engine()
    bt, start = _build_v2_multilevel_backtest(
        h,
        flatten_direction=flatten_direction,
    )

    try:
        before = binding.snapshot_state_values(bt.state_values(0))
        kernel = object.__new__(
            d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
        )
        kernel.bt = bt
        kernel.h = h
        kernel.next_flatten_order_id = 7002
        kernel.flatten_order_ids = []
        kernel.bound_fills = []
        kernel.policy_id = "M01"
        kernel.day = DAY_JAN
        kernel.inventory_clock = d1.InventoryClock(
            position=pre_position,
            nonzero_since_local_ns=start + 1_000_000_000,
        )
        kernel.flatten_response_local_ns = None

        kernel._execute_unique_flatten(
            direction=flatten_direction,
            qty=0.003,
        )
        after = binding.snapshot_state_values(bt.state_values(0))

        assert len(kernel.bound_fills) == 1
        event = kernel.bound_fills[0]
        assert event.kind == binding.FILL
        assert event.fill is not None
        assert event.fill.liquidity == binding.TAKER
        assert math.isclose(before.position, pre_position, abs_tol=1e-12)
        assert abs(after.position) <= 1e-12
        assert math.isclose(
            after.position - before.position,
            position_delta,
            abs_tol=1e-12,
        )
        assert math.isclose(
            after.trading_volume - before.trading_volume,
            0.003,
            abs_tol=1e-12,
        )
        expected_notional = 0.001 * (100.1 + 100.2 + 100.3)
        actual_notional = after.trading_value - before.trading_value
        assert math.isclose(actual_notional, expected_notional, abs_tol=1e-12)
        assert after.num_trades - before.num_trades == 3
        assert math.isclose(event.fill.qty, 0.003, abs_tol=1e-12)
        assert math.isclose(
            event.fill.price,
            expected_notional / 0.003,
            abs_tol=1e-12,
        )
        assert math.isclose(
            event.executed_quote_notional,
            expected_notional,
            abs_tol=1e-12,
        )
        assert math.isclose(
            event.fill.qty * event.fill.price,
            event.executed_quote_notional,
            abs_tol=1e-12,
        )
        assert not math.isclose(event.fill.price, final_price, abs_tol=1e-12)
        assert kernel.inventory_clock == d1.InventoryClock.flat()
        assert kernel.flatten_order_ids == [7002]
    finally:
        assert int(bt.close()) == 0


def prepare_top_level(monkeypatch, tmp_path, suffix):
    configure_result_surface(monkeypatch, tmp_path, suffix)
    authorize(monkeypatch)
    monkeypatch.setattr(
        q,
        "validate_repository_preflight",
        lambda: q.RepositoryIdentity(
            branch=q.EXPECTED_BRANCH,
            head="a" * 40,
            remote_ref=q.EXPECTED_REMOTE_REF,
            remote_head="a" * 40,
            tracked_worktree_clean=True,
            permitted_untracked_paths=(
                "evidence/dev045_d6r9a_feb01_full_day_v2.json",
            ),
            d6r20_driver_blob=q.D6R20_DRIVER_BLOB,
            m4_m6_binding_blob=q.M4_M6_BINDING_BLOB,
            v2_patch_sha256=q.V2_PATCH_SHA256,
            d6r20_canonical_runner_absent=True,
            d6r21_canonical_runner_absent=True,
            result_surface_virgin=True,
        ),
    )
    monkeypatch.setattr(q, "validate_qualification_contract", lambda: None)
    monkeypatch.setattr(q, "_hftbacktest_module", lambda: object())
    monkeypatch.setattr(
        q,
        "validate_runtime_identity",
        lambda h: q.RuntimeIdentity(
            q.HFTBACKTEST_VERSION,
            q.HFTBACKTEST_BINARY_SHA256,
            True,
        ),
    )


def test_success_only_after_all_20_and_contains_no_economics(monkeypatch, tmp_path):
    prepare_top_level(monkeypatch, tmp_path, "success")

    def run_day(*, day, on_replay_start, on_replay_complete, **kwargs):
        for replay_day, policy_id, scenario in q._day_plan(day):
            on_replay_start(replay_day, policy_id, scenario)
            on_replay_complete(make_diagnostics(replay_day, policy_id, scenario))
        return ()

    monkeypatch.setattr(q, "run_qualification_day_from_disk", run_day)
    payload = q.run_real_engine_qualification(
        authorization_token=q.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )
    assert payload["status"] == "REAL_ENGINE_QUALIFICATION_PASS"
    assert payload["replay_count"] == 20
    assert payload["january_replays"] == 16
    assert payload["april_replays"] == 4
    assert payload["canonical_attempt_consumed"] is False
    assert payload["economic_arena_called"] is False
    assert payload["strategy_ranking_performed"] is False
    assert payload["economic_conclusion"] == "NOT_EVALUATED"

    serialized = q.SUCCESS_RESULT_PATH.read_text(encoding="utf-8")
    for prohibited in (
        "net_pnl",
        "net_bps",
        "profit_factor",
        "max_drawdown",
        "economic_survivor_status",
    ):
        assert prohibited not in serialized


def test_q2_failure_is_noncanonical_and_preserves_primary(monkeypatch, tmp_path):
    prepare_top_level(monkeypatch, tmp_path, "failure")
    primary = RuntimeError("local_inventory_clock_mismatch")

    def fail(*, day, on_replay_start, **kwargs):
        on_replay_start(*q._day_plan(day)[0])
        raise primary

    monkeypatch.setattr(q, "run_qualification_day_from_disk", fail)
    with pytest.raises(RuntimeError) as captured:
        q.run_real_engine_qualification(
            authorization_token=q.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )
    assert captured.value is primary
    failure = json.loads(q.FAILURE_RESULT_PATH.read_text(encoding="utf-8"))
    assert failure["completed_qualification_replay_count"] == 0
    assert failure["exception_message"] == "local_inventory_clock_mismatch"
    assert failure["canonical_attempt_consumed"] is False
    assert failure["economic_arena_called"] is False
    assert failure["strategy_ranking_performed"] is False
    assert failure["economic_conclusion"] == "UNAVAILABLE"
    assert failure["automatic_retry"] is False


def test_no_canonical_or_economic_call_surface():
    source = Path(q.__file__).read_text(encoding="utf-8")
    assert not hasattr(q, "run_economic_arena")
    assert not hasattr(q, "rank_candidates")
    assert "run_" + "economic_arena" not in source
    assert "replay." + "cycles" not in source
    assert q._git_blob(Path(d6r20.__file__)) == q.D6R20_DRIVER_BLOB
    assert q._git_blob(Path(binding.__file__)) == q.M4_M6_BINDING_BLOB

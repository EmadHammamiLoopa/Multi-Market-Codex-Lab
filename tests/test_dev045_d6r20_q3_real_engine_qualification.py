from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import inspect
import json
import math
import os
from pathlib import Path
import textwrap
from types import SimpleNamespace

import pytest

from multimarket import dev045_d6r20_q2_real_engine_qualification as q2
from multimarket import dev045_d6r20_q3_real_engine_qualification as q3
from multimarket import dev045_d6r20_real_engine_qualification as q1
from multimarket import dev045_d6r20_residual_flatten_driver as d6r20
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket.dev044_t0_strategy_contract import LONG


DAY_JAN = "2026-01-01"
DAY_APR = "2026-04-01"
PRIMARY = "Q0_PRIMARY_250_250"
V2_ENGINE_TEST_ENABLED = os.environ.get("DEV045_Q3_V2_ENGINE_TEST") == "1"


def _authorize(monkeypatch) -> None:
    monkeypatch.setenv(q3.AUTHORIZATION_ENV, q3.AUTHORIZATION_TOKEN)


def _configure_result_surface(monkeypatch, tmp_path: Path, suffix: str):
    root = tmp_path / f"q3-{suffix}"
    monkeypatch.setattr(q3, "RESULT_ROOT", root)
    monkeypatch.setattr(
        q3,
        "SUCCESS_RESULT_PATH",
        root / "DEV045_D6R20_Q3_QUALIFICATION_RESULT.json",
    )
    monkeypatch.setattr(
        q3,
        "FAILURE_RESULT_PATH",
        root / "DEV045_D6R20_Q3_QUALIFICATION_FAILURE.json",
    )
    return root


def _runtime_module(tmp_path: Path):
    package = tmp_path / "hftbacktest"
    package.mkdir()
    init = package / "__init__.py"
    init.write_text("", encoding="utf-8")
    artifact = package / "_hftbacktest.synthetic.so"
    artifact.write_bytes(b"synthetic")
    return SimpleNamespace(__version__="2.4.4", __file__=str(init))


def _require_v2_engine():
    if not V2_ENGINE_TEST_ENABLED:
        pytest.skip("explicit isolated V2 synthetic engine runtime required")

    import hftbacktest as h

    assert importlib.metadata.version("hftbacktest") == "2.4.4"
    binaries = tuple(
        Path(h.__file__).resolve().parent.glob("_hftbacktest*.so")
    )
    assert len(binaries) == 1
    observed = hashlib.sha256(binaries[0].read_bytes()).hexdigest()
    expected = os.environ.get("DEV045_Q3_TEST_ENGINE_SHA256")

    if expected is not None:
        assert observed == expected

    return h


def _build_actual_backtest(h):
    data = m4.make_cancel_replace_fixture()
    asset = m4.build_asset(
        data,
        entry_latency_ns=0,
        response_latency_ns=0,
    )
    bt = h.HashMapMarketDepthBacktest([asset])
    assert int(bt.wait_next_feed(False, 2_000_000_000)) == 2
    return bt


def _submit_active_bid(bt, h, *, order_id: int = 8101):
    decision = p.policy_decision("M01", m4.policy_book())
    view = m4.submit_passive(
        bt,
        h,
        side="bid",
        order_id=order_id,
        decision=decision,
        wait=True,
    )
    assert int(view.status) == int(h.NEW)
    return view


def _submit_active_ask(bt, h, *, order_id: int):
    decision = p.policy_decision("M01", m4.policy_book())
    view = m4.submit_passive(
        bt,
        h,
        side="ask",
        order_id=order_id,
        decision=decision,
        wait=True,
    )
    assert int(view.status) == int(h.NEW)
    return view


def _build_partially_filled_backtest(h):
    import numpy as np

    data = np.zeros(4, dtype=h.event_dtype)
    rows = (
        (h.DEPTH_EVENT, h.SELL_EVENT, 1_000_000_000, 100.1, 8.0),
        (h.TRADE_EVENT, h.SELL_EVENT, 3_000_000_000, 100.0, 10.0),
        (h.TRADE_EVENT, h.SELL_EVENT, 5_000_000_000, 100.0, 0.001),
        (h.DEPTH_EVENT, h.SELL_EVENT, 8_000_000_000, 100.1, 8.0),
    )

    for index, (base, side, timestamp, price, qty) in enumerate(rows):
        data[index]["ev"] = int(base | h.EXCH_EVENT | h.LOCAL_EVENT | side)
        data[index]["exch_ts"] = timestamp
        data[index]["local_ts"] = timestamp
        data[index]["px"] = price
        data[index]["qty"] = qty

    asset = m4.build_asset(
        data,
        entry_latency_ns=100_000_000,
        response_latency_ns=100_000_000,
    )
    bt = h.HashMapMarketDepthBacktest([asset])
    assert int(bt.wait_next_feed(False, 2_000_000_000)) == 2
    assert int(
        bt.submit_buy_order(
            0,
            8201,
            100.0,
            0.002,
            h.GTC,
            h.LIMIT,
            True,
        )
    ) == 0
    assert int(bt.wait_next_feed(False, 3_000_000_000)) == 2
    assert int(bt.wait_next_feed(True, 600_000_000)) == 0
    assert int(bt.wait_next_feed(False, 3_000_000_000)) == 2
    assert int(bt.wait_next_feed(True, 600_000_000)) == 3
    partial = bt.orders(0).get(8201)
    assert int(partial.status) == int(q3.d2.HFT_PARTIALLY_FILLED)
    assert math.isclose(partial.leaves_qty, 0.001, abs_tol=1e-12)
    return bt


def _manual_values(order_dict) -> tuple:
    values = order_dict.values()
    result = []

    while True:
        raw = values.next()

        if raw is None:
            break

        result.append(raw)

    return tuple(result)


def _order_snapshot(order_dict) -> tuple:
    return tuple(
        sorted(
            (
                int(raw.order_id),
                int(raw.status),
                float(raw.leaves_qty),
                float(raw.exec_qty),
            )
            for raw in _manual_values(order_dict)
        )
    )


def _state_snapshot(bt) -> tuple:
    state = bt.state_values(0)
    return (
        float(state.position),
        float(state.balance),
        float(state.fee),
        int(state.num_trades),
        float(state.trading_volume),
        float(state.trading_value),
    )


def _completed_replay_and_kernel():
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
        market_wakeups=1,
        response_wakeups=1,
        policy_epochs=1,
        submit_requests=0,
        cancel_requests=0,
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
    return replay, kernel


def _diagnostics(day: str, policy_id: str, scenario: str):
    return q3.ReplayExecutionDiagnostics(
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
        q3,
        "validate_repository_preflight",
        lambda: q3.RepositoryIdentity(
            branch=q3.EXPECTED_BRANCH,
            head="a" * 40,
            remote_ref=q3.EXPECTED_REMOTE_REF,
            remote_head="a" * 40,
            tracked_worktree_clean=True,
            permitted_untracked_paths=(),
            d6r20_driver_blob=q3.D6R20_DRIVER_BLOB,
            m4_m6_binding_blob=q3.M4_M6_BINDING_BLOB,
            v2_patch_sha256=q3.V2_PATCH_SHA256,
            d6r20_canonical_runner_absent=True,
            d6r21_canonical_runner_absent=True,
            result_surface_virgin=True,
        ),
    )
    monkeypatch.setattr(q3, "validate_qualification_contract", lambda: None)
    monkeypatch.setattr(q3, "_hftbacktest_module", lambda: object())
    monkeypatch.setattr(
        q3,
        "validate_runtime_identity",
        lambda h: q3.RuntimeIdentity(
            q3.HFTBACKTEST_VERSION,
            q3.HFTBACKTEST_BINARY_SHA256,
            True,
        ),
    )


def test_q3_closed_noncanonical_and_exact_authorization(monkeypatch):
    assert q3.EXPERIMENT_ID == "DEV045-D6R20-Q3"
    assert q3.DESIGN_VERSION == (
        "real-hftbacktest-v2-order-values-validator-qualification-v1"
    )
    assert q3.AUTHORIZATION_ENV == "DEV045_D6R20_Q3_AUTHORIZE"
    assert q3.AUTHORIZATION_TOKEN == (
        "YES_REAL_HFTBACKTEST_V2_EXECUTION_QUALIFICATION_D6R20_Q3"
    )
    assert q3.QUALIFICATION_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert q3.REAL_HISTORICAL_QUALIFICATION_EXECUTED is False
    assert q3.Q1_RERUN_AUTHORIZED is False
    assert q3.Q2_RERUN_AUTHORIZED is False
    assert q3.CANONICAL_RUNNER_IMPLEMENTED is False
    assert q3.CANONICAL_ATTEMPT_CONSUMED is False
    assert q3.ECONOMIC_ARENA_EXECUTED is False
    assert q3.STRATEGY_RANKING_PERFORMED is False

    monkeypatch.setenv(q2.AUTHORIZATION_ENV, q2.AUTHORIZATION_TOKEN)
    monkeypatch.delenv(q3.AUTHORIZATION_ENV, raising=False)

    with pytest.raises(q3.QualificationError, match="authorization_environment"):
        q3._require_authorization(
            authorization_token=q3.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    _authorize(monkeypatch)
    q3._require_authorization(
        authorization_token=q3.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )


def test_q3_preserves_exact_q2_matrix_kernel_and_support(monkeypatch):
    q3.validate_qualification_contract()
    assert q3.QUALIFICATION_PLAN == q2.QUALIFICATION_PLAN
    assert len(q3.QUALIFICATION_PLAN) == 20
    assert len(q3._day_plan(DAY_JAN)) == 16
    assert len(q3._day_plan(DAY_APR)) == 4
    assert q3.HISTORICAL_KERNEL is (
        d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
    )

    sentinel = {"M06": object(), "M07": object()}
    calls = []

    def load(*, day):
        calls.append(day)
        return sentinel

    monkeypatch.setattr(q3.d6r19_runner, "load_frozen_day_support", load)
    assert q3.load_qualification_support(day=DAY_JAN) == {}
    assert q3.load_qualification_support(day=DAY_APR) == sentinel
    assert calls == [DAY_APR]
    assert q3.support.POLICY_TO_CORE_COLUMN["M06"][2] == "T10A_ACTION"
    assert q3.support.POLICY_TO_CORE_COLUMN["M07"][2] == "T05A_ACTION"


def test_q3_runtime_accepts_only_frozen_v2_sha(monkeypatch, tmp_path):
    module = _runtime_module(tmp_path)
    monkeypatch.setattr(
        q3,
        "_stream_sha256",
        lambda path: q3.OLD_HFTBACKTEST_BINARY_SHA256,
    )

    with pytest.raises(q3.QualificationError, match="hftbacktest_binary_sha256"):
        q3.validate_runtime_identity(module)

    monkeypatch.setattr(
        q3,
        "_stream_sha256",
        lambda path: q3.HFTBACKTEST_BINARY_SHA256,
    )
    identity = q3.validate_runtime_identity(module)
    assert identity.verified is True
    assert identity.compiled_artifact_sha256 == (
        "5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752"
    )


def test_q2_failure_was_frozen_byte_identically():
    path = (
        Path(__file__).resolve().parents[1]
        / "evidence/dev045_d6r20_q2_real_engine_qualification_failure.json"
    )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == q3.Q2_FAILURE_SHA256
    assert q3.Q2_FAILED_HEAD == "835676a3d3bb5d7780f63a2e2373c32a59315cab"


def test_order_values_helper_fails_closed_without_callable_next():
    order_dict = SimpleNamespace(values=lambda: SimpleNamespace(next=None))

    with pytest.raises(q3.QualificationError, match="order_values_next_unavailable"):
        q3._order_values_tuple(order_dict)


def test_q3_validator_error_surface_matches_frozen_q1_except_enumeration():
    def error_codes(function):
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        return tuple(
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "QualificationError"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        )

    assert q3._validate_completed_replay is not q1._validate_completed_replay
    assert q3._validate_completed_replay is not q2._validate_completed_replay
    assert error_codes(q3._validate_completed_replay) == error_codes(
        q1._validate_completed_replay
    )
    q1_source = inspect.getsource(q1._validate_completed_replay)
    q3_source = inspect.getsource(q3._validate_completed_replay)
    assert "bt.orders(d2.ASSET_NO).values()" in q1_source
    assert "_active_orders_tuple(bt.orders(d2.ASSET_NO))" in q3_source


def test_actual_values_api_reproduction_supported_traversal_parity_and_no_mutation():
    h = _require_v2_engine()
    bt = _build_actual_backtest(h)

    try:
        _submit_active_bid(bt, h)
        order_dict = bt.orders(0)
        before_orders = _order_snapshot(order_dict)
        before_state = _state_snapshot(bt)

        with pytest.raises(TypeError, match="'Values' object is not iterable"):
            list(order_dict.values())

        manual = _manual_values(order_dict)
        helper = q3._order_values_tuple(order_dict)
        manual_identity = tuple(
            (int(raw.order_id), int(raw.status)) for raw in manual
        )
        helper_identity = tuple(
            (int(raw.order_id), int(raw.status)) for raw in helper
        )

        assert manual_identity == ((8101, int(h.NEW)),)
        assert helper_identity == manual_identity
        assert len({order_id for order_id, _ in helper_identity}) == len(helper)
        assert _order_snapshot(order_dict) == before_orders
        assert _state_snapshot(bt) == before_state
    finally:
        assert int(bt.close()) == 0


def test_actual_active_filter_selects_only_new_or_partially_filled():
    h = _require_v2_engine()
    bt = _build_partially_filled_backtest(h)

    try:
        _submit_active_ask(bt, h, order_id=8202)
        filled = m4.submit_forced_flatten(
            bt,
            h,
            direction=LONG,
            qty=0.001,
            order_id=8203,
            wait=True,
        )
        assert int(filled.status) == int(h.FILLED)
        all_orders = q3._order_values_tuple(bt.orders(0))
        active = q3._active_orders_tuple(bt.orders(0))
        assert {
            (int(raw.order_id), int(raw.status)) for raw in all_orders
        } == {
            (8201, int(q3.d2.HFT_PARTIALLY_FILLED)),
            (8202, int(h.NEW)),
            (8203, int(h.FILLED)),
        }
        assert {
            (int(raw.order_id), int(raw.status)) for raw in active
        } == {
            (8201, int(q3.d2.HFT_PARTIALLY_FILLED)),
            (8202, int(h.NEW)),
        }
    finally:
        assert int(bt.close()) == 0


def test_actual_v2_completed_validator_passes_then_rejects_active_order():
    h = _require_v2_engine()
    bt = _build_actual_backtest(h)

    try:
        replay, kernel = _completed_replay_and_kernel()
        diagnostics = q3._validate_completed_replay(
            bt=bt,
            kernel=kernel,
            replay=replay,
        )
        assert diagnostics.terminal_flat is True
        assert diagnostics.terminal_working_quote_slots == 0

        _submit_active_bid(bt, h, order_id=8301)

        with pytest.raises(
            q3.QualificationError,
            match="simulator_working_orders_at_terminal",
        ):
            q3._validate_completed_replay(
                bt=bt,
                kernel=kernel,
                replay=replay,
            )
    finally:
        assert int(bt.close()) == 0


def test_q3_repository_branch_remote_and_result_surface_fail_closed(
    monkeypatch,
    tmp_path,
):
    _configure_result_surface(monkeypatch, tmp_path, "preflight")
    monkeypatch.setattr(q3, "_current_branch", lambda: "wrong")

    with pytest.raises(q3.QualificationError, match="repository_branch"):
        q3.validate_repository_preflight()

    monkeypatch.setattr(q3, "_current_branch", lambda: q3.EXPECTED_BRANCH)
    monkeypatch.setattr(q3, "_worktree_status", lambda: ())
    monkeypatch.setattr(q3, "_current_head", lambda: "a" * 40)
    monkeypatch.setattr(q3, "_remote_head", lambda: "b" * 40)

    with pytest.raises(q3.QualificationError, match="repository_remote_mismatch"):
        q3.validate_repository_preflight()

    q3.SUCCESS_RESULT_PATH.parent.mkdir()
    q3.SUCCESS_RESULT_PATH.write_text("{}\n", encoding="utf-8")

    with pytest.raises(q3.QualificationError, match="qualification_result_exists"):
        q3._require_virgin_result_surface()


def test_q3_primary_replay_exception_survives_close_failure(monkeypatch):
    primary = RuntimeError("local_inventory_clock_mismatch")

    class Backtest:
        def close(self):
            return 19

    class Kernel:
        def __init__(self, **kwargs):
            pass

        def run_full_day(self):
            raise primary

    monkeypatch.setattr(q3, "HISTORICAL_KERNEL", Kernel)
    monkeypatch.setattr(
        q3,
        "_hftbacktest_module",
        lambda: SimpleNamespace(HashMapMarketDepthBacktest=lambda assets: Backtest()),
    )
    monkeypatch.setattr(
        q3.base,
        "_build_asset_from_verified_source",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(q3.bridge, "validate_direct_index", lambda **kwargs: None)

    with pytest.raises(RuntimeError) as captured:
        q3.run_bound_verified_qualification_replay(
            SimpleNamespace(data=[{"local_ts": 30}]),
            policy_id="M01",
            day=DAY_JAN,
            scenario=PRIMARY,
            direct_index=None,
        )

    assert captured.value is primary


def test_q3_success_requires_all_20_and_remains_noneconomic(monkeypatch, tmp_path):
    _prepare_top_level(monkeypatch, tmp_path, "success")

    def run_day(*, day, on_replay_start, on_replay_complete, **kwargs):
        for replay_day, policy_id, scenario in q3._day_plan(day):
            on_replay_start(replay_day, policy_id, scenario)
            on_replay_complete(_diagnostics(replay_day, policy_id, scenario))
        return ()

    monkeypatch.setattr(q3, "run_qualification_day_from_disk", run_day)
    payload = q3.run_real_engine_qualification(
        authorization_token=q3.AUTHORIZATION_TOKEN,
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


def test_q3_failure_evidence_is_noncanonical_and_no_retry(monkeypatch, tmp_path):
    _prepare_top_level(monkeypatch, tmp_path, "failure")
    primary = RuntimeError("simulator_working_orders_at_terminal")

    def fail(*, day, on_replay_start, **kwargs):
        on_replay_start(*q3._day_plan(day)[0])
        raise primary

    monkeypatch.setattr(q3, "run_qualification_day_from_disk", fail)

    with pytest.raises(RuntimeError) as captured:
        q3.run_real_engine_qualification(
            authorization_token=q3.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert captured.value is primary
    failure = json.loads(q3.FAILURE_RESULT_PATH.read_text(encoding="utf-8"))
    assert failure["completed_qualification_replay_count"] == 0
    assert failure["exception_message"] == (
        "simulator_working_orders_at_terminal"
    )
    assert failure["canonical_attempt_consumed"] is False
    assert failure["economic_arena_called"] is False
    assert failure["strategy_ranking_performed"] is False
    assert failure["economic_conclusion"] == "UNAVAILABLE"
    assert failure["automatic_retry"] is False


def test_q3_has_no_canonical_or_economic_surface():
    source = Path(q3.__file__).read_text(encoding="utf-8")
    assert not hasattr(q3, "run_economic_arena")
    assert not hasattr(q3, "rank_candidates")
    assert "run_" + "economic_arena" not in source
    assert "replay." + "cycles" not in source
    assert q3.CANONICAL_ECONOMIC_ATTEMPT is False
    assert q3.CANONICAL_ATTEMPT_CONSUMED is False
    assert q3.LIVE_TRADING_AUTHORIZED is False

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from multimarket import dev045_d6r20_q6_initial_book_readiness_driver as q6_driver
from multimarket import dev045_d6r20_q7_flatten_end_of_data_forensic as q7
from multimarket import dev045_d6r20_q7_flatten_end_of_data_forensic_driver as driver
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket.dev044_t0_strategy_contract import LONG, SHORT


V2_ENGINE_TEST_ENABLED = os.environ.get("DEV045_Q7_V2_ENGINE_TEST") == "1"
SOURCE_ROOT_TEXT = os.environ.get("DEV045_HFT244_SOURCE_ROOT")
EXPECTED_BINARY_SHA256 = os.environ.get("DEV045_Q7_TEST_ENGINE_SHA256")
DAY_START_NS = int(
    datetime(2026, 4, 1, tzinfo=timezone.utc).timestamp()
    * 1_000_000_000
)


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

    if EXPECTED_BINARY_SHA256 is not None:
        assert observed == EXPECTED_BINARY_SHA256

    return h


def _event_data(h, *, end_ns: int):
    import numpy as np

    data = np.zeros(2, dtype=h.event_dtype)

    for index, offset in enumerate((1_000_000_000, int(end_ns))):
        timestamp = DAY_START_NS + offset
        data[index]["ev"] = int(
            h.DEPTH_EVENT | h.EXCH_EVENT | h.LOCAL_EVENT | h.SELL_EVENT
        )
        data[index]["exch_ts"] = timestamp
        data[index]["local_ts"] = timestamp
        data[index]["px"] = 100.1
        data[index]["qty"] = 8.0

    return data


def _build_backtest(h, *, end_ns: int, latency_ns: int):
    asset = (
        h.BacktestAsset()
        .data([_event_data(h, end_ns=end_ns)])
        .initial_snapshot(m4.make_initial_snapshot())
        .linear_asset(1.0)
        .constant_order_latency(latency_ns, latency_ns)
        .risk_adverse_queue_model()
        .partial_fill_exchange()
        .trading_value_fee_model(0.0, 0.002)
        .tick_size(p.TICK_SIZE)
        .lot_size(p.LOT_SIZE)
    )
    bt = h.HashMapMarketDepthBacktest([asset])
    assert int(bt.wait_next_feed(False, 2_000_000_000)) == 2
    return bt


def _slot():
    return SimpleNamespace(
        order_id=None,
        replacement_required=False,
        pending_replacement=None,
    )


def _bare_kernel(cls, *, bt, h, terminal: bool, force_present: bool):
    kernel = object.__new__(cls)
    kernel.bt = bt
    kernel.h = h
    kernel.policy_id = "M06"
    kernel.day = "2026-04-01"
    kernel.scenario = "Q0_STRESS_500_500"
    kernel.next_flatten_order_id = 9001
    kernel.flatten_order_ids = []
    kernel.bound_fills = []
    kernel.inventory_clock = d1.InventoryClock.flat()
    kernel.flatten_response_local_ns = None
    kernel.terminal_source_local_ns = DAY_START_NS + 1_100_000_000
    kernel.terminal_shutdown_cutoff_ns = DAY_START_NS + 100_000_000
    kernel.terminal_shutdown_started = terminal
    kernel.terminal_shutdown_quiescent = False
    kernel.terminal_shutdown_start_ns = (
        int(bt.current_timestamp) if terminal else None
    )
    kernel.force_decision = object() if force_present else None
    kernel.flatten_done = False
    kernel.bid = _slot()
    kernel.ask = _slot()
    kernel.q7_flatten_forensic_sink = []
    kernel.q7_eod_failure_sink = []
    kernel.q7_last_market_wakeup_ns = DAY_START_NS + 900_000_000
    kernel.q7_last_response_wakeup_ns = None
    kernel.q7_flatten_submit_attempts = 0
    return kernel


def _state_tuple(bt):
    state = bt.state_values(0)
    return (
        float(state.position),
        float(state.balance),
        float(state.fee),
        int(state.num_trades),
        float(state.trading_volume),
        float(state.trading_value),
    )


def test_q7_closed_by_default_and_exact_one_replay_scope(monkeypatch):
    monkeypatch.delenv(q7.AUTHORIZATION_ENV, raising=False)

    with pytest.raises(q7.FlattenEndOfDataForensicError, match="execution_gate_closed"):
        q7._require_authorization(
            authorization_token=q7.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )

    with pytest.raises(q7.FlattenEndOfDataForensicError, match="authorization_environment"):
        q7._require_authorization(
            authorization_token=q7.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert q7.FORENSIC_SCOPE == ((
        "2026-04-01", "M06", "Q0_STRESS_500_500"
    ),)
    assert q7.REAL_HISTORICAL_FORENSIC_EXECUTED is False
    assert q7.Q6_RERUN_AUTHORIZED is False


def test_q7_exact_authorization_and_q6_token_cannot_authorize(monkeypatch):
    monkeypatch.setenv(q7.AUTHORIZATION_ENV, q7.AUTHORIZATION_TOKEN)
    q7._require_authorization(
        authorization_token=q7.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )

    with pytest.raises(q7.FlattenEndOfDataForensicError, match="authorization_token"):
        q7._require_authorization(
            authorization_token=(
                "YES_REAL_HFTBACKTEST_V2_EXECUTION_QUALIFICATION_D6R20_Q6"
            ),
            execution_gate=True,
        )


def test_q6_failure_is_byte_frozen_with_exact_sha_and_facts():
    raw = q7.Q6_FAILURE_EVIDENCE_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == q7.Q6_FAILURE_SHA256
    payload = json.loads(raw)
    assert payload["head"] == q7.PARENT_HEAD
    assert payload["completed_qualification_replay_count"] == 17
    assert (
        payload["current_day"],
        payload["current_policy"],
        payload["current_scenario"],
    ) == q7.FORENSIC_SCOPE[0]
    assert payload["exception_type"] == "M4AdapterError"
    assert payload["exception_message"] == "flatten_rc:1"
    assert payload["canonical_attempt_consumed"] is False


def test_exact_rc_mapping_in_frozen_python_binding_source():
    assert driver.ELAPSE_RESULT_END_OF_DATA_RC == 1
    assert driver.BACKTEST_ERROR_ORDER_ID_EXIST_RC == 10
    assert driver.ELAPSE_RESULT_END_OF_DATA_RC != (
        driver.BACKTEST_ERROR_ORDER_ID_EXIST_RC
    )

    if SOURCE_ROOT_TEXT is None:
        pytest.skip("isolated upstream source root not supplied")

    source = (Path(SOURCE_ROOT_TEXT) / "py-hftbacktest/src/backtest.rs").read_text()
    assert "Ok(ElapseResult::EndOfData) => 1" in source
    assert "Err(BacktestError::OrderIdExist) => 10" in source


def test_actual_v2_rc_1_is_eod_and_rc_10_is_order_id_exist():
    h = _require_v2_engine()
    eod_bt = _build_backtest(h, end_ns=1_100_000_000, latency_ns=500_000_000)

    try:
        with pytest.raises(m4.M4AdapterError, match=r"^flatten_rc:1$"):
            m4.submit_forced_flatten(
                eod_bt,
                h,
                direction=LONG,
                qty=0.001,
                order_id=9001,
                wait=True,
            )
    finally:
        assert int(eod_bt.close()) == 0

    collision_bt = _build_backtest(
        h, end_ns=10_000_000_000, latency_ns=0
    )

    try:
        m4.submit_forced_flatten(
            collision_bt,
            h,
            direction=LONG,
            qty=0.001,
            order_id=9001,
            wait=True,
        )

        with pytest.raises(m4.M4AdapterError, match=r"^flatten_rc:10$"):
            m4.submit_forced_flatten(
                collision_bt,
                h,
                direction=LONG,
                qty=0.001,
                order_id=9001,
                wait=True,
            )
    finally:
        assert int(collision_bt.close()) == 0


@pytest.mark.parametrize(
    ("terminal", "force_present", "expected"),
    (
        (False, True, driver.STRATEGY_FLATTEN_EOD_WAIT),
        (True, False, driver.TERMINAL_SHUTDOWN_FLATTEN_EOD_WAIT),
        (False, False, driver.UNKNOWN_FLATTEN_EOD_WAIT),
    ),
)
def test_origin_classifier_exact(terminal, force_present, expected):
    assert driver.classify_flatten_origin(
        terminal_shutdown_started=terminal,
        force_decision_present=force_present,
    ) == expected


@pytest.mark.parametrize(
    ("terminal", "force_present", "expected"),
    (
        (False, True, driver.STRATEGY_FLATTEN_EOD_WAIT),
        (True, False, driver.TERMINAL_SHUTDOWN_FLATTEN_EOD_WAIT),
    ),
)
def test_actual_v2_eod_wrapper_capture_origin_and_no_retry(
    terminal, force_present, expected
):
    h = _require_v2_engine()
    bt = _build_backtest(h, end_ns=1_100_000_000, latency_ns=500_000_000)
    kernel = _bare_kernel(
        driver.FlattenEndOfDataForensicContinuousHistoricalPolicyKernel,
        bt=bt,
        h=h,
        terminal=terminal,
        force_present=force_present,
    )

    try:
        with pytest.raises(m4.M4AdapterError, match=r"^flatten_rc:1$"):
            kernel._execute_unique_flatten(direction=LONG, qty=0.001)

        assert kernel.q7_flatten_submit_attempts == 1
        assert kernel.next_flatten_order_id == 9001
        assert kernel.flatten_order_ids == []
        assert len(kernel.q7_flatten_forensic_sink) == 1
        assert len(kernel.q7_eod_failure_sink) == 1
        record = kernel.q7_eod_failure_sink[0]
        assert record["forensic_classification"] == expected
        assert record["original_exception_message"] == "flatten_rc:1"
        assert record["candidate_flatten_order_id"] == 9001
        assert record["candidate_order_existed_before_submit"] is False
        assert record["candidate_order_existed_after_submit"] is True
        assert record["end_of_data_rc"] == 1
        assert record["order_id_exist_rc"] == 10
        assert record["rc_1_is_order_id_collision"] is False
        assert record["retry_enabled"] is False
        assert record["before_submit_local_timestamp_ns"] == (
            DAY_START_NS + 1_000_000_000
        )
        assert record["after_submit_local_timestamp_ns"] == (
            DAY_START_NS + 1_000_000_000
        )
        assert record["clock_advancement_during_submit_wait_ns"] == 0
        assert record["remaining_ns_to_source_end_before_submit"] == 100_000_000
        assert record[
            "remaining_to_source_end_less_than_nominal_round_trip"
        ] is True
        order = record["candidate_order_after"]
        assert order["order_id"] == 9001
        assert order["order_type"] == int(h.MARKET)
        assert order["time_in_force"] == int(h.GTC)
        assert record["diagnostic_capture_errors"] == []
    finally:
        assert int(bt.close()) == 0


def _successful_flatten_trace(h, cls):
    bt = _build_backtest(h, end_ns=10_000_000_000, latency_ns=250_000_000)
    seed = m4.submit_forced_flatten(
        bt,
        h,
        direction=SHORT,
        qty=0.001,
        order_id=9000,
        wait=True,
    )
    assert int(seed.status) == int(h.FILLED)
    kernel = _bare_kernel(
        cls,
        bt=bt,
        h=h,
        terminal=False,
        force_present=True,
    )
    kernel.inventory_clock = d1.InventoryClock(
        position=-0.001,
        nonzero_since_local_ns=int(bt.current_timestamp),
    )
    kernel.next_flatten_order_id = 9001
    before_ns = int(bt.current_timestamp)
    kernel._execute_unique_flatten(direction=LONG, qty=0.001)
    return (
        bt,
        kernel,
        before_ns,
        int(bt.current_timestamp),
        _state_tuple(bt),
        deepcopy(kernel.bound_fills),
    )


def test_actual_v2_successful_flatten_is_observationally_identical_to_q6():
    h = _require_v2_engine()
    inherited = _successful_flatten_trace(
        h, q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel
    )
    observed = _successful_flatten_trace(
        h, driver.FlattenEndOfDataForensicContinuousHistoricalPolicyKernel
    )
    q6_bt, q6_kernel, q6_before, q6_after, q6_state, q6_fills = inherited
    q7_bt, q7_kernel, q7_before, q7_after, q7_state, q7_fills = observed

    try:
        assert q7_before == q6_before
        assert q7_after == q6_after
        assert q7_state == pytest.approx(q6_state, abs=1e-12)
        assert q7_kernel.flatten_order_ids == q6_kernel.flatten_order_ids == [9001]
        assert q7_kernel.next_flatten_order_id == q6_kernel.next_flatten_order_id
        assert q7_kernel.inventory_clock == q6_kernel.inventory_clock
        assert q7_fills == q6_fills
        assert len(q7_kernel.q7_flatten_forensic_sink) == 1
        assert q7_kernel.q7_eod_failure_sink == []
        assert q7_kernel.q7_flatten_forensic_sink[0]["outcome"] == (
            "FLATTEN_COMPLETED"
        )
        q6_order = q6_bt.orders(0).get(9001)
        q7_order = q7_bt.orders(0).get(9001)
        assert int(q7_order.order_id) == int(q6_order.order_id)
        assert int(q7_order.status) == int(q6_order.status)
        assert math.isclose(q7_order.exec_qty, q6_order.exec_qty, abs_tol=1e-12)
        assert math.isclose(q7_order.leaves_qty, q6_order.leaves_qty, abs_tol=1e-12)
    finally:
        assert int(q6_bt.close()) == 0
        assert int(q7_bt.close()) == 0


def test_driver_calls_inherited_unique_flatten_once_and_has_no_recovery():
    source = Path(driver.__file__).read_text()
    method = source[source.index("    def _execute_unique_flatten("):]
    assert method.count("super()._execute_unique_flatten(") == 1
    assert "submit_forced_flatten(" not in source
    assert driver.FLATTEN_RECOVERY_ENABLED is False
    assert driver.FLATTEN_RETRY_ENABLED is False
    assert driver.EXECUTION_SEMANTICS_CHANGED is False


def test_forensic_entrypoint_writes_result_then_preserves_original_error(
    monkeypatch, tmp_path
):
    result = tmp_path / "result.json"
    failure = tmp_path / "failure.json"
    monkeypatch.setattr(q7, "RESULT_ROOT", tmp_path)
    monkeypatch.setattr(q7, "RESULT_PATH", result)
    monkeypatch.setattr(q7, "FAILURE_PATH", failure)
    monkeypatch.setenv(q7.AUTHORIZATION_ENV, q7.AUTHORIZATION_TOKEN)
    repository = q7.ForensicRepositoryIdentity(
        branch=q7.EXPECTED_BRANCH,
        head="a" * 40,
        remote_ref=q7.EXPECTED_REMOTE_REF,
        remote_head="a" * 40,
        tracked_worktree_clean=True,
        permitted_untracked_paths=(),
        frozen_blobs_verified=True,
        v2_patch_sha256=q7.V2_PATCH_SHA256,
        q6_failure_sha256=q7.Q6_FAILURE_SHA256,
        canonical_runners_absent=True,
        result_surface_virgin=True,
    )
    runtime = SimpleNamespace(
        version="2.4.4",
        compiled_artifact_sha256=q7.HFTBACKTEST_BINARY_SHA256,
        verified=True,
    )
    source_path = tmp_path / "synthetic.npy"
    source_path.write_bytes(b"synthetic")

    class Source:
        path = source_path

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(q7, "validate_repository_preflight", lambda: repository)
    monkeypatch.setattr(q7, "_hftbacktest_module", lambda: object())
    monkeypatch.setattr(q7, "validate_runtime_identity", lambda _h: runtime)
    monkeypatch.setattr(q7, "validate_forensic_contract", lambda: None)
    monkeypatch.setattr(q7, "load_forensic_support", lambda: object())
    monkeypatch.setattr(
        q7,
        "open_verified_forensic_source",
        lambda **_kwargs: Source(),
    )
    monkeypatch.setattr(q7.base, "_stat_identity", lambda _path: (1, 2, 3))

    calls = []

    def fail_once(_source, **kwargs):
        calls.append("submit")
        record = {
            "forensic_classification": driver.STRATEGY_FLATTEN_EOD_WAIT,
            "original_exception_message": "flatten_rc:1",
        }
        kwargs["forensic_sink"].append(record)
        kwargs["eod_failure_sink"].append(deepcopy(record))
        raise m4.M4AdapterError("flatten_rc:1")

    monkeypatch.setattr(q7, "run_bound_forensic_replay", fail_once)

    with pytest.raises(m4.M4AdapterError, match=r"^flatten_rc:1$"):
        q7.run_flatten_end_of_data_forensic(
            authorization_token=q7.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert calls == ["submit"]
    assert result.exists()
    assert not failure.exists()
    payload = json.loads(result.read_text())
    assert payload["status"] == "FLATTEN_END_OF_DATA_FORENSIC_CAPTURED"
    assert payload["flatten_eod_failure_count"] == 1
    assert payload["retry_performed"] is False
    assert payload["replay_continued_after_failure"] is False
    assert payload["canonical_attempt_consumed"] is False
    assert payload["economic_arena_called"] is False


def test_forensic_contract_binds_q7_over_exact_q6_lineage():
    q7.validate_forensic_contract()
    assert q7.HISTORICAL_KERNEL is (
        driver.FlattenEndOfDataForensicContinuousHistoricalPolicyKernel
    )
    assert issubclass(q7.HISTORICAL_KERNEL, q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel)
    assert q7.HFTBACKTEST_BINARY_SHA256 == (
        "5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752"
    )


def test_result_surface_is_isolated_and_overwrite_refused(monkeypatch, tmp_path):
    production_root = str(q7.RESULT_ROOT)
    result = tmp_path / "q7" / "result.json"
    monkeypatch.setattr(q7, "RESULT_PATH", result)
    monkeypatch.setattr(q7, "FAILURE_PATH", tmp_path / "q7" / "failure.json")
    monkeypatch.setattr(q7, "RESULT_ROOT", tmp_path / "q7")
    q7._write_json_new(result, {"one": 1})

    with pytest.raises(q7.FlattenEndOfDataForensicError, match="forensic_result_exists"):
        q7._write_json_new(result, {"two": 2})

    assert "q7_flatten_end_of_data_forensic" in production_root
    assert "q6_real_engine_qualification" not in production_root


def test_no_economic_or_canonical_execution_surface():
    assert q7.CANONICAL_RUNNER_IMPLEMENTED is False
    assert q7.CANONICAL_ECONOMIC_ATTEMPT is False
    assert q7.CANONICAL_ATTEMPT_CONSUMED is False
    assert q7.ECONOMIC_ARENA_CALLED is False
    assert q7.STRATEGY_RANKING_PERFORMED is False
    assert q7.AUTOMATIC_RETRY is False
    source = Path(q7.__file__).read_text()
    assert "run_economic_arena(" not in source
    assert "account_fill_bucket(" not in source
    assert "profit" not in source.lower()
    assert "pnl" not in source.lower()

from __future__ import annotations

from dataclasses import fields
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path

import pytest

from multimarket import dev045_d6r17_direct_action_support as direct
from multimarket import dev045_d6r20_q4_scheduler_reconciled_driver as q4
from multimarket import dev045_d6r20_q6_initial_book_readiness_driver as q6_driver
from multimarket import dev045_d6r20_q7_flatten_end_of_data_forensic_driver as q7_driver
from multimarket import dev045_d6r20_q8_real_engine_qualification as q8
from multimarket import dev045_d6r20_q8_terminal_shutdown_grid_alignment_driver as driver
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket.dev044_t0_strategy_contract import SHORT


V2_ENGINE_TEST_ENABLED = os.environ.get("DEV045_Q8_V2_ENGINE_TEST") == "1"
EXPECTED_BINARY_SHA256 = os.environ.get("DEV045_Q8_TEST_ENGINE_SHA256")

SOURCE_END_NS = 1_775_087_999_958_615_000
STRESS_LEAD_NS = 3_000_000_000
STRESS_RAW_CUTOFF_NS = 1_775_087_996_958_615_000
STRESS_ALIGNED_CUTOFF_NS = 1_775_087_996_000_000_000
PRIMARY_LEAD_NS = 2_000_000_000
PRIMARY_RAW_CUTOFF_NS = 1_775_087_997_958_615_000
PRIMARY_ALIGNED_CUTOFF_NS = 1_775_087_997_000_000_000
GRID_NS = 1_000_000_000

PRIMARY = "Q0_PRIMARY_250_250"
STRESS = "Q0_STRESS_500_500"


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


def _event_data(h, *, first_ns: int, source_end_ns: int):
    import numpy as np

    data = np.zeros(2, dtype=h.event_dtype)

    for index, timestamp in enumerate((int(first_ns), int(source_end_ns))):
        data[index]["ev"] = int(
            h.DEPTH_EVENT | h.EXCH_EVENT | h.LOCAL_EVENT | h.SELL_EVENT
        )
        data[index]["exch_ts"] = timestamp
        data[index]["local_ts"] = timestamp
        data[index]["px"] = 100.1
        data[index]["qty"] = 8.0

    return data


def _build_terminal_backtest(
    h, *, source_end_ns: int, latency_ns: int, first_ns: int
):
    asset = (
        h.BacktestAsset()
        .data([_event_data(h, first_ns=first_ns, source_end_ns=source_end_ns)])
        .initial_snapshot(m4.make_initial_snapshot())
        .linear_asset(1.0)
        .constant_order_latency(latency_ns, latency_ns)
        .risk_adverse_queue_model()
        .partial_fill_exchange()
        .trading_value_fee_model(0.001, 0.002)
        .tick_size(p.TICK_SIZE)
        .lot_size(p.LOT_SIZE)
    )
    bt = h.HashMapMarketDepthBacktest([asset])
    assert int(bt.wait_next_feed(False, 2_000_000_000)) == 2
    seed = m4.submit_forced_flatten(
        bt,
        h,
        direction=SHORT,
        qty=0.002,
        order_id=8001,
        wait=True,
    )
    assert int(seed.status) == int(h.FILLED)
    assert math.isclose(bt.position(0), -0.002, abs_tol=1e-12)
    return bt


def _kernel(h, bt, cls, *, scenario: str, source_end_ns: int):
    kernel = cls(
        bt=bt,
        h=h,
        policy_id="M06",
        day="2026-04-01",
        scenario=scenario,
        terminal_source_local_ns=source_end_ns,
        direct_index=direct.DirectActionIndex(
            day="2026-04-01",
            policy_id="M06",
            points=(),
        ),
    )
    kernel.inventory_clock = d1.InventoryClock(
        position=-0.002,
        nonzero_since_local_ns=int(bt.current_timestamp),
    )
    return kernel


def _advance_to(bt, target_ns: int):
    timeout = int(target_ns) - int(bt.current_timestamp)
    assert timeout >= 0
    assert int(bt.wait_next_feed(True, timeout)) == 0
    assert int(bt.current_timestamp) == int(target_ns)


def _simulate_terminal_clearance_then_flatten(
    kernel, *, terminal_start_ns: int, clearance_delay_ns: int
):
    _advance_to(kernel.bt, terminal_start_ns)
    kernel.terminal_shutdown_started = True
    kernel.terminal_shutdown_start_ns = int(terminal_start_ns)
    kernel.terminal_shutdown_quiescent = False
    kernel.force_decision = None
    _advance_to(kernel.bt, terminal_start_ns + clearance_delay_ns)
    kernel._advance_terminal_shutdown()


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


def test_a_exact_april_stress_cutoff_arithmetic():
    raw = SOURCE_END_NS - STRESS_LEAD_NS
    aligned = driver.align_terminal_shutdown_cutoff_to_base_grid(
        raw_terminal_shutdown_cutoff_ns=raw
    )
    assert raw == STRESS_RAW_CUTOFF_NS
    assert aligned == STRESS_ALIGNED_CUTOFF_NS
    assert raw - aligned == 958_615_000
    assert aligned < raw < aligned + GRID_NS
    assert aligned <= raw
    assert 0 <= raw - aligned < d1.BASE_MAKER_STEP_NS
    assert SOURCE_END_NS - aligned == 3_958_615_000
    assert SOURCE_END_NS - aligned >= STRESS_LEAD_NS


def test_b_exact_aligned_raw_cutoff_has_no_extra_shift():
    exact = 1_775_087_996_000_000_000
    assert d1.is_base_policy_epoch_local(exact)
    assert driver.align_terminal_shutdown_cutoff_to_base_grid(
        raw_terminal_shutdown_cutoff_ns=exact
    ) == exact


@pytest.mark.parametrize(
    ("scenario", "lead", "raw", "aligned", "nominal_round_trip"),
    (
        (PRIMARY, PRIMARY_LEAD_NS, PRIMARY_RAW_CUTOFF_NS,
         PRIMARY_ALIGNED_CUTOFF_NS, 500_000_000),
        (STRESS, STRESS_LEAD_NS, STRESS_RAW_CUTOFF_NS,
         STRESS_ALIGNED_CUTOFF_NS, 1_000_000_000),
    ),
)
def test_primary_and_stress_alignment_preserve_full_response_slack(
    scenario, lead, raw, aligned, nominal_round_trip
):
    assert SOURCE_END_NS - lead == raw
    assert driver.align_terminal_shutdown_cutoff_to_base_grid(
        raw_terminal_shutdown_cutoff_ns=raw
    ) == aligned
    assert SOURCE_END_NS - aligned >= lead
    assert SOURCE_END_NS - aligned >= (
        d1.BASE_MAKER_STEP_NS + 2 * nominal_round_trip
    )
    assert base_lead(scenario) == lead


def base_lead(scenario: str) -> int:
    from multimarket import dev045_d6r17_real_historical_economic_driver as base

    return base.terminal_shutdown_lead_ns(scenario)


def test_q7_result_is_exact_and_proves_the_41_385ms_gap():
    raw = q8.Q7_RESULT_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == q8.Q7_RESULT_SHA256
    payload = json.loads(raw)
    record = payload["flatten_end_of_data"]
    assert payload["forensic_classification"] == (
        q7_driver.TERMINAL_SHUTDOWN_FLATTEN_EOD_WAIT
    )
    assert record["before_submit_local_timestamp_ns"] == 1_775_087_999_000_000_000
    assert record["terminal_source_local_ns"] == SOURCE_END_NS
    assert record["remaining_ns_to_source_end_before_submit"] == 958_615_000
    assert record["expected_nominal_request_round_trip_ns"] == 1_000_000_000
    assert 1_000_000_000 - 958_615_000 == 41_385_000
    assert record["latest_order_latency_tuple"] == [
        1_775_087_999_000_000_000,
        1_775_087_999_500_000_000,
        1_775_088_000_000_000_000,
    ]
    order = record["candidate_order_after"]
    assert order["order_id"] == 4998
    assert order["status"] == 3
    assert order["exec_qty"] == 0.002
    assert order["leaves_qty"] == 0.0
    assert record["simulator_position_before_submit"] == -0.002
    assert record["simulator_position_after_submit"] == 0.0
    assert record["inventory_clock_position_after_submit"] == -0.002
    assert record["candidate_order_existed_before_submit"] is False
    assert record["candidate_order_existed_after_submit"] is True


def test_c_d_actual_v2_q6_failure_and_q8_corrected_terminal_lifecycle():
    h = _require_v2_engine()
    first = STRESS_ALIGNED_CUTOFF_NS - 3_000_000_000
    q6_bt = _build_terminal_backtest(
        h,
        source_end_ns=SOURCE_END_NS,
        latency_ns=500_000_000,
        first_ns=first,
    )
    q8_bt = _build_terminal_backtest(
        h,
        source_end_ns=SOURCE_END_NS,
        latency_ns=500_000_000,
        first_ns=first,
    )
    q6_kernel = _kernel(
        h,
        q6_bt,
        q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel,
        scenario=STRESS,
        source_end_ns=SOURCE_END_NS,
    )
    q8_kernel = _kernel(
        h,
        q8_bt,
        driver.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel,
        scenario=STRESS,
        source_end_ns=SOURCE_END_NS,
    )
    q6_start = STRESS_RAW_CUTOFF_NS // GRID_NS * GRID_NS + GRID_NS
    assert q6_start == 1_775_087_997_000_000_000

    try:
        with pytest.raises(m4.M4AdapterError, match=r"^flatten_rc:1$"):
            _simulate_terminal_clearance_then_flatten(
                q6_kernel,
                terminal_start_ns=q6_start,
                clearance_delay_ns=2_000_000_000,
            )

        q6_candidate = q6_bt.orders(0).get(q6_kernel.next_flatten_order_id)
        assert q6_candidate is not None
        assert int(q6_candidate.status) == int(h.FILLED)
        assert math.isclose(q6_candidate.exec_qty, 0.002, abs_tol=1e-12)
        assert abs(q6_candidate.leaves_qty) <= 1e-12
        assert abs(q6_bt.position(0)) <= 1e-12
        assert math.isclose(
            q6_kernel.inventory_clock.position, -0.002, abs_tol=1e-12
        )
        assert SOURCE_END_NS - int(q6_bt.current_timestamp) == 958_615_000
        assert 958_615_000 < 1_000_000_000
        assert q6_kernel.flatten_order_ids == []
        assert q6_kernel.terminal_shutdown_quiescent is False

        _simulate_terminal_clearance_then_flatten(
            q8_kernel,
            terminal_start_ns=STRESS_ALIGNED_CUTOFF_NS,
            clearance_delay_ns=2_000_000_000,
        )
        assert int(q8_bt.current_timestamp) == 1_775_087_999_000_000_000
        assert SOURCE_END_NS - int(q8_bt.current_timestamp) == 958_615_000
        assert abs(q8_bt.position(0)) <= 1e-12
        assert q8_kernel.inventory_clock == d1.InventoryClock.flat()
        assert q8_kernel.terminal_shutdown_quiescent is True
        assert q8_kernel.flatten_order_ids == [4901]
        assert len(q8_kernel.bound_fills) == 1
        fill = q8_kernel.bound_fills[0].fill
        assert fill is not None
        assert fill.liquidity == "TAKER"
        assert fill.side == "BUY"
        assert math.isclose(fill.qty, 0.002, abs_tol=1e-12)
        diagnostics = q8_kernel.terminal_shutdown_alignment_diagnostics()
        assert diagnostics == {
            "raw_terminal_shutdown_cutoff_ns": STRESS_RAW_CUTOFF_NS,
            "aligned_terminal_shutdown_cutoff_ns": STRESS_ALIGNED_CUTOFF_NS,
            "cutoff_alignment_shift_ns": 958_615_000,
            "frozen_terminal_shutdown_lead_ns": STRESS_LEAD_NS,
            "actual_terminal_shutdown_start_ns": STRESS_ALIGNED_CUTOFF_NS,
            "remaining_ns_at_shutdown_start": 3_958_615_000,
            "terminal_start_no_later_than_raw_cutoff": True,
            "terminal_lead_preserved": True,
        }
    finally:
        assert int(q6_bt.close()) == 0
        assert int(q8_bt.close()) == 0


def _first_policy_trace(h, cls):
    day_start = int(
        datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
        * 1_000_000_000
    )
    source_end = day_start + 20_000_000_000
    asset = m4.build_asset(
        _event_data(
            h,
            first_ns=day_start + 373_615_000,
            source_end_ns=source_end,
        ),
        entry_latency_ns=250_000_000,
        response_latency_ns=250_000_000,
    )
    bt = h.HashMapMarketDepthBacktest([asset])
    kernel = cls(
        bt=bt,
        h=h,
        policy_id="M01",
        day="2026-01-01",
        scenario=PRIMARY,
        terminal_source_local_ns=source_end,
        direct_index=None,
    )
    assert int(bt.wait_next_feed(True, 10_000_000_000)) == 2
    kernel.market_wakeups += 1
    kernel._capture_last_trades()
    target = d1.next_base_policy_epoch_after(int(bt.current_timestamp))
    _advance_to(bt, target)
    following = kernel._consume_due_policy_target(next_policy_ns=target)
    order_ids = []
    values = bt.orders(0).values()

    while True:
        order = values.next()

        if order is None:
            break

        order_ids.append((
            int(order.order_id), int(order.side), int(order.status),
            int(order.req), int(order.price_tick), float(order.qty),
        ))

    return bt, kernel, target, following, tuple(sorted(order_ids)), _state_tuple(bt)


def test_f_actual_v2_execution_parity_when_raw_cutoff_is_already_aligned():
    h = _require_v2_engine()
    q6_trace = _first_policy_trace(
        h, q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel
    )
    q8_trace = _first_policy_trace(
        h, driver.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel
    )
    q6_bt, q6_kernel, q6_target, q6_following, q6_orders, q6_state = q6_trace
    q8_bt, q8_kernel, q8_target, q8_following, q8_orders, q8_state = q8_trace

    try:
        assert q8_kernel.raw_terminal_shutdown_cutoff_ns == (
            q8_kernel.aligned_terminal_shutdown_cutoff_ns
        )
        assert q8_kernel.cutoff_alignment_shift_ns == 0
        assert q8_target == q6_target
        assert q8_following == q6_following
        assert q8_kernel.decision_trace == q6_kernel.decision_trace
        assert q8_orders == q6_orders
        assert q8_state == pytest.approx(q6_state, abs=1e-12)
        assert q8_kernel.bound_fills == q6_kernel.bound_fills
        assert q8_kernel.submit_requests == q6_kernel.submit_requests
        assert q8_kernel.cancel_requests == q6_kernel.cancel_requests
        assert q8_kernel.inventory_clock == q6_kernel.inventory_clock
    finally:
        assert int(q6_bt.close()) == 0
        assert int(q8_bt.close()) == 0


def _ordinary_residual_flatten_trace(h, cls):
    day_start = int(
        datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
        * 1_000_000_000
    )
    source_end = day_start + 20_000_000_000
    bt = _build_terminal_backtest(
        h,
        source_end_ns=source_end,
        latency_ns=250_000_000,
        first_ns=day_start + 1_000_000_000,
    )
    kernel = cls(
        bt=bt,
        h=h,
        policy_id="M01",
        day="2026-01-01",
        scenario=PRIMARY,
        terminal_source_local_ns=source_end,
        direct_index=None,
    )
    kernel.inventory_clock = d1.InventoryClock(
        position=-0.002,
        nonzero_since_local_ns=int(bt.current_timestamp),
    )
    kernel.force_decision = object()
    kernel.flatten_done = False
    before = _state_tuple(bt)
    before_ns = int(bt.current_timestamp)
    kernel._maybe_execute_forced_flatten()
    return bt, kernel, before, before_ns, _state_tuple(bt), int(bt.current_timestamp)


def test_f_actual_v2_ordinary_residual_flatten_and_accounting_parity():
    h = _require_v2_engine()
    q6_trace = _ordinary_residual_flatten_trace(
        h, q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel
    )
    q8_trace = _ordinary_residual_flatten_trace(
        h, driver.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel
    )
    q6_bt, q6_kernel, q6_before, q6_before_ns, q6_after, q6_after_ns = q6_trace
    q8_bt, q8_kernel, q8_before, q8_before_ns, q8_after, q8_after_ns = q8_trace

    try:
        assert q8_kernel.cutoff_alignment_shift_ns == 0
        assert q8_before == pytest.approx(q6_before, abs=1e-12)
        assert q8_after == pytest.approx(q6_after, abs=1e-12)
        assert q8_before_ns == q6_before_ns
        assert q8_after_ns == q6_after_ns
        assert q8_kernel.flatten_order_ids == q6_kernel.flatten_order_ids == [4901]
        assert q8_kernel.completed_forced_flattens == (
            q6_kernel.completed_forced_flattens
        ) == 1
        assert q8_kernel.force_decision is q6_kernel.force_decision is None
        assert q8_kernel.inventory_clock == q6_kernel.inventory_clock
        assert q8_kernel.bound_fills == q6_kernel.bound_fills
        assert len(q8_kernel.bound_fills) == 1
        q8_fill = q8_kernel.bound_fills[0].fill
        q6_fill = q6_kernel.bound_fills[0].fill
        assert q8_fill == q6_fill
        assert q8_fill is not None
        assert q8_fill.side == "BUY"
        assert q8_fill.liquidity == "TAKER"
        assert math.isclose(q8_fill.qty, 0.002, abs_tol=1e-12)
        assert abs(q8_bt.position(0)) <= 1e-12
        assert abs(q6_bt.position(0)) <= 1e-12
    finally:
        assert int(q6_bt.close()) == 0
        assert int(q8_bt.close()) == 0


def test_e_q8_does_not_reinterpret_or_recover_flatten_rc_1():
    source = Path(driver.__file__).read_text()
    assert "flatten_rc:1" not in source
    assert "submit_forced_flatten(" not in source
    assert "bind_forced_flatten" not in source
    assert "_execute_unique_flatten" not in source
    assert "_advance_terminal_shutdown" not in source
    assert driver.END_OF_DATA_SUCCESS_ENABLED is False
    assert driver.MANUAL_POST_EOD_FILL_BINDING_ENABLED is False
    assert driver.FLATTEN_RETRY_ENABLED is False
    assert driver.SYNTHESIZED_RESPONSE_ENABLED is False


def test_i_j_same_timestamp_ordering_and_shutdown_blocking_are_inherited():
    cls = driver.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel
    parent = q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel
    assert cls.run_full_day is parent.run_full_day
    assert cls._consume_due_policy_target is parent._consume_due_policy_target
    assert cls._process_response_batch is parent._process_response_batch
    assert cls._reconcile_policy_target is parent._reconcile_policy_target
    assert cls._evaluate_policy_epoch is parent._evaluate_policy_epoch
    assert cls._execute_unique_flatten is parent._execute_unique_flatten
    assert cls._maybe_execute_forced_flatten is parent._maybe_execute_forced_flatten
    assert cls._maintain_side is parent._maintain_side
    assert cls._submit_side is parent._submit_side
    assert issubclass(cls, parent)
    assert parent._reconcile_policy_target is q4.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel._reconcile_policy_target


def test_no_policy_or_replacement_after_aligned_trigger_actual_v2():
    h = _require_v2_engine()
    first = STRESS_ALIGNED_CUTOFF_NS - 3_000_000_000
    bt = _build_terminal_backtest(
        h,
        source_end_ns=SOURCE_END_NS,
        latency_ns=500_000_000,
        first_ns=first,
    )
    kernel = _kernel(
        h,
        bt,
        driver.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel,
        scenario=STRESS,
        source_end_ns=SOURCE_END_NS,
    )
    kernel.inventory_clock = d1.InventoryClock.flat()

    # Remove the seeded inventory only through a real synchronous taker fill.
    m4.submit_forced_flatten(
        bt,
        h,
        direction=1,
        qty=0.002,
        order_id=8002,
        wait=True,
    )
    assert abs(bt.position(0)) <= 1e-12
    _advance_to(bt, STRESS_ALIGNED_CUTOFF_NS)
    before_policy_epochs = kernel.policy_epochs
    following = kernel._consume_due_policy_target(
        next_policy_ns=STRESS_ALIGNED_CUTOFF_NS
    )
    assert following > STRESS_ALIGNED_CUTOFF_NS
    assert kernel.terminal_shutdown_started is True
    assert kernel.terminal_shutdown_quiescent is True
    assert kernel.policy_epochs == before_policy_epochs == 0
    assert kernel.bid.order_id is None
    assert kernel.ask.order_id is None
    assert not getattr(kernel.bid, "replacement_required", False)
    assert not getattr(kernel.ask, "replacement_required", False)
    assert kernel.submit_requests == 0
    assert int(bt.close()) == 0


def test_q8_qualification_contract_matrix_auth_and_result_isolation(monkeypatch):
    monkeypatch.delenv(q8.AUTHORIZATION_ENV, raising=False)

    with pytest.raises(q8.QualificationError, match="execution_gate_closed"):
        q8._require_authorization(
            authorization_token=q8.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )

    monkeypatch.setenv(q8.AUTHORIZATION_ENV, q8.AUTHORIZATION_TOKEN)
    q8._require_authorization(
        authorization_token=q8.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )

    with pytest.raises(q8.QualificationError, match="authorization_token"):
        q8._require_authorization(
            authorization_token=(
                "YES_REAL_HFTBACKTEST_FLATTEN_END_OF_DATA_FORENSIC_D6R20_Q7"
            ),
            execution_gate=True,
        )

    assert q8.EXPERIMENT_ID == "DEV045-D6R20-Q8"
    assert len(q8.QUALIFICATION_PLAN) == 20
    assert sum(day == "2026-01-01" for day, _, _ in q8.QUALIFICATION_PLAN) == 16
    assert sum(day == "2026-04-01" for day, _, _ in q8.QUALIFICATION_PLAN) == 4
    assert q8.HISTORICAL_KERNEL is (
        driver.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel
    )
    assert "q8_real_engine_qualification" in str(q8.RESULT_ROOT)
    assert "q7_flatten_end_of_data" not in str(q8.RESULT_ROOT)
    assert q8.REAL_HISTORICAL_QUALIFICATION_EXECUTED is False
    assert q8.Q6_RERUN_AUTHORIZED is False
    assert q8.Q7_RERUN_AUTHORIZED is False
    assert q8.CANONICAL_ECONOMIC_ATTEMPT is False
    assert q8.ECONOMIC_ARENA_EXECUTED is False
    assert q8.STRATEGY_RANKING_PERFORMED is False
    q8.validate_qualification_contract()


def test_q8_diagnostics_extend_q6_without_removing_frozen_fields():
    q6_fields = {field.name for field in fields(q8.q6.ReplayExecutionDiagnostics)}
    q8_fields = {field.name for field in fields(q8.ReplayExecutionDiagnostics)}
    assert q6_fields < q8_fields
    assert {
        "raw_terminal_shutdown_cutoff_ns",
        "aligned_terminal_shutdown_cutoff_ns",
        "cutoff_alignment_shift_ns",
        "frozen_terminal_shutdown_lead_ns",
        "actual_terminal_shutdown_start_ns",
        "remaining_ns_at_shutdown_start",
        "terminal_start_no_later_than_raw_cutoff",
        "terminal_lead_preserved",
        "inventory_clock_matches_terminal_position",
    } <= q8_fields


def test_result_overwrite_refused_and_no_economic_surface(monkeypatch, tmp_path):
    result = tmp_path / "q8" / "result.json"
    monkeypatch.setattr(q8, "RESULT_ROOT", tmp_path / "q8")
    monkeypatch.setattr(q8, "SUCCESS_RESULT_PATH", result)
    monkeypatch.setattr(q8, "FAILURE_RESULT_PATH", tmp_path / "q8" / "failure.json")
    q8._write_json_new(result, {"one": 1})

    with pytest.raises(q8.QualificationError, match="result_exists"):
        q8._write_json_new(result, {"two": 2})

    source = Path(q8.__file__).read_text().lower()
    assert "run_economic_arena(" not in source
    assert "account_fill_bucket(" not in source
    assert "profit" not in source
    assert "pnl" not in source


def test_dedicated_workflow_is_v2_synthetic_only_and_installs_dependencies():
    workflow = (
        q8.REPOSITORY_ROOT
        / ".github/workflows/"
        "dev045_d6r20_q8_terminal_shutdown_grid_alignment_contract.yml"
    ).read_text()
    assert "a244a14250b42d97fc305569c93c4117cd5e1dff" in workflow
    assert "patch_hftbacktest_244_safe_v2.py" in workflow
    assert "--no-deps" not in workflow
    assert "DEV045_Q8_V2_ENGINE_TEST=1" in workflow
    assert "tests/test_dev045_d6r20_q8_terminal_shutdown_grid_alignment.py" in workflow
    assert "DEV045_D6R20_Q8_AUTHORIZE" not in workflow
    assert "run_real_engine_qualification" not in workflow
    assert "HISTORICAL_SOURCE_OPENED_IN_CI=NO" in workflow
    assert "CANONICAL_ECONOMICS_EXECUTED_IN_CI=NO" in workflow

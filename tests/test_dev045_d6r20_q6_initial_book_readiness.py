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

from multimarket import dev045_d6r17_direct_action_support as direct
from multimarket import dev045_d6r20_q4_scheduler_reconciled_driver as q4_driver
from multimarket import dev045_d6r20_q5_invalid_local_book_driver as q5_driver
from multimarket import dev045_d6r20_q6_initial_book_readiness_driver as q6_driver
from multimarket import dev045_d6r20_q6_real_engine_qualification as q6
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket import dev045_m6_event_loop_kernel as d2


V2_ENGINE_TEST_ENABLED = os.environ.get("DEV045_Q6_V2_ENGINE_TEST") == "1"
DAY_APR_START_NS = int(
    datetime(2026, 4, 1, tzinfo=timezone.utc).timestamp()
    * 1_000_000_000
)
DAY_JAN_START_NS = int(
    datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
    * 1_000_000_000
)
TRADE_NS = 373_615_000
DEPTH_NS = 1_136_017_000
SYNTH_START_NS = 0
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
    expected = os.environ.get("DEV045_Q6_TEST_ENGINE_SHA256")

    if expected is not None:
        assert observed == expected

    return h


def _event_row(h, array, index, *, event, side, timestamp, price, qty):
    array[index]["ev"] = int(event | h.EXCH_EVENT | h.LOCAL_EVENT | side)
    array[index]["exch_ts"] = int(timestamp)
    array[index]["local_ts"] = int(timestamp)
    array[index]["px"] = float(price)
    array[index]["qty"] = float(qty)


def _startup_asset(h, *, depth_offset_ns: int):
    import numpy as np

    data = np.zeros(4, dtype=h.event_dtype)
    _event_row(
        h,
        data,
        0,
        event=h.TRADE_EVENT,
        side=h.BUY_EVENT,
        timestamp=SYNTH_START_NS + TRADE_NS,
        price=100.0,
        qty=0.001,
    )
    _event_row(
        h,
        data,
        1,
        event=h.DEPTH_SNAPSHOT_EVENT,
        side=h.BUY_EVENT,
        timestamp=SYNTH_START_NS + depth_offset_ns,
        price=100.0,
        qty=8.0,
    )
    _event_row(
        h,
        data,
        2,
        event=h.DEPTH_SNAPSHOT_EVENT,
        side=h.SELL_EVENT,
        timestamp=SYNTH_START_NS + depth_offset_ns,
        price=100.1,
        qty=8.0,
    )
    _event_row(
        h,
        data,
        3,
        event=h.DEPTH_EVENT,
        side=h.SELL_EVENT,
        timestamp=SYNTH_START_NS + 20_000_000_000,
        price=100.1,
        qty=8.0,
    )
    asset = (
        h.BacktestAsset()
        .parallel_load(False)
        .latency_offset(0)
        .data(data)
        .linear_asset(1.0)
        .constant_order_latency(250_000_000, 250_000_000)
        .risk_adverse_queue_model()
        .partial_fill_exchange()
        .trading_value_fee_model(0.001, 0.002)
        .tick_size(p.TICK_SIZE)
        .lot_size(p.LOT_SIZE)
        .last_trades_capacity(4096)
    )
    return asset, data


def _april_kernel(h, bt, cls):
    return cls(
        bt=bt,
        h=h,
        policy_id="M06",
        day="2026-04-01",
        scenario=PRIMARY,
        terminal_source_local_ns=SYNTH_START_NS + 20_000_000_000,
        direct_index=direct.DirectActionIndex(
            day="2026-04-01",
            policy_id="M06",
            points=(),
        ),
    )


def _initialize_to_first_trade(kernel):
    assert int(kernel.bt.wait_next_feed(True, 10_000_000_000)) == 2
    assert int(kernel.bt.current_timestamp) == SYNTH_START_NS + TRADE_NS
    kernel.market_wakeups += 1
    kernel._capture_last_trades()
    target = d1.next_base_policy_epoch_after(
        int(kernel.bt.current_timestamp)
    )
    assert target == SYNTH_START_NS + 1_000_000_000
    assert int(
        kernel.bt.wait_next_feed(
            True,
            target - int(kernel.bt.current_timestamp),
        )
    ) == 0
    assert int(kernel.bt.current_timestamp) == target
    return target


def _order_tuple(order_dict):
    values = order_dict.values()
    result = []

    while True:
        order = values.next()

        if order is None:
            return tuple(sorted(result))

        result.append(
            (
                int(order.order_id),
                int(order.side),
                int(order.status),
                int(order.req),
                int(order.price_tick),
                float(order.qty),
                float(order.leaves_qty),
            )
        )


def test_a_actual_v2_exact_april_q4_failure_and_q6_startup_gate(monkeypatch):
    h = _require_v2_engine()
    q4_asset, q4_data = _startup_asset(h, depth_offset_ns=DEPTH_NS)
    q6_asset, q6_data = _startup_asset(h, depth_offset_ns=DEPTH_NS)
    q4_bt = h.HashMapMarketDepthBacktest(
        [q4_asset]
    )
    q6_bt = h.HashMapMarketDepthBacktest(
        [q6_asset]
    )
    assert len(q4_data) == len(q6_data) == 4

    try:
        q4_kernel = _april_kernel(
            h,
            q4_bt,
            q4_driver.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel,
        )
        q6_kernel = _april_kernel(
            h,
            q6_bt,
            q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel,
        )
        q4_target = _initialize_to_first_trade(q4_kernel)
        q6_target = _initialize_to_first_trade(q6_kernel)
        assert q4_target == q6_target == SYNTH_START_NS + 1_000_000_000
        q4_depth = q4_bt.depth(0)
        assert int(q4_depth.best_bid_tick) == -(2**63)
        assert int(q4_depth.best_ask_tick) == 2**63 - 1

        with pytest.raises(d2.EventLoopKernelError, match="^invalid_local_book$"):
            q4_kernel._consume_due_policy_target(next_policy_ns=q4_target)

        monkeypatch.setattr(
            q6_kernel,
            "_adapter_decision",
            lambda **kwargs: (_ for _ in ()).throw(
                AssertionError("adapter/direct support reached while unready")
            ),
        )
        next_target = q6_kernel._consume_due_policy_target(
            next_policy_ns=q6_target
        )
        assert next_target == SYNTH_START_NS + 2_000_000_000
        assert q6_kernel.policy_epochs == 0
        assert q6_kernel.adapter_candidate_epochs == 0
        assert q6_kernel.direct_action_queries == 0
        assert q6_kernel.submit_requests == 0
        assert q6_kernel.cancel_requests == 0
        assert _order_tuple(q6_bt.orders(0)) == ()
        assert q6_kernel.initial_book_ready is False
        assert q6_kernel.startup_policy_epoch_timestamps_skipped == [q6_target]
    finally:
        assert int(q4_bt.close()) == 0
        assert int(q6_bt.close()) == 0


def test_c_actual_v2_first_valid_between_epochs_never_replays_startup_epoch():
    h = _require_v2_engine()
    asset, data = _startup_asset(h, depth_offset_ns=DEPTH_NS)
    bt = h.HashMapMarketDepthBacktest(
        [asset]
    )
    assert len(data) == 4

    try:
        kernel = _april_kernel(
            h,
            bt,
            q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel,
        )
        first_target = _initialize_to_first_trade(kernel)
        next_target = kernel._consume_due_policy_target(
            next_policy_ns=first_target
        )
        assert int(
            bt.wait_next_feed(
                True,
                next_target - int(bt.current_timestamp),
            )
        ) == 2
        assert int(bt.current_timestamp) == SYNTH_START_NS + DEPTH_NS
        kernel.market_wakeups += 1
        kernel._capture_last_trades()
        assert kernel.initial_book_ready is True
        assert kernel.initial_book_ready_local_ns == SYNTH_START_NS + DEPTH_NS

        assert int(
            bt.wait_next_feed(
                True,
                next_target - int(bt.current_timestamp),
            )
        ) == 0
        following = kernel._consume_due_policy_target(
            next_policy_ns=next_target
        )
        assert following == SYNTH_START_NS + 3_000_000_000
        assert kernel.q4_policy_epoch_timestamps == [next_target]
        assert kernel.first_policy_epoch_executed == next_target
        assert kernel.startup_policy_epoch_timestamps_skipped == [first_target]
        assert first_target not in kernel.q4_policy_epoch_timestamps
        assert all(
            timestamp >= int(bt.current_timestamp) - d1.BASE_MAKER_STEP_NS
            for timestamp in kernel.q4_policy_epoch_timestamps
        )
        assert kernel.startup_readiness_diagnostics()[
            "no_retroactive_startup_policy"
        ] is True
    finally:
        assert int(bt.close()) == 0


def test_d_actual_v2_exact_epoch_depth_precedes_one_policy_decision():
    h = _require_v2_engine()
    asset, data = _startup_asset(h, depth_offset_ns=2_000_000_000)
    bt = h.HashMapMarketDepthBacktest(
        [asset]
    )
    assert len(data) == 4

    try:
        kernel = _april_kernel(
            h,
            bt,
            q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel,
        )
        first_target = _initialize_to_first_trade(kernel)
        second_target = kernel._consume_due_policy_target(
            next_policy_ns=first_target
        )
        assert second_target == SYNTH_START_NS + 2_000_000_000
        assert int(
            bt.wait_next_feed(
                True,
                second_target - int(bt.current_timestamp),
            )
        ) == 2
        assert int(bt.current_timestamp) == second_target
        kernel.market_wakeups += 1
        kernel._capture_last_trades()
        assert kernel.initial_book_ready_local_ns == second_target
        third_target = kernel._consume_due_policy_target(
            next_policy_ns=second_target
        )
        assert third_target == SYNTH_START_NS + 3_000_000_000
        assert kernel.q4_policy_epoch_timestamps == [second_target]
        assert kernel.first_policy_epoch_executed == second_target
        assert kernel.policy_epochs == 1
        assert kernel.startup_policy_epoch_timestamps_skipped == [first_target]
    finally:
        assert int(bt.close()) == 0


class MutableDepth:
    def __init__(self, bid_tick: int, ask_tick: int) -> None:
        self.best_bid_tick = bid_tick
        self.best_ask_tick = ask_tick

    def bid_qty_at_tick(self, tick):
        return 1.0 if tick == self.best_bid_tick else 0.0

    def ask_qty_at_tick(self, tick):
        return 1.0 if tick == self.best_ask_tick else 0.0


def _minimal_kernel(depth: MutableDepth):
    kernel = object.__new__(
        q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel
    )
    kernel.bt = SimpleNamespace(
        current_timestamp=2_000_000_000,
        depth=lambda asset_no: depth,
        position=lambda asset_no: 0.0,
    )
    kernel.flow = SimpleNamespace(
        quantities=lambda **kwargs: (0.0, 0.0)
    )
    kernel.inventory_clock = d1.InventoryClock.flat()
    kernel._ensure_initial_book_readiness_state()
    return kernel


def test_e_partial_same_timestamp_snapshot_uses_actual_two_sided_depth():
    depth = MutableDepth(1000, 2**63 - 1)
    kernel = _minimal_kernel(depth)
    assert kernel._observe_initial_book_readiness(
        local_timestamp_ns=2_000_000_000
    ) is False
    assert kernel.initial_book_ready_local_ns is None

    depth.best_ask_tick = 1001
    assert kernel._observe_initial_book_readiness(
        local_timestamp_ns=2_000_000_000
    ) is True
    assert kernel.initial_book_ready_local_ns == 2_000_000_000
    assert list(kernel.initial_book_readiness_observations) == [
        (2_000_000_000, 1000, 2**63 - 1, False),
        (2_000_000_000, 1000, 1001, True),
    ]


def _jan_asset(h):
    import numpy as np

    data = np.zeros(2, dtype=h.event_dtype)
    _event_row(
        h,
        data,
        0,
        event=h.TRADE_EVENT,
        side=h.BUY_EVENT,
        timestamp=DAY_JAN_START_NS + TRADE_NS,
        price=100.0,
        qty=0.001,
    )
    _event_row(
        h,
        data,
        1,
        event=h.DEPTH_EVENT,
        side=h.SELL_EVENT,
        timestamp=DAY_JAN_START_NS + 20_000_000_000,
        price=100.1,
        qty=8.0,
    )
    return m4.build_asset(
        data,
        entry_latency_ns=250_000_000,
        response_latency_ns=250_000_000,
    ), data


def _jan_first_policy(h, bt, cls):
    kernel = cls(
        bt=bt,
        h=h,
        policy_id="M01",
        day="2026-01-01",
        scenario=PRIMARY,
        terminal_source_local_ns=DAY_JAN_START_NS + 20_000_000_000,
        direct_index=None,
    )
    assert int(bt.wait_next_feed(True, 10_000_000_000)) == 2
    kernel.market_wakeups += 1
    kernel._capture_last_trades()
    target = d1.next_base_policy_epoch_after(int(bt.current_timestamp))
    assert int(bt.wait_next_feed(True, target - int(bt.current_timestamp))) == 0
    following = kernel._consume_due_policy_target(next_policy_ns=target)
    return kernel, target, following


def test_f_actual_v2_january_first_policy_and_order_intents_match_q4():
    h = _require_v2_engine()
    q4_asset, q4_data = _jan_asset(h)
    q6_asset, q6_data = _jan_asset(h)
    q4_bt = h.HashMapMarketDepthBacktest([q4_asset])
    q6_bt = h.HashMapMarketDepthBacktest([q6_asset])
    assert len(q4_data) == len(q6_data) == 2

    try:
        q4_kernel, q4_target, q4_following = _jan_first_policy(
            h,
            q4_bt,
            q4_driver.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel,
        )
        q6_kernel, q6_target, q6_following = _jan_first_policy(
            h,
            q6_bt,
            q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel,
        )
        assert q4_target == q6_target
        assert q4_following == q6_following
        assert q4_kernel.q4_policy_epoch_timestamps == [q4_target]
        assert q6_kernel.q4_policy_epoch_timestamps == [q6_target]
        assert q6_kernel.initial_book_ready_local_ns == DAY_JAN_START_NS + TRADE_NS
        assert q6_kernel.startup_policy_epochs_skipped == 0
        assert q6_kernel.first_policy_epoch_executed == q6_target
        assert q4_kernel.decision_trace == q6_kernel.decision_trace
        assert q4_kernel.submit_requests == q6_kernel.submit_requests == 2
        assert q4_kernel.cancel_requests == q6_kernel.cancel_requests == 0
        assert _order_tuple(q4_bt.orders(0)) == _order_tuple(q6_bt.orders(0))
        q4_state = q4_bt.state_values(0)
        q6_state = q6_bt.state_values(0)
        assert (
            q4_state.position,
            q4_state.balance,
            q4_state.fee,
            q4_state.trading_volume,
            q4_state.trading_value,
        ) == (
            q6_state.position,
            q6_state.balance,
            q6_state.fee,
            q6_state.trading_volume,
            q6_state.trading_value,
        )
    finally:
        assert int(q4_bt.close()) == 0
        assert int(q6_bt.close()) == 0


def test_g_later_invalid_book_keeps_original_fail_closed_semantics():
    depth = MutableDepth(1000, 1001)
    kernel = _minimal_kernel(depth)
    kernel.policy_id = "M01"
    kernel.day = "2026-01-01"
    kernel.scenario = PRIMARY
    assert kernel._observe_initial_book_readiness(
        local_timestamp_ns=1_000_000_000
    ) is True

    for bid, ask in ((0, 1001), (1000, 1000), (1001, 1000)):
        depth.best_bid_tick = bid
        depth.best_ask_tick = ask
        with pytest.raises(d2.EventLoopKernelError, match="^invalid_local_book$"):
            kernel._dynamic_market_state(local_timestamp_ns=2_000_000_000)
        assert kernel.initial_book_ready is True
        assert kernel.initial_book_ready_local_ns == 1_000_000_000


def test_h_q6_changes_only_startup_scheduler_hooks():
    cls = q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel
    parent = (
        q4_driver.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
    )
    assert cls.run_full_day is parent.run_full_day
    assert cls._reconcile_policy_target is parent._reconcile_policy_target
    assert cls._process_response_batch is parent._process_response_batch
    assert cls._maintain_side is parent._maintain_side
    assert cls._submit_side is parent._submit_side
    assert cls._execute_unique_flatten is parent._execute_unique_flatten
    assert cls._maybe_execute_forced_flatten is parent._maybe_execute_forced_flatten
    assert cls._dynamic_market_state is parent._dynamic_market_state
    assert issubclass(cls, parent)
    assert not issubclass(cls, q5_driver.InvalidLocalBookForensicContinuousHistoricalPolicyKernel)


def test_q5_result_freeze_and_root_cause_timing_are_exact():
    assert hashlib.sha256(q6.Q5_RESULT_PATH.read_bytes()).hexdigest() == (
        "4c33c2704278b5504d3ef09781eb9d21736b00370818b804fc688500d31bd85e"
    )
    payload = json.loads(q6.Q5_RESULT_PATH.read_text(encoding="utf-8"))
    snapshot = payload["invalid_local_book"]
    assert payload["status"] == "INVALID_LOCAL_BOOK_FORENSIC_CAPTURED"
    assert payload["forensic_classification"] == "BID_NONPOSITIVE"
    assert snapshot["bt_current_timestamp"] == DAY_APR_START_NS + 1_000_000_000
    assert snapshot["last_market_wakeup_timestamp"] == (
        DAY_APR_START_NS + TRADE_NS
    )
    assert snapshot["last_valid_local_book_top"] is None
    assert snapshot["best_bid_tick"] == -(2**63)
    assert snapshot["best_ask_tick"] == 2**63 - 1
    assert snapshot["adapter_decision_count_before_evaluation"] == 0
    assert snapshot["adapter_decision_count_at_failure"] == 0
    assert snapshot["direct_action_lookup_count_before_evaluation"] == 0
    assert snapshot["direct_action_lookup_count_at_failure"] == 0
    assert all(
        observation["classification"] == "BID_NONPOSITIVE"
        for observation in snapshot["recent_local_book_observations"]
    )
    market_observations = tuple(
        observation
        for observation in snapshot["recent_local_book_observations"]
        if observation["event_class"] == "LOCAL_MARKET"
    )
    assert market_observations
    assert all(
        int(observation["local_timestamp_ns"])
        < snapshot["bt_current_timestamp"]
        for observation in market_observations
    )
    assert snapshot["recent_local_book_observations"][-1][
        "local_timestamp_ns"
    ] == snapshot["bt_current_timestamp"]
    first_depth = next(
        row
        for row in payload["source_window"]["rows"]
        if any(
            event in row["decoded"]["event_types"]
            for event in ("DEPTH_CLEAR_EVENT", "DEPTH_SNAPSHOT_EVENT")
        )
    )
    assert first_depth["local_ts"] == DAY_APR_START_NS + DEPTH_NS
    assert first_depth["local_ts"] > snapshot["bt_current_timestamp"]
    assert payload["replay_continued_after_failure"] is False


def test_q6_contract_authorization_matrix_and_non_economic_surface(monkeypatch):
    assert q6.EXPERIMENT_ID == "DEV045-D6R20-Q6"
    assert q6.DESIGN_VERSION == (
        "real-hftbacktest-v2-initial-local-book-readiness-qualification-v1"
    )
    assert q6.AUTHORIZATION_ENV == "DEV045_D6R20_Q6_AUTHORIZE"
    assert q6.AUTHORIZATION_TOKEN == (
        "YES_REAL_HFTBACKTEST_V2_EXECUTION_QUALIFICATION_D6R20_Q6"
    )
    assert len(q6.QUALIFICATION_PLAN) == 20
    assert len(q6._day_plan("2026-01-01")) == 16
    assert len(q6._day_plan("2026-04-01")) == 4
    assert q6.QUALIFICATION_PLAN == q6.q4.QUALIFICATION_PLAN
    assert q6.HISTORICAL_KERNEL is (
        q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel
    )
    assert q6.QUALIFICATION_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert q6.REAL_HISTORICAL_QUALIFICATION_EXECUTED is False
    assert q6.Q5_RERUN_AUTHORIZED is False
    assert q6.CANONICAL_RUNNER_IMPLEMENTED is False
    assert q6.CANONICAL_ECONOMIC_ATTEMPT is False
    assert q6.CANONICAL_ATTEMPT_CONSUMED is False
    assert q6.ECONOMIC_ARENA_EXECUTED is False
    assert q6.STRATEGY_RANKING_PERFORMED is False
    assert q6.AUTOMATIC_RETRY is False
    assert q6.LIVE_TRADING_AUTHORIZED is False

    monkeypatch.delenv(q6.AUTHORIZATION_ENV, raising=False)
    with pytest.raises(q6.QualificationError, match="execution_gate_closed"):
        q6._require_authorization(
            authorization_token=q6.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )
    with pytest.raises(q6.QualificationError, match="authorization_environment"):
        q6._require_authorization(
            authorization_token=q6.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    source = Path(q6.__file__).read_text(encoding="utf-8")
    assert "run_" + "economic_arena" not in source
    assert "." + "cycles" not in source


def test_q6_runtime_guard_and_result_surface(monkeypatch, tmp_path):
    package = tmp_path / "hftbacktest"
    package.mkdir()
    init = package / "__init__.py"
    init.write_text("", encoding="utf-8")
    (package / "_hftbacktest.synthetic.so").write_bytes(b"synthetic")
    module = SimpleNamespace(__version__="2.4.4", __file__=str(init))

    monkeypatch.setattr(
        q6.q4,
        "_stream_sha256",
        lambda path: q6.OLD_HFTBACKTEST_BINARY_SHA256,
    )
    with pytest.raises(q6.QualificationError, match="hftbacktest_binary_sha256"):
        q6.validate_runtime_identity(module)

    monkeypatch.setattr(
        q6.q4,
        "_stream_sha256",
        lambda path: q6.HFTBACKTEST_BINARY_SHA256,
    )
    assert q6.validate_runtime_identity(module).verified is True

    root = tmp_path / "q6-result"
    monkeypatch.setattr(q6, "RESULT_ROOT", root)
    monkeypatch.setattr(q6, "SUCCESS_RESULT_PATH", root / "success.json")
    monkeypatch.setattr(q6, "FAILURE_RESULT_PATH", root / "failure.json")
    q6._write_json_new(q6.SUCCESS_RESULT_PATH, {"status": "first"})
    with pytest.raises(q6.QualificationError, match="result_exists"):
        q6._write_json_new(q6.SUCCESS_RESULT_PATH, {"status": "second"})


def test_q6_frozen_predecessor_hashes_and_contract_are_exact():
    q6.validate_qualification_contract()
    checks = (
        (q6.Q5_DRIVER_PATH, q6.Q5_DRIVER_BLOB),
        (q6.Q5_FORENSIC_PATH, q6.Q5_FORENSIC_BLOB),
        (q6.Q4_DRIVER_PATH, q6.Q4_DRIVER_BLOB),
        (q6.Q4_HARNESS_PATH, q6.Q4_HARNESS_BLOB),
        (q6.Q3_HARNESS_PATH, q6.Q3_HARNESS_BLOB),
        (q6.D6R20_DRIVER_PATH, q6.D6R20_DRIVER_BLOB),
        (q6.M4_M6_BINDING_PATH, q6.M4_M6_BINDING_BLOB),
    )
    for path, expected in checks:
        assert q6._git_blob(path) == expected
    assert q6._stream_sha256(q6.V2_PATCH_PATH) == q6.V2_PATCH_SHA256


def test_q6_readiness_predicate_is_exact():
    assert q6_driver.local_book_is_ready(
        best_bid_tick=1000,
        best_ask_tick=1001,
    ) is True
    assert q6_driver.local_book_is_ready(
        best_bid_tick=0,
        best_ask_tick=1001,
    ) is False
    assert q6_driver.local_book_is_ready(
        best_bid_tick=1000,
        best_ask_tick=1000,
    ) is False
    assert q6_driver.local_book_is_ready(
        best_bid_tick=1001,
        best_ask_tick=1000,
    ) is False


def test_q6_readiness_metrics_validation_adds_only_operational_fields(monkeypatch):
    frozen = q6.q4.ReplayExecutionDiagnostics(
        day="2026-04-01",
        policy_id="M06",
        scenario=PRIMARY,
        market_wakeups=3,
        response_wakeups=0,
        policy_epochs=1,
        submit_requests=2,
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
    monkeypatch.setattr(
        q6.q4,
        "_validate_completed_replay",
        lambda **kwargs: frozen,
    )
    kernel = SimpleNamespace(
        q4_policy_epoch_timestamps=[DAY_APR_START_NS + 2_000_000_000],
        startup_readiness_diagnostics=lambda: {
            "initial_book_ready_timestamp": DAY_APR_START_NS + DEPTH_NS,
            "startup_policy_epochs_skipped": 1,
            "startup_policy_epoch_timestamps_skipped": (
                DAY_APR_START_NS + 1_000_000_000,
            ),
            "first_policy_epoch_executed": DAY_APR_START_NS + 2_000_000_000,
            "no_retroactive_startup_policy": True,
        },
    )
    result = q6._validate_completed_replay(
        bt=object(),
        kernel=kernel,
        replay=object(),
    )
    assert result.initial_book_ready_timestamp == DAY_APR_START_NS + DEPTH_NS
    assert result.startup_policy_epochs_skipped == 1
    assert result.first_policy_epoch_executed == (
        DAY_APR_START_NS + 2_000_000_000
    )
    assert result.no_retroactive_startup_policy is True
    serialized = vars(result)
    prohibited = (
        "pnl",
        "bps",
        "profit",
        "drawdown",
        "return",
        "win_rate",
    )
    assert not any(
        token in key.lower()
        for key in serialized
        for token in prohibited
    )


def _q6_diagnostics(day: str, policy_id: str, scenario: str):
    return q6.ReplayExecutionDiagnostics(
        day=day,
        policy_id=policy_id,
        scenario=scenario,
        market_wakeups=3,
        response_wakeups=0,
        policy_epochs=1,
        submit_requests=2,
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
        initial_book_ready_timestamp=1,
        startup_policy_epochs_skipped=0,
        startup_policy_epoch_timestamps_skipped=(),
        first_policy_epoch_executed=2,
        no_retroactive_startup_policy=True,
    )


def _prepare_q6_top_level(monkeypatch, tmp_path):
    root = tmp_path / "q6-top"
    monkeypatch.setattr(q6, "RESULT_ROOT", root)
    monkeypatch.setattr(q6, "SUCCESS_RESULT_PATH", root / "success.json")
    monkeypatch.setattr(q6, "FAILURE_RESULT_PATH", root / "failure.json")
    monkeypatch.setenv(q6.AUTHORIZATION_ENV, q6.AUTHORIZATION_TOKEN)
    repository = q6.RepositoryIdentity(
        branch=q6.EXPECTED_BRANCH,
        head="a" * 40,
        remote_ref=q6.EXPECTED_REMOTE_REF,
        remote_head="a" * 40,
        tracked_worktree_clean=True,
        permitted_untracked_paths=(),
        d6r20_driver_blob=q6.D6R20_DRIVER_BLOB,
        m4_m6_binding_blob=q6.M4_M6_BINDING_BLOB,
        v2_patch_sha256=q6.V2_PATCH_SHA256,
        frozen_predecessors_verified=True,
        q5_result_sha256=q6.Q5_RESULT_SHA256,
        d6r20_canonical_runner_absent=True,
        d6r21_canonical_runner_absent=True,
        result_surface_virgin=True,
    )
    monkeypatch.setattr(q6, "validate_repository_preflight", lambda: repository)
    monkeypatch.setattr(q6, "validate_qualification_contract", lambda: None)
    monkeypatch.setattr(q6, "_hftbacktest_module", lambda: object())
    monkeypatch.setattr(
        q6,
        "validate_runtime_identity",
        lambda h: q6.RuntimeIdentity(
            q6.HFTBACKTEST_VERSION,
            q6.HFTBACKTEST_BINARY_SHA256,
            True,
        ),
    )
    return root


def test_q6_success_serializes_readiness_metrics_only_after_exact_20(
    monkeypatch,
    tmp_path,
):
    _prepare_q6_top_level(monkeypatch, tmp_path)

    def run_day(*, day, on_replay_start, on_replay_complete, **kwargs):
        results = []
        for item_day, policy_id, scenario in q6._day_plan(day):
            on_replay_start(item_day, policy_id, scenario)
            result = _q6_diagnostics(item_day, policy_id, scenario)
            on_replay_complete(result)
            results.append(result)
        return tuple(results)

    monkeypatch.setattr(q6, "run_qualification_day_from_disk", run_day)
    payload = q6.run_real_engine_qualification(
        authorization_token=q6.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )
    assert payload["status"] == "REAL_ENGINE_QUALIFICATION_PASS"
    assert payload["replay_count"] == 20
    assert len(payload["replays"]) == 20
    assert all(
        item["no_retroactive_startup_policy"] is True
        for item in payload["replays"]
    )
    assert payload["canonical_economic_attempt"] is False
    assert payload["canonical_attempt_consumed"] is False
    assert payload["economic_arena_called"] is False
    assert payload["strategy_ranking_performed"] is False
    assert payload["economic_conclusion"] == "NOT_EVALUATED"
    assert payload["automatic_retry"] is False


def test_q6_future_failure_artifact_is_noncanonical_and_nonretrying(
    monkeypatch,
    tmp_path,
):
    _prepare_q6_top_level(monkeypatch, tmp_path)

    def fail_day(*, day, on_replay_start, **kwargs):
        first = q6._day_plan(day)[0]
        on_replay_start(*first)
        raise d2.EventLoopKernelError("invalid_local_book")

    monkeypatch.setattr(q6, "run_qualification_day_from_disk", fail_day)
    with pytest.raises(d2.EventLoopKernelError, match="invalid_local_book"):
        q6.run_real_engine_qualification(
            authorization_token=q6.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )
    payload = json.loads(q6.FAILURE_RESULT_PATH.read_text(encoding="utf-8"))
    assert payload["status"] == "REAL_ENGINE_QUALIFICATION_FAILED"
    assert payload["completed_qualification_replay_count"] == 0
    assert payload["canonical_attempt_consumed"] is False
    assert payload["economic_arena_called"] is False
    assert payload["strategy_ranking_performed"] is False
    assert payload["economic_conclusion"] == "UNAVAILABLE"
    assert payload["automatic_retry"] is False


def test_q6_repository_preflight_fails_before_runtime_on_wrong_branch(monkeypatch):
    monkeypatch.setattr(q6, "_current_branch", lambda: "wrong")
    with pytest.raises(q6.QualificationError, match="repository_branch"):
        q6.validate_repository_preflight()

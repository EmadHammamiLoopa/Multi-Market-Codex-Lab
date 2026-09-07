from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import math
import os
from pathlib import Path

import pytest

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r19_response_batch_replacement_driver as d6r19
from multimarket import dev045_d6r20_q4_scheduler_reconciled_driver as q4
from multimarket import dev045_d6r20_residual_flatten_driver as d6r20
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket.dev044_t0_strategy_contract import LONG, SHORT


V2_ENGINE_TEST_ENABLED = os.environ.get("DEV045_Q4_V2_ENGINE_TEST") == "1"
DAY_START_NS = int(
    datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
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
    expected = os.environ.get("DEV045_Q4_TEST_ENGINE_SHA256")

    if expected is not None:
        assert observed == expected

    return h


def _event_row(h, array, index, *, timestamp):
    array[index]["ev"] = int(
        h.DEPTH_EVENT | h.EXCH_EVENT | h.LOCAL_EVENT | h.SELL_EVENT
    )
    array[index]["exch_ts"] = timestamp
    array[index]["local_ts"] = timestamp
    array[index]["px"] = 100.1
    array[index]["qty"] = 8.0


def _build_latency_backtest(h, *, latency_ns: int, first_event_ns: int):
    import numpy as np

    data = np.zeros(2, dtype=h.event_dtype)
    _event_row(h, data, 0, timestamp=first_event_ns)
    _event_row(h, data, 1, timestamp=DAY_START_NS + 20_000_000_000)
    asset = (
        h.BacktestAsset()
        .data([data])
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
    seed = m4.submit_forced_flatten(
        bt,
        h,
        direction=SHORT,
        qty=0.001,
        order_id=9001,
        wait=True,
    )
    assert int(seed.status) == int(h.FILLED)
    assert math.isclose(bt.position(0), -0.001, abs_tol=1e-12)
    return bt


def _state_tuple(bt) -> tuple:
    state = bt.state_values(0)
    return (
        float(state.position),
        float(state.balance),
        float(state.fee),
        int(state.num_trades),
        float(state.trading_volume),
        float(state.trading_value),
    )


def _execute_actual_blocking_flatten(
    h,
    *,
    latency_ns: int,
    first_event_ns: int,
):
    bt = _build_latency_backtest(
        h,
        latency_ns=latency_ns,
        first_event_ns=first_event_ns,
    )
    before_ns = int(bt.current_timestamp)
    next_policy_ns = d1.next_base_policy_epoch_after(before_ns)
    before = _state_tuple(bt)
    kernel = object.__new__(
        q4.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
    )
    kernel.bt = bt
    kernel.h = h
    kernel.next_flatten_order_id = 9002
    kernel.flatten_order_ids = []
    kernel.bound_fills = []
    kernel.policy_id = "M01"
    kernel.day = "2026-01-01"
    kernel.inventory_clock = d1.InventoryClock(
        position=-0.001,
        nonzero_since_local_ns=before_ns,
    )
    kernel.flatten_response_local_ns = None

    kernel._execute_unique_flatten(
        direction=LONG,
        qty=0.001,
    )
    after_ns = int(bt.current_timestamp)
    after = _state_tuple(bt)

    assert len(kernel.bound_fills) == 1
    event = kernel.bound_fills[0]
    assert event.kind == binding.FILL
    assert event.fill is not None
    assert event.fill.liquidity == binding.TAKER
    assert event.fill.side == "BUY"
    assert math.isclose(event.fill.qty, 0.001, abs_tol=1e-12)
    assert math.isclose(before[0], -0.001, abs_tol=1e-12)
    assert abs(after[0]) <= 1e-12
    assert math.isclose(after[0] - before[0], 0.001, abs_tol=1e-12)
    assert math.isclose(after[4] - before[4], 0.001, abs_tol=1e-12)
    assert math.isclose(after[5] - before[5], 0.1001, abs_tol=1e-12)
    assert after[3] - before[3] == 1
    assert kernel.flatten_order_ids == [9002]
    assert kernel.inventory_clock == d1.InventoryClock.flat()

    return bt, before_ns, next_policy_ns, after_ns, before, after, event


def _frozen_stale_target_guard(*, current_ns: int, next_policy_ns: int):
    if int(current_ns) > int(next_policy_ns):
        raise base.RealHistoricalDriverError("policy_epoch_skipped")


def test_a_actual_v2_stress_blocking_wait_reproduces_stale_policy_target():
    h = _require_v2_engine()
    trace = _execute_actual_blocking_flatten(
        h,
        latency_ns=500_000_000,
        first_event_ns=DAY_START_NS + 200_000_000,
    )
    bt, before_ns, target_ns, after_ns, *_ = trace

    try:
        assert before_ns == DAY_START_NS + 1_200_000_000
        assert target_ns == DAY_START_NS + 2_000_000_000
        assert after_ns == DAY_START_NS + 2_200_000_000
        assert after_ns - before_ns == 1_000_000_000

        with pytest.raises(
            base.RealHistoricalDriverError,
            match="policy_epoch_skipped",
        ):
            _frozen_stale_target_guard(
                current_ns=after_ns,
                next_policy_ns=target_ns,
            )

        assert q4.reconcile_policy_target_after_blocking_wait(
            current_local_ns=after_ns,
            next_policy_ns=target_ns,
        ) == DAY_START_NS + 3_000_000_000
    finally:
        assert int(bt.close()) == 0


def test_b_actual_v2_primary_blocking_wait_preserves_future_target():
    h = _require_v2_engine()
    trace = _execute_actual_blocking_flatten(
        h,
        latency_ns=250_000_000,
        first_event_ns=DAY_START_NS + 700_000_000,
    )
    bt, before_ns, target_ns, after_ns, *_ = trace

    try:
        assert before_ns == DAY_START_NS + 1_200_000_000
        assert target_ns == DAY_START_NS + 2_000_000_000
        assert after_ns == DAY_START_NS + 1_700_000_000
        assert after_ns - before_ns == 500_000_000
        _frozen_stale_target_guard(
            current_ns=after_ns,
            next_policy_ns=target_ns,
        )
        assert q4.reconcile_policy_target_after_blocking_wait(
            current_local_ns=after_ns,
            next_policy_ns=target_ns,
        ) == target_ns
    finally:
        assert int(bt.close()) == 0


def test_c_actual_v2_exact_equality_keeps_response_before_one_policy_epoch():
    h = _require_v2_engine()
    trace = _execute_actual_blocking_flatten(
        h,
        latency_ns=500_000_000,
        first_event_ns=DAY_START_NS + 1_000_000_000,
    )
    bt, before_ns, target_ns, after_ns, _before, _after, event = trace

    try:
        assert before_ns == DAY_START_NS + 2_000_000_000
        assert target_ns == DAY_START_NS + 3_000_000_000
        assert after_ns == target_ns
        reconciled = q4.reconcile_policy_target_after_blocking_wait(
            current_local_ns=after_ns,
            next_policy_ns=target_ns,
        )
        assert reconciled == after_ns

        assert int(event.timestamp_ns) < after_ns
        event_order = [("local_response_accounted", after_ns)]

        if after_ns == reconciled:
            event_order.append(("policy", reconciled))

        following = q4.reconcile_policy_target_after_blocking_wait(
            current_local_ns=after_ns,
            next_policy_ns=reconciled + d1.BASE_MAKER_STEP_NS,
        )
        assert event_order == [
            ("local_response_accounted", after_ns),
            ("policy", after_ns),
        ]
        assert following == DAY_START_NS + 4_000_000_000
    finally:
        assert int(bt.close()) == 0


def test_d_overshoot_uses_strictly_future_epoch_without_catchup():
    target = 2_000_000_000
    current = 2_200_000_000
    reconciled = q4.reconcile_policy_target_after_blocking_wait(
        current_local_ns=current,
        next_policy_ns=target,
    )
    evaluated = [reconciled]
    assert reconciled == 3_000_000_000
    assert evaluated == [3_000_000_000]
    assert target not in evaluated
    assert all(timestamp >= current for timestamp in evaluated)


def test_e_multi_epoch_overshoot_skips_every_missed_epoch():
    target = 2_000_000_000
    current = 4_600_000_000
    reconciled = q4.reconcile_policy_target_after_blocking_wait(
        current_local_ns=current,
        next_policy_ns=target,
    )
    missed = (2_000_000_000, 3_000_000_000, 4_000_000_000)
    evaluated = (reconciled,)
    assert reconciled == 5_000_000_000
    assert not set(missed).intersection(evaluated)
    assert evaluated[0] > current


def test_current_exact_epoch_after_overshoot_is_retained_not_replayed():
    assert q4.reconcile_policy_target_after_blocking_wait(
        current_local_ns=4_000_000_000,
        next_policy_ns=2_000_000_000,
    ) == 4_000_000_000


def test_no_execution_or_fill_semantics_are_overridden():
    cls = (
        q4.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
    )
    assert cls._execute_unique_flatten is base.ContinuousHistoricalPolicyKernel._execute_unique_flatten
    assert cls._maybe_execute_forced_flatten is (
        d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel._maybe_execute_forced_flatten
    )
    assert cls._process_response_batch is (
        d6r19.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel._process_response_batch
    )


def test_policy_target_reconciliation_fails_closed_on_invalid_target():
    with pytest.raises(
        base.RealHistoricalDriverError,
        match="q4_policy_target_not_base_epoch",
    ):
        q4.reconcile_policy_target_after_blocking_wait(
            current_local_ns=1_500_000_000,
            next_policy_ns=2_100_000_000,
        )

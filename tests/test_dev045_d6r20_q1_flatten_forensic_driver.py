from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r20_q1_flatten_forensic_driver as f
from multimarket import dev045_d6r20_residual_flatten_driver as d6r20
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m6_event_loop_kernel as d2
from multimarket.dev044_t0_strategy_contract import LONG, SHORT


def _hftbacktest_available() -> bool:
    return importlib.util.find_spec("hftbacktest") is not None


def _event_row(h, array, index, *, base, side, timestamp, price, qty):
    array[index]["ev"] = int(base | h.EXCH_EVENT | h.LOCAL_EVENT | side)
    array[index]["exch_ts"] = int(timestamp)
    array[index]["local_ts"] = int(timestamp)
    array[index]["px"] = float(price)
    array[index]["qty"] = float(qty)


def _build_real_partial_fill_backtest(*, bid_qty: float):
    import hftbacktest as h
    import numpy as np

    initial = np.zeros(2, dtype=h.event_dtype)
    _event_row(
        h,
        initial,
        0,
        base=h.DEPTH_SNAPSHOT_EVENT,
        side=h.BUY_EVENT,
        timestamp=100_000_000,
        price=100.0,
        qty=bid_qty,
    )
    _event_row(
        h,
        initial,
        1,
        base=h.DEPTH_SNAPSHOT_EVENT,
        side=h.SELL_EVENT,
        timestamp=100_000_000,
        price=100.1,
        qty=0.002,
    )

    data = np.zeros(2, dtype=h.event_dtype)
    _event_row(
        h,
        data,
        0,
        base=h.DEPTH_EVENT,
        side=h.SELL_EVENT,
        timestamp=1_000_000_000,
        price=100.2,
        qty=0.001,
    )
    _event_row(
        h,
        data,
        1,
        base=h.DEPTH_EVENT,
        side=h.SELL_EVENT,
        timestamp=10_000_000_000,
        price=100.2,
        qty=0.001,
    )

    asset = (
        h.BacktestAsset()
        .data([data])
        .initial_snapshot(initial)
        .linear_asset(1.0)
        .constant_order_latency(0, 0)
        .risk_adverse_queue_model()
        .partial_fill_exchange()
        .trading_value_fee_model(0.0, 0.0)
        .tick_size(p.TICK_SIZE)
        .lot_size(p.LOT_SIZE)
    )
    bt = h.HashMapMarketDepthBacktest([asset])
    assert int(bt.wait_next_feed(False, 2_000_000_000)) == 2
    seed = m4.submit_forced_flatten(
        bt,
        h,
        direction=LONG,
        qty=0.002,
        order_id=4801,
        wait=True,
    )
    assert seed.status == d2.HFT_FILLED
    assert math.isclose(bt.position(0), 0.002, abs_tol=1e-12)
    return h, bt


def _attempt(**overrides) -> f.FlattenAttemptDiagnostics:
    values = {
        "local_timestamp": 1,
        "current_position": 0.002,
        "requested_direction": "SHORT",
        "requested_direction_code": SHORT,
        "requested_qty": 0.002,
        "requested_lots": 2,
        "best_bid_tick": 1000,
        "best_ask_tick": 1001,
        "best_bid": 100.0,
        "best_ask": 100.1,
        "lot_size": 0.001,
        "market_sweep_lower_tick": 900,
        "market_sweep_upper_tick": 1000,
        "market_sweep_tick_count": 101,
        "market_sweep_visible_qty": 0.001,
        "market_sweep_visible_lots": 1,
        "market_sweep_visible_sufficient": False,
        "order_id": 4901,
        "status": d2.HFT_EXPIRED,
        "side": -1,
        "price_tick": 1000,
        "exec_price_tick": 1000,
        "exec_qty": 0.001,
        "leaves_qty": 0.001,
        "exch_timestamp": 2,
        "local_timestamp_after": 2,
        "cumulative_executed_qty": 0.001,
        "post_position": 0.002,
        "position_delta": 0.0,
        "expected_post_position": 0.001,
        "position_accounting_consistent": False,
        "order_status_is_filled": False,
        "order_status_is_expired": True,
        "residual_abs_position": 0.002,
        "classification": f.MARKET_DEPTH_SWEEP_INSUFFICIENT,
    }
    values.update(overrides)
    return f.FlattenAttemptDiagnostics(**values)


def test_forensic_closed_exact_scope_and_no_economics(monkeypatch):
    assert f.EXPERIMENT_ID == "DEV045-D6R20-Q1-FLATTEN-FORENSIC"
    assert f.FORENSIC_SCOPE == (
        ("2026-01-01", "M01", "Q0_PRIMARY_250_250"),
    )
    assert f.AUTHORIZATION_ENV == "DEV045_D6R20_Q1_FORENSIC_AUTHORIZE"
    assert f.AUTHORIZATION_TOKEN == (
        "YES_D6R20_Q1_JAN_M01_PRIMARY_FLATTEN_FORENSIC"
    )
    assert f.FORENSIC_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert f.REAL_FORENSIC_REPLAY_EXECUTED is False
    assert f.CANONICAL_RUNNER_IMPLEMENTED is False
    assert f.CANONICAL_ECONOMIC_ATTEMPT is False
    assert f.CANONICAL_ATTEMPT_CONSUMED is False
    assert f.ECONOMIC_ARENA_CALLED is False
    assert f.STRATEGY_RANKING_PERFORMED is False
    assert f.AUTOMATIC_RETRY is False
    assert f.LIVE_TRADING_AUTHORIZED is False

    monkeypatch.delenv(f.AUTHORIZATION_ENV, raising=False)
    with pytest.raises(f.FlattenForensicError, match="execution_gate_closed"):
        f._require_authorization(
            authorization_token=f.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )
    with pytest.raises(f.FlattenForensicError, match="authorization_environment"):
        f._require_authorization(
            authorization_token=f.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )


def test_d6r20_kernel_is_subclassed_without_changing_frozen_driver():
    assert issubclass(
        f.FlattenForensicContinuousHistoricalPolicyKernel,
        d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel,
    )
    assert f.HISTORICAL_KERNEL is (
        f.FlattenForensicContinuousHistoricalPolicyKernel
    )
    assert f._git_blob(Path(d6r20.__file__)) == (
        "1cae4584788aab29b409bf985168803759d42b1f"
    )
    source = Path(f.__file__).read_text(encoding="utf-8")
    assert source.count("m4.submit_forced_flatten(") == 1
    assert "order_type" not in source
    assert "rescue" + "_flatten" not in source
    assert "run_" + "economic_arena" not in source
    assert "replay." + "cycles" not in source


def test_market_sweep_tick_ranges_and_visible_quantity_are_exact():
    assert f.market_sweep_ticks(
        direction=SHORT,
        best_bid_tick=1000,
        best_ask_tick=1001,
    ) == tuple(range(1000, 899, -1))
    assert f.market_sweep_ticks(
        direction=LONG,
        best_bid_tick=1000,
        best_ask_tick=1001,
    ) == tuple(range(1001, 1101))

    class Depth:
        best_bid_tick = 1000
        best_ask_tick = 1001

        def bid_qty_at_tick(self, tick):
            return {1000: 0.001, 900: 0.002}.get(tick, 0.0)

        def ask_qty_at_tick(self, tick):
            return {1001: 0.003, 1100: 0.004}.get(tick, 0.0)

    sell = f.market_sweep_visible_qty(Depth(), direction=SHORT)
    buy = f.market_sweep_visible_qty(Depth(), direction=LONG)
    assert sell == (0.003, 900, 1000, 101)
    assert buy == (0.007, 1001, 1100, 100)
    assert f.quantity_lots(sell[0]) == 3
    assert f.quantity_lots(buy[0]) == 7


@pytest.mark.skipif(
    not _hftbacktest_available(),
    reason="frozen patched hftbacktest unavailable in generic CI",
)
def test_real_partial_fill_exchange_insufficient_sweep_expires_nonflat():
    import hftbacktest as h

    identity = f.q1.validate_runtime_identity(h)
    assert identity.compiled_artifact_sha256 == (
        "051f204ef714ad8baeac205c1a26ace3"
        "20598e6a3aabad6517d7028b9e0425f1"
    )
    h, bt = _build_real_partial_fill_backtest(bid_qty=0.001)

    try:
        visible_qty, lower, upper, count = f.market_sweep_visible_qty(
            bt.depth(0),
            direction=SHORT,
        )
        requested_qty = 0.002
        assert requested_qty > visible_qty
        view = m4.submit_forced_flatten(
            bt,
            h,
            direction=SHORT,
            qty=requested_qty,
            order_id=4901,
            wait=True,
        )
        cumulative = requested_qty - view.leaves_qty
        post_position = float(bt.position(0))
        expected_post = 0.002 - cumulative

        assert (lower, upper, count) == (900, 1000, 101)
        assert math.isclose(visible_qty, 0.001, abs_tol=1e-12)
        assert view.status == d2.HFT_EXPIRED
        assert view.leaves_qty > 1e-12
        assert math.isclose(cumulative, 0.001, abs_tol=1e-12)
        assert abs(post_position) > 1e-12
        assert f.classify_flatten_execution(
            requested_qty=requested_qty,
            market_sweep_visible_qty=visible_qty,
            leaves_qty=view.leaves_qty,
            post_position=post_position,
            expected_post_position=expected_post,
        ) == f.MARKET_DEPTH_SWEEP_INSUFFICIENT
    finally:
        assert int(bt.close()) == 0


@pytest.mark.skipif(
    not _hftbacktest_available(),
    reason="frozen patched hftbacktest unavailable in generic CI",
)
def test_real_partial_fill_exchange_sufficient_sweep_fills_flat():
    import hftbacktest as h

    f.q1.validate_runtime_identity(h)
    h, bt = _build_real_partial_fill_backtest(bid_qty=0.002)

    try:
        visible_qty, lower, upper, count = f.market_sweep_visible_qty(
            bt.depth(0),
            direction=SHORT,
        )
        requested_qty = 0.002
        view = m4.submit_forced_flatten(
            bt,
            h,
            direction=SHORT,
            qty=requested_qty,
            order_id=4901,
            wait=True,
        )
        cumulative = requested_qty - view.leaves_qty

        assert (lower, upper, count) == (900, 1000, 101)
        assert math.isclose(visible_qty, requested_qty, abs_tol=1e-12)
        assert view.status == d2.HFT_FILLED
        assert abs(view.leaves_qty) <= 1e-12
        assert math.isclose(cumulative, requested_qty, abs_tol=1e-12)
        assert abs(bt.position(0)) <= 1e-12
    finally:
        assert int(bt.close()) == 0


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    (
        (
            {
                "requested_qty": 0.002,
                "market_sweep_visible_qty": 0.001,
                "leaves_qty": 0.001,
                "post_position": 0.001,
                "expected_post_position": 0.001,
            },
            f.MARKET_DEPTH_SWEEP_INSUFFICIENT,
        ),
        (
            {
                "requested_qty": 0.002,
                "market_sweep_visible_qty": 0.002,
                "leaves_qty": 0.001,
                "post_position": 0.001,
                "expected_post_position": 0.001,
            },
            f.MARKET_ORDER_UNEXPECTED_PARTIAL,
        ),
        (
            {
                "requested_qty": 0.002,
                "market_sweep_visible_qty": 0.002,
                "leaves_qty": 0.0,
                "post_position": 0.001,
                "expected_post_position": 0.0,
            },
            f.POSITION_ACCOUNTING_MISMATCH,
        ),
        (
            {
                "requested_qty": 0.002,
                "market_sweep_visible_qty": 0.002,
                "leaves_qty": 0.0,
                "post_position": 0.0,
                "expected_post_position": 0.0,
            },
            f.OTHER_EXECUTION_MISMATCH,
        ),
    ),
)
def test_classification_is_mechanical(kwargs, expected):
    assert f.classify_flatten_execution(**kwargs) == expected


def test_completed_flatten_nonflat_is_enriched_not_silenced(monkeypatch):
    def inherited_failure(self):
        raise base.RealHistoricalDriverError("completed_flatten_nonflat")

    monkeypatch.setattr(
        d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel,
        "_maybe_execute_forced_flatten",
        inherited_failure,
    )
    kernel = object.__new__(f.FlattenForensicContinuousHistoricalPolicyKernel)

    with pytest.raises(
        f.FlattenForensicError,
        match="^completed_flatten_nonflat_forensic$",
    ) as captured:
        kernel._maybe_execute_forced_flatten()

    assert isinstance(captured.value.__cause__, base.RealHistoricalDriverError)
    assert str(captured.value.__cause__) == "completed_flatten_nonflat"


def test_failed_q1_artifact_is_exact_and_contract_uses_no_market_open():
    assert hashlib.sha256(f.FAILED_Q1_EVIDENCE_PATH.read_bytes()).hexdigest() == (
        "03eb0554c1085e6adbe14e1544045edac"
        "4e2c5ee41949912aaeb3f779aed7ac4"
    )
    f.validate_forensic_contract()


def test_result_overwrite_refused(monkeypatch, tmp_path):
    root = tmp_path / "forensic"
    monkeypatch.setattr(f, "RESULT_ROOT", root)
    monkeypatch.setattr(f, "RESULT_PATH", root / "result.json")
    f._write_json_new({"status": "first"})
    with pytest.raises(f.FlattenForensicError, match="forensic_result_exists"):
        f._write_json_new({"status": "second"})


def test_mocked_entrypoint_writes_failure_facts_without_economics(
    monkeypatch,
    tmp_path,
):
    root = tmp_path / "forensic-entry"
    monkeypatch.setattr(f, "RESULT_ROOT", root)
    monkeypatch.setattr(f, "RESULT_PATH", root / "result.json")
    monkeypatch.setenv(f.AUTHORIZATION_ENV, f.AUTHORIZATION_TOKEN)
    repository = f.ForensicRepositoryIdentity(
        branch=f.EXPECTED_BRANCH,
        head="a" * 40,
        remote_ref=f.EXPECTED_REMOTE_REF,
        remote_head="a" * 40,
        tracked_worktree_clean=True,
        permitted_untracked_paths=(
            "evidence/dev045_d6r9a_feb01_full_day_v2.json",
        ),
        d6r20_driver_blob=f.D6R20_DRIVER_BLOB,
        d6r20_canonical_runner_absent=True,
        result_surface_virgin=True,
    )
    monkeypatch.setattr(f, "validate_repository_preflight", lambda: repository)
    monkeypatch.setattr(f, "validate_forensic_contract", lambda: None)
    monkeypatch.setattr(
        f,
        "_hftbacktest_module",
        lambda: object(),
    )
    monkeypatch.setattr(
        f.q1,
        "validate_runtime_identity",
        lambda h: f.q1.RuntimeIdentity(
            version="2.4.4",
            compiled_artifact_sha256=(
                "051f204ef714ad8baeac205c1a26ace3"
                "20598e6a3aabad6517d7028b9e0425f1"
            ),
            verified=True,
        ),
    )

    class Source:
        path = Path("/synthetic/january.npy")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(f, "open_verified_january_source", lambda **kwargs: Source())
    monkeypatch.setattr(f.base, "_stat_identity", lambda path: (1, 2, 3, 4))

    def fail(source, *, forensic_sink):
        forensic_sink.append(_attempt())
        raise f.FlattenForensicError("completed_flatten_nonflat_forensic")

    monkeypatch.setattr(f, "run_bound_forensic_replay", fail)
    with pytest.raises(
        f.FlattenForensicError,
        match="completed_flatten_nonflat_forensic",
    ):
        f.run_flatten_execution_forensic(
            authorization_token=f.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    payload = json.loads(f.RESULT_PATH.read_text(encoding="utf-8"))
    assert payload["flatten_attempt_count"] == 1
    assert payload["flatten_attempts"][0]["cumulative_executed_qty"] == 0.001
    assert payload["classifications"] == [
        f.MARKET_DEPTH_SWEEP_INSUFFICIENT
    ]
    assert payload["canonical_economic_attempt"] is False
    assert payload["canonical_attempt_consumed"] is False
    assert payload["economic_arena_called"] is False
    assert payload["strategy_ranking_performed"] is False
    assert payload["economic_conclusion"] == "UNAVAILABLE"
    assert payload["live_trading_authorized"] is False

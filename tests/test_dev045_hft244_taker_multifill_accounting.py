from __future__ import annotations

import hashlib
import importlib.metadata
import math
import os
from pathlib import Path
import subprocess

import pytest

from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket.dev044_t0_strategy_contract import LONG, SHORT
from tools import patch_hftbacktest_244_safe as v1_patcher
from tools import patch_hftbacktest_244_safe_v2 as patcher


PATCH_EXPECTATION = os.environ.get("DEV045_HFT244_PATCH_EXPECTATION")
SOURCE_ROOT_TEXT = os.environ.get("DEV045_HFT244_SOURCE_ROOT")
EXPECTED_BINARY_SHA256 = os.environ.get(
    "DEV045_HFT244_EXPECTED_BINARY_SHA256"
)


def _require_engine(expectation: str):
    if PATCH_EXPECTATION != expectation:
        pytest.skip(f"requires {expectation} isolated hftbacktest runtime")

    import hftbacktest as h

    assert importlib.metadata.version("hftbacktest") == "2.4.4"
    binary_paths = tuple(
        sorted(Path(h.__file__).resolve().parent.glob("_hftbacktest*.so"))
    )
    assert len(binary_paths) == 1
    binary_sha256 = hashlib.sha256(binary_paths[0].read_bytes()).hexdigest()

    if EXPECTED_BINARY_SHA256 is not None:
        assert binary_sha256 == EXPECTED_BINARY_SHA256

    return h


def _event_row(h, array, index, *, side, timestamp, price, qty):
    array[index]["ev"] = int(
        h.DEPTH_EVENT | h.EXCH_EVENT | h.LOCAL_EVENT | side
    )
    array[index]["exch_ts"] = int(timestamp)
    array[index]["local_ts"] = int(timestamp)
    array[index]["px"] = float(price)
    array[index]["qty"] = float(qty)


def _snapshot(h, *, bids, asks):
    import numpy as np

    rows = tuple((h.BUY_EVENT, *row) for row in bids) + tuple(
        (h.SELL_EVENT, *row) for row in asks
    )
    result = np.zeros(len(rows), dtype=h.event_dtype)

    for index, (side, price, qty) in enumerate(rows):
        result[index]["ev"] = int(
            h.DEPTH_SNAPSHOT_EVENT | h.EXCH_EVENT | h.LOCAL_EVENT | side
        )
        result[index]["exch_ts"] = 100_000_000
        result[index]["local_ts"] = 100_000_000
        result[index]["px"] = float(price)
        result[index]["qty"] = float(qty)

    return result


def _build_backtest(h, *, bids, asks, taker_fee=0.0):
    import numpy as np

    data = np.zeros(2, dtype=h.event_dtype)
    _event_row(
        h,
        data,
        0,
        side=h.SELL_EVENT,
        timestamp=1_000_000_000,
        price=max(price for price, _qty in asks) + 10.0,
        qty=1.0,
    )
    _event_row(
        h,
        data,
        1,
        side=h.SELL_EVENT,
        timestamp=10_000_000_000,
        price=max(price for price, _qty in asks) + 10.0,
        qty=1.0,
    )
    asset = (
        h.BacktestAsset()
        .data([data])
        .initial_snapshot(_snapshot(h, bids=bids, asks=asks))
        .linear_asset(1.0)
        .constant_order_latency(0, 0)
        .risk_adverse_queue_model()
        .partial_fill_exchange()
        .trading_value_fee_model(0.0, float(taker_fee))
        .tick_size(p.TICK_SIZE)
        .lot_size(p.LOT_SIZE)
    )
    bt = h.HashMapMarketDepthBacktest([asset])
    assert int(bt.wait_next_feed(False, 2_000_000_000)) == 2
    return bt


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


def _seed_position(bt, h, *, direction, qty, order_id):
    view = m4.submit_forced_flatten(
        bt,
        h,
        direction=direction,
        qty=qty,
        order_id=order_id,
        wait=True,
    )
    assert view.status == h.FILLED
    assert abs(view.leaves_qty) <= 1e-12
    return view


def _buy_three_level_backtest(h, *, requested_qty=0.003, taker_fee=0.0):
    bt = _build_backtest(
        h,
        bids=((100.0, requested_qty),),
        asks=((100.1, 0.001), (100.2, 0.001), (100.3, 0.001)),
        taker_fee=taker_fee,
    )
    _seed_position(
        bt,
        h,
        direction=SHORT,
        qty=requested_qty,
        order_id=7001,
    )
    assert math.isclose(bt.position(0), -requested_qty, abs_tol=1e-12)
    return bt


def _sell_three_level_backtest(h, *, taker_fee=0.0):
    bt = _build_backtest(
        h,
        bids=((100.3, 0.001), (100.2, 0.001), (100.1, 0.001)),
        asks=((100.4, 0.003),),
        taker_fee=taker_fee,
    )
    _seed_position(
        bt,
        h,
        direction=LONG,
        qty=0.003,
        order_id=7001,
    )
    assert math.isclose(bt.position(0), 0.003, abs_tol=1e-12)
    return bt


def test_patchset_is_v1_plus_one_centralized_partial_response_change():
    assert patcher.BASE_COMMIT == (
        "a244a14250b42d97fc305569c93c4117cd5e1dff"
    )
    assert patcher.PATCHSET == (
        "ISSUE_312_EXACT_QTY_CLEANUP",
        "ISSUE_316_PARTIAL_LOCAL_ACCOUNTING",
        "TAKER_MULTILEVEL_INTERMEDIATE_RESPONSE_ACCOUNTING",
    )
    assert patcher.V1_REPLACEMENTS == v1_patcher.REPLACEMENTS
    assert len(patcher.FILL_FALSE_CALL_SITES) == 10
    assert all(
        item.role.startswith("IMMEDIATE_LIQUIDITY_TAKING")
        for item in patcher.FILL_FALSE_CALL_SITES
    )
    assert sum(
        item.role == "IMMEDIATE_LIQUIDITY_TAKING_LOOP"
        for item in patcher.FILL_FALSE_CALL_SITES
    ) == 8
    assert sum(
        item.role == "IMMEDIATE_LIQUIDITY_TAKING_FINAL_REMAINDER"
        for item in patcher.FILL_FALSE_CALL_SITES
    ) == 2
    assert (
        "MAKE_RESPONSE || order.status == Status::PartiallyFilled"
        in patcher.TAKER_RESPONSE_NEW
    )
    assert "Status::Filled" not in patcher.TAKER_RESPONSE_NEW


def test_patcher_rejects_wrong_base_commit(monkeypatch, tmp_path):
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(
        patcher,
        "_git_output",
        lambda root, *args: "f" * 40,
    )

    with pytest.raises(SystemExit, match="REFUSE_PATCH base_commit"):
        patcher.require_exact_clean_base(tmp_path)


def test_patched_source_has_exact_call_site_and_replacement_counts():
    if SOURCE_ROOT_TEXT is None:
        pytest.skip("isolated exact hftbacktest source root not supplied")

    root = Path(SOURCE_ROOT_TEXT)
    completed = subprocess.run(
        ("git", "-C", str(root), "rev-parse", "HEAD"),
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == patcher.BASE_COMMIT
    partial = (
        root / "hftbacktest/src/backtest/proc/partialfillexchange.rs"
    ).read_text(encoding="utf-8")
    patcher.audit_fill_false_call_sites(partial)
    assert partial.count(patcher.TAKER_RESPONSE_OLD) == 0
    assert partial.count(patcher.TAKER_RESPONSE_NEW) == 1

    for relative_path, replacements in patcher.V1_REPLACEMENTS.items():
        text = (root / relative_path).read_text(encoding="utf-8")

        for old, new, count in replacements:
            assert text.count(old) == 0
            assert text.count(new) == count


def test_a_v1_exact_three_level_buy_reproduces_local_underaccounting():
    h = _require_engine("v1")
    bt = _buy_three_level_backtest(h)

    try:
        before = _state_tuple(bt)
        view = m4.submit_forced_flatten(
            bt,
            h,
            direction=LONG,
            qty=0.003,
            order_id=7002,
            wait=True,
        )
        after = _state_tuple(bt)

        assert view.status == h.FILLED
        assert abs(view.leaves_qty) <= 1e-12
        assert math.isclose(view.exec_qty, 0.001, abs_tol=1e-12)
        assert math.isclose(after[0] - before[0], 0.001, abs_tol=1e-12)
        assert math.isclose(after[0], -0.002, abs_tol=1e-12)
    finally:
        assert int(bt.close()) == 0


def test_a_v2_exact_three_level_buy_accounts_every_slice_once():
    h = _require_engine("v2")
    bt = _buy_three_level_backtest(h)

    try:
        before = _state_tuple(bt)
        view = m4.submit_forced_flatten(
            bt,
            h,
            direction=LONG,
            qty=0.003,
            order_id=7002,
            wait=True,
        )
        after = _state_tuple(bt)

        assert view.status == h.FILLED
        assert abs(view.leaves_qty) <= 1e-12
        assert math.isclose(view.exec_qty, 0.001, abs_tol=1e-12)
        assert math.isclose(after[0] - before[0], 0.003, abs_tol=1e-12)
        assert abs(after[0]) <= 1e-12
        assert after[3] - before[3] == 3
    finally:
        assert int(bt.close()) == 0


def test_b_v2_exact_three_level_sell_accounts_every_slice_once():
    h = _require_engine("v2")
    bt = _sell_three_level_backtest(h)

    try:
        before = _state_tuple(bt)
        view = m4.submit_forced_flatten(
            bt,
            h,
            direction=SHORT,
            qty=0.003,
            order_id=7002,
            wait=True,
        )
        after = _state_tuple(bt)

        assert view.status == h.FILLED
        assert abs(view.leaves_qty) <= 1e-12
        assert math.isclose(after[0] - before[0], -0.003, abs_tol=1e-12)
        assert abs(after[0]) <= 1e-12
        assert after[3] - before[3] == 3
    finally:
        assert int(bt.close()) == 0


def test_c_v2_multi_price_balance_and_fee_are_per_slice_exact():
    h = _require_engine("v2")
    taker_fee = 0.002
    prices = (100.1, 100.2, 100.3)
    bt = _buy_three_level_backtest(h, taker_fee=taker_fee)

    try:
        before = _state_tuple(bt)
        view = m4.submit_forced_flatten(
            bt,
            h,
            direction=LONG,
            qty=0.003,
            order_id=7002,
            wait=True,
        )
        after = _state_tuple(bt)
        per_slice_value = math.fsum(price * 0.001 for price in prices)

        assert view.status == h.FILLED
        assert math.isclose(after[0] - before[0], 0.003, abs_tol=1e-12)
        assert math.isclose(
            after[1] - before[1],
            -per_slice_value,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        assert math.isclose(
            after[2] - before[2],
            per_slice_value * taker_fee,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        assert after[3] - before[3] == 3
        assert math.isclose(after[4] - before[4], 0.003, abs_tol=1e-12)
        assert math.isclose(
            after[5] - before[5],
            per_slice_value,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    finally:
        assert int(bt.close()) == 0


def test_d_v2_one_level_final_fill_is_not_double_accounted():
    h = _require_engine("v2")
    bt = _build_backtest(
        h,
        bids=((100.0, 0.003),),
        asks=((100.1, 0.003),),
    )
    _seed_position(bt, h, direction=SHORT, qty=0.003, order_id=7001)

    try:
        before = _state_tuple(bt)
        view = m4.submit_forced_flatten(
            bt,
            h,
            direction=LONG,
            qty=0.003,
            order_id=7002,
            wait=True,
        )
        after = _state_tuple(bt)

        assert view.status == h.FILLED
        assert math.isclose(view.exec_qty, 0.003, abs_tol=1e-12)
        assert math.isclose(after[0] - before[0], 0.003, abs_tol=1e-12)
        assert abs(after[0]) <= 1e-12
        assert after[3] - before[3] == 1
    finally:
        assert int(bt.close()) == 0


def test_e_v2_multilevel_partial_then_expired_accounts_only_real_slices():
    h = _require_engine("v2")
    bt = _buy_three_level_backtest(h, requested_qty=0.004)

    try:
        before = _state_tuple(bt)
        view = m4.submit_forced_flatten(
            bt,
            h,
            direction=LONG,
            qty=0.004,
            order_id=7002,
            wait=True,
        )
        after = _state_tuple(bt)

        assert view.status == h.EXPIRED
        assert math.isclose(view.leaves_qty, 0.001, abs_tol=1e-12)
        assert math.isclose(view.exec_qty, 0.001, abs_tol=1e-12)
        assert math.isclose(after[0] - before[0], 0.003, abs_tol=1e-12)
        assert math.isclose(after[0], -0.001, abs_tol=1e-12)
        assert after[3] - before[3] == 3
        assert math.isclose(after[4] - before[4], 0.003, abs_tol=1e-12)
    finally:
        assert int(bt.close()) == 0


def test_f_v2_issue_316_resting_maker_partial_local_accounting():
    h = _require_engine("v2")
    import numpy as np
    from hftbacktest.order import PARTIALLY_FILLED

    data = np.zeros(4, dtype=h.event_dtype)
    _event_row(
        h,
        data,
        0,
        side=h.SELL_EVENT,
        timestamp=1_000_000_000,
        price=100.1,
        qty=8.0,
    )

    for index, (timestamp, qty) in enumerate(
        ((3_000_000_000, 10.0), (5_000_000_000, 0.001)),
        start=1,
    ):
        data[index]["ev"] = int(
            h.TRADE_EVENT | h.EXCH_EVENT | h.LOCAL_EVENT | h.SELL_EVENT
        )
        data[index]["exch_ts"] = timestamp
        data[index]["local_ts"] = timestamp
        data[index]["px"] = 100.0
        data[index]["qty"] = qty

    _event_row(
        h,
        data,
        3,
        side=h.SELL_EVENT,
        timestamp=8_000_000_000,
        price=100.1,
        qty=8.0,
    )
    asset = (
        h.BacktestAsset()
        .data([data])
        .initial_snapshot(m4.make_initial_snapshot())
        .linear_asset(1.0)
        .constant_order_latency(100_000_000, 100_000_000)
        .risk_adverse_queue_model()
        .partial_fill_exchange()
        .trading_value_fee_model(0.0, 0.0)
        .tick_size(p.TICK_SIZE)
        .lot_size(p.LOT_SIZE)
    )
    bt = h.HashMapMarketDepthBacktest([asset])

    try:
        assert int(bt.wait_next_feed(False, 2_000_000_000)) == 2
        rc = bt.submit_buy_order(
            0, 7101, 100.0, 0.002, h.GTC, h.LIMIT, True
        )
        assert int(rc) == 0
        assert int(bt.wait_next_feed(False, 3_000_000_000)) == 2
        assert int(bt.wait_next_feed(True, 600_000_000)) == 0
        assert int(bt.wait_next_feed(False, 3_000_000_000)) == 2
        assert int(bt.wait_next_feed(True, 600_000_000)) == 3
        order = bt.orders(0).get(7101)
        assert order.status == PARTIALLY_FILLED
        assert math.isclose(order.exec_qty, 0.001, abs_tol=1e-12)
        assert math.isclose(order.leaves_qty, 0.001, abs_tol=1e-12)
        assert math.isclose(bt.position(0), 0.001, abs_tol=1e-12)
    finally:
        assert int(bt.close()) == 0


def test_g_v2_issue_312_exact_quantity_cleanup_allows_order_id_reuse():
    h = _require_engine("v2")
    data = m4.make_fill_fixture()
    bt = h.HashMapMarketDepthBacktest(
        [
            m4.build_asset(
                data,
                entry_latency_ns=100_000_000,
                response_latency_ns=100_000_000,
            )
        ]
    )

    try:
        assert int(bt.wait_next_feed(False, 2_000_000_000)) == 2
        decision = p.policy_decision("M01", m4.policy_book())
        first = m4.submit_passive(
            bt,
            h,
            side="bid",
            order_id=7101,
            decision=decision,
            wait=True,
        )
        assert first.status == h.NEW
        assert int(bt.wait_next_feed(False, 3_000_000_000)) == 2
        assert int(bt.wait_next_feed(True, 600_000_000)) == 0
        assert int(bt.wait_next_feed(False, 3_000_000_000)) == 2
        assert int(bt.wait_next_feed(True, 600_000_000)) == 3
        filled = bt.orders(0).get(7101)
        assert filled.status == h.FILLED
        assert abs(filled.leaves_qty) <= 1e-12

        bt.clear_inactive_orders(0)
        replacement = m4.submit_passive(
            bt,
            h,
            side="bid",
            order_id=7101,
            decision=decision,
            wait=True,
        )
        assert replacement.status == h.NEW
    finally:
        assert int(bt.close()) == 0

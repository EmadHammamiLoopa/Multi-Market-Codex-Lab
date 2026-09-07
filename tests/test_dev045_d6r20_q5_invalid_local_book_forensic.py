from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from multimarket import dev045_d6r20_q4_scheduler_reconciled_driver as q4_driver
from multimarket import dev045_d6r20_q5_invalid_local_book_driver as driver
from multimarket import dev045_d6r20_q5_invalid_local_book_forensic as forensic
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket import dev045_m6_event_loop_kernel as d2


class FakeDepth:
    def __init__(self, bid_tick: int, ask_tick: int) -> None:
        self.best_bid_tick = int(bid_tick)
        self.best_ask_tick = int(ask_tick)
        self.best_bid = float(bid_tick * p.TICK_SIZE)
        self.best_ask = float(ask_tick * p.TICK_SIZE)
        self.bid_quantities = {int(bid_tick): 2.0}
        self.ask_quantities = {int(ask_tick): 3.0}

    def bid_qty_at_tick(self, tick: int) -> float:
        return float(self.bid_quantities.get(int(tick), 0.0))

    def ask_qty_at_tick(self, tick: int) -> float:
        return float(self.ask_quantities.get(int(tick), 0.0))


class FakeBacktest:
    def __init__(self, *, bid_tick: int, ask_tick: int, timestamp: int) -> None:
        self.current_timestamp = int(timestamp)
        self._depth = FakeDepth(bid_tick, ask_tick)
        self._position = 0.0
        self._state = SimpleNamespace(
            position=0.0,
            balance=17.0,
            fee=0.25,
            num_trades=4,
            trading_volume=0.004,
            trading_value=0.4,
        )
        self.order_state = ((101, 1, 0.001),)

    def depth(self, asset_no: int):
        assert asset_no == 0
        return self._depth

    def position(self, asset_no: int) -> float:
        assert asset_no == 0
        return self._position

    def state_values(self, asset_no: int):
        assert asset_no == 0
        return self._state


class FakeFlow:
    def __init__(self) -> None:
        self.calls = 0

    def quantities(self, *, current_local_timestamp_ns: int):
        assert current_local_timestamp_ns >= 0
        self.calls += 1
        return 0.4, 0.2


def _kernel(*, bid_tick: int, ask_tick: int, timestamp: int = 2_000_000_000):
    kernel = object.__new__(
        driver.InvalidLocalBookForensicContinuousHistoricalPolicyKernel
    )
    kernel.bt = FakeBacktest(
        bid_tick=bid_tick,
        ask_tick=ask_tick,
        timestamp=timestamp,
    )
    kernel.h = SimpleNamespace()
    kernel.policy_id = "M06"
    kernel.day = "2026-04-01"
    kernel.scenario = "Q0_PRIMARY_250_250"
    kernel.flow = FakeFlow()
    kernel.inventory_clock = d1.InventoryClock.flat()
    kernel.bid = SimpleNamespace(
        order_id=101,
        replacement_required=False,
    )
    kernel.ask = SimpleNamespace(
        order_id=None,
        replacement_required=True,
    )
    kernel.terminal_shutdown_started = False
    kernel.terminal_shutdown_quiescent = False
    kernel.terminal_shutdown_start_ns = None
    kernel.policy_epochs = 7
    kernel.adapter_candidate_epochs = 3
    kernel.direct_action_queries = 3
    kernel.direct_action_rows_found = 2
    kernel.direct_action_missing_rows = 1
    kernel.direct_action_explicit_abstains = 0
    kernel.q4_policy_epoch_timestamps = [1_000_000_000]
    kernel.q4_skipped_policy_epochs = 0
    kernel._ensure_forensic_state()
    return kernel


@pytest.mark.parametrize(
    ("bid_tick", "ask_tick", "classification"),
    (
        (0, 1001, driver.BID_NONPOSITIVE),
        (1000, 1000, driver.ASK_NOT_ABOVE_BID),
        (1001, 1000, driver.ASK_NOT_ABOVE_BID),
        (0, 0, driver.BOTH_INVALID),
    ),
)
def test_invalid_book_classifications_preserve_original_failure(
    bid_tick,
    ask_tick,
    classification,
):
    kernel = _kernel(bid_tick=bid_tick, ask_tick=ask_tick)

    with pytest.raises(d2.EventLoopKernelError, match="^invalid_local_book$"):
        kernel._dynamic_market_state(local_timestamp_ns=2_000_000_000)

    snapshot = kernel.q5_invalid_local_book_snapshot
    assert snapshot is not None
    assert snapshot["classification"] == classification
    assert snapshot["best_bid_tick"] == bid_tick
    assert snapshot["best_ask_tick"] == ask_tick
    assert snapshot["best_bid"] == bid_tick * p.TICK_SIZE
    assert snapshot["best_ask"] == ask_tick * p.TICK_SIZE
    assert kernel.q5_recent_local_books[-1]["classification"] == classification
    assert len(kernel.q5_recent_local_books) <= 32


def test_valid_book_delegates_to_q4_without_forensic_failure():
    kernel = _kernel(bid_tick=1000, ask_tick=1001)
    state = kernel._dynamic_market_state(local_timestamp_ns=2_000_000_000)

    assert state.best_bid_tick == 1000
    assert state.best_ask_tick == 1001
    assert state.bid_depth_qty[1000] == 2.0
    assert state.ask_depth_qty[1001] == 3.0
    assert state.inventory == 0.0
    assert state.aggressive_buy_qty_1s == 0.4
    assert state.aggressive_sell_qty_1s == 0.2
    assert kernel.q5_invalid_local_book_snapshot is None
    assert kernel.q5_last_valid_local_book_top["best_bid_tick"] == 1000


def test_invalid_book_fails_before_adapter_or_direct_support_decision(monkeypatch):
    kernel = _kernel(bid_tick=0, ask_tick=1001)

    def forbidden_adapter(**kwargs):
        raise AssertionError("adapter/direct support must not be reached")

    monkeypatch.setattr(kernel, "_adapter_decision", forbidden_adapter)

    with pytest.raises(d2.EventLoopKernelError, match="^invalid_local_book$"):
        kernel._evaluate_policy_epoch(local_timestamp_ns=2_000_000_000)

    snapshot = kernel.q5_invalid_local_book_snapshot
    assert snapshot["policy_epoch_count_before_evaluation"] == 7
    assert snapshot["policy_epoch_count_before_failure"] == 8
    assert snapshot["adapter_candidate_count_before_evaluation"] == 3
    assert snapshot["adapter_candidate_count_at_failure"] == 3
    assert snapshot["adapter_decision_count_before_evaluation"] == 0
    assert snapshot["adapter_decision_count_at_failure"] == 0
    assert snapshot["direct_action_lookup_count_before_evaluation"] == 3
    assert snapshot["direct_action_lookup_count_at_failure"] == 3


def test_instrumentation_is_observationally_pure():
    kernel = _kernel(bid_tick=1000, ask_tick=1000)
    before = {
        "position": kernel.bt.position(0),
        "state": deepcopy(vars(kernel.bt.state_values(0))),
        "orders": deepcopy(kernel.bt.order_state),
        "bid": deepcopy(vars(kernel.bid)),
        "ask": deepcopy(vars(kernel.ask)),
        "clock": kernel.inventory_clock,
    }

    with pytest.raises(d2.EventLoopKernelError, match="^invalid_local_book$"):
        kernel._dynamic_market_state(local_timestamp_ns=2_000_000_000)

    after = {
        "position": kernel.bt.position(0),
        "state": deepcopy(vars(kernel.bt.state_values(0))),
        "orders": deepcopy(kernel.bt.order_state),
        "bid": deepcopy(vars(kernel.bid)),
        "ask": deepcopy(vars(kernel.ask)),
        "clock": kernel.inventory_clock,
    }
    assert after == before
    snapshot = kernel.q5_invalid_local_book_snapshot
    assert snapshot["simulator_position"] == 0.0
    assert snapshot["state_values"] == {
        "position": 0.0,
        "balance": 17.0,
        "fee": 0.25,
        "num_trades": 4,
        "trading_volume": 0.004,
        "trading_value": 0.4,
    }


def test_q5_inherits_q4_scheduler_reconciliation_without_semantic_change():
    cls = driver.InvalidLocalBookForensicContinuousHistoricalPolicyKernel
    assert issubclass(
        cls,
        q4_driver.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel,
    )
    assert cls.run_full_day is q4_driver.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel.run_full_day
    assert cls._consume_due_policy_target is q4_driver.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel._consume_due_policy_target

    kernel = _kernel(bid_tick=1000, ask_tick=1001)
    cases = (
        (1_500_000_000, 2_000_000_000, 2_000_000_000),
        (2_000_000_000, 2_000_000_000, 2_000_000_000),
        (2_200_000_000, 2_000_000_000, 3_000_000_000),
        (4_600_000_000, 2_000_000_000, 5_000_000_000),
    )

    for current, target, expected in cases:
        assert kernel._reconcile_policy_target(
            current_local_ns=current,
            next_policy_ns=target,
        ) == expected
        assert kernel.q5_last_blocking_wait_reconciliation == {
            "current_local_ns": current,
            "previous_next_policy_ns": target,
            "reconciled_next_policy_ns": expected,
        }


def test_forensic_closed_exact_scope_lineage_and_no_economics(monkeypatch):
    assert forensic.EXPERIMENT_ID == "DEV045-D6R20-Q5-FORENSIC"
    assert forensic.DESIGN_VERSION == "invalid-local-book-state-forensic-v1"
    assert forensic.FORENSIC_SCOPE == (
        ("2026-04-01", "M06", "Q0_PRIMARY_250_250"),
    )
    assert forensic.AUTHORIZATION_ENV == (
        "DEV045_D6R20_Q5_FORENSIC_AUTHORIZE"
    )
    assert forensic.AUTHORIZATION_TOKEN == (
        "YES_REAL_HFTBACKTEST_INVALID_LOCAL_BOOK_FORENSIC_D6R20_Q5"
    )
    assert forensic.HISTORICAL_KERNEL is (
        driver.InvalidLocalBookForensicContinuousHistoricalPolicyKernel
    )
    assert forensic.FORENSIC_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert forensic.REAL_HISTORICAL_FORENSIC_EXECUTED is False
    assert forensic.Q4_RERUN_AUTHORIZED is False
    assert forensic.CANONICAL_RUNNER_IMPLEMENTED is False
    assert forensic.CANONICAL_ECONOMIC_ATTEMPT is False
    assert forensic.CANONICAL_ATTEMPT_CONSUMED is False
    assert forensic.ECONOMIC_ARENA_CALLED is False
    assert forensic.STRATEGY_RANKING_PERFORMED is False
    assert forensic.AUTOMATIC_RETRY is False
    assert forensic.LIVE_TRADING_AUTHORIZED is False

    monkeypatch.delenv(forensic.AUTHORIZATION_ENV, raising=False)
    with pytest.raises(
        forensic.InvalidLocalBookForensicError,
        match="execution_gate_closed",
    ):
        forensic._require_authorization(
            authorization_token=forensic.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )
    with pytest.raises(
        forensic.InvalidLocalBookForensicError,
        match="authorization_environment",
    ):
        forensic._require_authorization(
            authorization_token=forensic.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    source = Path(forensic.__file__).read_text(encoding="utf-8")
    assert "run_" + "economic_arena" not in source
    assert "." + "cycles" not in source
    assert "strategy_ranking_performed\": False" in source


def test_q4_failure_is_byte_identical_and_facts_are_exact():
    path = forensic.Q4_FAILURE_EVIDENCE_PATH
    assert hashlib.sha256(path.read_bytes()).hexdigest() == (
        "93e27d418e62eae86bc5608c9a241024c57fbd1f9aee215091b1c57ea5667e87"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["completed_qualification_replay_count"] == 16
    assert (
        payload["current_day"],
        payload["current_policy"],
        payload["current_scenario"],
    ) == ("2026-04-01", "M06", "Q0_PRIMARY_250_250")
    assert payload["exception_type"] == "EventLoopKernelError"
    assert payload["exception_message"] == "invalid_local_book"
    forensic.validate_forensic_contract()


def test_bounded_post_failure_source_window_is_small_and_decoded():
    h = SimpleNamespace(
        DEPTH_EVENT=1,
        DEPTH_CLEAR_EVENT=2,
        DEPTH_SNAPSHOT_EVENT=4,
        TRADE_EVENT=8,
        EXCH_EVENT=16,
        LOCAL_EVENT=32,
        BUY_EVENT=64,
        SELL_EVENT=128,
    )
    dtype = np.dtype(
        [
            ("ev", "i8"),
            ("exch_ts", "i8"),
            ("local_ts", "i8"),
            ("px", "f8"),
            ("qty", "f8"),
        ]
    )
    data = np.zeros(10, dtype=dtype)
    data["local_ts"] = np.arange(10) * 10
    data["exch_ts"] = data["local_ts"] - 1
    data["ev"] = h.DEPTH_EVENT | h.LOCAL_EVENT | h.BUY_EVENT
    data["px"] = 100.0 + np.arange(10) / 10.0
    data["qty"] = 1.0
    window = forensic.bounded_source_window(
        data,
        failure_timestamp_ns=45,
        h=h,
        radius=2,
    )
    assert window["search_left_index"] == 5
    assert window["search_right_index_exclusive"] == 5
    assert window["exact_timestamp_row_count"] == 0
    assert window["selected_row_count"] == 5
    assert [row["row_index"] for row in window["rows"]] == [3, 4, 5, 6, 7]
    assert all(row["decoded"]["side"] == "BUY" for row in window["rows"])
    assert all("DEPTH_EVENT" in row["decoded"]["event_types"] for row in window["rows"])
    assert window["read_only_post_failure_diagnostic"] is True
    assert window["fed_back_into_execution"] is False


def test_bounded_window_captures_both_ends_of_same_timestamp_group():
    h = SimpleNamespace()
    dtype = np.dtype(
        [
            ("ev", "i8"),
            ("exch_ts", "i8"),
            ("local_ts", "i8"),
            ("px", "f8"),
            ("qty", "f8"),
        ]
    )
    data = np.zeros(20, dtype=dtype)
    data["local_ts"] = (0, 1, *([5] * 16), 9, 10)
    window = forensic.bounded_source_window(
        data,
        failure_timestamp_ns=5,
        h=h,
        radius=2,
    )
    indices = [row["row_index"] for row in window["rows"]]
    assert window["search_left_index"] == 2
    assert window["search_right_index_exclusive"] == 18
    assert window["exact_timestamp_row_count"] == 16
    assert window["exact_timestamp_group_truncated"] is True
    assert indices == [0, 1, 2, 3, 4, 15, 16, 17, 18, 19]


def test_result_surface_overwrite_is_refused(monkeypatch, tmp_path):
    root = tmp_path / "q5"
    monkeypatch.setattr(forensic, "RESULT_ROOT", root)
    monkeypatch.setattr(forensic, "RESULT_PATH", root / "result.json")
    monkeypatch.setattr(forensic, "FAILURE_PATH", root / "failure.json")
    forensic._write_json_new(forensic.RESULT_PATH, {"status": "first"})

    with pytest.raises(
        forensic.InvalidLocalBookForensicError,
        match="forensic_result_exists",
    ):
        forensic._write_json_new(forensic.RESULT_PATH, {"status": "second"})


def test_mocked_entrypoint_records_snapshot_then_preserves_original_failure(
    monkeypatch,
    tmp_path,
):
    root = tmp_path / "q5-entry"
    monkeypatch.setattr(forensic, "RESULT_ROOT", root)
    monkeypatch.setattr(forensic, "RESULT_PATH", root / "result.json")
    monkeypatch.setattr(forensic, "FAILURE_PATH", root / "failure.json")
    monkeypatch.setenv(forensic.AUTHORIZATION_ENV, forensic.AUTHORIZATION_TOKEN)
    repository = forensic.ForensicRepositoryIdentity(
        branch=forensic.EXPECTED_BRANCH,
        head="a" * 40,
        remote_ref=forensic.EXPECTED_REMOTE_REF,
        remote_head="a" * 40,
        tracked_worktree_clean=True,
        permitted_untracked_paths=(),
        frozen_blobs_verified=True,
        v2_patch_sha256=forensic.V2_PATCH_SHA256,
        canonical_runners_absent=True,
        result_surface_virgin=True,
    )
    runtime = SimpleNamespace(
        version="2.4.4",
        compiled_artifact_sha256=forensic.HFTBACKTEST_BINARY_SHA256,
        verified=True,
    )
    monkeypatch.setattr(forensic, "validate_repository_preflight", lambda: repository)
    monkeypatch.setattr(forensic, "validate_runtime_identity", lambda h: runtime)
    monkeypatch.setattr(forensic, "validate_forensic_contract", lambda: None)
    monkeypatch.setattr(forensic, "load_forensic_support", lambda: object())
    monkeypatch.setattr(forensic, "_hftbacktest_module", lambda: SimpleNamespace())

    dtype = np.dtype(
        [
            ("ev", "i8"),
            ("exch_ts", "i8"),
            ("local_ts", "i8"),
            ("px", "f8"),
            ("qty", "f8"),
        ]
    )
    data = np.zeros(3, dtype=dtype)
    data["local_ts"] = (90, 100, 110)

    class Source:
        path = Path("/synthetic/april.npy")

        def __init__(self):
            self.data = data

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(
        forensic,
        "open_verified_forensic_source",
        lambda **kwargs: Source(),
    )
    monkeypatch.setattr(forensic.base, "_stat_identity", lambda path: (1, 2, 3, 4))

    def reproduce(source, *, direct_index, forensic_sink):
        forensic_sink.append(
            {
                "bt_current_timestamp": 100,
                "classification": driver.ASK_NOT_ABOVE_BID,
                "best_bid_tick": 1000,
                "best_ask_tick": 1000,
            }
        )
        raise d2.EventLoopKernelError("invalid_local_book")

    monkeypatch.setattr(forensic, "run_bound_forensic_replay", reproduce)

    with pytest.raises(d2.EventLoopKernelError, match="^invalid_local_book$"):
        forensic.run_invalid_local_book_forensic(
            authorization_token=forensic.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    payload = json.loads(forensic.RESULT_PATH.read_text(encoding="utf-8"))
    assert payload["status"] == "INVALID_LOCAL_BOOK_FORENSIC_CAPTURED"
    assert payload["original_exception_type"] == "EventLoopKernelError"
    assert payload["original_exception_message"] == "invalid_local_book"
    assert payload["forensic_classification"] == driver.ASK_NOT_ABOVE_BID
    assert payload["replay_continued_after_failure"] is False
    assert payload["source_identity_unchanged"] is True
    assert payload["canonical_economic_attempt"] is False
    assert payload["canonical_attempt_consumed"] is False
    assert payload["economic_arena_called"] is False
    assert payload["strategy_ranking_performed"] is False
    assert payload["economic_conclusion"] == "UNAVAILABLE"
    assert payload["automatic_retry"] is False
    assert payload["live_trading_authorized"] is False
    assert not forensic.FAILURE_PATH.exists()


def test_frozen_blob_constants_match_repository_files():
    checks = (
        (forensic.Q4_DRIVER_PATH, forensic.Q4_DRIVER_BLOB),
        (forensic.Q4_HARNESS_PATH, forensic.Q4_HARNESS_BLOB),
        (forensic.Q3_HARNESS_PATH, forensic.Q3_HARNESS_BLOB),
        (forensic.D6R20_DRIVER_PATH, forensic.D6R20_DRIVER_BLOB),
        (forensic.D6R19_DRIVER_PATH, forensic.D6R19_DRIVER_BLOB),
        (forensic.M4_ADAPTER_PATH, forensic.M4_ADAPTER_BLOB),
        (forensic.M4_M6_BINDING_PATH, forensic.M4_M6_BINDING_BLOB),
        (forensic.M3_POLICY_PATH, forensic.M3_POLICY_BLOB),
    )
    for path, expected in checks:
        assert forensic._git_blob(path) == expected
    assert forensic._sha256(forensic.V2_PATCH_PATH) == forensic.V2_PATCH_SHA256
    assert forensic._sha256(forensic.Q4_FAILURE_EVIDENCE_PATH) == forensic.Q4_FAILURE_SHA256


def test_known_invalid_predicate_is_exactly_frozen_parent_predicate():
    assert driver.classify_invalid_local_book(
        best_bid_tick=0,
        best_ask_tick=1,
    ) == driver.BID_NONPOSITIVE
    assert driver.classify_invalid_local_book(
        best_bid_tick=1,
        best_ask_tick=1,
    ) == driver.ASK_NOT_ABOVE_BID
    assert driver.classify_invalid_local_book(
        best_bid_tick=1,
        best_ask_tick=2,
    ) is None
    frozen = Path(d2.__file__).read_text(encoding="utf-8")
    assert "if best_bid <= 0 or best_ask <= best_bid:" in frozen


def test_recorded_prices_are_derived_from_frozen_tick_size():
    kernel = _kernel(bid_tick=999, ask_tick=998)
    with pytest.raises(d2.EventLoopKernelError, match="invalid_local_book"):
        kernel._dynamic_market_state(local_timestamp_ns=2_000_000_000)
    snapshot = kernel.q5_invalid_local_book_snapshot
    assert math.isclose(snapshot["best_bid"], 999 * p.TICK_SIZE)
    assert math.isclose(snapshot["best_ask"], 998 * p.TICK_SIZE)

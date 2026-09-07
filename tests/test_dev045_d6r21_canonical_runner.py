from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from multimarket import dev045_d6r18_fresh_replacement_driver as d6r18_driver
from multimarket import dev045_d6r19_response_batch_replacement_driver as d6r19_driver
from multimarket import dev045_d6r20_q6_initial_book_readiness_driver as q6_driver
from multimarket import dev045_d6r20_q8_terminal_shutdown_grid_alignment_driver as q8_driver
from multimarket import dev045_d6r21_canonical_runner as r
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_economic_arena as m6


def authorize(monkeypatch) -> None:
    monkeypatch.setenv(r.AUTHORIZATION_ENV, r.AUTHORIZATION_TOKEN)


def configure_result_surface(monkeypatch, tmp_path: Path) -> Path:
    root = tmp_path / "dev045_d6r21_canonical_economic_run_v1"
    monkeypatch.setattr(r, "RESULT_ROOT", root)
    monkeypatch.setattr(
        r,
        "FINAL_RESULT_PATH",
        root / "DEV045_D6R21_CANONICAL_ECONOMIC_RESULT.json",
    )
    monkeypatch.setattr(
        r,
        "FAILURE_RESULT_PATH",
        root / "DEV045_D6R21_CANONICAL_FAILURE.json",
    )
    return root


def make_replay(
    *,
    policy_id: str,
    day: str,
    scenario: str,
    integrity_failures: int = 0,
    terminal_flat: bool = True,
    working_slots: int = 0,
    total_fill_count: int = 0,
    cycles=(),
):
    return SimpleNamespace(
        policy_id=policy_id,
        day=day,
        scenario=scenario,
        audit=m6.ReplayAudit(
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            execution_integrity_failures=integrity_failures,
            terminal_flat=terminal_flat,
        ),
        natural_end_of_data=True,
        terminal_local_timestamp_ns=1,
        market_wakeups=0,
        response_wakeups=0,
        policy_epochs=0,
        submit_requests=0,
        cancel_requests=0,
        maker_fill_count=0,
        taker_fill_count=0,
        total_fill_count=total_fill_count,
        forced_flatten_count=0,
        flatten_order_ids=(),
        terminal_position=0.0,
        terminal_flat=terminal_flat,
        terminal_working_quote_slots=working_slots,
        terminal_shutdown_started=True,
        terminal_shutdown_quiescent=True,
        adapter_candidate_epochs=0,
        cycles=tuple(cycles),
    )


def make_captured(
    *,
    policy_id: str,
    day: str,
    scenario: str,
    fills=(),
    **replay_kwargs,
) -> r.CapturedReplay:
    replay = make_replay(
        policy_id=policy_id,
        day=day,
        scenario=scenario,
        total_fill_count=len(fills),
        **replay_kwargs,
    )
    return r.CapturedReplay(
        replay=replay,
        fills=tuple(fills),
        direct_action_queries=0,
        direct_action_rows_found=0,
        direct_action_missing_rows=0,
        direct_action_explicit_abstains=0,
        q8_execution_diagnostics={
            "raw_terminal_shutdown_cutoff_ns": 10,
            "aligned_terminal_shutdown_cutoff_ns": 9,
            "cutoff_alignment_shift_ns": 1,
            "frozen_terminal_shutdown_lead_ns": 1,
            "actual_terminal_shutdown_start_ns": 9,
            "remaining_ns_at_shutdown_start": 2,
            "terminal_start_no_later_than_raw_cutoff": True,
            "terminal_lead_preserved": True,
            "inventory_clock_matches_terminal_position": True,
        },
    )


def make_day(day: str) -> r.DayMatrixResult:
    return r.DayMatrixResult(
        day=day,
        replays=tuple(
            make_captured(
                policy_id=policy_id,
                day=day,
                scenario=scenario,
            )
            for policy_id in r.POLICY_ORDER
            for scenario in r.SCENARIO_ORDER
        ),
    )


def test_exact_d6r21_identity_and_closed_execution():
    assert r.EXPERIMENT_ID == "DEV045-D6R21"
    assert r.DESIGN_VERSION == (
        "canonical-historical-economic-runner-q8-terminal-grid-aligned-v1"
    )
    assert r.PARENT_FREEZE_HEAD == (
        "fc7733a776cff8fc726be630dae4d389abd00e8c"
    )
    assert r.Q8_EXECUTION_HEAD == (
        "bc6b66fdf2634cdacf04f2738722b36a9f1619d8"
    )
    assert r.Q8_RESULT_SHA256 == (
        "a1997947b378a851d48016a79715480955233ccfe040bba7348b697e578a2641"
    )
    assert r.Q8_RESULT_BYTES == 41_178
    assert r.CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert r.CANONICAL_ATTEMPT_CONSUMED is False
    assert r.AUTOMATIC_RETRY is False
    assert r.RERUN_AFTER_ATTEMPT_CONSUMPTION is False
    assert r.TUNING_AFTER_FIRST_OUTPUT is False


def test_q8_frozen_result_and_git_lineage_are_exact():
    lineage = r.validate_q8_frozen_lineage()
    assert lineage == {
        "result_status": "REAL_ENGINE_QUALIFICATION_PASS",
        "result_sha256": r.Q8_RESULT_SHA256,
        "result_bytes": 41_178,
        "execution_head": r.Q8_EXECUTION_HEAD,
        "replay_count": 20,
        "all_terminal_leads_preserved": True,
        "all_inventory_clocks_match_terminal_position": True,
    }


def test_exact_112_matrix():
    assert r.DAY_ORDER == (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    )
    assert r.POLICY_ORDER == (
        "M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08"
    )
    assert r.SCENARIO_ORDER == (
        "Q0_PRIMARY_250_250",
        "Q0_STRESS_500_500",
    )
    assert len(r.REPLAY_ORDER) == 112
    assert r.REPLAY_ORDER == tuple(r.d6r19.REPLAY_ORDER)


def test_exact_q8_kernel_and_validator_binding():
    r.validate_runner_contract()
    assert r.HISTORICAL_KERNEL is (
        q8_driver.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel
    )
    assert r.Q8_REPLAY_VALIDATOR is r.q8q._validate_completed_replay


@pytest.mark.parametrize(
    "forbidden",
    (
        d6r19_driver.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel,
        d6r18_driver.FreshReplacementContinuousHistoricalPolicyKernel,
        q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel,
        r.bridge.DirectActionContinuousHistoricalPolicyKernel,
    ),
)
def test_predecessor_kernel_binding_is_rejected(monkeypatch, forbidden):
    monkeypatch.setattr(r, "HISTORICAL_KERNEL", forbidden)

    with pytest.raises(r.CanonicalRunnerError):
        r.validate_runner_contract()


def test_exact_authorization_gate(monkeypatch):
    monkeypatch.delenv(r.AUTHORIZATION_ENV, raising=False)

    with pytest.raises(r.CanonicalRunnerError, match="execution_gate_closed"):
        r._require_authorization(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )

    with pytest.raises(r.CanonicalRunnerError, match="authorization_token"):
        r._require_authorization(
            authorization_token=(
                "YES_JAN_JUL_M6_MAKER_ECONOMIC_ARENA_D6R19_ONE_SHOT"
            ),
            execution_gate=True,
        )

    with pytest.raises(
        r.CanonicalRunnerError,
        match="authorization_environment",
    ):
        r._require_authorization(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    authorize(monkeypatch)
    r._require_authorization(
        authorization_token=r.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )


def test_closed_gate_precedes_q8_lineage_and_source_opener(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("opener")
        raise AssertionError("source opener reached")

    monkeypatch.setattr(r.adapter, "_open_verified_file", forbidden)
    monkeypatch.setattr(
        r,
        "validate_q8_frozen_lineage",
        lambda: calls.append("lineage"),
    )

    with pytest.raises(r.CanonicalRunnerError, match="execution_gate_closed"):
        r.open_verified_day_source(
            day="2026-01-01",
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )

    assert calls == []


def test_exact_112_replay_boundary_order(monkeypatch):
    authorize(monkeypatch)
    events = []
    source = SimpleNamespace(path=Path("/synthetic/source.npy"))

    monkeypatch.setattr(
        r,
        "validate_canonical_verified_source",
        lambda source, *, day: None,
    )
    monkeypatch.setattr(r.bridge, "_validate_day_mapping", lambda **kwargs: None)
    monkeypatch.setattr(r.base, "_stat_identity", lambda path: (1, 2, 3, 4))

    def replay(source, *, policy_id, day, scenario, direct_index):
        events.append(("replay", day, policy_id, scenario))
        return make_captured(
            policy_id=policy_id,
            day=day,
            scenario=scenario,
        )

    monkeypatch.setattr(r, "run_bound_verified_replay_with_fills", replay)

    result = r.run_verified_day_matrix_with_boundary(
        source,
        day="2026-01-01",
        direct_by_policy={},
        authorization_token=r.AUTHORIZATION_TOKEN,
        execution_gate=True,
        mark_attempt_started=lambda: events.append(("boundary",)),
    )

    assert len(result.replays) == 16

    for index, expected in enumerate(r.REPLAY_ORDER[:16]):
        assert events[2 * index] == ("boundary",)
        assert events[2 * index + 1] == ("replay", *expected)


def test_execution_integrity_failure_stops_day(monkeypatch):
    authorize(monkeypatch)
    source = SimpleNamespace(path=Path("/synthetic/source.npy"))
    monkeypatch.setattr(
        r,
        "validate_canonical_verified_source",
        lambda source, *, day: None,
    )
    monkeypatch.setattr(r.bridge, "_validate_day_mapping", lambda **kwargs: None)
    monkeypatch.setattr(r.base, "_stat_identity", lambda path: (1, 2, 3, 4))

    def bad(*args, **kwargs):
        return make_captured(
            policy_id=kwargs["policy_id"],
            day=kwargs["day"],
            scenario=kwargs["scenario"],
            integrity_failures=1,
        )

    monkeypatch.setattr(r, "run_bound_verified_replay_with_fills", bad)

    with pytest.raises(r.CanonicalRunnerError, match="execution_integrity_failure"):
        r.run_verified_day_matrix_with_boundary(
            source,
            day="2026-01-01",
            direct_by_policy={},
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=True,
            mark_attempt_started=lambda: None,
        )


@pytest.mark.parametrize(
    ("terminal_flat", "working_slots", "message"),
    (
        (False, 0, "terminal_not_flat"),
        (True, 1, "terminal_working_quotes"),
    ),
)
def test_terminal_integrity_stops_day(
    monkeypatch,
    terminal_flat,
    working_slots,
    message,
):
    authorize(monkeypatch)
    source = SimpleNamespace(path=Path("/synthetic/source.npy"))
    monkeypatch.setattr(
        r,
        "validate_canonical_verified_source",
        lambda source, *, day: None,
    )
    monkeypatch.setattr(r.bridge, "_validate_day_mapping", lambda **kwargs: None)
    monkeypatch.setattr(r.base, "_stat_identity", lambda path: (1, 2, 3, 4))

    def bad(*args, **kwargs):
        return make_captured(
            policy_id=kwargs["policy_id"],
            day=kwargs["day"],
            scenario=kwargs["scenario"],
            terminal_flat=terminal_flat,
            working_slots=working_slots,
        )

    monkeypatch.setattr(r, "run_bound_verified_replay_with_fills", bad)

    with pytest.raises(r.CanonicalRunnerError, match=message):
        r.run_verified_day_matrix_with_boundary(
            source,
            day="2026-01-01",
            direct_by_policy={},
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=True,
            mark_attempt_started=lambda: None,
        )


@dataclass(frozen=True)
class FakeQ8Diagnostics:
    raw_terminal_shutdown_cutoff_ns: int
    aligned_terminal_shutdown_cutoff_ns: int
    cutoff_alignment_shift_ns: int
    frozen_terminal_shutdown_lead_ns: int
    actual_terminal_shutdown_start_ns: int
    remaining_ns_at_shutdown_start: int


def _fake_q8_validator(*, lead=2, remaining=3):
    return FakeQ8Diagnostics(
        raw_terminal_shutdown_cutoff_ns=10,
        aligned_terminal_shutdown_cutoff_ns=9,
        cutoff_alignment_shift_ns=1,
        frozen_terminal_shutdown_lead_ns=lead,
        actual_terminal_shutdown_start_ns=9,
        remaining_ns_at_shutdown_start=remaining,
    )


def test_q8_alignment_validation(monkeypatch):
    monkeypatch.setattr(
        r,
        "Q8_REPLAY_VALIDATOR",
        lambda **kwargs: _fake_q8_validator(),
    )
    kernel = SimpleNamespace(
        terminal_shutdown_cutoff_ns=9,
        terminal_source_local_ns=12,
        inventory_clock=SimpleNamespace(
            position=0.0,
            nonzero_since_local_ns=None,
        ),
    )
    bt = SimpleNamespace(position=lambda asset_no: 0.0)

    payload = r._validate_q8_execution_state(
        bt=bt,
        kernel=kernel,
        replay=object(),
    )

    assert payload["cutoff_alignment_shift_ns"] == 1
    assert payload["remaining_ns_at_shutdown_start"] == 3


def test_q8_terminal_lead_erosion_rejected(monkeypatch):
    monkeypatch.setattr(
        r,
        "Q8_REPLAY_VALIDATOR",
        lambda **kwargs: _fake_q8_validator(lead=3, remaining=2),
    )
    kernel = SimpleNamespace(
        terminal_shutdown_cutoff_ns=9,
        terminal_source_local_ns=13,
        inventory_clock=SimpleNamespace(
            position=0.0,
            nonzero_since_local_ns=None,
        ),
    )
    bt = SimpleNamespace(position=lambda asset_no: 0.0)

    with pytest.raises(
        r.CanonicalRunnerError,
        match="terminal_shutdown_lead_not_preserved",
    ):
        r._validate_q8_execution_state(
            bt=bt,
            kernel=kernel,
            replay=object(),
        )


def test_q8_inventory_clock_mismatch_rejected(monkeypatch):
    monkeypatch.setattr(
        r,
        "Q8_REPLAY_VALIDATOR",
        lambda **kwargs: _fake_q8_validator(),
    )
    kernel = SimpleNamespace(
        terminal_shutdown_cutoff_ns=9,
        terminal_source_local_ns=12,
        inventory_clock=SimpleNamespace(
            position=0.001,
            nonzero_since_local_ns=1,
        ),
    )
    bt = SimpleNamespace(position=lambda asset_no: 0.0)

    with pytest.raises(
        r.CanonicalRunnerError,
        match="terminal_inventory_clock_mismatch",
    ):
        r._validate_q8_execution_state(
            bt=bt,
            kernel=kernel,
            replay=object(),
        )


def test_raw_fill_capture_and_reaccount_before_close(monkeypatch):
    lifecycle = []

    class FakeBacktest:
        closed = False

        def close(self):
            lifecycle.append("close")
            self.closed = True
            return 0

        def position(self, asset_no):
            return 0.0

    bt = FakeBacktest()
    raw_fill = object()
    replay = make_replay(
        policy_id="M01",
        day="2026-01-01",
        scenario="Q0_PRIMARY_250_250",
        total_fill_count=1,
        cycles=("cycle",),
    )

    class FillEvent:
        kind = binding.FILL

        @property
        def fill(self):
            assert bt.closed is False
            lifecycle.append("capture_fill")
            return raw_fill

    class FakeKernel:
        def __init__(self, **kwargs):
            self.bound_fills = (FillEvent(),)
            self.direct_action_queries = 0
            self.direct_action_rows_found = 0
            self.direct_action_missing_rows = 0
            self.direct_action_explicit_abstains = 0

        def run_full_day(self):
            lifecycle.append("run_full_day")
            return replay

    monkeypatch.setattr(r, "HISTORICAL_KERNEL", FakeKernel)
    monkeypatch.setattr(r.bridge, "validate_direct_index", lambda **kwargs: None)
    monkeypatch.setattr(
        r,
        "_hftbacktest_module",
        lambda: SimpleNamespace(
            HashMapMarketDepthBacktest=lambda assets: bt
        ),
    )
    monkeypatch.setattr(
        r.base,
        "_build_asset_from_verified_source",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(
        r,
        "_validate_q8_execution_state",
        lambda **kwargs: {"q8": True},
    )

    def parity(**kwargs):
        assert bt.closed is False
        assert kwargs["fills"] == (raw_fill,)
        lifecycle.append("reaccount")
        return tuple(kwargs["replay_cycles"])

    monkeypatch.setattr(r, "verify_reaccount_parity", parity)

    captured = r.run_bound_verified_replay_with_fills(
        SimpleNamespace(data=[{"local_ts": 123}]),
        policy_id="M01",
        day="2026-01-01",
        scenario="Q0_PRIMARY_250_250",
    )

    assert captured.fills == (raw_fill,)
    assert captured.q8_execution_diagnostics == {"q8": True}
    assert lifecycle == [
        "run_full_day",
        "capture_fill",
        "capture_fill",
        "reaccount",
        "close",
    ]


def test_source_opened_once_for_all_16_day_replays(monkeypatch):
    authorize(monkeypatch)
    lifecycle = []

    class Source:
        def __enter__(self):
            lifecycle.append("open")
            return self

        def __exit__(self, exc_type, exc, tb):
            lifecycle.append("close")
            return False

    monkeypatch.setattr(r, "load_frozen_day_support", lambda *, day: {})
    monkeypatch.setattr(r, "open_verified_day_source", lambda **kwargs: Source())

    def matrix(source, **kwargs):
        lifecycle.append("matrix_16")
        return make_day(kwargs["day"])

    monkeypatch.setattr(r, "run_verified_day_matrix_with_boundary", matrix)

    result = r.run_canonical_day_from_disk_with_boundary(
        day="2026-01-01",
        authorization_token=r.AUTHORIZATION_TOKEN,
        execution_gate=True,
        mark_attempt_started=lambda: None,
    )

    assert len(result.replays) == 16
    assert lifecycle == ["open", "matrix_16", "close"]


def test_frozen_support_semantics_unchanged(monkeypatch):
    calls = []

    def load(*, day, policy_id):
        calls.append((day, policy_id))
        return object()

    monkeypatch.setattr(r.support, "load_verified_day", load)

    for day in ("2026-01-01", "2026-02-01", "2026-03-01"):
        assert r.load_frozen_day_support(day=day) == {}

    assert set(r.load_frozen_day_support(day="2026-04-01")) == {"M06", "M07"}
    assert calls == [
        ("2026-04-01", "M06"),
        ("2026-04-01", "M07"),
    ]
    assert r.support.FORWARD_FILL_ENABLED is False
    assert r.support.BACKFILL_ENABLED is False
    assert r.support.INTERPOLATION_ENABLED is False
    assert r.support.A0_REFIT_ENABLED is False
    assert r.support.LEGACY_STATE_REMATERIALIZATION_ENABLED is False


def test_source_spec_constants_without_historical_open():
    spec = r._spec_for_day("2026-06-01")
    assert spec.rows == 172_540_697
    assert spec.bytes == 11_042_604_864
    assert spec.sha256 == (
        "ac97ad27c9d58b3b3e249547b8ae7c74"
        "cf2ebfde07965103bd9c8c05d0df1160"
    )


def test_json_normalization_prevents_q8_tuple_list_false_failure(tmp_path):
    raw = {
        "nested": {
            "tuple": (1, 2, ("x", "y")),
        },
        "items": (("a", 1), ("b", 2)),
    }
    round_trip = json.loads(json.dumps(raw, sort_keys=True))

    assert raw != round_trip

    normalized = r._json_normalize(raw)
    assert normalized == round_trip

    path = tmp_path / "result.json"
    r._write_json_new(path, normalized)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert normalized == saved

    with pytest.raises(r.CanonicalRunnerError, match="result_exists"):
        r._write_json_new(path, normalized)


def test_unsafe_raw_payload_saved_assertion_pattern_absent():
    source = Path(r.__file__).read_text(encoding="utf-8")
    assert "assert payload == saved" not in source
    assert "payload == saved" not in source
    assert r.JSON_NORMALIZATION_BEFORE_SUCCESS_WRITE is True
    assert r.RAW_PAYLOAD_SAVED_ASSERTION_ALLOWED is False
    assert r.POST_WRITE_SEMANTIC_ASSERTIONS_ALLOWED is False


def test_success_returns_json_normalized_artifact_without_false_failure(
    monkeypatch,
    tmp_path,
):
    root = configure_result_surface(monkeypatch, tmp_path)
    authorize(monkeypatch)
    monkeypatch.setattr(r, "validate_runner_contract", lambda: None)
    monkeypatch.setattr(
        r,
        "run_canonical_day_from_disk_with_boundary",
        lambda *, day, mark_attempt_started, **kwargs: (
            mark_attempt_started() or make_day(day)
        ),
    )
    monkeypatch.setattr(r, "write_day_evidence", lambda result: None)
    monkeypatch.setattr(
        r.m6,
        "run_economic_arena",
        lambda **kwargs: {
            "ranking": (("M01", 1), ("M02", 2)),
            "nested": {"tuple": (1, 2, 3)},
        },
    )

    returned = r.run_full_canonical_arena(
        authorization_token=r.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )

    saved = json.loads(r.FINAL_RESULT_PATH.read_text(encoding="utf-8"))

    assert returned == saved
    assert returned["arena"]["ranking"] == [["M01", 1], ["M02", 2]]
    assert r.FAILURE_RESULT_PATH.exists() is False
    assert root.exists()


def test_arena_not_called_before_complete_112(monkeypatch, tmp_path):
    configure_result_surface(monkeypatch, tmp_path)
    authorize(monkeypatch)
    monkeypatch.setattr(r, "validate_runner_contract", lambda: None)
    calls = []

    def day_runner(*, day, mark_attempt_started, **kwargs):
        mark_attempt_started()
        if day == "2026-06-01":
            raise r.CanonicalRunnerError("synthetic_stop")
        return make_day(day)

    monkeypatch.setattr(
        r,
        "run_canonical_day_from_disk_with_boundary",
        day_runner,
    )
    monkeypatch.setattr(r, "write_day_evidence", lambda result: None)
    monkeypatch.setattr(
        r.m6,
        "run_economic_arena",
        lambda **kwargs: calls.append("arena"),
    )

    with pytest.raises(r.CanonicalRunnerError, match="synthetic_stop"):
        r.run_full_canonical_arena(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert calls == []
    assert r.FINAL_RESULT_PATH.exists() is False
    assert r.FAILURE_RESULT_PATH.exists() is True


def test_arena_called_once_after_complete_112(monkeypatch, tmp_path):
    configure_result_surface(monkeypatch, tmp_path)
    authorize(monkeypatch)
    monkeypatch.setattr(r, "validate_runner_contract", lambda: None)
    monkeypatch.setattr(
        r,
        "run_canonical_day_from_disk_with_boundary",
        lambda *, day, mark_attempt_started, **kwargs: (
            mark_attempt_started() or make_day(day)
        ),
    )
    monkeypatch.setattr(r, "write_day_evidence", lambda result: None)
    calls = []

    def arena(**kwargs):
        calls.append(
            (
                len(kwargs["audits"]),
                len(kwargs["primary_fills"]),
                len(kwargs["stress_fills"]),
            )
        )
        return {"status": "synthetic"}

    monkeypatch.setattr(r.m6, "run_economic_arena", arena)

    result = r.run_full_canonical_arena(
        authorization_token=r.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )

    assert result["status"] == "CANONICAL_112_COMPLETE"
    assert result["replay_count"] == 112
    assert calls == [(112, 0, 0)]


def test_result_surface_overwrite_refused(monkeypatch, tmp_path):
    configure_result_surface(monkeypatch, tmp_path)
    r._write_json_new(r.FINAL_RESULT_PATH, {"status": "one"})

    with pytest.raises(r.CanonicalRunnerError, match="result_exists"):
        r._write_json_new(r.FINAL_RESULT_PATH, {"status": "two"})

    with pytest.raises(r.CanonicalRunnerError, match="final_result_exists"):
        r._require_virgin_result_surface()


def test_implementation_guards_are_closed():
    assert r.REAL_HISTORICAL_EXECUTION_DURING_IMPLEMENTATION is False
    assert r.HISTORICAL_SOURCE_OPENED_DURING_IMPLEMENTATION is False
    assert r.HISTORICAL_SOURCE_HASHED_DURING_IMPLEMENTATION is False
    assert r.ECONOMIC_ARENA_EXECUTED_DURING_IMPLEMENTATION is False
    assert r.Q8_HISTORICAL_RERUN_DURING_IMPLEMENTATION is False
    assert r.Q7_HISTORICAL_RERUN_DURING_IMPLEMENTATION is False
    assert r.Q6_HISTORICAL_RERUN_DURING_IMPLEMENTATION is False
    assert r.NETWORK_ACQUISITION_ENABLED is False
    assert r.RAILWAY_ENABLED is False
    assert r.LIVE_TRADING_AUTHORIZED is False
    assert r.AUG_OPEN_AUTHORIZED is False
    assert r.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r.NON_BTC_OPEN_AUTHORIZED is False


def test_future_result_surface_is_virgin_during_implementation():
    assert r.FINAL_RESULT_PATH.exists() is False
    assert r.FAILURE_RESULT_PATH.exists() is False
    assert r.RESULT_ROOT.exists() is False

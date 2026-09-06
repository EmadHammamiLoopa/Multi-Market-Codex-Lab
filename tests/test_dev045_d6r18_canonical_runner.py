from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from multimarket import dev045_d6r18_canonical_runner as r
from multimarket import dev045_d6r18_fresh_replacement_driver as fresh
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_economic_arena as m6


def authorize(monkeypatch) -> None:
    monkeypatch.setenv(r.AUTHORIZATION_ENV, r.AUTHORIZATION_TOKEN)


def configure_result_surface(monkeypatch, tmp_path: Path) -> Path:
    root = tmp_path / "dev045_d6r18_canonical_economic_run_v1"
    monkeypatch.setattr(r, "RESULT_ROOT", root)
    monkeypatch.setattr(
        r,
        "FINAL_RESULT_PATH",
        root / "DEV045_D6R18_CANONICAL_ECONOMIC_RESULT.json",
    )
    monkeypatch.setattr(
        r,
        "FAILURE_RESULT_PATH",
        root / "DEV045_D6R18_CANONICAL_FAILURE.json",
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
        terminal_working_quote_slots=working_slots,
        total_fill_count=total_fill_count,
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


def test_execution_is_closed_by_default():
    assert r.EXPERIMENT_ID == "DEV045-D6R18"
    assert r.CANONICAL_SOURCE_OPEN_IMPLEMENTED is True
    assert r.CANONICAL_DAY_MATRIX_IMPLEMENTED is True
    assert r.FINAL_112_ARENA_IMPLEMENTED is True
    assert r.FRESH_REPLACEMENT_SEMANTICS is True
    assert r.CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert r.CANONICAL_ATTEMPT_CONSUMED is False
    assert r.AUTOMATIC_RETRY is False
    assert r.RERUN_AFTER_ATTEMPT_CONSUMPTION is False
    assert r.TUNING_AFTER_FIRST_OUTPUT is False
    assert r.NETWORK_ACQUISITION_ENABLED is False
    assert r.RAILWAY_ENABLED is False
    assert r.LIVE_TRADING_AUTHORIZED is False
    assert r.AUG_OPEN_AUTHORIZED is False
    assert r.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r.NON_BTC_OPEN_AUTHORIZED is False


def test_exact_new_authorization_gate(monkeypatch):
    assert r.AUTHORIZATION_ENV == "DEV045_D6R18_AUTHORIZE"
    assert r.AUTHORIZATION_TOKEN == (
        "YES_JAN_JUL_M6_MAKER_ECONOMIC_ARENA_D6R18_ONE_SHOT"
    )

    monkeypatch.delenv(r.AUTHORIZATION_ENV, raising=False)

    with pytest.raises(r.CanonicalRunnerError, match="execution_gate_closed"):
        r._require_authorization(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )

    with pytest.raises(r.CanonicalRunnerError, match="authorization_token"):
        r._require_authorization(
            authorization_token="D6R17_OR_WRONG_TOKEN",
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


def test_closed_gate_precedes_canonical_opener(monkeypatch):
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("canonical opener reached")

    monkeypatch.setattr(r.adapter, "_open_verified_file", forbidden)

    with pytest.raises(r.CanonicalRunnerError, match="execution_gate_closed"):
        r.open_verified_day_source(
            day="2026-01-01",
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )

    assert called is False


def test_exact_112_replay_order():
    r.validate_runner_contract()

    assert len(r.DAY_ORDER) == 7
    assert len(r.POLICY_ORDER) == 8
    assert len(r.SCENARIO_ORDER) == 2
    assert len(r.REPLAY_ORDER) == 112
    assert r.REPLAY_ORDER == tuple(
        (day, policy_id, scenario)
        for day in (
            "2026-01-01",
            "2026-02-01",
            "2026-03-01",
            "2026-04-01",
            "2026-05-01",
            "2026-06-01",
            "2026-07-01",
        )
        for policy_id in (
            "M01",
            "M02",
            "M03",
            "M04",
            "M05",
            "M06",
            "M07",
            "M08",
        )
        for scenario in (
            "Q0_PRIMARY_250_250",
            "Q0_STRESS_500_500",
        )
    )


def test_day_matrix_marks_boundary_immediately_before_each_ordered_replay(
    monkeypatch,
):
    authorize(monkeypatch)
    events = []
    source = SimpleNamespace(path=Path("/synthetic/source.npy"))

    monkeypatch.setattr(
        r,
        "validate_canonical_verified_source",
        lambda source, *, day: None,
    )
    monkeypatch.setattr(
        r.bridge,
        "_validate_day_mapping",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        r.base,
        "_stat_identity",
        lambda path: (1, 2, 3, 4),
    )

    def mark():
        events.append(("boundary",))

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
        mark_attempt_started=mark,
    )

    assert len(result.replays) == 16
    assert len(events) == 32

    for index, expected in enumerate(
        item
        for item in r.REPLAY_ORDER
        if item[0] == "2026-01-01"
    ):
        assert events[2 * index] == ("boundary",)
        assert events[2 * index + 1] == ("replay", *expected)


def test_replay_uses_d6r18_kernel_and_captures_raw_fills_before_close(
    monkeypatch,
):
    lifecycle = []

    class FakeBacktest:
        closed = False

        def close(self):
            lifecycle.append("close")
            self.closed = True
            return 0

    bt = FakeBacktest()
    raw_fill = object()

    class FillEvent:
        kind = binding.FILL

        @property
        def fill(self):
            assert bt.closed is False
            lifecycle.append("capture_fill")
            return raw_fill

    replay = make_replay(
        policy_id="M01",
        day="2026-01-01",
        scenario="Q0_PRIMARY_250_250",
        total_fill_count=1,
        cycles=("frozen-cycle",),
    )

    class FakeKernel:
        def __init__(self, **kwargs):
            lifecycle.append("d6r18_kernel_init")
            self.bound_fills = (FillEvent(),)
            self.direct_action_queries = 0
            self.direct_action_rows_found = 0
            self.direct_action_missing_rows = 0
            self.direct_action_explicit_abstains = 0

        def run_full_day(self):
            lifecycle.append("run_full_day")
            return replay

    class ForbiddenD6R17Kernel:
        def __init__(self, **kwargs):
            raise AssertionError("D6R17 kernel instantiated")

    monkeypatch.setattr(
        r.fresh,
        "FreshReplacementContinuousHistoricalPolicyKernel",
        FakeKernel,
    )
    monkeypatch.setattr(
        r.bridge,
        "DirectActionContinuousHistoricalPolicyKernel",
        ForbiddenD6R17Kernel,
    )
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
        r.bridge,
        "validate_direct_index",
        lambda **kwargs: None,
    )

    def parity(**kwargs):
        assert bt.closed is False
        assert kwargs["fills"] == (raw_fill,)
        lifecycle.append("reaccount_parity")
        return tuple(kwargs["replay_cycles"])

    monkeypatch.setattr(r, "verify_reaccount_parity", parity)

    source = SimpleNamespace(data=[{"local_ts": 123}])
    captured = r.run_bound_verified_replay_with_fills(
        source,
        policy_id="M01",
        day="2026-01-01",
        scenario="Q0_PRIMARY_250_250",
    )

    assert captured.fills[0] is raw_fill
    assert lifecycle[0:2] == ["d6r18_kernel_init", "run_full_day"]
    assert lifecycle.index("capture_fill") < lifecycle.index("close")
    assert lifecycle.index("reaccount_parity") < lifecycle.index("close")
    assert lifecycle[-1] == "close"


def test_raw_fill_count_parity_is_required():
    replay = make_replay(
        policy_id="M01",
        day="2026-01-01",
        scenario="Q0_PRIMARY_250_250",
        total_fill_count=1,
    )

    with pytest.raises(r.CanonicalRunnerError, match="raw_fill_count_parity"):
        r.CapturedReplay(
            replay=replay,
            fills=(),
            direct_action_queries=0,
            direct_action_rows_found=0,
            direct_action_missing_rows=0,
            direct_action_explicit_abstains=0,
        )


def test_reaccount_cycle_parity_is_required(monkeypatch):
    fill = m6.FillRecord(
        policy_id="M01",
        day="2026-01-01",
        timestamp_ns=1_767_225_600_000_000_000,
        side="BUY",
        qty=0.001,
        price=100.0,
        liquidity="MAKER",
    )
    monkeypatch.setattr(r.m6, "account_fill_bucket", lambda *args, **kwargs: [])

    with pytest.raises(r.CanonicalRunnerError, match="reaccount_cycle_parity"):
        r.verify_reaccount_parity(
            policy_id="M01",
            day="2026-01-01",
            scenario="Q0_PRIMARY_250_250",
            replay_total_fill_count=1,
            replay_cycles=(object(),),
            fills=(fill,),
        )


def test_source_is_opened_once_for_all_day_replays(monkeypatch):
    authorize(monkeypatch)
    lifecycle = []

    class Source:
        def __enter__(self):
            lifecycle.append("open")
            return self

        def __exit__(self, exc_type, exc, tb):
            lifecycle.append("close")
            return False

    monkeypatch.setattr(
        r,
        "load_frozen_day_support",
        lambda *, day: {},
    )
    monkeypatch.setattr(
        r,
        "open_verified_day_source",
        lambda **kwargs: Source(),
    )

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


def test_frozen_direct_action_support_semantics_are_reused(monkeypatch):
    calls = []

    def load(*, day, policy_id):
        calls.append((day, policy_id))
        return object()

    monkeypatch.setattr(r.support, "load_verified_day", load)

    for day in ("2026-01-01", "2026-02-01", "2026-03-01"):
        assert r.load_frozen_day_support(day=day) == {}

    result = r.load_frozen_day_support(day="2026-04-01")
    assert set(result) == {"M06", "M07"}
    assert calls == [
        ("2026-04-01", "M06"),
        ("2026-04-01", "M07"),
    ]
    assert r.support.POLICY_TO_CORE_COLUMN["M06"][2] == "T10A_ACTION"
    assert r.support.POLICY_TO_CORE_COLUMN["M07"][2] == "T05A_ACTION"
    assert r.support.FORWARD_FILL_ENABLED is False
    assert r.support.BACKFILL_ENABLED is False
    assert r.support.INTERPOLATION_ENABLED is False
    assert r.support.A0_REFIT_ENABLED is False
    assert r.support.LEGACY_STATE_REMATERIALIZATION_ENABLED is False


def test_june_authoritative_source_identity_is_exact():
    spec = r._spec_for_day("2026-06-01")

    assert spec.rows == 172_540_697
    assert spec.bytes == 11_042_604_864
    assert spec.sha256 == (
        "ac97ad27c9d58b3b3e249547b8ae7c74"
        "cf2ebfde07965103bd9c8c05d0df1160"
    )
    assert spec == r.d6r17._spec_for_day("2026-06-01")


def test_execution_integrity_failure_stops_matrix(monkeypatch):
    authorize(monkeypatch)
    calls = []
    source = SimpleNamespace(path=Path("/synthetic/source.npy"))

    monkeypatch.setattr(
        r,
        "validate_canonical_verified_source",
        lambda source, *, day: None,
    )
    monkeypatch.setattr(
        r.bridge,
        "_validate_day_mapping",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        r.base,
        "_stat_identity",
        lambda path: (1, 2, 3, 4),
    )

    def replay(source, *, policy_id, day, scenario, direct_index):
        calls.append((day, policy_id, scenario))
        return make_captured(
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            integrity_failures=1,
        )

    monkeypatch.setattr(r, "run_bound_verified_replay_with_fills", replay)

    with pytest.raises(
        r.CanonicalRunnerError,
        match="execution_integrity_failure",
    ):
        r.run_verified_day_matrix_with_boundary(
            source,
            day="2026-01-01",
            direct_by_policy={},
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=True,
            mark_attempt_started=lambda: None,
        )

    assert calls == [("2026-01-01", "M01", "Q0_PRIMARY_250_250")]


def test_negative_economics_do_not_stop_day_matrix(monkeypatch):
    authorize(monkeypatch)
    calls = []
    source = SimpleNamespace(path=Path("/synthetic/source.npy"))
    negative_cycle = SimpleNamespace(net_pnl=-1_000_000.0)

    monkeypatch.setattr(
        r,
        "validate_canonical_verified_source",
        lambda source, *, day: None,
    )
    monkeypatch.setattr(
        r.bridge,
        "_validate_day_mapping",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        r.base,
        "_stat_identity",
        lambda path: (1, 2, 3, 4),
    )

    def replay(source, *, policy_id, day, scenario, direct_index):
        calls.append((day, policy_id, scenario))
        return make_captured(
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            cycles=(negative_cycle,),
        )

    monkeypatch.setattr(r, "run_bound_verified_replay_with_fills", replay)
    result = r.run_verified_day_matrix_with_boundary(
        source,
        day="2026-01-01",
        direct_by_policy={},
        authorization_token=r.AUTHORIZATION_TOKEN,
        execution_gate=True,
        mark_attempt_started=lambda: None,
    )

    assert len(calls) == 16
    assert len(result.replays) == 16
    assert all(
        captured.replay.cycles[0].net_pnl < 0
        for captured in result.replays
    )


@pytest.mark.parametrize("failure_stage", ("support", "open", "source_stat"))
def test_pre_first_replay_failure_does_not_consume_attempt(
    monkeypatch,
    tmp_path,
    failure_stage,
):
    authorize(monkeypatch)
    configure_result_surface(monkeypatch, tmp_path)

    class Source:
        path = Path("/synthetic/source.npy")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    if failure_stage == "support":
        monkeypatch.setattr(
            r,
            "load_frozen_day_support",
            lambda *, day: (_ for _ in ()).throw(RuntimeError("support_fail")),
        )
    else:
        monkeypatch.setattr(r, "load_frozen_day_support", lambda *, day: {})

    if failure_stage == "open":
        monkeypatch.setattr(
            r,
            "open_verified_day_source",
            lambda **kwargs: (_ for _ in ()).throw(RuntimeError("open_fail")),
        )
    else:
        monkeypatch.setattr(
            r,
            "open_verified_day_source",
            lambda **kwargs: Source(),
        )

    if failure_stage == "source_stat":
        monkeypatch.setattr(
            r,
            "validate_canonical_verified_source",
            lambda source, *, day: None,
        )
        monkeypatch.setattr(
            r.bridge,
            "_validate_day_mapping",
            lambda **kwargs: None,
        )
        monkeypatch.setattr(
            r.base,
            "_stat_identity",
            lambda path: (_ for _ in ()).throw(RuntimeError("source_stat_fail")),
        )

    with pytest.raises(RuntimeError, match=failure_stage.split("_")[0]):
        r.run_full_canonical_arena(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert r.FAILURE_RESULT_PATH.exists() is False
    assert r.FINAL_RESULT_PATH.exists() is False
    assert r.CANONICAL_ATTEMPT_CONSUMED is False


def test_first_replay_entry_consumes_and_failure_writes_evidence(
    monkeypatch,
    tmp_path,
):
    authorize(monkeypatch)
    configure_result_surface(monkeypatch, tmp_path)

    def fail_first_replay(**kwargs):
        kwargs["mark_attempt_started"]()
        raise RuntimeError("first_historical_replay_failure")

    monkeypatch.setattr(
        r,
        "run_canonical_day_from_disk_with_boundary",
        fail_first_replay,
    )

    with pytest.raises(RuntimeError, match="first_historical_replay_failure"):
        r.run_full_canonical_arena(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    payload = json.loads(r.FAILURE_RESULT_PATH.read_text(encoding="utf-8"))
    assert payload["experiment_id"] == "DEV045-D6R18"
    assert payload["attempt_consumed"] is True
    assert payload["attempt_boundary"] == r.BOUNDARY_SEMANTIC
    assert payload["completed_days"] == []
    assert payload["completed_replays"] == 0
    assert payload["automatic_retry"] is False
    assert payload["rerun_forbidden"] is True
    assert payload["fresh_replacement_semantics"] is True
    assert r.FINAL_RESULT_PATH.exists() is False


def test_incomplete_matrix_never_calls_final_arena(monkeypatch, tmp_path):
    authorize(monkeypatch)
    configure_result_surface(monkeypatch, tmp_path)
    completed = 0

    def day_runner(**kwargs):
        nonlocal completed
        kwargs["mark_attempt_started"]()

        if completed == 6:
            raise RuntimeError("day_seven_incomplete")

        day = r.DAY_ORDER[completed]
        completed += 1
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
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("arena called before 112")
        ),
    )

    with pytest.raises(RuntimeError, match="day_seven_incomplete"):
        r.run_full_canonical_arena(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert completed == 6
    assert r.FINAL_RESULT_PATH.exists() is False
    assert r.FAILURE_RESULT_PATH.exists() is True


def test_final_arena_called_once_only_after_complete_112(
    monkeypatch,
    tmp_path,
):
    authorize(monkeypatch)
    configure_result_surface(monkeypatch, tmp_path)
    events = []

    def day_runner(**kwargs):
        kwargs["mark_attempt_started"]()
        day = kwargs["day"]
        result = make_day(day)
        events.extend(
            (captured.replay.day, captured.replay.policy_id, captured.replay.scenario)
            for captured in result.replays
        )
        return result

    monkeypatch.setattr(
        r,
        "run_canonical_day_from_disk_with_boundary",
        day_runner,
    )
    monkeypatch.setattr(r, "write_day_evidence", lambda result: None)

    arena_calls = []

    def arena(*, primary_fills, stress_fills, audits):
        arena_calls.append(
            (len(events), len(primary_fills), len(stress_fills), len(audits))
        )
        return {"synthetic_negative_economics": True}

    monkeypatch.setattr(r.m6, "run_economic_arena", arena)

    payload = r.run_full_canonical_arena(
        authorization_token=r.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )

    assert tuple(events) == r.REPLAY_ORDER
    assert arena_calls == [(112, 0, 0, 112)]
    assert payload["experiment_id"] == "DEV045-D6R18"
    assert payload["status"] == "CANONICAL_112_COMPLETE"
    assert payload["replay_count"] == 112
    assert payload["day_count"] == 7
    assert payload["audit_count"] == 112
    assert payload["attempt_consumed"] is True
    assert payload["fresh_replacement_semantics"] is True
    assert payload["live_trading_authorized"] is False
    assert r.FINAL_RESULT_PATH.exists() is True
    assert r.FAILURE_RESULT_PATH.exists() is False


def test_result_overwrite_is_refused(monkeypatch, tmp_path):
    authorize(monkeypatch)
    root = configure_result_surface(monkeypatch, tmp_path)
    root.mkdir(parents=True)
    r.FINAL_RESULT_PATH.write_text("frozen\n", encoding="utf-8")

    with pytest.raises(r.CanonicalRunnerError, match="final_result_exists"):
        r.run_full_canonical_arena(
            authorization_token=r.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert r.FINAL_RESULT_PATH.read_text(encoding="utf-8") == "frozen\n"


def test_d6r18_result_surface_names_are_isolated():
    assert r.RESULT_ROOT.name == "dev045_d6r18_canonical_economic_run_v1"
    assert r.FINAL_RESULT_PATH.name == (
        "DEV045_D6R18_CANONICAL_ECONOMIC_RESULT.json"
    )
    assert r.FAILURE_RESULT_PATH.name == "DEV045_D6R18_CANONICAL_FAILURE.json"
    assert r.day_evidence_path("2026-04-01").name == (
        "2026-04-01_DEV045_D6R18_DAY_RESULT.json"
    )


def test_fresh_replacement_driver_blob_is_unchanged():
    data = Path(fresh.__file__).read_bytes()
    git_blob = hashlib.sha1(
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()

    assert r.FRESH_REPLACEMENT_DRIVER_BLOB == (
        "adc432f36814a1ccf1b2dd63219f5826c604753e"
    )
    assert git_blob == r.FRESH_REPLACEMENT_DRIVER_BLOB


def test_dedicated_workflow_is_synthetic_only():
    workflow = Path(
        ".github/workflows/dev045_d6r18_canonical_runner.yml"
    ).read_text(encoding="utf-8")

    assert "tests/test_dev045_d6r18_canonical_runner.py" in workflow
    assert "tests/test_dev045_d6r18_fresh_replacement_driver.py" in workflow
    assert "run_full_canonical_arena" not in workflow
    assert r.AUTHORIZATION_TOKEN not in workflow
    assert "/home/emadh/Multi-Market/evidence" not in workflow

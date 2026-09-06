from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from multimarket import dev045_d6r17_direct_action_driver_bridge as d6r17
from multimarket import dev045_d6r18_fresh_replacement_driver as d6r18
from multimarket import dev045_d6r19_response_batch_replacement_driver as d6r19
from multimarket import dev045_d6r20_real_engine_qualification as q
from multimarket import dev045_d6r20_residual_flatten_driver as d6r20
from multimarket import dev045_m4_m6_binding as binding


DAY_JAN = "2026-01-01"
DAY_APR = "2026-04-01"
PRIMARY = "Q0_PRIMARY_250_250"


def authorize(monkeypatch) -> None:
    monkeypatch.setenv(q.AUTHORIZATION_ENV, q.AUTHORIZATION_TOKEN)


def configure_result_surface(
    monkeypatch,
    tmp_path: Path,
    *,
    suffix: str = "default",
) -> Path:
    root = tmp_path / f"qualification-{suffix}"
    monkeypatch.setattr(q, "RESULT_ROOT", root)
    monkeypatch.setattr(
        q,
        "SUCCESS_RESULT_PATH",
        root / "DEV045_D6R20_Q1_QUALIFICATION_RESULT.json",
    )
    monkeypatch.setattr(
        q,
        "FAILURE_RESULT_PATH",
        root / "DEV045_D6R20_Q1_QUALIFICATION_FAILURE.json",
    )
    return root


def make_diagnostics(
    day: str,
    policy_id: str,
    scenario: str,
) -> q.ReplayExecutionDiagnostics:
    return q.ReplayExecutionDiagnostics(
        day=day,
        policy_id=policy_id,
        scenario=scenario,
        market_wakeups=10,
        response_wakeups=5,
        policy_epochs=3,
        submit_requests=2,
        cancel_requests=2,
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


def make_completed_runtime(*, fill_event=None):
    fills = () if fill_event is None else (fill_event,)
    fill_count = len(fills)

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
        market_wakeups=10,
        response_wakeups=5,
        policy_epochs=3,
        submit_requests=2,
        cancel_requests=2,
        maker_fill_count=fill_count,
        taker_fill_count=0,
        total_fill_count=fill_count,
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
    slot = SimpleNamespace(
        order_id=None,
        pending_replacement=None,
        replacement_required=False,
    )
    kernel = SimpleNamespace(
        bid=slot,
        ask=SimpleNamespace(
            order_id=None,
            pending_replacement=None,
            replacement_required=False,
        ),
        force_decision=None,
        flatten_done=False,
        flatten_decision_local_ns=None,
        flatten_response_local_ns=None,
        inventory_clock=SimpleNamespace(
            position=0.0,
            nonzero_since_local_ns=None,
        ),
        bound_fills=fills,
        flatten_order_ids=[],
        completed_forced_flattens=0,
        direct_action_queries=0,
        direct_action_rows_found=0,
        direct_action_missing_rows=0,
        direct_action_explicit_abstains=0,
    )

    class Backtest:
        def position(self, asset_no):
            assert asset_no == 0
            return 0.0

        def orders(self, asset_no):
            assert asset_no == 0
            return {}

    return Backtest(), kernel, replay


def test_qualification_is_closed_and_noncanonical_by_default():
    assert q.EXPERIMENT_ID == "DEV045-D6R20-Q1"
    assert q.QUALIFICATION_EXECUTION_AUTHORIZED_BY_DEFAULT is False
    assert q.REAL_HISTORICAL_QUALIFICATION_EXECUTED is False
    assert q.CANONICAL_RUNNER_IMPLEMENTED is False
    assert q.CANONICAL_ECONOMIC_ATTEMPT is False
    assert q.CANONICAL_ATTEMPT_CONSUMED is False
    assert q.ECONOMIC_ARENA_EXECUTED is False
    assert q.STRATEGY_RANKING_PERFORMED is False
    assert q.AUTOMATIC_RETRY is False
    assert q.NETWORK_ACQUISITION_ENABLED is False
    assert q.RAILWAY_ENABLED is False
    assert q.LIVE_TRADING_AUTHORIZED is False
    assert q.AUG_OPEN_AUTHORIZED is False
    assert q.SEP_PLUS_OPEN_AUTHORIZED is False
    assert q.NON_BTC_OPEN_AUTHORIZED is False


def test_exact_q1_authorization_and_canonical_token_cannot_authorize(monkeypatch):
    assert q.AUTHORIZATION_ENV == "DEV045_D6R20_Q1_AUTHORIZE"
    assert q.AUTHORIZATION_TOKEN == (
        "YES_REAL_HFTBACKTEST_EXECUTION_QUALIFICATION_D6R20_Q1"
    )
    monkeypatch.delenv(q.AUTHORIZATION_ENV, raising=False)

    with pytest.raises(q.QualificationError, match="execution_gate_closed"):
        q._require_authorization(
            authorization_token=q.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )

    canonical_token = (
        "YES_JAN_JUL_M6_MAKER_ECONOMIC_ARENA_D6R19_ONE_SHOT"
    )
    monkeypatch.setenv(q.AUTHORIZATION_ENV, canonical_token)
    with pytest.raises(q.QualificationError, match="authorization_token"):
        q._require_authorization(
            authorization_token=canonical_token,
            execution_gate=True,
        )

    monkeypatch.setenv(q.AUTHORIZATION_ENV, q.AUTHORIZATION_TOKEN)
    with pytest.raises(q.QualificationError, match="authorization_token"):
        q._require_authorization(
            authorization_token=canonical_token,
            execution_gate=True,
        )

    authorize(monkeypatch)
    q._require_authorization(
        authorization_token=q.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )


def test_closed_gate_precedes_historical_source_opener(monkeypatch):
    calls = []

    def forbidden(*args, **kwargs):
        calls.append("opened")
        raise AssertionError("historical source opener reached")

    monkeypatch.setattr(q.adapter, "_open_verified_file", forbidden)
    with pytest.raises(q.QualificationError, match="execution_gate_closed"):
        q.open_verified_qualification_source(
            day=DAY_JAN,
            authorization_token=q.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )

    assert calls == []


def test_exact_20_replay_matrix_and_deterministic_order():
    q.validate_qualification_contract()
    assert q.QUALIFICATION_DAY_ORDER == (DAY_JAN, DAY_APR)
    assert q.JANUARY_POLICIES == (
        "M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08"
    )
    assert q.APRIL_POLICIES == ("M06", "M07")
    assert q.SCENARIO_ORDER == (
        "Q0_PRIMARY_250_250",
        "Q0_STRESS_500_500",
    )
    assert len(q.QUALIFICATION_PLAN) == 20
    assert len(q._day_plan(DAY_JAN)) == 16
    assert len(q._day_plan(DAY_APR)) == 4
    assert q.QUALIFICATION_PLAN == (
        (DAY_JAN, "M01", "Q0_PRIMARY_250_250"),
        (DAY_JAN, "M01", "Q0_STRESS_500_500"),
        (DAY_JAN, "M02", "Q0_PRIMARY_250_250"),
        (DAY_JAN, "M02", "Q0_STRESS_500_500"),
        (DAY_JAN, "M03", "Q0_PRIMARY_250_250"),
        (DAY_JAN, "M03", "Q0_STRESS_500_500"),
        (DAY_JAN, "M04", "Q0_PRIMARY_250_250"),
        (DAY_JAN, "M04", "Q0_STRESS_500_500"),
        (DAY_JAN, "M05", "Q0_PRIMARY_250_250"),
        (DAY_JAN, "M05", "Q0_STRESS_500_500"),
        (DAY_JAN, "M06", "Q0_PRIMARY_250_250"),
        (DAY_JAN, "M06", "Q0_STRESS_500_500"),
        (DAY_JAN, "M07", "Q0_PRIMARY_250_250"),
        (DAY_JAN, "M07", "Q0_STRESS_500_500"),
        (DAY_JAN, "M08", "Q0_PRIMARY_250_250"),
        (DAY_JAN, "M08", "Q0_STRESS_500_500"),
        (DAY_APR, "M06", "Q0_PRIMARY_250_250"),
        (DAY_APR, "M06", "Q0_STRESS_500_500"),
        (DAY_APR, "M07", "Q0_PRIMARY_250_250"),
        (DAY_APR, "M07", "Q0_STRESS_500_500"),
    )


def test_d6r20_kernel_binding_exact_and_prior_bindings_forbidden(monkeypatch):
    assert q.HISTORICAL_KERNEL is (
        d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
    )

    for forbidden in (
        d6r19.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel,
        d6r18.FreshReplacementContinuousHistoricalPolicyKernel,
        d6r17.DirectActionContinuousHistoricalPolicyKernel,
    ):
        monkeypatch.setattr(q, "HISTORICAL_KERNEL", forbidden)
        with pytest.raises(q.QualificationError, match="d6r20_kernel_binding"):
            q.validate_qualification_contract()


def test_exact_source_specs_are_reused_without_opening_sources():
    january = q._spec_for_day(DAY_JAN)
    april = q._spec_for_day(DAY_APR)
    assert str(january.path) == (
        "/home/emadh/Multi-Market/runtime/dev045_d6r4b/output/"
        "BTCUSDT_2026-01-01.npy"
    )
    assert january.rows == 64_314_723
    assert january.bytes == 4_116_142_528
    assert january.sha256 == (
        "8f0a4fbd56ecdc261dbe2041ce138a094"
        "56423074925d495272716219a1d4da1"
    )
    assert str(april.path) == (
        "/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/"
        "BTCUSDT_2026-04-01.npy"
    )
    assert april.rows == 132_829_759
    assert april.bytes == 8_501_104_832
    assert april.sha256 == (
        "de7e0471e63631394981b301bb461d679"
        "192c37eb6241d4d8073cf0640eca7f7"
    )


def test_january_base_only_and_april_direct_support_exact(monkeypatch):
    calls = []
    indices = {"M06": object(), "M07": object()}

    def load(*, day):
        calls.append(day)
        return indices

    monkeypatch.setattr(q.d6r19_runner, "load_frozen_day_support", load)
    assert q.load_qualification_support(day=DAY_JAN) == {}
    assert q.load_qualification_support(day=DAY_APR) == indices
    assert calls == [DAY_APR]
    assert q.support.POLICY_TO_CORE_COLUMN["M06"][2] == "T10A_ACTION"
    assert q.support.POLICY_TO_CORE_COLUMN["M07"][2] == "T05A_ACTION"
    assert q.support.FORWARD_FILL_ENABLED is False
    assert q.support.BACKFILL_ENABLED is False
    assert q.support.INTERPOLATION_ENABLED is False
    assert q.support.A0_REFIT_ENABLED is False
    assert q.support.LEGACY_STATE_REMATERIALIZATION_ENABLED is False


def test_verified_day_preserves_exact_order_and_source_identity(monkeypatch):
    authorize(monkeypatch)
    events = []
    source = SimpleNamespace(path=Path("/synthetic/january.npy"))
    monkeypatch.setattr(
        q.d6r19_runner,
        "validate_canonical_verified_source",
        lambda source, *, day: None,
    )
    monkeypatch.setattr(q.bridge, "_validate_day_mapping", lambda **kwargs: None)
    monkeypatch.setattr(q.base, "_stat_identity", lambda path: (1, 2, 3, 4))

    def replay(source, *, policy_id, day, scenario, direct_index):
        events.append((day, policy_id, scenario, direct_index))
        return make_diagnostics(day, policy_id, scenario)

    monkeypatch.setattr(q, "run_bound_verified_qualification_replay", replay)
    result = q.run_verified_qualification_day(
        source,
        day=DAY_JAN,
        direct_by_policy={},
        authorization_token=q.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )
    assert tuple((x.day, x.policy_id, x.scenario) for x in result) == (
        q.QUALIFICATION_PLAN[:16]
    )
    assert events == [(*item, None) for item in q.QUALIFICATION_PLAN[:16]]


def test_source_opens_and_closes_once_per_day(monkeypatch):
    authorize(monkeypatch)
    lifecycle = []

    class Source:
        def __init__(self, day):
            self.day = day

        def __enter__(self):
            lifecycle.append(("open", self.day))
            return self

        def __exit__(self, exc_type, exc, tb):
            lifecycle.append(("close", self.day))
            return False

    monkeypatch.setattr(q, "load_qualification_support", lambda *, day: {})
    monkeypatch.setattr(
        q,
        "open_verified_qualification_source",
        lambda *, day, **kwargs: Source(day),
    )

    def run_day(source, *, day, **kwargs):
        lifecycle.append(("matrix", day, len(q._day_plan(day))))
        return tuple(
            make_diagnostics(replay_day, policy_id, scenario)
            for replay_day, policy_id, scenario in q._day_plan(day)
        )

    monkeypatch.setattr(q, "run_verified_qualification_day", run_day)
    for day in q.QUALIFICATION_DAY_ORDER:
        q.run_qualification_day_from_disk(
            day=day,
            authorization_token=q.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert lifecycle == [
        ("open", DAY_JAN),
        ("matrix", DAY_JAN, 16),
        ("close", DAY_JAN),
        ("open", DAY_APR),
        ("matrix", DAY_APR, 4),
        ("close", DAY_APR),
    ]


def test_real_replay_path_uses_d6r20_and_validates_fills_before_close(
    monkeypatch,
):
    lifecycle = []
    fill = binding.FillRecord(
        policy_id="M01",
        day=DAY_JAN,
        timestamp_ns=1,
        side="BUY",
        qty=0.001,
        price=100.0,
        liquidity=binding.MAKER,
    )

    class FillEvent:
        kind = binding.FILL

        @property
        def fill(self):
            lifecycle.append("capture_real_fill_record")
            assert "close" not in lifecycle
            return fill

    bt, kernel_state, replay = make_completed_runtime(fill_event=FillEvent())

    class Backtest:
        def position(self, asset_no):
            return bt.position(asset_no)

        def orders(self, asset_no):
            return bt.orders(asset_no)

        def close(self):
            lifecycle.append("close")
            return 0

    actual_bt = Backtest()

    class FakeD6R20Kernel:
        def __init__(self, **kwargs):
            lifecycle.append("d6r20_kernel")
            self.__dict__.update(kernel_state.__dict__)

        def run_full_day(self):
            lifecycle.append("run_full_day")
            return replay

    monkeypatch.setattr(q, "HISTORICAL_KERNEL", FakeD6R20Kernel)
    monkeypatch.setattr(
        q,
        "_hftbacktest_module",
        lambda: SimpleNamespace(
            HashMapMarketDepthBacktest=lambda assets: actual_bt,
        ),
    )
    monkeypatch.setattr(
        q.base,
        "_build_asset_from_verified_source",
        lambda *args, **kwargs: object(),
    )
    monkeypatch.setattr(q.bridge, "validate_direct_index", lambda **kwargs: None)
    result = q.run_bound_verified_qualification_replay(
        SimpleNamespace(data=[{"local_ts": 30}]),
        policy_id="M01",
        day=DAY_JAN,
        scenario=PRIMARY,
        direct_index=None,
    )
    assert result.total_fill_count == 1
    assert lifecycle[0:2] == ["d6r20_kernel", "run_full_day"]
    assert lifecycle[-1] == "close"
    assert lifecycle.count("capture_real_fill_record") >= 1


def test_completed_replay_requires_fill_and_terminal_parity():
    bt, kernel, replay = make_completed_runtime()
    result = q._validate_completed_replay(bt=bt, kernel=kernel, replay=replay)
    assert result.terminal_flat is True
    assert result.final_inventory_clock_flat is True

    replay.total_fill_count = 1
    with pytest.raises(q.QualificationError, match="raw_fill_count_parity"):
        q._validate_completed_replay(bt=bt, kernel=kernel, replay=replay)

    replay.total_fill_count = 0
    kernel.inventory_clock.position = 0.001
    with pytest.raises(q.QualificationError, match="local_inventory_clock_mismatch"):
        q._validate_completed_replay(bt=bt, kernel=kernel, replay=replay)


def test_hftbacktest_identity_validation_uses_compiled_artifact(tmp_path, monkeypatch):
    package = tmp_path / "hftbacktest"
    package.mkdir()
    init = package / "__init__.py"
    init.write_text("", encoding="utf-8")
    artifact = package / "_hftbacktest.synthetic.so"
    artifact.write_bytes(b"synthetic compiled artifact")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    monkeypatch.setattr(q, "HFTBACKTEST_BINARY_SHA256", digest)
    module = SimpleNamespace(__version__="2.4.4", __file__=str(init))
    identity = q.validate_runtime_identity(module)
    assert identity == q.RuntimeIdentity("2.4.4", digest, True)


def prepare_top_level_run(monkeypatch, tmp_path: Path, *, suffix="run"):
    configure_result_surface(monkeypatch, tmp_path, suffix=suffix)
    authorize(monkeypatch)
    monkeypatch.setattr(q, "_current_head", lambda: q.PARENT_HEAD)
    monkeypatch.setattr(q, "validate_qualification_contract", lambda: None)
    monkeypatch.setattr(
        q,
        "validate_runtime_identity",
        lambda h: q.RuntimeIdentity(
            q.HFTBACKTEST_VERSION,
            q.HFTBACKTEST_BINARY_SHA256,
            True,
        ),
    )
    monkeypatch.setattr(q, "_hftbacktest_module", lambda: object())


def test_success_requires_all_20_and_persists_operational_data_only(
    monkeypatch,
    tmp_path,
):
    prepare_top_level_run(monkeypatch, tmp_path)

    def run_day(*, day, on_replay_start, on_replay_complete, **kwargs):
        results = []
        for replay_day, policy_id, scenario in q._day_plan(day):
            on_replay_start(replay_day, policy_id, scenario)
            result = make_diagnostics(replay_day, policy_id, scenario)
            on_replay_complete(result)
            results.append(result)
        return tuple(results)

    monkeypatch.setattr(q, "run_qualification_day_from_disk", run_day)
    payload = q.run_real_engine_qualification(
        authorization_token=q.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )
    assert payload["status"] == "REAL_ENGINE_QUALIFICATION_PASS"
    assert payload["replay_count"] == 20
    assert payload["january_replays"] == 16
    assert payload["april_replays"] == 4
    assert payload["real_hftbacktest"] is True
    assert payload["canonical_economic_attempt"] is False
    assert payload["canonical_attempt_consumed"] is False
    assert payload["economic_arena_called"] is False
    assert payload["strategy_ranking_performed"] is False
    assert payload["economic_conclusion"] == "NOT_EVALUATED"
    assert len(payload["replays"]) == 20
    assert q.SUCCESS_RESULT_PATH.exists()

    serialized = json.loads(q.SUCCESS_RESULT_PATH.read_text(encoding="utf-8"))
    prohibited = {
        "net_pnl",
        "net_bps",
        "gross_bps",
        "profit_factor",
        "daily_return",
        "max_drawdown",
        "win_rate",
        "profitability",
        "economic_survivor_status",
    }

    def keys(value):
        if isinstance(value, dict):
            for key, item in value.items():
                yield key
                yield from keys(item)
        elif isinstance(value, list):
            for item in value:
                yield from keys(item)

    assert prohibited.isdisjoint(set(keys(serialized)))


def test_incomplete_matrix_cannot_pass(monkeypatch, tmp_path):
    prepare_top_level_run(monkeypatch, tmp_path, suffix="incomplete")

    def run_day(*, day, on_replay_start, on_replay_complete, **kwargs):
        if day == DAY_JAN:
            for replay_day, policy_id, scenario in q._day_plan(day):
                on_replay_start(replay_day, policy_id, scenario)
                on_replay_complete(
                    make_diagnostics(replay_day, policy_id, scenario)
                )
        return ()

    monkeypatch.setattr(q, "run_qualification_day_from_disk", run_day)
    with pytest.raises(q.QualificationError, match="completed_qualification_order"):
        q.run_real_engine_qualification(
            authorization_token=q.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )
    assert not q.SUCCESS_RESULT_PATH.exists()
    failure = json.loads(q.FAILURE_RESULT_PATH.read_text(encoding="utf-8"))
    assert failure["completed_qualification_replay_count"] == 16


@pytest.mark.parametrize(
    "message",
    (
        "ask_not_passive",
        "bid_not_passive",
        "local_inventory_clock_mismatch",
        "completed_flatten_nonflat",
    ),
)
def test_first_execution_exception_stops_and_writes_noncanonical_failure(
    monkeypatch,
    tmp_path,
    message,
):
    prepare_top_level_run(monkeypatch, tmp_path, suffix=message)
    calls = []

    def fail(*, day, on_replay_start, **kwargs):
        calls.append(day)
        first = q._day_plan(day)[0]
        on_replay_start(*first)
        raise RuntimeError(message)

    monkeypatch.setattr(q, "run_qualification_day_from_disk", fail)
    with pytest.raises(RuntimeError, match=message):
        q.run_real_engine_qualification(
            authorization_token=q.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )
    assert calls == [DAY_JAN]
    failure = json.loads(q.FAILURE_RESULT_PATH.read_text(encoding="utf-8"))
    assert failure["completed_qualification_replay_count"] == 0
    assert (
        failure["current_day"],
        failure["current_policy"],
        failure["current_scenario"],
    ) == q.QUALIFICATION_PLAN[0]
    assert failure["exception_type"] == "RuntimeError"
    assert failure["exception_message"] == message
    assert failure["canonical_economic_attempt"] is False
    assert failure["canonical_attempt_consumed"] is False
    assert failure["economic_arena_called"] is False
    assert failure["economic_conclusion"] == "UNAVAILABLE"
    assert failure["automatic_retry"] is False


def test_result_surface_is_isolated_and_overwrite_refused(monkeypatch, tmp_path):
    assert str(q.RESULT_ROOT).endswith(
        "dev045_d6r20_q1_real_engine_qualification_v1"
    )
    assert "d6r17" not in str(q.RESULT_ROOT).lower()
    assert "d6r18" not in str(q.RESULT_ROOT).lower()
    assert "d6r19" not in str(q.RESULT_ROOT).lower()
    root = configure_result_surface(monkeypatch, tmp_path, suffix="overwrite")
    root.mkdir()
    q.SUCCESS_RESULT_PATH.write_text("{}\n", encoding="utf-8")
    with pytest.raises(q.QualificationError, match="qualification_result_exists"):
        q._require_virgin_result_surface()
    with pytest.raises(q.QualificationError, match="result_exists"):
        q._write_json_new(q.SUCCESS_RESULT_PATH, {})


def test_no_arena_or_ranking_call_surface_and_no_cycle_inspection():
    source = Path(q.__file__).read_text(encoding="utf-8")
    assert not hasattr(q, "run_economic_arena")
    assert not hasattr(q, "rank_candidates")
    assert "run_" + "economic_arena" not in source
    assert "replay." + "cycles" not in source
    assert "candidate_" + "ranking" not in source


def test_d6r20_driver_blob_exact_and_harness_does_not_implement_canonical():
    assert q._git_blob(Path(d6r20.__file__)) == (
        "1cae4584788aab29b409bf985168803759d42b1f"
    )
    assert q.CANONICAL_RUNNER_IMPLEMENTED is False
    assert q.CANONICAL_ECONOMIC_ATTEMPT is False

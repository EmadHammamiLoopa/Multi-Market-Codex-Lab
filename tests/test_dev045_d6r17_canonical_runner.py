from __future__ import annotations

from dataclasses import replace

import pytest

from multimarket import (
    dev045_d6r17_canonical_runner as r,
)
from multimarket import (
    dev045_d6r17_canonical_runner_contract as c,
)
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_economic_arena as m6


def test_default_execution_state_closed():
    assert (
        r.CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT
        is False
    )

    assert r.AUTOMATIC_RETRY is False
    assert r.RERUN_AFTER_ATTEMPT_CONSUMPTION is False
    assert r.TUNING_AFTER_FIRST_OUTPUT is False

    assert r.NETWORK_ACQUISITION_ENABLED is False
    assert r.RAILWAY_ENABLED is False
    assert r.LIVE_TRADING_AUTHORIZED is False

    assert r.AUG_OPEN_AUTHORIZED is False
    assert r.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r.NON_BTC_OPEN_AUTHORIZED is False


def test_authorization_requires_explicit_gate(monkeypatch):
    monkeypatch.setenv(
        c.AUTHORIZATION_ENV,
        c.AUTHORIZATION_TOKEN,
    )

    with pytest.raises(
        r.CanonicalRunnerError,
        match="execution_gate_closed",
    ):
        r._require_authorization(
            authorization_token=c.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )


def test_authorization_requires_exact_token(monkeypatch):
    monkeypatch.setenv(
        c.AUTHORIZATION_ENV,
        c.AUTHORIZATION_TOKEN,
    )

    with pytest.raises(
        r.CanonicalRunnerError,
        match="authorization_token",
    ):
        r._require_authorization(
            authorization_token="WRONG",
            execution_gate=True,
        )


def test_authorization_requires_environment(monkeypatch):
    monkeypatch.delenv(
        c.AUTHORIZATION_ENV,
        raising=False,
    )

    with pytest.raises(
        r.CanonicalRunnerError,
        match="authorization_environment",
    ):
        r._require_authorization(
            authorization_token=c.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )


def test_authorization_all_three_pass(monkeypatch):
    monkeypatch.setenv(
        c.AUTHORIZATION_ENV,
        c.AUTHORIZATION_TOKEN,
    )

    r._require_authorization(
        authorization_token=c.AUTHORIZATION_TOKEN,
        execution_gate=True,
    )


def test_open_guard_fails_before_filesystem(monkeypatch):
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError(
            "file opener must not run"
        )

    monkeypatch.setattr(
        r.adapter,
        "_open_verified_file",
        forbidden,
    )

    with pytest.raises(
        r.CanonicalRunnerError,
        match="execution_gate_closed",
    ):
        r.open_verified_day_source(
            day="2026-01-01",
            authorization_token=c.AUTHORIZATION_TOKEN,
            execution_gate=False,
        )

    assert called is False


def test_day_specs_are_exact():
    for day in c.DAY_ORDER:
        spec = r._spec_for_day(
            day
        )

        assert spec.day == day
        assert spec.path.suffix == ".npy"
        assert spec.rows > 0
        assert spec.bytes > 0
        assert len(spec.sha256) == 64


def test_base_days_load_no_support(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError(
            "support file must not open"
        )

    monkeypatch.setattr(
        r.support,
        "load_verified_day",
        forbidden,
    )

    for day in c.BASE_ONLY_DAYS:
        assert (
            r.load_frozen_day_support(
                day=day
            )
            == {}
        )


def test_direct_days_load_exact_two(monkeypatch):
    calls = []

    class FakeIndex:
        pass

    def fake_load(*, day, policy_id):
        calls.append(
            (
                day,
                policy_id,
            )
        )

        return FakeIndex()

    monkeypatch.setattr(
        r.support,
        "load_verified_day",
        fake_load,
    )

    x = r.load_frozen_day_support(
        day="2026-04-01"
    )

    assert set(x) == {
        "M06",
        "M07",
    }

    assert calls == [
        (
            "2026-04-01",
            "M06",
        ),
        (
            "2026-04-01",
            "M07",
        ),
    ]


def _flat_cycle_fills():
    return (
        m6.FillRecord(
            policy_id="M01",
            day="2026-01-01",
            timestamp_ns=(
                1767225601
                * 1_000_000_000
            ),
            side="BUY",
            qty=0.001,
            price=100_000.0,
            liquidity="MAKER",
        ),
        m6.FillRecord(
            policy_id="M01",
            day="2026-01-01",
            timestamp_ns=(
                1767225602
                * 1_000_000_000
            ),
            side="SELL",
            qty=0.001,
            price=100_010.0,
            liquidity="MAKER",
        ),
    )


def test_extract_fill_records_keeps_only_fill_events():
    fills = _flat_cycle_fills()

    e1 = binding.BoundReplayEvent(
        kind=binding.FILL,
        policy_id="M01",
        day="2026-01-01",
        order_id=1,
        timestamp_ns=fills[0].timestamp_ns,
        side="BUY",
        liquidity="MAKER",
        exec_qty=fills[0].qty,
        exec_price_tick=1_000_000,
        executed_quote_notional=100.0,
        fill=fills[0],
    )

    e2 = replace(
        e1,
        kind=binding.NO_FILL,
        order_id=2,
        fill=None,
        exec_qty=0.0,
        executed_quote_notional=0.0,
    )

    assert r.extract_fill_records(
        (e1, e2)
    ) == (
        fills[0],
    )


def test_reaccount_parity_passes():
    fills = _flat_cycle_fills()

    cycles = tuple(
        m6.account_fill_bucket(
            fills,
            scenario=(
                "Q0_PRIMARY_250_250"
            ),
        )
    )

    out = r.verify_reaccount_parity(
        policy_id="M01",
        day="2026-01-01",
        scenario="Q0_PRIMARY_250_250",
        replay_total_fill_count=2,
        replay_cycles=cycles,
        fills=fills,
    )

    assert out == cycles
    assert len(out) == 1


def test_reaccount_fill_count_fails_closed():
    fills = _flat_cycle_fills()

    with pytest.raises(
        r.CanonicalRunnerError,
        match="raw_fill_count_parity",
    ):
        r.verify_reaccount_parity(
            policy_id="M01",
            day="2026-01-01",
            scenario="Q0_PRIMARY_250_250",
            replay_total_fill_count=3,
            replay_cycles=(),
            fills=fills,
        )


def test_reaccount_cycle_mismatch_fails_closed():
    fills = _flat_cycle_fills()

    with pytest.raises(
        r.CanonicalRunnerError,
        match="reaccount_cycle_parity",
    ):
        r.verify_reaccount_parity(
            policy_id="M01",
            day="2026-01-01",
            scenario="Q0_PRIMARY_250_250",
            replay_total_fill_count=2,
            replay_cycles=(),
            fills=fills,
        )


def test_day_evidence_paths_are_frozen():
    p = r.day_evidence_path(
        "2026-04-01"
    )

    assert (
        p.name
        == "2026-04-01_DEV045_D6R17_DAY_RESULT.json"
    )

    assert p.parent == r.RESULT_ROOT


def test_final_entrypoint_not_called_by_import():
    assert (
        r.FINAL_RESULT_PATH.parent
        == r.RESULT_ROOT
    )

    assert (
        r.FAILURE_RESULT_PATH.parent
        == r.RESULT_ROOT
    )


def test_contract_identity():
    c.validate_contract()

    assert r.PARENT_HEAD == (
        "7c86bd5f240ef0533cbcb13526e9553888989d37"
    )

    assert c.EXPECTED_TOTAL_REPLAYS == 112
    assert c.EXPECTED_REPLAYS_PER_DAY == 16
    assert c.M6_FINAL_CALL_ONLY_AFTER_112
    assert c.RAW_FILL_CAPTURE_REQUIRED
    assert c.REACCOUNT_PARITY_REQUIRED


def test_june_source_identity_amendment_is_exact():
    assert (
        r.D6R16_SOURCE_IDENTITY_WITNESS_HEAD
        == "5411877e3bd1f8fcd9812176bc3dc39dbf18bf88"
    )

    assert (
        r.PARENT_JUNE_SHA256_DEFECTIVE
        == (
            "ac97ad27c9d58b3b3e249547b8ae7c74"
            "cf2ebfde07965103bd5f6c7b853c26b"
        )
    )

    assert len(
        r.PARENT_JUNE_SHA256_DEFECTIVE
    ) == 63

    assert (
        r.JUNE_SOURCE_SHA256
        == (
            "ac97ad27c9d58b3b3e249547b8ae7c74"
            "cf2ebfde07965103bd9c8c05d0df1160"
        )
    )

    assert len(
        r.JUNE_SOURCE_SHA256
    ) == 64

    frozen_parent = next(
        x
        for x in r.parent.DAY_SPECS
        if x.day == "2026-06-01"
    )

    assert (
        frozen_parent.sha256
        == r.PARENT_JUNE_SHA256_DEFECTIVE
    )

    amended = r._spec_for_day(
        "2026-06-01"
    )

    assert (
        amended.sha256
        == r.JUNE_SOURCE_SHA256
    )

    # Non-June source identities remain untouched.
    for day in (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-07-01",
    ):
        amended_spec = r._spec_for_day(
            day
        )

        parent_spec = next(
            x
            for x in r.parent.DAY_SPECS
            if x.day == day
        )

        assert (
            amended_spec
            == parent_spec
        )

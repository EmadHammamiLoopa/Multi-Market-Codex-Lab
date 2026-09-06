from __future__ import annotations

import json

import pytest

from multimarket import (
    dev045_d6r17_attempt_consumption_amendment as a,
)
from multimarket import (
    dev045_d6r17_canonical_runner_contract as c,
)


class FakeSource:
    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False


def authorize(monkeypatch):
    monkeypatch.setenv(
        c.AUTHORIZATION_ENV,
        c.AUTHORIZATION_TOKEN,
    )


def test_boundary_contract():
    assert (
        a.PRE_REPLAY_SOURCE_SHA_FAILURE_CONSUMES
        is False
    )

    assert (
        a.PRE_REPLAY_SOURCE_OPEN_FAILURE_CONSUMES
        is False
    )

    assert (
        a.PRE_REPLAY_SUPPORT_FAILURE_CONSUMES
        is False
    )

    assert (
        a.PRE_REPLAY_VALIDATION_FAILURE_CONSUMES
        is False
    )

    assert (
        a.FIRST_HISTORICAL_REPLAY_ENTRY_CONSUMES
        is True
    )

    assert a.AUTOMATIC_RETRY is False

    assert (
        a.CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT
        is False
    )


def test_support_failure_before_replay_not_consumed(
    monkeypatch,
    tmp_path,
):
    authorize(monkeypatch)

    final = tmp_path / "final.json"
    failure = tmp_path / "failure.json"

    monkeypatch.setattr(
        a,
        "FINAL_RESULT_PATH",
        final,
    )

    monkeypatch.setattr(
        a,
        "FAILURE_RESULT_PATH",
        failure,
    )

    monkeypatch.setattr(
        a,
        "RESULT_ROOT",
        tmp_path,
    )

    def fail_support(*, day):
        raise RuntimeError(
            "support_preflight_failure"
        )

    monkeypatch.setattr(
        a.frozen,
        "load_frozen_day_support",
        fail_support,
    )

    with pytest.raises(
        RuntimeError,
        match="support_preflight_failure",
    ):
        a.run_full_canonical_arena(
            authorization_token=c.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert not failure.exists()
    assert not final.exists()


def test_source_open_failure_before_replay_not_consumed(
    monkeypatch,
    tmp_path,
):
    authorize(monkeypatch)

    final = tmp_path / "final.json"
    failure = tmp_path / "failure.json"

    monkeypatch.setattr(
        a,
        "FINAL_RESULT_PATH",
        final,
    )

    monkeypatch.setattr(
        a,
        "FAILURE_RESULT_PATH",
        failure,
    )

    monkeypatch.setattr(
        a,
        "RESULT_ROOT",
        tmp_path,
    )

    monkeypatch.setattr(
        a.frozen,
        "load_frozen_day_support",
        lambda *, day: {},
    )

    def fail_open(**kwargs):
        raise RuntimeError(
            "source_sha_or_open_failure"
        )

    monkeypatch.setattr(
        a.frozen,
        "open_verified_day_source",
        fail_open,
    )

    with pytest.raises(
        RuntimeError,
        match="source_sha_or_open_failure",
    ):
        a.run_full_canonical_arena(
            authorization_token=c.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert not failure.exists()
    assert not final.exists()


def test_first_replay_entry_consumes_attempt(
    monkeypatch,
    tmp_path,
):
    authorize(monkeypatch)

    final = tmp_path / "final.json"
    failure = tmp_path / "failure.json"

    monkeypatch.setattr(
        a,
        "FINAL_RESULT_PATH",
        final,
    )

    monkeypatch.setattr(
        a,
        "FAILURE_RESULT_PATH",
        failure,
    )

    monkeypatch.setattr(
        a,
        "RESULT_ROOT",
        tmp_path,
    )

    monkeypatch.setattr(
        a.frozen,
        "load_frozen_day_support",
        lambda *, day: {},
    )

    monkeypatch.setattr(
        a.frozen,
        "open_verified_day_source",
        lambda **kwargs: FakeSource(),
    )

    def enter_replay_then_fail(
        source,
        *,
        day,
        direct_by_policy,
        authorization_token,
        execution_gate,
        mark_attempt_started,
    ):
        mark_attempt_started()

        raise RuntimeError(
            "first_historical_replay_failure"
        )

    monkeypatch.setattr(
        a,
        "run_verified_day_matrix_with_boundary",
        enter_replay_then_fail,
    )

    with pytest.raises(
        RuntimeError,
        match="first_historical_replay_failure",
    ):
        a.run_full_canonical_arena(
            authorization_token=c.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert failure.is_file()
    assert not final.exists()

    payload = json.loads(
        failure.read_text(
            encoding="utf-8"
        )
    )

    assert payload[
        "attempt_consumed"
    ] is True

    assert payload[
        "completed_days"
    ] == []

    assert payload[
        "completed_replays"
    ] == 0

    assert payload[
        "automatic_retry"
    ] is False

    assert payload[
        "attempt_boundary"
    ] == a.BOUNDARY_SEMANTIC


def test_authorization_failure_never_consumes(
    monkeypatch,
    tmp_path,
):
    monkeypatch.delenv(
        c.AUTHORIZATION_ENV,
        raising=False,
    )

    failure = tmp_path / "failure.json"

    monkeypatch.setattr(
        a,
        "FAILURE_RESULT_PATH",
        failure,
    )

    with pytest.raises(Exception):
        a.run_full_canonical_arena(
            authorization_token=c.AUTHORIZATION_TOKEN,
            execution_gate=True,
        )

    assert not failure.exists()

from __future__ import annotations

import os

import pytest

from multimarket import dev045_d6r26a_p2_r27p24_july_worst_case_full_day_file_backed_rss_preexecution as r


def test_contract_and_worst_case_scope_closed() -> None:
    r.validate_r27p24_contract()
    assert r.SOURCE_DAY == "2026-07-01"
    assert r.SOURCE_ROWS == 181_084_390
    assert r.SOURCE_BYTES == 11_589_401_216
    assert r.BYTES_PER_EVENT == 265
    assert r.EXPECTED_RAW_FILE_BYTES == 181_084_390 * 265
    assert max(r.FROZEN_JAN_JUL_ROWS) == r.SOURCE_ROWS
    assert max(r.FROZEN_JAN_JUL_BYTES) == r.SOURCE_BYTES
    assert r.MAX_PEAK_RSS_GIB == 12.0
    assert r.MIN_MEM_AVAILABLE_START_BYTES == 12 * 1024**3
    assert r.SYSTEM_MEM_ABORT_BYTES == 8 * 1024**3
    assert r.WATCHDOG_POLL_SECONDS == 0.25
    assert r.JULY_ONLY is True
    assert r.WORST_CASE_JAN_JUL_SOURCE is True
    assert r.FULL_DAY_CANDIDATE_ONLY is True
    assert r.REFERENCE_RERUN_AUTHORIZED is False
    assert r.NEW_REAL_PARITY_CLAIM is False
    assert r.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r.SIMULATOR_LANE_AUTHORIZED is False
    assert r.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r.P2_ATTEMPT_CONSUMED is False


def test_real_execution_requires_exact_authorization() -> None:
    assert r._authorized({}) is False
    assert r._authorized({r.AUTH_ENV: "WRONG"}) is False
    assert r._authorized({r.AUTH_ENV: r.AUTH_TOKEN}) is True
    assert r._worker_authorized({r.AUTH_ENV: r.AUTH_TOKEN}) is False
    assert r._worker_authorized({r.AUTH_ENV: r.AUTH_TOKEN, r.WORKER_ENV: r.WORKER_TOKEN}) is True


def test_ci_without_token_cannot_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(r.AUTH_ENV, raising=False)
    monkeypatch.delenv(r.WORKER_ENV, raising=False)
    with pytest.raises(r.R27P24Error, match="authorization"):
        r.run_july_full_day_supervised(env=os.environ)


def test_worker_cannot_be_invoked_directly_without_both_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(r.AUTH_ENV, r.AUTH_TOKEN)
    monkeypatch.delenv(r.WORKER_ENV, raising=False)
    with pytest.raises(r.R27P24Error, match="worker_authorization"):
        r._worker_probe()


def test_readiness_remains_closed_before_real_run() -> None:
    assert r.R27P23_JAN_FULL_DAY_RSS_PASS_INHERITED is True
    assert r.JAN_FULL_DAY_BOUNDED_MEMORY_PROVEN is True
    assert r.GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN is False
    assert r.CANONICAL_EXECUTION_READY is False
    assert r.READINESS_BLOCKER == "WORST_CASE_JUL_FULL_DAY_RSS_PROOF_NOT_YET_EXECUTED"
    assert r.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r.AUG_OPEN_AUTHORIZED is False
    assert r.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r.NON_BTC_OPEN_AUTHORIZED is False
    assert r.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False


def test_disk_gate_scales_with_july_file_backing() -> None:
    assert r.EXPECTED_RAW_FILE_BYTES == 47_987_363_350
    assert r.MIN_FREE_DISK_BYTES == r.EXPECTED_RAW_FILE_BYTES + 16 * 1024**3
    assert r.MIN_FREE_DISK_BYTES > 60 * 1024**3

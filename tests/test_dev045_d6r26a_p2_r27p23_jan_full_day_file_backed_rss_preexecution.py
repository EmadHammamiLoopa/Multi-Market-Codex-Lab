from __future__ import annotations

import os

import pytest

from multimarket import dev045_d6r26a_p2_r27p23_jan_full_day_file_backed_rss_preexecution as r


def test_contract_and_scope_closed() -> None:
    r.validate_r27p23_contract()
    assert r.FULL_DAY_ROWS == 64_314_723
    assert r.BYTES_PER_EVENT == 265
    assert r.EXPECTED_RAW_FILE_BYTES == 64_314_723 * 265
    assert r.MIN_FREE_DISK_GIB == 24.0
    assert r.MAX_PEAK_RSS_GIB == 12.0
    assert r.EXTERNAL_RSS_KILL_GIB == 12.0
    assert r.JANUARY_ONLY is True
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


def test_ci_without_token_cannot_execute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(r.AUTH_ENV, raising=False)
    with pytest.raises(r.R27P23Error, match="authorization"):
        r.run_jan_full_day_rss_probe(environ=os.environ)


def test_readiness_remains_closed_before_real_run() -> None:
    assert r.FULL_DAY_BOUNDED_MEMORY_PROVEN is False
    assert r.CANONICAL_EXECUTION_READY is False
    assert r.READINESS_BLOCKER == "JAN_FULL_DAY_RSS_PROOF_NOT_YET_EXECUTED"
    assert r.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r.AUG_OPEN_AUTHORIZED is False
    assert r.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r.NON_BTC_OPEN_AUTHORIZED is False
    assert r.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False

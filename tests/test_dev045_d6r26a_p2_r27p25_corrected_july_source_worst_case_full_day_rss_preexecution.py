from __future__ import annotations

from pathlib import Path
import os

import pytest

from multimarket import dev045_d6r26a_p2_r27p24_july_worst_case_full_day_file_backed_rss_preexecution as r24
from multimarket import dev045_d6r26a_p2_r27p25_corrected_july_source_worst_case_full_day_rss_preexecution as r


def test_contract_corrects_only_source_and_successor_identity() -> None:
    r.validate_r27p25_contract()
    assert r.EXPERIMENT_ID == "DEV045-D6R26A-P2-R27P25"
    assert r.PARENT_R27P24_INVALID_HEAD == "f86134bc067477f0f4cee686af09e0d6e51845b7"
    assert r.R27P24_INVALID_CLASSIFICATION == "INVALID_ENGINEERING_PRECONDITION_SOURCE_PATH"
    assert r.R27P24_RERUN_AUTHORIZED is False
    assert r.R27P24_SCIENTIFIC_MEMORY_RESULT_AVAILABLE is False
    assert r.SOURCE_PATH == Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy")
    assert r.SOURCE_PATH != r24.SOURCE_PATH
    assert r.SOURCE_DAY == r24.SOURCE_DAY == "2026-07-01"
    assert r.SOURCE_ROWS == r24.SOURCE_ROWS == 181_084_390
    assert r.SOURCE_BYTES == r24.SOURCE_BYTES == 11_589_401_216
    assert r.SOURCE_SHA256 == r24.SOURCE_SHA256
    assert r.SOURCE_DAY_END_EXCLUSIVE_NS - r.SOURCE_DAY_START_NS == 86_400_000_000_000


def test_scientific_thresholds_are_identical_to_r27p24() -> None:
    assert r.MAX_PEAK_RSS_BYTES == r24.MAX_PEAK_RSS_BYTES == 12 * 1024**3
    assert r.MAX_PEAK_RSS_GIB == 12.0
    assert r.MIN_MEM_AVAILABLE_START_BYTES == r24.MIN_MEM_AVAILABLE_START_BYTES == 12 * 1024**3
    assert r.SYSTEM_MEM_ABORT_BYTES == r24.SYSTEM_MEM_ABORT_BYTES == 8 * 1024**3
    assert r.WATCHDOG_POLL_SECONDS == r24.WATCHDOG_POLL_SECONDS == 0.25
    assert r.EXPECTED_RAW_FILE_BYTES == r24.EXPECTED_RAW_FILE_BYTES == 47_987_363_350
    assert r.DISK_HEADROOM_BYTES == r24.DISK_HEADROOM_BYTES == 16 * 1024**3
    assert r.MIN_FREE_DISK_BYTES == r.EXPECTED_RAW_FILE_BYTES + r.DISK_HEADROOM_BYTES


def test_new_scratch_cannot_reuse_r27p24_residue() -> None:
    assert r.SCRATCH_ROOT != r24.SCRATCH_ROOT
    assert str(r.SCRATCH_ROOT).endswith("dev045_d6r26a_p2_r27p25_jul_full_day_rss")
    assert r.PREEXISTING_R27P24_SCRATCH_REUSE_AUTHORIZED is False
    assert r.PREEXISTING_SCRATCH_REUSE_AUTHORIZED is False
    assert r.PREEXISTING_SCRATCH_AUTO_DELETE_AUTHORIZED is False


def test_real_execution_requires_exact_authorization() -> None:
    assert r._authorized({}) is False
    assert r._authorized({r.AUTH_ENV: "WRONG"}) is False
    assert r._authorized({r.AUTH_ENV: r.AUTH_TOKEN}) is True
    assert r._worker_authorized({r.AUTH_ENV: r.AUTH_TOKEN}) is False
    assert r._worker_authorized({r.AUTH_ENV: r.AUTH_TOKEN, r.WORKER_ENV: r.WORKER_TOKEN}) is True


def test_ci_without_token_cannot_touch_real_source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(r.AUTH_ENV, raising=False)
    monkeypatch.delenv(r.WORKER_ENV, raising=False)
    touched = {"source": False}

    def forbidden() -> None:
        touched["source"] = True
        raise AssertionError("real source touched")

    monkeypatch.setattr(r, "_validate_corrected_source_preflight", forbidden)
    with pytest.raises(r.R27P25Error, match="authorization"):
        r.run_july_full_day_supervised(env=os.environ)
    assert touched["source"] is False


def test_worker_cannot_be_directly_invoked_without_worker_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(r.AUTH_ENV, r.AUTH_TOKEN)
    monkeypatch.delenv(r.WORKER_ENV, raising=False)
    with pytest.raises(r.R27P25Error, match="worker_authorization"):
        r._worker_probe()


def test_execution_surfaces_remain_closed() -> None:
    assert r.REFERENCE_RERUN_AUTHORIZED is False
    assert r.NEW_REAL_PARITY_CLAIM is False
    assert r.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r.SIMULATOR_LANE_AUTHORIZED is False
    assert r.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r.MODEL_FIT_AUTHORIZED is False
    assert r.PNL_AUTHORIZED is False
    assert r.AUG_OPEN_AUTHORIZED is False
    assert r.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r.NON_BTC_OPEN_AUTHORIZED is False
    assert r.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False
    assert r.P2_ATTEMPT_CONSUMED is False
    assert r.GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN is False
    assert r.CANONICAL_EXECUTION_READY is False


def test_memory_watchdog_failure_has_distinct_scientific_class() -> None:
    assert issubclass(r.R27P25ScientificMemoryFail, r.R27P25Error)
    assert r.R27P25ScientificMemoryFail is not r.R27P25Error

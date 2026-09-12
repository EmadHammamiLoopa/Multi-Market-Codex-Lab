from __future__ import annotations

import inspect

import pytest

from multimarket import dev045_d6r26a_p2_r27p18_corrected_5m_speed_benchmark_preexecution as r27p18
from multimarket import dev045_d6r26a_p2_r27p22_real_5m_file_backed_rss_preexecution as r27p22


def test_contract_freezes_scope_and_memory_gate() -> None:
    r27p22.validate_r27p22_contract()
    assert r27p22.PARENT_R27P21_HEAD == "b4209d6a65e16d2039ff8a89e354a46cac81e340"
    assert r27p22.PREFIX_ROWS == 5_000_000
    assert r27p22.MAX_PEAK_RSS_BYTES == 12 * 1024**3
    assert r27p22.MAX_PEAK_RSS_GIB == 12.0
    assert r27p22.RSS_METRIC == "TOTAL_PROCESS_PEAK_RSS"
    assert r27p22.RSS_PLATFORM == "LINUX_RUSAGE_MAXRSS_KIB"
    assert r27p22.CANDIDATE_ONLY_RSS_PROBE is True
    assert r27p22.REFERENCE_RERUN_AUTHORIZED is False
    assert r27p22.NEW_REAL_PARITY_CLAIM is False
    assert r27p22.FULL_DAY_BOUNDED_MEMORY_PROVEN is False
    assert r27p22.CANONICAL_EXECUTION_READY is False
    assert r27p22.P2_ATTEMPT_CONSUMED is False


def test_source_identity_is_exact_r27p18_january_source() -> None:
    assert r27p22.SOURCE_DAY == r27p18.SOURCE_DAY == "2026-01-01"
    assert r27p22.SOURCE_PATH == r27p18.SOURCE_PATH
    assert r27p22.SOURCE_ROWS == r27p18.SOURCE_ROWS == 64_314_723
    assert r27p22.SOURCE_BYTES == r27p18.SOURCE_BYTES == 4_116_142_528
    assert r27p22.SOURCE_SHA256 == r27p18.SOURCE_SHA256 == "8f0a4fbd56ecdc261dbe2041ce138a09456423074925d495272716219a1d4da1"
    assert r27p22.R27P18_REAL_5M_EXACT_PARITY_INHERITED is True
    assert r27p22.R27P21_SYNTHETIC_REWRITE_EXACT_PARITY_INHERITED is True


def test_real_probe_requires_explicit_authorization_before_source_access(monkeypatch) -> None:
    touched = {"source": False}

    def forbidden_source_open():
        touched["source"] = True
        raise AssertionError("source access must not occur without authorization")

    monkeypatch.setattr(r27p22.r27p2, "_verify_source_identity", forbidden_source_open)
    with pytest.raises(r27p22.R27P22Error, match="authorization"):
        r27p22.run_real_5m_rss_probe(environ={})
    assert touched["source"] is False


def test_real_probe_has_no_reference_rerun_or_persistent_write_surface() -> None:
    source = inspect.getsource(r27p22.run_real_5m_rss_probe)
    assert "benchmark_loaded_prefix" not in source
    assert "run_real_benchmark" not in source
    assert "build_once_day_context" not in source
    assert "OUTPUT_MANIFEST" not in source
    assert r27p22.BENCHMARK_MANIFEST_WRITE_AUTHORIZED is False
    assert r27p22.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r27p22.FULL_DAY_CONTEXT_BUILD_AUTHORIZED is False
    assert r27p22.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r27p22.SIMULATOR_LANE_AUTHORIZED is False
    assert r27p22.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r27p22.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r27p22.MODEL_FIT_AUTHORIZED is False
    assert r27p22.PNL_AUTHORIZED is False
    assert r27p22.AUG_OPEN_AUTHORIZED is False
    assert r27p22.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r27p22.NON_BTC_OPEN_AUTHORIZED is False
    assert r27p22.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False

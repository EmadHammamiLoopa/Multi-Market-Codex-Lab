from pathlib import Path

from multimarket import dev045_d6r26a_p2_r27p27_thin_worker_rss_preexecution as r


def test_r27p27_contract_is_frozen_and_parent_is_scientific_fail():
    r.validate_r27p27_contract()
    assert r.EXPERIMENT_ID == "DEV045-D6R26A-P2-R27P27"
    assert r.PARENT_R27P26_RESULT_HEAD == "4aeacf59ad296456410215ac52f9ee9184fa0a87"
    assert r.PARENT_R27P26_CLASSIFICATION == "SCIENTIFIC_MEMORY_FAIL"
    assert r.PARENT_R27P26_PEAK_RSS_BYTES == 12_887_650_304
    assert r.PARENT_R27P26_EXCESS_BYTES == 2_748_416
    assert r.R27P26_RERUN_AUTHORIZED is False


def test_thresholds_are_identical_to_r27p26_contract():
    assert r.MAX_PEAK_RSS_BYTES == 12 * 1024**3
    assert r.MIN_MEM_AVAILABLE_START_BYTES == 12 * 1024**3
    assert r.SYSTEM_MEM_ABORT_BYTES == 8 * 1024**3
    assert r.WATCHDOG_POLL_SECONDS == 0.25
    assert r.EXPECTED_RAW_FILE_BYTES == 47_987_363_350
    assert r.DISK_HEADROOM_BYTES == 16 * 1024**3


def test_source_identity_and_new_scratch_are_exact():
    assert r.SOURCE_PATH == Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy")
    assert r.SOURCE_ROWS == 181_084_390
    assert r.SOURCE_BYTES == 11_589_401_216
    assert r.SOURCE_SHA256 == "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f"
    assert r.SCRATCH_ROOT == Path("/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p27_jul_full_day_rss")


def test_durable_supervisor_paths_are_inside_new_scratch():
    assert r.SUPERVISOR_TELEMETRY == r.SCRATCH_ROOT / "supervisor_telemetry.json"
    assert r.SUPERVISOR_OUTCOME == r.SCRATCH_ROOT / "supervisor_outcome.json"
    assert r.WORKER_RESULT == r.SCRATCH_ROOT / "worker_result.json"


def test_atomic_json_roundtrip(tmp_path):
    p = tmp_path / "x.json"
    r._atomic_json(p, {"classification": "TEST", "peak": 123})
    text = p.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert '"peak": 123' in text
    assert not p.with_name(p.name + ".tmp").exists()


def test_execution_surfaces_remain_closed():
    assert r.REFERENCE_RERUN_AUTHORIZED is False
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


def test_without_authorization_supervisor_is_closed():
    assert r._authorized({}) is False


def test_thin_worker_does_not_import_failed_supervisors_and_uses_heap_trim():
    root = Path(__file__).resolve().parents[1]
    worker = root / "src/multimarket/dev045_d6r26a_p2_r27p27_thin_worker.py"
    text = worker.read_text(encoding="utf-8")
    assert "dev045_d6r26a_p2_r27p25" not in text
    assert "dev045_d6r26a_p2_r27p26" not in text
    assert "malloc_trim" in text
    assert "gc.collect()" in text
    assert "build_corrected_fused_day_context" in text
    assert "build_file_backed_raw_kernel" in text
    assert "P2_ATTEMPT_CONSUMED" not in text or "p2_attempt_consumed" in text

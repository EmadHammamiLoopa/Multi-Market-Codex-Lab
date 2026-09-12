from pathlib import Path

from multimarket import dev045_d6r26a_p2_r27p26_durable_supervisor_telemetry_preexecution as r


def test_r27p26_contract():
    r.validate_r27p26_contract()
    assert r.EXPERIMENT_ID == "DEV045-D6R26A-P2-R27P26"
    assert r.PARENT_R27P25_INVALID_HEAD == "abcf7e2a3f68f7552723eb05682ed10020508af1"
    assert r.R27P25_INVALID_CLASSIFICATION == "INVALID_RESULT_NOT_DURABLY_CAPTURED"
    assert r.R27P25_RERUN_AUTHORIZED is False
    assert r.R27P25_SCIENTIFIC_RESULT_AVAILABLE is False


def test_thresholds_unchanged_from_r27p25():
    assert r.MAX_PEAK_RSS_BYTES == 12 * 1024**3
    assert r.MIN_MEM_AVAILABLE_START_BYTES == 12 * 1024**3
    assert r.SYSTEM_MEM_ABORT_BYTES == 8 * 1024**3
    assert r.WATCHDOG_POLL_SECONDS == 0.25


def test_corrected_july_source_and_new_scratch():
    assert r.SOURCE_PATH == Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy")
    assert r.SOURCE_ROWS == 181_084_390
    assert r.SOURCE_BYTES == 11_589_401_216
    assert r.SOURCE_SHA256 == "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f"
    assert r.SCRATCH_ROOT == Path("/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p26_jul_full_day_rss")


def test_durable_supervisor_paths_are_inside_new_scratch():
    assert r.SUPERVISOR_TELEMETRY == r.SCRATCH_ROOT / "supervisor_telemetry.json"
    assert r.SUPERVISOR_OUTCOME == r.SCRATCH_ROOT / "supervisor_outcome.json"
    assert r.WORKER_RESULT == r.SCRATCH_ROOT / "worker_result.json"


def test_atomic_json_roundtrip(tmp_path):
    path = tmp_path / "telemetry.json"
    r._atomic_json(path, {"a": 1, "state": "RUNNING"})
    assert path.read_text(encoding="utf-8").endswith("\n")
    assert '"a": 1' in path.read_text(encoding="utf-8")
    assert not path.with_name(path.name + ".tmp").exists()


def test_telemetry_contains_peak_and_trip_reason():
    p = r._telemetry_payload(
        pid=123,
        poll_count=7,
        peak_worker=13 * 1024**3,
        min_mem=9 * 1024**3,
        current_worker=13 * 1024**3,
        current_mem=9 * 1024**3,
        state="TRIP_RECORDED_BEFORE_TERMINATE",
        trip_reason="worker_rss_above_12_gib",
    )
    assert p["worker_pid"] == 123
    assert p["poll_count"] == 7
    assert p["peak_worker_rss_bytes"] == 13 * 1024**3
    assert p["minimum_system_mem_available_bytes"] == 9 * 1024**3
    assert p["state"] == "TRIP_RECORDED_BEFORE_TERMINATE"
    assert p["trip_reason"] == "worker_rss_above_12_gib"
    assert p["p2_attempt_consumed"] is False


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


def test_without_authorization_real_execution_is_blocked():
    assert r._authorized({}) is False
    assert r._worker_authorized({}) is False

from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import time

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P27"
DESIGN_VERSION = "thin-isolated-worker-rss-preexecution-v1"
PARENT_R27P26_RESULT_HEAD = "4aeacf59ad296456410215ac52f9ee9184fa0a87"
PARENT_R27P26_CLASSIFICATION = "SCIENTIFIC_MEMORY_FAIL"
PARENT_R27P26_PEAK_RSS_BYTES = 12_887_650_304
PARENT_R27P26_EXCESS_BYTES = 2_748_416
R27P26_RERUN_AUTHORIZED = False

AUTH_ENV = "DEV045_D6R26A_P2_R27P27_AUTHORIZE"
AUTH_TOKEN = "YES_FROZEN_JUL_THIN_WORKER_RSS_PROOF_PREATTEMPT"
WORKER_ENV = "DEV045_D6R26A_P2_R27P27_WORKER"
WORKER_TOKEN = "INTERNAL_SUPERVISED_WORKER_ONLY"

SOURCE_DAY = "2026-07-01"
SOURCE_PATH = Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy")
SOURCE_ROWS = 181_084_390
SOURCE_BYTES = 11_589_401_216
SOURCE_SHA256 = "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f"

BYTES_PER_EVENT = 265
EXPECTED_RAW_FILE_BYTES = 47_987_363_350
DISK_HEADROOM_BYTES = 16 * 1024**3
MIN_FREE_DISK_BYTES = EXPECTED_RAW_FILE_BYTES + DISK_HEADROOM_BYTES
MAX_PEAK_RSS_BYTES = 12 * 1024**3
MAX_PEAK_RSS_GIB = 12.0
MIN_MEM_AVAILABLE_START_BYTES = 12 * 1024**3
SYSTEM_MEM_ABORT_BYTES = 8 * 1024**3
WATCHDOG_POLL_SECONDS = 0.25

SCRATCH_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p27_jul_full_day_rss")
WORKER_RESULT = SCRATCH_ROOT / "worker_result.json"
WORKER_STDOUT = SCRATCH_ROOT / "worker.stdout.log"
WORKER_STDERR = SCRATCH_ROOT / "worker.stderr.log"
SUPERVISOR_TELEMETRY = SCRATCH_ROOT / "supervisor_telemetry.json"
SUPERVISOR_OUTCOME = SCRATCH_ROOT / "supervisor_outcome.json"

REFERENCE_RERUN_AUTHORIZED = False
DURABLE_CONTEXT_WRITE_AUTHORIZED = False
FULL_JAN_JUL_RERUN_AUTHORIZED = False
SIMULATOR_LANE_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED = False
P2_ATTEMPT_CONSUMED = False

GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN = False
CANONICAL_EXECUTION_READY = False
READINESS_BLOCKER = "THIN_WORKER_JUL_WORST_CASE_RSS_PROOF_NOT_YET_EXECUTED"


class R27P27Error(RuntimeError):
    pass


class R27P27ScientificMemoryFail(R27P27Error):
    pass


def _authorized(env: dict[str, str] | None = None) -> bool:
    current = os.environ if env is None else env
    return current.get(AUTH_ENV) == AUTH_TOKEN


def _atomic_json(path: Path, payload: dict) -> None:
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def _mem_available_bytes() -> int:
    with Path("/proc/meminfo").open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    raise R27P27Error("memavailable_unavailable")


def _process_rss_bytes(pid: int) -> int:
    path = Path(f"/proc/{pid}/status")
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    return 0


def _validate_source_preflight() -> None:
    if not SOURCE_PATH.is_file():
        raise R27P27Error("source_missing")
    if int(SOURCE_PATH.stat().st_size) != SOURCE_BYTES:
        raise R27P27Error("source_bytes")


def validate_r27p27_contract() -> None:
    if PARENT_R27P26_RESULT_HEAD != "4aeacf59ad296456410215ac52f9ee9184fa0a87":
        raise R27P27Error("parent_result_head")
    if PARENT_R27P26_CLASSIFICATION != "SCIENTIFIC_MEMORY_FAIL":
        raise R27P27Error("parent_classification")
    if PARENT_R27P26_PEAK_RSS_BYTES != 12_887_650_304 or PARENT_R27P26_EXCESS_BYTES != 2_748_416:
        raise R27P27Error("parent_observation")
    if R27P26_RERUN_AUTHORIZED:
        raise R27P27Error("parent_rerun")
    if SOURCE_PATH != Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy"):
        raise R27P27Error("source_path")
    if SOURCE_ROWS != 181_084_390 or SOURCE_BYTES != 11_589_401_216:
        raise R27P27Error("source_scope")
    if SOURCE_SHA256 != "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f":
        raise R27P27Error("source_sha")
    if BYTES_PER_EVENT != 265 or EXPECTED_RAW_FILE_BYTES != 47_987_363_350:
        raise R27P27Error("raw_capacity")
    if MAX_PEAK_RSS_BYTES != 12 * 1024**3:
        raise R27P27Error("rss_threshold_changed")
    if MIN_MEM_AVAILABLE_START_BYTES != 12 * 1024**3:
        raise R27P27Error("start_threshold_changed")
    if SYSTEM_MEM_ABORT_BYTES != 8 * 1024**3:
        raise R27P27Error("abort_threshold_changed")
    if WATCHDOG_POLL_SECONDS != 0.25:
        raise R27P27Error("poll_changed")
    if SCRATCH_ROOT == Path("/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p26_jul_full_day_rss"):
        raise R27P27Error("scratch_reuse")
    if any((
        REFERENCE_RERUN_AUTHORIZED,
        DURABLE_CONTEXT_WRITE_AUTHORIZED,
        FULL_JAN_JUL_RERUN_AUTHORIZED,
        SIMULATOR_LANE_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED,
        P2_ATTEMPT_CONSUMED,
    )):
        raise R27P27Error("execution_surface_open")


def _telemetry_payload(*, pid: int, poll_count: int, peak_worker: int, min_mem: int, current_worker: int, current_mem: int, state: str, trip_reason: str | None) -> dict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "unix_time_ns": time.time_ns(),
        "worker_pid": pid,
        "poll_count": poll_count,
        "state": state,
        "current_worker_rss_bytes": current_worker,
        "current_worker_rss_gib": current_worker / 1024**3,
        "peak_worker_rss_bytes": peak_worker,
        "peak_worker_rss_gib": peak_worker / 1024**3,
        "current_system_mem_available_bytes": current_mem,
        "current_system_mem_available_gib": current_mem / 1024**3,
        "minimum_system_mem_available_bytes": min_mem,
        "minimum_system_mem_available_gib": min_mem / 1024**3,
        "worker_rss_ceiling_bytes": MAX_PEAK_RSS_BYTES,
        "system_mem_abort_bytes": SYSTEM_MEM_ABORT_BYTES,
        "trip_reason": trip_reason,
        "p2_attempt_consumed": False,
    }


def _write_outcome(payload: dict) -> None:
    out = dict(payload)
    out["experiment_id"] = EXPERIMENT_ID
    out["design_version"] = DESIGN_VERSION
    out["unix_time_ns"] = time.time_ns()
    out["p2_attempt_consumed"] = False
    _atomic_json(SUPERVISOR_OUTCOME, out)


def run_july_full_day_supervised(env: dict[str, str] | None = None) -> dict:
    validate_r27p27_contract()
    current = os.environ if env is None else env
    if not _authorized(current):
        raise R27P27Error("authorization")
    if SCRATCH_ROOT.exists():
        raise R27P27Error("scratch_root_preexists_preserve_for_forensics")
    _validate_source_preflight()
    SCRATCH_ROOT.parent.mkdir(parents=True, exist_ok=True)
    free_disk = int(shutil.disk_usage(SCRATCH_ROOT.parent).free)
    if free_disk < MIN_FREE_DISK_BYTES:
        raise R27P27Error(f"insufficient_free_disk:{free_disk}")
    start_mem = _mem_available_bytes()
    if start_mem < MIN_MEM_AVAILABLE_START_BYTES:
        raise R27P27Error(f"insufficient_memavailable_start:{start_mem}")
    SCRATCH_ROOT.mkdir(parents=False, exist_ok=False)

    child_env = dict(os.environ)
    child_env.update(dict(current))
    child_env[AUTH_ENV] = AUTH_TOKEN
    child_env[WORKER_ENV] = WORKER_TOKEN
    cmd = [sys.executable, "-m", "multimarket.dev045_d6r26a_p2_r27p27_thin_worker"]

    peak_worker = 0
    min_mem = start_mem
    poll_count = 0
    trip_reason = None
    with WORKER_STDOUT.open("x", encoding="utf-8") as out, WORKER_STDERR.open("x", encoding="utf-8") as err:
        proc = subprocess.Popen(cmd, env=child_env, stdout=out, stderr=err, text=True)
        _atomic_json(SUPERVISOR_TELEMETRY, _telemetry_payload(
            pid=proc.pid, poll_count=0, peak_worker=0, min_mem=start_mem,
            current_worker=0, current_mem=start_mem, state="WORKER_STARTED", trip_reason=None,
        ))
        while proc.poll() is None:
            poll_count += 1
            worker_rss = _process_rss_bytes(proc.pid)
            mem_available = _mem_available_bytes()
            peak_worker = max(peak_worker, worker_rss)
            min_mem = min(min_mem, mem_available)
            if worker_rss > MAX_PEAK_RSS_BYTES:
                trip_reason = f"worker_rss_above_12_gib:{worker_rss}"
            elif mem_available < SYSTEM_MEM_ABORT_BYTES:
                trip_reason = f"system_memavailable_below_8_gib:{mem_available}"
            state = "TRIP_RECORDED_BEFORE_TERMINATE" if trip_reason else "RUNNING"
            _atomic_json(SUPERVISOR_TELEMETRY, _telemetry_payload(
                pid=proc.pid, poll_count=poll_count, peak_worker=peak_worker, min_mem=min_mem,
                current_worker=worker_rss, current_mem=mem_available, state=state, trip_reason=trip_reason,
            ))
            if trip_reason is not None:
                proc.terminate()
                break
            time.sleep(WATCHDOG_POLL_SECONDS)
        if trip_reason is not None:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        else:
            proc.wait()

    if trip_reason is not None:
        _write_outcome({
            "classification": "SCIENTIFIC_MEMORY_FAIL",
            "return_code": 3,
            "trip_reason": trip_reason,
            "worker_return_code": proc.returncode,
            "supervisor_peak_worker_rss_bytes": peak_worker,
            "minimum_system_mem_available_bytes": min_mem,
            "poll_count": poll_count,
        })
        raise R27P27ScientificMemoryFail(trip_reason)

    if proc.returncode != 0:
        _write_outcome({
            "classification": "INVALID_OR_ENGINEERING_ERROR",
            "return_code": 2,
            "trip_reason": None,
            "worker_return_code": proc.returncode,
            "supervisor_peak_worker_rss_bytes": peak_worker,
            "minimum_system_mem_available_bytes": min_mem,
            "poll_count": poll_count,
        })
        raise R27P27Error(f"worker_exit:{proc.returncode}")

    if not WORKER_RESULT.is_file():
        _write_outcome({
            "classification": "INVALID_OR_ENGINEERING_ERROR",
            "return_code": 2,
            "trip_reason": None,
            "worker_return_code": proc.returncode,
            "supervisor_peak_worker_rss_bytes": peak_worker,
            "minimum_system_mem_available_bytes": min_mem,
            "poll_count": poll_count,
            "reason": "worker_result_missing",
        })
        raise R27P27Error("worker_result_missing")

    worker = json.loads(WORKER_RESULT.read_text(encoding="utf-8"))
    internal_peak = int(worker["internal_peak_rss_bytes"])
    rss_gate = bool(internal_peak <= MAX_PEAK_RSS_BYTES and peak_worker <= MAX_PEAK_RSS_BYTES)
    system_gate = bool(min_mem >= SYSTEM_MEM_ABORT_BYTES)
    classification = "PASS_JUL_WORST_CASE_FULL_DAY_RSS_GATE" if rss_gate and system_gate else "SCIENTIFIC_MEMORY_FAIL"
    return_code = 0 if rss_gate and system_gate else 3
    _write_outcome({
        "classification": classification,
        "return_code": return_code,
        "trip_reason": None,
        "worker_return_code": proc.returncode,
        "supervisor_peak_worker_rss_bytes": peak_worker,
        "worker_internal_peak_rss_bytes": internal_peak,
        "minimum_system_mem_available_bytes": min_mem,
        "poll_count": poll_count,
        "heap_trim": worker.get("heap_trim"),
    })
    result = {
        "worker": worker,
        "supervisor_peak_worker_rss_bytes": peak_worker,
        "minimum_system_mem_available_bytes": min_mem,
        "rss_gate_pass": rss_gate,
        "system_memory_gate_pass": system_gate,
    }
    if not rss_gate or not system_gate:
        raise R27P27ScientificMemoryFail("completed_gate_fail")
    return result


def main() -> int:
    try:
        result = run_july_full_day_supervised()
    except R27P27ScientificMemoryFail as exc:
        print(f"R27P27_RESULT=SCIENTIFIC_MEMORY_FAIL REASON={exc}")
        print(f"R27P27_DURABLE_OUTCOME={SUPERVISOR_OUTCOME}")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 3
    except Exception as exc:
        print(f"R27P27_RESULT=INVALID_OR_ENGINEERING_ERROR TYPE={type(exc).__name__} REASON={exc}")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 2
    print(f"R27P27_SUPERVISOR_PEAK_WORKER_RSS_GIB={result['supervisor_peak_worker_rss_bytes'] / 1024**3:.6f}")
    print(f"R27P27_WORKER_INTERNAL_PEAK_RSS_GIB={result['worker']['internal_peak_rss_gib']:.6f}")
    print("R27P27_RESULT=PASS_JUL_WORST_CASE_FULL_DAY_RSS_GATE")
    print(f"R27P27_DURABLE_OUTCOME={SUPERVISOR_OUTCOME}")
    print("P2_ATTEMPT_CONSUMED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

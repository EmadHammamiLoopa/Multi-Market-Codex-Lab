from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p9_cpython313_float_sum_parity_amendment as r27p9
from multimarket import dev045_d6r26a_p2_r27p18_corrected_5m_speed_benchmark_preexecution as r27p18
from multimarket import dev045_d6r26a_p2_r27p21_file_backed_fused_raw_kernel_synthetic_parity as r27p21
from multimarket import dev045_d6r26a_p2_r27p25_corrected_july_source_worst_case_full_day_rss_preexecution as r27p25

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P26"
DESIGN_VERSION = "durable-supervisor-telemetry-preexecution-v1"
PARENT_R27P25_INVALID_HEAD = "abcf7e2a3f68f7552723eb05682ed10020508af1"
R27P25_INVALID_CLASSIFICATION = "INVALID_RESULT_NOT_DURABLY_CAPTURED"
R27P25_RERUN_AUTHORIZED = False
R27P25_SCIENTIFIC_RESULT_AVAILABLE = False

AUTH_ENV = "DEV045_D6R26A_P2_R27P26_AUTHORIZE"
AUTH_TOKEN = "YES_FROZEN_JUL_WORST_CASE_RSS_WITH_DURABLE_SUPERVISOR_TELEMETRY_PREATTEMPT"
WORKER_ENV = "DEV045_D6R26A_P2_R27P26_WORKER"
WORKER_TOKEN = "INTERNAL_SUPERVISED_WORKER_ONLY"

SOURCE_DAY = r27p25.SOURCE_DAY
SOURCE_PATH = r27p25.SOURCE_PATH
SOURCE_ROWS = r27p25.SOURCE_ROWS
SOURCE_BYTES = r27p25.SOURCE_BYTES
SOURCE_SHA256 = r27p25.SOURCE_SHA256
SOURCE_DAY_START_NS = r27p25.SOURCE_DAY_START_NS
SOURCE_DAY_END_EXCLUSIVE_NS = r27p25.SOURCE_DAY_END_EXCLUSIVE_NS

BYTES_PER_EVENT = r27p25.BYTES_PER_EVENT
EXPECTED_RAW_FILE_BYTES = r27p25.EXPECTED_RAW_FILE_BYTES
DISK_HEADROOM_BYTES = r27p25.DISK_HEADROOM_BYTES
MIN_FREE_DISK_BYTES = r27p25.MIN_FREE_DISK_BYTES
MAX_PEAK_RSS_BYTES = r27p25.MAX_PEAK_RSS_BYTES
MAX_PEAK_RSS_GIB = r27p25.MAX_PEAK_RSS_GIB
MIN_MEM_AVAILABLE_START_BYTES = r27p25.MIN_MEM_AVAILABLE_START_BYTES
SYSTEM_MEM_ABORT_BYTES = r27p25.SYSTEM_MEM_ABORT_BYTES
WATCHDOG_POLL_SECONDS = r27p25.WATCHDOG_POLL_SECONDS

SCRATCH_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p26_jul_full_day_rss")
WORKER_ROOT = SCRATCH_ROOT / "worker"
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
READINESS_BLOCKER = "DURABLE_JUL_WORST_CASE_RSS_RESULT_NOT_YET_EXECUTED"


class R27P26Error(RuntimeError):
    pass


class R27P26ScientificMemoryFail(R27P26Error):
    pass


def _authorized(env: dict[str, str] | None = None) -> bool:
    current = os.environ if env is None else env
    return current.get(AUTH_ENV) == AUTH_TOKEN


def _worker_authorized(env: dict[str, str] | None = None) -> bool:
    current = os.environ if env is None else env
    return _authorized(current) and current.get(WORKER_ENV) == WORKER_TOKEN


def _atomic_json(path: Path, payload: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


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


def _validate_source_preflight() -> None:
    if not SOURCE_PATH.is_file():
        raise R27P26Error("source_missing")
    if int(SOURCE_PATH.stat().st_size) != SOURCE_BYTES:
        raise R27P26Error("source_bytes")


def _verify_source_identity() -> np.memmap:
    _validate_source_preflight()
    if r27p2._sha256(SOURCE_PATH) != SOURCE_SHA256:
        raise R27P26Error("source_sha256")
    events = np.load(SOURCE_PATH, mmap_mode="r", allow_pickle=False)
    if not isinstance(events, np.memmap) or bool(events.flags.writeable):
        raise R27P26Error("source_memmap_contract")
    if int(events.size) != SOURCE_ROWS:
        raise R27P26Error("source_rows")
    return events


def validate_r27p26_contract() -> None:
    r27p25.validate_r27p25_contract()
    if PARENT_R27P25_INVALID_HEAD != "abcf7e2a3f68f7552723eb05682ed10020508af1":
        raise R27P26Error("parent")
    if R27P25_INVALID_CLASSIFICATION != "INVALID_RESULT_NOT_DURABLY_CAPTURED":
        raise R27P26Error("parent_classification")
    if R27P25_RERUN_AUTHORIZED or R27P25_SCIENTIFIC_RESULT_AVAILABLE:
        raise R27P26Error("parent_governance")
    if SOURCE_PATH != Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy"):
        raise R27P26Error("source_path")
    if MAX_PEAK_RSS_BYTES != 12 * 1024**3 or MAX_PEAK_RSS_BYTES != r27p25.MAX_PEAK_RSS_BYTES:
        raise R27P26Error("rss_threshold_changed")
    if MIN_MEM_AVAILABLE_START_BYTES != 12 * 1024**3 or MIN_MEM_AVAILABLE_START_BYTES != r27p25.MIN_MEM_AVAILABLE_START_BYTES:
        raise R27P26Error("start_threshold_changed")
    if SYSTEM_MEM_ABORT_BYTES != 8 * 1024**3 or SYSTEM_MEM_ABORT_BYTES != r27p25.SYSTEM_MEM_ABORT_BYTES:
        raise R27P26Error("abort_threshold_changed")
    if WATCHDOG_POLL_SECONDS != 0.25 or WATCHDOG_POLL_SECONDS != r27p25.WATCHDOG_POLL_SECONDS:
        raise R27P26Error("poll_interval_changed")
    if SCRATCH_ROOT == r27p25.SCRATCH_ROOT:
        raise R27P26Error("scratch_reuse")
    if SUPERVISOR_TELEMETRY.parent != SCRATCH_ROOT or SUPERVISOR_OUTCOME.parent != SCRATCH_ROOT:
        raise R27P26Error("durable_paths")
    if any((REFERENCE_RERUN_AUTHORIZED, DURABLE_CONTEXT_WRITE_AUTHORIZED, FULL_JAN_JUL_RERUN_AUTHORIZED, SIMULATOR_LANE_AUTHORIZED, ATTEMPT_MARKER_WRITE_AUTHORIZED, CANONICAL_LABEL_WRITE_AUTHORIZED, MODEL_FIT_AUTHORIZED, PNL_AUTHORIZED, AUG_OPEN_AUTHORIZED, SEP_PLUS_OPEN_AUTHORIZED, NON_BTC_OPEN_AUTHORIZED, MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED, P2_ATTEMPT_CONSUMED)):
        raise R27P26Error("execution_surface_open")


def _worker_probe() -> dict:
    validate_r27p26_contract()
    if not _worker_authorized():
        raise R27P26Error("worker_authorization")
    r27p2._validate_preattempt_state()
    events = _verify_source_identity()
    context = None
    holder = []
    try:
        WORKER_ROOT.mkdir(parents=False, exist_ok=False)
        adapter, holder = r27p21.make_r27p6_signature_adapter(
            WORKER_ROOT / "raw_buffers",
            kernel=r27p21.build_file_backed_raw_kernel(),
        )
        context, l5_changed, vol_changed = r27p18.build_corrected_fused_day_context(
            events,
            nominal_day_start_local_ns=SOURCE_DAY_START_NS,
            nominal_day_end_exclusive_local_ns=SOURCE_DAY_END_EXCLUSIVE_NS,
            scratch_root=WORKER_ROOT / "context",
            raw_kernel=adapter,
            base_feature_kernel=r27p5.build_feature_kernel(),
            l5_amendment_kernel=r27p9.build_l5_obi_amendment_kernel(),
        )
        digest = r27p0.digest_day_context(context)
        peak = r27p25._peak_rss_bytes()
        return {
            "experiment_id": EXPERIMENT_ID,
            "design_version": DESIGN_VERSION,
            "source_day": SOURCE_DAY,
            "source_path": str(SOURCE_PATH),
            "rows": SOURCE_ROWS,
            "source_bytes": SOURCE_BYTES,
            "source_sha256": SOURCE_SHA256,
            "internal_peak_rss_bytes": peak,
            "internal_peak_rss_gib": peak / 1024**3,
            "candidate_digest": asdict(digest),
            "l5_changed_cells": int(l5_changed),
            "volatility_changed_cells": int(vol_changed),
            "p2_attempt_consumed": False,
        }
    finally:
        if context is not None and not context.midpoint_index.closed:
            r20.close_midpoint_index(context.midpoint_index)
        r27p21.close_adapter_runs(holder)
        r27p18._close_source_memmap(events)


def _worker_main() -> int:
    try:
        result = _worker_probe()
        _atomic_json(WORKER_RESULT, result)
        print("R27P26_WORKER_RESULT=PASS")
        return 0
    except Exception as exc:
        print(f"R27P26_WORKER_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        return 2


def _write_outcome(payload: dict) -> None:
    payload = dict(payload)
    payload["experiment_id"] = EXPERIMENT_ID
    payload["design_version"] = DESIGN_VERSION
    payload["unix_time_ns"] = time.time_ns()
    payload["p2_attempt_consumed"] = False
    _atomic_json(SUPERVISOR_OUTCOME, payload)


def run_july_full_day_supervised(env: dict[str, str] | None = None) -> dict:
    validate_r27p26_contract()
    current = os.environ if env is None else env
    if not _authorized(current):
        raise R27P26Error("authorization")
    r27p2._validate_preattempt_state()
    if SCRATCH_ROOT.exists():
        raise R27P26Error("scratch_root_preexists_preserve_for_forensics")
    _validate_source_preflight()
    SCRATCH_ROOT.parent.mkdir(parents=True, exist_ok=True)
    free_disk = int(shutil.disk_usage(SCRATCH_ROOT.parent).free)
    if free_disk < MIN_FREE_DISK_BYTES:
        raise R27P26Error(f"insufficient_free_disk:{free_disk}")
    start_mem = r27p25._mem_available_bytes()
    if start_mem < MIN_MEM_AVAILABLE_START_BYTES:
        raise R27P26Error(f"insufficient_memavailable_start:{start_mem}")
    SCRATCH_ROOT.mkdir(parents=False, exist_ok=False)

    child_env = dict(os.environ)
    child_env.update(dict(current))
    child_env[AUTH_ENV] = AUTH_TOKEN
    child_env[WORKER_ENV] = WORKER_TOKEN
    cmd = [sys.executable, "-m", "multimarket.dev045_d6r26a_p2_r27p26_durable_supervisor_telemetry_preexecution", "--worker"]

    peak_worker = 0
    min_mem = start_mem
    poll_count = 0
    trip_reason = None
    with WORKER_STDOUT.open("x", encoding="utf-8") as out, WORKER_STDERR.open("x", encoding="utf-8") as err:
        proc = subprocess.Popen(cmd, env=child_env, stdout=out, stderr=err, text=True)
        _atomic_json(SUPERVISOR_TELEMETRY, _telemetry_payload(pid=proc.pid, poll_count=0, peak_worker=0, min_mem=start_mem, current_worker=0, current_mem=start_mem, state="WORKER_STARTED", trip_reason=None))
        while proc.poll() is None:
            poll_count += 1
            worker_rss = r27p25._process_rss_bytes(proc.pid)
            mem_available = r27p25._mem_available_bytes()
            peak_worker = max(peak_worker, worker_rss)
            min_mem = min(min_mem, mem_available)
            if worker_rss > MAX_PEAK_RSS_BYTES:
                trip_reason = f"worker_rss_above_12_gib:{worker_rss}"
            elif mem_available < SYSTEM_MEM_ABORT_BYTES:
                trip_reason = f"system_memavailable_below_8_gib:{mem_available}"
            state = "TRIP_RECORDED_BEFORE_TERMINATE" if trip_reason else "RUNNING"
            _atomic_json(SUPERVISOR_TELEMETRY, _telemetry_payload(pid=proc.pid, poll_count=poll_count, peak_worker=peak_worker, min_mem=min_mem, current_worker=worker_rss, current_mem=mem_available, state=state, trip_reason=trip_reason))
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
        outcome = {"classification": "SCIENTIFIC_MEMORY_FAIL", "return_code": 3, "trip_reason": trip_reason, "worker_return_code": proc.returncode, "supervisor_peak_worker_rss_bytes": peak_worker, "minimum_system_mem_available_bytes": min_mem, "poll_count": poll_count}
        _write_outcome(outcome)
        raise R27P26ScientificMemoryFail(trip_reason)

    if proc.returncode != 0:
        outcome = {"classification": "INVALID_OR_ENGINEERING_ERROR", "return_code": 2, "trip_reason": None, "worker_return_code": proc.returncode, "supervisor_peak_worker_rss_bytes": peak_worker, "minimum_system_mem_available_bytes": min_mem, "poll_count": poll_count}
        _write_outcome(outcome)
        raise R27P26Error(f"worker_exit:{proc.returncode}")
    if not WORKER_RESULT.is_file():
        outcome = {"classification": "INVALID_OR_ENGINEERING_ERROR", "return_code": 2, "trip_reason": None, "worker_return_code": proc.returncode, "supervisor_peak_worker_rss_bytes": peak_worker, "minimum_system_mem_available_bytes": min_mem, "poll_count": poll_count, "reason": "worker_result_missing"}
        _write_outcome(outcome)
        raise R27P26Error("worker_result_missing")

    worker = json.loads(WORKER_RESULT.read_text(encoding="utf-8"))
    rss_gate = int(worker["internal_peak_rss_bytes"]) <= MAX_PEAK_RSS_BYTES and peak_worker <= MAX_PEAK_RSS_BYTES
    system_gate = min_mem >= SYSTEM_MEM_ABORT_BYTES
    classification = "PASS_JUL_WORST_CASE_FULL_DAY_RSS_GATE" if rss_gate and system_gate else "SCIENTIFIC_MEMORY_FAIL"
    rc = 0 if classification.startswith("PASS") else 3
    outcome = {
        "classification": classification,
        "return_code": rc,
        "trip_reason": None,
        "worker_return_code": proc.returncode,
        "worker_internal_peak_rss_bytes": int(worker["internal_peak_rss_bytes"]),
        "supervisor_peak_worker_rss_bytes": peak_worker,
        "minimum_system_mem_available_bytes": min_mem,
        "poll_count": poll_count,
        "candidate_digest": worker.get("candidate_digest"),
        "l5_changed_cells": worker.get("l5_changed_cells"),
        "volatility_changed_cells": worker.get("volatility_changed_cells"),
    }
    _write_outcome(outcome)
    _atomic_json(SUPERVISOR_TELEMETRY, _telemetry_payload(pid=proc.pid, poll_count=poll_count, peak_worker=peak_worker, min_mem=min_mem, current_worker=0, current_mem=r27p25._mem_available_bytes(), state="COMPLETED_OUTCOME_DURABLE", trip_reason=None))
    if rc == 3:
        raise R27P26ScientificMemoryFail("completed_gate_fail")
    return outcome


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--worker":
        return _worker_main()
    try:
        outcome = run_july_full_day_supervised()
    except R27P26ScientificMemoryFail as exc:
        print(f"R27P26_RESULT=SCIENTIFIC_MEMORY_FAIL REASON={exc}")
        print(f"R27P26_DURABLE_OUTCOME={SUPERVISOR_OUTCOME}")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 3
    except Exception as exc:
        if SCRATCH_ROOT.exists() and not SUPERVISOR_OUTCOME.exists():
            _write_outcome({"classification": "INVALID_OR_ENGINEERING_ERROR", "return_code": 2, "reason": f"{type(exc).__name__}:{exc}"})
        print(f"R27P26_RESULT=INVALID_OR_ENGINEERING_ERROR TYPE={type(exc).__name__} REASON={exc}")
        print(f"R27P26_DURABLE_OUTCOME={SUPERVISOR_OUTCOME}")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 2
    print(f"R27P26_RESULT={outcome['classification']}")
    print(f"R27P26_DURABLE_OUTCOME={SUPERVISOR_OUTCOME}")
    print("P2_ATTEMPT_CONSUMED=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

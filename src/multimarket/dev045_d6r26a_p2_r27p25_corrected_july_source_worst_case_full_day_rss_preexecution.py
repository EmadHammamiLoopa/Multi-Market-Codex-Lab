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
from multimarket import dev045_d6r26a_p2_r27p24_july_worst_case_full_day_file_backed_rss_preexecution as r27p24

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P25"
DESIGN_VERSION = "corrected-july-source-worst-case-full-day-rss-preexecution-v1"
PARENT_R27P24_INVALID_HEAD = "f86134bc067477f0f4cee686af09e0d6e51845b7"
R27P24_INVALID_CLASSIFICATION = "INVALID_ENGINEERING_PRECONDITION_SOURCE_PATH"
R27P24_RERUN_AUTHORIZED = False
R27P24_SCIENTIFIC_MEMORY_RESULT_AVAILABLE = False

AUTH_ENV = "DEV045_D6R26A_P2_R27P25_AUTHORIZE"
AUTH_TOKEN = "YES_CORRECTED_FROZEN_JUL_WORST_CASE_FULL_DAY_FILE_BACKED_RSS_PROOF_PREATTEMPT"
WORKER_ENV = "DEV045_D6R26A_P2_R27P25_WORKER"
WORKER_TOKEN = "INTERNAL_SUPERVISED_WORKER_ONLY"

SOURCE_DAY = "2026-07-01"
SOURCE_PATH = Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy")
SOURCE_ROWS = 181_084_390
SOURCE_BYTES = 11_589_401_216
SOURCE_SHA256 = "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f"
SOURCE_DAY_START_NS = 1_782_864_000_000_000_000
SOURCE_DAY_END_EXCLUSIVE_NS = SOURCE_DAY_START_NS + 86_400_000_000_000

BYTES_PER_EVENT = 265
EXPECTED_RAW_FILE_BYTES = SOURCE_ROWS * BYTES_PER_EVENT
DISK_HEADROOM_BYTES = 16 * 1024**3
MIN_FREE_DISK_BYTES = EXPECTED_RAW_FILE_BYTES + DISK_HEADROOM_BYTES
MAX_PEAK_RSS_BYTES = 12 * 1024**3
MAX_PEAK_RSS_GIB = 12.0
MIN_MEM_AVAILABLE_START_BYTES = 12 * 1024**3
SYSTEM_MEM_ABORT_BYTES = 8 * 1024**3
WATCHDOG_POLL_SECONDS = 0.25

SCRATCH_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p25_jul_full_day_rss")
WORKER_ROOT = SCRATCH_ROOT / "worker"
WORKER_RESULT = SCRATCH_ROOT / "worker_result.json"
WORKER_STDOUT = SCRATCH_ROOT / "worker.stdout.log"
WORKER_STDERR = SCRATCH_ROOT / "worker.stderr.log"

REAL_HISTORICAL_FULL_DAY_OPEN_AUTHORIZED = True
REAL_HISTORICAL_FULL_DAY_REQUIRES_EXPLICIT_AUTHORIZATION = True
SOURCE_IDENTITY_REHASH_REQUIRED = True
CORRECTED_SOURCE_PATH_REQUIRED = True
ONE_FROZEN_SOURCE_ONLY = True
JULY_ONLY = True
WORST_CASE_JAN_JUL_SOURCE = True
FULL_DAY_CANDIDATE_ONLY = True
REFERENCE_RERUN_AUTHORIZED = False
NEW_REAL_PARITY_CLAIM = False
PREEXISTING_R27P24_SCRATCH_REUSE_AUTHORIZED = False
PREEXISTING_SCRATCH_REUSE_AUTHORIZED = False
PREEXISTING_SCRATCH_AUTO_DELETE_AUTHORIZED = False
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

R27P23_JAN_FULL_DAY_RSS_PASS_INHERITED = True
R27P23_JAN_FULL_DAY_PEAK_RSS_GIB = 5.951721
R27P24_INVALID_PRECONDITION_INHERITED = True
GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN = False
CANONICAL_EXECUTION_READY = False
READINESS_BLOCKER = "CORRECTED_JUL_SOURCE_WORST_CASE_RSS_PROOF_NOT_YET_EXECUTED"


class R27P25Error(RuntimeError):
    pass


class R27P25ScientificMemoryFail(R27P25Error):
    pass


def _authorized(env: dict[str, str] | None = None) -> bool:
    current = os.environ if env is None else env
    return current.get(AUTH_ENV) == AUTH_TOKEN


def _worker_authorized(env: dict[str, str] | None = None) -> bool:
    current = os.environ if env is None else env
    return _authorized(current) and current.get(WORKER_ENV) == WORKER_TOKEN


def _mem_available_bytes() -> int:
    return r27p24._mem_available_bytes()


def _process_rss_bytes(pid: int) -> int:
    return r27p24._process_rss_bytes(pid)


def _peak_rss_bytes() -> int:
    return r27p24._peak_rss_bytes()


def _validate_corrected_source_preflight() -> None:
    if not SOURCE_PATH.is_file():
        raise R27P25Error("corrected_source_missing")
    if int(SOURCE_PATH.stat().st_size) != SOURCE_BYTES:
        raise R27P25Error("corrected_source_bytes")


def _verify_source_identity() -> np.memmap:
    _validate_corrected_source_preflight()
    if r27p2._sha256(SOURCE_PATH) != SOURCE_SHA256:
        raise R27P25Error("source_sha256")
    events = np.load(SOURCE_PATH, mmap_mode="r", allow_pickle=False)
    if not isinstance(events, np.memmap):
        raise R27P25Error("source_not_memmap")
    if bool(events.flags.writeable):
        raise R27P25Error("source_writeable")
    if int(events.size) != SOURCE_ROWS:
        raise R27P25Error("source_rows")
    return events


def validate_r27p25_contract() -> None:
    r27p24.validate_r27p24_contract()
    if PARENT_R27P24_INVALID_HEAD != "f86134bc067477f0f4cee686af09e0d6e51845b7":
        raise R27P25Error("parent_invalid_head")
    if R27P24_INVALID_CLASSIFICATION != "INVALID_ENGINEERING_PRECONDITION_SOURCE_PATH":
        raise R27P25Error("parent_invalid_classification")
    if R27P24_RERUN_AUTHORIZED or R27P24_SCIENTIFIC_MEMORY_RESULT_AVAILABLE:
        raise R27P25Error("r27p24_governance")
    if SOURCE_PATH != Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy"):
        raise R27P25Error("corrected_source_path")
    if SOURCE_DAY != "2026-07-01" or SOURCE_ROWS != 181_084_390 or SOURCE_BYTES != 11_589_401_216:
        raise R27P25Error("source_scope")
    if SOURCE_SHA256 != "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f":
        raise R27P25Error("source_sha256_contract")
    if SOURCE_DAY_END_EXCLUSIVE_NS - SOURCE_DAY_START_NS != 86_400_000_000_000:
        raise R27P25Error("one_day_window")
    if EXPECTED_RAW_FILE_BYTES != 47_987_363_350:
        raise R27P25Error("raw_capacity")
    if DISK_HEADROOM_BYTES != 16 * 1024**3 or MIN_FREE_DISK_BYTES != EXPECTED_RAW_FILE_BYTES + DISK_HEADROOM_BYTES:
        raise R27P25Error("disk_gate")
    if MAX_PEAK_RSS_BYTES != r27p24.MAX_PEAK_RSS_BYTES or MAX_PEAK_RSS_BYTES != 12 * 1024**3:
        raise R27P25Error("rss_threshold_changed")
    if MIN_MEM_AVAILABLE_START_BYTES != r27p24.MIN_MEM_AVAILABLE_START_BYTES or MIN_MEM_AVAILABLE_START_BYTES != 12 * 1024**3:
        raise R27P25Error("start_memory_threshold_changed")
    if SYSTEM_MEM_ABORT_BYTES != r27p24.SYSTEM_MEM_ABORT_BYTES or SYSTEM_MEM_ABORT_BYTES != 8 * 1024**3:
        raise R27P25Error("abort_threshold_changed")
    if WATCHDOG_POLL_SECONDS != r27p24.WATCHDOG_POLL_SECONDS or WATCHDOG_POLL_SECONDS != 0.25:
        raise R27P25Error("watchdog_interval_changed")
    if SCRATCH_ROOT == r27p24.SCRATCH_ROOT:
        raise R27P25Error("scratch_reuse")

    required = (
        REAL_HISTORICAL_FULL_DAY_OPEN_AUTHORIZED,
        REAL_HISTORICAL_FULL_DAY_REQUIRES_EXPLICIT_AUTHORIZATION,
        SOURCE_IDENTITY_REHASH_REQUIRED,
        CORRECTED_SOURCE_PATH_REQUIRED,
        ONE_FROZEN_SOURCE_ONLY,
        JULY_ONLY,
        WORST_CASE_JAN_JUL_SOURCE,
        FULL_DAY_CANDIDATE_ONLY,
        R27P23_JAN_FULL_DAY_RSS_PASS_INHERITED,
        R27P24_INVALID_PRECONDITION_INHERITED,
        not REFERENCE_RERUN_AUTHORIZED,
        not NEW_REAL_PARITY_CLAIM,
        not PREEXISTING_R27P24_SCRATCH_REUSE_AUTHORIZED,
        not PREEXISTING_SCRATCH_REUSE_AUTHORIZED,
        not PREEXISTING_SCRATCH_AUTO_DELETE_AUTHORIZED,
        not DURABLE_CONTEXT_WRITE_AUTHORIZED,
        not GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not CANONICAL_EXECUTION_READY,
    )
    if not all(required):
        raise R27P25Error("required_guard")
    forbidden = (
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
    )
    if any(forbidden):
        raise R27P25Error("execution_surface_open")
    if READINESS_BLOCKER != "CORRECTED_JUL_SOURCE_WORST_CASE_RSS_PROOF_NOT_YET_EXECUTED":
        raise R27P25Error("readiness_blocker")


def _worker_probe() -> dict:
    validate_r27p25_contract()
    if not _worker_authorized():
        raise R27P25Error("worker_authorization")
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
        peak = _peak_rss_bytes()
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
            "expected_raw_file_bytes": EXPECTED_RAW_FILE_BYTES,
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
        temp = WORKER_RESULT.with_suffix(".json.tmp")
        with temp.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, WORKER_RESULT)
        print(f"R27P25_WORKER_INTERNAL_PEAK_RSS_GIB={result['internal_peak_rss_gib']:.6f}")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 0
    except Exception as exc:
        print(f"R27P25_WORKER_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 2


def run_july_full_day_supervised(env: dict[str, str] | None = None) -> dict:
    validate_r27p25_contract()
    current = os.environ if env is None else env
    if not _authorized(current):
        raise R27P25Error("authorization")
    r27p2._validate_preattempt_state()
    if SCRATCH_ROOT.exists():
        raise R27P25Error("scratch_root_preexists_preserve_for_forensics")
    _validate_corrected_source_preflight()
    SCRATCH_ROOT.parent.mkdir(parents=True, exist_ok=True)
    free_disk = int(shutil.disk_usage(SCRATCH_ROOT.parent).free)
    if free_disk < MIN_FREE_DISK_BYTES:
        raise R27P25Error(f"insufficient_free_disk:{free_disk}")
    start_mem = _mem_available_bytes()
    if start_mem < MIN_MEM_AVAILABLE_START_BYTES:
        raise R27P25Error(f"insufficient_memavailable_start:{start_mem}")
    SCRATCH_ROOT.mkdir(parents=False, exist_ok=False)

    child_env = dict(os.environ)
    child_env.update(dict(current))
    child_env[AUTH_ENV] = AUTH_TOKEN
    child_env[WORKER_ENV] = WORKER_TOKEN
    cmd = [
        sys.executable,
        "-m",
        "multimarket.dev045_d6r26a_p2_r27p25_corrected_july_source_worst_case_full_day_rss_preexecution",
        "--worker",
    ]

    peak_worker = 0
    min_mem = start_mem
    trip_reason = None
    with WORKER_STDOUT.open("x", encoding="utf-8") as out, WORKER_STDERR.open("x", encoding="utf-8") as err:
        proc = subprocess.Popen(cmd, env=child_env, stdout=out, stderr=err, text=True)
        while proc.poll() is None:
            worker_rss = _process_rss_bytes(proc.pid)
            mem_available = _mem_available_bytes()
            peak_worker = max(peak_worker, worker_rss)
            min_mem = min(min_mem, mem_available)
            if worker_rss > MAX_PEAK_RSS_BYTES:
                trip_reason = f"worker_rss_above_12_gib:{worker_rss}"
            elif mem_available < SYSTEM_MEM_ABORT_BYTES:
                trip_reason = f"system_memavailable_below_8_gib:{mem_available}"
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
        raise R27P25ScientificMemoryFail(trip_reason)
    if proc.returncode != 0:
        raise R27P25Error(f"worker_exit:{proc.returncode}")
    if not WORKER_RESULT.is_file():
        raise R27P25Error("worker_result_missing")

    worker = json.loads(WORKER_RESULT.read_text(encoding="utf-8"))
    rss_gate = bool(
        int(worker["internal_peak_rss_bytes"]) <= MAX_PEAK_RSS_BYTES
        and peak_worker <= MAX_PEAK_RSS_BYTES
    )
    system_gate = bool(min_mem >= SYSTEM_MEM_ABORT_BYTES)
    result = {
        "worker": worker,
        "supervisor_peak_worker_rss_bytes": peak_worker,
        "supervisor_peak_worker_rss_gib": peak_worker / 1024**3,
        "min_system_mem_available_bytes": min_mem,
        "min_system_mem_available_gib": min_mem / 1024**3,
        "rss_gate_pass": rss_gate,
        "system_memory_gate_pass": system_gate,
        "watchdog_tripped": False,
        "p2_attempt_consumed": False,
    }
    print(f"R27P25_SOURCE_IDENTITY=PASS DAY={SOURCE_DAY} ROWS={SOURCE_ROWS} BYTES={SOURCE_BYTES} SHA256={SOURCE_SHA256}")
    print(f"R27P25_SOURCE_PATH={SOURCE_PATH}")
    print(f"R27P25_EXPECTED_RAW_FILE_BYTES={EXPECTED_RAW_FILE_BYTES}")
    print(f"R27P25_MIN_FREE_DISK_BYTES={MIN_FREE_DISK_BYTES}")
    print(f"R27P25_PRE_RUN_DISK_FREE_BYTES={free_disk}")
    print(f"R27P25_PRE_RUN_MEM_AVAILABLE_GIB={start_mem / 1024**3:.6f}")
    print(f"R27P25_WORKER_INTERNAL_PEAK_RSS_GIB={worker['internal_peak_rss_gib']:.6f}")
    print(f"R27P25_SUPERVISOR_PEAK_WORKER_RSS_GIB={result['supervisor_peak_worker_rss_gib']:.6f}")
    print(f"R27P25_MIN_SYSTEM_MEM_AVAILABLE_GIB={result['min_system_mem_available_gib']:.6f}")
    print(f"R27P25_JUL_WORST_CASE_RSS_GATE={'PASS' if rss_gate else 'FAIL'}")
    print(f"R27P25_SYSTEM_MEMORY_GATE={'PASS' if system_gate else 'FAIL'}")
    print("R27P25_WATCHDOG_MONITORED_PID=PYTHON_WORKER_PID")
    print("R27P25_REFERENCE_RERUN=NO")
    print("R27P25_NEW_REAL_PARITY_CLAIM=NO")
    print("DURABLE_CONTEXT_WRITE=NO")
    print("SIMULATOR_RUN=NO")
    print("CANONICAL_LABEL_WRITE=NO")
    print("P2_ATTEMPT_CONSUMED=NO")
    return result


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "--worker":
        return _worker_main()
    try:
        result = run_july_full_day_supervised()
    except R27P25ScientificMemoryFail as exc:
        print(f"R27P25_RESULT=SCIENTIFIC_MEMORY_FAIL REASON={exc}")
        print("GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN=NO")
        print("CANONICAL_EXECUTION_READY=NO")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 3
    except Exception as exc:
        print(f"R27P25_RESULT=INVALID_OR_ENGINEERING_ERROR TYPE={type(exc).__name__} REASON={exc}")
        print("GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN=NO")
        print("CANONICAL_EXECUTION_READY=NO")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 2
    if not result["rss_gate_pass"] or not result["system_memory_gate_pass"]:
        print("R27P25_RESULT=SCIENTIFIC_MEMORY_FAIL COMPLETED_GATE_FAIL")
        return 3
    print("R27P25_RESULT=PASS_JUL_WORST_CASE_FULL_DAY_RSS_GATE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

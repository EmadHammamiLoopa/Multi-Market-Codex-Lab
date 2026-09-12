from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
import os
import resource
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
from multimarket import dev045_d6r26a_p2_r27p23_jan_full_day_file_backed_rss_preexecution as r27p23

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P24"
DESIGN_VERSION = "july-worst-case-full-day-file-backed-rss-preexecution-v1"
PARENT_R27P23_RESULT_HEAD = "138b7f91031f2548b1dbd486cbc4088911fd967b"

AUTH_ENV = "DEV045_D6R26A_P2_R27P24_AUTHORIZE"
AUTH_TOKEN = "YES_FROZEN_JUL_WORST_CASE_FULL_DAY_FILE_BACKED_RSS_PROOF_PREATTEMPT"
WORKER_ENV = "DEV045_D6R26A_P2_R27P24_WORKER"
WORKER_TOKEN = "INTERNAL_SUPERVISED_WORKER_ONLY"

SOURCE_DAY = "2026-07-01"
SOURCE_PATH = Path("/home/emadh/Multi-Market/runtime/dev045_d6r4b/output/BTCUSDT_2026-07-01.npy")
SOURCE_ROWS = 181_084_390
SOURCE_BYTES = 11_589_401_216
SOURCE_SHA256 = "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f"
SOURCE_DAY_START_NS = 1_782_864_000_000_000_000
SOURCE_DAY_END_EXCLUSIVE_NS = 1_785_542_400_000_000_000

FROZEN_JAN_JUL_ROWS = (
    64_314_723, 179_584_138, 150_979_263, 132_829_759,
    108_328_169, 172_540_697, 181_084_390,
)
FROZEN_JAN_JUL_BYTES = (
    4_116_142_528, 11_493_385_088, 9_662_673_088, 8_501_104_832,
    6_933_003_072, 11_042_604_864, 11_589_401_216,
)

BYTES_PER_EVENT = 265
EXPECTED_RAW_FILE_BYTES = SOURCE_ROWS * BYTES_PER_EVENT
DISK_HEADROOM_BYTES = 16 * 1024**3
MIN_FREE_DISK_BYTES = EXPECTED_RAW_FILE_BYTES + DISK_HEADROOM_BYTES
MAX_PEAK_RSS_BYTES = 12 * 1024**3
MAX_PEAK_RSS_GIB = 12.0
MIN_MEM_AVAILABLE_START_BYTES = 12 * 1024**3
SYSTEM_MEM_ABORT_BYTES = 8 * 1024**3
WATCHDOG_POLL_SECONDS = 0.25

SCRATCH_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p24_jul_full_day_rss")
WORKER_ROOT = SCRATCH_ROOT / "worker"
WORKER_RESULT = SCRATCH_ROOT / "worker_result.json"
WORKER_STDOUT = SCRATCH_ROOT / "worker.stdout.log"
WORKER_STDERR = SCRATCH_ROOT / "worker.stderr.log"

REAL_HISTORICAL_FULL_DAY_OPEN_AUTHORIZED = True
REAL_HISTORICAL_FULL_DAY_REQUIRES_EXPLICIT_AUTHORIZATION = True
SOURCE_IDENTITY_REHASH_REQUIRED = True
ONE_FROZEN_SOURCE_ONLY = True
JULY_ONLY = True
WORST_CASE_JAN_JUL_SOURCE = True
FULL_DAY_CANDIDATE_ONLY = True
REFERENCE_RERUN_AUTHORIZED = False
NEW_REAL_PARITY_CLAIM = False
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
JAN_FULL_DAY_BOUNDED_MEMORY_PROVEN = True
GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN = False
CANONICAL_EXECUTION_READY = False
READINESS_BLOCKER = "WORST_CASE_JUL_FULL_DAY_RSS_PROOF_NOT_YET_EXECUTED"


class R27P24Error(RuntimeError):
    pass


def _authorized(env: dict[str, str] | None = None) -> bool:
    current = os.environ if env is None else env
    return current.get(AUTH_ENV) == AUTH_TOKEN


def _worker_authorized(env: dict[str, str] | None = None) -> bool:
    current = os.environ if env is None else env
    return _authorized(current) and current.get(WORKER_ENV) == WORKER_TOKEN


def _peak_rss_bytes() -> int:
    kib = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if kib <= 0:
        raise R27P24Error("peak_rss_unavailable")
    return kib * 1024


def _mem_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise R27P24Error("memavailable_unavailable")


def _process_rss_bytes(pid: int) -> int:
    try:
        lines = Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return 0
    for line in lines:
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    return 0


def _verify_source_identity() -> np.memmap:
    if not SOURCE_PATH.is_file():
        raise R27P24Error("source_missing")
    if int(SOURCE_PATH.stat().st_size) != SOURCE_BYTES:
        raise R27P24Error("source_bytes")
    if r27p2._sha256(SOURCE_PATH) != SOURCE_SHA256:
        raise R27P24Error("source_sha256")
    events = np.load(SOURCE_PATH, mmap_mode="r", allow_pickle=False)
    if not isinstance(events, np.memmap):
        raise R27P24Error("source_not_memmap")
    if bool(events.flags.writeable):
        raise R27P24Error("source_writeable")
    if int(events.size) != SOURCE_ROWS:
        raise R27P24Error("source_rows")
    return events


def validate_r27p24_contract() -> None:
    r27p23.validate_r27p23_contract()
    if PARENT_R27P23_RESULT_HEAD != "138b7f91031f2548b1dbd486cbc4088911fd967b":
        raise R27P24Error("parent")
    if SOURCE_DAY != "2026-07-01" or SOURCE_ROWS != 181_084_390:
        raise R27P24Error("source_scope")
    if SOURCE_BYTES != 11_589_401_216 or SOURCE_SHA256 != "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f":
        raise R27P24Error("source_identity")
    if max(FROZEN_JAN_JUL_ROWS) != SOURCE_ROWS or max(FROZEN_JAN_JUL_BYTES) != SOURCE_BYTES:
        raise R27P24Error("worst_case_selection")
    if EXPECTED_RAW_FILE_BYTES != SOURCE_ROWS * 265:
        raise R27P24Error("raw_bytes")
    if MIN_FREE_DISK_BYTES != EXPECTED_RAW_FILE_BYTES + 16 * 1024**3:
        raise R27P24Error("disk_gate")
    if MAX_PEAK_RSS_BYTES != 12 * 1024**3:
        raise R27P24Error("rss_gate")
    if MIN_MEM_AVAILABLE_START_BYTES != 12 * 1024**3 or SYSTEM_MEM_ABORT_BYTES != 8 * 1024**3:
        raise R27P24Error("memory_guard")
    required = (
        REAL_HISTORICAL_FULL_DAY_OPEN_AUTHORIZED,
        REAL_HISTORICAL_FULL_DAY_REQUIRES_EXPLICIT_AUTHORIZATION,
        SOURCE_IDENTITY_REHASH_REQUIRED,
        ONE_FROZEN_SOURCE_ONLY,
        JULY_ONLY,
        WORST_CASE_JAN_JUL_SOURCE,
        FULL_DAY_CANDIDATE_ONLY,
        R27P23_JAN_FULL_DAY_RSS_PASS_INHERITED,
        JAN_FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not REFERENCE_RERUN_AUTHORIZED,
        not NEW_REAL_PARITY_CLAIM,
        not PREEXISTING_SCRATCH_REUSE_AUTHORIZED,
        not PREEXISTING_SCRATCH_AUTO_DELETE_AUTHORIZED,
        not DURABLE_CONTEXT_WRITE_AUTHORIZED,
        not GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not CANONICAL_EXECUTION_READY,
    )
    if not all(required):
        raise R27P24Error("required_guard")
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
        raise R27P24Error("execution_surface_open")
    if READINESS_BLOCKER != "WORST_CASE_JUL_FULL_DAY_RSS_PROOF_NOT_YET_EXECUTED":
        raise R27P24Error("readiness_blocker")


def _worker_probe() -> dict:
    validate_r27p24_contract()
    if not _worker_authorized():
        raise R27P24Error("worker_authorization")
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
            "rows": SOURCE_ROWS,
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
        print(f"R27P24_WORKER_INTERNAL_PEAK_RSS_GIB={result['internal_peak_rss_gib']:.6f}")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 0
    except Exception as exc:
        print(f"R27P24_WORKER_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 2


def run_july_full_day_supervised(env: dict[str, str] | None = None) -> dict:
    validate_r27p24_contract()
    current = os.environ if env is None else env
    if not _authorized(current):
        raise R27P24Error("authorization")
    r27p2._validate_preattempt_state()
    if SCRATCH_ROOT.exists():
        raise R27P24Error("scratch_root_preexists_preserve_for_forensics")
    SCRATCH_ROOT.parent.mkdir(parents=True, exist_ok=True)
    free_disk = int(shutil.disk_usage(SCRATCH_ROOT.parent).free)
    if free_disk < MIN_FREE_DISK_BYTES:
        raise R27P24Error(f"insufficient_free_disk:{free_disk}")
    start_mem = _mem_available_bytes()
    if start_mem < MIN_MEM_AVAILABLE_START_BYTES:
        raise R27P24Error(f"insufficient_memavailable_start:{start_mem}")
    SCRATCH_ROOT.mkdir(parents=False, exist_ok=False)

    child_env = dict(os.environ)
    child_env.update(dict(current))
    child_env[AUTH_ENV] = AUTH_TOKEN
    child_env[WORKER_ENV] = WORKER_TOKEN
    cmd = [
        sys.executable, "-m",
        "multimarket.dev045_d6r26a_p2_r27p24_july_worst_case_full_day_file_backed_rss_preexecution",
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
                trip_reason = f"worker_rss_above_gate:{worker_rss}"
            elif mem_available < SYSTEM_MEM_ABORT_BYTES:
                trip_reason = f"system_memavailable_below_abort:{mem_available}"
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
        raise R27P24Error(f"watchdog_tripped:{trip_reason}")
    if proc.returncode != 0:
        raise R27P24Error(f"worker_exit:{proc.returncode}")
    if not WORKER_RESULT.is_file():
        raise R27P24Error("worker_result_missing")

    worker = json.loads(WORKER_RESULT.read_text(encoding="utf-8"))
    rss_gate = worker["internal_peak_rss_bytes"] <= MAX_PEAK_RSS_BYTES and peak_worker <= MAX_PEAK_RSS_BYTES
    system_gate = min_mem >= SYSTEM_MEM_ABORT_BYTES
    result = {
        "worker": worker,
        "supervisor_peak_worker_rss_bytes": peak_worker,
        "supervisor_peak_worker_rss_gib": peak_worker / 1024**3,
        "min_system_mem_available_bytes": min_mem,
        "min_system_mem_available_gib": min_mem / 1024**3,
        "rss_gate_pass": bool(rss_gate),
        "system_memory_gate_pass": bool(system_gate),
        "watchdog_tripped": False,
        "p2_attempt_consumed": False,
    }
    print(f"R27P24_SOURCE_IDENTITY=PASS DAY={SOURCE_DAY} ROWS={SOURCE_ROWS} BYTES={SOURCE_BYTES} SHA256={SOURCE_SHA256}")
    print(f"R27P24_EXPECTED_RAW_FILE_BYTES={EXPECTED_RAW_FILE_BYTES}")
    print(f"R27P24_MIN_FREE_DISK_BYTES={MIN_FREE_DISK_BYTES}")
    print(f"R27P24_PRE_RUN_DISK_FREE_BYTES={free_disk}")
    print(f"R27P24_PRE_RUN_MEM_AVAILABLE_GIB={start_mem / 1024**3:.6f}")
    print(f"R27P24_WORKER_INTERNAL_PEAK_RSS_GIB={worker['internal_peak_rss_gib']:.6f}")
    print(f"R27P24_SUPERVISOR_PEAK_WORKER_RSS_GIB={result['supervisor_peak_worker_rss_gib']:.6f}")
    print(f"R27P24_MIN_SYSTEM_MEM_AVAILABLE_GIB={result['min_system_mem_available_gib']:.6f}")
    print(f"R27P24_JUL_WORST_CASE_RSS_GATE={'PASS' if rss_gate else 'FAIL'}")
    print(f"R27P24_SYSTEM_MEMORY_GATE={'PASS' if system_gate else 'FAIL'}")
    print("R27P24_WATCHDOG_MONITORED_PID=PYTHON_WORKER_PID")
    print("R27P24_REFERENCE_RERUN=NO")
    print("R27P24_NEW_REAL_PARITY_CLAIM=NO")
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
    except Exception as exc:
        print(f"R27P24_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("GLOBAL_WORST_CASE_FULL_DAY_BOUNDED_MEMORY_PROVEN=NO")
        print("CANONICAL_EXECUTION_READY=NO")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 2
    return 0 if result["rss_gate_pass"] and result["system_memory_gate_pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

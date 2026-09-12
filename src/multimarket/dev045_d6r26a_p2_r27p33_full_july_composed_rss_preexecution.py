from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import numpy as np

from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r27p29_stateful_windowed_raw_synthetic_parity as r27p29
from multimarket import dev045_d6r26a_p2_r27p31_stateful_corrected_feature_window_synthetic_parity as r27p31
from multimarket import dev045_d6r26a_p2_r27p32_5m_composed_rss_preexecution as r27p32

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P33"
DESIGN_VERSION = "real-full-july-composed-windowed-raw-corrected-feature-rss-v1"
PARENT_R27P32_RESULT_HEAD = "3df52a7d2a2ae98ba3757141715bc7af0eb0110d"
PARENT_R27P32_CLASSIFICATION = "ENGINEERING_5M_COMPOSED_PASS"
PARENT_R27P32_PEAK_RSS_BYTES = 652_070_912

SOURCE_PATH = Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy")
SOURCE_DAY = "2026-07-01"
SOURCE_ROWS = 181_084_390
SOURCE_BYTES = 11_589_401_216
SOURCE_SHA256_FROZEN = "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f"
DAY_START_LOCAL_NS = 1_782_864_000_000_000_000
DAY_END_EXCLUSIVE_LOCAL_NS = DAY_START_LOCAL_NS + 86_400_000_000_000
RAW_INPUT_CHUNK_ROWS = 262_144
FEATURE_DECISION_CHUNK_ROWS = 64

WORKER_RSS_CEILING_BYTES = 12 * 1024**3
START_MEMAVAILABLE_FLOOR_BYTES = 12 * 1024**3
SYSTEM_ABORT_MEMAVAILABLE_BYTES = 8 * 1024**3
WATCHDOG_POLL_SECONDS = 0.25

REAL_HISTORICAL_OPEN_AUTHORIZED = True
REAL_HISTORICAL_SCOPE = "ONE_FROZEN_FULL_JULY_DAY_ONLY"
SOURCE_REHASH_AUTHORIZED = False
FULL_DAY_OPEN_AUTHORIZED = True
FULL_JAN_JUL_RERUN_AUTHORIZED = False
DURABLE_ENGINEERING_RESULT_WRITE_AUTHORIZED = True
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


class R27P33Error(RuntimeError):
    pass


def _status_memory_bytes(pid: int) -> dict[str, int]:
    path = Path(f"/proc/{int(pid)}/status")
    wanted = {"VmRSS", "RssAnon", "RssFile", "RssShmem"}
    out: dict[str, int] = {}
    for line in path.read_text().splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        if key in wanted:
            fields = rest.split()
            if fields:
                out[key] = int(fields[0]) * 1024
    return out


def validate_contract() -> None:
    r27p31.validate_r27p31_contract()
    if PARENT_R27P32_RESULT_HEAD != "3df52a7d2a2ae98ba3757141715bc7af0eb0110d":
        raise R27P33Error("parent_result_head")
    if PARENT_R27P32_CLASSIFICATION != "ENGINEERING_5M_COMPOSED_PASS":
        raise R27P33Error("parent_classification")
    if PARENT_R27P32_PEAK_RSS_BYTES != 652_070_912:
        raise R27P33Error("parent_peak_rss")
    if SOURCE_ROWS != 181_084_390 or SOURCE_BYTES != 11_589_401_216:
        raise R27P33Error("source_contract")
    if WORKER_RSS_CEILING_BYTES != 12 * 1024**3:
        raise R27P33Error("rss_ceiling")
    if not REAL_HISTORICAL_OPEN_AUTHORIZED or not FULL_DAY_OPEN_AUTHORIZED:
        raise R27P33Error("full_day_authorization")
    if not DURABLE_ENGINEERING_RESULT_WRITE_AUTHORIZED:
        raise R27P33Error("result_authorization")
    forbidden = (
        SOURCE_REHASH_AUTHORIZED,
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
        raise R27P33Error("forbidden_surface")


def worker(root: Path) -> int:
    validate_contract()
    source = SOURCE_PATH
    if not source.is_file():
        raise R27P33Error(f"source_missing:{source}")
    if source.stat().st_size != SOURCE_BYTES:
        raise R27P33Error(f"source_size:{source.stat().st_size}")

    root.mkdir(parents=True, exist_ok=False)
    events = np.load(source, mmap_mode="r", allow_pickle=False)
    if int(events.shape[0]) != SOURCE_ROWS:
        raise R27P33Error(f"source_rows:{events.shape[0]}")

    first_local = int(events[0]["local_ts"])
    last_local = int(events[-1]["local_ts"])
    if first_local < DAY_START_LOCAL_NS or first_local >= DAY_START_LOCAL_NS + 1_000_000_000:
        raise R27P33Error(f"first_local_day_binding:{first_local}")
    if last_local < first_local or last_local >= DAY_END_EXCLUSIVE_LOCAL_NS:
        raise R27P33Error(f"last_local_day_binding:{last_local}")

    t0 = time.perf_counter()
    raw_kernel = r27p29.build_stateful_windowed_raw_kernel()
    raw = r27p29.run_stateful_windowed_raw_from_columns(
        events["ev"], events["exch_ts"], events["local_ts"], events["px"], events["qty"],
        root=root / "raw",
        input_chunk_rows=RAW_INPUT_CHUNK_ROWS,
        kernel=raw_kernel,
    )
    raw_elapsed = time.perf_counter() - t0
    if int(raw.error) != 0:
        raise R27P33Error(f"raw_error:{raw.error}")

    surface, raw_maps = r27p32._map_raw_prefix(raw)
    feature = None
    try:
        bounds = r17.derive_feed_bounds(
            events,
            nominal_day_start_local_ns=DAY_START_LOCAL_NS,
            nominal_day_end_exclusive_local_ns=DAY_END_EXCLUSIVE_LOCAL_NS,
        )
        requested = np.asarray(r17.build_shared_decision_grid(bounds=bounds), dtype="<i8")
        if requested.size == 0:
            raise R27P33Error("requested_grid_empty")

        t1 = time.perf_counter()
        feature_kernel = r27p31.build_stateful_corrected_feature_kernel()
        feature = r27p31.run_stateful_corrected_feature_surface(
            surface,
            requested,
            root=root / "feature",
            decision_chunk_rows=FEATURE_DECISION_CHUNK_ROWS,
            kernel=feature_kernel,
        )
        feature_elapsed = time.perf_counter() - t1
        digest = r27p32._digest_feature_result(feature)

        result = {
            "experiment_id": EXPERIMENT_ID,
            "design_version": DESIGN_VERSION,
            "classification": "ENGINEERING_FULL_JULY_COMPOSED_SUCCESS",
            "parent_r27p32_result_head": PARENT_R27P32_RESULT_HEAD,
            "source_day": SOURCE_DAY,
            "source_path": str(source),
            "source_full_rows": SOURCE_ROWS,
            "source_full_bytes": SOURCE_BYTES,
            "source_sha256_frozen_not_rehashed": SOURCE_SHA256_FROZEN,
            "rows": SOURCE_ROWS,
            "first_local_ns": first_local,
            "last_local_ns": last_local,
            "raw_input_chunk_rows": RAW_INPUT_CHUNK_ROWS,
            "feature_decision_chunk_rows": FEATURE_DECISION_CHUNK_ROWS,
            "raw_book_count": int(raw.book_count),
            "raw_flow_count": int(raw.flow_count),
            "raw_midpoint_count": int(raw.midpoint_count),
            "raw_chunk_count": int(raw.input_chunk_count),
            "raw_max_active_output_mapped_bytes": int(raw.max_active_output_mapped_bytes),
            "requested_decision_count": int(requested.size),
            "eligible_decision_count": int(feature.eligible_count),
            "leading_preeligible_count": int(feature.compiled.leading_preeligible_count),
            "feature_chunk_count": int(feature.decision_chunk_count),
            "feature_max_active_output_mapped_bytes": int(feature.max_active_output_mapped_bytes),
            "feature_max_transition_sq_rows": int(feature.max_transition_sq_rows),
            "feature_digest_sha256": digest,
            "raw_elapsed_seconds": raw_elapsed,
            "feature_elapsed_seconds": feature_elapsed,
            "worker_elapsed_seconds": time.perf_counter() - t0,
            "p2_attempt_consumed": False,
        }
        (root / "worker_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return 0
    finally:
        if feature is not None and not feature.closed:
            r27p31.close_feature_result(feature)
        r27p32._close_maps(raw_maps)
        mm = getattr(events, "_mmap", None)
        if mm is not None:
            mm.close()


def supervisor(root: Path) -> int:
    validate_contract()
    if root.exists():
        raise R27P33Error(f"result_root_exists:{root}")
    if r27p32._memavailable_bytes() < START_MEMAVAILABLE_FLOOR_BYTES:
        raise R27P33Error("start_memavailable_below_12_gib")

    cmd = [
        sys.executable,
        "-m",
        "multimarket.dev045_d6r26a_p2_r27p33_full_july_composed_rss_preexecution",
        "--worker",
        "--root",
        str(root),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    peak_rss = 0
    peak_status: dict[str, int] = {}
    peak_rollup: dict[str, int] = {}
    min_available = r27p32._memavailable_bytes()
    polls = 0
    trip = None
    started = time.perf_counter()

    while proc.poll() is None:
        polls += 1
        try:
            status = _status_memory_bytes(proc.pid)
            rss = int(status.get("VmRSS", 0))
            available = r27p32._memavailable_bytes()
            rollup = r27p32._smaps_rollup(proc.pid)
        except FileNotFoundError:
            break

        if rss > peak_rss:
            peak_rss = rss
            peak_status = status
            peak_rollup = rollup
        min_available = min(min_available, available)

        if rss > WORKER_RSS_CEILING_BYTES:
            trip = f"worker_rss_above_12_gib:{rss}"
        elif available < SYSTEM_ABORT_MEMAVAILABLE_BYTES:
            trip = f"system_memavailable_below_8_gib:{available}"

        if trip is not None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
            break

        time.sleep(WATCHDOG_POLL_SECONDS)

    stdout, stderr = proc.communicate()
    elapsed = time.perf_counter() - started
    root.mkdir(parents=True, exist_ok=True)
    worker_result_path = root / "worker_result.json"
    worker_result = json.loads(worker_result_path.read_text()) if worker_result_path.exists() else None

    classification = (
        "ENGINEERING_FULL_JULY_COMPOSED_PASS"
        if trip is None and proc.returncode == 0 and worker_result is not None
        else "ENGINEERING_FULL_JULY_COMPOSED_FAIL"
    )
    result = {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "classification": classification,
        "parent_r27p32_result_head": PARENT_R27P32_RESULT_HEAD,
        "rows": SOURCE_ROWS,
        "worker_rss_ceiling_bytes": WORKER_RSS_CEILING_BYTES,
        "peak_worker_rss_bytes": peak_rss,
        "peak_worker_rss_gib": peak_rss / 1024**3,
        "peak_status_memory_bytes": peak_status,
        "peak_smaps_rollup_bytes": peak_rollup,
        "min_memavailable_bytes": min_available,
        "min_memavailable_gib": min_available / 1024**3,
        "watchdog_polls": polls,
        "watchdog_poll_seconds": WATCHDOG_POLL_SECONDS,
        "trip": trip,
        "worker_returncode": proc.returncode,
        "elapsed_seconds": elapsed,
        "worker_stdout": stdout,
        "worker_stderr": stderr,
        "worker_result": worker_result,
        "p2_attempt_consumed": False,
        "source_rehashed": False,
    }
    (root / "supervisor_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if classification == "ENGINEERING_FULL_JULY_COMPOSED_PASS" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        return worker(args.root)
    return supervisor(args.root)


if __name__ == "__main__":
    raise SystemExit(main())

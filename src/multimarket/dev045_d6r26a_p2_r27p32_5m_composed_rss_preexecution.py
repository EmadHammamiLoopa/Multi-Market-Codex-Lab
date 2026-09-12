from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import numpy as np

from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p29_stateful_windowed_raw_synthetic_parity as r27p29
from multimarket import dev045_d6r26a_p2_r27p31_stateful_corrected_feature_window_synthetic_parity as r27p31

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P32"
DESIGN_VERSION = "real-5m-composed-windowed-raw-corrected-feature-rss-v1"
PARENT_R27P31_HEAD = "8492cca69ae6902cb6167f3e86fae44707fb6bc2"
PARENT_R27P31_CI_RUN = 34720214998
PARENT_R27P31_CI_JOB = 103624590789
PARENT_R27P31_CI_CONCLUSION = "success"

SOURCE_PATH = Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy")
SOURCE_DAY = "2026-07-01"
SOURCE_ROWS = 181_084_390
SOURCE_BYTES = 11_589_401_216
SOURCE_SHA256_FROZEN = "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f"
ROWS = 5_000_000
RAW_INPUT_CHUNK_ROWS = 262_144
FEATURE_DECISION_CHUNK_ROWS = 64

WORKER_RSS_CEILING_BYTES = 12 * 1024**3
START_MEMAVAILABLE_FLOOR_BYTES = 12 * 1024**3
SYSTEM_ABORT_MEMAVAILABLE_BYTES = 8 * 1024**3
WATCHDOG_POLL_SECONDS = 0.25

REAL_HISTORICAL_OPEN_AUTHORIZED = True
REAL_HISTORICAL_SCOPE = "FIRST_5M_ROWS_OF_FROZEN_JULY_SOURCE_ONLY"
SOURCE_REHASH_AUTHORIZED = False
FULL_DAY_OPEN_AUTHORIZED = False
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


class R27P32Error(RuntimeError):
    pass


def _memavailable_bytes() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise R27P32Error("memavailable_missing")


def _rss_bytes(pid: int) -> int:
    text = Path(f"/proc/{int(pid)}/status").read_text()
    for line in text.splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    return 0


def _smaps_rollup(pid: int) -> dict[str, int]:
    path = Path(f"/proc/{int(pid)}/smaps_rollup")
    if not path.exists():
        return {}
    wanted = {"Rss", "Pss", "RssAnon", "RssFile", "RssShmem", "Private_Clean", "Private_Dirty"}
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


def _map_raw_prefix(run: r27p29.StatefulRawRun) -> tuple[r27p5.CompactFeatureSurface, list[np.memmap]]:
    specs = {spec.name: spec for spec in r27p29.r27p20_specs()}
    counts = {
        "book_local_ns": run.book_count,
        "bid_ticks": run.book_count,
        "bid_qty": run.book_count,
        "ask_ticks": run.book_count,
        "ask_qty": run.book_count,
        "candidate_qty": run.book_count,
        "flow_local_ns": run.flow_count,
        "flow_code": run.flow_count,
        "flow_qty": run.flow_count,
    }
    mapped: dict[str, np.memmap] = {}
    for name, count in counts.items():
        spec = specs[name]
        mapped[name] = np.memmap(
            run.paths[name],
            mode="r",
            dtype=np.dtype(spec.dtype),
            shape=(int(count),) + tuple(spec.trailing_shape),
        )
        mapped[name].setflags(write=False)
    surface = r27p5.CompactFeatureSurface(
        book_local_ns=mapped["book_local_ns"],
        bid_ticks=mapped["bid_ticks"],
        bid_qty=mapped["bid_qty"],
        ask_ticks=mapped["ask_ticks"],
        ask_qty=mapped["ask_qty"],
        candidate_qty=mapped["candidate_qty"],
        flow_local_ns=mapped["flow_local_ns"],
        flow_code=mapped["flow_code"],
        flow_qty=mapped["flow_qty"],
    )
    return surface, list(mapped.values())


def _close_maps(arrays: list[np.memmap]) -> None:
    for array in arrays:
        mm = getattr(array, "_mmap", None)
        if mm is not None:
            mm.close()


def _digest_feature_result(result: r27p31.FileBackedFeatureResult) -> str:
    h = hashlib.sha256()
    for array in (
        result.compiled.decision_local_ns,
        result.compiled.best_bid_tick,
        result.compiled.best_ask_tick,
        result.compiled.values,
    ):
        view = np.asarray(array).view(np.uint8).reshape(-1)
        step = 8 * 1024 * 1024
        for start in range(0, int(view.size), step):
            h.update(memoryview(view[start : start + step]))
    return h.hexdigest()


def validate_contract() -> None:
    r27p31.validate_r27p31_contract()
    if PARENT_R27P31_HEAD != "8492cca69ae6902cb6167f3e86fae44707fb6bc2":
        raise R27P32Error("parent")
    if PARENT_R27P31_CI_RUN != 34720214998 or PARENT_R27P31_CI_JOB != 103624590789:
        raise R27P32Error("parent_ci")
    if PARENT_R27P31_CI_CONCLUSION != "success":
        raise R27P32Error("parent_ci_conclusion")
    if ROWS != 5_000_000 or ROWS >= SOURCE_ROWS:
        raise R27P32Error("row_scope")
    if SOURCE_BYTES != 11_589_401_216:
        raise R27P32Error("source_bytes_contract")
    if WORKER_RSS_CEILING_BYTES != 12 * 1024**3:
        raise R27P32Error("rss_ceiling")
    forbidden = (
        SOURCE_REHASH_AUTHORIZED,
        FULL_DAY_OPEN_AUTHORIZED,
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
        raise R27P32Error("forbidden_surface")
    if not REAL_HISTORICAL_OPEN_AUTHORIZED or not DURABLE_ENGINEERING_RESULT_WRITE_AUTHORIZED:
        raise R27P32Error("engineering_authorization")


def worker(root: Path) -> int:
    validate_contract()
    source = SOURCE_PATH
    if not source.is_file():
        raise R27P32Error(f"source_missing:{source}")
    if source.stat().st_size != SOURCE_BYTES:
        raise R27P32Error(f"source_size:{source.stat().st_size}")

    root.mkdir(parents=True, exist_ok=False)
    events_full = np.load(source, mmap_mode="r", allow_pickle=False)
    if int(events_full.shape[0]) != SOURCE_ROWS:
        raise R27P32Error(f"source_rows:{events_full.shape[0]}")
    events = events_full[:ROWS]

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
        raise R27P32Error(f"raw_error:{raw.error}")

    surface, raw_maps = _map_raw_prefix(raw)
    feature = None
    try:
        first_local = int(events[0]["local_ts"])
        last_local = int(events[-1]["local_ts"])
        # Bind a nominal interval that contains the prefix while preserving the
        # exact R17 one-second grid semantics. The prefix itself defines EOF.
        nominal_start = (first_local // 1_000_000_000) * 1_000_000_000
        nominal_end = max(nominal_start + 86_400_000_000_000, last_local + 1)
        bounds = r17.derive_feed_bounds(
            events,
            nominal_day_start_local_ns=nominal_start,
            nominal_day_end_exclusive_local_ns=nominal_end,
        )
        requested = np.asarray(r17.build_shared_decision_grid(bounds=bounds), dtype="<i8")
        if requested.size == 0:
            raise R27P32Error("requested_grid_empty")

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
        digest = _digest_feature_result(feature)

        result = {
            "experiment_id": EXPERIMENT_ID,
            "design_version": DESIGN_VERSION,
            "classification": "ENGINEERING_5M_COMPOSED_SUCCESS",
            "parent_r27p31_head": PARENT_R27P31_HEAD,
            "source_day": SOURCE_DAY,
            "source_path": str(source),
            "source_full_rows": SOURCE_ROWS,
            "source_full_bytes": SOURCE_BYTES,
            "source_sha256_frozen_not_rehashed": SOURCE_SHA256_FROZEN,
            "rows": ROWS,
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
        _close_maps(raw_maps)
        mm = getattr(events_full, "_mmap", None)
        if mm is not None:
            mm.close()


def supervisor(root: Path) -> int:
    validate_contract()
    if root.exists():
        raise R27P32Error(f"result_root_exists:{root}")
    if _memavailable_bytes() < START_MEMAVAILABLE_FLOOR_BYTES:
        raise R27P32Error("start_memavailable_below_12_gib")

    cmd = [sys.executable, "-m", "multimarket.dev045_d6r26a_p2_r27p32_5m_composed_rss_preexecution", "--worker", "--root", str(root)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    peak_rss = 0
    min_available = _memavailable_bytes()
    peak_rollup: dict[str, int] = {}
    polls = 0
    trip = None
    started = time.perf_counter()

    while proc.poll() is None:
        polls += 1
        try:
            rss = _rss_bytes(proc.pid)
            available = _memavailable_bytes()
            rollup = _smaps_rollup(proc.pid)
        except FileNotFoundError:
            break
        if rss > peak_rss:
            peak_rss = rss
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
    classification = "ENGINEERING_5M_COMPOSED_PASS" if trip is None and proc.returncode == 0 and worker_result is not None else "ENGINEERING_5M_COMPOSED_FAIL"
    result = {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "classification": classification,
        "parent_r27p31_head": PARENT_R27P31_HEAD,
        "rows": ROWS,
        "worker_rss_ceiling_bytes": WORKER_RSS_CEILING_BYTES,
        "peak_worker_rss_bytes": peak_rss,
        "peak_worker_rss_gib": peak_rss / 1024**3,
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
    return 0 if classification == "ENGINEERING_5M_COMPOSED_PASS" else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    return worker(args.root) if args.worker else supervisor(args.root)


if __name__ == "__main__":
    raise SystemExit(main())

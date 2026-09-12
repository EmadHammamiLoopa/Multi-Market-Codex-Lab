from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import ctypes
import gc
import hashlib
import json
import os

import numpy as np

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P27"
DESIGN_VERSION = "thin-isolated-worker-rss-preexecution-v1"

AUTH_ENV = "DEV045_D6R26A_P2_R27P27_AUTHORIZE"
AUTH_TOKEN = "YES_FROZEN_JUL_THIN_WORKER_RSS_PROOF_PREATTEMPT"
WORKER_ENV = "DEV045_D6R26A_P2_R27P27_WORKER"
WORKER_TOKEN = "INTERNAL_SUPERVISED_WORKER_ONLY"

SOURCE_DAY = "2026-07-01"
SOURCE_PATH = Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy")
SOURCE_ROWS = 181_084_390
SOURCE_BYTES = 11_589_401_216
SOURCE_SHA256 = "85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f"
SOURCE_DAY_START_NS = 1_782_864_000_000_000_000
SOURCE_DAY_END_EXCLUSIVE_NS = SOURCE_DAY_START_NS + 86_400_000_000_000

SCRATCH_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p27_jul_full_day_rss")
WORKER_ROOT = SCRATCH_ROOT / "worker"
WORKER_RESULT = SCRATCH_ROOT / "worker_result.json"

P2_ROOT = Path("/home/emadh/Multi-Market/evidence/dev045_d6r26a_p2_candidate_labels_v1")
P2_ATTEMPT_MARKER = P2_ROOT / "DEV045_D6R26A_P2_ATTEMPT_CONSUMED.json"
P2_FAILURE = P2_ROOT / "DEV045_D6R26A_P2_FAILURE.json"
P2_CANONICAL_MANIFEST = P2_ROOT / "DEV045_D6R26A_P2_CANONICAL_MANIFEST.json"


class R27P27WorkerError(RuntimeError):
    pass


def _authorized() -> bool:
    return (
        os.environ.get(AUTH_ENV) == AUTH_TOKEN
        and os.environ.get(WORKER_ENV) == WORKER_TOKEN
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb", buffering=0) as handle:
        while True:
            chunk = handle.read(8 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _validate_preattempt_state() -> None:
    forbidden = (P2_ATTEMPT_MARKER, P2_FAILURE, P2_CANONICAL_MANIFEST)
    present = [str(p) for p in forbidden if p.exists()]
    if present:
        raise R27P27WorkerError("p2_preattempt_state_closed:" + ",".join(present))


def _verify_source_identity() -> np.memmap:
    if not SOURCE_PATH.is_file():
        raise R27P27WorkerError("source_missing")
    if int(SOURCE_PATH.stat().st_size) != SOURCE_BYTES:
        raise R27P27WorkerError("source_bytes")
    if _sha256(SOURCE_PATH) != SOURCE_SHA256:
        raise R27P27WorkerError("source_sha256")
    events = np.load(SOURCE_PATH, mmap_mode="r", allow_pickle=False)
    if not isinstance(events, np.memmap):
        raise R27P27WorkerError("source_not_memmap")
    if bool(events.flags.writeable):
        raise R27P27WorkerError("source_writeable")
    if int(events.size) != SOURCE_ROWS:
        raise R27P27WorkerError("source_rows")
    return events


def _trim_process_heap() -> dict:
    collected = gc.collect()
    trim_called = False
    trim_return = None
    try:
        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim.argtypes = [ctypes.c_size_t]
        libc.malloc_trim.restype = ctypes.c_int
        trim_return = int(libc.malloc_trim(0))
        trim_called = True
    except Exception:
        trim_called = False
        trim_return = None
    return {
        "gc_collected": int(collected),
        "malloc_trim_called": bool(trim_called),
        "malloc_trim_return": trim_return,
    }


def _atomic_json(path: Path, payload: dict) -> None:
    temp = path.with_name(path.name + ".tmp")
    with temp.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def run_worker() -> dict:
    if not _authorized():
        raise R27P27WorkerError("worker_authorization")
    _validate_preattempt_state()
    events = _verify_source_identity()

    # Import the heavy execution stack only after governance/source identity is proven.
    from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
    from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
    from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
    from multimarket import dev045_d6r26a_p2_r27p9_cpython313_float_sum_parity_amendment as r27p9
    from multimarket import dev045_d6r26a_p2_r27p18_corrected_5m_speed_benchmark_preexecution as r27p18
    from multimarket import dev045_d6r26a_p2_r27p21_file_backed_fused_raw_kernel_synthetic_parity as r27p21

    trim = _trim_process_heap()
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
        import resource
        peak_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
        result = {
            "experiment_id": EXPERIMENT_ID,
            "design_version": DESIGN_VERSION,
            "source_day": SOURCE_DAY,
            "source_path": str(SOURCE_PATH),
            "rows": SOURCE_ROWS,
            "source_bytes": SOURCE_BYTES,
            "source_sha256": SOURCE_SHA256,
            "internal_peak_rss_bytes": peak_bytes,
            "internal_peak_rss_gib": peak_bytes / 1024**3,
            "candidate_digest": asdict(digest),
            "l5_changed_cells": int(l5_changed),
            "volatility_changed_cells": int(vol_changed),
            "heap_trim": trim,
            "p2_attempt_consumed": False,
        }
        _atomic_json(WORKER_RESULT, result)
        return result
    finally:
        if context is not None and not context.midpoint_index.closed:
            r20.close_midpoint_index(context.midpoint_index)
        r27p21.close_adapter_runs(holder)
        r27p18._close_source_memmap(events)


def main() -> int:
    try:
        result = run_worker()
        print(f"R27P27_WORKER_INTERNAL_PEAK_RSS_GIB={result['internal_peak_rss_gib']:.6f}")
        print("R27P27_WORKER_RESULT=PASS")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 0
    except Exception as exc:
        print(f"R27P27_WORKER_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

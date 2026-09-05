from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np

from multimarket import dev045_d6r8ed_semantic_real_parity_contract as c
from multimarket import dev045_d6r8ef_semantic_real_parity_runner as fixed
from multimarket import dev045_d6r8ee_semantic_parity_runner as parity

EXPERIMENT_ID = "DEV045-D6R8EG"
SCHEMA_VERSION = "dev045-d6r8eg-semantic-real-parity-successor-v1"
FIX_HEAD = "eb0762ca4b3b69fd8966e20ee51d213ea5fcd301"
FAILED_D6R8EF_EXECUTION_HEAD = "7d07dd531136bde1c7b7f6ecad023ff3fe5ce3d2"
EXECUTION_AUTHORIZED = True

RUNTIME_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r8eg")
ATTEMPT_MARKER = RUNTIME_ROOT / "ATTEMPT_STARTED.json"
SLICE_DIR = RUNTIME_ROOT / "slice"
WORK_DIR = RUNTIME_ROOT / "work"
OUTPUT_DIR = RUNTIME_ROOT / "output"
TRADE_SLICE = SLICE_DIR / "trades_BTCUSDT_2026-01-01_0000_0010.csv.gz"
DEPTH_SLICE = SLICE_DIR / "depth_BTCUSDT_2026-01-01_0000_0010.csv.gz"
UPSTREAM_OUT = OUTPUT_DIR / "upstream.npy"
OLD_OUT = OUTPUT_DIR / "old.npy"
V2_OUT = OUTPUT_DIR / "v2.npy"
OLD_SCRATCH = WORK_DIR / "old_scratch"
V2_SCRATCH = WORK_DIR / "v2_scratch"
DEFAULT_EVIDENCE = Path("evidence/dev045_d6r8eg_semantic_real_parity.json")

TRADE_RAW = Path(c.RAW_ROOT) / c.TRADE_RELATIVE_PATH
DEPTH_RAW = Path(c.RAW_ROOT) / c.DEPTH_RELATIVE_PATH

D6R8EF_MARKER = Path("/home/emadh/Multi-Market/runtime/dev045_d6r8ef/ATTEMPT_STARTED.json")
D6R8EF_MARKER_SHA256 = "f022ee78ce82f84a1d7e1fcfff376ff1fbdea988f2be3f79ef2f8886a0944cb6"
D6R8EF_EVIDENCE = Path("evidence/dev045_d6r8ef_semantic_real_parity.json")
D6R8EF_EVIDENCE_SHA256 = "4d42e51c91bc5950848c14e7f41ca576e5f64749fd512015f485cd14835d164f"

CHILD_DIAGNOSTIC_TAIL_CHARS = 8192


class D6R8EGError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _memavailable_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise D6R8EGError("memavailable_unavailable")


def _assert_historical_d6r8ef_frozen() -> dict[str, str]:
    if not D6R8EF_MARKER.is_file():
        raise D6R8EGError("d6r8ef_marker_missing")
    if not D6R8EF_EVIDENCE.is_file():
        raise D6R8EGError("d6r8ef_evidence_missing")
    marker_sha = _sha256(D6R8EF_MARKER)
    evidence_sha = _sha256(D6R8EF_EVIDENCE)
    if marker_sha != D6R8EF_MARKER_SHA256:
        raise D6R8EGError(f"d6r8ef_marker_sha256:{marker_sha}")
    if evidence_sha != D6R8EF_EVIDENCE_SHA256:
        raise D6R8EGError(f"d6r8ef_evidence_sha256:{evidence_sha}")
    payload = json.loads(D6R8EF_EVIDENCE.read_text(encoding="utf-8"))
    if payload.get("status") != "FAIL" or payload.get("experiment_id") != "DEV045-D6R8EF":
        raise D6R8EGError("d6r8ef_frozen_identity")
    return {"marker_sha256": marker_sha, "evidence_sha256": evidence_sha, "status": "FROZEN_FAIL"}


def _raw_identity(path: Path, expected_bytes: int, expected_sha256: str) -> dict[str, int | str]:
    if not path.is_file():
        raise D6R8EGError(f"missing_raw:{path}")
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise D6R8EGError(f"raw_bytes:{path}:{actual_bytes}:{expected_bytes}")
    actual_sha = _sha256(path)
    if actual_sha != expected_sha256:
        raise D6R8EGError(f"raw_sha256:{path}:{actual_sha}:{expected_sha256}")
    return {"bytes": actual_bytes, "sha256": actual_sha}


def _extract_slice(src: Path, dst: Path) -> dict[str, int | str | bool | None]:
    try:
        return fixed._extract_slice(src, dst)
    except Exception as exc:
        raise D6R8EGError(f"slice_extract:{src}:{type(exc).__name__}:{exc}") from exc


def _assert_trade_semantics(obs: dict[str, object]) -> None:
    actual = parity.SemanticIdentity(
        int(obs["selected_rows"]),
        int(obs["decompressed_bytes"]),
        str(obs["decompressed_sha256"]),
        int(obs["first_local_timestamp_us"]),
        int(obs["last_local_timestamp_us"]),
    )
    expected = parity.SemanticIdentity(
        c.TRADE_SEMANTIC_ROWS,
        c.TRADE_SEMANTIC_BYTES,
        c.TRADE_DECOMPRESSED_SHA256,
        c.TRADE_FIRST_LOCAL_TIMESTAMP_US,
        c.TRADE_LAST_LOCAL_TIMESTAMP_US,
    )
    if actual != expected:
        raise D6R8EGError(f"trade_semantic_identity:{actual!r}:{expected!r}")


def _assert_depth_semantics(obs: dict[str, object]) -> None:
    actual = parity.SemanticIdentity(
        int(obs["selected_rows"]),
        int(obs["decompressed_bytes"]),
        str(obs["decompressed_sha256"]),
        int(obs["first_local_timestamp_us"]),
        int(obs["last_local_timestamp_us"]),
    )
    expected = parity.SemanticIdentity(
        c.DEPTH_SEMANTIC_ROWS,
        c.DEPTH_SEMANTIC_BYTES,
        c.DEPTH_DECOMPRESSED_SHA256,
        c.DEPTH_FIRST_LOCAL_TIMESTAMP_US,
        c.DEPTH_LAST_LOCAL_TIMESTAMP_US,
    )
    if actual != expected:
        raise D6R8EGError(f"depth_semantic_identity:{actual!r}:{expected!r}")
    if obs["first_selected_is_snapshot"] is not c.DEPTH_FIRST_SELECTED_IS_SNAPSHOT:
        raise D6R8EGError("depth_first_selected_snapshot")
    if int(obs["snapshot_batches"]) != c.DEPTH_SNAPSHOT_BATCHES:
        raise D6R8EGError("depth_snapshot_batches")
    if int(obs["snapshot_rows"]) != c.DEPTH_SNAPSHOT_ROWS:
        raise D6R8EGError("depth_snapshot_rows")
    if bool(obs["ends_inside_snapshot_batch"]) is not c.DEPTH_ENDS_INSIDE_SNAPSHOT_BATCH:
        raise D6R8EGError("depth_ends_inside_snapshot")


def _child_convert(kind: str) -> int:
    import hftbacktest as h

    if h.__version__ != c.HFTBACKTEST_VERSION:
        raise D6R8EGError(f"hftbacktest_version:{h.__version__}")

    if kind == "upstream":
        sizes = fixed._upstream_buffer_sizes()
        if sizes.event_rows != 496_256 or sizes.snapshot_rows != 1_024:
            raise D6R8EGError(f"upstream_buffer_binding:{sizes}")
        arr = fixed._convert_upstream(TRADE_SLICE, DEPTH_SLICE)
        np.save(UPSTREAM_OUT, arr, allow_pickle=False)
        payload = {
            "rows": len(arr),
            "itemsize": arr.dtype.itemsize,
            "buffer_size": sizes.event_rows,
            "ss_buffer_size": sizes.snapshot_rows,
            "output_sha256": _sha256(UPSTREAM_OUT),
        }
    elif kind == "old":
        from multimarket import dev045_d6r_bounded_converter as old

        result = old.convert_tardis(
            TRADE_SLICE,
            DEPTH_SLICE,
            OLD_OUT,
            chunk_rows=c.OLD_PRODUCTION_CHUNK_ROWS,
            scratch_dir=OLD_SCRATCH,
        )
        payload = {
            "rows": result.final_event_rows,
            "itemsize": 64,
            "output_sha256": result.output_sha256,
        }
    elif kind == "v2":
        from multimarket import dev045_d6r8_structurally_bounded_converter as v2

        result = v2.convert_tardis(TRADE_SLICE, DEPTH_SLICE, V2_OUT, scratch_dir=V2_SCRATCH)
        peak_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        payload = {
            "rows": result.final_event_rows,
            "itemsize": 64,
            "output_sha256": result.output_sha256,
            "base_event_rows": result.base_event_rows,
            "initial_sort_runs": result.initial_sort_runs,
            "exchange_merge_levels": result.exchange_merge_levels,
            "local_merge_levels": result.local_merge_levels,
            "chunk_rows": result.chunk_rows,
            "peak_rss_bytes": int(peak_kib) * 1024,
        }
    else:
        raise D6R8EGError(f"unknown_child:{kind}")

    print(json.dumps(payload, sort_keys=True))
    return 0


def _diagnostic_tail(text: str) -> str:
    return text[-CHILD_DIAGNOSTIC_TAIL_CHARS:]


def _execute_child(kind: str, evidence: dict[str, object]) -> dict[str, object]:
    cmd = [sys.executable, "-m", "multimarket.dev045_d6r8eg_semantic_real_parity_successor", "--child", kind]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    stdout_sha = hashlib.sha256(proc.stdout.encode()).hexdigest()
    stderr_sha = hashlib.sha256(proc.stderr.encode()).hexdigest()
    evidence[f"{kind}_return_code"] = proc.returncode
    evidence[f"{kind}_stdout_sha256"] = stdout_sha
    evidence[f"{kind}_stderr_sha256"] = stderr_sha
    evidence[f"{kind}_stdout_tail"] = _diagnostic_tail(proc.stdout)
    evidence[f"{kind}_stderr_tail"] = _diagnostic_tail(proc.stderr)
    if proc.returncode != 0:
        raise D6R8EGError(f"{kind}_return_code:{proc.returncode}:stderr_sha256={stderr_sha}")
    try:
        payload = json.loads(proc.stdout.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise D6R8EGError(f"{kind}_invalid_json") from exc
    payload["stdout_sha256"] = stdout_sha
    payload["stderr_sha256"] = stderr_sha
    return payload


def _ensure_fresh_runtime(evidence_path: Path) -> None:
    if evidence_path.exists():
        raise D6R8EGError("canonical_evidence_already_exists")
    if ATTEMPT_MARKER.exists():
        raise D6R8EGError("canonical_attempt_already_started")
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    for path in (SLICE_DIR, WORK_DIR, OUTPUT_DIR):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    OLD_SCRATCH.mkdir()
    V2_SCRATCH.mkdir()


def run(evidence_path: Path) -> int:
    if not EXECUTION_AUTHORIZED or os.environ.get("DEV045_D6R8EG_AUTHORIZE") != "YES_ONE_SHOT":
        raise D6R8EGError("real_execution_not_authorized")

    _ensure_fresh_runtime(evidence_path)

    import hftbacktest as h

    if h.__version__ != c.HFTBACKTEST_VERSION:
        raise D6R8EGError(f"hftbacktest_version:{h.__version__}")
    sizes = fixed._upstream_buffer_sizes()
    if sizes.event_rows != 496_256 or sizes.snapshot_rows != 1_024:
        raise D6R8EGError(f"upstream_buffer_binding:{sizes}")
    mem = _memavailable_bytes()
    if mem < c.MIN_MEMAVAILABLE_BYTES:
        raise D6R8EGError(f"memavailable:{mem}:{c.MIN_MEMAVAILABLE_BYTES}")
    historical = _assert_historical_d6r8ef_frozen()

    attempt = {
        "experiment_id": EXPERIMENT_ID,
        "canonical_attempt": 1,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "fix_head": FIX_HEAD,
        "failed_d6r8ef_execution_head": FAILED_D6R8EF_EXECUTION_HEAD,
        "d6r8ef_status": "FROZEN_FAIL",
    }
    ATTEMPT_MARKER.write_text(json.dumps(attempt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    evidence: dict[str, object] = {
        **attempt,
        "schema_version": SCHEMA_VERSION,
        "status": "FAIL",
        "failure_reason": None,
        "mem_available_bytes": mem,
        "historical_d6r8ef": historical,
        "upstream_buffer_size": sizes.event_rows,
        "upstream_ss_buffer_size": sizes.snapshot_rows,
        "real_data_opened": False,
        "upstream_executed": False,
        "old_executed": False,
        "v2_executed": False,
        "d6r8ef_rerun": False,
        "jan_full_day_opened": False,
        "feb_jul_opened": False,
        "aug_opened": False,
        "sep_plus_opened": False,
        "non_btc_opened": False,
        "policy_replay_run": False,
        "historical_pnl_computed": False,
        "railway_touched": False,
        "live_trading_authorized": False,
    }

    try:
        evidence["real_data_opened"] = True
        evidence["raw_identity"] = {
            "trades": _raw_identity(TRADE_RAW, c.TRADE_RAW_BYTES, c.TRADE_RAW_SHA256),
            "depth": _raw_identity(DEPTH_RAW, c.DEPTH_RAW_BYTES, c.DEPTH_RAW_SHA256),
        }

        trade_obs = _extract_slice(TRADE_RAW, TRADE_SLICE)
        depth_obs = _extract_slice(DEPTH_RAW, DEPTH_SLICE)
        evidence["semantic_slice"] = {"trades": trade_obs, "depth": depth_obs}
        _assert_trade_semantics(trade_obs)
        _assert_depth_semantics(depth_obs)

        evidence["upstream_executed"] = True
        upstream = _execute_child("upstream", evidence)
        evidence["upstream"] = upstream

        evidence["old_executed"] = True
        old = _execute_child("old", evidence)
        evidence["old"] = old

        evidence["v2_executed"] = True
        v2 = _execute_child("v2", evidence)
        evidence["v2"] = v2
        if int(v2["peak_rss_bytes"]) > c.V2_RUNTIME_RSS_ABORT_BYTES:
            raise D6R8EGError("v2_peak_rss_over_contract")

        upstream_arr = np.load(UPSTREAM_OUT, allow_pickle=False)
        old_arr = np.load(OLD_OUT, allow_pickle=False)
        v2_arr = np.load(V2_OUT, allow_pickle=False)
        result = parity.compare_three_way(upstream_arr, old_arr, v2_arr)
        evidence["parity"] = {
            "rows": result.rows,
            "dtype_itemsize": result.dtype_itemsize,
            "upstream_old_equal": result.upstream_old_equal,
            "upstream_v2_equal": result.upstream_v2_equal,
            "old_v2_equal": result.old_v2_equal,
        }

        if any(OLD_SCRATCH.iterdir()) or any(V2_SCRATCH.iterdir()):
            raise D6R8EGError("scratch_not_empty")

        evidence["status"] = "PASS"
    except Exception as exc:
        evidence["failure_reason"] = f"{type(exc).__name__}:{exc}"
    finally:
        evidence["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return 0 if evidence["status"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", choices=("upstream", "old", "v2"))
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    if args.child:
        return _child_convert(args.child)
    return run(args.evidence)


if __name__ == "__main__":
    raise SystemExit(main())

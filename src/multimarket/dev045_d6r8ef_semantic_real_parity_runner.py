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
from multimarket import dev045_d6r8ee_semantic_parity_runner as parity

EXPERIMENT_ID = "DEV045-D6R8EF"
SCHEMA_VERSION = "dev045-d6r8ef-semantic-real-parity-v1"
PREAUTHORIZATION_HEAD = "0a204b479fd7c66b54824914be408f233a53e18e"
EXECUTION_AUTHORIZED = True

RUNTIME_ROOT = Path(c.SUCCESSOR_RUNTIME_ROOT)
ATTEMPT_MARKER = Path(c.SUCCESSOR_ATTEMPT_MARKER_PATH)
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
DEFAULT_EVIDENCE = Path(c.SUCCESSOR_EVIDENCE_PATH)

TRADE_RAW = Path(c.RAW_ROOT) / c.TRADE_RELATIVE_PATH
DEPTH_RAW = Path(c.RAW_ROOT) / c.DEPTH_RELATIVE_PATH


class D6R8EFError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _memavailable_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise D6R8EFError("memavailable_unavailable")


def _raw_identity(path: Path, expected_bytes: int, expected_sha256: str) -> dict[str, int | str]:
    if not path.is_file():
        raise D6R8EFError(f"missing_raw:{path}")
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise D6R8EFError(f"raw_bytes:{path}:{actual_bytes}:{expected_bytes}")
    actual_sha = _sha256(path)
    if actual_sha != expected_sha256:
        raise D6R8EFError(f"raw_sha256:{path}:{actual_sha}:{expected_sha256}")
    return {"bytes": actual_bytes, "sha256": actual_sha}


def _write_gzip(path: Path, lines: list[bytes]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as gz:
            for line in lines:
                gz.write(line)


def _extract_slice(src: Path, dst: Path) -> dict[str, int | str | bool | None]:
    selected: list[bytes] = []
    first_ts = None
    last_ts = None
    scanned = 0
    rows_before = 0
    snapshot_batches = 0
    snapshot_rows = 0
    in_snapshot = False
    first_selected_is_snapshot = None

    with gzip.open(src, "rb") as fh:
        header = fh.readline()
        if not header:
            raise D6R8EFError(f"empty_raw:{src}")
        header_fields = next(csv.reader([header.decode("utf-8").rstrip("\r\n")]))
        try:
            local_idx = header_fields.index(c.SELECTION_FIELD)
        except ValueError as exc:
            raise D6R8EFError(f"missing_selection_field:{src}") from exc
        snapshot_idx = header_fields.index("is_snapshot") if "is_snapshot" in header_fields else None
        selected.append(header)

        for raw_line in fh:
            scanned += 1
            row = next(csv.reader([raw_line.decode("utf-8").rstrip("\r\n")]))
            ts = int(row[local_idx])
            if ts < c.WINDOW_START_LOCAL_TIMESTAMP_US:
                rows_before += 1
                continue
            if ts >= c.WINDOW_END_LOCAL_TIMESTAMP_US:
                break
            if first_ts is None:
                first_ts = ts
            last_ts = ts

            if snapshot_idx is not None:
                is_snapshot = row[snapshot_idx].strip().lower() == "true"
                if first_selected_is_snapshot is None:
                    first_selected_is_snapshot = is_snapshot
                if is_snapshot:
                    snapshot_rows += 1
                    if not in_snapshot:
                        snapshot_batches += 1
                    in_snapshot = True
                else:
                    in_snapshot = False

            selected.append(raw_line)

    _write_gzip(dst, selected)
    ident = parity.inspect_semantic_identity(dst, local_idx)
    return {
        "selected_rows": ident.rows,
        "scanned_rows_until_stop": scanned,
        "rows_before_window": rows_before,
        "decompressed_bytes": ident.decompressed_bytes,
        "decompressed_sha256": ident.decompressed_sha256,
        "first_local_timestamp_us": ident.first_local_timestamp_us,
        "last_local_timestamp_us": ident.last_local_timestamp_us,
        "first_selected_is_snapshot": first_selected_is_snapshot,
        "snapshot_batches": snapshot_batches,
        "snapshot_rows": snapshot_rows,
        "ends_inside_snapshot_batch": in_snapshot if snapshot_idx is not None else None,
        "compressed_sha256_diagnostic": _sha256(dst),
    }


def _assert_trade_semantics(obs: dict[str, object]) -> None:
    expected = parity.SemanticIdentity(
        c.TRADE_SEMANTIC_ROWS,
        c.TRADE_SEMANTIC_BYTES,
        c.TRADE_DECOMPRESSED_SHA256,
        c.TRADE_FIRST_LOCAL_TIMESTAMP_US,
        c.TRADE_LAST_LOCAL_TIMESTAMP_US,
    )
    actual = parity.SemanticIdentity(
        int(obs["selected_rows"]),
        int(obs["decompressed_bytes"]),
        str(obs["decompressed_sha256"]),
        int(obs["first_local_timestamp_us"]),
        int(obs["last_local_timestamp_us"]),
    )
    parity.assert_expected_semantic_identity(actual, expected)


def _assert_depth_semantics(obs: dict[str, object]) -> None:
    expected = parity.SemanticIdentity(
        c.DEPTH_SEMANTIC_ROWS,
        c.DEPTH_SEMANTIC_BYTES,
        c.DEPTH_DECOMPRESSED_SHA256,
        c.DEPTH_FIRST_LOCAL_TIMESTAMP_US,
        c.DEPTH_LAST_LOCAL_TIMESTAMP_US,
    )
    actual = parity.SemanticIdentity(
        int(obs["selected_rows"]),
        int(obs["decompressed_bytes"]),
        str(obs["decompressed_sha256"]),
        int(obs["first_local_timestamp_us"]),
        int(obs["last_local_timestamp_us"]),
    )
    parity.assert_expected_semantic_identity(actual, expected)
    if obs["first_selected_is_snapshot"] is not c.DEPTH_FIRST_SELECTED_IS_SNAPSHOT:
        raise D6R8EFError("depth_first_selected_snapshot")
    if int(obs["snapshot_batches"]) != c.DEPTH_SNAPSHOT_BATCHES:
        raise D6R8EFError("depth_snapshot_batches")
    if int(obs["snapshot_rows"]) != c.DEPTH_SNAPSHOT_ROWS:
        raise D6R8EFError("depth_snapshot_rows")
    if bool(obs["ends_inside_snapshot_batch"]) is not c.DEPTH_ENDS_INSIDE_SNAPSHOT_BATCH:
        raise D6R8EFError("depth_ends_inside_snapshot")


def _child_convert(kind: str) -> int:
    import hftbacktest as h
    if h.__version__ != c.HFTBACKTEST_VERSION:
        raise D6R8EFError(f"hftbacktest_version:{h.__version__}")

    if kind == "upstream":
        from hftbacktest.data.utils import tardis
        arr = tardis.convert(
            [str(TRADE_SLICE), str(DEPTH_SLICE)],
            output_filename=None,
            buffer_size=128,
            ss_buffer_size=64,
            base_latency=c.UPSTREAM_BASE_LATENCY,
            snapshot_mode=c.UPSTREAM_SNAPSHOT_MODE,
        )
        np.save(UPSTREAM_OUT, arr, allow_pickle=False)
        payload = {"rows": len(arr), "itemsize": arr.dtype.itemsize, "output_sha256": _sha256(UPSTREAM_OUT)}
    elif kind == "old":
        from multimarket import dev045_d6r_bounded_converter as old
        result = old.convert_tardis(
            TRADE_SLICE,
            DEPTH_SLICE,
            OLD_OUT,
            chunk_rows=c.OLD_PRODUCTION_CHUNK_ROWS,
            scratch_dir=OLD_SCRATCH,
        )
        payload = {"rows": result.final_event_rows, "itemsize": 64, "output_sha256": result.output_sha256}
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
        raise D6R8EFError(f"unknown_child:{kind}")
    print(json.dumps(payload, sort_keys=True))
    return 0


def _run_child(kind: str) -> dict[str, object]:
    cmd = [sys.executable, "-m", "multimarket.dev045_d6r8ef_semantic_real_parity_runner", "--child", kind]
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise D6R8EFError(f"{kind}_return_code:{proc.returncode}:stderr_sha256={hashlib.sha256(proc.stderr.encode()).hexdigest()}")
    try:
        payload = json.loads(proc.stdout.strip())
    except json.JSONDecodeError as exc:
        raise D6R8EFError(f"{kind}_invalid_json") from exc
    payload["stdout_sha256"] = hashlib.sha256(proc.stdout.encode()).hexdigest()
    payload["stderr_sha256"] = hashlib.sha256(proc.stderr.encode()).hexdigest()
    return payload


def _ensure_fresh_runtime(evidence_path: Path) -> None:
    if evidence_path.exists():
        raise D6R8EFError("canonical_evidence_already_exists")
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    if ATTEMPT_MARKER.exists():
        raise D6R8EFError("canonical_attempt_already_started")
    for path in (SLICE_DIR, WORK_DIR, OUTPUT_DIR):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    OLD_SCRATCH.mkdir()
    V2_SCRATCH.mkdir()


def run(evidence_path: Path) -> int:
    if not EXECUTION_AUTHORIZED or os.environ.get("DEV045_D6R8EF_AUTHORIZE") != "YES_ONE_SHOT":
        raise D6R8EFError("real_execution_not_authorized")
    _ensure_fresh_runtime(evidence_path)

    attempt = {
        "experiment_id": EXPERIMENT_ID,
        "canonical_attempt": 1,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "preauthorization_head": PREAUTHORIZATION_HEAD,
        "parent_contract_head": c.PARENT_HEAD,
    }
    ATTEMPT_MARKER.write_text(json.dumps(attempt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    evidence: dict[str, object] = {
        **attempt,
        "schema_version": SCHEMA_VERSION,
        "status": "FAIL",
        "failure_reason": None,
        "real_data_opened": False,
        "upstream_executed": False,
        "old_executed": False,
        "v2_executed": False,
        "d6r8eb_rerun": False,
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
        mem = _memavailable_bytes()
        evidence["mem_available_bytes"] = mem
        if mem < c.MIN_MEMAVAILABLE_BYTES:
            raise D6R8EFError(f"memavailable:{mem}:{c.MIN_MEMAVAILABLE_BYTES}")

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
        upstream = _run_child("upstream")
        evidence["upstream"] = upstream

        evidence["old_executed"] = True
        old = _run_child("old")
        evidence["old"] = old

        evidence["v2_executed"] = True
        v2 = _run_child("v2")
        evidence["v2"] = v2
        if int(v2["peak_rss_bytes"]) > c.V2_RUNTIME_RSS_ABORT_BYTES:
            raise D6R8EFError("v2_peak_rss_over_contract")

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
            raise D6R8EFError("scratch_not_empty")
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

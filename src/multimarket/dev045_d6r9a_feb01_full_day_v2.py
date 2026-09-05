from __future__ import annotations

import argparse
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
from numpy.lib import format as npy_format

from multimarket import dev045_d6r8_structurally_bounded_converter as v2
from multimarket import dev045_d6r8c_bounded_converter_redesign_contract as resource_contract

EXPERIMENT_ID = "DEV045-D6R9A"
SCHEMA_VERSION = "dev045-d6r9a-feb01-full-day-v2-v1"
PARENT_PARITY_HEAD = "e8d87ed29998e1af5a037ff2290c72cdfe967344"
EXECUTION_AUTHORIZED = True
DAY = "2026-02-01"
SYMBOL = "BTCUSDT"

RAW_ROOT = Path("/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw")
TRADE_RAW = RAW_ROOT / "trades/BTCUSDT/2026-02-01.csv.gz"
DEPTH_RAW = RAW_ROOT / "incremental_book_L2/BTCUSDT/2026-02-01.csv.gz"
TRADE_RAW_BYTES = 57_631_972
TRADE_RAW_SHA256 = "dfd19ab53abbc90118ce3c861521ecb17dbed6ce7bcc7410c07f296460454508"
DEPTH_RAW_BYTES = 865_907_076
DEPTH_RAW_SHA256 = "a1e9fc0fcc20d309d171ed1b6367ebe17948c84dd025a07a5d13c80f0b023cc4"
FROZEN_RAW_ROWS = 172_721_707
REQUIRED_SCRATCH_BYTES = 127_721_761_664

D6R8EG_MARKER = Path("/home/emadh/Multi-Market/runtime/dev045_d6r8eg/ATTEMPT_STARTED.json")
D6R8EG_MARKER_SHA256 = "ccbf010be8a0493da30e22a8c51bbc98961bd5d11635eadd2a8403f4d7ada95f"
D6R8EG_EVIDENCE = Path("evidence/dev045_d6r8eg_semantic_real_parity.json")
D6R8EG_EVIDENCE_SHA256 = "c912e7a8233995aed3abfd4d911e35b10097f46e434f56502f09dbb41a5806b9"
D6R8EG_OUTPUT_SHA256 = "60ebc2aec273976c12526f7c49159d005368388a0f9d5993af269cc9753ffaf7"

RUNTIME_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r9a")
ATTEMPT_MARKER = RUNTIME_ROOT / "ATTEMPT_STARTED.json"
OUTPUT_DIR = RUNTIME_ROOT / "output"
SCRATCH_DIR = RUNTIME_ROOT / "scratch"
OUTPUT_PATH = OUTPUT_DIR / "BTCUSDT_2026-02-01.npy"
DEFAULT_EVIDENCE = Path("evidence/dev045_d6r9a_feb01_full_day_v2.json")
CHILD_DIAGNOSTIC_TAIL_CHARS = 8192


class D6R9AError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _assert_d6r8eg_frozen_pass() -> dict[str, object]:
    if not D6R8EG_MARKER.is_file():
        raise D6R9AError("d6r8eg_marker_missing")
    if not D6R8EG_EVIDENCE.is_file():
        raise D6R9AError("d6r8eg_evidence_missing")
    marker_sha = _sha256(D6R8EG_MARKER)
    evidence_sha = _sha256(D6R8EG_EVIDENCE)
    if marker_sha != D6R8EG_MARKER_SHA256:
        raise D6R9AError(f"d6r8eg_marker_sha256:{marker_sha}")
    if evidence_sha != D6R8EG_EVIDENCE_SHA256:
        raise D6R9AError(f"d6r8eg_evidence_sha256:{evidence_sha}")
    payload = json.loads(D6R8EG_EVIDENCE.read_text(encoding="utf-8"))
    parity = payload.get("parity") or {}
    if payload.get("status") != "PASS" or payload.get("experiment_id") != "DEV045-D6R8EG":
        raise D6R9AError("d6r8eg_status")
    if not all(
        parity.get(key) is True
        for key in ("upstream_old_equal", "upstream_v2_equal", "old_v2_equal")
    ):
        raise D6R9AError("d6r8eg_three_way_parity")
    for key in ("upstream", "old", "v2"):
        section = payload.get(key) or {}
        if section.get("output_sha256") != D6R8EG_OUTPUT_SHA256:
            raise D6R9AError(f"d6r8eg_output_sha256:{key}")
        if section.get("rows") != 503_934 or section.get("itemsize") != 64:
            raise D6R9AError(f"d6r8eg_output_shape:{key}")
    return {
        "status": "FROZEN_PASS",
        "marker_sha256": marker_sha,
        "evidence_sha256": evidence_sha,
        "three_way_output_sha256": D6R8EG_OUTPUT_SHA256,
        "rows": 503_934,
        "itemsize": 64,
    }


def _stat_raw_no_content() -> dict[str, dict[str, int]]:
    facts: dict[str, dict[str, int]] = {}
    for label, path, expected_bytes in (
        ("trades", TRADE_RAW, TRADE_RAW_BYTES),
        ("depth", DEPTH_RAW, DEPTH_RAW_BYTES),
    ):
        if not path.is_file():
            raise D6R9AError(f"missing_raw:{label}:{path}")
        actual = path.stat().st_size
        if actual != expected_bytes:
            raise D6R9AError(f"raw_bytes:{label}:{actual}:{expected_bytes}")
        facts[label] = {"bytes": actual}
    return facts


def _prepare_runtime(evidence_path: Path) -> None:
    if ATTEMPT_MARKER.exists():
        raise D6R9AError("canonical_attempt_already_started")
    if evidence_path.exists():
        raise D6R9AError("canonical_evidence_already_exists")
    if OUTPUT_PATH.exists():
        raise D6R9AError("output_already_exists")
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    for path in (OUTPUT_DIR, SCRATCH_DIR):
        if path.exists():
            if any(path.iterdir()):
                raise D6R9AError(f"runtime_directory_not_empty:{path}")
        else:
            path.mkdir()


def _preflight(evidence_path: Path) -> dict[str, object]:
    _prepare_runtime(evidence_path)
    raw_stat = _stat_raw_no_content()
    historical = _assert_d6r8eg_frozen_pass()
    import hftbacktest as h

    if h.__version__ != resource_contract.HFTBACKTEST_VERSION:
        raise D6R9AError(f"hftbacktest_version:{h.__version__}")
    if v2.PRODUCTION_INITIAL_CHUNK_ROWS != 250_000 or v2.MERGE_FAN_IN != 8:
        raise D6R9AError("v2_production_binding")
    resources = v2.canonical_resource_preflight(
        raw_rows=FROZEN_RAW_ROWS,
        scratch_dir=SCRATCH_DIR,
        output_parent=OUTPUT_DIR,
    )
    if resources["required_scratch_bytes"] != REQUIRED_SCRATCH_BYTES:
        raise D6R9AError(
            f"required_scratch:{resources['required_scratch_bytes']}:{REQUIRED_SCRATCH_BYTES}"
        )
    return {
        "raw_stat_no_content": raw_stat,
        "historical_d6r8eg": historical,
        "hftbacktest_version": h.__version__,
        "v2_chunk_rows": v2.PRODUCTION_INITIAL_CHUNK_ROWS,
        "v2_merge_fan_in": v2.MERGE_FAN_IN,
        "resource_preflight": resources,
    }


def _child_convert() -> int:
    import hftbacktest as h

    if h.__version__ != resource_contract.HFTBACKTEST_VERSION:
        raise D6R9AError(f"hftbacktest_version:{h.__version__}")
    result = v2.convert_tardis(
        TRADE_RAW,
        DEPTH_RAW,
        OUTPUT_PATH,
        scratch_dir=SCRATCH_DIR,
    )
    peak_rss_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    print(
        json.dumps(
            {
                "base_event_rows": result.base_event_rows,
                "final_event_rows": result.final_event_rows,
                "initial_sort_runs": result.initial_sort_runs,
                "exchange_merge_levels": result.exchange_merge_levels,
                "local_merge_levels": result.local_merge_levels,
                "chunk_rows": result.chunk_rows,
                "output_sha256": result.output_sha256,
                "peak_rss_bytes": peak_rss_bytes,
            },
            sort_keys=True,
        )
    )
    return 0


def _diagnostic_tail(text: str) -> str:
    return text[-CHILD_DIAGNOSTIC_TAIL_CHARS:]


def _execute_child(evidence: dict[str, object]) -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, "-m", "multimarket.dev045_d6r9a_feb01_full_day_v2", "--child"],
        text=True,
        capture_output=True,
        check=False,
    )
    stdout_sha = hashlib.sha256(proc.stdout.encode()).hexdigest()
    stderr_sha = hashlib.sha256(proc.stderr.encode()).hexdigest()
    evidence["v2_return_code"] = proc.returncode
    evidence["v2_stdout_sha256"] = stdout_sha
    evidence["v2_stderr_sha256"] = stderr_sha
    evidence["v2_stdout_tail"] = _diagnostic_tail(proc.stdout)
    evidence["v2_stderr_tail"] = _diagnostic_tail(proc.stderr)
    if proc.returncode != 0:
        raise D6R9AError(f"v2_return_code:{proc.returncode}:stderr_sha256={stderr_sha}")
    try:
        payload = json.loads(proc.stdout.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise D6R9AError("v2_invalid_json") from exc
    return payload


def _verify_output_header(expected_rows: int) -> dict[str, object]:
    import hftbacktest as h

    with OUTPUT_PATH.open("rb") as fh:
        version = npy_format.read_magic(fh)
        if version != (1, 0):
            raise D6R9AError(f"output_npy_version:{version}")
        shape, fortran, dtype = npy_format.read_array_header_1_0(fh)
        header_bytes = fh.tell()
    dtype = np.dtype(dtype)
    if tuple(shape) != (expected_rows,):
        raise D6R9AError(f"output_shape:{shape}:{expected_rows}")
    if fortran:
        raise D6R9AError("output_fortran_order")
    expected_dtype = np.dtype(h.event_dtype)
    if dtype != expected_dtype or dtype.itemsize != 64:
        raise D6R9AError(f"output_dtype:{dtype}:{dtype.itemsize}")
    output_bytes = OUTPUT_PATH.stat().st_size
    expected_bytes = header_bytes + expected_rows * 64
    if output_bytes != expected_bytes:
        raise D6R9AError(f"output_bytes:{output_bytes}:{expected_bytes}")
    return {
        "npy_version": [1, 0],
        "rows": expected_rows,
        "itemsize": 64,
        "header_bytes": header_bytes,
        "output_bytes": output_bytes,
    }


def run(evidence_path: Path) -> int:
    if not EXECUTION_AUTHORIZED or os.environ.get("DEV045_D6R9A_AUTHORIZE") != "YES_ONE_SHOT":
        raise D6R9AError("real_execution_not_authorized")

    preflight = _preflight(evidence_path)

    attempt = {
        "experiment_id": EXPERIMENT_ID,
        "canonical_attempt": 1,
        "day": DAY,
        "symbol": SYMBOL,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "parent_parity_head": PARENT_PARITY_HEAD,
        "d6r8eg_status": "FROZEN_PASS",
    }
    ATTEMPT_MARKER.write_text(json.dumps(attempt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    evidence: dict[str, object] = {
        **attempt,
        "schema_version": SCHEMA_VERSION,
        "status": "FAIL",
        "failure_reason": None,
        **preflight,
        "real_feb_data_opened": False,
        "v2_executed": False,
        "old_converter_executed": False,
        "upstream_converter_executed": False,
        "jan_rerun": False,
        "other_feb_jul_opened": False,
        "aug_opened": False,
        "sep_plus_opened": False,
        "non_btc_opened": False,
        "policy_replay_run": False,
        "historical_pnl_computed": False,
        "railway_touched": False,
        "live_trading_authorized": False,
    }

    try:
        evidence["real_feb_data_opened"] = True
        trade_sha = _sha256(TRADE_RAW)
        depth_sha = _sha256(DEPTH_RAW)
        evidence["raw_identity"] = {
            "trades": {"bytes": TRADE_RAW_BYTES, "sha256": trade_sha},
            "depth": {"bytes": DEPTH_RAW_BYTES, "sha256": depth_sha},
            "frozen_raw_rows": FROZEN_RAW_ROWS,
        }
        if trade_sha != TRADE_RAW_SHA256:
            raise D6R9AError(f"trade_raw_sha256:{trade_sha}:{TRADE_RAW_SHA256}")
        if depth_sha != DEPTH_RAW_SHA256:
            raise D6R9AError(f"depth_raw_sha256:{depth_sha}:{DEPTH_RAW_SHA256}")

        evidence["v2_executed"] = True
        result = _execute_child(evidence)
        evidence["v2"] = result
        if int(result["chunk_rows"]) != 250_000:
            raise D6R9AError("v2_chunk_rows")
        if int(result["peak_rss_bytes"]) > resource_contract.RUNTIME_RSS_ABORT_BYTES:
            raise D6R9AError(
                f"v2_peak_rss:{result['peak_rss_bytes']}:{resource_contract.RUNTIME_RSS_ABORT_BYTES}"
            )
        evidence["output_header"] = _verify_output_header(int(result["final_event_rows"]))
        evidence["output_sha256"] = str(result["output_sha256"])
        if any(SCRATCH_DIR.iterdir()):
            raise D6R9AError("scratch_not_empty")
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
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    if args.child:
        return _child_convert()
    return run(args.evidence)


if __name__ == "__main__":
    raise SystemExit(main())

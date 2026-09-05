from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
from numpy.lib import format as npy_format

from multimarket import dev045_d6r8_structurally_bounded_converter as v2
from multimarket import dev045_d6r8c_bounded_converter_redesign_contract as resource_contract

EXPERIMENT_ID = "DEV045-D6R9B"
SCHEMA_VERSION = "dev045-d6r9b-mar-jul-bulk-v2-v1"
PARENT_D6R9A_HEAD = "d9972bf8947466d91728a61dfa39bf5c1ed1f682"
EXECUTION_AUTHORIZED = True
SYMBOL = "BTCUSDT"

RAW_ROOT = Path("/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw")
RUNTIME_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r9b")
OUTPUT_DIR = RUNTIME_ROOT / "output"

D6R9A_MARKER = Path("/home/emadh/Multi-Market/runtime/dev045_d6r9a/ATTEMPT_STARTED.json")
D6R9A_MARKER_SHA256 = "66ffb16ae49ef37740e51a0e9b3d562ab2724762d4290ecf8e594a62b742d4c7"
D6R9A_EVIDENCE = Path("evidence/dev045_d6r9a_feb01_full_day_v2.json")
D6R9A_EVIDENCE_SHA256 = "54afd16ca610b76de0658d68764b661335fcda23e3ae3ca4ce4de93c57c199d9"
D6R9A_OUTPUT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r9a/output/BTCUSDT_2026-02-01.npy")
D6R9A_OUTPUT_BYTES = 11_493_385_088
D6R9A_OUTPUT_SHA256 = "d757d2ac32a29b0ac587323e115779c466068c6c0eba4270226b9c4109254cbc"
D6R9A_FINAL_ROWS = 179_584_138

CHILD_DIAGNOSTIC_TAIL_CHARS = 8192


@dataclass(frozen=True)
class DaySpec:
    day: str
    trade_bytes: int
    trade_sha256: str
    depth_bytes: int
    depth_sha256: str
    frozen_raw_rows: int
    required_scratch_bytes: int


DAY_SPECS = (
    DaySpec(
        "2026-03-01",
        50_842_755,
        "50d3762a883f3f1cddc6869bbc2dbaaacf5bb52637ac0b51b85ae4dfcafdcb50",
        737_199_360,
        "a5468fb97f161b05a89f8dcc39d8c88a58fb6dc60caeb69aa783facff66c27e1",
        145_757_298,
        110_464_539_904,
    ),
    DaySpec(
        "2026-04-01",
        33_823_287,
        "31959ff7bcf8aae71fe4826987a6cbafc7897c6e881a2d555b89b99ac4def804",
        675_132_621,
        "d1d08211ebcc8b576c4b9d50158ff39971f66dd463cffe1929dacd3d17223cfd",
        129_067_640,
        99_783_158_784,
    ),
    DaySpec(
        "2026-05-01",
        26_110_327,
        "272f6d8ac29d14098c27d9fdaf95795ac5ed371024a000f279feaa38cf5605e1",
        557_562_555,
        "284b95a8d84d1fdda10f73d80ba8cfb5f1f2ee60db9bd00937f3701e5948faf4",
        104_234_425,
        83_889_901_184,
    ),
    DaySpec(
        "2026-06-01",
        34_960_370,
        "f1f695bf6ef198f209a115250d1b99194bb21dfa4693cab2dcb4a10a969be53e",
        893_502_369,
        "581361873d3a692362257217e27961332ee25786dca27f280048be2ed150837d",
        165_502_465,
        123_101_446_784,
    ),
    DaySpec(
        "2026-07-01",
        41_982_532,
        "eefc51c11e55b6d0224e760479bff87fc1f052773ae3c8ae08700395fa229a87",
        923_475_379,
        "b2e8bbed3db89695f055dc3010a0fff074732d82ae18117a1602b5593c90d1f1",
        172_067_693,
        127_303_192_704,
    ),
)
DAY_BY_NAME = {spec.day: spec for spec in DAY_SPECS}


class D6R9BError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _trade_path(spec: DaySpec) -> Path:
    return RAW_ROOT / f"trades/BTCUSDT/{spec.day}.csv.gz"


def _depth_path(spec: DaySpec) -> Path:
    return RAW_ROOT / f"incremental_book_L2/BTCUSDT/{spec.day}.csv.gz"


def _day_root(spec: DaySpec) -> Path:
    return RUNTIME_ROOT / spec.day


def _scratch_dir(spec: DaySpec) -> Path:
    return _day_root(spec) / "scratch"


def _marker_path(spec: DaySpec) -> Path:
    return _day_root(spec) / "ATTEMPT_STARTED.json"


def _evidence_path(spec: DaySpec) -> Path:
    return Path(f"evidence/dev045_d6r9b_{spec.day}.json")


def _output_path(spec: DaySpec) -> Path:
    return OUTPUT_DIR / f"BTCUSDT_{spec.day}.npy"


def _assert_d6r9a_frozen_pass() -> dict[str, object]:
    if not D6R9A_MARKER.is_file() or not D6R9A_EVIDENCE.is_file():
        raise D6R9BError("d6r9a_frozen_artifact_missing")
    marker_sha = _sha256(D6R9A_MARKER)
    evidence_sha = _sha256(D6R9A_EVIDENCE)
    if marker_sha != D6R9A_MARKER_SHA256:
        raise D6R9BError(f"d6r9a_marker_sha256:{marker_sha}")
    if evidence_sha != D6R9A_EVIDENCE_SHA256:
        raise D6R9BError(f"d6r9a_evidence_sha256:{evidence_sha}")
    payload = json.loads(D6R9A_EVIDENCE.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS" or payload.get("experiment_id") != "DEV045-D6R9A":
        raise D6R9BError("d6r9a_status")
    if payload.get("output_sha256") != D6R9A_OUTPUT_SHA256:
        raise D6R9BError("d6r9a_output_sha256_evidence")
    if (payload.get("output_header") or {}).get("rows") != D6R9A_FINAL_ROWS:
        raise D6R9BError("d6r9a_final_rows")
    if not D6R9A_OUTPUT.is_file() or D6R9A_OUTPUT.stat().st_size != D6R9A_OUTPUT_BYTES:
        raise D6R9BError("d6r9a_output_file_identity")
    return {
        "status": "FROZEN_PASS",
        "marker_sha256": marker_sha,
        "evidence_sha256": evidence_sha,
        "output_sha256": D6R9A_OUTPUT_SHA256,
        "output_bytes": D6R9A_OUTPUT_BYTES,
        "final_rows": D6R9A_FINAL_ROWS,
    }


def _assert_static_bindings() -> dict[str, object]:
    import hftbacktest as h

    if h.__version__ != resource_contract.HFTBACKTEST_VERSION:
        raise D6R9BError(f"hftbacktest_version:{h.__version__}")
    if v2.PRODUCTION_INITIAL_CHUNK_ROWS != 250_000:
        raise D6R9BError("v2_chunk_rows")
    if v2.MERGE_FAN_IN != 8:
        raise D6R9BError("v2_merge_fan_in")
    for spec in DAY_SPECS:
        actual = resource_contract.required_scratch_bytes(spec.frozen_raw_rows)
        if actual != spec.required_scratch_bytes:
            raise D6R9BError(f"required_scratch:{spec.day}:{actual}:{spec.required_scratch_bytes}")
    return {
        "hftbacktest_version": h.__version__,
        "chunk_rows": v2.PRODUCTION_INITIAL_CHUNK_ROWS,
        "merge_fan_in": v2.MERGE_FAN_IN,
        "rss_abort_bytes": resource_contract.RUNTIME_RSS_ABORT_BYTES,
    }


def _prepare_dirs(spec: DaySpec) -> None:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    day_root = _day_root(spec)
    scratch = _scratch_dir(spec)
    day_root.mkdir(parents=True, exist_ok=True)
    if scratch.exists():
        if any(scratch.iterdir()):
            raise D6R9BError(f"scratch_not_fresh:{spec.day}")
    else:
        scratch.mkdir()


def _preflight_day(spec: DaySpec) -> dict[str, object]:
    marker = _marker_path(spec)
    evidence = _evidence_path(spec)
    output = _output_path(spec)
    if marker.exists() or evidence.exists() or output.exists():
        raise D6R9BError(f"day_not_fresh:{spec.day}")
    _prepare_dirs(spec)

    raw_stat: dict[str, int] = {}
    for label, path, expected in (
        ("trades", _trade_path(spec), spec.trade_bytes),
        ("depth", _depth_path(spec), spec.depth_bytes),
    ):
        if not path.is_file():
            raise D6R9BError(f"missing_raw:{spec.day}:{label}")
        actual = path.stat().st_size
        if actual != expected:
            raise D6R9BError(f"raw_bytes:{spec.day}:{label}:{actual}:{expected}")
        raw_stat[label] = actual

    resources = v2.canonical_resource_preflight(
        raw_rows=spec.frozen_raw_rows,
        scratch_dir=_scratch_dir(spec),
        output_parent=OUTPUT_DIR,
    )
    if resources["required_scratch_bytes"] != spec.required_scratch_bytes:
        raise D6R9BError(f"resource_preflight_scratch:{spec.day}")
    return {"raw_stat_no_content": raw_stat, "resource_preflight": resources}


def _existing_day_state(spec: DaySpec) -> str:
    marker = _marker_path(spec)
    evidence = _evidence_path(spec)
    output = _output_path(spec)
    if not marker.exists() and not evidence.exists() and not output.exists():
        return "FRESH"
    if marker.exists() and evidence.exists() and output.exists():
        try:
            payload = json.loads(evidence.read_text(encoding="utf-8"))
        except Exception as exc:
            raise D6R9BError(f"existing_evidence_unreadable:{spec.day}") from exc
        if payload.get("experiment_id") == EXPERIMENT_ID and payload.get("day") == spec.day and payload.get("status") == "PASS":
            return "FROZEN_PASS"
    return "FROZEN_NONPASS"


def _child_convert(spec: DaySpec) -> int:
    import hftbacktest as h

    if h.__version__ != resource_contract.HFTBACKTEST_VERSION:
        raise D6R9BError(f"hftbacktest_version:{h.__version__}")
    result = v2.convert_tardis(
        _trade_path(spec),
        _depth_path(spec),
        _output_path(spec),
        scratch_dir=_scratch_dir(spec),
    )
    peak_rss_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    print(json.dumps({
        "day": spec.day,
        "base_event_rows": result.base_event_rows,
        "final_event_rows": result.final_event_rows,
        "initial_sort_runs": result.initial_sort_runs,
        "exchange_merge_levels": result.exchange_merge_levels,
        "local_merge_levels": result.local_merge_levels,
        "chunk_rows": result.chunk_rows,
        "output_sha256": result.output_sha256,
        "peak_rss_bytes": peak_rss_bytes,
    }, sort_keys=True))
    return 0


def _diagnostic_tail(text: str) -> str:
    return text[-CHILD_DIAGNOSTIC_TAIL_CHARS:]


def _execute_child(spec: DaySpec, evidence: dict[str, object]) -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, "-m", "multimarket.dev045_d6r9b_mar_jul_bulk_v2", "--child", spec.day],
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
        raise D6R9BError(f"v2_return_code:{spec.day}:{proc.returncode}:stderr_sha256={stderr_sha}")
    try:
        return json.loads(proc.stdout.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise D6R9BError(f"v2_invalid_json:{spec.day}") from exc


def _verify_output_header(spec: DaySpec, expected_rows: int) -> dict[str, object]:
    import hftbacktest as h

    output = _output_path(spec)
    with output.open("rb") as fh:
        version = npy_format.read_magic(fh)
        if version != (1, 0):
            raise D6R9BError(f"output_npy_version:{spec.day}:{version}")
        shape, fortran, dtype = npy_format.read_array_header_1_0(fh)
        header_bytes = fh.tell()
    dtype = np.dtype(dtype)
    expected_dtype = np.dtype(h.event_dtype)
    if tuple(shape) != (expected_rows,) or fortran:
        raise D6R9BError(f"output_shape:{spec.day}:{shape}:{fortran}")
    if dtype != expected_dtype or dtype.itemsize != 64:
        raise D6R9BError(f"output_dtype:{spec.day}:{dtype}:{dtype.itemsize}")
    output_bytes = output.stat().st_size
    expected_bytes = header_bytes + expected_rows * 64
    if output_bytes != expected_bytes:
        raise D6R9BError(f"output_bytes:{spec.day}:{output_bytes}:{expected_bytes}")
    return {
        "npy_version": [1, 0],
        "rows": expected_rows,
        "itemsize": 64,
        "header_bytes": header_bytes,
        "output_bytes": output_bytes,
    }


def _run_day(spec: DaySpec, lineage: dict[str, object], bindings: dict[str, object]) -> bool:
    preflight = _preflight_day(spec)
    attempt = {
        "experiment_id": EXPERIMENT_ID,
        "schema_version": SCHEMA_VERSION,
        "canonical_attempt": 1,
        "day": spec.day,
        "symbol": SYMBOL,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "parent_d6r9a_head": PARENT_D6R9A_HEAD,
        "d6r9a_status": "FROZEN_PASS",
    }
    _marker_path(spec).write_text(json.dumps(attempt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    evidence: dict[str, object] = {
        **attempt,
        "status": "FAIL",
        "failure_reason": None,
        "historical_d6r9a": lineage,
        "bindings": bindings,
        **preflight,
        "real_day_data_opened": False,
        "v2_executed": False,
        "old_converter_executed": False,
        "upstream_converter_executed": False,
        "historical_pnl_computed": False,
        "aug_opened": False,
        "sep_plus_opened": False,
        "non_btc_opened": False,
        "policy_replay_run": False,
        "railway_touched": False,
        "live_trading_authorized": False,
    }

    try:
        evidence["real_day_data_opened"] = True
        trade_sha = _sha256(_trade_path(spec))
        depth_sha = _sha256(_depth_path(spec))
        evidence["raw_identity"] = {
            "trades": {"bytes": spec.trade_bytes, "sha256": trade_sha},
            "depth": {"bytes": spec.depth_bytes, "sha256": depth_sha},
            "frozen_raw_rows": spec.frozen_raw_rows,
        }
        if trade_sha != spec.trade_sha256:
            raise D6R9BError(f"trade_sha256:{spec.day}:{trade_sha}:{spec.trade_sha256}")
        if depth_sha != spec.depth_sha256:
            raise D6R9BError(f"depth_sha256:{spec.day}:{depth_sha}:{spec.depth_sha256}")

        evidence["v2_executed"] = True
        result = _execute_child(spec, evidence)
        evidence["v2"] = result
        if int(result["chunk_rows"]) != 250_000:
            raise D6R9BError(f"v2_chunk_rows:{spec.day}")
        if int(result["peak_rss_bytes"]) > resource_contract.RUNTIME_RSS_ABORT_BYTES:
            raise D6R9BError(f"v2_peak_rss:{spec.day}:{result['peak_rss_bytes']}")
        evidence["output_header"] = _verify_output_header(spec, int(result["final_event_rows"]))
        evidence["output_sha256"] = str(result["output_sha256"])
        if any(_scratch_dir(spec).iterdir()):
            raise D6R9BError(f"scratch_not_empty_after_success:{spec.day}")
        evidence["status"] = "PASS"
    except Exception as exc:
        evidence["failure_reason"] = f"{type(exc).__name__}:{exc}"
    finally:
        evidence["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        path = _evidence_path(spec)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return evidence["status"] == "PASS"


def run_bulk() -> int:
    if not EXECUTION_AUTHORIZED or os.environ.get("DEV045_D6R9B_AUTHORIZE") != "YES_BULK_SEQUENCE":
        raise D6R9BError("bulk_execution_not_authorized")

    lineage = _assert_d6r9a_frozen_pass()
    bindings = _assert_static_bindings()
    print(f"{EXPERIMENT_ID}_BULK_START=YES", flush=True)
    print("ORDER=" + ",".join(spec.day for spec in DAY_SPECS), flush=True)

    for spec in DAY_SPECS:
        state = _existing_day_state(spec)
        if state == "FROZEN_PASS":
            print(f"DAY={spec.day} STATUS=FROZEN_PASS ACTION=SKIP", flush=True)
            continue
        if state == "FROZEN_NONPASS":
            print(f"DAY={spec.day} STATUS=FROZEN_NONPASS ACTION=STOP RERUN=FORBIDDEN", flush=True)
            return 1

        print(f"DAY={spec.day} PREFLIGHT=START", flush=True)
        try:
            ok = _run_day(spec, lineage, bindings)
        except Exception as exc:
            print(f"DAY={spec.day} PRE_MARKER_FAILURE={type(exc).__name__}:{exc}", flush=True)
            print(f"DAY={spec.day} ATTEMPT_CONSUMED=NO", flush=True)
            return 1
        if not ok:
            print(f"DAY={spec.day} RESULT=FAIL RERUN=FORBIDDEN", flush=True)
            return 1
        payload = json.loads(_evidence_path(spec).read_text(encoding="utf-8"))
        result = payload["v2"]
        print(
            f"DAY={spec.day} RESULT=PASS ROWS={result['final_event_rows']} "
            f"PEAK_RSS_BYTES={result['peak_rss_bytes']} SHA256={result['output_sha256']}",
            flush=True,
        )

    print(f"{EXPERIMENT_ID}_BULK_RESULT=PASS", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", choices=tuple(DAY_BY_NAME))
    args = parser.parse_args()
    if args.child:
        return _child_convert(DAY_BY_NAME[args.child])
    return run_bulk()


if __name__ == "__main__":
    raise SystemExit(main())

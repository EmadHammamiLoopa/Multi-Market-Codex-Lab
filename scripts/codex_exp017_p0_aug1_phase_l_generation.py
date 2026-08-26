from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "CODEX-EXP-017-P0"
PASS_STATUS = "AUG1_PHASE_L_FEATURES_GENERATED_AND_INTEGRITY_PASS"
INVALID_STATUS = "INVALID"

DAY = "2026-08-01"
SYMBOL = "BTCUSDT"
EXPECTED_ROWS = 345_600
GRID_US = 250_000

EXP016_ARTIFACT = Path(
    "evidence/codex/exp016_p0_sealed_august_manifest/"
    "SEALED_AUGUST_RAW_INPUT_MANIFEST.json"
)
EXP016_ARTIFACT_SHA256 = (
    "0c95efcccc235ad4115200b0bc476c3881e8af05711e9716bb9c8d2c782f0782"
)

RAW_SHA256 = {
    "incremental_book_L2": (
        "bc7b4e6206bdbd893da75d035f63128b518ed34f3dd6490da71f96c72fe2a4cc"
    ),
    "trades": (
        "27622702d5e33e6d374ec3d6f9040e8d7550ca9229641bccb6289d64256e4afe"
    ),
}

SOURCE_BLOBS = {
    "tools/v23_phase0dl_depth250.cpp":
        "612706f3613271f22d639af96e426ebb0692c14f",
    "tools/v23_phase0dl_flow250.cpp":
        "e270ad43a8b2a771c9e8055c9b518888fe3e58ec",
    "tools/v23_phase0dl_trade250.cpp":
        "4dc14356a0ccd1e4d9ea292b755f59fd11b665a0",
    "tools/v23_phase0dl_snapshot_scan.cpp":
        "10ee2175bd32b8c4475e48c2f308c8c31ae93da4",
    "tools/v23_phase0dl_features250.cpp":
        "f76d4c374b38bf3d9ab1322ced2cfae26fa72142",
}

TOOL_ORDER = (
    "depth250",
    "flow250",
    "trade250",
    "snapshot_scan",
    "features250",
)

FEATURE_HEADER_PREFIX = (
    "local_timestamp_us,best_bid,best_ask,mid,book_valid,"
    "l0_valid,l1_valid,l2_valid,"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_sha(path: Path, workspace: Path) -> str:
    p = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )
    return p.stdout.strip()


def run_cmd(cmd: list[str], cwd: Path) -> dict[str, Any]:
    p = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return {
        "command": cmd,
        "returncode": int(p.returncode),
        "stdout": p.stdout,
        "stderr": p.stderr,
    }


def day_bounds_us() -> tuple[int, int]:
    start = int(
        datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp()
        * 1_000_000
    )
    return start, start + 86_400_000_000


def raw_paths(raw_dir: Path) -> dict[str, Path]:
    return {
        "incremental_book_L2":
            raw_dir / "incremental_book_L2" / SYMBOL / f"{DAY}.csv.gz",
        "trades":
            raw_dir / "trades" / SYMBOL / f"{DAY}.csv.gz",
    }


def derived_paths(derived_dir: Path) -> dict[str, Path]:
    root = derived_dir / SYMBOL
    return {
        "book250": root / f"{DAY}_BOOK250.csv",
        "flow250": root / f"{DAY}_FLOW250.csv",
        "trade250": root / f"{DAY}_TRADE250.csv",
        "snapshots": root / f"{DAY}_SNAPSHOTS.csv",
        "features250": root / f"{DAY}_FEATURES250.csv",
    }


def compile_tools(workspace: Path, build_dir: Path) -> dict[str, Any]:
    cxx = shutil.which("g++")
    if cxx is None:
        raise RuntimeError("g++ not found")

    build_dir.mkdir(parents=True, exist_ok=True)
    compiler_version = subprocess.run(
        [cxx, "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()[0]

    specs = {
        "depth250": (
            workspace / "tools/v23_phase0dl_depth250.cpp",
            True,
        ),
        "flow250": (
            workspace / "tools/v23_phase0dl_flow250.cpp",
            True,
        ),
        "trade250": (
            workspace / "tools/v23_phase0dl_trade250.cpp",
            True,
        ),
        "snapshot_scan": (
            workspace / "tools/v23_phase0dl_snapshot_scan.cpp",
            True,
        ),
        "features250": (
            workspace / "tools/v23_phase0dl_features250.cpp",
            False,
        ),
    }

    compiled: dict[str, Any] = {}

    for name in TOOL_ORDER:
        src, needs_zlib = specs[name]
        exe = build_dir / f"v23_phase0dl_{name}"
        cmd = [
            cxx,
            "-std=c++17",
            "-O3",
            "-DNDEBUG",
            str(src),
        ]
        if needs_zlib:
            cmd.append("-lz")
        cmd.extend(["-o", str(exe)])

        rec = run_cmd(cmd, workspace)
        if rec["returncode"] != 0:
            raise RuntimeError(
                f"compile failed for {name}: {rec['stderr']}"
            )

        rec["source_path"] = str(src.relative_to(workspace))
        rec["source_git_blob_sha"] = git_blob_sha(src, workspace)
        rec["executable_path"] = str(exe)
        rec["executable_sha256"] = sha256_file(exe)
        compiled[name] = rec

    return {
        "compiler": cxx,
        "compiler_version": compiler_version,
        "tools": compiled,
    }


def count_rows_and_grid(path: Path) -> dict[str, Any]:
    row_count = 0
    first_ts: int | None = None
    last_ts: int | None = None
    prev_ts: int | None = None
    grid_ok = True
    header: str | None = None

    with path.open("r", encoding="utf-8", newline="") as f:
        header = f.readline().rstrip("\r\n")
        reader = csv.reader(f)
        for row in reader:
            row_count += 1
            ts = int(row[0])
            if first_ts is None:
                first_ts = ts
            if prev_ts is not None and ts - prev_ts != GRID_US:
                grid_ok = False
            prev_ts = ts
            last_ts = ts

    return {
        "header": header,
        "rows": row_count,
        "first_timestamp_us": first_ts,
        "last_timestamp_us": last_ts,
        "grid_250ms_exact": grid_ok,
    }


def parse_features_stderr(stderr: str) -> dict[str, int | None]:
    keys = (
        "rows",
        "book_valid",
        "l0_valid",
        "l1_valid",
        "l2_valid",
        "snapshot_groups",
        "snapshot_masked_bins",
        "unknown_trades",
        "violations",
    )
    out: dict[str, int | None] = {}
    for key in keys:
        m = re.search(rf"\b{re.escape(key)}=([0-9]+)", stderr)
        out[key] = int(m.group(1)) if m else None
    return out


def generate(
    workspace: Path,
    raw_dir: Path,
    derived_dir: Path,
    build_dir: Path,
) -> dict[str, Any]:
    parent_path = workspace / EXP016_ARTIFACT
    if sha256_file(parent_path) != EXP016_ARTIFACT_SHA256:
        raise RuntimeError("EXP016 artifact SHA mismatch")

    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    if parent.get("status") != "SEALED_AUGUST_RAW_INPUT_MANIFEST_CAPTURED":
        raise RuntimeError("EXP016 parent status not ready")

    source_checks = {
        rel: git_blob_sha(workspace / rel, workspace) == expected
        for rel, expected in SOURCE_BLOBS.items()
    }
    if not all(source_checks.values()):
        raise RuntimeError("frozen source Git blob mismatch")

    raws = raw_paths(raw_dir)
    for kind, path in raws.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        if sha256_file(path) != RAW_SHA256[kind]:
            raise RuntimeError(f"raw SHA mismatch: {kind}")

    outputs = derived_paths(derived_dir)
    for path in outputs.values():
        if path.exists() or path.with_suffix(path.suffix + ".partial").exists():
            raise RuntimeError(f"pre-existing EXP017 output: {path}")
    (derived_dir / SYMBOL).mkdir(parents=True, exist_ok=True)

    compiled = compile_tools(workspace, build_dir)
    for name, expected_blob in zip(
        TOOL_ORDER,
        (
            SOURCE_BLOBS["tools/v23_phase0dl_depth250.cpp"],
            SOURCE_BLOBS["tools/v23_phase0dl_flow250.cpp"],
            SOURCE_BLOBS["tools/v23_phase0dl_trade250.cpp"],
            SOURCE_BLOBS["tools/v23_phase0dl_snapshot_scan.cpp"],
            SOURCE_BLOBS["tools/v23_phase0dl_features250.cpp"],
        ),
    ):
        if compiled["tools"][name]["source_git_blob_sha"] != expected_blob:
            raise RuntimeError(f"compiled source mismatch: {name}")

    start, end = day_bounds_us()
    exes = {
        name: Path(compiled["tools"][name]["executable_path"])
        for name in TOOL_ORDER
    }

    commands = [
        (
            "book250",
            [
                str(exes["depth250"]),
                str(raws["incremental_book_L2"]),
                str(outputs["book250"]),
                str(start),
                str(end),
            ],
        ),
        (
            "flow250",
            [
                str(exes["flow250"]),
                str(raws["incremental_book_L2"]),
                str(outputs["flow250"]),
                str(start),
                str(end),
            ],
        ),
        (
            "trade250",
            [
                str(exes["trade250"]),
                str(raws["trades"]),
                str(outputs["trade250"]),
                str(start),
                str(end),
            ],
        ),
        (
            "snapshots",
            [
                str(exes["snapshot_scan"]),
                str(raws["incremental_book_L2"]),
                str(outputs["snapshots"]),
                str(start),
                str(end),
            ],
        ),
        (
            "features250",
            [
                str(exes["features250"]),
                str(outputs["book250"]),
                str(outputs["flow250"]),
                str(outputs["trade250"]),
                str(outputs["snapshots"]),
                str(outputs["features250"]),
                str(start),
                str(end),
                SYMBOL,
            ],
        ),
    ]

    stage_results: dict[str, Any] = {}
    for stage, cmd in commands:
        rec = run_cmd(cmd, workspace)
        stage_results[stage] = rec
        if rec["returncode"] != 0:
            raise RuntimeError(
                f"generation stage failed: {stage}: {rec['stderr']}"
            )

    final_integrity = count_rows_and_grid(outputs["features250"])
    feature_diag = parse_features_stderr(
        stage_results["features250"]["stderr"]
    )

    expected_first = start
    expected_last = end - GRID_US

    checks = {
        "exp016_parent_sha_verified":
            sha256_file(parent_path) == EXP016_ARTIFACT_SHA256,
        "all_raw_sha_verified":
            all(
                sha256_file(raws[k]) == RAW_SHA256[k]
                for k in RAW_SHA256
            ),
        "all_source_git_blobs_verified": all(source_checks.values()),
        "all_compile_returncodes_zero": all(
            rec["returncode"] == 0
            for rec in compiled["tools"].values()
        ),
        "all_generation_returncodes_zero": all(
            rec["returncode"] == 0
            for rec in stage_results.values()
        ),
        "features_rows_exact_345600":
            final_integrity["rows"] == EXPECTED_ROWS,
        "features_first_timestamp_exact":
            final_integrity["first_timestamp_us"] == expected_first,
        "features_last_timestamp_exact":
            final_integrity["last_timestamp_us"] == expected_last,
        "features_grid_exact_250ms":
            final_integrity["grid_250ms_exact"] is True,
        "features_header_matches_frozen_schema_prefix":
            isinstance(final_integrity["header"], str)
            and final_integrity["header"].startswith(FEATURE_HEADER_PREFIX),
        "assembler_reported_rows_345600":
            feature_diag["rows"] == EXPECTED_ROWS,
        "assembler_reported_violations_zero":
            feature_diag["violations"] == 0,
        "all_five_derived_outputs_exist":
            all(path.is_file() for path in outputs.values()),
    }

    artifact_meta = {
        key: {
            "relative_derived_path": str(
                path.relative_to(derived_dir)
            ),
            "sha256": sha256_file(path),
            "size_bytes": int(path.stat().st_size),
        }
        for key, path in outputs.items()
    }

    status = PASS_STATUS if all(checks.values()) else INVALID_STATUS

    return {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "symbol": SYMBOL,
        "day": DAY,
        "exp016_artifact_sha256": EXP016_ARTIFACT_SHA256,
        "raw_sha256": RAW_SHA256,
        "source_git_blob_sha": SOURCE_BLOBS,
        "compiler": compiled,
        "stage_results": stage_results,
        "final_features_integrity": final_integrity,
        "final_features_assembler_diagnostics": feature_diag,
        "derived_artifacts": artifact_meta,
        "checks": checks,
        "august_raw_gzip_decompressed": True,
        "august_raw_csv_parsed_by_frozen_tools": True,
        "features_generated": True,
        "structural_integrity_inspected": True,
        "market_value_distributions_inspected": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
        "network_accessed": False,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Generate and integrity-check frozen Aug-01 BTCUSDT "
            "Phase-L FEATURES250 without predictive scoring"
        )
    )
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--raw-dir", type=Path, required=True)
    ap.add_argument("--derived-dir", type=Path, required=True)
    ap.add_argument("--build-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)

    workspace = args.workspace.resolve()
    output = args.output
    partial = output.with_suffix(output.suffix + ".partial")

    if output.exists() or partial.exists():
        raise RuntimeError("EXP017 result output already exists")

    result = generate(
        workspace=workspace,
        raw_dir=args.raw_dir,
        derived_dir=args.derived_dir,
        build_dir=args.build_dir,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    partial.replace(output)

    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "status": result["status"],
                "features250_sha256":
                    result["derived_artifacts"]["features250"]["sha256"],
                "features250_size_bytes":
                    result["derived_artifacts"]["features250"]["size_bytes"],
                "checks": result["checks"],
                "target_scored": result["target_scored"],
                "model_fit": result["model_fit"],
                "auc_scored": result["auc_scored"],
                "direction_scored": result["direction_scored"],
                "pnl_scored": result["pnl_scored"],
                "network_accessed": result["network_accessed"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

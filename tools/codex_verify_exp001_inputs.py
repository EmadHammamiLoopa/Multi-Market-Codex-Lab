from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from multimarket.v23_phase0dl_score import L0_NAMES, L1_EXTRA_NAMES, L2_EXTRA_NAMES


SYMBOLS = ("BTCUSDT", "ETHUSDT")
DAYS = tuple(date(2026, month, 1).isoformat() for month in range(1, 8))
EXPECTED_ROWS = 345_600
EXPECTED_HEADER = (
    "local_timestamp_us",
    "best_bid",
    "best_ask",
    "mid",
    "book_valid",
    "l0_valid",
    "l1_valid",
    "l2_valid",
    *L0_NAMES,
    *L1_EXTRA_NAMES,
    *L2_EXTRA_NAMES,
)
SEALED_NAMES = {
    "2026-08-01",
    *(f"2026-08-{day:02d}" for day in range(4, 24)),
}


def _sha_and_rows(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    newline_count = 0
    final_byte = b""
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
            newline_count += chunk.count(b"\n")
            final_byte = chunk[-1:]
    total_lines = newline_count + (1 if final_byte and final_byte != b"\n" else 0)
    return digest.hexdigest(), max(total_lines - 1, 0)


def _header(path: Path) -> tuple[str, ...]:
    with path.open("rb") as handle:
        raw = handle.readline()
    return tuple(raw.decode("utf-8").rstrip("\r\n").split(","))


def _manifest_index(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for record in payload.get("files", []):
        key = (str(record.get("symbol")), str(record.get("day")))
        if key in index:
            raise RuntimeError(f"duplicate manifest record: {key}")
        index[key] = record
    return index


def verify(feature_dir: Path, manifest_path: Path) -> dict[str, Any]:
    root = feature_dir.resolve(strict=True)
    manifest_resolved = manifest_path.resolve(strict=True)
    if manifest_resolved.parent != root:
        raise RuntimeError("manifest is not directly inside the frozen feature directory")
    for candidate in [manifest_resolved, *root.glob("*/*")]:
        value = str(candidate)
        if any(sealed in value for sealed in SEALED_NAMES):
            raise RuntimeError(f"sealed path name encountered; not opened: {candidate}")
    expected_paths = {
        root / symbol / f"{day}_FEATURES250.csv"
        for symbol in SYMBOLS
        for day in DAYS
    }
    actual_paths = set(root.glob("*/*_FEATURES250.csv"))
    missing = sorted(str(path) for path in expected_paths - actual_paths)
    unexpected = sorted(str(path) for path in actual_paths - expected_paths)
    if missing or unexpected:
        raise RuntimeError(f"feature path set mismatch: missing={missing}, unexpected={unexpected}")

    manifest_bytes = manifest_resolved.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("phase") != "V2.3-PHASE0DL-L2-MECHANISM":
        raise RuntimeError("unexpected manifest phase")
    if manifest.get("stage") != "FEATURE250_ASSEMBLY_AND_INTEGRITY":
        raise RuntimeError("unexpected manifest stage")
    if manifest.get("development_only") is not True:
        raise RuntimeError("manifest is not marked development_only")
    if manifest.get("confirmation_analytically_opened") is not False:
        raise RuntimeError("manifest says confirmation was analytically opened")
    if manifest.get("expected_jobs") != 14 or manifest.get("pass") is not True:
        raise RuntimeError("manifest did not freeze 14 passing jobs")
    if manifest.get("failures") not in ([], None):
        raise RuntimeError("manifest records failures")
    manifest_records = _manifest_index(manifest)
    expected_keys = {(symbol, day) for symbol in SYMBOLS for day in DAYS}
    if set(manifest_records) != expected_keys:
        raise RuntimeError("manifest symbol/day set does not equal the frozen experiment set")

    files: list[dict[str, Any]] = []
    for symbol in SYMBOLS:
        for day in DAYS:
            path = root / symbol / f"{day}_FEATURES250.csv"
            if path.is_symlink():
                raise RuntimeError(f"symlinked feature input is not allowed: {path}")
            resolved = path.resolve(strict=True)
            if resolved.parent.parent != root:
                raise RuntimeError(f"feature path escapes the frozen directory: {path}")
            manifest_record = manifest_records[(symbol, day)]
            expected_output = f"evidence/v23/phase0dl_features250/{symbol}/{day}_FEATURES250.csv"
            if manifest_record.get("output") != expected_output:
                raise RuntimeError(f"manifest output mismatch: {symbol} {day}")
            if manifest_record.get("pass") is not True:
                raise RuntimeError(f"manifest job did not pass: {symbol} {day}")
            if int(manifest_record.get("rows", -1)) != EXPECTED_ROWS:
                raise RuntimeError(f"manifest row count mismatch: {symbol} {day}")
            header = _header(resolved)
            if header != EXPECTED_HEADER:
                raise RuntimeError(f"header mismatch: {symbol} {day}")
            sha256, rows = _sha_and_rows(resolved)
            if rows != EXPECTED_ROWS:
                raise RuntimeError(f"CSV row count mismatch: {symbol} {day}: {rows}")
            if sha256 != manifest_record.get("sha256"):
                raise RuntimeError(f"SHA-256 mismatch: {symbol} {day}")
            files.append(
                {
                    "symbol": symbol,
                    "day": day,
                    "path": str(resolved),
                    "bytes": resolved.stat().st_size,
                    "rows": rows,
                    "columns": len(header),
                    "sha256": sha256,
                    "manifest_sha256_match": True,
                }
            )
    return {
        "status": "PASS",
        "feature_dir": str(root),
        "immutable_read_only_source": True,
        "manifest_path": str(manifest_resolved),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "manifest_phase": manifest["phase"],
        "manifest_stage": manifest["stage"],
        "development_only": True,
        "confirmation_analytically_opened": False,
        "sealed_paths_opened": False,
        "expected_rows_per_file": EXPECTED_ROWS,
        "expected_columns": len(EXPECTED_HEADER),
        "expected_header": list(EXPECTED_HEADER),
        "files_verified": len(files),
        "total_bytes": sum(record["bytes"] for record in files),
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only provenance check for frozen CODEX-EXP-001 inputs")
    parser.add_argument("--feature-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        payload = verify(args.feature_dir, args.manifest)
        code = 0
    except Exception as exc:
        payload = {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "sealed_paths_opened": False,
        }
        code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"CODEX_EXP001_INPUT_PROVENANCE={payload['status']}")
    print(f"output={args.output}")
    if code == 0:
        print(f"files_verified={payload['files_verified']} total_bytes={payload['total_bytes']}")
    else:
        print(payload["error"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())

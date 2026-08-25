#!/usr/bin/env python3
"""Verify, without regenerating, the sealed-safe EXP002 January--July inputs."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


ALLOWED_DAYS = tuple(f"2026-{month:02d}-01" for month in range(1, 8))
SYMBOLS = ("BTCUSDT", "ETHUSDT")
RAW_TYPES = ("incremental_book_L2", "trades")
RAW_HEADERS = {
    "incremental_book_L2": (
        "exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount"
    ),
    "trades": "exchange,symbol,timestamp,local_timestamp,id,side,price,amount",
}
MANIFESTS = {
    "acquisition": "data/v23_phase0dl_l2_raw/ACQUISITION_MANIFEST.json",
    "raw_audit": "evidence/v23/phase0dl_l2_audit.json",
    "book250": "evidence/v23/phase0dl_book250/BOOK250_MANIFEST.json",
    "flow250": "evidence/v23/phase0dl_flow250/FLOW250_MANIFEST.json",
    "trade250": "evidence/v23/phase0dl_trade250/TRADE250_MANIFEST.json",
    "snapshots": "evidence/v23/phase0dl_snapshots/SNAPSHOT_MANIFEST.json",
    "features250": "evidence/v23/phase0dl_features250/FEATURE250_MANIFEST.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def first_line(path: Path, compressed: bool = False) -> str:
    opener = gzip.open if compressed else open
    with opener(path, "rt", encoding="utf-8", newline="") as handle:
        return handle.readline().rstrip("\r\n")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"manifest is not an object: {path}")
    return value


def ensure_inside(root: Path, path: Path) -> str:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"path escapes original workspace: {resolved_path}") from exc
    if "2026-08" in relative:
        raise ValueError(f"sealed August path rejected: {relative}")
    return relative


def expected_raw_paths() -> set[str]:
    return {
        f"data/v23_phase0dl_l2_raw/{data_type}/{symbol}/{day}.csv.gz"
        for day in ALLOWED_DAYS
        for symbol in SYMBOLS
        for data_type in RAW_TYPES
    }


def expected_derived_paths() -> set[str]:
    paths: set[str] = set()
    for day in ALLOWED_DAYS:
        for symbol in SYMBOLS:
            paths.update(
                {
                    f"evidence/v23/phase0dl_book250/{symbol}/{day}_BOOK250.csv",
                    f"evidence/v23/phase0dl_flow250/{symbol}/{day}_FLOW250.csv",
                    f"evidence/v23/phase0dl_trade250/{symbol}/{day}_TRADE250.csv",
                    f"evidence/v23/phase0dl_snapshots/{symbol}/{day}_SNAPSHOTS.csv",
                    f"evidence/v23/phase0dl_features250/{symbol}/{day}_FEATURES250.csv",
                }
            )
    return paths


def index_files(
    manifest: dict[str, Any], *, data_type: bool = False
) -> dict[tuple[str, ...], dict[str, Any]]:
    indexed: dict[tuple[str, ...], dict[str, Any]] = {}
    for item in manifest.get("files", []):
        day = item.get("day")
        symbol = item.get("symbol")
        if day not in ALLOWED_DAYS or symbol not in SYMBOLS:
            continue
        key = (day, symbol, item.get("data_type")) if data_type else (day, symbol)
        if key in indexed:
            raise ValueError(f"duplicate manifest key: {key}")
        indexed[key] = item
    return indexed


def verify(original_root: Path) -> dict[str, Any]:
    manifests: dict[str, dict[str, Any]] = {}
    for name, relative in MANIFESTS.items():
        path = original_root / relative
        ensure_inside(original_root, path)
        manifests[name] = load_json(path)

    errors: list[str] = []
    checks: list[dict[str, Any]] = []
    raw_allowed = expected_raw_paths()
    derived_allowed = expected_derived_paths()

    for name, manifest in manifests.items():
        if manifest.get("confirmation_analytically_opened") is not False:
            errors.append(f"{name}: confirmation_analytically_opened is not false")
        if name != "acquisition" and manifest.get("pass") is not True:
            errors.append(f"{name}: manifest pass is not true")
        if manifest.get("failures"):
            errors.append(f"{name}: manifest contains failures")

    acquisition = index_files(manifests["acquisition"], data_type=True)
    audit = index_files(manifests["raw_audit"], data_type=True)
    expected_raw_keys = {
        (day, symbol, data_type)
        for day in ALLOWED_DAYS
        for symbol in SYMBOLS
        for data_type in RAW_TYPES
    }
    if set(acquisition) != expected_raw_keys:
        errors.append("acquisition manifest does not contain exactly 28 allowed raw entries")
    if set(audit) != expected_raw_keys:
        errors.append("raw audit does not contain exactly 28 allowed raw entries")

    for key in sorted(expected_raw_keys):
        day, symbol, data_type = key
        acq = acquisition.get(key, {})
        aud = audit.get(key, {})
        relative = acq.get(
            "path",
            f"data/v23_phase0dl_l2_raw/{data_type}/{symbol}/{day}.csv.gz",
        )
        if relative not in raw_allowed:
            errors.append(f"raw path is not whitelisted: {relative}")
            continue
        path = original_root / relative
        ensure_inside(original_root, path)
        record: dict[str, Any] = {
            "kind": "raw",
            "day": day,
            "symbol": symbol,
            "data_type": data_type,
            "path": relative,
            "exists": path.is_file(),
        }
        if not path.is_file():
            errors.append(f"missing raw file: {relative}")
            checks.append(record)
            continue
        print(f"hashing {relative}", file=sys.stderr, flush=True)
        actual_size = path.stat().st_size
        actual_hash = sha256_file(path)
        actual_header = first_line(path, compressed=True)
        record.update(
            {
                "bytes": actual_size,
                "manifest_bytes": acq.get("bytes"),
                "sha256": actual_hash,
                "manifest_sha256": acq.get("sha256"),
                "header": actual_header,
                "audit_rows": aud.get("rows"),
                "audit_bad_rows": aud.get("bad_rows"),
                "audit_pass": aud.get("pass"),
            }
        )
        if actual_size != acq.get("bytes"):
            errors.append(f"size mismatch: {relative}")
        if actual_hash != acq.get("sha256"):
            errors.append(f"hash mismatch: {relative}")
        if actual_header != RAW_HEADERS[data_type] or actual_header != acq.get("header"):
            errors.append(f"header mismatch: {relative}")
        if aud.get("path") != relative or aud.get("pass") is not True:
            errors.append(f"raw audit mismatch: {relative}")
        if aud.get("bad_rows") != 0 or not isinstance(aud.get("rows"), int):
            errors.append(f"raw audit row failure: {relative}")
        checks.append(record)

    derived_specs = {
        "book250": ("output_sha256", "rows"),
        "flow250": ("sha256", None),
        "trade250": ("sha256", None),
        "snapshots": (None, None),
        "features250": ("sha256", "rows"),
    }
    for kind, (hash_field, rows_field) in derived_specs.items():
        indexed = index_files(manifests[kind])
        expected_keys = {(day, symbol) for day in ALLOWED_DAYS for symbol in SYMBOLS}
        if set(indexed) != expected_keys:
            errors.append(f"{kind}: manifest does not contain exactly 14 allowed entries")
        for key in sorted(expected_keys):
            day, symbol = key
            item = indexed.get(key, {})
            relative = item.get("output", "")
            if relative not in derived_allowed:
                errors.append(f"derived path is not whitelisted: {relative or key}")
                continue
            path = original_root / relative
            ensure_inside(original_root, path)
            record = {
                "kind": kind,
                "day": day,
                "symbol": symbol,
                "path": relative,
                "exists": path.is_file(),
            }
            if not path.is_file():
                errors.append(f"missing derived file: {relative}")
                checks.append(record)
                continue
            print(f"hashing {relative}", file=sys.stderr, flush=True)
            actual_hash = sha256_file(path)
            actual_header = first_line(path)
            record.update(
                {
                    "bytes": path.stat().st_size,
                    "sha256": actual_hash,
                    "manifest_sha256": item.get(hash_field) if hash_field else None,
                    "header": actual_header,
                    "manifest_rows": item.get(rows_field) if rows_field else None,
                    "manifest_pass": item.get("pass"),
                }
            )
            if item.get("pass") is not True:
                errors.append(f"derived manifest failure: {relative}")
            if hash_field and actual_hash != item.get(hash_field):
                errors.append(f"hash mismatch: {relative}")
            if rows_field and item.get(rows_field) != 345600:
                errors.append(f"unexpected row count: {relative}")
            if not actual_header:
                errors.append(f"empty derived header: {relative}")
            checks.append(record)

    return {
        "experiment_id": "CODEX-EXP-002",
        "verified_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "original_workspace": str(original_root),
        "sealed_policy": {
            "allowed_days": list(ALLOWED_DAYS),
            "forbidden_day_prefix": "2026-08",
            "august_data_files_opened": 0,
            "regenerated_files": 0,
            "downloaded_files": 0,
        },
        "manifest_paths": MANIFESTS,
        "counts": {
            "raw_expected": 28,
            "raw_verified": sum(c.get("kind") == "raw" and c.get("exists") for c in checks),
            "derived_expected": 70,
            "derived_verified": sum(c.get("kind") != "raw" and c.get("exists") for c in checks),
        },
        "checks": checks,
        "errors": errors,
        "pass": not errors and len(checks) == 98,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.original_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), **result["counts"], "pass": result["pass"], "errors": result["errors"]}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

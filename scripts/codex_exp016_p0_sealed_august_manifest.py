from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "CODEX-EXP-016-P0"
PASS_STATUS = "SEALED_AUGUST_RAW_INPUT_MANIFEST_CAPTURED"
INVALID_STATUS = "INVALID"

DAY = "2026-08-01"
SYMBOL = "BTCUSDT"
DATA_TYPES = ("incremental_book_L2", "trades")

DEFAULT_OUTPUT = Path(
    "evidence/codex/exp016_p0_sealed_august_manifest/"
    "SEALED_AUGUST_RAW_INPUT_MANIFEST.json"
)


@dataclass(frozen=True)
class ManifestConfig:
    experiment_id: str = EXPERIMENT_ID
    symbol: str = SYMBOL
    day: str = DAY
    data_types: tuple[str, ...] = DATA_TYPES


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def expected_paths(raw_dir: Path) -> list[tuple[str, Path]]:
    return [
        (
            data_type,
            raw_dir / data_type / SYMBOL / f"{DAY}.csv.gz",
        )
        for data_type in DATA_TYPES
    ]


def capture_manifest(raw_dir: Path) -> dict[str, Any]:
    pairs = expected_paths(raw_dir)

    checks: dict[str, bool] = {
        "exact_day_is_2026_08_01": DAY == "2026-08-01",
        "btc_only": SYMBOL == "BTCUSDT",
        "exact_two_raw_data_types": DATA_TYPES == (
            "incremental_book_L2",
            "trades",
        ),
        "all_expected_files_exist_before_hashing": all(
            p.is_file() for _, p in pairs
        ),
    }

    guard_fields = {
        "gzip_decompressed": False,
        "csv_parsed": False,
        "header_inspected": False,
        "row_count_inspected": False,
        "timestamp_inspected": False,
        "market_values_inspected": False,
        "features_generated": False,
        "features_scored": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
        "network_accessed": False,
    }

    if not all(checks.values()):
        return {
            "experiment_id": EXPERIMENT_ID,
            "status": INVALID_STATUS,
            "configuration": asdict(ManifestConfig()),
            "files": [],
            "checks": checks,
            "august_raw_files_opened_for_provenance_only": False,
            **guard_fields,
        }

    files: list[dict[str, Any]] = []

    for data_type, path in pairs:
        files.append(
            {
                "day": DAY,
                "symbol": SYMBOL,
                "data_type": data_type,
                "relative_path": (
                    f"{data_type}/{SYMBOL}/{DAY}.csv.gz"
                ),
                "sha256": sha256_file(path),
                "size_bytes": int(path.stat().st_size),
            }
        )

    checks["all_sha256_length_64"] = all(
        len(x["sha256"]) == 64 for x in files
    )
    checks["all_sizes_positive"] = all(
        x["size_bytes"] > 0 for x in files
    )
    checks["data_types_exact_and_ordered"] = tuple(
        x["data_type"] for x in files
    ) == DATA_TYPES
    checks["relative_paths_exact"] = all(
        x["relative_path"]
        == f"{x['data_type']}/{SYMBOL}/{DAY}.csv.gz"
        for x in files
    )

    manifest_core = {
        "configuration": asdict(ManifestConfig()),
        "files": files,
    }
    manifest_sha = canonical_sha256(manifest_core)

    status = (
        PASS_STATUS
        if all(checks.values())
        else INVALID_STATUS
    )

    return {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "configuration": asdict(ManifestConfig()),
        "files": files,
        "manifest_sha256": manifest_sha,
        "checks": checks,
        "august_raw_files_opened_for_provenance_only": True,
        **guard_fields,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture SHA-256 manifest for sealed 2026-08-01 "
            "BTCUSDT Phase-L raw inputs without parsing them"
        )
    )
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    output = args.output
    partial = output.with_suffix(output.suffix + ".partial")

    if output.exists() or partial.exists():
        raise RuntimeError("EXP016 output already exists")

    result = capture_manifest(args.raw_dir)

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
                "file_count": len(result["files"]),
                "manifest_sha256": result.get("manifest_sha256"),
                "august_raw_files_opened_for_provenance_only":
                    result.get(
                        "august_raw_files_opened_for_provenance_only",
                        False,
                    ),
                "gzip_decompressed": result["gzip_decompressed"],
                "csv_parsed": result["csv_parsed"],
                "header_inspected": result["header_inspected"],
                "row_count_inspected": result["row_count_inspected"],
                "timestamp_inspected": result["timestamp_inspected"],
                "market_values_inspected":
                    result["market_values_inspected"],
                "features_generated": result["features_generated"],
                "features_scored": result["features_scored"],
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

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "CODEX-EXP-016-P0"
PASS_STATUS = "SEALED_AUGUST_PHASE_L_INPUT_MANIFEST_CAPTURED"
INVALID_STATUS = "INVALID"

DATES = (
    "2026-08-01",
    "2026-08-04",
    "2026-08-05",
    "2026-08-06",
    "2026-08-07",
    "2026-08-08",
    "2026-08-09",
    "2026-08-10",
    "2026-08-11",
    "2026-08-12",
    "2026-08-13",
    "2026-08-14",
    "2026-08-15",
    "2026-08-16",
    "2026-08-17",
    "2026-08-18",
    "2026-08-19",
    "2026-08-20",
    "2026-08-21",
    "2026-08-22",
    "2026-08-23",
)

SYMBOL = "BTCUSDT"

DEFAULT_OUTPUT = Path(
    "evidence/codex/exp016_p0_sealed_august_manifest/"
    "SEALED_AUGUST_PHASE_L_MANIFEST.json"
)


@dataclass(frozen=True)
class ManifestConfig:
    experiment_id: str = EXPERIMENT_ID
    symbol: str = SYMBOL
    dates: tuple[str, ...] = DATES
    file_suffix: str = "_FEATURES250.csv"


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


def expected_paths(feature_dir: Path) -> list[tuple[str, Path]]:
    return [
        (
            d,
            feature_dir / SYMBOL / f"{d}_FEATURES250.csv",
        )
        for d in DATES
    ]


def capture_manifest(feature_dir: Path) -> dict[str, Any]:
    pairs = expected_paths(feature_dir)

    checks: dict[str, bool] = {
        "exactly_21_frozen_dates": len(DATES) == 21 and len(set(DATES)) == 21,
        "btc_only": SYMBOL == "BTCUSDT",
        "date_scope_exact": DATES == (
            "2026-08-01",
            "2026-08-04",
            "2026-08-05",
            "2026-08-06",
            "2026-08-07",
            "2026-08-08",
            "2026-08-09",
            "2026-08-10",
            "2026-08-11",
            "2026-08-12",
            "2026-08-13",
            "2026-08-14",
            "2026-08-15",
            "2026-08-16",
            "2026-08-17",
            "2026-08-18",
            "2026-08-19",
            "2026-08-20",
            "2026-08-21",
            "2026-08-22",
            "2026-08-23",
        ),
        "all_expected_files_exist_before_hashing": all(
            p.is_file() for _, p in pairs
        ),
    }

    if not all(checks.values()):
        return {
            "experiment_id": EXPERIMENT_ID,
            "status": INVALID_STATUS,
            "configuration": asdict(ManifestConfig()),
            "files": [],
            "checks": checks,
            "csv_parsed": False,
            "row_count_inspected": False,
            "timestamp_inspected": False,
            "market_values_inspected": False,
            "features_scored": False,
            "target_scored": False,
            "model_fit": False,
            "auc_scored": False,
            "direction_scored": False,
            "pnl_scored": False,
            "network_accessed": False,
        }

    files: list[dict[str, Any]] = []

    for d, path in pairs:
        files.append(
            {
                "date": d,
                "relative_path": f"{SYMBOL}/{path.name}",
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
    checks["file_dates_exact_and_ordered"] = tuple(
        x["date"] for x in files
    ) == DATES
    checks["relative_paths_exact"] = all(
        x["relative_path"] == f"{SYMBOL}/{x['date']}_FEATURES250.csv"
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
        "august_files_opened_for_provenance_only": True,
        "csv_parsed": False,
        "row_count_inspected": False,
        "timestamp_inspected": False,
        "market_values_inspected": False,
        "features_scored": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
        "network_accessed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture frozen SHA-256 manifest for sealed August Phase-L inputs"
    )
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    output = args.output
    partial = output.with_suffix(output.suffix + ".partial")

    if output.exists() or partial.exists():
        raise RuntimeError("EXP016 output already exists")

    result = capture_manifest(args.feature_dir)

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
                "august_files_opened_for_provenance_only":
                    result.get("august_files_opened_for_provenance_only", False),
                "csv_parsed": result["csv_parsed"],
                "row_count_inspected": result["row_count_inspected"],
                "timestamp_inspected": result["timestamp_inspected"],
                "market_values_inspected": result["market_values_inspected"],
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

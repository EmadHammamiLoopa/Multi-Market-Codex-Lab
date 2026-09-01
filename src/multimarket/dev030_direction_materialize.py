"""DEV030-P2C deterministic direction-dataset support materialization.

Only provenance, counts, support hashes, and frozen fold structure are made
public. Feature matrices, model logic, predictive metrics, and economic
results do not belong in this layer.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from . import dev030_direction_dataset as dd


EXPERIMENT_ID = "DEV030-P2C"
MATERIALIZATION_VERSION = "v1"
STATUS = "DIRECTION_DATASET_SUPPORT_MANIFEST_MATERIALIZED"

FROZEN_BUILDER_SOURCE_REL = "src/multimarket/dev030_direction_dataset.py"
FROZEN_BUILDER_SOURCE_SHA256 = (
    "54e7315a12cac10413ac2017849466eb3d225282e3dcf48484615409680348c9"
)

REAL_OUTPUT_DIRECTORY = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p2c_direction_materialization_v1"
)
ARTIFACT_FILENAME = "DIRECTION_DATASET_MATERIALIZATION.json"
OUTPUT_PROBE_SUFFIX = ".output-preflight"

AUTHORIZED_DEVELOPMENT_SCOPE = "BTCUSDT consumed Jan-Jul development days only"
FORWARD_DATA_GUARDS = {
    "aug30_analytically_opened": False,
    "sep01_or_later_analytically_opened": False,
    "archive_bucket_opened": False,
    "abundant_love_opened": False,
}

DAY_COUNT_FIELDS = (
    "decision_count",
    "valid_target_count",
    "invalid_target_count",
    "long_first_count",
    "short_first_count",
    "none_count",
    "s0_native_support",
    "s1_native_support",
    "common_support_count",
    "t1_common_support_count",
    "t1_long_common_count",
    "t1_short_common_count",
    "target_future_boundary_valid_count",
    "target_future_boundary_invalid_count",
)
DAY_REASON_FIELDS = (
    "invalid_target_reasons",
    "s0_boundary_exclusion_reasons",
    "s1_boundary_exclusion_reasons",
    "target_future_boundary_exclusion_reasons",
    "s0_invalid_reasons",
    "s1_invalid_reasons",
)
DAY_SUPPORT_HASH_FIELDS = (
    "native_s0_support_sha256",
    "native_s1_support_sha256",
    "common_support_sha256",
    "t1_common_support_sha256",
)
FOLD_SUPPORT_HASH_FIELDS = (
    "train_native_s0_support_sha256",
    "train_native_s1_support_sha256",
    "train_common_support_sha256",
    "train_t1_common_support_sha256",
    "validation_native_s0_support_sha256",
    "validation_native_s1_support_sha256",
    "validation_common_support_sha256",
    "validation_t1_common_support_sha256",
    "train_support_sha256",
    "validation_support_sha256",
)


class DirectionMaterializationError(RuntimeError):
    """Operational, provenance, ordering, or serialization protocol failure."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


@dataclass(frozen=True)
class ArtifactWriteResult:
    output_directory: Path
    artifact_path: Path
    artifact_sha256: str
    artifact_bytes: int


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_frozen_builder_source(
    repository_root: Path,
    *,
    hash_file: Callable[[Path], str] = _sha256_file,
) -> dict[str, Any]:
    path = Path(repository_root).resolve() / FROZEN_BUILDER_SOURCE_REL
    if not path.is_file():
        raise DirectionMaterializationError("frozen_builder_source_missing")
    actual = str(hash_file(path))
    if actual != FROZEN_BUILDER_SOURCE_SHA256:
        raise DirectionMaterializationError("frozen_builder_source_sha256_mismatch")
    return {
        "path": FROZEN_BUILDER_SOURCE_REL,
        "sha256": actual,
        "sha256_verified": True,
    }


def runtime_provenance(*, jan_jul_analytically_opened: bool) -> dict[str, Any]:
    if type(jan_jul_analytically_opened) is not bool:
        raise DirectionMaterializationError(
            "jan_jul_analytically_opened_must_be_builtin_bool"
        )
    return {
        "jan_jul_analytically_opened": jan_jul_analytically_opened,
        "authorized_development_data": {
            "scope": AUTHORIZED_DEVELOPMENT_SCOPE,
            "analytically_loaded": jan_jul_analytically_opened,
        },
        "forward_data_guards": dict(FORWARD_DATA_GUARDS),
        "model_fit_run": False,
        "campaign_1_run": False,
        "pnl_backtest_run": False,
    }


def validate_runtime_provenance(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "jan_jul_analytically_opened",
        "authorized_development_data",
        "forward_data_guards",
        "model_fit_run",
        "campaign_1_run",
        "pnl_backtest_run",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise DirectionMaterializationError("runtime_provenance_schema_mismatch")
    opened = value["jan_jul_analytically_opened"]
    if type(opened) is not bool:
        raise DirectionMaterializationError(
            "jan_jul_analytically_opened_must_be_builtin_bool"
        )
    development = value["authorized_development_data"]
    if (
        not isinstance(development, Mapping)
        or set(development) != {"scope", "analytically_loaded"}
        or development.get("scope") != AUTHORIZED_DEVELOPMENT_SCOPE
        or type(development.get("analytically_loaded")) is not bool
    ):
        raise DirectionMaterializationError("authorized_development_runtime_mismatch")
    if development["analytically_loaded"] is not opened:
        raise DirectionMaterializationError("contradictory_development_runtime_state")
    guards = value["forward_data_guards"]
    if (
        not isinstance(guards, Mapping)
        or set(guards) != set(FORWARD_DATA_GUARDS)
        or any(type(item) is not bool for item in guards.values())
        or any(guards.values())
    ):
        raise DirectionMaterializationError("forward_data_guard_violation")
    for field in ("model_fit_run", "campaign_1_run", "pnl_backtest_run"):
        if type(value[field]) is not bool or value[field] is not False:
            raise DirectionMaterializationError(
                "prohibited_runtime_activity_detected", field
            )
    return normalize_json_safe(dict(value))


def frozen_candidate_keys() -> tuple[dd.CandidateKey, ...]:
    return tuple(
        dd.CandidateKey(target, window, block)
        for target in dd.FROZEN_TARGETS
        for window in dd.FROZEN_WINDOWS_SECONDS
        for block in dd.FROZEN_BLOCKS
    )


def _require_builtin_nonnegative_int(value: Any, *, field: str) -> int:
    if type(value) is not int or value < 0:
        raise DirectionMaterializationError("invalid_count_field", field)
    return value


def _require_fraction(value: Any, *, field: str) -> float | None:
    if value is None:
        return None
    if type(value) is not float or not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise DirectionMaterializationError("invalid_fraction_field", field)
    return value


def _require_sha256(value: Any, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DirectionMaterializationError("invalid_sha256_field", field)
    return value


def _reason_counts(value: Any, *, field: str) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise DirectionMaterializationError("invalid_reason_counts", field)
    result: dict[str, int] = {}
    for reason, count in value.items():
        if not isinstance(reason, str) or not reason:
            raise DirectionMaterializationError("invalid_reason_name", field)
        result[reason] = _require_builtin_nonnegative_int(
            count, field=f"{field}.{reason}"
        )
    return dict(sorted(result.items()))


def _target_public(target: dd.TargetGeometry) -> dict[str, Any]:
    if target not in dd.FROZEN_TARGETS:
        raise DirectionMaterializationError("non_frozen_target")
    return {
        "target_id": target.target_id,
        "horizon_seconds": int(target.horizon_seconds),
        "barrier_bps": int(target.barrier_bps),
    }


def _candidate_key_public(key: dd.CandidateKey) -> dict[str, Any]:
    if key not in frozen_candidate_keys():
        raise DirectionMaterializationError("non_frozen_candidate_key")
    return {
        "target": _target_public(key.target),
        "window_seconds": int(key.window_seconds),
        "block": key.block,
    }


def _candidate_day_public(dataset: dd.CandidateDayDataset) -> dict[str, Any]:
    counts: dict[str, Any] = {}
    for field in DAY_COUNT_FIELDS:
        if field not in dataset.counts:
            raise DirectionMaterializationError("missing_day_count", field)
        counts[field] = _require_builtin_nonnegative_int(
            dataset.counts[field], field=field
        )
    counts["common_support_fraction"] = _require_fraction(
        dataset.counts.get("common_support_fraction"),
        field="common_support_fraction",
    )
    if counts["decision_count"] == 0:
        if counts["common_support_fraction"] is not None:
            raise DirectionMaterializationError(
                "common_support_fraction_reconciliation_failed"
            )
    elif counts["common_support_fraction"] != (
        counts["common_support_count"] / counts["decision_count"]
    ):
        raise DirectionMaterializationError(
            "common_support_fraction_reconciliation_failed"
        )
    if counts["valid_target_count"] + counts["invalid_target_count"] != counts["decision_count"]:
        raise DirectionMaterializationError("target_count_reconciliation_failed")
    if counts["long_first_count"] + counts["short_first_count"] + counts["none_count"] != counts["valid_target_count"]:
        raise DirectionMaterializationError("valid_target_count_reconciliation_failed")
    if counts["target_future_boundary_valid_count"] + counts["target_future_boundary_invalid_count"] != counts["decision_count"]:
        raise DirectionMaterializationError(
            "target_boundary_count_reconciliation_failed"
        )
    if (
        counts["s0_native_support"] > counts["decision_count"]
        or counts["s1_native_support"] > counts["decision_count"]
        or counts["common_support_count"] > counts["decision_count"]
        or counts["common_support_count"] > counts["s0_native_support"]
        or counts["common_support_count"] > counts["s1_native_support"]
        or counts["t1_common_support_count"] > counts["common_support_count"]
    ):
        raise DirectionMaterializationError(
            "support_count_reconciliation_failed"
        )
    if (
        counts["t1_long_common_count"] + counts["t1_short_common_count"]
        != counts["t1_common_support_count"]
    ):
        raise DirectionMaterializationError(
            "t1_class_count_reconciliation_failed"
        )
    if (
        counts["t1_long_common_count"] > counts["long_first_count"]
        or counts["t1_short_common_count"] > counts["short_first_count"]
    ):
        raise DirectionMaterializationError(
            "t1_directional_subset_reconciliation_failed"
        )
    reasons = {
        field: _reason_counts(dataset.counts.get(field), field=field)
        for field in DAY_REASON_FIELDS
    }
    if sum(reasons["invalid_target_reasons"].values()) != counts["invalid_target_count"]:
        raise DirectionMaterializationError(
            "invalid_target_reason_count_reconciliation_failed"
        )
    if sum(reasons["target_future_boundary_exclusion_reasons"].values()) != counts[
        "target_future_boundary_invalid_count"
    ]:
        raise DirectionMaterializationError(
            "target_boundary_reason_count_reconciliation_failed"
        )
    if sum(reasons["s0_invalid_reasons"].values()) != (
        counts["decision_count"] - counts["s0_native_support"]
    ):
        raise DirectionMaterializationError(
            "s0_invalid_reason_count_reconciliation_failed"
        )
    if sum(reasons["s1_invalid_reasons"].values()) != (
        counts["decision_count"] - counts["s1_native_support"]
    ):
        raise DirectionMaterializationError(
            "s1_invalid_reason_count_reconciliation_failed"
        )
    if any(
        count > reasons["s0_invalid_reasons"].get(reason, 0)
        for reason, count in reasons["s0_boundary_exclusion_reasons"].items()
    ):
        raise DirectionMaterializationError(
            "s0_boundary_reason_reconciliation_failed"
        )
    if any(
        count > reasons["s1_invalid_reasons"].get(reason, 0)
        for reason, count in reasons["s1_boundary_exclusion_reasons"].items()
    ):
        raise DirectionMaterializationError(
            "s1_boundary_reason_reconciliation_failed"
        )
    hashes = {
        field: _require_sha256(dataset.support_hashes.get(field), field=field)
        for field in DAY_SUPPORT_HASH_FIELDS
    }
    return {
        "date": dataset.day.isoformat(),
        **counts,
        **reasons,
        "support_sha256": hashes,
    }


def _aggregate_candidate_days(
    datasets: Sequence[dd.CandidateDayDataset],
) -> dict[str, Any]:
    totals = {
        field: int(sum(dataset.counts[field] for dataset in datasets))
        for field in DAY_COUNT_FIELDS
    }
    reasons: dict[str, dict[str, int]] = {}
    for field in DAY_REASON_FIELDS:
        counter: Counter[str] = Counter()
        for dataset in datasets:
            counter.update(_reason_counts(dataset.counts[field], field=field))
        reasons[field] = dict(sorted(counter.items()))
    decisions = totals["decision_count"]
    totals["common_support_fraction"] = (
        float(totals["common_support_count"] / decisions) if decisions else None
    )
    timestamps = np.concatenate(
        [np.asarray(dataset.decision_timestamps_us, dtype=np.int64) for dataset in datasets]
    )
    if len(timestamps) and bool(np.any(np.diff(timestamps) <= 0)):
        raise DirectionMaterializationError("aggregate_timestamps_not_chronological")

    def pooled_hash(mask_name: str) -> str:
        mask = np.concatenate(
            [np.asarray(getattr(dataset, mask_name), dtype=bool) for dataset in datasets]
        )
        return dd.support_sha256(timestamps[mask])

    return {
        **totals,
        **reasons,
        "support_sha256": {
            "native_s0_support_sha256": pooled_hash("s0_valid"),
            "native_s1_support_sha256": pooled_hash("s1_valid"),
            "common_support_sha256": pooled_hash("common_valid"),
            "t1_common_support_sha256": pooled_hash("t1_common_valid"),
        },
    }


def _fold_public(fold: dd.FoldSupport) -> dict[str, Any]:
    if fold.fold not in dd.OUTER_FOLDS:
        raise DirectionMaterializationError("non_frozen_fold")
    if fold.key not in frozen_candidate_keys():
        raise DirectionMaterializationError("non_frozen_fold_candidate")
    hashes = {
        field: _require_sha256(fold.support_hashes.get(field), field=field)
        for field in FOLD_SUPPORT_HASH_FIELDS
    }
    train_long = _require_builtin_nonnegative_int(
        fold.train_class_counts.get("long"), field="train.long"
    )
    train_short = _require_builtin_nonnegative_int(
        fold.train_class_counts.get("short"), field="train.short"
    )
    validation_long = _require_builtin_nonnegative_int(
        fold.validation_class_counts.get("long"), field="validation.long"
    )
    validation_short = _require_builtin_nonnegative_int(
        fold.validation_class_counts.get("short"), field="validation.short"
    )
    train_t1_count = int(len(fold.train_t1_common_timestamps_us))
    validation_t1_count = int(len(fold.validation_t1_common_timestamps_us))
    if train_long + train_short != train_t1_count:
        raise DirectionMaterializationError(
            "train_fold_class_count_reconciliation_failed"
        )
    if validation_long + validation_short != validation_t1_count:
        raise DirectionMaterializationError(
            "validation_fold_class_count_reconciliation_failed"
        )
    return {
        "fold_id": int(fold.fold.fold_id),
        "train_days": [day.isoformat() for day in fold.fold.train_days],
        "validation_day": fold.fold.validation_day.isoformat(),
        "train_t1_count": train_t1_count,
        "validation_t1_count": validation_t1_count,
        "train_class_counts": {"long": train_long, "short": train_short},
        "validation_class_counts": {
            "long": validation_long,
            "short": validation_short,
        },
        "support_sha256": hashes,
    }


def _candidate_public(
    key: dd.CandidateKey,
    per_day: Mapping[date, dd.CandidateDayDataset],
) -> dict[str, Any]:
    if tuple(per_day) != dd.HISTORICAL_DAYS:
        raise DirectionMaterializationError("candidate_day_order_mismatch")
    datasets = [per_day[day] for day in dd.HISTORICAL_DAYS]
    for expected_day, dataset in zip(dd.HISTORICAL_DAYS, datasets, strict=True):
        if dataset.day != expected_day:
            raise DirectionMaterializationError("candidate_day_identity_mismatch")
        if dataset.key != key:
            raise DirectionMaterializationError("candidate_key_mismatch")
    folds = dd.build_fold_supports(per_day)
    if tuple(fold.fold for fold in folds) != dd.OUTER_FOLDS:
        raise DirectionMaterializationError("fold_order_mismatch")
    return {
        **_candidate_key_public(key),
        "per_day": [_candidate_day_public(dataset) for dataset in datasets],
        "aggregate": _aggregate_candidate_days(datasets),
        "folds": [_fold_public(fold) for fold in folds],
    }


def _manifest_public(entries: Sequence[dd.InputManifestEntry]) -> list[dict[str, Any]]:
    if tuple(entry.day for entry in entries) != dd.HISTORICAL_DAYS:
        raise DirectionMaterializationError("input_manifest_order_mismatch")
    return [
        {
            "date": entry.day.isoformat(),
            "path": str(entry.path),
            "bytes": _require_builtin_nonnegative_int(
                entry.bytes, field="input.bytes"
            ),
            "sha256": _require_sha256(entry.sha256, field="input.sha256"),
        }
        for entry in entries
    ]


def _validate_commit(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise DirectionMaterializationError("created_by_commit_must_be_full_sha")
    return value


def build_materialization_payload(
    *,
    created_by_commit: str,
    input_manifest: Sequence[dd.InputManifestEntry],
    candidate_days: Mapping[dd.CandidateKey, Mapping[date, dd.CandidateDayDataset]],
    runtime_state: Mapping[str, Any],
    builder_verification: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    expected_keys = frozen_candidate_keys()
    if set(candidate_days) != set(expected_keys) or len(candidate_days) != len(expected_keys):
        raise DirectionMaterializationError("candidate_grid_mismatch")
    if builder_verification is None:
        raise DirectionMaterializationError("builder_verification_required")
    verification = dict(builder_verification)
    if (
        verification.get("path") != FROZEN_BUILDER_SOURCE_REL
        or verification.get("sha256") != FROZEN_BUILDER_SOURCE_SHA256
        or verification.get("sha256_verified") is not True
    ):
        raise DirectionMaterializationError("invalid_builder_verification")
    payload = {
        "status": STATUS,
        "experiment_id": EXPERIMENT_ID,
        "materialization_version": MATERIALIZATION_VERSION,
        "created_by_commit": _validate_commit(created_by_commit),
        "frozen_builder_source_sha256": FROZEN_BUILDER_SOURCE_SHA256,
        "frozen_builder_source_sha256_verified": True,
        "frozen_first_passage_source_sha256": dd.FIRST_PASSAGE_SOURCE_SHA256,
        "frozen_sequence_feature_source_sha256": dd.SEQUENCE_FEATURE_SOURCE_SHA256,
        "authorized_input_manifest": _manifest_public(input_manifest),
        "configuration": dd.frozen_configuration_metadata(),
        "per_candidate": [
            _candidate_public(key, candidate_days[key]) for key in expected_keys
        ],
        "runtime_provenance": validate_runtime_provenance(runtime_state),
    }
    canonical_json_bytes(payload)
    return payload


def build_candidate_days_from_loaded_days(
    loaded_days: Sequence[Any],
) -> dict[dd.CandidateKey, dict[date, dd.CandidateDayDataset]]:
    if tuple(day.day for day in loaded_days) != dd.HISTORICAL_DAYS:
        raise DirectionMaterializationError("loaded_day_calendar_mismatch")
    result: dict[dd.CandidateKey, dict[date, dd.CandidateDayDataset]] = {}
    for key in frozen_candidate_keys():
        result[key] = {
            day.day: dd.build_candidate_day(
                day,
                target=key.target,
                window_seconds=key.window_seconds,
                block=key.block,
            )
            for day in loaded_days
        }
    return result


def normalize_json_safe(value: Any) -> Any:
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise DirectionMaterializationError("non_finite_json_value")
        return value
    if isinstance(value, np.generic):
        return normalize_json_safe(value.item())
    if isinstance(value, np.ndarray):
        return [normalize_json_safe(item) for item in value.tolist()]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise DirectionMaterializationError("json_mapping_key_not_string")
        return {key: normalize_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_json_safe(item) for item in value]
    raise DirectionMaterializationError("unsupported_json_value", type(value).__name__)


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    normalized = normalize_json_safe(payload)
    try:
        text = json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise DirectionMaterializationError("json_serialization_failed") from exc
    return (text + "\n").encode("utf-8")


def _assert_output_absent(output_directory: Path) -> None:
    path = Path(output_directory)
    if path.exists() or path.is_symlink():
        raise DirectionMaterializationError(
            "output_directory_already_exists", str(path)
        )


def _probe_path(output_directory: Path) -> Path:
    path = Path(output_directory)
    return path.parent / f".{path.name}{OUTPUT_PROBE_SUFFIX}"


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _assert_output_parent_writable(
    output_directory: Path,
    *,
    create_parent: bool = False,
) -> None:
    output = Path(output_directory)
    parent = output.parent
    if not parent.exists():
        if not create_parent:
            raise DirectionMaterializationError("output_parent_missing", str(parent))
        try:
            parent.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise DirectionMaterializationError(
                "output_parent_create_failed", str(exc)
            ) from exc
    if not parent.is_dir():
        raise DirectionMaterializationError("output_parent_not_directory", str(parent))

    probe = _probe_path(output)
    descriptor: int | None = None
    probe_created = False
    primary_failure: OSError | None = None
    cleanup_failure: OSError | None = None
    try:
        descriptor = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        probe_created = True
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(b"DEV030-P2C output preflight\n")
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(parent)
        probe.unlink()
        probe_created = False
        _fsync_directory(parent)
    except OSError as exc:
        primary_failure = exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                if primary_failure is None:
                    primary_failure = exc
        if probe_created:
            try:
                probe.unlink()
                probe_created = False
                _fsync_directory(parent)
            except OSError as exc:
                cleanup_failure = exc
    if cleanup_failure is not None:
        raise DirectionMaterializationError(
            "output_probe_cleanup_failed", str(cleanup_failure)
        ) from cleanup_failure
    if primary_failure is not None:
        raise DirectionMaterializationError(
            "output_parent_preflight_failed", str(primary_failure)
        ) from primary_failure
    if probe.exists() or probe.is_symlink():
        raise DirectionMaterializationError("output_probe_cleanup_failed")


def _atomic_write_file(path: Path, content: bytes) -> str:
    final = Path(path)
    part = final.with_name(final.name + ".part")
    if final.exists() or final.is_symlink():
        raise DirectionMaterializationError("artifact_already_exists", str(final))
    if part.exists() or part.is_symlink():
        raise DirectionMaterializationError(
            "partial_artifact_already_exists", str(part)
        )

    descriptor: int | None = None
    part_created = False
    final_committed = False
    try:
        descriptor = os.open(part, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        part_created = True
        handle = os.fdopen(descriptor, "wb")
        descriptor = None
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(part, final)
        part_created = False
        final_committed = True
        _fsync_directory(final.parent)
    except BaseException as primary_failure:
        close_failure: OSError | None = None
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                close_failure = exc
        if final_committed:
            raise DirectionMaterializationError(
                "artifact_directory_fsync_failed", str(primary_failure)
            ) from primary_failure
        cleanup_failure: OSError | None = None
        if part_created:
            try:
                part.unlink()
                part_created = False
                _fsync_directory(final.parent)
            except OSError as exc:
                cleanup_failure = exc
        if cleanup_failure is not None or close_failure is not None:
            raise DirectionMaterializationError(
                "artifact_partial_cleanup_failed",
                f"write={primary_failure}; close={close_failure}; cleanup={cleanup_failure}",
            ) from (cleanup_failure or close_failure)
        if part.exists() or part.is_symlink():
            raise DirectionMaterializationError(
                "artifact_partial_cleanup_incomplete"
            ) from primary_failure
        if isinstance(primary_failure, DirectionMaterializationError):
            raise
        raise DirectionMaterializationError(
            "artifact_write_failed", str(primary_failure)
        ) from primary_failure
    return hashlib.sha256(content).hexdigest()


def write_materialization_once(
    output_directory: Path,
    payload: Mapping[str, Any],
) -> ArtifactWriteResult:
    output = Path(output_directory)
    content = canonical_json_bytes(payload)
    _assert_output_absent(output)
    output_created = False
    artifact = output / ARTIFACT_FILENAME
    try:
        output.mkdir(mode=0o755)
        output_created = True
        _fsync_directory(output.parent)
        digest = _atomic_write_file(artifact, content)
    except BaseException as primary_failure:
        if not output_created:
            if isinstance(primary_failure, DirectionMaterializationError):
                raise
            raise DirectionMaterializationError(
                "output_directory_create_failed", str(primary_failure)
            ) from primary_failure
        if artifact.exists() or artifact.is_symlink():
            raise
        try:
            remaining = tuple(output.iterdir())
        except OSError as cleanup_failure:
            raise DirectionMaterializationError(
                "output_directory_cleanup_failed",
                f"write={primary_failure}; cleanup={cleanup_failure}",
            ) from cleanup_failure
        if remaining:
            raise DirectionMaterializationError(
                "output_directory_cleanup_not_empty",
                f"write={primary_failure}; remaining={[item.name for item in remaining]}",
            ) from primary_failure
        try:
            output.rmdir()
            _fsync_directory(output.parent)
        except OSError as cleanup_failure:
            raise DirectionMaterializationError(
                "output_directory_cleanup_failed",
                f"write={primary_failure}; cleanup={cleanup_failure}",
            ) from cleanup_failure
        if output.exists() or output.is_symlink():
            raise DirectionMaterializationError(
                "output_directory_cleanup_incomplete"
            ) from primary_failure
        raise
    return ArtifactWriteResult(output, artifact, digest, len(content))


def run_materialization(
    *,
    workspace: Path,
    output_directory: Path,
    created_by_commit: str,
    manifest_verifier: Callable[[], Sequence[dd.InputManifestEntry]] = dd.verify_input_manifest,
    analytical_day_loader: Callable[[], Sequence[Any]] = dd.load_authorized_days,
    candidate_builder: Callable[
        [Sequence[Any]],
        Mapping[dd.CandidateKey, Mapping[date, dd.CandidateDayDataset]],
    ] = build_candidate_days_from_loaded_days,
    payload_builder: Callable[..., Mapping[str, Any]] = build_materialization_payload,
    builder_hash_file: Callable[[Path], str] = _sha256_file,
    require_canonical_output: bool = True,
) -> ArtifactWriteResult:
    """Future real orchestration; tests inject synthetic manifests and days."""

    output = Path(output_directory)
    if not require_canonical_output and output == REAL_OUTPUT_DIRECTORY:
        raise DirectionMaterializationError("canonical_output_requires_real_mode")
    if require_canonical_output:
        production_dependencies = (
            ("manifest_verifier", manifest_verifier, dd.verify_input_manifest),
            ("analytical_day_loader", analytical_day_loader, dd.load_authorized_days),
            (
                "candidate_builder",
                candidate_builder,
                build_candidate_days_from_loaded_days,
            ),
            ("payload_builder", payload_builder, build_materialization_payload),
            ("builder_hash_file", builder_hash_file, _sha256_file),
        )
        for dependency_name, supplied, expected in production_dependencies:
            if supplied is not expected:
                raise DirectionMaterializationError(
                    "canonical_dependency_override_forbidden",
                    dependency_name,
                )
    if require_canonical_output and output != REAL_OUTPUT_DIRECTORY:
        raise DirectionMaterializationError("noncanonical_output_directory")
    _assert_output_absent(output)
    _assert_output_parent_writable(output)
    builder_verification = verify_frozen_builder_source(
        workspace, hash_file=builder_hash_file
    )
    manifest = tuple(manifest_verifier())
    loaded_days = tuple(analytical_day_loader())
    if tuple(day.day for day in loaded_days) != dd.HISTORICAL_DAYS:
        raise DirectionMaterializationError("loaded_day_calendar_mismatch")
    real_runtime_state = runtime_provenance(jan_jul_analytically_opened=True)
    candidates = candidate_builder(loaded_days)
    payload = payload_builder(
        created_by_commit=created_by_commit,
        input_manifest=manifest,
        candidate_days=candidates,
        runtime_state=real_runtime_state,
        builder_verification=builder_verification,
    )
    return write_materialization_once(output, payload)


__all__ = [
    "ARTIFACT_FILENAME",
    "EXPERIMENT_ID",
    "FROZEN_BUILDER_SOURCE_SHA256",
    "MATERIALIZATION_VERSION",
    "REAL_OUTPUT_DIRECTORY",
    "STATUS",
    "ArtifactWriteResult",
    "DirectionMaterializationError",
    "build_materialization_payload",
    "canonical_json_bytes",
    "frozen_candidate_keys",
    "normalize_json_safe",
    "run_materialization",
    "runtime_provenance",
    "validate_runtime_provenance",
    "verify_frozen_builder_source",
    "write_materialization_once",
]

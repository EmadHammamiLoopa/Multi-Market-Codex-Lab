"""DEV031-P1A exact-P3-support raw event/depth materialization.

This stage creates no predictive metric and fits no model.  It reconstructs
the frozen DEV030-P3 selected A/120s/16bp/32s/PRICE T1 support, extracts the
predeclared 26-feature EVENT_DEPTH block from raw L2, and requires exact
timestamp/label/support preservation.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np

from . import dev030_direction_dataset as dd
from .v23_phase0dl_score import _load_day


EXPERIMENT_ID = "DEV031-P1A"
DESIGN_VERSION = "event-depth-materialization-v1"
STATUS_PASS = "EVENT_DEPTH_EXACT_P3_SUPPORT_MATERIALIZED"
STATUS_FAIL = "FAIL_EVENT_DEPTH_EXACT_P3_SUPPORT_NOT_PRESERVED"
STATUS_INCONCLUSIVE = "INCONCLUSIVE_EVENT_DEPTH_MATERIALIZATION"

TARGET_ID = "A"
HORIZON_SECONDS = 120
BARRIER_BPS = 16
WINDOW_SECONDS = 32
BLOCK = "PRICE"

RAW_ROOT = Path(
    "/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw/"
    "incremental_book_L2/BTCUSDT"
)

P0A_ARTIFACT = Path(
    "/home/emadh/Multi-Market/evidence/dev031_p0a_event_depth_raw_l2_v1/"
    "DEV031_P0A_EVENT_DEPTH_RAW_L2_RESULT.json"
)
P0A_SHA256 = "97f43dccd6a119867aced5de372121a87bc912c20b26b6f032333b761c82cc01"

P2C_ARTIFACT = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p2c_direction_materialization_v1/"
    "DIRECTION_DATASET_MATERIALIZATION.json"
)
P2C_SHA256 = "a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0"

P3_ARTIFACT = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/"
    "DEV030_P3_CAMPAIGN1_RESULT.json"
)
P3_SHA256 = "f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e"

TOOL_REL = Path("tools/dev031_p1a_event_depth.cpp")

REAL_OUTPUT_DIRECTORY = Path(
    "/home/emadh/Multi-Market/evidence/dev031_p1a_event_depth_materialization_v1"
)
MANIFEST_FILENAME = "DEV031_P1A_EVENT_DEPTH_MATERIALIZATION.json"

FORWARD_GUARDS = {
    "aug01_opened": False,
    "aug30_opened": False,
    "sep01_or_later_opened": False,
    "railway_opened": False,
    "archive_bucket_opened": False,
    "abundant_love_opened": False,
    "downloads_or_acquisition_run": False,
    "model_fit_run": False,
    "predictive_metrics_run": False,
    "pnl_run": False,
    "exp024_filter_or_feature_used": False,
    "p4_composition_run": False,
}

EVENT_DEPTH_FEATURE_NAMES = (
    "obi_l20",
    "obi_l50",
    "log1p_bid_depth_l20",
    "log1p_ask_depth_l20",
    "log1p_bid_depth_l50",
    "log1p_ask_depth_l50",
    "bid_depth_concentration_l10_l50",
    "ask_depth_concentration_l10_l50",
    "flow_imbalance_1s_5bp",
    "flow_imbalance_1s_15bp",
    "flow_imbalance_1s_50bp",
    "flow_imbalance_4s_5bp",
    "flow_imbalance_4s_15bp",
    "flow_imbalance_4s_50bp",
    "flow_imbalance_16s_5bp",
    "flow_imbalance_16s_15bp",
    "flow_imbalance_16s_50bp",
    "flow_imbalance_32s_5bp",
    "flow_imbalance_32s_15bp",
    "flow_imbalance_32s_50bp",
    "insert_pressure_32s",
    "delete_pressure_32s",
    "replenish_pressure_32s",
    "deplete_pressure_32s",
    "log1p_non_snapshot_updates_32s",
    "log1p_distinct_local_groups_32s",
)

EXTRACTOR_HEADER = (
    "local_timestamp_us",
    "feature_valid",
) + EVENT_DEPTH_FEATURE_NAMES


class P1AMaterializationError(RuntimeError):
    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


@dataclass(frozen=True)
class DaySupport:
    day: date
    timestamps_us: np.ndarray
    labels: np.ndarray
    price_feature_names: tuple[str, ...]
    price_values: np.ndarray
    candidate: dd.CandidateDayDataset


@dataclass(frozen=True)
class ExtractedDay:
    day: date
    timestamps_us: np.ndarray
    event_values: np.ndarray
    stderr: str


@dataclass(frozen=True)
class ArtifactWriteResult:
    output_directory: Path
    artifact_path: Path
    artifact_sha256: str
    artifact_bytes: int


def _sha256_file(path: Path, *, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_verified(path: Path, expected_sha256: str, missing_reason: str, hash_reason: str) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise P1AMaterializationError(missing_reason, str(p))
    actual = _sha256_file(p)
    if actual != expected_sha256:
        raise P1AMaterializationError(hash_reason, f"expected={expected_sha256} actual={actual}")
    try:
        value = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise P1AMaterializationError("artifact_json_invalid", str(p)) from exc
    if not isinstance(value, dict):
        raise P1AMaterializationError("artifact_root_not_object", str(p))
    return value


def verify_artifacts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    p0a = _json_verified(P0A_ARTIFACT, P0A_SHA256, "p0a_artifact_missing", "p0a_artifact_sha256_mismatch")
    p2c = _json_verified(P2C_ARTIFACT, P2C_SHA256, "p2c_artifact_missing", "p2c_artifact_sha256_mismatch")
    p3a = _json_verified(P3_ARTIFACT, P3_SHA256, "p3_artifact_missing", "p3_artifact_sha256_mismatch")
    if p0a.get("status") != "DATA_READY_EVENT_DEPTH_RAW_L2" or p0a.get("pass") is not True:
        raise P1AMaterializationError("p0a_terminal_status_mismatch")
    if p2c.get("status") != "DIRECTION_DATASET_SUPPORT_MANIFEST_MATERIALIZED":
        raise P1AMaterializationError("p2c_terminal_status_mismatch")
    expected_selected = {
        "target": {
            "target_id": TARGET_ID,
            "horizon_seconds": HORIZON_SECONDS,
            "barrier_bps": BARRIER_BPS,
        },
        "window_seconds": WINDOW_SECONDS,
        "block": BLOCK,
    }
    if p3a.get("selected_for_next_development_stage") != expected_selected:
        raise P1AMaterializationError(
            "p3_selected_candidate_mismatch",
            repr(p3a.get("selected_for_next_development_stage")),
        )
    return p0a, p2c, p3a


def _selected_trial(p3_artifact: Mapping[str, Any]) -> Mapping[str, Any]:
    expected = {
        "target": {
            "target_id": TARGET_ID,
            "horizon_seconds": HORIZON_SECONDS,
            "barrier_bps": BARRIER_BPS,
        },
        "window_seconds": WINDOW_SECONDS,
        "block": BLOCK,
    }
    found: list[Mapping[str, Any]] = []
    for item in p3_artifact.get("trial_ledger", []):
        if not isinstance(item, Mapping):
            continue
        actual = {
            "target": item.get("target"),
            "window_seconds": item.get("window_seconds"),
            "block": item.get("block"),
        }
        if actual == expected:
            found.append(item)
    if len(found) != 1:
        raise P1AMaterializationError("p3_selected_trial_not_unique", str(len(found)))
    return found[0]


def _p0a_raw_manifest(p0a: Mapping[str, Any]) -> dict[date, dict[str, Any]]:
    result: dict[date, dict[str, Any]] = {}
    for item in p0a.get("days", []):
        try:
            d = date.fromisoformat(str(item["day"]))
        except Exception as exc:
            raise P1AMaterializationError("p0a_day_invalid") from exc
        result[d] = dict(item)
    if tuple(sorted(result)) != dd.HISTORICAL_DAYS:
        raise P1AMaterializationError("p0a_day_calendar_mismatch")
    return result


def verify_raw_manifest_against_p0a(p0a: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    p0days = _p0a_raw_manifest(p0a)
    rows: list[dict[str, Any]] = []

    def one(d: date) -> dict[str, Any]:
        path = RAW_ROOT / f"{d.isoformat()}.csv.gz"
        frozen = p0days[d]
        if str(path) != str(frozen.get("path")):
            raise P1AMaterializationError("raw_path_mismatch", d.isoformat())
        if not path.is_file():
            raise P1AMaterializationError("raw_file_missing", str(path))
        actual_bytes = int(path.stat().st_size)
        if actual_bytes != int(frozen.get("bytes")):
            raise P1AMaterializationError("raw_bytes_mismatch", d.isoformat())
        actual_sha = _sha256_file(path)
        if actual_sha != str(frozen.get("sha256")):
            raise P1AMaterializationError("raw_sha256_mismatch", d.isoformat())
        return {
            "day": d.isoformat(),
            "path": str(path),
            "bytes": actual_bytes,
            "sha256": actual_sha,
        }

    with ThreadPoolExecutor(max_workers=7) as pool:
        future = {pool.submit(one, d): d for d in dd.HISTORICAL_DAYS}
        by_day: dict[date, dict[str, Any]] = {}
        for f in as_completed(future):
            d = future[f]
            by_day[d] = f.result()
    for d in dd.HISTORICAL_DAYS:
        rows.append(by_day[d])
    return tuple(rows)


def _target() -> dd.TargetGeometry:
    for target in dd.FROZEN_TARGETS:
        if (
            target.target_id == TARGET_ID
            and target.horizon_seconds == HORIZON_SECONDS
            and target.barrier_bps == BARRIER_BPS
        ):
            return target
    raise P1AMaterializationError("frozen_target_missing")


def build_selected_p3_support() -> tuple[dict[date, DaySupport], tuple[dd.InputManifestEntry, ...], dict[str, Any]]:
    dd.verify_frozen_source_identities(Path(__file__).resolve().parents[2])
    dd.verify_phase0dl_feature_order()
    entries = tuple(dd.verify_input_manifest())
    by_entry = {item.day: item for item in entries}
    if tuple(sorted(by_entry)) != dd.HISTORICAL_DAYS:
        raise P1AMaterializationError("aggregated_input_calendar_mismatch")

    result: dict[date, DaySupport] = {}
    candidate_days: dict[date, dd.CandidateDayDataset] = {}
    target = _target()

    for d in dd.HISTORICAL_DAYS:
        entry = by_entry[d]
        day_obj = _load_day(entry.path, d)
        candidate = dd.build_candidate_day(
            day_obj,
            target=target,
            window_seconds=WINDOW_SECONDS,
            block=BLOCK,
        )
        mask = np.asarray(candidate.t1_common_valid, dtype=bool)
        ts = np.asarray(candidate.decision_timestamps_us, dtype=np.int64)[mask]
        labels = np.asarray(candidate.t1_labels, dtype=np.int8)[mask]
        price = np.asarray(candidate.s1_values, dtype=np.float64)[mask]
        names = tuple(candidate.s1_feature_names)
        if len(names) != 23 or price.shape != (len(ts), 23):
            raise P1AMaterializationError("p3_price_feature_shape_mismatch", d.isoformat())
        if len(ts) and bool(np.any(np.diff(ts) <= 0)):
            raise P1AMaterializationError("p3_support_not_chronological", d.isoformat())
        if not bool(np.all(np.isfinite(price))):
            raise P1AMaterializationError("p3_price_nonfinite", d.isoformat())
        if not bool(np.all((labels == 0) | (labels == 1))):
            raise P1AMaterializationError("p3_t1_label_invalid", d.isoformat())
        result[d] = DaySupport(d, ts, labels, names, price, candidate)
        candidate_days[d] = candidate
        del day_obj

    support_contract = candidate_support_contract(candidate_days)
    return result, entries, support_contract


def candidate_support_contract(
    per_day: Mapping[date, dd.CandidateDayDataset],
) -> dict[str, Any]:
    if tuple(per_day) != dd.HISTORICAL_DAYS:
        raise P1AMaterializationError("candidate_day_order_mismatch")
    day_entries: list[dict[str, Any]] = []
    for d in dd.HISTORICAL_DAYS:
        dataset = per_day[d]
        ts = np.asarray(dataset.decision_timestamps_us, dtype=np.int64)
        s0 = np.asarray(dataset.s0_valid, dtype=bool)
        s1 = np.asarray(dataset.s1_valid, dtype=bool)
        common = np.asarray(dataset.common_valid, dtype=bool)
        t1 = np.asarray(dataset.t1_common_valid, dtype=bool)
        labels = np.asarray(dataset.t1_labels, dtype=np.int8)
        day_entries.append(
            {
                "date": d.isoformat(),
                "t1_common_support_count": int(np.count_nonzero(t1)),
                "t1_long_common_count": int(np.count_nonzero(t1 & (labels == 1))),
                "t1_short_common_count": int(np.count_nonzero(t1 & (labels == 0))),
                "support_sha256": {
                    "native_s0_support_sha256": dd.support_sha256(ts[s0]),
                    "native_s1_support_sha256": dd.support_sha256(ts[s1]),
                    "common_support_sha256": dd.support_sha256(ts[common]),
                    "t1_common_support_sha256": dd.support_sha256(ts[t1]),
                },
            }
        )
    folds = dd.build_fold_supports(per_day)
    fold_entries = [
        {
            "fold_id": int(item.fold.fold_id),
            "train_days": [d.isoformat() for d in item.fold.train_days],
            "validation_day": item.fold.validation_day.isoformat(),
            "train_t1_count": int(len(item.train_t1_common_timestamps_us)),
            "validation_t1_count": int(len(item.validation_t1_common_timestamps_us)),
            "train_class_counts": dict(item.train_class_counts),
            "validation_class_counts": dict(item.validation_class_counts),
            "support_sha256": dict(item.support_hashes),
        }
        for item in folds
    ]
    return {"per_day": day_entries, "folds": fold_entries}


def reconcile_p3_support_contract(
    reconstructed: Mapping[str, Any],
    p3_artifact: Mapping[str, Any],
) -> None:
    trial = _selected_trial(p3_artifact)
    frozen = trial.get("support_contract")
    if reconstructed != frozen:
        raise P1AMaterializationError("p3_support_contract_mismatch")


def _compile_tool(workspace: Path, build_dir: Path) -> Path:
    root = Path(workspace).resolve()
    source = root / TOOL_REL
    if not source.is_file():
        raise P1AMaterializationError("extractor_source_missing", str(source))
    cxx = shutil.which("g++")
    if cxx is None:
        raise P1AMaterializationError("gpp_missing")
    build = Path(build_dir)
    build.mkdir(parents=True, exist_ok=True)
    exe = build / "dev031_p1a_event_depth"
    stamp = build / "dev031_p1a_event_depth.source.sha256"
    source_sha = _sha256_file(source)
    if exe.is_file() and stamp.is_file() and stamp.read_text().strip() == source_sha:
        return exe
    cmd = [cxx, "-std=c++17", "-O3", "-DNDEBUG", str(source), "-lz", "-o", str(exe)]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0:
        raise P1AMaterializationError("extractor_compile_failed", completed.stderr)
    stamp.write_text(source_sha + "\n")
    return exe


def _write_support_file(path: Path, timestamps: np.ndarray) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        handle.write("local_timestamp_us\n")
        for ts in np.asarray(timestamps, dtype=np.int64).tolist():
            handle.write(f"{int(ts)}\n")


def _parse_extractor_output(path: Path, support: DaySupport, stderr: str) -> ExtractedDay:
    timestamps: list[int] = []
    values: list[list[float]] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = tuple(next(reader))
        except StopIteration as exc:
            raise P1AMaterializationError("extractor_output_missing_header") from exc
        if header != EXTRACTOR_HEADER:
            raise P1AMaterializationError("extractor_header_mismatch", repr(header))
        for row in reader:
            if len(row) != len(EXTRACTOR_HEADER):
                raise P1AMaterializationError("extractor_row_width_mismatch")
            timestamps.append(int(row[0]))
            if row[1] != "1":
                raise P1AMaterializationError(
                    "event_depth_support_not_finite",
                    f"{support.day.isoformat()}@{row[0]}",
                )
            values.append([float(item) for item in row[2:]])
    ts = np.asarray(timestamps, dtype=np.int64)
    matrix = np.asarray(values, dtype=np.float64)
    if not np.array_equal(ts, support.timestamps_us):
        raise P1AMaterializationError("event_depth_timestamp_support_mismatch", support.day.isoformat())
    if matrix.shape != (len(ts), 26):
        raise P1AMaterializationError("event_depth_matrix_shape_mismatch", support.day.isoformat())
    validate_event_depth_values(matrix)
    return ExtractedDay(support.day, ts, matrix, stderr)


def validate_event_depth_values(values: Any) -> np.ndarray:
    x = np.asarray(values, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 26:
        raise P1AMaterializationError("event_depth_feature_count_mismatch")
    if not bool(np.all(np.isfinite(x))):
        raise P1AMaterializationError("event_depth_nonfinite")
    bounded = x[:, list(range(0, 2)) + list(range(8, 24))]
    if bool(np.any(bounded < -1.000000000001)) or bool(np.any(bounded > 1.000000000001)):
        raise P1AMaterializationError("bounded_event_feature_out_of_range")
    concentration = x[:, 6:8]
    if bool(np.any(concentration < -1e-12)) or bool(np.any(concentration > 1.000000000001)):
        raise P1AMaterializationError("depth_concentration_out_of_range")
    log_features = x[:, [2, 3, 4, 5, 24, 25]]
    if bool(np.any(log_features < -1e-12)):
        raise P1AMaterializationError("log_feature_negative")
    return x


def extract_all_days(
    *,
    exe: Path,
    supports: Mapping[date, DaySupport],
    temp_dir: Path,
) -> dict[date, ExtractedDay]:
    temp = Path(temp_dir)
    temp.mkdir(parents=True, exist_ok=True)

    jobs: dict[date, tuple[Path, Path]] = {}
    for d in dd.HISTORICAL_DAYS:
        support_path = temp / f"{d.isoformat()}_support.csv"
        output_path = temp / f"{d.isoformat()}_event_depth.csv"
        _write_support_file(support_path, supports[d].timestamps_us)
        jobs[d] = (support_path, output_path)

    def one(d: date) -> ExtractedDay:
        support_path, output_path = jobs[d]
        raw = RAW_ROOT / f"{d.isoformat()}.csv.gz"
        completed = subprocess.run(
            [str(exe), str(raw), str(support_path), str(output_path)],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise P1AMaterializationError(
                "extractor_execution_failed",
                f"{d.isoformat()} rc={completed.returncode} stderr={completed.stderr}",
            )
        return _parse_extractor_output(output_path, supports[d], completed.stderr.strip())

    by_day: dict[date, ExtractedDay] = {}
    with ThreadPoolExecutor(max_workers=7) as pool:
        future = {pool.submit(one, d): d for d in dd.HISTORICAL_DAYS}
        for f in as_completed(future):
            d = future[f]
            by_day[d] = f.result()
    return {d: by_day[d] for d in dd.HISTORICAL_DAYS}


def _hash_int64(values: Any, domain: bytes) -> str:
    a = np.asarray(values, dtype=np.int64)
    return hashlib.sha256(domain + a.astype(">i8", copy=False).tobytes(order="C")).hexdigest()


def _hash_int8(values: Any, domain: bytes) -> str:
    a = np.asarray(values, dtype=np.int8)
    return hashlib.sha256(domain + a.tobytes(order="C")).hexdigest()


def _hash_float64(values: Any, domain: bytes) -> str:
    a = np.asarray(values, dtype=np.float64)
    return hashlib.sha256(domain + a.astype(">f8", copy=False).tobytes(order="C")).hexdigest()


def _write_day_csv(path: Path, support: DaySupport, event: ExtractedDay) -> None:
    if not np.array_equal(support.timestamps_us, event.timestamps_us):
        raise P1AMaterializationError("day_write_support_mismatch")
    header = (
        ("local_timestamp_us", "t1_label")
        + support.price_feature_names
        + EVENT_DEPTH_FEATURE_NAMES
    )
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        for i in range(len(support.timestamps_us)):
            writer.writerow(
                [
                    str(int(support.timestamps_us[i])),
                    str(int(support.labels[i])),
                    *[format(float(v), ".17g") for v in support.price_values[i]],
                    *[format(float(v), ".17g") for v in event.event_values[i]],
                ]
            )


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _fold_summary(supports: Mapping[date, DaySupport]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for fold in dd.OUTER_FOLDS:
        train_ts = np.concatenate([supports[d].timestamps_us for d in fold.train_days])
        train_y = np.concatenate([supports[d].labels for d in fold.train_days])
        val_ts = supports[fold.validation_day].timestamps_us
        val_y = supports[fold.validation_day].labels
        result.append(
            {
                "fold_id": int(fold.fold_id),
                "train_days": [d.isoformat() for d in fold.train_days],
                "validation_day": fold.validation_day.isoformat(),
                "train_support": int(len(train_ts)),
                "validation_support": int(len(val_ts)),
                "train_long": int(np.count_nonzero(train_y == 1)),
                "train_short": int(np.count_nonzero(train_y == 0)),
                "validation_long": int(np.count_nonzero(val_y == 1)),
                "validation_short": int(np.count_nonzero(val_y == 0)),
                "train_support_sha256": dd.support_sha256(train_ts),
                "validation_support_sha256": dd.support_sha256(val_ts),
            }
        )
    return result


def run_p1a(
    *,
    workspace: Path,
    execution_commit: str,
    output_directory: Path = REAL_OUTPUT_DIRECTORY,
    require_canonical_output: bool = True,
) -> ArtifactWriteResult:
    output = Path(output_directory)
    if require_canonical_output and output != REAL_OUTPUT_DIRECTORY:
        raise P1AMaterializationError("noncanonical_output_directory")
    if not require_canonical_output and output == REAL_OUTPUT_DIRECTORY:
        raise P1AMaterializationError("canonical_output_requires_real_mode")
    if output.exists() or output.is_symlink():
        raise P1AMaterializationError("output_directory_already_exists")
    if (
        not isinstance(execution_commit, str)
        or len(execution_commit) != 40
        or any(ch not in "0123456789abcdef" for ch in execution_commit)
    ):
        raise P1AMaterializationError("execution_commit_must_be_full_sha")
    if any(FORWARD_GUARDS.values()):
        raise P1AMaterializationError("runtime_guard_violation")

    p0a, _p2c, p3_artifact = verify_artifacts()
    raw_manifest = verify_raw_manifest_against_p0a(p0a)
    supports, agg_manifest, contract = build_selected_p3_support()
    reconcile_p3_support_contract(contract, p3_artifact)

    build_dir = Path(workspace).resolve() / ".build" / "dev031_p1a"
    exe = _compile_tool(Path(workspace), build_dir)

    with tempfile.TemporaryDirectory(prefix="dev031_p1a_") as td:
        extracted = extract_all_days(exe=exe, supports=supports, temp_dir=Path(td))

        # All scientific checks complete before the canonical output directory exists.
        day_records: list[dict[str, Any]] = []
        staging = output.parent / f".{output.name}.part-{os.getpid()}"
        if staging.exists() or staging.is_symlink():
            raise P1AMaterializationError("staging_directory_preexists")
        staging.mkdir(mode=0o755)
        try:
            for d in dd.HISTORICAL_DAYS:
                support = supports[d]
                event = extracted[d]
                day_file = staging / f"{d.isoformat()}_P3_EVENT_DEPTH.csv"
                _write_day_csv(day_file, support, event)
                day_records.append(
                    {
                        "day": d.isoformat(),
                        "rows": int(len(support.timestamps_us)),
                        "long": int(np.count_nonzero(support.labels == 1)),
                        "short": int(np.count_nonzero(support.labels == 0)),
                        "support_sha256": dd.support_sha256(support.timestamps_us),
                        "timestamp_bytes_sha256": _hash_int64(
                            support.timestamps_us, b"DEV031-P1A-TS-V1\x00"
                        ),
                        "label_sha256": _hash_int8(
                            support.labels, b"DEV031-P1A-LABEL-V1\x00"
                        ),
                        "price_matrix_sha256": _hash_float64(
                            support.price_values, b"DEV031-P1A-PRICE23-V1\x00"
                        ),
                        "event_depth_matrix_sha256": _hash_float64(
                            event.event_values, b"DEV031-P1A-EVENT26-V1\x00"
                        ),
                        "file": day_file.name,
                        "file_sha256": _sha256_file(day_file),
                        "file_bytes": int(day_file.stat().st_size),
                        "extractor_stderr": event.stderr,
                    }
                )

            payload = {
                "experiment_id": EXPERIMENT_ID,
                "design_version": DESIGN_VERSION,
                "status": STATUS_PASS,
                "pass": True,
                "execution_commit": execution_commit,
                "selected_configuration": {
                    "symbol": "BTCUSDT",
                    "task": "DIRECTION_GIVEN_TOUCH",
                    "target_id": TARGET_ID,
                    "horizon_seconds": HORIZON_SECONDS,
                    "barrier_bps": BARRIER_BPS,
                    "window_seconds": WINDOW_SECONDS,
                    "block": BLOCK,
                    "p3_price_feature_count": 23,
                    "event_depth_feature_count": 26,
                    "future_p1b_augmented_feature_count": 49,
                },
                "feature_names": {
                    "price": list(next(iter(supports.values())).price_feature_names),
                    "event_depth": list(EVENT_DEPTH_FEATURE_NAMES),
                },
                "provenance": {
                    "p0a_artifact": {"path": str(P0A_ARTIFACT), "sha256": P0A_SHA256},
                    "p2c_artifact": {"path": str(P2C_ARTIFACT), "sha256": P2C_SHA256},
                    "p3_artifact": {"path": str(P3_ARTIFACT), "sha256": P3_SHA256},
                    "extractor_source": str(TOOL_REL),
                    "extractor_source_sha256": _sha256_file(Path(workspace) / TOOL_REL),
                    "raw_manifest": list(raw_manifest),
                    "aggregated_input_manifest": [
                        {
                            "day": item.day.isoformat(),
                            "path": str(item.path),
                            "sha256": item.sha256,
                            "bytes": int(item.bytes),
                        }
                        for item in agg_manifest
                    ],
                },
                "p3_support_contract_reproduced_exactly": True,
                "p3_support_contract": contract,
                "folds": _fold_summary(supports),
                "days": day_records,
                "forward_guards": dict(FORWARD_GUARDS),
                "scientific_interpretation": (
                    "the preregistered raw event-time/deep-depth feature family "
                    "was materialized on exact frozen P3 T1 support; no predictive "
                    "claim is made"
                ),
            }
            content = _canonical_json_bytes(payload)
            manifest_path = staging / MANIFEST_FILENAME
            with manifest_path.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            _fsync_directory(staging)
            os.replace(staging, output)
            _fsync_directory(output.parent)
        except BaseException:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise

    artifact = output / MANIFEST_FILENAME
    return ArtifactWriteResult(
        output,
        artifact,
        _sha256_file(artifact),
        int(artifact.stat().st_size),
    )


__all__ = [
    "BARRIER_BPS",
    "BLOCK",
    "DESIGN_VERSION",
    "EVENT_DEPTH_FEATURE_NAMES",
    "EXPERIMENT_ID",
    "EXTRACTOR_HEADER",
    "FORWARD_GUARDS",
    "HORIZON_SECONDS",
    "MANIFEST_FILENAME",
    "P1AMaterializationError",
    "RAW_ROOT",
    "REAL_OUTPUT_DIRECTORY",
    "STATUS_FAIL",
    "STATUS_INCONCLUSIVE",
    "STATUS_PASS",
    "TARGET_ID",
    "WINDOW_SECONDS",
    "build_selected_p3_support",
    "reconcile_p3_support_contract",
    "run_p1a",
    "validate_event_depth_values",
    "verify_artifacts",
]

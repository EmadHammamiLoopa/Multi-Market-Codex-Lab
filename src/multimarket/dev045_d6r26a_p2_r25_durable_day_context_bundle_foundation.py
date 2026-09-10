from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid

import numpy as np

from multimarket import (
    dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17,
)
from multimarket import (
    dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18,
)
from multimarket import (
    dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19,
)
from multimarket import (
    dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20,
)
from multimarket import (
    dev045_d6r26a_p2_r24_durable_context_performance_preexecution as r24,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R25"
DESIGN_VERSION = "durable-day-context-bundle-foundation-v1"
PARENT_R24_HEAD = "4abe7e0c3807c97a18226fddf1ac51ed81937c85"

MANIFEST_SCHEMA_VERSION = 1
MANIFEST_STATUS_COMPLETE = "COMPLETE"
MANIFEST_NAME = "DAY_CONTEXT_MANIFEST.json"

DECISION_FILE = "decision_local_ns.npy"
BEST_BID_FILE = "best_bid_tick.npy"
BEST_ASK_FILE = "best_ask_tick.npy"
FEATURE_VALUES_FILE = "feature_values.npy"
MIDPOINT_FILE = "exchange_midpoints.bin"

DATA_FILES = (
    DECISION_FILE,
    BEST_BID_FILE,
    BEST_ASK_FILE,
    FEATURE_VALUES_FILE,
    MIDPOINT_FILE,
)
DAY_FILES = DATA_FILES + (MANIFEST_NAME,)

HASH_CHUNK_BYTES = 8 * 1024 * 1024

DURABLE_BUNDLE_PERSISTENCE_IMPLEMENTED = True
DURABLE_BUNDLE_REOPEN_IMPLEMENTED = True
R20_OBJECT_RECONSTRUCTION_IMPLEMENTED = True
R21_COMPATIBLE_CONTEXT_SURFACE_REQUIRED = True
SOURCE_IDENTITY_PROVIDED_BY_CALLER_REQUIRED = True
EXACT_FILE_SET_REQUIRED = True
FILE_BYTES_SHA256_REQUIRED = True
ARRAY_DTYPE_SHAPE_REQUIRED = True
READ_ONLY_MMAP_REOPEN_REQUIRED = True
MIDPOINT_BYTES_PRESERVED_EXACTLY = True
STAGING_DIRECTORY_REQUIRED = True
ATOMIC_SAME_FILESYSTEM_PUBLISH_REQUIRED = True
MANIFEST_WRITTEN_LAST = True
PARTIAL_BUNDLE_REUSE_FORBIDDEN = True
RAW_CONTEXT_REBUILD_DURING_REOPEN_FORBIDDEN = True

P2_ATTEMPT_CONSUMED = False
PREEXECUTION_ONLY = True
SYNTHETIC_DURABLE_BUNDLE_TESTS_AUTHORIZED = True
GENERIC_DURABLE_FILE_IO_AUTHORIZED = True

HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
REAL_JAN_JUL_DURABLE_MATERIALIZATION_AUTHORIZED = False
HISTORICAL_CANDIDATE_SIMULATION_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False


class R25DurableBundleError(RuntimeError):
    pass


@dataclass(frozen=True)
class DurableSourceIdentity:
    day: str
    path: str
    rows: int
    bytes: int
    sha256: str


def _validate_sha256(value: str, *, field: str) -> str:
    digest = str(value).strip()
    if (
        len(digest) != 64
        or digest.lower() != digest
        or any(ch not in "0123456789abcdef" for ch in digest)
    ):
        raise R25DurableBundleError(f"{field}_sha256")
    return digest


def validate_source_identity(source: DurableSourceIdentity) -> None:
    try:
        parsed_day = date.fromisoformat(str(source.day))
    except ValueError as exc:
        raise R25DurableBundleError("source_day") from exc

    if parsed_day.isoformat() != str(source.day):
        raise R25DurableBundleError("source_day")
    if not str(source.path):
        raise R25DurableBundleError("source_path")
    if int(source.rows) <= 0:
        raise R25DurableBundleError("source_rows")
    if int(source.bytes) <= 0:
        raise R25DurableBundleError("source_bytes")
    _validate_sha256(source.sha256, field="source")


def _fsync_directory(path: Path) -> None:
    fd = os.open(
        Path(path),
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _hash_file(path: Path) -> tuple[int, str]:
    file_path = Path(path)
    if file_path.is_symlink() or not file_path.is_file():
        raise R25DurableBundleError(f"file_not_regular:{file_path.name}")

    digest = hashlib.sha256()
    total = 0
    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(HASH_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)

    observed_bytes = int(file_path.stat().st_size)
    if total != observed_bytes:
        raise R25DurableBundleError(f"file_size_changed:{file_path.name}")
    return observed_bytes, digest.hexdigest()


def _npy_identity(path: Path, array: np.ndarray) -> dict[str, object]:
    observed_bytes, digest = _hash_file(path)
    a = np.asarray(array)
    return {
        "bytes": observed_bytes,
        "sha256": digest,
        "dtype": a.dtype.str,
        "shape": [int(value) for value in a.shape],
    }


def _write_npy_exact(path: Path, array: np.ndarray) -> dict[str, object]:
    target = Path(path)
    with target.open("xb") as handle:
        np.save(handle, np.asarray(array), allow_pickle=False)
        handle.flush()
        os.fsync(handle.fileno())
    return _npy_identity(target, np.asarray(array))


def _copy_midpoint_exact(
    *,
    source_path: Path,
    destination_path: Path,
    expected_bytes: int,
    expected_sha256: str,
) -> dict[str, object]:
    source = Path(source_path)
    destination = Path(destination_path)
    if source.is_symlink() or not source.is_file():
        raise R25DurableBundleError("midpoint_source_path")

    before = source.stat()
    digest = hashlib.sha256()
    copied = 0

    with source.open("rb") as src, destination.open("xb") as dst:
        while True:
            chunk = src.read(HASH_CHUNK_BYTES)
            if not chunk:
                break
            dst.write(chunk)
            digest.update(chunk)
            copied += len(chunk)
        dst.flush()
        os.fsync(dst.fileno())

    after = source.stat()
    if (
        int(before.st_size) != int(after.st_size)
        or int(before.st_mtime_ns) != int(after.st_mtime_ns)
    ):
        raise R25DurableBundleError("midpoint_source_changed_during_copy")

    observed_sha = digest.hexdigest()
    if copied != int(expected_bytes):
        raise R25DurableBundleError("midpoint_copy_bytes")
    if observed_sha != _validate_sha256(
        expected_sha256,
        field="midpoint_expected",
    ):
        raise R25DurableBundleError("midpoint_copy_sha256")

    final_bytes, final_sha = _hash_file(destination)
    if final_bytes != copied or final_sha != observed_sha:
        raise R25DurableBundleError("midpoint_copy_identity")

    return {
        "file": MIDPOINT_FILE,
        "bytes": int(final_bytes),
        "sha256": final_sha,
    }


def _validate_bounds(bounds: r17.FeedBounds) -> None:
    start = int(bounds.nominal_day_start_local_ns)
    nominal_end = int(bounds.nominal_day_end_exclusive_local_ns)
    first = int(bounds.first_observed_local_ns)
    last = int(bounds.last_observed_local_ns)
    feed_end = int(bounds.feed_end_exclusive_local_ns)

    if start < 0 or nominal_end <= start:
        raise R25DurableBundleError("bounds_nominal")
    if first < start or last < first or last >= nominal_end:
        raise R25DurableBundleError("bounds_observed")
    if feed_end != last + 1:
        raise R25DurableBundleError("bounds_feed_end")


def _validate_feature_summary(
    summary: r19.FeatureCacheBuildSummary,
    cache: r18.DenseFeatureCache,
) -> None:
    if int(summary.raw_event_pass_count) != 1:
        raise R25DurableBundleError("summary_raw_event_pass_count")
    if int(summary.eligible_decision_count) != int(cache.decision_count):
        raise R25DurableBundleError("summary_eligible_count")
    if int(summary.requested_decision_count) != (
        int(summary.leading_preeligible_count)
        + int(summary.eligible_decision_count)
    ):
        raise R25DurableBundleError("summary_requested_count")
    if int(summary.leading_preeligible_count) < 0:
        raise R25DurableBundleError("summary_leading_preeligible")
    if int(summary.first_eligible_local_ns) != int(
        cache.decision_local_ns[0]
    ):
        raise R25DurableBundleError("summary_first_eligible")
    if int(summary.last_eligible_local_ns) != int(
        cache.decision_local_ns[-1]
    ):
        raise R25DurableBundleError("summary_last_eligible")
    if int(summary.first_requested_local_ns) > int(
        summary.first_eligible_local_ns
    ):
        raise R25DurableBundleError("summary_first_requested")


def _validate_midpoint_handle(index: r20.MidpointIndexHandle) -> None:
    if index.closed:
        raise R25DurableBundleError("midpoint_index_closed")
    if int(index.count) <= 0:
        raise R25DurableBundleError("midpoint_count")
    if int(index.bytes) != int(index.count) * r20.MIDPOINT_RECORD_BYTES:
        raise R25DurableBundleError("midpoint_bytes")
    if index.records.dtype != r20.MIDPOINT_RECORD_DTYPE:
        raise R25DurableBundleError("midpoint_dtype")
    if tuple(index.records.shape) != (int(index.count),):
        raise R25DurableBundleError("midpoint_shape")
    if bool(index.records.flags.writeable):
        raise R25DurableBundleError("midpoint_writeable")
    if Path(index.path).is_symlink() or not Path(index.path).is_file():
        raise R25DurableBundleError("midpoint_path")

    observed_bytes, observed_sha = _hash_file(Path(index.path))
    if observed_bytes != int(index.bytes):
        raise R25DurableBundleError("midpoint_file_bytes")
    if observed_sha != _validate_sha256(index.sha256, field="midpoint"):
        raise R25DurableBundleError("midpoint_file_sha256")

    first_exchange = int(index.records[0]["exchange_ns"])
    last_exchange = int(index.records[-1]["exchange_ns"])
    if first_exchange < 0 or last_exchange < first_exchange:
        raise R25DurableBundleError("midpoint_exchange_bounds")
    if int(index.source_exchange_observed_through_ns) < last_exchange:
        raise R25DurableBundleError("midpoint_observed_through")


def validate_input_context(context: r20.DayContextBuildResult) -> None:
    r24.validate_r24_contract()
    r20.validate_r20_contract()
    if int(context.raw_event_pass_count) != 1:
        raise R25DurableBundleError("context_raw_event_pass_count")
    _validate_bounds(context.bounds)
    r18.validate_dense_feature_cache(context.feature_cache)
    _validate_feature_summary(context.feature_summary, context.feature_cache)
    _validate_midpoint_handle(context.midpoint_index)


def _manifest_payload(
    *,
    source: DurableSourceIdentity,
    context: r20.DayContextBuildResult,
    arrays: dict[str, dict[str, object]],
    midpoint: dict[str, object],
) -> dict[str, object]:
    midpoint_payload = dict(midpoint)
    midpoint_payload.update(
        {
            "count": int(context.midpoint_index.count),
            "record_bytes": int(r20.MIDPOINT_RECORD_BYTES),
            "dtype_descr": [
                [str(name), str(dtype)]
                for name, dtype in r20.MIDPOINT_RECORD_DTYPE.descr
            ],
            "source_exchange_observed_through_ns": int(
                context.midpoint_index.source_exchange_observed_through_ns
            ),
        }
    )
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "status": MANIFEST_STATUS_COMPLETE,
        "source": asdict(source),
        "bounds": asdict(context.bounds),
        "feature_summary": asdict(context.feature_summary),
        "raw_event_pass_count": int(context.raw_event_pass_count),
        "arrays": arrays,
        "midpoint": midpoint_payload,
    }


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    encoded = (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    )
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def _exact_entry_names(root: Path) -> set[str]:
    directory = Path(root)
    if directory.is_symlink() or not directory.is_dir():
        raise R25DurableBundleError("bundle_root")
    return {entry.name for entry in directory.iterdir()}


def _validate_exact_file_set(root: Path) -> None:
    names = _exact_entry_names(root)
    if names != set(DAY_FILES):
        raise R25DurableBundleError(
            "bundle_file_set:" + ",".join(sorted(names))
        )
    for name in DAY_FILES:
        entry = Path(root) / name
        if entry.is_symlink() or not entry.is_file():
            raise R25DurableBundleError(f"bundle_entry:{name}")


def persist_day_context(
    *,
    context: r20.DayContextBuildResult,
    source_identity: DurableSourceIdentity,
    final_dir: Path,
) -> Path:
    """Persist an already-built R20 context without opening any raw source."""
    validate_source_identity(source_identity)
    validate_input_context(context)

    final = Path(final_dir)
    if os.path.lexists(final):
        raise R25DurableBundleError("final_bundle_exists")

    parent = final.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = parent / (
        f".{final.name}.staging.{os.getpid()}.{uuid.uuid4().hex}"
    )
    if os.path.lexists(staging):
        raise R25DurableBundleError("staging_collision")
    staging.mkdir(mode=0o700)

    published = False
    try:
        arrays = {
            DECISION_FILE: _write_npy_exact(
                staging / DECISION_FILE,
                context.feature_cache.decision_local_ns,
            ),
            BEST_BID_FILE: _write_npy_exact(
                staging / BEST_BID_FILE,
                context.feature_cache.best_bid_tick,
            ),
            BEST_ASK_FILE: _write_npy_exact(
                staging / BEST_ASK_FILE,
                context.feature_cache.best_ask_tick,
            ),
            FEATURE_VALUES_FILE: _write_npy_exact(
                staging / FEATURE_VALUES_FILE,
                context.feature_cache.values,
            ),
        }
        midpoint = _copy_midpoint_exact(
            source_path=context.midpoint_index.path,
            destination_path=staging / MIDPOINT_FILE,
            expected_bytes=context.midpoint_index.bytes,
            expected_sha256=context.midpoint_index.sha256,
        )
        payload = _manifest_payload(
            source=source_identity,
            context=context,
            arrays=arrays,
            midpoint=midpoint,
        )

        # Completion sentinel: deliberately written after every data file.
        _write_manifest(staging / MANIFEST_NAME, payload)
        _validate_exact_file_set(staging)
        _fsync_directory(staging)

        if os.path.lexists(final):
            raise R25DurableBundleError("final_bundle_raced")
        os.replace(staging, final)
        published = True
        _fsync_directory(parent)
        _validate_exact_file_set(final)
        return final
    except Exception:
        if not published and staging.exists():
            shutil.rmtree(staging)
            _fsync_directory(parent)
        raise


def _load_manifest(root: Path) -> dict[str, object]:
    manifest_path = Path(root) / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise R25DurableBundleError("manifest_missing")
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise R25DurableBundleError("manifest_parse") from exc
    if not isinstance(payload, dict):
        raise R25DurableBundleError("manifest_type")

    expected_keys = {
        "schema_version",
        "experiment_id",
        "design_version",
        "status",
        "source",
        "bounds",
        "feature_summary",
        "raw_event_pass_count",
        "arrays",
        "midpoint",
    }
    if set(payload) != expected_keys:
        raise R25DurableBundleError("manifest_keys")
    if int(payload["schema_version"]) != MANIFEST_SCHEMA_VERSION:
        raise R25DurableBundleError("manifest_schema_version")
    if payload["experiment_id"] != EXPERIMENT_ID:
        raise R25DurableBundleError("manifest_experiment_id")
    if payload["design_version"] != DESIGN_VERSION:
        raise R25DurableBundleError("manifest_design_version")
    if payload["status"] != MANIFEST_STATUS_COMPLETE:
        raise R25DurableBundleError("manifest_status")
    return payload


def _source_from_payload(payload: object) -> DurableSourceIdentity:
    if not isinstance(payload, dict):
        raise R25DurableBundleError("manifest_source_type")
    if set(payload) != {"day", "path", "rows", "bytes", "sha256"}:
        raise R25DurableBundleError("manifest_source_keys")
    try:
        source = DurableSourceIdentity(
            day=str(payload["day"]),
            path=str(payload["path"]),
            rows=int(payload["rows"]),
            bytes=int(payload["bytes"]),
            sha256=str(payload["sha256"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise R25DurableBundleError("manifest_source") from exc
    validate_source_identity(source)
    return source


def _verify_recorded_file(
    *,
    path: Path,
    record: object,
    name: str,
) -> dict[str, object]:
    if not isinstance(record, dict):
        raise R25DurableBundleError(f"file_record_type:{name}")
    if set(record) != {"bytes", "sha256", "dtype", "shape"}:
        raise R25DurableBundleError(f"file_record_keys:{name}")

    observed_bytes, observed_sha = _hash_file(path)
    try:
        expected_bytes = int(record["bytes"])
        expected_sha = _validate_sha256(
            str(record["sha256"]),
            field=f"file_{name}",
        )
    except (TypeError, ValueError) as exc:
        raise R25DurableBundleError(f"file_record_value:{name}") from exc
    if observed_bytes != expected_bytes:
        raise R25DurableBundleError(f"file_bytes:{name}")
    if observed_sha != expected_sha:
        raise R25DurableBundleError(f"file_sha256:{name}")
    return record


def _load_array(
    *,
    root: Path,
    name: str,
    record: object,
) -> np.memmap:
    verified = _verify_recorded_file(
        path=Path(root) / name,
        record=record,
        name=name,
    )
    try:
        array = np.load(
            Path(root) / name,
            mmap_mode="r",
            allow_pickle=False,
        )
    except (OSError, ValueError) as exc:
        raise R25DurableBundleError(f"npy_load:{name}") from exc
    if not isinstance(array, np.memmap):
        raise R25DurableBundleError(f"npy_not_memmap:{name}")
    if bool(array.flags.writeable):
        raise R25DurableBundleError(f"npy_writeable:{name}")
    try:
        expected_dtype = str(verified["dtype"])
        expected_shape = tuple(int(value) for value in verified["shape"])
    except (TypeError, ValueError) as exc:
        raise R25DurableBundleError(f"npy_record:{name}") from exc
    if array.dtype.str != expected_dtype:
        raise R25DurableBundleError(f"npy_dtype:{name}")
    if tuple(array.shape) != expected_shape:
        raise R25DurableBundleError(f"npy_shape:{name}")
    return array


def _midpoint_from_manifest(
    *,
    root: Path,
    payload: object,
) -> r20.MidpointIndexHandle:
    if not isinstance(payload, dict):
        raise R25DurableBundleError("midpoint_manifest_type")
    expected_keys = {
        "file",
        "bytes",
        "sha256",
        "count",
        "record_bytes",
        "dtype_descr",
        "source_exchange_observed_through_ns",
    }
    if set(payload) != expected_keys:
        raise R25DurableBundleError("midpoint_manifest_keys")
    if payload["file"] != MIDPOINT_FILE:
        raise R25DurableBundleError("midpoint_manifest_file")
    try:
        count = int(payload["count"])
        expected_bytes = int(payload["bytes"])
        record_bytes = int(payload["record_bytes"])
        observed_through = int(
            payload["source_exchange_observed_through_ns"]
        )
        expected_sha = _validate_sha256(
            str(payload["sha256"]),
            field="midpoint_manifest",
        )
    except (TypeError, ValueError) as exc:
        raise R25DurableBundleError("midpoint_manifest_value") from exc

    expected_descr = [
        [str(name), str(dtype)]
        for name, dtype in r20.MIDPOINT_RECORD_DTYPE.descr
    ]
    if payload["dtype_descr"] != expected_descr:
        raise R25DurableBundleError("midpoint_manifest_dtype")
    if record_bytes != r20.MIDPOINT_RECORD_BYTES:
        raise R25DurableBundleError("midpoint_manifest_record_bytes")
    if count <= 0 or expected_bytes != count * record_bytes:
        raise R25DurableBundleError("midpoint_manifest_count_bytes")

    path = Path(root) / MIDPOINT_FILE
    observed_bytes, observed_sha = _hash_file(path)
    if observed_bytes != expected_bytes:
        raise R25DurableBundleError("midpoint_reopen_bytes")
    if observed_sha != expected_sha:
        raise R25DurableBundleError("midpoint_reopen_sha256")

    try:
        records = np.memmap(
            path,
            dtype=r20.MIDPOINT_RECORD_DTYPE,
            mode="r",
            shape=(count,),
        )
    except (OSError, ValueError) as exc:
        raise R25DurableBundleError("midpoint_reopen_memmap") from exc
    if bool(records.flags.writeable):
        raise R25DurableBundleError("midpoint_reopen_writeable")

    first_exchange = int(records[0]["exchange_ns"])
    last_exchange = int(records[-1]["exchange_ns"])
    if first_exchange < 0 or last_exchange < first_exchange:
        _close_memmap(records)
        raise R25DurableBundleError("midpoint_reopen_exchange_bounds")
    if observed_through < last_exchange:
        _close_memmap(records)
        raise R25DurableBundleError("midpoint_reopen_observed_through")

    return r20.MidpointIndexHandle(
        path=path,
        records=records,
        count=count,
        bytes=expected_bytes,
        sha256=expected_sha,
        source_exchange_observed_through_ns=observed_through,
    )


def _bounds_from_payload(payload: object) -> r17.FeedBounds:
    if not isinstance(payload, dict):
        raise R25DurableBundleError("bounds_manifest_type")
    expected_keys = {
        "nominal_day_start_local_ns",
        "nominal_day_end_exclusive_local_ns",
        "first_observed_local_ns",
        "last_observed_local_ns",
        "feed_end_exclusive_local_ns",
    }
    if set(payload) != expected_keys:
        raise R25DurableBundleError("bounds_manifest_keys")
    try:
        bounds = r17.FeedBounds(
            **{key: int(value) for key, value in payload.items()}
        )
    except (TypeError, ValueError) as exc:
        raise R25DurableBundleError("bounds_manifest_value") from exc
    _validate_bounds(bounds)
    return bounds


def _summary_from_payload(payload: object) -> r19.FeatureCacheBuildSummary:
    if not isinstance(payload, dict):
        raise R25DurableBundleError("summary_manifest_type")
    expected_keys = {
        "requested_decision_count",
        "leading_preeligible_count",
        "eligible_decision_count",
        "first_requested_local_ns",
        "first_eligible_local_ns",
        "last_eligible_local_ns",
        "raw_event_pass_count",
    }
    if set(payload) != expected_keys:
        raise R25DurableBundleError("summary_manifest_keys")
    try:
        return r19.FeatureCacheBuildSummary(
            **{key: int(value) for key, value in payload.items()}
        )
    except (TypeError, ValueError) as exc:
        raise R25DurableBundleError("summary_manifest_value") from exc


def _close_memmap(array: np.ndarray) -> None:
    mm = getattr(array, "_mmap", None)
    if mm is not None:
        mm.close()


def open_verified_day_context(
    *,
    bundle_dir: Path,
    expected_source_identity: DurableSourceIdentity,
) -> r20.DayContextBuildResult:
    """Reopen a durable bundle without touching or rebuilding raw source."""
    r24.validate_r24_contract()
    validate_source_identity(expected_source_identity)

    root = Path(bundle_dir)
    _validate_exact_file_set(root)
    payload = _load_manifest(root)
    recorded_source = _source_from_payload(payload["source"])
    if recorded_source != expected_source_identity:
        raise R25DurableBundleError("source_identity_mismatch")

    arrays_payload = payload["arrays"]
    if not isinstance(arrays_payload, dict):
        raise R25DurableBundleError("arrays_manifest_type")
    expected_array_names = {
        DECISION_FILE,
        BEST_BID_FILE,
        BEST_ASK_FILE,
        FEATURE_VALUES_FILE,
    }
    if set(arrays_payload) != expected_array_names:
        raise R25DurableBundleError("arrays_manifest_keys")

    opened_arrays: list[np.memmap] = []
    midpoint: r20.MidpointIndexHandle | None = None
    try:
        decisions = _load_array(
            root=root,
            name=DECISION_FILE,
            record=arrays_payload[DECISION_FILE],
        )
        opened_arrays.append(decisions)
        bids = _load_array(
            root=root,
            name=BEST_BID_FILE,
            record=arrays_payload[BEST_BID_FILE],
        )
        opened_arrays.append(bids)
        asks = _load_array(
            root=root,
            name=BEST_ASK_FILE,
            record=arrays_payload[BEST_ASK_FILE],
        )
        opened_arrays.append(asks)
        values = _load_array(
            root=root,
            name=FEATURE_VALUES_FILE,
            record=arrays_payload[FEATURE_VALUES_FILE],
        )
        opened_arrays.append(values)

        if decisions.dtype != np.dtype("<i8"):
            raise R25DurableBundleError("decision_dtype")
        if bids.dtype != np.dtype("<i8"):
            raise R25DurableBundleError("bid_dtype")
        if asks.dtype != np.dtype("<i8"):
            raise R25DurableBundleError("ask_dtype")
        if values.dtype != r17.FEATURE_CACHE_VALUE_DTYPE:
            raise R25DurableBundleError("feature_dtype")

        cache = r18.DenseFeatureCache(
            decision_local_ns=decisions,
            best_bid_tick=bids,
            best_ask_tick=asks,
            values=values,
        )
        r18.validate_dense_feature_cache(cache)

        bounds = _bounds_from_payload(payload["bounds"])
        summary = _summary_from_payload(payload["feature_summary"])
        _validate_feature_summary(summary, cache)
        if int(payload["raw_event_pass_count"]) != 1:
            raise R25DurableBundleError("manifest_raw_event_pass_count")

        midpoint = _midpoint_from_manifest(
            root=root,
            payload=payload["midpoint"],
        )
        context = r20.DayContextBuildResult(
            bounds=bounds,
            feature_cache=cache,
            feature_summary=summary,
            midpoint_index=midpoint,
            raw_event_pass_count=1,
        )
        validate_input_context(context)
        return context
    except Exception:
        if midpoint is not None and not midpoint.closed:
            r20.close_midpoint_index(midpoint, delete=False)
        for array in opened_arrays:
            _close_memmap(array)
        raise


def close_reopened_day_context(context: r20.DayContextBuildResult) -> None:
    """Close R25 mmap handles while preserving all durable files."""
    for array in (
        context.feature_cache.decision_local_ns,
        context.feature_cache.best_bid_tick,
        context.feature_cache.best_ask_tick,
        context.feature_cache.values,
    ):
        _close_memmap(array)
    if not context.midpoint_index.closed:
        r20.close_midpoint_index(context.midpoint_index, delete=False)


def validate_r25_contract() -> None:
    r24.validate_r24_contract()
    r20.validate_r20_contract()

    if PARENT_R24_HEAD != "4abe7e0c3807c97a18226fddf1ac51ed81937c85":
        raise R25DurableBundleError("parent")
    if tuple(r24.DAY_FILES) != DAY_FILES:
        raise R25DurableBundleError("r24_day_files")
    if MANIFEST_NAME != DAY_FILES[-1]:
        raise R25DurableBundleError("manifest_last")
    if HASH_CHUNK_BYTES > 16 * 1024 * 1024:
        raise R25DurableBundleError("hash_chunk_bound")

    required = (
        DURABLE_BUNDLE_PERSISTENCE_IMPLEMENTED,
        DURABLE_BUNDLE_REOPEN_IMPLEMENTED,
        R20_OBJECT_RECONSTRUCTION_IMPLEMENTED,
        R21_COMPATIBLE_CONTEXT_SURFACE_REQUIRED,
        SOURCE_IDENTITY_PROVIDED_BY_CALLER_REQUIRED,
        EXACT_FILE_SET_REQUIRED,
        FILE_BYTES_SHA256_REQUIRED,
        ARRAY_DTYPE_SHAPE_REQUIRED,
        READ_ONLY_MMAP_REOPEN_REQUIRED,
        MIDPOINT_BYTES_PRESERVED_EXACTLY,
        STAGING_DIRECTORY_REQUIRED,
        ATOMIC_SAME_FILESYSTEM_PUBLISH_REQUIRED,
        MANIFEST_WRITTEN_LAST,
        PARTIAL_BUNDLE_REUSE_FORBIDDEN,
        RAW_CONTEXT_REBUILD_DURING_REOPEN_FORBIDDEN,
        SYNTHETIC_DURABLE_BUNDLE_TESTS_AUTHORIZED,
        GENERIC_DURABLE_FILE_IO_AUTHORIZED,
        PREEXECUTION_ONLY,
        P2_ATTEMPT_CONSUMED is False,
        r24.DURABLE_CONTEXT_BUILD_DOES_NOT_CONSUME_SIMULATOR_ATTEMPT,
        r24.PARTIAL_DAY_BUNDLE_REUSE_FORBIDDEN,
        r24.DAY_MANIFEST_WRITTEN_LAST,
    )
    if not all(required):
        raise R25DurableBundleError("required_guard")

    forbidden = (
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        REAL_JAN_JUL_DURABLE_MATERIALIZATION_AUTHORIZED,
        HISTORICAL_CANDIDATE_SIMULATION_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
    )
    if any(forbidden):
        raise R25DurableBundleError("execution_surface_open")


__all__ = [
    "DurableSourceIdentity",
    "DAY_FILES",
    "MANIFEST_NAME",
    "persist_day_context",
    "open_verified_day_context",
    "close_reopened_day_context",
    "validate_source_identity",
    "validate_input_context",
    "validate_r25_contract",
]

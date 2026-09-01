"""DEV030-P2B deterministic T1 dataset and support construction.

This module joins the frozen executable first-passage labels to the frozen
S0/S1 sequence representations. It contains dataset/support logic only: no
estimator, predictive metric, temporal null, opportunity gate, trading return,
capital, or position logic.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
from pathlib import Path
import struct
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from . import dev030_first_passage as fp
from . import dev030_sequence_features as sf
from .v23_phase0dl_score import L0_NAMES, L1_EXTRA_NAMES, L2_EXTRA_NAMES


EXPERIMENT_ID = "DEV030-P2B"
SYMBOL = "BTCUSDT"
DECISION_STEP_US = 60_000_000
DAY_US = 86_400_000_000

FIRST_PASSAGE_SOURCE_REL = "src/multimarket/dev030_first_passage.py"
SEQUENCE_FEATURE_SOURCE_REL = "src/multimarket/dev030_sequence_features.py"
FIRST_PASSAGE_SOURCE_SHA256 = (
    "33dbbb53dfe10cfa859037fa2a89d05010f7950e3ec74e51422135ec585d0bc7"
)
SEQUENCE_FEATURE_SOURCE_SHA256 = (
    "30952d31795d5fd88c9dfd9641a5332b662eeb32f30ec9ac283f8339d26ac11c"
)

# Authoritative positional order emitted by Phase0DL into X["L2"].
SOURCE_FEATURE_ORDER = tuple(L0_NAMES + L1_EXTRA_NAMES + L2_EXTRA_NAMES)

FEATURE_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/v23/phase0dl_features250/BTCUSDT"
)
HISTORICAL_DAYS = tuple(date(2026, month, 1) for month in range(1, 8))
EXPECTED_INPUT_SHA256 = {
    date(2026, 1, 1): "ab0c61fe9a7517cf97388300e6adb18248a37a7977aac8455a10c02b7906de98",
    date(2026, 2, 1): "33e56c6b5b02ec124bf3a21dbed27fc8705fc572cb7fed9ff73876de87c2978e",
    date(2026, 3, 1): "076067a4731047dd992004d936d962567c1d7ceed864bb6e778db05bc8c59420",
    date(2026, 4, 1): "a803fbb8d68f4173551be4c2cccf9fe03f25d86dc6e00469c4a5ab635ade2307",
    date(2026, 5, 1): "36015c5954d820d8b2f0505ecab9fdc96f40136247d1270365c9ef81312de2e3",
    date(2026, 6, 1): "5e73f8dc355e3dfcceda649525b4d067ccb74d0259992a287161a71375105535",
    date(2026, 7, 1): "aadf264ba38eac4563ebab7fd2da22b300d82752343ccd30b19809c70cd39012",
}


@dataclass(frozen=True, order=True)
class TargetGeometry:
    target_id: str
    horizon_seconds: int
    barrier_bps: int


FROZEN_TARGETS = (
    TargetGeometry("A", 120, 16),
    TargetGeometry("B", 300, 24),
    TargetGeometry("C", 300, 12),
    TargetGeometry("D", 60, 8),
)
FROZEN_WINDOWS_SECONDS = sf.FROZEN_WINDOWS_SECONDS
FROZEN_BLOCKS = sf.BLOCK_ORDER

BASE_CSV_COLUMNS = (
    "local_timestamp_us", "best_bid", "best_ask", "mid", "book_valid",
    "l0_valid", "l1_valid", "l2_valid",
)
EXPECTED_CSV_COLUMNS = BASE_CSV_COLUMNS + SOURCE_FEATURE_ORDER

T1_LONG = 1
T1_SHORT = 0
T1_EXCLUDED = -1
EXCLUDE_NONE = "none_excluded"
EXCLUDE_INVALID_UNSPECIFIED = "invalid_target_unspecified"
S0_BOUNDARY_BEFORE_DAY = "s0_raw_source_before_day"
S1_BOUNDARY_BEFORE_DAY = "s1_raw_source_before_day"
TARGET_BOUNDARY_AFTER_DAY = "target_future_after_day"
SUPPORT_HASH_DOMAIN = b"DEV030-P2B-SUPPORT-TIMESTAMPS-US-V1\x00"


@dataclass(frozen=True)
class FrozenSourceIdentity:
    name: str
    relative_path: str
    expected_sha256: str
    mismatch_reason: str


@dataclass(frozen=True)
class FrozenSourceVerification:
    name: str
    relative_path: str
    sha256: str
    sha256_verified: bool


FROZEN_SOURCE_IDENTITIES = (
    FrozenSourceIdentity(
        "first_passage", FIRST_PASSAGE_SOURCE_REL,
        FIRST_PASSAGE_SOURCE_SHA256, "first_passage_source_sha256_mismatch",
    ),
    FrozenSourceIdentity(
        "sequence_features", SEQUENCE_FEATURE_SOURCE_REL,
        SEQUENCE_FEATURE_SOURCE_SHA256, "sequence_feature_source_sha256_mismatch",
    ),
)


@dataclass(frozen=True)
class FrozenOuterFold:
    fold_id: int
    train_days: tuple[date, ...]
    validation_day: date


OUTER_FOLDS = (
    FrozenOuterFold(1, HISTORICAL_DAYS[:3], HISTORICAL_DAYS[3]),
    FrozenOuterFold(2, HISTORICAL_DAYS[:4], HISTORICAL_DAYS[4]),
    FrozenOuterFold(3, HISTORICAL_DAYS[:5], HISTORICAL_DAYS[5]),
    FrozenOuterFold(4, HISTORICAL_DAYS[:6], HISTORICAL_DAYS[6]),
)


@dataclass(frozen=True)
class InputManifestEntry:
    day: date
    path: Path
    sha256: str
    bytes: int


@dataclass(frozen=True)
class CandidateKey:
    target: TargetGeometry
    window_seconds: int
    block: str


@dataclass(frozen=True)
class CandidateBoundaryReasons:
    s0_boundary_reason: str | None
    s1_boundary_reason: str | None
    target_boundary_reason: str | None


@dataclass
class CandidateDayDataset:
    day: date
    key: CandidateKey
    decision_timestamps_us: np.ndarray
    target_records: tuple[dict[str, Any], ...]
    t1_labels: np.ndarray
    s0_feature_names: tuple[str, ...]
    s1_feature_names: tuple[str, ...]
    s0_values: np.ndarray
    s1_values: np.ndarray
    s0_valid: np.ndarray
    s1_valid: np.ndarray
    common_valid: np.ndarray
    t1_common_valid: np.ndarray
    target_future_boundary_valid: np.ndarray
    s0_boundary_reasons: tuple[str | None, ...]
    s1_boundary_reasons: tuple[str | None, ...]
    target_boundary_reasons: tuple[str | None, ...]
    s0_invalid_reasons: tuple[str | None, ...]
    s1_invalid_reasons: tuple[str | None, ...]
    counts: dict[str, Any]
    support_hashes: dict[str, str]


@dataclass(frozen=True)
class FoldSupport:
    fold: FrozenOuterFold
    key: CandidateKey
    train_decision_timestamps_us: np.ndarray
    validation_decision_timestamps_us: np.ndarray
    train_t1_common_indices: np.ndarray
    validation_t1_common_indices: np.ndarray
    train_t1_common_timestamps_us: np.ndarray
    validation_t1_common_timestamps_us: np.ndarray
    train_class_counts: dict[str, int]
    validation_class_counts: dict[str, int]
    support_hashes: dict[str, str]


class DirectionDatasetError(RuntimeError):
    """Frozen input, schema, chronology, or dataset protocol violation."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def verify_frozen_source_identities(
    repository_root: Path,
    *,
    identities: Sequence[FrozenSourceIdentity] = FROZEN_SOURCE_IDENTITIES,
    hash_file: Callable[[Path], str] = _sha256_file,
) -> tuple[FrozenSourceVerification, ...]:
    """Verify the two explicit frozen scientific sources as opaque bytes."""

    root = Path(repository_root).resolve()
    results: list[FrozenSourceVerification] = []
    # Frozen order: first-passage first, sequence features second.
    for identity in identities:
        source_path = root / identity.relative_path
        if not source_path.is_file():
            raise DirectionDatasetError("frozen_source_missing", identity.relative_path)
        actual = str(hash_file(source_path))
        if actual != identity.expected_sha256:
            raise DirectionDatasetError(identity.mismatch_reason, identity.relative_path)
        results.append(FrozenSourceVerification(
            identity.name, identity.relative_path, actual, True
        ))
    return tuple(results)


def verify_phase0dl_feature_order(
    source_feature_order: Sequence[str] = SOURCE_FEATURE_ORDER,
) -> tuple[str, ...]:
    normalized = tuple(str(name) for name in source_feature_order)
    if normalized != sf.ALLOWED_STORED_FEATURES:
        raise DirectionDatasetError("phase0dl_feature_order_mismatch")
    return normalized


def _target_geometry(target: TargetGeometry) -> TargetGeometry:
    if target not in FROZEN_TARGETS:
        raise DirectionDatasetError("unsupported_target_geometry", repr(target))
    return target


def _window(window_seconds: int) -> int:
    if isinstance(window_seconds, (bool, np.bool_)) or window_seconds not in FROZEN_WINDOWS_SECONDS:
        raise DirectionDatasetError("unsupported_sequence_window", str(window_seconds))
    return int(window_seconds)


def _block(block: str) -> str:
    if block not in FROZEN_BLOCKS:
        raise DirectionDatasetError("unsupported_feature_block", str(block))
    return block


def authorized_input_path(day: date, *, symbol: str = SYMBOL) -> Path:
    if symbol != SYMBOL:
        raise DirectionDatasetError("unauthorized_symbol", str(symbol))
    if day not in HISTORICAL_DAYS:
        raise DirectionDatasetError("unauthorized_historical_day", str(day))
    return FEATURE_ROOT / f"{day.isoformat()}_FEATURES250.csv"


def expected_input_paths() -> dict[date, Path]:
    return {day: authorized_input_path(day) for day in HISTORICAL_DAYS}


def validate_csv_columns(columns: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(str(column) for column in columns)
    if normalized != EXPECTED_CSV_COLUMNS:
        missing = sorted(set(EXPECTED_CSV_COLUMNS) - set(normalized))
        extra = sorted(set(normalized) - set(EXPECTED_CSV_COLUMNS))
        raise DirectionDatasetError("csv_schema_mismatch", f"missing={missing}, extra={extra}")
    return normalized


def _read_csv_header(path: Path) -> tuple[str, ...]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            line = handle.readline().rstrip("\r\n")
    except OSError as exc:
        raise DirectionDatasetError("csv_header_read_failed", str(path)) from exc
    return validate_csv_columns(line.split(","))


def _verify_manifest_entries(
    paths: Mapping[date, Path],
    expected_hashes: Mapping[date, str],
    *,
    hash_file: Callable[[Path], str],
) -> tuple[InputManifestEntry, ...]:
    if tuple(sorted(paths)) != HISTORICAL_DAYS:
        raise DirectionDatasetError("input_calendar_mismatch")
    if tuple(sorted(expected_hashes)) != HISTORICAL_DAYS:
        raise DirectionDatasetError("expected_hash_calendar_mismatch")
    entries: list[InputManifestEntry] = []
    for day in HISTORICAL_DAYS:
        path = Path(paths[day])
        if path.name != f"{day.isoformat()}_FEATURES250.csv":
            raise DirectionDatasetError("input_filename_mismatch", str(path))
        if not path.is_file():
            raise DirectionDatasetError("authorized_input_missing", str(path))
        actual = str(hash_file(path))
        if actual != expected_hashes[day]:
            raise DirectionDatasetError("authorized_input_sha256_mismatch", day.isoformat())
        entries.append(InputManifestEntry(day, path, actual, int(path.stat().st_size)))
    return tuple(entries)


def verify_input_manifest() -> tuple[InputManifestEntry, ...]:
    return _verify_manifest_entries(
        expected_input_paths(), EXPECTED_INPUT_SHA256, hash_file=_sha256_file
    )


def _load_verified_entries(
    entries: Sequence[InputManifestEntry],
    *,
    header_reader: Callable[[Path], Sequence[str]],
    loader: Callable[[Path, date], Any],
) -> tuple[Any, ...]:
    for entry in entries:
        validate_csv_columns(header_reader(entry.path))
    return tuple(loader(entry.path, entry.day) for entry in entries)


def _load_verified_authorized_days(
    *,
    repository_root: Path,
    source_identities: Sequence[FrozenSourceIdentity] = FROZEN_SOURCE_IDENTITIES,
    source_feature_order: Sequence[str] = SOURCE_FEATURE_ORDER,
    source_hash_file: Callable[[Path], str],
    input_paths: Mapping[date, Path],
    expected_input_hashes: Mapping[date, str],
    input_hash_file: Callable[[Path], str],
    header_reader: Callable[[Path], Sequence[str]],
    loader: Callable[[Path, date], Any],
) -> tuple[Any, ...]:
    """Enforce the exact fail-closed order before analytical row loading."""

    verify_frozen_source_identities(
        repository_root, identities=source_identities, hash_file=source_hash_file
    )
    verify_phase0dl_feature_order(source_feature_order)
    entries = _verify_manifest_entries(
        input_paths, expected_input_hashes, hash_file=input_hash_file
    )
    return _load_verified_entries(entries, header_reader=header_reader, loader=loader)


def _default_day_loader(path: Path, day_value: date) -> Any:
    from .v23_phase0dl_score import _load_day
    return _load_day(path, day_value)


def load_authorized_days() -> tuple[Any, ...]:
    return _load_verified_authorized_days(
        repository_root=_repository_root(),
        source_hash_file=_sha256_file,
        input_paths=expected_input_paths(),
        expected_input_hashes=EXPECTED_INPUT_SHA256,
        input_hash_file=_sha256_file,
        header_reader=_read_csv_header,
        loader=_default_day_loader,
    )


def exact_minute_decision_indices(timestamps_us: Any) -> np.ndarray:
    raw = np.asarray(timestamps_us)
    if raw.ndim != 1 or raw.dtype.kind not in "iu":
        raise DirectionDatasetError("timestamps_must_be_integer_1d")
    timestamps = raw.astype(np.int64, copy=False)
    if len(timestamps) == 0:
        return np.empty(0, dtype=np.int64)
    differences = np.diff(timestamps)
    if bool(np.any(differences == 0)):
        raise DirectionDatasetError("duplicate_timestamps")
    if bool(np.any(differences < 0)):
        raise DirectionDatasetError("non_monotonic_timestamps")
    if bool(np.any(timestamps % fp.GRID_US != 0)):
        raise DirectionDatasetError("off_grid_timestamp")
    return np.flatnonzero(timestamps % DECISION_STEP_US == 0).astype(np.int64, copy=False)


def _validate_day_structure(day: Any) -> sf.SequenceFeatureInput:
    source_feature_order = verify_phase0dl_feature_order()
    try:
        timestamps = np.asarray(day.ts)
        bid = np.asarray(day.bid)
        ask = np.asarray(day.ask)
        mid = np.asarray(day.mid)
        book_valid = np.asarray(day.book_valid)
        valid = day.valid
        full_matrix = np.asarray(day.X["L2"])
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise DirectionDatasetError("invalid_day_structure") from exc
    rows = len(timestamps)
    arrays = (bid, ask, mid, book_valid)
    if timestamps.ndim != 1 or any(array.ndim != 1 for array in arrays):
        raise DirectionDatasetError("day_arrays_must_be_one_dimensional")
    if any(len(array) != rows for array in arrays):
        raise DirectionDatasetError("day_array_length_mismatch")
    exact_minute_decision_indices(timestamps)
    if full_matrix.ndim != 2 or full_matrix.shape != (rows, len(source_feature_order)):
        raise DirectionDatasetError("phase0dl_feature_matrix_shape_mismatch")
    try:
        masks = {
            "book_valid": book_valid,
            "l0_valid": np.asarray(valid["L0"]),
            "l1_valid": np.asarray(valid["L1"]),
            "l2_valid": np.asarray(valid["L2"]),
        }
    except (KeyError, TypeError) as exc:
        raise DirectionDatasetError("phase0dl_validity_masks_missing") from exc
    if any(mask.ndim != 1 or len(mask) != rows for mask in masks.values()):
        raise DirectionDatasetError("phase0dl_validity_mask_shape_mismatch")
    features = {
        name: full_matrix[:, position]
        for position, name in enumerate(source_feature_order)
    }
    return sf.SequenceFeatureInput(timestamps, features, mid, masks)


def map_t1_record(record: Mapping[str, Any]) -> tuple[int | None, str | None]:
    target_valid = record.get("target_valid")
    if type(target_valid) is not bool:
        raise DirectionDatasetError("target_valid_must_be_builtin_bool")
    label = record.get("label")
    if target_valid is False:
        if label is not None:
            raise DirectionDatasetError("invalid_target_has_non_null_label")
        reason = record.get("invalid_reason")
        if not isinstance(reason, str) or not reason:
            reason = EXCLUDE_INVALID_UNSPECIFIED
        return None, reason
    if record.get("invalid_reason") is not None:
        raise DirectionDatasetError("valid_target_has_invalid_reason")
    if record.get("same_row_ambiguous") is not False:
        raise DirectionDatasetError("valid_target_marked_same_row_ambiguous")
    if label == fp.LONG_FIRST:
        return T1_LONG, None
    if label == fp.SHORT_FIRST:
        return T1_SHORT, None
    if label == fp.NONE:
        return None, EXCLUDE_NONE
    raise DirectionDatasetError("unexpected_first_passage_label", repr(label))


def sequence_summary_feature_names(block: str) -> tuple[str, ...]:
    names: list[str] = []
    statistics = (
        "last", "mean", "std", "minimum", "maximum", "last_minus_first", "ols_slope"
    )
    for feature in sf.block_feature_names(_block(block)):
        names.extend(f"{feature}__{statistic}" for statistic in statistics)
        if feature in sf.NATURALLY_SIGNED_FEATURES:
            names.append(f"{feature}__sign_persistence")
    return tuple(names)


def candidate_boundary_reasons(
    *,
    decision_timestamp_us: int,
    day_start_us: int,
    day_end_us: int,
    target: TargetGeometry,
    window_seconds: int,
    block: str,
) -> CandidateBoundaryReasons:
    target = _target_geometry(target)
    window_seconds = _window(window_seconds)
    block = _block(block)
    decision_us = int(decision_timestamp_us)
    last_grid_us = int(day_end_us) - fp.GRID_US
    if decision_us < int(day_start_us) or decision_us > last_grid_us:
        raise DirectionDatasetError("decision_outside_utc_day")
    lookback_ns = sf.block_internal_lookback_ns(block)
    if lookback_ns % 1_000 != 0:
        raise DirectionDatasetError("block_lookback_not_exact_microseconds")
    lookback_us = lookback_ns // 1_000
    interval = sf.information_intervals(
        decision_timestamp_us=decision_us,
        window_seconds=window_seconds,
        block=block,
        target_horizon_seconds=target.horizon_seconds,
    )
    s0_start = decision_us - lookback_us
    s1_start = decision_us - window_seconds * 1_000_000 - lookback_us
    target_start = decision_us + fp.GRID_US
    target_end = target_start + target.horizon_seconds * 1_000_000
    if interval.representation_end_us != decision_us:
        raise DirectionDatasetError("representation_uses_future_row")
    if interval.raw_source_start_us != s1_start:
        raise DirectionDatasetError("combined_source_interval_mismatch")
    if interval.raw_source_end_us != target_end:
        raise DirectionDatasetError("combined_target_interval_mismatch")
    return CandidateBoundaryReasons(
        S0_BOUNDARY_BEFORE_DAY if s0_start < int(day_start_us) else None,
        S1_BOUNDARY_BEFORE_DAY if s1_start < int(day_start_us) else None,
        TARGET_BOUNDARY_AFTER_DAY if target_end > last_grid_us else None,
    )


def _utc_day_bounds(day_value: date) -> tuple[int, int]:
    start = datetime(day_value.year, day_value.month, day_value.day, tzinfo=timezone.utc)
    start_us = int(start.timestamp()) * 1_000_000
    return start_us, start_us + DAY_US


def _slice_sequence_input(
    data: sf.SequenceFeatureInput, *, start_us: int, end_us: int
) -> sf.SequenceFeatureInput:
    timestamps = np.asarray(data.timestamps_us)
    left = int(np.searchsorted(timestamps, start_us, side="left"))
    right = int(np.searchsorted(timestamps, end_us, side="right"))
    selection = slice(left, right)
    return sf.SequenceFeatureInput(
        timestamps[selection],
        {name: np.asarray(values)[selection] for name, values in data.features.items()},
        np.asarray(data.mid)[selection],
        {name: np.asarray(values)[selection] for name, values in data.validity_masks.items()},
    )


def canonical_support_bytes(timestamps_us: Any) -> bytes:
    """Domain, uint64 count, then chronological big-endian int64 microseconds."""

    raw = np.asarray(timestamps_us)
    if raw.ndim != 1 or raw.dtype.kind not in "iu":
        raise DirectionDatasetError("support_timestamps_must_be_integer_1d")
    timestamps = raw.astype(np.int64, copy=False)
    if bool(np.any(np.diff(timestamps) <= 0)):
        raise DirectionDatasetError("support_not_unique_chronological")
    encoded = bytearray(SUPPORT_HASH_DOMAIN)
    encoded.extend(struct.pack(">Q", len(timestamps)))
    for timestamp in timestamps.tolist():
        encoded.extend(struct.pack(">q", int(timestamp)))
    return bytes(encoded)


def support_sha256(timestamps_us: Any) -> str:
    return hashlib.sha256(canonical_support_bytes(timestamps_us)).hexdigest()


def _support_hash(timestamps: np.ndarray, mask: np.ndarray) -> str:
    return support_sha256(timestamps[np.asarray(mask, dtype=bool)])


def _target_counts(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    long_count = short_count = none_count = valid_count = invalid_count = 0
    invalid_reasons: Counter[str] = Counter()
    for record in records:
        mapped, reason = map_t1_record(record)
        if record["target_valid"] is True:
            valid_count += 1
            if mapped == T1_LONG:
                long_count += 1
            elif mapped == T1_SHORT:
                short_count += 1
            else:
                none_count += 1
        else:
            invalid_count += 1
            invalid_reasons[str(reason)] += 1
    return {
        "valid_target_count": int(valid_count),
        "invalid_target_count": int(invalid_count),
        "long_first_count": int(long_count),
        "short_first_count": int(short_count),
        "none_count": int(none_count),
        "invalid_target_reasons": dict(sorted(invalid_reasons.items())),
    }


_LOCAL_REPRESENTATION_REASONS = {
    "decision_timestamp_missing", "window_grid_missing", "missing_prior_mid_endpoint",
    "non_finite_required_feature", "invalid_required_mask",
    "invalid_mid_for_derived_return", "non_finite_derived_return",
}


def _capture_representation(
    function: Callable[..., dict[str, float]], *args: Any, **kwargs: Any
) -> tuple[dict[str, float] | None, str | None]:
    try:
        return function(*args, **kwargs), None
    except sf.SequenceFeatureError as exc:
        if exc.reason not in _LOCAL_REPRESENTATION_REASONS:
            raise DirectionDatasetError("sequence_feature_protocol_violation", str(exc)) from exc
        return None, exc.reason


def build_candidate_day(
    day: Any,
    *,
    target: TargetGeometry,
    window_seconds: int,
    block: str,
    target_records: Sequence[Mapping[str, Any]] | None = None,
) -> CandidateDayDataset:
    """Construct one target/window/block dataset entirely in memory."""

    target = _target_geometry(target)
    window_seconds = _window(window_seconds)
    block = _block(block)
    sequence_input = _validate_day_structure(day)
    timestamps = np.asarray(sequence_input.timestamps_us, dtype=np.int64)
    decision_indices = exact_minute_decision_indices(timestamps)
    decision_timestamps = timestamps[decision_indices].astype(np.int64, copy=False)
    records = (
        fp.label_first_passage_targets(
            day, decision_indices, horizon_seconds=target.horizon_seconds,
            barrier_bps=target.barrier_bps, latency_ms=fp.LATENCY_MS,
        )
        if target_records is None else [dict(record) for record in target_records]
    )
    if len(records) != len(decision_indices):
        raise DirectionDatasetError("target_record_count_mismatch")

    s0_names = sf.block_feature_names(block)
    s1_names = sequence_summary_feature_names(block)
    s0_values = np.full((len(records), len(s0_names)), np.nan)
    s1_values = np.full((len(records), len(s1_names)), np.nan)
    s0_valid = np.zeros(len(records), dtype=bool)
    s1_valid = np.zeros(len(records), dtype=bool)
    target_future_valid = np.zeros(len(records), dtype=bool)
    t1_labels = np.full(len(records), T1_EXCLUDED, dtype=np.int8)
    s0_boundaries: list[str | None] = []
    s1_boundaries: list[str | None] = []
    target_boundaries: list[str | None] = []
    s0_reasons: list[str | None] = []
    s1_reasons: list[str | None] = []
    try:
        day_value = day.day
    except AttributeError as exc:
        raise DirectionDatasetError("day_date_missing") from exc
    day_start, day_end = _utc_day_bounds(day_value)

    for position, timestamp in enumerate(decision_timestamps.tolist()):
        record = records[position]
        mapped, _ = map_t1_record(record)
        if mapped is not None:
            t1_labels[position] = np.int8(mapped)
        boundaries = candidate_boundary_reasons(
            decision_timestamp_us=timestamp, day_start_us=day_start, day_end_us=day_end,
            target=target, window_seconds=window_seconds, block=block,
        )
        s0_boundaries.append(boundaries.s0_boundary_reason)
        s1_boundaries.append(boundaries.s1_boundary_reason)
        target_boundaries.append(boundaries.target_boundary_reason)
        target_future_valid[position] = boundaries.target_boundary_reason is None
        if not target_future_valid[position] and record["target_valid"] is True:
            raise DirectionDatasetError("target_boundary_labeler_mismatch")

        if boundaries.s0_boundary_reason is None:
            local = _slice_sequence_input(
                sequence_input, start_us=timestamp - fp.GRID_US, end_us=timestamp
            )
            s0, s0_reason = _capture_representation(
                sf.extract_snapshot, local, decision_timestamp_us=timestamp, block=block
            )
        else:
            s0, s0_reason = None, boundaries.s0_boundary_reason
        if boundaries.s1_boundary_reason is None:
            local = _slice_sequence_input(
                sequence_input,
                start_us=timestamp - window_seconds * 1_000_000 - fp.GRID_US,
                end_us=timestamp,
            )
            s1, s1_reason = _capture_representation(
                sf.extract_sequence_summaries, local,
                decision_timestamp_us=timestamp, window_seconds=window_seconds, block=block,
            )
        else:
            s1, s1_reason = None, boundaries.s1_boundary_reason
        s0_reasons.append(s0_reason)
        s1_reasons.append(s1_reason)
        if s0 is not None:
            if tuple(s0) != s0_names:
                raise DirectionDatasetError("s0_feature_order_mismatch")
            s0_values[position] = [s0[name] for name in s0_names]
            s0_valid[position] = True
        if s1 is not None:
            if tuple(s1) != s1_names:
                raise DirectionDatasetError("s1_feature_order_mismatch")
            s1_values[position] = [s1[name] for name in s1_names]
            s1_valid[position] = True

    common_valid = sf.matched_common_support(
        decision_timestamps, s0_valid, s1_valid
    ).mask.astype(bool, copy=False)
    directional_target_valid = np.asarray([
        record["target_valid"] is True
        and t1_labels[position] != T1_EXCLUDED
        and target_future_valid[position]
        for position, record in enumerate(records)
    ], dtype=bool)
    t1_common = common_valid & directional_target_valid
    if not bool(np.array_equal(common_valid, s0_valid & s1_valid)):
        raise DirectionDatasetError("common_support_definition_mismatch")
    if not bool(np.array_equal(t1_common, common_valid & directional_target_valid)):
        raise DirectionDatasetError("t1_common_support_definition_mismatch")

    decisions = len(records)
    counts = {
        "decision_count": int(decisions), **_target_counts(records),
        "s0_native_support": int(np.count_nonzero(s0_valid)),
        "s1_native_support": int(np.count_nonzero(s1_valid)),
        "common_support_count": int(np.count_nonzero(common_valid)),
        "t1_common_support_count": int(np.count_nonzero(t1_common)),
        "t1_long_common_count": int(np.count_nonzero(t1_common & (t1_labels == 1))),
        "t1_short_common_count": int(np.count_nonzero(t1_common & (t1_labels == 0))),
        "common_support_fraction": float(np.count_nonzero(common_valid) / decisions) if decisions else None,
        "target_future_boundary_valid_count": int(np.count_nonzero(target_future_valid)),
        "target_future_boundary_invalid_count": int(decisions - np.count_nonzero(target_future_valid)),
        "s0_boundary_exclusion_reasons": dict(sorted(Counter(x for x in s0_boundaries if x).items())),
        "s1_boundary_exclusion_reasons": dict(sorted(Counter(x for x in s1_boundaries if x).items())),
        "target_future_boundary_exclusion_reasons": dict(sorted(Counter(x for x in target_boundaries if x).items())),
        "s0_invalid_reasons": dict(sorted(Counter(x for x in s0_reasons if x).items())),
        "s1_invalid_reasons": dict(sorted(Counter(x for x in s1_reasons if x).items())),
    }
    hashes = {
        "native_s0_support_sha256": _support_hash(decision_timestamps, s0_valid),
        "native_s1_support_sha256": _support_hash(decision_timestamps, s1_valid),
        "common_support_sha256": _support_hash(decision_timestamps, common_valid),
        "t1_common_support_sha256": _support_hash(decision_timestamps, t1_common),
    }
    return CandidateDayDataset(
        day_value, CandidateKey(target, window_seconds, block), decision_timestamps,
        tuple(dict(record) for record in records), t1_labels, s0_names, s1_names,
        s0_values, s1_values, s0_valid, s1_valid, common_valid, t1_common,
        target_future_valid, tuple(s0_boundaries), tuple(s1_boundaries),
        tuple(target_boundaries), tuple(s0_reasons), tuple(s1_reasons), counts, hashes,
    )


def _concatenate_side(
    datasets: Sequence[CandidateDayDataset],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    timestamps = np.concatenate([item.decision_timestamps_us for item in datasets])
    s0 = np.concatenate([item.s0_valid for item in datasets])
    s1 = np.concatenate([item.s1_valid for item in datasets])
    common = np.concatenate([item.common_valid for item in datasets])
    t1 = np.concatenate([item.t1_common_valid for item in datasets])
    labels = np.concatenate([item.t1_labels for item in datasets])
    if len(timestamps) and bool(np.any(np.diff(timestamps) <= 0)):
        raise DirectionDatasetError("fold_support_not_chronological")
    return timestamps, s0, s1, common, t1, labels


def build_fold_supports(per_day: Mapping[date, CandidateDayDataset]) -> tuple[FoldSupport, ...]:
    if tuple(sorted(per_day)) != HISTORICAL_DAYS:
        raise DirectionDatasetError("fold_dataset_calendar_mismatch")
    keys = {dataset.key for dataset in per_day.values()}
    if len(keys) != 1:
        raise DirectionDatasetError("fold_candidate_key_mismatch")
    key = next(iter(keys))
    results: list[FoldSupport] = []
    for fold in OUTER_FOLDS:
        train = _concatenate_side([per_day[day] for day in fold.train_days])
        validation = _concatenate_side([per_day[fold.validation_day]])
        train_ts, train_s0, train_s1, train_common, train_t1, train_labels = train
        val_ts, val_s0, val_s1, val_common, val_t1, val_labels = validation
        if len(train_ts) and len(val_ts):
            train_target_end = int(train_ts[-1]) + fp.GRID_US + key.target.horizon_seconds * 1_000_000
            if train_target_end >= _utc_day_bounds(fold.validation_day)[0]:
                raise DirectionDatasetError("training_target_reaches_validation_period")
        train_indices = np.flatnonzero(train_t1).astype(np.int64, copy=False)
        val_indices = np.flatnonzero(val_t1).astype(np.int64, copy=False)
        train_t1_ts = train_ts[train_indices].astype(np.int64, copy=False)
        val_t1_ts = val_ts[val_indices].astype(np.int64, copy=False)
        hashes = {
            "train_native_s0_support_sha256": _support_hash(train_ts, train_s0),
            "train_native_s1_support_sha256": _support_hash(train_ts, train_s1),
            "train_common_support_sha256": _support_hash(train_ts, train_common),
            "train_t1_common_support_sha256": support_sha256(train_t1_ts),
            "validation_native_s0_support_sha256": _support_hash(val_ts, val_s0),
            "validation_native_s1_support_sha256": _support_hash(val_ts, val_s1),
            "validation_common_support_sha256": _support_hash(val_ts, val_common),
            "validation_t1_common_support_sha256": support_sha256(val_t1_ts),
            "train_support_sha256": support_sha256(train_t1_ts),
            "validation_support_sha256": support_sha256(val_t1_ts),
        }
        results.append(FoldSupport(
            fold, key, train_ts, val_ts, train_indices, val_indices, train_t1_ts, val_t1_ts,
            {"long": int(np.count_nonzero(train_t1 & (train_labels == 1))),
             "short": int(np.count_nonzero(train_t1 & (train_labels == 0)))},
            {"long": int(np.count_nonzero(val_t1 & (val_labels == 1))),
             "short": int(np.count_nonzero(val_t1 & (val_labels == 0)))},
            hashes,
        ))
    return tuple(results)


def frozen_configuration_metadata() -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "symbol": SYMBOL,
        "historical_days": [day.isoformat() for day in HISTORICAL_DAYS],
        "targets": [
            {"target_id": item.target_id, "horizon_seconds": item.horizon_seconds,
             "barrier_bps": item.barrier_bps} for item in FROZEN_TARGETS
        ],
        "windows_seconds": list(FROZEN_WINDOWS_SECONDS),
        "blocks": list(FROZEN_BLOCKS),
        "decision_step_us": DECISION_STEP_US,
        "latency_ms": fp.LATENCY_MS,
        "allowed_feature_count": len(sf.ALLOWED_FEATURES),
        "signed_feature_count": len(sf.NATURALLY_SIGNED_FEATURES),
        "block_internal_lookback_ns": {
            block: sf.block_internal_lookback_ns(block) for block in FROZEN_BLOCKS
        },
        "required_csv_schema": list(EXPECTED_CSV_COLUMNS),
        "source_feature_order": list(SOURCE_FEATURE_ORDER),
        "first_passage_source_path": FIRST_PASSAGE_SOURCE_REL,
        "first_passage_source_sha256": FIRST_PASSAGE_SOURCE_SHA256,
        "sequence_feature_source_path": SEQUENCE_FEATURE_SOURCE_REL,
        "sequence_feature_source_sha256": SEQUENCE_FEATURE_SOURCE_SHA256,
        "support_hash_encoding": (
            "ASCII domain DEV030-P2B-SUPPORT-TIMESTAMPS-US-V1\\0; "
            "uint64 big-endian count; chronological int64 big-endian timestamps_us"
        ),
    }

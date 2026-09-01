from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from multimarket import dev030_direction_dataset as dd
from multimarket import dev030_first_passage as fp
from multimarket import dev030_sequence_features as sf


def _record(
    label: str | None,
    *,
    target_valid: bool = True,
    invalid_reason: str | None = None,
    same_row_ambiguous: bool = False,
) -> dict[str, object]:
    return {
        "label": label,
        "target_valid": target_valid,
        "invalid_reason": invalid_reason,
        "same_row_ambiguous": same_row_ambiguous,
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_fixture(tmp_path: Path) -> tuple[Path, tuple[dd.FrozenSourceIdentity, ...]]:
    root = tmp_path / "repository"
    first = root / dd.FIRST_PASSAGE_SOURCE_REL
    sequence = root / dd.SEQUENCE_FEATURE_SOURCE_REL
    first.parent.mkdir(parents=True)
    first.write_bytes(b"frozen-first-passage\n")
    sequence.write_bytes(b"frozen-sequence-features\n")
    identities = (
        dd.FrozenSourceIdentity(
            "first_passage",
            dd.FIRST_PASSAGE_SOURCE_REL,
            _sha(first),
            "first_passage_source_sha256_mismatch",
        ),
        dd.FrozenSourceIdentity(
            "sequence_features",
            dd.SEQUENCE_FEATURE_SOURCE_REL,
            _sha(sequence),
            "sequence_feature_source_sha256_mismatch",
        ),
    )
    return root, identities


def _input_fixture(tmp_path: Path) -> tuple[dict[date, Path], dict[date, str]]:
    root = tmp_path / "inputs"
    root.mkdir()
    paths: dict[date, Path] = {}
    hashes: dict[date, str] = {}
    for day in dd.HISTORICAL_DAYS:
        path = root / f"{day.isoformat()}_FEATURES250.csv"
        path.write_bytes(f"synthetic-{day.isoformat()}\n".encode("ascii"))
        paths[day] = path
        hashes[day] = _sha(path)
    return paths, hashes


@dataclass
class _SyntheticDay:
    day: date
    ts: np.ndarray
    bid: np.ndarray
    ask: np.ndarray
    mid: np.ndarray
    book_valid: np.ndarray
    valid: dict[str, np.ndarray]
    X: dict[str, np.ndarray]


def _synthetic_day(*, final_timestamp_us: int = 240_000_000) -> _SyntheticDay:
    timestamps = np.arange(0, final_timestamp_us + fp.GRID_US, fp.GRID_US, dtype=np.int64)
    rows = len(timestamps)
    matrix = np.empty((rows, len(dd.SOURCE_FEATURE_ORDER)), dtype=np.float64)
    for column in range(matrix.shape[1]):
        matrix[:, column] = 0.01 * (column + 1) + timestamps / 1_000_000_000_000.0
    valid = np.ones(rows, dtype=bool)
    return _SyntheticDay(
        day=date(1970, 1, 1),
        ts=timestamps,
        bid=np.full(rows, 99.9),
        ask=np.full(rows, 100.1),
        mid=np.full(rows, 100.0),
        book_valid=valid.copy(),
        valid={"L0": valid.copy(), "L1": valid.copy(), "L2": valid.copy()},
        X={"L2": matrix},
    )


def _boundary_records() -> list[dict[str, object]]:
    # Decisions are 0, 60, 120, 180, and 240 seconds. The synthetic UTC-day
    # boundary is injected separately by the tests.
    return [
        _record(None, target_valid=False, invalid_reason="missing_entry_timestamp"),
        _record(fp.LONG_FIRST),
        _record(fp.SHORT_FIRST),
        _record(None, target_valid=False, invalid_reason="day_boundary_crossing"),
        _record(None, target_valid=False, invalid_reason="day_boundary_crossing"),
    ]


def _build_boundary_dataset(
    monkeypatch: pytest.MonkeyPatch,
    *,
    records: list[dict[str, object]] | None = None,
) -> dd.CandidateDayDataset:
    # last exact grid row is 240 seconds, so end is the following 250 ms.
    monkeypatch.setattr(dd, "_utc_day_bounds", lambda unused: (0, 240_250_000))
    return dd.build_candidate_day(
        _synthetic_day(),
        target=dd.FROZEN_TARGETS[3],
        window_seconds=60,
        block=sf.PRICE_BOOK_FLOW_DYNAMICS,
        target_records=_boundary_records() if records is None else records,
    )


def test_exact_frozen_campaign_constants() -> None:
    assert dd.DECISION_STEP_US == 60_000_000
    assert tuple((x.target_id, x.horizon_seconds, x.barrier_bps) for x in dd.FROZEN_TARGETS) == (
        ("A", 120, 16),
        ("B", 300, 24),
        ("C", 300, 12),
        ("D", 60, 8),
    )
    assert dd.FROZEN_WINDOWS_SECONDS == (8, 16, 32, 60)
    assert dd.FROZEN_BLOCKS == (
        "PRICE",
        "PRICE_BOOK",
        "PRICE_BOOK_FLOW",
        "PRICE_BOOK_FLOW_DYNAMICS",
    )


@pytest.mark.parametrize(
    ("record", "expected_label", "expected_reason"),
    [
        (_record(fp.LONG_FIRST), 1, None),
        (_record(fp.SHORT_FIRST), 0, None),
        (_record(fp.NONE), None, dd.EXCLUDE_NONE),
        (_record(None, target_valid=False, invalid_reason="invalid_path_quote"), None, "invalid_path_quote"),
        (
            _record(
                None,
                target_valid=False,
                invalid_reason="same_row_ambiguous",
                same_row_ambiguous=True,
            ),
            None,
            "same_row_ambiguous",
        ),
    ],
)
def test_t1_mapping(record: dict[str, object], expected_label: int | None, expected_reason: str | None) -> None:
    assert dd.map_t1_record(record) == (expected_label, expected_reason)


def test_actual_frozen_source_identities_pass() -> None:
    verified = dd.verify_frozen_source_identities(Path(dd.__file__).resolve().parents[2])
    assert [item.sha256 for item in verified] == [
        dd.FIRST_PASSAGE_SOURCE_SHA256,
        dd.SEQUENCE_FEATURE_SOURCE_SHA256,
    ]
    assert all(item.sha256_verified is True for item in verified)


def test_first_passage_source_mismatch_precedes_header_and_loader(tmp_path: Path) -> None:
    root, identities = _source_fixture(tmp_path)
    bad = list(identities)
    bad[0] = dd.FrozenSourceIdentity(
        bad[0].name, bad[0].relative_path, "0" * 64, bad[0].mismatch_reason
    )
    calls = {"header": 0, "loader": 0}

    with pytest.raises(dd.DirectionDatasetError, match="first_passage_source_sha256_mismatch"):
        dd._load_verified_authorized_days(
            repository_root=root,
            source_identities=tuple(bad),
            source_hash_file=_sha,
            input_paths={},
            expected_input_hashes={},
            input_hash_file=_sha,
            header_reader=lambda path: calls.__setitem__("header", calls["header"] + 1),
            loader=lambda path, day: calls.__setitem__("loader", calls["loader"] + 1),
        )
    assert calls == {"header": 0, "loader": 0}


def test_sequence_source_mismatch_precedes_header_and_loader(tmp_path: Path) -> None:
    root, identities = _source_fixture(tmp_path)
    bad = list(identities)
    bad[1] = dd.FrozenSourceIdentity(
        bad[1].name, bad[1].relative_path, "f" * 64, bad[1].mismatch_reason
    )
    calls = {"header": 0, "loader": 0}

    with pytest.raises(dd.DirectionDatasetError, match="sequence_feature_source_sha256_mismatch"):
        dd._load_verified_authorized_days(
            repository_root=root,
            source_identities=tuple(bad),
            source_hash_file=_sha,
            input_paths={},
            expected_input_hashes={},
            input_hash_file=_sha,
            header_reader=lambda path: calls.__setitem__("header", calls["header"] + 1),
            loader=lambda path, day: calls.__setitem__("loader", calls["loader"] + 1),
        )
    assert calls == {"header": 0, "loader": 0}


def test_missing_frozen_source_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(dd.DirectionDatasetError, match="frozen_source_missing"):
        dd.verify_frozen_source_identities(tmp_path)


def test_exact_source_feature_order_passes() -> None:
    assert dd.verify_phase0dl_feature_order() == sf.ALLOWED_STORED_FEATURES
    assert dd.SOURCE_FEATURE_ORDER == sf.ALLOWED_STORED_FEATURES


def test_same_length_reordered_source_manifest_fails_closed() -> None:
    reordered = list(dd.SOURCE_FEATURE_ORDER)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    assert len(reordered) == len(dd.SOURCE_FEATURE_ORDER)
    with pytest.raises(dd.DirectionDatasetError, match="phase0dl_feature_order_mismatch"):
        dd.verify_phase0dl_feature_order(reordered)


def test_reordered_feature_manifest_fails_before_header_and_loader(tmp_path: Path) -> None:
    root, identities = _source_fixture(tmp_path)
    paths, hashes = _input_fixture(tmp_path)
    reordered = list(dd.SOURCE_FEATURE_ORDER)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    calls = {"header": 0, "loader": 0}

    with pytest.raises(dd.DirectionDatasetError, match="phase0dl_feature_order_mismatch"):
        dd._load_verified_authorized_days(
            repository_root=root,
            source_identities=identities,
            source_feature_order=reordered,
            source_hash_file=_sha,
            input_paths=paths,
            expected_input_hashes=hashes,
            input_hash_file=_sha,
            header_reader=lambda path: calls.__setitem__("header", calls["header"] + 1),
            loader=lambda path, day: calls.__setitem__("loader", calls["loader"] + 1),
        )

    assert len(reordered) == len(dd.SOURCE_FEATURE_ORDER)
    assert calls == {"header": 0, "loader": 0}


def test_feature_order_guard_precedes_positional_l2_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"mapped": 0}

    def reject() -> tuple[str, ...]:
        calls["mapped"] += 1
        raise dd.DirectionDatasetError("phase0dl_feature_order_mismatch")

    monkeypatch.setattr(dd, "verify_phase0dl_feature_order", reject)
    with pytest.raises(dd.DirectionDatasetError, match="phase0dl_feature_order_mismatch"):
        dd._validate_day_structure(_synthetic_day())
    assert calls["mapped"] == 1


def test_jan_jul_hash_mismatch_precedes_header_and_loader(tmp_path: Path) -> None:
    root, identities = _source_fixture(tmp_path)
    paths, hashes = _input_fixture(tmp_path)
    hashes[dd.HISTORICAL_DAYS[2]] = "0" * 64
    calls = {"header": 0, "loader": 0}

    with pytest.raises(dd.DirectionDatasetError, match="authorized_input_sha256_mismatch"):
        dd._load_verified_authorized_days(
            repository_root=root,
            source_identities=identities,
            source_hash_file=_sha,
            input_paths=paths,
            expected_input_hashes=hashes,
            input_hash_file=_sha,
            header_reader=lambda path: calls.__setitem__("header", calls["header"] + 1),
            loader=lambda path, day: calls.__setitem__("loader", calls["loader"] + 1),
        )
    assert calls == {"header": 0, "loader": 0}


def test_csv_schema_mismatch_precedes_analytical_loader(tmp_path: Path) -> None:
    root, identities = _source_fixture(tmp_path)
    paths, hashes = _input_fixture(tmp_path)
    calls = {"header": 0, "loader": 0}

    def bad_header(unused: Path) -> tuple[str, ...]:
        calls["header"] += 1
        return dd.EXPECTED_CSV_COLUMNS[:-1]

    with pytest.raises(dd.DirectionDatasetError, match="csv_schema_mismatch"):
        dd._load_verified_authorized_days(
            repository_root=root,
            source_identities=identities,
            source_hash_file=_sha,
            input_paths=paths,
            expected_input_hashes=hashes,
            input_hash_file=_sha,
            header_reader=bad_header,
            loader=lambda path, day: calls.__setitem__("loader", calls["loader"] + 1),
        )
    assert calls == {"header": 1, "loader": 0}


def test_complete_guard_order_allows_only_fully_verified_synthetic_load(tmp_path: Path) -> None:
    root, identities = _source_fixture(tmp_path)
    paths, hashes = _input_fixture(tmp_path)
    loaded: list[date] = []
    result = dd._load_verified_authorized_days(
        repository_root=root,
        source_identities=identities,
        source_hash_file=_sha,
        input_paths=paths,
        expected_input_hashes=hashes,
        input_hash_file=_sha,
        header_reader=lambda path: dd.EXPECTED_CSV_COLUMNS,
        loader=lambda path, day: loaded.append(day) or day.isoformat(),
    )
    assert loaded == list(dd.HISTORICAL_DAYS)
    assert result == tuple(day.isoformat() for day in dd.HISTORICAL_DAYS)


def test_exact_minute_grid_and_no_shuffle() -> None:
    timestamps = np.arange(0, 121_000_000, fp.GRID_US, dtype=np.int64)
    indices = dd.exact_minute_decision_indices(timestamps)
    assert timestamps[indices].tolist() == [0, 60_000_000, 120_000_000]


@pytest.mark.parametrize(
    ("timestamps", "reason"),
    [
        (np.array([0, 250_000, 250_000], dtype=np.int64), "duplicate_timestamps"),
        (np.array([0, 500_000, 250_000], dtype=np.int64), "non_monotonic_timestamps"),
        (np.array([0, 250_001], dtype=np.int64), "off_grid_timestamp"),
    ],
)
def test_bad_timestamp_sequences_fail(timestamps: np.ndarray, reason: str) -> None:
    with pytest.raises(dd.DirectionDatasetError, match=reason):
        dd.exact_minute_decision_indices(timestamps)


def test_native_s0_s1_and_target_boundaries_are_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    built = _build_boundary_dataset(monkeypatch)
    positions = {int(ts): i for i, ts in enumerate(built.decision_timestamps_us)}
    early = positions[60_000_000]
    late = positions[180_000_000]

    assert built.s0_valid[early]
    assert not built.s1_valid[early]
    assert built.s0_boundary_reasons[early] is None
    assert built.s1_boundary_reasons[early] == dd.S1_BOUNDARY_BEFORE_DAY

    assert built.s0_valid[late]
    assert built.s1_valid[late]
    assert not built.target_future_boundary_valid[late]
    assert built.target_boundary_reasons[late] == dd.TARGET_BOUNDARY_AFTER_DAY
    assert np.array_equal(built.common_valid, built.s0_valid & built.s1_valid)
    assert np.array_equal(
        built.t1_common_valid,
        built.common_valid
        & (built.t1_labels != dd.T1_EXCLUDED)
        & built.target_future_boundary_valid,
    )


def test_target_boundary_does_not_change_native_support_or_hashes(monkeypatch: pytest.MonkeyPatch) -> None:
    built = _build_boundary_dataset(monkeypatch)
    records = _boundary_records()
    records[2] = _record(None, target_valid=False, invalid_reason="invalid_path_quote")
    changed_targets = _build_boundary_dataset(monkeypatch, records=records)
    assert np.array_equal(built.s0_valid, changed_targets.s0_valid)
    assert np.array_equal(built.s1_valid, changed_targets.s1_valid)
    assert built.support_hashes["native_s0_support_sha256"] == changed_targets.support_hashes["native_s0_support_sha256"]
    assert built.support_hashes["native_s1_support_sha256"] == changed_targets.support_hashes["native_s1_support_sha256"]
    assert built.support_hashes["t1_common_support_sha256"] != changed_targets.support_hashes["t1_common_support_sha256"]


def test_frozen_target_counts_preserve_original_records() -> None:
    records = [
        _record(fp.LONG_FIRST),
        _record(fp.SHORT_FIRST),
        _record(fp.NONE),
        _record(None, target_valid=False, invalid_reason="invalid_path_quote"),
        _record(
            None,
            target_valid=False,
            invalid_reason="same_row_ambiguous",
            same_row_ambiguous=True,
        ),
    ]
    assert dd._target_counts(records) == {
        "valid_target_count": 3,
        "invalid_target_count": 2,
        "long_first_count": 1,
        "short_first_count": 1,
        "none_count": 1,
        "invalid_target_reasons": {"invalid_path_quote": 1, "same_row_ambiguous": 1},
    }


def test_future_boundary_counts_are_separate(monkeypatch: pytest.MonkeyPatch) -> None:
    built = _build_boundary_dataset(monkeypatch)
    assert built.counts["valid_target_count"] == 2
    assert built.counts["invalid_target_count"] == 3
    assert built.counts["invalid_target_reasons"] == {
        "day_boundary_crossing": 2,
        "missing_entry_timestamp": 1,
    }
    assert built.counts["target_future_boundary_valid_count"] == 3
    assert built.counts["target_future_boundary_invalid_count"] == 2
    assert built.counts["target_future_boundary_exclusion_reasons"] == {
        dd.TARGET_BOUNDARY_AFTER_DAY: 2
    }


def test_boundary_invalid_but_frozen_valid_raises_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    records = _boundary_records()
    records[3] = _record(fp.LONG_FIRST)
    with pytest.raises(dd.DirectionDatasetError, match="target_boundary_labeler_mismatch"):
        _build_boundary_dataset(monkeypatch, records=records)


def test_boundary_valid_with_other_frozen_invalid_reason_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    records = _boundary_records()
    records[1] = _record(None, target_valid=False, invalid_reason="invalid_path_quote")
    built = _build_boundary_dataset(monkeypatch, records=records)
    position = int(np.flatnonzero(built.decision_timestamps_us == 60_000_000)[0])
    assert built.target_future_boundary_valid[position]
    assert not built.t1_common_valid[position]
    assert built.s0_valid[position]


def test_s1_failure_does_not_invalidate_s0(monkeypatch: pytest.MonkeyPatch) -> None:
    built = _build_boundary_dataset(monkeypatch)
    position = int(np.flatnonzero(built.decision_timestamps_us == 60_000_000)[0])
    assert built.s0_valid[position] and not built.s1_valid[position]
    assert built.counts["s0_native_support"] > built.counts["s1_native_support"]


def test_build_candidate_uses_frozen_s0_and_s1_extractors(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"s0": 0, "s1": 0}
    original_s0 = sf.extract_snapshot
    original_s1 = sf.extract_sequence_summaries

    def s0(*args: object, **kwargs: object) -> dict[str, float]:
        calls["s0"] += 1
        return original_s0(*args, **kwargs)

    def s1(*args: object, **kwargs: object) -> dict[str, float]:
        calls["s1"] += 1
        return original_s1(*args, **kwargs)

    monkeypatch.setattr(sf, "extract_snapshot", s0)
    monkeypatch.setattr(sf, "extract_sequence_summaries", s1)
    _build_boundary_dataset(monkeypatch)
    assert calls["s0"] > 0
    assert calls["s1"] > 0


def test_support_hash_is_deterministic_and_membership_only() -> None:
    timestamps = np.array(
        [1_000_000, 2_000_000, 3_000_000, 4_000_000], dtype=np.int64
    )
    support_mask = np.array([True, False, True, True], dtype=bool)
    first_context = {
        "timestamps_us": timestamps.copy(),
        "support_mask": support_mask.copy(),
        "irrelevant_feature_values": np.array([1.0, 2.0, 3.0, 4.0]),
        "irrelevant_payload": {"candidate": "first", "count": 4},
    }
    second_context = {
        "timestamps_us": timestamps.copy(),
        "support_mask": support_mask.copy(),
        "irrelevant_feature_values": np.array([-99.0, 500.0, 0.0, 1_000.0]),
        "irrelevant_payload": {"candidate": "second", "count": 999},
    }

    first_hash = dd._support_hash(
        first_context["timestamps_us"], first_context["support_mask"]
    )
    second_hash = dd._support_hash(
        second_context["timestamps_us"], second_context["support_mask"]
    )
    assert not np.array_equal(
        first_context["irrelevant_feature_values"],
        second_context["irrelevant_feature_values"],
    )
    assert first_context["irrelevant_payload"] != second_context["irrelevant_payload"]
    assert first_hash == second_hash

    changed_membership = support_mask.copy()
    changed_membership[1] = True
    assert dd._support_hash(timestamps, changed_membership) != first_hash


def test_support_hash_encoding_is_explicit_and_chronological() -> None:
    timestamps = np.array([250_000, 60_000_000], dtype=np.int64)
    encoded = dd.canonical_support_bytes(timestamps)
    assert encoded.startswith(dd.SUPPORT_HASH_DOMAIN)
    assert hashlib.sha256(encoded).hexdigest() == dd.support_sha256(timestamps)
    with pytest.raises(dd.DirectionDatasetError, match="support_not_unique_chronological"):
        dd.support_sha256(timestamps[::-1])


def _dummy_candidate_day(
    day_value: date,
    key: dd.CandidateKey,
    *,
    timestamp_us: int | None = None,
    label: int = 1,
) -> dd.CandidateDayDataset:
    start = int(datetime(day_value.year, day_value.month, day_value.day, tzinfo=timezone.utc).timestamp()) * 1_000_000
    timestamps = np.array([start + 60_000_000 if timestamp_us is None else timestamp_us], dtype=np.int64)
    truth = np.ones(1, dtype=bool)
    labels = np.array([label], dtype=np.int8)
    hashes = {
        "native_s0_support_sha256": dd.support_sha256(timestamps),
        "native_s1_support_sha256": dd.support_sha256(timestamps),
        "common_support_sha256": dd.support_sha256(timestamps),
        "t1_common_support_sha256": dd.support_sha256(timestamps),
    }
    return dd.CandidateDayDataset(
        day_value,
        key,
        timestamps,
        tuple(),
        labels,
        tuple(),
        tuple(),
        np.empty((1, 0)),
        np.empty((1, 0)),
        truth.copy(),
        truth.copy(),
        truth.copy(),
        truth.copy(),
        truth.copy(),
        (None,),
        (None,),
        (None,),
        (None,),
        (None,),
        {},
        hashes,
    )


def test_exact_four_expanding_outer_folds_and_chronology() -> None:
    assert tuple((fold.train_days, fold.validation_day) for fold in dd.OUTER_FOLDS) == (
        (dd.HISTORICAL_DAYS[:3], dd.HISTORICAL_DAYS[3]),
        (dd.HISTORICAL_DAYS[:4], dd.HISTORICAL_DAYS[4]),
        (dd.HISTORICAL_DAYS[:5], dd.HISTORICAL_DAYS[5]),
        (dd.HISTORICAL_DAYS[:6], dd.HISTORICAL_DAYS[6]),
    )
    key = dd.CandidateKey(dd.FROZEN_TARGETS[0], 8, sf.PRICE)
    per_day = {
        day: _dummy_candidate_day(day, key, label=index % 2)
        for index, day in enumerate(dd.HISTORICAL_DAYS)
    }
    folds = dd.build_fold_supports(per_day)
    assert len(folds) == 4
    for result in folds:
        assert np.all(np.diff(result.train_decision_timestamps_us) > 0)
        assert np.all(result.train_decision_timestamps_us < result.validation_decision_timestamps_us[0])
        assert np.array_equal(
            result.train_t1_common_indices,
            np.arange(len(result.train_t1_common_indices)),
        )


def test_training_target_interval_cannot_reach_validation_period() -> None:
    key = dd.CandidateKey(dd.FROZEN_TARGETS[1], 8, sf.PRICE)
    per_day = {day: _dummy_candidate_day(day, key) for day in dd.HISTORICAL_DAYS}
    april_start = int(datetime(2026, 4, 1, tzinfo=timezone.utc).timestamp()) * 1_000_000
    per_day[date(2026, 3, 1)] = _dummy_candidate_day(
        date(2026, 3, 1), key, timestamp_us=april_start - 100_000_000
    )
    with pytest.raises(dd.DirectionDatasetError, match="training_target_reaches_validation_period"):
        dd.build_fold_supports(per_day)


def test_metadata_is_json_safe_and_records_frozen_provenance() -> None:
    metadata = dd.frozen_configuration_metadata()
    serialized = json.dumps(metadata, allow_nan=False, sort_keys=True)
    assert json.loads(serialized)["decision_step_us"] == 60_000_000
    assert metadata["first_passage_source_sha256"] == dd.FIRST_PASSAGE_SOURCE_SHA256
    assert metadata["sequence_feature_source_sha256"] == dd.SEQUENCE_FEATURE_SOURCE_SHA256
    assert metadata["source_feature_order"] == list(dd.SOURCE_FEATURE_ORDER)


def test_authorization_excludes_future_days_and_other_symbols() -> None:
    with pytest.raises(dd.DirectionDatasetError, match="unauthorized_historical_day"):
        dd.authorized_input_path(date(2026, 8, 30))
    with pytest.raises(dd.DirectionDatasetError, match="unauthorized_historical_day"):
        dd.authorized_input_path(date(2026, 9, 1))
    with pytest.raises(dd.DirectionDatasetError, match="unauthorized_symbol"):
        dd.authorized_input_path(date(2026, 1, 1), symbol="ETHUSDT")
    with pytest.raises(dd.DirectionDatasetError, match="unauthorized_symbol"):
        dd.authorized_input_path(date(2026, 1, 1), symbol="SOLUSDT")


def test_module_has_no_model_predictive_metric_or_economic_dependency() -> None:
    source = inspect.getsource(dd)
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert not ({"sklearn", "xgboost", "lightgbm", "catboost"} & imports)
    function_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert not any(name.startswith(("fit_", "score_", "backtest_")) for name in function_names)
    assert not ({"balanced_accuracy", "macro_f1", "mcc", "profit_factor", "pnl"} & function_names)

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping

import numpy as np
import pytest

from multimarket import dev030_direction_dataset as dd
from multimarket import dev030_direction_materialize as dm


COMMIT = "a" * 40
_DEFAULT_VERIFICATION = object()


def _reason(callable_: Callable[..., Any], *args: Any, **kwargs: Any) -> str:
    with pytest.raises(dm.DirectionMaterializationError) as caught:
        callable_(*args, **kwargs)
    return caught.value.reason


def _verified_builder() -> dict[str, Any]:
    return {
        "path": dm.FROZEN_BUILDER_SOURCE_REL,
        "sha256": dm.FROZEN_BUILDER_SOURCE_SHA256,
        "sha256_verified": True,
    }


def _day_timestamp_us(day_value: date, seconds: int) -> int:
    midnight = datetime(
        day_value.year,
        day_value.month,
        day_value.day,
        tzinfo=timezone.utc,
    )
    return int(midnight.timestamp() * 1_000_000) + seconds * 1_000_000


def _candidate_day(
    key: dd.CandidateKey,
    day_value: date,
) -> dd.CandidateDayDataset:
    timestamps = np.asarray(
        [
            _day_timestamp_us(day_value, 12 * 3600),
            _day_timestamp_us(day_value, 12 * 3600 + 60),
        ],
        dtype=np.int64,
    )
    valid = np.ones(2, dtype=bool)
    support_hash = dd.support_sha256(timestamps)
    return dd.CandidateDayDataset(
        day=day_value,
        key=key,
        decision_timestamps_us=timestamps,
        target_records=(
            {"label": "LONG_FIRST", "target_valid": True},
            {"label": "SHORT_FIRST", "target_valid": True},
        ),
        t1_labels=np.asarray([1, 0], dtype=np.int8),
        s0_feature_names=("synthetic",),
        s1_feature_names=("synthetic__last",),
        s0_values=np.asarray([[1.0], [2.0]], dtype=np.float64),
        s1_values=np.asarray([[3.0], [4.0]], dtype=np.float64),
        s0_valid=valid.copy(),
        s1_valid=valid.copy(),
        common_valid=valid.copy(),
        t1_common_valid=valid.copy(),
        target_future_boundary_valid=valid.copy(),
        s0_boundary_reasons=(None, None),
        s1_boundary_reasons=(None, None),
        target_boundary_reasons=(None, None),
        s0_invalid_reasons=(None, None),
        s1_invalid_reasons=(None, None),
        counts={
            "decision_count": 2,
            "valid_target_count": 2,
            "invalid_target_count": 0,
            "long_first_count": 1,
            "short_first_count": 1,
            "none_count": 0,
            "s0_native_support": 2,
            "s1_native_support": 2,
            "common_support_count": 2,
            "t1_common_support_count": 2,
            "t1_long_common_count": 1,
            "t1_short_common_count": 1,
            "target_future_boundary_valid_count": 2,
            "target_future_boundary_invalid_count": 0,
            "common_support_fraction": 1.0,
            "invalid_target_reasons": {},
            "s0_boundary_exclusion_reasons": {},
            "s1_boundary_exclusion_reasons": {},
            "target_future_boundary_exclusion_reasons": {},
            "s0_invalid_reasons": {},
            "s1_invalid_reasons": {},
        },
        support_hashes={
            "native_s0_support_sha256": support_hash,
            "native_s1_support_sha256": support_hash,
            "common_support_sha256": support_hash,
            "t1_common_support_sha256": support_hash,
        },
    )


def _candidate_grid() -> dict[dd.CandidateKey, dict[date, dd.CandidateDayDataset]]:
    return {
        key: {day: _candidate_day(key, day) for day in dd.HISTORICAL_DAYS}
        for key in dm.frozen_candidate_keys()
    }


def _manifest(tmp_path: Path) -> tuple[dd.InputManifestEntry, ...]:
    return tuple(
        dd.InputManifestEntry(
            day,
            tmp_path / f"synthetic-{day.isoformat()}.csv",
            hashlib.sha256(day.isoformat().encode("ascii")).hexdigest(),
            100 + position,
        )
        for position, day in enumerate(dd.HISTORICAL_DAYS)
    )


def _payload(
    tmp_path: Path,
    *,
    candidate_days: Mapping[
        dd.CandidateKey, Mapping[date, dd.CandidateDayDataset]
    ] | None = None,
    input_manifest: tuple[dd.InputManifestEntry, ...] | None = None,
    runtime_state: Mapping[str, Any] | None = None,
    builder_verification: object = _DEFAULT_VERIFICATION,
) -> dict[str, Any]:
    verification = (
        _verified_builder()
        if builder_verification is _DEFAULT_VERIFICATION
        else builder_verification
    )
    return dm.build_materialization_payload(
        created_by_commit=COMMIT,
        input_manifest=_manifest(tmp_path) if input_manifest is None else input_manifest,
        candidate_days=_candidate_grid() if candidate_days is None else candidate_days,
        runtime_state=(
            dm.runtime_provenance(jan_jul_analytically_opened=False)
            if runtime_state is None
            else runtime_state
        ),
        builder_verification=verification,  # type: ignore[arg-type]
    )


def _replace_first_day(
    grid: dict[dd.CandidateKey, dict[date, dd.CandidateDayDataset]],
    dataset: dd.CandidateDayDataset,
) -> None:
    first_key = dm.frozen_candidate_keys()[0]
    grid[first_key][dd.HISTORICAL_DAYS[0]] = dataset


def _with_counts(
    dataset: dd.CandidateDayDataset,
    **updates: Any,
) -> dd.CandidateDayDataset:
    counts = dict(dataset.counts)
    counts.update(updates)
    return replace(dataset, counts=counts)


def _first_day() -> dd.CandidateDayDataset:
    key = dm.frozen_candidate_keys()[0]
    return _candidate_day(key, dd.HISTORICAL_DAYS[0])


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    source = workspace / dm.FROZEN_BUILDER_SOURCE_REL
    source.parent.mkdir(parents=True)
    source.write_bytes(b"synthetic builder identity fixture\n")
    return workspace


def _loaded_days() -> tuple[SimpleNamespace, ...]:
    return tuple(SimpleNamespace(day=day) for day in dd.HISTORICAL_DAYS)


def _run_synthetic(
    tmp_path: Path,
    *,
    output: Path | None = None,
    manifest_verifier: Callable[[], Any] | None = None,
    analytical_day_loader: Callable[[], Any] | None = None,
    candidate_builder: Callable[[Any], Any] | None = None,
    payload_builder: Callable[..., Mapping[str, Any]] | None = None,
    builder_hash_file: Callable[[Path], str] | None = None,
) -> dm.ArtifactWriteResult:
    return dm.run_materialization(
        workspace=_workspace(tmp_path),
        output_directory=tmp_path / "materialized" if output is None else output,
        created_by_commit=COMMIT,
        manifest_verifier=(
            (lambda: _manifest(tmp_path))
            if manifest_verifier is None
            else manifest_verifier
        ),
        analytical_day_loader=(
            _loaded_days if analytical_day_loader is None else analytical_day_loader
        ),
        candidate_builder=(
            (lambda unused: _candidate_grid())
            if candidate_builder is None
            else candidate_builder
        ),
        payload_builder=(
            dm.build_materialization_payload
            if payload_builder is None
            else payload_builder
        ),
        builder_hash_file=(
            (lambda unused: dm.FROZEN_BUILDER_SOURCE_SHA256)
            if builder_hash_file is None
            else builder_hash_file
        ),
        require_canonical_output=False,
    )


@pytest.mark.parametrize(
    ("verification", "expected"),
    [
        (None, "builder_verification_required"),
        (
            {
                "path": "wrong.py",
                "sha256": dm.FROZEN_BUILDER_SOURCE_SHA256,
                "sha256_verified": True,
            },
            "invalid_builder_verification",
        ),
        (
            {
                "path": dm.FROZEN_BUILDER_SOURCE_REL,
                "sha256": "0" * 64,
                "sha256_verified": True,
            },
            "invalid_builder_verification",
        ),
        (
            {
                "path": dm.FROZEN_BUILDER_SOURCE_REL,
                "sha256": dm.FROZEN_BUILDER_SOURCE_SHA256,
                "sha256_verified": False,
            },
            "invalid_builder_verification",
        ),
    ],
)
def test_builder_verification_fails_closed(
    tmp_path: Path, verification: Mapping[str, Any] | None, expected: str
) -> None:
    assert _reason(_payload, tmp_path, builder_verification=verification) == expected


def test_valid_explicit_builder_verification_succeeds(tmp_path: Path) -> None:
    payload = _payload(tmp_path, builder_verification=_verified_builder())
    assert payload["frozen_builder_source_sha256_verified"] is True


def test_run_passes_explicit_builder_verification_and_opened_state(
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def payload_builder(**kwargs: Any) -> Mapping[str, Any]:
        captured.update(kwargs)
        return {"runtime_provenance": kwargs["runtime_state"]}

    result = _run_synthetic(tmp_path, payload_builder=payload_builder)
    assert captured["builder_verification"] == _verified_builder()
    runtime = captured["runtime_state"]
    assert runtime["jan_jul_analytically_opened"] is True
    assert runtime["authorized_development_data"]["analytically_loaded"] is True
    assert result.artifact_path.is_file()


def test_builder_sha_mismatch_precedes_manifest_and_loader(tmp_path: Path) -> None:
    calls = {"manifest": 0, "loader": 0}

    def manifest() -> tuple[Any, ...]:
        calls["manifest"] += 1
        return ()

    def loader() -> tuple[Any, ...]:
        calls["loader"] += 1
        return ()

    assert _reason(
        _run_synthetic,
        tmp_path,
        manifest_verifier=manifest,
        analytical_day_loader=loader,
        builder_hash_file=lambda unused: "0" * 64,
    ) == "frozen_builder_source_sha256_mismatch"
    assert calls == {"manifest": 0, "loader": 0}


def test_runtime_provenance_records_explicit_development_state() -> None:
    closed = dm.runtime_provenance(jan_jul_analytically_opened=False)
    opened = dm.runtime_provenance(jan_jul_analytically_opened=True)
    assert closed["jan_jul_analytically_opened"] is False
    assert closed["authorized_development_data"]["analytically_loaded"] is False
    assert opened["jan_jul_analytically_opened"] is True
    assert opened["authorized_development_data"]["analytically_loaded"] is True


def test_contradictory_runtime_state_fails() -> None:
    state = dm.runtime_provenance(jan_jul_analytically_opened=False)
    state["authorized_development_data"]["analytically_loaded"] = True
    assert _reason(dm.validate_runtime_provenance, state) == (
        "contradictory_development_runtime_state"
    )


def test_malformed_runtime_schema_fails() -> None:
    state = dm.runtime_provenance(jan_jul_analytically_opened=False)
    del state["campaign_1_run"]
    assert _reason(dm.validate_runtime_provenance, state) == (
        "runtime_provenance_schema_mismatch"
    )


@pytest.mark.parametrize("guard", tuple(dm.FORWARD_DATA_GUARDS))
def test_forward_runtime_guards_must_remain_false(guard: str) -> None:
    state = dm.runtime_provenance(jan_jul_analytically_opened=False)
    state["forward_data_guards"][guard] = True
    assert _reason(dm.validate_runtime_provenance, state) == (
        "forward_data_guard_violation"
    )


@pytest.mark.parametrize("field", ("model_fit_run", "campaign_1_run", "pnl_backtest_run"))
def test_prohibited_runtime_activities_must_remain_false(field: str) -> None:
    state = dm.runtime_provenance(jan_jul_analytically_opened=False)
    state[field] = True
    assert _reason(dm.validate_runtime_provenance, state) == (
        "prohibited_runtime_activity_detected"
    )


def test_loader_failure_creates_no_completed_artifact(tmp_path: Path) -> None:
    output = tmp_path / "materialized"

    def fail_loader() -> tuple[Any, ...]:
        raise RuntimeError("synthetic loader failure")

    with pytest.raises(RuntimeError, match="synthetic loader failure"):
        _run_synthetic(tmp_path, output=output, analytical_day_loader=fail_loader)
    assert not output.exists()


def test_loaded_day_calendar_mismatch_fails_closed(tmp_path: Path) -> None:
    assert _reason(
        _run_synthetic,
        tmp_path,
        analytical_day_loader=lambda: _loaded_days()[:-1],
    ) == "loaded_day_calendar_mismatch"


def test_exact_candidate_count_and_order(tmp_path: Path) -> None:
    expected = [
        (key.target.target_id, key.window_seconds, key.block)
        for key in dm.frozen_candidate_keys()
    ]
    assert len(expected) == 4 * 4 * 4 == 64
    payload = _payload(tmp_path)
    actual = [
        (
            item["target"]["target_id"],
            item["window_seconds"],
            item["block"],
        )
        for item in payload["per_candidate"]
    ]
    assert actual == expected


@pytest.mark.parametrize("mutation", ("missing", "extra"))
def test_candidate_grid_identity_fails(tmp_path: Path, mutation: str) -> None:
    grid = _candidate_grid()
    if mutation == "missing":
        del grid[dm.frozen_candidate_keys()[0]]
    else:
        extra = dd.CandidateKey(dd.TargetGeometry("X", 1, 1), 8, dd.FROZEN_BLOCKS[0])
        grid[extra] = {}
    assert _reason(_payload, tmp_path, candidate_days=grid) == "candidate_grid_mismatch"


def test_candidate_key_mutation_fails(tmp_path: Path) -> None:
    grid = _candidate_grid()
    first_key = dm.frozen_candidate_keys()[0]
    first_day = dd.HISTORICAL_DAYS[0]
    wrong_key = dm.frozen_candidate_keys()[1]
    grid[first_key][first_day] = replace(grid[first_key][first_day], key=wrong_key)
    assert _reason(_payload, tmp_path, candidate_days=grid) == "candidate_key_mismatch"


def test_day_order_and_identity_are_exact(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    first = payload["per_candidate"][0]
    assert [item["date"] for item in first["per_day"]] == [
        day.isoformat() for day in dd.HISTORICAL_DAYS
    ]
    grid = _candidate_grid()
    key = dm.frozen_candidate_keys()[0]
    grid[key] = dict(reversed(tuple(grid[key].items())))
    assert _reason(_payload, tmp_path, candidate_days=grid) == (
        "candidate_day_order_mismatch"
    )


def test_fold_identity_and_day_naming_are_exact(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    folds = payload["per_candidate"][0]["folds"]
    assert len(folds) == 4
    assert [item["fold_id"] for item in folds] == [1, 2, 3, 4]
    for expected, actual in zip(dd.OUTER_FOLDS, folds, strict=True):
        assert actual["train_days"] == [day.isoformat() for day in expected.train_days]
        assert actual["validation_day"] == expected.validation_day.isoformat()
        assert "train_months" not in actual
        assert "validation_month" not in actual


def test_non_frozen_fold_fails() -> None:
    grid = _candidate_grid()
    key = dm.frozen_candidate_keys()[0]
    fold = dd.build_fold_supports(grid[key])[0]
    altered = replace(
        fold,
        fold=dd.FrozenOuterFold(99, fold.fold.train_days, fold.fold.validation_day),
    )
    assert _reason(dm._fold_public, altered) == "non_frozen_fold"


@pytest.mark.parametrize(
    "updates",
    [
        {"s0_native_support": 3},
        {"s1_native_support": 3},
        {"common_support_count": 3, "common_support_fraction": 1.5},
        {"s0_native_support": 1},
        {"s1_native_support": 1},
        {
            "common_support_count": 1,
            "common_support_fraction": 0.5,
            "t1_common_support_count": 2,
        },
    ],
)
def test_support_count_reconciliation_fails(updates: dict[str, Any]) -> None:
    dataset = _with_counts(_first_day(), **updates)
    expected = (
        "invalid_fraction_field"
        if updates.get("common_support_fraction") == 1.5
        else "support_count_reconciliation_failed"
    )
    assert _reason(dm._candidate_day_public, dataset) == expected


def test_t1_class_count_reconciliation_fails() -> None:
    dataset = _with_counts(_first_day(), t1_long_common_count=0)
    assert _reason(dm._candidate_day_public, dataset) == (
        "t1_class_count_reconciliation_failed"
    )


@pytest.mark.parametrize(
    "updates",
    [
        {"t1_long_common_count": 2, "t1_short_common_count": 0},
        {"t1_long_common_count": 0, "t1_short_common_count": 2},
    ],
)
def test_t1_directional_subset_reconciliation_fails(
    updates: dict[str, int],
) -> None:
    assert _reason(
        dm._candidate_day_public, _with_counts(_first_day(), **updates)
    ) == "t1_directional_subset_reconciliation_failed"


def test_train_fold_class_count_reconciliation_fails() -> None:
    grid = _candidate_grid()
    key = dm.frozen_candidate_keys()[0]
    fold = dd.build_fold_supports(grid[key])[0]
    altered = replace(fold, train_class_counts={"long": 0, "short": 0})
    assert _reason(dm._fold_public, altered) == (
        "train_fold_class_count_reconciliation_failed"
    )


def test_validation_fold_class_count_reconciliation_fails() -> None:
    grid = _candidate_grid()
    key = dm.frozen_candidate_keys()[0]
    fold = dd.build_fold_supports(grid[key])[0]
    altered = replace(fold, validation_class_counts={"long": 0, "short": 0})
    assert _reason(dm._fold_public, altered) == (
        "validation_fold_class_count_reconciliation_failed"
    )


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ({"invalid_target_count": 1}, "target_count_reconciliation_failed"),
        ({"none_count": 1}, "valid_target_count_reconciliation_failed"),
        (
            {"target_future_boundary_valid_count": 1},
            "target_boundary_count_reconciliation_failed",
        ),
    ],
)
def test_core_target_count_reconciliation_fails(
    updates: dict[str, int], expected: str
) -> None:
    assert _reason(
        dm._candidate_day_public, _with_counts(_first_day(), **updates)
    ) == expected


def test_counts_require_builtin_nonnegative_ints() -> None:
    assert _reason(
        dm._candidate_day_public,
        _with_counts(_first_day(), decision_count=np.int64(2)),
    ) == "invalid_count_field"
    assert _reason(
        dm._candidate_day_public,
        _with_counts(_first_day(), decision_count=-1),
    ) == "invalid_count_field"


def test_common_support_fraction_reconciles() -> None:
    assert dm._candidate_day_public(_first_day())["common_support_fraction"] == 1.0
    incorrect = _with_counts(
        _first_day(),
        decision_count=3,
        valid_target_count=3,
        long_first_count=2,
        common_support_count=2,
        common_support_fraction=0.5,
        target_future_boundary_valid_count=3,
        s0_native_support=3,
        s1_native_support=3,
    )
    assert _reason(dm._candidate_day_public, incorrect) == (
        "common_support_fraction_reconciliation_failed"
    )


@pytest.mark.parametrize(
    "dataset",
    [
        _with_counts(_first_day(), decision_count=0, common_support_fraction=0.0),
        _with_counts(_first_day(), common_support_fraction=None),
    ],
)
def test_common_support_fraction_none_contract(dataset: dd.CandidateDayDataset) -> None:
    assert _reason(dm._candidate_day_public, dataset) == (
        "common_support_fraction_reconciliation_failed"
    )


@pytest.mark.parametrize("value", (float("nan"), float("inf"), float("-inf")))
def test_nonfinite_common_support_fraction_fails(value: float) -> None:
    assert _reason(
        dm._candidate_day_public,
        _with_counts(_first_day(), common_support_fraction=value),
    ) == "invalid_fraction_field"


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        (
            "invalid_target_reasons",
            {"synthetic": 1},
            "invalid_target_reason_count_reconciliation_failed",
        ),
        (
            "target_future_boundary_exclusion_reasons",
            {"synthetic": 1},
            "target_boundary_reason_count_reconciliation_failed",
        ),
        (
            "s0_invalid_reasons",
            {"synthetic": 1},
            "s0_invalid_reason_count_reconciliation_failed",
        ),
        (
            "s1_invalid_reasons",
            {"synthetic": 1},
            "s1_invalid_reason_count_reconciliation_failed",
        ),
    ],
)
def test_reason_count_reconciliation_fails(
    field: str, value: dict[str, int], expected: str
) -> None:
    assert _reason(
        dm._candidate_day_public, _with_counts(_first_day(), **{field: value})
    ) == expected


def test_s0_boundary_reason_reconciliation_fails() -> None:
    dataset = _with_counts(
        _first_day(),
        s0_native_support=1,
        common_support_count=1,
        t1_common_support_count=1,
        t1_short_common_count=0,
        common_support_fraction=0.5,
        s0_invalid_reasons={"other": 1},
        s0_boundary_exclusion_reasons={"boundary": 1},
    )
    assert _reason(dm._candidate_day_public, dataset) == (
        "s0_boundary_reason_reconciliation_failed"
    )


def test_s1_boundary_reason_reconciliation_fails() -> None:
    dataset = _with_counts(
        _first_day(),
        s1_native_support=1,
        common_support_count=1,
        t1_common_support_count=1,
        t1_short_common_count=0,
        common_support_fraction=0.5,
        s1_invalid_reasons={"other": 1},
        s1_boundary_exclusion_reasons={"boundary": 1},
    )
    assert _reason(dm._candidate_day_public, dataset) == (
        "s1_boundary_reason_reconciliation_failed"
    )


def test_valid_reason_dictionaries_are_preserved_exactly() -> None:
    dataset = _with_counts(
        _first_day(),
        valid_target_count=1,
        invalid_target_count=1,
        short_first_count=0,
        t1_common_support_count=1,
        t1_short_common_count=0,
        invalid_target_reasons={"z_reason": 1},
    )
    public = dm._candidate_day_public(dataset)
    assert public["invalid_target_reasons"] == {"z_reason": 1}


def test_day_and_fold_support_hashes_are_preserved(tmp_path: Path) -> None:
    grid = _candidate_grid()
    key = dm.frozen_candidate_keys()[0]
    payload = _payload(tmp_path, candidate_days=grid)
    public = payload["per_candidate"][0]
    assert public["per_day"][0]["support_sha256"] == grid[key][
        dd.HISTORICAL_DAYS[0]
    ].support_hashes
    expected_fold = dd.build_fold_supports(grid[key])[0]
    assert public["folds"][0]["support_sha256"] == expected_fold.support_hashes


def test_manifest_and_dependency_hash_provenance(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    payload = _payload(tmp_path, input_manifest=manifest)
    assert [entry["date"] for entry in payload["authorized_input_manifest"]] == [
        day.isoformat() for day in dd.HISTORICAL_DAYS
    ]
    assert payload["frozen_first_passage_source_sha256"] == (
        dd.FIRST_PASSAGE_SOURCE_SHA256
    )
    assert payload["frozen_sequence_feature_source_sha256"] == (
        dd.SEQUENCE_FEATURE_SOURCE_SHA256
    )
    assert _reason(_payload, tmp_path, input_manifest=tuple(reversed(manifest))) == (
        "input_manifest_order_mismatch"
    )


def test_invalid_sha_field_fails(tmp_path: Path) -> None:
    manifest = list(_manifest(tmp_path))
    manifest[0] = replace(manifest[0], sha256="not-a-sha")
    assert _reason(_payload, tmp_path, input_manifest=tuple(manifest)) == (
        "invalid_sha256_field"
    )


def test_canonical_serialization_is_byte_identical_and_sorted(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    first = dm.canonical_json_bytes(payload)
    second = dm.canonical_json_bytes(payload)
    assert first == second
    assert first == dm.canonical_json_bytes(dict(reversed(tuple(payload.items()))))
    decoded = json.loads(first)
    assert decoded["experiment_id"] == dm.EXPERIMENT_ID


def test_numpy_normalization_is_json_safe() -> None:
    normalized = dm.normalize_json_safe(
        {"scalar": np.int64(3), "array": np.asarray([1.5, 2.5])}
    )
    assert normalized == {"scalar": 3, "array": [1.5, 2.5]}
    json.dumps(normalized, allow_nan=False)


@pytest.mark.parametrize("value", (float("nan"), float("inf"), float("-inf")))
def test_nonfinite_json_values_are_rejected(value: float) -> None:
    assert _reason(dm.canonical_json_bytes, {"value": value}) == (
        "non_finite_json_value"
    )


def test_unsupported_json_values_and_mapping_keys_are_rejected() -> None:
    assert _reason(dm.canonical_json_bytes, {"value": object()}) == (
        "unsupported_json_value"
    )
    assert _reason(dm.canonical_json_bytes, {1: "value"}) == (
        "json_mapping_key_not_string"
    )


def test_scientific_content_change_changes_artifact_sha(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    original = hashlib.sha256(dm.canonical_json_bytes(payload)).hexdigest()
    changed = dict(payload)
    changed["created_by_commit"] = "b" * 40
    assert hashlib.sha256(dm.canonical_json_bytes(changed)).hexdigest() != original


def test_artifact_has_no_model_metric_or_economic_schema(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    scientific_sections = {
        "configuration": payload["configuration"],
        "per_candidate": payload["per_candidate"],
    }
    text = json.dumps(scientific_sections, sort_keys=True).lower()
    for forbidden in (
        "estimator",
        "hyperparameter",
        "balanced_accuracy",
        "macro_f1",
        "matthews",
        "profit",
        "pnl",
        "capital",
        "leverage",
    ):
        assert forbidden not in text


@pytest.mark.parametrize(
    "dependency_name",
    (
        "manifest_verifier",
        "analytical_day_loader",
        "candidate_builder",
        "payload_builder",
        "builder_hash_file",
    ),
)
def test_canonical_dependency_overrides_fail_before_any_call(
    monkeypatch: pytest.MonkeyPatch,
    dependency_name: str,
) -> None:
    calls = {"manifest": 0, "loader": 0, "preflight": 0}

    def production_manifest() -> tuple[Any, ...]:
        calls["manifest"] += 1
        return ()

    def production_loader() -> tuple[Any, ...]:
        calls["loader"] += 1
        return ()

    monkeypatch.setattr(dm.dd, "verify_input_manifest", production_manifest)
    monkeypatch.setattr(dm.dd, "load_authorized_days", production_loader)
    monkeypatch.setattr(
        dm,
        "_assert_output_absent",
        lambda unused: calls.__setitem__("preflight", calls["preflight"] + 1),
    )
    kwargs: dict[str, Any] = {
        "workspace": Path("synthetic-workspace"),
        "output_directory": dm.REAL_OUTPUT_DIRECTORY,
        "created_by_commit": COMMIT,
        "manifest_verifier": production_manifest,
        "analytical_day_loader": production_loader,
    }
    overrides: dict[str, Any] = {
        "manifest_verifier": lambda: (),
        "analytical_day_loader": lambda: (),
        "candidate_builder": lambda unused: {},
        "payload_builder": lambda **unused: {},
        "builder_hash_file": lambda unused: dm.FROZEN_BUILDER_SOURCE_SHA256,
    }
    kwargs[dependency_name] = overrides[dependency_name]
    assert _reason(dm.run_materialization, **kwargs) == (
        "canonical_dependency_override_forbidden"
    )
    assert calls == {"manifest": 0, "loader": 0, "preflight": 0}


def test_canonical_output_cannot_enter_test_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"manifest": 0, "loader": 0, "preflight": 0}

    def manifest() -> tuple[Any, ...]:
        calls["manifest"] += 1
        return ()

    def loader() -> tuple[Any, ...]:
        calls["loader"] += 1
        return ()

    monkeypatch.setattr(
        dm,
        "_assert_output_absent",
        lambda unused: calls.__setitem__("preflight", calls["preflight"] + 1),
    )
    assert _reason(
        dm.run_materialization,
        workspace=Path("synthetic-workspace"),
        output_directory=dm.REAL_OUTPUT_DIRECTORY,
        created_by_commit=COMMIT,
        manifest_verifier=manifest,
        analytical_day_loader=loader,
        candidate_builder=lambda unused: {},
        payload_builder=lambda **unused: {},
        builder_hash_file=lambda unused: dm.FROZEN_BUILDER_SOURCE_SHA256,
        require_canonical_output=False,
    ) == "canonical_output_requires_real_mode"
    assert calls == {"manifest": 0, "loader": 0, "preflight": 0}


def test_noncanonical_injected_orchestration_succeeds(tmp_path: Path) -> None:
    result = _run_synthetic(tmp_path)
    assert result.output_directory == tmp_path / "materialized"
    assert result.artifact_path.is_file()
    assert result.artifact_sha256 == hashlib.sha256(
        result.artifact_path.read_bytes()
    ).hexdigest()


def test_existing_output_fails_before_manifest_and_loader(tmp_path: Path) -> None:
    output = tmp_path / "materialized"
    output.mkdir()
    marker = output / "preserve.txt"
    marker.write_text("preserve", encoding="utf-8")
    calls = {"manifest": 0, "loader": 0}

    def manifest() -> tuple[Any, ...]:
        calls["manifest"] += 1
        return ()

    def loader() -> tuple[Any, ...]:
        calls["loader"] += 1
        return ()

    assert _reason(
        _run_synthetic,
        tmp_path,
        output=output,
        manifest_verifier=manifest,
        analytical_day_loader=loader,
    ) == "output_directory_already_exists"
    assert calls == {"manifest": 0, "loader": 0}
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_missing_output_parent_uses_tmp_path(tmp_path: Path) -> None:
    output = tmp_path / "missing" / "nested" / "materialized"
    assert _reason(dm._assert_output_parent_writable, output) == "output_parent_missing"


def test_successful_output_probe_leaves_no_probe(tmp_path: Path) -> None:
    output = tmp_path / "materialized"
    probe = dm._probe_path(output)
    dm._assert_output_parent_writable(output)
    assert not probe.exists()
    assert not output.exists()


def test_probe_failure_attempts_successful_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "materialized"
    probe = dm._probe_path(output)
    calls = {"fsync": 0}

    def fail_first_fsync(unused: Path) -> None:
        calls["fsync"] += 1
        if calls["fsync"] == 1:
            raise OSError("synthetic fsync failure")

    monkeypatch.setattr(dm, "_fsync_directory", fail_first_fsync)
    assert _reason(dm._assert_output_parent_writable, output) == (
        "output_parent_preflight_failed"
    )
    assert not probe.exists()
    assert calls["fsync"] >= 2


def test_probe_cleanup_failure_has_stable_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "materialized"
    probe = dm._probe_path(output)
    original_unlink = Path.unlink

    def fail_probe_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        if path == probe:
            raise OSError("synthetic unlink failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_probe_unlink)
    assert _reason(dm._assert_output_parent_writable, output) == (
        "output_probe_cleanup_failed"
    )


def test_generic_preflight_failure_precedes_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"manifest": 0, "loader": 0}
    monkeypatch.setattr(
        dm,
        "_assert_output_parent_writable",
        lambda unused: (_ for _ in ()).throw(
            dm.DirectionMaterializationError("synthetic_preflight_failure")
        ),
    )

    def manifest() -> tuple[Any, ...]:
        calls["manifest"] += 1
        return ()

    def loader() -> tuple[Any, ...]:
        calls["loader"] += 1
        return ()

    assert _reason(
        _run_synthetic,
        tmp_path,
        manifest_verifier=manifest,
        analytical_day_loader=loader,
    ) == "synthetic_preflight_failure"
    assert calls == {"manifest": 0, "loader": 0}


def test_existing_final_and_partial_artifacts_are_refused(tmp_path: Path) -> None:
    final = tmp_path / "artifact.json"
    final.write_bytes(b"existing")
    assert _reason(dm._atomic_write_file, final, b"new") == "artifact_already_exists"
    final.unlink()
    part = final.with_name(final.name + ".part")
    part.write_bytes(b"stale")
    assert _reason(dm._atomic_write_file, final, b"new") == (
        "partial_artifact_already_exists"
    )
    assert not final.exists()
    assert part.read_bytes() == b"stale"


def test_successful_atomic_write_and_exact_sha(tmp_path: Path) -> None:
    final = tmp_path / "artifact.json"
    content = b'{"synthetic":true}\n'
    digest = dm._atomic_write_file(final, content)
    assert final.read_bytes() == content
    assert not final.with_name(final.name + ".part").exists()
    assert digest == hashlib.sha256(content).hexdigest()


def test_repeated_materialization_write_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "materialized"
    payload = {"synthetic": True}
    dm.write_materialization_once(output, payload)
    assert _reason(dm.write_materialization_once, output, payload) == (
        "output_directory_already_exists"
    )


def test_serialization_failure_creates_no_output_directory(tmp_path: Path) -> None:
    output = tmp_path / "materialized"
    assert _reason(
        dm.write_materialization_once, output, {"bad": float("nan")}
    ) == "non_finite_json_value"
    assert not output.exists()


def test_pre_replace_failure_cleans_partial_and_output_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "materialized"
    monkeypatch.setattr(
        dm.os,
        "replace",
        lambda source, target: (_ for _ in ()).throw(
            OSError("synthetic replace failure")
        ),
    )
    assert _reason(dm.write_materialization_once, output, {"ok": True}) == (
        "artifact_write_failed"
    )
    assert not output.exists()
    assert not (output / (dm.ARTIFACT_FILENAME + ".part")).exists()


def test_failed_write_removes_invocation_created_empty_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "materialized"
    monkeypatch.setattr(
        dm,
        "_atomic_write_file",
        lambda path, content: (_ for _ in ()).throw(
            dm.DirectionMaterializationError("synthetic_write_failure")
        ),
    )
    assert _reason(dm.write_materialization_once, output, {"ok": True}) == (
        "synthetic_write_failure"
    )
    assert not output.exists()


def test_output_directory_cleanup_failure_has_stable_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "materialized"
    monkeypatch.setattr(
        dm,
        "_atomic_write_file",
        lambda path, content: (_ for _ in ()).throw(OSError("write failed")),
    )
    original_rmdir = Path.rmdir

    def fail_output_rmdir(path: Path) -> None:
        if path == output:
            raise OSError("synthetic rmdir failure")
        original_rmdir(path)

    monkeypatch.setattr(Path, "rmdir", fail_output_rmdir)
    assert _reason(dm.write_materialization_once, output, {"ok": True}) == (
        "output_directory_cleanup_failed"
    )


def test_partial_cleanup_failure_has_stable_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    final = tmp_path / "artifact.json"
    part = final.with_name(final.name + ".part")
    monkeypatch.setattr(
        dm.os,
        "replace",
        lambda source, target: (_ for _ in ()).throw(OSError("replace failed")),
    )
    original_unlink = Path.unlink

    def fail_part_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        if path == part:
            raise OSError("part cleanup failed")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_part_unlink)
    assert _reason(dm._atomic_write_file, final, b"content") == (
        "artifact_partial_cleanup_failed"
    )
    assert not final.exists()


def test_preexisting_output_directory_is_never_deleted(tmp_path: Path) -> None:
    output = tmp_path / "materialized"
    output.mkdir()
    marker = output / "marker"
    marker.write_bytes(b"preserve")
    assert _reason(dm.write_materialization_once, output, {"ok": True}) == (
        "output_directory_already_exists"
    )
    assert marker.read_bytes() == b"preserve"


def test_post_replace_directory_fsync_failure_preserves_final(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    final = tmp_path / "artifact.json"
    monkeypatch.setattr(
        dm,
        "_fsync_directory",
        lambda unused: (_ for _ in ()).throw(OSError("directory fsync failed")),
    )
    assert _reason(dm._atomic_write_file, final, b"committed") == (
        "artifact_directory_fsync_failed"
    )
    assert final.read_bytes() == b"committed"
    assert not final.with_name(final.name + ".part").exists()

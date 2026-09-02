"""DEV030-P9 dense causal PRICE sequence diagnostic.

Frozen scientific question:
Does a dense causal path from the same three PRICE primitives add stable
T1 LONG_FIRST-vs-SHORT_FIRST information beyond the frozen 32-second PRICE S1
whole-window summaries?

P9 changes representation only. It keeps target A / 120s / 16bp / 32s,
matched P3 PRICE T1 support, train-only scaling, and L2 logistic regression.

The real Jan-Jul run remains separately gated. Synthetic tests must not open
real market files.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

from . import dev030_direction_dataset as dd
from . import dev030_p3_direction as p3
from . import dev030_p4_touch_composition as p4
from . import dev030_sequence_features as sf


EXPERIMENT_ID = "DEV030-P9"
DESIGN_VERSION = "price-dense-sequence-linear-v1"

SELECTED_TARGET = next(item for item in dd.FROZEN_TARGETS if item.target_id == "A")
SELECTED_WINDOW_SECONDS = 32
SELECTED_BLOCK = sf.PRICE
SELECTED_KEY = dd.CandidateKey(
    SELECTED_TARGET,
    SELECTED_WINDOW_SECONDS,
    SELECTED_BLOCK,
)

SHORT_FIRST = 0
LONG_FIRST = 1
THRESHOLD = 0.5
RANDOM_STATE = 20260825
C_GRID = (0.01, 0.1, 1.0, 10.0)

LAG_SECONDS = tuple(range(32, 0, -1))
SEQUENCE_SAMPLE_INTERVAL_SECONDS = 1
PRICE_LAG_PRIMITIVES = (
    "spread_bps",
    "microprice_minus_mid_bps",
    sf.DERIVED_MID_RETURN,
)

BASELINE_FEATURE_NAMES = dd.sequence_summary_feature_names(SELECTED_BLOCK)
DENSE_SEQUENCE_FEATURE_NAMES = tuple(
    f"{feature}__lag_{lag}s"
    for feature in PRICE_LAG_PRIMITIVES
    for lag in LAG_SECONDS
)
AUGMENTED_FEATURE_NAMES = (
    BASELINE_FEATURE_NAMES + DENSE_SEQUENCE_FEATURE_NAMES
)

EXPECTED_BASELINE_FEATURE_COUNT = 23
EXPECTED_DENSE_SEQUENCE_FEATURE_COUNT = 96
EXPECTED_AUGMENTED_FEATURE_COUNT = 119

EXPECTED_POOLED_SUPPORT = 573
EXPECTED_POOLED_LONG = 309
EXPECTED_POOLED_SHORT = 264
EXPECTED_FOLD_SUPPORT = (159, 64, 126, 224)
EXPECTED_FOLD_LONG = (86, 40, 60, 123)
EXPECTED_FOLD_SHORT = (73, 24, 66, 101)

P2C_ARTIFACT_PATH = p3.P2C_ARTIFACT_PATH
P2C_ARTIFACT_SHA256 = p3.P2C_ARTIFACT_SHA256

P3_ARTIFACT_PATH = p4.P3_ARTIFACT_PATH
P3_ARTIFACT_SHA256 = p4.P3_ARTIFACT_SHA256
P4_ARTIFACT_PATH = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p4_t2_composition_v1/"
    "DEV030_P4_T2_COMPOSITION_RESULT.json"
)
P4_ARTIFACT_SHA256 = (
    "8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16"
)
P5_ARTIFACT_PATH = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p5_joint_threeclass_v1/"
    "DEV030_P5_JOINT_THREECLASS_RESULT.json"
)
P5_ARTIFACT_SHA256 = (
    "d9a89a1be1dc3733cd510666f9a2d717e853a8c414c2c3c943d28ebafa741c00"
)
P6_ARTIFACT_PATH = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p6_m2_direction_v1/"
    "DEV030_P6_M2_DIRECTION_RESULT.json"
)
P6_ARTIFACT_SHA256 = (
    "b7ccd3f81e7c1dac869e4b4059c11af6efa30b90761ef821e5e325f962f58c0a"
)
P7_ARTIFACT_PATH = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p7_ofi_incremental_v1/"
    "DEV030_P7_OFI_INCREMENTAL_RESULT.json"
)
P7_ARTIFACT_SHA256 = (
    "07d3f7f09dc19d771ad2d6ed9323ae3100d0054d6eb8ff37dee1453258efd85c"
)

P3_SOURCE_REL = "src/multimarket/dev030_p3_direction.py"
P3_TEST_REL = "tests/test_dev030_p3_direction.py"
P3_SOURCE_SHA256 = p4.P3_SOURCE_SHA256
P3_TEST_SHA256 = p4.P3_TEST_SHA256
P4_SOURCE_REL = "src/multimarket/dev030_p4_touch_composition.py"
P4_TEST_REL = "tests/test_dev030_p4_touch_composition.py"
P4_SOURCE_SHA256 = (
    "bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f"
)
P4_TEST_SHA256 = (
    "7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265"
)

REAL_OUTPUT_DIRECTORY = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p9_price_dense_sequence_v1"
)
ARTIFACT_FILENAME = "DEV030_P9_PRICE_DENSE_SEQUENCE_RESULT.json"

PREDICTION_HASH_DOMAIN = b"DEV030-P9-OOF-PREDICTION-V1\x00"
LABEL_HASH_DOMAIN = b"DEV030-P9-LABELS-V1\x00"

FORWARD_GUARDS = {
    "aug30_analytically_opened": False,
    "sep01_or_later_analytically_opened": False,
    "archive_bucket_opened": False,
    "abundant_love_opened": False,
}


class P9Error(RuntimeError):
    """Frozen P9 protocol, provenance, model, or output violation."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


@dataclass(frozen=True)
class DenseDay:
    day: date
    timestamps_us: np.ndarray
    labels: np.ndarray
    c0_values: np.ndarray
    c1_values: np.ndarray
    c0_feature_names: tuple[str, ...]
    c1_feature_names: tuple[str, ...]
    support_sha256: str
    label_sha256: str


@dataclass(frozen=True)
class FoldResult:
    fold_id: int
    representation: str
    selected_c: float
    support: int
    long_count: int
    short_count: int
    metrics: dict[str, Any]
    timestamps_us: np.ndarray
    y_true: np.ndarray
    p_long: np.ndarray
    y_pred: np.ndarray
    prediction_sha256: str
    support_sha256: str
    label_sha256: str
    inner_c_ledger: tuple[dict[str, Any], ...]
    scaler: Any
    model: Any


@dataclass(frozen=True)
class RepresentationResult:
    representation: str
    folds: tuple[FoldResult, ...]
    pooled_metrics: dict[str, Any]
    pooled_support_sha256: str
    pooled_label_sha256: str


@dataclass(frozen=True)
class PairedTemporalNull:
    eligible_shifts: tuple[int, ...]
    null_log_loss_improvement: tuple[float, ...]
    null_auc_delta: tuple[float, ...]
    log_loss_improvement_q95: float
    auc_delta_q95: float
    empirical_p: float
    observed_log_loss_improvement: float
    observed_auc_delta: float
    pass_gate: bool


@dataclass(frozen=True)
class ArtifactWriteResult:
    output_directory: Path
    artifact_path: Path
    artifact_sha256: str
    artifact_bytes: int


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_execution_commit(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise P9Error("execution_commit_must_be_full_sha")
    return value


def load_verified_json_artifact(
    path: Path,
    expected_sha256: str,
    *,
    hash_file: Any = _sha256_file,
) -> dict[str, Any]:
    artifact = Path(path)
    if not artifact.is_file():
        raise P9Error("frozen_artifact_missing", str(artifact))
    actual = str(hash_file(artifact))
    if actual != expected_sha256:
        raise P9Error("frozen_artifact_sha256_mismatch", str(artifact))
    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise P9Error("frozen_artifact_read_failed", str(exc)) from exc
    if not isinstance(payload, dict):
        raise P9Error("frozen_artifact_not_object")
    return payload


def verify_frozen_dependencies(
    repository_root: Path,
    *,
    hash_file: Any = _sha256_file,
) -> dict[str, str]:
    root = Path(repository_root).resolve()
    expected = (
        (
            dd.FIRST_PASSAGE_SOURCE_REL,
            dd.FIRST_PASSAGE_SOURCE_SHA256,
            "first_passage_source_sha256_mismatch",
        ),
        (
            dd.SEQUENCE_FEATURE_SOURCE_REL,
            dd.SEQUENCE_FEATURE_SOURCE_SHA256,
            "sequence_source_sha256_mismatch",
        ),
        (
            p3.P2B_SOURCE_REL,
            p3.P2B_SOURCE_SHA256,
            "p2b_source_sha256_mismatch",
        ),
        (P3_SOURCE_REL, P3_SOURCE_SHA256, "p3_source_sha256_mismatch"),
        (P3_TEST_REL, P3_TEST_SHA256, "p3_test_sha256_mismatch"),
        (P4_SOURCE_REL, P4_SOURCE_SHA256, "p4_source_sha256_mismatch"),
        (P4_TEST_REL, P4_TEST_SHA256, "p4_test_sha256_mismatch"),
    )
    result: dict[str, str] = {}
    for rel, expected_sha, reason in expected:
        file_path = root / rel
        if not file_path.is_file():
            raise P9Error("frozen_dependency_missing", rel)
        actual = str(hash_file(file_path))
        if actual != expected_sha:
            raise P9Error(reason, rel)
        result[rel] = actual
    return result


def validate_prior_artifacts(
    p3_payload: Mapping[str, Any],
    p4_payload: Mapping[str, Any],
    p5_payload: Mapping[str, Any],
    p6_payload: Mapping[str, Any],
    p7_payload: Mapping[str, Any],
) -> None:
    try:
        p4.validate_p3_selected_survivor(p3_payload)
    except p4.P4Error as exc:
        raise P9Error(exc.reason, str(exc)) from exc
    expected = (
        (
            p4_payload.get("status"),
            "FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE",
            "p4_terminal_status_mismatch",
        ),
        (
            p5_payload.get("status"),
            "FAIL_DIRECT_JOINT_THREECLASS_NO_INCREMENTAL_VALUE",
            "p5_terminal_status_mismatch",
        ),
        (
            p6_payload.get("status"),
            "FAIL_M2_DIRECTION_NO_STABLE_INCREMENTAL_VALUE",
            "p6_terminal_status_mismatch",
        ),
        (
            p7_payload.get("status"),
            "FAIL_L1_OFI_NO_STABLE_INCREMENTAL_VALUE",
            "p7_terminal_status_mismatch",
        ),
    )
    for actual, wanted, reason in expected:
        if actual != wanted:
            raise P9Error(reason)
    if p6_payload.get("eligible_for_direction_capacity_upgrade") is not False:
        raise P9Error("p6_capacity_upgrade_state_mismatch")
    if p7_payload.get("eligible_l1_ofi_incremental_information") is not False:
        raise P9Error("p7_incremental_information_state_mismatch")


def validate_feature_contract() -> None:
    if len(BASELINE_FEATURE_NAMES) != EXPECTED_BASELINE_FEATURE_COUNT:
        raise P9Error("baseline_feature_count_mismatch")
    expected_shape = tuple(
        f"{feature}__lag_{lag}s"
        for feature in PRICE_LAG_PRIMITIVES
        for lag in LAG_SECONDS
    )
    if DENSE_SEQUENCE_FEATURE_NAMES != expected_shape:
        raise P9Error("dense_sequence_feature_order_mismatch")
    if len(DENSE_SEQUENCE_FEATURE_NAMES) != EXPECTED_DENSE_SEQUENCE_FEATURE_COUNT:
        raise P9Error("dense_sequence_feature_count_mismatch")
    if len(AUGMENTED_FEATURE_NAMES) != EXPECTED_AUGMENTED_FEATURE_COUNT:
        raise P9Error("augmented_feature_count_mismatch")
    if len(set(AUGMENTED_FEATURE_NAMES)) != len(AUGMENTED_FEATURE_NAMES):
        raise P9Error("augmented_feature_duplicate")
    if any("__lag_0s" in name for name in DENSE_SEQUENCE_FEATURE_NAMES):
        raise P9Error("current_value_must_not_be_duplicated")


def validate_candidate(dataset: dd.CandidateDayDataset) -> None:
    validate_feature_contract()
    if dataset.key != SELECTED_KEY:
        raise P9Error("candidate_identity_mismatch")
    if tuple(dataset.s1_feature_names) != BASELINE_FEATURE_NAMES:
        raise P9Error("baseline_feature_order_mismatch")
    n = len(dataset.decision_timestamps_us)
    if not (
        len(dataset.t1_labels) == n
        and len(dataset.t1_common_valid) == n
        and len(dataset.s1_values) == n
    ):
        raise P9Error("candidate_array_length_mismatch")


def label_sha256(timestamps_us: Any, labels: Any) -> str:
    ts = np.asarray(timestamps_us, dtype=np.int64)
    y = np.asarray(labels, dtype=np.int8)
    if ts.ndim != 1 or y.ndim != 1 or len(ts) != len(y):
        raise P9Error("label_hash_shape_mismatch")
    if not bool(np.all(np.isin(y, (SHORT_FIRST, LONG_FIRST)))):
        raise P9Error("label_hash_invalid_labels")
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P9Error("label_hash_timestamps_not_chronological")
    digest = hashlib.sha256()
    digest.update(LABEL_HASH_DOMAIN)
    digest.update(struct.pack(">Q", len(ts)))
    for timestamp, label in zip(ts.tolist(), y.tolist(), strict=True):
        digest.update(struct.pack(">qb", int(timestamp), int(label)))
    return digest.hexdigest()


def _exact_positions(
    raw_timestamps_us: np.ndarray,
    requested_timestamps_us: np.ndarray,
) -> np.ndarray:
    positions = np.searchsorted(
        raw_timestamps_us, requested_timestamps_us, side="left"
    ).astype(np.int64, copy=False)
    if bool(np.any(positions >= len(raw_timestamps_us))):
        raise P9Error("lag_timestamp_missing")
    if not bool(
        np.array_equal(raw_timestamps_us[positions], requested_timestamps_us)
    ):
        raise P9Error("lag_timestamp_missing")
    return positions


def extract_dense_sequence_matrix(
    sequence_input: sf.SequenceFeatureInput,
    decision_timestamps_us: Any,
) -> np.ndarray:
    """Extract exactly 96 causal PRICE sequence values at one-second lags 32s..1s."""

    validate_feature_contract()
    raw_ts = np.asarray(sequence_input.timestamps_us)
    decisions = np.asarray(decision_timestamps_us)
    if raw_ts.ndim != 1 or raw_ts.dtype.kind not in "iu":
        raise P9Error("raw_timestamps_must_be_integer_1d")
    if decisions.ndim != 1 or decisions.dtype.kind not in "iu":
        raise P9Error("decision_timestamps_must_be_integer_1d")
    raw_ts = raw_ts.astype(np.int64, copy=False)
    decisions = decisions.astype(np.int64, copy=False)
    if len(decisions) and bool(np.any(np.diff(decisions) <= 0)):
        raise P9Error("decision_timestamps_not_chronological")
    if len(raw_ts) == 0 or bool(np.any(np.diff(raw_ts) <= 0)):
        raise P9Error("raw_timestamps_not_chronological")
    if bool(np.any(raw_ts % sf.GRID_US != 0)):
        raise P9Error("raw_timestamp_off_grid")

    try:
        spread = np.asarray(
            sequence_input.features["spread_bps"], dtype=np.float64
        )
        micro = np.asarray(
            sequence_input.features["microprice_minus_mid_bps"],
            dtype=np.float64,
        )
        mid = np.asarray(sequence_input.mid, dtype=np.float64)
        book_valid = np.asarray(
            sequence_input.validity_masks["book_valid"], dtype=bool
        )
        l0_valid = np.asarray(
            sequence_input.validity_masks["l0_valid"], dtype=bool
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise P9Error("invalid_price_sequence_input") from exc

    n_raw = len(raw_ts)
    if any(
        array.ndim != 1 or len(array) != n_raw
        for array in (spread, micro, mid, book_valid, l0_valid)
    ):
        raise P9Error("price_sequence_array_shape_mismatch")

    columns: list[np.ndarray] = []
    for primitive in PRICE_LAG_PRIMITIVES:
        for lag in LAG_SECONDS:
            requested = decisions - int(lag) * 1_000_000
            positions = _exact_positions(raw_ts, requested)
            if not bool(
                np.all(book_valid[positions]) and np.all(l0_valid[positions])
            ):
                raise P9Error("lag_snapshot_invalid_required_mask")

            if primitive == "spread_bps":
                values = spread[positions]
            elif primitive == "microprice_minus_mid_bps":
                values = micro[positions]
            elif primitive == sf.DERIVED_MID_RETURN:
                prior_positions = positions - 1
                if bool(np.any(prior_positions < 0)):
                    raise P9Error("lag_prior_mid_missing")
                if not bool(
                    np.array_equal(
                        raw_ts[prior_positions],
                        requested - sf.GRID_US,
                    )
                ):
                    raise P9Error("lag_prior_mid_missing")
                if not bool(
                    np.all(book_valid[prior_positions])
                    and np.all(book_valid[positions])
                ):
                    raise P9Error("lag_prior_mid_invalid_book")
                current_mid = mid[positions]
                prior_mid = mid[prior_positions]
                if not bool(
                    np.all(np.isfinite(current_mid))
                    and np.all(np.isfinite(prior_mid))
                    and np.all(current_mid > 0.0)
                    and np.all(prior_mid > 0.0)
                ):
                    raise P9Error("lag_mid_invalid")
                values = 10_000.0 * np.log(current_mid / prior_mid)
            else:
                raise P9Error("unexpected_price_primitive")

            if not bool(np.all(np.isfinite(values))):
                raise P9Error("lag_feature_non_finite", primitive)
            columns.append(np.asarray(values, dtype=np.float64))

    if not columns:
        raise P9Error("dense_sequence_columns_empty")
    matrix = np.column_stack(columns)
    if matrix.shape != (
        len(decisions),
        EXPECTED_DENSE_SEQUENCE_FEATURE_COUNT,
    ):
        raise P9Error("dense_sequence_matrix_shape_mismatch")
    return matrix


def build_shape_day(
    candidate: dd.CandidateDayDataset,
    sequence_input: sf.SequenceFeatureInput,
) -> DenseDay:
    validate_candidate(candidate)
    mask = np.asarray(candidate.t1_common_valid, dtype=bool)
    ts = np.asarray(candidate.decision_timestamps_us, dtype=np.int64)[mask]
    y = np.asarray(candidate.t1_labels, dtype=np.int8)[mask]
    x0 = np.asarray(candidate.s1_values, dtype=np.float64)[mask]
    if len(ts) == 0:
        raise P9Error("dense_support_empty")
    if x0.shape != (len(ts), EXPECTED_BASELINE_FEATURE_COUNT):
        raise P9Error("baseline_selected_shape_mismatch")
    if not bool(np.all(np.isfinite(x0))):
        raise P9Error("baseline_features_non_finite")
    if not bool(np.all(np.isin(y, (SHORT_FIRST, LONG_FIRST)))):
        raise P9Error("dense_labels_invalid")

    shape = extract_dense_sequence_matrix(sequence_input, ts)
    x1 = np.column_stack((x0, shape))
    if x1.shape != (len(ts), EXPECTED_AUGMENTED_FEATURE_COUNT):
        raise P9Error("augmented_selected_shape_mismatch")

    # P9 is forbidden from shrinking support relative to frozen PRICE S1.
    if len(x1) != int(np.count_nonzero(mask)):
        raise P9Error("dense_sequence_support_shrink")

    return DenseDay(
        day=candidate.day,
        timestamps_us=ts,
        labels=y,
        c0_values=x0,
        c1_values=x1,
        c0_feature_names=BASELINE_FEATURE_NAMES,
        c1_feature_names=AUGMENTED_FEATURE_NAMES,
        support_sha256=dd.support_sha256(ts),
        label_sha256=label_sha256(ts, y),
    )


def reconcile_selected_candidate_with_p2c(
    candidate_per_day: Mapping[date, dd.CandidateDayDataset],
    p2c_payload: Mapping[str, Any],
) -> None:
    try:
        p4.reconcile_selected_candidate_with_p2c(candidate_per_day, p2c_payload)
    except p4.P4Error as exc:
        raise P9Error(exc.reason, str(exc)) from exc


def reproduce_frozen_p3(
    price_per_day: Mapping[date, dd.CandidateDayDataset],
) -> dict[str, Any]:
    try:
        folds = p4.reproduce_frozen_t1(price_per_day)
    except p4.P4Error as exc:
        raise P9Error(exc.reason, str(exc)) from exc
    result = {
        "pass": all(fold.reproduced for fold in folds),
        "folds": [
            {
                "fold_id": fold.fold_id,
                "selected_C": fold.selected_c,
                "expected_prediction_sha256": fold.expected_prediction_sha256,
                "actual_prediction_sha256": fold.actual_prediction_sha256,
                "reproduced": fold.reproduced,
            }
            for fold in folds
        ],
    }
    if result["pass"] is not True:
        raise P9Error("frozen_p3_reproduction_failed")
    return result


def verify_interval_separation(
    candidate_per_day: Mapping[date, dd.CandidateDayDataset],
) -> tuple[dict[str, Any], ...]:
    checks: list[dict[str, Any]] = []
    for fold in dd.OUTER_FOLDS:
        train_day = fold.train_days[-1]
        validation_day = fold.validation_day
        train = candidate_per_day[train_day]
        validation = candidate_per_day[validation_day]
        train_ts = np.asarray(train.decision_timestamps_us, dtype=np.int64)[
            np.asarray(train.t1_common_valid, dtype=bool)
        ]
        val_ts = np.asarray(validation.decision_timestamps_us, dtype=np.int64)[
            np.asarray(validation.t1_common_valid, dtype=bool)
        ]
        if len(train_ts) == 0 or len(val_ts) == 0:
            raise P9Error("interval_check_support_empty")
        train_end = sf.information_intervals(
            decision_timestamp_us=int(train_ts[-1]),
            window_seconds=SELECTED_WINDOW_SECONDS,
            block=SELECTED_BLOCK,
            target_horizon_seconds=SELECTED_TARGET.horizon_seconds,
        ).raw_source_end_us
        val_start = sf.information_intervals(
            decision_timestamp_us=int(val_ts[0]),
            window_seconds=SELECTED_WINDOW_SECONDS,
            block=SELECTED_BLOCK,
            target_horizon_seconds=SELECTED_TARGET.horizon_seconds,
        ).raw_source_start_us
        if train_end >= val_start:
            raise P9Error("training_validation_information_overlap")
        checks.append(
            {
                "fold_id": int(fold.fold_id),
                "latest_training_information_end_us": int(train_end),
                "earliest_validation_information_start_us": int(val_start),
                "strictly_separated": True,
            }
        )
    return tuple(checks)


def _stack_days(
    per_day: Mapping[date, DenseDay],
    days: Sequence[date],
    representation: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if representation not in ("C0", "C1"):
        raise P9Error("invalid_representation")
    chunks = [per_day[day] for day in days]
    x = np.concatenate(
        [
            item.c0_values if representation == "C0" else item.c1_values
            for item in chunks
        ],
        axis=0,
    )
    y = np.concatenate([item.labels for item in chunks]).astype(
        np.int8, copy=False
    )
    ts = np.concatenate([item.timestamps_us for item in chunks]).astype(
        np.int64, copy=False
    )
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P9Error("stacked_timestamps_not_chronological")
    return x, y, ts


def probability_metrics(y_true: Any, p_long: Any) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(p_long, dtype=np.float64)
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p) or len(y) == 0:
        raise P9Error("metric_shape_mismatch")
    if not bool(np.all(np.isin(y, (0, 1)))):
        raise P9Error("metric_labels_invalid")
    if len(np.unique(y)) != 2:
        raise P9Error("metric_requires_both_classes")
    if not bool(np.all(np.isfinite(p))) or not bool(
        np.all((p >= 0.0) & (p <= 1.0))
    ):
        raise P9Error("metric_probabilities_invalid")

    pred = (p >= THRESHOLD).astype(np.int8)
    cm = confusion_matrix(y, pred, labels=[0, 1])
    precision, recall, f1, support = precision_recall_fscore_support(
        y, pred, labels=[0, 1], zero_division=0
    )
    return {
        "support": int(len(y)),
        "long_count": int(np.count_nonzero(y == 1)),
        "short_count": int(np.count_nonzero(y == 0)),
        "binary_log_loss": float(
            log_loss(y, np.column_stack((1.0 - p, p)), labels=[0, 1])
        ),
        "brier": float(brier_score_loss(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "balanced_accuracy_at_0_5": float(
            balanced_accuracy_score(y, pred)
        ),
        "macro_f1_at_0_5": float(
            f1_score(y, pred, average="macro", zero_division=0)
        ),
        "mcc_at_0_5": float(matthews_corrcoef(y, pred)),
        "predicted_long_count_at_0_5": int(np.count_nonzero(pred == 1)),
        "predicted_short_count_at_0_5": int(np.count_nonzero(pred == 0)),
        "short": {
            "precision": float(precision[0]),
            "recall": float(recall[0]),
            "f1": float(f1[0]),
            "support": int(support[0]),
        },
        "long": {
            "precision": float(precision[1]),
            "recall": float(recall[1]),
            "f1": float(f1[1]),
            "support": int(support[1]),
        },
        "confusion_matrix_short_long_at_0_5": cm.astype(int).tolist(),
    }


def _new_logistic(c_value: float) -> LogisticRegression:
    if c_value not in C_GRID:
        raise P9Error("c_not_in_frozen_grid")
    return LogisticRegression(
        C=float(c_value),
        solver="lbfgs",
        l1_ratio=0.0,
        class_weight=None,
        max_iter=1000,
        fit_intercept=True,
        random_state=RANDOM_STATE,
    )


def select_c_probability_first(
    x_fit: Any,
    y_fit: Any,
    x_validation: Any,
    y_validation: Any,
) -> tuple[float, tuple[dict[str, Any], ...]]:
    xf = np.asarray(x_fit, dtype=np.float64)
    xv = np.asarray(x_validation, dtype=np.float64)
    yf = np.asarray(y_fit, dtype=np.int8)
    yv = np.asarray(y_validation, dtype=np.int8)
    if xf.ndim != 2 or xv.ndim != 2 or xf.shape[1] != xv.shape[1]:
        raise P9Error("inner_feature_shape_mismatch")
    if len(xf) != len(yf) or len(xv) != len(yv):
        raise P9Error("inner_length_mismatch")
    if len(np.unique(yf)) != 2 or len(np.unique(yv)) != 2:
        raise P9Error("inner_split_requires_both_classes")
    if not bool(np.all(np.isfinite(xf))) or not bool(np.all(np.isfinite(xv))):
        raise P9Error("non_finite_inner_features")

    ledger: list[dict[str, Any]] = []
    for c_value in C_GRID:
        scaler = StandardScaler()
        xfs = scaler.fit_transform(xf)
        xvs = scaler.transform(xv)
        model = _new_logistic(c_value)
        model.fit(xfs, yf)
        p_long = model.predict_proba(xvs)[:, 1]
        metrics = probability_metrics(yv, p_long)
        ledger.append(
            {
                "C": float(c_value),
                "binary_log_loss": metrics["binary_log_loss"],
                "brier": metrics["brier"],
                "roc_auc": metrics["roc_auc"],
            }
        )

    chosen = sorted(
        ledger,
        key=lambda item: (
            float(item["binary_log_loss"]),
            float(item["brier"]),
            -float(item["roc_auc"]),
            float(item["C"]),
        ),
    )[0]
    return float(chosen["C"]), tuple(ledger)


def prediction_sha256(
    *,
    fold_id: int,
    representation: str,
    timestamps_us: Any,
    y_true: Any,
    p_long: Any,
) -> str:
    if representation not in ("C0", "C1"):
        raise P9Error("prediction_hash_representation_invalid")
    ts = np.asarray(timestamps_us, dtype=np.int64)
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(p_long, dtype=np.float64)
    if not (ts.ndim == y.ndim == p.ndim == 1):
        raise P9Error("prediction_hash_shape_mismatch")
    if not (len(ts) == len(y) == len(p)):
        raise P9Error("prediction_hash_length_mismatch")
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P9Error("prediction_hash_timestamps_not_chronological")
    if not bool(np.all(np.isin(y, (0, 1)))):
        raise P9Error("prediction_hash_labels_invalid")
    if not bool(np.all(np.isfinite(p))) or not bool(
        np.all((p >= 0) & (p <= 1))
    ):
        raise P9Error("prediction_hash_probabilities_invalid")

    digest = hashlib.sha256()
    digest.update(PREDICTION_HASH_DOMAIN)
    digest.update(f"{fold_id}|{representation}".encode("ascii"))
    for timestamp, label, probability in zip(
        ts.tolist(), y.tolist(), p.tolist(), strict=True
    ):
        digest.update(
            struct.pack(">qbd", int(timestamp), int(label), float(probability))
        )
    return digest.hexdigest()


def fit_fold(
    *,
    fold: dd.FrozenOuterFold,
    per_day: Mapping[date, DenseDay],
    representation: str,
) -> FoldResult:
    inner_validation_day = fold.train_days[-1]
    inner_fit_days = fold.train_days[:-1]
    if not inner_fit_days:
        raise P9Error("inner_fit_empty")

    x_if, y_if, _ = _stack_days(per_day, inner_fit_days, representation)
    x_iv, y_iv, _ = _stack_days(
        per_day, (inner_validation_day,), representation
    )
    x_train, y_train, _ = _stack_days(
        per_day, fold.train_days, representation
    )
    x_val, y_val, ts_val = _stack_days(
        per_day, (fold.validation_day,), representation
    )

    selected_c, ledger = select_c_probability_first(
        x_if, y_if, x_iv, y_iv
    )
    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_val_scaled = scaler.transform(x_val)
    model = _new_logistic(selected_c)
    model.fit(x_train_scaled, y_train)
    p_long = model.predict_proba(x_val_scaled)[:, 1]
    pred = (p_long >= THRESHOLD).astype(np.int8)
    metrics = probability_metrics(y_val, p_long)

    return FoldResult(
        fold_id=int(fold.fold_id),
        representation=representation,
        selected_c=float(selected_c),
        support=int(len(y_val)),
        long_count=int(np.count_nonzero(y_val == 1)),
        short_count=int(np.count_nonzero(y_val == 0)),
        metrics=metrics,
        timestamps_us=ts_val,
        y_true=y_val,
        p_long=p_long,
        y_pred=pred,
        prediction_sha256=prediction_sha256(
            fold_id=fold.fold_id,
            representation=representation,
            timestamps_us=ts_val,
            y_true=y_val,
            p_long=p_long,
        ),
        support_sha256=dd.support_sha256(ts_val),
        label_sha256=label_sha256(ts_val, y_val),
        inner_c_ledger=ledger,
        scaler=scaler,
        model=model,
    )


def fit_representation(
    per_day: Mapping[date, DenseDay],
    representation: str,
) -> RepresentationResult:
    if tuple(per_day) != dd.HISTORICAL_DAYS:
        raise P9Error("shape_day_order_mismatch")
    folds = tuple(
        fit_fold(fold=fold, per_day=per_day, representation=representation)
        for fold in dd.OUTER_FOLDS
    )
    y = np.concatenate([fold.y_true for fold in folds])
    p = np.concatenate([fold.p_long for fold in folds])
    ts = np.concatenate([fold.timestamps_us for fold in folds])
    return RepresentationResult(
        representation=representation,
        folds=folds,
        pooled_metrics=probability_metrics(y, p),
        pooled_support_sha256=dd.support_sha256(ts),
        pooled_label_sha256=label_sha256(ts, y),
    )


def validate_matched_support(
    c0: RepresentationResult,
    c1: RepresentationResult,
) -> None:
    if len(c0.folds) != 4 or len(c1.folds) != 4:
        raise P9Error("outer_fold_count_mismatch")
    for left, right in zip(c0.folds, c1.folds, strict=True):
        if left.fold_id != right.fold_id:
            raise P9Error("fold_alignment_mismatch")
        if not np.array_equal(left.timestamps_us, right.timestamps_us):
            raise P9Error("timestamp_alignment_mismatch")
        if not np.array_equal(left.y_true, right.y_true):
            raise P9Error("label_alignment_mismatch")
        if left.support_sha256 != right.support_sha256:
            raise P9Error("support_hash_alignment_mismatch")
        if left.label_sha256 != right.label_sha256:
            raise P9Error("label_hash_alignment_mismatch")
    if (
        c0.pooled_support_sha256 != c1.pooled_support_sha256
        or c0.pooled_label_sha256 != c1.pooled_label_sha256
    ):
        raise P9Error("pooled_support_alignment_mismatch")


def validate_expected_p3_support(result: RepresentationResult) -> None:
    supports = tuple(fold.support for fold in result.folds)
    longs = tuple(fold.long_count for fold in result.folds)
    shorts = tuple(fold.short_count for fold in result.folds)
    if supports != EXPECTED_FOLD_SUPPORT:
        raise P9Error("p3_fold_support_mismatch")
    if longs != EXPECTED_FOLD_LONG or shorts != EXPECTED_FOLD_SHORT:
        raise P9Error("p3_fold_class_count_mismatch")
    metrics = result.pooled_metrics
    if int(metrics["support"]) != EXPECTED_POOLED_SUPPORT:
        raise P9Error("p3_pooled_support_mismatch")
    if (
        int(metrics["long_count"]) != EXPECTED_POOLED_LONG
        or int(metrics["short_count"]) != EXPECTED_POOLED_SHORT
    ):
        raise P9Error("p3_pooled_class_count_mismatch")


def comparison_summary(
    c0: RepresentationResult,
    c1: RepresentationResult,
    *,
    invariants_pass: bool,
) -> dict[str, Any]:
    validate_matched_support(c0, c1)

    pooled_ll = float(
        c0.pooled_metrics["binary_log_loss"]
        - c1.pooled_metrics["binary_log_loss"]
    )
    pooled_brier = float(
        c0.pooled_metrics["brier"] - c1.pooled_metrics["brier"]
    )
    pooled_auc = float(
        c1.pooled_metrics["roc_auc"] - c0.pooled_metrics["roc_auc"]
    )
    fold_ll = tuple(
        float(
            left.metrics["binary_log_loss"]
            - right.metrics["binary_log_loss"]
        )
        for left, right in zip(c0.folds, c1.folds, strict=True)
    )
    fold_auc = tuple(
        float(right.metrics["roc_auc"] - left.metrics["roc_auc"])
        for left, right in zip(c0.folds, c1.folds, strict=True)
    )

    loo_ll: list[float] = []
    loo_auc: list[float] = []
    for omitted in range(4):
        y = np.concatenate(
            [c0.folds[i].y_true for i in range(4) if i != omitted]
        )
        p0 = np.concatenate(
            [c0.folds[i].p_long for i in range(4) if i != omitted]
        )
        p1 = np.concatenate(
            [c1.folds[i].p_long for i in range(4) if i != omitted]
        )
        m0 = probability_metrics(y, p0)
        m1 = probability_metrics(y, p1)
        loo_ll.append(
            float(m0["binary_log_loss"] - m1["binary_log_loss"])
        )
        loo_auc.append(float(m1["roc_auc"] - m0["roc_auc"]))

    noncollapsed = all(
        bool(np.any(fold.p_long > 0.0) and np.any(fold.p_long < 1.0))
        for fold in c1.folds
    )
    gates = {
        "pooled_c1_log_loss_better": pooled_ll > 0.0,
        "pooled_c1_brier_better": pooled_brier > 0.0,
        "pooled_c1_auc_better": pooled_auc > 0.0,
        "pooled_c1_auc_at_least_056": (
            float(c1.pooled_metrics["roc_auc"]) >= 0.56
        ),
        "at_least_3_of_4_fold_log_loss_improve": (
            sum(value > 0 for value in fold_ll) >= 3
        ),
        "at_least_3_of_4_fold_auc_improve": (
            sum(value > 0 for value in fold_auc) >= 3
        ),
        "at_least_3_of_4_fold_c1_auc_gt_050": (
            sum(float(fold.metrics["roc_auc"]) > 0.50 for fold in c1.folds)
            >= 3
        ),
        "leave_one_fold_out_log_loss_improvement_positive": all(
            value > 0 for value in loo_ll
        ),
        "leave_one_fold_out_auc_delta_positive": all(
            value > 0 for value in loo_auc
        ),
        "both_classes_receive_nonzero_probability_each_fold": noncollapsed,
        "exact_p3_support_pass": True,
        "all_invariants_pass": bool(invariants_pass),
    }
    return {
        "pooled_log_loss_improvement": pooled_ll,
        "pooled_brier_improvement": pooled_brier,
        "pooled_auc_delta": pooled_auc,
        "fold_log_loss_improvement": list(fold_ll),
        "fold_auc_delta": list(fold_auc),
        "leave_one_fold_out_log_loss_improvement": loo_ll,
        "leave_one_fold_out_auc_delta": loo_auc,
        "precheck_gates": gates,
        "precheck_pass": all(gates.values()),
    }


def eligible_shared_shifts(group_sizes: Sequence[int]) -> tuple[int, ...]:
    sizes = tuple(int(value) for value in group_sizes)
    if not sizes or any(value <= 0 for value in sizes):
        raise P9Error("invalid_null_group_sizes")
    return tuple(
        k
        for k in range(1, min(sizes))
        if all(min(k, n - k) >= 10 for n in sizes)
    )


def paired_temporal_null(
    c0: RepresentationResult,
    c1: RepresentationResult,
    comparison: Mapping[str, Any],
) -> PairedTemporalNull:
    validate_matched_support(c0, c1)
    shifts = eligible_shared_shifts([len(fold.y_true) for fold in c0.folds])
    if len(shifts) < 20:
        raise P9Error("insufficient_temporal_null_shifts")

    p0 = np.concatenate([fold.p_long for fold in c0.folds])
    p1 = np.concatenate([fold.p_long for fold in c1.folds])
    observed_ll = float(comparison["pooled_log_loss_improvement"])
    observed_auc = float(comparison["pooled_auc_delta"])
    null_ll: list[float] = []
    null_auc: list[float] = []

    for k in shifts:
        shifted = np.concatenate(
            [np.roll(fold.y_true, k) for fold in c0.folds]
        )
        m0 = probability_metrics(shifted, p0)
        m1 = probability_metrics(shifted, p1)
        null_ll.append(
            float(m0["binary_log_loss"] - m1["binary_log_loss"])
        )
        null_auc.append(float(m1["roc_auc"] - m0["roc_auc"]))

    ll_q95 = float(
        np.quantile(np.asarray(null_ll), 0.95, method="higher")
    )
    auc_q95 = float(
        np.quantile(np.asarray(null_auc), 0.95, method="higher")
    )
    empirical_p = float(
        (1 + sum(value >= observed_ll for value in null_ll))
        / (1 + len(null_ll))
    )
    return PairedTemporalNull(
        eligible_shifts=shifts,
        null_log_loss_improvement=tuple(null_ll),
        null_auc_delta=tuple(null_auc),
        log_loss_improvement_q95=ll_q95,
        auc_delta_q95=auc_q95,
        empirical_p=empirical_p,
        observed_log_loss_improvement=observed_ll,
        observed_auc_delta=observed_auc,
        pass_gate=bool(observed_ll > ll_q95 and empirical_p <= 0.05),
    )


def final_gates(
    comparison: Mapping[str, Any],
    null: PairedTemporalNull | None,
) -> dict[str, bool]:
    gates = dict(comparison["precheck_gates"])
    gates["temporal_null_run"] = null is not None
    gates["temporal_null_log_loss_improvement_gt_q95"] = bool(
        null is not None
        and null.observed_log_loss_improvement
        > null.log_loss_improvement_q95
    )
    gates["temporal_null_p_le_005"] = bool(
        null is not None and null.empirical_p <= 0.05
    )
    return gates


def runtime_provenance(
    *,
    model_fit_run: bool,
    p9_run: bool,
) -> dict[str, Any]:
    if type(model_fit_run) is not bool or type(p9_run) is not bool:
        raise P9Error("runtime_flags_must_be_builtin_bool")
    if p9_run and not model_fit_run:
        raise P9Error("p9_requires_model_fit")
    return {
        "jan_jul_analytically_opened": True,
        "authorized_development_data": {
            "scope": "BTCUSDT consumed Jan-Jul development days only",
            "analytically_loaded": True,
        },
        "forward_data_guards": dict(FORWARD_GUARDS),
        "model_fit_run": model_fit_run,
        "p9_run": p9_run,
        "threshold_optimization_run": False,
        "pnl_backtest_run": False,
        "opportunity_gate_run": False,
        "t2_composition_run": False,
        "alternate_model_family_run": False,
        "deep_model_run": False,
        "lag_search_run": False,
        "feature_family_search_run": False,
        "class_weighting_or_resampling_run": False,
        "calibration_run": False,
    }


def validate_runtime_provenance(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "jan_jul_analytically_opened",
        "authorized_development_data",
        "forward_data_guards",
        "model_fit_run",
        "p9_run",
        "threshold_optimization_run",
        "pnl_backtest_run",
        "opportunity_gate_run",
        "t2_composition_run",
        "alternate_model_family_run",
        "deep_model_run",
        "lag_search_run",
        "feature_family_search_run",
        "class_weighting_or_resampling_run",
        "calibration_run",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise P9Error("runtime_provenance_schema_mismatch")
    if value["jan_jul_analytically_opened"] is not True:
        raise P9Error("jan_jul_runtime_state_invalid")
    guards = value["forward_data_guards"]
    if (
        not isinstance(guards, Mapping)
        or set(guards) != set(FORWARD_GUARDS)
        or any(type(item) is not bool for item in guards.values())
        or any(guards.values())
    ):
        raise P9Error("forward_data_guard_violation")
    if value["p9_run"] and not value["model_fit_run"]:
        raise P9Error("p9_requires_model_fit")
    prohibited = (
        "threshold_optimization_run",
        "pnl_backtest_run",
        "opportunity_gate_run",
        "t2_composition_run",
        "alternate_model_family_run",
        "deep_model_run",
        "lag_search_run",
        "feature_family_search_run",
        "class_weighting_or_resampling_run",
        "calibration_run",
    )
    if any(value[name] is not False for name in prohibited):
        raise P9Error("prohibited_runtime_activity")
    return dict(value)


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    def normalize(value: Any) -> Any:
        if value is None or type(value) in (str, bool, int):
            return value
        if type(value) is float:
            if not math.isfinite(value):
                raise P9Error("non_finite_json_value")
            return value
        if isinstance(value, np.generic):
            return normalize(value.item())
        if isinstance(value, np.ndarray):
            return [normalize(item) for item in value.tolist()]
        if isinstance(value, Mapping):
            if not all(isinstance(key, str) for key in value):
                raise P9Error("json_mapping_key_not_string")
            return {
                key: normalize(item) for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, date):
            return value.isoformat()
        raise P9Error("unsupported_json_value", type(value).__name__)

    text = json.dumps(
        normalize(dict(payload)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return (text + "\n").encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _output_preflight(output_directory: Path) -> None:
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise P9Error("output_directory_already_exists")
    parent = output.parent
    if not parent.is_dir():
        raise P9Error("output_parent_missing")
    probe = parent / f".{output.name}.preflight"
    if probe.exists() or probe.is_symlink():
        raise P9Error("output_probe_preexists")
    try:
        with probe.open("xb") as handle:
            handle.write(b"DEV030-P9 preflight\n")
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(parent)
        probe.unlink()
        _fsync_directory(parent)
    except OSError as exc:
        try:
            if probe.exists():
                probe.unlink()
                _fsync_directory(parent)
        except OSError as cleanup_exc:
            raise P9Error(
                "output_probe_cleanup_failed", str(cleanup_exc)
            ) from cleanup_exc
        raise P9Error(
            "output_parent_preflight_failed", str(exc)
        ) from exc


def write_result_once(
    output_directory: Path,
    payload: Mapping[str, Any],
    *,
    require_canonical_output: bool = True,
) -> ArtifactWriteResult:
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise P9Error("output_directory_already_exists")
    if require_canonical_output and output != REAL_OUTPUT_DIRECTORY:
        raise P9Error("noncanonical_output_directory")
    if not require_canonical_output and output == REAL_OUTPUT_DIRECTORY:
        raise P9Error("canonical_output_requires_real_mode")

    content = canonical_json_bytes(payload)
    output.mkdir(mode=0o755)
    _fsync_directory(output.parent)
    final = output / ARTIFACT_FILENAME
    part = final.with_name(final.name + ".part")
    try:
        with part.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(part, final)
        _fsync_directory(output)
    except BaseException as exc:
        if final.exists():
            raise P9Error(
                "artifact_directory_fsync_failed", str(exc)
            ) from exc
        try:
            if part.exists():
                part.unlink()
            if output.exists() and not any(output.iterdir()):
                output.rmdir()
        except OSError as cleanup_exc:
            raise P9Error(
                "artifact_cleanup_failed", str(cleanup_exc)
            ) from cleanup_exc
        if isinstance(exc, P9Error):
            raise
        raise P9Error("artifact_write_failed", str(exc)) from exc

    return ArtifactWriteResult(
        output_directory=output,
        artifact_path=final,
        artifact_sha256=hashlib.sha256(content).hexdigest(),
        artifact_bytes=len(content),
    )


def _fold_public(fold: FoldResult) -> dict[str, Any]:
    return {
        "fold_id": fold.fold_id,
        "representation": fold.representation,
        "selected_C": fold.selected_c,
        "support": fold.support,
        "long_count": fold.long_count,
        "short_count": fold.short_count,
        "metrics": fold.metrics,
        "prediction_sha256": fold.prediction_sha256,
        "support_sha256": fold.support_sha256,
        "label_sha256": fold.label_sha256,
        "inner_c_ledger": [
            dict(item) for item in fold.inner_c_ledger
        ],
    }


def run_p9(
    *,
    workspace: Path,
    output_directory: Path,
    execution_commit: str,
    require_canonical_output: bool = True,
    dependency_verifier: Any = verify_frozen_dependencies,
    p2c_loader: Any = None,
    p3_loader: Any = None,
    p4_loader: Any = None,
    p5_loader: Any = None,
    p6_loader: Any = None,
    p7_loader: Any = None,
    manifest_verifier: Any = dd.verify_input_manifest,
    analytical_day_loader: Any = dd.load_authorized_days,
) -> ArtifactWriteResult:
    """Run the separately-authorized canonical P9 development campaign."""

    supplied = {
        "p2c_loader": p2c_loader,
        "p3_loader": p3_loader,
        "p4_loader": p4_loader,
        "p5_loader": p5_loader,
        "p6_loader": p6_loader,
        "p7_loader": p7_loader,
    }
    if p2c_loader is None:
        p2c_loader = lambda: load_verified_json_artifact(
            P2C_ARTIFACT_PATH, P2C_ARTIFACT_SHA256
        )
    if p3_loader is None:
        p3_loader = lambda: load_verified_json_artifact(
            P3_ARTIFACT_PATH, P3_ARTIFACT_SHA256
        )
    if p4_loader is None:
        p4_loader = lambda: load_verified_json_artifact(
            P4_ARTIFACT_PATH, P4_ARTIFACT_SHA256
        )
    if p5_loader is None:
        p5_loader = lambda: load_verified_json_artifact(
            P5_ARTIFACT_PATH, P5_ARTIFACT_SHA256
        )
    if p6_loader is None:
        p6_loader = lambda: load_verified_json_artifact(
            P6_ARTIFACT_PATH, P6_ARTIFACT_SHA256
        )
    if p7_loader is None:
        p7_loader = lambda: load_verified_json_artifact(
            P7_ARTIFACT_PATH, P7_ARTIFACT_SHA256
        )

    output = Path(output_directory)
    if require_canonical_output:
        if output != REAL_OUTPUT_DIRECTORY:
            raise P9Error("noncanonical_output_directory")
        for name, value in supplied.items():
            if value is not None:
                raise P9Error(
                    "canonical_dependency_override_forbidden", name
                )
        if dependency_verifier is not verify_frozen_dependencies:
            raise P9Error(
                "canonical_dependency_override_forbidden",
                "dependency_verifier",
            )
        if manifest_verifier is not dd.verify_input_manifest:
            raise P9Error(
                "canonical_dependency_override_forbidden",
                "manifest_verifier",
            )
        if analytical_day_loader is not dd.load_authorized_days:
            raise P9Error(
                "canonical_dependency_override_forbidden",
                "analytical_day_loader",
            )
    elif output == REAL_OUTPUT_DIRECTORY:
        raise P9Error("canonical_output_requires_real_mode")

    _output_preflight(output)
    execution_sha = _validate_execution_commit(execution_commit)
    dependency_hashes = dict(dependency_verifier(Path(workspace)))

    p2c_payload = dict(p2c_loader())
    p3_payload = dict(p3_loader())
    p4_payload = dict(p4_loader())
    p5_payload = dict(p5_loader())
    p6_payload = dict(p6_loader())
    p7_payload = dict(p7_loader())
    validate_prior_artifacts(
        p3_payload,
        p4_payload,
        p5_payload,
        p6_payload,
        p7_payload,
    )

    manifest = tuple(manifest_verifier())
    loaded_days = tuple(analytical_day_loader())
    if tuple(day.day for day in loaded_days) != dd.HISTORICAL_DAYS:
        raise P9Error("loaded_day_calendar_mismatch")

    candidate_per_day: dict[date, dd.CandidateDayDataset] = {}
    sequence_input_per_day: dict[date, sf.SequenceFeatureInput] = {}
    for day in loaded_days:
        try:
            sequence_input = dd._validate_day_structure(day)
        except dd.DirectionDatasetError as exc:
            raise P9Error(exc.reason, str(exc)) from exc
        candidate = dd.build_candidate_day(
            day,
            target=SELECTED_TARGET,
            window_seconds=SELECTED_WINDOW_SECONDS,
            block=SELECTED_BLOCK,
        )
        validate_candidate(candidate)
        candidate_per_day[day.day] = candidate
        sequence_input_per_day[day.day] = sequence_input

    if tuple(candidate_per_day) != dd.HISTORICAL_DAYS:
        raise P9Error("candidate_day_order_mismatch")

    reconcile_selected_candidate_with_p2c(
        candidate_per_day, p2c_payload
    )
    p3_reproduction = reproduce_frozen_p3(candidate_per_day)
    interval_checks = verify_interval_separation(candidate_per_day)

    dense_days = {
        day: build_shape_day(
            candidate_per_day[day],
            sequence_input_per_day[day],
        )
        for day in dd.HISTORICAL_DAYS
    }

    c0 = fit_representation(dense_days, "C0")
    c1 = fit_representation(dense_days, "C1")
    validate_matched_support(c0, c1)
    validate_expected_p3_support(c0)
    validate_expected_p3_support(c1)

    comparison = comparison_summary(
        c0,
        c1,
        invariants_pass=True,
    )
    null: PairedTemporalNull | None = None
    if comparison["precheck_pass"]:
        null = paired_temporal_null(c0, c1, comparison)

    gates = final_gates(comparison, null)
    eligible = all(gates.values())
    if eligible:
        status = (
            "ELIGIBLE_PRICE_DENSE_SEQUENCE_INCREMENTAL_INFORMATION"
        )
    elif comparison["precheck_pass"]:
        status = "FAIL_PRICE_DENSE_SEQUENCE_TEMPORAL_NULL"
    else:
        status = (
            "FAIL_PRICE_DENSE_SEQUENCE_NO_STABLE_INCREMENTAL_VALUE"
        )

    runtime = runtime_provenance(model_fit_run=True, p9_run=True)
    validate_runtime_provenance(runtime)

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "status": status,
        "execution_commit": execution_sha,
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "selected_configuration": {
            "target": {
                "target_id": "A",
                "horizon_seconds": 120,
                "barrier_bps": 16,
            },
            "window_seconds": 32,
            "block": "PRICE",
            "task": "DIRECTION_GIVEN_TOUCH",
            "baseline_feature_count": EXPECTED_BASELINE_FEATURE_COUNT,
            "dense_sequence_feature_count": EXPECTED_DENSE_SEQUENCE_FEATURE_COUNT,
            "augmented_feature_count": EXPECTED_AUGMENTED_FEATURE_COUNT,
            "lag_seconds": list(LAG_SECONDS),
            "sequence_primitives": list(PRICE_LAG_PRIMITIVES),
            "baseline_feature_names": list(BASELINE_FEATURE_NAMES),
            "dense_sequence_feature_names": list(DENSE_SEQUENCE_FEATURE_NAMES),
            "augmented_feature_names": list(AUGMENTED_FEATURE_NAMES),
        },
        "dependency_sha256": dict(sorted(dependency_hashes.items())),
        "frozen_artifacts": {
            "p2c": {
                "path": str(P2C_ARTIFACT_PATH),
                "sha256": P2C_ARTIFACT_SHA256,
            },
            "p3": {
                "path": str(P3_ARTIFACT_PATH),
                "sha256": P3_ARTIFACT_SHA256,
            },
            "p4": {
                "path": str(P4_ARTIFACT_PATH),
                "sha256": P4_ARTIFACT_SHA256,
            },
            "p5": {
                "path": str(P5_ARTIFACT_PATH),
                "sha256": P5_ARTIFACT_SHA256,
            },
            "p6": {
                "path": str(P6_ARTIFACT_PATH),
                "sha256": P6_ARTIFACT_SHA256,
            },
            "p7": {
                "path": str(P7_ARTIFACT_PATH),
                "sha256": P7_ARTIFACT_SHA256,
            },
        },
        "authorized_input_manifest": [
            {
                "date": item.day.isoformat(),
                "path": str(item.path),
                "sha256": item.sha256,
                "bytes": int(item.bytes),
            }
            for item in manifest
        ],
        "p3_reproduction": p3_reproduction,
        "interval_separation_checks": list(interval_checks),
        "exact_support": {
            "expected_pooled_support": EXPECTED_POOLED_SUPPORT,
            "expected_pooled_long": EXPECTED_POOLED_LONG,
            "expected_pooled_short": EXPECTED_POOLED_SHORT,
            "expected_fold_support": list(EXPECTED_FOLD_SUPPORT),
            "expected_fold_long": list(EXPECTED_FOLD_LONG),
            "expected_fold_short": list(EXPECTED_FOLD_SHORT),
            "pooled_support_sha256": c0.pooled_support_sha256,
            "pooled_label_sha256": c0.pooled_label_sha256,
        },
        "c0_price_s1": {
            "feature_count": EXPECTED_BASELINE_FEATURE_COUNT,
            "folds": [_fold_public(fold) for fold in c0.folds],
            "pooled": c0.pooled_metrics,
        },
        "c1_price_s1_plus_dense_sequence": {
            "feature_count": EXPECTED_AUGMENTED_FEATURE_COUNT,
            "folds": [_fold_public(fold) for fold in c1.folds],
            "pooled": c1.pooled_metrics,
        },
        "comparison_c1_vs_c0": comparison,
        "temporal_null": (
            {
                "eligible_shifts": list(null.eligible_shifts),
                "null_log_loss_improvement": list(
                    null.null_log_loss_improvement
                ),
                "null_auc_delta": list(null.null_auc_delta),
                "log_loss_improvement_q95": (
                    null.log_loss_improvement_q95
                ),
                "auc_delta_q95": null.auc_delta_q95,
                "empirical_p": null.empirical_p,
                "observed_log_loss_improvement": (
                    null.observed_log_loss_improvement
                ),
                "observed_auc_delta": null.observed_auc_delta,
                "pass_gate": null.pass_gate,
            }
            if null is not None
            else {
                "status": "TEMPORAL_NULL_NOT_RUN_PRECHECK_FAILED"
            }
        ),
        "promotion_gates": gates,
        "eligible_price_dense_sequence_incremental_information": (
            eligible
        ),
        "runtime_provenance": runtime,
        "prohibited_activity": {
            "forward_data": False,
            "threshold_optimization": False,
            "pnl": False,
            "economics": False,
            "opportunity_gate": False,
            "t2_composition": False,
            "alternate_model_family": False,
            "deep_model": False,
            "lag_search": False,
            "feature_family_search": False,
            "class_weighting_or_resampling": False,
            "calibration": False,
        },
    }

    return write_result_once(
        output,
        payload,
        require_canonical_output=require_canonical_output,
    )


__all__ = [
    "ARTIFACT_FILENAME",
    "AUGMENTED_FEATURE_NAMES",
    "BASELINE_FEATURE_NAMES",
    "C_GRID",
    "DESIGN_VERSION",
    "EXPERIMENT_ID",
    "EXPECTED_AUGMENTED_FEATURE_COUNT",
    "EXPECTED_BASELINE_FEATURE_COUNT",
    "EXPECTED_DENSE_SEQUENCE_FEATURE_COUNT",
    "LAG_SECONDS",
    "PRICE_LAG_PRIMITIVES",
    "P9Error",
    "REAL_OUTPUT_DIRECTORY",
    "DENSE_SEQUENCE_FEATURE_NAMES",
    "ArtifactWriteResult",
    "FoldResult",
    "PairedTemporalNull",
    "RepresentationResult",
    "DenseDay",
    "build_shape_day",
    "canonical_json_bytes",
    "comparison_summary",
    "eligible_shared_shifts",
    "extract_dense_sequence_matrix",
    "final_gates",
    "fit_fold",
    "fit_representation",
    "label_sha256",
    "load_verified_json_artifact",
    "paired_temporal_null",
    "prediction_sha256",
    "probability_metrics",
    "reconcile_selected_candidate_with_p2c",
    "reproduce_frozen_p3",
    "run_p9",
    "runtime_provenance",
    "select_c_probability_first",
    "validate_candidate",
    "validate_expected_p3_support",
    "validate_feature_contract",
    "validate_matched_support",
    "validate_prior_artifacts",
    "validate_runtime_provenance",
    "verify_frozen_dependencies",
    "verify_interval_separation",
    "write_result_once",
]

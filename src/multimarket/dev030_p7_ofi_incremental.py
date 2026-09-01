"""DEV030-P7 incremental multiscale L1 order-flow information.

Frozen scientific question:
Does exactly one predeclared information family -- S1 summaries of
ofi_l1_250ms, ofi_l1_1s, and ofi_l1_3s -- add stable T1
LONG_FIRST-vs-SHORT_FIRST probability information beyond a matched-support
PRICE-only baseline on A / 120s / 16bp / 32s?

P7 changes information, not model family. Both C0 and C1 use the same
train-only StandardScaler + L2 logistic-regression protocol.

The real Jan-Jul P7 run remains separately gated. Synthetic tests may inject
in-memory CandidateDayDataset objects and must not open real market files.
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


EXPERIMENT_ID = "DEV030-P7"
DESIGN_VERSION = "incremental-l1-ofi-v1"

SELECTED_TARGET = p4.SELECTED_TARGET
SELECTED_WINDOW_SECONDS = 32
BASELINE_BLOCK = dd.sf.PRICE
SOURCE_BLOCK = dd.sf.PRICE_BOOK_FLOW

BASELINE_KEY = dd.CandidateKey(
    SELECTED_TARGET, SELECTED_WINDOW_SECONDS, BASELINE_BLOCK
)
SOURCE_KEY = dd.CandidateKey(
    SELECTED_TARGET, SELECTED_WINDOW_SECONDS, SOURCE_BLOCK
)
SELECTED_SPEC = p3.CandidateSpec("A", 120, 16, 32, "PRICE")

SHORT_FIRST = 0
LONG_FIRST = 1
THRESHOLD = 0.5
RANDOM_STATE = 20260825
C_GRID = (0.01, 0.1, 1.0, 10.0)

OFI_SOURCE_FEATURES = (
    "ofi_l1_250ms",
    "ofi_l1_1s",
    "ofi_l1_3s",
)
SUMMARY_STATS = (
    "last",
    "mean",
    "std",
    "minimum",
    "maximum",
    "last_minus_first",
    "ols_slope",
    "sign_persistence",
)

BASELINE_FEATURE_NAMES = dd.sequence_summary_feature_names(BASELINE_BLOCK)
OFI_FEATURE_NAMES = tuple(
    f"{feature}__{stat}"
    for feature in OFI_SOURCE_FEATURES
    for stat in SUMMARY_STATS
)
AUGMENTED_FEATURE_NAMES = BASELINE_FEATURE_NAMES + OFI_FEATURE_NAMES

EXPECTED_BASELINE_FEATURE_COUNT = 23
EXPECTED_OFI_FEATURE_COUNT = 24
EXPECTED_AUGMENTED_FEATURE_COUNT = 47

P2C_ARTIFACT_PATH = p4.P2C_ARTIFACT_PATH
P2C_ARTIFACT_SHA256 = p4.P2C_ARTIFACT_SHA256

P3_ARTIFACT_PATH = p4.P3_ARTIFACT_PATH
P3_ARTIFACT_SHA256 = p4.P3_ARTIFACT_SHA256
P3_SOURCE_REL = "src/multimarket/dev030_p3_direction.py"
P3_TEST_REL = "tests/test_dev030_p3_direction.py"
P3_SOURCE_SHA256 = p4.P3_SOURCE_SHA256
P3_TEST_SHA256 = p4.P3_TEST_SHA256

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

FROZEN_P3_C_BY_FOLD = dict(p4.FROZEN_T1_C_BY_FOLD)
FROZEN_P3_PREDICTION_SHA256_BY_FOLD = dict(
    p4.FROZEN_T1_PREDICTION_SHA256_BY_FOLD
)

REAL_OUTPUT_DIRECTORY = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p7_ofi_incremental_v1"
)
ARTIFACT_FILENAME = "DEV030_P7_OFI_INCREMENTAL_RESULT.json"

PREDICTION_HASH_DOMAIN = b"DEV030-P7-OOF-PREDICTION-V1\x00"
LABEL_HASH_DOMAIN = b"DEV030-P7-LABELS-V1\x00"

FORWARD_GUARDS = {
    "aug30_analytically_opened": False,
    "sep01_or_later_analytically_opened": False,
    "archive_bucket_opened": False,
    "abundant_love_opened": False,
}


class P7Error(RuntimeError):
    """Frozen P7 protocol, provenance, model, or output violation."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


@dataclass(frozen=True)
class RepresentationDay:
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
        raise P7Error("execution_commit_must_be_full_sha")
    return value


def load_verified_json_artifact(
    path: Path,
    expected_sha256: str,
    *,
    hash_file: Any = _sha256_file,
) -> dict[str, Any]:
    artifact = Path(path)
    if not artifact.is_file():
        raise P7Error("frozen_artifact_missing", str(artifact))
    actual = str(hash_file(artifact))
    if actual != expected_sha256:
        raise P7Error("frozen_artifact_sha256_mismatch", str(artifact))
    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise P7Error("frozen_artifact_read_failed", str(exc)) from exc
    if not isinstance(payload, dict):
        raise P7Error("frozen_artifact_not_object")
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
        (p3.P2B_SOURCE_REL, p3.P2B_SOURCE_SHA256, "p2b_source_sha256_mismatch"),
        (P3_SOURCE_REL, P3_SOURCE_SHA256, "p3_source_sha256_mismatch"),
        (P3_TEST_REL, P3_TEST_SHA256, "p3_test_sha256_mismatch"),
    )
    result: dict[str, str] = {}
    for rel, expected_sha, reason in expected:
        file_path = root / rel
        if not file_path.is_file():
            raise P7Error("frozen_dependency_missing", rel)
        actual = str(hash_file(file_path))
        if actual != expected_sha:
            raise P7Error(reason, rel)
        result[rel] = actual
    return result


def validate_prior_artifacts(
    p3_payload: Mapping[str, Any],
    p4_payload: Mapping[str, Any],
    p5_payload: Mapping[str, Any],
    p6_payload: Mapping[str, Any],
) -> None:
    try:
        p4.validate_p3_selected_survivor(p3_payload)
    except p4.P4Error as exc:
        raise P7Error(exc.reason, str(exc)) from exc

    if p4_payload.get("status") != "FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE":
        raise P7Error("p4_terminal_status_mismatch")
    if p5_payload.get("status") != "FAIL_DIRECT_JOINT_THREECLASS_NO_INCREMENTAL_VALUE":
        raise P7Error("p5_terminal_status_mismatch")
    if p6_payload.get("status") != "FAIL_M2_DIRECTION_NO_STABLE_INCREMENTAL_VALUE":
        raise P7Error("p6_terminal_status_mismatch")
    if p6_payload.get("eligible_for_direction_capacity_upgrade") is not False:
        raise P7Error("p6_capacity_upgrade_state_mismatch")


def validate_feature_contract() -> None:
    if len(BASELINE_FEATURE_NAMES) != EXPECTED_BASELINE_FEATURE_COUNT:
        raise P7Error("baseline_feature_count_mismatch")
    if len(OFI_FEATURE_NAMES) != EXPECTED_OFI_FEATURE_COUNT:
        raise P7Error("ofi_feature_count_mismatch")
    if len(AUGMENTED_FEATURE_NAMES) != EXPECTED_AUGMENTED_FEATURE_COUNT:
        raise P7Error("augmented_feature_count_mismatch")
    expected_ofi = tuple(
        f"{feature}__{stat}"
        for feature in OFI_SOURCE_FEATURES
        for stat in SUMMARY_STATS
    )
    if OFI_FEATURE_NAMES != expected_ofi:
        raise P7Error("ofi_feature_order_mismatch")
    if len(set(AUGMENTED_FEATURE_NAMES)) != len(AUGMENTED_FEATURE_NAMES):
        raise P7Error("augmented_feature_duplicate")


def validate_source_candidate(dataset: dd.CandidateDayDataset) -> None:
    validate_feature_contract()
    if dataset.key != SOURCE_KEY:
        raise P7Error("source_candidate_identity_mismatch")
    expected_names = dd.sequence_summary_feature_names(SOURCE_BLOCK)
    if tuple(dataset.s1_feature_names) != tuple(expected_names):
        raise P7Error("source_feature_order_mismatch")
    missing = [
        name for name in AUGMENTED_FEATURE_NAMES
        if name not in dataset.s1_feature_names
    ]
    if missing:
        raise P7Error("selected_feature_missing", ",".join(missing))


def validate_baseline_candidate(dataset: dd.CandidateDayDataset) -> None:
    if dataset.key != BASELINE_KEY:
        raise P7Error("baseline_candidate_identity_mismatch")
    if tuple(dataset.s1_feature_names) != BASELINE_FEATURE_NAMES:
        raise P7Error("baseline_feature_order_mismatch")


def label_sha256(timestamps_us: Any, labels: Any) -> str:
    ts = np.asarray(timestamps_us, dtype=np.int64)
    y = np.asarray(labels, dtype=np.int8)
    if ts.ndim != 1 or y.ndim != 1 or len(ts) != len(y):
        raise P7Error("label_hash_shape_mismatch")
    if not bool(np.all(np.isin(y, (SHORT_FIRST, LONG_FIRST)))):
        raise P7Error("label_hash_invalid_labels")
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P7Error("label_hash_timestamps_not_chronological")
    digest = hashlib.sha256()
    digest.update(LABEL_HASH_DOMAIN)
    digest.update(struct.pack(">Q", len(ts)))
    for timestamp, label in zip(ts.tolist(), y.tolist(), strict=True):
        digest.update(struct.pack(">qb", int(timestamp), int(label)))
    return digest.hexdigest()


def build_representation_day(
    source: dd.CandidateDayDataset,
) -> RepresentationDay:
    validate_source_candidate(source)
    names = tuple(source.s1_feature_names)
    matrix = np.asarray(source.s1_values, dtype=np.float64)
    labels = np.asarray(source.t1_labels, dtype=np.int8)
    timestamps = np.asarray(source.decision_timestamps_us, dtype=np.int64)
    mask = np.asarray(source.t1_common_valid, dtype=bool)

    if matrix.ndim != 2 or matrix.shape[1] != len(names):
        raise P7Error("source_matrix_shape_mismatch")
    if not (len(matrix) == len(labels) == len(timestamps) == len(mask)):
        raise P7Error("source_array_length_mismatch")

    idx0 = [names.index(name) for name in BASELINE_FEATURE_NAMES]
    idx1 = [names.index(name) for name in AUGMENTED_FEATURE_NAMES]

    x0 = matrix[mask][:, idx0]
    x1 = matrix[mask][:, idx1]
    y = labels[mask]
    ts = timestamps[mask]

    if x0.shape[1] != EXPECTED_BASELINE_FEATURE_COUNT:
        raise P7Error("baseline_selected_shape_mismatch")
    if x1.shape[1] != EXPECTED_AUGMENTED_FEATURE_COUNT:
        raise P7Error("augmented_selected_shape_mismatch")
    if not bool(np.all(np.isfinite(x0))) or not bool(np.all(np.isfinite(x1))):
        raise P7Error("non_finite_selected_features")
    if not bool(np.all(np.isin(y, (SHORT_FIRST, LONG_FIRST)))):
        raise P7Error("matched_t1_labels_invalid")
    if len(ts) == 0 or bool(np.any(np.diff(ts) <= 0)):
        raise P7Error("matched_timestamps_invalid")

    return RepresentationDay(
        day=source.day,
        timestamps_us=ts,
        labels=y,
        c0_values=x0,
        c1_values=x1,
        c0_feature_names=BASELINE_FEATURE_NAMES,
        c1_feature_names=AUGMENTED_FEATURE_NAMES,
        support_sha256=dd.support_sha256(ts),
        label_sha256=label_sha256(ts, y),
    )


def reconcile_candidate_with_p2c(
    candidate_per_day: Mapping[date, dd.CandidateDayDataset],
    p2c_payload: Mapping[str, Any],
    *,
    expected_key: dd.CandidateKey,
) -> None:
    candidates = p2c_payload.get("per_candidate")
    if not isinstance(candidates, list):
        raise P7Error("p2c_candidate_payload_missing")
    target = expected_key.target
    matches = [
        item
        for item in candidates
        if item.get("target")
        == {
            "target_id": target.target_id,
            "horizon_seconds": int(target.horizon_seconds),
            "barrier_bps": int(target.barrier_bps),
        }
        and item.get("window_seconds") == expected_key.window_seconds
        and item.get("block") == expected_key.block
    ]
    if len(matches) != 1:
        raise P7Error("p2c_candidate_not_unique", expected_key.block)
    frozen_days = matches[0].get("per_day")
    if not isinstance(frozen_days, list) or len(frozen_days) != len(dd.HISTORICAL_DAYS):
        raise P7Error("p2c_day_contract_missing", expected_key.block)

    for day, frozen_day in zip(dd.HISTORICAL_DAYS, frozen_days, strict=True):
        dataset = candidate_per_day[day]
        if dataset.key != expected_key:
            raise P7Error("candidate_key_mismatch", expected_key.block)
        expected = {
            "date": day.isoformat(),
            "decision_count": int(dataset.counts["decision_count"]),
            "t1_common_support_count": int(dataset.counts["t1_common_support_count"]),
            "t1_long_common_count": int(dataset.counts["t1_long_common_count"]),
            "t1_short_common_count": int(dataset.counts["t1_short_common_count"]),
            "support_sha256": dict(dataset.support_hashes),
        }
        for field, value in expected.items():
            if frozen_day.get(field) != value:
                raise P7Error(
                    "p2c_candidate_reconciliation_failed",
                    f"{expected_key.block}:{day}:{field}",
                )


def _stack_days(
    per_day: Mapping[date, RepresentationDay],
    days: Sequence[date],
    representation: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if representation not in ("C0", "C1"):
        raise P7Error("invalid_representation")
    chunks = [per_day[day] for day in days]
    x = np.concatenate(
        [
            item.c0_values if representation == "C0" else item.c1_values
            for item in chunks
        ],
        axis=0,
    )
    y = np.concatenate([item.labels for item in chunks]).astype(np.int8, copy=False)
    ts = np.concatenate([item.timestamps_us for item in chunks]).astype(
        np.int64, copy=False
    )
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P7Error("stacked_timestamps_not_chronological")
    return x, y, ts


def probability_metrics(y_true: Any, p_long: Any) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(p_long, dtype=np.float64)
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p) or len(y) == 0:
        raise P7Error("metric_shape_mismatch")
    if not bool(np.all(np.isin(y, (0, 1)))):
        raise P7Error("metric_labels_invalid")
    if len(np.unique(y)) != 2:
        raise P7Error("metric_requires_both_classes")
    if not bool(np.all(np.isfinite(p))) or not bool(np.all((p >= 0) & (p <= 1))):
        raise P7Error("metric_probabilities_invalid")

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
        "balanced_accuracy_at_0_5": float(balanced_accuracy_score(y, pred)),
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
        raise P7Error("c_not_in_frozen_grid")
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
        raise P7Error("inner_feature_shape_mismatch")
    if len(xf) != len(yf) or len(xv) != len(yv):
        raise P7Error("inner_length_mismatch")
    if len(np.unique(yf)) != 2 or len(np.unique(yv)) != 2:
        raise P7Error("inner_split_requires_both_classes")
    if not bool(np.all(np.isfinite(xf))) or not bool(np.all(np.isfinite(xv))):
        raise P7Error("non_finite_inner_features")

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
        raise P7Error("prediction_hash_representation_invalid")
    ts = np.asarray(timestamps_us, dtype=np.int64)
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(p_long, dtype=np.float64)
    if not (ts.ndim == y.ndim == p.ndim == 1):
        raise P7Error("prediction_hash_shape_mismatch")
    if not (len(ts) == len(y) == len(p)):
        raise P7Error("prediction_hash_length_mismatch")
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P7Error("prediction_hash_timestamps_not_chronological")
    if not bool(np.all(np.isin(y, (0, 1)))):
        raise P7Error("prediction_hash_labels_invalid")
    if not bool(np.all(np.isfinite(p))) or not bool(np.all((p >= 0) & (p <= 1))):
        raise P7Error("prediction_hash_probabilities_invalid")

    digest = hashlib.sha256()
    digest.update(PREDICTION_HASH_DOMAIN)
    digest.update(f"{fold_id}|{representation}".encode("ascii"))
    for t, yy, pp in zip(ts.tolist(), y.tolist(), p.tolist(), strict=True):
        digest.update(struct.pack(">qbd", int(t), int(yy), float(pp)))
    return digest.hexdigest()


def fit_fold(
    *,
    fold: dd.FrozenOuterFold,
    per_day: Mapping[date, RepresentationDay],
    representation: str,
) -> FoldResult:
    inner_validation_day = fold.train_days[-1]
    inner_fit_days = fold.train_days[:-1]
    if not inner_fit_days:
        raise P7Error("inner_fit_empty")

    x_if, y_if, _ = _stack_days(per_day, inner_fit_days, representation)
    x_iv, y_iv, _ = _stack_days(
        per_day, (inner_validation_day,), representation
    )
    x_train, y_train, _ = _stack_days(per_day, fold.train_days, representation)
    x_val, y_val, ts_val = _stack_days(
        per_day, (fold.validation_day,), representation
    )

    selected_c, ledger = select_c_probability_first(x_if, y_if, x_iv, y_iv)
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
    per_day: Mapping[date, RepresentationDay],
    representation: str,
) -> RepresentationResult:
    if tuple(per_day) != dd.HISTORICAL_DAYS:
        raise P7Error("representation_day_order_mismatch")
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
        raise P7Error("outer_fold_count_mismatch")
    for a, b in zip(c0.folds, c1.folds, strict=True):
        if a.fold_id != b.fold_id:
            raise P7Error("fold_alignment_mismatch")
        if not np.array_equal(a.timestamps_us, b.timestamps_us):
            raise P7Error("timestamp_alignment_mismatch")
        if not np.array_equal(a.y_true, b.y_true):
            raise P7Error("label_alignment_mismatch")
        if a.support_sha256 != b.support_sha256:
            raise P7Error("support_hash_alignment_mismatch")
        if a.label_sha256 != b.label_sha256:
            raise P7Error("label_hash_alignment_mismatch")
    if (
        c0.pooled_support_sha256 != c1.pooled_support_sha256
        or c0.pooled_label_sha256 != c1.pooled_label_sha256
    ):
        raise P7Error("pooled_support_alignment_mismatch")


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
        float(a.metrics["binary_log_loss"] - b.metrics["binary_log_loss"])
        for a, b in zip(c0.folds, c1.folds, strict=True)
    )
    fold_auc = tuple(
        float(b.metrics["roc_auc"] - a.metrics["roc_auc"])
        for a, b in zip(c0.folds, c1.folds, strict=True)
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
        "pooled_c1_auc_at_least_056": float(c1.pooled_metrics["roc_auc"]) >= 0.56,
        "at_least_3_of_4_fold_log_loss_improve": sum(v > 0 for v in fold_ll) >= 3,
        "at_least_3_of_4_fold_auc_improve": sum(v > 0 for v in fold_auc) >= 3,
        "at_least_3_of_4_fold_c1_auc_gt_050": sum(
            float(f.metrics["roc_auc"]) > 0.50 for f in c1.folds
        ) >= 3,
        "leave_one_fold_out_log_loss_improvement_positive": all(
            v > 0 for v in loo_ll
        ),
        "leave_one_fold_out_auc_delta_positive": all(v > 0 for v in loo_auc),
        "both_classes_receive_nonzero_probability_each_fold": noncollapsed,
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
    sizes = tuple(int(v) for v in group_sizes)
    if not sizes or any(v <= 0 for v in sizes):
        raise P7Error("invalid_null_group_sizes")
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
    shifts = eligible_shared_shifts([len(f.y_true) for f in c0.folds])
    if len(shifts) < 20:
        raise P7Error("insufficient_temporal_null_shifts")

    p0 = np.concatenate([f.p_long for f in c0.folds])
    p1 = np.concatenate([f.p_long for f in c1.folds])
    observed_ll = float(comparison["pooled_log_loss_improvement"])
    observed_auc = float(comparison["pooled_auc_delta"])

    null_ll: list[float] = []
    null_auc: list[float] = []
    for k in shifts:
        shifted = np.concatenate([np.roll(f.y_true, k) for f in c0.folds])
        m0 = probability_metrics(shifted, p0)
        m1 = probability_metrics(shifted, p1)
        null_ll.append(float(m0["binary_log_loss"] - m1["binary_log_loss"]))
        null_auc.append(float(m1["roc_auc"] - m0["roc_auc"]))

    ll_q95 = float(np.quantile(np.asarray(null_ll), 0.95, method="higher"))
    auc_q95 = float(np.quantile(np.asarray(null_auc), 0.95, method="higher"))
    empirical_p = float(
        (1 + sum(v >= observed_ll for v in null_ll)) / (1 + len(null_ll))
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


def reproduce_frozen_p3(
    price_per_day: Mapping[date, dd.CandidateDayDataset],
) -> dict[str, Any]:
    try:
        folds = p4.reproduce_frozen_t1(price_per_day)
    except p4.P4Error as exc:
        raise P7Error(exc.reason, str(exc)) from exc
    return {
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


def runtime_provenance(
    *,
    model_fit_run: bool,
    p7_run: bool,
) -> dict[str, Any]:
    if type(model_fit_run) is not bool or type(p7_run) is not bool:
        raise P7Error("runtime_flags_must_be_builtin_bool")
    if p7_run and not model_fit_run:
        raise P7Error("p7_requires_model_fit")
    return {
        "jan_jul_analytically_opened": True,
        "authorized_development_data": {
            "scope": "BTCUSDT consumed Jan-Jul development days only",
            "analytically_loaded": True,
        },
        "forward_data_guards": dict(FORWARD_GUARDS),
        "model_fit_run": model_fit_run,
        "p7_run": p7_run,
        "threshold_optimization_run": False,
        "pnl_backtest_run": False,
        "opportunity_gate_run": False,
        "t2_composition_run": False,
        "alternate_model_family_run": False,
        "deep_model_run": False,
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
        "p7_run",
        "threshold_optimization_run",
        "pnl_backtest_run",
        "opportunity_gate_run",
        "t2_composition_run",
        "alternate_model_family_run",
        "deep_model_run",
        "feature_family_search_run",
        "class_weighting_or_resampling_run",
        "calibration_run",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise P7Error("runtime_provenance_schema_mismatch")
    if value["jan_jul_analytically_opened"] is not True:
        raise P7Error("jan_jul_runtime_state_invalid")
    guards = value["forward_data_guards"]
    if (
        not isinstance(guards, Mapping)
        or set(guards) != set(FORWARD_GUARDS)
        or any(type(v) is not bool for v in guards.values())
        or any(guards.values())
    ):
        raise P7Error("forward_data_guard_violation")
    if value["p7_run"] and not value["model_fit_run"]:
        raise P7Error("p7_requires_model_fit")
    prohibited = (
        "threshold_optimization_run",
        "pnl_backtest_run",
        "opportunity_gate_run",
        "t2_composition_run",
        "alternate_model_family_run",
        "deep_model_run",
        "feature_family_search_run",
        "class_weighting_or_resampling_run",
        "calibration_run",
    )
    if any(value[name] is not False for name in prohibited):
        raise P7Error("prohibited_runtime_activity")
    return dict(value)


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    def normalize(value: Any) -> Any:
        if value is None or type(value) in (str, bool, int):
            return value
        if type(value) is float:
            if not math.isfinite(value):
                raise P7Error("non_finite_json_value")
            return value
        if isinstance(value, np.generic):
            return normalize(value.item())
        if isinstance(value, np.ndarray):
            return [normalize(v) for v in value.tolist()]
        if isinstance(value, Mapping):
            if not all(isinstance(k, str) for k in value):
                raise P7Error("json_mapping_key_not_string")
            return {k: normalize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(v) for v in value]
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, date):
            return value.isoformat()
        raise P7Error("unsupported_json_value", type(value).__name__)

    text = json.dumps(
        normalize(dict(payload)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return (text + "\n").encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _output_preflight(output_directory: Path) -> None:
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise P7Error("output_directory_already_exists")
    parent = output.parent
    if not parent.is_dir():
        raise P7Error("output_parent_missing")
    probe = parent / f".{output.name}.preflight"
    if probe.exists() or probe.is_symlink():
        raise P7Error("output_probe_preexists")
    try:
        with probe.open("xb") as handle:
            handle.write(b"DEV030-P7 preflight\n")
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
            raise P7Error("output_probe_cleanup_failed", str(cleanup_exc)) from cleanup_exc
        raise P7Error("output_parent_preflight_failed", str(exc)) from exc


def write_result_once(
    output_directory: Path,
    payload: Mapping[str, Any],
    *,
    require_canonical_output: bool = True,
) -> ArtifactWriteResult:
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise P7Error("output_directory_already_exists")
    if require_canonical_output and output != REAL_OUTPUT_DIRECTORY:
        raise P7Error("noncanonical_output_directory")
    if not require_canonical_output and output == REAL_OUTPUT_DIRECTORY:
        raise P7Error("canonical_output_requires_real_mode")

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
            raise P7Error("artifact_directory_fsync_failed", str(exc)) from exc
        try:
            if part.exists():
                part.unlink()
            if output.exists() and not any(output.iterdir()):
                output.rmdir()
        except OSError as cleanup_exc:
            raise P7Error("artifact_cleanup_failed", str(cleanup_exc)) from cleanup_exc
        if isinstance(exc, P7Error):
            raise
        raise P7Error("artifact_write_failed", str(exc)) from exc

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
        "inner_c_ledger": [dict(item) for item in fold.inner_c_ledger],
    }


def run_p7(
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
    manifest_verifier: Any = dd.verify_input_manifest,
    analytical_day_loader: Any = dd.load_authorized_days,
) -> ArtifactWriteResult:
    """Run separately-authorized real P7 after implementation freeze."""

    supplied = {
        "p2c_loader": p2c_loader,
        "p3_loader": p3_loader,
        "p4_loader": p4_loader,
        "p5_loader": p5_loader,
        "p6_loader": p6_loader,
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

    output = Path(output_directory)
    if require_canonical_output:
        if output != REAL_OUTPUT_DIRECTORY:
            raise P7Error("noncanonical_output_directory")
        for name, value in supplied.items():
            if value is not None:
                raise P7Error("canonical_dependency_override_forbidden", name)
        if dependency_verifier is not verify_frozen_dependencies:
            raise P7Error(
                "canonical_dependency_override_forbidden", "dependency_verifier"
            )
        if manifest_verifier is not dd.verify_input_manifest:
            raise P7Error(
                "canonical_dependency_override_forbidden", "manifest_verifier"
            )
        if analytical_day_loader is not dd.load_authorized_days:
            raise P7Error(
                "canonical_dependency_override_forbidden", "analytical_day_loader"
            )
    elif output == REAL_OUTPUT_DIRECTORY:
        raise P7Error("canonical_output_requires_real_mode")

    _output_preflight(output)
    execution_sha = _validate_execution_commit(execution_commit)
    dependency_hashes = dict(dependency_verifier(Path(workspace)))

    p2c_payload = dict(p2c_loader())
    p3_payload = dict(p3_loader())
    p4_payload = dict(p4_loader())
    p5_payload = dict(p5_loader())
    p6_payload = dict(p6_loader())
    validate_prior_artifacts(
        p3_payload, p4_payload, p5_payload, p6_payload
    )

    manifest = tuple(manifest_verifier())
    loaded_days = tuple(analytical_day_loader())
    if tuple(day.day for day in loaded_days) != dd.HISTORICAL_DAYS:
        raise P7Error("loaded_day_calendar_mismatch")

    price_per_day = {
        day.day: dd.build_candidate_day(
            day,
            target=SELECTED_TARGET,
            window_seconds=SELECTED_WINDOW_SECONDS,
            block=BASELINE_BLOCK,
        )
        for day in loaded_days
    }
    flow_per_day = {
        day.day: dd.build_candidate_day(
            day,
            target=SELECTED_TARGET,
            window_seconds=SELECTED_WINDOW_SECONDS,
            block=SOURCE_BLOCK,
        )
        for day in loaded_days
    }

    for dataset in price_per_day.values():
        validate_baseline_candidate(dataset)
    for dataset in flow_per_day.values():
        validate_source_candidate(dataset)

    reconcile_candidate_with_p2c(
        price_per_day, p2c_payload, expected_key=BASELINE_KEY
    )
    reconcile_candidate_with_p2c(
        flow_per_day, p2c_payload, expected_key=SOURCE_KEY
    )

    p3_reproduction = reproduce_frozen_p3(price_per_day)
    if p3_reproduction["pass"] is not True:
        raise P7Error("frozen_p3_reproduction_failed")

    representation_days = {
        day: build_representation_day(flow_per_day[day])
        for day in dd.HISTORICAL_DAYS
    }

    c0 = fit_representation(representation_days, "C0")
    c1 = fit_representation(representation_days, "C1")
    validate_matched_support(c0, c1)

    comparison = comparison_summary(c0, c1, invariants_pass=True)
    null: PairedTemporalNull | None = None
    if comparison["precheck_pass"]:
        null = paired_temporal_null(c0, c1, comparison)

    gates = final_gates(comparison, null)
    eligible = all(gates.values())
    if eligible:
        status = "ELIGIBLE_L1_OFI_INCREMENTAL_INFORMATION"
    elif comparison["precheck_pass"]:
        status = "FAIL_L1_OFI_TEMPORAL_NULL"
    else:
        status = "FAIL_L1_OFI_NO_STABLE_INCREMENTAL_VALUE"

    runtime = runtime_provenance(model_fit_run=True, p7_run=True)
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
            "task": "DIRECTION_GIVEN_TOUCH",
            "baseline_block": BASELINE_BLOCK,
            "source_block": SOURCE_BLOCK,
            "baseline_feature_count": EXPECTED_BASELINE_FEATURE_COUNT,
            "ofi_feature_count": EXPECTED_OFI_FEATURE_COUNT,
            "augmented_feature_count": EXPECTED_AUGMENTED_FEATURE_COUNT,
            "ofi_source_features": list(OFI_SOURCE_FEATURES),
            "baseline_feature_names": list(BASELINE_FEATURE_NAMES),
            "ofi_feature_names": list(OFI_FEATURE_NAMES),
            "augmented_feature_names": list(AUGMENTED_FEATURE_NAMES),
        },
        "dependency_sha256": dict(sorted(dependency_hashes.items())),
        "frozen_artifacts": {
            "p2c": {"path": str(P2C_ARTIFACT_PATH), "sha256": P2C_ARTIFACT_SHA256},
            "p3": {"path": str(P3_ARTIFACT_PATH), "sha256": P3_ARTIFACT_SHA256},
            "p4": {"path": str(P4_ARTIFACT_PATH), "sha256": P4_ARTIFACT_SHA256},
            "p5": {"path": str(P5_ARTIFACT_PATH), "sha256": P5_ARTIFACT_SHA256},
            "p6": {"path": str(P6_ARTIFACT_PATH), "sha256": P6_ARTIFACT_SHA256},
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
        "matched_support": {
            "per_validation_fold": [
                {
                    "fold_id": fold.fold_id,
                    "support": fold.support,
                    "long_count": fold.long_count,
                    "short_count": fold.short_count,
                    "support_sha256": fold.support_sha256,
                    "label_sha256": fold.label_sha256,
                }
                for fold in c0.folds
            ],
            "pooled_support": int(c0.pooled_metrics["support"]),
            "pooled_long_count": int(c0.pooled_metrics["long_count"]),
            "pooled_short_count": int(c0.pooled_metrics["short_count"]),
            "pooled_support_sha256": c0.pooled_support_sha256,
            "pooled_label_sha256": c0.pooled_label_sha256,
        },
        "c0_price_only": {
            "feature_count": EXPECTED_BASELINE_FEATURE_COUNT,
            "folds": [_fold_public(f) for f in c0.folds],
            "pooled": c0.pooled_metrics,
        },
        "c1_price_plus_l1_ofi": {
            "feature_count": EXPECTED_AUGMENTED_FEATURE_COUNT,
            "folds": [_fold_public(f) for f in c1.folds],
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
                "log_loss_improvement_q95": null.log_loss_improvement_q95,
                "auc_delta_q95": null.auc_delta_q95,
                "empirical_p": null.empirical_p,
                "observed_log_loss_improvement": (
                    null.observed_log_loss_improvement
                ),
                "observed_auc_delta": null.observed_auc_delta,
                "pass_gate": null.pass_gate,
            }
            if null is not None
            else {"status": "TEMPORAL_NULL_NOT_RUN_PRECHECK_FAILED"}
        ),
        "promotion_gates": gates,
        "eligible_l1_ofi_incremental_information": eligible,
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
    "EXPECTED_OFI_FEATURE_COUNT",
    "OFI_FEATURE_NAMES",
    "OFI_SOURCE_FEATURES",
    "P7Error",
    "REAL_OUTPUT_DIRECTORY",
    "ArtifactWriteResult",
    "FoldResult",
    "PairedTemporalNull",
    "RepresentationDay",
    "RepresentationResult",
    "build_representation_day",
    "canonical_json_bytes",
    "comparison_summary",
    "eligible_shared_shifts",
    "final_gates",
    "fit_fold",
    "fit_representation",
    "label_sha256",
    "load_verified_json_artifact",
    "paired_temporal_null",
    "prediction_sha256",
    "probability_metrics",
    "reconcile_candidate_with_p2c",
    "reproduce_frozen_p3",
    "run_p7",
    "runtime_provenance",
    "select_c_probability_first",
    "validate_feature_contract",
    "validate_matched_support",
    "validate_prior_artifacts",
    "validate_runtime_provenance",
    "validate_source_candidate",
    "verify_frozen_dependencies",
    "write_result_once",
]

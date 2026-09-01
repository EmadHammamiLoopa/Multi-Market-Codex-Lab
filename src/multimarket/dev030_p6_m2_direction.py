"""DEV030-P6 bounded nonlinear T1 direction-capacity experiment.

Frozen scientific question:
Does a tightly bounded HistGradientBoostingClassifier add stable conditional
LONG_FIRST-vs-SHORT_FIRST probability information beyond the exact frozen P3
M1 logistic head on the selected A / 120s / 16bp / 32s / PRICE / S1
representation?

This module deliberately excludes:
- target/window/block/feature search;
- class weighting/resampling;
- calibration or threshold optimization;
- T2/opportunity composition;
- PnL/economics;
- forward holdout;
- alternate/deep model families.

The real Jan-Jul P6 run remains separately gated. Synthetic tests may inject
in-memory CandidateDayDataset objects and must not open real market files.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
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

from . import dev030_direction_dataset as dd
from . import dev030_direction_materialize as dm
from . import dev030_p3_direction as p3
from . import dev030_p4_touch_composition as p4


EXPERIMENT_ID = "DEV030-P6"
DESIGN_VERSION = "m2-direction-hgb-v1"

SELECTED_TARGET = p4.SELECTED_TARGET
SELECTED_WINDOW_SECONDS = 32
SELECTED_BLOCK = "PRICE"
SELECTED_KEY = dd.CandidateKey(
    SELECTED_TARGET,
    SELECTED_WINDOW_SECONDS,
    SELECTED_BLOCK,
)
SELECTED_SPEC = p3.CandidateSpec("A", 120, 16, 32, "PRICE")

SHORT_FIRST = 0
LONG_FIRST = 1
THRESHOLD = 0.5
RANDOM_STATE = 20260825

EXPECTED_FEATURE_COUNT = 23
EXPECTED_POOLED_VALIDATION_SUPPORT = 573
EXPECTED_POOLED_VALIDATION_LONG = 309
EXPECTED_POOLED_VALIDATION_SHORT = 264
EXPECTED_FOLD_SUPPORT = (159, 64, 126, 224)
EXPECTED_FOLD_LONG = (86, 40, 60, 123)
EXPECTED_FOLD_SHORT = (73, 24, 66, 101)

FROZEN_M1_C_BY_FOLD = dict(p4.FROZEN_T1_C_BY_FOLD)
FROZEN_M1_PREDICTION_SHA256_BY_FOLD = dict(
    p4.FROZEN_T1_PREDICTION_SHA256_BY_FOLD
)

P3_SOURCE_REL = "src/multimarket/dev030_p3_direction.py"
P3_TEST_REL = "tests/test_dev030_p3_direction.py"
P3_SOURCE_SHA256 = (
    "9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675"
)
P3_TEST_SHA256 = (
    "a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b"
)
P3_ARTIFACT_PATH = p4.P3_ARTIFACT_PATH
P3_ARTIFACT_SHA256 = p4.P3_ARTIFACT_SHA256

P4_SOURCE_REL = "src/multimarket/dev030_p4_touch_composition.py"
P4_TEST_REL = "tests/test_dev030_p4_touch_composition.py"
P4_SOURCE_SHA256 = (
    "bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f"
)
P4_TEST_SHA256 = (
    "7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265"
)
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

P2C_ARTIFACT_PATH = p4.P2C_ARTIFACT_PATH
P2C_ARTIFACT_SHA256 = p4.P2C_ARTIFACT_SHA256

REAL_OUTPUT_DIRECTORY = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p6_m2_direction_v1"
)
ARTIFACT_FILENAME = "DEV030_P6_M2_DIRECTION_RESULT.json"

CAPACITY_GRID = (
    ("H1", 3, 50),
    ("H2", 3, 100),
    ("H3", 7, 50),
    ("H4", 7, 100),
)

FIXED_HGB_PARAMS = {
    "loss": "log_loss",
    "learning_rate": 0.05,
    "min_samples_leaf": 20,
    "l2_regularization": 1.0,
    "max_features": 1.0,
    "max_bins": 255,
    "categorical_features": None,
    "early_stopping": False,
    "class_weight": None,
    "random_state": RANDOM_STATE,
}

FORWARD_GUARDS = {
    "aug30_analytically_opened": False,
    "sep01_or_later_analytically_opened": False,
    "archive_bucket_opened": False,
    "abundant_love_opened": False,
}

M2_PREDICTION_HASH_DOMAIN = b"DEV030-P6-M2-OOF-PREDICTION-V1\x00"
LABEL_HASH_DOMAIN = b"DEV030-P6-T1-LABELS-V1\x00"


class P6Error(RuntimeError):
    """Frozen P6 protocol, provenance, modeling, or output violation."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


@dataclass(frozen=True)
class DirectionFold:
    fold_id: int
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


@dataclass(frozen=True)
class M2Fold(DirectionFold):
    selected_capacity_id: str
    selected_max_leaf_nodes: int
    selected_max_iter: int
    inner_capacity_ledger: tuple[dict[str, Any], ...]
    model: Any


@dataclass(frozen=True)
class M2Result:
    folds: tuple[M2Fold, ...]
    pooled_metrics: dict[str, Any]
    pooled_support_sha256: str
    pooled_label_sha256: str


@dataclass(frozen=True)
class M1Result:
    folds: tuple[DirectionFold, ...]
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
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise P6Error("execution_commit_must_be_full_sha")
    return value


def verify_frozen_dependencies(
    repository_root: Path,
    *,
    hash_file: Any = _sha256_file,
) -> dict[str, str]:
    root = Path(repository_root).resolve()
    expected = (
        (P3_SOURCE_REL, P3_SOURCE_SHA256, "p3_source_sha256_mismatch"),
        (P3_TEST_REL, P3_TEST_SHA256, "p3_test_sha256_mismatch"),
        (P4_SOURCE_REL, P4_SOURCE_SHA256, "p4_source_sha256_mismatch"),
        (P4_TEST_REL, P4_TEST_SHA256, "p4_test_sha256_mismatch"),
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
    )
    result: dict[str, str] = {}
    for rel, expected_sha, reason in expected:
        source = root / rel
        if not source.is_file():
            raise P6Error("frozen_dependency_missing", rel)
        actual = str(hash_file(source))
        if actual != expected_sha:
            raise P6Error(reason, rel)
        result[rel] = actual
    return result


def load_verified_json_artifact(
    path: Path,
    expected_sha256: str,
    *,
    hash_file: Any = _sha256_file,
) -> dict[str, Any]:
    artifact = Path(path)
    if not artifact.is_file():
        raise P6Error("frozen_artifact_missing", str(artifact))
    if str(hash_file(artifact)) != expected_sha256:
        raise P6Error("frozen_artifact_sha256_mismatch", str(artifact))
    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise P6Error("frozen_artifact_read_failed", str(exc)) from exc
    if not isinstance(payload, dict):
        raise P6Error("frozen_artifact_not_object")
    return payload


def validate_prior_artifacts(
    p3_payload: Mapping[str, Any],
    p4_payload: Mapping[str, Any],
    p5_payload: Mapping[str, Any],
) -> None:
    try:
        p4.validate_p3_selected_survivor(p3_payload)
    except p4.P4Error as exc:
        raise P6Error(exc.reason, str(exc)) from exc

    expected_base = {
        "target": {"target_id": "A", "horizon_seconds": 120, "barrier_bps": 16},
        "window_seconds": 32,
        "block": "PRICE",
    }
    if p4_payload.get("experiment_id") != "DEV030-P4":
        raise P6Error("p4_experiment_id_mismatch")
    if p4_payload.get("status") != "FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE":
        raise P6Error("p4_terminal_status_mismatch")
    if p4_payload.get("selected_configuration") != expected_base:
        raise P6Error("p4_selected_configuration_mismatch")
    t2 = p4_payload.get("t2")
    if not isinstance(t2, Mapping) or t2.get("eligible_for_composition") is not True:
        raise P6Error("p4_t2_not_frozen_eligible")

    if p5_payload.get("experiment_id") != "DEV030-P5":
        raise P6Error("p5_experiment_id_mismatch")
    if p5_payload.get("status") != "FAIL_DIRECT_JOINT_THREECLASS_NO_INCREMENTAL_VALUE":
        raise P6Error("p5_terminal_status_mismatch")
    expected_p5 = {**expected_base, "representation": "S1"}
    if p5_payload.get("selected_configuration") != expected_p5:
        raise P6Error("p5_selected_configuration_mismatch")
    if p5_payload.get("p4_baseline_reproduction", {}).get("pass") is not True:
        raise P6Error("p5_p4_baseline_reproduction_not_passed")


def validate_selected_candidate(dataset: dd.CandidateDayDataset) -> None:
    if dataset.key != SELECTED_KEY:
        raise P6Error("selected_candidate_identity_mismatch")
    expected_names = dd.sequence_summary_feature_names(SELECTED_BLOCK)
    if tuple(dataset.s1_feature_names) != tuple(expected_names):
        raise P6Error("selected_s1_feature_order_mismatch")
    if len(expected_names) != EXPECTED_FEATURE_COUNT:
        raise P6Error("selected_feature_count_mismatch")
    values = np.asarray(dataset.s1_values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != EXPECTED_FEATURE_COUNT:
        raise P6Error("selected_s1_feature_shape_mismatch")


def _t1_rows(
    dataset: dd.CandidateDayDataset,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    validate_selected_candidate(dataset)
    mask = np.asarray(dataset.t1_common_valid, dtype=bool)
    x = np.asarray(dataset.s1_values, dtype=np.float64)
    labels = np.asarray(dataset.t1_labels, dtype=np.int8)
    timestamps = np.asarray(dataset.decision_timestamps_us, dtype=np.int64)
    if not (len(mask) == len(x) == len(labels) == len(timestamps)):
        raise P6Error("candidate_array_length_mismatch")
    selected_x = x[mask]
    selected_y = labels[mask]
    selected_ts = timestamps[mask]
    if len(selected_y) == 0:
        raise P6Error("t1_support_empty")
    if not bool(np.all(np.isin(selected_y, (SHORT_FIRST, LONG_FIRST)))):
        raise P6Error("t1_labels_invalid")
    if not bool(np.all(np.isfinite(selected_x))):
        raise P6Error("non_finite_m2_features")
    if len(selected_ts) and bool(np.any(np.diff(selected_ts) <= 0)):
        raise P6Error("t1_timestamps_not_chronological")
    return selected_x, selected_y, selected_ts


def _stack_days(
    per_day: Mapping[date, dd.CandidateDayDataset],
    days: Sequence[date],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    chunks = [_t1_rows(per_day[day]) for day in days]
    x = np.concatenate([item[0] for item in chunks], axis=0)
    y = np.concatenate([item[1] for item in chunks], axis=0)
    ts = np.concatenate([item[2] for item in chunks], axis=0)
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P6Error("stacked_t1_timestamps_not_chronological")
    return x, y, ts


def label_sha256(timestamps_us: Any, labels: Any) -> str:
    ts = np.asarray(timestamps_us, dtype=np.int64)
    y = np.asarray(labels, dtype=np.int8)
    if ts.ndim != 1 or y.ndim != 1 or len(ts) != len(y):
        raise P6Error("label_hash_shape_mismatch")
    if not bool(np.all(np.isin(y, (SHORT_FIRST, LONG_FIRST)))):
        raise P6Error("label_hash_invalid_labels")
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P6Error("label_hash_timestamps_not_chronological")
    digest = hashlib.sha256()
    digest.update(LABEL_HASH_DOMAIN)
    digest.update(struct.pack(">Q", len(ts)))
    for timestamp, label in zip(ts.tolist(), y.tolist(), strict=True):
        digest.update(struct.pack(">qb", int(timestamp), int(label)))
    return digest.hexdigest()


def binary_probability_metrics(y_true: Any, p_long: Any) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(p_long, dtype=np.float64)
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p) or len(y) == 0:
        raise P6Error("binary_metric_shape_mismatch")
    if not bool(np.all(np.isin(y, (SHORT_FIRST, LONG_FIRST)))):
        raise P6Error("binary_metric_labels_invalid")
    if len(np.unique(y)) != 2:
        raise P6Error("binary_metric_requires_both_classes")
    if not bool(np.all(np.isfinite(p))) or not bool(np.all((p >= 0.0) & (p <= 1.0))):
        raise P6Error("binary_metric_probabilities_invalid")

    pred = (p >= THRESHOLD).astype(np.int8)
    cm = confusion_matrix(y, pred, labels=[SHORT_FIRST, LONG_FIRST])
    precision, recall, f1, support = precision_recall_fscore_support(
        y,
        pred,
        labels=[SHORT_FIRST, LONG_FIRST],
        zero_division=0,
    )
    return {
        "support": int(len(y)),
        "long_count": int(np.count_nonzero(y == LONG_FIRST)),
        "short_count": int(np.count_nonzero(y == SHORT_FIRST)),
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
        "predicted_long_count_at_0_5": int(np.count_nonzero(pred == LONG_FIRST)),
        "predicted_short_count_at_0_5": int(np.count_nonzero(pred == SHORT_FIRST)),
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


def _capacity_spec(capacity_id: str) -> tuple[int, int]:
    matches = [
        (leaves, iterations)
        for cid, leaves, iterations in CAPACITY_GRID
        if cid == capacity_id
    ]
    if len(matches) != 1:
        raise P6Error("capacity_id_not_frozen", capacity_id)
    return matches[0]


def new_m2_model(capacity_id: str) -> HistGradientBoostingClassifier:
    leaves, iterations = _capacity_spec(capacity_id)
    return HistGradientBoostingClassifier(
        max_leaf_nodes=int(leaves),
        max_iter=int(iterations),
        **FIXED_HGB_PARAMS,
    )


def select_capacity(
    x_inner_fit: Any,
    y_inner_fit: Any,
    x_inner_validation: Any,
    y_inner_validation: Any,
) -> tuple[str, tuple[dict[str, Any], ...]]:
    xf = np.asarray(x_inner_fit, dtype=np.float64)
    xv = np.asarray(x_inner_validation, dtype=np.float64)
    yf = np.asarray(y_inner_fit, dtype=np.int8)
    yv = np.asarray(y_inner_validation, dtype=np.int8)
    if xf.ndim != 2 or xv.ndim != 2 or xf.shape[1] != xv.shape[1]:
        raise P6Error("inner_feature_shape_mismatch")
    if xf.shape[1] != EXPECTED_FEATURE_COUNT:
        raise P6Error("inner_feature_count_mismatch")
    if len(xf) != len(yf) or len(xv) != len(yv):
        raise P6Error("inner_length_mismatch")
    if set(np.unique(yf).tolist()) != {SHORT_FIRST, LONG_FIRST}:
        raise P6Error("inner_fit_requires_both_classes")
    if set(np.unique(yv).tolist()) != {SHORT_FIRST, LONG_FIRST}:
        raise P6Error("inner_validation_requires_both_classes")
    if not bool(np.all(np.isfinite(xf))) or not bool(np.all(np.isfinite(xv))):
        raise P6Error("non_finite_m2_features")

    ledger: list[dict[str, Any]] = []
    for capacity_id, leaves, iterations in CAPACITY_GRID:
        model = new_m2_model(capacity_id)
        model.fit(xf, yf)
        if tuple(model.classes_.tolist()) != (SHORT_FIRST, LONG_FIRST):
            raise P6Error("m2_class_order_mismatch")
        p_long = model.predict_proba(xv)[:, 1]
        metrics = binary_probability_metrics(yv, p_long)
        ledger.append(
            {
                "capacity_id": capacity_id,
                "max_leaf_nodes": int(leaves),
                "max_iter": int(iterations),
                "binary_log_loss": metrics["binary_log_loss"],
                "brier": metrics["brier"],
                "roc_auc": metrics["roc_auc"],
            }
        )

    selected = sorted(
        ledger,
        key=lambda item: (
            float(item["binary_log_loss"]),
            float(item["brier"]),
            -float(item["roc_auc"]),
            int(item["max_leaf_nodes"]),
            int(item["max_iter"]),
        ),
    )[0]
    return str(selected["capacity_id"]), tuple(ledger)


def m2_prediction_sha256(
    *,
    fold_id: int,
    capacity_id: str,
    timestamps_us: Any,
    y_true: Any,
    p_long: Any,
) -> str:
    ts = np.asarray(timestamps_us, dtype=np.int64)
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(p_long, dtype=np.float64)
    if ts.ndim != 1 or y.ndim != 1 or p.ndim != 1:
        raise P6Error("prediction_hash_shape_mismatch")
    if not (len(ts) == len(y) == len(p)):
        raise P6Error("prediction_hash_length_mismatch")
    if not bool(np.all(np.isin(y, (0, 1)))):
        raise P6Error("prediction_hash_labels_invalid")
    if not bool(np.all(np.isfinite(p))) or not bool(np.all((p >= 0) & (p <= 1))):
        raise P6Error("prediction_hash_probabilities_invalid")
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P6Error("prediction_hash_timestamps_not_chronological")

    digest = hashlib.sha256()
    digest.update(M2_PREDICTION_HASH_DOMAIN)
    domain = (
        f"{SELECTED_SPEC.target_id}|{SELECTED_SPEC.horizon_seconds}|"
        f"{SELECTED_SPEC.barrier_bps}|{SELECTED_SPEC.window_seconds}|"
        f"{SELECTED_SPEC.block}|S1|{int(fold_id)}|{capacity_id}"
    ).encode("ascii")
    digest.update(struct.pack(">Q", len(domain)))
    digest.update(domain)
    digest.update(struct.pack(">Q", len(ts)))
    for timestamp, truth, probability in zip(
        ts.tolist(), y.tolist(), p.tolist(), strict=True
    ):
        digest.update(struct.pack(">qbd", int(timestamp), int(truth), float(probability)))
    return digest.hexdigest()


def fit_m2_fold(
    *,
    fold: dd.FrozenOuterFold,
    per_day: Mapping[date, dd.CandidateDayDataset],
) -> M2Fold:
    inner_validation_day = fold.train_days[-1]
    inner_fit_days = fold.train_days[:-1]
    if not inner_fit_days:
        raise P6Error("inner_fit_empty")

    x_if, y_if, _ = _stack_days(per_day, inner_fit_days)
    x_iv, y_iv, _ = _stack_days(per_day, (inner_validation_day,))
    x_train, y_train, _ = _stack_days(per_day, fold.train_days)
    x_val, y_val, ts_val = _stack_days(per_day, (fold.validation_day,))

    capacity_id, ledger = select_capacity(x_if, y_if, x_iv, y_iv)
    leaves, iterations = _capacity_spec(capacity_id)
    model = new_m2_model(capacity_id)
    model.fit(x_train, y_train)
    if tuple(model.classes_.tolist()) != (SHORT_FIRST, LONG_FIRST):
        raise P6Error("m2_class_order_mismatch")
    p_long = model.predict_proba(x_val)[:, 1]
    pred = (p_long >= THRESHOLD).astype(np.int8)
    metrics = binary_probability_metrics(y_val, p_long)

    return M2Fold(
        fold_id=int(fold.fold_id),
        support=int(len(y_val)),
        long_count=int(np.count_nonzero(y_val == LONG_FIRST)),
        short_count=int(np.count_nonzero(y_val == SHORT_FIRST)),
        metrics=metrics,
        timestamps_us=ts_val,
        y_true=y_val,
        p_long=p_long,
        y_pred=pred,
        prediction_sha256=m2_prediction_sha256(
            fold_id=fold.fold_id,
            capacity_id=capacity_id,
            timestamps_us=ts_val,
            y_true=y_val,
            p_long=p_long,
        ),
        support_sha256=dd.support_sha256(ts_val),
        label_sha256=label_sha256(ts_val, y_val),
        selected_capacity_id=capacity_id,
        selected_max_leaf_nodes=int(leaves),
        selected_max_iter=int(iterations),
        inner_capacity_ledger=ledger,
        model=model,
    )


def validate_fold_support_contract(
    folds: Sequence[DirectionFold],
) -> None:
    if len(folds) != 4:
        raise P6Error("outer_fold_count_mismatch")
    if tuple(item.support for item in folds) != EXPECTED_FOLD_SUPPORT:
        raise P6Error("fold_support_contract_mismatch")
    if tuple(item.long_count for item in folds) != EXPECTED_FOLD_LONG:
        raise P6Error("fold_long_count_contract_mismatch")
    if tuple(item.short_count for item in folds) != EXPECTED_FOLD_SHORT:
        raise P6Error("fold_short_count_contract_mismatch")

    y = np.concatenate([item.y_true for item in folds])
    ts = np.concatenate([item.timestamps_us for item in folds])
    if len(y) != EXPECTED_POOLED_VALIDATION_SUPPORT:
        raise P6Error("pooled_support_contract_mismatch")
    if int(np.count_nonzero(y == LONG_FIRST)) != EXPECTED_POOLED_VALIDATION_LONG:
        raise P6Error("pooled_long_count_contract_mismatch")
    if int(np.count_nonzero(y == SHORT_FIRST)) != EXPECTED_POOLED_VALIDATION_SHORT:
        raise P6Error("pooled_short_count_contract_mismatch")
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P6Error("pooled_timestamps_not_chronological")


def fit_m2(
    per_day: Mapping[date, dd.CandidateDayDataset],
) -> M2Result:
    if tuple(per_day) != dd.HISTORICAL_DAYS:
        raise P6Error("candidate_day_order_mismatch")
    folds = tuple(
        fit_m2_fold(fold=fold, per_day=per_day)
        for fold in dd.OUTER_FOLDS
    )
    validate_fold_support_contract(folds)
    y = np.concatenate([fold.y_true for fold in folds])
    p = np.concatenate([fold.p_long for fold in folds])
    ts = np.concatenate([fold.timestamps_us for fold in folds])
    return M2Result(
        folds=folds,
        pooled_metrics=binary_probability_metrics(y, p),
        pooled_support_sha256=dd.support_sha256(ts),
        pooled_label_sha256=label_sha256(ts, y),
    )


def reconstruct_frozen_m1(
    per_day: Mapping[date, dd.CandidateDayDataset],
) -> M1Result:
    try:
        reproduction = p4.reproduce_frozen_t1(per_day)
    except p4.P4Error as exc:
        raise P6Error(exc.reason, str(exc)) from exc

    folds: list[DirectionFold] = []
    for outer, frozen in zip(dd.OUTER_FOLDS, reproduction, strict=True):
        if frozen.fold_id != outer.fold_id:
            raise P6Error("m1_fold_alignment_mismatch")
        if frozen.selected_c != FROZEN_M1_C_BY_FOLD[outer.fold_id]:
            raise P6Error("m1_frozen_c_mismatch")
        if (
            frozen.expected_prediction_sha256
            != FROZEN_M1_PREDICTION_SHA256_BY_FOLD[outer.fold_id]
            or frozen.actual_prediction_sha256
            != FROZEN_M1_PREDICTION_SHA256_BY_FOLD[outer.fold_id]
            or frozen.reproduced is not True
        ):
            raise P6Error("m1_prediction_hash_reproduction_failed")

        x_val, y_val, ts_val = _stack_days(per_day, (outer.validation_day,))
        p_long = frozen.model.predict_proba(frozen.scaler.transform(x_val))[:, 1]
        pred = (p_long >= THRESHOLD).astype(np.int8)
        actual_hash = p3.prediction_sha256(
            spec=SELECTED_SPEC,
            representation="S1",
            fold_id=outer.fold_id,
            timestamps_us=ts_val,
            y_true=y_val,
            y_pred=pred,
            p_long=p_long,
        )
        if actual_hash != FROZEN_M1_PREDICTION_SHA256_BY_FOLD[outer.fold_id]:
            raise P6Error("m1_probability_hash_reproduction_failed")

        folds.append(
            DirectionFold(
                fold_id=int(outer.fold_id),
                support=int(len(y_val)),
                long_count=int(np.count_nonzero(y_val == LONG_FIRST)),
                short_count=int(np.count_nonzero(y_val == SHORT_FIRST)),
                metrics=binary_probability_metrics(y_val, p_long),
                timestamps_us=ts_val,
                y_true=y_val,
                p_long=p_long,
                y_pred=pred,
                prediction_sha256=actual_hash,
                support_sha256=dd.support_sha256(ts_val),
                label_sha256=label_sha256(ts_val, y_val),
            )
        )

    result_folds = tuple(folds)
    validate_fold_support_contract(result_folds)
    y = np.concatenate([fold.y_true for fold in result_folds])
    p = np.concatenate([fold.p_long for fold in result_folds])
    ts = np.concatenate([fold.timestamps_us for fold in result_folds])
    pooled = binary_probability_metrics(y, p)

    if not math.isclose(
        float(pooled["balanced_accuracy_at_0_5"]),
        0.5419424831488764,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise P6Error("m1_pooled_balanced_accuracy_mismatch")
    if not math.isclose(
        float(pooled["macro_f1_at_0_5"]),
        0.5113006396588486,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise P6Error("m1_pooled_macro_f1_mismatch")
    if not math.isclose(
        float(pooled["mcc_at_0_5"]),
        0.092011918153975,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise P6Error("m1_pooled_mcc_mismatch")
    if not math.isclose(
        float(pooled["roc_auc"]),
        0.5367264881752768,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise P6Error("m1_pooled_auc_mismatch")

    return M1Result(
        folds=result_folds,
        pooled_metrics=pooled,
        pooled_support_sha256=dd.support_sha256(ts),
        pooled_label_sha256=label_sha256(ts, y),
    )


def verify_interval_separation(
    per_day: Mapping[date, dd.CandidateDayDataset],
) -> tuple[dict[str, Any], ...]:
    """Prove train target-information ends before validation raw feature starts."""

    if tuple(per_day) != dd.HISTORICAL_DAYS:
        raise P6Error("candidate_day_order_mismatch")

    checks: list[dict[str, Any]] = []

    def one_check(
        *,
        scope: str,
        fold_id: int,
        train_days: Sequence[date],
        validation_day: date,
    ) -> None:
        _, _, train_ts = _stack_days(per_day, train_days)
        _, _, val_ts = _stack_days(per_day, (validation_day,))
        train_last = int(train_ts[-1])
        validation_first = int(val_ts[0])
        train_info = dd.sf.information_intervals(
            decision_timestamp_us=train_last,
            window_seconds=SELECTED_WINDOW_SECONDS,
            block=SELECTED_BLOCK,
            target_horizon_seconds=SELECTED_TARGET.horizon_seconds,
        )
        validation_info = dd.sf.information_intervals(
            decision_timestamp_us=validation_first,
            window_seconds=SELECTED_WINDOW_SECONDS,
            block=SELECTED_BLOCK,
            target_horizon_seconds=SELECTED_TARGET.horizon_seconds,
        )
        passed = (
            int(train_info.raw_source_end_us)
            < int(validation_info.raw_source_start_us)
        )
        if not passed:
            raise P6Error(
                "train_validation_information_interval_overlap",
                f"{scope}:fold={fold_id}",
            )
        checks.append(
            {
                "scope": scope,
                "fold_id": int(fold_id),
                "train_last_decision_us": train_last,
                "train_raw_source_end_us": int(train_info.raw_source_end_us),
                "validation_first_decision_us": validation_first,
                "validation_raw_source_start_us": int(
                    validation_info.raw_source_start_us
                ),
                "pass": True,
            }
        )

    for outer in dd.OUTER_FOLDS:
        one_check(
            scope="outer",
            fold_id=outer.fold_id,
            train_days=outer.train_days,
            validation_day=outer.validation_day,
        )
        one_check(
            scope="inner",
            fold_id=outer.fold_id,
            train_days=outer.train_days[:-1],
            validation_day=outer.train_days[-1],
        )
    return tuple(checks)


def comparison_summary(
    *,
    m1: M1Result,
    m2: M2Result,
    invariant_pass: bool,
) -> dict[str, Any]:
    if len(m1.folds) != 4 or len(m2.folds) != 4:
        raise P6Error("comparison_outer_fold_count_mismatch")

    for a, b in zip(m1.folds, m2.folds, strict=True):
        if a.fold_id != b.fold_id:
            raise P6Error("comparison_fold_alignment_mismatch")
        if not np.array_equal(a.timestamps_us, b.timestamps_us):
            raise P6Error("comparison_timestamp_alignment_mismatch")
        if not np.array_equal(a.y_true, b.y_true):
            raise P6Error("comparison_label_alignment_mismatch")
        if a.support_sha256 != b.support_sha256 or a.label_sha256 != b.label_sha256:
            raise P6Error("comparison_support_hash_alignment_mismatch")

    pooled_log_loss_improvement = float(
        m1.pooled_metrics["binary_log_loss"]
        - m2.pooled_metrics["binary_log_loss"]
    )
    pooled_brier_improvement = float(
        m1.pooled_metrics["brier"] - m2.pooled_metrics["brier"]
    )
    pooled_auc_delta = float(
        m2.pooled_metrics["roc_auc"] - m1.pooled_metrics["roc_auc"]
    )

    fold_log_loss_improvement = tuple(
        float(
            m1_fold.metrics["binary_log_loss"]
            - m2_fold.metrics["binary_log_loss"]
        )
        for m1_fold, m2_fold in zip(m1.folds, m2.folds, strict=True)
    )
    fold_auc_delta = tuple(
        float(
            m2_fold.metrics["roc_auc"] - m1_fold.metrics["roc_auc"]
        )
        for m1_fold, m2_fold in zip(m1.folds, m2.folds, strict=True)
    )

    loo_ll: list[float] = []
    loo_auc: list[float] = []
    for omitted in range(4):
        y = np.concatenate(
            [m1.folds[i].y_true for i in range(4) if i != omitted]
        )
        p1 = np.concatenate(
            [m1.folds[i].p_long for i in range(4) if i != omitted]
        )
        p2 = np.concatenate(
            [m2.folds[i].p_long for i in range(4) if i != omitted]
        )
        m1_metrics = binary_probability_metrics(y, p1)
        m2_metrics = binary_probability_metrics(y, p2)
        loo_ll.append(
            float(
                m1_metrics["binary_log_loss"]
                - m2_metrics["binary_log_loss"]
            )
        )
        loo_auc.append(
            float(m2_metrics["roc_auc"] - m1_metrics["roc_auc"])
        )

    probability_noncollapse = all(
        bool(np.any(fold.p_long > 0.0) and np.any(fold.p_long < 1.0))
        for fold in m2.folds
    )

    gates = {
        "pooled_log_loss_better_than_m1": pooled_log_loss_improvement > 0.0,
        "pooled_brier_better_than_m1": pooled_brier_improvement > 0.0,
        "pooled_auc_better_than_m1": pooled_auc_delta > 0.0,
        "pooled_m2_auc_at_least_056": float(m2.pooled_metrics["roc_auc"]) >= 0.56,
        "at_least_3_of_4_fold_log_loss_improve": sum(
            value > 0.0 for value in fold_log_loss_improvement
        ) >= 3,
        "at_least_3_of_4_fold_m2_auc_gt_050": sum(
            float(fold.metrics["roc_auc"]) > 0.50 for fold in m2.folds
        ) >= 3,
        "at_least_3_of_4_fold_m2_auc_at_least_m1": sum(
            value >= 0.0 for value in fold_auc_delta
        ) >= 3,
        "leave_one_fold_out_log_loss_improvement_positive": all(
            value > 0.0 for value in loo_ll
        ),
        "leave_one_fold_out_auc_delta_positive": all(
            value > 0.0 for value in loo_auc
        ),
        "both_classes_receive_nonzero_probability_each_fold": probability_noncollapse,
        "all_invariants_pass": bool(invariant_pass),
    }

    return {
        "pooled_log_loss_improvement_vs_m1": pooled_log_loss_improvement,
        "pooled_brier_improvement_vs_m1": pooled_brier_improvement,
        "pooled_auc_delta_vs_m1": pooled_auc_delta,
        "fold_log_loss_improvement_vs_m1": list(fold_log_loss_improvement),
        "fold_auc_delta_vs_m1": list(fold_auc_delta),
        "leave_one_fold_out_log_loss_improvement_vs_m1": loo_ll,
        "leave_one_fold_out_auc_delta_vs_m1": loo_auc,
        "precheck_gates": gates,
        "precheck_pass": all(gates.values()),
    }


def eligible_shared_shifts(group_sizes: Sequence[int]) -> tuple[int, ...]:
    sizes = tuple(int(value) for value in group_sizes)
    if not sizes or any(value <= 0 for value in sizes):
        raise P6Error("invalid_null_group_sizes")
    return tuple(
        k
        for k in range(1, min(sizes))
        if all(min(k, n - k) >= 10 for n in sizes)
    )


def paired_temporal_null(
    *,
    m1: M1Result,
    m2: M2Result,
    comparison: Mapping[str, Any],
) -> PairedTemporalNull:
    shifts = eligible_shared_shifts([len(fold.y_true) for fold in m1.folds])
    if len(shifts) < 20:
        raise P6Error("insufficient_temporal_null_shifts")

    p1 = np.concatenate([fold.p_long for fold in m1.folds])
    p2 = np.concatenate([fold.p_long for fold in m2.folds])
    observed_ll = float(comparison["pooled_log_loss_improvement_vs_m1"])
    observed_auc = float(comparison["pooled_auc_delta_vs_m1"])

    null_ll: list[float] = []
    null_auc: list[float] = []
    for k in shifts:
        shifted = np.concatenate(
            [np.roll(fold.y_true, k) for fold in m1.folds]
        )
        metrics1 = binary_probability_metrics(shifted, p1)
        metrics2 = binary_probability_metrics(shifted, p2)
        null_ll.append(
            float(
                metrics1["binary_log_loss"]
                - metrics2["binary_log_loss"]
            )
        )
        null_auc.append(
            float(metrics2["roc_auc"] - metrics1["roc_auc"])
        )

    ll_q95 = float(np.quantile(np.asarray(null_ll), 0.95, method="higher"))
    auc_q95 = float(np.quantile(np.asarray(null_auc), 0.95, method="higher"))
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
    *,
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
    p6_run: bool,
) -> dict[str, Any]:
    if type(model_fit_run) is not bool or type(p6_run) is not bool:
        raise P6Error("runtime_flags_must_be_builtin_bool")
    if p6_run and not model_fit_run:
        raise P6Error("p6_requires_model_fit")
    return {
        "jan_jul_analytically_opened": True,
        "authorized_development_data": {
            "scope": "BTCUSDT consumed Jan-Jul development days only",
            "analytically_loaded": True,
        },
        "forward_data_guards": dict(FORWARD_GUARDS),
        "model_fit_run": model_fit_run,
        "p6_run": p6_run,
        "threshold_optimization_run": False,
        "pnl_backtest_run": False,
        "opportunity_gate_run": False,
        "t2_composition_run": False,
        "alternate_model_family_run": False,
        "deep_model_run": False,
        "class_weighting_or_resampling_run": False,
        "calibration_run": False,
    }


def validate_runtime_provenance(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "jan_jul_analytically_opened",
        "authorized_development_data",
        "forward_data_guards",
        "model_fit_run",
        "p6_run",
        "threshold_optimization_run",
        "pnl_backtest_run",
        "opportunity_gate_run",
        "t2_composition_run",
        "alternate_model_family_run",
        "deep_model_run",
        "class_weighting_or_resampling_run",
        "calibration_run",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise P6Error("runtime_provenance_schema_mismatch")
    if value["jan_jul_analytically_opened"] is not True:
        raise P6Error("jan_jul_runtime_state_invalid")
    development = value["authorized_development_data"]
    if (
        not isinstance(development, Mapping)
        or set(development) != {"scope", "analytically_loaded"}
        or development["scope"] != "BTCUSDT consumed Jan-Jul development days only"
        or development["analytically_loaded"] is not True
    ):
        raise P6Error("authorized_development_runtime_mismatch")
    guards = value["forward_data_guards"]
    if (
        not isinstance(guards, Mapping)
        or set(guards) != set(FORWARD_GUARDS)
        or any(type(item) is not bool for item in guards.values())
        or any(guards.values())
    ):
        raise P6Error("forward_data_guard_violation")
    for field in (
        "model_fit_run",
        "p6_run",
        "threshold_optimization_run",
        "pnl_backtest_run",
        "opportunity_gate_run",
        "t2_composition_run",
        "alternate_model_family_run",
        "deep_model_run",
        "class_weighting_or_resampling_run",
        "calibration_run",
    ):
        if type(value[field]) is not bool:
            raise P6Error("runtime_flags_must_be_builtin_bool")
    if value["p6_run"] and not value["model_fit_run"]:
        raise P6Error("p6_requires_model_fit")
    prohibited = (
        "threshold_optimization_run",
        "pnl_backtest_run",
        "opportunity_gate_run",
        "t2_composition_run",
        "alternate_model_family_run",
        "deep_model_run",
        "class_weighting_or_resampling_run",
        "calibration_run",
    )
    if any(value[field] for field in prohibited):
        raise P6Error("prohibited_runtime_activity")
    return dict(value)


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    def normalize(value: Any) -> Any:
        if value is None or type(value) in (str, bool, int):
            return value
        if type(value) is float:
            if not math.isfinite(value):
                raise P6Error("non_finite_json_value")
            return value
        if isinstance(value, np.generic):
            return normalize(value.item())
        if isinstance(value, np.ndarray):
            return [normalize(item) for item in value.tolist()]
        if isinstance(value, Mapping):
            if not all(isinstance(key, str) for key in value):
                raise P6Error("json_mapping_key_not_string")
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, date):
            return value.isoformat()
        raise P6Error("unsupported_json_value", type(value).__name__)

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
        raise P6Error("output_directory_already_exists")
    parent = output.parent
    if not parent.is_dir():
        raise P6Error("output_parent_missing")
    probe = parent / f".{output.name}.preflight"
    if probe.exists() or probe.is_symlink():
        raise P6Error("output_probe_preexists")
    try:
        with probe.open("xb") as handle:
            handle.write(b"DEV030-P6 preflight\n")
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
            raise P6Error("output_probe_cleanup_failed", str(cleanup_exc)) from cleanup_exc
        raise P6Error("output_parent_preflight_failed", str(exc)) from exc


def write_result_once(
    output_directory: Path,
    payload: Mapping[str, Any],
    *,
    require_canonical_output: bool = True,
) -> ArtifactWriteResult:
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise P6Error("output_directory_already_exists")
    if not require_canonical_output and output == REAL_OUTPUT_DIRECTORY:
        raise P6Error("canonical_output_requires_real_mode")
    if require_canonical_output and output != REAL_OUTPUT_DIRECTORY:
        raise P6Error("noncanonical_output_directory")

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
            raise P6Error("artifact_directory_fsync_failed", str(exc)) from exc
        try:
            if part.exists():
                part.unlink()
            if output.exists() and not any(output.iterdir()):
                output.rmdir()
        except OSError as cleanup_exc:
            raise P6Error("artifact_cleanup_failed", str(cleanup_exc)) from cleanup_exc
        if isinstance(exc, P6Error):
            raise
        raise P6Error("artifact_write_failed", str(exc)) from exc

    return ArtifactWriteResult(
        output_directory=output,
        artifact_path=final,
        artifact_sha256=hashlib.sha256(content).hexdigest(),
        artifact_bytes=len(content),
    )


def _direction_fold_public(fold: DirectionFold) -> dict[str, Any]:
    return {
        "fold_id": fold.fold_id,
        "support": fold.support,
        "long_count": fold.long_count,
        "short_count": fold.short_count,
        "metrics": fold.metrics,
        "prediction_sha256": fold.prediction_sha256,
        "support_sha256": fold.support_sha256,
        "label_sha256": fold.label_sha256,
    }


def _m2_fold_public(fold: M2Fold) -> dict[str, Any]:
    return {
        **_direction_fold_public(fold),
        "selected_capacity_id": fold.selected_capacity_id,
        "selected_max_leaf_nodes": fold.selected_max_leaf_nodes,
        "selected_max_iter": fold.selected_max_iter,
        "inner_capacity_ledger": [dict(item) for item in fold.inner_capacity_ledger],
    }


def run_p6(
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
    manifest_verifier: Any = dd.verify_input_manifest,
    analytical_day_loader: Any = dd.load_authorized_days,
) -> ArtifactWriteResult:
    """Run the separately-authorized canonical P6 development campaign."""

    supplied = {
        "p2c_loader": p2c_loader,
        "p3_loader": p3_loader,
        "p4_loader": p4_loader,
        "p5_loader": p5_loader,
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

    output = Path(output_directory)
    if require_canonical_output:
        if output != REAL_OUTPUT_DIRECTORY:
            raise P6Error("noncanonical_output_directory")
        for name, value in supplied.items():
            if value is not None:
                raise P6Error("canonical_dependency_override_forbidden", name)
        if dependency_verifier is not verify_frozen_dependencies:
            raise P6Error(
                "canonical_dependency_override_forbidden", "dependency_verifier"
            )
        if manifest_verifier is not dd.verify_input_manifest:
            raise P6Error(
                "canonical_dependency_override_forbidden", "manifest_verifier"
            )
        if analytical_day_loader is not dd.load_authorized_days:
            raise P6Error(
                "canonical_dependency_override_forbidden", "analytical_day_loader"
            )
    elif output == REAL_OUTPUT_DIRECTORY:
        raise P6Error("canonical_output_requires_real_mode")

    _output_preflight(output)
    execution_sha = _validate_execution_commit(execution_commit)
    dependency_hashes = dict(dependency_verifier(Path(workspace)))

    p2c_payload = dict(p2c_loader())
    p3_payload = dict(p3_loader())
    p4_payload = dict(p4_loader())
    p5_payload = dict(p5_loader())
    validate_prior_artifacts(p3_payload, p4_payload, p5_payload)

    manifest = tuple(manifest_verifier())
    loaded_days = tuple(analytical_day_loader())
    if tuple(day.day for day in loaded_days) != dd.HISTORICAL_DAYS:
        raise P6Error("loaded_day_calendar_mismatch")

    candidate_per_day = {
        day.day: dd.build_candidate_day(
            day,
            target=SELECTED_TARGET,
            window_seconds=SELECTED_WINDOW_SECONDS,
            block=SELECTED_BLOCK,
        )
        for day in loaded_days
    }
    if tuple(candidate_per_day) != dd.HISTORICAL_DAYS:
        raise P6Error("selected_candidate_day_order_mismatch")
    for dataset in candidate_per_day.values():
        validate_selected_candidate(dataset)

    try:
        p4.reconcile_selected_candidate_with_p2c(candidate_per_day, p2c_payload)
    except p4.P4Error as exc:
        raise P6Error(exc.reason, str(exc)) from exc

    interval_checks = verify_interval_separation(candidate_per_day)
    m1 = reconstruct_frozen_m1(candidate_per_day)
    m2 = fit_m2(candidate_per_day)

    if (
        m1.pooled_support_sha256 != m2.pooled_support_sha256
        or m1.pooled_label_sha256 != m2.pooled_label_sha256
    ):
        raise P6Error("pooled_support_or_label_hash_mismatch")

    comparison = comparison_summary(
        m1=m1,
        m2=m2,
        invariant_pass=True,
    )

    null: PairedTemporalNull | None = None
    if comparison["precheck_pass"]:
        null = paired_temporal_null(m1=m1, m2=m2, comparison=comparison)

    gates = final_gates(comparison=comparison, null=null)
    eligible = all(gates.values())
    if eligible:
        status = "ELIGIBLE_FOR_DIRECTION_CAPACITY_UPGRADE"
    elif comparison["precheck_pass"]:
        status = "FAIL_M2_DIRECTION_TEMPORAL_NULL"
    else:
        status = "FAIL_M2_DIRECTION_NO_STABLE_INCREMENTAL_VALUE"

    runtime = runtime_provenance(model_fit_run=True, p6_run=True)
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
            "representation": "S1",
            "task": "DIRECTION_GIVEN_TOUCH",
            "feature_count": EXPECTED_FEATURE_COUNT,
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
        "interval_separation_checks": list(interval_checks),
        "m1_reproduction": {
            "pass": True,
            "frozen_C_by_fold": dict(FROZEN_M1_C_BY_FOLD),
            "frozen_prediction_sha256_by_fold": dict(
                FROZEN_M1_PREDICTION_SHA256_BY_FOLD
            ),
            "folds": [_direction_fold_public(fold) for fold in m1.folds],
            "pooled": m1.pooled_metrics,
            "pooled_support_sha256": m1.pooled_support_sha256,
            "pooled_label_sha256": m1.pooled_label_sha256,
        },
        "m2": {
            "model_family": "HistGradientBoostingClassifier",
            "fixed_params": dict(FIXED_HGB_PARAMS),
            "capacity_grid": [
                {
                    "capacity_id": capacity_id,
                    "max_leaf_nodes": leaves,
                    "max_iter": iterations,
                }
                for capacity_id, leaves, iterations in CAPACITY_GRID
            ],
            "folds": [_m2_fold_public(fold) for fold in m2.folds],
            "pooled": m2.pooled_metrics,
            "pooled_support_sha256": m2.pooled_support_sha256,
            "pooled_label_sha256": m2.pooled_label_sha256,
        },
        "comparison_vs_m1": comparison,
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
        "eligible_for_direction_capacity_upgrade": eligible,
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
    "CAPACITY_GRID",
    "DESIGN_VERSION",
    "EXPECTED_FEATURE_COUNT",
    "EXPECTED_FOLD_SUPPORT",
    "EXPECTED_POOLED_VALIDATION_SUPPORT",
    "EXPERIMENT_ID",
    "FIXED_HGB_PARAMS",
    "FROZEN_M1_C_BY_FOLD",
    "FROZEN_M1_PREDICTION_SHA256_BY_FOLD",
    "P6Error",
    "REAL_OUTPUT_DIRECTORY",
    "SELECTED_BLOCK",
    "SELECTED_KEY",
    "SELECTED_SPEC",
    "SELECTED_TARGET",
    "SELECTED_WINDOW_SECONDS",
    "ArtifactWriteResult",
    "DirectionFold",
    "M1Result",
    "M2Fold",
    "M2Result",
    "PairedTemporalNull",
    "binary_probability_metrics",
    "canonical_json_bytes",
    "comparison_summary",
    "eligible_shared_shifts",
    "final_gates",
    "fit_m2",
    "fit_m2_fold",
    "label_sha256",
    "load_verified_json_artifact",
    "m2_prediction_sha256",
    "new_m2_model",
    "paired_temporal_null",
    "reconstruct_frozen_m1",
    "run_p6",
    "runtime_provenance",
    "select_capacity",
    "validate_prior_artifacts",
    "validate_runtime_provenance",
    "validate_selected_candidate",
    "verify_frozen_dependencies",
    "verify_interval_separation",
    "write_result_once",
]

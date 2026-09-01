"""DEV030-P5 direct low-complexity joint three-class experiment.

Frozen configuration:
    BTCUSDT / target A / 120s / 16bp / 32s / PRICE / S1

Classes:
    NONE=0, SHORT_FIRST=1, LONG_FIRST=2

P5 tests whether a single direct multinomial logistic model improves joint
probability quality over the frozen P4 C1 baseline.  No threshold search,
economics, opportunity gate, forward holdout, class weighting, resampling, or
higher-capacity model is implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from . import dev030_direction_dataset as dd
from . import dev030_p3_direction as p3
from . import dev030_p4_touch_composition as p4


EXPERIMENT_ID = "DEV030-P5"
DESIGN_VERSION = "joint-threeclass-v1"

SELECTED_TARGET = p4.SELECTED_TARGET
SELECTED_WINDOW_SECONDS = p4.SELECTED_WINDOW_SECONDS
SELECTED_BLOCK = p4.SELECTED_BLOCK
SELECTED_KEY = p4.SELECTED_KEY

NONE = 0
SHORT_FIRST = 1
LONG_FIRST = 2
CLASS_ORDER = (NONE, SHORT_FIRST, LONG_FIRST)
CLASS_NAMES = ("NONE", "SHORT_FIRST", "LONG_FIRST")

C_GRID = (0.01, 0.1, 1.0, 10.0)
RANDOM_STATE = 20260825

P4_SOURCE_REL = "src/multimarket/dev030_p4_touch_composition.py"
P4_TEST_REL = "tests/test_dev030_p4_touch_composition.py"
P4_SOURCE_SHA256 = "bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f"
P4_TEST_SHA256 = "7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265"
P4_ARTIFACT_PATH = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p4_t2_composition_v1/"
    "DEV030_P4_T2_COMPOSITION_RESULT.json"
)
P4_ARTIFACT_SHA256 = "8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16"

P3_SOURCE_REL = "src/multimarket/dev030_p3_direction.py"
P3_SOURCE_SHA256 = "9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675"
P3_ARTIFACT_PATH = p4.P3_ARTIFACT_PATH
P3_ARTIFACT_SHA256 = p4.P3_ARTIFACT_SHA256
P2C_ARTIFACT_PATH = p4.P2C_ARTIFACT_PATH
P2C_ARTIFACT_SHA256 = p4.P2C_ARTIFACT_SHA256

EXPECTED_POOLED_SUPPORT = 5748
EXPECTED_POOLED_COUNTS = {
    "NONE": 5175,
    "SHORT_FIRST": 264,
    "LONG_FIRST": 309,
}
EXPECTED_FOLD_SUPPORT = (1437, 1437, 1437, 1437)

REAL_OUTPUT_DIRECTORY = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p5_joint_threeclass_v1"
)
ARTIFACT_FILENAME = "DEV030_P5_JOINT_THREECLASS_RESULT.json"

FORWARD_GUARDS = {
    "aug30_analytically_opened": False,
    "sep01_or_later_analytically_opened": False,
    "archive_bucket_opened": False,
    "abundant_love_opened": False,
}


class P5Error(RuntimeError):
    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


@dataclass(frozen=True)
class JointDayDataset:
    day: date
    timestamps_us: np.ndarray
    labels: np.ndarray
    s1_values: np.ndarray
    s1_feature_names: tuple[str, ...]
    support_sha256: str
    label_sha256: str
    class_counts: dict[str, int]


@dataclass(frozen=True)
class JointFoldResult:
    fold_id: int
    selected_c: float
    support: int
    class_counts: dict[str, int]
    metrics: dict[str, Any]
    timestamps_us: np.ndarray
    y_true: np.ndarray
    probabilities: np.ndarray
    prediction_sha256: str
    support_sha256: str
    label_sha256: str
    inner_c_ledger: tuple[dict[str, Any], ...]
    scaler: Any
    model: Any


@dataclass(frozen=True)
class JointModelResult:
    folds: tuple[JointFoldResult, ...]
    pooled: dict[str, Any]
    pooled_support_sha256: str
    pooled_label_sha256: str


@dataclass(frozen=True)
class BaselineBundle:
    c0_folds: tuple[np.ndarray, ...]
    c1_folds: tuple[np.ndarray, ...]
    c2_folds: tuple[np.ndarray, ...]
    labels_by_fold: tuple[np.ndarray, ...]
    timestamps_by_fold: tuple[np.ndarray, ...]
    metrics_c0_folds: tuple[dict[str, Any], ...]
    metrics_c1_folds: tuple[dict[str, Any], ...]
    metrics_c2_folds: tuple[dict[str, Any], ...]
    pooled_c0: dict[str, Any]
    pooled_c1: dict[str, Any]
    pooled_c2: dict[str, Any]


@dataclass(frozen=True)
class JointTemporalNull:
    eligible_shifts: tuple[int, ...]
    null_log_loss_improvement: tuple[float, ...]
    null_macro_ap_delta: tuple[float, ...]
    log_loss_improvement_q95: float
    macro_ap_delta_q95: float
    empirical_p: float
    observed_log_loss_improvement: float
    observed_macro_ap_delta: float
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
        raise P5Error("execution_commit_must_be_full_sha")
    return value


def verify_frozen_dependencies(
    repository_root: Path,
    *,
    hash_file: Any = _sha256_file,
) -> dict[str, str]:
    root = Path(repository_root).resolve()
    expected = (
        (P4_SOURCE_REL, P4_SOURCE_SHA256, "p4_source_sha256_mismatch"),
        (P4_TEST_REL, P4_TEST_SHA256, "p4_test_sha256_mismatch"),
        (P3_SOURCE_REL, P3_SOURCE_SHA256, "p3_source_sha256_mismatch"),
        (dd.FIRST_PASSAGE_SOURCE_REL, dd.FIRST_PASSAGE_SOURCE_SHA256,
         "first_passage_source_sha256_mismatch"),
        (dd.SEQUENCE_FEATURE_SOURCE_REL, dd.SEQUENCE_FEATURE_SOURCE_SHA256,
         "sequence_source_sha256_mismatch"),
        (p3.P2B_SOURCE_REL, p3.P2B_SOURCE_SHA256, "p2b_source_sha256_mismatch"),
    )
    result: dict[str, str] = {}
    for rel, expected_sha, reason in expected:
        source = root / rel
        if not source.is_file():
            raise P5Error("frozen_dependency_missing", rel)
        actual = str(hash_file(source))
        if actual != expected_sha:
            raise P5Error(reason, rel)
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
        raise P5Error("frozen_artifact_missing", str(artifact))
    if str(hash_file(artifact)) != expected_sha256:
        raise P5Error("frozen_artifact_sha256_mismatch", str(artifact))
    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise P5Error("frozen_artifact_read_failed", str(exc)) from exc
    if not isinstance(payload, dict):
        raise P5Error("frozen_artifact_not_object")
    return payload


def validate_p4_artifact_identity(payload: Mapping[str, Any]) -> None:
    if payload.get("experiment_id") != "DEV030-P4":
        raise P5Error("p4_experiment_id_mismatch")
    if payload.get("status") != "FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE":
        raise P5Error("p4_terminal_status_mismatch")
    expected = {
        "target": {"target_id": "A", "horizon_seconds": 120, "barrier_bps": 16},
        "window_seconds": 32,
        "block": "PRICE",
    }
    if payload.get("selected_configuration") != expected:
        raise P5Error("p4_selected_configuration_mismatch")
    t2 = payload.get("t2")
    if not isinstance(t2, Mapping) or t2.get("eligible_for_composition") is not True:
        raise P5Error("p4_t2_not_frozen_eligible")


def validate_selected_candidate(dataset: dd.CandidateDayDataset) -> None:
    try:
        p4.validate_selected_candidate(dataset)
    except p4.P4Error as exc:
        raise P5Error(exc.reason, str(exc)) from exc


def _label_hash(timestamps_us: Any, labels: Any) -> str:
    ts = np.asarray(timestamps_us, dtype=np.int64)
    y = np.asarray(labels, dtype=np.int8)
    if ts.ndim != 1 or y.ndim != 1 or len(ts) != len(y):
        raise P5Error("label_hash_shape_mismatch")
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P5Error("label_hash_timestamps_not_chronological")
    digest = hashlib.sha256()
    digest.update(b"DEV030-P5-JOINT-LABELS-V1\x00")
    for t, yy in zip(ts.tolist(), y.tolist(), strict=True):
        digest.update(int(t).to_bytes(8, "big", signed=True))
        digest.update(int(yy).to_bytes(1, "big", signed=False))
    return digest.hexdigest()


def build_joint_day(dataset: dd.CandidateDayDataset) -> JointDayDataset:
    validate_selected_candidate(dataset)
    t2_day = p4.build_t2_day(dataset)
    labels = p4.three_class_labels(dataset, t2_day)
    if len(labels) != len(t2_day.timestamps_us):
        raise P5Error("joint_support_length_mismatch")
    if not bool(np.all(np.isin(labels, CLASS_ORDER))):
        raise P5Error("joint_label_mapping_invalid")
    x = np.asarray(t2_day.s1_values, dtype=np.float64)
    if not bool(np.all(np.isfinite(x))):
        raise P5Error("non_finite_joint_features")
    counts = {
        "NONE": int(np.count_nonzero(labels == NONE)),
        "SHORT_FIRST": int(np.count_nonzero(labels == SHORT_FIRST)),
        "LONG_FIRST": int(np.count_nonzero(labels == LONG_FIRST)),
    }
    ts = np.asarray(t2_day.timestamps_us, dtype=np.int64)
    return JointDayDataset(
        dataset.day,
        ts,
        labels.astype(np.int8, copy=False),
        x,
        tuple(t2_day.s1_feature_names),
        dd.support_sha256(ts),
        _label_hash(ts, labels),
        counts,
    )


def _stack_days(
    per_day: Mapping[date, JointDayDataset],
    days: Sequence[date],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    chunks = [per_day[day] for day in days]
    x = np.concatenate([item.s1_values for item in chunks])
    y = np.concatenate([item.labels for item in chunks]).astype(np.int8, copy=False)
    ts = np.concatenate([item.timestamps_us for item in chunks]).astype(np.int64, copy=False)
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P5Error("joint_stack_not_chronological")
    return x, y, ts


def _new_joint_logistic(c_value: float) -> LogisticRegression:
    if c_value not in C_GRID:
        raise P5Error("c_not_in_frozen_grid")
    return LogisticRegression(
        C=float(c_value),
        solver="lbfgs",
        l1_ratio=0.0,
        class_weight=None,
        max_iter=1000,
        fit_intercept=True,
        random_state=RANDOM_STATE,
    )


def _validate_probability_matrix(probabilities: Any, rows: int | None = None) -> np.ndarray:
    p = np.asarray(probabilities, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3:
        raise P5Error("joint_probability_shape_mismatch")
    if rows is not None and p.shape[0] != int(rows):
        raise P5Error("joint_probability_row_mismatch")
    if not bool(np.all(np.isfinite(p))) or not bool(np.all((p >= 0) & (p <= 1))):
        raise P5Error("invalid_joint_probability")
    if not bool(np.allclose(p.sum(axis=1), 1.0, rtol=0.0, atol=1e-12)):
        raise P5Error("joint_probability_sum_mismatch")
    return p


def joint_metrics(y_true: Any, probabilities: Any) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int8)
    if y.ndim != 1 or len(y) == 0 or not bool(np.all(np.isin(y, CLASS_ORDER))):
        raise P5Error("invalid_joint_labels")
    try:
        return p4.multiclass_probability_metrics(
            y,
            _validate_probability_matrix(probabilities, len(y)),
        )
    except p4.P4Error as exc:
        raise P5Error(exc.reason, str(exc)) from exc


def select_c(
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
        raise P5Error("inner_feature_shape_mismatch")
    if len(xf) != len(yf) or len(xv) != len(yv):
        raise P5Error("inner_length_mismatch")
    if set(np.unique(yf).tolist()) != set(CLASS_ORDER):
        raise P5Error("inner_fit_missing_class")
    if set(np.unique(yv).tolist()) != set(CLASS_ORDER):
        raise P5Error("inner_validation_missing_class")
    if not bool(np.all(np.isfinite(xf))) or not bool(np.all(np.isfinite(xv))):
        raise P5Error("non_finite_joint_features")

    ledger: list[dict[str, Any]] = []
    for c_value in C_GRID:
        scaler = StandardScaler()
        xfs = scaler.fit_transform(xf)
        xvs = scaler.transform(xv)
        model = _new_joint_logistic(c_value)
        model.fit(xfs, yf)
        if tuple(model.classes_.tolist()) != CLASS_ORDER:
            raise P5Error("joint_model_class_order_mismatch")
        probabilities = model.predict_proba(xvs)
        metrics = joint_metrics(yv, probabilities)
        ledger.append({
            "C": float(c_value),
            "multiclass_log_loss": metrics["multiclass_log_loss"],
            "multiclass_brier": metrics["multiclass_brier"],
            "macro_ovr_average_precision": metrics["macro_ovr_average_precision"],
        })

    chosen = sorted(
        ledger,
        key=lambda item: (
            float(item["multiclass_log_loss"]),
            float(item["multiclass_brier"]),
            -float(item["macro_ovr_average_precision"]),
            float(item["C"]),
        ),
    )[0]
    return float(chosen["C"]), tuple(ledger)


def _prediction_hash(
    *,
    fold_id: int,
    timestamps_us: Any,
    y_true: Any,
    probabilities: Any,
) -> str:
    ts = np.asarray(timestamps_us, dtype=np.int64)
    y = np.asarray(y_true, dtype=np.int8)
    p = _validate_probability_matrix(probabilities, len(y))
    if len(ts) != len(y):
        raise P5Error("prediction_hash_length_mismatch")
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P5Error("prediction_hash_timestamps_not_chronological")
    digest = hashlib.sha256()
    digest.update(b"DEV030-P5-J1-OOF-V1\x00")
    digest.update(int(fold_id).to_bytes(2, "big", signed=False))
    for t, yy, row in zip(ts.tolist(), y.tolist(), p, strict=True):
        digest.update(int(t).to_bytes(8, "big", signed=True))
        digest.update(int(yy).to_bytes(1, "big", signed=False))
        digest.update(np.asarray(row, dtype=">f8").tobytes())
    return digest.hexdigest()


def fit_joint_fold(
    *,
    fold: dd.FrozenOuterFold,
    per_day: Mapping[date, JointDayDataset],
) -> JointFoldResult:
    inner_validation_day = fold.train_days[-1]
    inner_fit_days = fold.train_days[:-1]
    x_if, y_if, _ = _stack_days(per_day, inner_fit_days)
    x_iv, y_iv, _ = _stack_days(per_day, (inner_validation_day,))
    x_train, y_train, _ = _stack_days(per_day, fold.train_days)
    x_val, y_val, ts_val = _stack_days(per_day, (fold.validation_day,))

    selected_c, ledger = select_c(x_if, y_if, x_iv, y_iv)

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_val_scaled = scaler.transform(x_val)
    model = _new_joint_logistic(selected_c)
    model.fit(x_train_scaled, y_train)
    if tuple(model.classes_.tolist()) != CLASS_ORDER:
        raise P5Error("joint_model_class_order_mismatch")
    probs = model.predict_proba(x_val_scaled)
    metrics = joint_metrics(y_val, probs)
    counts = {
        "NONE": int(np.count_nonzero(y_val == NONE)),
        "SHORT_FIRST": int(np.count_nonzero(y_val == SHORT_FIRST)),
        "LONG_FIRST": int(np.count_nonzero(y_val == LONG_FIRST)),
    }
    return JointFoldResult(
        fold.fold_id,
        selected_c,
        int(len(y_val)),
        counts,
        metrics,
        ts_val,
        y_val,
        probs,
        _prediction_hash(
            fold_id=fold.fold_id,
            timestamps_us=ts_val,
            y_true=y_val,
            probabilities=probs,
        ),
        dd.support_sha256(ts_val),
        _label_hash(ts_val, y_val),
        ledger,
        scaler,
        model,
    )


def fit_joint_model(
    per_day: Mapping[date, JointDayDataset],
) -> JointModelResult:
    if tuple(per_day) != dd.HISTORICAL_DAYS:
        raise P5Error("joint_day_order_mismatch")
    folds = tuple(
        fit_joint_fold(fold=fold, per_day=per_day)
        for fold in dd.OUTER_FOLDS
    )
    y = np.concatenate([f.y_true for f in folds])
    p = np.concatenate([f.probabilities for f in folds])
    ts = np.concatenate([f.timestamps_us for f in folds])
    if tuple(f.support for f in folds) != EXPECTED_FOLD_SUPPORT:
        raise P5Error("p5_fold_support_contract_mismatch")
    if len(y) != EXPECTED_POOLED_SUPPORT:
        raise P5Error("p5_pooled_support_contract_mismatch")
    counts = {
        "NONE": int(np.count_nonzero(y == NONE)),
        "SHORT_FIRST": int(np.count_nonzero(y == SHORT_FIRST)),
        "LONG_FIRST": int(np.count_nonzero(y == LONG_FIRST)),
    }
    if counts != EXPECTED_POOLED_COUNTS:
        raise P5Error("p5_pooled_class_count_contract_mismatch")
    return JointModelResult(
        folds,
        joint_metrics(y, p),
        dd.support_sha256(ts),
        _label_hash(ts, y),
    )


def _three_class_training_prevalence(
    candidate_per_day: Mapping[date, dd.CandidateDayDataset],
    t2_per_day: Mapping[date, p4.T2DayDataset],
    days: Sequence[date],
) -> np.ndarray:
    labels = np.concatenate([
        p4.three_class_labels(candidate_per_day[day], t2_per_day[day])
        for day in days
    ])
    counts = np.asarray(
        [np.count_nonzero(labels == cls) for cls in CLASS_ORDER],
        dtype=np.float64,
    )
    if counts.sum() <= 0:
        raise P5Error("three_class_training_support_empty")
    return counts / counts.sum()


def reconstruct_p4_baselines(
    *,
    candidate_per_day: Mapping[date, dd.CandidateDayDataset],
    t2_per_day: Mapping[date, p4.T2DayDataset],
) -> BaselineBundle:
    t2_result = p4.fit_t2(t2_per_day)
    if not t2_result.precheck_pass:
        raise P5Error("p4_t2_reconstruction_precheck_failed")
    t2_null = p4.t2_temporal_null(t2_result.s1_folds)
    if not p4.t2_is_eligible(t2_result, t2_null):
        raise P5Error("p4_t2_reconstruction_not_eligible")
    t1_reproduction = p4.reproduce_frozen_t1(candidate_per_day)

    c0_folds: list[np.ndarray] = []
    c1_folds: list[np.ndarray] = []
    c2_folds: list[np.ndarray] = []
    labels_by_fold: list[np.ndarray] = []
    timestamps_by_fold: list[np.ndarray] = []
    m0_folds: list[dict[str, Any]] = []
    m1_folds: list[dict[str, Any]] = []
    m2_folds: list[dict[str, Any]] = []

    for outer, t2_fold, t1_fold in zip(
        dd.OUTER_FOLDS,
        t2_result.s1_folds,
        t1_reproduction,
        strict=True,
    ):
        t2_day = t2_per_day[outer.validation_day]
        candidate_day = candidate_per_day[outer.validation_day]
        if not np.array_equal(t2_day.timestamps_us, t2_fold.timestamps_us):
            raise P5Error("p4_baseline_timestamp_alignment_mismatch")
        p_long = t1_fold.model.predict_proba(
            t1_fold.scaler.transform(np.asarray(t2_day.s1_values, dtype=np.float64))
        )[:, 1]
        y3 = p4.three_class_labels(candidate_day, t2_day)
        train_prev3 = _three_class_training_prevalence(
            candidate_per_day, t2_per_day, outer.train_days
        )
        train_p_long = p4.directional_training_prevalence(
            candidate_per_day, outer.train_days
        )
        c0, c1, c2 = p4.composition_baselines(
            y_validation=y3,
            training_class_prevalence=train_prev3,
            p_touch=t2_fold.p_touch,
            training_p_long_given_touch=train_p_long,
            p_long_given_touch=p_long,
        )
        c0_folds.append(c0)
        c1_folds.append(c1)
        c2_folds.append(c2)
        labels_by_fold.append(y3)
        timestamps_by_fold.append(np.asarray(t2_day.timestamps_us, dtype=np.int64))
        m0_folds.append(joint_metrics(y3, c0))
        m1_folds.append(joint_metrics(y3, c1))
        m2_folds.append(joint_metrics(y3, c2))

    y_pooled = np.concatenate(labels_by_fold)
    c0_pooled = np.concatenate(c0_folds)
    c1_pooled = np.concatenate(c1_folds)
    c2_pooled = np.concatenate(c2_folds)

    return BaselineBundle(
        tuple(c0_folds),
        tuple(c1_folds),
        tuple(c2_folds),
        tuple(labels_by_fold),
        tuple(timestamps_by_fold),
        tuple(m0_folds),
        tuple(m1_folds),
        tuple(m2_folds),
        joint_metrics(y_pooled, c0_pooled),
        joint_metrics(y_pooled, c1_pooled),
        joint_metrics(y_pooled, c2_pooled),
    )


def _assert_close_dict(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    keys: Sequence[str],
    atol: float = 1e-12,
) -> None:
    for key in keys:
        av = float(actual[key])
        ev = float(expected[key])
        if not math.isclose(av, ev, rel_tol=0.0, abs_tol=atol):
            raise P5Error("p4_baseline_metric_reproduction_mismatch", key)


def reconcile_reconstructed_p4_baselines(
    baselines: BaselineBundle,
    p4_payload: Mapping[str, Any],
) -> None:
    validate_p4_artifact_identity(p4_payload)
    composition = p4_payload.get("composition")
    if not isinstance(composition, Mapping):
        raise P5Error("p4_composition_payload_missing")
    if composition.get("status") != "FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE":
        raise P5Error("p4_composition_status_mismatch")

    metric_keys = (
        "multiclass_log_loss",
        "multiclass_brier",
        "macro_ovr_average_precision",
        "macro_ovr_roc_auc",
        "argmax_balanced_accuracy",
        "argmax_macro_f1",
    )
    _assert_close_dict(baselines.pooled_c0, composition["pooled_c0"], keys=metric_keys)
    _assert_close_dict(baselines.pooled_c1, composition["pooled_c1"], keys=metric_keys)
    _assert_close_dict(baselines.pooled_c2, composition["pooled_c2"], keys=metric_keys)

    frozen_folds = composition.get("folds")
    if not isinstance(frozen_folds, list) or len(frozen_folds) != 4:
        raise P5Error("p4_composition_fold_payload_mismatch")
    for i, frozen in enumerate(frozen_folds):
        if int(frozen.get("fold_id")) != i + 1:
            raise P5Error("p4_composition_fold_id_mismatch")
        _assert_close_dict(
            baselines.metrics_c0_folds[i],
            frozen["metrics_c0"],
            keys=metric_keys,
        )
        _assert_close_dict(
            baselines.metrics_c1_folds[i],
            frozen["metrics_c1"],
            keys=metric_keys,
        )
        _assert_close_dict(
            baselines.metrics_c2_folds[i],
            frozen["metrics_c2"],
            keys=metric_keys,
        )

    pooled_labels = np.concatenate(baselines.labels_by_fold)
    pooled_ts = np.concatenate(baselines.timestamps_by_fold)
    if len(pooled_labels) != EXPECTED_POOLED_SUPPORT:
        raise P5Error("p4_baseline_support_count_mismatch")
    counts = {
        "NONE": int(np.count_nonzero(pooled_labels == NONE)),
        "SHORT_FIRST": int(np.count_nonzero(pooled_labels == SHORT_FIRST)),
        "LONG_FIRST": int(np.count_nonzero(pooled_labels == LONG_FIRST)),
    }
    if counts != EXPECTED_POOLED_COUNTS:
        raise P5Error("p4_baseline_class_count_mismatch")
    if tuple(len(x) for x in baselines.labels_by_fold) != EXPECTED_FOLD_SUPPORT:
        raise P5Error("p4_baseline_fold_support_mismatch")
    if len(pooled_ts) and bool(np.any(np.diff(pooled_ts) <= 0)):
        raise P5Error("p4_baseline_pooled_timestamps_not_chronological")


def comparison_summary(
    *,
    joint: JointModelResult,
    baselines: BaselineBundle,
) -> dict[str, Any]:
    if len(joint.folds) != 4:
        raise P5Error("joint_outer_fold_count_mismatch")
    j1 = joint.pooled
    c1 = baselines.pooled_c1

    fold_ll_improvement = tuple(
        float(
            baselines.metrics_c1_folds[i]["multiclass_log_loss"]
            - joint.folds[i].metrics["multiclass_log_loss"]
        )
        for i in range(4)
    )

    loo: list[float] = []
    for omitted in range(4):
        labels = np.concatenate([
            baselines.labels_by_fold[i] for i in range(4) if i != omitted
        ])
        c1p = np.concatenate([
            baselines.c1_folds[i] for i in range(4) if i != omitted
        ])
        j1p = np.concatenate([
            joint.folds[i].probabilities for i in range(4) if i != omitted
        ])
        loo.append(
            float(
                joint_metrics(labels, c1p)["multiclass_log_loss"]
                - joint_metrics(labels, j1p)["multiclass_log_loss"]
            )
        )

    short_delta = float(
        j1["per_class_average_precision"]["SHORT_FIRST"]
        - c1["per_class_average_precision"]["SHORT_FIRST"]
    )
    long_delta = float(
        j1["per_class_average_precision"]["LONG_FIRST"]
        - c1["per_class_average_precision"]["LONG_FIRST"]
    )
    mean_directional_delta = float((short_delta + long_delta) / 2.0)

    gates = {
        "pooled_log_loss_better_than_c1": (
            float(j1["multiclass_log_loss"]) < float(c1["multiclass_log_loss"])
        ),
        "pooled_brier_better_than_c1": (
            float(j1["multiclass_brier"]) < float(c1["multiclass_brier"])
        ),
        "pooled_macro_ap_better_than_c1": (
            float(j1["macro_ovr_average_precision"])
            > float(c1["macro_ovr_average_precision"])
        ),
        "at_least_3_of_4_fold_log_loss_improve": (
            sum(value > 0 for value in fold_ll_improvement) >= 3
        ),
        "leave_one_fold_out_log_loss_improvement_positive": all(
            value > 0 for value in loo
        ),
        "at_least_one_directional_ap_improves": (
            short_delta > 0 or long_delta > 0
        ),
        "mean_directional_ap_delta_positive": mean_directional_delta > 0,
    }

    return {
        "pooled_log_loss_improvement_vs_c1": float(
            c1["multiclass_log_loss"] - j1["multiclass_log_loss"]
        ),
        "pooled_brier_improvement_vs_c1": float(
            c1["multiclass_brier"] - j1["multiclass_brier"]
        ),
        "pooled_macro_ap_delta_vs_c1": float(
            j1["macro_ovr_average_precision"]
            - c1["macro_ovr_average_precision"]
        ),
        "short_first_ap_delta_vs_c1": short_delta,
        "long_first_ap_delta_vs_c1": long_delta,
        "mean_directional_ap_delta_vs_c1": mean_directional_delta,
        "fold_log_loss_improvement_vs_c1": list(fold_ll_improvement),
        "leave_one_fold_out_log_loss_improvement_vs_c1": loo,
        "precheck_gates": gates,
        "precheck_pass": all(gates.values()),
    }


def eligible_shared_shifts(group_sizes: Sequence[int]) -> tuple[int, ...]:
    sizes = tuple(int(value) for value in group_sizes)
    if not sizes or any(value <= 0 for value in sizes):
        raise P5Error("invalid_null_group_sizes")
    return tuple(
        k
        for k in range(1, min(sizes))
        if all(min(k, n - k) >= 10 for n in sizes)
    )


def temporal_null(
    *,
    joint: JointModelResult,
    baselines: BaselineBundle,
    comparison: Mapping[str, Any],
) -> JointTemporalNull:
    if len(joint.folds) != 4 or len(baselines.labels_by_fold) != 4:
        raise P5Error("null_outer_fold_count_mismatch")
    shifts = eligible_shared_shifts(
        [len(values) for values in baselines.labels_by_fold]
    )
    if len(shifts) < 20:
        raise P5Error("insufficient_temporal_null_shifts")

    observed_ll = float(comparison["pooled_log_loss_improvement_vs_c1"])
    observed_ap = float(comparison["pooled_macro_ap_delta_vs_c1"])

    c1_pooled = np.concatenate(baselines.c1_folds)
    j1_pooled = np.concatenate([fold.probabilities for fold in joint.folds])

    null_ll: list[float] = []
    null_ap: list[float] = []
    for k in shifts:
        shifted = np.concatenate([
            np.roll(labels, k)
            for labels in baselines.labels_by_fold
        ])
        c1_metrics = joint_metrics(shifted, c1_pooled)
        j1_metrics = joint_metrics(shifted, j1_pooled)
        null_ll.append(float(
            c1_metrics["multiclass_log_loss"]
            - j1_metrics["multiclass_log_loss"]
        ))
        null_ap.append(float(
            j1_metrics["macro_ovr_average_precision"]
            - c1_metrics["macro_ovr_average_precision"]
        ))

    ll_q95 = float(np.quantile(np.asarray(null_ll), 0.95, method="higher"))
    ap_q95 = float(np.quantile(np.asarray(null_ap), 0.95, method="higher"))
    empirical_p = float(
        (1 + sum(value >= observed_ll for value in null_ll))
        / (1 + len(null_ll))
    )
    return JointTemporalNull(
        shifts,
        tuple(null_ll),
        tuple(null_ap),
        ll_q95,
        ap_q95,
        empirical_p,
        observed_ll,
        observed_ap,
        bool(observed_ll > ll_q95 and empirical_p <= 0.05),
    )


def final_gates(
    *,
    comparison: Mapping[str, Any],
    null: JointTemporalNull | None,
    baseline_reproduction_pass: bool,
) -> dict[str, bool]:
    gates = dict(comparison["precheck_gates"])
    gates["baseline_reproduction_pass"] = bool(baseline_reproduction_pass)
    gates["temporal_null_run"] = null is not None
    gates["temporal_null_log_loss_improvement_gt_q95"] = bool(
        null is not None
        and null.observed_log_loss_improvement > null.log_loss_improvement_q95
    )
    gates["temporal_null_p_le_005"] = bool(
        null is not None and null.empirical_p <= 0.05
    )
    return gates


def runtime_provenance(*, model_fit_run: bool, p5_run: bool) -> dict[str, Any]:
    if type(model_fit_run) is not bool or type(p5_run) is not bool:
        raise P5Error("runtime_flags_must_be_builtin_bool")
    if p5_run and not model_fit_run:
        raise P5Error("p5_requires_model_fit")
    return {
        "jan_jul_analytically_opened": True,
        "authorized_development_data": {
            "scope": "BTCUSDT consumed Jan-Jul development days only",
            "analytically_loaded": True,
        },
        "forward_data_guards": dict(FORWARD_GUARDS),
        "model_fit_run": model_fit_run,
        "p5_run": p5_run,
        "threshold_optimization_run": False,
        "pnl_backtest_run": False,
        "opportunity_gate_run": False,
        "m2_or_deep_model_run": False,
    }


def validate_runtime_provenance(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "jan_jul_analytically_opened",
        "authorized_development_data",
        "forward_data_guards",
        "model_fit_run",
        "p5_run",
        "threshold_optimization_run",
        "pnl_backtest_run",
        "opportunity_gate_run",
        "m2_or_deep_model_run",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise P5Error("runtime_provenance_schema_mismatch")
    if value["jan_jul_analytically_opened"] is not True:
        raise P5Error("jan_jul_runtime_state_invalid")
    development = value["authorized_development_data"]
    if (
        not isinstance(development, Mapping)
        or development.get("scope")
        != "BTCUSDT consumed Jan-Jul development days only"
        or development.get("analytically_loaded") is not True
    ):
        raise P5Error("authorized_development_runtime_mismatch")
    guards = value["forward_data_guards"]
    if (
        not isinstance(guards, Mapping)
        or set(guards) != set(FORWARD_GUARDS)
        or any(type(item) is not bool for item in guards.values())
        or any(guards.values())
    ):
        raise P5Error("forward_data_guard_violation")
    for field in (
        "model_fit_run",
        "p5_run",
        "threshold_optimization_run",
        "pnl_backtest_run",
        "opportunity_gate_run",
        "m2_or_deep_model_run",
    ):
        if type(value[field]) is not bool:
            raise P5Error("runtime_flags_must_be_builtin_bool")
    if value["p5_run"] and not value["model_fit_run"]:
        raise P5Error("p5_requires_model_fit")
    if (
        value["threshold_optimization_run"]
        or value["pnl_backtest_run"]
        or value["opportunity_gate_run"]
        or value["m2_or_deep_model_run"]
    ):
        raise P5Error("prohibited_runtime_activity")
    return dict(value)


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    def normalize(value: Any) -> Any:
        if value is None or type(value) in (str, bool, int):
            return value
        if type(value) is float:
            if not math.isfinite(value):
                raise P5Error("non_finite_json_value")
            return value
        if isinstance(value, np.generic):
            return normalize(value.item())
        if isinstance(value, np.ndarray):
            return [normalize(item) for item in value.tolist()]
        if isinstance(value, Mapping):
            if not all(isinstance(key, str) for key in value):
                raise P5Error("json_mapping_key_not_string")
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, date):
            return value.isoformat()
        raise P5Error("unsupported_json_value", type(value).__name__)

    return (
        json.dumps(
            normalize(dict(payload)),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_result_once(
    output_directory: Path,
    payload: Mapping[str, Any],
    *,
    require_canonical_output: bool = True,
) -> ArtifactWriteResult:
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise P5Error("output_directory_already_exists")
    if not require_canonical_output and output == REAL_OUTPUT_DIRECTORY:
        raise P5Error("canonical_output_requires_real_mode")
    if require_canonical_output and output != REAL_OUTPUT_DIRECTORY:
        raise P5Error("noncanonical_output_directory")

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
        try:
            if part.exists():
                part.unlink()
            if output.exists() and not any(output.iterdir()):
                output.rmdir()
        except OSError as cleanup_exc:
            raise P5Error("artifact_cleanup_failed", str(cleanup_exc)) from cleanup_exc
        if isinstance(exc, P5Error):
            raise
        raise P5Error("artifact_write_failed", str(exc)) from exc

    return ArtifactWriteResult(
        output,
        final,
        hashlib.sha256(content).hexdigest(),
        len(content),
    )


def _fold_public(fold: JointFoldResult) -> dict[str, Any]:
    return {
        "fold_id": fold.fold_id,
        "selected_C": fold.selected_c,
        "support": fold.support,
        "class_counts": dict(fold.class_counts),
        "metrics": fold.metrics,
        "prediction_sha256": fold.prediction_sha256,
        "support_sha256": fold.support_sha256,
        "label_sha256": fold.label_sha256,
        "inner_c_ledger": [dict(item) for item in fold.inner_c_ledger],
    }


def run_p5(
    *,
    workspace: Path,
    output_directory: Path,
    execution_commit: str,
    require_canonical_output: bool = True,
    dependency_verifier: Any = verify_frozen_dependencies,
    p4_loader: Any = None,
    p3_loader: Any = None,
    p2c_loader: Any = None,
    manifest_verifier: Any = dd.verify_input_manifest,
    analytical_day_loader: Any = dd.load_authorized_days,
) -> ArtifactWriteResult:
    """Run the separately-authorized real P5 campaign."""

    supplied_p4_loader = p4_loader
    supplied_p3_loader = p3_loader
    supplied_p2c_loader = p2c_loader

    if p4_loader is None:
        p4_loader = lambda: load_verified_json_artifact(
            P4_ARTIFACT_PATH, P4_ARTIFACT_SHA256
        )
    if p3_loader is None:
        p3_loader = lambda: load_verified_json_artifact(
            P3_ARTIFACT_PATH, P3_ARTIFACT_SHA256
        )
    if p2c_loader is None:
        p2c_loader = lambda: load_verified_json_artifact(
            P2C_ARTIFACT_PATH, P2C_ARTIFACT_SHA256
        )

    output = Path(output_directory)
    if require_canonical_output:
        if output != REAL_OUTPUT_DIRECTORY:
            raise P5Error("noncanonical_output_directory")
        for name, supplied in (
            ("p4_loader", supplied_p4_loader),
            ("p3_loader", supplied_p3_loader),
            ("p2c_loader", supplied_p2c_loader),
        ):
            if supplied is not None:
                raise P5Error("canonical_dependency_override_forbidden", name)
        if dependency_verifier is not verify_frozen_dependencies:
            raise P5Error(
                "canonical_dependency_override_forbidden", "dependency_verifier"
            )
        if manifest_verifier is not dd.verify_input_manifest:
            raise P5Error(
                "canonical_dependency_override_forbidden", "manifest_verifier"
            )
        if analytical_day_loader is not dd.load_authorized_days:
            raise P5Error(
                "canonical_dependency_override_forbidden", "analytical_day_loader"
            )
    elif output == REAL_OUTPUT_DIRECTORY:
        raise P5Error("canonical_output_requires_real_mode")

    if output.exists() or output.is_symlink():
        raise P5Error("output_directory_already_exists")

    execution_sha = _validate_execution_commit(execution_commit)
    dependency_hashes = dict(dependency_verifier(Path(workspace)))
    p4_payload = dict(p4_loader())
    p3_payload = dict(p3_loader())
    p2c_payload = dict(p2c_loader())
    validate_p4_artifact_identity(p4_payload)
    p4.validate_p3_selected_survivor(p3_payload)

    manifest = tuple(manifest_verifier())
    loaded_days = tuple(analytical_day_loader())
    if tuple(day.day for day in loaded_days) != dd.HISTORICAL_DAYS:
        raise P5Error("loaded_day_calendar_mismatch")

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
        raise P5Error("selected_candidate_day_order_mismatch")
    try:
        p4.reconcile_selected_candidate_with_p2c(candidate_per_day, p2c_payload)
    except p4.P4Error as exc:
        raise P5Error(exc.reason, str(exc)) from exc

    t2_per_day = {
        day: p4.build_t2_day(candidate_per_day[day])
        for day in dd.HISTORICAL_DAYS
    }
    joint_per_day = {
        day: build_joint_day(candidate_per_day[day])
        for day in dd.HISTORICAL_DAYS
    }

    baselines = reconstruct_p4_baselines(
        candidate_per_day=candidate_per_day,
        t2_per_day=t2_per_day,
    )
    reconcile_reconstructed_p4_baselines(baselines, p4_payload)

    joint = fit_joint_model(joint_per_day)
    comparison = comparison_summary(joint=joint, baselines=baselines)

    null: JointTemporalNull | None = None
    if comparison["precheck_pass"]:
        null = temporal_null(
            joint=joint,
            baselines=baselines,
            comparison=comparison,
        )

    gates = final_gates(
        comparison=comparison,
        null=null,
        baseline_reproduction_pass=True,
    )
    eligible = all(gates.values())
    if eligible:
        status = "ELIGIBLE_FOR_LATER_POLICY_DESIGN"
    elif comparison["precheck_pass"]:
        status = "FAIL_DIRECT_JOINT_THREECLASS_TEMPORAL_NULL"
    else:
        status = "FAIL_DIRECT_JOINT_THREECLASS_NO_INCREMENTAL_VALUE"

    runtime = runtime_provenance(model_fit_run=True, p5_run=True)
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
            "target": {"target_id": "A", "horizon_seconds": 120, "barrier_bps": 16},
            "window_seconds": 32,
            "block": "PRICE",
            "representation": "S1",
        },
        "dependency_sha256": dict(sorted(dependency_hashes.items())),
        "frozen_artifacts": {
            "p2c": {"path": str(P2C_ARTIFACT_PATH), "sha256": P2C_ARTIFACT_SHA256},
            "p3": {"path": str(P3_ARTIFACT_PATH), "sha256": P3_ARTIFACT_SHA256},
            "p4": {"path": str(P4_ARTIFACT_PATH), "sha256": P4_ARTIFACT_SHA256},
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
        "joint_support": [
            {
                "date": day.isoformat(),
                "support": int(len(joint_per_day[day].labels)),
                "class_counts": dict(joint_per_day[day].class_counts),
                "support_sha256": joint_per_day[day].support_sha256,
                "label_sha256": joint_per_day[day].label_sha256,
            }
            for day in dd.HISTORICAL_DAYS
        ],
        "p4_baseline_reproduction": {
            "pass": True,
            "pooled_c0": baselines.pooled_c0,
            "pooled_c1": baselines.pooled_c1,
            "pooled_c2": baselines.pooled_c2,
        },
        "j1": {
            "folds": [_fold_public(fold) for fold in joint.folds],
            "pooled": joint.pooled,
            "pooled_support_sha256": joint.pooled_support_sha256,
            "pooled_label_sha256": joint.pooled_label_sha256,
        },
        "comparison_vs_c1": comparison,
        "temporal_null": (
            {
                "eligible_shifts": list(null.eligible_shifts),
                "null_log_loss_improvement": list(null.null_log_loss_improvement),
                "null_macro_ap_delta": list(null.null_macro_ap_delta),
                "log_loss_improvement_q95": null.log_loss_improvement_q95,
                "macro_ap_delta_q95": null.macro_ap_delta_q95,
                "empirical_p": null.empirical_p,
                "observed_log_loss_improvement": null.observed_log_loss_improvement,
                "observed_macro_ap_delta": null.observed_macro_ap_delta,
                "pass_gate": null.pass_gate,
            }
            if null is not None
            else {"status": "TEMPORAL_NULL_NOT_RUN_PRECHECK_FAILED"}
        ),
        "promotion_gates": gates,
        "eligible_for_later_policy_design": eligible,
        "runtime_provenance": runtime,
        "prohibited_activity": {
            "threshold_optimization": False,
            "pnl": False,
            "economics": False,
            "opportunity_gate": False,
            "forward_data": False,
            "class_weighting_or_resampling": False,
            "m2_or_deep_model": False,
        },
    }
    return write_result_once(
        output,
        payload,
        require_canonical_output=require_canonical_output,
    )


__all__ = [
    "ARTIFACT_FILENAME",
    "CLASS_NAMES",
    "CLASS_ORDER",
    "C_GRID",
    "DESIGN_VERSION",
    "EXPECTED_FOLD_SUPPORT",
    "EXPECTED_POOLED_COUNTS",
    "EXPECTED_POOLED_SUPPORT",
    "EXPERIMENT_ID",
    "LONG_FIRST",
    "NONE",
    "P4_ARTIFACT_SHA256",
    "P5Error",
    "REAL_OUTPUT_DIRECTORY",
    "SELECTED_BLOCK",
    "SELECTED_KEY",
    "SELECTED_TARGET",
    "SELECTED_WINDOW_SECONDS",
    "SHORT_FIRST",
    "ArtifactWriteResult",
    "BaselineBundle",
    "JointDayDataset",
    "JointFoldResult",
    "JointModelResult",
    "JointTemporalNull",
    "build_joint_day",
    "canonical_json_bytes",
    "comparison_summary",
    "eligible_shared_shifts",
    "final_gates",
    "fit_joint_fold",
    "fit_joint_model",
    "joint_metrics",
    "load_verified_json_artifact",
    "reconcile_reconstructed_p4_baselines",
    "reconstruct_p4_baselines",
    "run_p5",
    "runtime_provenance",
    "select_c",
    "temporal_null",
    "validate_p4_artifact_identity",
    "validate_runtime_provenance",
    "verify_frozen_dependencies",
    "write_result_once",
]

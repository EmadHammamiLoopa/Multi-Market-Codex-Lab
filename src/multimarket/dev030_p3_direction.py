"""DEV030-P3 bounded Campaign-1 direction modeling.

This module implements the frozen DEV030-P3 design for the oracle-touch T1
DIRECTION_GIVEN_TOUCH diagnostic.  It is intentionally narrow:

* BTCUSDT consumed Jan-Jul development days only;
* exact 64 frozen target/window/block candidates;
* matched S0 snapshot versus S1 sequence-summary representations;
* M0 controls plus train-only StandardScaler + L2 logistic regression M1;
* four frozen expanding chronological outer folds with one-day inner selection;
* deterministic metrics, prediction hashes, temporal-label nulls, gates, and
  survivor ranking;
* no PnL, no execution policy, no opportunity gating, and no forward-data use.

The real Campaign-1 run remains separately gated.  Synthetic tests may inject
in-memory candidate datasets and must not touch the authorized market files.
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
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

from . import dev030_direction_dataset as dd
from . import dev030_direction_materialize as dm


EXPERIMENT_ID = "DEV030-P3"
DESIGN_VERSION = "campaign1-v1"
STATUS_COMPLETE = "CAMPAIGN1_COMPLETE"
STATUS_NO_SURVIVOR = "CAMPAIGN1_NO_PRIMARY_SURVIVOR"
STATUS_SURVIVOR = "CAMPAIGN1_PRIMARY_SURVIVOR"

P2C_ARTIFACT_PATH = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p2c_direction_materialization_v1/"
    "DIRECTION_DATASET_MATERIALIZATION.json"
)
P2C_ARTIFACT_SHA256 = (
    "a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0"
)
P2B_SOURCE_REL = "src/multimarket/dev030_direction_dataset.py"
P2B_SOURCE_SHA256 = (
    "54e7315a12cac10413ac2017849466eb3d225282e3dcf48484615409680348c9"
)
SEQUENCE_SOURCE_REL = "src/multimarket/dev030_sequence_features.py"
SEQUENCE_SOURCE_SHA256 = dd.SEQUENCE_FEATURE_SOURCE_SHA256
FIRST_PASSAGE_SOURCE_REL = "src/multimarket/dev030_first_passage.py"
FIRST_PASSAGE_SOURCE_SHA256 = dd.FIRST_PASSAGE_SOURCE_SHA256

REAL_OUTPUT_DIRECTORY = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1"
)
ARTIFACT_FILENAME = "DEV030_P3_CAMPAIGN1_RESULT.json"

C_GRID = (0.01, 0.1, 1.0, 10.0)
THRESHOLD = 0.5
RANDOM_STATE = 20260825
PROMOTABLE_TARGET_IDS = ("A", "B")
CONTROL_TARGET_IDS = ("C", "D")
PREDICTION_HASH_DOMAIN = b"DEV030-P3-OOF-PREDICTION-V1\x00"

FORWARD_GUARDS = {
    "aug30_analytically_opened": False,
    "sep01_or_later_analytically_opened": False,
    "archive_bucket_opened": False,
    "abundant_love_opened": False,
}


class Campaign1Error(RuntimeError):
    """Frozen design, data, model, metric, or output protocol violation."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


@dataclass(frozen=True)
class CandidateSpec:
    target_id: str
    horizon_seconds: int
    barrier_bps: int
    window_seconds: int
    block: str


@dataclass(frozen=True)
class RepresentationFoldResult:
    fold_id: int
    selected_c: float
    support: int
    metrics: dict[str, Any]
    prediction_sha256: str
    y_true: np.ndarray
    y_pred: np.ndarray
    p_long: np.ndarray
    timestamps_us: np.ndarray


@dataclass(frozen=True)
class CandidateModelResult:
    spec: CandidateSpec
    feature_count_s0: int
    feature_count_s1: int
    s0_folds: tuple[RepresentationFoldResult, ...]
    s1_folds: tuple[RepresentationFoldResult, ...]
    s0_pooled: dict[str, Any]
    s1_pooled: dict[str, Any]
    fold_delta_ba: tuple[float, ...]
    pooled_delta_ba: float
    pooled_delta_macro_f1: float
    leave_one_fold_out_delta_ba: tuple[float, ...]
    precheck_pass: bool
    precheck_gates: dict[str, bool]


@dataclass(frozen=True)
class TemporalNullResult:
    eligible_shifts: tuple[int, ...]
    null_balanced_accuracy: tuple[float, ...]
    null_q95: float
    empirical_p: float
    observed_balanced_accuracy: float
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


def frozen_candidate_specs() -> tuple[CandidateSpec, ...]:
    return tuple(
        CandidateSpec(
            target.target_id,
            int(target.horizon_seconds),
            int(target.barrier_bps),
            int(window),
            str(block),
        )
        for target in dd.FROZEN_TARGETS
        for window in dd.FROZEN_WINDOWS_SECONDS
        for block in dd.FROZEN_BLOCKS
    )


def _candidate_key(spec: CandidateSpec) -> dd.CandidateKey:
    for target in dd.FROZEN_TARGETS:
        if (
            target.target_id == spec.target_id
            and int(target.horizon_seconds) == spec.horizon_seconds
            and int(target.barrier_bps) == spec.barrier_bps
        ):
            return dd.CandidateKey(target, spec.window_seconds, spec.block)
    raise Campaign1Error("candidate_spec_not_frozen", repr(spec))


def runtime_provenance(*, model_fit_run: bool, campaign_1_run: bool) -> dict[str, Any]:
    if type(model_fit_run) is not bool or type(campaign_1_run) is not bool:
        raise Campaign1Error("runtime_flags_must_be_builtin_bool")
    if campaign_1_run and not model_fit_run:
        raise Campaign1Error("campaign1_requires_model_fit")
    return {
        "jan_jul_analytically_opened": True,
        "authorized_development_data": {
            "scope": "BTCUSDT consumed Jan-Jul development days only",
            "analytically_loaded": True,
        },
        "forward_data_guards": dict(FORWARD_GUARDS),
        "model_fit_run": model_fit_run,
        "campaign_1_run": campaign_1_run,
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
        raise Campaign1Error("runtime_provenance_schema_mismatch")
    if value["jan_jul_analytically_opened"] is not True:
        raise Campaign1Error("jan_jul_runtime_state_invalid")
    development = value["authorized_development_data"]
    if (
        not isinstance(development, Mapping)
        or set(development) != {"scope", "analytically_loaded"}
        or development["scope"] != "BTCUSDT consumed Jan-Jul development days only"
        or development["analytically_loaded"] is not True
    ):
        raise Campaign1Error("authorized_development_runtime_mismatch")
    guards = value["forward_data_guards"]
    if (
        not isinstance(guards, Mapping)
        or set(guards) != set(FORWARD_GUARDS)
        or any(type(item) is not bool for item in guards.values())
        or any(guards.values())
    ):
        raise Campaign1Error("forward_data_guard_violation")
    for field in ("model_fit_run", "campaign_1_run", "pnl_backtest_run"):
        if type(value[field]) is not bool:
            raise Campaign1Error("runtime_flags_must_be_builtin_bool")
    if value["campaign_1_run"] and not value["model_fit_run"]:
        raise Campaign1Error("campaign1_requires_model_fit")
    if value["pnl_backtest_run"] is not False:
        raise Campaign1Error("pnl_forbidden")
    return dm.normalize_json_safe(dict(value))


def verify_frozen_dependencies(
    repository_root: Path,
    *,
    hash_file: Callable[[Path], str] = _sha256_file,
) -> dict[str, str]:
    root = Path(repository_root).resolve()
    expected = (
        (P2B_SOURCE_REL, P2B_SOURCE_SHA256, "p2b_source_sha256_mismatch"),
        (SEQUENCE_SOURCE_REL, SEQUENCE_SOURCE_SHA256, "sequence_source_sha256_mismatch"),
        (FIRST_PASSAGE_SOURCE_REL, FIRST_PASSAGE_SOURCE_SHA256, "first_passage_source_sha256_mismatch"),
    )
    result: dict[str, str] = {}
    for rel, expected_sha, reason in expected:
        path = root / rel
        if not path.is_file():
            raise Campaign1Error("frozen_source_missing", rel)
        actual = str(hash_file(path))
        if actual != expected_sha:
            raise Campaign1Error(reason, rel)
        result[rel] = actual
    return result


def load_frozen_p2c_artifact(
    path: Path = P2C_ARTIFACT_PATH,
    *,
    hash_file: Callable[[Path], str] = _sha256_file,
) -> dict[str, Any]:
    artifact = Path(path)
    if not artifact.is_file():
        raise Campaign1Error("p2c_artifact_missing", str(artifact))
    if str(hash_file(artifact)) != P2C_ARTIFACT_SHA256:
        raise Campaign1Error("p2c_artifact_sha256_mismatch")
    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Campaign1Error("p2c_artifact_read_failed", str(exc)) from exc
    if not isinstance(payload, dict):
        raise Campaign1Error("p2c_artifact_not_object")
    return payload


def _public_spec(spec: CandidateSpec) -> dict[str, Any]:
    return {
        "target": {
            "target_id": spec.target_id,
            "horizon_seconds": spec.horizon_seconds,
            "barrier_bps": spec.barrier_bps,
        },
        "window_seconds": spec.window_seconds,
        "block": spec.block,
    }


def reconcile_candidate_payload(
    reconstructed_payload: Mapping[str, Any],
    frozen_payload: Mapping[str, Any],
) -> None:
    """Compare all frozen candidate/day/fold support contracts before fitting."""

    required_top = ("authorized_input_manifest", "configuration", "per_candidate")
    if any(key not in reconstructed_payload or key not in frozen_payload for key in required_top):
        raise Campaign1Error("p2c_reconciliation_schema_missing")

    if reconstructed_payload["authorized_input_manifest"] != frozen_payload["authorized_input_manifest"]:
        raise Campaign1Error("input_manifest_reconciliation_failed")

    reconstructed = reconstructed_payload["per_candidate"]
    frozen = frozen_payload["per_candidate"]
    if not isinstance(reconstructed, list) or not isinstance(frozen, list):
        raise Campaign1Error("candidate_payload_not_list")
    if len(reconstructed) != 64 or len(frozen) != 64:
        raise Campaign1Error("candidate_count_reconciliation_failed")

    frozen_specs = [_public_spec(spec) for spec in frozen_candidate_specs()]
    for index, (left, right, expected_spec) in enumerate(zip(reconstructed, frozen, frozen_specs, strict=True)):
        identity_left = {
            "target": left.get("target"),
            "window_seconds": left.get("window_seconds"),
            "block": left.get("block"),
        }
        identity_right = {
            "target": right.get("target"),
            "window_seconds": right.get("window_seconds"),
            "block": right.get("block"),
        }
        if identity_left != expected_spec or identity_right != expected_spec:
            raise Campaign1Error("candidate_order_reconciliation_failed", str(index))

        left_days = left.get("per_day")
        right_days = right.get("per_day")
        if not isinstance(left_days, list) or not isinstance(right_days, list) or len(left_days) != 7 or len(right_days) != 7:
            raise Campaign1Error("candidate_day_reconciliation_failed", str(index))
        for lday, rday in zip(left_days, right_days, strict=True):
            fields = (
                "date",
                "decision_count",
                "t1_common_support_count",
                "t1_long_common_count",
                "t1_short_common_count",
                "support_sha256",
            )
            if any(lday.get(field) != rday.get(field) for field in fields):
                raise Campaign1Error("candidate_day_reconciliation_failed", f"{index}:{lday.get('date')}")

        left_folds = left.get("folds")
        right_folds = right.get("folds")
        if not isinstance(left_folds, list) or not isinstance(right_folds, list) or len(left_folds) != 4 or len(right_folds) != 4:
            raise Campaign1Error("fold_reconciliation_failed", str(index))
        for lfold, rfold in zip(left_folds, right_folds, strict=True):
            fields = (
                "fold_id",
                "train_days",
                "validation_day",
                "train_t1_count",
                "validation_t1_count",
                "train_class_counts",
                "validation_class_counts",
                "support_sha256",
            )
            if any(lfold.get(field) != rfold.get(field) for field in fields):
                raise Campaign1Error("fold_reconciliation_failed", f"{index}:{lfold.get('fold_id')}")


def _require_binary_labels(y: Any, *, reason: str) -> np.ndarray:
    raw = np.asarray(y)
    if raw.ndim != 1 or raw.dtype.kind not in "iub":
        raise Campaign1Error(reason)
    labels = raw.astype(np.int8, copy=False)
    if len(labels) == 0 or not bool(np.all(np.isin(labels, (0, 1)))):
        raise Campaign1Error(reason)
    return labels


def metric_summary(y_true: Any, y_pred: Any, p_long: Any | None = None) -> dict[str, Any]:
    truth = _require_binary_labels(y_true, reason="invalid_metric_labels")
    pred = _require_binary_labels(y_pred, reason="invalid_metric_predictions")
    if len(truth) != len(pred):
        raise Campaign1Error("metric_length_mismatch")

    cm = confusion_matrix(truth, pred, labels=[0, 1])
    precision, recall, f1, support = precision_recall_fscore_support(
        truth, pred, labels=[0, 1], zero_division=0
    )
    result: dict[str, Any] = {
        "support": int(len(truth)),
        "long_count": int(np.count_nonzero(truth == 1)),
        "short_count": int(np.count_nonzero(truth == 0)),
        "predicted_long_count": int(np.count_nonzero(pred == 1)),
        "predicted_short_count": int(np.count_nonzero(pred == 0)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, pred)),
        "macro_f1": float(f1_score(truth, pred, average="macro", zero_division=0)),
        "mcc": float(matthews_corrcoef(truth, pred)),
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
        "confusion_matrix_short_long": cm.astype(int).tolist(),
    }
    if p_long is not None:
        scores = np.asarray(p_long, dtype=np.float64)
        if scores.ndim != 1 or len(scores) != len(truth) or not bool(np.all(np.isfinite(scores))):
            raise Campaign1Error("invalid_probability_vector")
        if not bool(np.all((scores >= 0.0) & (scores <= 1.0))):
            raise Campaign1Error("invalid_probability_vector")
        result["roc_auc_diagnostic"] = (
            float(roc_auc_score(truth, scores)) if len(np.unique(truth)) == 2 else None
        )
    return result


def _new_logistic(c_value: float) -> LogisticRegression:
    if c_value not in C_GRID:
        raise Campaign1Error("c_not_in_frozen_grid", str(c_value))
    return LogisticRegression(
        C=float(c_value),
        solver="lbfgs",
        l1_ratio=0.0,
        class_weight=None,
        max_iter=1000,
        fit_intercept=True,
        random_state=RANDOM_STATE,
    )


def select_c_chronologically(
    x_fit: Any,
    y_fit: Any,
    x_inner_validation: Any,
    y_inner_validation: Any,
) -> tuple[float, tuple[dict[str, Any], ...]]:
    x_train = np.asarray(x_fit, dtype=np.float64)
    x_val = np.asarray(x_inner_validation, dtype=np.float64)
    y_train = _require_binary_labels(y_fit, reason="invalid_inner_fit_labels")
    y_val = _require_binary_labels(y_inner_validation, reason="invalid_inner_validation_labels")
    if x_train.ndim != 2 or x_val.ndim != 2 or x_train.shape[1] != x_val.shape[1]:
        raise Campaign1Error("inner_feature_shape_mismatch")
    if len(x_train) != len(y_train) or len(x_val) != len(y_val):
        raise Campaign1Error("inner_length_mismatch")
    if len(np.unique(y_train)) != 2 or len(np.unique(y_val)) != 2:
        raise Campaign1Error("inner_split_requires_both_classes")
    if not bool(np.all(np.isfinite(x_train))) or not bool(np.all(np.isfinite(x_val))):
        raise Campaign1Error("non_finite_model_input")

    ledger: list[dict[str, Any]] = []
    for c_value in C_GRID:
        scaler = StandardScaler()
        fit_scaled = scaler.fit_transform(x_train)
        validation_scaled = scaler.transform(x_val)
        model = _new_logistic(c_value)
        model.fit(fit_scaled, y_train)
        probs = model.predict_proba(validation_scaled)[:, 1]
        pred = (probs >= THRESHOLD).astype(np.int8)
        metrics = metric_summary(y_val, pred, probs)
        ledger.append(
            {
                "C": float(c_value),
                "balanced_accuracy": metrics["balanced_accuracy"],
                "macro_f1": metrics["macro_f1"],
            }
        )

    selected = sorted(
        ledger,
        key=lambda item: (
            -float(item["balanced_accuracy"]),
            -float(item["macro_f1"]),
            float(item["C"]),
        ),
    )[0]
    return float(selected["C"]), tuple(ledger)


def prediction_sha256(
    *,
    spec: CandidateSpec,
    representation: str,
    fold_id: int,
    timestamps_us: Any,
    y_true: Any,
    y_pred: Any,
    p_long: Any,
) -> str:
    if representation not in ("S0", "S1"):
        raise Campaign1Error("invalid_representation")
    timestamps = np.asarray(timestamps_us)
    if timestamps.ndim != 1 or timestamps.dtype.kind not in "iu":
        raise Campaign1Error("prediction_hash_timestamps_invalid")
    timestamps = timestamps.astype(np.int64, copy=False)
    truth = _require_binary_labels(y_true, reason="prediction_hash_labels_invalid")
    pred = _require_binary_labels(y_pred, reason="prediction_hash_predictions_invalid")
    probs = np.asarray(p_long, dtype=np.float64)
    if probs.ndim != 1 or not bool(np.all(np.isfinite(probs))):
        raise Campaign1Error("prediction_hash_probabilities_invalid")
    if not (len(timestamps) == len(truth) == len(pred) == len(probs)):
        raise Campaign1Error("prediction_hash_length_mismatch")
    if len(timestamps) and bool(np.any(np.diff(timestamps) <= 0)):
        raise Campaign1Error("prediction_hash_timestamps_not_chronological")

    digest = hashlib.sha256()
    digest.update(PREDICTION_HASH_DOMAIN)
    domain = (
        f"{spec.target_id}|{spec.horizon_seconds}|{spec.barrier_bps}|"
        f"{spec.window_seconds}|{spec.block}|{representation}|{int(fold_id)}"
    ).encode("ascii")
    digest.update(struct.pack(">Q", len(domain)))
    digest.update(domain)
    digest.update(struct.pack(">Q", len(timestamps)))
    for timestamp, truth_value, pred_value, probability in zip(
        timestamps.tolist(), truth.tolist(), pred.tolist(), probs.tolist(), strict=True
    ):
        digest.update(struct.pack(">qbbd", int(timestamp), int(truth_value), int(pred_value), float(probability)))
    return digest.hexdigest()


def fit_outer_representation(
    *,
    spec: CandidateSpec,
    representation: str,
    fold_id: int,
    x_inner_fit: Any,
    y_inner_fit: Any,
    x_inner_validation: Any,
    y_inner_validation: Any,
    x_outer_train: Any,
    y_outer_train: Any,
    x_outer_validation: Any,
    y_outer_validation: Any,
    outer_validation_timestamps_us: Any,
) -> RepresentationFoldResult:
    selected_c, _ = select_c_chronologically(
        x_inner_fit, y_inner_fit, x_inner_validation, y_inner_validation
    )
    x_train = np.asarray(x_outer_train, dtype=np.float64)
    x_val = np.asarray(x_outer_validation, dtype=np.float64)
    y_train = _require_binary_labels(y_outer_train, reason="invalid_outer_train_labels")
    y_val = _require_binary_labels(y_outer_validation, reason="invalid_outer_validation_labels")
    if len(np.unique(y_train)) != 2 or len(np.unique(y_val)) != 2:
        raise Campaign1Error("outer_split_requires_both_classes")
    if x_train.ndim != 2 or x_val.ndim != 2 or x_train.shape[1] != x_val.shape[1]:
        raise Campaign1Error("outer_feature_shape_mismatch")
    if len(x_train) != len(y_train) or len(x_val) != len(y_val):
        raise Campaign1Error("outer_length_mismatch")
    if not bool(np.all(np.isfinite(x_train))) or not bool(np.all(np.isfinite(x_val))):
        raise Campaign1Error("non_finite_model_input")

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_val_scaled = scaler.transform(x_val)
    model = _new_logistic(selected_c)
    model.fit(x_train_scaled, y_train)
    probs = model.predict_proba(x_val_scaled)[:, 1]
    pred = (probs >= THRESHOLD).astype(np.int8)
    timestamps = np.asarray(outer_validation_timestamps_us, dtype=np.int64)
    metrics = metric_summary(y_val, pred, probs)
    digest = prediction_sha256(
        spec=spec,
        representation=representation,
        fold_id=fold_id,
        timestamps_us=timestamps,
        y_true=y_val,
        y_pred=pred,
        p_long=probs,
    )
    return RepresentationFoldResult(
        int(fold_id),
        float(selected_c),
        int(len(y_val)),
        metrics,
        digest,
        y_val.copy(),
        pred,
        probs.astype(np.float64, copy=False),
        timestamps,
    )


def _dataset_rows(dataset: dd.CandidateDayDataset, representation: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if representation == "S0":
        values = np.asarray(dataset.s0_values, dtype=np.float64)
    elif representation == "S1":
        values = np.asarray(dataset.s1_values, dtype=np.float64)
    else:
        raise Campaign1Error("invalid_representation")
    mask = np.asarray(dataset.t1_common_valid, dtype=bool)
    labels = np.asarray(dataset.t1_labels, dtype=np.int8)
    timestamps = np.asarray(dataset.decision_timestamps_us, dtype=np.int64)
    if values.ndim != 2 or len(values) != len(mask) or len(labels) != len(mask) or len(timestamps) != len(mask):
        raise Campaign1Error("candidate_day_array_shape_mismatch")
    return values[mask], labels[mask], timestamps[mask]


def _stack_days(
    per_day: Mapping[date, dd.CandidateDayDataset],
    days: Sequence[date],
    representation: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    chunks = [_dataset_rows(per_day[day], representation) for day in days]
    x = np.concatenate([item[0] for item in chunks], axis=0)
    y = np.concatenate([item[1] for item in chunks], axis=0)
    ts = np.concatenate([item[2] for item in chunks], axis=0)
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise Campaign1Error("stacked_timestamps_not_chronological")
    return x, y, ts


def _pooled_fold_metrics(folds: Sequence[RepresentationFoldResult]) -> dict[str, Any]:
    if len(folds) != 4:
        raise Campaign1Error("outer_fold_count_mismatch")
    truth = np.concatenate([fold.y_true for fold in folds])
    pred = np.concatenate([fold.y_pred for fold in folds])
    probs = np.concatenate([fold.p_long for fold in folds])
    timestamps = np.concatenate([fold.timestamps_us for fold in folds])
    if len(timestamps) and bool(np.any(np.diff(timestamps) <= 0)):
        raise Campaign1Error("pooled_timestamps_not_chronological")
    return metric_summary(truth, pred, probs)


def fit_candidate_m1(
    spec: CandidateSpec,
    per_day: Mapping[date, dd.CandidateDayDataset],
) -> CandidateModelResult:
    if tuple(per_day) != dd.HISTORICAL_DAYS:
        raise Campaign1Error("candidate_day_order_mismatch")
    key = _candidate_key(spec)
    for day in dd.HISTORICAL_DAYS:
        if per_day[day].key != key:
            raise Campaign1Error("candidate_key_mismatch")

    s0_folds: list[RepresentationFoldResult] = []
    s1_folds: list[RepresentationFoldResult] = []
    for outer in dd.OUTER_FOLDS:
        inner_validation_day = outer.train_days[-1]
        inner_fit_days = outer.train_days[:-1]
        if not inner_fit_days:
            raise Campaign1Error("inner_fit_empty")
        for representation, sink in (("S0", s0_folds), ("S1", s1_folds)):
            x_inner_fit, y_inner_fit, _ = _stack_days(per_day, inner_fit_days, representation)
            x_inner_val, y_inner_val, _ = _stack_days(per_day, (inner_validation_day,), representation)
            x_train, y_train, _ = _stack_days(per_day, outer.train_days, representation)
            x_val, y_val, val_ts = _stack_days(per_day, (outer.validation_day,), representation)
            sink.append(
                fit_outer_representation(
                    spec=spec,
                    representation=representation,
                    fold_id=outer.fold_id,
                    x_inner_fit=x_inner_fit,
                    y_inner_fit=y_inner_fit,
                    x_inner_validation=x_inner_val,
                    y_inner_validation=y_inner_val,
                    x_outer_train=x_train,
                    y_outer_train=y_train,
                    x_outer_validation=x_val,
                    y_outer_validation=y_val,
                    outer_validation_timestamps_us=val_ts,
                )
            )

    s0_tuple = tuple(s0_folds)
    s1_tuple = tuple(s1_folds)
    s0_pooled = _pooled_fold_metrics(s0_tuple)
    s1_pooled = _pooled_fold_metrics(s1_tuple)
    fold_delta = tuple(
        float(s1.metrics["balanced_accuracy"] - s0.metrics["balanced_accuracy"])
        for s0, s1 in zip(s0_tuple, s1_tuple, strict=True)
    )
    pooled_delta_ba = float(s1_pooled["balanced_accuracy"] - s0_pooled["balanced_accuracy"])
    pooled_delta_f1 = float(s1_pooled["macro_f1"] - s0_pooled["macro_f1"])

    loo: list[float] = []
    for omitted in range(4):
        s0_keep = tuple(item for index, item in enumerate(s0_tuple) if index != omitted)
        s1_keep = tuple(item for index, item in enumerate(s1_tuple) if index != omitted)
        loo.append(
            float(
                _pooled_fold_metrics(s1_keep + (s1_tuple[omitted],))["balanced_accuracy"]
                - _pooled_fold_metrics(s0_keep + (s0_tuple[omitted],))["balanced_accuracy"]
            )
        )
    # Recompute true leave-one-fold-out metrics explicitly, without the omitted fold.
    loo = []
    for omitted in range(4):
        s0_truth = np.concatenate([f.y_true for i, f in enumerate(s0_tuple) if i != omitted])
        s0_pred = np.concatenate([f.y_pred for i, f in enumerate(s0_tuple) if i != omitted])
        s1_truth = np.concatenate([f.y_true for i, f in enumerate(s1_tuple) if i != omitted])
        s1_pred = np.concatenate([f.y_pred for i, f in enumerate(s1_tuple) if i != omitted])
        if not np.array_equal(s0_truth, s1_truth):
            raise Campaign1Error("matched_support_label_mismatch")
        loo.append(
            float(
                balanced_accuracy_score(s1_truth, s1_pred)
                - balanced_accuracy_score(s0_truth, s0_pred)
            )
        )

    s1_ba = [float(f.metrics["balanced_accuracy"]) for f in s1_tuple]
    predicted_minor = min(
        int(s1_pooled["predicted_long_count"]),
        int(s1_pooled["predicted_short_count"]),
    ) / int(s1_pooled["support"])
    gates = {
        "primary_target": spec.target_id in PROMOTABLE_TARGET_IDS,
        "pooled_ba_at_least_054": float(s1_pooled["balanced_accuracy"]) >= 0.54,
        "median_fold_ba_gt_050": float(np.median(s1_ba)) > 0.50,
        "at_least_3_of_4_fold_ba_gt_050": sum(value > 0.50 for value in s1_ba) >= 3,
        "pooled_delta_ba_at_least_002": pooled_delta_ba >= 0.02,
        "at_least_3_of_4_positive_fold_delta": sum(value > 0.0 for value in fold_delta) >= 3,
        "both_classes_predicted_each_fold": all(
            int(f.metrics["predicted_long_count"]) > 0 and int(f.metrics["predicted_short_count"]) > 0
            for f in s1_tuple
        ),
        "pooled_predicted_minority_fraction_at_least_010": predicted_minor >= 0.10,
        "leave_one_fold_out_delta_positive": all(value > 0.0 for value in loo),
    }
    precheck = all(gates.values())
    first_day = per_day[dd.HISTORICAL_DAYS[0]]
    return CandidateModelResult(
        spec,
        int(len(first_day.s0_feature_names)),
        int(len(first_day.s1_feature_names)),
        s0_tuple,
        s1_tuple,
        s0_pooled,
        s1_pooled,
        fold_delta,
        pooled_delta_ba,
        pooled_delta_f1,
        tuple(loo),
        precheck,
        gates,
    )


def eligible_shared_null_shifts(group_sizes: Sequence[int]) -> tuple[int, ...]:
    sizes = tuple(int(item) for item in group_sizes)
    if not sizes or any(item <= 0 for item in sizes):
        raise Campaign1Error("invalid_null_group_sizes")
    upper = min(sizes) - 1
    return tuple(
        k
        for k in range(1, upper + 1)
        if all(min(k, n - k) >= 10 for n in sizes)
    )


def temporal_label_null(
    folds: Sequence[RepresentationFoldResult],
) -> TemporalNullResult:
    if len(folds) != 4:
        raise Campaign1Error("outer_fold_count_mismatch")
    group_sizes = [len(fold.y_true) for fold in folds]
    shifts = eligible_shared_null_shifts(group_sizes)
    if len(shifts) < 20:
        raise Campaign1Error("insufficient_temporal_null_shifts")

    truth = np.concatenate([fold.y_true for fold in folds])
    pred = np.concatenate([fold.y_pred for fold in folds])
    observed = float(balanced_accuracy_score(truth, pred))
    null_values: list[float] = []
    for k in shifts:
        shifted = np.concatenate([np.roll(fold.y_true, k) for fold in folds])
        null_values.append(float(balanced_accuracy_score(shifted, pred)))
    q95 = float(np.quantile(np.asarray(null_values), 0.95, method="higher"))
    empirical_p = float(
        (1 + sum(value >= observed for value in null_values))
        / (1 + len(null_values))
    )
    return TemporalNullResult(
        shifts,
        tuple(null_values),
        q95,
        empirical_p,
        observed,
        bool(observed > q95 and empirical_p <= 0.05),
    )


def final_promotion_gates(
    model_result: CandidateModelResult,
    null_result: TemporalNullResult | None,
) -> dict[str, bool]:
    gates = dict(model_result.precheck_gates)
    gates["temporal_null_run"] = null_result is not None
    gates["temporal_null_ba_gt_q95"] = bool(
        null_result is not None
        and null_result.observed_balanced_accuracy > null_result.null_q95
    )
    gates["temporal_null_p_le_005"] = bool(
        null_result is not None and null_result.empirical_p <= 0.05
    )
    return gates


def candidate_is_eligible(
    model_result: CandidateModelResult,
    null_result: TemporalNullResult | None,
) -> bool:
    return all(final_promotion_gates(model_result, null_result).values())


def survivor_rank_key(result: CandidateModelResult) -> tuple[Any, ...]:
    if result.spec.target_id not in PROMOTABLE_TARGET_IDS:
        raise Campaign1Error("control_target_not_rankable")
    s1_ba = [float(f.metrics["balanced_accuracy"]) for f in result.s1_folds]
    block_index = dd.FROZEN_BLOCKS.index(result.spec.block)
    target_index = PROMOTABLE_TARGET_IDS.index(result.spec.target_id)
    return (
        -min(s1_ba),
        -float(np.median(s1_ba)),
        -float(result.pooled_delta_ba),
        -float(result.s1_pooled["balanced_accuracy"]),
        -float(result.s1_pooled["macro_f1"]),
        int(result.spec.window_seconds),
        int(block_index),
        int(target_index),
    )


def select_survivor(
    candidates: Sequence[tuple[CandidateModelResult, TemporalNullResult | None]],
) -> CandidateModelResult | None:
    eligible = [
        model
        for model, null in candidates
        if candidate_is_eligible(model, null)
    ]
    if not eligible:
        return None
    return sorted(eligible, key=survivor_rank_key)[0]


def _fold_public(fold: RepresentationFoldResult) -> dict[str, Any]:
    return {
        "fold_id": fold.fold_id,
        "selected_C": fold.selected_c,
        "support": fold.support,
        "metrics": fold.metrics,
        "prediction_sha256": fold.prediction_sha256,
    }


def _model_result_public(
    model: CandidateModelResult,
    null: TemporalNullResult | None,
) -> dict[str, Any]:
    gates = final_promotion_gates(model, null)
    return {
        **_public_spec(model.spec),
        "feature_count_s0": model.feature_count_s0,
        "feature_count_s1": model.feature_count_s1,
        "s0": {
            "folds": [_fold_public(item) for item in model.s0_folds],
            "pooled": model.s0_pooled,
        },
        "s1": {
            "folds": [_fold_public(item) for item in model.s1_folds],
            "pooled": model.s1_pooled,
        },
        "fold_delta_balanced_accuracy": list(model.fold_delta_ba),
        "pooled_delta_balanced_accuracy": model.pooled_delta_ba,
        "pooled_delta_macro_f1": model.pooled_delta_macro_f1,
        "leave_one_fold_out_delta_balanced_accuracy": list(model.leave_one_fold_out_delta_ba),
        "precheck_pass": model.precheck_pass,
        "temporal_null": (
            {
                "eligible_shifts": list(null.eligible_shifts),
                "null_balanced_accuracy": list(null.null_balanced_accuracy),
                "null_q95": null.null_q95,
                "empirical_p": null.empirical_p,
                "observed_balanced_accuracy": null.observed_balanced_accuracy,
                "pass_gate": null.pass_gate,
            }
            if null is not None
            else {"status": "TEMPORAL_NULL_NOT_RUN_PRECHECK_FAILED"}
        ),
        "promotion_gates": gates,
        "eligible_for_next_development_stage": bool(all(gates.values())),
    }


def build_campaign_payload(
    *,
    execution_commit: str,
    runtime_state: Mapping[str, Any],
    candidate_results: Sequence[tuple[CandidateModelResult, TemporalNullResult | None]],
    input_manifest: Sequence[dd.InputManifestEntry],
    dependency_hashes: Mapping[str, str],
) -> dict[str, Any]:
    if len(candidate_results) != 64:
        raise Campaign1Error("trial_ledger_must_contain_64_candidates")
    expected_specs = frozen_candidate_specs()
    actual_specs = tuple(item[0].spec for item in candidate_results)
    if actual_specs != expected_specs:
        raise Campaign1Error("trial_ledger_candidate_order_mismatch")
    runtime = validate_runtime_provenance(runtime_state)
    selected = select_survivor(candidate_results)
    entries = [_model_result_public(model, null) for model, null in candidate_results]
    selected_public = _public_spec(selected.spec) if selected is not None else None
    status = STATUS_SURVIVOR if selected is not None else STATUS_NO_SURVIVOR
    return {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "status": status,
        "execution_commit": str(execution_commit),
        "p2c_artifact": {
            "path": str(P2C_ARTIFACT_PATH),
            "sha256": P2C_ARTIFACT_SHA256,
        },
        "dependency_sha256": dict(sorted(dependency_hashes.items())),
        "authorized_input_manifest": [
            {
                "date": item.day.isoformat(),
                "path": str(item.path),
                "sha256": item.sha256,
                "bytes": int(item.bytes),
            }
            for item in input_manifest
        ],
        "configuration": {
            "candidate_count": 64,
            "targets": [
                {
                    "target_id": target.target_id,
                    "horizon_seconds": int(target.horizon_seconds),
                    "barrier_bps": int(target.barrier_bps),
                }
                for target in dd.FROZEN_TARGETS
            ],
            "windows_seconds": list(dd.FROZEN_WINDOWS_SECONDS),
            "blocks": list(dd.FROZEN_BLOCKS),
            "outer_folds": [
                {
                    "fold_id": int(fold.fold_id),
                    "train_days": [day.isoformat() for day in fold.train_days],
                    "validation_day": fold.validation_day.isoformat(),
                }
                for fold in dd.OUTER_FOLDS
            ],
            "inner_rule": "final outer-training consumed day is inner validation",
            "C_grid": list(C_GRID),
            "threshold": THRESHOLD,
            "solver": "lbfgs",
            "l1_ratio": 0.0,
            "class_weight": None,
            "max_iter": 1000,
            "random_state": RANDOM_STATE,
        },
        "runtime_provenance": runtime,
        "trial_ledger": entries,
        "selected_for_next_development_stage": selected_public,
        "prohibited_activity": {
            "pnl": False,
            "economics": False,
            "opportunity_gate": False,
            "forward_data": False,
            "t2": False,
            "m2_or_deep_model": False,
        },
    }


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    safe = dm.normalize_json_safe(dict(payload))
    try:
        text = json.dumps(
            safe,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise Campaign1Error("canonical_json_failed", str(exc)) from exc
    return (text + "\n").encode("utf-8")


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_result_once(
    output_directory: Path,
    payload: Mapping[str, Any],
) -> ArtifactWriteResult:
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise Campaign1Error("output_directory_already_exists")
    if output != REAL_OUTPUT_DIRECTORY:
        raise Campaign1Error("noncanonical_output_directory")
    content = canonical_json_bytes(payload)
    output.mkdir(mode=0o755)
    _fsync_directory(output.parent)
    final = output / ARTIFACT_FILENAME
    part = final.with_name(final.name + ".part")
    if final.exists() or part.exists() or final.is_symlink() or part.is_symlink():
        raise Campaign1Error("artifact_path_preexists")
    try:
        with part.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(part, final)
        _fsync_directory(output)
    except BaseException as exc:
        if final.exists():
            raise Campaign1Error("artifact_directory_fsync_failed", str(exc)) from exc
        try:
            if part.exists():
                part.unlink()
            if output.exists() and not any(output.iterdir()):
                output.rmdir()
        except OSError as cleanup_exc:
            raise Campaign1Error("artifact_cleanup_failed", str(cleanup_exc)) from cleanup_exc
        if isinstance(exc, Campaign1Error):
            raise
        raise Campaign1Error("artifact_write_failed", str(exc)) from exc
    digest = hashlib.sha256(content).hexdigest()
    return ArtifactWriteResult(output, final, digest, len(content))


__all__ = [
    "ARTIFACT_FILENAME",
    "C_GRID",
    "DESIGN_VERSION",
    "EXPERIMENT_ID",
    "P2C_ARTIFACT_PATH",
    "P2C_ARTIFACT_SHA256",
    "PROMOTABLE_TARGET_IDS",
    "REAL_OUTPUT_DIRECTORY",
    "THRESHOLD",
    "ArtifactWriteResult",
    "Campaign1Error",
    "CandidateModelResult",
    "CandidateSpec",
    "RepresentationFoldResult",
    "TemporalNullResult",
    "build_campaign_payload",
    "candidate_is_eligible",
    "canonical_json_bytes",
    "eligible_shared_null_shifts",
    "final_promotion_gates",
    "fit_candidate_m1",
    "fit_outer_representation",
    "frozen_candidate_specs",
    "load_frozen_p2c_artifact",
    "metric_summary",
    "prediction_sha256",
    "reconcile_candidate_payload",
    "runtime_provenance",
    "select_c_chronologically",
    "select_survivor",
    "survivor_rank_key",
    "validate_runtime_provenance",
    "verify_frozen_dependencies",
    "write_result_once",
]

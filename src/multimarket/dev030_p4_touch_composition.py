"""DEV030-P4 T2 TOUCH_VS_NONE and two-head composition.

This module implements the frozen P4 design on exactly one representation:

    BTCUSDT / target A (120s, 16bp) / 32s / PRICE

P4 is predictive/compositional only.  It does not implement a trading
threshold, PnL, opportunity gating, forward-holdout access, or a new model
family.

The real Jan-Jul run remains separately gated.  Synthetic tests may inject
in-memory CandidateDayDataset objects and must not open market files.
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
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

from . import dev030_direction_dataset as dd
from . import dev030_direction_materialize as dm
from . import dev030_p3_direction as p3


EXPERIMENT_ID = "DEV030-P4"
DESIGN_VERSION = "t2-composition-v1"

SELECTED_TARGET = next(item for item in dd.FROZEN_TARGETS if item.target_id == "A")
SELECTED_WINDOW_SECONDS = 32
SELECTED_BLOCK = "PRICE"
SELECTED_KEY = dd.CandidateKey(
    SELECTED_TARGET,
    SELECTED_WINDOW_SECONDS,
    SELECTED_BLOCK,
)

T2_NONE = 0
T2_TOUCH = 1

C_GRID = (0.01, 0.1, 1.0, 10.0)
THRESHOLD = 0.5
RANDOM_STATE = 20260825

P3_ARTIFACT_PATH = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/"
    "DEV030_P3_CAMPAIGN1_RESULT.json"
)
P3_ARTIFACT_SHA256 = (
    "f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e"
)
P3_SOURCE_SHA256 = (
    "9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675"
)
P3_TEST_SHA256 = (
    "a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b"
)
P2C_ARTIFACT_PATH = p3.P2C_ARTIFACT_PATH
P2C_ARTIFACT_SHA256 = p3.P2C_ARTIFACT_SHA256
P3_SOURCE_REL = "src/multimarket/dev030_p3_direction.py"
P3_TEST_REL = "tests/test_dev030_p3_direction.py"

REAL_OUTPUT_DIRECTORY = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p4_t2_composition_v1"
)
ARTIFACT_FILENAME = "DEV030_P4_T2_COMPOSITION_RESULT.json"

FROZEN_T1_C_BY_FOLD = {
    1: 10.0,
    2: 10.0,
    3: 0.1,
    4: 0.01,
}
FROZEN_T1_PREDICTION_SHA256_BY_FOLD = {
    1: "e03d233bff936b49a0452994497f32ca5ecbe52c1f490d855fe8d06dbfa9dcf4",
    2: "cd2cba0a6dcf3591ec9848b78e31aef796dad15d371bbecb8517aa2507340bdd",
    3: "19f9acf70b0065a307c0373952cad350339768607a156c9307e5192503bb1f31",
    4: "b05ee6e926d6a943e1fc89828eb3801af0863fa270bc2e5db5ed7cd93e9a4b66",
}

FORWARD_GUARDS = {
    "aug30_analytically_opened": False,
    "sep01_or_later_analytically_opened": False,
    "archive_bucket_opened": False,
    "abundant_love_opened": False,
}


class P4Error(RuntimeError):
    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


@dataclass(frozen=True)
class T2DayDataset:
    day: date
    timestamps_us: np.ndarray
    labels: np.ndarray
    s0_values: np.ndarray
    s1_values: np.ndarray
    s0_feature_names: tuple[str, ...]
    s1_feature_names: tuple[str, ...]
    valid_mask_on_candidate: np.ndarray
    support_sha256: str
    touch_count: int
    none_count: int


@dataclass(frozen=True)
class ProbabilityFoldResult:
    fold_id: int
    selected_c: float | None
    support: int
    touch_count: int
    none_count: int
    prevalence: float
    metrics: dict[str, Any]
    timestamps_us: np.ndarray
    y_true: np.ndarray
    p_touch: np.ndarray
    prediction_sha256: str
    inner_c_ledger: tuple[dict[str, Any], ...] = ()
    scaler: Any | None = None
    model: Any | None = None


@dataclass(frozen=True)
class T2ModelResult:
    b0_folds: tuple[ProbabilityFoldResult, ...]
    s0_folds: tuple[ProbabilityFoldResult, ...]
    s1_folds: tuple[ProbabilityFoldResult, ...]
    b0_pooled: dict[str, Any]
    s0_pooled: dict[str, Any]
    s1_pooled: dict[str, Any]
    fold_delta_ap: tuple[float, ...]
    fold_delta_auc: tuple[float, ...]
    pooled_delta_ap: float
    pooled_delta_auc: float
    pooled_delta_brier: float
    ap_lift_ratio: float
    brier_skill_vs_prevalence: float
    leave_one_fold_out_delta_ap: tuple[float, ...]
    precheck_gates: dict[str, bool]
    precheck_pass: bool


@dataclass(frozen=True)
class T2TemporalNull:
    eligible_shifts: tuple[int, ...]
    null_ap: tuple[float, ...]
    null_auc: tuple[float, ...]
    ap_q95: float
    auc_q95: float
    empirical_ap_p: float
    observed_ap: float
    observed_auc: float
    pass_gate: bool


@dataclass(frozen=True)
class T1ReproductionFold:
    fold_id: int
    selected_c: float
    expected_prediction_sha256: str
    actual_prediction_sha256: str
    reproduced: bool
    scaler: Any
    model: Any


@dataclass(frozen=True)
class CompositionFoldResult:
    fold_id: int
    support: int
    metrics_c0: dict[str, Any]
    metrics_c1: dict[str, Any]
    metrics_c2: dict[str, Any]
    log_loss_improvement_vs_c1: float


@dataclass(frozen=True)
class CompositionResult:
    folds: tuple[CompositionFoldResult, ...]
    pooled_c0: dict[str, Any]
    pooled_c1: dict[str, Any]
    pooled_c2: dict[str, Any]
    leave_one_fold_out_log_loss_improvement: tuple[float, ...]
    gates: dict[str, bool]
    eligible_for_later_policy_design: bool


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
        raise P4Error("execution_commit_must_be_full_sha")
    return value


def verify_frozen_dependencies(
    repository_root: Path,
    *,
    hash_file: Any = _sha256_file,
) -> dict[str, str]:
    root = Path(repository_root).resolve()
    expected = (
        (dd.FIRST_PASSAGE_SOURCE_REL, dd.FIRST_PASSAGE_SOURCE_SHA256, "first_passage_source_sha256_mismatch"),
        (dd.SEQUENCE_FEATURE_SOURCE_REL, dd.SEQUENCE_FEATURE_SOURCE_SHA256, "sequence_source_sha256_mismatch"),
        (p3.P2B_SOURCE_REL, p3.P2B_SOURCE_SHA256, "p2b_source_sha256_mismatch"),
        (P3_SOURCE_REL, P3_SOURCE_SHA256, "p3_source_sha256_mismatch"),
        (P3_TEST_REL, P3_TEST_SHA256, "p3_test_sha256_mismatch"),
    )
    result: dict[str, str] = {}
    for rel, expected_sha, reason in expected:
        source = root / rel
        if not source.is_file():
            raise P4Error("frozen_dependency_missing", rel)
        actual = str(hash_file(source))
        if actual != expected_sha:
            raise P4Error(reason, rel)
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
        raise P4Error("frozen_artifact_missing", str(artifact))
    if str(hash_file(artifact)) != expected_sha256:
        raise P4Error("frozen_artifact_sha256_mismatch", str(artifact))
    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise P4Error("frozen_artifact_read_failed", str(exc)) from exc
    if not isinstance(payload, dict):
        raise P4Error("frozen_artifact_not_object")
    return payload


def validate_p3_selected_survivor(payload: Mapping[str, Any]) -> None:
    selected = payload.get("selected_for_next_development_stage")
    expected = {
        "target": {"target_id": "A", "horizon_seconds": 120, "barrier_bps": 16},
        "window_seconds": 32,
        "block": "PRICE",
    }
    if selected != expected:
        raise P4Error("p3_selected_survivor_mismatch")


def runtime_provenance(
    *,
    model_fit_run: bool,
    t2_run: bool,
    composition_run: bool,
) -> dict[str, Any]:
    for value in (model_fit_run, t2_run, composition_run):
        if type(value) is not bool:
            raise P4Error("runtime_flags_must_be_builtin_bool")
    if t2_run and not model_fit_run:
        raise P4Error("t2_requires_model_fit")
    if composition_run and not t2_run:
        raise P4Error("composition_requires_t2")
    return {
        "jan_jul_analytically_opened": True,
        "authorized_development_data": {
            "scope": "BTCUSDT consumed Jan-Jul development days only",
            "analytically_loaded": True,
        },
        "forward_data_guards": dict(FORWARD_GUARDS),
        "model_fit_run": model_fit_run,
        "t2_run": t2_run,
        "composition_run": composition_run,
        "threshold_optimization_run": False,
        "pnl_backtest_run": False,
        "opportunity_gate_run": False,
    }


def validate_runtime_provenance(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "jan_jul_analytically_opened",
        "authorized_development_data",
        "forward_data_guards",
        "model_fit_run",
        "t2_run",
        "composition_run",
        "threshold_optimization_run",
        "pnl_backtest_run",
        "opportunity_gate_run",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise P4Error("runtime_provenance_schema_mismatch")
    if value["jan_jul_analytically_opened"] is not True:
        raise P4Error("jan_jul_runtime_state_invalid")
    development = value["authorized_development_data"]
    if (
        not isinstance(development, Mapping)
        or set(development) != {"scope", "analytically_loaded"}
        or development["scope"] != "BTCUSDT consumed Jan-Jul development days only"
        or development["analytically_loaded"] is not True
    ):
        raise P4Error("authorized_development_runtime_mismatch")
    guards = value["forward_data_guards"]
    if (
        not isinstance(guards, Mapping)
        or set(guards) != set(FORWARD_GUARDS)
        or any(type(item) is not bool for item in guards.values())
        or any(guards.values())
    ):
        raise P4Error("forward_data_guard_violation")
    for field in (
        "model_fit_run",
        "t2_run",
        "composition_run",
        "threshold_optimization_run",
        "pnl_backtest_run",
        "opportunity_gate_run",
    ):
        if type(value[field]) is not bool:
            raise P4Error("runtime_flags_must_be_builtin_bool")
    if value["t2_run"] and not value["model_fit_run"]:
        raise P4Error("t2_requires_model_fit")
    if value["composition_run"] and not value["t2_run"]:
        raise P4Error("composition_requires_t2")
    if (
        value["threshold_optimization_run"]
        or value["pnl_backtest_run"]
        or value["opportunity_gate_run"]
    ):
        raise P4Error("prohibited_runtime_activity")
    return dict(value)


def validate_selected_candidate(dataset: dd.CandidateDayDataset) -> None:
    if dataset.key != SELECTED_KEY:
        raise P4Error("selected_candidate_identity_mismatch")
    if dataset.s0_feature_names != tuple(dd.sf.block_feature_names(SELECTED_BLOCK)):
        raise P4Error("selected_s0_feature_order_mismatch")
    if dataset.s1_feature_names != dd.sequence_summary_feature_names(SELECTED_BLOCK):
        raise P4Error("selected_s1_feature_order_mismatch")


def build_t2_day(dataset: dd.CandidateDayDataset) -> T2DayDataset:
    """Map frozen first-passage records to TOUCH/NONE on common valid support."""

    validate_selected_candidate(dataset)
    n = len(dataset.decision_timestamps_us)
    if len(dataset.target_records) != n:
        raise P4Error("target_record_count_mismatch")

    common = np.asarray(dataset.common_valid, dtype=bool)
    future = np.asarray(dataset.target_future_boundary_valid, dtype=bool)
    if len(common) != n or len(future) != n:
        raise P4Error("candidate_mask_length_mismatch")

    labels = np.full(n, -1, dtype=np.int8)
    valid_target = np.zeros(n, dtype=bool)
    for i, record in enumerate(dataset.target_records):
        mapped, reason = dd.map_t1_record(record)
        if record["target_valid"] is True and future[i]:
            valid_target[i] = True
            labels[i] = T2_TOUCH if mapped in (dd.T1_LONG, dd.T1_SHORT) else T2_NONE
        else:
            if mapped is not None:
                raise P4Error("invalid_target_mapped_directionally")
            if record["target_valid"] is True and not future[i]:
                raise P4Error("target_boundary_labeler_mismatch")
            _ = reason

    mask = common & valid_target
    timestamps = np.asarray(dataset.decision_timestamps_us, dtype=np.int64)[mask]
    y = labels[mask]
    if len(y) == 0 or not bool(np.all(np.isin(y, (0, 1)))):
        raise P4Error("t2_support_empty_or_invalid")
    s0 = np.asarray(dataset.s0_values, dtype=np.float64)[mask]
    s1 = np.asarray(dataset.s1_values, dtype=np.float64)[mask]
    if not bool(np.all(np.isfinite(s0))) or not bool(np.all(np.isfinite(s1))):
        raise P4Error("non_finite_t2_features")
    digest = dd.support_sha256(timestamps)
    return T2DayDataset(
        dataset.day,
        timestamps,
        y,
        s0,
        s1,
        tuple(dataset.s0_feature_names),
        tuple(dataset.s1_feature_names),
        mask,
        digest,
        int(np.count_nonzero(y == T2_TOUCH)),
        int(np.count_nonzero(y == T2_NONE)),
    )



def reconcile_selected_candidate_with_p2c(
    candidate_per_day: Mapping[date, dd.CandidateDayDataset],
    p2c_payload: Mapping[str, Any],
) -> None:
    candidates = p2c_payload.get("per_candidate")
    if not isinstance(candidates, list):
        raise P4Error("p2c_candidate_payload_missing")
    matches = [
        item for item in candidates
        if item.get("target") == {
            "target_id": "A",
            "horizon_seconds": 120,
            "barrier_bps": 16,
        }
        and item.get("window_seconds") == 32
        and item.get("block") == "PRICE"
    ]
    if len(matches) != 1:
        raise P4Error("p2c_selected_candidate_not_unique")
    frozen = matches[0]
    frozen_days = frozen.get("per_day")
    if not isinstance(frozen_days, list) or len(frozen_days) != len(dd.HISTORICAL_DAYS):
        raise P4Error("p2c_selected_day_contract_missing")

    for day, frozen_day in zip(dd.HISTORICAL_DAYS, frozen_days, strict=True):
        dataset = candidate_per_day[day]
        validate_selected_candidate(dataset)
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
                raise P4Error("p2c_selected_candidate_reconciliation_failed", f"{day}:{field}")


def _stack_days(
    per_day: Mapping[date, T2DayDataset],
    days: Sequence[date],
    representation: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if representation not in ("S0", "S1"):
        raise P4Error("invalid_representation")
    chunks = [per_day[day] for day in days]
    x = np.concatenate([
        item.s0_values if representation == "S0" else item.s1_values
        for item in chunks
    ])
    y = np.concatenate([item.labels for item in chunks]).astype(np.int8, copy=False)
    ts = np.concatenate([item.timestamps_us for item in chunks]).astype(np.int64, copy=False)
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P4Error("stacked_t2_timestamps_not_chronological")
    return x, y, ts


def probability_metrics(y_true: Any, p_touch: Any) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(p_touch, dtype=np.float64)
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p) or len(y) == 0:
        raise P4Error("probability_metric_shape_mismatch")
    if not bool(np.all(np.isin(y, (0, 1)))):
        raise P4Error("invalid_t2_labels")
    if not bool(np.all(np.isfinite(p))) or not bool(np.all((p >= 0) & (p <= 1))):
        raise P4Error("invalid_touch_probabilities")
    if len(np.unique(y)) != 2:
        raise P4Error("t2_metric_requires_both_classes")

    pred = (p >= THRESHOLD).astype(np.int8)
    prevalence = float(np.mean(y))
    return {
        "support": int(len(y)),
        "touch_count": int(np.count_nonzero(y == 1)),
        "none_count": int(np.count_nonzero(y == 0)),
        "touch_prevalence": prevalence,
        "average_precision": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, np.column_stack((1.0 - p, p)), labels=[0, 1])),
        "balanced_accuracy_at_0_5": float(balanced_accuracy_score(y, pred)),
        "macro_f1_at_0_5": float(f1_score(y, pred, average="macro", zero_division=0)),
        "mcc_at_0_5": float(matthews_corrcoef(y, pred)),
        "predicted_touch_count_at_0_5": int(np.count_nonzero(pred == 1)),
        "predicted_none_count_at_0_5": int(np.count_nonzero(pred == 0)),
        "confusion_matrix_none_touch_at_0_5": confusion_matrix(
            y, pred, labels=[0, 1]
        ).astype(int).tolist(),
    }


def _new_logistic(c_value: float) -> LogisticRegression:
    if c_value not in C_GRID:
        raise P4Error("c_not_in_frozen_grid")
    return LogisticRegression(
        C=float(c_value),
        solver="lbfgs",
        l1_ratio=0.0,
        class_weight=None,
        max_iter=1000,
        fit_intercept=True,
        random_state=RANDOM_STATE,
    )


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
        raise P4Error("inner_feature_shape_mismatch")
    if len(xf) != len(yf) or len(xv) != len(yv):
        raise P4Error("inner_length_mismatch")
    if len(np.unique(yf)) != 2 or len(np.unique(yv)) != 2:
        raise P4Error("inner_split_requires_both_classes")
    if not bool(np.all(np.isfinite(xf))) or not bool(np.all(np.isfinite(xv))):
        raise P4Error("non_finite_t2_features")

    ledger: list[dict[str, Any]] = []
    for c_value in C_GRID:
        scaler = StandardScaler()
        xfs = scaler.fit_transform(xf)
        xvs = scaler.transform(xv)
        model = _new_logistic(c_value)
        model.fit(xfs, yf)
        probs = model.predict_proba(xvs)[:, 1]
        metrics = probability_metrics(yv, probs)
        ledger.append({
            "C": float(c_value),
            "average_precision": metrics["average_precision"],
            "roc_auc": metrics["roc_auc"],
            "brier": metrics["brier"],
        })

    chosen = sorted(
        ledger,
        key=lambda item: (
            -float(item["average_precision"]),
            -float(item["roc_auc"]),
            float(item["brier"]),
            float(item["C"]),
        ),
    )[0]
    return float(chosen["C"]), tuple(ledger)


def probability_prediction_sha256(
    *,
    fold_id: int,
    representation: str,
    timestamps_us: Any,
    y_true: Any,
    p_touch: Any,
) -> str:
    if representation not in ("B0", "S0", "S1"):
        raise P4Error("invalid_probability_hash_representation")
    ts = np.asarray(timestamps_us, dtype=np.int64)
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(p_touch, dtype=np.float64)
    if not (len(ts) == len(y) == len(p)):
        raise P4Error("probability_hash_length_mismatch")
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P4Error("probability_hash_timestamps_not_chronological")
    digest = hashlib.sha256()
    digest.update(b"DEV030-P4-T2-OOF-V1\x00")
    digest.update(f"{fold_id}|{representation}".encode("ascii"))
    for t, yy, pp in zip(ts.tolist(), y.tolist(), p.tolist(), strict=True):
        digest.update(int(t).to_bytes(8, "big", signed=True))
        digest.update(int(yy).to_bytes(1, "big", signed=False))
        digest.update(np.asarray(float(pp), dtype=">f8").tobytes())
    return digest.hexdigest()


def fit_probability_fold(
    *,
    fold_id: int,
    representation: str,
    x_inner_fit: Any,
    y_inner_fit: Any,
    x_inner_validation: Any,
    y_inner_validation: Any,
    x_outer_train: Any,
    y_outer_train: Any,
    x_outer_validation: Any,
    y_outer_validation: Any,
    validation_timestamps_us: Any,
) -> ProbabilityFoldResult:
    selected_c, ledger = select_c(
        x_inner_fit,
        y_inner_fit,
        x_inner_validation,
        y_inner_validation,
    )
    xt = np.asarray(x_outer_train, dtype=np.float64)
    yt = np.asarray(y_outer_train, dtype=np.int8)
    xv = np.asarray(x_outer_validation, dtype=np.float64)
    yv = np.asarray(y_outer_validation, dtype=np.int8)
    if len(np.unique(yt)) != 2 or len(np.unique(yv)) != 2:
        raise P4Error("outer_split_requires_both_classes")
    scaler = StandardScaler()
    xts = scaler.fit_transform(xt)
    xvs = scaler.transform(xv)
    model = _new_logistic(selected_c)
    model.fit(xts, yt)
    p_touch = model.predict_proba(xvs)[:, 1]
    metrics = probability_metrics(yv, p_touch)
    ts = np.asarray(validation_timestamps_us, dtype=np.int64)
    return ProbabilityFoldResult(
        int(fold_id),
        selected_c,
        int(len(yv)),
        int(np.count_nonzero(yv == 1)),
        int(np.count_nonzero(yv == 0)),
        float(np.mean(yv)),
        metrics,
        ts,
        yv.copy(),
        p_touch,
        probability_prediction_sha256(
            fold_id=fold_id,
            representation=representation,
            timestamps_us=ts,
            y_true=yv,
            p_touch=p_touch,
        ),
        ledger,
        scaler,
        model,
    )


def prevalence_fold(
    *,
    fold_id: int,
    y_train: Any,
    y_validation: Any,
    validation_timestamps_us: Any,
) -> ProbabilityFoldResult:
    yt = np.asarray(y_train, dtype=np.int8)
    yv = np.asarray(y_validation, dtype=np.int8)
    if len(yt) == 0 or len(yv) == 0:
        raise P4Error("prevalence_support_empty")
    prevalence = float(np.mean(yt))
    probs = np.full(len(yv), prevalence, dtype=np.float64)
    metrics = probability_metrics(yv, probs)
    ts = np.asarray(validation_timestamps_us, dtype=np.int64)
    return ProbabilityFoldResult(
        int(fold_id),
        None,
        int(len(yv)),
        int(np.count_nonzero(yv == 1)),
        int(np.count_nonzero(yv == 0)),
        float(np.mean(yv)),
        metrics,
        ts,
        yv.copy(),
        probs,
        probability_prediction_sha256(
            fold_id=fold_id,
            representation="B0",
            timestamps_us=ts,
            y_true=yv,
            p_touch=probs,
        ),
    )


def _pooled_probability_metrics(
    folds: Sequence[ProbabilityFoldResult],
) -> dict[str, Any]:
    y = np.concatenate([f.y_true for f in folds])
    p = np.concatenate([f.p_touch for f in folds])
    ts = np.concatenate([f.timestamps_us for f in folds])
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P4Error("pooled_t2_timestamps_not_chronological")
    return probability_metrics(y, p)


def fit_t2(per_day: Mapping[date, T2DayDataset]) -> T2ModelResult:
    if tuple(per_day) != dd.HISTORICAL_DAYS:
        raise P4Error("t2_day_order_mismatch")

    b0_folds: list[ProbabilityFoldResult] = []
    s0_folds: list[ProbabilityFoldResult] = []
    s1_folds: list[ProbabilityFoldResult] = []

    for fold in dd.OUTER_FOLDS:
        inner_val_day = fold.train_days[-1]
        inner_fit_days = fold.train_days[:-1]

        x0_if, y_if, _ = _stack_days(per_day, inner_fit_days, "S0")
        x0_iv, y_iv, _ = _stack_days(per_day, (inner_val_day,), "S0")
        x0_tr, y_tr, _ = _stack_days(per_day, fold.train_days, "S0")
        x0_va, y_va, ts_va = _stack_days(per_day, (fold.validation_day,), "S0")

        x1_if, y1_if, _ = _stack_days(per_day, inner_fit_days, "S1")
        x1_iv, y1_iv, _ = _stack_days(per_day, (inner_val_day,), "S1")
        x1_tr, y1_tr, _ = _stack_days(per_day, fold.train_days, "S1")
        x1_va, y1_va, ts1_va = _stack_days(per_day, (fold.validation_day,), "S1")

        if not (
            np.array_equal(y_if, y1_if)
            and np.array_equal(y_iv, y1_iv)
            and np.array_equal(y_tr, y1_tr)
            and np.array_equal(y_va, y1_va)
            and np.array_equal(ts_va, ts1_va)
        ):
            raise P4Error("s0_s1_t2_support_mismatch")

        b0_folds.append(
            prevalence_fold(
                fold_id=fold.fold_id,
                y_train=y_tr,
                y_validation=y_va,
                validation_timestamps_us=ts_va,
            )
        )
        s0_folds.append(
            fit_probability_fold(
                fold_id=fold.fold_id,
                representation="S0",
                x_inner_fit=x0_if,
                y_inner_fit=y_if,
                x_inner_validation=x0_iv,
                y_inner_validation=y_iv,
                x_outer_train=x0_tr,
                y_outer_train=y_tr,
                x_outer_validation=x0_va,
                y_outer_validation=y_va,
                validation_timestamps_us=ts_va,
            )
        )
        s1_folds.append(
            fit_probability_fold(
                fold_id=fold.fold_id,
                representation="S1",
                x_inner_fit=x1_if,
                y_inner_fit=y1_if,
                x_inner_validation=x1_iv,
                y_inner_validation=y1_iv,
                x_outer_train=x1_tr,
                y_outer_train=y1_tr,
                x_outer_validation=x1_va,
                y_outer_validation=y1_va,
                validation_timestamps_us=ts1_va,
            )
        )

    b0 = tuple(b0_folds)
    s0 = tuple(s0_folds)
    s1 = tuple(s1_folds)
    b0_pooled = _pooled_probability_metrics(b0)
    s0_pooled = _pooled_probability_metrics(s0)
    s1_pooled = _pooled_probability_metrics(s1)

    fold_delta_ap = tuple(
        float(a.metrics["average_precision"] - b.metrics["average_precision"])
        for a, b in zip(s1, s0, strict=True)
    )
    fold_delta_auc = tuple(
        float(a.metrics["roc_auc"] - b.metrics["roc_auc"])
        for a, b in zip(s1, s0, strict=True)
    )

    loo: list[float] = []
    for omitted in range(4):
        s1_y = np.concatenate([f.y_true for i, f in enumerate(s1) if i != omitted])
        s1_p = np.concatenate([f.p_touch for i, f in enumerate(s1) if i != omitted])
        s0_y = np.concatenate([f.y_true for i, f in enumerate(s0) if i != omitted])
        s0_p = np.concatenate([f.p_touch for i, f in enumerate(s0) if i != omitted])
        if not np.array_equal(s1_y, s0_y):
            raise P4Error("loo_support_mismatch")
        loo.append(
            float(
                average_precision_score(s1_y, s1_p)
                - average_precision_score(s0_y, s0_p)
            )
        )

    prevalence = float(s1_pooled["touch_prevalence"])
    ap_lift_ratio = float(s1_pooled["average_precision"] / prevalence)
    brier_skill = float(1.0 - s1_pooled["brier"] / b0_pooled["brier"])

    gates = {
        "pooled_s1_auc_at_least_060": float(s1_pooled["roc_auc"]) >= 0.60,
        "pooled_ap_lift_at_least_150": ap_lift_ratio >= 1.50,
        "pooled_s1_minus_s0_ap_positive": (
            float(s1_pooled["average_precision"] - s0_pooled["average_precision"]) > 0
        ),
        "pooled_s1_minus_s0_auc_positive": (
            float(s1_pooled["roc_auc"] - s0_pooled["roc_auc"]) > 0
        ),
        "brier_skill_vs_prevalence_positive": brier_skill > 0,
        "at_least_3_of_4_fold_auc_gt_050": (
            sum(float(f.metrics["roc_auc"]) > 0.50 for f in s1) >= 3
        ),
        "at_least_3_of_4_fold_ap_gt_prevalence": (
            sum(
                float(f.metrics["average_precision"]) > float(f.prevalence)
                for f in s1
            ) >= 3
        ),
        "leave_one_fold_out_ap_delta_positive": all(value > 0 for value in loo),
    }

    return T2ModelResult(
        b0,
        s0,
        s1,
        b0_pooled,
        s0_pooled,
        s1_pooled,
        fold_delta_ap,
        fold_delta_auc,
        float(s1_pooled["average_precision"] - s0_pooled["average_precision"]),
        float(s1_pooled["roc_auc"] - s0_pooled["roc_auc"]),
        float(s0_pooled["brier"] - s1_pooled["brier"]),
        ap_lift_ratio,
        brier_skill,
        tuple(loo),
        gates,
        all(gates.values()),
    )


def eligible_shared_shifts(group_sizes: Sequence[int]) -> tuple[int, ...]:
    sizes = tuple(int(value) for value in group_sizes)
    if not sizes or any(value <= 0 for value in sizes):
        raise P4Error("invalid_null_group_sizes")
    return tuple(
        k
        for k in range(1, min(sizes))
        if all(min(k, n - k) >= 10 for n in sizes)
    )


def t2_temporal_null(
    folds: Sequence[ProbabilityFoldResult],
) -> T2TemporalNull:
    if len(folds) != 4:
        raise P4Error("outer_fold_count_mismatch")
    shifts = eligible_shared_shifts([len(f.y_true) for f in folds])
    if len(shifts) < 20:
        raise P4Error("insufficient_temporal_null_shifts")

    observed_y = np.concatenate([f.y_true for f in folds])
    observed_p = np.concatenate([f.p_touch for f in folds])
    observed_ap = float(average_precision_score(observed_y, observed_p))
    observed_auc = float(roc_auc_score(observed_y, observed_p))

    null_ap: list[float] = []
    null_auc: list[float] = []
    for k in shifts:
        shifted = np.concatenate([np.roll(f.y_true, k) for f in folds])
        null_ap.append(float(average_precision_score(shifted, observed_p)))
        null_auc.append(float(roc_auc_score(shifted, observed_p)))

    ap_q95 = float(np.quantile(np.asarray(null_ap), 0.95, method="higher"))
    auc_q95 = float(np.quantile(np.asarray(null_auc), 0.95, method="higher"))
    empirical_p = float(
        (1 + sum(value >= observed_ap for value in null_ap))
        / (1 + len(null_ap))
    )
    return T2TemporalNull(
        shifts,
        tuple(null_ap),
        tuple(null_auc),
        ap_q95,
        auc_q95,
        empirical_p,
        observed_ap,
        observed_auc,
        bool(observed_ap > ap_q95 and empirical_p <= 0.05),
    )


def t2_final_gates(
    result: T2ModelResult,
    null: T2TemporalNull | None,
) -> dict[str, bool]:
    gates = dict(result.precheck_gates)
    gates["temporal_null_run"] = null is not None
    gates["temporal_null_ap_gt_q95"] = bool(
        null is not None and null.observed_ap > null.ap_q95
    )
    gates["temporal_null_ap_p_le_005"] = bool(
        null is not None and null.empirical_ap_p <= 0.05
    )
    return gates


def t2_is_eligible(
    result: T2ModelResult,
    null: T2TemporalNull | None,
) -> bool:
    return all(t2_final_gates(result, null).values())


def fit_frozen_t1_fold(
    *,
    fold: dd.FrozenOuterFold,
    candidate_per_day: Mapping[date, dd.CandidateDayDataset],
) -> T1ReproductionFold:
    c_value = FROZEN_T1_C_BY_FOLD[fold.fold_id]

    def stack(days: Sequence[date]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        xs: list[np.ndarray] = []
        ys: list[np.ndarray] = []
        ts: list[np.ndarray] = []
        for day in days:
            dataset = candidate_per_day[day]
            mask = np.asarray(dataset.t1_common_valid, dtype=bool)
            xs.append(np.asarray(dataset.s1_values, dtype=np.float64)[mask])
            ys.append(np.asarray(dataset.t1_labels, dtype=np.int8)[mask])
            ts.append(np.asarray(dataset.decision_timestamps_us, dtype=np.int64)[mask])
        return np.concatenate(xs), np.concatenate(ys), np.concatenate(ts)

    x_train, y_train, _ = stack(fold.train_days)
    x_val, y_val, ts_val = stack((fold.validation_day,))
    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(x_train)
    val_scaled = scaler.transform(x_val)
    model = p3._new_logistic(c_value)
    model.fit(train_scaled, y_train)
    p_long = model.predict_proba(val_scaled)[:, 1]
    pred = (p_long >= p3.THRESHOLD).astype(np.int8)

    actual = p3.prediction_sha256(
        spec=p3.CandidateSpec("A", 120, 16, 32, "PRICE"),
        representation="S1",
        fold_id=fold.fold_id,
        timestamps_us=ts_val,
        y_true=y_val,
        y_pred=pred,
        p_long=p_long,
    )
    expected = FROZEN_T1_PREDICTION_SHA256_BY_FOLD[fold.fold_id]
    return T1ReproductionFold(
        fold.fold_id,
        c_value,
        expected,
        actual,
        actual == expected,
        scaler,
        model,
    )


def reproduce_frozen_t1(
    candidate_per_day: Mapping[date, dd.CandidateDayDataset],
) -> tuple[T1ReproductionFold, ...]:
    if tuple(candidate_per_day) != dd.HISTORICAL_DAYS:
        raise P4Error("t1_reproduction_day_order_mismatch")
    for dataset in candidate_per_day.values():
        validate_selected_candidate(dataset)
    results = tuple(
        fit_frozen_t1_fold(fold=fold, candidate_per_day=candidate_per_day)
        for fold in dd.OUTER_FOLDS
    )
    if not all(result.reproduced for result in results):
        raise P4Error("frozen_t1_prediction_hash_mismatch")
    return results


def compose_probabilities(
    p_touch: Any,
    p_long_given_touch: Any,
) -> np.ndarray:
    pt = np.asarray(p_touch, dtype=np.float64)
    pl = np.asarray(p_long_given_touch, dtype=np.float64)
    if pt.ndim != 1 or pl.ndim != 1 or len(pt) != len(pl):
        raise P4Error("composition_probability_shape_mismatch")
    if (
        not bool(np.all(np.isfinite(pt)))
        or not bool(np.all(np.isfinite(pl)))
        or not bool(np.all((pt >= 0) & (pt <= 1)))
        or not bool(np.all((pl >= 0) & (pl <= 1)))
    ):
        raise P4Error("invalid_composition_probability")
    p_none = 1.0 - pt
    p_long = pt * pl
    p_short = pt * (1.0 - pl)
    matrix = np.column_stack((p_none, p_short, p_long))
    if not bool(np.allclose(matrix.sum(axis=1), 1.0, rtol=0.0, atol=1e-12)):
        raise P4Error("composition_probability_sum_mismatch")
    return matrix


def three_class_labels(
    candidate_dataset: dd.CandidateDayDataset,
    t2_day: T2DayDataset,
) -> np.ndarray:
    labels: list[int] = []
    for include, record in zip(
        t2_day.valid_mask_on_candidate.tolist(),
        candidate_dataset.target_records,
        strict=True,
    ):
        if not include:
            continue
        mapped, _ = dd.map_t1_record(record)
        if mapped == dd.T1_SHORT:
            labels.append(1)
        elif mapped == dd.T1_LONG:
            labels.append(2)
        elif mapped is None and record["target_valid"] is True:
            labels.append(0)
        else:
            raise P4Error("three_class_label_mapping_failed")
    result = np.asarray(labels, dtype=np.int8)
    if len(result) != len(t2_day.labels):
        raise P4Error("three_class_support_mismatch")
    return result


def multiclass_probability_metrics(
    y_true: Any,
    probabilities: Any,
) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(probabilities, dtype=np.float64)
    if p.ndim != 2 or p.shape != (len(y), 3):
        raise P4Error("multiclass_probability_shape_mismatch")
    if not bool(np.all(np.isfinite(p))) or not bool(np.all((p >= 0) & (p <= 1))):
        raise P4Error("invalid_multiclass_probability")
    if not bool(np.allclose(p.sum(axis=1), 1.0, rtol=0.0, atol=1e-12)):
        raise P4Error("multiclass_probability_sum_mismatch")
    if not bool(np.all(np.isin(y, (0, 1, 2)))):
        raise P4Error("invalid_three_class_labels")

    onehot = np.eye(3, dtype=np.float64)[y]
    brier = float(np.mean(np.sum((p - onehot) ** 2, axis=1)))
    ap_values = []
    auc_values = []
    for cls in range(3):
        binary = (y == cls).astype(np.int8)
        if len(np.unique(binary)) != 2:
            raise P4Error("multiclass_metric_class_missing")
        ap_values.append(float(average_precision_score(binary, p[:, cls])))
        auc_values.append(float(roc_auc_score(binary, p[:, cls])))
    pred = np.argmax(p, axis=1).astype(np.int8)
    return {
        "support": int(len(y)),
        "multiclass_log_loss": float(log_loss(y, p, labels=[0, 1, 2])),
        "multiclass_brier": brier,
        "macro_ovr_average_precision": float(np.mean(ap_values)),
        "macro_ovr_roc_auc": float(np.mean(auc_values)),
        "per_class_average_precision": {
            "NONE": ap_values[0],
            "SHORT_FIRST": ap_values[1],
            "LONG_FIRST": ap_values[2],
        },
        "per_class_roc_auc": {
            "NONE": auc_values[0],
            "SHORT_FIRST": auc_values[1],
            "LONG_FIRST": auc_values[2],
        },
        "argmax_macro_f1": float(f1_score(y, pred, average="macro", zero_division=0)),
        "argmax_balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "argmax_confusion_matrix_none_short_long": confusion_matrix(
            y, pred, labels=[0, 1, 2]
        ).astype(int).tolist(),
    }


def directional_training_prevalence(
    candidate_per_day: Mapping[date, dd.CandidateDayDataset],
    days: Sequence[date],
) -> float:
    values: list[np.ndarray] = []
    for day in days:
        dataset = candidate_per_day[day]
        mask = np.asarray(dataset.t1_common_valid, dtype=bool)
        labels = np.asarray(dataset.t1_labels, dtype=np.int8)[mask]
        if len(labels):
            values.append(labels)
    if not values:
        raise P4Error("directional_training_support_empty")
    y = np.concatenate(values)
    return float(np.mean(y == dd.T1_LONG))


def composition_baselines(
    *,
    y_validation: np.ndarray,
    training_class_prevalence: np.ndarray,
    p_touch: np.ndarray,
    training_p_long_given_touch: float,
    p_long_given_touch: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    c0 = np.tile(training_class_prevalence, (len(y_validation), 1))
    c1 = compose_probabilities(
        p_touch,
        np.full(len(p_touch), training_p_long_given_touch, dtype=np.float64),
    )
    c2 = compose_probabilities(p_touch, p_long_given_touch)
    return c0, c1, c2



def _three_class_training_prevalence(
    candidate_per_day: Mapping[date, dd.CandidateDayDataset],
    t2_per_day: Mapping[date, T2DayDataset],
    days: Sequence[date],
) -> np.ndarray:
    labels = np.concatenate([
        three_class_labels(candidate_per_day[day], t2_per_day[day])
        for day in days
    ])
    counts = np.asarray([np.count_nonzero(labels == cls) for cls in (0, 1, 2)], dtype=np.float64)
    if counts.sum() <= 0:
        raise P4Error("three_class_training_support_empty")
    return counts / counts.sum()


def _pooled_multiclass(
    labels_by_fold: Sequence[np.ndarray],
    probabilities_by_fold: Sequence[np.ndarray],
) -> dict[str, Any]:
    return multiclass_probability_metrics(
        np.concatenate(labels_by_fold),
        np.concatenate(probabilities_by_fold),
    )


def evaluate_composition(
    *,
    candidate_per_day: Mapping[date, dd.CandidateDayDataset],
    t2_per_day: Mapping[date, T2DayDataset],
    t2_result: T2ModelResult,
    t1_reproduction: Sequence[T1ReproductionFold],
) -> CompositionResult:
    if len(t1_reproduction) != 4 or len(t2_result.s1_folds) != 4:
        raise P4Error("composition_outer_fold_count_mismatch")
    if not all(item.reproduced for item in t1_reproduction):
        raise P4Error("frozen_t1_prediction_hash_mismatch")

    folds: list[CompositionFoldResult] = []
    labels_by_fold: list[np.ndarray] = []
    c0_by_fold: list[np.ndarray] = []
    c1_by_fold: list[np.ndarray] = []
    c2_by_fold: list[np.ndarray] = []

    for outer, t2_fold, t1_fold in zip(
        dd.OUTER_FOLDS, t2_result.s1_folds, t1_reproduction, strict=True
    ):
        if outer.fold_id != t2_fold.fold_id or outer.fold_id != t1_fold.fold_id:
            raise P4Error("composition_fold_alignment_mismatch")
        t2_day = t2_per_day[outer.validation_day]
        candidate_day = candidate_per_day[outer.validation_day]
        if not np.array_equal(t2_day.timestamps_us, t2_fold.timestamps_us):
            raise P4Error("composition_timestamp_alignment_mismatch")

        x_s1 = np.asarray(t2_day.s1_values, dtype=np.float64)
        p_long = t1_fold.model.predict_proba(t1_fold.scaler.transform(x_s1))[:, 1]
        y3 = three_class_labels(candidate_day, t2_day)
        train_prev3 = _three_class_training_prevalence(
            candidate_per_day, t2_per_day, outer.train_days
        )
        train_p_long = directional_training_prevalence(
            candidate_per_day, outer.train_days
        )
        c0, c1, c2 = composition_baselines(
            y_validation=y3,
            training_class_prevalence=train_prev3,
            p_touch=t2_fold.p_touch,
            training_p_long_given_touch=train_p_long,
            p_long_given_touch=p_long,
        )
        m0 = multiclass_probability_metrics(y3, c0)
        m1 = multiclass_probability_metrics(y3, c1)
        m2 = multiclass_probability_metrics(y3, c2)
        folds.append(
            CompositionFoldResult(
                fold_id=outer.fold_id,
                support=int(len(y3)),
                metrics_c0=m0,
                metrics_c1=m1,
                metrics_c2=m2,
                log_loss_improvement_vs_c1=float(
                    m1["multiclass_log_loss"] - m2["multiclass_log_loss"]
                ),
            )
        )
        labels_by_fold.append(y3)
        c0_by_fold.append(c0)
        c1_by_fold.append(c1)
        c2_by_fold.append(c2)

    pooled_c0 = _pooled_multiclass(labels_by_fold, c0_by_fold)
    pooled_c1 = _pooled_multiclass(labels_by_fold, c1_by_fold)
    pooled_c2 = _pooled_multiclass(labels_by_fold, c2_by_fold)

    loo: list[float] = []
    for omitted in range(4):
        labels = [value for i, value in enumerate(labels_by_fold) if i != omitted]
        c1s = [value for i, value in enumerate(c1_by_fold) if i != omitted]
        c2s = [value for i, value in enumerate(c2_by_fold) if i != omitted]
        m1 = _pooled_multiclass(labels, c1s)
        m2 = _pooled_multiclass(labels, c2s)
        loo.append(float(m1["multiclass_log_loss"] - m2["multiclass_log_loss"]))

    gates = {
        "t1_reproduced_all_folds": all(item.reproduced for item in t1_reproduction),
        "pooled_log_loss_better_than_c1": (
            float(pooled_c2["multiclass_log_loss"]) < float(pooled_c1["multiclass_log_loss"])
        ),
        "pooled_brier_better_than_c1": (
            float(pooled_c2["multiclass_brier"]) < float(pooled_c1["multiclass_brier"])
        ),
        "pooled_macro_ap_better_than_c1": (
            float(pooled_c2["macro_ovr_average_precision"]) >
            float(pooled_c1["macro_ovr_average_precision"])
        ),
        "at_least_3_of_4_fold_log_loss_improve": (
            sum(item.log_loss_improvement_vs_c1 > 0 for item in folds) >= 3
        ),
        "leave_one_fold_out_log_loss_improvement_positive": all(value > 0 for value in loo),
    }
    return CompositionResult(
        tuple(folds),
        pooled_c0,
        pooled_c1,
        pooled_c2,
        tuple(loo),
        gates,
        all(gates.values()),
    )


def composition_is_eligible(
    *,
    t2_result: T2ModelResult,
    t2_null: T2TemporalNull | None,
    composition_result: CompositionResult | None,
) -> bool:
    if not t2_is_eligible(t2_result, t2_null):
        return False
    return bool(
        composition_result is not None
        and composition_result.eligible_for_later_policy_design
    )


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    def normalize(value: Any) -> Any:
        if value is None or type(value) in (str, bool, int):
            return value
        if type(value) is float:
            if not math.isfinite(value):
                raise P4Error("non_finite_json_value")
            return value
        if isinstance(value, np.generic):
            return normalize(value.item())
        if isinstance(value, np.ndarray):
            return [normalize(item) for item in value.tolist()]
        if isinstance(value, Mapping):
            if not all(isinstance(key, str) for key in value):
                raise P4Error("json_mapping_key_not_string")
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, date):
            return value.isoformat()
        raise P4Error("unsupported_json_value", type(value).__name__)

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


def write_result_once(
    output_directory: Path,
    payload: Mapping[str, Any],
    *,
    require_canonical_output: bool = True,
) -> ArtifactWriteResult:
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise P4Error("output_directory_already_exists")
    if not require_canonical_output and output == REAL_OUTPUT_DIRECTORY:
        raise P4Error("canonical_output_requires_real_mode")
    if require_canonical_output and output != REAL_OUTPUT_DIRECTORY:
        raise P4Error("noncanonical_output_directory")

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
            raise P4Error("artifact_cleanup_failed", str(cleanup_exc)) from cleanup_exc
        if isinstance(exc, P4Error):
            raise
        raise P4Error("artifact_write_failed", str(exc)) from exc
    return ArtifactWriteResult(
        output,
        final,
        hashlib.sha256(content).hexdigest(),
        len(content),
    )


def _fold_probability_public(fold: ProbabilityFoldResult) -> dict[str, Any]:
    return {
        "fold_id": fold.fold_id,
        "selected_C": fold.selected_c,
        "support": fold.support,
        "touch_count": fold.touch_count,
        "none_count": fold.none_count,
        "prevalence": fold.prevalence,
        "metrics": fold.metrics,
        "prediction_sha256": fold.prediction_sha256,
        "inner_c_ledger": [dict(item) for item in fold.inner_c_ledger],
    }


def _t2_public(
    result: T2ModelResult,
    null: T2TemporalNull | None,
) -> dict[str, Any]:
    return {
        "b0": {
            "folds": [_fold_probability_public(f) for f in result.b0_folds],
            "pooled": result.b0_pooled,
        },
        "s0": {
            "folds": [_fold_probability_public(f) for f in result.s0_folds],
            "pooled": result.s0_pooled,
        },
        "s1": {
            "folds": [_fold_probability_public(f) for f in result.s1_folds],
            "pooled": result.s1_pooled,
        },
        "fold_delta_ap": list(result.fold_delta_ap),
        "fold_delta_auc": list(result.fold_delta_auc),
        "pooled_delta_ap": result.pooled_delta_ap,
        "pooled_delta_auc": result.pooled_delta_auc,
        "pooled_delta_brier": result.pooled_delta_brier,
        "ap_lift_ratio": result.ap_lift_ratio,
        "brier_skill_vs_prevalence": result.brier_skill_vs_prevalence,
        "leave_one_fold_out_delta_ap": list(result.leave_one_fold_out_delta_ap),
        "precheck_gates": dict(result.precheck_gates),
        "precheck_pass": result.precheck_pass,
        "temporal_null": (
            {
                "eligible_shifts": list(null.eligible_shifts),
                "null_ap": list(null.null_ap),
                "null_auc": list(null.null_auc),
                "ap_q95": null.ap_q95,
                "auc_q95": null.auc_q95,
                "empirical_ap_p": null.empirical_ap_p,
                "observed_ap": null.observed_ap,
                "observed_auc": null.observed_auc,
                "pass_gate": null.pass_gate,
            }
            if null is not None
            else {"status": "TEMPORAL_NULL_NOT_RUN_PRECHECK_FAILED"}
        ),
        "promotion_gates": t2_final_gates(result, null),
        "eligible_for_composition": t2_is_eligible(result, null),
    }


def _composition_public(
    result: CompositionResult | None,
) -> dict[str, Any]:
    if result is None:
        return {"status": "COMPOSITION_NOT_RUN_T2_NOT_ELIGIBLE"}
    return {
        "status": (
            "ELIGIBLE_FOR_LATER_POLICY_DESIGN"
            if result.eligible_for_later_policy_design
            else "FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE"
        ),
        "folds": [
            {
                "fold_id": f.fold_id,
                "support": f.support,
                "metrics_c0": f.metrics_c0,
                "metrics_c1": f.metrics_c1,
                "metrics_c2": f.metrics_c2,
                "log_loss_improvement_vs_c1": f.log_loss_improvement_vs_c1,
            }
            for f in result.folds
        ],
        "pooled_c0": result.pooled_c0,
        "pooled_c1": result.pooled_c1,
        "pooled_c2": result.pooled_c2,
        "leave_one_fold_out_log_loss_improvement": list(
            result.leave_one_fold_out_log_loss_improvement
        ),
        "gates": dict(result.gates),
        "eligible_for_later_policy_design": result.eligible_for_later_policy_design,
    }


def run_p4(
    *,
    workspace: Path,
    output_directory: Path,
    execution_commit: str,
    require_canonical_output: bool = True,
    dependency_verifier: Any = verify_frozen_dependencies,
    p2c_loader: Any = None,
    p3_loader: Any = None,
    manifest_verifier: Any = dd.verify_input_manifest,
    analytical_day_loader: Any = dd.load_authorized_days,
) -> ArtifactWriteResult:
    """Run the separately-authorized real P4 development campaign."""

    supplied_p2c_loader = p2c_loader
    supplied_p3_loader = p3_loader
    if p2c_loader is None:
        p2c_loader = lambda: load_verified_json_artifact(
            P2C_ARTIFACT_PATH, P2C_ARTIFACT_SHA256
        )
    if p3_loader is None:
        p3_loader = lambda: load_verified_json_artifact(
            P3_ARTIFACT_PATH, P3_ARTIFACT_SHA256
        )

    output = Path(output_directory)
    if require_canonical_output:
        if supplied_p2c_loader is not None:
            raise P4Error("canonical_dependency_override_forbidden", "p2c_loader")
        if supplied_p3_loader is not None:
            raise P4Error("canonical_dependency_override_forbidden", "p3_loader")
        if output != REAL_OUTPUT_DIRECTORY:
            raise P4Error("noncanonical_output_directory")
        if dependency_verifier is not verify_frozen_dependencies:
            raise P4Error("canonical_dependency_override_forbidden", "dependency_verifier")
        if manifest_verifier is not dd.verify_input_manifest:
            raise P4Error("canonical_dependency_override_forbidden", "manifest_verifier")
        if analytical_day_loader is not dd.load_authorized_days:
            raise P4Error("canonical_dependency_override_forbidden", "analytical_day_loader")
    elif output == REAL_OUTPUT_DIRECTORY:
        raise P4Error("canonical_output_requires_real_mode")

    if output.exists() or output.is_symlink():
        raise P4Error("output_directory_already_exists")

    execution_sha = _validate_execution_commit(execution_commit)
    dependency_hashes = dict(dependency_verifier(Path(workspace)))
    p2c_payload = dict(p2c_loader())
    p3_payload = dict(p3_loader())
    validate_p3_selected_survivor(p3_payload)

    manifest = tuple(manifest_verifier())
    loaded_days = tuple(analytical_day_loader())
    if tuple(day.day for day in loaded_days) != dd.HISTORICAL_DAYS:
        raise P4Error("loaded_day_calendar_mismatch")

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
        raise P4Error("selected_candidate_day_order_mismatch")
    reconcile_selected_candidate_with_p2c(candidate_per_day, p2c_payload)

    t2_per_day = {
        day: build_t2_day(candidate_per_day[day])
        for day in dd.HISTORICAL_DAYS
    }
    t2_result = fit_t2(t2_per_day)
    t2_null: T2TemporalNull | None = None
    if t2_result.precheck_pass:
        try:
            t2_null = t2_temporal_null(t2_result.s1_folds)
        except P4Error as exc:
            if exc.reason != "insufficient_temporal_null_shifts":
                raise

    t1_reproduction: tuple[T1ReproductionFold, ...] = ()
    composition_result: CompositionResult | None = None
    if t2_is_eligible(t2_result, t2_null):
        t1_reproduction = reproduce_frozen_t1(candidate_per_day)
        composition_result = evaluate_composition(
            candidate_per_day=candidate_per_day,
            t2_per_day=t2_per_day,
            t2_result=t2_result,
            t1_reproduction=t1_reproduction,
        )

    final_status = (
        "ELIGIBLE_FOR_LATER_POLICY_DESIGN"
        if composition_is_eligible(
            t2_result=t2_result,
            t2_null=t2_null,
            composition_result=composition_result,
        )
        else (
            "FAIL_T2_TOUCH_NOT_STABLE"
            if not t2_is_eligible(t2_result, t2_null)
            else "FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE"
        )
    )
    runtime = runtime_provenance(
        model_fit_run=True,
        t2_run=True,
        composition_run=composition_result is not None,
    )
    validate_runtime_provenance(runtime)

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "status": final_status,
        "execution_commit": execution_sha,
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "dependency_sha256": dict(sorted(dependency_hashes.items())),
        "frozen_artifacts": {
            "p2c": {"path": str(P2C_ARTIFACT_PATH), "sha256": P2C_ARTIFACT_SHA256},
            "p3": {"path": str(P3_ARTIFACT_PATH), "sha256": P3_ARTIFACT_SHA256},
        },
        "selected_configuration": {
            "target": {"target_id": "A", "horizon_seconds": 120, "barrier_bps": 16},
            "window_seconds": 32,
            "block": "PRICE",
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
        "t2_support": [
            {
                "date": day.isoformat(),
                "support": int(len(t2_per_day[day].labels)),
                "touch_count": int(t2_per_day[day].touch_count),
                "none_count": int(t2_per_day[day].none_count),
                "support_sha256": t2_per_day[day].support_sha256,
            }
            for day in dd.HISTORICAL_DAYS
        ],
        "t2": _t2_public(t2_result, t2_null),
        "t1_reproduction": [
            {
                "fold_id": item.fold_id,
                "selected_C": item.selected_c,
                "expected_prediction_sha256": item.expected_prediction_sha256,
                "actual_prediction_sha256": item.actual_prediction_sha256,
                "reproduced": item.reproduced,
            }
            for item in t1_reproduction
        ],
        "composition": _composition_public(composition_result),
        "runtime_provenance": runtime,
        "prohibited_activity": {
            "threshold_optimization": False,
            "pnl": False,
            "economics": False,
            "opportunity_gate": False,
            "forward_data": False,
            "m2_or_deep_model": False,
        },
    }
    return write_result_once(
        output,
        payload,
        require_canonical_output=require_canonical_output,
    )


__all__ = [
    "C_GRID",
    "DESIGN_VERSION",
    "EXPERIMENT_ID",
    "FROZEN_T1_C_BY_FOLD",
    "FROZEN_T1_PREDICTION_SHA256_BY_FOLD",
    "P3_ARTIFACT_SHA256",
    "SELECTED_BLOCK",
    "SELECTED_KEY",
    "SELECTED_TARGET",
    "SELECTED_WINDOW_SECONDS",
    "THRESHOLD",
    "ArtifactWriteResult",
    "CompositionFoldResult",
    "CompositionResult",
    "P4Error",
    "ProbabilityFoldResult",
    "T1ReproductionFold",
    "T2DayDataset",
    "T2ModelResult",
    "T2TemporalNull",
    "build_t2_day",
    "composition_is_eligible",
    "canonical_json_bytes",
    "compose_probabilities",
    "composition_baselines",
    "directional_training_prevalence",
    "evaluate_composition",
    "eligible_shared_shifts",
    "fit_frozen_t1_fold",
    "fit_probability_fold",
    "fit_t2",
    "load_verified_json_artifact",
    "multiclass_probability_metrics",
    "probability_metrics",
    "reconcile_selected_candidate_with_p2c",
    "reproduce_frozen_t1",
    "run_p4",
    "runtime_provenance",
    "select_c",
    "t2_final_gates",
    "t2_is_eligible",
    "t2_temporal_null",
    "three_class_labels",
    "validate_p3_selected_survivor",
    "validate_runtime_provenance",
    "validate_selected_candidate",
    "verify_frozen_dependencies",
    "write_result_once",
]

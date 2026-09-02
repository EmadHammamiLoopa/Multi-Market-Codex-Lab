from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import struct
from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
    matthews_corrcoef,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

EXPERIMENT_ID = "DEV032-E1B"
DESIGN_VERSION = "broad-predictive-screen-v1"

C_GRID = (0.01, 0.1, 1.0, 10.0)
RANDOM_STATE = 20260825
THRESHOLD = 0.5
NULL_SEED = 20260902
NULL_REPLICATES = 1999

STATUS_STRONG = "STRONG_SCREENING_SURVIVOR"
STATUS_INCONCLUSIVE = "SCREENING_INCONCLUSIVE"
STATUS_REJECTED = "SCREENING_REJECTED"

class E1BScreenError(RuntimeError):
    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")

@dataclass(frozen=True)
class DayMatrix:
    day: date
    timestamps_us: np.ndarray
    labels: np.ndarray
    values: np.ndarray

@dataclass(frozen=True)
class FoldSpec:
    fold_id: int
    train_days: tuple[date, ...]
    validation_day: date

@dataclass(frozen=True)
class FoldPrediction:
    fold_id: int
    representation: str
    selected_c: float
    timestamps_us: np.ndarray
    labels: np.ndarray
    probabilities: np.ndarray
    metrics: dict[str, Any]
    inner_c_ledger: tuple[dict[str, float], ...]
    prediction_sha256: str

@dataclass(frozen=True)
class RepresentationResult:
    representation: str
    feature_count: int
    folds: tuple[FoldPrediction, ...]
    pooled_metrics: dict[str, Any]

def probability_metrics(y: Any, p: Any) -> dict[str, Any]:
    y = np.asarray(y, dtype=np.int8)
    p = np.asarray(p, dtype=np.float64)
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p) or len(y) == 0:
        raise E1BScreenError("metric_shape")
    if set(np.unique(y).tolist()) != {0, 1}:
        raise E1BScreenError("metric_classes")
    if not np.all(np.isfinite(p)) or not np.all((p >= 0.0) & (p <= 1.0)):
        raise E1BScreenError("metric_probability")
    pred = (p >= THRESHOLD).astype(np.int8)
    return {
        "support": int(len(y)),
        "long_count": int(np.sum(y == 1)),
        "short_count": int(np.sum(y == 0)),
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
    }

def prediction_sha256(
    fold_id: int,
    representation: str,
    timestamps_us: Any,
    labels: Any,
    probabilities: Any,
) -> str:
    ts = np.asarray(timestamps_us, dtype=np.int64)
    y = np.asarray(labels, dtype=np.int8)
    p = np.asarray(probabilities, dtype=np.float64)
    if not (len(ts) == len(y) == len(p)):
        raise E1BScreenError("prediction_hash_shape")
    h = hashlib.sha256(b"DEV032-E1B-OOF-PREDICTION-V1\0")
    h.update(f"{fold_id}|{representation}".encode("ascii"))
    for t, v, q in zip(ts.tolist(), y.tolist(), p.tolist(), strict=True):
        h.update(struct.pack(">qbd", int(t), int(v), float(q)))
    return h.hexdigest()

def _validate_day(day: DayMatrix) -> DayMatrix:
    ts = np.asarray(day.timestamps_us, dtype=np.int64)
    y = np.asarray(day.labels, dtype=np.int8)
    x = np.asarray(day.values, dtype=np.float64)
    if ts.ndim != 1 or y.ndim != 1 or x.ndim != 2:
        raise E1BScreenError("day_shape", day.day.isoformat())
    if len(ts) == 0 or len(ts) != len(y) or len(ts) != x.shape[0]:
        raise E1BScreenError("day_length", day.day.isoformat())
    if np.any(np.diff(ts) <= 0):
        raise E1BScreenError("day_chronology", day.day.isoformat())
    if not np.all(np.isin(y, (0, 1))):
        raise E1BScreenError("day_labels", day.day.isoformat())
    if not np.all(np.isfinite(x)):
        raise E1BScreenError("day_nonfinite", day.day.isoformat())
    return DayMatrix(day.day, ts, y, x)

def stack_days(
    per_day: Mapping[date, DayMatrix],
    days: Sequence[date],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    ts: list[np.ndarray] = []
    width: int | None = None
    for d in days:
        if d not in per_day:
            raise E1BScreenError("missing_day", d.isoformat())
        z = _validate_day(per_day[d])
        if width is None:
            width = z.values.shape[1]
        elif z.values.shape[1] != width:
            raise E1BScreenError("feature_width_changes", d.isoformat())
        xs.append(z.values)
        ys.append(z.labels)
        ts.append(z.timestamps_us)
    x = np.concatenate(xs, axis=0)
    y = np.concatenate(ys)
    t = np.concatenate(ts)
    if len(t) and np.any(np.diff(t) <= 0):
        raise E1BScreenError("stack_chronology")
    return x, y, t

def _new_model(c_value: float) -> LogisticRegression:
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
) -> tuple[float, tuple[dict[str, float], ...]]:
    xf = np.asarray(x_fit, dtype=np.float64)
    yf = np.asarray(y_fit, dtype=np.int8)
    xv = np.asarray(x_validation, dtype=np.float64)
    yv = np.asarray(y_validation, dtype=np.int8)
    ledger: list[dict[str, float]] = []
    for c_value in C_GRID:
        scaler = StandardScaler()
        a = scaler.fit_transform(xf)
        b = scaler.transform(xv)
        model = _new_model(c_value)
        model.fit(a, yf)
        p = model.predict_proba(b)[:, 1]
        q = probability_metrics(yv, p)
        ledger.append(
            {
                "C": float(c_value),
                "binary_log_loss": float(q["binary_log_loss"]),
                "brier": float(q["brier"]),
                "roc_auc": float(q["roc_auc"]),
            }
        )
    winner = sorted(
        ledger,
        key=lambda q: (
            q["binary_log_loss"],
            q["brier"],
            -q["roc_auc"],
            q["C"],
        ),
    )[0]
    return float(winner["C"]), tuple(ledger)

def fit_fold(
    per_day: Mapping[date, DayMatrix],
    fold: FoldSpec,
    representation: str,
) -> FoldPrediction:
    if len(fold.train_days) < 2:
        raise E1BScreenError("inner_split_requires_two_train_days")
    inner_validation_day = fold.train_days[-1]
    inner_fit_days = fold.train_days[:-1]
    xif, yif, _ = stack_days(per_day, inner_fit_days)
    xiv, yiv, _ = stack_days(per_day, (inner_validation_day,))
    xt, yt, _ = stack_days(per_day, fold.train_days)
    xv, yv, tv = stack_days(per_day, (fold.validation_day,))
    c_value, ledger = select_c(xif, yif, xiv, yiv)
    scaler = StandardScaler()
    a = scaler.fit_transform(xt)
    b = scaler.transform(xv)
    model = _new_model(c_value)
    model.fit(a, yt)
    p = model.predict_proba(b)[:, 1]
    return FoldPrediction(
        fold_id=int(fold.fold_id),
        representation=str(representation),
        selected_c=float(c_value),
        timestamps_us=tv,
        labels=yv,
        probabilities=p,
        metrics=probability_metrics(yv, p),
        inner_c_ledger=ledger,
        prediction_sha256=prediction_sha256(
            fold.fold_id, representation, tv, yv, p
        ),
    )

def fit_representation(
    per_day: Mapping[date, DayMatrix],
    folds: Sequence[FoldSpec],
    representation: str,
) -> RepresentationResult:
    fold_results = tuple(
        fit_fold(per_day, f, representation) for f in folds
    )
    if len(fold_results) != 4:
        raise E1BScreenError("outer_fold_count")
    y = np.concatenate([f.labels for f in fold_results])
    p = np.concatenate([f.probabilities for f in fold_results])
    widths = {per_day[d].values.shape[1] for d in per_day}
    if len(widths) != 1:
        raise E1BScreenError("feature_width_changes")
    return RepresentationResult(
        representation=str(representation),
        feature_count=int(next(iter(widths))),
        folds=fold_results,
        pooled_metrics=probability_metrics(y, p),
    )

def compare_to_baseline(
    baseline: RepresentationResult,
    candidate: RepresentationResult,
) -> dict[str, Any]:
    if len(baseline.folds) != 4 or len(candidate.folds) != 4:
        raise E1BScreenError("outer_fold_count")
    fold_auc_delta: list[float] = []
    fold_log_loss_improvement: list[float] = []
    fold_brier_improvement: list[float] = []
    for b, c in zip(baseline.folds, candidate.folds, strict=True):
        if b.fold_id != c.fold_id:
            raise E1BScreenError("fold_id_mismatch")
        if not np.array_equal(b.timestamps_us, c.timestamps_us):
            raise E1BScreenError("matched_support")
        if not np.array_equal(b.labels, c.labels):
            raise E1BScreenError("matched_labels")
        fold_auc_delta.append(
            float(c.metrics["roc_auc"] - b.metrics["roc_auc"])
        )
        fold_log_loss_improvement.append(
            float(b.metrics["binary_log_loss"] - c.metrics["binary_log_loss"])
        )
        fold_brier_improvement.append(
            float(b.metrics["brier"] - c.metrics["brier"])
        )

    loo_auc_delta: list[float] = []
    for omitted in range(4):
        y = np.concatenate(
            [
                baseline.folds[i].labels
                for i in range(4)
                if i != omitted
            ]
        )
        pb = np.concatenate(
            [
                baseline.folds[i].probabilities
                for i in range(4)
                if i != omitted
            ]
        )
        pc = np.concatenate(
            [
                candidate.folds[i].probabilities
                for i in range(4)
                if i != omitted
            ]
        )
        loo_auc_delta.append(
            float(roc_auc_score(y, pc) - roc_auc_score(y, pb))
        )

    return {
        "pooled_auc_delta": float(
            candidate.pooled_metrics["roc_auc"]
            - baseline.pooled_metrics["roc_auc"]
        ),
        "pooled_log_loss_improvement": float(
            baseline.pooled_metrics["binary_log_loss"]
            - candidate.pooled_metrics["binary_log_loss"]
        ),
        "pooled_brier_improvement": float(
            baseline.pooled_metrics["brier"]
            - candidate.pooled_metrics["brier"]
        ),
        "fold_auc_delta": fold_auc_delta,
        "fold_log_loss_improvement": fold_log_loss_improvement,
        "fold_brier_improvement": fold_brier_improvement,
        "positive_fold_auc_deltas": int(sum(v > 0.0 for v in fold_auc_delta)),
        "candidate_fold_auc_gt_0_5": int(
            sum(f.metrics["roc_auc"] > 0.5 for f in candidate.folds)
        ),
        "leave_one_fold_out_auc_delta": loo_auc_delta,
        "all_loo_auc_delta_positive": bool(all(v > 0.0 for v in loo_auc_delta)),
        "worst_fold_auc": float(
            min(f.metrics["roc_auc"] for f in candidate.folds)
        ),
    }

def _legal_shifts(n: int) -> np.ndarray:
    if n < 21:
        raise E1BScreenError("validation_fold_too_small_for_null")
    values = np.arange(10, n - 9, dtype=np.int64)
    if len(values) == 0:
        raise E1BScreenError("no_legal_null_shift")
    return values

def temporal_max_stat_null(
    baseline: RepresentationResult,
    candidates: Mapping[str, RepresentationResult],
    *,
    seed: int = NULL_SEED,
    replicates: int = NULL_REPLICATES,
) -> dict[str, Any]:
    if replicates <= 0:
        raise E1BScreenError("null_replicates")
    ids = tuple(candidates)
    if len(ids) == 0:
        raise E1BScreenError("null_candidates_empty")
    if len(set(ids)) != len(ids):
        raise E1BScreenError("null_candidate_duplicate")
    if len(baseline.folds) != 4:
        raise E1BScreenError("outer_fold_count")
    for sid in ids:
        c = candidates[sid]
        if len(c.folds) != 4:
            raise E1BScreenError("outer_fold_count")
        for b, z in zip(baseline.folds, c.folds, strict=True):
            if not np.array_equal(b.timestamps_us, z.timestamps_us):
                raise E1BScreenError("matched_support", sid)
            if not np.array_equal(b.labels, z.labels):
                raise E1BScreenError("matched_labels", sid)

    fold_sizes = [len(f.labels) for f in baseline.folds]
    legal = [_legal_shifts(n) for n in fold_sizes]
    baseline_p = np.concatenate([f.probabilities for f in baseline.folds])
    candidate_p = {
        sid: np.concatenate([f.probabilities for f in candidates[sid].folds])
        for sid in ids
    }
    observed = {
        sid: float(
            candidates[sid].pooled_metrics["roc_auc"]
            - baseline.pooled_metrics["roc_auc"]
        )
        for sid in ids
    }

    rng = np.random.default_rng(seed)
    candidate_null = {
        sid: np.empty(replicates, dtype=np.float64) for sid in ids
    }
    max_null = np.empty(replicates, dtype=np.float64)
    shift_tuples: list[list[int]] = []

    for r in range(replicates):
        shifts = [
            int(legal[i][rng.integers(0, len(legal[i]))])
            for i in range(4)
        ]
        shift_tuples.append(shifts)
        shifted_y = np.concatenate(
            [
                np.roll(baseline.folds[i].labels, shifts[i])
                for i in range(4)
            ]
        )
        auc_b = float(roc_auc_score(shifted_y, baseline_p))
        row_max = -np.inf
        for sid in ids:
            delta = float(roc_auc_score(shifted_y, candidate_p[sid]) - auc_b)
            candidate_null[sid][r] = delta
            if delta > row_max:
                row_max = delta
        max_null[r] = row_max

    q95 = float(np.quantile(max_null, 0.95, method="higher"))
    per_candidate: dict[str, Any] = {}
    for sid in ids:
        obs = observed[sid]
        raw_p = float(
            (1 + int(np.sum(candidate_null[sid] >= obs)))
            / (1 + replicates)
        )
        fwer_p = float(
            (1 + int(np.sum(max_null >= obs)))
            / (1 + replicates)
        )
        per_candidate[sid] = {
            "observed_pooled_auc_delta": obs,
            "raw_empirical_p": raw_p,
            "max_stat_fwer_empirical_p": fwer_p,
            "max_stat_q95": q95,
            "observed_minus_q95": float(obs - q95),
        }

    return {
        "seed": int(seed),
        "replicates": int(replicates),
        "candidate_ids": list(ids),
        "fold_sizes": fold_sizes,
        "max_stat_q95": q95,
        "max_stat_null": max_null.tolist(),
        "shift_tuples": shift_tuples,
        "per_candidate": per_candidate,
    }

def legacy_common_shift_audit(
    baseline: RepresentationResult,
    candidates: Mapping[str, RepresentationResult],
) -> dict[str, Any]:
    sizes = [len(f.labels) for f in baseline.folds]
    max_common = min(sizes)
    shifts = [
        k for k in range(1, max_common)
        if all(min(k, n - k) >= 10 for n in sizes)
    ]
    if not shifts:
        raise E1BScreenError("legacy_null_no_shifts")
    baseline_p = np.concatenate([f.probabilities for f in baseline.folds])
    candidate_p = {
        sid: np.concatenate([f.probabilities for f in z.folds])
        for sid, z in candidates.items()
    }
    records: list[dict[str, Any]] = []
    for k in shifts:
        y = np.concatenate(
            [np.roll(f.labels, k) for f in baseline.folds]
        )
        auc_b = float(roc_auc_score(y, baseline_p))
        deltas = {
            sid: float(roc_auc_score(y, p) - auc_b)
            for sid, p in candidate_p.items()
        }
        records.append(
            {
                "shift": int(k),
                "candidate_auc_delta": deltas,
                "max_auc_delta": float(max(deltas.values())),
            }
        )
    return {"eligible_shifts": shifts, "records": records}

def classify_candidate(
    candidate: RepresentationResult,
    comparison: Mapping[str, Any],
    null_record: Mapping[str, Any],
) -> str:
    pooled_auc = float(candidate.pooled_metrics["roc_auc"])
    pooled_delta = float(comparison["pooled_auc_delta"])
    stable = (
        pooled_delta > 0.0
        and int(comparison["positive_fold_auc_deltas"]) >= 3
        and bool(comparison["all_loo_auc_delta_positive"])
    )
    strong = (
        stable
        and pooled_auc >= 0.56
        and int(comparison["candidate_fold_auc_gt_0_5"]) >= 3
        and pooled_delta > float(null_record["max_stat_q95"])
        and float(null_record["max_stat_fwer_empirical_p"]) <= 0.05
    )
    if strong:
        return STATUS_STRONG
    if stable:
        return STATUS_INCONCLUSIVE
    return STATUS_REJECTED

def leaderboard_rows(
    baseline: RepresentationResult,
    candidates: Mapping[str, RepresentationResult],
    null_result: Mapping[str, Any],
    *,
    family_by_candidate: Mapping[str, str],
) -> list[dict[str, Any]]:
    if tuple(candidates) != tuple(null_result["candidate_ids"]):
        raise E1BScreenError("leaderboard_null_order")
    rows: list[dict[str, Any]] = []
    for sid, candidate in candidates.items():
        comp = compare_to_baseline(baseline, candidate)
        null_rec = null_result["per_candidate"][sid]
        status = classify_candidate(candidate, comp, null_rec)
        rows.append(
            {
                "candidate_id": sid,
                "family": family_by_candidate[sid],
                "status": status,
                "feature_count": int(candidate.feature_count),
                "pooled_metrics": dict(candidate.pooled_metrics),
                "comparison_vs_b00": comp,
                "null": dict(null_rec),
                "folds": [
                    {
                        "fold_id": f.fold_id,
                        "selected_C": f.selected_c,
                        "metrics": dict(f.metrics),
                        "prediction_sha256": f.prediction_sha256,
                        "inner_c_ledger": list(f.inner_c_ledger),
                    }
                    for f in candidate.folds
                ],
            }
        )
    status_rank = {
        STATUS_STRONG: 0,
        STATUS_INCONCLUSIVE: 1,
        STATUS_REJECTED: 2,
    }
    rows.sort(
        key=lambda row: (
            status_rank[row["status"]],
            row["null"]["max_stat_fwer_empirical_p"],
            -row["comparison_vs_b00"]["pooled_auc_delta"],
            -row["comparison_vs_b00"]["worst_fold_auc"],
            row["feature_count"],
            row["candidate_id"],
        )
    )
    return rows

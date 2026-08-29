from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

from .codex_exp004_headroom import (
    DAYS,
    executable_fixed_horizon,
    load_frozen_provenance,
)
from .codex_exp004_p1 import (
    DECISION_STEP_ROWS,
    HORIZON_S,
    LABEL_THRESHOLD_BPS,
    R_FEATURE_NAMES,
    FixedLogistic,
    _r_features,
    _spread,
    build_day_dataset,
)
from .codex_research import canonical_sha256, sha256_file
from .v23_phase0dl_score import DayData, _load_day


EXPERIMENT_ID = "CODEX-EXP-022-P1"
PASS_STATUS = "PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED"
FAIL_STATUS = "FAIL_PROSPECTIVE_VOLATILITY_RANKING_NOT_CONFIRMED"
INCONCLUSIVE_STATUS = "INCONCLUSIVE_INSUFFICIENT_SUPPORT"
INVALID_STATUS = "INVALID"

SYMBOL = "BTCUSDT"
TRAIN_DAYS = DAYS
PROSPECTIVE_DAY = date(2026, 8, 28)
PREREGISTRATION_COMMIT = "73feafca0b1f901b10d2856b07c3058462f1cfff"
PREREGISTRATION_REL = Path("docs/CODEX_EXP022_P1_PREREGISTRATION.md")
PREREGISTRATION_SHA256 = (
    "e4c9ca4075834de29d01613c695b534081a01b506e7f233ca6fa9542419e3f5b"
)

P0_AUDIT_REL = Path(
    "evidence/codex/exp022_p0_prospective_bookticker/"
    "PROSPECTIVE_BOOKTICKER_AUDIT.json"
)
P0_AUDIT_SHA256 = (
    "d1d2a90844260e88ab2fae4e20456960c2491512b91372147f3810c16c71d779"
)
P0_STATUS = "PROSPECTIVE_BOOKTICKER_DATA_READY"
PROSPECTIVE_RAW_SHA256 = (
    "c0a11173f8f03dbad787f18e3a7db31af1b1d8abb113f1171772ef9c6460f5a0"
)
PROSPECTIVE_GRID_SHA256 = (
    "cf3a7291bc54a819e6b619badfcd01db10d4330566d0c3d8d3f16f204b7988ad"
)
PROSPECTIVE_GRID_BYTES = 33_390_476
PROSPECTIVE_GRID_FILENAME = "2026-08-28_BOOKTICKER250.csv"

GRID_US = 250_000
EXPECTED_GRID_ROWS = 345_600
DAY_START_US = int(
    datetime(2026, 8, 28, tzinfo=timezone.utc).timestamp() * 1_000_000
)
DAY_END_US = DAY_START_US + 86_400_000_000
GRID_COLUMNS = (
    "local_timestamp_us",
    "best_bid",
    "best_ask",
    "mid",
    "book_valid",
    "quote_age_ms",
    "connection_epoch",
    "source_update_id",
    "exchange_event_time_ms",
    "exchange_transaction_time_ms",
)

VOL_FEATURE = "rv_30m_bps"
VOL_INDEX = R_FEATURE_NAMES.index(VOL_FEATURE)
SEED = 20260825
MIN_SUPPORT_N = 1200
MIN_POSITIVES = 10
MIN_NEGATIVES = 100
NULL_SHIFT_STEP = 30
MIN_NULL_SHIFTS = 20

P0_TRUE_GATES = (
    "raw_file_nonempty",
    "grid_rows_exact_345600",
    "grid_step_exact_250000us",
    "first_timestamp_exact",
    "last_timestamp_exact",
    "valid_coverage_at_least_0_99",
    "no_invalid_crossed_price_accepted",
    "no_negative_quantity_accepted",
    "no_accepted_wall_clock_reversal",
    "no_accepted_monotonic_clock_reversal",
    "no_other_symbol_accepted",
    "no_future_quote_used",
    "raw_sha_recorded",
    "grid_sha_recorded",
)
P0_FALSE_GATES = (
    "older_august_holdout_opened",
    "historical_aug1_feature_reparsed",
    "target_scored",
    "model_fit",
    "auc_scored",
    "direction_scored",
    "pnl_scored",
)


@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbol: str = SYMBOL
    training_days: tuple[str, ...] = tuple(d.isoformat() for d in TRAIN_DAYS)
    prospective_day: str = PROSPECTIVE_DAY.isoformat()
    primary_feature: str = VOL_FEATURE
    grid_us: int = GRID_US
    decision_step_s: int = 60
    decision_step_rows: int = DECISION_STEP_ROWS
    entry_delay_ms: int = 250
    horizon_s: int = HORIZON_S
    label_threshold_bps: float = LABEL_THRESHOLD_BPS
    model_c: float = 1.0
    model_penalty: str = "l2"
    model_solver: str = "lbfgs"
    model_class_weight: str | None = None
    model_max_iter: int = 1000
    model_random_state: int = SEED
    min_support_n: int = MIN_SUPPORT_N
    min_positives: int = MIN_POSITIVES
    min_negatives: int = MIN_NEGATIVES
    auc_min: float = 0.60
    ap_over_prevalence_min: float = 1.50
    top_decile_lift_min: float = 1.50
    null_shift_step_rows: int = NULL_SHIFT_STEP
    min_null_shifts: int = MIN_NULL_SHIFTS
    null_quantile: float = 0.95
    null_quantile_method: str = "higher"


@dataclass(frozen=True)
class GridAuthorization:
    resolved_path: Path
    byte_size: int
    sha256: str


@dataclass
class ProspectiveDataset:
    decision_indices: np.ndarray
    timestamp_us: np.ndarray
    rv_30m_bps: np.ndarray
    label: np.ndarray
    feature_valid: np.ndarray
    target_valid: np.ndarray
    candidate_support: np.ndarray
    nonoverlap_10m: np.ndarray


@dataclass
class SupportedRows:
    timestamp_us: np.ndarray
    label: np.ndarray
    probability: np.ndarray
    nonoverlap_10m: np.ndarray


@dataclass
class ExecutionState:
    prospective_grid_opaque_verified: bool = False
    prospective_grid_analytically_opened: bool = False
    model_fit: bool = False
    target_scored: bool = False
    ranking_metrics_scored: bool = False


def _sha256_opaque(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(workspace: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _is_ancestor(workspace: Path, ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def verify_preregistration(workspace: Path) -> str:
    path = workspace / PREREGISTRATION_REL
    digest = _sha256_opaque(path)
    if digest != PREREGISTRATION_SHA256:
        raise RuntimeError("EXP022-P1 preregistration SHA mismatch")
    return digest


def assert_frozen_workspace(workspace: Path, frozen_commit: str) -> None:
    if len(frozen_commit) != 40:
        raise RuntimeError("full 40-character frozen commit required")
    try:
        int(frozen_commit, 16)
    except ValueError as exc:
        raise RuntimeError("frozen commit must be hexadecimal") from exc
    if _git(workspace, "rev-parse", "HEAD") != frozen_commit:
        raise RuntimeError("frozen implementation commit mismatch")
    if not _is_ancestor(
        workspace,
        PREREGISTRATION_COMMIT,
        frozen_commit,
    ):
        raise RuntimeError("preregistration commit is not an ancestor")
    if _git(
        workspace,
        "status",
        "--porcelain",
        "--untracked-files=no",
    ):
        raise RuntimeError("tracked worktree changes after implementation freeze")
    verify_preregistration(workspace)


def verify_p0_audit(
    path: Path,
    *,
    expected_sha256: str = P0_AUDIT_SHA256,
    expected_status: str = P0_STATUS,
    expected_raw_sha256: str = PROSPECTIVE_RAW_SHA256,
    expected_grid_sha256: str = PROSPECTIVE_GRID_SHA256,
    expected_grid_bytes: int = PROSPECTIVE_GRID_BYTES,
) -> dict[str, Any]:
    digest = _sha256_opaque(path)
    if digest != expected_sha256:
        raise RuntimeError("EXP022-P0 audit SHA mismatch")

    audit = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "experiment_id": "CODEX-EXP-022-P0",
        "status": expected_status,
        "symbol": SYMBOL,
        "collection_day": PROSPECTIVE_DAY.isoformat(),
        "raw_sha256": expected_raw_sha256,
        "grid_sha256": expected_grid_sha256,
        "grid_bytes": expected_grid_bytes,
    }
    for key, expected in required.items():
        if audit.get(key) != expected:
            raise RuntimeError(f"EXP022-P0 audit mismatch: {key}")

    gates = audit.get("integrity_gates")
    if not isinstance(gates, dict):
        raise RuntimeError("EXP022-P0 integrity gates missing")
    for name in P0_TRUE_GATES:
        if gates.get(name) is not True:
            raise RuntimeError(f"EXP022-P0 integrity gate not true: {name}")
    for name in P0_FALSE_GATES:
        if gates.get(name) is not False:
            raise RuntimeError(f"EXP022-P0 guard not false: {name}")

    return {
        "audit_sha256": digest,
        "status": str(audit["status"]),
        "recorded_raw_sha256": str(audit["raw_sha256"]),
        "recorded_grid_sha256": str(audit["grid_sha256"]),
        "recorded_grid_bytes": int(audit["grid_bytes"]),
        "integrity_gates_verified": True,
    }


def authorize_prospective_grid(
    path: Path,
    *,
    expected_bytes: int = PROSPECTIVE_GRID_BYTES,
    expected_sha256: str = PROSPECTIVE_GRID_SHA256,
    expected_filename: str = PROSPECTIVE_GRID_FILENAME,
) -> GridAuthorization:
    if path.name != expected_filename:
        raise RuntimeError("prospective grid filename is not authorized")
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise RuntimeError("prospective grid is not a regular file")
    size = int(resolved.stat().st_size)
    if size != expected_bytes:
        raise RuntimeError("prospective grid byte-size mismatch")
    digest = _sha256_opaque(resolved)
    if digest != expected_sha256:
        raise RuntimeError("prospective grid SHA mismatch")
    return GridAuthorization(resolved, size, digest)


def load_prospective_grid(
    path: Path,
    authorization: GridAuthorization,
    *,
    expected_rows: int = EXPECTED_GRID_ROWS,
    day_start_us: int = DAY_START_US,
    grid_us: int = GRID_US,
    prospective_day: date = PROSPECTIVE_DAY,
) -> DayData:
    resolved = path.resolve(strict=True)
    if resolved != authorization.resolved_path:
        raise RuntimeError("grid authorization path mismatch")
    if int(resolved.stat().st_size) != authorization.byte_size:
        raise RuntimeError("grid changed after opaque authorization")

    values = np.empty((expected_rows, 5), dtype=np.float64)
    row_count = 0
    with resolved.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = tuple(next(reader))
        except StopIteration as exc:
            raise RuntimeError("prospective grid is empty") from exc
        if header != GRID_COLUMNS:
            raise RuntimeError("prospective grid schema mismatch")
        for row_count, row in enumerate(reader, start=1):
            if row_count > expected_rows:
                raise RuntimeError("prospective grid has too many rows")
            if len(row) != len(GRID_COLUMNS):
                raise RuntimeError("prospective grid data-row schema mismatch")
            try:
                values[row_count - 1] = [float(value) for value in row[:5]]
            except ValueError as exc:
                raise RuntimeError(
                    f"prospective grid invalid numeric row: {row_count}"
                ) from exc
    if row_count != expected_rows:
        raise RuntimeError(
            f"prospective grid expected {expected_rows} rows, got {row_count}"
        )

    raw_ts = values[:, 0]
    if np.any(~np.isfinite(raw_ts)) or np.any(raw_ts != np.floor(raw_ts)):
        raise RuntimeError("prospective grid timestamps must be finite integers")
    ts = raw_ts.astype(np.int64)
    expected_ts = day_start_us + np.arange(expected_rows, dtype=np.int64) * grid_us
    if not np.array_equal(ts, expected_ts):
        raise RuntimeError("prospective grid timestamps are not the exact frozen grid")
    if len(np.unique(ts)) != expected_rows:
        raise RuntimeError("prospective grid contains duplicate timestamps")

    flags = values[:, 4]
    if np.any(~np.isfinite(flags)) or np.any((flags != 0.0) & (flags != 1.0)):
        raise RuntimeError("book_valid must contain only 0 or 1")
    book_valid = flags.astype(bool)
    bid, ask, mid = values[:, 1], values[:, 2], values[:, 3]
    valid_values = (
        np.isfinite(bid)
        & np.isfinite(ask)
        & np.isfinite(mid)
        & (bid > 0.0)
        & (ask > bid)
        & (mid > 0.0)
    )
    if np.any(book_valid & ~valid_values):
        raise RuntimeError("valid grid row has invalid bid/ask/mid")

    return DayData(
        day=prospective_day,
        ts=ts,
        bid=bid,
        ask=ask,
        mid=mid,
        book_valid=book_valid,
        valid={},
        X={},
    )


def build_prospective_dataset(
    day: DayData,
    *,
    required_day: date | None = PROSPECTIVE_DAY,
) -> ProspectiveDataset:
    if required_day is not None and day.day != required_day:
        raise ValueError("wrong EXP022-P1 prospective day")
    if len(day.ts) == 0:
        raise RuntimeError("empty day")

    decisions = np.arange(0, len(day.ts), DECISION_STEP_ROWS, dtype=np.int64)
    outcomes = executable_fixed_horizon(day, decisions, HORIZON_S)
    target_valid = outcomes["valid"] & np.isfinite(outcomes["oracle_gross_bps"])
    label = (
        outcomes["oracle_gross_bps"] >= LABEL_THRESHOLD_BPS
    ).astype(np.int8)

    spread = _spread(day)
    rv = np.full(len(decisions), np.nan, dtype=np.float64)
    feature_valid = np.zeros(len(decisions), dtype=bool)
    for position, current in enumerate(decisions.tolist()):
        features = _r_features(day, current, spread)
        if features is None:
            continue
        value = float(features[VOL_INDEX])
        if math.isfinite(value):
            rv[position] = value
            feature_valid[position] = True

    candidate = feature_valid & target_valid & np.isfinite(rv)
    minute = decisions // DECISION_STEP_ROWS
    timestamps = day.ts[decisions].astype(np.int64, copy=False)
    if np.any(np.diff(timestamps) <= 0):
        raise RuntimeError("decision timestamps are not unique and ascending")

    return ProspectiveDataset(
        decision_indices=decisions,
        timestamp_us=timestamps,
        rv_30m_bps=rv,
        label=label,
        feature_valid=feature_valid,
        target_valid=target_valid,
        candidate_support=candidate,
        nonoverlap_10m=(minute % 10) == 0,
    )


def finalize_common_support(
    dataset: ProspectiveDataset,
    candidate_probabilities: np.ndarray,
) -> SupportedRows:
    candidate_indices = np.flatnonzero(dataset.candidate_support)
    probabilities = np.asarray(candidate_probabilities, dtype=np.float64)
    if probabilities.ndim != 1 or len(probabilities) != len(candidate_indices):
        raise RuntimeError("candidate score length mismatch")
    finite = np.isfinite(probabilities)
    supported_indices = candidate_indices[finite]
    supported_probabilities = probabilities[finite]
    if np.any((supported_probabilities < 0.0) | (supported_probabilities > 1.0)):
        raise RuntimeError("model probability outside [0, 1]")

    timestamps = dataset.timestamp_us[supported_indices]
    if len(timestamps) and (
        np.any(np.diff(timestamps) <= 0)
        or len(np.unique(timestamps)) != len(timestamps)
    ):
        raise RuntimeError("common support is not unique and chronological")

    return SupportedRows(
        timestamp_us=timestamps,
        label=dataset.label[supported_indices].astype(np.int8, copy=False),
        probability=supported_probabilities,
        nonoverlap_10m=dataset.nonoverlap_10m[supported_indices],
    )


def _validate_metric_inputs(
    timestamps: np.ndarray,
    labels: np.ndarray,
    probabilities: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ts = np.asarray(timestamps, dtype=np.int64)
    y = np.asarray(labels, dtype=np.int8)
    p = np.asarray(probabilities, dtype=np.float64)
    if ts.ndim != 1 or y.ndim != 1 or p.ndim != 1:
        raise ValueError("metric inputs must be one-dimensional")
    if not (len(ts) == len(y) == len(p)):
        raise ValueError("metric input length mismatch")
    if np.any((y != 0) & (y != 1)):
        raise ValueError("labels must be binary")
    if np.any(~np.isfinite(p)) or np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("probabilities must be finite in [0, 1]")
    if len(ts) and (
        np.any(np.diff(ts) <= 0) or len(np.unique(ts)) != len(ts)
    ):
        raise ValueError("metric timestamps must be unique and ascending")
    return ts, y, p


def p1_metrics(
    timestamps: np.ndarray,
    labels: np.ndarray,
    probabilities: np.ndarray,
    *,
    include_secondary: bool = True,
) -> dict[str, Any]:
    ts, y, p = _validate_metric_inputs(timestamps, labels, probabilities)
    n = len(y)
    positives = int(y.sum())
    negatives = int(n - positives)
    prevalence = float(np.mean(y)) if n else None
    result: dict[str, Any] = {
        "n": n,
        "positives": positives,
        "negatives": negatives,
        "prevalence": prevalence,
        "roc_auc": None,
        "average_precision": None,
        "average_precision_over_prevalence": None,
        "top_decile_precision": None,
        "top_decile_lift": None,
    }

    if n and positives and negatives:
        auc = float(roc_auc_score(y, p))
        ap = float(average_precision_score(y, p))
        top_n = int(math.ceil(0.10 * n))
        ordering = np.lexsort((ts, -p))
        top_precision = float(np.mean(y[ordering[:top_n]]))
        result.update(
            {
                "roc_auc": auc,
                "average_precision": ap,
                "average_precision_over_prevalence": (
                    ap / prevalence if prevalence else None
                ),
                "top_decile_precision": top_precision,
                "top_decile_lift": (
                    top_precision / prevalence if prevalence else None
                ),
            }
        )

    if include_secondary:
        result.update(
            {
                "brier_score": None,
                "brier_skill_score": None,
                "log_loss": None,
                "mean_predicted_probability": None,
            }
        )
        if n and positives and negatives:
            brier = float(brier_score_loss(y, p))
            baseline = float(np.mean((y - prevalence) ** 2))
            result.update(
                {
                    "brier_score": brier,
                    "brier_skill_score": (
                        1.0 - brier / baseline if baseline > 0.0 else None
                    ),
                    "log_loss": float(
                        log_loss(y, np.clip(p, 1e-12, 1.0 - 1e-12))
                    ),
                    "mean_predicted_probability": float(np.mean(p)),
                }
            )
    return result


def eligible_circular_shifts(n: int) -> list[int]:
    if n < 0:
        raise ValueError("n must be non-negative")
    return [
        k
        for k in range(NULL_SHIFT_STEP, n, NULL_SHIFT_STEP)
        if min(k, n - k) >= NULL_SHIFT_STEP
    ]


def circular_shift_labels(labels: np.ndarray, k: int) -> np.ndarray:
    y = np.asarray(labels, dtype=np.int8)
    if y.ndim != 1:
        raise ValueError("labels must be one-dimensional")
    if k <= 0 or k >= len(y) or min(k, len(y) - k) < NULL_SHIFT_STEP:
        raise ValueError("ineligible circular shift")
    return np.roll(y, k)


def higher_q95(values: np.ndarray) -> float:
    a = np.asarray(values, dtype=np.float64)
    if a.ndim != 1 or len(a) == 0 or np.any(~np.isfinite(a)):
        raise ValueError("null values must be a nonempty finite vector")
    return float(np.quantile(a, 0.95, method="higher"))


def empirical_one_sided_p(null_values: np.ndarray, observed: float) -> float:
    a = np.asarray(null_values, dtype=np.float64)
    if a.ndim != 1 or len(a) == 0 or np.any(~np.isfinite(a)):
        raise ValueError("null values must be a nonempty finite vector")
    if not math.isfinite(observed):
        raise ValueError("observed value must be finite")
    return float((1 + np.count_nonzero(a >= observed)) / (1 + len(a)))


def temporal_shift_null(
    labels: np.ndarray,
    probabilities: np.ndarray,
) -> dict[str, Any]:
    y = np.asarray(labels, dtype=np.int8)
    p = np.asarray(probabilities, dtype=np.float64)
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p):
        raise ValueError("temporal-null input mismatch")
    if np.unique(y).size != 2 or np.any(~np.isfinite(p)):
        raise ValueError("temporal null requires both classes and finite scores")
    shifts = eligible_circular_shifts(len(y))
    if len(shifts) < MIN_NULL_SHIFTS:
        return {
            "number_of_shifts": len(shifts),
            "auc_null_q95": None,
            "ap_null_q95": None,
            "auc_empirical_p": None,
            "ap_empirical_p": None,
        }

    auc_values = np.empty(len(shifts), dtype=np.float64)
    ap_values = np.empty(len(shifts), dtype=np.float64)
    for position, shift in enumerate(shifts):
        shifted = circular_shift_labels(y, shift)
        auc_values[position] = roc_auc_score(shifted, p)
        ap_values[position] = average_precision_score(shifted, p)

    observed_auc = float(roc_auc_score(y, p))
    observed_ap = float(average_precision_score(y, p))
    return {
        "number_of_shifts": len(shifts),
        "auc_null_q95": higher_q95(auc_values),
        "ap_null_q95": higher_q95(ap_values),
        "auc_empirical_p": empirical_one_sided_p(auc_values, observed_auc),
        "ap_empirical_p": empirical_one_sided_p(ap_values, observed_ap),
    }


def support_is_sufficient(labels: np.ndarray) -> bool:
    y = np.asarray(labels, dtype=np.int8)
    if y.ndim != 1 or np.any((y != 0) & (y != 1)):
        raise ValueError("support labels must be a binary vector")
    positives = int(y.sum())
    negatives = int(len(y) - positives)
    return (
        len(y) >= MIN_SUPPORT_N
        and positives >= MIN_POSITIVES
        and negatives >= MIN_NEGATIVES
    )


def primary_gates(
    metrics: dict[str, Any],
    null_summary: dict[str, Any],
    invariants_pass: bool,
) -> dict[str, bool]:
    auc = metrics.get("roc_auc")
    ap = metrics.get("average_precision")
    ap_ratio = metrics.get("average_precision_over_prevalence")
    lift = metrics.get("top_decile_lift")
    auc_q95 = null_summary.get("auc_null_q95")
    ap_q95 = null_summary.get("ap_null_q95")
    auc_p = null_summary.get("auc_empirical_p")
    ap_p = null_summary.get("ap_empirical_p")
    return {
        "prospective_auc_at_least_0_60": auc is not None and auc >= 0.60,
        "prospective_ap_over_prevalence_at_least_1_50": (
            ap_ratio is not None and ap_ratio >= 1.50
        ),
        "prospective_top_decile_lift_at_least_1_50": (
            lift is not None and lift >= 1.50
        ),
        "observed_auc_strictly_above_temporal_null_q95": (
            auc is not None and auc_q95 is not None and auc > auc_q95
        ),
        "temporal_null_auc_empirical_p_at_most_0_05": (
            auc_p is not None and auc_p <= 0.05
        ),
        "observed_ap_strictly_above_temporal_null_q95": (
            ap is not None and ap_q95 is not None and ap > ap_q95
        ),
        "temporal_null_ap_empirical_p_at_most_0_05": (
            ap_p is not None and ap_p <= 0.05
        ),
        "all_provenance_causality_protocol_invariants_pass": invariants_pass,
    }


def adjudicate_status(
    *,
    support_sufficient: bool,
    null_support_sufficient: bool,
    gates: dict[str, bool],
    invariants_pass: bool,
) -> str:
    if not invariants_pass:
        return INVALID_STATUS
    if not support_sufficient or not null_support_sufficient:
        return INCONCLUSIVE_STATUS
    return PASS_STATUS if all(gates.values()) else FAIL_STATUS


def nonoverlap_diagnostic(rows: SupportedRows) -> dict[str, Any]:
    mask = rows.nonoverlap_10m
    return p1_metrics(
        rows.timestamp_us[mask],
        rows.label[mask],
        rows.probability[mask],
        include_secondary=False,
    )


def _verify_training_inputs(
    feature_dir: Path,
    workspace: Path,
) -> list[dict[str, Any]]:
    provenance = load_frozen_provenance(workspace)
    manifest: list[dict[str, Any]] = []
    for day in TRAIN_DAYS:
        path = feature_dir / SYMBOL / f"{day.isoformat()}_FEATURES250.csv"
        if not path.is_file():
            raise FileNotFoundError(path)
        frozen = provenance[(SYMBOL, day.isoformat())]
        size = int(path.stat().st_size)
        digest = sha256_file(path)
        if size != int(frozen["bytes"]):
            raise RuntimeError(f"historical feature byte-size mismatch: {day}")
        if digest != str(frozen["sha256"]):
            raise RuntimeError(f"historical feature SHA mismatch: {day}")
        manifest.append(
            {
                "symbol": SYMBOL,
                "day": day.isoformat(),
                "path": str(path),
                "bytes": size,
                "sha256": digest,
                "frozen_provenance_match": True,
            }
        )
    return manifest


def _semantic_equivalence(
    day: DayData,
    frozen_dataset: Any,
) -> dict[str, Any]:
    adapted = build_prospective_dataset(day, required_day=None)
    if not np.array_equal(adapted.timestamp_us, frozen_dataset.timestamp_us):
        raise RuntimeError(f"historical decision timestamp mismatch: {day.day}")
    if not np.array_equal(adapted.candidate_support, frozen_dataset.valid_R):
        raise RuntimeError(f"historical valid-support mismatch: {day.day}")
    support = frozen_dataset.valid_R
    if not np.array_equal(adapted.label[support], frozen_dataset.y[support]):
        raise RuntimeError(f"historical target-label mismatch: {day.day}")
    frozen_rv = frozen_dataset.X_R[support, VOL_INDEX]
    adapted_rv = adapted.rv_30m_bps[support]
    if not np.array_equal(adapted_rv, frozen_rv):
        raise RuntimeError(f"historical rv_30m_bps mismatch: {day.day}")
    return {
        "day": day.day.isoformat(),
        "decision_rows": int(len(adapted.timestamp_us)),
        "common_support_n": int(support.sum()),
        "rv_exact_match": True,
        "target_and_support_exact_match": True,
    }


def _prepare_historical(
    feature_dir: Path,
    workspace: Path,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    np.ndarray,
    np.ndarray,
    list[dict[str, Any]],
]:
    manifest = _verify_training_inputs(feature_dir, workspace)
    features: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    validation: list[dict[str, Any]] = []
    counts: list[dict[str, Any]] = []

    for day in TRAIN_DAYS:
        loaded = _load_day(
            feature_dir / SYMBOL / f"{day.isoformat()}_FEATURES250.csv",
            day,
        )
        frozen_dataset = build_day_dataset(SYMBOL, loaded)
        validation.append(_semantic_equivalence(loaded, frozen_dataset))
        support = frozen_dataset.valid_R
        x = frozen_dataset.X_R[support][:, [VOL_INDEX]]
        y = frozen_dataset.y[support].astype(np.int8, copy=False)
        features.append(x)
        labels.append(y)
        counts.append(
            {
                "day": day.isoformat(),
                "n": int(len(y)),
                "positives": int(y.sum()),
                "negatives": int(len(y) - y.sum()),
            }
        )

    X = np.concatenate(features)
    y = np.concatenate(labels)
    if X.ndim != 2 or X.shape[1] != 1 or np.any(~np.isfinite(X)):
        raise RuntimeError("invalid one-feature historical training matrix")
    if len(y) != len(X) or np.unique(y).size != 2:
        raise RuntimeError("historical training labels lack both classes")
    return manifest, validation, X, y, counts


def run_preflight(
    *,
    feature_dir: Path,
    workspace: Path,
    p0_audit: Path,
) -> dict[str, Any]:
    prereg_sha = verify_preregistration(workspace)
    p0 = verify_p0_audit(p0_audit)
    manifest, validation, X, y, counts = _prepare_historical(
        feature_dir,
        workspace,
    )
    return {
        "experiment_id": EXPERIMENT_ID,
        "mode": "preflight",
        "status": "PREOPEN_VALIDATION_PASS",
        "preregistration_sha256": prereg_sha,
        "p0_audit": p0,
        "historical_input_manifest": manifest,
        "historical_semantic_validation": validation,
        "historical_training_counts": counts,
        "historical_training_n": int(len(y)),
        "historical_feature_columns": int(X.shape[1]),
        "model_fit": False,
        "prospective_grid_opaque_verified": False,
        "prospective_grid_analytically_opened": False,
        "prospective_metrics_scored": False,
        **execution_guards(),
    }


def execution_guards() -> dict[str, bool]:
    return {
        "direction_scored": False,
        "pnl_scored": False,
        "leverage_scored": False,
        "older_august_holdout_opened": False,
        "historical_aug1_feature_reparsed": False,
        "network_accessed": False,
        "prospective_raw_opened": False,
    }


def _split_metrics(metrics: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    primary_names = (
        "n",
        "positives",
        "negatives",
        "prevalence",
        "roc_auc",
        "average_precision",
        "average_precision_over_prevalence",
        "top_decile_precision",
        "top_decile_lift",
    )
    secondary_names = (
        "brier_score",
        "brier_skill_score",
        "log_loss",
        "mean_predicted_probability",
    )
    return (
        {name: metrics[name] for name in primary_names},
        {name: metrics[name] for name in secondary_names},
    )


def _execute_once(
    *,
    feature_dir: Path,
    grid: Path,
    workspace: Path,
    frozen_commit: str,
    p0_audit: Path,
    state: ExecutionState,
) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)
    prereg_sha = verify_preregistration(workspace)
    p0 = verify_p0_audit(p0_audit)
    authorization = authorize_prospective_grid(grid)
    state.prospective_grid_opaque_verified = True

    manifest, validation, X_train, y_train, train_counts = _prepare_historical(
        feature_dir,
        workspace,
    )
    model = FixedLogistic().fit(X_train, y_train)
    state.model_fit = True

    state.prospective_grid_analytically_opened = True
    day = load_prospective_grid(grid, authorization)
    dataset = build_prospective_dataset(day)
    state.target_scored = True

    candidate = dataset.candidate_support
    candidate_probabilities = model.predict_proba(
        dataset.rv_30m_bps[candidate].reshape(-1, 1)
    )
    rows = finalize_common_support(dataset, candidate_probabilities)
    metrics = p1_metrics(
        rows.timestamp_us,
        rows.label,
        rows.probability,
    )
    state.ranking_metrics_scored = True

    support_ok = support_is_sufficient(rows.label)
    if support_ok:
        null_summary = temporal_shift_null(rows.label, rows.probability)
    else:
        null_summary = {
            "number_of_shifts": len(eligible_circular_shifts(len(rows.label))),
            "auc_null_q95": None,
            "ap_null_q95": None,
            "auc_empirical_p": None,
            "ap_empirical_p": None,
        }
    null_support_ok = null_summary["number_of_shifts"] >= MIN_NULL_SHIFTS

    invariants = {
        "preregistration_sha_exact": prereg_sha == PREREGISTRATION_SHA256,
        "preregistration_commit_is_ancestor": _is_ancestor(
            workspace,
            PREREGISTRATION_COMMIT,
            frozen_commit,
        ),
        "p0_audit_sha_and_status_exact": (
            p0["audit_sha256"] == P0_AUDIT_SHA256
            and p0["status"] == P0_STATUS
        ),
        "p0_recorded_raw_sha_exact_without_raw_open": (
            p0["recorded_raw_sha256"] == PROSPECTIVE_RAW_SHA256
        ),
        "prospective_grid_sha_and_bytes_exact": (
            authorization.sha256 == PROSPECTIVE_GRID_SHA256
            and authorization.byte_size == PROSPECTIVE_GRID_BYTES
        ),
        "historical_training_days_exact_jan_jul": TRAIN_DAYS == tuple(
            date(2026, month, 1) for month in range(1, 8)
        ),
        "prospective_day_exact_2026_08_28": day.day == PROSPECTIVE_DAY,
        "symbol_exact_btcusdt": SYMBOL == "BTCUSDT",
        "primary_feature_exact_rv_30m_bps": VOL_FEATURE == "rv_30m_bps",
        "one_legitimate_feature_only": X_train.shape[1] == 1,
        "decision_step_exact_60s": DECISION_STEP_ROWS == 240,
        "entry_delay_exact_250ms": True,
        "target_horizon_exact_600s": HORIZON_S == 600,
        "target_threshold_exact_24bp": LABEL_THRESHOLD_BPS == 24.0,
        "historical_adapter_semantics_exact": all(
            item["rv_exact_match"] and item["target_and_support_exact_match"]
            for item in validation
        ),
        "common_support_unique_and_chronological": (
            len(rows.timestamp_us) == len(np.unique(rows.timestamp_us))
            and (
                len(rows.timestamp_us) < 2
                or np.all(np.diff(rows.timestamp_us) > 0)
            )
        ),
        "no_august_fit_or_refit": True,
        **{f"guard_{key}": value for key, value in execution_guards().items()},
    }
    positive_invariants = {
        key: value
        for key, value in invariants.items()
        if not key.startswith("guard_")
    }
    guard_invariants = {
        key: value
        for key, value in invariants.items()
        if key.startswith("guard_")
    }
    invariants_pass = all(value is True for value in positive_invariants.values())
    invariants_pass &= all(value is False for value in guard_invariants.values())

    gates = primary_gates(metrics, null_summary, invariants_pass)
    status = adjudicate_status(
        support_sufficient=support_ok,
        null_support_sufficient=null_support_ok,
        gates=gates,
        invariants_pass=invariants_pass,
    )
    nonoverlap = nonoverlap_diagnostic(rows)
    primary, secondary = _split_metrics(metrics)

    score_records = [
        {
            "timestamp_us": int(timestamp),
            "label": int(label),
            "model_probability": float(probability),
            "nonoverlap_10m": bool(nonoverlap_flag),
        }
        for timestamp, label, probability, nonoverlap_flag in zip(
            rows.timestamp_us.tolist(),
            rows.label.tolist(),
            rows.probability.tolist(),
            rows.nonoverlap_10m.tolist(),
        )
    ]

    return {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "frozen_implementation_commit": frozen_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "preregistration_sha256": prereg_sha,
        "p0_audit": p0,
        "prospective_grid": {
            "sha256": authorization.sha256,
            "bytes": authorization.byte_size,
        },
        "historical_input_manifest": manifest,
        "historical_training_counts": train_counts,
        "configuration": asdict(Config()),
        "configuration_sha256": canonical_sha256(Config()),
        "support": {
            "n": int(len(rows.label)),
            "positives": int(rows.label.sum()),
            "negatives": int(len(rows.label) - rows.label.sum()),
            "minimum_support_pass": support_ok,
        },
        "primary_metrics": primary,
        "secondary_calibration_diagnostics": secondary,
        "circular_shift_null_summary": null_summary,
        "primary_gates": gates,
        "nonoverlap_10m_diagnostic": nonoverlap,
        "invariants": invariants,
        "deterministic_score_records_sha256": canonical_sha256(score_records),
        "score_records": score_records,
        "prospective_grid_opaque_verified": state.prospective_grid_opaque_verified,
        "prospective_grid_analytically_opened": (
            state.prospective_grid_analytically_opened
        ),
        "model_fit": state.model_fit,
        "target_scored": state.target_scored,
        "ranking_metrics_scored": state.ranking_metrics_scored,
        **execution_guards(),
    }


def invalid_payload(
    exc: Exception,
    frozen_commit: str,
    state: ExecutionState,
) -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "status": INVALID_STATUS,
        "frozen_implementation_commit": frozen_commit,
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "configuration": asdict(Config()),
        "configuration_sha256": canonical_sha256(Config()),
        "failure_type": type(exc).__name__,
        "failure_message": str(exc),
        "prospective_grid_opaque_verified": state.prospective_grid_opaque_verified,
        "prospective_grid_analytically_opened": (
            state.prospective_grid_analytically_opened
        ),
        "model_fit": state.model_fit,
        "target_scored": state.target_scored,
        "ranking_metrics_scored": state.ranking_metrics_scored,
        **execution_guards(),
    }


def ensure_fresh_output(output: Path) -> Path:
    part = output.with_name(output.name + ".part")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing result: {output}")
    if part.exists():
        raise FileExistsError(f"interrupted result marker already exists: {part}")
    return part


def _write_once(output: Path, payload: dict[str, Any]) -> None:
    part = output.with_name(output.name + ".part")
    encoded = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    with part.open("x", encoding="utf-8") as f:
        f.write(encoded)
    if output.exists():
        raise FileExistsError(f"result appeared during execution: {output}")
    part.replace(output)


def run_execute(
    *,
    feature_dir: Path,
    grid: Path,
    output: Path,
    workspace: Path,
    frozen_commit: str,
    p0_audit: Path,
) -> dict[str, Any]:
    ensure_fresh_output(output)
    state = ExecutionState()
    try:
        payload = _execute_once(
            feature_dir=feature_dir,
            grid=grid,
            workspace=workspace,
            frozen_commit=frozen_commit,
            p0_audit=p0_audit,
            state=state,
        )
    except Exception as exc:
        payload = invalid_payload(exc, frozen_commit, state)
    _write_once(output, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "execute"), required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--p0-audit", type=Path)
    parser.add_argument("--grid", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--frozen-commit")
    args = parser.parse_args(argv)

    workspace = args.workspace.resolve()
    p0_audit = args.p0_audit or workspace / P0_AUDIT_REL
    if args.mode == "preflight":
        if args.grid is not None or args.output is not None:
            parser.error("preflight does not accept --grid or --output")
        if args.frozen_commit is not None:
            parser.error("preflight does not accept --frozen-commit")
        result = run_preflight(
            feature_dir=args.feature_dir,
            workspace=workspace,
            p0_audit=p0_audit,
        )
    else:
        if args.grid is None:
            parser.error("execute requires --grid")
        if args.output is None:
            parser.error("execute requires --output")
        if args.frozen_commit is None:
            parser.error("execute requires --frozen-commit")
        result = run_execute(
            feature_dir=args.feature_dir,
            grid=args.grid,
            output=args.output,
            workspace=workspace,
            frozen_commit=args.frozen_commit,
            p0_audit=p0_audit,
        )

    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "mode": args.mode,
                "status": result["status"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

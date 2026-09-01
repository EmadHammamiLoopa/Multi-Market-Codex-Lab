"""DEV030-P1 label-only first-passage feasibility audit.

This module aggregates executable first-passage labels on the exact consumed
BTCUSDT January-July 2026 Phase0DL files. It contains no predictive model,
feature selection, opportunity gate, direction model, or PnL backtest.

Real-data execution is allowed only from a committed, clean implementation
whose HEAD descends from the frozen DEV030 first-passage baseline.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Mapping, Sequence

import numpy as np

from .dev030_first_passage import (
    GRID_US,
    LATENCY_MS,
    LONG_FIRST,
    NONE,
    SHORT_FIRST,
    label_first_passage_targets,
)
from .v23_phase0dl_score import DayData, _load_day

EXPERIMENT_ID = "DEV030-P1"
STATUS = "LABEL_FEASIBILITY_AUDIT_COMPLETE"

PARENT_BASELINE_COMMIT = "024fdbe9be36db73ae7ac7f2f746a05f3f5a88a0"
EXPECTED_BRANCH = "research/dev030-p1-label-feasibility"
EXPECTED_ORIGIN = (
    "https://github.com/EmadHammamiLoopa/Multi-Market-Codex-Lab.git"
)

EXP029_REL = (
    "evidence/codex/exp029_p0_causal_rank_opportunity_readiness/"
    "HISTORICAL_SELECTION.json"
)
EXPECTED_EXP029_SHA256 = (
    "86a5c29c977ee325dc37d3a3c0d2f9b3366360fcf46734785fd25fa45f1a75ee"
)

SYMBOL = "BTCUSDT"
HISTORICAL_DAYS = tuple(date(2026, month, 1) for month in range(1, 8))
FEATURE_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/v23/"
    "phase0dl_features250/BTCUSDT"
)
EXPECTED_INPUT_SHA256 = {
    date(2026, 1, 1): (
        "ab0c61fe9a7517cf97388300e6adb18248a37a7977aac8455a10c02b7906de98"
    ),
    date(2026, 2, 1): (
        "33e56c6b5b02ec124bf3a21dbed27fc8705fc572cb7fed9ff73876de87c2978e"
    ),
    date(2026, 3, 1): (
        "076067a4731047dd992004d936d962567c1d7ceed864bb6e778db05bc8c59420"
    ),
    date(2026, 4, 1): (
        "a803fbb8d68f4173551be4c2cccf9fe03f25d86dc6e00469c4a5ab635ade2307"
    ),
    date(2026, 5, 1): (
        "36015c5954d820d8b2f0505ecab9fdc96f40136247d1270365c9ef81312de2e3"
    ),
    date(2026, 6, 1): (
        "5e73f8dc355e3dfcceda649525b4d067ccb74d0259992a287161a71375105535"
    ),
    date(2026, 7, 1): (
        "aadf264ba38eac4563ebab7fd2da22b300d82752343ccd30b19809c70cd39012"
    ),
}

HORIZONS_SECONDS = (10, 30, 60, 120, 300, 600)
BARRIERS_BPS = (4, 8, 12, 16, 24, 36)
DECISION_STEP_US = 60_000_000
EXPECTED_ROWS = 345_600
DAY_US = 86_400_000_000

ADDITIONAL_COST_REFERENCES_BPS = (8, 12)

ROBUST_MIN_VALID_FRACTION = 0.95
ROBUST_MIN_DIRECTIONAL_TOUCHES = 150
ROBUST_MIN_MINORITY_DIRECTION = 50
ROBUST_MIN_TOUCH_DAYS = 6
ROBUST_MIN_BOTH_DIRECTION_DAYS = 5

USABLE_MIN_VALID_FRACTION = 0.90
USABLE_MIN_DIRECTIONAL_TOUCHES = 75
USABLE_MIN_MINORITY_DIRECTION = 25
USABLE_MIN_TOUCH_DAYS = 5

THIN_MIN_DIRECTIONAL_TOUCHES = 25
MATERIAL_MIN_VALID_FRACTION = 0.90
SHORTLIST_MAX_GEOMETRIES = 6

ROBUST_SUPPORT = "ROBUST_SUPPORT"
USABLE_SUPPORT = "USABLE_SUPPORT"
THIN_SUPPORT = "THIN_SUPPORT"
NOT_USABLE = "NOT_USABLE"

# These classes describe only gross-barrier margins relative to the existing
# 8/12 bp additional-cost references. They are not profitability claims.
COST_CHALLENGED = "COST_CHALLENGED"  # barrier <= 8 bp
POSITIVE_AFTER_8_ONLY = "POSITIVE_AFTER_8_ONLY"  # 8 < barrier <= 12 bp
POSITIVE_AFTER_12 = "POSITIVE_AFTER_12"  # barrier > 12 bp

DESIGN_REL = "docs/DEV030_P0_SEQUENTIAL_DIRECTION_DESIGN.md"
SOURCE_REL = "src/multimarket/dev030_label_feasibility.py"
TEST_REL = "tests/test_dev030_label_feasibility.py"
FIRST_PASSAGE_REL = "src/multimarket/dev030_first_passage.py"

EXECUTION_TRACKED_FILES = (
    SOURCE_REL,
    TEST_REL,
    DESIGN_REL,
    FIRST_PASSAGE_REL,
)

AUDIT_JSON_NAME = "LABEL_FEASIBILITY_AUDIT.json"
AUDIT_SUMMARY_NAME = "LABEL_FEASIBILITY_SUMMARY.md"


class AuditProtocolError(RuntimeError):
    """The explicit data, code, lineage, or output contract was violated."""


@dataclass
class RunResult:
    payload: dict[str, Any]
    audit_json_sha256: str
    audit_summary_sha256: str


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    if completed.returncode not in (0, 1):
        raise AuditProtocolError(
            "git ancestry verification failed: "
            f"returncode={completed.returncode}, "
            f"stderr={completed.stderr.strip()}"
        )
    return bool(completed.returncode == 0)


def _tracked_at_execution_head(
    workspace: Path,
    relative_path: str,
) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative_path],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return True
    if completed.returncode == 1:
        return False
    raise AuditProtocolError(
        f"unable to verify tracked file {relative_path}: "
        f"returncode={completed.returncode}, "
        f"stderr={completed.stderr.strip()}"
    )


def verify_exp029_artifact(workspace: Path) -> dict[str, Any]:
    """Verify the frozen EXP029 artifact as opaque bytes only.

    The artifact is not parsed, summarized, modified, or rerun.
    """

    artifact = workspace / EXP029_REL
    if not artifact.is_file():
        raise AuditProtocolError(f"EXP029 artifact missing: {artifact}")
    actual_sha256 = _sha256_file(artifact)
    if actual_sha256 != EXPECTED_EXP029_SHA256:
        raise AuditProtocolError("EXP029 artifact SHA-256 mismatch")
    return {
        "exp029_artifact_path": EXP029_REL,
        "exp029_artifact_sha256": actual_sha256,
        "exp029_artifact_sha256_verified": True,
    }


def verify_workspace(workspace: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    if _git(workspace, "rev-parse", "--show-toplevel") != str(workspace):
        raise AuditProtocolError("workspace is not the repository root")

    origin = _git(workspace, "remote", "get-url", "origin")
    if origin != EXPECTED_ORIGIN:
        raise AuditProtocolError("repository origin mismatch")

    head = _git(workspace, "rev-parse", "HEAD")
    branch = _git(workspace, "branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise AuditProtocolError(
            "DEV030 label-feasibility branch mismatch"
        )
    if not _is_ancestor(workspace, PARENT_BASELINE_COMMIT, head):
        raise AuditProtocolError(
            "DEV030 first-passage baseline is not an ancestor of execution HEAD"
        )

    tracked_status = _git(
        workspace,
        "status",
        "--porcelain",
        "--untracked-files=no",
    )
    if tracked_status:
        raise AuditProtocolError("tracked worktree changes detected")

    missing_tracked_files = [
        relative_path
        for relative_path in EXECUTION_TRACKED_FILES
        if not _tracked_at_execution_head(workspace, relative_path)
    ]
    if missing_tracked_files:
        raise AuditProtocolError(
            "real audit requires committed implementation inputs; "
            f"untracked at execution HEAD: {missing_tracked_files}"
        )

    # This verification deliberately precedes Jan-Jul manifest hashing and
    # every call to the historical CSV loader.
    exp029_provenance = verify_exp029_artifact(workspace)

    return {
        "workspace": str(workspace),
        "origin": origin,
        "head": head,
        "branch": branch,
        "parent_baseline_commit": PARENT_BASELINE_COMMIT,
        "parent_baseline_is_ancestor": True,
        "tracked_tree_clean": True,
        "execution_files_tracked": list(EXECUTION_TRACKED_FILES),
        **exp029_provenance,
    }


def authorized_feature_path(day: date) -> Path:
    if type(day) is not date or day not in HISTORICAL_DAYS:
        raise AuditProtocolError(
            "day outside exact Jan-Jul BTC authorization"
        )
    return FEATURE_ROOT / f"{day.isoformat()}_FEATURES250.csv"


def verify_input_manifest() -> list[dict[str, Any]]:
    """Hash only the seven explicit authorized paths before analytical load."""

    records: list[dict[str, Any]] = []
    resolved_paths: set[Path] = set()

    for day in HISTORICAL_DAYS:
        path = authorized_feature_path(day)
        if not path.is_file():
            raise AuditProtocolError(
                f"authorized historical input missing: {path}"
            )

        resolved = path.resolve()
        if resolved in resolved_paths:
            raise AuditProtocolError(
                "duplicate authorized historical input path"
            )
        resolved_paths.add(resolved)

        actual_sha256 = _sha256_file(path)
        expected_sha256 = EXPECTED_INPUT_SHA256[day]
        if actual_sha256 != expected_sha256:
            raise AuditProtocolError(
                "historical input SHA-256 mismatch for "
                f"{day.isoformat()}"
            )

        records.append(
            {
                "symbol": SYMBOL,
                "date": day.isoformat(),
                "path": str(path),
                "filename": path.name,
                "bytes": int(path.stat().st_size),
                "sha256": actual_sha256,
                "expected_sha256": expected_sha256,
                "sha256_verified_before_analytical_load": True,
            }
        )

    if len(records) != 7:
        raise AuditProtocolError(
            "exactly seven authorized inputs are required"
        )
    return records


def minute_decision_indices(
    timestamps_us: Sequence[int] | np.ndarray,
) -> np.ndarray:
    raw = np.asarray(timestamps_us)
    if raw.ndim != 1 or raw.dtype.kind not in "iu":
        raise ValueError(
            "timestamps must be a one-dimensional integer array"
        )

    timestamps = raw.astype(np.int64, copy=False)
    if len(timestamps) > 1 and bool(np.any(np.diff(timestamps) <= 0)):
        raise ValueError(
            "timestamps must be unique and chronological"
        )

    return np.flatnonzero(
        timestamps % DECISION_STEP_US == 0
    ).astype(np.int64, copy=False)


def _safe_ratio(
    numerator: int | float,
    denominator: int | float,
) -> float | None:
    if denominator == 0:
        return None
    value = float(numerator) / float(denominator)
    if not math.isfinite(value):
        raise AuditProtocolError("non-finite ratio")
    return value


def _percentiles(
    values: Sequence[float],
    quantiles: Mapping[str, float],
) -> dict[str, float | None]:
    if not values:
        return {name: None for name in quantiles}

    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or not bool(np.all(np.isfinite(array))):
        raise AuditProtocolError("non-finite diagnostic values")

    return {
        name: float(
            np.quantile(array, quantile, method="linear")
        )
        for name, quantile in quantiles.items()
    }


@dataclass
class RecordAccumulator:
    candidate_decisions: int = 0
    valid_targets: int = 0
    invalid_targets: int = 0
    invalid_counts: Counter[str] = field(default_factory=Counter)
    same_row_ambiguous_count: int = 0

    long_first_count: int = 0
    short_first_count: int = 0
    none_count: int = 0

    touch_times_ms: list[float] = field(default_factory=list)
    long_touch_times_ms: list[float] = field(default_factory=list)
    short_touch_times_ms: list[float] = field(default_factory=list)

    entry_spreads_bps: list[float] = field(default_factory=list)
    long_mfe_bps: list[float] = field(default_factory=list)
    long_mae_bps: list[float] = field(default_factory=list)
    short_mfe_bps: list[float] = field(default_factory=list)
    short_mae_bps: list[float] = field(default_factory=list)

    @staticmethod
    def _finite(record: Mapping[str, Any], key: str) -> float:
        value = record.get(key)
        if isinstance(value, (bool, np.bool_)):
            raise AuditProtocolError(
                f"{key} must be a finite number"
            )
        try:
            converted = float(value)
        except (TypeError, ValueError) as exc:
            raise AuditProtocolError(
                f"{key} must be a finite number"
            ) from exc
        if not math.isfinite(converted):
            raise AuditProtocolError(f"{key} must be finite")
        return converted

    @staticmethod
    def _nonnegative(record: Mapping[str, Any], key: str) -> float:
        value = RecordAccumulator._finite(record, key)
        if value < 0.0:
            raise AuditProtocolError(
                f"{key} must be non-negative"
            )
        return value

    def add(self, record: Mapping[str, Any]) -> None:
        self.candidate_decisions += 1

        target_valid = record.get("target_valid")
        same_row = record.get("same_row_ambiguous")
        if type(target_valid) is not bool or type(same_row) is not bool:
            raise AuditProtocolError(
                "target validity flags must be built-in bool"
            )

        if not target_valid:
            if record.get("label") is not None:
                raise AuditProtocolError(
                    "invalid target must have null label"
                )

            reason = record.get("invalid_reason")
            if type(reason) is not str or not reason:
                raise AuditProtocolError(
                    "invalid target must have stable reason"
                )
            if same_row and reason != "same_row_ambiguous":
                raise AuditProtocolError(
                    "same-row flag/reason mismatch"
                )
            if reason == "same_row_ambiguous" and not same_row:
                raise AuditProtocolError(
                    "same-row reason/flag mismatch"
                )

            self.invalid_targets += 1
            self.invalid_counts[reason] += 1
            self.same_row_ambiguous_count += int(same_row)
            return

        if record.get("invalid_reason") is not None or same_row:
            raise AuditProtocolError(
                "valid target carries invalid diagnostics"
            )

        label = record.get("label")
        if label not in (LONG_FIRST, SHORT_FIRST, NONE):
            raise AuditProtocolError(
                "valid target label outside frozen contract"
            )

        self.valid_targets += 1
        if label == LONG_FIRST:
            self.long_first_count += 1
        elif label == SHORT_FIRST:
            self.short_first_count += 1
        else:
            self.none_count += 1

        self.entry_spreads_bps.append(
            self._nonnegative(record, "entry_spread_bps")
        )
        self.long_mfe_bps.append(
            self._nonnegative(
                record,
                "long_max_favorable_excursion_bps",
            )
        )
        self.long_mae_bps.append(
            self._nonnegative(
                record,
                "long_max_adverse_excursion_bps",
            )
        )
        self.short_mfe_bps.append(
            self._nonnegative(
                record,
                "short_max_favorable_excursion_bps",
            )
        )
        self.short_mae_bps.append(
            self._nonnegative(
                record,
                "short_max_adverse_excursion_bps",
            )
        )

        if label in (LONG_FIRST, SHORT_FIRST):
            touch_time = self._nonnegative(
                record,
                "time_to_first_barrier_ms",
            )
            self.touch_times_ms.append(touch_time)
            if label == LONG_FIRST:
                self.long_touch_times_ms.append(touch_time)
            else:
                self.short_touch_times_ms.append(touch_time)
        elif record.get("time_to_first_barrier_ms") is not None:
            raise AuditProtocolError(
                "NONE target must not have touch time"
            )

    def extend(self, records: Sequence[Mapping[str, Any]]) -> None:
        for record in records:
            self.add(record)

    def merge(self, other: "RecordAccumulator") -> None:
        self.candidate_decisions += other.candidate_decisions
        self.valid_targets += other.valid_targets
        self.invalid_targets += other.invalid_targets
        self.invalid_counts.update(other.invalid_counts)
        self.same_row_ambiguous_count += (
            other.same_row_ambiguous_count
        )

        self.long_first_count += other.long_first_count
        self.short_first_count += other.short_first_count
        self.none_count += other.none_count

        self.touch_times_ms.extend(other.touch_times_ms)
        self.long_touch_times_ms.extend(
            other.long_touch_times_ms
        )
        self.short_touch_times_ms.extend(
            other.short_touch_times_ms
        )

        self.entry_spreads_bps.extend(other.entry_spreads_bps)
        self.long_mfe_bps.extend(other.long_mfe_bps)
        self.long_mae_bps.extend(other.long_mae_bps)
        self.short_mfe_bps.extend(other.short_mfe_bps)
        self.short_mae_bps.extend(other.short_mae_bps)

    def summary(self) -> dict[str, Any]:
        if (
            self.valid_targets + self.invalid_targets
            != self.candidate_decisions
        ):
            raise AuditProtocolError(
                "candidate target accounting mismatch"
            )

        directional = (
            self.long_first_count + self.short_first_count
        )
        if (
            self.long_first_count
            + self.short_first_count
            + self.none_count
            != self.valid_targets
        ):
            raise AuditProtocolError(
                "valid label accounting mismatch"
            )

        minority = min(
            self.long_first_count,
            self.short_first_count,
        )
        majority = max(
            self.long_first_count,
            self.short_first_count,
        )

        return {
            "candidate_decisions": int(self.candidate_decisions),
            "valid_targets": int(self.valid_targets),
            "invalid_targets": int(self.invalid_targets),
            "valid_fraction": _safe_ratio(
                self.valid_targets,
                self.candidate_decisions,
            ),
            "invalid_fraction": _safe_ratio(
                self.invalid_targets,
                self.candidate_decisions,
            ),
            "invalid_counts_by_reason": {
                key: int(self.invalid_counts[key])
                for key in sorted(self.invalid_counts)
            },
            "same_row_ambiguous_count": int(
                self.same_row_ambiguous_count
            ),
            "LONG_FIRST_count": int(self.long_first_count),
            "SHORT_FIRST_count": int(self.short_first_count),
            "NONE_count": int(self.none_count),
            "LONG_FIRST_fraction_of_valid": _safe_ratio(
                self.long_first_count,
                self.valid_targets,
            ),
            "SHORT_FIRST_fraction_of_valid": _safe_ratio(
                self.short_first_count,
                self.valid_targets,
            ),
            "NONE_fraction_of_valid": _safe_ratio(
                self.none_count,
                self.valid_targets,
            ),
            "directional_touch_count": int(directional),
            "directional_touch_fraction_of_valid": _safe_ratio(
                directional,
                self.valid_targets,
            ),
            "LONG_fraction_of_directional": _safe_ratio(
                self.long_first_count,
                directional,
            ),
            "SHORT_fraction_of_directional": _safe_ratio(
                self.short_first_count,
                directional,
            ),
            "minority_direction_count": int(minority),
            "direction_balance_ratio": _safe_ratio(
                minority,
                majority,
            ),
            "time_to_first_barrier_ms": _percentiles(
                self.touch_times_ms,
                {
                    "p10": 0.10,
                    "p25": 0.25,
                    "median": 0.50,
                    "p75": 0.75,
                    "p90": 0.90,
                },
            ),
            "LONG_FIRST_time_to_touch_median_ms": _percentiles(
                self.long_touch_times_ms,
                {"median": 0.50},
            )["median"],
            "SHORT_FIRST_time_to_touch_median_ms": _percentiles(
                self.short_touch_times_ms,
                {"median": 0.50},
            )["median"],
            "entry_spread_bps": _percentiles(
                self.entry_spreads_bps,
                {
                    "median": 0.50,
                    "p90": 0.90,
                    "p95": 0.95,
                },
            ),
            "long_max_favorable_excursion_bps": _percentiles(
                self.long_mfe_bps,
                {"median": 0.50, "p90": 0.90},
            ),
            "long_max_adverse_excursion_bps": _percentiles(
                self.long_mae_bps,
                {"median": 0.50, "p90": 0.90},
            ),
            "short_max_favorable_excursion_bps": _percentiles(
                self.short_mfe_bps,
                {"median": 0.50, "p90": 0.90},
            ),
            "short_max_adverse_excursion_bps": _percentiles(
                self.short_mae_bps,
                {"median": 0.50, "p90": 0.90},
            ),
        }


def summarize_records(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    accumulator = RecordAccumulator()
    accumulator.extend(records)
    return accumulator.summary()


def pooled_day_metrics(
    pooled: Mapping[str, Any],
    per_day: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not per_day:
        raise AuditProtocolError(
            "pooled geometry requires at least one day"
        )

    valid_counts = [
        int(day["valid_targets"])
        for day in per_day
    ]
    directional_counts = [
        int(day["directional_touch_count"])
        for day in per_day
    ]
    minority_counts = [
        int(day["minority_direction_count"])
        for day in per_day
    ]
    directional_fractions = [
        float(day["directional_touch_fraction_of_valid"])
        for day in per_day
        if day["directional_touch_fraction_of_valid"] is not None
    ]

    result = dict(pooled)
    result.update(
        {
            "days_with_any_valid_target": int(
                sum(value > 0 for value in valid_counts)
            ),
            "days_with_any_directional_touch": int(
                sum(value > 0 for value in directional_counts)
            ),
            "days_with_both_long_and_short": int(
                sum(
                    int(day["LONG_FIRST_count"]) > 0
                    and int(day["SHORT_FIRST_count"]) > 0
                    for day in per_day
                )
            ),
            "minimum_valid_targets_across_days": int(
                min(valid_counts)
            ),
            "minimum_directional_touches_across_days": int(
                min(directional_counts)
            ),
            "minimum_minority_direction_count_across_days": int(
                min(minority_counts)
            ),
            "median_directional_touch_fraction_across_days": (
                float(
                    np.median(
                        np.asarray(
                            directional_fractions,
                            dtype=np.float64,
                        )
                    )
                )
                if directional_fractions
                else None
            ),
        }
    )
    return result


def cost_plausibility(
    barrier_bps: int | float,
) -> dict[str, Any]:
    """Describe barrier-minus-cost references, not realized profitability."""

    barrier = float(barrier_bps)
    if not math.isfinite(barrier) or barrier <= 0.0:
        raise ValueError(
            "barrier must be positive and finite"
        )

    if barrier <= 8.0:
        cost_class = COST_CHALLENGED
    elif barrier <= 12.0:
        cost_class = POSITIVE_AFTER_8_ONLY
    else:
        cost_class = POSITIVE_AFTER_12

    return {
        "gross_barrier_bps": barrier,
        "margin_after_8bps": float(barrier - 8.0),
        "margin_after_12bps": float(barrier - 12.0),
        "cost_plausibility_class": cost_class,
    }


def classify_support(metrics: Mapping[str, Any]) -> str:
    """Classify support only; cost plausibility does not change this class."""

    valid_fraction = metrics.get("valid_fraction")
    if valid_fraction is None:
        return NOT_USABLE

    valid_fraction = float(valid_fraction)
    directional = int(metrics["directional_touch_count"])
    minority = int(metrics["minority_direction_count"])
    touch_days = int(
        metrics["days_with_any_directional_touch"]
    )
    both_days = int(
        metrics["days_with_both_long_and_short"]
    )

    if valid_fraction < MATERIAL_MIN_VALID_FRACTION:
        return NOT_USABLE

    if (
        valid_fraction >= ROBUST_MIN_VALID_FRACTION
        and directional >= ROBUST_MIN_DIRECTIONAL_TOUCHES
        and minority >= ROBUST_MIN_MINORITY_DIRECTION
        and touch_days >= ROBUST_MIN_TOUCH_DAYS
        and both_days >= ROBUST_MIN_BOTH_DIRECTION_DAYS
    ):
        return ROBUST_SUPPORT

    if (
        valid_fraction >= USABLE_MIN_VALID_FRACTION
        and directional >= USABLE_MIN_DIRECTIONAL_TOUCHES
        and minority >= USABLE_MIN_MINORITY_DIRECTION
        and touch_days >= USABLE_MIN_TOUCH_DAYS
    ):
        return USABLE_SUPPORT

    if directional >= THIN_MIN_DIRECTIONAL_TOUCHES:
        return THIN_SUPPORT

    return NOT_USABLE


def _support_reason(metrics: Mapping[str, Any]) -> str:
    cost = metrics["cost_plausibility"]
    touch_time = metrics["time_to_first_barrier_ms"]["median"]
    return (
        f"support_class={metrics['support_class']}; "
        f"directional_touch_count="
        f"{metrics['directional_touch_count']}; "
        f"minority_direction_count="
        f"{metrics['minority_direction_count']}; "
        f"days_with_any_directional_touch="
        f"{metrics['days_with_any_directional_touch']}; "
        f"days_with_both_long_and_short="
        f"{metrics['days_with_both_long_and_short']}; "
        f"direction_balance_ratio="
        f"{metrics['direction_balance_ratio']}; "
        f"median_time_to_first_barrier_ms={touch_time}; "
        f"gross_barrier_bps={cost['gross_barrier_bps']}; "
        f"margin_after_8bps={cost['margin_after_8bps']}; "
        f"margin_after_12bps={cost['margin_after_12bps']}; "
        f"cost_plausibility_class="
        f"{cost['cost_plausibility_class']}"
    )


def _touch_time_fraction(metrics: Mapping[str, Any]) -> float:
    median_ms = metrics["time_to_first_barrier_ms"]["median"]
    if median_ms is None:
        return math.inf
    return float(median_ms) / (
        float(metrics["horizon_seconds"]) * 1_000.0
    )


def _within_bucket_key(
    metrics: Mapping[str, Any],
) -> tuple[Any, ...]:
    balance = metrics["direction_balance_ratio"]
    return (
        -int(metrics["days_with_any_directional_touch"]),
        -int(metrics["days_with_both_long_and_short"]),
        -float(balance if balance is not None else 0.0),
        _touch_time_fraction(metrics),
        -int(metrics["minority_direction_count"]),
        -int(metrics["directional_touch_count"]),
        -float(metrics["valid_fraction"] or 0.0),
        int(metrics["horizon_seconds"]),
        int(metrics["barrier_bps"]),
    )


def _advisory_shortlist(
    ranked: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Select diverse support/cost alternatives without choosing a target."""

    cost_order = (
        POSITIVE_AFTER_12,
        POSITIVE_AFTER_8_ONLY,
        COST_CHALLENGED,
    )
    shortlist: list[dict[str, Any]] = []

    # Support class remains primary. Within ROBUST and then USABLE, selection
    # is round-robin across cost classes. Tiny barriers therefore cannot occupy
    # every slot solely because they generate more labels.
    for support_class in (ROBUST_SUPPORT, USABLE_SUPPORT):
        buckets = {
            cost_class: sorted(
                [
                    row
                    for row in ranked
                    if row["support_class"] == support_class
                    and row["cost_plausibility"][
                        "cost_plausibility_class"
                    ]
                    == cost_class
                ],
                key=_within_bucket_key,
            )
            for cost_class in cost_order
        }

        while (
            any(
                buckets[cost_class]
                for cost_class in cost_order
            )
            and len(shortlist) < SHORTLIST_MAX_GEOMETRIES
        ):
            for cost_class in cost_order:
                if not buckets[cost_class]:
                    continue

                row = buckets[cost_class].pop(0)
                shortlist.append(
                    {
                        "horizon_seconds": int(
                            row["horizon_seconds"]
                        ),
                        "barrier_bps": int(row["barrier_bps"]),
                        "support_class": str(
                            row["support_class"]
                        ),
                        "cost_plausibility_class": str(
                            row["cost_plausibility"][
                                "cost_plausibility_class"
                            ]
                        ),
                        "reason": str(row["support_reason"]),
                    }
                )
                if (
                    len(shortlist)
                    == SHORTLIST_MAX_GEOMETRIES
                ):
                    break

        if len(shortlist) == SHORTLIST_MAX_GEOMETRIES:
            break

    return shortlist


def rank_and_shortlist(
    pooled_results: Sequence[Mapping[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    support_priority = {
        ROBUST_SUPPORT: 0,
        USABLE_SUPPORT: 1,
        THIN_SUPPORT: 2,
        NOT_USABLE: 3,
    }
    cost_priority = {
        POSITIVE_AFTER_12: 0,
        POSITIVE_AFTER_8_ONLY: 1,
        COST_CHALLENGED: 2,
    }

    enriched: list[dict[str, Any]] = []
    for row in pooled_results:
        current = dict(row)
        current["support_class"] = classify_support(current)
        current["support_reason"] = _support_reason(current)
        enriched.append(current)

    ranked = sorted(
        enriched,
        key=lambda row: (
            support_priority[str(row["support_class"])],
            cost_priority[
                str(
                    row["cost_plausibility"][
                        "cost_plausibility_class"
                    ]
                )
            ],
            *_within_bucket_key(row),
        ),
    )

    for index, row in enumerate(ranked, start=1):
        row["support_rank"] = index

    shortlist = _advisory_shortlist(ranked)

    # A low barrier is never discarded merely for being cost challenged.
    # It remains in the full diagnostic ranking and may occupy one diverse
    # shortlist slot if its independent support class warrants inclusion.
    discards = [
        {
            "horizon_seconds": int(row["horizon_seconds"]),
            "barrier_bps": int(row["barrier_bps"]),
            "support_class": str(row["support_class"]),
            "cost_plausibility_class": str(
                row["cost_plausibility"][
                    "cost_plausibility_class"
                ]
            ),
            "reason": str(row["support_reason"]),
        }
        for row in ranked
        if row["support_class"] == NOT_USABLE
    ]

    return ranked, shortlist, discards


def _verify_loaded_day(
    day_data: DayData,
    expected_day: date,
) -> None:
    if (
        day_data.day != expected_day
        or len(day_data.ts) != EXPECTED_ROWS
    ):
        raise AuditProtocolError(
            "loaded historical day identity/row count mismatch"
        )

    start_us = int(
        datetime(
            expected_day.year,
            expected_day.month,
            expected_day.day,
            tzinfo=timezone.utc,
        ).timestamp()
        * 1_000_000
    )

    if int(day_data.ts[0]) != start_us:
        raise AuditProtocolError(
            "historical day does not start at UTC midnight"
        )
    if int(day_data.ts[-1]) != start_us + DAY_US - GRID_US:
        raise AuditProtocolError(
            "historical day does not end at 23:59:59.750 UTC"
        )
    if not bool(np.all(np.diff(day_data.ts) == GRID_US)):
        raise AuditProtocolError(
            "historical day is not an exact 250 ms grid"
        )


def scientific_configuration() -> dict[str, Any]:
    return {
        "symbol": SYMBOL,
        "historical_days": [
            day.isoformat()
            for day in HISTORICAL_DAYS
        ],
        "feature_root": str(FEATURE_ROOT),
        "decision_step_seconds": 60,
        "decision_timestamp_rule": (
            "timestamp_us % 60000000 == 0"
        ),
        "latency_ms": LATENCY_MS,
        "horizons_seconds": list(HORIZONS_SECONDS),
        "barriers_bps": list(BARRIERS_BPS),
        "total_target_geometries": (
            len(HORIZONS_SECONDS) * len(BARRIERS_BPS)
        ),
        "percentile_method": "linear",
        "cost_reference_bps": list(
            ADDITIONAL_COST_REFERENCES_BPS
        ),
        "cost_plausibility_classes": {
            COST_CHALLENGED: "gross barrier <= 8 bp",
            POSITIVE_AFTER_8_ONLY: (
                "gross barrier > 8 bp and <= 12 bp"
            ),
            POSITIVE_AFTER_12: "gross barrier > 12 bp",
        },
        "support_rules": {
            ROBUST_SUPPORT: {
                "minimum_valid_fraction": (
                    ROBUST_MIN_VALID_FRACTION
                ),
                "minimum_pooled_directional_touches": (
                    ROBUST_MIN_DIRECTIONAL_TOUCHES
                ),
                "minimum_pooled_minority_direction": (
                    ROBUST_MIN_MINORITY_DIRECTION
                ),
                "minimum_days_with_directional_touch": (
                    ROBUST_MIN_TOUCH_DAYS
                ),
                "minimum_days_with_both_directions": (
                    ROBUST_MIN_BOTH_DIRECTION_DAYS
                ),
            },
            USABLE_SUPPORT: {
                "minimum_valid_fraction": (
                    USABLE_MIN_VALID_FRACTION
                ),
                "minimum_pooled_directional_touches": (
                    USABLE_MIN_DIRECTIONAL_TOUCHES
                ),
                "minimum_pooled_minority_direction": (
                    USABLE_MIN_MINORITY_DIRECTION
                ),
                "minimum_days_with_directional_touch": (
                    USABLE_MIN_TOUCH_DAYS
                ),
            },
            THIN_SUPPORT: {
                "minimum_pooled_directional_touches": (
                    THIN_MIN_DIRECTIONAL_TOUCHES
                ),
                "must_not_satisfy": USABLE_SUPPORT,
            },
            NOT_USABLE: {
                "pooled_directional_touches_below": (
                    THIN_MIN_DIRECTIONAL_TOUCHES
                ),
                "or_valid_fraction_below": (
                    MATERIAL_MIN_VALID_FRACTION
                ),
            },
            "shortlist_max_geometries": (
                SHORTLIST_MAX_GEOMETRIES
            ),
            "shortlist_policy": (
                "support class is primary; within ROBUST then USABLE, "
                "round-robin across cost-plausibility classes, then "
                "prefer cross-day persistence, LONG/SHORT balance, "
                "faster relative touch timing, minority support, and "
                "total support"
            ),
        },
        "economic_scope": (
            "barrier-minus-cost plausibility only; no spread double "
            "subtraction, strategy PnL, leverage, or profitability claim"
        ),
    }


def _guards() -> dict[str, Any]:
    return {
        "AUG30_ANALYTICALLY_OPENED": False,
        "SEP01_OR_LATER_ANALYTICALLY_OPENED": False,
        "MODEL_FIT_RUN": False,
        "DIRECTION_MODEL_RUN": False,
        "OPPORTUNITY_THRESHOLD_OPTIMIZED": False,
        "PNL_BACKTEST_RUN": False,
        "LEVERAGE_SCORED": False,
        "EXP024_MODIFIED": False,
        "EXP029_RERUN": False,
        "EXP029_MODIFIED": False,
        "EXP025_MODIFIED": False,
        "EXP027_MODIFIED": False,
        "MARKET_DATA_READ": "JAN_JUL_BTC_PHASE0DL_ONLY",
    }


def _descriptive_findings(
    ranked: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    invalid_sorted = sorted(
        ranked,
        key=lambda row: float(
            row["invalid_fraction"] or 0.0
        ),
        reverse=True,
    )
    directional = [
        row
        for row in ranked
        if int(row["directional_touch_count"]) > 0
    ]
    balance_sorted = sorted(
        directional,
        key=lambda row: float(
            row["direction_balance_ratio"] or 0.0
        ),
        reverse=True,
    )
    touch_medians = [
        float(row["time_to_first_barrier_ms"]["median"])
        for row in directional
        if row["time_to_first_barrier_ms"]["median"]
        is not None
    ]

    return {
        "highest_invalid_fraction_geometry": (
            {
                "horizon_seconds": int(
                    invalid_sorted[0]["horizon_seconds"]
                ),
                "barrier_bps": int(
                    invalid_sorted[0]["barrier_bps"]
                ),
                "invalid_fraction": invalid_sorted[0][
                    "invalid_fraction"
                ],
                "invalid_counts_by_reason": invalid_sorted[0][
                    "invalid_counts_by_reason"
                ],
            }
            if invalid_sorted
            else None
        ),
        "most_balanced_directional_geometry": (
            {
                "horizon_seconds": int(
                    balance_sorted[0]["horizon_seconds"]
                ),
                "barrier_bps": int(
                    balance_sorted[0]["barrier_bps"]
                ),
                "direction_balance_ratio": balance_sorted[0][
                    "direction_balance_ratio"
                ],
            }
            if balance_sorted
            else None
        ),
        "pooled_touch_time_median_ms_range": (
            {
                "minimum": min(touch_medians),
                "maximum": max(touch_medians),
            }
            if touch_medians
            else None
        ),
        "cost_interpretation": (
            "Margins are gross barrier minus 8/12 bp additional-cost "
            "references; they are not realized returns or profitability "
            "estimates."
        ),
    }


def _summary_markdown(
    payload: Mapping[str, Any],
    audit_json_sha256: str,
) -> str:
    lines = [
        "# DEV030-P1 Label Feasibility Summary",
        "",
        f"Status: `{payload['status']}`",
        "",
        (
            "This is a label-support audit only. "
            "It fits no model and reports no PnL."
        ),
        "",
        f"JSON artifact SHA-256: `{audit_json_sha256}`",
        "",
        (
            "| Horizon | Barrier | Valid fraction | Directional touches "
            "| Minority direction | Touch fraction | Touch days | Support "
            "| Cost class | Margin after 8 bp | Margin after 12 bp |"
        ),
        (
            "|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|"
        ),
    ]

    for row in payload["support_classification"][
        "ranked_geometries"
    ]:
        valid_fraction = row["valid_fraction"]
        touch_fraction = row[
            "directional_touch_fraction_of_valid"
        ]
        lines.append(
            "| {h} | {b} | {vf} | {touches} | {minority} | "
            "{tf} | {days} | {support} | {cost_class} | "
            "{m8:.1f} | {m12:.1f} |".format(
                h=row["horizon_seconds"],
                b=row["barrier_bps"],
                vf=(
                    "null"
                    if valid_fraction is None
                    else f"{valid_fraction:.6f}"
                ),
                touches=row["directional_touch_count"],
                minority=row["minority_direction_count"],
                tf=(
                    "null"
                    if touch_fraction is None
                    else f"{touch_fraction:.6f}"
                ),
                days=row["days_with_any_directional_touch"],
                support=row["support_class"],
                cost_class=row["cost_plausibility"][
                    "cost_plausibility_class"
                ],
                m8=row["cost_plausibility"][
                    "margin_after_8bps"
                ],
                m12=row["cost_plausibility"][
                    "margin_after_12bps"
                ],
            )
        )

    lines.extend(["", "## Advisory shortlist", ""])
    shortlist = payload["support_classification"]["shortlist"]
    if shortlist:
        for row in shortlist:
            lines.append(
                f"- {row['horizon_seconds']}s / "
                f"{row['barrier_bps']} bp — {row['reason']}"
            )
    else:
        lines.append(
            "- None under the current transparent support heuristics."
        )

    lines.extend(["", "## Obvious discards", ""])
    discards = payload["support_classification"][
        "obvious_discards"
    ]
    if discards:
        for row in discards:
            lines.append(
                f"- {row['horizon_seconds']}s / "
                f"{row['barrier_bps']} bp — {row['reason']}"
            )
    else:
        lines.append("- None.")

    lines.extend(["", "## Guards", ""])
    for name, value in payload["guards"].items():
        lines.append(f"- `{name}` = `{value}`")

    return "\n".join(lines) + "\n"


def _assert_json_safe(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _assert_output_absent(output_directory: Path) -> None:
    if output_directory.exists():
        raise FileExistsError(
            f"output directory already exists: {output_directory}"
        )


def _write_file_once(path: Path, content: bytes) -> str:
    part = path.with_name(path.name + ".part")
    if path.exists() or part.exists():
        raise FileExistsError(
            f"refusing to overwrite output or partial: {path}"
        )

    descriptor = os.open(
        part,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o644,
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(part, path)
    return hashlib.sha256(content).hexdigest()


def run_label_feasibility(
    *,
    workspace: Path,
    output_directory: Path,
    argv: Sequence[str] | None = None,
) -> RunResult:
    # Phase-B ordering is deliberate:
    # 1. verify committed lineage, clean tracked tree, tracked implementation,
    #    and frozen EXP029 opaque digest;
    # 2. refuse an existing output;
    # 3. hash the seven explicit Jan-Jul inputs;
    # 4. only then load Jan-Jul analytically.
    workspace_info = verify_workspace(workspace)
    _assert_output_absent(output_directory)
    input_manifest = verify_input_manifest()

    started_at = datetime.now(timezone.utc).isoformat()
    per_day_results: list[dict[str, Any]] = []
    pooled_accumulators = {
        (horizon, barrier): RecordAccumulator()
        for horizon in HORIZONS_SECONDS
        for barrier in BARRIERS_BPS
    }

    for input_record in input_manifest:
        current_day = date.fromisoformat(
            str(input_record["date"])
        )
        expected_path = authorized_feature_path(current_day)
        if Path(str(input_record["path"])) != expected_path:
            raise AuditProtocolError(
                "input manifest path authorization mismatch"
            )

        loaded = _load_day(expected_path, current_day)
        _verify_loaded_day(loaded, current_day)
        decisions = minute_decision_indices(loaded.ts)

        for horizon in HORIZONS_SECONDS:
            for barrier in BARRIERS_BPS:
                records = label_first_passage_targets(
                    loaded,
                    decisions,
                    horizon_seconds=horizon,
                    barrier_bps=barrier,
                    latency_ms=LATENCY_MS,
                )
                accumulator = RecordAccumulator()
                accumulator.extend(records)
                summary = accumulator.summary()

                per_day_results.append(
                    {
                        "date": current_day.isoformat(),
                        "horizon_seconds": int(horizon),
                        "barrier_bps": int(barrier),
                        **summary,
                    }
                )
                pooled_accumulators[
                    (horizon, barrier)
                ].merge(accumulator)

        del loaded

    pooled_results: list[dict[str, Any]] = []
    for horizon in HORIZONS_SECONDS:
        for barrier in BARRIERS_BPS:
            day_rows = [
                row
                for row in per_day_results
                if row["horizon_seconds"] == horizon
                and row["barrier_bps"] == barrier
            ]
            pooled = pooled_day_metrics(
                pooled_accumulators[
                    (horizon, barrier)
                ].summary(),
                day_rows,
            )
            pooled_results.append(
                {
                    "horizon_seconds": int(horizon),
                    "barrier_bps": int(barrier),
                    **pooled,
                    "cost_plausibility": cost_plausibility(
                        barrier
                    ),
                }
            )

    ranked, shortlist, discards = rank_and_shortlist(
        pooled_results
    )

    source_hashes = {
        "source_sha256": _sha256_file(
            workspace / SOURCE_REL
        ),
        "test_sha256": _sha256_file(
            workspace / TEST_REL
        ),
        "first_passage_source_sha256": _sha256_file(
            workspace / FIRST_PASSAGE_REL
        ),
        "design_document_sha256": _sha256_file(
            workspace / DESIGN_REL
        ),
    }

    payload: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "status": STATUS,
        "scope": "LABEL_ONLY_FEASIBILITY_AUDIT",
        "started_at_utc": started_at,
        "finished_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "execution_argv": list(
            argv if argv is not None else sys.argv
        ),
        "workspace_provenance": workspace_info,
        "environment": {
            "python_version": platform.python_version(),
            "python_implementation": (
                platform.python_implementation()
            ),
            "platform": platform.platform(),
            "numpy_version": np.__version__,
        },
        "source_provenance": source_hashes,
        "input_manifest": input_manifest,
        "configuration": scientific_configuration(),
        "per_day_results": per_day_results,
        "pooled_results": pooled_results,
        "support_classification": {
            "ranked_geometries": ranked,
            "shortlist": shortlist,
            "obvious_discards": discards,
            "selection_semantics": (
                "descriptive advisory only; no final target selected"
            ),
        },
        "descriptive_findings": _descriptive_findings(ranked),
        "guards": _guards(),
        "artifact_sha256_semantics": (
            "computed externally after atomic write; "
            "not recursively embedded"
        ),
    }

    encoded_json = _assert_json_safe(payload)
    json_digest = hashlib.sha256(encoded_json).hexdigest()
    encoded_summary = _summary_markdown(
        payload,
        json_digest,
    ).encode("utf-8")

    _assert_output_absent(output_directory)
    output_directory.mkdir(parents=True, exist_ok=False)

    audit_json_sha256 = _write_file_once(
        output_directory / AUDIT_JSON_NAME,
        encoded_json,
    )
    audit_summary_sha256 = _write_file_once(
        output_directory / AUDIT_SUMMARY_NAME,
        encoded_summary,
    )

    try:
        directory_descriptor = os.open(
            output_directory,
            os.O_RDONLY,
        )
    except OSError:
        directory_descriptor = None

    if directory_descriptor is not None:
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)

    return RunResult(
        payload,
        audit_json_sha256,
        audit_summary_sha256,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="DEV030-P1 label feasibility audit"
    )
    parser.add_argument(
        "--mode",
        choices=("label-feasibility",),
        required=True,
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        required=True,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    effective_argv = (
        list(argv)
        if argv is not None
        else sys.argv[1:]
    )

    result = run_label_feasibility(
        workspace=args.workspace,
        output_directory=args.output_directory,
        argv=effective_argv,
    )

    print(
        json.dumps(
            {
                "output_directory": str(
                    args.output_directory
                ),
                "audit_json_sha256": (
                    result.audit_json_sha256
                ),
                "audit_summary_sha256": (
                    result.audit_summary_sha256
                ),
                "status": result.payload["status"],
            },
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

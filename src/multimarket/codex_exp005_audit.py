from __future__ import annotations

import argparse
import csv
import gzip
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .codex_exp005_acquire import DAYS, EXCHANGE, DATA_TYPE, SYMBOLS, DatasetRequest, frozen_requests
from .codex_research import assert_unsealed_path, canonical_sha256, sha256_file

EXPERIMENT_ID = "CODEX-EXP-005-P0"
DAY_US = 86_400_000_000
MINUTE_US = 60_000_000
DECISION_GRID_US = np.arange(0, DAY_US, MINUTE_US, dtype=np.int64)

FIELD_ALIASES = {
    "local_timestamp": ("local_timestamp", "receipt_timestamp"),
    "timestamp": ("timestamp", "exchange_timestamp"),
    "open_interest": ("open_interest",),
    "funding_timestamp": ("funding_timestamp",),
    "funding_rate": ("funding_rate",),
    "predicted_funding_rate": ("predicted_funding_rate", "next_funding_rate"),
    "last_price": ("last_price",),
    "mark_price": ("mark_price",),
    "index_price": ("index_price",),
}
NUMERIC_FIELDS = (
    "open_interest",
    "funding_rate",
    "predicted_funding_rate",
    "last_price",
    "mark_price",
    "index_price",
)


@dataclass(frozen=True)
class SchemaClassification:
    availability_timestamp: str | None
    event_timestamp: str | None
    open_interest: str
    funding: str
    mark_price: str
    index_price: str
    premium: str


def _resolve(columns: tuple[str, ...], aliases: tuple[str, ...]) -> str | None:
    hits = [name for name in aliases if name in columns]
    if len(hits) > 1:
        raise RuntimeError(f"ambiguous schema aliases: {hits}")
    return hits[0] if hits else None


def classify_schema(columns: tuple[str, ...]) -> tuple[SchemaClassification, dict[str, str | None]]:
    resolved = {key: _resolve(columns, aliases) for key, aliases in FIELD_ALIASES.items()}
    availability = resolved["local_timestamp"] or resolved["timestamp"]
    funding_native = bool(resolved["funding_rate"] or resolved["predicted_funding_rate"])
    mark_native = bool(resolved["mark_price"])
    index_native = bool(resolved["index_price"])
    return (
        SchemaClassification(
            availability_timestamp=availability,
            event_timestamp=resolved["timestamp"],
            open_interest="PRESENT_NATIVE" if resolved["open_interest"] else "ABSENT",
            funding="PRESENT_NATIVE" if funding_native else "ABSENT",
            mark_price="PRESENT_NATIVE" if mark_native else "ABSENT",
            index_price="PRESENT_NATIVE" if index_native else "ABSENT",
            premium="DERIVABLE_CAUSALLY" if mark_native and index_native else "ABSENT",
        ),
        resolved,
    )


def parse_timestamp_us(value: str) -> int:
    value = value.strip()
    if not value:
        raise ValueError("empty timestamp")
    if value.lstrip("-").isdigit():
        raw = int(value)
        magnitude = abs(raw)
        if magnitude < 10**11:
            return raw * 1_000_000
        if magnitude < 10**14:
            return raw * 1_000
        if magnitude < 10**17:
            return raw
        return raw // 1_000
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1_000_000)


def _parse_numeric(value: str | None) -> tuple[float, bool]:
    """Return (numeric-or-NaN, malformed). Empty native fields are missing, not malformed."""
    if value is None or not str(value).strip():
        return float("nan"), False
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return float("nan"), True
    if not np.isfinite(parsed):
        return float("nan"), True
    return parsed, False


def deterministic_order_and_deduplicate(
    timestamps: np.ndarray,
    rows: list[dict[str, str]],
) -> tuple[np.ndarray, list[dict[str, str]], int]:
    """Stable receipt-time order; remove exact duplicate rows only.

    Multiple distinct rows at the same receipt timestamp are preserved in original file order.
    """
    if len(timestamps) != len(rows):
        raise ValueError("timestamp/row length mismatch")
    order = np.argsort(timestamps, kind="stable")
    ordered_ts = timestamps[order]
    ordered_rows = [rows[int(i)] for i in order]
    seen: set[tuple[tuple[str, str], ...]] = set()
    keep_ts: list[int] = []
    keep_rows: list[dict[str, str]] = []
    duplicate_count = 0
    for ts, row in zip(ordered_ts.tolist(), ordered_rows):
        key = tuple(sorted((str(k), str(v)) for k, v in row.items()))
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        keep_ts.append(int(ts))
        keep_rows.append(row)
    return np.asarray(keep_ts, dtype=np.int64), keep_rows, duplicate_count


def gap_stats(timestamps_us: np.ndarray) -> dict[str, float | int | None]:
    if len(timestamps_us) < 2:
        return {"median_us": None, "p90_us": None, "p99_us": None, "longest_us": None}
    delta = np.diff(timestamps_us.astype(np.int64))
    return {
        "median_us": float(np.median(delta)),
        "p90_us": float(np.quantile(delta, 0.90)),
        "p99_us": float(np.quantile(delta, 0.99)),
        "longest_us": int(delta.max()),
    }


def asof_indices(record_timestamps_us: np.ndarray, decision_timestamps_us: np.ndarray) -> np.ndarray:
    return np.searchsorted(record_timestamps_us, decision_timestamps_us, side="right") - 1


def asof_values(
    update_timestamps_us: np.ndarray,
    update_values: np.ndarray,
    decision_timestamps_us: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Past-only state reconstruction from native finite field updates."""
    if len(update_timestamps_us) != len(update_values):
        raise ValueError("update timestamp/value length mismatch")
    idx = asof_indices(update_timestamps_us, decision_timestamps_us)
    values = np.full(len(decision_timestamps_us), np.nan, dtype=np.float64)
    source_ts = np.full(len(decision_timestamps_us), -1, dtype=np.int64)
    valid = idx >= 0
    if np.any(valid):
        values[valid] = update_values[idx[valid]]
        source_ts[valid] = update_timestamps_us[idx[valid]]
    return values, source_ts


def decision_coverage(
    update_timestamps_us: np.ndarray,
    decision_timestamps_us: np.ndarray,
    *,
    max_staleness_us: int | None = None,
) -> dict[str, float | int]:
    idx = asof_indices(update_timestamps_us, decision_timestamps_us)
    covered = idx >= 0
    if max_staleness_us is not None and np.any(covered):
        loc = np.flatnonzero(covered)
        covered[loc] &= (
            decision_timestamps_us[loc] - update_timestamps_us[idx[loc]]
        ) <= max_staleness_us
    return {
        "covered": int(covered.sum()),
        "total": int(len(covered)),
        "fraction": float(np.mean(covered)),
    }


def _numeric_stats(raw_values: np.ndarray, update_timestamps: np.ndarray) -> dict[str, Any]:
    finite = np.isfinite(raw_values)
    v = raw_values[finite]
    return {
        "finite_native_updates": int(finite.sum()),
        "native_missing_fraction": float(1.0 - np.mean(finite)) if len(raw_values) else 1.0,
        "zero_fraction_of_finite_updates": float(np.mean(v == 0.0)) if len(v) else None,
        "unique_values": int(len(np.unique(v))) if len(v) else 0,
        "first_native_update_timestamp_us": int(update_timestamps[0]) if len(update_timestamps) else None,
        "last_native_update_timestamp_us": int(update_timestamps[-1]) if len(update_timestamps) else None,
        "native_update_gaps": gap_stats(update_timestamps),
    }


def _read_file(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    assert_unsealed_path(path)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        rows = [dict(row) for row in reader]
    if not columns or not rows:
        raise RuntimeError(f"empty derivative ticker file: {path}")
    return columns, rows


def _field_updates(
    rows: list[dict[str, str]],
    timestamps: np.ndarray,
    column: str,
) -> tuple[np.ndarray, np.ndarray, int]:
    values: list[float] = []
    update_ts: list[int] = []
    malformed = 0
    for row, ts in zip(rows, timestamps.tolist()):
        value, bad = _parse_numeric(row.get(column))
        malformed += int(bad)
        if np.isfinite(value):
            values.append(value)
            update_ts.append(int(ts))
    return np.asarray(update_ts, dtype=np.int64), np.asarray(values, dtype=np.float64), malformed


def audit_file(request: DatasetRequest, raw_root: Path) -> dict[str, Any]:
    path = request.output_path(raw_root)
    if not path.exists():
        raise FileNotFoundError(path)
    columns, rows = _read_file(path)
    classification, resolved = classify_schema(columns)
    if classification.availability_timestamp is None:
        raise RuntimeError(f"no causal availability timestamp: {path}")

    availability_col = classification.availability_timestamp
    parsed_ts: list[int] = []
    timestamp_good: list[bool] = []
    malformed_timestamp_rows = 0
    for row in rows:
        try:
            parsed_ts.append(parse_timestamp_us(row.get(availability_col, "")))
            timestamp_good.append(True)
        except Exception:
            parsed_ts.append(-1)
            timestamp_good.append(False)
            malformed_timestamp_rows += 1
    raw_ts = np.asarray(parsed_ts, dtype=np.int64)
    good = np.asarray(timestamp_good, dtype=bool)
    valid_raw_ts = raw_ts[good]
    timestamp_regressions = int(np.sum(np.diff(valid_raw_ts) < 0)) if len(valid_raw_ts) >= 2 else 0
    valid_rows = [row for row, ok in zip(rows, good.tolist()) if ok]
    ts, ordered_rows, duplicate_count = deterministic_order_and_deduplicate(valid_raw_ts, valid_rows)

    day_start = int(
        datetime(request.day.year, request.day.month, request.day.day, tzinfo=timezone.utc).timestamp()
        * 1_000_000
    )
    decisions = day_start + DECISION_GRID_US

    fields: dict[str, Any] = {}
    updates: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    malformed_numeric_cells = 0
    nonblank_numeric_cells = 0

    for canonical in NUMERIC_FIELDS:
        column = resolved.get(canonical)
        if column is None:
            continue
        for row in ordered_rows:
            raw = row.get(column)
            if raw is not None and str(raw).strip():
                nonblank_numeric_cells += 1
        uts, vals, malformed = _field_updates(ordered_rows, ts, column)
        malformed_numeric_cells += malformed
        updates[canonical] = (uts, vals)
        stats = _numeric_stats(
            np.asarray([_parse_numeric(row.get(column))[0] for row in ordered_rows]), uts
        )
        stats["malformed_nonblank_values"] = malformed
        stats["decision_coverage_no_staleness_limit"] = decision_coverage(uts, decisions)
        fields[canonical] = stats

    if "open_interest" in updates:
        uts, oi = updates["open_interest"]
        rel = np.abs(np.diff(oi) / oi[:-1]) if len(oi) > 1 else np.empty(0)
        fields["open_interest"].update(
            {
                "non_positive_count": int(np.sum(oi <= 0)),
                "one_step_relative_change_gt_10pct": int(np.sum(rel > 0.10)),
                "unchanged_update_fraction": float(np.mean(np.diff(oi) == 0)) if len(oi) > 1 else None,
            }
        )

    funding_name = None
    if "funding_rate" in updates:
        funding_name = "funding_rate"
    elif "predicted_funding_rate" in updates:
        funding_name = "predicted_funding_rate"
    if funding_name:
        _, funding = updates[funding_name]
        fields[funding_name].update(
            {
                "actual_changes": int(np.sum(np.diff(funding) != 0)) if len(funding) > 1 else 0,
                "scheduled_or_stepwise": bool(
                    len(funding) > 1 and np.mean(np.diff(funding) == 0) >= 0.50
                ),
            }
        )

    premium_stats = None
    if "mark_price" in updates and "index_price" in updates:
        mark_ts, mark_values = updates["mark_price"]
        index_ts, index_values = updates["index_price"]
        mark_state, mark_source = asof_values(mark_ts, mark_values, decisions)
        index_state, index_source = asof_values(index_ts, index_values, decisions)
        good_premium = (
            np.isfinite(mark_state)
            & np.isfinite(index_state)
            & (mark_state > 0)
            & (index_state > 0)
        )
        premium = np.full(len(decisions), np.nan, dtype=np.float64)
        premium[good_premium] = 10_000.0 * (
            mark_state[good_premium] / index_state[good_premium] - 1.0
        )
        pv = premium[good_premium]
        premium_stats = {
            "decision_grid_finite_count": int(good_premium.sum()),
            "decision_coverage_no_staleness_limit": {
                "covered": int(good_premium.sum()),
                "total": int(len(decisions)),
                "fraction": float(np.mean(good_premium)),
            },
            "median_abs_bps": float(np.median(np.abs(pv))) if len(pv) else None,
            "p95_abs_bps": float(np.quantile(np.abs(pv), 0.95)) if len(pv) else None,
            "sign_changes_on_decision_grid": int(
                np.sum(np.sign(pv[1:]) != np.sign(pv[:-1]))
            ) if len(pv) > 1 else 0,
            "mark_source_staleness_us": gap_stats(np.unique(mark_source[mark_source >= 0])),
            "index_source_staleness_us": gap_stats(np.unique(index_source[index_source >= 0])),
            "impossible_native_price_updates": int(np.sum(mark_values <= 0) + np.sum(index_values <= 0)),
        }

    day_coverage = (
        float(max(0, min(DAY_US, int(ts[-1]) - int(ts[0]))) / DAY_US) if len(ts) else 0.0
    )
    malformed_fraction = (
        float(malformed_numeric_cells / nonblank_numeric_cells)
        if nonblank_numeric_cells
        else 0.0
    )

    return {
        "symbol": request.symbol,
        "day": request.day.isoformat(),
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "columns": list(columns),
        "schema": {
            "availability_timestamp": classification.availability_timestamp,
            "event_timestamp": classification.event_timestamp,
            "availability_uses_local_receipt": classification.availability_timestamp == resolved["local_timestamp"],
            "open_interest": classification.open_interest,
            "funding": classification.funding,
            "mark_price": classification.mark_price,
            "index_price": classification.index_price,
            "premium": classification.premium,
        },
        "raw_rows": len(rows),
        "retained_rows_after_timestamp_and_exact_duplicate_resolution": len(ts),
        "malformed_timestamp_rows": malformed_timestamp_rows,
        "timestamp_regressions_raw_file_order": timestamp_regressions,
        "exact_duplicate_rows": duplicate_count,
        "first_availability_timestamp_us": int(ts[0]) if len(ts) else None,
        "last_availability_timestamp_us": int(ts[-1]) if len(ts) else None,
        "day_coverage_fraction": day_coverage,
        "record_update_gaps": gap_stats(ts),
        "malformed_nonblank_numeric_cells": malformed_numeric_cells,
        "nonblank_numeric_cells": nonblank_numeric_cells,
        "malformed_nonblank_numeric_fraction": malformed_fraction,
        "fields": fields,
        "premium": premium_stats,
    }


def _git_ignored(workspace: Path, raw_root: Path) -> bool:
    workspace = workspace.resolve()
    raw_root = raw_root.resolve()
    try:
        relative = raw_root.relative_to(workspace)
    except ValueError:
        return False
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", str(relative)],
        cwd=workspace,
        text=True,
    )
    return result.returncode == 0


def readiness(audits: list[dict[str, Any]], *, raw_ignored: bool) -> dict[str, Any]:
    if len(audits) != 14:
        return {
            "status": "FAIL_DERIVATIVES_DATA_NOT_READY",
            "gates": {"all_14_files": False},
        }

    def field_present(row: dict[str, Any], name: str) -> bool:
        return row["schema"].get(name) in {"PRESENT_NATIVE", "DERIVABLE_CAUSALLY"}

    oi_native = all(field_present(row, "open_interest") for row in audits)
    premium_available = all(field_present(row, "premium") for row in audits)
    availability_defined = all(row["schema"]["availability_timestamp"] is not None for row in audits)
    malformed_ok = all(row["malformed_nonblank_numeric_fraction"] <= 0.05 for row in audits)

    oi_symbol_cov: dict[str, float] = {}
    premium_symbol_cov: dict[str, float] = {}
    for symbol in SYMBOLS:
        selected = [row for row in audits if row["symbol"] == symbol]
        oi_cov = [
            row["fields"].get("open_interest", {})
            .get("decision_coverage_no_staleness_limit", {})
            .get("fraction", 0.0)
            for row in selected
        ]
        oi_symbol_cov[symbol] = float(np.mean(oi_cov)) if oi_cov else 0.0
        premium_cov = [
            row.get("premium", {})
            .get("decision_coverage_no_staleness_limit", {})
            .get("fraction", 0.0)
            if row.get("premium")
            else 0.0
            for row in selected
        ]
        premium_symbol_cov[symbol] = float(np.mean(premium_cov)) if premium_cov else 0.0

    gates = {
        "all_14_files": True,
        "no_august_accessed": True,
        "causal_availability_timestamp_defined": availability_defined,
        "open_interest_schema_unambiguous": oi_native,
        "open_interest_coverage_each_symbol_at_least_95pct": all(
            value >= 0.95 for value in oi_symbol_cov.values()
        ),
        "malformed_nonblank_numeric_at_most_5pct_each_day": malformed_ok,
        "timestamp_regressions_deterministically_resolved": True,
        "past_only_asof_supported": availability_defined,
        "raw_directory_gitignored": raw_ignored,
    }
    premium_track_ready = premium_available and all(
        value >= 0.95 for value in premium_symbol_cov.values()
    )
    core_ready = all(gates.values())
    if core_ready and premium_track_ready:
        status = "DATA_READY_SANDBOX"
    elif core_ready:
        status = "PARTIAL_DATA_READY"
    else:
        status = "FAIL_DERIVATIVES_DATA_NOT_READY"
    return {
        "status": status,
        "gates": gates,
        "premium_track_ready": premium_track_ready,
        "open_interest_symbol_decision_coverage": oi_symbol_cov,
        "premium_symbol_decision_coverage": premium_symbol_cov,
    }


def run(raw_root: Path, workspace: Path, output: Path) -> dict[str, Any]:
    assert_unsealed_path(raw_root)
    assert_unsealed_path(output)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite audit output: {output}")
    partial = output.with_name(output.name + ".part")
    if partial.exists():
        raise FileExistsError(f"partial audit output exists: {partial}")

    audits = [audit_file(request, raw_root) for request in frozen_requests()]
    ready = readiness(audits, raw_ignored=_git_ignored(workspace, raw_root))
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": ready["status"],
        "configuration_sha256": canonical_sha256(
            {
                "exchange": EXCHANGE,
                "data_type": DATA_TYPE,
                "symbols": SYMBOLS,
                "days": [day.isoformat() for day in DAYS],
                "decision_grid_seconds": 60,
                "coverage_threshold": 0.95,
                "availability_clock": "local_timestamp preferred; timestamp fallback",
                "duplicate_rule": "stable receipt-time sort; remove exact duplicate rows only",
                "field_state_rule": "past-only carry-forward of most recent finite native field update",
            }
        ),
        "raw_root": str(raw_root),
        "file_count": len(audits),
        "files": audits,
        "readiness": ready,
        "sealed_august_opened": False,
        "predictive_model_run": False,
        "pnl_scored": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    partial.replace(output)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CODEX-EXP-005-P0 derivative-state data audit"
    )
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.raw_root, args.workspace, args.output)
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "status": result["status"],
                "file_count": result["file_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

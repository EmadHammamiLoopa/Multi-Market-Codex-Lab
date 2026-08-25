from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
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
    "funding_rate": ("funding_rate",),
    "predicted_funding_rate": ("predicted_funding_rate", "next_funding_rate"),
    "mark_price": ("mark_price",),
    "index_price": ("index_price",),
}


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
    event = resolved["timestamp"]
    mark = "PRESENT_NATIVE" if resolved["mark_price"] else "ABSENT"
    index = "PRESENT_NATIVE" if resolved["index_price"] else "ABSENT"
    premium = "DERIVABLE_CAUSALLY" if resolved["mark_price"] and resolved["index_price"] else "ABSENT"
    funding_present = resolved["funding_rate"] or resolved["predicted_funding_rate"]
    return (
        SchemaClassification(
            availability_timestamp=availability,
            event_timestamp=event,
            open_interest="PRESENT_NATIVE" if resolved["open_interest"] else "ABSENT",
            funding="PRESENT_NATIVE" if funding_present else "ABSENT",
            mark_price=mark,
            index_price=index,
            premium=premium,
        ),
        resolved,
    )


def parse_timestamp_us(value: str) -> int:
    value = value.strip()
    if not value:
        raise ValueError("empty timestamp")
    if value.lstrip("-").isdigit():
        raw = int(value)
        # Tardis CSV timestamps are normally microseconds; tolerate seconds/ms/ns deterministically.
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


def _float_or_nan(value: str | None) -> float:
    if value is None or not str(value).strip():
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def deterministic_deduplicate(timestamps: np.ndarray, rows: list[dict[str, str]]) -> tuple[np.ndarray, list[dict[str, str]], int]:
    if len(timestamps) != len(rows):
        raise ValueError("timestamp/row length mismatch")
    # Stable sort by availability time then original file order; last receipt at an identical
    # timestamp wins. This uses no future values and is deterministic.
    order = np.argsort(timestamps, kind="stable")
    ts = timestamps[order]
    ordered_rows = [rows[int(i)] for i in order]
    keep: list[int] = []
    i = 0
    while i < len(ts):
        j = i + 1
        while j < len(ts) and ts[j] == ts[i]:
            j += 1
        keep.append(j - 1)
        i = j
    duplicate_count = len(ts) - len(keep)
    return ts[keep], [ordered_rows[i] for i in keep], duplicate_count


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
    # Past-only: searchsorted(right)-1 can never select a record after the decision timestamp.
    return np.searchsorted(record_timestamps_us, decision_timestamps_us, side="right") - 1


def decision_coverage(
    record_timestamps_us: np.ndarray,
    decision_timestamps_us: np.ndarray,
    valid_values: np.ndarray,
    *,
    max_staleness_us: int | None = None,
) -> dict[str, float | int]:
    if len(record_timestamps_us) != len(valid_values):
        raise ValueError("record/value length mismatch")
    idx = asof_indices(record_timestamps_us, decision_timestamps_us)
    covered = idx >= 0
    if np.any(covered):
        loc = np.flatnonzero(covered)
        ridx = idx[loc]
        covered[loc] &= valid_values[ridx]
        if max_staleness_us is not None:
            covered[loc] &= (decision_timestamps_us[loc] - record_timestamps_us[ridx]) <= max_staleness_us
    return {"covered": int(covered.sum()), "total": int(len(covered)), "fraction": float(np.mean(covered))}


def _numeric_stats(values: np.ndarray, timestamps: np.ndarray) -> dict[str, Any]:
    finite = np.isfinite(values)
    v = values[finite]
    ts = timestamps[finite]
    return {
        "finite_rows": int(finite.sum()),
        "missing_fraction": float(1.0 - np.mean(finite)) if len(values) else 1.0,
        "zero_fraction": float(np.mean(v == 0.0)) if len(v) else None,
        "unique_values": int(len(np.unique(v))) if len(v) else 0,
        "first_valid_timestamp_us": int(ts[0]) if len(ts) else None,
        "last_valid_timestamp_us": int(ts[-1]) if len(ts) else None,
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


def audit_file(request: DatasetRequest, raw_root: Path) -> dict[str, Any]:
    path = request.output_path(raw_root)
    if not path.exists():
        raise FileNotFoundError(path)
    columns, rows = _read_file(path)
    classification, resolved = classify_schema(columns)
    if classification.availability_timestamp is None:
        raise RuntimeError(f"no causal availability timestamp: {path}")

    availability_col = classification.availability_timestamp
    raw_ts: list[int] = []
    malformed_timestamp_rows = 0
    for row in rows:
        try:
            raw_ts.append(parse_timestamp_us(row.get(availability_col, "")))
        except Exception:
            raw_ts.append(-1)
            malformed_timestamp_rows += 1
    raw_ts_arr = np.asarray(raw_ts, dtype=np.int64)
    good_ts = raw_ts_arr >= 0
    timestamp_regressions = int(np.sum(np.diff(raw_ts_arr[good_ts]) < 0)) if np.sum(good_ts) >= 2 else 0
    filtered_rows = [row for row, good in zip(rows, good_ts.tolist()) if good]
    filtered_ts = raw_ts_arr[good_ts]
    ts, dedup_rows, duplicate_count = deterministic_deduplicate(filtered_ts, filtered_rows)

    day_start = int(datetime(request.day.year, request.day.month, request.day.day, tzinfo=timezone.utc).timestamp() * 1_000_000)
    day_decisions = day_start + DECISION_GRID_US

    fields: dict[str, Any] = {}
    arrays: dict[str, np.ndarray] = {}
    for canonical in ("open_interest", "funding_rate", "predicted_funding_rate", "mark_price", "index_price"):
        column = resolved[canonical]
        if column is None:
            continue
        values = np.asarray([_float_or_nan(row.get(column)) for row in dedup_rows], dtype=np.float64)
        arrays[canonical] = values
        stats = _numeric_stats(values, ts)
        stats["decision_coverage_no_staleness_limit"] = decision_coverage(ts, day_decisions, np.isfinite(values))
        fields[canonical] = stats

    oi = arrays.get("open_interest")
    if oi is not None:
        finite = np.isfinite(oi)
        fv = oi[finite]
        rel = np.abs(np.diff(fv) / fv[:-1]) if len(fv) > 1 else np.empty(0)
        fields["open_interest"].update(
            {
                "non_positive_count": int(np.sum(fv <= 0)),
                "one_step_relative_change_gt_10pct": int(np.sum(rel > 0.10)),
                "unchanged_step_fraction": float(np.mean(np.diff(fv) == 0)) if len(fv) > 1 else None,
            }
        )

    funding_name = "funding_rate" if "funding_rate" in arrays else ("predicted_funding_rate" if "predicted_funding_rate" in arrays else None)
    if funding_name:
        fv = arrays[funding_name]
        finite = np.isfinite(fv)
        x = fv[finite]
        fields[funding_name].update(
            {
                "actual_changes": int(np.sum(np.diff(x) != 0)) if len(x) > 1 else 0,
                "scheduled_or_stepwise": bool(len(x) > 1 and np.mean(np.diff(x) == 0) >= 0.50),
            }
        )

    premium_stats = None
    if "mark_price" in arrays and "index_price" in arrays:
        mark = arrays["mark_price"]
        index = arrays["index_price"]
        good = np.isfinite(mark) & np.isfinite(index) & (mark > 0) & (index > 0)
        premium = np.full(len(mark), np.nan)
        premium[good] = 10_000.0 * (mark[good] / index[good] - 1.0)
        pv = premium[np.isfinite(premium)]
        premium_stats = {
            **_numeric_stats(premium, ts),
            "finite_overlap_count": int(len(pv)),
            "median_abs_bps": float(np.median(np.abs(pv))) if len(pv) else None,
            "p95_abs_bps": float(np.quantile(np.abs(pv), 0.95)) if len(pv) else None,
            "sign_changes": int(np.sum(np.sign(pv[1:]) != np.sign(pv[:-1]))) if len(pv) > 1 else 0,
            "impossible_price_rows": int(np.sum(np.isfinite(mark) & (mark <= 0)) + np.sum(np.isfinite(index) & (index <= 0))),
            "decision_coverage_no_staleness_limit": decision_coverage(ts, day_decisions, np.isfinite(premium)),
        }

    gaps = gap_stats(ts)
    day_coverage = 0.0
    if len(ts):
        day_coverage = float(max(0, min(DAY_US, ts[-1] - ts[0])) / DAY_US)

    malformed_numeric = 0
    retained_numeric_total = 0
    for values in arrays.values():
        malformed_numeric += int(np.sum(~np.isfinite(values)))
        retained_numeric_total += len(values)
    malformed_fraction = float(malformed_numeric / retained_numeric_total) if retained_numeric_total else 1.0

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
        "retained_rows_after_timestamp_and_duplicate_resolution": len(ts),
        "malformed_timestamp_rows": malformed_timestamp_rows,
        "timestamp_regressions_raw_file_order": timestamp_regressions,
        "duplicate_availability_timestamps": duplicate_count,
        "first_availability_timestamp_us": int(ts[0]) if len(ts) else None,
        "last_availability_timestamp_us": int(ts[-1]) if len(ts) else None,
        "day_coverage_fraction": day_coverage,
        "update_gaps": gaps,
        "malformed_or_nonfinite_numeric_fraction": malformed_fraction,
        "fields": fields,
        "premium": premium_stats,
    }


def _git_ignored(workspace: Path, raw_root: Path) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", str(raw_root)], cwd=workspace, text=True
    )
    return result.returncode == 0


def readiness(audits: list[dict[str, Any]], *, raw_ignored: bool) -> dict[str, Any]:
    if len(audits) != 14:
        return {"status": "FAIL_DERIVATIVES_DATA_NOT_READY", "gates": {"all_14_files": False}}

    def field_present(row: dict[str, Any], name: str) -> bool:
        return row["schema"].get(name) in {"PRESENT_NATIVE", "DERIVABLE_CAUSALLY"}

    oi_native = all(field_present(row, "open_interest") for row in audits)
    premium_available = all(field_present(row, "premium") for row in audits)
    availability_defined = all(row["schema"]["availability_timestamp"] is not None for row in audits)
    malformed_ok = all(row["malformed_or_nonfinite_numeric_fraction"] <= 0.05 for row in audits)

    oi_symbol_cov: dict[str, float] = {}
    premium_symbol_cov: dict[str, float] = {}
    for symbol in SYMBOLS:
        selected = [row for row in audits if row["symbol"] == symbol]
        oi_cov = [row["fields"].get("open_interest", {}).get("decision_coverage_no_staleness_limit", {}).get("fraction", 0.0) for row in selected]
        oi_symbol_cov[symbol] = float(np.mean(oi_cov)) if oi_cov else 0.0
        p_cov = [row.get("premium", {}).get("decision_coverage_no_staleness_limit", {}).get("fraction", 0.0) if row.get("premium") else 0.0 for row in selected]
        premium_symbol_cov[symbol] = float(np.mean(p_cov)) if p_cov else 0.0

    gates = {
        "all_14_files": len(audits) == 14,
        "no_august_accessed": True,
        "causal_availability_timestamp_defined": availability_defined,
        "open_interest_schema_unambiguous": oi_native,
        "open_interest_coverage_each_symbol_at_least_95pct": all(v >= 0.95 for v in oi_symbol_cov.values()),
        "malformed_or_nonfinite_rows_at_most_5pct_each_day": malformed_ok,
        "timestamp_regressions_deterministically_resolved": True,
        "past_only_asof_supported": availability_defined,
        "raw_directory_gitignored": raw_ignored,
    }
    premium_gate = premium_available and all(v >= 0.95 for v in premium_symbol_cov.values())
    all_core = all(gates.values())
    if all_core and premium_gate:
        status = "DATA_READY_SANDBOX"
    elif all_core:
        status = "PARTIAL_DATA_READY"
    else:
        status = "FAIL_DERIVATIVES_DATA_NOT_READY"
    return {
        "status": status,
        "gates": gates,
        "premium_track_ready": premium_gate,
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
                "days": [d.isoformat() for d in DAYS],
                "decision_grid_seconds": 60,
                "coverage_threshold": 0.95,
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
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    partial.replace(output)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CODEX-EXP-005-P0 derivative-state data audit")
    parser.add_argument("--raw-root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.raw_root, args.workspace, args.output)
    print(json.dumps({"experiment_id": result["experiment_id"], "status": result["status"], "file_count": result["file_count"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

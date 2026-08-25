from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .codex_research import (
    assert_unsealed_day,
    assert_unsealed_path,
    canonical_sha256,
    sha256_file,
)
from .v23_phase0dl_score import DayData, _load_day

EXPERIMENT_ID = "CODEX-EXP-004-P0"
SYMBOLS = ("BTCUSDT", "ETHUSDT")
DAYS = tuple(date(2026, month, 1) for month in range(1, 8))
GRID_US = 250_000
ENTRY_STEPS = 1
DENSE_STEP_S = 60
SCHEDULES = ("dense_1m", "nonoverlap")
HORIZONS_S = (60, 180, 300, 600, 900, 1800, 3600)
COSTS_BPS = (8.0, 12.0)
HEADROOM_THRESHOLDS_BPS = (8.0, 12.0, 16.0, 24.0, 36.0, 40.0, 60.0, 80.0)
KEY_HEADROOM_BPS = 24.0
STRONG_HEADROOM_BPS = 36.0
PROVENANCE_RELPATH = "evidence/codex/CODEX_EXP001_INPUT_PROVENANCE_20260825.json"

MIN_POOLED_KEY_EVENTS = 100
MIN_POOLED_KEY_FRACTION = 0.01
MIN_SYMBOL_DAYS_WITH_KEY_EVENT = 12
MIN_MEDIAN_KEY_EVENTS_PER_SYMBOL_DAY = 3.0
MIN_KEY_EVENTS_PER_SYMBOL = 30
MAX_SYMBOL_DAY_KEY_EVENT_SHARE = 0.25
MIN_POOLED_STRONG_EVENTS = 40


@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbols: tuple[str, ...] = SYMBOLS
    days: tuple[str, ...] = tuple(day.isoformat() for day in DAYS)
    grid_us: int = GRID_US
    entry_steps: int = ENTRY_STEPS
    dense_step_s: int = DENSE_STEP_S
    schedules: tuple[str, ...] = SCHEDULES
    horizons_s: tuple[int, ...] = HORIZONS_S
    costs_bps: tuple[float, ...] = COSTS_BPS
    headroom_thresholds_bps: tuple[float, ...] = HEADROOM_THRESHOLDS_BPS
    key_headroom_bps: float = KEY_HEADROOM_BPS
    strong_headroom_bps: float = STRONG_HEADROOM_BPS
    provenance_relpath: str = PROVENANCE_RELPATH
    min_pooled_key_events: int = MIN_POOLED_KEY_EVENTS
    min_pooled_key_fraction: float = MIN_POOLED_KEY_FRACTION
    min_symbol_days_with_key_event: int = MIN_SYMBOL_DAYS_WITH_KEY_EVENT
    min_median_key_events_per_symbol_day: float = MIN_MEDIAN_KEY_EVENTS_PER_SYMBOL_DAY
    min_key_events_per_symbol: int = MIN_KEY_EVENTS_PER_SYMBOL
    max_symbol_day_key_event_share: float = MAX_SYMBOL_DAY_KEY_EVENT_SHARE
    min_pooled_strong_events: int = MIN_POOLED_STRONG_EVENTS


def _git(workspace: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=workspace, text=True, capture_output=True, check=True
    )
    return completed.stdout.strip()


def assert_frozen_workspace(workspace: Path, frozen_commit: str) -> None:
    if len(frozen_commit) != 40:
        raise RuntimeError("full 40-character frozen commit required")
    current = _git(workspace, "rev-parse", "HEAD")
    if current != frozen_commit:
        raise RuntimeError(f"frozen commit mismatch: expected {frozen_commit}, current {current}")
    if _git(workspace, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked worktree changes detected after freeze")


def feature_path(feature_dir: Path, symbol: str, day: date) -> Path:
    if symbol not in SYMBOLS:
        raise ValueError("symbol outside frozen audit")
    assert_unsealed_day(day, allowed=DAYS)
    path = feature_dir / symbol / f"{day.isoformat()}_FEATURES250.csv"
    assert_unsealed_path(path)
    return path


def scheduled_indices(day: DayData, *, horizon_s: int, schedule: str) -> np.ndarray:
    if horizon_s not in HORIZONS_S:
        raise ValueError("horizon outside frozen audit")
    if schedule not in SCHEDULES:
        raise ValueError("unknown schedule")
    step_s = DENSE_STEP_S if schedule == "dense_1m" else horizon_s
    step = int(step_s * 1_000_000 // GRID_US)
    return np.arange(0, len(day.ts), step, dtype=np.int64)


def executable_fixed_horizon(
    day: DayData,
    indices: np.ndarray,
    horizon_s: int,
) -> dict[str, np.ndarray]:
    if horizon_s not in HORIZONS_S:
        raise ValueError("horizon outside frozen audit")
    indices = np.asarray(indices, dtype=np.int64)
    horizon_steps = int(round(horizon_s * 1_000_000 / GRID_US))
    entry = indices + ENTRY_STEPS
    exit_ = entry + horizon_steps
    valid = (
        (indices >= 0)
        & (indices < len(day.ts))
        & (entry < len(day.ts))
        & (exit_ < len(day.ts))
    )
    safe_i = np.minimum(np.maximum(indices, 0), len(day.ts) - 1)
    safe_e = np.minimum(np.maximum(entry, 0), len(day.ts) - 1)
    safe_x = np.minimum(np.maximum(exit_, 0), len(day.ts) - 1)
    valid &= day.book_valid[safe_i] & day.book_valid[safe_e] & day.book_valid[safe_x]
    valid &= (
        np.isfinite(day.bid[safe_e])
        & np.isfinite(day.ask[safe_e])
        & np.isfinite(day.bid[safe_x])
        & np.isfinite(day.ask[safe_x])
        & (day.bid[safe_e] > 0)
        & (day.ask[safe_e] > 0)
        & (day.bid[safe_x] > 0)
        & (day.ask[safe_x] > 0)
    )
    long_gross = np.full(len(indices), np.nan, dtype=np.float64)
    short_gross = np.full(len(indices), np.nan, dtype=np.float64)
    loc = np.flatnonzero(valid)
    e = entry[loc]
    x = exit_[loc]
    long_gross[loc] = 10_000.0 * np.log(day.bid[x] / day.ask[e])
    short_gross[loc] = 10_000.0 * np.log(day.bid[e] / day.ask[x])
    oracle = np.fmax(long_gross, short_gross)
    return {
        "decision_index": indices,
        "entry_index": entry,
        "exit_index": exit_,
        "valid": valid,
        "long_gross_bps": long_gross,
        "short_gross_bps": short_gross,
        "oracle_gross_bps": oracle,
    }


def _distribution(values: np.ndarray) -> dict[str, float | int | None]:
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if not len(values):
        return {
            "count": 0,
            "mean": None,
            "q50": None,
            "q75": None,
            "q90": None,
            "q95": None,
            "q99": None,
        }
    q = np.quantile(values, [0.50, 0.75, 0.90, 0.95, 0.99])
    return {
        "count": int(len(values)),
        "mean": float(np.mean(values)),
        "q50": float(q[0]),
        "q75": float(q[1]),
        "q90": float(q[2]),
        "q95": float(q[3]),
        "q99": float(q[4]),
    }


def summarize_outcomes(outcomes: dict[str, np.ndarray]) -> dict[str, Any]:
    valid = outcomes["valid"]
    long_gross = outcomes["long_gross_bps"][valid]
    short_gross = outcomes["short_gross_bps"][valid]
    oracle = outcomes["oracle_gross_bps"][valid]
    threshold = {
        str(int(value)): {
            "count": int(np.sum(oracle >= value)),
            "fraction": float(np.mean(oracle >= value)) if len(oracle) else 0.0,
        }
        for value in HEADROOM_THRESHOLDS_BPS
    }
    costs = {}
    for cost in COSTS_BPS:
        net = oracle - cost
        costs[str(int(cost))] = {
            "distribution": _distribution(net),
            "positive_count": int(np.sum(net > 0)),
            "positive_fraction": float(np.mean(net > 0)) if len(net) else 0.0,
        }
    wins_long = long_gross > short_gross
    wins_short = short_gross > long_gross
    ties = ~(wins_long | wins_short)
    return {
        "valid_decisions": int(np.sum(valid)),
        "long_gross_bps": _distribution(long_gross),
        "short_gross_bps": _distribution(short_gross),
        "oracle_gross_bps": _distribution(oracle),
        "headroom": threshold,
        "oracle_net_after_cost": costs,
        "oracle_direction_fraction": {
            "long": float(np.mean(wins_long)) if len(oracle) else 0.0,
            "short": float(np.mean(wins_short)) if len(oracle) else 0.0,
            "tie": float(np.mean(ties)) if len(oracle) else 0.0,
        },
    }


def _eligibility(rows: list[dict[str, Any]], horizon_s: int) -> dict[str, Any]:
    key = str(int(KEY_HEADROOM_BPS))
    strong = str(int(STRONG_HEADROOM_BPS))
    selected = [
        row
        for row in rows
        if row["schedule"] == "nonoverlap" and row["horizon_s"] == horizon_s
    ]
    if len(selected) != len(SYMBOLS) * len(DAYS):
        raise RuntimeError("incomplete symbol-day matrix")
    key_counts = np.asarray(
        [row["summary"]["headroom"][key]["count"] for row in selected],
        dtype=np.int64,
    )
    strong_counts = np.asarray(
        [row["summary"]["headroom"][strong]["count"] for row in selected],
        dtype=np.int64,
    )
    valid_counts = np.asarray(
        [row["summary"]["valid_decisions"] for row in selected],
        dtype=np.int64,
    )
    total_key = int(key_counts.sum())
    total_valid = int(valid_counts.sum())
    by_symbol = {
        symbol: int(
            sum(
                row["summary"]["headroom"][key]["count"]
                for row in selected
                if row["symbol"] == symbol
            )
        )
        for symbol in SYMBOLS
    }
    maximum_share = float(key_counts.max() / total_key) if total_key > 0 else 1.0
    pooled_fraction = float(total_key / total_valid) if total_valid else 0.0
    gates = {
        "pooled_24bp_events_at_least_100": total_key >= MIN_POOLED_KEY_EVENTS,
        "pooled_24bp_fraction_at_least_1pct": pooled_fraction >= MIN_POOLED_KEY_FRACTION,
        "at_least_12_of_14_symbol_days_with_event": int(np.sum(key_counts > 0)) >= MIN_SYMBOL_DAYS_WITH_KEY_EVENT,
        "median_24bp_events_per_symbol_day_at_least_3": float(np.median(key_counts)) >= MIN_MEDIAN_KEY_EVENTS_PER_SYMBOL_DAY,
        "btc_24bp_events_at_least_30": by_symbol["BTCUSDT"] >= MIN_KEY_EVENTS_PER_SYMBOL,
        "eth_24bp_events_at_least_30": by_symbol["ETHUSDT"] >= MIN_KEY_EVENTS_PER_SYMBOL,
        "max_symbol_day_share_at_most_25pct": maximum_share <= MAX_SYMBOL_DAY_KEY_EVENT_SHARE,
        "pooled_36bp_events_at_least_40": int(strong_counts.sum()) >= MIN_POOLED_STRONG_EVENTS,
    }
    return {
        "horizon_s": horizon_s,
        "pooled_valid_decisions": total_valid,
        "pooled_24bp_events": total_key,
        "pooled_24bp_fraction": pooled_fraction,
        "symbol_days_with_24bp_event": int(np.sum(key_counts > 0)),
        "median_24bp_events_per_symbol_day": float(np.median(key_counts)),
        "by_symbol_24bp_events": by_symbol,
        "maximum_symbol_day_24bp_share": maximum_share,
        "pooled_36bp_events": int(strong_counts.sum()),
        "gates": gates,
        "eligible": all(gates.values()),
    }


def evaluate_model_worthiness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    horizons = [_eligibility(rows, horizon_s) for horizon_s in HORIZONS_S]
    eligible = [row["horizon_s"] for row in horizons if row["eligible"]]
    return {
        "horizons": horizons,
        "eligible_horizons_s": eligible,
        "selected_shortest_eligible_horizon_s": min(eligible) if eligible else None,
        "status": "MODEL_WORTHY_SANDBOX" if eligible else "STOP_NO_MODEL_WORTHY_HORIZON",
    }


def load_frozen_provenance(workspace: Path) -> dict[tuple[str, str], dict[str, Any]]:
    path = workspace / PROVENANCE_RELPATH
    assert_unsealed_path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise RuntimeError("frozen feature provenance is not PASS")
    if payload.get("sealed_paths_opened") is not False:
        raise RuntimeError("frozen feature provenance does not assert sealed paths closed")
    if payload.get("files_verified") != len(SYMBOLS) * len(DAYS):
        raise RuntimeError("frozen feature provenance does not contain 14 verified files")
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for record in payload.get("files", []):
        key = (str(record.get("symbol")), str(record.get("day")))
        if key in records:
            raise RuntimeError(f"duplicate frozen provenance record: {key}")
        records[key] = record
    expected_keys = {(symbol, day.isoformat()) for symbol in SYMBOLS for day in DAYS}
    if set(records) != expected_keys:
        raise RuntimeError("frozen feature provenance symbol/day matrix mismatch")
    return records


def input_manifest(feature_dir: Path, workspace: Path) -> list[dict[str, Any]]:
    provenance = load_frozen_provenance(workspace)
    records = []
    for symbol in SYMBOLS:
        for day in DAYS:
            path = feature_path(feature_dir, symbol, day)
            if not path.exists():
                raise FileNotFoundError(path)
            actual_bytes = path.stat().st_size
            actual_sha = sha256_file(path)
            frozen = provenance[(symbol, day.isoformat())]
            if actual_bytes != int(frozen["bytes"]):
                raise RuntimeError(f"feature byte-size mismatch for {symbol} {day}")
            if actual_sha != str(frozen["sha256"]):
                raise RuntimeError(f"feature SHA-256 mismatch for {symbol} {day}")
            records.append(
                {
                    "symbol": symbol,
                    "day": day.isoformat(),
                    "path": str(path),
                    "bytes": actual_bytes,
                    "sha256": actual_sha,
                    "frozen_provenance_match": True,
                }
            )
    return records


def assert_fresh_output(output: Path) -> Path:
    assert_unsealed_path(output)
    partial = output.with_name(output.name + ".part")
    assert_unsealed_path(partial)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing result: {output}")
    if partial.exists():
        raise FileExistsError(f"interrupted result marker already exists: {partial}")
    return partial


def run(feature_dir: Path, output: Path, workspace: Path, frozen_commit: str) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)
    partial_output = assert_fresh_output(output)
    manifest = input_manifest(feature_dir, workspace)
    rows: list[dict[str, Any]] = []
    for symbol in SYMBOLS:
        for day in DAYS:
            loaded = _load_day(feature_path(feature_dir, symbol, day), day)
            for horizon_s in HORIZONS_S:
                for schedule in SCHEDULES:
                    indices = scheduled_indices(
                        loaded, horizon_s=horizon_s, schedule=schedule
                    )
                    outcomes = executable_fixed_horizon(loaded, indices, horizon_s)
                    rows.append(
                        {
                            "symbol": symbol,
                            "day": day.isoformat(),
                            "horizon_s": horizon_s,
                            "schedule": schedule,
                            "summary": summarize_outcomes(outcomes),
                        }
                    )
    worthiness = evaluate_model_worthiness(rows)
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": worthiness["status"],
        "sandbox_descriptive_only": True,
        "profitability_claim_permitted": False,
        "predictability_claim_permitted": False,
        "frozen_commit": frozen_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": asdict(Config()),
        "configuration_sha256": canonical_sha256(Config()),
        "input_manifest": manifest,
        "symbol_day_results": rows,
        "model_worthiness": worthiness,
        "interpretation": (
            "Oracle headroom is future-aware descriptive upper-bound evidence only. "
            "Eligibility authorizes a separately preregistered predictive experiment; "
            "it is not a strategy PASS."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    partial_output.write_text(encoded, encoding="utf-8")
    partial_output.replace(output)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Model-free CODEX-EXP-004-P0 economic headroom audit"
    )
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args(argv)
    result = run(args.feature_dir, args.output, args.workspace, args.frozen_commit)
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "status": result["status"],
                "selected_shortest_eligible_horizon_s": result[
                    "model_worthiness"
                ]["selected_shortest_eligible_horizon_s"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

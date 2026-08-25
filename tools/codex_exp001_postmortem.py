from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

from multimarket.codex_exp001 import (
    COSTS_BPS,
    HORIZONS_S,
    MIN_INNER_TRADES,
    PROBABILITY_THRESHOLDS,
    REGULARIZATION_C,
    _fit_pair,
    calibration_metrics,
    score_probabilistic_actions,
)
from multimarket.codex_research import SANDBOX_DAYS, assert_unsealed_day, assert_unsealed_path
from multimarket.v23_phase0dl_score import _load_day


SYMBOLS = ("BTCUSDT", "ETHUSDT")
BLOCKS = ("L0", "L2")


def _finite_or_none(value: float) -> float | None:
    return float(value) if math.isfinite(float(value)) else None


def _discrimination(labels: np.ndarray, probability: np.ndarray) -> dict[str, float | None]:
    unique = np.unique(labels)
    if len(unique) != 2:
        return {"roc_auc": None, "average_precision": None}
    return {
        "roc_auc": float(roc_auc_score(labels, probability)),
        "average_precision": float(average_precision_score(labels, probability)),
    }


def _compact_score(score: dict[str, Any], selection_rows: int) -> dict[str, Any]:
    costs: dict[str, Any] = {}
    for cost in COSTS_BPS:
        raw = score["costs"][str(int(cost))]
        costs[str(int(cost))] = {
            key: _finite_or_none(value) if isinstance(value, float) else value
            for key, value in raw.items()
            if key != "net_values_bps"
        }
    trades = int(costs["8"]["trades"])
    return {
        "probability_threshold": float(score["probability_threshold"]),
        "candidate_rows": int(score["candidate_rows"]),
        "candidate_row_coverage": float(score["candidate_rows"] / selection_rows) if selection_rows else 0.0,
        "trades": trades,
        "directions": score["directions"],
        "costs": costs,
    }


def _gate_components(score: dict[str, Any]) -> dict[str, bool]:
    primary = score["costs"]["8"]
    stress = score["costs"]["12"]
    profit_factor = primary["profit_factor"]
    profit_factor_pass = (
        float(profit_factor) > 1.0
        if profit_factor is not None
        else float(primary["total_net_bps"]) > 0.0
    )
    components = {
        "minimum_20_trades": int(primary["trades"]) >= MIN_INNER_TRADES,
        "positive_expectancy_8": float(primary["net_bps_trade"]) > 0.0,
        "positive_total_8": float(primary["total_net_bps"]) > 0.0,
        "profit_factor_above_1_at_8": profit_factor_pass,
        "positive_expectancy_12": float(stress["net_bps_trade"]) > 0.0,
        "positive_total_12": float(stress["total_net_bps"]) > 0.0,
    }
    components["survives"] = all(components.values())
    return components


def _candidate_rank(record: dict[str, Any], cost: str) -> tuple[float, int, float]:
    metrics = record["score"]["costs"][cost]
    expectancy = metrics["net_bps_trade"]
    return (
        float(expectancy) if expectancy is not None else float("-inf"),
        int(metrics["trades"]),
        float(metrics["total_net_bps"]) if metrics["total_net_bps"] is not None else float("-inf"),
    )


def diagnose_symbol(feature_dir: Path, symbol: str) -> dict[str, Any]:
    days = []
    for day in SANDBOX_DAYS:
        assert_unsealed_day(day, allowed=SANDBOX_DAYS)
        path = feature_dir / symbol / f"{day.isoformat()}_FEATURES250.csv"
        assert_unsealed_path(path)
        days.append(_load_day(path, day))
    folds: list[dict[str, Any]] = []
    all_candidates: list[dict[str, Any]] = []
    failure_counts: Counter[str] = Counter()
    for eval_index in range(2, 7):
        train_days = days[: eval_index - 1]
        inner_day = days[eval_index - 1]
        fold: dict[str, Any] = {
            "fold": eval_index - 1,
            "base_training_days": [item.day.isoformat() for item in train_days],
            "inner_calibration_selection_day": inner_day.day.isoformat(),
            "outer_day_not_scored": days[eval_index].day.isoformat(),
            "blocks": {},
        }
        for block in BLOCKS:
            block_candidates: list[dict[str, Any]] = []
            models: list[dict[str, Any]] = []
            for horizon_s in HORIZONS_S:
                for c_value in REGULARIZATION_C:
                    pair, outcomes, calibration_idx, selection_idx = _fit_pair(
                        train_days, inner_day, block, horizon_s, c_value
                    )
                    X_selection = inner_day.X[block][selection_idx]
                    p_long, u_long = pair.long.forecast(X_selection)
                    p_short, u_short = pair.short.forecast(X_selection)
                    y_long = outcomes.long_positive[selection_idx].astype(np.int8)
                    y_short = outcomes.short_positive[selection_idx].astype(np.int8)
                    long_calibration = calibration_metrics(y_long, p_long)
                    short_calibration = calibration_metrics(y_short, p_short)
                    long_calibration.update(_discrimination(y_long, p_long))
                    short_calibration.update(_discrimination(y_short, p_short))
                    model_record = {
                        "horizon_s": horizon_s,
                        "c_value": c_value,
                        "calibration_rows": int(len(calibration_idx)),
                        "selection_rows": int(len(selection_idx)),
                        "long": {
                            "metrics_on_inner_selection": long_calibration,
                            "positive_mean_net_bps_from_calibration": pair.long.positive_mean_net_bps,
                            "nonpositive_mean_net_bps_from_calibration": pair.long.nonpositive_mean_net_bps,
                            "positive_utility_rows": int(np.sum(u_long > 0.0)),
                        },
                        "short": {
                            "metrics_on_inner_selection": short_calibration,
                            "positive_mean_net_bps_from_calibration": pair.short.positive_mean_net_bps,
                            "nonpositive_mean_net_bps_from_calibration": pair.short.nonpositive_mean_net_bps,
                            "positive_utility_rows": int(np.sum(u_short > 0.0)),
                        },
                    }
                    models.append(model_record)
                    for threshold in PROBABILITY_THRESHOLDS:
                        score = score_probabilistic_actions(
                            inner_day,
                            outcomes,
                            selection_idx,
                            p_long,
                            p_short,
                            u_long,
                            u_short,
                            probability_threshold=threshold,
                            horizon_s=horizon_s,
                        )
                        compact = _compact_score(score, len(selection_idx))
                        gates = _gate_components(compact)
                        for gate, passed in gates.items():
                            if gate != "survives" and not passed:
                                failure_counts[gate] += 1
                        record = {
                            "symbol": symbol,
                            "fold": eval_index - 1,
                            "block": block,
                            "horizon_s": horizon_s,
                            "c_value": c_value,
                            "probability_threshold": threshold,
                            "score": compact,
                            "gates": gates,
                        }
                        block_candidates.append(record)
                        all_candidates.append(record)
            fold["blocks"][block] = {
                "models": models,
                "candidates_tested": len(block_candidates),
                "survivors": sum(item["gates"]["survives"] for item in block_candidates),
                "best_posthoc_by_net_8": max(block_candidates, key=lambda item: _candidate_rank(item, "8")),
                "best_posthoc_by_net_12": max(block_candidates, key=lambda item: _candidate_rank(item, "12")),
                "highest_trade_count": max(block_candidates, key=lambda item: item["score"]["trades"]),
            }
        folds.append(fold)
        print(symbol, inner_day.day.isoformat(), "diagnosed", flush=True)
    return {
        "symbol": symbol,
        "folds": folds,
        "candidates_tested": len(all_candidates),
        "survivors": sum(item["gates"]["survives"] for item in all_candidates),
        "candidate_gate_failure_counts": dict(sorted(failure_counts.items())),
        "best_posthoc_by_net_8": max(all_candidates, key=lambda item: _candidate_rank(item, "8")),
        "best_posthoc_by_net_12": max(all_candidates, key=lambda item: _candidate_rank(item, "12")),
        "highest_trade_count": max(all_candidates, key=lambda item: item["score"]["trades"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Non-promotional inner-sandbox postmortem for frozen CODEX-EXP-001")
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    for value in (args.feature_dir, args.output):
        assert_unsealed_path(value)
    payload = {
        "diagnostic_id": "CODEX-DIAG-001",
        "parent_experiment": "CODEX-EXP-001",
        "status": "HYPOTHESIS_GENERATING_ONLY",
        "frozen_result_unchanged": True,
        "outer_days_scored": False,
        "sealed_periods_analytically_opened": False,
        "feature_dir": str(args.feature_dir.resolve()),
        "symbols": [diagnose_symbol(args.feature_dir, symbol) for symbol in SYMBOLS],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(f"CODEX_DIAG_001=COMPLETE output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

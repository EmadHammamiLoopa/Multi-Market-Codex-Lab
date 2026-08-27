from __future__ import annotations

import argparse
import json
import math
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression

from .codex_exp004_headroom import DAYS, load_frozen_provenance
from .codex_exp004_p1 import (
    FixedLogistic,
    R_FEATURE_NAMES,
    build_day_dataset,
    score,
)
from .codex_research import canonical_sha256, sha256_file
from .v23_phase0dl_score import _load_day


EXPERIMENT_ID = "CODEX-EXP-021-P0"
READY_STATUS = "CALIBRATION_DESIGN_READY_SANDBOX"
NO_READY_STATUS = "NO_CALIBRATION_DESIGN_READY_SANDBOX"
INVALID_STATUS = "INVALID"

SYMBOL = "BTCUSDT"
VOL_FEATURE = "rv_30m_bps"
VOL_INDEX = R_FEATURE_NAMES.index(VOL_FEATURE)

OUTER_DAYS = tuple(date(2026, m, 1) for m in range(4, 8))
OOF_DAYS = tuple(date(2026, m, 1) for m in range(3, 7))
SEED = 20260827
CLIP_EPS = 1e-6

EXP020_RESULT = Path(
    "evidence/codex/exp020_p0_volatility_diagnostic/"
    "VOLATILITY_FALSIFICATION_CALIBRATION.json"
)
EXP020_RESULT_SHA256 = (
    "cbbe2bd8a148b556cb0670b7a5adb4f49aef677e85ef77b8c4bea01a53e69249"
)
EXP019_RESULT = Path(
    "evidence/codex/exp019_p1_corrected_volatility_aug1/"
    "INDEPENDENT_VOLATILITY_AUG1_CORRECTED.json"
)
EXP019_RESULT_SHA256 = (
    "a6d55db8e938a0c9b80f3e39117c07fd85e0316d408b159f6bd421ffa7920def"
)


@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbol: str = SYMBOL
    days: tuple[str, ...] = tuple(d.isoformat() for d in DAYS)
    outer_days: tuple[str, ...] = tuple(d.isoformat() for d in OUTER_DAYS)
    oof_days: tuple[str, ...] = tuple(d.isoformat() for d in OOF_DAYS)
    feature: str = VOL_FEATURE
    clip_eps: float = CLIP_EPS
    platt_c: float = 1e6
    platt_solver: str = "lbfgs"
    platt_class_weight: str | None = None
    platt_max_iter: int = 1000
    platt_random_state: int = SEED
    min_improved_folds: int = 3
    auc_tolerance: float = 1e-12
    exp020_result_sha256: str = EXP020_RESULT_SHA256
    exp019_result_sha256: str = EXP019_RESULT_SHA256


def _git(workspace: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", *args],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=True,
    )
    return p.stdout.strip()


def assert_frozen_workspace(workspace: Path, frozen_commit: str) -> None:
    if len(frozen_commit) != 40:
        raise RuntimeError("full frozen commit required")
    if _git(workspace, "rev-parse", "HEAD") != frozen_commit:
        raise RuntimeError("frozen commit mismatch")
    if _git(workspace, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked worktree changes after freeze")


def verify_parent_artifacts(workspace: Path) -> dict[str, Any]:
    p20 = workspace / EXP020_RESULT
    p19 = workspace / EXP019_RESULT
    if sha256_file(p20) != EXP020_RESULT_SHA256:
        raise RuntimeError("EXP020 result SHA mismatch")
    if sha256_file(p19) != EXP019_RESULT_SHA256:
        raise RuntimeError("EXP019 result SHA mismatch")

    a20 = json.loads(p20.read_text(encoding="utf-8"))
    a19 = json.loads(p19.read_text(encoding="utf-8"))

    if a20.get("status") != (
        "DIAGNOSTIC_COMPLETE_VOLATILITY_FALSIFICATION_AND_CALIBRATION"
    ):
        raise RuntimeError("EXP020 status mismatch")
    if a19.get("status") != (
        "FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED"
    ):
        raise RuntimeError("EXP019 status mismatch")
    if a20.get("aug_feature_reparsed") is not False:
        raise RuntimeError("EXP020 Aug reparse guard mismatch")
    if a20.get("older_august_holdout_opened") is not False:
        raise RuntimeError("EXP020 older August guard mismatch")
    if a20.get("direction_scored") is not False:
        raise RuntimeError("EXP020 direction guard mismatch")
    if a20.get("pnl_scored") is not False:
        raise RuntimeError("EXP020 PnL guard mismatch")
    return {"EXP020": a20, "EXP019": a19}


def verify_training_inputs(
    feature_dir: Path,
    workspace: Path,
) -> list[dict[str, Any]]:
    provenance = load_frozen_provenance(workspace)
    rows: list[dict[str, Any]] = []
    for d in DAYS:
        path = feature_dir / SYMBOL / f"{d.isoformat()}_FEATURES250.csv"
        if not path.is_file():
            raise FileNotFoundError(path)
        frozen = provenance[(SYMBOL, d.isoformat())]
        size = int(path.stat().st_size)
        digest = sha256_file(path)
        if size != int(frozen["bytes"]):
            raise RuntimeError(f"training feature size mismatch: {d}")
        if digest != str(frozen["sha256"]):
            raise RuntimeError(f"training feature SHA mismatch: {d}")
        rows.append(
            {
                "day": d.isoformat(),
                "bytes": size,
                "sha256": digest,
                "frozen_provenance_match": True,
            }
        )
    return rows


def load_days(feature_dir: Path) -> dict[date, Any]:
    out: dict[date, Any] = {}
    for d in DAYS:
        phase = _load_day(
            feature_dir / SYMBOL / f"{d.isoformat()}_FEATURES250.csv",
            d,
        )
        out[d] = build_day_dataset(SYMBOL, phase)
    return out


def _vol_xy(day: Any) -> tuple[np.ndarray, np.ndarray]:
    m = day.valid_R
    return day.X_R[m][:, [VOL_INDEX]], day.y[m]


def _concat_days(days: list[Any]) -> tuple[np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    for d in days:
        x, y = _vol_xy(d)
        xs.append(x)
        ys.append(y)
    return np.concatenate(xs), np.concatenate(ys)


def _clip_prob(p: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(p, dtype=float), CLIP_EPS, 1 - CLIP_EPS)


def _logit(p: np.ndarray) -> np.ndarray:
    p = _clip_prob(p)
    return np.log(p / (1 - p))


def _sigmoid(z: np.ndarray | float) -> np.ndarray:
    z = np.asarray(z, dtype=float)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def fit_intercept_delta(
    p_hist: np.ndarray,
    y_hist: np.ndarray,
) -> float:
    z = _logit(p_hist)
    target = float(np.mean(y_hist))
    if not (0 < target < 1):
        raise RuntimeError("historical OOF prevalence must be in (0,1)")

    lo, hi = -30.0, 30.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        mean_p = float(np.mean(_sigmoid(z + mid)))
        if mean_p < target:
            lo = mid
        else:
            hi = mid
    return float((lo + hi) / 2.0)


def apply_intercept(p: np.ndarray, delta: float) -> np.ndarray:
    return _sigmoid(_logit(p) + delta)


def fit_platt(
    p_hist: np.ndarray,
    y_hist: np.ndarray,
) -> tuple[LogisticRegression, float, float]:
    z = _logit(p_hist).reshape(-1, 1)
    y = np.asarray(y_hist, dtype=np.int8)
    if np.unique(y).size != 2:
        raise RuntimeError("Platt history lacks both classes")
    m = LogisticRegression(
        C=1e6,
        solver="lbfgs",
        class_weight=None,
        max_iter=1000,
        random_state=SEED,
    )
    m.fit(z, y)
    return m, float(m.intercept_[0]), float(m.coef_[0, 0])


def apply_platt(m: LogisticRegression, p: np.ndarray) -> np.ndarray:
    return m.predict_proba(_logit(p).reshape(-1, 1))[:, 1]


def build_oof_record(
    data: dict[date, Any],
    target_day: date,
) -> dict[str, Any]:
    train_days = [d for d in DAYS if d < target_day]
    train = [data[d] for d in train_days]
    Xtr, ytr = _concat_days(train)
    model = FixedLogistic().fit(Xtr, ytr)

    Xo, yo = _vol_xy(data[target_day])
    p = model.predict_proba(Xo)

    return {
        "day": target_day.isoformat(),
        "train_days": [d.isoformat() for d in train_days],
        "n": int(len(yo)),
        "positive_n": int(np.sum(yo)),
        "prevalence": float(np.mean(yo)),
        "labels": yo,
        "raw_prob": p,
    }


def _metric_with_mean(y: np.ndarray, p: np.ndarray) -> dict[str, Any]:
    m = score(y, p)
    m["mean_probability"] = float(np.mean(p))
    return m


def run_audit(
    data: dict[date, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    oof_cache: dict[date, dict[str, Any]] = {}
    for d in tuple(date(2026, m, 1) for m in range(3, 8)):
        oof_cache[d] = build_oof_record(data, d)

    folds: list[dict[str, Any]] = []
    all_labels: list[np.ndarray] = []
    track_probs: dict[str, list[np.ndarray]] = {
        "RAW": [],
        "ROLLING_OOF_INTERCEPT": [],
        "ROLLING_OOF_PLATT": [],
    }
    fold_baseline_sse = 0.0

    for outer in OUTER_DAYS:
        current = oof_cache[outer]
        y = current["labels"]
        raw = current["raw_prob"]

        hist_days = [
            d for d in OOF_DAYS
            if d < outer
        ]
        hist_rows = [oof_cache[d] for d in hist_days]
        p_hist = np.concatenate([r["raw_prob"] for r in hist_rows])
        y_hist = np.concatenate([r["labels"] for r in hist_rows])

        delta = fit_intercept_delta(p_hist, y_hist)
        p_int = apply_intercept(raw, delta)

        platt, platt_intercept, platt_slope = fit_platt(p_hist, y_hist)
        p_platt = apply_platt(platt, raw)

        metrics = {
            "RAW": _metric_with_mean(y, raw),
            "ROLLING_OOF_INTERCEPT": _metric_with_mean(y, p_int),
            "ROLLING_OOF_PLATT": _metric_with_mean(y, p_platt),
        }

        fold_baseline_sse += float(
            np.sum((y - float(np.mean(y))) ** 2)
        )
        all_labels.append(y)
        track_probs["RAW"].append(raw)
        track_probs["ROLLING_OOF_INTERCEPT"].append(p_int)
        track_probs["ROLLING_OOF_PLATT"].append(p_platt)

        folds.append(
            {
                "outer_day": outer.isoformat(),
                "base_model_train_days": current["train_days"],
                "calibration_history_days": [
                    d.isoformat() for d in hist_days
                ],
                "calibration_history_n": int(len(y_hist)),
                "calibration_history_positive_n": int(np.sum(y_hist)),
                "calibration_history_prevalence": float(np.mean(y_hist)),
                "intercept_delta": delta,
                "platt_intercept": platt_intercept,
                "platt_slope": platt_slope,
                "metrics": metrics,
            }
        )

    Y = np.concatenate(all_labels)
    aggregates: dict[str, Any] = {}
    raw_fold = [f["metrics"]["RAW"] for f in folds]

    for track, parts in track_probs.items():
        P = np.concatenate(parts)
        total_sse = float(np.sum((Y - P) ** 2))
        agg_brier = float(total_sse / len(Y))
        agg_logloss = float(
            -np.mean(
                Y * np.log(np.clip(P, 1e-12, 1 - 1e-12))
                + (1 - Y) * np.log(np.clip(1 - P, 1e-12, 1 - 1e-12))
            )
        )
        fold_skill = (
            1.0 - total_sse / fold_baseline_sse
            if fold_baseline_sse > 0
            else None
        )
        aggregates[track] = {
            "n": int(len(Y)),
            "aggregate_brier_score": agg_brier,
            "aggregate_log_loss": agg_logloss,
            "aggregate_fold_normalized_brier_skill": (
                float(fold_skill) if fold_skill is not None else None
            ),
        }

    for track in ("ROLLING_OOF_INTERCEPT", "ROLLING_OOF_PLATT"):
        aggregates[track]["folds_brier_improved_vs_raw"] = int(
            sum(
                f["metrics"][track]["brier_score"]
                < f["metrics"]["RAW"]["brier_score"]
                for f in folds
            )
        )
        aggregates[track]["folds_logloss_improved_vs_raw"] = int(
            sum(
                f["metrics"][track]["log_loss"]
                < f["metrics"]["RAW"]["log_loss"]
                for f in folds
            )
        )
        aggregates[track]["folds_auc_preserved"] = int(
            sum(
                abs(
                    f["metrics"][track]["roc_auc"]
                    - f["metrics"]["RAW"]["roc_auc"]
                )
                <= 1e-12
                for f in folds
            )
        )

    return folds, {
        "tracks": aggregates,
        "fold_baseline_sse": float(fold_baseline_sse),
    }


def readiness(
    folds: list[dict[str, Any]],
    aggregate: dict[str, Any],
) -> tuple[dict[str, Any], str | None, str]:
    raw = aggregate["tracks"]["RAW"]
    out: dict[str, Any] = {}

    for track in ("ROLLING_OOF_INTERCEPT", "ROLLING_OOF_PLATT"):
        a = aggregate["tracks"][track]
        checks = {
            "aggregate_brier_improves_vs_raw": (
                a["aggregate_brier_score"]
                < raw["aggregate_brier_score"]
            ),
            "aggregate_logloss_improves_vs_raw": (
                a["aggregate_log_loss"]
                < raw["aggregate_log_loss"]
            ),
            "aggregate_fold_normalized_brier_skill_positive": (
                a["aggregate_fold_normalized_brier_skill"] is not None
                and a["aggregate_fold_normalized_brier_skill"] > 0
            ),
            "brier_improves_in_at_least_3_of_4_folds": (
                a["folds_brier_improved_vs_raw"] >= 3
            ),
            "logloss_improves_in_at_least_3_of_4_folds": (
                a["folds_logloss_improved_vs_raw"] >= 3
            ),
            "auc_preserved_all_4_folds": (
                a["folds_auc_preserved"] == 4
            ),
        }
        if track == "ROLLING_OOF_PLATT":
            checks["platt_slope_positive_all_4_folds"] = all(
                f["platt_slope"] > 0 for f in folds
            )
        out[track] = {
            "checks": checks,
            "ready": all(checks.values()),
        }

    ready = [k for k, v in out.items() if v["ready"]]
    selected: str | None = None

    if len(ready) == 1:
        selected = ready[0]
    elif len(ready) == 2:
        a, b = ready
        aa = aggregate["tracks"][a]
        bb = aggregate["tracks"][b]
        if aa["aggregate_brier_score"] < bb["aggregate_brier_score"]:
            selected = a
        elif bb["aggregate_brier_score"] < aa["aggregate_brier_score"]:
            selected = b
        elif aa["aggregate_log_loss"] < bb["aggregate_log_loss"]:
            selected = a
        elif bb["aggregate_log_loss"] < aa["aggregate_log_loss"]:
            selected = b
        else:
            selected = "ROLLING_OOF_INTERCEPT"

    status = READY_STATUS if selected is not None else NO_READY_STATUS
    return out, selected, status


def run(
    feature_dir: Path,
    output: Path,
    workspace: Path,
    frozen_commit: str,
) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)
    if output.exists() or output.with_name(output.name + ".part").exists():
        raise RuntimeError("EXP021 output already exists")

    parents = verify_parent_artifacts(workspace)
    manifest = verify_training_inputs(feature_dir, workspace)
    data = load_days(feature_dir)

    folds, aggregate = run_audit(data)
    candidate_readiness, selected, status = readiness(folds, aggregate)

    invariants = {
        "exp020_result_sha_exact": (
            sha256_file(workspace / EXP020_RESULT) == EXP020_RESULT_SHA256
        ),
        "exp020_status_exact": (
            parents["EXP020"]["status"]
            == "DIAGNOSTIC_COMPLETE_VOLATILITY_FALSIFICATION_AND_CALIBRATION"
        ),
        "exp019_status_remains_frozen_fail": (
            parents["EXP019"]["status"]
            == "FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED"
        ),
        "outer_days_exact_apr_jul": (
            OUTER_DAYS == tuple(date(2026, m, 1) for m in range(4, 8))
        ),
        "oof_days_begin_mar": OOF_DAYS[0] == date(2026, 3, 1),
        "all_outer_base_training_strictly_earlier": all(
            all(date.fromisoformat(d) < date.fromisoformat(f["outer_day"])
                for d in f["base_model_train_days"])
            for f in folds
        ),
        "all_calibration_history_strictly_earlier": all(
            all(date.fromisoformat(d) < date.fromisoformat(f["outer_day"])
                for d in f["calibration_history_days"])
            for f in folds
        ),
        "aug_feature_reparsed": False,
        "older_august_holdout_opened": False,
        "direction_scored": False,
        "pnl_scored": False,
        "network_accessed": False,
        "exp019_re_adjudicated": False,
    }

    expected_false = {
        "aug_feature_reparsed",
        "older_august_holdout_opened",
        "direction_scored",
        "pnl_scored",
        "network_accessed",
        "exp019_re_adjudicated",
    }
    if not all(
        (v is False if k in expected_false else v is True)
        for k, v in invariants.items()
    ):
        raise RuntimeError("EXP021 invariant failure")

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "selected_calibration_design": selected,
        "frozen_commit": frozen_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": asdict(Config()),
        "configuration_sha256": canonical_sha256(Config()),
        "exp020_result_sha256": EXP020_RESULT_SHA256,
        "exp019_result_sha256": EXP019_RESULT_SHA256,
        "training_input_manifest": manifest,
        "folds": folds,
        "aggregate": aggregate,
        "candidate_readiness": candidate_readiness,
        "invariants": invariants,
        "scientific_adjudication": {
            "exp019_status_unchanged": (
                "FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED"
            ),
            "design_audit_only": True,
            "predictive_validation_claim_permitted": False,
            "direction_or_pnl_permitted": False,
        },
        "aug_feature_reparsed": False,
        "older_august_holdout_opened": False,
        "direction_scored": False,
        "pnl_scored": False,
        "network_accessed": False,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    part = output.with_name(output.name + ".part")
    part.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    part.replace(output)
    return payload


def invalid_payload(exc: Exception, frozen_commit: str) -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "status": INVALID_STATUS,
        "frozen_commit": frozen_commit,
        "failure_type": type(exc).__name__,
        "failure_message": str(exc),
        "aug_feature_reparsed": False,
        "older_august_holdout_opened": False,
        "direction_scored": False,
        "pnl_scored": False,
        "network_accessed": False,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--feature-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--frozen-commit", required=True)
    a = p.parse_args(argv)

    if a.output.exists() or a.output.with_name(a.output.name + ".part").exists():
        raise RuntimeError("EXP021 output already exists")

    try:
        result = run(
            a.feature_dir,
            a.output,
            a.workspace.resolve(),
            a.frozen_commit,
        )
    except Exception as exc:
        result = invalid_payload(exc, a.frozen_commit)
        a.output.parent.mkdir(parents=True, exist_ok=True)
        part = a.output.with_name(a.output.name + ".part")
        part.write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        part.replace(a.output)

    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "status": result["status"],
                "selected_calibration_design": result.get(
                    "selected_calibration_design"
                ),
                "failure_type": result.get("failure_type"),
                "failure_message": result.get("failure_message"),
                "candidate_readiness": result.get("candidate_readiness"),
                "aggregate": result.get("aggregate"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

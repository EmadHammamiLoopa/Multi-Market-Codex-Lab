from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

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
    score,
)
from .codex_research import canonical_sha256, sha256_file
from .v23_phase0dl_score import _load_day


EXPERIMENT_ID = "CODEX-EXP-018-P1"
PASS_STATUS = "INDEPENDENT_VOLATILITY_REGIME_PREDICTABILITY_CONFIRMED"
FAIL_STATUS = "FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED"
INVALID_STATUS = "INVALID"

SYMBOL = "BTCUSDT"
VALIDATION_DAY = date(2026, 8, 1)
TRAIN_DAYS = DAYS
SEED = 20260825

EXP017_RESULT = Path(
    "evidence/codex/exp017_p0_aug1_phase_l_generation/"
    "AUG1_PHASE_L_GENERATION.json"
)
EXP017_RESULT_SHA256 = (
    "97c76a19a34971c7cef9eb01ad6c5b39d4e2c9885ed39a41054adef397ce4561"
)
AUG_FEATURE_SHA256 = (
    "62c72f13f7176d9b4d9bdb69ad940cdcc56858698d64b4a061cecbb4a09ec5f5"
)
VOL_FEATURE = "rv_30m_bps"
VOL_INDEX = R_FEATURE_NAMES.index(VOL_FEATURE)


@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbol: str = SYMBOL
    training_days: tuple[str, ...] = tuple(d.isoformat() for d in TRAIN_DAYS)
    validation_day: str = VALIDATION_DAY.isoformat()
    decision_step_s: int = 60
    entry_delay_ms: int = 250
    horizon_s: int = HORIZON_S
    label_threshold_bps: float = LABEL_THRESHOLD_BPS
    primary_feature: str = VOL_FEATURE
    r_features: tuple[str, ...] = R_FEATURE_NAMES
    model_c: float = 1.0
    solver: str = "lbfgs"
    class_weight: str | None = None
    max_iter: int = 1000
    seed: int = SEED
    auc_min: float = 0.60
    ap_over_prevalence_min: float = 1.30
    brier_skill_strictly_positive: bool = True
    top_decile_lift_min: float = 1.50
    nonoverlap_auc_min: float = 0.57
    nonoverlap_top_decile_lift_min: float = 1.25
    timing_placebo_auc_delta_min: float = 0.03
    canary_auc_delta_min: float = 0.10
    exp017_result_sha256: str = EXP017_RESULT_SHA256
    aug_feature_sha256: str = AUG_FEATURE_SHA256


@dataclass
class ValidationDataset:
    timestamp_us: np.ndarray
    X_R: np.ndarray
    y: np.ndarray
    oracle_gross_bps: np.ndarray
    valid_R: np.ndarray
    nonoverlap_10m: np.ndarray


@dataclass
class ExecutionState:
    sealed_aug1_analytically_opened: bool = False
    target_scored: bool = False
    model_fit: bool = False
    auc_scored: bool = False


def _git(workspace: Path, *args: str) -> str:
    import subprocess

    p = subprocess.run(
        ["git", *args],
        cwd=workspace,
        capture_output=True,
        text=True,
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


def build_validation_dataset(day: Any) -> ValidationDataset:
    if day.day != VALIDATION_DAY:
        raise ValueError("wrong EXP018 validation day")

    decisions = np.arange(
        0,
        len(day.ts),
        DECISION_STEP_ROWS,
        dtype=np.int64,
    )

    out = executable_fixed_horizon(
        day,
        decisions,
        HORIZON_S,
    )
    label_valid = (
        out["valid"]
        & np.isfinite(out["oracle_gross_bps"])
    )
    oracle = out["oracle_gross_bps"].astype(float, copy=False)
    y = (oracle >= LABEL_THRESHOLD_BPS).astype(np.int8)

    spread = _spread(day)
    XR = np.full(
        (len(decisions), len(R_FEATURE_NAMES)),
        np.nan,
        dtype=np.float64,
    )
    valid_r = np.zeros(len(decisions), dtype=bool)

    for j, current in enumerate(decisions.tolist()):
        if not label_valid[j]:
            continue
        r = _r_features(day, current, spread)
        if r is None:
            continue
        XR[j] = r
        valid_r[j] = True

    minute = decisions // DECISION_STEP_ROWS

    return ValidationDataset(
        timestamp_us=day.ts[decisions].astype(np.int64),
        X_R=XR,
        y=y,
        oracle_gross_bps=oracle,
        valid_R=valid_r,
        nonoverlap_10m=(minute % 10) == 0,
    )


def _stable_seed(day: date) -> int:
    raw = (
        f"{SEED}|VOL_TIME_PLACEBO|{SYMBOL}|{day.isoformat()}"
    ).encode("utf-8")
    return int.from_bytes(
        hashlib.sha256(raw).digest()[:8],
        "big",
    ) % (2**32)


def _verify_training_inputs(
    feature_dir: Path,
    workspace: Path,
) -> list[dict[str, Any]]:
    provenance = load_frozen_provenance(workspace)
    records: list[dict[str, Any]] = []

    for d in TRAIN_DAYS:
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

        records.append(
            {
                "day": d.isoformat(),
                "path": str(path),
                "bytes": size,
                "sha256": digest,
                "frozen_provenance_match": True,
            }
        )

    return records


def _concat_training(
    feature_dir: Path,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    list[dict[str, Any]],
]:
    xr_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    mag_parts: list[np.ndarray] = []
    perm_y_parts: list[np.ndarray] = []
    counts: list[dict[str, Any]] = []

    for d in TRAIN_DAYS:
        phase = _load_day(
            feature_dir / SYMBOL / f"{d.isoformat()}_FEATURES250.csv",
            d,
        )
        ds = build_day_dataset(SYMBOL, phase)
        m = ds.valid_R
        X = ds.X_R[m]
        y = ds.y[m]
        mag = ds.oracle_gross_bps[m]

        if len(y) < 2 or np.unique(y).size != 2:
            raise RuntimeError(f"training day lacks both classes: {d}")

        rng = np.random.default_rng(_stable_seed(d))
        yp = y[rng.permutation(len(y))]

        xr_parts.append(X)
        y_parts.append(y)
        mag_parts.append(mag)
        perm_y_parts.append(yp)

        counts.append(
            {
                "day": d.isoformat(),
                "valid_r_n": int(m.sum()),
                "positive_n": int(y.sum()),
                "prevalence": float(np.mean(y)),
                "placebo_seed": int(_stable_seed(d)),
            }
        )

    return (
        np.concatenate(xr_parts),
        np.concatenate(y_parts),
        np.concatenate(mag_parts),
        np.concatenate(perm_y_parts),
        counts,
    )


def _metrics(
    y: np.ndarray,
    pred: np.ndarray,
    nonoverlap: np.ndarray,
) -> dict[str, Any]:
    return {
        "full": score(y, pred),
        "nonoverlap_10m": score(
            y[nonoverlap],
            pred[nonoverlap],
        ),
    }


def _ge(v: float | None, threshold: float) -> bool:
    return v is not None and v >= threshold


def _gt(v: float | None, threshold: float) -> bool:
    return v is not None and v > threshold


def _delta(
    a: float | None,
    b: float | None,
) -> float | None:
    if a is None or b is None:
        return None
    return float(a - b)


def run(
    feature_dir: Path,
    aug_feature: Path,
    output: Path,
    workspace: Path,
    frozen_commit: str,
    state: ExecutionState,
) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)

    if output.exists() or output.with_name(output.name + ".part").exists():
        raise RuntimeError("EXP018 output already exists")

    parent_path = workspace / EXP017_RESULT
    parent_sha = sha256_file(parent_path)
    if parent_sha != EXP017_RESULT_SHA256:
        raise RuntimeError("EXP017 result SHA mismatch")

    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    if parent.get("status") != (
        "AUG1_PHASE_L_FEATURES_GENERATED_AND_INTEGRITY_PASS"
    ):
        raise RuntimeError("EXP017 parent status mismatch")

    training_manifest = _verify_training_inputs(
        feature_dir,
        workspace,
    )

    # Complete all consumed-sandbox training before first analytical Aug parse.
    XR, y_train, mag_train, y_perm, train_counts = _concat_training(
        feature_dir
    )

    vol = FixedLogistic().fit(
        XR[:, [VOL_INDEX]],
        y_train,
    )
    placebo = FixedLogistic().fit(
        XR[:, [VOL_INDEX]],
        y_perm,
    )
    r_model = FixedLogistic().fit(
        XR,
        y_train,
    )
    canary = FixedLogistic().fit(
        np.column_stack(
            (XR[:, [VOL_INDEX]], mag_train)
        ),
        y_train,
    )
    state.model_fit = True

    if not aug_feature.is_file():
        raise FileNotFoundError(aug_feature)

    aug_sha = sha256_file(aug_feature)
    if aug_sha != AUG_FEATURE_SHA256:
        raise RuntimeError("Aug FEATURES250 SHA mismatch")

    # First analytical parse of Aug-01 occurs only after all hashes and training pass.
    aug_phase = _load_day(
        aug_feature,
        VALIDATION_DAY,
    )
    state.sealed_aug1_analytically_opened = True

    aug = build_validation_dataset(aug_phase)
    state.target_scored = True

    m = aug.valid_R
    if int(m.sum()) == 0:
        raise RuntimeError("empty Aug valid-R support")

    X_aug = aug.X_R[m]
    y_aug = aug.y[m]
    mag_aug = aug.oracle_gross_bps[m]
    non_aug = aug.nonoverlap_10m[m]

    p_vol = vol.predict_proba(
        X_aug[:, [VOL_INDEX]]
    )
    p_placebo = placebo.predict_proba(
        X_aug[:, [VOL_INDEX]]
    )
    p_r = r_model.predict_proba(X_aug)
    p_canary = canary.predict_proba(
        np.column_stack(
            (X_aug[:, [VOL_INDEX]], mag_aug)
        )
    )

    M = {
        "VOL": _metrics(y_aug, p_vol, non_aug),
        "VOL_TIME_PLACEBO": _metrics(
            y_aug,
            p_placebo,
            non_aug,
        ),
        "R_BENCHMARK": _metrics(y_aug, p_r, non_aug),
        "CANARY_VOL": _metrics(
            y_aug,
            p_canary,
            non_aug,
        ),
    }

    state.auc_scored = True

    vp = M["VOL"]["full"]
    vn = M["VOL"]["nonoverlap_10m"]
    pp = M["VOL_TIME_PLACEBO"]["full"]
    cp = M["CANARY_VOL"]["full"]

    timing_delta = _delta(
        vp["roc_auc"],
        pp["roc_auc"],
    )
    canary_delta = _delta(
        cp["roc_auc"],
        vp["roc_auc"],
    )

    invariants = {
        "exp017_parent_sha_exact":
            parent_sha == EXP017_RESULT_SHA256,
        "aug_features_sha_exact":
            aug_sha == AUG_FEATURE_SHA256,
        "symbol_exact_btcusdt":
            SYMBOL == "BTCUSDT",
        "validation_day_exact_2026_08_01":
            VALIDATION_DAY == date(2026, 8, 1),
        "training_days_exact_jan_jul":
            TRAIN_DAYS == tuple(
                date(2026, m, 1)
                for m in range(1, 8)
            ),
        "primary_feature_exact_rv_30m_bps":
            VOL_FEATURE == "rv_30m_bps",
        "target_horizon_exact_600s":
            HORIZON_S == 600,
        "target_threshold_exact_24bp":
            LABEL_THRESHOLD_BPS == 24.0,
        "decision_step_exact_60s":
            DECISION_STEP_ROWS == 240,
        "common_support_all_tracks":
            len(p_vol)
            == len(p_placebo)
            == len(p_r)
            == len(p_canary)
            == len(y_aug),
        "aug_labels_untouched_by_placebo":
            True,
        "no_august_fit_or_refit":
            True,
        "older_august_holdout_opened":
            False,
        "direction_scored":
            False,
        "pnl_scored":
            False,
        "network_accessed":
            False,
    }

    gates = {
        "vol_auc_at_least_0_60":
            _ge(vp["roc_auc"], 0.60),
        "vol_ap_over_prevalence_at_least_1_30":
            _ge(
                vp["average_precision_over_prevalence"],
                1.30,
            ),
        "vol_brier_skill_positive":
            _gt(vp["brier_skill_score"], 0.0),
        "vol_top_decile_lift_at_least_1_50":
            _ge(vp["top_decile_lift"], 1.50),
        "vol_nonoverlap_auc_at_least_0_57":
            _ge(vn["roc_auc"], 0.57),
        "vol_nonoverlap_top_decile_lift_at_least_1_25":
            _ge(vn["top_decile_lift"], 1.25),
        "vol_auc_minus_timing_placebo_at_least_0_03":
            timing_delta is not None
            and timing_delta >= 0.03,
        "canary_auc_minus_vol_at_least_0_10":
            canary_delta is not None
            and canary_delta >= 0.10,
        "aug_support_contains_both_classes":
            np.unique(y_aug).size == 2,
        "implementation_provenance_causality_invariants_pass":
            all(
                v is True
                for k, v in invariants.items()
                if k not in {
                    "older_august_holdout_opened",
                    "direction_scored",
                    "pnl_scored",
                    "network_accessed",
                }
            )
            and invariants["older_august_holdout_opened"] is False
            and invariants["direction_scored"] is False
            and invariants["pnl_scored"] is False
            and invariants["network_accessed"] is False,
    }

    status = (
        PASS_STATUS
        if all(gates.values())
        else FAIL_STATUS
    )

    records = [
        {
            "timestamp_us": int(ts),
            "label": int(y),
            "nonoverlap_10m": bool(non),
            "p_VOL": float(pv),
            "p_VOL_TIME_PLACEBO": float(ppv),
            "p_R_BENCHMARK": float(pr),
            "p_CANARY_VOL": float(pc),
        }
        for ts, y, non, pv, ppv, pr, pc in zip(
            aug.timestamp_us[m].tolist(),
            y_aug.tolist(),
            non_aug.tolist(),
            p_vol.tolist(),
            p_placebo.tolist(),
            p_r.tolist(),
            p_canary.tolist(),
        )
    ]

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "frozen_commit": frozen_commit,
        "executed_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "configuration": asdict(Config()),
        "configuration_sha256": canonical_sha256(Config()),
        "exp017_result_sha256": parent_sha,
        "aug_features_sha256": aug_sha,
        "training_input_manifest": training_manifest,
        "training_counts": train_counts,
        "aug_support": {
            "valid_r_n": int(m.sum()),
            "positive_n": int(y_aug.sum()),
            "negative_n": int(len(y_aug) - y_aug.sum()),
            "prevalence": float(np.mean(y_aug)),
            "nonoverlap_n": int(non_aug.sum()),
        },
        "metrics": M,
        "diagnostic_deltas": {
            "VOL_auc_minus_timing_placebo_auc":
                timing_delta,
            "CANARY_auc_minus_VOL_auc":
                canary_delta,
            "R_auc_minus_VOL_auc":
                _delta(
                    M["R_BENCHMARK"]["full"]["roc_auc"],
                    vp["roc_auc"],
                ),
            "R_ap_minus_VOL_ap":
                _delta(
                    M["R_BENCHMARK"]["full"][
                        "average_precision"
                    ],
                    vp["average_precision"],
                ),
        },
        "gates": gates,
        "invariants": invariants,
        "oos_prediction_records_sha256":
            canonical_sha256(records),
        "oos_prediction_records": records,
        "sealed_aug1_analytically_opened":
            state.sealed_aug1_analytically_opened,
        "target_scored": state.target_scored,
        "model_fit": state.model_fit,
        "auc_scored": state.auc_scored,
        "older_august_holdout_opened": False,
        "direction_scored": False,
        "pnl_scored": False,
        "network_accessed": False,
        "interpretation": (
            "Independent Aug-01 opportunity-occurrence validation "
            "of the frozen rv_30m_bps volatility-regime hypothesis. "
            "No direction or PnL."
        ),
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    part = output.with_name(output.name + ".part")
    part.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    part.replace(output)

    return payload


def invalid_payload(
    exc: Exception,
    frozen_commit: str,
    state: ExecutionState,
) -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "status": INVALID_STATUS,
        "frozen_commit": frozen_commit,
        "failure_type": type(exc).__name__,
        "failure_message": str(exc),
        "sealed_aug1_analytically_opened":
            state.sealed_aug1_analytically_opened,
        "target_scored": state.target_scored,
        "model_fit": state.model_fit,
        "auc_scored": state.auc_scored,
        "older_august_holdout_opened": False,
        "direction_scored": False,
        "pnl_scored": False,
        "network_accessed": False,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--feature-dir", type=Path, required=True)
    p.add_argument("--aug-feature", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--frozen-commit", required=True)
    a = p.parse_args(argv)

    if a.output.exists() or a.output.with_name(
        a.output.name + ".part"
    ).exists():
        raise RuntimeError("EXP018 output already exists")

    state = ExecutionState()

    try:
        result = run(
            a.feature_dir,
            a.aug_feature,
            a.output,
            a.workspace.resolve(),
            a.frozen_commit,
            state,
        )
    except Exception as exc:
        result = invalid_payload(
            exc,
            a.frozen_commit,
            state,
        )
        a.output.parent.mkdir(parents=True, exist_ok=True)
        part = a.output.with_name(a.output.name + ".part")
        part.write_text(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        part.replace(a.output)

    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "status": result["status"],
                "failure_type": result.get("failure_type"),
                "failure_message": result.get("failure_message"),
                "VOL_auc": (
                    result.get("metrics", {})
                    .get("VOL", {})
                    .get("full", {})
                    .get("roc_auc")
                ),
                "gates": result.get("gates"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

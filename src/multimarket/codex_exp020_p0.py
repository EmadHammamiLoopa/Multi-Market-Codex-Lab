from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .codex_exp004_headroom import DAYS, load_frozen_provenance
from .codex_exp004_p1 import (
    FixedLogistic,
    R_FEATURE_NAMES,
    build_day_dataset,
    score,
)
from .codex_research import canonical_sha256, sha256_file
from .v23_phase0dl_score import _load_day


EXPERIMENT_ID = "CODEX-EXP-020-P0"
STATUS = "DIAGNOSTIC_COMPLETE_VOLATILITY_FALSIFICATION_AND_CALIBRATION"
INVALID = "INVALID"

SYMBOL = "BTCUSDT"
SEED = 20260827
OUTER_DAYS = DAYS[2:]  # Mar-Jul
N_PERMUTATIONS = 200
VOL_FEATURE = "rv_30m_bps"
VOL_INDEX = R_FEATURE_NAMES.index(VOL_FEATURE)

EXP019_RESULT = Path(
    "evidence/codex/exp019_p1_corrected_volatility_aug1/"
    "INDEPENDENT_VOLATILITY_AUG1_CORRECTED.json"
)
EXP019_RESULT_SHA256 = (
    "a6d55db8e938a0c9b80f3e39117c07fd85e0316d408b159f6bd421ffa7920def"
)
EXP019_OOS_SHA256 = (
    "3be80f4e869fe1138f9e395fb382d6b854cbcffe20ff70608a47c4bf286c3b23"
)


@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbol: str = SYMBOL
    training_days: tuple[str, ...] = tuple(d.isoformat() for d in DAYS)
    outer_days: tuple[str, ...] = tuple(d.isoformat() for d in OUTER_DAYS)
    primary_feature: str = VOL_FEATURE
    n_test_feature_permutations: int = N_PERMUTATIONS
    seed: int = SEED
    exp019_result_sha256: str = EXP019_RESULT_SHA256
    exp019_oos_prediction_records_sha256: str = EXP019_OOS_SHA256
    direction_scored: bool = False
    pnl_scored: bool = False
    older_august_holdout_opened: bool = False
    network_accessed: bool = False


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


def verify_exp019(workspace: Path) -> dict[str, Any]:
    path = workspace / EXP019_RESULT
    digest = sha256_file(path)
    if digest != EXP019_RESULT_SHA256:
        raise RuntimeError("EXP019 result SHA mismatch")
    a = json.loads(path.read_text(encoding="utf-8"))
    if a.get("experiment_id") != "CODEX-EXP-019-P1":
        raise RuntimeError("wrong EXP019 experiment id")
    if a.get("status") != "FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED":
        raise RuntimeError("EXP019 frozen status changed")
    if canonical_sha256(a.get("oos_prediction_records", [])) != EXP019_OOS_SHA256:
        raise RuntimeError("EXP019 OOS prediction-record SHA mismatch")
    if a.get("oos_prediction_records_sha256") != EXP019_OOS_SHA256:
        raise RuntimeError("EXP019 recorded OOS SHA mismatch")
    if a.get("sealed_aug1_analytically_opened") is not True:
        raise RuntimeError("EXP019 analytical state mismatch")
    if a.get("older_august_holdout_opened") is not False:
        raise RuntimeError("older August holdout was opened")
    if a.get("direction_scored") is not False or a.get("pnl_scored") is not False:
        raise RuntimeError("EXP019 direction/PnL guard mismatch")
    if a.get("network_accessed") is not False:
        raise RuntimeError("EXP019 network guard mismatch")
    return a


def verify_training_inputs(
    feature_dir: Path,
    workspace: Path,
) -> list[dict[str, Any]]:
    provenance = load_frozen_provenance(workspace)
    out: list[dict[str, Any]] = []
    for day in DAYS:
        path = feature_dir / SYMBOL / f"{day.isoformat()}_FEATURES250.csv"
        if not path.is_file():
            raise FileNotFoundError(path)
        frozen = provenance[(SYMBOL, day.isoformat())]
        size = int(path.stat().st_size)
        digest = sha256_file(path)
        if size != int(frozen["bytes"]):
            raise RuntimeError(f"training feature size mismatch: {day}")
        if digest != str(frozen["sha256"]):
            raise RuntimeError(f"training feature SHA mismatch: {day}")
        out.append(
            {
                "day": day.isoformat(),
                "path": str(path),
                "bytes": size,
                "sha256": digest,
                "frozen_provenance_match": True,
            }
        )
    return out


def load_consumed_days(feature_dir: Path) -> dict[date, Any]:
    data: dict[date, Any] = {}
    for day in DAYS:
        phase = _load_day(
            feature_dir / SYMBOL / f"{day.isoformat()}_FEATURES250.csv",
            day,
        )
        data[day] = build_day_dataset(SYMBOL, phase)
    return data


def _concat_training(days: list[Any]) -> tuple[np.ndarray, np.ndarray]:
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    for d in days:
        m = d.valid_R
        xs.append(d.X_R[m][:, [VOL_INDEX]])
        ys.append(d.y[m])
    return np.concatenate(xs), np.concatenate(ys)


def _average_ranks(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(len(x), dtype=float)
    i = 0
    while i < len(x):
        j = i + 1
        while j < len(x) and x[order[j]] == x[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2.0
        ranks[order[i:j]] = rank
        i = j
    return ranks


def _corr(a: np.ndarray, b: np.ndarray) -> float | None:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) < 2 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def monotonic_placebo_diagnostic(exp019: dict[str, Any]) -> dict[str, Any]:
    rows = exp019["oos_prediction_records"]
    p = np.asarray([r["p_VOL"] for r in rows], dtype=float)
    q = np.asarray([r["p_VOL_TIME_PLACEBO"] for r in rows], dtype=float)
    rp = _average_ranks(p)
    rq = _average_ranks(q)
    order_p = np.argsort(p, kind="mergesort")
    order_q = np.argsort(q, kind="mergesort")
    return {
        "n": int(len(rows)),
        "pearson_prediction_correlation": _corr(p, q),
        "spearman_rank_correlation": _corr(rp, rq),
        "stable_sorted_order_identical": bool(np.array_equal(order_p, order_q)),
        "max_absolute_probability_difference": float(np.max(np.abs(p - q))),
        "mean_absolute_probability_difference": float(np.mean(np.abs(p - q))),
        "vol_auc": exp019["metrics"]["VOL"]["full"]["roc_auc"],
        "placebo_auc": exp019["metrics"]["VOL_TIME_PLACEBO"]["full"]["roc_auc"],
        "vol_ap": exp019["metrics"]["VOL"]["full"]["average_precision"],
        "placebo_ap": exp019["metrics"]["VOL_TIME_PLACEBO"]["full"]["average_precision"],
        "interpretation": (
            "Identical rank order implies identical ROC AUC/AP/top-k ranking for "
            "these one-feature monotonic probability transforms; calibration can "
            "still differ."
        ),
    }


def _perm_seed(day: date, replicate: int) -> int:
    raw = (
        f"{SEED}|EXP020|VOL_TEST_FEATURE_PERM|"
        f"{day.isoformat()}|{replicate}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") % (2**32)


def _auc(y: np.ndarray, p: np.ndarray) -> float:
    value = score(y, p)["roc_auc"]
    if value is None:
        raise RuntimeError("AUC undefined in EXP020 permutation diagnostic")
    return float(value)


def test_feature_permutation_diagnostic(
    data: dict[date, Any],
) -> dict[str, Any]:
    folds: list[dict[str, Any]] = []
    pooled_y_parts: list[np.ndarray] = []
    pooled_real_parts: list[np.ndarray] = []
    pooled_perm_parts: list[list[np.ndarray]] = [
        [] for _ in range(N_PERMUTATIONS)
    ]

    for outer_day in OUTER_DAYS:
        train_days = [d for d in DAYS if d < outer_day]
        train = [data[d] for d in train_days]
        outer = data[outer_day]

        Xtr, ytr = _concat_training(train)
        model = FixedLogistic().fit(Xtr, ytr)

        m = outer.valid_R
        Xo = outer.X_R[m][:, [VOL_INDEX]]
        yo = outer.y[m]

        real_p = model.predict_proba(Xo)
        real_auc = _auc(yo, real_p)

        perm_auc: list[float] = []
        for rep in range(N_PERMUTATIONS):
            rng = np.random.default_rng(_perm_seed(outer_day, rep))
            idx = rng.permutation(len(Xo))
            pp = model.predict_proba(Xo[idx])
            perm_auc.append(_auc(yo, pp))
            pooled_perm_parts[rep].append(pp)

        pa = np.asarray(perm_auc, dtype=float)
        empirical_p = float(
            (1 + int(np.sum(pa >= real_auc)))
            / (1 + N_PERMUTATIONS)
        )

        folds.append(
            {
                "outer_day": outer_day.isoformat(),
                "train_days": [d.isoformat() for d in train_days],
                "outer_n": int(len(yo)),
                "outer_prevalence": float(np.mean(yo)),
                "real_auc": real_auc,
                "permutation_auc_mean": float(np.mean(pa)),
                "permutation_auc_median": float(np.median(pa)),
                "permutation_auc_q95": float(np.quantile(pa, 0.95)),
                "empirical_one_sided_p": empirical_p,
            }
        )

        pooled_y_parts.append(yo)
        pooled_real_parts.append(real_p)

    pooled_y = np.concatenate(pooled_y_parts)
    pooled_real = np.concatenate(pooled_real_parts)
    pooled_real_auc = _auc(pooled_y, pooled_real)

    pooled_perm_auc = np.asarray(
        [
            _auc(pooled_y, np.concatenate(parts))
            for parts in pooled_perm_parts
        ],
        dtype=float,
    )
    pooled_p = float(
        (1 + int(np.sum(pooled_perm_auc >= pooled_real_auc)))
        / (1 + N_PERMUTATIONS)
    )

    return {
        "folds": folds,
        "pooled": {
            "n": int(len(pooled_y)),
            "prevalence": float(np.mean(pooled_y)),
            "real_auc": pooled_real_auc,
            "permutation_auc_mean": float(np.mean(pooled_perm_auc)),
            "permutation_auc_median": float(np.median(pooled_perm_auc)),
            "permutation_auc_q95": float(np.quantile(pooled_perm_auc, 0.95)),
            "empirical_one_sided_p": pooled_p,
        },
        "n_permutations": N_PERMUTATIONS,
    }


def _prior_shift_correct(
    p: np.ndarray,
    pi_train: float,
    pi_target: float,
) -> np.ndarray:
    eps = 1e-12
    p = np.clip(np.asarray(p, dtype=float), eps, 1 - eps)
    if not (0 < pi_train < 1 and 0 < pi_target < 1):
        raise RuntimeError("invalid prevalence for prior-shift correction")
    odds = p / (1 - p)
    train_odds = pi_train / (1 - pi_train)
    target_odds = pi_target / (1 - pi_target)
    corrected_odds = odds * (target_odds / train_odds)
    return corrected_odds / (1 + corrected_odds)


def calibration_shift_diagnostic(exp019: dict[str, Any]) -> dict[str, Any]:
    counts = exp019["training_counts"]
    total_n = int(sum(int(r["valid_r_n"]) for r in counts))
    total_pos = int(sum(int(r["positive_n"]) for r in counts))
    pi_train = float(total_pos / total_n)

    rows = exp019["oos_prediction_records"]
    y = np.asarray([r["label"] for r in rows], dtype=np.int8)
    p_vol = np.asarray([r["p_VOL"] for r in rows], dtype=float)
    p_placebo = np.asarray(
        [r["p_VOL_TIME_PLACEBO"] for r in rows],
        dtype=float,
    )
    p_r = np.asarray([r["p_R_BENCHMARK"] for r in rows], dtype=float)
    pi_aug = float(np.mean(y))

    baseline_brier = float(np.mean((y - pi_aug) ** 2))
    observed = score(y, p_vol)

    corrected = _prior_shift_correct(p_vol, pi_train, pi_aug)
    corrected_metrics = score(y, corrected)

    return {
        "training_prevalence_by_day": [
            {
                "day": r["day"],
                "n": int(r["valid_r_n"]),
                "positive_n": int(r["positive_n"]),
                "prevalence": float(r["prevalence"]),
            }
            for r in counts
        ],
        "pooled_train_n": total_n,
        "pooled_train_positive_n": total_pos,
        "pooled_train_prevalence": pi_train,
        "aug_n": int(len(y)),
        "aug_positive_n": int(np.sum(y)),
        "aug_prevalence": pi_aug,
        "prevalence_ratio_aug_over_train": float(pi_aug / pi_train),
        "mean_p_VOL": float(np.mean(p_vol)),
        "mean_p_VOL_TIME_PLACEBO": float(np.mean(p_placebo)),
        "mean_p_R_BENCHMARK": float(np.mean(p_r)),
        "prevalence_baseline_brier": baseline_brier,
        "observed_VOL_metrics": observed,
        "descriptive_prior_shift_corrected_VOL_metrics": corrected_metrics,
        "descriptive_prior_shift_mean_probability": float(np.mean(corrected)),
        "prior_shift_uses_observed_aug_prevalence": True,
        "promotion_permitted": False,
    }


def run(
    feature_dir: Path,
    output: Path,
    workspace: Path,
    frozen_commit: str,
) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)

    if output.exists() or output.with_name(output.name + ".part").exists():
        raise RuntimeError("EXP020 output already exists")

    exp019 = verify_exp019(workspace)
    training_manifest = verify_training_inputs(feature_dir, workspace)
    data = load_consumed_days(feature_dir)

    mono = monotonic_placebo_diagnostic(exp019)
    perm = test_feature_permutation_diagnostic(data)
    cal = calibration_shift_diagnostic(exp019)

    invariants = {
        "exp019_result_sha_exact": (
            sha256_file(workspace / EXP019_RESULT)
            == EXP019_RESULT_SHA256
        ),
        "exp019_oos_records_sha_exact": (
            canonical_sha256(exp019["oos_prediction_records"])
            == EXP019_OOS_SHA256
        ),
        "exp019_status_remains_frozen_fail": (
            exp019["status"]
            == "FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED"
        ),
        "training_days_exact_jan_jul": (
            DAYS == tuple(date(2026, m, 1) for m in range(1, 8))
        ),
        "outer_days_exact_mar_jul": (
            OUTER_DAYS == tuple(date(2026, m, 1) for m in range(3, 8))
        ),
        "primary_feature_exact_rv_30m_bps": VOL_FEATURE == "rv_30m_bps",
        "n_permutations_exact_200": N_PERMUTATIONS == 200,
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
    invariant_pass = all(
        (v is False if k in expected_false else v is True)
        for k, v in invariants.items()
    )
    if not invariant_pass:
        raise RuntimeError("EXP020 invariant failure")

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": STATUS,
        "frozen_commit": frozen_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": asdict(Config()),
        "configuration_sha256": canonical_sha256(Config()),
        "exp019_result_sha256": EXP019_RESULT_SHA256,
        "exp019_oos_prediction_records_sha256": EXP019_OOS_SHA256,
        "training_input_manifest": training_manifest,
        "diagnostic_A_monotonic_placebo": mono,
        "diagnostic_B_test_feature_permutation": perm,
        "diagnostic_C_calibration_base_rate_shift": cal,
        "invariants": invariants,
        "scientific_adjudication": {
            "exp019_status_unchanged": (
                "FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED"
            ),
            "exp020_is_diagnostic_only": True,
            "promotion_permitted": False,
            "independent_validation_claim_permitted": False,
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
        "status": INVALID,
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
        raise RuntimeError("EXP020 output already exists")

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
                "failure_type": result.get("failure_type"),
                "failure_message": result.get("failure_message"),
                "pooled_test_feature_perm": (
                    result.get("diagnostic_B_test_feature_permutation", {})
                    .get("pooled")
                ),
                "calibration": (
                    result.get("diagnostic_C_calibration_base_rate_shift", {})
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

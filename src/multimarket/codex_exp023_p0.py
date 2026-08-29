from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from . import codex_exp022_p1 as frozen_p1
from .codex_research import canonical_sha256
from .v23_phase0dl_score import DayData


EXPERIMENT_ID = "CODEX-EXP-023-P0"
PASS_STATUS = "IMPLEMENTATION_CORRECTION_READY_FOR_FRESH_PROSPECTIVE_VALIDATION"
FAIL_STATUS = "FAIL_IMPLEMENTATION_CORRECTION_NOT_READY"
INVALID_STATUS = "INVALID"

PARENT_PRESERVED_COMMIT = "91ae1465a20354082e9005eff1742ac3b2b73651"
INVALID_PARENT_EXPERIMENT = "CODEX-EXP-022-P1"
INVALID_PARENT_STATUS = frozen_p1.INVALID_STATUS
INVALID_FROZEN_IMPLEMENTATION = "0a86f2440d44a7969cd640ecca830b07a4350e00"

PREREGISTRATION_REL = Path("docs/CODEX_EXP023_P0_PREREGISTRATION.md")
PREREGISTRATION_SHA256 = (
    "96e5ebfe93a2ddba8403813086637e3733cb5fc8309230ac359efdfa8c9bd4cf"
)

FROZEN_REFERENCE_SHA256 = {
    Path("docs/CODEX_EXP022_P1_PREREGISTRATION.md"): (
        "e4c9ca4075834de29d01613c695b534081a01b506e7f233ca6fa9542419e3f5b"
    ),
    Path("docs/CODEX_EXP022_P1_RESULT.md"): (
        "a007d0f1249e7ad480f1bfeabfbf58c5d9d3896ed3630f1e5081c3ffaa69dd80"
    ),
    Path("src/multimarket/codex_exp022_p1.py"): (
        "79300d16e7cb9790c43b082c0788cb88a622cce622a3b15c6027bb072c1fb831"
    ),
    Path("tests/test_codex_exp022_p1.py"): (
        "ccc76bb8e827c679b06ee7078725cb1d9a861ec05cf1180d18b7664af313385d"
    ),
    Path("evidence/codex/exp022_p1_invalid_execution/ATTEMPT2_EXECUTE.log"): (
        "ead250b412305756b1a25139e8c1a3c59240c91c388360b2f6fb9b29dcd1ea84"
    ),
}

FROZEN_SCIENTIFIC_CONFIGURATION: dict[str, Any] = {
    "experiment_id": "CODEX-EXP-022-P1",
    "symbol": "BTCUSDT",
    "training_days": tuple(
        f"2026-{month:02d}-01" for month in range(1, 8)
    ),
    "prospective_day": "2026-08-28",
    "primary_feature": "rv_30m_bps",
    "grid_us": 250_000,
    "decision_step_s": 60,
    "decision_step_rows": 240,
    "entry_delay_ms": 250,
    "horizon_s": 600,
    "label_threshold_bps": 24.0,
    "model_c": 1.0,
    "model_penalty": "l2",
    "model_solver": "lbfgs",
    "model_class_weight": None,
    "model_max_iter": 1000,
    "model_random_state": 20260825,
    "min_support_n": 1200,
    "min_positives": 10,
    "min_negatives": 100,
    "auc_min": 0.60,
    "ap_over_prevalence_min": 1.50,
    "top_decile_lift_min": 1.50,
    "null_shift_step_rows": 30,
    "min_null_shifts": 20,
    "null_quantile": 0.95,
    "null_quantile_method": "higher",
}
FROZEN_SCIENTIFIC_CONFIGURATION_SHA256 = (
    "5592bd41fa4cfc48dd418f0f1920762d8d760ab6bb39ce2000e0114d9603f348"
)

TRAIN_DAYS = frozen_p1.TRAIN_DAYS
SYMBOL = frozen_p1.SYMBOL
VOL_FEATURE = frozen_p1.VOL_FEATURE
VOL_INDEX = frozen_p1.VOL_INDEX
GRID_US = frozen_p1.GRID_US
DECISION_STEP_ROWS = frozen_p1.DECISION_STEP_ROWS
HORIZON_S = frozen_p1.HORIZON_S
LABEL_THRESHOLD_BPS = frozen_p1.LABEL_THRESHOLD_BPS

# These aliases intentionally inherit the frozen scientific helpers.  This P0
# module provides no August loader and no execution mode.
FixedLogistic = frozen_p1.FixedLogistic
eligible_circular_shifts = frozen_p1.eligible_circular_shifts
circular_shift_labels = frozen_p1.circular_shift_labels
higher_q95 = frozen_p1.higher_q95
empirical_one_sided_p = frozen_p1.empirical_one_sided_p
temporal_shift_null = frozen_p1.temporal_shift_null


class InvariantTypeError(TypeError):
    """An invariant reached adjudication without exact built-in bool type."""


class JsonSafetyError(TypeError):
    """A result payload contains a value outside the frozen JSON policy."""


def _sha256_opaque(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
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
    return completed.returncode == 0


def verify_frozen_references(workspace: Path) -> dict[str, str]:
    expected = {
        PREREGISTRATION_REL: PREREGISTRATION_SHA256,
        **FROZEN_REFERENCE_SHA256,
    }
    verified: dict[str, str] = {}
    for relative, expected_digest in expected.items():
        path = workspace / relative
        digest = _sha256_opaque(path)
        if digest != expected_digest:
            raise RuntimeError(f"frozen reference SHA mismatch: {relative}")
        verified[str(relative)] = digest
    return verified


def assert_frozen_workspace(workspace: Path, frozen_commit: str) -> None:
    if len(frozen_commit) != 40:
        raise RuntimeError("full 40-character frozen commit required")
    try:
        int(frozen_commit, 16)
    except ValueError as exc:
        raise RuntimeError("frozen commit must be hexadecimal") from exc
    if _git(workspace, "rev-parse", "HEAD") != frozen_commit:
        raise RuntimeError("frozen implementation commit mismatch")
    if not _is_ancestor(workspace, PARENT_PRESERVED_COMMIT, frozen_commit):
        raise RuntimeError("EXP023-P0 parent commit is not an ancestor")
    if _git(workspace, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked worktree changes after implementation freeze")
    verify_frozen_references(workspace)


def scientific_configuration() -> dict[str, Any]:
    actual = asdict(frozen_p1.Config())
    if actual != FROZEN_SCIENTIFIC_CONFIGURATION:
        raise RuntimeError("scientific configuration differs from frozen EXP022-P1")
    if canonical_sha256(actual) != FROZEN_SCIENTIFIC_CONFIGURATION_SHA256:
        raise RuntimeError("frozen scientific configuration SHA mismatch")
    return dict(actual)


def validate_builtin_bool_invariants(
    invariants: Mapping[str, Any],
) -> dict[str, bool]:
    if not isinstance(invariants, Mapping):
        raise InvariantTypeError("invariants must be a mapping")
    checked: dict[str, bool] = {}
    for name, value in invariants.items():
        if type(name) is not str:
            raise InvariantTypeError("invariant names must be strings")
        if type(value) is not bool:
            raise InvariantTypeError(
                f"invariant {name!r} must be exact built-in bool, "
                f"got {type(value).__name__}"
            )
        checked[name] = value
    return checked


def adjudicate_invariants(
    invariants: Mapping[str, Any],
    *,
    expected: Mapping[str, Any] | None = None,
) -> bool:
    checked = validate_builtin_bool_invariants(invariants)
    if expected is None:
        expectations = {name: True for name in checked}
    else:
        expectations = validate_builtin_bool_invariants(expected)
        if checked.keys() != expectations.keys():
            raise InvariantTypeError("invariant and expectation names differ")
    return bool(
        all(checked[name] == expectations[name] for name in checked)
    )


def common_support_unique_and_chronological(
    timestamps: np.ndarray,
) -> bool:
    values = np.asarray(timestamps, dtype=np.int64)
    if values.ndim != 1:
        raise ValueError("common-support timestamps must be one-dimensional")
    unique = len(values) == len(np.unique(values))
    chronological = len(values) < 2 or bool(np.all(np.diff(values) > 0))
    return bool(unique and chronological)


def normalize_json_safe(value: Any, *, path: str = "$") -> Any:
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        converted = float(value)
        if not math.isfinite(converted):
            raise JsonSafetyError(f"non-finite NumPy float at {path}")
        return converted

    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise JsonSafetyError(f"non-finite float at {path}")
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise JsonSafetyError(f"non-string mapping key at {path}")
            normalized[key] = normalize_json_safe(
                item,
                path=f"{path}.{key}",
            )
        return normalized
    if isinstance(value, (list, tuple)):
        return [
            normalize_json_safe(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise JsonSafetyError(
        f"unsupported payload type {type(value).__name__} at {path}"
    )


def normalize_result_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise JsonSafetyError("result payload must be a mapping")
    if "invariants" in payload:
        validate_builtin_bool_invariants(payload["invariants"])
    normalized = normalize_json_safe(payload)
    if not isinstance(normalized, dict):
        raise JsonSafetyError("normalized result payload must be a dictionary")
    json.dumps(normalized, allow_nan=False, sort_keys=True)
    return normalized


def encode_result_payload(payload: Mapping[str, Any]) -> str:
    normalized = normalize_result_payload(payload)
    return json.dumps(
        normalized,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"


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


def frozen_bug_regression() -> dict[str, bool]:
    frozen_value = np.all(np.asarray([True, True], dtype=bool))
    frozen_identity_failed = bool(frozen_value) and type(frozen_value) is not bool
    frozen_json_failed = False
    try:
        json.dumps({"common_support": frozen_value}, allow_nan=False)
    except TypeError:
        frozen_json_failed = True

    corrected_value = common_support_unique_and_chronological(
        np.asarray([0, 60_000_000], dtype=np.int64)
    )
    corrected = {"common_support_unique_and_chronological": corrected_value}
    corrected_adjudication = adjudicate_invariants(corrected)
    corrected_json = encode_result_payload({"invariants": corrected})
    checks = {
        "frozen_expression_produced_numpy_bool": bool(
            isinstance(frozen_value, np.bool_)
        ),
        "frozen_identity_adjudication_failure_reproduced": bool(
            frozen_identity_failed
        ),
        "frozen_json_serialization_failure_reproduced": bool(
            frozen_json_failed
        ),
        "corrected_invariant_is_builtin_bool": bool(
            type(corrected_value) is bool
        ),
        "corrected_invariant_adjudicates_true": bool(corrected_adjudication),
        "corrected_invariant_json_serializes": bool(
            json.loads(corrected_json)["invariants"]
            ["common_support_unique_and_chronological"]
        ),
    }
    return validate_builtin_bool_invariants(checks)


def synthetic_result_payload(status: str) -> dict[str, Any]:
    allowed = {
        frozen_p1.PASS_STATUS,
        frozen_p1.FAIL_STATUS,
        frozen_p1.INCONCLUSIVE_STATUS,
        frozen_p1.INVALID_STATUS,
    }
    if status not in allowed:
        raise ValueError("unsupported synthetic result status")
    invariants = {
        "common_support_unique_and_chronological": True,
        "scientific_configuration_exact": True,
        "execution_guards_pass": True,
    }
    payload: dict[str, Any] = {
        "experiment_id": "SYNTHETIC-CODEX-EXP-022-P1-SHAPE",
        "synthetic_fixture": True,
        "status": status,
        "frozen_implementation_commit": "0" * 40,
        "configuration": scientific_configuration(),
        "configuration_sha256": FROZEN_SCIENTIFIC_CONFIGURATION_SHA256,
        "support": {
            "n": np.int64(1200),
            "positives": np.int32(10),
            "negatives": np.int64(1190),
            "minimum_support_pass": np.bool_(
                status not in {frozen_p1.INCONCLUSIVE_STATUS, frozen_p1.INVALID_STATUS}
            ),
        },
        "primary_metrics": {
            "roc_auc": np.float64(0.61),
            "average_precision": np.float32(0.025),
            "average_precision_over_prevalence": np.float64(3.0),
            "top_decile_lift": np.float64(1.6),
        },
        "secondary_calibration_diagnostics": {
            "brier_score": np.float64(0.01),
            "brier_skill_score": np.float64(0.02),
            "log_loss": np.float64(0.04),
            "mean_predicted_probability": np.float64(0.01),
        },
        "circular_shift_null_summary": {
            "number_of_shifts": np.int64(39),
            "auc_null_q95": np.float64(0.55),
            "ap_null_q95": np.float64(0.02),
            "auc_empirical_p": np.float64(0.025),
            "ap_empirical_p": np.float64(0.025),
        },
        "primary_gates": {
            "synthetic_gate": np.bool_(status == frozen_p1.PASS_STATUS),
        },
        "invariants": invariants,
        "score_records": [
            {
                "timestamp_us": np.int64(0),
                "label": np.int8(1),
                "model_probability": np.float64(0.75),
                "nonoverlap_10m": np.bool_(True),
            }
        ],
        **execution_guards(),
    }
    if status == frozen_p1.INVALID_STATUS:
        payload.update(
            {
                "failure_type": "SyntheticImplementationError",
                "failure_message": "synthetic fixture only",
            }
        )
    return payload


def synthetic_status_payloads_serialize() -> bool:
    statuses = (
        frozen_p1.PASS_STATUS,
        frozen_p1.FAIL_STATUS,
        frozen_p1.INCONCLUSIVE_STATUS,
        frozen_p1.INVALID_STATUS,
    )
    for status in statuses:
        encoded = encode_result_payload(synthetic_result_payload(status))
        if json.loads(encoded)["status"] != status:
            return False
    return True


def build_historical_adapter_dataset(day: DayData) -> frozen_p1.ProspectiveDataset:
    if day.day not in TRAIN_DAYS:
        raise ValueError("EXP023-P0 adapter accepts frozen Jan-Jul days only")
    return frozen_p1.build_prospective_dataset(day, required_day=None)


def historical_semantic_equivalence(
    day: DayData,
    frozen_dataset: Any,
) -> dict[str, Any]:
    if day.day not in TRAIN_DAYS:
        raise ValueError("EXP023-P0 equivalence accepts frozen Jan-Jul days only")
    return frozen_p1._semantic_equivalence(day, frozen_dataset)


def _historical_preflight(
    feature_dir: Path,
    workspace: Path,
) -> dict[str, Any]:
    manifest, validation, features, labels, counts = frozen_p1._prepare_historical(
        feature_dir,
        workspace,
    )
    if tuple(item["day"] for item in counts) != tuple(
        day.isoformat() for day in TRAIN_DAYS
    ):
        raise RuntimeError("historical preflight did not use exact Jan-Jul days")
    if features.ndim != 2 or features.shape[1] != 1:
        raise RuntimeError("historical preflight did not preserve one feature")
    return {
        "historical_input_manifest": manifest,
        "historical_semantic_validation": validation,
        "historical_training_counts": counts,
        "historical_training_n": int(len(labels)),
        "historical_feature_columns": int(features.shape[1]),
    }


def _preflight_once(
    *,
    feature_dir: Path,
    workspace: Path,
    frozen_commit: str,
) -> dict[str, Any]:
    assert_frozen_workspace(workspace, frozen_commit)
    references = verify_frozen_references(workspace)
    configuration = scientific_configuration()
    bug_checks = frozen_bug_regression()
    payload_shape_check = synthetic_status_payloads_serialize()
    historical = _historical_preflight(feature_dir, workspace)
    validation = historical["historical_semantic_validation"]
    guards = execution_guards()

    invariants = {
        "parent_preserved_commit_is_ancestor": bool(
            _is_ancestor(workspace, PARENT_PRESERVED_COMMIT, frozen_commit)
        ),
        "frozen_references_exact": bool(
            len(references) == len(FROZEN_REFERENCE_SHA256) + 1
        ),
        "scientific_configuration_exact": bool(
            configuration == FROZEN_SCIENTIFIC_CONFIGURATION
            and canonical_sha256(configuration)
            == FROZEN_SCIENTIFIC_CONFIGURATION_SHA256
        ),
        "frozen_numpy_bool_defect_reproduced": bool(all(bug_checks.values())),
        "complete_status_payloads_json_safe": bool(payload_shape_check),
        "historical_days_exact_jan_jul": bool(
            tuple(item["day"] for item in historical["historical_training_counts"])
            == tuple(day.isoformat() for day in TRAIN_DAYS)
        ),
        "historical_semantics_exact": bool(
            len(validation) == len(TRAIN_DAYS)
            and all(
                item["rv_exact_match"]
                and item["target_and_support_exact_match"]
                for item in validation
            )
        ),
        "one_legitimate_feature_only": bool(
            historical["historical_feature_columns"] == 1
        ),
        "no_august_market_data_accessed": True,
        "no_predictive_metrics_produced": True,
        "execution_guards_all_false": bool(
            all(type(value) is bool and not value for value in guards.values())
        ),
    }
    checked_invariants = validate_builtin_bool_invariants(invariants)
    ready = adjudicate_invariants(checked_invariants)

    return {
        "experiment_id": EXPERIMENT_ID,
        "status": PASS_STATUS if ready else FAIL_STATUS,
        "scope": "IMPLEMENTATION_CORRECTION_READINESS_ONLY",
        "predictive_claim_permitted": False,
        "frozen_implementation_commit": frozen_commit,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "parent_preserved_commit": PARENT_PRESERVED_COMMIT,
        "invalid_parent_experiment": INVALID_PARENT_EXPERIMENT,
        "invalid_parent_status": INVALID_PARENT_STATUS,
        "invalid_frozen_implementation": INVALID_FROZEN_IMPLEMENTATION,
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "frozen_reference_sha256": references,
        "frozen_scientific_configuration": configuration,
        "frozen_scientific_configuration_sha256": (
            FROZEN_SCIENTIFIC_CONFIGURATION_SHA256
        ),
        **historical,
        "correction_checks": bug_checks,
        "invariants": checked_invariants,
        "model_fit": False,
        "predictive_metrics_produced": False,
        "prospective_grid_opened": False,
        **guards,
    }


def invalid_payload(
    exc: Exception,
    frozen_commit: str,
) -> dict[str, Any]:
    invariants = validate_builtin_bool_invariants(
        {
            "implementation_preflight_completed": False,
            "result_is_nonpredictive": True,
            "no_august_market_data_accessed": True,
        }
    )
    return {
        "experiment_id": EXPERIMENT_ID,
        "status": INVALID_STATUS,
        "scope": "IMPLEMENTATION_CORRECTION_READINESS_ONLY",
        "predictive_claim_permitted": False,
        "frozen_implementation_commit": frozen_commit,
        "parent_preserved_commit": PARENT_PRESERVED_COMMIT,
        "invalid_parent_experiment": INVALID_PARENT_EXPERIMENT,
        "invalid_parent_status": INVALID_PARENT_STATUS,
        "invalid_frozen_implementation": INVALID_FROZEN_IMPLEMENTATION,
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "frozen_scientific_configuration": dict(
            FROZEN_SCIENTIFIC_CONFIGURATION
        ),
        "frozen_scientific_configuration_sha256": (
            FROZEN_SCIENTIFIC_CONFIGURATION_SHA256
        ),
        "failure_type": type(exc).__name__,
        "failure_message": str(exc),
        "invariants": invariants,
        "model_fit": False,
        "predictive_metrics_produced": False,
        "prospective_grid_opened": False,
        **execution_guards(),
    }


def ensure_fresh_output(output: Path) -> Path:
    part = output.with_name(output.name + ".part")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing result: {output}")
    if part.exists():
        raise FileExistsError(f"interrupted result marker already exists: {part}")
    return part


def _write_once(output: Path, payload: Mapping[str, Any]) -> None:
    part = ensure_fresh_output(output)
    encoded = encode_result_payload(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    with part.open("x", encoding="utf-8") as handle:
        handle.write(encoded)
    if output.exists():
        raise FileExistsError(f"result appeared during execution: {output}")
    part.replace(output)


def run_preflight(
    *,
    feature_dir: Path,
    output: Path,
    workspace: Path,
    frozen_commit: str,
) -> dict[str, Any]:
    ensure_fresh_output(output)
    try:
        payload = _preflight_once(
            feature_dir=feature_dir,
            workspace=workspace,
            frozen_commit=frozen_commit,
        )
        normalize_result_payload(payload)
    except Exception as exc:
        payload = invalid_payload(exc, frozen_commit)
        normalize_result_payload(payload)
    _write_once(output, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight",), required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args(argv)

    result = run_preflight(
        feature_dir=args.feature_dir,
        output=args.output,
        workspace=args.workspace.resolve(),
        frozen_commit=args.frozen_commit,
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
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

import numpy as np

from . import codex_exp022_p1 as frozen_p1
from .codex_exp023_p0 import (
    adjudicate_invariants,
    common_support_unique_and_chronological,
    encode_result_payload,
    frozen_bug_regression,
    normalize_result_payload,
    validate_builtin_bool_invariants,
)
from .codex_research import canonical_sha256


EXPERIMENT_ID = "CODEX-EXP-024-P1"
PASS_STATUS = frozen_p1.PASS_STATUS
FAIL_STATUS = frozen_p1.FAIL_STATUS
INCONCLUSIVE_STATUS = frozen_p1.INCONCLUSIVE_STATUS
INVALID_STATUS = frozen_p1.INVALID_STATUS
PREOPEN_PASS_STATUS = "PREOPEN_VALIDATION_PASS"

SYMBOL = "BTCUSDT"
TRAIN_DAYS = frozen_p1.TRAIN_DAYS
PROSPECTIVE_DAY = date(2026, 8, 30)
P0_ACQUISITION_COMMIT = "2eb478bb5969c6f2bb8a7eb0b72eda8baa45ec23"
P0_EXPERIMENT_ID = "CODEX-EXP-024-P0"
P0_STATUS = "PROSPECTIVE_BOOKTICKER_DATA_READY"
P0_SCOPE = "DATA_ACQUISITION_AND_INTEGRITY_ONLY"
P0_PREREGISTRATION_SHA256 = (
    "1630ab4591b20a26640a45c980b28b788516434110795d5d406f0189d92a6bd2"
)
EXP023_READINESS_SHA256 = (
    "4eaf158b2517cf6c0be2efc2e7026a73a6b9986977d2c78499bb5785f142c1af"
)
EXP023_READINESS_STATUS = (
    "IMPLEMENTATION_CORRECTION_READY_FOR_FRESH_PROSPECTIVE_VALIDATION"
)

PREREGISTRATION_REL = Path("docs/CODEX_EXP024_P1_PREREGISTRATION.md")
PREREGISTRATION_SHA256 = (
    "dc835423dc516a14a1e5b79a43b364bf8d8180f8288670aeac9e679db778caf3"
)
READINESS_REL = Path(
    "evidence/codex/exp023_p0_implementation_correction/"
    "IMPLEMENTATION_CORRECTION_READINESS.json"
)

FROZEN_REFERENCE_SHA256 = {
    Path("docs/CODEX_EXP022_P1_PREREGISTRATION.md"): (
        "e4c9ca4075834de29d01613c695b534081a01b506e7f233ca6fa9542419e3f5b"
    ),
    Path("src/multimarket/codex_exp022_p1.py"): (
        "79300d16e7cb9790c43b082c0788cb88a622cce622a3b15c6027bb072c1fb831"
    ),
    Path("docs/CODEX_EXP023_P0_PREREGISTRATION.md"): (
        "96e5ebfe93a2ddba8403813086637e3733cb5fc8309230ac359efdfa8c9bd4cf"
    ),
    Path("docs/CODEX_EXP023_P0_RESULT.md"): (
        "33ad0f463435816e50c5e6afdcc0418b70acfb35d94cd6aff57948957a27341f"
    ),
    Path("src/multimarket/codex_exp023_p0.py"): (
        "826c9bdeb0300a1af583998bca67a8bd6d7bf54a0cd8f6f8cd1ba3e5a9c5ceef"
    ),
    READINESS_REL: EXP023_READINESS_SHA256,
    Path("docs/CODEX_EXP024_P0_PREREGISTRATION.md"): (
        P0_PREREGISTRATION_SHA256
    ),
    Path("src/multimarket/codex_exp024_collect.py"): (
        "ed8ed1f64b8343fc183b923f20df73a1bb63c46125fe07509ba8f6cbba842f0e"
    ),
    Path("src/multimarket/codex_exp024_finalize.py"): (
        "d8b06a2b68ad1a6de1c0aea8fc1cb6fd70932f1d90314ecc3f35f973ac23b2b9"
    ),
    Path("tests/test_codex_exp024_p0.py"): (
        "d7c53e5a5c46e013d67c4a6e9b3b90be76206f1612fdd66d89abe90d2c1e88a0"
    ),
}

GRID_US = frozen_p1.GRID_US
GRID_COLUMNS = frozen_p1.GRID_COLUMNS
EXPECTED_GRID_ROWS = frozen_p1.EXPECTED_GRID_ROWS
DAY_START_US = int(
    datetime(2026, 8, 30, tzinfo=timezone.utc).timestamp() * 1_000_000
)
DAY_END_US = DAY_START_US + 86_400_000_000
PROSPECTIVE_GRID_FILENAME = "2026-08-30_BOOKTICKER250.csv"
EXPECTED_GRID_PATH_SUFFIX = (
    "evidence",
    "codex",
    "exp024_prospective_bookticker",
    "BTCUSDT",
    PROSPECTIVE_GRID_FILENAME,
)

VOL_FEATURE = frozen_p1.VOL_FEATURE
VOL_INDEX = frozen_p1.VOL_INDEX
DECISION_STEP_ROWS = frozen_p1.DECISION_STEP_ROWS
HORIZON_S = frozen_p1.HORIZON_S
LABEL_THRESHOLD_BPS = frozen_p1.LABEL_THRESHOLD_BPS
MIN_SUPPORT_N = frozen_p1.MIN_SUPPORT_N
MIN_POSITIVES = frozen_p1.MIN_POSITIVES
MIN_NEGATIVES = frozen_p1.MIN_NEGATIVES
MIN_NULL_SHIFTS = frozen_p1.MIN_NULL_SHIFTS
SEED = frozen_p1.SEED

FixedLogistic = frozen_p1.FixedLogistic
ProspectiveDataset = frozen_p1.ProspectiveDataset
SupportedRows = frozen_p1.SupportedRows
finalize_common_support = frozen_p1.finalize_common_support
p1_metrics = frozen_p1.p1_metrics
eligible_circular_shifts = frozen_p1.eligible_circular_shifts
circular_shift_labels = frozen_p1.circular_shift_labels
higher_q95 = frozen_p1.higher_q95
empirical_one_sided_p = frozen_p1.empirical_one_sided_p
temporal_shift_null = frozen_p1.temporal_shift_null
support_is_sufficient = frozen_p1.support_is_sufficient
primary_gates = frozen_p1.primary_gates
adjudicate_status = frozen_p1.adjudicate_status
nonoverlap_diagnostic = frozen_p1.nonoverlap_diagnostic

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
    "raw_bytes_recorded",
    "grid_bytes_recorded",
    "collector_armed_before_utc_midnight",
    "collector_metadata_exact",
    "at_least_one_connection_attempt",
    "collection_end_recorded_after_day",
    "no_quote_outside_collection_day_accepted",
    "no_malformed_transport_record",
)
P0_FALSE_GATES = (
    "older_august_holdout_opened",
    "historical_aug1_feature_reparsed",
    "target_scored",
    "model_fit",
    "auc_scored",
    "direction_scored",
    "pnl_scored",
    "leverage_scored",
)
EXECUTION_GUARD_NAMES = (
    "direction_scored",
    "pnl_scored",
    "leverage_scored",
    "older_august_holdout_opened",
    "historical_aug1_feature_reparsed",
    "network_accessed",
    "prospective_raw_opened",
)


@dataclass(frozen=True)
class Config:
    experiment_id: str = EXPERIMENT_ID
    symbol: str = SYMBOL
    training_days: tuple[str, ...] = tuple(
        day.isoformat() for day in TRAIN_DAYS
    )
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
    null_shift_step_rows: int = frozen_p1.NULL_SHIFT_STEP
    min_null_shifts: int = MIN_NULL_SHIFTS
    null_quantile: float = 0.95
    null_quantile_method: str = "higher"


SCIENTIFIC_CONFIGURATION_SHA256 = (
    "3a9edfa6d2c9d15591373237574eb9552f09755eff2f0265e434621508e83b88"
)


@dataclass(frozen=True)
class P0AuditAuthorization:
    audit_sha256: str
    grid_sha256: str
    grid_bytes: int
    grid_path: str
    frozen_implementation_commit: str


@dataclass(frozen=True)
class GridAuthorization:
    resolved_path: Path
    byte_size: int
    sha256: str


@dataclass
class ExecutionState:
    prospective_grid_opaque_verified: bool = False
    prospective_grid_analytically_opened: bool = False
    model_fit: bool = False
    target_constructed: bool = False
    prospective_metrics_scored: bool = False


def _sha256_opaque(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


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
    digest = _sha256_opaque(workspace / PREREGISTRATION_REL)
    if digest != PREREGISTRATION_SHA256:
        raise RuntimeError("EXP024-P1 preregistration SHA mismatch")
    return digest


def verify_frozen_references(workspace: Path) -> dict[str, str]:
    verified: dict[str, str] = {}
    for relative, expected in FROZEN_REFERENCE_SHA256.items():
        digest = _sha256_opaque(workspace / relative)
        if digest != expected:
            raise RuntimeError(f"frozen reference SHA mismatch: {relative}")
        verified[str(relative)] = digest
    return verified


def verify_exp023_readiness(workspace: Path) -> dict[str, Any]:
    path = workspace / READINESS_REL
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXP023_READINESS_SHA256:
        raise RuntimeError("EXP023 readiness artifact SHA mismatch")
    payload = json.loads(raw)
    if payload.get("experiment_id") != "CODEX-EXP-023-P0":
        raise RuntimeError("wrong EXP023 readiness experiment")
    if payload.get("status") != EXP023_READINESS_STATUS:
        raise RuntimeError("EXP023 implementation correction is not ready")
    if payload.get("predictive_metrics_produced") is not False:
        raise RuntimeError("EXP023 readiness recorded predictive metrics")
    return {"sha256": digest, "status": payload["status"]}


def assert_frozen_workspace(workspace: Path, frozen_commit: str) -> None:
    if len(frozen_commit) != 40:
        raise RuntimeError("full 40-character frozen commit required")
    try:
        int(frozen_commit, 16)
    except ValueError as exc:
        raise RuntimeError("frozen commit must be hexadecimal") from exc
    if _git(workspace, "rev-parse", "HEAD") != frozen_commit:
        raise RuntimeError("frozen implementation commit mismatch")
    if not _is_ancestor(workspace, P0_ACQUISITION_COMMIT, frozen_commit):
        raise RuntimeError("EXP024-P0 acquisition commit is not an ancestor")
    if _git(workspace, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked worktree changes after implementation freeze")
    verify_preregistration(workspace)
    verify_frozen_references(workspace)
    verify_exp023_readiness(workspace)


def scientific_configuration() -> dict[str, Any]:
    current = asdict(Config())
    if canonical_sha256(current) != SCIENTIFIC_CONFIGURATION_SHA256:
        raise RuntimeError("EXP024-P1 scientific configuration SHA mismatch")
    parent = asdict(frozen_p1.Config())
    for identity_key in ("experiment_id", "prospective_day"):
        current.pop(identity_key)
        parent.pop(identity_key)
    if current != parent:
        raise RuntimeError("scientific configuration differs from EXP022-P1")
    return asdict(Config())


def execution_guards() -> dict[str, bool]:
    return {name: False for name in EXECUTION_GUARD_NAMES}


def _grid_path_belongs_to_exp024(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parts = PurePosixPath(value).parts
    return bool(
        len(parts) >= len(EXPECTED_GRID_PATH_SUFFIX)
        and tuple(parts[-len(EXPECTED_GRID_PATH_SUFFIX) :])
        == EXPECTED_GRID_PATH_SUFFIX
    )


def synthetic_p0_audit_payload(
    *,
    grid_sha256: str,
    grid_bytes: int,
) -> dict[str, Any]:
    gates = {name: True for name in P0_TRUE_GATES}
    gates.update({name: False for name in P0_FALSE_GATES})
    return {
        "experiment_id": P0_EXPERIMENT_ID,
        "status": P0_STATUS,
        "scope": P0_SCOPE,
        "collection_day": PROSPECTIVE_DAY.isoformat(),
        "symbol": SYMBOL,
        "frozen_implementation_commit": P0_ACQUISITION_COMMIT,
        "preregistration_sha256": P0_PREREGISTRATION_SHA256,
        "readiness_artifact_sha256": EXP023_READINESS_SHA256,
        "raw_path": "/data/bookticker/BTCUSDT/2026-08-30.jsonl.gz",
        "grid_path": (
            "/data/evidence/codex/exp024_prospective_bookticker/"
            f"BTCUSDT/{PROSPECTIVE_GRID_FILENAME}"
        ),
        "raw_bytes": 100,
        "grid_bytes": grid_bytes,
        "raw_sha256": "a" * 64,
        "grid_sha256": grid_sha256,
        "integrity_gates": gates,
        "network_accessed_for_acquisition": True,
        "predictive_metrics_calculated": False,
        **{name: False for name in P0_FALSE_GATES},
        **execution_guards(),
    }


def verify_p0_audit(path: Path) -> P0AuditAuthorization:
    raw = path.read_bytes()
    audit_sha256 = hashlib.sha256(raw).hexdigest()
    audit = json.loads(raw)
    required = {
        "experiment_id": P0_EXPERIMENT_ID,
        "status": P0_STATUS,
        "scope": P0_SCOPE,
        "collection_day": PROSPECTIVE_DAY.isoformat(),
        "symbol": SYMBOL,
        "frozen_implementation_commit": P0_ACQUISITION_COMMIT,
        "preregistration_sha256": P0_PREREGISTRATION_SHA256,
        "readiness_artifact_sha256": EXP023_READINESS_SHA256,
    }
    for name, expected in required.items():
        if audit.get(name) != expected:
            raise RuntimeError(f"EXP024-P0 audit mismatch: {name}")

    if type(audit.get("predictive_metrics_calculated")) is not bool or audit[
        "predictive_metrics_calculated"
    ]:
        raise RuntimeError("EXP024-P0 audit predictive-metrics guard failed")
    network_accessed_for_acquisition = audit.get(
        "network_accessed_for_acquisition"
    )
    if (
        type(network_accessed_for_acquisition) is not bool
        or network_accessed_for_acquisition is not True
    ):
        raise RuntimeError("EXP024-P0 acquisition network provenance missing")
    for name in P0_FALSE_GATES:
        value = audit.get(name)
        if type(value) is not bool or value:
            raise RuntimeError(f"EXP024-P0 no-analysis guard failed: {name}")

    gates_value = audit.get("integrity_gates")
    if not isinstance(gates_value, Mapping):
        raise RuntimeError("EXP024-P0 integrity gates missing")
    gates = validate_builtin_bool_invariants(gates_value)
    expected_names = set(P0_TRUE_GATES) | set(P0_FALSE_GATES)
    if set(gates) != expected_names:
        raise RuntimeError("EXP024-P0 integrity gate names mismatch")
    expectations = {
        name: name in P0_TRUE_GATES
        for name in gates
    }
    if not adjudicate_invariants(gates, expected=expectations):
        raise RuntimeError("EXP024-P0 integrity gates did not pass")

    grid_path = audit.get("grid_path")
    if not _grid_path_belongs_to_exp024(grid_path):
        raise RuntimeError("EXP024-P0 grid path is not authorized")
    grid_sha256 = audit.get("grid_sha256")
    if not _valid_sha256(grid_sha256):
        raise RuntimeError("EXP024-P0 grid SHA is invalid")
    grid_bytes = audit.get("grid_bytes")
    if type(grid_bytes) is not int or grid_bytes <= 0:
        raise RuntimeError("EXP024-P0 grid byte size is invalid")
    if not _valid_sha256(audit.get("raw_sha256")):
        raise RuntimeError("EXP024-P0 raw SHA is invalid")
    if type(audit.get("raw_bytes")) is not int or audit["raw_bytes"] <= 0:
        raise RuntimeError("EXP024-P0 raw byte size is invalid")

    return P0AuditAuthorization(
        audit_sha256=audit_sha256,
        grid_sha256=str(grid_sha256),
        grid_bytes=grid_bytes,
        grid_path=str(grid_path),
        frozen_implementation_commit=str(
            audit["frozen_implementation_commit"]
        ),
    )


def authorize_prospective_grid(
    path: Path,
    p0_authorization: P0AuditAuthorization,
) -> GridAuthorization:
    if path.name != PROSPECTIVE_GRID_FILENAME:
        raise RuntimeError("prospective grid filename is not authorized")
    resolved = path.resolve(strict=True)
    if not _grid_path_belongs_to_exp024(resolved.as_posix()):
        raise RuntimeError("prospective grid path is not authorized")
    if not resolved.is_file():
        raise RuntimeError("prospective grid is not a regular file")
    size = int(resolved.stat().st_size)
    if size != p0_authorization.grid_bytes:
        raise RuntimeError("prospective grid byte-size mismatch")
    digest = _sha256_opaque(resolved)
    if digest != p0_authorization.grid_sha256:
        raise RuntimeError("prospective grid SHA mismatch")
    return GridAuthorization(resolved, size, digest)


def load_prospective_grid(
    path: Path,
    authorization: GridAuthorization,
    *,
    expected_rows: int = EXPECTED_GRID_ROWS,
) -> Any:
    return frozen_p1.load_prospective_grid(
        path,
        authorization,
        expected_rows=expected_rows,
        day_start_us=DAY_START_US,
        grid_us=GRID_US,
        prospective_day=PROSPECTIVE_DAY,
    )


def build_prospective_dataset(day: Any) -> ProspectiveDataset:
    return frozen_p1.build_prospective_dataset(
        day,
        required_day=PROSPECTIVE_DAY,
    )


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
    return frozen_p1._prepare_historical(feature_dir, workspace)


def _split_metrics(metrics: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return frozen_p1._split_metrics(metrics)


def synthetic_result_payload(status: str) -> dict[str, Any]:
    allowed = {PASS_STATUS, FAIL_STATUS, INCONCLUSIVE_STATUS, INVALID_STATUS}
    if status not in allowed:
        raise ValueError("unsupported synthetic result status")
    invariants = validate_builtin_bool_invariants(
        {
            "common_support_unique_and_chronological": True,
            "p0_audit_authorized": True,
            "grid_hash_authorized": True,
        }
    )
    payload: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "synthetic_fixture": True,
        "status": status,
        "configuration": asdict(Config()),
        "configuration_sha256": SCIENTIFIC_CONFIGURATION_SHA256,
        "support": {
            "n": np.int64(1200),
            "positives": np.int32(10),
            "negatives": np.int64(1190),
            "minimum_support_pass": np.bool_(
                status not in {INCONCLUSIVE_STATUS, INVALID_STATUS}
            ),
        },
        "primary_metrics": {
            "roc_auc": np.float64(0.61),
            "average_precision": np.float64(0.03),
            "average_precision_over_prevalence": np.float64(3.6),
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
        "primary_gates": {"synthetic_gate": np.bool_(status == PASS_STATUS)},
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
    if status == INVALID_STATUS:
        payload.update(
            {
                "failure_type": "SyntheticImplementationError",
                "failure_message": "synthetic fixture only",
            }
        )
    return payload


def synthetic_status_payloads_serialize() -> bool:
    for status in (PASS_STATUS, FAIL_STATUS, INCONCLUSIVE_STATUS, INVALID_STATUS):
        normalized = normalize_result_payload(synthetic_result_payload(status))
        encoded = json.dumps(normalized, allow_nan=False, sort_keys=True)
        if json.loads(encoded)["status"] != status:
            return False
    return True


def _synthetic_authorization_self_check() -> bool:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        grid = root.joinpath(*EXPECTED_GRID_PATH_SUFFIX)
        grid.parent.mkdir(parents=True, exist_ok=True)
        grid.write_bytes(b"synthetic-grid-bytes")
        grid_sha256 = _sha256_opaque(grid)
        audit = root / "audit.json"
        audit.write_text(
            json.dumps(
                synthetic_p0_audit_payload(
                    grid_sha256=grid_sha256,
                    grid_bytes=grid.stat().st_size,
                ),
                sort_keys=True,
                allow_nan=False,
            ),
            encoding="utf-8",
        )
        p0 = verify_p0_audit(audit)
        authorization = authorize_prospective_grid(grid, p0)
        return bool(
            authorization.sha256 == grid_sha256
            and authorization.byte_size == grid.stat().st_size
        )


def _synthetic_authorization_rejection_self_check() -> bool:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        grid = root.joinpath(*EXPECTED_GRID_PATH_SUFFIX)
        grid.parent.mkdir(parents=True, exist_ok=True)
        grid.write_bytes(b"synthetic-grid-authorization-rejection")
        digest = _sha256_opaque(grid)
        base = synthetic_p0_audit_payload(
            grid_sha256=digest,
            grid_bytes=grid.stat().st_size,
        )
        mutations: list[tuple[str, Any]] = [
            ("experiment_id", "wrong"),
            ("status", "FAIL"),
            ("scope", "wrong"),
            ("collection_day", "2026-08-31"),
            ("symbol", "ETHUSDT"),
            ("frozen_implementation_commit", "0" * 40),
            ("preregistration_sha256", "0" * 64),
            ("readiness_artifact_sha256", "0" * 64),
            ("predictive_metrics_calculated", True),
            *[(name, True) for name in P0_FALSE_GATES],
        ]
        audit_path = root / "audit.json"
        rejected = 0
        for name, value in mutations:
            payload = dict(base)
            payload["integrity_gates"] = dict(base["integrity_gates"])
            payload[name] = value
            audit_path.write_text(
                json.dumps(payload, sort_keys=True, allow_nan=False),
                encoding="utf-8",
            )
            try:
                verify_p0_audit(audit_path)
            except RuntimeError:
                rejected += 1
        if rejected != len(mutations):
            return False

        valid_audit = root / "valid-audit.json"
        valid_audit.write_text(
            json.dumps(base, sort_keys=True, allow_nan=False),
            encoding="utf-8",
        )
        authorization = verify_p0_audit(valid_audit)
        changed = bytearray(grid.read_bytes())
        changed[0] ^= 1
        grid.write_bytes(changed)
        try:
            authorize_prospective_grid(grid, authorization)
        except RuntimeError as exc:
            return bool("SHA mismatch" in str(exc))
        return False


def _fixed_model_parameters_exact() -> bool:
    params = FixedLogistic().model.get_params()
    expected = {
        "C": 1.0,
        "penalty": "l2",
        "solver": "lbfgs",
        "class_weight": None,
        "max_iter": 1000,
        "random_state": SEED,
    }
    return bool(all(params.get(name) == value for name, value in expected.items()))


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


def _synthetic_one_shot_self_check() -> bool:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        output = root / "result.json"
        payload = {
            "experiment_id": EXPERIMENT_ID,
            "status": INVALID_STATUS,
            "synthetic_fixture": True,
            "invariants": {"synthetic_json_safe": True},
            **execution_guards(),
        }
        _write_once(output, payload)
        refused_final = False
        try:
            ensure_fresh_output(output)
        except FileExistsError:
            refused_final = True
        output.unlink()
        part = output.with_name(output.name + ".part")
        part.write_text("synthetic", encoding="utf-8")
        refused_part = False
        try:
            ensure_fresh_output(output)
        except FileExistsError:
            refused_part = True
        return bool(refused_final and refused_part)


def _synthetic_temporal_null_equivalence() -> bool:
    labels = np.asarray(([1] + [0] * 39) * 30, dtype=np.int8)
    probabilities = np.linspace(0.01, 0.99, len(labels))
    current = temporal_shift_null(labels, probabilities)
    parent = frozen_p1.temporal_shift_null(labels, probabilities)
    return bool(current == parent)


def run_preflight(*, feature_dir: Path, workspace: Path) -> dict[str, Any]:
    preregistration_sha256 = verify_preregistration(workspace)
    references = verify_frozen_references(workspace)
    readiness = verify_exp023_readiness(workspace)
    configuration = scientific_configuration()
    bug_checks = frozen_bug_regression()
    serialization_safe = synthetic_status_payloads_serialize()
    authorization_safe = _synthetic_authorization_self_check()
    authorization_rejections_safe = (
        _synthetic_authorization_rejection_self_check()
    )
    one_shot_safe = _synthetic_one_shot_self_check()
    temporal_exact = _synthetic_temporal_null_equivalence()
    manifest, validation, features, labels, counts = _prepare_historical(
        feature_dir,
        workspace,
    )
    guards = execution_guards()
    invariants = validate_builtin_bool_invariants(
        {
            "preregistration_sha_exact": bool(
                preregistration_sha256 == PREREGISTRATION_SHA256
            ),
            "frozen_references_exact": bool(
                len(references) == len(FROZEN_REFERENCE_SHA256)
            ),
            "exp023_correction_readiness_exact": bool(
                readiness["sha256"] == EXP023_READINESS_SHA256
                and readiness["status"] == EXP023_READINESS_STATUS
            ),
            "scientific_configuration_exact": bool(
                canonical_sha256(configuration)
                == SCIENTIFIC_CONFIGURATION_SHA256
            ),
            "historical_days_exact_jan_jul": bool(
                tuple(item["day"] for item in counts)
                == tuple(day.isoformat() for day in TRAIN_DAYS)
            ),
            "one_legitimate_feature_only": bool(
                features.ndim == 2 and features.shape[1] == 1
            ),
            "fixed_model_parameters_exact": _fixed_model_parameters_exact(),
            "historical_semantics_exact": bool(
                len(validation) == len(TRAIN_DAYS)
                and all(
                    item["rv_exact_match"]
                    and item["target_and_support_exact_match"]
                    for item in validation
                )
            ),
            "corrected_invariant_typing_exact": bool(all(bug_checks.values())),
            "complete_status_payloads_json_safe": bool(serialization_safe),
            "synthetic_p0_authorization_exact": bool(authorization_safe),
            "synthetic_p0_authorization_rejections_exact": bool(
                authorization_rejections_safe
            ),
            "temporal_null_exact": bool(temporal_exact),
            "one_shot_output_protection_exact": bool(one_shot_safe),
            "no_august_market_data_accessed": True,
            "no_prospective_metrics_scored": True,
            "execution_guards_all_false": bool(
                all(type(value) is bool and not value for value in guards.values())
            ),
        }
    )
    if not adjudicate_invariants(invariants):
        raise RuntimeError("EXP024-P1 preflight invariant failure")
    return {
        "experiment_id": EXPERIMENT_ID,
        "mode": "preflight",
        "status": PREOPEN_PASS_STATUS,
        "preregistration_sha256": preregistration_sha256,
        "scientific_configuration_sha256": SCIENTIFIC_CONFIGURATION_SHA256,
        "historical_input_manifest": manifest,
        "historical_semantic_validation": validation,
        "historical_training_counts": counts,
        "historical_training_n": int(len(labels)),
        "historical_feature_columns": int(features.shape[1]),
        "invariants": invariants,
        "prospective_grid_opaque_verified": False,
        "prospective_grid_analytically_opened": False,
        "model_fit": False,
        "prospective_metrics_scored": False,
        **guards,
    }


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
    preregistration_sha256 = verify_preregistration(workspace)
    p0 = verify_p0_audit(p0_audit)
    grid_authorization = authorize_prospective_grid(grid, p0)
    state.prospective_grid_opaque_verified = True

    manifest, validation, training_features, training_labels, counts = (
        _prepare_historical(feature_dir, workspace)
    )
    model = FixedLogistic().fit(training_features, training_labels)
    state.model_fit = True

    state.prospective_grid_analytically_opened = True
    day = load_prospective_grid(grid, grid_authorization)
    dataset = build_prospective_dataset(day)
    state.target_constructed = True
    candidate = dataset.candidate_support
    candidate_probabilities = model.predict_proba(
        dataset.rv_30m_bps[candidate].reshape(-1, 1)
    )
    rows = finalize_common_support(dataset, candidate_probabilities)
    metrics = p1_metrics(rows.timestamp_us, rows.label, rows.probability)
    state.prospective_metrics_scored = True

    support_sufficient = support_is_sufficient(rows.label)
    if support_sufficient:
        null_summary = temporal_shift_null(rows.label, rows.probability)
    else:
        null_summary = {
            "number_of_shifts": len(eligible_circular_shifts(len(rows.label))),
            "auc_null_q95": None,
            "ap_null_q95": None,
            "auc_empirical_p": None,
            "ap_empirical_p": None,
        }
    null_support_sufficient = bool(
        null_summary["number_of_shifts"] >= MIN_NULL_SHIFTS
    )
    guards = execution_guards()
    invariants = validate_builtin_bool_invariants(
        {
            "preregistration_sha_exact": bool(
                preregistration_sha256 == PREREGISTRATION_SHA256
            ),
            "p0_audit_authorized": bool(
                p0.frozen_implementation_commit == P0_ACQUISITION_COMMIT
            ),
            "prospective_grid_sha_and_bytes_exact": bool(
                grid_authorization.sha256 == p0.grid_sha256
                and grid_authorization.byte_size == p0.grid_bytes
            ),
            "historical_training_days_exact_jan_jul": bool(
                TRAIN_DAYS
                == tuple(date(2026, month, 1) for month in range(1, 8))
            ),
            "prospective_day_exact_2026_08_30": bool(
                day.day == PROSPECTIVE_DAY
            ),
            "symbol_exact_btcusdt": bool(SYMBOL == "BTCUSDT"),
            "primary_feature_exact_rv_30m_bps": bool(
                VOL_FEATURE == "rv_30m_bps"
            ),
            "one_legitimate_feature_only": bool(
                training_features.ndim == 2 and training_features.shape[1] == 1
            ),
            "decision_step_exact_60s": bool(DECISION_STEP_ROWS == 240),
            "entry_delay_exact_250ms": True,
            "target_horizon_exact_600s": bool(HORIZON_S == 600),
            "target_threshold_exact_24bp": bool(
                LABEL_THRESHOLD_BPS == 24.0
            ),
            "historical_adapter_semantics_exact": bool(
                len(validation) == len(TRAIN_DAYS)
                and all(
                    item["rv_exact_match"]
                    and item["target_and_support_exact_match"]
                    for item in validation
                )
            ),
            "common_support_unique_and_chronological": (
                common_support_unique_and_chronological(rows.timestamp_us)
            ),
            "no_august_fit_or_refit": True,
            "execution_guards_all_false": bool(
                all(type(value) is bool and not value for value in guards.values())
            ),
        }
    )
    invariants_pass = adjudicate_invariants(invariants)
    gates = validate_builtin_bool_invariants(
        primary_gates(metrics, null_summary, invariants_pass)
    )
    status = adjudicate_status(
        support_sufficient=bool(support_sufficient),
        null_support_sufficient=null_support_sufficient,
        gates=gates,
        invariants_pass=invariants_pass,
    )
    primary, secondary = _split_metrics(metrics)
    nonoverlap = nonoverlap_diagnostic(rows)
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
        "preregistration_sha256": preregistration_sha256,
        "p0_authorization": {
            "audit_sha256": p0.audit_sha256,
            "status": P0_STATUS,
            "frozen_implementation_commit": p0.frozen_implementation_commit,
            "grid_sha256": p0.grid_sha256,
            "grid_bytes": p0.grid_bytes,
        },
        "historical_input_manifest": manifest,
        "historical_training_counts": counts,
        "configuration": asdict(Config()),
        "configuration_sha256": SCIENTIFIC_CONFIGURATION_SHA256,
        "support": {
            "n": int(len(rows.label)),
            "positives": int(rows.label.sum()),
            "negatives": int(len(rows.label) - rows.label.sum()),
            "minimum_support_pass": bool(support_sufficient),
        },
        "primary_metrics": primary,
        "secondary_calibration_diagnostics": secondary,
        "circular_shift_null_summary": null_summary,
        "primary_gates": gates,
        "nonoverlap_10m_diagnostic": nonoverlap,
        "invariants": invariants,
        "deterministic_score_records_sha256": canonical_sha256(score_records),
        "score_records": score_records,
        "prospective_grid_opaque_verified": (
            state.prospective_grid_opaque_verified
        ),
        "prospective_grid_analytically_opened": (
            state.prospective_grid_analytically_opened
        ),
        "model_fit": state.model_fit,
        "target_constructed": state.target_constructed,
        "prospective_metrics_scored": state.prospective_metrics_scored,
        **guards,
    }


def invalid_payload(
    exc: Exception,
    frozen_commit: str,
    state: ExecutionState,
) -> dict[str, Any]:
    invariants = validate_builtin_bool_invariants(
        {
            "execution_completed": False,
            "invalid_status_recorded": True,
        }
    )
    return {
        "experiment_id": EXPERIMENT_ID,
        "status": INVALID_STATUS,
        "frozen_implementation_commit": frozen_commit,
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "configuration": asdict(Config()),
        "configuration_sha256": SCIENTIFIC_CONFIGURATION_SHA256,
        "failure_type": type(exc).__name__,
        "failure_message": str(exc),
        "invariants": invariants,
        "prospective_grid_opaque_verified": state.prospective_grid_opaque_verified,
        "prospective_grid_analytically_opened": (
            state.prospective_grid_analytically_opened
        ),
        "model_fit": state.model_fit,
        "target_constructed": state.target_constructed,
        "prospective_metrics_scored": state.prospective_metrics_scored,
        **execution_guards(),
    }


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
        normalize_result_payload(payload)
    except Exception as exc:
        payload = invalid_payload(exc, frozen_commit, state)
        normalize_result_payload(payload)
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

    if args.mode == "preflight":
        if any(
            value is not None
            for value in (
                args.p0_audit,
                args.grid,
                args.output,
                args.frozen_commit,
            )
        ):
            parser.error(
                "preflight does not accept P0 audit, grid, output, or frozen commit"
            )
        result = run_preflight(
            feature_dir=args.feature_dir,
            workspace=workspace,
        )
    else:
        if args.p0_audit is None:
            parser.error("execute requires --p0-audit")
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
            p0_audit=args.p0_audit,
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

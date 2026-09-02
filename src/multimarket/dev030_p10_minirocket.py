"""Nested DEV030-P10 MiniRocket analytical runner.

Implementation only. The canonical Jan-Jul campaign remains separately gated.

P10 preserves the frozen P3/P8/P9 direction-given-touch baseline and replaces
only the temporal representation: one deterministic MiniRocket-style transform
of the same three 32-second PRICE channels. Transform parameters are fitted
inside each chronological training split to prevent validation leakage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import sklearn
from sklearn.preprocessing import StandardScaler

from . import dev030_direction_dataset as dd
from . import dev030_p9_price_dense_sequence as p9
from . import dev030_p10_minirocket_transform as mr


EXPERIMENT_ID = "DEV030-P10"
DESIGN_VERSION = "price-minirocket-multivariate-linear-v1"

SELECTED_TARGET = p9.SELECTED_TARGET
SELECTED_WINDOW_SECONDS = p9.SELECTED_WINDOW_SECONDS
SELECTED_BLOCK = p9.SELECTED_BLOCK

EXPECTED_BASELINE_FEATURE_COUNT = 23
EXPECTED_TRANSFORM_FEATURE_COUNT = 9_996
EXPECTED_AUGMENTED_FEATURE_COUNT = 10_019

EXPECTED_POOLED_SUPPORT = p9.EXPECTED_POOLED_SUPPORT
EXPECTED_POOLED_LONG = p9.EXPECTED_POOLED_LONG
EXPECTED_POOLED_SHORT = p9.EXPECTED_POOLED_SHORT
EXPECTED_FOLD_SUPPORT = p9.EXPECTED_FOLD_SUPPORT
EXPECTED_FOLD_LONG = p9.EXPECTED_FOLD_LONG
EXPECTED_FOLD_SHORT = p9.EXPECTED_FOLD_SHORT

P9_ARTIFACT_PATH = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p9_price_dense_sequence_v1/"
    "DEV030_P9_PRICE_DENSE_SEQUENCE_RESULT.json"
)
P9_ARTIFACT_SHA256 = (
    "2f1913b3ac80df5cb0dd01dc7001c333983d22e6a8514346f9cee57a3333b9dc"
)
P9_TERMINAL_STATUS = "FAIL_PRICE_DENSE_SEQUENCE_NO_STABLE_INCREMENTAL_VALUE"

P10_TRANSFORM_SOURCE_REL = "src/multimarket/dev030_p10_minirocket_transform.py"
P10_TRANSFORM_SOURCE_SHA256 = (
    "56071d2cde4a189b5e1d6711aff16139c315618192e13d13d38374a9a91f384f"
)
P9_SOURCE_REL = "src/multimarket/dev030_p9_price_dense_sequence.py"
P9_SOURCE_SHA256 = (
    "0be4fa90366dfb33a08669a367efe427239b6ee8a32378d269b84e69e2c36228"
)

REAL_OUTPUT_DIRECTORY = Path(
    "/home/emadh/Multi-Market/evidence/dev030_p10_price_minirocket_v1"
)
ARTIFACT_FILENAME = "DEV030_P10_PRICE_MINIROCKET_RESULT.json"

P10_C1_PREDICTION_HASH_DOMAIN = b"DEV030-P10-OOF-PREDICTION-V1\x00"

FORWARD_GUARDS = {
    "aug30_analytically_opened": False,
    "sep01_or_later_analytically_opened": False,
    "archive_bucket_opened": False,
    "abundant_love_opened": False,
}


class P10Error(RuntimeError):
    """Frozen P10 protocol, implementation, or output violation."""

    def __init__(self, reason: str, detail: str | None = None) -> None:
        self.reason = str(reason)
        super().__init__(self.reason if detail is None else f"{self.reason}: {detail}")


@dataclass(frozen=True)
class P10Day:
    day: date
    timestamps_us: np.ndarray
    labels: np.ndarray
    c0_values: np.ndarray
    sequence_values: np.ndarray
    support_sha256: str
    label_sha256: str


@dataclass(frozen=True)
class FoldTransformLedger:
    fold_id: int
    inner_parameter_sha256: str
    outer_parameter_sha256: str
    inner_fit_support: int
    inner_validation_support: int
    outer_train_support: int
    outer_validation_support: int


@dataclass(frozen=True)
class ArtifactWriteResult:
    output_directory: Path
    artifact_path: Path
    artifact_sha256: str
    artifact_bytes: int


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_frozen_dependencies(workspace: Path) -> dict[str, str]:
    """Verify inherited P9 dependencies plus frozen P9/transform source identity."""
    root = Path(workspace)
    try:
        inherited = dict(p9.verify_frozen_dependencies(root))
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc

    required = {
        P9_SOURCE_REL: P9_SOURCE_SHA256,
        P10_TRANSFORM_SOURCE_REL: P10_TRANSFORM_SOURCE_SHA256,
    }
    for rel, expected in required.items():
        path = root / rel
        if not path.is_file():
            raise P10Error("frozen_dependency_missing", rel)
        actual = _sha256_file(path)
        if actual != expected:
            raise P10Error(
                "frozen_dependency_sha_mismatch",
                f"{rel}: expected={expected} actual={actual}",
            )
        inherited[rel] = actual
    return dict(sorted(inherited.items()))


def load_verified_json_artifact(path: Path, expected_sha256: str) -> dict[str, Any]:
    try:
        return p9.load_verified_json_artifact(path, expected_sha256)
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc


def validate_prior_artifacts(
    p3_payload: Mapping[str, Any],
    p4_payload: Mapping[str, Any],
    p5_payload: Mapping[str, Any],
    p6_payload: Mapping[str, Any],
    p7_payload: Mapping[str, Any],
    p8_payload: Mapping[str, Any],
    p9_payload: Mapping[str, Any],
) -> None:
    try:
        p9.validate_prior_artifacts(
            p3_payload,
            p4_payload,
            p5_payload,
            p6_payload,
            p7_payload,
        )
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc

    if p8_payload.get("status") != (
        "FAIL_PRICE_TEMPORAL_SHAPE_NO_STABLE_INCREMENTAL_VALUE"
    ):
        raise P10Error("p8_terminal_status_mismatch")
    if p9_payload.get("status") != P9_TERMINAL_STATUS:
        raise P10Error("p9_terminal_status_mismatch")
    if p9_payload.get(
        "eligible_price_dense_sequence_incremental_information"
    ) is not False:
        raise P10Error("p9_eligibility_state_mismatch")


def extract_sequence_tensor(
    sequence_input: Any,
    decision_timestamps_us: Any,
) -> np.ndarray:
    """Reuse frozen P9 exact sequence extraction and reshape to [N,3,32]."""
    try:
        flat = p9.extract_dense_sequence_matrix(
            sequence_input,
            decision_timestamps_us,
        )
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc

    array = np.asarray(flat, dtype=np.float64)
    expected = (
        len(np.asarray(decision_timestamps_us)),
        mr.EXPECTED_CHANNELS * mr.EXPECTED_TIMEPOINTS,
    )
    if array.shape != expected:
        raise P10Error(
            "sequence_flat_shape_mismatch",
            f"expected={expected} actual={array.shape}",
        )
    tensor = array.reshape(
        len(array),
        mr.EXPECTED_CHANNELS,
        mr.EXPECTED_TIMEPOINTS,
    ).astype(np.float32)
    if not bool(np.all(np.isfinite(tensor))):
        raise P10Error("sequence_non_finite")
    return np.ascontiguousarray(tensor, dtype=np.float32)


def build_p10_day(
    candidate: dd.CandidateDayDataset,
    sequence_input: Any,
) -> P10Day:
    try:
        p9.validate_candidate(candidate)
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc

    mask = np.asarray(candidate.t1_common_valid, dtype=bool)
    ts = np.asarray(candidate.decision_timestamps_us, dtype=np.int64)[mask]
    y = np.asarray(candidate.t1_labels, dtype=np.int8)[mask]
    x0 = np.asarray(candidate.s1_values, dtype=np.float64)[mask]
    if len(ts) == 0:
        raise P10Error("support_empty")
    if x0.shape != (len(ts), EXPECTED_BASELINE_FEATURE_COUNT):
        raise P10Error("baseline_shape_mismatch")
    if not bool(np.all(np.isfinite(x0))):
        raise P10Error("baseline_non_finite")

    sequence = extract_sequence_tensor(sequence_input, ts)
    if sequence.shape != (len(ts), 3, 32):
        raise P10Error("sequence_tensor_shape_mismatch")
    if len(sequence) != int(np.count_nonzero(mask)):
        raise P10Error("sequence_support_shrink")

    return P10Day(
        day=candidate.day,
        timestamps_us=ts,
        labels=y,
        c0_values=x0,
        sequence_values=sequence,
        support_sha256=dd.support_sha256(ts),
        label_sha256=p9.label_sha256(ts, y),
    )


def _stack_days(
    per_day: Mapping[date, P10Day],
    days: Sequence[date],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    chunks = [per_day[day] for day in days]
    x0 = np.concatenate([item.c0_values for item in chunks], axis=0)
    seq = np.concatenate([item.sequence_values for item in chunks], axis=0)
    y = np.concatenate([item.labels for item in chunks]).astype(np.int8, copy=False)
    ts = np.concatenate([item.timestamps_us for item in chunks]).astype(
        np.int64, copy=False
    )
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P10Error("stacked_timestamps_not_chronological")
    return x0, seq, y, ts


def _as_p9_c0_days(
    per_day: Mapping[date, P10Day],
) -> dict[date, p9.DenseDay]:
    result: dict[date, p9.DenseDay] = {}
    for day in dd.HISTORICAL_DAYS:
        item = per_day[day]
        result[day] = p9.DenseDay(
            day=day,
            timestamps_us=item.timestamps_us,
            labels=item.labels,
            c0_values=item.c0_values,
            c1_values=item.c0_values,
            c0_feature_names=p9.BASELINE_FEATURE_NAMES,
            c1_feature_names=p9.BASELINE_FEATURE_NAMES,
            support_sha256=item.support_sha256,
            label_sha256=item.label_sha256,
        )
    return result


def fit_c0_exact(
    per_day: Mapping[date, P10Day],
    p8_payload: Mapping[str, Any],
) -> p9.RepresentationResult:
    """Fit exact inherited C0 and require byte-level P8 reproduction."""
    try:
        result = p9.fit_representation(_as_p9_c0_days(per_day), "C0")
        p9.validate_exact_p8_c0_reproduction(result, p8_payload)
        p9.validate_expected_p3_support(result)
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc
    return result


def c1_prediction_sha256(
    *,
    fold_id: int,
    timestamps_us: Any,
    y_true: Any,
    p_long: Any,
) -> str:
    ts = np.asarray(timestamps_us, dtype=np.int64)
    y = np.asarray(y_true, dtype=np.int8)
    p = np.asarray(p_long, dtype=np.float64)
    if not (ts.ndim == y.ndim == p.ndim == 1):
        raise P10Error("prediction_hash_shape_mismatch")
    if not (len(ts) == len(y) == len(p)):
        raise P10Error("prediction_hash_length_mismatch")
    if len(ts) and bool(np.any(np.diff(ts) <= 0)):
        raise P10Error("prediction_hash_timestamps_not_chronological")
    if not bool(np.all(np.isin(y, (0, 1)))):
        raise P10Error("prediction_hash_labels_invalid")
    if not bool(np.all(np.isfinite(p))) or not bool(
        np.all((p >= 0.0) & (p <= 1.0))
    ):
        raise P10Error("prediction_hash_probabilities_invalid")

    digest = hashlib.sha256()
    digest.update(P10_C1_PREDICTION_HASH_DOMAIN)
    digest.update(f"{int(fold_id)}|C1".encode("ascii"))
    for timestamp, label, probability in zip(
        ts.tolist(), y.tolist(), p.tolist(), strict=True
    ):
        digest.update(
            struct.pack(">qbd", int(timestamp), int(label), float(probability))
        )
    return digest.hexdigest()


def _augment(
    x0: np.ndarray,
    transformed: np.ndarray,
) -> np.ndarray:
    left = np.asarray(x0, dtype=np.float64)
    right = np.asarray(transformed, dtype=np.float32)
    if right.ndim != 2 or right.shape[1] != EXPECTED_TRANSFORM_FEATURE_COUNT:
        raise P10Error("transform_feature_shape_mismatch")
    if len(left) != len(right):
        raise P10Error("augment_length_mismatch")
    result = np.column_stack((left, right.astype(np.float64)))
    if result.shape != (len(left), EXPECTED_AUGMENTED_FEATURE_COUNT):
        raise P10Error("augmented_feature_shape_mismatch")
    if not bool(np.all(np.isfinite(result))):
        raise P10Error("augmented_non_finite")
    return result


def fit_c1_fold(
    *,
    fold: dd.FrozenOuterFold,
    per_day: Mapping[date, P10Day],
) -> tuple[p9.FoldResult, FoldTransformLedger]:
    """Fit C1 with transform parameters strictly nested inside chronology."""
    inner_validation_day = fold.train_days[-1]
    inner_fit_days = fold.train_days[:-1]
    if not inner_fit_days:
        raise P10Error("inner_fit_empty")

    x0_if, seq_if, y_if, _ = _stack_days(per_day, inner_fit_days)
    x0_iv, seq_iv, y_iv, _ = _stack_days(
        per_day, (inner_validation_day,)
    )

    try:
        inner_params = mr.fit(seq_if)
        z_if = mr.transform(seq_if, inner_params)
        z_iv = mr.transform(seq_iv, inner_params)
    except mr.P10TransformError as exc:
        raise P10Error(exc.reason, str(exc)) from exc

    x_if = _augment(x0_if, z_if)
    x_iv = _augment(x0_iv, z_iv)

    try:
        selected_c, ledger = p9.select_c_probability_first(
            x_if, y_if, x_iv, y_iv
        )
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc

    x0_train, seq_train, y_train, _ = _stack_days(
        per_day, fold.train_days
    )
    x0_val, seq_val, y_val, ts_val = _stack_days(
        per_day, (fold.validation_day,)
    )

    try:
        outer_params = mr.fit(seq_train)
        z_train = mr.transform(seq_train, outer_params)
        z_val = mr.transform(seq_val, outer_params)
    except mr.P10TransformError as exc:
        raise P10Error(exc.reason, str(exc)) from exc

    x_train = _augment(x0_train, z_train)
    x_val = _augment(x0_val, z_val)

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_val_scaled = scaler.transform(x_val)
    try:
        model = p9._new_logistic(selected_c)
        model.fit(x_train_scaled, y_train)
        p_long = model.predict_proba(x_val_scaled)[:, 1]
        pred = (p_long >= p9.THRESHOLD).astype(np.int8)
        metrics = p9.probability_metrics(y_val, p_long)
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc

    fold_result = p9.FoldResult(
        fold_id=int(fold.fold_id),
        representation="C1",
        selected_c=float(selected_c),
        support=int(len(y_val)),
        long_count=int(np.count_nonzero(y_val == 1)),
        short_count=int(np.count_nonzero(y_val == 0)),
        metrics=metrics,
        timestamps_us=ts_val,
        y_true=y_val,
        p_long=p_long,
        y_pred=pred,
        prediction_sha256=c1_prediction_sha256(
            fold_id=fold.fold_id,
            timestamps_us=ts_val,
            y_true=y_val,
            p_long=p_long,
        ),
        support_sha256=dd.support_sha256(ts_val),
        label_sha256=p9.label_sha256(ts_val, y_val),
        inner_c_ledger=ledger,
        scaler=scaler,
        model=model,
    )
    transform_ledger = FoldTransformLedger(
        fold_id=int(fold.fold_id),
        inner_parameter_sha256=mr.parameter_sha256(inner_params),
        outer_parameter_sha256=mr.parameter_sha256(outer_params),
        inner_fit_support=int(len(y_if)),
        inner_validation_support=int(len(y_iv)),
        outer_train_support=int(len(y_train)),
        outer_validation_support=int(len(y_val)),
    )
    return fold_result, transform_ledger


def fit_c1(
    per_day: Mapping[date, P10Day],
) -> tuple[p9.RepresentationResult, tuple[FoldTransformLedger, ...]]:
    if tuple(per_day) != dd.HISTORICAL_DAYS:
        raise P10Error("p10_day_order_mismatch")

    fitted = tuple(
        fit_c1_fold(fold=fold, per_day=per_day)
        for fold in dd.OUTER_FOLDS
    )
    folds = tuple(item[0] for item in fitted)
    ledgers = tuple(item[1] for item in fitted)

    y = np.concatenate([fold.y_true for fold in folds])
    p = np.concatenate([fold.p_long for fold in folds])
    ts = np.concatenate([fold.timestamps_us for fold in folds])
    result = p9.RepresentationResult(
        representation="C1",
        folds=folds,
        pooled_metrics=p9.probability_metrics(y, p),
        pooled_support_sha256=dd.support_sha256(ts),
        pooled_label_sha256=p9.label_sha256(ts, y),
    )
    try:
        p9.validate_expected_p3_support(result)
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc
    return result, ledgers


def comparison_summary(
    c0: p9.RepresentationResult,
    c1: p9.RepresentationResult,
) -> dict[str, Any]:
    try:
        result = dict(
            p9.comparison_summary(c0, c1, invariants_pass=True)
        )
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc

    gates = dict(result["precheck_gates"])
    gates["pooled_balanced_accuracy_no_regression"] = (
        float(c1.pooled_metrics["balanced_accuracy_at_0_5"])
        >= float(c0.pooled_metrics["balanced_accuracy_at_0_5"])
    )
    gates["pooled_macro_f1_no_regression"] = (
        float(c1.pooled_metrics["macro_f1_at_0_5"])
        >= float(c0.pooled_metrics["macro_f1_at_0_5"])
    )
    result["precheck_gates"] = gates
    result["precheck_pass"] = all(gates.values())
    return result


def final_gates(
    comparison: Mapping[str, Any],
    null: p9.PairedTemporalNull | None,
) -> dict[str, bool]:
    try:
        return p9.final_gates(comparison, null)
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc


def validate_matched_support(
    c0: p9.RepresentationResult,
    c1: p9.RepresentationResult,
) -> None:
    try:
        p9.validate_matched_support(c0, c1)
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc


def _fold_public(fold: p9.FoldResult) -> dict[str, Any]:
    return {
        "fold_id": fold.fold_id,
        "representation": fold.representation,
        "selected_C": fold.selected_c,
        "support": fold.support,
        "long_count": fold.long_count,
        "short_count": fold.short_count,
        "metrics": fold.metrics,
        "prediction_sha256": fold.prediction_sha256,
        "support_sha256": fold.support_sha256,
        "label_sha256": fold.label_sha256,
        "inner_c_ledger": [dict(item) for item in fold.inner_c_ledger],
    }


def _ledger_public(item: FoldTransformLedger) -> dict[str, Any]:
    return {
        "fold_id": item.fold_id,
        "inner_parameter_sha256": item.inner_parameter_sha256,
        "outer_parameter_sha256": item.outer_parameter_sha256,
        "inner_fit_support": item.inner_fit_support,
        "inner_validation_support": item.inner_validation_support,
        "outer_train_support": item.outer_train_support,
        "outer_validation_support": item.outer_validation_support,
    }


def runtime_provenance(*, model_fit_run: bool, p10_run: bool) -> dict[str, Any]:
    if type(model_fit_run) is not bool or type(p10_run) is not bool:
        raise P10Error("runtime_flags_must_be_builtin_bool")
    if p10_run and not model_fit_run:
        raise P10Error("p10_requires_model_fit")
    return {
        "jan_jul_analytically_opened": bool(p10_run),
        "authorized_development_data": {
            "scope": "BTCUSDT consumed Jan-Jul development days only",
            "analytically_loaded": bool(p10_run),
        },
        "forward_data_guards": dict(FORWARD_GUARDS),
        "model_fit_run": model_fit_run,
        "p10_run": p10_run,
        "threshold_optimization_run": False,
        "pnl_backtest_run": False,
        "opportunity_gate_run": False,
        "alternate_model_family_run": False,
        "deep_model_run": False,
        "lag_search_run": False,
        "feature_family_search_run": False,
        "kernel_count_search_run": False,
        "seed_search_run": False,
        "class_weighting_or_resampling_run": False,
        "calibration_run": False,
    }


def _validate_execution_commit(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise P10Error("execution_commit_must_be_full_sha")
    return value


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _output_preflight(output_directory: Path) -> None:
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise P10Error("output_directory_already_exists")
    parent = output.parent
    if not parent.is_dir():
        raise P10Error("output_parent_missing")
    probe = parent / f".{output.name}.preflight"
    if probe.exists() or probe.is_symlink():
        raise P10Error("output_probe_preexists")
    try:
        with probe.open("xb") as handle:
            handle.write(b"DEV030-P10 preflight\n")
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(parent)
        probe.unlink()
        _fsync_directory(parent)
    except OSError as exc:
        try:
            if probe.exists():
                probe.unlink()
                _fsync_directory(parent)
        except OSError as cleanup_exc:
            raise P10Error(
                "output_probe_cleanup_failed", str(cleanup_exc)
            ) from cleanup_exc
        raise P10Error(
            "output_parent_preflight_failed", str(exc)
        ) from exc


def write_result_once(
    output_directory: Path,
    payload: Mapping[str, Any],
    *,
    require_canonical_output: bool = True,
) -> ArtifactWriteResult:
    output = Path(output_directory)
    if output.exists() or output.is_symlink():
        raise P10Error("output_directory_already_exists")
    if require_canonical_output and output != REAL_OUTPUT_DIRECTORY:
        raise P10Error("noncanonical_output_directory")
    if not require_canonical_output and output == REAL_OUTPUT_DIRECTORY:
        raise P10Error("canonical_output_requires_real_mode")

    content = canonical_json_bytes(payload)
    output.mkdir(mode=0o755)
    _fsync_directory(output.parent)
    final = output / ARTIFACT_FILENAME
    part = final.with_name(final.name + ".part")
    try:
        with part.open("xb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(part, final)
        _fsync_directory(output)
    except BaseException as exc:
        if final.exists():
            raise P10Error(
                "artifact_directory_fsync_failed", str(exc)
            ) from exc
        try:
            if part.exists():
                part.unlink()
            if output.exists() and not any(output.iterdir()):
                output.rmdir()
        except OSError as cleanup_exc:
            raise P10Error(
                "artifact_cleanup_failed", str(cleanup_exc)
            ) from cleanup_exc
        if isinstance(exc, P10Error):
            raise
        raise P10Error("artifact_write_failed", str(exc)) from exc

    return ArtifactWriteResult(
        output_directory=output,
        artifact_path=final,
        artifact_sha256=hashlib.sha256(content).hexdigest(),
        artifact_bytes=len(content),
    )


def run_p10(
    *,
    workspace: Path,
    output_directory: Path,
    execution_commit: str,
    require_canonical_output: bool = True,
    dependency_verifier: Any = verify_frozen_dependencies,
    p2c_loader: Any = None,
    p3_loader: Any = None,
    p4_loader: Any = None,
    p5_loader: Any = None,
    p6_loader: Any = None,
    p7_loader: Any = None,
    p8_loader: Any = None,
    p9_loader: Any = None,
    manifest_verifier: Any = dd.verify_input_manifest,
    analytical_day_loader: Any = dd.load_authorized_days,
) -> ArtifactWriteResult:
    """Run the separately-authorized canonical P10 development campaign."""
    supplied = {
        "p2c_loader": p2c_loader,
        "p3_loader": p3_loader,
        "p4_loader": p4_loader,
        "p5_loader": p5_loader,
        "p6_loader": p6_loader,
        "p7_loader": p7_loader,
        "p8_loader": p8_loader,
        "p9_loader": p9_loader,
    }
    if p2c_loader is None:
        p2c_loader = lambda: load_verified_json_artifact(
            p9.P2C_ARTIFACT_PATH, p9.P2C_ARTIFACT_SHA256
        )
    if p3_loader is None:
        p3_loader = lambda: load_verified_json_artifact(
            p9.P3_ARTIFACT_PATH, p9.P3_ARTIFACT_SHA256
        )
    if p4_loader is None:
        p4_loader = lambda: load_verified_json_artifact(
            p9.P4_ARTIFACT_PATH, p9.P4_ARTIFACT_SHA256
        )
    if p5_loader is None:
        p5_loader = lambda: load_verified_json_artifact(
            p9.P5_ARTIFACT_PATH, p9.P5_ARTIFACT_SHA256
        )
    if p6_loader is None:
        p6_loader = lambda: load_verified_json_artifact(
            p9.P6_ARTIFACT_PATH, p9.P6_ARTIFACT_SHA256
        )
    if p7_loader is None:
        p7_loader = lambda: load_verified_json_artifact(
            p9.P7_ARTIFACT_PATH, p9.P7_ARTIFACT_SHA256
        )
    if p8_loader is None:
        p8_loader = lambda: load_verified_json_artifact(
            p9.P8_ARTIFACT_PATH, p9.P8_ARTIFACT_SHA256
        )
    if p9_loader is None:
        p9_loader = lambda: load_verified_json_artifact(
            P9_ARTIFACT_PATH, P9_ARTIFACT_SHA256
        )

    output = Path(output_directory)
    if require_canonical_output:
        if output != REAL_OUTPUT_DIRECTORY:
            raise P10Error("noncanonical_output_directory")
        for name, value in supplied.items():
            if value is not None:
                raise P10Error(
                    "canonical_dependency_override_forbidden", name
                )
        if dependency_verifier is not verify_frozen_dependencies:
            raise P10Error(
                "canonical_dependency_override_forbidden",
                "dependency_verifier",
            )
        if manifest_verifier is not dd.verify_input_manifest:
            raise P10Error(
                "canonical_dependency_override_forbidden",
                "manifest_verifier",
            )
        if analytical_day_loader is not dd.load_authorized_days:
            raise P10Error(
                "canonical_dependency_override_forbidden",
                "analytical_day_loader",
            )
    elif output == REAL_OUTPUT_DIRECTORY:
        raise P10Error("canonical_output_requires_real_mode")

    _output_preflight(output)
    execution_sha = _validate_execution_commit(execution_commit)
    try:
        mr.validate_frozen_runtime()
    except mr.P10TransformError as exc:
        raise P10Error(exc.reason, str(exc)) from exc
    dependency_hashes = dict(dependency_verifier(Path(workspace)))

    p2c_payload = dict(p2c_loader())
    p3_payload = dict(p3_loader())
    p4_payload = dict(p4_loader())
    p5_payload = dict(p5_loader())
    p6_payload = dict(p6_loader())
    p7_payload = dict(p7_loader())
    p8_payload = dict(p8_loader())
    p9_payload = dict(p9_loader())

    validate_prior_artifacts(
        p3_payload,
        p4_payload,
        p5_payload,
        p6_payload,
        p7_payload,
        p8_payload,
        p9_payload,
    )

    manifest = tuple(manifest_verifier())
    loaded_days = tuple(analytical_day_loader())
    if tuple(day.day for day in loaded_days) != dd.HISTORICAL_DAYS:
        raise P10Error("loaded_day_calendar_mismatch")

    candidate_per_day: dict[date, dd.CandidateDayDataset] = {}
    sequence_input_per_day: dict[date, Any] = {}
    for day in loaded_days:
        try:
            sequence_input = dd._validate_day_structure(day)
            candidate = dd.build_candidate_day(
                day,
                target=SELECTED_TARGET,
                window_seconds=SELECTED_WINDOW_SECONDS,
                block=SELECTED_BLOCK,
            )
        except dd.DirectionDatasetError as exc:
            raise P10Error(exc.reason, str(exc)) from exc
        try:
            p9.validate_candidate(candidate)
        except p9.P9Error as exc:
            raise P10Error(exc.reason, str(exc)) from exc
        candidate_per_day[day.day] = candidate
        sequence_input_per_day[day.day] = sequence_input

    if tuple(candidate_per_day) != dd.HISTORICAL_DAYS:
        raise P10Error("candidate_day_order_mismatch")

    try:
        p9.reconcile_selected_candidate_with_p2c(
            candidate_per_day, p2c_payload
        )
        p3_reproduction = p9.reproduce_frozen_p3(candidate_per_day)
        interval_checks = p9.verify_interval_separation(candidate_per_day)
    except p9.P9Error as exc:
        raise P10Error(exc.reason, str(exc)) from exc

    per_day = {
        day: build_p10_day(
            candidate_per_day[day],
            sequence_input_per_day[day],
        )
        for day in dd.HISTORICAL_DAYS
    }

    c0 = fit_c0_exact(per_day, p8_payload)
    c1, transform_ledgers = fit_c1(per_day)
    validate_matched_support(c0, c1)

    comparison = comparison_summary(c0, c1)
    null: p9.PairedTemporalNull | None = None
    if comparison["precheck_pass"]:
        try:
            null = p9.paired_temporal_null(c0, c1, comparison)
        except p9.P9Error as exc:
            raise P10Error(exc.reason, str(exc)) from exc

    gates = final_gates(comparison, null)
    eligible = all(gates.values())
    if eligible:
        status = "ELIGIBLE_PRICE_MINIROCKET_INCREMENTAL_INFORMATION"
    elif comparison["precheck_pass"]:
        status = "FAIL_PRICE_MINIROCKET_TEMPORAL_NULL"
    else:
        status = "FAIL_PRICE_MINIROCKET_NO_STABLE_INCREMENTAL_VALUE"

    runtime = runtime_provenance(model_fit_run=True, p10_run=True)

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "status": status,
        "execution_commit": execution_sha,
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            **mr.runtime_versions(),
        },
        "selected_configuration": {
            "target": {
                "target_id": "A",
                "horizon_seconds": 120,
                "barrier_bps": 16,
            },
            "window_seconds": 32,
            "block": "PRICE",
            "task": "DIRECTION_GIVEN_TOUCH",
            "baseline_feature_count": EXPECTED_BASELINE_FEATURE_COUNT,
            "transform_feature_count": EXPECTED_TRANSFORM_FEATURE_COUNT,
            "augmented_feature_count": EXPECTED_AUGMENTED_FEATURE_COUNT,
            "sequence_channels": list(p9.PRICE_LAG_PRIMITIVES),
            "sequence_timepoints": 32,
            "requested_transform_features": mr.REQUESTED_FEATURES,
            "actual_transform_features": mr.ACTUAL_FEATURES,
            "dilations": list(mr.EXPECTED_DILATIONS),
            "features_per_dilation_per_kernel": list(
                mr.EXPECTED_FEATURES_PER_DILATION
            ),
            "random_state": mr.RANDOM_STATE,
            "transform_threads": mr.TRANSFORM_THREADS,
            "C_grid": list(p9.C_GRID),
        },
        "dependency_sha256": dependency_hashes,
        "frozen_artifacts": {
            "p2c": {
                "path": str(p9.P2C_ARTIFACT_PATH),
                "sha256": p9.P2C_ARTIFACT_SHA256,
            },
            "p3": {
                "path": str(p9.P3_ARTIFACT_PATH),
                "sha256": p9.P3_ARTIFACT_SHA256,
            },
            "p4": {
                "path": str(p9.P4_ARTIFACT_PATH),
                "sha256": p9.P4_ARTIFACT_SHA256,
            },
            "p5": {
                "path": str(p9.P5_ARTIFACT_PATH),
                "sha256": p9.P5_ARTIFACT_SHA256,
            },
            "p6": {
                "path": str(p9.P6_ARTIFACT_PATH),
                "sha256": p9.P6_ARTIFACT_SHA256,
            },
            "p7": {
                "path": str(p9.P7_ARTIFACT_PATH),
                "sha256": p9.P7_ARTIFACT_SHA256,
            },
            "p8": {
                "path": str(p9.P8_ARTIFACT_PATH),
                "sha256": p9.P8_ARTIFACT_SHA256,
            },
            "p9": {
                "path": str(P9_ARTIFACT_PATH),
                "sha256": P9_ARTIFACT_SHA256,
            },
        },
        "authorized_input_manifest": [
            {
                "date": item.day.isoformat(),
                "path": str(item.path),
                "sha256": item.sha256,
                "bytes": int(item.bytes),
            }
            for item in manifest
        ],
        "p3_reproduction": p3_reproduction,
        "interval_separation_checks": list(interval_checks),
        "exact_support": {
            "expected_pooled_support": EXPECTED_POOLED_SUPPORT,
            "expected_pooled_long": EXPECTED_POOLED_LONG,
            "expected_pooled_short": EXPECTED_POOLED_SHORT,
            "expected_fold_support": list(EXPECTED_FOLD_SUPPORT),
            "expected_fold_long": list(EXPECTED_FOLD_LONG),
            "expected_fold_short": list(EXPECTED_FOLD_SHORT),
            "pooled_support_sha256": c0.pooled_support_sha256,
            "pooled_label_sha256": c0.pooled_label_sha256,
        },
        "c0_price_s1": {
            "feature_count": EXPECTED_BASELINE_FEATURE_COUNT,
            "folds": [_fold_public(fold) for fold in c0.folds],
            "pooled": c0.pooled_metrics,
        },
        "c1_price_s1_plus_minirocket": {
            "feature_count": EXPECTED_AUGMENTED_FEATURE_COUNT,
            "folds": [_fold_public(fold) for fold in c1.folds],
            "pooled": c1.pooled_metrics,
            "transform_ledgers": [
                _ledger_public(item) for item in transform_ledgers
            ],
        },
        "comparison_c1_vs_c0": comparison,
        "temporal_null": (
            {
                "eligible_shifts": list(null.eligible_shifts),
                "null_log_loss_improvement": list(
                    null.null_log_loss_improvement
                ),
                "null_auc_delta": list(null.null_auc_delta),
                "log_loss_improvement_q95": (
                    null.log_loss_improvement_q95
                ),
                "auc_delta_q95": null.auc_delta_q95,
                "empirical_p": null.empirical_p,
                "observed_log_loss_improvement": (
                    null.observed_log_loss_improvement
                ),
                "observed_auc_delta": null.observed_auc_delta,
                "pass_gate": null.pass_gate,
            }
            if null is not None
            else {
                "status": "TEMPORAL_NULL_NOT_RUN_PRECHECK_FAILED"
            }
        ),
        "promotion_gates": gates,
        "eligible_price_minirocket_incremental_information": eligible,
        "runtime_provenance": runtime,
        "prohibited_activity": {
            "forward_data": False,
            "threshold_optimization": False,
            "pnl": False,
            "economics": False,
            "opportunity_gate": False,
            "alternate_model_family": False,
            "deep_model": False,
            "lag_search": False,
            "feature_family_search": False,
            "kernel_count_search": False,
            "seed_search": False,
            "class_weighting_or_resampling": False,
            "calibration": False,
        },
    }

    return write_result_once(
        output,
        payload,
        require_canonical_output=require_canonical_output,
    )


__all__ = [
    "ARTIFACT_FILENAME",
    "DESIGN_VERSION",
    "EXPERIMENT_ID",
    "EXPECTED_AUGMENTED_FEATURE_COUNT",
    "EXPECTED_TRANSFORM_FEATURE_COUNT",
    "P10Day",
    "P10Error",
    "P9_ARTIFACT_PATH",
    "P9_ARTIFACT_SHA256",
    "REAL_OUTPUT_DIRECTORY",
    "build_p10_day",
    "comparison_summary",
    "fit_c0_exact",
    "fit_c1",
    "fit_c1_fold",
    "run_p10",
    "runtime_provenance",
    "validate_prior_artifacts",
    "verify_frozen_dependencies",
]

from __future__ import annotations

import ast
from datetime import date
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from multimarket import dev030_direction_dataset as dd
from multimarket import dev030_p4_touch_composition as p4
from multimarket import dev030_p5_joint_threeclass as p5


def _reason(function: Any, *args: Any, **kwargs: Any) -> str:
    with pytest.raises(p5.P5Error) as caught:
        function(*args, **kwargs)
    return caught.value.reason


def _record(label: str | None, *, valid: bool = True) -> dict[str, Any]:
    if valid:
        return {
            "target_valid": True,
            "label": label,
            "invalid_reason": None,
            "same_row_ambiguous": False,
        }
    return {
        "target_valid": False,
        "label": None,
        "invalid_reason": "synthetic_invalid",
        "same_row_ambiguous": False,
    }


def _candidate_day(
    day: date,
    *,
    labels: tuple[str | None, ...] = (
        dd.fp.NONE,
        dd.fp.SHORT_FIRST,
        dd.fp.LONG_FIRST,
        dd.fp.NONE,
    ),
    invalid_last: bool = False,
) -> dd.CandidateDayDataset:
    n = len(labels)
    ts = day.month * 10**12 + np.arange(n, dtype=np.int64) * 60_000_000
    records: list[dict[str, Any]] = []
    for i, label in enumerate(labels):
        records.append(
            _record(None, valid=False)
            if invalid_last and i == n - 1
            else _record(label, valid=True)
        )

    s0_names = tuple(dd.sf.block_feature_names("PRICE"))
    s1_names = dd.sequence_summary_feature_names("PRICE")
    s0 = np.tile(
        np.arange(1, len(s0_names) + 1, dtype=np.float64),
        (n, 1),
    )
    s1 = np.tile(
        np.arange(1, len(s1_names) + 1, dtype=np.float64),
        (n, 1),
    )
    s0 += np.arange(n, dtype=np.float64)[:, None] * 0.01
    s1 += np.arange(n, dtype=np.float64)[:, None] * 0.02

    common = np.ones(n, dtype=bool)
    future = np.ones(n, dtype=bool)
    t1 = np.asarray(
        [label in (dd.fp.SHORT_FIRST, dd.fp.LONG_FIRST) for label in labels],
        dtype=bool,
    )
    if invalid_last:
        t1[-1] = False
    t1_labels = np.full(n, dd.T1_EXCLUDED, dtype=np.int8)
    for i, label in enumerate(labels):
        if label == dd.fp.LONG_FIRST:
            t1_labels[i] = dd.T1_LONG
        elif label == dd.fp.SHORT_FIRST:
            t1_labels[i] = dd.T1_SHORT

    none_reason = tuple(None for _ in range(n))
    counts = {
        "decision_count": n,
        "t1_common_support_count": int(np.count_nonzero(t1)),
        "t1_long_common_count": int(np.count_nonzero(t1_labels == dd.T1_LONG)),
        "t1_short_common_count": int(np.count_nonzero(t1_labels == dd.T1_SHORT)),
    }
    hashes = {
        "native_s0_support_sha256": dd.support_sha256(ts),
        "native_s1_support_sha256": dd.support_sha256(ts),
        "common_support_sha256": dd.support_sha256(ts),
        "t1_common_support_sha256": dd.support_sha256(ts[t1]),
    }
    return dd.CandidateDayDataset(
        day=day,
        key=p5.SELECTED_KEY,
        decision_timestamps_us=ts,
        target_records=tuple(records),
        t1_labels=t1_labels,
        s0_feature_names=s0_names,
        s1_feature_names=s1_names,
        s0_values=s0,
        s1_values=s1,
        s0_valid=common.copy(),
        s1_valid=common.copy(),
        common_valid=common.copy(),
        t1_common_valid=t1.copy(),
        target_future_boundary_valid=future,
        s0_boundary_reasons=none_reason,
        s1_boundary_reasons=none_reason,
        target_boundary_reasons=none_reason,
        s0_invalid_reasons=none_reason,
        s1_invalid_reasons=none_reason,
        counts=counts,
        support_hashes=hashes,
    )


def _synthetic_joint_days(rows: int = 120) -> dict[date, p5.JointDayDataset]:
    result: dict[date, p5.JointDayDataset] = {}
    for month, day in enumerate(dd.HISTORICAL_DAYS, start=1):
        idx = np.arange(rows)
        y = ((idx + month) % 3).astype(np.int8)
        ts = month * 10**12 + idx.astype(np.int64) * 60_000_000
        x = np.column_stack(
            (
                (y == 0).astype(float) * 2.0 + np.sin(idx * 0.03),
                (y == 1).astype(float) * 2.0 + np.cos(idx * 0.05),
                (y == 2).astype(float) * 2.0 + np.sin(idx * 0.07),
            )
        )
        counts = {
            "NONE": int(np.count_nonzero(y == 0)),
            "SHORT_FIRST": int(np.count_nonzero(y == 1)),
            "LONG_FIRST": int(np.count_nonzero(y == 2)),
        }
        result[day] = p5.JointDayDataset(
            day,
            ts,
            y,
            x,
            ("a", "b", "c"),
            dd.support_sha256(ts),
            p5._label_hash(ts, y),
            counts,
        )
    return result


def _baseline_for_joint(
    joint_folds: tuple[p5.JointFoldResult, ...],
    *,
    quality_gap: float = 0.02,
) -> p5.BaselineBundle:
    labels = tuple(f.y_true.copy() for f in joint_folds)
    timestamps = tuple(f.timestamps_us.copy() for f in joint_folds)

    c0: list[np.ndarray] = []
    c1: list[np.ndarray] = []
    c2: list[np.ndarray] = []
    m0: list[dict[str, Any]] = []
    m1: list[dict[str, Any]] = []
    m2: list[dict[str, Any]] = []
    for fold in joint_folds:
        n = len(fold.y_true)
        prevalence = np.bincount(fold.y_true, minlength=3).astype(float)
        prevalence /= prevalence.sum()
        p0 = np.tile(prevalence, (n, 1))

        # Create deliberately weaker C1/C2 fixtures while preserving valid
        # probability rows. A uniform convex shrinkage would preserve every
        # per-class ranking and therefore leave Average Precision unchanged,
        # which cannot exercise the frozen macro-AP/directional-AP gates.
        if not 0.0 < quality_gap < 1.0:
            raise AssertionError("quality_gap must be in (0, 1)")
        p1 = fold.probabilities.copy()
        p2 = fold.probabilities.copy()

        # Corrupt deterministic subsets by cycling class-probability columns.
        # This changes rankings as well as proper scoring rules without using
        # randomness or altering labels.
        stride1 = max(2, int(round(1.0 / quality_gap)))
        stride2 = max(2, int(round(2.0 / quality_gap)))
        idx1 = np.arange(0, n, stride1)
        idx2 = np.arange(stride2 // 2, n, stride2)
        p1[idx1] = p1[idx1][:, [1, 2, 0]]
        p2[idx2] = p2[idx2][:, [2, 0, 1]]

        p1 /= p1.sum(axis=1, keepdims=True)
        p2 /= p2.sum(axis=1, keepdims=True)

        c0.append(p0)
        c1.append(p1)
        c2.append(p2)
        m0.append(p5.joint_metrics(fold.y_true, p0))
        m1.append(p5.joint_metrics(fold.y_true, p1))
        m2.append(p5.joint_metrics(fold.y_true, p2))

    pooled_y = np.concatenate(labels)
    return p5.BaselineBundle(
        tuple(c0),
        tuple(c1),
        tuple(c2),
        labels,
        timestamps,
        tuple(m0),
        tuple(m1),
        tuple(m2),
        p5.joint_metrics(pooled_y, np.concatenate(c0)),
        p5.joint_metrics(pooled_y, np.concatenate(c1)),
        p5.joint_metrics(pooled_y, np.concatenate(c2)),
    )


def test_selected_configuration_is_exact() -> None:
    assert p5.SELECTED_TARGET.target_id == "A"
    assert p5.SELECTED_TARGET.horizon_seconds == 120
    assert p5.SELECTED_TARGET.barrier_bps == 16
    assert p5.SELECTED_WINDOW_SECONDS == 32
    assert p5.SELECTED_BLOCK == "PRICE"


def test_build_joint_day_maps_exact_class_order() -> None:
    result = p5.build_joint_day(_candidate_day(dd.HISTORICAL_DAYS[0]))
    assert result.labels.tolist() == [0, 1, 2, 0]
    assert result.class_counts == {
        "NONE": 2,
        "SHORT_FIRST": 1,
        "LONG_FIRST": 1,
    }


def test_build_joint_day_excludes_invalid_target() -> None:
    result = p5.build_joint_day(
        _candidate_day(dd.HISTORICAL_DAYS[0], invalid_last=True)
    )
    assert result.labels.tolist() == [0, 1, 2]


def test_wrong_candidate_identity_fails() -> None:
    dataset = _candidate_day(dd.HISTORICAL_DAYS[0])
    dataset.key = dd.CandidateKey(dd.FROZEN_TARGETS[1], 32, "PRICE")
    assert _reason(
        p5.build_joint_day, dataset
    ) == "selected_candidate_identity_mismatch"


def test_joint_metrics_perfect_probabilities() -> None:
    y = np.asarray([0, 1, 2, 0, 1, 2], dtype=np.int8)
    p = np.eye(3, dtype=float)[y] * 0.98 + 0.02 / 3.0
    p /= p.sum(axis=1, keepdims=True)
    metrics = p5.joint_metrics(y, p)
    assert metrics["argmax_balanced_accuracy"] == 1.0
    assert metrics["macro_ovr_average_precision"] == 1.0


def test_joint_metrics_rejects_bad_probability_sum() -> None:
    y = np.asarray([0, 1, 2], dtype=np.int8)
    p = np.asarray([[0.5, 0.3, 0.3]] * 3)
    assert _reason(p5.joint_metrics, y, p) == "joint_probability_sum_mismatch"


def test_joint_model_configuration() -> None:
    model = p5._new_joint_logistic(0.1)
    assert p5.C_GRID == (0.01, 0.1, 1.0, 10.0)
    assert model.C == 0.1
    assert model.solver == "lbfgs"
    assert model.l1_ratio == 0.0
    assert model.class_weight is None
    assert model.max_iter == 1000


def test_select_c_tie_prefers_smaller_c() -> None:
    x_fit = np.zeros((60, 3), dtype=float)
    y_fit = np.tile(np.asarray([0, 1, 2], dtype=np.int8), 20)
    x_val = np.zeros((60, 3), dtype=float)
    y_val = np.tile(np.asarray([0, 1, 2], dtype=np.int8), 20)
    selected, ledger = p5.select_c(x_fit, y_fit, x_val, y_val)
    assert selected == 0.01
    assert [item["C"] for item in ledger] == list(p5.C_GRID)


def test_fit_joint_fold_respects_chronological_fold() -> None:
    result = p5.fit_joint_fold(
        fold=dd.OUTER_FOLDS[0],
        per_day=_synthetic_joint_days(),
    )
    assert result.fold_id == 1
    assert result.support == 120
    assert tuple(result.model.classes_.tolist()) == p5.CLASS_ORDER


def test_prediction_hash_is_deterministic() -> None:
    folds = _synthetic_joint_days()
    a = p5.fit_joint_fold(fold=dd.OUTER_FOLDS[0], per_day=folds)
    b = p5.fit_joint_fold(fold=dd.OUTER_FOLDS[0], per_day=folds)
    assert a.prediction_sha256 == b.prediction_sha256


def test_expected_real_support_contract_constants() -> None:
    assert p5.EXPECTED_POOLED_SUPPORT == 5748
    assert p5.EXPECTED_FOLD_SUPPORT == (1437, 1437, 1437, 1437)
    assert p5.EXPECTED_POOLED_COUNTS == {
        "NONE": 5175,
        "SHORT_FIRST": 264,
        "LONG_FIRST": 309,
    }


def test_p4_artifact_identity_requires_frozen_failure_state() -> None:
    payload = {
        "experiment_id": "DEV030-P4",
        "status": "FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE",
        "selected_configuration": {
            "target": {
                "target_id": "A",
                "horizon_seconds": 120,
                "barrier_bps": 16,
            },
            "window_seconds": 32,
            "block": "PRICE",
        },
        "t2": {"eligible_for_composition": True},
    }
    p5.validate_p4_artifact_identity(payload)


def test_p4_artifact_identity_rejects_changed_configuration() -> None:
    payload = {
        "experiment_id": "DEV030-P4",
        "status": "FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE",
        "selected_configuration": {
            "target": {
                "target_id": "A",
                "horizon_seconds": 120,
                "barrier_bps": 16,
            },
            "window_seconds": 60,
            "block": "PRICE",
        },
        "t2": {"eligible_for_composition": True},
    }
    assert _reason(
        p5.validate_p4_artifact_identity, payload
    ) == "p4_selected_configuration_mismatch"


def test_comparison_summary_detects_positive_improvement() -> None:
    days = _synthetic_joint_days()
    folds = tuple(
        p5.fit_joint_fold(fold=fold, per_day=days)
        for fold in dd.OUTER_FOLDS
    )
    joint = p5.JointModelResult(
        folds,
        p5.joint_metrics(
            np.concatenate([f.y_true for f in folds]),
            np.concatenate([f.probabilities for f in folds]),
        ),
        dd.support_sha256(np.concatenate([f.timestamps_us for f in folds])),
        p5._label_hash(
            np.concatenate([f.timestamps_us for f in folds]),
            np.concatenate([f.y_true for f in folds]),
        ),
    )
    baseline = _baseline_for_joint(folds, quality_gap=0.10)
    comparison = p5.comparison_summary(joint=joint, baselines=baseline)
    assert comparison["pooled_log_loss_improvement_vs_c1"] > 0
    assert comparison["pooled_brier_improvement_vs_c1"] > 0
    assert comparison["pooled_macro_ap_delta_vs_c1"] > 0
    assert comparison["precheck_pass"] is True


def test_directional_safeguard_is_present() -> None:
    days = _synthetic_joint_days()
    folds = tuple(
        p5.fit_joint_fold(fold=fold, per_day=days)
        for fold in dd.OUTER_FOLDS
    )
    joint = p5.JointModelResult(
        folds,
        p5.joint_metrics(
            np.concatenate([f.y_true for f in folds]),
            np.concatenate([f.probabilities for f in folds]),
        ),
        dd.support_sha256(np.concatenate([f.timestamps_us for f in folds])),
        p5._label_hash(
            np.concatenate([f.timestamps_us for f in folds]),
            np.concatenate([f.y_true for f in folds]),
        ),
    )
    baseline = _baseline_for_joint(folds, quality_gap=0.10)
    comparison = p5.comparison_summary(joint=joint, baselines=baseline)
    assert "at_least_one_directional_ap_improves" in comparison["precheck_gates"]
    assert "mean_directional_ap_delta_positive" in comparison["precheck_gates"]


def test_temporal_null_is_deterministic() -> None:
    days = _synthetic_joint_days()
    folds = tuple(
        p5.fit_joint_fold(fold=fold, per_day=days)
        for fold in dd.OUTER_FOLDS
    )
    joint = p5.JointModelResult(
        folds,
        p5.joint_metrics(
            np.concatenate([f.y_true for f in folds]),
            np.concatenate([f.probabilities for f in folds]),
        ),
        dd.support_sha256(np.concatenate([f.timestamps_us for f in folds])),
        p5._label_hash(
            np.concatenate([f.timestamps_us for f in folds]),
            np.concatenate([f.y_true for f in folds]),
        ),
    )
    baseline = _baseline_for_joint(folds, quality_gap=0.10)
    comparison = p5.comparison_summary(joint=joint, baselines=baseline)
    first = p5.temporal_null(
        joint=joint,
        baselines=baseline,
        comparison=comparison,
    )
    second = p5.temporal_null(
        joint=joint,
        baselines=baseline,
        comparison=comparison,
    )
    assert first == second


def test_temporal_null_uses_paired_c1_and_j1_statistic() -> None:
    days = _synthetic_joint_days()
    folds = tuple(
        p5.fit_joint_fold(fold=fold, per_day=days)
        for fold in dd.OUTER_FOLDS
    )
    joint = p5.JointModelResult(
        folds,
        p5.joint_metrics(
            np.concatenate([f.y_true for f in folds]),
            np.concatenate([f.probabilities for f in folds]),
        ),
        dd.support_sha256(np.concatenate([f.timestamps_us for f in folds])),
        p5._label_hash(
            np.concatenate([f.timestamps_us for f in folds]),
            np.concatenate([f.y_true for f in folds]),
        ),
    )
    baseline = _baseline_for_joint(folds, quality_gap=0.10)
    comparison = p5.comparison_summary(joint=joint, baselines=baseline)
    null = p5.temporal_null(
        joint=joint,
        baselines=baseline,
        comparison=comparison,
    )
    k = null.eligible_shifts[0]
    shifted = np.concatenate([
        np.roll(y, k) for y in baseline.labels_by_fold
    ])
    expected = (
        p5.joint_metrics(shifted, np.concatenate(baseline.c1_folds))[
            "multiclass_log_loss"
        ]
        - p5.joint_metrics(
            shifted,
            np.concatenate([f.probabilities for f in folds]),
        )["multiclass_log_loss"]
    )
    assert null.null_log_loss_improvement[0] == pytest.approx(expected)


def test_null_shift_rule_exact() -> None:
    assert p5.eligible_shared_shifts([40, 40, 40, 40]) == tuple(range(10, 31))


def test_insufficient_null_shifts_fail_closed() -> None:
    assert len(p5.eligible_shared_shifts([20, 20, 20, 20])) < 20


def test_missing_null_cannot_promote() -> None:
    comparison = {
        "precheck_gates": {
            "a": True,
        }
    }
    gates = p5.final_gates(
        comparison=comparison,
        null=None,
        baseline_reproduction_pass=True,
    )
    assert gates["temporal_null_run"] is False
    assert all(gates.values()) is False


def test_baseline_reproduction_gate_cannot_be_rescued() -> None:
    comparison = {"precheck_gates": {"a": True}}
    gates = p5.final_gates(
        comparison=comparison,
        null=None,
        baseline_reproduction_pass=False,
    )
    assert gates["baseline_reproduction_pass"] is False


def test_runtime_guards_are_closed() -> None:
    state = p5.runtime_provenance(model_fit_run=True, p5_run=True)
    assert not any(state["forward_data_guards"].values())
    assert state["threshold_optimization_run"] is False
    assert state["pnl_backtest_run"] is False
    assert state["opportunity_gate_run"] is False
    assert state["m2_or_deep_model_run"] is False


def test_runtime_validator_rejects_forward_open() -> None:
    state = p5.runtime_provenance(model_fit_run=True, p5_run=True)
    state["forward_data_guards"]["sep01_or_later_analytically_opened"] = True
    assert _reason(
        p5.validate_runtime_provenance, state
    ) == "forward_data_guard_violation"


def test_p5_requires_model_fit() -> None:
    assert _reason(
        p5.runtime_provenance,
        model_fit_run=False,
        p5_run=True,
    ) == "p5_requires_model_fit"


def test_canonical_json_is_deterministic() -> None:
    assert p5.canonical_json_bytes({"b": 2, "a": 1}) == p5.canonical_json_bytes(
        {"a": 1, "b": 2}
    )


def test_writer_is_atomic_and_write_once(tmp_path: Path) -> None:
    output = tmp_path / "p5"
    result = p5.write_result_once(
        output,
        {"synthetic": True},
        require_canonical_output=False,
    )
    assert result.artifact_path.is_file()
    assert result.artifact_sha256 == hashlib.sha256(
        result.artifact_path.read_bytes()
    ).hexdigest()
    assert not result.artifact_path.with_name(
        result.artifact_path.name + ".part"
    ).exists()
    assert _reason(
        p5.write_result_once,
        output,
        {"synthetic": True},
        require_canonical_output=False,
    ) == "output_directory_already_exists"


def test_real_output_cannot_enter_synthetic_mode_when_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_real = tmp_path / "canonical"
    monkeypatch.setattr(p5, "REAL_OUTPUT_DIRECTORY", fake_real)
    assert _reason(
        p5.write_result_once,
        fake_real,
        {"synthetic": True},
        require_canonical_output=False,
    ) == "canonical_output_requires_real_mode"


def test_canonical_run_rejects_dependency_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_real = tmp_path / "canonical"
    monkeypatch.setattr(p5, "REAL_OUTPUT_DIRECTORY", fake_real)
    assert _reason(
        p5.run_p5,
        workspace=tmp_path,
        output_directory=fake_real,
        execution_commit="a" * 40,
        require_canonical_output=True,
        p4_loader=lambda: {},
    ) == "canonical_dependency_override_forbidden"


def test_test_module_does_not_call_real_data_loader_or_run() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name):
            calls.add(function.id)
        elif isinstance(function, ast.Attribute):
            calls.add(function.attr)
    assert "load_authorized_days" not in calls
    assert "run_p5" not in calls
    assert "run_p4" not in calls

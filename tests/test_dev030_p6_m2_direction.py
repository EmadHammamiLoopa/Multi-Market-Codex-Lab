from __future__ import annotations

import ast
from datetime import date
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from multimarket import dev030_direction_dataset as dd
from multimarket import dev030_p6_m2_direction as p6


def _reason(function: Any, *args: Any, **kwargs: Any) -> str:
    with pytest.raises(p6.P6Error) as caught:
        function(*args, **kwargs)
    return caught.value.reason


def _candidate_day(day: date, rows: int = 90) -> dd.CandidateDayDataset:
    names = dd.sequence_summary_feature_names("PRICE")
    ts = (
        day.month * 10**12
        + np.arange(rows, dtype=np.int64) * 60_000_000
    )
    y = ((np.arange(rows) + day.month) % 2).astype(np.int8)
    x = np.column_stack(
        [
            np.sin(np.arange(rows) * (0.01 + j * 0.002))
            + 0.35 * y
            + j * 0.001
            for j in range(len(names))
        ]
    )
    s0_names = tuple(dd.sf.block_feature_names("PRICE"))
    s0 = np.zeros((rows, len(s0_names)), dtype=float)
    valid = np.ones(rows, dtype=bool)
    records = tuple(
        {
            "target_valid": True,
            "label": dd.fp.LONG_FIRST if yy == 1 else dd.fp.SHORT_FIRST,
            "invalid_reason": None,
            "same_row_ambiguous": False,
        }
        for yy in y.tolist()
    )
    return dd.CandidateDayDataset(
        day=day,
        key=p6.SELECTED_KEY,
        decision_timestamps_us=ts,
        target_records=records,
        t1_labels=y.copy(),
        s0_feature_names=s0_names,
        s1_feature_names=tuple(names),
        s0_values=s0,
        s1_values=x,
        s0_valid=valid.copy(),
        s1_valid=valid.copy(),
        common_valid=valid.copy(),
        t1_common_valid=valid.copy(),
        target_future_boundary_valid=valid.copy(),
        s0_boundary_reasons=tuple(None for _ in range(rows)),
        s1_boundary_reasons=tuple(None for _ in range(rows)),
        target_boundary_reasons=tuple(None for _ in range(rows)),
        s0_invalid_reasons=tuple(None for _ in range(rows)),
        s1_invalid_reasons=tuple(None for _ in range(rows)),
        counts={},
        support_hashes={},
    )


def _per_day(rows: int = 90) -> dict[date, dd.CandidateDayDataset]:
    return {day: _candidate_day(day, rows=rows) for day in dd.HISTORICAL_DAYS}


def _direction_fold(
    fold_id: int,
    y: np.ndarray,
    p: np.ndarray,
    ts: np.ndarray,
) -> p6.DirectionFold:
    pred = (p >= 0.5).astype(np.int8)
    return p6.DirectionFold(
        fold_id=fold_id,
        support=len(y),
        long_count=int(np.count_nonzero(y == 1)),
        short_count=int(np.count_nonzero(y == 0)),
        metrics=p6.binary_probability_metrics(y, p),
        timestamps_us=ts,
        y_true=y,
        p_long=p,
        y_pred=pred,
        prediction_sha256="x" * 64,
        support_sha256=dd.support_sha256(ts),
        label_sha256=p6.label_sha256(ts, y),
    )


def test_selected_configuration_is_exact() -> None:
    assert p6.SELECTED_TARGET.target_id == "A"
    assert p6.SELECTED_TARGET.horizon_seconds == 120
    assert p6.SELECTED_TARGET.barrier_bps == 16
    assert p6.SELECTED_WINDOW_SECONDS == 32
    assert p6.SELECTED_BLOCK == "PRICE"
    assert p6.EXPECTED_FEATURE_COUNT == 23


def test_price_s1_feature_count_is_23() -> None:
    assert len(dd.sequence_summary_feature_names("PRICE")) == 23


def test_validate_selected_candidate_accepts_exact_shape() -> None:
    p6.validate_selected_candidate(_candidate_day(dd.HISTORICAL_DAYS[0]))


def test_validate_selected_candidate_rejects_wrong_key() -> None:
    dataset = _candidate_day(dd.HISTORICAL_DAYS[0])
    dataset.key = dd.CandidateKey(dd.FROZEN_TARGETS[1], 32, "PRICE")
    assert _reason(
        p6.validate_selected_candidate, dataset
    ) == "selected_candidate_identity_mismatch"


def test_validate_selected_candidate_rejects_wrong_feature_order() -> None:
    dataset = _candidate_day(dd.HISTORICAL_DAYS[0])
    dataset.s1_feature_names = tuple(reversed(dataset.s1_feature_names))
    assert _reason(
        p6.validate_selected_candidate, dataset
    ) == "selected_s1_feature_order_mismatch"


def test_t1_rows_excludes_none_via_mask_contract() -> None:
    dataset = _candidate_day(dd.HISTORICAL_DAYS[0], rows=6)
    dataset.t1_common_valid[2] = False
    dataset.t1_labels[2] = dd.T1_EXCLUDED
    x, y, ts = p6._t1_rows(dataset)
    assert len(y) == 5
    assert dd.T1_EXCLUDED not in y
    assert len(x) == len(ts) == 5


def test_binary_probability_metrics_perfect() -> None:
    y = np.array([0, 1, 0, 1], dtype=np.int8)
    p = np.array([0.01, 0.99, 0.02, 0.98], dtype=float)
    m = p6.binary_probability_metrics(y, p)
    assert m["roc_auc"] == 1.0
    assert m["balanced_accuracy_at_0_5"] == 1.0
    assert m["macro_f1_at_0_5"] == 1.0


def test_binary_probability_metrics_rejects_invalid_probability() -> None:
    y = np.array([0, 1], dtype=np.int8)
    assert _reason(
        p6.binary_probability_metrics,
        y,
        np.array([0.2, 1.2]),
    ) == "binary_metric_probabilities_invalid"


def test_hgb_grid_is_exactly_four_bounded_capacities() -> None:
    assert p6.CAPACITY_GRID == (
        ("H1", 3, 50),
        ("H2", 3, 100),
        ("H3", 7, 50),
        ("H4", 7, 100),
    )


def test_hgb_fixed_parameters_match_design() -> None:
    model = p6.new_m2_model("H1")
    assert model.loss == "log_loss"
    assert model.learning_rate == 0.05
    assert model.min_samples_leaf == 20
    assert model.l2_regularization == 1.0
    assert model.max_features == 1.0
    assert model.max_bins == 255
    assert model.early_stopping is False
    assert model.class_weight is None
    assert model.random_state == 20260825
    assert model.max_leaf_nodes == 3
    assert model.max_iter == 50


def test_unknown_capacity_fails_closed() -> None:
    assert _reason(p6.new_m2_model, "HX") == "capacity_id_not_frozen"


def test_select_capacity_returns_one_frozen_id() -> None:
    rng = np.random.default_rng(123)
    xf = rng.normal(size=(180, 23))
    yf = np.tile(np.array([0, 1], dtype=np.int8), 90)
    xv = rng.normal(size=(80, 23))
    yv = np.tile(np.array([0, 1], dtype=np.int8), 40)
    selected, ledger = p6.select_capacity(xf, yf, xv, yv)
    assert selected in {"H1", "H2", "H3", "H4"}
    assert [x["capacity_id"] for x in ledger] == ["H1", "H2", "H3", "H4"]


def test_m2_prediction_hash_is_deterministic() -> None:
    ts = np.arange(10, dtype=np.int64) * 60_000_000
    y = np.tile(np.array([0, 1], dtype=np.int8), 5)
    p = np.linspace(0.1, 0.9, 10)
    a = p6.m2_prediction_sha256(
        fold_id=1,
        capacity_id="H1",
        timestamps_us=ts,
        y_true=y,
        p_long=p,
    )
    b = p6.m2_prediction_sha256(
        fold_id=1,
        capacity_id="H1",
        timestamps_us=ts,
        y_true=y,
        p_long=p,
    )
    assert a == b


def test_label_hash_changes_when_label_changes() -> None:
    ts = np.arange(4, dtype=np.int64) * 60_000_000
    y1 = np.array([0, 1, 0, 1], dtype=np.int8)
    y2 = np.array([0, 1, 1, 1], dtype=np.int8)
    assert p6.label_sha256(ts, y1) != p6.label_sha256(ts, y2)


def test_fit_m2_fold_preserves_chronological_validation_day() -> None:
    result = p6.fit_m2_fold(
        fold=dd.OUTER_FOLDS[0],
        per_day=_per_day(),
    )
    assert result.fold_id == 1
    assert result.support == 90
    assert np.all(np.diff(result.timestamps_us) > 0)
    assert result.selected_capacity_id in {"H1", "H2", "H3", "H4"}


def test_interval_separation_passes_for_monthly_synthetic_days() -> None:
    checks = p6.verify_interval_separation(_per_day())
    assert len(checks) == 8
    assert all(item["pass"] is True for item in checks)


def test_expected_real_support_contract_is_frozen() -> None:
    assert p6.EXPECTED_POOLED_VALIDATION_SUPPORT == 573
    assert p6.EXPECTED_FOLD_SUPPORT == (159, 64, 126, 224)


def test_comparison_summary_detects_better_m2() -> None:
    m1_folds = []
    m2_folds = []
    for fold_id, n in enumerate((60, 60, 60, 60), start=1):
        ts = fold_id * 10**12 + np.arange(n, dtype=np.int64) * 60_000_000
        y = np.tile(np.array([0, 1], dtype=np.int8), n // 2)
        p1 = np.where(y == 1, 0.55, 0.45)
        p2 = np.where(y == 1, 0.75, 0.25)
        m1_folds.append(_direction_fold(fold_id, y, p1, ts))
        base = _direction_fold(fold_id, y, p2, ts)
        m2_folds.append(
            p6.M2Fold(
                **base.__dict__,
                selected_capacity_id="H1",
                selected_max_leaf_nodes=3,
                selected_max_iter=50,
                inner_capacity_ledger=(),
                model=None,
            )
        )

    pooled_y = np.concatenate([f.y_true for f in m1_folds])
    pooled_ts = np.concatenate([f.timestamps_us for f in m1_folds])
    m1 = p6.M1Result(
        tuple(m1_folds),
        p6.binary_probability_metrics(
            pooled_y, np.concatenate([f.p_long for f in m1_folds])
        ),
        dd.support_sha256(pooled_ts),
        p6.label_sha256(pooled_ts, pooled_y),
    )
    m2 = p6.M2Result(
        tuple(m2_folds),
        p6.binary_probability_metrics(
            pooled_y, np.concatenate([f.p_long for f in m2_folds])
        ),
        dd.support_sha256(pooled_ts),
        p6.label_sha256(pooled_ts, pooled_y),
    )
    comparison = p6.comparison_summary(m1=m1, m2=m2, invariant_pass=True)
    assert comparison["pooled_log_loss_improvement_vs_m1"] > 0
    assert comparison["pooled_brier_improvement_vs_m1"] > 0
    assert comparison["pooled_auc_delta_vs_m1"] >= 0
    assert comparison["precheck_gates"]["all_invariants_pass"] is True


def test_comparison_rejects_timestamp_mismatch() -> None:
    y = np.array([0, 1, 0, 1], dtype=np.int8)
    ts1 = np.arange(4, dtype=np.int64)
    ts2 = ts1 + 1
    f1 = _direction_fold(1, y, np.array([0.4, 0.6, 0.4, 0.6]), ts1)
    base = _direction_fold(1, y, np.array([0.3, 0.7, 0.3, 0.7]), ts2)
    f2 = p6.M2Fold(
        **base.__dict__,
        selected_capacity_id="H1",
        selected_max_leaf_nodes=3,
        selected_max_iter=50,
        inner_capacity_ledger=(),
        model=None,
    )
    m1 = p6.M1Result((f1, f1, f1, f1), {}, "a", "b")
    m2 = p6.M2Result((f2, f2, f2, f2), {}, "a", "b")
    assert _reason(
        p6.comparison_summary, m1=m1, m2=m2, invariant_pass=True
    ) == "comparison_timestamp_alignment_mismatch"


def test_common_shift_rule_matches_frozen_smallest_fold() -> None:
    assert p6.eligible_shared_shifts([159, 64, 126, 224]) == tuple(range(10, 55))


def test_insufficient_null_shifts_fail_closed() -> None:
    assert len(p6.eligible_shared_shifts([20, 20, 20, 20])) < 20


def test_missing_temporal_null_cannot_promote() -> None:
    comparison = {"precheck_gates": {"a": True}}
    gates = p6.final_gates(comparison=comparison, null=None)
    assert gates["temporal_null_run"] is False
    assert all(gates.values()) is False


def test_runtime_guards_are_closed() -> None:
    state = p6.runtime_provenance(model_fit_run=True, p6_run=True)
    assert not any(state["forward_data_guards"].values())
    assert state["threshold_optimization_run"] is False
    assert state["pnl_backtest_run"] is False
    assert state["opportunity_gate_run"] is False
    assert state["t2_composition_run"] is False
    assert state["alternate_model_family_run"] is False
    assert state["deep_model_run"] is False
    assert state["class_weighting_or_resampling_run"] is False
    assert state["calibration_run"] is False


def test_runtime_validator_rejects_forward_open() -> None:
    state = p6.runtime_provenance(model_fit_run=True, p6_run=True)
    state["forward_data_guards"]["sep01_or_later_analytically_opened"] = True
    assert _reason(
        p6.validate_runtime_provenance, state
    ) == "forward_data_guard_violation"


def test_p6_requires_model_fit() -> None:
    assert _reason(
        p6.runtime_provenance,
        model_fit_run=False,
        p6_run=True,
    ) == "p6_requires_model_fit"


def test_canonical_json_is_deterministic() -> None:
    assert p6.canonical_json_bytes({"b": 2, "a": 1}) == p6.canonical_json_bytes(
        {"a": 1, "b": 2}
    )


def test_writer_is_atomic_and_write_once(tmp_path: Path) -> None:
    output = tmp_path / "p6"
    result = p6.write_result_once(
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
        p6.write_result_once,
        output,
        {"synthetic": True},
        require_canonical_output=False,
    ) == "output_directory_already_exists"


def test_real_output_cannot_enter_synthetic_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = tmp_path / "canonical"
    monkeypatch.setattr(p6, "REAL_OUTPUT_DIRECTORY", fake)
    assert _reason(
        p6.write_result_once,
        fake,
        {"synthetic": True},
        require_canonical_output=False,
    ) == "canonical_output_requires_real_mode"


def test_canonical_run_rejects_loader_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = tmp_path / "canonical"
    monkeypatch.setattr(p6, "REAL_OUTPUT_DIRECTORY", fake)
    assert _reason(
        p6.run_p6,
        workspace=tmp_path,
        output_directory=fake,
        execution_commit="a" * 40,
        require_canonical_output=True,
        p3_loader=lambda: {},
    ) == "canonical_dependency_override_forbidden"


def test_test_module_does_not_open_real_data_or_run_campaign() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Name):
            calls.add(fn.id)
        elif isinstance(fn, ast.Attribute):
            calls.add(fn.attr)
    assert "load_authorized_days" not in calls
    assert "run_p6" not in calls
    assert "run_p5" not in calls
    assert "run_p4" not in calls

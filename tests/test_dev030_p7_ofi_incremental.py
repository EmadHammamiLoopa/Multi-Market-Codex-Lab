from __future__ import annotations

import ast
from datetime import date
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from multimarket import dev030_direction_dataset as dd
from multimarket import dev030_p7_ofi_incremental as p7


def _reason(function: Any, *args: Any, **kwargs: Any) -> str:
    with pytest.raises(p7.P7Error) as caught:
        function(*args, **kwargs)
    return caught.value.reason


def _flow_day(day: date, rows: int = 96) -> dd.CandidateDayDataset:
    names = dd.sequence_summary_feature_names(dd.sf.PRICE_BOOK_FLOW)
    ts = day.month * 10**12 + np.arange(rows, dtype=np.int64) * 60_000_000
    y = ((np.arange(rows) + day.month) % 2).astype(np.int8)
    x = np.column_stack(
        [
            np.sin(np.arange(rows) * (0.01 + j * 0.0007))
            + (0.18 + (j % 5) * 0.01) * y
            + j * 0.0001
            for j in range(len(names))
        ]
    )
    s0_names = tuple(dd.sf.block_feature_names(dd.sf.PRICE_BOOK_FLOW))
    s0 = np.zeros((rows, len(s0_names)), dtype=float)
    valid = np.ones(rows, dtype=bool)
    records = tuple(
        {
            "target_valid": True,
            "label": dd.fp.LONG_FIRST if label == 1 else dd.fp.SHORT_FIRST,
            "invalid_reason": None,
            "same_row_ambiguous": False,
        }
        for label in y.tolist()
    )
    return dd.CandidateDayDataset(
        day=day,
        key=p7.SOURCE_KEY,
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
        counts={
            "decision_count": rows,
            "t1_common_support_count": rows,
            "t1_long_common_count": int(np.count_nonzero(y == 1)),
            "t1_short_common_count": int(np.count_nonzero(y == 0)),
        },
        support_hashes={},
    )


def _repr_day(day: date, rows: int = 96) -> p7.RepresentationDay:
    return p7.build_representation_day(_flow_day(day, rows=rows))


def _per_day(rows: int = 96) -> dict[date, p7.RepresentationDay]:
    return {day: _repr_day(day, rows=rows) for day in dd.HISTORICAL_DAYS}


def test_feature_contract_exact_counts() -> None:
    p7.validate_feature_contract()
    assert len(p7.BASELINE_FEATURE_NAMES) == 23
    assert len(p7.OFI_FEATURE_NAMES) == 24
    assert len(p7.AUGMENTED_FEATURE_NAMES) == 47


def test_exact_ofi_source_family() -> None:
    assert p7.OFI_SOURCE_FEATURES == (
        "ofi_l1_250ms",
        "ofi_l1_1s",
        "ofi_l1_3s",
    )


def test_ofi_feature_names_use_only_frozen_stats() -> None:
    assert p7.OFI_FEATURE_NAMES[0] == "ofi_l1_250ms__last"
    assert p7.OFI_FEATURE_NAMES[-1] == "ofi_l1_3s__sign_persistence"
    assert all(
        name.split("__", 1)[0] in p7.OFI_SOURCE_FEATURES
        for name in p7.OFI_FEATURE_NAMES
    )


def test_no_mlofi_or_trade_imbalance_in_augmented_features() -> None:
    joined = " ".join(p7.AUGMENTED_FEATURE_NAMES)
    assert "mlofi" not in joined
    assert "trade_qty" not in joined
    assert "trade_count" not in joined


def test_source_candidate_must_be_price_book_flow() -> None:
    dataset = _flow_day(dd.HISTORICAL_DAYS[0])
    dataset.key = p7.BASELINE_KEY
    assert _reason(
        p7.validate_source_candidate, dataset
    ) == "source_candidate_identity_mismatch"


def test_build_representation_day_selects_only_23_and_47_columns() -> None:
    rep = _repr_day(dd.HISTORICAL_DAYS[0])
    assert rep.c0_values.shape[1] == 23
    assert rep.c1_values.shape[1] == 47
    assert rep.c0_feature_names == p7.BASELINE_FEATURE_NAMES
    assert rep.c1_feature_names == p7.AUGMENTED_FEATURE_NAMES


def test_build_representation_day_uses_flow_t1_support() -> None:
    dataset = _flow_day(dd.HISTORICAL_DAYS[0], rows=10)
    dataset.t1_common_valid[3] = False
    dataset.t1_labels[3] = dd.T1_EXCLUDED
    rep = p7.build_representation_day(dataset)
    assert len(rep.labels) == 9
    assert dd.T1_EXCLUDED not in rep.labels


def test_build_representation_day_rejects_nonfinite_selected_feature() -> None:
    dataset = _flow_day(dd.HISTORICAL_DAYS[0])
    col = dataset.s1_feature_names.index("ofi_l1_1s__mean")
    dataset.s1_values[2, col] = np.nan
    assert _reason(
        p7.build_representation_day, dataset
    ) == "non_finite_selected_features"


def test_probability_metrics_perfect_prediction() -> None:
    y = np.array([0, 1, 0, 1], dtype=np.int8)
    p = np.array([0.01, 0.99, 0.02, 0.98], dtype=float)
    metrics = p7.probability_metrics(y, p)
    assert metrics["roc_auc"] == 1.0
    assert metrics["balanced_accuracy_at_0_5"] == 1.0


def test_probability_metrics_rejects_out_of_range() -> None:
    y = np.array([0, 1], dtype=np.int8)
    assert _reason(
        p7.probability_metrics, y, np.array([0.1, 1.1])
    ) == "metric_probabilities_invalid"


def test_c_grid_is_frozen() -> None:
    assert p7.C_GRID == (0.01, 0.1, 1.0, 10.0)


def test_select_c_probability_first_returns_frozen_c() -> None:
    rng = np.random.default_rng(5)
    xf = rng.normal(size=(180, 23))
    yf = np.tile(np.array([0, 1], dtype=np.int8), 90)
    xv = rng.normal(size=(80, 23))
    yv = np.tile(np.array([0, 1], dtype=np.int8), 40)
    c, ledger = p7.select_c_probability_first(xf, yf, xv, yv)
    assert c in p7.C_GRID
    assert [item["C"] for item in ledger] == list(p7.C_GRID)


def test_logistic_family_has_no_class_weight() -> None:
    model = p7._new_logistic(0.1)
    assert model.solver == "lbfgs"
    assert model.l1_ratio == 0.0
    assert model.class_weight is None
    assert model.max_iter == 1000


def test_fit_fold_c0_and_c1_use_same_validation_support() -> None:
    per_day = _per_day()
    c0 = p7.fit_fold(
        fold=dd.OUTER_FOLDS[0],
        per_day=per_day,
        representation="C0",
    )
    c1 = p7.fit_fold(
        fold=dd.OUTER_FOLDS[0],
        per_day=per_day,
        representation="C1",
    )
    assert np.array_equal(c0.timestamps_us, c1.timestamps_us)
    assert np.array_equal(c0.y_true, c1.y_true)
    assert c0.support_sha256 == c1.support_sha256
    assert c0.label_sha256 == c1.label_sha256


def test_fit_representation_preserves_four_outer_folds() -> None:
    result = p7.fit_representation(_per_day(), "C0")
    assert [fold.fold_id for fold in result.folds] == [1, 2, 3, 4]


def test_prediction_hash_is_deterministic() -> None:
    ts = np.arange(10, dtype=np.int64) * 60_000_000
    y = np.tile(np.array([0, 1], dtype=np.int8), 5)
    p = np.linspace(0.1, 0.9, 10)
    a = p7.prediction_sha256(
        fold_id=1,
        representation="C1",
        timestamps_us=ts,
        y_true=y,
        p_long=p,
    )
    b = p7.prediction_sha256(
        fold_id=1,
        representation="C1",
        timestamps_us=ts,
        y_true=y,
        p_long=p,
    )
    assert a == b


def test_label_hash_changes_if_label_changes() -> None:
    ts = np.arange(4, dtype=np.int64)
    y1 = np.array([0, 1, 0, 1], dtype=np.int8)
    y2 = np.array([0, 1, 1, 1], dtype=np.int8)
    assert p7.label_sha256(ts, y1) != p7.label_sha256(ts, y2)


def test_matched_support_rejects_different_timestamps() -> None:
    per_day = _per_day()
    c0 = p7.fit_representation(per_day, "C0")
    c1 = p7.fit_representation(per_day, "C1")
    first = c1.folds[0]
    shifted = p7.FoldResult(
        **{
            **first.__dict__,
            "timestamps_us": first.timestamps_us + 1,
            "support_sha256": dd.support_sha256(first.timestamps_us + 1),
        }
    )
    bad = p7.RepresentationResult(
        "C1",
        (shifted,) + c1.folds[1:],
        c1.pooled_metrics,
        c1.pooled_support_sha256,
        c1.pooled_label_sha256,
    )
    assert _reason(
        p7.validate_matched_support, c0, bad
    ) == "timestamp_alignment_mismatch"


def test_comparison_summary_has_all_precheck_gates() -> None:
    per_day = _per_day()
    c0 = p7.fit_representation(per_day, "C0")
    c1 = p7.fit_representation(per_day, "C1")
    result = p7.comparison_summary(c0, c1, invariants_pass=True)
    assert "pooled_c1_log_loss_better" in result["precheck_gates"]
    assert "pooled_c1_auc_at_least_056" in result["precheck_gates"]
    assert "leave_one_fold_out_auc_delta_positive" in result["precheck_gates"]


def test_common_shift_rule_requires_ten_rows_on_each_side() -> None:
    assert p7.eligible_shared_shifts([64, 100, 120, 200]) == tuple(range(10, 55))


def test_missing_null_cannot_promote() -> None:
    comparison = {"precheck_gates": {"x": True}}
    gates = p7.final_gates(comparison, None)
    assert gates["temporal_null_run"] is False
    assert all(gates.values()) is False


def test_runtime_provenance_all_prohibited_actions_false() -> None:
    state = p7.runtime_provenance(model_fit_run=True, p7_run=True)
    assert not any(state["forward_data_guards"].values())
    assert state["threshold_optimization_run"] is False
    assert state["pnl_backtest_run"] is False
    assert state["opportunity_gate_run"] is False
    assert state["t2_composition_run"] is False
    assert state["alternate_model_family_run"] is False
    assert state["deep_model_run"] is False
    assert state["feature_family_search_run"] is False
    assert state["class_weighting_or_resampling_run"] is False
    assert state["calibration_run"] is False


def test_runtime_validator_rejects_forward_open() -> None:
    state = p7.runtime_provenance(model_fit_run=True, p7_run=True)
    state["forward_data_guards"]["sep01_or_later_analytically_opened"] = True
    assert _reason(
        p7.validate_runtime_provenance, state
    ) == "forward_data_guard_violation"


def test_canonical_json_rejects_integer_mapping_keys() -> None:
    assert _reason(
        p7.canonical_json_bytes, {"x": {1: "bad"}}
    ) == "json_mapping_key_not_string"


def test_canonical_json_is_deterministic() -> None:
    assert p7.canonical_json_bytes({"b": 2, "a": 1}) == p7.canonical_json_bytes(
        {"a": 1, "b": 2}
    )


def test_writer_is_atomic_and_write_once(tmp_path: Path) -> None:
    output = tmp_path / "p7"
    result = p7.write_result_once(
        output, {"synthetic": True}, require_canonical_output=False
    )
    assert result.artifact_path.is_file()
    assert result.artifact_sha256 == hashlib.sha256(
        result.artifact_path.read_bytes()
    ).hexdigest()
    assert not result.artifact_path.with_name(
        result.artifact_path.name + ".part"
    ).exists()
    assert _reason(
        p7.write_result_once,
        output,
        {"synthetic": True},
        require_canonical_output=False,
    ) == "output_directory_already_exists"


def test_real_output_cannot_enter_synthetic_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = tmp_path / "canonical"
    monkeypatch.setattr(p7, "REAL_OUTPUT_DIRECTORY", fake)
    assert _reason(
        p7.write_result_once,
        fake,
        {"synthetic": True},
        require_canonical_output=False,
    ) == "canonical_output_requires_real_mode"


def test_canonical_run_rejects_loader_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = tmp_path / "canonical"
    monkeypatch.setattr(p7, "REAL_OUTPUT_DIRECTORY", fake)
    assert _reason(
        p7.run_p7,
        workspace=tmp_path,
        output_directory=fake,
        execution_commit="a" * 40,
        require_canonical_output=True,
        p6_loader=lambda: {},
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
    assert "run_p7" not in calls
    assert "run_p6" not in calls

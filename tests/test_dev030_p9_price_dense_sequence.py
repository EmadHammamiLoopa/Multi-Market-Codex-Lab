from __future__ import annotations

import ast
from datetime import date
import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from multimarket import dev030_direction_dataset as dd
from multimarket import dev030_p9_price_dense_sequence as p9
from multimarket import dev030_sequence_features as sf


def _reason(function: Any, *args: Any, **kwargs: Any) -> str:
    with pytest.raises(p9.P9Error) as caught:
        function(*args, **kwargs)
    return caught.value.reason


def _sequence_input(
    *,
    start_us: int = 0,
    seconds: int = 120,
) -> sf.SequenceFeatureInput:
    rows = seconds * 4 + 1
    ts = start_us + np.arange(rows, dtype=np.int64) * sf.GRID_US
    x = np.arange(rows, dtype=np.float64)
    features = {
        "spread_bps": 1.0 + 0.001 * x,
        "microprice_minus_mid_bps": -0.5 + 0.002 * x,
    }
    mid = 100.0 * np.exp(0.00001 * x)
    masks = {
        "book_valid": np.ones(rows, dtype=bool),
        "l0_valid": np.ones(rows, dtype=bool),
    }
    return sf.SequenceFeatureInput(ts, features, mid, masks)


def _candidate_day(
    day: date,
    decision_timestamps_us: np.ndarray,
) -> dd.CandidateDayDataset:
    n = len(decision_timestamps_us)
    labels = (np.arange(n) % 2).astype(np.int8)
    names = p9.BASELINE_FEATURE_NAMES
    s1 = np.column_stack([
        np.sin(np.arange(n) * (0.01 + j * 0.001))
        + 0.2 * labels
        for j in range(len(names))
    ])
    valid = np.ones(n, dtype=bool)
    records = tuple(
        {
            "target_valid": True,
            "label": dd.fp.LONG_FIRST if y == 1 else dd.fp.SHORT_FIRST,
            "invalid_reason": None,
            "same_row_ambiguous": False,
        }
        for y in labels.tolist()
    )
    return dd.CandidateDayDataset(
        day=day,
        key=p9.SELECTED_KEY,
        decision_timestamps_us=decision_timestamps_us,
        target_records=records,
        t1_labels=labels,
        s0_feature_names=tuple(sf.block_feature_names(sf.PRICE)),
        s1_feature_names=names,
        s0_values=np.zeros((n, len(sf.block_feature_names(sf.PRICE)))),
        s1_values=s1,
        s0_valid=valid.copy(),
        s1_valid=valid.copy(),
        common_valid=valid.copy(),
        t1_common_valid=valid.copy(),
        target_future_boundary_valid=valid.copy(),
        s0_boundary_reasons=tuple(None for _ in range(n)),
        s1_boundary_reasons=tuple(None for _ in range(n)),
        target_boundary_reasons=tuple(None for _ in range(n)),
        s0_invalid_reasons=tuple(None for _ in range(n)),
        s1_invalid_reasons=tuple(None for _ in range(n)),
        counts={
            "decision_count": n,
            "t1_common_support_count": n,
            "t1_long_common_count": int(np.count_nonzero(labels == 1)),
            "t1_short_common_count": int(np.count_nonzero(labels == 0)),
        },
        support_hashes={},
    )


def _shape_day(day: date, rows: int = 96) -> p9.DenseDay:
    ts = (
        day.month * 10**12
        + np.arange(rows, dtype=np.int64) * 60_000_000
        + 40_000_000
    )
    labels = ((np.arange(rows) + day.month) % 2).astype(np.int8)
    x0 = np.column_stack([
        np.sin(np.arange(rows) * (0.01 + j * 0.0007))
        + (0.15 + (j % 4) * 0.01) * labels
        for j in range(p9.EXPECTED_BASELINE_FEATURE_COUNT)
    ])
    dense = np.column_stack([
        np.cos(np.arange(rows) * (0.02 + j * 0.0009))
        + (0.04 + (j % 3) * 0.005) * labels
        for j in range(p9.EXPECTED_DENSE_SEQUENCE_FEATURE_COUNT)
    ])
    x1 = np.column_stack((x0, shape))
    return p9.DenseDay(
        day=day,
        timestamps_us=ts,
        labels=labels,
        c0_values=x0,
        c1_values=x1,
        c0_feature_names=p9.BASELINE_FEATURE_NAMES,
        c1_feature_names=p9.AUGMENTED_FEATURE_NAMES,
        support_sha256=dd.support_sha256(ts),
        label_sha256=p9.label_sha256(ts, labels),
    )


def _per_day(rows: int = 96) -> dict[date, p9.DenseDay]:
    return {day: _shape_day(day, rows=rows) for day in dd.HISTORICAL_DAYS}


def test_feature_contract_exact_counts() -> None:
    p9.validate_feature_contract()
    assert len(p9.BASELINE_FEATURE_NAMES) == 23
    assert len(p9.DENSE_SEQUENCE_FEATURE_NAMES) == 96
    assert len(p9.AUGMENTED_FEATURE_NAMES) == 119


def test_lag_family_is_exact_and_has_no_current_duplicate() -> None:
    assert p9.LAG_SECONDS == tuple(range(32, 0, -1))
    assert p9.PRICE_LAG_PRIMITIVES == (
        "spread_bps",
        "microprice_minus_mid_bps",
        sf.DERIVED_MID_RETURN,
    )
    assert all("__lag_0s" not in name for name in p9.DENSE_SEQUENCE_FEATURE_NAMES)


def test_dense_sequence_feature_order_is_primitive_then_lag() -> None:
    assert p9.DENSE_SEQUENCE_FEATURE_NAMES[:4] == (
        "spread_bps__lag_32s",
        "spread_bps__lag_31s",
        "spread_bps__lag_30s",
        "spread_bps__lag_29s",
    )
    assert p9.DENSE_SEQUENCE_FEATURE_NAMES[31] == "spread_bps__lag_1s"
    assert p9.DENSE_SEQUENCE_FEATURE_NAMES[32] == "microprice_minus_mid_bps__lag_32s"
    assert p9.DENSE_SEQUENCE_FEATURE_NAMES[-1] == "mid_log_return_250ms_bps__lag_1s"


def test_extract_dense_sequence_matrix_exact_values() -> None:
    inp = _sequence_input(seconds=100)
    decisions = np.array([40_000_000, 60_000_000], dtype=np.int64)
    matrix = p9.extract_dense_sequence_matrix(inp, decisions)
    assert matrix.shape == (2, 96)

    ts = np.asarray(inp.timestamps_us)
    spread = np.asarray(inp.features["spread_bps"])
    expected = []
    for lag in p9.LAG_SECONDS:
        idx = int(np.where(ts == decisions[0] - lag * 1_000_000)[0][0])
        expected.append(spread[idx])
    assert np.allclose(matrix[0, :32], expected)


def test_derived_return_lag_is_causal() -> None:
    inp = _sequence_input(seconds=100)
    decisions = np.array([40_000_000], dtype=np.int64)
    matrix = p9.extract_dense_sequence_matrix(inp, decisions)
    ts = np.asarray(inp.timestamps_us)
    mid = np.asarray(inp.mid)
    lag_ts = decisions[0] - 32_000_000
    idx = int(np.where(ts == lag_ts)[0][0])
    expected = 10_000.0 * np.log(mid[idx] / mid[idx - 1])
    assert matrix[0, 8] == pytest.approx(expected)


def test_extract_dense_sequence_rejects_missing_lag_timestamp() -> None:
    inp = _sequence_input(seconds=100)
    raw_ts = np.asarray(inp.timestamps_us)
    keep = raw_ts != 8_000_000
    broken = sf.SequenceFeatureInput(
        raw_ts[keep],
        {k: np.asarray(v)[keep] for k, v in inp.features.items()},
        np.asarray(inp.mid)[keep],
        {k: np.asarray(v)[keep] for k, v in inp.validity_masks.items()},
    )
    assert _reason(
        p9.extract_dense_sequence_matrix,
        broken,
        np.array([40_000_000], dtype=np.int64),
    ) == "lag_timestamp_missing"


def test_extract_dense_sequence_rejects_invalid_lag_mask() -> None:
    inp = _sequence_input(seconds=100)
    masks = {k: np.asarray(v).copy() for k, v in inp.validity_masks.items()}
    idx = int(np.where(np.asarray(inp.timestamps_us) == 8_000_000)[0][0])
    masks["l0_valid"][idx] = False
    broken = sf.SequenceFeatureInput(
        inp.timestamps_us,
        inp.features,
        inp.mid,
        masks,
    )
    assert _reason(
        p9.extract_dense_sequence_matrix,
        broken,
        np.array([40_000_000], dtype=np.int64),
    ) == "lag_snapshot_invalid_required_mask"


def test_build_shape_day_preserves_candidate_support() -> None:
    inp = _sequence_input(seconds=100)
    decisions = np.array([40_000_000, 60_000_000], dtype=np.int64)
    candidate = _candidate_day(dd.HISTORICAL_DAYS[0], decisions)
    dense = p9.build_shape_day(candidate, inp)
    assert np.array_equal(dense.timestamps_us, decisions)
    assert dense.c0_values.shape == (2, 23)
    assert dense.c1_values.shape == (2, 119)


def test_build_shape_day_rejects_nonfinite_baseline() -> None:
    inp = _sequence_input(seconds=100)
    decisions = np.array([40_000_000, 60_000_000], dtype=np.int64)
    candidate = _candidate_day(dd.HISTORICAL_DAYS[0], decisions)
    candidate.s1_values[0, 0] = np.nan
    assert _reason(p9.build_shape_day, candidate, inp) == "baseline_features_non_finite"


def test_probability_metrics_perfect_prediction() -> None:
    y = np.array([0, 1, 0, 1], dtype=np.int8)
    p = np.array([0.01, 0.99, 0.02, 0.98])
    result = p9.probability_metrics(y, p)
    assert result["roc_auc"] == 1.0
    assert result["balanced_accuracy_at_0_5"] == 1.0


def test_c_grid_is_frozen() -> None:
    assert p9.C_GRID == (0.01, 0.1, 1.0, 10.0)


def test_select_c_probability_first_returns_frozen_c() -> None:
    rng = np.random.default_rng(8)
    xf = rng.normal(size=(160, 23))
    yf = np.tile(np.array([0, 1], dtype=np.int8), 80)
    xv = rng.normal(size=(80, 23))
    yv = np.tile(np.array([0, 1], dtype=np.int8), 40)
    c, ledger = p9.select_c_probability_first(xf, yf, xv, yv)
    assert c in p9.C_GRID
    assert [row["C"] for row in ledger] == list(p9.C_GRID)
    assert all("binary_log_loss" in row for row in ledger)


def test_logistic_family_has_no_class_weight() -> None:
    model = p9._new_logistic(0.1)
    assert model.solver == "lbfgs"
    assert model.class_weight is None
    assert model.l1_ratio == 0.0


def test_fit_fold_c0_c1_use_same_support() -> None:
    per_day = _per_day()
    c0 = p9.fit_fold(
        fold=dd.OUTER_FOLDS[0],
        per_day=per_day,
        representation="C0",
    )
    c1 = p9.fit_fold(
        fold=dd.OUTER_FOLDS[0],
        per_day=per_day,
        representation="C1",
    )
    assert np.array_equal(c0.timestamps_us, c1.timestamps_us)
    assert np.array_equal(c0.y_true, c1.y_true)
    assert c0.support_sha256 == c1.support_sha256
    assert c0.label_sha256 == c1.label_sha256


def test_fit_representation_has_four_outer_folds() -> None:
    result = p9.fit_representation(_per_day(), "C0")
    assert [fold.fold_id for fold in result.folds] == [1, 2, 3, 4]


def test_prediction_hash_is_deterministic() -> None:
    ts = np.arange(10, dtype=np.int64) * 60_000_000
    y = np.tile(np.array([0, 1], dtype=np.int8), 5)
    p = np.linspace(0.1, 0.9, 10)
    a = p9.prediction_sha256(
        fold_id=1,
        representation="C1",
        timestamps_us=ts,
        y_true=y,
        p_long=p,
    )
    b = p9.prediction_sha256(
        fold_id=1,
        representation="C1",
        timestamps_us=ts,
        y_true=y,
        p_long=p,
    )
    assert a == b


def test_label_hash_changes_when_label_changes() -> None:
    ts = np.arange(4, dtype=np.int64)
    y1 = np.array([0, 1, 0, 1], dtype=np.int8)
    y2 = np.array([0, 1, 1, 1], dtype=np.int8)
    assert p9.label_sha256(ts, y1) != p9.label_sha256(ts, y2)


def test_matched_support_rejects_timestamp_change() -> None:
    per_day = _per_day()
    c0 = p9.fit_representation(per_day, "C0")
    c1 = p9.fit_representation(per_day, "C1")
    first = c1.folds[0]
    changed = p9.FoldResult(
        **{
            **first.__dict__,
            "timestamps_us": first.timestamps_us + 1,
            "support_sha256": dd.support_sha256(first.timestamps_us + 1),
        }
    )
    bad = p9.RepresentationResult(
        "C1",
        (changed,) + c1.folds[1:],
        c1.pooled_metrics,
        c1.pooled_support_sha256,
        c1.pooled_label_sha256,
    )
    assert _reason(
        p9.validate_matched_support,
        c0,
        bad,
    ) == "timestamp_alignment_mismatch"


def test_expected_support_validator_rejects_synthetic_support() -> None:
    result = p9.fit_representation(_per_day(), "C0")
    assert _reason(
        p9.validate_expected_p3_support,
        result,
    ) == "p3_fold_support_mismatch"


def test_exact_p8_c0_reproduction_accepts_matching_payload() -> None:
    c0 = p9.fit_representation(_per_day(), "C0")
    payload = {
        "status": "FAIL_PRICE_TEMPORAL_SHAPE_NO_STABLE_INCREMENTAL_VALUE",
        "c0_price_s1": {
            "folds": [p9._fold_public(fold) for fold in c0.folds],
            "pooled": c0.pooled_metrics,
        },
    }
    p9.validate_exact_p8_c0_reproduction(c0, payload)


def test_exact_p8_c0_reproduction_rejects_prediction_hash_change() -> None:
    c0 = p9.fit_representation(_per_day(), "C0")
    folds = [p9._fold_public(fold) for fold in c0.folds]
    folds[0]["prediction_sha256"] = "0" * 64
    payload = {
        "status": "FAIL_PRICE_TEMPORAL_SHAPE_NO_STABLE_INCREMENTAL_VALUE",
        "c0_price_s1": {
            "folds": folds,
            "pooled": c0.pooled_metrics,
        },
    }
    assert _reason(
        p9.validate_exact_p8_c0_reproduction,
        c0,
        payload,
    ) == "p8_c0_reproduction_mismatch"


def test_comparison_has_required_gates() -> None:
    per_day = _per_day()
    c0 = p9.fit_representation(per_day, "C0")
    c1 = p9.fit_representation(per_day, "C1")
    result = p9.comparison_summary(c0, c1, invariants_pass=True)
    assert "pooled_c1_log_loss_better" in result["precheck_gates"]
    assert "pooled_c1_auc_at_least_056" in result["precheck_gates"]
    assert "exact_p3_support_pass" in result["precheck_gates"]
    assert "leave_one_fold_out_auc_delta_positive" in result["precheck_gates"]


def test_common_shift_rule_matches_p3_support_minimum() -> None:
    assert p9.eligible_shared_shifts([159, 64, 126, 224]) == tuple(range(10, 55))


def test_missing_null_cannot_promote() -> None:
    gates = p9.final_gates({"precheck_gates": {"x": True}}, None)
    assert gates["temporal_null_run"] is False
    assert all(gates.values()) is False


def test_runtime_provenance_prohibits_search_and_forward() -> None:
    state = p9.runtime_provenance(model_fit_run=True, p9_run=True)
    assert not any(state["forward_data_guards"].values())
    assert state["lag_search_run"] is False
    assert state["feature_family_search_run"] is False
    assert state["alternate_model_family_run"] is False
    assert state["deep_model_run"] is False
    assert state["pnl_backtest_run"] is False


def test_runtime_validator_rejects_lag_search() -> None:
    state = p9.runtime_provenance(model_fit_run=True, p9_run=True)
    state["lag_search_run"] = True
    assert _reason(
        p9.validate_runtime_provenance,
        state,
    ) == "prohibited_runtime_activity"


def test_canonical_json_rejects_integer_mapping_key() -> None:
    assert _reason(
        p9.canonical_json_bytes,
        {"x": {1: "bad"}},
    ) == "json_mapping_key_not_string"


def test_canonical_json_is_deterministic() -> None:
    assert p9.canonical_json_bytes({"b": 2, "a": 1}) == p9.canonical_json_bytes(
        {"a": 1, "b": 2}
    )


def test_writer_atomic_and_write_once(tmp_path: Path) -> None:
    output = tmp_path / "p9"
    result = p9.write_result_once(
        output,
        {"synthetic": True},
        require_canonical_output=False,
    )
    assert result.artifact_sha256 == hashlib.sha256(
        result.artifact_path.read_bytes()
    ).hexdigest()
    assert not result.artifact_path.with_name(
        result.artifact_path.name + ".part"
    ).exists()
    assert _reason(
        p9.write_result_once,
        output,
        {"synthetic": True},
        require_canonical_output=False,
    ) == "output_directory_already_exists"


def test_real_output_cannot_enter_synthetic_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = tmp_path / "canonical"
    monkeypatch.setattr(p9, "REAL_OUTPUT_DIRECTORY", fake)
    assert _reason(
        p9.write_result_once,
        fake,
        {"synthetic": True},
        require_canonical_output=False,
    ) == "canonical_output_requires_real_mode"


def test_canonical_run_rejects_dependency_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = tmp_path / "canonical"
    monkeypatch.setattr(p9, "REAL_OUTPUT_DIRECTORY", fake)
    assert _reason(
        p9.run_p9,
        workspace=tmp_path,
        output_directory=fake,
        execution_commit="a" * 40,
        require_canonical_output=True,
        p7_loader=lambda: {},
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
    assert "run_p9" not in calls
    assert "run_p7" not in calls

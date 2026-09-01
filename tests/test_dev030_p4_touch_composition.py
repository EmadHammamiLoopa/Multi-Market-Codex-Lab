from __future__ import annotations

from datetime import date
import ast
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from multimarket import dev030_direction_dataset as dd
from multimarket import dev030_p4_touch_composition as p4


def _reason(function: Any, *args: Any, **kwargs: Any) -> str:
    with pytest.raises(p4.P4Error) as caught:
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
        dd.fp.LONG_FIRST,
        dd.fp.SHORT_FIRST,
        dd.fp.NONE,
        dd.fp.NONE,
    ),
    invalid_last: bool = False,
) -> dd.CandidateDayDataset:
    n = len(labels)
    ts = (
        int(date(day.year, day.month, day.day).strftime("%s")) * 1_000_000
        if False
        else np.arange(n, dtype=np.int64) * 60_000_000
        + (day.month * 10**12)
    )
    records = []
    for i, label in enumerate(labels):
        if invalid_last and i == n - 1:
            records.append(_record(None, valid=False))
        else:
            records.append(_record(label, valid=True))

    s0_names = tuple(dd.sf.block_feature_names("PRICE"))
    s1_names = dd.sequence_summary_feature_names("PRICE")
    s0 = np.column_stack(
        [
            np.linspace(1.0, 2.0, n),
            np.linspace(-1.0, 1.0, n),
            np.linspace(-0.5, 0.5, n),
        ]
    )
    if s0.shape[1] != len(s0_names):
        # Build exact width robustly if PRICE feature count changes.
        s0 = np.tile(np.arange(1, len(s0_names) + 1, dtype=np.float64), (n, 1))
        s0 += np.arange(n, dtype=np.float64)[:, None] * 0.01

    s1 = np.tile(
        np.arange(1, len(s1_names) + 1, dtype=np.float64),
        (n, 1),
    )
    s1 += np.arange(n, dtype=np.float64)[:, None] * 0.01

    common = np.ones(n, dtype=bool)
    future = np.ones(n, dtype=bool)
    t1 = np.asarray(
        [label in (dd.fp.LONG_FIRST, dd.fp.SHORT_FIRST) for label in labels],
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
    return dd.CandidateDayDataset(
        day=day,
        key=p4.SELECTED_KEY,
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
        counts={},
        support_hashes={},
    )


def _synthetic_t2_days(rows: int = 80) -> dict[date, p4.T2DayDataset]:
    result = {}
    for month, day in enumerate(dd.HISTORICAL_DAYS, start=1):
        ts = month * 10**12 + np.arange(rows, dtype=np.int64) * 60_000_000
        y = ((np.arange(rows) + month) % 4 == 0).astype(np.int8)
        x0 = np.column_stack(
            (np.sin(np.arange(rows) * 0.13), np.cos(np.arange(rows) * 0.07))
        )
        x1 = np.column_stack(
            (
                y.astype(np.float64) * 2.5 + np.sin(np.arange(rows) * 0.03),
                np.cos(np.arange(rows) * 0.05),
            )
        )
        result[day] = p4.T2DayDataset(
            day=day,
            timestamps_us=ts,
            labels=y,
            s0_values=x0,
            s1_values=x1,
            s0_feature_names=("s0a", "s0b"),
            s1_feature_names=("s1a", "s1b"),
            valid_mask_on_candidate=np.ones(rows, dtype=bool),
            support_sha256=dd.support_sha256(ts),
            touch_count=int(np.count_nonzero(y == 1)),
            none_count=int(np.count_nonzero(y == 0)),
        )
    return result


def test_selected_configuration_is_exact() -> None:
    assert p4.SELECTED_TARGET.target_id == "A"
    assert p4.SELECTED_TARGET.horizon_seconds == 120
    assert p4.SELECTED_TARGET.barrier_bps == 16
    assert p4.SELECTED_WINDOW_SECONDS == 32
    assert p4.SELECTED_BLOCK == "PRICE"


def test_build_t2_maps_direction_to_touch_and_none_to_none() -> None:
    dataset = _candidate_day(dd.HISTORICAL_DAYS[0])
    result = p4.build_t2_day(dataset)
    assert result.labels.tolist() == [1, 1, 0, 0]
    assert result.touch_count == 2
    assert result.none_count == 2


def test_build_t2_excludes_invalid_target() -> None:
    dataset = _candidate_day(dd.HISTORICAL_DAYS[0], invalid_last=True)
    result = p4.build_t2_day(dataset)
    assert result.labels.tolist() == [1, 1, 0]
    assert len(result.timestamps_us) == 3


def test_wrong_candidate_identity_fails() -> None:
    dataset = _candidate_day(dd.HISTORICAL_DAYS[0])
    dataset.key = dd.CandidateKey(dd.FROZEN_TARGETS[1], 32, "PRICE")
    assert _reason(p4.build_t2_day, dataset) == "selected_candidate_identity_mismatch"


def test_probability_metrics_known_values() -> None:
    y = np.asarray([0, 0, 1, 1], dtype=np.int8)
    p = np.asarray([0.1, 0.2, 0.8, 0.9], dtype=np.float64)
    metrics = p4.probability_metrics(y, p)
    assert metrics["average_precision"] == 1.0
    assert metrics["roc_auc"] == 1.0
    assert metrics["balanced_accuracy_at_0_5"] == 1.0
    assert metrics["confusion_matrix_none_touch_at_0_5"] == [[2, 0], [0, 2]]


def test_probability_metrics_rejects_nonfinite() -> None:
    assert _reason(
        p4.probability_metrics,
        np.asarray([0, 1]),
        np.asarray([0.1, np.nan]),
    ) == "invalid_touch_probabilities"


def test_logistic_configuration_and_c_grid() -> None:
    model = p4._new_logistic(0.1)
    assert p4.C_GRID == (0.01, 0.1, 1.0, 10.0)
    assert model.C == 0.1
    assert model.solver == "lbfgs"
    assert model.l1_ratio == 0.0
    assert model.class_weight is None
    assert model.max_iter == 1000


def test_select_c_tie_prefers_smaller_c() -> None:
    x_fit = np.zeros((40, 2), dtype=np.float64)
    y_fit = np.asarray([0, 1] * 20, dtype=np.int8)
    x_val = np.zeros((40, 2), dtype=np.float64)
    y_val = np.asarray([0, 1] * 20, dtype=np.int8)
    selected, ledger = p4.select_c(x_fit, y_fit, x_val, y_val)
    assert selected == 0.01
    assert [x["C"] for x in ledger] == list(p4.C_GRID)


def test_prevalence_fold_uses_training_prevalence() -> None:
    result = p4.prevalence_fold(
        fold_id=1,
        y_train=np.asarray([0, 0, 0, 1], dtype=np.int8),
        y_validation=np.asarray([0, 1], dtype=np.int8),
        validation_timestamps_us=np.asarray([1, 2], dtype=np.int64),
    )
    assert np.allclose(result.p_touch, 0.25)


def test_fit_t2_uses_four_outer_folds() -> None:
    result = p4.fit_t2(_synthetic_t2_days())
    assert len(result.b0_folds) == 4
    assert len(result.s0_folds) == 4
    assert len(result.s1_folds) == 4
    assert [f.fold_id for f in result.s1_folds] == [1, 2, 3, 4]


def test_synthetic_s1_beats_s0() -> None:
    result = p4.fit_t2(_synthetic_t2_days())
    assert result.s1_pooled["roc_auc"] > result.s0_pooled["roc_auc"]
    assert result.s1_pooled["average_precision"] > result.s0_pooled["average_precision"]


def test_null_shift_rule_exact() -> None:
    assert p4.eligible_shared_shifts([40, 40, 40, 40]) == tuple(range(10, 31))


def test_temporal_null_requires_four_folds() -> None:
    days = _synthetic_t2_days()
    result = p4.fit_t2(days)
    assert _reason(p4.t2_temporal_null, result.s1_folds[:3]) == "outer_fold_count_mismatch"


def test_t2_null_is_deterministic() -> None:
    result = p4.fit_t2(_synthetic_t2_days())
    first = p4.t2_temporal_null(result.s1_folds)
    second = p4.t2_temporal_null(result.s1_folds)
    assert first == second


def test_missing_null_cannot_promote() -> None:
    result = p4.fit_t2(_synthetic_t2_days())
    assert p4.t2_is_eligible(result, None) is False


def test_compose_probabilities_exact() -> None:
    matrix = p4.compose_probabilities(
        np.asarray([0.8]),
        np.asarray([0.75]),
    )
    assert np.allclose(matrix, [[0.2, 0.2, 0.6]])
    assert np.allclose(matrix.sum(axis=1), 1.0)


def test_compose_probabilities_rejects_invalid() -> None:
    assert _reason(
        p4.compose_probabilities,
        np.asarray([1.1]),
        np.asarray([0.5]),
    ) == "invalid_composition_probability"


def test_three_class_label_order_none_short_long() -> None:
    candidate = _candidate_day(dd.HISTORICAL_DAYS[0])
    t2 = p4.build_t2_day(candidate)
    labels = p4.three_class_labels(candidate, t2)
    assert labels.tolist() == [2, 1, 0, 0]


def test_multiclass_metrics_perfect_probabilities() -> None:
    y = np.asarray([0, 1, 2, 0, 1, 2], dtype=np.int8)
    p = np.eye(3)[y] * 0.98 + 0.02 / 3.0
    p /= p.sum(axis=1, keepdims=True)
    metrics = p4.multiclass_probability_metrics(y, p)
    assert metrics["argmax_balanced_accuracy"] == 1.0
    assert metrics["argmax_confusion_matrix_none_short_long"] == [
        [2, 0, 0],
        [0, 2, 0],
        [0, 0, 2],
    ]


def test_directional_training_prevalence() -> None:
    per_day = {
        day: _candidate_day(day)
        for day in dd.HISTORICAL_DAYS
    }
    value = p4.directional_training_prevalence(per_day, dd.HISTORICAL_DAYS[:2])
    assert value == 0.5


def test_composition_baselines_are_exact() -> None:
    y = np.asarray([0, 1, 2], dtype=np.int8)
    train_prev = np.asarray([0.7, 0.15, 0.15], dtype=np.float64)
    p_touch = np.asarray([0.2, 0.5, 0.8], dtype=np.float64)
    p_long = np.asarray([0.25, 0.5, 0.75], dtype=np.float64)
    c0, c1, c2 = p4.composition_baselines(
        y_validation=y,
        training_class_prevalence=train_prev,
        p_touch=p_touch,
        training_p_long_given_touch=0.4,
        p_long_given_touch=p_long,
    )
    assert np.allclose(c0, np.tile(train_prev, (3, 1)))
    assert np.allclose(c1.sum(axis=1), 1.0)
    assert np.allclose(c2.sum(axis=1), 1.0)
    assert not np.array_equal(c1, c2)


def test_frozen_t1_constants_match_p3_result() -> None:
    assert p4.FROZEN_T1_C_BY_FOLD == {1: 10.0, 2: 10.0, 3: 0.1, 4: 0.01}
    assert p4.FROZEN_T1_PREDICTION_SHA256_BY_FOLD[1] == (
        "e03d233bff936b49a0452994497f32ca5ecbe52c1f490d855fe8d06dbfa9dcf4"
    )


def test_runtime_provenance_guards_are_closed() -> None:
    state = p4.runtime_provenance(
        model_fit_run=True,
        t2_run=True,
        composition_run=False,
    )
    assert not any(state["forward_data_guards"].values())
    assert state["threshold_optimization_run"] is False
    assert state["pnl_backtest_run"] is False
    assert state["opportunity_gate_run"] is False


def test_composition_requires_t2() -> None:
    assert _reason(
        p4.runtime_provenance,
        model_fit_run=True,
        t2_run=False,
        composition_run=True,
    ) == "composition_requires_t2"


def test_canonical_json_deterministic() -> None:
    assert p4.canonical_json_bytes({"b": 2, "a": 1}) == p4.canonical_json_bytes(
        {"a": 1, "b": 2}
    )


def test_test_module_has_no_real_loader_calls() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name):
            called_names.add(function.id)
        elif isinstance(function, ast.Attribute):
            called_names.add(function.attr)

    assert "load_authorized_days" not in called_names
    assert "run_campaign1" not in called_names
    assert "run_materialization" not in called_names

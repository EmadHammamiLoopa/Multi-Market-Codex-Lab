from __future__ import annotations

from dataclasses import replace
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from multimarket import dev030_direction_dataset as dd
from multimarket import dev030_p3_direction as p3


def _reason(function: Any, *args: Any, **kwargs: Any) -> str:
    with pytest.raises(p3.Campaign1Error) as caught:
        function(*args, **kwargs)
    return caught.value.reason


def _spec(
    target_id: str = "A",
    window_seconds: int = 8,
    block: str = "PRICE_BOOK_FLOW",
) -> p3.CandidateSpec:
    target = next(item for item in dd.FROZEN_TARGETS if item.target_id == target_id)
    return p3.CandidateSpec(
        target.target_id,
        int(target.horizon_seconds),
        int(target.barrier_bps),
        int(window_seconds),
        block,
    )


def _day_start_us(day: Any) -> int:
    return int(
        datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp()
        * 1_000_000
    )


def _candidate_day(
    day: Any,
    *,
    spec: p3.CandidateSpec | None = None,
    rows: int = 80,
    s1_strength: float = 4.0,
) -> dd.CandidateDayDataset:
    spec = _spec() if spec is None else spec
    key = next(
        key
        for key in (
            dd.CandidateKey(target, spec.window_seconds, spec.block)
            for target in dd.FROZEN_TARGETS
        )
        if key.target.target_id == spec.target_id
        and key.target.horizon_seconds == spec.horizon_seconds
        and key.target.barrier_bps == spec.barrier_bps
    )
    timestamps = _day_start_us(day) + (
        np.arange(rows, dtype=np.int64) + 1
    ) * dd.DECISION_STEP_US
    labels = (np.arange(rows) % 2).astype(np.int8)

    # S0 intentionally contains only weak/noisy information but includes all M0
    # control features required by the frozen design.
    phase = np.arange(rows, dtype=np.float64)
    s0_names = (
        "microprice_minus_mid_bps",
        "obi_l1",
        "ofi_l1_1s",
        "noise",
    )
    s0 = np.column_stack(
        (
            np.sin(phase * 0.31),
            np.cos(phase * 0.23),
            np.sin(phase * 0.17 + 0.4),
            np.cos(phase * 0.11),
        )
    )

    # S1 carries a deterministic synthetic temporal signal.  This is only a
    # fixture for model plumbing; it is not market evidence.
    signed = (labels * 2 - 1).astype(np.float64)
    s1_names = ("synthetic_temporal_signal", "synthetic_aux")
    s1 = np.column_stack(
        (
            s1_strength * signed + 0.05 * np.sin(phase),
            np.cos(phase * 0.07),
        )
    )

    mask = np.ones(rows, dtype=bool)
    target_records = tuple(
        {
            "target_valid": True,
            "label": "LONG_FIRST" if int(label) == 1 else "SHORT_FIRST",
            "invalid_reason": None,
            "same_row_ambiguous": False,
        }
        for label in labels
    )
    zero_reason = tuple(None for _ in range(rows))
    return dd.CandidateDayDataset(
        day=day,
        key=key,
        decision_timestamps_us=timestamps,
        target_records=target_records,
        t1_labels=labels,
        s0_feature_names=s0_names,
        s1_feature_names=s1_names,
        s0_values=s0,
        s1_values=s1,
        s0_valid=mask.copy(),
        s1_valid=mask.copy(),
        common_valid=mask.copy(),
        t1_common_valid=mask.copy(),
        target_future_boundary_valid=mask.copy(),
        s0_boundary_reasons=zero_reason,
        s1_boundary_reasons=zero_reason,
        target_boundary_reasons=zero_reason,
        s0_invalid_reasons=zero_reason,
        s1_invalid_reasons=zero_reason,
        counts={},
        support_hashes={},
    )


def _per_day(
    *,
    spec: p3.CandidateSpec | None = None,
    rows: int = 80,
    s1_strength: float = 4.0,
) -> dict[Any, dd.CandidateDayDataset]:
    return {
        day: _candidate_day(day, spec=spec, rows=rows, s1_strength=s1_strength)
        for day in dd.HISTORICAL_DAYS
    }


def _fold_result(
    fold_id: int,
    *,
    ba: float = 0.60,
    macro_f1: float = 0.60,
    pred_long: int = 20,
    pred_short: int = 20,
    support: int = 40,
) -> p3.RepresentationFoldResult:
    y = np.asarray(([0, 1] * (support // 2))[:support], dtype=np.int8)
    pred = y.copy()
    probs = np.where(pred == 1, 0.8, 0.2).astype(np.float64)
    ts = fold_id * 10**12 + np.arange(support, dtype=np.int64) * 60_000_000
    metrics = {
        "support": support,
        "long_count": support // 2,
        "short_count": support - support // 2,
        "predicted_long_count": pred_long,
        "predicted_short_count": pred_short,
        "balanced_accuracy": ba,
        "macro_f1": macro_f1,
        "mcc": 0.2,
        "short": {"precision": 0.6, "recall": 0.6, "f1": 0.6, "support": support // 2},
        "long": {"precision": 0.6, "recall": 0.6, "f1": 0.6, "support": support // 2},
        "confusion_matrix_short_long": [[10, 10], [10, 10]],
        "roc_auc_diagnostic": 0.6,
    }
    return p3.RepresentationFoldResult(
        fold_id,
        0.1,
        support,
        metrics,
        hashlib.sha256(str(fold_id).encode()).hexdigest(),
        y,
        pred,
        probs,
        ts,
    )


def _synthetic_support_contract() -> dict[str, Any]:
    per_day = [
        {
            "date": day.isoformat(),
            "t1_common_support_count": 40,
            "t1_long_common_count": 20,
            "t1_short_common_count": 20,
            "support_sha256": {
                "native_s0_support_sha256": "1" * 64,
                "native_s1_support_sha256": "2" * 64,
                "common_support_sha256": "3" * 64,
                "t1_common_support_sha256": "4" * 64,
            },
        }
        for day in dd.HISTORICAL_DAYS
    ]
    folds = [
        {
            "fold_id": int(fold.fold_id),
            "train_days": [day.isoformat() for day in fold.train_days],
            "validation_day": fold.validation_day.isoformat(),
            "train_t1_count": 40 * len(fold.train_days),
            "validation_t1_count": 40,
            "train_class_counts": {
                "long": 20 * len(fold.train_days),
                "short": 20 * len(fold.train_days),
            },
            "validation_class_counts": {"long": 20, "short": 20},
            "support_sha256": {
                "train_native_s0_support_sha256": "5" * 64,
                "train_native_s1_support_sha256": "6" * 64,
                "train_common_support_sha256": "7" * 64,
                "train_t1_common_support_sha256": "8" * 64,
                "validation_native_s0_support_sha256": "9" * 64,
                "validation_native_s1_support_sha256": "a" * 64,
                "validation_common_support_sha256": "b" * 64,
                "validation_t1_common_support_sha256": "c" * 64,
                "train_support_sha256": "8" * 64,
                "validation_support_sha256": "c" * 64,
            },
        }
        for fold in dd.OUTER_FOLDS
    ]
    return {"per_day": per_day, "folds": folds}


def _model_result(
    *,
    spec: p3.CandidateSpec | None = None,
    s1_ba: float = 0.60,
    delta: float = 0.03,
    all_precheck: bool = True,
) -> p3.CandidateModelResult:
    spec = _spec() if spec is None else spec
    s1_folds = tuple(_fold_result(i + 1, ba=s1_ba) for i in range(4))
    s0_folds = tuple(_fold_result(i + 1, ba=s1_ba - delta) for i in range(4))
    gates = {
        "primary_target": spec.target_id in p3.PROMOTABLE_TARGET_IDS,
        "pooled_ba_at_least_054": True,
        "median_fold_ba_gt_050": True,
        "at_least_3_of_4_fold_ba_gt_050": True,
        "pooled_delta_ba_at_least_002": True,
        "at_least_3_of_4_positive_fold_delta": True,
        "both_classes_predicted_each_fold": True,
        "pooled_predicted_minority_fraction_at_least_010": True,
        "leave_one_fold_out_delta_positive": True,
    }
    if not all_precheck:
        gates["pooled_ba_at_least_054"] = False
    pooled_s1 = dict(s1_folds[0].metrics)
    pooled_s0 = dict(s0_folds[0].metrics)
    pooled_s1["balanced_accuracy"] = s1_ba
    pooled_s1["macro_f1"] = 0.60
    pooled_s0["balanced_accuracy"] = s1_ba - delta
    pooled_s0["macro_f1"] = 0.56
    return p3.CandidateModelResult(
        spec=spec,
        feature_count_s0=4,
        feature_count_s1=2,
        m0_folds=tuple({"fold_id": i + 1, "controls": {}} for i in range(4)),
        s0_folds=s0_folds,
        s1_folds=s1_folds,
        s0_pooled=pooled_s0,
        s1_pooled=pooled_s1,
        fold_delta_ba=(delta, delta, delta, delta),
        pooled_delta_ba=delta,
        pooled_delta_macro_f1=0.04,
        leave_one_fold_out_delta_ba=(delta, delta, delta, delta),
        precheck_pass=all(gates.values()),
        precheck_gates=gates,
        support_contract=_synthetic_support_contract(),
    )


def _passing_null(observed: float = 0.60) -> p3.TemporalNullResult:
    return p3.TemporalNullResult(
        eligible_shifts=tuple(range(10, 31)),
        null_balanced_accuracy=tuple([0.50] * 21),
        null_q95=0.50,
        empirical_p=1 / 22,
        observed_balanced_accuracy=observed,
        pass_gate=True,
    )


def _fake_materialization_payload() -> dict[str, Any]:
    candidates = []
    for spec in p3.frozen_candidate_specs():
        per_day = []
        for day in dd.HISTORICAL_DAYS:
            per_day.append(
                {
                    "date": day.isoformat(),
                    "decision_count": 2,
                    "t1_common_support_count": 2,
                    "t1_long_common_count": 1,
                    "t1_short_common_count": 1,
                    "support_sha256": {
                        "native_s0_support_sha256": "1" * 64,
                        "native_s1_support_sha256": "2" * 64,
                        "common_support_sha256": "3" * 64,
                        "t1_common_support_sha256": "4" * 64,
                    },
                }
            )
        folds = []
        for fold in dd.OUTER_FOLDS:
            folds.append(
                {
                    "fold_id": fold.fold_id,
                    "train_days": [day.isoformat() for day in fold.train_days],
                    "validation_day": fold.validation_day.isoformat(),
                    "train_t1_count": 2,
                    "validation_t1_count": 2,
                    "train_class_counts": {"long": 1, "short": 1},
                    "validation_class_counts": {"long": 1, "short": 1},
                    "support_sha256": {"synthetic": "5" * 64},
                }
            )
        candidates.append(
            {
                "target": {
                    "target_id": spec.target_id,
                    "horizon_seconds": spec.horizon_seconds,
                    "barrier_bps": spec.barrier_bps,
                },
                "window_seconds": spec.window_seconds,
                "block": spec.block,
                "per_day": per_day,
                "folds": folds,
            }
        )
    return {
        "authorized_input_manifest": [
            {"date": day.isoformat(), "sha256": "a" * 64} for day in dd.HISTORICAL_DAYS
        ],
        "configuration": {"candidate_count": 64},
        "per_candidate": candidates,
    }



def _raw_price_day(day: Any) -> Any:
    rows = 300
    start = _day_start_us(day)
    ts = start + np.arange(rows, dtype=np.int64) * 250_000
    bid = np.full(rows, 99.5, dtype=np.float64)
    ask = np.full(rows, 100.5, dtype=np.float64)
    mid = np.linspace(100.0, 101.0, rows, dtype=np.float64)
    valid = np.ones(rows, dtype=bool)
    matrix = np.zeros((rows, len(dd.SOURCE_FEATURE_ORDER)), dtype=np.float64)
    # deterministic non-constant PRICE primitives
    matrix[:, dd.SOURCE_FEATURE_ORDER.index("spread_bps")] = np.linspace(1.0, 2.0, rows)
    matrix[:, dd.SOURCE_FEATURE_ORDER.index("microprice_minus_mid_bps")] = np.sin(
        np.arange(rows) * 0.05
    )
    return SimpleNamespace(
        day=day,
        ts=ts,
        bid=bid,
        ask=ask,
        mid=mid,
        book_valid=valid.copy(),
        valid={"L0": valid.copy(), "L1": valid.copy(), "L2": valid.copy()},
        X={"L2": matrix},
    )


def _single_price_candidate_day(day: Any) -> dd.CandidateDayDataset:
    spec = _spec(block="PRICE")
    key = dd.CandidateKey(
        next(target for target in dd.FROZEN_TARGETS if target.target_id == spec.target_id),
        spec.window_seconds,
        spec.block,
    )
    timestamp = _day_start_us(day) + 60_000_000
    s0_names = tuple(dd.sf.block_feature_names("PRICE"))
    s1_names = dd.sequence_summary_feature_names("PRICE")
    mask = np.asarray([True], dtype=bool)
    return dd.CandidateDayDataset(
        day=day,
        key=key,
        decision_timestamps_us=np.asarray([timestamp], dtype=np.int64),
        target_records=(
            {
                "target_valid": True,
                "label": "LONG_FIRST",
                "invalid_reason": None,
                "same_row_ambiguous": False,
            },
        ),
        t1_labels=np.asarray([1], dtype=np.int8),
        s0_feature_names=s0_names,
        s1_feature_names=s1_names,
        s0_values=np.zeros((1, len(s0_names)), dtype=np.float64),
        s1_values=np.zeros((1, len(s1_names)), dtype=np.float64),
        s0_valid=mask.copy(),
        s1_valid=mask.copy(),
        common_valid=mask.copy(),
        t1_common_valid=mask.copy(),
        target_future_boundary_valid=mask.copy(),
        s0_boundary_reasons=(None,),
        s1_boundary_reasons=(None,),
        target_boundary_reasons=(None,),
        s0_invalid_reasons=(None,),
        s1_invalid_reasons=(None,),
        counts={},
        support_hashes={},
    )


def test_frozen_candidate_grid_is_exact_and_ordered() -> None:
    specs = p3.frozen_candidate_specs()
    assert len(specs) == 64
    assert [item.target_id for item in specs[:16]] == ["A"] * 16
    assert [item.window_seconds for item in specs[:16]] == [8] * 4 + [16] * 4 + [32] * 4 + [60] * 4
    assert [item.block for item in specs[:4]] == list(dd.FROZEN_BLOCKS)


def test_runtime_provenance_success_and_guards() -> None:
    state = p3.runtime_provenance(model_fit_run=True, campaign_1_run=True)
    assert p3.validate_runtime_provenance(state) == state
    assert state["pnl_backtest_run"] is False
    assert not any(state["forward_data_guards"].values())


def test_runtime_campaign_requires_model_fit() -> None:
    assert _reason(
        p3.runtime_provenance,
        model_fit_run=False,
        campaign_1_run=True,
    ) == "campaign1_requires_model_fit"


@pytest.mark.parametrize("guard", tuple(p3.FORWARD_GUARDS))
def test_runtime_forward_guards_fail_closed(guard: str) -> None:
    state = p3.runtime_provenance(model_fit_run=True, campaign_1_run=True)
    state["forward_data_guards"][guard] = True
    assert _reason(p3.validate_runtime_provenance, state) == "forward_data_guard_violation"


def test_pnl_runtime_state_is_forbidden() -> None:
    state = p3.runtime_provenance(model_fit_run=True, campaign_1_run=True)
    state["pnl_backtest_run"] = True
    assert _reason(p3.validate_runtime_provenance, state) == "pnl_forbidden"


def test_dependency_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    for rel in (p3.P2B_SOURCE_REL, p3.SEQUENCE_SOURCE_REL, p3.FIRST_PASSAGE_SOURCE_REL):
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("synthetic", encoding="utf-8")

    def hashes(path: Path) -> str:
        if path.as_posix().endswith(p3.P2B_SOURCE_REL):
            return "0" * 64
        if path.as_posix().endswith(p3.SEQUENCE_SOURCE_REL):
            return p3.SEQUENCE_SOURCE_SHA256
        return p3.FIRST_PASSAGE_SOURCE_SHA256

    assert _reason(
        p3.verify_frozen_dependencies, tmp_path, hash_file=hashes
    ) == "p2b_source_sha256_mismatch"


def test_dependency_hashes_pass_with_explicit_expected_values(tmp_path: Path) -> None:
    expected = {
        p3.P2B_SOURCE_REL: p3.P2B_SOURCE_SHA256,
        p3.SEQUENCE_SOURCE_REL: p3.SEQUENCE_SOURCE_SHA256,
        p3.FIRST_PASSAGE_SOURCE_REL: p3.FIRST_PASSAGE_SOURCE_SHA256,
    }
    for rel in expected:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("synthetic", encoding="utf-8")

    result = p3.verify_frozen_dependencies(
        tmp_path,
        hash_file=lambda path: expected[path.relative_to(tmp_path).as_posix()],
    )
    assert result == expected


def test_p2c_artifact_hash_mismatch_fails_before_parse(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    path.write_text("{not json", encoding="utf-8")
    assert _reason(
        p3.load_frozen_p2c_artifact,
        path,
        hash_file=lambda unused: "0" * 64,
    ) == "p2c_artifact_sha256_mismatch"


def test_p2c_candidate_reconciliation_exact_success() -> None:
    payload = _fake_materialization_payload()
    p3.reconcile_candidate_payload(payload, json.loads(json.dumps(payload)))


def test_p2c_candidate_reconciliation_detects_day_support_change() -> None:
    left = _fake_materialization_payload()
    right = json.loads(json.dumps(left))
    right["per_candidate"][0]["per_day"][0]["support_sha256"]["common_support_sha256"] = "f" * 64
    assert _reason(
        p3.reconcile_candidate_payload, left, right
    ) == "candidate_day_reconciliation_failed"


def test_p2c_candidate_reconciliation_detects_fold_hash_change() -> None:
    left = _fake_materialization_payload()
    right = json.loads(json.dumps(left))
    right["per_candidate"][0]["folds"][0]["support_sha256"]["synthetic"] = "f" * 64
    assert _reason(
        p3.reconcile_candidate_payload, left, right
    ) == "fold_reconciliation_failed"


def test_metric_summary_exact_confusion_order() -> None:
    truth = np.asarray([0, 0, 1, 1], dtype=np.int8)
    pred = np.asarray([0, 1, 0, 1], dtype=np.int8)
    probs = np.asarray([0.1, 0.6, 0.4, 0.9])
    result = p3.metric_summary(truth, pred, probs)
    assert result["balanced_accuracy"] == 0.5
    assert result["confusion_matrix_short_long"] == [[1, 1], [1, 1]]
    assert result["long_count"] == 2
    assert result["short_count"] == 2
    assert "roc_auc_diagnostic" in result


@pytest.mark.parametrize("value", (np.nan, np.inf, -np.inf))
def test_metric_summary_rejects_nonfinite_probabilities(value: float) -> None:
    assert _reason(
        p3.metric_summary,
        np.asarray([0, 1], dtype=np.int8),
        np.asarray([0, 1], dtype=np.int8),
        np.asarray([0.1, value]),
    ) == "invalid_probability_vector"


def test_frozen_logistic_configuration() -> None:
    model = p3._new_logistic(0.1)
    assert model.C == 0.1
    assert model.solver == "lbfgs"
    assert model.l1_ratio == 0.0
    assert model.class_weight is None
    assert model.max_iter == 1000
    assert model.fit_intercept is True
    assert model.random_state == p3.RANDOM_STATE
    assert p3.C_GRID == (0.01, 0.1, 1.0, 10.0)
    assert p3.THRESHOLD == 0.5


def test_select_c_tie_prefers_smaller_c() -> None:
    x_fit = np.zeros((20, 2), dtype=np.float64)
    y_fit = np.asarray([0, 1] * 10, dtype=np.int8)
    x_val = np.zeros((20, 2), dtype=np.float64)
    y_val = np.asarray([0, 1] * 10, dtype=np.int8)
    selected, ledger = p3.select_c_chronologically(x_fit, y_fit, x_val, y_val)
    assert selected == 0.01
    assert [item["C"] for item in ledger] == list(p3.C_GRID)


def test_select_c_requires_both_classes_in_inner_fit() -> None:
    assert _reason(
        p3.select_c_chronologically,
        np.zeros((10, 2)),
        np.zeros(10, dtype=np.int8),
        np.zeros((10, 2)),
        np.asarray([0, 1] * 5, dtype=np.int8),
    ) == "inner_split_requires_both_classes"


def test_prediction_hash_is_deterministic_and_order_sensitive() -> None:
    spec = _spec()
    timestamps = np.asarray([1, 2, 3], dtype=np.int64)
    truth = np.asarray([0, 1, 0], dtype=np.int8)
    pred = np.asarray([0, 1, 1], dtype=np.int8)
    probs = np.asarray([0.2, 0.8, 0.7])
    first = p3.prediction_sha256(
        spec=spec,
        representation="S1",
        fold_id=1,
        timestamps_us=timestamps,
        y_true=truth,
        y_pred=pred,
        p_long=probs,
    )
    second = p3.prediction_sha256(
        spec=spec,
        representation="S1",
        fold_id=1,
        timestamps_us=timestamps,
        y_true=truth,
        y_pred=pred,
        p_long=probs,
    )
    assert first == second
    changed = p3.prediction_sha256(
        spec=spec,
        representation="S1",
        fold_id=1,
        timestamps_us=timestamps,
        y_true=truth,
        y_pred=pred,
        p_long=np.asarray([0.2, 0.8, 0.6]),
    )
    assert changed != first


def test_prediction_hash_rejects_nonchronological_timestamps() -> None:
    assert _reason(
        p3.prediction_sha256,
        spec=_spec(),
        representation="S1",
        fold_id=1,
        timestamps_us=np.asarray([2, 1], dtype=np.int64),
        y_true=np.asarray([0, 1], dtype=np.int8),
        y_pred=np.asarray([0, 1], dtype=np.int8),
        p_long=np.asarray([0.2, 0.8]),
    ) == "prediction_hash_timestamps_not_chronological"


def test_m0_training_tie_maps_to_short() -> None:
    days = _per_day(rows=20)
    train = [days[dd.HISTORICAL_DAYS[0]]]
    val = days[dd.HISTORICAL_DAYS[1]]
    controls = p3.m0_controls_for_fold(
        train_dataset_rows=train,
        validation_dataset=val,
    )
    majority = controls["training_majority"]
    assert majority["predicted_short_count"] == 20
    assert majority["predicted_long_count"] == 0


def test_m0_flow_control_is_present_for_flow_fixture() -> None:
    days = _per_day(rows=20)
    controls = p3.m0_controls_for_fold(
        train_dataset_rows=[days[dd.HISTORICAL_DAYS[0]]],
        validation_dataset=days[dd.HISTORICAL_DAYS[1]],
    )
    assert "microprice_minus_mid_bps_sign" in controls
    assert "obi_l1_sign" in controls
    assert "ofi_l1_1s_sign" in controls



def test_price_m0_requires_and_uses_book_reference() -> None:
    price_spec = _spec(block="PRICE")
    price_days = _per_day(spec=price_spec, rows=20)
    validation = price_days[dd.HISTORICAL_DAYS[1]]
    # Make the candidate fixture realistic for PRICE: OBI/OFI are absent.
    validation.s0_feature_names = ("microprice_minus_mid_bps", "noise")
    validation.s0_values = validation.s0_values[:, [0, 3]]

    assert _reason(
        p3.m0_controls_for_fold,
        train_dataset_rows=[price_days[dd.HISTORICAL_DAYS[0]]],
        validation_dataset=validation,
    ) == "m0_reference_required"

    book_ref = _candidate_day(
        dd.HISTORICAL_DAYS[1],
        spec=_spec(block="PRICE_BOOK"),
        rows=20,
    )
    controls = p3.m0_controls_for_fold(
        train_dataset_rows=[price_days[dd.HISTORICAL_DAYS[0]]],
        validation_dataset=validation,
        obi_reference_validation=book_ref,
    )
    assert "obi_l1_sign" in controls
    assert "ofi_l1_1s_sign" not in controls


def test_reverse_s1_summary_matrix_exact_arithmetic() -> None:
    names = (
        "x__last",
        "x__mean",
        "x__std",
        "x__minimum",
        "x__maximum",
        "x__last_minus_first",
        "x__ols_slope",
        "x__sign_persistence",
    )
    values = np.asarray([[5.0, 3.0, 1.0, 1.0, 5.0, 4.0, 2.0, 0.5]])
    reversed_values = p3.reverse_s1_summary_matrix(values, names)
    assert reversed_values[0, 0] == 1.0
    assert reversed_values[0, 1] == 3.0
    assert reversed_values[0, 2] == 1.0
    assert reversed_values[0, 5] == -4.0
    assert reversed_values[0, 6] == -2.0
    assert reversed_values[0, 7] == 0.5


def test_time_permuted_s1_matrix_is_deterministic_and_exact_shape() -> None:
    day = dd.HISTORICAL_DAYS[0]
    raw = _raw_price_day(day)
    dataset = _single_price_candidate_day(day)
    spec = _spec(block="PRICE")
    first = p3.permuted_s1_matrix(
        raw_day=raw,
        dataset=dataset,
        spec=spec,
        fold_id=1,
    )
    second = p3.permuted_s1_matrix(
        raw_day=raw,
        dataset=dataset,
        spec=spec,
        fold_id=1,
    )
    assert first.shape == (1, len(dataset.s1_feature_names))
    assert np.array_equal(first, second)


def test_block_alignment_permutation_preserves_earlier_block_columns() -> None:
    spec = _spec(block="PRICE_BOOK")
    names = dd.sequence_summary_feature_names("PRICE_BOOK")
    rows = 30
    matrix = np.arange(rows * len(names), dtype=np.float64).reshape(rows, len(names))
    transformed = p3.block_alignment_permuted_matrix(
        matrix,
        spec=spec,
        feature_names=names,
    )
    assert transformed is not None
    prior = set(dd.sequence_summary_feature_names("PRICE"))
    prior_indices = [i for i, name in enumerate(names) if name in prior]
    new_indices = [i for i, name in enumerate(names) if name not in prior]
    assert np.array_equal(transformed[:, prior_indices], matrix[:, prior_indices])
    assert not np.array_equal(transformed[:, new_indices], matrix[:, new_indices])


def test_fit_candidate_uses_exact_four_outer_folds_and_inner_days() -> None:
    result = p3.fit_candidate_m1(_spec(), _per_day(rows=60))
    assert len(result.s0_folds) == 4
    assert len(result.s1_folds) == 4
    assert [fold.fold_id for fold in result.s1_folds] == [1, 2, 3, 4]
    assert [item["fold_id"] for item in result.m0_folds] == [1, 2, 3, 4]
    assert all(fold.selected_c in p3.C_GRID for fold in result.s0_folds)
    assert all(fold.selected_c in p3.C_GRID for fold in result.s1_folds)


def test_synthetic_temporal_signal_beats_snapshot_in_fit() -> None:
    result = p3.fit_candidate_m1(_spec(), _per_day(rows=80, s1_strength=4.0))
    assert result.s1_pooled["balanced_accuracy"] > result.s0_pooled["balanced_accuracy"]
    assert result.pooled_delta_ba > 0.0


def test_fit_candidate_rejects_day_order_mutation() -> None:
    days = _per_day(rows=20)
    reversed_days = dict(reversed(tuple(days.items())))
    assert _reason(
        p3.fit_candidate_m1, _spec(), reversed_days
    ) == "candidate_day_order_mismatch"


def test_eligible_shared_null_shifts_exact() -> None:
    assert p3.eligible_shared_null_shifts([40, 40, 40, 40]) == tuple(range(10, 31))


def test_temporal_null_requires_at_least_20_shifts() -> None:
    folds = tuple(_fold_result(i + 1, support=25) for i in range(4))
    assert _reason(p3.temporal_label_null, folds) == "insufficient_temporal_null_shifts"


def test_temporal_null_arithmetic_is_deterministic() -> None:
    folds = tuple(_fold_result(i + 1, support=40) for i in range(4))
    first = p3.temporal_label_null(folds)
    second = p3.temporal_label_null(folds)
    assert first == second
    assert len(first.eligible_shifts) == 21
    assert math_is_finite(first.null_q95)
    assert math_is_finite(first.empirical_p)


def math_is_finite(value: float) -> bool:
    return bool(np.isfinite(value))


def test_control_target_can_never_be_promoted() -> None:
    model = _model_result(spec=_spec(target_id="C"))
    gates = p3.final_promotion_gates(model, _passing_null())
    assert gates["primary_target"] is False
    assert p3.candidate_is_eligible(model, _passing_null()) is False


def test_missing_temporal_null_cannot_promote() -> None:
    model = _model_result()
    gates = p3.final_promotion_gates(model, None)
    assert gates["temporal_null_run"] is False
    assert p3.candidate_is_eligible(model, None) is False


def test_failed_precheck_cannot_be_rescued_by_null() -> None:
    model = _model_result(all_precheck=False)
    assert p3.candidate_is_eligible(model, _passing_null()) is False


def test_survivor_ranking_prefers_stability_before_delta() -> None:
    stable = _model_result(s1_ba=0.62, delta=0.03)
    less_stable = _model_result(
        spec=_spec(window_seconds=16),
        s1_ba=0.60,
        delta=0.08,
    )
    selected = p3.select_survivor(
        [(less_stable, _passing_null(0.60)), (stable, _passing_null(0.62))]
    )
    assert selected is not None
    assert selected.spec == stable.spec


def test_survivor_ranking_uses_shorter_window_as_late_tiebreaker() -> None:
    short = _model_result(spec=_spec(window_seconds=8))
    long = _model_result(spec=_spec(window_seconds=16))
    selected = p3.select_survivor(
        [(long, _passing_null()), (short, _passing_null())]
    )
    assert selected is not None
    assert selected.spec.window_seconds == 8


def test_control_target_rank_is_forbidden() -> None:
    assert _reason(
        p3.survivor_rank_key,
        _model_result(spec=_spec(target_id="D")),
    ) == "control_target_not_rankable"



def test_campaign_payload_requires_f2_when_temporal_null_passes() -> None:
    results = []
    specs = p3.frozen_candidate_specs()
    for index, spec in enumerate(specs):
        model = _model_result(spec=spec, all_precheck=(index == 0))
        results.append((model, _passing_null() if index == 0 else None))
    manifest = tuple(
        dd.InputManifestEntry(day, Path(f"/synthetic/{day}.csv"), "a" * 64, 1)
        for day in dd.HISTORICAL_DAYS
    )
    assert _reason(
        p3.build_campaign_payload,
        execution_commit="a" * 40,
        runtime_state=p3.runtime_provenance(model_fit_run=True, campaign_1_run=True),
        candidate_results=results,
        input_manifest=manifest,
        dependency_hashes={},
    ) == "f2_diagnostics_required"


def test_run_campaign1_reconciliation_failure_prevents_any_fit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fit_calls = {"count": 0}
    frozen = _fake_materialization_payload()
    reconstructed = json.loads(json.dumps(frozen))
    reconstructed["per_candidate"][0]["per_day"][0]["decision_count"] = 999

    monkeypatch.setattr(
        p3.dm,
        "build_materialization_payload",
        lambda **kwargs: reconstructed,
    )
    monkeypatch.setattr(
        p3.dm,
        "verify_frozen_builder_source",
        lambda workspace: {
            "path": p3.dm.FROZEN_BUILDER_SOURCE_REL,
            "sha256": p3.dm.FROZEN_BUILDER_SOURCE_SHA256,
            "sha256_verified": True,
        },
    )

    fake_days = tuple(SimpleNamespace(day=day) for day in dd.HISTORICAL_DAYS)
    fake_candidates = {
        dd.CandidateKey(target, window, block): {}
        for target in dd.FROZEN_TARGETS
        for window in dd.FROZEN_WINDOWS_SECONDS
        for block in dd.FROZEN_BLOCKS
    }

    def fitter(*args: Any, **kwargs: Any) -> Any:
        fit_calls["count"] += 1
        raise AssertionError("fitter must not be called")

    assert _reason(
        p3.run_campaign1,
        workspace=tmp_path,
        output_directory=tmp_path / "out",
        execution_commit="a" * 40,
        require_canonical_output=False,
        p2c_loader=lambda: frozen,
        manifest_verifier=lambda: (),
        analytical_day_loader=lambda: fake_days,
        candidate_builder=lambda days: fake_candidates,
        candidate_fitter=fitter,
        dependency_verifier=lambda workspace: {},
    ) in {
        "input_manifest_reconciliation_failed",
        "candidate_day_reconciliation_failed",
    }
    assert fit_calls["count"] == 0


def test_canonical_json_is_deterministic_and_rejects_nonfinite() -> None:
    payload = {"b": 2, "a": 1}
    assert p3.canonical_json_bytes(payload) == p3.canonical_json_bytes(
        {"a": 1, "b": 2}
    )
    with pytest.raises(Exception):
        p3.canonical_json_bytes({"value": float("nan")})


def test_noncanonical_synthetic_writer_succeeds_once(tmp_path: Path) -> None:
    output = tmp_path / "campaign"
    result = p3.write_result_once(
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
        p3.write_result_once,
        output,
        {"synthetic": True},
        require_canonical_output=False,
    ) == "output_directory_already_exists"


def test_real_output_cannot_enter_synthetic_mode() -> None:
    assert _reason(
        p3.write_result_once,
        p3.REAL_OUTPUT_DIRECTORY,
        {"synthetic": True},
        require_canonical_output=False,
    ) == "canonical_output_requires_real_mode"


def test_trial_ledger_requires_exactly_64_candidates() -> None:
    assert _reason(
        p3.build_campaign_payload,
        execution_commit="a" * 40,
        runtime_state=p3.runtime_provenance(
            model_fit_run=True, campaign_1_run=True
        ),
        candidate_results=[],
        input_manifest=[],
        dependency_hashes={},
    ) == "trial_ledger_must_contain_64_candidates"


def test_campaign_payload_has_no_economic_or_forward_activity() -> None:
    # Build 64 synthetic non-survivors in frozen order.
    results = []
    for spec in p3.frozen_candidate_specs():
        model = _model_result(spec=spec, all_precheck=False)
        results.append((model, None))
    manifest = tuple(
        dd.InputManifestEntry(day, Path(f"/synthetic/{day}.csv"), "a" * 64, 1)
        for day in dd.HISTORICAL_DAYS
    )
    payload = p3.build_campaign_payload(
        execution_commit="a" * 40,
        runtime_state=p3.runtime_provenance(
            model_fit_run=True, campaign_1_run=True
        ),
        candidate_results=results,
        input_manifest=manifest,
        dependency_hashes={
            p3.P2B_SOURCE_REL: p3.P2B_SOURCE_SHA256,
            p3.SEQUENCE_SOURCE_REL: p3.SEQUENCE_SOURCE_SHA256,
            p3.FIRST_PASSAGE_SOURCE_REL: p3.FIRST_PASSAGE_SOURCE_SHA256,
        },
    )
    assert len(payload["trial_ledger"]) == 64
    assert payload["selected_for_next_development_stage"] is None
    assert not any(payload["prohibited_activity"].values())
    serialized = json.dumps(payload, sort_keys=True).lower()
    assert '"pnl": false' in serialized
    assert '"forward_data": false' in serialized


def test_trial_ledger_order_mutation_fails() -> None:
    specs = p3.frozen_candidate_specs()
    results = [
        (_model_result(spec=spec, all_precheck=False), None) for spec in specs
    ]
    results[0], results[1] = results[1], results[0]
    manifest = tuple(
        dd.InputManifestEntry(day, Path(f"/synthetic/{day}.csv"), "a" * 64, 1)
        for day in dd.HISTORICAL_DAYS
    )
    assert _reason(
        p3.build_campaign_payload,
        execution_commit="a" * 40,
        runtime_state=p3.runtime_provenance(
            model_fit_run=True, campaign_1_run=True
        ),
        candidate_results=results,
        input_manifest=manifest,
        dependency_hashes={},
    ) == "trial_ledger_candidate_order_mismatch"


def test_test_module_contains_no_real_data_opening_interface() -> None:
    # Guard against accidental future edits that turn this synthetic suite into
    # a data-opening test. Inspect actual call sites rather than searching raw
    # source text, so the guard cannot fail on its own forbidden-name literals.
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    called_names: set[str] = set()
    opens_p2c_artifact = False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function = node.func
        if isinstance(function, ast.Name):
            called_names.add(function.id)
            if function.id == "open" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Name) and first.id == "P2C_ARTIFACT_PATH":
                    opens_p2c_artifact = True
        elif isinstance(function, ast.Attribute):
            called_names.add(function.attr)

    assert "load_authorized_days" not in called_names
    assert "run_materialization" not in called_names
    assert opens_p2c_artifact is False

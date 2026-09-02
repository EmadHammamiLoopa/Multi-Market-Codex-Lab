from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from multimarket import dev030_p9_price_dense_sequence as p9
from multimarket import dev030_p10_minirocket as p10


def _reason(fn, *args, **kwargs) -> str:
    with pytest.raises(p10.P10Error) as exc:
        fn(*args, **kwargs)
    return exc.value.reason


def _fold(
    fold_id: int,
    *,
    auc: float,
    logloss: float,
    brier: float,
    ba: float,
    macro_f1: float,
) -> p9.FoldResult:
    n = 12
    ts = np.arange(n, dtype=np.int64) + fold_id * 100
    y = np.tile(np.array([0, 1], dtype=np.int8), n // 2)
    p = np.linspace(0.2, 0.8, n)
    metrics = {
        "support": n,
        "long_count": 6,
        "short_count": 6,
        "binary_log_loss": logloss,
        "brier": brier,
        "roc_auc": auc,
        "balanced_accuracy_at_0_5": ba,
        "macro_f1_at_0_5": macro_f1,
        "mcc_at_0_5": 0.0,
        "predicted_long_count_at_0_5": 6,
        "predicted_short_count_at_0_5": 6,
        "short": {"precision": 0.5, "recall": 0.5, "f1": 0.5, "support": 6},
        "long": {"precision": 0.5, "recall": 0.5, "f1": 0.5, "support": 6},
        "confusion_matrix_short_long_at_0_5": [[3, 3], [3, 3]],
    }
    return p9.FoldResult(
        fold_id=fold_id,
        representation="C0",
        selected_c=0.1,
        support=n,
        long_count=6,
        short_count=6,
        metrics=metrics,
        timestamps_us=ts,
        y_true=y,
        p_long=p,
        y_pred=(p >= 0.5).astype(np.int8),
        prediction_sha256=f"{fold_id:064x}"[-64:],
        support_sha256=f"{fold_id+10:064x}"[-64:],
        label_sha256=f"{fold_id+20:064x}"[-64:],
        inner_c_ledger=(),
        scaler=None,
        model=None,
    )


def _rep(
    *,
    auc: float,
    logloss: float,
    brier: float,
    ba: float,
    macro_f1: float,
    representation: str,
) -> p9.RepresentationResult:
    folds = tuple(
        replace(
            _fold(
                i,
                auc=auc,
                logloss=logloss,
                brier=brier,
                ba=ba,
                macro_f1=macro_f1,
            ),
            representation=representation,
        )
        for i in range(1, 5)
    )
    return p9.RepresentationResult(
        representation=representation,
        folds=folds,
        pooled_metrics={
            **folds[0].metrics,
            "support": 48,
            "long_count": 24,
            "short_count": 24,
            "roc_auc": auc,
            "binary_log_loss": logloss,
            "brier": brier,
            "balanced_accuracy_at_0_5": ba,
            "macro_f1_at_0_5": macro_f1,
        },
        pooled_support_sha256="a" * 64,
        pooled_label_sha256="b" * 64,
    )


def test_frozen_p9_artifact_identity() -> None:
    assert p10.P9_ARTIFACT_SHA256 == (
        "2f1913b3ac80df5cb0dd01dc7001c333983d22e6a8514346f9cee57a3333b9dc"
    )
    assert p10.P9_TERMINAL_STATUS == (
        "FAIL_PRICE_DENSE_SEQUENCE_NO_STABLE_INCREMENTAL_VALUE"
    )


def test_transform_feature_geometry_frozen() -> None:
    assert p10.EXPECTED_BASELINE_FEATURE_COUNT == 23
    assert p10.EXPECTED_TRANSFORM_FEATURE_COUNT == 9_996
    assert p10.EXPECTED_AUGMENTED_FEATURE_COUNT == 10_019


def test_runtime_provenance_synthetic_does_not_claim_data_opened() -> None:
    prov = p10.runtime_provenance(model_fit_run=False, p10_run=False)
    assert prov["jan_jul_analytically_opened"] is False
    assert prov["model_fit_run"] is False
    assert prov["p10_run"] is False
    assert not any(prov["forward_data_guards"].values())


def test_runtime_provenance_rejects_run_without_fit() -> None:
    assert _reason(
        p10.runtime_provenance,
        model_fit_run=False,
        p10_run=True,
    ) == "p10_requires_model_fit"


def test_wrong_p9_status_rejected(monkeypatch) -> None:
    monkeypatch.setattr(p9, "validate_prior_artifacts", lambda *args: None)
    good = {}
    p8 = {"status": "FAIL_PRICE_TEMPORAL_SHAPE_NO_STABLE_INCREMENTAL_VALUE"}
    p9_payload = {
        "status": "SOMETHING_ELSE",
        "eligible_price_dense_sequence_incremental_information": False,
    }
    assert _reason(
        p10.validate_prior_artifacts,
        good, good, good, good, good, p8, p9_payload,
    ) == "p9_terminal_status_mismatch"


def test_p9_eligibility_must_be_false(monkeypatch) -> None:
    monkeypatch.setattr(p9, "validate_prior_artifacts", lambda *args: None)
    good = {}
    p8 = {"status": "FAIL_PRICE_TEMPORAL_SHAPE_NO_STABLE_INCREMENTAL_VALUE"}
    p9_payload = {
        "status": p10.P9_TERMINAL_STATUS,
        "eligible_price_dense_sequence_incremental_information": True,
    }
    assert _reason(
        p10.validate_prior_artifacts,
        good, good, good, good, good, p8, p9_payload,
    ) == "p9_eligibility_state_mismatch"


def test_comparison_adds_ba_and_macro_f1_nonregression(monkeypatch) -> None:
    c0 = _rep(
        auc=0.55,
        logloss=0.70,
        brier=0.25,
        ba=0.54,
        macro_f1=0.52,
        representation="C0",
    )
    c1 = _rep(
        auc=0.57,
        logloss=0.69,
        brier=0.24,
        ba=0.53,
        macro_f1=0.51,
        representation="C1",
    )
    base = {
        "pooled_log_loss_improvement": 0.01,
        "pooled_brier_improvement": 0.01,
        "pooled_auc_delta": 0.02,
        "fold_log_loss_improvement": [0.01] * 4,
        "fold_auc_delta": [0.01] * 4,
        "leave_one_fold_out_log_loss_improvement": [0.01] * 4,
        "leave_one_fold_out_auc_delta": [0.01] * 4,
        "precheck_gates": {"all_invariants_pass": True},
        "precheck_pass": True,
    }
    monkeypatch.setattr(p9, "comparison_summary", lambda *a, **k: base)

    result = p10.comparison_summary(c0, c1)
    assert result["precheck_gates"]["pooled_balanced_accuracy_no_regression"] is False
    assert result["precheck_gates"]["pooled_macro_f1_no_regression"] is False
    assert result["precheck_pass"] is False


def test_c1_prediction_hash_is_deterministic_and_domain_specific() -> None:
    ts = np.arange(12, dtype=np.int64)
    y = np.tile(np.array([0, 1], dtype=np.int8), 6)
    p = np.linspace(0.1, 0.9, 12)
    a = p10.c1_prediction_sha256(
        fold_id=1,
        timestamps_us=ts,
        y_true=y,
        p_long=p,
    )
    b = p10.c1_prediction_sha256(
        fold_id=1,
        timestamps_us=ts,
        y_true=y,
        p_long=p,
    )
    assert a == b
    assert a != p9.prediction_sha256(
        fold_id=1,
        representation="C1",
        timestamps_us=ts,
        y_true=y,
        p_long=p,
    )


def test_write_result_once_refuses_existing_directory(tmp_path: Path) -> None:
    out = tmp_path / "result"
    out.mkdir()
    assert _reason(
        p10.write_result_once,
        out,
        {"status": "x"},
        require_canonical_output=False,
    ) == "output_directory_already_exists"


def test_noncanonical_mode_cannot_write_real_output() -> None:
    assert _reason(
        p10.write_result_once,
        p10.REAL_OUTPUT_DIRECTORY,
        {"status": "x"},
        require_canonical_output=False,
    ) in {
        "output_directory_already_exists",
        "canonical_output_requires_real_mode",
    }


def test_canonical_run_rejects_dependency_override_before_data_load(
    tmp_path: Path,
) -> None:
    marker = {"loaded": False}

    def should_not_load():
        marker["loaded"] = True
        raise AssertionError("must not load")

    assert _reason(
        p10.run_p10,
        workspace=tmp_path,
        output_directory=p10.REAL_OUTPUT_DIRECTORY,
        execution_commit="1" * 40,
        require_canonical_output=True,
        dependency_verifier=lambda _: {},
        analytical_day_loader=should_not_load,
    ) == "canonical_dependency_override_forbidden"
    assert marker["loaded"] is False

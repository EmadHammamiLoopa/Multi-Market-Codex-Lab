from __future__ import annotations

from pathlib import Path

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p6a_full_context_fusion_midpoint_transport as r27p6a


def test_contract_is_strictly_synthetic_and_preattempt() -> None:
    r27p6a.validate_r27p6a_contract()
    assert r27p6a.P2_ATTEMPT_CONSUMED is False
    assert r27p6a.REAL_HISTORICAL_BENCHMARK_AUTHORIZED is False
    assert r27p6a.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r27p6a.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r27p6a.SIMULATOR_LANE_AUTHORIZED is False
    assert r27p6a.MODEL_FIT_AUTHORIZED is False
    assert r27p6a.PNL_AUTHORIZED is False


def test_fused_raw_surface_has_one_compiled_raw_pass_contract() -> None:
    r27p6.validate_r27p6_contract()
    assert r27p6.ONE_COMPILED_RAW_EVENT_PASS is True
    assert r27p6.PYTHON_RAW_EVENT_LOOP_FORBIDDEN is True
    assert r27p6.PYTHON_REFERENCE_DECODER_FOR_ACCELERATED_PATH_FORBIDDEN is True
    assert r27p6.RAW_EVENT_PASS_COUNT == 1


def test_full_context_fused_builder_is_exact_r20_parity(tmp_path: Path) -> None:
    data = r20.make_synthetic_dual_context_fixture()
    r27p6a.assert_full_context_synthetic_parity(
        data,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
        reference_scratch_root=tmp_path / "reference",
        candidate_scratch_root=tmp_path / "candidate",
    )


def test_candidate_builder_does_not_delegate_to_r20_reference(tmp_path: Path, monkeypatch) -> None:
    data = r20.make_synthetic_dual_context_fixture()

    def forbidden_reference(*args, **kwargs):
        del args, kwargs
        raise AssertionError("python_reference_builder_forbidden")

    monkeypatch.setattr(r20, "build_once_day_context", forbidden_reference)

    candidate = r27p6a.build_fused_day_context(
        data,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
        scratch_root=tmp_path / "candidate",
    )
    try:
        assert candidate.raw_event_pass_count == 1
        assert candidate.feature_cache.decision_count > 0
        assert candidate.midpoint_index.count > 0
    finally:
        r20.close_midpoint_index(candidate.midpoint_index)

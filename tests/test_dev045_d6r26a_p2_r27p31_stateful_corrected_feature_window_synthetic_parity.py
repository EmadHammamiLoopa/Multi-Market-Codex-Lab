from pathlib import Path
from tempfile import TemporaryDirectory

from multimarket import dev045_d6r26a_p2_r27p31_stateful_corrected_feature_window_synthetic_parity as r


def test_contract_parent_green_and_all_execution_surfaces_closed():
    r.validate_r27p31_contract()
    assert r.PARENT_R27P30_HEAD == "64fe4292c06bb19df5117f5a474f099fe7f513ca"
    assert r.PARENT_R27P30_CI_RUN == 34718235901
    assert r.PARENT_R27P30_CI_JOB == 103619204229
    assert r.PARENT_R27P30_CI_CONCLUSION == "success"
    assert r.SYNTHETIC_ONLY is True
    assert r.REAL_HISTORICAL_OPEN_AUTHORIZED is False
    assert r.SOURCE_REHASH_AUTHORIZED is False
    assert r.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r.SIMULATOR_LANE_AUTHORIZED is False
    assert r.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r.P2_ATTEMPT_CONSUMED is False
    assert r.RAW_INPUT_BOUNDED_WINDOW_MAPPING_COMPLETE is False
    assert r.FULL_DAY_BOUNDED_MEMORY_PROVEN is False
    assert r.CANONICAL_EXECUTION_READY is False
    assert r.READINESS_BLOCKER == "RAW_INPUT_MAPPING_AND_COMPOSED_PIPELINE_RSS_NOT_YET_PROVEN"


def test_exact_corrected_context_parity_worst_and_odd_chunk_boundaries():
    # width=1 is the pathological boundary case; width=7 proves state carry
    # across a nontrivial odd-sized chunk without adding a redundant third
    # full corrected-context parity execution.
    result = r.run_synthetic_feature_parity_probe((1, 7))
    assert result.requested_count > 0
    assert len(result.cases) == 2
    for case in result.cases:
        assert case.exact_context_parity is True
        assert case.exact_context_digest is True
        assert case.eligible_count > 0
        assert case.leading_preeligible_count > 0
        assert case.max_active_output_mapped_bytes <= min(case.decision_chunk_rows, result.requested_count) * r.OUTPUT_BYTES_PER_ELIGIBLE_DECISION
        assert case.max_transition_sq_rows > 0


def test_file_backed_capacity_without_recompiling_feature_or_raw_kernels():
    # Capacity/mapping layout is independent of JIT semantics, so test it
    # directly instead of rebuilding raw + corrected feature surfaces again.
    requested_count = 11
    with TemporaryDirectory(prefix="r27p31_capacity_") as root:
        paths = r.prepare_feature_files(Path(root) / "feature", requested_count)
        assert Path(paths["decision_local_ns"]).stat().st_size == requested_count * 8
        assert Path(paths["best_bid_tick"]).stat().st_size == requested_count * 8
        assert Path(paths["best_ask_tick"]).stat().st_size == requested_count * 8
        assert Path(paths["values"]).stat().st_size == requested_count * r.CASE_COUNT * r.FEATURE_COUNT * 8

    assert r.FULL_DAY_O_N_TRANSITION_ARRAYS_ELIMINATED is True
    assert r.AMENDMENT_FULL_VALUES_COPY_ELIMINATED is True
    assert r.FULL_DAY_RAM_OUTPUT_ARRAYS_ELIMINATED is True
    assert r.CORRECTED_L5_WRITTEN_INLINE is True
    assert r.CORRECTED_R10_VOLATILITY_WRITTEN_INLINE is True

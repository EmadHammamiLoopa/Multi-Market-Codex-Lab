from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p18_corrected_5m_speed_benchmark_preexecution as r27p18
from multimarket import dev045_d6r26a_p2_r27p31_stateful_corrected_feature_window_synthetic_parity as r


def test_contract_is_synthetic_only_and_parent_green():
    r.validate_r27p31_contract()
    assert r.PARENT_R27P30_HEAD == "64fe4292c06bb19df5117f5a474f099fe7f513ca"
    assert r.PARENT_R27P30_CI_RUN == 34718235901
    assert r.PARENT_R27P30_CI_JOB == 103619204229
    assert r.PARENT_R27P30_CI_CONCLUSION == "success"
    assert r.SYNTHETIC_ONLY is True
    assert r.REAL_HISTORICAL_OPEN_AUTHORIZED is False
    assert r.P2_ATTEMPT_CONSUMED is False
    assert r.FULL_DAY_BOUNDED_MEMORY_PROVEN is False
    assert r.CANONICAL_EXECUTION_READY is False


def test_exact_corrected_context_parity_across_decision_chunk_boundaries():
    result = r.run_synthetic_feature_parity_probe((1, 3, 7))
    assert result.requested_count > 0
    assert len(result.cases) == 3
    for case in result.cases:
        assert case.exact_context_parity is True
        assert case.exact_context_digest is True
        assert case.eligible_count > 0
        assert case.leading_preeligible_count > 0
        assert case.max_active_output_mapped_bytes <= min(case.decision_chunk_rows, result.requested_count) * r.OUTPUT_BYTES_PER_ELIGIBLE_DECISION
        assert case.max_transition_sq_rows > 0


def test_file_backed_output_capacity_and_mapping_bound():
    fixture = r20.make_synthetic_dual_context_fixture()
    a = r19._validate_event_surface(fixture)
    bounds = r17.derive_feed_bounds(
        a,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
    )
    requested = np.asarray(r17.build_shared_decision_grid(bounds=bounds), dtype="<i8")
    raw = r27p6.run_fused_raw_surface(a)
    surface = r27p18._compact_from_raw(raw)
    with TemporaryDirectory(prefix="r27p31_test_") as root:
        result = r.run_stateful_corrected_feature_surface(
            surface,
            requested,
            root=Path(root) / "feature",
            decision_chunk_rows=3,
        )
        try:
            assert Path(result.paths["decision_local_ns"]).stat().st_size == requested.size * 8
            assert Path(result.paths["best_bid_tick"]).stat().st_size == requested.size * 8
            assert Path(result.paths["best_ask_tick"]).stat().st_size == requested.size * 8
            assert Path(result.paths["values"]).stat().st_size == requested.size * r.CASE_COUNT * r.FEATURE_COUNT * 8
            assert result.max_active_output_mapped_bytes <= 3 * r.OUTPUT_BYTES_PER_ELIGIBLE_DECISION
            assert isinstance(result.compiled.values, np.memmap)
        finally:
            r.close_feature_result(result)


def test_known_full_day_ram_allocations_are_explicitly_eliminated():
    assert r.FULL_DAY_O_N_TRANSITION_ARRAYS_ELIMINATED is True
    assert r.AMENDMENT_FULL_VALUES_COPY_ELIMINATED is True
    assert r.FULL_DAY_RAM_OUTPUT_ARRAYS_ELIMINATED is True
    assert r.CORRECTED_L5_WRITTEN_INLINE is True
    assert r.CORRECTED_R10_VOLATILITY_WRITTEN_INLINE is True
    assert r.RAW_INPUT_BOUNDED_WINDOW_MAPPING_COMPLETE is False
    assert r.READINESS_BLOCKER == "RAW_INPUT_MAPPING_AND_COMPOSED_PIPELINE_RSS_NOT_YET_PROVEN"

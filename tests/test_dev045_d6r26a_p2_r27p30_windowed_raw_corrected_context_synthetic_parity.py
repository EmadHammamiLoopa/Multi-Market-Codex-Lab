from __future__ import annotations

from multimarket import dev045_d6r26a_p2_r27p30_windowed_raw_corrected_context_synthetic_parity as r


def test_contract_preserves_parent_and_closes_real_surfaces() -> None:
    r.validate_r27p30_contract()
    assert r.EXPERIMENT_ID == "DEV045-D6R26A-P2-R27P30"
    assert r.PARENT_R27P29_HEAD == "ee53aa5f9fc597e253d73ddbcf1f241a8bd1c9cb"
    assert r.PARENT_R27P29_CI_RUN == 34716655575
    assert r.PARENT_R27P29_CI_JOB == 103615006481
    assert r.PARENT_R27P29_CI_CONCLUSION == "success"
    assert r.PARENT_R27P29_TEST_COUNT == 4
    assert r.WINDOWED_RAW_SEMANTICS_INTEGRATED is True
    assert r.DOWNSTREAM_FULL_DAY_BOUNDED_CONTEXT_COMPLETE is False
    assert r.FULL_DAY_BOUNDED_MEMORY_PROVEN is False
    assert r.CANONICAL_EXECUTION_READY is False
    assert r.P2_ATTEMPT_CONSUMED is False


def test_corrected_context_parity_with_windowed_raw() -> None:
    result = r.run_synthetic_corrected_context_parity_probe(chunk_rows=3)
    assert result.chunk_rows == 3
    assert result.input_chunk_count >= 2
    assert result.max_active_output_mapped_bytes > 0
    assert result.raw_adapter_call_count == 1
    assert result.exact_context_parity is True
    assert result.exact_context_digest is True
    assert result.exact_midpoint_bytes is True
    assert result.reference_digest == result.candidate_digest
    assert result.l5_changed_cells >= 0
    assert result.volatility_changed_cells >= 0


def test_corrected_context_parity_at_single_event_boundaries() -> None:
    result = r.run_synthetic_corrected_context_parity_probe(chunk_rows=1)
    assert result.chunk_rows == 1
    assert result.input_chunk_count >= 2
    assert result.exact_context_parity is True
    assert result.exact_context_digest is True
    assert result.exact_midpoint_bytes is True


def test_all_real_execution_surfaces_remain_closed() -> None:
    assert r.SYNTHETIC_ONLY is True
    assert r.REAL_HISTORICAL_OPEN_AUTHORIZED is False
    assert r.SOURCE_REHASH_AUTHORIZED is False
    assert r.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r.SIMULATOR_LANE_AUTHORIZED is False
    assert r.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r.P2_ATTEMPT_CONSUMED is False
    assert r.MODEL_FIT_AUTHORIZED is False
    assert r.PNL_AUTHORIZED is False
    assert r.AUG_OPEN_AUTHORIZED is False
    assert r.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r.NON_BTC_OPEN_AUTHORIZED is False
    assert r.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False

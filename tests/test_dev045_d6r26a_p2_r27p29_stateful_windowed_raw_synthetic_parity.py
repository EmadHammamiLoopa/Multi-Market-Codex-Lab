from __future__ import annotations

from multimarket import dev045_d6r26a_p2_r27p29_stateful_windowed_raw_synthetic_parity as r


def test_contract_is_synthetic_only_and_parent_green_is_bound() -> None:
    r.validate_r27p29_contract()
    assert r.EXPERIMENT_ID == "DEV045-D6R26A-P2-R27P29"
    assert r.PARENT_R27P28_HEAD == "0792fd992870081a9880a37aa6f5a0e05ffe41f3"
    assert r.PARENT_R27P28_CI_RUN == 34715145539
    assert r.PARENT_R27P28_CI_JOB == 103610947812
    assert r.PARENT_R27P28_CI_CONCLUSION == "success"
    assert r.STATEFUL_RAW_KERNEL_WINDOWING_COMPLETE is True
    assert r.FULL_CORRECTED_CONTEXT_WINDOWING_COMPLETE is False
    assert r.FULL_DAY_BOUNDED_MEMORY_PROVEN is False
    assert r.CANONICAL_EXECUTION_READY is False
    assert r.P2_ATTEMPT_CONSUMED is False


def test_stateful_raw_parity_across_boundary_stress_cases() -> None:
    result = r.run_synthetic_stateful_raw_parity_probe((1, 2, 3, 5, 7))
    assert result.rows > 0
    assert result.raw_buffer_count == 11
    assert result.bytes_per_event == 265
    assert len(result.cases) == 5
    for case in result.cases:
        assert case.exact_raw_bytes is True
        assert case.error == 0
        assert case.input_chunk_count >= 1
        assert case.max_active_output_mapped_bytes > 0


def test_single_row_chunking_matches_reference() -> None:
    result = r.run_synthetic_stateful_raw_parity_probe((1,))
    case = result.cases[0]
    assert case.input_chunk_rows == 1
    assert case.input_chunk_count == result.rows
    assert case.exact_raw_bytes is True


def test_execution_surfaces_remain_closed() -> None:
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

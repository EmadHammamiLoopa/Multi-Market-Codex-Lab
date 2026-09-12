import inspect

from multimarket import dev045_d6r26a_p2_r27p21_file_backed_fused_raw_kernel_synthetic_parity as r


def test_contract_and_closed_execution_surfaces():
    r.validate_r27p21_contract()
    assert r.RAW_BUFFER_COUNT == 11
    assert r.BYTES_PER_EVENT == 265
    assert r.ONE_COMPILED_RAW_EVENT_PASS is True
    assert r.RAW_EVENT_PASS_COUNT == 1
    assert r.CALLER_PROVIDED_OUTPUT_BUFFERS is True
    assert r.ANONYMOUS_FULL_N_RAW_OUTPUT_ALLOCATION is False
    assert r.R27P6_RAW_SEMANTICS_REWRITE_COMPLETE is True
    assert r.SYNTHETIC_ONLY is True
    assert r.REAL_HISTORICAL_OPEN_AUTHORIZED is False
    assert r.SOURCE_REHASH_AUTHORIZED is False
    assert r.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r.SIMULATOR_LANE_AUTHORIZED is False
    assert r.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r.P2_ATTEMPT_CONSUMED is False
    assert r.FULL_DAY_BOUNDED_MEMORY_PROVEN is False
    assert r.CANONICAL_EXECUTION_READY is False
    assert r.READINESS_BLOCKER == "FULL_DAY_RSS_BOUND_NOT_YET_PROVEN"


def test_target_kernel_has_no_internal_full_n_np_empty():
    source = inspect.getsource(r.build_file_backed_raw_kernel)
    assert "np.empty(" not in source


def test_exact_synthetic_raw_surface_byte_parity():
    r.run_synthetic_raw_parity_probe()


def test_exact_corrected_25_feature_context_and_midpoint_parity():
    result = r.run_synthetic_corrected_context_parity_probe()
    assert result.raw_buffer_count == 11
    assert result.raw_event_pass_count == 1
    assert result.raw_byte_parity is True
    assert result.corrected_context_parity is True
    assert result.midpoint_byte_parity is True
    assert result.reference_digest == result.candidate_digest

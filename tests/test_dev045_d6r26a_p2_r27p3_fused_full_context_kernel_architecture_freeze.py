from __future__ import annotations

from multimarket import (
    dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20,
)
from multimarket import (
    dev045_d6r26a_p2_r27p3_fused_full_context_kernel_architecture_freeze as r,
)


def test_contract_passes() -> None:
    r.validate_r27p3_contract()


def test_r27p2_real_kernel_gate_is_bound() -> None:
    assert r.R27P2_REAL_KERNEL_GATE_PASSED is True
    assert r.R27P2_GATE_PREFIX_ROWS == 5_000_000
    assert r.R27P2_OBSERVED_GATE_SPEEDUP == 224.975
    assert r.R27P2_OBSERVED_GATE_SPEEDUP >= r.R27P2_MIN_REQUIRED_SPEEDUP


def test_full_context_parity_surface_is_mandatory() -> None:
    assert r.EXACT_R20_OUTPUT_PARITY_REQUIRED is True
    assert r.BOUNDS_PARITY_REQUIRED is True
    assert r.FEATURE_SUMMARY_PARITY_REQUIRED is True
    assert r.DECISION_ARRAY_PARITY_REQUIRED is True
    assert r.BEST_BID_ARRAY_PARITY_REQUIRED is True
    assert r.BEST_ASK_ARRAY_PARITY_REQUIRED is True
    assert r.FEATURE_VALUES_PARITY_REQUIRED is True
    assert r.MIDPOINT_RECORD_PARITY_REQUIRED is True
    assert r.MIDPOINT_METADATA_PARITY_REQUIRED is True
    assert r.RAW_EVENT_PASS_COUNT_PARITY_REQUIRED is True


def test_accelerated_path_forbids_python_per_row_and_book_sorting() -> None:
    assert r.ONE_CAUSAL_RAW_EVENT_PASS_REQUIRED is True
    assert r.PYTHON_PER_ROW_LOOP_FORBIDDEN_IN_ACCELERATED_REAL_PATH is True
    assert r.PYTHON_BOOK_OBJECT_MATERIALIZATION_PER_GROUP_FORBIDDEN is True
    assert r.PYTHON_FULL_BOOK_SORT_PER_GROUP_FORBIDDEN is True
    assert r.COMPILED_STATE_MACHINE_REQUIRED is True


def test_exact_timestamp_and_midpoint_semantics_are_frozen() -> None:
    assert r.ROLLING_WINDOWS_EXACT_TIMESTAMP_BASED is True
    assert r.APPROXIMATE_SECOND_BUCKETING_FORBIDDEN is True
    assert r.RECENT_BOOK_ASOF_250MS_FROZEN is True
    assert r.RECENT_BOOK_ASOF_1S_FROZEN is True
    assert r.ROLLING_1S_5S_30S_BOUNDARIES_FROZEN is True
    assert r.MIDPOINT_RECORD_BYTES == r20.MIDPOINT_RECORD_BYTES == 16
    assert r.MIDPOINT_EXCHANGE_TIMESTAMP_STRICTLY_INCREASING is True
    assert r.MARKOUT_ASOF_RULE_FROZEN is True


def test_no_real_execution_or_p2_consumption_is_opened() -> None:
    assert r.P2_ATTEMPT_CONSUMED is False
    assert r.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r.HISTORICAL_SOURCE_REHASH_AUTHORIZED is False
    assert r.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r.SIMULATOR_LANE_AUTHORIZED is False
    assert r.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r.MODEL_FIT_AUTHORIZED is False
    assert r.PNL_AUTHORIZED is False
    assert r.AUG_OPEN_AUTHORIZED is False
    assert r.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r.NON_BTC_OPEN_AUTHORIZED is False

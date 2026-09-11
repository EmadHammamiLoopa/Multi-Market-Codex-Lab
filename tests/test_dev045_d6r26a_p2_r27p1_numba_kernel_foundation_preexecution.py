from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p1_numba_kernel_foundation_preexecution as r27p1


def test_contract_is_closed_and_preattempt():
    r27p1.validate_r27p1_contract()
    assert r27p1.P2_ATTEMPT_CONSUMED is False
    assert r27p1.REAL_HISTORICAL_BENCHMARK_AUTHORIZED is False
    assert r27p1.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r27p1.SIMULATOR_LANE_AUTHORIZED is False
    assert r27p1.MODEL_FIT_AUTHORIZED is False
    assert r27p1.PNL_AUTHORIZED is False


def test_numba_scan_exact_parity_on_frozen_synthetic_fixture():
    events = r20.make_synthetic_dual_context_fixture()
    kernel = r27p1.build_numba_scan_kernel()
    r27p1.assert_scan_parity(events, kernel=kernel)


def test_numba_scan_matches_reference_summary_fields():
    events = r20.make_synthetic_dual_context_fixture()
    expected = r27p1._python_scan(events)
    observed = r27p1.numba_scan(events)
    assert observed == expected
    assert observed.row_count == int(events.size)
    assert observed.local_rows > 0
    assert observed.exchange_rows > 0
    assert observed.depth_rows > 0


def test_unknown_event_fails_closed():
    events = r20.make_synthetic_dual_context_fixture().copy()
    events[0]["ev"] = np.uint64((int(events[0]["ev"]) & ~0xFF) | 99)
    with pytest.raises(r27p1.R27P1Error, match="unknown_event_kind"):
        r27p1.numba_scan(events)


def test_timestamp_regression_fails_closed():
    events = r20.make_synthetic_dual_context_fixture().copy()
    if events.size < 2:
        pytest.skip("fixture too small")
    events[1]["local_ts"] = events[0]["local_ts"] - 1
    with pytest.raises(r27p1.R27P1Error, match="local_timestamp_regression"):
        r27p1.numba_scan(events)


def test_bounded_synthetic_benchmark_executes_without_opening_historical():
    events = r20.make_synthetic_dual_context_fixture()
    py_s, nb_s, speedup = r27p1.benchmark_scan(events, repetitions=1)
    assert py_s > 0.0
    assert nb_s > 0.0
    assert speedup > 0.0

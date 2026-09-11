from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p8_real_prefix_parity_localization_preexecution as r27p8


def test_contract_opens_only_frozen_100k_diagnostic() -> None:
    r27p8.validate_r27p8_contract()
    assert r27p8.DIAGNOSTIC_PREFIX_ROWS == 100_000
    assert r27p8.REAL_HISTORICAL_DIAGNOSTIC_AUTHORIZED is True
    assert r27p8.REAL_HISTORICAL_DIAGNOSTIC_REQUIRES_EXPLICIT_AUTHORIZATION is True
    assert r27p8.ONE_FROZEN_SOURCE_ONLY is True
    assert r27p8.PREFIX_ONLY is True
    assert r27p8.NO_TIMING is True
    assert r27p8.NO_SPEED_GATE is True
    assert r27p8.NO_BENCHMARK_MANIFEST is True
    assert r27p8.P2_ATTEMPT_CONSUMED is False
    assert r27p8.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r27p8.SIMULATOR_LANE_AUTHORIZED is False
    assert r27p8.MODEL_FIT_AUTHORIZED is False
    assert r27p8.PNL_AUTHORIZED is False


def test_real_authorization_is_exact_token_only() -> None:
    assert r27p8.real_diagnostic_authorized({}) is False
    assert r27p8.real_diagnostic_authorized({r27p8.AUTH_ENV: "YES"}) is False
    assert r27p8.real_diagnostic_authorized(
        {r27p8.AUTH_ENV: r27p8.AUTH_TOKEN}
    ) is True


def test_unauthorized_runner_fails_before_source_probe(monkeypatch) -> None:
    def forbidden_probe() -> None:
        raise AssertionError("probe_before_auth")

    def forbidden_source():
        raise AssertionError("source_before_auth")

    monkeypatch.setattr(r27p2, "_validate_preattempt_state", forbidden_probe)
    monkeypatch.setattr(r27p2, "_verify_source_identity", forbidden_source)

    with pytest.raises(r27p8.R27P8Error, match="authorization"):
        r27p8.run_real_localization(environ={})


def test_compare_array_localizes_first_feature_mismatch() -> None:
    a = np.zeros((2, 8, 25), dtype=np.float64)
    b = a.copy()
    b[1, 3, 6] = 2.5
    diff = r27p8.compare_array("feature_values", a, b)
    assert diff.equal is False
    assert diff.mismatch_count == 1
    assert diff.first_index == (1, 3, 6)
    assert diff.feature_name == "bbo_ofi_1s"
    assert diff.expected_value == 0.0
    assert diff.observed_value == 2.5


def test_synthetic_fixture_reproduces_no_difference() -> None:
    data = r20.make_synthetic_dual_context_fixture()
    report = r27p8.diagnose_events(
        data,
        prefix_rows=int(data.size),
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
    )
    assert report.root_layer == "NOT_REPRODUCED"
    assert all(item.equal for item in report.surface)
    assert all(item.equal for item in report.reference_surface_kernel)
    assert all(item.equal for item in report.fused_surface_kernel)
    assert report.reference_leading_preeligible == report.compiled_reference_leading_preeligible
    assert report.reference_leading_preeligible == report.compiled_fused_leading_preeligible


def test_prefix_above_100k_fails_closed() -> None:
    data = r20.make_synthetic_dual_context_fixture()
    with pytest.raises(r27p8.R27P8Error, match="prefix_rows"):
        r27p8.diagnose_events(
            data,
            prefix_rows=r27p8.DIAGNOSTIC_PREFIX_ROWS + 1,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
        )

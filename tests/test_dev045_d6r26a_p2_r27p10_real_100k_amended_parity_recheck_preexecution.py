from __future__ import annotations

import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p10_real_100k_amended_parity_recheck_preexecution as r27p10


def test_contract_is_narrow_real_100k_parity_recheck_only() -> None:
    r27p10.validate_r27p10_contract()
    assert r27p10.PREFIX_ROWS == 100_000
    assert r27p10.REAL_HISTORICAL_PARITY_RECHECK_AUTHORIZED is True
    assert r27p10.REAL_HISTORICAL_PARITY_RECHECK_REQUIRES_EXPLICIT_AUTHORIZATION is True
    assert r27p10.NO_TIMING is True
    assert r27p10.NO_SPEED_GATE is True
    assert r27p10.NO_MIDPOINT_BENCHMARK is True
    assert r27p10.P2_ATTEMPT_CONSUMED is False
    assert r27p10.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r27p10.SIMULATOR_LANE_AUTHORIZED is False
    assert r27p10.MODEL_FIT_AUTHORIZED is False
    assert r27p10.PNL_AUTHORIZED is False


def test_authorization_is_exact_token_only() -> None:
    assert r27p10.real_recheck_authorized({}) is False
    assert r27p10.real_recheck_authorized({r27p10.AUTH_ENV: "YES"}) is False
    assert r27p10.real_recheck_authorized({r27p10.AUTH_ENV: r27p10.AUTH_TOKEN}) is True


def test_unauthorized_recheck_fails_before_source_probe(monkeypatch) -> None:
    def forbidden_probe() -> None:
        raise AssertionError("probe_forbidden_before_auth")

    def forbidden_source():
        raise AssertionError("source_forbidden_before_auth")

    monkeypatch.setattr(r27p2, "_validate_preattempt_state", forbidden_probe)
    monkeypatch.setattr(r27p2, "_verify_source_identity", forbidden_source)

    with pytest.raises(r27p10.R27P10Error, match="authorization"):
        r27p10.run_real_recheck(environ={})


def test_synthetic_fixture_exact_parity_after_amendment() -> None:
    data = r20.make_synthetic_dual_context_fixture()
    result = r27p10.recheck_events(
        data,
        prefix_rows=int(data.size),
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
    )
    assert result.exact_parity is True
    assert result.decision_count > 0
    assert all(index == 5 for index in result.amendment_changed_feature_indices)


def test_prefix_bounds_fail_closed() -> None:
    data = r20.make_synthetic_dual_context_fixture()
    with pytest.raises(r27p10.R27P10Error, match="prefix_rows"):
        r27p10.recheck_events(
            data,
            prefix_rows=0,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
        )


def test_source_identity_is_frozen() -> None:
    assert r27p10.SOURCE_DAY == r27p2.SOURCE_DAY
    assert r27p10.SOURCE_PATH == r27p2.SOURCE_PATH
    assert r27p10.SOURCE_ROWS == r27p2.SOURCE_ROWS
    assert r27p10.SOURCE_BYTES == r27p2.SOURCE_BYTES
    assert r27p10.SOURCE_SHA256 == r27p2.SOURCE_SHA256

from __future__ import annotations

import os

import numpy as np
import pytest

from multimarket import (
    dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20,
)
from multimarket import (
    dev045_d6r26a_p2_r27p1_numba_kernel_foundation_preexecution as r27p1,
)
from multimarket import (
    dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2,
)


def test_r27p2_contract_is_strictly_bounded_and_preattempt():
    r27p2.validate_r27p2_contract()
    assert r27p2.REAL_HISTORICAL_BENCHMARK_AUTHORIZED is True
    assert r27p2.BENCHMARK_SCOPE_ONE_FROZEN_SOURCE_ONLY is True
    assert r27p2.BENCHMARK_PREFIX_ONLY is True
    assert r27p2.FULL_DAY_CONTEXT_BUILD_AUTHORIZED is False
    assert r27p2.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r27p2.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r27p2.SIMULATOR_LANE_AUTHORIZED is False
    assert r27p2.P2_ATTEMPT_CONSUMED is False
    assert r27p2.PREFIX_ROWS == (100_000, 1_000_000, 5_000_000)
    assert r27p2.GATE_PREFIX_ROWS == 5_000_000
    assert r27p2.MIN_ACCEPTED_SPEEDUP == 10.0


def test_r27p2_source_identity_is_exact_frozen_january():
    assert r27p2.SOURCE_DAY == "2026-01-01"
    assert r27p2.SOURCE_ROWS == 64_314_723
    assert r27p2.SOURCE_BYTES == 4_116_142_528
    assert (
        r27p2.SOURCE_SHA256
        == "8f0a4fbd56ecdc261dbe2041ce138a09456423074925d495272716219a1d4da1"
    )


def test_r27p2_requires_explicit_authorization(monkeypatch):
    monkeypatch.delenv(r27p2.AUTH_ENV, raising=False)
    with pytest.raises(r27p2.R27P2Error, match="authorization"):
        # force failure before touching any historical source
        r27p2.run_real_benchmark()


def test_r27p2_prefix_benchmark_parity_on_synthetic_fixture(monkeypatch):
    data = r20.make_synthetic_dual_context_fixture()
    kernel = r27p1.build_numba_scan_kernel()
    n = min(10_000, int(data.size))
    observed = r27p2._benchmark_prefix(data, prefix_rows=n, kernel=kernel)
    assert observed.prefix_rows == n
    assert observed.parity is True
    assert observed.python_seconds > 0.0
    assert observed.numba_seconds_best > 0.0
    assert observed.speedup > 0.0


def test_r27p2_full_execution_surface_remains_closed():
    forbidden = (
        r27p2.FULL_DAY_CONTEXT_BUILD_AUTHORIZED,
        r27p2.FULL_JAN_JUL_RERUN_AUTHORIZED,
        r27p2.DURABLE_CONTEXT_WRITE_AUTHORIZED,
        r27p2.SIMULATOR_LANE_AUTHORIZED,
        r27p2.ATTEMPT_MARKER_WRITE_AUTHORIZED,
        r27p2.CANONICAL_LABEL_WRITE_AUTHORIZED,
        r27p2.MODEL_FIT_AUTHORIZED,
        r27p2.PNL_AUTHORIZED,
        r27p2.LIVE_TRADING_AUTHORIZED,
        r27p2.AUG_OPEN_AUTHORIZED,
        r27p2.SEP_PLUS_OPEN_AUTHORIZED,
        r27p2.NON_BTC_OPEN_AUTHORIZED,
        r27p2.P2_ATTEMPT_CONSUMED,
    )
    assert not any(forbidden)

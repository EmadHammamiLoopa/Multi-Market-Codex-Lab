from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
from multimarket import dev045_d6r26a_p2_r27p11_amended_bounded_speed_benchmark_preexecution as r27p11


def test_contract_opens_only_explicit_bounded_benchmark() -> None:
    r27p11.validate_r27p11_contract()
    assert r27p11.REAL_HISTORICAL_BENCHMARK_AUTHORIZED is True
    assert r27p11.REAL_HISTORICAL_BENCHMARK_REQUIRES_EXPLICIT_AUTHORIZATION is True
    assert r27p11.BENCHMARK_SCOPE_ONE_FROZEN_SOURCE_ONLY is True
    assert r27p11.BENCHMARK_PREFIX_ONLY is True
    assert r27p11.FULL_CONTEXT_OVER_BOUNDED_PREFIX_ONLY is True
    assert r27p11.FULL_DAY_CONTEXT_BUILD_AUTHORIZED is False
    assert r27p11.CPYTHON313_SUM_AMENDMENT_REQUIRED is True
    assert r27p11.BENCHMARK_MANIFEST_WRITE_AUTHORIZED is False
    assert r27p11.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r27p11.P2_ATTEMPT_CONSUMED is False
    assert r27p11.SIMULATOR_LANE_AUTHORIZED is False
    assert r27p11.MODEL_FIT_AUTHORIZED is False
    assert r27p11.PNL_AUTHORIZED is False


def test_real_authorization_is_exact_token_only() -> None:
    assert r27p11.real_benchmark_authorized({}) is False
    assert r27p11.real_benchmark_authorized({r27p11.AUTH_ENV: "YES"}) is False
    assert r27p11.real_benchmark_authorized({r27p11.AUTH_ENV: r27p11.AUTH_TOKEN}) is True


def test_unauthorized_runner_fails_before_source_probe(monkeypatch) -> None:
    def forbidden_probe() -> None:
        raise AssertionError("probe_forbidden")

    monkeypatch.setattr(r27p11.r27p2, "_validate_preattempt_state", forbidden_probe)

    with pytest.raises(r27p11.R27P11Error, match="authorization"):
        r27p11.run_real_benchmark(environ={})


def test_amended_full_context_synthetic_parity(tmp_path: Path) -> None:
    data = r20.make_synthetic_dual_context_fixture()
    reference = r20.build_once_day_context(
        data,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
        scratch_root=tmp_path / "reference",
    )
    candidate = None
    try:
        candidate, changed = r27p11.build_amended_fused_day_context(
            data,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
            scratch_root=tmp_path / "candidate",
        )
        assert changed >= 0
        r27p0.assert_exact_context_parity(reference, candidate)
        assert r27p0.digest_day_context(reference) == r27p0.digest_day_context(candidate)
        assert reference.midpoint_index.sha256 == candidate.midpoint_index.sha256
        assert reference.midpoint_index.bytes == candidate.midpoint_index.bytes
    finally:
        if not reference.midpoint_index.closed:
            r20.close_midpoint_index(reference.midpoint_index)
        if candidate is not None and not candidate.midpoint_index.closed:
            r20.close_midpoint_index(candidate.midpoint_index)


def test_loaded_synthetic_benchmark_exact_parity_and_cleanup(tmp_path: Path) -> None:
    data = r20.make_synthetic_dual_context_fixture()
    observation = r27p11.benchmark_loaded_prefix(
        data,
        prefix_rows=int(data.size),
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
        scratch_root=tmp_path,
    )
    assert observation.parity is True
    assert observation.reference_digest == observation.candidate_digest
    assert observation.reference_seconds > 0.0
    assert observation.candidate_seconds > 0.0
    assert observation.speedup > 0.0
    assert list(tmp_path.rglob("exchange_midpoints.bin")) == []


@pytest.mark.parametrize("prefix_rows", [0, -1, r27p11.MAX_BENCHMARK_ROWS + 1])
def test_prefix_bounds_fail_closed(tmp_path: Path, prefix_rows: int) -> None:
    data = r20.make_synthetic_dual_context_fixture()
    with pytest.raises(r27p11.R27P11Error, match="prefix_rows"):
        r27p11.benchmark_loaded_prefix(
            data,
            prefix_rows=prefix_rows,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
            scratch_root=tmp_path,
        )


def test_amendment_is_only_feature_five_on_realistic_arrays() -> None:
    # Contract-level check independent of historical data.
    values = np.zeros((2, 8, 25), dtype=np.float64)
    before = r27p11.r27p5.CompiledFeatureResult(
        decision_local_ns=np.array([1, 2], dtype="<i8"),
        best_bid_tick=np.array([10, 10], dtype="<i8"),
        best_ask_tick=np.array([11, 11], dtype="<i8"),
        values=values,
        leading_preeligible_count=0,
    )
    after_values = values.copy()
    after_values[:, :, 5] = 1.0
    after = r27p11.r27p5.CompiledFeatureResult(
        decision_local_ns=before.decision_local_ns,
        best_bid_tick=before.best_bid_tick,
        best_ask_tick=before.best_ask_tick,
        values=after_values,
        leading_preeligible_count=0,
    )
    audit = r27p11.r27p9.audit_amendment(before, after)
    assert audit.changed_feature_indices == (5,)
    assert audit.other_feature_bytes_equal is True

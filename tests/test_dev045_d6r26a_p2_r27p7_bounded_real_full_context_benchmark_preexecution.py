from __future__ import annotations

from pathlib import Path

import pytest

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p6a_full_context_fusion_midpoint_transport as r27p6a
from multimarket import dev045_d6r26a_p2_r27p7_bounded_real_full_context_benchmark_preexecution as r27p7


def test_contract_opens_only_bounded_explicit_real_benchmark() -> None:
    r27p7.validate_r27p7_contract()
    assert r27p7.REAL_HISTORICAL_BENCHMARK_AUTHORIZED is True
    assert r27p7.REAL_HISTORICAL_BENCHMARK_REQUIRES_EXPLICIT_AUTHORIZATION is True
    assert r27p7.BENCHMARK_SCOPE_ONE_FROZEN_SOURCE_ONLY is True
    assert r27p7.BENCHMARK_PREFIX_ONLY is True
    assert r27p7.FULL_CONTEXT_OVER_BOUNDED_PREFIX_ONLY is True
    assert r27p7.FULL_DAY_CONTEXT_BUILD_AUTHORIZED is False
    assert r27p7.BENCHMARK_MANIFEST_WRITE_AUTHORIZED is False
    assert r27p7.DURABLE_CONTEXT_WRITE_AUTHORIZED is False
    assert r27p7.P2_ATTEMPT_CONSUMED is False
    assert r27p7.SIMULATOR_LANE_AUTHORIZED is False
    assert r27p7.MODEL_FIT_AUTHORIZED is False
    assert r27p7.PNL_AUTHORIZED is False


def test_r27p6a_itself_remains_historical_closed() -> None:
    r27p6a.validate_r27p6a_contract()
    assert r27p6a.REAL_HISTORICAL_BENCHMARK_AUTHORIZED is False
    assert r27p6a.FULL_JAN_JUL_RERUN_AUTHORIZED is False
    assert r27p6a.DURABLE_CONTEXT_WRITE_AUTHORIZED is False


def test_frozen_source_identity_and_prefix_plan_are_delegated_to_r27p2() -> None:
    assert r27p7.SOURCE_DAY == r27p2.SOURCE_DAY
    assert r27p7.SOURCE_PATH == r27p2.SOURCE_PATH
    assert r27p7.SOURCE_ROWS == r27p2.SOURCE_ROWS
    assert r27p7.SOURCE_BYTES == r27p2.SOURCE_BYTES
    assert r27p7.SOURCE_SHA256 == r27p2.SOURCE_SHA256
    assert r27p7.PREFIX_ROWS == r27p2.PREFIX_ROWS
    assert r27p7.GATE_PREFIX_ROWS == r27p2.GATE_PREFIX_ROWS


def test_real_authorization_is_exact_token_only() -> None:
    assert r27p7.real_benchmark_authorized({}) is False
    assert r27p7.real_benchmark_authorized({r27p7.AUTH_ENV: "YES"}) is False
    assert (
        r27p7.real_benchmark_authorized(
            {r27p7.AUTH_ENV: r27p7.AUTH_TOKEN}
        )
        is True
    )


def test_unauthorized_runner_fails_before_any_filesystem_or_source_open(monkeypatch) -> None:
    def forbidden_probe() -> None:
        raise AssertionError("filesystem_probe_forbidden_before_auth")

    def forbidden_source():
        raise AssertionError("source_open_forbidden_before_auth")

    monkeypatch.setattr(r27p2, "_validate_preattempt_state", forbidden_probe)
    monkeypatch.setattr(r27p2, "_verify_source_identity", forbidden_source)

    with pytest.raises(r27p7.R27P7Error, match="authorization"):
        r27p7.run_real_benchmark(environ={})


def test_loaded_synthetic_prefix_is_exact_full_context_parity_and_ephemeral(
    tmp_path: Path,
) -> None:
    data = r20.make_synthetic_dual_context_fixture()
    observation = r27p7.benchmark_loaded_prefix(
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


def test_parity_failure_is_fail_closed_and_scratch_is_cleaned(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data = r20.make_synthetic_dual_context_fixture()

    def forced_mismatch(*args, **kwargs) -> None:
        del args, kwargs
        raise r27p7.R27P7Error("forced_parity_failure")

    monkeypatch.setattr(r27p7.r27p0, "assert_exact_context_parity", forced_mismatch)

    with pytest.raises(r27p7.R27P7Error, match="forced_parity_failure"):
        r27p7.benchmark_loaded_prefix(
            data,
            prefix_rows=int(data.size),
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
            scratch_root=tmp_path,
        )
    assert list(tmp_path.rglob("exchange_midpoints.bin")) == []


@pytest.mark.parametrize("prefix_rows", [0, -1, r27p7.MAX_BENCHMARK_ROWS + 1])
def test_prefix_bounds_fail_closed(tmp_path: Path, prefix_rows: int) -> None:
    data = r20.make_synthetic_dual_context_fixture()
    with pytest.raises(r27p7.R27P7Error, match="prefix_rows"):
        r27p7.benchmark_loaded_prefix(
            data,
            prefix_rows=prefix_rows,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
            scratch_root=tmp_path,
        )

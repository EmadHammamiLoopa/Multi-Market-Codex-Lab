from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
from multimarket import dev045_d6r26a_p2_r27p18_corrected_5m_speed_benchmark_preexecution as r27p18


def test_r27p18_contract_is_5m_speed_only_and_closed():
    r27p18.validate_r27p18_contract()
    assert r27p18.PREFIX_ROWS == 5_000_000
    assert r27p18.GATE_PREFIX_ROWS == 5_000_000
    assert r27p18.R27P9_L5_AMENDMENT_REQUIRED is True
    assert r27p18.R27P16_VOLATILITY_AMENDMENT_REQUIRED is True
    assert r27p18.JIT_COMPILE_TIME_EXCLUDED is True
    assert r27p18.PARITY_COMPARISON_EXCLUDED_FROM_TIMING is True
    assert r27p18.DIGEST_COMPUTATION_EXCLUDED_FROM_TIMING is True
    assert r27p18.R27P17_RERUN_AUTHORIZED is False
    assert r27p18.P2_ATTEMPT_CONSUMED is False
    assert r27p18.MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED is False


def test_real_benchmark_requires_explicit_authorization(monkeypatch):
    monkeypatch.delenv(r27p18.AUTH_ENV, raising=False)
    with pytest.raises(r27p18.R27P18Error, match="authorization"):
        r27p18._require_real_benchmark_authorized()


def test_synthetic_corrected_full_context_exactly_matches_r20():
    events = r20.make_synthetic_dual_context_fixture()
    reference = None
    candidate = None
    with TemporaryDirectory(prefix="dev045_r27p18_test_") as root:
        try:
            reference = r20.build_once_day_context(
                events,
                nominal_day_start_local_ns=0,
                nominal_day_end_exclusive_local_ns=100_000_000_000,
                scratch_root=Path(root) / "reference",
            )
            candidate, _, _ = r27p18.build_corrected_fused_day_context(
                events,
                nominal_day_start_local_ns=0,
                nominal_day_end_exclusive_local_ns=100_000_000_000,
                scratch_root=Path(root) / "candidate",
            )
            r27p0.assert_exact_context_parity(reference, candidate)
            assert r27p0.digest_day_context(reference) == r27p0.digest_day_context(candidate)
            assert reference.midpoint_index.sha256 == candidate.midpoint_index.sha256
            assert reference.midpoint_index.bytes == candidate.midpoint_index.bytes
        finally:
            if reference is not None and not reference.midpoint_index.closed:
                r20.close_midpoint_index(reference.midpoint_index)
            if candidate is not None and not candidate.midpoint_index.closed:
                r20.close_midpoint_index(candidate.midpoint_index)

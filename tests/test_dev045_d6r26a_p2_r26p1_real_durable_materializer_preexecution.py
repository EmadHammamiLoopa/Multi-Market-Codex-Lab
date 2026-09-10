from __future__ import annotations

import pytest

from multimarket import (
    dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4,
)
from multimarket import (
    dev045_d6r26a_p2_r22_final_successor_campaign_runner_binding_preauthorization as r22,
)
from multimarket import (
    dev045_d6r26a_p2_r26p0_durable_materialization_freeze as r26p0,
)
from multimarket import (
    dev045_d6r26a_p2_r26p1_real_durable_materializer_preexecution as r26p1,
)


def _verified_sources_without_io() -> tuple[r4.VerifiedSource, ...]:
    return tuple(
        r4.VerifiedSource(
            day=day,
            path=r26p0.source_identity(day).path,
            rows=r26p0.source_identity(day).rows,
            bytes=r26p0.source_identity(day).bytes,
            sha256=r26p0.source_identity(day).sha256,
        )
        for day in r26p0.EXPECTED_DAYS
    )


def test_r26p1_contract() -> None:
    r26p1.validate_r26p1_contract()


def test_authorization_is_explicit() -> None:
    with pytest.raises(
        r26p1.R26P1MaterializationError,
        match="authorization_denied",
    ):
        r26p1.require_authorization(None)

    r26p1.require_authorization(r26p1.AUTH_TOKEN)


def test_verified_source_identity_is_exact_without_io() -> None:
    for source in _verified_sources_without_io():
        identity = r26p1._source_identity_from_verified(source)
        assert identity == r26p0.source_identity(source.day)


def test_memory_growth_guard() -> None:
    baseline = r22.MemorySnapshot(
        mem_available_bytes=30 * r26p0.GIB,
        rss_anon_bytes=100,
        vm_swap_bytes=0,
    )
    good = r22.MemorySnapshot(
        mem_available_bytes=20 * r26p0.GIB,
        rss_anon_bytes=200,
        vm_swap_bytes=0,
    )
    r26p1._validate_memory_growth(
        baseline=baseline,
        observed=good,
        stage="synthetic",
    )

    low = r22.MemorySnapshot(
        mem_available_bytes=(
            r26p0.RUNTIME_MEMAVAILABLE_ABORT_BYTES - 1
        ),
        rss_anon_bytes=200,
        vm_swap_bytes=0,
    )
    with pytest.raises(
        r26p1.R26P1MaterializationError,
        match="runtime_memavailable",
    ):
        r26p1._validate_memory_growth(
            baseline=baseline,
            observed=low,
            stage="synthetic",
        )

    swapped = r22.MemorySnapshot(
        mem_available_bytes=20 * r26p0.GIB,
        rss_anon_bytes=200,
        vm_swap_bytes=4096,
    )
    with pytest.raises(
        r26p1.R26P1MaterializationError,
        match="process_swap_growth",
    ):
        r26p1._validate_memory_growth(
            baseline=baseline,
            observed=swapped,
            stage="synthetic",
        )


def test_missing_bundles_are_pending_without_historical_io() -> None:
    completed, pending = r26p1.classify_completed_bundles(
        _verified_sources_without_io()
    )

    # GitHub CI has no real durable root. This proves classification itself
    # does not open or rehash Jan-Jul raw sources.
    assert completed == ()
    assert tuple(item.day for item in pending) == r26p0.EXPECTED_DAYS


def test_completion_payload_is_stable_and_pre_attempt() -> None:
    records = tuple(
        r26p1.DayBundleRecord(
            day=day,
            source_sha256=r26p0.source_identity(day).sha256,
            bundle_dir=str(r26p0.durable_day_dir(day)),
            day_manifest_sha256="a" * 64,
            disposition="BUILT_VERIFIED",
        )
        for day in r26p0.EXPECTED_DAYS
    )

    payload = r26p1._completion_payload(records)

    assert payload["status"] == (
        "ALL_SEVEN_DURABLE_CONTEXTS_VERIFIED"
    )
    assert payload["verified_bundle_count"] == 7
    assert payload["p2_attempt_consumed"] is False
    assert payload["simulator_run"] is False
    assert payload["canonical_labels_written"] is False
    assert payload["model_fit"] is False
    assert payload["pnl"] is False


def test_execution_surfaces_remain_separated() -> None:
    assert r26p1.REAL_DURABLE_MATERIALIZER_IMPLEMENTED is True

    assert (
        r26p1.REAL_JAN_JUL_SOURCE_REHASH_WITH_TOKEN_AUTHORIZED
        is True
    )
    assert (
        r26p1.REAL_JAN_JUL_SOURCE_OPEN_WITH_TOKEN_AUTHORIZED
        is True
    )
    assert (
        r26p1.REAL_R20_CONTEXT_BUILD_WITH_TOKEN_AUTHORIZED
        is True
    )

    assert r26p1.P2_ATTEMPT_CONSUMED is False
    assert r26p1.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r26p1.SIMULATOR_LANE_AUTHORIZED is False
    assert r26p1.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r26p1.MODEL_FIT_AUTHORIZED is False
    assert r26p1.PNL_AUTHORIZED is False

    assert r26p1.CI_OPENS_HISTORICAL_SOURCE is False
    assert r26p1.CI_REHASHES_HISTORICAL_SOURCE is False
    assert r26p1.CI_BUILDS_REAL_CONTEXT is False
    assert r26p1.CI_RUNS_SIMULATOR is False

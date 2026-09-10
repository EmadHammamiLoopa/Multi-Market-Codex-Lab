from __future__ import annotations

from multimarket import (
    dev045_d6r26a_p2_r2_frozen_source_registry as r2,
)
from multimarket import (
    dev045_d6r26a_p2_r26p0_durable_materialization_freeze as r26,
)


def test_r26p0_contract() -> None:
    r26.validate_r26p0_contract()


def test_exact_jan_jul_identity_without_io() -> None:
    assert r26.EXPECTED_DAYS == (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    )

    assert tuple(
        r26.source_identity(day).sha256
        for day in r26.EXPECTED_DAYS
    ) == tuple(
        record.sha256
        for record in r2.FROZEN_SOURCE_REGISTRY
    )


def test_memory_admission_boundaries() -> None:
    one = r26.MIN_MEMAVAILABLE_ONE_WORKER_BYTES
    two = r26.MIN_MEMAVAILABLE_TWO_WORKERS_BYTES

    assert r26.admitted_worker_limit(one - 1) == 0
    assert r26.admitted_worker_limit(one) == 1
    assert r26.admitted_worker_limit(two - 1) == 1
    assert r26.admitted_worker_limit(two) == 2
    assert r26.admitted_worker_limit(100 * r26.GIB) == 2


def test_worker_cap_is_conservative_successor_of_r24() -> None:
    assert r26.R24_MAX_PARALLEL_CAP == 4
    assert r26.R26_BUILD_WORKER_CAP == 2
    assert r26.R26_BUILD_WORKER_CAP <= r26.R24_MAX_PARALLEL_CAP


def test_restart_semantics_are_pre_attempt() -> None:
    assert r26.P2_ATTEMPT_CONSUMED is False
    assert r26.ATTEMPT_MARKER_WRITE_AUTHORIZED is False

    assert (
        r26.COMPLETED_DAY_REUSE_AFTER_RESTART_AUTHORIZED
        is True
    )

    assert (
        r26.PARTIAL_STAGING_REUSE_FORBIDDEN
        is True
    )

    assert (
        r26.PARTIAL_STAGING_AUTO_DELETE_AUTHORIZED
        is False
    )


def test_no_historical_execution_in_r26p0() -> None:
    assert r26.THIS_COMMIT_OPENS_HISTORICAL_SOURCE is False
    assert r26.THIS_COMMIT_REHASHES_HISTORICAL_SOURCE is False
    assert r26.THIS_COMMIT_BUILDS_REAL_CONTEXT is False
    assert r26.THIS_COMMIT_RUNS_SIMULATOR is False
    assert r26.THIS_COMMIT_WRITES_CANONICAL_LABELS is False

    assert r26.MODEL_FIT_AUTHORIZED is False
    assert r26.PNL_AUTHORIZED is False

    assert r26.AUG_OPEN_AUTHORIZED is False
    assert r26.SEP_PLUS_OPEN_AUTHORIZED is False
    assert r26.NON_BTC_OPEN_AUTHORIZED is False


def test_durable_paths_are_exact() -> None:
    assert str(r26.DURABLE_ROOT) == (
        "/home/emadh/Multi-Market/runtime/"
        "dev045_d6r26a_p2_durable_context_v1"
    )

    assert str(
        r26.durable_day_dir("2026-01-01")
    ).endswith(
        "dev045_d6r26a_p2_durable_context_v1/2026-01-01"
    )

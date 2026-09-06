from __future__ import annotations

import pytest

from multimarket import (
    dev045_d6r17_direct_action_support as s,
)


def test_execution_surfaces_stay_closed():
    assert (
        s.SUPPORT_EVIDENCE_FILE_IO_ENABLED
        is True
    )

    assert (
        s.CANONICAL_MARKET_FILE_IO_ENABLED
        is False
    )

    assert (
        s.HFTBACKTEST_EXECUTION_ENABLED
        is False
    )

    assert (
        s.POLICY_EXECUTION_ENABLED
        is False
    )

    assert (
        s.HISTORICAL_PNL_ENABLED
        is False
    )

    assert (
        s.ECONOMIC_ARENA_EXECUTION_ENABLED
        is False
    )

    assert (
        s.CANONICAL_PNL_WRITE_ENABLED
        is False
    )

    assert (
        s.NETWORK_ACQUISITION_ENABLED
        is False
    )

    assert s.RAILWAY_ENABLED is False
    assert s.LIVE_TRADING_AUTHORIZED is False


def test_exact_frozen_policy_mapping():
    assert s.POLICY_TO_CORE_COLUMN[
        "M06"
    ] == (
        "T10_READY",
        "T10_ACTION",
        "T10A_ACTION",
    )

    assert s.POLICY_TO_CORE_COLUMN[
        "M07"
    ] == (
        "T05_READY",
        "T05_ACTION",
        "T05A_ACTION",
    )


def test_no_probability_reconstruction_or_fill():
    assert s.FORWARD_FILL_ENABLED is False
    assert s.BACKFILL_ENABLED is False
    assert s.INTERPOLATION_ENABLED is False
    assert s.NEAREST_NEIGHBOR_ENABLED is False
    assert s.A0_REFIT_ENABLED is False
    assert s.A0_RETRAIN_ENABLED is False

    assert (
        s.LEGACY_STATE_REMATERIALIZATION_ENABLED
        is False
    )


def test_frozen_day_identity():
    assert tuple(
        x.day
        for x in s.DAY_SPECS
    ) == s.DIRECT_SUPPORT_DAYS

    assert sum(
        x.rows
        for x in s.DAY_SPECS
    ) == 5516

    assert sum(
        x.t05_ready
        for x in s.DAY_SPECS
    ) == 5516

    assert sum(
        x.t10_ready
        for x in s.DAY_SPECS
    ) == 5506


def test_exact_index_distinguishes_missing_from_abstain():
    idx = s.DirectActionIndex(
        day="2026-04-01",
        policy_id="M06",
        points=(
            s.DirectActionPoint(
                timestamp_us=60_000_000,
                direction=0,
                ready=False,
            ),
            s.DirectActionPoint(
                timestamp_us=120_000_000,
                direction=1,
                ready=True,
            ),
        ),
    )

    explicit = idx.exact(
        60_000_000
    )

    assert explicit is not None
    assert explicit.direction == 0
    assert explicit.ready is False

    assert idx.exact(
        90_000_000
    ) is None

    active = idx.exact(
        120_000_000
    )

    assert active is not None
    assert active.direction == 1
    assert active.ready is True


def test_unavailable_nonzero_is_rejected():
    with pytest.raises(
        s.DirectActionSupportError,
        match="unavailable_nonzero_direction",
    ):
        s.DirectActionPoint(
            timestamp_us=60_000_000,
            direction=1,
            ready=False,
        )


def test_index_requires_exact_utc_minute():
    with pytest.raises(
        s.DirectActionSupportError,
        match="not_exact_utc_minute",
    ):
        s.DirectActionIndex(
            day="2026-04-01",
            policy_id="M07",
            points=(
                s.DirectActionPoint(
                    timestamp_us=60_000_001,
                    direction=0,
                    ready=True,
                ),
            ),
        )


def test_jan_mar_are_base_only():
    assert s.BASE_ONLY_DAYS == (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
    )

    for spec in s.DAY_SPECS:
        assert spec.day not in s.BASE_ONLY_DAYS

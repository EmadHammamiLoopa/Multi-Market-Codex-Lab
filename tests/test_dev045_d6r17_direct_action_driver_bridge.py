from __future__ import annotations

import pytest

from multimarket import (
    dev045_d6r17_direct_action_driver_bridge as b,
)
from multimarket import (
    dev045_d6r17_direct_action_support as s,
)


def index(
    day: str,
    policy: str,
    *points,
):
    return s.DirectActionIndex(
        day=day,
        policy_id=policy,
        points=tuple(points),
    )


def point(
    minute: int,
    direction: int,
    ready: bool = True,
):
    return s.DirectActionPoint(
        timestamp_us=(
            minute
            * 60_000_000
        ),
        direction=direction,
        ready=ready,
    )


def test_execution_surfaces_closed():
    assert (
        b.CANONICAL_SOURCE_OPEN_IMPLEMENTED
        is False
    )

    assert (
        b.CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT
        is False
    )

    assert b.AUTOMATIC_RETRY is False
    assert b.CANONICAL_PNL_WRITE_ENABLED is False
    assert b.NETWORK_ACQUISITION_ENABLED is False
    assert b.LIVE_TRADING_AUTHORIZED is False


def test_jan_mar_are_base_only():
    r = b.resolve_direct_action_clock(
        day="2026-01-01",
        policy_id="M06",
        timestamp_us=60_000_000,
        previous_direction=1,
        index=None,
    )

    assert r.mode == b.MODE_BASE_ONLY
    assert r.active_direction == 0
    assert r.queried_support is False


def test_intermediate_second_persists_only_direction():
    idx = index(
        "2026-04-01",
        "M06",
        point(1, 1),
    )

    r = b.resolve_direct_action_clock(
        day="2026-04-01",
        policy_id="M06",
        timestamp_us=61_000_000,
        previous_direction=-1,
        index=idx,
    )

    assert r.mode == b.MODE_NO_ALPHA_UPDATE
    assert r.active_direction == -1
    assert r.queried_support is False
    assert r.exact_row_present is False


def test_exact_frozen_long_action():
    idx = index(
        "2026-04-01",
        "M07",
        point(1, 1),
    )

    r = b.resolve_direct_action_clock(
        day="2026-04-01",
        policy_id="M07",
        timestamp_us=60_000_000,
        previous_direction=-1,
        index=idx,
    )

    assert r.mode == b.MODE_DIRECT_FROZEN_ACTION
    assert r.active_direction == 1
    assert r.queried_support is True
    assert r.exact_row_present is True


def test_explicit_frozen_abstain_is_not_missing():
    idx = index(
        "2026-04-01",
        "M06",
        point(
            1,
            0,
            ready=False,
        ),
    )

    r = b.resolve_direct_action_clock(
        day="2026-04-01",
        policy_id="M06",
        timestamp_us=60_000_000,
        previous_direction=1,
        index=idx,
    )

    assert r.mode == b.MODE_DIRECT_FROZEN_ABSTAIN
    assert r.active_direction == 0
    assert r.queried_support is True
    assert r.exact_row_present is True


def test_missing_exact_row_falls_back_to_m02():
    idx = index(
        "2026-04-01",
        "M06",
        point(2, 1),
    )

    r = b.resolve_direct_action_clock(
        day="2026-04-01",
        policy_id="M06",
        timestamp_us=60_000_000,
        previous_direction=1,
        index=idx,
    )

    assert r.mode == b.MODE_FALLBACK_TO_M02
    assert r.active_direction == 0
    assert r.queried_support is True
    assert r.exact_row_present is False


def test_apr_jul_adapter_requires_index():
    with pytest.raises(
        b.DirectActionBridgeError,
        match="required_direct_index_missing",
    ):
        b.resolve_direct_action_clock(
            day="2026-04-01",
            policy_id="M06",
            timestamp_us=60_000_000,
            previous_direction=0,
            index=None,
        )


def test_wrong_policy_index_rejected():
    idx = index(
        "2026-04-01",
        "M07",
        point(1, 1),
    )

    with pytest.raises(
        b.DirectActionBridgeError,
        match="direct_index_policy",
    ):
        b.validate_direct_index(
            policy_id="M06",
            day="2026-04-01",
            index=idx,
        )


def test_nonadapter_cannot_receive_direct_index():
    idx = index(
        "2026-04-01",
        "M06",
        point(1, 1),
    )

    with pytest.raises(
        b.DirectActionBridgeError,
        match="direct_index_for_nonadapter",
    ):
        b.validate_direct_index(
            policy_id="M01",
            day="2026-04-01",
            index=idx,
        )


def test_day_mapping_exact_identity():
    m06 = index(
        "2026-04-01",
        "M06",
        point(1, 0),
    )

    m07 = index(
        "2026-04-01",
        "M07",
        point(1, 0),
    )

    b._validate_day_mapping(
        day="2026-04-01",
        direct_by_policy={
            "M06": m06,
            "M07": m07,
        },
    )

    with pytest.raises(
        b.DirectActionBridgeError,
        match="support_mapping_identity",
    ):
        b._validate_day_mapping(
            day="2026-04-01",
            direct_by_policy={
                "M06": m06,
            },
        )


def test_replay_counter_identity():
    class Replay:
        pass

    x = b.DirectActionReplayResult(
        replay=Replay(),
        direct_action_queries=5,
        direct_action_rows_found=4,
        direct_action_missing_rows=1,
        direct_action_explicit_abstains=2,
    )

    assert x.direct_action_queries == 5

    with pytest.raises(
        b.DirectActionBridgeError,
        match="query_counter_identity",
    ):
        b.DirectActionReplayResult(
            replay=Replay(),
            direct_action_queries=5,
            direct_action_rows_found=3,
            direct_action_missing_rows=1,
            direct_action_explicit_abstains=0,
        )

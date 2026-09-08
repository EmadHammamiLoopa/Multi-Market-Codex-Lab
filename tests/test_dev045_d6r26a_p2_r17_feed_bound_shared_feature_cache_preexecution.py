from __future__ import annotations

import numpy as np
import pytest

from multimarket import (
    dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0,
)
from multimarket import (
    dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17,
)


DTYPE = np.dtype(
    [
        ("ev", "<u8"),
        ("exch_ts", "<i8"),
        ("local_ts", "<i8"),
        ("px", "<f8"),
        ("qty", "<f8"),
    ]
)


def _events(*local_times: int) -> np.ndarray:
    a = np.zeros(len(local_times), dtype=DTYPE)

    for i, local in enumerate(local_times):
        a[i]["local_ts"] = int(local)
        a[i]["exch_ts"] = max(0, int(local) - 1)

    return a


def test_r17_contract_is_preexecution_and_one_raw_feature_pass():
    r17.validate_r17_contract()

    assert r17.NATURAL_END_OF_DATA_IS_VALID_TERMINAL is True
    assert r17.EXPECTED_SUCCESS_TERMINAL_REASON == "NATURAL_END_OF_DATA"

    assert r17.FIXED_EVENT_TARGET is None
    assert r17.FIXED_WAKEUP_TARGET is None
    assert r17.REFERENCE_WAKEUP_COUNT_IS_STOP_CONDITION is False
    assert r17.NOMINAL_DAY_END_IS_STOP_CONDITION is False

    assert r17.RAW_FEATURE_PASSES_PER_DAY == 1
    assert r17.PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN is True
    assert r17.FEATURE_CACHE_SHARED_ACROSS_ALL_40_LANES is True

    assert r17.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r17.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r17.P2_ATTEMPT_CONSUMED if hasattr(r17, "P2_ATTEMPT_CONSUMED") else True


def test_feed_end_is_last_observed_local_plus_one_not_nominal_day_end():
    a = _events(
        1_000_000_000,
        20_000_000_000,
        47_300_000_000,
    )

    bounds = r17.derive_feed_bounds(
        a,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
    )

    assert bounds.first_observed_local_ns == 1_000_000_000
    assert bounds.last_observed_local_ns == 47_300_000_000
    assert bounds.feed_end_exclusive_local_ns == 47_300_000_001

    assert (
        bounds.feed_end_exclusive_local_ns
        != bounds.nominal_day_end_exclusive_local_ns
    )


def test_phase_union_stops_at_actual_feed_and_covers_each_second_once():
    a = _events(
        1_000_000_000,
        47_300_000_000,
    )

    bounds = r17.derive_feed_bounds(
        a,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
    )

    grid = r17.build_shared_decision_grid(
        bounds=bounds,
    )

    assert grid == tuple(
        range(
            30_000_000_000,
            48_000_000_000,
            1_000_000_000,
        )
    )

    assert max(grid) == 47_000_000_000
    assert max(grid) <= bounds.last_observed_local_ns

    by_phase = {
        phase: r17.build_phase_decisions(
            bounds=bounds,
            phase=phase,
        )
        for phase in p0.LANE_PHASE_OFFSETS_S
    }

    assert sorted(
        ts
        for epochs in by_phase.values()
        for ts in epochs
    ) == list(grid)

    for epochs in by_phase.values():
        assert all(
            b - a == p0.MAX_CANDIDATE_LIFETIME_NS
            for a, b in zip(epochs, epochs[1:])
        )


def test_decision_exactly_at_final_feed_timestamp_is_retained():
    a = _events(
        1_000_000_000,
        47_000_000_000,
    )

    bounds = r17.derive_feed_bounds(
        a,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
    )

    grid = r17.build_shared_decision_grid(
        bounds=bounds,
    )

    assert grid[-1] == 47_000_000_000
    assert grid[-1] == bounds.last_observed_local_ns


def test_no_decision_is_generated_after_eof():
    a = _events(
        1_000_000_000,
        47_999_999_999,
    )

    bounds = r17.derive_feed_bounds(
        a,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
    )

    grid = r17.build_shared_decision_grid(
        bounds=bounds,
    )

    assert grid[-1] == 47_000_000_000
    assert 48_000_000_000 not in grid


def test_short_feed_before_warmup_produces_no_candidates_not_failure():
    a = _events(
        1_000_000_000,
        20_000_000_000,
    )

    bounds = r17.derive_feed_bounds(
        a,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=100_000_000_000,
    )

    assert r17.build_shared_decision_grid(
        bounds=bounds,
    ) == ()


def test_empty_feed_fails_closed():
    with pytest.raises(
        r17.FeedBoundScheduleError,
        match="source_empty",
    ):
        r17.derive_feed_bounds(
            np.zeros(0, dtype=DTYPE),
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=100_000_000_000,
        )


def test_dense_full_day_feature_cache_is_bounded_below_256_mib():
    full_day_decisions = len(
        range(
            30_000_000_000,
            r17.NOMINAL_DAY_NS,
            1_000_000_000,
        )
    )

    layout = r17.feature_cache_layout(
        decision_count=full_day_decisions,
    )

    assert layout.decision_count == 86_370
    assert layout.candidate_grid_cases == 8
    assert layout.feature_count == 25

    assert layout.total_bytes < 256 * 1024 * 1024
    assert layout.total_bytes < 150 * 1024 * 1024


def test_cache_budget_fails_closed_if_unbounded_cardinality_is_requested():
    with pytest.raises(
        r17.FeedBoundScheduleError,
        match="feature_cache_too_large",
    ):
        r17.feature_cache_layout(
            decision_count=1_000_000,
        )

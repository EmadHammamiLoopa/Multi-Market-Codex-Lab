from __future__ import annotations

import numpy as np
import pytest

from multimarket import (
    dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0,
)
from multimarket import (
    dev045_d6r26a_p1_synthetic_candidate_labeler as p1,
)
from multimarket import (
    dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1,
)
from multimarket import (
    dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b,
)
from multimarket import (
    dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9,
)
from multimarket import (
    dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17,
)
from multimarket import (
    dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18,
)
from multimarket import (
    dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19,
)


def _build():
    data = r19.make_synthetic_feature_fixture()

    result = r19.build_once_day_dense_feature_cache(
        data,
        nominal_day_start_local_ns=0,
        nominal_day_end_exclusive_local_ns=(
            100_000_000_000
        ),
    )

    return data, result


def test_r19_contract_is_strictly_preauthorization():
    r19.validate_r19_contract()

    assert r19.RAW_EVENT_PASSES_PER_DAY == 1
    assert (
        r19.EXCHANGE_MIDPOINT_PASS_FOR_FEATURE_CACHE
        is False
    )
    assert (
        r19.PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN
        is True
    )
    assert r19.CACHE_SHARED_ACROSS_40_LANES is True

    assert (
        r19.LEADING_PREELIGIBLE_EPOCHS_AUDITED_NOT_DROPPED_ROWS
        is True
    )
    assert (
        r19.INELIGIBILITY_AFTER_FIRST_ELIGIBLE_EPOCH_FAILS_CLOSED
        is True
    )

    assert r19.P2_ATTEMPT_CONSUMED is False
    assert r19.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r19.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r19.CANONICAL_LABEL_WRITE_AUTHORIZED is False


def test_requested_30s_epoch_is_audited_preeligible_and_cache_starts_31s():
    _, result = _build()

    summary = result.summary
    cache = result.cache

    # R17 requested grid: 30s .. 47s.
    assert summary.requested_decision_count == 18
    assert summary.first_requested_local_ns == 30_000_000_000

    # First complete book is at 1s. Therefore 30s has only 29s causal
    # support; 31s is the first eligible candidate epoch.
    assert summary.leading_preeligible_count == 1
    assert summary.first_eligible_local_ns == 31_000_000_000
    assert summary.last_eligible_local_ns == 47_000_000_000
    assert summary.eligible_decision_count == 17
    assert summary.raw_event_pass_count == 1

    assert cache.decision_local_ns.tolist() == list(
        range(
            31_000_000_000,
            48_000_000_000,
            1_000_000_000,
        )
    )

    assert cache.values.shape == (17, 8, 25)


def test_cache_is_exact_r17_dense_layout_and_readonly():
    _, result = _build()

    cache = result.cache

    layout = r17.feature_cache_layout(
        decision_count=17,
    )

    assert cache.total_bytes == layout.total_bytes
    assert cache.values.dtype == np.dtype("<f8")

    assert cache.decision_local_ns.flags.writeable is False
    assert cache.best_bid_tick.flags.writeable is False
    assert cache.best_ask_tick.flags.writeable is False
    assert cache.values.flags.writeable is False

    assert not hasattr(cache, "events")
    assert not hasattr(cache, "books")
    assert not hasattr(cache, "flows")
    assert not hasattr(cache, "decoder")
    assert not hasattr(cache, "accumulator")


def test_all_eight_cases_at_31s_match_frozen_r8b_batch_semantics():
    data, result = _build()

    history = r9.decode_local_history(
        data
    )

    decision = 31_000_000_000

    current = r8b.book_asof(
        books=history.books,
        target_local_ns=decision,
    )

    for side, distance in r18.CANDIDATE_GRID:
        candidate = p1.CandidateSpec(
            side=side,
            distance_ticks=int(distance),
            decision_local_ns=decision,
            best_bid_tick=int(
                current.best_bid.price_tick
            ),
            best_ask_tick=int(
                current.best_ask.price_tick
            ),
        )

        expected = r8b.compute_features(
            candidate=candidate,
            books=history.books,
            flows=history.flows,
        )

        observed = r18.lookup_feature_vector(
            cache=result.cache,
            candidate=candidate,
        )

        assert tuple(observed.values) == tuple(
            expected.values
        )

        for name in r8b.FEATURE_NAMES:
            assert observed.values[name] == pytest.approx(
                expected.values[name],
                rel=0.0,
                abs=1e-12,
            )

            assert (
                observed.observable_local_ns[name]
                == decision
            )


@pytest.mark.parametrize(
    "decision",
    (
        31_000_000_000,
        36_000_000_000,
        41_000_000_000,
        46_000_000_000,
    ),
)
def test_bid_d0_sequential_phase_feature_lookup_is_stable(decision):
    _, result = _build()

    index = int(
        np.searchsorted(
            result.cache.decision_local_ns,
            decision,
        )
    )

    candidate = p1.CandidateSpec(
        side="BID",
        distance_ticks=0,
        decision_local_ns=decision,
        best_bid_tick=int(
            result.cache.best_bid_tick[index]
        ),
        best_ask_tick=int(
            result.cache.best_ask_tick[index]
        ),
    )

    observed = r18.lookup_feature_vector(
        cache=result.cache,
        candidate=candidate,
    )

    assert observed.support
    assert all(
        ts == decision
        for ts in observed.observable_local_ns.values()
    )


def test_lane_schedule_is_derived_only_from_eligible_cache():
    _, result = _build()

    lane = next(
        lane
        for lane in r1.build_materialization_plan()
        if (
            lane.side == "BID"
            and lane.distance_ticks == 0
            and lane.phase == 1
        )
    )

    decisions = r19.lane_decisions_from_cache(
        cache=result.cache,
        lane=lane,
        day_start_local_ns=0,
    )

    assert decisions == (
        31_000_000_000,
        36_000_000_000,
        41_000_000_000,
        46_000_000_000,
    )

    assert all(
        b - a == p0.MAX_CANDIDATE_LIFETIME_NS
        for a, b in zip(
            decisions,
            decisions[1:],
        )
    )

    assert 30_000_000_000 not in decisions


def test_no_decision_after_actual_feed_eof_enters_cache():
    _, result = _build()

    assert (
        int(result.cache.decision_local_ns[-1])
        <= result.bounds.last_observed_local_ns
    )

    assert 48_000_000_000 not in set(
        map(
            int,
            result.cache.decision_local_ns,
        )
    )


def test_short_feed_with_no_30s_support_fails_closed_not_empty_cache():
    data = r19.make_synthetic_feature_fixture()

    short = data[
        data["local_ts"] <= 20_000_000_000
    ]

    with pytest.raises(
        r19.OnceDayFeatureCacheError,
        match="requested_decision_grid_empty",
    ):
        r19.build_once_day_dense_feature_cache(
            short,
            nominal_day_start_local_ns=0,
            nominal_day_end_exclusive_local_ns=(
                100_000_000_000
            ),
        )

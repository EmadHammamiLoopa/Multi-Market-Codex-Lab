from __future__ import annotations

import pytest

from multimarket import (
    dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0,
)
from multimarket import (
    dev045_d6r26a_p1_synthetic_candidate_labeler as p1,
)
from multimarket import (
    dev045_d6r26a_p2_r15_sequential_lane_real_engine_preexecution as r15,
)


def test_r15_contract_is_strictly_synthetic():
    r15.validate_r15_contract()

    assert r15.SYNTHETIC_REAL_ENGINE_ONLY is True
    assert r15.SEQUENTIAL_SAME_ENGINE_LANE_FROZEN is True

    assert r15.SEQUENTIAL_DECISION_LOCAL_NS == (
        31_000_000_000,
        36_000_000_000,
        41_000_000_000,
    )

    assert r15.FIXED_EVENT_TARGET is None
    assert r15.FIXED_WAKEUP_TARGET is None
    assert r15.TOTAL_RSS_ABORT_THRESHOLD_BYTES is None
    assert r15.TOTAL_RSS_IS_BOUNDEDNESS_GATE is False

    assert (
        r15.END_OF_SOURCE_CANDIDATES_RETAINED_WITH_CENSORING
        is True
    )
    assert r15.CENSORED_MAPS_TO_NO_FILL is False

    assert r15.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r15.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r15.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r15.MODEL_FIT_AUTHORIZED is False
    assert r15.PNL_AUTHORIZED is False


@pytest.mark.parametrize(
    "side",
    ("BID", "ASK"),
)
def test_three_candidates_share_one_engine_and_exact_boundaries(side):
    result = r15.run_sequential_lane(
        side=side,
        distance_ticks=0,
    )

    assert result.side == side
    assert len(result.candidates) == 3

    decisions = tuple(
        x.candidate.decision_local_ns
        for x in result.candidates
    )

    assert decisions == r15.SEQUENTIAL_DECISION_LOCAL_NS

    for item in result.candidates:
        decision = item.candidate.decision_local_ns

        assert item.placement_outcome == p1.POST_ONLY_ACCEPTED
        assert item.final_status == p1.HFT_CANCELED

        assert item.cancel_request_local_ns == (
            decision
            + p0.MAX_CANDIDATE_LIFETIME_NS
            - p0.ENTRY_LATENCY_NS
            - p0.RESPONSE_LATENCY_NS
        )

        assert item.terminal_local_ns == (
            decision
            + p0.MAX_CANDIDATE_LIFETIME_NS
        )

        assert item.ack_latency_triplet == (
            decision,
            decision + p0.ENTRY_LATENCY_NS,
            decision
            + p0.ENTRY_LATENCY_NS
            + p0.RESPONSE_LATENCY_NS,
        )

        # Exact R11 correction stays frozen for every candidate.
        assert item.cancel_latency_triplet == (
            decision,
            item.cancel_request_local_ns
            + p0.ENTRY_LATENCY_NS,
            item.terminal_local_ns,
        )

        assert all(
            ts <= decision
            for ts in item.feature_vector.observable_local_ns.values()
        )

    # Critical same-timestamp sequencing guard:
    # prior cancel response completes at exactly next decision.
    assert (
        result.candidates[0].terminal_local_ns
        == result.candidates[1].candidate.decision_local_ns
    )
    assert (
        result.candidates[1].terminal_local_ns
        == result.candidates[2].candidate.decision_local_ns
    )


def test_eof_candidate_is_retained_and_partially_censored():
    labels = {
        int(x.horizon_ns): x
        for x in r15.eof_fill_label_probe()
    }

    assert (
        labels[250_000_000].state
        == p1.NOT_FILLED_WITHIN_TAU
    )
    assert (
        labels[500_000_000].state
        == p1.NOT_FILLED_WITHIN_TAU
    )
    assert (
        labels[1_000_000_000].state
        == p1.NOT_FILLED_WITHIN_TAU
    )

    assert (
        labels[2_000_000_000].state
        == p1.CENSORED
    )
    assert (
        labels[5_000_000_000].state
        == p1.CENSORED
    )

    assert (
        labels[2_000_000_000].any_fill_within_tau
        is None
    )
    assert (
        labels[5_000_000_000].any_fill_within_tau
        is None
    )

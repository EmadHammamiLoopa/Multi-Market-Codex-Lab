from __future__ import annotations

import math
import pytest

from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1


def candidate(side="BID"):
    return p1.CandidateSpec(
        side=side,
        distance_ticks=0,
        decision_local_ns=1_000_000_000,
        best_bid_tick=1000,
        best_ask_tick=1001,
    )


def test_contract_closed():
    p1.validate_p1_contract()
    assert p1.SYNTHETIC_ONLY is True
    assert p1.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert p1.CANONICAL_LABEL_MATERIALIZATION_AUTHORIZED is False
    assert p1.MODEL_FIT_AUTHORIZED is False
    assert p1.PNL_AUTHORIZED is False


def test_candidate_price_and_sign():
    b = candidate("BID")
    a = candidate("ASK")
    assert b.price_tick == 1000
    assert a.price_tick == 1001
    assert b.side_sign == 1
    assert a.side_sign == -1


def test_lane_phase_and_isolation():
    start = 10_000_000_000
    assert p1.lane_phase(day_start_local_ns=start, decision_local_ns=start) == 0
    assert p1.lane_phase(day_start_local_ns=start, decision_local_ns=start + 4_000_000_000) == 4
    assert p1.lane_phase(day_start_local_ns=start, decision_local_ns=start + 5_000_000_000) == 0
    p1.assert_lane_isolation((start, start + 5_000_000_000, start + 10_000_000_000))
    with pytest.raises(p1.CandidateLabelerError, match="lane_overlap"):
        p1.assert_lane_isolation((start, start + 4_000_000_000))


def test_feature_observability_fail_closed():
    p1.validate_feature_observability(
        decision_local_ns=100,
        feature_observable_local_ns={"ok": 100, "old": 99},
    )
    with pytest.raises(p1.CandidateLabelerError, match="future_feature"):
        p1.validate_feature_observability(
            decision_local_ns=100,
            feature_observable_local_ns={"future": 101},
        )


def test_fill_label_observed_fill():
    c = candidate()
    fills = (
        p1.FillObservation(
            exchange_execution_ns=1_200_000_000,
            local_response_ns=1_450_000_000,
            qty=0.001,
            price=100.0,
        ),
    )
    x = p1.fill_horizon_label(
        candidate=c,
        fills=fills,
        horizon_ns=250_000_000,
        source_exchange_observed_through_ns=2_000_000_000,
        placement_outcome=p1.POST_ONLY_ACCEPTED,
    )
    assert x.state == p1.FILLED_WITHIN_TAU
    assert x.any_fill_within_tau is True
    assert math.isclose(x.fill_fraction_at_tau, 1.0)
    assert x.time_to_first_fill_ns == 200_000_000
    assert x.time_to_full_fill_ns == 200_000_000


def test_censored_is_not_no_fill():
    c = candidate()
    x = p1.fill_horizon_label(
        candidate=c,
        fills=(),
        horizon_ns=1_000_000_000,
        source_exchange_observed_through_ns=1_500_000_000,
        placement_outcome=p1.POST_ONLY_ACCEPTED,
    )
    assert x.state == p1.CENSORED
    assert x.any_fill_within_tau is None
    assert x.fill_fraction_at_tau is None
    assert x.fill_fraction_censored is True


def test_post_only_rejection_is_observed_no_fill():
    c = candidate()
    x = p1.fill_horizon_label(
        candidate=c,
        fills=(),
        horizon_ns=5_000_000_000,
        source_exchange_observed_through_ns=1_300_000_000,
        placement_outcome=p1.POST_ONLY_REJECTED_AT_ARRIVAL,
    )
    assert x.state == p1.NOT_FILLED_WITHIN_TAU
    assert x.any_fill_within_tau is False
    assert x.fill_fraction_at_tau == 0.0


def test_partial_fill_fraction_censored_when_horizon_not_complete():
    c = candidate()
    fills = (
        p1.FillObservation(
            exchange_execution_ns=1_500_000_000,
            local_response_ns=1_750_000_000,
            qty=0.0004,
            price=100.0,
        ),
    )
    x = p1.fill_horizon_label(
        candidate=c,
        fills=fills,
        horizon_ns=2_000_000_000,
        source_exchange_observed_through_ns=2_000_000_000,
        placement_outcome=p1.POST_ONLY_ACCEPTED,
    )
    assert x.state == p1.FILLED_WITHIN_TAU
    assert x.any_fill_within_tau is True
    assert x.fill_fraction_at_tau is None
    assert x.fill_fraction_censored is True
    assert x.full_fill_status == p1.FULL_STATUS_CENSORED


def test_markout_bid_and_ask_sign():
    assert p1.fill_markout_bps(side="BID", fill_price=100.0, future_mid=100.1) > 0
    assert p1.fill_markout_bps(side="ASK", fill_price=100.1, future_mid=100.0) > 0
    assert p1.fill_markout_bps(side="BID", fill_price=100.0, future_mid=99.9) < 0


def test_candidate_markout_qty_weighted_and_no_double_count():
    c = candidate("BID")
    fills = (
        p1.FillObservation(1_200_000_000, 1_450_000_000, 0.0004, 100.0),
        p1.FillObservation(1_600_000_000, 1_850_000_000, 0.0006, 100.0),
    )
    mids = (
        p1.MidObservation(2_100_000_000, 1000, 1002),
        p1.MidObservation(2_500_000_000, 1001, 1003),
        p1.MidObservation(2_700_000_000, 1002, 1004),
    )
    x = p1.candidate_markout_label(
        candidate=c,
        fills=fills,
        midpoints=mids,
        horizon_ns=1_000_000_000,
        source_exchange_observed_through_ns=3_000_000_000,
    )
    assert x.status == p1.MARKOUT_OBSERVED
    assert x.included_fill_count == 2
    assert x.included_fill_qty == pytest.approx(0.001)
    assert x.value_bps is not None


def test_markout_censors_if_future_mid_not_observable():
    c = candidate("BID")
    fills = (
        p1.FillObservation(1_200_000_000, 1_450_000_000, 0.001, 100.0),
    )
    x = p1.candidate_markout_label(
        candidate=c,
        fills=fills,
        midpoints=(p1.MidObservation(1_500_000_000, 1000, 1001),),
        horizon_ns=1_000_000_000,
        source_exchange_observed_through_ns=2_000_000_000,
    )
    assert x.status == p1.MARKOUT_CENSORED
    assert x.value_bps is None


def test_hft_status_mapping_contract():
    assert p1.classify_gtx_placement_status(p1.HFT_NEW) == p1.POST_ONLY_ACCEPTED
    assert p1.classify_gtx_placement_status(p1.HFT_EXPIRED) == p1.POST_ONLY_REJECTED_AT_ARRIVAL
    assert p1.classify_gtx_placement_status(p1.HFT_NONE) == p1.CENSORED_BEFORE_PLACEMENT_OUTCOME
    with pytest.raises(p1.CandidateLabelerError):
        p1.classify_gtx_placement_status(p1.HFT_REJECTED)

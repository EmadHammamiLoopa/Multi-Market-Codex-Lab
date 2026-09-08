from __future__ import annotations

import math

import pytest

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1
from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b


NS = 1_000_000_000


def _levels(side: str, best_tick: int, best_qty: float):
    if side == "BID":
        ticks = (best_tick, best_tick - 1, best_tick - 2, best_tick - 3, best_tick - 4)
        qty = (best_qty, 8.0, 6.0, 4.0, 2.0)
    else:
        ticks = (best_tick, best_tick + 1, best_tick + 2, best_tick + 3, best_tick + 4)
        qty = (best_qty, 7.0, 6.0, 5.0, 4.0)
    return tuple(r8b.BookLevel(t, q) for t, q in zip(ticks, qty))


def _book(seconds: float, bid_qty: float, ask_qty: float, *, bid_tick: int = 1000, ask_tick: int = 1001):
    local = int(seconds * NS)
    exchange = max(0, local - 1)
    return r8b.BookObservation(
        local_ns=local,
        exchange_ns=exchange,
        bids=_levels("BID", bid_tick, bid_qty),
        asks=_levels("ASK", ask_tick, ask_qty),
    )


def _flow(seconds: float, kind: str, side: str, qty: float):
    local = int(seconds * NS)
    return r8b.FlowObservation(
        local_ns=local,
        exchange_ns=max(0, local - 1),
        kind=kind,
        side=side,
        qty=qty,
    )


def _base_books():
    return (
        _book(0.0, 10.0, 8.0),
        _book(29.0, 11.0, 9.0),
        _book(29.75, 12.0, 8.0),
        _book(30.0, 12.0, 7.0),
    )


def _base_flows():
    return (
        _flow(26.0, "TRADE", "SELL", 2.0),
        _flow(29.2, "TRADE", "BUY", 2.0),
        _flow(29.4, "TRADE", "SELL", 1.0),
        _flow(29.5, "ADD", "BID", 3.0),
        _flow(29.6, "ADD", "ASK", 1.0),
        _flow(29.7, "CANCEL", "BID", 1.0),
        _flow(29.8, "CANCEL", "ASK", 2.0),
    )


def _candidate(side="BID", distance=1):
    return p1.CandidateSpec(
        side=side,
        distance_ticks=distance,
        decision_local_ns=30 * NS,
        best_bid_tick=1000,
        best_ask_tick=1001,
    )


def test_r8b_contract_freezes_exact_25_feature_identity_and_keeps_execution_closed():
    r8b.validate_r8b_contract()
    assert r8b.PARENT_R8A_HEAD == "abcfd786e5c8345b9857310f98e5e7e856d75815"
    assert r8b.DATA_ROLE == "CONSUMED_DEVELOPMENT"
    assert r8b.FEATURE_LABEL_EXECUTOR_FROZEN is True
    assert len(r8b.FEATURE_NAMES) == 25
    assert r8b.FEATURE_NAMES == tuple(x for family in p0.LOCAL_FEATURE_FAMILIES.values() for x in family)
    assert tuple(r8b.FEATURE_DEFINITIONS) == r8b.FEATURE_NAMES
    assert r8b.feature_definition_sha256() == "cafe4cc9ff73e92f9d0a6b1c786a3a59769939afdd503fa3146bd262ea3dba92"
    assert r8b.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r8b.SIMULATOR_IMPORT_AUTHORIZED is False
    assert r8b.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r8b.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r8b.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r8b.MODEL_FIT_AUTHORIZED is False
    assert r8b.PNL_AUTHORIZED is False


def test_static_feature_math_signs_windows_and_candidate_execution_fields():
    result = r8b.compute_features(
        candidate=_candidate("BID", 1),
        books=_base_books(),
        flows=_base_flows(),
    )
    x = result.values

    assert tuple(x) == r8b.FEATURE_NAMES
    assert x["spread_ticks"] == 1.0
    assert x["microprice_minus_mid_bps"] > 0.0
    assert x["vamp_bbo_minus_mid_bps"] == x["microprice_minus_mid_bps"]
    assert math.isfinite(x["vamp_l5_minus_mid_bps"])
    assert math.isclose(x["l1_obi"], 5.0 / 19.0)
    assert math.isclose(x["l5_obi"], 3.0 / 61.0)

    # OFI: 0->29s is 0, 29->29.75 is +2, 29.75->30 is +1.
    assert math.isclose(x["bbo_ofi_1s"], 3.0)
    assert math.isclose(x["bbo_ofi_5s"], 3.0)
    assert math.isclose(x["ofi_acceleration_1s_vs_5s"], 2.4)

    assert math.isclose(x["trade_imbalance_1s"], 1.0 / 3.0)
    assert math.isclose(x["trade_imbalance_5s"], -1.0 / 5.0)
    assert math.isclose(x["add_imbalance_1s"], 0.5)
    assert math.isclose(x["cancel_imbalance_1s"], 1.0 / 3.0)

    assert x["same_side_depth_change_250ms"] == 0.0
    assert x["opposite_side_depth_change_250ms"] == -1.0
    assert x["spread_change_1s"] == 0.0
    assert x["realized_vol_1s"] == 0.0
    assert x["realized_vol_5s"] == 0.0
    assert x["realized_vol_30s"] == 0.0

    assert x["candidate_side_sign"] == 1.0
    assert x["candidate_distance_ticks"] == 1.0
    assert x["displayed_qty_at_candidate_price"] == 8.0
    assert x["estimated_queue_ahead_qty_from_decision_book"] == 8.0
    assert x["own_best_depth_qty"] == 12.0
    assert x["opposite_best_depth_qty"] == 7.0

    assert result.support == "VALID_LOCAL_BBO_AND_30S_CAUSAL_FEATURE_HISTORY_AT_DECISION_EPOCH"
    assert set(result.observable_local_ns) == set(r8b.FEATURE_NAMES)
    assert set(result.observable_local_ns.values()) == {30 * NS}


def test_candidate_side_conditioned_depth_features_reverse_for_ask():
    bid = r8b.compute_features(candidate=_candidate("BID", 1), books=_base_books(), flows=_base_flows()).values
    ask = r8b.compute_features(candidate=_candidate("ASK", 1), books=_base_books(), flows=_base_flows()).values

    assert bid["candidate_side_sign"] == 1.0
    assert ask["candidate_side_sign"] == -1.0
    assert bid["same_side_depth_change_250ms"] == 0.0
    assert bid["opposite_side_depth_change_250ms"] == -1.0
    assert ask["same_side_depth_change_250ms"] == -1.0
    assert ask["opposite_side_depth_change_250ms"] == 0.0
    assert ask["own_best_depth_qty"] == 7.0
    assert ask["opposite_best_depth_qty"] == 12.0


def test_future_book_and_flow_observations_cannot_change_decision_features():
    base = r8b.compute_features(candidate=_candidate(), books=_base_books(), flows=_base_flows())

    future_books = _base_books() + (
        _book(31.0, 99.0, 0.5, bid_tick=1004, ask_tick=1005),
    )
    future_flows = _base_flows() + (
        _flow(31.0, "TRADE", "BUY", 999.0),
    )

    future = r8b.compute_features(candidate=_candidate(), books=future_books, flows=future_flows)
    assert future.values == base.values
    assert future.observable_local_ns == base.observable_local_ns


def test_realized_vol_uses_anchor_and_coalesced_bbo_mid_path():
    books = (
        _book(0.0, 10.0, 8.0, bid_tick=1000, ask_tick=1001),
        _book(29.0, 10.0, 8.0, bid_tick=1001, ask_tick=1002),
        _book(30.0, 10.0, 8.0, bid_tick=1000, ask_tick=1001),
    )
    value = r8b.realized_vol_bps(books=books, decision_local_ns=30 * NS, window_ns=1 * NS)
    expected = 10_000.0 * abs(math.log((1000.5 * 0.1) / (1001.5 * 0.1)))
    assert math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-12)
    assert value > 0.0


def test_depth_delta_flow_mapping_freezes_add_cancel_sign_semantics():
    add = r8b.depth_delta_to_flow(local_ns=10, exchange_ns=9, side="BID", before_qty=2.0, after_qty=5.0)
    cancel = r8b.depth_delta_to_flow(local_ns=11, exchange_ns=10, side="ASK", before_qty=5.0, after_qty=2.0)
    same = r8b.depth_delta_to_flow(local_ns=12, exchange_ns=11, side="BID", before_qty=2.0, after_qty=2.0)

    assert add is not None and (add.kind, add.side, add.qty) == ("ADD", "BID", 3.0)
    assert cancel is not None and (cancel.kind, cancel.side, cancel.qty) == ("CANCEL", "ASK", 3.0)
    assert same is None


def test_standard_cont_bbo_ofi_transition_signs_buy_pressure_positive():
    a = _book(0.0, 10.0, 8.0)
    b = _book(1.0, 12.0, 7.0)
    assert r8b.bbo_ofi_transition(a, b) == 3.0

    # Bid price drops and ask price rises: both components are negative pressure.
    c = _book(2.0, 5.0, 6.0, bid_tick=999, ask_tick=1002)
    assert r8b.bbo_ofi_transition(b, c) < 0.0


def test_feature_support_requires_30s_anchor_and_current_l5_depth():
    with pytest.raises(r8b.FeatureLabelExecutorError, match="book_asof_missing"):
        r8b.compute_features(
            candidate=_candidate(),
            books=(
                _book(1.0, 10.0, 8.0),
                _book(30.0, 12.0, 7.0),
            ),
            flows=(),
        )

    short = r8b.BookObservation(
        local_ns=30 * NS,
        exchange_ns=30 * NS - 1,
        bids=(r8b.BookLevel(1000, 12.0),),
        asks=(r8b.BookLevel(1001, 7.0),),
    )
    with pytest.raises(r8b.FeatureLabelExecutorError, match="current_l5_support"):
        r8b.compute_features(
            candidate=_candidate(),
            books=(_book(0.0, 10.0, 8.0), short),
            flows=(),
        )


def test_label_bundle_is_exact_p1_binding_for_all_frozen_horizons():
    candidate = p1.CandidateSpec(
        side="BID",
        distance_ticks=0,
        decision_local_ns=30 * NS,
        best_bid_tick=1000,
        best_ask_tick=1001,
    )
    fills = (
        p1.FillObservation(
            exchange_execution_ns=30_500_000_000,
            local_response_ns=30_750_000_000,
            qty=0.001,
            price=100.0,
        ),
    )
    midpoints = tuple(
        p1.MidObservation(exchange_ns=t, best_bid_tick=bid, best_ask_tick=bid + 1)
        for t, bid in (
            (30_000_000_000, 1000),
            (30_750_000_000, 1000),
            (31_000_000_000, 1000),
            (31_500_000_000, 1001),
            (32_500_000_000, 1001),
            (35_500_000_000, 1002),
        )
    )

    bundle = r8b.build_label_bundle(
        candidate=candidate,
        fills=fills,
        midpoints=midpoints,
        source_exchange_observed_through_ns=36 * NS,
        placement_outcome=p1.POST_ONLY_ACCEPTED,
    )

    assert tuple(x.horizon_ns for x in bundle.fill_labels) == p0.FILL_HORIZONS_NS
    assert tuple(x.horizon_ns for x in bundle.markout_labels) == p0.MARKOUT_HORIZONS_NS
    assert bundle.fill_labels[0].state == p1.NOT_FILLED_WITHIN_TAU
    assert bundle.fill_labels[1].state == p1.FILLED_WITHIN_TAU
    assert all(x.status == p1.MARKOUT_OBSERVED for x in bundle.markout_labels)
    assert bundle.markout_labels[2].value_bps is not None


def test_end_of_source_fill_label_censoring_is_preserved_not_collapsed_to_no_fill():
    candidate = _candidate("BID", 0)
    bundle = r8b.build_label_bundle(
        candidate=candidate,
        fills=(),
        midpoints=(),
        source_exchange_observed_through_ns=30_100_000_000,
        placement_outcome=p1.POST_ONLY_ACCEPTED,
    )
    assert all(x.state == p1.CENSORED for x in bundle.fill_labels)
    assert all(x.any_fill_within_tau is None for x in bundle.fill_labels)
    assert all(x.status == p1.MARKOUT_NOT_APPLICABLE_NO_FILL for x in bundle.markout_labels)

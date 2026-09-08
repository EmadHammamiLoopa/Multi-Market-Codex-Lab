from __future__ import annotations

import math

import pytest

from multimarket import (
    dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0,
)
from multimarket import (
    dev045_d6r26a_p1_synthetic_candidate_labeler as p1,
)
from multimarket import (
    dev045_d6r26a_p2_r12_one_day_lane_driver_preexecution as r12,
)
from multimarket import (
    dev045_d6r26a_p2_r14_synthetic_candidate_grid_real_engine_preexecution as r14,
)


def _primary_fill(result):
    return next(
        x
        for x in result.labels.fill_labels
        if int(x.horizon_ns)
        == p0.PRIMARY_FILL_HORIZON_NS
    )


def test_r14_contract_is_synthetic_and_sealed():
    r14.validate_r14_contract()

    assert r14.SYNTHETIC_REAL_ENGINE_ONLY is True
    assert (
        r14.CANDIDATE_GRID_REAL_ENGINE_PREEXECUTION_FROZEN
        is True
    )

    assert r14.CANDIDATE_GRID == (
        ("BID", 0),
        ("BID", 1),
        ("BID", 2),
        ("BID", 4),
        ("ASK", 0),
        ("ASK", 1),
        ("ASK", 2),
        ("ASK", 4),
    )

    assert r14.NO_FIXED_EVENT_TARGET is True
    assert r14.NO_FIXED_WAKEUP_TARGET is True
    assert r14.TOTAL_RSS_NOT_BOUNDEDNESS_GATE is True

    assert r14.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r14.CANONICAL_HISTORICAL_RUN_AUTHORIZED is False
    assert r14.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r14.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r14.MODEL_FIT_AUTHORIZED is False
    assert r14.PNL_AUTHORIZED is False


@pytest.mark.parametrize(
    "side,distance",
    r14.CANDIDATE_GRID,
)
def test_real_engine_no_fill_grid_exact_cancel_semantics(
    side,
    distance,
):
    result = r14.run_grid_case(
        side=side,
        distance_ticks=distance,
        with_fill=False,
    )

    assert result.candidate.side == side
    assert result.candidate.distance_ticks == distance
    assert result.placement_outcome == p1.POST_ONLY_ACCEPTED

    assert result.fills == ()
    assert result.canceled_at_boundary is True
    assert result.final_status == p1.HFT_CANCELED

    assert result.final_local_ns == (
        r14.CANDIDATE_TERMINAL_BOUNDARY_NS
    )

    assert result.ack_latency_triplet == (
        r14.DECISION_LOCAL_NS,
        r14.DECISION_LOCAL_NS + p0.ENTRY_LATENCY_NS,
        r14.DECISION_LOCAL_NS
        + p0.ENTRY_LATENCY_NS
        + p0.RESPONSE_LATENCY_NS,
    )

    # Regression guard for the exact R11 correction:
    # cancel latency field zero remains NEW request local timestamp.
    assert result.cancel_latency_triplet == (
        r14.DECISION_LOCAL_NS,
        r14.CANCEL_REQUEST_LOCAL_NS
        + p0.ENTRY_LATENCY_NS,
        r14.CANDIDATE_TERMINAL_BOUNDARY_NS,
    )

    assert all(
        x.state == p1.NOT_FILLED_WITHIN_TAU
        for x in result.labels.fill_labels
    )

    assert all(
        x.status
        == p1.MARKOUT_NOT_APPLICABLE_NO_FILL
        for x in result.labels.markout_labels
    )


@pytest.mark.parametrize(
    "side",
    ("BID", "ASK"),
)
def test_real_engine_bbo_fill_probe_is_side_symmetric(side):
    result = r14.run_grid_case(
        side=side,
        distance_ticks=0,
        with_fill=True,
    )

    assert result.candidate.side == side
    assert result.candidate.distance_ticks == 0
    assert result.placement_outcome == p1.POST_ONLY_ACCEPTED

    assert result.canceled_at_boundary is False
    assert result.cancel_latency_triplet is None
    assert result.final_status == p1.HFT_FILLED

    assert len(result.fills) == 1

    fill = result.fills[0]

    assert fill.exchange_execution_ns == 31_800_000_000
    assert fill.local_response_ns == 32_050_000_000

    assert math.isclose(
        float(fill.qty),
        p0.CANDIDATE_ORDER_QTY,
        rel_tol=0.0,
        abs_tol=1e-15,
    )

    expected_price = (
        100.0
        if side == "BID"
        else 100.1
    )

    assert math.isclose(
        float(fill.price),
        expected_price,
        rel_tol=0.0,
        abs_tol=1e-12,
    )

    primary = _primary_fill(result)

    assert primary.state == p1.FILLED_WITHIN_TAU
    assert primary.any_fill_within_tau is True

    # 800ms execution delay from 31.0s decision:
    by_horizon = {
        int(x.horizon_ns): x
        for x in result.labels.fill_labels
    }

    assert (
        by_horizon[250_000_000].state
        == p1.NOT_FILLED_WITHIN_TAU
    )
    assert (
        by_horizon[500_000_000].state
        == p1.NOT_FILLED_WITHIN_TAU
    )
    assert (
        by_horizon[1_000_000_000].state
        == p1.FILLED_WITHIN_TAU
    )
    assert (
        by_horizon[2_000_000_000].state
        == p1.FILLED_WITHIN_TAU
    )
    assert (
        by_horizon[5_000_000_000].state
        == p1.FILLED_WITHIN_TAU
    )


def test_r14_binds_the_existing_40_lane_day_grid_without_opening_data():
    plan = r12.build_one_day_plan("2026-02-01")

    assert len(plan.lanes) == 40

    observed_grid = {
        (
            lane.side,
            lane.distance_ticks,
            lane.phase,
        )
        for lane in plan.lanes
    }

    expected_grid = {
        (side, distance, phase)
        for side in ("BID", "ASK")
        for distance in (0, 1, 2, 4)
        for phase in (0, 1, 2, 3, 4)
    }

    assert observed_grid == expected_grid

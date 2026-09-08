from __future__ import annotations

import math

from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1
from multimarket import dev045_d6r26a_p2_r11_synthetic_real_engine_lane_lifecycle as r11


def test_r11_contract_is_synthetic_only():
    r11.validate_r11_contract()
    assert r11.SYNTHETIC_REAL_ENGINE_ONLY is True
    assert r11.REAL_ENGINE_LANE_LIFECYCLE_FROZEN is True
    assert r11.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r11.CANONICAL_HISTORICAL_RUN_AUTHORIZED is False
    assert r11.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r11.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r11.MODEL_FIT_AUTHORIZED is False
    assert r11.PNL_AUTHORIZED is False


def test_real_engine_fill_lifecycle_produces_frozen_labels():
    out = r11.run_synthetic_lane(with_fill=True, distance_ticks=0)
    assert out.placement_outcome == p1.POST_ONLY_ACCEPTED
    assert out.canceled_at_boundary is False
    assert out.final_status == p1.HFT_FILLED
    assert len(out.fills) == 1
    fill = out.fills[0]
    assert fill.exchange_execution_ns == 31_800_000_000
    assert fill.local_response_ns == 32_050_000_000
    assert math.isclose(fill.qty, 0.001, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(fill.price, 100.0, rel_tol=0.0, abs_tol=1e-12)
    assert out.order_latency_triplet == (
        31_000_000_000,
        31_250_000_000,
        31_500_000_000,
    )
    labels = {x.horizon_ns: x for x in out.labels.fill_labels}
    assert labels[250_000_000].state == p1.NOT_FILLED_WITHIN_TAU
    assert labels[500_000_000].state == p1.NOT_FILLED_WITHIN_TAU
    assert labels[1_000_000_000].state == p1.FILLED_WITHIN_TAU
    assert labels[2_000_000_000].state == p1.FILLED_WITHIN_TAU
    assert labels[5_000_000_000].state == p1.FILLED_WITHIN_TAU
    markouts = {x.horizon_ns: x for x in out.labels.markout_labels}
    assert all(x.status == p1.MARKOUT_OBSERVED for x in markouts.values())
    assert all(x.included_fill_count == 1 for x in markouts.values())
    assert out.source_exchange_observed_through_ns >= 36_800_000_000
    assert len(out.feature_vector.values) == 25


def test_real_engine_no_fill_cancels_terminally_at_exact_t_plus_5_boundary():
    out = r11.run_synthetic_lane(with_fill=False, distance_ticks=4)
    assert out.placement_outcome == p1.POST_ONLY_ACCEPTED
    assert out.canceled_at_boundary is True
    assert out.final_status == p1.HFT_CANCELED
    assert out.final_local_ns == r11.CANDIDATE_TERMINAL_BOUNDARY_NS
    assert out.fills == ()
    assert all(x.state == p1.NOT_FILLED_WITHIN_TAU for x in out.labels.fill_labels)
    assert all(
        x.status == p1.MARKOUT_NOT_APPLICABLE_NO_FILL
        for x in out.labels.markout_labels
    )
    assert len(out.feature_vector.values) == 25

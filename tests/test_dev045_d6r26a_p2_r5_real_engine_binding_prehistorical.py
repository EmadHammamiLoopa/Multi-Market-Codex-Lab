from __future__ import annotations

import importlib.util

import pytest

from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1
from multimarket import dev045_d6r26a_p2_r5_real_engine_binding_prehistorical as r5


def test_r5_contract_keeps_historical_surface_closed():
    r5.validate_r5_contract()
    assert r5.REAL_ENGINE_PROBE_AUTHORIZED is True
    assert r5.SYNTHETIC_FIXTURE_ONLY is True
    assert r5.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r5.HISTORICAL_FILE_IO_AUTHORIZED is False
    assert r5.CANONICAL_RUNNER_BINDING_AUTHORIZED is False
    assert r5.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r5.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r5.MODEL_FIT_AUTHORIZED is False
    assert r5.PNL_AUTHORIZED is False
    assert r5.LIVE_TRADING_AUTHORIZED is False


@pytest.mark.skipif(importlib.util.find_spec("hftbacktest") is None, reason="real engine dedicated CI only")
def test_exact_real_engine_identity_and_gtx_statuses():
    identity = r5.verify_engine_identity()
    assert identity.version == "2.4.4"
    assert identity.gtx == 1
    assert (identity.none, identity.new, identity.expired, identity.filled, identity.canceled, identity.partially_filled, identity.rejected) == (0, 1, 2, 3, 4, 5, 6)


@pytest.mark.skipif(importlib.util.find_spec("hftbacktest") is None, reason="real engine dedicated CI only")
def test_gtx_passive_accepts_and_fills_on_real_engine_synthetic_fixture():
    result = r5.run_gtx_accept_fill_probe()
    assert result.accepted_status == 1
    assert result.accepted_placement == p1.POST_ONLY_ACCEPTED
    assert result.post_trade10_status == 1
    assert result.terminal_status == 3
    assert result.terminal_placement == p1.POST_ONLY_ACCEPTED
    assert result.exec_qty == pytest.approx(0.001)
    assert result.position == pytest.approx(0.001)
    assert result.fill_response_rc == 3


@pytest.mark.skipif(importlib.util.find_spec("hftbacktest") is None, reason="real engine dedicated CI only")
def test_gtx_crossing_is_expired_post_only_refusal_on_real_engine():
    result = r5.run_gtx_cross_probe()
    assert result.terminal_status == 2
    assert result.placement == p1.POST_ONLY_REJECTED_AT_ARRIVAL
    assert result.position == pytest.approx(0.0)

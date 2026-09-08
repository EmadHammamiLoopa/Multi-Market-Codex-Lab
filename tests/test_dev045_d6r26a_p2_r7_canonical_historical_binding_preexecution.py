from __future__ import annotations

from multimarket import dev045_d6r26a_p2_r7_canonical_historical_binding_preexecution as r7


def test_r7_contract_binds_frozen_r6_pass_and_keeps_execution_closed():
    r7.validate_r7_contract()
    assert r7.PARENT_R6_FREEZE_HEAD == "36bd3ed16094a29fe647487543a028dfa0498e3b"
    assert r7.R6_FROZEN_RESULT_BYTES == 2201
    assert r7.R6_FROZEN_RESULT_SHA256 == "d4f0cc248f8c68c6a9f6a364716a7a64a2f1658bbed11cf32140a3f64327bac9"
    assert r7.SOURCE_REGISTRY_SHA256 == "97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4"
    assert r7.CANONICAL_BINDING_READY is True
    assert r7.EXECUTION_AUTHORIZATION_CREATED is False
    assert r7.HISTORICAL_FILE_IO_AUTHORIZED is False
    assert r7.SIMULATOR_IMPORT_AUTHORIZED is False
    assert r7.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r7.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r7.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r7.MODEL_FIT_AUTHORIZED is False
    assert r7.PNL_AUTHORIZED is False


def test_frozen_r6_evidence_is_exact():
    payload = r7.frozen_r6_result_bytes()
    assert len(payload) == 2201
    result = r7.frozen_r6_result()
    assert result["status"] == "SOURCE_IDENTITY_PREFLIGHT_PASS"
    assert result["verified_source_count"] == 7
    assert result["p2_attempt_consumed"] is False
    assert result["candidate_simulation_started"] is False


def test_r7_cardinality_and_attempt_boundary_are_frozen():
    assert (r7.EXPECTED_DAYS, r7.EXPECTED_LANES_PER_DAY) == (7, 40)
    assert (r7.EXPECTED_TOTAL_LANES, r7.EXPECTED_TOTAL_PARTITIONS) == (280, 280)
    assert r7.ATTEMPT_CONSUMPTION_EVENT == "FIRST_CANONICAL_CANDIDATE_SIMULATION_LANE_START"

import pytest
from multimarket import dev045_d6r26a_p2_r3_execution_authorization_contract as r3


def test_contract_is_pure_and_closed():
    r3.validate_execution_authorization_contract()
    assert r3.THIS_COMMIT_EXECUTES_HISTORICAL_DATA is False
    assert r3.THIS_COMMIT_IMPORTS_SIMULATOR is False
    assert r3.THIS_COMMIT_WRITES_LABELS is False
    assert r3.RERUN_AFTER_ATTEMPT_MARKER_AUTHORIZED is False
    assert r3.RESUME_AFTER_ATTEMPT_MARKER_AUTHORIZED is False
    assert r3.AUTOMATIC_RETRY_AUTHORIZED is False
    assert r3.PNL_AUTHORIZED is False
    assert r3.LIVE_TRADING_AUTHORIZED is False


def test_authorization_is_exact_token_only():
    with pytest.raises(r3.ExecutionAuthorizationError):
        r3.build_authorized_execution_contract(None)
    with pytest.raises(r3.ExecutionAuthorizationError):
        r3.build_authorized_execution_contract('YES')
    c = r3.build_authorized_execution_contract(r3.AUTH_TOKEN)
    assert c.source_registry_sha256 == r3.FROZEN_SOURCE_REGISTRY_SHA256
    assert c.lane_count == 280
    assert len(c.source_days) == 7


def test_attempt_consumption_semantics_are_fail_closed():
    assert r3.AUTHORIZATION_FAILURE_CONSUMES_ATTEMPT is False
    assert r3.SOURCE_IDENTITY_PRECHECK_FAILURE_CONSUMES_ATTEMPT is False
    assert r3.FIRST_SIMULATOR_LANE_START_CONSUMES_ATTEMPT is True
    assert r3.ATTEMPT_CONSUMPTION_EVENT == 'FIRST_CANONICAL_CANDIDATE_SIMULATOR_LANE_START_AFTER_EXACT_SOURCE_IDENTITY_VERIFICATION'
    assert r3.FAILURE_AFTER_CONSUMPTION_IS_TERMINAL is True
    assert r3.CANONICAL_COMPLETION_REQUIRES_ALL_280_PARTITIONS is True

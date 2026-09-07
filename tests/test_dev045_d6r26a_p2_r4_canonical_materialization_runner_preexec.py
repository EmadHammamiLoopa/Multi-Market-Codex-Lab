from __future__ import annotations

from multimarket import dev045_d6r26a_p2_r2_frozen_source_registry as r2
from multimarket import dev045_d6r26a_p2_r3_execution_authorization_contract as r3
from multimarket import dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4


def _verified(expected):
    return r4.VerifiedSource(
        day=expected.day,
        path=expected.path,
        rows=expected.rows,
        bytes=expected.bytes,
        sha256=expected.sha256,
    )


def _hooks(*, fail_lane=None, attempt_exists=False, bad_source_day=None):
    events = []
    final = []
    failure = []

    def verify_source(expected):
        events.append(("verify", expected.day))
        out = _verified(expected)
        if expected.day == bad_source_day:
            out = r4.VerifiedSource(out.day, out.path, out.rows, out.bytes, "0" * 64)
        return out

    def write_attempt(payload):
        events.append(("attempt", payload["expected_lanes"]))

    def open_day(source):
        events.append(("open", source.day))
        return source.day

    def run_lane(handle, lane):
        events.append(("lane", lane.lane_id))
        if fail_lane == lane.lane_id:
            raise RuntimeError("synthetic_lane_failure")
        payload = lane.lane_id.encode()
        import hashlib
        return r4.LaneArtifact(
            lane_id=lane.lane_id,
            relpath=lane.partition_relpath,
            bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            row_count=1,
        )

    def close_day(handle):
        events.append(("close", handle))

    def verify_partition(artifact):
        events.append(("partition", artifact.lane_id))

    def write_failure(payload):
        failure.append(payload)

    def write_final(payload):
        final.append(payload)

    return (
        r4.RunnerHooks(
            attempt_marker_exists=lambda: attempt_exists,
            verify_source=verify_source,
            write_attempt_marker=write_attempt,
            open_day_source=open_day,
            run_lane=run_lane,
            close_day_source=close_day,
            verify_partition=verify_partition,
            write_failure_artifact=write_failure,
            write_final_manifest=write_final,
        ),
        events,
        final,
        failure,
    )


def test_runner_contract_is_closed():
    r4.validate_runner_contract()
    assert r4.PREEXECUTION_ONLY is True
    assert r4.REAL_EXECUTION_BINDING_AUTHORIZED is False
    assert r4.HISTORICAL_FILE_IO_AUTHORIZED is False
    assert r4.SIMULATOR_IMPORT_AUTHORIZED is False
    assert r4.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r4.MODEL_FIT_AUTHORIZED is False
    assert r4.PNL_AUTHORIZED is False
    assert r4.LIVE_TRADING_AUTHORIZED is False


def test_precheck_failure_does_not_consume_attempt():
    hooks, events, final, failure = _hooks(bad_source_day="2026-06-01")
    try:
        r4.run_canonical_materialization(authorization_value=r3.AUTH_TOKEN, hooks=hooks)
    except r4.CanonicalRunnerError as exc:
        assert str(exc) == "source_identity_mismatch:2026-06-01"
    else:
        raise AssertionError("expected fail closed")
    assert not any(x[0] == "attempt" for x in events)
    assert final == []
    assert failure == []


def test_existing_attempt_marker_blocks_rerun_before_precheck():
    hooks, events, final, failure = _hooks(attempt_exists=True)
    try:
        r4.run_canonical_materialization(authorization_value=r3.AUTH_TOKEN, hooks=hooks)
    except r4.CanonicalRunnerError as exc:
        assert str(exc) == "attempt_already_consumed"
    else:
        raise AssertionError("expected rerun guard")
    assert events == []
    assert final == []
    assert failure == []


def test_attempt_marker_precedes_first_lane_and_success_requires_280():
    hooks, events, final, failure = _hooks()
    result = r4.run_canonical_materialization(authorization_value=r3.AUTH_TOKEN, hooks=hooks)
    assert result.status == "CANONICAL_280_PARTITIONS_COMPLETE"
    assert result.verified_source_count == 7
    assert result.completed_day_count == 7
    assert result.completed_lane_count == 280
    assert result.partition_count == 280
    assert result.attempt_consumed is True
    assert failure == []
    assert len(final) == 1
    assert final[0]["partition_count"] == 280
    first_attempt = next(i for i, x in enumerate(events) if x[0] == "attempt")
    first_lane = next(i for i, x in enumerate(events) if x[0] == "lane")
    last_verify = max(i for i, x in enumerate(events) if x[0] == "verify")
    assert last_verify < first_attempt < first_lane
    assert sum(1 for x in events if x[0] == "open") == 7
    assert sum(1 for x in events if x[0] == "close") == 7
    assert sum(1 for x in events if x[0] == "lane") == 280
    assert sum(1 for x in events if x[0] == "partition") == 280


def test_lane_failure_after_attempt_is_terminal_and_no_final_manifest():
    first_lane = r4.r1.build_materialization_plan()[0].lane_id
    hooks, events, final, failure = _hooks(fail_lane=first_lane)
    result = r4.run_canonical_materialization(authorization_value=r3.AUTH_TOKEN, hooks=hooks)
    assert result.status == "TERMINAL_FAILURE_AFTER_ATTEMPT_CONSUMPTION"
    assert result.attempt_consumed is True
    assert result.completed_lane_count == 0
    assert final == []
    assert len(failure) == 1
    assert failure[0]["rerun_authorized"] is False
    assert failure[0]["resume_authorized"] is False
    first_attempt = next(i for i, x in enumerate(events) if x[0] == "attempt")
    first_lane_event = next(i for i, x in enumerate(events) if x[0] == "lane")
    assert first_attempt < first_lane_event


def test_registry_bound_to_corrected_frozen_source_identity():
    by_day = {x.day: x for x in r2.FROZEN_SOURCE_REGISTRY}
    assert by_day["2026-06-01"].sha256 == "ac97ad27c9d58b3b3e249547b8ae7c74cf2ebfde07965103bd9c8c05d0df1160"

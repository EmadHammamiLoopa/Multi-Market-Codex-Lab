from __future__ import annotations

import pytest

from multimarket import (
    dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4,
)
from multimarket import (
    dev045_d6r26a_p2_r12_one_day_lane_driver_preexecution as r12,
)


def test_r12_contract_remains_preexecution_only():
    r12.validate_r12_contract()

    assert r12.PREEXECUTION_ONLY is True
    assert r12.ONE_DAY_AT_A_TIME is True
    assert r12.SOURCE_OPEN_ONCE_PER_DAY is True
    assert r12.SOURCE_CLOSE_ONCE_PER_DAY is True
    assert r12.STOP_ON_FIRST_LANE_FAILURE is True
    assert r12.LANES_PER_DAY == 40

    assert r12.REAL_HISTORICAL_HOOKS_BOUND_FOR_EXECUTION is False
    assert r12.FINAL_ONE_SHOT_BINDING_AUTHORIZED is False
    assert r12.EXECUTION_AUTHORIZATION_CREATED is False
    assert r12.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r12.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert r12.ATTEMPT_MARKER_WRITE_AUTHORIZED is False
    assert r12.CANONICAL_LABEL_WRITE_AUTHORIZED is False
    assert r12.MODEL_FIT_AUTHORIZED is False
    assert r12.PNL_AUTHORIZED is False


def test_r12_builds_exact_frozen_40_lane_day_plan():
    plan = r12.build_one_day_plan("2026-02-01")

    assert plan.day == "2026-02-01"
    assert plan.source.day == "2026-02-01"
    assert len(plan.lanes) == 40
    assert len({lane.lane_id for lane in plan.lanes}) == 40

    assert {
        (lane.side, lane.distance_ticks, lane.phase)
        for lane in plan.lanes
    } == {
        (side, distance, phase)
        for side in ("BID", "ASK")
        for distance in (0, 1, 2, 4)
        for phase in (0, 1, 2, 3, 4)
    }


def test_r12_synthetic_driver_opens_and_closes_source_exactly_once():
    plan = r12.build_one_day_plan("2026-02-01")

    opened = []
    closed = []
    executed = []
    verified = []

    def open_source(source):
        opened.append(source.day)
        return {"day": source.day}

    def run_lane(handle, lane):
        assert handle["day"] == lane.day
        executed.append(lane.lane_id)
        return r4.LaneArtifact(
            lane_id=lane.lane_id,
            relpath=lane.partition_relpath,
            bytes=8,
            sha256="0" * 64,
            row_count=1,
        )

    def verify_partition(artifact):
        verified.append(artifact.lane_id)

    def close_source(handle):
        closed.append(handle["day"])

    summary = r12.run_one_day_preexecution(
        plan=plan,
        hooks=r12.OneDayHooks(
            open_source=open_source,
            run_lane=run_lane,
            verify_partition=verify_partition,
            close_source=close_source,
        ),
    )

    assert opened == ["2026-02-01"]
    assert closed == ["2026-02-01"]
    assert executed == [lane.lane_id for lane in plan.lanes]
    assert verified == executed

    assert summary.lane_count == 40
    assert summary.partition_count == 40
    assert summary.source_open_count == 1
    assert summary.source_close_count == 1


def test_r12_failure_closes_source_and_stops_immediately():
    plan = r12.build_one_day_plan("2026-02-01")

    closed = []
    executed = []

    def open_source(source):
        return {"day": source.day}

    def run_lane(handle, lane):
        executed.append(lane.lane_id)
        if len(executed) == 3:
            raise RuntimeError("synthetic_lane_failure")
        return r4.LaneArtifact(
            lane_id=lane.lane_id,
            relpath=lane.partition_relpath,
            bytes=8,
            sha256="1" * 64,
            row_count=1,
        )

    def verify_partition(artifact):
        pass

    def close_source(handle):
        closed.append(handle["day"])

    with pytest.raises(RuntimeError, match="synthetic_lane_failure"):
        r12.run_one_day_preexecution(
            plan=plan,
            hooks=r12.OneDayHooks(
                open_source=open_source,
                run_lane=run_lane,
                verify_partition=verify_partition,
                close_source=close_source,
            ),
        )

    assert len(executed) == 3
    assert closed == ["2026-02-01"]

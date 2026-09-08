from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from multimarket import (
    dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0,
)
from multimarket import (
    dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1,
)
from multimarket import (
    dev045_d6r26a_p2_r2_frozen_source_registry as r2,
)
from multimarket import (
    dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4,
)
from multimarket import (
    dev045_d6r26a_p2_r8a_real_hooks_writer_preexecution as r8a,
)
from multimarket import (
    dev045_d6r26a_p2_r11_synthetic_real_engine_lane_lifecycle as r11,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R12"
DESIGN_VERSION = "one-day-lane-driver-preexecution-v1"
PARENT_R11_HEAD = "21eeec972aec1f1b75474595db0ca843931aa9e7"
DATA_ROLE = "CONSUMED_DEVELOPMENT"

ONE_DAY_DRIVER_PREEXECUTION_FROZEN = True
R4_CAMPAIGN_ORCHESTRATION_BOUND = True
R8A_REAL_SOURCE_AND_WRITER_PRIMITIVES_BOUND = True
R11_REAL_ENGINE_LIFECYCLE_BOUND = True

ONE_DAY_AT_A_TIME = True
SOURCE_OPEN_ONCE_PER_DAY = True
SOURCE_CLOSE_ONCE_PER_DAY = True
STOP_ON_FIRST_LANE_FAILURE = True
LANES_PER_DAY = 40
REFERENCE_DRIVER_PARALLELISM = 1
MAX_PARALLEL_LANES = 8

# R12 is construction/preexecution only.
PREEXECUTION_ONLY = True
REAL_HISTORICAL_HOOKS_BOUND_FOR_EXECUTION = False
FINAL_ONE_SHOT_BINDING_AUTHORIZED = False
EXECUTION_AUTHORIZATION_CREATED = False
HISTORICAL_FILE_IO_AUTHORIZED = False
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
SIMULATOR_IMPORT_AUTHORIZED = False
CANDIDATE_SIMULATION_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False


class OneDayLaneDriverError(RuntimeError):
    pass


@dataclass(frozen=True)
class OneDayPlan:
    day: str
    source: r4.VerifiedSource
    lanes: tuple[r1.LaneSpec, ...]


@dataclass
class OneDayHooks:
    open_source: Callable[[r4.VerifiedSource], object]
    run_lane: Callable[[object, r1.LaneSpec], r4.LaneArtifact]
    verify_partition: Callable[[r4.LaneArtifact], None]
    close_source: Callable[[object], None]


@dataclass(frozen=True)
class OneDaySummary:
    day: str
    lane_count: int
    partition_count: int
    source_open_count: int
    source_close_count: int


def _verified_source_for_day(day: str) -> r4.VerifiedSource:
    matches = tuple(
        source
        for source in r2.FROZEN_SOURCE_REGISTRY
        if source.day == day
    )
    if len(matches) != 1:
        raise OneDayLaneDriverError(f"source_day:{day}")

    source = matches[0]
    return r4.VerifiedSource(
        day=source.day,
        path=source.path,
        rows=int(source.rows),
        bytes=int(source.bytes),
        sha256=source.sha256,
    )


def build_one_day_plan(day: str) -> OneDayPlan:
    r2.validate_frozen_source_registry()
    r4.validate_runner_contract()
    r11.validate_r11_contract()

    source = _verified_source_for_day(day)

    lanes = tuple(
        lane
        for lane in r1.build_materialization_plan()
        if lane.day == day
    )

    if len(lanes) != LANES_PER_DAY:
        raise OneDayLaneDriverError(
            f"lane_count:{day}:{len(lanes)}"
        )

    if len({lane.lane_id for lane in lanes}) != LANES_PER_DAY:
        raise OneDayLaneDriverError("duplicate_lane_id")

    observed_grid = {
        (
            lane.side,
            int(lane.distance_ticks),
            int(lane.phase),
        )
        for lane in lanes
    }
    expected_grid = {
        (side, int(distance), int(phase))
        for side in p0.CANDIDATE_SIDES
        for distance in p0.CANDIDATE_DISTANCE_TICKS
        for phase in p0.LANE_PHASE_OFFSETS_S
    }

    if observed_grid != expected_grid:
        raise OneDayLaneDriverError("lane_grid")

    return OneDayPlan(
        day=day,
        source=source,
        lanes=lanes,
    )


def _validate_lane_artifact(
    lane: r1.LaneSpec,
    artifact: r4.LaneArtifact,
) -> None:
    if artifact.lane_id != lane.lane_id:
        raise OneDayLaneDriverError(
            f"lane_artifact_identity:{lane.lane_id}"
        )
    if artifact.relpath != lane.partition_relpath:
        raise OneDayLaneDriverError(
            f"partition_relpath:{lane.lane_id}"
        )
    if int(artifact.bytes) < 0:
        raise OneDayLaneDriverError(
            f"partition_bytes:{lane.lane_id}"
        )
    if int(artifact.row_count) < 0:
        raise OneDayLaneDriverError(
            f"partition_rows:{lane.lane_id}"
        )
    if len(str(artifact.sha256)) != 64:
        raise OneDayLaneDriverError(
            f"partition_sha256:{lane.lane_id}"
        )


def run_one_day_preexecution(
    *,
    plan: OneDayPlan,
    hooks: OneDayHooks,
) -> OneDaySummary:
    """
    Generic one-day orchestration proof.

    R12 does not bind these callbacks to real Jan-Jul I/O. CI supplies only
    synthetic/in-memory hooks. The final one-shot binding may bind the already
    frozen real implementations after separate authorization.
    """
    canonical = build_one_day_plan(plan.day)

    if plan != canonical:
        raise OneDayLaneDriverError("plan_identity")

    source_open_count = 0
    source_close_count = 0
    artifacts: list[r4.LaneArtifact] = []

    handle = hooks.open_source(plan.source)
    source_open_count += 1

    try:
        for lane in plan.lanes:
            artifact = hooks.run_lane(handle, lane)
            _validate_lane_artifact(lane, artifact)
            hooks.verify_partition(artifact)
            artifacts.append(artifact)
    finally:
        hooks.close_source(handle)
        source_close_count += 1

    if source_open_count != 1:
        raise OneDayLaneDriverError("source_open_count")

    if source_close_count != 1:
        raise OneDayLaneDriverError("source_close_count")

    if len(artifacts) != LANES_PER_DAY:
        raise OneDayLaneDriverError("completed_lane_count")

    if len({x.lane_id for x in artifacts}) != LANES_PER_DAY:
        raise OneDayLaneDriverError("duplicate_partition")

    return OneDaySummary(
        day=plan.day,
        lane_count=len(plan.lanes),
        partition_count=len(artifacts),
        source_open_count=source_open_count,
        source_close_count=source_close_count,
    )


def validate_r12_contract() -> None:
    r2.validate_frozen_source_registry()
    r4.validate_runner_contract()
    r11.validate_r11_contract()

    if PARENT_R11_HEAD != (
        "21eeec972aec1f1b75474595db0ca843931aa9e7"
    ):
        raise OneDayLaneDriverError("parent")

    if DATA_ROLE != "CONSUMED_DEVELOPMENT":
        raise OneDayLaneDriverError("data_role")

    if LANES_PER_DAY != 40:
        raise OneDayLaneDriverError("lanes_per_day")

    if MAX_PARALLEL_LANES != r1.MAX_PARALLEL_LANES:
        raise OneDayLaneDriverError("parallelism")

    if REFERENCE_DRIVER_PARALLELISM != 1:
        raise OneDayLaneDriverError("reference_parallelism")

    required = (
        ONE_DAY_DRIVER_PREEXECUTION_FROZEN,
        R4_CAMPAIGN_ORCHESTRATION_BOUND,
        R8A_REAL_SOURCE_AND_WRITER_PRIMITIVES_BOUND,
        R11_REAL_ENGINE_LIFECYCLE_BOUND,
        ONE_DAY_AT_A_TIME,
        SOURCE_OPEN_ONCE_PER_DAY,
        SOURCE_CLOSE_ONCE_PER_DAY,
        STOP_ON_FIRST_LANE_FAILURE,
        PREEXECUTION_ONLY,
        r8a.REAL_SOURCE_VERIFIER_IMPLEMENTED,
        r8a.READ_ONLY_MMAP_OPEN_IMPLEMENTED,
        r8a.REAL_ENGINE_FACTORY_IMPLEMENTED,
        r8a.ATOMIC_WRITER_IMPLEMENTED,
        r8a.SEALED_RUNNER_HOOKS_IMPLEMENTED,
        r11.SYNTHETIC_REAL_ENGINE_ONLY,
    )
    if not all(required):
        raise OneDayLaneDriverError("required_binding")

    forbidden = (
        REAL_HISTORICAL_HOOKS_BOUND_FOR_EXECUTION,
        FINAL_ONE_SHOT_BINDING_AUTHORIZED,
        EXECUTION_AUTHORIZATION_CREATED,
        HISTORICAL_FILE_IO_AUTHORIZED,
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        SIMULATOR_IMPORT_AUTHORIZED,
        CANDIDATE_SIMULATION_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        NETWORK_ACQUISITION_AUTHORIZED,
    )
    if any(forbidden):
        raise OneDayLaneDriverError("execution_surface_open")


__all__ = [
    "OneDayPlan",
    "OneDayHooks",
    "OneDaySummary",
    "build_one_day_plan",
    "run_one_day_preexecution",
    "validate_r12_contract",
]

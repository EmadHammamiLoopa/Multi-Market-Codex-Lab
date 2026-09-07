from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from multimarket import dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1
from multimarket import dev045_d6r26a_p2_r2_frozen_source_registry as r2
from multimarket import dev045_d6r26a_p2_r3_execution_authorization_contract as r3


EXPERIMENT_ID = "DEV045-D6R26A-P2-R4"
DESIGN_VERSION = "canonical-materialization-runner-preexecution-v1"
PARENT_P2_R3_HEAD = "49f3d4c522d5010ff1c957b70e11a2341f11dded"
DATA_ROLE = "CONSUMED_DEVELOPMENT"

PREEXECUTION_ONLY = True
REAL_EXECUTION_BINDING_AUTHORIZED = False
HISTORICAL_FILE_IO_AUTHORIZED = False
SIMULATOR_IMPORT_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False

PRECHECK_ALL_SEVEN_SOURCES_BEFORE_ATTEMPT = True
ATTEMPT_MARKER_BEFORE_FIRST_LANE = True
STOP_ON_FIRST_FAILURE = True
NO_RESUME_AFTER_ATTEMPT = True
NO_RERUN_AFTER_ATTEMPT = True
ONE_DAY_AT_A_TIME = True
SOURCE_OPEN_ONCE_PER_DAY = True
EXPECTED_DAYS = 7
EXPECTED_LANES_PER_DAY = 40
EXPECTED_TOTAL_LANES = 280
EXPECTED_TOTAL_PARTITIONS = 280


class CanonicalRunnerError(RuntimeError):
    pass


@dataclass(frozen=True)
class VerifiedSource:
    day: str
    path: str
    rows: int
    bytes: int
    sha256: str


@dataclass(frozen=True)
class LaneArtifact:
    lane_id: str
    relpath: str
    bytes: int
    sha256: str
    row_count: int


@dataclass(frozen=True)
class RunnerSummary:
    status: str
    verified_source_count: int
    completed_day_count: int
    completed_lane_count: int
    partition_count: int
    attempt_consumed: bool
    failure: str | None


@dataclass
class RunnerHooks:
    attempt_marker_exists: Callable[[], bool]
    verify_source: Callable[[r2.FrozenSourceRecord], VerifiedSource]
    write_attempt_marker: Callable[[Mapping[str, object]], None]
    open_day_source: Callable[[VerifiedSource], object]
    run_lane: Callable[[object, r1.LaneSpec], LaneArtifact]
    close_day_source: Callable[[object], None]
    verify_partition: Callable[[LaneArtifact], None]
    write_failure_artifact: Callable[[Mapping[str, object]], None]
    write_final_manifest: Callable[[Mapping[str, object]], None]


def _assert_verified_source(expected: r2.FrozenSourceRecord, observed: VerifiedSource) -> None:
    if (
        observed.day != expected.day
        or observed.path != expected.path
        or observed.rows != expected.rows
        or observed.bytes != expected.bytes
        or observed.sha256 != expected.sha256
    ):
        raise CanonicalRunnerError(f"source_identity_mismatch:{expected.day}")


def _assert_lane_artifact(lane: r1.LaneSpec, artifact: LaneArtifact) -> None:
    if artifact.lane_id != lane.lane_id:
        raise CanonicalRunnerError(f"lane_artifact_identity:{lane.lane_id}")
    if artifact.relpath != lane.partition_relpath:
        raise CanonicalRunnerError(f"partition_relpath:{lane.lane_id}")
    if artifact.bytes < 0 or artifact.row_count < 0:
        raise CanonicalRunnerError(f"partition_counts:{lane.lane_id}")
    if len(artifact.sha256) != 64:
        raise CanonicalRunnerError(f"partition_sha256:{lane.lane_id}")


def _attempt_payload() -> dict[str, object]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "data_role": DATA_ROLE,
        "source_registry_sha256": r2.FROZEN_SOURCE_REGISTRY_SHA256,
        "attempt_consumption_event": r3.ATTEMPT_CONSUMPTION_EVENT,
        "expected_lanes": EXPECTED_TOTAL_LANES,
        "rerun_authorized": False,
        "resume_authorized": False,
    }


def _failure_payload(*, reason: str, completed_days: int, completed_lanes: int) -> dict[str, object]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "status": "TERMINAL_FAILURE_AFTER_ATTEMPT_CONSUMPTION",
        "reason": reason,
        "completed_day_count": completed_days,
        "completed_lane_count": completed_lanes,
        "attempt_consumed": True,
        "rerun_authorized": False,
        "resume_authorized": False,
    }


def _final_payload(
    *,
    verified: Sequence[VerifiedSource],
    artifacts: Sequence[LaneArtifact],
) -> dict[str, object]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "status": "CANONICAL_280_PARTITIONS_COMPLETE",
        "data_role": DATA_ROLE,
        "source_registry_sha256": r2.FROZEN_SOURCE_REGISTRY_SHA256,
        "verified_source_count": len(verified),
        "completed_lane_count": len(artifacts),
        "partition_count": len(artifacts),
        "attempt_consumed": True,
        "model_fit": False,
        "pnl": False,
        "live_trading": False,
    }


def run_canonical_materialization(
    *,
    authorization_value: str | None,
    hooks: RunnerHooks,
) -> RunnerSummary:
    """Orchestration only. Real historical/simulator hooks remain unbound in R4."""
    r3.validate_execution_authorization_contract()
    r3.require_authorization(authorization_value)
    r2.validate_frozen_source_registry()

    if hooks.attempt_marker_exists():
        raise CanonicalRunnerError("attempt_already_consumed")

    # All seven identities must pass before the attempt can be consumed.
    verified: list[VerifiedSource] = []
    for expected in r2.FROZEN_SOURCE_REGISTRY:
        observed = hooks.verify_source(expected)
        _assert_verified_source(expected, observed)
        verified.append(observed)

    if len(verified) != EXPECTED_DAYS:
        raise CanonicalRunnerError("verified_source_count")

    plan = r1.build_materialization_plan()
    if len(plan) != EXPECTED_TOTAL_LANES:
        raise CanonicalRunnerError("lane_plan_count")

    lanes_by_day: dict[str, list[r1.LaneSpec]] = {x.day: [] for x in verified}
    for lane in plan:
        lanes_by_day[lane.day].append(lane)
    if any(len(v) != EXPECTED_LANES_PER_DAY for v in lanes_by_day.values()):
        raise CanonicalRunnerError("lanes_per_day")

    # This exact write is the attempt-consumption boundary and MUST precede
    # the first canonical simulator lane start.
    hooks.write_attempt_marker(_attempt_payload())
    attempt_consumed = True

    artifacts: list[LaneArtifact] = []
    completed_days = 0

    try:
        for source in verified:
            handle = hooks.open_day_source(source)
            try:
                day_artifacts: list[LaneArtifact] = []
                for lane in lanes_by_day[source.day]:
                    artifact = hooks.run_lane(handle, lane)
                    _assert_lane_artifact(lane, artifact)
                    hooks.verify_partition(artifact)
                    day_artifacts.append(artifact)
                if len(day_artifacts) != EXPECTED_LANES_PER_DAY:
                    raise CanonicalRunnerError(f"day_partition_count:{source.day}")
                artifacts.extend(day_artifacts)
            finally:
                hooks.close_day_source(handle)
            completed_days += 1
    except Exception as exc:
        reason = f"{type(exc).__name__}:{exc}"
        hooks.write_failure_artifact(
            _failure_payload(
                reason=reason,
                completed_days=completed_days,
                completed_lanes=len(artifacts),
            )
        )
        return RunnerSummary(
            status="TERMINAL_FAILURE_AFTER_ATTEMPT_CONSUMPTION",
            verified_source_count=len(verified),
            completed_day_count=completed_days,
            completed_lane_count=len(artifacts),
            partition_count=len(artifacts),
            attempt_consumed=attempt_consumed,
            failure=reason,
        )

    if completed_days != EXPECTED_DAYS:
        raise CanonicalRunnerError("completed_day_count")
    if len(artifacts) != EXPECTED_TOTAL_PARTITIONS:
        raise CanonicalRunnerError("partition_count")
    if len({x.lane_id for x in artifacts}) != EXPECTED_TOTAL_PARTITIONS:
        raise CanonicalRunnerError("duplicate_lane_artifact")

    hooks.write_final_manifest(_final_payload(verified=verified, artifacts=artifacts))
    return RunnerSummary(
        status="CANONICAL_280_PARTITIONS_COMPLETE",
        verified_source_count=len(verified),
        completed_day_count=completed_days,
        completed_lane_count=len(artifacts),
        partition_count=len(artifacts),
        attempt_consumed=attempt_consumed,
        failure=None,
    )


def validate_runner_contract() -> None:
    r3.validate_execution_authorization_contract()
    if PARENT_P2_R3_HEAD != "49f3d4c522d5010ff1c957b70e11a2341f11dded":
        raise CanonicalRunnerError("parent")
    if DATA_ROLE != "CONSUMED_DEVELOPMENT":
        raise CanonicalRunnerError("data_role")
    if (EXPECTED_DAYS, EXPECTED_LANES_PER_DAY, EXPECTED_TOTAL_LANES, EXPECTED_TOTAL_PARTITIONS) != (7, 40, 280, 280):
        raise CanonicalRunnerError("cardinality")
    if not all((PREEXECUTION_ONLY, PRECHECK_ALL_SEVEN_SOURCES_BEFORE_ATTEMPT, ATTEMPT_MARKER_BEFORE_FIRST_LANE, STOP_ON_FIRST_FAILURE, NO_RESUME_AFTER_ATTEMPT, NO_RERUN_AFTER_ATTEMPT, ONE_DAY_AT_A_TIME, SOURCE_OPEN_ONCE_PER_DAY)):
        raise CanonicalRunnerError("required_guard_disabled")
    if any((REAL_EXECUTION_BINDING_AUTHORIZED, HISTORICAL_FILE_IO_AUTHORIZED, SIMULATOR_IMPORT_AUTHORIZED, CANONICAL_LABEL_WRITE_AUTHORIZED, MODEL_FIT_AUTHORIZED, PNL_AUTHORIZED, LIVE_TRADING_AUTHORIZED, AUG_OPEN_AUTHORIZED, SEP_PLUS_OPEN_AUTHORIZED, NON_BTC_OPEN_AUTHORIZED, NETWORK_ACQUISITION_AUTHORIZED)):
        raise CanonicalRunnerError("closed_surface_open")


__all__ = [
    "VerifiedSource",
    "LaneArtifact",
    "RunnerSummary",
    "RunnerHooks",
    "run_canonical_materialization",
    "validate_runner_contract",
]

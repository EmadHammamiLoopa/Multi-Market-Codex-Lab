from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from multimarket import (
    dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1,
)
from multimarket import (
    dev045_d6r26a_p2_r2_frozen_source_registry as r2,
)
from multimarket import (
    dev045_d6r26a_p2_r3_execution_authorization_contract as r3,
)
from multimarket import (
    dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4,
)
from multimarket import (
    dev045_d6r26a_p2_r5_real_engine_binding_prehistorical as r5,
)
from multimarket import (
    dev045_d6r26a_p2_r8a_real_hooks_writer_preexecution as r8a,
)
from multimarket import (
    dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17,
)
from multimarket import (
    dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20,
)
from multimarket import (
    dev045_d6r26a_p2_r21_generic_lane_executor_preexecution as r21,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R22"
DESIGN_VERSION = (
    "final-successor-campaign-runner-binding-preauthorization-v1"
)
PARENT_R21_HEAD = (
    "a667c20be84a2e4496cd9d7ddb90fbba5237120b"
)

FINAL_SUCCESSOR_RUNNER_FROZEN = True
REAL_CALLBACK_BINDING_IMPLEMENTED = True

PRECHECK_ALL_SEVEN_IDENTITIES_BEFORE_ANY_SOURCE_OPEN = True
ENGINE_IDENTITY_PRECHECK_BEFORE_ANY_SIMULATOR_LANE = True

FIRST_DAY_CONTEXT_PREPARED_BEFORE_ATTEMPT_CONSUMPTION = True
FIRST_DAY_CONTEXT_FAILURE_CONSUMES_ATTEMPT = False

FIRST_LANE_START_CONSUMES_ATTEMPT = True
ATTEMPT_MARKER_IMMEDIATELY_BEFORE_FIRST_RUN_LANE = True
NO_CALLBACK_BETWEEN_FIRST_MARKER_AND_FIRST_RUN_LANE = True

ONE_SOURCE_OPEN_PER_DAY = True
ONE_DAY_CONTEXT_PER_DAY = True
ONE_RAW_CONTEXT_PASS_PER_DAY = True
FORTY_FRESH_ENGINES_PER_DAY = True
FRESH_ENGINE_PER_LANE = True
SEQUENTIAL_REFERENCE_DRIVER = True
STOP_ON_FIRST_FAILURE = True

EXPECTED_SOURCE_COUNT = 7
EXPECTED_LANES_PER_DAY = 40
EXPECTED_TOTAL_LANES = 280
EXPECTED_TOTAL_PARTITIONS = 280

SOURCE_READ_ONLY_REQUIRED = True
SOURCE_PERIOD_IS_UTC_24H_DAY = True
NATURAL_END_OF_DATA_IS_VALID_TERMINAL = True
POST_EOF_ORDER_REQUEST_FORBIDDEN = True

R20_CONTEXT_CLOSE_BEFORE_SOURCE_MMAP_CLOSE = True
R21_ENGINE_CLOSE_INSIDE_EACH_LANE = True

OUTPUT_ROOT_MUST_BE_PRISTINE_BEFORE_ATTEMPT = True
PARTITION_VERIFY_IMMEDIATELY_AFTER_LANE = True
FINAL_MANIFEST_ONLY_AFTER_280_VERIFIED_PARTITIONS = True

RERUN_AFTER_ATTEMPT_MARKER_AUTHORIZED = False
RESUME_AFTER_ATTEMPT_MARKER_AUTHORIZED = False
AUTOMATIC_RETRY_AUTHORIZED = False

# Correct D6R14 memory policy.
PREEXEC_MIN_MEMAVAILABLE_BYTES = 8_442_945_536
RUNTIME_MIN_MEMAVAILABLE_BYTES = 4_294_967_296
PROCESS_SWAP_GROWTH_ABORT = True
ANON_GROWTH_ABORT_THRESHOLD_BYTES = 536_870_912

TOTAL_RSS_ABORT_THRESHOLD_BYTES = None
TOTAL_RSS_IS_BOUNDEDNESS_GATE = False

# Engine-bound memory baseline, not pre-mmap total RSS.
PER_LANE_ANON_BASELINE_AFTER_ENGINE_BINDING = True
PER_LANE_MEMORY_CHECK_BEFORE_ENGINE_CLOSE = True

P2_ATTEMPT_CONSUMED = False

PREAUTHORIZATION_ONLY = True
EXECUTION_AUTHORIZATION_CREATED = False

HISTORICAL_FILE_IO_AUTHORIZED = False
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_SIMULATOR_LANE_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False

MODEL_FIT_AUTHORIZED = False
MODEL_SELECTION_AUTHORIZED = False
THRESHOLD_TUNING_AUTHORIZED = False
PNL_AUTHORIZED = False
ECONOMIC_ARENA_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False


class SuccessorCampaignError(RuntimeError):
    pass


@dataclass(frozen=True)
class MemorySnapshot:
    mem_available_bytes: int
    rss_anon_bytes: int
    vm_swap_bytes: int


@dataclass
class PreparedRealDay:
    source: r4.VerifiedSource
    source_handle: r8a.DaySourceHandle
    context: r20.DayContextBuildResult
    day_start_local_ns: int
    day_end_exclusive_local_ns: int
    closed: bool = False


@dataclass(frozen=True)
class SuccessorRunnerSummary:
    status: str
    verified_source_count: int
    prepared_day_count: int
    completed_day_count: int
    completed_lane_count: int
    partition_count: int
    attempt_consumed: bool
    failure: str | None


@dataclass
class SuccessorHooks:
    attempt_marker_exists: Callable[[], bool]
    assert_output_pristine: Callable[[], None]

    preflight_memory: Callable[[], MemorySnapshot]
    capture_runtime_memory_baseline: Callable[[], MemorySnapshot]
    check_runtime_memory: Callable[[MemorySnapshot], None]

    verify_source: Callable[
        [r2.FrozenSourceRecord],
        r4.VerifiedSource,
    ]

    verify_engine_identity: Callable[[], None]

    prepare_day: Callable[
        [r4.VerifiedSource],
        object,
    ]

    close_prepared_day: Callable[
        [object],
        None,
    ]

    write_attempt_marker: Callable[
        [Mapping[str, object]],
        None,
    ]

    run_lane: Callable[
        [object, r1.LaneSpec],
        r4.LaneArtifact,
    ]

    verify_partition: Callable[
        [r4.LaneArtifact],
        None,
    ]

    write_failure_artifact: Callable[
        [Mapping[str, object]],
        None,
    ]

    write_final_manifest: Callable[
        [Mapping[str, object]],
        None,
    ]


def utc_day_bounds_ns(
    day: str,
) -> tuple[int, int]:
    if day not in r1.REAL_DEVELOPMENT_DAYS:
        raise SuccessorCampaignError(
            f"day_not_frozen:{day}"
        )

    parsed = datetime.strptime(
        day,
        "%Y-%m-%d",
    ).replace(
        tzinfo=timezone.utc
    )

    start_seconds = calendar.timegm(
        parsed.utctimetuple()
    )

    start = (
        int(start_seconds)
        * 1_000_000_000
    )

    end = (
        start
        + r17.NOMINAL_DAY_NS
    )

    if (
        end - start
        != 86_400_000_000_000
    ):
        raise SuccessorCampaignError(
            "day_span"
        )

    return start, end


def _read_kib_field(
    text: str,
    field: str,
) -> int:
    prefix = field + ":"

    matches = [
        line
        for line in text.splitlines()
        if line.startswith(prefix)
    ]

    if len(matches) != 1:
        raise SuccessorCampaignError(
            f"proc_field:{field}"
        )

    parts = (
        matches[0]
        .split(":", 1)[1]
        .strip()
        .split()
    )

    if not parts:
        raise SuccessorCampaignError(
            f"proc_field_empty:{field}"
        )

    value = int(parts[0])

    if value < 0:
        raise SuccessorCampaignError(
            f"proc_field_negative:{field}"
        )

    if (
        len(parts) >= 2
        and parts[1] != "kB"
    ):
        raise SuccessorCampaignError(
            f"proc_field_unit:{field}"
        )

    return value * 1024


def memory_snapshot_from_text(
    *,
    meminfo_text: str,
    status_text: str,
) -> MemorySnapshot:
    return MemorySnapshot(
        mem_available_bytes=(
            _read_kib_field(
                meminfo_text,
                "MemAvailable",
            )
        ),
        rss_anon_bytes=(
            _read_kib_field(
                status_text,
                "RssAnon",
            )
        ),
        vm_swap_bytes=(
            _read_kib_field(
                status_text,
                "VmSwap",
            )
        ),
    )


def read_memory_snapshot() -> MemorySnapshot:
    return memory_snapshot_from_text(
        meminfo_text=Path(
            "/proc/meminfo"
        ).read_text(
            encoding="utf-8"
        ),
        status_text=Path(
            "/proc/self/status"
        ).read_text(
            encoding="utf-8"
        ),
    )


def validate_preexec_memory(
    snapshot: MemorySnapshot,
) -> None:
    if (
        snapshot.mem_available_bytes
        < PREEXEC_MIN_MEMAVAILABLE_BYTES
    ):
        raise SuccessorCampaignError(
            "preexec_memavailable"
        )


def validate_runtime_memory(
    *,
    baseline: MemorySnapshot,
    observed: MemorySnapshot,
) -> None:
    if (
        observed.mem_available_bytes
        < RUNTIME_MIN_MEMAVAILABLE_BYTES
    ):
        raise SuccessorCampaignError(
            "runtime_memavailable"
        )

    if (
        PROCESS_SWAP_GROWTH_ABORT
        and observed.vm_swap_bytes
        > baseline.vm_swap_bytes
    ):
        raise SuccessorCampaignError(
            "process_swap_growth"
        )

    anonymous_growth = (
        observed.rss_anon_bytes
        - baseline.rss_anon_bytes
    )

    if (
        anonymous_growth
        > ANON_GROWTH_ABORT_THRESHOLD_BYTES
    ):
        raise SuccessorCampaignError(
            f"anonymous_growth:"
            f"{anonymous_growth}"
        )


def _assert_verified_source(
    expected: r2.FrozenSourceRecord,
    observed: r4.VerifiedSource,
) -> None:
    expected_identity = (
        expected.day,
        expected.path,
        int(expected.rows),
        int(expected.bytes),
        expected.sha256,
    )

    observed_identity = (
        observed.day,
        observed.path,
        int(observed.rows),
        int(observed.bytes),
        observed.sha256,
    )

    if observed_identity != expected_identity:
        raise SuccessorCampaignError(
            f"source_identity:"
            f"{expected.day}"
        )


def _assert_lane_artifact(
    lane: r1.LaneSpec,
    artifact: r4.LaneArtifact,
) -> None:
    if artifact.lane_id != lane.lane_id:
        raise SuccessorCampaignError(
            f"artifact_lane:"
            f"{lane.lane_id}"
        )

    if (
        artifact.relpath
        != lane.partition_relpath
    ):
        raise SuccessorCampaignError(
            f"artifact_relpath:"
            f"{lane.lane_id}"
        )

    if (
        int(artifact.bytes) < 0
        or int(artifact.row_count) < 0
    ):
        raise SuccessorCampaignError(
            f"artifact_counts:"
            f"{lane.lane_id}"
        )

    if len(artifact.sha256) != 64:
        raise SuccessorCampaignError(
            f"artifact_sha:"
            f"{lane.lane_id}"
        )


def _attempt_payload() -> dict[str, object]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "data_role": r2.DATA_ROLE,
        "source_registry_sha256": (
            r2.FROZEN_SOURCE_REGISTRY_SHA256
        ),
        "attempt_consumption_event": (
            r3.ATTEMPT_CONSUMPTION_EVENT
        ),
        "expected_sources": (
            EXPECTED_SOURCE_COUNT
        ),
        "expected_lanes": (
            EXPECTED_TOTAL_LANES
        ),
        "rerun_authorized": False,
        "resume_authorized": False,
    }


def _failure_payload(
    *,
    reason: str,
    completed_days: int,
    completed_lanes: int,
) -> dict[str, object]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "status": (
            "TERMINAL_FAILURE_AFTER_ATTEMPT_CONSUMPTION"
        ),
        "reason": reason,
        "completed_day_count": (
            int(completed_days)
        ),
        "completed_lane_count": (
            int(completed_lanes)
        ),
        "attempt_consumed": True,
        "rerun_authorized": False,
        "resume_authorized": False,
    }


def _final_payload(
    *,
    verified_source_count: int,
    completed_day_count: int,
    artifacts: tuple[
        r4.LaneArtifact,
        ...,
    ],
) -> dict[str, object]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "status": (
            "CANONICAL_280_PARTITIONS_COMPLETE"
        ),
        "data_role": r2.DATA_ROLE,
        "source_registry_sha256": (
            r2.FROZEN_SOURCE_REGISTRY_SHA256
        ),
        "verified_source_count": (
            int(verified_source_count)
        ),
        "completed_day_count": (
            int(completed_day_count)
        ),
        "completed_lane_count": (
            len(artifacts)
        ),
        "partition_count": (
            len(artifacts)
        ),
        "attempt_consumed": True,
        "model_fit": False,
        "pnl": False,
        "live_trading": False,
    }


def run_successor_campaign(
    *,
    authorization_value: str | None,
    hooks: SuccessorHooks,
) -> SuccessorRunnerSummary:
    r3.validate_execution_authorization_contract()

    r3.require_authorization(
        authorization_value
    )

    r2.validate_frozen_source_registry()

    if hooks.attempt_marker_exists():
        raise SuccessorCampaignError(
            "attempt_already_consumed"
        )

    hooks.assert_output_pristine()

    preexec_memory = (
        hooks.preflight_memory()
    )

    validate_preexec_memory(
        preexec_memory
    )

    # All seven exact identities before any source is opened.
    verified: list[
        r4.VerifiedSource
    ] = []

    for expected in (
        r2.FROZEN_SOURCE_REGISTRY
    ):
        observed = (
            hooks.verify_source(
                expected
            )
        )

        _assert_verified_source(
            expected,
            observed,
        )

        verified.append(
            observed
        )

    if len(verified) != EXPECTED_SOURCE_COUNT:
        raise SuccessorCampaignError(
            "verified_source_count"
        )

    # Engine identity is also a pure pre-attempt check.
    hooks.verify_engine_identity()

    plan = (
        r1.build_materialization_plan()
    )

    if len(plan) != EXPECTED_TOTAL_LANES:
        raise SuccessorCampaignError(
            "lane_plan_count"
        )

    lanes_by_day = {
        source.day: []
        for source in verified
    }

    for lane in plan:
        lanes_by_day[
            lane.day
        ].append(
            lane
        )

    if any(
        len(items)
        != EXPECTED_LANES_PER_DAY
        for items in lanes_by_day.values()
    ):
        raise SuccessorCampaignError(
            "lanes_per_day"
        )

    attempt_consumed = False

    artifacts: list[
        r4.LaneArtifact
    ] = []

    prepared_day_count = 0
    completed_day_count = 0

    try:
        for source in verified:
            prepared = None

            try:
                # First historical source/context preparation is still
                # PRE-ATTEMPT. R3 consumes only when the first simulator
                # lane begins.
                prepared = hooks.prepare_day(
                    source
                )

                prepared_day_count += 1

                runtime_baseline = (
                    hooks.capture_runtime_memory_baseline()
                )

                day_artifacts: list[
                    r4.LaneArtifact
                ] = []

                for lane in lanes_by_day[
                    source.day
                ]:
                    # Final pre-marker callback on lane 1.
                    hooks.check_runtime_memory(
                        runtime_baseline
                    )

                    if not attempt_consumed:
                        hooks.write_attempt_marker(
                            _attempt_payload()
                        )

                        attempt_consumed = True

                    # IMPORTANT: on first lane there is no callback between
                    # the marker write and this call.
                    artifact = hooks.run_lane(
                        prepared,
                        lane,
                    )

                    _assert_lane_artifact(
                        lane,
                        artifact,
                    )

                    hooks.verify_partition(
                        artifact
                    )

                    hooks.check_runtime_memory(
                        runtime_baseline
                    )

                    day_artifacts.append(
                        artifact
                    )

                    artifacts.append(
                        artifact
                    )

                if (
                    len(day_artifacts)
                    != EXPECTED_LANES_PER_DAY
                ):
                    raise SuccessorCampaignError(
                        f"day_partition_count:"
                        f"{source.day}"
                    )

            finally:
                if prepared is not None:
                    hooks.close_prepared_day(
                        prepared
                    )

            completed_day_count += 1

    except Exception as exc:
        reason = (
            f"{type(exc).__name__}:"
            f"{exc}"
        )

        if not attempt_consumed:
            raise SuccessorCampaignError(
                f"PRE_ATTEMPT_FAILURE:"
                f"{reason}"
            ) from exc

        hooks.write_failure_artifact(
            _failure_payload(
                reason=reason,
                completed_days=(
                    completed_day_count
                ),
                completed_lanes=(
                    len(artifacts)
                ),
            )
        )

        return SuccessorRunnerSummary(
            status=(
                "TERMINAL_FAILURE_AFTER_ATTEMPT_CONSUMPTION"
            ),
            verified_source_count=(
                len(verified)
            ),
            prepared_day_count=(
                prepared_day_count
            ),
            completed_day_count=(
                completed_day_count
            ),
            completed_lane_count=(
                len(artifacts)
            ),
            partition_count=(
                len(artifacts)
            ),
            attempt_consumed=True,
            failure=reason,
        )

    if (
        completed_day_count
        != EXPECTED_SOURCE_COUNT
    ):
        raise SuccessorCampaignError(
            "completed_day_count"
        )

    if (
        len(artifacts)
        != EXPECTED_TOTAL_PARTITIONS
    ):
        raise SuccessorCampaignError(
            "partition_count"
        )

    if (
        len(
            {
                item.lane_id
                for item in artifacts
            }
        )
        != EXPECTED_TOTAL_PARTITIONS
    ):
        raise SuccessorCampaignError(
            "duplicate_artifact"
        )

    frozen = tuple(
        artifacts
    )

    hooks.write_final_manifest(
        _final_payload(
            verified_source_count=(
                len(verified)
            ),
            completed_day_count=(
                completed_day_count
            ),
            artifacts=frozen,
        )
    )

    return SuccessorRunnerSummary(
        status=(
            "CANONICAL_280_PARTITIONS_COMPLETE"
        ),
        verified_source_count=(
            len(verified)
        ),
        prepared_day_count=(
            prepared_day_count
        ),
        completed_day_count=(
            completed_day_count
        ),
        completed_lane_count=(
            len(frozen)
        ),
        partition_count=(
            len(frozen)
        ),
        attempt_consumed=True,
        failure=None,
    )


def _assert_output_pristine_real(
    *,
    output_root: Path,
) -> None:
    root = Path(
        output_root
    )

    if not root.exists():
        return

    files = tuple(
        path
        for path in root.rglob("*")
        if path.is_file()
    )

    if files:
        raise SuccessorCampaignError(
            "output_root_not_pristine"
        )


def _preflight_memory_real() -> MemorySnapshot:
    observed = read_memory_snapshot()

    validate_preexec_memory(
        observed
    )

    return observed


def _runtime_memory_real(
    baseline: MemorySnapshot,
) -> None:
    validate_runtime_memory(
        baseline=baseline,
        observed=read_memory_snapshot(),
    )


def _prepare_real_day(
    *,
    source: r4.VerifiedSource,
    scratch_root: Path,
) -> PreparedRealDay:
    source_handle = (
        r8a.open_day_source_impl(
            source
        )
    )

    context = None

    try:
        # Full source validation is once/day, never once/lane.
        r8a.validate_engine_input_impl(
            source_handle
        )

        (
            day_start,
            day_end,
        ) = utc_day_bounds_ns(
            source.day
        )

        context = (
            r20.build_once_day_context(
                source_handle.events,
                nominal_day_start_local_ns=(
                    day_start
                ),
                nominal_day_end_exclusive_local_ns=(
                    day_end
                ),
                scratch_root=(
                    Path(scratch_root)
                    / source.day
                ),
            )
        )

        if (
            context.bounds.nominal_day_start_local_ns
            != day_start
        ):
            raise SuccessorCampaignError(
                "context_day_start"
            )

        if (
            context.bounds.nominal_day_end_exclusive_local_ns
            != day_end
        ):
            raise SuccessorCampaignError(
                "context_day_end"
            )

        return PreparedRealDay(
            source=source,
            source_handle=source_handle,
            context=context,
            day_start_local_ns=(
                day_start
            ),
            day_end_exclusive_local_ns=(
                day_end
            ),
        )

    except Exception:
        if context is not None:
            r20.close_midpoint_index(
                context.midpoint_index
            )

        r8a.close_day_source_impl(
            source_handle
        )

        raise


def _close_real_day(
    prepared: PreparedRealDay,
) -> None:
    if prepared.closed:
        raise SuccessorCampaignError(
            "prepared_day_already_closed"
        )

    try:
        r20.close_midpoint_index(
            prepared.context.midpoint_index
        )

    finally:
        r8a.close_day_source_impl(
            prepared.source_handle
        )

        prepared.closed = True


def _run_real_lane(
    *,
    prepared: PreparedRealDay,
    lane: r1.LaneSpec,
    output_root: Path,
) -> r4.LaneArtifact:
    if prepared.closed:
        raise SuccessorCampaignError(
            "prepared_day_closed"
        )

    if lane.day != prepared.source.day:
        raise SuccessorCampaignError(
            "lane_day_binding"
        )

    engine = (
        r8a.new_engine_impl(
            prepared.source_handle
        )
    )

    # D6R14 semantics: anonymous-memory baseline AFTER engine binding.
    engine_memory_baseline = (
        read_memory_snapshot()
    )

    frozen_source = (
        r1.FrozenSourceIdentity(
            day=prepared.source.day,
            path=prepared.source.path,
            bytes=prepared.source.bytes,
            sha256=prepared.source.sha256,
        )
    )

    try:
        summary = (
            r21.execute_and_materialize_lane(
                engine=engine,
                source=frozen_source,
                lane=lane,
                day_start_local_ns=(
                    prepared.day_start_local_ns
                ),
                context=prepared.context,
                output_root=(
                    Path(output_root)
                ),
            )
        )

        # Check while engine remains bound, before close.
        validate_runtime_memory(
            baseline=engine_memory_baseline,
            observed=read_memory_snapshot(),
        )

        return summary.artifact

    finally:
        r8a.close_engine_impl(
            engine
        )


def build_real_successor_hooks(
    *,
    output_root: Path,
    scratch_root: Path,
) -> SuccessorHooks:
    """
    Construct real callbacks only.

    This function itself performs no historical file access and does not
    write the attempt marker.
    """
    output_root = Path(
        output_root
    )

    scratch_root = Path(
        scratch_root
    )

    return SuccessorHooks(
        attempt_marker_exists=lambda: (
            output_root.joinpath(
                r8a.ATTEMPT_MARKER_RELPATH
            ).exists()
        ),

        assert_output_pristine=lambda: (
            _assert_output_pristine_real(
                output_root=output_root
            )
        ),

        preflight_memory=(
            _preflight_memory_real
        ),

        capture_runtime_memory_baseline=(
            read_memory_snapshot
        ),

        check_runtime_memory=(
            _runtime_memory_real
        ),

        verify_source=(
            r8a.verify_source_impl
        ),

        verify_engine_identity=lambda: (
            r5.verify_engine_identity()
            and None
        ),

        prepare_day=lambda source: (
            _prepare_real_day(
                source=source,
                scratch_root=scratch_root,
            )
        ),

        close_prepared_day=(
            _close_real_day
        ),

        write_attempt_marker=lambda payload: (
            r8a.write_control_json_impl(
                root=output_root,
                relpath=(
                    r8a.ATTEMPT_MARKER_RELPATH
                ),
                payload=payload,
            )
            and None
        ),

        run_lane=lambda prepared, lane: (
            _run_real_lane(
                prepared=prepared,
                lane=lane,
                output_root=output_root,
            )
        ),

        verify_partition=lambda artifact: (
            r8a.verify_partition_impl(
                root=output_root,
                artifact=artifact,
            )
        ),

        write_failure_artifact=lambda payload: (
            r8a.write_control_json_impl(
                root=output_root,
                relpath=(
                    r8a.FAILURE_ARTIFACT_RELPATH
                ),
                payload=payload,
            )
            and None
        ),

        write_final_manifest=lambda payload: (
            r8a.write_control_json_impl(
                root=output_root,
                relpath=(
                    r8a.FINAL_MANIFEST_RELPATH
                ),
                payload=payload,
            )
            and None
        ),
    )


def validate_r22_contract() -> None:
    r3.validate_execution_authorization_contract()
    r4.validate_runner_contract()
    r8a.validate_r8a_contract()
    r17.validate_r17_contract()
    r20.validate_r20_contract()
    r21.validate_r21_contract()

    if PARENT_R21_HEAD != (
        "a667c20be84a2e4496cd9d7ddb90fbba5237120b"
    ):
        raise SuccessorCampaignError(
            "parent"
        )

    if (
        r3.ATTEMPT_CONSUMPTION_EVENT
        != (
            "FIRST_CANONICAL_CANDIDATE_SIMULATOR_"
            "LANE_START_AFTER_EXACT_SOURCE_IDENTITY_"
            "VERIFICATION"
        )
    ):
        raise SuccessorCampaignError(
            "attempt_event"
        )

    if (
        EXPECTED_SOURCE_COUNT,
        EXPECTED_LANES_PER_DAY,
        EXPECTED_TOTAL_LANES,
        EXPECTED_TOTAL_PARTITIONS,
    ) != (
        7,
        40,
        280,
        280,
    ):
        raise SuccessorCampaignError(
            "cardinality"
        )

    if (
        TOTAL_RSS_ABORT_THRESHOLD_BYTES
        is not None
    ):
        raise SuccessorCampaignError(
            "total_rss_gate"
        )

    required = (
        FINAL_SUCCESSOR_RUNNER_FROZEN,
        REAL_CALLBACK_BINDING_IMPLEMENTED,
        PRECHECK_ALL_SEVEN_IDENTITIES_BEFORE_ANY_SOURCE_OPEN,
        ENGINE_IDENTITY_PRECHECK_BEFORE_ANY_SIMULATOR_LANE,
        FIRST_DAY_CONTEXT_PREPARED_BEFORE_ATTEMPT_CONSUMPTION,
        not FIRST_DAY_CONTEXT_FAILURE_CONSUMES_ATTEMPT,
        FIRST_LANE_START_CONSUMES_ATTEMPT,
        ATTEMPT_MARKER_IMMEDIATELY_BEFORE_FIRST_RUN_LANE,
        NO_CALLBACK_BETWEEN_FIRST_MARKER_AND_FIRST_RUN_LANE,
        ONE_SOURCE_OPEN_PER_DAY,
        ONE_DAY_CONTEXT_PER_DAY,
        ONE_RAW_CONTEXT_PASS_PER_DAY,
        FORTY_FRESH_ENGINES_PER_DAY,
        FRESH_ENGINE_PER_LANE,
        SEQUENTIAL_REFERENCE_DRIVER,
        STOP_ON_FIRST_FAILURE,
        SOURCE_READ_ONLY_REQUIRED,
        SOURCE_PERIOD_IS_UTC_24H_DAY,
        NATURAL_END_OF_DATA_IS_VALID_TERMINAL,
        POST_EOF_ORDER_REQUEST_FORBIDDEN,
        R20_CONTEXT_CLOSE_BEFORE_SOURCE_MMAP_CLOSE,
        R21_ENGINE_CLOSE_INSIDE_EACH_LANE,
        OUTPUT_ROOT_MUST_BE_PRISTINE_BEFORE_ATTEMPT,
        PARTITION_VERIFY_IMMEDIATELY_AFTER_LANE,
        FINAL_MANIFEST_ONLY_AFTER_280_VERIFIED_PARTITIONS,
        PROCESS_SWAP_GROWTH_ABORT,
        not TOTAL_RSS_IS_BOUNDEDNESS_GATE,
        PER_LANE_ANON_BASELINE_AFTER_ENGINE_BINDING,
        PER_LANE_MEMORY_CHECK_BEFORE_ENGINE_CLOSE,
        P2_ATTEMPT_CONSUMED is False,
        PREAUTHORIZATION_ONLY,
        r21.POST_EOF_ORDER_REQUEST_FORBIDDEN,
        r20.COMBINED_RAW_EVENT_PASSES_PER_DAY
        == 1,
        r17.NOMINAL_DAY_NS
        == 86_400_000_000_000,
    )

    if not all(required):
        raise SuccessorCampaignError(
            "required_guard"
        )

    forbidden = (
        RERUN_AFTER_ATTEMPT_MARKER_AUTHORIZED,
        RESUME_AFTER_ATTEMPT_MARKER_AUTHORIZED,
        AUTOMATIC_RETRY_AUTHORIZED,
        EXECUTION_AUTHORIZATION_CREATED,
        HISTORICAL_FILE_IO_AUTHORIZED,
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_SIMULATOR_LANE_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        MODEL_SELECTION_AUTHORIZED,
        THRESHOLD_TUNING_AUTHORIZED,
        PNL_AUTHORIZED,
        ECONOMIC_ARENA_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        NETWORK_ACQUISITION_AUTHORIZED,
    )

    if any(forbidden):
        raise SuccessorCampaignError(
            "closed_surface_open"
        )


__all__ = [
    "MemorySnapshot",
    "PreparedRealDay",
    "SuccessorRunnerSummary",
    "SuccessorHooks",
    "utc_day_bounds_ns",
    "memory_snapshot_from_text",
    "validate_preexec_memory",
    "validate_runtime_memory",
    "run_successor_campaign",
    "build_real_successor_hooks",
    "validate_r22_contract",
]

from __future__ import annotations

from pathlib import Path

from multimarket import (
    dev045_d6r26a_p2_r22_final_successor_campaign_runner_binding_preauthorization as r22,
)
from multimarket import (
    dev045_d6r26a_p2_r23_final_one_shot_readiness_authorization_preflight as r23,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R23A"
DESIGN_VERSION = (
    "execution-head-lineage-amendment-preflight-v1"
)

PARENT_R23_HEAD = (
    "124dc037b1fab545a336d830419d40ed55138c8c"
)

EXECUTION_HEAD_AMENDMENT_FROZEN = True
EXACT_EXECUTION_HEAD_MUST_BE_SUPPLIED_BY_ONE_SHOT_WRAPPER = True
R23_PARENT_LINEAGE_REQUIRED = True
CLEAN_WORKTREE_REQUIRED = True

# All source/readiness semantics remain R23.
SOURCE_METADATA_ONLY = True
HISTORICAL_PAYLOAD_READ_AUTHORIZED = False
SOURCE_NPY_LOAD_AUTHORIZED = False
SOURCE_MMAP_AUTHORIZED = False
SOURCE_REHASH_AUTHORIZED = False
SOURCE_ROW_SCAN_AUTHORIZED = False

ATTEMPT_MARKER_WRITE_AUTHORIZED = False
HISTORICAL_SIMULATOR_LANE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False

P2_ATTEMPT_CONSUMED = False
ONE_SHOT_EXECUTION_STARTED = False

MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False


class ExecutionHeadPreflightError(RuntimeError):
    pass


def _validate_expected_head(
    expected_execution_head: str,
) -> str:
    value = str(
        expected_execution_head
    ).strip()

    if (
        len(value) != 40
        or any(
            ch not in "0123456789abcdef"
            for ch in value
        )
    ):
        raise ExecutionHeadPreflightError(
            "expected_execution_head"
        )

    return value


def run_readiness_preflight(
    *,
    hooks: r23.ReadinessHooks,
    expected_execution_head: str,
    output_root: Path = r23.CANONICAL_OUTPUT_ROOT,
    scratch_root: Path = r23.CANONICAL_SCRATCH_ROOT,
) -> r23.ReadinessReport:
    """
    R23 readiness semantics with the execution HEAD supplied explicitly by
    the final one-shot wrapper.

    This avoids the impossible R23-v1 condition that required live HEAD to
    equal its parent R22 commit.
    """
    r23.validate_r23_contract()

    expected_head = (
        _validate_expected_head(
            expected_execution_head
        )
    )

    observed_head = (
        hooks.repo_head()
    )

    if observed_head != expected_head:
        raise ExecutionHeadPreflightError(
            f"head:"
            f"{observed_head}:"
            f"{expected_head}"
        )

    if not hooks.worktree_clean():
        raise ExecutionHeadPreflightError(
            "worktree_dirty"
        )

    if hooks.attempt_marker_exists():
        raise ExecutionHeadPreflightError(
            "attempt_marker_exists"
        )

    if not hooks.output_root_pristine():
        raise ExecutionHeadPreflightError(
            "output_root_not_pristine"
        )

    r23._validate_scratch_root(
        scratch_root=Path(
            scratch_root
        ),
        output_root=Path(
            output_root
        ),
    )

    if not hooks.scratch_root_pristine():
        raise ExecutionHeadPreflightError(
            "scratch_root_not_pristine"
        )

    metadata: list[
        r23.SourceMetadata
    ] = []

    for expected in (
        r23.r2.FROZEN_SOURCE_REGISTRY
    ):
        observed = (
            hooks.source_metadata(
                expected
            )
        )

        r23._validate_source_metadata(
            expected=expected,
            observed=observed,
        )

        metadata.append(
            observed
        )

    if (
        len(metadata)
        != r23.EXPECTED_SOURCE_COUNT
    ):
        raise ExecutionHeadPreflightError(
            "source_count"
        )

    memory = hooks.memory_snapshot()

    r22.validate_preexec_memory(
        memory
    )

    identity = hooks.engine_identity()

    if (
        identity.version
        != r23.HFTBACKTEST_VERSION
    ):
        raise ExecutionHeadPreflightError(
            "engine_version"
        )

    return r23.ReadinessReport(
        status=(
            "READY_FOR_EXPLICIT_ONE_SHOT_EXECUTION"
        ),
        head=observed_head,
        source_count=len(
            metadata
        ),
        total_source_bytes=sum(
            int(item.bytes)
            for item in metadata
        ),
        mem_available_bytes=(
            memory.mem_available_bytes
        ),
        engine_version=(
            identity.version
        ),
        output_root=str(
            Path(output_root)
        ),
        scratch_root=str(
            Path(scratch_root)
        ),
        attempt_marker_absent=True,
        historical_payload_read=False,
        attempt_consumed=False,
    )


def run_real_readiness_preflight(
    *,
    repo_root: Path,
    expected_execution_head: str,
    output_root: Path = r23.CANONICAL_OUTPUT_ROOT,
    scratch_root: Path = r23.CANONICAL_SCRATCH_ROOT,
) -> r23.ReadinessReport:
    hooks = (
        r23.build_real_readiness_hooks(
            repo_root=Path(
                repo_root
            ),
            output_root=Path(
                output_root
            ),
            scratch_root=Path(
                scratch_root
            ),
        )
    )

    return run_readiness_preflight(
        hooks=hooks,
        expected_execution_head=(
            expected_execution_head
        ),
        output_root=Path(
            output_root
        ),
        scratch_root=Path(
            scratch_root
        ),
    )


def validate_r23a_contract() -> None:
    r23.validate_r23_contract()

    if PARENT_R23_HEAD != (
        "124dc037b1fab545a336d830419d40ed55138c8c"
    ):
        raise ExecutionHeadPreflightError(
            "parent"
        )

    required = (
        EXECUTION_HEAD_AMENDMENT_FROZEN,
        EXACT_EXECUTION_HEAD_MUST_BE_SUPPLIED_BY_ONE_SHOT_WRAPPER,
        R23_PARENT_LINEAGE_REQUIRED,
        CLEAN_WORKTREE_REQUIRED,
        SOURCE_METADATA_ONLY,
        P2_ATTEMPT_CONSUMED is False,
        ONE_SHOT_EXECUTION_STARTED is False,
        r23.PARENT_R22_HEAD
        == (
            "016079a5fae640b4cd5f686aebdec2f7b556a4b3"
        ),
    )

    if not all(required):
        raise ExecutionHeadPreflightError(
            "required_guard"
        )

    forbidden = (
        HISTORICAL_PAYLOAD_READ_AUTHORIZED,
        SOURCE_NPY_LOAD_AUTHORIZED,
        SOURCE_MMAP_AUTHORIZED,
        SOURCE_REHASH_AUTHORIZED,
        SOURCE_ROW_SCAN_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        HISTORICAL_SIMULATOR_LANE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
    )

    if any(forbidden):
        raise ExecutionHeadPreflightError(
            "execution_surface_open"
        )


__all__ = [
    "run_readiness_preflight",
    "run_real_readiness_preflight",
    "validate_r23a_contract",
]

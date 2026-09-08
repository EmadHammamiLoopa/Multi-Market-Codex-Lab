from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Callable

from multimarket import (
    dev045_d6r26a_p2_r2_frozen_source_registry as r2,
)
from multimarket import (
    dev045_d6r26a_p2_r3_execution_authorization_contract as r3,
)
from multimarket import (
    dev045_d6r26a_p2_r5_real_engine_binding_prehistorical as r5,
)
from multimarket import (
    dev045_d6r26a_p2_r22_final_successor_campaign_runner_binding_preauthorization as r22,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R23"
DESIGN_VERSION = (
    "final-one-shot-readiness-authorization-preflight-v1"
)

PARENT_R22_HEAD = (
    "016079a5fae640b4cd5f686aebdec2f7b556a4b3"
)

FINAL_ONE_SHOT_READINESS_PREFLIGHT_FROZEN = True

EXPECTED_SOURCE_COUNT = 7
EXPECTED_TOTAL_LANES = 280

SOURCE_METADATA_STAT_AUTHORIZED = True

# R23 never opens or reads source payloads.
HISTORICAL_PAYLOAD_READ_AUTHORIZED = False
SOURCE_NPY_LOAD_AUTHORIZED = False
SOURCE_MMAP_AUTHORIZED = False
SOURCE_REHASH_AUTHORIZED = False
SOURCE_ROW_SCAN_AUTHORIZED = False

# Exact SHA / row validation happens once inside R22 immediately before
# historical preparation and before the attempt-consumption boundary.
SOURCE_SHA_PREATTEMPT_VERIFICATION_DEFERRED_TO_R22 = True
SOURCE_ROWS_PREATTEMPT_VERIFICATION_DEFERRED_TO_R22 = True

OUTPUT_ROOT_PRISTINE_REQUIRED = True
ATTEMPT_MARKER_ABSENT_REQUIRED = True
SCRATCH_ROOT_PRISTINE_REQUIRED = True

EXACT_R22_HEAD_REQUIRED = True
CLEAN_WORKTREE_REQUIRED = True

PREEXEC_MEMORY_GATE_REQUIRED = True
ENGINE_API_IDENTITY_REQUIRED = True

HFTBACKTEST_VERSION = r5.HFTBACKTEST_VERSION
HFTBACKTEST_UPSTREAM_HEAD = r5.HFTBACKTEST_UPSTREAM_HEAD
HFTBACKTEST_FROZEN_BINARY_SHA256 = (
    r5.HFTBACKTEST_FROZEN_BINARY_SHA256
)

# Binary hash is a frozen lineage identity in R23; R23 does not pretend to
# recompute it from an unknown installation artifact path.
ENGINE_FROZEN_BINARY_SHA_LINEAGE_BOUND = True
ENGINE_RUNTIME_API_IDENTITY_CHECKED_BY_R5 = True

CANONICAL_OUTPUT_ROOT = Path(
    r3.OUTPUT_ROOT
)

CANONICAL_SCRATCH_ROOT = Path(
    "/home/emadh/Multi-Market/runtime/"
    "dev045_d6r26a_p2_canonical_scratch"
)

P2_ATTEMPT_CONSUMED = False
ONE_SHOT_EXECUTION_STARTED = False

EXECUTION_START_FUNCTION_IMPLEMENTED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
HISTORICAL_SIMULATOR_LANE_AUTHORIZED = False

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


class ReadinessPreflightError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceMetadata:
    day: str
    path: str
    bytes: int


@dataclass(frozen=True)
class ReadinessReport:
    status: str
    head: str
    source_count: int
    total_source_bytes: int
    mem_available_bytes: int
    engine_version: str
    output_root: str
    scratch_root: str
    attempt_marker_absent: bool
    historical_payload_read: bool
    attempt_consumed: bool


@dataclass
class ReadinessHooks:
    repo_head: Callable[[], str]
    worktree_clean: Callable[[], bool]

    attempt_marker_exists: Callable[[], bool]
    output_root_pristine: Callable[[], bool]
    scratch_root_pristine: Callable[[], bool]

    source_metadata: Callable[
        [r2.FrozenSourceRecord],
        SourceMetadata,
    ]

    memory_snapshot: Callable[
        [],
        r22.MemorySnapshot,
    ]

    engine_identity: Callable[
        [],
        r5.EngineIdentity,
    ]


def _git(
    repo_root: Path,
    *args: str,
) -> str:
    result = subprocess.run(
        (
            "git",
            "-C",
            str(repo_root),
            *args,
        ),
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


def _real_repo_head(
    repo_root: Path,
) -> str:
    return _git(
        repo_root,
        "rev-parse",
        "HEAD",
    )


def _real_worktree_clean(
    repo_root: Path,
) -> bool:
    return (
        _git(
            repo_root,
            "status",
            "--porcelain",
        )
        == ""
    )


def _tree_has_files(
    root: Path,
) -> bool:
    root = Path(root)

    if not root.exists():
        return False

    if not root.is_dir():
        raise ReadinessPreflightError(
            f"root_not_directory:{root}"
        )

    return any(
        path.is_file()
        or path.is_symlink()
        for path in root.rglob("*")
    )


def _real_source_metadata(
    expected: r2.FrozenSourceRecord,
) -> SourceMetadata:
    path = Path(
        expected.path
    )

    # Metadata only: no open(), no np.load(), no mmap(), no hashing.
    if path.is_symlink():
        raise ReadinessPreflightError(
            f"source_symlink:{expected.day}"
        )

    if not path.is_file():
        raise ReadinessPreflightError(
            f"source_missing:{expected.day}"
        )

    observed_bytes = int(
        path.stat().st_size
    )

    return SourceMetadata(
        day=expected.day,
        path=str(path),
        bytes=observed_bytes,
    )


def _validate_source_metadata(
    *,
    expected: r2.FrozenSourceRecord,
    observed: SourceMetadata,
) -> None:
    if (
        observed.day,
        observed.path,
        int(observed.bytes),
    ) != (
        expected.day,
        expected.path,
        int(expected.bytes),
    ):
        raise ReadinessPreflightError(
            f"source_metadata_mismatch:"
            f"{expected.day}"
        )


def _validate_scratch_root(
    *,
    scratch_root: Path,
    output_root: Path,
) -> None:
    scratch = Path(
        scratch_root
    ).resolve(
        strict=False
    )

    output = Path(
        output_root
    ).resolve(
        strict=False
    )

    if scratch == output:
        raise ReadinessPreflightError(
            "scratch_equals_output"
        )

    for source in (
        r2.FROZEN_SOURCE_REGISTRY
    ):
        source_path = Path(
            source.path
        ).resolve(
            strict=False
        )

        if scratch == source_path:
            raise ReadinessPreflightError(
                "scratch_equals_source"
            )


def run_readiness_preflight(
    *,
    hooks: ReadinessHooks,
    output_root: Path = CANONICAL_OUTPUT_ROOT,
    scratch_root: Path = CANONICAL_SCRATCH_ROOT,
) -> ReadinessReport:
    """
    Metadata/readiness-only preflight.

    No source payload opening, hashing, mmap, label write, marker write or
    simulator execution is reachable through this function.
    """
    r22.validate_r22_contract()
    r2.validate_frozen_source_registry()

    head = hooks.repo_head()

    if head != PARENT_R22_HEAD:
        raise ReadinessPreflightError(
            f"head:{head}"
        )

    if not hooks.worktree_clean():
        raise ReadinessPreflightError(
            "worktree_dirty"
        )

    if hooks.attempt_marker_exists():
        raise ReadinessPreflightError(
            "attempt_marker_exists"
        )

    if not hooks.output_root_pristine():
        raise ReadinessPreflightError(
            "output_root_not_pristine"
        )

    _validate_scratch_root(
        scratch_root=Path(
            scratch_root
        ),
        output_root=Path(
            output_root
        ),
    )

    if not hooks.scratch_root_pristine():
        raise ReadinessPreflightError(
            "scratch_root_not_pristine"
        )

    metadata: list[
        SourceMetadata
    ] = []

    for expected in (
        r2.FROZEN_SOURCE_REGISTRY
    ):
        observed = hooks.source_metadata(
            expected
        )

        _validate_source_metadata(
            expected=expected,
            observed=observed,
        )

        metadata.append(
            observed
        )

    if len(metadata) != EXPECTED_SOURCE_COUNT:
        raise ReadinessPreflightError(
            "source_count"
        )

    memory = hooks.memory_snapshot()

    r22.validate_preexec_memory(
        memory
    )

    identity = hooks.engine_identity()

    if (
        identity.version
        != HFTBACKTEST_VERSION
    ):
        raise ReadinessPreflightError(
            "engine_version"
        )

    return ReadinessReport(
        status=(
            "READY_FOR_EXPLICIT_ONE_SHOT_EXECUTION"
        ),
        head=head,
        source_count=(
            len(metadata)
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


def build_real_readiness_hooks(
    *,
    repo_root: Path,
    output_root: Path = CANONICAL_OUTPUT_ROOT,
    scratch_root: Path = CANONICAL_SCRATCH_ROOT,
) -> ReadinessHooks:
    """
    Construction only. No callback executes until run_readiness_preflight().
    """
    repo_root = Path(
        repo_root
    )

    output_root = Path(
        output_root
    )

    scratch_root = Path(
        scratch_root
    )

    return ReadinessHooks(
        repo_head=lambda: (
            _real_repo_head(
                repo_root
            )
        ),

        worktree_clean=lambda: (
            _real_worktree_clean(
                repo_root
            )
        ),

        attempt_marker_exists=lambda: (
            r3.ATTEMPT_MARKER_PATH.exists()
        ),

        output_root_pristine=lambda: (
            not _tree_has_files(
                output_root
            )
        ),

        scratch_root_pristine=lambda: (
            not _tree_has_files(
                scratch_root
            )
        ),

        source_metadata=(
            _real_source_metadata
        ),

        memory_snapshot=(
            r22.read_memory_snapshot
        ),

        engine_identity=(
            r5.verify_engine_identity
        ),
    )


def run_real_readiness_preflight(
    *,
    repo_root: Path,
    output_root: Path = CANONICAL_OUTPUT_ROOT,
    scratch_root: Path = CANONICAL_SCRATCH_ROOT,
) -> ReadinessReport:
    hooks = build_real_readiness_hooks(
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

    return run_readiness_preflight(
        hooks=hooks,
        output_root=Path(
            output_root
        ),
        scratch_root=Path(
            scratch_root
        ),
    )


def validate_r23_contract() -> None:
    r22.validate_r22_contract()
    r2.validate_frozen_source_registry()

    if PARENT_R22_HEAD != (
        "016079a5fae640b4cd5f686aebdec2f7b556a4b3"
    ):
        raise ReadinessPreflightError(
            "parent"
        )

    if (
        EXPECTED_SOURCE_COUNT,
        EXPECTED_TOTAL_LANES,
    ) != (
        7,
        280,
    ):
        raise ReadinessPreflightError(
            "cardinality"
        )

    if (
        HFTBACKTEST_VERSION
        != "2.4.4"
    ):
        raise ReadinessPreflightError(
            "engine_version_constant"
        )

    if (
        HFTBACKTEST_UPSTREAM_HEAD
        != (
            "a244a14250b42d97fc305569c93c4117cd5e1dff"
        )
    ):
        raise ReadinessPreflightError(
            "engine_upstream"
        )

    if (
        HFTBACKTEST_FROZEN_BINARY_SHA256
        != (
            "5174f486abc4b29cfef565672548798ea"
            "68ec54c0f6c04077bcbdf43f5033752"
        )
    ):
        raise ReadinessPreflightError(
            "engine_binary_sha"
        )

    required = (
        FINAL_ONE_SHOT_READINESS_PREFLIGHT_FROZEN,
        SOURCE_METADATA_STAT_AUTHORIZED,
        SOURCE_SHA_PREATTEMPT_VERIFICATION_DEFERRED_TO_R22,
        SOURCE_ROWS_PREATTEMPT_VERIFICATION_DEFERRED_TO_R22,
        OUTPUT_ROOT_PRISTINE_REQUIRED,
        ATTEMPT_MARKER_ABSENT_REQUIRED,
        SCRATCH_ROOT_PRISTINE_REQUIRED,
        EXACT_R22_HEAD_REQUIRED,
        CLEAN_WORKTREE_REQUIRED,
        PREEXEC_MEMORY_GATE_REQUIRED,
        ENGINE_API_IDENTITY_REQUIRED,
        ENGINE_FROZEN_BINARY_SHA_LINEAGE_BOUND,
        ENGINE_RUNTIME_API_IDENTITY_CHECKED_BY_R5,
        P2_ATTEMPT_CONSUMED is False,
        ONE_SHOT_EXECUTION_STARTED is False,
        EXECUTION_START_FUNCTION_IMPLEMENTED is False,
    )

    if not all(required):
        raise ReadinessPreflightError(
            "required_guard"
        )

    forbidden = (
        HISTORICAL_PAYLOAD_READ_AUTHORIZED,
        SOURCE_NPY_LOAD_AUTHORIZED,
        SOURCE_MMAP_AUTHORIZED,
        SOURCE_REHASH_AUTHORIZED,
        SOURCE_ROW_SCAN_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        HISTORICAL_SIMULATOR_LANE_AUTHORIZED,
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
        raise ReadinessPreflightError(
            "closed_surface_open"
        )


__all__ = [
    "SourceMetadata",
    "ReadinessReport",
    "ReadinessHooks",
    "run_readiness_preflight",
    "build_real_readiness_hooks",
    "run_real_readiness_preflight",
    "validate_r23_contract",
]

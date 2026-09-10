from __future__ import annotations

from pathlib import Path

from multimarket import (
    dev045_d6r26a_p2_r2_frozen_source_registry as r2,
)
from multimarket import (
    dev045_d6r26a_p2_r24_durable_context_performance_preexecution as r24,
)
from multimarket import (
    dev045_d6r26a_p2_r25_durable_day_context_bundle_foundation as r25,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R26P0"
DESIGN_VERSION = "real-durable-materialization-freeze-v1"

PARENT_R25_HEAD = (
    "f9a2b4217f4ae291871b3fac6ff210c88187ed5b"
)

SOURCE_REGISTRY_SHA256 = (
    "97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4"
)

EXPECTED_DAYS = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)

DURABLE_ROOT = Path(
    "/home/emadh/Multi-Market/runtime/"
    "dev045_d6r26a_p2_durable_context_v1"
)

EXACT_RUNTIME_PYTHON = Path(
    "/home/emadh/Multi-Market/runtime/"
    "dev045_d6r26a_p2_exact_runtime_v1/"
    "py313/bin/python"
)

# Source verification happens before any R20 context build.
ALL_SEVEN_SOURCE_IDENTITIES_VERIFIED_BEFORE_BUILD = True
SOURCE_SHA256_VERIFICATION_REQUIRED = True
SOURCE_ROWS_BYTES_VERIFICATION_REQUIRED = True
SOURCE_VERIFICATION_SERIAL = True

# Existing completed durable bundles are reusable only after R25 verification.
COMPLETED_BUNDLE_VERIFY_BEFORE_REUSE = True
COMPLETED_BUNDLE_RAW_CONTEXT_REBUILD_FORBIDDEN = True
INVALID_COMPLETED_BUNDLE_FAIL_CLOSED = True

# Host-power-loss staging residue is never mistaken for completion.
PARTIAL_STAGING_IS_NOT_COMPLETE = True
PARTIAL_STAGING_REUSE_FORBIDDEN = True
PARTIAL_STAGING_AUTO_DELETE_AUTHORIZED = False
PARTIAL_STAGING_PRESERVED_FOR_FORENSICS = True

# Conservative first real materialization policy.
R24_MAX_PARALLEL_CAP = 4
R26_BUILD_WORKER_CAP = 2
DYNAMIC_MEMORY_ADMISSION_REQUIRED = True

GIB = 1024 ** 3

MIN_MEMAVAILABLE_ONE_WORKER_BYTES = 12 * GIB
MIN_MEMAVAILABLE_TWO_WORKERS_BYTES = 20 * GIB
RUNTIME_MEMAVAILABLE_ABORT_BYTES = 8 * GIB

PROCESS_SWAP_GROWTH_FORBIDDEN = True
STOP_ADMISSION_ON_FIRST_FAILURE = True
NO_AUTOMATIC_DAY_RETRY = True

# A later invocation may reuse already completed, verified days because this
# entire materialization stage remains before the canonical simulator attempt.
RESTART_AFTER_PREATTEMPT_INTERRUPTION_AUTHORIZED = True
COMPLETED_DAY_REUSE_AFTER_RESTART_AUTHORIZED = True

P2_ATTEMPT_CONSUMED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False

PREEXECUTION_ONLY = True
THIS_COMMIT_OPENS_HISTORICAL_SOURCE = False
THIS_COMMIT_REHASHES_HISTORICAL_SOURCE = False
THIS_COMMIT_BUILDS_REAL_CONTEXT = False
THIS_COMMIT_RUNS_SIMULATOR = False
THIS_COMMIT_WRITES_CANONICAL_LABELS = False

MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False


class R26P0FreezeError(RuntimeError):
    pass


def admitted_worker_limit(mem_available_bytes: int) -> int:
    """
    Pure admission policy only. No process launch or market-data access.
    """
    available = int(mem_available_bytes)

    if available < 0:
        raise R26P0FreezeError("negative_memavailable")

    if available < MIN_MEMAVAILABLE_ONE_WORKER_BYTES:
        return 0

    if available < MIN_MEMAVAILABLE_TWO_WORKERS_BYTES:
        return 1

    return R26_BUILD_WORKER_CAP


def source_identity(
    day: str,
) -> r25.DurableSourceIdentity:
    matches = [
        record
        for record in r2.FROZEN_SOURCE_REGISTRY
        if record.day == day
    ]

    if len(matches) != 1:
        raise R26P0FreezeError(
            f"source_day:{day}"
        )

    record = matches[0]

    return r25.DurableSourceIdentity(
        day=record.day,
        path=record.path,
        rows=int(record.rows),
        bytes=int(record.bytes),
        sha256=record.sha256,
    )


def durable_day_dir(day: str) -> Path:
    if day not in EXPECTED_DAYS:
        raise R26P0FreezeError(
            f"unauthorized_day:{day}"
        )

    return DURABLE_ROOT / day


def validate_r26p0_contract() -> None:
    r2.validate_frozen_source_registry()
    r24.validate_r24_contract()
    r25.validate_r25_contract()

    if PARENT_R25_HEAD != (
        "f9a2b4217f4ae291871b3fac6ff210c88187ed5b"
    ):
        raise R26P0FreezeError("parent")

    if (
        r2.FROZEN_SOURCE_REGISTRY_SHA256
        != SOURCE_REGISTRY_SHA256
    ):
        raise R26P0FreezeError(
            "source_registry_sha"
        )

    observed_days = tuple(
        record.day
        for record in r2.FROZEN_SOURCE_REGISTRY
    )

    if observed_days != EXPECTED_DAYS:
        raise R26P0FreezeError(
            "day_identity"
        )

    if len(EXPECTED_DAYS) != 7:
        raise R26P0FreezeError(
            "day_count"
        )

    if DURABLE_ROOT.name != (
        r24.DURABLE_ROOT_NAME
    ):
        raise R26P0FreezeError(
            "durable_root_name"
        )

    if tuple(r25.DAY_FILES) != tuple(
        r24.DAY_FILES
    ):
        raise R26P0FreezeError(
            "day_file_contract"
        )

    if (
        R26_BUILD_WORKER_CAP <= 0
        or R26_BUILD_WORKER_CAP
        > R24_MAX_PARALLEL_CAP
        or R24_MAX_PARALLEL_CAP
        != r24.MAX_PARALLEL_DAY_CONTEXT_BUILD_CAP
    ):
        raise R26P0FreezeError(
            "worker_cap"
        )

    if not (
        0
        < RUNTIME_MEMAVAILABLE_ABORT_BYTES
        < MIN_MEMAVAILABLE_ONE_WORKER_BYTES
        < MIN_MEMAVAILABLE_TWO_WORKERS_BYTES
    ):
        raise R26P0FreezeError(
            "memory_threshold_order"
        )

    if admitted_worker_limit(
        MIN_MEMAVAILABLE_ONE_WORKER_BYTES - 1
    ) != 0:
        raise R26P0FreezeError(
            "admission_zero"
        )

    if admitted_worker_limit(
        MIN_MEMAVAILABLE_ONE_WORKER_BYTES
    ) != 1:
        raise R26P0FreezeError(
            "admission_one"
        )

    if admitted_worker_limit(
        MIN_MEMAVAILABLE_TWO_WORKERS_BYTES
    ) != 2:
        raise R26P0FreezeError(
            "admission_two"
        )

    required = (
        ALL_SEVEN_SOURCE_IDENTITIES_VERIFIED_BEFORE_BUILD,
        SOURCE_SHA256_VERIFICATION_REQUIRED,
        SOURCE_ROWS_BYTES_VERIFICATION_REQUIRED,
        SOURCE_VERIFICATION_SERIAL,
        COMPLETED_BUNDLE_VERIFY_BEFORE_REUSE,
        COMPLETED_BUNDLE_RAW_CONTEXT_REBUILD_FORBIDDEN,
        INVALID_COMPLETED_BUNDLE_FAIL_CLOSED,
        PARTIAL_STAGING_IS_NOT_COMPLETE,
        PARTIAL_STAGING_REUSE_FORBIDDEN,
        PARTIAL_STAGING_PRESERVED_FOR_FORENSICS,
        DYNAMIC_MEMORY_ADMISSION_REQUIRED,
        PROCESS_SWAP_GROWTH_FORBIDDEN,
        STOP_ADMISSION_ON_FIRST_FAILURE,
        NO_AUTOMATIC_DAY_RETRY,
        RESTART_AFTER_PREATTEMPT_INTERRUPTION_AUTHORIZED,
        COMPLETED_DAY_REUSE_AFTER_RESTART_AUTHORIZED,
        PREEXECUTION_ONLY,
    )

    if not all(required):
        raise R26P0FreezeError(
            "required_guard"
        )

    forbidden = (
        PARTIAL_STAGING_AUTO_DELETE_AUTHORIZED,
        P2_ATTEMPT_CONSUMED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        THIS_COMMIT_OPENS_HISTORICAL_SOURCE,
        THIS_COMMIT_REHASHES_HISTORICAL_SOURCE,
        THIS_COMMIT_BUILDS_REAL_CONTEXT,
        THIS_COMMIT_RUNS_SIMULATOR,
        THIS_COMMIT_WRITES_CANONICAL_LABELS,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
    )

    if any(forbidden):
        raise R26P0FreezeError(
            "closed_surface_open"
        )


__all__ = [
    "EXPECTED_DAYS",
    "DURABLE_ROOT",
    "EXACT_RUNTIME_PYTHON",
    "R26_BUILD_WORKER_CAP",
    "admitted_worker_limit",
    "source_identity",
    "durable_day_dir",
    "validate_r26p0_contract",
]

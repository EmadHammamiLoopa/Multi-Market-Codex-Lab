from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Sequence
import uuid

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
    dev045_d6r26a_p2_r8a_real_hooks_writer_preexecution as r8a,
)
from multimarket import (
    dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20,
)
from multimarket import (
    dev045_d6r26a_p2_r22_final_successor_campaign_runner_binding_preauthorization as r22,
)
from multimarket import (
    dev045_d6r26a_p2_r25_durable_day_context_bundle_foundation as r25,
)
from multimarket import (
    dev045_d6r26a_p2_r26p0_durable_materialization_freeze as r26p0,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R26P1"
DESIGN_VERSION = "real-durable-materializer-implementation-v1"
PARENT_R26P0_HEAD = "2ec9be95b200437465388a46e04921ccea47ab1e"

AUTH_ENV_NAME = "DEV045_D6R26A_P2_R26P1_AUTHORIZE"
AUTH_TOKEN = "YES_FROZEN_JAN_JUL_DURABLE_CONTEXT_MATERIALIZATION_PREATTEMPT"

COMPLETION_MANIFEST_NAME = (
    "DEV045_D6R26A_P2_R26P1_DURABLE_CONTEXT_MANIFEST.json"
)
COMPLETION_MANIFEST_PATH = r26p0.DURABLE_ROOT / COMPLETION_MANIFEST_NAME
BUILD_ROOT_NAME = ".build"
HASH_CHUNK_BYTES = 8 * 1024 * 1024

REAL_DURABLE_MATERIALIZER_IMPLEMENTED = True
SERIAL_ALL_SEVEN_SOURCE_REVERIFY_IMPLEMENTED = True
R8A_READ_ONLY_SOURCE_OPEN_BOUND = True
R8A_FULL_ENGINE_INPUT_VALIDATION_BOUND = True
R20_ONCE_DAY_CONTEXT_BUILDER_BOUND = True
R25_DURABLE_PERSISTENCE_BOUND = True
R25_REOPEN_VERIFICATION_BOUND = True
R22_UTC_DAY_BOUNDS_BOUND = True

PROCESS_WORKER_PARALLELISM_IMPLEMENTED = True
WORKER_CAP = r26p0.R26_BUILD_WORKER_CAP
DYNAMIC_MEMORY_ADMISSION_IMPLEMENTED = True
ACTIVE_BATCH_MAY_FINISH_AFTER_PEER_FAILURE = True
NO_NEW_ADMISSION_AFTER_FIRST_FAILURE = True
NO_AUTOMATIC_DAY_RETRY = True

COMPLETED_BUNDLE_REUSE_IMPLEMENTED = True
INVALID_COMPLETED_BUNDLE_FAILS_CLOSED = True
PREEXISTING_PARTIAL_BUILD_REUSE_FORBIDDEN = True
PREEXISTING_PARTIAL_BUILD_AUTO_DELETE_FORBIDDEN = True
FAILED_BUILD_RESIDUE_PRESERVED = True
SUCCESSFUL_SCRATCH_DELETE_AFTER_DURABLE_VERIFY = True

P2_ATTEMPT_CONSUMED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
SIMULATOR_LANE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

# Real historical access is implemented but only reachable through the explicit
# R26P1 authorization token. CI/import/contract validation never calls it.
REAL_JAN_JUL_SOURCE_REHASH_WITH_TOKEN_AUTHORIZED = True
REAL_JAN_JUL_SOURCE_OPEN_WITH_TOKEN_AUTHORIZED = True
REAL_R20_CONTEXT_BUILD_WITH_TOKEN_AUTHORIZED = True
REAL_DURABLE_CONTEXT_WRITE_WITH_TOKEN_AUTHORIZED = True

CI_OPENS_HISTORICAL_SOURCE = False
CI_REHASHES_HISTORICAL_SOURCE = False
CI_BUILDS_REAL_CONTEXT = False
CI_RUNS_SIMULATOR = False


class R26P1MaterializationError(RuntimeError):
    pass


@dataclass(frozen=True)
class DayBundleRecord:
    day: str
    source_sha256: str
    bundle_dir: str
    day_manifest_sha256: str
    disposition: str


@dataclass(frozen=True)
class MaterializationSummary:
    status: str
    verified_source_count: int
    completed_bundle_count: int
    built_day_count: int
    reused_day_count: int
    completion_manifest_path: str
    completion_manifest_sha256: str
    p2_attempt_consumed: bool


def require_authorization(value: str | None) -> None:
    if value != AUTH_TOKEN:
        raise R26P1MaterializationError("authorization_denied")


def _sha256_file(path: Path) -> str:
    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise R26P1MaterializationError(f"file_identity:{target}")

    digest = hashlib.sha256()
    with target.open("rb", buffering=0) as handle:
        while True:
            chunk = handle.read(HASH_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _source_identity_from_verified(
    source: r4.VerifiedSource,
) -> r25.DurableSourceIdentity:
    expected = r26p0.source_identity(source.day)
    observed = r25.DurableSourceIdentity(
        day=source.day,
        path=source.path,
        rows=int(source.rows),
        bytes=int(source.bytes),
        sha256=source.sha256,
    )
    if observed != expected:
        raise R26P1MaterializationError(
            f"verified_source_identity:{source.day}"
        )
    return observed


def verify_all_sources_serial_real() -> tuple[r4.VerifiedSource, ...]:
    """
    Reverify all seven exact source identities serially before any R20 build.
    This function performs real Jan-Jul file I/O and requires R26P1 authorization
    from its caller.
    """
    observed: list[r4.VerifiedSource] = []
    for expected in r2.FROZEN_SOURCE_REGISTRY:
        print(
            f"R26P1_SOURCE_VERIFY_BEGIN={expected.day}",
            flush=True,
        )
        source = r8a.verify_source_impl(expected)
        _source_identity_from_verified(source)
        observed.append(source)
        print(
            "R26P1_SOURCE_VERIFY_PASS="
            f"{source.day} ROWS={source.rows} BYTES={source.bytes} "
            f"SHA256={source.sha256}",
            flush=True,
        )

    if tuple(item.day for item in observed) != r26p0.EXPECTED_DAYS:
        raise R26P1MaterializationError("verified_day_order")
    if len(observed) != 7:
        raise R26P1MaterializationError("verified_source_count")
    return tuple(observed)


def _validate_memory_growth(
    *,
    baseline: r22.MemorySnapshot,
    observed: r22.MemorySnapshot,
    stage: str,
) -> None:
    if (
        observed.mem_available_bytes
        < r26p0.RUNTIME_MEMAVAILABLE_ABORT_BYTES
    ):
        raise R26P1MaterializationError(
            f"runtime_memavailable:{stage}:{observed.mem_available_bytes}"
        )

    if (
        r26p0.PROCESS_SWAP_GROWTH_FORBIDDEN
        and observed.vm_swap_bytes > baseline.vm_swap_bytes
    ):
        raise R26P1MaterializationError(
            f"process_swap_growth:{stage}:"
            f"{baseline.vm_swap_bytes}:{observed.vm_swap_bytes}"
        )

    anonymous_growth = (
        observed.rss_anon_bytes - baseline.rss_anon_bytes
    )
    if anonymous_growth > r22.ANON_GROWTH_ABORT_THRESHOLD_BYTES:
        raise R26P1MaterializationError(
            f"anonymous_growth:{stage}:{anonymous_growth}"
        )


def _verify_completed_bundle(
    source: r4.VerifiedSource,
    *,
    disposition: str,
) -> DayBundleRecord:
    identity = _source_identity_from_verified(source)
    bundle_dir = r26p0.durable_day_dir(source.day)

    context = r25.open_verified_day_context(
        bundle_dir=bundle_dir,
        expected_source_identity=identity,
    )
    try:
        day_start, day_end = r22.utc_day_bounds_ns(source.day)
        if (
            context.bounds.nominal_day_start_local_ns
            != day_start
        ):
            raise R26P1MaterializationError(
                f"bundle_day_start:{source.day}"
            )
        if (
            context.bounds.nominal_day_end_exclusive_local_ns
            != day_end
        ):
            raise R26P1MaterializationError(
                f"bundle_day_end:{source.day}"
            )
    finally:
        r25.close_reopened_day_context(context)

    day_manifest = bundle_dir / r25.MANIFEST_NAME
    return DayBundleRecord(
        day=source.day,
        source_sha256=source.sha256,
        bundle_dir=str(bundle_dir),
        day_manifest_sha256=_sha256_file(day_manifest),
        disposition=disposition,
    )


def classify_completed_bundles(
    verified_sources: Sequence[r4.VerifiedSource],
) -> tuple[tuple[DayBundleRecord, ...], tuple[r4.VerifiedSource, ...]]:
    """
    Verify completed day bundles before reuse. Missing final day directories are
    pending. Any existing but incomplete/corrupt final directory fails closed.
    """
    completed: list[DayBundleRecord] = []
    pending: list[r4.VerifiedSource] = []

    for source in verified_sources:
        final_dir = r26p0.durable_day_dir(source.day)

        if os.path.lexists(final_dir):
            if final_dir.is_symlink() or not final_dir.is_dir():
                raise R26P1MaterializationError(
                    f"invalid_completed_bundle_path:{source.day}"
                )
            completed.append(
                _verify_completed_bundle(
                    source,
                    disposition="REUSED_VERIFIED",
                )
            )
        else:
            pending.append(source)

    return tuple(completed), tuple(pending)


def _remove_successful_build_scratch(build_dir: Path) -> None:
    root = Path(build_dir)
    if not root.exists():
        return
    entries = tuple(root.iterdir())
    if entries:
        raise R26P1MaterializationError(
            f"successful_build_scratch_not_empty:{root}"
        )
    root.rmdir()


def _build_one_verified_source_real(
    source: r4.VerifiedSource,
) -> DayBundleRecord:
    """
    Build exactly one already-verified frozen source into an R25 durable bundle.
    Never retries. On ordinary failure or host interruption, residue is left for
    forensics and is never accepted as a completed bundle.
    """
    identity = _source_identity_from_verified(source)
    final_dir = r26p0.durable_day_dir(source.day)

    if os.path.lexists(final_dir):
        raise R26P1MaterializationError(
            f"worker_final_bundle_exists:{source.day}"
        )

    initial = r22.read_memory_snapshot()
    if (
        initial.mem_available_bytes
        < r26p0.MIN_MEMAVAILABLE_ONE_WORKER_BYTES
    ):
        raise R26P1MaterializationError(
            f"worker_admission_memavailable:{source.day}:"
            f"{initial.mem_available_bytes}"
        )

    build_root = r26p0.DURABLE_ROOT / BUILD_ROOT_NAME
    build_root.mkdir(parents=True, exist_ok=True)

    build_dir = build_root / (
        f"{source.day}.{os.getpid()}.{uuid.uuid4().hex}"
    )
    build_dir.mkdir(mode=0o700)

    source_handle = None
    context = None
    durable_verified = False

    print(
        f"R26P1_DAY_BUILD_BEGIN={source.day} BUILD_DIR={build_dir}",
        flush=True,
    )

    try:
        source_handle = r8a.open_day_source_impl(source)
        r8a.validate_engine_input_impl(source_handle)

        _validate_memory_growth(
            baseline=initial,
            observed=r22.read_memory_snapshot(),
            stage=f"{source.day}:after_source_validation",
        )

        day_start, day_end = r22.utc_day_bounds_ns(source.day)

        context = r20.build_once_day_context(
            source_handle.events,
            nominal_day_start_local_ns=day_start,
            nominal_day_end_exclusive_local_ns=day_end,
            scratch_root=build_dir,
        )

        if (
            int(context.bounds.nominal_day_start_local_ns)
            != int(day_start)
            or int(context.bounds.nominal_day_end_exclusive_local_ns)
            != int(day_end)
        ):
            raise R26P1MaterializationError(
                f"context_nominal_bounds:{source.day}"
            )

        _validate_memory_growth(
            baseline=initial,
            observed=r22.read_memory_snapshot(),
            stage=f"{source.day}:after_r20",
        )

        r25.persist_day_context(
            context=context,
            source_identity=identity,
            final_dir=final_dir,
        )

        record = _verify_completed_bundle(
            source,
            disposition="BUILT_VERIFIED",
        )
        durable_verified = True

        _validate_memory_growth(
            baseline=initial,
            observed=r22.read_memory_snapshot(),
            stage=f"{source.day}:after_durable_verify",
        )

        print(
            f"R26P1_DAY_BUILD_PASS={source.day} "
            f"MANIFEST_SHA256={record.day_manifest_sha256}",
            flush=True,
        )

        return record

    except Exception as exc:
        print(
            f"R26P1_DAY_BUILD_FAIL={source.day} "
            f"{type(exc).__name__}:{exc} BUILD_DIR={build_dir}",
            flush=True,
        )
        raise

    finally:
        if context is not None and not context.midpoint_index.closed:
            # Preserve completed R20 scratch on failure; remove only after the
            # durable copy has reopened and verified successfully.
            r20.close_midpoint_index(
                context.midpoint_index,
                delete=durable_verified,
            )

        if source_handle is not None and not source_handle.closed:
            r8a.close_day_source_impl(source_handle)

        if durable_verified:
            _remove_successful_build_scratch(build_dir)


def _completion_payload(
    records: Sequence[DayBundleRecord],
) -> dict[str, object]:
    ordered = tuple(sorted(records, key=lambda item: item.day))
    if tuple(item.day for item in ordered) != r26p0.EXPECTED_DAYS:
        raise R26P1MaterializationError("completion_day_identity")

    return {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "status": "ALL_SEVEN_DURABLE_CONTEXTS_VERIFIED",
        "parent_r26p0_head": PARENT_R26P0_HEAD,
        "source_registry_sha256": r2.FROZEN_SOURCE_REGISTRY_SHA256,
        "days": [
            {
                "day": item.day,
                "source_sha256": item.source_sha256,
                "bundle_dir": item.bundle_dir,
                "day_manifest_sha256": item.day_manifest_sha256,
            }
            for item in ordered
        ],
        "verified_bundle_count": len(ordered),
        "p2_attempt_consumed": False,
        "simulator_run": False,
        "canonical_labels_written": False,
        "model_fit": False,
        "pnl": False,
    }


def _canonical_json_bytes(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        + b"\n"
    )


def _write_completion_manifest_once(
    records: Sequence[DayBundleRecord],
) -> str:
    payload = _completion_payload(records)
    encoded = _canonical_json_bytes(payload)
    digest = hashlib.sha256(encoded).hexdigest()

    r26p0.DURABLE_ROOT.mkdir(parents=True, exist_ok=True)
    target = COMPLETION_MANIFEST_PATH

    if target.exists():
        if target.is_symlink() or not target.is_file():
            raise R26P1MaterializationError(
                "completion_manifest_path"
            )
        existing = target.read_bytes()
        if existing != encoded:
            raise R26P1MaterializationError(
                "completion_manifest_mismatch"
            )
        return digest

    temp = target.with_name(
        f".{target.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}"
    )
    with temp.open("xb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temp, target)

    dir_fd = os.open(
        target.parent,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)

    if _sha256_file(target) != digest:
        raise R26P1MaterializationError(
            "completion_manifest_postwrite_sha"
        )

    return digest


def _run_build_batch(
    sources: Sequence[r4.VerifiedSource],
) -> tuple[DayBundleRecord, ...]:
    if not sources:
        return ()

    snapshot = r22.read_memory_snapshot()
    admitted = r26p0.admitted_worker_limit(
        snapshot.mem_available_bytes
    )
    worker_count = min(
        int(admitted),
        int(WORKER_CAP),
        len(sources),
    )

    if worker_count <= 0:
        raise R26P1MaterializationError(
            f"materialization_admission_denied:"
            f"{snapshot.mem_available_bytes}"
        )

    batch = tuple(sources[:worker_count])

    print(
        f"R26P1_BATCH_BEGIN="
        f"{','.join(item.day for item in batch)} "
        f"WORKERS={worker_count} "
        f"MEMAVAILABLE={snapshot.mem_available_bytes}",
        flush=True,
    )

    results: list[DayBundleRecord] = []
    failures: list[str] = []

    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(
                _build_one_verified_source_real,
                source,
            ): source
            for source in batch
        }

        for future in as_completed(future_map):
            source = future_map[future]
            try:
                results.append(future.result())
            except Exception as exc:
                failures.append(
                    f"{source.day}:{type(exc).__name__}:{exc}"
                )

    if failures:
        raise R26P1MaterializationError(
            "batch_failure:" + "|".join(sorted(failures))
        )

    return tuple(sorted(results, key=lambda item: item.day))


def run_real_materialization(
    *,
    authorization_value: str | None,
) -> MaterializationSummary:
    """
    Real Jan-Jul durable context materialization only. This remains entirely
    before the P2 simulator-attempt boundary.
    """
    validate_r26p1_contract()
    require_authorization(authorization_value)

    if r3.ATTEMPT_MARKER_PATH.exists():
        raise R26P1MaterializationError(
            "p2_attempt_already_consumed"
        )
    if r3.FAILURE_ARTIFACT_PATH.exists():
        raise R26P1MaterializationError(
            "canonical_failure_artifact_exists"
        )
    if r3.FINAL_MANIFEST_PATH.exists():
        raise R26P1MaterializationError(
            "canonical_manifest_exists"
        )

    verified = verify_all_sources_serial_real()

    reused, pending = classify_completed_bundles(verified)
    records: dict[str, DayBundleRecord] = {
        item.day: item for item in reused
    }

    remaining = list(pending)

    while remaining:
        snapshot = r22.read_memory_snapshot()
        admitted = r26p0.admitted_worker_limit(
            snapshot.mem_available_bytes
        )
        if admitted <= 0:
            raise R26P1MaterializationError(
                f"parent_admission_denied:"
                f"{snapshot.mem_available_bytes}"
            )

        batch_size = min(
            int(admitted),
            int(WORKER_CAP),
            len(remaining),
        )

        current = tuple(remaining[:batch_size])
        built = _run_build_batch(current)

        for item in built:
            records[item.day] = item

        remaining = remaining[batch_size:]

    final_records = tuple(
        _verify_completed_bundle(
            source,
            disposition=(
                records[source.day].disposition
                if source.day in records
                else "FINAL_VERIFIED"
            ),
        )
        for source in verified
    )

    if len(final_records) != 7:
        raise R26P1MaterializationError(
            "final_bundle_count"
        )

    completion_sha = _write_completion_manifest_once(
        final_records
    )

    return MaterializationSummary(
        status="ALL_SEVEN_DURABLE_CONTEXTS_VERIFIED",
        verified_source_count=len(verified),
        completed_bundle_count=len(final_records),
        built_day_count=sum(
            item.disposition == "BUILT_VERIFIED"
            for item in final_records
        ),
        reused_day_count=sum(
            item.disposition == "REUSED_VERIFIED"
            for item in final_records
        ),
        completion_manifest_path=str(
            COMPLETION_MANIFEST_PATH
        ),
        completion_manifest_sha256=completion_sha,
        p2_attempt_consumed=False,
    )


def validate_r26p1_contract() -> None:
    r26p0.validate_r26p0_contract()
    r25.validate_r25_contract()
    r22.validate_r22_contract()

    if PARENT_R26P0_HEAD != (
        "2ec9be95b200437465388a46e04921ccea47ab1e"
    ):
        raise R26P1MaterializationError("parent")

    if WORKER_CAP != 2:
        raise R26P1MaterializationError("worker_cap")

    if WORKER_CAP > r26p0.R24_MAX_PARALLEL_CAP:
        raise R26P1MaterializationError(
            "r24_worker_cap"
        )

    if COMPLETION_MANIFEST_PATH.parent != r26p0.DURABLE_ROOT:
        raise R26P1MaterializationError(
            "completion_manifest_root"
        )

    required = (
        REAL_DURABLE_MATERIALIZER_IMPLEMENTED,
        SERIAL_ALL_SEVEN_SOURCE_REVERIFY_IMPLEMENTED,
        R8A_READ_ONLY_SOURCE_OPEN_BOUND,
        R8A_FULL_ENGINE_INPUT_VALIDATION_BOUND,
        R20_ONCE_DAY_CONTEXT_BUILDER_BOUND,
        R25_DURABLE_PERSISTENCE_BOUND,
        R25_REOPEN_VERIFICATION_BOUND,
        R22_UTC_DAY_BOUNDS_BOUND,
        PROCESS_WORKER_PARALLELISM_IMPLEMENTED,
        DYNAMIC_MEMORY_ADMISSION_IMPLEMENTED,
        ACTIVE_BATCH_MAY_FINISH_AFTER_PEER_FAILURE,
        NO_NEW_ADMISSION_AFTER_FIRST_FAILURE,
        NO_AUTOMATIC_DAY_RETRY,
        COMPLETED_BUNDLE_REUSE_IMPLEMENTED,
        INVALID_COMPLETED_BUNDLE_FAILS_CLOSED,
        PREEXISTING_PARTIAL_BUILD_REUSE_FORBIDDEN,
        PREEXISTING_PARTIAL_BUILD_AUTO_DELETE_FORBIDDEN,
        FAILED_BUILD_RESIDUE_PRESERVED,
        SUCCESSFUL_SCRATCH_DELETE_AFTER_DURABLE_VERIFY,
        REAL_JAN_JUL_SOURCE_REHASH_WITH_TOKEN_AUTHORIZED,
        REAL_JAN_JUL_SOURCE_OPEN_WITH_TOKEN_AUTHORIZED,
        REAL_R20_CONTEXT_BUILD_WITH_TOKEN_AUTHORIZED,
        REAL_DURABLE_CONTEXT_WRITE_WITH_TOKEN_AUTHORIZED,
    )
    if not all(required):
        raise R26P1MaterializationError("required_guard")

    forbidden = (
        P2_ATTEMPT_CONSUMED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        SIMULATOR_LANE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        CI_OPENS_HISTORICAL_SOURCE,
        CI_REHASHES_HISTORICAL_SOURCE,
        CI_BUILDS_REAL_CONTEXT,
        CI_RUNS_SIMULATOR,
    )
    if any(forbidden):
        raise R26P1MaterializationError(
            "forbidden_surface_open"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)

    result = run_real_materialization(
        authorization_value=os.environ.get(
            AUTH_ENV_NAME
        )
    )

    print(f"STATUS={result.status}")
    print(
        f"VERIFIED_SOURCE_COUNT="
        f"{result.verified_source_count}"
    )
    print(
        f"COMPLETED_BUNDLE_COUNT="
        f"{result.completed_bundle_count}"
    )
    print(
        f"BUILT_DAY_COUNT={result.built_day_count}"
    )
    print(
        f"REUSED_DAY_COUNT={result.reused_day_count}"
    )
    print(
        f"COMPLETION_MANIFEST="
        f"{result.completion_manifest_path}"
    )
    print(
        f"COMPLETION_MANIFEST_SHA256="
        f"{result.completion_manifest_sha256}"
    )
    print("P2_ATTEMPT_CONSUMED=NO")
    print("SIMULATOR_RUN=NO")
    print("CANONICAL_LABELS_WRITTEN=NO")
    print("MODEL_FIT=NO")
    print("PNL=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DayBundleRecord",
    "MaterializationSummary",
    "require_authorization",
    "verify_all_sources_serial_real",
    "classify_completed_bundles",
    "run_real_materialization",
    "validate_r26p1_contract",
]

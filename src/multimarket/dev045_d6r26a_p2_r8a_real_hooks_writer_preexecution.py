from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib
import json
import os
from pathlib import Path
from typing import Mapping

import numpy as np

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p2_r1_canonical_label_materializer_preauth as r1
from multimarket import dev045_d6r26a_p2_r2_frozen_source_registry as r2
from multimarket import dev045_d6r26a_p2_r3_execution_authorization_contract as r3
from multimarket import dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4
from multimarket import dev045_d6r26a_p2_r5_real_engine_binding_prehistorical as r5
from multimarket import dev045_d6r26a_p2_r6_historical_source_identity_preflight as r6
from multimarket import dev045_d6r26a_p2_r7_canonical_historical_binding_preexecution as r7
from multimarket import dev045_m4_adapter as m4


EXPERIMENT_ID = "DEV045-D6R26A-P2-R8A"
DESIGN_VERSION = "real-historical-hooks-writer-preexecution-v1"
PARENT_R7_HEAD = "a167f39dd6bf50e43d8f2bc67feab0a60729248a"
DATA_ROLE = "CONSUMED_DEVELOPMENT"
SOURCE_REGISTRY_SHA256 = r2.FROZEN_SOURCE_REGISTRY_SHA256

CANONICAL_OUTPUT_ROOT = Path(r1.OUTPUT_ROOT)
ATTEMPT_MARKER_RELPATH = (
    r3.ATTEMPT_MARKER_PATH.relative_to(r3.OUTPUT_ROOT).as_posix()
)
FAILURE_ARTIFACT_RELPATH = (
    r3.FAILURE_ARTIFACT_PATH.relative_to(r3.OUTPUT_ROOT).as_posix()
)
FINAL_MANIFEST_RELPATH = (
    r3.FINAL_MANIFEST_PATH.relative_to(r3.OUTPUT_ROOT).as_posix()
)

REAL_SOURCE_VERIFIER_IMPLEMENTED = True
READ_ONLY_MMAP_OPEN_IMPLEMENTED = True
REAL_ENGINE_FACTORY_IMPLEMENTED = True
ATOMIC_WRITER_IMPLEMENTED = True
SEALED_RUNNER_HOOKS_IMPLEMENTED = True

# The feature/label lane executor is intentionally NOT frozen in R8A.
FEATURE_LABEL_EXECUTOR_FROZEN = False

PREEXECUTION_ONLY = True
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

PARQUET_MAGIC = b"PAR1"


class RealHooksPreexecutionError(RuntimeError):
    pass


@dataclass
class DaySourceHandle:
    source: r4.VerifiedSource
    events: np.ndarray
    closed: bool = False
    engine_input_validated: bool = False
    engine_identity_verified: bool = False


@dataclass(frozen=True)
class LaneEngineHandle:
    hftbacktest_module: object
    backtest: object


def _sha256_file(
    path: Path,
    *,
    chunk_bytes: int = r6.HASH_CHUNK_BYTES,
) -> str:
    if int(chunk_bytes) <= 0:
        raise RealHooksPreexecutionError("hash_chunk_bytes")

    digest = hashlib.sha256()
    buf = bytearray(int(chunk_bytes))
    view = memoryview(buf)

    with Path(path).open("rb", buffering=0) as handle:
        while True:
            n = handle.readinto(buf)
            if not n:
                break
            digest.update(view[:n])

    return digest.hexdigest()


def verify_source_impl(
    expected: r2.FrozenSourceRecord,
) -> r4.VerifiedSource:
    """
    Exact real-source verifier implementation.

    It is implemented here for the later execution binding but is NOT wired
    into the R4 runner by R8A.
    """
    observed = r6.verify_source_file(expected)

    return r4.VerifiedSource(
        day=observed.day,
        path=observed.path,
        rows=observed.rows,
        bytes=observed.bytes,
        sha256=observed.sha256,
    )


def _expected_frozen_source(
    source: r4.VerifiedSource,
) -> r2.FrozenSourceRecord:
    matches = [
        item
        for item in r2.FROZEN_SOURCE_REGISTRY
        if item.day == source.day
    ]

    if len(matches) != 1:
        raise RealHooksPreexecutionError(
            f"source_day_not_frozen:{source.day}"
        )

    expected = matches[0]

    observed_identity = (
        source.day,
        source.path,
        int(source.rows),
        int(source.bytes),
        source.sha256,
    )
    frozen_identity = (
        expected.day,
        expected.path,
        int(expected.rows),
        int(expected.bytes),
        expected.sha256,
    )

    if observed_identity != frozen_identity:
        raise RealHooksPreexecutionError(
            f"source_identity_not_frozen:{source.day}"
        )

    return expected


def _open_npy_memmap(
    path: Path,
    *,
    expected_rows: int,
    expected_bytes: int,
    expected_itemsize: int = r6.CANONICAL_EVENT_ITEMSIZE,
) -> np.ndarray:
    """
    Shared bounded-memory read-only NPY opener.

    R8A CI exercises this only on a temporary synthetic NPY probe.
    """
    path = Path(path)

    if not path.is_file():
        raise RealHooksPreexecutionError(f"source_missing:{path}")

    if path.suffix != ".npy":
        raise RealHooksPreexecutionError(
            f"source_suffix:{path.suffix}"
        )

    observed_bytes = int(path.stat().st_size)

    if observed_bytes != int(expected_bytes):
        raise RealHooksPreexecutionError(
            f"source_bytes:{observed_bytes}:{expected_bytes}"
        )

    arr = np.load(
        path,
        mmap_mode="r",
        allow_pickle=False,
    )

    try:
        if int(arr.ndim) != 1:
            raise RealHooksPreexecutionError(
                f"source_ndim:{arr.ndim}"
            )

        if int(arr.shape[0]) != int(expected_rows):
            raise RealHooksPreexecutionError(
                f"source_rows:{arr.shape[0]}:{expected_rows}"
            )

        if int(arr.dtype.itemsize) != int(expected_itemsize):
            raise RealHooksPreexecutionError(
                f"source_itemsize:{arr.dtype.itemsize}:{expected_itemsize}"
            )

        if bool(arr.flags.writeable):
            raise RealHooksPreexecutionError(
                "source_not_read_only"
            )

        return arr

    except Exception:
        mm = getattr(arr, "_mmap", None)
        if mm is not None:
            mm.close()
        raise


def open_day_source_impl(
    source: r4.VerifiedSource,
) -> DaySourceHandle:
    """
    Real frozen-source read-only mmap implementation.

    Caller must have already executed verify_source_impl.
    R8A itself never calls this on Jan-Jul.
    """
    _expected_frozen_source(source)

    events = _open_npy_memmap(
        Path(source.path),
        expected_rows=source.rows,
        expected_bytes=source.bytes,
    )

    return DaySourceHandle(
        source=source,
        events=events,
    )


def close_day_source_impl(
    handle: DaySourceHandle,
) -> None:
    if handle.closed:
        raise RealHooksPreexecutionError(
            "source_already_closed"
        )

    mm = getattr(handle.events, "_mmap", None)

    if mm is not None:
        mm.close()

    handle.closed = True


def validate_engine_input_impl(
    handle: DaySourceHandle,
) -> None:
    """
    Validate the full source at most once per opened day.

    It must NOT be repeated once per one of the 40 lanes.
    """
    if handle.closed:
        raise RealHooksPreexecutionError("source_closed")

    _expected_frozen_source(handle.source)

    if not handle.engine_input_validated:
        m4.validate_events(handle.events)
        handle.engine_input_validated = True


def new_engine_impl(
    handle: DaySourceHandle,
) -> LaneEngineHandle:
    """
    Lazy real hftbacktest 2.4.4 factory.

    No import happens at module import time. R8A's sealed RunnerHooks never
    call this function. A later frozen execution surface may bind it.
    """
    if handle.closed:
        raise RealHooksPreexecutionError("source_closed")

    _expected_frozen_source(handle.source)

    if not handle.engine_identity_verified:
        r5.verify_engine_identity()
        handle.engine_identity_verified = True

    validate_engine_input_impl(handle)

    hft = importlib.import_module("hftbacktest")

    asset = m4.build_asset(
        handle.events,
        queue_model="risk_adverse",
        entry_latency_ns=p0.ENTRY_LATENCY_NS,
        response_latency_ns=p0.RESPONSE_LATENCY_NS,
        maker_fee=0.0,
        taker_fee=0.0,
    )

    backtest = hft.HashMapMarketDepthBacktest(
        [asset]
    )

    return LaneEngineHandle(
        hftbacktest_module=hft,
        backtest=backtest,
    )


def close_engine_impl(
    engine: LaneEngineHandle,
) -> None:
    rc = int(engine.backtest.close())

    if rc != 0:
        raise RealHooksPreexecutionError(
            f"bt_close_rc:{rc}"
        )


def canonical_json_bytes(
    payload: Mapping[str, object],
) -> bytes:
    return (
        json.dumps(
            dict(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        + b"\n"
    )


def _safe_relpath(
    relpath: str,
) -> tuple[str, ...]:
    raw = str(relpath)

    if (
        not raw
        or raw.startswith("/")
        or "\\" in raw
    ):
        raise RealHooksPreexecutionError(
            "unsafe_relpath"
        )

    parts = tuple(raw.split("/"))

    if any(
        part in ("", ".", "..")
        for part in parts
    ):
        raise RealHooksPreexecutionError(
            "unsafe_relpath"
        )

    return parts


def _fsync_directory(
    path: Path,
) -> None:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
    )

    fd = os.open(
        Path(path),
        flags,
    )

    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write_once(
    *,
    root: Path,
    relpath: str,
    payload: bytes,
) -> tuple[int, str]:
    """
    Frozen publish primitive:

    WRITE_TEMP_FSYNC_HASH_VERIFY_ATOMIC_RENAME_ONCE.
    """
    if not isinstance(payload, bytes):
        raise RealHooksPreexecutionError(
            "payload_not_bytes"
        )

    parts = _safe_relpath(relpath)
    root = Path(root)

    root.mkdir(
        parents=True,
        exist_ok=True,
    )

    final = root.joinpath(*parts)

    final.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = final.with_name(
        final.name + ".tmp"
    )

    if final.exists():
        raise RealHooksPreexecutionError(
            f"artifact_already_exists:{relpath}"
        )

    if temp.exists():
        raise RealHooksPreexecutionError(
            f"temp_artifact_exists:{relpath}"
        )

    expected_bytes = len(payload)
    expected_sha256 = hashlib.sha256(
        payload
    ).hexdigest()

    with temp.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

    if int(temp.stat().st_size) != expected_bytes:
        raise RealHooksPreexecutionError(
            f"temp_bytes:{relpath}"
        )

    if _sha256_file(temp) != expected_sha256:
        raise RealHooksPreexecutionError(
            f"temp_sha256:{relpath}"
        )

    os.replace(
        temp,
        final,
    )

    _fsync_directory(
        final.parent
    )

    if int(final.stat().st_size) != expected_bytes:
        raise RealHooksPreexecutionError(
            f"final_bytes:{relpath}"
        )

    observed_sha256 = _sha256_file(
        final
    )

    if observed_sha256 != expected_sha256:
        raise RealHooksPreexecutionError(
            f"final_sha256:{relpath}"
        )

    return (
        expected_bytes,
        observed_sha256,
    )


def write_partition_bytes_impl(
    *,
    root: Path,
    lane: r1.LaneSpec,
    payload: bytes,
    row_count: int,
) -> r4.LaneArtifact:
    """
    Atomic publisher for already-produced Parquet bytes.

    R8A implements it but does not bind or authorize it.
    """
    if (
        isinstance(row_count, bool)
        or int(row_count) < 0
    ):
        raise RealHooksPreexecutionError(
            "row_count"
        )

    expected_relpath = r1.partition_relpath(
        lane.day,
        lane.side,
        lane.distance_ticks,
        lane.phase,
    )

    if lane.partition_relpath != expected_relpath:
        raise RealHooksPreexecutionError(
            "lane_partition_relpath"
        )

    if (
        len(payload) < 8
        or payload[:4] != PARQUET_MAGIC
        or payload[-4:] != PARQUET_MAGIC
    ):
        raise RealHooksPreexecutionError(
            "parquet_magic"
        )

    size, digest = atomic_write_once(
        root=Path(root),
        relpath=lane.partition_relpath,
        payload=payload,
    )

    return r4.LaneArtifact(
        lane_id=lane.lane_id,
        relpath=lane.partition_relpath,
        bytes=size,
        sha256=digest,
        row_count=int(row_count),
    )


def verify_partition_impl(
    *,
    root: Path,
    artifact: r4.LaneArtifact,
) -> None:
    parts = _safe_relpath(
        artifact.relpath
    )

    path = Path(root).joinpath(
        *parts
    )

    if not path.is_file():
        raise RealHooksPreexecutionError(
            f"partition_missing:{artifact.lane_id}"
        )

    if int(path.stat().st_size) != int(artifact.bytes):
        raise RealHooksPreexecutionError(
            f"partition_bytes:{artifact.lane_id}"
        )

    observed_sha256 = _sha256_file(
        path
    )

    if observed_sha256 != artifact.sha256:
        raise RealHooksPreexecutionError(
            f"partition_sha256:{artifact.lane_id}"
        )


def write_control_json_impl(
    *,
    root: Path,
    relpath: str,
    payload: Mapping[str, object],
) -> tuple[int, str]:
    """
    Generic atomic control-artifact primitive.

    It remains unbound in R8A, including the attempt marker.
    """
    if relpath not in {
        ATTEMPT_MARKER_RELPATH,
        FAILURE_ARTIFACT_RELPATH,
        FINAL_MANIFEST_RELPATH,
    }:
        raise RealHooksPreexecutionError(
            "control_relpath"
        )

    return atomic_write_once(
        root=Path(root),
        relpath=relpath,
        payload=canonical_json_bytes(payload),
    )


def _sealed(
    name: str,
):
    def _raise(*args, **kwargs):
        del args, kwargs
        raise RealHooksPreexecutionError(
            f"execution_surface_sealed:{name}"
        )

    return _raise


def _feature_label_executor_not_frozen(
    *args,
    **kwargs,
):
    del args, kwargs

    raise RealHooksPreexecutionError(
        "FEATURE_LABEL_EXECUTOR_NOT_FROZEN"
    )


def build_sealed_runner_hooks(
    *,
    output_root: Path = CANONICAL_OUTPUT_ROOT,
) -> r4.RunnerHooks:
    """
    R4-compatible shape that provably cannot execute R8A.

    Even a valid frozen R3 authorization token cannot reach the attempt-marker
    write because verify_source remains sealed.
    """
    root = Path(output_root)

    return r4.RunnerHooks(
        attempt_marker_exists=lambda: (
            root.joinpath(
                *_safe_relpath(
                    ATTEMPT_MARKER_RELPATH
                )
            ).exists()
        ),
        verify_source=_sealed(
            "verify_source"
        ),
        write_attempt_marker=_sealed(
            "write_attempt_marker"
        ),
        open_day_source=_sealed(
            "open_day_source"
        ),
        run_lane=(
            _feature_label_executor_not_frozen
        ),
        close_day_source=_sealed(
            "close_day_source"
        ),
        verify_partition=_sealed(
            "verify_partition"
        ),
        write_failure_artifact=_sealed(
            "write_failure_artifact"
        ),
        write_final_manifest=_sealed(
            "write_final_manifest"
        ),
    )


def validate_r8a_contract() -> None:
    r7.validate_r7_contract()

    if (
        PARENT_R7_HEAD
        != "a167f39dd6bf50e43d8f2bc67feab0a60729248a"
    ):
        raise RealHooksPreexecutionError(
            "parent"
        )

    if (
        DATA_ROLE != r7.DATA_ROLE
        or DATA_ROLE != "CONSUMED_DEVELOPMENT"
    ):
        raise RealHooksPreexecutionError(
            "data_role"
        )

    if (
        SOURCE_REGISTRY_SHA256
        != r7.SOURCE_REGISTRY_SHA256
    ):
        raise RealHooksPreexecutionError(
            "registry_sha256"
        )

    if CANONICAL_OUTPUT_ROOT != r3.OUTPUT_ROOT:
        raise RealHooksPreexecutionError(
            "output_root"
        )

    expected_relpaths = (
        "DEV045_D6R26A_P2_ATTEMPT_CONSUMED.json",
        "DEV045_D6R26A_P2_FAILURE.json",
        "DEV045_D6R26A_P2_CANONICAL_MANIFEST.json",
    )

    observed_relpaths = (
        ATTEMPT_MARKER_RELPATH,
        FAILURE_ARTIFACT_RELPATH,
        FINAL_MANIFEST_RELPATH,
    )

    if observed_relpaths != expected_relpaths:
        raise RealHooksPreexecutionError(
            "control_relpaths"
        )

    implemented = (
        REAL_SOURCE_VERIFIER_IMPLEMENTED,
        READ_ONLY_MMAP_OPEN_IMPLEMENTED,
        REAL_ENGINE_FACTORY_IMPLEMENTED,
        ATOMIC_WRITER_IMPLEMENTED,
        SEALED_RUNNER_HOOKS_IMPLEMENTED,
        PREEXECUTION_ONLY,
    )

    if not all(implemented):
        raise RealHooksPreexecutionError(
            "implementation_surface"
        )

    if FEATURE_LABEL_EXECUTOR_FROZEN:
        raise RealHooksPreexecutionError(
            "feature_executor_prematurely_frozen"
        )

    forbidden = (
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
        raise RealHooksPreexecutionError(
            "execution_surface_open"
        )


__all__ = [
    "DaySourceHandle",
    "LaneEngineHandle",
    "verify_source_impl",
    "open_day_source_impl",
    "close_day_source_impl",
    "validate_engine_input_impl",
    "new_engine_impl",
    "close_engine_impl",
    "canonical_json_bytes",
    "atomic_write_once",
    "write_partition_bytes_impl",
    "verify_partition_impl",
    "write_control_json_impl",
    "build_sealed_runner_hooks",
    "validate_r8a_contract",
]

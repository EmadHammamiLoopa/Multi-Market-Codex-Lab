from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

import numpy as np

from multimarket import dev045_d6r26a_p2_r2_frozen_source_registry as r2
from multimarket import dev045_d6r26a_p2_r5_real_engine_binding_prehistorical as r5


EXPERIMENT_ID = "DEV045-D6R26A-P2-R6"
DESIGN_VERSION = "historical-source-identity-preflight-v1"
PARENT_P2_R5_HEAD = "0524ebd92b6f600d9b1a844c707076f11e4a54f6"
DATA_ROLE = "CONSUMED_DEVELOPMENT"
SOURCE_REGISTRY_SHA256 = r2.FROZEN_SOURCE_REGISTRY_SHA256

AUTH_ENV_NAME = "DEV045_D6R26A_P2_R6_AUTHORIZE"
AUTH_TOKEN = "YES_FROZEN_JAN_JUL_SOURCE_IDENTITY_PREFLIGHT_ONLY"

HISTORICAL_FILE_IO_AUTHORIZED = True
HISTORICAL_SOURCE_OPEN_AUTHORIZED = True
HISTORICAL_SOURCE_REHASH_AUTHORIZED = True
SIMULATOR_IMPORT_AUTHORIZED = False
CANDIDATE_SIMULATION_AUTHORIZED = False
CANONICAL_RUNNER_BINDING_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False

P2_ATTEMPT_CONSUMPTION_EVENT = "FIRST_CANONICAL_CANDIDATE_SIMULATION_LANE_START"
P2_ATTEMPT_CONSUMED_BY_R6 = False

HASH_CHUNK_BYTES = 64 * 1024 * 1024
CANONICAL_EVENT_ITEMSIZE = 64
CANONICAL_NPY_HEADER_BYTES = 256
RESULT_ROOT = Path("/home/emadh/Multi-Market/evidence/dev045_d6r26a_p2_r6_source_identity_preflight_v1")
RESULT_PATH = RESULT_ROOT / "DEV045_D6R26A_P2_R6_SOURCE_IDENTITY_PREFLIGHT.json"


class SourceIdentityPreflightError(RuntimeError):
    pass


@dataclass(frozen=True)
class ObservedSourceIdentity:
    day: str
    path: str
    rows: int
    bytes: int
    sha256: str
    ndim: int
    itemsize: int


@dataclass(frozen=True)
class SourceIdentityPreflightResult:
    experiment_id: str
    design_version: str
    status: str
    data_role: str
    source_registry_sha256: str
    verified_source_count: int
    sources: tuple[ObservedSourceIdentity, ...]
    historical_source_opened: bool
    simulator_imported: bool
    candidate_simulation_started: bool
    attempt_marker_written: bool
    p2_attempt_consumed: bool
    model_fit: bool
    pnl: bool
    live_trading: bool


def require_authorization(value: str | None) -> None:
    if value != AUTH_TOKEN:
        raise SourceIdentityPreflightError("authorization_denied")


def _sha256_file(path: Path, *, chunk_bytes: int = HASH_CHUNK_BYTES) -> str:
    if int(chunk_bytes) <= 0:
        raise SourceIdentityPreflightError("hash_chunk_bytes")
    h = hashlib.sha256()
    buf = bytearray(int(chunk_bytes))
    view = memoryview(buf)
    with path.open("rb", buffering=0) as f:
        while True:
            n = f.readinto(buf)
            if not n:
                break
            h.update(view[:n])
    return h.hexdigest()


def _read_npy_shape_and_itemsize(path: Path) -> tuple[int, int, int]:
    arr = np.load(path, mmap_mode="r", allow_pickle=False)
    try:
        ndim = int(arr.ndim)
        if ndim != 1:
            raise SourceIdentityPreflightError(f"npy_ndim:{path}:{ndim}")
        rows = int(arr.shape[0])
        itemsize = int(arr.dtype.itemsize)
        return rows, ndim, itemsize
    finally:
        del arr


def verify_source_file(expected: r2.FrozenSourceRecord) -> ObservedSourceIdentity:
    path = Path(expected.path)
    if not path.exists():
        raise SourceIdentityPreflightError(f"source_missing:{expected.day}:{path}")
    if not path.is_file():
        raise SourceIdentityPreflightError(f"source_not_file:{expected.day}:{path}")
    if path.suffix != ".npy":
        raise SourceIdentityPreflightError(f"source_suffix:{expected.day}:{path.suffix}")

    observed_bytes = int(path.stat().st_size)
    if observed_bytes != int(expected.bytes):
        raise SourceIdentityPreflightError(
            f"source_bytes_mismatch:{expected.day}:{observed_bytes}:{expected.bytes}"
        )

    rows, ndim, itemsize = _read_npy_shape_and_itemsize(path)
    if rows != int(expected.rows):
        raise SourceIdentityPreflightError(
            f"source_rows_mismatch:{expected.day}:{rows}:{expected.rows}"
        )
    if itemsize != CANONICAL_EVENT_ITEMSIZE:
        raise SourceIdentityPreflightError(
            f"source_itemsize_mismatch:{expected.day}:{itemsize}:{CANONICAL_EVENT_ITEMSIZE}"
        )

    observed_sha256 = _sha256_file(path)
    if observed_sha256 != expected.sha256:
        raise SourceIdentityPreflightError(
            f"source_sha256_mismatch:{expected.day}:{observed_sha256}:{expected.sha256}"
        )

    return ObservedSourceIdentity(
        day=expected.day,
        path=str(path),
        rows=rows,
        bytes=observed_bytes,
        sha256=observed_sha256,
        ndim=ndim,
        itemsize=itemsize,
    )


def run_source_identity_preflight(
    *,
    authorization_value: str | None,
    registry: Iterable[r2.FrozenSourceRecord] = r2.FROZEN_SOURCE_REGISTRY,
) -> SourceIdentityPreflightResult:
    validate_r6_contract()
    require_authorization(authorization_value)

    expected = tuple(registry)
    if expected != tuple(r2.FROZEN_SOURCE_REGISTRY):
        raise SourceIdentityPreflightError("registry_override_forbidden")

    observed: list[ObservedSourceIdentity] = []
    for source in expected:
        print(f"SOURCE_PREFLIGHT_BEGIN={source.day}", flush=True)
        item = verify_source_file(source)
        observed.append(item)
        print(
            f"SOURCE_PREFLIGHT_PASS={source.day} ROWS={item.rows} BYTES={item.bytes} SHA256={item.sha256}",
            flush=True,
        )

    if len(observed) != 7:
        raise SourceIdentityPreflightError("verified_source_count")

    return SourceIdentityPreflightResult(
        experiment_id=EXPERIMENT_ID,
        design_version=DESIGN_VERSION,
        status="SOURCE_IDENTITY_PREFLIGHT_PASS",
        data_role=DATA_ROLE,
        source_registry_sha256=SOURCE_REGISTRY_SHA256,
        verified_source_count=len(observed),
        sources=tuple(observed),
        historical_source_opened=True,
        simulator_imported=False,
        candidate_simulation_started=False,
        attempt_marker_written=False,
        p2_attempt_consumed=False,
        model_fit=False,
        pnl=False,
        live_trading=False,
    )


def canonical_result_bytes(result: SourceIdentityPreflightResult) -> bytes:
    return json.dumps(
        asdict(result),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8") + b"\n"


def write_result_once(result: SourceIdentityPreflightResult, path: Path = RESULT_PATH) -> str:
    payload = canonical_result_bytes(result)
    digest = hashlib.sha256(payload).hexdigest()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SourceIdentityPreflightError(f"result_already_exists:{path}")
    temp = path.with_name(path.name + ".tmp")
    if temp.exists():
        raise SourceIdentityPreflightError(f"temp_result_exists:{temp}")
    with temp.open("xb") as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)
    return digest


def validate_r6_contract() -> None:
    r2.validate_frozen_source_registry()
    r5.validate_r5_contract()
    if PARENT_P2_R5_HEAD != "0524ebd92b6f600d9b1a844c707076f11e4a54f6":
        raise SourceIdentityPreflightError("parent")
    if DATA_ROLE != "CONSUMED_DEVELOPMENT":
        raise SourceIdentityPreflightError("data_role")
    if SOURCE_REGISTRY_SHA256 != "97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4":
        raise SourceIdentityPreflightError("registry_sha256")
    if len(r2.FROZEN_SOURCE_REGISTRY) != 7:
        raise SourceIdentityPreflightError("source_count")
    for x in r2.FROZEN_SOURCE_REGISTRY:
        if int(x.bytes) - int(x.rows) * CANONICAL_EVENT_ITEMSIZE != CANONICAL_NPY_HEADER_BYTES:
            raise SourceIdentityPreflightError(f"npy_layout_identity:{x.day}")
    required = (
        HISTORICAL_FILE_IO_AUTHORIZED,
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_SOURCE_REHASH_AUTHORIZED,
    )
    if not all(required):
        raise SourceIdentityPreflightError("historical_preflight_surface_closed")
    forbidden = (
        SIMULATOR_IMPORT_AUTHORIZED,
        CANDIDATE_SIMULATION_AUTHORIZED,
        CANONICAL_RUNNER_BINDING_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        NETWORK_ACQUISITION_AUTHORIZED,
        P2_ATTEMPT_CONSUMED_BY_R6,
    )
    if any(forbidden):
        raise SourceIdentityPreflightError("forbidden_surface_open")
    if P2_ATTEMPT_CONSUMPTION_EVENT != "FIRST_CANONICAL_CANDIDATE_SIMULATION_LANE_START":
        raise SourceIdentityPreflightError("attempt_boundary")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args(argv)
    result = run_source_identity_preflight(
        authorization_value=os.environ.get(AUTH_ENV_NAME),
    )
    digest = write_result_once(result, args.output)
    print(f"STATUS={result.status}")
    print(f"VERIFIED_SOURCE_COUNT={result.verified_source_count}")
    print(f"SOURCE_REGISTRY_SHA256={result.source_registry_sha256}")
    print(f"RESULT_PATH={args.output}")
    print(f"RESULT_SHA256={digest}")
    print("SIMULATOR_IMPORTED=NO")
    print("CANDIDATE_SIMULATION_STARTED=NO")
    print("ATTEMPT_MARKER_WRITTEN=NO")
    print("P2_ATTEMPT_CONSUMED=NO")
    print("MODEL_FIT=NO")
    print("PNL=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ObservedSourceIdentity",
    "SourceIdentityPreflightResult",
    "require_authorization",
    "verify_source_file",
    "run_source_identity_preflight",
    "canonical_result_bytes",
    "write_result_once",
    "validate_r6_contract",
]

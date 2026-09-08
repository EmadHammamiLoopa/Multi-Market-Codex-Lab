from __future__ import annotations

import hashlib
import json
from pathlib import Path

from multimarket import dev045_d6r26a_p2_r4_canonical_materialization_runner_preexec as r4
from multimarket import dev045_d6r26a_p2_r5_real_engine_binding_prehistorical as r5
from multimarket import dev045_d6r26a_p2_r6_historical_source_identity_preflight as r6


EXPERIMENT_ID = "DEV045-D6R26A-P2-R7"
DESIGN_VERSION = "canonical-historical-binding-preexecution-v1"
PARENT_R6_FREEZE_HEAD = "36bd3ed16094a29fe647487543a028dfa0498e3b"
DATA_ROLE = "CONSUMED_DEVELOPMENT"

R6_FROZEN_RESULT_RELPATH = "evidence/dev045_d6r26a_p2_r6_source_identity_preflight_pass_frozen.json"
R6_FROZEN_RESULT_BYTES = 2201
R6_FROZEN_RESULT_SHA256 = "d4f0cc248f8c68c6a9f6a364716a7a64a2f1658bbed11cf32140a3f64327bac9"
SOURCE_REGISTRY_SHA256 = "97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4"

CANONICAL_BINDING_READY = True
R4_RUNNER_BOUND_BY_IDENTITY = True
R5_ENGINE_SEMANTICS_BOUND_BY_IDENTITY = True
R6_SOURCE_PREFLIGHT_BOUND_BY_FROZEN_RESULT = True

PREEXECUTION_ONLY = True
EXECUTION_AUTHORIZATION_CREATED = False
HISTORICAL_FILE_IO_AUTHORIZED = False
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

EXPECTED_DAYS = 7
EXPECTED_LANES_PER_DAY = 40
EXPECTED_TOTAL_LANES = 280
EXPECTED_TOTAL_PARTITIONS = 280
ATTEMPT_CONSUMPTION_EVENT = "FIRST_CANONICAL_CANDIDATE_SIMULATION_LANE_START"


class CanonicalHistoricalBindingError(RuntimeError):
    pass


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def frozen_r6_result_path() -> Path:
    return repository_root() / R6_FROZEN_RESULT_RELPATH


def frozen_r6_result_bytes() -> bytes:
    p = frozen_r6_result_path()
    if not p.is_file():
        raise CanonicalHistoricalBindingError(f"r6_result_missing:{p}")
    payload = p.read_bytes()
    if len(payload) != R6_FROZEN_RESULT_BYTES:
        raise CanonicalHistoricalBindingError(
            f"r6_result_bytes:{len(payload)}:{R6_FROZEN_RESULT_BYTES}"
        )
    digest = hashlib.sha256(payload).hexdigest()
    if digest != R6_FROZEN_RESULT_SHA256:
        raise CanonicalHistoricalBindingError(f"r6_result_sha256:{digest}")
    return payload


def frozen_r6_result() -> dict[str, object]:
    payload = frozen_r6_result_bytes()
    try:
        obj = json.loads(payload)
    except Exception as exc:
        raise CanonicalHistoricalBindingError(f"r6_result_json:{type(exc).__name__}") from exc
    if not isinstance(obj, dict):
        raise CanonicalHistoricalBindingError("r6_result_type")
    return obj


def validate_frozen_r6_result() -> None:
    d = frozen_r6_result()
    expected_pairs = {
        "experiment_id": "DEV045-D6R26A-P2-R6",
        "design_version": "historical-source-identity-preflight-v1",
        "status": "SOURCE_IDENTITY_PREFLIGHT_PASS",
        "data_role": DATA_ROLE,
        "source_registry_sha256": SOURCE_REGISTRY_SHA256,
        "verified_source_count": EXPECTED_DAYS,
        "historical_source_opened": True,
        "simulator_imported": False,
        "candidate_simulation_started": False,
        "attempt_marker_written": False,
        "p2_attempt_consumed": False,
        "model_fit": False,
        "pnl": False,
        "live_trading": False,
    }
    for key, value in expected_pairs.items():
        if d.get(key) != value:
            raise CanonicalHistoricalBindingError(f"r6_result_field:{key}:{d.get(key)!r}")
    sources = d.get("sources")
    if not isinstance(sources, list) or len(sources) != EXPECTED_DAYS:
        raise CanonicalHistoricalBindingError("r6_source_count")
    if tuple(x.get("day") for x in sources) != tuple(r6.r2.FROZEN_SOURCE_REGISTRY[i].day for i in range(EXPECTED_DAYS)):
        raise CanonicalHistoricalBindingError("r6_source_day_order")
    for observed, frozen in zip(sources, r6.r2.FROZEN_SOURCE_REGISTRY):
        expected = {
            "day": frozen.day,
            "path": frozen.path,
            "rows": frozen.rows,
            "bytes": frozen.bytes,
            "sha256": frozen.sha256,
            "ndim": 1,
            "itemsize": 64,
        }
        if observed != expected:
            raise CanonicalHistoricalBindingError(f"r6_source_identity:{frozen.day}")


def validate_r7_contract() -> None:
    r4.validate_runner_contract()
    r5.validate_r5_contract()
    r6.validate_r6_contract()
    validate_frozen_r6_result()

    if PARENT_R6_FREEZE_HEAD != "36bd3ed16094a29fe647487543a028dfa0498e3b":
        raise CanonicalHistoricalBindingError("parent")
    if DATA_ROLE != "CONSUMED_DEVELOPMENT":
        raise CanonicalHistoricalBindingError("data_role")
    if SOURCE_REGISTRY_SHA256 != r6.SOURCE_REGISTRY_SHA256:
        raise CanonicalHistoricalBindingError("registry_sha256")
    if not (
        CANONICAL_BINDING_READY
        and R4_RUNNER_BOUND_BY_IDENTITY
        and R5_ENGINE_SEMANTICS_BOUND_BY_IDENTITY
        and R6_SOURCE_PREFLIGHT_BOUND_BY_FROZEN_RESULT
        and PREEXECUTION_ONLY
    ):
        raise CanonicalHistoricalBindingError("binding_readiness")
    if EXECUTION_AUTHORIZATION_CREATED:
        raise CanonicalHistoricalBindingError("execution_authorization_created")
    if (EXPECTED_DAYS, EXPECTED_LANES_PER_DAY, EXPECTED_TOTAL_LANES, EXPECTED_TOTAL_PARTITIONS) != (7, 40, 280, 280):
        raise CanonicalHistoricalBindingError("cardinality")
    if ATTEMPT_CONSUMPTION_EVENT != r6.P2_ATTEMPT_CONSUMPTION_EVENT:
        raise CanonicalHistoricalBindingError("attempt_boundary")
    forbidden = (
        HISTORICAL_FILE_IO_AUTHORIZED,
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
        raise CanonicalHistoricalBindingError("execution_surface_open")


__all__ = [
    "frozen_r6_result_path",
    "frozen_r6_result_bytes",
    "frozen_r6_result",
    "validate_frozen_r6_result",
    "validate_r7_contract",
]

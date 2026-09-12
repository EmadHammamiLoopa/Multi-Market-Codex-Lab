from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import stat

from multimarket import dev045_d6r26a_p2_r2_frozen_source_registry as r2
from multimarket import dev045_d6r26a_p2_r3_execution_authorization_contract as r3
from multimarket import dev045_d6r26a_p2_r25_durable_day_context_bundle_foundation as r25
from multimarket import dev045_d6r26a_p2_r26p0_durable_materialization_freeze as r26p0
from multimarket import dev045_d6r26a_p2_r26p1_real_durable_materializer_preexecution as r26p1
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p6a_full_context_fusion_midpoint_transport as r27p6a
from multimarket import dev045_d6r26a_p2_r27p9_cpython313_float_sum_parity_amendment as r27p9
from multimarket import dev045_d6r26a_p2_r27p16_r10_rolling_volatility_parity_amendment as r27p16
from multimarket import dev045_d6r26a_p2_r27p18_corrected_5m_speed_benchmark_preexecution as r27p18


EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P19"
DESIGN_VERSION = "canonical-materialization-readiness-preflight-v1"
PARENT_R27P18_FREEZE_HEAD = "5d3c2da07a46335a42477178ff03715e7691f588"

SOURCE_REGISTRY_SHA256 = r2.FROZEN_SOURCE_REGISTRY_SHA256
SOURCE_DAYS = tuple(item.day for item in r2.FROZEN_SOURCE_REGISTRY)
SOURCE_COUNT = len(SOURCE_DAYS)

AUTH_ENV_NAME = r3.AUTH_ENV_NAME
AUTH_TOKEN = r3.AUTH_TOKEN
CANONICAL_OUTPUT_ROOT = Path(r3.OUTPUT_ROOT)
ATTEMPT_MARKER_PATH = Path(r3.ATTEMPT_MARKER_PATH)
FAILURE_ARTIFACT_PATH = Path(r3.FAILURE_ARTIFACT_PATH)
FINAL_MANIFEST_PATH = Path(r3.FINAL_MANIFEST_PATH)

DURABLE_ROOT = Path(r26p0.DURABLE_ROOT)
DURABLE_BUILD_ROOT = DURABLE_ROOT / r26p1.BUILD_ROOT_NAME
DURABLE_COMPLETION_MANIFEST_PATH = Path(r26p1.COMPLETION_MANIFEST_PATH)

EXPECTED_LANES_PER_DAY = r3.EXPECTED_LANES_PER_DAY
EXPECTED_TOTAL_PARTITIONS = r3.EXPECTED_TOTAL_PARTITIONS
CANONICAL_COMPLETION_REQUIRES_ALL_280_PARTITIONS = (
    r3.CANONICAL_COMPLETION_REQUIRES_ALL_280_PARTITIONS
)

CORRECTED_ENGINE_IDENTITY = r27p18.CANDIDATE_IMPLEMENTATION
EXPECTED_CORRECTED_ENGINE_IDENTITY = (
    "R27P6A_PLUS_R27P9_L5_PLUS_R27P16_R10_VOLATILITY"
)
R27P6A_REQUIRED = True
R27P9_L5_AMENDMENT_REQUIRED = True
R27P16_R10_VOLATILITY_AMENDMENT_REQUIRED = True

# R27P6 allocates these arrays at capacity n before slicing them to observed
# counts. This is a static capacity upper bound, not an RSS measurement.
FUSED_RAW_CAPACITY_COMPONENT_BYTES_PER_EVENT = (
    ("book_local_ns", 8),
    ("bid_ticks_5", 5 * 8),
    ("bid_qty_5", 5 * 8),
    ("ask_ticks_5", 5 * 8),
    ("ask_qty_5", 5 * 8),
    ("candidate_qty_8", 8 * 8),
    ("flow_local_ns", 8),
    ("flow_code", 1),
    ("flow_qty", 8),
    ("midpoint_exchange_ns", 8),
    ("midpoint_tick_sum", 8),
)
FUSED_RAW_CAPACITY_BYTES_PER_EVENT = sum(
    size for _, size in FUSED_RAW_CAPACITY_COMPONENT_BYTES_PER_EVENT
)
LARGEST_SOURCE = max(r2.FROZEN_SOURCE_REGISTRY, key=lambda item: int(item.rows))
LARGEST_SOURCE_DAY = LARGEST_SOURCE.day
LARGEST_SOURCE_ROWS = int(LARGEST_SOURCE.rows)
LARGEST_SOURCE_BYTES = int(LARGEST_SOURCE.bytes)
LARGEST_FUSED_RAW_CAPACITY_BYTES = (
    LARGEST_SOURCE_ROWS * FUSED_RAW_CAPACITY_BYTES_PER_EVENT
)

R27P18_PROVED_EXACT_PARITY_AT_5M = True
R27P18_PROVED_MINIMUM_SPEEDUP_AT_5M = True
FULL_DAY_BOUNDED_MEMORY_PROVEN = False
FULL_DAY_MEMORY_PROOF_REQUIRED_BEFORE_CANONICAL_EXECUTION = True
DIRECT_FULL_DAY_ACCELERATED_MATERIALIZATION_AUTHORIZED = False
CANONICAL_EXECUTION_READY = False
READINESS_BLOCKER = "FULL_DAY_BOUNDED_MEMORY_NOT_PROVEN"

P2_ATTEMPT_CONSUMED = False
THIS_COMMIT_OPENS_HISTORICAL_SOURCE = False
THIS_COMMIT_REHASHES_HISTORICAL_SOURCE = False
THIS_COMMIT_BUILDS_DURABLE_CONTEXT = False
THIS_COMMIT_RUNS_SIMULATOR = False
THIS_COMMIT_WRITES_CANONICAL_LABELS = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
DURABLE_CONTEXT_WRITE_AUTHORIZED = False

PARTIAL_DURABLE_BUILD_IS_NOT_COMPLETE = True
PARTIAL_DURABLE_BUILD_REUSE_AUTHORIZED = False
PARTIAL_DURABLE_BUILD_AUTO_DELETE_AUTHORIZED = False
PARTIAL_DURABLE_BUILD_PRESERVE_FOR_FORENSICS = True
COMPLETED_DURABLE_BUNDLE_REUSE_REQUIRES_R25_VERIFICATION = True

MODEL_FIT_AUTHORIZED = False
MODEL_SELECTION_AUTHORIZED = False
THRESHOLD_TUNING_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED = False


class R27P19Error(RuntimeError):
    pass


@dataclass(frozen=True)
class LocalMetadataPreflight:
    source_count: int
    source_stat_match_count: int
    canonical_output_root_exists: bool
    canonical_output_entries: tuple[str, ...]
    attempt_marker_exists: bool
    failure_artifact_exists: bool
    final_manifest_exists: bool
    durable_root_exists: bool
    durable_completed_day_names: tuple[str, ...]
    durable_partial_build_names: tuple[str, ...]
    durable_completion_manifest_exists: bool
    canonical_execution_ready: bool
    readiness_blocker: str


def fused_raw_capacity_bytes(rows: int) -> int:
    value = int(rows)
    if value < 0:
        raise R27P19Error("negative_rows")
    return value * FUSED_RAW_CAPACITY_BYTES_PER_EVENT


def _regular_file_size_without_open(path: Path) -> int | None:
    target = Path(path)
    try:
        info = target.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise R27P19Error(f"source_not_regular:{target}")
    return int(info.st_size)


def _directory_entries(path: Path) -> tuple[str, ...]:
    target = Path(path)
    try:
        info = target.lstat()
    except FileNotFoundError:
        return ()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise R27P19Error(f"not_directory:{target}")
    return tuple(sorted(item.name for item in target.iterdir()))


def inspect_local_metadata_only() -> LocalMetadataPreflight:
    """Inspect filesystem metadata only; never open or hash market payloads."""
    source_stat_match_count = 0
    for item in r2.FROZEN_SOURCE_REGISTRY:
        observed_bytes = _regular_file_size_without_open(Path(item.path))
        if observed_bytes is None:
            raise R27P19Error(f"source_missing:{item.day}")
        if observed_bytes != int(item.bytes):
            raise R27P19Error(
                f"source_stat_bytes:{item.day}:{observed_bytes}:{int(item.bytes)}"
            )
        source_stat_match_count += 1

    canonical_entries = _directory_entries(CANONICAL_OUTPUT_ROOT)
    marker_exists = ATTEMPT_MARKER_PATH.exists()
    failure_exists = FAILURE_ARTIFACT_PATH.exists()
    final_manifest_exists = FINAL_MANIFEST_PATH.exists()

    # Any existing canonical output is a collision at this pre-attempt stage.
    if marker_exists:
        raise R27P19Error("attempt_marker_exists")
    if canonical_entries:
        raise R27P19Error(
            "canonical_output_not_pristine:" + ",".join(canonical_entries)
        )

    durable_entries = _directory_entries(DURABLE_ROOT)
    completed = tuple(
        day
        for day in SOURCE_DAYS
        if (DURABLE_ROOT / day / r25.MANIFEST_NAME).is_file()
    )
    build_entries = _directory_entries(DURABLE_BUILD_ROOT)

    unknown_top_level = tuple(
        name
        for name in durable_entries
        if name not in set(SOURCE_DAYS)
        and name not in {r26p1.BUILD_ROOT_NAME, r26p1.COMPLETION_MANIFEST_NAME}
    )
    if unknown_top_level:
        raise R27P19Error(
            "durable_unknown_top_level:" + ",".join(unknown_top_level)
        )

    return LocalMetadataPreflight(
        source_count=SOURCE_COUNT,
        source_stat_match_count=source_stat_match_count,
        canonical_output_root_exists=CANONICAL_OUTPUT_ROOT.exists(),
        canonical_output_entries=canonical_entries,
        attempt_marker_exists=marker_exists,
        failure_artifact_exists=failure_exists,
        final_manifest_exists=final_manifest_exists,
        durable_root_exists=DURABLE_ROOT.exists(),
        durable_completed_day_names=completed,
        durable_partial_build_names=build_entries,
        durable_completion_manifest_exists=DURABLE_COMPLETION_MANIFEST_PATH.is_file(),
        canonical_execution_ready=False,
        readiness_blocker=READINESS_BLOCKER,
    )


def validate_r27p19_contract() -> None:
    r2.validate_frozen_source_registry()
    r3.validate_execution_authorization_contract()
    r25.validate_r25_contract()
    r26p0.validate_r26p0_contract()
    r26p1.validate_r26p1_contract()
    r27p6.validate_r27p6_contract()
    r27p6a.validate_r27p6a_contract()
    r27p9.validate_r27p9_contract()
    r27p16.validate_r27p16_contract()
    r27p18.validate_r27p18_contract()

    if PARENT_R27P18_FREEZE_HEAD != "5d3c2da07a46335a42477178ff03715e7691f588":
        raise R27P19Error("parent")
    if SOURCE_REGISTRY_SHA256 != "97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4":
        raise R27P19Error("source_registry")
    if SOURCE_COUNT != 7 or SOURCE_DAYS != tuple(r26p0.EXPECTED_DAYS):
        raise R27P19Error("source_days")
    if EXPECTED_LANES_PER_DAY != 40 or EXPECTED_TOTAL_PARTITIONS != 280:
        raise R27P19Error("partition_cardinality")
    if not CANONICAL_COMPLETION_REQUIRES_ALL_280_PARTITIONS:
        raise R27P19Error("completion_contract")
    if CORRECTED_ENGINE_IDENTITY != EXPECTED_CORRECTED_ENGINE_IDENTITY:
        raise R27P19Error("corrected_engine_identity")
    if not (
        R27P6A_REQUIRED
        and R27P9_L5_AMENDMENT_REQUIRED
        and R27P16_R10_VOLATILITY_AMENDMENT_REQUIRED
        and r27p18.R27P9_L5_AMENDMENT_REQUIRED
        and r27p18.R27P16_VOLATILITY_AMENDMENT_REQUIRED
    ):
        raise R27P19Error("corrected_engine_binding")
    if FUSED_RAW_CAPACITY_BYTES_PER_EVENT != 265:
        raise R27P19Error("fused_raw_capacity_per_event")
    if LARGEST_SOURCE_DAY != "2026-07-01" or LARGEST_SOURCE_ROWS != 181_084_390:
        raise R27P19Error("largest_source_identity")
    if LARGEST_FUSED_RAW_CAPACITY_BYTES != fused_raw_capacity_bytes(LARGEST_SOURCE_ROWS):
        raise R27P19Error("largest_capacity")
    if FULL_DAY_BOUNDED_MEMORY_PROVEN:
        raise R27P19Error("unearned_memory_proof")
    if DIRECT_FULL_DAY_ACCELERATED_MATERIALIZATION_AUTHORIZED or CANONICAL_EXECUTION_READY:
        raise R27P19Error("premature_execution_readiness")
    if READINESS_BLOCKER != "FULL_DAY_BOUNDED_MEMORY_NOT_PROVEN":
        raise R27P19Error("readiness_blocker")
    if not (
        PARTIAL_DURABLE_BUILD_IS_NOT_COMPLETE
        and PARTIAL_DURABLE_BUILD_PRESERVE_FOR_FORENSICS
        and COMPLETED_DURABLE_BUNDLE_REUSE_REQUIRES_R25_VERIFICATION
        and FULL_DAY_MEMORY_PROOF_REQUIRED_BEFORE_CANONICAL_EXECUTION
    ):
        raise R27P19Error("required_guard_disabled")
    forbidden = (
        P2_ATTEMPT_CONSUMED,
        THIS_COMMIT_OPENS_HISTORICAL_SOURCE,
        THIS_COMMIT_REHASHES_HISTORICAL_SOURCE,
        THIS_COMMIT_BUILDS_DURABLE_CONTEXT,
        THIS_COMMIT_RUNS_SIMULATOR,
        THIS_COMMIT_WRITES_CANONICAL_LABELS,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        DURABLE_CONTEXT_WRITE_AUTHORIZED,
        PARTIAL_DURABLE_BUILD_REUSE_AUTHORIZED,
        PARTIAL_DURABLE_BUILD_AUTO_DELETE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        MODEL_SELECTION_AUTHORIZED,
        THRESHOLD_TUNING_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED,
    )
    if any(forbidden):
        raise R27P19Error("closed_surface_open")


def print_contract_summary() -> None:
    validate_r27p19_contract()
    gib = 1024 ** 3
    print("R27P19_CONTRACT=PASS")
    print(f"PARENT_R27P18_FREEZE_HEAD={PARENT_R27P18_FREEZE_HEAD}")
    print(f"SOURCE_REGISTRY_SHA256={SOURCE_REGISTRY_SHA256}")
    print(f"SOURCE_COUNT={SOURCE_COUNT}")
    print(f"EXPECTED_TOTAL_PARTITIONS={EXPECTED_TOTAL_PARTITIONS}")
    print(f"CANONICAL_OUTPUT_ROOT={CANONICAL_OUTPUT_ROOT}")
    print(f"ATTEMPT_MARKER_PATH={ATTEMPT_MARKER_PATH}")
    print(f"DURABLE_ROOT={DURABLE_ROOT}")
    print(f"CORRECTED_ENGINE_IDENTITY={CORRECTED_ENGINE_IDENTITY}")
    print(f"FUSED_RAW_CAPACITY_BYTES_PER_EVENT={FUSED_RAW_CAPACITY_BYTES_PER_EVENT}")
    print(f"LARGEST_SOURCE_DAY={LARGEST_SOURCE_DAY}")
    print(f"LARGEST_SOURCE_ROWS={LARGEST_SOURCE_ROWS}")
    print(
        "LARGEST_FUSED_RAW_CAPACITY_GIB="
        f"{LARGEST_FUSED_RAW_CAPACITY_BYTES / gib:.6f}"
    )
    print("FULL_DAY_BOUNDED_MEMORY_PROVEN=NO")
    print("CANONICAL_EXECUTION_READY=NO")
    print(f"READINESS_BLOCKER={READINESS_BLOCKER}")
    print("P2_ATTEMPT_CONSUMED=NO")
    print("MARKET_RAW_ARCHIVE=SEALED")


if __name__ == "__main__":
    print_contract_summary()

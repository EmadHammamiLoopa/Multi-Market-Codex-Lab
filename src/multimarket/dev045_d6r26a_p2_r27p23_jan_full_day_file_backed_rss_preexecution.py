from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import resource
import shutil

from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p0_accelerated_context_engine_design_parity_freeze as r27p0
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p9_cpython313_float_sum_parity_amendment as r27p9
from multimarket import dev045_d6r26a_p2_r27p18_corrected_5m_speed_benchmark_preexecution as r27p18
from multimarket import dev045_d6r26a_p2_r27p21_file_backed_fused_raw_kernel_synthetic_parity as r27p21
from multimarket import dev045_d6r26a_p2_r27p22_real_5m_file_backed_rss_preexecution as r27p22

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P23"
DESIGN_VERSION = "jan-full-day-file-backed-rss-preexecution-v1"
PARENT_R27P22_HEAD = "9c330d8a6b5ddaae400bf1cb779ef7bf09582aed"

AUTH_ENV = "DEV045_D6R26A_P2_R27P23_AUTHORIZE"
AUTH_TOKEN = "YES_FROZEN_JAN_FULL_DAY_FILE_BACKED_RSS_PROOF_PREATTEMPT"

SOURCE_DAY = r27p22.SOURCE_DAY
SOURCE_PATH = r27p22.SOURCE_PATH
SOURCE_ROWS = r27p22.SOURCE_ROWS
SOURCE_BYTES = r27p22.SOURCE_BYTES
SOURCE_SHA256 = r27p22.SOURCE_SHA256
SOURCE_DAY_START_NS = r27p22.SOURCE_DAY_START_NS
SOURCE_DAY_END_EXCLUSIVE_NS = r27p22.SOURCE_DAY_END_EXCLUSIVE_NS
FULL_DAY_ROWS = SOURCE_ROWS

BYTES_PER_EVENT = 265
EXPECTED_RAW_FILE_BYTES = FULL_DAY_ROWS * BYTES_PER_EVENT
MIN_FREE_DISK_BYTES = 24 * 1024**3
MIN_FREE_DISK_GIB = 24.0
MAX_PEAK_RSS_BYTES = 12 * 1024**3
MAX_PEAK_RSS_GIB = 12.0
RSS_METRIC = "TOTAL_PROCESS_PEAK_RSS"
RSS_PLATFORM = "LINUX_RUSAGE_MAXRSS_KIB"
EXTERNAL_RSS_KILL_GIB = 12.0

SCRATCH_ROOT = Path("/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_r27p23_jan_full_day_rss")

REAL_HISTORICAL_FULL_DAY_OPEN_AUTHORIZED = True
REAL_HISTORICAL_FULL_DAY_REQUIRES_EXPLICIT_AUTHORIZATION = True
SOURCE_IDENTITY_REHASH_REQUIRED = True
ONE_FROZEN_SOURCE_ONLY = True
JANUARY_ONLY = True
FULL_DAY_CANDIDATE_ONLY = True
REFERENCE_RERUN_AUTHORIZED = False
NEW_REAL_PARITY_CLAIM = False
EPHEMERAL_SCRATCH_ONLY = True
PREEXISTING_SCRATCH_REUSE_AUTHORIZED = False
PREEXISTING_SCRATCH_AUTO_DELETE_AUTHORIZED = False
BENCHMARK_MANIFEST_WRITE_AUTHORIZED = False
DURABLE_CONTEXT_WRITE_AUTHORIZED = False
FULL_JAN_JUL_RERUN_AUTHORIZED = False
SIMULATOR_LANE_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED = False
P2_ATTEMPT_CONSUMED = False

R27P18_REAL_5M_EXACT_PARITY_INHERITED = True
R27P21_SYNTHETIC_REWRITE_EXACT_PARITY_INHERITED = True
R27P22_REAL_5M_RSS_PASS_INHERITED = True
FULL_DAY_BOUNDED_MEMORY_PROVEN = False
CANONICAL_EXECUTION_READY = False
READINESS_BLOCKER = "JAN_FULL_DAY_RSS_PROOF_NOT_YET_EXECUTED"


class R27P23Error(RuntimeError):
    pass


@dataclass(frozen=True)
class JanFullDayRssObservation:
    experiment_id: str
    design_version: str
    source_day: str
    rows: int
    peak_rss_bytes: int
    peak_rss_gib: float
    max_peak_rss_bytes: int
    rss_gate_pass: bool
    candidate_digest: r27p0.ContextDigest
    l5_changed_cells: int
    volatility_changed_cells: int
    expected_raw_file_bytes: int
    p2_attempt_consumed: bool


def _authorized(environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(AUTH_ENV) == AUTH_TOKEN


def _peak_rss_bytes() -> int:
    value_kib = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if value_kib <= 0:
        raise R27P23Error("peak_rss_unavailable")
    return value_kib * 1024


def _validate_scratch_preflight() -> None:
    if SCRATCH_ROOT.exists():
        raise R27P23Error("scratch_root_preexists_preserve_for_forensics")
    SCRATCH_ROOT.parent.mkdir(parents=True, exist_ok=True)
    free_bytes = int(shutil.disk_usage(SCRATCH_ROOT.parent).free)
    if free_bytes < MIN_FREE_DISK_BYTES:
        raise R27P23Error(f"insufficient_free_disk:{free_bytes}")


def validate_r27p23_contract() -> None:
    r27p22.validate_r27p22_contract()
    if PARENT_R27P22_HEAD != "9c330d8a6b5ddaae400bf1cb779ef7bf09582aed":
        raise R27P23Error("parent")
    if SOURCE_DAY != "2026-01-01" or FULL_DAY_ROWS != 64_314_723:
        raise R27P23Error("source_scope")
    if SOURCE_BYTES != 4_116_142_528:
        raise R27P23Error("source_bytes")
    if SOURCE_SHA256 != "8f0a4fbd56ecdc261dbe2041ce138a09456423074925d495272716219a1d4da1":
        raise R27P23Error("source_sha256")
    if BYTES_PER_EVENT != 265:
        raise R27P23Error("bytes_per_event")
    if EXPECTED_RAW_FILE_BYTES != FULL_DAY_ROWS * 265:
        raise R27P23Error("raw_file_bytes")
    if MIN_FREE_DISK_BYTES != 24 * 1024**3 or MIN_FREE_DISK_GIB != 24.0:
        raise R27P23Error("disk_gate")
    if MAX_PEAK_RSS_BYTES != 12 * 1024**3 or MAX_PEAK_RSS_GIB != 12.0:
        raise R27P23Error("rss_gate")
    required = (
        REAL_HISTORICAL_FULL_DAY_OPEN_AUTHORIZED,
        REAL_HISTORICAL_FULL_DAY_REQUIRES_EXPLICIT_AUTHORIZATION,
        SOURCE_IDENTITY_REHASH_REQUIRED,
        ONE_FROZEN_SOURCE_ONLY,
        JANUARY_ONLY,
        FULL_DAY_CANDIDATE_ONLY,
        EPHEMERAL_SCRATCH_ONLY,
        R27P18_REAL_5M_EXACT_PARITY_INHERITED,
        R27P21_SYNTHETIC_REWRITE_EXACT_PARITY_INHERITED,
        R27P22_REAL_5M_RSS_PASS_INHERITED,
        not REFERENCE_RERUN_AUTHORIZED,
        not NEW_REAL_PARITY_CLAIM,
        not PREEXISTING_SCRATCH_REUSE_AUTHORIZED,
        not PREEXISTING_SCRATCH_AUTO_DELETE_AUTHORIZED,
        not BENCHMARK_MANIFEST_WRITE_AUTHORIZED,
        not DURABLE_CONTEXT_WRITE_AUTHORIZED,
        not FULL_DAY_BOUNDED_MEMORY_PROVEN,
        not CANONICAL_EXECUTION_READY,
    )
    if not all(required):
        raise R27P23Error("required_guard")
    forbidden = (
        FULL_JAN_JUL_RERUN_AUTHORIZED,
        SIMULATOR_LANE_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED,
        P2_ATTEMPT_CONSUMED,
    )
    if any(forbidden):
        raise R27P23Error("execution_surface_open")
    if READINESS_BLOCKER != "JAN_FULL_DAY_RSS_PROOF_NOT_YET_EXECUTED":
        raise R27P23Error("readiness_blocker")


def run_jan_full_day_rss_probe(*, environ: dict[str, str] | None = None) -> JanFullDayRssObservation:
    validate_r27p23_contract()
    if not _authorized(environ):
        raise R27P23Error("authorization")
    r27p2._validate_preattempt_state()
    _validate_scratch_preflight()

    events = r27p2._verify_source_identity()
    context = None
    holder = []
    try:
        if bool(events.flags.writeable):
            raise R27P23Error("source_writeable")
        if int(events.size) != FULL_DAY_ROWS:
            raise R27P23Error("source_rows")

        SCRATCH_ROOT.mkdir(parents=False, exist_ok=False)
        target_raw_kernel = r27p21.build_file_backed_raw_kernel()
        base_feature_kernel = r27p5.build_feature_kernel()
        l5_amendment_kernel = r27p9.build_l5_obi_amendment_kernel()
        adapter, holder = r27p21.make_r27p6_signature_adapter(
            SCRATCH_ROOT / "raw_buffers",
            kernel=target_raw_kernel,
        )
        context, l5_changed_cells, volatility_changed_cells = r27p18.build_corrected_fused_day_context(
            events,
            nominal_day_start_local_ns=SOURCE_DAY_START_NS,
            nominal_day_end_exclusive_local_ns=SOURCE_DAY_END_EXCLUSIVE_NS,
            scratch_root=SCRATCH_ROOT / "context",
            raw_kernel=adapter,
            base_feature_kernel=base_feature_kernel,
            l5_amendment_kernel=l5_amendment_kernel,
        )
        digest = r27p0.digest_day_context(context)
        peak_rss_bytes = _peak_rss_bytes()
        gate_pass = bool(peak_rss_bytes <= MAX_PEAK_RSS_BYTES)
        observation = JanFullDayRssObservation(
            experiment_id=EXPERIMENT_ID,
            design_version=DESIGN_VERSION,
            source_day=SOURCE_DAY,
            rows=FULL_DAY_ROWS,
            peak_rss_bytes=int(peak_rss_bytes),
            peak_rss_gib=float(peak_rss_bytes / 1024**3),
            max_peak_rss_bytes=MAX_PEAK_RSS_BYTES,
            rss_gate_pass=gate_pass,
            candidate_digest=digest,
            l5_changed_cells=int(l5_changed_cells),
            volatility_changed_cells=int(volatility_changed_cells),
            expected_raw_file_bytes=EXPECTED_RAW_FILE_BYTES,
            p2_attempt_consumed=False,
        )
    finally:
        if context is not None and not context.midpoint_index.closed:
            r20.close_midpoint_index(context.midpoint_index)
        r27p21.close_adapter_runs(holder)
        r27p18._close_source_memmap(events)

    print(f"R27P23_SOURCE_IDENTITY=PASS DAY={SOURCE_DAY} ROWS={SOURCE_ROWS} BYTES={SOURCE_BYTES} SHA256={SOURCE_SHA256}")
    print(f"R27P23_FULL_DAY_ROWS={observation.rows}")
    print(f"R27P23_EXPECTED_RAW_FILE_BYTES={observation.expected_raw_file_bytes}")
    print(f"R27P23_PEAK_RSS_BYTES={observation.peak_rss_bytes}")
    print(f"R27P23_PEAK_RSS_GIB={observation.peak_rss_gib:.6f}")
    print(f"R27P23_MAX_PEAK_RSS_GIB={MAX_PEAK_RSS_GIB:.1f}")
    print(f"R27P23_JAN_FULL_DAY_RSS_GATE={'PASS' if observation.rss_gate_pass else 'FAIL'}")
    print(f"R27P23_CANDIDATE_DIGEST={observation.candidate_digest}")
    print(f"R27P23_L5_AMENDMENT_CHANGED_CELLS={observation.l5_changed_cells}")
    print(f"R27P23_VOLATILITY_AMENDMENT_CHANGED_CELLS={observation.volatility_changed_cells}")
    print("R27P23_REFERENCE_RERUN=NO")
    print("R27P23_NEW_REAL_PARITY_CLAIM=NO")
    print("DURABLE_CONTEXT_WRITE=NO")
    print("SIMULATOR_RUN=NO")
    print("CANONICAL_LABEL_WRITE=NO")
    print("P2_ATTEMPT_CONSUMED=NO")
    print("MARKET_RAW_ARCHIVE_OPENED=NO")
    return observation


def main() -> int:
    try:
        observation = run_jan_full_day_rss_probe()
    except Exception as exc:
        print(f"R27P23_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("FULL_DAY_BOUNDED_MEMORY_PROVEN=NO")
        print("CANONICAL_EXECUTION_READY=NO")
        print("P2_ATTEMPT_CONSUMED=NO")
        return 2
    return 0 if observation.rss_gate_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AUTH_ENV",
    "AUTH_TOKEN",
    "EXPECTED_RAW_FILE_BYTES",
    "EXTERNAL_RSS_KILL_GIB",
    "FULL_DAY_ROWS",
    "MAX_PEAK_RSS_BYTES",
    "MAX_PEAK_RSS_GIB",
    "MIN_FREE_DISK_BYTES",
    "SCRATCH_ROOT",
    "JanFullDayRssObservation",
    "run_jan_full_day_rss_probe",
    "validate_r27p23_contract",
]

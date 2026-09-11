from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p11_amended_bounded_speed_benchmark_preexecution as r27p11
from multimarket import dev045_d6r26a_p2_r27p14_cpython_volatility_parity_amendment as r27p14

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P15"
DESIGN_VERSION = "real-5m-exact-parity-recheck-preexecution-v1"
PARENT_R27P14_FREEZE_HEAD = "c558bfe0e2e7b11243996daa28ea4bf3f34a2648"
AUTH_ENV = "DEV045_D6R26A_P2_R27P15_AUTHORIZE"
AUTH_TOKEN = "YES_REAL_5M_EXACT_PARITY_RECHECK"
PREFIX_ROWS = 5_000_000

SOURCE_DAY = r27p11.SOURCE_DAY
SOURCE_PATH = r27p11.SOURCE_PATH
SOURCE_ROWS = r27p11.SOURCE_ROWS
SOURCE_BYTES = r27p11.SOURCE_BYTES
SOURCE_SHA256 = r27p11.SOURCE_SHA256
SOURCE_DAY_START_NS = r27p11.SOURCE_DAY_START_NS
SOURCE_DAY_END_EXCLUSIVE_NS = r27p11.SOURCE_DAY_END_EXCLUSIVE_NS

REAL_HISTORICAL_DIAGNOSTIC_AUTHORIZED = True
REAL_HISTORICAL_DIAGNOSTIC_REQUIRES_EXPLICIT_AUTHORIZATION = True
ONE_FROZEN_SOURCE_ONLY = True
PREFIX_ONLY = True
EXACT_FEATURE_PARITY_REQUIRED = True
R27P9_L5_AMENDMENT_REQUIRED = True
R27P14_VOLATILITY_AMENDMENT_REQUIRED = True
NO_TIMING = True
NO_SPEED_GATE = True
NO_BENCHMARK_MANIFEST = True
SOURCE_READ_ONLY_REQUIRED = True

R27P12_RERUN_AUTHORIZED = False
R27P13_RERUN_AUTHORIZED = False
FULL_JAN_JUL_RERUN_AUTHORIZED = False
DURABLE_CONTEXT_WRITE_AUTHORIZED = False
P2_ATTEMPT_CONSUMED = False
SIMULATOR_LANE_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED = False


class R27P15Error(RuntimeError):
    pass


@dataclass(frozen=True)
class ParityReport:
    prefix_rows: int
    decision_count: int
    leading_preeligible_count: int
    exact_feature_parity: bool
    mismatch_cells: int
    mismatch_feature_indices: tuple[int, ...]
    l5_changed_cells: int
    volatility_changed_cells: int


def real_diagnostic_authorized(environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(AUTH_ENV) == AUTH_TOKEN


def _require_authorized(environ: dict[str, str] | None = None) -> None:
    if not real_diagnostic_authorized(environ):
        raise R27P15Error("authorization")


def diagnose_events(events: np.ndarray, *, prefix_rows: int) -> ParityReport:
    a = r19._validate_event_surface(events)
    n = int(prefix_rows)
    if n != PREFIX_ROWS or n > int(a.size):
        raise R27P15Error("prefix_rows")
    prefix = a[:n]

    reference = r19.build_once_day_dense_feature_cache(
        prefix,
        nominal_day_start_local_ns=SOURCE_DAY_START_NS,
        nominal_day_end_exclusive_local_ns=SOURCE_DAY_END_EXCLUSIVE_NS,
    )

    with TemporaryDirectory(prefix="dev045_r27p15_diag_") as root:
        candidate_context, l5_changed = r27p11.build_amended_fused_day_context(
            prefix,
            nominal_day_start_local_ns=SOURCE_DAY_START_NS,
            nominal_day_end_exclusive_local_ns=SOURCE_DAY_END_EXCLUSIVE_NS,
            scratch_root=Path(root),
        )
        try:
            cache = candidate_context.feature_cache
            if not np.array_equal(reference.cache.decision_local_ns, cache.decision_local_ns):
                raise R27P15Error("decision_local_ns")
            if not np.array_equal(reference.cache.best_bid_tick, cache.best_bid_tick):
                raise R27P15Error("best_bid_tick")
            if not np.array_equal(reference.cache.best_ask_tick, cache.best_ask_tick):
                raise R27P15Error("best_ask_tick")

            raw = r27p11.r27p6.run_fused_raw_surface(prefix)
            surface = r27p11._compact_from_raw(raw)
            base = r27p11.r27p5.CompiledFeatureResult(
                decision_local_ns=cache.decision_local_ns,
                best_bid_tick=cache.best_bid_tick,
                best_ask_tick=cache.best_ask_tick,
                values=cache.values,
                leading_preeligible_count=candidate_context.feature_summary.leading_preeligible_count,
            )
            amended = r27p14.apply_volatility_amendment(surface, base)
            vol_audit = r27p14.audit_amendment(base, amended)
            if not vol_audit.other_feature_bytes_equal:
                raise R27P15Error("volatility_amendment_scope")
            if any(i not in r27p14.AMENDED_FEATURE_INDICES for i in vol_audit.changed_feature_indices):
                raise R27P15Error("volatility_amendment_feature_indices")

            mismatch = np.not_equal(reference.cache.values, amended.values)
            mismatch_cells = int(np.count_nonzero(mismatch))
            coords = np.argwhere(mismatch)
            mismatch_features = tuple(sorted({int(row[2]) for row in coords})) if coords.size else ()
            exact = mismatch_cells == 0
        finally:
            if not candidate_context.midpoint_index.closed:
                r20.close_midpoint_index(candidate_context.midpoint_index)

    return ParityReport(
        prefix_rows=n,
        decision_count=int(reference.cache.decision_local_ns.size),
        leading_preeligible_count=int(reference.summary.leading_preeligible_count),
        exact_feature_parity=bool(exact),
        mismatch_cells=mismatch_cells,
        mismatch_feature_indices=mismatch_features,
        l5_changed_cells=int(l5_changed),
        volatility_changed_cells=int(vol_audit.changed_cells),
    )


def run_real_recheck(*, environ: dict[str, str] | None = None) -> ParityReport:
    validate_r27p15_contract()
    _require_authorized(environ)
    r27p2._validate_preattempt_state()
    events = r27p2._verify_source_identity()
    try:
        if bool(events.flags.writeable):
            raise R27P15Error("source_writeable")
        report = diagnose_events(events, prefix_rows=PREFIX_ROWS)
    finally:
        mm = getattr(events, "_mmap", None)
        if mm is not None:
            mm.close()

    print(f"R27P15_SOURCE_IDENTITY=PASS DAY={SOURCE_DAY} ROWS={SOURCE_ROWS} BYTES={SOURCE_BYTES} SHA256={SOURCE_SHA256}")
    print(f"R27P15_PREFIX_ROWS={report.prefix_rows}")
    print(f"R27P15_DECISION_COUNT={report.decision_count}")
    print(f"R27P15_LEADING_PREELIGIBLE={report.leading_preeligible_count}")
    print(f"R27P15_L5_AMENDMENT_CHANGED_CELLS={report.l5_changed_cells}")
    print(f"R27P15_VOLATILITY_AMENDMENT_CHANGED_CELLS={report.volatility_changed_cells}")
    print(f"R27P15_MISMATCH_CELLS={report.mismatch_cells}")
    print(f"R27P15_MISMATCH_FEATURE_INDICES={report.mismatch_feature_indices}")
    print(f"R27P15_EXACT_FEATURE_PARITY={'PASS' if report.exact_feature_parity else 'FAIL'}")
    print("R27P15_TIMING_PERFORMED=NO")
    print("R27P15_SPEED_GATE_RUN=NO")
    print("R27P12_RERUN=NO")
    print("R27P13_RERUN=NO")
    print("100K_RERUN=NO")
    print("1M_RERUN=NO")
    print("BENCHMARK_MANIFEST_WRITTEN=NO")
    print("P2_ATTEMPT_CONSUMED=NO")
    print("FULL_JAN_JUL_RERUN=NO")
    print("SIMULATOR_RUN=NO")
    print("MODEL_FIT=NO")
    print("PNL=NO")
    print("MARKET_RAW_ARCHIVE_OPENED=NO")
    if not report.exact_feature_parity:
        raise R27P15Error("exact_feature_parity")
    return report


def validate_r27p15_contract() -> None:
    r27p14.validate_r27p14_contract()
    if PARENT_R27P14_FREEZE_HEAD != "c558bfe0e2e7b11243996daa28ea4bf3f34a2648":
        raise R27P15Error("parent")
    required = (
        PREFIX_ROWS == 5_000_000,
        REAL_HISTORICAL_DIAGNOSTIC_AUTHORIZED,
        REAL_HISTORICAL_DIAGNOSTIC_REQUIRES_EXPLICIT_AUTHORIZATION,
        ONE_FROZEN_SOURCE_ONLY,
        PREFIX_ONLY,
        EXACT_FEATURE_PARITY_REQUIRED,
        R27P9_L5_AMENDMENT_REQUIRED,
        R27P14_VOLATILITY_AMENDMENT_REQUIRED,
        NO_TIMING,
        NO_SPEED_GATE,
        NO_BENCHMARK_MANIFEST,
        SOURCE_READ_ONLY_REQUIRED,
    )
    if not all(required):
        raise R27P15Error("required_guard")
    forbidden = (
        R27P12_RERUN_AUTHORIZED,
        R27P13_RERUN_AUTHORIZED,
        FULL_JAN_JUL_RERUN_AUTHORIZED,
        DURABLE_CONTEXT_WRITE_AUTHORIZED,
        P2_ATTEMPT_CONSUMED,
        SIMULATOR_LANE_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED,
    )
    if any(forbidden):
        raise R27P15Error("execution_surface_open")


def main() -> int:
    try:
        run_real_recheck()
    except Exception as exc:
        print(f"R27P15_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("R27P15_SPEED_GATE_RUN=NO")
        print("R27P12_RERUN=NO")
        print("R27P13_RERUN=NO")
        print("100K_RERUN=NO")
        print("1M_RERUN=NO")
        print("P2_ATTEMPT_CONSUMED=NO")
        print("MARKET_RAW_ARCHIVE_OPENED=NO")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

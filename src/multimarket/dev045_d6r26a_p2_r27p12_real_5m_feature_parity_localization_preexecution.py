from __future__ import annotations

from dataclasses import dataclass
import os

import numpy as np

from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p11_amended_bounded_speed_benchmark_preexecution as r27p11

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P12"
DESIGN_VERSION = "real-5m-feature-parity-localization-preexecution-v1"
PARENT_R27P11_FAILURE_FREEZE_HEAD = "516ddc55c87f758eaf8d1137685acdec464fa5b3"

AUTH_ENV = "DEV045_D6R26A_P2_R27P12_AUTHORIZE"
AUTH_TOKEN = "YES_REAL_5M_FEATURE_PARITY_LOCALIZATION"
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
NO_TIMING = True
NO_SPEED_GATE = True
NO_BENCHMARK_MANIFEST = True
SOURCE_READ_ONLY_REQUIRED = True

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


class R27P12Error(RuntimeError):
    pass


@dataclass(frozen=True)
class FeatureDiff:
    feature_index: int
    feature_name: str
    mismatch_count: int
    first_decision_index: int | None
    first_case_index: int | None
    expected_value: float | None
    observed_value: float | None
    max_abs_diff: float


@dataclass(frozen=True)
class LocalizationReport:
    prefix_rows: int
    decision_count: int
    leading_preeligible_count: int
    feature_diffs: tuple[FeatureDiff, ...]
    mismatching_features: tuple[str, ...]
    total_mismatch_cells: int


def real_diagnostic_authorized(environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(AUTH_ENV) == AUTH_TOKEN


def _require_authorized(environ: dict[str, str] | None = None) -> None:
    if not real_diagnostic_authorized(environ):
        raise R27P12Error("authorization")


def localize_values(expected: np.ndarray, observed: np.ndarray) -> tuple[FeatureDiff, ...]:
    a = np.asarray(expected)
    b = np.asarray(observed)
    if a.dtype != b.dtype:
        raise R27P12Error("feature_values_dtype")
    if a.shape != b.shape:
        raise R27P12Error("feature_values_shape")
    if a.ndim != 3 or a.shape[2] != len(r8b.FEATURE_NAMES):
        raise R27P12Error("feature_values_surface")

    out: list[FeatureDiff] = []
    for fi, name in enumerate(r8b.FEATURE_NAMES):
        ea = a[:, :, fi]
        ob = b[:, :, fi]
        mismatch = np.not_equal(ea, ob)
        count = int(np.count_nonzero(mismatch))
        if count:
            coords = np.argwhere(mismatch)
            di, ci = (int(x) for x in coords[0])
            ev = float(ea[di, ci])
            ov = float(ob[di, ci])
            max_abs = float(np.max(np.abs(ea[mismatch] - ob[mismatch])))
        else:
            di = ci = None
            ev = ov = None
            max_abs = 0.0
        out.append(
            FeatureDiff(
                feature_index=int(fi),
                feature_name=str(name),
                mismatch_count=count,
                first_decision_index=di,
                first_case_index=ci,
                expected_value=ev,
                observed_value=ov,
                max_abs_diff=max_abs,
            )
        )
    return tuple(out)


def diagnose_events(events: np.ndarray, *, prefix_rows: int) -> LocalizationReport:
    a = r19._validate_event_surface(events)
    n = int(prefix_rows)
    if n != PREFIX_ROWS or n > int(a.size):
        raise R27P12Error("prefix_rows")
    prefix = a[:n]

    reference = r19.build_once_day_dense_feature_cache(
        prefix,
        nominal_day_start_local_ns=SOURCE_DAY_START_NS,
        nominal_day_end_exclusive_local_ns=SOURCE_DAY_END_EXCLUSIVE_NS,
    )

    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(prefix="dev045_r27p12_diag_") as root:
        candidate, _changed = r27p11.build_amended_fused_day_context(
            prefix,
            nominal_day_start_local_ns=SOURCE_DAY_START_NS,
            nominal_day_end_exclusive_local_ns=SOURCE_DAY_END_EXCLUSIVE_NS,
            scratch_root=Path(root),
        )
        try:
            if not np.array_equal(reference.cache.decision_local_ns, candidate.feature_cache.decision_local_ns):
                raise R27P12Error("decision_local_ns")
            if not np.array_equal(reference.cache.best_bid_tick, candidate.feature_cache.best_bid_tick):
                raise R27P12Error("best_bid_tick")
            if not np.array_equal(reference.cache.best_ask_tick, candidate.feature_cache.best_ask_tick):
                raise R27P12Error("best_ask_tick")
            diffs = localize_values(reference.cache.values, candidate.feature_cache.values)
        finally:
            if not candidate.midpoint_index.closed:
                from multimarket import dev045_d6r26a_p2_r20_combined_day_context_midpoint_index_preexecution as r20
                r20.close_midpoint_index(candidate.midpoint_index)

    mismatching = tuple(item.feature_name for item in diffs if item.mismatch_count)
    total = int(sum(item.mismatch_count for item in diffs))
    return LocalizationReport(
        prefix_rows=n,
        decision_count=int(reference.cache.decision_local_ns.size),
        leading_preeligible_count=int(reference.summary.leading_preeligible_count),
        feature_diffs=diffs,
        mismatching_features=mismatching,
        total_mismatch_cells=total,
    )


def run_real_localization(*, environ: dict[str, str] | None = None) -> LocalizationReport:
    validate_r27p12_contract()
    _require_authorized(environ)
    r27p2._validate_preattempt_state()
    events = r27p2._verify_source_identity()
    try:
        if bool(events.flags.writeable):
            raise R27P12Error("source_writeable")
        report = diagnose_events(events, prefix_rows=PREFIX_ROWS)
    finally:
        mm = getattr(events, "_mmap", None)
        if mm is not None:
            mm.close()

    print(f"R27P12_SOURCE_IDENTITY=PASS DAY={SOURCE_DAY} ROWS={SOURCE_ROWS} BYTES={SOURCE_BYTES} SHA256={SOURCE_SHA256}")
    print(f"R27P12_PREFIX_ROWS={report.prefix_rows}")
    print(f"R27P12_DECISION_COUNT={report.decision_count}")
    print(f"R27P12_LEADING_PREELIGIBLE={report.leading_preeligible_count}")
    for item in report.feature_diffs:
        print(
            f"R27P12_FEATURE_INDEX={item.feature_index} FEATURE={item.feature_name} "
            f"MISMATCH_COUNT={item.mismatch_count} FIRST_DECISION_INDEX={item.first_decision_index} "
            f"FIRST_CASE_INDEX={item.first_case_index} EXPECTED={item.expected_value!r} "
            f"OBSERVED={item.observed_value!r} MAX_ABS_DIFF={item.max_abs_diff!r}"
        )
    print(f"R27P12_MISMATCHING_FEATURES={report.mismatching_features}")
    print(f"R27P12_TOTAL_MISMATCH_CELLS={report.total_mismatch_cells}")
    print("R27P12_TIMING_PERFORMED=NO")
    print("R27P12_SPEED_GATE_RUN=NO")
    print("R27P11_RERUN=NO")
    print("BENCHMARK_MANIFEST_WRITTEN=NO")
    print("P2_ATTEMPT_CONSUMED=NO")
    print("FULL_JAN_JUL_RERUN=NO")
    print("SIMULATOR_RUN=NO")
    print("MODEL_FIT=NO")
    print("PNL=NO")
    print("MARKET_RAW_ARCHIVE_OPENED=NO")
    return report


def validate_r27p12_contract() -> None:
    r27p11.validate_r27p11_contract()
    if PARENT_R27P11_FAILURE_FREEZE_HEAD != "516ddc55c87f758eaf8d1137685acdec464fa5b3":
        raise R27P12Error("parent")
    if PREFIX_ROWS != 5_000_000:
        raise R27P12Error("prefix")
    required = (
        REAL_HISTORICAL_DIAGNOSTIC_AUTHORIZED,
        REAL_HISTORICAL_DIAGNOSTIC_REQUIRES_EXPLICIT_AUTHORIZATION,
        ONE_FROZEN_SOURCE_ONLY,
        PREFIX_ONLY,
        NO_TIMING,
        NO_SPEED_GATE,
        NO_BENCHMARK_MANIFEST,
        SOURCE_READ_ONLY_REQUIRED,
        not FULL_JAN_JUL_RERUN_AUTHORIZED,
        not DURABLE_CONTEXT_WRITE_AUTHORIZED,
        not MARKET_RAW_ARCHIVE_OPEN_AUTHORIZED,
    )
    if not all(required):
        raise R27P12Error("required_guard")
    forbidden = (
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
    )
    if any(forbidden):
        raise R27P12Error("execution_surface_open")


def main() -> int:
    try:
        run_real_localization()
    except Exception as exc:
        print(f"R27P12_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("R27P12_TIMING_PERFORMED=NO")
        print("R27P12_SPEED_GATE_RUN=NO")
        print("R27P11_RERUN=NO")
        print("P2_ATTEMPT_CONSUMED=NO")
        print("MARKET_RAW_ARCHIVE_OPENED=NO")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

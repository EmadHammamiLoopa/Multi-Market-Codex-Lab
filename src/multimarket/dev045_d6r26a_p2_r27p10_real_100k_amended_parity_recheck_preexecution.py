from __future__ import annotations

from dataclasses import dataclass
import os

import numpy as np

from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p8_real_prefix_parity_localization_preexecution as r27p8
from multimarket import dev045_d6r26a_p2_r27p9_cpython313_float_sum_parity_amendment as r27p9

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P10"
DESIGN_VERSION = "real-100k-amended-parity-recheck-preexecution-v1"
PARENT_R27P9_HEAD = "406841974817d03950b6cf0b15fb97676900b3b3"

AUTH_ENV = "DEV045_D6R26A_P2_R27P10_AUTHORIZE"
AUTH_TOKEN = "YES_REAL_100K_AMENDED_PARITY_RECHECK"

SOURCE_DAY = r27p8.SOURCE_DAY
SOURCE_PATH = r27p8.SOURCE_PATH
SOURCE_ROWS = r27p8.SOURCE_ROWS
SOURCE_BYTES = r27p8.SOURCE_BYTES
SOURCE_SHA256 = r27p8.SOURCE_SHA256
SOURCE_DAY_START_NS = r27p8.SOURCE_DAY_START_NS
SOURCE_DAY_END_EXCLUSIVE_NS = r27p8.SOURCE_DAY_END_EXCLUSIVE_NS
PREFIX_ROWS = 100_000

REAL_HISTORICAL_PARITY_RECHECK_AUTHORIZED = True
REAL_HISTORICAL_PARITY_RECHECK_REQUIRES_EXPLICIT_AUTHORIZATION = True
ONE_FROZEN_SOURCE_ONLY = True
PREFIX_ONLY = True
EXACT_PARITY_REQUIRED = True
CPYTHON313_SUM_AMENDMENT_REQUIRED = True
NO_TIMING = True
NO_SPEED_GATE = True
NO_MIDPOINT_BENCHMARK = True
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


class R27P10Error(RuntimeError):
    pass


@dataclass(frozen=True)
class ParityRecheckResult:
    prefix_rows: int
    decision_count: int
    leading_preeligible_count: int
    amendment_changed_cells: int
    amendment_changed_feature_indices: tuple[int, ...]
    exact_parity: bool


def real_recheck_authorized(environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(AUTH_ENV) == AUTH_TOKEN


def _require_real_recheck_authorized(environ: dict[str, str] | None = None) -> None:
    if not real_recheck_authorized(environ):
        raise R27P10Error("authorization")


def _compact_from_raw(raw: r27p6.FusedRawSurface) -> r27p5.CompactFeatureSurface:
    return r27p5.CompactFeatureSurface(
        book_local_ns=raw.book_local_ns,
        bid_ticks=raw.bid_ticks,
        bid_qty=raw.bid_qty,
        ask_ticks=raw.ask_ticks,
        ask_qty=raw.ask_qty,
        candidate_qty=raw.candidate_qty,
        flow_local_ns=raw.flow_local_ns,
        flow_code=raw.flow_code,
        flow_qty=raw.flow_qty,
    )


def recheck_events(
    events: np.ndarray,
    *,
    prefix_rows: int,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
    raw_kernel=None,
    base_feature_kernel=None,
    amendment_kernel=None,
) -> ParityRecheckResult:
    a = r19._validate_event_surface(events)
    n = int(prefix_rows)
    if n <= 0 or n > int(a.size) or n > PREFIX_ROWS:
        raise R27P10Error("prefix_rows")
    prefix = a[:n]

    bounds = r17.derive_feed_bounds(
        prefix,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
    )
    requested = np.asarray(r17.build_shared_decision_grid(bounds=bounds), dtype="<i8")
    if requested.size <= 0:
        raise R27P10Error("requested_decision_grid_empty")

    reference = r19.build_once_day_dense_feature_cache(
        prefix,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
    )

    raw_k = r27p6.build_fused_raw_kernel() if raw_kernel is None else raw_kernel
    base_k = r27p5.build_feature_kernel() if base_feature_kernel is None else base_feature_kernel
    amend_k = r27p9.build_l5_obi_amendment_kernel() if amendment_kernel is None else amendment_kernel

    fused_raw = r27p6.run_fused_raw_surface(prefix, kernel=raw_k)
    surface = _compact_from_raw(fused_raw)

    before = r27p5.run_compiled_feature_kernel(surface, requested, kernel=base_k)
    after = r27p9.run_amended_feature_kernel(
        surface,
        requested,
        base_kernel=base_k,
        amendment_kernel=amend_k,
    )
    audit = r27p9.audit_amendment(before, after)

    if not audit.other_feature_bytes_equal:
        raise R27P10Error("other_feature_bytes_changed")
    if any(index != r27p9.AMENDED_FEATURE_INDEX for index in audit.changed_feature_indices):
        raise R27P10Error("amendment_scope")
    if after.leading_preeligible_count != reference.summary.leading_preeligible_count:
        raise R27P10Error("leading_preeligible_count")

    pairs = (
        ("decision_local_ns", reference.cache.decision_local_ns, after.decision_local_ns),
        ("best_bid_tick", reference.cache.best_bid_tick, after.best_bid_tick),
        ("best_ask_tick", reference.cache.best_ask_tick, after.best_ask_tick),
        ("feature_values", reference.cache.values, after.values),
    )
    for name, expected, observed in pairs:
        if expected.dtype != observed.dtype:
            raise R27P10Error(f"{name}_dtype")
        if expected.shape != observed.shape:
            raise R27P10Error(f"{name}_shape")
        if not np.array_equal(expected, observed):
            mismatch = np.argwhere(np.not_equal(expected, observed))
            first = tuple(int(x) for x in mismatch[0]) if mismatch.size else None
            raise R27P10Error(f"{name}_values:first={first}:count={int(mismatch.shape[0])}")

    return ParityRecheckResult(
        prefix_rows=n,
        decision_count=int(after.decision_local_ns.size),
        leading_preeligible_count=int(after.leading_preeligible_count),
        amendment_changed_cells=int(audit.changed_cells),
        amendment_changed_feature_indices=audit.changed_feature_indices,
        exact_parity=True,
    )


def run_real_recheck(*, environ: dict[str, str] | None = None) -> ParityRecheckResult:
    validate_r27p10_contract()
    _require_real_recheck_authorized(environ)
    r27p2._validate_preattempt_state()
    events = r27p2._verify_source_identity()
    try:
        if bool(events.flags.writeable):
            raise R27P10Error("source_writeable")
        result = recheck_events(
            events,
            prefix_rows=PREFIX_ROWS,
            nominal_day_start_local_ns=SOURCE_DAY_START_NS,
            nominal_day_end_exclusive_local_ns=SOURCE_DAY_END_EXCLUSIVE_NS,
        )
    finally:
        mm = getattr(events, "_mmap", None)
        if mm is not None:
            mm.close()

    print(
        f"R27P10_SOURCE_IDENTITY=PASS DAY={SOURCE_DAY} ROWS={SOURCE_ROWS} "
        f"BYTES={SOURCE_BYTES} SHA256={SOURCE_SHA256}"
    )
    print(f"R27P10_PREFIX_ROWS={result.prefix_rows}")
    print(f"R27P10_DECISION_COUNT={result.decision_count}")
    print(f"R27P10_LEADING_PREELIGIBLE={result.leading_preeligible_count}")
    print(f"R27P10_AMENDMENT_CHANGED_CELLS={result.amendment_changed_cells}")
    print(f"R27P10_AMENDMENT_FEATURE_INDICES={result.amendment_changed_feature_indices}")
    print("R27P10_EXACT_FEATURE_PARITY=PASS")
    print("R27P10_TIMING_PERFORMED=NO")
    print("R27P10_SPEED_GATE_RUN=NO")
    print("R27P7_RERUN=NO")
    print("BENCHMARK_MANIFEST_WRITTEN=NO")
    print("P2_ATTEMPT_CONSUMED=NO")
    print("FULL_JAN_JUL_RERUN=NO")
    print("SIMULATOR_RUN=NO")
    print("MODEL_FIT=NO")
    print("PNL=NO")
    return result


def validate_r27p10_contract() -> None:
    r27p9.validate_r27p9_contract()
    if PARENT_R27P9_HEAD != "406841974817d03950b6cf0b15fb97676900b3b3":
        raise R27P10Error("parent")
    if PREFIX_ROWS != r27p8.DIAGNOSTIC_PREFIX_ROWS or PREFIX_ROWS != 100_000:
        raise R27P10Error("prefix_identity")
    if (
        SOURCE_DAY != r27p8.SOURCE_DAY
        or SOURCE_PATH != r27p8.SOURCE_PATH
        or SOURCE_ROWS != r27p8.SOURCE_ROWS
        or SOURCE_BYTES != r27p8.SOURCE_BYTES
        or SOURCE_SHA256 != r27p8.SOURCE_SHA256
    ):
        raise R27P10Error("source_identity")
    required = (
        REAL_HISTORICAL_PARITY_RECHECK_AUTHORIZED,
        REAL_HISTORICAL_PARITY_RECHECK_REQUIRES_EXPLICIT_AUTHORIZATION,
        ONE_FROZEN_SOURCE_ONLY,
        PREFIX_ONLY,
        EXACT_PARITY_REQUIRED,
        CPYTHON313_SUM_AMENDMENT_REQUIRED,
        NO_TIMING,
        NO_SPEED_GATE,
        NO_MIDPOINT_BENCHMARK,
        NO_BENCHMARK_MANIFEST,
        SOURCE_READ_ONLY_REQUIRED,
        not FULL_JAN_JUL_RERUN_AUTHORIZED,
        not DURABLE_CONTEXT_WRITE_AUTHORIZED,
    )
    if not all(required):
        raise R27P10Error("required_guard")
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
        raise R27P10Error("execution_surface_open")


def main() -> int:
    try:
        run_real_recheck()
    except Exception as exc:
        print(f"R27P10_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("R27P10_TIMING_PERFORMED=NO")
        print("R27P10_SPEED_GATE_RUN=NO")
        print("R27P7_RERUN=NO")
        print("BENCHMARK_MANIFEST_WRITTEN=NO")
        print("P2_ATTEMPT_CONSUMED=NO")
        print("FULL_JAN_JUL_RERUN=NO")
        print("SIMULATOR_RUN=NO")
        print("MODEL_FIT=NO")
        print("PNL=NO")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AUTH_ENV",
    "AUTH_TOKEN",
    "PREFIX_ROWS",
    "ParityRecheckResult",
    "real_recheck_authorized",
    "recheck_events",
    "run_real_recheck",
    "validate_r27p10_contract",
]

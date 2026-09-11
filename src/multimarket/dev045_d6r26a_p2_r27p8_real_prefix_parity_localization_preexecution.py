from __future__ import annotations

from dataclasses import dataclass
import os

import numpy as np

from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b
from multimarket import dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17
from multimarket import dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19
from multimarket import dev045_d6r26a_p2_r27p2_bounded_real_numba_benchmark_preexecution as r27p2
from multimarket import dev045_d6r26a_p2_r27p5_compiled_rolling_feature_kernel_preexecution as r27p5
from multimarket import dev045_d6r26a_p2_r27p6_full_context_fusion_synthetic_parity as r27p6
from multimarket import dev045_d6r26a_p2_r27p7_bounded_real_full_context_benchmark_preexecution as r27p7

EXPERIMENT_ID = "DEV045-D6R26A-P2-R27P8"
DESIGN_VERSION = "real-prefix-parity-localization-preexecution-v1"
PARENT_R27P7_HEAD = "fdc64fa92cf2d955ac8ecd127594f77de1b89bea"

AUTH_ENV = "DEV045_D6R26A_P2_R27P8_AUTHORIZE"
AUTH_TOKEN = "YES_REAL_100K_PARITY_LOCALIZATION"

SOURCE_DAY = r27p7.SOURCE_DAY
SOURCE_PATH = r27p7.SOURCE_PATH
SOURCE_ROWS = r27p7.SOURCE_ROWS
SOURCE_BYTES = r27p7.SOURCE_BYTES
SOURCE_SHA256 = r27p7.SOURCE_SHA256
SOURCE_DAY_START_NS = r27p7.SOURCE_DAY_START_NS
SOURCE_DAY_END_EXCLUSIVE_NS = r27p7.SOURCE_DAY_END_EXCLUSIVE_NS
DIAGNOSTIC_PREFIX_ROWS = 100_000

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


class R27P8Error(RuntimeError):
    pass


@dataclass(frozen=True)
class ArrayDiff:
    name: str
    equal: bool
    expected_dtype: str
    observed_dtype: str
    expected_shape: tuple[int, ...]
    observed_shape: tuple[int, ...]
    mismatch_count: int
    first_index: tuple[int, ...] | None
    expected_value: object | None
    observed_value: object | None
    feature_name: str | None


@dataclass(frozen=True)
class LocalizationReport:
    prefix_rows: int
    surface: tuple[ArrayDiff, ...]
    reference_surface_kernel: tuple[ArrayDiff, ...]
    fused_surface_kernel: tuple[ArrayDiff, ...]
    reference_leading_preeligible: int
    compiled_reference_leading_preeligible: int
    compiled_fused_leading_preeligible: int
    root_layer: str


def real_diagnostic_authorized(environ: dict[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    return env.get(AUTH_ENV) == AUTH_TOKEN


def _require_real_diagnostic_authorized(environ: dict[str, str] | None = None) -> None:
    if not real_diagnostic_authorized(environ):
        raise R27P8Error("authorization")


def _python_scalar(value):
    return value.item() if isinstance(value, np.generic) else value


def compare_array(name: str, expected: np.ndarray, observed: np.ndarray) -> ArrayDiff:
    a = np.asarray(expected)
    b = np.asarray(observed)
    dtype_equal = a.dtype == b.dtype
    shape_equal = a.shape == b.shape
    if not dtype_equal or not shape_equal:
        return ArrayDiff(
            name=name,
            equal=False,
            expected_dtype=str(a.dtype),
            observed_dtype=str(b.dtype),
            expected_shape=tuple(int(x) for x in a.shape),
            observed_shape=tuple(int(x) for x in b.shape),
            mismatch_count=-1,
            first_index=None,
            expected_value=None,
            observed_value=None,
            feature_name=None,
        )
    if np.array_equal(a, b):
        return ArrayDiff(
            name=name,
            equal=True,
            expected_dtype=str(a.dtype),
            observed_dtype=str(b.dtype),
            expected_shape=tuple(int(x) for x in a.shape),
            observed_shape=tuple(int(x) for x in b.shape),
            mismatch_count=0,
            first_index=None,
            expected_value=None,
            observed_value=None,
            feature_name=None,
        )
    mismatch = np.not_equal(a, b)
    coords = np.argwhere(mismatch)
    first = tuple(int(x) for x in coords[0])
    feature_name = None
    if a.ndim == 3 and len(first) == 3 and 0 <= first[2] < len(r8b.FEATURE_NAMES):
        feature_name = str(r8b.FEATURE_NAMES[first[2]])
    return ArrayDiff(
        name=name,
        equal=False,
        expected_dtype=str(a.dtype),
        observed_dtype=str(b.dtype),
        expected_shape=tuple(int(x) for x in a.shape),
        observed_shape=tuple(int(x) for x in b.shape),
        mismatch_count=int(np.count_nonzero(mismatch)),
        first_index=first,
        expected_value=_python_scalar(a[first]),
        observed_value=_python_scalar(b[first]),
        feature_name=feature_name,
    )


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


def _surface_diffs(
    expected: r27p5.CompactFeatureSurface,
    observed: r27p5.CompactFeatureSurface,
) -> tuple[ArrayDiff, ...]:
    names = (
        "book_local_ns",
        "bid_ticks",
        "bid_qty",
        "ask_ticks",
        "ask_qty",
        "candidate_qty",
        "flow_local_ns",
        "flow_code",
        "flow_qty",
    )
    return tuple(compare_array(name, getattr(expected, name), getattr(observed, name)) for name in names)


def _feature_diffs(reference, compiled, *, label: str) -> tuple[ArrayDiff, ...]:
    cache = reference.cache
    return (
        compare_array(f"{label}:decision_local_ns", cache.decision_local_ns, compiled.decision_local_ns),
        compare_array(f"{label}:best_bid_tick", cache.best_bid_tick, compiled.best_bid_tick),
        compare_array(f"{label}:best_ask_tick", cache.best_ask_tick, compiled.best_ask_tick),
        compare_array(f"{label}:feature_values", cache.values, compiled.values),
    )


def diagnose_events(
    events: np.ndarray,
    *,
    prefix_rows: int,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
    raw_kernel=None,
    feature_kernel=None,
) -> LocalizationReport:
    a = r19._validate_event_surface(events)
    n = int(prefix_rows)
    if n <= 0 or n > int(a.size) or n > DIAGNOSTIC_PREFIX_ROWS:
        raise R27P8Error("prefix_rows")
    prefix = a[:n]

    bounds = r17.derive_feed_bounds(
        prefix,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
    )
    requested = np.asarray(r17.build_shared_decision_grid(bounds=bounds), dtype="<i8")
    if requested.size <= 0:
        raise R27P8Error("requested_decision_grid_empty")

    reference = r19.build_once_day_dense_feature_cache(
        prefix,
        nominal_day_start_local_ns=int(nominal_day_start_local_ns),
        nominal_day_end_exclusive_local_ns=int(nominal_day_end_exclusive_local_ns),
    )
    reference_surface = r27p5.build_compact_reference_surface(prefix)

    raw_k = r27p6.build_fused_raw_kernel() if raw_kernel is None else raw_kernel
    feature_k = r27p5.build_feature_kernel() if feature_kernel is None else feature_kernel
    fused_raw = r27p6.run_fused_raw_surface(prefix, kernel=raw_k)
    fused_surface = _compact_from_raw(fused_raw)

    surface = _surface_diffs(reference_surface, fused_surface)
    compiled_reference = r27p5.run_compiled_feature_kernel(
        reference_surface,
        requested,
        kernel=feature_k,
    )
    compiled_fused = r27p5.run_compiled_feature_kernel(
        fused_surface,
        requested,
        kernel=feature_k,
    )

    reference_surface_kernel = _feature_diffs(
        reference,
        compiled_reference,
        label="reference_surface_kernel",
    )
    fused_surface_kernel = _feature_diffs(
        reference,
        compiled_fused,
        label="fused_surface_kernel",
    )

    if any(not item.equal for item in surface):
        root_layer = "RAW_SURFACE"
    elif any(not item.equal for item in reference_surface_kernel):
        root_layer = "FEATURE_KERNEL"
    elif any(not item.equal for item in fused_surface_kernel):
        root_layer = "FUSION_INTERFACE"
    else:
        root_layer = "NOT_REPRODUCED"

    return LocalizationReport(
        prefix_rows=n,
        surface=surface,
        reference_surface_kernel=reference_surface_kernel,
        fused_surface_kernel=fused_surface_kernel,
        reference_leading_preeligible=int(reference.summary.leading_preeligible_count),
        compiled_reference_leading_preeligible=int(compiled_reference.leading_preeligible_count),
        compiled_fused_leading_preeligible=int(compiled_fused.leading_preeligible_count),
        root_layer=root_layer,
    )


def _print_diff(group: str, item: ArrayDiff) -> None:
    print(
        f"R27P8_GROUP={group} NAME={item.name} EQUAL={'YES' if item.equal else 'NO'} "
        f"MISMATCH_COUNT={item.mismatch_count} FIRST_INDEX={item.first_index} "
        f"FEATURE={item.feature_name} EXPECTED={item.expected_value!r} OBSERVED={item.observed_value!r} "
        f"EXPECTED_DTYPE={item.expected_dtype} OBSERVED_DTYPE={item.observed_dtype} "
        f"EXPECTED_SHAPE={item.expected_shape} OBSERVED_SHAPE={item.observed_shape}"
    )


def run_real_localization(*, environ: dict[str, str] | None = None) -> LocalizationReport:
    validate_r27p8_contract()
    _require_real_diagnostic_authorized(environ)
    r27p2._validate_preattempt_state()
    events = r27p2._verify_source_identity()
    try:
        if bool(events.flags.writeable):
            raise R27P8Error("source_writeable")
        report = diagnose_events(
            events,
            prefix_rows=DIAGNOSTIC_PREFIX_ROWS,
            nominal_day_start_local_ns=SOURCE_DAY_START_NS,
            nominal_day_end_exclusive_local_ns=SOURCE_DAY_END_EXCLUSIVE_NS,
        )
    finally:
        mm = getattr(events, "_mmap", None)
        if mm is not None:
            mm.close()

    print(
        f"R27P8_SOURCE_IDENTITY=PASS DAY={SOURCE_DAY} ROWS={SOURCE_ROWS} "
        f"BYTES={SOURCE_BYTES} SHA256={SOURCE_SHA256}"
    )
    print(f"R27P8_PREFIX_ROWS={report.prefix_rows}")
    print(f"R27P8_REFERENCE_LEADING_PREELIGIBLE={report.reference_leading_preeligible}")
    print(f"R27P8_COMPILED_REFERENCE_LEADING_PREELIGIBLE={report.compiled_reference_leading_preeligible}")
    print(f"R27P8_COMPILED_FUSED_LEADING_PREELIGIBLE={report.compiled_fused_leading_preeligible}")
    for item in report.surface:
        _print_diff("RAW_SURFACE", item)
    for item in report.reference_surface_kernel:
        _print_diff("REFERENCE_SURFACE_KERNEL", item)
    for item in report.fused_surface_kernel:
        _print_diff("FUSED_SURFACE_KERNEL", item)
    print(f"R27P8_ROOT_LAYER={report.root_layer}")
    print("R27P8_TIMING_PERFORMED=NO")
    print("BENCHMARK_MANIFEST_WRITTEN=NO")
    print("P2_ATTEMPT_CONSUMED=NO")
    print("FULL_JAN_JUL_RERUN=NO")
    print("SIMULATOR_RUN=NO")
    print("MODEL_FIT=NO")
    print("PNL=NO")
    return report


def validate_r27p8_contract() -> None:
    r27p7.validate_r27p7_contract()
    if PARENT_R27P7_HEAD != "fdc64fa92cf2d955ac8ecd127594f77de1b89bea":
        raise R27P8Error("parent")
    if DIAGNOSTIC_PREFIX_ROWS != r27p7.PREFIX_ROWS[0] or DIAGNOSTIC_PREFIX_ROWS != 100_000:
        raise R27P8Error("diagnostic_prefix")
    if (
        SOURCE_DAY != r27p7.SOURCE_DAY
        or SOURCE_PATH != r27p7.SOURCE_PATH
        or SOURCE_ROWS != r27p7.SOURCE_ROWS
        or SOURCE_BYTES != r27p7.SOURCE_BYTES
        or SOURCE_SHA256 != r27p7.SOURCE_SHA256
    ):
        raise R27P8Error("source_identity")

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
    )
    if not all(required):
        raise R27P8Error("required_guard")

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
        raise R27P8Error("execution_surface_open")


def main() -> int:
    try:
        run_real_localization()
    except Exception as exc:
        print(f"R27P8_RESULT=FAIL TYPE={type(exc).__name__} REASON={exc}")
        print("R27P8_TIMING_PERFORMED=NO")
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
    "ArrayDiff",
    "DIAGNOSTIC_PREFIX_ROWS",
    "LocalizationReport",
    "compare_array",
    "diagnose_events",
    "real_diagnostic_authorized",
    "run_real_localization",
    "validate_r27p8_contract",
]

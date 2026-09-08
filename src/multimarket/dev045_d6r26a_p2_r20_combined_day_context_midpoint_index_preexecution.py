from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path

import numpy as np

from multimarket import (
    dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0,
)
from multimarket import (
    dev045_d6r26a_p1_synthetic_candidate_labeler as p1,
)
from multimarket import (
    dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b,
)
from multimarket import (
    dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9,
)
from multimarket import (
    dev045_d6r26a_p2_r10_bounded_feature_accumulator_freeze as r10,
)
from multimarket import (
    dev045_d6r26a_p2_r13_streaming_raw_decoder_preexecution as r13,
)
from multimarket import (
    dev045_d6r26a_p2_r13a_dual_stream_eof_memory_amendment as r13a,
)
from multimarket import (
    dev045_d6r26a_p2_r17_feed_bound_shared_feature_cache_preexecution as r17,
)
from multimarket import (
    dev045_d6r26a_p2_r18_generic_lane_materializer_integration_preexecution as r18,
)
from multimarket import (
    dev045_d6r26a_p2_r19_once_day_dense_feature_cache_builder_preexecution as r19,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R20"
DESIGN_VERSION = "combined-day-context-midpoint-index-preexecution-v1"
PARENT_R19_HEAD = "7a86630e5662e1ae6c7dc47f77836d31cb7d0a95"

COMBINED_ONCE_DAY_CONTEXT_BUILDER_FROZEN = True
R19_FEATURE_CACHE_SEMANTICS_BOUND = True
R13A_EXCHANGE_STREAM_SEMANTICS_BOUND = True
R18_DENSE_CACHE_CONSUMER_BOUND = True

# One Python raw-event pass builds BOTH surfaces.
COMBINED_RAW_EVENT_PASSES_PER_DAY = 1
SECOND_RAW_PASS_FOR_MIDPOINTS_FORBIDDEN = True
PER_LANE_RAW_MIDPOINT_RESCAN_FORBIDDEN = True
PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN = True

MIDPOINT_INDEX_FILE_BACKED = True
MIDPOINT_HISTORY_PYTHON_OBJECT_MATERIALIZATION_FORBIDDEN = True

MIDPOINT_RECORD_DTYPE = np.dtype(
    [
        ("exchange_ns", "<i8"),
        ("mid_tick_sum", "<i8"),
    ]
)
MIDPOINT_RECORD_BYTES = 16
MIDPOINT_BUFFER_ROWS = 65_536
MIDPOINT_BUFFER_MAX_BYTES = (
    MIDPOINT_BUFFER_ROWS * MIDPOINT_RECORD_BYTES
)

# The exact p1 markout query contract.
MARKOUT_MID_ASOF_RULE = (
    "LAST_BBO_MID_WITH_EXCHANGE_TS_LE_TARGET"
)

P2_ATTEMPT_CONSUMED = False

PREEXECUTION_ONLY = True
HISTORICAL_FILE_IO_AUTHORIZED = False
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_CANDIDATE_SIMULATION_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False


class CombinedDayContextError(RuntimeError):
    pass


@dataclass
class MidpointIndexHandle:
    path: Path
    records: np.memmap
    count: int
    bytes: int
    sha256: str
    source_exchange_observed_through_ns: int
    closed: bool = False


@dataclass(frozen=True)
class DayContextBuildResult:
    bounds: r17.FeedBounds
    feature_cache: r18.DenseFeatureCache
    feature_summary: r19.FeatureCacheBuildSummary
    midpoint_index: MidpointIndexHandle
    raw_event_pass_count: int


def _fsync_directory(path: Path) -> None:
    fd = os.open(
        Path(path),
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0),
    )

    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class _MidpointSpool:
    def __init__(
        self,
        *,
        scratch_root: Path,
        index_name: str,
    ) -> None:
        root = Path(scratch_root)

        if (
            not index_name
            or "/" in index_name
            or "\\" in index_name
            or index_name in (".", "..")
        ):
            raise CombinedDayContextError(
                "midpoint_index_name"
            )

        root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.final = root / index_name
        self.temp = root / (
            index_name + ".tmp"
        )

        if self.final.exists():
            raise CombinedDayContextError(
                f"midpoint_index_exists:{self.final}"
            )

        if self.temp.exists():
            raise CombinedDayContextError(
                f"midpoint_temp_exists:{self.temp}"
            )

        self.handle = self.temp.open("xb")

        self.buffer = np.empty(
            MIDPOINT_BUFFER_ROWS,
            dtype=MIDPOINT_RECORD_DTYPE,
        )

        self.used = 0
        self.count = 0
        self.last_exchange_ns = -1
        self.digest = hashlib.sha256()
        self.finished = False

    def _flush(self) -> None:
        if self.used <= 0:
            return

        raw = self.buffer[
            : self.used
        ].tobytes(
            order="C"
        )

        self.handle.write(raw)
        self.digest.update(raw)

        self.count += self.used
        self.used = 0

    def append(
        self,
        midpoint: p1.MidObservation,
    ) -> None:
        if self.finished:
            raise CombinedDayContextError(
                "midpoint_append_after_finish"
            )

        exchange_ns = int(
            midpoint.exchange_ns
        )

        if exchange_ns <= self.last_exchange_ns:
            raise CombinedDayContextError(
                "midpoint_exchange_not_strict"
            )

        mid_tick_sum = (
            int(midpoint.best_bid_tick)
            + int(midpoint.best_ask_tick)
        )

        if mid_tick_sum <= 0:
            raise CombinedDayContextError(
                "midpoint_tick_sum"
            )

        self.buffer[self.used][
            "exchange_ns"
        ] = exchange_ns

        self.buffer[self.used][
            "mid_tick_sum"
        ] = mid_tick_sum

        self.used += 1
        self.last_exchange_ns = exchange_ns

        if self.used >= MIDPOINT_BUFFER_ROWS:
            self._flush()

    def finish(
        self,
        *,
        source_exchange_observed_through_ns: int,
    ) -> MidpointIndexHandle:
        if self.finished:
            raise CombinedDayContextError(
                "midpoint_finish_twice"
            )

        self.finished = True

        try:
            self._flush()

            if self.count <= 0:
                raise CombinedDayContextError(
                    "midpoint_index_empty"
                )

            observed_through = int(
                source_exchange_observed_through_ns
            )

            if (
                observed_through
                < self.last_exchange_ns
            ):
                raise CombinedDayContextError(
                    "midpoint_observed_through"
                )

            self.handle.flush()
            os.fsync(
                self.handle.fileno()
            )
            self.handle.close()

            expected_bytes = (
                self.count
                * MIDPOINT_RECORD_BYTES
            )

            if int(
                self.temp.stat().st_size
            ) != expected_bytes:
                raise CombinedDayContextError(
                    "midpoint_temp_bytes"
                )

            os.replace(
                self.temp,
                self.final,
            )

            _fsync_directory(
                self.final.parent
            )

            if int(
                self.final.stat().st_size
            ) != expected_bytes:
                raise CombinedDayContextError(
                    "midpoint_final_bytes"
                )

            records = np.memmap(
                self.final,
                dtype=MIDPOINT_RECORD_DTYPE,
                mode="r",
                shape=(self.count,),
            )

            if bool(
                records.flags.writeable
            ):
                raise CombinedDayContextError(
                    "midpoint_index_writeable"
                )

            if int(
                records[0]["exchange_ns"]
            ) < 0:
                raise CombinedDayContextError(
                    "midpoint_first_exchange"
                )

            if int(
                records[-1]["exchange_ns"]
            ) != self.last_exchange_ns:
                raise CombinedDayContextError(
                    "midpoint_last_exchange"
                )

            return MidpointIndexHandle(
                path=self.final,
                records=records,
                count=int(self.count),
                bytes=int(expected_bytes),
                sha256=self.digest.hexdigest(),
                source_exchange_observed_through_ns=(
                    observed_through
                ),
            )

        except Exception:
            try:
                if not self.handle.closed:
                    self.handle.close()
            finally:
                if self.temp.exists():
                    self.temp.unlink()
            raise

    def abort(self) -> None:
        if not self.handle.closed:
            self.handle.close()

        if self.temp.exists():
            self.temp.unlink()


def close_midpoint_index(
    index: MidpointIndexHandle,
    *,
    delete: bool = True,
) -> None:
    if index.closed:
        raise CombinedDayContextError(
            "midpoint_index_already_closed"
        )

    mm = getattr(
        index.records,
        "_mmap",
        None,
    )

    if mm is not None:
        mm.close()

    index.closed = True

    if delete and index.path.exists():
        index.path.unlink()
        _fsync_directory(
            index.path.parent
        )


def midpoint_asof(
    *,
    index: MidpointIndexHandle,
    target_exchange_ns: int,
) -> float | None:
    if index.closed:
        raise CombinedDayContextError(
            "midpoint_index_closed"
        )

    target = int(
        target_exchange_ns
    )

    if target < 0:
        raise CombinedDayContextError(
            "midpoint_target"
        )

    if (
        index.source_exchange_observed_through_ns
        < target
    ):
        return None

    if index.count <= 0:
        return None

    times = index.records[
        "exchange_ns"
    ]

    position = int(
        np.searchsorted(
            times,
            target,
            side="right",
        )
    ) - 1

    if position < 0:
        return None

    mid_tick_sum = int(
        index.records[
            position
        ]["mid_tick_sum"]
    )

    if mid_tick_sum <= 0:
        raise CombinedDayContextError(
            "midpoint_lookup_tick_sum"
        )

    return (
        0.5
        * float(mid_tick_sum)
        * float(p0.TICK_SIZE)
    )


def _freeze_cache_arrays(
    *,
    decisions: np.ndarray,
    bids: np.ndarray,
    asks: np.ndarray,
    values: np.ndarray,
) -> r18.DenseFeatureCache:
    decisions.setflags(
        write=False
    )
    bids.setflags(
        write=False
    )
    asks.setflags(
        write=False
    )
    values.setflags(
        write=False
    )

    cache = r18.DenseFeatureCache(
        decision_local_ns=decisions,
        best_bid_tick=bids,
        best_ask_tick=asks,
        values=values,
    )

    r18.validate_dense_feature_cache(
        cache
    )

    return cache


def build_once_day_context(
    events: np.ndarray,
    *,
    nominal_day_start_local_ns: int,
    nominal_day_end_exclusive_local_ns: int,
    scratch_root: Path,
    midpoint_index_name: str = (
        "exchange_midpoints.bin"
    ),
) -> DayContextBuildResult:
    """
    One and only one Python raw-event pass.

    The local branch produces the exact R19 eligible dense feature cache.
    The exchange branch simultaneously spools the exact R13A/R9 midpoint
    stream to a bounded-buffer file-backed index.
    """
    a = r19._validate_event_surface(
        events
    )

    bounds = r17.derive_feed_bounds(
        a,
        nominal_day_start_local_ns=int(
            nominal_day_start_local_ns
        ),
        nominal_day_end_exclusive_local_ns=int(
            nominal_day_end_exclusive_local_ns
        ),
    )

    requested = (
        r17.build_shared_decision_grid(
            bounds=bounds,
        )
    )

    if not requested:
        raise CombinedDayContextError(
            "requested_decision_grid_empty"
        )

    decoder = (
        r13a.DualStreamingDecoder()
    )
    accumulator = (
        r10.RollingFeatureAccumulator()
    )

    spool = _MidpointSpool(
        scratch_root=Path(
            scratch_root
        ),
        index_name=midpoint_index_name,
    )

    latest_book: (
        r8b.BookObservation | None
    ) = None

    requested_index = 0
    leading_preeligible = 0

    out_decisions: (
        np.ndarray | None
    ) = None
    out_bids: (
        np.ndarray | None
    ) = None
    out_asks: (
        np.ndarray | None
    ) = None
    out_values: (
        np.ndarray | None
    ) = None

    out_index = 0
    first_eligible_requested_index: (
        int | None
    ) = None

    source_exchange_observed_through_ns = -1

    def process_decision(
        decision: int,
    ) -> None:
        nonlocal leading_preeligible
        nonlocal out_decisions
        nonlocal out_bids
        nonlocal out_asks
        nonlocal out_values
        nonlocal out_index
        nonlocal first_eligible_requested_index

        if latest_book is None:
            if (
                first_eligible_requested_index
                is None
            ):
                leading_preeligible += 1
                return

            raise CombinedDayContextError(
                "book_missing_after_eligibility"
            )

        try:
            matrix = r19._case_matrix(
                accumulator=accumulator,
                latest_book=latest_book,
                decision_local_ns=int(
                    decision
                ),
            )

        except r10.BoundedFeatureAccumulatorError as exc:
            reason = str(exc)

            if (
                first_eligible_requested_index
                is None
                and reason
                in r19._ELIGIBILITY_ERRORS_BEFORE_FIRST_SUCCESS
            ):
                leading_preeligible += 1
                return

            raise CombinedDayContextError(
                "feature_failure_after_eligibility:"
                f"{decision}:{reason}"
            ) from exc

        if (
            first_eligible_requested_index
            is None
        ):
            first_eligible_requested_index = (
                requested_index
            )

            remaining = (
                len(requested)
                - first_eligible_requested_index
            )

            out_decisions = np.empty(
                remaining,
                dtype="<i8",
            )

            out_bids = np.empty(
                remaining,
                dtype="<i8",
            )

            out_asks = np.empty(
                remaining,
                dtype="<i8",
            )

            out_values = np.empty(
                (
                    remaining,
                    r18.CANDIDATE_GRID_CASE_COUNT,
                    len(r8b.FEATURE_NAMES),
                ),
                dtype=(
                    r17.FEATURE_CACHE_VALUE_DTYPE
                ),
            )

        assert out_decisions is not None
        assert out_bids is not None
        assert out_asks is not None
        assert out_values is not None

        out_decisions[
            out_index
        ] = int(decision)

        out_bids[
            out_index
        ] = int(
            latest_book.best_bid.price_tick
        )

        out_asks[
            out_index
        ] = int(
            latest_book.best_ask.price_tick
        )

        out_values[
            out_index,
            :,
            :,
        ] = matrix

        out_index += 1

    def process_before(
        local_ns: int,
    ) -> None:
        nonlocal requested_index

        while (
            requested_index
            < len(requested)
            and int(
                requested[
                    requested_index
                ]
            )
            < int(local_ns)
        ):
            process_decision(
                int(
                    requested[
                        requested_index
                    ]
                )
            )

            requested_index += 1

    def ingest_local_group(
        group: r13.LocalGroupEmission,
    ) -> None:
        nonlocal latest_book
        nonlocal requested_index

        process_before(
            int(group.local_ns)
        )

        r13.feed_group_to_accumulator(
            accumulator=accumulator,
            emission=group,
        )

        if group.books:
            latest_book = (
                group.books[-1]
            )

        if (
            requested_index
            < len(requested)
            and int(
                requested[
                    requested_index
                ]
            )
            == int(group.local_ns)
        ):
            process_decision(
                int(
                    requested[
                        requested_index
                    ]
                )
            )

            requested_index += 1

    try:
        # EXACTLY ONE full Python raw-event pass.
        for row in a:
            exchange_ns = int(
                row["exch_ts"]
            )

            if exchange_ns < 0:
                raise CombinedDayContextError(
                    "source_exchange_timestamp"
                )

            source_exchange_observed_through_ns = max(
                source_exchange_observed_through_ns,
                exchange_ns,
            )

            emitted = decoder.feed(
                row
            )

            for midpoint in (
                emitted.exchange_midpoints
            ):
                spool.append(
                    midpoint
                )

            for group in (
                emitted.local_groups
            ):
                ingest_local_group(
                    group
                )

        final = decoder.finish()

        for midpoint in (
            final.exchange_midpoints
        ):
            spool.append(
                midpoint
            )

        for group in (
            final.local_groups
        ):
            ingest_local_group(
                group
            )

        while (
            requested_index
            < len(requested)
        ):
            process_decision(
                int(
                    requested[
                        requested_index
                    ]
                )
            )

            requested_index += 1

        if (
            first_eligible_requested_index
            is None
        ):
            raise CombinedDayContextError(
                "no_eligible_feature_decision"
            )

        assert out_decisions is not None
        assert out_bids is not None
        assert out_asks is not None
        assert out_values is not None

        expected_eligible = (
            len(requested)
            - first_eligible_requested_index
        )

        if out_index != expected_eligible:
            raise CombinedDayContextError(
                f"eligible_count:"
                f"{out_index}:"
                f"{expected_eligible}"
            )

        expected_decisions = np.asarray(
            requested[
                first_eligible_requested_index:
            ],
            dtype="<i8",
        )

        if not np.array_equal(
            out_decisions,
            expected_decisions,
        ):
            raise CombinedDayContextError(
                "eligible_grid_identity"
            )

        if (
            leading_preeligible
            != first_eligible_requested_index
        ):
            raise CombinedDayContextError(
                "leading_preeligible_count"
            )

        cache = _freeze_cache_arrays(
            decisions=out_decisions,
            bids=out_bids,
            asks=out_asks,
            values=out_values,
        )

        summary = (
            r19.FeatureCacheBuildSummary(
                requested_decision_count=(
                    len(requested)
                ),
                leading_preeligible_count=(
                    leading_preeligible
                ),
                eligible_decision_count=(
                    cache.decision_count
                ),
                first_requested_local_ns=int(
                    requested[0]
                ),
                first_eligible_local_ns=int(
                    cache.decision_local_ns[0]
                ),
                last_eligible_local_ns=int(
                    cache.decision_local_ns[-1]
                ),
                raw_event_pass_count=1,
            )
        )

        midpoint_index = spool.finish(
            source_exchange_observed_through_ns=(
                source_exchange_observed_through_ns
            )
        )

        return DayContextBuildResult(
            bounds=bounds,
            feature_cache=cache,
            feature_summary=summary,
            midpoint_index=midpoint_index,
            raw_event_pass_count=1,
        )

    except Exception:
        spool.abort()
        raise


def make_synthetic_dual_context_fixture() -> np.ndarray:
    """
    Exact R19 local feature fixture with exchange-domain flags added.

    Adding EXCH_EVENT does not alter LOCAL_EVENT feature semantics.
    """
    data = (
        r19.make_synthetic_feature_fixture()
        .copy()
    )

    data["ev"] = (
        data["ev"]
        | np.uint64(
            r9.EXCH_EVENT
        )
    )

    return data


def validate_r20_contract() -> None:
    r13a.validate_r13a_contract()
    r17.validate_r17_contract()
    r18.validate_r18_contract()
    r19.validate_r19_contract()

    if PARENT_R19_HEAD != (
        "7a86630e5662e1ae6c7dc47f77836d31cb7d0a95"
    ):
        raise CombinedDayContextError(
            "parent"
        )

    if MIDPOINT_RECORD_DTYPE.itemsize != 16:
        raise CombinedDayContextError(
            "midpoint_record_itemsize"
        )

    if MIDPOINT_RECORD_BYTES != 16:
        raise CombinedDayContextError(
            "midpoint_record_bytes"
        )

    if (
        MIDPOINT_BUFFER_MAX_BYTES
        > 2 * 1024 * 1024
    ):
        raise CombinedDayContextError(
            "midpoint_buffer_bound"
        )

    if (
        MARKOUT_MID_ASOF_RULE
        != p1.MARKOUT_MID_ASOF_RULE
    ):
        raise CombinedDayContextError(
            "markout_mid_asof_rule"
        )

    required = (
        COMBINED_ONCE_DAY_CONTEXT_BUILDER_FROZEN,
        R19_FEATURE_CACHE_SEMANTICS_BOUND,
        R13A_EXCHANGE_STREAM_SEMANTICS_BOUND,
        R18_DENSE_CACHE_CONSUMER_BOUND,
        COMBINED_RAW_EVENT_PASSES_PER_DAY == 1,
        SECOND_RAW_PASS_FOR_MIDPOINTS_FORBIDDEN,
        PER_LANE_RAW_MIDPOINT_RESCAN_FORBIDDEN,
        PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN,
        MIDPOINT_INDEX_FILE_BACKED,
        MIDPOINT_HISTORY_PYTHON_OBJECT_MATERIALIZATION_FORBIDDEN,
        P2_ATTEMPT_CONSUMED is False,
        PREEXECUTION_ONLY,
        r19.RAW_EVENT_PASSES_PER_DAY == 1,
        r19.PER_LANE_RAW_FEATURE_RESCAN_FORBIDDEN,
        r17.FEATURE_CACHE_SHARED_ACROSS_ALL_40_LANES,
        r13a.FULL_HISTORY_MATERIALIZATION_IN_REAL_PATH_FORBIDDEN,
    )

    if not all(required):
        raise CombinedDayContextError(
            "required_guard"
        )

    required_r19_internal_surface = (
        "_validate_event_surface",
        "_case_matrix",
        "_ELIGIBILITY_ERRORS_BEFORE_FIRST_SUCCESS",
    )

    if not all(
        hasattr(r19, name)
        for name in required_r19_internal_surface
    ):
        raise CombinedDayContextError(
            "r19_internal_binding_surface"
        )

    forbidden = (
        HISTORICAL_FILE_IO_AUTHORIZED,
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_CANDIDATE_SIMULATION_AUTHORIZED,
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
        raise CombinedDayContextError(
            "execution_surface_open"
        )


__all__ = [
    "DayContextBuildResult",
    "MidpointIndexHandle",
    "build_once_day_context",
    "close_midpoint_index",
    "make_synthetic_dual_context_fixture",
    "midpoint_asof",
    "validate_r20_contract",
]

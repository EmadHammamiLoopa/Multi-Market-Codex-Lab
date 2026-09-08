from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np

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
    dev045_d6r26a_p2_r12_one_day_lane_driver_preexecution as r12,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R13"
DESIGN_VERSION = "streaming-raw-decoder-preexecution-v1"
PARENT_R12_HEAD = "2e6fcbb8c96dae386e548eb72e5e1ba7ed6e2e5d"
DATA_ROLE = "CONSUMED_DEVELOPMENT"

STREAMING_RAW_DECODER_PREEXECUTION_FROZEN = True
R9_EXACT_DECODER_SEMANTICS_BOUND = True
R10_BOUNDED_ACCUMULATOR_BOUND = True
LOCAL_GROUP_FINAL_POST_MARKET_BOOK_FIRST = True
FLOW_SOURCE_ORDER_WITHIN_LOCAL_GROUP = True
DECISION_AFTER_LOCAL_GROUP_FLUSH_REQUIRED = True

PREEXECUTION_ONLY = True
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


class StreamingRawDecoderError(RuntimeError):
    pass


@dataclass(frozen=True)
class LocalGroupEmission:
    local_ns: int
    books: tuple[r8b.BookObservation, ...]
    flows: tuple[r8b.FlowObservation, ...]


class LocalStreamingDecoder:
    """
    Bounded local-time decoder.

    It preserves the exact frozen R9 local-event semantics while emitting one
    completed local timestamp group at a time instead of materializing a
    full-day DecodedHistory object.

    A group is emitted only after all rows carrying that local timestamp have
    been consumed. The final post-market BookObservation is emitted before
    same-local-time FlowObservations so downstream R10 decisions can occur
    only after the complete local market group is visible.
    """

    def __init__(self) -> None:
        self._state = r9._BookState.empty()
        self._current_local: int | None = None
        self._group_exchange_max = 0
        self._group_market_changed = False
        self._group_flows: list[r8b.FlowObservation] = []
        self._last_local = -1
        self._finished = False

    def _drain_current(self) -> LocalGroupEmission | None:
        if self._current_local is None:
            return None

        books: tuple[r8b.BookObservation, ...] = ()

        if self._group_market_changed and self._state.valid():
            books = (
                self._state.observation(
                    local_ns=int(self._current_local),
                    exchange_ns=int(self._group_exchange_max),
                ),
            )

        emission = LocalGroupEmission(
            local_ns=int(self._current_local),
            books=books,
            flows=tuple(self._group_flows),
        )

        self._group_market_changed = False
        self._group_flows = []
        self._group_exchange_max = 0

        return emission

    def feed(self, row) -> tuple[LocalGroupEmission, ...]:
        if self._finished:
            raise StreamingRawDecoderError("feed_after_finish")

        ev = int(row["ev"])
        kind = r9._event_kind(ev)

        if kind not in r9.SUPPORTED_EVENT_TYPES:
            raise StreamingRawDecoderError(
                f"unknown_event_kind:{kind}"
            )

        # R9 local decoder ignores rows lacking LOCAL_EVENT.
        if not r9._has_flag(ev, r9.LOCAL_EVENT):
            return ()

        local_ns = int(row["local_ts"])
        exchange_ns = int(row["exch_ts"])

        if (
            local_ns < 0
            or exchange_ns < 0
            or local_ns < exchange_ns
        ):
            raise StreamingRawDecoderError("event_timestamp")

        if local_ns < self._last_local:
            raise StreamingRawDecoderError(
                "local_timestamp_regression"
            )

        emitted: list[LocalGroupEmission] = []

        if self._current_local is None:
            self._current_local = local_ns
        elif local_ns != self._current_local:
            previous = self._drain_current()
            if previous is not None:
                emitted.append(previous)
            self._current_local = local_ns

        self._last_local = local_ns
        self._group_exchange_max = max(
            int(self._group_exchange_max),
            exchange_ns,
        )

        if kind in (
            r9.DEPTH_EVENT,
            r9.DEPTH_CLEAR_EVENT,
            r9.DEPTH_SNAPSHOT_EVENT,
        ):
            flow = r9._process_depth_row(
                self._state,
                row,
                timestamp_domain="LOCAL",
                emit_flow=True,
            )

            if flow is not None:
                self._group_flows.append(flow)

            self._group_market_changed = True

        elif kind == r9.TRADE_EVENT:
            self._group_flows.append(
                r8b.trade_to_flow(
                    local_ns=local_ns,
                    exchange_ns=exchange_ns,
                    aggressor_side=r9._aggressor_side(ev),
                    qty=float(row["qty"]),
                )
            )

        elif kind in r9.IGNORED_L2_EVENT_TYPES:
            pass

        else:
            raise StreamingRawDecoderError(
                f"unsupported_local_kind:{kind}"
            )

        return tuple(emitted)

    def finish(self) -> tuple[LocalGroupEmission, ...]:
        if self._finished:
            raise StreamingRawDecoderError("finish_twice")

        self._finished = True

        final = self._drain_current()

        if final is None:
            return ()

        return (final,)


def iter_local_groups(
    events: np.ndarray,
) -> Iterator[LocalGroupEmission]:
    a = r9._validate_event_array(events)
    decoder = LocalStreamingDecoder()

    for row in a:
        yield from decoder.feed(row)

    yield from decoder.finish()


def decode_local_streaming(
    events: np.ndarray,
) -> r9.DecodedHistory:
    """
    Synthetic/reference parity helper.

    Real execution must consume iter_local_groups() incrementally instead of
    constructing this aggregate object. This helper exists only for CI parity
    against frozen R9.
    """
    books: list[r8b.BookObservation] = []
    flows: list[r8b.FlowObservation] = []

    for emission in iter_local_groups(events):
        books.extend(emission.books)
        flows.extend(emission.flows)

    r8b.validate_book_history(books)
    r8b.validate_flow_history(flows)

    return r9.DecodedHistory(
        books=tuple(books),
        flows=tuple(flows),
    )


def feed_group_to_accumulator(
    *,
    accumulator: r10.RollingFeatureAccumulator,
    emission: LocalGroupEmission,
) -> None:
    """
    Frozen downstream ordering for one completed local group.

    Final post-market book first, then source-order flows. Candidate decision
    may occur only after this function has completed for that local timestamp.
    """
    for book in emission.books:
        accumulator.ingest_book(book)

    for flow in emission.flows:
        accumulator.ingest_flow(flow)


def validate_r13_contract() -> None:
    r9.validate_r9_contract()
    r10.validate_r10_contract()
    r12.validate_r12_contract()

    if PARENT_R12_HEAD != (
        "2e6fcbb8c96dae386e548eb72e5e1ba7ed6e2e5d"
    ):
        raise StreamingRawDecoderError("parent")

    if DATA_ROLE != "CONSUMED_DEVELOPMENT":
        raise StreamingRawDecoderError("data_role")

    required = (
        STREAMING_RAW_DECODER_PREEXECUTION_FROZEN,
        R9_EXACT_DECODER_SEMANTICS_BOUND,
        R10_BOUNDED_ACCUMULATOR_BOUND,
        LOCAL_GROUP_FINAL_POST_MARKET_BOOK_FIRST,
        FLOW_SOURCE_ORDER_WITHIN_LOCAL_GROUP,
        DECISION_AFTER_LOCAL_GROUP_FLUSH_REQUIRED,
        PREEXECUTION_ONLY,
    )

    if not all(required):
        raise StreamingRawDecoderError("required_guard")

    # Bind directly to the exact frozen R9 parser surface rather than inventing
    # a second raw-event semantic definition.
    required_r9_symbols = (
        "_BookState",
        "_event_kind",
        "_has_flag",
        "_process_depth_row",
        "_aggressor_side",
        "_validate_event_array",
    )

    if not all(hasattr(r9, name) for name in required_r9_symbols):
        raise StreamingRawDecoderError("r9_binding_surface")

    forbidden = (
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
    )

    if any(forbidden):
        raise StreamingRawDecoderError(
            "execution_surface_open"
        )


__all__ = [
    "LocalGroupEmission",
    "LocalStreamingDecoder",
    "iter_local_groups",
    "decode_local_streaming",
    "feed_group_to_accumulator",
    "validate_r13_contract",
]

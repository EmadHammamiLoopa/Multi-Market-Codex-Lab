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
    dev045_d6r26a_p2_r13_streaming_raw_decoder_preexecution as r13,
)


EXPERIMENT_ID = "DEV045-D6R26A-P2-R13A"
DESIGN_VERSION = "dual-stream-eof-memory-amendment-v1"
PARENT_R13_HEAD = "88a423c295e197fcfec2a4e5e8ad08c086d19a88"

DUAL_STREAM_DECODER_AMENDMENT_FROZEN = True
LOCAL_STREAM_BOUND_TO_R13 = True
EXCHANGE_STREAM_BOUND_TO_R9 = True
R9_EXACT_DECODER_SEMANTICS_REQUIRED = True

# Historical D6R13/D6R14 anti-regression rules.
NATURAL_END_OF_SOURCE_IS_VALID_TERMINAL = True
FINAL_TIMESTAMP_GROUP_FLUSH_REQUIRED = True
FIXED_EVENT_TARGET = None
FIXED_WAKEUP_TARGET = None

# mmap/file-backed RSS is not evidence of owned-memory leakage.
TOTAL_RSS_ABORT_THRESHOLD_BYTES = None
TOTAL_RSS_IS_BOUNDEDNESS_GATE = False

# Streaming state may scale with the active L2 book and the current timestamp
# group, but must not scale with elapsed full-day output history.
INTERNAL_STATE_BOUND_TO_ACTIVE_BOOK_AND_CURRENT_GROUP = True
FULL_HISTORY_MATERIALIZATION_IN_REAL_PATH_FORBIDDEN = True
BATCH_PARITY_HELPERS_SYNTHETIC_ONLY = True

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


class DualStreamingDecoderError(RuntimeError):
    pass


class ExchangeStreamingDecoder:
    """
    Streaming exchange-time midpoint decoder.

    Exact semantic reference: R9.decode_exchange_midpoints().

    Unlike the R9 batch parity helper, this object never stores the complete
    midpoint series. It retains only the current L2 state and current exchange
    timestamp group and emits a completed midpoint incrementally.
    """

    def __init__(self) -> None:
        self._state = r9._BookState.empty()
        self._current_exchange: int | None = None
        self._group_changed = False
        self._last_exchange = -1
        self._finished = False

    def _drain_current(self) -> r8b.p1.MidObservation | None:
        if self._current_exchange is None:
            return None

        midpoint: r8b.p1.MidObservation | None = None

        if self._group_changed and self._state.valid():
            midpoint = r8b.p1.MidObservation(
                exchange_ns=int(self._current_exchange),
                best_bid_tick=max(self._state.bids),
                best_ask_tick=min(self._state.asks),
            )

        self._group_changed = False
        return midpoint

    def feed(self, row) -> tuple[r8b.p1.MidObservation, ...]:
        if self._finished:
            raise DualStreamingDecoderError("exchange_feed_after_finish")

        ev = int(row["ev"])
        kind = r9._event_kind(ev)

        # Match R9: unknown event types fail closed even if the row would
        # otherwise be ignored by timestamp-domain filtering.
        if kind not in r9.SUPPORTED_EVENT_TYPES:
            raise DualStreamingDecoderError(
                f"unknown_event_kind:{kind}"
            )

        if not r9._has_flag(ev, r9.EXCH_EVENT):
            return ()

        exchange_ns = int(row["exch_ts"])

        if exchange_ns < 0:
            raise DualStreamingDecoderError("exchange_timestamp")

        if exchange_ns < self._last_exchange:
            raise DualStreamingDecoderError(
                "exchange_timestamp_regression"
            )

        emitted: list[r8b.p1.MidObservation] = []

        if self._current_exchange is None:
            self._current_exchange = exchange_ns
        elif exchange_ns != self._current_exchange:
            previous = self._drain_current()
            if previous is not None:
                emitted.append(previous)
            self._current_exchange = exchange_ns

        self._last_exchange = exchange_ns

        if kind in (
            r9.DEPTH_EVENT,
            r9.DEPTH_CLEAR_EVENT,
            r9.DEPTH_SNAPSHOT_EVENT,
        ):
            r9._process_depth_row(
                self._state,
                row,
                timestamp_domain="EXCHANGE",
                emit_flow=False,
            )
            self._group_changed = True

        elif kind in (
            r9.TRADE_EVENT,
            *r9.IGNORED_L2_EVENT_TYPES,
        ):
            pass

        else:
            raise DualStreamingDecoderError(
                f"unsupported_exchange_kind:{kind}"
            )

        return tuple(emitted)

    def finish(self) -> tuple[r8b.p1.MidObservation, ...]:
        if self._finished:
            raise DualStreamingDecoderError("exchange_finish_twice")

        self._finished = True
        final = self._drain_current()

        if final is None:
            return ()

        return (final,)

    @property
    def active_level_count(self) -> int:
        return len(self._state.bids) + len(self._state.asks)


@dataclass(frozen=True)
class DualStreamEmission:
    local_groups: tuple[r13.LocalGroupEmission, ...]
    exchange_midpoints: tuple[r8b.p1.MidObservation, ...]


class DualStreamingDecoder:
    """
    One-pass bounded decoder for both local-feature and exchange-label streams.
    """

    def __init__(self) -> None:
        self.local = r13.LocalStreamingDecoder()
        self.exchange = ExchangeStreamingDecoder()
        self._finished = False

    def feed(self, row) -> DualStreamEmission:
        if self._finished:
            raise DualStreamingDecoderError("dual_feed_after_finish")

        local_groups = self.local.feed(row)
        exchange_midpoints = self.exchange.feed(row)

        return DualStreamEmission(
            local_groups=local_groups,
            exchange_midpoints=exchange_midpoints,
        )

    def finish(self) -> DualStreamEmission:
        if self._finished:
            raise DualStreamingDecoderError("dual_finish_twice")

        self._finished = True

        return DualStreamEmission(
            local_groups=self.local.finish(),
            exchange_midpoints=self.exchange.finish(),
        )


def iter_exchange_midpoints(
    events: np.ndarray,
) -> Iterator[r8b.p1.MidObservation]:
    a = r9._validate_event_array(events)
    decoder = ExchangeStreamingDecoder()

    for row in a:
        yield from decoder.feed(row)

    yield from decoder.finish()


def decode_exchange_streaming(
    events: np.ndarray,
) -> tuple[r8b.p1.MidObservation, ...]:
    """
    Synthetic CI parity helper only.

    Real historical execution must consume iter_exchange_midpoints()
    incrementally and must not materialize the full-day tuple.
    """
    return tuple(iter_exchange_midpoints(events))


def validate_r13a_contract() -> None:
    r9.validate_r9_contract()
    r13.validate_r13_contract()

    if PARENT_R13_HEAD != (
        "88a423c295e197fcfec2a4e5e8ad08c086d19a88"
    ):
        raise DualStreamingDecoderError("parent")

    required = (
        DUAL_STREAM_DECODER_AMENDMENT_FROZEN,
        LOCAL_STREAM_BOUND_TO_R13,
        EXCHANGE_STREAM_BOUND_TO_R9,
        R9_EXACT_DECODER_SEMANTICS_REQUIRED,
        NATURAL_END_OF_SOURCE_IS_VALID_TERMINAL,
        FINAL_TIMESTAMP_GROUP_FLUSH_REQUIRED,
        INTERNAL_STATE_BOUND_TO_ACTIVE_BOOK_AND_CURRENT_GROUP,
        FULL_HISTORY_MATERIALIZATION_IN_REAL_PATH_FORBIDDEN,
        BATCH_PARITY_HELPERS_SYNTHETIC_ONLY,
        PREEXECUTION_ONLY,
    )

    if not all(required):
        raise DualStreamingDecoderError("required_guard")

    if FIXED_EVENT_TARGET is not None:
        raise DualStreamingDecoderError("fixed_event_target")

    if FIXED_WAKEUP_TARGET is not None:
        raise DualStreamingDecoderError("fixed_wakeup_target")

    if TOTAL_RSS_ABORT_THRESHOLD_BYTES is not None:
        raise DualStreamingDecoderError("rss_threshold")

    if TOTAL_RSS_IS_BOUNDEDNESS_GATE:
        raise DualStreamingDecoderError("rss_boundedness_gate")

    if (
        r9.DECODER_DEFINITION_SHA256
        != "50ddc5f01872cb6155d7ea3f8adc8e040a95407249657e2c891859d4921fdd58"
    ):
        raise DualStreamingDecoderError("r9_semantic_identity")

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
        raise DualStreamingDecoderError("execution_surface_open")


__all__ = [
    "DualStreamEmission",
    "DualStreamingDecoder",
    "DualStreamingDecoderError",
    "ExchangeStreamingDecoder",
    "decode_exchange_streaming",
    "iter_exchange_midpoints",
    "validate_r13a_contract",
]

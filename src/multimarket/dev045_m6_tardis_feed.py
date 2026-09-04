from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import csv
import gzip
import math
import os
from pathlib import Path
from typing import Any

import numpy as np

from multimarket import dev045_m4_adapter as m4
from multimarket.dev045_m5_prereg import AUTHORIZED_DAYS
from multimarket.dev045_m6_economic_arena import SYMBOL
from multimarket.v23_phase0dl_audit import L2_HEADER, TRADES_HEADER


TARDIS_EXCHANGE = "binance-futures"
DEPTH_DATA_TYPE = "incremental_book_L2"
TRADES_DATA_TYPE = "trades"

# This module binds the already-frozen Phase0DL raw feed to the frozen
# hftbacktest 2.4.4 Tardis converter. It intentionally does not execute a
# policy, run the simulator, account PnL, or write a historical result.
HISTORICAL_REPLAY_EXECUTION_ENABLED = False
HISTORICAL_PNL_OUTPUT_ENABLED = False
NETWORK_ACQUISITION_ENABLED = False

_ALLOWED_SUFFIX = ".csv.gz"


class HistoricalFeedError(RuntimeError):
    pass


@dataclass(frozen=True)
class TardisFeedSpec:
    day: str
    raw_root: Path
    trades_path: Path
    depth_path: Path
    exchange: str = TARDIS_EXCHANGE
    symbol: str = SYMBOL


@dataclass(frozen=True)
class RawFileAudit:
    data_type: str
    rows: int
    snapshot_rows: int
    snapshot_batches: int
    max_snapshot_side_rows: int
    first_local_us: int
    last_local_us: int


@dataclass(frozen=True)
class FeedPreflight:
    spec: TardisFeedSpec
    trades: RawFileAudit
    depth: RawFileAudit
    converter_buffer_size: int
    snapshot_buffer_size: int


@dataclass(frozen=True)
class ConvertedDay:
    spec: TardisFeedSpec
    preflight: FeedPreflight
    data: Any


def _validate_day(day: str) -> str:
    value = str(day)
    if value not in AUTHORIZED_DAYS:
        raise HistoricalFeedError("authorized_day")
    return value


def _local_root(raw_root: str | os.PathLike[str]) -> Path:
    text = os.fspath(raw_root)
    if not text or not text.strip():
        raise HistoricalFeedError("raw_root")

    low = text.strip().lower()
    if "://" in low or low.startswith("\\\\"):
        raise HistoricalFeedError("network_or_url_root")

    return Path(text)


def make_feed_spec(
    raw_root: str | os.PathLike[str],
    day: str,
) -> TardisFeedSpec:
    frozen_day = _validate_day(day)
    root = _local_root(raw_root)

    trades = root / TRADES_DATA_TYPE / SYMBOL / f"{frozen_day}{_ALLOWED_SUFFIX}"
    depth = root / DEPTH_DATA_TYPE / SYMBOL / f"{frozen_day}{_ALLOWED_SUFFIX}"

    return TardisFeedSpec(
        day=frozen_day,
        raw_root=root,
        trades_path=trades,
        depth_path=depth,
    )


def _day_bounds_us(day: str) -> tuple[int, int]:
    dt = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    start = int(dt.timestamp() * 1_000_000)
    return start, start + 86_400_000_000


def _finite(name: str, value: str) -> float:
    try:
        x = float(value)
    except Exception as exc:
        raise HistoricalFeedError(name) from exc
    if not math.isfinite(x):
        raise HistoricalFeedError(name)
    return x


def _integer(name: str, value: str) -> int:
    try:
        return int(value)
    except Exception as exc:
        raise HistoricalFeedError(name) from exc


def _audit_file(
    path: Path,
    *,
    data_type: str,
    day: str,
) -> RawFileAudit:
    if data_type not in (TRADES_DATA_TYPE, DEPTH_DATA_TYPE):
        raise HistoricalFeedError("data_type")

    if path.suffixes[-2:] != [".csv", ".gz"]:
        raise HistoricalFeedError("file_suffix")

    if not path.is_file():
        raise HistoricalFeedError(f"missing_file:{data_type}")

    expected = TRADES_HEADER if data_type == TRADES_DATA_TYPE else L2_HEADER
    start_us, end_us = _day_bounds_us(day)

    rows = 0
    snapshot_rows = 0
    snapshot_batches = 0
    max_snapshot_side_rows = 0

    seen_snapshot = False
    prev_snapshot = False
    current_snapshot_bid_rows = 0
    current_snapshot_ask_rows = 0
    pre_snapshot_rows = 0

    first_local: int | None = None
    last_local: int | None = None
    prev_local: int | None = None

    try:
        fh = gzip.open(path, "rt", encoding="utf-8", newline="")
    except Exception as exc:
        raise HistoricalFeedError(f"open_failed:{data_type}") from exc

    with fh:
        reader = csv.reader(fh)
        try:
            header = tuple(next(reader))
        except StopIteration as exc:
            raise HistoricalFeedError(f"empty_file:{data_type}") from exc

        if header != expected:
            raise HistoricalFeedError(f"header_mismatch:{data_type}")

        pos = {name: i for i, name in enumerate(header)}

        for line_no, row in enumerate(reader, start=2):
            rows += 1

            if len(row) != len(header):
                raise HistoricalFeedError(
                    f"row_width:{data_type}:{line_no}"
                )

            if row[pos["exchange"]] != TARDIS_EXCHANGE:
                raise HistoricalFeedError(
                    f"exchange:{data_type}:{line_no}"
                )

            if row[pos["symbol"]] != SYMBOL:
                raise HistoricalFeedError(
                    f"symbol:{data_type}:{line_no}"
                )

            exch_us = _integer(
                f"timestamp:{data_type}:{line_no}",
                row[pos["timestamp"]],
            )
            local_us = _integer(
                f"local_timestamp:{data_type}:{line_no}",
                row[pos["local_timestamp"]],
            )

            if exch_us < 0 or local_us < 0:
                raise HistoricalFeedError(
                    f"negative_timestamp:{data_type}:{line_no}"
                )

            # M4 explicitly forbids negative feed latency. Do not allow the
            # upstream converter to repair it silently.
            if local_us < exch_us:
                raise HistoricalFeedError(
                    f"negative_feed_latency:{data_type}:{line_no}"
                )

            # Phase0DL daily files are scoped by message-arrival/local time.
            if local_us < start_us or local_us >= end_us:
                raise HistoricalFeedError(
                    f"local_timestamp_day:{data_type}:{line_no}"
                )

            if prev_local is not None and local_us < prev_local:
                raise HistoricalFeedError(
                    f"local_order:{data_type}:{line_no}"
                )
            prev_local = local_us

            price = _finite(
                f"price:{data_type}:{line_no}",
                row[pos["price"]],
            )
            amount = _finite(
                f"amount:{data_type}:{line_no}",
                row[pos["amount"]],
            )

            if price <= 0.0:
                raise HistoricalFeedError(
                    f"nonpositive_price:{data_type}:{line_no}"
                )

            side = row[pos["side"]].strip().lower()

            if data_type == TRADES_DATA_TYPE:
                # Tardis documents this as taker/aggressor side. Queue replay
                # cannot safely infer an unknown aggressor direction.
                if side not in ("buy", "sell"):
                    raise HistoricalFeedError(
                        f"trade_side:{line_no}"
                    )
                if amount <= 0.0:
                    raise HistoricalFeedError(
                        f"nonpositive_trade_amount:{line_no}"
                    )
            else:
                if side not in ("bid", "ask"):
                    raise HistoricalFeedError(
                        f"depth_side:{line_no}"
                    )
                if amount < 0.0:
                    raise HistoricalFeedError(
                        f"negative_depth_amount:{line_no}"
                    )

                snap_text = row[pos["is_snapshot"]].strip().lower()
                if snap_text not in ("true", "false"):
                    raise HistoricalFeedError(
                        f"is_snapshot:{line_no}"
                    )

                is_snapshot = snap_text == "true"

                if is_snapshot:
                    snapshot_rows += 1

                    if not prev_snapshot:
                        snapshot_batches += 1
                        current_snapshot_bid_rows = 0
                        current_snapshot_ask_rows = 0

                    seen_snapshot = True

                    if side == "bid":
                        current_snapshot_bid_rows += 1
                    else:
                        current_snapshot_ask_rows += 1

                    max_snapshot_side_rows = max(
                        max_snapshot_side_rows,
                        current_snapshot_bid_rows,
                        current_snapshot_ask_rows,
                    )
                else:
                    if not seen_snapshot:
                        pre_snapshot_rows += 1
                    current_snapshot_bid_rows = 0
                    current_snapshot_ask_rows = 0

                prev_snapshot = is_snapshot

            if first_local is None:
                first_local = local_us
            last_local = local_us

    if rows == 0 or first_local is None or last_local is None:
        raise HistoricalFeedError(f"empty_dataset:{data_type}")

    if data_type == DEPTH_DATA_TYPE:
        if not seen_snapshot or snapshot_rows == 0:
            raise HistoricalFeedError("depth_snapshot_missing")
        if pre_snapshot_rows:
            raise HistoricalFeedError("depth_rows_before_sod_snapshot")

        # Upstream _convert_depth flushes a snapshot batch when the next
        # non-snapshot depth update is seen. Ending inside a snapshot batch
        # would otherwise silently omit that final batch.
        if prev_snapshot:
            raise HistoricalFeedError("depth_ends_inside_snapshot_batch")

    return RawFileAudit(
        data_type=data_type,
        rows=rows,
        snapshot_rows=snapshot_rows,
        snapshot_batches=snapshot_batches,
        max_snapshot_side_rows=max_snapshot_side_rows,
        first_local_us=first_local,
        last_local_us=last_local,
    )


def preflight_day(
    raw_root: str | os.PathLike[str],
    day: str,
) -> FeedPreflight:
    spec = make_feed_spec(raw_root, day)

    # The official hftbacktest Tardis converter requires trades before
    # depth so a trade does not reduce queue position a second time after
    # its associated depth update.
    trades = _audit_file(
        spec.trades_path,
        data_type=TRADES_DATA_TYPE,
        day=spec.day,
    )
    depth = _audit_file(
        spec.depth_path,
        data_type=DEPTH_DATA_TYPE,
        day=spec.day,
    )

    # _convert_depth may insert up to two DEPTH_CLEAR_EVENT rows for each
    # snapshot batch. Add a small guard margin while avoiding the upstream
    # 100,000,000-row default allocation.
    converter_buffer_size = (
        trades.rows
        + depth.rows
        + 2 * depth.snapshot_batches
        + 32
    )

    snapshot_buffer_size = max(
        depth.max_snapshot_side_rows + 16,
        1024,
    )

    return FeedPreflight(
        spec=spec,
        trades=trades,
        depth=depth,
        converter_buffer_size=converter_buffer_size,
        snapshot_buffer_size=snapshot_buffer_size,
    )


def convert_day(
    raw_root: str | os.PathLike[str],
    day: str,
) -> ConvertedDay:
    preflight = preflight_day(raw_root, day)
    spec = preflight.spec

    from hftbacktest.data.utils import tardis

    # Fixed semantics:
    #   1. trades BEFORE depth, as required by upstream queue semantics;
    #   2. process SOD snapshots;
    #   3. base_latency=0 because negative raw latency has already failed;
    #   4. no output_filename: conversion writes no historical artifact.
    data = tardis.convert(
        [
            str(spec.trades_path),
            str(spec.depth_path),
        ],
        output_filename=None,
        buffer_size=preflight.converter_buffer_size,
        ss_buffer_size=preflight.snapshot_buffer_size,
        base_latency=0,
        snapshot_mode="process",
    )

    if len(data) == 0:
        raise HistoricalFeedError("converted_empty")

    # Reuse the frozen M4 event-order + nonnegative-feed-latency contract.
    try:
        m4.validate_events(data)
    except Exception as exc:
        raise HistoricalFeedError("m4_event_validation") from exc

    start_us, end_us = _day_bounds_us(spec.day)
    start_ns = start_us * 1000
    end_ns = end_us * 1000

    local_ts = np.asarray(data["local_ts"], dtype=np.int64)
    if np.any(local_ts < start_ns) or np.any(local_ts >= end_ns):
        raise HistoricalFeedError("converted_local_timestamp_day")

    import hftbacktest as h

    ev = np.asarray(data["ev"])

    if not np.any((ev & h.TRADE_EVENT) == h.TRADE_EVENT):
        raise HistoricalFeedError("converted_trade_missing")

    if not np.any(
        (ev & h.DEPTH_SNAPSHOT_EVENT) == h.DEPTH_SNAPSHOT_EVENT
    ):
        raise HistoricalFeedError("converted_snapshot_missing")

    return ConvertedDay(
        spec=spec,
        preflight=preflight,
        data=data,
    )


__all__ = [
    "TARDIS_EXCHANGE",
    "DEPTH_DATA_TYPE",
    "TRADES_DATA_TYPE",
    "HISTORICAL_REPLAY_EXECUTION_ENABLED",
    "HISTORICAL_PNL_OUTPUT_ENABLED",
    "NETWORK_ACQUISITION_ENABLED",
    "HistoricalFeedError",
    "TardisFeedSpec",
    "RawFileAudit",
    "FeedPreflight",
    "ConvertedDay",
    "make_feed_spec",
    "preflight_day",
    "convert_day",
]

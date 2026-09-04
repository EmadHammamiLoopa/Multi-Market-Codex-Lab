from __future__ import annotations

from datetime import datetime, timezone
import gzip
from pathlib import Path

import numpy as np
import pytest

from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m6_tardis_feed as f


DAY = "2026-01-01"


def _us(hms: str) -> int:
    dt = datetime.fromisoformat(
        f"{DAY}T{hms}+00:00"
    ).astimezone(timezone.utc)
    return int(dt.timestamp() * 1_000_000)


def _write_gz(path: Path, header: tuple[str, ...], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write(",".join(header) + "\n")
        for row in rows:
            fh.write(",".join(str(v) for v in row) + "\n")


def _valid_files(root: Path) -> None:
    trades = root / "trades" / "BTCUSDT" / f"{DAY}.csv.gz"
    depth = (
        root
        / "incremental_book_L2"
        / "BTCUSDT"
        / f"{DAY}.csv.gz"
    )

    _write_gz(
        trades,
        (
            "exchange",
            "symbol",
            "timestamp",
            "local_timestamp",
            "id",
            "side",
            "price",
            "amount",
        ),
        [
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.200000"),
                _us("00:00:00.210000"),
                "t1",
                "sell",
                100.0,
                0.001,
            ),
        ],
    )

    _write_gz(
        depth,
        (
            "exchange",
            "symbol",
            "timestamp",
            "local_timestamp",
            "is_snapshot",
            "side",
            "price",
            "amount",
        ),
        [
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.100000"),
                _us("00:00:00.110000"),
                "true",
                "bid",
                99.9,
                1.0,
            ),
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.100000"),
                _us("00:00:00.110000"),
                "true",
                "bid",
                100.0,
                10.0,
            ),
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.100000"),
                _us("00:00:00.110000"),
                "true",
                "ask",
                100.1,
                8.0,
            ),
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.100000"),
                _us("00:00:00.110000"),
                "true",
                "ask",
                100.2,
                1.0,
            ),
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.300000"),
                _us("00:00:00.310000"),
                "false",
                "ask",
                100.1,
                7.999,
            ),
        ],
    )


def test_scope_is_exact_phase0dl_btc_development_only(tmp_path: Path):
    spec = f.make_feed_spec(tmp_path, DAY)

    assert spec.exchange == "binance-futures"
    assert spec.symbol == "BTCUSDT"
    assert spec.trades_path == (
        tmp_path / "trades" / "BTCUSDT" / f"{DAY}.csv.gz"
    )
    assert spec.depth_path == (
        tmp_path
        / "incremental_book_L2"
        / "BTCUSDT"
        / f"{DAY}.csv.gz"
    )

    with pytest.raises(f.HistoricalFeedError, match="authorized_day"):
        f.make_feed_spec(tmp_path, "2026-08-01")

    with pytest.raises(
        f.HistoricalFeedError,
        match="network_or_url_root",
    ):
        f.make_feed_spec("https://datasets.tardis.dev/v1", DAY)

    assert f.HISTORICAL_REPLAY_EXECUTION_ENABLED is False
    assert f.HISTORICAL_PNL_OUTPUT_ENABLED is False
    assert f.NETWORK_ACQUISITION_ENABLED is False


def test_preflight_sizes_buffers_without_default_100m_allocation(
    tmp_path: Path,
):
    _valid_files(tmp_path)

    p = f.preflight_day(tmp_path, DAY)

    assert p.trades.rows == 1
    assert p.depth.rows == 5
    assert p.depth.snapshot_rows == 4
    assert p.depth.snapshot_batches == 1
    assert p.depth.max_snapshot_side_rows == 2
    assert p.converter_buffer_size == 40
    assert p.snapshot_buffer_size == 1024


def test_official_tardis_converter_produces_m4_valid_event_stream(
    tmp_path: Path,
):
    import hftbacktest as h

    _valid_files(tmp_path)
    r = f.convert_day(tmp_path, DAY)

    assert len(r.data) > 0

    ev = np.asarray(r.data["ev"])
    assert np.any((ev & h.TRADE_EVENT) == h.TRADE_EVENT)
    assert np.any(
        (ev & h.DEPTH_SNAPSHOT_EVENT)
        == h.DEPTH_SNAPSHOT_EVENT
    )

    assert np.all(r.data["local_ts"] >= r.data["exch_ts"])

    # Explicitly rerun the frozen M4 contract at the test boundary.
    m4.validate_events(r.data)


def test_negative_raw_feed_latency_fails_before_upstream_correction(
    tmp_path: Path,
):
    trades = tmp_path / "trades" / "BTCUSDT" / f"{DAY}.csv.gz"

    _write_gz(
        trades,
        (
            "exchange",
            "symbol",
            "timestamp",
            "local_timestamp",
            "id",
            "side",
            "price",
            "amount",
        ),
        [
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.200000"),
                _us("00:00:00.190000"),
                "t1",
                "sell",
                100.0,
                0.001,
            ),
        ],
    )

    with pytest.raises(
        f.HistoricalFeedError,
        match="negative_feed_latency",
    ):
        f.preflight_day(tmp_path, DAY)


def test_unknown_trade_aggressor_fails_closed(tmp_path: Path):
    trades = tmp_path / "trades" / "BTCUSDT" / f"{DAY}.csv.gz"

    _write_gz(
        trades,
        (
            "exchange",
            "symbol",
            "timestamp",
            "local_timestamp",
            "id",
            "side",
            "price",
            "amount",
        ),
        [
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.200000"),
                _us("00:00:00.210000"),
                "t1",
                "unknown",
                100.0,
                0.001,
            ),
        ],
    )

    with pytest.raises(
        f.HistoricalFeedError,
        match="trade_side",
    ):
        f.preflight_day(tmp_path, DAY)


def test_depth_must_start_from_sod_snapshot(tmp_path: Path):
    trades = tmp_path / "trades" / "BTCUSDT" / f"{DAY}.csv.gz"
    depth = (
        tmp_path
        / "incremental_book_L2"
        / "BTCUSDT"
        / f"{DAY}.csv.gz"
    )

    _write_gz(
        trades,
        (
            "exchange",
            "symbol",
            "timestamp",
            "local_timestamp",
            "id",
            "side",
            "price",
            "amount",
        ),
        [
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.200000"),
                _us("00:00:00.210000"),
                "t1",
                "sell",
                100.0,
                0.001,
            ),
        ],
    )

    _write_gz(
        depth,
        (
            "exchange",
            "symbol",
            "timestamp",
            "local_timestamp",
            "is_snapshot",
            "side",
            "price",
            "amount",
        ),
        [
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.100000"),
                _us("00:00:00.110000"),
                "false",
                "bid",
                100.0,
                10.0,
            ),
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.120000"),
                _us("00:00:00.130000"),
                "true",
                "bid",
                100.0,
                10.0,
            ),
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.120000"),
                _us("00:00:00.130000"),
                "true",
                "ask",
                100.1,
                8.0,
            ),
            (
                "binance-futures",
                "BTCUSDT",
                _us("00:00:00.300000"),
                _us("00:00:00.310000"),
                "false",
                "ask",
                100.1,
                7.0,
            ),
        ],
    )

    with pytest.raises(
        f.HistoricalFeedError,
        match="depth_rows_before_sod_snapshot",
    ):
        f.preflight_day(tmp_path, DAY)

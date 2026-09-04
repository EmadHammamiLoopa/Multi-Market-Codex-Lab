from __future__ import annotations

import csv
from dataclasses import dataclass
import gzip
from pathlib import Path
from typing import Callable

import numpy as np
import pytest

from multimarket import dev045_d6r_bounded_converter as bounded
from multimarket import dev045_m4_adapter as m4


TRADE_HEADER = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "id",
    "side",
    "price",
    "amount",
)

DEPTH_HEADER = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "is_snapshot",
    "side",
    "price",
    "amount",
)

TRADE_ROWS = (
    (
        "binance-futures",
        "BTCUSDT",
        "1000",
        "1000",
        "trade-1",
        "buy",
        "100.10",
        "0.25",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "900",
        "1100",
        "trade-2",
        "sell",
        "100.00",
        "0.50",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1000",
        "1100",
        "trade-3",
        "buy",
        "100.20",
        "0.125",
    ),
)

# Eleven SOD snapshot rows force the batch across every required raw chunk
# boundary, including chunk_rows=7. Bid and ask rows are intentionally
# interleaved so the converter must retain the upstream side-grouped flush.
DEPTH_ROWS = (
    (
        "binance-futures",
        "BTCUSDT",
        "1500",
        "2000",
        "true",
        "bid",
        "99.9",
        "1.0",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1500",
        "2000",
        "true",
        "ask",
        "100.1",
        "1.1",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1500",
        "2000",
        "true",
        "bid",
        "99.8",
        "2.0",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1500",
        "2000",
        "true",
        "ask",
        "100.2",
        "2.1",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1500",
        "2000",
        "true",
        "bid",
        "99.7",
        "3.0",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1500",
        "2000",
        "true",
        "ask",
        "100.3",
        "3.1",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1500",
        "2000",
        "true",
        "bid",
        "99.6",
        "4.0",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1500",
        "2000",
        "true",
        "ask",
        "100.4",
        "4.1",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1500",
        "2000",
        "true",
        "bid",
        "99.5",
        "5.0",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1500",
        "2000",
        "true",
        "ask",
        "100.5",
        "5.1",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1500",
        "2000",
        "true",
        "bid",
        "99.4",
        "6.0",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1600",
        "2100",
        "false",
        "ask",
        "100.1",
        "4.0",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1700",
        "2200",
        "false",
        "bid",
        "99.9",
        "0.0",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1700",
        "2300",
        "false",
        "ask",
        "100.2",
        "2.0",
    ),
    (
        "binance-futures",
        "BTCUSDT",
        "1700",
        "2300",
        "false",
        "bid",
        "99.8",
        "2.5",
    ),
)


@dataclass(frozen=True)
class SyntheticFiles:
    trades: Path
    depth: Path


@dataclass(frozen=True)
class ConvertedFixture:
    result: bounded.BoundedConversionResult
    scratch: Path


def _write_gzip_csv(
    path: Path,
    header: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _make_files(
    directory: Path,
    *,
    trade_rows: tuple[tuple[str, ...], ...] = TRADE_ROWS,
    depth_rows: tuple[tuple[str, ...], ...] = DEPTH_ROWS,
) -> SyntheticFiles:
    trades = directory / "trades.csv.gz"
    depth = directory / "incremental_book_L2.csv.gz"
    _write_gzip_csv(trades, TRADE_HEADER, trade_rows)
    _write_gzip_csv(depth, DEPTH_HEADER, depth_rows)
    return SyntheticFiles(trades=trades, depth=depth)


@pytest.fixture(scope="session")
def synthetic_files(tmp_path_factory: pytest.TempPathFactory) -> SyntheticFiles:
    return _make_files(tmp_path_factory.mktemp("dev045_d6r_synthetic"))


@pytest.fixture(scope="session")
def upstream_oracle(synthetic_files: SyntheticFiles) -> np.ndarray:
    import hftbacktest as h
    from hftbacktest.data.utils import tardis

    assert h.__version__ == "2.4.4"
    return tardis.convert(
        [str(synthetic_files.trades), str(synthetic_files.depth)],
        output_filename=None,
        buffer_size=128,
        ss_buffer_size=64,
        base_latency=0,
        snapshot_mode="process",
    )


@pytest.fixture(scope="session")
def bounded_outputs(
    tmp_path_factory: pytest.TempPathFactory,
    synthetic_files: SyntheticFiles,
) -> dict[int, ConvertedFixture]:
    directory = tmp_path_factory.mktemp("dev045_d6r_bounded")
    outputs: dict[int, ConvertedFixture] = {}
    for chunk_rows in (1, 2, 3, 7):
        scratch = directory / f"scratch_{chunk_rows}"
        scratch.mkdir()
        result = bounded.convert_tardis(
            synthetic_files.trades,
            synthetic_files.depth,
            directory / f"bounded_{chunk_rows}.npy",
            chunk_rows=chunk_rows,
            scratch_dir=scratch,
        )
        outputs[chunk_rows] = ConvertedFixture(result=result, scratch=scratch)
    return outputs


def _assert_fieldwise_exact(actual: np.ndarray, expected: np.ndarray) -> None:
    assert actual.shape == expected.shape
    assert actual.dtype == expected.dtype
    assert actual.dtype.names == expected.dtype.names
    assert actual.dtype.itemsize == expected.dtype.itemsize == 64

    assert actual.dtype.names is not None
    for field in actual.dtype.names:
        if actual.dtype[field].kind == "f":
            assert np.array_equal(
                actual[field],
                expected[field],
                equal_nan=True,
            ), field
        else:
            assert np.array_equal(actual[field], expected[field]), field


@pytest.mark.parametrize("chunk_rows", (1, 2, 3, 7))
def test_synthetic_upstream_oracle_parity(
    chunk_rows: int,
    upstream_oracle: np.ndarray,
    bounded_outputs: dict[int, ConvertedFixture],
) -> None:
    converted = bounded_outputs[chunk_rows]
    actual = np.load(
        converted.result.output_path,
        mmap_mode="r",
        allow_pickle=False,
    )
    _assert_fieldwise_exact(actual, upstream_oracle)

    assert converted.result.base_event_rows == 20
    expected_run_pairs = (20 + chunk_rows - 1) // chunk_rows
    assert converted.result.temporary_sort_runs == 2 * expected_run_pairs
    assert converted.result.final_event_rows == len(upstream_oracle)
    assert converted.result.chunk_rows == chunk_rows
    assert len(converted.result.output_sha256) == 64


def test_snapshot_crosses_chunk_boundary_with_exact_flush_order(
    bounded_outputs: dict[int, ConvertedFixture],
) -> None:
    import hftbacktest as h

    data = np.load(
        bounded_outputs[7].result.output_path,
        mmap_mode="r",
        allow_pickle=False,
    )
    selected = data[
        (data["exch_ts"] == 1_500_000)
        & (data["local_ts"] == 2_000_000)
    ]

    event_flags = int(h.EXCH_EVENT) | int(h.LOCAL_EVENT)
    actual = [
        (
            int(row["ev"]) & ~event_flags,
            float(row["px"]),
            float(row["qty"]),
        )
        for row in selected
    ]
    expected = [
        (int(h.DEPTH_CLEAR_EVENT | h.BUY_EVENT), 99.4, 0.0),
        *[
            (int(h.DEPTH_SNAPSHOT_EVENT | h.BUY_EVENT), px, qty)
            for px, qty in (
                (99.9, 1.0),
                (99.8, 2.0),
                (99.7, 3.0),
                (99.6, 4.0),
                (99.5, 5.0),
                (99.4, 6.0),
            )
        ],
        (int(h.DEPTH_CLEAR_EVENT | h.SELL_EVENT), 100.5, 0.0),
        *[
            (int(h.DEPTH_SNAPSHOT_EVENT | h.SELL_EVENT), px, qty)
            for px, qty in (
                (100.1, 1.1),
                (100.2, 2.1),
                (100.3, 3.1),
                (100.4, 4.1),
                (100.5, 5.1),
            )
        ],
    ]
    assert actual == expected


def test_zero_quantity_delete_source_seq_absence_memmap_and_m4_validation(
    bounded_outputs: dict[int, ConvertedFixture],
) -> None:
    import hftbacktest as h

    result = bounded_outputs[1].result
    data = np.load(result.output_path, mmap_mode="r", allow_pickle=False)
    assert isinstance(data, np.memmap)
    assert data.dtype == h.event_dtype
    assert data.dtype.names == (
        "ev",
        "exch_ts",
        "local_ts",
        "px",
        "qty",
        "order_id",
        "ival",
        "fval",
    )
    assert "source_seq" not in data.dtype.names

    deletes = [
        row
        for row in data
        if (int(row["ev"]) & 0xFF) == int(h.DEPTH_EVENT)
        and (int(row["ev"]) & int(h.BUY_EVENT)) == int(h.BUY_EVENT)
        and float(row["px"]) == 99.9
        and float(row["qty"]) == 0.0
    ]
    assert deletes
    event_dtype, constants = bounded._installed_contract()
    bounded._validate_final(
        result.output_path,
        event_dtype,
        result.chunk_rows,
        constants,
    )


def test_scratch_temporary_files_are_cleaned(
    bounded_outputs: dict[int, ConvertedFixture],
) -> None:
    for converted in bounded_outputs.values():
        assert list(converted.scratch.iterdir()) == []


def test_final_validation_calls_m4_only_with_bounded_slices(
    synthetic_files: SyntheticFiles,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_rows: list[int] = []
    frozen_validate_events = m4.validate_events

    def observe_slice(data: np.ndarray) -> None:
        observed_rows.append(len(data))
        assert isinstance(data, np.memmap)
        frozen_validate_events(data)

    monkeypatch.setattr(bounded.m4, "validate_events", observe_slice)
    result = bounded.convert_tardis(
        synthetic_files.trades,
        synthetic_files.depth,
        tmp_path / "bounded_validation.npy",
        chunk_rows=7,
        scratch_dir=tmp_path,
    )

    assert len(observed_rows) > 1
    assert sum(observed_rows) == result.final_event_rows
    assert max(observed_rows) == 7
    assert all(0 < rows <= result.chunk_rows for rows in observed_rows)


def _write_validation_file(
    path: Path,
    event_dtype: np.dtype,
    base_event: int,
    rows: tuple[tuple[int, int, int], ...],
) -> None:
    data = np.zeros(len(rows), dtype=event_dtype)
    for row_number, (event_flags, exch_ts, local_ts) in enumerate(rows):
        data[row_number]["ev"] = base_event | event_flags
        data[row_number]["exch_ts"] = exch_ts
        data[row_number]["local_ts"] = local_ts
        data[row_number]["px"] = 100.0
        data[row_number]["qty"] = 1.0
    np.save(path, data, allow_pickle=False)


def test_valid_event_order_across_validation_chunks_passes(
    tmp_path: Path,
) -> None:
    event_dtype, constants = bounded._installed_contract()
    path = tmp_path / "valid_chunks.npy"
    _write_validation_file(
        path,
        event_dtype,
        constants.depth | constants.buy,
        (
            (constants.exchange, 100, 1000),
            (constants.local, 150, 900),
            (constants.exchange | constants.local, 200, 1000),
            (constants.local, 250, 1100),
            (constants.exchange, 300, 1200),
        ),
    )

    bounded._validate_final(path, event_dtype, 2, constants)


def test_cross_boundary_exchange_order_violation_fails_closed(
    tmp_path: Path,
) -> None:
    event_dtype, constants = bounded._installed_contract()
    path = tmp_path / "exchange_boundary.npy"
    _write_validation_file(
        path,
        event_dtype,
        constants.depth | constants.buy,
        (
            (constants.exchange | constants.local, 100, 1000),
            (constants.exchange | constants.local, 200, 1100),
            (constants.local, 250, 1200),
            (constants.exchange, 150, 1250),
            (constants.exchange | constants.local, 300, 1300),
        ),
    )

    with pytest.raises(
        bounded.BoundedConverterError,
        match="final_exchange_order",
    ):
        bounded._validate_final(path, event_dtype, 2, constants)


def test_cross_boundary_local_order_violation_fails_closed(
    tmp_path: Path,
) -> None:
    event_dtype, constants = bounded._installed_contract()
    path = tmp_path / "local_boundary.npy"
    _write_validation_file(
        path,
        event_dtype,
        constants.depth | constants.buy,
        (
            (constants.exchange | constants.local, 100, 1000),
            (constants.exchange | constants.local, 200, 1100),
            (constants.exchange, 300, 1200),
            (constants.local, 400, 1050),
            (constants.exchange | constants.local, 500, 1300),
        ),
    )

    with pytest.raises(
        bounded.BoundedConverterError,
        match="final_local_order",
    ):
        bounded._validate_final(path, event_dtype, 2, constants)


def test_negative_latency_in_later_validation_slice_fails_closed(
    tmp_path: Path,
) -> None:
    event_dtype, constants = bounded._installed_contract()
    path = tmp_path / "negative_latency_slice.npy"
    _write_validation_file(
        path,
        event_dtype,
        constants.depth | constants.buy,
        (
            (constants.exchange | constants.local, 100, 1000),
            (constants.exchange | constants.local, 200, 1100),
            (constants.exchange | constants.local, 1200, 1199),
            (constants.exchange | constants.local, 1300, 1400),
        ),
    )

    with pytest.raises(
        bounded.BoundedConverterError,
        match="final_negative_feed_latency",
    ):
        bounded._validate_final(path, event_dtype, 2, constants)


def _mutate_row(
    rows: tuple[tuple[str, ...], ...],
    row_number: int,
    column_number: int,
    value: str,
) -> tuple[tuple[str, ...], ...]:
    mutable = [list(row) for row in rows]
    mutable[row_number][column_number] = value
    return tuple(tuple(row) for row in mutable)


def test_negative_raw_feed_latency_fails_closed(tmp_path: Path) -> None:
    rows = _mutate_row(TRADE_ROWS, 0, 3, "999")
    files = _make_files(tmp_path, trade_rows=rows)
    scratch = tmp_path / "scratch"
    scratch.mkdir()

    with pytest.raises(
        bounded.BoundedConverterError,
        match="negative_raw_feed_latency",
    ):
        bounded.convert_tardis(
            files.trades,
            files.depth,
            tmp_path / "negative.npy",
            chunk_rows=2,
            scratch_dir=scratch,
        )
    assert not (tmp_path / "negative.npy").exists()


@pytest.mark.parametrize(
    ("file_kind", "mutator", "match"),
    (
        (
            "trade",
            lambda: _mutate_row(TRADE_ROWS, 0, 5, "unknown"),
            "trade_side",
        ),
        (
            "depth",
            lambda: _mutate_row(DEPTH_ROWS, 0, 5, "unknown"),
            "depth_side",
        ),
    ),
)
def test_invalid_side_fails_closed(
    tmp_path: Path,
    file_kind: str,
    mutator: Callable[[], tuple[tuple[str, ...], ...]],
    match: str,
) -> None:
    if file_kind == "trade":
        files = _make_files(tmp_path, trade_rows=mutator())
    else:
        files = _make_files(tmp_path, depth_rows=mutator())
    scratch = tmp_path / "scratch"
    scratch.mkdir()

    with pytest.raises(bounded.BoundedConverterError, match=match):
        bounded.convert_tardis(
            files.trades,
            files.depth,
            tmp_path / "invalid.npy",
            chunk_rows=3,
            scratch_dir=scratch,
        )
    assert not (tmp_path / "invalid.npy").exists()


@pytest.mark.parametrize("chunk_rows", (0, -1))
def test_nonpositive_chunk_rows_fail_closed(
    synthetic_files: SyntheticFiles,
    tmp_path: Path,
    chunk_rows: int,
) -> None:
    with pytest.raises(bounded.BoundedConverterError, match="chunk_rows"):
        bounded.convert_tardis(
            synthetic_files.trades,
            synthetic_files.depth,
            tmp_path / "invalid_chunk.npy",
            chunk_rows=chunk_rows,
            scratch_dir=tmp_path,
        )


def test_unfinished_snapshot_batch_fails_closed(tmp_path: Path) -> None:
    files = _make_files(tmp_path, depth_rows=DEPTH_ROWS[:11])

    with pytest.raises(
        bounded.BoundedConverterError,
        match="unfinished_snapshot_batch",
    ):
        bounded.convert_tardis(
            files.trades,
            files.depth,
            tmp_path / "unfinished.npy",
            chunk_rows=7,
            scratch_dir=tmp_path,
        )
    assert not (tmp_path / "unfinished.npy").exists()


def test_implementation_does_not_use_polars_read_csv(
    synthetic_files: SyntheticFiles,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import polars as pl

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("polars.read_csv must not be used")

    monkeypatch.setattr(pl, "read_csv", forbidden)
    result = bounded.convert_tardis(
        synthetic_files.trades,
        synthetic_files.depth,
        tmp_path / "without_polars.npy",
        chunk_rows=3,
        scratch_dir=tmp_path,
    )
    assert result.base_event_rows == 20
    assert result.output_path.is_file()

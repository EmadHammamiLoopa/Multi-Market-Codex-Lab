from __future__ import annotations

from dataclasses import dataclass
import csv
import gzip
import hashlib
import heapq
import os
from pathlib import Path
import tempfile
from typing import Iterator, Sequence

import numpy as np

from multimarket import dev045_m4_adapter as m4


PRODUCTION_CHUNK_ROWS = 500_000

_EVENT_FIELDS = (
    "ev",
    "exch_ts",
    "local_ts",
    "px",
    "qty",
    "order_id",
    "ival",
    "fval",
)

_TRADE_HEADER = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "id",
    "side",
    "price",
    "amount",
)

_DEPTH_HEADER = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "is_snapshot",
    "side",
    "price",
    "amount",
)

_TEMP_DTYPE = np.dtype(
    [
        ("source_seq", "<u8"),
        ("ev", "<u8"),
        ("exch_ts", "<i8"),
        ("local_ts", "<i8"),
        ("px", "<f8"),
        ("qty", "<f8"),
        ("order_id", "<u8"),
        ("ival", "<i8"),
        ("fval", "<f8"),
    ],
    align=True,
)

_MAX_UINT64 = np.iinfo(np.uint64).max
_MIN_INT64 = np.iinfo(np.int64).min
_MAX_INT64 = np.iinfo(np.int64).max


class BoundedConverterError(RuntimeError):
    pass


@dataclass(frozen=True)
class BoundedConversionResult:
    base_event_rows: int
    final_event_rows: int
    temporary_sort_runs: int
    output_path: Path
    output_sha256: str
    chunk_rows: int


@dataclass(frozen=True)
class _EventConstants:
    buy: int
    sell: int
    trade: int
    depth: int
    depth_clear: int
    depth_snapshot: int
    exchange: int
    local: int


def _installed_contract() -> tuple[np.dtype, _EventConstants]:
    try:
        import hftbacktest as h
    except Exception as exc:  # pragma: no cover - exercised by environment gate
        raise BoundedConverterError("hftbacktest_import") from exc

    if h.__version__ != "2.4.4":
        raise BoundedConverterError(f"hftbacktest_version:{h.__version__}")

    event_dtype = np.dtype(h.event_dtype)
    if event_dtype.itemsize != 64:
        raise BoundedConverterError(
            f"event_dtype_itemsize:{event_dtype.itemsize}"
        )
    if event_dtype.names != _EVENT_FIELDS:
        raise BoundedConverterError(
            f"event_dtype_fields:{event_dtype.names}"
        )

    constants = _EventConstants(
        buy=int(h.BUY_EVENT),
        sell=int(h.SELL_EVENT),
        trade=int(h.TRADE_EVENT),
        depth=int(h.DEPTH_EVENT),
        depth_clear=int(h.DEPTH_CLEAR_EVENT),
        depth_snapshot=int(h.DEPTH_SNAPSHOT_EVENT),
        exchange=int(h.EXCH_EVENT),
        local=int(h.LOCAL_EVENT),
    )
    return event_dtype, constants


def _input_path(value: str | os.PathLike[str], label: str) -> Path:
    path = Path(value)
    if path.suffixes[-2:] != [".csv", ".gz"]:
        raise BoundedConverterError(f"{label}_suffix")
    if not path.is_file():
        raise BoundedConverterError(f"{label}_missing")
    return path


def _output_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    if path.suffix != ".npy":
        raise BoundedConverterError("output_suffix")
    if not path.parent.is_dir():
        raise BoundedConverterError("output_parent")
    if path.exists():
        raise BoundedConverterError("output_exists")
    return path


def _scratch_path(value: str | os.PathLike[str] | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if not path.is_dir():
        raise BoundedConverterError("scratch_directory")
    return path


def _csv_chunks(
    path: Path,
    expected_header: tuple[str, ...],
    chunk_rows: int,
    label: str,
) -> Iterator[list[tuple[int, list[str]]]]:
    try:
        with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            try:
                header = tuple(next(reader))
            except StopIteration as exc:
                raise BoundedConverterError(f"{label}_empty_file") from exc
            if header != expected_header:
                raise BoundedConverterError(f"{label}_header")

            chunk: list[tuple[int, list[str]]] = []
            for line_no, row in enumerate(reader, start=2):
                if len(row) != len(expected_header):
                    raise BoundedConverterError(
                        f"{label}_row_width:{line_no}"
                    )
                chunk.append((line_no, row))
                if len(chunk) == chunk_rows:
                    yield chunk
                    chunk = []
            if chunk:
                yield chunk
    except BoundedConverterError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise BoundedConverterError(f"{label}_read") from exc


def _timestamp_ns(text: str, label: str, line_no: int) -> int:
    try:
        value = int(text) * 1000
    except (TypeError, ValueError) as exc:
        raise BoundedConverterError(f"{label}_timestamp:{line_no}") from exc
    if value < _MIN_INT64 or value > _MAX_INT64:
        raise BoundedConverterError(f"{label}_timestamp_range:{line_no}")
    return value


def _number(text: str, label: str, line_no: int) -> float:
    try:
        return float(text)
    except (TypeError, ValueError) as exc:
        raise BoundedConverterError(f"{label}_number:{line_no}") from exc


def _close_memmap(array: np.ndarray) -> None:
    mmap = getattr(array, "_mmap", None)
    if mmap is not None:
        mmap.close()


class _RunBuilder:
    def __init__(self, work_dir: Path, chunk_rows: int) -> None:
        self._work_dir = work_dir
        self._buffer = np.empty(chunk_rows, dtype=_TEMP_DTYPE)
        self._rows = 0
        self._source_seq = 0
        self._run_number = 0
        self.exchange_paths: list[Path] = []
        self.local_paths: list[Path] = []

    @property
    def base_event_rows(self) -> int:
        return self._source_seq

    @property
    def temporary_sort_runs(self) -> int:
        return len(self.exchange_paths) + len(self.local_paths)

    def emit(
        self,
        *,
        ev: int,
        exch_ts: int,
        local_ts: int,
        px: float,
        qty: float,
        order_id: int = 0,
        ival: int = 0,
        fval: float = 0.0,
    ) -> None:
        if local_ts < exch_ts:
            raise BoundedConverterError("negative_raw_feed_latency")
        if self._source_seq > _MAX_UINT64:
            raise BoundedConverterError("source_seq_overflow")

        self._buffer[self._rows] = (
            self._source_seq,
            ev,
            exch_ts,
            local_ts,
            px,
            qty,
            order_id,
            ival,
            fval,
        )
        self._rows += 1
        self._source_seq += 1
        if self._rows == len(self._buffer):
            self._flush()

    def finish(self) -> None:
        self._flush()

    def _flush(self) -> None:
        if self._rows == 0:
            return

        records = self._buffer[: self._rows]
        exchange_path = self._work_dir / (
            f"exchange_{self._run_number:08d}.npy"
        )
        local_path = self._work_dir / f"local_{self._run_number:08d}.npy"

        order = np.lexsort((records["source_seq"], records["exch_ts"]))
        sorted_records = records[order]
        np.save(exchange_path, sorted_records, allow_pickle=False)
        del sorted_records, order

        order = np.lexsort((records["source_seq"], records["local_ts"]))
        sorted_records = records[order]
        np.save(local_path, sorted_records, allow_pickle=False)
        del sorted_records, order

        self.exchange_paths.append(exchange_path)
        self.local_paths.append(local_path)
        self._run_number += 1
        self._rows = 0


class _SnapshotBatch:
    def __init__(
        self,
        work_dir: Path,
        chunk_rows: int,
        event_dtype: np.dtype,
        constants: _EventConstants,
        batch_number: int,
    ) -> None:
        self._work_dir = work_dir
        self._event_dtype = event_dtype
        self._constants = constants
        self._batch_number = batch_number
        self._capacity = chunk_rows
        self._buffers = {
            "bid": np.empty(chunk_rows, dtype=event_dtype),
            "ask": np.empty(chunk_rows, dtype=event_dtype),
        }
        self._buffer_rows = {"bid": 0, "ask": 0}
        self._paths: dict[str, list[Path]] = {"bid": [], "ask": []}
        self._counts = {"bid": 0, "ask": 0}
        self._first_timestamp: dict[str, tuple[int, int]] = {}
        self._last_price: dict[str, float] = {}

    def append(
        self,
        side: str,
        *,
        exch_ts: int,
        local_ts: int,
        px: float,
        qty: float,
    ) -> None:
        if side not in ("bid", "ask"):
            raise BoundedConverterError("depth_side")
        if local_ts < exch_ts:
            raise BoundedConverterError("negative_raw_feed_latency")

        if self._counts[side] == 0:
            self._first_timestamp[side] = (exch_ts, local_ts)
        self._last_price[side] = px

        row_number = self._buffer_rows[side]
        side_flag = (
            self._constants.buy if side == "bid" else self._constants.sell
        )
        self._buffers[side][row_number] = (
            self._constants.depth_snapshot | side_flag,
            exch_ts,
            local_ts,
            px,
            qty,
            0,
            0,
            0.0,
        )
        self._buffer_rows[side] += 1
        self._counts[side] += 1
        if self._buffer_rows[side] == self._capacity:
            self._flush_side(side)

    def emit_to(self, builder: _RunBuilder) -> None:
        self._flush_side("bid")
        self._flush_side("ask")

        for side in ("bid", "ask"):
            if self._counts[side] == 0:
                continue
            side_flag = (
                self._constants.buy
                if side == "bid"
                else self._constants.sell
            )
            exch_ts, local_ts = self._first_timestamp[side]
            builder.emit(
                ev=self._constants.depth_clear | side_flag,
                exch_ts=exch_ts,
                local_ts=local_ts,
                px=self._last_price[side],
                qty=0.0,
            )

            for path in self._paths[side]:
                rows = np.load(path, mmap_mode="r", allow_pickle=False)
                try:
                    if rows.dtype != self._event_dtype:
                        raise BoundedConverterError("snapshot_spool_dtype")
                    for row in rows:
                        builder.emit(
                            ev=int(row["ev"]),
                            exch_ts=int(row["exch_ts"]),
                            local_ts=int(row["local_ts"]),
                            px=float(row["px"]),
                            qty=float(row["qty"]),
                            order_id=int(row["order_id"]),
                            ival=int(row["ival"]),
                            fval=float(row["fval"]),
                        )
                finally:
                    _close_memmap(rows)
                path.unlink()

    def _flush_side(self, side: str) -> None:
        row_count = self._buffer_rows[side]
        if row_count == 0:
            return
        path = self._work_dir / (
            f"snapshot_{self._batch_number:08d}_{side}_"
            f"{len(self._paths[side]):08d}.npy"
        )
        np.save(
            path,
            self._buffers[side][:row_count],
            allow_pickle=False,
        )
        self._paths[side].append(path)
        self._buffer_rows[side] = 0


class _MergedRunStream:
    def __init__(self, paths: Sequence[Path], timestamp_field: str) -> None:
        self._paths = paths
        self._timestamp_field = timestamp_field
        self._arrays: list[np.ndarray] = []
        self._heap: list[tuple[int, int, int, int]] = []

    def __enter__(self) -> _MergedRunStream:
        try:
            for run_number, path in enumerate(self._paths):
                rows = np.load(path, mmap_mode="r", allow_pickle=False)
                if rows.dtype != _TEMP_DTYPE:
                    _close_memmap(rows)
                    raise BoundedConverterError("sort_run_dtype")
                self._arrays.append(rows)
                if len(rows):
                    self._push(run_number, 0)
        except Exception:
            self.close()
            raise
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._heap.clear()
        for rows in self._arrays:
            _close_memmap(rows)
        self._arrays.clear()

    def __iter__(self) -> _MergedRunStream:
        return self

    def __next__(self) -> np.void:
        if not self._heap:
            raise StopIteration
        _, _, run_number, row_number = heapq.heappop(self._heap)
        rows = self._arrays[run_number]
        row = rows[row_number]
        next_row = row_number + 1
        if next_row < len(rows):
            self._push(run_number, next_row)
        return row

    def _push(self, run_number: int, row_number: int) -> None:
        row = self._arrays[run_number][row_number]
        heapq.heappush(
            self._heap,
            (
                int(row[self._timestamp_field]),
                int(row["source_seq"]),
                run_number,
                row_number,
            ),
        )


def _next_or_none(stream: Iterator[np.void]) -> np.void | None:
    try:
        return next(stream)
    except StopIteration:
        return None


def _corrected_events(
    exchange_paths: Sequence[Path],
    local_paths: Sequence[Path],
    constants: _EventConstants,
) -> Iterator[tuple[np.void, int]]:
    with (
        _MergedRunStream(exchange_paths, "exch_ts") as exchange_stream,
        _MergedRunStream(local_paths, "local_ts") as local_stream,
    ):
        exchange_row = _next_or_none(exchange_stream)
        local_row = _next_or_none(local_stream)

        while exchange_row is not None or local_row is not None:
            if exchange_row is not None and local_row is not None:
                exchange_exch_ts = int(exchange_row["exch_ts"])
                exchange_local_ts = int(exchange_row["local_ts"])
                local_exch_ts = int(local_row["exch_ts"])
                local_local_ts = int(local_row["local_ts"])

                if (
                    exchange_exch_ts == local_exch_ts
                    and exchange_local_ts == local_local_ts
                ):
                    if int(exchange_row["source_seq"]) != int(
                        local_row["source_seq"]
                    ):
                        raise BoundedConverterError(
                            "exact_timestamp_source_seq"
                        )
                    yield exchange_row, constants.exchange | constants.local
                    exchange_row = _next_or_none(exchange_stream)
                    local_row = _next_or_none(local_stream)
                    continue

                if (
                    exchange_exch_ts < local_exch_ts
                    or (
                        exchange_exch_ts == local_exch_ts
                        and exchange_local_ts < local_local_ts
                    )
                ):
                    yield exchange_row, constants.exchange
                    exchange_row = _next_or_none(exchange_stream)
                    continue

                yield local_row, constants.local
                local_row = _next_or_none(local_stream)
                continue

            if exchange_row is not None:
                yield exchange_row, constants.exchange
                exchange_row = _next_or_none(exchange_stream)
            else:
                assert local_row is not None
                yield local_row, constants.local
                local_row = _next_or_none(local_stream)


def _convert_trades(
    path: Path,
    chunk_rows: int,
    builder: _RunBuilder,
    constants: _EventConstants,
) -> None:
    for chunk in _csv_chunks(path, _TRADE_HEADER, chunk_rows, "trades"):
        for line_no, row in chunk:
            exch_ts = _timestamp_ns(row[2], "trades_exchange", line_no)
            local_ts = _timestamp_ns(row[3], "trades_local", line_no)
            if local_ts < exch_ts:
                raise BoundedConverterError(
                    f"negative_raw_feed_latency:trades:{line_no}"
                )
            side = row[5]
            if side == "buy":
                side_flag = constants.buy
            elif side == "sell":
                side_flag = constants.sell
            else:
                raise BoundedConverterError(f"trade_side:{line_no}")
            builder.emit(
                ev=side_flag | constants.trade,
                exch_ts=exch_ts,
                local_ts=local_ts,
                px=_number(row[6], "trades_price", line_no),
                qty=_number(row[7], "trades_amount", line_no),
            )


def _convert_depth(
    path: Path,
    chunk_rows: int,
    builder: _RunBuilder,
    work_dir: Path,
    event_dtype: np.dtype,
    constants: _EventConstants,
) -> None:
    snapshot: _SnapshotBatch | None = None
    snapshot_number = 0

    for chunk in _csv_chunks(path, _DEPTH_HEADER, chunk_rows, "depth"):
        for line_no, row in chunk:
            exch_ts = _timestamp_ns(row[2], "depth_exchange", line_no)
            local_ts = _timestamp_ns(row[3], "depth_local", line_no)
            if local_ts < exch_ts:
                raise BoundedConverterError(
                    f"negative_raw_feed_latency:depth:{line_no}"
                )

            snapshot_text = row[4].lower()
            if snapshot_text == "true":
                is_snapshot = True
            elif snapshot_text == "false":
                is_snapshot = False
            else:
                raise BoundedConverterError(f"is_snapshot:{line_no}")

            side = row[5]
            if side not in ("bid", "ask"):
                raise BoundedConverterError(f"depth_side:{line_no}")
            px = _number(row[6], "depth_price", line_no)
            qty = _number(row[7], "depth_amount", line_no)

            if is_snapshot:
                if snapshot is None:
                    snapshot = _SnapshotBatch(
                        work_dir,
                        chunk_rows,
                        event_dtype,
                        constants,
                        snapshot_number,
                    )
                    snapshot_number += 1
                snapshot.append(
                    side,
                    exch_ts=exch_ts,
                    local_ts=local_ts,
                    px=px,
                    qty=qty,
                )
                continue

            if snapshot is not None:
                snapshot.emit_to(builder)
                snapshot = None

            side_flag = constants.buy if side == "bid" else constants.sell
            builder.emit(
                ev=constants.depth | side_flag,
                exch_ts=exch_ts,
                local_ts=local_ts,
                px=px,
                qty=qty,
            )

    if snapshot is not None:
        raise BoundedConverterError("unfinished_snapshot_batch")


def _write_event(
    output: np.memmap,
    row_number: int,
    row: np.void,
    event_flags: int,
) -> None:
    output[row_number] = (
        int(row["ev"]) | event_flags,
        int(row["exch_ts"]),
        int(row["local_ts"]),
        float(row["px"]),
        float(row["qty"]),
        int(row["order_id"]),
        int(row["ival"]),
        float(row["fval"]),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def _validate_final(
    path: Path,
    event_dtype: np.dtype,
    chunk_rows: int,
    constants: _EventConstants,
) -> None:
    if chunk_rows <= 0:
        raise BoundedConverterError("validation_chunk_rows")

    data = np.load(path, mmap_mode="r", allow_pickle=False)
    try:
        if not isinstance(data, np.memmap):
            raise BoundedConverterError("final_not_memmap")
        if len(data) == 0:
            raise BoundedConverterError("final_empty")
        if data.dtype != event_dtype:
            raise BoundedConverterError(f"final_dtype:{data.dtype}")
        if data.dtype.names != _EVENT_FIELDS:
            raise BoundedConverterError(f"final_fields:{data.dtype.names}")
        if data.dtype.itemsize != 64:
            raise BoundedConverterError(
                f"final_itemsize:{data.dtype.itemsize}"
            )

        previous_exchange_ts: int | None = None
        previous_local_ts: int | None = None
        for start in range(0, len(data), chunk_rows):
            chunk = data[start : start + chunk_rows]
            if chunk.dtype != event_dtype:
                raise BoundedConverterError(
                    f"final_chunk_dtype:{chunk.dtype}"
                )
            if chunk.dtype.names != _EVENT_FIELDS:
                raise BoundedConverterError(
                    f"final_chunk_fields:{chunk.dtype.names}"
                )
            if chunk.dtype.itemsize != 64:
                raise BoundedConverterError(
                    f"final_chunk_itemsize:{chunk.dtype.itemsize}"
                )
            if np.any(chunk["local_ts"] < chunk["exch_ts"]):
                raise BoundedConverterError("final_negative_feed_latency")

            try:
                m4.validate_events(chunk)
            except Exception as exc:
                raise BoundedConverterError("m4_event_validation") from exc

            exchange_mask = (
                chunk["ev"] & constants.exchange
            ) == constants.exchange
            exchange_indices = np.flatnonzero(exchange_mask)
            if len(exchange_indices):
                first_exchange_ts = int(
                    chunk["exch_ts"][exchange_indices[0]]
                )
                if (
                    previous_exchange_ts is not None
                    and first_exchange_ts < previous_exchange_ts
                ):
                    raise BoundedConverterError("final_exchange_order")
                previous_exchange_ts = int(
                    chunk["exch_ts"][exchange_indices[-1]]
                )
            del exchange_indices, exchange_mask

            local_mask = (
                chunk["ev"] & constants.local
            ) == constants.local
            local_indices = np.flatnonzero(local_mask)
            if len(local_indices):
                first_local_ts = int(chunk["local_ts"][local_indices[0]])
                if (
                    previous_local_ts is not None
                    and first_local_ts < previous_local_ts
                ):
                    raise BoundedConverterError("final_local_order")
                previous_local_ts = int(
                    chunk["local_ts"][local_indices[-1]]
                )
    finally:
        _close_memmap(data)


def convert_tardis(
    trades_filename: str | os.PathLike[str],
    depth_filename: str | os.PathLike[str],
    output_filename: str | os.PathLike[str],
    *,
    chunk_rows: int = PRODUCTION_CHUNK_ROWS,
    scratch_dir: str | os.PathLike[str] | None = None,
) -> BoundedConversionResult:
    """Convert Tardis trades and L2 depth into a bounded, exact ``.npy``.

    Base events are created in frozen upstream order: every trade event first,
    followed by every converted depth event. Temporary sort records carry a
    monotonic source sequence; the final hftbacktest dtype does not.
    """
    if isinstance(chunk_rows, bool) or not isinstance(chunk_rows, int):
        raise BoundedConverterError("chunk_rows")
    if chunk_rows <= 0:
        raise BoundedConverterError("chunk_rows")

    event_dtype, constants = _installed_contract()
    trades_path = _input_path(trades_filename, "trades")
    depth_path = _input_path(depth_filename, "depth")
    output_path = _output_path(output_filename)
    scratch_path = _scratch_path(scratch_dir)

    output_created = False
    try:
        with tempfile.TemporaryDirectory(
            prefix="dev045_d6r_",
            dir=scratch_path,
        ) as temporary_name:
            work_dir = Path(temporary_name)
            builder = _RunBuilder(work_dir, chunk_rows)

            _convert_trades(trades_path, chunk_rows, builder, constants)
            _convert_depth(
                depth_path,
                chunk_rows,
                builder,
                work_dir,
                event_dtype,
                constants,
            )
            builder.finish()

            if builder.base_event_rows == 0:
                raise BoundedConverterError("base_events_empty")

            final_event_rows = sum(
                1
                for _ in _corrected_events(
                    builder.exchange_paths,
                    builder.local_paths,
                    constants,
                )
            )
            if final_event_rows == 0:
                raise BoundedConverterError("final_events_empty")

            partial_path = work_dir / "final.npy"
            output = np.lib.format.open_memmap(
                partial_path,
                mode="w+",
                dtype=event_dtype,
                shape=(final_event_rows,),
            )
            written = 0
            try:
                for row, event_flags in _corrected_events(
                    builder.exchange_paths,
                    builder.local_paths,
                    constants,
                ):
                    _write_event(output, written, row, event_flags)
                    written += 1
                if written != final_event_rows:
                    raise BoundedConverterError(
                        f"final_row_count:{written}:{final_event_rows}"
                    )
                output.flush()
            finally:
                _close_memmap(output)
                del output

            os.replace(partial_path, output_path)
            output_created = True
            _validate_final(
                output_path,
                event_dtype,
                chunk_rows,
                constants,
            )
            output_sha256 = _sha256(output_path)

            return BoundedConversionResult(
                base_event_rows=builder.base_event_rows,
                final_event_rows=final_event_rows,
                temporary_sort_runs=builder.temporary_sort_runs,
                output_path=output_path,
                output_sha256=output_sha256,
                chunk_rows=chunk_rows,
            )
    except Exception:
        if output_created:
            output_path.unlink(missing_ok=True)
        raise


__all__ = [
    "PRODUCTION_CHUNK_ROWS",
    "BoundedConverterError",
    "BoundedConversionResult",
    "convert_tardis",
]

from __future__ import annotations

from contextlib import ExitStack
import csv
from dataclasses import dataclass
import gzip
import hashlib
import heapq
import os
from pathlib import Path
import resource
import shutil
import tempfile
from typing import Iterator, Sequence

import numpy as np
from numpy.lib import format as npy_format

from multimarket import dev045_d6r8c_bounded_converter_redesign_contract as contract
from multimarket import dev045_m4_adapter as m4


PRODUCTION_INITIAL_CHUNK_ROWS = contract.PRODUCTION_INITIAL_CHUNK_ROWS
MERGE_FAN_IN = contract.MERGE_FAN_IN
MERGE_INPUT_WINDOW_ROWS = contract.MERGE_INPUT_WINDOW_ROWS
MERGE_OUTPUT_BUFFER_ROWS = contract.MERGE_OUTPUT_BUFFER_ROWS
CORRECTED_INPUT_WINDOW_ROWS = contract.CORRECTED_INPUT_WINDOW_ROWS
FINAL_OUTPUT_BUFFER_ROWS = contract.FINAL_OUTPUT_BUFFER_ROWS
VALIDATION_WINDOW_ROWS = contract.VALIDATION_WINDOW_ROWS
RUNTIME_RSS_ABORT_BYTES = contract.RUNTIME_RSS_ABORT_BYTES

_EVENT_FIELDS = contract.EVENT_FIELDS
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


class StructurallyBoundedConverterError(RuntimeError):
    pass


@dataclass(frozen=True)
class StructurallyBoundedConversionResult:
    base_event_rows: int
    final_event_rows: int
    initial_sort_runs: int
    exchange_merge_levels: int
    local_merge_levels: int
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


@dataclass(frozen=True)
class _Tuning:
    chunk_rows: int = PRODUCTION_INITIAL_CHUNK_ROWS
    merge_fan_in: int = MERGE_FAN_IN
    merge_input_window_rows: int = MERGE_INPUT_WINDOW_ROWS
    merge_output_buffer_rows: int = MERGE_OUTPUT_BUFFER_ROWS
    corrected_input_window_rows: int = CORRECTED_INPUT_WINDOW_ROWS
    final_output_buffer_rows: int = FINAL_OUTPUT_BUFFER_ROWS
    validation_window_rows: int = VALIDATION_WINDOW_ROWS
    rss_abort_bytes: int = RUNTIME_RSS_ABORT_BYTES


PRODUCTION_TUNING = _Tuning()


def _testing_tuning(
    *,
    chunk_rows: int,
    merge_fan_in: int = 2,
    merge_input_window_rows: int = 2,
    merge_output_buffer_rows: int = 3,
    corrected_input_window_rows: int = 2,
    final_output_buffer_rows: int = 3,
    validation_window_rows: int = 3,
    rss_abort_bytes: int = RUNTIME_RSS_ABORT_BYTES,
) -> _Tuning:
    """Build a smaller synthetic-only tuning used to force merge boundaries."""
    return _Tuning(
        chunk_rows=chunk_rows,
        merge_fan_in=merge_fan_in,
        merge_input_window_rows=merge_input_window_rows,
        merge_output_buffer_rows=merge_output_buffer_rows,
        corrected_input_window_rows=corrected_input_window_rows,
        final_output_buffer_rows=final_output_buffer_rows,
        validation_window_rows=validation_window_rows,
        rss_abort_bytes=rss_abort_bytes,
    )


def _validate_tuning(tuning: _Tuning) -> None:
    values = (
        tuning.chunk_rows,
        tuning.merge_fan_in,
        tuning.merge_input_window_rows,
        tuning.merge_output_buffer_rows,
        tuning.corrected_input_window_rows,
        tuning.final_output_buffer_rows,
        tuning.validation_window_rows,
        tuning.rss_abort_bytes,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values):
        raise StructurallyBoundedConverterError("tuning")
    if tuning.merge_fan_in < 2:
        raise StructurallyBoundedConverterError("merge_fan_in")


def _installed_contract() -> tuple[np.dtype, _EventConstants]:
    try:
        import hftbacktest as h
    except Exception as exc:  # pragma: no cover
        raise StructurallyBoundedConverterError("hftbacktest_import") from exc
    if h.__version__ != contract.HFTBACKTEST_VERSION:
        raise StructurallyBoundedConverterError(f"hftbacktest_version:{h.__version__}")
    event_dtype = np.dtype(h.event_dtype)
    if event_dtype.itemsize != contract.EVENT_ITEMSIZE_BYTES:
        raise StructurallyBoundedConverterError(f"event_dtype_itemsize:{event_dtype.itemsize}")
    if event_dtype.names != _EVENT_FIELDS:
        raise StructurallyBoundedConverterError(f"event_dtype_fields:{event_dtype.names}")
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
        raise StructurallyBoundedConverterError(f"{label}_suffix")
    if not path.is_file():
        raise StructurallyBoundedConverterError(f"{label}_missing")
    return path


def _output_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    if path.suffix != ".npy":
        raise StructurallyBoundedConverterError("output_suffix")
    if not path.parent.is_dir():
        raise StructurallyBoundedConverterError("output_parent")
    if path.exists():
        raise StructurallyBoundedConverterError("output_exists")
    return path


def _scratch_path(
    value: str | os.PathLike[str] | None,
    output_parent: Path,
) -> Path:
    path = output_parent if value is None else Path(value)
    if not path.is_dir():
        raise StructurallyBoundedConverterError("scratch_directory")
    if os.stat(path).st_dev != os.stat(output_parent).st_dev:
        raise StructurallyBoundedConverterError("scratch_output_device")
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
                raise StructurallyBoundedConverterError(f"{label}_empty_file") from exc
            if header != expected_header:
                raise StructurallyBoundedConverterError(f"{label}_header")
            chunk: list[tuple[int, list[str]]] = []
            for line_no, row in enumerate(reader, start=2):
                if len(row) != len(expected_header):
                    raise StructurallyBoundedConverterError(f"{label}_row_width:{line_no}")
                chunk.append((line_no, row))
                if len(chunk) == chunk_rows:
                    yield chunk
                    chunk = []
            if chunk:
                yield chunk
    except StructurallyBoundedConverterError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise StructurallyBoundedConverterError(f"{label}_read") from exc


def _timestamp_ns(text: str, label: str, line_no: int) -> int:
    try:
        value = int(text) * 1000
    except (TypeError, ValueError) as exc:
        raise StructurallyBoundedConverterError(f"{label}_timestamp:{line_no}") from exc
    if value < _MIN_INT64 or value > _MAX_INT64:
        raise StructurallyBoundedConverterError(f"{label}_timestamp_range:{line_no}")
    return value


def _number(text: str, label: str, line_no: int) -> float:
    try:
        return float(text)
    except (TypeError, ValueError) as exc:
        raise StructurallyBoundedConverterError(f"{label}_number:{line_no}") from exc


def _current_rss_bytes() -> int:
    try:
        with Path("/proc/self/statm").open("rt", encoding="ascii") as fh:
            fields = fh.read().split()
        if len(fields) < 2:
            raise ValueError("statm_fields")
        return int(fields[1]) * int(os.sysconf("SC_PAGE_SIZE"))
    except Exception as exc:  # pragma: no cover
        raise StructurallyBoundedConverterError("rss_unavailable") from exc


def _rss_guard(limit_bytes: int) -> int:
    rss = _current_rss_bytes()
    if rss > limit_bytes:
        raise StructurallyBoundedConverterError(f"rss_abort:{rss}:{limit_bytes}")
    return rss


def _memavailable_bytes() -> int:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except Exception as exc:  # pragma: no cover
        raise StructurallyBoundedConverterError("memavailable_unavailable") from exc
    raise StructurallyBoundedConverterError("memavailable_unavailable")


def canonical_resource_preflight(
    *,
    raw_rows: int,
    scratch_dir: str | os.PathLike[str],
    output_parent: str | os.PathLike[str],
) -> dict[str, int]:
    scratch = Path(scratch_dir)
    output = Path(output_parent)
    if not scratch.is_dir() or not output.is_dir():
        raise StructurallyBoundedConverterError("resource_directory")
    if os.stat(scratch).st_dev != os.stat(output).st_dev:
        raise StructurallyBoundedConverterError("scratch_output_device")
    mem_available = _memavailable_bytes()
    if mem_available < contract.MIN_MEMAVAILABLE_BYTES:
        raise StructurallyBoundedConverterError(
            f"memavailable:{mem_available}:{contract.MIN_MEMAVAILABLE_BYTES}"
        )
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft < contract.MIN_NOFILE_SOFT or hard < contract.MIN_NOFILE_HARD:
        raise StructurallyBoundedConverterError(f"nofile:{soft}:{hard}")
    required_scratch = contract.required_scratch_bytes(raw_rows)
    scratch_free = shutil.disk_usage(scratch).free
    if scratch_free < required_scratch:
        raise StructurallyBoundedConverterError(
            f"scratch_free:{scratch_free}:{required_scratch}"
        )
    return {
        "mem_available_bytes": int(mem_available),
        "nofile_soft": int(soft),
        "nofile_hard": int(hard),
        "scratch_free_bytes": int(scratch_free),
        "required_scratch_bytes": int(required_scratch),
    }


def _npy_header(path: Path) -> tuple[tuple[int, ...], bool, np.dtype, int]:
    try:
        with path.open("rb") as fh:
            version = npy_format.read_magic(fh)
            if version != contract.INTERMEDIATE_NPY_VERSION:
                raise StructurallyBoundedConverterError(f"npy_version:{version}")
            shape, fortran_order, dtype = npy_format.read_array_header_1_0(fh)
            offset = fh.tell()
    except StructurallyBoundedConverterError:
        raise
    except Exception as exc:
        raise StructurallyBoundedConverterError("npy_header") from exc
    return tuple(shape), bool(fortran_order), np.dtype(dtype), int(offset)


def _write_npy_header(fh: object, dtype: np.dtype, rows: int) -> None:
    if rows < 0:
        raise StructurallyBoundedConverterError("npy_rows")
    npy_format.write_array_header_1_0(
        fh,
        {
            "descr": npy_format.dtype_to_descr(dtype),
            "fortran_order": False,
            "shape": (int(rows),),
        },
    )


class _NpyWindowReader:
    def __init__(self, path: Path, expected_dtype: np.dtype, window_rows: int) -> None:
        self.path = path
        self.expected_dtype = np.dtype(expected_dtype)
        self.window_rows = window_rows
        self.rows = 0
        self._remaining = 0
        self._fh = None

    def __enter__(self) -> "_NpyWindowReader":
        try:
            self._fh = self.path.open("rb")
            version = npy_format.read_magic(self._fh)
            if version != contract.INTERMEDIATE_NPY_VERSION:
                raise StructurallyBoundedConverterError(f"npy_version:{version}")
            shape, fortran_order, dtype = npy_format.read_array_header_1_0(self._fh)
            dtype = np.dtype(dtype)
            if fortran_order:
                raise StructurallyBoundedConverterError("npy_fortran_order")
            if len(shape) != 1:
                raise StructurallyBoundedConverterError(f"npy_shape:{shape}")
            if dtype != self.expected_dtype:
                raise StructurallyBoundedConverterError(f"npy_dtype:{dtype}")
            self.rows = int(shape[0])
            self._remaining = self.rows
        except Exception:
            self.close()
            raise
        return self

    def read_window(self) -> np.ndarray:
        if self._fh is None:
            raise StructurallyBoundedConverterError("reader_closed")
        if self._remaining == 0:
            return np.empty(0, dtype=self.expected_dtype)
        count = min(self.window_rows, self._remaining)
        data = np.fromfile(self._fh, dtype=self.expected_dtype, count=count)
        if len(data) != count:
            raise StructurallyBoundedConverterError(
                f"npy_short_read:{len(data)}:{count}"
            )
        self._remaining -= count
        return data

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def __exit__(self, *_: object) -> None:
        self.close()


class _SequentialRowReader:
    def __init__(self, path: Path, expected_dtype: np.dtype, window_rows: int) -> None:
        self._reader = _NpyWindowReader(path, expected_dtype, window_rows)
        self._buffer = np.empty(0, dtype=expected_dtype)
        self._index = 0
        self.rows = 0

    def __enter__(self) -> "_SequentialRowReader":
        self._reader.__enter__()
        self.rows = self._reader.rows
        self._refill()
        return self

    def _refill(self) -> None:
        self._buffer = self._reader.read_window()
        self._index = 0

    def pop(self) -> np.void | None:
        if self._index >= len(self._buffer):
            if len(self._buffer) == 0:
                return None
            self._refill()
            if len(self._buffer) == 0:
                return None
        row = self._buffer[self._index]
        self._index += 1
        return row

    def close(self) -> None:
        self._buffer = np.empty(0, dtype=self._reader.expected_dtype)
        self._index = 0
        self._reader.close()

    def __exit__(self, *_: object) -> None:
        self.close()


class _NpyBufferedWriter:
    def __init__(
        self,
        path: Path,
        dtype: np.dtype,
        rows: int,
        buffer_rows: int,
    ) -> None:
        self.path = path
        self.dtype = np.dtype(dtype)
        self.rows = int(rows)
        self.buffer = np.empty(buffer_rows, dtype=self.dtype)
        self.buffered = 0
        self.written = 0
        self._fh = None

    def __enter__(self) -> "_NpyBufferedWriter":
        self._fh = self.path.open("xb")
        _write_npy_header(self._fh, self.dtype, self.rows)
        return self

    def append(self, value: object) -> None:
        if self._fh is None:
            raise StructurallyBoundedConverterError("writer_closed")
        if self.written + self.buffered >= self.rows:
            raise StructurallyBoundedConverterError("writer_overflow")
        self.buffer[self.buffered] = value
        self.buffered += 1
        if self.buffered == len(self.buffer):
            self.flush()

    def flush(self) -> None:
        if self._fh is None:
            raise StructurallyBoundedConverterError("writer_closed")
        if self.buffered:
            self.buffer[: self.buffered].tofile(self._fh)
            self.written += self.buffered
            self.buffered = 0

    def close(self, *, require_complete: bool) -> None:
        if self._fh is None:
            return
        self.flush()
        if require_complete and self.written != self.rows:
            actual = self.written
            expected = self.rows
            self._fh.close()
            self._fh = None
            raise StructurallyBoundedConverterError(
                f"writer_row_count:{actual}:{expected}"
            )
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._fh.close()
        self._fh = None

    def __exit__(self, exc_type: object, *_: object) -> None:
        self.close(require_complete=exc_type is None)


class _RunBuilder:
    def __init__(
        self,
        work_dir: Path,
        tuning: _Tuning,
    ) -> None:
        self.work_dir = work_dir
        self.tuning = tuning
        self.buffer = np.empty(tuning.chunk_rows, dtype=_TEMP_DTYPE)
        self.rows = 0
        self.source_seq = 0
        self.run_number = 0
        self.exchange_paths: list[Path] = []
        self.local_paths: list[Path] = []

    @property
    def base_event_rows(self) -> int:
        return self.source_seq

    @property
    def initial_sort_runs(self) -> int:
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
            raise StructurallyBoundedConverterError("negative_raw_feed_latency")
        if self.source_seq > _MAX_UINT64:
            raise StructurallyBoundedConverterError("source_seq_overflow")
        self.buffer[self.rows] = (
            self.source_seq,
            ev,
            exch_ts,
            local_ts,
            px,
            qty,
            order_id,
            ival,
            fval,
        )
        self.rows += 1
        self.source_seq += 1
        if self.rows == len(self.buffer):
            self.flush()

    def finish(self) -> None:
        self.flush()

    def flush(self) -> None:
        if self.rows == 0:
            return
        records = self.buffer[: self.rows]
        exchange_path = self.work_dir / f"exchange_l0_{self.run_number:08d}.npy"
        local_path = self.work_dir / f"local_l0_{self.run_number:08d}.npy"

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
        self.run_number += 1
        self.rows = 0
        _rss_guard(self.tuning.rss_abort_bytes)


class _SnapshotBatch:
    def __init__(
        self,
        work_dir: Path,
        tuning: _Tuning,
        event_dtype: np.dtype,
        constants: _EventConstants,
        batch_number: int,
    ) -> None:
        self.work_dir = work_dir
        self.tuning = tuning
        self.event_dtype = event_dtype
        self.constants = constants
        self.batch_number = batch_number
        self.capacity = tuning.chunk_rows
        self.buffers = {
            "bid": np.empty(self.capacity, dtype=event_dtype),
            "ask": np.empty(self.capacity, dtype=event_dtype),
        }
        self.buffer_rows = {"bid": 0, "ask": 0}
        self.paths: dict[str, list[Path]] = {"bid": [], "ask": []}
        self.counts = {"bid": 0, "ask": 0}
        self.first_timestamp: dict[str, tuple[int, int]] = {}
        self.last_price: dict[str, float] = {}

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
            raise StructurallyBoundedConverterError("depth_side")
        if local_ts < exch_ts:
            raise StructurallyBoundedConverterError("negative_raw_feed_latency")
        if self.counts[side] == 0:
            self.first_timestamp[side] = (exch_ts, local_ts)
        self.last_price[side] = px
        index = self.buffer_rows[side]
        side_flag = self.constants.buy if side == "bid" else self.constants.sell
        self.buffers[side][index] = (
            self.constants.depth_snapshot | side_flag,
            exch_ts,
            local_ts,
            px,
            qty,
            0,
            0,
            0.0,
        )
        self.buffer_rows[side] += 1
        self.counts[side] += 1
        if self.buffer_rows[side] == self.capacity:
            self._flush_side(side)

    def emit_to(self, builder: _RunBuilder) -> None:
        self._flush_side("bid")
        self._flush_side("ask")
        for side in ("bid", "ask"):
            if self.counts[side] == 0:
                continue
            side_flag = self.constants.buy if side == "bid" else self.constants.sell
            exch_ts, local_ts = self.first_timestamp[side]
            builder.emit(
                ev=self.constants.depth_clear | side_flag,
                exch_ts=exch_ts,
                local_ts=local_ts,
                px=self.last_price[side],
                qty=0.0,
            )
            for path in self.paths[side]:
                rows = np.load(path, allow_pickle=False)
                try:
                    if rows.dtype != self.event_dtype:
                        raise StructurallyBoundedConverterError("snapshot_spool_dtype")
                    if len(rows) > self.capacity:
                        raise StructurallyBoundedConverterError("snapshot_spool_rows")
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
                    del rows
                path.unlink()

    def _flush_side(self, side: str) -> None:
        count = self.buffer_rows[side]
        if count == 0:
            return
        path = self.work_dir / (
            f"snapshot_{self.batch_number:08d}_{side}_{len(self.paths[side]):08d}.npy"
        )
        np.save(path, self.buffers[side][:count], allow_pickle=False)
        self.paths[side].append(path)
        self.buffer_rows[side] = 0


def _convert_trades(
    path: Path,
    tuning: _Tuning,
    builder: _RunBuilder,
    constants: _EventConstants,
) -> None:
    for chunk in _csv_chunks(path, _TRADE_HEADER, tuning.chunk_rows, "trades"):
        for line_no, row in chunk:
            exch_ts = _timestamp_ns(row[2], "trades_exchange", line_no)
            local_ts = _timestamp_ns(row[3], "trades_local", line_no)
            if local_ts < exch_ts:
                raise StructurallyBoundedConverterError(
                    f"negative_raw_feed_latency:trades:{line_no}"
                )
            if row[5] == "buy":
                side_flag = constants.buy
            elif row[5] == "sell":
                side_flag = constants.sell
            else:
                raise StructurallyBoundedConverterError(f"trade_side:{line_no}")
            builder.emit(
                ev=side_flag | constants.trade,
                exch_ts=exch_ts,
                local_ts=local_ts,
                px=_number(row[6], "trades_price", line_no),
                qty=_number(row[7], "trades_amount", line_no),
            )
        _rss_guard(tuning.rss_abort_bytes)


def _convert_depth(
    path: Path,
    tuning: _Tuning,
    builder: _RunBuilder,
    work_dir: Path,
    event_dtype: np.dtype,
    constants: _EventConstants,
) -> None:
    snapshot: _SnapshotBatch | None = None
    snapshot_number = 0
    for chunk in _csv_chunks(path, _DEPTH_HEADER, tuning.chunk_rows, "depth"):
        for line_no, row in chunk:
            exch_ts = _timestamp_ns(row[2], "depth_exchange", line_no)
            local_ts = _timestamp_ns(row[3], "depth_local", line_no)
            if local_ts < exch_ts:
                raise StructurallyBoundedConverterError(
                    f"negative_raw_feed_latency:depth:{line_no}"
                )
            snapshot_text = row[4].lower()
            if snapshot_text == "true":
                is_snapshot = True
            elif snapshot_text == "false":
                is_snapshot = False
            else:
                raise StructurallyBoundedConverterError(f"is_snapshot:{line_no}")
            side = row[5]
            if side not in ("bid", "ask"):
                raise StructurallyBoundedConverterError(f"depth_side:{line_no}")
            px = _number(row[6], "depth_price", line_no)
            qty = _number(row[7], "depth_amount", line_no)
            if is_snapshot:
                if snapshot is None:
                    snapshot = _SnapshotBatch(
                        work_dir,
                        tuning,
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
        _rss_guard(tuning.rss_abort_bytes)
    if snapshot is not None:
        raise StructurallyBoundedConverterError("unfinished_snapshot_batch")


def _run_rows(path: Path) -> int:
    shape, fortran, dtype, _ = _npy_header(path)
    if fortran or dtype != _TEMP_DTYPE or len(shape) != 1:
        raise StructurallyBoundedConverterError("sort_run_contract")
    return int(shape[0])


def _merge_group(
    paths: Sequence[Path],
    output_path: Path,
    timestamp_field: str,
    tuning: _Tuning,
) -> None:
    if not 2 <= len(paths) <= tuning.merge_fan_in:
        raise StructurallyBoundedConverterError("merge_group_size")
    expected_rows = sum(_run_rows(path) for path in paths)
    readers: list[_SequentialRowReader] = []
    heap: list[tuple[int, int, int, np.void]] = []
    with ExitStack() as stack:
        for index, path in enumerate(paths):
            reader = stack.enter_context(
                _SequentialRowReader(
                    path,
                    _TEMP_DTYPE,
                    tuning.merge_input_window_rows,
                )
            )
            readers.append(reader)
            row = reader.pop()
            if row is not None:
                heapq.heappush(
                    heap,
                    (
                        int(row[timestamp_field]),
                        int(row["source_seq"]),
                        index,
                        row,
                    ),
                )
        with _NpyBufferedWriter(
            output_path,
            _TEMP_DTYPE,
            expected_rows,
            tuning.merge_output_buffer_rows,
        ) as writer:
            while heap:
                _, _, index, row = heapq.heappop(heap)
                writer.append(row)
                next_row = readers[index].pop()
                if next_row is not None:
                    heapq.heappush(
                        heap,
                        (
                            int(next_row[timestamp_field]),
                            int(next_row["source_seq"]),
                            index,
                            next_row,
                        ),
                    )
                if writer.buffered == 0:
                    _rss_guard(tuning.rss_abort_bytes)


def _merge_axis(
    paths: Sequence[Path],
    *,
    axis: str,
    timestamp_field: str,
    work_dir: Path,
    tuning: _Tuning,
) -> tuple[Path, int]:
    current = list(paths)
    if not current:
        raise StructurallyBoundedConverterError(f"{axis}_runs_empty")
    level = 0
    while len(current) > 1:
        level += 1
        next_paths: list[Path] = []
        for group_number, start in enumerate(
            range(0, len(current), tuning.merge_fan_in)
        ):
            group = current[start : start + tuning.merge_fan_in]
            if len(group) == 1:
                next_paths.append(group[0])
                continue
            output = work_dir / f"{axis}_l{level}_{group_number:08d}.npy"
            try:
                _merge_group(group, output, timestamp_field, tuning)
            except Exception:
                output.unlink(missing_ok=True)
                raise
            for path in group:
                path.unlink()
            next_paths.append(output)
            _rss_guard(tuning.rss_abort_bytes)
        current = next_paths
    return current[0], level


def _corrected_events(
    exchange_path: Path,
    local_path: Path,
    constants: _EventConstants,
    tuning: _Tuning,
) -> Iterator[tuple[np.void, int]]:
    with (
        _SequentialRowReader(
            exchange_path,
            _TEMP_DTYPE,
            tuning.corrected_input_window_rows,
        ) as exchange_stream,
        _SequentialRowReader(
            local_path,
            _TEMP_DTYPE,
            tuning.corrected_input_window_rows,
        ) as local_stream,
    ):
        exchange_row = exchange_stream.pop()
        local_row = local_stream.pop()
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
                    if int(exchange_row["source_seq"]) != int(local_row["source_seq"]):
                        raise StructurallyBoundedConverterError(
                            "exact_timestamp_source_seq"
                        )
                    yield exchange_row, constants.exchange | constants.local
                    exchange_row = exchange_stream.pop()
                    local_row = local_stream.pop()
                    continue
                if (
                    exchange_exch_ts < local_exch_ts
                    or (
                        exchange_exch_ts == local_exch_ts
                        and exchange_local_ts < local_local_ts
                    )
                ):
                    yield exchange_row, constants.exchange
                    exchange_row = exchange_stream.pop()
                    continue
                yield local_row, constants.local
                local_row = local_stream.pop()
                continue
            if exchange_row is not None:
                yield exchange_row, constants.exchange
                exchange_row = exchange_stream.pop()
            else:
                assert local_row is not None
                yield local_row, constants.local
                local_row = local_stream.pop()


def _event_tuple(row: np.void, event_flags: int) -> tuple[object, ...]:
    return (
        int(row["ev"]) | event_flags,
        int(row["exch_ts"]),
        int(row["local_ts"]),
        float(row["px"]),
        float(row["qty"]),
        int(row["order_id"]),
        int(row["ival"]),
        float(row["fval"]),
    )


def _validate_final(
    path: Path,
    event_dtype: np.dtype,
    window_rows: int,
    constants: _EventConstants,
    rss_abort_bytes: int = RUNTIME_RSS_ABORT_BYTES,
) -> None:
    if window_rows <= 0:
        raise StructurallyBoundedConverterError("validation_window_rows")
    previous_exchange_ts: int | None = None
    previous_local_ts: int | None = None
    total = 0
    with _NpyWindowReader(path, event_dtype, window_rows) as reader:
        if reader.rows == 0:
            raise StructurallyBoundedConverterError("final_empty")
        while True:
            chunk = reader.read_window()
            if len(chunk) == 0:
                break
            total += len(chunk)
            if chunk.dtype != event_dtype:
                raise StructurallyBoundedConverterError(f"final_chunk_dtype:{chunk.dtype}")
            if chunk.dtype.names != _EVENT_FIELDS:
                raise StructurallyBoundedConverterError(
                    f"final_chunk_fields:{chunk.dtype.names}"
                )
            if chunk.dtype.itemsize != contract.EVENT_ITEMSIZE_BYTES:
                raise StructurallyBoundedConverterError(
                    f"final_chunk_itemsize:{chunk.dtype.itemsize}"
                )
            if np.any(chunk["local_ts"] < chunk["exch_ts"]):
                raise StructurallyBoundedConverterError("final_negative_feed_latency")
            try:
                m4.validate_events(chunk)
            except Exception as exc:
                raise StructurallyBoundedConverterError("m4_event_validation") from exc

            exchange_mask = (
                chunk["ev"] & constants.exchange
            ) == constants.exchange
            exchange_indices = np.flatnonzero(exchange_mask)
            if len(exchange_indices):
                first_exchange_ts = int(chunk["exch_ts"][exchange_indices[0]])
                if (
                    previous_exchange_ts is not None
                    and first_exchange_ts < previous_exchange_ts
                ):
                    raise StructurallyBoundedConverterError("final_exchange_order")
                previous_exchange_ts = int(chunk["exch_ts"][exchange_indices[-1]])

            local_mask = (chunk["ev"] & constants.local) == constants.local
            local_indices = np.flatnonzero(local_mask)
            if len(local_indices):
                first_local_ts = int(chunk["local_ts"][local_indices[0]])
                if (
                    previous_local_ts is not None
                    and first_local_ts < previous_local_ts
                ):
                    raise StructurallyBoundedConverterError("final_local_order")
                previous_local_ts = int(chunk["local_ts"][local_indices[-1]])
            _rss_guard(rss_abort_bytes)
        if total != reader.rows:
            raise StructurallyBoundedConverterError(
                f"final_validation_rows:{total}:{reader.rows}"
            )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(contract.SHA256_BLOCK_BYTES)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def convert_tardis(
    trades_filename: str | os.PathLike[str],
    depth_filename: str | os.PathLike[str],
    output_filename: str | os.PathLike[str],
    *,
    scratch_dir: str | os.PathLike[str] | None = None,
    _tuning: _Tuning = PRODUCTION_TUNING,
) -> StructurallyBoundedConversionResult:
    """Convert Tardis trades/L2 data with structurally bounded resident memory."""
    _validate_tuning(_tuning)
    event_dtype, constants = _installed_contract()
    trades_path = _input_path(trades_filename, "trades")
    depth_path = _input_path(depth_filename, "depth")
    output_path = _output_path(output_filename)
    scratch_path = _scratch_path(scratch_dir, output_path.parent)

    with tempfile.TemporaryDirectory(
        prefix="dev045_d6r8_",
        dir=scratch_path,
    ) as temporary_name:
        work_dir = Path(temporary_name)
        builder = _RunBuilder(work_dir, _tuning)
        _convert_trades(trades_path, _tuning, builder, constants)
        _convert_depth(
            depth_path,
            _tuning,
            builder,
            work_dir,
            event_dtype,
            constants,
        )
        builder.finish()
        if builder.base_event_rows == 0:
            raise StructurallyBoundedConverterError("base_events_empty")
        initial_sort_runs = builder.initial_sort_runs

        exchange_path, exchange_levels = _merge_axis(
            builder.exchange_paths,
            axis="exchange",
            timestamp_field="exch_ts",
            work_dir=work_dir,
            tuning=_tuning,
        )
        local_path, local_levels = _merge_axis(
            builder.local_paths,
            axis="local",
            timestamp_field="local_ts",
            work_dir=work_dir,
            tuning=_tuning,
        )

        final_event_rows = sum(
            1
            for _ in _corrected_events(
                exchange_path,
                local_path,
                constants,
                _tuning,
            )
        )
        if final_event_rows == 0:
            raise StructurallyBoundedConverterError("final_events_empty")

        partial_path = work_dir / "final.npy"
        with _NpyBufferedWriter(
            partial_path,
            event_dtype,
            final_event_rows,
            _tuning.final_output_buffer_rows,
        ) as writer:
            for row, event_flags in _corrected_events(
                exchange_path,
                local_path,
                constants,
                _tuning,
            ):
                writer.append(_event_tuple(row, event_flags))
                if writer.buffered == 0:
                    _rss_guard(_tuning.rss_abort_bytes)

        _validate_final(
            partial_path,
            event_dtype,
            _tuning.validation_window_rows,
            constants,
            _tuning.rss_abort_bytes,
        )
        output_sha256 = _sha256(partial_path)
        os.replace(partial_path, output_path)

        return StructurallyBoundedConversionResult(
            base_event_rows=builder.base_event_rows,
            final_event_rows=final_event_rows,
            initial_sort_runs=initial_sort_runs,
            exchange_merge_levels=exchange_levels,
            local_merge_levels=local_levels,
            output_path=output_path,
            output_sha256=output_sha256,
            chunk_rows=_tuning.chunk_rows,
        )


__all__ = [
    "PRODUCTION_TUNING",
    "StructurallyBoundedConverterError",
    "StructurallyBoundedConversionResult",
    "canonical_resource_preflight",
    "convert_tardis",
]

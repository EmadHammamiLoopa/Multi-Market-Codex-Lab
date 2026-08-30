from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import gzip
import io
import json
import math
import os
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path
from typing import Any

import websockets


EXPERIMENT_ID = "CODEX-EXP-025-P0"
INITIAL_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
SUPPORTED_SYMBOLS = frozenset(INITIAL_SYMBOLS)
VENUE = "BINANCE_USD_M_FUTURES"
ASSET_CLASS = "CRYPTO_PERPETUAL_FUTURES"
MARKET = "USD_M_PERPETUAL"
STREAM_SUFFIX = "@bookTicker"
WS_BASE = "wss://fstream.binance.com/stream?streams="
WS_URL = WS_BASE + "/".join(
    f"{symbol.lower()}{STREAM_SUFFIX}" for symbol in INITIAL_SYMBOLS
)
RAW_RELATIVE_ROOT = Path("multimarket/bookticker")
QUEUE_MAXSIZE = 100_000
WRITER_SHUTDOWN_TIMEOUT_S = 30.0
OPERATIONAL_FAILURE_SUFFIX = ".operational-failure.json"


class AcquisitionOperationalError(RuntimeError):
    def __init__(self, symbol: str, message: str) -> None:
        super().__init__(f"{symbol}: {message}")
        self.symbol = symbol


class SymbolQueueOverflow(AcquisitionOperationalError):
    pass


class WriterShutdownTimeout(AcquisitionOperationalError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _day_start(day: date) -> datetime:
    return datetime.combine(day, datetime_time(), tzinfo=timezone.utc)


def _day_from_wall_ns(wall_ns: int) -> date:
    seconds = wall_ns // 1_000_000_000
    return datetime.fromtimestamp(seconds, timezone.utc).date()


def _iso_from_ns(ns: int) -> str:
    seconds, nanoseconds = divmod(ns, 1_000_000_000)
    instant = datetime.fromtimestamp(seconds, tz=timezone.utc).replace(
        microsecond=nanoseconds // 1000
    )
    return instant.isoformat(timespec="microseconds")


def _full_hex_commit(value: str) -> str:
    if len(value) != 40:
        raise ValueError("full 40-character frozen implementation commit required")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError("frozen implementation commit must be hexadecimal") from exc
    return value.lower()


def raw_relative_path(symbol: str, day: date) -> Path:
    normalized = symbol.upper()
    if normalized not in SUPPORTED_SYMBOLS:
        raise ValueError(f"unsupported EXP025 symbol: {symbol}")
    return RAW_RELATIVE_ROOT / normalized / f"{day.isoformat()}.jsonl.gz"


def operational_failure_path(raw_path: Path) -> Path:
    return raw_path.with_name(raw_path.name + OPERATIONAL_FAILURE_SUFFIX)


def no_analysis_guards() -> dict[str, bool]:
    return {
        "older_august_holdout_opened": False,
        "historical_aug1_feature_reparsed": False,
        "features_constructed": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "ap_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
        "leverage_scored": False,
        "automatic_holdout_scoring": False,
    }


@dataclass
class SymbolState:
    symbol: str
    accepted_quotes: int = 0
    rejected_quotes: int = 0
    last_wall_ns: int | None = None
    last_mono_ns: int | None = None
    active_connection_epoch: int | None = None
    latest_quote: dict[str, Any] | None = None

    def invalidate(self) -> None:
        self.active_connection_epoch = None
        self.latest_quote = None


@dataclass(frozen=True)
class CollectorIdentity:
    collector_run_id: str
    process_id: int
    frozen_implementation_commit: str
    collector_started_wall_ns: int
    collector_started_utc: str


class RawWriter:
    """Exclusive gzip JSONL writer with a durable close boundary."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._raw = path.open("xb")
        self._gzip = gzip.GzipFile(
            filename=path.name,
            mode="wb",
            fileobj=self._raw,
            compresslevel=3,
            mtime=0,
        )
        self._text = io.TextIOWrapper(self._gzip, encoding="utf-8")
        self._closed = False

    def write(self, record: dict[str, Any]) -> None:
        if self._closed:
            raise RuntimeError("raw writer is closed")
        self._text.write(
            json.dumps(
                record,
                separators=(",", ":"),
                sort_keys=True,
                allow_nan=False,
            )
            + "\n"
        )
        self._text.flush()
        self._gzip.flush()

    def close(self) -> None:
        if self._closed:
            return
        self._text.flush()
        self._text.detach()
        self._gzip.close()
        self._raw.flush()
        os.fsync(self._raw.fileno())
        self._raw.close()
        self._closed = True


class AsyncSymbolSink:
    """A symbol-isolated write queue so feed routing never waits on another symbol."""

    _STOP = object()

    def __init__(
        self,
        symbol: str,
        writer: RawWriter,
        *,
        maxsize: int = QUEUE_MAXSIZE,
        shutdown_timeout_s: float = WRITER_SHUTDOWN_TIMEOUT_S,
    ):
        if symbol not in SUPPORTED_SYMBOLS:
            raise ValueError(f"unsupported writer symbol: {symbol}")
        if maxsize < 1:
            raise ValueError("writer queue maxsize must be positive")
        if not math.isfinite(shutdown_timeout_s) or shutdown_timeout_s <= 0:
            raise ValueError("writer shutdown timeout must be finite and positive")
        self.symbol = symbol
        self.writer = writer
        self.queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=maxsize)
        self.shutdown_timeout_s = float(shutdown_timeout_s)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.stopped = asyncio.Event()
        self.stop_enqueued = False
        self.closed = False
        self.operational_failure: AcquisitionOperationalError | None = None
        self.task = asyncio.create_task(self._worker())

    async def _worker(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            while True:
                item = await self.queue.get()
                try:
                    if item is self._STOP:
                        await loop.run_in_executor(
                            self.executor,
                            self.writer.close,
                        )
                        return
                    await loop.run_in_executor(
                        self.executor,
                        self.writer.write,
                        item,
                    )
                finally:
                    self.queue.task_done()
        finally:
            self.stopped.set()

    def emit(self, record: dict[str, Any]) -> None:
        if self.closed or self.stop_enqueued:
            raise AcquisitionOperationalError(
                self.symbol,
                "writer is closing or already closed",
            )
        if self.task.done():
            exception = self.task.exception()
            error = AcquisitionOperationalError(
                self.symbol,
                "writer worker stopped unexpectedly",
            )
            self.operational_failure = error
            raise error from exception
        try:
            self.queue.put_nowait(record)
        except asyncio.QueueFull as exc:
            error = SymbolQueueOverflow(
                self.symbol,
                f"writer queue capacity {self.queue.maxsize} exhausted; "
                "refusing silent quote loss",
            )
            self.operational_failure = error
            raise error from exc

    async def _request_stop_and_wait(self) -> None:
        if not self.stop_enqueued:
            await self.queue.put(self._STOP)
            self.stop_enqueued = True
        while not self.task.done():
            await asyncio.sleep(0.01)

    async def close(self) -> None:
        if self.closed:
            return
        try:
            await asyncio.wait_for(
                self._request_stop_and_wait(),
                timeout=self.shutdown_timeout_s,
            )
        except asyncio.TimeoutError as exc:
            error = WriterShutdownTimeout(
                self.symbol,
                "writer shutdown exceeded "
                f"{self.shutdown_timeout_s:.3f}s; day failed closed",
            )
            self.operational_failure = error
            raise error from exc

        try:
            self.task.result()
        except Exception as exc:
            error = AcquisitionOperationalError(
                self.symbol,
                "writer worker failed during shutdown",
            )
            self.operational_failure = error
            raise error from exc
        finally:
            self.executor.shutdown(wait=True)
        self.closed = True


def _transport_record(
    event: str,
    epoch: int,
    *,
    wall_ns: int | None = None,
    mono_ns: int | None = None,
    **extra: Any,
) -> dict[str, Any]:
    wall = time.time_ns() if wall_ns is None else wall_ns
    mono = time.monotonic_ns() if mono_ns is None else mono_ns
    return {
        "record_type": "transport",
        "event": event,
        "connection_epoch": epoch,
        "receive_wall_ns": wall,
        "receive_wall_utc": _iso_from_ns(wall),
        "receive_monotonic_ns": mono,
        **extra,
    }


def _day_started_record(
    *,
    symbol: str,
    day: date,
    identity: CollectorIdentity,
    wall_ns: int,
    mono_ns: int,
) -> dict[str, Any]:
    day_start = _day_start(day)
    day_end = day_start + timedelta(days=1)
    armed_before = identity.collector_started_wall_ns < (
        int(day_start.timestamp()) * 1_000_000_000
    )
    return _transport_record(
        "day_started",
        0,
        wall_ns=wall_ns,
        mono_ns=mono_ns,
        experiment_id=EXPERIMENT_ID,
        collector_run_id=identity.collector_run_id,
        process_id=identity.process_id,
        frozen_implementation_commit=identity.frozen_implementation_commit,
        collector_started_wall_ns=identity.collector_started_wall_ns,
        collector_started_utc=identity.collector_started_utc,
        armed_before_day_start=armed_before,
        symbol=symbol,
        collection_day=day.isoformat(),
        collection_start_utc=day_start.isoformat(),
        collection_end_utc=day_end.isoformat(),
        initial_symbols=list(INITIAL_SYMBOLS),
        venue=VENUE,
        asset_class=ASSET_CLASS,
        source="BINANCE_FUTURES_BOOKTICKER_WEBSOCKET",
    )


class AsyncDailyRawBank:
    def __init__(
        self,
        output_root: Path,
        identity: CollectorIdentity,
        *,
        symbols: tuple[str, ...] = INITIAL_SYMBOLS,
        queue_maxsize: int = QUEUE_MAXSIZE,
        writer_shutdown_timeout_s: float = WRITER_SHUTDOWN_TIMEOUT_S,
        writer_factory: Any = RawWriter,
    ) -> None:
        if symbols != INITIAL_SYMBOLS:
            raise ValueError("EXP025 initial symbol set and order are exact")
        self.output_root = output_root
        self.identity = identity
        self.symbols = symbols
        self.queue_maxsize = queue_maxsize
        self.writer_shutdown_timeout_s = writer_shutdown_timeout_s
        self.writer_factory = writer_factory
        self.current_day: date | None = None
        self.sinks: dict[str, AsyncSymbolSink] = {}

    async def open_day(
        self,
        day: date,
        *,
        wall_ns: int,
        mono_ns: int,
        active_epoch: int | None = None,
    ) -> None:
        if self.sinks:
            raise RuntimeError("daily bank already has open writers")
        paths = {
            symbol: self.output_root / raw_relative_path(symbol, day)
            for symbol in self.symbols
        }
        existing = [str(path) for path in paths.values() if path.exists()]
        if existing:
            raise FileExistsError(
                "refusing to append, resume, or overwrite daily raw file: "
                + ", ".join(existing)
            )

        opened: dict[str, RawWriter] = {}
        try:
            for symbol, path in paths.items():
                opened[symbol] = self.writer_factory(path)
        except Exception:
            for writer in opened.values():
                writer.close()
            raise

        self.sinks = {
            symbol: AsyncSymbolSink(
                symbol,
                opened[symbol],
                maxsize=self.queue_maxsize,
                shutdown_timeout_s=self.writer_shutdown_timeout_s,
            )
            for symbol in self.symbols
        }
        self.current_day = day
        for symbol in self.symbols:
            self.emit(
                symbol,
                _day_started_record(
                    symbol=symbol,
                    day=day,
                    identity=self.identity,
                    wall_ns=wall_ns,
                    mono_ns=mono_ns,
                ),
            )
            if active_epoch is not None:
                self.emit(
                    symbol,
                    _transport_record(
                        "connection_carried",
                        active_epoch,
                        wall_ns=wall_ns,
                        mono_ns=mono_ns,
                    ),
                )

    def emit(self, symbol: str, record: dict[str, Any]) -> None:
        if symbol not in self.sinks:
            raise ValueError(f"no open writer for symbol: {symbol}")
        try:
            self.sinks[symbol].emit(record)
        except AcquisitionOperationalError as exc:
            self._record_operational_failure((symbol,), exc)
            raise

    def broadcast(self, record: dict[str, Any]) -> None:
        for symbol in self.symbols:
            self.emit(symbol, dict(record))

    async def close_day(self) -> None:
        sinks = tuple(self.sinks.values())
        results = await asyncio.gather(
            *(sink.close() for sink in sinks),
            return_exceptions=True,
        )
        failures = [result for result in results if isinstance(result, Exception)]
        if failures:
            exc = failures[0]
            if not isinstance(exc, AcquisitionOperationalError):
                exc = AcquisitionOperationalError(
                    self.symbols[0],
                    f"writer shutdown failed: {type(exc).__name__}: {exc}",
                )
                affected_symbols = self.symbols
            else:
                affected_symbols = (exc.symbol,)
            self._record_operational_failure(affected_symbols, exc)
            raise exc
        self.sinks = {}
        self.current_day = None

    def _record_operational_failure(
        self,
        symbols: tuple[str, ...],
        exc: AcquisitionOperationalError,
    ) -> None:
        if self.current_day is None:
            return
        payload = {
            "experiment_id": EXPERIMENT_ID,
            "status": "OPERATIONAL_FAILURE",
            "collection_day": self.current_day.isoformat(),
            "failure_type": type(exc).__name__,
            "failure_message": str(exc),
            "created_at": _utc_now().isoformat(),
        }
        for symbol in symbols:
            raw_path = self.output_root / raw_relative_path(
                symbol,
                self.current_day,
            )
            failure_path = operational_failure_path(raw_path)
            if failure_path.exists():
                continue
            failure_path.parent.mkdir(parents=True, exist_ok=True)
            part = failure_path.with_suffix(failure_path.suffix + ".part")
            encoded = json.dumps(
                {**payload, "symbol": symbol},
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ) + "\n"
            try:
                with part.open("x", encoding="utf-8") as handle:
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
                part.replace(failure_path)
            except FileExistsError:
                if part.exists():
                    part.unlink()
                if not failure_path.exists():
                    raise

    async def rollover(
        self,
        next_day: date,
        *,
        wall_ns: int,
        mono_ns: int,
        active_epoch: int | None,
    ) -> None:
        if self.current_day is None:
            raise RuntimeError("cannot roll over a closed daily bank")
        if next_day != self.current_day + timedelta(days=1):
            raise RuntimeError("daily rollover must advance exactly one UTC day")
        self.broadcast(
            _transport_record(
                "day_rollover",
                active_epoch or 0,
                wall_ns=wall_ns,
                mono_ns=mono_ns,
                completed_day=self.current_day.isoformat(),
                next_day=next_day.isoformat(),
            )
        )
        await self.close_day()
        await self.open_day(
            next_day,
            wall_ns=wall_ns,
            mono_ns=mono_ns,
            active_epoch=active_epoch,
        )


def _validate_payload(
    payload: dict[str, Any],
    *,
    expected_symbol: str,
) -> tuple[bool, str | None]:
    if expected_symbol not in SUPPORTED_SYMBOLS:
        return False, "UNSUPPORTED_SYMBOL"
    if str(payload.get("s", "")).upper() != expected_symbol:
        return False, "WRONG_SYMBOL"
    try:
        bid = float(payload["b"])
        ask = float(payload["a"])
        bid_qty = float(payload["B"])
        ask_qty = float(payload["A"])
    except Exception:
        return False, "PARSE_FAIL"
    values = (bid, ask, bid_qty, ask_qty)
    if not all(math.isfinite(value) for value in values):
        return False, "NONFINITE"
    if bid <= 0 or ask <= 0 or ask <= bid:
        return False, "INVALID_OR_CROSSED_PRICE"
    if bid_qty < 0 or ask_qty < 0:
        return False, "NEGATIVE_QUANTITY"
    return True, None


def _rejected_record(
    *,
    reason: str,
    epoch: int,
    wall_ns: int,
    mono_ns: int,
    observed_symbol: str | None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_type": "rejected",
        "reason": reason,
        "observed_symbol": observed_symbol,
        "connection_epoch": epoch,
        "receive_wall_ns": wall_ns,
        "receive_wall_utc": _iso_from_ns(wall_ns),
        "receive_monotonic_ns": mono_ns,
    }
    if payload is not None:
        record["payload"] = payload
    return record


def process_quote_payload(
    state: SymbolState,
    payload: dict[str, Any],
    *,
    epoch: int,
    wall_ns: int,
    mono_ns: int,
) -> dict[str, Any]:
    if state.symbol not in SUPPORTED_SYMBOLS:
        raise ValueError("state has unsupported symbol")
    if state.last_wall_ns is not None and wall_ns < state.last_wall_ns:
        state.rejected_quotes += 1
        return _rejected_record(
            reason="WALL_CLOCK_REVERSAL",
            epoch=epoch,
            wall_ns=wall_ns,
            mono_ns=mono_ns,
            observed_symbol=str(payload.get("s", "")).upper() or None,
        )
    if state.last_mono_ns is not None and mono_ns < state.last_mono_ns:
        state.rejected_quotes += 1
        return _rejected_record(
            reason="MONOTONIC_CLOCK_REVERSAL",
            epoch=epoch,
            wall_ns=wall_ns,
            mono_ns=mono_ns,
            observed_symbol=str(payload.get("s", "")).upper() or None,
        )

    valid, reason = _validate_payload(payload, expected_symbol=state.symbol)
    if not valid:
        state.rejected_quotes += 1
        return _rejected_record(
            reason=str(reason),
            epoch=epoch,
            wall_ns=wall_ns,
            mono_ns=mono_ns,
            observed_symbol=str(payload.get("s", "")).upper() or None,
            payload=payload,
        )

    bid = float(payload["b"])
    ask = float(payload["a"])
    record = {
        "record_type": "quote",
        "market": MARKET,
        "symbol": state.symbol,
        "venue": VENUE,
        "asset_class": ASSET_CLASS,
        "connection_epoch": epoch,
        "receive_wall_ns": wall_ns,
        "receive_timestamp_utc": _iso_from_ns(wall_ns),
        "receive_monotonic_ns": mono_ns,
        "source_timestamp_if_available": payload.get("E"),
        "exchange_event_time_ms": payload.get("E"),
        "exchange_transaction_time_ms": payload.get("T"),
        "update_id": payload.get("u"),
        "bid": bid,
        "ask": ask,
        "bid_size": float(payload["B"]),
        "ask_size": float(payload["A"]),
        # Compatibility aliases preserve the validated raw-to-grid schema.
        "best_bid": bid,
        "best_ask": ask,
        "best_bid_qty": float(payload["B"]),
        "best_ask_qty": float(payload["A"]),
    }
    state.last_wall_ns = wall_ns
    state.last_mono_ns = mono_ns
    state.active_connection_epoch = epoch
    state.latest_quote = record
    state.accepted_quotes += 1
    return record


class MultiSymbolRouter:
    def __init__(self) -> None:
        self.states = {
            symbol: SymbolState(symbol=symbol) for symbol in INITIAL_SYMBOLS
        }
        self.unsupported_rejections = 0

    def connection_opened(self, epoch: int) -> None:
        for state in self.states.values():
            state.active_connection_epoch = epoch
            state.latest_quote = None

    def invalidate_all(self) -> None:
        for state in self.states.values():
            state.invalidate()

    def route(
        self,
        payload: dict[str, Any],
        *,
        epoch: int,
        wall_ns: int,
        mono_ns: int,
    ) -> tuple[str | None, dict[str, Any]]:
        observed = str(payload.get("s", "")).upper()
        if observed not in SUPPORTED_SYMBOLS:
            self.unsupported_rejections += 1
            return None, _rejected_record(
                reason="UNSUPPORTED_SYMBOL",
                epoch=epoch,
                wall_ns=wall_ns,
                mono_ns=mono_ns,
                observed_symbol=observed or None,
                payload=payload,
            )
        state = self.states[observed]
        return observed, process_quote_payload(
            state,
            payload,
            epoch=epoch,
            wall_ns=wall_ns,
            mono_ns=mono_ns,
        )


def _parse_message(raw_message: str | bytes) -> dict[str, Any]:
    envelope = json.loads(raw_message)
    payload = envelope.get("data", envelope)
    if not isinstance(payload, dict):
        raise TypeError("bookTicker payload is not an object")
    return payload


async def collect_continuously(
    output_root: Path,
    *,
    frozen_commit: str,
    stop_event: asyncio.Event | None = None,
) -> dict[str, Any]:
    implementation_commit = _full_hex_commit(frozen_commit)
    started_wall_ns = time.time_ns()
    started_mono_ns = time.monotonic_ns()
    identity = CollectorIdentity(
        collector_run_id=str(uuid.uuid4()),
        process_id=os.getpid(),
        frozen_implementation_commit=implementation_commit,
        collector_started_wall_ns=started_wall_ns,
        collector_started_utc=_iso_from_ns(started_wall_ns),
    )
    router = MultiSymbolRouter()
    bank = AsyncDailyRawBank(output_root, identity)
    await bank.open_day(
        _day_from_wall_ns(started_wall_ns),
        wall_ns=started_wall_ns,
        mono_ns=started_mono_ns,
    )

    epoch = 0
    active_epoch: int | None = None

    async def advance_daily_partition(wall_ns: int, mono_ns: int) -> None:
        target_day = _day_from_wall_ns(wall_ns)
        while bank.current_day is not None and target_day > bank.current_day:
            await bank.rollover(
                bank.current_day + timedelta(days=1),
                wall_ns=wall_ns,
                mono_ns=mono_ns,
                active_epoch=active_epoch,
            )
            for state in router.states.values():
                state.latest_quote = None

    try:
        while stop_event is None or not stop_event.is_set():
            epoch += 1
            active_epoch = None
            router.invalidate_all()
            attempt_wall_ns = time.time_ns()
            attempt_mono_ns = time.monotonic_ns()
            await advance_daily_partition(attempt_wall_ns, attempt_mono_ns)
            bank.broadcast(
                _transport_record(
                    "connection_open_attempt",
                    epoch,
                    wall_ns=attempt_wall_ns,
                    mono_ns=attempt_mono_ns,
                )
            )
            try:
                async with websockets.connect(
                    WS_URL,
                    ping_interval=20,
                    ping_timeout=60,
                    open_timeout=20,
                    max_queue=100_000,
                ) as websocket:
                    opened_wall_ns = time.time_ns()
                    opened_mono_ns = time.monotonic_ns()
                    await advance_daily_partition(
                        opened_wall_ns,
                        opened_mono_ns,
                    )
                    active_epoch = epoch
                    router.connection_opened(epoch)
                    bank.broadcast(
                        _transport_record(
                            "connection_opened",
                            epoch,
                            wall_ns=opened_wall_ns,
                            mono_ns=opened_mono_ns,
                        )
                    )
                    while stop_event is None or not stop_event.is_set():
                        now = _utc_now()
                        if bank.current_day is not None and now.date() > bank.current_day:
                            boundary_wall_ns = time.time_ns()
                            boundary_mono_ns = time.monotonic_ns()
                            await advance_daily_partition(
                                boundary_wall_ns,
                                boundary_mono_ns,
                            )

                        try:
                            raw_message = await asyncio.wait_for(
                                websocket.recv(), timeout=1.0
                            )
                        except asyncio.TimeoutError:
                            continue
                        wall_ns = time.time_ns()
                        mono_ns = time.monotonic_ns()
                        await advance_daily_partition(wall_ns, mono_ns)
                        try:
                            payload = _parse_message(raw_message)
                        except Exception:
                            bank.broadcast(
                                _rejected_record(
                                    reason="JSON_PARSE_FAIL",
                                    epoch=epoch,
                                    wall_ns=wall_ns,
                                    mono_ns=mono_ns,
                                    observed_symbol=None,
                                )
                            )
                            continue
                        symbol, record = router.route(
                            payload,
                            epoch=epoch,
                            wall_ns=wall_ns,
                            mono_ns=mono_ns,
                        )
                        if symbol is None:
                            bank.broadcast(record)
                        else:
                            bank.emit(symbol, record)

                    closed_wall_ns = time.time_ns()
                    closed_mono_ns = time.monotonic_ns()
                    await advance_daily_partition(
                        closed_wall_ns,
                        closed_mono_ns,
                    )
                    bank.broadcast(
                        _transport_record(
                            "connection_closed",
                            epoch,
                            wall_ns=closed_wall_ns,
                            mono_ns=closed_mono_ns,
                        )
                    )
                    router.invalidate_all()
                    active_epoch = None
            except asyncio.CancelledError:
                raise
            except AcquisitionOperationalError:
                raise
            except Exception as exc:
                error_wall_ns = time.time_ns()
                error_mono_ns = time.monotonic_ns()
                await advance_daily_partition(error_wall_ns, error_mono_ns)
                router.invalidate_all()
                active_epoch = None
                bank.broadcast(
                    _transport_record(
                        "transport_error",
                        epoch,
                        wall_ns=error_wall_ns,
                        mono_ns=error_mono_ns,
                        detail=repr(exc),
                    )
                )
                if stop_event is None or not stop_event.is_set():
                    await asyncio.sleep(2.0)
    finally:
        if bank.sinks:
            if not any(
                sink.operational_failure is not None
                for sink in bank.sinks.values()
            ):
                bank.broadcast(
                    _transport_record(
                        "collector_stopped",
                        active_epoch or epoch,
                    )
                )
            await bank.close_day()

    return {
        "experiment_id": EXPERIMENT_ID,
        "collector_run_id": identity.collector_run_id,
        "frozen_implementation_commit": implementation_commit,
        "symbols": list(INITIAL_SYMBOLS),
        "connection_epochs": epoch,
        "unsupported_symbol_rejections": router.unsupported_rejections,
        "network_accessed_for_acquisition": True,
        **no_analysis_guards(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args(argv)
    implementation_commit = _full_hex_commit(args.frozen_commit)
    result = asyncio.run(
        collect_continuously(
            args.output_root,
            frozen_commit=implementation_commit,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

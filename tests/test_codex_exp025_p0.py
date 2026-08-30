import asyncio
import csv
import gzip
import inspect
import json
import tempfile
import threading
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import multimarket.codex_exp025_collect as collect
import multimarket.codex_exp025_finalize as finalize


TEST_DAY = date(2025, 1, 2)
TEST_COMMIT = "1" * 40


def _bounds() -> tuple[int, int]:
    return finalize.day_bounds_us(TEST_DAY)


def _transport(
    event: str,
    offset_us: int,
    mono_ns: int,
    *,
    epoch: int = 1,
    **extra,
) -> dict:
    start_us, _ = _bounds()
    wall_ns = (start_us + offset_us) * 1000
    return {
        "record_type": "transport",
        "event": event,
        "connection_epoch": epoch,
        "receive_wall_ns": wall_ns,
        "receive_wall_utc": collect._iso_from_ns(wall_ns),
        "receive_monotonic_ns": mono_ns,
        **extra,
    }


def _day_started(*, armed: bool, offset_us: int = 0) -> dict:
    start_us, _ = _bounds()
    collector_started_ns = (
        (start_us - 1_000_000) * 1000
        if armed
        else (start_us + 3_600_000_000) * 1000
    )
    wall_ns = (start_us + offset_us) * 1000
    start = datetime(TEST_DAY.year, TEST_DAY.month, TEST_DAY.day, tzinfo=timezone.utc)
    return {
        "record_type": "transport",
        "event": "day_started",
        "connection_epoch": 0,
        "receive_wall_ns": wall_ns,
        "receive_wall_utc": collect._iso_from_ns(wall_ns),
        "receive_monotonic_ns": 1,
        "experiment_id": collect.EXPERIMENT_ID,
        "collector_run_id": "synthetic-run",
        "process_id": 123,
        "frozen_implementation_commit": TEST_COMMIT,
        "collector_started_wall_ns": collector_started_ns,
        "collector_started_utc": collect._iso_from_ns(collector_started_ns),
        "armed_before_day_start": armed,
        "symbol": "BTCUSDT",
        "collection_day": TEST_DAY.isoformat(),
        "collection_start_utc": start.isoformat(),
        "collection_end_utc": (start + timedelta(days=1)).isoformat(),
        "initial_symbols": list(collect.INITIAL_SYMBOLS),
        "venue": collect.VENUE,
        "asset_class": collect.ASSET_CLASS,
        "source": "BINANCE_FUTURES_BOOKTICKER_WEBSOCKET",
    }


def _quote(
    offset_us: int,
    mono_ns: int,
    update_id: int,
    *,
    symbol: str = "BTCUSDT",
    epoch: int = 1,
    bid: float = 100.0,
    ask: float = 100.2,
    bid_size: float = 1.0,
    ask_size: float = 2.0,
) -> dict:
    start_us, _ = _bounds()
    wall_ns = (start_us + offset_us) * 1000
    return {
        "record_type": "quote",
        "market": collect.MARKET,
        "symbol": symbol,
        "venue": collect.VENUE,
        "asset_class": collect.ASSET_CLASS,
        "connection_epoch": epoch,
        "receive_wall_ns": wall_ns,
        "receive_timestamp_utc": collect._iso_from_ns(wall_ns),
        "receive_monotonic_ns": mono_ns,
        "source_timestamp_if_available": None,
        "exchange_event_time_ms": None,
        "exchange_transaction_time_ms": None,
        "update_id": update_id,
        "bid": bid,
        "ask": ask,
        "bid_size": bid_size,
        "ask_size": ask_size,
        "best_bid": bid,
        "best_ask": ask,
        "best_bid_qty": bid_size,
        "best_ask_qty": ask_size,
    }


def _rollover() -> dict:
    _, end_us = _bounds()
    return _transport(
        "day_rollover",
        end_us - _bounds()[0],
        10_000,
        completed_day=TEST_DAY.isoformat(),
        next_day=(TEST_DAY + timedelta(days=1)).isoformat(),
    )


def _complete_records(*events: dict, armed: bool = True) -> list[dict]:
    return [
        _day_started(
            armed=armed,
            offset_us=0 if armed else 3_600_000_000,
        ),
        _transport("connection_open_attempt", 0, 2),
        _transport("connection_opened", 0, 3),
        *events,
        _rollover(),
    ]


def _write_fixture(path: Path, records: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")


def _read_grid(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


async def _wait_for_thread_event(
    event: threading.Event,
    *,
    timeout: float = 2.0,
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not event.is_set():
        if loop.time() >= deadline:
            raise AssertionError("synthetic writer synchronization timed out")
        await asyncio.sleep(0.001)


class _SyntheticThreadWriter:
    def __init__(self, path: Path, *, block_predicate=None):
        self.path = path
        self.block_predicate = block_predicate
        self.entered = threading.Event()
        self.release = threading.Event()
        self.written = threading.Event()
        self.closed_event = threading.Event()
        self.records: list[dict] = []
        self._lock = threading.Lock()
        self._blocked_once = False

    def write(self, record: dict) -> None:
        should_block = bool(
            self.block_predicate is not None
            and not self._blocked_once
            and self.block_predicate(record)
        )
        if should_block:
            self._blocked_once = True
            self.entered.set()
            if not self.release.wait(5.0):
                raise RuntimeError("synthetic writer was not released")
        with self._lock:
            self.records.append(record)
        self.written.set()

    def close(self) -> None:
        self.closed_event.set()


class Exp025IdentityAndRoutingTests(unittest.TestCase):
    def test_exact_initial_symbol_set_and_combined_stream(self):
        self.assertEqual(
            collect.INITIAL_SYMBOLS,
            ("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        )
        self.assertEqual(collect.SUPPORTED_SYMBOLS, frozenset(collect.INITIAL_SYMBOLS))
        self.assertEqual(collect.WS_URL.count("@bookTicker"), 3)
        for symbol in collect.INITIAL_SYMBOLS:
            self.assertIn(f"{symbol.lower()}@bookTicker", collect.WS_URL)

    def test_normalized_quote_schema_and_exact_symbol(self):
        state = collect.SymbolState("ETHUSDT")
        record = collect.process_quote_payload(
            state,
            {"s": "ETHUSDT", "b": "10", "B": "2", "a": "11", "A": "3"},
            epoch=7,
            wall_ns=1_000_000_000,
            mono_ns=100,
        )
        required = {
            "market",
            "symbol",
            "venue",
            "asset_class",
            "receive_timestamp_utc",
            "bid",
            "ask",
            "bid_size",
            "ask_size",
            "source_timestamp_if_available",
            "connection_epoch",
        }
        self.assertTrue(required.issubset(record))
        self.assertEqual(record["symbol"], "ETHUSDT")
        self.assertEqual(record["connection_epoch"], 7)

    def test_cross_symbol_routing_and_state_isolation(self):
        router = collect.MultiSymbolRouter()
        router.connection_opened(1)
        btc_payload = {"s": "BTCUSDT", "b": "100", "B": "1", "a": "101", "A": "2"}
        eth_payload = {"s": "ETHUSDT", "b": "10", "B": "3", "a": "11", "A": "4"}
        btc_symbol, btc = router.route(
            btc_payload, epoch=1, wall_ns=100, mono_ns=100
        )
        btc_snapshot = dict(router.states["BTCUSDT"].latest_quote)
        eth_symbol, eth = router.route(
            eth_payload, epoch=1, wall_ns=101, mono_ns=101
        )
        self.assertEqual((btc_symbol, btc["symbol"]), ("BTCUSDT", "BTCUSDT"))
        self.assertEqual((eth_symbol, eth["symbol"]), ("ETHUSDT", "ETHUSDT"))
        self.assertEqual(router.states["BTCUSDT"].latest_quote, btc_snapshot)
        self.assertEqual(router.states["BTCUSDT"].accepted_quotes, 1)
        self.assertEqual(router.states["ETHUSDT"].accepted_quotes, 1)
        self.assertEqual(router.states["SOLUSDT"].accepted_quotes, 0)
        self.assertIsNone(router.states["SOLUSDT"].latest_quote)

    def test_wrong_and_unsupported_symbols_are_rejected_without_contamination(self):
        router = collect.MultiSymbolRouter()
        router.connection_opened(1)
        before = {name: state.accepted_quotes for name, state in router.states.items()}
        symbol, rejected = router.route(
            {"s": "XRPUSDT", "b": "1", "B": "1", "a": "2", "A": "1"},
            epoch=1,
            wall_ns=100,
            mono_ns=100,
        )
        self.assertIsNone(symbol)
        self.assertEqual(rejected["reason"], "UNSUPPORTED_SYMBOL")
        self.assertEqual(
            {name: state.accepted_quotes for name, state in router.states.items()},
            before,
        )
        state = collect.SymbolState("BTCUSDT")
        wrong = collect.process_quote_payload(
            state,
            {"s": "ETHUSDT", "b": "1", "B": "1", "a": "2", "A": "1"},
            epoch=1,
            wall_ns=100,
            mono_ns=100,
        )
        self.assertEqual(wrong["reason"], "WRONG_SYMBOL")
        self.assertIsNone(state.latest_quote)

    def test_price_quantity_and_clock_validity_are_strict(self):
        base = {"s": "SOLUSDT", "b": "100", "B": "1", "a": "101", "A": "2"}
        cases = (
            ({**base, "a": "100"}, "INVALID_OR_CROSSED_PRICE"),
            ({**base, "B": "-1"}, "NEGATIVE_QUANTITY"),
            ({**base, "a": "nan"}, "NONFINITE"),
        )
        for payload, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(
                    collect._validate_payload(payload, expected_symbol="SOLUSDT"),
                    (False, reason),
                )
        state = collect.SymbolState("SOLUSDT")
        accepted = collect.process_quote_payload(
            state, base, epoch=1, wall_ns=100, mono_ns=200
        )
        self.assertEqual(accepted["record_type"], "quote")
        self.assertEqual(
            collect.process_quote_payload(
                state, base, epoch=1, wall_ns=99, mono_ns=201
            )["reason"],
            "WALL_CLOCK_REVERSAL",
        )
        self.assertEqual(
            collect.process_quote_payload(
                state, base, epoch=1, wall_ns=101, mono_ns=199
            )["reason"],
            "MONOTONIC_CLOCK_REVERSAL",
        )
        self.assertEqual(state.accepted_quotes, 1)

    def test_reconnect_invalidates_every_symbol_and_requires_fresh_quotes(self):
        router = collect.MultiSymbolRouter()
        router.connection_opened(1)
        router.route(
            {"s": "BTCUSDT", "b": "100", "B": "1", "a": "101", "A": "2"},
            epoch=1,
            wall_ns=100,
            mono_ns=100,
        )
        router.invalidate_all()
        self.assertTrue(
            all(state.latest_quote is None for state in router.states.values())
        )
        self.assertTrue(
            all(
                state.active_connection_epoch is None
                for state in router.states.values()
            )
        )
        router.connection_opened(2)
        self.assertTrue(
            all(state.latest_quote is None for state in router.states.values())
        )


class Exp025WriterAndRolloverTests(unittest.TestCase):
    def test_raw_writer_is_exclusive_and_closes_valid_gzip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "raw.jsonl.gz"
            writer = collect.RawWriter(path)
            writer.write({"record_type": "synthetic"})
            writer.close()
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                self.assertEqual(json.loads(handle.readline())["record_type"], "synthetic")
            with self.assertRaises(FileExistsError):
                collect.RawWriter(path)

    def test_symbol_writer_routing_is_nonawaiting_and_worker_is_threaded(self):
        self.assertFalse(inspect.iscoroutinefunction(collect.AsyncSymbolSink.emit))
        self.assertIn(
            "run_in_executor",
            inspect.getsource(collect.AsyncSymbolSink._worker),
        )
        self.assertIn(
            "put_nowait",
            inspect.getsource(collect.AsyncSymbolSink.emit),
        )
        self.assertEqual(collect.QUEUE_MAXSIZE, 100_000)
        self.assertEqual(collect.WRITER_SHUTDOWN_TIMEOUT_S, 30.0)

    def test_runtime_symbol_writers_are_behaviorally_isolated(self):
        async def scenario():
            btc_writer = _SyntheticThreadWriter(
                Path("BTCUSDT.synthetic"),
                block_predicate=lambda record: True,
            )
            eth_writer = _SyntheticThreadWriter(Path("ETHUSDT.synthetic"))
            sol_writer = _SyntheticThreadWriter(Path("SOLUSDT.synthetic"))
            writers = {
                "BTCUSDT": btc_writer,
                "ETHUSDT": eth_writer,
                "SOLUSDT": sol_writer,
            }
            sinks = {
                symbol: collect.AsyncSymbolSink(
                    symbol,
                    writer,
                    shutdown_timeout_s=2.0,
                )
                for symbol, writer in writers.items()
            }
            worker_threads = []
            try:
                sinks["BTCUSDT"].emit({"symbol": "BTCUSDT", "sequence": 1})
                await _wait_for_thread_event(btc_writer.entered)

                sinks["ETHUSDT"].emit({"symbol": "ETHUSDT", "sequence": 2})
                sinks["SOLUSDT"].emit({"symbol": "SOLUSDT", "sequence": 3})
                await asyncio.gather(
                    _wait_for_thread_event(eth_writer.written),
                    _wait_for_thread_event(sol_writer.written),
                )

                responsive = asyncio.Event()
                asyncio.get_running_loop().call_soon(responsive.set)
                await asyncio.wait_for(responsive.wait(), timeout=1.0)

                self.assertEqual(btc_writer.records, [])
                self.assertEqual(
                    eth_writer.records,
                    [{"symbol": "ETHUSDT", "sequence": 2}],
                )
                self.assertEqual(
                    sol_writer.records,
                    [{"symbol": "SOLUSDT", "sequence": 3}],
                )
            finally:
                btc_writer.release.set()
                await asyncio.gather(*(sink.close() for sink in sinks.values()))
                for sink in sinks.values():
                    worker_threads.extend(tuple(sink.executor._threads))

            self.assertEqual(
                btc_writer.records,
                [{"symbol": "BTCUSDT", "sequence": 1}],
            )
            self.assertTrue(all(writer.closed_event.is_set() for writer in writers.values()))
            self.assertTrue(all(sink.task.done() for sink in sinks.values()))
            self.assertTrue(all(not thread.is_alive() for thread in worker_threads))

        asyncio.run(scenario())

    def test_normal_sink_close_drains_and_terminates(self):
        async def scenario():
            writer = _SyntheticThreadWriter(Path("ETHUSDT.synthetic"))
            sink = collect.AsyncSymbolSink(
                "ETHUSDT",
                writer,
                shutdown_timeout_s=1.0,
            )
            sink.emit({"symbol": "ETHUSDT"})
            await sink.close()
            self.assertTrue(sink.closed)
            self.assertTrue(sink.task.done())
            self.assertTrue(writer.closed_event.is_set())
            self.assertEqual(writer.records, [{"symbol": "ETHUSDT"}])
            self.assertTrue(
                all(not thread.is_alive() for thread in sink.executor._threads)
            )

        asyncio.run(scenario())

    def test_stuck_writer_close_times_out_and_is_surfaced(self):
        async def scenario():
            writer = _SyntheticThreadWriter(
                Path("BTCUSDT.synthetic"),
                block_predicate=lambda record: True,
            )
            sink = collect.AsyncSymbolSink(
                "BTCUSDT",
                writer,
                shutdown_timeout_s=0.05,
            )
            sink.emit({"symbol": "BTCUSDT"})
            await _wait_for_thread_event(writer.entered)
            try:
                with self.assertRaises(collect.WriterShutdownTimeout) as raised:
                    await sink.close()
                self.assertIn("BTCUSDT", str(raised.exception))
                self.assertIn("0.050s", str(raised.exception))
                self.assertIs(sink.operational_failure, raised.exception)
                self.assertFalse(sink.task.done())
            finally:
                writer.release.set()
                sink.shutdown_timeout_s = 2.0
                await sink.close()

            self.assertTrue(sink.task.done())
            self.assertTrue(writer.closed_event.is_set())
            self.assertTrue(
                all(not thread.is_alive() for thread in sink.executor._threads)
            )

        asyncio.run(scenario())

    def test_tiny_queue_overflow_is_explicit_and_marks_symbol_day(self):
        async def scenario(root: Path):
            started = datetime(2025, 1, 1, 23, tzinfo=timezone.utc)
            identity = collect.CollectorIdentity(
                "run",
                123,
                TEST_COMMIT,
                int(started.timestamp() * 1_000_000_000),
                started.isoformat(),
            )
            writers: dict[str, _SyntheticThreadWriter] = {}

            def factory(path: Path):
                symbol = path.parent.name
                writer = _SyntheticThreadWriter(
                    path,
                    block_predicate=(
                        (lambda record: True) if symbol == "BTCUSDT" else None
                    ),
                )
                writers[symbol] = writer
                return writer

            bank = collect.AsyncDailyRawBank(
                root,
                identity,
                queue_maxsize=1,
                writer_shutdown_timeout_s=2.0,
                writer_factory=factory,
            )
            await bank.open_day(
                TEST_DAY,
                wall_ns=int(
                    datetime(2025, 1, 2, tzinfo=timezone.utc).timestamp()
                    * 1_000_000_000
                ),
                mono_ns=1,
            )
            await _wait_for_thread_event(writers["BTCUSDT"].entered)
            try:
                bank.emit("BTCUSDT", {"symbol": "BTCUSDT", "sequence": 1})
                with self.assertRaises(collect.SymbolQueueOverflow) as raised:
                    bank.emit("BTCUSDT", {"symbol": "BTCUSDT", "sequence": 2})
                self.assertIn("BTCUSDT", str(raised.exception))
                self.assertIn("capacity 1", str(raised.exception))
                marker = collect.operational_failure_path(
                    root / collect.raw_relative_path("BTCUSDT", TEST_DAY)
                )
                self.assertTrue(marker.is_file())
                self.assertEqual(
                    json.loads(marker.read_text())["failure_type"],
                    "SymbolQueueOverflow",
                )
                self.assertFalse(
                    collect.operational_failure_path(
                        root / collect.raw_relative_path("ETHUSDT", TEST_DAY)
                    ).exists()
                )
            finally:
                writers["BTCUSDT"].release.set()
                await bank.close_day()

        with tempfile.TemporaryDirectory() as temp_dir:
            asyncio.run(scenario(Path(temp_dir)))

    def test_rollover_close_failure_is_explicit_and_cannot_be_full(self):
        async def scenario(root: Path):
            started = datetime(2025, 1, 1, 23, tzinfo=timezone.utc)
            identity = collect.CollectorIdentity(
                "run",
                123,
                TEST_COMMIT,
                int(started.timestamp() * 1_000_000_000),
                started.isoformat(),
            )
            writers: dict[str, _SyntheticThreadWriter] = {}
            created_paths: list[Path] = []

            def factory(path: Path):
                symbol = path.parent.name
                created_paths.append(path)
                writer = _SyntheticThreadWriter(
                    path,
                    block_predicate=(
                        lambda record: symbol == "BTCUSDT"
                        and record.get("event") == "day_rollover"
                    ),
                )
                writers[symbol] = writer
                return writer

            bank = collect.AsyncDailyRawBank(
                root,
                identity,
                writer_shutdown_timeout_s=0.05,
                writer_factory=factory,
            )
            midnight = datetime(2025, 1, 2, tzinfo=timezone.utc)
            await bank.open_day(
                TEST_DAY,
                wall_ns=int(midnight.timestamp() * 1_000_000_000),
                mono_ns=1,
            )
            rollover = asyncio.create_task(
                bank.rollover(
                    TEST_DAY + timedelta(days=1),
                    wall_ns=int(
                        (midnight + timedelta(days=1)).timestamp()
                        * 1_000_000_000
                    ),
                    mono_ns=2,
                    active_epoch=1,
                )
            )
            await _wait_for_thread_event(writers["BTCUSDT"].entered)
            try:
                with self.assertRaises(collect.WriterShutdownTimeout):
                    await rollover
                self.assertEqual(bank.current_day, TEST_DAY)
                self.assertFalse(
                    any(
                        path.name == f"{(TEST_DAY + timedelta(days=1)).isoformat()}.jsonl.gz"
                        for path in created_paths
                    )
                )
                marker = collect.operational_failure_path(
                    root / collect.raw_relative_path("BTCUSDT", TEST_DAY)
                )
                self.assertTrue(marker.is_file())
            finally:
                writers["BTCUSDT"].release.set()
                bank.writer_shutdown_timeout_s = 2.0
                bank.sinks["BTCUSDT"].shutdown_timeout_s = 2.0
                await bank.close_day()

            raw = root / collect.raw_relative_path("BTCUSDT", TEST_DAY)
            raw.write_bytes(b"synthetic raw blocked by failure marker")
            grid = root / "grid.csv"
            audit = root / "audit.json"
            inventory = root / "inventory.json"
            with self.assertRaisesRegex(RuntimeError, "operational-failure marker"):
                finalize.run(
                    raw,
                    grid,
                    audit,
                    inventory,
                    symbol="BTCUSDT",
                    day=TEST_DAY,
                )
            self.assertFalse(grid.exists())
            self.assertFalse(audit.exists())
            self.assertFalse(inventory.exists())

        with tempfile.TemporaryDirectory() as temp_dir:
            asyncio.run(scenario(Path(temp_dir)))

    def test_utc_rollover_closes_old_files_and_exclusively_opens_next_day(self):
        async def scenario(root: Path):
            start = datetime(2025, 1, 2, 12, tzinfo=timezone.utc)
            identity = collect.CollectorIdentity(
                collector_run_id="synthetic-run",
                process_id=123,
                frozen_implementation_commit=TEST_COMMIT,
                collector_started_wall_ns=int(start.timestamp() * 1_000_000_000),
                collector_started_utc=start.isoformat(),
            )
            bank = collect.AsyncDailyRawBank(root, identity)
            await bank.open_day(
                TEST_DAY,
                wall_ns=identity.collector_started_wall_ns,
                mono_ns=1,
            )
            next_day = TEST_DAY + timedelta(days=1)
            boundary = datetime(2025, 1, 3, tzinfo=timezone.utc)
            await bank.rollover(
                next_day,
                wall_ns=int(boundary.timestamp() * 1_000_000_000),
                mono_ns=2,
                active_epoch=4,
            )
            await bank.close_day()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            asyncio.run(scenario(root))
            for symbol in collect.INITIAL_SYMBOLS:
                first = root / collect.raw_relative_path(symbol, TEST_DAY)
                second = root / collect.raw_relative_path(
                    symbol, TEST_DAY + timedelta(days=1)
                )
                self.assertTrue(first.is_file())
                self.assertTrue(second.is_file())
                with gzip.open(first, "rt", encoding="utf-8") as handle:
                    first_records = [json.loads(line) for line in handle]
                with gzip.open(second, "rt", encoding="utf-8") as handle:
                    second_records = [json.loads(line) for line in handle]
                self.assertEqual(first_records[0]["event"], "day_started")
                self.assertFalse(first_records[0]["armed_before_day_start"])
                self.assertEqual(first_records[-1]["event"], "day_rollover")
                self.assertEqual(second_records[0]["event"], "day_started")
                self.assertTrue(second_records[0]["armed_before_day_start"])
                self.assertEqual(second_records[1]["event"], "connection_carried")

    def test_existing_daily_partition_refuses_before_any_writer_is_opened(self):
        async def scenario(root: Path):
            started = datetime(2025, 1, 2, tzinfo=timezone.utc)
            identity = collect.CollectorIdentity(
                "run", 123, TEST_COMMIT, int(started.timestamp() * 1e9), started.isoformat()
            )
            bank = collect.AsyncDailyRawBank(root, identity)
            with self.assertRaises(FileExistsError):
                await bank.open_day(TEST_DAY, wall_ns=int(started.timestamp() * 1e9), mono_ns=1)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            existing = root / collect.raw_relative_path("ETHUSDT", TEST_DAY)
            existing.parent.mkdir(parents=True)
            existing.touch()
            asyncio.run(scenario(root))
            self.assertFalse(
                (root / collect.raw_relative_path("BTCUSDT", TEST_DAY)).exists()
            )
            self.assertFalse(
                (root / collect.raw_relative_path("SOLUSDT", TEST_DAY)).exists()
            )

    def test_collector_has_no_backfill_or_single_symbol_date_interface(self):
        source = inspect.getsource(collect.main)
        self.assertNotIn("--backfill", source)
        self.assertNotIn("--symbol", source)
        self.assertNotIn("--day", source)
        with mock.patch.object(collect.asyncio, "run") as run:
            with self.assertRaises(SystemExit):
                collect.main(
                    [
                        "--output-root",
                        "synthetic",
                        "--frozen-commit",
                        TEST_COMMIT,
                        "--backfill",
                        "2025-01-01",
                    ]
                )
        run.assert_not_called()


class Exp025GridSemanticsTests(unittest.TestCase):
    def test_grid_constants_and_full_day_shape_are_exact(self):
        self.assertEqual(finalize.GRID_US, 250_000)
        self.assertEqual(finalize.EXPECTED_ROWS, 345_600)
        self.assertEqual(finalize.MAX_AGE_US, 2_000_000)
        start_us, end_us = _bounds()
        self.assertEqual(end_us - start_us, 86_400_000_000)
        self.assertEqual(
            start_us + (finalize.EXPECTED_ROWS - 1) * finalize.GRID_US,
            end_us - finalize.GRID_US,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            grid = Path(temp_dir) / "full.csv"
            diagnostics = finalize.build_grid(
                [], grid, symbol="SOLUSDT", day=TEST_DAY
            )
            with grid.open("rb") as handle:
                rows = sum(1 for _ in handle) - 1
            self.assertEqual(rows, 345_600)
            self.assertEqual(diagnostics["rows"], 345_600)
            self.assertEqual(diagnostics["first_timestamp_us"], start_us)
            self.assertEqual(diagnostics["last_timestamp_us"], end_us - 250_000)

    def test_no_future_quote_and_exact_boundary_use(self):
        records = _complete_records(
            _quote(100_000, 4, 1),
            _quote(250_000, 5, 2, bid=101.0, ask=101.2),
            _quote(375_000, 6, 3, bid=102.0, ask=102.2),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw, grid = root / "raw.gz", root / "grid.csv"
            _write_fixture(raw, records)
            raw_diag, grid_diag = finalize.stream_raw_to_grid(
                raw, grid, symbol="BTCUSDT", day=TEST_DAY, expected_rows=4
            )
            rows = _read_grid(grid)
        self.assertEqual(rows[0]["book_valid"], "0")
        self.assertEqual(rows[1]["source_update_id"], "2")
        self.assertEqual(rows[2]["source_update_id"], "3")
        self.assertEqual(rows[2]["quote_age_ms"], "125.0")
        self.assertEqual(grid_diag["future_quote_violations"], 0)
        self.assertEqual(raw_diag["accepted_quotes"], 3)

    def test_stale_quote_after_two_seconds_is_invalid(self):
        records = _complete_records(_quote(0, 4, 1))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw, grid = root / "raw.gz", root / "grid.csv"
            _write_fixture(raw, records)
            _, diagnostics = finalize.stream_raw_to_grid(
                raw, grid, symbol="BTCUSDT", day=TEST_DAY, expected_rows=10
            )
            rows = _read_grid(grid)
        self.assertEqual(rows[8]["book_valid"], "1")
        self.assertEqual(rows[8]["quote_age_ms"], "2000.0")
        self.assertEqual(rows[9]["book_valid"], "0")
        self.assertEqual(rows[9]["quote_age_ms"], "2250.0")
        self.assertEqual(diagnostics["stale_or_unavailable_rows"], 1)

    def test_transport_error_and_new_epoch_require_fresh_quote(self):
        records = _complete_records(
            _quote(0, 4, 1),
            _transport("transport_error", 300_000, 5, epoch=1),
            _transport("connection_open_attempt", 400_000, 6, epoch=2),
            _transport("connection_opened", 450_000, 7, epoch=2),
            _quote(600_000, 8, 2, epoch=1),
            _quote(800_000, 9, 3, epoch=2, bid=102.0, ask=102.2),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw, grid = root / "raw.gz", root / "grid.csv"
            _write_fixture(raw, records)
            _, diagnostics = finalize.stream_raw_to_grid(
                raw, grid, symbol="BTCUSDT", day=TEST_DAY, expected_rows=5
            )
            rows = _read_grid(grid)
        self.assertEqual([row["book_valid"] for row in rows], ["1", "1", "0", "0", "1"])
        self.assertEqual(rows[-1]["source_update_id"], "3")
        self.assertGreaterEqual(diagnostics["reconnect_invalid_rows"], 2)

    def test_finalization_is_deterministic_for_each_symbol(self):
        for symbol in collect.INITIAL_SYMBOLS:
            with self.subTest(symbol=symbol), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                records = _complete_records(
                    _quote(0, 4, 1, symbol=symbol),
                    _quote(625_000, 5, 2, symbol=symbol, bid=101, ask=101.2),
                )
                records[0]["symbol"] = symbol
                raw = root / "raw.gz"
                first, second = root / "first.csv", root / "second.csv"
                _write_fixture(raw, records)
                first_raw, first_grid = finalize.stream_raw_to_grid(
                    raw, first, symbol=symbol, day=TEST_DAY, expected_rows=8
                )
                second_raw, second_grid = finalize.stream_raw_to_grid(
                    raw, second, symbol=symbol, day=TEST_DAY, expected_rows=8
                )
                self.assertEqual(first.read_bytes(), second.read_bytes())
                self.assertEqual(first_raw, second_raw)
                self.assertEqual(first_grid, second_grid)

    def test_coverage_is_valid_rows_divided_by_exact_grid_rows(self):
        records = _complete_records(_quote(0, 4, 1))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw, grid = root / "raw.gz", root / "grid.csv"
            _write_fixture(raw, records)
            _, diagnostics = finalize.stream_raw_to_grid(
                raw, grid, symbol="BTCUSDT", day=TEST_DAY, expected_rows=12
            )
        self.assertEqual(diagnostics["valid_rows"], 9)
        self.assertEqual(diagnostics["valid_coverage"], 9 / 12)


class Exp025StatusAuditAndInventoryTests(unittest.TestCase):
    def _run_fixture(self, records: list[dict], *, symbol: str = "BTCUSDT"):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        raw = root / "raw.jsonl.gz"
        grid = root / "grid.csv"
        audit = root / "audit.json"
        inventory = root / "inventory" / symbol / f"{TEST_DAY.isoformat()}.json"
        _write_fixture(raw, records)
        with mock.patch.object(finalize, "EXPECTED_ROWS", 4):
            payload = finalize.run(
                raw,
                grid,
                audit,
                inventory,
                symbol=symbol,
                day=TEST_DAY,
            )
        return payload, raw, grid, audit, inventory

    def test_full_day_status_requires_pre_midnight_arming_and_rollover(self):
        full, *_ = self._run_fixture(
            _complete_records(_quote(0, 4, 1), armed=True)
        )
        self.assertEqual(full["status"], finalize.STATUS_FULL)
        self.assertTrue(full["integrity_gates"]["collector_armed_before_utc_midnight"])
        self.assertTrue(full["integrity_gates"]["day_rollover_observed_after_day"])

        partial_records = _complete_records(armed=False)
        partial, *_ = self._run_fixture(partial_records)
        self.assertEqual(partial["status"], finalize.STATUS_PARTIAL)
        self.assertFalse(
            partial["integrity_gates"]["collector_armed_before_utc_midnight"]
        )

        corrupt_partial = _complete_records(
            _quote(3_600_000_000, 4, 1, ask=99.0),
            armed=False,
        )
        corrupt, *_ = self._run_fixture(corrupt_partial)
        self.assertEqual(corrupt["status"], finalize.STATUS_FAIL)

    def test_missing_rollover_or_integrity_failure_is_not_full(self):
        missing_rollover = _complete_records(_quote(0, 4, 1))[:-1]
        payload, *_ = self._run_fixture(missing_rollover)
        self.assertEqual(payload["status"], finalize.STATUS_FAIL)
        crossed = _complete_records(_quote(0, 4, 1, ask=99.0))
        payload, *_ = self._run_fixture(crossed)
        self.assertEqual(payload["status"], finalize.STATUS_FAIL)
        self.assertFalse(
            payload["integrity_gates"]["no_invalid_crossed_price_accepted"]
        )

    def test_hashes_bytes_diagnostics_and_no_analysis_guards_are_recorded(self):
        payload, raw, grid, audit, _ = self._run_fixture(
            _complete_records(_quote(0, 4, 1))
        )
        self.assertEqual(payload["raw_bytes"], raw.stat().st_size)
        self.assertEqual(payload["grid_bytes"], grid.stat().st_size)
        self.assertEqual(payload["raw_sha256"], finalize.sha256_file(raw))
        self.assertEqual(payload["grid_sha256"], finalize.sha256_file(grid))
        self.assertEqual(json.loads(audit.read_text())["status"], finalize.STATUS_FULL)
        self.assertEqual(payload["raw_diagnostics"]["first_accepted_quote_utc"], _quote(0, 4, 1)["receive_timestamp_utc"])
        self.assertFalse(payload["predictive_metrics_calculated"])
        for name, value in collect.no_analysis_guards().items():
            self.assertIs(value, False)
            self.assertIs(payload[name], False)
            self.assertIs(payload["integrity_gates"][name], False)

    def test_audit_and_inventory_are_immutable(self):
        records = _complete_records(_quote(0, 4, 1))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "raw.gz"
            _write_fixture(raw, records)
            for occupied_name in ("grid.csv", "audit.json", "inventory.json"):
                with self.subTest(occupied_name=occupied_name):
                    grid = root / "grid.csv"
                    audit = root / "audit.json"
                    inventory = root / "inventory.json"
                    for path in (grid, audit, inventory):
                        if path.exists():
                            path.unlink()
                    occupied = root / occupied_name
                    occupied.write_text("immutable", encoding="utf-8")
                    with self.assertRaises(FileExistsError):
                        finalize.run(
                            raw,
                            grid,
                            audit,
                            inventory,
                            symbol="BTCUSDT",
                            day=TEST_DAY,
                        )
                    self.assertEqual(occupied.read_text(), "immutable")

    def test_inventory_is_metadata_only_and_counts_untouched_full_days(self):
        payload, _, _, _, inventory = self._run_fixture(
            _complete_records(_quote(0, 4, 1))
        )
        entry = json.loads(inventory.read_text(encoding="utf-8"))
        self.assertEqual(set(entry), set(finalize.INVENTORY_FIELDS))
        self.assertEqual(entry["status"], finalize.STATUS_FULL)
        lowered = {name.lower() for name in entry}
        self.assertTrue(finalize.FORBIDDEN_INVENTORY_FIELDS.isdisjoint(lowered))
        entries = [
            entry,
            {**entry, "symbol": "ETHUSDT"},
            {**entry, "symbol": "ETHUSDT", "day": "2025-01-03"},
            {**entry, "symbol": "SOLUSDT", "status": finalize.STATUS_PARTIAL},
        ]
        self.assertEqual(
            finalize.full_day_counts(entries),
            {"BTCUSDT": 1, "ETHUSDT": 2, "SOLUSDT": 0},
        )
        self.assertEqual(
            finalize.untouched_full_day_counts(
                entries,
                analytical_openings=(
                    {"symbol": "ETHUSDT", "day": "2025-01-03"},
                ),
            ),
            {"BTCUSDT": 1, "ETHUSDT": 1, "SOLUSDT": 0},
        )
        self.assertEqual(payload["status"], finalize.STATUS_FULL)

    def test_inventory_path_is_one_entry_per_symbol_day(self):
        for symbol in collect.INITIAL_SYMBOLS:
            path = finalize.inventory_relative_path(symbol, TEST_DAY)
            self.assertEqual(
                str(path),
                f"multimarket/inventory/{symbol}/{TEST_DAY.isoformat()}.json",
            )

    def test_public_finalizer_has_no_row_count_override(self):
        self.assertNotIn("expected_rows", inspect.signature(finalize.run).parameters)


class Exp025ScopeSafetyTests(unittest.TestCase):
    def test_modules_have_no_predictive_or_trading_engine_dependencies(self):
        collector_source = inspect.getsource(collect)
        finalizer_source = inspect.getsource(finalize)
        forbidden_imports = (
            "sklearn",
            "LogisticRegression",
            "StandardScaler",
            "roc_auc_score",
            "average_precision_score",
            "executable_fixed_horizon",
            "predict_proba",
            "order placement",
        )
        for source in (collector_source, finalizer_source):
            for forbidden in forbidden_imports:
                self.assertNotIn(forbidden, source)
        self.assertNotIn("codex_exp022", finalizer_source)
        self.assertNotIn("codex_exp023", finalizer_source)
        self.assertNotIn("codex_exp024", finalizer_source)
        self.assertFalse(hasattr(collect, "backfill"))
        self.assertFalse(hasattr(finalize, "score"))

    def test_no_august_exp024_or_railway_artifact_access_is_encoded(self):
        for module in (collect, finalize):
            source = inspect.getsource(module)
            self.assertNotIn("2026-08-30", source)
            self.assertNotIn("2026-08-28", source)
            self.assertNotIn("exp024", source.lower())
            self.assertNotIn("railway", source.lower())
        self.assertNotIn("requests", inspect.getsource(collect))
        self.assertNotIn("urlopen", inspect.getsource(collect))

    def test_tests_never_invoke_network_collector(self):
        with mock.patch.object(
            collect.websockets,
            "connect",
            side_effect=AssertionError("network forbidden in synthetic tests"),
        ) as connect:
            router = collect.MultiSymbolRouter()
            router.connection_opened(1)
            router.route(
                {"s": "BTCUSDT", "b": "1", "B": "1", "a": "2", "A": "1"},
                epoch=1,
                wall_ns=1,
                mono_ns=1,
            )
        connect.assert_not_called()

    def test_invalid_payload_is_nonpredictive(self):
        payload = finalize.invalid_payload(
            RuntimeError("synthetic"), symbol="BTCUSDT", day=TEST_DAY
        )
        self.assertEqual(payload["status"], finalize.STATUS_INVALID)
        self.assertFalse(payload["predictive_metrics_calculated"])
        for value in collect.no_analysis_guards().values():
            self.assertIs(value, False)
        json.dumps(payload, allow_nan=False)


if __name__ == "__main__":
    unittest.main()

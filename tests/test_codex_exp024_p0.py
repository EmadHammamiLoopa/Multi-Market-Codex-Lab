import asyncio
import csv
import gzip
import inspect
import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

import multimarket.codex_exp024_collect as collect
import multimarket.codex_exp024_finalize as finalize


FROZEN_COMMIT = "a" * 40


def _transport(
    offset_us: int,
    monotonic_ns: int,
    event: str,
    epoch: int,
    **extra,
) -> dict:
    return {
        "record_type": "transport",
        "event": event,
        "connection_epoch": epoch,
        "receive_wall_ns": (finalize.DAY_START_US + offset_us) * 1000,
        "receive_monotonic_ns": monotonic_ns,
        **extra,
    }


def _armed(offset_us: int = -1_000_000, **overrides) -> dict:
    record = _transport(
        offset_us,
        1,
        "collector_armed",
        0,
        experiment_id=collect.EXPERIMENT_ID,
        symbol=collect.SYMBOL,
        collection_day=collect.COLLECTION_DAY.isoformat(),
        collection_start_utc=collect.COLLECTION_START.isoformat(),
        collection_end_utc=collect.COLLECTION_END.isoformat(),
        frozen_implementation_commit=FROZEN_COMMIT,
        preregistration_sha256=collect.PREREGISTRATION_SHA256,
        readiness_artifact_sha256=collect.READINESS_ARTIFACT_SHA256,
    )
    record.update(overrides)
    return record


def _quote(
    offset_us: int,
    monotonic_ns: int,
    update_id: int,
    *,
    epoch: int = 1,
    symbol: str = "BTCUSDT",
    bid: float = 100.0,
    ask: float = 100.2,
    bid_qty: float = 1.0,
    ask_qty: float = 2.0,
) -> dict:
    return {
        "record_type": "quote",
        "connection_epoch": epoch,
        "receive_wall_ns": (finalize.DAY_START_US + offset_us) * 1000,
        "receive_monotonic_ns": monotonic_ns,
        "exchange_event_time_ms": 10_000 + update_id,
        "exchange_transaction_time_ms": 20_000 + update_id,
        "update_id": update_id,
        "symbol": symbol,
        "best_bid": bid,
        "best_bid_qty": bid_qty,
        "best_ask": ask,
        "best_ask_qty": ask_qty,
    }


def _complete_records(*quotes: dict) -> list[dict]:
    return [
        _armed(),
        _transport(0, 2, "connection_open_attempt", 1),
        _transport(0, 3, "connection_opened", 1),
        *quotes,
        _transport(
            finalize.DAY_END_US - finalize.DAY_START_US,
            1_000_000,
            "collection_end",
            1,
        ),
    ]


def _write_fixture(path: Path, records: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")


def _read_grid(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class Exp024P0IdentityAndCollectorTests(unittest.TestCase):
    def test_identity_day_source_and_lineage_are_frozen(self):
        self.assertEqual(collect.EXPERIMENT_ID, "CODEX-EXP-024-P0")
        self.assertEqual(finalize.EXPERIMENT_ID, "CODEX-EXP-024-P0")
        self.assertEqual(collect.SYMBOL, "BTCUSDT")
        self.assertEqual(collect.COLLECTION_DAY.isoformat(), "2026-08-30")
        self.assertEqual(
            str(collect.RAW_REL),
            "bookticker/BTCUSDT/2026-08-30.jsonl.gz",
        )
        self.assertEqual(
            collect.READINESS_ARTIFACT_SHA256,
            "4eaf158b2517cf6c0be2efc2e7026a73a6b9986977d2c78499bb5785f142c1af",
        )
        self.assertEqual(
            collect.PREREGISTRATION_SHA256,
            "1630ab4591b20a26640a45c980b28b788516434110795d5d406f0189d92a6bd2",
        )
        self.assertIn("fstream.binance.com", collect.WS_URL)
        self.assertIn("btcusdt@bookTicker", collect.WS_URL)

    def test_exact_utc_day_boundaries_and_grid_are_frozen(self):
        self.assertEqual(collect.COLLECTION_START.utcoffset(), timedelta(0))
        self.assertEqual(collect.COLLECTION_END.utcoffset(), timedelta(0))
        self.assertEqual(
            collect.COLLECTION_END - collect.COLLECTION_START,
            timedelta(days=1),
        )
        self.assertEqual(finalize.GRID_US, 250_000)
        self.assertEqual(finalize.EXPECTED_ROWS, 345_600)
        self.assertEqual(finalize.MAX_AGE_US, 2_000_000)
        self.assertEqual(
            finalize.DAY_END_US - finalize.DAY_START_US,
            86_400_000_000,
        )
        self.assertEqual(
            finalize.DAY_START_US
            + (finalize.EXPECTED_ROWS - 1) * finalize.GRID_US,
            finalize.DAY_END_US - finalize.GRID_US,
        )

    def test_quote_validity_accepts_only_clean_btc_bookticker(self):
        valid = {
            "s": "BTCUSDT",
            "b": "100.0",
            "B": "1.2",
            "a": "100.1",
            "A": "2.3",
        }
        self.assertEqual(collect._validate_payload(valid), (True, None))

        cases = (
            ({**valid, "s": "ETHUSDT"}, "WRONG_SYMBOL"),
            ({**valid, "b": "101", "a": "100"}, "INVALID_OR_CROSSED_PRICE"),
            ({**valid, "B": "-1"}, "NEGATIVE_QUANTITY"),
            ({**valid, "a": "nan"}, "NONFINITE"),
            ({"s": "BTCUSDT"}, "PARSE_FAIL"),
        )
        for payload, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(
                    collect._validate_payload(payload),
                    (False, reason),
                )

    def test_process_quote_rejects_clock_reversals_without_advancing_state(self):
        state = collect.CollectorState()
        payload = {
            "s": "BTCUSDT",
            "b": "100",
            "B": "1",
            "a": "101",
            "A": "2",
            "u": 1,
        }
        accepted = collect.process_quote_payload(
            state,
            payload,
            epoch=1,
            wall_ns=100,
            mono_ns=200,
        )
        self.assertEqual(accepted["record_type"], "quote")

        wall_reversal = collect.process_quote_payload(
            state,
            payload,
            epoch=1,
            wall_ns=99,
            mono_ns=201,
        )
        mono_reversal = collect.process_quote_payload(
            state,
            payload,
            epoch=1,
            wall_ns=101,
            mono_ns=199,
        )
        self.assertEqual(wall_reversal["reason"], "WALL_CLOCK_REVERSAL")
        self.assertEqual(mono_reversal["reason"], "MONOTONIC_CLOCK_REVERSAL")
        self.assertEqual(state.accepted_quotes, 1)
        self.assertEqual(state.rejected_quotes, 2)
        self.assertEqual(state.last_wall_ns, 100)
        self.assertEqual(state.last_mono_ns, 200)

    def test_process_quote_records_wrong_symbol_price_and_quantity_rejections(self):
        base = {"s": "BTCUSDT", "b": "100", "B": "1", "a": "101", "A": "2"}
        cases = (
            ({**base, "s": "ETHUSDT"}, "WRONG_SYMBOL"),
            ({**base, "a": "99"}, "INVALID_OR_CROSSED_PRICE"),
            ({**base, "A": "-2"}, "NEGATIVE_QUANTITY"),
        )
        for index, (payload, reason) in enumerate(cases):
            with self.subTest(reason=reason):
                state = collect.CollectorState()
                record = collect.process_quote_payload(
                    state,
                    payload,
                    epoch=1,
                    wall_ns=100 + index,
                    mono_ns=200 + index,
                )
                self.assertEqual(record["record_type"], "rejected")
                self.assertEqual(record["reason"], reason)
                self.assertEqual(state.accepted_quotes, 0)
                self.assertEqual(state.rejected_quotes, 1)

    def test_raw_writer_exclusively_refuses_even_empty_existing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "raw.jsonl.gz"
            path.touch()
            with self.assertRaises(FileExistsError):
                collect.RawWriter(path)
            self.assertEqual(path.stat().st_size, 0)

    def test_collect_refuses_late_arming_before_raw_or_network_open(self):
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            collect.time,
            "time_ns",
            return_value=finalize.DAY_START_US * 1000,
        ), mock.patch.object(collect.websockets, "connect") as connect:
            with self.assertRaisesRegex(RuntimeError, "not armed before"):
                asyncio.run(
                    collect.collect(
                        Path(temp_dir),
                        collect.COLLECTION_START,
                        collect.COLLECTION_END,
                        frozen_commit=FROZEN_COMMIT,
                    )
                )
            self.assertFalse((Path(temp_dir) / collect.RAW_REL).exists())
            connect.assert_not_called()

    def test_main_refuses_at_midnight_and_does_not_start_collection(self):
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            collect,
            "_utc_now",
            return_value=collect.COLLECTION_START,
        ), mock.patch.object(collect.asyncio, "run") as run:
            with self.assertRaisesRegex(SystemExit, "missed EXP024"):
                collect.main(
                    [
                        "--output-root",
                        temp_dir,
                        "--frozen-commit",
                        FROZEN_COMMIT,
                    ]
                )
            run.assert_not_called()
            self.assertFalse((Path(temp_dir) / collect.RAW_REL).exists())

    def test_main_has_no_backfill_or_date_switch_interface(self):
        with mock.patch.object(
            collect,
            "_utc_now",
            return_value=collect.COLLECTION_START - timedelta(minutes=1),
        ), mock.patch.object(collect.asyncio, "run") as run:
            with self.assertRaises(SystemExit):
                collect.main(
                    [
                        "--output-root",
                        "synthetic",
                        "--frozen-commit",
                        FROZEN_COMMIT,
                        "--backfill",
                        "2026-08-30",
                    ]
                )
        run.assert_not_called()


class Exp024P0StreamingFinalizerTests(unittest.TestCase):
    def test_no_future_quote_usage_and_exact_boundary_semantics(self):
        records = _complete_records(
            _quote(100_000, 4, 1),
            _quote(250_000, 5, 2, bid=101.0, ask=101.2),
            _quote(375_000, 6, 3, bid=102.0, ask=102.2),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "synthetic.jsonl.gz"
            grid = root / "grid.csv"
            _write_fixture(raw, records)
            with mock.patch.object(finalize, "EXPECTED_ROWS", 4):
                raw_diagnostics, grid_diagnostics = finalize.stream_raw_to_grid(
                    raw, grid
                )
            rows = _read_grid(grid)

        self.assertEqual(rows[0]["book_valid"], "0")
        self.assertEqual(rows[1]["source_update_id"], "2")
        self.assertEqual(rows[1]["quote_age_ms"], "0.0")
        self.assertEqual(rows[2]["source_update_id"], "3")
        self.assertEqual(rows[2]["quote_age_ms"], "125.0")
        self.assertEqual(grid_diagnostics["future_quote_violations"], 0)
        self.assertEqual(raw_diagnostics["accepted_quotes"], 3)

    def test_stale_quote_over_two_seconds_is_invalid(self):
        records = _complete_records(_quote(0, 4, 1))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "synthetic.jsonl.gz"
            grid = root / "grid.csv"
            _write_fixture(raw, records)
            with mock.patch.object(finalize, "EXPECTED_ROWS", 10):
                _, diagnostics = finalize.stream_raw_to_grid(raw, grid)
            rows = _read_grid(grid)

        self.assertEqual(rows[8]["book_valid"], "1")
        self.assertEqual(rows[8]["quote_age_ms"], "2000.0")
        self.assertEqual(rows[9]["book_valid"], "0")
        self.assertEqual(rows[9]["quote_age_ms"], "2250.0")
        self.assertEqual(diagnostics["stale_or_unavailable_rows"], 1)

    def test_disconnect_and_new_epoch_require_fresh_quote(self):
        records = _complete_records(
            _quote(0, 4, 1),
            _transport(300_000, 5, "transport_error", 1),
            _transport(400_000, 6, "connection_open_attempt", 2),
            _transport(450_000, 7, "connection_opened", 2),
            _quote(600_000, 8, 2, epoch=1),
            _quote(800_000, 9, 3, epoch=2, bid=102.0, ask=102.2),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "synthetic.jsonl.gz"
            grid = root / "grid.csv"
            _write_fixture(raw, records)
            with mock.patch.object(finalize, "EXPECTED_ROWS", 5):
                _, diagnostics = finalize.stream_raw_to_grid(raw, grid)
            rows = _read_grid(grid)

        self.assertEqual(rows[0]["book_valid"], "1")
        self.assertEqual(rows[1]["book_valid"], "1")
        self.assertEqual(rows[2]["book_valid"], "0")
        self.assertEqual(rows[3]["book_valid"], "0")
        self.assertEqual(rows[4]["source_update_id"], "3")
        self.assertGreaterEqual(diagnostics["reconnect_invalid_rows"], 2)

    def test_streaming_finalization_is_byte_deterministic(self):
        records = _complete_records(
            _quote(0, 4, 1),
            _quote(625_000, 5, 2, bid=101.0, ask=101.2),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "synthetic.jsonl.gz"
            first = root / "first.csv"
            second = root / "second.csv"
            _write_fixture(raw, records)
            with mock.patch.object(finalize, "EXPECTED_ROWS", 8):
                first_raw, first_grid = finalize.stream_raw_to_grid(raw, first)
                second_raw, second_grid = finalize.stream_raw_to_grid(raw, second)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(finalize.sha256_file(first), finalize.sha256_file(second))
            self.assertEqual(first_raw, second_raw)
            self.assertEqual(first_grid, second_grid)

    def test_raw_diagnostics_report_rejections_transport_and_reconnects(self):
        rejected = {
            "record_type": "rejected",
            "reason": "WRONG_SYMBOL",
            "connection_epoch": 1,
            "receive_wall_ns": finalize.DAY_START_US * 1000,
            "receive_monotonic_ns": 10,
        }
        records = _complete_records(
            _quote(0, 4, 1),
            _transport(100_000, 5, "transport_error", 1),
            _transport(200_000, 6, "connection_open_attempt", 2),
            _transport(250_000, 7, "connection_opened", 2),
            rejected,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "synthetic.jsonl.gz"
            grid = root / "grid.csv"
            _write_fixture(raw, records)
            with mock.patch.object(finalize, "EXPECTED_ROWS", 4):
                diagnostics, _ = finalize.stream_raw_to_grid(raw, grid)

        self.assertEqual(diagnostics["rejected_records"], 1)
        self.assertEqual(diagnostics["rejected_by_reason"], {"WRONG_SYMBOL": 1})
        self.assertEqual(diagnostics["connection_open_attempts"], 2)
        self.assertEqual(diagnostics["connections_opened"], 2)
        self.assertEqual(diagnostics["transport_errors"], 1)
        self.assertEqual(diagnostics["connection_epochs"], 2)
        self.assertEqual(diagnostics["collection_end_records"], 1)


class Exp024P0IntegrityAndSafetyTests(unittest.TestCase):
    def _run_fixture(self, records: list[dict]) -> tuple[dict, bytes, bytes]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        raw = root / "synthetic.jsonl.gz"
        grid = root / "grid.csv"
        audit = root / "audit.json"
        _write_fixture(raw, records)
        with mock.patch.object(finalize, "EXPECTED_ROWS", 4), mock.patch.object(
            finalize,
            "_utc_now",
            return_value=collect.COLLECTION_END + timedelta(seconds=1),
        ):
            payload = finalize.run(raw, grid, audit)
        return payload, raw.read_bytes(), audit.read_bytes()

    def test_complete_synthetic_day_passes_and_records_hashes_bytes_and_guards(self):
        payload, raw_bytes, audit_bytes = self._run_fixture(
            _complete_records(_quote(0, 4, 1))
        )
        self.assertEqual(payload["status"], finalize.STATUS_PASS)
        self.assertEqual(payload["raw_bytes"], len(raw_bytes))
        self.assertGreater(payload["grid_bytes"], 0)
        self.assertEqual(len(payload["raw_sha256"]), 64)
        self.assertEqual(len(payload["grid_sha256"]), 64)
        self.assertEqual(json.loads(audit_bytes)["status"], finalize.STATUS_PASS)
        self.assertTrue(
            all(
                type(value) is bool
                for value in payload["integrity_gates"].values()
            )
        )
        for name, value in collect.no_analysis_guards().items():
            self.assertIs(payload[name], value)
            self.assertIs(payload["integrity_gates"][name], value)
        self.assertFalse(payload["predictive_metrics_calculated"])

    def test_missing_or_late_arming_fails_full_day_integrity(self):
        without_arm = _complete_records(_quote(0, 4, 1))[1:]
        missing, _, _ = self._run_fixture(without_arm)
        self.assertEqual(missing["status"], finalize.STATUS_FAIL)
        self.assertFalse(
            missing["integrity_gates"]["collector_armed_before_utc_midnight"]
        )

        late_records = _complete_records(_quote(0, 4, 1))
        late_records[0] = _armed(offset_us=1)
        late, _, _ = self._run_fixture(late_records)
        self.assertEqual(late["status"], finalize.STATUS_FAIL)
        self.assertFalse(
            late["integrity_gates"]["collector_armed_before_utc_midnight"]
        )

    def test_missing_collection_end_fails_full_day_integrity(self):
        records = _complete_records(_quote(0, 4, 1))[:-1]
        payload, _, _ = self._run_fixture(records)
        self.assertEqual(payload["status"], finalize.STATUS_FAIL)
        self.assertFalse(
            payload["integrity_gates"]["collection_end_recorded_after_day"]
        )

    def test_wrong_metadata_and_out_of_day_quote_fail_integrity(self):
        wrong_metadata = _complete_records(_quote(0, 4, 1))
        wrong_metadata[0] = _armed(symbol="ETHUSDT")
        metadata_payload, _, _ = self._run_fixture(wrong_metadata)
        self.assertEqual(metadata_payload["status"], finalize.STATUS_FAIL)
        self.assertFalse(
            metadata_payload["integrity_gates"]["collector_metadata_exact"]
        )

        out_of_day = _complete_records(_quote(-1, 4, 1))
        day_payload, _, _ = self._run_fixture(out_of_day)
        self.assertEqual(day_payload["status"], finalize.STATUS_FAIL)
        self.assertFalse(
            day_payload["integrity_gates"]
            ["no_quote_outside_collection_day_accepted"]
        )

    def test_injected_invalid_accepted_quotes_and_clock_reversal_fail_gates(self):
        records = _complete_records(
            _quote(100, 10, 1),
            _quote(50, 11, 2, ask=99.0),
            _quote(200, 9, 3, bid_qty=-1.0),
            _quote(300, 12, 4, symbol="ETHUSDT"),
        )
        payload, _, _ = self._run_fixture(records)
        gates = payload["integrity_gates"]
        self.assertEqual(payload["status"], finalize.STATUS_FAIL)
        self.assertFalse(gates["no_accepted_wall_clock_reversal"])
        self.assertFalse(gates["no_accepted_monotonic_clock_reversal"])
        self.assertFalse(gates["no_invalid_crossed_price_accepted"])
        self.assertFalse(gates["no_negative_quantity_accepted"])
        self.assertFalse(gates["no_other_symbol_accepted"])

    def test_existing_grid_audit_or_part_is_never_overwritten(self):
        records = _complete_records(_quote(0, 4, 1))
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "synthetic.jsonl.gz"
            grid = root / "grid.csv"
            audit = root / "audit.json"
            _write_fixture(raw, records)
            grid.write_text("immutable", encoding="utf-8")
            with mock.patch.object(
                finalize,
                "_utc_now",
                return_value=collect.COLLECTION_END + timedelta(seconds=1),
            ):
                with self.assertRaises(FileExistsError):
                    finalize.run(raw, grid, audit)
            self.assertEqual(grid.read_text(encoding="utf-8"), "immutable")

            grid.unlink()
            audit.write_text("immutable", encoding="utf-8")
            with mock.patch.object(
                finalize,
                "_utc_now",
                return_value=collect.COLLECTION_END + timedelta(seconds=1),
            ):
                with self.assertRaises(FileExistsError):
                    finalize.run(raw, grid, audit)
            self.assertEqual(audit.read_text(encoding="utf-8"), "immutable")

    def test_modules_expose_no_scoring_old_august_or_backfill_functionality(self):
        collector_source = inspect.getsource(collect)
        finalizer_source = inspect.getsource(finalize)
        collector_main = inspect.getsource(collect.main)
        finalizer_main = inspect.getsource(finalize.main)

        for source in (collector_source, finalizer_source):
            self.assertNotIn("2026-08-28", source)
            self.assertNotIn("roc_auc_score", source)
            self.assertNotIn("average_precision_score", source)
            self.assertNotIn("LogisticRegression", source)
            self.assertNotIn("executable_fixed_horizon", source)
        self.assertNotIn("--day", collector_main)
        self.assertNotIn("--backfill", collector_main)
        self.assertNotIn("--target", finalizer_main)
        self.assertNotIn("--model", finalizer_main)
        self.assertNotIn("--auc", finalizer_main)
        self.assertNotIn("--pnl", finalizer_main)


if __name__ == "__main__":
    unittest.main()

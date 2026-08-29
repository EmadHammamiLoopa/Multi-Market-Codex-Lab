import csv
import gzip
import io
import inspect
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import multimarket.codex_exp022_finalize as finalize

from multimarket.codex_exp022_collect import (
    COLLECTION_DAY,
    EXPERIMENT_ID,
    RAW_REL,
    SYMBOL,
    _validate_payload,
    main as collect_main,
)
from multimarket.codex_exp022_finalize import (
    DAY_END_US,
    DAY_START_US,
    EXPECTED_ROWS,
    GRID_US,
    MAX_AGE_US,
    _apply_timeline_event,
    _valid_quote_record,
    run,
    stream_raw_to_grid,
)


GRID_COLUMNS = [
    "local_timestamp_us",
    "best_bid",
    "best_ask",
    "mid",
    "book_valid",
    "quote_age_ms",
    "connection_epoch",
    "source_update_id",
    "exchange_event_time_ms",
    "exchange_transaction_time_ms",
]


def _transport(
    offset_us: int,
    monotonic_ns: int,
    event: str,
    epoch: int,
) -> dict:
    return {
        "record_type": "transport",
        "event": event,
        "connection_epoch": epoch,
        "receive_wall_ns": (DAY_START_US + offset_us) * 1000,
        "receive_monotonic_ns": monotonic_ns,
    }


def _quote(
    offset_us: int,
    monotonic_ns: int,
    update_id: int,
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
        "receive_wall_ns": (DAY_START_US + offset_us) * 1000,
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


def _write_fixture(path: Path, records: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")


def _materialized_reference_csv(
    records: list[dict],
    expected_rows: int,
) -> str:
    timeline = []
    for record in records:
        if record.get("record_type") == "transport":
            if (
                "receive_wall_ns" in record
                and "receive_monotonic_ns" in record
            ):
                timeline.append(record)
        elif record.get("record_type") == "quote":
            timeline.append(record)

    timeline.sort(
        key=lambda r: (
            int(r["receive_wall_ns"]),
            int(r["receive_monotonic_ns"]),
            0 if r.get("record_type") == "transport" else 1,
        )
    )

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(GRID_COLUMNS)
    event_idx = 0
    latest = None
    active_epoch = None

    for i in range(expected_rows):
        ts_us = DAY_START_US + i * GRID_US
        while event_idx < len(timeline):
            event = timeline[event_idx]
            if int(event["receive_wall_ns"]) // 1000 > ts_us:
                break
            latest, active_epoch = _apply_timeline_event(
                latest,
                active_epoch,
                event,
            )
            event_idx += 1

        valid = False
        bid = ask = mid = float("nan")
        age_ms = float("nan")
        epoch = ""
        update_id = ""
        event_ms = ""
        trans_ms = ""

        if latest is not None:
            quote_us = int(latest["receive_wall_ns"]) // 1000
            age_us = ts_us - quote_us
            age_ms = age_us / 1000.0
            if age_us <= MAX_AGE_US and _valid_quote_record(latest):
                valid = True
                bid = float(latest["best_bid"])
                ask = float(latest["best_ask"])
                mid = (bid + ask) / 2.0
                epoch = int(latest["connection_epoch"])
                update_id = latest.get("update_id", "")
                event_ms = latest.get("exchange_event_time_ms", "")
                trans_ms = latest.get("exchange_transaction_time_ms", "")

        writer.writerow(
            [
                ts_us,
                bid,
                ask,
                mid,
                1 if valid else 0,
                age_ms,
                epoch,
                update_id,
                event_ms,
                trans_ms,
            ]
        )

    return output.getvalue()


class Exp022P0Tests(unittest.TestCase):
    def test_identity_scope_and_day(self):
        self.assertEqual(EXPERIMENT_ID, "CODEX-EXP-022-P0")
        self.assertEqual(SYMBOL, "BTCUSDT")
        self.assertEqual(COLLECTION_DAY, date(2026, 8, 28))
        self.assertEqual(
            str(RAW_REL),
            "bookticker/BTCUSDT/2026-08-28.jsonl.gz",
        )

    def test_grid_constants_exact(self):
        self.assertEqual(GRID_US, 250_000)
        self.assertEqual(EXPECTED_ROWS, 345_600)
        self.assertEqual(MAX_AGE_US, 2_000_000)
        self.assertEqual(DAY_END_US - DAY_START_US, 86_400_000_000)
        self.assertEqual(
            DAY_START_US + (EXPECTED_ROWS - 1) * GRID_US,
            DAY_END_US - GRID_US,
        )

    def test_valid_payload_accepts_clean_btc_bookticker(self):
        ok, reason = _validate_payload(
            {
                "s": "BTCUSDT",
                "b": "100.0",
                "B": "1.2",
                "a": "100.1",
                "A": "2.3",
            }
        )
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_payload_rejects_wrong_symbol(self):
        ok, reason = _validate_payload(
            {
                "s": "ETHUSDT",
                "b": "100.0",
                "B": "1",
                "a": "100.1",
                "A": "1",
            }
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "WRONG_SYMBOL")

    def test_payload_rejects_crossed_quote(self):
        ok, reason = _validate_payload(
            {
                "s": "BTCUSDT",
                "b": "100.1",
                "B": "1",
                "a": "100.0",
                "A": "1",
            }
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "INVALID_OR_CROSSED_PRICE")

    def test_payload_rejects_negative_quantity(self):
        ok, reason = _validate_payload(
            {
                "s": "BTCUSDT",
                "b": "100",
                "B": "-1",
                "a": "101",
                "A": "1",
            }
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "NEGATIVE_QUANTITY")

    def test_finalize_quote_validator(self):
        q = {
            "record_type": "quote",
            "symbol": "BTCUSDT",
            "best_bid": 100.0,
            "best_ask": 100.1,
            "best_bid_qty": 1.0,
            "best_ask_qty": 2.0,
        }
        self.assertTrue(_valid_quote_record(q))
        q["best_ask"] = 99.0
        self.assertFalse(_valid_quote_record(q))

    def test_reconnect_invalidates_old_quote(self):
        latest = {
            "record_type": "quote",
            "connection_epoch": 1,
        }
        active = 1

        latest, active = _apply_timeline_event(
            latest,
            active,
            {
                "record_type": "transport",
                "event": "transport_error",
                "connection_epoch": 1,
            },
        )

        self.assertIsNone(latest)
        self.assertIsNone(active)

    def test_new_epoch_requires_new_quote(self):
        latest = None
        active = None

        latest, active = _apply_timeline_event(
            latest,
            active,
            {
                "record_type": "transport",
                "event": "connection_opened",
                "connection_epoch": 2,
            },
        )
        self.assertIsNone(latest)
        self.assertEqual(active, 2)

        old_quote = {
            "record_type": "quote",
            "connection_epoch": 1,
        }
        latest, active = _apply_timeline_event(
            latest,
            active,
            old_quote,
        )
        self.assertIsNone(latest)

        new_quote = {
            "record_type": "quote",
            "connection_epoch": 2,
        }
        latest, active = _apply_timeline_event(
            latest,
            active,
            new_quote,
        )
        self.assertIs(latest, new_quote)

    def test_streaming_grid_matches_materialized_semantics(self):
        records = [
            _transport(-200_000, 1, "connection_open_attempt", 1),
            _transport(-100_000, 2, "connection_opened", 1),
            _quote(100_000, 3, 1),
            _quote(500_000, 4, 2, bid=101.0, ask=101.2),
            _quote(625_000, 5, 3, bid=102.0, ask=102.2),
            _quote(800_000, 6, 4, bid=103.0, ask=103.2),
            _quote(900_000, 7, 5, bid=104.0, ask=104.2),
            _transport(1_100_000, 8, "connection_closed", 1),
            _quote(1_300_000, 9, 6, epoch=1, bid=105.0, ask=105.2),
            _transport(1_400_000, 10, "connection_opened", 2),
            _quote(1_600_000, 11, 7, epoch=2, bid=106.0, ask=106.2),
            _transport(1_900_000, 12, "transport_error", 2),
            _transport(2_100_000, 13, "connection_opened", 3),
            _quote(2_350_000, 14, 8, epoch=3, bid=107.0, ask=107.2),
            _transport(4_600_000, 15, "collection_end", 3),
            {
                "record_type": "rejected",
                "reason": "INVALID_OR_CROSSED_PRICE",
                "receive_wall_ns": (DAY_START_US + 4_700_000) * 1000,
                "receive_monotonic_ns": 16,
            },
            _quote(5_000_000, 17, 9, epoch=3, bid=108.0, ask=107.0),
            _quote(
                5_100_000,
                18,
                10,
                epoch=3,
                bid=108.0,
                ask=108.2,
                bid_qty=-1.0,
            ),
            _quote(
                5_200_000,
                19,
                11,
                epoch=3,
                symbol="ETHUSDT",
                bid=108.0,
                ask=108.2,
            ),
            {"record_type": "transport", "event": "diagnostic_only"},
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "synthetic.jsonl.gz"
            grid = root / "grid.csv"
            _write_fixture(raw, records)

            with mock.patch.object(finalize, "EXPECTED_ROWS", 20):
                raw_diag, grid_diag = stream_raw_to_grid(raw, grid)

            self.assertEqual(
                grid.read_text(encoding="utf-8").splitlines(),
                _materialized_reference_csv(records, 20).splitlines(),
            )
            with grid.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(list(rows[0]), GRID_COLUMNS)
        self.assertEqual(rows[0]["book_valid"], "0")
        self.assertEqual(rows[1]["source_update_id"], "1")
        self.assertEqual(rows[1]["quote_age_ms"], "150.0")
        self.assertEqual(rows[2]["source_update_id"], "2")
        self.assertEqual(rows[2]["quote_age_ms"], "0.0")
        self.assertEqual(rows[3]["source_update_id"], "3")
        self.assertEqual(rows[4]["source_update_id"], "5")
        self.assertEqual(rows[5]["book_valid"], "0")
        self.assertEqual(rows[6]["book_valid"], "0")
        self.assertEqual(rows[7]["source_update_id"], "7")
        self.assertEqual(rows[8]["book_valid"], "0")
        self.assertEqual(rows[9]["book_valid"], "0")
        self.assertEqual(rows[10]["source_update_id"], "8")
        self.assertEqual(rows[17]["book_valid"], "1")
        self.assertEqual(rows[18]["book_valid"], "0")
        self.assertEqual(rows[18]["quote_age_ms"], "2150.0")
        self.assertEqual(rows[19]["book_valid"], "0")

        self.assertEqual(
            raw_diag,
            {
                "rejected_records": 1,
                "transport_records": 8,
                "accepted_quotes": 11,
                "accepted_wall_clock_reversals": 0,
                "accepted_monotonic_clock_reversals": 0,
                "wrong_symbol_accepted": 1,
                "invalid_price_accepted": 1,
                "negative_quantity_accepted": 1,
            },
        )
        self.assertEqual(grid_diag["future_quote_violations"], 0)
        self.assertEqual(grid_diag["stale_or_unavailable_rows"], 1)
        self.assertEqual(grid_diag["reconnect_invalid_rows"], 3)

    def test_out_of_order_input_retains_materialized_sort_semantics(self):
        records = [
            _quote(250_000, 10, 1),
            _transport(250_000, 10, "connection_opened", 1),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "synthetic.jsonl.gz"
            grid = root / "grid.csv"
            _write_fixture(raw, records)

            with mock.patch.object(finalize, "EXPECTED_ROWS", 3):
                raw_diag, grid_diag = stream_raw_to_grid(raw, grid)

            self.assertEqual(
                grid.read_text(encoding="utf-8").splitlines(),
                _materialized_reference_csv(records, 3).splitlines(),
            )
            with grid.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(rows[1]["book_valid"], "1")
        self.assertEqual(rows[1]["source_update_id"], "1")
        self.assertEqual(grid_diag["future_quote_violations"], 0)
        self.assertEqual(raw_diag["accepted_quotes"], 1)

    def test_run_preserves_gate_names_schema_and_one_shot_outputs(self):
        records = [
            _transport(-100_000, 1, "connection_opened", 1),
            _quote(-50_000, 2, 1),
        ]
        expected_gate_names = {
            "raw_file_nonempty",
            "grid_rows_exact_345600",
            "grid_step_exact_250000us",
            "first_timestamp_exact",
            "last_timestamp_exact",
            "valid_coverage_at_least_0_99",
            "no_invalid_crossed_price_accepted",
            "no_negative_quantity_accepted",
            "no_accepted_wall_clock_reversal",
            "no_accepted_monotonic_clock_reversal",
            "no_other_symbol_accepted",
            "no_future_quote_used",
            "raw_sha_recorded",
            "grid_sha_recorded",
            "older_august_holdout_opened",
            "historical_aug1_feature_reparsed",
            "target_scored",
            "model_fit",
            "auc_scored",
            "direction_scored",
            "pnl_scored",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "synthetic.jsonl.gz"
            grid = root / "grid.csv"
            audit = root / "audit.json"
            _write_fixture(raw, records)

            with mock.patch.object(finalize, "EXPECTED_ROWS", 4):
                payload = run(raw, grid, audit)
                audit_before = audit.read_bytes()
                with self.assertRaisesRegex(
                    RuntimeError,
                    "audit output already exists",
                ):
                    run(raw, grid, audit)

            self.assertEqual(audit.read_bytes(), audit_before)
            with grid.open(newline="", encoding="utf-8") as f:
                header = next(csv.reader(f))

        self.assertEqual(payload["status"], finalize.STATUS_PASS)
        self.assertEqual(set(payload["integrity_gates"]), expected_gate_names)
        self.assertEqual(header, GRID_COLUMNS)
        self.assertFalse(payload["target_scored"])
        self.assertFalse(payload["model_fit"])
        self.assertFalse(payload["auc_scored"])
        self.assertFalse(payload["direction_scored"])
        self.assertFalse(payload["pnl_scored"])

    def test_collector_has_no_scoring_interface(self):
        source = inspect.getsource(collect_main)
        self.assertNotIn("--aug-feature", source)
        self.assertNotIn("--target", source)
        self.assertNotIn("--model", source)
        self.assertNotIn("--auc", source)
        self.assertNotIn("--pnl", source.lower())


if __name__ == "__main__":
    unittest.main()

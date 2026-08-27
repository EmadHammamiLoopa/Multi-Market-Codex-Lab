import inspect
import unittest
from datetime import date

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
)


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

    def test_collector_has_no_scoring_interface(self):
        source = inspect.getsource(collect_main)
        self.assertNotIn("--aug-feature", source)
        self.assertNotIn("--target", source)
        self.assertNotIn("--model", source)
        self.assertNotIn("--auc", source)
        self.assertNotIn("--pnl", source.lower())


if __name__ == "__main__":
    unittest.main()

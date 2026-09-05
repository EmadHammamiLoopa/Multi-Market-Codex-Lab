from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from multimarket import dev045_d6r7_canonical_ingestion_contract as c


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: str) -> str:
    digest = hashlib.sha256()

    with (ROOT / path).open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


class TestD6R7CanonicalIngestionContract(unittest.TestCase):

    def test_exact_parent(self):
        self.assertEqual(
            c.PARENT_HEAD,
            "56c46cd2f60e300a3a406d5ff81d9db068d2ecee",
        )

    def test_frozen_d6r6b_implementation_identity(self):
        self.assertEqual(
            _sha256(c.D6R6B_IMPLEMENTATION_PATH),
            c.D6R6B_IMPLEMENTATION_SHA256,
        )

    def test_both_d6r6b_ci_gates_are_frozen_pass(self):
        self.assertEqual(
            c.D6R6B_DEFAULT_CI_REQUIRED,
            "PASS",
        )

        self.assertEqual(
            c.D6R6B_PATCHED_HFT_CI_REQUIRED,
            "PASS",
        )

        self.assertEqual(
            c.D6R6B_DEFAULT_CI_RUN,
            33_935_467_049,
        )

        self.assertEqual(
            c.D6R6B_PATCHED_HFT_CI_RUN,
            33_935_467_064,
        )

    def test_resource_gate_is_derived_from_real_full_jan_validation(self):
        self.assertEqual(
            c.D6R5C_PEAK_RSS_BYTES,
            4_221_472_768,
        )

        self.assertEqual(
            c.MEMORY_SAFETY_MULTIPLIER,
            2,
        )

        self.assertEqual(
            c.REQUIRED_MEMAVAILABLE_BYTES,
            8_442_945_536,
        )

        self.assertIs(
            c.SWAP_COUNTS_AS_AVAILABLE_MEMORY,
            False,
        )

    def test_exact_jan_identity(self):
        self.assertEqual(c.DAY, "2026-01-01")
        self.assertEqual(c.SYMBOL, "BTCUSDT")
        self.assertEqual(
            c.CANONICAL_NPY_ROWS,
            64_314_723,
        )
        self.assertEqual(
            c.CANONICAL_NPY_BYTES,
            4_116_142_528,
        )
        self.assertEqual(
            c.CANONICAL_NPY_DEVICE_ID,
            2096,
        )

    def test_ingestion_is_feed_only(self):
        self.assertEqual(
            c.INGESTION_MODE,
            "FEED_ONLY_NO_STRATEGY",
        )

        self.assertIs(
            c.WAIT_NEXT_FEED_INCLUDE_ORDER_RESPONSE,
            False,
        )

        self.assertEqual(
            c.EXPECTED_TERMINAL_RC,
            1,
        )

        self.assertEqual(
            c.MARKET_FEED_RC,
            2,
        )

        self.assertIs(
            c.WAKEUP_COUNT_MUST_EQUAL_SOURCE_ROWS,
            False,
        )

        self.assertIs(
            c.TERMINAL_FEED_MAY_BE_APPLIED_BEFORE_END_OF_DATA_RC,
            True,
        )

    def test_one_shot_boundary(self):
        self.assertEqual(
            c.CANONICAL_INGESTION_ATTEMPTS,
            1,
        )

        self.assertEqual(
            c.CANONICAL_ATTEMPT_STARTS_AT,
            "_build_lifetime_safe_binding(source)",
        )

        self.assertIs(
            c.FIRST_CANONICAL_INGESTION_RESULT_FROZEN,
            True,
        )

        self.assertIs(
            c.CANONICAL_RERUN_ALLOWED,
            False,
        )

    def test_lifetime_order_remains_frozen(self):
        self.assertIs(
            c.MEMMAP_OWNER_MUST_OUTLIVE_BACKTEST,
            True,
        )

        self.assertIs(
            c.BACKTEST_CLOSE_BEFORE_MEMMAP_CLOSE,
            True,
        )

        self.assertIs(c.PARALLEL_LOAD, False)
        self.assertEqual(
            c.FEED_LATENCY_OFFSET_NS,
            0,
        )

    def test_d6r7a_does_not_open_or_execute(self):
        self.assertIs(
            c.D6R7A_OPENS_CANONICAL_JAN,
            False,
        )

        self.assertIs(
            c.D6R7A_RUNS_HFTBACKTEST,
            False,
        )

    def test_economic_and_future_surfaces_stay_closed(self):
        values = (
            c.D6R7B_POLICY_EXECUTION_AUTHORIZED,
            c.D6R7B_ORDER_SUBMISSION_AUTHORIZED,
            c.D6R7B_ORDER_CANCEL_AUTHORIZED,
            c.D6R7B_PNL_AUTHORIZED,
            c.RAW_CSV_OPEN_AUTHORIZED,
            c.CONVERTER_RERUN_AUTHORIZED,
            c.CANONICAL_NPY_WRITE_AUTHORIZED,
            c.OTHER_DAY_OPEN_AUTHORIZED,
            c.FEB_TO_JUL_OPEN_AUTHORIZED,
            c.AUG_OPEN_AUTHORIZED,
            c.SEP_PLUS_OPEN_AUTHORIZED,
            c.NON_BTC_OPEN_AUTHORIZED,
            c.HISTORICAL_POLICY_REPLAY_AUTHORIZED,
            c.HISTORICAL_PNL_AUTHORIZED,
            c.ECONOMIC_ARENA_AUTHORIZED,
            c.CANONICAL_PNL_WRITE_AUTHORIZED,
            c.NETWORK_ACQUISITION_AUTHORIZED,
            c.RAILWAY_AUTHORIZED,
            c.LIVE_TRADING_AUTHORIZED,
        )

        self.assertTrue(
            all(value is False for value in values)
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from multimarket import dev045_d6r8_resource_scaling_contract as c


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


class TestD6R8ResourceScalingContract(unittest.TestCase):
    def test_exact_parent_and_frozen_evidence(self):
        self.assertEqual(
            c.PARENT_HEAD,
            "c301e691ae89675f6e244a7b987d3cb0b4488381",
        )
        self.assertEqual(
            _sha256(c.D6R7B_EVIDENCE_PATH),
            c.D6R7B_EVIDENCE_SHA256,
        )
        self.assertEqual(
            _sha256(c.D6R4B_EVIDENCE_PATH),
            c.D6R4B_EVIDENCE_SHA256,
        )
        self.assertEqual(c.D6R7B_STATUS, "PASS")
        self.assertEqual(c.D6R4B_STATUS, "PASS")

    def test_jan_real_conversion_was_near_memory_ceiling(self):
        self.assertEqual(
            c.JAN_FULL_CONVERSION_PEAK_RSS_BYTES,
            9_946_800_128,
        )
        self.assertEqual(
            c.JAN_FULL_CONVERSION_PRECHECK_MEMAVAILABLE_BYTES,
            10_097_618_944,
        )
        self.assertGreater(
            c.JAN_FULL_CONVERSION_MEM_UTILIZATION,
            0.98,
        )
        self.assertLess(
            c.JAN_FULL_CONVERSION_MEM_UTILIZATION,
            1.0,
        )

    def test_d5b_reference_counts_are_exact_and_discrepancy_preserved(self):
        self.assertEqual(
            c.D5B_REFERENCE_RAW_ROWS,
            {
                "2026-01": 63_666_274,
                "2026-02": 172_721_707,
                "2026-03": 145_757_298,
                "2026-04": 129_067_640,
                "2026-05": 104_234_425,
                "2026-06": 165_502_465,
                "2026-07": 172_067_693,
            },
        )
        self.assertEqual(
            sum(c.D5B_REFERENCE_RAW_ROWS.values()),
            c.D5B_REFERENCE_TOTAL_RAW_ROWS,
        )
        self.assertIs(
            c.JAN_REFERENCE_COUNT_DISCREPANCY_PRESERVED,
            True,
        )
        self.assertEqual(c.JAN_REFERENCE_COUNT_DIFFERENCE, 2)

    def test_every_future_reference_count_is_materially_larger_than_jan(self):
        jan = c.D5B_JAN_REFERENCE_RAW_ROWS
        for month in c.FUTURE_MONTHS:
            self.assertGreater(
                c.D5B_REFERENCE_RAW_ROWS[month],
                jan,
            )
        self.assertGreater(c.MIN_FUTURE_TO_JAN_ROW_RATIO, 1.6)
        self.assertGreater(c.MAX_FUTURE_TO_JAN_ROW_RATIO, 2.7)

    def test_linear_projection_is_danger_signal_not_authorization_model(self):
        self.assertIs(
            c.NAIVE_LINEAR_PROJECTION_FOR_RISK_ONLY,
            True,
        )
        self.assertIs(
            c.RESOURCE_SCALING_MODEL_IS_AUTHORIZATION_MODEL,
            False,
        )
        self.assertIs(c.LINEAR_RSS_ASSUMPTION_VALIDATED, False)
        for month in c.FUTURE_MONTHS:
            self.assertGreater(
                c.NAIVE_LINEAR_RSS_RISK_PROJECTIONS_BYTES[month],
                c.JAN_FULL_CONVERSION_PRECHECK_MEMAVAILABLE_BYTES,
            )

    def test_unrelated_rss_numbers_cannot_authorize_conversion(self):
        self.assertIs(
            c.D6R7B_RSS_IS_CONVERTER_CAPACITY_PROXY,
            False,
        )
        self.assertIs(
            c.D6R5C_RSS_IS_CONVERTER_CAPACITY_PROXY,
            False,
        )
        self.assertIs(
            c.D6R2B_10MIN_RSS_IS_FULL_DAY_CAPACITY_PROXY,
            False,
        )

    def test_feb_to_jul_conversion_stays_closed(self):
        self.assertIs(
            c.CURRENT_CONVERTER_AS_IS_FEB_TO_JUL_AUTHORIZED,
            False,
        )
        self.assertIs(c.RAW_OPEN_FEB_TO_JUL_AUTHORIZED, False)
        self.assertIs(c.CONVERSION_FEB_TO_JUL_AUTHORIZED, False)
        self.assertIs(c.D6R8A_OPENS_RAW_DATA, False)
        self.assertIs(c.D6R8A_RUNS_CONVERTER, False)
        self.assertIs(c.D6R8A_OPENS_FEB_TO_JUL, False)

    def test_d6r8b_is_static_audit_only(self):
        self.assertEqual(
            c.D6R8B_AUDIT_MODE,
            "STATIC_CODE_PATH_MEMORY_SCALING_AUDIT",
        )
        self.assertIs(c.D6R8B_RAW_DATA_OPEN_AUTHORIZED, False)
        self.assertIs(c.D6R8B_CONVERTER_EXECUTION_AUTHORIZED, False)
        self.assertIn(
            "peak_rss_scaling_driver",
            c.D6R8B_MUST_IDENTIFY,
        )
        self.assertIn(
            "structurally_bounded_redesign_if_required",
            c.D6R8B_MUST_IDENTIFY,
        )

    def test_all_economic_future_and_live_surfaces_stay_closed(self):
        closed = (
            c.RAW_CSV_OPEN_AUTHORIZED,
            c.RERUN_JAN_CONVERTER_AUTHORIZED,
            c.WRITE_CANONICAL_NPY_AUTHORIZED,
            c.OTHER_DAY_OPEN_AUTHORIZED,
            c.AUG_OPEN_AUTHORIZED,
            c.SEP_PLUS_OPEN_AUTHORIZED,
            c.NON_BTC_OPEN_AUTHORIZED,
            c.POLICY_EXECUTION_AUTHORIZED,
            c.HISTORICAL_POLICY_REPLAY_AUTHORIZED,
            c.HISTORICAL_PNL_AUTHORIZED,
            c.ECONOMIC_ARENA_AUTHORIZED,
            c.CANONICAL_PNL_WRITE_AUTHORIZED,
            c.NETWORK_ACQUISITION_AUTHORIZED,
            c.RAILWAY_AUTHORIZED,
            c.LIVE_TRADING_AUTHORIZED,
        )
        self.assertTrue(all(value is False for value in closed))


if __name__ == "__main__":
    unittest.main()

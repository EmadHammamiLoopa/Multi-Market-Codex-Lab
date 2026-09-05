from __future__ import annotations

import unittest

from multimarket import dev045_personal_trading_economic_gate as c


class TestPersonalTradingEconomicGateV1(unittest.TestCase):
    def test_exact_parent_and_pre_pnl_freeze(self):
        self.assertEqual(
            c.PARENT_HEAD,
            "caffbfb8bb0a979299a497456ed50e1d3b32f3ac",
        )
        self.assertIs(c.FROZEN_BEFORE_112_REPLAY_PNL, True)
        self.assertIs(c.PERSONAL_TRADING_DECISION_GATE, True)
        self.assertIs(c.ACADEMIC_PUBLICATION_GATE, False)

    def test_primary_veto_gates_are_real_trading_failures(self):
        required = {
            "net_expectancy_positive_after_realistic_costs",
            "profit_factor_above_one",
            "execution_integrity_complete",
            "no_future_leakage",
            "realistic_fees_slippage_latency_queue_fills",
            "drawdown_within_frozen_personal_risk_limit",
            "inventory_and_terminal_state_safe",
        }
        self.assertEqual(set(c.PRIMARY_VETO_GATES), required)
        self.assertIs(c.REALISTIC_BASE_CASE_MUST_PASS, True)
        self.assertIs(c.PRIMARY_GATE_FAILURE_IS_NEAR_PASS, False)

    def test_secondary_scientific_gates_are_not_single_vetoes(self):
        self.assertIs(c.FWER_P_LE_005_IS_AUTOMATIC_TRADING_VETO, False)
        self.assertIs(
            c.FOUR_OF_SEVEN_POSITIVE_DAYS_IS_AUTOMATIC_TRADING_VETO,
            False,
        )
        self.assertIs(c.CONCENTRATION_LE_050_IS_AUTOMATIC_TRADING_VETO, False)
        self.assertIs(
            c.EXTREME_STRESS_NET_POSITIVE_IS_AUTOMATIC_TRADING_VETO,
            False,
        )
        self.assertIs(c.SECONDARY_ONLY_FAILURE_MAY_BE_PROMISING, True)

    def test_stress_semantics_are_realistic(self):
        self.assertIs(c.ADVERSE_CASE_PROFIT_MAY_DEGRADE, True)
        self.assertIs(c.ADVERSE_CASE_MUST_NOT_UNACCEPTABLY_COLLAPSE, True)
        self.assertIs(c.EXTREME_STRESS_PROFITABILITY_REQUIRED, False)
        self.assertIs(c.EXTREME_STRESS_REQUIRES_BOUNDED_LOSS, True)
        self.assertIs(c.EXTREME_STRESS_REQUIRES_RISK_CONTROLS, True)

    def test_confidence_controls_capital_sizing(self):
        self.assertEqual(
            c.STATISTICAL_EVIDENCE_ROLE,
            "CONFIDENCE_AND_CAPITAL_SIZING",
        )
        self.assertEqual(
            c.ROBUSTNESS_EVIDENCE_ROLE,
            "CONFIDENCE_AND_CAPITAL_SIZING",
        )
        self.assertEqual(
            c.DECISION_DIMENSIONS,
            ("profitability", "robustness", "confidence"),
        )

    def test_prior_results_keep_their_proven_roles(self):
        self.assertIs(c.REUSE_ALL_VALID_PRIOR_SUCCESSES_IN_PROVEN_ROLE, True)
        self.assertIs(c.PRESERVE_ALL_PRIOR_FAILURES_AS_LESSONS, True)
        self.assertIs(c.NO_BLIND_ROLE_TRANSFER, True)
        self.assertIs(c.HISTORICAL_PIPELINE_SUCCESS_PROVES_EDGE, False)
        self.assertIs(
            c.PREDICTIVE_SUCCESS_AUTOMATICALLY_PROVES_PROFITABILITY,
            False,
        )

    def test_live_requires_staged_validation(self):
        self.assertEqual(
            c.LIVE_SEQUENCE,
            (
                "fresh_replication",
                "untouched_forward_validation",
                "paper_or_shadow_execution",
                "very_small_real_capital",
                "measured_live_fill_slippage_validation",
                "gradual_capital_scaling",
            ),
        )
        self.assertIs(c.M6_HISTORICAL_PASS_DIRECTLY_AUTHORIZES_LIVE, False)
        self.assertIs(c.FRESH_REPLICATION_REQUIRED, True)
        self.assertIs(c.UNTOUCHED_FORWARD_REQUIRED, True)
        self.assertIs(c.PAPER_OR_SHADOW_REQUIRED, True)

    def test_contract_does_not_open_execution_surfaces(self):
        values = (
            c.RUN_112_REPLAYS_AUTHORIZED,
            c.HISTORICAL_PNL_AUTHORIZED,
            c.POLICY_EXECUTION_AUTHORIZED,
            c.FEB_TO_JUL_RAW_OPEN_AUTHORIZED,
            c.FEB_TO_JUL_CONVERSION_AUTHORIZED,
            c.AUG_OPEN_AUTHORIZED,
            c.SEP_PLUS_OPEN_AUTHORIZED,
            c.NETWORK_ACQUISITION_AUTHORIZED,
            c.RAILWAY_AUTHORIZED,
            c.LIVE_TRADING_AUTHORIZED,
        )
        self.assertTrue(all(value is False for value in values))


if __name__ == "__main__":
    unittest.main()

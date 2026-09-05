from __future__ import annotations

import unittest

from multimarket import dev045_personal_trading_entry_abstention_gate as c


class TestPersonalTradingEntryAbstentionGateV1(unittest.TestCase):
    def test_exact_parent(self):
        self.assertEqual(
            c.PARENT_HEAD,
            "b7fcb2aceab80ebb910fae59703cad3484197a35",
        )

    def test_entry_is_conjunctive_not_signal_only(self):
        self.assertEqual(
            c.ENTRY_DECISION_MODE,
            "CONJUNCTIVE_ALL_REQUIRED_GATES",
        )
        self.assertIs(c.ALL_REQUIRED_GATES_MUST_PASS, True)
        self.assertIs(c.MAJORITY_VOTE_ENTRY_AUTHORIZED, False)
        self.assertIs(c.SIGNAL_ALONE_AUTHORIZES_ENTRY, False)

    def test_unknown_or_missing_support_abstains(self):
        self.assertEqual(c.DEFAULT_ACTION, "ABSTAIN")
        self.assertIs(c.UNKNOWN_MEANS_ABSTAIN, True)
        self.assertIs(c.MISSING_SUPPORT_MEANS_ABSTAIN, True)
        self.assertIs(c.OUT_OF_SUPPORT_DOMAIN_MEANS_ABSTAIN, True)
        self.assertIs(c.UNSUPPORTED_REGIME_MEANS_ABSTAIN, True)
        self.assertIs(c.UNSUPPORTED_A0_MEANS_ABSTAIN, True)
        self.assertIs(c.MISSING_STATE_SIGNAL_MEANS_ABSTAIN, True)

    def test_required_gates_are_exact(self):
        self.assertEqual(
            c.ENTRY_GATES,
            (
                "strategy_signal_valid",
                "market_regime_supported",
                "liquidity_spread_acceptable",
                "execution_conditions_acceptable",
                "risk_budget_available",
                "confidence_support_sufficient",
            ),
        )

    def test_realism_invariants_remain_strict(self):
        values = (
            c.NO_FUTURE_LEAKAGE,
            c.NO_INVENTED_A0_PROBABILITIES,
            c.NO_UNSUPPORTED_FORWARD_FILL,
            c.NO_IMPOSSIBLE_MAKER_FILLS,
            c.NO_OPTIMISTIC_QUEUE_ASSUMPTIONS,
            c.NO_IGNORED_FEES,
            c.NO_IGNORED_LATENCY,
            c.NO_AUTOMATIC_RESCUE_TUNING,
            c.NO_ENTRY_ON_MISSING_SUPPORT,
            c.NO_FORCED_TRADE_QUOTA,
            c.NO_ALWAYS_IN_MARKET,
        )
        self.assertTrue(all(value is True for value in values))

    def test_confidence_controls_staging_but_never_overrides_safety(self):
        self.assertIs(c.LOW_CONFIDENCE_LIVE_ENTRY_AUTHORIZED, False)
        self.assertIs(c.CONFIDENCE_CAN_OVERRIDE_FAILED_EXECUTION_GATE, False)
        self.assertIs(c.CONFIDENCE_CAN_OVERRIDE_FAILED_RISK_GATE, False)
        self.assertIs(c.CONFIDENCE_CAN_OVERRIDE_FAILED_LIQUIDITY_GATE, False)

    def test_live_sequence_remains_staged(self):
        self.assertEqual(
            c.LIVE_VALIDATION_SEQUENCE,
            (
                "fresh_historical_replication",
                "untouched_forward_validation",
                "paper_or_shadow_execution",
                "very_small_real_capital",
                "measured_live_fill_slippage_validation",
                "gradual_capital_scaling",
            ),
        )
        self.assertIs(c.M6_HISTORICAL_PASS_DIRECTLY_AUTHORIZES_ENTRY, False)

    def test_contract_does_not_open_execution_surfaces(self):
        values = (
            c.ENTRY_EXECUTION_AUTHORIZED,
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

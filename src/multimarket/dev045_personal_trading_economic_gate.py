from __future__ import annotations

EXPERIMENT_ID = "DEV045-PERSONAL-TRADING-GATE-V1"
CONTRACT_ID = "PERSONAL_TRADING_ECONOMIC_GATE_V1"
SCHEMA_VERSION = "dev045-personal-trading-economic-gate-v1"

PARENT_BRANCH = "research/dev045-m6-feb-jul-resource-scaling-contract"
PARENT_HEAD = "caffbfb8bb0a979299a497456ed50e1d3b32f3ac"

OBJECTIVE = (
    "REALISTIC_PERSONAL_TRADING_PROFITABILITY_WITH_CAPITAL_PROTECTION"
)

FROZEN_BEFORE_112_REPLAY_PNL = True
ACADEMIC_PUBLICATION_GATE = False
PERSONAL_TRADING_DECISION_GATE = True

# Primary trading viability gates. These are veto-level because failure means
# the strategy is not realistically tradable in its tested form.
PRIMARY_VETO_GATES = (
    "net_expectancy_positive_after_realistic_costs",
    "profit_factor_above_one",
    "execution_integrity_complete",
    "no_future_leakage",
    "realistic_fees_slippage_latency_queue_fills",
    "drawdown_within_frozen_personal_risk_limit",
    "inventory_and_terminal_state_safe",
)

REALISTIC_BASE_CASE_MUST_PASS = True
REALISTIC_BASE_CASE_REQUIRES = PRIMARY_VETO_GATES

# Adverse conditions are robustness tests. Profit may degrade, but the strategy
# must not exhibit unacceptable collapse relative to the frozen risk envelope.
ADVERSE_CASE_PROFIT_MAY_DEGRADE = True
ADVERSE_CASE_MUST_NOT_UNACCEPTABLY_COLLAPSE = True
ADVERSE_CASE_IS_PRIMARY_RISK_EVIDENCE = True

# Extreme stress is a survival / containment test, not a requirement to remain
# profitable under implausibly severe conditions.
EXTREME_STRESS_PROFITABILITY_REQUIRED = False
EXTREME_STRESS_REQUIRES_BOUNDED_LOSS = True
EXTREME_STRESS_REQUIRES_RISK_CONTROLS = True

# These legacy scientific/robustness gates are retained and reported, but do
# not independently veto a realistically profitable and safely executable
# strategy.
SECONDARY_ROBUSTNESS_AND_CONFIDENCE_EVIDENCE = (
    "familywise_p_value",
    "positive_day_count",
    "profit_concentration",
    "extreme_stress_net_pnl",
)

FWER_P_LE_005_IS_AUTOMATIC_TRADING_VETO = False
FOUR_OF_SEVEN_POSITIVE_DAYS_IS_AUTOMATIC_TRADING_VETO = False
CONCENTRATION_LE_050_IS_AUTOMATIC_TRADING_VETO = False
EXTREME_STRESS_NET_POSITIVE_IS_AUTOMATIC_TRADING_VETO = False

STATISTICAL_EVIDENCE_ROLE = "CONFIDENCE_AND_CAPITAL_SIZING"
ROBUSTNESS_EVIDENCE_ROLE = "CONFIDENCE_AND_CAPITAL_SIZING"

# Failure classification matters. Failing a primary economic or integrity gate
# is not a near-pass. Failing only a secondary confidence gate may still be a
# promising edge requiring lower capital and stronger fresh validation.
PRIMARY_GATE_FAILURE_IS_NEAR_PASS = False
SECONDARY_ONLY_FAILURE_MAY_BE_PROMISING = True

DECISION_DIMENSIONS = (
    "profitability",
    "robustness",
    "confidence",
)

# Historical success is necessary evidence but never proof of live edge.
HISTORICAL_PIPELINE_SUCCESS_PROVES_EDGE = False
PREDICTIVE_SUCCESS_AUTOMATICALLY_PROVES_PROFITABILITY = False
EXECUTION_INFRASTRUCTURE_SUCCESS_AUTOMATICALLY_PROVES_EDGE = False

# Every prior valid success remains usable in its demonstrated role; every
# failure remains preserved as an exclusion, constraint, or lesson.
REUSE_ALL_VALID_PRIOR_SUCCESSES_IN_PROVEN_ROLE = True
PRESERVE_ALL_PRIOR_FAILURES_AS_LESSONS = True
NO_BLIND_ROLE_TRANSFER = True

# Live capital escalation path. Historical M6 evidence alone cannot authorize
# meaningful real capital.
LIVE_SEQUENCE = (
    "fresh_replication",
    "untouched_forward_validation",
    "paper_or_shadow_execution",
    "very_small_real_capital",
    "measured_live_fill_slippage_validation",
    "gradual_capital_scaling",
)

M6_HISTORICAL_PASS_DIRECTLY_AUTHORIZES_LIVE = False
FRESH_REPLICATION_REQUIRED = True
UNTOUCHED_FORWARD_REQUIRED = True
PAPER_OR_SHADOW_REQUIRED = True
SMALL_REAL_CAPITAL_BEFORE_SCALING_REQUIRED = True

# Current execution surfaces remain closed. This contract only changes how the
# eventual economic evidence is interpreted; it does not authorize any replay,
# PnL run, market-data access, conversion, or live action.
RUN_112_REPLAYS_AUTHORIZED = False
HISTORICAL_PNL_AUTHORIZED = False
POLICY_EXECUTION_AUTHORIZED = False
FEB_TO_JUL_RAW_OPEN_AUTHORIZED = False
FEB_TO_JUL_CONVERSION_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False
RAILWAY_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

GOVERNING_PRINCIPLE = (
    "Use every valid prior success in the role it proved, learn from every "
    "failure, and make the final trading test as realistic and strict as "
    "needed to protect capital—not artificially harder than reality. The "
    "goal is a genuine edge that is profitable, robust, and tradable with "
    "our own money."
)

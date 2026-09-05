from __future__ import annotations

EXPERIMENT_ID = "DEV045-PERSONAL-TRADING-ENTRY-ABSTENTION-GATE-V1"
CONTRACT_ID = "PERSONAL_TRADING_ENTRY_ABSTENTION_GATE_V1"
SCHEMA_VERSION = "dev045-personal-trading-entry-abstention-gate-v1"

PARENT_BRANCH = "research/dev045-m6-personal-trading-economic-gate-v1"
PARENT_HEAD = "b7fcb2aceab80ebb910fae59703cad3484197a35"

OBJECTIVE = "ALLOW_ENTRY_ONLY_WHEN_ALL_REQUIRED_REAL_TRADING_GATES_PASS"

ENTRY_DECISION_MODE = "CONJUNCTIVE_ALL_REQUIRED_GATES"
DEFAULT_ACTION = "ABSTAIN"
UNKNOWN_MEANS_ABSTAIN = True
MISSING_SUPPORT_MEANS_ABSTAIN = True
NO_FORCED_TRADE_QUOTA = True
NO_ALWAYS_IN_MARKET_REQUIREMENT = True

ENTRY_GATES = (
    "strategy_signal_valid",
    "market_regime_supported",
    "liquidity_spread_acceptable",
    "execution_conditions_acceptable",
    "risk_budget_available",
    "confidence_support_sufficient",
)

ALL_REQUIRED_GATES_MUST_PASS = True
ANY_REQUIRED_GATE_FAILS_MEANS_ABSTAIN = True
ANY_REQUIRED_GATE_UNKNOWN_MEANS_ABSTAIN = True
MAJORITY_VOTE_ENTRY_AUTHORIZED = False
SIGNAL_ALONE_AUTHORIZES_ENTRY = False

# Safety / realism invariants inherited from the frozen project lineage.
NO_FUTURE_LEAKAGE = True
NO_INVENTED_A0_PROBABILITIES = True
NO_UNSUPPORTED_FORWARD_FILL = True
NO_IMPOSSIBLE_MAKER_FILLS = True
NO_OPTIMISTIC_QUEUE_ASSUMPTIONS = True
NO_IGNORED_FEES = True
NO_IGNORED_LATENCY = True
NO_AUTOMATIC_RESCUE_TUNING = True
NO_ENTRY_ON_MISSING_SUPPORT = True
NO_FORCED_TRADE_QUOTA = True
NO_ALWAYS_IN_MARKET = True

# Confidence is not direction. It controls eligibility/capital staging.
CONFIDENCE_LEVELS = (
    "HIGH",
    "MEDIUM",
    "LOW",
)

HIGH_CONFIDENCE_ROLE = (
    "potentially_larger_allocation_only_after_later_validation"
)
MEDIUM_CONFIDENCE_ROLE = (
    "reduced_allocation_or_paper_shadow_or_tiny_real_stage"
)
LOW_CONFIDENCE_ROLE = "abstain_from_live_capital"

LOW_CONFIDENCE_LIVE_ENTRY_AUTHORIZED = False
CONFIDENCE_CAN_OVERRIDE_FAILED_EXECUTION_GATE = False
CONFIDENCE_CAN_OVERRIDE_FAILED_RISK_GATE = False
CONFIDENCE_CAN_OVERRIDE_FAILED_LIQUIDITY_GATE = False

# Historical support must be in-domain and actually supported.
OUT_OF_SUPPORT_DOMAIN_MEANS_ABSTAIN = True
UNSUPPORTED_REGIME_MEANS_ABSTAIN = True
UNSUPPORTED_A0_MEANS_ABSTAIN = True
MISSING_STATE_SIGNAL_MEANS_ABSTAIN = True

# Economic acceptance of the overall strategy is separate from per-entry eligibility.
PERSONAL_TRADING_ECONOMIC_GATE_MUST_PASS_BEFORE_LIVE_ENTRY = True
M6_HISTORICAL_PASS_DIRECTLY_AUTHORIZES_ENTRY = False

LIVE_VALIDATION_SEQUENCE = (
    "fresh_historical_replication",
    "untouched_forward_validation",
    "paper_or_shadow_execution",
    "very_small_real_capital",
    "measured_live_fill_slippage_validation",
    "gradual_capital_scaling",
)

# This contract changes decision semantics only. It does not open execution.
ENTRY_EXECUTION_AUTHORIZED = False
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

GOVERNING_RULE = (
    "When evidence, support, liquidity, execution conditions, risk budget, "
    "or confidence are insufficient or unknown, the system does not guess: "
    "it abstains."
)

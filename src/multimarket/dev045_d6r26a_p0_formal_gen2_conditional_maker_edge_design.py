from __future__ import annotations


EXPERIMENT_ID = "DEV045-D6R26A-P0"
DESIGN_VERSION = "formal-generation2-conditional-maker-edge-design-v1"

PARENT_D6R25_R1_FREEZE_HEAD = "be9b827d2d4c4ccdeb4ecccf8979e771debd5dd2"
D6R25_R1_RESULT_SHA256 = (
    "dbd0b72b9427a81865280f1c54f606cd9d912fa2776a80eedfd1a0636f085983"
)
D6R25_R1_RESULT_BYTES = 1_929_146
D6R25_R1_CLASSIFICATION = "ZERO_FEE_GROSS_EDGE_NEGATIVE_POLICY_FAMILY_REJECT"

# Generation-2 scope.  This design does not attempt to rescue M01-M08.
GENERATION = 2
SYMBOL = "BTCUSDT"
VENUE = "BINANCE_FUTURES"
MARKET_MAKING_GENERAL_REJECTED = False
GEN1_AS_INSTANTIATED_REJECTED = True

AUTHORIZED_DAYS = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)
DEVELOPMENT_DAYS = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
)
QUALIFICATION_DAYS = (
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)

# Frozen causal decision clock inherited from D1.
DECISION_CLOCK_DOMAIN = "LOCAL_STRATEGY_TIME"
DECISION_STEP_NS = 1_000_000_000
LOCAL_EVENT_ORDER = (
    "LOCAL_MARKET",
    "LOCAL_ORDER_RESPONSE",
    "CANDIDATE_DECISION",
)

# Candidate universe.  Exactly one size in P0/P1/P2/P3.
CANDIDATE_SIDES = ("BID", "ASK")
CANDIDATE_DISTANCE_TICKS = (0, 1, 2, 4)
CANDIDATE_ORDER_QTY = 0.001
TICK_SIZE = 0.1
LOT_SIZE = 0.001
CANDIDATE_TIME_IN_FORCE = "GTX_POST_ONLY"
CANDIDATE_ORDER_TYPE = "LIMIT"
INSIDE_SPREAD_IMPROVEMENT_ALLOWED = False

# Primary queue/fill semantics are inherited from the validated D6R24 asset model,
# except fees are non-decisional and no PnL is computed in D6R26A.
PRIMARY_LABEL_SCENARIO = "Q0_PRIMARY_250_250"
SECONDARY_STRESS_SCENARIO = "Q0_STRESS_500_500"
QUEUE_MODEL = "RISK_ADVERSE"
EXCHANGE_MODEL = "PARTIAL_FILL"
ENTRY_LATENCY_NS = 250_000_000
RESPONSE_LATENCY_NS = 250_000_000
STRESS_ENTRY_LATENCY_NS = 500_000_000
STRESS_RESPONSE_LATENCY_NS = 500_000_000

# To cover every 1-second decision epoch while preventing overlapping candidate
# orders inside one simulator lane, P2 partitions epochs into five phase cohorts.
MAX_CANDIDATE_LIFETIME_NS = 5_000_000_000
LANE_PHASE_OFFSETS_S = (0, 1, 2, 3, 4)
LANE_COUNT_PER_DAY = (
    len(LANE_PHASE_OFFSETS_S)
    * len(CANDIDATE_SIDES)
    * len(CANDIDATE_DISTANCE_TICKS)
)
CANDIDATE_ISOLATION = (
    "ONE_SIDE_X_DISTANCE_X_PHASE_LANE; PREVIOUS ORDER MUST BE TERMINAL "
    "BEFORE NEXT LANE CANDIDATE"
)
EXPIRY_BEFORE_NEXT_PLACEMENT_AT_EQUAL_TIMESTAMP = True

# Fill labels.  CENSORING is never collapsed into NO_FILL.
FILL_HORIZONS_NS = (
    250_000_000,
    500_000_000,
    1_000_000_000,
    2_000_000_000,
    5_000_000_000,
)
PRIMARY_FILL_HORIZON_NS = 1_000_000_000
FILL_LABEL_STATES = (
    "FILLED_WITHIN_TAU",
    "NOT_FILLED_WITHIN_TAU",
    "CENSORED",
)
PLACEMENT_OUTCOMES = (
    "POST_ONLY_ACCEPTED",
    "POST_ONLY_REJECTED_AT_ARRIVAL",
    "CENSORED_BEFORE_PLACEMENT_OUTCOME",
)
CENSORED_MAPS_TO_NO_FILL = False
POST_ONLY_REJECTION_MAPS_TO_OBSERVED_NO_FILL = True
PARTIAL_FILL_FIELDS = (
    "any_fill_within_tau",
    "fill_fraction_at_tau",
    "time_to_first_fill_ns",
    "time_to_full_fill_ns",
)

# Markout target.  Fill price already contains spread capture; no separate spread
# term may be added when this target is used.
MARKOUT_HORIZONS_NS = FILL_HORIZONS_NS
PRIMARY_MARKOUT_HORIZON_NS = 1_000_000_000
MARKOUT_ORIGIN = "EXCHANGE_EXECUTION_TIME"
MARKOUT_REFERENCE = "FUTURE_BBO_MID"
MARKOUT_SIGN = {"BID": 1, "ASK": -1}
MARKOUT_FORMULA = (
    "10000 * side_sign * (future_mid_h - fill_price) / fill_price"
)
CANDIDATE_MULTI_FILL_MARKOUT = (
    "EXECUTED_QTY_WEIGHTED_MEAN_OF_PER_FILL_MARKOUTS"
)
MARKOUT_CENSOR_RULE = (
    "IF ANY INCLUDED FILL LACKS FULL HORIZON OBSERVABILITY, "
    "CANDIDATE_MARKOUT_H_IS_CENSORED"
)
SPREAD_CAPTURE_ADDED_SEPARATELY = False

# Initial A0 local-only feature contract.  Every feature must be observable at or
# before decision_local_ns.  Realized queue-at-arrival is a label diagnostic only.
LOCAL_FEATURE_FAMILIES = {
    "F0_FAIR_VALUE": (
        "spread_ticks",
        "microprice_minus_mid_bps",
        "vamp_bbo_minus_mid_bps",
        "vamp_l5_minus_mid_bps",
    ),
    "F1_FLOW": (
        "l1_obi",
        "l5_obi",
        "bbo_ofi_1s",
        "bbo_ofi_5s",
        "trade_imbalance_1s",
        "trade_imbalance_5s",
        "add_imbalance_1s",
        "cancel_imbalance_1s",
    ),
    "F2_TOXICITY": (
        "ofi_acceleration_1s_vs_5s",
        "same_side_depth_change_250ms",
        "opposite_side_depth_change_250ms",
        "spread_change_1s",
        "realized_vol_1s",
        "realized_vol_5s",
        "realized_vol_30s",
    ),
    "F3_EXECUTION": (
        "candidate_side_sign",
        "candidate_distance_ticks",
        "displayed_qty_at_candidate_price",
        "estimated_queue_ahead_qty_from_decision_book",
        "own_best_depth_qty",
        "opposite_best_depth_qty",
    ),
}
INVENTORY_FEATURES_IN_D6R26A = False
INVENTORY_FEATURES_DEFERRED_TO_D6R26B = True
CROSS_VENUE_FEATURES_IN_A0 = False
CROSS_VENUE_REQUIRES_FROZEN_A0_INCREMENTAL_SUCCESS = True

FORBIDDEN_FEATURES = (
    "realized_queue_ahead_at_exchange_arrival",
    "future_fill_state",
    "future_midprice",
    "future_trade_flow",
    "exchange_event_observed_after_decision_local_ns",
    "cross_venue_feature_without_observability_latency_binding",
)
FEATURE_OBSERVABILITY_RULE = (
    "feature_observable_local_time <= decision_local_time"
)

# Core model families are deliberately small.  No deep model or RL in A0.
FILL_MODEL_FAMILIES = (
    "LOGISTIC_FILL",
    "HGB_FILL",
)
MARKOUT_MODEL_FAMILIES = (
    "RIDGE_MARKOUT",
    "HGB_MARKOUT",
)
DEEP_LEARNING_AUTHORIZED = False
RL_AUTHORIZED = False

# Development uses only Jan-Mar.  Model-family choice is frozen before the
# untouched Apr-Jul qualification surface is opened by P3.
DEVELOPMENT_VALIDATION = "LEAVE_ONE_DAY_OUT_WITHIN_JAN_MAR"
QUALIFICATION_VALIDATION = "STRICT_OUT_OF_TIME_APR_JUL_NO_REFIT"
QUALIFICATION_REFIT_AUTHORIZED = False
QUALIFICATION_THRESHOLD_TUNING_AUTHORIZED = False

FILL_QUALIFICATION_METRICS = (
    "brier_score",
    "log_loss",
    "base_rate_log_loss",
    "reliability_by_probability_bucket",
    "post_only_rejection_rate",
    "censor_rate",
    "partial_fill_rate",
    "full_fill_rate",
    "time_to_first_fill_distribution",
)
MARKOUT_QUALIFICATION_METRICS = (
    "mae_bps",
    "spearman_rank_correlation",
    "top_decile_mean_bps",
    "bottom_decile_mean_bps",
    "top_minus_bottom_bps",
    "mean_bps",
    "median_bps",
    "q10_bps",
    "q25_bps",
    "probability_markout_lt_0",
    "probability_markout_lt_minus_2bp",
)
ROBUSTNESS_METRICS = (
    "bid_vs_ask",
    "qualification_day_by_day",
    "development_loo_day_by_day",
    "volatility_regime",
    "support_coverage",
    "markout_horizon_half_life",
)

# D6R26A is not PnL.  The score is a conditional execution-quality score only.
CORE_EDGE_SCORE = (
    "P(any_fill_within_1s | decision_state, quote) * "
    "E(markout_1s_bps | fill_within_1s, decision_state, quote)"
)
CORE_EDGE_SCORE_IS_REALIZED_PNL = False
PRIMARY_FEE_HURDLE_BPS_DIAGNOSTIC_ONLY = 2.0

# Conservative, pre-registered qualification gates.  A failure cannot be rescued
# by another horizon, side, fee schedule, cross-venue feature, or model family.
QUALIFICATION_GATES = (
    "selected_fill_model_logloss_better_than_base_rate_aggregate",
    "selected_fill_model_logloss_better_than_base_rate_on_at_least_3_of_4_qualification_days",
    "primary_1s_markout_top_decile_mean_gt_bottom_decile_mean_aggregate",
    "primary_1s_markout_top_decile_mean_gt_0_aggregate",
    "primary_1s_markout_top_minus_bottom_gt_0_on_at_least_3_of_4_qualification_days",
    "primary_1s_markout_top_minus_bottom_gt_0_for_bid_and_ask_aggregate",
    "no_missing_or_censored_label_silently_mapped_to_observed_outcome",
)
ALTERNATE_HORIZON_CAN_RESCUE_PRIMARY_GATE_FAILURE = False
SECONDARY_MODEL_CAN_RESCUE_SELECTED_MODEL_QUALIFICATION_FAILURE = False

# Phase separation.
P0_DESIGN_ONLY = True
P1_LABELER_IMPLEMENTATION_SYNTHETIC_ONLY = True
P2_CANONICAL_LABEL_MATERIALIZATION = True
P3_MODEL_OOF_OOT_QUALIFICATION = True
P2_MODEL_FIT_AUTHORIZED = False
P2_PNL_AUTHORIZED = False
P3_SIMULATOR_AUTHORIZED = False
P3_PNL_AUTHORIZED = False

# Closed in this design commit.
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_SOURCE_HASH_AUTHORIZED = False
CANDIDATE_SIMULATION_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
ECONOMIC_ARENA_AUTHORIZED = False
FEE_RESCUE_AUTHORIZED = False
SIZE_TUNING_AUTHORIZED = False
LEVERAGE_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False

DESIGN_EXECUTED_DURING_IMPLEMENTATION = False
HISTORICAL_SOURCE_OPENED_DURING_DESIGN = False
D6R25_R1_RESULT_REINTERPRETED_AS_MARKET_MAKING_FAILURE = False

NEXT_PHASE = "D6R26A_P1_CANDIDATE_LABELER_IMPLEMENTATION_SYNTHETIC_ONLY"


def validate_design_contract() -> None:
    if EXPERIMENT_ID != "DEV045-D6R26A-P0":
        raise RuntimeError("experiment_id")
    if PARENT_D6R25_R1_FREEZE_HEAD != (
        "be9b827d2d4c4ccdeb4ecccf8979e771debd5dd2"
    ):
        raise RuntimeError("parent_freeze")
    if D6R25_R1_RESULT_SHA256 != (
        "dbd0b72b9427a81865280f1c54f606cd9d912fa2776a80eedfd1a0636f085983"
    ):
        raise RuntimeError("d6r25_result_sha")
    if D6R25_R1_CLASSIFICATION != (
        "ZERO_FEE_GROSS_EDGE_NEGATIVE_POLICY_FAMILY_REJECT"
    ):
        raise RuntimeError("d6r25_classification")
    if tuple(AUTHORIZED_DAYS) != DEVELOPMENT_DAYS + QUALIFICATION_DAYS:
        raise RuntimeError("day_partition")
    if DECISION_STEP_NS != 1_000_000_000:
        raise RuntimeError("decision_step")
    if CANDIDATE_SIDES != ("BID", "ASK"):
        raise RuntimeError("candidate_sides")
    if CANDIDATE_DISTANCE_TICKS != (0, 1, 2, 4):
        raise RuntimeError("candidate_distances")
    if CANDIDATE_ORDER_QTY != LOT_SIZE or CANDIDATE_ORDER_QTY != 0.001:
        raise RuntimeError("single_lot_size")
    if CANDIDATE_TIME_IN_FORCE != "GTX_POST_ONLY":
        raise RuntimeError("maker_tif")
    if INSIDE_SPREAD_IMPROVEMENT_ALLOWED:
        raise RuntimeError("inside_spread")
    if QUEUE_MODEL != "RISK_ADVERSE" or EXCHANGE_MODEL != "PARTIAL_FILL":
        raise RuntimeError("execution_semantics")
    if ENTRY_LATENCY_NS != 250_000_000 or RESPONSE_LATENCY_NS != 250_000_000:
        raise RuntimeError("primary_latency")
    if MAX_CANDIDATE_LIFETIME_NS != 5_000_000_000:
        raise RuntimeError("candidate_lifetime")
    if LANE_COUNT_PER_DAY != 40:
        raise RuntimeError("lane_count")
    if CENSORED_MAPS_TO_NO_FILL:
        raise RuntimeError("censor_mapping")
    if not POST_ONLY_REJECTION_MAPS_TO_OBSERVED_NO_FILL:
        raise RuntimeError("post_only_rejection_semantics")
    if PRIMARY_FILL_HORIZON_NS != 1_000_000_000:
        raise RuntimeError("primary_fill_horizon")
    if PRIMARY_MARKOUT_HORIZON_NS != 1_000_000_000:
        raise RuntimeError("primary_markout_horizon")
    if SPREAD_CAPTURE_ADDED_SEPARATELY:
        raise RuntimeError("markout_double_count")
    if CROSS_VENUE_FEATURES_IN_A0:
        raise RuntimeError("cross_venue_a0")
    if INVENTORY_FEATURES_IN_D6R26A:
        raise RuntimeError("inventory_in_a")
    if not INVENTORY_FEATURES_DEFERRED_TO_D6R26B:
        raise RuntimeError("inventory_defer")
    if DEEP_LEARNING_AUTHORIZED or RL_AUTHORIZED:
        raise RuntimeError("complex_model_authorized")
    if QUALIFICATION_REFIT_AUTHORIZED or QUALIFICATION_THRESHOLD_TUNING_AUTHORIZED:
        raise RuntimeError("qualification_tuning")
    if ALTERNATE_HORIZON_CAN_RESCUE_PRIMARY_GATE_FAILURE:
        raise RuntimeError("horizon_rescue")
    if SECONDARY_MODEL_CAN_RESCUE_SELECTED_MODEL_QUALIFICATION_FAILURE:
        raise RuntimeError("model_rescue")
    if CORE_EDGE_SCORE_IS_REALIZED_PNL:
        raise RuntimeError("score_is_pnl")
    forbidden = (
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_SOURCE_HASH_AUTHORIZED,
        CANDIDATE_SIMULATION_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        ECONOMIC_ARENA_AUTHORIZED,
        FEE_RESCUE_AUTHORIZED,
        SIZE_TUNING_AUTHORIZED,
        LEVERAGE_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        NETWORK_ACQUISITION_AUTHORIZED,
        DESIGN_EXECUTED_DURING_IMPLEMENTATION,
        HISTORICAL_SOURCE_OPENED_DURING_DESIGN,
        D6R25_R1_RESULT_REINTERPRETED_AS_MARKET_MAKING_FAILURE,
    )
    if any(forbidden):
        raise RuntimeError("forbidden_authorization")
    if NEXT_PHASE != "D6R26A_P1_CANDIDATE_LABELER_IMPLEMENTATION_SYNTHETIC_ONLY":
        raise RuntimeError("next_phase")


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_D6R25_R1_FREEZE_HEAD",
    "D6R25_R1_RESULT_SHA256",
    "D6R25_R1_CLASSIFICATION",
    "AUTHORIZED_DAYS",
    "DEVELOPMENT_DAYS",
    "QUALIFICATION_DAYS",
    "DECISION_STEP_NS",
    "CANDIDATE_SIDES",
    "CANDIDATE_DISTANCE_TICKS",
    "CANDIDATE_ORDER_QTY",
    "CANDIDATE_TIME_IN_FORCE",
    "FILL_HORIZONS_NS",
    "MARKOUT_HORIZONS_NS",
    "PRIMARY_FILL_HORIZON_NS",
    "PRIMARY_MARKOUT_HORIZON_NS",
    "FILL_LABEL_STATES",
    "PLACEMENT_OUTCOMES",
    "LOCAL_FEATURE_FAMILIES",
    "FORBIDDEN_FEATURES",
    "FILL_MODEL_FAMILIES",
    "MARKOUT_MODEL_FAMILIES",
    "QUALIFICATION_GATES",
    "CORE_EDGE_SCORE",
    "NEXT_PHASE",
    "validate_design_contract",
]

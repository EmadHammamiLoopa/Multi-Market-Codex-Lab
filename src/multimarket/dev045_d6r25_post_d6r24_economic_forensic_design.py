from __future__ import annotations


EXPERIMENT_ID = "DEV045-D6R25"
DESIGN_VERSION = "post-d6r24-economic-forensic-artifact-only-v1"

PARENT_D6R24_FREEZE_HEAD = "06eff337e4a039cf47c8b10a41aa91e52df4c792"
D6R24_EXECUTION_HEAD = "b04a18f8eb5b4689abd15d7cdf6a6c889ee36212"
D6R24_RESULT_SHA256 = (
    "fafae1e2d98a6f5ad63188f69b61b5d42b53ca2e86a7032971378d7f82e31316"
)
D6R24_RESULT_BYTES = 22_165
D6R24_RESULT_GIT_BLOB = "88a5b9c1e9b0b79c38e0466b7b1b99b69d2cb802"
D6R24_FREEZE_GIT_BLOB = "3064dfdc09ab79bb894248e229c332ee383fba85"
D6R24_CLASSIFICATION = (
    "ENGINEERING_CANONICAL_PASS_ECONOMIC_FALSIFICATION_FAIL_ALL_POLICIES"
)

DAY_ORDER = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)
POLICY_ORDER = ("M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08")
SCENARIO_ORDER = ("Q0_PRIMARY_250_250", "Q0_STRESS_500_500")

PRIMARY_MAKER_RATE = 0.0002
PRIMARY_TAKER_RATE = 0.0005
STRESS_MAKER_RATE = 0.0003
STRESS_TAKER_RATE = 0.00075

INPUT_SURFACE = "FROZEN_D6R24_DAY_ARTIFACTS_ONLY"
ONE_DAY_AT_A_TIME = True
MAX_FROZEN_DAY_ARTIFACT_BYTES = 160_744_910

HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_SOURCE_HASH_AUTHORIZED = False
SIMULATOR_AUTHORIZED = False
D6R24_RERUN_AUTHORIZED = False
D6R23_Q1_RERUN_AUTHORIZED = False
D6R22_RERUN_AUTHORIZED = False
D6R21_RERUN_AUTHORIZED = False
Q8_RERUN_AUTHORIZED = False
ECONOMIC_ARENA_RERUN_AUTHORIZED = False
FEE_CHANGE_AUTHORIZED = False
POLICY_RETUNING_AUTHORIZED = False
POLICY_PROMOTION_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

DESIGN_EXECUTED_DURING_IMPLEMENTATION = False
D6R24_DAY_ARTIFACTS_OPENED_DURING_IMPLEMENTATION = False
D6R24_DAY_ARTIFACTS_HASHED_DURING_IMPLEMENTATION = False

CYCLE_FIELDS_REQUIRED = (
    "policy_id",
    "day",
    "start_timestamp_ns",
    "end_timestamp_ns",
    "cash_pnl_before_fees",
    "fees",
    "net_pnl",
    "entry_notional",
    "net_bps",
    "maker_notional",
    "taker_notional",
    "fill_count",
)

AUTHORIZED_DIAGNOSTICS = (
    "cycle_count",
    "total_gross_cash_pnl",
    "total_fees",
    "total_net_pnl",
    "gross_expectancy_bps_cycle_mean",
    "fee_drag_bps_cycle_mean",
    "net_expectancy_bps_cycle_mean",
    "gross_fee_net_parity",
    "gross_expectancy_bps_notional_weighted",
    "fee_drag_bps_notional_weighted",
    "net_expectancy_bps_notional_weighted",
    "positive_gross_cycle_count",
    "positive_gross_cycle_share",
    "positive_net_cycle_count",
    "positive_net_cycle_share",
    "gross_bps_q05_q50_q95",
    "net_bps_q05_q50_q95",
    "cycle_duration_ns_q05_q50_q95",
    "maker_notional",
    "taker_notional",
    "maker_notional_share",
    "taker_notional_share",
    "maker_fee_component",
    "taker_fee_component",
    "uniform_fee_multiplier_break_even",
    "zero_fee_expectancy_bps",
    "daily_gross_fee_net",
    "four_hour_block_gross_fee_net",
    "primary_minus_stress_gross_expectancy_bps",
    "primary_minus_stress_fee_drag_bps",
    "primary_minus_stress_net_expectancy_bps",
    "forced_flatten_count_context_only",
)

UNSUPPORTED_ATTRIBUTIONS = (
    "forced_flatten_pnl_attribution",
    "forced_flatten_fee_attribution",
    "adverse_selection_markout",
    "spread_capture_vs_price_move_decomposition",
    "queue_position_edge_attribution",
)

UNSUPPORTED_REASON = {
    "forced_flatten_pnl_attribution": (
        "saved FillRecord omits order_id, so flatten_order_ids cannot be joined to fills"
    ),
    "forced_flatten_fee_attribution": (
        "saved FillRecord omits order_id, so taker fills cannot be labeled as forced flatten exactly"
    ),
    "adverse_selection_markout": (
        "no post-fill reference midprice/markout series is stored in the frozen day artifacts"
    ),
    "spread_capture_vs_price_move_decomposition": (
        "flat-to-flat gross cash PnL is stored, but no reference-price decomposition is stored"
    ),
    "queue_position_edge_attribution": (
        "artifact contains executed fills and cycle accounting, not queue-position counterfactuals"
    ),
}

FORMULAS = {
    "gross_bps_cycle": "10000 * cash_pnl_before_fees / entry_notional",
    "fee_drag_bps_cycle": "10000 * fees / entry_notional",
    "net_bps_cycle": "10000 * net_pnl / entry_notional",
    "gross_fee_net_cycle_parity": "gross_bps_cycle - fee_drag_bps_cycle == net_bps_cycle",
    "weighted_gross_bps": "10000 * sum(cash_pnl_before_fees) / sum(entry_notional)",
    "weighted_fee_drag_bps": "10000 * sum(fees) / sum(entry_notional)",
    "weighted_net_bps": "10000 * sum(net_pnl) / sum(entry_notional)",
    "maker_fee_component": "maker_notional * frozen_maker_rate",
    "taker_fee_component": "taker_notional * frozen_taker_rate",
    "uniform_fee_multiplier_break_even": (
        "gross_expectancy_bps_cycle_mean / fee_drag_bps_cycle_mean if gross_expectancy_bps_cycle_mean > 0 else NONE"
    ),
    "zero_fee_expectancy_bps": "gross_expectancy_bps_cycle_mean",
}

BREAK_EVEN_CLASSIFICATION = {
    "gross_expectancy_le_zero": "NO_NONNEGATIVE_FEE_MULTIPLIER_CAN_RESCUE_EXPECTANCY",
    "gross_expectancy_gt_zero_and_net_lt_zero": "POSITIVE_GROSS_EDGE_OVERWHELMED_BY_FEES",
    "net_expectancy_ge_zero": "ALREADY_NONNEGATIVE_NET",
}

INTERPRETATION_GUARDS = (
    "D6R24 remains economic FAIL regardless of forensic findings",
    "No M01-M08 policy may be promoted from this forensic",
    "Fee counterfactual is diagnostic only and does not amend frozen Binance fee assumptions",
    "Primary-vs-stress gross delta may diagnose scenario sensitivity but does not prove causal latency attribution",
    "Unsupported attributions must be emitted as NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACT",
)

NEXT_DECISION_CLASSES = (
    "ZERO_FEE_GROSS_EDGE_NEGATIVE_POLICY_FAMILY_REJECT",
    "POSITIVE_GROSS_EDGE_FEE_DOMINATED_REDESIGN_EXECUTION_ECONOMICS",
    "MIXED_BY_POLICY_OR_REGIME_NEW_PREREGISTERED_FAMILY_REQUIRED",
)


def validate_design_contract() -> None:
    if EXPERIMENT_ID != "DEV045-D6R25":
        raise RuntimeError("experiment_id")
    if PARENT_D6R24_FREEZE_HEAD != "06eff337e4a039cf47c8b10a41aa91e52df4c792":
        raise RuntimeError("parent_freeze")
    if D6R24_RESULT_SHA256 != (
        "fafae1e2d98a6f5ad63188f69b61b5d42b53ca2e86a7032971378d7f82e31316"
    ):
        raise RuntimeError("result_sha")
    if D6R24_RESULT_BYTES != 22_165:
        raise RuntimeError("result_bytes")
    if D6R24_CLASSIFICATION != (
        "ENGINEERING_CANONICAL_PASS_ECONOMIC_FALSIFICATION_FAIL_ALL_POLICIES"
    ):
        raise RuntimeError("classification")
    if len(DAY_ORDER) != 7 or len(POLICY_ORDER) != 8 or len(SCENARIO_ORDER) != 2:
        raise RuntimeError("matrix_identity")
    if INPUT_SURFACE != "FROZEN_D6R24_DAY_ARTIFACTS_ONLY":
        raise RuntimeError("input_surface")
    if not ONE_DAY_AT_A_TIME:
        raise RuntimeError("bounded_memory")
    forbidden = (
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_SOURCE_HASH_AUTHORIZED,
        SIMULATOR_AUTHORIZED,
        D6R24_RERUN_AUTHORIZED,
        D6R23_Q1_RERUN_AUTHORIZED,
        D6R22_RERUN_AUTHORIZED,
        D6R21_RERUN_AUTHORIZED,
        Q8_RERUN_AUTHORIZED,
        ECONOMIC_ARENA_RERUN_AUTHORIZED,
        FEE_CHANGE_AUTHORIZED,
        POLICY_RETUNING_AUTHORIZED,
        POLICY_PROMOTION_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
        DESIGN_EXECUTED_DURING_IMPLEMENTATION,
        D6R24_DAY_ARTIFACTS_OPENED_DURING_IMPLEMENTATION,
        D6R24_DAY_ARTIFACTS_HASHED_DURING_IMPLEMENTATION,
    )
    if any(forbidden):
        raise RuntimeError("forbidden_authorization")
    if set(UNSUPPORTED_ATTRIBUTIONS) != set(UNSUPPORTED_REASON):
        raise RuntimeError("unsupported_attribution_contract")
    if "gross_expectancy_bps_cycle_mean" not in AUTHORIZED_DIAGNOSTICS:
        raise RuntimeError("gross_metric_missing")
    if "fee_drag_bps_cycle_mean" not in AUTHORIZED_DIAGNOSTICS:
        raise RuntimeError("fee_metric_missing")
    if "uniform_fee_multiplier_break_even" not in AUTHORIZED_DIAGNOSTICS:
        raise RuntimeError("break_even_metric_missing")
    if BREAK_EVEN_CLASSIFICATION["gross_expectancy_le_zero"] != (
        "NO_NONNEGATIVE_FEE_MULTIPLIER_CAN_RESCUE_EXPECTANCY"
    ):
        raise RuntimeError("zero_fee_guard")


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_D6R24_FREEZE_HEAD",
    "D6R24_RESULT_SHA256",
    "D6R24_RESULT_BYTES",
    "DAY_ORDER",
    "POLICY_ORDER",
    "SCENARIO_ORDER",
    "CYCLE_FIELDS_REQUIRED",
    "AUTHORIZED_DIAGNOSTICS",
    "UNSUPPORTED_ATTRIBUTIONS",
    "UNSUPPORTED_REASON",
    "FORMULAS",
    "BREAK_EVEN_CLASSIFICATION",
    "INTERPRETATION_GUARDS",
    "NEXT_DECISION_CLASSES",
    "validate_design_contract",
]

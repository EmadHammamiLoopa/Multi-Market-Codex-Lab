from __future__ import annotations

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as d


def test_contract_validates() -> None:
    d.validate_design_contract()


def test_exact_parent_and_scope() -> None:
    assert d.PARENT_D6R25_R1_FREEZE_HEAD == (
        "be9b827d2d4c4ccdeb4ecccf8979e771debd5dd2"
    )
    assert d.D6R25_R1_CLASSIFICATION == (
        "ZERO_FEE_GROSS_EDGE_NEGATIVE_POLICY_FAMILY_REJECT"
    )
    assert d.GENERATION == 2
    assert d.GEN1_AS_INSTANTIATED_REJECTED is True
    assert d.MARKET_MAKING_GENERAL_REJECTED is False


def test_candidate_universe_is_frozen() -> None:
    assert d.DECISION_STEP_NS == 1_000_000_000
    assert d.CANDIDATE_SIDES == ("BID", "ASK")
    assert d.CANDIDATE_DISTANCE_TICKS == (0, 1, 2, 4)
    assert d.CANDIDATE_ORDER_QTY == 0.001
    assert d.CANDIDATE_TIME_IN_FORCE == "GTX_POST_ONLY"
    assert d.CANDIDATE_ORDER_TYPE == "LIMIT"
    assert d.INSIDE_SPREAD_IMPROVEMENT_ALLOWED is False
    assert d.LANE_COUNT_PER_DAY == 40
    assert d.MAX_CANDIDATE_LIFETIME_NS == 5_000_000_000


def test_censoring_and_partial_fill_semantics() -> None:
    assert d.FILL_LABEL_STATES == (
        "FILLED_WITHIN_TAU",
        "NOT_FILLED_WITHIN_TAU",
        "CENSORED",
    )
    assert d.CENSORED_MAPS_TO_NO_FILL is False
    assert d.POST_ONLY_REJECTION_MAPS_TO_OBSERVED_NO_FILL is True
    assert "fill_fraction_at_tau" in d.PARTIAL_FILL_FIELDS
    assert "time_to_first_fill_ns" in d.PARTIAL_FILL_FIELDS
    assert "time_to_full_fill_ns" in d.PARTIAL_FILL_FIELDS


def test_markout_has_no_spread_double_count() -> None:
    assert d.MARKOUT_ORIGIN == "EXCHANGE_EXECUTION_TIME"
    assert d.MARKOUT_REFERENCE == "FUTURE_BBO_MID"
    assert d.MARKOUT_SIGN == {"BID": 1, "ASK": -1}
    assert d.SPREAD_CAPTURE_ADDED_SEPARATELY is False
    assert d.PRIMARY_MARKOUT_HORIZON_NS == 1_000_000_000
    assert d.CANDIDATE_MULTI_FILL_MARKOUT == (
        "EXECUTED_QTY_WEIGHTED_MEAN_OF_PER_FILL_MARKOUTS"
    )


def test_local_only_a0_and_no_leakage() -> None:
    assert d.CROSS_VENUE_FEATURES_IN_A0 is False
    assert d.INVENTORY_FEATURES_IN_D6R26A is False
    assert d.INVENTORY_FEATURES_DEFERRED_TO_D6R26B is True
    assert d.FEATURE_OBSERVABILITY_RULE == (
        "feature_observable_local_time <= decision_local_time"
    )
    assert "realized_queue_ahead_at_exchange_arrival" in d.FORBIDDEN_FEATURES
    assert "future_midprice" in d.FORBIDDEN_FEATURES


def test_development_qualification_separation() -> None:
    assert d.DEVELOPMENT_DAYS == (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
    )
    assert d.QUALIFICATION_DAYS == (
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    )
    assert d.DEVELOPMENT_VALIDATION == "LEAVE_ONE_DAY_OUT_WITHIN_JAN_MAR"
    assert d.QUALIFICATION_VALIDATION == "STRICT_OUT_OF_TIME_APR_JUL_NO_REFIT"
    assert d.QUALIFICATION_REFIT_AUTHORIZED is False
    assert d.QUALIFICATION_THRESHOLD_TUNING_AUTHORIZED is False


def test_primary_gate_cannot_be_rescued_posthoc() -> None:
    assert d.PRIMARY_FILL_HORIZON_NS == 1_000_000_000
    assert d.PRIMARY_MARKOUT_HORIZON_NS == 1_000_000_000
    assert d.ALTERNATE_HORIZON_CAN_RESCUE_PRIMARY_GATE_FAILURE is False
    assert d.SECONDARY_MODEL_CAN_RESCUE_SELECTED_MODEL_QUALIFICATION_FAILURE is False


def test_p0_is_closed() -> None:
    assert d.P0_DESIGN_ONLY is True
    assert d.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert d.HISTORICAL_SOURCE_HASH_AUTHORIZED is False
    assert d.CANDIDATE_SIMULATION_AUTHORIZED is False
    assert d.MODEL_FIT_AUTHORIZED is False
    assert d.PNL_AUTHORIZED is False
    assert d.ECONOMIC_ARENA_AUTHORIZED is False
    assert d.FEE_RESCUE_AUTHORIZED is False
    assert d.SIZE_TUNING_AUTHORIZED is False
    assert d.LEVERAGE_AUTHORIZED is False
    assert d.LIVE_TRADING_AUTHORIZED is False
    assert d.AUG_OPEN_AUTHORIZED is False
    assert d.SEP_PLUS_OPEN_AUTHORIZED is False
    assert d.NON_BTC_OPEN_AUTHORIZED is False

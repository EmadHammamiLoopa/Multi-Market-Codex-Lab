from multimarket import dev045_d6r26a_p2_jan_jul_consumed_development_label_design as p2


def test_p2_design_contract():
    p2.validate_design_contract()


def test_all_jan_jul_are_consumed_development():
    assert p2.DATA_ROLE == "CONSUMED_DEVELOPMENT"
    assert p2.APR_JUL_ROLE == "CONSUMED_DEVELOPMENT"
    assert len(p2.REAL_DEVELOPMENT_DAYS) == 7
    assert p2.INTERNAL_FRESH_HOLDOUT_DAYS == ()
    assert p2.INDEPENDENT_REPLICATION_CLAIM_FROM_JAN_JUL_AUTHORIZED is False


def test_final_real_bucket_remains_sealed_and_external_to_jan_jul():
    assert p2.FINAL_REAL_BUCKET_ROLE == "UNTOUCHED_ONE_SHOT_HISTORICAL_HOLDOUT"
    assert p2.FINAL_REAL_BUCKET_ASSIGNED is False
    assert p2.FINAL_REAL_BUCKET_OPEN_AUTHORIZED is False
    assert p2.FINAL_REAL_BUCKET_SELECTION_FROM_JAN_JUL_AUTHORIZED is False


def test_candidate_and_lane_surface_frozen():
    assert p2.CANDIDATE_SIDES == ("BID", "ASK")
    assert p2.CANDIDATE_DISTANCE_TICKS == (0, 1, 2, 4)
    assert p2.CANDIDATE_ORDER_QTY == 0.001
    assert p2.CANDIDATE_TIME_IN_FORCE == "GTX_POST_ONLY"
    assert p2.LANES_PER_DAY == 40
    assert p2.TOTAL_LANES == 280
    assert p2.MAX_PARALLEL_LANES == 8


def test_materialization_shape_and_censoring():
    assert p2.ROW_GRAIN == "ONE_DECISION_EPOCH_X_SIDE_X_DISTANCE"
    assert p2.OUTPUT_FORMAT == "PARQUET_ZSTD"
    assert p2.ONE_DAY_AT_A_TIME is True
    assert p2.BOUNDED_MEMORY is True
    assert p2.END_OF_SOURCE_CANDIDATES_RETAINED_WITH_CENSORING is True
    assert p2.CENSORED_MAPS_TO_NO_FILL is False
    assert p2.MISSING_LABELS_DROPPED is False
    assert p2.MISSING_FEATURE_ROWS_DROPPED is False


def test_p2_design_is_closed():
    forbidden = (
        p2.HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        p2.HISTORICAL_SOURCE_HASH_AUTHORIZED,
        p2.CANDIDATE_SIMULATION_AUTHORIZED,
        p2.CANONICAL_LABEL_WRITE_AUTHORIZED,
        p2.MODEL_FIT_AUTHORIZED,
        p2.MODEL_SELECTION_AUTHORIZED,
        p2.THRESHOLD_TUNING_AUTHORIZED,
        p2.PNL_AUTHORIZED,
        p2.ECONOMIC_ARENA_AUTHORIZED,
        p2.LIVE_TRADING_AUTHORIZED,
        p2.AUG_OPEN_AUTHORIZED,
        p2.SEP_PLUS_OPEN_AUTHORIZED,
        p2.NON_BTC_OPEN_AUTHORIZED,
        p2.NETWORK_ACQUISITION_AUTHORIZED,
    )
    assert not any(forbidden)

from __future__ import annotations

from multimarket import (
    dev045_d6r_bounded_converter_contract as c,
)


def test_d6b_failure_is_immutable() -> None:
    assert c.D6B_STATUS == "FAIL"
    assert c.D6B_PREFLIGHT_STATUS == "PASS"
    assert c.D6B_MEMORY_GATE_PASS is False
    assert c.D6B_CONVERTER_EXECUTED is False

    assert c.D6B_RERUN_ALLOWED is False
    assert c.D6B_GATE_RELAXATION_ALLOWED is False

    assert c.OLD_D6C_WHOLE_DAY_PATH_AUTHORIZED is False


def test_amendment_is_resource_only() -> None:
    assert (
        c.AMENDMENT_REASON
        == "WHOLE_DAY_CONVERTER_RESOURCE_INFEASIBLE"
    )

    assert c.AMENDMENT_CHANGES_MARKET_SEMANTICS is False
    assert c.AMENDMENT_CHANGES_POLICY_SEMANTICS is False
    assert c.AMENDMENT_CHANGES_FEES is False
    assert c.AMENDMENT_CHANGES_LATENCY is False
    assert c.AMENDMENT_CHANGES_ECONOMIC_GATES is False

    assert c.AMENDMENT_IS_MEMORY_EXECUTION_PATH_ONLY is True


def test_upstream_oracle_is_exact() -> None:
    assert c.HFTBACKTEST_VERSION == "2.4.4"

    assert (
        c.HFTBACKTEST_UPSTREAM_COMMIT
        == "a244a14250b42d97fc305569c93c4117cd5e1dff"
    )

    assert (
        c.UPSTREAM_TARDIS_GIT_BLOB
        == "1ca038895d30f320561d6b28ffa13c1d788ea6bf"
    )

    assert (
        c.UPSTREAM_VALIDATION_GIT_BLOB
        == "60c6ca3458f16417e41deb3d86c40e9df3df5d7c"
    )

    assert c.EVENT_DTYPE_ITEMSIZE_BYTES == 64


def test_conversion_semantics_are_frozen() -> None:
    assert c.INPUT_FILE_ORDER == (
        "trades",
        "incremental_book_L2",
    )

    assert c.TIMESTAMP_SCALE_US_TO_NS == 1000
    assert c.BASE_LATENCY == 0
    assert c.SNAPSHOT_MODE == "process"

    assert c.DEPTH_ZERO_QTY_PRESERVED is True

    assert (
        c.SNAPSHOT_BATCH_STATE_MUST_CROSS_CHUNK_BOUNDARIES
        is True
    )


def test_snapshot_flush_order_is_exact() -> None:
    assert c.SNAPSHOT_FLUSH_ORDER == (
        "BID_CLEAR",
        "BID_SNAPSHOT_ROWS",
        "ASK_CLEAR",
        "ASK_SNAPSHOT_ROWS",
        "CURRENT_NON_SNAPSHOT_DEPTH_ROW",
    )

    assert c.SNAPSHOT_CLEAR_QTY == 0.0


def test_source_sequence_recreates_stable_order() -> None:
    assert c.SOURCE_SEQUENCE_REQUIRED is True

    assert (
        c.SOURCE_SEQUENCE_ORDER
        == "ALL_CONVERTED_TRADE_EVENTS_FIRST_"
        "THEN_ALL_CONVERTED_DEPTH_EVENTS"
    )

    assert c.SOURCE_SEQUENCE_WRITTEN_TO_FINAL_OUTPUT is False


def test_bounded_memory_contract() -> None:
    assert c.PRODUCTION_RAW_CHUNK_ROWS == 500_000

    assert c.WHOLE_DAY_POLARS_READ_ALLOWED is False
    assert c.WHOLE_DAY_NUMPY_PREALLOCATION_ALLOWED is False

    assert c.EXTERNAL_STABLE_SORT_REQUIRED is True

    assert c.EXCHANGE_SORT_KEYS == (
        "exch_ts",
        "source_seq",
    )

    assert c.LOCAL_SORT_KEYS == (
        "local_ts",
        "source_seq",
    )


def test_final_merge_reuses_upstream_logic() -> None:
    assert (
        c.FINAL_ORDER_ALGORITHM
        == "UPSTREAM_CORRECT_EVENT_ORDER_EXACT"
    )

    assert c.FINAL_MERGE_REQUIRES_TWO_GLOBAL_STREAMS is True

    assert (
        c.EXACT_TIMESTAMP_PAIR_REQUIRES_SAME_SOURCE_SEQ
        is True
    )


def test_disk_backed_output_contract() -> None:
    assert (
        c.FINAL_OUTPUT_FORMAT
        == "NUMPY_NPY_EVENT_DTYPE"
    )

    assert c.FINAL_OUTPUT_DISK_BACKED is True
    assert c.FINAL_OUTPUT_MEMORY_MAP_COMPATIBLE is True

    assert c.FINAL_OUTPUT_TWO_PASS_MERGE is True
    assert c.FINAL_OUTPUT_CONTAINS_SOURCE_SEQ is False

    assert c.FINAL_OUTPUT_FILE_NOT_COMMITTED_TO_GIT is True
    assert c.FINAL_OUTPUT_SHA256_EVIDENCE_REQUIRED is True


def test_synthetic_oracle_parity_is_mandatory() -> None:
    assert c.SYNTHETIC_ORACLE_PARITY_REQUIRED is True

    assert c.SYNTHETIC_TEST_CHUNK_SIZES == (
        1,
        2,
        3,
        7,
    )

    assert (
        c.SYNTHETIC_PARITY_COMPARISON
        == "FIELDWISE_EXACT_NAN_EQUAL"
    )


def test_real_parity_slice_is_fixed_before_execution() -> None:
    assert c.REAL_PARITY_REQUIRED is True
    assert c.REAL_PARITY_DAY == "2026-01-01"
    assert c.REAL_PARITY_SYMBOL == "BTCUSDT"

    assert c.REAL_PARITY_WINDOW_START_SECONDS == 0
    assert c.REAL_PARITY_WINDOW_END_SECONDS == 600

    assert c.REAL_PARITY_SELECTION_USES_PNL is False
    assert c.REAL_PARITY_SELECTION_USES_POLICY_RESULT is False


def test_full_day_remains_closed() -> None:
    assert c.FULL_DAY_CANARY_DAY == "2026-01-01"

    assert (
        c.FULL_DAY_BOUNDED_CONVERSION_AUTHORIZED_NOW
        is False
    )

    assert c.RESOURCE_PREFLIGHT_REQUIRED is True


def test_economic_surfaces_remain_closed() -> None:
    assert c.NETWORK_MARKET_DATA_ACQUISITION_ALLOWED is False

    assert c.AUG01_ALLOWED is False
    assert c.SEP_PLUS_ALLOWED is False
    assert c.NON_BTC_ALLOWED is False

    assert c.POLICY_EXECUTION_ALLOWED is False
    assert c.M01_M08_EXECUTION_ALLOWED is False

    assert c.HISTORICAL_POLICY_REPLAY_ALLOWED is False
    assert c.HISTORICAL_PNL_ALLOWED is False

    assert c.ECONOMIC_ARENA_ALLOWED is False
    assert c.CANONICAL_PNL_WRITE_ALLOWED is False

    assert c.RAILWAY_ALLOWED is False
    assert c.LIVE_TRADING_ALLOWED is False

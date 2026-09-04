from __future__ import annotations

from multimarket import (
    dev045_d6r2_real_parity_contract as c,
)


def test_parent_and_synthetic_prerequisite() -> None:
    assert (
        c.PARENT_HEAD
        == "c0647ef3ad32db199401643aa0324fe3e12133b8"
    )

    assert c.D6R1B_STATUS == "PASS"
    assert c.D6R1B_CANONICAL_ATTEMPT == 1

    assert c.D6R1B_REQUIRED_CHUNKS == (
        1,
        2,
        3,
        7,
    )


def test_frozen_real_scope() -> None:
    assert c.EXCHANGE == "binance-futures"
    assert c.SYMBOL == "BTCUSDT"
    assert c.DAY == "2026-01-01"

    assert (
        c.TRADE_RELATIVE_PATH
        == "trades/BTCUSDT/2026-01-01.csv.gz"
    )

    assert (
        c.DEPTH_RELATIVE_PATH
        == "incremental_book_L2/BTCUSDT/2026-01-01.csv.gz"
    )


def test_window_is_exactly_first_ten_minutes() -> None:
    assert (
        c.WINDOW_START_LOCAL_TIMESTAMP_US
        == 1_767_225_600_000_000
    )

    assert (
        c.WINDOW_END_LOCAL_TIMESTAMP_US
        == 1_767_226_200_000_000
    )

    assert c.WINDOW_DURATION_SECONDS == 600

    assert c.SELECTION_FIELD == "local_timestamp"

    assert c.SELECTION_LEFT_INCLUSIVE is True
    assert c.SELECTION_RIGHT_EXCLUSIVE is True

    assert c.WINDOW_EXTENSION_ALLOWED is False
    assert c.WINDOW_SHRINK_ALLOWED is False


def test_selection_has_no_economic_information() -> None:
    assert c.SELECTION_USES_EXCHANGE_TIMESTAMP is False
    assert c.SELECTION_USES_PNL is False
    assert c.SELECTION_USES_POLICY_RESULT is False
    assert c.SELECTION_USES_MODEL_OUTPUT is False
    assert c.SELECTION_USES_FUTURE_DATA is False


def test_extraction_preserves_rows() -> None:
    assert c.EXTRACTION_MODE == "SEQUENTIAL_GZIP_CSV_STREAM"

    assert (
        c.PHYSICAL_LOCAL_TIMESTAMP_MONOTONIC_REQUIRED
        is True
    )

    assert c.ORIGINAL_HEADER_PRESERVED is True
    assert c.ORIGINAL_ROW_TEXT_PRESERVED is True
    assert c.ORIGINAL_ROW_ORDER_PRESERVED is True

    assert (
        c.STOP_AT_FIRST_LOCAL_TIMESTAMP_GTE_WINDOW_END
        is True
    )


def test_snapshot_boundary_is_fail_closed() -> None:
    assert c.DEPTH_INITIAL_SNAPSHOT_REQUIRED is True

    assert (
        c.DEPTH_END_OUTSIDE_SNAPSHOT_BATCH_REQUIRED
        is True
    )

    assert c.TRAILING_SNAPSHOT_CAUSES_FAIL is True

    assert (
        c.WINDOW_MAY_NOT_BE_EXTENDED_FOR_SNAPSHOT
        is True
    )


def test_upstream_oracle_is_frozen() -> None:
    assert c.HFTBACKTEST_VERSION == "2.4.4"

    assert (
        c.HFTBACKTEST_UPSTREAM_COMMIT
        == "a244a14250b42d97fc305569c93c4117cd5e1dff"
    )

    assert c.ORACLE_FILE_ORDER == (
        "trades",
        "incremental_book_L2",
    )

    assert c.ORACLE_OUTPUT_FILENAME is None
    assert c.ORACLE_BASE_LATENCY == 0
    assert c.ORACLE_SNAPSHOT_MODE == "process"


def test_bounded_candidate_uses_production_chunk() -> None:
    assert c.PRODUCTION_CHUNK_ROWS == 500_000
    assert c.BOUNDED_CHUNK_ROWS == 500_000

    assert c.BOUNDED_OUTPUT_DISK_BACKED is True


def test_process_isolation_and_rss_measurement() -> None:
    assert (
        c.ORACLE_EXECUTION_PROCESS
        == "FRESH_PYTHON_SUBPROCESS"
    )

    assert (
        c.BOUNDED_EXECUTION_PROCESS
        == "FRESH_PYTHON_SUBPROCESS"
    )

    assert c.PEAK_RSS_MEASUREMENT_REQUIRED is True

    assert (
        c.PEAK_RSS_TARGET
        == "BOUNDED_CONVERTER_FRESH_SUBPROCESS"
    )

    assert c.PEAK_RSS_PLATFORM == "LINUX"
    assert c.PEAK_RSS_SOURCE_UNIT == "KIB"

    assert c.ORACLE_PEAK_RSS_IS_RESOURCE_GATE_INPUT is False
    assert c.BOUNDED_PEAK_RSS_IS_RESOURCE_GATE_INPUT is True


def test_exact_parity_contract() -> None:
    assert c.PARITY_REQUIRED is True

    assert (
        c.PARITY_COMPARISON
        == "FIELDWISE_EXACT_NAN_EQUAL"
    )

    assert c.PARITY_ROW_REORDERING_ALLOWED is False
    assert c.PARITY_FLOAT_TOLERANCE_ALLOWED is False

    assert c.PARITY_SHAPE_EQUAL_REQUIRED is True
    assert c.PARITY_DTYPE_EQUAL_REQUIRED is True
    assert c.PARITY_ITEMSIZE_REQUIRED == 64


def test_one_shot_result_is_frozen() -> None:
    assert c.CANONICAL_REAL_PARITY_ATTEMPTS == 1

    assert c.FIRST_RESULT_FROZEN_PASS_OR_FAIL is True
    assert c.REAL_PARITY_RERUN_AFTER_RESULT_ALLOWED is False


def test_full_day_still_closed() -> None:
    assert c.FULL_DAY_CONVERSION_AUTHORIZED_NOW is False

    assert (
        c.RESOURCE_PREFLIGHT_REQUIRED_AFTER_REAL_PARITY
        is True
    )

    assert (
        c.REAL_PARITY_PASS_NEXT_GATE
        == "FREEZE_FULL_DAY_RESOURCE_PREFLIGHT_CONTRACT"
    )


def test_economic_and_future_surfaces_closed() -> None:
    assert c.RAW_BYTES_MODIFICATION_ALLOWED is False

    assert c.OTHER_REAL_WINDOWS_ALLOWED is False
    assert c.OTHER_DAYS_ALLOWED is False

    assert c.AUG01_ALLOWED is False
    assert c.SEP_PLUS_ALLOWED is False
    assert c.NON_BTC_ALLOWED is False

    assert c.POLICY_EXECUTION_ALLOWED is False
    assert c.M01_M08_EXECUTION_ALLOWED is False

    assert c.HISTORICAL_POLICY_REPLAY_ALLOWED is False
    assert c.HISTORICAL_PNL_ALLOWED is False

    assert c.ECONOMIC_ARENA_ALLOWED is False
    assert c.CANONICAL_PNL_WRITE_ALLOWED is False

    assert c.NETWORK_MARKET_DATA_ACQUISITION_ALLOWED is False

    assert c.RAILWAY_ALLOWED is False
    assert c.LIVE_TRADING_ALLOWED is False


def test_d6r2a_itself_does_not_open_real_data() -> None:
    assert c.REAL_RAW_CONTENT_OPEN_AUTHORIZED_BY_D6R2A is False
    assert c.REAL_PARITY_EXECUTION_AUTHORIZED_BY_D6R2A is False

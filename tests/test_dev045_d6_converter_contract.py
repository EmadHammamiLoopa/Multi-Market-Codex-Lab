from __future__ import annotations

from multimarket import (
    dev045_d6_converter_contract as c,
)


def test_parent_and_d5b_are_frozen() -> None:
    assert (
        c.PARENT_HEAD
        == "d8d9935579b703d10107435d9d14c3be0be49654"
    )

    assert (
        c.D5B_ARTIFACT_SHA256
        == "51af9bbf48d36de43ee7ce8337f6ef77"
        "2cd74c555c1bc2f85db485d3d463d96a"
    )

    assert c.D5B_REQUIRED_STATUS == "PASS"
    assert c.D5B_REQUIRED_TOTAL_VIOLATIONS == 0


def test_converter_lineage_is_frozen() -> None:
    assert c.HFTBACKTEST_VERSION == "2.4.4"

    assert (
        c.HFTBACKTEST_UPSTREAM_COMMIT
        == "a244a14250b42d97fc305569c93c4117cd5e1dff"
    )

    assert (
        c.UPSTREAM_TARDIS_GIT_BLOB
        == "1ca038895d30f320561d6b28ffa13c1d788ea6bf"
    )

    assert c.TARDIS_CONVERTER_CHANGED_BY_M1_PATCH is False


def test_project_binding_is_frozen() -> None:
    assert (
        c.FEED_MODULE_GIT_BLOB
        == "8bf7d620ce54cfa0ef759e9f8a866cea39570bc8"
    )

    assert (
        c.FEED_TEST_GIT_BLOB
        == "21b7d01db28da4924dec13aa611dd87f0bdcb76f"
    )

    assert (
        c.PATCH_SCRIPT_GIT_BLOB
        == "3b839a2b87d3399d573db5777a7db030e579b291"
    )

    assert (
        c.M4_ADAPTER_GIT_BLOB
        == "7f6a321b4512dd1ec1edf94c79416e176ee75e1c"
    )


def test_canary_selection_is_resource_only() -> None:
    assert c.CANARY_DAY == "2026-01-01"
    assert c.CANARY_SYMBOL == "BTCUSDT"

    assert (
        c.CANARY_SELECTION_REASON
        == "MINIMUM_D5B_TOTAL_ROWS_RESOURCE_SAFETY_ONLY"
    )

    assert c.CANARY_SELECTED_FROM_ECONOMIC_RESULT is False
    assert c.CANARY_PNL_CONSULTED is False


def test_converter_call_semantics_are_frozen() -> None:
    assert c.INPUT_ORDER == (
        "trades",
        "incremental_book_L2",
    )

    assert c.SNAPSHOT_MODE == "process"
    assert c.BASE_LATENCY == 0
    assert c.OUTPUT_FILENAME is None

    assert c.NETWORK_ACQUISITION_ALLOWED is False
    assert c.RAW_BYTES_MODIFICATION_ALLOWED is False


def test_event_dtype_contract_is_exact() -> None:
    assert c.EVENT_DTYPE_FIELDS == (
        "ev",
        "exch_ts",
        "local_ts",
        "px",
        "qty",
        "order_id",
        "ival",
        "fval",
    )

    assert c.EVENT_DTYPE_ITEMSIZE_BYTES == 64


def test_d6b_is_preflight_only() -> None:
    assert c.D6B_CONVERTER_EXECUTION_ALLOWED is False

    assert c.D6B_RAW_SCOPE == (
        ("trades", "BTCUSDT", "2026-01-01"),
        (
            "incremental_book_L2",
            "BTCUSDT",
            "2026-01-01",
        ),
    )

    assert c.D6B_REQUIRE_FEED_PREFLIGHT is True

    assert (
        c.D6B_REQUIRE_MACHINE_MEMORY_MEASUREMENT
        is True
    )

    assert c.MEMORY_SAFETY_MULTIPLIER == 4


def test_d6c_requires_frozen_d6b_pass() -> None:
    assert c.D6C_REQUIRES_FROZEN_D6B_PASS is True
    assert c.D6C_REAL_CONVERTER_EXECUTION_ALLOWED is True

    assert c.D6C_IN_MEMORY_ONLY is True
    assert c.D6C_NPZ_WRITE_ALLOWED is False


def test_d6c_validation_requirements_are_frozen() -> None:
    assert c.D6C_REQUIRE_M4_EVENT_VALIDATION is True
    assert c.D6C_REQUIRE_NONEMPTY_OUTPUT is True

    assert c.D6C_REQUIRE_TRADE_EVENT is True
    assert c.D6C_REQUIRE_DEPTH_SNAPSHOT_EVENT is True

    assert c.D6C_REQUIRE_LOCAL_GTE_EXCHANGE is True

    assert (
        c.D6C_REQUIRE_LOCAL_TIMESTAMP_CANARY_DAY
        is True
    )

    assert c.D6C_REQUIRE_EVENT_DTYPE_FIELDS is True
    assert c.D6C_REQUIRE_EVENT_DTYPE_ITEMSIZE is True


def test_economic_execution_remains_closed() -> None:
    assert c.HFTBACKTEST_POLICY_EXECUTION_ALLOWED is False
    assert c.M01_M08_EXECUTION_ALLOWED is False

    assert c.HISTORICAL_POLICY_REPLAY_ALLOWED is False
    assert c.HISTORICAL_PNL_ALLOWED is False

    assert c.ECONOMIC_ARENA_ALLOWED is False
    assert c.CANONICAL_PNL_WRITE_ALLOWED is False

    assert c.AUG01_ALLOWED is False
    assert c.SEP_PLUS_ALLOWED is False
    assert c.NON_BTC_ALLOWED is False

    assert c.RAILWAY_ALLOWED is False
    assert c.LIVE_TRADING_ALLOWED is False

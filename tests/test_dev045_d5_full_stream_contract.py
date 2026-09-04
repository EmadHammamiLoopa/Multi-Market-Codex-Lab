from __future__ import annotations

from multimarket import (
    dev045_d5_full_stream_contract as c,
)


def test_identity_is_frozen() -> None:
    assert (
        c.CONTRACT_ID
        == "DEV045-D5-FULL-STREAM-INTEGRITY-V1"
    )

    assert (
        c.PARENT_HEAD
        == "47d45f011c15f9d37089bf2627228a524a63e1cf"
    )

    assert (
        c.D4_MANIFEST_SHA256
        == "7fa6cf76ee8c6da98c5758756c887f0f"
        "b7b4d2e5eaf6b0e9f87551dce9981c12"
    )


def test_exact_market_scope_is_frozen() -> None:
    assert c.EXPECTED_EXCHANGE == "binance-futures"
    assert c.EXPECTED_SYMBOL == "BTCUSDT"

    assert c.EXPECTED_DAYS == (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    )

    assert c.EXPECTED_KINDS == (
        "trades",
        "incremental_book_L2",
    )

    assert c.EXPECTED_FILE_COUNT == 14
    assert len(c.EXPECTED_STREAMS) == 14
    assert len(set(c.EXPECTED_STREAMS)) == 14


def test_exact_headers_are_frozen() -> None:
    assert c.EXPECTED_FIELD_COUNT == 8

    assert c.EXPECTED_HEADERS["trades"] == (
        "exchange",
        "symbol",
        "timestamp",
        "local_timestamp",
        "id",
        "side",
        "price",
        "amount",
    )

    assert (
        c.EXPECTED_HEADERS["incremental_book_L2"]
        == (
            "exchange",
            "symbol",
            "timestamp",
            "local_timestamp",
            "is_snapshot",
            "side",
            "price",
            "amount",
        )
    )


def test_market_value_semantics_are_frozen() -> None:
    assert c.REQUIRE_FINITE_PRICE is True
    assert c.REQUIRE_FINITE_AMOUNT is True

    assert c.TRADES_PRICE_RULE == ">0"
    assert c.TRADES_AMOUNT_RULE == ">0"

    assert c.DEPTH_PRICE_RULE == ">0"
    assert c.DEPTH_AMOUNT_RULE == ">=0"

    assert c.DEPTH_ZERO_AMOUNT_ALLOWED is True
    assert (
        c.DEPTH_ZERO_AMOUNT_MEANING
        == "LEVEL_DELETE_OR_REMOVE"
    )


def test_side_domains_are_frozen() -> None:
    assert c.ALLOWED_SIDES["trades"] == {
        "buy",
        "sell",
    }

    assert (
        c.ALLOWED_SIDES["incremental_book_L2"]
        == {
            "bid",
            "ask",
        }
    )


def test_temporal_contract_is_frozen() -> None:
    assert c.REQUIRE_INTEGER_TIMESTAMPS is True
    assert c.REQUIRE_POSITIVE_TIMESTAMPS is True

    assert c.REQUIRE_LOCAL_GTE_EXCHANGE is True

    assert (
        c.REQUIRE_LOCAL_TIMESTAMP_NONDECREASING
        is True
    )

    assert (
        c.REQUIRE_EXCHANGE_TIMESTAMP_NONDECREASING
        is False
    )

    assert c.REQUIRE_EXCHANGE_UTC_DAY_MATCH is True


def test_depth_snapshot_contract_is_frozen() -> None:
    assert c.DEPTH_SNAPSHOT_DOMAIN == {
        "true",
        "false",
    }

    assert c.REQUIRE_DEPTH_SNAPSHOT_BOOLEAN is True

    assert (
        c.REQUIRE_DEPTH_AT_LEAST_ONE_SNAPSHOT_PER_FILE
        is True
    )


def test_structural_contract_is_frozen() -> None:
    assert c.REQUIRE_NONEMPTY_FILE is True
    assert c.REQUIRE_EXACT_HEADER is True
    assert c.REQUIRE_EXACT_FIELD_COUNT is True
    assert c.REQUIRE_GZIP_READ_TO_EOF is True
    assert c.REQUIRE_NO_SYMLINK is True

    assert c.REQUIRE_D4_BYTE_SIZE_IDENTITY is True
    assert c.REQUIRE_D4_SHA256_IDENTITY is True


def test_non_gates_are_explicit() -> None:
    assert c.REQUIRE_TRADE_ID_UNIQUENESS is False
    assert c.REQUIRE_ROW_UNIQUENESS is False

    assert (
        c.REQUIRE_EXCHANGE_TIMESTAMP_MONOTONICITY
        is False
    )

    assert "economic_performance" in c.NON_GATES
    assert "policy_pnl" in c.NON_GATES


def test_scope_containment_is_frozen() -> None:
    assert (
        c.FULL_SCAN_MAY_OPEN_ONLY_FROZEN_D4_STREAMS
        is True
    )

    assert c.AUG01_ALLOWED is False
    assert c.SEP_PLUS_ALLOWED is False
    assert c.NON_BTC_ALLOWED is False

    assert (
        c.NETWORK_MARKET_DATA_ACQUISITION_ALLOWED
        is False
    )

    assert c.TARDIS_CONVERTER_ALLOWED is False
    assert c.HFTBACKTEST_ALLOWED is False

    assert (
        c.HISTORICAL_POLICY_REPLAY_ALLOWED
        is False
    )

    assert c.HISTORICAL_PNL_ALLOWED is False
    assert c.ECONOMIC_ARENA_ALLOWED is False
    assert c.CANONICAL_PNL_WRITE_ALLOWED is False

    assert c.RAILWAY_ALLOWED is False
    assert c.LIVE_TRADING_ALLOWED is False


def test_d5a_observation_cannot_become_gate() -> None:
    assert c.D5A_SAMPLE_ROWS_PER_FILE == 256

    assert (
        c.D5A_DEPTH_ZERO_AMOUNT_ROWS_OBSERVED
        == 114
    )

    assert (
        c.D5A_ZERO_AMOUNT_COUNT_IS_ACCEPTANCE_THRESHOLD
        is False
    )

    assert (
        c.D5A_ZERO_AMOUNT_COUNT_IS_EXPECTED_FULL_COUNT
        is False
    )

from __future__ import annotations

from pathlib import Path

from multimarket import dev045_d6r4_full_day_contract as c


def test_parent_and_prerequisites() -> None:
    assert (
        c.PARENT_HEAD
        == "b67b18bedece7a0fb07cb9a42d0809f6c3778692"
    )

    assert c.D6R3B_REQUIRED_STATUS == "PASS"
    assert c.D6R2B_REQUIRED_STATUS == "PASS"
    assert c.D6R2B_EXACT_PARITY_REQUIRED is True


def test_exact_raw_identity() -> None:
    assert c.DAY == "2026-01-01"
    assert c.SYMBOL == "BTCUSDT"
    assert c.EXCHANGE == "binance-futures"

    assert c.TRADE_RAW_BYTES == 9_691_108

    assert (
        c.TRADE_RAW_SHA256
        == "e4aaee2b9f85016a5198e0cace5755db"
        "d789c0f6f47ac0fc802c8f4b533833f6"
    )

    assert c.DEPTH_RAW_BYTES == 347_513_061

    assert (
        c.DEPTH_RAW_SHA256
        == "0488a2204c9070b1e6a8769af48d54fb"
        "36e6a5658613267e2615cd3228002ded"
    )

    assert c.RAW_SHA256_PRECHECK_REQUIRED is True
    assert c.RAW_SIZE_PRECHECK_REQUIRED is True


def test_expected_conversion_geometry() -> None:
    assert c.PRODUCTION_CHUNK_ROWS == 500_000

    assert c.EXPECTED_TRADE_ROWS == 1_056_983
    assert c.EXPECTED_DEPTH_ROWS == 62_609_291

    assert c.EXPECTED_DEPTH_SNAPSHOT_BATCHES == 1

    assert c.EXPECTED_BASE_EVENT_ROWS == 63_666_276

    assert c.EXPECTED_TEMPORARY_SORT_RUNS == 256


def test_resource_recheck() -> None:
    assert c.RESOURCE_RECHECK_REQUIRED is True

    assert c.RESOURCE_RECHECK_BEFORE_RAW_OPEN is True

    assert (
        c.REQUIRED_AVAILABLE_MEMORY_BYTES
        == 1_805_762_560
    )

    assert (
        c.REQUIRED_SCRATCH_FREE_BYTES
        == 24_447_849_984
    )

    assert c.REQUIRED_NOFILE_SOFT == 320

    assert c.SWAP_COUNTS_AS_AVAILABLE_MEMORY is False


def test_runtime_is_on_frozen_filesystem() -> None:
    root = Path(c.PROBED_FILESYSTEM_ROOT)
    runtime = Path(c.RUNTIME_ROOT)
    scratch = Path(c.SCRATCH_ROOT)
    output_root = Path(c.OUTPUT_ROOT)
    output = Path(c.OUTPUT_PATH)

    assert c.PROBED_FILESYSTEM_DEVICE_ID == 2096

    assert runtime.is_relative_to(root)
    assert scratch.is_relative_to(root)
    assert output_root.is_relative_to(root)
    assert output.is_relative_to(root)

    assert (
        c.SCRATCH_DEVICE_MUST_EQUAL_PROBED_DEVICE
        is True
    )

    assert (
        c.OUTPUT_DEVICE_MUST_EQUAL_PROBED_DEVICE
        is True
    )

    assert (
        c.SCRATCH_AND_OUTPUT_DEVICE_MUST_MATCH
        is True
    )


def test_output_cleanliness_and_retention() -> None:
    assert (
        c.OUTPUT_MUST_NOT_EXIST_BEFORE_CANONICAL_RUN
        is True
    )

    assert (
        c.SCRATCH_ROOT_MUST_BE_EMPTY_BEFORE_CANONICAL_RUN
        is True
    )

    assert c.OUTPUT_RETAINED_AFTER_PASS is True
    assert c.OUTPUT_COMMITTED_TO_GIT is False


def test_one_shot_boundary() -> None:
    assert c.CANONICAL_FULL_DAY_ATTEMPTS == 1

    assert (
        c.CANONICAL_ATTEMPT_STARTS_AT_CONVERTER_INVOCATION
        is True
    )

    assert (
        c.FIRST_CONVERTER_RESULT_FROZEN_PASS_OR_FAIL
        is True
    )

    assert c.CANONICAL_RERUN_ALLOWED is False


def test_output_requirements() -> None:
    assert c.EXPECTED_OUTPUT_ITEMSIZE == 64

    assert (
        c.OUTPUT_MUST_BE_NUMPY_MEMMAP_COMPATIBLE
        is True
    )

    assert c.OUTPUT_MUST_HAVE_NO_SOURCE_SEQ is True

    assert (
        c.CONVERTER_RETURN_IMPLIES_INTERNAL_M4_VALIDATION_PASS
        is True
    )


def test_cpu_not_artificially_capped() -> None:
    assert c.CPU_CAP_ALLOWED is False

    assert c.USE_AVAILABLE_MACHINE_CPU_CAPACITY is True


def test_d6r4a_itself_does_not_execute() -> None:
    assert (
        c.RAW_CONTENT_OPEN_AUTHORIZED_BY_D6R4A
        is False
    )

    assert (
        c.FULL_DAY_CONVERSION_AUTHORIZED_BY_D6R4A
        is False
    )

    assert (
        c.FULL_DAY_EXECUTION_REQUIRES_D6R4A_CI_GREEN
        is True
    )


def test_economic_surfaces_remain_closed() -> None:
    assert c.POLICY_EXECUTION_ALLOWED is False
    assert c.M01_M08_EXECUTION_ALLOWED is False

    assert c.HISTORICAL_POLICY_REPLAY_ALLOWED is False
    assert c.HISTORICAL_PNL_ALLOWED is False

    assert c.ECONOMIC_ARENA_ALLOWED is False
    assert c.CANONICAL_PNL_WRITE_ALLOWED is False

    assert c.OTHER_DAYS_ALLOWED is False
    assert c.AUG01_ALLOWED is False
    assert c.SEP_PLUS_ALLOWED is False
    assert c.NON_BTC_ALLOWED is False

    assert c.NETWORK_MARKET_DATA_ACQUISITION_ALLOWED is False

    assert c.RAILWAY_ALLOWED is False
    assert c.LIVE_TRADING_ALLOWED is False

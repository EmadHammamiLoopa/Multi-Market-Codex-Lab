from __future__ import annotations

from multimarket import dev045_d6r3_resource_contract as c


def test_real_parity_prerequisite() -> None:
    assert (
        c.PARENT_HEAD
        == "4ff70ec50e39da432a70bf0444907f536586ed3e"
    )

    assert c.D6R2B_STATUS == "PASS"
    assert c.D6R2B_CANONICAL_ATTEMPT == 1
    assert c.D6R2B_EXACT_PARITY_PASS is True

    assert (
        c.BOUNDED_REAL_SLICE_PEAK_RSS_BYTES
        == 451_440_640
    )


def test_full_day_geometry() -> None:
    assert c.FULL_DAY == "2026-01-01"
    assert c.FULL_DAY_SYMBOL == "BTCUSDT"

    assert c.FULL_DAY_TRADE_ROWS == 1_056_983
    assert c.FULL_DAY_DEPTH_ROWS == 62_609_291

    assert (
        c.FULL_DAY_DEPTH_SNAPSHOT_BATCHES
        == 1
    )

    assert c.FULL_DAY_BASE_EVENT_ROWS == 63_666_276

    assert (
        c.FULL_DAY_BASE_EVENT_BUFFER_BYTES
        == 4_074_641_664
    )


def test_memory_gate_is_frozen() -> None:
    assert c.MEMORY_SAFETY_MULTIPLIER == 4

    assert (
        c.REQUIRED_AVAILABLE_MEMORY_BYTES
        == 1_805_762_560
    )

    assert c.MEMORY_PROBE_FIELD == "MemAvailable"

    assert c.SWAP_COUNTS_AS_AVAILABLE_MEMORY is False


def test_disk_gate_is_frozen() -> None:
    assert c.SCRATCH_SAFETY_MULTIPLIER == 6

    assert (
        c.REQUIRED_SCRATCH_FREE_BYTES
        == 24_447_849_984
    )

    assert (
        c.SCRATCH_FILESYSTEM_PROBE_PATH
        == "/home/emadh/Multi-Market"
    )

    assert (
        c.FULL_DAY_SCRATCH_MUST_USE_PROBED_FILESYSTEM
        is True
    )

    assert (
        c.FULL_DAY_OUTPUT_MUST_USE_PROBED_FILESYSTEM
        is True
    )


def test_run_and_fd_geometry() -> None:
    assert c.PRODUCTION_CHUNK_ROWS == 500_000

    assert c.EXPECTED_RUN_PAIRS == 128
    assert c.EXPECTED_TEMPORARY_SORT_RUNS == 256

    assert c.FILE_DESCRIPTOR_HEADROOM == 64
    assert c.REQUIRED_NOFILE_SOFT == 320


def test_all_three_gates_required() -> None:
    assert c.REQUIRED_GATES == (
        "MEMORY",
        "SCRATCH_DISK",
        "NOFILE",
    )

    assert c.ALL_REQUIRED_GATES_MUST_PASS is True


def test_cpu_not_capped_or_gating() -> None:
    assert c.CPU_CAP_ALLOWED is False
    assert c.USE_AVAILABLE_MACHINE_CPU_CAPACITY is True

    assert c.RECORD_CPU_COUNT is True
    assert c.RECORD_CPU_AFFINITY_COUNT is True


def test_resource_preflight_has_no_market_execution() -> None:
    assert c.RESOURCE_PREFLIGHT_CANONICAL_ATTEMPTS == 1

    assert c.RESOURCE_PREFLIGHT_OPENS_RAW_DATA is False
    assert c.RESOURCE_PREFLIGHT_RUNS_CONVERTER is False

    assert c.RESOURCE_PREFLIGHT_RUNS_POLICY is False
    assert c.RESOURCE_PREFLIGHT_COMPUTES_PNL is False


def test_full_day_remains_closed() -> None:
    assert c.FULL_DAY_CONVERSION_AUTHORIZED_NOW is False

    assert (
        c.RESOURCE_PASS_NEXT_GATE
        == "FREEZE_JAN01_FULL_DAY_BOUNDED_CONVERSION_CONTRACT"
    )


def test_all_sensitive_surfaces_closed() -> None:
    assert c.RAW_CONTENT_OPEN_ALLOWED is False
    assert c.FULL_DAY_CONVERTER_RUN_ALLOWED is False

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

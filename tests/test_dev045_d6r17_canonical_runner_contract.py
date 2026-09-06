from __future__ import annotations

from multimarket import (
    dev045_d6r17_canonical_runner_contract as c,
)


def test_contract_validates():
    c.validate_contract()


def test_exact_multiplicity():
    assert len(c.DAY_ORDER) == 7
    assert len(c.POLICY_ORDER) == 8
    assert len(c.SCENARIO_ORDER) == 2

    assert (
        c.EXPECTED_REPLAYS_PER_DAY
        == 16
    )

    assert (
        c.EXPECTED_TOTAL_REPLAYS
        == 112
    )

    assert len(c.REPLAY_ORDER) == 112

    for day in c.DAY_ORDER:
        rows = c.expected_day_replays(
            day
        )

        assert len(rows) == 16

        assert tuple(
            x[1:]
            for x in rows
        ) == tuple(
            (
                policy,
                scenario,
            )
            for policy in c.POLICY_ORDER
            for scenario in c.SCENARIO_ORDER
        )


def test_support_calendar():
    for day in (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
    ):
        assert (
            c.expected_support_keys(day)
            == ()
        )

    for day in (
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    ):
        assert (
            c.expected_support_keys(day)
            == ("M06", "M07")
        )


def test_source_lifecycle():
    assert c.OPEN_SOURCE_ONCE_PER_DAY
    assert c.KEEP_SOURCE_OPEN_FOR_ALL_16_REPLAYS
    assert c.CLOSE_SOURCE_AFTER_ALL_16_REPLAYS

    assert c.SOURCE_OPEN_COUNT_PER_DAY == 1
    assert c.SOURCE_CLOSE_COUNT_PER_DAY == 1

    assert c.FULL_SHA256_BEFORE_MEMMAP_REQUIRED
    assert c.SOURCE_READ_ONLY_REQUIRED


def test_raw_fill_capture_and_reaccounting():
    assert c.RAW_FILL_CAPTURE_REQUIRED

    assert (
        c.RAW_FILL_CAPTURE_SOURCE
        == "DirectActionContinuousHistoricalPolicyKernel.bound_fills"
    )

    assert c.CAPTURE_BEFORE_BACKTEST_CLOSE

    assert (
        c.RAW_FILL_COUNT_MUST_EQUAL_REPLAY_TOTAL_FILL_COUNT
    )

    assert c.REACCOUNT_PARITY_REQUIRED

    assert (
        c.REACCOUNT_FUNCTION
        == "dev045_m6_economic_arena.account_fill_bucket"
    )

    assert (
        c.REACCOUNT_CYCLES_MUST_EQUAL_REPLAY_CYCLES
    )

    assert (
        c.M6_FINAL_ENTRYPOINT
        == "dev045_m6_economic_arena.run_economic_arena"
    )

    assert c.M6_FINAL_CALL_ONLY_AFTER_112


def test_attempt_semantics():
    assert c.STOP_ON_EXECUTION_INTEGRITY_FAILURE
    assert c.STOP_ON_ECONOMIC_NONPASS is False

    assert c.FIRST_HISTORICAL_OUTPUT_IS_EVIDENCE
    assert c.ATTEMPT_CONSUMED_AFTER_FIRST_HISTORICAL_OUTPUT

    assert c.AUTOMATIC_RETRY is False
    assert c.RERUN_AFTER_ATTEMPT_CONSUMPTION is False

    assert c.TUNING_AFTER_FIRST_OUTPUT is False

    assert c.PER_DAY_EVIDENCE_REQUIRED
    assert c.PER_DAY_RANKING_FORBIDDEN

    assert c.FINAL_ARENA_REQUIRES_ALL_DAYS_COMPLETE


def test_all_execution_surfaces_closed():
    assert c.CANONICAL_SOURCE_OPEN_ENABLED is False
    assert c.CANONICAL_SOURCE_HASH_ENABLED is False

    assert c.HFTBACKTEST_EXECUTION_ENABLED is False
    assert c.POLICY_EXECUTION_ENABLED is False
    assert c.HISTORICAL_PNL_ENABLED is False

    assert (
        c.ECONOMIC_ARENA_EXECUTION_ENABLED
        is False
    )

    assert c.CANONICAL_RESULT_WRITE_ENABLED is False

    assert c.NETWORK_ACQUISITION_ENABLED is False
    assert c.RAILWAY_ENABLED is False
    assert c.LIVE_TRADING_AUTHORIZED is False

    assert c.AUG_OPEN_AUTHORIZED is False
    assert c.SEP_PLUS_OPEN_AUTHORIZED is False
    assert c.NON_BTC_OPEN_AUTHORIZED is False

    assert c.RUNNER_IMPLEMENTATION_AUTHORIZED is False
    assert c.CANONICAL_EXECUTION_AUTHORIZED is False


def test_no_support_reconstruction():
    assert c.EXACT_TIMESTAMP_ONLY

    assert (
        c.MISSING_EXACT_ROW_SEMANTIC
        == "FALLBACK_TO_M02"
    )

    assert (
        c.EXPLICIT_ZERO_SEMANTIC
        == "FROZEN_ABSTAIN"
    )

    assert c.PROBABILITY_FORWARD_FILL is False
    assert c.PROBABILITY_INTERPOLATION is False
    assert c.PROBABILITY_BACKFILL is False
    assert c.PROBABILITY_RECONSTRUCTION is False

    assert c.LEGACY_STATE_REMATERIALIZATION is False
    assert c.A0_REFIT is False
    assert c.A0_RETRAIN is False

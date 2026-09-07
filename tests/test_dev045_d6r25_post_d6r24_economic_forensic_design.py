from __future__ import annotations

from pathlib import Path

from multimarket import dev045_d6r25_post_d6r24_economic_forensic_design as d


def test_exact_frozen_parent_and_result_identity():
    assert d.EXPERIMENT_ID == "DEV045-D6R25"
    assert d.PARENT_D6R24_FREEZE_HEAD == (
        "06eff337e4a039cf47c8b10a41aa91e52df4c792"
    )
    assert d.D6R24_EXECUTION_HEAD == (
        "b04a18f8eb5b4689abd15d7cdf6a6c889ee36212"
    )
    assert d.D6R24_RESULT_SHA256 == (
        "fafae1e2d98a6f5ad63188f69b61b5d42b53ca2e86a7032971378d7f82e31316"
    )
    assert d.D6R24_RESULT_BYTES == 22165
    assert d.D6R24_CLASSIFICATION == (
        "ENGINEERING_CANONICAL_PASS_ECONOMIC_FALSIFICATION_FAIL_ALL_POLICIES"
    )


def test_exact_matrix_and_frozen_fees():
    assert len(d.DAY_ORDER) == 7
    assert len(d.POLICY_ORDER) == 8
    assert len(d.SCENARIO_ORDER) == 2
    assert d.PRIMARY_MAKER_RATE == 0.0002
    assert d.PRIMARY_TAKER_RATE == 0.0005
    assert d.STRESS_MAKER_RATE == 0.0003
    assert d.STRESS_TAKER_RATE == 0.00075


def test_forensic_is_artifact_only_and_bounded_memory():
    assert d.INPUT_SURFACE == "FROZEN_D6R24_DAY_ARTIFACTS_ONLY"
    assert d.ONE_DAY_AT_A_TIME is True
    assert d.MAX_FROZEN_DAY_ARTIFACT_BYTES == 160_744_910


def test_no_execution_or_rerun_authorization():
    assert d.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert d.HISTORICAL_SOURCE_HASH_AUTHORIZED is False
    assert d.SIMULATOR_AUTHORIZED is False
    assert d.D6R24_RERUN_AUTHORIZED is False
    assert d.D6R23_Q1_RERUN_AUTHORIZED is False
    assert d.D6R22_RERUN_AUTHORIZED is False
    assert d.D6R21_RERUN_AUTHORIZED is False
    assert d.Q8_RERUN_AUTHORIZED is False
    assert d.ECONOMIC_ARENA_RERUN_AUTHORIZED is False
    assert d.FEE_CHANGE_AUTHORIZED is False
    assert d.POLICY_RETUNING_AUTHORIZED is False
    assert d.POLICY_PROMOTION_AUTHORIZED is False
    assert d.LIVE_TRADING_AUTHORIZED is False
    assert d.AUG_OPEN_AUTHORIZED is False
    assert d.SEP_PLUS_OPEN_AUTHORIZED is False
    assert d.NON_BTC_OPEN_AUTHORIZED is False


def test_implementation_does_not_consume_day_artifacts():
    assert d.DESIGN_EXECUTED_DURING_IMPLEMENTATION is False
    assert d.D6R24_DAY_ARTIFACTS_OPENED_DURING_IMPLEMENTATION is False
    assert d.D6R24_DAY_ARTIFACTS_HASHED_DURING_IMPLEMENTATION is False


def test_gross_fee_net_and_break_even_are_preregistered():
    required = {
        "gross_expectancy_bps_cycle_mean",
        "fee_drag_bps_cycle_mean",
        "net_expectancy_bps_cycle_mean",
        "gross_fee_net_parity",
        "maker_notional_share",
        "taker_notional_share",
        "maker_fee_component",
        "taker_fee_component",
        "uniform_fee_multiplier_break_even",
        "zero_fee_expectancy_bps",
        "primary_minus_stress_gross_expectancy_bps",
    }
    assert required.issubset(set(d.AUTHORIZED_DIAGNOSTICS))
    assert d.BREAK_EVEN_CLASSIFICATION["gross_expectancy_le_zero"] == (
        "NO_NONNEGATIVE_FEE_MULTIPLIER_CAN_RESCUE_EXPECTANCY"
    )


def test_unsupported_attributions_fail_closed():
    assert set(d.UNSUPPORTED_ATTRIBUTIONS) == {
        "forced_flatten_pnl_attribution",
        "forced_flatten_fee_attribution",
        "adverse_selection_markout",
        "spread_capture_vs_price_move_decomposition",
        "queue_position_edge_attribution",
    }
    assert set(d.UNSUPPORTED_ATTRIBUTIONS) == set(d.UNSUPPORTED_REASON)
    assert "order_id" in d.UNSUPPORTED_REASON["forced_flatten_pnl_attribution"]
    assert "markout" in d.UNSUPPORTED_REASON["adverse_selection_markout"]


def test_no_hidden_execution_calls_in_design_module():
    source = Path(d.__file__).read_text(encoding="utf-8")
    assert "run_full_canonical_arena(" not in source
    assert "run_economic_arena(" not in source
    assert "run_full_day(" not in source
    assert "_open_verified_file(" not in source


def test_design_contract_green():
    d.validate_design_contract()

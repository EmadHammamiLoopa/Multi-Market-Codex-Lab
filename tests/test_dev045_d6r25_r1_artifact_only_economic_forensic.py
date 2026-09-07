from __future__ import annotations

from pathlib import Path

import pytest

from multimarket import dev045_d6r25_r1_artifact_only_economic_forensic as r


def _cycle(**overrides):
    base = {
        "policy_id": "M01",
        "day": "2026-01-01",
        "start_timestamp_ns": 1_767_225_600_000_000_000,
        "end_timestamp_ns": 1_767_225_602_000_000_000,
        "cash_pnl_before_fees": 1.0,
        "fees": 0.4,
        "net_pnl": 0.6,
        "entry_notional": 1000.0,
        "net_bps": 6.0,
        "maker_notional": 2000.0,
        "taker_notional": 0.0,
        "fill_count": 2,
    }
    base.update(overrides)
    return base


def test_identity_and_forbidden_surface():
    assert r.EXPERIMENT_ID == "DEV045-D6R25-R1"
    assert r.PARENT_DESIGN_HEAD == "da088950d8602cd6bec681d127050e636d00b2d9"
    assert r.PARENT_D6R24_FREEZE_HEAD == "06eff337e4a039cf47c8b10a41aa91e52df4c792"
    assert r.AUTHORIZED_BY_DEFAULT is False
    assert r.AUTOMATIC_RETRY is False
    assert r.HISTORICAL_SOURCE_OPEN_AUTHORIZED is False
    assert r.SIMULATOR_AUTHORIZED is False
    assert r.ECONOMIC_ARENA_RERUN_AUTHORIZED is False
    assert r.D6R24_RERUN_AUTHORIZED is False
    assert r.FEE_CHANGE_AUTHORIZED is False
    assert r.POLICY_RETUNING_AUTHORIZED is False
    assert r.LIVE_TRADING_AUTHORIZED is False


def test_frozen_buckets_are_exact():
    assert r.MAKER_SHARE_BUCKETS == (
        "PURE_MAKER_100",
        "MAKER_90_TO_LT100",
        "MAKER_50_TO_LT90",
        "MAKER_LT50",
    )
    assert r.FILL_COUNT_BUCKETS == ("FILL_2", "FILL_3_TO_4", "FILL_5_TO_8", "FILL_9_PLUS")
    assert r.HOLDING_TIME_BUCKETS == (
        "HOLD_LE_1S",
        "HOLD_GT1_TO_5S",
        "HOLD_GT5_TO_30S",
        "HOLD_GT30S",
    )


def test_bucket_helpers():
    assert r._maker_share_bucket(100.0, 0.0) == "PURE_MAKER_100"
    assert r._maker_share_bucket(95.0, 5.0) == "MAKER_90_TO_LT100"
    assert r._maker_share_bucket(70.0, 30.0) == "MAKER_50_TO_LT90"
    assert r._maker_share_bucket(40.0, 60.0) == "MAKER_LT50"
    assert r._fill_count_bucket(2) == "FILL_2"
    assert r._fill_count_bucket(4) == "FILL_3_TO_4"
    assert r._fill_count_bucket(8) == "FILL_5_TO_8"
    assert r._fill_count_bucket(9) == "FILL_9_PLUS"
    assert r._holding_bucket(1_000_000_000) == "HOLD_LE_1S"
    assert r._holding_bucket(5_000_000_000) == "HOLD_GT1_TO_5S"
    assert r._holding_bucket(30_000_000_000) == "HOLD_GT5_TO_30S"
    assert r._holding_bucket(30_000_000_001) == "HOLD_GT30S"


def test_support_regime_is_only_m06_m07_apr_jul():
    assert r._support_regime(day="2026-03-01", policy_id="M06") == "NO_DIRECT_SUPPORT"
    assert r._support_regime(day="2026-04-01", policy_id="M06") == "DIRECT_SUPPORT_ACTIVE"
    assert r._support_regime(day="2026-07-01", policy_id="M07") == "DIRECT_SUPPORT_ACTIVE"
    assert r._support_regime(day="2026-07-01", policy_id="M08") == "NO_DIRECT_SUPPORT"


def test_cycle_decomposition_and_break_even():
    acc = r._new_acc()
    r._add_cycle(acc, _cycle(), scenario=r.PRIMARY)
    out = r._finalize(acc)
    assert out["cycle_count"] == 1
    assert out["gross_expectancy_bps_cycle_mean"] == pytest.approx(10.0)
    assert out["fee_drag_bps_cycle_mean"] == pytest.approx(4.0)
    assert out["net_expectancy_bps_cycle_mean"] == pytest.approx(6.0)
    assert out["uniform_fee_multiplier_break_even"] == 1.0
    assert out["break_even_classification"] == "ALREADY_NONNEGATIVE_NET"


def test_negative_gross_is_not_fee_rescuable():
    acc = r._new_acc()
    c = _cycle(cash_pnl_before_fees=-0.2, fees=0.4, net_pnl=-0.6)
    r._add_cycle(acc, c, scenario=r.PRIMARY)
    out = r._finalize(acc)
    assert out["gross_expectancy_bps_cycle_mean"] < 0
    assert out["uniform_fee_multiplier_break_even"] is None
    assert out["break_even_classification"] == "NO_NONNEGATIVE_FEE_MULTIPLIER_CAN_RESCUE_EXPECTANCY"


def test_positive_gross_fee_dominated_break_even():
    acc = r._new_acc()
    c = _cycle(cash_pnl_before_fees=0.2, fees=0.4, net_pnl=-0.2)
    r._add_cycle(acc, c, scenario=r.PRIMARY)
    out = r._finalize(acc)
    assert out["gross_expectancy_bps_cycle_mean"] == pytest.approx(2.0)
    assert out["fee_drag_bps_cycle_mean"] == pytest.approx(4.0)
    assert out["uniform_fee_multiplier_break_even"] == pytest.approx(0.5)
    assert out["break_even_classification"] == "POSITIVE_GROSS_EDGE_OVERWHELMED_BY_FEES"


def test_fee_component_mismatch_fails_closed():
    acc = r._new_acc()
    c = _cycle(fees=0.5, net_pnl=0.5)
    with pytest.raises(r.D6R25ForensicError, match="fee_component_parity"):
        r._add_cycle(acc, c, scenario=r.PRIMARY)


def test_unsupported_attributions_are_explicitly_not_identifiable():
    assert r.UNSUPPORTED
    assert set(r.UNSUPPORTED.values()) == {"NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACT"}
    assert "forced_flatten_pnl_attribution" in r.UNSUPPORTED
    assert "adverse_selection_markout" in r.UNSUPPORTED


def test_execution_closed_without_environment(monkeypatch):
    monkeypatch.delenv(r.AUTHORIZATION_ENV, raising=False)
    with pytest.raises(r.D6R25ForensicError, match="execution_gate_closed"):
        r._require_authorization(token=r.AUTHORIZATION_TOKEN, gate=False)
    with pytest.raises(r.D6R25ForensicError, match="authorization_environment"):
        r._require_authorization(token=r.AUTHORIZATION_TOKEN, gate=True)


def test_no_replay_or_arena_entrypoints_in_source():
    source = Path(r.__file__).read_text(encoding="utf-8")
    assert "hftbacktest" not in source
    assert "run_economic_arena(" not in source
    assert "run_full_canonical_arena(" not in source
    assert "run_target_qualification(" not in source
    assert "market_depth" not in source.lower()


def test_frozen_lineage_and_contract_are_green():
    r.validate_execution_contract()

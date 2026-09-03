from multimarket import dev045_m5_fee_amendment as a
from multimarket import dev045_m5_prereg as m5


def test_public_primary_fee_schedule_is_exact_and_conservative_no_discount():
    a.validate_amendment()
    f = a.primary_fee_schedule()
    assert f.maker_rate == 0.0002
    assert f.taker_rate == 0.0005
    assert f.verified_public_schedule is True
    assert "REGULAR_USER_USDT_M_NO_BNB_DISCOUNT" in f.basis


def test_adverse_fee_stress_is_frozen_before_economics():
    f = a.stress_fee_schedule()
    assert f.maker_rate == 0.0003
    assert f.taker_rate == 0.00075
    assert abs(f.maker_rate / a.PRIMARY_MAKER_RATE - 1.5) < 1e-12
    assert abs(f.taker_rate / a.PRIMARY_TAKER_RATE - 1.5) < 1e-12


def test_original_m5_family_and_core_prereg_remain_unchanged():
    m5.validate_family()
    assert m5.AUTHORIZED_DAYS == (
        "2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01",
        "2026-05-01", "2026-06-01", "2026-07-01",
    )
    assert m5.PRIMARY_QUEUE_MODEL == "RISK_ADVERSE"
    assert m5.DIAGNOSTIC_QUEUE_MODEL == "LOG_PROB"
    assert m5.PRIMARY_ENTRY_LATENCY_MS == 250
    assert m5.PRIMARY_RESPONSE_LATENCY_MS == 250
    assert m5.STRESS_ENTRY_LATENCY_MS == 500
    assert m5.STRESS_RESPONSE_LATENCY_MS == 500
    assert m5.BOOTSTRAP_REPS == 20_000
    assert m5.BOOTSTRAP_SEED == 450045
    assert m5.FAMILY_ALPHA == 0.05


def test_historical_authorized_but_live_forbidden():
    assert a.M6_HISTORICAL_ECONOMICS_AUTHORIZED is True
    assert a.LIVE_TRADING_AUTHORIZED is False

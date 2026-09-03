from __future__ import annotations

import json
import pytest

from tools import dev045_m5_binance_fee_probe as p


def test_signature_is_deterministic_and_matches_known_vector():
    query, sig = p.sign_query(
        "test-secret",
        {
            "symbol": "BTCUSDT",
            "timestamp": 1700000000000,
            "recvWindow": 5000,
        },
    )
    assert query == "symbol=BTCUSDT&timestamp=1700000000000&recvWindow=5000"
    assert sig == "c201372a9a7f79a53a289fccae4136f400d519701924c18cb6c5ecc7e2c4e6c6"


def test_parse_personal_commission_response():
    e = p.parse_commission_response(
        {
            "symbol": "BTCUSDT",
            "makerCommissionRate": "0.000200",
            "takerCommissionRate": "0.000500",
            "rpiCommissionRate": "0.000050",
        },
        "BTCUSDT",
        1700000000000,
    )
    assert e.maker_rate == pytest.approx(0.0002)
    assert e.taker_rate == pytest.approx(0.0005)
    assert e.rpi_rate == pytest.approx(0.00005)
    assert not e.trade_test_attempted


def test_parse_rejects_symbol_mismatch_and_absurd_rates():
    with pytest.raises(p.BinanceFeeProbeError, match="symbol_mismatch"):
        p.parse_commission_response(
            {
                "symbol": "ETHUSDT",
                "makerCommissionRate": "0.0002",
                "takerCommissionRate": "0.0005",
            },
            "BTCUSDT",
            1,
        )
    with pytest.raises(p.BinanceFeeProbeError, match="out_of_range"):
        p.parse_commission_response(
            {
                "symbol": "BTCUSDT",
                "makerCommissionRate": "0.2",
                "takerCommissionRate": "0.0005",
            },
            "BTCUSDT",
            1,
        )


def test_evidence_never_contains_credentials_or_authorizes_m6():
    e = p.CommissionEvidence(
        symbol="BTCUSDT",
        maker_rate=0.0002,
        taker_rate=0.0005,
        rpi_rate=None,
        server_time_ms=1700000000000,
        trade_test_attempted=True,
        trade_test_passed=True,
        trade_test_error_code=None,
        trade_test_error_message=None,
    )
    out = p.evidence_json(e, base_url=p.PROD_BASE_URL)
    encoded = json.dumps(out).lower()
    assert "api_secret" not in encoded
    assert "api_key" not in encoded or out["api_key_or_secret_emitted"] is False
    assert out["credentials_persisted"] is False
    assert out["primary_fee_schedule_frozen"] is False
    assert out["m6_authorized"] is False


def test_trade_test_failure_preserves_exchange_error(monkeypatch):
    monkeypatch.setattr(p, "market_min_qty", lambda base_url, symbol: "0.001")
    monkeypatch.setattr(p, "server_time_ms", lambda base_url: 1700000000000)

    def boom(*args, **kwargs):
        raise p.BinanceFeeProbeError("binance_http_error:400:-2015:Invalid API-key, IP, or permissions for action")

    monkeypatch.setattr(p, "signed_request", boom)
    passed, code, msg = p.test_trade_permission(
        base_url=p.PROD_BASE_URL,
        symbol="BTCUSDT",
        api_key="x",
        api_secret="y",
    )
    assert not passed
    assert code == -2015
    assert "permissions" in msg

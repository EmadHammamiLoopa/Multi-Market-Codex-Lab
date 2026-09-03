#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import getpass
import hashlib
import hmac
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

PROD_BASE_URL = "https://fapi.binance.com"
DEFAULT_SYMBOL = "BTCUSDT"
RECV_WINDOW_MS = 5000
COMMISSION_PATH = "/fapi/v1/commissionRate"
SERVER_TIME_PATH = "/fapi/v1/time"
EXCHANGE_INFO_PATH = "/fapi/v1/exchangeInfo"
TEST_ORDER_PATH = "/fapi/v1/order/test"


class BinanceFeeProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class CommissionEvidence:
    symbol: str
    maker_rate: float
    taker_rate: float
    rpi_rate: float | None
    server_time_ms: int
    trade_test_attempted: bool
    trade_test_passed: bool | None
    trade_test_error_code: int | None
    trade_test_error_message: str | None


def encode_query(params: Mapping[str, Any]) -> str:
    return urllib.parse.urlencode(list(params.items()))


def sign_query(secret: str, params: Mapping[str, Any]) -> tuple[str, str]:
    if not secret:
        raise BinanceFeeProbeError("empty_api_secret")
    query = encode_query(params)
    signature = hmac.new(
        secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return query, signature


def _request_json(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    body: bytes | None = None,
    timeout_s: float = 15.0,
) -> Any:
    req = urllib.request.Request(
        url,
        data=body,
        headers=dict(headers or {}),
        method=method.upper(),
    )
    try:
        with urllib.request.urlopen(req, timeout=float(timeout_s)) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"code": exc.code, "msg": raw[:500]}
        raise BinanceFeeProbeError(
            f"binance_http_error:{exc.code}:{payload.get('code')}:{payload.get('msg')}"
        ) from None
    except urllib.error.URLError as exc:
        raise BinanceFeeProbeError(f"binance_network_error:{exc.reason}") from None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise BinanceFeeProbeError("binance_non_json_response") from None


def server_time_ms(base_url: str) -> int:
    payload = _request_json("GET", base_url.rstrip("/") + SERVER_TIME_PATH)
    try:
        value = int(payload["serverTime"])
    except Exception:
        raise BinanceFeeProbeError("invalid_server_time_response") from None
    if value <= 0:
        raise BinanceFeeProbeError("invalid_server_time")
    return value


def signed_request(
    method: str,
    base_url: str,
    path: str,
    *,
    api_key: str,
    api_secret: str,
    params: Mapping[str, Any],
    server_ms: int,
) -> Any:
    if not api_key:
        raise BinanceFeeProbeError("empty_api_key")
    signed_params = dict(params)
    signed_params["timestamp"] = int(server_ms)
    signed_params["recvWindow"] = RECV_WINDOW_MS
    query, signature = sign_query(api_secret, signed_params)
    payload = f"{query}&signature={signature}"
    headers = {
        "X-MBX-APIKEY": api_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Multi-Market-Codex-Lab-DEV045-M5-Fee-Probe/1.0",
    }
    base = base_url.rstrip("/")
    if method.upper() == "GET":
        return _request_json("GET", f"{base}{path}?{payload}", headers=headers)
    if method.upper() == "POST":
        return _request_json(
            "POST", f"{base}{path}", headers=headers, body=payload.encode("utf-8")
        )
    raise BinanceFeeProbeError("unsupported_method")


def parse_commission_response(payload: Any, symbol: str, server_ms: int) -> CommissionEvidence:
    if not isinstance(payload, dict):
        raise BinanceFeeProbeError("commission_response_not_object")
    returned_symbol = str(payload.get("symbol", ""))
    if returned_symbol != symbol:
        raise BinanceFeeProbeError("commission_symbol_mismatch")
    try:
        maker = float(payload["makerCommissionRate"])
        taker = float(payload["takerCommissionRate"])
    except Exception:
        raise BinanceFeeProbeError("commission_rate_missing_or_invalid") from None
    rpi_raw = payload.get("rpiCommissionRate")
    rpi = None if rpi_raw is None else float(rpi_raw)
    for name, value in (("maker", maker), ("taker", taker)):
        if not math.isfinite(value) or value < -0.01 or value > 0.01:
            raise BinanceFeeProbeError(f"commission_rate_out_of_range:{name}")
    if rpi is not None and (not math.isfinite(rpi) or rpi < -0.01 or rpi > 0.01):
        raise BinanceFeeProbeError("commission_rate_out_of_range:rpi")
    return CommissionEvidence(
        symbol=symbol,
        maker_rate=maker,
        taker_rate=taker,
        rpi_rate=rpi,
        server_time_ms=int(server_ms),
        trade_test_attempted=False,
        trade_test_passed=None,
        trade_test_error_code=None,
        trade_test_error_message=None,
    )


def fetch_commission(
    *,
    base_url: str,
    symbol: str,
    api_key: str,
    api_secret: str,
) -> CommissionEvidence:
    server_ms = server_time_ms(base_url)
    payload = signed_request(
        "GET",
        base_url,
        COMMISSION_PATH,
        api_key=api_key,
        api_secret=api_secret,
        params={"symbol": symbol},
        server_ms=server_ms,
    )
    return parse_commission_response(payload, symbol, server_ms)


def market_min_qty(base_url: str, symbol: str) -> str:
    payload = _request_json("GET", base_url.rstrip("/") + EXCHANGE_INFO_PATH)
    if not isinstance(payload, dict):
        raise BinanceFeeProbeError("exchange_info_not_object")
    for item in payload.get("symbols", []):
        if item.get("symbol") != symbol:
            continue
        filters = {f.get("filterType"): f for f in item.get("filters", [])}
        f = filters.get("MARKET_LOT_SIZE") or filters.get("LOT_SIZE")
        if not f or "minQty" not in f:
            raise BinanceFeeProbeError("market_min_qty_missing")
        qty = str(f["minQty"])
        if float(qty) <= 0:
            raise BinanceFeeProbeError("market_min_qty_invalid")
        return qty
    raise BinanceFeeProbeError("symbol_missing_from_exchange_info")


def test_trade_permission(
    *,
    base_url: str,
    symbol: str,
    api_key: str,
    api_secret: str,
) -> tuple[bool, int | None, str | None]:
    """Validate the signed Futures TRADE endpoint without creating a real order.

    Binance USD-M POST /fapi/v1/order/test validates an order request but does
    not place it. A failure may still reflect account state (for example API
    permissions or regional/product eligibility), so callers must preserve the
    exact error instead of converting all failures into one interpretation.
    """
    qty = market_min_qty(base_url, symbol)
    server_ms = server_time_ms(base_url)
    try:
        signed_request(
            "POST",
            base_url,
            TEST_ORDER_PATH,
            api_key=api_key,
            api_secret=api_secret,
            params={
                "symbol": symbol,
                "side": "BUY",
                "type": "MARKET",
                "quantity": qty,
            },
            server_ms=server_ms,
        )
        return True, None, None
    except BinanceFeeProbeError as exc:
        text = str(exc)
        parts = text.split(":", 3)
        code = None
        msg = text
        if len(parts) == 4 and parts[0] == "binance_http_error":
            try:
                code = int(parts[2])
            except Exception:
                code = None
            msg = parts[3]
        return False, code, msg[:500]


def evidence_json(e: CommissionEvidence, *, base_url: str) -> dict[str, Any]:
    captured = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return {
        "schema": "DEV045_M5_PERSONAL_BINANCE_FUTURES_FEE_CAPTURE_V1",
        "status": "FEE_EVIDENCE_CAPTURED",
        "venue": "BINANCE_FUTURES",
        "product_scope": "USD_M_FUTURES",
        "symbol": e.symbol,
        "maker_rate": e.maker_rate,
        "taker_rate": e.taker_rate,
        "rpi_rate": e.rpi_rate,
        "rate_unit": "decimal_fraction",
        "evidence_source": "SIGNED_GET_/fapi/v1/commissionRate",
        "base_url": base_url,
        "server_time_ms": e.server_time_ms,
        "captured_at_utc": captured,
        "futures_user_data_access": True,
        "trade_test_attempted": e.trade_test_attempted,
        "trade_test_passed": e.trade_test_passed,
        "trade_test_error_code": e.trade_test_error_code,
        "trade_test_error_message": e.trade_test_error_message,
        "api_key_or_secret_emitted": False,
        "credentials_persisted": False,
        "primary_fee_schedule_frozen": False,
        "m6_authorized": False,
        "note": "Capture only. M6 remains blocked until this evidence is reviewed and frozen into the M5 fee-freeze contract.",
    }


def _credential(name: str, env_name: str) -> str:
    value = os.environ.get(env_name)
    if value:
        return value.strip()
    return getpass.getpass(f"{name} (hidden input): ").strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read personal Binance USD-M Futures commission rates without placing a real order."
    )
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL)
    parser.add_argument("--base-url", default=PROD_BASE_URL)
    parser.add_argument(
        "--check-trade-permission",
        action="store_true",
        help="Also call POST /fapi/v1/order/test. This validates the TRADE endpoint but never places an order.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional local JSON output path. Credentials are never written.",
    )
    args = parser.parse_args(argv)

    symbol = str(args.symbol).upper().strip()
    if not symbol or not symbol.isalnum():
        raise BinanceFeeProbeError("invalid_symbol")

    api_key = _credential("Binance API key", "BINANCE_API_KEY")
    api_secret = _credential("Binance API secret", "BINANCE_API_SECRET")
    if not api_key or not api_secret:
        raise BinanceFeeProbeError("credentials_missing")

    evidence = fetch_commission(
        base_url=args.base_url,
        symbol=symbol,
        api_key=api_key,
        api_secret=api_secret,
    )

    if args.check_trade_permission:
        passed, code, msg = test_trade_permission(
            base_url=args.base_url,
            symbol=symbol,
            api_key=api_key,
            api_secret=api_secret,
        )
        evidence = CommissionEvidence(
            symbol=evidence.symbol,
            maker_rate=evidence.maker_rate,
            taker_rate=evidence.taker_rate,
            rpi_rate=evidence.rpi_rate,
            server_time_ms=evidence.server_time_ms,
            trade_test_attempted=True,
            trade_test_passed=passed,
            trade_test_error_code=code,
            trade_test_error_message=msg,
        )

    out = evidence_json(evidence, base_url=args.base_url)
    rendered = json.dumps(out, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BinanceFeeProbeError as exc:
        print(json.dumps({"status": "FEE_PROBE_FAIL", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(2)

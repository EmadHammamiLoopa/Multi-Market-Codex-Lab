from __future__ import annotations

from dataclasses import dataclass

ORIGINAL_M5_IDENTITY = "cbffd48a9eea77a7ace843f9c830ac96bd39a071"
FEE_BASIS = "OFFICIAL_PUBLIC_REGULAR_USER_USDT_M_NO_BNB_DISCOUNT"
PRIMARY_MAKER_RATE = 0.0002
PRIMARY_TAKER_RATE = 0.0005
STRESS_MULTIPLIER = 1.5
STRESS_MAKER_RATE = 0.0003
STRESS_TAKER_RATE = 0.00075
OFFICIAL_EVIDENCE_URL = "https://www.binance.com/en-BH/fee/futureFee"
M6_HISTORICAL_ECONOMICS_AUTHORIZED = True
LIVE_TRADING_AUTHORIZED = False


class FeeAmendmentError(RuntimeError):
    pass


@dataclass(frozen=True)
class FrozenFeeSchedule:
    maker_rate: float
    taker_rate: float
    source: str
    basis: str
    verified_public_schedule: bool


def primary_fee_schedule() -> FrozenFeeSchedule:
    return FrozenFeeSchedule(
        maker_rate=PRIMARY_MAKER_RATE,
        taker_rate=PRIMARY_TAKER_RATE,
        source=OFFICIAL_EVIDENCE_URL,
        basis=FEE_BASIS,
        verified_public_schedule=True,
    )


def stress_fee_schedule() -> FrozenFeeSchedule:
    return FrozenFeeSchedule(
        maker_rate=STRESS_MAKER_RATE,
        taker_rate=STRESS_TAKER_RATE,
        source="PRE_RESULT_1.5X_PRIMARY_FEE_STRESS",
        basis=FEE_BASIS,
        verified_public_schedule=False,
    )


def validate_amendment() -> None:
    if ORIGINAL_M5_IDENTITY != "cbffd48a9eea77a7ace843f9c830ac96bd39a071":
        raise FeeAmendmentError("m5_identity")
    if FEE_BASIS != "OFFICIAL_PUBLIC_REGULAR_USER_USDT_M_NO_BNB_DISCOUNT":
        raise FeeAmendmentError("fee_basis")
    if PRIMARY_MAKER_RATE != 0.0002 or PRIMARY_TAKER_RATE != 0.0005:
        raise FeeAmendmentError("primary_fee_identity")
    if STRESS_MULTIPLIER != 1.5:
        raise FeeAmendmentError("stress_multiplier")
    if abs(STRESS_MAKER_RATE - PRIMARY_MAKER_RATE * STRESS_MULTIPLIER) > 1e-15:
        raise FeeAmendmentError("stress_maker")
    if abs(STRESS_TAKER_RATE - PRIMARY_TAKER_RATE * STRESS_MULTIPLIER) > 1e-15:
        raise FeeAmendmentError("stress_taker")
    if not OFFICIAL_EVIDENCE_URL.startswith("https://www.binance.com/"):
        raise FeeAmendmentError("evidence_source")
    if not M6_HISTORICAL_ECONOMICS_AUTHORIZED:
        raise FeeAmendmentError("m6_authorization")
    if LIVE_TRADING_AUTHORIZED:
        raise FeeAmendmentError("live_must_remain_forbidden")

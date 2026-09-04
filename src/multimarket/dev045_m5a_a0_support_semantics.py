from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, replace
import math

from multimarket.dev044_t0_strategy_contract import StrategyState
from multimarket.dev045_m3_policy import (
    MarketState,
    PolicyDecision,
    policy_decision,
)

EXPERIMENT_ID = "DEV045-M5A"
DESIGN_VERSION = "a0-exact-joint-support-decision-clock-v1"

AUTHORIZED_DAYS = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)

A0_UNAVAILABLE_DAYS = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
)

A0_EXACT_SUPPORT_DAYS = (
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)

POLICY_IDS = (
    "M01",
    "M02",
    "M03",
    "M04",
    "M05",
    "M06",
    "M07",
    "M08",
)

MARKET_EVENT = "MARKET_EVENT"
POLICY_DECISION_EPOCH = "POLICY_DECISION_EPOCH"

MARKET_EVENT_REEVALUATES_POLICY = False
PROBABILITY_FORWARD_FILL_ENABLED = False
PROBABILITY_INTERPOLATION_ENABLED = False
PROBABILITY_BACKFILL_ENABLED = False
A0_REFIT_ENABLED = False
A0_RETRAIN_ENABLED = False
FUTURE_INFORMATION_ENABLED = False
HISTORICAL_FILE_IO_ENABLED = False
HISTORICAL_REPLAY_EXECUTION_ENABLED = False
HISTORICAL_PNL_ENABLED = False
CANONICAL_PNL_WRITE_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

M3_COMPATIBILITY_SENTINEL = 0.0
M3_COMPATIBILITY_SENTINEL_IS_PREDICTION = False

DIAGNOSTIC_ONLY = True
PROMOTION_GATE = False
MODEL_SELECTION = False
RESCUE_AUTHORIZATION = False

FROZEN_POLICY_COUNT = 8
FROZEN_DAY_COUNT = 7
FROZEN_BLOCKS_PER_DAY = 6
FROZEN_BLOCKS_PER_POLICY = 42
FROZEN_BOOTSTRAP_REPS = 20_000
FROZEN_BOOTSTRAP_SEED = 450045
FROZEN_FWER_ALPHA = 0.05


class M5ASupportError(RuntimeError):
    pass


@dataclass(frozen=True)
class A0ScorePoint:
    timestamp_us: int
    p_touch: float

    def __post_init__(self) -> None:
        t = int(self.timestamp_us)
        p = float(self.p_touch)
        if t < 0:
            raise M5ASupportError("negative_timestamp")
        if not math.isfinite(p) or p < 0.0 or p > 1.0:
            raise M5ASupportError("invalid_probability")


@dataclass(frozen=True)
class ExactA0ScoreIndex:
    day: str
    points: tuple[A0ScorePoint, ...]

    def __post_init__(self) -> None:
        if self.day not in A0_EXACT_SUPPORT_DAYS:
            raise M5ASupportError("a0_index_day_not_frozen_support_day")
        ts = tuple(int(x.timestamp_us) for x in self.points)
        if any(b <= a for a, b in zip(ts, ts[1:])):
            raise M5ASupportError("a0_support_not_strictly_ordered")

    def exact(self, timestamp_us: int) -> float | None:
        """Return only an exact timestamp match.

        No interpolation, nearest-neighbor lookup, forward-fill, backfill,
        or cross-epoch carry is permitted.
        """
        t = int(timestamp_us)
        ts = tuple(int(x.timestamp_us) for x in self.points)
        i = bisect_left(ts, t)
        if i >= len(ts) or ts[i] != t:
            return None
        return float(self.points[i].p_touch)


@dataclass(frozen=True)
class A0LegacySupport:
    decision_timestamp_us: int
    available: bool
    p_touch: float | None
    legacy_state: StrategyState | None

    def __post_init__(self) -> None:
        if int(self.decision_timestamp_us) < 0:
            raise M5ASupportError("negative_decision_timestamp")

        joint = self.p_touch is not None and self.legacy_state is not None

        if bool(self.available) != bool(joint):
            raise M5ASupportError("half_valid_support")

        if self.p_touch is not None:
            p = float(self.p_touch)
            if not math.isfinite(p) or p < 0.0 or p > 1.0:
                raise M5ASupportError("invalid_support_probability")

    @classmethod
    def unavailable(cls, decision_timestamp_us: int) -> "A0LegacySupport":
        return cls(
            decision_timestamp_us=int(decision_timestamp_us),
            available=False,
            p_touch=None,
            legacy_state=None,
        )

    @classmethod
    def available_at(
        cls,
        decision_timestamp_us: int,
        p_touch: float,
        legacy_state: StrategyState,
    ) -> "A0LegacySupport":
        return cls(
            decision_timestamp_us=int(decision_timestamp_us),
            available=True,
            p_touch=float(p_touch),
            legacy_state=legacy_state,
        )


def resolve_joint_support(
    *,
    day: str,
    decision_timestamp_us: int,
    a0_index: ExactA0ScoreIndex | None,
    causal_legacy_state: StrategyState | None,
) -> A0LegacySupport:
    """Resolve support at one explicit policy-decision epoch.

    Availability means BOTH:
      1. exact legitimate A0 support at this timestamp, and
      2. causal legacy StrategyState available at this timestamp.
    """
    if day not in AUTHORIZED_DAYS:
        raise M5ASupportError("unauthorized_day")

    t = int(decision_timestamp_us)

    if day in A0_UNAVAILABLE_DAYS:
        # Fail closed if a caller attempts to inject A0 support into Jan-Mar.
        if a0_index is not None:
            raise M5ASupportError("a0_index_for_frozen_unavailable_day")
        return A0LegacySupport.unavailable(t)

    if a0_index is None:
        return A0LegacySupport.unavailable(t)

    if a0_index.day != day:
        raise M5ASupportError("a0_index_day_mismatch")

    p = a0_index.exact(t)

    if p is None or causal_legacy_state is None:
        return A0LegacySupport.unavailable(t)

    return A0LegacySupport.available_at(
        t,
        p,
        causal_legacy_state,
    )


def bind_support_to_m3(
    state: MarketState,
    support: A0LegacySupport,
) -> MarketState:
    """Bind M5A support to frozen M3 without modifying M3.

    Unavailable support uses numeric 0.0 only because frozen M3 requires
    a finite probability field. legacy_state=None is the authoritative
    unavailable gate. The sentinel is never a prediction.
    """
    if support.available:
        assert support.p_touch is not None
        assert support.legacy_state is not None
        return replace(
            state,
            legacy_state=support.legacy_state,
            a0_p_touch=float(support.p_touch),
        )

    return replace(
        state,
        legacy_state=None,
        a0_p_touch=M3_COMPATIBILITY_SENTINEL,
    )


def assert_policy_decision_clock(clock_kind: str) -> None:
    if clock_kind == MARKET_EVENT:
        raise M5ASupportError("policy_evaluation_forbidden_on_market_event")
    if clock_kind != POLICY_DECISION_EPOCH:
        raise M5ASupportError("unknown_clock_kind")


def decision_at_epoch(
    *,
    policy_id: str,
    state: MarketState,
    support: A0LegacySupport,
    clock_kind: str = POLICY_DECISION_EPOCH,
) -> PolicyDecision:
    """Evaluate a policy only at an explicit policy-decision epoch.

    M06/M07 receive M5A support semantics.
    Other frozen policies are evaluated on the supplied M3 MarketState
    without any A0/legacy mutation.
    """
    assert_policy_decision_clock(clock_kind)

    if policy_id not in POLICY_IDS:
        raise M5ASupportError("unknown_policy")

    if policy_id in ("M06", "M07"):
        bound = bind_support_to_m3(state, support)
    else:
        bound = state

    return policy_decision(policy_id, bound)


def behavior_signature(decision: PolicyDecision) -> tuple:
    """Behavioral fields frozen for M02/M06/M07 fallback equivalence."""
    return (
        decision.bid_target_tick,
        decision.ask_target_tick,
        decision.bid_size,
        decision.ask_size,
        decision.bid_enabled,
        decision.ask_enabled,
        decision.reference_shift_ticks,
        decision.force_flatten,
        decision.flatten_direction,
        decision.flatten_qty,
    )

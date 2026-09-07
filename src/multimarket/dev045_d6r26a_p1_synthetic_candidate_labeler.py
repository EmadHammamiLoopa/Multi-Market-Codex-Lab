from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import math
from typing import Mapping, Sequence

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0


EXPERIMENT_ID = "DEV045-D6R26A-P1"
DESIGN_VERSION = "synthetic-candidate-labeler-engine-contract-v1"
PARENT_P0_HEAD = "33c61a4e3904659ea44a0edfe763f31e31c58ba8"

SYNTHETIC_ONLY = True
HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_SOURCE_HASH_AUTHORIZED = False
CANONICAL_LABEL_MATERIALIZATION_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
ECONOMIC_ARENA_AUTHORIZED = False
NETWORK_ACQUISITION_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

FILL_HORIZON_ORIGIN = "DECISION_LOCAL_TIME"
MARKOUT_HORIZON_ORIGIN = p0.MARKOUT_ORIGIN
MARKOUT_MID_ASOF_RULE = "LAST_BBO_MID_WITH_EXCHANGE_TS_LE_TARGET"
MARKOUT_FILL_INCLUSION_HORIZON_NS = p0.PRIMARY_FILL_HORIZON_NS

POST_ONLY_ACCEPTED = "POST_ONLY_ACCEPTED"
POST_ONLY_REJECTED_AT_ARRIVAL = "POST_ONLY_REJECTED_AT_ARRIVAL"
CENSORED_BEFORE_PLACEMENT_OUTCOME = "CENSORED_BEFORE_PLACEMENT_OUTCOME"

FILLED_WITHIN_TAU = "FILLED_WITHIN_TAU"
NOT_FILLED_WITHIN_TAU = "NOT_FILLED_WITHIN_TAU"
CENSORED = "CENSORED"

FULL_WITHIN_TAU = "FULL_WITHIN_TAU"
NOT_FULL_WITHIN_TAU = "NOT_FULL_WITHIN_TAU"
FULL_STATUS_CENSORED = "CENSORED"

MARKOUT_OBSERVED = "OBSERVED"
MARKOUT_CENSORED = "CENSORED"
MARKOUT_NOT_APPLICABLE_NO_FILL = "NOT_APPLICABLE_NO_FILL"

HFT_NONE = 0
HFT_NEW = 1
HFT_EXPIRED = 2
HFT_FILLED = 3
HFT_CANCELED = 4
HFT_PARTIALLY_FILLED = 5
HFT_REJECTED = 6


class CandidateLabelerError(RuntimeError):
    pass


def _finite(name: str, value: object) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise CandidateLabelerError(name) from exc
    if not math.isfinite(x):
        raise CandidateLabelerError(name)
    return x


def _ns(name: str, value: object) -> int:
    if isinstance(value, bool):
        raise CandidateLabelerError(name)
    try:
        x = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise CandidateLabelerError(name) from exc
    if x < 0 or x != value:
        raise CandidateLabelerError(name)
    return x


@dataclass(frozen=True)
class CandidateSpec:
    side: str
    distance_ticks: int
    decision_local_ns: int
    best_bid_tick: int
    best_ask_tick: int
    qty: float = p0.CANDIDATE_ORDER_QTY

    def __post_init__(self) -> None:
        if self.side not in p0.CANDIDATE_SIDES:
            raise CandidateLabelerError("candidate_side")
        if int(self.distance_ticks) not in p0.CANDIDATE_DISTANCE_TICKS:
            raise CandidateLabelerError("candidate_distance")
        if int(self.best_bid_tick) <= 0 or int(self.best_ask_tick) <= int(self.best_bid_tick):
            raise CandidateLabelerError("candidate_book")
        if not math.isclose(float(self.qty), p0.CANDIDATE_ORDER_QTY, rel_tol=0.0, abs_tol=1e-15):
            raise CandidateLabelerError("candidate_qty")
        _ns("decision_local_ns", self.decision_local_ns)

    @property
    def price_tick(self) -> int:
        if self.side == "BID":
            return int(self.best_bid_tick) - int(self.distance_ticks)
        return int(self.best_ask_tick) + int(self.distance_ticks)

    @property
    def price(self) -> float:
        tick = self.price_tick
        if tick <= 0:
            raise CandidateLabelerError("candidate_price_tick")
        return float(tick) * float(p0.TICK_SIZE)

    @property
    def side_sign(self) -> int:
        return 1 if self.side == "BID" else -1


@dataclass(frozen=True)
class FillObservation:
    exchange_execution_ns: int
    local_response_ns: int
    qty: float
    price: float

    def __post_init__(self) -> None:
        ex = _ns("fill_exchange_execution_ns", self.exchange_execution_ns)
        local = _ns("fill_local_response_ns", self.local_response_ns)
        if local < ex:
            raise CandidateLabelerError("fill_response_before_execution")
        if _finite("fill_qty", self.qty) <= 0.0:
            raise CandidateLabelerError("fill_qty")
        if _finite("fill_price", self.price) <= 0.0:
            raise CandidateLabelerError("fill_price")


@dataclass(frozen=True)
class MidObservation:
    exchange_ns: int
    best_bid_tick: int
    best_ask_tick: int

    def __post_init__(self) -> None:
        _ns("mid_exchange_ns", self.exchange_ns)
        if int(self.best_bid_tick) <= 0 or int(self.best_ask_tick) <= int(self.best_bid_tick):
            raise CandidateLabelerError("mid_book")

    @property
    def mid(self) -> float:
        return 0.5 * (int(self.best_bid_tick) + int(self.best_ask_tick)) * float(p0.TICK_SIZE)


@dataclass(frozen=True)
class FillHorizonLabel:
    horizon_ns: int
    state: str
    any_fill_within_tau: bool | None
    fill_fraction_at_tau: float | None
    fill_fraction_censored: bool
    time_to_first_fill_ns: int | None
    time_to_full_fill_ns: int | None
    full_fill_status: str


@dataclass(frozen=True)
class MarkoutLabel:
    horizon_ns: int
    status: str
    value_bps: float | None
    included_fill_count: int
    included_fill_qty: float


def validate_feature_observability(
    *,
    decision_local_ns: int,
    feature_observable_local_ns: Mapping[str, int],
) -> None:
    decision = _ns("decision_local_ns", decision_local_ns)
    for name, raw in feature_observable_local_ns.items():
        observed = _ns(f"feature_time:{name}", raw)
        if observed > decision:
            raise CandidateLabelerError(f"future_feature:{name}")


def lane_phase(*, day_start_local_ns: int, decision_local_ns: int) -> int:
    start = _ns("day_start_local_ns", day_start_local_ns)
    decision = _ns("decision_local_ns", decision_local_ns)
    if decision < start:
        raise CandidateLabelerError("decision_before_day")
    delta = decision - start
    if delta % p0.DECISION_STEP_NS != 0:
        raise CandidateLabelerError("decision_not_grid_aligned")
    second_index = delta // p0.DECISION_STEP_NS
    return int(second_index % len(p0.LANE_PHASE_OFFSETS_S))


def assert_lane_isolation(decision_local_ns: Sequence[int]) -> None:
    ordered = tuple(int(x) for x in decision_local_ns)
    if any(b <= a for a, b in zip(ordered, ordered[1:])):
        raise CandidateLabelerError("lane_not_strict")
    if any(
        b - a < p0.MAX_CANDIDATE_LIFETIME_NS
        for a, b in zip(ordered, ordered[1:])
    ):
        raise CandidateLabelerError("lane_overlap")


def _sorted_fills(fills: Sequence[FillObservation]) -> tuple[FillObservation, ...]:
    ordered = tuple(sorted(fills, key=lambda x: (x.exchange_execution_ns, x.local_response_ns)))
    total = sum(float(x.qty) for x in ordered)
    if total > p0.CANDIDATE_ORDER_QTY + 1e-12:
        raise CandidateLabelerError("fill_qty_exceeds_candidate")
    return ordered


def fill_horizon_label(
    *,
    candidate: CandidateSpec,
    fills: Sequence[FillObservation],
    horizon_ns: int,
    source_exchange_observed_through_ns: int,
    placement_outcome: str,
) -> FillHorizonLabel:
    if int(horizon_ns) not in p0.FILL_HORIZONS_NS:
        raise CandidateLabelerError("fill_horizon")
    if placement_outcome not in p0.PLACEMENT_OUTCOMES:
        raise CandidateLabelerError("placement_outcome")

    observed_through = _ns("source_exchange_observed_through_ns", source_exchange_observed_through_ns)
    target = int(candidate.decision_local_ns) + int(horizon_ns)
    ordered = _sorted_fills(fills)
    in_horizon = tuple(x for x in ordered if int(x.exchange_execution_ns) <= target)
    cum = sum(float(x.qty) for x in in_horizon)
    any_fill = bool(in_horizon)
    full_time = None
    running = 0.0
    for fill in in_horizon:
        running += float(fill.qty)
        if running >= float(candidate.qty) - 1e-12:
            full_time = int(fill.exchange_execution_ns) - int(candidate.decision_local_ns)
            break
    first_time = (
        int(in_horizon[0].exchange_execution_ns) - int(candidate.decision_local_ns)
        if in_horizon else None
    )

    terminal_no_fill = placement_outcome == POST_ONLY_REJECTED_AT_ARRIVAL
    horizon_observed = observed_through >= target

    if any_fill:
        state = FILLED_WITHIN_TAU
        any_fill_value: bool | None = True
    elif terminal_no_fill or horizon_observed:
        state = NOT_FILLED_WITHIN_TAU
        any_fill_value = False
    else:
        state = CENSORED
        any_fill_value = None

    if terminal_no_fill:
        fill_fraction = 0.0
        fraction_censored = False
        full_status = NOT_FULL_WITHIN_TAU
    elif horizon_observed:
        fill_fraction = min(1.0, cum / float(candidate.qty))
        fraction_censored = False
        full_status = FULL_WITHIN_TAU if full_time is not None else NOT_FULL_WITHIN_TAU
    else:
        fill_fraction = None
        fraction_censored = True
        full_status = FULL_WITHIN_TAU if full_time is not None else FULL_STATUS_CENSORED

    return FillHorizonLabel(
        horizon_ns=int(horizon_ns),
        state=state,
        any_fill_within_tau=any_fill_value,
        fill_fraction_at_tau=fill_fraction,
        fill_fraction_censored=fraction_censored,
        time_to_first_fill_ns=first_time,
        time_to_full_fill_ns=full_time,
        full_fill_status=full_status,
    )


def _validate_mid_series(midpoints: Sequence[MidObservation]) -> tuple[MidObservation, ...]:
    ordered = tuple(sorted(midpoints, key=lambda x: x.exchange_ns))
    if any(b.exchange_ns <= a.exchange_ns for a, b in zip(ordered, ordered[1:])):
        raise CandidateLabelerError("mid_series_not_strict")
    return ordered


def mid_asof(
    *,
    midpoints: Sequence[MidObservation],
    target_exchange_ns: int,
    source_exchange_observed_through_ns: int,
) -> float | None:
    target = _ns("target_exchange_ns", target_exchange_ns)
    observed_through = _ns("source_exchange_observed_through_ns", source_exchange_observed_through_ns)
    if observed_through < target:
        return None
    ordered = _validate_mid_series(midpoints)
    if not ordered:
        return None
    ts = [x.exchange_ns for x in ordered]
    i = bisect_right(ts, target) - 1
    if i < 0:
        return None
    return float(ordered[i].mid)


def fill_markout_bps(*, side: str, fill_price: float, future_mid: float) -> float:
    if side not in p0.CANDIDATE_SIDES:
        raise CandidateLabelerError("markout_side")
    price = _finite("fill_price", fill_price)
    mid = _finite("future_mid", future_mid)
    if price <= 0.0 or mid <= 0.0:
        raise CandidateLabelerError("markout_price")
    sign = 1.0 if side == "BID" else -1.0
    return 10_000.0 * sign * (mid - price) / price


def candidate_markout_label(
    *,
    candidate: CandidateSpec,
    fills: Sequence[FillObservation],
    midpoints: Sequence[MidObservation],
    horizon_ns: int,
    source_exchange_observed_through_ns: int,
    fill_inclusion_horizon_ns: int = MARKOUT_FILL_INCLUSION_HORIZON_NS,
) -> MarkoutLabel:
    if int(horizon_ns) not in p0.MARKOUT_HORIZONS_NS:
        raise CandidateLabelerError("markout_horizon")
    if int(fill_inclusion_horizon_ns) not in p0.FILL_HORIZONS_NS:
        raise CandidateLabelerError("fill_inclusion_horizon")

    cutoff = int(candidate.decision_local_ns) + int(fill_inclusion_horizon_ns)
    included = tuple(
        x for x in _sorted_fills(fills)
        if int(x.exchange_execution_ns) <= cutoff
    )
    if not included:
        return MarkoutLabel(
            horizon_ns=int(horizon_ns),
            status=MARKOUT_NOT_APPLICABLE_NO_FILL,
            value_bps=None,
            included_fill_count=0,
            included_fill_qty=0.0,
        )

    weighted = 0.0
    qty_total = 0.0
    for fill in included:
        target = int(fill.exchange_execution_ns) + int(horizon_ns)
        mid = mid_asof(
            midpoints=midpoints,
            target_exchange_ns=target,
            source_exchange_observed_through_ns=source_exchange_observed_through_ns,
        )
        if mid is None:
            return MarkoutLabel(
                horizon_ns=int(horizon_ns),
                status=MARKOUT_CENSORED,
                value_bps=None,
                included_fill_count=len(included),
                included_fill_qty=sum(float(x.qty) for x in included),
            )
        value = fill_markout_bps(
            side=candidate.side,
            fill_price=float(fill.price),
            future_mid=mid,
        )
        weighted += float(fill.qty) * value
        qty_total += float(fill.qty)

    if qty_total <= 0.0:
        raise CandidateLabelerError("markout_zero_qty")
    return MarkoutLabel(
        horizon_ns=int(horizon_ns),
        status=MARKOUT_OBSERVED,
        value_bps=weighted / qty_total,
        included_fill_count=len(included),
        included_fill_qty=qty_total,
    )


def classify_gtx_placement_status(status: int) -> str:
    s = int(status)
    if s in (HFT_NEW, HFT_PARTIALLY_FILLED, HFT_FILLED, HFT_CANCELED):
        return POST_ONLY_ACCEPTED
    if s == HFT_EXPIRED:
        return POST_ONLY_REJECTED_AT_ARRIVAL
    if s in (HFT_NONE,):
        return CENSORED_BEFORE_PLACEMENT_OUTCOME
    if s == HFT_REJECTED:
        raise CandidateLabelerError("unexpected_gtx_rejected_status")
    raise CandidateLabelerError("unknown_hft_status")


def validate_p1_contract() -> None:
    p0.validate_design_contract()
    if EXPERIMENT_ID != "DEV045-D6R26A-P1":
        raise RuntimeError("experiment_id")
    if PARENT_P0_HEAD != "33c61a4e3904659ea44a0edfe763f31e31c58ba8":
        raise RuntimeError("parent_p0")
    if FILL_HORIZON_ORIGIN != "DECISION_LOCAL_TIME":
        raise RuntimeError("fill_horizon_origin")
    if MARKOUT_HORIZON_ORIGIN != "EXCHANGE_EXECUTION_TIME":
        raise RuntimeError("markout_horizon_origin")
    if MARKOUT_FILL_INCLUSION_HORIZON_NS != 1_000_000_000:
        raise RuntimeError("markout_fill_inclusion")
    if POST_ONLY_REJECTED_AT_ARRIVAL not in p0.PLACEMENT_OUTCOMES:
        raise RuntimeError("placement_semantics")
    if CENSORED not in p0.FILL_LABEL_STATES:
        raise RuntimeError("censor_semantics")
    forbidden = (
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_SOURCE_HASH_AUTHORIZED,
        CANONICAL_LABEL_MATERIALIZATION_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        ECONOMIC_ARENA_AUTHORIZED,
        NETWORK_ACQUISITION_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
    )
    if any(forbidden):
        raise RuntimeError("forbidden_authorization")


__all__ = [
    "CandidateSpec",
    "FillObservation",
    "MidObservation",
    "FillHorizonLabel",
    "MarkoutLabel",
    "fill_horizon_label",
    "candidate_markout_label",
    "fill_markout_bps",
    "mid_asof",
    "lane_phase",
    "assert_lane_isolation",
    "validate_feature_observability",
    "classify_gtx_placement_status",
    "validate_p1_contract",
]

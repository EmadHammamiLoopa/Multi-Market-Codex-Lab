from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math

from multimarket import dev045_d6r26a_p0_formal_gen2_conditional_maker_edge_design as p0
from multimarket import dev045_d6r26a_p1_synthetic_candidate_labeler as p1
from multimarket import dev045_d6r26a_p2_jan_jul_consumed_development_label_design as p2
from multimarket import dev045_d6r26a_p2_r8b_feature_label_executor_freeze as r8b
from multimarket import dev045_d6r26a_p2_r9_raw_event_decoder_freeze as r9

EXPERIMENT_ID = "DEV045-D6R26A-P2-R10"
DESIGN_VERSION = "bounded-rolling-feature-accumulator-freeze-v1"
PARENT_R9_HEAD = "6dfa308399f8c6b4780dcfedfc9509dae8bcfbed"
DATA_ROLE = "CONSUMED_DEVELOPMENT"

BOUNDED_ROLLING_FEATURE_ACCUMULATOR_FROZEN = True
REFERENCE_SEMANTICS = "R8B_BATCH_FEATURE_DEFINITIONS"
RAW_EVENT_SEMANTICS = "R9_EXACT_L2_DECODER"
MAX_FEATURE_WINDOW_NS = 30_000_000_000
RECENT_BOOK_RETENTION_NS = 1_000_000_000
FEATURE_WARMUP_NS = p2.FEATURE_WARMUP_NS

HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
SIMULATOR_IMPORT_AUTHORIZED = False
CANDIDATE_SIMULATION_AUTHORIZED = False
ATTEMPT_MARKER_WRITE_AUTHORIZED = False
CANONICAL_LABEL_WRITE_AUTHORIZED = False
MODEL_FIT_AUTHORIZED = False
PNL_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False
AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False


class BoundedFeatureAccumulatorError(RuntimeError):
    pass


@dataclass
class _RollingSum:
    window_ns: int

    def __post_init__(self) -> None:
        self.events: deque[tuple[int, float]] = deque()
        self.total = 0.0

    def add(self, local_ns: int, value: float) -> None:
        ts = int(local_ns)
        x = float(value)
        if self.events and ts < self.events[-1][0]:
            raise BoundedFeatureAccumulatorError("rolling_timestamp_regression")
        if not math.isfinite(x):
            raise BoundedFeatureAccumulatorError("rolling_nonfinite")
        self.events.append((ts, x))
        self.total += x

    def advance(self, decision_local_ns: int) -> float:
        cutoff = int(decision_local_ns) - int(self.window_ns)
        while self.events and self.events[0][0] <= cutoff:
            _, x = self.events.popleft()
            self.total -= x
        return float(self.total)


class RollingFeatureAccumulator:
    def __init__(self) -> None:
        self._last_book: r8b.BookObservation | None = None
        self._first_book_local_ns: int | None = None
        self._latest_observed_local_ns = -1
        self._last_decision_local_ns = -1
        self._recent_books: deque[r8b.BookObservation] = deque()

        self._ofi_1s = _RollingSum(1_000_000_000)
        self._ofi_5s = _RollingSum(5_000_000_000)
        self._vol_1s = _RollingSum(1_000_000_000)
        self._vol_5s = _RollingSum(5_000_000_000)
        self._vol_30s = _RollingSum(30_000_000_000)

        self._trade_buy_1s = _RollingSum(1_000_000_000)
        self._trade_sell_1s = _RollingSum(1_000_000_000)
        self._trade_buy_5s = _RollingSum(5_000_000_000)
        self._trade_sell_5s = _RollingSum(5_000_000_000)
        self._add_bid_1s = _RollingSum(1_000_000_000)
        self._add_ask_1s = _RollingSum(1_000_000_000)
        self._cancel_bid_1s = _RollingSum(1_000_000_000)
        self._cancel_ask_1s = _RollingSum(1_000_000_000)

    def ingest_book(self, book: r8b.BookObservation) -> None:
        ts = int(book.local_ns)
        if ts < self._latest_observed_local_ns:
            raise BoundedFeatureAccumulatorError("book_timestamp_regression")
        if self._last_book is not None:
            ofi = r8b.bbo_ofi_transition(self._last_book, book)
            self._ofi_1s.add(ts, ofi)
            self._ofi_5s.add(ts, ofi)
            before = float(self._last_book.mid_price)
            after = float(book.mid_price)
            if before <= 0.0 or after <= 0.0:
                raise BoundedFeatureAccumulatorError("mid_price")
            sq = math.log(after / before) ** 2
            self._vol_1s.add(ts, sq)
            self._vol_5s.add(ts, sq)
            self._vol_30s.add(ts, sq)
        else:
            self._first_book_local_ns = ts
        self._last_book = book
        self._recent_books.append(book)
        self._latest_observed_local_ns = max(self._latest_observed_local_ns, ts)

    def ingest_flow(self, flow: r8b.FlowObservation) -> None:
        ts = int(flow.local_ns)
        if ts < self._latest_observed_local_ns:
            # Books and flows may share a timestamp, but a future flow cannot be
            # inserted after a later observed timestamp.
            raise BoundedFeatureAccumulatorError("flow_timestamp_regression")
        q = float(flow.qty)
        if flow.kind == "TRADE":
            if flow.side == "BUY":
                self._trade_buy_1s.add(ts, q)
                self._trade_buy_5s.add(ts, q)
            else:
                self._trade_sell_1s.add(ts, q)
                self._trade_sell_5s.add(ts, q)
        elif flow.kind == "ADD":
            (self._add_bid_1s if flow.side == "BID" else self._add_ask_1s).add(ts, q)
        elif flow.kind == "CANCEL":
            (self._cancel_bid_1s if flow.side == "BID" else self._cancel_ask_1s).add(ts, q)
        else:
            raise BoundedFeatureAccumulatorError("flow_kind")
        self._latest_observed_local_ns = max(self._latest_observed_local_ns, ts)

    def _advance_all(self, decision: int) -> dict[str, float]:
        return {
            "ofi1": self._ofi_1s.advance(decision),
            "ofi5": self._ofi_5s.advance(decision),
            "vol1sq": self._vol_1s.advance(decision),
            "vol5sq": self._vol_5s.advance(decision),
            "vol30sq": self._vol_30s.advance(decision),
            "tb1": self._trade_buy_1s.advance(decision),
            "ts1": self._trade_sell_1s.advance(decision),
            "tb5": self._trade_buy_5s.advance(decision),
            "ts5": self._trade_sell_5s.advance(decision),
            "ab1": self._add_bid_1s.advance(decision),
            "aa1": self._add_ask_1s.advance(decision),
            "cb1": self._cancel_bid_1s.advance(decision),
            "ca1": self._cancel_ask_1s.advance(decision),
        }

    def _prune_recent_books(self, decision: int) -> None:
        cutoff = decision - RECENT_BOOK_RETENTION_NS
        while len(self._recent_books) >= 2 and self._recent_books[1].local_ns <= cutoff:
            self._recent_books.popleft()

    def _book_asof_recent(self, target: int) -> r8b.BookObservation:
        for book in reversed(self._recent_books):
            if int(book.local_ns) <= int(target):
                return book
        raise BoundedFeatureAccumulatorError("recent_book_asof_missing")

    @staticmethod
    def _ratio(a: float, b: float) -> float:
        den = float(a) + float(b)
        return 0.0 if den <= 0.0 else (float(a) - float(b)) / den

    def compute(self, *, candidate: p1.CandidateSpec) -> r8b.FeatureVector:
        decision = int(candidate.decision_local_ns)
        if decision < self._last_decision_local_ns:
            raise BoundedFeatureAccumulatorError("decision_regression")
        if self._latest_observed_local_ns > decision:
            raise BoundedFeatureAccumulatorError("future_observation_ingested")
        if self._last_book is None or self._first_book_local_ns is None:
            raise BoundedFeatureAccumulatorError("book_support_missing")
        if decision - self._first_book_local_ns < FEATURE_WARMUP_NS:
            raise BoundedFeatureAccumulatorError("feature_warmup")
        current = self._last_book
        if int(current.local_ns) > decision:
            raise BoundedFeatureAccumulatorError("current_book_future")
        if len(current.bids) < 5 or len(current.asks) < 5:
            raise BoundedFeatureAccumulatorError("current_l5_support")

        sums = self._advance_all(decision)
        self._prune_recent_books(decision)
        prior250 = self._book_asof_recent(decision - 250_000_000)
        prior1s = self._book_asof_recent(decision - 1_000_000_000)

        mid = float(current.mid_price)
        micro = r8b.microprice_bbo(current)
        vamp5 = r8b.vamp_l5(current)
        bid5 = sum(float(x.qty) for x in current.bids[:5])
        ask5 = sum(float(x.qty) for x in current.asks[:5])
        side = candidate.side
        opposite = "ASK" if side == "BID" else "BID"

        def best_depth(book: r8b.BookObservation, side_name: str) -> float:
            return float(book.best_bid.qty if side_name == "BID" else book.best_ask.qty)

        def visible_qty(book: r8b.BookObservation, side_name: str, tick: int) -> float:
            levels = book.bids if side_name == "BID" else book.asks
            for level in levels:
                if int(level.price_tick) == int(tick):
                    return float(level.qty)
            return 0.0

        displayed = visible_qty(current, side, candidate.price_tick)
        values = {
            "spread_ticks": float(current.spread_ticks),
            "microprice_minus_mid_bps": 10_000.0 * (micro - mid) / mid,
            "vamp_bbo_minus_mid_bps": 10_000.0 * (micro - mid) / mid,
            "vamp_l5_minus_mid_bps": 10_000.0 * (vamp5 - mid) / mid,
            "l1_obi": self._ratio(float(current.best_bid.qty), float(current.best_ask.qty)),
            "l5_obi": self._ratio(bid5, ask5),
            "bbo_ofi_1s": sums["ofi1"],
            "bbo_ofi_5s": sums["ofi5"],
            "trade_imbalance_1s": self._ratio(sums["tb1"], sums["ts1"]),
            "trade_imbalance_5s": self._ratio(sums["tb5"], sums["ts5"]),
            "add_imbalance_1s": self._ratio(sums["ab1"], sums["aa1"]),
            "cancel_imbalance_1s": self._ratio(sums["ca1"], sums["cb1"]),
            "ofi_acceleration_1s_vs_5s": sums["ofi1"] - sums["ofi5"] / 5.0,
            "same_side_depth_change_250ms": best_depth(current, side) - best_depth(prior250, side),
            "opposite_side_depth_change_250ms": best_depth(current, opposite) - best_depth(prior250, opposite),
            "spread_change_1s": float(current.spread_ticks - prior1s.spread_ticks),
            "realized_vol_1s": 10_000.0 * math.sqrt(max(0.0, sums["vol1sq"])),
            "realized_vol_5s": 10_000.0 * math.sqrt(max(0.0, sums["vol5sq"])),
            "realized_vol_30s": 10_000.0 * math.sqrt(max(0.0, sums["vol30sq"])),
            "candidate_side_sign": float(candidate.side_sign),
            "candidate_distance_ticks": float(candidate.distance_ticks),
            "displayed_qty_at_candidate_price": displayed,
            "estimated_queue_ahead_qty_from_decision_book": displayed,
            "own_best_depth_qty": best_depth(current, side),
            "opposite_best_depth_qty": best_depth(current, opposite),
        }
        if tuple(values) != r8b.FEATURE_NAMES:
            raise BoundedFeatureAccumulatorError("feature_order")
        if any(not math.isfinite(float(x)) for x in values.values()):
            raise BoundedFeatureAccumulatorError("feature_nonfinite")
        observable = {name: decision for name in r8b.FEATURE_NAMES}
        p1.validate_feature_observability(
            decision_local_ns=decision,
            feature_observable_local_ns=observable,
        )
        self._last_decision_local_ns = decision
        return r8b.FeatureVector(values, observable, p2.CANDIDATE_ELIGIBILITY)

    def bounded_counts(self) -> dict[str, int]:
        return {
            "recent_books": len(self._recent_books),
            "ofi_5s": len(self._ofi_5s.events),
            "vol_30s": len(self._vol_30s.events),
            "trade_5s": len(self._trade_buy_5s.events) + len(self._trade_sell_5s.events),
        }


def validate_r10_contract() -> None:
    r9.validate_r9_contract()
    r8b.validate_r8b_contract()
    if PARENT_R9_HEAD != "6dfa308399f8c6b4780dcfedfc9509dae8bcfbed":
        raise BoundedFeatureAccumulatorError("parent")
    if DATA_ROLE != "CONSUMED_DEVELOPMENT":
        raise BoundedFeatureAccumulatorError("data_role")
    if MAX_FEATURE_WINDOW_NS != FEATURE_WARMUP_NS or MAX_FEATURE_WINDOW_NS != 30_000_000_000:
        raise BoundedFeatureAccumulatorError("feature_window")
    if RECENT_BOOK_RETENTION_NS != 1_000_000_000:
        raise BoundedFeatureAccumulatorError("book_retention")
    if not BOUNDED_ROLLING_FEATURE_ACCUMULATOR_FROZEN:
        raise BoundedFeatureAccumulatorError("freeze")
    forbidden = (
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        SIMULATOR_IMPORT_AUTHORIZED,
        CANDIDATE_SIMULATION_AUTHORIZED,
        ATTEMPT_MARKER_WRITE_AUTHORIZED,
        CANONICAL_LABEL_WRITE_AUTHORIZED,
        MODEL_FIT_AUTHORIZED,
        PNL_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUG_OPEN_AUTHORIZED,
        SEP_PLUS_OPEN_AUTHORIZED,
        NON_BTC_OPEN_AUTHORIZED,
    )
    if any(forbidden):
        raise BoundedFeatureAccumulatorError("execution_surface_open")


__all__ = [
    "RollingFeatureAccumulator",
    "validate_r10_contract",
]

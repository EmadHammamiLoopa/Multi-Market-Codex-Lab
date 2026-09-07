from __future__ import annotations

from collections import deque
from copy import deepcopy
import math

from multimarket import dev045_d6r20_q4_scheduler_reconciled_driver as q4
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m6_event_loop_kernel as d2


EXPERIMENT_ID = "DEV045-D6R20-Q5-FORENSIC"
DESIGN_VERSION = "invalid-local-book-state-forensic-v1"

BID_NONPOSITIVE = "BID_NONPOSITIVE"
ASK_NOT_ABOVE_BID = "ASK_NOT_ABOVE_BID"
BOTH_INVALID = "BOTH_INVALID"
RECENT_BOOK_OBSERVATION_LIMIT = 32

EXECUTION_SEMANTICS_CHANGED = False
STRATEGY_SEMANTICS_CHANGED = False
INVALID_BOOK_RECOVERY_ENABLED = False
SYNTHETIC_VALIDATION_ALLOWED = True
LIVE_TRADING_AUTHORIZED = False


def classify_invalid_local_book(
    *,
    best_bid_tick: int,
    best_ask_tick: int,
) -> str | None:
    bid_invalid = int(best_bid_tick) <= 0
    ask_invalid = int(best_ask_tick) <= int(best_bid_tick)

    if bid_invalid and ask_invalid:
        return BOTH_INVALID

    if bid_invalid:
        return BID_NONPOSITIVE

    if ask_invalid:
        return ASK_NOT_ABOVE_BID

    return None


def _pending_replacement(slot) -> bool:
    return bool(
        getattr(slot, "replacement_required", False)
        or getattr(slot, "pending_replacement", None) is not None
    )


class InvalidLocalBookForensicContinuousHistoricalPolicyKernel(
    q4.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
):
    """Observational Q4 wrapper that preserves invalid-book failure behavior."""

    def __init__(self, *args, forensic_sink=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.q5_forensic_sink = (
            forensic_sink if forensic_sink is not None else []
        )
        self.q5_recent_local_books = deque(
            maxlen=RECENT_BOOK_OBSERVATION_LIMIT
        )
        self.q5_last_valid_local_book_top: dict | None = None
        self.q5_invalid_local_book_snapshot: dict | None = None
        self.q5_last_market_wakeup_ns: int | None = None
        self.q5_last_response_wakeup_ns: int | None = None
        self.q5_current_wakeup_event_class: str | None = None
        self.q5_current_policy_target_ns: int | None = None
        self.q5_policy_epochs_before_evaluation = 0
        self.q5_adapter_candidates_before_evaluation = 0
        self.q5_direct_queries_before_evaluation = 0
        self.q5_adapter_decisions = 0
        self.q5_adapter_decisions_before_evaluation = 0
        self.q5_last_blocking_wait_reconciliation: dict | None = None

    def _ensure_forensic_state(self) -> None:
        if not hasattr(self, "q5_recent_local_books"):
            self.q5_recent_local_books = deque(
                maxlen=RECENT_BOOK_OBSERVATION_LIMIT
            )
            self.q5_last_valid_local_book_top = None
            self.q5_invalid_local_book_snapshot = None
            self.q5_last_market_wakeup_ns = None
            self.q5_last_response_wakeup_ns = None
            self.q5_current_wakeup_event_class = None
            self.q5_current_policy_target_ns = None
            self.q5_policy_epochs_before_evaluation = int(
                getattr(self, "policy_epochs", 0)
            )
            self.q5_adapter_candidates_before_evaluation = int(
                getattr(self, "adapter_candidate_epochs", 0)
            )
            self.q5_direct_queries_before_evaluation = int(
                getattr(self, "direct_action_queries", 0)
            )
            self.q5_adapter_decisions = 0
            self.q5_adapter_decisions_before_evaluation = 0
            self.q5_last_blocking_wait_reconciliation = None
            self.q5_forensic_sink = []

    def _book_observation(
        self,
        *,
        local_timestamp_ns: int,
        event_class: str,
    ) -> dict:
        self._ensure_forensic_state()
        depth = self.bt.depth(d2.ASSET_NO)
        bid_tick = int(depth.best_bid_tick)
        ask_tick = int(depth.best_ask_tick)
        classification = classify_invalid_local_book(
            best_bid_tick=bid_tick,
            best_ask_tick=ask_tick,
        )
        observation = {
            "local_timestamp_ns": int(local_timestamp_ns),
            "event_class": str(event_class),
            "best_bid_tick": bid_tick,
            "best_ask_tick": ask_tick,
            "best_bid": float(bid_tick * p.TICK_SIZE),
            "best_ask": float(ask_tick * p.TICK_SIZE),
            "classification": classification,
        }
        self.q5_recent_local_books.append(observation)

        if classification is None:
            self.q5_last_valid_local_book_top = deepcopy(observation)

        return observation

    def _capture_invalid_snapshot(
        self,
        *,
        observation: dict,
    ) -> None:
        state = self.bt.state_values(d2.ASSET_NO)
        clock = self.inventory_clock
        snapshot = {
            "bt_current_timestamp": int(self.bt.current_timestamp),
            "current_policy_target_timestamp": self.q5_current_policy_target_ns,
            "next_policy_ns": self.q5_current_policy_target_ns,
            "day": self.day,
            "policy": self.policy_id,
            "scenario": self.scenario,
            "best_bid_tick": int(observation["best_bid_tick"]),
            "best_ask_tick": int(observation["best_ask_tick"]),
            "best_bid": float(observation["best_bid"]),
            "best_ask": float(observation["best_ask"]),
            "tick_size": float(p.TICK_SIZE),
            "classification": observation["classification"],
            "simulator_position": float(self.bt.position(d2.ASSET_NO)),
            "inventory_clock": {
                "position": float(clock.position),
                "nonzero_since_local_ns": (
                    int(clock.nonzero_since_local_ns)
                    if clock.nonzero_since_local_ns is not None
                    else None
                ),
            },
            "working_bid_order_id": self.bid.order_id,
            "working_ask_order_id": self.ask.order_id,
            "pending_replacement": {
                "bid": _pending_replacement(self.bid),
                "ask": _pending_replacement(self.ask),
            },
            "shutdown": {
                "started": bool(self.terminal_shutdown_started),
                "quiescent": bool(self.terminal_shutdown_quiescent),
                "start_ns": self.terminal_shutdown_start_ns,
            },
            "last_market_wakeup_timestamp": self.q5_last_market_wakeup_ns,
            "last_response_wakeup_timestamp": self.q5_last_response_wakeup_ns,
            "current_wakeup_event_class": self.q5_current_wakeup_event_class,
            "last_valid_local_book_top": deepcopy(
                self.q5_last_valid_local_book_top
            ),
            "recent_local_book_observations": deepcopy(
                list(self.q5_recent_local_books)
            ),
            "policy_epoch_count_before_failure": int(self.policy_epochs),
            "policy_epoch_count_before_evaluation": int(
                self.q5_policy_epochs_before_evaluation
            ),
            "adapter_candidate_count_before_evaluation": int(
                self.q5_adapter_candidates_before_evaluation
            ),
            "adapter_decision_count_before_evaluation": int(
                self.q5_adapter_decisions_before_evaluation
            ),
            "direct_action_lookup_count_before_evaluation": int(
                self.q5_direct_queries_before_evaluation
            ),
            "adapter_candidate_count_at_failure": int(
                self.adapter_candidate_epochs
            ),
            "adapter_decision_count_at_failure": int(
                self.q5_adapter_decisions
            ),
            "direct_action_lookup_count_at_failure": int(
                self.direct_action_queries
            ),
            "last_blocking_wait_clock_reconciliation": deepcopy(
                self.q5_last_blocking_wait_reconciliation
            ),
            "state_values": {
                "position": float(state.position),
                "balance": float(state.balance),
                "fee": float(state.fee),
                "num_trades": int(state.num_trades),
                "trading_volume": float(state.trading_volume),
                "trading_value": float(state.trading_value),
            },
        }
        self.q5_invalid_local_book_snapshot = snapshot
        self.q5_forensic_sink.append(deepcopy(snapshot))

    def _capture_last_trades(self) -> None:
        super()._capture_last_trades()
        timestamp = int(self.bt.current_timestamp)
        self.q5_last_market_wakeup_ns = timestamp
        self.q5_current_wakeup_event_class = "LOCAL_MARKET"
        self._book_observation(
            local_timestamp_ns=timestamp,
            event_class="LOCAL_MARKET",
        )

    def _process_response_batch(
        self,
        *,
        local_response_ns: int,
    ) -> None:
        self._ensure_forensic_state()
        self.q5_last_response_wakeup_ns = int(local_response_ns)
        self.q5_current_wakeup_event_class = "LOCAL_ORDER_RESPONSE"
        super()._process_response_batch(
            local_response_ns=local_response_ns,
        )
        self._book_observation(
            local_timestamp_ns=int(self.bt.current_timestamp),
            event_class="LOCAL_ORDER_RESPONSE",
        )

    def _evaluate_policy_epoch(
        self,
        *,
        local_timestamp_ns: int,
    ) -> None:
        self._ensure_forensic_state()
        self.q5_current_wakeup_event_class = "BASE_POLICY_DECISION"
        self.q5_current_policy_target_ns = int(local_timestamp_ns)
        self.q5_policy_epochs_before_evaluation = int(self.policy_epochs)
        self.q5_adapter_candidates_before_evaluation = int(
            self.adapter_candidate_epochs
        )
        self.q5_direct_queries_before_evaluation = int(
            self.direct_action_queries
        )
        self.q5_adapter_decisions_before_evaluation = int(
            self.q5_adapter_decisions
        )
        super()._evaluate_policy_epoch(
            local_timestamp_ns=local_timestamp_ns,
        )

    def _adapter_decision(self, **kwargs):
        self._ensure_forensic_state()
        self.q5_adapter_decisions += 1
        return super()._adapter_decision(**kwargs)

    def _reconcile_policy_target(
        self,
        *,
        current_local_ns: int,
        next_policy_ns: int,
    ) -> int:
        reconciled = super()._reconcile_policy_target(
            current_local_ns=current_local_ns,
            next_policy_ns=next_policy_ns,
        )
        self._ensure_forensic_state()
        self.q5_last_blocking_wait_reconciliation = {
            "current_local_ns": int(current_local_ns),
            "previous_next_policy_ns": int(next_policy_ns),
            "reconciled_next_policy_ns": int(reconciled),
        }
        self.q5_current_policy_target_ns = int(reconciled)
        return reconciled

    def _dynamic_market_state(
        self,
        *,
        local_timestamp_ns: int,
    ) -> p.MarketState:
        event_class = self.q5_current_wakeup_event_class or "UNKNOWN"
        observation = self._book_observation(
            local_timestamp_ns=local_timestamp_ns,
            event_class=event_class,
        )

        if observation["classification"] is not None:
            self._capture_invalid_snapshot(
                observation=observation,
            )

        # Delegate even when invalid. The frozen parent rechecks the same book
        # and raises EventLoopKernelError("invalid_local_book") unchanged.
        return super()._dynamic_market_state(
            local_timestamp_ns=local_timestamp_ns,
        )


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "BID_NONPOSITIVE",
    "ASK_NOT_ABOVE_BID",
    "BOTH_INVALID",
    "RECENT_BOOK_OBSERVATION_LIMIT",
    "EXECUTION_SEMANTICS_CHANGED",
    "STRATEGY_SEMANTICS_CHANGED",
    "INVALID_BOOK_RECOVERY_ENABLED",
    "classify_invalid_local_book",
    "InvalidLocalBookForensicContinuousHistoricalPolicyKernel",
]

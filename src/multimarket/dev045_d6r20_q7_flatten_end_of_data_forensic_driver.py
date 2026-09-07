from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r20_q6_initial_book_readiness_driver as q6
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_event_loop_kernel as d2
from multimarket.dev044_t0_strategy_contract import LONG, SHORT


EXPERIMENT_ID = "DEV045-D6R20-Q7-FORENSIC"
DESIGN_VERSION = "forced-flatten-end-of-data-response-forensic-v1"

STRATEGY_FLATTEN_EOD_WAIT = "STRATEGY_FLATTEN_EOD_WAIT"
TERMINAL_SHUTDOWN_FLATTEN_EOD_WAIT = (
    "TERMINAL_SHUTDOWN_FLATTEN_EOD_WAIT"
)
UNKNOWN_FLATTEN_EOD_WAIT = "UNKNOWN_FLATTEN_EOD_WAIT"

# Exact py-hftbacktest 2.4.4 return-code contract. These constants are
# diagnostic labels only; they do not affect execution.
ELAPSE_RESULT_END_OF_DATA_RC = 1
BACKTEST_ERROR_ORDER_ID_EXIST_RC = 10

EXECUTION_SEMANTICS_CHANGED = False
STRATEGY_SEMANTICS_CHANGED = False
FLATTEN_RECOVERY_ENABLED = False
FLATTEN_RETRY_ENABLED = False
SYNTHETIC_VALIDATION_ALLOWED = True
LIVE_TRADING_AUTHORIZED = False


def classify_flatten_origin(*, terminal_shutdown_started: bool,
                            force_decision_present: bool) -> str:
    if terminal_shutdown_started:
        return TERMINAL_SHUTDOWN_FLATTEN_EOD_WAIT

    if force_decision_present:
        return STRATEGY_FLATTEN_EOD_WAIT

    return UNKNOWN_FLATTEN_EOD_WAIT


def _pending_replacement(slot) -> bool:
    return bool(
        getattr(slot, "replacement_required", False)
        or getattr(slot, "pending_replacement", None) is not None
    )


def _enum_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _order_values_tuple(order_dict) -> tuple:
    values = order_dict.values()
    next_value = getattr(values, "next", None)

    if not callable(next_value):
        return ()

    result = []

    while True:
        raw = next_value()

        if raw is None:
            break

        result.append(raw)

    return tuple(result)


def _order_snapshot(raw) -> dict | None:
    if raw is None:
        return None

    return {
        "order_id": _enum_int(getattr(raw, "order_id", None)),
        "status": _enum_int(getattr(raw, "status", None)),
        "req": _enum_int(getattr(raw, "req", None)),
        "side": _enum_int(getattr(raw, "side", None)),
        "order_type": _enum_int(
            getattr(raw, "order_type", getattr(raw, "ord_type", None))
        ),
        "time_in_force": _enum_int(
            getattr(raw, "time_in_force", getattr(raw, "tif", None))
        ),
        "qty": float(getattr(raw, "qty", 0.0)),
        "leaves_qty": float(getattr(raw, "leaves_qty", 0.0)),
        "exec_qty": float(getattr(raw, "exec_qty", 0.0)),
        "exch_timestamp": _enum_int(
            getattr(raw, "exch_timestamp", None)
        ),
        "local_timestamp": _enum_int(
            getattr(raw, "local_timestamp", None)
        ),
    }


class FlattenEndOfDataForensicContinuousHistoricalPolicyKernel(
    q6.InitialBookReadinessContinuousHistoricalPolicyKernel
):
    """Observational Q6 wrapper around the unique forced-flatten call."""

    def __init__(
        self,
        *args,
        forensic_sink: list[dict] | None = None,
        eod_failure_sink: list[dict] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.q7_flatten_forensic_sink = (
            forensic_sink if forensic_sink is not None else []
        )
        self.q7_eod_failure_sink = (
            eod_failure_sink if eod_failure_sink is not None else []
        )
        self.q7_last_market_wakeup_ns: int | None = None
        self.q7_last_response_wakeup_ns: int | None = None
        self.q7_flatten_submit_attempts = 0

    def _ensure_q7_state(self) -> None:
        if not hasattr(self, "q7_flatten_forensic_sink"):
            self.q7_flatten_forensic_sink = []
            self.q7_eod_failure_sink = []
            self.q7_last_market_wakeup_ns = None
            self.q7_last_response_wakeup_ns = None
            self.q7_flatten_submit_attempts = 0

    def _capture_last_trades(self) -> None:
        super()._capture_last_trades()
        self._ensure_q7_state()
        self.q7_last_market_wakeup_ns = int(self.bt.current_timestamp)

    def _process_response_batch(self, *, local_response_ns: int) -> None:
        self._ensure_q7_state()
        self.q7_last_response_wakeup_ns = int(local_response_ns)
        super()._process_response_batch(local_response_ns=local_response_ns)

    def _safe_capture(
        self,
        record: dict,
        field: str,
        capture: Callable[[], Any],
    ) -> Any:
        try:
            value = capture()
        except BaseException as exc:  # observational diagnostics must not mask execution
            record.setdefault("diagnostic_capture_errors", []).append(
                {
                    "field": field,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                }
            )
            return None

        return value

    def _state_values_snapshot(self) -> dict:
        state = binding.snapshot_state_values(
            self.bt.state_values(d2.ASSET_NO)
        )
        return {
            "position": float(state.position),
            "balance": float(state.balance),
            "fee": float(state.fee),
            "num_trades": int(state.num_trades),
            "trading_volume": float(state.trading_volume),
            "trading_value": float(state.trading_value),
        }

    def _book_top_snapshot(self) -> dict:
        depth = self.bt.depth(d2.ASSET_NO)
        return {
            "best_bid_tick": int(depth.best_bid_tick),
            "best_ask_tick": int(depth.best_ask_tick),
            "best_bid": float(depth.best_bid),
            "best_ask": float(depth.best_ask),
        }

    def _slot_snapshot(self, slot) -> dict:
        order_id = getattr(slot, "order_id", None)
        raw = None

        if order_id is not None:
            raw = self.bt.orders(d2.ASSET_NO).get(int(order_id))

        return {
            "order_id": int(order_id) if order_id is not None else None,
            "replacement_required": _pending_replacement(slot),
            "order": _order_snapshot(raw),
        }

    def _active_or_in_process_order_ids(self) -> tuple[int, ...]:
        active = []

        for raw in _order_values_tuple(self.bt.orders(d2.ASSET_NO)):
            status = int(raw.status)
            req = int(raw.req)

            if req != int(d2.HFT_NONE) or status in (
                int(d2.HFT_NEW),
                int(d2.HFT_PARTIALLY_FILLED),
            ):
                active.append(int(raw.order_id))

        return tuple(active)

    def _order_latency_snapshot(self):
        latency = self.bt.order_latency(d2.ASSET_NO)

        if latency is None:
            return None

        return tuple(int(value) for value in latency)

    def _pre_flatten_snapshot(
        self,
        *,
        direction: int,
        qty: float,
        candidate_order_id: int,
    ) -> dict:
        self._ensure_q7_state()
        record: dict[str, Any] = {"diagnostic_capture_errors": []}
        now = int(self.bt.current_timestamp)
        terminal_source = getattr(self, "terminal_source_local_ns", None)
        cutoff = getattr(self, "terminal_shutdown_cutoff_ns", None)
        terminal_started = bool(
            getattr(self, "terminal_shutdown_started", False)
        )
        force_present = getattr(self, "force_decision", None) is not None
        cfg = base.orch.scenario_config(self.scenario)
        entry_latency = int(cfg.entry_latency_ns)
        response_latency = int(cfg.response_latency_ns)
        nominal_round_trip = entry_latency + response_latency
        candidate = self._safe_capture(
            record,
            "candidate_order_before",
            lambda: self.bt.orders(d2.ASSET_NO).get(candidate_order_id),
        )

        record.update(
            {
                "attempt_index": int(self.q7_flatten_submit_attempts),
                "before_submit_local_timestamp_ns": now,
                "day": self.day,
                "policy": self.policy_id,
                "scenario": self.scenario,
                "terminal_source_local_ns": (
                    int(terminal_source) if terminal_source is not None else None
                ),
                "terminal_shutdown_cutoff_ns": (
                    int(cutoff) if cutoff is not None else None
                ),
                "terminal_shutdown_started": terminal_started,
                "terminal_shutdown_quiescent": bool(
                    getattr(self, "terminal_shutdown_quiescent", False)
                ),
                "terminal_shutdown_start_ns": getattr(
                    self, "terminal_shutdown_start_ns", None
                ),
                "remaining_ns_to_source_end_before_submit": (
                    int(terminal_source) - now
                    if terminal_source is not None else None
                ),
                "remaining_ns_to_shutdown_cutoff_before_submit": (
                    int(cutoff) - now if cutoff is not None else None
                ),
                "entry_latency_ns": entry_latency,
                "response_latency_ns": response_latency,
                "expected_nominal_request_round_trip_ns": nominal_round_trip,
                "remaining_to_source_end_less_than_nominal_round_trip": (
                    int(terminal_source) - now < nominal_round_trip
                    if terminal_source is not None else None
                ),
                "requested_direction": int(direction),
                "requested_direction_label": (
                    "LONG" if int(direction) == int(LONG)
                    else "SHORT" if int(direction) == int(SHORT)
                    else "UNKNOWN"
                ),
                "requested_qty": float(qty),
                "simulator_position_before_submit": float(
                    self.bt.position(d2.ASSET_NO)
                ),
                "inventory_clock_position_before_submit": float(
                    self.inventory_clock.position
                ),
                "candidate_flatten_order_id": candidate_order_id,
                "candidate_order_existed_before_submit": candidate is not None,
                "candidate_order_before": _order_snapshot(candidate),
                "prior_flatten_order_ids": tuple(
                    int(value) for value in self.flatten_order_ids
                ),
                "prior_flatten_order_id_count": len(self.flatten_order_ids),
                "working_bid": self._safe_capture(
                    record, "working_bid", lambda: self._slot_snapshot(self.bid)
                ),
                "working_ask": self._safe_capture(
                    record, "working_ask", lambda: self._slot_snapshot(self.ask)
                ),
                "pending_replacements": {
                    "bid": _pending_replacement(self.bid),
                    "ask": _pending_replacement(self.ask),
                },
                "force_decision_present": force_present,
                "flatten_done": bool(getattr(self, "flatten_done", False)),
                "book_top_before_submit": self._safe_capture(
                    record, "book_top_before_submit", self._book_top_snapshot
                ),
                "state_values_before_submit": self._safe_capture(
                    record, "state_values_before_submit",
                    self._state_values_snapshot,
                ),
                "last_market_wakeup_timestamp": self.q7_last_market_wakeup_ns,
                "last_response_wakeup_timestamp": self.q7_last_response_wakeup_ns,
                "flatten_origin": classify_flatten_origin(
                    terminal_shutdown_started=terminal_started,
                    force_decision_present=force_present,
                ),
                "end_of_data_rc": ELAPSE_RESULT_END_OF_DATA_RC,
                "order_id_exist_rc": BACKTEST_ERROR_ORDER_ID_EXIST_RC,
                "rc_1_is_order_id_collision": False,
                "execution_semantics_changed": False,
                "retry_enabled": False,
            }
        )
        return record

    def _after_snapshot(self, record: dict, *, failed: bool) -> None:
        now = int(self.bt.current_timestamp)
        terminal_source = getattr(self, "terminal_source_local_ns", None)
        candidate_order_id = int(record["candidate_flatten_order_id"])
        candidate = self._safe_capture(
            record,
            "candidate_order_after",
            lambda: self.bt.orders(d2.ASSET_NO).get(candidate_order_id),
        )
        record.update(
            {
                "after_submit_local_timestamp_ns": now,
                "clock_advancement_during_submit_wait_ns": (
                    now - int(record["before_submit_local_timestamp_ns"])
                ),
                "remaining_ns_to_source_end_after_submit": (
                    int(terminal_source) - now
                    if terminal_source is not None else None
                ),
                "candidate_order_existed_after_submit": candidate is not None,
                "candidate_order_after": _order_snapshot(candidate),
                "active_or_in_process_order_ids_after_submit": self._safe_capture(
                    record,
                    "active_or_in_process_order_ids_after_submit",
                    self._active_or_in_process_order_ids,
                ),
                "simulator_position_after_submit": float(
                    self.bt.position(d2.ASSET_NO)
                ),
                "inventory_clock_position_after_submit": float(
                    self.inventory_clock.position
                ),
                "state_values_after_submit": self._safe_capture(
                    record, "state_values_after_submit",
                    self._state_values_snapshot,
                ),
                "book_top_after_submit": self._safe_capture(
                    record, "book_top_after_submit", self._book_top_snapshot
                ),
                "terminal_shutdown_started_after_submit": bool(
                    getattr(self, "terminal_shutdown_started", False)
                ),
                "terminal_shutdown_quiescent_after_submit": bool(
                    getattr(self, "terminal_shutdown_quiescent", False)
                ),
                "source_at_or_past_terminal_after_submit": (
                    now >= int(terminal_source)
                    if terminal_source is not None else None
                ),
                "latest_order_latency_tuple": self._safe_capture(
                    record, "latest_order_latency_tuple",
                    self._order_latency_snapshot,
                ),
                "submit_failed": bool(failed),
            }
        )

    def _execute_unique_flatten(self, *, direction: int, qty: float) -> None:
        self._ensure_q7_state()
        self.q7_flatten_submit_attempts += 1
        candidate_order_id = int(self.next_flatten_order_id)
        record = self._pre_flatten_snapshot(
            direction=direction,
            qty=qty,
            candidate_order_id=candidate_order_id,
        )
        self.q7_flatten_forensic_sink.append(record)

        try:
            super()._execute_unique_flatten(direction=direction, qty=qty)
        except m4.M4AdapterError as exc:
            if str(exc) == "flatten_rc:1":
                # Capture is deliberately best-effort so the original M4
                # exception always remains the externally observed failure.
                try:
                    self._after_snapshot(record, failed=True)
                except BaseException as capture_exc:
                    record.setdefault("diagnostic_capture_errors", []).append(
                        {
                            "field": "after_failure_snapshot",
                            "exception_type": type(capture_exc).__name__,
                            "exception_message": str(capture_exc),
                        }
                    )
                record["original_exception_type"] = type(exc).__name__
                record["original_exception_message"] = str(exc)
                record["forensic_classification"] = record["flatten_origin"]
                self.q7_eod_failure_sink.append(deepcopy(record))
            raise

        self._after_snapshot(record, failed=False)
        record["outcome"] = "FLATTEN_COMPLETED"


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "STRATEGY_FLATTEN_EOD_WAIT",
    "TERMINAL_SHUTDOWN_FLATTEN_EOD_WAIT",
    "UNKNOWN_FLATTEN_EOD_WAIT",
    "ELAPSE_RESULT_END_OF_DATA_RC",
    "BACKTEST_ERROR_ORDER_ID_EXIST_RC",
    "EXECUTION_SEMANTICS_CHANGED",
    "STRATEGY_SEMANTICS_CHANGED",
    "FLATTEN_RECOVERY_ENABLED",
    "FLATTEN_RETRY_ENABLED",
    "classify_flatten_origin",
    "FlattenEndOfDataForensicContinuousHistoricalPolicyKernel",
]

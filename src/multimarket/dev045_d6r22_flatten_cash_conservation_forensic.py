from __future__ import annotations

from contextlib import contextmanager
import math
from typing import Any, Callable, Iterator

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r20_q8_terminal_shutdown_grid_alignment_driver as q8
from multimarket import dev045_m4_m6_binding as binding


EXPERIMENT_ID = "DEV045-D6R22-FORENSIC"
DESIGN_VERSION = "flatten-cash-conservation-observational-forensic-v1"

PARENT_FAILURE_FREEZE_HEAD = "cbbbb0572f3408a787272bd06db4bba276500049"
D6R21_EXECUTION_HEAD = "8c0043bb6359fa37147e36fd68c3c2d72243f902"
D6R21_FAILURE_SHA256 = (
    "adbbdd39800145121f860ed584641d00e71add896ab5a98defbf8431a914a3c1"
)
D6R21_FAILURE_EXCEPTION = "flatten_cash_conservation"
JAN_MAX_REPLAY_TRADING_VALUE_ULP = 1.1641532182693481e-10

TARGET_DAY = "2026-02-01"
TARGET_POLICY = "M01"
TARGET_SCENARIO = "Q0_PRIMARY_250_250"

EXECUTION_SEMANTICS_CHANGED = False
STRATEGY_SEMANTICS_CHANGED = False
BINDING_SEMANTICS_CHANGED = False
TOLERANCE_CHANGED = False
ECONOMIC_ACCOUNTING_CHANGED = False
FLATTEN_RETRY_ENABLED = False
AUTOMATIC_RETRY = False
SYNTHETIC_VALIDATION_ALLOWED = True
LIVE_TRADING_AUTHORIZED = False


def _ulp(value: float) -> float:
    x = float(value)
    if not math.isfinite(x):
        return math.inf
    return float(math.ulp(x))


def cash_conservation_diagnostics(
    view,
    *,
    before: binding.ReplayStateView,
    after: binding.ReplayStateView,
) -> dict[str, Any]:
    side = int(view.side)
    if side == int(binding.HFT_BUY):
        side_sign = 1.0
        side_label = "BUY"
    elif side == int(binding.HFT_SELL):
        side_sign = -1.0
        side_label = "SELL"
    else:
        raise binding.M4M6BindingError("side")

    b_position = float(before.position)
    a_position = float(after.position)
    b_balance = float(before.balance)
    a_balance = float(after.balance)
    b_fee = float(before.fee)
    a_fee = float(after.fee)
    b_trades = int(before.num_trades)
    a_trades = int(after.num_trades)
    b_volume = float(before.trading_volume)
    a_volume = float(after.trading_volume)
    b_value = float(before.trading_value)
    a_value = float(after.trading_value)

    qty = a_volume - b_volume
    quote_notional = a_value - b_value
    cash_delta = a_balance - b_balance
    expected_cash_delta = -side_sign * quote_notional
    cash_residual = cash_delta - expected_cash_delta

    original_rel_tol = 1e-12
    original_abs_tol = 1e-12
    original_effective_tolerance = max(
        original_abs_tol,
        original_rel_tol
        * max(abs(cash_delta), abs(expected_cash_delta)),
    )

    endpoint_ulps = {
        "before_balance_ulp": _ulp(b_balance),
        "after_balance_ulp": _ulp(a_balance),
        "before_trading_value_ulp": _ulp(b_value),
        "after_trading_value_ulp": _ulp(a_value),
    }
    endpoint_ulp_budget = math.fsum(endpoint_ulps.values())

    position_delta = a_position - b_position
    expected_position_delta = side_sign * qty

    return {
        "side": side_label,
        "order_id": int(view.order_id),
        "status": int(view.status),
        "final_exec_qty": float(view.exec_qty),
        "final_exec_price_tick": int(view.exec_price_tick),
        "leaves_qty": float(view.leaves_qty),
        "exch_timestamp": int(view.exch_timestamp),
        "local_timestamp": int(view.local_timestamp),
        "before_state": {
            "position": b_position,
            "balance": b_balance,
            "fee": b_fee,
            "num_trades": b_trades,
            "trading_volume": b_volume,
            "trading_value": b_value,
        },
        "after_state": {
            "position": a_position,
            "balance": a_balance,
            "fee": a_fee,
            "num_trades": a_trades,
            "trading_volume": a_volume,
            "trading_value": a_value,
        },
        "position_delta": position_delta,
        "expected_position_delta": expected_position_delta,
        "position_conservation_isclose": math.isclose(
            position_delta,
            expected_position_delta,
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "volume_delta": qty,
        "trading_value_delta": quote_notional,
        "trade_count_delta": a_trades - b_trades,
        "fee_delta": a_fee - b_fee,
        "cash_delta": cash_delta,
        "expected_cash_delta": expected_cash_delta,
        "cash_residual": cash_residual,
        "abs_cash_residual": abs(cash_residual),
        "original_rel_tol": original_rel_tol,
        "original_abs_tol": original_abs_tol,
        "original_effective_tolerance": original_effective_tolerance,
        "original_cash_isclose": math.isclose(
            cash_delta,
            expected_cash_delta,
            rel_tol=original_rel_tol,
            abs_tol=original_abs_tol,
        ),
        **endpoint_ulps,
        "endpoint_ulp_budget": endpoint_ulp_budget,
        "abs_residual_over_endpoint_ulp_budget": (
            abs(cash_residual) / endpoint_ulp_budget
            if endpoint_ulp_budget > 0.0
            else math.inf
        ),
        "abs_residual_over_original_tolerance": (
            abs(cash_residual) / original_effective_tolerance
            if original_effective_tolerance > 0.0
            else math.inf
        ),
        "jan_reference_max_replay_trading_value_ulp": (
            JAN_MAX_REPLAY_TRADING_VALUE_ULP
        ),
    }


@contextmanager
def observe_flatten_cash_binding(
    *,
    sink: list[dict[str, Any]],
    context_factory: Callable[[], dict[str, Any]] | None = None,
) -> Iterator[None]:
    original = base.binding.bind_forced_flatten_from_state_delta

    def observed(view, *, before, after, policy_id, day):
        try:
            return original(
                view,
                before=before,
                after=after,
                policy_id=policy_id,
                day=day,
            )
        except binding.M4M6BindingError as exc:
            if str(exc) == D6R21_FAILURE_EXCEPTION:
                record = cash_conservation_diagnostics(
                    view,
                    before=before,
                    after=after,
                )
                record.update(
                    {
                        "policy_id": policy_id,
                        "day": day,
                        "original_exception_type": type(exc).__name__,
                        "original_exception_message": str(exc),
                        "all_pre_cash_binding_guards_passed": True,
                        "execution_semantics_changed": False,
                        "binding_semantics_changed": False,
                        "tolerance_changed": False,
                        "retry_enabled": False,
                    }
                )
                if context_factory is not None:
                    record.update(context_factory())
                sink.append(record)
            raise

    base.binding.bind_forced_flatten_from_state_delta = observed
    try:
        yield
    finally:
        base.binding.bind_forced_flatten_from_state_delta = original


class FlattenCashConservationForensicKernel(
    q8.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel
):
    """Q8 execution with observational capture around the frozen M4↔M6 bind."""

    def __init__(
        self,
        *args,
        forensic_sink: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.d6r22_forensic_sink = (
            forensic_sink if forensic_sink is not None else []
        )

    def _forensic_context(self) -> dict[str, Any]:
        diagnostics = self.terminal_shutdown_alignment_diagnostics()
        return {
            "scenario": self.scenario,
            "forensic_target_day": TARGET_DAY,
            "forensic_target_policy": TARGET_POLICY,
            "forensic_target_scenario": TARGET_SCENARIO,
            "current_timestamp_ns": int(self.bt.current_timestamp),
            "terminal_shutdown_started": bool(
                self.terminal_shutdown_started
            ),
            "terminal_shutdown_quiescent": bool(
                self.terminal_shutdown_quiescent
            ),
            "flatten_origin": (
                "TERMINAL_SHUTDOWN"
                if self.terminal_shutdown_started
                else "STRATEGY_LIFECYCLE"
            ),
            "q8_alignment": diagnostics,
        }

    def _execute_unique_flatten(self, *, direction: int, qty: float) -> None:
        with observe_flatten_cash_binding(
            sink=self.d6r22_forensic_sink,
            context_factory=self._forensic_context,
        ):
            super()._execute_unique_flatten(direction=direction, qty=qty)


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_FAILURE_FREEZE_HEAD",
    "D6R21_EXECUTION_HEAD",
    "D6R21_FAILURE_SHA256",
    "D6R21_FAILURE_EXCEPTION",
    "JAN_MAX_REPLAY_TRADING_VALUE_ULP",
    "TARGET_DAY",
    "TARGET_POLICY",
    "TARGET_SCENARIO",
    "EXECUTION_SEMANTICS_CHANGED",
    "STRATEGY_SEMANTICS_CHANGED",
    "BINDING_SEMANTICS_CHANGED",
    "TOLERANCE_CHANGED",
    "ECONOMIC_ACCOUNTING_CHANGED",
    "FLATTEN_RETRY_ENABLED",
    "AUTOMATIC_RETRY",
    "cash_conservation_diagnostics",
    "observe_flatten_cash_binding",
    "FlattenCashConservationForensicKernel",
]

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import math
from typing import Any, Iterator

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r20_q8_terminal_shutdown_grid_alignment_driver as q8
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_m6_binding as binding


EXPERIMENT_ID = "DEV045-D6R23"
DESIGN_VERSION = "ulp-aware-flatten-cash-conservation-v1"

PARENT_D6R22_FREEZE_HEAD = "883a4af9ee4ded6319d68a5306412342c1f6e217"
D6R22_RESULT_SHA256 = (
    "a8b55ee5fd5decb3a026393baccad54aa24f1d7d92dfb2a9060b4833def4ccae"
)
D6R22_CLASSIFICATION = (
    "FALSE_POSITIVE_FLATTEN_CASH_CONSERVATION_FROM_FLOAT_LEDGER_DELTA_CANCELLATION"
)

ORIGINAL_REL_TOL = 1e-12
ORIGINAL_ABS_TOL = 1e-12

EXECUTION_SEMANTICS_CHANGED = False
STRATEGY_SEMANTICS_CHANGED = False
FEE_SEMANTICS_CHANGED = False
ECONOMIC_ACCOUNTING_CHANGED = False
RETRY_SEMANTICS_CHANGED = False
AUTOMATIC_RETRY = False
LIVE_TRADING_AUTHORIZED = False

# The binding policy changes only at the already-proven false-positive cash
# conservation guard. All earlier frozen M4↔M6 guards are still executed by
# the exact predecessor function before this fallback can run.
BINDING_GUARD_CHANGE_SCOPE = "FLATTEN_CASH_CONSERVATION_ONLY"
ULP_AWARE_FALLBACK_ENABLED = True
ULP_MULTIPLIER = 1.0

FROZEN_BIND_FORCED_FLATTEN = binding.bind_forced_flatten_from_state_delta


@dataclass(frozen=True)
class CashConservationDecision:
    cash_delta: float
    expected_cash_delta: float
    residual: float
    abs_residual: float
    original_effective_tolerance: float
    before_balance_ulp: float
    after_balance_ulp: float
    before_trading_value_ulp: float
    after_trading_value_ulp: float
    endpoint_ulp_budget: float
    allowed_tolerance: float
    accepted_by_original_tolerance: bool
    accepted_by_ulp_fallback: bool


def _finite_ulp(value: float) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise binding.M4M6BindingError("flatten_cash_ulp_nonfinite")
    return float(math.ulp(x))


def cash_conservation_decision(
    view,
    *,
    before: binding.ReplayStateView,
    after: binding.ReplayStateView,
) -> CashConservationDecision:
    side = int(view.side)
    if side == int(binding.HFT_BUY):
        side_sign = 1.0
    elif side == int(binding.HFT_SELL):
        side_sign = -1.0
    else:
        raise binding.M4M6BindingError("side")

    b_balance = float(before.balance)
    a_balance = float(after.balance)
    b_value = float(before.trading_value)
    a_value = float(after.trading_value)

    for name, value in (
        ("before_balance", b_balance),
        ("after_balance", a_balance),
        ("before_trading_value", b_value),
        ("after_trading_value", a_value),
    ):
        if not math.isfinite(value):
            raise binding.M4M6BindingError(name)

    quote_notional = a_value - b_value
    cash_delta = a_balance - b_balance
    expected_cash_delta = -side_sign * quote_notional
    residual = cash_delta - expected_cash_delta

    original_effective_tolerance = max(
        ORIGINAL_ABS_TOL,
        ORIGINAL_REL_TOL
        * max(abs(cash_delta), abs(expected_cash_delta)),
    )

    before_balance_ulp = _finite_ulp(b_balance)
    after_balance_ulp = _finite_ulp(a_balance)
    before_value_ulp = _finite_ulp(b_value)
    after_value_ulp = _finite_ulp(a_value)

    endpoint_ulp_budget = math.fsum(
        (
            before_balance_ulp,
            after_balance_ulp,
            before_value_ulp,
            after_value_ulp,
        )
    ) * ULP_MULTIPLIER

    allowed_tolerance = max(
        original_effective_tolerance,
        endpoint_ulp_budget,
    )
    abs_residual = abs(residual)

    return CashConservationDecision(
        cash_delta=cash_delta,
        expected_cash_delta=expected_cash_delta,
        residual=residual,
        abs_residual=abs_residual,
        original_effective_tolerance=original_effective_tolerance,
        before_balance_ulp=before_balance_ulp,
        after_balance_ulp=after_balance_ulp,
        before_trading_value_ulp=before_value_ulp,
        after_trading_value_ulp=after_value_ulp,
        endpoint_ulp_budget=endpoint_ulp_budget,
        allowed_tolerance=allowed_tolerance,
        accepted_by_original_tolerance=(
            abs_residual <= original_effective_tolerance
        ),
        accepted_by_ulp_fallback=(
            abs_residual > original_effective_tolerance
            and abs_residual <= allowed_tolerance
        ),
    )


def _complete_binding_after_cash_guard(
    view,
    *,
    before: binding.ReplayStateView,
    after: binding.ReplayStateView,
    policy_id: str,
    day: str,
):
    side_raw = int(view.side)
    side = "BUY" if side_raw == int(binding.HFT_BUY) else "SELL"
    side_sign = 1.0 if side == "BUY" else -1.0

    qty = float(after.trading_volume) - float(before.trading_volume)
    quote_notional = float(after.trading_value) - float(before.trading_value)

    # These checks duplicate only the post-cash tail of the frozen binding.
    # Every pre-cash check has already passed in FROZEN_BIND_FORCED_FLATTEN.
    price = quote_notional / qty
    if not math.isfinite(price) or price <= 0.0:
        raise binding.M4M6BindingError("flatten_vwap")

    timestamp_ns = int(view.exch_timestamp)
    final_exec_price_tick = int(view.exec_price_tick)

    fill = binding.FillRecord(
        policy_id=policy_id,
        day=day,
        timestamp_ns=timestamp_ns,
        side=side,
        qty=qty,
        price=price,
        liquidity=binding.TAKER,
    )

    if not math.isclose(
        float(fill.qty) * float(fill.price),
        quote_notional,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise binding.M4M6BindingError("flatten_notional_conservation")

    # Preserve the predecessor return surface exactly.
    return binding.BoundReplayEvent(
        kind=binding.FILL,
        policy_id=policy_id,
        day=day,
        order_id=int(view.order_id),
        timestamp_ns=timestamp_ns,
        side=side,
        liquidity=binding.TAKER,
        exec_qty=qty,
        exec_price_tick=final_exec_price_tick,
        executed_quote_notional=quote_notional,
        fill=fill,
    )


def bind_forced_flatten_from_state_delta_ulp_aware(
    view,
    *,
    before: binding.ReplayStateView,
    after: binding.ReplayStateView,
    policy_id: str,
    day: str,
    diagnostic_sink: list[dict[str, Any]] | None = None,
):
    try:
        return FROZEN_BIND_FORCED_FLATTEN(
            view,
            before=before,
            after=after,
            policy_id=policy_id,
            day=day,
        )
    except binding.M4M6BindingError as exc:
        if str(exc) != "flatten_cash_conservation":
            raise

        decision = cash_conservation_decision(
            view,
            before=before,
            after=after,
        )

        record = {
            "day": day,
            "policy_id": policy_id,
            "order_id": int(view.order_id),
            "side": "BUY" if int(view.side) == int(binding.HFT_BUY) else "SELL",
            "original_exception": str(exc),
            "cash_delta": decision.cash_delta,
            "expected_cash_delta": decision.expected_cash_delta,
            "residual": decision.residual,
            "abs_residual": decision.abs_residual,
            "original_effective_tolerance": decision.original_effective_tolerance,
            "before_balance_ulp": decision.before_balance_ulp,
            "after_balance_ulp": decision.after_balance_ulp,
            "before_trading_value_ulp": decision.before_trading_value_ulp,
            "after_trading_value_ulp": decision.after_trading_value_ulp,
            "endpoint_ulp_budget": decision.endpoint_ulp_budget,
            "allowed_tolerance": decision.allowed_tolerance,
            "accepted_by_original_tolerance": decision.accepted_by_original_tolerance,
            "accepted_by_ulp_fallback": decision.accepted_by_ulp_fallback,
            "ulp_multiplier": ULP_MULTIPLIER,
        }

        if diagnostic_sink is not None:
            diagnostic_sink.append(record)

        if not decision.accepted_by_ulp_fallback:
            raise

        return _complete_binding_after_cash_guard(
            view,
            before=before,
            after=after,
            policy_id=policy_id,
            day=day,
        )


@contextmanager
def use_ulp_aware_flatten_binding(
    *,
    diagnostic_sink: list[dict[str, Any]] | None = None,
) -> Iterator[None]:
    original = base.binding.bind_forced_flatten_from_state_delta

    def patched(view, *, before, after, policy_id, day):
        return bind_forced_flatten_from_state_delta_ulp_aware(
            view,
            before=before,
            after=after,
            policy_id=policy_id,
            day=day,
            diagnostic_sink=diagnostic_sink,
        )

    base.binding.bind_forced_flatten_from_state_delta = patched
    try:
        yield
    finally:
        base.binding.bind_forced_flatten_from_state_delta = original


class UlpAwareFlattenCashContinuousHistoricalPolicyKernel(
    q8.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel
):
    """Exact Q8 execution with only the D6R23 M4↔M6 cash-guard successor."""

    def __init__(
        self,
        *args,
        cash_guard_diagnostics: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.d6r23_cash_guard_diagnostics = (
            cash_guard_diagnostics
            if cash_guard_diagnostics is not None
            else []
        )

    def _execute_unique_flatten(self, *, direction: int, qty: float) -> None:
        with use_ulp_aware_flatten_binding(
            diagnostic_sink=self.d6r23_cash_guard_diagnostics
        ):
            super()._execute_unique_flatten(direction=direction, qty=qty)


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_D6R22_FREEZE_HEAD",
    "D6R22_RESULT_SHA256",
    "D6R22_CLASSIFICATION",
    "ORIGINAL_REL_TOL",
    "ORIGINAL_ABS_TOL",
    "EXECUTION_SEMANTICS_CHANGED",
    "STRATEGY_SEMANTICS_CHANGED",
    "FEE_SEMANTICS_CHANGED",
    "ECONOMIC_ACCOUNTING_CHANGED",
    "RETRY_SEMANTICS_CHANGED",
    "AUTOMATIC_RETRY",
    "LIVE_TRADING_AUTHORIZED",
    "BINDING_GUARD_CHANGE_SCOPE",
    "ULP_AWARE_FALLBACK_ENABLED",
    "ULP_MULTIPLIER",
    "CashConservationDecision",
    "cash_conservation_decision",
    "bind_forced_flatten_from_state_delta_ulp_aware",
    "use_ulp_aware_flatten_binding",
    "UlpAwareFlattenCashContinuousHistoricalPolicyKernel",
]

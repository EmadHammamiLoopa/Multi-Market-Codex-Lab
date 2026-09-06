from __future__ import annotations

import math

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r19_response_batch_replacement_driver as d6r19
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket import dev045_m6_event_loop_kernel as d2
from multimarket.dev044_t0_strategy_contract import LONG, SHORT


EXPERIMENT_ID = "DEV045-D6R20"
DESIGN_VERSION = "execution-time-residual-forced-flatten-v1"

CANONICAL_RUNNER_IMPLEMENTED = False
CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT = False
CANONICAL_ATTEMPT_CONSUMED = False
AUTOMATIC_RETRY = False
CANONICAL_PNL_WRITE_ENABLED = False
NETWORK_ACQUISITION_ENABLED = False
RAILWAY_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

SYNTHETIC_VALIDATION_ALLOWED = True


class ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel(
    d6r19.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel
):
    """
    D6R20 successor with execution-time residual forced-flatten sizing.

    The frozen policy decision remains the liquidation trigger and latch.
    Quote cancellation, unique forced-order execution, M4 submission, M6 fill
    binding, inventory observation, and lifecycle reset remain inherited.
    Only the eventual taker direction and quantity are derived afresh from the
    actual residual position after every maker quote slot is clear.
    """

    def _maybe_execute_forced_flatten(self) -> None:
        if self.flatten_done:
            return

        if self.force_decision is None:
            return

        if not self._all_quote_slots_clear():
            return

        position = float(self.bt.position(d2.ASSET_NO))

        if not math.isfinite(position):
            raise base.RealHistoricalDriverError(
                "force_flatten_residual_position_nonfinite"
            )

        if abs(position) <= 1e-15:
            self.flatten_done = True
            self.inventory_clock = d1.InventoryClock.flat()
            self.flatten_response_local_ns = int(
                self.bt.current_timestamp
            )
        else:
            direction = SHORT if position > 0.0 else LONG
            quantity = abs(position)

            self._execute_unique_flatten(
                direction=direction,
                qty=quantity,
            )
            self.flatten_done = True

        if not self.flatten_done:
            return

        position = float(self.bt.position(d2.ASSET_NO))

        if abs(position) > 1e-12:
            raise base.RealHistoricalDriverError(
                "completed_flatten_nonflat"
            )

        if not self._all_quote_slots_clear():
            raise base.RealHistoricalDriverError(
                "completed_flatten_quotes_not_clear"
            )

        self.completed_forced_flattens += 1

        self.force_decision = None
        self.flatten_done = False

        self.flatten_decision_local_ns = None
        self.flatten_response_local_ns = None
        self.first_nonzero_inventory_local_ns = None
        self.maker_local_response_ns = None


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "CANONICAL_RUNNER_IMPLEMENTED",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "AUTOMATIC_RETRY",
    "ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel",
]

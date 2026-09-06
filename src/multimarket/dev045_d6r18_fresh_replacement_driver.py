from __future__ import annotations

from dataclasses import dataclass

from multimarket import dev045_d6r17_direct_action_driver_bridge as bridge
from multimarket import dev045_d6r17_direct_action_support as direct
from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m6_event_loop_kernel as d2
from multimarket import dev045_m6_policy_integration as d3


EXPERIMENT_ID = "DEV045-D6R18"
DESIGN_VERSION = "fresh-cancel-response-replacement-semantics-v1"

CANONICAL_SOURCE_OPEN_IMPLEMENTED = False
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


class FreshReplacementError(RuntimeError):
    pass


@dataclass
class FreshReplacementSideSlot:
    """One working side plus a target-free cancel/replace intent."""

    side: str
    order_id: int | None = None
    last_leaves_qty: float = 0.0
    replacement_required: bool = False

    def active(self) -> bool:
        return self.order_id is not None

    @property
    def pending_replacement(self) -> None:
        """Compatibility surface that can never hold a PolicyDecision."""
        return None

    @pending_replacement.setter
    def pending_replacement(self, value: object) -> None:
        # Frozen inherited shutdown/submission paths clear this name.  A
        # non-None assignment would reintroduce the D6R17 defect, so fail
        # closed instead of retaining it.
        if value is not None:
            raise FreshReplacementError(
                "stale_pending_replacement_forbidden"
            )

        self.replacement_required = False


class FreshReplacementContinuousHistoricalPolicyKernel(
    bridge.DirectActionContinuousHistoricalPolicyKernel
):
    """
    D6R18 successor with fresh cancel-response replacement decisions.

    D6R17 stores an entire PolicyDecision while a cancel is in flight.
    D6R18 stores only a boolean intent.  After the acknowledgement clears
    the old slot, it reconstructs current MarketState and enters the normal
    empty-slot maintenance path with a newly evaluated decision.

    For M06/M07, a response-time refresh uses only the currently active
    direction integer.  Frozen support remains queryable solely by the
    one-second policy clock, so this path cannot forward-fill, backfill,
    interpolate, rematerialize legacy state, or invent an A0 observation.
    """

    def __init__(
        self,
        *,
        bt,
        h,
        policy_id: str,
        day: str,
        scenario: str,
        terminal_source_local_ns: int,
        direct_index: direct.DirectActionIndex | None = None,
    ) -> None:
        super().__init__(
            bt=bt,
            h=h,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            terminal_source_local_ns=terminal_source_local_ns,
            direct_index=direct_index,
        )

        self.bid = FreshReplacementSideSlot("bid")
        self.ask = FreshReplacementSideSlot("ask")
        self.fresh_replacement_evaluations = 0

    def _request_cancel(
        self,
        *,
        slot: FreshReplacementSideSlot,
        replacement: p.PolicyDecision | None,
    ) -> None:
        replacement_required = replacement is not None

        # Reuse every frozen cancel validation and latency action, but pass
        # no decision into storage.  Only the boolean is retained afterward.
        super()._request_cancel(
            slot=slot,
            replacement=None,
        )
        slot.replacement_required = replacement_required

    def _fresh_policy_decision(
        self,
        *,
        local_timestamp_ns: int,
    ) -> p.PolicyDecision:
        state = self._dynamic_market_state(
            local_timestamp_ns=local_timestamp_ns
        )

        if self.policy_id in bridge.ADAPTER_POLICIES:
            # Same-timestamp order responses precede the frozen policy timer.
            # Consume only the direction legitimately active at this point;
            # the timer remains the only path allowed to query exact support.
            decision = d3.decision_from_active_adapter_direction(
                policy_id=self.policy_id,
                state=state,
                active_direction=self.active_adapter_direction,
            )
        else:
            decision = p.policy_decision(
                self.policy_id,
                state,
            )

        self.fresh_replacement_evaluations += 1
        return decision

    def _replacement_is_blocked(self) -> bool:
        return bool(
            self.force_decision is not None
            or self.terminal_shutdown_started
        )

    def _handle_fresh_replacement(
        self,
        *,
        side: str,
        local_response_ns: int,
    ) -> None:
        if self._replacement_is_blocked():
            return

        decision = self._fresh_policy_decision(
            local_timestamp_ns=local_response_ns
        )

        if decision.force_flatten:
            if self.flatten_decision_local_ns is None:
                self.flatten_decision_local_ns = int(
                    local_response_ns
                )

            self._force_cancel_quotes(decision)
            self._maybe_execute_forced_flatten()
            return

        # The inherited empty-slot path applies the frozen maintenance rules,
        # then frozen M4 validates the unmodified target against the live book.
        self._maintain_side(
            side=side,
            decision=decision,
        )

    def _process_response_batch(
        self,
        *,
        local_response_ns: int,
    ) -> None:
        self.response_sequence += 1
        seq = int(self.response_sequence)

        for slot in (self.bid, self.ask):
            if slot.order_id is None:
                continue

            raw = self.bt.orders(d2.ASSET_NO).get(
                int(slot.order_id)
            )

            if raw is None:
                raise d2.EventLoopKernelError(
                    "response_order_missing"
                )

            status = int(raw.status)
            req = int(raw.req)

            if status in (
                int(d2.HFT_PARTIALLY_FILLED),
                int(d2.HFT_FILLED),
            ):
                self._bind_new_execution(
                    slot=slot,
                    raw=raw,
                    local_response_ns=local_response_ns,
                )

            if status == int(d2.HFT_FILLED):
                slot.order_id = None
                slot.replacement_required = False
                slot.last_leaves_qty = 0.0
                continue

            if (
                status in (
                    int(d2.HFT_CANCELED),
                    int(d2.HFT_EXPIRED),
                )
                and req == int(d2.HFT_NONE)
            ):
                replacement_required = bool(
                    slot.replacement_required
                )

                # Cancel-before-replace: clear the acknowledged old order
                # before calculating or optionally submitting anything new.
                slot.order_id = None
                slot.replacement_required = False
                slot.last_leaves_qty = 0.0

                if replacement_required:
                    self._handle_fresh_replacement(
                        side=slot.side,
                        local_response_ns=local_response_ns,
                    )

        self.response_ledger = self.response_ledger.consume(seq)


def run_bound_verified_replay(
    source,
    *,
    policy_id: str,
    day: str,
    scenario: str,
    direct_index: direct.DirectActionIndex | None = None,
    initial_snapshot=None,
) -> bridge.DirectActionReplayResult:
    """Run the D6R18 kernel over a caller-owned, already-verified source."""
    bridge.validate_direct_index(
        policy_id=policy_id,
        day=day,
        index=direct_index,
    )

    import hftbacktest as h

    asset = base._build_asset_from_verified_source(
        source,
        scenario=scenario,
        initial_snapshot=initial_snapshot,
    )
    bt = h.HashMapMarketDepthBacktest([asset])

    try:
        terminal_source_local_ns = int(
            source.data[-1]["local_ts"]
        )

        kernel = FreshReplacementContinuousHistoricalPolicyKernel(
            bt=bt,
            h=h,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            terminal_source_local_ns=terminal_source_local_ns,
            direct_index=direct_index,
        )

        replay = kernel.run_full_day()

        return bridge.DirectActionReplayResult(
            replay=replay,
            direct_action_queries=int(
                kernel.direct_action_queries
            ),
            direct_action_rows_found=int(
                kernel.direct_action_rows_found
            ),
            direct_action_missing_rows=int(
                kernel.direct_action_missing_rows
            ),
            direct_action_explicit_abstains=int(
                kernel.direct_action_explicit_abstains
            ),
        )
    finally:
        rc = int(bt.close())

        if rc != 0:
            raise FreshReplacementError(
                f"backtest_close_rc:{rc}"
            )


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "CANONICAL_SOURCE_OPEN_IMPLEMENTED",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "AUTOMATIC_RETRY",
    "FreshReplacementError",
    "FreshReplacementSideSlot",
    "FreshReplacementContinuousHistoricalPolicyKernel",
    "run_bound_verified_replay",
]

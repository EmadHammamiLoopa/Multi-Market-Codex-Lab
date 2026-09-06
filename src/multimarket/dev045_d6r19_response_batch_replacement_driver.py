from __future__ import annotations

import math

from multimarket import dev045_d6r18_fresh_replacement_driver as d6r18
from multimarket import dev045_m6_event_loop_kernel as d2


EXPERIMENT_ID = "DEV045-D6R19"
DESIGN_VERSION = "response-batch-coherent-fresh-replacement-v1"

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


class ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel(
    d6r18.FreshReplacementContinuousHistoricalPolicyKernel
):
    """
    D6R19 successor with response-batch-coherent replacement refreshes.

    Phase 1 consumes execution deltas and acknowledged lifecycle changes for
    both quote slots.  It retains only the sides whose acknowledged cancels
    still require replacement.  Phase 2 evaluates those replacements against
    current state, after every execution in the batch has updated the frozen
    inventory clock through the inherited fill-binding path.

    All quote construction, support-clock semantics, passivity validation,
    latency, accounting, forced flatten, and terminal behavior remain
    inherited unchanged.
    """

    def _require_response_inventory_coherence(self) -> None:
        if not math.isclose(
            float(self.bt.position(d2.ASSET_NO)),
            float(self.inventory_clock.position),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            # Preserve the frozen invariant and its exact failure identity.
            # Coherence may only arise from inherited execution binding; this
            # method never assigns either inventory representation.
            raise d2.EventLoopKernelError(
                "local_inventory_clock_mismatch"
            )

    def _process_response_batch(
        self,
        *,
        local_response_ns: int,
    ) -> None:
        self.response_sequence += 1
        seq = int(self.response_sequence)

        replacement_sides: list[str] = []
        responses: list[
            tuple[
                d6r18.FreshReplacementSideSlot,
                object,
                int,
                int,
            ]
        ] = []

        # Snapshot both raw response views before applying any lifecycle
        # changes to the strategy-owned slots.
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
            responses.append((slot, raw, status, req))

        # Phase 1a: bind every execution delta in the complete response batch.
        # This is the only operation here that advances the inventory clock.
        for slot, raw, status, _req in responses:
            if status in (
                int(d2.HFT_PARTIALLY_FILLED),
                int(d2.HFT_FILLED),
            ):
                self._bind_new_execution(
                    slot=slot,
                    raw=raw,
                    local_response_ns=local_response_ns,
                )

        # Phase 1b: only after all execution binding is complete, consume all
        # acknowledged slot lifecycles and collect target-free side intents.
        # No fresh policy decision or submission is permitted in this loop.
        for slot, _raw, status, req in responses:
            if status == int(d2.HFT_FILLED):
                # A fill wins over any stale target-free replacement intent.
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

                # Cancel-before-replace remains strict: the acknowledged old
                # slot is cleared during Phase 1, while only its side survives
                # as target-free intent for Phase 2.
                slot.order_id = None
                slot.replacement_required = False
                slot.last_leaves_qty = 0.0

                if replacement_required:
                    replacement_sides.append(slot.side)

        # Phase 2: only now may current state be reconstructed and the frozen
        # policy reevaluated.  The explicit check adds no synchronization; it
        # proves inherited execution binding has made the two views coherent.
        for side in replacement_sides:
            if self._replacement_is_blocked():
                continue

            self._require_response_inventory_coherence()
            self._handle_fresh_replacement(
                side=side,
                local_response_ns=local_response_ns,
            )

        self.response_ledger = self.response_ledger.consume(seq)


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "CANONICAL_RUNNER_IMPLEMENTED",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "AUTOMATIC_RETRY",
    "ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel",
]

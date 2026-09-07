from __future__ import annotations

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r20_residual_flatten_driver as d6r20
from multimarket import dev045_m6_event_loop_contract as d1


EXPERIMENT_ID = "DEV045-D6R20-Q4"
DESIGN_VERSION = "blocking-wait-policy-clock-reconciliation-v1"

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


def reconcile_policy_target_after_blocking_wait(
    *,
    current_local_ns: int,
    next_policy_ns: int,
) -> int:
    """Reconcile a base-policy target after a synchronous engine wait.

    An equal target remains eligible because the response that advanced the
    clock has already been applied. Missed targets are never replayed: an
    exact current base epoch is retained, otherwise the frozen D1 helper
    supplies the strictly next base epoch.
    """
    current = int(current_local_ns)
    target = int(next_policy_ns)

    if current < 0 or target < 0:
        raise base.RealHistoricalDriverError(
            "q4_negative_scheduler_timestamp"
        )

    if not d1.is_base_policy_epoch_local(target):
        raise base.RealHistoricalDriverError(
            "q4_policy_target_not_base_epoch"
        )

    if current <= target:
        return target

    if d1.is_base_policy_epoch_local(current):
        reconciled = current
    else:
        reconciled = d1.next_base_policy_epoch_after(current)

    if reconciled < current:
        raise base.RealHistoricalDriverError(
            "q4_reconciled_policy_target_in_past"
        )

    if not d1.is_base_policy_epoch_local(reconciled):
        raise base.RealHistoricalDriverError(
            "q4_reconciled_target_not_base_epoch"
        )

    return int(reconciled)


class SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel(
    d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
):
    """D6R20 execution with causal reconciliation after blocking waits."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.q4_policy_epoch_timestamps: list[int] = []
        self.q4_skipped_policy_epochs = 0

    def _evaluate_policy_epoch(
        self,
        *,
        local_timestamp_ns: int,
    ) -> None:
        timestamp = int(local_timestamp_ns)
        current = int(self.bt.current_timestamp)

        if timestamp < current:
            raise base.RealHistoricalDriverError(
                "q4_policy_epoch_before_current"
            )

        if timestamp != current:
            raise base.RealHistoricalDriverError(
                "q4_policy_epoch_not_current"
            )

        if not d1.is_base_policy_epoch_local(timestamp):
            raise base.RealHistoricalDriverError(
                "q4_policy_epoch_not_base_epoch"
            )

        if (
            self.q4_policy_epoch_timestamps
            and timestamp <= self.q4_policy_epoch_timestamps[-1]
        ):
            raise base.RealHistoricalDriverError(
                "q4_policy_epoch_not_strictly_monotonic"
            )

        self.q4_policy_epoch_timestamps.append(timestamp)
        super()._evaluate_policy_epoch(
            local_timestamp_ns=timestamp,
        )

    def _reconcile_policy_target(
        self,
        *,
        current_local_ns: int,
        next_policy_ns: int,
    ) -> int:
        reconciled = reconcile_policy_target_after_blocking_wait(
            current_local_ns=current_local_ns,
            next_policy_ns=next_policy_ns,
        )

        if reconciled > int(next_policy_ns):
            skipped = (
                reconciled - int(next_policy_ns)
            ) // int(d1.BASE_MAKER_STEP_NS)
            self.q4_skipped_policy_epochs += int(skipped)

        return reconciled

    def _consume_due_policy_target(
        self,
        *,
        next_policy_ns: int,
    ) -> int:
        now = int(self.bt.current_timestamp)

        if now != int(next_policy_ns):
            raise base.RealHistoricalDriverError(
                "q4_policy_target_not_due"
            )

        if (
            self.terminal_shutdown_started
            or now >= self.terminal_shutdown_cutoff_ns
        ):
            self._begin_terminal_shutdown(
                local_timestamp_ns=now,
            )
        else:
            self._evaluate_policy_epoch(
                local_timestamp_ns=now,
            )

            if self.policy_epochs > base.MAX_POLICY_EPOCHS_PER_DAY:
                raise base.RealHistoricalDriverError(
                    "policy_epoch_guard"
                )

        after = int(self.bt.current_timestamp)

        if after < now:
            raise base.RealHistoricalDriverError(
                "local_clock_reversal"
            )

        following_target = (
            int(next_policy_ns) + int(d1.BASE_MAKER_STEP_NS)
        )
        return self._reconcile_policy_target(
            current_local_ns=after,
            next_policy_ns=following_target,
        )

    def run_full_day(self) -> base.ContinuousReplayResult:
        rc = int(
            self.bt.wait_next_feed(
                True,
                base.INITIAL_FEED_TIMEOUT_NS,
            )
        )

        if rc != 2:
            raise base.RealHistoricalDriverError(
                f"initial_feed_rc:{rc}"
            )

        self.market_wakeups += 1
        self._capture_last_trades()

        next_policy_ns = d1.next_base_policy_epoch_after(
            int(self.bt.current_timestamp)
        )

        while True:
            now = int(self.bt.current_timestamp)

            if now > next_policy_ns:
                raise base.RealHistoricalDriverError(
                    "policy_epoch_skipped"
                )

            # Policy timer after all local-visible events already consumed at
            # this timestamp. The helper reconciles if this policy operation
            # performs a synchronous forced-flatten wait.
            if now == next_policy_ns:
                next_policy_ns = self._consume_due_policy_target(
                    next_policy_ns=next_policy_ns,
                )
                continue

            timeout = next_policy_ns - now
            before = now
            rc = int(
                self.bt.wait_next_feed(
                    True,
                    int(timeout),
                )
            )
            now = int(self.bt.current_timestamp)

            if now < before:
                raise base.RealHistoricalDriverError(
                    "local_clock_reversal"
                )

            if rc == 1:
                self.natural_end_of_data = True
                self.terminal_local_timestamp_ns = now
                break

            if rc == 2:
                self.market_wakeups += 1
                self._capture_last_trades()

            elif rc == 3:
                self.response_wakeups += 1
                self._process_response_batch(
                    local_response_ns=now,
                )

                if self.terminal_shutdown_started:
                    self._advance_terminal_shutdown()
                else:
                    self._maybe_execute_forced_flatten()

                after_response = int(self.bt.current_timestamp)

                if after_response < now:
                    raise base.RealHistoricalDriverError(
                        "local_clock_reversal"
                    )

                next_policy_ns = self._reconcile_policy_target(
                    current_local_ns=after_response,
                    next_policy_ns=next_policy_ns,
                )
                now = after_response

            elif rc == 0:
                pass

            else:
                raise base.RealHistoricalDriverError(
                    f"unexpected_wait_rc:{rc}"
                )

            # Feed waits retain the frozen fail-closed overshoot check. Only
            # the known synchronous response/flatten path reconciles targets.
            if now > next_policy_ns:
                raise base.RealHistoricalDriverError(
                    "wake_after_policy_target"
                )

            if now == next_policy_ns:
                next_policy_ns = self._consume_due_policy_target(
                    next_policy_ns=next_policy_ns,
                )

        if not self.natural_end_of_data:
            raise base.RealHistoricalDriverError(
                "natural_eod_missing"
            )

        terminal_position = float(self.bt.position(0))
        active_slots = int(self.bid.order_id is not None) + int(
            self.ask.order_id is not None
        )

        if not self.terminal_shutdown_started:
            raise base.RealHistoricalDriverError(
                "terminal_shutdown_not_started"
            )

        if not self.terminal_shutdown_quiescent:
            raise base.RealHistoricalDriverError(
                "terminal_shutdown_not_quiescent"
            )

        if abs(terminal_position) > 1e-12:
            raise base.RealHistoricalDriverError(
                f"end_of_data_nonflat:{terminal_position}"
            )

        if active_slots != 0:
            raise base.RealHistoricalDriverError(
                f"end_of_data_working_quotes:{active_slots}"
            )

        fill_records = []
        maker_fill_count = 0
        taker_fill_count = 0

        for event in self.bound_fills:
            if event.kind != "FILL":
                continue

            if event.fill is None:
                raise base.RealHistoricalDriverError(
                    "fill_event_without_record"
                )

            fill_records.append(event.fill)

            if event.fill.liquidity == "MAKER":
                maker_fill_count += 1
            elif event.fill.liquidity == "TAKER":
                taker_fill_count += 1
            else:
                raise base.RealHistoricalDriverError(
                    "unknown_liquidity"
                )

        if fill_records:
            cycles = tuple(
                base.m6.account_fill_bucket(
                    fill_records,
                    scenario=self.scenario,
                )
            )
        else:
            cycles = ()

        audit = base.m6.ReplayAudit(
            policy_id=self.policy_id,
            day=self.day,
            scenario=self.scenario,
            execution_integrity_failures=0,
            terminal_flat=True,
        )

        return base.ContinuousReplayResult(
            policy_id=self.policy_id,
            day=self.day,
            scenario=self.scenario,
            cycles=cycles,
            audit=audit,
            natural_end_of_data=True,
            terminal_local_timestamp_ns=int(
                self.terminal_local_timestamp_ns
            ),
            market_wakeups=int(self.market_wakeups),
            response_wakeups=int(self.response_wakeups),
            policy_epochs=int(self.policy_epochs),
            submit_requests=int(self.submit_requests),
            cancel_requests=int(self.cancel_requests),
            maker_fill_count=int(maker_fill_count),
            taker_fill_count=int(taker_fill_count),
            total_fill_count=int(len(fill_records)),
            forced_flatten_count=int(self.completed_forced_flattens),
            flatten_order_ids=tuple(
                int(x) for x in self.flatten_order_ids
            ),
            terminal_position=terminal_position,
            terminal_flat=True,
            terminal_working_quote_slots=active_slots,
            terminal_shutdown_started=bool(
                self.terminal_shutdown_started
            ),
            terminal_shutdown_quiescent=bool(
                self.terminal_shutdown_quiescent
            ),
            terminal_source_local_ns=int(self.terminal_source_local_ns),
            terminal_shutdown_cutoff_ns=int(
                self.terminal_shutdown_cutoff_ns
            ),
            terminal_shutdown_start_ns=(
                int(self.terminal_shutdown_start_ns)
                if self.terminal_shutdown_start_ns is not None
                else None
            ),
            terminal_shutdown_cancel_requests=int(
                self.terminal_shutdown_cancel_requests
            ),
            adapter_candidate_epochs=int(self.adapter_candidate_epochs),
            legacy_state_queries=int(self.legacy_state_queries),
            exact_minute_identity_checks=int(
                self.exact_minute_identity_checks
            ),
        )


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "CANONICAL_RUNNER_IMPLEMENTED",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "AUTOMATIC_RETRY",
    "reconcile_policy_target_after_blocking_wait",
    "SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel",
]

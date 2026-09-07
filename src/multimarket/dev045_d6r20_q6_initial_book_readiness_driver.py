from __future__ import annotations

from collections import deque

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r20_q4_scheduler_reconciled_driver as q4
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket import dev045_m6_event_loop_kernel as d2


EXPERIMENT_ID = "DEV045-D6R20-Q6"
DESIGN_VERSION = "initial-local-book-readiness-gate-v1"

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
EMPTY_ASK_TICK = 2**63 - 1
STARTUP_READINESS_OBSERVATION_LIMIT = 256


def local_book_is_ready(*, best_bid_tick: int, best_ask_tick: int) -> bool:
    return bool(
        int(best_bid_tick) > 0
        and int(best_ask_tick) < EMPTY_ASK_TICK
        and int(best_ask_tick) > int(best_bid_tick)
    )


class InitialBookReadinessContinuousHistoricalPolicyKernel(
    q4.SchedulerReconciledExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
):
    """Frozen Q4 execution with a startup-only two-sided-book gate."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.initial_book_ready = False
        self.initial_book_ready_local_ns: int | None = None
        self.startup_policy_epochs_skipped = 0
        self.startup_policy_epoch_timestamps_skipped: list[int] = []
        self.first_policy_epoch_executed: int | None = None
        self.initial_book_readiness_observations = deque(
            maxlen=STARTUP_READINESS_OBSERVATION_LIMIT
        )

    def _ensure_initial_book_readiness_state(self) -> None:
        if hasattr(self, "initial_book_ready"):
            return

        self.initial_book_ready = False
        self.initial_book_ready_local_ns = None
        self.startup_policy_epochs_skipped = 0
        self.startup_policy_epoch_timestamps_skipped = []
        self.first_policy_epoch_executed = None
        self.initial_book_readiness_observations = deque(
            maxlen=STARTUP_READINESS_OBSERVATION_LIMIT
        )

    def _observe_initial_book_readiness(
        self,
        *,
        local_timestamp_ns: int,
    ) -> bool:
        self._ensure_initial_book_readiness_state()

        if self.initial_book_ready:
            return True

        depth = self.bt.depth(d2.ASSET_NO)
        bid_tick = int(depth.best_bid_tick)
        ask_tick = int(depth.best_ask_tick)
        ready_now = local_book_is_ready(
            best_bid_tick=bid_tick,
            best_ask_tick=ask_tick,
        )
        self.initial_book_readiness_observations.append(
            (
                int(local_timestamp_ns),
                bid_tick,
                ask_tick,
                ready_now,
            )
        )

        if not self.initial_book_ready and ready_now:
            self.initial_book_ready = True
            self.initial_book_ready_local_ns = int(local_timestamp_ns)

        return bool(self.initial_book_ready)

    def _capture_last_trades(self) -> None:
        super()._capture_last_trades()
        self._observe_initial_book_readiness(
            local_timestamp_ns=int(self.bt.current_timestamp),
        )

    def _evaluate_policy_epoch(
        self,
        *,
        local_timestamp_ns: int,
    ) -> None:
        self._ensure_initial_book_readiness_state()
        timestamp = int(local_timestamp_ns)

        if not self.initial_book_ready:
            raise base.RealHistoricalDriverError(
                "q6_policy_before_initial_book_ready"
            )

        ready_timestamp = self.initial_book_ready_local_ns

        if ready_timestamp is None or timestamp < int(ready_timestamp):
            raise base.RealHistoricalDriverError(
                "q6_retroactive_startup_policy"
            )

        super()._evaluate_policy_epoch(
            local_timestamp_ns=timestamp,
        )

        if self.first_policy_epoch_executed is None:
            self.first_policy_epoch_executed = timestamp

    def _consume_due_policy_target(
        self,
        *,
        next_policy_ns: int,
    ) -> int:
        self._ensure_initial_book_readiness_state()
        now = int(self.bt.current_timestamp)
        target = int(next_policy_ns)

        if now != target:
            raise base.RealHistoricalDriverError(
                "q6_policy_target_not_due"
            )

        # Re-read actual simulator depth at the decision boundary. This does
        # not infer readiness from a row/event flag and permits a complete
        # same-timestamp depth update to precede the policy exactly once.
        self._observe_initial_book_readiness(
            local_timestamp_ns=now,
        )

        if (
            not self.initial_book_ready
            and not self.terminal_shutdown_started
            and now < self.terminal_shutdown_cutoff_ns
        ):
            self.startup_policy_epochs_skipped += 1
            self.startup_policy_epoch_timestamps_skipped.append(target)
            following_target = target + int(d1.BASE_MAKER_STEP_NS)
            return self._reconcile_policy_target(
                current_local_ns=now,
                next_policy_ns=following_target,
            )

        return super()._consume_due_policy_target(
            next_policy_ns=target,
        )

    def startup_readiness_diagnostics(self) -> dict:
        self._ensure_initial_book_readiness_state()
        ready_ns = self.initial_book_ready_local_ns
        first_policy_ns = self.first_policy_epoch_executed
        skipped = tuple(
            int(value)
            for value in self.startup_policy_epoch_timestamps_skipped
        )
        no_retroactive = bool(
            ready_ns is not None
            and first_policy_ns is not None
            and int(first_policy_ns) >= int(ready_ns)
            and int(first_policy_ns) not in skipped
            and all(value < int(first_policy_ns) for value in skipped)
        )
        return {
            "initial_book_ready_timestamp": (
                int(ready_ns) if ready_ns is not None else None
            ),
            "startup_policy_epochs_skipped": int(
                self.startup_policy_epochs_skipped
            ),
            "startup_policy_epoch_timestamps_skipped": skipped,
            "first_policy_epoch_executed": (
                int(first_policy_ns)
                if first_policy_ns is not None
                else None
            ),
            "no_retroactive_startup_policy": no_retroactive,
        }


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "CANONICAL_RUNNER_IMPLEMENTED",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "AUTOMATIC_RETRY",
    "SYNTHETIC_VALIDATION_ALLOWED",
    "EMPTY_ASK_TICK",
    "STARTUP_READINESS_OBSERVATION_LIMIT",
    "local_book_is_ready",
    "InitialBookReadinessContinuousHistoricalPolicyKernel",
]

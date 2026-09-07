from __future__ import annotations

from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r20_q6_initial_book_readiness_driver as q6
from multimarket import dev045_m6_event_loop_contract as d1


EXPERIMENT_ID = "DEV045-D6R20-Q8"
DESIGN_VERSION = "terminal-shutdown-grid-alignment-v1"

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
END_OF_DATA_SUCCESS_ENABLED = False
MANUAL_POST_EOD_FILL_BINDING_ENABLED = False
FLATTEN_RETRY_ENABLED = False
SYNTHESIZED_RESPONSE_ENABLED = False


def align_terminal_shutdown_cutoff_to_base_grid(
    *, raw_terminal_shutdown_cutoff_ns: int
) -> int:
    """Floor a raw terminal cutoff to the frozen base-policy grid."""
    raw = int(raw_terminal_shutdown_cutoff_ns)
    step = int(d1.BASE_MAKER_STEP_NS)

    if raw < 0:
        raise base.RealHistoricalDriverError("q8_negative_terminal_cutoff")

    if step <= 0:
        raise base.RealHistoricalDriverError("q8_invalid_base_policy_step")

    aligned = (raw // step) * step
    shift = raw - aligned

    if aligned > raw:
        raise base.RealHistoricalDriverError("q8_terminal_cutoff_after_raw")

    if shift < 0 or shift >= step:
        raise base.RealHistoricalDriverError("q8_terminal_alignment_shift")

    if not d1.is_base_policy_epoch_local(aligned):
        raise base.RealHistoricalDriverError(
            "q8_terminal_cutoff_not_base_epoch"
        )

    return int(aligned)


class TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel(
    q6.InitialBookReadinessContinuousHistoricalPolicyKernel
):
    """Frozen Q6 execution with only its terminal cutoff floored to D1 grid."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        raw = int(self.terminal_shutdown_cutoff_ns)
        aligned = align_terminal_shutdown_cutoff_to_base_grid(
            raw_terminal_shutdown_cutoff_ns=raw
        )
        lead = int(base.terminal_shutdown_lead_ns(self.scenario))
        shift = raw - aligned

        if int(self.terminal_source_local_ns) - raw != lead:
            raise base.RealHistoricalDriverError("q8_raw_terminal_lead")

        if int(self.terminal_source_local_ns) - aligned < lead:
            raise base.RealHistoricalDriverError(
                "q8_aligned_terminal_lead_eroded"
            )

        self.raw_terminal_shutdown_cutoff_ns = raw
        self.aligned_terminal_shutdown_cutoff_ns = aligned
        self.cutoff_alignment_shift_ns = shift
        self.frozen_terminal_shutdown_lead_ns = lead

        # This is the only inherited execution-control field Q8 changes.
        self.terminal_shutdown_cutoff_ns = aligned

    def terminal_shutdown_alignment_diagnostics(self) -> dict:
        actual_start = self.terminal_shutdown_start_ns
        remaining = (
            int(self.terminal_source_local_ns) - int(actual_start)
            if actual_start is not None
            else None
        )
        no_later_than_raw = bool(
            actual_start is not None
            and int(actual_start) <= int(self.raw_terminal_shutdown_cutoff_ns)
        )
        lead_preserved = bool(
            remaining is not None
            and int(remaining) >= int(self.frozen_terminal_shutdown_lead_ns)
        )
        return {
            "raw_terminal_shutdown_cutoff_ns": int(
                self.raw_terminal_shutdown_cutoff_ns
            ),
            "aligned_terminal_shutdown_cutoff_ns": int(
                self.aligned_terminal_shutdown_cutoff_ns
            ),
            "cutoff_alignment_shift_ns": int(self.cutoff_alignment_shift_ns),
            "frozen_terminal_shutdown_lead_ns": int(
                self.frozen_terminal_shutdown_lead_ns
            ),
            "actual_terminal_shutdown_start_ns": (
                int(actual_start) if actual_start is not None else None
            ),
            "remaining_ns_at_shutdown_start": remaining,
            "terminal_start_no_later_than_raw_cutoff": no_later_than_raw,
            "terminal_lead_preserved": lead_preserved,
        }


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "CANONICAL_RUNNER_IMPLEMENTED",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "AUTOMATIC_RETRY",
    "END_OF_DATA_SUCCESS_ENABLED",
    "MANUAL_POST_EOD_FILL_BINDING_ENABLED",
    "FLATTEN_RETRY_ENABLED",
    "SYNTHESIZED_RESPONSE_ENABLED",
    "align_terminal_shutdown_cutoff_to_base_grid",
    "TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel",
]

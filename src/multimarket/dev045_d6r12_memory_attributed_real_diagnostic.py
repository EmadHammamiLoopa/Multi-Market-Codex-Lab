from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Sequence

from multimarket import dev045_d6r11_memory_attribution as memory
from multimarket import dev045_d6r12_memory_attributed_real_diagnostic_contract as c


class D6R12DesignError(RuntimeError):
    pass


@dataclass(frozen=True)
class DiagnosticMemorySample:
    capture_point: str
    market_wakeups: int | None
    snapshot: memory.MemorySnapshot

    def to_dict(self) -> dict[str, object]:
        _validate_sample(self)
        return {
            "capture_point": self.capture_point,
            "market_wakeups": self.market_wakeups,
            "captured_at_utc": self.snapshot.captured_at_utc,
            "process": self.snapshot.process.to_dict(),
            "system": {"MemAvailable_bytes": self.snapshot.mem_available_bytes},
            "smaps_rollup_available": self.snapshot.smaps_rollup is not None,
            "smaps_rollup": (
                None
                if self.snapshot.smaps_rollup is None
                else self.snapshot.smaps_rollup.to_dict()
            ),
        }


@dataclass(frozen=True)
class DiagnosticMemorySummary:
    peak_vm_rss_bytes: int
    peak_rss_anon_bytes: int
    peak_rss_file_bytes: int
    peak_rss_shmem_bytes: int
    minimum_memavailable_bytes: int
    peak_vm_swap_bytes: int

    def to_dict(self) -> dict[str, int]:
        return {
            "peak_vm_rss_bytes": self.peak_vm_rss_bytes,
            "peak_rss_anon_bytes": self.peak_rss_anon_bytes,
            "peak_rss_file_bytes": self.peak_rss_file_bytes,
            "peak_rss_shmem_bytes": self.peak_rss_shmem_bytes,
            "minimum_memavailable_bytes": self.minimum_memavailable_bytes,
            "peak_vm_swap_bytes": self.peak_vm_swap_bytes,
        }


@dataclass(frozen=True)
class WakeupProgress:
    market_wakeups: int
    bounded_wakeup_reached: bool
    crossed_old_failure_region: bool
    terminal_reason: str | None


def wakeup_snapshot_schedule() -> tuple[int, ...]:
    interval_points = tuple(
        range(
            c.WAKEUP_CAPTURE_INTERVAL,
            c.BOUNDED_WAKEUP_TARGET + 1,
            c.WAKEUP_CAPTURE_INTERVAL,
        )
    )
    schedule = (c.FIRST_WAKEUP_CAPTURE, *interval_points)
    if schedule[-1] != c.BOUNDED_WAKEUP_TARGET:
        raise D6R12DesignError("target_not_scheduled")
    if not all(point in schedule for point in c.SPECIFIC_WAKEUP_CAPTURES):
        raise D6R12DesignError("specific_capture_missing")
    return schedule


def snapshot_due_at_wakeup(market_wakeups: int) -> bool:
    _validate_wakeup_count(market_wakeups)
    if market_wakeups > c.BOUNDED_WAKEUP_TARGET:
        raise D6R12DesignError(c.TARGET_OVERSHOOT_ERROR)
    return market_wakeups == c.FIRST_WAKEUP_CAPTURE or (
        market_wakeups > 0
        and market_wakeups % c.WAKEUP_CAPTURE_INTERVAL == 0
    )


def evaluate_wakeup_progress(market_wakeups: int) -> WakeupProgress:
    _validate_wakeup_count(market_wakeups)
    if market_wakeups > c.BOUNDED_WAKEUP_TARGET:
        raise D6R12DesignError(c.TARGET_OVERSHOOT_ERROR)
    reached = market_wakeups == c.BOUNDED_WAKEUP_TARGET
    return WakeupProgress(
        market_wakeups=market_wakeups,
        bounded_wakeup_reached=reached,
        crossed_old_failure_region=(
            market_wakeups > c.OLD_D6R10_LAST_HEARTBEAT_WAKEUPS
        ),
        terminal_reason=(c.BOUNDED_TARGET_TERMINAL_REASON if reached else None),
    )


def attempt_state(*, marker_exists: bool, evidence_exists: bool) -> str:
    if not isinstance(marker_exists, bool) or not isinstance(evidence_exists, bool):
        raise D6R12DesignError("attempt_state_type")
    if marker_exists or evidence_exists:
        return "CONSUMED_NO_RERUN"
    return "FRESH"


def preexecution_failure_reason(snapshot: memory.MemorySnapshot) -> str | None:
    _validate_required_snapshot(snapshot)
    if snapshot.mem_available_bytes < c.PREEXEC_MIN_MEMAVAILABLE_BYTES:
        return "PREEXEC_MEMAVAILABLE_BELOW_MINIMUM"
    return None


def hard_safety_abort_reason(
    baseline: memory.MemorySnapshot,
    current: memory.MemorySnapshot,
) -> str | None:
    _validate_required_snapshot(baseline)
    _validate_required_snapshot(current)

    baseline_swap = baseline.process.vm_swap_bytes
    current_swap = current.process.vm_swap_bytes
    if baseline_swap is None or current_swap is None:
        raise D6R12DesignError("VmSwap_missing")
    if c.RUNTIME_ABORT_ON_PROCESS_SWAP_GROWTH and current_swap > baseline_swap:
        return "PROCESS_SWAP_GROWTH"

    return None


def summarize_memory_samples(
    samples: Sequence[DiagnosticMemorySample],
) -> DiagnosticMemorySummary:
    if not samples:
        raise D6R12DesignError("memory_samples_empty")
    for sample in samples:
        _validate_sample(sample)

    swaps = [sample.snapshot.process.vm_swap_bytes for sample in samples]
    if any(value is None for value in swaps):
        raise D6R12DesignError("VmSwap_missing")

    return DiagnosticMemorySummary(
        peak_vm_rss_bytes=max(sample.snapshot.process.vm_rss_bytes for sample in samples),
        peak_rss_anon_bytes=max(
            sample.snapshot.process.rss_anon_bytes for sample in samples
        ),
        peak_rss_file_bytes=max(
            sample.snapshot.process.rss_file_bytes for sample in samples
        ),
        peak_rss_shmem_bytes=max(
            sample.snapshot.process.rss_shmem_bytes for sample in samples
        ),
        minimum_memavailable_bytes=min(
            sample.snapshot.mem_available_bytes for sample in samples
        ),
        peak_vm_swap_bytes=max(int(value) for value in swaps if value is not None),
    )


def serialize_memory_samples(samples: Sequence[DiagnosticMemorySample]) -> str:
    payload = [sample.to_dict() for sample in samples]
    if not payload:
        raise D6R12DesignError("memory_samples_empty")
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def closed_evidence_flags() -> dict[str, bool]:
    return {
        "full_day_attempted": False,
        "full_day_validated": False,
        "canonical_npy_written": False,
        "raw_csv_opened": False,
        "converter_rerun": False,
        "orders": False,
        "policy_execution": False,
        "historical_pnl": False,
        "economic_arena": False,
        "aug_opened": False,
        "sep_plus_opened": False,
        "non_btc_opened": False,
        "network_acquisition": False,
        "railway_touched": False,
        "live_trading_authorized": False,
    }


def _validate_wakeup_count(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise D6R12DesignError("market_wakeups")


def _validate_required_snapshot(snapshot: memory.MemorySnapshot) -> None:
    if not isinstance(snapshot, memory.MemorySnapshot):
        raise D6R12DesignError("memory_snapshot_type")
    process = snapshot.process
    missing = []
    if process.vm_size_bytes is None:
        missing.append("VmSize")
    if process.vm_data_bytes is None:
        missing.append("VmData")
    if process.vm_swap_bytes is None:
        missing.append("VmSwap")
    if missing:
        raise D6R12DesignError(f"status_field_missing:{','.join(missing)}")


def _validate_sample(sample: DiagnosticMemorySample) -> None:
    if not isinstance(sample, DiagnosticMemorySample):
        raise D6R12DesignError("memory_sample_type")
    if not sample.capture_point:
        raise D6R12DesignError("capture_point")
    if sample.market_wakeups is not None:
        _validate_wakeup_count(sample.market_wakeups)
        if sample.market_wakeups > c.BOUNDED_WAKEUP_TARGET:
            raise D6R12DesignError(c.TARGET_OVERSHOOT_ERROR)
    _validate_required_snapshot(sample.snapshot)

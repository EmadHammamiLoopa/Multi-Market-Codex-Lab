from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
import mmap
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence

from multimarket import dev045_d6r11_memory_attribution as memory
from multimarket import dev045_d6r12_memory_attributed_real_diagnostic as diagnostic
from multimarket import dev045_d6r14_memory_policy as policy
from multimarket import dev045_d6r15_full_day_contract as c


class D6R15ExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class FullDayDependencies:
    capture_memory: Callable[[], memory.MemorySnapshot]
    open_source: Callable[[], Any]
    build_binding: Callable[[Any], Any]
    source_identity: Callable[[], tuple[int, int, int, int]]
    persist_heartbeat: Callable[[dict[str, object]], None]


@dataclass(frozen=True)
class FullDayOutcome:
    market_wakeups: int
    last_timestamp_ns: int
    memory_samples: tuple[diagnostic.DiagnosticMemorySample, ...]
    lifecycle: tuple[str, ...]
    position: float
    working_order_count: int
    source_unchanged: bool
    terminal_classification: str

    def to_evidence_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "experiment_id": c.EXPERIMENT_ID,
            "schema_version": c.SCHEMA_VERSION,
            "day": c.DAY,
            "symbol": c.SYMBOL,
            "exchange": c.EXCHANGE,
            "source_path": str(c.SOURCE_PATH),
            "source_sha256": c.SOURCE_SHA256,
            "source_rows": c.SOURCE_ROWS,
            "source_bytes": c.SOURCE_BYTES,
            "source_content_opened": True,
            "source_verified_by_adapter": True,
            "natural_end_of_data_reached": True,
            "fixed_wakeup_stop_target": None,
            "market_wakeups": self.market_wakeups,
            "reference_eod_wakeups": c.REFERENCE_EOD_WAKEUPS,
            "reference_eod_wakeups_match": (
                self.market_wakeups == c.REFERENCE_EOD_WAKEUPS
            ),
            "last_timestamp_ns": self.last_timestamp_ns,
            "reference_last_timestamp_ns": c.REFERENCE_LAST_TIMESTAMP_NS,
            "reference_last_timestamp_match": (
                self.last_timestamp_ns == c.REFERENCE_LAST_TIMESTAMP_NS
            ),
            "terminal_classification": self.terminal_classification,
            "full_day_validated": (
                self.terminal_classification == "PASS_NATURAL_END_OF_DATA"
            ),
            "memory_snapshots": [
                sample.to_dict() for sample in self.memory_samples
            ],
            "memory_summary": diagnostic.summarize_memory_samples(
                self.memory_samples
            ).to_dict(),
            "lifecycle": list(self.lifecycle),
            "position": self.position,
            "working_order_count": self.working_order_count,
            "source_unchanged": self.source_unchanged,
        }
        payload.update(closed_surface_flags())
        return payload


@dataclass(frozen=True)
class ChildProcessResult:
    returncode: int
    stdout: str
    stderr: str


def closed_surface_flags() -> dict[str, bool]:
    return {
        "full_day_attempted": True,
        "full_day_validation": True,
        "mar_to_jul_opened": False,
        "historical_pnl": False,
        "policy_execution": False,
        "orders": False,
        "order_submission": False,
        "order_cancel": False,
        "converter_rerun": False,
        "raw_csv_opened": False,
        "canonical_npy_written": False,
        "aug_opened": False,
        "sep_plus_opened": False,
        "non_btc_opened": False,
        "network_acquisition": False,
        "railway_touched": False,
        "live_trading": False,
    }


def require_execution_authorization(
    environ: Mapping[str, str] | None = None,
) -> None:
    env = os.environ if environ is None else environ

    if env.get(c.AUTHORIZATION_ENV) != c.AUTHORIZATION_TOKEN:
        raise D6R15ExecutionError("authorization_token")

    if not c.REAL_EXECUTION_ENABLED:
        raise D6R15ExecutionError("execution_disabled_by_contract")

    if c.AUTHORIZED_EXECUTION_FLAGS != (
        True,
    ) * len(c.AUTHORIZED_EXECUTION_FLAGS):
        raise D6R15ExecutionError("authorized_execution_flags")

    if c.PROHIBITED_EXECUTION_FLAGS != (
        False,
    ) * len(c.PROHIBITED_EXECUTION_FLAGS):
        raise D6R15ExecutionError("prohibited_execution_flags")


def child_command(*, smoke: bool = False) -> list[str]:
    flag = (
        c.CHILD_RESOLUTION_SMOKE_FLAG
        if smoke
        else c.CHILD_FLAG
    )
    command = [sys.executable, "-m", c.CHILD_MODULE_NAME, flag]

    if "__main__" in command:
        raise D6R15ExecutionError("child_command_uses_main")

    return command


def child_resolution_smoke_payload() -> dict[str, object]:
    return {
        "status": "PASS",
        "experiment_id": c.EXPERIMENT_ID,
        "runtime_name": __name__,
        "resolved_module_name": c.CHILD_MODULE_NAME,
        "canonical_data_opened": False,
        "attempt_marker_created": False,
        "heartbeat_created": False,
        "hftbacktest_canonical_run": False,
        "full_day_attempted": False,
        "real_execution_enabled": c.REAL_EXECUTION_ENABLED,
    }


def run_child_resolution_smoke() -> dict[str, object]:
    completed = subprocess.run(
        child_command(smoke=True),
        text=True,
        capture_output=True,
        check=False,
        env=dict(os.environ),
    )

    if completed.returncode != 0:
        raise D6R15ExecutionError(
            f"child_resolution_return_code:{completed.returncode}"
        )

    lines = [
        line for line in completed.stdout.splitlines()
        if line.strip()
    ]

    if not lines:
        raise D6R15ExecutionError("child_resolution_stdout_empty")

    payload = json.loads(lines[-1])

    required = {
        "status": "PASS",
        "experiment_id": c.EXPERIMENT_ID,
        "runtime_name": "__main__",
        "resolved_module_name": c.CHILD_MODULE_NAME,
        "canonical_data_opened": False,
        "attempt_marker_created": False,
        "heartbeat_created": False,
        "hftbacktest_canonical_run": False,
        "full_day_attempted": False,
        "real_execution_enabled": True,
    }

    for key, expected in required.items():
        if payload.get(key) != expected:
            raise D6R15ExecutionError(
                f"child_resolution_invariant:{key}"
            )

    return payload


def _sha256_small(path: Path) -> str:
    p = Path(path)

    if not p.is_file():
        raise D6R15ExecutionError(f"small_artifact_missing:{p}")

    if p.stat().st_size > 2 * 1024 * 1024:
        raise D6R15ExecutionError(f"small_artifact_too_large:{p}")

    digest = hashlib.sha256()

    with p.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def attempt_state() -> str:
    if (
        c.ATTEMPT_MARKER_PATH.exists()
        or c.MEMORY_HEARTBEAT_PATH.exists()
        or c.EVIDENCE_PATH.exists()
    ):
        return "NOT_FRESH"

    return "FRESH"


def run_preflight() -> dict[str, object]:
    if (
        _sha256_small(c.PARENT_D6R14_FREEZE_MANIFEST_PATH)
        != c.PARENT_D6R14_FREEZE_MANIFEST_SHA256
    ):
        raise D6R15ExecutionError(
            "parent_d6r14_freeze_manifest_sha"
        )

    parent = json.loads(
        c.PARENT_D6R14_FREEZE_MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    if (
        parent.get("status")
        != "FROZEN_MEMORY_POLICY_FEED_BOUND_DESIGN_PASS"
    ):
        raise D6R15ExecutionError(
            "parent_d6r14_freeze_status"
        )

    if parent.get("d6r13_rerun_forbidden") is not True:
        raise D6R15ExecutionError(
            "parent_d6r13_rerun_guard"
        )

    if (
        parent.get("d6r13_diagnostic_question_answered")
        is not True
    ):
        raise D6R15ExecutionError(
            "parent_memory_question"
        )

    observed = c.SOURCE_PATH.stat()

    if not stat.S_ISREG(observed.st_mode):
        raise D6R15ExecutionError("source_not_regular_file")

    if int(observed.st_size) != c.SOURCE_BYTES:
        raise D6R15ExecutionError(
            f"source_bytes:{observed.st_size}"
        )

    hft_version = importlib.metadata.version(
        "hftbacktest"
    )

    if hft_version != c.HFTBACKTEST_VERSION:
        raise D6R15ExecutionError(
            f"hftbacktest_version:{hft_version}"
        )

    snapshot = memory.capture_memory_snapshot()

    if (
        snapshot.mem_available_bytes
        < c.PREEXEC_MIN_MEMAVAILABLE_BYTES
    ):
        raise D6R15ExecutionError(
            "preexec_memavailable"
        )

    state = attempt_state()

    if state != "FRESH":
        raise D6R15ExecutionError(
            f"attempt_state:{state}"
        )

    smoke = run_child_resolution_smoke()

    return {
        "experiment_id": c.EXPERIMENT_ID,
        "status": "PASS",
        "stage_mode": c.STAGE_MODE,
        "source_stat_verified": True,
        "source_content_opened": False,
        "source_content_hashed": False,
        "source_bytes": int(observed.st_size),
        "hftbacktest_version": hft_version,
        "mem_available_bytes": snapshot.mem_available_bytes,
        "attempt_state": state,
        "launcher_smoke_verified": (
            smoke.get("status") == "PASS"
        ),
        "real_execution_performed": False,
        "d6r12_rerun": False,
        "d6r13_rerun": False,
    }


def _apply_madv_sequential(source: Any) -> None:
    mapped = getattr(
        getattr(source, "data", None),
        "_mmap",
        None,
    )

    if (
        c.MADV_SEQUENTIAL_IF_SUPPORTED
        and mapped is not None
        and hasattr(mapped, "madvise")
        and hasattr(mmap, "MADV_SEQUENTIAL")
    ):
        mapped.madvise(mmap.MADV_SEQUENTIAL)


def atomic_write_json(
    path: Path,
    payload: Mapping[str, object],
) -> None:
    destination = Path(path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = destination.with_name(
        destination.name + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        destination,
    )


def create_one_shot_marker(
    path: Path,
    payload: Mapping[str, object],
) -> None:
    destination = Path(path)

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode()

    try:
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise D6R15ExecutionError(
            "attempt_marker_exists"
        ) from exc

    with os.fdopen(
        descriptor,
        "wb",
    ) as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with Path(path).open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def _required_swap(
    snapshot: memory.MemorySnapshot,
) -> int:
    value = snapshot.process.vm_swap_bytes

    if value is None:
        raise D6R15ExecutionError(
            "vm_swap_unavailable"
        )

    return int(value)


def _memory_abort_reason(
    *,
    baseline_swap_bytes: int,
    baseline_rss_anon_bytes: int,
    snapshot: memory.MemorySnapshot,
) -> str | None:
    current_swap = _required_swap(snapshot)

    return policy.memory_abort_reason(
        baseline_swap_bytes=baseline_swap_bytes,
        current_swap_bytes=current_swap,
        baseline_rss_anon_bytes=(
            baseline_rss_anon_bytes
        ),
        current_rss_anon_bytes=(
            snapshot.process.rss_anon_bytes
        ),
        current_memavailable_bytes=(
            snapshot.mem_available_bytes
        ),
    )


def _capture_payload(
    samples: Sequence[
        diagnostic.DiagnosticMemorySample
    ],
    current_timestamp_ns: int | None,
) -> dict[str, object]:
    if not samples:
        raise D6R15ExecutionError(
            "heartbeat_samples_empty"
        )

    latest = samples[-1]

    payload: dict[str, object] = {
        "experiment_id": c.EXPERIMENT_ID,
        "schema_version": c.SCHEMA_VERSION,
        "capture_point": latest.capture_point,
        "market_wakeups": (
            latest.market_wakeups or 0
        ),
        "current_timestamp_ns": (
            current_timestamp_ns
        ),
        "MemAvailable_bytes": (
            latest.snapshot.mem_available_bytes
        ),
        "updated_at_utc": (
            latest.snapshot.captured_at_utc
        ),
        "memory_snapshots": [
            sample.to_dict()
            for sample in samples
        ],
    }

    payload.update(
        latest.snapshot.process.to_dict()
    )

    return payload


def close_with_snapshots(
    binding: Any,
    capture: Callable[
        [str],
        diagnostic.DiagnosticMemorySample,
    ],
) -> None:
    if binding._closed:
        return

    close_rc: int | None = None

    try:
        if not getattr(
            binding,
            "_d6r15_backtest_close_attempted",
            False,
        ):
            binding._d6r15_backtest_close_attempted = True
            close_rc = int(binding.bt.close())
            binding.lifecycle.append(
                "backtest_closed"
            )
            capture("after_backtest_close")
    finally:
        if not getattr(
            binding,
            "_d6r15_memmap_close_attempted",
            False,
        ):
            binding._d6r15_memmap_close_attempted = True
            binding.source.close()
            binding.lifecycle.append(
                "memmap_closed"
            )
            binding._closed = True
            capture("after_memmap_close")

    if close_rc is not None and close_rc != 0:
        raise D6R15ExecutionError(
            f"backtest_close_rc:{close_rc}"
        )


def run_full_day_feed(
    deps: FullDayDependencies,
    *,
    capture_interval: int = c.WAKEUP_CAPTURE_INTERVAL,
    reference_wakeups: int = c.REFERENCE_EOD_WAKEUPS,
    reference_last_timestamp_ns: int = (
        c.REFERENCE_LAST_TIMESTAMP_NS
    ),
) -> FullDayOutcome:
    if capture_interval <= 0:
        raise D6R15ExecutionError(
            "capture_interval"
        )

    samples: list[
        diagnostic.DiagnosticMemorySample
    ] = []

    source = None
    binding = None
    market_wakeups = 0
    current_timestamp_ns: int | None = None

    def capture(
        point: str,
    ) -> diagnostic.DiagnosticMemorySample:
        sample = diagnostic.DiagnosticMemorySample(
            capture_point=point,
            market_wakeups=(
                market_wakeups
                if market_wakeups
                else None
            ),
            snapshot=deps.capture_memory(),
        )

        samples.append(sample)

        deps.persist_heartbeat(
            _capture_payload(
                samples,
                current_timestamp_ns,
            )
        )

        return sample

    baseline = capture(
        "before_source_open"
    )

    if (
        baseline.snapshot.mem_available_bytes
        < c.PREEXEC_MIN_MEMAVAILABLE_BYTES
    ):
        raise D6R15ExecutionError(
            "preexec_memavailable"
        )

    baseline_swap = _required_swap(
        baseline.snapshot
    )

    source_before = deps.source_identity()

    try:
        source = deps.open_source()

        capture(
            "after_verified_memmap_open"
        )

        _apply_madv_sequential(source)

        binding = deps.build_binding(source)

        after_binding = capture(
            "after_hftbacktest_binding_creation"
        )

        baseline_anon = (
            after_binding.snapshot.process.rss_anon_bytes
        )

        reason = _memory_abort_reason(
            baseline_swap_bytes=baseline_swap,
            baseline_rss_anon_bytes=baseline_anon,
            snapshot=after_binding.snapshot,
        )

        if reason is not None:
            raise D6R15ExecutionError(reason)

        while True:
            rc = int(
                binding.bt.wait_next_feed(
                    False,
                    c.WAIT_NEXT_FEED_TIMEOUT_NS,
                )
            )

            if rc == 1:
                break

            if rc != 2:
                raise D6R15ExecutionError(
                    f"feed_rc:{rc}"
                )

            market_wakeups += 1

            current_timestamp_ns = int(
                binding.bt.current_timestamp
            )

            if (
                market_wakeups == 1
                or market_wakeups
                % capture_interval
                == 0
            ):
                current = capture(
                    f"market_wakeup_{market_wakeups}"
                )

                reason = _memory_abort_reason(
                    baseline_swap_bytes=(
                        baseline_swap
                    ),
                    baseline_rss_anon_bytes=(
                        baseline_anon
                    ),
                    snapshot=current.snapshot,
                )

                if reason is not None:
                    raise D6R15ExecutionError(
                        reason
                    )

        if market_wakeups <= 0:
            raise D6R15ExecutionError(
                "empty_feed"
            )

        eod = capture(
            "natural_end_of_data"
        )

        reason = _memory_abort_reason(
            baseline_swap_bytes=baseline_swap,
            baseline_rss_anon_bytes=baseline_anon,
            snapshot=eod.snapshot,
        )

        if reason is not None:
            raise D6R15ExecutionError(reason)

        if current_timestamp_ns is None:
            raise D6R15ExecutionError(
                "terminal_timestamp_missing"
            )

        if (
            c.REFERENCE_EOD_VALIDATION_REQUIRED
            and market_wakeups
            != reference_wakeups
        ):
            raise D6R15ExecutionError(
                "reference_eod_wakeup_mismatch:"
                f"{market_wakeups}:"
                f"{reference_wakeups}"
            )

        if (
            c.REFERENCE_LAST_TIMESTAMP_VALIDATION_REQUIRED
            and current_timestamp_ns
            != reference_last_timestamp_ns
        ):
            raise D6R15ExecutionError(
                "reference_last_timestamp_mismatch:"
                f"{current_timestamp_ns}:"
                f"{reference_last_timestamp_ns}"
            )

        position = float(
            binding.bt.position(0)
        )

        working_order_count = int(
            len(binding.bt.orders(0))
        )

        if (
            position != 0.0
            or working_order_count != 0
        ):
            raise D6R15ExecutionError(
                "terminal_execution_state"
            )

        capture(
            "immediately_before_close"
        )

        close_with_snapshots(
            binding,
            capture,
        )

        source_unchanged = (
            deps.source_identity()
            == source_before
        )

        classification = (
            policy.classify_feed_terminal(
                end_of_data=True,
                market_wakeups=market_wakeups,
                hard_safety_abort_reason=None,
                position=position,
                working_order_count=(
                    working_order_count
                ),
                source_unchanged=(
                    source_unchanged
                ),
                lifecycle=binding.lifecycle,
            )
        )

        if (
            classification
            != "PASS_NATURAL_END_OF_DATA"
        ):
            raise D6R15ExecutionError(
                f"terminal_classification:"
                f"{classification}"
            )

        return FullDayOutcome(
            market_wakeups=market_wakeups,
            last_timestamp_ns=(
                current_timestamp_ns
            ),
            memory_samples=tuple(samples),
            lifecycle=tuple(
                binding.lifecycle
            ),
            position=position,
            working_order_count=(
                working_order_count
            ),
            source_unchanged=(
                source_unchanged
            ),
            terminal_classification=(
                classification
            ),
        )

    finally:
        if (
            binding is not None
            and not binding._closed
        ):
            close_with_snapshots(
                binding,
                capture,
            )

        elif (
            binding is None
            and source is not None
            and not source._closed
        ):
            source.close()
            capture(
                "after_memmap_close"
            )


def run_parent_attempt(
    child_runner: Callable[
        [],
        ChildProcessResult,
    ],
) -> dict[str, object]:
    if attempt_state() != "FRESH":
        raise D6R15ExecutionError(
            "attempt_not_fresh"
        )

    marker = {
        "experiment_id": c.EXPERIMENT_ID,
        "schema_version": c.SCHEMA_VERSION,
        "canonical_attempt": 1,
        "day": c.DAY,
        "mode": "FEED_ONLY_TO_NATURAL_END_OF_DATA",
        "fixed_wakeup_stop_target": None,
        "reference_eod_wakeups": (
            c.REFERENCE_EOD_WAKEUPS
        ),
        "reference_last_timestamp_ns": (
            c.REFERENCE_LAST_TIMESTAMP_NS
        ),
    }

    create_one_shot_marker(
        c.ATTEMPT_MARKER_PATH,
        marker,
    )

    evidence: dict[str, object] = {
        **marker,
        "status": "FAIL",
        "failure_reason": None,
        "source_content_opened": False,
        **closed_surface_flags(),
    }

    try:
        child = child_runner()

        evidence["child_return_code"] = (
            child.returncode
        )

        evidence["child_stdout_tail"] = (
            child.stdout[-8192:]
        )

        evidence["child_stderr_tail"] = (
            child.stderr[-8192:]
        )

        if child.returncode != 0:
            raise D6R15ExecutionError(
                f"child_return_code:"
                f"{child.returncode}"
            )

        lines = [
            line
            for line in child.stdout.splitlines()
            if line.strip()
        ]

        if not lines:
            raise D6R15ExecutionError(
                "child_stdout_empty"
            )

        payload = json.loads(
            lines[-1]
        )

        required = {
            "experiment_id": c.EXPERIMENT_ID,
            "natural_end_of_data_reached": True,
            "market_wakeups": (
                c.REFERENCE_EOD_WAKEUPS
            ),
            "reference_eod_wakeups_match": True,
            "last_timestamp_ns": (
                c.REFERENCE_LAST_TIMESTAMP_NS
            ),
            "reference_last_timestamp_match": True,
            "terminal_classification": (
                "PASS_NATURAL_END_OF_DATA"
            ),
            "full_day_validated": True,
            "position": 0.0,
            "working_order_count": 0,
            "source_unchanged": True,
        }

        for key, expected in required.items():
            if payload.get(key) != expected:
                raise D6R15ExecutionError(
                    f"child_payload_invariant:{key}"
                )

        lifecycle = payload.get(
            "lifecycle"
        )

        if (
            not isinstance(lifecycle, list)
            or lifecycle[-2:]
            != [
                "backtest_closed",
                "memmap_closed",
            ]
        ):
            raise D6R15ExecutionError(
                "child_close_lifecycle"
            )

        evidence.update(payload)
        evidence["status"] = "PASS"

    except Exception as exc:
        evidence["failure_reason"] = (
            f"{type(exc).__name__}:{exc}"
        )

    finally:
        if c.MEMORY_HEARTBEAT_PATH.is_file():
            evidence[
                "latest_heartbeat_sha256"
            ] = _sha256(
                c.MEMORY_HEARTBEAT_PATH
            )

            heartbeat = json.loads(
                c.MEMORY_HEARTBEAT_PATH.read_text(
                    encoding="utf-8"
                )
            )

            evidence["latest_heartbeat"] = (
                heartbeat
            )

            samples = heartbeat.get(
                "memory_snapshots",
                [],
            )

            evidence["memory_snapshots"] = (
                samples
                if isinstance(samples, list)
                else []
            )

            if any(
                isinstance(item, dict)
                and item.get("capture_point")
                != "before_source_open"
                for item
                in evidence["memory_snapshots"]
            ):
                evidence[
                    "source_content_opened"
                ] = True

        atomic_write_json(
            c.EVIDENCE_PATH,
            evidence,
        )

    return evidence


def run_real_parent(
    environ: Mapping[str, str] | None = None,
) -> int:
    require_execution_authorization(
        environ
    )

    result = run_preflight()

    if result["attempt_state"] != "FRESH":
        raise D6R15ExecutionError(
            "preflight_attempt_state"
        )

    def child_runner() -> ChildProcessResult:
        completed = subprocess.run(
            child_command(),
            text=True,
            capture_output=True,
            check=False,
            env=dict(os.environ),
        )

        return ChildProcessResult(
            int(completed.returncode),
            completed.stdout,
            completed.stderr,
        )

    evidence = run_parent_attempt(
        child_runner
    )

    return (
        0
        if evidence["status"] == "PASS"
        else 1
    )


def run_real_child(
    environ: Mapping[str, str] | None = None,
) -> int:
    require_execution_authorization(
        environ
    )

    from multimarket import dev045_d6r5_memmap_adapter as adapter
    from multimarket import dev045_d6r6_historical_driver as driver

    def source_identity() -> tuple[
        int,
        int,
        int,
        int,
    ]:
        observed = c.SOURCE_PATH.stat()

        return (
            int(observed.st_dev),
            int(observed.st_ino),
            int(observed.st_size),
            int(observed.st_mtime_ns),
        )

    deps = FullDayDependencies(
        capture_memory=(
            memory.capture_memory_snapshot
        ),
        open_source=lambda: (
            adapter._open_verified_file(
                c.SOURCE_PATH,
                expected_sha256=(
                    c.SOURCE_SHA256
                ),
                expected_bytes=(
                    c.SOURCE_BYTES
                ),
                expected_rows=(
                    c.SOURCE_ROWS
                ),
            )
        ),
        build_binding=(
            driver._build_lifetime_safe_binding
        ),
        source_identity=(
            source_identity
        ),
        persist_heartbeat=lambda payload: (
            atomic_write_json(
                c.MEMORY_HEARTBEAT_PATH,
                payload,
            )
        ),
    )

    outcome = run_full_day_feed(
        deps
    )

    print(
        json.dumps(
            outcome.to_evidence_dict(),
            sort_keys=True,
        ),
        flush=True,
    )

    return 0


def main(
    argv: Sequence[str] | None = None,
) -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        c.CHILD_RESOLUTION_SMOKE_FLAG,
        action="store_true",
    )

    parser.add_argument(
        c.CHILD_FLAG,
        action="store_true",
    )

    parser.add_argument(
        c.PREFLIGHT_FLAG,
        action="store_true",
    )

    args = parser.parse_args(argv)

    if args.child_resolution_smoke:
        print(
            json.dumps(
                child_resolution_smoke_payload(),
                sort_keys=True,
            ),
            flush=True,
        )
        return 0

    if args.preflight:
        print(
            json.dumps(
                run_preflight(),
                sort_keys=True,
            ),
            flush=True,
        )
        return 0

    if args.child:
        return run_real_child()

    return run_real_parent()


if __name__ == "__main__":
    raise SystemExit(main())

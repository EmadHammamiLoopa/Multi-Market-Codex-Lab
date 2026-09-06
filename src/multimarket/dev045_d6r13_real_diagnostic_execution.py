from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import mmap
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable, Mapping, Sequence

from multimarket import dev045_d6r11_memory_attribution as memory
from multimarket import dev045_d6r12_memory_attributed_real_diagnostic as design
from multimarket import dev045_d6r13_real_diagnostic_execution_contract as c
from multimarket import dev045_d6r13_real_diagnostic_successor_preflight as preflight


class D6R13ExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChildResolutionResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def payload(self) -> dict[str, object]:
        if self.returncode != 0:
            raise D6R13ExecutionError(f"child_resolution_return_code:{self.returncode}")
        lines = [line for line in self.stdout.splitlines() if line.strip()]
        if not lines:
            raise D6R13ExecutionError("child_resolution_stdout_empty")
        parsed = json.loads(lines[-1])
        if not isinstance(parsed, dict):
            raise D6R13ExecutionError("child_resolution_payload_type")
        return parsed


@dataclass(frozen=True)
class BoundedDependencies:
    capture_memory: Callable[[], memory.MemorySnapshot]
    open_source: Callable[[], Any]
    build_binding: Callable[[Any], Any]
    source_identity: Callable[[], tuple[int, int, int, int]]
    persist_heartbeat: Callable[[dict[str, object]], None]


@dataclass(frozen=True)
class BoundedOutcome:
    market_wakeups: int
    terminal_reason: str
    memory_samples: tuple[design.DiagnosticMemorySample, ...]
    summary: design.DiagnosticMemorySummary
    lifecycle: tuple[str, ...]
    position: float
    working_order_count: int
    source_unchanged: bool

    def to_evidence_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "experiment_id": c.EXPERIMENT_ID,
            "schema_version": c.SCHEMA_VERSION,
            "day": c.DAY,
            "source_path": str(c.SOURCE_PATH),
            "source_sha256": c.SOURCE_SHA256,
            "source_rows": c.SOURCE_ROWS,
            "source_bytes": c.SOURCE_BYTES,
            "source_content_opened": True,
            "bounded_wakeup_target": c.BOUNDED_WAKEUP_TARGET,
            "bounded_wakeup_reached": self.market_wakeups == c.BOUNDED_WAKEUP_TARGET,
            "market_wakeups": self.market_wakeups,
            "terminal_reason": self.terminal_reason,
            "memory_snapshots": [sample.to_dict() for sample in self.memory_samples],
            "old_d6r10_abort_bytes": c.OLD_D6R10_ABORT_BYTES,
            "old_d6r10_last_heartbeat_wakeups": c.OLD_D6R10_LAST_HEARTBEAT_WAKEUPS,
            "crossed_old_failure_region": self.market_wakeups > c.OLD_D6R10_LAST_HEARTBEAT_WAKEUPS,
            "lifecycle": list(self.lifecycle),
            "position": self.position,
            "working_order_count": self.working_order_count,
            "source_unchanged": self.source_unchanged,
        }
        payload.update(self.summary.to_dict())
        payload.update(design.closed_evidence_flags())
        return payload


@dataclass(frozen=True)
class ChildProcessResult:
    returncode: int
    stdout: str
    stderr: str


def require_execution_authorization(environ: Mapping[str, str] | None = None) -> None:
    env = os.environ if environ is None else environ
    if env.get(c.AUTHORIZATION_ENV) != c.AUTHORIZATION_TOKEN:
        raise D6R13ExecutionError("authorization_token")
    if not c.REAL_EXECUTION_ENABLED:
        raise D6R13ExecutionError("execution_disabled_by_contract")


def child_command(*, smoke: bool = False) -> list[str]:
    flag = c.CHILD_RESOLUTION_SMOKE_FLAG if smoke else c.CHILD_FLAG
    command = [sys.executable, "-m", c.CHILD_MODULE_NAME, flag]
    if "__main__" in command:
        raise D6R13ExecutionError("child_command_uses_main")
    return command


def run_child_resolution_smoke() -> ChildResolutionResult:
    completed = subprocess.run(
        child_command(smoke=True), text=True, capture_output=True, check=False, env=dict(os.environ)
    )
    result = ChildResolutionResult(int(completed.returncode), completed.stdout, completed.stderr)
    validate_child_resolution_payload(result.payload)
    return result


def validate_child_resolution_payload(payload: Mapping[str, object]) -> None:
    required = {
        "status": "PASS",
        "experiment_id": c.EXPERIMENT_ID,
        "runtime_name": "__main__",
        "resolved_module_name": c.CHILD_MODULE_NAME,
        "canonical_data_opened": False,
        "attempt_marker_created": False,
        "heartbeat_created": False,
        "hftbacktest_canonical_run": False,
        "real_execution_enabled": False,
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise D6R13ExecutionError(f"child_resolution_invariant:{key}")


def _apply_madv_sequential(source: Any) -> None:
    mapped = getattr(source.data, "_mmap", None)
    if (
        c.MADV_SEQUENTIAL_IF_SUPPORTED
        and mapped is not None
        and hasattr(mapped, "madvise")
        and hasattr(mmap, "MADV_SEQUENTIAL")
    ):
        mapped.madvise(mmap.MADV_SEQUENTIAL)


def _capture_payload(samples: Sequence[design.DiagnosticMemorySample], current_timestamp_ns: int | None) -> dict[str, object]:
    if not samples:
        raise D6R13ExecutionError("heartbeat_samples_empty")
    latest = samples[-1]
    payload: dict[str, object] = {
        "experiment_id": c.EXPERIMENT_ID,
        "schema_version": c.SCHEMA_VERSION,
        "capture_point": latest.capture_point,
        "market_wakeups": latest.market_wakeups or 0,
        "current_timestamp_ns": current_timestamp_ns,
        "MemAvailable_bytes": latest.snapshot.mem_available_bytes,
        "memory_snapshots": [sample.to_dict() for sample in samples],
        "updated_at_utc": latest.snapshot.captured_at_utc,
        "current_summary": design.summarize_memory_samples(samples).to_dict(),
    }
    payload.update(latest.snapshot.process.to_dict())
    return payload


def close_with_snapshots(binding: Any, capture: Callable[[str], design.DiagnosticMemorySample]) -> None:
    if binding._closed:
        return
    if getattr(binding, "_d6r13_backtest_close_attempted", False):
        raise D6R13ExecutionError("backtest_close_incomplete")
    binding._d6r13_backtest_close_attempted = True
    rc = int(binding.bt.close())
    binding.lifecycle.append("backtest_closed")
    capture("after_backtest_close")
    if rc != 0:
        raise D6R13ExecutionError(f"backtest_close_rc:{rc}")
    if getattr(binding, "_d6r13_memmap_close_attempted", False):
        raise D6R13ExecutionError("memmap_close_incomplete")
    binding._d6r13_memmap_close_attempted = True
    binding.source.close()
    binding.lifecycle.append("memmap_closed")
    binding._closed = True
    capture("after_memmap_close")


def run_bounded_diagnostic(
    deps: BoundedDependencies,
    *,
    target: int = c.BOUNDED_WAKEUP_TARGET,
    capture_interval: int = c.WAKEUP_CAPTURE_INTERVAL,
) -> BoundedOutcome:
    if target <= 0 or capture_interval <= 0 or target % capture_interval != 0:
        raise D6R13ExecutionError("bounded_schedule")
    samples: list[design.DiagnosticMemorySample] = []
    source = None
    binding = None
    market_wakeups = 0
    current_timestamp_ns: int | None = None

    def capture(point: str) -> design.DiagnosticMemorySample:
        sample = design.DiagnosticMemorySample(
            capture_point=point,
            market_wakeups=(market_wakeups if market_wakeups else None),
            snapshot=deps.capture_memory(),
        )
        samples.append(sample)
        deps.persist_heartbeat(_capture_payload(samples, current_timestamp_ns))
        return sample

    baseline = capture("before_source_open")
    source_before = deps.source_identity()
    try:
        source = deps.open_source()
        capture("after_verified_memmap_open")
        _apply_madv_sequential(source)
        binding = deps.build_binding(source)
        capture("after_hftbacktest_binding_creation")

        while market_wakeups < target:
            rc = int(binding.bt.wait_next_feed(False, c.WAIT_NEXT_FEED_TIMEOUT_NS))
            if rc == 1:
                raise D6R13ExecutionError(f"end_of_data_before_target:{market_wakeups}:{target}")
            if rc != 2:
                raise D6R13ExecutionError(f"feed_rc:{rc}")
            market_wakeups += 1
            if market_wakeups > target:
                raise D6R13ExecutionError(c.TARGET_OVERSHOOT_ERROR)
            current_timestamp_ns = int(binding.bt.current_timestamp)
            if market_wakeups == 1 or market_wakeups % capture_interval == 0:
                current = capture(f"market_wakeup_{market_wakeups}")
                reason = design.hard_safety_abort_reason(baseline.snapshot, current.snapshot)
                if reason is not None:
                    raise D6R13ExecutionError(reason)

        position = float(binding.bt.position(0))
        working_order_count = int(len(binding.bt.orders(0)))
        if position != 0.0 or working_order_count != 0:
            raise D6R13ExecutionError("terminal_execution_state")
        capture("immediately_before_close")
        close_with_snapshots(binding, capture)
        if deps.source_identity() != source_before:
            raise D6R13ExecutionError("source_changed")
        return BoundedOutcome(
            market_wakeups=market_wakeups,
            terminal_reason=c.BOUNDED_TARGET_TERMINAL_REASON,
            memory_samples=tuple(samples),
            summary=design.summarize_memory_samples(samples),
            lifecycle=tuple(binding.lifecycle),
            position=position,
            working_order_count=working_order_count,
            source_unchanged=True,
        )
    finally:
        if binding is not None and not binding._closed:
            if not getattr(binding, "_d6r13_backtest_close_attempted", False):
                if not samples or samples[-1].capture_point != "immediately_before_close":
                    capture("immediately_before_close")
                close_with_snapshots(binding, capture)
        elif binding is None and source is not None and not source._closed:
            source.close()
            capture("after_memmap_close")


def atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, destination)


def create_one_shot_marker(path: Path, payload: Mapping[str, object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise D6R13ExecutionError("attempt_marker_exists") from exc
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_parent_attempt(child_runner: Callable[[], ChildProcessResult]) -> dict[str, object]:
    if c.ATTEMPT_MARKER_PATH.exists() or c.EVIDENCE_PATH.exists():
        raise D6R13ExecutionError("attempt_not_fresh")
    marker = {
        "experiment_id": c.EXPERIMENT_ID,
        "schema_version": c.SCHEMA_VERSION,
        "canonical_attempt": 1,
        "day": c.DAY,
        "bounded_wakeup_target": c.BOUNDED_WAKEUP_TARGET,
    }
    create_one_shot_marker(c.ATTEMPT_MARKER_PATH, marker)
    evidence: dict[str, object] = {
        **marker,
        "status": "FAIL",
        "failure_reason": None,
        "source_content_opened": False,
        **design.closed_evidence_flags(),
    }
    try:
        child = child_runner()
        evidence["child_return_code"] = child.returncode
        evidence["child_stdout_tail"] = child.stdout[-c.DIAGNOSTIC_TAIL_CHARS :]
        evidence["child_stderr_tail"] = child.stderr[-c.DIAGNOSTIC_TAIL_CHARS :]
        if child.returncode != 0:
            raise D6R13ExecutionError(f"child_return_code:{child.returncode}")
        payload = json.loads(child.stdout.splitlines()[-1])
        if payload.get("experiment_id") != c.EXPERIMENT_ID:
            raise D6R13ExecutionError("child_experiment_id")
        if payload.get("market_wakeups") != c.BOUNDED_WAKEUP_TARGET:
            raise D6R13ExecutionError("child_market_wakeups")
        evidence.update(payload)
        evidence["status"] = "PASS"
    except Exception as exc:
        evidence["failure_reason"] = f"{type(exc).__name__}:{exc}"
    finally:
        if c.MEMORY_HEARTBEAT_PATH.is_file():
            evidence["latest_heartbeat_sha256"] = _sha256(c.MEMORY_HEARTBEAT_PATH)
            heartbeat = json.loads(c.MEMORY_HEARTBEAT_PATH.read_text())
            evidence["latest_heartbeat"] = heartbeat
            evidence["memory_snapshots"] = heartbeat.get("memory_snapshots", []) if isinstance(heartbeat.get("memory_snapshots", []), list) else []
            if any(isinstance(item, dict) and item.get("capture_point") != "before_source_open" for item in evidence["memory_snapshots"]):
                evidence["source_content_opened"] = True
        atomic_write_json(c.EVIDENCE_PATH, evidence)
    return evidence


def run_real_parent(environ: Mapping[str, str] | None = None) -> int:
    require_execution_authorization(environ)
    result = preflight.run_preflight()
    if result.attempt_state != "FRESH":
        raise D6R13ExecutionError("preflight_attempt_state")

    def child_runner() -> ChildProcessResult:
        completed = subprocess.run(child_command(), text=True, capture_output=True, check=False, env=dict(os.environ))
        return ChildProcessResult(int(completed.returncode), completed.stdout, completed.stderr)

    evidence = run_parent_attempt(child_runner)
    return 0 if evidence["status"] == "PASS" else 1


def run_real_child(environ: Mapping[str, str] | None = None) -> int:
    require_execution_authorization(environ)
    from multimarket import dev045_d6r5_memmap_adapter as adapter
    from multimarket import dev045_d6r6_historical_driver as driver

    def source_identity() -> tuple[int, int, int, int]:
        observed = c.SOURCE_PATH.stat()
        return int(observed.st_dev), int(observed.st_ino), int(observed.st_size), int(observed.st_mtime_ns)

    deps = BoundedDependencies(
        capture_memory=memory.capture_memory_snapshot,
        open_source=lambda: adapter._open_verified_file(
            c.SOURCE_PATH,
            expected_sha256=c.SOURCE_SHA256,
            expected_bytes=c.SOURCE_BYTES,
            expected_rows=c.SOURCE_ROWS,
        ),
        build_binding=driver._build_lifetime_safe_binding,
        source_identity=source_identity,
        persist_heartbeat=lambda payload: atomic_write_json(c.MEMORY_HEARTBEAT_PATH, payload),
    )
    outcome = run_bounded_diagnostic(deps)
    print(json.dumps(outcome.to_evidence_dict(), sort_keys=True), flush=True)
    return 0


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
        "real_execution_enabled": c.REAL_EXECUTION_ENABLED,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(c.CHILD_RESOLUTION_SMOKE_FLAG, action="store_true")
    parser.add_argument(c.CHILD_FLAG, action="store_true")
    parser.add_argument(c.PREFLIGHT_FLAG, action="store_true")
    args = parser.parse_args(argv)
    if args.child_resolution_smoke:
        print(json.dumps(child_resolution_smoke_payload(), sort_keys=True), flush=True)
        return 0
    if args.preflight:
        print(json.dumps(preflight.run_preflight().to_dict(), sort_keys=True), flush=True)
        return 0
    if args.child:
        return run_real_child()
    return run_real_parent()


if __name__ == "__main__":
    raise SystemExit(main())

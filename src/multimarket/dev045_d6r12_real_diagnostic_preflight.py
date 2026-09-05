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
from multimarket import dev045_d6r12_memory_attributed_real_diagnostic as design
from multimarket import dev045_d6r12_real_diagnostic_preflight_contract as c


class D6R12PreflightError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreflightConfig:
    repo_root: Path
    source_path: Path
    source_rows: int
    source_bytes: int
    source_sha256: str
    source_lineage_evidence_path: Path
    source_lineage_evidence_sha256: str
    design_freeze_manifest_path: Path
    design_freeze_manifest_sha256: str
    d6r11_freeze_manifest_path: Path
    d6r11_freeze_manifest_sha256: str
    d6r10_evidence_path: Path
    d6r10_evidence_sha256: str
    d6r10_attempt_marker_path: Path
    d6r10_attempt_marker_sha256: str
    d6r10_heartbeat_path: Path
    d6r10_heartbeat_sha256: str
    runtime_root: Path
    attempt_marker_path: Path
    evidence_path: Path


@dataclass(frozen=True)
class PreflightDependencies:
    verify_git_lineage_and_cleanliness: Callable[[Path], None]
    installed_hftbacktest_version: Callable[[], str]
    capture_memory: Callable[[], memory.MemorySnapshot]


@dataclass(frozen=True)
class PreflightResult:
    source_stat_verified: bool
    source_content_opened: bool
    source_content_sha_verified: bool
    source_lineage_verified: bool
    hftbacktest_version: str
    memory_snapshot: memory.MemorySnapshot
    attempt_state: str

    def to_dict(self) -> dict[str, object]:
        return {
            "experiment_id": c.EXPERIMENT_ID,
            "preflight_id": c.PREFLIGHT_ID,
            "schema_version": c.SCHEMA_VERSION,
            "status": "PASS",
            "source_stat_verified": self.source_stat_verified,
            "source_content_opened": self.source_content_opened,
            "source_content_sha_verified": self.source_content_sha_verified,
            "source_lineage_verified": self.source_lineage_verified,
            "hftbacktest_version": self.hftbacktest_version,
            "memory_snapshot": self.memory_snapshot.to_dict(),
            "attempt_state": self.attempt_state,
            "real_execution_enabled": c.REAL_EXECUTION_ENABLED,
            "attempt_marker_created": False,
        }


@dataclass(frozen=True)
class BoundedDiagnosticDependencies:
    capture_memory: Callable[[], memory.MemorySnapshot]
    open_source: Callable[[], Any]
    build_binding: Callable[[Any], Any]
    source_identity: Callable[[], tuple[int, int, int, int]]
    persist_heartbeat: Callable[[dict[str, object]], None]


@dataclass(frozen=True)
class BoundedDiagnosticOutcome:
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
            "crossed_old_failure_region": (
                self.market_wakeups > c.OLD_D6R10_LAST_HEARTBEAT_WAKEUPS
            ),
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


def canonical_preflight_config(repo_root: Path | None = None) -> PreflightConfig:
    root = Path.cwd() if repo_root is None else Path(repo_root)
    return PreflightConfig(
        repo_root=root,
        source_path=c.SOURCE_PATH,
        source_rows=c.SOURCE_ROWS,
        source_bytes=c.SOURCE_BYTES,
        source_sha256=c.SOURCE_SHA256,
        source_lineage_evidence_path=root / c.SOURCE_LINEAGE_EVIDENCE_PATH,
        source_lineage_evidence_sha256=c.SOURCE_LINEAGE_EVIDENCE_SHA256,
        design_freeze_manifest_path=root / c.DESIGN_FREEZE_MANIFEST_PATH,
        design_freeze_manifest_sha256=c.DESIGN_FREEZE_MANIFEST_SHA256,
        d6r11_freeze_manifest_path=root / c.D6R11_FREEZE_MANIFEST_PATH,
        d6r11_freeze_manifest_sha256=c.D6R11_FREEZE_MANIFEST_SHA256,
        d6r10_evidence_path=root / c.D6R10_EVIDENCE_PATH,
        d6r10_evidence_sha256=c.D6R10_EVIDENCE_SHA256,
        d6r10_attempt_marker_path=c.D6R10_ATTEMPT_MARKER_PATH,
        d6r10_attempt_marker_sha256=c.D6R10_ATTEMPT_MARKER_SHA256,
        d6r10_heartbeat_path=c.D6R10_HEARTBEAT_PATH,
        d6r10_heartbeat_sha256=c.D6R10_HEARTBEAT_SHA256,
        runtime_root=c.RUNTIME_ROOT,
        attempt_marker_path=c.ATTEMPT_MARKER_PATH,
        evidence_path=root / c.EVIDENCE_PATH,
    )


def default_preflight_dependencies() -> PreflightDependencies:
    return PreflightDependencies(
        verify_git_lineage_and_cleanliness=_verify_git_lineage_and_cleanliness,
        installed_hftbacktest_version=lambda: importlib.metadata.version("hftbacktest"),
        capture_memory=memory.capture_memory_snapshot,
    )


def run_preflight(
    config: PreflightConfig | None = None,
    dependencies: PreflightDependencies | None = None,
) -> PreflightResult:
    cfg = canonical_preflight_config() if config is None else config
    deps = default_preflight_dependencies() if dependencies is None else dependencies

    deps.verify_git_lineage_and_cleanliness(cfg.repo_root)
    _verify_small_artifact(
        cfg.design_freeze_manifest_path,
        cfg.design_freeze_manifest_sha256,
        cfg.source_path,
        "design_freeze_manifest",
    )
    _verify_small_artifact(
        cfg.d6r11_freeze_manifest_path,
        cfg.d6r11_freeze_manifest_sha256,
        cfg.source_path,
        "d6r11_freeze_manifest",
    )
    _verify_small_artifact(
        cfg.d6r10_evidence_path,
        cfg.d6r10_evidence_sha256,
        cfg.source_path,
        "d6r10_evidence",
    )
    _verify_small_artifact(
        cfg.d6r10_attempt_marker_path,
        cfg.d6r10_attempt_marker_sha256,
        cfg.source_path,
        "d6r10_attempt_marker",
    )
    _verify_small_artifact(
        cfg.d6r10_heartbeat_path,
        cfg.d6r10_heartbeat_sha256,
        cfg.source_path,
        "d6r10_heartbeat",
    )

    _verify_source_stat_only(cfg.source_path, cfg.source_bytes)
    _verify_source_lineage(cfg)

    version = deps.installed_hftbacktest_version()
    if version != c.HFTBACKTEST_VERSION:
        raise D6R12PreflightError(f"hftbacktest_version:{version}")

    snapshot = deps.capture_memory()
    failure = design.preexecution_failure_reason(snapshot)
    if failure is not None:
        raise D6R12PreflightError(failure)

    runtime_root = cfg.runtime_root.resolve(strict=False)
    d6r10_root = c.D6R10_RUNTIME_ROOT.resolve(strict=False)
    if runtime_root == d6r10_root or runtime_root.is_relative_to(d6r10_root):
        raise D6R12PreflightError("runtime_namespace_not_distinct")

    state = design.attempt_state(
        marker_exists=cfg.attempt_marker_path.exists(),
        evidence_exists=cfg.evidence_path.exists(),
    )
    if state != "FRESH":
        raise D6R12PreflightError(f"attempt_state:{state}")

    return PreflightResult(
        source_stat_verified=True,
        source_content_opened=False,
        source_content_sha_verified=False,
        source_lineage_verified=True,
        hftbacktest_version=version,
        memory_snapshot=snapshot,
        attempt_state=state,
    )


def require_execution_authorization(environ: Mapping[str, str] | None = None) -> None:
    env = os.environ if environ is None else environ
    if env.get(c.AUTHORIZATION_ENV) != c.AUTHORIZATION_TOKEN:
        raise D6R12PreflightError("authorization_token")
    if not c.REAL_EXECUTION_ENABLED:
        raise D6R12PreflightError("execution_disabled_by_contract")


def run_bounded_diagnostic(
    deps: BoundedDiagnosticDependencies,
    *,
    target: int = c.BOUNDED_WAKEUP_TARGET,
    capture_interval: int = c.WAKEUP_CAPTURE_INTERVAL,
) -> BoundedDiagnosticOutcome:
    if target <= 0 or capture_interval <= 0 or target % capture_interval != 0:
        raise D6R12PreflightError("bounded_schedule")

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
        deps.persist_heartbeat(
            build_memory_heartbeat(
                samples,
                current_timestamp_ns=current_timestamp_ns,
            )
        )
        return sample

    baseline = capture("before_source_open")
    source_before = deps.source_identity()
    try:
        source = deps.open_source()
        capture("after_verified_memmap_open")
        _apply_madv_sequential(source)

        binding = deps.build_binding(source)
        capture("after_hftbacktest_binding_creation")

        while True:
            rc = int(binding.bt.wait_next_feed(False, c.WAIT_NEXT_FEED_TIMEOUT_NS))
            if rc == 1:
                raise D6R12PreflightError(
                    f"end_of_data_before_target:{market_wakeups}:{target}"
                )
            if rc != 2:
                raise D6R12PreflightError(f"feed_rc:{rc}")

            market_wakeups += 1
            if market_wakeups > target:
                raise D6R12PreflightError(c.TARGET_OVERSHOOT_ERROR)
            current_timestamp_ns = int(binding.bt.current_timestamp)

            if market_wakeups == 1 or market_wakeups % capture_interval == 0:
                current = capture(f"market_wakeup_{market_wakeups}")
                reason = design.hard_safety_abort_reason(
                    baseline.snapshot,
                    current.snapshot,
                )
                if reason is not None:
                    raise D6R12PreflightError(reason)

            if market_wakeups == target:
                break

        position = float(binding.bt.position(0))
        working_order_count = int(len(binding.bt.orders(0)))
        if position != 0.0 or working_order_count != 0:
            raise D6R12PreflightError("terminal_execution_state")

        capture("immediately_before_close")
        close_with_separate_snapshots(binding, capture)
        source_after = deps.source_identity()
        if source_after != source_before:
            raise D6R12PreflightError("source_changed")

        summary = design.summarize_memory_samples(samples)
        return BoundedDiagnosticOutcome(
            market_wakeups=market_wakeups,
            terminal_reason=c.BOUNDED_TARGET_TERMINAL_REASON,
            memory_samples=tuple(samples),
            summary=summary,
            lifecycle=tuple(binding.lifecycle),
            position=position,
            working_order_count=working_order_count,
            source_unchanged=True,
        )
    finally:
        if binding is not None and not binding._closed:
            close_already_attempted = (
                getattr(binding, "_d6r12_backtest_close_attempted", False)
                or getattr(binding, "_d6r12_memmap_close_attempted", False)
            )
            if not close_already_attempted:
                if not samples or samples[-1].capture_point != "immediately_before_close":
                    capture("immediately_before_close")
                close_with_separate_snapshots(binding, capture)
        elif binding is None and source is not None and not source._closed:
            source.close()
            capture("after_memmap_close")


def close_with_separate_snapshots(
    binding: Any,
    capture: Callable[[str], design.DiagnosticMemorySample],
) -> None:
    if binding._closed:
        return

    rc = int(getattr(binding, "_d6r12_backtest_close_rc", 0))
    capture_error: BaseException | None = None
    if not getattr(binding, "_d6r12_backtest_closed", False):
        if getattr(binding, "_d6r12_backtest_close_attempted", False):
            raise D6R12PreflightError("backtest_close_incomplete")
        binding._d6r12_backtest_close_attempted = True
        rc = int(binding.bt.close())
        binding._d6r12_backtest_close_rc = rc
        binding._d6r12_backtest_closed = True
        binding.lifecycle.append("backtest_closed")
        try:
            capture("after_backtest_close")
        except BaseException as exc:
            capture_error = exc

    if not getattr(binding, "_d6r12_memmap_closed", False):
        if getattr(binding, "_d6r12_memmap_close_attempted", False):
            raise D6R12PreflightError("memmap_close_incomplete")
        binding._d6r12_memmap_close_attempted = True
        binding.source.close()
        binding._d6r12_memmap_closed = True
        binding.lifecycle.append("memmap_closed")
        binding._closed = True
        capture("after_memmap_close")

    if capture_error is not None:
        raise capture_error
    if rc != 0:
        raise D6R12PreflightError(f"backtest_close_rc:{rc}")


def build_memory_heartbeat(
    samples: Sequence[design.DiagnosticMemorySample],
    *,
    current_timestamp_ns: int | None,
) -> dict[str, object]:
    if not samples:
        raise D6R12PreflightError("heartbeat_samples_empty")
    latest = samples[-1]
    summary = design.summarize_memory_samples(samples)
    process = latest.snapshot.process.to_dict()
    payload: dict[str, object] = {
        "experiment_id": c.EXPERIMENT_ID,
        "schema_version": c.SCHEMA_VERSION,
        "capture_point": latest.capture_point,
        "market_wakeups": latest.market_wakeups or 0,
        "current_timestamp_ns": current_timestamp_ns,
        "MemAvailable_bytes": latest.snapshot.mem_available_bytes,
        "smaps_rollup_available": latest.snapshot.smaps_rollup is not None,
        "smaps_rollup": (
            None
            if latest.snapshot.smaps_rollup is None
            else latest.snapshot.smaps_rollup.to_dict()
        ),
        "current_summary": summary.to_dict(),
        "memory_snapshots": [sample.to_dict() for sample in samples],
        "updated_at_utc": latest.snapshot.captured_at_utc,
    }
    payload.update(process)
    return payload


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
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise D6R12PreflightError("attempt_marker_exists") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        # An ambiguous start consumes the attempt, so retain the exclusive marker.
        raise


def run_parent_attempt(
    *,
    marker_path: Path,
    evidence_path: Path,
    heartbeat_path: Path,
    child_runner: Callable[[], ChildProcessResult],
) -> dict[str, object]:
    state = design.attempt_state(
        marker_exists=Path(marker_path).exists(),
        evidence_exists=Path(evidence_path).exists(),
    )
    if state != "FRESH":
        raise D6R12PreflightError(f"attempt_state:{state}")

    marker = {
        "experiment_id": c.EXPERIMENT_ID,
        "schema_version": c.SCHEMA_VERSION,
        "canonical_attempt": 1,
        "day": c.DAY,
        "bounded_wakeup_target": c.BOUNDED_WAKEUP_TARGET,
    }
    create_one_shot_marker(marker_path, marker)

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
        evidence["child_stdout_sha256"] = hashlib.sha256(child.stdout.encode()).hexdigest()
        evidence["child_stderr_sha256"] = hashlib.sha256(child.stderr.encode()).hexdigest()
        evidence["child_stdout_tail"] = child.stdout[-c.DIAGNOSTIC_TAIL_CHARS :]
        evidence["child_stderr_tail"] = child.stderr[-c.DIAGNOSTIC_TAIL_CHARS :]
        if child.returncode != 0:
            raise D6R12PreflightError(f"child_return_code:{child.returncode}")
        child_payload = json.loads(child.stdout.splitlines()[-1])
        _validate_child_success_payload(child_payload)
        evidence.update(child_payload)
        evidence["status"] = "PASS"
    except Exception as exc:
        evidence["failure_reason"] = f"{type(exc).__name__}:{exc}"
    finally:
        if Path(heartbeat_path).is_file():
            evidence["latest_heartbeat_sha256"] = _sha256_small_artifact(
                Path(heartbeat_path),
                source_path=Path("/__not_the_source__"),
            )
            heartbeat = json.loads(Path(heartbeat_path).read_text())
            evidence["latest_heartbeat"] = heartbeat
            snapshots = heartbeat.get("memory_snapshots", [])
            if not isinstance(snapshots, list):
                snapshots = []
            evidence["memory_snapshots"] = snapshots
            if any(
                isinstance(item, dict)
                and item.get("capture_point") != "before_source_open"
                for item in snapshots
            ):
                evidence["source_content_opened"] = True
        atomic_write_json(evidence_path, evidence)
    return evidence


def run_real_parent(environ: Mapping[str, str] | None = None) -> int:
    require_execution_authorization(environ)
    preflight = run_preflight()
    if preflight.attempt_state != "FRESH":
        raise D6R12PreflightError("preflight_attempt_state")

    def child_runner() -> ChildProcessResult:
        completed = subprocess.run(
            [sys.executable, "-m", __name__, "--child"],
            text=True,
            capture_output=True,
            check=False,
            env=dict(os.environ),
        )
        return ChildProcessResult(completed.returncode, completed.stdout, completed.stderr)

    evidence = run_parent_attempt(
        marker_path=c.ATTEMPT_MARKER_PATH,
        evidence_path=c.EVIDENCE_PATH,
        heartbeat_path=c.MEMORY_HEARTBEAT_PATH,
        child_runner=child_runner,
    )
    return 0 if evidence["status"] == "PASS" else 1


def run_real_child(environ: Mapping[str, str] | None = None) -> int:
    require_execution_authorization(environ)
    from multimarket import dev045_d6r5_memmap_adapter as adapter
    from multimarket import dev045_d6r6_historical_driver as driver

    def source_identity() -> tuple[int, int, int, int]:
        observed = c.SOURCE_PATH.stat()
        return (
            int(observed.st_dev),
            int(observed.st_ino),
            int(observed.st_size),
            int(observed.st_mtime_ns),
        )

    deps = BoundedDiagnosticDependencies(
        capture_memory=memory.capture_memory_snapshot,
        open_source=lambda: adapter._open_verified_file(
            c.SOURCE_PATH,
            expected_sha256=c.SOURCE_SHA256,
            expected_bytes=c.SOURCE_BYTES,
            expected_rows=c.SOURCE_ROWS,
        ),
        build_binding=driver._build_lifetime_safe_binding,
        source_identity=source_identity,
        persist_heartbeat=lambda payload: atomic_write_json(
            c.MEMORY_HEARTBEAT_PATH,
            payload,
        ),
    )
    outcome = run_bounded_diagnostic(deps)
    print(json.dumps(outcome.to_evidence_dict(), sort_keys=True), flush=True)
    return 0


def _verify_source_stat_only(path: Path, expected_bytes: int) -> None:
    try:
        observed = os.stat(path, follow_symlinks=True)
    except OSError as exc:
        raise D6R12PreflightError("source_stat") from exc
    if not stat.S_ISREG(observed.st_mode):
        raise D6R12PreflightError("source_not_regular")
    if int(observed.st_size) != expected_bytes:
        raise D6R12PreflightError(f"source_bytes:{observed.st_size}")


def _validate_child_success_payload(payload: Mapping[str, object]) -> None:
    required = {
        "bounded_wakeup_reached": True,
        "market_wakeups": c.BOUNDED_WAKEUP_TARGET,
        "terminal_reason": c.BOUNDED_TARGET_TERMINAL_REASON,
        "crossed_old_failure_region": True,
        "source_unchanged": True,
        "position": 0.0,
        "working_order_count": 0,
        "full_day_attempted": False,
        "full_day_validated": False,
        "orders": False,
        "policy_execution": False,
        "historical_pnl": False,
    }
    for name, expected in required.items():
        if payload.get(name) != expected:
            raise D6R12PreflightError(f"child_success_invariant:{name}")
    lifecycle = payload.get("lifecycle")
    if not isinstance(lifecycle, list) or lifecycle[-2:] != [
        "backtest_closed",
        "memmap_closed",
    ]:
        raise D6R12PreflightError("child_success_invariant:lifecycle")
    snapshots = payload.get("memory_snapshots")
    if not isinstance(snapshots, list):
        raise D6R12PreflightError("child_success_invariant:memory_snapshots")
    points = [item.get("capture_point") for item in snapshots if isinstance(item, dict)]
    for required_point in c.LIFECYCLE_CAPTURE_POINTS:
        if required_point not in points:
            raise D6R12PreflightError(
                f"child_success_invariant:snapshot:{required_point}"
            )
    wakeup_points = {
        item.get("market_wakeups")
        for item in snapshots
        if isinstance(item, dict) and str(item.get("capture_point", "")).startswith("market_wakeup_")
    }
    if not set(design.wakeup_snapshot_schedule()).issubset(wakeup_points):
        raise D6R12PreflightError("child_success_invariant:wakeup_snapshots")


def _verify_source_lineage(config: PreflightConfig) -> None:
    _verify_small_artifact(
        config.source_lineage_evidence_path,
        config.source_lineage_evidence_sha256,
        config.source_path,
        "source_lineage_evidence",
    )
    try:
        payload = json.loads(config.source_lineage_evidence_path.read_text())
    except Exception as exc:
        raise D6R12PreflightError("source_lineage_json") from exc
    output_sha = payload.get("output_sha256") or (payload.get("v2") or {}).get(
        "output_sha256"
    )
    header = payload.get("output_header") or {}
    if payload.get("status") != "PASS":
        raise D6R12PreflightError("source_lineage_status")
    if output_sha != config.source_sha256:
        raise D6R12PreflightError("source_lineage_sha256")
    if int(header.get("rows", -1)) != config.source_rows:
        raise D6R12PreflightError("source_lineage_rows")
    if int(header.get("output_bytes", -1)) != config.source_bytes:
        raise D6R12PreflightError("source_lineage_bytes")


def _verify_small_artifact(
    path: Path,
    expected_sha256: str,
    source_path: Path,
    label: str,
) -> None:
    observed = _sha256_small_artifact(path, source_path=source_path)
    if observed != expected_sha256:
        raise D6R12PreflightError(f"{label}_sha256:{observed}")


def _sha256_small_artifact(path: Path, *, source_path: Path) -> str:
    target = Path(path)
    if target.resolve(strict=False) == Path(source_path).resolve(strict=False):
        raise D6R12PreflightError("source_content_hash_forbidden_in_preflight")
    try:
        size = target.stat().st_size
    except OSError as exc:
        raise D6R12PreflightError(f"artifact_stat:{target}") from exc
    if size > c.MAX_SMALL_ARTIFACT_HASH_BYTES:
        raise D6R12PreflightError(f"artifact_too_large:{target}:{size}")
    digest = hashlib.sha256()
    try:
        with target.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise D6R12PreflightError(f"artifact_read:{target}") from exc
    return digest.hexdigest()


def _verify_git_lineage_and_cleanliness(repo_root: Path) -> None:
    root = Path(repo_root)

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )

    parent = git("show", "-s", "--format=%P", c.PARENT_HEAD)
    if parent.returncode != 0 or parent.stdout.strip() != c.DESIGN_HEAD:
        raise D6R12PreflightError("git_frozen_parent")
    ancestor = git("merge-base", "--is-ancestor", c.PARENT_HEAD, "HEAD")
    if ancestor.returncode != 0:
        raise D6R12PreflightError("git_lineage")
    if git("diff", "--quiet").returncode != 0:
        raise D6R12PreflightError("tracked_worktree_dirty")
    if git("diff", "--cached", "--quiet").returncode != 0:
        raise D6R12PreflightError("index_dirty")


def _apply_madv_sequential(source: Any) -> None:
    mapped = getattr(source.data, "_mmap", None)
    if (
        c.MADV_SEQUENTIAL_IF_SUPPORTED
        and mapped is not None
        and hasattr(mapped, "madvise")
        and hasattr(mmap, "MADV_SEQUENTIAL")
    ):
        mapped.madvise(mmap.MADV_SEQUENTIAL)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--child", action="store_true")
    args = parser.parse_args(argv)
    if args.preflight and args.child:
        raise D6R12PreflightError("mode")
    if args.preflight:
        print(json.dumps(run_preflight().to_dict(), sort_keys=True))
        return 0
    if args.child:
        return run_real_child()
    return run_real_parent()


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
from typing import Callable

from multimarket import dev045_d6r11_memory_attribution as memory
from multimarket import dev045_d6r12_memory_attributed_real_diagnostic as design
from multimarket import dev045_d6r13_child_launch_successor as launcher
from multimarket import dev045_d6r13_real_diagnostic_successor_preflight_contract as c


class D6R13PreflightError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreflightDependencies:
    capture_memory: Callable[[], memory.MemorySnapshot]
    installed_hftbacktest_version: Callable[[], str]


@dataclass(frozen=True)
class PreflightResult:
    source_stat_verified: bool
    source_content_opened: bool
    source_content_sha_verified: bool
    source_lineage_verified: bool
    launcher_smoke_verified: bool
    hftbacktest_version: str
    attempt_state: str
    memory_snapshot: memory.MemorySnapshot

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
            "launcher_smoke_verified": self.launcher_smoke_verified,
            "hftbacktest_version": self.hftbacktest_version,
            "attempt_state": self.attempt_state,
            "memory_snapshot": self.memory_snapshot.to_dict(),
            "real_execution_enabled": c.REAL_EXECUTION_ENABLED,
            "attempt_marker_created": False,
            "heartbeat_created": False,
        }


def _sha256_small(path: Path) -> str:
    if path.resolve(strict=False) == c.SOURCE_PATH.resolve(strict=False):
        raise D6R13PreflightError("source_hash_forbidden_in_preflight")
    size = path.stat().st_size
    if size > c.MAX_SMALL_ARTIFACT_HASH_BYTES:
        raise D6R13PreflightError(f"artifact_too_large:{path}:{size}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_small(path: Path, expected: str, label: str) -> None:
    observed = _sha256_small(path)
    if observed != expected:
        raise D6R13PreflightError(f"{label}_sha256:{observed}")


def _verify_source_stat_only() -> None:
    observed = os.stat(c.SOURCE_PATH, follow_symlinks=True)
    if not stat.S_ISREG(observed.st_mode):
        raise D6R13PreflightError("source_not_regular")
    if int(observed.st_size) != c.SOURCE_BYTES:
        raise D6R13PreflightError(f"source_bytes:{observed.st_size}")


def _verify_source_lineage(repo_root: Path) -> None:
    path = repo_root / c.SOURCE_LINEAGE_EVIDENCE_PATH
    _verify_small(path, c.SOURCE_LINEAGE_EVIDENCE_SHA256, "source_lineage")
    payload = json.loads(path.read_text())
    output_sha = payload.get("output_sha256") or (payload.get("v2") or {}).get("output_sha256")
    header = payload.get("output_header") or {}
    if payload.get("status") != "PASS":
        raise D6R13PreflightError("source_lineage_status")
    if output_sha != c.SOURCE_SHA256:
        raise D6R13PreflightError("source_lineage_sha256")
    if int(header.get("rows", -1)) != c.SOURCE_ROWS:
        raise D6R13PreflightError("source_lineage_rows")
    if int(header.get("output_bytes", -1)) != c.SOURCE_BYTES:
        raise D6R13PreflightError("source_lineage_bytes")


def run_preflight(repo_root: Path | None = None, deps: PreflightDependencies | None = None) -> PreflightResult:
    root = Path.cwd() if repo_root is None else Path(repo_root)
    dependencies = deps or PreflightDependencies(
        capture_memory=memory.capture_memory_snapshot,
        installed_hftbacktest_version=lambda: importlib.metadata.version("hftbacktest"),
    )

    _verify_small(root / c.D6R13_DESIGN_FREEZE_MANIFEST_PATH, c.D6R13_DESIGN_FREEZE_MANIFEST_SHA256, "d6r13_design_freeze")
    _verify_small(root / c.D6R12_FAILURE_FREEZE_PATH, c.D6R12_FAILURE_FREEZE_SHA256, "d6r12_failure_freeze")
    _verify_small(root / c.D6R12_FAILURE_EVIDENCE_PATH, c.D6R12_FAILURE_EVIDENCE_SHA256, "d6r12_failure_evidence")

    _verify_source_stat_only()
    _verify_source_lineage(root)

    version = dependencies.installed_hftbacktest_version()
    if version != c.HFTBACKTEST_VERSION:
        raise D6R13PreflightError(f"hftbacktest_version:{version}")

    snapshot = dependencies.capture_memory()
    reason = design.preexecution_failure_reason(snapshot)
    if reason is not None:
        raise D6R13PreflightError(reason)

    state = design.attempt_state(
        marker_exists=c.ATTEMPT_MARKER_PATH.exists(),
        evidence_exists=(root / c.EVIDENCE_PATH).exists(),
    )
    if state != "FRESH":
        raise D6R13PreflightError(f"attempt_state:{state}")

    smoke = launcher.run_smoke_parent()
    launcher.validate_smoke_payload(smoke.payload)

    if c.PROHIBITED_EXECUTION_FLAGS != (False,) * len(c.PROHIBITED_EXECUTION_FLAGS):
        raise D6R13PreflightError("execution_surface_open")

    return PreflightResult(
        source_stat_verified=True,
        source_content_opened=False,
        source_content_sha_verified=False,
        source_lineage_verified=True,
        launcher_smoke_verified=True,
        hftbacktest_version=version,
        attempt_state=state,
        memory_snapshot=snapshot,
    )

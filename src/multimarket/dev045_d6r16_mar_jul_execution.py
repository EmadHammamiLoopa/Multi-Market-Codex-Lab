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
from multimarket import dev045_d6r10_feb_jul_v2_hft_ingestion as d6r10_witness
from multimarket import dev045_d6r14_memory_policy as policy
from multimarket import dev045_d6r16_mar_jul_contract as c


class D6R16ExecutionError(RuntimeError):
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
    first_timestamp_ns: int
    last_timestamp_ns: int
    memory_samples: tuple[diagnostic.DiagnosticMemorySample, ...]
    lifecycle: tuple[str, ...]
    position: float
    working_order_count: int
    source_unchanged: bool
    terminal_classification: str

    def to_evidence_dict(
        self,
        spec: c.DaySpec,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "experiment_id": c.EXPERIMENT_ID,
            "schema_version": c.SCHEMA_VERSION,
            "day": spec.day,
            "symbol": c.SYMBOL,
            "exchange": c.EXCHANGE,
            "mode": c.MODE,
            "source_path": str(spec.path),
            "source_sha256": spec.sha256,
            "source_rows": spec.rows,
            "source_bytes": spec.bytes,
            "source_content_opened": True,
            "source_verified_by_adapter": True,
            "mar_to_jul_feed_opened": True,
            "natural_end_of_data_reached": True,
            "fixed_wakeup_stop_target": None,
            "market_wakeups": self.market_wakeups,
            "first_timestamp_ns": self.first_timestamp_ns,
            "last_timestamp_ns": self.last_timestamp_ns,
            "terminal_classification": self.terminal_classification,
            "full_day_validated": (
                self.terminal_classification
                == "PASS_NATURAL_END_OF_DATA"
            ),
            "memory_snapshots": [
                sample.to_dict()
                for sample in self.memory_samples
            ],
            "memory_summary": (
                diagnostic.summarize_memory_samples(
                    self.memory_samples
                ).to_dict()
            ),
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


def marker_path(spec: c.DaySpec) -> Path:
    return c.RUNTIME_ROOT / spec.day / "ATTEMPT_STARTED.json"


def heartbeat_path(spec: c.DaySpec) -> Path:
    return c.RUNTIME_ROOT / spec.day / "MEMORY_HEARTBEAT.json"


def evidence_path(spec: c.DaySpec) -> Path:
    return Path(
        f"evidence/dev045_d6r16_{spec.day}.json"
    )


def closed_surface_flags() -> dict[str, bool]:
    return {
        "feb01_opened": False,
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
        raise D6R16ExecutionError("authorization_token")

    if c.AUTHORIZED_EXECUTION_FLAGS != (
        True,
    ) * len(c.AUTHORIZED_EXECUTION_FLAGS):
        raise D6R16ExecutionError(
            "authorized_execution_flags"
        )

    if c.PROHIBITED_EXECUTION_FLAGS != (
        False,
    ) * len(c.PROHIBITED_EXECUTION_FLAGS):
        raise D6R16ExecutionError(
            "prohibited_execution_flags"
        )


def child_command(
    day: str | None = None,
    *,
    smoke: bool = False,
) -> list[str]:
    if smoke:
        command = [
            sys.executable,
            "-m",
            c.CHILD_MODULE_NAME,
            c.CHILD_RESOLUTION_SMOKE_FLAG,
        ]
    else:
        if day not in c.DAY_BY_NAME:
            raise D6R16ExecutionError("child_day")
        command = [
            sys.executable,
            "-m",
            c.CHILD_MODULE_NAME,
            c.CHILD_FLAG,
            day,
        ]

    if "__main__" in command:
        raise D6R16ExecutionError(
            "child_command_uses_main"
        )

    return command


def child_resolution_smoke_payload() -> dict[str, object]:
    return {
        "status": "PASS",
        "experiment_id": c.EXPERIMENT_ID,
        "runtime_name": __name__,
        "resolved_module_name": c.CHILD_MODULE_NAME,
        "canonical_data_opened": False,
        "mar_to_jul_opened": False,
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
        raise D6R16ExecutionError(
            f"child_resolution_return_code:{completed.returncode}"
        )

    lines = [
        x for x in completed.stdout.splitlines()
        if x.strip()
    ]

    if not lines:
        raise D6R16ExecutionError(
            "child_resolution_stdout_empty"
        )

    payload = json.loads(lines[-1])

    required = {
        "status": "PASS",
        "experiment_id": c.EXPERIMENT_ID,
        "runtime_name": "__main__",
        "resolved_module_name": c.CHILD_MODULE_NAME,
        "canonical_data_opened": False,
        "mar_to_jul_opened": False,
        "attempt_marker_created": False,
        "heartbeat_created": False,
        "hftbacktest_canonical_run": False,
        "full_day_attempted": False,
        "real_execution_enabled": True,
    }

    for key, expected in required.items():
        if payload.get(key) != expected:
            raise D6R16ExecutionError(
                f"child_resolution_invariant:{key}"
            )

    return payload


def _sha256_small(path: Path) -> str:
    p = Path(path)

    if not p.is_file():
        raise D6R16ExecutionError(
            f"small_artifact_missing:{p}"
        )

    if p.stat().st_size > 2 * 1024 * 1024:
        raise D6R16ExecutionError(
            f"small_artifact_too_large:{p}"
        )

    h = hashlib.sha256()

    with p.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def _git_blob_sha1(path: Path) -> str:
    completed = subprocess.run(
        ["git", "hash-object", "--", str(Path(path))],
        text=True,
        capture_output=True,
        check=False,
    )

    observed = completed.stdout.strip()

    if completed.returncode != 0 or not observed:
        raise D6R16ExecutionError(
            f"git_hash_object:{path}:{completed.returncode}"
        )

    return observed


def verify_lineage_witness(
    spec: c.DaySpec,
) -> None:
    if (
        d6r10_witness.PARENT_D6R9B_HEAD
        != c.D6R9B_PARENT_HEAD
    ):
        raise D6R16ExecutionError(
            "d6r10_witness_parent_d6r9b_head"
        )

    witness = d6r10_witness.DAY_BY_NAME.get(
        spec.day
    )

    if witness is None:
        raise D6R16ExecutionError(
            f"d6r10_witness_day_missing:{spec.day}"
        )

    expected = (
        spec.path,
        spec.rows,
        spec.bytes,
        spec.sha256,
        spec.lineage_evidence,
        spec.lineage_evidence_sha256,
    )

    observed = (
        witness.path,
        witness.rows,
        witness.bytes,
        witness.sha256,
        witness.lineage_evidence,
        witness.lineage_evidence_sha256,
    )

    if observed != expected:
        raise D6R16ExecutionError(
            f"d6r10_witness_identity:{spec.day}"
        )


def _verify_lineage(
    spec: c.DaySpec,
) -> str:
    # The downstream D6R10 frozen contract is always checked.
    verify_lineage_witness(spec)

    # Preferred path: original D6R9B daily evidence exists.
    if spec.lineage_evidence.is_file():
        if (
            _sha256_small(spec.lineage_evidence)
            != spec.lineage_evidence_sha256
        ):
            raise D6R16ExecutionError(
                f"lineage_sha256:{spec.day}"
            )

        payload = json.loads(
            spec.lineage_evidence.read_text(
                encoding="utf-8"
            )
        )

        if payload.get("status") != "PASS":
            raise D6R16ExecutionError(
                f"lineage_status:{spec.day}"
            )

        observed_sha = (
            payload.get("output_sha256")
            or (payload.get("v2") or {}).get(
                "output_sha256"
            )
        )

        observed_rows = (
            payload.get("output_header") or {}
        ).get("rows")

        if (
            observed_sha != spec.sha256
            or observed_rows != spec.rows
        ):
            raise D6R16ExecutionError(
                f"lineage_output_identity:{spec.day}"
            )

        return "ORIGINAL_D6R9B_DAILY_EVIDENCE"

    # No reconstruction or fabricated replacement is allowed.
    return c.LINEAGE_WITNESS_MODE


def day_state(spec: c.DaySpec) -> str:
    marker = marker_path(spec)
    heartbeat = heartbeat_path(spec)
    evidence = evidence_path(spec)

    if (
        not marker.exists()
        and not heartbeat.exists()
        and not evidence.exists()
    ):
        return "FRESH"

    if (
        marker.is_file()
        and heartbeat.is_file()
        and evidence.is_file()
    ):
        try:
            payload = json.loads(
                evidence.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            return "CONSUMED_NONPASS"

        if (
            payload.get("experiment_id")
            == c.EXPERIMENT_ID
            and payload.get("day")
            == spec.day
            and payload.get("status")
            == "PASS"
        ):
            return "FROZEN_PASS"

    return "CONSUMED_NONPASS"


def sequence_plan(
    states: Sequence[str],
) -> tuple[str, ...]:
    if len(states) != len(c.DAY_SPECS):
        raise D6R16ExecutionError(
            "sequence_state_count"
        )

    actions: list[str] = []
    seen_fresh = False

    for state in states:
        if state == "CONSUMED_NONPASS":
            raise D6R16ExecutionError(
                "sequence_contains_consumed_nonpass"
            )

        if state == "FRESH":
            seen_fresh = True
            actions.append("RUN_FRESH")
            continue

        if state == "FROZEN_PASS":
            if seen_fresh:
                raise D6R16ExecutionError(
                    "nonprefix_frozen_pass"
                )
            actions.append("SKIP_FROZEN_PASS")
            continue

        raise D6R16ExecutionError(
            f"unknown_day_state:{state}"
        )

    return tuple(actions)


def run_preflight() -> dict[str, object]:
    if (
        _sha256_small(
            c.PARENT_D6R15_FREEZE_MANIFEST_PATH
        )
        != c.PARENT_D6R15_FREEZE_MANIFEST_SHA256
    ):
        raise D6R16ExecutionError(
            "parent_d6r15_freeze_manifest_sha"
        )

    parent = json.loads(
        c.PARENT_D6R15_FREEZE_MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    if (
        parent.get("status")
        != "FROZEN_CANONICAL_FULL_DAY_PASS"
    ):
        raise D6R16ExecutionError(
            "parent_d6r15_status"
        )

    if parent.get("rerun_forbidden") is not True:
        raise D6R16ExecutionError(
            "parent_d6r15_rerun_guard"
        )

    if (
        _git_blob_sha1(
            c.D6R9B_AUTHORIZATION_PATH
        )
        != c.D6R9B_AUTHORIZATION_GIT_BLOB_SHA1
    ):
        raise D6R16ExecutionError(
            "d6r9b_authorization_blob_sha"
        )

    if (
        _git_blob_sha1(
            c.D6R10_LINEAGE_WITNESS_PATH
        )
        != c.D6R10_LINEAGE_WITNESS_GIT_BLOB_SHA1
    ):
        raise D6R16ExecutionError(
            "d6r10_lineage_witness_blob_sha"
        )

    observed_days: list[dict[str, object]] = []

    for spec in c.DAY_SPECS:
        lineage_mode = _verify_lineage(spec)

        st = spec.path.stat()

        if not stat.S_ISREG(st.st_mode):
            raise D6R16ExecutionError(
                f"source_not_regular:{spec.day}"
            )

        if int(st.st_size) != spec.bytes:
            raise D6R16ExecutionError(
                f"source_bytes:{spec.day}:{st.st_size}"
            )

        observed_days.append(
            {
                "day": spec.day,
                "source_stat_verified": True,
                "source_bytes": int(st.st_size),
                "source_content_opened": False,
                "source_content_hashed": False,
                "lineage_verification_mode": lineage_mode,
                "original_daily_lineage_evidence_present": (
                    spec.lineage_evidence.is_file()
                ),
                "attempt_state": day_state(spec),
            }
        )

    states = tuple(
        str(x["attempt_state"])
        for x in observed_days
    )

    actions = sequence_plan(states)

    hft_version = importlib.metadata.version(
        "hftbacktest"
    )

    if hft_version != c.HFTBACKTEST_VERSION:
        raise D6R16ExecutionError(
            f"hftbacktest_version:{hft_version}"
        )

    snapshot = memory.capture_memory_snapshot()

    if (
        snapshot.mem_available_bytes
        < c.PREEXEC_MIN_MEMAVAILABLE_BYTES
    ):
        raise D6R16ExecutionError(
            "preexec_memavailable"
        )

    smoke = run_child_resolution_smoke()

    return {
        "experiment_id": c.EXPERIMENT_ID,
        "status": "PASS",
        "stage_mode": c.STAGE_MODE,
        "days": observed_days,
        "sequence_actions": list(actions),
        "all_days_fresh": all(
            x == "FRESH"
            for x in states
        ),
        "source_content_opened": False,
        "source_content_hashed": False,
        "hftbacktest_version": hft_version,
        "mem_available_bytes": (
            snapshot.mem_available_bytes
        ),
        "launcher_smoke_verified": (
            smoke.get("status") == "PASS"
        ),
        "real_execution_performed": False,
        "feb01_rerun": False,
        "d6r12_rerun": False,
        "d6r13_rerun": False,
        "d6r15_rerun": False,
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
        ) + "\n",
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
        ) + "\n"
    ).encode()

    try:
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise D6R16ExecutionError(
            "attempt_marker_exists"
        ) from exc

    with os.fdopen(
        descriptor,
        "wb",
    ) as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def _required_swap(
    snapshot: memory.MemorySnapshot,
) -> int:
    value = snapshot.process.vm_swap_bytes

    if value is None:
        raise D6R16ExecutionError(
            "vm_swap_unavailable"
        )

    return int(value)


def _memory_abort_reason(
    *,
    baseline_swap_bytes: int,
    baseline_rss_anon_bytes: int,
    snapshot: memory.MemorySnapshot,
) -> str | None:
    return policy.memory_abort_reason(
        baseline_swap_bytes=baseline_swap_bytes,
        current_swap_bytes=_required_swap(snapshot),
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
    *,
    spec: c.DaySpec,
    samples: Sequence[
        diagnostic.DiagnosticMemorySample
    ],
    current_timestamp_ns: int | None,
) -> dict[str, object]:
    latest = samples[-1]

    payload: dict[str, object] = {
        "experiment_id": c.EXPERIMENT_ID,
        "schema_version": c.SCHEMA_VERSION,
        "day": spec.day,
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
            "_d6r16_backtest_close_attempted",
            False,
        ):
            binding._d6r16_backtest_close_attempted = True
            close_rc = int(binding.bt.close())
            binding.lifecycle.append(
                "backtest_closed"
            )
            capture("after_backtest_close")
    finally:
        if not getattr(
            binding,
            "_d6r16_memmap_close_attempted",
            False,
        ):
            binding._d6r16_memmap_close_attempted = True
            binding.source.close()
            binding.lifecycle.append(
                "memmap_closed"
            )
            binding._closed = True
            capture("after_memmap_close")

    if close_rc is not None and close_rc != 0:
        raise D6R16ExecutionError(
            f"backtest_close_rc:{close_rc}"
        )


def run_full_day_feed(
    spec: c.DaySpec,
    deps: FullDayDependencies,
    *,
    capture_interval: int = c.WAKEUP_CAPTURE_INTERVAL,
) -> FullDayOutcome:
    if capture_interval <= 0:
        raise D6R16ExecutionError(
            "capture_interval"
        )

    samples: list[
        diagnostic.DiagnosticMemorySample
    ] = []

    source = None
    binding = None
    market_wakeups = 0
    first_timestamp_ns: int | None = None
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
                spec=spec,
                samples=samples,
                current_timestamp_ns=(
                    current_timestamp_ns
                ),
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
        raise D6R16ExecutionError(
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
            raise D6R16ExecutionError(reason)

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
                raise D6R16ExecutionError(
                    f"feed_rc:{spec.day}:{rc}"
                )

            market_wakeups += 1
            current_timestamp_ns = int(
                binding.bt.current_timestamp
            )

            if first_timestamp_ns is None:
                first_timestamp_ns = (
                    current_timestamp_ns
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
                    raise D6R16ExecutionError(
                        reason
                    )

        if (
            market_wakeups <= 0
            or first_timestamp_ns is None
            or current_timestamp_ns is None
        ):
            raise D6R16ExecutionError(
                f"empty_feed:{spec.day}"
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
            raise D6R16ExecutionError(reason)

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
            raise D6R16ExecutionError(
                f"terminal_execution_state:{spec.day}"
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
            raise D6R16ExecutionError(
                "terminal_classification:"
                f"{spec.day}:{classification}"
            )

        return FullDayOutcome(
            market_wakeups=market_wakeups,
            first_timestamp_ns=(
                first_timestamp_ns
            ),
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


def run_parent_day(
    spec: c.DaySpec,
    child_runner: Callable[
        [],
        ChildProcessResult,
    ],
) -> bool:
    if day_state(spec) != "FRESH":
        raise D6R16ExecutionError(
            f"day_not_fresh:{spec.day}"
        )

    marker = {
        "experiment_id": c.EXPERIMENT_ID,
        "schema_version": c.SCHEMA_VERSION,
        "canonical_attempt": 1,
        "day": spec.day,
        "symbol": c.SYMBOL,
        "exchange": c.EXCHANGE,
        "mode": c.MODE,
        "fixed_wakeup_stop_target": None,
    }

    create_one_shot_marker(
        marker_path(spec),
        marker,
    )

    evidence: dict[str, object] = {
        **marker,
        "status": "FAIL",
        "failure_reason": None,
        "source_content_opened": False,
        "mar_to_jul_feed_opened": False,
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
            raise D6R16ExecutionError(
                f"child_return_code:"
                f"{spec.day}:{child.returncode}"
            )

        lines = [
            x for x in child.stdout.splitlines()
            if x.strip()
        ]

        if not lines:
            raise D6R16ExecutionError(
                f"child_stdout_empty:{spec.day}"
            )

        payload = json.loads(
            lines[-1]
        )

        required = {
            "experiment_id": c.EXPERIMENT_ID,
            "day": spec.day,
            "source_sha256": spec.sha256,
            "source_rows": spec.rows,
            "source_bytes": spec.bytes,
            "source_verified_by_adapter": True,
            "natural_end_of_data_reached": True,
            "fixed_wakeup_stop_target": None,
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
                raise D6R16ExecutionError(
                    f"child_payload_invariant:"
                    f"{spec.day}:{key}"
                )

        if int(payload.get("market_wakeups", 0)) <= 0:
            raise D6R16ExecutionError(
                f"child_wakeup_count:{spec.day}"
            )

        if int(payload.get("last_timestamp_ns", 0)) <= 0:
            raise D6R16ExecutionError(
                f"child_last_timestamp:{spec.day}"
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
            raise D6R16ExecutionError(
                f"child_close_lifecycle:{spec.day}"
            )

        evidence.update(payload)
        evidence["status"] = "PASS"

    except Exception as exc:
        evidence["failure_reason"] = (
            f"{type(exc).__name__}:{exc}"
        )

    finally:
        hb = heartbeat_path(spec)

        if hb.is_file():
            heartbeat = json.loads(
                hb.read_text(
                    encoding="utf-8"
                )
            )

            evidence["latest_heartbeat"] = heartbeat
            evidence["source_content_opened"] = any(
                isinstance(item, dict)
                and item.get("capture_point")
                != "before_source_open"
                for item in heartbeat.get(
                    "memory_snapshots",
                    [],
                )
            )
            evidence["mar_to_jul_feed_opened"] = (
                evidence["source_content_opened"]
            )

        atomic_write_json(
            evidence_path(spec),
            evidence,
        )

    return evidence["status"] == "PASS"


def execute_sequence(
    *,
    state_getter: Callable[[c.DaySpec], str],
    day_runner: Callable[[c.DaySpec], bool],
    persist_summary: Callable[
        [dict[str, object]],
        None,
    ],
) -> bool:
    states = tuple(
        state_getter(spec)
        for spec in c.DAY_SPECS
    )

    actions = sequence_plan(states)

    completed: list[dict[str, object]] = []

    for spec, state, action in zip(
        c.DAY_SPECS,
        states,
        actions,
    ):
        if action == "SKIP_FROZEN_PASS":
            completed.append(
                {
                    "day": spec.day,
                    "initial_state": state,
                    "action": action,
                    "result": "PASS_ALREADY_FROZEN",
                }
            )
            continue

        ok = day_runner(spec)

        completed.append(
            {
                "day": spec.day,
                "initial_state": state,
                "action": action,
                "result": (
                    "PASS"
                    if ok
                    else "FAIL_CONSUMED_STOP"
                ),
            }
        )

        summary = {
            "experiment_id": c.EXPERIMENT_ID,
            "schema_version": c.SCHEMA_VERSION,
            "status": (
                "IN_PROGRESS"
                if ok
                else "FAIL_STOPPED"
            ),
            "stop_on_first_nonpass": True,
            "automatic_retry": False,
            "completed": completed,
        }

        persist_summary(summary)

        if not ok:
            return False

    persist_summary(
        {
            "experiment_id": c.EXPERIMENT_ID,
            "schema_version": c.SCHEMA_VERSION,
            "status": "PASS",
            "stop_on_first_nonpass": True,
            "automatic_retry": False,
            "completed": completed,
        }
    )

    return True


def run_real_parent(
    environ: Mapping[str, str] | None = None,
) -> int:
    require_execution_authorization(
        environ
    )

    preflight = run_preflight()

    if preflight["status"] != "PASS":
        raise D6R16ExecutionError(
            "preflight_status"
        )

    if not any(
        x == "RUN_FRESH"
        for x in preflight["sequence_actions"]
    ):
        raise D6R16ExecutionError(
            "sequence_already_complete"
        )

    def real_day_runner(
        spec: c.DaySpec,
    ) -> bool:
        def child_runner() -> ChildProcessResult:
            completed = subprocess.run(
                child_command(spec.day),
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

        return run_parent_day(
            spec,
            child_runner,
        )

    ok = execute_sequence(
        state_getter=day_state,
        day_runner=real_day_runner,
        persist_summary=lambda payload: (
            atomic_write_json(
                c.SEQUENCE_EVIDENCE_PATH,
                payload,
            )
        ),
    )

    return 0 if ok else 1


def run_real_child(
    day: str,
    environ: Mapping[str, str] | None = None,
) -> int:
    require_execution_authorization(
        environ
    )

    if day not in c.DAY_BY_NAME:
        raise D6R16ExecutionError(
            f"unknown_day:{day}"
        )

    spec = c.DAY_BY_NAME[day]

    from multimarket import dev045_d6r5_memmap_adapter as adapter
    from multimarket import dev045_d6r6_historical_driver as driver

    def source_identity() -> tuple[
        int,
        int,
        int,
        int,
    ]:
        observed = spec.path.stat()

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
                spec.path,
                expected_sha256=spec.sha256,
                expected_bytes=spec.bytes,
                expected_rows=spec.rows,
            )
        ),
        build_binding=(
            driver._build_lifetime_safe_binding
        ),
        source_identity=source_identity,
        persist_heartbeat=lambda payload: (
            atomic_write_json(
                heartbeat_path(spec),
                payload,
            )
        ),
    )

    outcome = run_full_day_feed(
        spec,
        deps,
    )

    print(
        json.dumps(
            outcome.to_evidence_dict(spec),
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
        c.PREFLIGHT_FLAG,
        action="store_true",
    )
    parser.add_argument(
        c.CHILD_FLAG,
        metavar="DAY",
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

    if args.child is not None:
        return run_real_child(
            args.child
        )

    return run_real_parent()


if __name__ == "__main__":
    raise SystemExit(main())

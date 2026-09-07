from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess

import numpy as np

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r17_direct_action_driver_bridge as bridge
from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r19_canonical_runner as d6r19_runner
from multimarket import dev045_d6r20_q4_real_engine_qualification as q4
from multimarket import dev045_d6r20_q5_invalid_local_book_driver as driver
from multimarket import dev045_m6_event_loop_kernel as d2


EXPERIMENT_ID = "DEV045-D6R20-Q5-FORENSIC"
DESIGN_VERSION = "invalid-local-book-state-forensic-v1"

PARENT_HEAD = "c222dd787963a0fd01fc0182a14ff2d03934037d"
Q4_FAILURE_SHA256 = (
    "93e27d418e62eae86bc5608c9a241024c57fbd1f9aee215091b1c57ea5667e87"
)
Q4_DRIVER_BLOB = "aa1f9b3bcfd4262b1b1d23a94fd6fae7946830f7"
Q4_HARNESS_BLOB = "80f89e62d88196be8364bf2f78f93afcb933f6ea"
Q3_HARNESS_BLOB = "f24604a58b7541b0ba407f7be75b77cf0cc8a19f"
D6R20_DRIVER_BLOB = "1cae4584788aab29b409bf985168803759d42b1f"
D6R19_DRIVER_BLOB = "5aaf880795f796d5086b3b86a6e7dde0fd7f56ed"
M4_ADAPTER_BLOB = "7f6a321b4512dd1ec1edf94c79416e176ee75e1c"
M4_M6_BINDING_BLOB = "7c0673a60c59772b5c187d90b4037693d120d94b"
M3_POLICY_BLOB = "256644726f8478d2b76105bce97e5f2c536cabf6"
V2_PATCH_SHA256 = (
    "436061c6d4be1ebab8725ffbd842237a46ba7e7e90a20d320278836f199e3c70"
)
HFTBACKTEST_VERSION = "2.4.4"
HFTBACKTEST_BINARY_SHA256 = (
    "5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752"
)

FORENSIC_DAY = "2026-04-01"
FORENSIC_POLICY = "M06"
FORENSIC_SCENARIO = "Q0_PRIMARY_250_250"
FORENSIC_SCOPE = ((FORENSIC_DAY, FORENSIC_POLICY, FORENSIC_SCENARIO),)

AUTHORIZATION_ENV = "DEV045_D6R20_Q5_FORENSIC_AUTHORIZE"
AUTHORIZATION_TOKEN = (
    "YES_REAL_HFTBACKTEST_INVALID_LOCAL_BOOK_FORENSIC_D6R20_Q5"
)

EXPECTED_BRANCH = "research/dev045-m6-d6r20-q5-invalid-local-book-forensic"
EXPECTED_REMOTE_REF = f"origin/{EXPECTED_BRANCH}"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
Q4_FAILURE_EVIDENCE_PATH = (
    REPOSITORY_ROOT
    / "evidence/dev045_d6r20_q4_real_engine_qualification_failure.json"
)
Q4_DRIVER_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q4_scheduler_reconciled_driver.py"
)
Q4_HARNESS_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q4_real_engine_qualification.py"
)
Q3_HARNESS_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q3_real_engine_qualification.py"
)
D6R20_DRIVER_PATH = (
    REPOSITORY_ROOT / "src/multimarket/dev045_d6r20_residual_flatten_driver.py"
)
D6R19_DRIVER_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r19_response_batch_replacement_driver.py"
)
M4_ADAPTER_PATH = REPOSITORY_ROOT / "src/multimarket/dev045_m4_adapter.py"
M4_M6_BINDING_PATH = (
    REPOSITORY_ROOT / "src/multimarket/dev045_m4_m6_binding.py"
)
M3_POLICY_PATH = REPOSITORY_ROOT / "src/multimarket/dev045_m3_policy.py"
V2_PATCH_PATH = REPOSITORY_ROOT / "tools/patch_hftbacktest_244_safe_v2.py"
D6R20_CANONICAL_RUNNER_PATH = (
    REPOSITORY_ROOT / "src/multimarket/dev045_d6r20_canonical_runner.py"
)
D6R21_CANONICAL_RUNNER_PATH = (
    REPOSITORY_ROOT / "src/multimarket/dev045_d6r21_canonical_runner.py"
)
ALLOWED_UNTRACKED_PATHS = (
    "evidence/dev045_d6r9a_feb01_full_day_v2.json",
)

RESULT_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/"
    "dev045_d6r20_q5_invalid_local_book_forensic_v1"
)
RESULT_PATH = RESULT_ROOT / "DEV045_D6R20_Q5_FORENSIC_RESULT.json"
FAILURE_PATH = RESULT_ROOT / "DEV045_D6R20_Q5_FORENSIC_FAILURE.json"
SOURCE_WINDOW_RADIUS = 12

HISTORICAL_KERNEL = (
    driver.InvalidLocalBookForensicContinuousHistoricalPolicyKernel
)

FORENSIC_EXECUTION_AUTHORIZED_BY_DEFAULT = False
REAL_HISTORICAL_FORENSIC_EXECUTED = False
Q4_RERUN_AUTHORIZED = False
CANONICAL_RUNNER_IMPLEMENTED = False
CANONICAL_ECONOMIC_ATTEMPT = False
CANONICAL_ATTEMPT_CONSUMED = False
ECONOMIC_ARENA_CALLED = False
STRATEGY_RANKING_PERFORMED = False
AUTOMATIC_RETRY = False
LIVE_TRADING_AUTHORIZED = False


class InvalidLocalBookForensicError(RuntimeError):
    pass


@dataclass(frozen=True)
class ForensicRepositoryIdentity:
    branch: str
    head: str
    remote_ref: str
    remote_head: str
    tracked_worktree_clean: bool
    permitted_untracked_paths: tuple[str, ...]
    frozen_blobs_verified: bool
    v2_patch_sha256: str
    canonical_runners_absent: bool
    result_surface_virgin: bool


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def _git_blob(path: Path) -> str:
    data = path.read_bytes()
    payload = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(payload).hexdigest()


def _git_output(*args: str) -> str:
    try:
        completed = subprocess.run(
            ("git", *args),
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise InvalidLocalBookForensicError(
            f"repository_git_command:{args[0]}"
        ) from exc

    return completed.stdout.rstrip("\n")


def _require_authorization(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> None:
    if execution_gate is not True:
        raise InvalidLocalBookForensicError("execution_gate_closed")

    if authorization_token != AUTHORIZATION_TOKEN:
        raise InvalidLocalBookForensicError("authorization_token")

    if os.environ.get(AUTHORIZATION_ENV) != AUTHORIZATION_TOKEN:
        raise InvalidLocalBookForensicError("authorization_environment")


def _require_virgin_result_surface() -> None:
    if RESULT_PATH.exists():
        raise InvalidLocalBookForensicError("forensic_result_exists")

    if FAILURE_PATH.exists():
        raise InvalidLocalBookForensicError("forensic_failure_exists")

    if RESULT_ROOT.exists():
        if not RESULT_ROOT.is_dir():
            raise InvalidLocalBookForensicError("forensic_root_not_directory")

        if any(RESULT_ROOT.iterdir()):
            raise InvalidLocalBookForensicError("forensic_surface_not_virgin")


def validate_repository_preflight() -> ForensicRepositoryIdentity:
    branch = _git_output("branch", "--show-current")

    if branch != EXPECTED_BRANCH:
        raise InvalidLocalBookForensicError(f"repository_branch:{branch}")

    raw_status = _git_output(
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    status = tuple(line for line in raw_status.splitlines() if line)
    allowed = {f"?? {path}" for path in ALLOWED_UNTRACKED_PATHS}
    unexpected = tuple(line for line in status if line not in allowed)

    if unexpected:
        raise InvalidLocalBookForensicError(
            f"repository_worktree_dirty_or_unexpected:{unexpected[0]}"
        )

    head = _git_output("rev-parse", "HEAD")
    remote_head = _git_output("rev-parse", EXPECTED_REMOTE_REF)

    if len(head) != 40 or len(remote_head) != 40:
        raise InvalidLocalBookForensicError("repository_head")

    if head != remote_head:
        raise InvalidLocalBookForensicError(
            f"repository_remote_mismatch:{head}:{remote_head}"
        )

    expected_blobs = (
        (Q4_DRIVER_PATH, Q4_DRIVER_BLOB, "q4_driver_blob"),
        (Q4_HARNESS_PATH, Q4_HARNESS_BLOB, "q4_harness_blob"),
        (Q3_HARNESS_PATH, Q3_HARNESS_BLOB, "q3_harness_blob"),
        (D6R20_DRIVER_PATH, D6R20_DRIVER_BLOB, "d6r20_driver_blob"),
        (D6R19_DRIVER_PATH, D6R19_DRIVER_BLOB, "d6r19_driver_blob"),
        (M4_ADAPTER_PATH, M4_ADAPTER_BLOB, "m4_adapter_blob"),
        (M4_M6_BINDING_PATH, M4_M6_BINDING_BLOB, "m4_m6_binding_blob"),
        (M3_POLICY_PATH, M3_POLICY_BLOB, "m3_policy_blob"),
    )

    for path, expected, label in expected_blobs:
        observed = _git_blob(path)

        if observed != expected:
            raise InvalidLocalBookForensicError(f"{label}:{observed}")

    patch_sha = _sha256(V2_PATCH_PATH)

    if patch_sha != V2_PATCH_SHA256:
        raise InvalidLocalBookForensicError(f"v2_patch_sha256:{patch_sha}")

    if D6R20_CANONICAL_RUNNER_PATH.exists():
        raise InvalidLocalBookForensicError("d6r20_canonical_runner_exists")

    if D6R21_CANONICAL_RUNNER_PATH.exists():
        raise InvalidLocalBookForensicError("d6r21_canonical_runner_exists")

    _require_virgin_result_surface()

    return ForensicRepositoryIdentity(
        branch=branch,
        head=head,
        remote_ref=EXPECTED_REMOTE_REF,
        remote_head=remote_head,
        tracked_worktree_clean=True,
        permitted_untracked_paths=tuple(
            line[3:] for line in status if line in allowed
        ),
        frozen_blobs_verified=True,
        v2_patch_sha256=patch_sha,
        canonical_runners_absent=True,
        result_surface_virgin=True,
    )


def validate_forensic_contract() -> None:
    if FORENSIC_SCOPE != (
        (FORENSIC_DAY, FORENSIC_POLICY, FORENSIC_SCENARIO),
    ):
        raise InvalidLocalBookForensicError("forensic_scope")

    if HISTORICAL_KERNEL is not (
        driver.InvalidLocalBookForensicContinuousHistoricalPolicyKernel
    ):
        raise InvalidLocalBookForensicError("q5_kernel_binding")

    if not issubclass(HISTORICAL_KERNEL, q4.HISTORICAL_KERNEL):
        raise InvalidLocalBookForensicError("q4_kernel_lineage")

    if _sha256(Q4_FAILURE_EVIDENCE_PATH) != Q4_FAILURE_SHA256:
        raise InvalidLocalBookForensicError("q4_failure_sha256")

    spec = d6r19_runner._spec_for_day(FORENSIC_DAY)

    if (
        int(spec.rows) != 132_829_759
        or int(spec.bytes) != 8_501_104_832
        or spec.sha256
        != "de7e0471e63631394981b301bb461d679192c37eb6241d4d8073cf0640eca7f7"
    ):
        raise InvalidLocalBookForensicError("april_source_identity")


def _hftbacktest_module():
    import hftbacktest as h

    return h


def validate_runtime_identity(h):
    identity = q4.validate_runtime_identity(h)

    if identity.version != HFTBACKTEST_VERSION:
        raise InvalidLocalBookForensicError("hftbacktest_version")

    if identity.compiled_artifact_sha256 != HFTBACKTEST_BINARY_SHA256:
        raise InvalidLocalBookForensicError("hftbacktest_binary_sha256")

    return identity


def open_verified_forensic_source(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> adapter.CanonicalJanMemmap:
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    spec = d6r19_runner._spec_for_day(FORENSIC_DAY)
    source = adapter._open_verified_file(
        spec.path,
        expected_sha256=spec.sha256,
        expected_bytes=spec.bytes,
        expected_rows=spec.rows,
    )

    try:
        d6r19_runner.validate_canonical_verified_source(
            source,
            day=FORENSIC_DAY,
        )
    except Exception:
        source.close()
        raise

    return source


def load_forensic_support():
    direct_by_policy = q4.load_qualification_support(day=FORENSIC_DAY)
    bridge._validate_day_mapping(
        day=FORENSIC_DAY,
        direct_by_policy=direct_by_policy,
    )

    if set(direct_by_policy) != {"M06", "M07"}:
        raise InvalidLocalBookForensicError("april_support_mapping")

    return direct_by_policy[FORENSIC_POLICY]


def _flag_present(event_flags: int, flag: int) -> bool:
    value = int(flag)
    return value != 0 and (int(event_flags) & value) == value


def decode_event_flags(event_flags: int, h) -> dict:
    flags = int(event_flags)
    event_types = tuple(
        name
        for name in (
            "DEPTH_EVENT",
            "DEPTH_CLEAR_EVENT",
            "DEPTH_SNAPSHOT_EVENT",
            "TRADE_EVENT",
        )
        if hasattr(h, name)
        and _flag_present(flags, int(getattr(h, name)))
    )
    domains = tuple(
        name
        for name in ("EXCH_EVENT", "LOCAL_EVENT")
        if hasattr(h, name)
        and _flag_present(flags, int(getattr(h, name)))
    )
    buy = bool(
        hasattr(h, "BUY_EVENT")
        and _flag_present(flags, int(h.BUY_EVENT))
    )
    sell = bool(
        hasattr(h, "SELL_EVENT")
        and _flag_present(flags, int(h.SELL_EVENT))
    )

    if buy and sell:
        side = "BOTH"
    elif buy:
        side = "BUY"
    elif sell:
        side = "SELL"
    else:
        side = "NONE"

    return {
        "event_types": event_types,
        "domains": domains,
        "side": side,
    }


def bounded_source_window(
    data,
    *,
    failure_timestamp_ns: int,
    h,
    radius: int = SOURCE_WINDOW_RADIUS,
) -> dict:
    window_radius = int(radius)

    if window_radius < 0 or window_radius > 64:
        raise InvalidLocalBookForensicError("source_window_radius")

    rows = int(len(data))
    timestamps = data["local_ts"]
    timestamp = int(failure_timestamp_ns)
    left = int(np.searchsorted(timestamps, timestamp, side="left"))
    right = int(np.searchsorted(timestamps, timestamp, side="right"))
    exact_count = right - left

    if exact_count == 0:
        indices = tuple(
            range(
                max(0, left - window_radius),
                min(rows, left + window_radius + 1),
            )
        )
    else:
        leading = range(
            max(0, left - window_radius),
            min(rows, left + window_radius + 1),
        )
        trailing = range(
            max(0, right - window_radius - 1),
            min(rows, right + window_radius),
        )
        indices = tuple(sorted(set(leading).union(trailing)))

    observations = []

    for index in indices:
        row = data[index]
        flags = int(row["ev"])
        observations.append(
            {
                "row_index": int(index),
                "local_ts": int(row["local_ts"]),
                "exch_ts": int(row["exch_ts"]),
                "event_flags": flags,
                "px": float(row["px"]),
                "qty": float(row["qty"]),
                "decoded": decode_event_flags(flags, h),
            }
        )

    return {
        "failure_timestamp_ns": int(failure_timestamp_ns),
        "search_left_index": left,
        "search_right_index_exclusive": right,
        "exact_timestamp_row_count": exact_count,
        "selected_row_count": len(indices),
        "exact_timestamp_group_truncated": bool(exact_count > len(indices)),
        "radius": window_radius,
        "rows": observations,
        "read_only_post_failure_diagnostic": True,
        "fed_back_into_execution": False,
    }


def run_bound_forensic_replay(
    source: adapter.CanonicalJanMemmap,
    *,
    direct_index,
    forensic_sink: list[dict],
) -> None:
    bridge.validate_direct_index(
        policy_id=FORENSIC_POLICY,
        day=FORENSIC_DAY,
        index=direct_index,
    )
    h = _hftbacktest_module()
    asset = base._build_asset_from_verified_source(
        source,
        scenario=FORENSIC_SCENARIO,
        initial_snapshot=None,
    )
    bt = h.HashMapMarketDepthBacktest([asset])
    primary_exception: BaseException | None = None

    try:
        kernel = HISTORICAL_KERNEL(
            bt=bt,
            h=h,
            policy_id=FORENSIC_POLICY,
            day=FORENSIC_DAY,
            scenario=FORENSIC_SCENARIO,
            terminal_source_local_ns=int(source.data[-1]["local_ts"]),
            direct_index=direct_index,
            forensic_sink=forensic_sink,
        )
        kernel.run_full_day()
        raise InvalidLocalBookForensicError("invalid_local_book_not_observed")
    except BaseException as exc:
        primary_exception = exc
        raise
    finally:
        try:
            rc = int(bt.close())
        except BaseException:
            if primary_exception is None:
                raise
        else:
            if rc != 0 and primary_exception is None:
                raise InvalidLocalBookForensicError(
                    f"backtest_close_rc:{rc}"
                )


def _write_json_new(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise InvalidLocalBookForensicError(
            f"forensic_result_exists:{path.name}"
        ) from exc

    return path


def _common_payload(*, repository, runtime) -> dict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "design_version": DESIGN_VERSION,
        "head": repository.head,
        "repository": asdict(repository),
        "hftbacktest": {
            "version": runtime.version,
            "compiled_artifact_sha256": runtime.compiled_artifact_sha256,
            "verified": runtime.verified,
        },
        "q4_failure_sha256": Q4_FAILURE_SHA256,
        "forensic_scope": {
            "day": FORENSIC_DAY,
            "policy": FORENSIC_POLICY,
            "scenario": FORENSIC_SCENARIO,
        },
        "canonical_economic_attempt": False,
        "canonical_attempt_consumed": False,
        "economic_arena_called": False,
        "strategy_ranking_performed": False,
        "economic_conclusion": "UNAVAILABLE",
        "automatic_retry": False,
        "live_trading_authorized": False,
    }


def run_invalid_local_book_forensic(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> dict:
    """Run the one authorized April Q5 diagnostic and preserve its failure."""
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    repository = validate_repository_preflight()
    runtime = validate_runtime_identity(_hftbacktest_module())
    validate_forensic_contract()
    direct_index = load_forensic_support()
    forensic_sink: list[dict] = []

    try:
        with open_verified_forensic_source(
            authorization_token=authorization_token,
            execution_gate=execution_gate,
        ) as source:
            before = base._stat_identity(source.path)

            try:
                run_bound_forensic_replay(
                    source,
                    direct_index=direct_index,
                    forensic_sink=forensic_sink,
                )
            except d2.EventLoopKernelError as exc:
                if str(exc) != "invalid_local_book":
                    raise

                if len(forensic_sink) != 1:
                    raise InvalidLocalBookForensicError(
                        "invalid_local_book_snapshot_count"
                    ) from exc

                snapshot = forensic_sink[0]
                source_window = bounded_source_window(
                    source.data,
                    failure_timestamp_ns=int(snapshot["bt_current_timestamp"]),
                    h=_hftbacktest_module(),
                )
                after = base._stat_identity(source.path)

                if before != after:
                    raise InvalidLocalBookForensicError(
                        "source_identity_changed"
                    ) from exc

                payload = {
                    **_common_payload(repository=repository, runtime=runtime),
                    "schema_version": "dev045-d6r20-q5-forensic-result-v1",
                    "status": "INVALID_LOCAL_BOOK_FORENSIC_CAPTURED",
                    "original_exception_type": type(exc).__name__,
                    "original_exception_message": str(exc),
                    "invalid_local_book": snapshot,
                    "source_window": source_window,
                    "source_identity_unchanged": True,
                    "replay_continued_after_failure": False,
                    "forensic_classification": snapshot["classification"],
                }
                _write_json_new(RESULT_PATH, payload)
                raise

            raise InvalidLocalBookForensicError(
                "forensic_replay_returned_without_failure"
            )

    except d2.EventLoopKernelError:
        raise
    except Exception as exc:
        failure = {
            **_common_payload(repository=repository, runtime=runtime),
            "schema_version": "dev045-d6r20-q5-forensic-failure-v1",
            "status": "INVALID_LOCAL_BOOK_FORENSIC_FAILED",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "captured_snapshot_count": len(forensic_sink),
        }
        _write_json_new(FAILURE_PATH, failure)
        raise


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_HEAD",
    "Q4_FAILURE_SHA256",
    "HFTBACKTEST_VERSION",
    "HFTBACKTEST_BINARY_SHA256",
    "FORENSIC_DAY",
    "FORENSIC_POLICY",
    "FORENSIC_SCENARIO",
    "FORENSIC_SCOPE",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "EXPECTED_BRANCH",
    "EXPECTED_REMOTE_REF",
    "RESULT_ROOT",
    "RESULT_PATH",
    "FAILURE_PATH",
    "HISTORICAL_KERNEL",
    "FORENSIC_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "REAL_HISTORICAL_FORENSIC_EXECUTED",
    "Q4_RERUN_AUTHORIZED",
    "CANONICAL_RUNNER_IMPLEMENTED",
    "CANONICAL_ECONOMIC_ATTEMPT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "ECONOMIC_ARENA_CALLED",
    "STRATEGY_RANKING_PERFORMED",
    "AUTOMATIC_RETRY",
    "LIVE_TRADING_AUTHORIZED",
    "InvalidLocalBookForensicError",
    "ForensicRepositoryIdentity",
    "validate_repository_preflight",
    "validate_forensic_contract",
    "validate_runtime_identity",
    "open_verified_forensic_source",
    "load_forensic_support",
    "decode_event_flags",
    "bounded_source_window",
    "run_bound_forensic_replay",
    "run_invalid_local_book_forensic",
]

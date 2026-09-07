from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
from typing import Callable, Mapping

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r17_direct_action_driver_bridge as bridge
from multimarket import dev045_d6r17_direct_action_support as support
from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r19_canonical_runner as d6r19_runner
from multimarket import dev045_d6r20_q6_real_engine_qualification as q6
from multimarket import dev045_d6r20_q8_terminal_shutdown_grid_alignment_driver as q8_driver
from multimarket import dev045_m6_event_loop_contract as d1


EXPERIMENT_ID = "DEV045-D6R20-Q8"
DESIGN_VERSION = (
    "real-hftbacktest-v2-terminal-shutdown-grid-alignment-qualification-v1"
)

PARENT_HEAD = "3c9ff9009e2516ba47a0e250f75289ef6ad4f6dd"
Q7_RESULT_SHA256 = (
    "9b7e9d45fcc3bbcdaaab45df8062a1ced6b514c6ad6bae16fbfca6043b5df212"
)
Q7_DRIVER_BLOB = "d4840e7546a6fc3c1a2ba5acfc017133e24b5272"
Q7_FORENSIC_BLOB = "9a4ab63b28e2c826794da6dd71c3f6648d6615c5"
Q6_DRIVER_BLOB = "af5556f6a11f0a86aab16f4d8e7ac1076990d7b1"
Q6_QUALIFICATION_BLOB = "7ddc57d21d8ff89e516d21ecc2b63620e52cdd1e"
UPSTREAM_COMMIT = q6.UPSTREAM_COMMIT
D6R20_DRIVER_BLOB = q6.D6R20_DRIVER_BLOB
M4_M6_BINDING_BLOB = q6.M4_M6_BINDING_BLOB
V2_PATCH_SHA256 = q6.V2_PATCH_SHA256
PATCHED_SOURCE_DIFF_SHA256 = q6.PATCHED_SOURCE_DIFF_SHA256
HFTBACKTEST_VERSION = q6.HFTBACKTEST_VERSION
HFTBACKTEST_BINARY_SHA256 = q6.HFTBACKTEST_BINARY_SHA256
OLD_HFTBACKTEST_BINARY_SHA256 = q6.OLD_HFTBACKTEST_BINARY_SHA256

EXPECTED_BRANCH = (
    "research/dev045-m6-d6r20-q8-terminal-shutdown-grid-alignment"
)
EXPECTED_REMOTE_REF = f"origin/{EXPECTED_BRANCH}"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
Q7_RESULT_PATH = (
    REPOSITORY_ROOT
    / "evidence/dev045_d6r20_q7_flatten_end_of_data_forensic_result.json"
)
Q7_DRIVER_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q7_flatten_end_of_data_forensic_driver.py"
)
Q7_FORENSIC_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q7_flatten_end_of_data_forensic.py"
)
Q6_DRIVER_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q6_initial_book_readiness_driver.py"
)
Q6_QUALIFICATION_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q6_real_engine_qualification.py"
)
D6R20_DRIVER_PATH = q6.D6R20_DRIVER_PATH
M4_M6_BINDING_PATH = q6.M4_M6_BINDING_PATH
V2_PATCH_PATH = q6.V2_PATCH_PATH
D6R20_CANONICAL_RUNNER_PATH = q6.D6R20_CANONICAL_RUNNER_PATH
D6R21_CANONICAL_RUNNER_PATH = q6.D6R21_CANONICAL_RUNNER_PATH
ALLOWED_UNTRACKED_PATHS = q6.ALLOWED_UNTRACKED_PATHS

AUTHORIZATION_ENV = "DEV045_D6R20_Q8_AUTHORIZE"
AUTHORIZATION_TOKEN = (
    "YES_REAL_HFTBACKTEST_V2_EXECUTION_QUALIFICATION_D6R20_Q8"
)

QUALIFICATION_DAY_ORDER = q6.QUALIFICATION_DAY_ORDER
JANUARY_POLICIES = q6.JANUARY_POLICIES
APRIL_POLICIES = q6.APRIL_POLICIES
SCENARIO_ORDER = q6.SCENARIO_ORDER
QUALIFICATION_PLAN = q6.QUALIFICATION_PLAN
EXPECTED_REPLAY_COUNT = q6.EXPECTED_REPLAY_COUNT
EXPECTED_JANUARY_REPLAYS = q6.EXPECTED_JANUARY_REPLAYS
EXPECTED_APRIL_REPLAYS = q6.EXPECTED_APRIL_REPLAYS

HISTORICAL_KERNEL = (
    q8_driver.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel
)

QUALIFICATION_EXECUTION_AUTHORIZED_BY_DEFAULT = False
REAL_HISTORICAL_QUALIFICATION_EXECUTED = False
Q6_RERUN_AUTHORIZED = False
Q7_RERUN_AUTHORIZED = False
CANONICAL_RUNNER_IMPLEMENTED = False
CANONICAL_ECONOMIC_ATTEMPT = False
CANONICAL_ATTEMPT_CONSUMED = False
ECONOMIC_ARENA_EXECUTED = False
STRATEGY_RANKING_PERFORMED = False
AUTOMATIC_RETRY = False
NETWORK_ACQUISITION_ENABLED = False
RAILWAY_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

RESULT_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/"
    "dev045_d6r20_q8_real_engine_qualification_v1"
)
SUCCESS_RESULT_PATH = RESULT_ROOT / "DEV045_D6R20_Q8_QUALIFICATION_RESULT.json"
FAILURE_RESULT_PATH = RESULT_ROOT / "DEV045_D6R20_Q8_QUALIFICATION_FAILURE.json"


QualificationError = q6.QualificationError
RuntimeIdentity = q6.RuntimeIdentity
_git_blob = q6._git_blob
_stream_sha256 = q6._stream_sha256
_git_output = q6._git_output
_current_head = q6._current_head
_current_branch = q6._current_branch
_worktree_status = q6._worktree_status


@dataclass(frozen=True)
class RepositoryIdentity:
    branch: str
    head: str
    remote_ref: str
    remote_head: str
    tracked_worktree_clean: bool
    permitted_untracked_paths: tuple[str, ...]
    frozen_predecessors_verified: bool
    d6r20_driver_blob: str
    m4_m6_binding_blob: str
    v2_patch_sha256: str
    q7_result_sha256: str
    d6r20_canonical_runner_absent: bool
    d6r21_canonical_runner_absent: bool
    result_surface_virgin: bool


@dataclass(frozen=True)
class ReplayExecutionDiagnostics(q6.ReplayExecutionDiagnostics):
    raw_terminal_shutdown_cutoff_ns: int
    aligned_terminal_shutdown_cutoff_ns: int
    cutoff_alignment_shift_ns: int
    frozen_terminal_shutdown_lead_ns: int
    actual_terminal_shutdown_start_ns: int
    remaining_ns_at_shutdown_start: int
    terminal_start_no_later_than_raw_cutoff: bool
    terminal_lead_preserved: bool
    inventory_clock_matches_terminal_position: bool


def _require_authorization(
    *, authorization_token: str, execution_gate: bool
) -> None:
    if execution_gate is not True:
        raise QualificationError("execution_gate_closed")

    if authorization_token != AUTHORIZATION_TOKEN:
        raise QualificationError("authorization_token")

    if os.environ.get(AUTHORIZATION_ENV) != AUTHORIZATION_TOKEN:
        raise QualificationError("authorization_environment")


def _hftbacktest_module():
    import hftbacktest as h

    return h


def validate_runtime_identity(h) -> RuntimeIdentity:
    return q6.validate_runtime_identity(h)


def _remote_head() -> str:
    head = _git_output("rev-parse", EXPECTED_REMOTE_REF)

    if len(head) != 40:
        raise QualificationError("git_remote_head")

    return head


def _require_virgin_result_surface() -> None:
    if SUCCESS_RESULT_PATH.exists():
        raise QualificationError("qualification_result_exists")

    if FAILURE_RESULT_PATH.exists():
        raise QualificationError("qualification_failure_exists")

    if RESULT_ROOT.exists():
        if not RESULT_ROOT.is_dir():
            raise QualificationError("qualification_root_not_directory")

        if any(RESULT_ROOT.iterdir()):
            raise QualificationError("qualification_surface_not_virgin")


def validate_repository_preflight() -> RepositoryIdentity:
    branch = _current_branch()

    if branch != EXPECTED_BRANCH:
        raise QualificationError(f"repository_branch:{branch}")

    status = _worktree_status()
    allowed = {f"?? {path}" for path in ALLOWED_UNTRACKED_PATHS}
    unexpected = tuple(line for line in status if line not in allowed)

    if unexpected:
        raise QualificationError(
            f"repository_worktree_dirty_or_unexpected:{unexpected[0]}"
        )

    head = _current_head()
    remote_head = _remote_head()

    if head != remote_head:
        raise QualificationError(
            f"repository_remote_mismatch:{head}:{remote_head}"
        )

    expected_blobs = (
        (Q7_DRIVER_PATH, Q7_DRIVER_BLOB, "q7_driver_blob"),
        (Q7_FORENSIC_PATH, Q7_FORENSIC_BLOB, "q7_forensic_blob"),
        (Q6_DRIVER_PATH, Q6_DRIVER_BLOB, "q6_driver_blob"),
        (
            Q6_QUALIFICATION_PATH,
            Q6_QUALIFICATION_BLOB,
            "q6_qualification_blob",
        ),
        (D6R20_DRIVER_PATH, D6R20_DRIVER_BLOB, "d6r20_driver_blob"),
        (M4_M6_BINDING_PATH, M4_M6_BINDING_BLOB, "m4_m6_binding_blob"),
    )

    for path, expected, label in expected_blobs:
        observed = _git_blob(path)

        if observed != expected:
            raise QualificationError(f"{label}:{observed}")

    patch_sha = _stream_sha256(V2_PATCH_PATH)

    if patch_sha != V2_PATCH_SHA256:
        raise QualificationError(f"v2_patch_sha256:{patch_sha}")

    q7_result_sha = _stream_sha256(Q7_RESULT_PATH)

    if q7_result_sha != Q7_RESULT_SHA256:
        raise QualificationError(f"q7_result_sha256:{q7_result_sha}")

    if D6R20_CANONICAL_RUNNER_PATH.exists():
        raise QualificationError("d6r20_canonical_runner_exists")

    if D6R21_CANONICAL_RUNNER_PATH.exists():
        raise QualificationError("d6r21_canonical_runner_exists")

    _require_virgin_result_surface()

    return RepositoryIdentity(
        branch=branch,
        head=head,
        remote_ref=EXPECTED_REMOTE_REF,
        remote_head=remote_head,
        tracked_worktree_clean=True,
        permitted_untracked_paths=tuple(
            line[3:] for line in status if line in allowed
        ),
        frozen_predecessors_verified=True,
        d6r20_driver_blob=D6R20_DRIVER_BLOB,
        m4_m6_binding_blob=M4_M6_BINDING_BLOB,
        v2_patch_sha256=patch_sha,
        q7_result_sha256=q7_result_sha,
        d6r20_canonical_runner_absent=True,
        d6r21_canonical_runner_absent=True,
        result_surface_virgin=True,
    )


def _spec_for_day(day: str):
    if day not in QUALIFICATION_DAY_ORDER:
        raise QualificationError("qualification_day")

    return d6r19_runner._spec_for_day(day)


def validate_qualification_contract() -> None:
    q6.validate_qualification_contract()

    if QUALIFICATION_PLAN != q6.QUALIFICATION_PLAN:
        raise QualificationError("qualification_order")

    if len(QUALIFICATION_PLAN) != EXPECTED_REPLAY_COUNT:
        raise QualificationError("qualification_replay_count")

    if HISTORICAL_KERNEL is not (
        q8_driver.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel
    ):
        raise QualificationError("q8_kernel_binding")

    if not issubclass(HISTORICAL_KERNEL, q6.HISTORICAL_KERNEL):
        raise QualificationError("q6_kernel_lineage")

    if _stream_sha256(Q7_RESULT_PATH) != Q7_RESULT_SHA256:
        raise QualificationError("q7_result_sha256")


def open_verified_qualification_source(
    *, day: str, authorization_token: str, execution_gate: bool
) -> adapter.CanonicalJanMemmap:
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    spec = _spec_for_day(day)
    source = adapter._open_verified_file(
        spec.path,
        expected_sha256=spec.sha256,
        expected_bytes=spec.bytes,
        expected_rows=spec.rows,
    )

    try:
        d6r19_runner.validate_canonical_verified_source(source, day=day)
    except Exception:
        source.close()
        raise

    return source


def load_qualification_support(
    *, day: str
) -> dict[str, support.DirectActionIndex]:
    return q6.load_qualification_support(day=day)


def _validate_completed_replay(
    *, bt, kernel, replay
) -> ReplayExecutionDiagnostics:
    frozen = q6._validate_completed_replay(
        bt=bt,
        kernel=kernel,
        replay=replay,
    )
    alignment = kernel.terminal_shutdown_alignment_diagnostics()
    raw = int(alignment["raw_terminal_shutdown_cutoff_ns"])
    aligned = int(alignment["aligned_terminal_shutdown_cutoff_ns"])
    shift = int(alignment["cutoff_alignment_shift_ns"])
    lead = int(alignment["frozen_terminal_shutdown_lead_ns"])
    start = alignment["actual_terminal_shutdown_start_ns"]
    remaining = alignment["remaining_ns_at_shutdown_start"]

    if aligned > raw:
        raise QualificationError("aligned_terminal_cutoff_after_raw")

    if shift != raw - aligned:
        raise QualificationError("terminal_cutoff_shift_parity")

    if shift < 0 or shift >= int(d1.BASE_MAKER_STEP_NS):
        raise QualificationError("terminal_cutoff_shift_range")

    if int(kernel.terminal_shutdown_cutoff_ns) != aligned:
        raise QualificationError("terminal_cutoff_not_aligned")

    if int(kernel.terminal_source_local_ns) - raw != lead:
        raise QualificationError("raw_terminal_lead")

    if start is None or remaining is None:
        raise QualificationError("terminal_shutdown_start_missing")

    if not bool(alignment["terminal_start_no_later_than_raw_cutoff"]):
        raise QualificationError("terminal_shutdown_started_after_raw_cutoff")

    if not bool(alignment["terminal_lead_preserved"]):
        raise QualificationError("terminal_shutdown_lead_not_preserved")

    simulator_position = float(bt.position(0))
    clock_position = float(kernel.inventory_clock.position)

    if not math.isclose(
        simulator_position, clock_position, rel_tol=0.0, abs_tol=1e-12
    ):
        raise QualificationError("terminal_inventory_clock_mismatch")

    return ReplayExecutionDiagnostics(
        **asdict(frozen),
        raw_terminal_shutdown_cutoff_ns=raw,
        aligned_terminal_shutdown_cutoff_ns=aligned,
        cutoff_alignment_shift_ns=shift,
        frozen_terminal_shutdown_lead_ns=lead,
        actual_terminal_shutdown_start_ns=int(start),
        remaining_ns_at_shutdown_start=int(remaining),
        terminal_start_no_later_than_raw_cutoff=True,
        terminal_lead_preserved=True,
        inventory_clock_matches_terminal_position=True,
    )


def run_bound_verified_qualification_replay(
    source: adapter.CanonicalJanMemmap,
    *,
    policy_id: str,
    day: str,
    scenario: str,
    direct_index: support.DirectActionIndex | None,
) -> ReplayExecutionDiagnostics:
    bridge.validate_direct_index(
        policy_id=policy_id,
        day=day,
        index=direct_index,
    )
    h = _hftbacktest_module()
    asset = base._build_asset_from_verified_source(
        source,
        scenario=scenario,
        initial_snapshot=None,
    )
    bt = h.HashMapMarketDepthBacktest([asset])
    diagnostics = None
    primary_exception: BaseException | None = None

    try:
        kernel = HISTORICAL_KERNEL(
            bt=bt,
            h=h,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            terminal_source_local_ns=int(source.data[-1]["local_ts"]),
            direct_index=direct_index,
        )
        replay = kernel.run_full_day()

        if (
            replay.day,
            replay.policy_id,
            replay.scenario,
        ) != (day, policy_id, scenario):
            raise QualificationError("replay_identity")

        diagnostics = _validate_completed_replay(
            bt=bt,
            kernel=kernel,
            replay=replay,
        )
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
                raise QualificationError(f"backtest_close_rc:{rc}")

    if diagnostics is None:
        raise QualificationError("qualification_diagnostics_missing")

    return diagnostics


def _day_plan(day: str) -> tuple[tuple[str, str, str], ...]:
    result = tuple(item for item in QUALIFICATION_PLAN if item[0] == day)

    if not result:
        raise QualificationError("empty_day_plan")

    return result


def run_verified_qualification_day(
    source: adapter.CanonicalJanMemmap,
    *,
    day: str,
    direct_by_policy: Mapping[str, support.DirectActionIndex],
    authorization_token: str,
    execution_gate: bool,
    on_replay_start: Callable[[str, str, str], None] | None = None,
    on_replay_complete: Callable[[ReplayExecutionDiagnostics], None] | None = None,
) -> tuple[ReplayExecutionDiagnostics, ...]:
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    d6r19_runner.validate_canonical_verified_source(source, day=day)
    bridge._validate_day_mapping(day=day, direct_by_policy=direct_by_policy)
    before = base._stat_identity(source.path)
    completed = []

    for _, policy_id, scenario in _day_plan(day):
        if on_replay_start is not None:
            on_replay_start(day, policy_id, scenario)

        result = run_bound_verified_qualification_replay(
            source,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            direct_index=direct_by_policy.get(policy_id),
        )
        completed.append(result)

        if on_replay_complete is not None:
            on_replay_complete(result)

    after = base._stat_identity(source.path)

    if before != after:
        raise QualificationError("source_identity_changed")

    return tuple(completed)


def run_qualification_day_from_disk(
    *,
    day: str,
    authorization_token: str,
    execution_gate: bool,
    on_replay_start: Callable[[str, str, str], None] | None = None,
    on_replay_complete: Callable[[ReplayExecutionDiagnostics], None] | None = None,
) -> tuple[ReplayExecutionDiagnostics, ...]:
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    direct_by_policy = load_qualification_support(day=day)

    with open_verified_qualification_source(
        day=day,
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    ) as source:
        return run_verified_qualification_day(
            source,
            day=day,
            direct_by_policy=direct_by_policy,
            authorization_token=authorization_token,
            execution_gate=execution_gate,
            on_replay_start=on_replay_start,
            on_replay_complete=on_replay_complete,
        )


def _write_json_new(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise QualificationError(f"result_exists:{path.name}") from exc

    return path


def _runtime_payload(identity: RuntimeIdentity) -> dict:
    return {
        "version": identity.version,
        "compiled_artifact_sha256": identity.compiled_artifact_sha256,
        "verified": identity.verified,
    }


def run_real_engine_qualification(
    *, authorization_token: str, execution_gate: bool
) -> dict:
    """Run the explicitly authorized 20-replay Q8 engineering qualification."""
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    repository = validate_repository_preflight()
    head = repository.head
    current_day, current_policy, current_scenario = QUALIFICATION_PLAN[0]
    completed: list[ReplayExecutionDiagnostics] = []
    runtime = RuntimeIdentity(
        version=HFTBACKTEST_VERSION,
        compiled_artifact_sha256=HFTBACKTEST_BINARY_SHA256,
        verified=False,
    )

    try:
        validate_qualification_contract()
        runtime = validate_runtime_identity(_hftbacktest_module())

        def replay_started(day: str, policy_id: str, scenario: str) -> None:
            nonlocal current_day, current_policy, current_scenario
            current_day = day
            current_policy = policy_id
            current_scenario = scenario

        def replay_completed(result: ReplayExecutionDiagnostics) -> None:
            completed.append(result)

        for day in QUALIFICATION_DAY_ORDER:
            current_day, current_policy, current_scenario = _day_plan(day)[0]
            run_qualification_day_from_disk(
                day=day,
                authorization_token=authorization_token,
                execution_gate=execution_gate,
                on_replay_start=replay_started,
                on_replay_complete=replay_completed,
            )

        if tuple(
            (item.day, item.policy_id, item.scenario) for item in completed
        ) != QUALIFICATION_PLAN:
            raise QualificationError("completed_qualification_order")

        if len(completed) != EXPECTED_REPLAY_COUNT:
            raise QualificationError("completed_qualification_count")

        payload = {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": "dev045-d6r20-q8-real-engine-result-v1",
            "status": "REAL_ENGINE_QUALIFICATION_PASS",
            "head": head,
            "d6r20_driver_blob": D6R20_DRIVER_BLOB,
            "m4_m6_binding_blob": M4_M6_BINDING_BLOB,
            "v2_patch_sha256": V2_PATCH_SHA256,
            "q7_result_sha256": Q7_RESULT_SHA256,
            "repository": asdict(repository),
            "hftbacktest": _runtime_payload(runtime),
            "replay_count": 20,
            "january_replays": 16,
            "april_replays": 4,
            "real_hftbacktest": True,
            "replays": [asdict(item) for item in completed],
            "canonical_economic_attempt": False,
            "canonical_attempt_consumed": False,
            "economic_arena_called": False,
            "strategy_ranking_performed": False,
            "economic_conclusion": "NOT_EVALUATED",
            "automatic_retry": False,
            "live_trading_authorized": False,
        }
        _write_json_new(SUCCESS_RESULT_PATH, payload)
        return payload

    except Exception as exc:
        failure = {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": "dev045-d6r20-q8-real-engine-failure-v1",
            "status": "REAL_ENGINE_QUALIFICATION_FAILED",
            "head": head,
            "d6r20_driver_blob": D6R20_DRIVER_BLOB,
            "m4_m6_binding_blob": M4_M6_BINDING_BLOB,
            "v2_patch_sha256": V2_PATCH_SHA256,
            "q7_result_sha256": Q7_RESULT_SHA256,
            "repository": asdict(repository),
            "hftbacktest": _runtime_payload(runtime),
            "completed_qualification_replay_count": len(completed),
            "current_day": current_day,
            "current_policy": current_policy,
            "current_scenario": current_scenario,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "canonical_economic_attempt": False,
            "canonical_attempt_consumed": False,
            "economic_arena_called": False,
            "strategy_ranking_performed": False,
            "economic_conclusion": "UNAVAILABLE",
            "automatic_retry": False,
            "live_trading_authorized": False,
        }
        _write_json_new(FAILURE_RESULT_PATH, failure)
        raise


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_HEAD",
    "Q7_RESULT_SHA256",
    "UPSTREAM_COMMIT",
    "D6R20_DRIVER_BLOB",
    "M4_M6_BINDING_BLOB",
    "V2_PATCH_SHA256",
    "EXPECTED_BRANCH",
    "EXPECTED_REMOTE_REF",
    "HFTBACKTEST_VERSION",
    "HFTBACKTEST_BINARY_SHA256",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "QUALIFICATION_DAY_ORDER",
    "JANUARY_POLICIES",
    "APRIL_POLICIES",
    "SCENARIO_ORDER",
    "QUALIFICATION_PLAN",
    "EXPECTED_REPLAY_COUNT",
    "HISTORICAL_KERNEL",
    "QUALIFICATION_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "REAL_HISTORICAL_QUALIFICATION_EXECUTED",
    "Q6_RERUN_AUTHORIZED",
    "Q7_RERUN_AUTHORIZED",
    "CANONICAL_RUNNER_IMPLEMENTED",
    "CANONICAL_ECONOMIC_ATTEMPT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "ECONOMIC_ARENA_EXECUTED",
    "STRATEGY_RANKING_PERFORMED",
    "AUTOMATIC_RETRY",
    "LIVE_TRADING_AUTHORIZED",
    "RESULT_ROOT",
    "SUCCESS_RESULT_PATH",
    "FAILURE_RESULT_PATH",
    "QualificationError",
    "RuntimeIdentity",
    "RepositoryIdentity",
    "ReplayExecutionDiagnostics",
    "validate_repository_preflight",
    "validate_runtime_identity",
    "validate_qualification_contract",
    "open_verified_qualification_source",
    "load_qualification_support",
    "run_bound_verified_qualification_replay",
    "run_verified_qualification_day",
    "run_qualification_day_from_disk",
    "run_real_engine_qualification",
]

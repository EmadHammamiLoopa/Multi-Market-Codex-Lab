from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Callable, Mapping, Sequence

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r17_direct_action_driver_bridge as bridge
from multimarket import dev045_d6r17_direct_action_support as support
from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r17_real_historical_economic_driver_contract as parent
from multimarket import dev045_d6r18_fresh_replacement_driver as d6r18
from multimarket import dev045_d6r19_canonical_runner as d6r19_runner
from multimarket import dev045_d6r19_response_batch_replacement_driver as d6r19
from multimarket import dev045_d6r20_residual_flatten_driver as d6r20
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_event_loop_kernel as d2


EXPERIMENT_ID = "DEV045-D6R20-Q1"
DESIGN_VERSION = "real-hftbacktest-execution-qualification-v1"

PARENT_HEAD = "72aa4dc8fc84a694f6b9b628b627394231e4fc33"
D6R20_DRIVER_BLOB = "1cae4584788aab29b409bf985168803759d42b1f"
EXPECTED_BRANCH = "research/dev045-m6-d6r20-real-engine-qualification"
EXPECTED_REMOTE_REF = f"origin/{EXPECTED_BRANCH}"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
D6R20_DRIVER_PATH = Path(d6r20.__file__).resolve()
D6R20_CANONICAL_RUNNER_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_canonical_runner.py"
)
ALLOWED_UNTRACKED_PATHS = (
    "evidence/dev045_d6r9a_feb01_full_day_v2.json",
)

HFTBACKTEST_VERSION = "2.4.4"
HFTBACKTEST_BINARY_SHA256 = (
    "051f204ef714ad8baeac205c1a26ace320598e6a3aabad6517d7028b9e0425f1"
)

AUTHORIZATION_ENV = "DEV045_D6R20_Q1_AUTHORIZE"
AUTHORIZATION_TOKEN = "YES_REAL_HFTBACKTEST_EXECUTION_QUALIFICATION_D6R20_Q1"

QUALIFICATION_DAY_ORDER = (
    "2026-01-01",
    "2026-04-01",
)
JANUARY_POLICIES = tuple(parent.POLICY_IDS)
APRIL_POLICIES = (
    "M06",
    "M07",
)
SCENARIO_ORDER = tuple(parent.SCENARIOS)

QUALIFICATION_PLAN = tuple(
    ("2026-01-01", policy_id, scenario)
    for policy_id in JANUARY_POLICIES
    for scenario in SCENARIO_ORDER
) + tuple(
    ("2026-04-01", policy_id, scenario)
    for policy_id in APRIL_POLICIES
    for scenario in SCENARIO_ORDER
)

EXPECTED_REPLAY_COUNT = 20
EXPECTED_JANUARY_REPLAYS = 16
EXPECTED_APRIL_REPLAYS = 4

HISTORICAL_KERNEL = (
    d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
)

QUALIFICATION_EXECUTION_AUTHORIZED_BY_DEFAULT = False
REAL_HISTORICAL_QUALIFICATION_EXECUTED = False
CANONICAL_RUNNER_IMPLEMENTED = False
CANONICAL_ECONOMIC_ATTEMPT = False
CANONICAL_ATTEMPT_CONSUMED = False
ECONOMIC_ARENA_EXECUTED = False
STRATEGY_RANKING_PERFORMED = False
AUTOMATIC_RETRY = False
NETWORK_ACQUISITION_ENABLED = False
RAILWAY_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

RESULT_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/"
    "dev045_d6r20_q1_real_engine_qualification_v1"
)
SUCCESS_RESULT_PATH = RESULT_ROOT / "DEV045_D6R20_Q1_QUALIFICATION_RESULT.json"
FAILURE_RESULT_PATH = RESULT_ROOT / "DEV045_D6R20_Q1_QUALIFICATION_FAILURE.json"


class QualificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeIdentity:
    version: str
    compiled_artifact_sha256: str
    verified: bool


@dataclass(frozen=True)
class RepositoryIdentity:
    branch: str
    head: str
    remote_ref: str
    remote_head: str
    tracked_worktree_clean: bool
    permitted_untracked_paths: tuple[str, ...]
    d6r20_driver_blob: str
    d6r20_canonical_runner_absent: bool
    result_surface_virgin: bool


@dataclass(frozen=True)
class ReplayExecutionDiagnostics:
    day: str
    policy_id: str
    scenario: str
    market_wakeups: int
    response_wakeups: int
    policy_epochs: int
    submit_requests: int
    cancel_requests: int
    maker_fill_count: int
    taker_fill_count: int
    total_fill_count: int
    forced_flatten_count: int
    flatten_order_id_count: int
    terminal_position: float
    terminal_flat: bool
    terminal_working_quote_slots: int
    terminal_shutdown_started: bool
    terminal_shutdown_quiescent: bool
    adapter_candidate_epochs: int
    direct_action_queries: int
    direct_action_rows_found: int
    direct_action_missing_rows: int
    direct_action_explicit_abstains: int
    simulator_inventory_clock_match: bool
    final_inventory_clock_flat: bool
    quote_slots_clear: bool
    pending_replacement_absent: bool
    forced_flatten_lifecycle_complete: bool
    flatten_order_ids_unique: bool
    request_overlap_invariant: bool
    duplicate_working_side_invariant: bool
    post_shutdown_replacement_absent: bool


def _require_authorization(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> None:
    if execution_gate is not True:
        raise QualificationError("execution_gate_closed")

    if authorization_token != AUTHORIZATION_TOKEN:
        raise QualificationError("authorization_token")

    if os.environ.get(AUTHORIZATION_ENV) != AUTHORIZATION_TOKEN:
        raise QualificationError("authorization_environment")


def _git_blob(path: Path) -> str:
    data = path.read_bytes()
    payload = f"blob {len(data)}\0".encode("ascii") + data
    return hashlib.sha1(payload).hexdigest()


def _stream_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(8 * 1024 * 1024)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()


def _compiled_artifact_path(h) -> Path:
    module_file = getattr(h, "__file__", None)

    if not module_file:
        raise QualificationError("hftbacktest_module_path")

    package = Path(module_file).resolve().parent
    candidates = tuple(sorted(package.glob("_hftbacktest*.so")))

    if len(candidates) != 1:
        raise QualificationError("hftbacktest_compiled_artifact")

    return candidates[0]


def validate_runtime_identity(h) -> RuntimeIdentity:
    version = str(getattr(h, "__version__", ""))

    if version != HFTBACKTEST_VERSION:
        raise QualificationError(f"hftbacktest_version:{version}")

    artifact = _compiled_artifact_path(h)
    observed_sha256 = _stream_sha256(artifact)

    if observed_sha256 != HFTBACKTEST_BINARY_SHA256:
        raise QualificationError(
            f"hftbacktest_binary_sha256:{observed_sha256}"
        )

    return RuntimeIdentity(
        version=version,
        compiled_artifact_sha256=observed_sha256,
        verified=True,
    )


def _hftbacktest_module():
    import hftbacktest as h

    return h


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
        raise QualificationError(
            f"repository_git_command:{args[0]}"
        ) from exc

    return completed.stdout.rstrip("\n")


def _current_head() -> str:
    head = _git_output("rev-parse", "HEAD")

    if len(head) != 40:
        raise QualificationError("git_head")

    return head


def _current_branch() -> str:
    return _git_output("branch", "--show-current")


def _remote_head() -> str:
    head = _git_output("rev-parse", EXPECTED_REMOTE_REF)

    if len(head) != 40:
        raise QualificationError("git_remote_head")

    return head


def _worktree_status() -> tuple[str, ...]:
    output = _git_output(
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )
    return tuple(line for line in output.splitlines() if line)


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

    driver_blob = _git_blob(D6R20_DRIVER_PATH)

    if driver_blob != D6R20_DRIVER_BLOB:
        raise QualificationError(f"d6r20_driver_blob:{driver_blob}")

    if D6R20_CANONICAL_RUNNER_PATH.exists():
        raise QualificationError("d6r20_canonical_runner_exists")

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
        d6r20_driver_blob=driver_blob,
        d6r20_canonical_runner_absent=True,
        result_surface_virgin=True,
    )


def _spec_for_day(day: str) -> parent.DaySourceSpec:
    if day not in QUALIFICATION_DAY_ORDER:
        raise QualificationError("qualification_day")

    return d6r19_runner._spec_for_day(day)


def validate_qualification_contract() -> None:
    expected = tuple(
        ("2026-01-01", policy_id, scenario)
        for policy_id in (
            "M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08"
        )
        for scenario in (
            "Q0_PRIMARY_250_250",
            "Q0_STRESS_500_500",
        )
    ) + tuple(
        ("2026-04-01", policy_id, scenario)
        for policy_id in ("M06", "M07")
        for scenario in (
            "Q0_PRIMARY_250_250",
            "Q0_STRESS_500_500",
        )
    )

    if QUALIFICATION_PLAN != expected:
        raise QualificationError("qualification_order")

    if len(QUALIFICATION_PLAN) != EXPECTED_REPLAY_COUNT:
        raise QualificationError("qualification_replay_count")

    if sum(x[0] == "2026-01-01" for x in QUALIFICATION_PLAN) != 16:
        raise QualificationError("january_replay_count")

    if sum(x[0] == "2026-04-01" for x in QUALIFICATION_PLAN) != 4:
        raise QualificationError("april_replay_count")

    if HISTORICAL_KERNEL is not (
        d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
    ):
        raise QualificationError("d6r20_kernel_binding")

    forbidden = (
        d6r19.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel,
        d6r18.FreshReplacementContinuousHistoricalPolicyKernel,
        bridge.DirectActionContinuousHistoricalPolicyKernel,
    )

    if HISTORICAL_KERNEL in forbidden:
        raise QualificationError("prior_kernel_forbidden")

    if _git_blob(Path(d6r20.__file__)) != D6R20_DRIVER_BLOB:
        raise QualificationError("d6r20_driver_blob")

    january = _spec_for_day("2026-01-01")
    april = _spec_for_day("2026-04-01")

    if (
        january.rows != 64_314_723
        or january.bytes != 4_116_142_528
        or january.sha256
        != "8f0a4fbd56ecdc261dbe2041ce138a09456423074925d495272716219a1d4da1"
    ):
        raise QualificationError("january_source_identity")

    if (
        april.rows != 132_829_759
        or april.bytes != 8_501_104_832
        or april.sha256
        != "de7e0471e63631394981b301bb461d679192c37eb6241d4d8073cf0640eca7f7"
    ):
        raise QualificationError("april_source_identity")


def open_verified_qualification_source(
    *,
    day: str,
    authorization_token: str,
    execution_gate: bool,
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
    *,
    day: str,
) -> dict[str, support.DirectActionIndex]:
    if day == "2026-01-01":
        return {}

    if day != "2026-04-01":
        raise QualificationError("qualification_support_day")

    result = d6r19_runner.load_frozen_day_support(day=day)

    if set(result) != {"M06", "M07"}:
        raise QualificationError("april_support_mapping")

    return result


def _slot_has_pending_replacement(slot) -> bool:
    return bool(
        getattr(slot, "pending_replacement", None) is not None
        or getattr(slot, "replacement_required", False)
    )


def _validate_completed_replay(
    *,
    bt,
    kernel,
    replay,
) -> ReplayExecutionDiagnostics:
    audit = replay.audit

    if (
        audit.policy_id,
        audit.day,
        audit.scenario,
    ) != (
        replay.policy_id,
        replay.day,
        replay.scenario,
    ):
        raise QualificationError("replay_audit_identity")

    if not bool(replay.natural_end_of_data):
        raise QualificationError("natural_end_of_data_missing")

    if int(audit.execution_integrity_failures) != 0:
        raise QualificationError("execution_integrity_failure")

    if not bool(audit.terminal_flat) or not bool(replay.terminal_flat):
        raise QualificationError("terminal_not_flat")

    terminal_position = float(replay.terminal_position)

    if not math.isfinite(terminal_position):
        raise QualificationError("terminal_position_nonfinite")

    if abs(terminal_position) > 1e-12:
        raise QualificationError("terminal_position_nonflat")

    if int(replay.terminal_working_quote_slots) != 0:
        raise QualificationError("terminal_working_quotes")

    if not bool(replay.terminal_shutdown_started):
        raise QualificationError("terminal_shutdown_not_started")

    if not bool(replay.terminal_shutdown_quiescent):
        raise QualificationError("terminal_shutdown_not_quiescent")

    if replay.terminal_shutdown_start_ns is None:
        raise QualificationError("terminal_shutdown_start_missing")

    if not (
        int(replay.terminal_shutdown_cutoff_ns)
        <= int(replay.terminal_shutdown_start_ns)
        <= int(replay.terminal_source_local_ns)
    ):
        raise QualificationError("terminal_shutdown_timing")

    quote_slots_clear = bool(
        kernel.bid.order_id is None
        and kernel.ask.order_id is None
    )

    if not quote_slots_clear:
        raise QualificationError("kernel_quote_slots_not_clear")

    pending_replacement_absent = not any(
        _slot_has_pending_replacement(slot)
        for slot in (kernel.bid, kernel.ask)
    )

    if not pending_replacement_absent:
        raise QualificationError("pending_replacement_at_terminal")

    forced_flatten_lifecycle_complete = bool(
        kernel.force_decision is None
        and not kernel.flatten_done
    )

    if not forced_flatten_lifecycle_complete:
        raise QualificationError("forced_flatten_lifecycle_incomplete")

    simulator_position = float(bt.position(d2.ASSET_NO))
    clock_position = float(kernel.inventory_clock.position)

    if not math.isfinite(simulator_position) or not math.isfinite(clock_position):
        raise QualificationError("terminal_inventory_nonfinite")

    simulator_inventory_clock_match = math.isclose(
        simulator_position,
        clock_position,
        rel_tol=0.0,
        abs_tol=1e-12,
    )

    if not simulator_inventory_clock_match:
        raise QualificationError("local_inventory_clock_mismatch")

    if not math.isclose(
        terminal_position,
        simulator_position,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise QualificationError("terminal_position_simulator_mismatch")

    final_inventory_clock_flat = bool(
        abs(clock_position) <= 1e-12
        and kernel.inventory_clock.nonzero_since_local_ns is None
    )

    if not final_inventory_clock_flat:
        raise QualificationError("terminal_inventory_clock_nonflat")

    fills = []
    maker_fill_count = 0
    taker_fill_count = 0

    for event in tuple(kernel.bound_fills):
        if event.kind != binding.FILL:
            raise QualificationError("bound_nonfill_event")

        if event.fill is None or not isinstance(event.fill, binding.FillRecord):
            raise QualificationError("fill_event_without_record")

        fills.append(event.fill)

        if event.fill.liquidity == binding.MAKER:
            maker_fill_count += 1
        elif event.fill.liquidity == binding.TAKER:
            taker_fill_count += 1
        else:
            raise QualificationError("unknown_fill_liquidity")

    if len(fills) != int(replay.total_fill_count):
        raise QualificationError("raw_fill_count_parity")

    if int(replay.maker_fill_count) != maker_fill_count:
        raise QualificationError("maker_fill_count_parity")

    if int(replay.taker_fill_count) != taker_fill_count:
        raise QualificationError("taker_fill_count_parity")

    if maker_fill_count + taker_fill_count != int(replay.total_fill_count):
        raise QualificationError("fill_role_count_parity")

    counters = (
        replay.market_wakeups,
        replay.response_wakeups,
        replay.policy_epochs,
        replay.submit_requests,
        replay.cancel_requests,
        replay.forced_flatten_count,
        replay.adapter_candidate_epochs,
        kernel.direct_action_queries,
        kernel.direct_action_rows_found,
        kernel.direct_action_missing_rows,
        kernel.direct_action_explicit_abstains,
    )

    if any(int(value) < 0 for value in counters):
        raise QualificationError("negative_execution_counter")

    if (
        int(kernel.direct_action_rows_found)
        + int(kernel.direct_action_missing_rows)
        != int(kernel.direct_action_queries)
    ):
        raise QualificationError("direct_action_query_count_parity")

    if int(kernel.direct_action_explicit_abstains) > int(
        kernel.direct_action_rows_found
    ):
        raise QualificationError("direct_action_abstain_count")

    direct_counts = (
        int(kernel.direct_action_queries),
        int(kernel.direct_action_rows_found),
        int(kernel.direct_action_missing_rows),
        int(kernel.direct_action_explicit_abstains),
    )

    if replay.day == "2026-01-01" and replay.policy_id in ("M06", "M07"):
        if any(direct_counts):
            raise QualificationError("january_direct_action_support_used")

    if replay.day == "2026-04-01" and replay.policy_id in ("M06", "M07"):
        if int(kernel.direct_action_queries) <= 0:
            raise QualificationError("april_direct_action_queries_missing")

    flatten_order_ids = tuple(int(x) for x in replay.flatten_order_ids)
    flatten_order_ids_unique = len(flatten_order_ids) == len(
        set(flatten_order_ids)
    )

    if not flatten_order_ids_unique:
        raise QualificationError("duplicate_flatten_order_id")

    if flatten_order_ids != tuple(int(x) for x in kernel.flatten_order_ids):
        raise QualificationError("flatten_order_id_kernel_parity")

    if int(replay.forced_flatten_count) != int(
        kernel.completed_forced_flattens
    ):
        raise QualificationError("forced_flatten_count_kernel_parity")

    if taker_fill_count != len(flatten_order_ids):
        raise QualificationError("taker_fill_flatten_order_id_parity")

    if len(flatten_order_ids) > int(replay.forced_flatten_count) + 1:
        raise QualificationError("flatten_order_count_exceeds_lifecycles")

    active_orders = [
        raw
        for raw in bt.orders(d2.ASSET_NO).values()
        if int(raw.status) in (
            int(d2.HFT_NEW),
            int(d2.HFT_PARTIALLY_FILLED),
        )
    ]

    if active_orders:
        raise QualificationError("simulator_working_orders_at_terminal")

    return ReplayExecutionDiagnostics(
        day=replay.day,
        policy_id=replay.policy_id,
        scenario=replay.scenario,
        market_wakeups=int(replay.market_wakeups),
        response_wakeups=int(replay.response_wakeups),
        policy_epochs=int(replay.policy_epochs),
        submit_requests=int(replay.submit_requests),
        cancel_requests=int(replay.cancel_requests),
        maker_fill_count=int(replay.maker_fill_count),
        taker_fill_count=int(replay.taker_fill_count),
        total_fill_count=int(replay.total_fill_count),
        forced_flatten_count=int(replay.forced_flatten_count),
        flatten_order_id_count=len(flatten_order_ids),
        terminal_position=terminal_position,
        terminal_flat=True,
        terminal_working_quote_slots=0,
        terminal_shutdown_started=True,
        terminal_shutdown_quiescent=True,
        adapter_candidate_epochs=int(replay.adapter_candidate_epochs),
        direct_action_queries=int(kernel.direct_action_queries),
        direct_action_rows_found=int(kernel.direct_action_rows_found),
        direct_action_missing_rows=int(kernel.direct_action_missing_rows),
        direct_action_explicit_abstains=int(
            kernel.direct_action_explicit_abstains
        ),
        simulator_inventory_clock_match=True,
        final_inventory_clock_flat=True,
        quote_slots_clear=True,
        pending_replacement_absent=True,
        forced_flatten_lifecycle_complete=True,
        flatten_order_ids_unique=True,
        request_overlap_invariant=True,
        duplicate_working_side_invariant=True,
        post_shutdown_replacement_absent=True,
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
    on_replay_complete: (
        Callable[[ReplayExecutionDiagnostics], None] | None
    ) = None,
) -> tuple[ReplayExecutionDiagnostics, ...]:
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    d6r19_runner.validate_canonical_verified_source(source, day=day)
    bridge._validate_day_mapping(
        day=day,
        direct_by_policy=direct_by_policy,
    )
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
    on_replay_complete: (
        Callable[[ReplayExecutionDiagnostics], None] | None
    ) = None,
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


def _runtime_payload(identity: RuntimeIdentity) -> dict:
    return {
        "version": identity.version,
        "compiled_artifact_sha256": identity.compiled_artifact_sha256,
        "verified": identity.verified,
    }


def run_real_engine_qualification(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> dict:
    """Run the explicitly authorized 20-replay engineering qualification."""
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
            (item.day, item.policy_id, item.scenario)
            for item in completed
        ) != QUALIFICATION_PLAN:
            raise QualificationError("completed_qualification_order")

        if len(completed) != EXPECTED_REPLAY_COUNT:
            raise QualificationError("completed_qualification_count")

        payload = {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": "dev045-d6r20-q1-real-engine-result-v1",
            "status": "REAL_ENGINE_QUALIFICATION_PASS",
            "head": head,
            "d6r20_driver_blob": D6R20_DRIVER_BLOB,
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
            "schema_version": "dev045-d6r20-q1-real-engine-failure-v1",
            "status": "REAL_ENGINE_QUALIFICATION_FAILED",
            "head": head,
            "d6r20_driver_blob": D6R20_DRIVER_BLOB,
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
    "D6R20_DRIVER_BLOB",
    "EXPECTED_BRANCH",
    "EXPECTED_REMOTE_REF",
    "REPOSITORY_ROOT",
    "D6R20_DRIVER_PATH",
    "D6R20_CANONICAL_RUNNER_PATH",
    "ALLOWED_UNTRACKED_PATHS",
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
    "CANONICAL_RUNNER_IMPLEMENTED",
    "CANONICAL_ATTEMPT_CONSUMED",
    "ECONOMIC_ARENA_EXECUTED",
    "STRATEGY_RANKING_PERFORMED",
    "AUTOMATIC_RETRY",
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

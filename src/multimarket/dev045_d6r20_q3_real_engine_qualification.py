from __future__ import annotations

from dataclasses import asdict
import json
import math
import os
from pathlib import Path
from typing import Callable, Mapping

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r17_direct_action_driver_bridge as bridge
from multimarket import dev045_d6r17_direct_action_support as support
from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r18_fresh_replacement_driver as d6r18
from multimarket import dev045_d6r19_canonical_runner as d6r19_runner
from multimarket import dev045_d6r19_response_batch_replacement_driver as d6r19
from multimarket import dev045_d6r20_q2_real_engine_qualification as q2
from multimarket import dev045_d6r20_residual_flatten_driver as d6r20
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_event_loop_kernel as d2


EXPERIMENT_ID = "DEV045-D6R20-Q3"
DESIGN_VERSION = (
    "real-hftbacktest-v2-order-values-validator-qualification-v1"
)

PARENT_HEAD = "835676a3d3bb5d7780f63a2e2373c32a59315cab"
Q2_FAILED_HEAD = PARENT_HEAD
Q2_FAILURE_SHA256 = (
    "dcfec8623e1a9e660f3ca5116fb3cc974fd87a8d4764f6c65fcb47eae3f671b9"
)
ENGINE_FIX_HEAD = q2.ENGINE_FIX_HEAD
UPSTREAM_COMMIT = q2.UPSTREAM_COMMIT
D6R20_DRIVER_BLOB = q2.D6R20_DRIVER_BLOB
M4_M6_BINDING_BLOB = q2.M4_M6_BINDING_BLOB
V2_PATCH_SHA256 = q2.V2_PATCH_SHA256
PATCHED_SOURCE_DIFF_SHA256 = q2.PATCHED_SOURCE_DIFF_SHA256

EXPECTED_BRANCH = "research/dev045-m6-d6r20-q3-order-values-validator-fix"
EXPECTED_REMOTE_REF = f"origin/{EXPECTED_BRANCH}"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
D6R20_DRIVER_PATH = q2.D6R20_DRIVER_PATH
M4_M6_BINDING_PATH = q2.M4_M6_BINDING_PATH
V2_PATCH_PATH = q2.V2_PATCH_PATH
D6R20_CANONICAL_RUNNER_PATH = q2.D6R20_CANONICAL_RUNNER_PATH
D6R21_CANONICAL_RUNNER_PATH = q2.D6R21_CANONICAL_RUNNER_PATH
ALLOWED_UNTRACKED_PATHS = q2.ALLOWED_UNTRACKED_PATHS

HFTBACKTEST_VERSION = q2.HFTBACKTEST_VERSION
HFTBACKTEST_BINARY_SHA256 = q2.HFTBACKTEST_BINARY_SHA256
OLD_HFTBACKTEST_BINARY_SHA256 = q2.OLD_HFTBACKTEST_BINARY_SHA256

AUTHORIZATION_ENV = "DEV045_D6R20_Q3_AUTHORIZE"
AUTHORIZATION_TOKEN = (
    "YES_REAL_HFTBACKTEST_V2_EXECUTION_QUALIFICATION_D6R20_Q3"
)

QUALIFICATION_DAY_ORDER = q2.QUALIFICATION_DAY_ORDER
JANUARY_POLICIES = q2.JANUARY_POLICIES
APRIL_POLICIES = q2.APRIL_POLICIES
SCENARIO_ORDER = q2.SCENARIO_ORDER
QUALIFICATION_PLAN = q2.QUALIFICATION_PLAN
EXPECTED_REPLAY_COUNT = q2.EXPECTED_REPLAY_COUNT
EXPECTED_JANUARY_REPLAYS = q2.EXPECTED_JANUARY_REPLAYS
EXPECTED_APRIL_REPLAYS = q2.EXPECTED_APRIL_REPLAYS

HISTORICAL_KERNEL = (
    d6r20.ExecutionTimeResidualFlattenContinuousHistoricalPolicyKernel
)

QUALIFICATION_EXECUTION_AUTHORIZED_BY_DEFAULT = False
REAL_HISTORICAL_QUALIFICATION_EXECUTED = False
Q1_RERUN_AUTHORIZED = False
Q2_RERUN_AUTHORIZED = False
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
    "dev045_d6r20_q3_real_engine_qualification_v1"
)
SUCCESS_RESULT_PATH = RESULT_ROOT / "DEV045_D6R20_Q3_QUALIFICATION_RESULT.json"
FAILURE_RESULT_PATH = RESULT_ROOT / "DEV045_D6R20_Q3_QUALIFICATION_FAILURE.json"


QualificationError = q2.QualificationError
RuntimeIdentity = q2.RuntimeIdentity
RepositoryIdentity = q2.RepositoryIdentity
ReplayExecutionDiagnostics = q2.ReplayExecutionDiagnostics


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


_git_blob = q2._git_blob
_stream_sha256 = q2._stream_sha256
_compiled_artifact_path = q2._compiled_artifact_path
_git_output = q2._git_output
_current_head = q2._current_head
_current_branch = q2._current_branch
_worktree_status = q2._worktree_status
_slot_has_pending_replacement = q2._slot_has_pending_replacement


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

    driver_blob = _git_blob(D6R20_DRIVER_PATH)

    if driver_blob != D6R20_DRIVER_BLOB:
        raise QualificationError(f"d6r20_driver_blob:{driver_blob}")

    binding_blob = _git_blob(M4_M6_BINDING_PATH)

    if binding_blob != M4_M6_BINDING_BLOB:
        raise QualificationError(f"m4_m6_binding_blob:{binding_blob}")

    patch_sha256 = _stream_sha256(V2_PATCH_PATH)

    if patch_sha256 != V2_PATCH_SHA256:
        raise QualificationError(f"v2_patch_sha256:{patch_sha256}")

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
        d6r20_driver_blob=driver_blob,
        m4_m6_binding_blob=binding_blob,
        v2_patch_sha256=patch_sha256,
        d6r20_canonical_runner_absent=True,
        d6r21_canonical_runner_absent=True,
        result_surface_virgin=True,
    )


def _spec_for_day(day: str):
    if day not in QUALIFICATION_DAY_ORDER:
        raise QualificationError("qualification_day")

    return d6r19_runner._spec_for_day(day)


def validate_qualification_contract() -> None:
    q2.validate_qualification_contract()

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
    return q2.load_qualification_support(day=day)


def _order_values_tuple(order_dict) -> tuple:
    """Materialize OrderDict values through hftbacktest's supported API."""
    values = order_dict.values()
    next_value = getattr(values, "next", None)

    if not callable(next_value):
        raise QualificationError("order_values_next_unavailable")

    result = []

    while True:
        raw = next_value()

        if raw is None:
            break

        result.append(raw)

    return tuple(result)


def _active_orders_tuple(order_dict) -> tuple:
    return tuple(
        raw
        for raw in _order_values_tuple(order_dict)
        if int(raw.status) in (
            int(d2.HFT_NEW),
            int(d2.HFT_PARTIALLY_FILLED),
        )
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

    active_orders = _active_orders_tuple(bt.orders(d2.ASSET_NO))

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
    """Run the explicitly authorized 20-replay Q3 engineering qualification."""
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
            "schema_version": "dev045-d6r20-q3-real-engine-result-v1",
            "status": "REAL_ENGINE_QUALIFICATION_PASS",
            "head": head,
            "d6r20_driver_blob": D6R20_DRIVER_BLOB,
            "m4_m6_binding_blob": M4_M6_BINDING_BLOB,
            "v2_patch_sha256": V2_PATCH_SHA256,
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
            "schema_version": "dev045-d6r20-q3-real-engine-failure-v1",
            "status": "REAL_ENGINE_QUALIFICATION_FAILED",
            "head": head,
            "d6r20_driver_blob": D6R20_DRIVER_BLOB,
            "m4_m6_binding_blob": M4_M6_BINDING_BLOB,
            "v2_patch_sha256": V2_PATCH_SHA256,
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
    "Q2_FAILED_HEAD",
    "Q2_FAILURE_SHA256",
    "ENGINE_FIX_HEAD",
    "UPSTREAM_COMMIT",
    "D6R20_DRIVER_BLOB",
    "M4_M6_BINDING_BLOB",
    "V2_PATCH_SHA256",
    "PATCHED_SOURCE_DIFF_SHA256",
    "EXPECTED_BRANCH",
    "EXPECTED_REMOTE_REF",
    "HFTBACKTEST_VERSION",
    "HFTBACKTEST_BINARY_SHA256",
    "OLD_HFTBACKTEST_BINARY_SHA256",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "QUALIFICATION_DAY_ORDER",
    "JANUARY_POLICIES",
    "APRIL_POLICIES",
    "SCENARIO_ORDER",
    "QUALIFICATION_PLAN",
    "EXPECTED_REPLAY_COUNT",
    "EXPECTED_JANUARY_REPLAYS",
    "EXPECTED_APRIL_REPLAYS",
    "HISTORICAL_KERNEL",
    "QUALIFICATION_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "REAL_HISTORICAL_QUALIFICATION_EXECUTED",
    "Q1_RERUN_AUTHORIZED",
    "Q2_RERUN_AUTHORIZED",
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

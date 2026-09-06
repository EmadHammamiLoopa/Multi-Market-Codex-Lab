from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Sequence
import os

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r17_canonical_runner_contract as contract
from multimarket import dev045_d6r17_direct_action_driver_bridge as bridge
from multimarket import dev045_d6r17_direct_action_support as support
from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r17_real_historical_economic_driver_contract as parent
from multimarket import dev045_d6r18_canonical_runner as frozen
from multimarket import dev045_d6r18_fresh_replacement_driver as d6r18_driver
from multimarket import dev045_d6r19_response_batch_replacement_driver as coherent
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_economic_arena as m6


EXPERIMENT_ID = "DEV045-D6R19"
DESIGN_VERSION = "canonical-historical-economic-runner-v1"

PARENT_HEAD = "fb37731318703fe1d2283c2d0f0b9c8b8164c499"
D6R19_DRIVER_BLOB = "5aaf880795f796d5086b3b86a6e7dde0fd7f56ed"
D6R18_RUNNER_BLOB = "f8d81680ef75a3095f57bada6e01664391e69b72"

AUTHORIZATION_ENV = "DEV045_D6R19_AUTHORIZE"
AUTHORIZATION_TOKEN = (
    "YES_JAN_JUL_M6_MAKER_ECONOMIC_ARENA_D6R19_ONE_SHOT"
)

BOUNDARY_SEMANTIC = frozen.BOUNDARY_SEMANTIC

DAY_ORDER = tuple(frozen.DAY_ORDER)
POLICY_ORDER = tuple(frozen.POLICY_ORDER)
SCENARIO_ORDER = tuple(frozen.SCENARIO_ORDER)
REPLAY_ORDER = tuple(frozen.REPLAY_ORDER)

EXPECTED_DAY_COUNT = frozen.EXPECTED_DAY_COUNT
EXPECTED_REPLAYS_PER_DAY = frozen.EXPECTED_REPLAYS_PER_DAY
EXPECTED_TOTAL_REPLAYS = frozen.EXPECTED_TOTAL_REPLAYS

HISTORICAL_KERNEL = (
    coherent.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel
)

CANONICAL_SOURCE_OPEN_IMPLEMENTED = True
CANONICAL_DAY_MATRIX_IMPLEMENTED = True
FINAL_112_ARENA_IMPLEMENTED = True
FRESH_REPLACEMENT_SEMANTICS = True
RESPONSE_BATCH_COHERENT_REPLACEMENT = True

CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT = False
CANONICAL_ATTEMPT_CONSUMED = False
AUTOMATIC_RETRY = False
RERUN_AFTER_ATTEMPT_CONSUMPTION = False
TUNING_AFTER_FIRST_OUTPUT = False

PRE_REPLAY_SOURCE_SHA_FAILURE_CONSUMES = False
PRE_REPLAY_SOURCE_OPEN_FAILURE_CONSUMES = False
PRE_REPLAY_SUPPORT_FAILURE_CONSUMES = False
PRE_REPLAY_VALIDATION_FAILURE_CONSUMES = False
FIRST_HISTORICAL_REPLAY_ENTRY_CONSUMES = True

NETWORK_ACQUISITION_ENABLED = False
RAILWAY_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

RESULT_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/"
    "dev045_d6r19_canonical_economic_run_v1"
)
FINAL_RESULT_PATH = (
    RESULT_ROOT
    / "DEV045_D6R19_CANONICAL_ECONOMIC_RESULT.json"
)
FAILURE_RESULT_PATH = (
    RESULT_ROOT
    / "DEV045_D6R19_CANONICAL_FAILURE.json"
)


# These frozen D6R18 structures and pure helpers define the unchanged result,
# fill, and accounting protocol.  Reusing them prevents a new conversion or
# economic interpretation from entering the D6R19 successor.
CanonicalRunnerError = frozen.CanonicalRunnerError
CapturedReplay = frozen.CapturedReplay
DayMatrixResult = frozen.DayMatrixResult
extract_fill_records = frozen.extract_fill_records
verify_reaccount_parity = frozen.verify_reaccount_parity


def validate_runner_contract() -> None:
    frozen.validate_runner_contract()

    if DAY_ORDER != tuple(contract.DAY_ORDER):
        raise CanonicalRunnerError("day_order")

    if POLICY_ORDER != tuple(contract.POLICY_ORDER):
        raise CanonicalRunnerError("policy_order")

    if SCENARIO_ORDER != tuple(contract.SCENARIO_ORDER):
        raise CanonicalRunnerError("scenario_order")

    if len(REPLAY_ORDER) != EXPECTED_TOTAL_REPLAYS:
        raise CanonicalRunnerError("replay_count")

    if HISTORICAL_KERNEL is not (
        coherent.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel
    ):
        raise CanonicalRunnerError("d6r19_kernel_binding")

    if HISTORICAL_KERNEL is (
        d6r18_driver.FreshReplacementContinuousHistoricalPolicyKernel
    ):
        raise CanonicalRunnerError("d6r18_kernel_forbidden")

    if HISTORICAL_KERNEL is (
        bridge.DirectActionContinuousHistoricalPolicyKernel
    ):
        raise CanonicalRunnerError("d6r17_kernel_forbidden")


def _require_authorization(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> None:
    if execution_gate is not True:
        raise CanonicalRunnerError("execution_gate_closed")

    if authorization_token != AUTHORIZATION_TOKEN:
        raise CanonicalRunnerError("authorization_token")

    if os.environ.get(AUTHORIZATION_ENV) != AUTHORIZATION_TOKEN:
        raise CanonicalRunnerError("authorization_environment")


def _spec_for_day(day: str) -> parent.DaySourceSpec:
    """Reuse the frozen D6R18 path to D6R17's June-amended source specs."""
    return frozen._spec_for_day(day)


def validate_canonical_verified_source(
    source: adapter.CanonicalJanMemmap,
    *,
    day: str,
) -> parent.DaySourceSpec:
    return frozen.validate_canonical_verified_source(source, day=day)


def open_verified_day_source(
    *,
    day: str,
    authorization_token: str,
    execution_gate: bool,
) -> adapter.CanonicalJanMemmap:
    """Authorize before the frozen full-SHA/read-only-memmap opener."""
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
        validate_canonical_verified_source(source, day=day)
    except Exception:
        source.close()
        raise

    return source


def load_frozen_day_support(
    *,
    day: str,
) -> dict[str, support.DirectActionIndex]:
    return frozen.load_frozen_day_support(day=day)


def _hftbacktest_module():
    import hftbacktest as h

    return h


def run_bound_verified_replay_with_fills(
    source: adapter.CanonicalJanMemmap,
    *,
    policy_id: str,
    day: str,
    scenario: str,
    direct_index: support.DirectActionIndex | None = None,
) -> CapturedReplay:
    """Run the D6R19 kernel and capture exact raw M6 fills before close."""
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

    replay = None
    fills: tuple[m6.FillRecord, ...] = ()
    direct_action_queries = 0
    direct_action_rows_found = 0
    direct_action_missing_rows = 0
    direct_action_explicit_abstains = 0

    try:
        terminal_source_local_ns = int(
            source.data[-1]["local_ts"]
        )

        kernel = HISTORICAL_KERNEL(
            bt=bt,
            h=h,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            terminal_source_local_ns=terminal_source_local_ns,
            direct_index=direct_index,
        )
        replay = kernel.run_full_day()

        # Every value below is captured and checked while bt remains open.
        fills = extract_fill_records(tuple(kernel.bound_fills))
        direct_action_queries = int(kernel.direct_action_queries)
        direct_action_rows_found = int(
            kernel.direct_action_rows_found
        )
        direct_action_missing_rows = int(
            kernel.direct_action_missing_rows
        )
        direct_action_explicit_abstains = int(
            kernel.direct_action_explicit_abstains
        )

        verify_reaccount_parity(
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            replay_total_fill_count=replay.total_fill_count,
            replay_cycles=replay.cycles,
            fills=fills,
        )
    finally:
        rc = int(bt.close())

        if rc != 0:
            raise CanonicalRunnerError(f"backtest_close_rc:{rc}")

    if replay is None:
        raise CanonicalRunnerError("replay_missing")

    return CapturedReplay(
        replay=replay,
        fills=fills,
        direct_action_queries=direct_action_queries,
        direct_action_rows_found=direct_action_rows_found,
        direct_action_missing_rows=direct_action_missing_rows,
        direct_action_explicit_abstains=direct_action_explicit_abstains,
    )


def run_verified_day_matrix_with_boundary(
    source: adapter.CanonicalJanMemmap,
    *,
    day: str,
    direct_by_policy: Mapping[str, support.DirectActionIndex],
    authorization_token: str,
    execution_gate: bool,
    mark_attempt_started: Callable[[], None],
) -> DayMatrixResult:
    """Validate first; cross the attempt boundary immediately before replay."""
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    validate_canonical_verified_source(source, day=day)
    bridge._validate_day_mapping(
        day=day,
        direct_by_policy=direct_by_policy,
    )
    before = base._stat_identity(source.path)

    completed = []

    for policy_id in POLICY_ORDER:
        direct_index = direct_by_policy.get(policy_id)

        for scenario in SCENARIO_ORDER:
            mark_attempt_started()
            captured = run_bound_verified_replay_with_fills(
                source,
                policy_id=policy_id,
                day=day,
                scenario=scenario,
                direct_index=direct_index,
            )

            if captured.replay.audit.execution_integrity_failures != 0:
                raise CanonicalRunnerError(
                    "execution_integrity_failure"
                )

            if not captured.replay.audit.terminal_flat:
                raise CanonicalRunnerError("terminal_not_flat")

            if captured.replay.terminal_working_quote_slots != 0:
                raise CanonicalRunnerError("terminal_working_quotes")

            completed.append(captured)

    after = base._stat_identity(source.path)

    if before != after:
        raise CanonicalRunnerError("source_identity_changed")

    return DayMatrixResult(day=day, replays=tuple(completed))


def run_canonical_day_from_disk_with_boundary(
    *,
    day: str,
    authorization_token: str,
    execution_gate: bool,
    mark_attempt_started: Callable[[], None],
) -> DayMatrixResult:
    """Open one verified source once and reuse it for all 16 day replays."""
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    direct_by_policy = load_frozen_day_support(day=day)

    with open_verified_day_source(
        day=day,
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    ) as source:
        return run_verified_day_matrix_with_boundary(
            source,
            day=day,
            direct_by_policy=direct_by_policy,
            authorization_token=authorization_token,
            execution_gate=execution_gate,
            mark_attempt_started=mark_attempt_started,
        )


def day_evidence_path(day: str) -> Path:
    if day not in DAY_ORDER:
        raise CanonicalRunnerError("day_evidence_day")

    return RESULT_ROOT / f"{day}_DEV045_D6R19_DAY_RESULT.json"


def _write_json_new(path: Path, payload: dict) -> Path:
    return frozen._write_json_new(path, payload)


def write_day_evidence(result: DayMatrixResult) -> Path:
    return _write_json_new(
        day_evidence_path(result.day),
        {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": "dev045-d6r19-canonical-day-result-v1",
            "status": "DAY_COMPLETE",
            "day": result.day,
            "replay_count": len(result.replays),
            "response_batch_coherent_replacement": True,
            "fresh_replacement_semantics": True,
            "replays": [
                frozen._replay_payload(captured)
                for captured in result.replays
            ],
        },
    )


def _flatten_streams(
    days: Sequence[DayMatrixResult],
) -> tuple[
    tuple[m6.FillRecord, ...],
    tuple[m6.FillRecord, ...],
    tuple[m6.ReplayAudit, ...],
]:
    return frozen._flatten_streams(days)


def _require_virgin_result_surface() -> None:
    if FINAL_RESULT_PATH.exists():
        raise CanonicalRunnerError("final_result_exists")

    if FAILURE_RESULT_PATH.exists():
        raise CanonicalRunnerError("prior_failure_evidence_exists")

    if RESULT_ROOT.exists():
        if not RESULT_ROOT.is_dir():
            raise CanonicalRunnerError("result_root_not_directory")

        if any(RESULT_ROOT.iterdir()):
            raise CanonicalRunnerError("result_surface_not_virgin")


def run_full_canonical_arena(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> dict:
    """One-shot D6R19 entrypoint. Never called by development or CI."""
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    validate_runner_contract()
    _require_virgin_result_surface()

    completed_days = []
    execution_started = False

    def mark_attempt_started() -> None:
        nonlocal execution_started
        execution_started = True

    try:
        for day in DAY_ORDER:
            day_result = run_canonical_day_from_disk_with_boundary(
                day=day,
                authorization_token=authorization_token,
                execution_gate=execution_gate,
                mark_attempt_started=mark_attempt_started,
            )
            write_day_evidence(day_result)
            completed_days.append(day_result)

        if len(completed_days) != EXPECTED_DAY_COUNT:
            raise CanonicalRunnerError("completed_day_count")

        primary, stress, audits = _flatten_streams(completed_days)

        # This is the sole arena call and is unreachable before 112 replays.
        arena = m6.run_economic_arena(
            primary_fills=primary,
            stress_fills=stress,
            audits=audits,
        )

        payload = {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": (
                "dev045-d6r19-canonical-economic-result-v1"
            ),
            "status": "CANONICAL_112_COMPLETE",
            "replay_count": EXPECTED_TOTAL_REPLAYS,
            "day_count": EXPECTED_DAY_COUNT,
            "audit_count": len(audits),
            "primary_raw_fill_count": len(primary),
            "stress_raw_fill_count": len(stress),
            "arena": arena,
            "attempt_consumed": True,
            "attempt_boundary": BOUNDARY_SEMANTIC,
            "response_batch_coherent_replacement": True,
            "fresh_replacement_semantics": True,
            "live_trading_authorized": False,
        }
        _write_json_new(FINAL_RESULT_PATH, payload)
        return payload

    except Exception as exc:
        if not execution_started:
            raise

        failure = {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": "dev045-d6r19-canonical-failure-v1",
            "status": "CANONICAL_ATTEMPT_FAILED",
            "attempt_consumed": True,
            "attempt_boundary": BOUNDARY_SEMANTIC,
            "completed_days": [
                result.day
                for result in completed_days
            ],
            "completed_replays": sum(
                len(result.replays)
                for result in completed_days
            ),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "automatic_retry": False,
            "rerun_forbidden": True,
            "response_batch_coherent_replacement": True,
            "fresh_replacement_semantics": True,
            "live_trading_authorized": False,
        }
        _write_json_new(FAILURE_RESULT_PATH, failure)
        raise


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_HEAD",
    "D6R19_DRIVER_BLOB",
    "D6R18_RUNNER_BLOB",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "BOUNDARY_SEMANTIC",
    "DAY_ORDER",
    "POLICY_ORDER",
    "SCENARIO_ORDER",
    "REPLAY_ORDER",
    "EXPECTED_TOTAL_REPLAYS",
    "HISTORICAL_KERNEL",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "AUTOMATIC_RETRY",
    "RESPONSE_BATCH_COHERENT_REPLACEMENT",
    "CapturedReplay",
    "DayMatrixResult",
    "validate_runner_contract",
    "open_verified_day_source",
    "load_frozen_day_support",
    "extract_fill_records",
    "verify_reaccount_parity",
    "run_bound_verified_replay_with_fills",
    "run_verified_day_matrix_with_boundary",
    "run_canonical_day_from_disk_with_boundary",
    "day_evidence_path",
    "write_day_evidence",
    "run_full_canonical_arena",
]

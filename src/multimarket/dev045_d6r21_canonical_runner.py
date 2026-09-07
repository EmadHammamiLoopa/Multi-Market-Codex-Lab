from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

from multimarket import dev045_d6r18_canonical_runner as frozen
from multimarket import dev045_d6r18_fresh_replacement_driver as d6r18_driver
from multimarket import dev045_d6r19_canonical_runner as d6r19
from multimarket import dev045_d6r19_response_batch_replacement_driver as d6r19_driver
from multimarket import dev045_d6r20_q6_initial_book_readiness_driver as q6_driver
from multimarket import dev045_d6r20_q8_real_engine_qualification as q8q
from multimarket import dev045_d6r20_q8_terminal_shutdown_grid_alignment_driver as q8_driver
from multimarket import dev045_m6_event_loop_contract as d1


EXPERIMENT_ID = "DEV045-D6R21"
DESIGN_VERSION = "canonical-historical-economic-runner-q8-terminal-grid-aligned-v1"

PARENT_FREEZE_HEAD = "fc7733a776cff8fc726be630dae4d389abd00e8c"
Q8_EXECUTION_HEAD = "bc6b66fdf2634cdacf04f2738722b36a9f1619d8"
Q8_RESULT_SHA256 = (
    "a1997947b378a851d48016a79715480955233ccfe040bba7348b697e578a2641"
)
Q8_RESULT_BYTES = 41_178
Q8_DRIVER_BLOB = "1302016fbb433511a1a874eea1c913988283efeb"
Q8_RESULT_GIT_BLOB = "fdffff1dd771365bb323468c79cd30ae52129372"
Q8_FREEZE_METADATA_GIT_BLOB = "c7584948389b048fbbca229efa2ec19e1d1d6411"
D6R19_RUNNER_BLOB = "9b714066955ddbd637c4d3dd5f94eccbd257cb2c"

AUTHORIZATION_ENV = "DEV045_D6R21_AUTHORIZE"
AUTHORIZATION_TOKEN = (
    "YES_JAN_JUL_M6_MAKER_ECONOMIC_ARENA_D6R21_Q8_ONE_SHOT"
)

BOUNDARY_SEMANTIC = d6r19.BOUNDARY_SEMANTIC
DAY_ORDER = tuple(d6r19.DAY_ORDER)
POLICY_ORDER = tuple(d6r19.POLICY_ORDER)
SCENARIO_ORDER = tuple(d6r19.SCENARIO_ORDER)
REPLAY_ORDER = tuple(d6r19.REPLAY_ORDER)

EXPECTED_DAY_COUNT = d6r19.EXPECTED_DAY_COUNT
EXPECTED_REPLAYS_PER_DAY = d6r19.EXPECTED_REPLAYS_PER_DAY
EXPECTED_TOTAL_REPLAYS = d6r19.EXPECTED_TOTAL_REPLAYS

HISTORICAL_KERNEL = (
    q8_driver.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel
)
Q8_REPLAY_VALIDATOR = q8q._validate_completed_replay

CANONICAL_SOURCE_OPEN_IMPLEMENTED = True
CANONICAL_DAY_MATRIX_IMPLEMENTED = True
FINAL_112_ARENA_IMPLEMENTED = True
Q8_TERMINAL_ALIGNMENT_SEMANTICS = True
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

REAL_HISTORICAL_EXECUTION_DURING_IMPLEMENTATION = False
HISTORICAL_SOURCE_OPENED_DURING_IMPLEMENTATION = False
HISTORICAL_SOURCE_HASHED_DURING_IMPLEMENTATION = False
ECONOMIC_ARENA_EXECUTED_DURING_IMPLEMENTATION = False
Q8_HISTORICAL_RERUN_DURING_IMPLEMENTATION = False
Q7_HISTORICAL_RERUN_DURING_IMPLEMENTATION = False
Q6_HISTORICAL_RERUN_DURING_IMPLEMENTATION = False

JSON_NORMALIZATION_BEFORE_SUCCESS_WRITE = True
RAW_PAYLOAD_SAVED_ASSERTION_ALLOWED = False
POST_WRITE_SEMANTIC_ASSERTIONS_ALLOWED = False

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
Q8_DRIVER_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q8_terminal_shutdown_grid_alignment_driver.py"
)
Q8_RESULT_PATH = (
    REPOSITORY_ROOT
    / "evidence/dev045_d6r20_q8_real_engine_qualification_result.json"
)
Q8_FREEZE_METADATA_PATH = (
    REPOSITORY_ROOT
    / "evidence/dev045_d6r20_q8_real_engine_qualification_freeze.json"
)
D6R19_RUNNER_PATH = (
    REPOSITORY_ROOT / "src/multimarket/dev045_d6r19_canonical_runner.py"
)

RESULT_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/"
    "dev045_d6r21_canonical_economic_run_v1"
)
FINAL_RESULT_PATH = (
    RESULT_ROOT / "DEV045_D6R21_CANONICAL_ECONOMIC_RESULT.json"
)
FAILURE_RESULT_PATH = RESULT_ROOT / "DEV045_D6R21_CANONICAL_FAILURE.json"

CanonicalRunnerError = frozen.CanonicalRunnerError
DayMatrixResult = frozen.DayMatrixResult
extract_fill_records = frozen.extract_fill_records
verify_reaccount_parity = frozen.verify_reaccount_parity

adapter = d6r19.adapter
bridge = d6r19.bridge
support = d6r19.support
base = d6r19.base
parent = d6r19.parent
m6 = d6r19.m6


@dataclass(frozen=True)
class CapturedReplay(frozen.CapturedReplay):
    q8_execution_diagnostics: dict[str, object]


def _stream_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _git_blob(path: Path) -> str:
    relative = path.resolve().relative_to(REPOSITORY_ROOT.resolve())
    return subprocess.check_output(
        ["git", "hash-object", str(relative)],
        cwd=REPOSITORY_ROOT,
        text=True,
    ).strip()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_normalize(value):
    return json.loads(json.dumps(value, sort_keys=True))


def validate_q8_frozen_lineage() -> dict:
    if _git_blob(D6R19_RUNNER_PATH) != D6R19_RUNNER_BLOB:
        raise CanonicalRunnerError("d6r19_runner_blob")

    if _git_blob(Q8_DRIVER_PATH) != Q8_DRIVER_BLOB:
        raise CanonicalRunnerError("q8_driver_blob")

    if _git_blob(Q8_RESULT_PATH) != Q8_RESULT_GIT_BLOB:
        raise CanonicalRunnerError("q8_result_git_blob")

    if _git_blob(Q8_FREEZE_METADATA_PATH) != Q8_FREEZE_METADATA_GIT_BLOB:
        raise CanonicalRunnerError("q8_freeze_metadata_git_blob")

    if Q8_RESULT_PATH.stat().st_size != Q8_RESULT_BYTES:
        raise CanonicalRunnerError("q8_result_bytes")

    observed_sha = _stream_sha256(Q8_RESULT_PATH)

    if observed_sha != Q8_RESULT_SHA256:
        raise CanonicalRunnerError("q8_result_sha256")

    result = _load_json(Q8_RESULT_PATH)
    freeze_meta = _load_json(Q8_FREEZE_METADATA_PATH)

    if result.get("experiment_id") != "DEV045-D6R20-Q8":
        raise CanonicalRunnerError("q8_result_experiment")

    if result.get("status") != "REAL_ENGINE_QUALIFICATION_PASS":
        raise CanonicalRunnerError("q8_result_status")

    if result.get("head") != Q8_EXECUTION_HEAD:
        raise CanonicalRunnerError("q8_execution_head")

    if int(result.get("replay_count", -1)) != 20:
        raise CanonicalRunnerError("q8_replay_count")

    replays = tuple(result.get("replays", ()))

    if len(replays) != 20:
        raise CanonicalRunnerError("q8_replay_payload_count")

    if not all(item.get("terminal_lead_preserved") is True for item in replays):
        raise CanonicalRunnerError("q8_terminal_lead")

    if not all(
        item.get("inventory_clock_matches_terminal_position") is True
        for item in replays
    ):
        raise CanonicalRunnerError("q8_inventory_clock")

    if freeze_meta.get("freeze_status") != (
        "REAL_ENGINE_QUALIFICATION_PASS_FROZEN"
    ):
        raise CanonicalRunnerError("q8_freeze_status")

    if freeze_meta.get("execution_head") != Q8_EXECUTION_HEAD:
        raise CanonicalRunnerError("q8_freeze_execution_head")

    if freeze_meta.get("result_artifact_sha256") != Q8_RESULT_SHA256:
        raise CanonicalRunnerError("q8_freeze_result_sha256")

    if int(freeze_meta.get("result_artifact_bytes", -1)) != Q8_RESULT_BYTES:
        raise CanonicalRunnerError("q8_freeze_result_bytes")

    if freeze_meta.get("q8_rerun_authorized") is not False:
        raise CanonicalRunnerError("q8_rerun_guard")

    if freeze_meta.get("economic_arena_called") is not False:
        raise CanonicalRunnerError("q8_economic_guard")

    return {
        "result_status": result["status"],
        "result_sha256": observed_sha,
        "result_bytes": Q8_RESULT_BYTES,
        "execution_head": result["head"],
        "replay_count": len(replays),
        "all_terminal_leads_preserved": True,
        "all_inventory_clocks_match_terminal_position": True,
    }


def validate_runner_contract() -> None:
    d6r19.validate_runner_contract()
    lineage = validate_q8_frozen_lineage()

    if DAY_ORDER != tuple(d6r19.DAY_ORDER):
        raise CanonicalRunnerError("day_order")

    if POLICY_ORDER != tuple(d6r19.POLICY_ORDER):
        raise CanonicalRunnerError("policy_order")

    if SCENARIO_ORDER != tuple(d6r19.SCENARIO_ORDER):
        raise CanonicalRunnerError("scenario_order")

    if REPLAY_ORDER != tuple(d6r19.REPLAY_ORDER):
        raise CanonicalRunnerError("replay_order")

    if len(REPLAY_ORDER) != EXPECTED_TOTAL_REPLAYS:
        raise CanonicalRunnerError("replay_count")

    if HISTORICAL_KERNEL is not (
        q8_driver.TerminalShutdownGridAlignedContinuousHistoricalPolicyKernel
    ):
        raise CanonicalRunnerError("q8_kernel_binding")

    if Q8_REPLAY_VALIDATOR is not q8q._validate_completed_replay:
        raise CanonicalRunnerError("q8_validator_binding")

    forbidden = (
        d6r19_driver.ResponseBatchCoherentFreshReplacementContinuousHistoricalPolicyKernel,
        d6r18_driver.FreshReplacementContinuousHistoricalPolicyKernel,
        bridge.DirectActionContinuousHistoricalPolicyKernel,
        q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel,
    )

    if HISTORICAL_KERNEL in forbidden:
        raise CanonicalRunnerError("prior_kernel_forbidden")

    if not issubclass(
        HISTORICAL_KERNEL,
        q6_driver.InitialBookReadinessContinuousHistoricalPolicyKernel,
    ):
        raise CanonicalRunnerError("q8_q6_lineage")

    if lineage["replay_count"] != 20:
        raise CanonicalRunnerError("q8_frozen_lineage_replay_count")

    if not JSON_NORMALIZATION_BEFORE_SUCCESS_WRITE:
        raise CanonicalRunnerError("json_normalization_disabled")

    if RAW_PAYLOAD_SAVED_ASSERTION_ALLOWED:
        raise CanonicalRunnerError("raw_payload_saved_assertion_enabled")

    if POST_WRITE_SEMANTIC_ASSERTIONS_ALLOWED:
        raise CanonicalRunnerError("post_write_semantic_assertions_enabled")


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


def _spec_for_day(day: str):
    return d6r19._spec_for_day(day)


def validate_canonical_verified_source(source, *, day: str):
    return d6r19.validate_canonical_verified_source(source, day=day)


def open_verified_day_source(
    *,
    day: str,
    authorization_token: str,
    execution_gate: bool,
):
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    validate_q8_frozen_lineage()
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


def load_frozen_day_support(*, day: str):
    return d6r19.load_frozen_day_support(day=day)


def _hftbacktest_module():
    return d6r19._hftbacktest_module()


def _validate_q8_execution_state(*, bt, kernel, replay) -> dict[str, object]:
    diagnostics = Q8_REPLAY_VALIDATOR(
        bt=bt,
        kernel=kernel,
        replay=replay,
    )
    payload = asdict(diagnostics)

    raw = int(payload["raw_terminal_shutdown_cutoff_ns"])
    aligned = int(payload["aligned_terminal_shutdown_cutoff_ns"])
    shift = int(payload["cutoff_alignment_shift_ns"])
    lead = int(payload["frozen_terminal_shutdown_lead_ns"])
    start = int(payload["actual_terminal_shutdown_start_ns"])
    remaining = int(payload["remaining_ns_at_shutdown_start"])

    if aligned > raw:
        raise CanonicalRunnerError("aligned_terminal_cutoff_after_raw")

    if shift != raw - aligned:
        raise CanonicalRunnerError("terminal_cutoff_shift_parity")

    if shift < 0 or shift >= int(d1.BASE_MAKER_STEP_NS):
        raise CanonicalRunnerError("terminal_cutoff_shift_range")

    if int(kernel.terminal_shutdown_cutoff_ns) != aligned:
        raise CanonicalRunnerError("terminal_cutoff_not_aligned")

    if int(kernel.terminal_source_local_ns) - raw != lead:
        raise CanonicalRunnerError("raw_terminal_lead")

    if start > raw:
        raise CanonicalRunnerError("terminal_shutdown_started_after_raw_cutoff")

    if remaining < lead:
        raise CanonicalRunnerError("terminal_shutdown_lead_not_preserved")

    simulator_position = float(bt.position(0))
    clock_position = float(kernel.inventory_clock.position)

    if not math.isclose(
        simulator_position,
        clock_position,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise CanonicalRunnerError("terminal_inventory_clock_mismatch")

    if abs(clock_position) > 1e-12:
        raise CanonicalRunnerError("terminal_inventory_clock_nonflat")

    if kernel.inventory_clock.nonzero_since_local_ns is not None:
        raise CanonicalRunnerError("terminal_inventory_clock_nonzero_since")

    return payload


def run_bound_verified_replay_with_fills(
    source,
    *,
    policy_id: str,
    day: str,
    scenario: str,
    direct_index=None,
) -> CapturedReplay:
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
    fills = ()
    diagnostics = None
    direct_action_queries = 0
    direct_action_rows_found = 0
    direct_action_missing_rows = 0
    direct_action_explicit_abstains = 0
    primary_exception: BaseException | None = None

    try:
        terminal_source_local_ns = int(source.data[-1]["local_ts"])
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

        if (
            replay.day,
            replay.policy_id,
            replay.scenario,
        ) != (day, policy_id, scenario):
            raise CanonicalRunnerError("replay_identity")

        diagnostics = _validate_q8_execution_state(
            bt=bt,
            kernel=kernel,
            replay=replay,
        )

        fills = extract_fill_records(tuple(kernel.bound_fills))
        direct_action_queries = int(kernel.direct_action_queries)
        direct_action_rows_found = int(kernel.direct_action_rows_found)
        direct_action_missing_rows = int(kernel.direct_action_missing_rows)
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
                raise CanonicalRunnerError(f"backtest_close_rc:{rc}")

    if replay is None or diagnostics is None:
        raise CanonicalRunnerError("replay_capture_missing")

    return CapturedReplay(
        replay=replay,
        fills=tuple(fills),
        direct_action_queries=direct_action_queries,
        direct_action_rows_found=direct_action_rows_found,
        direct_action_missing_rows=direct_action_missing_rows,
        direct_action_explicit_abstains=direct_action_explicit_abstains,
        q8_execution_diagnostics=diagnostics,
    )


def run_verified_day_matrix_with_boundary(
    source,
    *,
    day: str,
    direct_by_policy: Mapping[str, support.DirectActionIndex],
    authorization_token: str,
    execution_gate: bool,
    mark_attempt_started,
) -> DayMatrixResult:
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
                raise CanonicalRunnerError("execution_integrity_failure")

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
    mark_attempt_started,
) -> DayMatrixResult:
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


def _replay_payload(captured: CapturedReplay) -> dict:
    payload = frozen._replay_payload(captured)
    payload["q8_execution_diagnostics"] = _json_normalize(
        captured.q8_execution_diagnostics
    )
    return payload


def day_evidence_path(day: str) -> Path:
    if day not in DAY_ORDER:
        raise CanonicalRunnerError("day_evidence_day")

    return RESULT_ROOT / f"{day}_DEV045_D6R21_DAY_RESULT.json"


def _write_json_new(path: Path, payload: dict) -> Path:
    normalized = _json_normalize(payload)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(normalized, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise CanonicalRunnerError(f"result_exists:{path.name}") from exc

    return path


def write_day_evidence(result: DayMatrixResult) -> Path:
    return _write_json_new(
        day_evidence_path(result.day),
        {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": "dev045-d6r21-canonical-day-result-v1",
            "status": "DAY_COMPLETE",
            "day": result.day,
            "replay_count": len(result.replays),
            "q8_terminal_alignment_semantics": True,
            "response_batch_coherent_replacement": True,
            "fresh_replacement_semantics": True,
            "replays": [
                _replay_payload(captured)
                for captured in result.replays
            ],
        },
    )


def _flatten_streams(
    days: Sequence[DayMatrixResult],
):
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
    """One-shot D6R21 entrypoint. Never called by development or CI."""
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

        arena = m6.run_economic_arena(
            primary_fills=primary,
            stress_fills=stress,
            audits=audits,
        )

        payload = {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": (
                "dev045-d6r21-canonical-economic-result-v1"
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
            "q8_execution_head": Q8_EXECUTION_HEAD,
            "q8_result_sha256": Q8_RESULT_SHA256,
            "q8_terminal_alignment_semantics": True,
            "response_batch_coherent_replacement": True,
            "fresh_replacement_semantics": True,
            "live_trading_authorized": False,
        }

        normalized_payload = _json_normalize(payload)
        _write_json_new(FINAL_RESULT_PATH, normalized_payload)

        # The immutable success write is the final semantic transition.
        # No post-write assertion or verification is allowed here.
        return normalized_payload

    except Exception as exc:
        # A success artifact must never be downgraded into a failure artifact.
        if FINAL_RESULT_PATH.exists():
            raise

        if not execution_started:
            raise

        failure = _json_normalize(
            {
                "experiment_id": EXPERIMENT_ID,
                "schema_version": "dev045-d6r21-canonical-failure-v1",
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
                "q8_terminal_alignment_semantics": True,
                "response_batch_coherent_replacement": True,
                "fresh_replacement_semantics": True,
                "live_trading_authorized": False,
            }
        )
        _write_json_new(FAILURE_RESULT_PATH, failure)
        raise


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_FREEZE_HEAD",
    "Q8_EXECUTION_HEAD",
    "Q8_RESULT_SHA256",
    "Q8_RESULT_BYTES",
    "Q8_DRIVER_BLOB",
    "Q8_RESULT_GIT_BLOB",
    "Q8_FREEZE_METADATA_GIT_BLOB",
    "D6R19_RUNNER_BLOB",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "BOUNDARY_SEMANTIC",
    "DAY_ORDER",
    "POLICY_ORDER",
    "SCENARIO_ORDER",
    "REPLAY_ORDER",
    "EXPECTED_TOTAL_REPLAYS",
    "HISTORICAL_KERNEL",
    "Q8_REPLAY_VALIDATOR",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "AUTOMATIC_RETRY",
    "RERUN_AFTER_ATTEMPT_CONSUMPTION",
    "TUNING_AFTER_FIRST_OUTPUT",
    "CapturedReplay",
    "DayMatrixResult",
    "validate_q8_frozen_lineage",
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
    "_json_normalize",
    "run_full_canonical_arena",
]

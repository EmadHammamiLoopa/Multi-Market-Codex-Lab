from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

from multimarket import dev045_d6r21_canonical_runner as d6r21
from multimarket import dev045_d6r23_ulp_aware_flatten_cash_conservation as d6r23


EXPERIMENT_ID = "DEV045-D6R24"
DESIGN_VERSION = "canonical-historical-economic-runner-q8-d6r23-ulp-aware-v1"

PARENT_Q1_FREEZE_HEAD = "a62518c15fe08bc028771ef016abb88eebb91130"
D6R23_IMPLEMENTATION_HEAD = "a73884294249f77b405f9b0620405f9ed9e3b2fb"
D6R23_FIX_BLOB = "4cd849bbb2bab29f31fb9f6ed6913d37cff255c1"
D6R23_Q1_FREEZE_BLOB = "375fab8044792d8452bacbbdb36a205ed1a6c686"
D6R23_Q1_FAILURE_BLOB = "eb4787e3c9c61af5ed99b4464fdb87361002e2ab"
D6R23_Q1_FAILURE_SHA256 = (
    "5988a574f17fcc3f860a7edd1553a7705279807e52c6e7b5071e1f3b57ce4c5a"
)
D6R21_RUNNER_BLOB = "fb641c27820445c4d9f695f80ab51b37ce8f7454"

AUTHORIZATION_ENV = "DEV045_D6R24_AUTHORIZE"
AUTHORIZATION_TOKEN = (
    "YES_JAN_JUL_M6_MAKER_ECONOMIC_ARENA_D6R24_ULP_AWARE_ONE_SHOT"
)

BOUNDARY_SEMANTIC = d6r21.BOUNDARY_SEMANTIC
DAY_ORDER = tuple(d6r21.DAY_ORDER)
POLICY_ORDER = tuple(d6r21.POLICY_ORDER)
SCENARIO_ORDER = tuple(d6r21.SCENARIO_ORDER)
REPLAY_ORDER = tuple(d6r21.REPLAY_ORDER)

EXPECTED_DAY_COUNT = d6r21.EXPECTED_DAY_COUNT
EXPECTED_REPLAYS_PER_DAY = d6r21.EXPECTED_REPLAYS_PER_DAY
EXPECTED_TOTAL_REPLAYS = d6r21.EXPECTED_TOTAL_REPLAYS

HISTORICAL_KERNEL = d6r23.UlpAwareFlattenCashContinuousHistoricalPolicyKernel
Q8_REPLAY_VALIDATOR = d6r21.Q8_REPLAY_VALIDATOR

CANONICAL_SOURCE_OPEN_IMPLEMENTED = True
CANONICAL_DAY_MATRIX_IMPLEMENTED = True
FINAL_112_ARENA_IMPLEMENTED = True
D6R23_ULP_AWARE_BINDING = True
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
D6R23_Q1_RERUN_DURING_IMPLEMENTATION = False
D6R22_RERUN_DURING_IMPLEMENTATION = False
D6R21_RERUN_DURING_IMPLEMENTATION = False
Q8_RERUN_DURING_IMPLEMENTATION = False

JSON_NORMALIZATION_BEFORE_SUCCESS_WRITE = True
POST_WRITE_SEMANTIC_ASSERTIONS_ALLOWED = False
Q1_INVALID_COMPLETED_CYCLE_ATTRIBUTE_ALLOWED = False
CORRECT_CYCLE_COUNT_EXPRESSION = "len(replay.cycles)"

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
D6R23_FIX_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r23_ulp_aware_flatten_cash_conservation.py"
)
D6R23_Q1_FREEZE_PATH = (
    REPOSITORY_ROOT
    / "evidence/dev045_d6r23_q1_post_validation_artifactization_freeze.json"
)
D6R23_Q1_FAILURE_PATH = (
    REPOSITORY_ROOT
    / "evidence/dev045_d6r23_q1_post_validation_artifactization_failure.json"
)
D6R21_RUNNER_PATH = (
    REPOSITORY_ROOT / "src/multimarket/dev045_d6r21_canonical_runner.py"
)

RESULT_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/"
    "dev045_d6r24_canonical_economic_run_v1"
)
FINAL_RESULT_PATH = RESULT_ROOT / "DEV045_D6R24_CANONICAL_ECONOMIC_RESULT.json"
FAILURE_RESULT_PATH = RESULT_ROOT / "DEV045_D6R24_CANONICAL_FAILURE.json"

CanonicalRunnerError = d6r21.CanonicalRunnerError
DayMatrixResult = d6r21.DayMatrixResult
extract_fill_records = d6r21.extract_fill_records
verify_reaccount_parity = d6r21.verify_reaccount_parity

adapter = d6r21.adapter
bridge = d6r21.bridge
support = d6r21.support
base = d6r21.base
m6 = d6r21.m6


@dataclass(frozen=True)
class CapturedReplay(d6r21.CapturedReplay):
    d6r23_cash_guard_diagnostics: tuple[dict[str, object], ...]


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


def validate_d6r23_q1_frozen_lineage() -> dict:
    if _git_blob(D6R23_FIX_PATH) != D6R23_FIX_BLOB:
        raise CanonicalRunnerError("d6r23_fix_blob")
    if _git_blob(D6R23_Q1_FREEZE_PATH) != D6R23_Q1_FREEZE_BLOB:
        raise CanonicalRunnerError("d6r23_q1_freeze_blob")
    if _git_blob(D6R23_Q1_FAILURE_PATH) != D6R23_Q1_FAILURE_BLOB:
        raise CanonicalRunnerError("d6r23_q1_failure_blob")
    if _git_blob(D6R21_RUNNER_PATH) != D6R21_RUNNER_BLOB:
        raise CanonicalRunnerError("d6r21_runner_blob")

    freeze = _load_json(D6R23_Q1_FREEZE_PATH)
    failure = _load_json(D6R23_Q1_FAILURE_PATH)

    if freeze.get("freeze_status") != (
        "CONSUMED_POST_VALIDATION_ARTIFACTIZATION_FAILURE_FROZEN"
    ):
        raise CanonicalRunnerError("d6r23_q1_freeze_status")
    if freeze.get("execution_head") != D6R23_IMPLEMENTATION_HEAD:
        raise CanonicalRunnerError("d6r23_q1_execution_head")
    if freeze.get("failure_artifact_sha256") != D6R23_Q1_FAILURE_SHA256:
        raise CanonicalRunnerError("d6r23_q1_failure_sha")
    if freeze.get("qualification_attempt_consumed") is not True:
        raise CanonicalRunnerError("d6r23_q1_attempt")
    if freeze.get("q1_rerun_authorized") is not False:
        raise CanonicalRunnerError("d6r23_q1_rerun_guard")
    if freeze.get("classification") != (
        "SEMANTIC_QUALIFICATION_PASS_POST_VALIDATION_ARTIFACTIZATION_FAILURE"
    ):
        raise CanonicalRunnerError("d6r23_q1_classification")

    semantic = freeze.get("semantic_qualification", {})
    required_true = (
        "replay_run_full_day_returned",
        "replay_identity_guard_passed_by_control_flow",
        "q8_execution_validation_passed_by_control_flow",
        "reaccount_parity_passed_by_control_flow",
        "ulp_fallback_observed_by_control_flow",
        "execution_integrity_zero_passed_by_control_flow",
        "terminal_flat_passed_by_control_flow",
        "terminal_working_quote_slots_zero_passed_by_control_flow",
        "semantic_qualification_pass",
    )
    if not all(semantic.get(key) is True for key in required_true):
        raise CanonicalRunnerError("d6r23_q1_semantic_qualification")
    if semantic.get("success_artifact_written") is not False:
        raise CanonicalRunnerError("d6r23_q1_artifact_status")

    artifact = freeze.get("artifactization_failure", {})
    if artifact.get("invalid_expression") != "replay.completed_cycle_count":
        raise CanonicalRunnerError("d6r23_q1_invalid_expression")
    if artifact.get("correct_expression") != CORRECT_CYCLE_COUNT_EXPRESSION:
        raise CanonicalRunnerError("d6r23_q1_correct_expression")
    if artifact.get("execution_or_accounting_failure") is not False:
        raise CanonicalRunnerError("d6r23_q1_execution_failure_classification")

    if failure.get("status") != "ULP_AWARE_FLATTEN_CASH_QUALIFICATION_FAILED":
        raise CanonicalRunnerError("d6r23_q1_failure_status")
    if failure.get("exception_type") != "AttributeError":
        raise CanonicalRunnerError("d6r23_q1_exception_type")
    if failure.get("exception_message") != (
        "'ContinuousReplayResult' object has no attribute 'completed_cycle_count'"
    ):
        raise CanonicalRunnerError("d6r23_q1_exception_message")
    if failure.get("economic_arena_called") is not False:
        raise CanonicalRunnerError("d6r23_q1_economic_guard")

    return {
        "freeze_status": freeze["freeze_status"],
        "classification": freeze["classification"],
        "semantic_qualification_pass": True,
        "ulp_fallback_observed": True,
        "correct_cycle_count_expression": artifact["correct_expression"],
        "q1_rerun_authorized": False,
    }


def validate_runner_contract() -> None:
    d6r21.validate_runner_contract()
    lineage = validate_d6r23_q1_frozen_lineage()

    if DAY_ORDER != tuple(d6r21.DAY_ORDER):
        raise CanonicalRunnerError("day_order")
    if POLICY_ORDER != tuple(d6r21.POLICY_ORDER):
        raise CanonicalRunnerError("policy_order")
    if SCENARIO_ORDER != tuple(d6r21.SCENARIO_ORDER):
        raise CanonicalRunnerError("scenario_order")
    if REPLAY_ORDER != tuple(d6r21.REPLAY_ORDER):
        raise CanonicalRunnerError("replay_order")
    if len(REPLAY_ORDER) != EXPECTED_TOTAL_REPLAYS:
        raise CanonicalRunnerError("replay_count")

    if HISTORICAL_KERNEL is not d6r23.UlpAwareFlattenCashContinuousHistoricalPolicyKernel:
        raise CanonicalRunnerError("d6r23_kernel_binding")
    if not issubclass(HISTORICAL_KERNEL, d6r21.HISTORICAL_KERNEL):
        raise CanonicalRunnerError("d6r23_q8_kernel_lineage")
    if Q8_REPLAY_VALIDATOR is not d6r21.Q8_REPLAY_VALIDATOR:
        raise CanonicalRunnerError("q8_validator_binding")

    if d6r23.BINDING_GUARD_CHANGE_SCOPE != "FLATTEN_CASH_CONSERVATION_ONLY":
        raise CanonicalRunnerError("d6r23_fix_scope")
    if d6r23.ULP_MULTIPLIER != 1.0:
        raise CanonicalRunnerError("d6r23_ulp_multiplier")
    if not d6r23.ULP_AWARE_FALLBACK_ENABLED:
        raise CanonicalRunnerError("d6r23_ulp_fallback_disabled")
    if any(
        (
            d6r23.EXECUTION_SEMANTICS_CHANGED,
            d6r23.STRATEGY_SEMANTICS_CHANGED,
            d6r23.FEE_SEMANTICS_CHANGED,
            d6r23.ECONOMIC_ACCOUNTING_CHANGED,
            d6r23.RETRY_SEMANTICS_CHANGED,
            d6r23.AUTOMATIC_RETRY,
            d6r23.LIVE_TRADING_AUTHORIZED,
        )
    ):
        raise CanonicalRunnerError("d6r23_forbidden_semantic_change")

    if lineage["semantic_qualification_pass"] is not True:
        raise CanonicalRunnerError("d6r23_q1_semantic_qualification_missing")
    if lineage["ulp_fallback_observed"] is not True:
        raise CanonicalRunnerError("d6r23_q1_ulp_fallback_missing")
    if Q1_INVALID_COMPLETED_CYCLE_ATTRIBUTE_ALLOWED:
        raise CanonicalRunnerError("q1_invalid_cycle_attribute_allowed")
    if CORRECT_CYCLE_COUNT_EXPRESSION != "len(replay.cycles)":
        raise CanonicalRunnerError("cycle_count_expression")
    if not JSON_NORMALIZATION_BEFORE_SUCCESS_WRITE:
        raise CanonicalRunnerError("json_normalization_disabled")
    if POST_WRITE_SEMANTIC_ASSERTIONS_ALLOWED:
        raise CanonicalRunnerError("post_write_assertions_enabled")


def _require_authorization(*, authorization_token: str, execution_gate: bool) -> None:
    if execution_gate is not True:
        raise CanonicalRunnerError("execution_gate_closed")
    if authorization_token != AUTHORIZATION_TOKEN:
        raise CanonicalRunnerError("authorization_token")
    if os.environ.get(AUTHORIZATION_ENV) != AUTHORIZATION_TOKEN:
        raise CanonicalRunnerError("authorization_environment")


def _spec_for_day(day: str):
    return d6r21._spec_for_day(day)


def validate_canonical_verified_source(source, *, day: str):
    return d6r21.validate_canonical_verified_source(source, day=day)


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
    validate_d6r23_q1_frozen_lineage()
    d6r21.validate_q8_frozen_lineage()
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
    return d6r21.load_frozen_day_support(day=day)


def _hftbacktest_module():
    return d6r21._hftbacktest_module()


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
    q8_diagnostics = None
    cash_guard_diagnostics: list[dict[str, object]] = []
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
            cash_guard_diagnostics=cash_guard_diagnostics,
        )
        replay = kernel.run_full_day()

        if (replay.day, replay.policy_id, replay.scenario) != (
            day,
            policy_id,
            scenario,
        ):
            raise CanonicalRunnerError("replay_identity")

        q8_diagnostics = d6r21._validate_q8_execution_state(
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

    if replay is None or q8_diagnostics is None:
        raise CanonicalRunnerError("replay_capture_missing")

    return CapturedReplay(
        replay=replay,
        fills=tuple(fills),
        direct_action_queries=direct_action_queries,
        direct_action_rows_found=direct_action_rows_found,
        direct_action_missing_rows=direct_action_missing_rows,
        direct_action_explicit_abstains=direct_action_explicit_abstains,
        q8_execution_diagnostics=q8_diagnostics,
        d6r23_cash_guard_diagnostics=tuple(
            _json_normalize(cash_guard_diagnostics)
        ),
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
    bridge._validate_day_mapping(day=day, direct_by_policy=direct_by_policy)
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
    payload = d6r21._replay_payload(captured)
    payload["d6r23_cash_guard_diagnostics"] = _json_normalize(
        captured.d6r23_cash_guard_diagnostics
    )
    payload["d6r23_ulp_fallback_count"] = sum(
        1
        for item in captured.d6r23_cash_guard_diagnostics
        if item.get("accepted_by_ulp_fallback") is True
    )
    return payload


def day_evidence_path(day: str) -> Path:
    if day not in DAY_ORDER:
        raise CanonicalRunnerError("day_evidence_day")
    return RESULT_ROOT / f"{day}_DEV045_D6R24_DAY_RESULT.json"


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
            "schema_version": "dev045-d6r24-canonical-day-result-v1",
            "status": "DAY_COMPLETE",
            "day": result.day,
            "replay_count": len(result.replays),
            "d6r23_ulp_aware_binding": True,
            "q8_terminal_alignment_semantics": True,
            "response_batch_coherent_replacement": True,
            "fresh_replacement_semantics": True,
            "ulp_fallback_count": sum(
                sum(
                    1
                    for item in captured.d6r23_cash_guard_diagnostics
                    if item.get("accepted_by_ulp_fallback") is True
                )
                for captured in result.replays
            ),
            "replays": [_replay_payload(captured) for captured in result.replays],
        },
    )


def _flatten_streams(days: Sequence[DayMatrixResult]):
    return d6r21._flatten_streams(days)


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


def _all_cash_guard_diagnostics(days: Sequence[DayMatrixResult]) -> tuple[dict, ...]:
    return tuple(
        item
        for day in days
        for captured in day.replays
        for item in captured.d6r23_cash_guard_diagnostics
    )


def run_full_canonical_arena(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> dict:
    """One-shot D6R24 canonical 112 replay + one frozen M6 economic arena."""
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

        cash_diagnostics = _all_cash_guard_diagnostics(completed_days)
        ulp_fallbacks = tuple(
            item
            for item in cash_diagnostics
            if item.get("accepted_by_ulp_fallback") is True
        )

        payload = {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": "dev045-d6r24-canonical-economic-result-v1",
            "status": "CANONICAL_112_COMPLETE",
            "replay_count": EXPECTED_TOTAL_REPLAYS,
            "day_count": EXPECTED_DAY_COUNT,
            "audit_count": len(audits),
            "primary_raw_fill_count": len(primary),
            "stress_raw_fill_count": len(stress),
            "ulp_fallback_count": len(ulp_fallbacks),
            "ulp_guard_diagnostic_count": len(cash_diagnostics),
            "arena": arena,
            "attempt_consumed": True,
            "attempt_boundary": BOUNDARY_SEMANTIC,
            "parent_q1_freeze_head": PARENT_Q1_FREEZE_HEAD,
            "d6r23_implementation_head": D6R23_IMPLEMENTATION_HEAD,
            "d6r23_binding_guard_change_scope": d6r23.BINDING_GUARD_CHANGE_SCOPE,
            "d6r23_ulp_multiplier": d6r23.ULP_MULTIPLIER,
            "q8_execution_head": d6r21.Q8_EXECUTION_HEAD,
            "q8_result_sha256": d6r21.Q8_RESULT_SHA256,
            "q8_terminal_alignment_semantics": True,
            "response_batch_coherent_replacement": True,
            "fresh_replacement_semantics": True,
            "live_trading_authorized": False,
        }

        normalized_payload = _json_normalize(payload)
        _write_json_new(FINAL_RESULT_PATH, normalized_payload)
        return normalized_payload

    except Exception as exc:
        if FINAL_RESULT_PATH.exists():
            raise
        if not execution_started:
            raise

        failure = _json_normalize(
            {
                "experiment_id": EXPERIMENT_ID,
                "schema_version": "dev045-d6r24-canonical-failure-v1",
                "status": "CANONICAL_ATTEMPT_FAILED",
                "attempt_consumed": True,
                "attempt_boundary": BOUNDARY_SEMANTIC,
                "completed_days": [result.day for result in completed_days],
                "completed_replays": sum(
                    len(result.replays) for result in completed_days
                ),
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "automatic_retry": False,
                "rerun_forbidden": True,
                "d6r23_ulp_aware_binding": True,
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
    "PARENT_Q1_FREEZE_HEAD",
    "D6R23_IMPLEMENTATION_HEAD",
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
    "CapturedReplay",
    "DayMatrixResult",
    "validate_d6r23_q1_frozen_lineage",
    "validate_runner_contract",
    "open_verified_day_source",
    "load_frozen_day_support",
    "run_bound_verified_replay_with_fills",
    "run_verified_day_matrix_with_boundary",
    "run_canonical_day_from_disk_with_boundary",
    "day_evidence_path",
    "write_day_evidence",
    "run_full_canonical_arena",
]

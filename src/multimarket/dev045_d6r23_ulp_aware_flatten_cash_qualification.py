from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess

from multimarket import dev045_d6r21_canonical_runner as d6r21
from multimarket import dev045_d6r23_ulp_aware_flatten_cash_conservation as fix


EXPERIMENT_ID = "DEV045-D6R23-Q1"
DESIGN_VERSION = "feb01-m01-primary-ulp-aware-flatten-cash-qualification-v1"

PARENT_D6R22_FREEZE_HEAD = "883a4af9ee4ded6319d68a5306412342c1f6e217"
D6R22_FREEZE_BLOB = "08565c12c60aa6cd7e039222ad3fcfa3aa791d03"
D6R22_RESULT_BLOB = "70e22e0d85f6f86b06ea1a13967dc24e7dd53aaa"
D6R22_RESULT_SHA256 = (
    "a8b55ee5fd5decb3a026393baccad54aa24f1d7d92dfb2a9060b4833def4ccae"
)

AUTHORIZATION_ENV = "DEV045_D6R23_Q1_AUTHORIZE"
AUTHORIZATION_TOKEN = "YES_FEB01_M01_PRIMARY_D6R23_ULP_AWARE_ONE_SHOT"

TARGET_DAY = "2026-02-01"
TARGET_POLICY = "M01"
TARGET_SCENARIO = "Q0_PRIMARY_250_250"

QUALIFICATION_AUTHORIZED_BY_DEFAULT = False
QUALIFICATION_ATTEMPT_CONSUMED = False
AUTOMATIC_RETRY = False
RERUN_AFTER_ATTEMPT_CONSUMPTION = False
ECONOMIC_ARENA_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

REAL_HISTORICAL_EXECUTION_DURING_IMPLEMENTATION = False
HISTORICAL_SOURCE_OPENED_DURING_IMPLEMENTATION = False
HISTORICAL_SOURCE_HASHED_DURING_IMPLEMENTATION = False
ECONOMIC_ARENA_EXECUTED_DURING_IMPLEMENTATION = False
D6R22_RERUN_DURING_IMPLEMENTATION = False
D6R21_RERUN_DURING_IMPLEMENTATION = False
Q8_RERUN_DURING_IMPLEMENTATION = False

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
D6R22_FREEZE_PATH = (
    REPOSITORY_ROOT
    / "evidence/dev045_d6r22_flatten_cash_conservation_forensic_freeze.json"
)
D6R22_RESULT_PATH = (
    REPOSITORY_ROOT
    / "evidence/dev045_d6r22_flatten_cash_conservation_forensic_result.json"
)

RESULT_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/"
    "dev045_d6r23_ulp_aware_flatten_cash_qualification_v1"
)
RESULT_PATH = RESULT_ROOT / "DEV045_D6R23_Q1_RESULT.json"
FAILURE_PATH = RESULT_ROOT / "DEV045_D6R23_Q1_FAILURE.json"


class D6R23QualificationError(RuntimeError):
    pass


def _git_blob(path: Path) -> str:
    relative = path.resolve().relative_to(REPOSITORY_ROOT.resolve())
    return subprocess.check_output(
        ["git", "hash-object", str(relative)],
        cwd=REPOSITORY_ROOT,
        text=True,
    ).strip()


def _json_normalize(value):
    return json.loads(json.dumps(value, sort_keys=True))


def _write_json_new(path: Path, payload: dict) -> None:
    normalized = _json_normalize(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(normalized, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise D6R23QualificationError(f"result_exists:{path.name}") from exc


def validate_d6r22_frozen_lineage() -> dict:
    if _git_blob(D6R22_FREEZE_PATH) != D6R22_FREEZE_BLOB:
        raise D6R23QualificationError("d6r22_freeze_blob")
    if _git_blob(D6R22_RESULT_PATH) != D6R22_RESULT_BLOB:
        raise D6R23QualificationError("d6r22_result_blob")

    freeze = json.loads(D6R22_FREEZE_PATH.read_text(encoding="utf-8"))
    result = json.loads(D6R22_RESULT_PATH.read_text(encoding="utf-8"))

    if freeze.get("freeze_status") != "FORENSIC_CAPTURE_COMPLETE_FROZEN":
        raise D6R23QualificationError("d6r22_freeze_status")
    if freeze.get("classification") != fix.D6R22_CLASSIFICATION:
        raise D6R23QualificationError("d6r22_classification")
    if freeze.get("forensic_attempt_consumed") is not True:
        raise D6R23QualificationError("d6r22_attempt_not_consumed")
    if freeze.get("rerun_forbidden") is not True:
        raise D6R23QualificationError("d6r22_rerun_guard")
    if result.get("status") != "FORENSIC_CAPTURE_COMPLETE":
        raise D6R23QualificationError("d6r22_result_status")
    if result.get("original_failure_reproduced") is not True:
        raise D6R23QualificationError("d6r22_failure_reproduction")
    if result.get("original_exception_message") != "flatten_cash_conservation":
        raise D6R23QualificationError("d6r22_exception")

    return {
        "freeze_status": freeze["freeze_status"],
        "classification": freeze["classification"],
        "abs_cash_residual": freeze["abs_cash_residual"],
        "original_effective_tolerance": freeze["original_effective_tolerance"],
        "endpoint_ulp_budget": freeze["endpoint_ulp_budget"],
    }


def validate_contract() -> None:
    lineage = validate_d6r22_frozen_lineage()
    d6r21.validate_q8_frozen_lineage()

    if fix.PARENT_D6R22_FREEZE_HEAD != PARENT_D6R22_FREEZE_HEAD:
        raise D6R23QualificationError("fix_parent")
    if fix.D6R22_RESULT_SHA256 != D6R22_RESULT_SHA256:
        raise D6R23QualificationError("fix_result_sha")
    if fix.BINDING_GUARD_CHANGE_SCOPE != "FLATTEN_CASH_CONSERVATION_ONLY":
        raise D6R23QualificationError("fix_scope")
    if fix.ULP_MULTIPLIER != 1.0:
        raise D6R23QualificationError("ulp_multiplier")
    if fix.EXECUTION_SEMANTICS_CHANGED:
        raise D6R23QualificationError("execution_change")
    if fix.STRATEGY_SEMANTICS_CHANGED:
        raise D6R23QualificationError("strategy_change")
    if fix.FEE_SEMANTICS_CHANGED:
        raise D6R23QualificationError("fee_change")
    if fix.ECONOMIC_ACCOUNTING_CHANGED:
        raise D6R23QualificationError("economic_change")
    if fix.RETRY_SEMANTICS_CHANGED or fix.AUTOMATIC_RETRY:
        raise D6R23QualificationError("retry_change")
    if ECONOMIC_ARENA_AUTHORIZED or LIVE_TRADING_AUTHORIZED:
        raise D6R23QualificationError("forbidden_runtime_surface")

    if not (
        float(lineage["abs_cash_residual"])
        > float(lineage["original_effective_tolerance"])
    ):
        raise D6R23QualificationError("forensic_original_tolerance_relation")
    if not (
        float(lineage["abs_cash_residual"])
        < float(lineage["endpoint_ulp_budget"])
    ):
        raise D6R23QualificationError("forensic_ulp_relation")


def _require_authorization(*, authorization_token: str, execution_gate: bool) -> None:
    if execution_gate is not True:
        raise D6R23QualificationError("execution_gate_closed")
    if authorization_token != AUTHORIZATION_TOKEN:
        raise D6R23QualificationError("authorization_token")
    if os.environ.get(AUTHORIZATION_ENV) != AUTHORIZATION_TOKEN:
        raise D6R23QualificationError("authorization_environment")


def _require_virgin_surface() -> None:
    if RESULT_PATH.exists():
        raise D6R23QualificationError("result_exists")
    if FAILURE_PATH.exists():
        raise D6R23QualificationError("failure_exists")
    if RESULT_ROOT.exists() and any(RESULT_ROOT.iterdir()):
        raise D6R23QualificationError("result_surface_not_virgin")


def run_target_qualification(
    *, authorization_token: str, execution_gate: bool
) -> dict:
    """One-shot Feb-01/M01/PRIMARY qualification. No economics or retry."""
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    validate_contract()
    _require_virgin_surface()

    attempt_started = False
    source = None
    bt = None

    try:
        spec = d6r21._spec_for_day(TARGET_DAY)
        source = d6r21.adapter._open_verified_file(
            spec.path,
            expected_sha256=spec.sha256,
            expected_bytes=spec.bytes,
            expected_rows=spec.rows,
        )
        d6r21.validate_canonical_verified_source(source, day=TARGET_DAY)

        h = d6r21._hftbacktest_module()
        asset = d6r21.base._build_asset_from_verified_source(
            source,
            scenario=TARGET_SCENARIO,
            initial_snapshot=None,
        )
        bt = h.HashMapMarketDepthBacktest([asset])
        cash_diagnostics: list[dict] = []
        kernel = fix.UlpAwareFlattenCashContinuousHistoricalPolicyKernel(
            bt=bt,
            h=h,
            policy_id=TARGET_POLICY,
            day=TARGET_DAY,
            scenario=TARGET_SCENARIO,
            terminal_source_local_ns=int(source.data[-1]["local_ts"]),
            direct_index=None,
            cash_guard_diagnostics=cash_diagnostics,
        )

        attempt_started = True
        replay = kernel.run_full_day()

        if (
            replay.day,
            replay.policy_id,
            replay.scenario,
        ) != (TARGET_DAY, TARGET_POLICY, TARGET_SCENARIO):
            raise D6R23QualificationError("replay_identity")

        q8_diagnostics = d6r21._validate_q8_execution_state(
            bt=bt,
            kernel=kernel,
            replay=replay,
        )

        fills = d6r21.extract_fill_records(tuple(kernel.bound_fills))
        d6r21.verify_reaccount_parity(
            policy_id=TARGET_POLICY,
            day=TARGET_DAY,
            scenario=TARGET_SCENARIO,
            replay_total_fill_count=replay.total_fill_count,
            replay_cycles=replay.cycles,
            fills=fills,
        )

        ulp_accepts = tuple(
            item for item in cash_diagnostics
            if item.get("accepted_by_ulp_fallback") is True
        )
        if not ulp_accepts:
            raise D6R23QualificationError("no_ulp_fallback_observed")

        if replay.audit.execution_integrity_failures != 0:
            raise D6R23QualificationError("execution_integrity_failure")
        if not replay.audit.terminal_flat:
            raise D6R23QualificationError("terminal_not_flat")
        if replay.terminal_working_quote_slots != 0:
            raise D6R23QualificationError("terminal_working_quotes")

        payload = _json_normalize(
            {
                "experiment_id": EXPERIMENT_ID,
                "schema_version": "dev045-d6r23-q1-v1",
                "status": "ULP_AWARE_FLATTEN_CASH_QUALIFICATION_PASS",
                "target": {
                    "day": TARGET_DAY,
                    "policy_id": TARGET_POLICY,
                    "scenario": TARGET_SCENARIO,
                },
                "qualification_attempt_consumed": True,
                "automatic_retry": False,
                "rerun_forbidden": True,
                "economic_arena_called": False,
                "live_trading_authorized": False,
                "execution_semantics_changed": False,
                "strategy_semantics_changed": False,
                "fee_semantics_changed": False,
                "economic_accounting_changed": False,
                "binding_guard_change_scope": fix.BINDING_GUARD_CHANGE_SCOPE,
                "ulp_multiplier": fix.ULP_MULTIPLIER,
                "ulp_fallback_count": len(ulp_accepts),
                "cash_guard_diagnostics": cash_diagnostics,
                "q8_execution_diagnostics": q8_diagnostics,
                "replay": {
                    "total_fill_count": replay.total_fill_count,
                    "maker_fill_count": replay.maker_fill_count,
                    "taker_fill_count": replay.taker_fill_count,
                    "completed_cycle_count": replay.completed_cycle_count,
                    "forced_flatten_count": replay.forced_flatten_count,
                    "terminal_flat": replay.audit.terminal_flat,
                    "execution_integrity_failures": replay.audit.execution_integrity_failures,
                    "terminal_working_quote_slots": replay.terminal_working_quote_slots,
                },
                "reaccount_fill_count": len(fills),
            }
        )
        _write_json_new(RESULT_PATH, payload)
        return payload

    except Exception as exc:
        if RESULT_PATH.exists():
            raise
        if not attempt_started:
            raise
        failure = _json_normalize(
            {
                "experiment_id": EXPERIMENT_ID,
                "status": "ULP_AWARE_FLATTEN_CASH_QUALIFICATION_FAILED",
                "qualification_attempt_consumed": True,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "automatic_retry": False,
                "rerun_forbidden": True,
                "economic_arena_called": False,
                "live_trading_authorized": False,
            }
        )
        _write_json_new(FAILURE_PATH, failure)
        raise
    finally:
        if bt is not None:
            bt.close()
        if source is not None:
            source.close()


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_D6R22_FREEZE_HEAD",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "TARGET_DAY",
    "TARGET_POLICY",
    "TARGET_SCENARIO",
    "QUALIFICATION_AUTHORIZED_BY_DEFAULT",
    "QUALIFICATION_ATTEMPT_CONSUMED",
    "AUTOMATIC_RETRY",
    "RERUN_AFTER_ATTEMPT_CONSUMPTION",
    "ECONOMIC_ARENA_AUTHORIZED",
    "LIVE_TRADING_AUTHORIZED",
    "validate_d6r22_frozen_lineage",
    "validate_contract",
    "run_target_qualification",
]

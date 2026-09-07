from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from multimarket import dev045_d6r21_canonical_runner as d6r21
from multimarket import dev045_d6r22_flatten_cash_conservation_forensic as forensic
from multimarket import dev045_m4_m6_binding as binding


EXPERIMENT_ID = "DEV045-D6R22-FORENSIC"
DESIGN_VERSION = "flatten-cash-conservation-targeted-replay-forensic-v1"

PARENT_FAILURE_FREEZE_HEAD = "cbbbb0572f3408a787272bd06db4bba276500049"
D6R21_FAILURE_FREEZE_BLOB = "d42e121798086e31fff40e10c454e8ebf68f647b"
D6R21_FAILURE_RESULT_BLOB = "7b7cc63ceee2dd0fe8011908da6433918c989bed"
D6R21_FAILURE_SHA256 = (
    "adbbdd39800145121f860ed584641d00e71add896ab5a98defbf8431a914a3c1"
)

AUTHORIZATION_ENV = "DEV045_D6R22_FORENSIC_AUTHORIZE"
AUTHORIZATION_TOKEN = "YES_FEB01_M01_PRIMARY_FLATTEN_CASH_FORENSIC_ONE_SHOT"

TARGET_DAY = forensic.TARGET_DAY
TARGET_POLICY = forensic.TARGET_POLICY
TARGET_SCENARIO = forensic.TARGET_SCENARIO
EXPECTED_ORIGINAL_EXCEPTION = forensic.D6R21_FAILURE_EXCEPTION

FORENSIC_EXECUTION_AUTHORIZED_BY_DEFAULT = False
FORENSIC_ATTEMPT_CONSUMED = False
AUTOMATIC_RETRY = False
RERUN_AFTER_ATTEMPT_CONSUMPTION = False
TOLERANCE_CHANGE_AUTHORIZED = False
BINDING_CHANGE_AUTHORIZED = False
ECONOMIC_ARENA_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
D6R21_FAILURE_FREEZE_PATH = (
    REPOSITORY_ROOT / "evidence/dev045_d6r21_canonical_failure_freeze.json"
)
D6R21_FAILURE_RESULT_PATH = (
    REPOSITORY_ROOT / "evidence/dev045_d6r21_canonical_failure_result.json"
)

RESULT_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/"
    "dev045_d6r22_flatten_cash_conservation_forensic_v1"
)
RESULT_PATH = RESULT_ROOT / "DEV045_D6R22_FORENSIC_RESULT.json"
FAILURE_PATH = RESULT_ROOT / "DEV045_D6R22_FORENSIC_FAILURE.json"


class D6R22ForensicError(RuntimeError):
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
        raise D6R22ForensicError(f"result_exists:{path.name}") from exc


def validate_frozen_failure_lineage() -> dict:
    if _git_blob(D6R21_FAILURE_FREEZE_PATH) != D6R21_FAILURE_FREEZE_BLOB:
        raise D6R22ForensicError("d6r21_failure_freeze_blob")
    if _git_blob(D6R21_FAILURE_RESULT_PATH) != D6R21_FAILURE_RESULT_BLOB:
        raise D6R22ForensicError("d6r21_failure_result_blob")

    freeze = json.loads(D6R21_FAILURE_FREEZE_PATH.read_text(encoding="utf-8"))
    failure = json.loads(D6R21_FAILURE_RESULT_PATH.read_text(encoding="utf-8"))

    if freeze.get("freeze_status") != "CANONICAL_CONSUMED_FAILURE_FROZEN":
        raise D6R22ForensicError("freeze_status")
    if freeze.get("failure_artifact_sha256") != D6R21_FAILURE_SHA256:
        raise D6R22ForensicError("failure_sha")
    if freeze.get("attempt_consumed") is not True:
        raise D6R22ForensicError("d6r21_attempt_not_consumed")
    if freeze.get("completed_replays") != 16:
        raise D6R22ForensicError("completed_replays")
    if freeze.get("exception_message") != EXPECTED_ORIGINAL_EXCEPTION:
        raise D6R22ForensicError("failure_exception")
    if freeze.get("d6r21_rerun_authorized") is not False:
        raise D6R22ForensicError("d6r21_rerun_guard")
    if failure.get("status") != "CANONICAL_ATTEMPT_FAILED":
        raise D6R22ForensicError("failure_status")
    if failure.get("exception_message") != EXPECTED_ORIGINAL_EXCEPTION:
        raise D6R22ForensicError("failure_result_exception")

    return {
        "freeze_status": freeze["freeze_status"],
        "failure_sha256": freeze["failure_artifact_sha256"],
        "completed_replays": freeze["completed_replays"],
        "exception_message": freeze["exception_message"],
        "jan_max_replay_trading_value_ulp": freeze[
            "january_reference_stats"
        ]["max_single_replay_trading_value_ulp"],
    }


def validate_contract() -> None:
    validate_frozen_failure_lineage()
    d6r21.validate_q8_frozen_lineage()

    if TARGET_DAY != "2026-02-01":
        raise D6R22ForensicError("target_day")
    if TARGET_POLICY != "M01":
        raise D6R22ForensicError("target_policy")
    if TARGET_SCENARIO != "Q0_PRIMARY_250_250":
        raise D6R22ForensicError("target_scenario")
    if forensic.EXECUTION_SEMANTICS_CHANGED:
        raise D6R22ForensicError("execution_semantics_changed")
    if forensic.BINDING_SEMANTICS_CHANGED:
        raise D6R22ForensicError("binding_semantics_changed")
    if forensic.TOLERANCE_CHANGED:
        raise D6R22ForensicError("tolerance_changed")
    if forensic.FLATTEN_RETRY_ENABLED:
        raise D6R22ForensicError("flatten_retry_enabled")
    if ECONOMIC_ARENA_AUTHORIZED:
        raise D6R22ForensicError("economics_enabled")
    if LIVE_TRADING_AUTHORIZED:
        raise D6R22ForensicError("live_enabled")


def _require_authorization(*, authorization_token: str, execution_gate: bool) -> None:
    if execution_gate is not True:
        raise D6R22ForensicError("execution_gate_closed")
    if authorization_token != AUTHORIZATION_TOKEN:
        raise D6R22ForensicError("authorization_token")
    if os.environ.get(AUTHORIZATION_ENV) != AUTHORIZATION_TOKEN:
        raise D6R22ForensicError("authorization_environment")


def _require_virgin_surface() -> None:
    if RESULT_PATH.exists():
        raise D6R22ForensicError("result_exists")
    if FAILURE_PATH.exists():
        raise D6R22ForensicError("failure_exists")
    if RESULT_ROOT.exists() and any(RESULT_ROOT.iterdir()):
        raise D6R22ForensicError("result_surface_not_virgin")


def run_target_forensic(
    *, authorization_token: str, execution_gate: bool
) -> dict:
    """One-shot Feb-01/M01/PRIMARY replay. No economic arena and no retry."""
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    validate_contract()
    _require_virgin_surface()

    forensic_attempt_started = False
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
        sink: list[dict] = []
        kernel = forensic.FlattenCashConservationForensicKernel(
            bt=bt,
            h=h,
            policy_id=TARGET_POLICY,
            day=TARGET_DAY,
            scenario=TARGET_SCENARIO,
            terminal_source_local_ns=int(source.data[-1]["local_ts"]),
            direct_index=None,
            forensic_sink=sink,
        )

        forensic_attempt_started = True

        try:
            kernel.run_full_day()
        except binding.M4M6BindingError as exc:
            if str(exc) != EXPECTED_ORIGINAL_EXCEPTION:
                raise
            if len(sink) != 1:
                raise D6R22ForensicError(
                    f"expected_one_cash_failure_record:{len(sink)}"
                ) from exc

            diagnostic = sink[0]
            payload = _json_normalize(
                {
                    "experiment_id": EXPERIMENT_ID,
                    "schema_version": "dev045-d6r22-flatten-cash-forensic-v1",
                    "status": "FORENSIC_CAPTURE_COMPLETE",
                    "target": {
                        "day": TARGET_DAY,
                        "policy_id": TARGET_POLICY,
                        "scenario": TARGET_SCENARIO,
                    },
                    "original_failure_reproduced": True,
                    "original_exception_type": type(exc).__name__,
                    "original_exception_message": str(exc),
                    "forensic_attempt_consumed": True,
                    "automatic_retry": False,
                    "rerun_forbidden": True,
                    "execution_semantics_changed": False,
                    "binding_semantics_changed": False,
                    "tolerance_changed": False,
                    "economic_arena_called": False,
                    "live_trading_authorized": False,
                    "diagnostic": diagnostic,
                }
            )
            _write_json_new(RESULT_PATH, payload)
            return payload

        payload = _json_normalize(
            {
                "experiment_id": EXPERIMENT_ID,
                "status": "TARGET_FAILURE_NOT_REPRODUCED",
                "target": {
                    "day": TARGET_DAY,
                    "policy_id": TARGET_POLICY,
                    "scenario": TARGET_SCENARIO,
                },
                "forensic_attempt_consumed": True,
                "automatic_retry": False,
                "rerun_forbidden": True,
                "economic_arena_called": False,
                "live_trading_authorized": False,
            }
        )
        _write_json_new(RESULT_PATH, payload)
        return payload

    except Exception as exc:
        if RESULT_PATH.exists():
            raise
        if not forensic_attempt_started:
            raise
        failure = _json_normalize(
            {
                "experiment_id": EXPERIMENT_ID,
                "status": "FORENSIC_ATTEMPT_FAILED",
                "forensic_attempt_consumed": True,
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
    "PARENT_FAILURE_FREEZE_HEAD",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "TARGET_DAY",
    "TARGET_POLICY",
    "TARGET_SCENARIO",
    "FORENSIC_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "FORENSIC_ATTEMPT_CONSUMED",
    "AUTOMATIC_RETRY",
    "RERUN_AFTER_ATTEMPT_CONSUMPTION",
    "TOLERANCE_CHANGE_AUTHORIZED",
    "BINDING_CHANGE_AUTHORIZED",
    "ECONOMIC_ARENA_AUTHORIZED",
    "LIVE_TRADING_AUTHORIZED",
    "validate_frozen_failure_lineage",
    "validate_contract",
    "run_target_forensic",
]

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r17_direct_action_driver_bridge as bridge
from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r19_canonical_runner as d6r19_runner
from multimarket import dev045_d6r20_q6_real_engine_qualification as q6
from multimarket import dev045_d6r20_q7_flatten_end_of_data_forensic_driver as driver
from multimarket import dev045_m4_adapter as m4


EXPERIMENT_ID = "DEV045-D6R20-Q7-FORENSIC"
DESIGN_VERSION = "forced-flatten-end-of-data-response-forensic-v1"

PARENT_HEAD = "6f4c5c4f54e16a78446d9442eec38bbfaf912dad"
Q6_FAILURE_SHA256 = (
    "658e58f1352352b0a048aa19dd56fd2dc17e96d1dd56864200e086c20b3463fa"
)
Q6_DRIVER_BLOB = "af5556f6a11f0a86aab16f4d8e7ac1076990d7b1"
Q6_QUALIFICATION_BLOB = "7ddc57d21d8ff89e516d21ecc2b63620e52cdd1e"
Q5_DRIVER_BLOB = "66a82211ad865eae012e6a166e782bcf8a966ff8"
Q4_DRIVER_BLOB = "aa1f9b3bcfd4262b1b1d23a94fd6fae7946830f7"
D6R20_DRIVER_BLOB = "1cae4584788aab29b409bf985168803759d42b1f"
D6R19_DRIVER_BLOB = "5aaf880795f796d5086b3b86a6e7dde0fd7f56ed"
M4_ADAPTER_BLOB = "7f6a321b4512dd1ec1edf94c79416e176ee75e1c"
M4_M6_BINDING_BLOB = "7c0673a60c59772b5c187d90b4037693d120d94b"
M3_POLICY_BLOB = "256644726f8478d2b76105bce97e5f2c536cabf6"
UPSTREAM_COMMIT = "a244a14250b42d97fc305569c93c4117cd5e1dff"
V2_PATCH_SHA256 = (
    "436061c6d4be1ebab8725ffbd842237a46ba7e7e90a20d320278836f199e3c70"
)
HFTBACKTEST_VERSION = "2.4.4"
HFTBACKTEST_BINARY_SHA256 = (
    "5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752"
)

FORENSIC_DAY = "2026-04-01"
FORENSIC_POLICY = "M06"
FORENSIC_SCENARIO = "Q0_STRESS_500_500"
FORENSIC_SCOPE = ((FORENSIC_DAY, FORENSIC_POLICY, FORENSIC_SCENARIO),)

AUTHORIZATION_ENV = "DEV045_D6R20_Q7_FORENSIC_AUTHORIZE"
AUTHORIZATION_TOKEN = (
    "YES_REAL_HFTBACKTEST_FLATTEN_END_OF_DATA_FORENSIC_D6R20_Q7"
)

EXPECTED_BRANCH = (
    "research/dev045-m6-d6r20-q7-flatten-end-of-data-forensic"
)
EXPECTED_REMOTE_REF = f"origin/{EXPECTED_BRANCH}"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
Q6_FAILURE_EVIDENCE_PATH = (
    REPOSITORY_ROOT
    / "evidence/dev045_d6r20_q6_real_engine_qualification_failure.json"
)
Q6_DRIVER_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q6_initial_book_readiness_driver.py"
)
Q6_QUALIFICATION_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q6_real_engine_qualification.py"
)
Q5_DRIVER_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q5_invalid_local_book_driver.py"
)
Q4_DRIVER_PATH = (
    REPOSITORY_ROOT
    / "src/multimarket/dev045_d6r20_q4_scheduler_reconciled_driver.py"
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
    "dev045_d6r20_q7_flatten_end_of_data_forensic_v1"
)
RESULT_PATH = RESULT_ROOT / "DEV045_D6R20_Q7_FORENSIC_RESULT.json"
FAILURE_PATH = RESULT_ROOT / "DEV045_D6R20_Q7_FORENSIC_FAILURE.json"

HISTORICAL_KERNEL = (
    driver.FlattenEndOfDataForensicContinuousHistoricalPolicyKernel
)

FORENSIC_EXECUTION_AUTHORIZED_BY_DEFAULT = False
REAL_HISTORICAL_FORENSIC_EXECUTED = False
Q6_RERUN_AUTHORIZED = False
CANONICAL_RUNNER_IMPLEMENTED = False
CANONICAL_ECONOMIC_ATTEMPT = False
CANONICAL_ATTEMPT_CONSUMED = False
ECONOMIC_ARENA_CALLED = False
STRATEGY_RANKING_PERFORMED = False
AUTOMATIC_RETRY = False
LIVE_TRADING_AUTHORIZED = False


class FlattenEndOfDataForensicError(RuntimeError):
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
    q6_failure_sha256: str
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
        raise FlattenEndOfDataForensicError(
            f"repository_git_command:{args[0]}"
        ) from exc

    return completed.stdout.rstrip("\n")


def _require_authorization(
    *, authorization_token: str, execution_gate: bool
) -> None:
    if execution_gate is not True:
        raise FlattenEndOfDataForensicError("execution_gate_closed")

    if authorization_token != AUTHORIZATION_TOKEN:
        raise FlattenEndOfDataForensicError("authorization_token")

    if os.environ.get(AUTHORIZATION_ENV) != AUTHORIZATION_TOKEN:
        raise FlattenEndOfDataForensicError("authorization_environment")


def _require_virgin_result_surface() -> None:
    if RESULT_PATH.exists():
        raise FlattenEndOfDataForensicError("forensic_result_exists")

    if FAILURE_PATH.exists():
        raise FlattenEndOfDataForensicError("forensic_failure_exists")

    if RESULT_ROOT.exists():
        if not RESULT_ROOT.is_dir():
            raise FlattenEndOfDataForensicError("forensic_root_not_directory")

        if any(RESULT_ROOT.iterdir()):
            raise FlattenEndOfDataForensicError("forensic_surface_not_virgin")


def validate_repository_preflight() -> ForensicRepositoryIdentity:
    branch = _git_output("branch", "--show-current")

    if branch != EXPECTED_BRANCH:
        raise FlattenEndOfDataForensicError(f"repository_branch:{branch}")

    raw_status = _git_output(
        "status", "--porcelain=v1", "--untracked-files=all"
    )
    status = tuple(line for line in raw_status.splitlines() if line)
    allowed = {f"?? {path}" for path in ALLOWED_UNTRACKED_PATHS}
    unexpected = tuple(line for line in status if line not in allowed)

    if unexpected:
        raise FlattenEndOfDataForensicError(
            f"repository_worktree_dirty_or_unexpected:{unexpected[0]}"
        )

    head = _git_output("rev-parse", "HEAD")
    remote_head = _git_output("rev-parse", EXPECTED_REMOTE_REF)

    if len(head) != 40 or len(remote_head) != 40:
        raise FlattenEndOfDataForensicError("repository_head")

    if head != remote_head:
        raise FlattenEndOfDataForensicError(
            f"repository_remote_mismatch:{head}:{remote_head}"
        )

    expected_blobs = (
        (Q6_DRIVER_PATH, Q6_DRIVER_BLOB, "q6_driver_blob"),
        (Q6_QUALIFICATION_PATH, Q6_QUALIFICATION_BLOB, "q6_qualification_blob"),
        (Q5_DRIVER_PATH, Q5_DRIVER_BLOB, "q5_driver_blob"),
        (Q4_DRIVER_PATH, Q4_DRIVER_BLOB, "q4_driver_blob"),
        (D6R20_DRIVER_PATH, D6R20_DRIVER_BLOB, "d6r20_driver_blob"),
        (D6R19_DRIVER_PATH, D6R19_DRIVER_BLOB, "d6r19_driver_blob"),
        (M4_ADAPTER_PATH, M4_ADAPTER_BLOB, "m4_adapter_blob"),
        (M4_M6_BINDING_PATH, M4_M6_BINDING_BLOB, "m4_m6_binding_blob"),
        (M3_POLICY_PATH, M3_POLICY_BLOB, "m3_policy_blob"),
    )

    for path, expected, label in expected_blobs:
        observed = _git_blob(path)

        if observed != expected:
            raise FlattenEndOfDataForensicError(f"{label}:{observed}")

    patch_sha = _sha256(V2_PATCH_PATH)

    if patch_sha != V2_PATCH_SHA256:
        raise FlattenEndOfDataForensicError(f"v2_patch_sha256:{patch_sha}")

    q6_failure_sha = _sha256(Q6_FAILURE_EVIDENCE_PATH)

    if q6_failure_sha != Q6_FAILURE_SHA256:
        raise FlattenEndOfDataForensicError(
            f"q6_failure_sha256:{q6_failure_sha}"
        )

    if D6R20_CANONICAL_RUNNER_PATH.exists():
        raise FlattenEndOfDataForensicError("d6r20_canonical_runner_exists")

    if D6R21_CANONICAL_RUNNER_PATH.exists():
        raise FlattenEndOfDataForensicError("d6r21_canonical_runner_exists")

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
        q6_failure_sha256=q6_failure_sha,
        canonical_runners_absent=True,
        result_surface_virgin=True,
    )


def _hftbacktest_module():
    import hftbacktest as h

    return h


def validate_runtime_identity(h):
    return q6.validate_runtime_identity(h)


def validate_forensic_contract() -> None:
    if FORENSIC_SCOPE != ((
        "2026-04-01", "M06", "Q0_STRESS_500_500"
    ),):
        raise FlattenEndOfDataForensicError("forensic_scope")

    if HISTORICAL_KERNEL is not (
        driver.FlattenEndOfDataForensicContinuousHistoricalPolicyKernel
    ):
        raise FlattenEndOfDataForensicError("q7_kernel_binding")

    if not issubclass(HISTORICAL_KERNEL, q6.HISTORICAL_KERNEL):
        raise FlattenEndOfDataForensicError("q6_kernel_lineage")

    if driver.ELAPSE_RESULT_END_OF_DATA_RC != 1:
        raise FlattenEndOfDataForensicError("end_of_data_rc")

    if driver.BACKTEST_ERROR_ORDER_ID_EXIST_RC != 10:
        raise FlattenEndOfDataForensicError("order_id_exist_rc")

    if _sha256(Q6_FAILURE_EVIDENCE_PATH) != Q6_FAILURE_SHA256:
        raise FlattenEndOfDataForensicError("q6_failure_sha256")


def open_verified_forensic_source(
    *, authorization_token: str, execution_gate: bool
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
            source, day=FORENSIC_DAY
        )
    except Exception:
        source.close()
        raise

    return source


def load_forensic_support():
    support_by_policy = q6.load_qualification_support(day=FORENSIC_DAY)

    if tuple(support_by_policy) != ("M06", "M07"):
        raise FlattenEndOfDataForensicError("april_support_mapping")

    return support_by_policy[FORENSIC_POLICY]


def run_bound_forensic_replay(
    source: adapter.CanonicalJanMemmap,
    *,
    direct_index,
    forensic_sink: list[dict],
    eod_failure_sink: list[dict],
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
            eod_failure_sink=eod_failure_sink,
        )
        kernel.run_full_day()
        raise FlattenEndOfDataForensicError("flatten_rc_1_not_observed")
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
                raise FlattenEndOfDataForensicError(
                    f"backtest_close_rc:{rc}"
                )


def _write_json_new(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise FlattenEndOfDataForensicError(
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
            "upstream_commit": UPSTREAM_COMMIT,
            "v2_patch_sha256": V2_PATCH_SHA256,
        },
        "q6_failure_sha256": Q6_FAILURE_SHA256,
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


def run_flatten_end_of_data_forensic(
    *, authorization_token: str, execution_gate: bool
) -> dict:
    """Run the one authorized Q7 replay and preserve flatten_rc:1."""
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )
    repository = validate_repository_preflight()
    runtime = validate_runtime_identity(_hftbacktest_module())
    validate_forensic_contract()
    direct_index = load_forensic_support()
    forensic_sink: list[dict] = []
    eod_failure_sink: list[dict] = []

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
                    eod_failure_sink=eod_failure_sink,
                )
            except m4.M4AdapterError as exc:
                if str(exc) != "flatten_rc:1":
                    raise

                if len(eod_failure_sink) != 1:
                    raise FlattenEndOfDataForensicError(
                        "flatten_eod_snapshot_count"
                    ) from exc

                after = base._stat_identity(source.path)

                if before != after:
                    raise FlattenEndOfDataForensicError(
                        "source_identity_changed"
                    ) from exc

                diagnostic = eod_failure_sink[0]
                payload = {
                    **_common_payload(repository=repository, runtime=runtime),
                    "schema_version": "dev045-d6r20-q7-forensic-result-v1",
                    "status": "FLATTEN_END_OF_DATA_FORENSIC_CAPTURED",
                    "original_exception_type": type(exc).__name__,
                    "original_exception_message": str(exc),
                    "forensic_classification": diagnostic[
                        "forensic_classification"
                    ],
                    "flatten_end_of_data": diagnostic,
                    "all_flatten_attempts": forensic_sink,
                    "flatten_attempt_count": len(forensic_sink),
                    "flatten_eod_failure_count": 1,
                    "source_identity_unchanged": True,
                    "replay_continued_after_failure": False,
                    "retry_performed": False,
                    "rc_1_is_order_id_collision": False,
                }
                _write_json_new(RESULT_PATH, payload)
                raise

            raise FlattenEndOfDataForensicError(
                "forensic_replay_returned_without_failure"
            )

    except m4.M4AdapterError as exc:
        if str(exc) == "flatten_rc:1" and len(eod_failure_sink) == 1:
            raise
        failure = {
            **_common_payload(repository=repository, runtime=runtime),
            "schema_version": "dev045-d6r20-q7-forensic-failure-v1",
            "status": "FLATTEN_END_OF_DATA_FORENSIC_FAILED",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "flatten_attempt_count": len(forensic_sink),
            "flatten_eod_failure_count": len(eod_failure_sink),
        }
        _write_json_new(FAILURE_PATH, failure)
        raise
    except Exception as exc:
        failure = {
            **_common_payload(repository=repository, runtime=runtime),
            "schema_version": "dev045-d6r20-q7-forensic-failure-v1",
            "status": "FLATTEN_END_OF_DATA_FORENSIC_FAILED",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "flatten_attempt_count": len(forensic_sink),
            "flatten_eod_failure_count": len(eod_failure_sink),
        }
        _write_json_new(FAILURE_PATH, failure)
        raise


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_HEAD",
    "Q6_FAILURE_SHA256",
    "UPSTREAM_COMMIT",
    "V2_PATCH_SHA256",
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
    "Q6_RERUN_AUTHORIZED",
    "CANONICAL_RUNNER_IMPLEMENTED",
    "CANONICAL_ECONOMIC_ATTEMPT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "ECONOMIC_ARENA_CALLED",
    "STRATEGY_RANKING_PERFORMED",
    "AUTOMATIC_RETRY",
    "LIVE_TRADING_AUTHORIZED",
    "FlattenEndOfDataForensicError",
    "ForensicRepositoryIdentity",
    "validate_repository_preflight",
    "validate_runtime_identity",
    "validate_forensic_contract",
    "open_verified_forensic_source",
    "load_forensic_support",
    "run_bound_forensic_replay",
    "run_flatten_end_of_data_forensic",
]

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Callable, Mapping, Sequence

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_d6r6_historical_driver as d6r6
from multimarket import dev045_d6r17_canonical_runner as d6r17
from multimarket import dev045_d6r17_canonical_runner_contract as contract
from multimarket import dev045_d6r17_direct_action_driver_bridge as bridge
from multimarket import dev045_d6r17_direct_action_support as support
from multimarket import dev045_d6r17_real_historical_economic_driver as base
from multimarket import dev045_d6r17_real_historical_economic_driver_contract as parent
from multimarket import dev045_d6r18_fresh_replacement_driver as fresh
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_economic_arena as m6


EXPERIMENT_ID = "DEV045-D6R18"
DESIGN_VERSION = "canonical-historical-economic-runner-v1"

PARENT_HEAD = "25204113272f68d4e09fcee39b560145196ecc1d"
FRESH_REPLACEMENT_DRIVER_BLOB = (
    "adc432f36814a1ccf1b2dd63219f5826c604753e"
)

AUTHORIZATION_ENV = "DEV045_D6R18_AUTHORIZE"
AUTHORIZATION_TOKEN = (
    "YES_JAN_JUL_M6_MAKER_ECONOMIC_ARENA_D6R18_ONE_SHOT"
)

BOUNDARY_SEMANTIC = (
    "ATTEMPT_STARTS_IMMEDIATELY_BEFORE_FIRST_"
    "RUN_BOUND_VERIFIED_HISTORICAL_REPLAY"
)

DAY_ORDER = tuple(contract.DAY_ORDER)
POLICY_ORDER = tuple(contract.POLICY_ORDER)
SCENARIO_ORDER = tuple(contract.SCENARIO_ORDER)
REPLAY_ORDER = tuple(
    (day, policy_id, scenario)
    for day in DAY_ORDER
    for policy_id in POLICY_ORDER
    for scenario in SCENARIO_ORDER
)

EXPECTED_DAY_COUNT = 7
EXPECTED_REPLAYS_PER_DAY = 16
EXPECTED_TOTAL_REPLAYS = 112

CANONICAL_SOURCE_OPEN_IMPLEMENTED = True
CANONICAL_DAY_MATRIX_IMPLEMENTED = True
FINAL_112_ARENA_IMPLEMENTED = True
FRESH_REPLACEMENT_SEMANTICS = True

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
    "dev045_d6r18_canonical_economic_run_v1"
)
FINAL_RESULT_PATH = (
    RESULT_ROOT
    / "DEV045_D6R18_CANONICAL_ECONOMIC_RESULT.json"
)
FAILURE_RESULT_PATH = (
    RESULT_ROOT
    / "DEV045_D6R18_CANONICAL_FAILURE.json"
)


class CanonicalRunnerError(RuntimeError):
    pass


@dataclass(frozen=True)
class CapturedReplay:
    replay: base.ContinuousReplayResult
    fills: tuple[m6.FillRecord, ...]

    direct_action_queries: int
    direct_action_rows_found: int
    direct_action_missing_rows: int
    direct_action_explicit_abstains: int

    def __post_init__(self) -> None:
        if len(self.fills) != int(self.replay.total_fill_count):
            raise CanonicalRunnerError("raw_fill_count_parity")

        if (
            int(self.direct_action_rows_found)
            + int(self.direct_action_missing_rows)
            != int(self.direct_action_queries)
        ):
            raise CanonicalRunnerError("support_counter_identity")


@dataclass(frozen=True)
class DayMatrixResult:
    day: str
    replays: tuple[CapturedReplay, ...]

    def __post_init__(self) -> None:
        if self.day not in DAY_ORDER:
            raise CanonicalRunnerError("day_identity")

        if len(self.replays) != EXPECTED_REPLAYS_PER_DAY:
            raise CanonicalRunnerError("day_matrix_count")

        observed = tuple(
            (
                captured.replay.day,
                captured.replay.policy_id,
                captured.replay.scenario,
            )
            for captured in self.replays
        )
        expected = tuple(
            item
            for item in REPLAY_ORDER
            if item[0] == self.day
        )

        if observed != expected:
            raise CanonicalRunnerError("day_matrix_order")


def validate_runner_contract() -> None:
    contract.validate_contract()
    parent.validate_contract()

    if DAY_ORDER != (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    ):
        raise CanonicalRunnerError("day_order")

    if POLICY_ORDER != (
        "M01",
        "M02",
        "M03",
        "M04",
        "M05",
        "M06",
        "M07",
        "M08",
    ):
        raise CanonicalRunnerError("policy_order")

    if SCENARIO_ORDER != (
        "Q0_PRIMARY_250_250",
        "Q0_STRESS_500_500",
    ):
        raise CanonicalRunnerError("scenario_order")

    if len(REPLAY_ORDER) != EXPECTED_TOTAL_REPLAYS:
        raise CanonicalRunnerError("replay_count")

    if tuple(m6.POLICY_IDS) != POLICY_ORDER:
        raise CanonicalRunnerError("m6_policy_identity")

    if tuple(m6.AUTHORIZED_DAYS) != DAY_ORDER:
        raise CanonicalRunnerError("m6_day_identity")

    if tuple(m6.SCENARIOS) != SCENARIO_ORDER:
        raise CanonicalRunnerError("m6_scenario_identity")


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
    """Reuse the frozen D6R17 source specs and June SHA amendment."""
    return d6r17._spec_for_day(day)


def validate_canonical_verified_source(
    source: adapter.CanonicalJanMemmap,
    *,
    day: str,
) -> parent.DaySourceSpec:
    """Validate an already-open source against the amended day identity."""
    spec = _spec_for_day(day)
    d6r6._validate_verified_source(source)

    if Path(source.path) != spec.path:
        raise CanonicalRunnerError("canonical_source_path")

    if source.sha256 != spec.sha256:
        raise CanonicalRunnerError("canonical_source_sha256")

    if len(source.data) != spec.rows:
        raise CanonicalRunnerError("canonical_source_rows")

    if int(source.path.stat().st_size) != spec.bytes:
        raise CanonicalRunnerError("canonical_source_bytes")

    return spec


def open_verified_day_source(
    *,
    day: str,
    authorization_token: str,
    execution_gate: bool,
) -> adapter.CanonicalJanMemmap:
    """Authorize before the actual full-SHA/read-only-memmap opener."""
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
    if day in support.BASE_ONLY_DAYS:
        return {}

    if day not in support.DIRECT_SUPPORT_DAYS:
        raise CanonicalRunnerError("support_day")

    return {
        "M06": support.load_verified_day(
            day=day,
            policy_id="M06",
        ),
        "M07": support.load_verified_day(
            day=day,
            policy_id="M07",
        ),
    }


def extract_fill_records(
    events: Sequence[binding.BoundReplayEvent],
) -> tuple[m6.FillRecord, ...]:
    fills = []

    for event in events:
        if event.kind != binding.FILL:
            continue

        if event.fill is None:
            raise CanonicalRunnerError("fill_event_without_record")

        fills.append(event.fill)

    return tuple(fills)


def verify_reaccount_parity(
    *,
    policy_id: str,
    day: str,
    scenario: str,
    replay_total_fill_count: int,
    replay_cycles: Sequence[m6.CycleRecord],
    fills: Sequence[m6.FillRecord],
) -> tuple[m6.CycleRecord, ...]:
    if len(fills) != int(replay_total_fill_count):
        raise CanonicalRunnerError("raw_fill_count_parity")

    for fill in fills:
        if fill.policy_id != policy_id:
            raise CanonicalRunnerError("fill_policy")

        if fill.day != day:
            raise CanonicalRunnerError("fill_day")

    recomputed = tuple(
        m6.account_fill_bucket(
            tuple(fills),
            scenario=scenario,
        )
    )

    if recomputed != tuple(replay_cycles):
        raise CanonicalRunnerError("reaccount_cycle_parity")

    return recomputed


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
    """Run D6R18 and capture exact raw M6 fills before backtest close."""
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

        kernel = fresh.FreshReplacementContinuousHistoricalPolicyKernel(
            bt=bt,
            h=h,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            terminal_source_local_ns=terminal_source_local_ns,
            direct_index=direct_index,
        )
        replay = kernel.run_full_day()

        # Every object below is captured while bt is still open.
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

            if (
                captured.replay.audit.execution_integrity_failures
                != 0
            ):
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
    """Open one verified source once and reuse it for the day's 16 replays."""
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


def _fill_payload(fill: m6.FillRecord) -> dict:
    return asdict(fill)


def _cycle_payload(cycle: m6.CycleRecord) -> dict:
    return asdict(cycle)


def _replay_payload(captured: CapturedReplay) -> dict:
    replay = captured.replay

    return {
        "policy_id": replay.policy_id,
        "day": replay.day,
        "scenario": replay.scenario,
        "audit": asdict(replay.audit),
        "natural_end_of_data": replay.natural_end_of_data,
        "terminal_local_timestamp_ns": (
            replay.terminal_local_timestamp_ns
        ),
        "market_wakeups": replay.market_wakeups,
        "response_wakeups": replay.response_wakeups,
        "policy_epochs": replay.policy_epochs,
        "submit_requests": replay.submit_requests,
        "cancel_requests": replay.cancel_requests,
        "maker_fill_count": replay.maker_fill_count,
        "taker_fill_count": replay.taker_fill_count,
        "total_fill_count": replay.total_fill_count,
        "forced_flatten_count": replay.forced_flatten_count,
        "flatten_order_ids": list(replay.flatten_order_ids),
        "terminal_position": replay.terminal_position,
        "terminal_flat": replay.terminal_flat,
        "terminal_working_quote_slots": (
            replay.terminal_working_quote_slots
        ),
        "terminal_shutdown_started": replay.terminal_shutdown_started,
        "terminal_shutdown_quiescent": (
            replay.terminal_shutdown_quiescent
        ),
        "adapter_candidate_epochs": replay.adapter_candidate_epochs,
        "direct_action_queries": captured.direct_action_queries,
        "direct_action_rows_found": captured.direct_action_rows_found,
        "direct_action_missing_rows": (
            captured.direct_action_missing_rows
        ),
        "direct_action_explicit_abstains": (
            captured.direct_action_explicit_abstains
        ),
        "cycles": [
            _cycle_payload(cycle)
            for cycle in replay.cycles
        ],
        "fills": [
            _fill_payload(fill)
            for fill in captured.fills
        ],
    }


def day_evidence_path(day: str) -> Path:
    if day not in DAY_ORDER:
        raise CanonicalRunnerError("day_evidence_day")

    return RESULT_ROOT / f"{day}_DEV045_D6R18_DAY_RESULT.json"


def _write_json_new(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise CanonicalRunnerError(
            f"result_exists:{path.name}"
        ) from exc

    return path


def write_day_evidence(result: DayMatrixResult) -> Path:
    return _write_json_new(
        day_evidence_path(result.day),
        {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": "dev045-d6r18-canonical-day-result-v1",
            "status": "DAY_COMPLETE",
            "day": result.day,
            "replay_count": len(result.replays),
            "fresh_replacement_semantics": True,
            "replays": [
                _replay_payload(captured)
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
    primary = []
    stress = []
    audits = []
    replay_count = 0

    for day_result in days:
        for captured in day_result.replays:
            replay_count += 1
            audits.append(captured.replay.audit)

            if captured.replay.scenario == parent.PRIMARY_SCENARIO:
                primary.extend(captured.fills)
            elif captured.replay.scenario == parent.STRESS_SCENARIO:
                stress.extend(captured.fills)
            else:
                raise CanonicalRunnerError("scenario")

    if replay_count != EXPECTED_TOTAL_REPLAYS:
        raise CanonicalRunnerError("final_replay_count")

    if len(audits) != EXPECTED_TOTAL_REPLAYS:
        raise CanonicalRunnerError("audit_count")

    return tuple(primary), tuple(stress), tuple(audits)


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
    """One-shot D6R18 entrypoint. Never called by development or CI."""
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

        # This is the only arena call and is unreachable before 112 replays.
        arena = m6.run_economic_arena(
            primary_fills=primary,
            stress_fills=stress,
            audits=audits,
        )

        payload = {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": (
                "dev045-d6r18-canonical-economic-result-v1"
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
            "schema_version": "dev045-d6r18-canonical-failure-v1",
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
            "fresh_replacement_semantics": True,
            "live_trading_authorized": False,
        }
        _write_json_new(FAILURE_RESULT_PATH, failure)
        raise


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_HEAD",
    "FRESH_REPLACEMENT_DRIVER_BLOB",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "BOUNDARY_SEMANTIC",
    "DAY_ORDER",
    "POLICY_ORDER",
    "SCENARIO_ORDER",
    "REPLAY_ORDER",
    "EXPECTED_TOTAL_REPLAYS",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "CANONICAL_ATTEMPT_CONSUMED",
    "AUTOMATIC_RETRY",
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

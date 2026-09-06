from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
import os
from pathlib import Path
from typing import Mapping, Sequence

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import (
    dev045_d6r17_canonical_runner_contract as contract,
)
from multimarket import (
    dev045_d6r17_direct_action_driver_bridge as bridge,
)
from multimarket import (
    dev045_d6r17_direct_action_support as support,
)
from multimarket import (
    dev045_d6r17_real_historical_economic_driver as base,
)
from multimarket import (
    dev045_d6r17_real_historical_economic_driver_contract as parent,
)
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_economic_arena as m6


EXPERIMENT_ID = "DEV045-D6R17"
DESIGN_VERSION = "canonical-runner-implementation-v1"

PARENT_HEAD = (
    "7c86bd5f240ef0533cbcb13526e9553888989d37"
)

D6R16_SOURCE_IDENTITY_WITNESS_HEAD = (
    "5411877e3bd1f8fcd9812176bc3dc39dbf18bf88"
)

PARENT_JUNE_SHA256_DEFECTIVE = (
    "ac97ad27c9d58b3b3e249547b8ae7c74cf2ebfde07965103bd5f6c7b853c26b"
)

JUNE_SOURCE_SHA256 = (
    "ac97ad27c9d58b3b3e249547b8ae7c74cf2ebfde07965103bd9c8c05d0df1160"
)

CANONICAL_SOURCE_OPEN_IMPLEMENTED = True
CANONICAL_DAY_MATRIX_IMPLEMENTED = True
FINAL_112_ARENA_IMPLEMENTED = True

CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT = False
AUTOMATIC_RETRY = False
RERUN_AFTER_ATTEMPT_CONSUMPTION = False
TUNING_AFTER_FIRST_OUTPUT = False

NETWORK_ACQUISITION_ENABLED = False
RAILWAY_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

AUG_OPEN_AUTHORIZED = False
SEP_PLUS_OPEN_AUTHORIZED = False
NON_BTC_OPEN_AUTHORIZED = False

RESULT_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/"
    "dev045_d6r17_canonical_economic_run_v1"
)

FINAL_RESULT_PATH = (
    RESULT_ROOT
    / "DEV045_D6R17_CANONICAL_ECONOMIC_RESULT.json"
)

FAILURE_RESULT_PATH = (
    RESULT_ROOT
    / "DEV045_D6R17_CANONICAL_FAILURE.json"
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
        if len(self.fills) != int(
            self.replay.total_fill_count
        ):
            raise CanonicalRunnerError(
                "raw_fill_count_parity"
            )

        if (
            int(self.direct_action_rows_found)
            + int(self.direct_action_missing_rows)
            != int(self.direct_action_queries)
        ):
            raise CanonicalRunnerError(
                "support_counter_identity"
            )


@dataclass(frozen=True)
class DayMatrixResult:
    day: str
    replays: tuple[CapturedReplay, ...]

    def __post_init__(self) -> None:
        if self.day not in contract.DAY_ORDER:
            raise CanonicalRunnerError(
                "day_identity"
            )

        if len(self.replays) != 16:
            raise CanonicalRunnerError(
                "day_matrix_count"
            )

        observed = tuple(
            (
                x.replay.day,
                x.replay.policy_id,
                x.replay.scenario,
            )
            for x in self.replays
        )

        expected = contract.expected_day_replays(
            self.day
        )

        if observed != expected:
            raise CanonicalRunnerError(
                "day_matrix_order"
            )


def _require_authorization(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> None:
    if execution_gate is not True:
        raise CanonicalRunnerError(
            "execution_gate_closed"
        )

    if authorization_token != contract.AUTHORIZATION_TOKEN:
        raise CanonicalRunnerError(
            "authorization_token"
        )

    if os.environ.get(
        contract.AUTHORIZATION_ENV
    ) != contract.AUTHORIZATION_TOKEN:
        raise CanonicalRunnerError(
            "authorization_environment"
        )


def _spec_for_day(
    day: str,
) -> parent.DaySourceSpec:
    matches = tuple(
        x
        for x in parent.DAY_SPECS
        if x.day == day
    )

    if len(matches) != 1:
        raise CanonicalRunnerError(
            "day_spec"
        )

    spec = matches[0]

    # Frozen D6R17 parent contains a transcription defect only
    # for the 2026-06-01 SHA256. Preserve the parent unchanged
    # and apply the exact D6R16 canonical witness identity here.
    if day == "2026-06-01":
        if (
            spec.sha256
            != PARENT_JUNE_SHA256_DEFECTIVE
        ):
            raise CanonicalRunnerError(
                "unexpected_parent_june_identity"
            )

        return replace(
            spec,
            sha256=JUNE_SOURCE_SHA256,
        )

    return spec


def open_verified_day_source(
    *,
    day: str,
    authorization_token: str,
    execution_gate: bool,
) -> adapter.CanonicalJanMemmap:
    """
    Future canonical source opener.

    Authorization is checked before filesystem access.

    `_open_verified_file` performs the frozen full streamed SHA256
    before opening a read-only memmap.
    """
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
        base.validate_canonical_verified_source(
            source,
            day=day,
        )
    except Exception:
        source.close()
        raise

    return source


def load_frozen_day_support(
    *,
    day: str,
) -> dict[
    str,
    support.DirectActionIndex,
]:
    if day in support.BASE_ONLY_DAYS:
        return {}

    if day not in support.DIRECT_SUPPORT_DAYS:
        raise CanonicalRunnerError(
            "support_day"
        )

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
    events: Sequence[
        binding.BoundReplayEvent
    ],
) -> tuple[m6.FillRecord, ...]:
    out = []

    for event in events:
        if event.kind != binding.FILL:
            continue

        if event.fill is None:
            raise CanonicalRunnerError(
                "fill_event_without_record"
            )

        out.append(
            event.fill
        )

    return tuple(out)


def verify_reaccount_parity(
    *,
    policy_id: str,
    day: str,
    scenario: str,
    replay_total_fill_count: int,
    replay_cycles: Sequence[m6.CycleRecord],
    fills: Sequence[m6.FillRecord],
) -> tuple[m6.CycleRecord, ...]:
    if len(fills) != int(
        replay_total_fill_count
    ):
        raise CanonicalRunnerError(
            "raw_fill_count_parity"
        )

    for fill in fills:
        if fill.policy_id != policy_id:
            raise CanonicalRunnerError(
                "fill_policy"
            )

        if fill.day != day:
            raise CanonicalRunnerError(
                "fill_day"
            )

    recomputed = tuple(
        m6.account_fill_bucket(
            tuple(fills),
            scenario=scenario,
        )
    )

    if recomputed != tuple(
        replay_cycles
    ):
        raise CanonicalRunnerError(
            "reaccount_cycle_parity"
        )

    return recomputed


def run_bound_verified_replay_with_fills(
    source: adapter.CanonicalJanMemmap,
    *,
    policy_id: str,
    day: str,
    scenario: str,
    direct_index: (
        support.DirectActionIndex
        | None
    ) = None,
) -> CapturedReplay:
    """
    Execute exactly one already-authorized replay over a caller-owned
    verified source.

    Raw M6 FillRecords are captured from kernel.bound_fills before
    bt.close(), then independently re-accounted for cycle parity.
    """
    bridge.validate_direct_index(
        policy_id=policy_id,
        day=day,
        index=direct_index,
    )

    import hftbacktest as h

    asset = base._build_asset_from_verified_source(
        source,
        scenario=scenario,
        initial_snapshot=None,
    )

    bt = h.HashMapMarketDepthBacktest(
        [asset]
    )

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

        kernel = (
            bridge.DirectActionContinuousHistoricalPolicyKernel(
                bt=bt,
                h=h,
                policy_id=policy_id,
                day=day,
                scenario=scenario,
                terminal_source_local_ns=(
                    terminal_source_local_ns
                ),
                direct_index=direct_index,
            )
        )

        replay = kernel.run_full_day()

        # Contract-critical capture before bt.close().
        fills = extract_fill_records(
            tuple(kernel.bound_fills)
        )

        direct_action_queries = int(
            kernel.direct_action_queries
        )
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
            replay_total_fill_count=(
                replay.total_fill_count
            ),
            replay_cycles=replay.cycles,
            fills=fills,
        )

    finally:
        rc = int(
            bt.close()
        )

        if rc != 0:
            raise CanonicalRunnerError(
                f"backtest_close_rc:{rc}"
            )

    if replay is None:
        raise CanonicalRunnerError(
            "replay_missing"
        )

    return CapturedReplay(
        replay=replay,
        fills=fills,
        direct_action_queries=direct_action_queries,
        direct_action_rows_found=direct_action_rows_found,
        direct_action_missing_rows=direct_action_missing_rows,
        direct_action_explicit_abstains=(
            direct_action_explicit_abstains
        ),
    )


def run_verified_day_matrix(
    source: adapter.CanonicalJanMemmap,
    *,
    day: str,
    direct_by_policy: Mapping[
        str,
        support.DirectActionIndex,
    ],
    authorization_token: str,
    execution_gate: bool,
) -> DayMatrixResult:
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )

    base.validate_canonical_verified_source(
        source,
        day=day,
    )

    bridge._validate_day_mapping(
        day=day,
        direct_by_policy=direct_by_policy,
    )

    before = base._stat_identity(
        source.path
    )

    out = []

    for policy_id in contract.POLICY_ORDER:
        direct_index = (
            direct_by_policy.get(
                policy_id
            )
        )

        for scenario in contract.SCENARIO_ORDER:
            captured = (
                run_bound_verified_replay_with_fills(
                    source,
                    policy_id=policy_id,
                    day=day,
                    scenario=scenario,
                    direct_index=direct_index,
                )
            )

            if (
                captured.replay.audit
                .execution_integrity_failures
                != 0
            ):
                raise CanonicalRunnerError(
                    "execution_integrity_failure"
                )

            if not captured.replay.audit.terminal_flat:
                raise CanonicalRunnerError(
                    "terminal_not_flat"
                )

            if (
                captured.replay
                .terminal_working_quote_slots
                != 0
            ):
                raise CanonicalRunnerError(
                    "terminal_working_quotes"
                )

            out.append(
                captured
            )

    after = base._stat_identity(
        source.path
    )

    if before != after:
        raise CanonicalRunnerError(
            "source_identity_changed"
        )

    return DayMatrixResult(
        day=day,
        replays=tuple(out),
    )


def run_canonical_day_from_disk(
    *,
    day: str,
    authorization_token: str,
    execution_gate: bool,
) -> DayMatrixResult:
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )

    direct_by_policy = (
        load_frozen_day_support(
            day=day
        )
    )

    with open_verified_day_source(
        day=day,
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    ) as source:
        return run_verified_day_matrix(
            source,
            day=day,
            direct_by_policy=direct_by_policy,
            authorization_token=authorization_token,
            execution_gate=execution_gate,
        )


def _fill_payload(
    fill: m6.FillRecord,
) -> dict:
    return asdict(fill)


def _cycle_payload(
    cycle: m6.CycleRecord,
) -> dict:
    return asdict(cycle)


def _replay_payload(
    captured: CapturedReplay,
) -> dict:
    r = captured.replay

    return {
        "policy_id": r.policy_id,
        "day": r.day,
        "scenario": r.scenario,

        "audit": asdict(
            r.audit
        ),

        "natural_end_of_data":
            r.natural_end_of_data,

        "terminal_local_timestamp_ns":
            r.terminal_local_timestamp_ns,

        "market_wakeups":
            r.market_wakeups,

        "response_wakeups":
            r.response_wakeups,

        "policy_epochs":
            r.policy_epochs,

        "submit_requests":
            r.submit_requests,

        "cancel_requests":
            r.cancel_requests,

        "maker_fill_count":
            r.maker_fill_count,

        "taker_fill_count":
            r.taker_fill_count,

        "total_fill_count":
            r.total_fill_count,

        "forced_flatten_count":
            r.forced_flatten_count,

        "flatten_order_ids":
            list(r.flatten_order_ids),

        "terminal_position":
            r.terminal_position,

        "terminal_flat":
            r.terminal_flat,

        "terminal_working_quote_slots":
            r.terminal_working_quote_slots,

        "terminal_shutdown_started":
            r.terminal_shutdown_started,

        "terminal_shutdown_quiescent":
            r.terminal_shutdown_quiescent,

        "adapter_candidate_epochs":
            r.adapter_candidate_epochs,

        "direct_action_queries":
            captured.direct_action_queries,

        "direct_action_rows_found":
            captured.direct_action_rows_found,

        "direct_action_missing_rows":
            captured.direct_action_missing_rows,

        "direct_action_explicit_abstains":
            captured.direct_action_explicit_abstains,

        "cycles": [
            _cycle_payload(x)
            for x in r.cycles
        ],

        # Raw fills are evidence and are preserved exactly for
        # independent frozen M6 re-accounting.
        "fills": [
            _fill_payload(x)
            for x in captured.fills
        ],
    }


def day_evidence_path(
    day: str,
) -> Path:
    if day not in contract.DAY_ORDER:
        raise CanonicalRunnerError(
            "day_evidence_day"
        )

    return (
        RESULT_ROOT
        / (
            day
            + "_DEV045_D6R17_DAY_RESULT.json"
        )
    )


def write_day_evidence(
    result: DayMatrixResult,
) -> Path:
    RESULT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = day_evidence_path(
        result.day
    )

    if path.exists():
        raise CanonicalRunnerError(
            "day_evidence_exists"
        )

    payload = {
        "experiment_id":
            EXPERIMENT_ID,

        "schema_version":
            "dev045-d6r17-canonical-day-result-v1",

        "status":
            "DAY_COMPLETE",

        "day":
            result.day,

        "replay_count":
            len(result.replays),

        "replays": [
            _replay_payload(x)
            for x in result.replays
        ],
    }

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    return path


def _flatten_streams(
    days: Sequence[
        DayMatrixResult
    ],
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

            audits.append(
                captured.replay.audit
            )

            if (
                captured.replay.scenario
                == parent.PRIMARY_SCENARIO
            ):
                primary.extend(
                    captured.fills
                )

            elif (
                captured.replay.scenario
                == parent.STRESS_SCENARIO
            ):
                stress.extend(
                    captured.fills
                )

            else:
                raise CanonicalRunnerError(
                    "scenario"
                )

    if replay_count != 112:
        raise CanonicalRunnerError(
            "final_replay_count"
        )

    if len(audits) != 112:
        raise CanonicalRunnerError(
            "audit_count"
        )

    return (
        tuple(primary),
        tuple(stress),
        tuple(audits),
    )


def run_full_canonical_arena(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> dict:
    """
    Future one-shot canonical execution entrypoint.

    This function is implemented now but MUST NOT be called until
    the separate final preauthorization gate is frozen and green.
    """
    _require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )

    contract.validate_contract()
    parent.validate_contract()

    if FINAL_RESULT_PATH.exists():
        raise CanonicalRunnerError(
            "final_result_exists"
        )

    if FAILURE_RESULT_PATH.exists():
        raise CanonicalRunnerError(
            "prior_failure_evidence_exists"
        )

    completed_days = []
    execution_started = False

    try:
        for day in contract.DAY_ORDER:
            # Execution is considered consumed once the first
            # historical replay is entered. No automatic rerun.
            execution_started = True

            day_result = (
                run_canonical_day_from_disk(
                    day=day,
                    authorization_token=authorization_token,
                    execution_gate=execution_gate,
                )
            )

            write_day_evidence(
                day_result
            )

            completed_days.append(
                day_result
            )

        if len(completed_days) != 7:
            raise CanonicalRunnerError(
                "completed_day_count"
            )

        primary, stress, audits = (
            _flatten_streams(
                completed_days
            )
        )

        arena = m6.run_economic_arena(
            primary_fills=primary,
            stress_fills=stress,
            audits=audits,
        )

        RESULT_ROOT.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "experiment_id":
                EXPERIMENT_ID,

            "schema_version":
                "dev045-d6r17-canonical-economic-result-v1",

            "status":
                "CANONICAL_112_COMPLETE",

            "replay_count":
                112,

            "day_count":
                7,

            "primary_raw_fill_count":
                len(primary),

            "stress_raw_fill_count":
                len(stress),

            "audit_count":
                len(audits),

            "arena":
                arena,

            "live_trading_authorized":
                False,
        }

        FINAL_RESULT_PATH.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )

        return payload

    except Exception as exc:
        if execution_started:
            RESULT_ROOT.mkdir(
                parents=True,
                exist_ok=True,
            )

            if not FAILURE_RESULT_PATH.exists():
                FAILURE_RESULT_PATH.write_text(
                    json.dumps(
                        {
                            "experiment_id":
                                EXPERIMENT_ID,

                            "schema_version":
                                "dev045-d6r17-canonical-failure-v1",

                            "status":
                                "CANONICAL_ATTEMPT_FAILED",

                            "attempt_consumed":
                                True,

                            "completed_days": [
                                x.day
                                for x in completed_days
                            ],

                            "completed_replays":
                                sum(
                                    len(x.replays)
                                    for x in completed_days
                                ),

                            "exception_type":
                                type(exc).__name__,

                            "exception_message":
                                str(exc),

                            "automatic_retry":
                                False,
                        },
                        indent=2,
                        sort_keys=True,
                    ) + "\n",
                    encoding="utf-8",
                )

        raise


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "PARENT_HEAD",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "AUTOMATIC_RETRY",
    "CapturedReplay",
    "DayMatrixResult",
    "open_verified_day_source",
    "load_frozen_day_support",
    "extract_fill_records",
    "verify_reaccount_parity",
    "run_bound_verified_replay_with_fills",
    "run_verified_day_matrix",
    "run_canonical_day_from_disk",
    "day_evidence_path",
    "write_day_evidence",
    "run_full_canonical_arena",
]

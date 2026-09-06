from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Mapping

from multimarket import (
    dev045_d6r17_canonical_runner as frozen,
)
from multimarket import (
    dev045_d6r17_canonical_runner_contract as contract,
)
from multimarket import (
    dev045_d6r17_direct_action_driver_bridge as bridge,
)
from multimarket import (
    dev045_d6r17_direct_action_support as support,
)
from multimarket import dev045_m6_economic_arena as m6


EXPERIMENT_ID = "DEV045-D6R17"

DESIGN_VERSION = (
    "attempt-consumption-boundary-amendment-v1"
)

PARENT_HEAD = (
    "7bf477234d62656ae2d75660fca94c3ae4fdd8f8"
)

BOUNDARY_SEMANTIC = (
    "ATTEMPT_STARTS_IMMEDIATELY_BEFORE_FIRST_"
    "RUN_BOUND_VERIFIED_HISTORICAL_REPLAY"
)

PRE_REPLAY_SOURCE_SHA_FAILURE_CONSUMES = False
PRE_REPLAY_SOURCE_OPEN_FAILURE_CONSUMES = False
PRE_REPLAY_SUPPORT_FAILURE_CONSUMES = False
PRE_REPLAY_VALIDATION_FAILURE_CONSUMES = False

FIRST_HISTORICAL_REPLAY_ENTRY_CONSUMES = True

AUTOMATIC_RETRY = False
RERUN_AFTER_CONSUMPTION = False

CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT = False
LIVE_TRADING_AUTHORIZED = False

RESULT_ROOT = frozen.RESULT_ROOT
FINAL_RESULT_PATH = frozen.FINAL_RESULT_PATH
FAILURE_RESULT_PATH = frozen.FAILURE_RESULT_PATH


class AttemptBoundaryError(RuntimeError):
    pass


def run_verified_day_matrix_with_boundary(
    source,
    *,
    day: str,
    direct_by_policy: Mapping[
        str,
        support.DirectActionIndex,
    ],
    authorization_token: str,
    execution_gate: bool,
    mark_attempt_started: Callable[
        [],
        None,
    ],
) -> frozen.DayMatrixResult:
    """
    Equivalent successor of the frozen day matrix, except that the
    caller receives an exact hook immediately before each historical
    replay call.

    All source/support validation occurs BEFORE that hook.
    """
    frozen._require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )

    frozen.base.validate_canonical_verified_source(
        source,
        day=day,
    )

    bridge._validate_day_mapping(
        day=day,
        direct_by_policy=direct_by_policy,
    )

    before = frozen.base._stat_identity(
        source.path
    )

    out = []

    for policy_id in contract.POLICY_ORDER:
        direct_index = direct_by_policy.get(
            policy_id
        )

        for scenario in contract.SCENARIO_ORDER:
            # This is the exact consumption boundary.
            # Everything above is pre-replay validation.
            mark_attempt_started()

            captured = (
                frozen.run_bound_verified_replay_with_fills(
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
                raise AttemptBoundaryError(
                    "execution_integrity_failure"
                )

            if not captured.replay.audit.terminal_flat:
                raise AttemptBoundaryError(
                    "terminal_not_flat"
                )

            if (
                captured.replay
                .terminal_working_quote_slots
                != 0
            ):
                raise AttemptBoundaryError(
                    "terminal_working_quotes"
                )

            out.append(
                captured
            )

    after = frozen.base._stat_identity(
        source.path
    )

    if before != after:
        raise AttemptBoundaryError(
            "source_identity_changed"
        )

    return frozen.DayMatrixResult(
        day=day,
        replays=tuple(out),
    )


def run_canonical_day_from_disk_with_boundary(
    *,
    day: str,
    authorization_token: str,
    execution_gate: bool,
    mark_attempt_started: Callable[
        [],
        None,
    ],
) -> frozen.DayMatrixResult:
    """
    SHA verification, support loading and source opening are all
    pre-attempt operations.

    The attempt boundary is crossed only inside
    run_verified_day_matrix_with_boundary immediately before the
    first real historical replay.
    """
    frozen._require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )

    direct_by_policy = (
        frozen.load_frozen_day_support(
            day=day
        )
    )

    with frozen.open_verified_day_source(
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


def run_full_canonical_arena(
    *,
    authorization_token: str,
    execution_gate: bool,
) -> dict:
    """
    Corrected one-shot canonical entrypoint.

    IMPORTANT:
    - source SHA/open/support/validation failures occurring before the
      first replay do NOT consume the attempt;
    - immediately before the first historical replay call the attempt
      becomes consumed;
    - every failure after that point is frozen evidence and cannot be
      automatically retried.
    """
    frozen._require_authorization(
        authorization_token=authorization_token,
        execution_gate=execution_gate,
    )

    contract.validate_contract()
    frozen.parent.validate_contract()

    if FINAL_RESULT_PATH.exists():
        raise AttemptBoundaryError(
            "final_result_exists"
        )

    if FAILURE_RESULT_PATH.exists():
        raise AttemptBoundaryError(
            "prior_failure_evidence_exists"
        )

    completed_days = []
    execution_started = False

    def mark_attempt_started() -> None:
        nonlocal execution_started
        execution_started = True

    try:
        for day in contract.DAY_ORDER:
            day_result = (
                run_canonical_day_from_disk_with_boundary(
                    day=day,
                    authorization_token=authorization_token,
                    execution_gate=execution_gate,
                    mark_attempt_started=mark_attempt_started,
                )
            )

            frozen.write_day_evidence(
                day_result
            )

            completed_days.append(
                day_result
            )

        if len(completed_days) != 7:
            raise AttemptBoundaryError(
                "completed_day_count"
            )

        primary, stress, audits = (
            frozen._flatten_streams(
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

            "attempt_consumed":
                True,

            "attempt_boundary":
                BOUNDARY_SEMANTIC,

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
        # Before first replay: no canonical attempt has been consumed.
        if not execution_started:
            raise

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
                            "dev045-d6r17-canonical-failure-v2",

                        "status":
                            "CANONICAL_ATTEMPT_FAILED",

                        "attempt_consumed":
                            True,

                        "attempt_boundary":
                            BOUNDARY_SEMANTIC,

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
    "BOUNDARY_SEMANTIC",
    "PRE_REPLAY_SOURCE_SHA_FAILURE_CONSUMES",
    "PRE_REPLAY_SOURCE_OPEN_FAILURE_CONSUMES",
    "PRE_REPLAY_SUPPORT_FAILURE_CONSUMES",
    "PRE_REPLAY_VALIDATION_FAILURE_CONSUMES",
    "FIRST_HISTORICAL_REPLAY_ENTRY_CONSUMES",
    "AUTOMATIC_RETRY",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "run_verified_day_matrix_with_boundary",
    "run_canonical_day_from_disk_with_boundary",
    "run_full_canonical_arena",
]

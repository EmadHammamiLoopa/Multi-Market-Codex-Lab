from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from multimarket import (
    dev045_d6r17_direct_action_support as direct,
)
from multimarket import (
    dev045_d6r17_real_historical_economic_driver as base,
)
from multimarket import (
    dev045_d6r17_real_historical_economic_driver_contract as contract,
)
from multimarket import dev045_m3_policy as p
from multimarket import dev045_m5a_a0_support_semantics as m5a
from multimarket import dev045_m5b_multirate_clock as m5b
from multimarket import dev045_m6_policy_integration as d3
from multimarket.dev044_t0_strategy_contract import ABSTAIN


EXPERIMENT_ID = "DEV045-D6R17"
DESIGN_VERSION = "direct-frozen-action-driver-bridge-v1"

# This successor does not open canonical market files itself.
CANONICAL_SOURCE_OPEN_IMPLEMENTED = False
CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT = False
CANONICAL_PNL_WRITE_ENABLED = False
NETWORK_ACQUISITION_ENABLED = False
LIVE_TRADING_AUTHORIZED = False
AUTOMATIC_RETRY = False

SYNTHETIC_VALIDATION_ALLOWED = True

ADAPTER_POLICIES = (
    "M06",
    "M07",
)

MODE_BASE_ONLY = "BASE_ONLY"
MODE_NO_ALPHA_UPDATE = "NO_ALPHA_UPDATE"
MODE_DIRECT_FROZEN_ACTION = "DIRECT_FROZEN_ACTION"
MODE_DIRECT_FROZEN_ABSTAIN = "DIRECT_FROZEN_ABSTAIN"
MODE_FALLBACK_TO_M02 = "FALLBACK_TO_M02"


class DirectActionBridgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class DirectActionClockResolution:
    day: str
    policy_id: str
    timestamp_us: int
    mode: str
    active_direction: int
    queried_support: bool
    exact_row_present: bool

    def __post_init__(self) -> None:
        if self.day not in contract.AUTHORIZED_DAYS:
            raise DirectActionBridgeError(
                "resolution_day"
            )

        if self.policy_id not in ADAPTER_POLICIES:
            raise DirectActionBridgeError(
                "resolution_policy"
            )

        if int(self.timestamp_us) < 0:
            raise DirectActionBridgeError(
                "resolution_timestamp"
            )

        if int(self.active_direction) not in (
            -1,
            0,
            1,
        ):
            raise DirectActionBridgeError(
                "resolution_direction"
            )

        allowed = {
            MODE_BASE_ONLY,
            MODE_NO_ALPHA_UPDATE,
            MODE_DIRECT_FROZEN_ACTION,
            MODE_DIRECT_FROZEN_ABSTAIN,
            MODE_FALLBACK_TO_M02,
        }

        if self.mode not in allowed:
            raise DirectActionBridgeError(
                "resolution_mode"
            )

        if self.mode in (
            MODE_BASE_ONLY,
            MODE_NO_ALPHA_UPDATE,
        ):
            if self.queried_support:
                raise DirectActionBridgeError(
                    "unexpected_support_query"
                )

            if self.exact_row_present:
                raise DirectActionBridgeError(
                    "unexpected_exact_row"
                )

        if self.mode == MODE_FALLBACK_TO_M02:
            if not self.queried_support:
                raise DirectActionBridgeError(
                    "fallback_without_query"
                )

            if self.exact_row_present:
                raise DirectActionBridgeError(
                    "fallback_with_row"
                )

            if self.active_direction != ABSTAIN:
                raise DirectActionBridgeError(
                    "fallback_nonabstain"
                )

        if self.mode in (
            MODE_DIRECT_FROZEN_ACTION,
            MODE_DIRECT_FROZEN_ABSTAIN,
        ):
            if not self.queried_support:
                raise DirectActionBridgeError(
                    "direct_without_query"
                )

            if not self.exact_row_present:
                raise DirectActionBridgeError(
                    "direct_without_row"
                )

        if (
            self.mode
            == MODE_DIRECT_FROZEN_ABSTAIN
            and self.active_direction != ABSTAIN
        ):
            raise DirectActionBridgeError(
                "abstain_mode_nonzero"
            )

        if (
            self.mode
            == MODE_DIRECT_FROZEN_ACTION
            and self.active_direction == ABSTAIN
        ):
            raise DirectActionBridgeError(
                "action_mode_zero"
            )


@dataclass(frozen=True)
class DirectActionReplayResult:
    replay: base.ContinuousReplayResult

    direct_action_queries: int
    direct_action_rows_found: int
    direct_action_missing_rows: int
    direct_action_explicit_abstains: int

    def __post_init__(self) -> None:
        values = (
            self.direct_action_queries,
            self.direct_action_rows_found,
            self.direct_action_missing_rows,
            self.direct_action_explicit_abstains,
        )

        if any(int(x) < 0 for x in values):
            raise DirectActionBridgeError(
                "negative_counter"
            )

        if (
            int(self.direct_action_rows_found)
            + int(self.direct_action_missing_rows)
            != int(self.direct_action_queries)
        ):
            raise DirectActionBridgeError(
                "query_counter_identity"
            )


def validate_direct_index(
    *,
    policy_id: str,
    day: str,
    index: direct.DirectActionIndex | None,
) -> None:
    if policy_id not in contract.POLICY_IDS:
        raise DirectActionBridgeError(
            "policy_id"
        )

    if day not in contract.AUTHORIZED_DAYS:
        raise DirectActionBridgeError(
            "day"
        )

    if policy_id not in ADAPTER_POLICIES:
        if index is not None:
            raise DirectActionBridgeError(
                "direct_index_for_nonadapter"
            )

        return

    if day in direct.BASE_ONLY_DAYS:
        if index is not None:
            raise DirectActionBridgeError(
                "direct_index_on_base_only_day"
            )

        return

    if day not in direct.DIRECT_SUPPORT_DAYS:
        raise DirectActionBridgeError(
            "unknown_support_day"
        )

    if index is None:
        raise DirectActionBridgeError(
            "required_direct_index_missing"
        )

    if index.day != day:
        raise DirectActionBridgeError(
            "direct_index_day"
        )

    if index.policy_id != policy_id:
        raise DirectActionBridgeError(
            "direct_index_policy"
        )


def resolve_direct_action_clock(
    *,
    day: str,
    policy_id: str,
    timestamp_us: int,
    previous_direction: int,
    index: direct.DirectActionIndex | None,
) -> DirectActionClockResolution:
    validate_direct_index(
        policy_id=policy_id,
        day=day,
        index=index,
    )

    t = int(timestamp_us)
    previous = int(previous_direction)

    if previous not in (
        -1,
        0,
        1,
    ):
        raise DirectActionBridgeError(
            "previous_direction"
        )

    if not m5b.is_base_maker_decision_epoch(t):
        raise DirectActionBridgeError(
            "not_base_maker_epoch"
        )

    if day in direct.BASE_ONLY_DAYS:
        return DirectActionClockResolution(
            day=day,
            policy_id=policy_id,
            timestamp_us=t,
            mode=MODE_BASE_ONLY,
            active_direction=ABSTAIN,
            queried_support=False,
            exact_row_present=False,
        )

    candidate = m5b.is_adapter_candidate_epoch(
        day=day,
        timestamp_us=t,
    )

    if not candidate:
        return DirectActionClockResolution(
            day=day,
            policy_id=policy_id,
            timestamp_us=t,
            mode=MODE_NO_ALPHA_UPDATE,
            active_direction=previous,
            queried_support=False,
            exact_row_present=False,
        )

    assert index is not None

    point = index.exact(t)

    if point is None:
        # Frozen M5B meaning at an exact adapter candidate:
        # unavailable exact support resets the adapter to M02.
        return DirectActionClockResolution(
            day=day,
            policy_id=policy_id,
            timestamp_us=t,
            mode=MODE_FALLBACK_TO_M02,
            active_direction=ABSTAIN,
            queried_support=True,
            exact_row_present=False,
        )

    direction = int(
        point.direction
    )

    mode = (
        MODE_DIRECT_FROZEN_ABSTAIN
        if direction == ABSTAIN
        else MODE_DIRECT_FROZEN_ACTION
    )

    return DirectActionClockResolution(
        day=day,
        policy_id=policy_id,
        timestamp_us=t,
        mode=mode,
        active_direction=direction,
        queried_support=True,
        exact_row_present=True,
    )


class DirectActionContinuousHistoricalPolicyKernel(
    base.ContinuousHistoricalPolicyKernel
):
    """
    Successor bridge over the frozen full-day D6R17 driver.

    Only M06/M07 alpha resolution changes:
      Apr-Jul exact adapter minutes consume the already-frozen
      DEV044-T0E final direction.
      Missing exact rows fall back to M02.
      Intermediate seconds query nothing and persist only the
      last resolved direction integer.
      Jan-Mar remain base-only.

    Quote maintenance, inventory control, fills, terminal
    shutdown, accounting and simulator lifecycle are inherited
    unchanged from the frozen full-day driver.
    """

    def __init__(
        self,
        *,
        bt,
        h,
        policy_id: str,
        day: str,
        scenario: str,
        terminal_source_local_ns: int,
        direct_index: direct.DirectActionIndex | None = None,
    ) -> None:
        validate_direct_index(
            policy_id=policy_id,
            day=day,
            index=direct_index,
        )

        # Do not pass reconstructed A0 or StrategyState into D3.
        super().__init__(
            bt=bt,
            h=h,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            terminal_source_local_ns=terminal_source_local_ns,
            a0_index=None,
            legacy_index=None,
        )

        self.direct_index = direct_index

        self.direct_action_queries = 0
        self.direct_action_rows_found = 0
        self.direct_action_missing_rows = 0
        self.direct_action_explicit_abstains = 0

    def _adapter_decision(
        self,
        *,
        state: p.MarketState,
        local_timestamp_ns: int,
    ) -> tuple[p.PolicyDecision, str]:
        timestamp_us = (
            int(local_timestamp_ns)
            // 1_000
        )

        resolution = resolve_direct_action_clock(
            day=self.day,
            policy_id=self.policy_id,
            timestamp_us=timestamp_us,
            previous_direction=(
                self.active_adapter_direction
            ),
            index=self.direct_index,
        )

        if resolution.queried_support:
            self.adapter_candidate_epochs += 1
            self.direct_action_queries += 1

            if resolution.exact_row_present:
                self.direct_action_rows_found += 1

                if (
                    resolution.active_direction
                    == ABSTAIN
                ):
                    self.direct_action_explicit_abstains += 1

            else:
                self.direct_action_missing_rows += 1

        self.active_adapter_direction = int(
            resolution.active_direction
        )

        decision = (
            d3.decision_from_active_adapter_direction(
                policy_id=self.policy_id,
                state=state,
                active_direction=(
                    self.active_adapter_direction
                ),
            )
        )

        return (
            decision,
            resolution.mode,
        )


def run_bound_verified_replay(
    source,
    *,
    policy_id: str,
    day: str,
    scenario: str,
    direct_index: direct.DirectActionIndex | None = None,
    initial_snapshot=None,
) -> DirectActionReplayResult:
    """
    Execute over a caller-owned already-verified source.

    This bridge never opens or closes the canonical source.
    """
    validate_direct_index(
        policy_id=policy_id,
        day=day,
        index=direct_index,
    )

    import hftbacktest as h

    asset = base._build_asset_from_verified_source(
        source,
        scenario=scenario,
        initial_snapshot=initial_snapshot,
    )

    bt = h.HashMapMarketDepthBacktest(
        [asset]
    )

    try:
        terminal_source_local_ns = int(
            source.data[-1]["local_ts"]
        )

        kernel = (
            DirectActionContinuousHistoricalPolicyKernel(
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

        return DirectActionReplayResult(
            replay=replay,
            direct_action_queries=int(
                kernel.direct_action_queries
            ),
            direct_action_rows_found=int(
                kernel.direct_action_rows_found
            ),
            direct_action_missing_rows=int(
                kernel.direct_action_missing_rows
            ),
            direct_action_explicit_abstains=int(
                kernel.direct_action_explicit_abstains
            ),
        )

    finally:
        rc = int(
            bt.close()
        )

        if rc != 0:
            raise DirectActionBridgeError(
                f"backtest_close_rc:{rc}"
            )


def _validate_day_mapping(
    *,
    day: str,
    direct_by_policy: Mapping[
        str,
        direct.DirectActionIndex,
    ],
) -> None:
    keys = set(
        direct_by_policy
    )

    if day in direct.BASE_ONLY_DAYS:
        if keys:
            raise DirectActionBridgeError(
                "support_mapping_on_base_only_day"
            )

        return

    if day in direct.DIRECT_SUPPORT_DAYS:
        if keys != set(
            ADAPTER_POLICIES
        ):
            raise DirectActionBridgeError(
                "support_mapping_identity"
            )

        for policy_id in ADAPTER_POLICIES:
            validate_direct_index(
                policy_id=policy_id,
                day=day,
                index=direct_by_policy[
                    policy_id
                ],
            )

        return

    raise DirectActionBridgeError(
        "unknown_day_mapping"
    )


def run_canonical_day_matrix(
    source,
    *,
    day: str,
    direct_by_policy: Mapping[
        str,
        direct.DirectActionIndex,
    ],
    authorization_token: str,
    execution_gate: bool,
) -> tuple[DirectActionReplayResult, ...]:
    """
    Future gated 16-replay/day entrypoint.

    It cannot open canonical sources and is not called during
    this bridge implementation stage.
    """
    if execution_gate is not True:
        raise DirectActionBridgeError(
            "execution_gate_closed"
        )

    if (
        authorization_token
        != contract.AUTHORIZATION_TOKEN
    ):
        raise DirectActionBridgeError(
            "authorization_token"
        )

    base.validate_canonical_verified_source(
        source,
        day=day,
    )

    _validate_day_mapping(
        day=day,
        direct_by_policy=direct_by_policy,
    )

    before = base._stat_identity(
        source.path
    )

    out = []

    for policy_id in contract.POLICY_IDS:
        index = direct_by_policy.get(
            policy_id
        )

        for scenario in contract.SCENARIOS:
            out.append(
                run_bound_verified_replay(
                    source,
                    policy_id=policy_id,
                    day=day,
                    scenario=scenario,
                    direct_index=index,
                    initial_snapshot=None,
                )
            )

    after = base._stat_identity(
        source.path
    )

    if before != after:
        raise DirectActionBridgeError(
            "canonical_source_changed"
        )

    if len(out) != 16:
        raise DirectActionBridgeError(
            "day_matrix_count"
        )

    return tuple(out)


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "CANONICAL_SOURCE_OPEN_IMPLEMENTED",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "AUTOMATIC_RETRY",
    "MODE_BASE_ONLY",
    "MODE_NO_ALPHA_UPDATE",
    "MODE_DIRECT_FROZEN_ACTION",
    "MODE_DIRECT_FROZEN_ABSTAIN",
    "MODE_FALLBACK_TO_M02",
    "DirectActionClockResolution",
    "DirectActionReplayResult",
    "validate_direct_index",
    "resolve_direct_action_clock",
    "DirectActionContinuousHistoricalPolicyKernel",
    "run_bound_verified_replay",
    "run_canonical_day_matrix",
]

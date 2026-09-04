from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import math

from multimarket import dev045_m3_policy as p
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m5a_a0_support_semantics as m5a
from multimarket import dev045_m5b_multirate_clock as m5b
from multimarket import dev045_m6_economic_arena as m6
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket import dev045_m6_event_loop_kernel as d2
from multimarket import dev045_m6_historical_orchestration as orch
from multimarket.dev044_t0_strategy_contract import (
    ABSTAIN,
    LONG,
    SHORT,
    A0_GATE_THRESHOLD,
    StrategyState,
    core_action,
)


EXPERIMENT_ID = "DEV045-D3"
DESIGN_VERSION = "all-policy-patched-kernel-synthetic-v1"

SYNTHETIC_ONLY = True

HISTORICAL_FILE_IO_ENABLED = False
HISTORICAL_REPLAY_EXECUTION_ENABLED = False
HISTORICAL_PNL_ENABLED = False
ECONOMIC_ARENA_EXECUTION_ENABLED = False
CANONICAL_PNL_WRITE_ENABLED = False
NETWORK_ACQUISITION_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

MODE_DIRECT = "DIRECT"

ADAPTER_POLICIES = ("M06", "M07")


class PolicyIntegrationError(RuntimeError):
    pass


def _finite(name: str, value: object) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise PolicyIntegrationError(name) from exc

    if not math.isfinite(x):
        raise PolicyIntegrationError(name)

    return x


def day_start_ns(day: str) -> int:
    if day not in m5a.AUTHORIZED_DAYS:
        raise PolicyIntegrationError("unauthorized_day")

    dt = datetime.fromisoformat(day).replace(
        tzinfo=timezone.utc
    )

    return int(dt.timestamp()) * 1_000_000_000


def day_start_us(day: str) -> int:
    return day_start_ns(day) // 1_000


@dataclass(frozen=True)
class SyntheticLegacyStatePoint:
    timestamp_us: int
    state: StrategyState

    def __post_init__(self) -> None:
        if int(self.timestamp_us) < 0:
            raise PolicyIntegrationError(
                "negative_legacy_timestamp"
            )


@dataclass(frozen=True)
class SyntheticLegacyStateIndex:
    day: str
    points: tuple[SyntheticLegacyStatePoint, ...]

    def __post_init__(self) -> None:
        if self.day not in m5a.A0_EXACT_SUPPORT_DAYS:
            raise PolicyIntegrationError(
                "legacy_index_day"
            )

        ts = tuple(
            int(x.timestamp_us)
            for x in self.points
        )

        if any(
            b <= a
            for a, b in zip(ts, ts[1:])
        ):
            raise PolicyIntegrationError(
                "legacy_index_not_strict"
            )

        for t in ts:
            if not m5b.is_adapter_candidate_epoch(
                day=self.day,
                timestamp_us=t,
            ):
                raise PolicyIntegrationError(
                    "legacy_point_not_adapter_epoch"
                )

    def exact(
        self,
        timestamp_us: int,
    ) -> StrategyState | None:
        t = int(timestamp_us)

        for point in self.points:
            if int(point.timestamp_us) == t:
                return point.state

        return None


@dataclass(frozen=True)
class DecisionTrace:
    local_timestamp_ns: int
    adapter_mode: str
    active_adapter_direction: int

    best_bid_tick: int
    best_ask_tick: int

    l1_obi: float
    microprice_shift_ticks: int
    trade_flow_imbalance: float

    inventory: float
    inventory_age_s: float

    decision: p.PolicyDecision


@dataclass(frozen=True)
class PolicyIntegrationResult:
    kernel: d2.SyntheticKernelResult
    trace: tuple[DecisionTrace, ...]

    adapter_candidate_epochs: int
    legacy_state_queries: int
    exact_minute_identity_checks: int


def _adapter_core_id(policy_id: str) -> str:
    if policy_id == "M06":
        return "T10"

    if policy_id == "M07":
        return "T05"

    raise PolicyIntegrationError(
        "not_adapter_policy"
    )


def adapter_direction_from_support(
    *,
    policy_id: str,
    support: m5a.A0LegacySupport,
) -> int:
    if policy_id not in ADAPTER_POLICIES:
        raise PolicyIntegrationError(
            "not_adapter_policy"
        )

    if not support.available:
        return ABSTAIN

    if support.p_touch is None:
        raise PolicyIntegrationError(
            "available_without_probability"
        )

    if support.legacy_state is None:
        raise PolicyIntegrationError(
            "available_without_legacy_state"
        )

    # The probability itself is used only at this exact adapter epoch.
    # It is never stored in D3 execution state.
    if float(support.p_touch) < A0_GATE_THRESHOLD:
        return ABSTAIN

    return int(
        core_action(
            _adapter_core_id(policy_id),
            support.legacy_state,
        )
    )


def decision_from_active_adapter_direction(
    *,
    policy_id: str,
    state: p.MarketState,
    active_direction: int,
) -> p.PolicyDecision:
    """
    Recompute fresh M02 inventory/risk state every second, then apply only
    the already-resolved one-sided M06/M07 adapter direction.

    The persisted execution state is only LONG/SHORT/ABSTAIN. No p_touch,
    StrategyState, A0 row, or probability is carried between minutes.
    """
    if policy_id not in ADAPTER_POLICIES:
        raise PolicyIntegrationError(
            "not_adapter_policy"
        )

    if int(active_direction) not in (
        ABSTAIN,
        LONG,
        SHORT,
    ):
        raise PolicyIntegrationError(
            "adapter_direction"
        )

    clean_state = replace(
        state,
        legacy_state=None,
        a0_p_touch=m5a.M3_COMPATIBILITY_SENTINEL,
    )

    base = p.policy_decision(
        "M02",
        clean_state,
    )

    if base.force_flatten:
        return replace(
            base,
            policy_id=policy_id,
        )

    bid_tick = base.bid_target_tick
    ask_tick = base.ask_target_tick

    bid_enabled = bool(base.bid_enabled)
    ask_enabled = bool(base.ask_enabled)

    if active_direction == LONG:
        if ask_tick is not None:
            ask_tick = int(ask_tick) + 1

    elif active_direction == SHORT:
        if bid_tick is not None:
            bid_tick = int(bid_tick) - 1

    bid_size = 0.0
    ask_size = 0.0

    if bid_enabled and bid_tick is not None:
        bid_size = p.quote_size(
            float(
                clean_state.bid_depth_qty.get(
                    int(bid_tick),
                    0.0,
                )
            )
        )

        bid_enabled = bool(
            bid_size > 0.0
        )

    if ask_enabled and ask_tick is not None:
        ask_size = p.quote_size(
            float(
                clean_state.ask_depth_qty.get(
                    int(ask_tick),
                    0.0,
                )
            )
        )

        ask_enabled = bool(
            ask_size > 0.0
        )

    if not bid_enabled:
        bid_tick = None
        bid_size = 0.0

    if not ask_enabled:
        ask_tick = None
        ask_size = 0.0

    return p.PolicyDecision(
        policy_id=policy_id,
        bid_target_tick=(
            int(bid_tick)
            if bid_tick is not None
            else None
        ),
        ask_target_tick=(
            int(ask_tick)
            if ask_tick is not None
            else None
        ),
        bid_size=float(bid_size),
        ask_size=float(ask_size),
        bid_enabled=bool(bid_enabled),
        ask_enabled=bool(ask_enabled),
        reference_shift_ticks=int(
            base.reference_shift_ticks
        ),
        force_flatten=False,
        flatten_direction=ABSTAIN,
        flatten_qty=0.0,
    )


class PolicySpecificKernel(
    d2.ActualEventLoopKernel
):
    """
    D3 policy-specific integration over the already-proven D2 kernel.

    M03/M04/M05 consume the current simulator L1 / local trade window
    inherited from D2.

    M06/M07 have two clocks:
      - fresh maker/risk maintenance every exact local second;
      - adapter update only at exact local UTC minutes.

    Between adapter minutes, only the resolved direction integer persists.
    Probability and legacy feature state never persist.
    """

    def __init__(
        self,
        *,
        bt,
        h,
        policy_id: str,
        day: str,
        scenario: str,
        a0_index: m5a.ExactA0ScoreIndex | None = None,
        legacy_index: SyntheticLegacyStateIndex | None = None,
    ) -> None:
        super().__init__(
            bt=bt,
            h=h,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
        )

        if policy_id not in p.POLICY_IDS:
            raise PolicyIntegrationError(
                "policy_id"
            )

        if policy_id not in ADAPTER_POLICIES:
            if (
                a0_index is not None
                or legacy_index is not None
            ):
                raise PolicyIntegrationError(
                    "adapter_input_for_nonadapter_policy"
                )

        if a0_index is not None:
            if a0_index.day != day:
                raise PolicyIntegrationError(
                    "a0_day_mismatch"
                )

        if legacy_index is not None:
            if legacy_index.day != day:
                raise PolicyIntegrationError(
                    "legacy_day_mismatch"
                )

        self.a0_index = a0_index
        self.legacy_index = legacy_index

        self.active_adapter_direction = ABSTAIN

        self.decision_trace: list[
            DecisionTrace
        ] = []

        self.adapter_candidate_epochs = 0
        self.legacy_state_queries = 0
        self.exact_minute_identity_checks = 0

    def _adapter_decision(
        self,
        *,
        state: p.MarketState,
        local_timestamp_ns: int,
    ) -> tuple[p.PolicyDecision, str]:
        timestamp_us = d1.local_ns_to_us(
            local_timestamp_ns
        )

        candidate = (
            m5b.is_adapter_candidate_epoch(
                day=self.day,
                timestamp_us=timestamp_us,
            )
        )

        legacy_state = None

        if candidate:
            self.adapter_candidate_epochs += 1

            if self.legacy_index is not None:
                self.legacy_state_queries += 1
                legacy_state = (
                    self.legacy_index.exact(
                        timestamp_us
                    )
                )

        resolution = m5b.resolve_adapter_clock(
            day=self.day,
            timestamp_us=timestamp_us,
            a0_index=self.a0_index,
            causal_legacy_state=legacy_state,
        )

        if resolution.mode == m5b.MODE_APPLY_ADAPTER:
            if resolution.support is None:
                raise PolicyIntegrationError(
                    "apply_without_support"
                )

            self.active_adapter_direction = (
                adapter_direction_from_support(
                    policy_id=self.policy_id,
                    support=resolution.support,
                )
            )

            decision = (
                decision_from_active_adapter_direction(
                    policy_id=self.policy_id,
                    state=state,
                    active_direction=(
                        self.active_adapter_direction
                    ),
                )
            )

            frozen_decision = (
                m5a.decision_at_epoch(
                    policy_id=self.policy_id,
                    state=state,
                    support=resolution.support,
                )
            )

            if (
                m5a.behavior_signature(decision)
                !=
                m5a.behavior_signature(
                    frozen_decision
                )
            ):
                raise PolicyIntegrationError(
                    "adapter_minute_m3_identity"
                )

            self.exact_minute_identity_checks += 1

            return (
                decision,
                resolution.mode,
            )

        if (
            resolution.mode
            == m5b.MODE_FALLBACK_TO_M02
        ):
            self.active_adapter_direction = ABSTAIN

            decision = (
                decision_from_active_adapter_direction(
                    policy_id=self.policy_id,
                    state=state,
                    active_direction=ABSTAIN,
                )
            )

            base = p.policy_decision(
                "M02",
                replace(
                    state,
                    legacy_state=None,
                    a0_p_touch=(
                        m5a.M3_COMPATIBILITY_SENTINEL
                    ),
                ),
            )

            if (
                m5a.behavior_signature(decision)
                != m5a.behavior_signature(base)
            ):
                raise PolicyIntegrationError(
                    "fallback_not_m02"
                )

            self.exact_minute_identity_checks += 1

            return (
                decision,
                resolution.mode,
            )

        if resolution.mode == m5b.MODE_BASE_ONLY:
            self.active_adapter_direction = ABSTAIN

            return (
                decision_from_active_adapter_direction(
                    policy_id=self.policy_id,
                    state=state,
                    active_direction=ABSTAIN,
                ),
                resolution.mode,
            )

        if (
            resolution.mode
            == m5b.MODE_NO_ALPHA_UPDATE
        ):
            # Critical D3 binding:
            # fresh base maker/risk state is recomputed,
            # but the previously resolved direction integer is unchanged.
            # No probability or StrategyState is reused.
            return (
                decision_from_active_adapter_direction(
                    policy_id=self.policy_id,
                    state=state,
                    active_direction=(
                        self.active_adapter_direction
                    ),
                ),
                resolution.mode,
            )

        raise PolicyIntegrationError(
            f"unexpected_adapter_mode:{resolution.mode}"
        )

    def _evaluate_policy_epoch(
        self,
        *,
        local_timestamp_ns: int,
    ) -> None:
        self.policy_epochs += 1

        state = self._dynamic_market_state(
            local_timestamp_ns=local_timestamp_ns
        )

        if self.policy_id in ADAPTER_POLICIES:
            decision, mode = self._adapter_decision(
                state=state,
                local_timestamp_ns=(
                    local_timestamp_ns
                ),
            )
        else:
            decision = p.policy_decision(
                self.policy_id,
                state,
            )
            mode = MODE_DIRECT

        self.decision_trace.append(
            DecisionTrace(
                local_timestamp_ns=int(
                    local_timestamp_ns
                ),
                adapter_mode=mode,
                active_adapter_direction=int(
                    self.active_adapter_direction
                ),
                best_bid_tick=int(
                    state.best_bid_tick
                ),
                best_ask_tick=int(
                    state.best_ask_tick
                ),
                l1_obi=float(
                    p.l1_obi(state)
                ),
                microprice_shift_ticks=int(
                    p.microprice_shift_ticks(state)
                ),
                trade_flow_imbalance=float(
                    p.trade_flow_imbalance(state)
                ),
                inventory=float(
                    state.inventory
                ),
                inventory_age_s=float(
                    state.inventory_age_s
                ),
                decision=decision,
            )
        )

        if decision.force_flatten:
            if self.flatten_decision_local_ns is None:
                self.flatten_decision_local_ns = int(
                    local_timestamp_ns
                )

            self._force_cancel_quotes(decision)
            self._maybe_execute_forced_flatten()
            return

        self._maintain_side(
            side="bid",
            decision=decision,
        )

        self._maintain_side(
            side="ask",
            decision=decision,
        )


def _policy_initial_snapshot():
    import numpy as np
    import hftbacktest as h

    rows = (
        (h.BUY_EVENT, 99.7, 10.0),
        (h.BUY_EVENT, 99.8, 10.0),
        (h.BUY_EVENT, 99.9, 10.0),
        (h.BUY_EVENT, 100.0, 20.0),
        (h.SELL_EVENT, 100.3, 1.0),
        (h.SELL_EVENT, 100.4, 10.0),
        (h.SELL_EVENT, 100.5, 10.0),
        (h.SELL_EVENT, 100.6, 10.0),
    )

    out = np.zeros(
        len(rows),
        dtype=h.event_dtype,
    )

    for i, (side, price, qty) in enumerate(rows):
        out[i]["ev"] = int(
            h.DEPTH_SNAPSHOT_EVENT
            | h.EXCH_EVENT
            | h.LOCAL_EVENT
            | side
        )
        out[i]["exch_ts"] = 100_000_000
        out[i]["local_ts"] = 110_000_000
        out[i]["px"] = float(price)
        out[i]["qty"] = float(qty)

    return out


def _policy_fixture(day: str):
    import numpy as np
    import hftbacktest as h

    if day not in m5a.AUTHORIZED_DAYS:
        raise PolicyIntegrationError(
            "authorized_day"
        )

    base = m4.make_fill_fixture().copy()

    # First market-visible event before the first exact 1-second timer.
    base[0]["exch_ts"] = 100_000_000
    base[0]["local_ts"] = 110_000_000
    base[0]["px"] = 100.3
    base[0]["qty"] = 1.0

    # RiskAdverse q_ahead at bid 100.0 is exactly 20 BTC in this fixture.
    # The first aggressive sell exhausts queue ahead without filling us.
    base[1]["exch_ts"] = 2_100_000_000
    base[1]["local_ts"] = 2_110_000_000
    base[1]["px"] = 100.0
    base[1]["qty"] = 20.0

    # The next one-lot sell fills the frozen one-lot maker order.
    base[2]["exch_ts"] = 2_200_000_000
    base[2]["local_ts"] = 2_210_000_000
    base[2]["px"] = 100.0
    base[2]["qty"] = p.BASE_ORDER_QTY

    # Keep replay alive past the exact 60-second inventory timeout.
    base[3]["exch_ts"] = 70_000_000_000
    base[3]["local_ts"] = 70_010_000_000
    base[3]["px"] = 100.3
    base[3]["qty"] = 1.0

    offset = day_start_ns(day)

    base["exch_ts"] += offset
    base["local_ts"] += offset

    data = np.asarray(
        base,
        dtype=h.event_dtype,
    )

    m4.validate_events(data)

    return data


def _build_policy_asset(
    data,
    *,
    scenario: str,
):
    import hftbacktest as h

    cfg = orch.scenario_config(
        scenario
    )

    return (
        h.BacktestAsset()
        .data([data])
        .initial_snapshot(
            _policy_initial_snapshot()
        )
        .linear_asset(1.0)
        .constant_order_latency(
            int(cfg.entry_latency_ns),
            int(cfg.response_latency_ns),
        )
        .risk_adverse_queue_model()
        .partial_fill_exchange()
        .trading_value_fee_model(
            float(cfg.maker_fee),
            float(cfg.taker_fee),
        )
        .tick_size(p.TICK_SIZE)
        .lot_size(p.LOT_SIZE)
        .last_trades_capacity(4096)
    )


def synthetic_legacy_state(
    *,
    policy_id: str,
    direction: int,
) -> StrategyState:
    if policy_id not in ADAPTER_POLICIES:
        raise PolicyIntegrationError(
            "not_adapter_policy"
        )

    if direction not in (
        ABSTAIN,
        LONG,
        SHORT,
    ):
        raise PolicyIntegrationError(
            "direction"
        )

    if policy_id == "M06":
        x = 0.0

        if direction == LONG:
            x = 0.20
        elif direction == SHORT:
            x = -0.20

        return StrategyState(
            ofi_1s=x,
            ofi_16s=x,
            ofi_32s=x,
            mid_price=100.0,
            round_level=100.0,
            round_distance_bps=0.0,
            spread_bps=3.0,
        )

    z = 0.0

    if direction == LONG:
        z = -2.0
    elif direction == SHORT:
        z = 2.0

    return StrategyState(
        price_z_32=z,
        mid_price=100.0,
        round_level=100.0,
        round_distance_bps=0.0,
        spread_bps=3.0,
    )


def synthetic_joint_support_inputs(
    *,
    policy_id: str,
    day: str = "2026-04-01",
    direction: int = LONG,
    p_touch: float = 0.75,
) -> tuple[
    m5a.ExactA0ScoreIndex,
    SyntheticLegacyStateIndex,
]:
    if day not in m5a.A0_EXACT_SUPPORT_DAYS:
        raise PolicyIntegrationError(
            "support_day"
        )

    prob = _finite(
        "p_touch",
        p_touch,
    )

    if prob < 0.0 or prob > 1.0:
        raise PolicyIntegrationError(
            "p_touch"
        )

    minute_us = (
        day_start_us(day)
        + m5b.ADAPTER_CANDIDATE_STEP_US
    )

    a0 = m5a.ExactA0ScoreIndex(
        day=day,
        points=(
            m5a.A0ScorePoint(
                minute_us,
                prob,
            ),
        ),
    )

    legacy = SyntheticLegacyStateIndex(
        day=day,
        points=(
            SyntheticLegacyStatePoint(
                minute_us,
                synthetic_legacy_state(
                    policy_id=policy_id,
                    direction=direction,
                ),
            ),
        ),
    )

    return a0, legacy


def run_policy_probe(
    *,
    policy_id: str,
    day: str = "2026-01-01",
    scenario: str = m6.PRIMARY_SCENARIO,
    a0_index: m5a.ExactA0ScoreIndex | None = None,
    legacy_index: SyntheticLegacyStateIndex | None = None,
) -> PolicyIntegrationResult:
    if policy_id not in p.POLICY_IDS:
        raise PolicyIntegrationError(
            "policy_id"
        )

    import hftbacktest as h

    data = _policy_fixture(day)

    asset = _build_policy_asset(
        data,
        scenario=scenario,
    )

    bt = h.HashMapMarketDepthBacktest(
        [asset]
    )

    try:
        kernel = PolicySpecificKernel(
            bt=bt,
            h=h,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            a0_index=a0_index,
            legacy_index=legacy_index,
        )

        result = kernel.run()

        return PolicyIntegrationResult(
            kernel=result,
            trace=tuple(
                kernel.decision_trace
            ),
            adapter_candidate_epochs=int(
                kernel.adapter_candidate_epochs
            ),
            legacy_state_queries=int(
                kernel.legacy_state_queries
            ),
            exact_minute_identity_checks=int(
                kernel.exact_minute_identity_checks
            ),
        )

    finally:
        bt.close()


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "SYNTHETIC_ONLY",
    "HISTORICAL_FILE_IO_ENABLED",
    "HISTORICAL_REPLAY_EXECUTION_ENABLED",
    "HISTORICAL_PNL_ENABLED",
    "ECONOMIC_ARENA_EXECUTION_ENABLED",
    "CANONICAL_PNL_WRITE_ENABLED",
    "NETWORK_ACQUISITION_ENABLED",
    "LIVE_TRADING_AUTHORIZED",
    "MODE_DIRECT",
    "ADAPTER_POLICIES",
    "PolicyIntegrationError",
    "SyntheticLegacyStatePoint",
    "SyntheticLegacyStateIndex",
    "DecisionTrace",
    "PolicyIntegrationResult",
    "day_start_ns",
    "day_start_us",
    "adapter_direction_from_support",
    "decision_from_active_adapter_direction",
    "PolicySpecificKernel",
    "synthetic_legacy_state",
    "synthetic_joint_support_inputs",
    "run_policy_probe",
]

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from multimarket import dev045_d6r5_memmap_adapter as adapter
from multimarket import dev045_m4_adapter as m4
from multimarket import dev045_m4_m6_binding as binding
from multimarket import dev045_m6_event_loop_kernel as d2
from multimarket import dev045_d6r6_historical_driver as d6r6
from multimarket import dev045_d6r17_real_historical_economic_driver_contract as c
from multimarket import dev045_m5a_a0_support_semantics as m5a
from multimarket import dev045_m6_economic_arena as m6
from multimarket import dev045_m6_event_loop_contract as d1
from multimarket import dev045_m6_historical_orchestration as orch
from multimarket import dev045_m6_policy_integration as d3
from multimarket.dev044_t0_strategy_contract import LONG, SHORT, StrategyState


EXPERIMENT_ID = "DEV045-D6R17"
DESIGN_VERSION = "continuous-full-day-real-historical-driver-v1"

# Implementation exists, but canonical execution is still a later gate.
CANONICAL_SOURCE_OPEN_IMPLEMENTED = False
CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT = False
AUTOMATIC_RETRY = False
CANONICAL_PNL_WRITE_ENABLED = False
NETWORK_ACQUISITION_ENABLED = False
LIVE_TRADING_AUTHORIZED = False

SYNTHETIC_VALIDATION_ALLOWED = True

INITIAL_FEED_TIMEOUT_NS = 10_000_000_000
MAX_POLICY_EPOCHS_PER_DAY = 86_500

ADAPTER_POLICIES = ("M06", "M07")


def terminal_shutdown_lead_ns(
    scenario: str,
) -> int:
    cfg = orch.scenario_config(
        scenario
    )

    lead = (
        int(d1.BASE_MAKER_STEP_NS)
        + 2
        * (
            int(cfg.entry_latency_ns)
            + int(cfg.response_latency_ns)
        )
    )

    if lead <= 0:
        raise RealHistoricalDriverError(
            "terminal_shutdown_lead"
        )

    return int(lead)


class RealHistoricalDriverError(RuntimeError):
    pass


@dataclass(frozen=True)
class HistoricalLegacyStatePoint:
    timestamp_us: int
    state: StrategyState

    def __post_init__(self) -> None:
        if isinstance(self.timestamp_us, bool):
            raise RealHistoricalDriverError(
                "legacy_timestamp"
            )

        if int(self.timestamp_us) < 0:
            raise RealHistoricalDriverError(
                "legacy_timestamp"
            )


@dataclass(frozen=True)
class HistoricalLegacyStateIndex:
    day: str
    points: tuple[HistoricalLegacyStatePoint, ...]

    def __post_init__(self) -> None:
        if self.day not in m5a.A0_EXACT_SUPPORT_DAYS:
            raise RealHistoricalDriverError(
                "legacy_support_day"
            )

        ts = tuple(
            int(x.timestamp_us)
            for x in self.points
        )

        if any(
            b <= a
            for a, b in zip(ts, ts[1:])
        ):
            raise RealHistoricalDriverError(
                "legacy_index_not_strict"
            )

        object.__setattr__(
            self,
            "_timestamps",
            ts,
        )

    def exact(
        self,
        timestamp_us: int,
    ) -> StrategyState | None:
        t = int(timestamp_us)

        ts = getattr(
            self,
            "_timestamps",
        )

        i = bisect_left(ts, t)

        if i >= len(ts) or ts[i] != t:
            return None

        return self.points[i].state


@dataclass(frozen=True)
class HistoricalAdapterSupport:
    a0_index: m5a.ExactA0ScoreIndex
    legacy_index: HistoricalLegacyStateIndex

    def __post_init__(self) -> None:
        if self.a0_index.day != self.legacy_index.day:
            raise RealHistoricalDriverError(
                "adapter_support_day_mismatch"
            )


@dataclass(frozen=True)
class ContinuousReplayResult:
    policy_id: str
    day: str
    scenario: str

    cycles: tuple[m6.CycleRecord, ...]
    audit: m6.ReplayAudit

    natural_end_of_data: bool
    terminal_local_timestamp_ns: int

    market_wakeups: int
    response_wakeups: int
    policy_epochs: int

    submit_requests: int
    cancel_requests: int

    maker_fill_count: int
    taker_fill_count: int
    total_fill_count: int

    forced_flatten_count: int
    flatten_order_ids: tuple[int, ...]

    terminal_position: float
    terminal_flat: bool
    terminal_working_quote_slots: int

    terminal_shutdown_started: bool
    terminal_shutdown_quiescent: bool
    terminal_source_local_ns: int
    terminal_shutdown_cutoff_ns: int
    terminal_shutdown_start_ns: int | None
    terminal_shutdown_cancel_requests: int

    adapter_candidate_epochs: int
    legacy_state_queries: int
    exact_minute_identity_checks: int


class ContinuousHistoricalPolicyKernel(
    d3.PolicySpecificKernel
):
    """
    Full-day successor to the frozen D3 single-cycle probe.

    D3 proves the policy/simulator lifecycle, but its run() intentionally
    terminates after the first forced flat-to-flat lifecycle.

    This successor preserves D3 policy decisions, quote maintenance,
    response handling, fill binding and clocks, while resetting only the
    completed forced-flatten lifecycle state so the same frozen policy may
    continue until natural EndOfData.

    It does not open files and does not own the caller's memmap.
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
        a0_index: m5a.ExactA0ScoreIndex | None = None,
        legacy_index: HistoricalLegacyStateIndex | None = None,
    ) -> None:
        super().__init__(
            bt=bt,
            h=h,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            a0_index=a0_index,
            legacy_index=legacy_index,
        )

        self.completed_forced_flattens = 0

        # M4's frozen single-cycle probe uses 4901.
        # Full-day replay must never reuse a completed order ID.
        # Keep flatten IDs strictly below D2 passive ORDER_ID_START.
        self.next_flatten_order_id = int(
            m4.FLATTEN_ORDER_ID
        )
        self.flatten_order_ids: list[int] = []

        final_local = int(
            terminal_source_local_ns
        )

        lead = terminal_shutdown_lead_ns(
            scenario
        )

        if final_local <= lead:
            raise RealHistoricalDriverError(
                "terminal_source_too_short"
            )

        self.terminal_source_local_ns = final_local
        self.terminal_shutdown_cutoff_ns = (
            final_local - lead
        )

        self.terminal_shutdown_started = False
        self.terminal_shutdown_quiescent = False
        self.terminal_shutdown_start_ns: int | None = None
        self.terminal_shutdown_cancel_requests = 0

        self.natural_end_of_data = False
        self.terminal_local_timestamp_ns = -1

    def _execute_unique_flatten(
        self,
        *,
        direction: int,
        qty: float,
    ) -> None:
        before = (
            binding.snapshot_state_values(
                self.bt.state_values(0)
            )
        )

        flatten_order_id = int(
            self.next_flatten_order_id
        )

        if (
            flatten_order_id
            >= int(d2.ORDER_ID_START)
        ):
            raise RealHistoricalDriverError(
                "flatten_order_id_exhausted"
            )

        view = m4.submit_forced_flatten(
            self.bt,
            self.h,
            direction=int(direction),
            qty=float(qty),
            order_id=flatten_order_id,
            wait=True,
        )

        if int(view.order_id) != flatten_order_id:
            raise RealHistoricalDriverError(
                "flatten_order_identity"
            )

        self.next_flatten_order_id += 1

        self.flatten_order_ids.append(
            flatten_order_id
        )

        after = (
            binding.snapshot_state_values(
                self.bt.state_values(0)
            )
        )

        event = (
            binding.bind_forced_flatten_from_state_delta(
                view,
                before=before,
                after=after,
                policy_id=self.policy_id,
                day=self.day,
            )
        )

        if event.kind != binding.FILL:
            raise RealHistoricalDriverError(
                "flatten_fill_missing"
            )

        self.bound_fills.append(
            event
        )

        response_local_ns = int(
            self.bt.current_timestamp
        )

        self.inventory_clock = (
            self.inventory_clock.observe_local_position(
                new_position=float(
                    self.bt.position(0)
                ),
                local_response_timestamp_ns=(
                    response_local_ns
                ),
            )
        )

        self.flatten_response_local_ns = (
            response_local_ns
        )


    def _maybe_execute_forced_flatten(self) -> None:
        if self.flatten_done:
            return

        decision = self.force_decision

        if decision is None:
            return

        if not self._all_quote_slots_clear():
            return

        position = float(
            self.bt.position(0)
        )

        if abs(position) <= 1e-15:
            self.flatten_done = True
            self.inventory_clock = (
                d1.InventoryClock.flat()
            )
            self.flatten_response_local_ns = int(
                self.bt.current_timestamp
            )

        else:
            self._execute_unique_flatten(
                direction=decision.flatten_direction,
                qty=decision.flatten_qty,
            )

            self.flatten_done = True

        if not self.flatten_done:
            return

        position = float(
            self.bt.position(0)
        )

        if abs(position) > 1e-12:
            raise RealHistoricalDriverError(
                "completed_flatten_nonflat"
            )

        if not self._all_quote_slots_clear():
            raise RealHistoricalDriverError(
                "completed_flatten_quotes_not_clear"
            )

        self.completed_forced_flattens += 1

        self.force_decision = None
        self.flatten_done = False

        self.flatten_decision_local_ns = None
        self.flatten_response_local_ns = None
        self.first_nonzero_inventory_local_ns = None
        self.maker_local_response_ns = None


    def _request_terminal_cancels(self) -> None:
        for slot in (
            self.bid,
            self.ask,
        ):
            slot.pending_replacement = None

            if slot.order_id is None:
                continue

            raw = self.bt.orders(0).get(
                int(slot.order_id)
            )

            if raw is None:
                raise RealHistoricalDriverError(
                    "terminal_order_missing"
                )

            if int(raw.req) != int(d2.HFT_NONE):
                continue

            if int(raw.status) in (
                int(d2.HFT_NEW),
                int(d2.HFT_PARTIALLY_FILLED),
            ):
                self._request_cancel(
                    slot=slot,
                    replacement=None,
                )

                self.terminal_shutdown_cancel_requests += 1


    def _advance_terminal_shutdown(self) -> None:
        if not self.terminal_shutdown_started:
            return

        if self.terminal_shutdown_quiescent:
            return

        self._request_terminal_cancels()

        if not self._all_quote_slots_clear():
            return

        position = float(
            self.bt.position(0)
        )

        if abs(position) > 1e-15:
            direction = (
                SHORT
                if position > 0.0
                else LONG
            )

            self._execute_unique_flatten(
                direction=direction,
                qty=abs(position),
            )

            position = float(
                self.bt.position(0)
            )

        if abs(position) > 1e-12:
            raise RealHistoricalDriverError(
                "terminal_shutdown_nonflat"
            )

        if not self._all_quote_slots_clear():
            raise RealHistoricalDriverError(
                "terminal_shutdown_working_quotes"
            )

        self.inventory_clock = (
            d1.InventoryClock.flat()
        )

        self.terminal_shutdown_quiescent = True


    def _begin_terminal_shutdown(
        self,
        *,
        local_timestamp_ns: int,
    ) -> None:
        if self.terminal_shutdown_started:
            self._advance_terminal_shutdown()
            return

        now = int(
            local_timestamp_ns
        )

        if now < self.terminal_shutdown_cutoff_ns:
            raise RealHistoricalDriverError(
                "terminal_shutdown_before_cutoff"
            )

        if now > self.terminal_source_local_ns:
            raise RealHistoricalDriverError(
                "terminal_shutdown_after_source_end"
            )

        self.terminal_shutdown_started = True
        self.terminal_shutdown_start_ns = now

        # Sample-boundary risk takes precedence over any
        # pending strategy lifecycle.  No replacement quote
        # is allowed once shutdown starts.
        self.force_decision = None

        for slot in (
            self.bid,
            self.ask,
        ):
            slot.pending_replacement = None

        self._advance_terminal_shutdown()


    def run_full_day(
        self,
    ) -> ContinuousReplayResult:
        rc = int(
            self.bt.wait_next_feed(
                True,
                INITIAL_FEED_TIMEOUT_NS,
            )
        )

        if rc != 2:
            raise RealHistoricalDriverError(
                f"initial_feed_rc:{rc}"
            )

        self.market_wakeups += 1
        self._capture_last_trades()

        next_policy_ns = (
            d1.next_base_policy_epoch_after(
                int(self.bt.current_timestamp)
            )
        )

        while True:
            now = int(
                self.bt.current_timestamp
            )

            if now > next_policy_ns:
                raise RealHistoricalDriverError(
                    "policy_epoch_skipped"
                )

            # Policy timer after all local-visible events already consumed
            # at this timestamp.
            if now == next_policy_ns:
                if (
                    self.terminal_shutdown_started
                    or now
                    >= self.terminal_shutdown_cutoff_ns
                ):
                    self._begin_terminal_shutdown(
                        local_timestamp_ns=now
                    )

                else:
                    self._evaluate_policy_epoch(
                        local_timestamp_ns=now
                    )

                    if (
                        self.policy_epochs
                        > MAX_POLICY_EPOCHS_PER_DAY
                    ):
                        raise RealHistoricalDriverError(
                            "policy_epoch_guard"
                        )

                next_policy_ns += (
                    d1.BASE_MAKER_STEP_NS
                )

                continue

            timeout = (
                next_policy_ns - now
            )

            before = now

            rc = int(
                self.bt.wait_next_feed(
                    True,
                    int(timeout),
                )
            )

            now = int(
                self.bt.current_timestamp
            )

            if now < before:
                raise RealHistoricalDriverError(
                    "local_clock_reversal"
                )

            if rc == 1:
                self.natural_end_of_data = True
                self.terminal_local_timestamp_ns = now
                break

            if rc == 2:
                self.market_wakeups += 1
                self._capture_last_trades()

            elif rc == 3:
                self.response_wakeups += 1

                self._process_response_batch(
                    local_response_ns=now
                )

                if self.terminal_shutdown_started:
                    self._advance_terminal_shutdown()
                else:
                    self._maybe_execute_forced_flatten()

            elif rc == 0:
                pass

            else:
                raise RealHistoricalDriverError(
                    f"unexpected_wait_rc:{rc}"
                )

            if now > next_policy_ns:
                raise RealHistoricalDriverError(
                    "wake_after_policy_target"
                )

            if now == next_policy_ns:
                if (
                    self.terminal_shutdown_started
                    or now
                    >= self.terminal_shutdown_cutoff_ns
                ):
                    self._begin_terminal_shutdown(
                        local_timestamp_ns=now
                    )

                else:
                    self._evaluate_policy_epoch(
                        local_timestamp_ns=now
                    )

                    if (
                        self.policy_epochs
                        > MAX_POLICY_EPOCHS_PER_DAY
                    ):
                        raise RealHistoricalDriverError(
                            "policy_epoch_guard"
                        )

                next_policy_ns += (
                    d1.BASE_MAKER_STEP_NS
                )

        if not self.natural_end_of_data:
            raise RealHistoricalDriverError(
                "natural_eod_missing"
            )

        terminal_position = float(
            self.bt.position(0)
        )

        active_slots = int(
            self.bid.order_id is not None
        ) + int(
            self.ask.order_id is not None
        )

        if not self.terminal_shutdown_started:
            raise RealHistoricalDriverError(
                "terminal_shutdown_not_started"
            )

        if not self.terminal_shutdown_quiescent:
            raise RealHistoricalDriverError(
                "terminal_shutdown_not_quiescent"
            )

        if abs(terminal_position) > 1e-12:
            raise RealHistoricalDriverError(
                f"end_of_data_nonflat:{terminal_position}"
            )

        if active_slots != 0:
            raise RealHistoricalDriverError(
                f"end_of_data_working_quotes:{active_slots}"
            )

        fill_records = []

        maker_fill_count = 0
        taker_fill_count = 0

        for event in self.bound_fills:
            if event.kind != "FILL":
                continue

            if event.fill is None:
                raise RealHistoricalDriverError(
                    "fill_event_without_record"
                )

            fill_records.append(
                event.fill
            )

            if event.fill.liquidity == "MAKER":
                maker_fill_count += 1

            elif event.fill.liquidity == "TAKER":
                taker_fill_count += 1

            else:
                raise RealHistoricalDriverError(
                    "unknown_liquidity"
                )

        if fill_records:
            cycles = tuple(
                m6.account_fill_bucket(
                    fill_records,
                    scenario=self.scenario,
                )
            )
        else:
            cycles = ()

        audit = m6.ReplayAudit(
            policy_id=self.policy_id,
            day=self.day,
            scenario=self.scenario,
            execution_integrity_failures=0,
            terminal_flat=True,
        )

        return ContinuousReplayResult(
            policy_id=self.policy_id,
            day=self.day,
            scenario=self.scenario,
            cycles=cycles,
            audit=audit,
            natural_end_of_data=True,
            terminal_local_timestamp_ns=int(
                self.terminal_local_timestamp_ns
            ),
            market_wakeups=int(
                self.market_wakeups
            ),
            response_wakeups=int(
                self.response_wakeups
            ),
            policy_epochs=int(
                self.policy_epochs
            ),
            submit_requests=int(
                self.submit_requests
            ),
            cancel_requests=int(
                self.cancel_requests
            ),
            maker_fill_count=int(
                maker_fill_count
            ),
            taker_fill_count=int(
                taker_fill_count
            ),
            total_fill_count=int(
                len(fill_records)
            ),
            forced_flatten_count=int(
                self.completed_forced_flattens
            ),
            flatten_order_ids=tuple(
                int(x)
                for x in self.flatten_order_ids
            ),
            terminal_position=terminal_position,
            terminal_flat=True,
            terminal_working_quote_slots=active_slots,
            terminal_shutdown_started=bool(
                self.terminal_shutdown_started
            ),
            terminal_shutdown_quiescent=bool(
                self.terminal_shutdown_quiescent
            ),
            terminal_source_local_ns=int(
                self.terminal_source_local_ns
            ),
            terminal_shutdown_cutoff_ns=int(
                self.terminal_shutdown_cutoff_ns
            ),
            terminal_shutdown_start_ns=(
                int(self.terminal_shutdown_start_ns)
                if self.terminal_shutdown_start_ns
                is not None
                else None
            ),
            terminal_shutdown_cancel_requests=int(
                self.terminal_shutdown_cancel_requests
            ),
            adapter_candidate_epochs=int(
                self.adapter_candidate_epochs
            ),
            legacy_state_queries=int(
                self.legacy_state_queries
            ),
            exact_minute_identity_checks=int(
                self.exact_minute_identity_checks
            ),
        )


def _validate_support(
    *,
    policy_id: str,
    day: str,
    support: HistoricalAdapterSupport | None,
) -> tuple[
    m5a.ExactA0ScoreIndex | None,
    HistoricalLegacyStateIndex | None,
]:
    if policy_id not in c.POLICY_IDS:
        raise RealHistoricalDriverError(
            "policy_id"
        )

    if day not in c.AUTHORIZED_DAYS:
        raise RealHistoricalDriverError(
            "day"
        )

    if policy_id not in ADAPTER_POLICIES:
        if support is not None:
            raise RealHistoricalDriverError(
                "adapter_support_for_nonadapter_policy"
            )

        return None, None

    if day in m5a.A0_UNAVAILABLE_DAYS:
        if support is not None:
            raise RealHistoricalDriverError(
                "adapter_support_on_frozen_unavailable_day"
            )

        return None, None

    if day not in m5a.A0_EXACT_SUPPORT_DAYS:
        raise RealHistoricalDriverError(
            "unknown_adapter_day"
        )

    if support is None:
        # Critical fail-closed real-historical rule.
        # D3 allows fallback for synthetic semantics, but canonical
        # Apr-Jul M06/M07 may not silently become M02 because a historical
        # support input was simply forgotten.
        raise RealHistoricalDriverError(
            "required_historical_adapter_support_missing"
        )

    if support.a0_index.day != day:
        raise RealHistoricalDriverError(
            "a0_day_mismatch"
        )

    if support.legacy_index.day != day:
        raise RealHistoricalDriverError(
            "legacy_day_mismatch"
        )

    return (
        support.a0_index,
        support.legacy_index,
    )


def _build_asset_from_verified_source(
    source: adapter.CanonicalJanMemmap,
    *,
    scenario: str,
    initial_snapshot=None,
):
    c.validate_contract()

    d6r6._validate_verified_source(
        source
    )

    if scenario not in c.SCENARIOS:
        raise RealHistoricalDriverError(
            "scenario"
        )

    import hftbacktest as h

    if source.data.dtype != h.event_dtype:
        raise RealHistoricalDriverError(
            "hft_event_dtype_mismatch"
        )

    cfg = orch.scenario_config(
        scenario
    )

    asset = (
        h.BacktestAsset()
        .parallel_load(False)
        .latency_offset(0)
        .data(source.data)
    )

    if initial_snapshot is not None:
        asset = asset.initial_snapshot(
            initial_snapshot
        )

    asset = (
        asset
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
        .tick_size(0.1)
        .lot_size(0.001)
        .last_trades_capacity(4096)
    )

    return asset


def run_bound_verified_replay(
    source: adapter.CanonicalJanMemmap,
    *,
    policy_id: str,
    day: str,
    scenario: str,
    support: HistoricalAdapterSupport | None = None,
    initial_snapshot=None,
) -> ContinuousReplayResult:
    """
    Execute one policy/day/scenario over a caller-owned verified memmap.

    This function never opens or closes the source.  The caller must keep
    the verified memmap alive until the hftbacktest object is closed.

    `initial_snapshot` exists only for bounded synthetic validation.  The
    canonical Jan-Jul sources are self-contained and future canonical
    execution must pass None.
    """

    if policy_id not in c.POLICY_IDS:
        raise RealHistoricalDriverError(
            "policy_id"
        )

    if day not in c.AUTHORIZED_DAYS:
        raise RealHistoricalDriverError(
            "day"
        )

    a0_index, legacy_index = (
        _validate_support(
            policy_id=policy_id,
            day=day,
            support=support,
        )
    )

    import hftbacktest as h

    asset = _build_asset_from_verified_source(
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

        kernel = ContinuousHistoricalPolicyKernel(
            bt=bt,
            h=h,
            policy_id=policy_id,
            day=day,
            scenario=scenario,
            terminal_source_local_ns=(
                terminal_source_local_ns
            ),
            a0_index=a0_index,
            legacy_index=legacy_index,
        )

        return kernel.run_full_day()

    finally:
        rc = int(
            bt.close()
        )

        if rc != 0:
            raise RealHistoricalDriverError(
                f"backtest_close_rc:{rc}"
            )


def _spec_for_day(
    day: str,
) -> c.DaySourceSpec:
    matches = tuple(
        x
        for x in c.DAY_SPECS
        if x.day == day
    )

    if len(matches) != 1:
        raise RealHistoricalDriverError(
            "day_spec"
        )

    return matches[0]


def _stat_identity(
    path: Path,
) -> tuple[int, int, int, int]:
    st = path.stat()

    return (
        int(st.st_dev),
        int(st.st_ino),
        int(st.st_size),
        int(st.st_mtime_ns),
    )


def validate_canonical_verified_source(
    source: adapter.CanonicalJanMemmap,
    *,
    day: str,
) -> c.DaySourceSpec:
    """
    Validate an already-opened source against the frozen D6R17 identity.

    No file is opened here and no hash is recomputed here; the D6R5 adapter
    must already have performed the exact streamed SHA256 verification.
    """

    spec = _spec_for_day(day)

    d6r6._validate_verified_source(
        source
    )

    if Path(source.path) != spec.path:
        raise RealHistoricalDriverError(
            "canonical_source_path"
        )

    if source.sha256 != spec.sha256:
        raise RealHistoricalDriverError(
            "canonical_source_sha256"
        )

    if len(source.data) != spec.rows:
        raise RealHistoricalDriverError(
            "canonical_source_rows"
        )

    if int(source.path.stat().st_size) != spec.bytes:
        raise RealHistoricalDriverError(
            "canonical_source_bytes"
        )

    return spec


def _validate_day_support_mapping(
    *,
    day: str,
    support_by_policy: Mapping[
        str,
        HistoricalAdapterSupport,
    ],
) -> None:
    keys = set(
        support_by_policy
    )

    if day in m5a.A0_UNAVAILABLE_DAYS:
        if keys:
            raise RealHistoricalDriverError(
                "support_mapping_on_unavailable_day"
            )

        return

    if day in m5a.A0_EXACT_SUPPORT_DAYS:
        if keys != set(ADAPTER_POLICIES):
            raise RealHistoricalDriverError(
                "support_mapping_identity"
            )

        for policy_id in ADAPTER_POLICIES:
            _validate_support(
                policy_id=policy_id,
                day=day,
                support=support_by_policy[
                    policy_id
                ],
            )

        return

    raise RealHistoricalDriverError(
        "unknown_day_support_semantics"
    )


def run_canonical_day_matrix(
    source: adapter.CanonicalJanMemmap,
    *,
    day: str,
    support_by_policy: Mapping[
        str,
        HistoricalAdapterSupport,
    ],
    authorization_token: str,
    execution_gate: bool,
) -> tuple[ContinuousReplayResult, ...]:
    """
    Future one-shot canonical execution entrypoint for one day.

    It deliberately cannot open the canonical source.  A separately
    authorized runner must:
      1. verify/open it through D6R5;
      2. keep it alive;
      3. call this function exactly once for the day;
      4. close the source only after all 16 replays finish.

    The current D6R17 implementation stage never calls this function.
    """

    if execution_gate is not True:
        raise RealHistoricalDriverError(
            "execution_gate_closed"
        )

    if (
        authorization_token
        != c.AUTHORIZATION_TOKEN
    ):
        raise RealHistoricalDriverError(
            "authorization_token"
        )

    validate_canonical_verified_source(
        source,
        day=day,
    )

    _validate_day_support_mapping(
        day=day,
        support_by_policy=support_by_policy,
    )

    before = _stat_identity(
        source.path
    )

    out = []

    # Frozen deterministic multiplicity order:
    # policy-major, then PRIMARY -> STRESS.
    for policy_id in c.POLICY_IDS:
        support = support_by_policy.get(
            policy_id
        )

        for scenario in c.SCENARIOS:
            out.append(
                run_bound_verified_replay(
                    source,
                    policy_id=policy_id,
                    day=day,
                    scenario=scenario,
                    support=support,
                    initial_snapshot=None,
                )
            )

    after = _stat_identity(
        source.path
    )

    if after != before:
        raise RealHistoricalDriverError(
            "canonical_source_changed"
        )

    if len(out) != 16:
        raise RealHistoricalDriverError(
            "day_matrix_count"
        )

    return tuple(out)


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "CANONICAL_SOURCE_OPEN_IMPLEMENTED",
    "CANONICAL_EXECUTION_AUTHORIZED_BY_DEFAULT",
    "AUTOMATIC_RETRY",
    "CANONICAL_PNL_WRITE_ENABLED",
    "NETWORK_ACQUISITION_ENABLED",
    "LIVE_TRADING_AUTHORIZED",
    "terminal_shutdown_lead_ns",
    "HistoricalLegacyStatePoint",
    "HistoricalLegacyStateIndex",
    "HistoricalAdapterSupport",
    "ContinuousReplayResult",
    "ContinuousHistoricalPolicyKernel",
    "validate_canonical_verified_source",
    "run_bound_verified_replay",
    "run_canonical_day_matrix",
]

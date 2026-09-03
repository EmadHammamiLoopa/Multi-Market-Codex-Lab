from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
import sys
from typing import Iterable, Mapping, Sequence

import numpy as np

from multimarket.dev045_m3_policy import POLICY_IDS
from multimarket.dev045_m5_fee_amendment import (
    PRIMARY_MAKER_RATE,
    PRIMARY_TAKER_RATE,
    STRESS_MAKER_RATE,
    STRESS_TAKER_RATE,
    M6_HISTORICAL_ECONOMICS_AUTHORIZED,
    LIVE_TRADING_AUTHORIZED,
    validate_amendment,
)
from multimarket.dev045_m5_prereg import (
    AUTHORIZED_DAYS,
    BLOCKS_PER_DAY,
    BLOCK_HOURS,
    TOTAL_BLOCKS,
    block_maxstat_test,
    evaluate_eligibility,
    validate_family,
)

VENUE = "BINANCE_FUTURES"
SYMBOL = "BTCUSDT"
PRIMARY_SCENARIO = "Q0_PRIMARY_250_250"
STRESS_SCENARIO = "Q0_STRESS_500_500"
SCENARIOS = (PRIMARY_SCENARIO, STRESS_SCENARIO)
SIDES = ("BUY", "SELL")
LIQUIDITIES = ("MAKER", "TAKER")
INVENTORY_TOL = 1e-12


class M6ArenaError(RuntimeError):
    pass


@dataclass(frozen=True)
class FillRecord:
    policy_id: str
    day: str
    timestamp_ns: int
    side: str
    qty: float
    price: float
    liquidity: str
    venue: str = VENUE
    symbol: str = SYMBOL


@dataclass(frozen=True)
class CycleRecord:
    policy_id: str
    day: str
    start_timestamp_ns: int
    end_timestamp_ns: int
    cash_pnl_before_fees: float
    fees: float
    net_pnl: float
    entry_notional: float
    net_bps: float
    maker_notional: float
    taker_notional: float
    fill_count: int


@dataclass(frozen=True)
class ReplayAudit:
    policy_id: str
    day: str
    scenario: str
    execution_integrity_failures: int
    terminal_flat: bool


def _finite_positive(name: str, value: float) -> float:
    x = float(value)
    if not math.isfinite(x) or x <= 0.0:
        raise M6ArenaError(name)
    return x


def _utc_datetime(timestamp_ns: int) -> datetime:
    if isinstance(timestamp_ns, bool) or int(timestamp_ns) != timestamp_ns or int(timestamp_ns) < 0:
        raise M6ArenaError("timestamp_ns")
    return datetime.fromtimestamp(int(timestamp_ns) / 1_000_000_000, tz=timezone.utc)


def _validate_fill(fill: FillRecord) -> None:
    if fill.policy_id not in POLICY_IDS:
        raise M6ArenaError("policy_id")
    if fill.day not in AUTHORIZED_DAYS:
        raise M6ArenaError("authorized_day")
    if fill.venue != VENUE:
        raise M6ArenaError("venue")
    if fill.symbol != SYMBOL:
        raise M6ArenaError("symbol")
    if fill.side not in SIDES:
        raise M6ArenaError("side")
    if fill.liquidity not in LIQUIDITIES:
        raise M6ArenaError("liquidity")
    _finite_positive("qty", fill.qty)
    _finite_positive("price", fill.price)
    if _utc_datetime(fill.timestamp_ns).date().isoformat() != fill.day:
        raise M6ArenaError("timestamp_day_mismatch")


def _fee_rates(scenario: str) -> tuple[float, float]:
    validate_amendment()
    if not M6_HISTORICAL_ECONOMICS_AUTHORIZED or LIVE_TRADING_AUTHORIZED:
        raise M6ArenaError("authorization_state")
    if scenario == PRIMARY_SCENARIO:
        return PRIMARY_MAKER_RATE, PRIMARY_TAKER_RATE
    if scenario == STRESS_SCENARIO:
        return STRESS_MAKER_RATE, STRESS_TAKER_RATE
    raise M6ArenaError("scenario")


def _fee_rate(scenario: str, liquidity: str) -> float:
    maker, taker = _fee_rates(scenario)
    if liquidity == "MAKER":
        return maker
    if liquidity == "TAKER":
        return taker
    raise M6ArenaError("liquidity")


def _signed_qty(fill: FillRecord) -> float:
    return float(fill.qty) if fill.side == "BUY" else -float(fill.qty)


def _cash_delta(fill: FillRecord) -> float:
    notional = float(fill.qty) * float(fill.price)
    return -notional if fill.side == "BUY" else notional


def account_fill_bucket(fills: Sequence[FillRecord], *, scenario: str) -> list[CycleRecord]:
    """Account one policy/day replay into realized flat-to-flat cycles.

    Input order is execution order and is therefore validated, not silently sorted.
    A sign flip without an observed zero-inventory state fails closed.
    Terminal non-flat inventory also fails closed; the replay layer must provide the
    frozen executable taker flatten before accounting is considered complete.
    """
    _fee_rates(scenario)
    if not fills:
        return []

    first = fills[0]
    for fill in fills:
        _validate_fill(fill)
        if fill.policy_id != first.policy_id or fill.day != first.day:
            raise M6ArenaError("mixed_bucket")

    last_ts = -1
    inventory = 0.0
    cycle_start_ns: int | None = None
    cash = 0.0
    fees = 0.0
    entry_notional = 0.0
    maker_notional = 0.0
    taker_notional = 0.0
    fill_count = 0
    cycles: list[CycleRecord] = []

    for fill in fills:
        ts = int(fill.timestamp_ns)
        if ts < last_ts:
            raise M6ArenaError("out_of_order_fill")
        last_ts = ts

        old_inventory = inventory
        delta = _signed_qty(fill)
        new_inventory = old_inventory + delta
        if abs(new_inventory) <= INVENTORY_TOL:
            new_inventory = 0.0

        if old_inventory != 0.0 and new_inventory != 0.0 and old_inventory * new_inventory < 0.0:
            raise M6ArenaError("inventory_sign_flip_without_flat")

        if old_inventory == 0.0:
            if new_inventory == 0.0:
                raise M6ArenaError("zero_to_zero_fill")
            cycle_start_ns = ts
            cash = 0.0
            fees = 0.0
            entry_notional = 0.0
            maker_notional = 0.0
            taker_notional = 0.0
            fill_count = 0

        notional = float(fill.qty) * float(fill.price)
        cash += _cash_delta(fill)
        fees += notional * _fee_rate(scenario, fill.liquidity)
        fill_count += 1
        if fill.liquidity == "MAKER":
            maker_notional += notional
        else:
            taker_notional += notional
        if abs(new_inventory) > abs(old_inventory) + INVENTORY_TOL:
            entry_notional += notional

        inventory = new_inventory

        if inventory == 0.0:
            if cycle_start_ns is None or entry_notional <= 0.0:
                raise M6ArenaError("cycle_state")
            net = cash - fees
            net_bps = 10_000.0 * net / entry_notional
            if not all(math.isfinite(x) for x in (cash, fees, net, net_bps)):
                raise M6ArenaError("nonfinite_cycle")
            cycles.append(
                CycleRecord(
                    policy_id=first.policy_id,
                    day=first.day,
                    start_timestamp_ns=cycle_start_ns,
                    end_timestamp_ns=ts,
                    cash_pnl_before_fees=float(cash),
                    fees=float(fees),
                    net_pnl=float(net),
                    entry_notional=float(entry_notional),
                    net_bps=float(net_bps),
                    maker_notional=float(maker_notional),
                    taker_notional=float(taker_notional),
                    fill_count=int(fill_count),
                )
            )
            cycle_start_ns = None

    if inventory != 0.0 or cycle_start_ns is not None:
        raise M6ArenaError("terminal_inventory_not_flat")
    return cycles


def account_fills(fills: Iterable[FillRecord], *, scenario: str) -> dict[str, list[CycleRecord]]:
    """Account all authorized policy/day buckets; missing buckets are valid zero-activity buckets."""
    validate_family()
    _fee_rates(scenario)
    buckets: dict[tuple[str, str], list[FillRecord]] = {
        (pid, day): [] for pid in POLICY_IDS for day in AUTHORIZED_DAYS
    }
    last_seen: dict[tuple[str, str], int] = {}
    for fill in fills:
        _validate_fill(fill)
        key = (fill.policy_id, fill.day)
        ts = int(fill.timestamp_ns)
        if key in last_seen and ts < last_seen[key]:
            raise M6ArenaError("out_of_order_fill")
        last_seen[key] = ts
        buckets[key].append(fill)

    out = {pid: [] for pid in POLICY_IDS}
    for pid in POLICY_IDS:
        for day in AUTHORIZED_DAYS:
            out[pid].extend(account_fill_bucket(buckets[(pid, day)], scenario=scenario))
    return out


def cycle_block_index(cycle: CycleRecord) -> int:
    if cycle.policy_id not in POLICY_IDS or cycle.day not in AUTHORIZED_DAYS:
        raise M6ArenaError("cycle_identity")
    dt = _utc_datetime(cycle.start_timestamp_ns)
    if dt.date().isoformat() != cycle.day:
        raise M6ArenaError("cycle_timestamp_day_mismatch")
    day_index = AUTHORIZED_DAYS.index(cycle.day)
    return day_index * BLOCKS_PER_DAY + dt.hour // BLOCK_HOURS


def block_cycle_pnl(cycles_by_policy: Mapping[str, Sequence[CycleRecord]]) -> dict[str, list[float]]:
    if tuple(cycles_by_policy.keys()) != tuple(POLICY_IDS):
        raise M6ArenaError("family_identity")
    matrix = {pid: [0.0] * TOTAL_BLOCKS for pid in POLICY_IDS}
    for pid in POLICY_IDS:
        for cycle in cycles_by_policy[pid]:
            if cycle.policy_id != pid:
                raise M6ArenaError("cycle_policy_mismatch")
            idx = cycle_block_index(cycle)
            matrix[pid][idx] += float(cycle.net_pnl)
    return matrix


def _profit_factor(cycles: Sequence[CycleRecord]) -> float:
    gross_profit = sum(max(0.0, float(c.net_pnl)) for c in cycles)
    gross_loss = -sum(min(0.0, float(c.net_pnl)) for c in cycles)
    if gross_loss > 0.0:
        return float(gross_profit / gross_loss)
    if gross_profit > 0.0:
        # Mathematically +infinity. The frozen M5 eligibility validator requires a
        # finite number, so use the largest finite float without changing >1 truth.
        return sys.float_info.max
    return 0.0


def _cycle_expectancy_bps(cycles: Sequence[CycleRecord]) -> float:
    if not cycles:
        return 0.0
    return float(np.mean(np.asarray([c.net_bps for c in cycles], dtype=np.float64)))


def _daily_net(cycles: Sequence[CycleRecord]) -> dict[str, float]:
    out = {day: 0.0 for day in AUTHORIZED_DAYS}
    for cycle in cycles:
        if cycle.day not in out:
            raise M6ArenaError("authorized_day")
        out[cycle.day] += float(cycle.net_pnl)
    return out


def _positive_day_concentration(daily: Mapping[str, float]) -> float:
    positives = [float(daily[d]) for d in AUTHORIZED_DAYS if float(daily[d]) > 0.0]
    if not positives:
        return 1.0
    total = float(sum(positives))
    return float(max(positives) / total)


def validate_audits(audits: Sequence[ReplayAudit]) -> dict[tuple[str, str, str], ReplayAudit]:
    expected = {(pid, day, scenario) for pid in POLICY_IDS for day in AUTHORIZED_DAYS for scenario in SCENARIOS}
    got: dict[tuple[str, str, str], ReplayAudit] = {}
    for audit in audits:
        if audit.policy_id not in POLICY_IDS or audit.day not in AUTHORIZED_DAYS or audit.scenario not in SCENARIOS:
            raise M6ArenaError("audit_identity")
        if isinstance(audit.execution_integrity_failures, bool) or int(audit.execution_integrity_failures) != audit.execution_integrity_failures or int(audit.execution_integrity_failures) < 0:
            raise M6ArenaError("audit_integrity_count")
        key = (audit.policy_id, audit.day, audit.scenario)
        if key in got:
            raise M6ArenaError("duplicate_audit")
        got[key] = audit
    if set(got) != expected:
        raise M6ArenaError("audit_matrix")
    return got


def run_economic_arena(
    *,
    primary_fills: Iterable[FillRecord],
    stress_fills: Iterable[FillRecord],
    audits: Sequence[ReplayAudit],
) -> dict:
    """Apply the frozen M5 accounting, max-stat inference, and eligibility gates.

    This function consumes replay outputs only. It does not open files, run a
    simulator, alter policy parameters, or authorize live trading.
    """
    validate_amendment()
    validate_family()
    audit_map = validate_audits(audits)

    primary_cycles = account_fills(primary_fills, scenario=PRIMARY_SCENARIO)
    stress_cycles = account_fills(stress_fills, scenario=STRESS_SCENARIO)
    blocks = block_cycle_pnl(primary_cycles)
    inference = block_maxstat_test(blocks)

    policy_results: dict[str, dict] = {}
    for pid in POLICY_IDS:
        pcycles = primary_cycles[pid]
        scycles = stress_cycles[pid]
        daily = _daily_net(pcycles)
        positive_days = sum(1 for d in AUTHORIZED_DAYS if daily[d] > 0.0)
        concentration = _positive_day_concentration(daily)
        primary_expectancy = _cycle_expectancy_bps(pcycles)
        stress_expectancy = _cycle_expectancy_bps(scycles)
        pf = _profit_factor(pcycles)

        policy_audits = [
            audit_map[(pid, day, scenario)]
            for day in AUTHORIZED_DAYS
            for scenario in SCENARIOS
        ]
        integrity_failures = sum(int(a.execution_integrity_failures) for a in policy_audits)
        terminal_flat = all(bool(a.terminal_flat) for a in policy_audits)
        fwer = float(inference["fwer_pvalues"][pid])
        eligibility = evaluate_eligibility(
            policy_id=pid,
            primary_net_expectancy=primary_expectancy,
            primary_pf=pf,
            positive_days=positive_days,
            positive_day_concentration=concentration,
            stress_net_expectancy=stress_expectancy,
            execution_integrity_failures=integrity_failures,
            terminal_flat=terminal_flat,
            fwer_pvalue=fwer,
        )

        policy_results[pid] = {
            "primary_completed_cycles": len(pcycles),
            "stress_completed_cycles": len(scycles),
            "primary_net_expectancy_bps": primary_expectancy,
            "stress_net_expectancy_bps": stress_expectancy,
            "primary_profit_factor": pf,
            "primary_total_net_pnl": float(sum(c.net_pnl for c in pcycles)),
            "daily_net_pnl": daily,
            "positive_days": int(positive_days),
            "positive_day_concentration": concentration,
            "execution_integrity_failures": int(integrity_failures),
            "terminal_flat": bool(terminal_flat),
            "fwer_pvalue": fwer,
            "eligibility": asdict(eligibility),
            "passes_all_gates": bool(eligibility.passes),
        }

    survivors = [pid for pid in POLICY_IDS if policy_results[pid]["passes_all_gates"]]
    return {
        "schema": "DEV045_M6_ECONOMIC_ARENA_V1",
        "venue": VENUE,
        "symbol": SYMBOL,
        "authorized_days": list(AUTHORIZED_DAYS),
        "policy_ids": list(POLICY_IDS),
        "primary_scenario": PRIMARY_SCENARIO,
        "stress_scenario": STRESS_SCENARIO,
        "primary_fees": {"maker": PRIMARY_MAKER_RATE, "taker": PRIMARY_TAKER_RATE},
        "stress_fees": {"maker": STRESS_MAKER_RATE, "taker": STRESS_TAKER_RATE},
        "block_cycle_pnl": blocks,
        "family_inference": inference,
        "policies": policy_results,
        "development_survivors": survivors,
        "live_trading_authorized": False,
    }

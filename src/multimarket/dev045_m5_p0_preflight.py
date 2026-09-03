from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from multimarket.dev045_m3_policy import POLICY_IDS
from multimarket.dev045_m4_adapter import (
    PRIMARY_LATENCY_NS,
    DIAGNOSTIC_LATENCY_NS,
    STRESS_LATENCY_NS,
)
from multimarket.dev045_m5_prereg import AUTHORIZED_DAYS

STATUS_READY = "HISTORICAL_REPLAY_PIPELINE_READY_NO_ECONOMICS"
STATUS_BLOCKED = "HISTORICAL_REPLAY_PIPELINE_BLOCKED"

EXPECTED_POLICIES = ("M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08")
EXPECTED_DAYS = (
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)
EXPECTED_LATENCIES_NS = {
    "diagnostic": 100_000_000,
    "primary": 250_000_000,
    "stress": 500_000_000,
}

FORBIDDEN_OUTPUT_TOKENS = (
    "fill",
    "pnl",
    "profit",
    "spread_capture",
    "fee",
    "markout",
    "expectancy",
    "drawdown",
    "bootstrap",
    "pvalue",
    "p_value",
    "winner",
    "survivor",
    "rank",
    "queue_wait",
    "liquidation",
)

ALLOWED_GATE_KEYS = (
    "authorized_days_identity",
    "policy_family_identity",
    "latency_identity",
    "tardis_inputs_present",
    "tardis_inputs_parseable",
    "event_chronology_valid",
    "book_state_valid",
    "legacy_state_resolvable",
    "adapter_contract_valid",
    "patched_simulator_identity_valid",
)


class M5P0PreflightError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreflightResult:
    status: str
    m6_authorized: bool
    gates: Mapping[str, bool]


def validate_frozen_identities() -> None:
    if tuple(AUTHORIZED_DAYS) != EXPECTED_DAYS:
        raise M5P0PreflightError("authorized_days_identity")
    if tuple(POLICY_IDS) != EXPECTED_POLICIES:
        raise M5P0PreflightError("policy_family_identity")
    actual = {
        "diagnostic": int(DIAGNOSTIC_LATENCY_NS),
        "primary": int(PRIMARY_LATENCY_NS),
        "stress": int(STRESS_LATENCY_NS),
    }
    if actual != EXPECTED_LATENCIES_NS:
        raise M5P0PreflightError("latency_identity")


def validate_output_contract(payload: Mapping[str, object]) -> None:
    def walk_key(key: str) -> None:
        k = key.lower()
        if any(tok in k for tok in FORBIDDEN_OUTPUT_TOKENS):
            raise M5P0PreflightError(f"forbidden_output_key:{key}")

    def walk(value: object) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                walk_key(str(key))
                walk(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                walk(child)

    walk(payload)


def evaluate_preflight(gates: Mapping[str, bool]) -> PreflightResult:
    validate_frozen_identities()
    if tuple(gates.keys()) != ALLOWED_GATE_KEYS:
        raise M5P0PreflightError("gate_identity_or_order")
    if any(type(v) is not bool for v in gates.values()):
        raise M5P0PreflightError("non_boolean_gate")

    passed = all(gates.values())
    result = PreflightResult(
        status=STATUS_READY if passed else STATUS_BLOCKED,
        m6_authorized=False,
        gates=dict(gates),
    )
    payload = {
        "status": result.status,
        "m6_authorized": result.m6_authorized,
        "gates": result.gates,
    }
    validate_output_contract(payload)
    return result


def canonical_gate_map(values: Sequence[bool]) -> dict[str, bool]:
    if len(values) != len(ALLOWED_GATE_KEYS):
        raise M5P0PreflightError("gate_count")
    return {k: bool(v) for k, v in zip(ALLOWED_GATE_KEYS, values)}

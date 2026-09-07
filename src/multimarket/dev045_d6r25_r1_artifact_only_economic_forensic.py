from __future__ import annotations

from collections import defaultdict
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
from typing import Iterable

from multimarket import dev045_d6r25_post_d6r24_economic_forensic_design as design


EXPERIMENT_ID = "DEV045-D6R25-R1"
DESIGN_VERSION = "artifact-only-economic-loss-decomposition-v1"
PARENT_DESIGN_HEAD = "da088950d8602cd6bec681d127050e636d00b2d9"
PARENT_D6R24_FREEZE_HEAD = design.PARENT_D6R24_FREEZE_HEAD

AUTHORIZATION_ENV = "DEV045_D6R25_R1_AUTHORIZE"
AUTHORIZATION_TOKEN = "YES_FROZEN_D6R24_DAY_ARTIFACT_FORENSIC_ONLY"
AUTHORIZED_BY_DEFAULT = False
AUTOMATIC_RETRY = False
RERUN_REQUIRED = False

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
D6R24_FREEZE_META = REPOSITORY_ROOT / "evidence/dev045_d6r24_canonical_economic_freeze.json"
D6R24_FROZEN_RESULT = REPOSITORY_ROOT / "evidence/dev045_d6r24_canonical_economic_result.json"
LOCAL_D6R24_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/dev045_d6r24_canonical_economic_run_v1"
)
RESULT_ROOT = Path(
    "/home/emadh/Multi-Market/evidence/dev045_d6r25_post_d6r24_economic_forensic_v1"
)
RESULT_PATH = RESULT_ROOT / "DEV045_D6R25_R1_FORENSIC_RESULT.json"
FAILURE_PATH = RESULT_ROOT / "DEV045_D6R25_R1_FORENSIC_FAILURE.json"

# Frozen before any D6R24 day artifact is opened by D6R25-R1.
MAKER_SHARE_BUCKETS = (
    "PURE_MAKER_100",
    "MAKER_90_TO_LT100",
    "MAKER_50_TO_LT90",
    "MAKER_LT50",
)
FILL_COUNT_BUCKETS = ("FILL_2", "FILL_3_TO_4", "FILL_5_TO_8", "FILL_9_PLUS")
HOLDING_TIME_BUCKETS = ("HOLD_LE_1S", "HOLD_GT1_TO_5S", "HOLD_GT5_TO_30S", "HOLD_GT30S")
CYCLE_TYPE_BUCKETS = ("PURE_MAKER", "TAKER_CONTAINING")
SUPPORT_REGIMES = ("NO_DIRECT_SUPPORT", "DIRECT_SUPPORT_ACTIVE")

PRIMARY = "Q0_PRIMARY_250_250"
STRESS = "Q0_STRESS_500_500"
SCENARIOS = (PRIMARY, STRESS)
POLICIES = design.POLICY_ORDER
DAYS = design.DAY_ORDER

HISTORICAL_SOURCE_OPEN_AUTHORIZED = False
HISTORICAL_SOURCE_HASH_AUTHORIZED = False
SIMULATOR_AUTHORIZED = False
ECONOMIC_ARENA_RERUN_AUTHORIZED = False
D6R24_RERUN_AUTHORIZED = False
FEE_CHANGE_AUTHORIZED = False
POLICY_RETUNING_AUTHORIZED = False
POLICY_PROMOTION_AUTHORIZED = False
LIVE_TRADING_AUTHORIZED = False

UNSUPPORTED = {
    key: "NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACT"
    for key in design.UNSUPPORTED_ATTRIBUTIONS
}


class D6R25ForensicError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_normalize(value):
    return json.loads(json.dumps(value, sort_keys=True))


def _require_authorization(*, token: str, gate: bool) -> None:
    if gate is not True:
        raise D6R25ForensicError("execution_gate_closed")
    if token != AUTHORIZATION_TOKEN:
        raise D6R25ForensicError("authorization_token")
    if os.environ.get(AUTHORIZATION_ENV) != AUTHORIZATION_TOKEN:
        raise D6R25ForensicError("authorization_environment")


def _require_virgin_result_surface() -> None:
    if RESULT_PATH.exists() or FAILURE_PATH.exists():
        raise D6R25ForensicError("result_surface_not_virgin")
    if RESULT_ROOT.exists() and any(RESULT_ROOT.iterdir()):
        raise D6R25ForensicError("result_surface_not_virgin")


def validate_frozen_lineage() -> dict:
    design.validate_design_contract()
    if not D6R24_FREEZE_META.is_file() or not D6R24_FROZEN_RESULT.is_file():
        raise D6R25ForensicError("frozen_lineage_missing")
    if _sha256(D6R24_FROZEN_RESULT) != design.D6R24_RESULT_SHA256:
        raise D6R25ForensicError("d6r24_result_sha")
    if D6R24_FROZEN_RESULT.stat().st_size != design.D6R24_RESULT_BYTES:
        raise D6R25ForensicError("d6r24_result_bytes")
    freeze = _load_json(D6R24_FREEZE_META)
    result = _load_json(D6R24_FROZEN_RESULT)
    if freeze.get("freeze_status") != "CANONICAL_112_ENGINEERING_PASS_ECONOMIC_FAIL_FROZEN":
        raise D6R25ForensicError("freeze_status")
    if freeze.get("classification") != design.D6R24_CLASSIFICATION:
        raise D6R25ForensicError("freeze_classification")
    if result.get("status") != "CANONICAL_112_COMPLETE":
        raise D6R25ForensicError("result_status")
    if result.get("replay_count") != 112:
        raise D6R25ForensicError("result_replay_count")
    if result.get("arena", {}).get("development_survivors") != []:
        raise D6R25ForensicError("unexpected_survivor")
    return freeze


def validate_execution_contract() -> None:
    validate_frozen_lineage()
    if tuple(MAKER_SHARE_BUCKETS) != (
        "PURE_MAKER_100",
        "MAKER_90_TO_LT100",
        "MAKER_50_TO_LT90",
        "MAKER_LT50",
    ):
        raise D6R25ForensicError("maker_share_buckets")
    if tuple(FILL_COUNT_BUCKETS) != ("FILL_2", "FILL_3_TO_4", "FILL_5_TO_8", "FILL_9_PLUS"):
        raise D6R25ForensicError("fill_count_buckets")
    if tuple(HOLDING_TIME_BUCKETS) != (
        "HOLD_LE_1S",
        "HOLD_GT1_TO_5S",
        "HOLD_GT5_TO_30S",
        "HOLD_GT30S",
    ):
        raise D6R25ForensicError("holding_buckets")
    forbidden = (
        HISTORICAL_SOURCE_OPEN_AUTHORIZED,
        HISTORICAL_SOURCE_HASH_AUTHORIZED,
        SIMULATOR_AUTHORIZED,
        ECONOMIC_ARENA_RERUN_AUTHORIZED,
        D6R24_RERUN_AUTHORIZED,
        FEE_CHANGE_AUTHORIZED,
        POLICY_RETUNING_AUTHORIZED,
        POLICY_PROMOTION_AUTHORIZED,
        LIVE_TRADING_AUTHORIZED,
        AUTOMATIC_RETRY,
    )
    if any(forbidden):
        raise D6R25ForensicError("forbidden_authorization")


def _scenario_rates(scenario: str) -> tuple[float, float]:
    if scenario == PRIMARY:
        return design.PRIMARY_MAKER_RATE, design.PRIMARY_TAKER_RATE
    if scenario == STRESS:
        return design.STRESS_MAKER_RATE, design.STRESS_TAKER_RATE
    raise D6R25ForensicError("scenario")


def _maker_share_bucket(maker: float, taker: float) -> str:
    total = maker + taker
    if total <= 0.0:
        raise D6R25ForensicError("zero_cycle_notional")
    share = maker / total
    if taker <= 1e-12:
        return "PURE_MAKER_100"
    if share >= 0.90:
        return "MAKER_90_TO_LT100"
    if share >= 0.50:
        return "MAKER_50_TO_LT90"
    return "MAKER_LT50"


def _fill_count_bucket(count: int) -> str:
    if count < 2:
        raise D6R25ForensicError("fill_count_lt2")
    if count == 2:
        return "FILL_2"
    if count <= 4:
        return "FILL_3_TO_4"
    if count <= 8:
        return "FILL_5_TO_8"
    return "FILL_9_PLUS"


def _holding_bucket(duration_ns: int) -> str:
    if duration_ns < 0:
        raise D6R25ForensicError("negative_duration")
    if duration_ns <= 1_000_000_000:
        return "HOLD_LE_1S"
    if duration_ns <= 5_000_000_000:
        return "HOLD_GT1_TO_5S"
    if duration_ns <= 30_000_000_000:
        return "HOLD_GT5_TO_30S"
    return "HOLD_GT30S"


def _support_regime(*, day: str, policy_id: str) -> str:
    if day in ("2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01") and policy_id in ("M06", "M07"):
        return "DIRECT_SUPPORT_ACTIVE"
    return "NO_DIRECT_SUPPORT"


def _q(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    x = (len(ordered) - 1) * p
    lo = int(math.floor(x))
    hi = int(math.ceil(x))
    if lo == hi:
        return float(ordered[lo])
    w = x - lo
    return float(ordered[lo] * (1.0 - w) + ordered[hi] * w)


def _new_acc() -> dict:
    return {
        "cycle_count": 0,
        "gross": 0.0,
        "fees": 0.0,
        "net": 0.0,
        "entry": 0.0,
        "maker": 0.0,
        "taker": 0.0,
        "maker_fee": 0.0,
        "taker_fee": 0.0,
        "positive_gross": 0,
        "positive_net": 0,
        "gross_bps": [],
        "fee_bps": [],
        "net_bps": [],
        "durations_ns": [],
    }


def _add_cycle(acc: dict, cycle: dict, *, scenario: str) -> None:
    missing = set(design.CYCLE_FIELDS_REQUIRED) - set(cycle)
    if missing:
        raise D6R25ForensicError(f"cycle_fields:{sorted(missing)}")
    gross = float(cycle["cash_pnl_before_fees"])
    fees = float(cycle["fees"])
    net = float(cycle["net_pnl"])
    entry = float(cycle["entry_notional"])
    maker = float(cycle["maker_notional"])
    taker = float(cycle["taker_notional"])
    if entry <= 0.0 or maker < 0.0 or taker < 0.0:
        raise D6R25ForensicError("cycle_notional")
    if not math.isclose(gross - fees, net, rel_tol=1e-10, abs_tol=1e-9):
        raise D6R25ForensicError("gross_fee_net_cash_parity")
    maker_rate, taker_rate = _scenario_rates(scenario)
    maker_fee = maker * maker_rate
    taker_fee = taker * taker_rate
    if not math.isclose(maker_fee + taker_fee, fees, rel_tol=1e-10, abs_tol=1e-8):
        raise D6R25ForensicError("fee_component_parity")
    gross_bps = 10_000.0 * gross / entry
    fee_bps = 10_000.0 * fees / entry
    net_bps = 10_000.0 * net / entry
    if not math.isclose(gross_bps - fee_bps, net_bps, rel_tol=1e-10, abs_tol=1e-9):
        raise D6R25ForensicError("gross_fee_net_bps_parity")
    duration_ns = int(cycle["end_timestamp_ns"]) - int(cycle["start_timestamp_ns"])
    acc["cycle_count"] += 1
    acc["gross"] += gross
    acc["fees"] += fees
    acc["net"] += net
    acc["entry"] += entry
    acc["maker"] += maker
    acc["taker"] += taker
    acc["maker_fee"] += maker_fee
    acc["taker_fee"] += taker_fee
    acc["positive_gross"] += int(gross > 0.0)
    acc["positive_net"] += int(net > 0.0)
    acc["gross_bps"].append(gross_bps)
    acc["fee_bps"].append(fee_bps)
    acc["net_bps"].append(net_bps)
    acc["durations_ns"].append(float(duration_ns))


def _finalize(acc: dict) -> dict:
    n = int(acc["cycle_count"])
    if n == 0:
        return {"cycle_count": 0}
    gross_mean = statistics.fmean(acc["gross_bps"])
    fee_mean = statistics.fmean(acc["fee_bps"])
    net_mean = statistics.fmean(acc["net_bps"])
    weighted_gross = 10_000.0 * acc["gross"] / acc["entry"]
    weighted_fee = 10_000.0 * acc["fees"] / acc["entry"]
    weighted_net = 10_000.0 * acc["net"] / acc["entry"]
    total_notional = acc["maker"] + acc["taker"]
    if gross_mean <= 0.0:
        break_even = None
        break_even_class = "NO_NONNEGATIVE_FEE_MULTIPLIER_CAN_RESCUE_EXPECTANCY"
    elif net_mean < 0.0:
        break_even = gross_mean / fee_mean if fee_mean > 0.0 else None
        break_even_class = "POSITIVE_GROSS_EDGE_OVERWHELMED_BY_FEES"
    else:
        break_even = 1.0
        break_even_class = "ALREADY_NONNEGATIVE_NET"
    return {
        "cycle_count": n,
        "total_gross_cash_pnl": acc["gross"],
        "total_fees": acc["fees"],
        "total_net_pnl": acc["net"],
        "total_entry_notional": acc["entry"],
        "gross_expectancy_bps_cycle_mean": gross_mean,
        "fee_drag_bps_cycle_mean": fee_mean,
        "net_expectancy_bps_cycle_mean": net_mean,
        "gross_expectancy_bps_notional_weighted": weighted_gross,
        "fee_drag_bps_notional_weighted": weighted_fee,
        "net_expectancy_bps_notional_weighted": weighted_net,
        "positive_gross_cycle_count": acc["positive_gross"],
        "positive_gross_cycle_share": acc["positive_gross"] / n,
        "positive_net_cycle_count": acc["positive_net"],
        "positive_net_cycle_share": acc["positive_net"] / n,
        "gross_bps_q05_q50_q95": [_q(acc["gross_bps"], 0.05), _q(acc["gross_bps"], 0.50), _q(acc["gross_bps"], 0.95)],
        "net_bps_q05_q50_q95": [_q(acc["net_bps"], 0.05), _q(acc["net_bps"], 0.50), _q(acc["net_bps"], 0.95)],
        "cycle_duration_ns_q05_q50_q95": [_q(acc["durations_ns"], 0.05), _q(acc["durations_ns"], 0.50), _q(acc["durations_ns"], 0.95)],
        "maker_notional": acc["maker"],
        "taker_notional": acc["taker"],
        "maker_notional_share": acc["maker"] / total_notional if total_notional > 0 else None,
        "taker_notional_share": acc["taker"] / total_notional if total_notional > 0 else None,
        "maker_fee_component": acc["maker_fee"],
        "taker_fee_component": acc["taker_fee"],
        "zero_fee_expectancy_bps": gross_mean,
        "uniform_fee_multiplier_break_even": break_even,
        "break_even_classification": break_even_class,
    }


def _day_path(day: str) -> Path:
    return LOCAL_D6R24_ROOT / f"{day}_DEV045_D6R24_DAY_RESULT.json"


def _day_identity_map(freeze: dict) -> dict[str, dict]:
    items = freeze.get("day_artifacts", [])
    out = {item["day"]: item for item in items}
    if tuple(out) != DAYS:
        raise D6R25ForensicError("day_identity_order")
    return out


def _write_new(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(_json_normalize(payload), handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise D6R25ForensicError("result_exists") from exc


def run_artifact_only_forensic(*, authorization_token: str, execution_gate: bool) -> dict:
    _require_authorization(token=authorization_token, gate=execution_gate)
    validate_execution_contract()
    _require_virgin_result_surface()
    freeze = validate_frozen_lineage()
    identities = _day_identity_map(freeze)

    overall = {(pid, scenario): _new_acc() for pid in POLICIES for scenario in SCENARIOS}
    cycle_type = defaultdict(_new_acc)
    maker_share = defaultdict(_new_acc)
    fill_bucket = defaultdict(_new_acc)
    hold_bucket = defaultdict(_new_acc)
    support_regime = defaultdict(_new_acc)
    daily = defaultdict(_new_acc)
    blocks = defaultdict(_new_acc)
    forced_flatten_context = defaultdict(int)
    opened_days: list[str] = []

    try:
        for day in DAYS:
            path = _day_path(day)
            expected = identities[day]
            if not path.is_file():
                raise D6R25ForensicError(f"day_missing:{day}")
            if path.stat().st_size != int(expected["bytes"]):
                raise D6R25ForensicError(f"day_bytes:{day}")
            if _sha256(path) != expected["sha256"]:
                raise D6R25ForensicError(f"day_sha:{day}")
            payload = _load_json(path)
            opened_days.append(day)
            if payload.get("experiment_id") != "DEV045-D6R24" or payload.get("status") != "DAY_COMPLETE":
                raise D6R25ForensicError(f"day_schema:{day}")
            if payload.get("day") != day or payload.get("replay_count") != 16:
                raise D6R25ForensicError(f"day_matrix:{day}")
            replays = payload.get("replays", [])
            if len(replays) != 16:
                raise D6R25ForensicError(f"day_replays:{day}")
            seen = set()
            for replay in replays:
                pid = replay["policy_id"]
                scenario = replay["scenario"]
                if pid not in POLICIES or scenario not in SCENARIOS or replay["day"] != day:
                    raise D6R25ForensicError("replay_identity")
                key = (pid, scenario)
                if key in seen:
                    raise D6R25ForensicError("duplicate_replay")
                seen.add(key)
                forced_flatten_context[key] += int(replay.get("forced_flatten_count", 0))
                for cycle in replay.get("cycles", []):
                    if cycle["policy_id"] != pid or cycle["day"] != day:
                        raise D6R25ForensicError("cycle_identity")
                    maker = float(cycle["maker_notional"])
                    taker = float(cycle["taker_notional"])
                    ctype = "PURE_MAKER" if taker <= 1e-12 else "TAKER_CONTAINING"
                    mshare = _maker_share_bucket(maker, taker)
                    fbucket = _fill_count_bucket(int(cycle["fill_count"]))
                    duration_ns = int(cycle["end_timestamp_ns"]) - int(cycle["start_timestamp_ns"])
                    hbucket = _holding_bucket(duration_ns)
                    regime = _support_regime(day=day, policy_id=pid)
                    block = int((int(cycle["start_timestamp_ns"]) // 1_000_000_000) % 86_400 // 14_400)
                    _add_cycle(overall[key], cycle, scenario=scenario)
                    _add_cycle(cycle_type[(pid, scenario, ctype)], cycle, scenario=scenario)
                    _add_cycle(maker_share[(pid, scenario, mshare)], cycle, scenario=scenario)
                    _add_cycle(fill_bucket[(pid, scenario, fbucket)], cycle, scenario=scenario)
                    _add_cycle(hold_bucket[(pid, scenario, hbucket)], cycle, scenario=scenario)
                    _add_cycle(support_regime[(pid, scenario, regime)], cycle, scenario=scenario)
                    _add_cycle(daily[(pid, scenario, day)], cycle, scenario=scenario)
                    _add_cycle(blocks[(pid, scenario, day, block)], cycle, scenario=scenario)
            if len(seen) != 16:
                raise D6R25ForensicError(f"day_replay_matrix:{day}")
            del payload, replays
            gc.collect()
            print(f"D6R25_DAY_COMPLETE={day}", flush=True)

        overall_final = {
            pid: {scenario: _finalize(overall[(pid, scenario)]) for scenario in SCENARIOS}
            for pid in POLICIES
        }
        deltas = {}
        for pid in POLICIES:
            p = overall_final[pid][PRIMARY]
            s = overall_final[pid][STRESS]
            deltas[pid] = {
                "primary_minus_stress_gross_expectancy_bps": p["gross_expectancy_bps_cycle_mean"] - s["gross_expectancy_bps_cycle_mean"],
                "primary_minus_stress_fee_drag_bps": p["fee_drag_bps_cycle_mean"] - s["fee_drag_bps_cycle_mean"],
                "primary_minus_stress_net_expectancy_bps": p["net_expectancy_bps_cycle_mean"] - s["net_expectancy_bps_cycle_mean"],
            }

        primary_gross = [overall_final[pid][PRIMARY]["gross_expectancy_bps_cycle_mean"] for pid in POLICIES]
        if all(value <= 0.0 for value in primary_gross):
            decision = "ZERO_FEE_GROSS_EDGE_NEGATIVE_POLICY_FAMILY_REJECT"
        elif all(overall_final[pid][PRIMARY]["net_expectancy_bps_cycle_mean"] < 0.0 for pid in POLICIES):
            decision = "POSITIVE_GROSS_EDGE_FEE_DOMINATED_REDESIGN_EXECUTION_ECONOMICS"
        else:
            decision = "MIXED_BY_POLICY_OR_REGIME_NEW_PREREGISTERED_FAMILY_REQUIRED"

        result = {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": "dev045-d6r25-r1-artifact-only-economic-forensic-v1",
            "status": "ARTIFACT_ONLY_FORENSIC_COMPLETE",
            "parent_design_head": PARENT_DESIGN_HEAD,
            "parent_d6r24_freeze_head": PARENT_D6R24_FREEZE_HEAD,
            "input_surface": design.INPUT_SURFACE,
            "opened_day_artifacts": opened_days,
            "historical_source_opened": False,
            "historical_source_hashed": False,
            "simulator_started": False,
            "economic_arena_rerun": False,
            "d6r24_rerun": False,
            "fees_changed": False,
            "policy_retuned": False,
            "unsupported_attributions": UNSUPPORTED,
            "unsupported_reasons": design.UNSUPPORTED_REASON,
            "frozen_buckets": {
                "cycle_type": list(CYCLE_TYPE_BUCKETS),
                "maker_share": list(MAKER_SHARE_BUCKETS),
                "fill_count": list(FILL_COUNT_BUCKETS),
                "holding_time": list(HOLDING_TIME_BUCKETS),
                "support_regime": list(SUPPORT_REGIMES),
            },
            "policy_scenario": overall_final,
            "cycle_type": {
                pid: {scenario: {bucket: _finalize(cycle_type[(pid, scenario, bucket)]) for bucket in CYCLE_TYPE_BUCKETS} for scenario in SCENARIOS}
                for pid in POLICIES
            },
            "maker_share_bucket": {
                pid: {scenario: {bucket: _finalize(maker_share[(pid, scenario, bucket)]) for bucket in MAKER_SHARE_BUCKETS} for scenario in SCENARIOS}
                for pid in POLICIES
            },
            "fill_count_bucket": {
                pid: {scenario: {bucket: _finalize(fill_bucket[(pid, scenario, bucket)]) for bucket in FILL_COUNT_BUCKETS} for scenario in SCENARIOS}
                for pid in POLICIES
            },
            "holding_time_bucket": {
                pid: {scenario: {bucket: _finalize(hold_bucket[(pid, scenario, bucket)]) for bucket in HOLDING_TIME_BUCKETS} for scenario in SCENARIOS}
                for pid in POLICIES
            },
            "support_regime": {
                pid: {scenario: {bucket: _finalize(support_regime[(pid, scenario, bucket)]) for bucket in SUPPORT_REGIMES} for scenario in SCENARIOS}
                for pid in POLICIES
            },
            "daily": {
                pid: {scenario: {day: _finalize(daily[(pid, scenario, day)]) for day in DAYS} for scenario in SCENARIOS}
                for pid in POLICIES
            },
            "four_hour_blocks": {
                pid: {scenario: {day: {str(block): _finalize(blocks[(pid, scenario, day, block)]) for block in range(6)} for day in DAYS} for scenario in SCENARIOS}
                for pid in POLICIES
            },
            "forced_flatten_count_context_only": {
                pid: {scenario: forced_flatten_context[(pid, scenario)] for scenario in SCENARIOS}
                for pid in POLICIES
            },
            "primary_minus_stress": deltas,
            "decision_class": decision,
            "interpretation_guard": (
                "M01-M08 quoting family as instantiated only; no claim about market making generally"
            ),
            "next_gate": "D6R26A_FORMAL_GENERATION2_CONDITIONAL_MAKER_EDGE_DESIGN",
        }
        _write_new(RESULT_PATH, result)
        return _json_normalize(result)
    except Exception as exc:
        if opened_days and not RESULT_PATH.exists() and not FAILURE_PATH.exists():
            _write_new(
                FAILURE_PATH,
                {
                    "experiment_id": EXPERIMENT_ID,
                    "status": "ARTIFACT_ONLY_FORENSIC_FAILED",
                    "opened_day_artifacts": opened_days,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc),
                    "automatic_retry": False,
                    "d6r24_rerun": False,
                    "historical_source_opened": False,
                    "simulator_started": False,
                    "economic_arena_rerun": False,
                },
            )
        raise


__all__ = [
    "EXPERIMENT_ID",
    "DESIGN_VERSION",
    "AUTHORIZATION_ENV",
    "AUTHORIZATION_TOKEN",
    "AUTHORIZED_BY_DEFAULT",
    "RESULT_PATH",
    "FAILURE_PATH",
    "MAKER_SHARE_BUCKETS",
    "FILL_COUNT_BUCKETS",
    "HOLDING_TIME_BUCKETS",
    "CYCLE_TYPE_BUCKETS",
    "SUPPORT_REGIMES",
    "UNSUPPORTED",
    "validate_frozen_lineage",
    "validate_execution_contract",
    "run_artifact_only_forensic",
]

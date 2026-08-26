#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPERIMENT_ID = "CODEX-EXP-014-P0"

PASS_STATUS = "DATA_READY_CORRECTED_EXPIRY_SEGMENTED_BTC_OPTIONS_FLOW_SANDBOX"
FAIL_STATUS = "FAIL_CORRECTED_EXPIRY_SEGMENTED_BTC_OPTIONS_FLOW_DATA_NOT_READY"
INVALID_STATUS = "INVALID"

PARENT_PATH = Path(
    "evidence/codex/exp013_p0_corrected_expiry_segmented_options_flow/"
    "CORRECTED_EXPIRY_SEGMENTED_OPTIONS_FLOW_P0_AUDIT.json"
)
PARENT_SHA256 = "fa590862c00d207917e720e0157db495b67cbf3209bac6301f3568008ac0ce4b"

OUT = Path(
    "evidence/codex/exp014_p0_exp013_artifact_adjudication/"
    "EXP013_ARTIFACT_ADJUDICATION_P0.json"
)

EXPECTED_DATES = (
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)

POSITIVE_INVARIANTS = (
    "exp012_result_sha256_verified",
    "all_five_option_raw_hashes_verified",
    "btc_only",
    "only_march_to_july_loaded",
    "atm_log_moneyness_boundary_exact_0_025",
    "atm_numeric_boundary_tolerance_only_1e_12",
    "deribit_option_expiry_hour_exact_08_utc",
    "maturity_boundaries_exact_7_and_30_days",
    "flow_windows_frozen_1_5_15_30",
    "decision_grid_0030_to_2349",
    "strict_underlying_reference_before_trade",
)

SCIENTIFIC_GUARDS = (
    "network_accessed",
    "sealed_august_opened",
    "target_scored",
    "model_fit",
    "auc_scored",
    "direction_scored",
    "pnl_scored",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_parent(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def adjudicate(parent: dict, observed_sha256: str) -> dict:
    checks: dict[str, bool] = {}

    checks["parent_sha256_exact"] = observed_sha256 == PARENT_SHA256
    checks["parent_experiment_id"] = parent.get("experiment_id") == "CODEX-EXP-013-P0"
    checks["parent_status_remains_invalid"] = parent.get("status") == "INVALID"

    invariants = parent.get("invariants")
    checks["invariants_is_dict"] = isinstance(invariants, dict)

    if isinstance(invariants, dict):
        for key in POSITIVE_INVARIANTS:
            checks[f"positive_invariant::{key}"] = invariants.get(key) is True
        for key in SCIENTIFIC_GUARDS:
            checks[f"invariant_guard_false::{key}"] = invariants.get(key) is False
    else:
        for key in POSITIVE_INVARIANTS:
            checks[f"positive_invariant::{key}"] = False
        for key in SCIENTIFIC_GUARDS:
            checks[f"invariant_guard_false::{key}"] = False

    for key in SCIENTIFIC_GUARDS:
        checks[f"top_level_guard_false::{key}"] = parent.get(key) is False

    integrity = parent.get("all_five_days_integrity_pass")
    readiness = parent.get("all_five_days_readiness_pass")
    all_pass = parent.get("all_five_days_pass")

    checks["aggregate_integrity_boolean"] = isinstance(integrity, bool)
    checks["aggregate_readiness_boolean"] = isinstance(readiness, bool)
    checks["aggregate_pass_boolean"] = isinstance(all_pass, bool)
    checks["aggregate_pass_consistent"] = (
        isinstance(integrity, bool)
        and isinstance(readiness, bool)
        and isinstance(all_pass, bool)
        and all_pass is (integrity and readiness)
    )

    days = parent.get("days")
    checks["days_is_five_record_list"] = isinstance(days, list) and len(days) == 5

    if isinstance(days, list):
        dates = tuple(d.get("date") for d in days if isinstance(d, dict))
        checks["dates_exact_and_ordered"] = dates == EXPECTED_DATES

        day_schema_ok = len(days) == 5 and all(isinstance(d, dict) for d in days)
        checks["all_day_records_are_dicts"] = day_schema_ok

        if day_schema_ok:
            checks["all_day_integrity_pass"] = all(d.get("integrity_pass") is True for d in days)
            checks["all_day_readiness_pass"] = all(d.get("readiness_pass") is True for d in days)
            checks["all_day_pass"] = all(d.get("pass") is True for d in days)
            checks["all_day_invalid_expired_zero"] = all(
                d.get("invalid_expired_trades") == 0 for d in days
            )
            checks["all_day_integrity_checks_true"] = all(
                isinstance(d.get("integrity_checks"), dict)
                and d["integrity_checks"]
                and all(v is True for v in d["integrity_checks"].values())
                for d in days
            )
            checks["all_day_readiness_checks_true"] = all(
                isinstance(d.get("readiness_checks"), dict)
                and d["readiness_checks"]
                and all(v is True for v in d["readiness_checks"].values())
                for d in days
            )
        else:
            for key in (
                "all_day_integrity_pass",
                "all_day_readiness_pass",
                "all_day_pass",
                "all_day_invalid_expired_zero",
                "all_day_integrity_checks_true",
                "all_day_readiness_checks_true",
            ):
                checks[key] = False
    else:
        checks["dates_exact_and_ordered"] = False
        checks["all_day_records_are_dicts"] = False
        for key in (
            "all_day_integrity_pass",
            "all_day_readiness_pass",
            "all_day_pass",
            "all_day_invalid_expired_zero",
            "all_day_integrity_checks_true",
            "all_day_readiness_checks_true",
        ):
            checks[key] = False

    provenance_and_schema_keys = (
        "parent_sha256_exact",
        "parent_experiment_id",
        "parent_status_remains_invalid",
        "invariants_is_dict",
        "aggregate_integrity_boolean",
        "aggregate_readiness_boolean",
        "aggregate_pass_boolean",
        "aggregate_pass_consistent",
        "days_is_five_record_list",
        "dates_exact_and_ordered",
        "all_day_records_are_dicts",
    )

    polarity_checks = [
        checks[f"positive_invariant::{k}"] for k in POSITIVE_INVARIANTS
    ] + [
        checks[f"invariant_guard_false::{k}"] for k in SCIENTIFIC_GUARDS
    ] + [
        checks[f"top_level_guard_false::{k}"] for k in SCIENTIFIC_GUARDS
    ]

    provenance_and_schema_ok = all(checks[k] for k in provenance_and_schema_keys)
    polarity_ok = all(polarity_checks)

    day_integrity_recorded = (
        checks["all_day_integrity_pass"]
        and checks["all_day_invalid_expired_zero"]
        and checks["all_day_integrity_checks_true"]
    )

    day_readiness_recorded = (
        checks["all_day_readiness_pass"]
        and checks["all_day_pass"]
        and checks["all_day_readiness_checks_true"]
    )

    parent_integrity_recorded = integrity is True and day_integrity_recorded
    parent_readiness_recorded = readiness is True and day_readiness_recorded

    if not provenance_and_schema_ok or not polarity_ok:
        status = INVALID_STATUS
    elif not parent_integrity_recorded:
        status = INVALID_STATUS
    elif parent_readiness_recorded:
        status = PASS_STATUS
    elif readiness is False:
        status = FAIL_STATUS
    else:
        status = INVALID_STATUS

    return {
        "experiment_id": EXPERIMENT_ID,
        "source_experiment_id": "CODEX-EXP-013-P0",
        "source_artifact_sha256": observed_sha256,
        "expected_source_artifact_sha256": PARENT_SHA256,
        "status": status,
        "source_status_preserved": parent.get("status"),
        "recorded_integrity_pass": integrity,
        "recorded_readiness_pass": readiness,
        "recorded_all_five_days_pass": all_pass,
        "verification_checks": checks,
        "positive_invariant_keys": list(POSITIVE_INVARIANTS),
        "scientific_guard_keys": list(SCIENTIFIC_GUARDS),
        "network_accessed": False,
        "sealed_august_opened": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
        "raw_market_data_read": False,
        "phase_l_read": False,
        "market_metrics_recomputed": False,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Frozen CODEX-EXP-014-P0 artifact-only adjudication correction"
    )
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--source", type=Path, default=PARENT_PATH)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args(argv)

    workspace = args.workspace.resolve()
    source = workspace / args.source
    output = workspace / args.output
    partial = output.with_suffix(output.suffix + ".partial")

    if output.exists() or partial.exists():
        raise RuntimeError("EXP014 output already exists")

    observed_sha256 = sha256_file(source)
    parent = load_parent(source)
    result = adjudicate(parent, observed_sha256)

    output.parent.mkdir(parents=True, exist_ok=True)
    partial.write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n",
        encoding="utf-8",
    )
    partial.replace(output)

    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "source_artifact_sha256": result["source_artifact_sha256"],
                "status": result["status"],
                "recorded_integrity_pass": result["recorded_integrity_pass"],
                "recorded_readiness_pass": result["recorded_readiness_pass"],
                "network_accessed": False,
                "sealed_august_opened": False,
                "target_scored": False,
                "model_fit": False,
                "auc_scored": False,
                "direction_scored": False,
                "pnl_scored": False,
                "raw_market_data_read": False,
                "phase_l_read": False,
                "market_metrics_recomputed": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

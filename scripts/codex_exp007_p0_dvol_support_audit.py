#!/usr/bin/env python3

import hashlib
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


EXPERIMENT_ID = "CODEX-EXP-007-P0"

ROOT = Path(__file__).resolve().parents[1]

PREREG = ROOT / "docs" / "CODEX_EXP007_P0_PREREGISTRATION.md"

EXP006_ROOT = ROOT / "evidence" / "codex" / "exp006_p0_dvol"
RAW_DIR = EXP006_ROOT / "raw"
EXP006_MANIFEST = EXP006_ROOT / "DVOL_ACQUISITION_MANIFEST.json"

OUT_ROOT = ROOT / "evidence" / "codex" / "exp007_p0_dvol_support"
RESULT_PATH = OUT_ROOT / "DVOL_SUPPORT_AUDIT.json"

CURRENCIES = ("BTC", "ETH")

SUPERVISED_DAYS = (
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)

CONTEXT_PAIRS = (
    ("2026-02-28", "2026-03-01"),
    ("2026-03-31", "2026-04-01"),
    ("2026-04-30", "2026-05-01"),
    ("2026-05-31", "2026-06-01"),
    ("2026-06-30", "2026-07-01"),
)

EXPECTED_ALL_DATES = (
    "2026-02-28",
    "2026-03-01",
    "2026-03-31",
    "2026-04-01",
    "2026-04-30",
    "2026-05-01",
    "2026-05-31",
    "2026-06-01",
    "2026-06-30",
    "2026-07-01",
)

MINUTE_MS = 60_000
EXPECTED_DAY_ROWS = 1440
TAIL_MINUTES = 31


def canonical_json_bytes(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def parse_day(day_s):
    return datetime.strptime(
        day_s,
        "%Y-%m-%d",
    ).replace(tzinfo=timezone.utc)


def ms(dt):
    return int(dt.timestamp() * 1000)


def raw_filename(currency, day_s):
    return (
        f"{currency}_DVOL_60S_"
        f"{day_s.replace('-', '')}.json"
    )


def validate_ohlc_row(row):
    if not isinstance(row, list):
        return False

    if len(row) != 5:
        return False

    ts, opn, high, low, close = row

    if (
        not isinstance(ts, int)
        or isinstance(ts, bool)
    ):
        return False

    values = (opn, high, low, close)

    for x in values:
        if (
            not isinstance(x, (int, float))
            or isinstance(x, bool)
        ):
            return False

        x = float(x)

        if not math.isfinite(x) or x <= 0.0:
            return False

    opn = float(opn)
    high = float(high)
    low = float(low)
    close = float(close)

    if high < max(opn, close):
        return False

    if low > min(opn, close):
        return False

    if high < low:
        return False

    return True


def load_raw(currency, day_s):
    path = RAW_DIR / raw_filename(
        currency,
        day_s,
    )

    if not path.exists():
        raise RuntimeError(
            f"Missing frozen raw artifact: {path}"
        )

    obj = json.loads(
        path.read_text(encoding="utf-8")
    )

    if obj.get("currency") != currency:
        raise RuntimeError(
            f"Currency mismatch: {path}"
        )

    if obj.get("date") != day_s:
        raise RuntimeError(
            f"Date mismatch: {path}"
        )

    if obj.get("resolution_seconds") != 60:
        raise RuntimeError(
            f"Resolution mismatch: {path}"
        )

    data = obj.get("data")

    if not isinstance(data, list):
        raise RuntimeError(
            f"Data is not a list: {path}"
        )

    return path, data


def expected_full_day_timestamps(day_s):
    start = ms(parse_day(day_s))

    return [
        start + i * MINUTE_MS
        for i in range(EXPECTED_DAY_ROWS)
    ]


def expected_context_tail(day_s):
    day = parse_day(day_s)

    start = day + timedelta(
        hours=23,
        minutes=29,
    )

    return [
        ms(start + timedelta(minutes=i))
        for i in range(TAIL_MINUTES)
    ]


def build_manifest_index(manifest):
    entries = manifest.get("entries")

    if not isinstance(entries, list):
        raise RuntimeError(
            "EXP006 manifest entries missing"
        )

    index = {}

    for entry in entries:
        key = (
            entry.get("currency"),
            entry.get("date"),
        )

        if key in index:
            raise RuntimeError(
                f"Duplicate manifest entry: {key}"
            )

        index[key] = entry

    return index


def main():
    if not PREREG.exists():
        raise RuntimeError(
            f"Missing EXP007 preregistration: {PREREG}"
        )

    if not EXP006_MANIFEST.exists():
        raise RuntimeError(
            f"Missing frozen EXP006 manifest: "
            f"{EXP006_MANIFEST}"
        )

    if OUT_ROOT.exists():
        raise RuntimeError(
            f"Refusing to overwrite existing "
            f"EXP007-P0 result directory: {OUT_ROOT}"
        )

    # Explicit sealed-August guard on all frozen date lists.
    all_dates = set(SUPERVISED_DAYS)

    for context_day, target_day in CONTEXT_PAIRS:
        all_dates.add(context_day)
        all_dates.add(target_day)

    if any(
        day >= "2026-08-01"
        for day in all_dates
    ):
        raise RuntimeError(
            "SEALED_AUGUST_DATE_REFUSED"
        )

    if set(all_dates) != set(EXPECTED_ALL_DATES):
        raise RuntimeError(
            "Frozen EXP007 date set changed"
        )

    manifest = json.loads(
        EXP006_MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    manifest_index = build_manifest_index(
        manifest
    )

    expected_manifest_keys = {
        (currency, day)
        for currency in CURRENCIES
        for day in EXPECTED_ALL_DATES
    }

    if (
        set(manifest_index.keys())
        != expected_manifest_keys
    ):
        raise RuntimeError(
            "EXP006 manifest symbol/day set "
            "does not exactly match frozen EXP007 set"
        )

    print("=" * 112)
    print(
        "CODEX-EXP-007-P0 — "
        "MAINTENANCE-AWARE CAUSAL DVOL SUPPORT AUDIT"
    )
    print(
        "READ FROZEN EXP006 ARTIFACTS ONLY — "
        "NO NETWORK — NO TARGET — NO MODEL — "
        "NO DIRECTION — NO PNL — NO AUGUST"
    )
    print("=" * 112)

    hash_checks = []
    loaded = {}

    print()
    print("===== IMMUTABLE HASH VERIFICATION =====")

    for currency in CURRENCIES:
        for day_s in EXPECTED_ALL_DATES:
            entry = manifest_index[
                (currency, day_s)
            ]

            path, data = load_raw(
                currency,
                day_s,
            )

            actual_sha = sha256_file(path)
            expected_sha = entry.get(
                "canonical_sha256"
            )

            passed = (
                isinstance(expected_sha, str)
                and actual_sha == expected_sha
            )

            hash_checks.append(
                {
                    "currency": currency,
                    "date": day_s,
                    "path": str(
                        path.relative_to(ROOT)
                    ),
                    "expected_sha256":
                        expected_sha,
                    "actual_sha256":
                        actual_sha,
                    "pass": passed,
                }
            )

            loaded[
                (currency, day_s)
            ] = data

            print(
                f"{currency:3s} {day_s} "
                f"hash={'PASS' if passed else 'FAIL'} "
                f"{actual_sha}"
            )

    all_hashes_pass = all(
        item["pass"]
        for item in hash_checks
    )

    supervised_checks = []

    print()
    print("===== SUPERVISED DAY SUPPORT =====")

    for currency in CURRENCIES:
        for day_s in SUPERVISED_DAYS:
            rows = loaded[
                (currency, day_s)
            ]

            timestamps = [
                row[0]
                for row in rows
                if (
                    isinstance(row, list)
                    and len(row) >= 1
                    and isinstance(row[0], int)
                    and not isinstance(row[0], bool)
                )
            ]

            expected_ts = (
                expected_full_day_timestamps(
                    day_s
                )
            )

            exact_rows = (
                len(rows)
                == EXPECTED_DAY_ROWS
            )

            unique_ts = (
                len(set(timestamps))
                == EXPECTED_DAY_ROWS
            )

            exact_timestamp_set = (
                sorted(timestamps)
                == expected_ts
            )

            consecutive_60s = (
                len(timestamps)
                == EXPECTED_DAY_ROWS
                and all(
                    b - a == MINUTE_MS
                    for a, b in zip(
                        sorted(timestamps),
                        sorted(timestamps)[1:],
                    )
                )
            )

            ohlc_valid = (
                len(rows)
                == EXPECTED_DAY_ROWS
                and all(
                    validate_ohlc_row(row)
                    for row in rows
                )
            )

            passed = all(
                (
                    exact_rows,
                    unique_ts,
                    exact_timestamp_set,
                    consecutive_60s,
                    ohlc_valid,
                )
            )

            supervised_checks.append(
                {
                    "currency": currency,
                    "date": day_s,
                    "rows": len(rows),
                    "exactly_1440_rows":
                        exact_rows,
                    "exactly_1440_unique_timestamps":
                        unique_ts,
                    "exact_full_day_timestamp_set":
                        exact_timestamp_set,
                    "all_adjacent_60_seconds":
                        consecutive_60s,
                    "ohlc_valid":
                        ohlc_valid,
                    "pass": passed,
                }
            )

            print(
                f"{currency:3s} {day_s} "
                f"rows={len(rows):4d} "
                f"full_day="
                f"{'PASS' if exact_timestamp_set else 'FAIL'} "
                f"ohlc="
                f"{'PASS' if ohlc_valid else 'FAIL'} "
                f"status={'PASS' if passed else 'FAIL'}"
            )

    all_supervised_pass = all(
        item["pass"]
        for item in supervised_checks
    )

    boundary_checks = []

    print()
    print("===== CONTEXT MIDNIGHT SUPPORT =====")

    for currency in CURRENCIES:
        for context_day, target_day in CONTEXT_PAIRS:
            rows = loaded[
                (currency, context_day)
            ]

            row_by_ts = {}

            for row in rows:
                if (
                    isinstance(row, list)
                    and len(row) >= 1
                    and isinstance(row[0], int)
                    and not isinstance(row[0], bool)
                ):
                    row_by_ts[row[0]] = row

            required = expected_context_tail(
                context_day
            )

            missing_required = [
                ts
                for ts in required
                if ts not in row_by_ts
            ]

            required_rows = [
                row_by_ts[ts]
                for ts in required
                if ts in row_by_ts
            ]

            all_31_present = (
                len(missing_required) == 0
                and len(required_rows)
                == TAIL_MINUTES
            )

            consecutive_60s = (
                all_31_present
                and all(
                    b - a == MINUTE_MS
                    for a, b in zip(
                        required,
                        required[1:],
                    )
                )
            )

            ohlc_valid = (
                all_31_present
                and all(
                    validate_ohlc_row(row)
                    for row in required_rows
                )
            )

            target_midnight = ms(
                parse_day(target_day)
            )

            correct_boundary_end = (
                required[-1]
                == target_midnight
                - MINUTE_MS
            )

            no_gap_intersects_support = (
                all_31_present
            )

            passed = all(
                (
                    all_31_present,
                    consecutive_60s,
                    ohlc_valid,
                    correct_boundary_end,
                    no_gap_intersects_support,
                )
            )

            boundary_checks.append(
                {
                    "currency": currency,
                    "context_day":
                        context_day,
                    "target_day":
                        target_day,
                    "required_start_timestamp":
                        required[0],
                    "required_end_timestamp":
                        required[-1],
                    "required_count":
                        len(required),
                    "missing_required_count":
                        len(missing_required),
                    "missing_required_timestamps":
                        missing_required,
                    "all_31_required_present":
                        all_31_present,
                    "required_timestamps_consecutive_60s":
                        consecutive_60s,
                    "required_ohlc_valid":
                        ohlc_valid,
                    "required_end_is_t_minus_1m":
                        correct_boundary_end,
                    "maintenance_gap_intersects_required_support":
                        not no_gap_intersects_support,
                    "pass":
                        passed,
                }
            )

            print(
                f"{currency:3s} "
                f"{context_day} -> {target_day} "
                f"required=31 "
                f"missing={len(missing_required):2d} "
                f"ohlc={'PASS' if ohlc_valid else 'FAIL'} "
                f"status={'PASS' if passed else 'FAIL'}"
            )

    all_boundary_pass = all(
        item["pass"]
        for item in boundary_checks
    )

    invariants = {
        "frozen_exp006_raw_hashes_unchanged":
            all_hashes_pass,

        "all_10_supervised_symbol_days_complete":
            (
                len(supervised_checks) == 10
                and all_supervised_pass
            ),

        "all_10_context_midnight_tails_complete":
            (
                len(boundary_checks) == 10
                and all_boundary_pass
            ),

        "no_maintenance_gap_intersects_required_cross_midnight_support":
            all(
                not item[
                    "maintenance_gap_intersects_required_support"
                ]
                for item in boundary_checks
            ),

        "no_august_accessed":
            True,

        "no_network_used":
            True,

        "target_scored":
            False,

        "future_returns_inspected":
            False,

        "model_fit":
            False,

        "auc_scored":
            False,

        "average_precision_scored":
            False,

        "direction_scored":
            False,

        "pnl_scored":
            False,
    }

    positive_gate_values = (
        invariants[
            "frozen_exp006_raw_hashes_unchanged"
        ],
        invariants[
            "all_10_supervised_symbol_days_complete"
        ],
        invariants[
            "all_10_context_midnight_tails_complete"
        ],
        invariants[
            "no_maintenance_gap_intersects_required_cross_midnight_support"
        ],
        invariants[
            "no_august_accessed"
        ],
        invariants[
            "no_network_used"
        ],
    )

    negative_activity_values = (
        invariants["target_scored"],
        invariants[
            "future_returns_inspected"
        ],
        invariants["model_fit"],
        invariants["auc_scored"],
        invariants[
            "average_precision_scored"
        ],
        invariants["direction_scored"],
        invariants["pnl_scored"],
    )

    final_pass = (
        all(positive_gate_values)
        and not any(
            negative_activity_values
        )
    )

    status = (
        "DATA_READY_MAINTENANCE_AWARE_DVOL_SANDBOX"
        if final_pass
        else "FAIL_MAINTENANCE_AWARE_DVOL_SUPPORT"
    )

    result = {
        "experiment_id":
            EXPERIMENT_ID,

        "status":
            status,

        "preregistration_path":
            str(
                PREREG.relative_to(ROOT)
            ),

        "preregistration_sha256":
            sha256_file(PREREG),

        "implementation_path":
            str(
                Path(__file__).resolve().relative_to(ROOT)
            ),

        "implementation_sha256":
            sha256_file(
                Path(__file__).resolve()
            ),

        "frozen_exp006_manifest_path":
            str(
                EXP006_MANIFEST.relative_to(ROOT)
            ),

        "frozen_exp006_manifest_sha256":
            sha256_file(
                EXP006_MANIFEST
            ),

        "maximum_dvol_lookback_minutes":
            30,

        "availability_lag_seconds":
            60,

        "required_cross_midnight_context_minutes":
            31,

        "supervised_days":
            list(SUPERVISED_DAYS),

        "context_pairs":
            [
                {
                    "context_day": a,
                    "target_day": b,
                }
                for a, b in CONTEXT_PAIRS
            ],

        "invariants":
            invariants,

        "raw_hash_checks":
            hash_checks,

        "supervised_day_checks":
            supervised_checks,

        "context_boundary_checks":
            boundary_checks,
    }

    OUT_ROOT.mkdir(parents=True)

    result_bytes = canonical_json_bytes(
        result
    )

    RESULT_PATH.write_bytes(
        result_bytes
    )

    print()
    print("=" * 112)
    print("EXP007-P0 FINAL")
    print("=" * 112)

    print(
        f"status                              : "
        f"{status}"
    )

    print(
        "raw_hashes_unchanged                : "
        f"{all_hashes_pass}"
    )

    print(
        "supervised_symbol_days_complete     : "
        f"{len(supervised_checks)}/10 "
        f"pass={all_supervised_pass}"
    )

    print(
        "context_midnight_tails_complete     : "
        f"{len(boundary_checks)}/10 "
        f"pass={all_boundary_pass}"
    )

    print(
        "maintenance_gap_hits_required_tail  : "
        f"{any(item['maintenance_gap_intersects_required_support'] for item in boundary_checks)}"
    )

    print(
        "sealed_august_opened                : "
        "False"
    )

    print(
        "network_used                        : "
        "False"
    )

    print(
        "target_scored                       : "
        "False"
    )

    print(
        "model_fit                           : "
        "False"
    )

    print(
        "auc_scored                          : "
        "False"
    )

    print(
        "direction_scored                    : "
        "False"
    )

    print(
        "pnl_scored                          : "
        "False"
    )

    print(
        "result_sha256                       : "
        f"{sha256_bytes(result_bytes)}"
    )

    print(
        "result                              : "
        f"{RESULT_PATH.relative_to(ROOT)}"
    )

    print("=" * 112)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except Exception as exc:
        print(
            f"\nFATAL_EXP007_P0_AUDIT_ERROR: {exc}",
            file=sys.stderr,
        )
        raise

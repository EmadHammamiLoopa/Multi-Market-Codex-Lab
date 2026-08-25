#!/usr/bin/env python3

import hashlib
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


EXPERIMENT_ID = "CODEX-EXP-006-P0"
SOURCE_ID = "deribit_public_get_volatility_index_data"
BASE_URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"

CURRENCIES = ("BTC", "ETH")

REQUIRED_DATES = (
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

CONTEXT_TARGET_PAIRS = (
    ("2026-02-28", "2026-03-01"),
    ("2026-03-31", "2026-04-01"),
    ("2026-04-30", "2026-05-01"),
    ("2026-05-31", "2026-06-01"),
    ("2026-06-30", "2026-07-01"),
)

RESOLUTION = "60"
EXPECTED_ROWS = 1440
MINUTE_MS = 60_000

SEALED_AUGUST_START = datetime(
    2026, 8, 1, tzinfo=timezone.utc
)

ROOT = Path(__file__).resolve().parents[1]

PREREG = ROOT / "docs" / "CODEX_EXP006_P0_PREREGISTRATION.md"

OUT_ROOT = ROOT / "evidence" / "codex" / "exp006_p0_dvol"
RAW_DIR = OUT_ROOT / "raw"

MANIFEST_PATH = OUT_ROOT / "DVOL_ACQUISITION_MANIFEST.json"
AUDIT_PATH = OUT_ROOT / "DVOL_P0_AUDIT.json"


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
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ms(dt):
    return int(dt.timestamp() * 1000)


def dt_from_ms(value):
    return datetime.fromtimestamp(
        value / 1000,
        tz=timezone.utc,
    )


def parse_day(day_s):
    return datetime.strptime(
        day_s,
        "%Y-%m-%d",
    ).replace(tzinfo=timezone.utc)


def percentile(values, p):
    if not values:
        return None

    xs = sorted(float(x) for x in values)

    if len(xs) == 1:
        return xs[0]

    pos = (len(xs) - 1) * p
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))

    if lo == hi:
        return xs[lo]

    weight = pos - lo
    return xs[lo] * (1.0 - weight) + xs[hi] * weight


def assert_unsealed_interval(start_ms, end_ms):
    sealed_ms = ms(SEALED_AUGUST_START)

    if start_ms >= sealed_ms or end_ms >= sealed_ms:
        raise RuntimeError(
            "SEALED_AUGUST_ACCESS_REFUSED"
        )


def fetch_page(currency, start_ms, end_ms):
    assert currency in CURRENCIES
    assert_unsealed_interval(start_ms, end_ms)

    params = urllib.parse.urlencode(
        {
            "currency": currency,
            "start_timestamp": start_ms,
            "end_timestamp": end_ms,
            "resolution": RESOLUTION,
        }
    )

    url = BASE_URL + "?" + params

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Multi-Market-Research/CODEX-EXP-006-P0"
        },
    )

    last_exc = None

    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(
                req,
                timeout=30,
            ) as response:
                payload = json.load(response)

            if "error" in payload:
                raise RuntimeError(
                    f"Deribit API error: {payload['error']}"
                )

            result = payload.get("result")

            if not isinstance(result, dict):
                raise RuntimeError(
                    "Deribit result is not an object"
                )

            return result

        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
        ) as exc:
            last_exc = exc

            if attempt == 4:
                break

            time.sleep(1.5 * attempt)

    raise RuntimeError(
        f"Network request failed after retries: {last_exc}"
    )


def acquire_full_day(currency, day_s):
    day = parse_day(day_s)

    start_ms = ms(day)
    original_end_ms = ms(day + timedelta(days=1)) - 1

    assert_unsealed_interval(
        start_ms,
        original_end_ms,
    )

    end_ms = original_end_ms

    pages = []
    rows = []
    seen_end_values = set()

    while True:
        if end_ms in seen_end_values:
            raise RuntimeError(
                f"Pagination loop detected "
                f"{currency} {day_s}"
            )

        seen_end_values.add(end_ms)

        result = fetch_page(
            currency,
            start_ms,
            end_ms,
        )

        page_rows = result.get("data", [])
        continuation = result.get("continuation")

        if not isinstance(page_rows, list):
            raise RuntimeError(
                f"data is not a list: "
                f"{currency} {day_s}"
            )

        rows.extend(page_rows)

        pages.append(
            {
                "request_end_timestamp": end_ms,
                "rows_returned": len(page_rows),
                "continuation": continuation,
            }
        )

        if continuation is None:
            break

        if not isinstance(continuation, int):
            raise RuntimeError(
                f"Non-integer continuation: "
                f"{currency} {day_s}"
            )

        if continuation >= end_ms:
            raise RuntimeError(
                f"Non-decreasing continuation: "
                f"{currency} {day_s}: "
                f"{continuation} >= {end_ms}"
            )

        end_ms = continuation

        if len(pages) > 20:
            raise RuntimeError(
                f"Unexpected pagination depth: "
                f"{currency} {day_s}"
            )

        time.sleep(0.12)

    return rows, pages


def is_number(x):
    return (
        isinstance(x, (int, float))
        and not isinstance(x, bool)
    )


def audit_rows(currency, day_s, rows, pages):
    day = parse_day(day_s)

    expected_first = ms(day)
    expected_last = (
        ms(day + timedelta(days=1))
        - MINUTE_MS
    )

    row_length_ok = all(
        isinstance(row, list) and len(row) == 5
        for row in rows
    )

    timestamp_integer_ok = (
        row_length_ok
        and all(
            isinstance(row[0], int)
            and not isinstance(row[0], bool)
            for row in rows
        )
    )

    numerical_ok = (
        row_length_ok
        and all(
            all(is_number(x) for x in row[1:])
            for row in rows
        )
    )

    positive_finite_ok = (
        numerical_ok
        and all(
            math.isfinite(float(x))
            and float(x) > 0.0
            for row in rows
            for x in row[1:]
        )
    )

    ohlc_order_ok = (
        positive_finite_ok
        and all(
            float(row[2])
            >= max(
                float(row[1]),
                float(row[4]),
            )
            and float(row[3])
            <= min(
                float(row[1]),
                float(row[4]),
            )
            and float(row[2])
            >= float(row[3])
            for row in rows
        )
    )

    timestamps = (
        [row[0] for row in rows]
        if timestamp_integer_ok
        else []
    )

    unique_timestamps = set(timestamps)

    sorted_rows = (
        sorted(rows, key=lambda row: row[0])
        if timestamp_integer_ok
        else list(rows)
    )

    sorted_timestamps = (
        [row[0] for row in sorted_rows]
        if timestamp_integer_ok
        else []
    )

    one_minute_spacing_ok = (
        len(sorted_timestamps) >= 2
        and all(
            b - a == MINUTE_MS
            for a, b in zip(
                sorted_timestamps,
                sorted_timestamps[1:],
            )
        )
    )

    checks = {
        "exactly_1440_rows":
            len(rows) == EXPECTED_ROWS,

        "exactly_1440_unique_timestamps":
            len(unique_timestamps) == EXPECTED_ROWS,

        "no_duplicate_timestamps":
            len(unique_timestamps) == len(timestamps),

        "first_timestamp_00_00_utc":
            bool(sorted_timestamps)
            and sorted_timestamps[0] == expected_first,

        "last_timestamp_23_59_utc":
            bool(sorted_timestamps)
            and sorted_timestamps[-1] == expected_last,

        "all_adjacent_timestamps_60_seconds":
            one_minute_spacing_ok,

        "every_row_has_five_fields":
            row_length_ok,

        "timestamp_integer_milliseconds":
            timestamp_integer_ok,

        "ohlc_finite_positive":
            positive_finite_ok,

        "high_ge_open_and_close":
            positive_finite_ok
            and all(
                float(row[2])
                >= max(
                    float(row[1]),
                    float(row[4]),
                )
                for row in rows
            ),

        "low_le_open_and_close":
            positive_finite_ok
            and all(
                float(row[3])
                <= min(
                    float(row[1]),
                    float(row[4]),
                )
                for row in rows
            ),

        "high_ge_low":
            positive_finite_ok
            and all(
                float(row[2])
                >= float(row[3])
                for row in rows
            ),

        "pagination_terminated":
            bool(pages)
            and pages[-1]["continuation"] is None,

        "august_not_accessed":
            True,
    }

    closes = (
        [float(row[4]) for row in sorted_rows]
        if positive_finite_ok
        else []
    )

    close_deltas = [
        b - a
        for a, b in zip(
            closes,
            closes[1:],
        )
    ]

    pct_changes = [
        (b / a - 1.0) * 100.0
        for a, b in zip(
            closes,
            closes[1:],
        )
        if a > 0
    ]

    diagnostics = {}

    if closes:
        diagnostics = {
            "close_min": min(closes),
            "close_max": max(closes),
            "close_mean": statistics.fmean(closes),
            "close_p05": percentile(closes, 0.05),
            "close_p50": percentile(closes, 0.50),
            "close_p95": percentile(closes, 0.95),
            "zero_close_change_fraction":
                (
                    sum(
                        1
                        for d in close_deltas
                        if d == 0.0
                    )
                    / len(close_deltas)
                    if close_deltas
                    else None
                ),
            "max_abs_close_change":
                (
                    max(abs(d) for d in close_deltas)
                    if close_deltas
                    else None
                ),
            "max_abs_close_pct_change":
                (
                    max(abs(d) for d in pct_changes)
                    if pct_changes
                    else None
                ),
        }

    return {
        "currency": currency,
        "date": day_s,
        "row_count_received": len(rows),
        "unique_timestamp_count":
            len(unique_timestamps),
        "page_count": len(pages),
        "first_timestamp":
            (
                sorted_timestamps[0]
                if sorted_timestamps
                else None
            ),
        "last_timestamp":
            (
                sorted_timestamps[-1]
                if sorted_timestamps
                else None
            ),
        "first_timestamp_iso":
            (
                dt_from_ms(
                    sorted_timestamps[0]
                ).isoformat()
                if sorted_timestamps
                else None
            ),
        "last_timestamp_iso":
            (
                dt_from_ms(
                    sorted_timestamps[-1]
                ).isoformat()
                if sorted_timestamps
                else None
            ),
        "checks": checks,
        "descriptive_diagnostics": diagnostics,
        "pass":
            all(checks.values()),
        "sorted_rows": sorted_rows,
    }


def write_canonical_day(
    currency,
    day_s,
    sorted_rows,
):
    obj = {
        "source": SOURCE_ID,
        "currency": currency,
        "date": day_s,
        "resolution_seconds": 60,
        "data": sorted_rows,
    }

    raw = canonical_json_bytes(obj)

    filename = (
        f"{currency}_DVOL_60S_"
        f"{day_s.replace('-', '')}.json"
    )

    path = RAW_DIR / filename

    if path.exists():
        raise RuntimeError(
            f"Refusing to overwrite existing raw artifact: "
            f"{path}"
        )

    path.write_bytes(raw)

    return (
        path,
        sha256_bytes(raw),
        len(raw),
    )


def main():
    if not PREREG.exists():
        raise RuntimeError(
            f"Missing preregistration: {PREREG}"
        )

    if OUT_ROOT.exists():
        raise RuntimeError(
            f"Refusing to overwrite existing P0 output: "
            f"{OUT_ROOT}"
        )

    if any(
        day.startswith("2026-08")
        for day in REQUIRED_DATES
    ):
        raise RuntimeError(
            "SEALED_AUGUST_DATE_IN_FROZEN_LIST"
        )

    OUT_ROOT.mkdir(parents=True)
    RAW_DIR.mkdir()

    prereg_sha = sha256_file(PREREG)

    started = datetime.now(
        timezone.utc
    ).isoformat()

    entries = []
    audits = []
    day_lookup = {}

    print("=" * 112)
    print(
        "CODEX-EXP-006-P0 — "
        "FROZEN DVOL ACQUISITION + DATA AUDIT"
    )
    print(
        "NO MODEL — NO TARGET — NO DIRECTION — "
        "NO PNL — NO AUGUST"
    )
    print("=" * 112)

    for currency in CURRENCIES:
        print()
        print(f"===== {currency} =====")

        for day_s in REQUIRED_DATES:
            rows, pages = acquire_full_day(
                currency,
                day_s,
            )

            audit = audit_rows(
                currency,
                day_s,
                rows,
                pages,
            )

            sorted_rows = audit.pop("sorted_rows")

            path, data_sha, size_bytes = (
                write_canonical_day(
                    currency,
                    day_s,
                    sorted_rows,
                )
            )

            relative_path = str(
                path.relative_to(ROOT)
            )

            entry = {
                "currency": currency,
                "date": day_s,
                "source": SOURCE_ID,
                "resolution_seconds": 60,
                "canonical_path": relative_path,
                "canonical_sha256": data_sha,
                "canonical_size_bytes": size_bytes,
                "pages": pages,
            }

            entries.append(entry)

            audit["canonical_path"] = relative_path
            audit["canonical_sha256"] = data_sha

            audits.append(audit)

            day_lookup[(currency, day_s)] = {
                "rows": sorted_rows,
                "audit": audit,
            }

            print(
                f"{currency:3s} {day_s} "
                f"rows={audit['row_count_received']:4d} "
                f"unique={audit['unique_timestamp_count']:4d} "
                f"pages={audit['page_count']:2d} "
                f"status={'PASS' if audit['pass'] else 'FAIL'} "
                f"sha256={data_sha}"
            )

            time.sleep(0.12)

    boundary_checks = []

    for currency in CURRENCIES:
        for context_day, target_day in CONTEXT_TARGET_PAIRS:
            left = day_lookup[
                (currency, context_day)
            ]["rows"]

            right = day_lookup[
                (currency, target_day)
            ]["rows"]

            timestamp_continuity = (
                bool(left)
                and bool(right)
                and int(right[0][0])
                - int(left[-1][0])
                == MINUTE_MS
            )

            close_to_open_change = None

            if left and right:
                prior_close = float(left[-1][4])
                next_open = float(right[0][1])

                if prior_close > 0:
                    close_to_open_change = (
                        next_open / prior_close - 1.0
                    ) * 100.0

            boundary_checks.append(
                {
                    "currency": currency,
                    "context_day": context_day,
                    "target_day": target_day,
                    "timestamp_continuity_60_seconds":
                        timestamp_continuity,
                    "context_last_close_to_target_first_open_pct":
                        close_to_open_change,
                }
            )

    all_day_pass = all(
        item["pass"]
        for item in audits
    )

    all_boundary_timestamp_pass = all(
        item["timestamp_continuity_60_seconds"]
        for item in boundary_checks
    )

    final_status = (
        "DATA_READY_DVOL_SANDBOX"
        if (
            len(audits) == 20
            and all_day_pass
            and all_boundary_timestamp_pass
        )
        else "FAIL_DVOL_DATA_NOT_CAUSALLY_USABLE"
    )

    finished = datetime.now(
        timezone.utc
    ).isoformat()

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "source": SOURCE_ID,
        "endpoint": BASE_URL,
        "resolution_seconds": 60,
        "currencies": list(CURRENCIES),
        "required_dates": list(REQUIRED_DATES),
        "expected_symbol_day_count": 20,
        "actual_symbol_day_count": len(entries),
        "preregistration_path":
            str(PREREG.relative_to(ROOT)),
        "preregistration_sha256":
            prereg_sha,
        "acquisition_started_at_utc":
            started,
        "acquisition_finished_at_utc":
            finished,
        "sealed_august_opened": False,
        "entries": entries,
    }

    manifest_bytes = canonical_json_bytes(
        manifest
    )

    MANIFEST_PATH.write_bytes(
        manifest_bytes
    )

    audit_result = {
        "experiment_id": EXPERIMENT_ID,
        "status": final_status,
        "preregistration_sha256":
            prereg_sha,
        "expected_symbol_day_count": 20,
        "actual_symbol_day_count":
            len(audits),
        "all_required_day_checks_pass":
            all_day_pass,
        "all_context_target_timestamp_boundaries_pass":
            all_boundary_timestamp_pass,
        "sealed_august_opened": False,
        "target_scored": False,
        "model_fit": False,
        "direction_scored": False,
        "pnl_scored": False,
        "day_audits": audits,
        "context_target_boundary_diagnostics":
            boundary_checks,
        "manifest_sha256":
            sha256_bytes(manifest_bytes),
    }

    audit_bytes = canonical_json_bytes(
        audit_result
    )

    AUDIT_PATH.write_bytes(
        audit_bytes
    )

    print()
    print("=" * 112)
    print("P0 FINAL")
    print("=" * 112)
    print(f"status                     : {final_status}")
    print(f"symbol_days                : {len(audits)}/20")
    print(f"all_day_checks_pass        : {all_day_pass}")
    print(
        "boundary_timestamp_pass    : "
        f"{all_boundary_timestamp_pass}"
    )
    print("sealed_august_opened       : False")
    print("target_scored              : False")
    print("model_fit                  : False")
    print("direction_scored           : False")
    print("pnl_scored                 : False")
    print(
        "manifest_sha256            : "
        f"{sha256_bytes(manifest_bytes)}"
    )
    print(
        "audit_sha256               : "
        f"{sha256_bytes(audit_bytes)}"
    )
    print(
        f"manifest                    : "
        f"{MANIFEST_PATH.relative_to(ROOT)}"
    )
    print(
        f"audit                       : "
        f"{AUDIT_PATH.relative_to(ROOT)}"
    )
    print("=" * 112)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"\nFATAL_P0_ACQUISITION_ERROR: {exc}",
            file=sys.stderr,
        )
        raise

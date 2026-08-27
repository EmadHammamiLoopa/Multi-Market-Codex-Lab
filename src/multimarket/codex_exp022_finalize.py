from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "CODEX-EXP-022-P0"
STATUS_PASS = "PROSPECTIVE_BOOKTICKER_DATA_READY"
STATUS_FAIL = "FAIL_PROSPECTIVE_BOOKTICKER_DATA_INTEGRITY"
STATUS_INVALID = "INVALID"

SYMBOL = "BTCUSDT"
DAY_START_US = int(
    datetime(2026, 8, 28, tzinfo=timezone.utc).timestamp() * 1_000_000
)
DAY_END_US = DAY_START_US + 86_400_000_000
GRID_US = 250_000
EXPECTED_ROWS = 345_600
MAX_AGE_US = 2_000_000

RAW_DEFAULT = Path(
    "/home/emadh/Multi-Market/data/codex_exp022/"
    "bookticker/BTCUSDT/2026-08-28.jsonl.gz"
)
GRID_DEFAULT = Path(
    "/home/emadh/Multi-Market/evidence/codex/"
    "exp022_prospective_bookticker/BTCUSDT/"
    "2026-08-28_BOOKTICKER250.csv"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _wall_us(record: dict[str, Any]) -> int:
    return int(record["receive_wall_ns"]) // 1000


def _valid_quote_record(r: dict[str, Any]) -> bool:
    if r.get("record_type") != "quote":
        return False
    if r.get("symbol") != SYMBOL:
        return False
    vals = (
        float(r["best_bid"]),
        float(r["best_ask"]),
        float(r["best_bid_qty"]),
        float(r["best_ask_qty"]),
    )
    if not all(math.isfinite(x) for x in vals):
        return False
    bid, ask, bq, aq = vals
    return bid > 0 and ask > bid and bq >= 0 and aq >= 0


def load_raw(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    quotes: list[dict[str, Any]] = []
    rejected = 0
    transports = 0
    wall_reversals = 0
    mono_reversals = 0
    wrong_symbol_accepted = 0
    invalid_price_accepted = 0
    negative_qty_accepted = 0
    last_wall: int | None = None
    last_mono: int | None = None

    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            r = json.loads(line)

            if r.get("record_type") == "rejected":
                rejected += 1
                continue
            if r.get("record_type") == "transport":
                transports += 1
                continue
            if r.get("record_type") != "quote":
                continue

            wall = int(r["receive_wall_ns"])
            mono = int(r["receive_monotonic_ns"])

            if last_wall is not None and wall < last_wall:
                wall_reversals += 1
            if last_mono is not None and mono < last_mono:
                mono_reversals += 1
            last_wall = wall
            last_mono = mono

            if r.get("symbol") != SYMBOL:
                wrong_symbol_accepted += 1

            bid = float(r["best_bid"])
            ask = float(r["best_ask"])
            bq = float(r["best_bid_qty"])
            aq = float(r["best_ask_qty"])

            if not (math.isfinite(bid) and math.isfinite(ask)) or not (
                bid > 0 and ask > bid
            ):
                invalid_price_accepted += 1
            if not (math.isfinite(bq) and math.isfinite(aq)) or bq < 0 or aq < 0:
                negative_qty_accepted += 1

            quotes.append(r)

    return quotes, {
        "rejected_records": rejected,
        "transport_records": transports,
        "accepted_quotes": len(quotes),
        "accepted_wall_clock_reversals": wall_reversals,
        "accepted_monotonic_clock_reversals": mono_reversals,
        "wrong_symbol_accepted": wrong_symbol_accepted,
        "invalid_price_accepted": invalid_price_accepted,
        "negative_quantity_accepted": negative_qty_accepted,
    }


def build_grid(
    quotes: list[dict[str, Any]],
    output: Path,
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".part")
    if tmp.exists():
        tmp.unlink()

    quote_idx = 0
    latest: dict[str, Any] | None = None
    valid_rows = 0
    future_quote_violations = 0
    stale_rows = 0
    reconnect_invalid_rows = 0

    # Sort by local causal receive timestamp only.
    quotes = sorted(
        quotes,
        key=lambda r: (
            int(r["receive_wall_ns"]),
            int(r["receive_monotonic_ns"]),
        ),
    )

    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "local_timestamp_us",
                "best_bid",
                "best_ask",
                "mid",
                "book_valid",
                "quote_age_ms",
                "connection_epoch",
                "source_update_id",
                "exchange_event_time_ms",
                "exchange_transaction_time_ms",
            ]
        )

        for i in range(EXPECTED_ROWS):
            ts_us = DAY_START_US + i * GRID_US

            while quote_idx < len(quotes):
                q = quotes[quote_idx]
                q_us = _wall_us(q)
                if q_us > ts_us:
                    break
                latest = q
                quote_idx += 1

            valid = False
            bid = ask = mid = float("nan")
            age_ms = float("nan")
            epoch = ""
            update_id = ""
            event_ms = ""
            trans_ms = ""

            if latest is not None:
                q_us = _wall_us(latest)
                if q_us > ts_us:
                    future_quote_violations += 1
                else:
                    age_us = ts_us - q_us
                    age_ms = age_us / 1000.0
                    if age_us <= MAX_AGE_US and _valid_quote_record(latest):
                        valid = True
                        bid = float(latest["best_bid"])
                        ask = float(latest["best_ask"])
                        mid = (bid + ask) / 2.0
                        epoch = int(latest["connection_epoch"])
                        update_id = latest.get("update_id", "")
                        event_ms = latest.get("exchange_event_time_ms", "")
                        trans_ms = latest.get(
                            "exchange_transaction_time_ms",
                            "",
                        )
                        valid_rows += 1
                    else:
                        stale_rows += 1

            w.writerow(
                [
                    ts_us,
                    bid,
                    ask,
                    mid,
                    1 if valid else 0,
                    age_ms,
                    epoch,
                    update_id,
                    event_ms,
                    trans_ms,
                ]
            )

    tmp.replace(output)

    return {
        "rows": EXPECTED_ROWS,
        "valid_rows": valid_rows,
        "valid_coverage": valid_rows / EXPECTED_ROWS,
        "future_quote_violations": future_quote_violations,
        "stale_or_unavailable_rows": stale_rows,
        "reconnect_invalid_rows": reconnect_invalid_rows,
        "first_timestamp_us": DAY_START_US,
        "last_timestamp_us": DAY_START_US + (EXPECTED_ROWS - 1) * GRID_US,
        "grid_step_us": GRID_US,
    }


def run(raw: Path, grid: Path, audit: Path) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    day_end = datetime(2026, 8, 29, tzinfo=timezone.utc)
    if now < day_end:
        raise RuntimeError(
            "cannot finalize EXP022 before 2026-08-29T00:00:00Z"
        )
    if not raw.is_file() or raw.stat().st_size == 0:
        raise RuntimeError("raw prospective file missing or empty")
    if audit.exists() or audit.with_suffix(audit.suffix + ".part").exists():
        raise RuntimeError("EXP022 audit output already exists")
    if grid.exists() or grid.with_suffix(grid.suffix + ".part").exists():
        raise RuntimeError("EXP022 finalized grid already exists")

    quotes, raw_diag = load_raw(raw)
    grid_diag = build_grid(quotes, grid)

    raw_sha = sha256_file(raw)
    grid_sha = sha256_file(grid)

    gates = {
        "raw_file_nonempty": raw.stat().st_size > 0,
        "grid_rows_exact_345600": grid_diag["rows"] == EXPECTED_ROWS,
        "grid_step_exact_250000us": grid_diag["grid_step_us"] == GRID_US,
        "first_timestamp_exact": grid_diag["first_timestamp_us"] == DAY_START_US,
        "last_timestamp_exact": (
            grid_diag["last_timestamp_us"]
            == DAY_START_US + (EXPECTED_ROWS - 1) * GRID_US
        ),
        "valid_coverage_at_least_0_99": grid_diag["valid_coverage"] >= 0.99,
        "no_invalid_crossed_price_accepted": (
            raw_diag["invalid_price_accepted"] == 0
        ),
        "no_negative_quantity_accepted": (
            raw_diag["negative_quantity_accepted"] == 0
        ),
        "no_accepted_wall_clock_reversal": (
            raw_diag["accepted_wall_clock_reversals"] == 0
        ),
        "no_accepted_monotonic_clock_reversal": (
            raw_diag["accepted_monotonic_clock_reversals"] == 0
        ),
        "no_other_symbol_accepted": raw_diag["wrong_symbol_accepted"] == 0,
        "no_future_quote_used": grid_diag["future_quote_violations"] == 0,
        "raw_sha_recorded": len(raw_sha) == 64,
        "grid_sha_recorded": len(grid_sha) == 64,
        "older_august_holdout_opened": False,
        "historical_aug1_feature_reparsed": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
    }

    expected_false = {
        "older_august_holdout_opened",
        "historical_aug1_feature_reparsed",
        "target_scored",
        "model_fit",
        "auc_scored",
        "direction_scored",
        "pnl_scored",
    }

    integrity_pass = all(
        (v is False if k in expected_false else v is True)
        for k, v in gates.items()
    )

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "status": STATUS_PASS if integrity_pass else STATUS_FAIL,
        "collection_day": "2026-08-28",
        "symbol": SYMBOL,
        "raw_path": str(raw),
        "grid_path": str(grid),
        "raw_bytes": raw.stat().st_size,
        "grid_bytes": grid.stat().st_size,
        "raw_sha256": raw_sha,
        "grid_sha256": grid_sha,
        "raw_diagnostics": raw_diag,
        "grid_diagnostics": grid_diag,
        "integrity_gates": gates,
        "network_accessed_for_acquisition": True,
        "older_august_holdout_opened": False,
        "historical_aug1_feature_reparsed": False,
        "target_scored": False,
        "model_fit": False,
        "auc_scored": False,
        "direction_scored": False,
        "pnl_scored": False,
    }

    audit.parent.mkdir(parents=True, exist_ok=True)
    part = audit.with_suffix(audit.suffix + ".part")
    part.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    part.replace(audit)
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--raw", type=Path, default=RAW_DEFAULT)
    p.add_argument("--grid", type=Path, default=GRID_DEFAULT)
    p.add_argument("--audit", type=Path, required=True)
    a = p.parse_args(argv)

    try:
        result = run(a.raw, a.grid, a.audit)
    except Exception as exc:
        result = {
            "experiment_id": EXPERIMENT_ID,
            "status": STATUS_INVALID,
            "failure_type": type(exc).__name__,
            "failure_message": str(exc),
            "older_august_holdout_opened": False,
            "historical_aug1_feature_reparsed": False,
            "target_scored": False,
            "model_fit": False,
            "auc_scored": False,
            "direction_scored": False,
            "pnl_scored": False,
        }
        a.audit.parent.mkdir(parents=True, exist_ok=True)
        part = a.audit.with_suffix(a.audit.suffix + ".part")
        part.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        part.replace(a.audit)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

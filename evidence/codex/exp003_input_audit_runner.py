from __future__ import annotations

import argparse
import gc
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import multimarket.codex_exp003 as exp
from multimarket.codex_research import canonical_sha256, sha256_file


def quantiles(values: np.ndarray) -> dict[str, float | int | None]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if not len(finite):
        return {
            "count": 0,
            "minimum": None,
            "p01": None,
            "p05": None,
            "p50": None,
            "p95": None,
            "p99": None,
            "maximum": None,
            "mean": None,
        }
    return {
        "count": int(len(finite)),
        "minimum": float(np.min(finite)),
        "p01": float(np.quantile(finite, 0.01)),
        "p05": float(np.quantile(finite, 0.05)),
        "p50": float(np.quantile(finite, 0.50)),
        "p95": float(np.quantile(finite, 0.95)),
        "p99": float(np.quantile(finite, 0.99)),
        "maximum": float(np.max(finite)),
        "mean": float(np.mean(finite)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-dir", type=Path, required=True)
    parser.add_argument("--external-root", type=Path, required=True)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    acquisition = json.loads(args.acquisition_manifest.read_text(encoding="utf-8"))
    if acquisition.get("frozen_commit") != (
        "e6109a78c7ec9ed74364260732e63252030bb735"
    ):
        raise RuntimeError("acquisition manifest frozen commit mismatch")
    if acquisition.get("sealed_august_opened") is not False:
        raise RuntimeError("sealed-August declaration is not false")
    if len(acquisition.get("files", [])) != 56:
        raise RuntimeError("expected exactly 56 acquisition records")

    acquisition_by_key = {
        (record["exchange"], record["symbol"], record["day"], record["data_type"]): record
        for record in acquisition["files"]
    }
    parser_audits: dict[tuple[str, str, str, str], dict[str, object]] = {}
    coverage: list[dict[str, object]] = []
    asymmetry: list[dict[str, object]] = []

    for symbol in exp.SYMBOLS:
        for day in exp.DAYS:
            base_path = args.feature_dir / symbol / f"{day.isoformat()}_FEATURES250.csv"
            base = exp._load_day(base_path, day)
            built: dict[str, exp.ExternalFeatures] = {}
            row_counts: dict[str, dict[str, int]] = {}
            source_coverage: dict[str, dict[str, object]] = {}

            for source in exp.SOURCE_EXCHANGES:
                book_path, trade_path = exp.external_paths(
                    args.external_root, source, symbol, day
                )
                book = exp.load_book_snapshot_5(
                    book_path, exchange=source, symbol=symbol, day=day
                )
                trades = exp.load_trades(
                    trade_path, exchange=source, symbol=symbol, day=day
                )
                if int(np.sum(np.diff(book.local_timestamp_us) < 0)) != 0:
                    raise RuntimeError(f"book local timestamp regression: {book_path}")
                if int(np.sum(np.diff(trades.local_timestamp_us) < 0)) != 0:
                    raise RuntimeError(f"trade local timestamp regression: {trade_path}")

                book_audit = dict(book.audit)
                book_audit.update(
                    {
                        "local_timestamp_regressions": 0,
                        "continuity_gaps_over_2000ms": int(
                            np.sum(np.diff(book.local_timestamp_us) > exp.GAP_BREAK_US)
                        ),
                        "malformed_rows": int(book.audit["invalid_rows"]),
                    }
                )
                trade_audit = dict(trades.audit)
                trade_audit.update(
                    {
                        "local_timestamp_regressions": 0,
                        "continuity_gaps_over_2000ms": int(
                            np.sum(np.diff(trades.local_timestamp_us) > exp.GAP_BREAK_US)
                        ),
                        "malformed_rows": 0,
                    }
                )
                parser_audits[(source, symbol, day.isoformat(), "book_snapshot_5")] = book_audit
                parser_audits[(source, symbol, day.isoformat(), "trades")] = trade_audit
                row_counts[source] = {
                    "book_snapshot_5": int(book.audit["raw_rows"]),
                    "trades": int(trades.audit["raw_rows"]),
                }

                external = exp.build_external_features(
                    base.ts,
                    base.mid,
                    base.book_valid,
                    book,
                    trades,
                    delay_us=exp.PRIMARY_DELAY_US,
                    canary=False,
                )
                built[source] = external
                source_coverage[source] = {
                    "valid_rows": int(external.valid.sum()),
                    "valid_fraction": float(external.valid.mean()),
                    "source_age_us_on_source_valid_rows": quantiles(
                        external.source_age_us[external.valid]
                    ),
                    "local_timestamp_eligibility_violations": int(
                        external.audit["local_timestamp_eligibility_violations"]
                    ),
                }
                del book, trades

            common = base.valid["L2"] & built["binance"].valid & built["bybit"].valid
            common_record: dict[str, object] = {
                "symbol": symbol,
                "day": day.isoformat(),
                "decision_rows": int(len(common)),
                "base_l2_valid_rows": int(base.valid["L2"].sum()),
                "common_support_rows": int(common.sum()),
                "common_support_fraction": float(common.mean()),
                "sources": source_coverage,
            }
            for source in exp.SOURCE_EXCHANGES:
                common_record[f"{source}_source_age_us_on_common_support"] = quantiles(
                    built[source].source_age_us[common]
                )
            coverage.append(common_record)

            asymmetry.append(
                {
                    "symbol": symbol,
                    "day": day.isoformat(),
                    "bybit_to_binance_book_row_ratio": (
                        row_counts["bybit"]["book_snapshot_5"]
                        / row_counts["binance"]["book_snapshot_5"]
                    ),
                    "bybit_to_binance_trade_row_ratio": (
                        row_counts["bybit"]["trades"]
                        / row_counts["binance"]["trades"]
                    ),
                    "bybit_minus_binance_valid_fraction": (
                        float(source_coverage["bybit"]["valid_fraction"])
                        - float(source_coverage["binance"]["valid_fraction"])
                    ),
                    "common_support_fraction": float(common.mean()),
                }
            )
            del base, built, common
            gc.collect()

    file_records: list[dict[str, object]] = []
    aggregate: defaultdict[str, int] = defaultdict(int)
    for key in sorted(acquisition_by_key):
        source, symbol, day_text, data_type = key
        acquired = acquisition_by_key[key]
        path = args.external_root / source / data_type / symbol / f"{day_text}.csv.gz"
        audit = parser_audits[key]
        digest = sha256_file(path)
        record = {
            "exchange": source,
            "symbol": symbol,
            "day": day_text,
            "data_type": data_type,
            "path": str(path),
            "bytes": path.stat().st_size,
            "rows": acquired["rows"],
            "header": acquired["header"],
            "sha256": digest,
            "acquisition_sha256_match": digest == acquired["sha256"],
            "parser_audit": audit,
        }
        if not record["acquisition_sha256_match"]:
            raise RuntimeError(f"SHA-256 changed after acquisition: {path}")
        if int(audit["raw_rows"]) != int(acquired["rows"]):
            raise RuntimeError(f"row count mismatch: {path}")
        file_records.append(record)
        aggregate["bytes"] += int(record["bytes"])
        aggregate["rows"] += int(record["rows"])
        aggregate["exchange_timestamp_regressions"] += int(
            audit["exchange_timestamp_regressions"]
        )
        aggregate["local_timestamp_regressions"] += int(
            audit["local_timestamp_regressions"]
        )
        aggregate["malformed_rows"] += int(audit["malformed_rows"])
        aggregate["continuity_gaps_over_2000ms"] += int(
            audit["continuity_gaps_over_2000ms"]
        )
        aggregate["duplicate_trade_ids_removed"] += int(
            audit.get("duplicate_trade_ids_removed", 0)
        )

    payload = {
        "experiment_id": exp.EXPERIMENT_ID,
        "audit_phase": "PRE_SCORE_INPUT_AUDIT",
        "frozen_commit": "e6109a78c7ec9ed74364260732e63252030bb735",
        "configuration_sha256": canonical_sha256(exp.ExperimentConfig()),
        "sealed_august_opened": False,
        "profitability_inspected": False,
        "expected_files": 56,
        "observed_files": len(file_records),
        "all_sha256_match_acquisition": all(
            bool(record["acquisition_sha256_match"]) for record in file_records
        ),
        "aggregate": dict(aggregate),
        "files": file_records,
        "common_support_coverage": coverage,
        "venue_date_asymmetry": asymmetry,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(args.output), **payload["aggregate"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from datetime import date, datetime, timezone
import csv
import gzip
from pathlib import Path

import pytest

from multimarket import dev031_p0_event_depth_audit as p0


def _write_fixture(path: Path, day: date) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp()*1_000_000)
    rows = [
        ["binance-futures","BTCUSDT",str(start+1000),str(start+1000),"true","bid","100","2"],
        ["binance-futures","BTCUSDT",str(start+1000),str(start+1000),"true","ask","101","2"],
        ["binance-futures","BTCUSDT",str(start+2000),str(start+2000),"false","bid","99","1"],
        ["binance-futures","BTCUSDT",str(start+3000),str(start+3000),"false","ask","102","1"],
        ["binance-futures","BTCUSDT",str(start+4000),str(start+4000),"false","bid","98","0"],
        ["binance-futures","BTCUSDT",str(start+5000),str(start+5000),"false","ask","103","1"],
        ["binance-futures","BTCUSDT",str(start+6000),str(start+6000),"false","bid","97","1"],
        ["binance-futures","BTCUSDT",str(start+7000),str(start+7000),"false","ask","104","1"],
        ["binance-futures","BTCUSDT",str(start+8000),str(start+8000),"false","bid","96","1"],
        ["binance-futures","BTCUSDT",str(start+9000),str(start+9000),"false","ask","105","1"],
        ["binance-futures","BTCUSDT",str(start+10000),str(start+10000),"false","bid","95","1"],
        ["binance-futures","BTCUSDT",str(start+11000),str(start+11000),"false","ask","106","1"],
    ]
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        writer=csv.writer(fh, lineterminator="\n")
        writer.writerow(p0.EXPECTED_HEADER)
        writer.writerows(rows)


def test_fixture_audit_detects_new_event_information(tmp_path: Path) -> None:
    day=p0.DEVELOPMENT_DAYS[0]
    root=tmp_path/"raw"
    path=root/f"{day.isoformat()}.csv.gz"
    _write_fixture(path, day)

    item=p0.audit_day(path, raw_root=root, day=day)
    assert item.bad_rows == 0
    assert item.snapshot_rows == 2
    assert item.post_snapshot_incremental_rows > 0
    assert item.deletion_rows > 0
    assert item.distinct_prices_touched > 10
    assert item.multirow_250ms_buckets > 0
    assert item.multigroup_250ms_buckets > 0
    assert item.max_rows_per_250ms_bucket > 1
    assert item.initialized_after_snapshot is True


def test_wrong_day_path_rejected(tmp_path: Path) -> None:
    day=p0.DEVELOPMENT_DAYS[0]
    root=tmp_path/"raw"
    wrong=root/"something.csv.gz"
    with pytest.raises(p0.P0AuditError) as exc:
        p0.audit_day(wrong, raw_root=root, day=day)
    assert exc.value.reason == "raw_path_outside_frozen_scope"


def test_forward_guards_all_false() -> None:
    assert not any(p0.FORWARD_GUARDS.values())


def test_scope_exactly_seven_jan_jul_days() -> None:
    assert [d.isoformat() for d in p0.DEVELOPMENT_DAYS] == [
        "2026-01-01","2026-02-01","2026-03-01","2026-04-01",
        "2026-05-01","2026-06-01","2026-07-01",
    ]


def test_noncanonical_run_cannot_use_canonical_output(tmp_path: Path) -> None:
    with pytest.raises(p0.P0AuditError) as exc:
        p0.write_result_once(
            p0.REAL_OUTPUT_DIRECTORY,
            {"status":"x"},
            require_canonical_output=False,
        )
    assert exc.value.reason in {
        "output_directory_already_exists",
        "canonical_output_requires_real_mode",
    }


def test_canonical_raw_root_override_rejected_before_read(tmp_path: Path) -> None:
    with pytest.raises(p0.P0AuditError) as exc:
        p0.run_p0(
            raw_root=tmp_path,
            output_directory=p0.REAL_OUTPUT_DIRECTORY,
            require_canonical_output=True,
        )
    assert exc.value.reason == "canonical_raw_root_override_forbidden"

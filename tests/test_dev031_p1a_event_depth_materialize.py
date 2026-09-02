from __future__ import annotations

from datetime import date
import csv
import gzip
import math
from pathlib import Path
import subprocess

import numpy as np
import pytest

from multimarket import dev031_p1a_event_depth_materialize as p1a


def _raw_fixture(path: Path, *, t0: int = 1_800_000_000_000_000) -> tuple[int, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    # One valid 60x60 snapshot group.
    for i in range(60):
        rows.append(
            ["binance-futures", "BTCUSDT", t0, t0, "true", "bid", 100.0 - 0.1 * i, 1.0]
        )
        rows.append(
            ["binance-futures", "BTCUSDT", t0, t0, "true", "ask", 101.0 + 0.1 * i, 1.0]
        )
    # One eligible event group one second later:
    # bid replenish +1 at best bid; ask delete -1 at best ask.
    e = t0 + 1_000_000
    rows.extend(
        [
            ["binance-futures", "BTCUSDT", e, e, "false", "bid", 100.0, 2.0],
            ["binance-futures", "BTCUSDT", e, e, "false", "ask", 101.0, 0.0],
        ]
    )
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            ("exchange", "symbol", "timestamp", "local_timestamp",
             "is_snapshot", "side", "price", "amount")
        )
        writer.writerows(rows)
    return t0, t0 + 2_000_000


def _run_cpp_fixture(tmp_path: Path) -> tuple[np.ndarray, tuple[str, ...]]:
    raw = tmp_path / "raw.csv.gz"
    _, support_ts = _raw_fixture(raw)
    support = tmp_path / "support.csv"
    support.write_text(f"local_timestamp_us\n{support_ts}\n", encoding="utf-8")

    root = Path(__file__).resolve().parents[1]
    exe = p1a._compile_tool(root, tmp_path / "build")
    out = tmp_path / "out.csv"
    completed = subprocess.run(
        [str(exe), str(raw), str(support), str(out)],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr

    with out.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert tuple(rows[0]) == p1a.EXTRACTOR_HEADER
    assert len(rows) == 2
    assert rows[1][1] == "1"
    return np.asarray([float(x) for x in rows[1][2:]], dtype=np.float64), tuple(rows[0])


def test_frozen_identity_and_feature_count() -> None:
    assert p1a.EXPERIMENT_ID == "DEV031-P1A"
    assert p1a.DESIGN_VERSION == "event-depth-materialization-v1"
    assert p1a.TARGET_ID == "A"
    assert p1a.HORIZON_SECONDS == 120
    assert p1a.BARRIER_BPS == 16
    assert p1a.WINDOW_SECONDS == 32
    assert p1a.BLOCK == "PRICE"
    assert len(p1a.EVENT_DEPTH_FEATURE_NAMES) == 26
    assert len(set(p1a.EVENT_DEPTH_FEATURE_NAMES)) == 26
    assert not any(p1a.FORWARD_GUARDS.values())


def test_cpp_extractor_known_event_semantics(tmp_path: Path) -> None:
    x, header = _run_cpp_fixture(tmp_path)
    assert header == p1a.EXTRACTOR_HEADER
    assert x.shape == (26,)
    p1a.validate_event_depth_values(x.reshape(1, -1))

    # Static depth after +1 best-bid replenish and best-ask deletion.
    assert x[0] == pytest.approx(1.0 / 41.0)  # OBI L20
    assert x[1] == pytest.approx(1.0 / 101.0)  # OBI L50
    assert x[2] == pytest.approx(math.log1p(21.0))
    assert x[3] == pytest.approx(math.log1p(20.0))
    assert x[4] == pytest.approx(math.log1p(51.0))
    assert x[5] == pytest.approx(math.log1p(50.0))
    assert x[6] == pytest.approx(11.0 / 51.0)
    assert x[7] == pytest.approx(10.0 / 50.0)

    # Both updates are ~49.75bp from pre-group mid=100.5, so only <=50bp.
    for idx in (8, 9, 11, 12, 14, 15, 17, 18):
        assert x[idx] == pytest.approx(0.0)
    for idx in (10, 13, 16, 19):
        assert x[idx] == pytest.approx(1.0)

    # insert, delete, replenish, deplete pressures.
    assert x[20] == pytest.approx(0.0)
    assert x[21] == pytest.approx(1.0)  # ask deletion is upward pressure
    assert x[22] == pytest.approx(1.0)  # bid replenishment is upward pressure
    assert x[23] == pytest.approx(0.0)
    assert x[24] == pytest.approx(math.log1p(2.0))
    assert x[25] == pytest.approx(math.log1p(1.0))


def test_validate_event_depth_domains() -> None:
    good = np.zeros((3, 26), dtype=np.float64)
    good[:, 2:6] = 1.0
    good[:, 6:8] = 0.5
    good[:, 24:26] = 1.0
    returned = p1a.validate_event_depth_values(good)
    assert np.array_equal(returned, good)

    bad = good.copy()
    bad[0, 8] = 1.01
    with pytest.raises(p1a.P1AMaterializationError) as exc:
        p1a.validate_event_depth_values(bad)
    assert exc.value.reason == "bounded_event_feature_out_of_range"

    bad = good.copy()
    bad[0, 6] = -0.01
    with pytest.raises(p1a.P1AMaterializationError) as exc:
        p1a.validate_event_depth_values(bad)
    assert exc.value.reason == "depth_concentration_out_of_range"

    bad = good.copy()
    bad[0, 24] = -0.1
    with pytest.raises(p1a.P1AMaterializationError) as exc:
        p1a.validate_event_depth_values(bad)
    assert exc.value.reason == "log_feature_negative"


def test_selected_trial_is_exact_and_unique() -> None:
    wanted = {
        "target_id": "A",
        "horizon_seconds": 120,
        "barrier_bps": 16,
        "window_seconds": 32,
        "block": "PRICE",
        "support_contract": {"x": 1},
    }
    artifact = {"trial_ledger": [wanted, {"target_id": "B"}]}
    assert p1a._selected_trial(artifact) is wanted

    with pytest.raises(p1a.P1AMaterializationError) as exc:
        p1a._selected_trial({"trial_ledger": []})
    assert exc.value.reason == "p3_selected_trial_not_unique"


def test_support_contract_reconciliation_exact() -> None:
    frozen = {
        "target_id": "A",
        "horizon_seconds": 120,
        "barrier_bps": 16,
        "window_seconds": 32,
        "block": "PRICE",
        "support_contract": {"per_day": [{"date": "2026-01-01"}], "folds": []},
    }
    artifact = {"trial_ledger": [frozen]}
    reconstructed = {"per_day": [{"date": "2026-01-01"}], "folds": []}
    p1a.reconcile_p3_support_contract(reconstructed, artifact)

    with pytest.raises(p1a.P1AMaterializationError) as exc:
        p1a.reconcile_p3_support_contract(
            {"per_day": [{"date": "2026-01-02"}], "folds": []},
            artifact,
        )
    assert exc.value.reason == "p3_support_contract_mismatch"


def test_canonical_output_guard_fails_before_real_data(tmp_path: Path) -> None:
    with pytest.raises(p1a.P1AMaterializationError) as exc:
        p1a.run_p1a(
            workspace=tmp_path,
            execution_commit="0" * 40,
            output_directory=tmp_path / "not-canonical",
            require_canonical_output=True,
        )
    assert exc.value.reason == "noncanonical_output_directory"


def test_invalid_execution_commit_fails_before_real_data(tmp_path: Path) -> None:
    with pytest.raises(p1a.P1AMaterializationError) as exc:
        p1a.run_p1a(
            workspace=tmp_path,
            execution_commit="short",
            output_directory=tmp_path / "synthetic-out",
            require_canonical_output=False,
        )
    assert exc.value.reason == "execution_commit_must_be_full_sha"

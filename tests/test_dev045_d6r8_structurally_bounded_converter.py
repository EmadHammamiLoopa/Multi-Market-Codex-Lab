from __future__ import annotations

import csv
import gzip
import hashlib
from pathlib import Path

import numpy as np
import pytest

from multimarket import dev045_d6r_bounded_converter as old
from multimarket import dev045_d6r8_structurally_bounded_converter as v2
from multimarket import dev045_d6r8c_bounded_converter_redesign_contract as contract


TRADE_HEADER = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "id",
    "side",
    "price",
    "amount",
)
DEPTH_HEADER = (
    "exchange",
    "symbol",
    "timestamp",
    "local_timestamp",
    "is_snapshot",
    "side",
    "price",
    "amount",
)


def _trade_rows() -> tuple[tuple[str, ...], ...]:
    return (
        ("binance-futures", "BTCUSDT", "1000", "1000", "t1", "buy", "100.1", "0.25"),
        ("binance-futures", "BTCUSDT", "900", "1100", "t2", "sell", "100.0", "0.50"),
        ("binance-futures", "BTCUSDT", "1000", "1100", "t3", "buy", "100.2", "0.125"),
    )


def _depth_rows() -> tuple[tuple[str, ...], ...]:
    snapshot = []
    for index in range(11):
        side = "bid" if index % 2 == 0 else "ask"
        if side == "bid":
            price = f"{99.9 - 0.1 * (index // 2):.1f}"
            amount = f"{1.0 + index // 2:.1f}"
        else:
            price = f"{100.1 + 0.1 * (index // 2):.1f}"
            amount = f"{1.1 + index // 2:.1f}"
        snapshot.append(
            (
                "binance-futures",
                "BTCUSDT",
                "1500",
                "2000",
                "true",
                side,
                price,
                amount,
            )
        )
    incremental = [
        ("binance-futures", "BTCUSDT", "1600", "2100", "false", "ask", "100.1", "4.0"),
        ("binance-futures", "BTCUSDT", "1700", "2200", "false", "bid", "99.9", "0.0"),
        ("binance-futures", "BTCUSDT", "1700", "2300", "false", "ask", "100.2", "2.0"),
        ("binance-futures", "BTCUSDT", "1700", "2300", "false", "bid", "99.8", "2.5"),
    ]
    return tuple(snapshot + incremental)


def _write_gzip_csv(
    path: Path,
    header: tuple[str, ...],
    rows: tuple[tuple[str, ...], ...],
) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _make_files(directory: Path) -> tuple[Path, Path]:
    trades = directory / "trades.csv.gz"
    depth = directory / "incremental_book_L2.csv.gz"
    _write_gzip_csv(trades, TRADE_HEADER, _trade_rows())
    _write_gzip_csv(depth, DEPTH_HEADER, _depth_rows())
    return trades, depth


def _assert_fieldwise_exact(actual: np.ndarray, expected: np.ndarray) -> None:
    assert actual.shape == expected.shape
    assert actual.dtype == expected.dtype
    assert actual.dtype.names == expected.dtype.names
    assert actual.dtype.itemsize == expected.dtype.itemsize == 64
    assert actual.dtype.names is not None
    for field in actual.dtype.names:
        if actual.dtype[field].kind == "f":
            assert np.array_equal(actual[field], expected[field], equal_nan=True), field
        else:
            assert np.array_equal(actual[field], expected[field]), field


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            block = fh.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


@pytest.mark.parametrize("chunk_rows", (1, 2, 3, 7))
def test_v2_synthetic_exact_parity_with_frozen_old_converter(
    tmp_path: Path,
    chunk_rows: int,
) -> None:
    trades, depth = _make_files(tmp_path)
    old_output = tmp_path / f"old_{chunk_rows}.npy"
    v2_output = tmp_path / f"v2_{chunk_rows}.npy"

    old_result = old.convert_tardis(
        trades,
        depth,
        old_output,
        chunk_rows=chunk_rows,
        scratch_dir=tmp_path,
    )
    tuning = v2._testing_tuning(
        chunk_rows=chunk_rows,
        merge_fan_in=2,
        merge_input_window_rows=2,
        merge_output_buffer_rows=3,
        corrected_input_window_rows=2,
        final_output_buffer_rows=3,
        validation_window_rows=3,
    )
    v2_result = v2.convert_tardis(
        trades,
        depth,
        v2_output,
        scratch_dir=tmp_path,
        _tuning=tuning,
    )

    old_data = np.load(old_output, allow_pickle=False)
    v2_data = np.load(v2_output, allow_pickle=False)
    _assert_fieldwise_exact(v2_data, old_data)
    assert old_result.base_event_rows == v2_result.base_event_rows == 20
    assert old_result.final_event_rows == v2_result.final_event_rows
    assert _sha256(v2_output) == _sha256(old_output)
    assert v2_result.output_sha256 == _sha256(v2_output)


def test_v2_forces_more_than_eight_runs_and_three_merge_levels(tmp_path: Path) -> None:
    trades, depth = _make_files(tmp_path)
    tuning = v2._testing_tuning(
        chunk_rows=1,
        merge_fan_in=2,
        merge_input_window_rows=1,
        merge_output_buffer_rows=2,
        corrected_input_window_rows=1,
        final_output_buffer_rows=2,
        validation_window_rows=2,
    )
    result = v2.convert_tardis(
        trades,
        depth,
        tmp_path / "deep_merge.npy",
        scratch_dir=tmp_path,
        _tuning=tuning,
    )
    assert result.initial_sort_runs == 40
    assert result.initial_sort_runs // 2 > 8
    assert result.exchange_merge_levels >= 3
    assert result.local_merge_levels >= 3


def test_v2_source_forbids_whole_file_memmap_paths() -> None:
    source = Path(v2.__file__).read_text(encoding="utf-8")
    assert "mmap_mode" not in source
    assert "open_memmap" not in source
    assert "FIXED_FAN_IN_HIERARCHICAL_EXTERNAL_MERGE" == contract.MERGE_ALGORITHM
    assert contract.WHOLE_FILE_MMAP_ALLOWED is False
    assert contract.FINAL_OUTPUT_FULL_SHAPE_MEMMAP_ALLOWED is False


def test_v2_validation_is_window_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trades, depth = _make_files(tmp_path)
    tuning = v2._testing_tuning(
        chunk_rows=2,
        merge_fan_in=2,
        merge_input_window_rows=2,
        merge_output_buffer_rows=2,
        corrected_input_window_rows=2,
        final_output_buffer_rows=2,
        validation_window_rows=2,
    )
    observed: list[int] = []
    frozen = v2.m4.validate_events

    def observe(data: np.ndarray) -> None:
        observed.append(len(data))
        assert not isinstance(data, np.memmap)
        assert len(data) <= 2
        frozen(data)

    monkeypatch.setattr(v2.m4, "validate_events", observe)
    result = v2.convert_tardis(
        trades,
        depth,
        tmp_path / "windowed_validation.npy",
        scratch_dir=tmp_path,
        _tuning=tuning,
    )
    assert observed
    assert sum(observed) == result.final_event_rows
    assert max(observed) <= 2


def test_v2_rss_guard_is_exercised_without_trigger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trades, depth = _make_files(tmp_path)
    calls: list[int] = []

    def fake_rss() -> int:
        calls.append(1)
        return 123_456

    monkeypatch.setattr(v2, "_current_rss_bytes", fake_rss)
    tuning = v2._testing_tuning(
        chunk_rows=2,
        merge_fan_in=2,
        merge_input_window_rows=2,
        merge_output_buffer_rows=2,
        corrected_input_window_rows=2,
        final_output_buffer_rows=2,
        validation_window_rows=2,
        rss_abort_bytes=1_000_000,
    )
    result = v2.convert_tardis(
        trades,
        depth,
        tmp_path / "rss_guard.npy",
        scratch_dir=tmp_path,
        _tuning=tuning,
    )
    assert result.final_event_rows > 0
    assert len(calls) >= 10


def test_v2_failed_validation_never_promotes_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trades, depth = _make_files(tmp_path)
    output = tmp_path / "must_not_exist.npy"

    def fail_validation(*_args: object, **_kwargs: object) -> None:
        raise v2.StructurallyBoundedConverterError("synthetic_forced_validation_failure")

    monkeypatch.setattr(v2, "_validate_final", fail_validation)
    tuning = v2._testing_tuning(
        chunk_rows=2,
        merge_fan_in=2,
        merge_input_window_rows=2,
        merge_output_buffer_rows=2,
        corrected_input_window_rows=2,
        final_output_buffer_rows=2,
        validation_window_rows=2,
    )
    with pytest.raises(
        v2.StructurallyBoundedConverterError,
        match="synthetic_forced_validation_failure",
    ):
        v2.convert_tardis(
            trades,
            depth,
            output,
            scratch_dir=tmp_path,
            _tuning=tuning,
        )
    assert not output.exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith("dev045_d6r8_")]


def test_v2_rss_guard_fails_closed_before_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trades, depth = _make_files(tmp_path)
    output = tmp_path / "rss_abort.npy"
    monkeypatch.setattr(v2, "_current_rss_bytes", lambda: 10_000)
    tuning = v2._testing_tuning(
        chunk_rows=2,
        rss_abort_bytes=1,
    )
    with pytest.raises(v2.StructurallyBoundedConverterError, match="rss_abort"):
        v2.convert_tardis(
            trades,
            depth,
            output,
            scratch_dir=tmp_path,
            _tuning=tuning,
        )
    assert not output.exists()


def test_v2_production_constants_equal_frozen_contract() -> None:
    tuning = v2.PRODUCTION_TUNING
    assert tuning.chunk_rows == 250_000
    assert tuning.merge_fan_in == 8
    assert tuning.merge_input_window_rows == 16_384
    assert tuning.merge_output_buffer_rows == 65_536
    assert tuning.corrected_input_window_rows == 32_768
    assert tuning.final_output_buffer_rows == 65_536
    assert tuning.validation_window_rows == 65_536
    assert tuning.rss_abort_bytes == 6 * 1024 ** 3
    assert contract.MIN_MEMAVAILABLE_BYTES == 8 * 1024 ** 3
    assert contract.MIN_NOFILE_SOFT == contract.MIN_NOFILE_HARD == 128


def test_v2_invalid_tuning_fails_closed(tmp_path: Path) -> None:
    trades, depth = _make_files(tmp_path)
    bad = v2._testing_tuning(chunk_rows=1, merge_fan_in=1)
    with pytest.raises(v2.StructurallyBoundedConverterError, match="merge_fan_in"):
        v2.convert_tardis(
            trades,
            depth,
            tmp_path / "bad.npy",
            scratch_dir=tmp_path,
            _tuning=bad,
        )

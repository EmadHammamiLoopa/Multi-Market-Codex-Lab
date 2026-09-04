from __future__ import annotations

from dataclasses import replace

import pytest

from multimarket import (
    dev045_d4_raw_provenance as d4,
)


def test_execution_surfaces_are_closed():
    assert (
        d4.COMPRESSED_BYTE_HASHING_ENABLED
        is True
    )

    assert (
        d4.RAW_GZIP_DECOMPRESSION_ENABLED
        is False
    )

    assert (
        d4.RAW_CSV_HEADER_READ_ENABLED
        is False
    )

    assert (
        d4.RAW_CSV_ROW_PARSE_ENABLED
        is False
    )

    assert (
        d4.TARDIS_CONVERTER_EXECUTION_ENABLED
        is False
    )

    assert (
        d4.HISTORICAL_POLICY_REPLAY_ENABLED
        is False
    )

    assert (
        d4.HISTORICAL_PNL_ENABLED
        is False
    )

    assert (
        d4.ECONOMIC_ARENA_EXECUTION_ENABLED
        is False
    )

    assert (
        d4.CANONICAL_PNL_WRITE_ENABLED
        is False
    )

    assert (
        d4.NETWORK_MARKET_DATA_ACQUISITION_ENABLED
        is False
    )

    assert (
        d4.LIVE_TRADING_AUTHORIZED
        is False
    )


def test_manifest_identity_and_structure():
    rows = d4.verify_frozen_manifest()

    assert len(rows) == 14

    assert (
        d4.manifest_file_sha256()
        == d4.FROZEN_MANIFEST_SHA256
    )

    assert tuple(
        (row.kind, row.day)
        for row in rows
    ) == d4.expected_order()

    assert sum(
        row.kind == "trades"
        for row in rows
    ) == 7

    assert sum(
        row.kind
        == "incremental_book_L2"
        for row in rows
    ) == 7


def test_exact_authorized_calendar():
    assert d4.AUTHORIZED_DAYS == (
        "2026-01-01",
        "2026-02-01",
        "2026-03-01",
        "2026-04-01",
        "2026-05-01",
        "2026-06-01",
        "2026-07-01",
    )

    assert d4.STREAMS == (
        "trades",
        "incremental_book_L2",
    )

    assert d4.SYMBOL == "BTCUSDT"


def test_every_manifest_path_is_exact():
    rows = d4.verify_frozen_manifest()

    for row in rows:
        assert (
            row.relative_path
            == d4.expected_relative_path(
                row.kind,
                row.day,
            )
        )

        assert (
            "/BTCUSDT/"
            in row.relative_path
        )

        assert row.relative_path.endswith(
            f"/{row.day}.csv.gz"
        )


def test_manifest_has_no_absolute_local_path():
    text = d4.manifest_path().read_text(
        encoding="utf-8"
    )

    assert "/home/" not in text
    assert "/mnt/" not in text
    assert "mtime" not in text.lower()


def test_first_and_last_frozen_identity():
    rows = d4.verify_frozen_manifest()

    first = rows[0]
    last = rows[-1]

    assert first.kind == "trades"
    assert first.day == "2026-01-01"
    assert first.bytes == 9_691_108
    assert first.sha256 == (
        "e4aaee2b9f85016a5198e0cace5755db"
        "d789c0f6f47ac0fc802c8f4b533833f6"
    )

    assert last.kind == (
        "incremental_book_L2"
    )
    assert last.day == "2026-07-01"
    assert last.bytes == 923_475_379
    assert last.sha256 == (
        "b2e8bbed3db89695f055dc3010a0fff0"
        "74732d82ae18117a1602b5593c90d1f1"
    )


def test_reject_duplicate_path_alias_at_row_boundary():
    rows = d4.verify_frozen_manifest()

    # RawFileProvenance enforces the exact kind/day -> path mapping
    # before a malformed row can reach manifest-level validation.
    # Therefore a duplicate-path alias is rejected at construction time.
    with pytest.raises(
        d4.RawProvenanceError,
        match="relative_path",
    ):
        replace(
            rows[-1],
            relative_path=rows[0].relative_path,
        )


def test_reject_wrong_stream():
    row = d4.verify_frozen_manifest()[0]

    with pytest.raises(
        d4.RawProvenanceError,
        match="stream",
    ):
        replace(
            row,
            kind="bybit",
        )


def test_reject_august():
    row = d4.verify_frozen_manifest()[0]

    with pytest.raises(
        d4.RawProvenanceError,
        match="unauthorized_day",
    ):
        replace(
            row,
            day="2026-08-01",
        )


def test_reject_wrong_symbol_path():
    row = d4.verify_frozen_manifest()[0]

    with pytest.raises(
        d4.RawProvenanceError,
        match="relative_path",
    ):
        replace(
            row,
            relative_path=(
                "trades/ETHUSDT/"
                "2026-01-01.csv.gz"
            ),
        )


def test_local_verifier_refuses_wrong_root_before_read():
    with pytest.raises(
        d4.RawProvenanceError,
        match="raw_root_basename",
    ):
        d4.verify_local_compressed_bytes(
            "/tmp/not-the-frozen-root",
        )

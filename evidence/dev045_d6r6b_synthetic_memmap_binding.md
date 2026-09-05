# DEV045 D6R6B — Synthetic Memmap HftBacktest Binding

Status: IMPLEMENTATION / SYNTHETIC MEMMAP ONLY

Parent:

`049de0c0e6b8630c8a0b765a60b10045f677df68`

## Purpose

D6R6B implements the D6R6A lifetime-safe memmap-to-hftbacktest
binding.

This phase proves the binding only on a tiny synthetic `.npy` memmap.

The canonical Jan artifact is not opened by D6R6B.

## Frozen behavior

The binding:

1. requires an already verified `CanonicalJanMemmap` owner;
2. requires a read-only, contiguous `numpy.memmap`;
3. requires the exact frozen 64-byte hftbacktest event dtype;
4. registers that live memmap through `BacktestAsset.data`;
5. sets `parallel_load(False)`;
6. freezes feed latency offset at zero;
7. retains the memmap owner for the full backtest lifetime;
8. closes hftbacktest first;
9. only then closes/unmaps the memmap.

## Synthetic test

The dedicated test creates a four-row temporary `.npy` fixture.

The fixture is reopened through the frozen D6R5 verification machinery
as a read-only memmap.

The test then binds it to the exact patched hftbacktest 2.4.4 kernel and
consumes the four strategy-visible feed timestamps.

No order is submitted.

No policy function is called.

No PnL is calculated.

## Safety boundary

Still forbidden:

- opening canonical Jan inside hftbacktest;
- opening raw CSV;
- rerunning conversion;
- modifying or reordering canonical data;
- M01-M08 execution;
- historical replay;
- historical PnL;
- economic arena execution;
- canonical PnL writing;
- Feb-Jul opening;
- Aug opening;
- Sep+ opening;
- non-BTC opening;
- network market-data acquisition;
- Railway access;
- live trading.

## Next gate

After both repository CI and the dedicated D6R6B patched-hftbacktest CI
are independently green, the next step is a separately frozen
**canonical Jan hftbacktest ingestion contract**.

That later contract must define the first real Jan ingestion boundary
before the canonical file is opened inside hftbacktest.

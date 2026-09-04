# DEV045 D6R3 Full-Day Resource Preflight Contract

## Purpose

D6R3 determines whether the frozen bounded-memory converter may safely
attempt the first complete real day:

`BTCUSDT 2026-01-01`.

D6R3A freezes resource gates only.

It does not open raw market content and does not run either converter.

D6R3B later measures the current machine against these frozen gates.

## Real parity prerequisite

D6R2B is frozen PASS at:

`4ff70ec50e39da432a70bf0444907f536586ed3e`

The fixed real ten-minute bounded output matched the frozen upstream
hftbacktest oracle exactly.

Measured bounded-converter peak RSS:

`451,440,640 bytes`

approximately:

`0.420437 GiB`.

## Frozen full-day geometry

D6B remains a frozen FAIL for the old whole-day in-memory converter.

Only its already-frozen Jan-01 preflight geometry is reused:

- trades rows: `1,056,983`
- depth rows: `62,609,291`
- depth snapshot batches: `1`

A processed snapshot batch adds:

- one bid clear event;
- one ask clear event.

Therefore frozen base-event rows are:

`63,666,276`

At exact hftbacktest event size `64 bytes`:

`base_event_buffer_bytes = 4,074,641,664`.

This is a conservative resource-sizing quantity only.

## Memory gate

Frozen D6R0 rule:

`MemAvailable >= 4 × bounded peak RSS from fixed real parity`

Thus:

`4 × 451,440,640 = 1,805,762,560 bytes`

approximately:

`1.68175 GiB`.

The probe is Linux `/proc/meminfo` field:

`MemAvailable`.

Swap does not count.

## Scratch-disk gate

Frozen D6R0 rule:

`free scratch bytes >= 6 × base-event buffer bytes`

Thus:

`6 × 4,074,641,664 = 24,447,849,984 bytes`

approximately:

`22.7688 GiB`.

The probed filesystem is the filesystem containing:

`/home/emadh/Multi-Market`.

The later full-day output and scratch directory must remain on that
same probed filesystem unless a new contract is frozen first.

D6R3B only measures free capacity; it does not allocate the full amount.

## File-descriptor gate

Frozen production chunk size:

`500,000 rows`.

For:

`63,666,276 base events`

the expected number of run pairs is:

`ceil(63,666,276 / 500,000) = 128`.

Therefore expected temporary sort-run files:

- exchange runs: 128
- local runs: 128
- total: 256

With 64 descriptors of explicit engineering headroom:

`required soft RLIMIT_NOFILE = 320`.

## CPU / v24 machine capacity

CPU count and affinity are recorded as diagnostics only.

CPU count is not a gate.

No artificial CPU cap is permitted.

Later heavy execution may use the machine's available CPU capacity.

This does not weaken memory, disk, or file-descriptor gates.

## Canonical D6R3B PASS

All three gates must pass:

1. MEMORY
2. SCRATCH_DISK
3. NOFILE

The first measured PASS or FAIL is frozen.

## After PASS

A D6R3B resource PASS does not execute January.

It authorizes only the next separate phase:

`FREEZE_JAN01_FULL_DAY_BOUNDED_CONVERSION_CONTRACT`.

## Explicitly closed

D6R3 does not authorize:

- raw market-content opening;
- full-day conversion;
- any other real date;
- August;
- September or later;
- non-BTC;
- policy execution;
- M01-M08;
- historical replay;
- PnL;
- economic arena;
- canonical PnL;
- network market-data acquisition;
- Railway;
- live trading.

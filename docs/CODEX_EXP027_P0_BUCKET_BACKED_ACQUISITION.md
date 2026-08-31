# CODEX-EXP-027-P0 Bucket-Backed Continuous Acquisition Design

Status: **PREREGISTERED STORAGE/ACQUISITION ENGINEERING — NOT YET DEPLOYED**

Experiment ID: `CODEX-EXP-027-P0`

Parent EXP025 frozen implementation:

`1bd708ee2c2082fbeb3c8008e5ce2c16c3bfc379`

## Motivation

EXP025-P0 proved that continuous BTCUSDT/ETHUSDT/SOLUSDT acquisition can run
concurrently and independently, but the deployed Hobby-plan Railway volume is
capped at 5 GB. The observed aggregate compressed raw write rate is high enough
that a full UTC day may exceed that capacity.

EXP027-P0 is therefore an operational storage redesign only. It does not
change any predictive hypothesis, model, feature, target, direction, PnL, or
holdout policy.

## Scope

Initial symbols remain exactly:

- BTCUSDT
- ETHUSDT
- SOLUSDT

Feed remains exactly Binance USD-M Futures combined `bookTicker`.

The local causal receive timestamp remains the authoritative time.

No REST backfill is permitted.

## Storage model

The collector writes immutable **hourly raw chunks** instead of one monolithic
daily gzip file.

Local staging path:

```
/data/staging/bookticker/<SYMBOL>/<YYYY-MM-DD>/<HH>.jsonl.gz
```

Archive object key:

```
bookticker/<SYMBOL>/<YYYY-MM-DD>/<HH>.jsonl.gz
```

Every hourly chunk:

1. is created exclusively;
2. receives exact symbol/day/hour/process/implementation metadata;
3. accepts only records whose local receive timestamp belongs to that UTC hour;
4. is closed, gzip-finalized, flushed, and fsynced before upload;
5. has SHA-256 and byte size calculated after close;
6. is uploaded to a private S3-compatible Railway Bucket;
7. is verified remotely by exact object byte size plus stored SHA-256 metadata;
8. receives an immutable local/archive manifest record;
9. may be deleted from local staging **only after** successful verification.

An unverified local chunk is never deleted.

Active chunks are never uploaded as authoritative objects and never deleted.

## Daily manifest

For each symbol/day the collector creates a one-shot manifest containing:

- experiment ID;
- symbol;
- UTC day;
- frozen implementation commit;
- collector run/process identity;
- 24 expected hourly chunk keys;
- per-chunk byte size;
- per-chunk SHA-256;
- upload verification status;
- connection/transport summary;
- no-analysis guards;
- whether the process was armed before UTC midnight;
- whether next-day rollover was observed.

A day cannot become archive-ready until all 24 hourly chunks are present and
verified plus rollover has completed.

## Daily status

`FULL_DAY_RAW_ARCHIVE_READY` requires:

- collector armed before day start;
- all 24 hour chunks present;
- all 24 chunks locally finalized before upload;
- all 24 remote object sizes exact;
- all 24 remote SHA-256 metadata values exact;
- no local operational-failure marker;
- no unsupported symbol acceptance;
- no accepted clock reversal;
- no backfill;
- observed next-day rollover;
- all no-analysis guards false.

`PARTIAL_START_DAY` is used for a process that begins after that day's UTC
midnight.

`FAIL_ARCHIVE_INTEGRITY` is used when a cleanly completed day cannot satisfy
the archive requirements.

`INVALID` is used for implementation/provenance/protocol failures.

These are acquisition/storage statuses, never predictive results.

## Finalization

A separate deterministic finalizer reconstructs the same causal 250 ms grid
semantics from the ordered 24 hourly archive objects.

It must:

- download/stream chunks in exact hour order;
- verify every chunk SHA-256 and byte size before analytical parsing;
- use only the latest accepted quote with local receive time <= grid time;
- preserve the 2,000 ms staleness rule;
- preserve connection-epoch invalidation/fresh-quote rules;
- never interpolate or backfill;
- create immutable grid and audit artifacts.

## Local-capacity invariant

The design must keep the local 5 GB service volume bounded by removing only
verified, closed hourly chunks.

At least the current active hour plus any unverified prior chunks may remain
local.

If uploads fail long enough that local free-space safety is threatened, the
collector must stop with an explicit operational failure rather than deleting
unverified data or silently dropping quotes.

## Bucket requirements

The Railway Bucket must be private and S3-compatible.

Credentials are injected only into the EXP027 service.

The current live EXP025 `abundant-love` deployment must not be redeployed or
modified merely to add bucket credentials.

## Transition from EXP025

EXP025's current 2026-08-31 files remain a partial-start operational artifact.

EXP027 should be deployed as a separate service/volume and proven healthy
before EXP025 is stopped.

No day is considered a full prospective holdout if collection for that day
began after midnight or if the transition caused a gap.

## Scientific guards

EXP027-P0 performs no:

- feature construction;
- target construction;
- model fit;
- AUC/AP scoring;
- direction scoring;
- PnL scoring;
- leverage scoring;
- session selection;
- holdout opening.

Its sole purpose is durable prospective acquisition under bounded local
storage.

## Required tests before deployment

- deterministic hourly rollover;
- exact symbol isolation;
- hourly boundary quote routing;
- close/fsync before upload;
- exact remote size/SHA metadata verification;
- upload failure preserves local chunk;
- remote mismatch preserves local chunk and fails;
- local deletion occurs only after verified upload;
- restart cannot overwrite an existing local chunk or remote authoritative key;
- one slow/failing symbol does not silently corrupt another;
- queue overflow remains explicit;
- writer shutdown timeout remains explicit;
- daily manifest cannot report FULL_DAY_RAW_ARCHIVE_READY with fewer than 24
  verified chunks;
- finalizer rejects any missing/mismatched archive chunk;
- no predictive code or network backfill exists.

## Deployment rule

Do not stop the healthy EXP025 collector until an EXP027 deployment has:

- started successfully;
- connected to the feed;
- created symbol-isolated staging chunks;
- uploaded at least one closed test/hourly chunk successfully;
- verified exact size/SHA metadata;
- shown no operational-failure markers.

A mid-day transition day remains partial and cannot be used as a fresh
confirmatory holdout.

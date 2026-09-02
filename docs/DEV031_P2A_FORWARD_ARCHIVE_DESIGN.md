# DEV031-P2A — Frozen Forward Archive Metadata Audit Design

Status: `DESIGN_FROZEN_BEFORE_ARCHIVE ACCESS`

Experiment:
`DEV031-P2A`

Design version:
`forward-archive-metadata-feasibility-v1`

## 1. Storage source

Railway bucket:
`market-raw-archive`

Collector:
`EXP027 / exp027-archive`

The bucket is read-only for P2A.

No delete, upload, overwrite, rename, copy, lifecycle mutation, or collector
restart is permitted.

## 2. Metadata-only authorization

P2A may obtain only object-list metadata needed to determine:
- object key;
- object byte size;
- object last-modified/storage timestamp if returned by the listing interface.

P2A must NOT:
- GET/download an object body;
- range-read an object;
- decompress;
- inspect CSV/JSON payload content;
- calculate labels;
- calculate features;
- fit a model;
- calculate AUC/log loss/Brier/BA/F1;
- run PnL.

## 3. Candidate market-time set

Only BTCUSDT forward objects whose market date is:
`>= 2026-09-01 UTC`

Explicitly excluded:
- Aug-01;
- Aug-30;
- Jan-Jul;
- ETHUSDT;
- SOLUSDT.

## 4. Frozen day-selection rule

The selected confirmation candidate day is:

> the chronologically earliest UTC date >= 2026-09-01 for which metadata
> demonstrates all 24 hourly BTCUSDT objects 00..23 are present and each object
> has positive byte size.

The selection uses no object-body content and no market outcome.

If more than one object matches an expected symbol/date/hour slot, P2A fails
closed for that day rather than choosing one post hoc.

If Sep-01 is incomplete, inspect Sep-02 metadata next, and so on
chronologically.

No date may be skipped because of perceived market behavior.

## 5. Frozen expected archive granularity

Historical handoff evidence states EXP027 writes hourly objects and was observed
with BTCUSDT hourly objects during Sep-01.

P2A therefore requires exactly 24 hourly slots.

P2A does not assume EXP027 objects are byte-identical to EXP025 files.

## 6. Schema compatibility boundary

P2A does not open payloads, therefore it cannot prove payload-level schema.

It records object-key naming structure only.

A later P2B preflight may perform a separately frozen, minimal schema/header
verification before analytical use.

P2A PASS must be interpreted as archive coverage feasibility, not full feature
reconstruction feasibility.

## 7. No model selection / no rescue

P2A must not use:
- P1B scores;
- EXP024 scores;
- P3 predictions;
- P4 touch probabilities;
- volatility;
- price movement;
- session identity;
- realized outcome

to choose the forward day.

## 8. Canonical result fields

P2A artifact records:
- experiment/design id;
- access method;
- bucket name;
- metadata-access timestamp;
- all candidate BTCUSDT keys considered;
- parsed UTC day/hour for each key;
- object byte size;
- per-day 24-slot coverage vector;
- duplicate-slot diagnostics;
- exact selected day or null;
- guards proving no object body was opened;
- terminal status.

## 9. Terminal statuses

If an exact earliest complete day exists:

`FORWARD_ARCHIVE_DAY_METADATA_READY`

If no inspected forward date is complete:

`FAIL_FORWARD_ARCHIVE_DAY_METADATA_INCOMPLETE`

If object naming cannot be parsed deterministically without content access:

`INCONCLUSIVE_FORWARD_ARCHIVE_KEY_SCHEMA`

## 10. Canonical output

`/home/emadh/Multi-Market/evidence/dev031_p2a_forward_archive_audit_v1/DEV031_P2A_FORWARD_ARCHIVE_AUDIT.json`

Write once.

## 11. One-shot and consumption rule

Once a valid canonical P2A artifact exists:
`DEV031-P2A MUST NEVER BE RERUN`.

P2A metadata inspection does not consume the forward analytical holdout.

The first later P2B object-body read for the selected market day DOES consume
that day and must occur only after P2B design/implementation freeze.

## 12. Next stage if P2A PASS

P2B must be separately preregistered.

P2B will:
- freeze the selected P2A day before body access;
- perform payload/schema reconstruction;
- construct the exact A/120s/16bp/32s support;
- use frozen Jan-Jul-trained direction models;
- test the ranking hypothesis only under predeclared forward gates.

P2A itself performs none of these actions.

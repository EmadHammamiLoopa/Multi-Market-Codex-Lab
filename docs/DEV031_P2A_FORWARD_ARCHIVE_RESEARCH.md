# DEV031-P2A — Forward Archive Feasibility Audit

Status: `PREREGISTERED_BEFORE_FORWARD_ARCHIVE_ACCESS`

Parent evidence:
- DEV031-P1B official status =
  `FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE`
- preserved partial signal:
  pooled AUC 0.536469 -> 0.576493, +0.040024;
  3/4 fold AUC deltas positive;
  all four leave-one-fold-out AUC deltas positive.

P1B probability-quality gates failed, therefore P1B remains a FAIL.

## Scientific purpose

P2A is NOT a predictive confirmation.

It asks only whether the previously sealed forward archive contains a complete,
usable BTCUSDT day from which the already-frozen forward confirmation pipeline
could later be reconstructed.

P2A may inspect object metadata only.

No object body may be downloaded, opened, decompressed, parsed, or sampled.

## Why forward confirmation now

A ranking-only follow-up on Jan-Jul would be post-hoc reuse of consumed
development outcomes.

Therefore the P1B AUC pattern is treated only as a hypothesis. A later
ranking-specific confirmation must use fresh unseen market time.

## Holdout semantics

Market-time identity, not storage location, defines consumption.

Sep-01+ remained sealed during DEV030/DEV031 development.

P2A metadata-only storage operations do not analytically consume the holdout.

Any later P2B object-body opening will consume the selected forward market day.

## Preserved prior successes

- EXP024-P1 remains the strong opportunity-ranking component.
- DEV030-P3 remains the frozen direction baseline.
- DEV030-P4 touch head remains a preserved component success.

P2A does not combine any of them.

## P2A output meaning

PASS means only:
a complete forward archive day exists and a later frozen confirmation can be
constructed.

FAIL means only:
the archive is incomplete/incompatible for the frozen confirmation protocol.

No predictability, AUC, economics, or profitability claim is made.

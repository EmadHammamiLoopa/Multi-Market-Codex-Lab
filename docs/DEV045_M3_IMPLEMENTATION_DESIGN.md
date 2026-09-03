# DEV045-M3 — Maker Policy Implementation and Synthetic Contract Tests

Status:

`IMPLEMENTED_SYNTHETIC_CI_PENDING_NO_PNL`

Date: 2026-09-03

## Parent

DEV045-M2 final green identity:

`9a21e870d20f3b7c85a571de4d319d9972c9895e`

M2 policy definitions are frozen.

## Scope

M3 implements deterministic policy-state logic only.

It does not:

- open historical data;
- submit a real-data strategy order;
- compute maker PnL;
- rank policies;
- alter fees;
- tune thresholds;
- change queue models.

## Architecture

Policy logic is intentionally independent from hftbacktest.

Reason:

policy correctness and simulator correctness are separate failure domains.
M1 already validated the safety-patched simulator path. M3 first proves the
policy state machine without importing simulator semantics into policy
decisions.

Implementation:

`src/multimarket/dev045_m3_policy.py`

Tests:

`tests/test_dev045_m3_policy.py`

## Frozen semantics implemented

- exactly M01..M08;
- integer-tick price decisions;
- no inside-spread improvement;
- 0.001 BTC / 1%-displayed size rule;
- +/-0.003 BTC inventory hard cap;
- 60s unresolved-inventory forced flatten;
- M02 inventory reservation;
- M03 fixed L1 OBI thresholds;
- M04 bounded microprice shift;
- M05 fixed 1s trade-flow retreat/veto;
- M06 exact frozen T10 + A0>=0.50 adapter;
- M07 exact frozen T05 + A0>=0.50 adapter;
- M08 one-tick queue-preservation hysteresis;
- cancel-first / submit-after-cancel two-phase maintenance;
- terminal cancel + executable flatten plan;
- fail-closed crossed book and inventory-cap validation.

## Passive-only resolution

M2 simultaneously froze signed reference shifts and forbade inside-spread
improvement.

M3 resolves these consistently and conservatively:

- positive reference shift may only retreat the ask outward;
- negative reference shift may only retreat the bid outward;
- the favorable side remains at the displayed best;
- no policy is allowed to improve through the spread.

This preserves the economic direction of the frozen skew while honoring the
stronger passive-only/no-inside-improvement constraint.

## Next gate

M3 passes only if dedicated synthetic CI is green.

After M3 green/freeze, next stage is:

`DEV045-M4 REPLAY ADAPTER + EXECUTION-INTEGRITY SYNTHETIC TESTS`

M4 will bind M3 decisions to the M1 safety-patched simulator and prove actual
submit/cancel/partial-fill/inventory/forced-flatten lifecycle parity.

Still NO canonical maker PnL in M4.

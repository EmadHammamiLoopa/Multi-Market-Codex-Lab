# DEV045-M1 Final Replay-Parity Freeze

Status:

`DEV045_M1_GREEN_FROZEN`

Date: 2026-09-03

## Frozen scientific execution identity

`589074c37a099b2414527dbc85a01de615493742`

This commit is the final M1 implementation identity.

## Dedicated CI

Workflow:

`dev045-m1-replay-parity`

Final run:

- run #13
- GitHub Actions id: `33798183767`
- result: `SUCCESS`

The final CI includes the safety-patched hftbacktest 2.4.4 source path and the
mandatory cancel-latency sentinel.

## Local real-data converter smoke

Executed from the active local clone:

`/mnt/c/Users/emadh/Downloads/market-exp026`

Code/data separation remains:

- active code/worktree:
  `/mnt/c/Users/emadh/Downloads/market-exp026`
- raw/evidence storage:
  `/home/emadh/Multi-Market/data/...`
  and
  `/home/emadh/Multi-Market/evidence/...`

Authorized smoke scope:

- BTCUSDT
- 2026-01-01 only
- bounded prefix only
- L2 prefix rows = `100000`
- trade prefix rows = `25000`
- converted events = `126594`

Observed terminal status:

`DEV045_M1_REAL_DATA_CONVERTER_SMOKE_PASS`

Confirmed:

- strategy order submitted = false
- maker PnL run = false
- Sep-01+ opened = false
- non-BTC opened = false

The local smoke used unpatched hftbacktest 2.4.4 only for Tardis conversion and
book construction. It submitted no order and exercised no fill/accounting path.

## Permanent simulator safety rule

Unpatched PyPI `hftbacktest==2.4.4` remains FORBIDDEN for any maker
fill/accounting/PnL path.

All future DEV045 maker execution must use the exact upstream source identity:

`a244a14250b42d97fc305569c93c4117cd5e1dff`

with the fail-closed minimal corrections already validated in M1 for upstream
issues #312 and #316:

1. partial fills update local state/accounting;
2. exact-final-fill cleanup removes the completed exchange-side order.

Mandatory accounting invariant:

`sum(fill-response executed quantity) == position delta`

Mandatory fee invariant:

`engine fee == independently calculated fee`

## M1 conclusion

The historical MBP+trades replay path is operational for controlled maker
research under explicit queue-model uncertainty.

Primary queue model remains:

`RISK_ADVERSE`

Diagnostic only:

`LOG_PROB`

Exact FIFO rank remains unobservable from MBP data.

Therefore prospective live fill calibration is still mandatory before any real
capital deployment.

## Permanent no-rerun rule

DEV045-M1 is complete and frozen.

Do not add more diagnostics to the M1 branch.

Do not rerun or redesign M1 to rescue later maker economics.

## Next stage

`DEV045-M2 FINITE MAKER POLICY CONTRACT DESIGN`

M2 remains NO-PNL.

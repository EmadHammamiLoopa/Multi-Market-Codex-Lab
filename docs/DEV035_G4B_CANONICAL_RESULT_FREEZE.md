# DEV035-G4B Canonical Result Freeze

Status: `CANONICAL_SUCCESS_ZERO_TRUE_G4_SURVIVORS_DEEP_VERIFY_NEXT`

Date: 2026-09-02

Scientific execution commit:

`806a0a49a102248250770807cb4cb3c45fcb9797`

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev035_g4b_eth_cross_asset_screen_v1/DEV035_G4B_ETH_CROSS_ASSET_SCREEN_RESULT.json`

Artifact SHA256:

`f73543756c5e882d054bd19388e90838ae6f7b2e277234fa1e1ce147b4d28455`

Artifact bytes:

`243563`

Canonical execution:

- exit code = 0
- artifact contract = 43 PASS / 0 FAIL
- process returned success = YES
- staging residue = none
- git tree remained clean

Permanent rule activated:

`DEV035-G4B MUST NEVER BE RERUN`

Upstream permanent rules remain:

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

## Frozen comparator

Comparator identity:

`BTC45_PROMOTED_BASE_REFIT`

Pooled balanced accuracy:

`0.5920001546112814`

This exactly reproduces the promoted G3C16 direction-stage base performance
under the matched G4B protocol.

## Joint temporal max-stat null

- seed = 20260902
- replicates = 1999
- candidates = 3
- max-stat q95 =
  `0.028557992114824682`

## Candidate results

### G4C01 — ETH_L0_STATIC_STATE

- BA = `0.5989512201406962`
- delta BA = `+0.006951065529414824`
- max-stat FWER p = `0.4055`
- status = `G4_LAYER_REJECTED`

Interpretation:

Static ETH state was numerically positive but failed the preregistered
incremental, stability, and multiplicity-controlled survivor requirements.

It must not be promoted or refined post hoc.

### G4C02 — ETH_L1_EVENT_FLOW

- BA = `0.5610778983173139`
- delta BA = `-0.0309222562939675`
- max-stat FWER p = `0.988`
- status = `G4_LAYER_REJECTED`

### G4C03 — ETH_L2_FULL_MICROSTRUCTURE

- BA = `0.5657935424021439`
- delta BA = `-0.02620661220913756`
- max-stat FWER p = `0.979`
- status = `G4_LAYER_REJECTED`

## Terminal G4 classification

Layer survivors:

`[]`

Advanced layers:

`[]`

Scientific result:

`ZERO_TRUE_G4_SURVIVORS`

## Scientific consequence

Per the frozen G4B stop rule and permanent layered-search governance:

- retain `BTC45 = DEV030-P3 + G3C16` unchanged;
- close the tested simultaneous ETH cross-asset microstructure family;
- do not promote G4C01 because it was the best-scoring candidate;
- do not refine G4C01 thresholds/features/models post hoc;
- do not promote any rejected ETH L1/L2 candidate;
- move only after deep read-only verification to the next scientifically
  distinct information family.

No forward data was opened.
No PnL was run.

Current state:

`DEV035_G4B_CANONICAL_ZERO_SURVIVORS_DEEP_READ_ONLY_VERIFICATION_NEXT`

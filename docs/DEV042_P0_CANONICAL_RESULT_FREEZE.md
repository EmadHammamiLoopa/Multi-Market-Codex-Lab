# DEV042-P0 Canonical Feature Schema Audit Result Freeze

Status:

`DEV042_P0_FEATURE_SCHEMA_AUDIT_PASS`

Date: 2026-09-03

Scientific execution commit:

`5be56ceefbc82cfb4104b0e78b4618a123fd8ad5`

Permanent rule:

`DEV042-P0 MUST NEVER BE RERUN`

## Canonical artifact

Path:

`/home/emadh/Multi-Market/evidence/dev042_p0_feature_schema_audit_v1/DEV042_P0_FEATURE_SCHEMA_AUDIT_RESULT.json`

SHA256:

`d9259a53d24492f478615c986ed73981f052d483a764935a8dfd68d17212b882`

Bytes:

`12989`

Canonical log:

`/home/emadh/Multi-Market/evidence/dev042_p0_canonical_console_v1.log`

SHA256:

`37b3cffb5ee11dd718ee780265784d27800b8a11e32344a68288db47647dcce1`

Bytes:

`842`

Canonical process:

- run RC = 0
- read-only verification RC = 0
- verification = 27 PASS / 0 FAIL
- git tree clean
- no staging residue

## Frozen feature dimensions

- C0 PRICE = 15
- C1 PRICE+OFI = 60
- C2 PRESSURE_CAPACITY = 51
- C3 COMBINED_LOGIT = 111
- C4 COMBINED_HGB = 111

## Common support

Pooled exact minute decisions:

`10080`

Pooled common support:

`9863`

Retention:

`0.9784722222222222`

This exceeds the frozen 0.90 minimum.

Every day:

- minute decisions = 1440
- F0 native support = 1409
- F1 native support = 1409
- F2 native support = 1424
- common support = 1409
- common retention = 0.9784722222222222
- all common features finite = true

Per-day common support SHA256:

- 2026-01-01:
  `a1ff0a85368724426a9ff9666d998984178ef0427d919644c078351af4c29382`
- 2026-02-01:
  `1b87e100ef77817ef707bb460fb8a9f53895f7d6511f489fb238e3c6afd0b715`
- 2026-03-01:
  `551569f597c63c8f818fd14386b921d131ee2a207b37410ac718d99de0138954`
- 2026-04-01:
  `0d3c2729cfe4ceca7ebbd02252bcc81077e3f53d9d955a3bd2c52a9cb65b346b`
- 2026-05-01:
  `2a3062b8edf4da5aa3c6fc54badab5e5176c25d4bfdf4b7c37b5b3431a494e60`
- 2026-06-01:
  `a334b098c9fb3557a22259195df2fa9650cebc4198d0d7e2c7dc609936805372`
- 2026-07-01:
  `09a954c73b4bc6d30159ec47c019e197fe5d8e18ea7a6625a985202bf8fcf6e2`

## No-result guarantee

P0 did NOT construct or calculate:

- H1800/B32 labels
- class prevalence
- model fits
- classification metrics
- economic metrics
- ranking
- temporal null

No Sep-01+ analytical access occurred.

No non-BTC market was analytically opened.

## Authorization

DEV042-P1 feature-materialization implementation + synthetic/unit CI is now
authorized.

No canonical predictive scoring is authorized yet.

Current state:

`DEV042_P0_FROZEN_PASS_DEV042_P1_IMPLEMENTATION_NEXT`

# DEV035-G4A — ETH→BTC Cross-Asset Support Audit Result

Status: `PASS_FULL_SUPPORT_NO_SHRINK`

Date: 2026-09-02

## Frozen design

`docs/DEV035_G4A_ETH_BTC_CROSS_ASSET_SUPPORT_AUDIT_DESIGN.md`

## Result

The read-only support/alignment diagnostic completed with:

- CHECKS_PASS = 31
- CHECKS_FAIL = 0
- diagnostic RC = 0
- no model fit
- no direction metric
- no temporal null
- no PnL
- no forward-data access

Every frozen BTC promoted-base timestamp aligned exactly to the existing
ETHUSDT 250 ms feature grid.

All three frozen ETH feature validity levels retained the entire promoted BTC
support:

- ETH-L0 = 1341 / 665 LONG / 676 SHORT
- ETH-L1 = 1341 / 665 LONG / 676 SHORT
- ETH-L2 = 1341 / 665 LONG / 676 SHORT

Support loss for all three blocks:

`0 / 1341 = 0.0%`

All three support SHA256 values equal the promoted BTC support SHA256:

`caa61e84281061d00e4244e4f9b30ed2096e5acb95df9906aa7de0f28750ab75`

Every Apr/May/Jun/Jul validation fold retains both classes for L0, L1, and L2.

Feasibility classification:

- L0 = HIGH_SUPPORT
- L1 = HIGH_SUPPORT
- L2 = HIGH_SUPPORT

Nested validity L2 ⊆ L1 ⊆ L0 passed on all seven days.

## Frozen ETH feature-file identities

- 2026-01-01:
  `036f300bbe31f1ccbe4ec52362060870cf6c644a44c8f8b5fd30e79749a39359`
- 2026-02-01:
  `cbac5c6b624930774bd60f3a50383f2551303e3ba5de3648275a362b69e5a643`
- 2026-03-01:
  `006aaa3879fb3051bb241f73cd8b1e1af6e647ea95577e5f2d004fb7cce05187`
- 2026-04-01:
  `54dfa0cf9cb45e869c531db6e082bbb09fa0d819973fd29642be1b68c5691256`
- 2026-05-01:
  `a7e96f52a91f303296ff579d8f72ec206aedb1b1d5227c7472db641b5a5c9fa5`
- 2026-06-01:
  `7753c43fed7574520ac8583e413a57116779aa636ca6fb71026ddf8d86420c1c`
- 2026-07-01:
  `38e8853ba2a777293fa0cd645af5c709cdf9b4faeeaa57941cd37021d675b57d`

## Interpretation

A G4 predictive experiment can use the existing 1341-row promoted support
without any support recovery, imputation, fill, or candidate-specific deletion.

This result establishes feasibility only. It does not establish predictive
value, ETH leadership, or economic value.

Current state:

`DEV035_G4A_SUPPORT_PASS_G4B_PREDICTIVE_DESIGN_AUTHORIZED`

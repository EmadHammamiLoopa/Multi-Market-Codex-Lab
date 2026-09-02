# DEV035-G4B Execution Freeze

Status: `EXECUTION_FROZEN_LOCAL_REAL_DATA_PREFLIGHT_REQUIRED`

Date: 2026-09-02

Scientific implementation commit:

`806a0a49a102248250770807cb4cb3c45fcb9797`

Dedicated CI:

- workflow run = `33664179654`
- job = `dev035-g4b-screen`
- pytest = SUCCESS
- process-pool smoke = SUCCESS
- workflow conclusion = SUCCESS

The earlier final-tip run `33663874691` failed only because of a Python
SyntaxError in the artifact newline serialization. That pre-execution failure
was fixed before any real-data fit or canonical output.

## Frozen parent identities

DEV034-G3B-R1 canonical artifact:

`/home/emadh/Multi-Market/evidence/dev034_g3b_r1_common_support_screen_v1/DEV034_G3B_R1_COMMON_SUPPORT_SCREEN_RESULT.json`

SHA256:

`16200a1595d9472fe488740c0ab63e013b65824298ef1cb0b8856322416a8167`

Bytes:

`873268`

Required promoted survivor:

`G3C16`

Required promoted base:

`BTC45 = DEV030-P3 + G3C16 FULL_FROZEN_R_CONTEXT`

Base width:

`45`

Common support:

- rows = 1341
- LONG = 665
- SHORT = 676

Support SHA256:

`caa61e84281061d00e4244e4f9b30ed2096e5acb95df9906aa7de0f28750ab75`

Label SHA256:

`fcb1b8f6c5f7994ca8c611cb3381146f401be7623ef36ae316a9a2e477a83385`

## Frozen G4 candidates

- G4C01 ETH_L0_STATIC_STATE = width 56
- G4C02 ETH_L1_EVENT_FLOW = width 71
- G4C03 ETH_L2_FULL_MICROSTRUCTURE = width 88

All three must use the exact same 1341-row support.

## Frozen ETH source identities

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

## Predictive protocol

Comparator:

`BTC45_PROMOTED_BASE_REFIT`

Model lineage:

- StandardScaler fit on training rows only
- LogisticRegression L2 / lbfgs
- C grid = 0.01 / 0.1 / 1.0 / 10.0
- threshold = 0.5
- random_state = 20260825

Joint null:

- candidates = G4C01..G4C03
- replicates = 1999
- seed = 20260902
- 3-way max-stat FWER

At most one nested ETH survivor may advance.

## Canonical output reserved

Directory:

`/home/emadh/Multi-Market/evidence/dev035_g4b_eth_cross_asset_screen_v1`

Artifact:

`DEV035_G4B_ETH_CROSS_ASSET_SCREEN_RESULT.json`

From the moment canonical G4B predictive execution starts:

`DEV035-G4B MUST NEVER BE RERUN`

This applies even if that canonical attempt fails.

## Next permitted action

Local real-data preflight only.

The preflight may:

- verify G3B canonical parent identity;
- verify G3C16 promotion;
- verify exact ETH file hashes;
- reconstruct BTC45 and all three G4 matrices;
- verify widths, support, labels, feature names, finiteness, and fold counts;
- run synthetic/unit tests and harness smoke.

The preflight must NOT:

- fit any estimator on real data;
- compute real G4 direction metrics;
- run the real G4 temporal null;
- write canonical output;
- run PnL;
- open forward data.

Current state:

`DEV035_G4B_EXECUTION_FROZEN_LOCAL_REAL_DATA_PREFLIGHT_REQUIRED`

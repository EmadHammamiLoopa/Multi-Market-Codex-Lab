# DEV036-C1 Canonical Result Freeze

Status: `CANONICAL_SUCCESS_PROMOTED_DIRECTION_IMPROVES_P3_BUT_COMPOSITION_NOT_USEFUL`

Date: 2026-09-02

Scientific execution commit:

`cc449a90214b2ab5e1a8e8e9b30d6f25ffcf0b0b`

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev036_c1_promoted_direction_composition_v1/DEV036_C1_PROMOTED_DIRECTION_COMPOSITION_RESULT.json`

Artifact SHA256:

`9278e4c1ef8868b77e2c45a3cd4bcf93a87c99a77fcbf925a12842b3731708b4`

Artifact bytes:

`98670`

Canonical execution:

- exit code = 0
- artifact contract = 36 PASS / 0 FAIL
- process returned success = YES
- staging residue = none
- git tree remained clean

Permanent rule activated:

`DEV036-C1 MUST NEVER BE RERUN`

Upstream permanent rules remain:

`DEV035-G4B MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV034-G3A-R1 MUST NEVER BE RERUN`

## Frozen support

Common support:

- rows = 9849
- TOUCH = 1341
- NONE = 8508

Support SHA256:

`dc89f3012341bd771591693b03af00b86f64f95aa4f7db4e9dc65b7e0e7f7b3f`

Pooled outer validation:

- rows = 5628
- TOUCH = 559
- NONE = 5069

## Direction reproduction

All eight frozen direction prediction hashes reproduced exactly:

- P3_COMMON_SUPPORT_REFIT: 4/4 folds
- G3C16 / BTC45: 4/4 folds

Therefore the C3-vs-C2 comparison is a valid composition comparison using the
same frozen direction systems that were established in G3B-R1.

## Four-system pooled results

### C0 — THREE_CLASS_TRAIN_PREVALENCE

- log loss = `0.4108279963835227`
- Brier = `0.19054457016257817`
- macro AP = `0.3265209275079492`
- macro AUC = `0.4416435032150077`
- macro F1 = `0.3159141192234583`
- balanced accuracy = `0.3333333333333333`

### C1 — TOUCH_PLUS_DIRECTIONAL_PRIOR

- log loss = `0.38191977380368203`
- Brier = `0.18115804127452012`
- macro AP = `0.42213909717556114`
- macro AUC = `0.7269830171014903`
- macro F1 = `0.3563956055694324`
- balanced accuracy = `0.3586455039776633`

### C2 — TOUCH_PLUS_P3_COMMON_DIRECTION

- log loss = `0.384114078372311`
- Brier = `0.1820634665950246`
- macro AP = `0.4171582522392591`
- macro AUC = `0.7237005524480745`
- macro F1 = `0.375595210902331`
- balanced accuracy = `0.3657917683257193`

### C3 — TOUCH_PLUS_BTC45_PROMOTED_DIRECTION

- log loss = `0.38146628782625`
- Brier = `0.18177420484529802`
- macro AP = `0.4220518630457996`
- macro AUC = `0.7294259896430256`
- macro F1 = `0.3920494653475673`
- balanced accuracy = `0.376108057896128`

## Primary result: C3 vs C2

Observed promoted-direction increment:

- delta log loss = `+0.002647790546061013`
- delta Brier = `+0.0002892617497265715`
- delta macro AP = `+0.004893610806540494`
- positive fold log-loss improvements = `4/4`
- all four LOO log-loss improvements positive = true

Fold log-loss improvements:

- `0.0015409089263574427`
- `0.002000333699142126`
- `0.00427873638812637`
- `0.0027711831706180856`

LOO improvements:

- `0.003016751085962166`
- `0.002863609495033892`
- `0.0021041419320392274`
- `0.0026066596712086554`

Temporal null:

- seed = 20260902
- replicates = 1999
- q95 = `-0.0004924853219331338`
- empirical p = `0.0005`
- observed minus q95 = `0.0031402758679941467`

All preregistered C3-vs-C2 gates passed.

Scientific interpretation:

`BTC45 / G3C16 materially and temporally validly improves three-class
composition compared with P3.`

This confirms that the promoted direction layer is real even when embedded
inside the touch-plus-direction architecture.

## Overall composition result: C3 vs C1

Compared with touch plus training-fold directional prior:

- delta log loss = `+0.00045348597743205543`
- delta Brier = `-0.0006161635707779001`
- delta macro AP = `-0.00008723412976152645`
- positive fold log-loss improvements = `2/4`
- all LOO log-loss improvements positive = false

Fold log-loss improvements:

- `+0.0018174144040669638`
- `+0.002707178107995034`
- `-0.0007173507022942283`
- `-0.001993297900039659`

LOO improvements:

- `-0.0000011568314463028528`
- `-0.00029774473275567814`
- `+0.0008437648706741685`
- `+0.0012690806032559232`

Failed overall-composition gates:

- C3 Brier < C1 = FAIL
- C3 macro AP > C1 = FAIL
- >=3/4 positive C3-vs-C1 fold log-loss improvements = FAIL
- all C3-vs-C1 LOO improvements positive = FAIL

## Terminal classification

`FAIL_PROMOTED_DIRECTION_IMPROVES_P3_BUT_COMPOSITION_NOT_USEFUL`

This is not a failure of BTC45.

It means:

1. BTC45 genuinely improves the old P3 directional component;
2. that directional improvement survives composition and temporal falsification;
3. but the three-class product composition does not yet provide robust overall
   value beyond a simpler touch-plus-directional-prior system.

Therefore:

- retain BTC45 as the frozen direction-stage base;
- retain P4 T2 as a successful touch/opportunity component;
- do not claim current product composition is policy-ready;
- do not tune composition weights or thresholds post hoc;
- do not calibrate C3 after seeing this result;
- do not rerun DEV036-C1.

No forward data was opened.
No PnL was run.

Current state:

`DEV036_C1_CANONICAL_CONFIRMS_DIRECTION_INCREMENT_BUT_COMPOSITION_ROUTE_NOT_PROMOTED`

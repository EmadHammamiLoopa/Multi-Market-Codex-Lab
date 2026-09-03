# DEV043-B Canonical Conditional-Direction Result Freeze

Status:

`DEV043_B_NO_DIRECTION_SURVIVOR`

Date: 2026-09-03

Scientific execution commit:

`ccf345984b4668e80bebd4b2ecdd5746851de470`

Permanent rules:

`DEV043-B MUST NEVER BE RERUN`

`NO SECOND ATTEMPT`

`NO FOURTH STAGE-B MODEL`

`NO THRESHOLD RESCUE`

`NO CALIBRATION RESCUE`

`NO HYPERPARAMETER RESCUE`

`NO NULL REDESIGN`

`NO PREDICTED-TOUCH SUPPORT RESCUE`

`NO STAGE-C COMPOSITION`

## Canonical artifact

Path:

`/home/emadh/Multi-Market/evidence/dev043_b_direction_screen_v1/DEV043_B_DIRECTION_SCREEN_RESULT.json`

Bytes:

`91460`

SHA256:

`1f8d2d642b01d8257b6033127388016be44368625e021866c94a4df25a361398`

## Canonical log

Path:

`/home/emadh/Multi-Market/evidence/dev043_b_canonical_console_v1.log`

Bytes:

`5063`

SHA256:

`bc0ddefc972e7f42c69478a64c09463270dfdd219303ee2a326dbae696fec780`

## Canonical process

- canonical run RC = 0
- read-only verification RC = 0
- verification = 31 PASS / 0 FAIL
- git tree clean
- no staging residue
- Stage-A parent identity PASS
- actual historical TOUCH-only support contract PASS
- Sep-01+ sealed
- all non-BTC markets sealed

## Common Stage-B OOF support

Pooled support:

`2683`

Direction counts:

- LONG = 1377
- SHORT = 1306
- LONG prevalence = `0.5132314573238912`

All three candidates used the exact same conditional-TOUCH validation support.

## Candidate results

### B0_DIR_PRICE_LOGIT

Pooled:

- balanced accuracy = `0.42206769271147854`
- BA lift over 0.50 = `-0.07793230728852146`
- ROC AUC = `0.4020931269677629`
- Brier = `0.26398339720398223`
- log loss = `0.7218147842379249`
- prior log loss = `0.6927969967559763`
- AP LONG = `0.43765386569690534`
- AP SHORT = `0.42840280295551136`
- macro AP = `0.43302833432620835`

Per-fold BA lift:

- Apr = `-0.0015509875153499886`
- May = `-0.025326797385620936`
- Jun = `-0.14061718098415343`
- Jul = `0.0062929061784897655`

LOO balanced accuracy:

- omit Apr = `0.39828109235332426`
- omit May = `0.41775458865913434`
- omit Jun = `0.497643529142948`
- omit Jul = `0.39057523930499477`

Joint temporal null:

- observed BA lift = `-0.07793230728852146`
- joint q95 = `0.024055779648368913`
- observed - q95 = `-0.10198808693689038`
- FWER p = `1.0`
- null PASS = false

Failed frozen gates:

- pooled balanced accuracy > 0.55
- pooled ROC AUC > 0.60
- positive BA lift in >=3/4 folds
- all four LOO BA > 0.50
- pooled log loss better than prior
- FWER p <= 0.05
- observed BA lift > joint q95

### B1_DIR_PRESSURE_LOGIT

Pooled:

- balanced accuracy = `0.46177465938448436`
- BA lift over 0.50 = `-0.038225340615515635`
- ROC AUC = `0.44560939343691647`
- Brier = `0.2702911941486766`
- log loss = `0.7386327708649727`
- prior log loss = `0.6927969967559763`
- AP LONG = `0.489236591622536`
- AP SHORT = `0.45602726336473404`
- macro AP = `0.47263192749363503`

Per-fold BA lift:

- Apr = `-0.01225759823986905`
- May = `-0.041666666666666685`
- Jun = `-0.051647206005004165`
- Jul = `0.04948512585812359`

LOO balanced accuracy:

- omit Apr = `0.45601049656207227`
- omit May = `0.4576069509797381`
- omit Jun = `0.5146057481198899`
- omit Jul = `0.43227555232953774`

Joint temporal null:

- observed BA lift = `-0.038225340615515635`
- joint q95 = `0.024055779648368913`
- observed - q95 = `-0.06228112026388455`
- FWER p = `0.9755`
- null PASS = false

Failed frozen gates:

- pooled balanced accuracy > 0.55
- pooled ROC AUC > 0.60
- positive BA lift in >=3/4 folds
- all four LOO BA > 0.50
- pooled log loss better than prior
- FWER p <= 0.05
- observed BA lift > joint q95

### B2_DIR_COMBINED_HGB

Pooled:

- balanced accuracy = `0.5061528212895958`
- BA lift over 0.50 = `0.006152821289595822`
- ROC AUC = `0.5031195054165958`
- Brier = `0.3148407982830371`
- log loss = `0.8977859046325818`
- prior log loss = `0.6927969967559763`
- AP LONG = `0.5088419176183108`
- AP SHORT = `0.4840820971150643`
- macro AP = `0.49646200736668755`

Per-fold BA lift:

- Apr = `0.04667992734343018`
- May = `0.014297385620914982`
- Jun = `0.013177648040033407`
- Jul = `0.016804919908466776`

LOO balanced accuracy:

- omit Apr = `0.49722963647836516`
- omit May = `0.5215766071589754`
- omit Jun = `0.5149137185944626`
- omit Jul = `0.4931395454339246`

Joint temporal null:

- observed BA lift = `0.006152821289595822`
- joint q95 = `0.024055779648368913`
- observed - q95 = `-0.01790295835877309`
- FWER p = `0.2545`
- null PASS = false

Failed frozen gates:

- pooled balanced accuracy > 0.55
- pooled ROC AUC > 0.60
- all four LOO BA > 0.50
- pooled log loss better than prior
- FWER p <= 0.05
- observed BA lift > joint q95

## Joint temporal null

Frozen null identity reproduced exactly:

- seed = `20260903`
- replicates = `1999`
- minimum shift positions = `60`
- joint max-stat q95 = `0.024055779648368913`
- 1999 shift tuples recorded
- 1999 max-stat values recorded
- all three candidates present

No candidate passed the joint temporal null.

## Final decision

Eligible candidates:

`[]`

Survivor ranking:

`[]`

Advanced candidate:

`[]`

Frozen status:

`DEV043_B_NO_DIRECTION_SURVIVOR`

Therefore the preregistered stop rule fires:

`STOP DEV043`

DEV043-C is NOT authorized.

## Scientific interpretation

DEV043 produced an asymmetric result.

Stage A established that H1800/B32 TOUCH occurrence is materially predictable OOF
with the frozen price/momentum representation.

Stage B does not establish conditional LONG/SHORT direction predictability on
actual historical TOUCH rows.

The strongest Stage-B candidate, B2_DIR_COMBINED_HGB, is effectively near random
on pooled discrimination:

- balanced accuracy = `0.5061528212895958`
- ROC AUC = `0.5031195054165958`

and fails the multiplicity-controlled temporal null:

- observed BA lift = `0.006152821289595822`
- joint q95 = `0.024055779648368913`
- FWER p = `0.2545`

B0 and B1 are materially below random on pooled balanced accuracy and ROC AUC.

This is not a marginal gate failure and does not justify a rescue within DEV043.

The supported conclusion is:

`EVENT OCCURRENCE SIGNAL YES; CONDITIONAL DIRECTION SIGNAL NOT ESTABLISHED`

No combined A0 + B trading/economic claim is authorized.

## Closure

DEV043 is closed.

Permanent closure constraints:

- do not rerun DEV043-P0
- do not rerun DEV043-A
- do not rerun DEV043-B
- do not add a fourth Stage-B model
- do not search thresholds
- do not add calibration as a rescue
- do not tune Stage-B hyperparameters
- do not redesign the Stage-B null
- do not weaken eligibility gates
- do not substitute predicted TOUCH for actual-TOUCH support
- do not build DEV043-C
- do not open Sep-01+ as a rescue
- do not open another market as a rescue

Any future work must be a genuinely distinct, separately preregistered hypothesis
family rather than a modification of DEV043 after seeing this result.

Sep-01+ and all non-BTC markets remain analytically sealed.

## Current state

`DEV043_CLOSED_NO_DIRECTION_SURVIVOR_NEW_FAMILY_REQUIRES_SEPARATE_HYPOTHESIS`

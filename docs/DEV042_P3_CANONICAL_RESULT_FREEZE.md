# DEV042-P3 Canonical Predictive Screen Final Result Freeze

Status:

`DEV042_NO_PREDICTIVE_SURVIVOR_FOR_H1800_B32`

Date: 2026-09-03

Scientific execution commit:

`1558d2090b8d4e269b67ddb8bb7687069087f410`

Permanent rules:

`DEV042-P3 MUST NEVER BE RERUN`

`NO SECOND ATTEMPT`

`NO SIXTH MODEL`

`NO THRESHOLD RESCUE`

`NO HYPERPARAMETER RESCUE`

`NO NULL REDESIGN`

## Canonical artifact

Path:

`/home/emadh/Multi-Market/evidence/dev042_p3_predictive_screen_v1/DEV042_P3_PREDICTIVE_SCREEN_RESULT.json`

Bytes:

`155134`

SHA256:

`bdb411e8536d94bb21deca5bfb7f31998023dacd727c27c3a67993b0bc07ac3f`

## Canonical log

Path:

`/home/emadh/Multi-Market/evidence/dev042_p3_canonical_console_v1.log`

Bytes:

`8938`

SHA256:

`836d1fafb250d843c999fc375f051450c3f5d4aaafaa4b04e5a8a383298d9124`

## Canonical process

- canonical run RC = 0
- read-only verification RC = 0
- verification = 35 PASS / 0 FAIL
- git tree clean
- no staging residue
- Sep-01+ sealed
- all non-BTC markets sealed

## Final decision

Eligible candidates:

`[]`

Survivor ranking:

`[]`

Advanced candidate:

`[]`

Canonical status:

`DEV042_NO_PREDICTIVE_SURVIVOR_FOR_H1800_B32`

The frozen five-candidate H1800/B32 predictive family is therefore CLOSED.

## Common OOF target support

All candidates were evaluated on the same OOF support:

- pooled support = 5516
- LONG_FIRST = 1377
- NONE = 2833
- SHORT_FIRST = 1306

Fractions:

- LONG_FIRST = 0.2496374184191443
- NONE = 0.5135968092820885
- SHORT_FIRST = 0.23676577229876722

Common-support and target alignment guards passed.

## Candidate summary

### C0_PRICE_LOGIT

Classification:

- macro F1 = 0.3480270203383462
- balanced accuracy = 0.3825017252999389
- log loss = 1.021339473733765
- macro OVR AP = 0.41811166443615155
- action coverage = 0.20866569978245106

Execution:

- raw actions = 1151
- accepted trades = 120
- LONG = 45
- SHORT = 75
- TP = 39
- SL = 44
- forced horizon = 37

Economics:

- mean gross = -0.8900524201131313 bps/trade
- C1 mean net = -10.890052420113133 bps/trade
- C2 mean net = -16.890052420113133 bps/trade
- C2 total = -2026.8062904135759 bps
- C2 PF = 0.26519846186128915
- C2 positive folds = 0/4

Null:

- joint q95 = -11.776452244869635
- observed - q95 = -5.113600175243498
- FWER p = 0.9685
- null PASS = false

### C1_OFI_LOGIT

Classification:

- macro F1 = 0.341327692923942
- balanced accuracy = 0.36282760798488395
- log loss = 1.174698842512674
- macro OVR AP = 0.3708599476348682
- action coverage = 0.252356780275562

Execution:

- raw actions = 1392
- accepted trades = 139
- LONG = 78
- SHORT = 61
- TP = 39
- SL = 46
- forced horizon = 54

Economics:

- mean gross = -1.7325502437457152 bps/trade
- C1 mean net = -11.732550243745715 bps/trade
- C2 mean net = -17.732550243745717 bps/trade
- C2 total = -2464.8244838806545 bps
- C2 PF = 0.2276472735661499
- C2 positive folds = 0/4

Null:

- observed - q95 = -5.956097998876082
- FWER p = 0.993
- null PASS = false

### C2_PRESSURE_CAPACITY_LOGIT

This was the strongest economic candidate, but it still failed all frozen
promotion requirements.

Classification:

- macro F1 = 0.3692326202911474
- balanced accuracy = 0.3827506695968938
- log loss = 1.0910875309964143
- macro OVR AP = 0.3970055950638691
- action coverage = 0.3134517766497462

Execution:

- raw actions = 1729
- accepted trades = 130
- LONG = 46
- SHORT = 84
- TP = 47
- SL = 35
- forced horizon = 48

Economics:

- mean gross = +2.5357003777301026 bps/trade
- C1 mean net = -7.4642996222698965 bps/trade
- C1 total = -970.3589508950865 bps
- C2 mean net = -13.464299622269898 bps/trade
- C2 total = -1750.3589508950868 bps
- C2 PF = 0.3233688578333247
- C2 positive folds = 0/4
- minimum fold C2 mean = -17.881529397618987 bps/trade
- minimum LOO C2 mean = -14.47573232051467 bps/trade

Null:

- observed = -13.464299622269898
- joint q95 = -11.776452244869635
- observed - q95 = -1.6878473774002636
- FWER p = 0.274
- null PASS = false

Interpretation:

The pressure/capacity representation produced the only clearly positive mean
gross edge among the five candidates, but the edge was only about 2.54 bps per
accepted trade, far below both frozen cost envelopes and not statistically
better than the family-wise temporal null.

It is therefore NOT eligible for threshold, cost, hyperparameter, or model
rescue inside DEV042.

### C3_COMBINED_LOGIT

- mean gross = -0.10500292978610945 bps/trade
- C1 mean net = -10.105002929786108 bps/trade
- C2 mean net = -16.10500292978611 bps/trade
- C2 total = -2657.3254834147083 bps
- C2 PF = 0.25544153925038254
- positive folds = 0/4
- FWER p = 0.903
- null PASS = false

### C4_COMBINED_HGB

Best classification macro F1, but no economic advantage.

Classification:

- macro F1 = 0.3937571971448197
- balanced accuracy = 0.3948518814617543
- log loss = 1.3251939424505308
- macro OVR AP = 0.38908368045759606
- action coverage = 0.5210297316896302

Economics:

- mean gross = -0.34263341872951775 bps/trade
- C1 mean net = -10.342633418729516 bps/trade
- C2 mean net = -16.34263341872952 bps/trade
- C2 total = -3105.1003495586087 bps
- C2 PF = 0.25035392057736755
- positive folds = 0/4
- FWER p = 0.9315
- null PASS = false

This confirms again that better classification metrics do not imply executable
economic value.

## Joint temporal null

Frozen null:

- seed = 20260903
- replicates = 1999
- minimum shift positions = 60
- joint max-stat q95 = -11.776452244869635

All five candidates failed the joint null gate.

## Scientific interpretation

DEV041 established strong oracle executable headroom for H1800/B32.

DEV042 shows that the frozen decision-time information/model family did NOT
recover that oracle headroom predictively.

The failure is not explained by insufficient activity:

- every candidate generated enough actions;
- every candidate had accepted trades in all four folds;
- LONG and SHORT were both present;
- execution-invalid count was zero.

The key failure is predictive-economic alignment.

Four candidates had non-positive mean gross executable return.

The strongest representation, PRESSURE_CAPACITY_LOGIT, achieved only about
+2.54 bps/trade gross and remained negative even under the lighter C1 cost
envelope.

Therefore the gap between oracle headroom and deployable predictive capture
remains large.

## Permanent closure

The exact DEV042 H1800/B32 predictive family is CLOSED.

No:

- sixth model
- HGB tuning
- logistic C tuning
- threshold search
- quantile controller
- cost-envelope weakening
- target modification
- additional DEV042 feature family
- null redesign
- gate weakening
- rerun
- other-market rescue

is permitted.

Any future experiment must be a genuinely new scientific family with a
separately preregistered hypothesis, not a DEV042 rescue.

## Forward reserve

Sep-01+ remains analytically sealed.

All non-BTC markets remain analytically sealed.

## Current state

`DEV042_CLOSED_NO_PREDICTIVE_SURVIVOR_NEW_FAMILY_REQUIRES_SEPARATE_HYPOTHESIS`

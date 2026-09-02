# DEV037-P1 Execution Freeze

Status: `EXECUTION_FROZEN_P0_REAL_DATA_FEASIBILITY_PREFLIGHT_NEXT`

Date: 2026-09-02

Scientific implementation commit:

`32397bee3691ec746d8b845c919c6adcb157a308`

Dedicated CI:

- workflow run = `33683225776`
- dedicated job = `dev037-joint-policy`
- pytest = SUCCESS
- harness smoke = SUCCESS

The workflow was still finishing unrelated jobs when checked, but the dedicated
DEV037 job itself completed successfully.

## Frozen design lineage

Design:

`docs/DEV037_JOINT_SELECTIVE_POLICY_SCREEN_DESIGN.md`

Policies:

- S0 TOUCH_ONLY_SELECTIVE
- S1 DIRECTION_CONFIDENCE_SELECTIVE
- S2 PRODUCT_JOINT_SELECTIVE
- S3 BALANCED_MIN_PERCENTILE
- S4 GEOMETRIC_BALANCED_PERCENTILE
- S5 META_CORRECTNESS_FILTER

All policies emit:

`LONG / SHORT / ABSTAIN`

## Frozen OOF mechanics

For every outer fold:

- Jan and Feb seed expanding training;
- OOF training predictions begin with Mar;
- every scored OOF day is predicted only from strictly earlier days;
- touch and BTC45 component C selection use only earlier days;
- all q80 thresholds derive from concatenated OOF training scores only;
- S5 meta model trains only on OOF component predictions/outcomes.

No validation label may influence a threshold or S5 fit.

## Frozen support

DEV036-C1 common support:

- rows = 9849
- TOUCH = 1341
- NONE = 8508
- support SHA256 =
  `dc89f3012341bd771591693b03af00b86f64f95aa4f7db4e9dc65b7e0e7f7b3f`

Outer validation:

- Apr = 1407
- May = 1407
- Jun = 1407
- Jul = 1407
- pooled = 5628

## Frozen comparator and endpoint

Comparator:

`S0 TOUCH_ONLY_SELECTIVE`

Primary endpoint:

`ACTION_PRECISION = correct_actions / all_actions`

Primary challenger increment:

`Delta_ACTION_PRECISION = ACTION_PRECISION(challenger) - ACTION_PRECISION(S0)`

## Frozen target coverage

Threshold:

`q80`

derived from OOF training score only.

Operational coverage guards:

- each validation fold coverage >= 0.05
- each validation fold coverage <= 0.40
- pooled coverage >= 0.10
- pooled coverage <= 0.30
- LONG and SHORT both emitted in every validation fold

## Frozen joint null

Five challengers S1-S5 jointly tested against S0.

- 1999 replicates
- seed = 20260902
- full three-class validation outcome sequence shifted within each fold
- same shifted labels applied to every policy
- candidate actions fixed
- joint max-stat q95
- plus-one FWER empirical p

## Canonical output reserved

Directory:

`/home/emadh/Multi-Market/evidence/dev037_p1_joint_selective_policy_v1`

Artifact:

`DEV037_P1_JOINT_SELECTIVE_POLICY_RESULT.json`

From the moment the canonical DEV037-P1 start marker is printed:

`DEV037-P1 MUST NEVER BE RERUN`

even if the canonical attempt fails.

## Next permitted action

DEV037-P0 real-data policy feasibility preflight only.

P0 may fit historical component models and S5 on OOF training rows because this
is required to derive frozen policy thresholds and operational feasibility.

P0 may inspect:

- exact support identity;
- OOF chronology;
- OOF row counts;
- component selected C values;
- OOF prediction hashes;
- q80 thresholds;
- validation score finiteness;
- action coverage;
- abstention count;
- LONG action count;
- SHORT action count;
- S5 OOF meta target class counts.

P0 must NOT inspect validation correctness:

- no validation action precision;
- no validation correct/false-action count;
- no validation outcome-conditioned policy comparison;
- no challenger-vs-S0 correctness delta;
- no temporal null;
- no survivor classification;
- no PnL;
- no fees/slippage;
- no forward data.

Scientific execution for any later canonical P1 must reset exactly to:

`32397bee3691ec746d8b845c919c6adcb157a308`

Current state:

`DEV037_P1_EXECUTION_FROZEN_P0_REAL_DATA_FEASIBILITY_PREFLIGHT_NEXT`

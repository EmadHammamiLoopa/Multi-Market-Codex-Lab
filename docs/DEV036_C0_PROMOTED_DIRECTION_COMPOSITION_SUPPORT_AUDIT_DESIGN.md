# DEV036-C0 — Promoted Direction × Frozen Touch Support Audit v1

Status: `DESIGN_FROZEN_BEFORE_ANY_COMPOSITION_REFIT`

Date: 2026-09-02

## 1. Scientific purpose

DEV030-P4 established a strong frozen TOUCH_VS_NONE head on target A:

- target = A
- horizon = 120 s
- barrier = 16 bp
- window = 32 s
- PRICE/S1 representation
- pooled support = 5748
- TOUCH = 573
- NONE = 5175
- S1 AP = 0.2942831079
- S1 ROC AUC = 0.7317547276
- S1 AP lift over prevalence = 2.9520755744x
- temporal-null AP q95 = 0.1675981527
- temporal-null AP p = 0.0007047216
- T2 eligible for composition = YES

However, the original P4 two-head composition failed because its frozen
conditional-direction head was the earlier DEV030-P3 head.

Since then, DEV034-G3C16 produced a new promoted direction-stage base:

`BTC45 = DEV030-P3 + G3C16 FULL_FROZEN_R_CONTEXT`

with pooled matched direction BA:

`0.5920001546112814`

DEV036 asks whether the already-successful frozen touch head can now be
composed with the stronger promoted direction head.

This C0 stage is support/provenance only.

No model fit or composition metric is authorized yet.

## 2. Why support audit is required

P4 TOUCH_VS_NONE evaluates all valid target-A rows:

- total = 5748
- TOUCH = 573
- NONE = 5175

BTC45 was frozen only on the G3C16-compatible T1 directional-touch support:

- rows = 1341
- LONG = 665
- SHORT = 676

Therefore the 22 G3C16 R-context features must be audited on the full P4 T2
support before any three-class composition can be defined.

It is forbidden to assume that the 1341-row direction support implies full
coverage of all 5748 T2 rows.

## 3. Frozen parent identities

### P4

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev030_p4_t2_composition_v1/DEV030_P4_T2_COMPOSITION_RESULT.json`

SHA256:

`8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`

Bytes:

`90545`

Official terminal status:

`FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE`

Retained component success:

`T2 TOUCH_VS_NONE = ELIGIBLE_FOR_COMPOSITION`

### G3B-R1 / BTC45

Canonical artifact:

`/home/emadh/Multi-Market/evidence/dev034_g3b_r1_common_support_screen_v1/DEV034_G3B_R1_COMMON_SUPPORT_SCREEN_RESULT.json`

SHA256:

`16200a1595d9472fe488740c0ab63e013b65824298ef1cb0b8856322416a8167`

Required survivor:

`G3C16`

Promoted direction base width:

`45 = 23 P3 + 22 R-context`

## 4. Audit question

For every row in the frozen P4 T2 support:

1. reconstruct the exact P4 T2 timestamp and TOUCH/NONE label;
2. verify exact BTCUSDT Phase0DL source identity;
3. test whether all 22 frozen G3C16 R-context features are causally valid;
4. record deterministic exclusion reason when they are not;
5. report resulting common support per day and campaign;
6. report TOUCH/NONE class counts;
7. verify every outer validation fold retains both TOUCH and NONE;
8. verify that the directional-touch subset embedded inside the resulting
   common support contains the already-frozen G3C16 support without drift.

## 5. Support policy

No candidate-specific support exists in DEV036-C0.

One deterministic support object only:

`P4_T2 ∩ G3C16_R_CONTEXT_VALID`

If any rows are excluded, exclusion is determined only by frozen causal R
feature validity, never by label or model result.

No imputation.
No fill.
No boundary repair.
No alternative lookback.
No dropping rows after seeing predictive metrics.

## 6. Required invariants

The audit must verify:

- exact P4 parent SHA;
- exact G3B parent SHA;
- exact seven BTC Phase0DL file hashes;
- exact P4 T2 support reconstruction;
- exact TOUCH/NONE counts before R filtering;
- exact causal R extraction semantics;
- exact 22-column R width;
- no nonfinite retained R row;
- chronological ordering;
- label independence of exclusion logic;
- frozen G3C16 directional support remains an exact subset of the new common
  support on the corresponding directional rows.

## 7. Required outputs

Read-only diagnostic first.

Per day report:

- P4 T2 rows
- TOUCH count
- NONE count
- R-valid rows
- R-invalid rows
- R-valid TOUCH count
- R-valid NONE count
- support SHA256
- exclusion reason counts

Campaign report:

- total original P4 T2 rows
- total retained common rows
- retained fraction
- TOUCH/NONE totals
- support SHA256
- label SHA256
- exclusion totals/reasons

Outer folds:

- Apr retained TOUCH/NONE
- May retained TOUCH/NONE
- Jun retained TOUCH/NONE
- Jul retained TOUCH/NONE

## 8. Feasibility classification

Descriptive only:

`HIGH_SUPPORT`
if retained fraction >= 0.95 and all validation folds contain both classes.

`USABLE_SUPPORT`
if retained fraction >= 0.90 and all validation folds contain both classes.

`THIN_SUPPORT`
if retained fraction >= 0.75.

Otherwise:

`NOT_USABLE`

This classification does not authorize predictive composition by itself.

## 9. Stop rule

If support is HIGH/USABLE:

- freeze a separate DEV036-C1 composition design;
- comparator and promoted-direction composition must use the exact same audited
  support.

If support is THIN/NOT_USABLE:

- do not silently shrink further;
- do not reopen G3C16 feature selection;
- close this promoted-direction composition route or design a separately
  justified alternative representation.

## 10. Strict prohibitions

DEV036-C0 must not:

- fit T2 again;
- fit BTC45 direction;
- score composition metrics;
- run temporal null;
- optimize thresholds;
- use EXP024 gating;
- open Aug-30;
- open Sep-01+;
- open Railway/archive/abundant-love;
- run PnL/economics;
- acquire new data.

## 11. Permanent upstream rules

`DEV034-G3A-R1 MUST NEVER BE RERUN`

`DEV034-G3B-R1 MUST NEVER BE RERUN`

`DEV035-G4B MUST NEVER BE RERUN`

## 12. Current state

`DEV036_C0_SUPPORT_AUDIT_DESIGN_FROZEN_DIAGNOSTIC_NEXT_NO_FIT`

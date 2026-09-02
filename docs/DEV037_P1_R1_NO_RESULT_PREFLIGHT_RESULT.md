# DEV037-P1-R1 No-Result Reproduction Preflight Result

Status: `PASS_SINGLE_CANONICAL_CORRECTNESS_SCREEN_NEXT`

Date: 2026-09-02

Scientific execution commit:

`25221269bee4681916af663b668cf1f4446a3294`

## Preflight result

- checks PASS = 22
- checks FAIL = 0
- preflight RC = 0
- focused tests = 6 passed
- test RC = 0
- harness smoke = PASS
- smoke RC = 0
- post-preflight git tree = clean
- canonical output remained absent
- canonical log remained absent

## Parent identity

DEV037-P0-R2 parent:

- SHA256 =
  `494122f1aea64fb2a4c956d674330d9a400709656f0e116187d6fa2fefaa3336`
- bytes = 27056
- selected controller = W120

All parent identity checks passed.

## Common support reproduction

Exact DEV036-C1 common support reproduced:

- rows = 9849
- TOUCH = 1341
- NONE = 8508
- support SHA256 =
  `dc89f3012341bd771591693b03af00b86f64f95aa4f7db4e9dc65b7e0e7f7b3f`

## W120 operational reproduction

All 16 policy-fold records reproduced exactly and remained feasible.

Fold 1 / Apr:

- S0 coverage 0.17057569296375266, actions 240, LONG 92, SHORT 148
- S1 coverage 0.20113717128642503, actions 283, LONG 23, SHORT 260
- S2 coverage 0.18336886993603413, actions 258, LONG 51, SHORT 207
- S5 coverage 0.17199715707178392, actions 242, LONG 89, SHORT 153

Fold 2 / May:

- S0 coverage 0.17484008528784648, actions 246, LONG 109, SHORT 137
- S1 coverage 0.19829424307036247, actions 279, LONG 43, SHORT 236
- S2 coverage 0.17981520966595593, actions 253, LONG 77, SHORT 176
- S5 coverage 0.17626154939587776, actions 248, LONG 83, SHORT 165

Fold 3 / Jun:

- S0 coverage 0.2082444918265814, actions 293, LONG 99, SHORT 194
- S1 coverage 0.19545131485429992, actions 275, LONG 62, SHORT 213
- S2 coverage 0.19545131485429992, actions 275, LONG 75, SHORT 200
- S5 coverage 0.20540156361051884, actions 289, LONG 98, SHORT 191

Fold 4 / Jul:

- S0 coverage 0.2281449893390192, actions 321, LONG 155, SHORT 166
- S1 coverage 0.20398009950248755, actions 287, LONG 95, SHORT 192
- S2 coverage 0.2125088841506752, actions 299, LONG 132, SHORT 167
- S5 coverage 0.22103766879886283, actions 311, LONG 159, SHORT 152

Frozen assertions:

`ALL_16_W120_POLICY_FOLD_RECORDS_REPRODUCED=PASS`

`ALL_16_W120_POLICY_FOLD_RECORDS_FEASIBLE=PASS`

## Explicit non-observation contract

The preflight did NOT:

- call validation action metrics;
- calculate validation action precision;
- calculate validation correct-action count;
- calculate validation false-action count;
- calculate challenger-vs-S0 correctness deltas;
- run temporal null;
- classify survivors;
- calculate correctness under W360/W720;
- calculate S3/S4 correctness;
- run PnL;
- run fees/slippage;
- open forward data.

Therefore no DEV037-P1-R1 correctness result has yet been observed.

## Next action

The single canonical DEV037-P1-R1 correctness screen is authorized next.

From its canonical start marker:

`DEV037-P1-R1 MUST NEVER BE RERUN`

even if the canonical attempt fails.

Current state:

`DEV037_P1_R1_ALL_PREFLIGHTS_PASS_SINGLE_CANONICAL_CORRECTNESS_SCREEN_NEXT`

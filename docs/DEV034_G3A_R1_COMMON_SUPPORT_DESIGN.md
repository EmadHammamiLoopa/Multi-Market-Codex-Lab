# DEV034-G3A-R1 — Common Full-R Support Recovery Design

Status: `DESIGN_FROZEN_NO_CANONICAL_MATERIALIZATION_NO_G3_MODEL_FIT`

Date: 2026-09-02

Parent design:
`DEV034-G3A`

Parent status:
`DEV034_G3A_PREEXECUTION_INFEASIBLE_FULL_R_NO_SUPPORT_SHRINK_NO_RESULT`

## 1. Why R1 is required

The original G3A design required all 1374 frozen P3 T1 rows to possess a valid
22-feature frozen R context.

Read-only feasibility diagnosis found:

- original P3 T1 support = 1374
- full-R eligible = 1341
- ineligible = 33
- eligibility fraction = 0.9759825327510917

Reasons:

- 30 = START_OF_DAY_30M_BOUNDARY
- 3 = BOOK_INVALID_IN_30M_HISTORY

This occurred before canonical G3A execution. No scientific result exists for
the original G3A design.

## 2. Frozen common-support rule

R1 preregisters one deterministic common-support eligibility rule for the
entire G3 family:

`eligible iff frozen EXP004 _r_features(day,current,spread) returns a finite 22-vector`

This mask:

- is computed only from causal feature availability;
- is independent of the direction label;
- is independent of candidate identity;
- is identical for P3 comparator and all 16 G3 candidates;
- may not be changed after predictive results are observed.

No candidate-specific row deletion is allowed.

## 3. Frozen common support

Expected campaign support from the diagnosis:

- rows = 1341
- LONG = 665
- SHORT = 676

Expected per-day support:

- Jan = 4
- Feb = 422
- Mar = 356
- Apr = 156
- May = 64
- Jun = 121
- Jul = 218

Expected outer validation support:

- Apr = 156 = 85 LONG / 71 SHORT
- May = 64 = 40 LONG / 24 SHORT
- Jun = 121 = 55 LONG / 66 SHORT
- Jul = 218 = 122 LONG / 96 SHORT

All four outer validation folds retain both classes.

## 4. Frozen invalid-row provenance

Expected invalid count = 33.

Reason counts exactly:

- START_OF_DAY_30M_BOUNDARY = 30
- BOOK_INVALID_IN_30M_HISTORY = 3

The three non-boundary rows are exactly:

- 2026-02-01T00:30:00+00:00
- 2026-06-01T00:30:00+00:00
- 2026-07-01T00:30:00+00:00

G3A-R1 artifact must serialize the complete 33-row exclusion ledger with:

- day
- timestamp_us
- UTC timestamp
- label
- exclusion reason

The mask/exclusion ledger becomes frozen scientific provenance.

## 5. G3A-R1 scope

G3A-R1 is materialization only.

It must:

- reconstruct exact frozen P3 T1 support;
- independently verify original P3 lineage;
- derive the single full-R eligibility mask;
- materialize only the common eligible rows;
- store the 22 frozen R_FEATURE_NAMES once;
- retain hashes for all 16 candidate subsets;
- retain full exclusion ledger;
- retain original-support and common-support hashes/counts.

It must NOT:

- fit any G3 direction model;
- score any G3 direction metric;
- run any temporal null;
- run PnL;
- access August/Sep-01+/Railway/archive/new acquisition.

## 6. Comparator rule for future G3B-R1

Future predictive comparison must NOT use the original P3 predictions as the
primary comparator on a different support.

Instead, after first verifying the original frozen P3 lineage, future G3B-R1
must re-fit the exact P3 model lineage on the same common-support training rows
and evaluate it on the same common-support validation rows as all G3
candidates.

Thus:

`delta_BA = BA(G3 candidate on common support) - BA(P3 refit on common support)`

The model protocol remains P3-exact:

- train-only StandardScaler
- LogisticRegression
- C grid 0.01, 0.1, 1.0, 10.0
- chronological inner C selection
- threshold 0.5
- same outer calendar
- random_state 20260825

## 7. Frozen G3 candidate universe

Exactly the same 16 candidates from the original G3 design.

No candidate is added, removed, renamed, or altered.

## 8. Stop rules

If G3A-R1 cannot reproduce the exact preregistered 1341-row common support and
33-row exclusion ledger, it fails closed.

If G3A-R1 succeeds, freeze and independently verify its artifact before any
G3B-R1 model fit.

Current state:

`DEV034_G3A_R1_COMMON_SUPPORT_DESIGN_FROZEN_IMPLEMENTATION_NEXT_NO_MODEL_FIT`

# DEV030-P2 Sequence Direction Design Freeze

Status: **DESIGN FROZEN BEFORE DEV030-P2 MODEL FITTING**

Parent branch: `research/dev030-p1-label-feasibility`

Parent head: `20e4ab1aa3b513d763ed9a1a141d095ee522ee0d`

Design branch: `research/dev030-p2-sequence-design`

DEV030-P1 immutable audit:
`/home/emadh/Multi-Market/evidence/dev030_p1_label_feasibility_v2/LABEL_FEASIBILITY_AUDIT.json`

DEV030-P1 audit SHA-256:
`3e2bdc7447290737df7f87f0e3eebce70be4e2071a54753fdc055b484f9f8a2a`

This document freezes a bounded direction-prediction development campaign. It
does not contain a fitted model, a model result, a PnL result, or a claim of
profitability. During its creation, Jan-Jul market files were not analytically
reopened, Aug-30 and Sep-01+ remained closed, and no model was fit.

## 1. Research question and scope

### 1.1 Primary question

Can causal temporal microstructure information available at decision time
`t` predict whether `LONG_FIRST` or `SHORT_FIRST` occurs first, conditional
on a directional first-passage event, better and more stably than matched
snapshot baselines?

This is the primary DEV030-P2 question. It isolates the missing direction
layer after DEV030-P1 established that usable first-passage labels exist.

### 1.2 Secondary question

Only if the primary direction diagnostic succeeds:

Can that conditional direction information be combined with a causal
`TOUCH`-versus-`NONE` model into a deployable abstention-aware pipeline?

### 1.3 Claim boundary

DEV030-P2 is predictive-direction development research on consumed Jan-Jul
data. It is not:

- a prospective confirmation;
- a trading strategy;
- a PnL or profitability experiment;
- an execution-policy optimization;
- a leverage or position-sizing experiment;
- permission to open Aug-30, Sep-01+, or any other forward partition.

## 2. Evidence and assets preserved

The following evidence constrains P2 and must remain unchanged.

### 2.1 EXP024

EXP024 prospectively confirmed that `rv_30m_bps` ranks the occurrence of a
large any-direction executable opportunity. It did not establish direction.
P2 therefore does not treat opportunity ranking as a directional feature and
does not condition its initial campaign on EXP024 scores.

### 2.2 EXP026 and EXP028

The prior direction/execution readiness pipelines were not ready. EXP026 had
a validation fold with no executed Candidate-A trade. EXP028 had only two
ACTIVE folds. P2 does not rescue those experiments, reuse their A/B/C
selection, or lower their gate. It asks the earlier question: does direction
information exist in recent microstructure paths?

### 2.3 DEV030-P1

DEV030-P1 established label feasibility, not predictability. Of 36 audited
geometries, 29 were `ROBUST_SUPPORT`, one was `USABLE_SUPPORT`, three were
`THIN_SUPPORT`, and three were `NOT_USABLE`.

The P1 result supports proceeding because the selected primary targets have
substantial, persistent, nearly balanced direction labels. It does not imply
that any feature predicts those labels.

### 2.4 Frozen components

P2 must reuse rather than alter:

- `src/multimarket/dev030_first_passage.py` for target creation;
- the exact 250 ms executable quote convention;
- entry at `t + 250 ms`;
- complete-path validity and same-row ambiguity invalidation;
- the exact consumed Jan-Jul BTCUSDT input provenance;
- Phase0DL timestamp, feature, and validity semantics;
- chronological month-level outer folds.

## 3. Frozen target geometries

The initial campaign contains exactly four geometries. No fifth geometry may
be added during P2A.

| Role | Horizon | Barrier | P1 support | LONG | SHORT | Directional | Balance | Median first touch | Margin after 12 bp |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| Primary economic A | 120 s | 16 bp | ROBUST | 684 | 690 | 1,374 | 0.991304347826087 | 66.25 s | +4 bp |
| Primary economic B | 300 s | 24 bp | ROBUST | 848 | 856 | 1,704 | 0.9906542056074766 | 165.125 s | +12 bp |
| Learnability control C | 300 s | 12 bp | ROBUST | 2,429 | 2,503 | 4,932 | 0.9704354774270875 | 121.5 s | 0 bp |
| Short/cost control D | 60 s | 8 bp | ROBUST | 1,223 | 1,237 | 2,460 | 0.9886822958771221 | 27.375 s | -4 bp |

The 300/12 target tests learnability with more labels but has no margin after
the 12 bp reference. The 60/8 target tests a shorter horizon but is explicitly
cost-challenged. Neither can establish that the economically more meaningful
targets are solved.

The 600/12 geometry is reserve-only. It is not part of the initial P2 search
and may not be introduced in response to P2A results.

## 4. Frozen task formulation

### 4.1 T1 — DIRECTION_GIVEN_TOUCH

T1 is the primary diagnostic.

Include only target-valid decisions labeled:

- `LONG_FIRST`, mapped to `1`;
- `SHORT_FIRST`, mapped to `0`.

Exclude:

- `NONE`;
- every invalid target;
- every `same_row_ambiguous` target.

T1 is an **oracle-touch diagnostic**. Membership in its support uses an ex
post fact—that a barrier was eventually touched. Consequently, T1 accuracy
must never be described as a deployable strategy or directly converted to a
trade backtest. Its sole purpose is to determine whether causal information at
`t` contains stable direction information conditional on a later touch.

### 4.2 T2 — TOUCH_VS_NONE

T2 is a secondary deployable component.

On all target-valid decisions:

- `LONG_FIRST` or `SHORT_FIRST` maps to `TOUCH`;
- `NONE` maps to `NONE`.

Invalid and same-row-ambiguous targets remain excluded. T2 must remain a
simple baseline until T1 passes the promotion gate on a primary economic
target. P2A does not tune T2.

### 4.3 T3 — later deployable composition

The later two-head composition is:

```text
P(LONG_FIRST | x)  = P(touch | x) * P(long | touch, x)
P(SHORT_FIRST | x) = P(touch | x) * (1 - P(long | touch, x))
```

An eventual action policy may abstain when touch probability or conditional
direction confidence is insufficient. No action threshold is chosen or tuned
in P2A.

A direct `LONG_FIRST`/`SHORT_FIRST`/`NONE` multiclass model may later be a
matched secondary comparison. It is not the primary P2 formulation.

## 5. Causal sequence windows

The initial sequence windows are exactly:

- 8 seconds;
- 16 seconds;
- 32 seconds;
- 60 seconds.

The grid is exactly 250 ms. A window begins at `t - W` and ends at `t`, both
inclusive. Thus the windows contain 32/64/128/240 250 ms intervals and
33/65/129/241 timestamped state observations respectively. A return series
formed between adjacent observations contains 32/64/128/240 increments.

The target path begins at `t + 250 ms`, never at `t`. No input at a timestamp
greater than `t` may enter:

- the snapshot;
- a sequence;
- a summary statistic;
- normalization;
- model selection;
- a diagnostic transformation.

There is no future interpolation, future backward fill, or filling across an
invalid state. Every timestamp must lie on the exact stored 250 ms grid.

## 6. Allowed-feature manifest

This manifest comes from repository source definitions, principally
`tools/v23_phase0dl_features250.cpp`,
`src/multimarket/v23_phase0dl_score.py`, and the point-in-time return
convention in `src/multimarket/codex_exp004_p1.py`. No CSV values were
inspected to create it.

Phase0DL stores 43 named L0/L1/L2 features plus timestamp, best bid, best ask,
mid, book validity, and the nested L0/L1/L2 validity masks. Initial P2 uses
BTCUSDT only. The historical source configuration also supports ETHUSDT, but
ETH and cross-asset features are excluded from the initial campaign. SOL has
no equivalent prepared historical Phase0DL set.

### 6.1 PRICE — executable and price state

Stored primitives:

- `spread_bps`;
- `microprice_minus_mid_bps`;
- `mid` solely as the source for causal returns and validity checks;
- `best_bid` and `best_ask` solely for target/executable-state verification,
  not as nonstationary raw price-level predictors.

Deterministic representation transform:

```text
mid_log_return_250ms_bps(s)
    = 10000 * log(mid(s) / mid(s - 250ms))
```

This return is a deterministic causal transform of the stored `mid`, not a
new market-data primitive. Both endpoint mids and the intervening book state
must be valid. P2A does not add a searched return-lag library.

The existing project also defines longer signed returns (`ret_1m_bps`,
`ret_3m_bps`, `ret_5m_bps`, `ret_10m_bps`, `ret_30m_bps`) in
`codex_exp004_p1._r_features`. They remain available for a later regime
ablation but are not included in the initial microstructure sequence campaign.

### 6.2 BOOK — displayed book state

Exact stored features added by `PRICE + BOOK`:

- `obi_l1`;
- `obi_l5`;
- `obi_l10`;
- `log_bid_qty_l1`;
- `log_ask_qty_l1`;
- `log_bid_depth_l5`;
- `log_ask_depth_l5`;
- `log_bid_depth_l10`;
- `log_ask_depth_l10`.

These are aggregate displayed-state features. They are not raw top-10
price/quantity matrices and do not identify individual orders or queue
position.

### 6.3 FLOW — order and trade flow

Exact stored features added by `PRICE + BOOK + FLOW`:

- `ofi_l1_250ms`;
- `ofi_l1_1s`;
- `ofi_l1_3s`;
- `mlofi_l5_250ms`;
- `mlofi_l5_1s`;
- `mlofi_l5_3s`;
- `mlofi_l10_250ms`;
- `mlofi_l10_1s`;
- `mlofi_l10_3s`;
- `trade_qty_imbalance_250ms`;
- `trade_qty_imbalance_1s`;
- `trade_qty_imbalance_3s`;
- `trade_count_imbalance_250ms`;
- `trade_count_imbalance_1s`;
- `trade_count_imbalance_3s`.

The 1 s and 3 s columns are already causal rolling aggregates produced by the
Phase0DL generator. Their overlap is part of the stored representation and
must not be mislabeled as independent observations.

### 6.4 DYNAMICS — book changes and interactions

Exact stored features added by `PRICE + BOOK + FLOW + DYNAMICS`:

- `d_obi_l1_250ms`;
- `d_obi_l1_1s`;
- `d_obi_l5_250ms`;
- `d_obi_l5_1s`;
- `d_obi_l10_250ms`;
- `d_obi_l10_1s`;
- `d_spread_bps_250ms`;
- `d_spread_bps_1s`;
- `d_microprice_minus_mid_bps_250ms`;
- `d_microprice_minus_mid_bps_1s`;
- `bid_replenish_l5_1s`;
- `ask_replenish_l5_1s`;
- `bid_deplete_l5_1s`;
- `ask_deplete_l5_1s`;
- `trade_qty_imbalance_1s_x_obi_l5`;
- `trade_qty_imbalance_1s_x_microprice_minus_mid_bps`;
- `mlofi_l5_1s_x_spread_bps`.

Replenishment and depletion are displayed-flow proxies based on equal-price
level comparisons. They do not support claims about order identity, exact
queue position, partial fills, or cancellation intent.

### 6.5 Incremental block order and exclusions

The only initial feature-block progression is:

1. `PRICE`;
2. `PRICE + BOOK`;
3. `PRICE + BOOK + FLOW`;
4. `PRICE + BOOK + FLOW + DYNAMICS`.

Excluded from the initial campaign:

- options and DVOL;
- ETH or SOL cross-asset features;
- EXP024 opportunity probabilities or ranks;
- EXP029 eligibility or gate state;
- funding, open interest, liquidations, macro, news, and on-chain data;
- any feature derived from Aug-30 or Sep-01+.

## 7. Validity and common support

For a block at decision `t`, every required Phase0DL validity mask must be
true for every stored row in `[t-W, t]`. The derived 250 ms return additionally
requires the prior endpoint needed by each return increment. All values must
be finite.

This stored-row validity interval is not the complete raw-source information
interval. Each stored primitive remains causal at its timestamp, but its value
may summarize earlier source events. Section 10 freezes the block-specific
internal-lookback accounting used for boundary checks and purging.

No imputation is allowed. A missing or invalid row invalidates that sample for
that representation.

Comparisons must use exact common support:

- S1 versus S0 uses the intersection of their valid rows for the same target,
  feature block, window, and fold;
- adjacent feature-block comparisons use the intersection of both blocks;
- model comparisons use identical labels and timestamp order;
- native-support counts are reported separately but never used for an
  unmatched performance comparison.

Support is fixed before fitting and must not be altered after labels,
predictions, or fold metrics are observed.

## 8. Frozen representations

### 8.1 S0 — matched snapshot baseline

S0 contains the latest causal value available at `t` for every feature in the
chosen block. Its evaluation rows are restricted to the same support as the
corresponding S1 window. This prevents a sequence model from winning or losing
merely because it was evaluated on different observations.

### 8.2 S1 — engineered causal sequence summaries

For every allowed primitive over each frozen window, compute exactly:

- `last`;
- arithmetic mean;
- population standard deviation (`ddof=0`);
- minimum;
- maximum;
- `last - first`;
- ordinary-least-squares slope against elapsed seconds.

The OLS time coordinate starts at zero and advances in exact 0.25-second
increments. Constant series have slope zero.

For naturally signed variables, add one sign-persistence statistic:

```text
sign_persistence = abs(mean(sign(value)))
```

where `sign(0) = 0`. This statistic lies in `[0, 1]`; signed direction remains
available through the other summaries.

Naturally signed variables are:

- the causal mid return;
- `microprice_minus_mid_bps`;
- all OBI features;
- all OFI and MLOFI features;
- all trade imbalance features;
- all `d_obi_*`, `d_spread_*`, and `d_microprice_*` features;
- the three stored signed interaction features.

The summary library may not expand during P2A. In particular, P2A excludes
arbitrary quantiles, arbitrary lag sets, EMA searches, wavelets, spectral
features, and automatically generated cross-products.

Raw sequence tensors are not part of Campaign 1 or Campaign 2.

## 9. Model ladder

Complexity is stage-gated. A model family cannot be used merely because a
previous level was disappointing.

### 9.1 M0 — controls

Report these non-tuned controls on every common-support fold:

- training-majority prediction, with a training tie mapped to `SHORT`;
- `microprice_minus_mid_bps >= 0` predicts `LONG`, else `SHORT`;
- `obi_l1 >= 0` predicts `LONG`, else `SHORT`;
- `ofi_l1_1s >= 0` predicts `LONG`, else `SHORT` when FLOW is present.

These controls are diagnostics, not candidate searches.

### 9.2 M1 — regularized logistic regression

Pipeline:

1. `StandardScaler`, fit on training rows only;
2. `LogisticRegression` with:
   - `penalty="l2"`;
   - `solver="lbfgs"`;
   - `class_weight=None`;
   - `max_iter=1000`;
   - `random_state=20260825`.

The only M1 hyperparameter grid is:

```text
C = [0.01, 0.1, 1.0, 10.0]
```

For each outer fold, the final month inside the outer training calendar is the
inner validation month; all earlier outer-training months form the inner fit.
Select C by inner balanced accuracy, then inner macro F1, then the smaller C.
Refit scaler and logistic regression on the complete outer training calendar
using the selected C. Outer validation labels never select C.

Prediction is `LONG` iff `p_long >= 0.5`; otherwise `SHORT`. No confidence
threshold is searched in P2A.

### 9.3 M2 — controlled nonlinear boosting

M2 is permitted only for target/representation/block/window combinations that
survive Campaign 1. It uses `sklearn.HistGradientBoostingClassifier` on the
same engineered summaries, with training-only chronological selection over:

```text
learning_rate   = [0.05, 0.10]
max_leaf_nodes  = [7, 15]
max_iter        = 200
min_samples_leaf = 20
l2_regularization = [0.0, 1.0]
early_stopping  = False
random_state    = 20260825
```

Tie order prefers lower learning rate, fewer leaves, and stronger L2.

### 9.4 Deferred levels

- M3: a small MLP on the same summaries, only after stable M1/M2 information;
- M4: a small causal 1D-CNN or TCN on raw sequences, only after S1 adds value;
- M5: TLOB/Transformer-style attention, deferred.

M3 and M4 require a reviewed campaign amendment that freezes their exact
architectures before fitting. M5 is not authorized by this design.

## 10. Chronological validation

Use BTCUSDT Jan-Jul 2026 only, with exact expanding outer folds:

| Fold | Train | Validate |
|---|---|---|
| 1 | Jan-Mar | Apr |
| 2 | Jan-Apr | May |
| 3 | Jan-May | Jun |
| 4 | Jan-Jun | Jul |

There is no random row shuffle. Each full validation day remains intact.

Every sample has two distinct causal intervals.

### 10.1 Representation row interval

The stored feature rows supplied to S0/S1 are exactly:

```text
[t - sequence_window, t]
```

No representation row after `t` is allowed. This interval describes stored
row timestamps, not the full source history used to construct those rows.

### 10.2 Underlying raw-source information interval

Let `L_block` be the maximum causal internal lookback of any primitive or
transform in the selected feature block. The complete information interval
for purging, boundary checks, provenance, and leakage tests is:

```text
[t - sequence_window - L_block, t + 250ms + target_horizon]
```

The representation input still ends at `t`; the future portion is used only
by the frozen target labeler. A stored 3-second aggregate does not begin at its
row timestamp: it is causal and available at that timestamp, while its raw
source information extends backward through its internal lookback.

For the initial P2 manifest, the maximum known internal lookback is 3 seconds
when the selected block contains the stored 3-second OFI, MLOFI, or trade-flow
primitives. The derived `mid_log_return_250ms_bps(s)` requires `s - 250ms`,
which contributes a 250 ms internal lookback but does not exceed the 3-second
maximum when the full FLOW block is present. For a block that contains no
3-second primitive, the implementation must derive and use that block's exact
`L_block`; it must not assign 3 seconds blindly when a smaller exact bound is
known.

Frozen Phase0DL validity masks may continue to establish value validity, but
the implementation must record both intervals and the exact `L_block` used for
every prepared candidate.

Every train/validation boundary must be checked so no training target interval
reaches the validation period and no validation feature interval reaches into
future data. Whole-day/month separation naturally exceeds the maximum
information interval, but the implementation must prove this rather than
assume it.

Inner model selection is chronological and wholly inside outer training data.
All scaling, hyperparameter selection, and learned parameters are training
only. Fold predictions are concatenated chronologically only after all four
outer models have been independently fit.

## 11. Primary metrics

For T1, report per outer fold and pooled out-of-fold:

- support;
- LONG count and SHORT count;
- predicted LONG count and predicted SHORT count;
- balanced accuracy;
- macro F1;
- Matthews correlation coefficient;
- LONG precision, recall, and F1;
- SHORT precision, recall, and F1;
- confusion matrix in fixed order `[SHORT, LONG]`.

The primary representation comparison is S1 versus its matched S0 model on
exact common support. Report per fold and pooled:

```text
delta_balanced_accuracy = BA(S1) - BA(S0)
delta_macro_f1          = macro_F1(S1) - macro_F1(S0)
```

Do not pool first and hide fold instability. Report native support, common
support, class counts, and all fold metrics before pooled summaries.

No PnL, fee-adjusted return, profit factor, drawdown, Sharpe ratio, capital
simulation, or leverage metric belongs in P2A.

## 12. Temporal and causal falsification

### 12.1 Primary within-day direction-label null

For each candidate, order each outer validation fold's T1 rows by decision
timestamp and group them by UTC validation day. Keep fitted scores and
predictions fixed. Circularly shift binary direction labels independently
inside each UTC-day group only:

```text
y_shifted_fold_day = np.roll(y_fold_day, k)
```

Never wrap a label across a UTC-day boundary. Even when a prepared validation
fold contains one UTC day and the arithmetic is numerically equivalent, the
implementation must remain day-grouped by construction.

Use the same deterministic integer `k` across fold/day groups in a pooled null
replicate only when `k` is eligible for every participating group. Eligible
shifts are every integer `k` satisfying, for each participating UTC-day group:

```text
k > 0
min(k, n_fold_day - k) >= 10
```

A displacement of `k=10` T1 positions corresponds to at least 10 minutes of
decision-time separation on the 60-second decision grid when T1 rows are
consecutive; because T1 excludes `NONE` rows, actual elapsed separation may be
longer. This comfortably exceeds the maximum initial P2 information span of
approximately `60s + 3s + 250ms + 300s = 363.25 seconds`. Do not use `k=0`, random
subsampling, cross-day or cross-fold shifts, or training-label permutation.
If a UTC-day group lacks enough T1 support for the frozen shift rule, record
that explicitly; never combine or wrap it with another day to manufacture
support. Require at least 20 eligible shared shifts; otherwise the candidate
cannot pass the temporal null gate.

For every shift, concatenate folds in chronological order and compute pooled
balanced accuracy. Define:

```text
null_q95 = np.quantile(null_values, 0.95, method="higher")

empirical_p =
    (1 + count(null_values >= observed_value))
    / (1 + number_of_null_values)
```

The real pooled balanced accuracy must be strictly greater than `null_q95`
and empirical `p <= 0.05` for promotion. Macro-F1 null results are reported as
secondary diagnostics.

### 12.2 Sequence-order reversal

Reverse the raw chronological order inside every validation sequence, then
recompute S1 summaries and score with the unchanged trained model. Do not
refit. This changes endpoint and trend information while preserving the
multiset of sequence values.

### 12.3 Within-sequence time permutation

Apply one deterministic position permutation to every validation sequence in
a fold/window, recompute summaries, and score without refitting. The
permutation seed is derived with SHA-256 from:

```text
20260825 | target | window | outer_fold | "time_permutation"
```

The permutation is created without labels and is identical across samples in
that fold. Marginal values are preserved while temporal order is broken.

### 12.4 Feature-block permutation

On validation data only, cyclically shift the newly added feature block across
chronological samples while leaving earlier blocks, labels, and timestamps in
place. Use displacement:

```text
k = max(10, floor(n_fold / 3))
```

reduced only if required to keep `k < n_fold`. Preserve all columns within the
block as a unit and do not refit. This diagnoses whether an apparent block
gain depends on correct feature/label alignment.

The reversal and permutation diagnostics are explanatory. They cannot rescue
a failure of the primary temporal-label null.

## 13. Engineering promotion gate

A sequence representation advances from P2A only if all conditions below hold
on at least one primary economic target, 120/16 or 300/24:

1. pooled OOF balanced accuracy is at least `0.54`;
2. median outer-fold balanced accuracy is strictly greater than `0.50`;
3. at least three of four outer folds have balanced accuracy above `0.50`;
4. pooled S1-minus-matched-S0 balanced-accuracy delta is at least `+0.02`;
5. the balanced-accuracy delta is positive in at least three of four folds;
6. both classes are genuinely predicted: each fold predicts at least one LONG
   and one SHORT, and pooled predicted-minority fraction is at least `0.10`;
7. observed pooled balanced accuracy is strictly above temporal-null q95 and
   its one-sided empirical p-value is at most `0.05`;
8. gains are not explained by one validation day: after omitting each fold in
   turn, pooled S1-minus-S0 balanced-accuracy delta remains strictly positive.

This is an engineering promotion gate, not an academic truth claim or a
profitability claim.

### 13.1 Search-aware interpretation and complete trial ledger

Campaign 1 intentionally evaluates multiple frozen targets, sequence windows,
and incremental feature blocks. Every candidate attempted, including every
failure, must be retained in an append-only trial ledger with its complete
configuration, support, fold results, diagnostics, and failure reason. No
candidate may disappear from the ledger after its outcome is known.

The candidate-level temporal-null empirical `p <= 0.05` gate is a bounded
development diagnostic. It is not a family-wise-error-corrected confirmatory
p-value across the Campaign-1 search. This design does not add a complicated
multiple-testing correction; the untouched forward-confirmation layer serves
that role.

A candidate satisfying P2A is labeled only:

```text
ELIGIBLE_FOR_NEXT_DEVELOPMENT_STAGE
```

It must never be labeled or described as `CONFIRMED_DIRECTION_SIGNAL`. After
development selection, exactly one final configuration and policy must be
frozen before any untouched forward evaluation. Only a later untouched
forward test can provide prospective confirmation.

If 300/12 or 60/8 passes but both primary economic targets fail, record that
direction may be learnable only on an easier or cost-challenged target. Do not
call direction solved and do not advance to deployable composition.

If every T1 sequence representation fails to beat its matched snapshot
materially, stop the initial direction campaign. Do not escalate to boosting,
MLPs, CNNs, TCNs, or attention merely to search for a survivor.

## 14. Bounded development campaigns

### Campaign 1 — representation

Targets:

- 120/16;
- 300/24;
- 300/12;
- 60/8.

Task: T1 only.

Models: M0 and M1 only.

Comparisons:

- S0 versus S1;
- incremental feature blocks;
- 8/16/32/60-second windows.

Purpose: determine whether temporal summaries add stable direction
information beyond the latest matched state.

### Campaign 2 — nonlinearity

Only Campaign-1 survivors may enter. Use M2 on the same support and same S1
features. Do not add targets, windows, feature blocks, or a new boosting
library.

### Campaign 3 — raw temporal model

Only if Campaign 1 or 2 establishes stable sequence information. A separately
reviewed amendment must freeze a small causal CNN/TCN. Compare it on exactly
the winning engineered-summary support.

### Campaign 4 — deployable composition

Only if T1 passes on a primary economic target. Develop a simple T2
`TOUCH_VS_NONE` baseline and combine it with the frozen T1 head. A direct
three-class model may be a matched secondary baseline. Threshold and economic
evaluation require later freezes.

P2A reports every tested combination and every gate. It does not add a target,
window, feature, or model after seeing outer results.

## 15. Prohibitions

P2A must not perform:

- PnL or capital simulation;
- leverage or position sizing;
- stop-loss or take-profit optimization;
- execution-policy optimization;
- opportunity-gate or opportunity-threshold optimization;
- confidence-threshold search on outer folds;
- T2 development before T1 promotion;
- raw Transformer or TLOB training;
- cross-asset expansion;
- options, DVOL, funding, OI, liquidation, or external-data addition;
- collector changes;
- EXP025 or EXP027 changes;
- Aug-30 or Sep-01+ access.

## 16. Why this design follows the evidence

EXP024 established opportunity ranking, not direction. EXP026 and EXP028
showed that the previous direction/execution schedules were not ready. P1 now
shows abundant, balanced first-passage labels on the selected geometries.

The 120/16 and 300/24 classes are nearly perfectly balanced, persist across
all seven development days, and retain positive gross barrier distance after
the 12 bp reference. T1 therefore avoids `NONE` dominance and directly tests
the missing question: conditional directional predictability.

The 300/12 geometry supplies label-rich learnability evidence but has zero
margin after the 12 bp reference. The 60/8 geometry tests a shorter horizon
but is cost-challenged. These controls help distinguish “direction cannot be
learned” from “direction is visible only where costs are unfavorable.”

The oracle-touch diagnostic is intentionally non-deployable. It must never be
presented as an action policy or trading strategy.

[Kolm, Turiel & Westray, *Deep Order Flow Imbalance: Extracting Alpha at
Multiple Horizons from the Limit Order Book*](https://doi.org/10.1111/mafi.12413)
motivates stationary order-flow representations and multi-horizon testing.
It does not establish transfer to Binance BTCUSDT or executable profitability.

[Berti & Kasneci, *TLOB: A Novel Transformer Model with Dual Attention for
Price Trend Prediction with Limit Order Book Data*](https://arxiv.org/abs/2502.15757)
motivates temporal/feature-axis modeling while also reinforcing the need for
strong simple baselines. Current Phase0DL aggregates cannot reproduce a
faithful raw TLOB input. Attention is therefore deferred.

The literature and prior repository failures support the same ladder:
representation before capacity, stationary flow before raw levels, exact
chronology, simple models first, and no inference that model complexity is
evidence of alpha.

## 17. Implementation contract for later work

Recommended new modules:

- `src/multimarket/dev030_sequence_features.py` — pure window extraction,
  validity, S0, and S1 summaries;
- `src/multimarket/dev030_direction_dataset.py` — exact target/feature joins,
  task maps, common support, and fold manifests;
- `src/multimarket/dev030_p2_direction.py` — bounded Campaign-1 fitting,
  falsification, metrics, and immutable development result writing;
- `tests/test_dev030_sequence_features.py`;
- `tests/test_dev030_direction_dataset.py`;
- `tests/test_dev030_p2_direction.py`.

Reuse:

- the frozen first-passage labeler;
- the exact Phase0DL loader/schema after provenance verification;
- existing JSON-safety, built-in-bool, git-lineage, and atomic-output helpers;
- sklearn metric primitives directly.

Required synthetic tests before any model fit include:

- exact window boundaries and inclusive row counts;
- exact distinction between `[t-W, t]` representation rows and the expanded
  block-specific raw-source information interval;
- exact per-primitive internal-lookback manifest and exact `L_block`
  derivation, including 3 seconds for blocks containing the frozen 3-second
  flow primitives and 250 ms for the derived mid return where it is maximal;
- purging, boundary, provenance, and leakage checks use
  `[t-W-L_block, t+250ms+H]` rather than only stored row timestamps;
- no value after `t` affects a feature;
- missing/invalid lookback invalidates the representation;
- exact 43-column stored-feature manifest;
- deterministic 250 ms return arithmetic;
- exact summary formulas and sign persistence;
- S0/S1 exact common support;
- T1/T2 label mapping and invalid exclusion;
- exact four folds and chronological inner selection;
- train-only scaling and C selection;
- no outer-label hyperparameter fit;
- per-fold metric arithmetic and confusion-matrix order;
- deterministic day-local null shift set, no cross-day wrapping, explicit
  insufficient-day support, q95, and empirical p-value;
- reversal and permutation diagnostics;
- each promotion gate independently vetoes advancement;
- every bounded-search candidate and failure remains in the trial ledger, and
  a passing candidate is labeled only `ELIGIBLE_FOR_NEXT_DEVELOPMENT_STAGE`;
- forbidden data, model, economic, and collector interfaces are absent.

The later execution must record source/test/config hashes, exact input
manifest, folds, support timestamps or deterministic support hashes, selected
training-only hyperparameters, all fold/pooled metrics, all falsification
results, each promotion boolean, runtime guards, and JSON-safe artifacts.

## 18. Immediate next step

After human review and commit of this design, implement only the pure causal
window/summary engine and synthetic tests first. Do not fit Campaign 1 in the
same implementation task.

The first implementation review should prove:

1. exact allowed-feature identity;
2. exact `[t-W, t]` causality;
3. full-window validity;
4. exact summary arithmetic;
5. S0/S1 common-support equality;
6. no filesystem or model behavior inside the pure feature engine.

Only after that implementation is frozen and tested may a separate authorized
task build the Jan-Jul T1 datasets and fit Campaign 1.

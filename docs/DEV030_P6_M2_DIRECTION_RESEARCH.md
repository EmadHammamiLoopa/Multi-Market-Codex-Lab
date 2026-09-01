# DEV030-P6 Research Review — Bounded Nonlinear Direction Capacity

Date: 2026-09-02

Purpose: external research review performed before freezing DEV030-P6.

This note is decision support for the next consumed-development experiment. It
does not alter any frozen P3/P4/P5 result and it does not authorize model
fitting.

## 1. Current empirical state

The project has now isolated the bottleneck:

- P4 T2 TOUCH_VS_NONE is strong and stable on
  A / 120s / 16bp / 32s / PRICE.
- Frozen P3 M1 conditional direction is materially weaker:
  pooled ROC AUC 0.5367264882 and pooled balanced accuracy 0.5419424831
  on 573 chronological OOF touch rows.
- P4 two-head composition did not improve joint probability quality over C1.
- P5 direct linear three-class J1 was worse than C1 in all four folds.

Therefore the next narrow question is whether the already-frozen PRICE
sequence summaries contain nonlinear directional structure that regularized
logistic regression cannot express.

## 2. Data geometry matters for the model choice

The selected PRICE S1 representation is compact tabular data, not a raw LOB
tensor.

PRICE contains three causal series:

1. spread_bps
2. microprice_minus_mid_bps
3. mid_log_return_250ms_bps

The frozen S1 summarizer produces:
- 7 summaries for spread
- 8 summaries for microprice-minus-mid
- 8 summaries for signed mid return

Therefore P6 has exactly 23 input features.

Frozen T1 support:
- total Jan-Jul touch rows = 1,374
- chronological OOF validation rows = 573
- Fold 1 validation = 159
- Fold 2 validation = 64
- Fold 3 validation = 126
- Fold 4 validation = 224

This is a small, low-dimensional tabular problem with only seven consumed
calendar days and a clear regime/nonstationarity concern.

## 3. Why P6 should not start with a deep neural network

Grinsztajn, Oyallon, and Varoquaux (NeurIPS 2022) benchmarked tree ensembles
against modern neural architectures on typical tabular datasets and found that
tree-based models remained state of the art on medium-sized tabular data. Their
analysis emphasizes robustness to uninformative features and irregular
decision functions as key tree-model advantages.

Reference:
L. Grinsztajn, E. Oyallon, G. Varoquaux,
"Why do tree-based models still outperform deep learning on typical tabular
data?", NeurIPS 2022.
arXiv:2207.08815.

The 2025 TabPFN Nature paper also describes the longstanding difficulty of
ordinary deep learning on small/medium tabular datasets and notes the historic
dominance of gradient-boosted trees. TabPFN itself is intentionally not chosen
here: it would introduce a pretrained foundation-model dependency and a large
methodological jump when the scientific question only requires a controlled
capacity escalation.

Reference:
N. Hollmann et al.,
"Accurate predictions on small data with a tabular foundation model",
Nature 637, 319-326 (2025).

DeepLOB is important evidence that deep architectures can learn short-horizon
LOB structure, but it uses large-scale raw limit-order-book sequences with
CNN/LSTM inductive structure. That is a different data regime from 1,374
touch-conditioned rows represented by 23 engineered summary features.

Reference:
Z. Zhang, S. Zohren, S. Roberts,
"DeepLOB: Deep Convolutional Neural Networks for Limit Order Books",
IEEE Transactions on Signal Processing / arXiv:1808.03668.

Conclusion:
calling an MLP/CNN/LSTM "M2" now would increase capacity far more than needed
to answer the immediate scientific question and would make a failure harder
to diagnose.

## 4. Evidence that nonlinear microstructure models can matter

Kolm, Turiel, and Westray (Mathematical Finance 2023) show that high-frequency
forecasting performance can improve when models consume stationary
microstructure/order-flow inputs rather than raw book states. Their strongest
setting has far more observations and richer order-flow information than P6,
so the result motivates nonlinear capacity but does not justify a large neural
network here.

Reference:
P. N. Kolm, J. Turiel, N. Westray,
"Deep order flow imbalance: Extracting alpha at multiple horizons from the
limit order book", Mathematical Finance 33 (2023), 1044-1081.
DOI:10.1111/mafi.12413.

Tsantekidis et al. likewise report advantages from stationary LOB
representations before applying deep models.

Reference:
A. Tsantekidis et al.,
"Using Deep Learning for price prediction by exploiting stationary limit order
book features", Applied Soft Computing 93 (2020), 106401.

Recent crypto-specific work reinforces the broader point that order-book and
event-flow structure can carry short-horizon directional information. A 2026
open-access BTC study using multivariate Hawkes processes emphasizes
non-stationarity and richer LOB event dynamics; it also reviews evidence that
imbalance variables are related to future price changes.

Reference:
D. Raffaelli et al.,
"Forecasting Bitcoin price movements using multivariate Hawkes processes and
limit order book data", Decisions in Economics and Finance (2026).
DOI:10.1007/s10203-026-00570-z.

A 2026 crypto-microstructure study by Bieganowski and Slepaczuk reports
cross-asset stability of engineered order-book/trade features under a CatBoost
pipeline. This is encouraging for nonlinear trees, but that work uses much
larger 1-second multi-asset data and richer book/trade information. It should
not be treated as evidence that P6 must pass.

Reference:
B. Bieganowski, R. Slepaczuk,
"Explainable Patterns in Cryptocurrency Microstructure",
arXiv:2602.00776 (2026).

## 5. Why the validation must remain conservative

The most relevant caution from recent BTC evidence is that short-horizon
microstructure effects can change materially as more days are added.

A 2026 working paper by Michael Schmalz reports that the out-of-sample sign of
an OFI result reversed twice as a BTC/USDT capture expanded from roughly 7 to
9 to 17 days. The paper uses walk-forward evaluation, purge/embargo, HAC
inference, and moving-block bootstrap. It is a recent working paper rather than
a settled benchmark, so it is used here as a cautionary example rather than an
authority.

Reference:
M. Schmalz,
"Order Flow Imbalance and Short-Horizon BTC/USDT Returns: A Signal That Kept
Needing More Scrutiny", SSRN 7227998 (2026).

This is directly relevant because DEV030 currently has seven consumed
development days. Therefore P6 must not accept a pooled win that is carried by
one day.

Required consequence:
- preserve the exact expanding chronological folds;
- require fold-level and leave-one-fold-out stability;
- keep the forward holdout closed;
- do not compensate for a weak fold by broad hyperparameter search.

## 6. Overlapping future-horizon labels

Financial labels measured over future intervals can leak across train/test
boundaries when their evaluation windows overlap. Purging/embargo is a standard
guard for this problem.

DEV030's outer folds are separated by calendar days/months and the target
builder rejects day-boundary-crossing labels. Therefore no train-label interval
at the end of a consumed day can overlap a validation label interval on the
next consumed calendar day.

P6 should still implement an explicit interval-overlap assertion from the
frozen information-interval contract rather than merely assuming safety.

Reference for the general issue:
E. Lazarev,
"purgedcv: scikit-learn-compatible purged and combinatorial cross-validation
for time-series and financial machine learning" (2026 software paper /
documentation), implementing the López de Prado overlap/purge framework.

## 7. Why probability quality becomes primary in P6

P3 promoted M1 mainly using balanced accuracy and macro F1 because it was a
direction-learnability campaign.

P4 then showed that a direction head can improve classification diagnostics
without improving the downstream three-class probability distribution.
Therefore P6 must evaluate whether M2 improves conditional directional
probabilities, not just the 0.5 decision rule.

Log loss and Brier score are strictly proper scoring rules. A probability
forecast minimizes expected proper loss only by reporting the true conditional
probability distribution. This makes them appropriate primary measures for a
head intended for later probabilistic composition.

Reference:
T. Silva Filho et al.,
"Classifier calibration: a survey on how to assess and improve predicted class
probabilities", Machine Learning (2023).

scikit-learn 1.9 documentation likewise treats log loss and Brier as proper
probability scoring rules.

Consequence:
- pooled conditional log loss is the first P6 comparison criterion;
- Brier is second;
- ROC AUC measures directional ranking;
- BA/macro F1/MCC at threshold 0.5 remain diagnostics;
- no threshold optimization is allowed.

## 8. Why HistGradientBoostingClassifier is the preferred M2

For this exact P6 geometry, the best controlled capacity step is
scikit-learn's HistGradientBoostingClassifier (HGB), not an MLP.

Reasons:

1. It adds nonlinear thresholds and interactions to the same 23 features.
2. It remains an ordinary open-source scikit-learn dependency already present
   in the frozen environment.
3. Its native binary classification loss is log loss and it exposes
   predict_proba.
4. Capacity can be tightly bounded with max_leaf_nodes, max_iter,
   min_samples_leaf, learning_rate, and L2 leaf regularization.
5. It does not require scaling.
6. With early_stopping=False, it does not create an extra internal random
   validation split.
7. It is materially more expressive than M1 but far less of a methodological
   jump than CNN/LSTM/Transformer/TabPFN.

scikit-learn 1.9 documents HGB with native log-loss classification,
max_leaf_nodes capacity control, min_samples_leaf, L2 regularization, and
explicit early-stopping behavior.

Reference:
scikit-learn 1.9,
HistGradientBoostingClassifier documentation.

## 9. Recommended bounded M2 capacity grid

Do not perform a generic hyperparameter sweep.

Freeze one model family and four capacities:

| ID | max_leaf_nodes | max_iter |
| --- | ---: | ---: |
| H1 | 3 | 50 |
| H2 | 3 | 100 |
| H3 | 7 | 50 |
| H4 | 7 | 100 |

Fixed across all four:
- loss = log_loss
- learning_rate = 0.05
- min_samples_leaf = 20
- l2_regularization = 1.0
- max_features = 1.0
- max_bins = 255
- early_stopping = False
- class_weight = None
- categorical_features = None
- random_state = 20260825

The last outer-training day remains the only inner-validation day.

Inner selection order:
1. lowest binary log loss
2. lowest Brier
3. highest ROC AUC
4. fewer max_leaf_nodes
5. fewer max_iter

This is a four-point capacity test, not tuning-by-search.

## 10. Recommended promotion philosophy

A capacity increase should earn its complexity.

M2 should only advance if it improves frozen M1:
- proper probability quality pooled;
- directional ranking pooled;
- most individual outer folds;
- every leave-one-fold-out aggregate;
- and a paired day-local temporal-label null.

A small isolated threshold-accuracy increase is not enough.

The temporal null should hold M1 and M2 probabilities fixed and circularly
shift the validation labels within each day by the same eligible k. The null
statistic should be the paired M1-minus-M2 log-loss improvement under the same
shifted labels.

## 11. What P6 should not do

P6 should not:
- add PRICE_BOOK/FLOW/DYNAMICS;
- revisit the 64-candidate P3 representation search;
- tune the target, horizon, barrier, or window;
- use class weights or resampling;
- calibrate M2 post hoc;
- optimize an action threshold;
- compose with T2;
- run PnL/economics;
- open Aug-30 or Sep-01+;
- use ETH/SOL;
- use a deep neural model.

If HGB fails, the clean conclusion is that modest nonlinear capacity does not
rescue direction on the frozen PRICE representation.

At that point the next question becomes information content, not more
capacity.

## 12. Research conclusion

Recommended P6:

> A single-family, four-capacity HistGradientBoostingClassifier test of
> T1 LONG_FIRST vs SHORT_FIRST on the exact frozen
> A / 120s / 16bp / 32s / PRICE / S1 support, compared against exact
> reconstructed frozen P3 M1 probabilities under proper scoring, day stability,
> and paired temporal-null gates.

This design maximizes information gained from the next experiment while
minimizing new researcher degrees of freedom.

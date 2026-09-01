# DEV030-P7 Research Review — Incremental Order-Flow Information

Date: 2026-09-02

Purpose: external research review before freezing DEV030-P7.

This note motivates exactly one new information family after P6 established
that bounded nonlinear model capacity does not solve the frozen PRICE
direction bottleneck.

## 1. Empirical trigger from DEV030

Frozen evidence now says:

- P4 T2 TOUCH_VS_NONE is strong and remains the best deployability-relevant
  predictor.
- P3 found a weak but non-random T1 DIRECTION_GIVEN_TOUCH signal on
  A / 120s / 16bp / 32s / PRICE / S1.
- P5 direct linear three-class composition failed.
- P6 bounded HistGradientBoosting improved pooled log loss/Brier slightly but
  did not improve directional AUC and failed stability gates.

Therefore the next experiment should change **information**, not model
capacity.

## 2. Why order-flow imbalance is the preferred next family

Cont, Kukanov, and Stoikov show that short-interval price changes are strongly
related to order-flow imbalance at the best bid/ask, and that OFI is more
robust than raw traded volume as a short-horizon price-impact variable.

Reference:
R. Cont, A. Kukanov, S. Stoikov,
"The Price Impact of Order Book Events", 2010/2014.
arXiv:1011.6402.

Gould and Bonart show that queue imbalance contains predictive information for
the direction of the next mid-price move, including probabilistic logistic
classification improvements over a null model.

Reference:
M. D. Gould, J. Bonart,
"Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book",
2015.
arXiv:1512.03492.

Xu, Gould, and Howison show that multi-level order-flow imbalance improves
out-of-sample fit as additional book levels are included. This supports the
broader idea that imbalance measures deeper in the book can carry incremental
information, but P7 deliberately does **not** open a multi-level search yet.

Reference:
K. Xu, M. D. Gould, S. D. Howison,
"Multi-Level Order-Flow Imbalance in a Limit Order Book",
Market Microstructure and Liquidity / arXiv:1907.06230.

Kolm, Turiel, and Westray show that stationary order-flow-derived inputs can
outperform raw order-book states for high-frequency forecasting. Their study
uses much larger Nasdaq data and richer model classes, so P7 uses it as an
information-family motivation, not as justification for deep learning.

Reference:
P. N. Kolm, J. Turiel, N. Westray,
"Deep order flow imbalance: Extracting alpha at multiple horizons from the
limit order book", Mathematical Finance 33 (2023), 1044-1081.
DOI:10.1111/mafi.12413.

## 3. Why P7 starts with L1 OFI only

The repository already contains causal frozen features:

- ofi_l1_250ms
- ofi_l1_1s
- ofi_l1_3s
- mlofi_l5_*
- mlofi_l10_*
- trade imbalance families

Opening all of them together would recreate a broad feature search after the
P6 stop rule.

P7 therefore freezes the smallest research-backed family:

> top-of-book L1 order-flow imbalance at 250 ms, 1 s, and 3 s horizons.

This family is chosen before fitting.

P7 does NOT test:
- mlofi_l5
- mlofi_l10
- trade quantity imbalance
- trade count imbalance
- queue-depth features
- replenishment/depletion features
- dynamics interactions

Those remain future DEV questions only if P7 gives a scientifically useful
result.

## 4. Why the baseline model remains logistic

P7 asks whether OFI adds information.

Using the same low-complexity regularized logistic family as P3 makes that
question easier to interpret than changing both features and model family.

Therefore:
- baseline = PRICE S1 regularized logistic;
- augmented = PRICE S1 + frozen L1 OFI summaries, regularized logistic;
- same preprocessing and chronological C-selection protocol.

This isolates information gain.

## 5. Matched-support requirement

The OFI family is only valid where the FLOW representation is valid.

The PRICE baseline has slightly broader support than FLOW in P2C.

Therefore P7 must **not** compare:
- frozen P3 PRICE predictions on one support
against
- OFI-augmented predictions on a smaller support.

Instead P7 has two baseline roles:

1. **Frozen P3 reproduction** on the original P3 support as provenance.
2. **Matched C0 baseline**: PRICE-only logistic refit on the exact OFI-valid
   support using the same chronological training/validation rows as C1.

Primary incremental inference is C1 vs matched C0.

This is required to avoid support-selection confounding.

## 6. Exact new feature family

For each of the three frozen OFI series:

- ofi_l1_250ms
- ofi_l1_1s
- ofi_l1_3s

use the existing frozen S1 statistics only:

- last
- mean
- std
- minimum
- maximum
- last_minus_first
- ols_slope
- sign_persistence

Thus the new family contributes exactly 24 features.

PRICE S1 contributes 23 features.

Total augmented C1 feature count = 47.

No new feature formula is introduced.

## 7. Why multiscale OFI is preferable to one arbitrary horizon

The repository already defines 250 ms, 1 s, and 3 s causal OFI horizons as one
coherent feature family.

Choosing only one after seeing development results would create an unnecessary
researcher degree of freedom.

P7 therefore freezes all three as a single predeclared multiscale L1 OFI
family.

## 8. Evaluation implication after P6

P6 showed that pooled proper-score improvements can occur without stronger
directional ordering.

Therefore P7 must require both:

- improved probability quality;
- improved directional AUC/ranking;

plus fold and leave-one-fold-out stability.

A gain in log loss alone is not enough.

## 9. No deep or tree model in P7

P7 uses logistic regression only.

If OFI adds information under a low-complexity model, a later DEV experiment
may ask whether nonlinear capacity adds anything further.

If OFI does not add stable information under this controlled test, P7 must not
silently switch model family.

## 10. Research conclusion

Recommended P7:

> On the exact frozen A / 120s / 16bp / 32s T1 direction task, compare a
> matched-support PRICE-only regularized logistic baseline against the same
> model augmented with exactly the 24 frozen S1 summaries of
> ofi_l1_250ms, ofi_l1_1s, and ofi_l1_3s.

This is the smallest defensible information-layer experiment after P6.

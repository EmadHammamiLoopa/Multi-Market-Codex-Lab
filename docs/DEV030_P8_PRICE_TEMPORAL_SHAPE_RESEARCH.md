# DEV030-P8 Research Review — PRICE Temporal Shape

Date: 2026-09-02

Purpose: freeze the next information question after P7.

## Empirical trigger

P6 showed that bounded nonlinear capacity did not materially improve the frozen
PRICE S1 direction representation.

P7 then added a compact, predeclared multiscale L1 OFI family. It failed
materially:
- pooled log loss worsened from 0.6950752690 to 0.7622082285;
- pooled Brier worsened from 0.2511438333 to 0.2727784755;
- pooled ROC AUC fell from 0.5416790859 to 0.5097739692;
- June/Fold 3 collapsed to AUC 0.3975346687 and log loss 1.0028875429.

Therefore the next question should not be another feature-family rescue.

## Research/design motivation

The original DEV030 sequential-direction design explicitly separated:
- latest/snapshot information;
- engineered window summaries;
- raw/light temporal sequences.

It also stated that new value should come from temporal sequence
representation/event dynamics rather than merely re-adding OFI/MLOFI.

The current PRICE S1 representation compresses the whole 32-second path into
global statistics such as last, mean, std, min/max, last-minus-first, slope,
and sign persistence. Two very different paths can share similar global
summaries.

A low-risk next diagnostic is therefore to add a few fixed causal landmarks
from the exact same PRICE primitives, while keeping:
- the same task;
- the same target geometry;
- the same 32-second window;
- the same support;
- the same linear model family.

This isolates whether coarse path shape was lost by whole-window aggregation.

## Why fixed lags rather than another model family

Fixed lags are transparent, deterministic, low-dimensional, and require no new
market-data family.

They test a distinct hypothesis:
> does the ordering of recent PRICE states contain information that whole-window
> S1 summaries discard?

This is a representation test, not a capacity test.

## Exact proposed family

Use the three existing PRICE primitives:
1. spread_bps
2. microprice_minus_mid_bps
3. mid_log_return_250ms_bps

Add their exact causal snapshot values at:
- t - 32s
- t - 24s
- t - 16s
- t - 8s

Do not add t itself because S1 already contains the exact terminal value via
the frozen `__last` feature.

This contributes exactly 12 new features.

Baseline C0:
- 23 frozen PRICE S1 features.

Augmented C1:
- same 23 PRICE S1 features;
- 12 fixed-lag PRICE landmarks;
- total = 35 features.

## Why these lags

The four landmarks partition the selected 32-second lookback into four coarse
8-second stages without opening a new window search.

They are chosen before fitting and do not depend on P7 outcomes beyond the
decision to test temporal shape next.

No other lag is allowed inside P8.

## Model/evaluation principle

Use matched-support StandardScaler + L2 LogisticRegression for both C0 and C1.

Select C inside the training side only using:
1. lowest binary log loss;
2. lowest Brier;
3. highest ROC AUC;
4. smaller C.

Require improvement in both proper probability scores and AUC, plus fold/LOO
stability. A log-loss-only gain is insufficient, following P6.

## Stop rule

If fixed-lag PRICE landmarks fail, do not tune lag spacing post hoc and do not
add more lag points inside P8.

The next question would then move to a separately frozen raw/light sequence
model or another explicitly justified representation.

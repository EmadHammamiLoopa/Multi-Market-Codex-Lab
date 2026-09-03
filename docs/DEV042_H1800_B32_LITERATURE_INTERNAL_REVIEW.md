# DEV042 Literature / Internal-Evidence Review

Status: `FROZEN_RESEARCH_BASIS_BEFORE_ANY_DEV042_REAL_PREDICTIVE_RESULT`

Date: 2026-09-03

## Objective

Define a small evidence-backed predictive candidate family for the sole frozen
DEV041 geometry:

`H1800_B32`

DEV042 asks whether information available at decision time can predict enough
of the H1800/B32 first-passage structure to retain executable economic value.

## Internal evidence

The project has already learned several relevant lessons.

### DEV038-A

For the prior H120/B16 target, richer BOOK/FLOW/FULL representations did not
beat PRICE32 on average precision.

Therefore DEV042 must not assume that more microstructure features are
automatically better.

A price/momentum-only baseline remains mandatory.

### DEV037 / DEV038-A-P2

The prior family showed that opportunity selection was a major bottleneck.

Therefore DEV042 uses an explicit NONE class and allows abstention when NONE is
the most probable class.

### DEV040

The old H120/B16 predictive family failed gross executable economics.

Therefore DEV042 does not reuse that predictor/controller as a rescue.

### DEV041

Model-free headroom showed that H1800/B32 is the strongest preregistered
geometry under the severe C2 envelope.

This authorizes a new predictor for H1800/B32 only.

## External evidence

### Order-flow imbalance

Recent BTC/USDT evidence finds that OFI can contain small but real
out-of-sample information, but its strength is unstable across samples and it
benefits from combination with simple autoregressive/momentum information.

Design consequence:

- OFI is a challenger, not the baseline;
- price/momentum remains explicit;
- combined price+OFI is tested.

### Pressure versus absorption capacity

Recent BTC perpetual-futures evidence reports that flow adjusted by near-touch
depth/absorption capacity can be more informative and stable than raw
directional flow alone, with liquidity fragility adding state information.

Design consequence:

- include one economically interpretable pressure/capacity representation;
- do not rely only on raw OBI/OFI.

### Model complexity

Published digital-asset order-book work shows temporal CNNs can predict very
short-horizon movements, but those results concern second-scale horizons and
much denser training samples.

Broader cryptocurrency ML evidence also indicates that added model complexity
does not automatically produce proportional predictive gains.

DEV042 has roughly ten thousand minute decision rows across seven historical
days.

Design consequence:

- no Transformer;
- no LSTM;
- no large CNN;
- no neural architecture search;
- exactly one bounded nonlinear tree challenger after interpretable linear
  candidates.

### Execution fidelity

hftbacktest distinguishes feed, order-entry, and response latency and provides
queue models.

NautilusTrader documents that fills depend materially on book type and explicit
fill assumptions.

Design consequence:

DEV042 retains the already-frozen executable crossing semantics and 250 ms
entry/response latency. Passive fill assumptions are not introduced during
predictive discovery.

## Frozen candidate philosophy

Candidate diversity comes from economically different information sets, not
from dozens of hyperparameter variants.

Exactly five candidates are allowed:

- price/momentum baseline;
- OFI/flow challenger;
- pressure/capacity/liquidity challenger;
- combined linear model;
- combined nonlinear model.

No sixth model may be added after real DEV042 results begin.

## Web references

- Schmalz, Order Flow Imbalance and Short-Horizon BTC/USDT Returns:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7227998
- Chang, Do Order-Book States Predict Passive-Buy Toxicity? Evidence from BTC
  Perpetual Futures:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6693260
- Jha et al., Deep Learning for Digital Asset Limit Order Books:
  https://arxiv.org/abs/2010.01241
- hftbacktest latency models:
  https://hftbacktest.readthedocs.io/en/latest/
- NautilusTrader fill models:
  https://nautilustrader.io/docs/latest/concepts/backtesting/fill-models/

## Non-claim

The literature motivates candidate construction only.

No external paper is treated as proof that DEV042 will be profitable.

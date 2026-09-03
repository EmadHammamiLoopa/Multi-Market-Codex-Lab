# DEV041 Literature / Reference Review

Status: `FROZEN_RESEARCH_BASIS_BEFORE_DEV041_REAL_HEADROOM_OUTPUT`

Date: 2026-09-03

## Purpose

This review defines the scientific and implementation basis for a new
model-free economic-headroom family after DEV040-P1 closed the previous
predictive/execution family as F0.

DEV041 is not a rescue of DEV040-P1.

## Key literature conclusions

### Barrier + vertical-horizon labeling

The triple-barrier framework uses upper/lower return barriers together with a
vertical time barrier. This supports treating target magnitude and horizon as
a joint design object rather than assuming one fixed holding period is
universally appropriate.

Reference implementation:
- mlfinpy Data Labelling / Triple-Barrier documentation.

DEV041 therefore screens a frozen set of barrier/horizon geometries before any
new predictor is built.

### Stop-loss / TP search is not assumed beneficial

Kaminski and Lo show that stop-loss rules do not add value mechanically; under
a random-walk setting they can reduce expected return, while value depends on
return dynamics such as momentum.

DEV041 therefore does NOT run a stop-loss / take-profit parameter rescue grid.

### Execution and order placement are separate mechanisms

Cont and Kukanov model market-vs-limit order placement as a problem determined
by order-book state, queue sizes, fees and rebates.

This supports separating:
1. economic movement headroom;
2. predictive learnability;
3. execution mechanism.

DEV041 addresses (1) only.

### Latency / queue modeling

hftbacktest explicitly models feed latency, order-entry latency,
order-response latency and queue position.

NautilusTrader likewise distinguishes the fidelity available from L1/L2/L3
data and provides matching/fill models.

These implementations are references for later execution work. They are not
used to claim that passive execution can rescue DEV040.

## Implementation references

- hftbacktest:
  market replay, latency models, queue-position models.
- NautilusTrader:
  order-book backtesting, execution flow and fill models.
- mlfinpy:
  triple-barrier / vertical-barrier labeling.

## Design consequence

DEV041 will use the repository's existing executable first-passage engine as
the primary headroom mechanism because it already:

- enters at causal executable bid/ask;
- uses a fixed 250 ms entry latency;
- evaluates executable liquidation/cover paths;
- supports upper/lower first-passage semantics;
- invalidates broken causal paths.

No new execution simulator is introduced during headroom discovery.

The goal is to find a target geometry with enough executable movement and
opportunity density to justify a completely new predictive family later.

## Explicit non-claims

A DEV041 survivor does NOT prove:

- predictability;
- tradability;
- forward profitability;
- passive-fill feasibility;
- production execution quality.

It proves only that the consumed historical market paths contain sufficient
model-free executable movement headroom under the frozen screen.

## Web references used for this review

- mlfinpy, Data Labelling / Triple-Barrier documentation:
  https://mlfinpy.readthedocs.io/en/stable/Labelling.html
- Rama Cont and Arseniy Kukanov, Optimal order placement in limit order
  markets:
  https://arxiv.org/abs/1210.1625
- Kathryn Kaminski and Andrew W. Lo, When Do Stop-Loss Rules Stop Losses?:
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=968338
- hftbacktest documentation:
  https://hftbacktest.readthedocs.io/en/latest/
- hftbacktest latency models:
  https://hftbacktest.readthedocs.io/en/v1.8.4/latency_models.html
- hftbacktest queue models:
  https://hftbacktest.readthedocs.io/en/v1.8.4/reference/queue_models.html
- NautilusTrader backtest data and venues:
  https://nautilustrader.io/docs/latest/concepts/backtesting/data-and-venues/
- NautilusTrader execution flow:
  https://nautilustrader.io/docs/latest/concepts/backtesting/execution-flow/

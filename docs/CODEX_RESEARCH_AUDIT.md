# Codex Research Audit

Status: completed before new model implementation  
Scientific baseline: `f193b199e8da440d2c598546fc1bba480a454762`  
Repository reviewed: `EmadHammamiLoopa/Multi-Market`  
Lab repository: `EmadHammamiLoopa/Multi-Market-Codex-Lab`  
Audit date: 2026-08-25

## Executive finding

The project has not established a profitable trading edge. It has, however, established several useful negative results and one recurring fact: short-horizon order-flow and book state contain a small amount of forecast information, but the observed gross opportunity is usually below realistic execution cost and is unstable across days. The priority for the next experiment is therefore not another generic direction forecaster. It is an execution-conditioned, calibrated decision model whose labels and abstention rule are defined directly in net basis points.

The historical record is unusually disciplined about preregistration, causal feature construction, explicit failure, and sealed holdouts. Its main weakness is cumulative research flexibility: many sequential rescues, feature expansions, horizons, models, and thresholds were tried on the same broad development era. The January--July 2026 material must now be treated as a consumed sandbox rather than fresh validation.

## Scope and evidence grade

I reviewed the full reachable commit graph (346 commits), all 41 baseline research documents, the source tree, 49 test modules, and committed result/manifests under `evidence/`. I also inspected the next upstream commit after the requested baseline; it contains only a prospective passive-execution preregistration and is not imported as evidence or treated as the best design.

The checked-out scientific baseline is exact at `f193b199...`. The initially supplied local directory was a small, unrelated starter snapshot with no Git metadata and did not match that commit. The lab working tree was therefore reconstructed from the named upstream commit before any new implementation. The local-only MIT `LICENSE` was retained because the baseline package already declares MIT licensing.

Evidence grades used below:

- **Reproduced**: executable now from committed inputs with matching output.
- **Audited artifact**: code, result, and/or hash artifact is committed and internally reviewable, but required raw input is not committed.
- **Documented claim**: result appears in a signed-off project document but cannot be independently regenerated from this checkout.
- **Hypothesis only**: post-hoc diagnostic or untested proposal; it must not be reported as validated alpha.

No historical economic experiment can be independently reproduced from this checkout because market data and Phase L `FEATURES250.csv` products are intentionally gitignored and absent. The committed V2/V2.1/V2.2 and early V2.3 JSON/log artifacts are auditable. The later high-frequency numeric results are primarily documented claims plus source/test review. This limitation is material and will remain explicit in the ledger.

## Experiment lineage

| Stage | Main change | Honest result | Evidence grade | Decision |
|---|---|---|---|---|
| V0 | Momentum/replay and execution infrastructure | Research plumbing, not demonstrated alpha | Source/tests | Preserve infrastructure only |
| V1 | XGBoost future-close direction, 35 causal features | High selected accuracy in a few windows, but mostly negative economics; a BTC configuration was exploratory only | Audited artifacts/docs | Reject accuracy as promotion metric |
| V1 frozen windows | Fixed confidence rule | 39/450 actions and 82.05% selected accuracy, contaminated by stale/weekend EUR/XAU behavior | Documented claim | Reject |
| V1.1 | Clean-session filter | 5/450 actions, 2 correct, 3 wrong, 1.11% coverage | Documented claim | Reject |
| V2 | Volatility/economic labels, price-only features, 2 bp cost | 5 actions, 0 winners, -154.89 bp total, -30.98 bp/trade | Audited artifacts | Reject |
| V2.1 | Price, regime, and cross-market features | 6 actions, 3 winners, -33.35 bp total, -5.56 bp/trade; ranking unstable | Audited artifacts | Reject |
| V2.2 | Frozen macro D/E/F block | 3 actionable of 344 scored, 0 winners, -119.88 bp total, -39.96 bp/trade, PF 0 | Audited artifacts | Reject; holdout consumed |
| V2.3 Phase 0 | Dense cross-sectional sensor block | Pooled incremental R2: Ridge -0.004762, ElasticNet -0.004712; 0/5 positive targets | Audited artifacts | Reject block |
| Phase 0B | Acquire/canonicalize 17 ETF sensors | Data audit passed; no alpha claim | Audited artifacts | Preserve data tooling |
| Phase 0C/C-R | Asset/regime asynchronous sensors | All four scored targets failed C2/C3; QQQ unavailable; no economic candidate | Audited artifacts | Reject price-only block |
| Phase 0D | Prospective Binance collector | Infrastructure only; no completed 30-day inference | Source/docs | Preserve collector, no alpha claim |
| Phase D-H-L1 | Historical `bookTicker` + `aggTrades` | Infeasible because the required 2026 `bookTicker` archive was unavailable | Source/docs | Data-source failure, not signal rejection |
| Phase D-H-TF | `aggTrades` flow | Positive incremental rank/R2 cells, but directional gate below 0.45/0.47; holdout stayed sealed | Documented claim | Reject for trading |
| Opportunity diagnostic | 500 configurations per symbol | No configuration survived 12 or 15 bp; best gross 4.845 bp/trade BTC, 4.118 ETH | Documented claim, post-hoc | Hypothesis only |
| Phase I | Longer-horizon flow | BTC inner winners reversed outer: pooled 38 trades, -16.50 bp/trade at 12 bp, PF 0.505; ETH no candidate | Documented claim | Reject; temporal instability |
| Phase J | Mark/index/premium plus flow, Ridge | BTC 39 trades, -11.725 bp/trade; ETH 80, -9.243 at 12 bp | Documented claim | Reject |
| Phase K | XGBoost on the same information | BTC 73 trades, -14.383 bp/trade, PF .359; ETH 63, -18.018, PF .244; no positive folds | Documented claim | Reject nonlinear rescue |
| Phase L | Full L2, OFI/MLOFI, flow, resiliency; causal 250 ms grid | Acquisition, audits, and feature preparation passed 14/14; every inner fold selected `None` for static and dynamic blocks | Source/tests/docs | Reject promotion; keep data pipeline |
| Phase L postmortem | Rank gross dynamic configurations after failure | Best gross cells ranged roughly 0.48--2.80 bp/trade, with highly variable counts; no cost-adjusted candidate | Documented claim, post-hoc | Hypothesis only |

## Failure-mode analysis

### 1. The objective repeatedly drifted away from executable value

Early versions optimized future-close direction or classification accuracy. Later versions scored trading economics, but even Phase L trains a future-mid-return regression target and only applies touch execution and cost during selection. That mismatch matters when the typical gross edge is one or two basis points. A model can improve R2 yet systematically rank examples whose touch-to-touch payoff is negative.

### 2. Costs dominate the measured signal

The strongest diagnostics repeatedly land below ordinary retail/VIP-0 crypto-futures round-trip taker cost before adding latency and adverse selection. Phase L correctly embeds the spread through bid/ask touches and adds 5/8/12 bp scenarios. The 8 bp primary additional-cost gate is economically defensible for a 4 bp-per-side taker schedule, but the actual authenticated account commission must be frozen for any future promotion claim.

### 3. The edge is temporally unstable

Positive inner periods reverse in the next outer day, and some months have very few selected events. First-of-month sampling produces only one validation day per fold and cannot estimate ordinary day-of-week, event-day, volatility-regime, or venue-condition variability. The reported opportunity is therefore closer to a fragile conditional anomaly than a durable process.

### 4. Researcher degrees of freedom accumulated

The project is careful within individual preregistrations, but the full lineage tries many labels, markets, feature families, horizons, thresholds, linear/nonlinear models, and rescue diagnostics. Repeated consultation of January--July means it is no longer valid as an unbiased model-comparison set. Post-hoc rankings are useful for choosing mechanisms, not for estimating performance.

### 5. Calibration and coverage were underdeveloped

Absolute prediction quantiles are learned from training predictions and can change meaning across days. Directional accuracy and R2 do not say whether the highest-confidence subset is calibrated. The small action counts then make point estimates and profit factors extremely uncertain. Promotion needs reliability curves, selective-risk/coverage curves, block-bootstrap intervals, and an explicit `NO_TRADE` action.

### 6. Passive execution is promising but not yet measurable from current evidence

Maker economics can reduce explicit fees, but market-by-price replay cannot reveal exact queue position and historical passive fills without a queue model are assumptions, not observations. Any maker experiment must report RiskAverse and probabilistic queue-model sensitivity, order-entry and response latency, cancellation logic, fill ratio, adverse selection, and maximum inventory. A maker backtest cannot be compared fairly with a taker strategy using only mid-price forecasts.

## Architecture and systems audit

### What is strong

- Point-in-time replay and chronological splits are first-class concepts.
- Feature code uses causal windows and Phase L explicitly groups atomic events by `local_timestamp`.
- Phase L separates acquisition, audit, preparation, preregistration, and scoring.
- Executable bid/ask touches, latency, non-overlap, cost scenarios, opportunity count, expectancy, and PF are represented in the later framework.
- Tests cover feature semantics, native scorer equivalence, day sealing, schema, non-overlap, and the Ridge sufficient-statistics implementation.
- Failed gates are recorded as failures rather than rewritten as successes.

### What needs correction

- There is no single experiment registry connecting code SHA, config SHA, data SHA, split, environment, and result status.
- Most command-line phases embed constants in Python instead of loading immutable experiment configs.
- Large result products and raw data are absent without a portable fetch/verify manifest that can fully rebuild every historical run.
- Fold aggregation emphasizes pooled metrics; it needs dispersion, confidence intervals, worst fold/day, and regime-conditioned results.
- The first-of-month Phase L sample is too sparse for stability claims.
- Selection is all-or-none at the inner gate, so the framework properly prevents promotion but leaves limited outer diagnostic information after a failure.
- There is no unified action model for `NO_TRADE`, taker-long, taker-short, maker-long, and maker-short under the same net-value objective.
- There is no calibrated probability or uncertainty interface for abstention.
- Resource requirements and wall-clock measurements are not consistently logged.

## Data, leakage, and reproducibility audit

The reviewed feature definitions are causal by construction and the Phase L tests make same-timestamp atomicity explicit. The most important remaining leakage risks are procedural rather than a single obvious future column:

1. selecting mechanisms after viewing all sandbox months;
2. fitting normalization, threshold, calibration, or label boundaries outside the training subperiod;
3. overlapping labels across train/validation boundaries without purge plus latency/horizon embargo;
4. synchronizing cross-market feeds using exchange timestamps without respecting local receipt order and staleness;
5. using future-aware latency or queue information in replay;
6. treating absent quotes, closed sessions, or stale bars as ordinary observations;
7. reporting many cells without a family-level false-discovery or reality-check adjustment.

Every new runner must therefore fail closed when a split touches 2026-08-01 or 2026-08-04 through 2026-08-23, fit all transforms inside its fold, record the exact columns used, and emit hashes for config, inputs, source commit, and output.

## What is preserved, dropped, and added

Preserve:

- point-in-time replay and causal event ordering;
- Phase L L2/flow/resiliency feature preparation and its semantic tests;
- executable touch pricing, explicit latency, non-overlap, and cost stress;
- chronological inner/outer evaluation and the willingness to abstain;
- manifest/hash conventions and sealed-period guards.

Drop from the primary path:

- accuracy-led promotion;
- generic mid-return prediction as the sole training objective;
- further feature-family expansion before the cost/objective mismatch is tested;
- reuse of V2.2 holdouts or either sealed August period;
- post-hoc best-cell results as evidence of performance;
- another XGBoost/deep model on unchanged labels and sampling.

Add:

- direct executable-net labels for long and short actions;
- calibrated probabilities and an explicit no-trade policy;
- day/regime stability gates and uncertainty intervals;
- a config-driven experiment ledger with deterministic hashes;
- conservative maker queue-model sensitivity as a separate follow-up track;
- cross-market sequence models only after a simple cost-aligned baseline demonstrates stable incremental value.

## Seal and safety decision

The new lab treats 2026-08-01 and 2026-08-04 through 2026-08-23 as sealed. No implementation, test fixture, default path, or exploratory command may read them. January 1 through July 1, 2026 is explicitly a development sandbox and cannot support a fresh unbiased profitability claim. No component added by this research program sends orders or enables live exchange connectors.

## Audit verdict

The best next scientific question is narrow: **does directly modeling the probability of a positive executable taker payoff, with fold-local calibration and abstention, improve stable net expectancy over the Phase L future-mid Ridge baseline on the already-consumed sandbox?** A negative answer closes the taker-L2 branch more decisively. A positive sandbox result only earns a preregistered, still-sealed future evaluation; it is not deployment evidence.

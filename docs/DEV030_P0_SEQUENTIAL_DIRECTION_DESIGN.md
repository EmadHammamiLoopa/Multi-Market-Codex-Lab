# DEV030-P0 Opportunity-Conditioned Sequential Microstructure Direction Discovery

Status: **DESIGN FOR HUMAN REVIEW — NO DEV030 MODEL HAS BEEN IMPLEMENTED OR FIT**

Date: 2026-09-01

Baseline commit: `993ad5370731600f404fa13ba2a9c74ae2220ae3`

Development branch: `research/dev030-p0-sequential-direction`

This is a personal quantitative-trading R&D design, not a publication-style
preregistration. It deliberately permits iterative development on already
consumed January–July 2026 data. That freedom does not relax point-in-time
causality, chronological validation, executable-price accounting, or the
separation of untouched forward data.

The repository, frozen result artifacts, and public research were audited for
this document. No market-data file was opened, no model was fit, EXP029 was not
rerun, 2026-08-30 was not reopened, and 2026-09-01 or later was not inspected.

## 1. Executive Summary

What worked is specific and valuable. EXP024-P1 prospectively confirmed that
the one-feature `rv_30m_bps` model ranks the occurrence of a 10-minute,
at-least-24 bp executable move on BTCUSDT. On the fresh 2026-08-30 day it
produced AUC `0.7994`, AP/prevalence `4.4824`, and top-decile lift `2.9012`,
with its temporal-null gates passing. The acquisition, causal 250 ms grids,
historical feature construction, executable bid/ask outcome helper, immutable
result handling, and continuous archive are also reusable assets.

What failed is a different layer. Repeated direction/economics tracks did not
show stable executable direction: passive fills were adversely selected;
cross-venue, derivatives, and options blocks did not add useful information;
linear, boosted-tree, and XGBoost versions of row-level signed-return models
failed out of sample; and EXP026/EXP028 could not establish a sufficiently
dense, stable direction policy. EXP029 retained meaningful opportunity
enrichment but failed its frozen AUC-null p-value gate. None of those results
negates EXP024's narrower prospective finding.

DEV030 therefore changes the representation and target before escalating model
capacity. Its core development hypothesis is that direction may be encoded in
the *path* of OFI, MLOFI, queue imbalance, microprice, replenishment, depletion,
trade flow, and spread immediately before an opportunity—not adequately in one
row of short aggregates predicting a terminal signed return. It will compare
causal sequence summaries and raw sequences using an executable first-passage
`LONG_FIRST / SHORT_FIRST / NONE` target, while carrying the EXP024 opportunity
score as a distinct context variable or gate.

DEV030 preserves rather than resets:

- EXP024's opportunity question, model, feature, and executable convention;
- EXP029 as negative evidence about one fixed causal gate, without rerunning or
  rescuing it;
- the Phase0DL 250 ms feature files and exact causal semantics;
- EXP004's executable bid/ask helper and EXP026/EXP029 timing/occupancy logic;
- EXP025/EXP027 continuous BTC/ETH/SOL acquisition and immutable archive;
- every negative result as an anti-repeat constraint.

The first implementation after review should be a standalone, synthetic-tested
executable first-passage labeler and label-feasibility audit. It should not be a
Transformer. Until the new target is unambiguous and its class/support geometry
is understood on consumed data, larger models would only accelerate confusion.

## 2. Cumulative Project Architecture

| Layer | Decision | Preserved asset | DEV030 treatment |
|---|---|---|---|
| Data / archive | **KEEP** | Phase0DL point-in-time files; EXP025 continuous collector; EXP027 bucket-backed immutable chunks, manifests, and finalizer | Read through explicit manifests only. Add richer streams later, never replace or mutate the current archive. |
| Opportunity detection | **KEEP AND IMPROVE** | EXP024 `rv_30m_bps` rank model; EXP029 causal-rank lessons; EXP004 target helper | Keep opportunity and direction as separate questions. Compare continuous score, causal rank, gates, and interactions during development. Do not assume `q=0.90` is universal. |
| Direction prediction | **REDESIGN** | Existing causal microstructure features and negative baselines | Replace single-row/fixed-terminal-return framing with temporal paths and executable first passage. Establish incremental sequence information before complex models. |
| Execution / economics | **REUSE, THEN IMPROVE** | Bid/ask crossing, 250 ms latency, exact horizon, costs, non-overlap, drawdown/PF utilities, EXP002 queue replay | Use current helpers for conservative small-order aggressive-fill tests. Adopt event-driven queue simulation only when the data can identify it. |
| Risk / position sizing | **LATER** | Existing guard conventions | No leverage, Kelly, stop-loss search, or size optimization in DEV030-P0. Risk work starts only after stable net executable expectancy. |

The architectural boundary is important: an opportunity score answers *when a
large move is plausible*; a direction score answers *which side is favored*;
an action/meta layer answers *whether confidence is sufficient to trade*; and
the execution/risk layers determine whether that prediction can survive costs.
One model must not be allowed to blur all four questions during discovery.

## 3. Frozen Assets That Must Be Preserved

### EXP024: successful opportunity ranking

Keep the exact parent signal as a baseline and context feature:

- BTCUSDT; `rv_30m_bps` only;
- 60-second decisions;
- entry at `t + 250 ms`, exit 600 seconds after entry;
- any-direction executable opportunity `>= 24 bp`;
- training-only `StandardScaler` plus `LogisticRegression(C=1.0, l2,
  lbfgs, class_weight=None, max_iter=1000, random_state=20260825)`.

The preserved result is ranking evidence only. It is not direction, PnL, or
calibration evidence, and 2026-08-30 is now consumed.

### EXP029: closed negative policy evidence

Keep the artifact and status unchanged. The exact rolling `q=0.90`, 1399-score
policy preserved enrichment (pooled lift `2.1210`, active folds `3/4`) but
failed its AUC temporal-null empirical-p gate (`0.0652 > 0.05`). DEV030 may
develop alternative opportunity representations later, but must never rewrite
that closed result as a pass or rerun it under EXP029.

### EXP025 and EXP027: acquisition/archive infrastructure

The EXP025 implementation uses one asynchronous Binance USD-M Futures combined
`bookTicker` process for exact symbols `BTCUSDT`, `ETHUSDT`, and `SOLUSDT`, with
symbol-isolated queues/writers, no REST backfill, exclusive files, UTC rollover,
transport invalidation, and deterministic 250 ms finalization. EXP027 preserves
those semantics while writing immutable hourly gzip chunks to a private
S3-compatible bucket, verifying size and SHA-256 before local deletion, and
requiring all 24 hours plus rollover for archive readiness.

These branches are cumulative infrastructure even though their files are not
merged into the EXP029 result branch. They must not be deleted, replaced,
stopped, redeployed, or analytically opened by DEV030. Current collection is
best-book data, not a substitute for historical Phase0DL L2/trade data.

### Historical features and point-in-time semantics

Keep:

- `v23_phase0dl_score.DayData` and `_load_day`;
- `tools/v23_phase0dl_features250.cpp` and
  `docs/V23_PHASE0DL_FEATURE_SEMANTICS_FREEZE.md`;
- per-block validity (`book_valid`, `valid_l0`, `valid_l1`, `valid_l2`);
- atomic local-receive-time event grouping, `(t-250ms, t]` flow bins, and no
  fill through invalid state;
- train-only transforms and exact chronological timestamps.

### Execution and safety helpers

Prefer these existing components where their assumptions match:

- `codex_exp004_headroom.executable_fixed_horizon` for `t+250ms` bid/ask
  entry and executable exit arithmetic;
- `codex_exp004_p1._r_features`, `_spread`, `build_day_dataset`, and
  `FixedLogistic` for the frozen opportunity layer;
- EXP026 profit-factor, drawdown, cost, and non-overlap utilities;
- EXP029 direction-independent occupancy timing and JSON/invariant safety;
- EXP023 recursive NumPy normalization and exact built-in-bool discipline;
- EXP002 queue replay only for future passive-order work with qualifying data.

The new first-passage path target cannot be obtained by calling the fixed-exit
helper once, but it must use the same bid/ask orientation, entry latency, valid
book rules, and log-bps arithmetic.

## 4. Prior Experiment Lessons

### Positive evidence

- **EXP004-P0:** executable 10-minute/24 bp headroom existed often enough to
  justify prediction.
- **EXP004-P1:** the R block ranked opportunity (AUC `0.670`, lift `2.135`), but
  most value came from volatility and L2 did not improve it. Its calibration and
  then-used permutation gate failed.
- **EXP020/EXP021:** time-aligned volatility information survived a proper
  feature permutation, while prevalence shifted and historical calibration
  corrections were not stable. Use scores/ranks cautiously; do not revive a
  calibration rescue.
- **EXP024-P1:** the volatility-only opportunity model passed genuinely fresh
  prospective ranking/null gates. This is the strongest positive predictive
  asset in the repository.
- **EXP029-P0:** despite official FAIL, three folds were active and the causal
  gate lift was above two pooled. Opportunity context remains worth retaining;
  one rigid gate is not the whole opportunity layer.

### Negative evidence that constrains DEV030

- **EXP002:** 4,238 queue-qualified passive fills lost `-0.988 bp` gross and
  `-6.988 bp` net per fill; 75.77% had adverse 1-second markout. Capacity was not
  the problem. A fill model with no qualifying action set is not an edge.
- **EXP003:** causal spot/Bybit features received at least 500 ms early made the
  Binance-futures economics worse; only the intentionally illegal future
  canary was strongly profitable. Cross-market features need a new temporal
  hypothesis, not a replay of that fixed representation.
- **EXP005:** derivatives state did not add stable opportunity timing beyond R.
- **EXP011/EXP015:** aggregate and expiry/moneyness-segmented BTC options flow
  did not add incremental timing; the 96-feature segmented version materially
  degraded performance.
- **Phase0DH:** 1-second trade-flow features improved rank/R2 but directional
  accuracy remained below 0.50. Explanatory flow is not automatically an
  actionable side signal.
- **Phase0DI:** longer 10/30/60-minute terminal-return development produced
  inner survivors that failed outer folds, consistent with search instability.
- **Phase0DJ:** mark/index/premium state plus Ridge failed both absolute
  economics and incremental value.
- **Phase0DK:** XGBoost on essentially the same state/target also failed with
  negative gross direction, directly rejecting “same row + stronger model.”
- **Phase0DL:** the richest stored L0/L1/L2 row blocks, including 250 ms/1 s/3 s
  aggregates, produced no inner survivor for 1/3/10/30-second signed terminal
  mid-return targets. It did *not* test an 8–60-second feature trajectory with
  path summaries or an executable first-passage target.
- **EXP026/EXP028:** A/B/C economic selection could not establish support
  stability; EXP028 had only two active folds. The direction layer must be
  learned before it is forced through a sparse economic gate.

## 5. Anti-Repeat Matrix

| Prior approach | Why it failed | What it already tested | What must not be repeated | How DEV030 is materially different |
|---|---|---|---|---|
| Phase0DH | Flow improved rank but direction accuracy failed | 1-second trade aggregates, 1/3/5/10-second imbalance summaries, Ridge/HGBR, 10-second terminal last-price return | Call flow “directional” because it explains variance; use the same target with only another classifier | Preserve the flow variables but model their 250 ms path and use executable first passage |
| Phase0DI | Inner longer-horizon survivors collapsed out of sample | 30/60/120/300-second aggregate summaries, 600/1800/3600-second terminal returns, extreme gates | Broad nested search with pooled success masking fold instability | Day-level purged walk-forward, smaller staged search, per-regime stability, new target |
| Phase0DJ | Futures state was neither profitable nor incremental | Mark/index/premium/basis features, linear model, 5/10/30-minute terminal return | Add the same state block and expect direction to appear | Opportunity context remains separate; microstructure trajectories are the direction hypothesis |
| Phase0DK | Nonlinearity did not rescue negative gross expectancy | XGBoost variants on DJ representation and target | “XGBoost/LightGBM/CatBoost is the new idea” | Boosting enters only after summary sequences beat snapshot baselines |
| Phase0DL | No robust tradable configuration survived | Exact L0/L1/L2 features at a row, fixed 250 ms/1 s/3 s aggregates, 1/3/10/30-second terminal mid-return | Flatten the same current row into a larger model | Explicit 8/16/32/60-second paths; first-passage executable labels; snapshot-vs-sequence ablation |
| EXP026 | Candidate A had a fold with zero executed trades | `rv_30m_bps` q90 gate plus A/B/C direction and 10-minute fixed-exit economics | Select direction only inside a gate too sparse to train/evaluate | During discovery use continuous opportunity context and separate direction support from occupancy |
| EXP028 | Only two of four folds were active | Abstention-aware reuse of same q90 opportunity schedule and A/B/C | Count abstentions as zero performance or lower a gate post hoc | Learn a direction representation first; tune opportunity conditioning only inside consumed development data |
| EXP029 | One temporal-null p gate failed; April had no eligible signals | One causal rolling rank window, one q90 gate, direction-free occupancy | Rescue EXP029 or declare all opportunity ranking useless | Treat raw score/rank/gate as competing context designs in a new development track, with EXP029 unchanged |

The novelty test for every later proposal is: does it change the information
representation, target, conditioning, or executable decision in a way that
isolates a previously untested explanation? A new library or classifier name
alone fails that test.

## 6. Existing Data Capability Inventory

### 6.1 Prepared 250 ms Phase0DL blocks

All features below are produced by `tools/v23_phase0dl_features250.cpp`, loaded
by `src/multimarket/v23_phase0dl_score.py`, and present for the historical
Phase0DL BTCUSDT and ETHUSDT days. The module's exact symbol allowlist is
`BTCUSDT, ETHUSDT`; SOLUSDT has no equivalent prepared historical Phase0DL
feature set in this repository. Every sequence must AND the relevant validity
mask over its entire lookback.

| Block | Exact features | Sampling / causal lookback | Inputs | BTC | ETH | SOL | Sequence use without regeneration |
|---|---|---|---|---:|---:|---:|---|
| L0 | `spread_bps`; `microprice_minus_mid_bps`; `obi_l1`, `obi_l5`, `obi_l10`; `log_bid_qty_l1`, `log_ask_qty_l1`; `log_bid_depth_l5`, `log_ask_depth_l5`; `log_bid_depth_l10`, `log_ask_depth_l10` | Current causal 250 ms state | L1 plus top-5/top-10 L2 snapshot | Yes | Yes | No | Yes; consecutive stored rows form a path. Full level-by-level prices/sizes are not retained. |
| L1 OFI/MLOFI | `ofi_l1_250ms`, `_1s`, `_3s`; `mlofi_l5_250ms`, `_1s`, `_3s`; `mlofi_l10_250ms`, `_1s`, `_3s` | Current `(t-250ms,t]` event bin; sums of last 4 or 12 bins | L2 updates, local causal clock | Yes | Yes | No | Yes; already causal, but overlapping summaries are correlated. |
| L1 trades | `trade_qty_imbalance_250ms`, `_1s`, `_3s`; `trade_count_imbalance_250ms`, `_1s`, `_3s` | Directional buy/sell totals in 1, 4, or 12 bins | Trades plus local causal clock | Yes | Yes | No | Yes. Unknown side is excluded and audited. |
| L2 changes | `d_obi_l1_250ms`, `_1s`; `d_obi_l5_250ms`, `_1s`; `d_obi_l10_250ms`, `_1s`; `d_spread_bps_250ms`, `_1s`; `d_microprice_minus_mid_bps_250ms`, `_1s` | Current minus exact 1-row or 4-row lag | Valid state at both endpoints | Yes | Yes | No | Yes. Do not compute across invalid intervals. |
| L2 queue flow | `bid_replenish_l5_1s`, `ask_replenish_l5_1s`, `bid_deplete_l5_1s`, `ask_deplete_l5_1s` | Exact-price top-5 changes aggregated over 4 bins | L2 updates | Yes | Yes | No | Yes. These are displayed-flow proxies, not order IDs or queue positions. |
| L2 interactions | `trade_qty_imbalance_1s_x_obi_l5`; `trade_qty_imbalance_1s_x_microprice_minus_mid_bps`; `mlofi_l5_1s_x_spread_bps` | Current causal components | L2 plus trades | Yes | Yes | No | Yes; compare against letting the model learn interactions from primitive paths. |

The feature generator applies event groups atomically before sampling. OFI uses
the standard best-price/size event rule; MLOFI applies it independently across
levels; one- and three-second values sum raw flows before forming trade
imbalances; replenishment/depletion compares quantities at identical price
levels rather than rank positions. No forward fill through an invalid book is
allowed.

### 6.2 Opportunity/regime features

`src/multimarket/codex_exp004_p1.py` computes these at authorized decision
indices from `DayData`:

| Family | Exact features | Required causal lookback |
|---|---|---|
| Returns | `ret_1m_bps`, `ret_3m_bps`, `ret_5m_bps`, `ret_10m_bps`, `ret_30m_bps` | Exact mid at t and each lag; full book-valid interval under frozen R support |
| Absolute returns | `abs_ret_1m_bps`, `abs_ret_3m_bps`, `abs_ret_5m_bps`, `abs_ret_10m_bps`, `abs_ret_30m_bps` | Same as signed returns |
| Realized volatility | `rv_5m_bps`, `rv_15m_bps`, `rv_30m_bps` | One-minute causal mids, complete 5/15/30-minute windows |
| Spread | `spread_bps`, `spread_mean_1m_bps`, `spread_mean_5m_bps` | Current, trailing 1 minute, trailing 5 minutes |
| Range | `range_5m_bps`, `range_15m_bps`, `range_30m_bps` | Complete trailing high/low mid windows |
| Range position | `range_position_5m`, `_15m`, `_30m` | Current mid relative to complete trailing range |

The exact EXP024 feature is `rv_30m_bps`. DEV030 should obtain its opportunity
probability from the preserved model path, not silently reconstruct a similar
volatility score.

### 6.3 Other reusable prepared sources

| Source module / artifact | Frequency and content | Historical markets | Use / limitation |
|---|---|---|---|
| `v23_phase0dh_tf.py` prepared trade-flow data | 1-second grid; `ret1`, `ret3`, quantity/count flow imbalance over 1/3/5/10s, log quantity/count, VWAP pressure, buy/sell presence | BTC, ETH | Useful independent flow baseline and regeneration reference. Its original calendar/terminal last-price label differs from the Phase0DL first-of-month dataset. Do not join without an explicit timestamp/provenance audit. |
| `v23_phase0di_longer_horizon.py` | Derives 30/60/120/300-second flow/return summaries from Phase0DH | BTC, ETH | Reusable summary formulas, but prior economic selection failed and data is 1-second rather than 250 ms. |
| `v23_phase0dj_score.py` | One-minute mark, index, premium/basis state and lags/z-scores | BTC, ETH | Optional regime diagnostic only; prior incremental direction result failed. |
| EXP025/EXP027 archive | Event-driven Binance USD-M `bookTicker`, raw best bid/ask and quantities; deterministic final grid currently stores bid, ask, mid and provenance | BTC, ETH, SOL | Excellent prospective opportunity/BBO archive. Insufficient by itself for historical MLOFI, deeper queues, cancellation attribution, or faithful DeepLOB/TLOB inputs. |

### 6.4 What can be sequenced now

The 43 Phase0DL L0/L1/L2 values can be sliced into causal `[time, feature]`
tensors for any decision whose entire lookback is valid. No market-data
regeneration is needed for engineered summaries or raw sequences of those
stored variables. Candidate 8/16/32/60-second windows correspond to 32/64/128/
240 rows at 250 ms.

What cannot be recovered from the prepared rows is the exact top-10 matrix of
price and quantity at every level, individual order identities, precise queue
position, or every native event. Faithful raw-book DeepLOB/TLOB, event-time
models, and realistic limit-order replay require a new *additional* data stream
or already-authorized raw L2/trade replay—not inference from aggregates.

## 7. External Research Review

Public papers, primary documentation, and repository source surfaces were
reviewed on 2026-09-01. They are design inputs, not evidence about this
repository's unseen data. No published metric is assumed transferable to
Binance USD-M BTCUSDT after costs.

### 7.1 Methods and applicability

| Source | What the method does | Why it may help DEV030 | Data required / current support | Reusable part / not applicable | Leakage, overfit, and compute risk |
|---|---|---|---|---|---|
| [Cont, Kukanov & Stoikov, *The Price Impact of Order Book Events*](https://arxiv.org/abs/1011.6402) | Defines best-level OFI from limit orders, cancels, and market orders and relates short-interval price change to OFI/depth. | Supports treating the signed *evolution* of supply/demand as more informative than trade volume alone. | Event-level best book and trades; Phase0DL already implements the exact causal event rule and rolling sums. | Reuse existing OFI primitives and cumulative/path summaries. The paper studies largely contemporaneous impact, not guaranteed forward net returns. | Overlapping flow/return intervals can turn contemporaneous explanation into apparent prediction. Purge target overlap and lag inputs strictly. Compute is low. |
| [Xu, Gould & Howison, *Multi-Level Order-Flow Imbalance*](https://arxiv.org/abs/1907.06230) | Extends OFI across book levels; additional levels improved out-of-sample explanatory fit in its equity sample. | Motivates trajectories and level contrasts of stored MLOFI L5/L10 rather than only L1. | Multi-level updates; current historical Phase0DL supports aggregate L5/L10 MLOFI, but not every level's separate trajectory. | Reuse L5/L10 paths and short-vs-long contrasts. Do not claim the aggregate vector is a full level matrix. | More levels/features increase collinearity and multiplicity. Begin with regularized summary baselines. Low/medium compute. |
| [Gould & Bonart, *Queue Imbalance as a One-Tick-Ahead Price Predictor*](https://arxiv.org/abs/1512.03492) | Uses bid/ask queue imbalance in logistic and local-logistic models for the next mid-price direction. | Provides a strong Level-0 heuristic and a falsifiable baseline for OBI persistence/reversal. | Best-level quantities; current Phase0DL has OBI L1/L5/L10 and BBO quantities for BTC/ETH. | Reuse signed OBI and microprice heuristics. One-tick equity results do not establish 10–600-second crypto economics. | Tick-size regime matters; repeatedly selecting lags can overfit. Compute is low. |
| [Stoikov, *The Micro-Price*](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2970694) and [official code](https://github.com/sstoikov/microprice) | Estimates a future fair price as a spread/imbalance-conditioned adjustment to mid through state transitions. | Motivates the trajectory, persistence, and reversal of microprice-minus-mid as a direction signal. | BBO price/size states and transition data; current Phase0DL has a static `microprice_minus_mid_bps`, enough for path tests but not necessarily the paper's full learned recursion. | Reuse the stored static signal honestly. A later full Stoikov estimator must be separately implemented/tested and not mislabeled as weighted mid. | State bucketing and transition estimation can leak if fit on validation. Fit all bins/transitions on training only. Low/medium compute. |
| [DeepLOB](https://arxiv.org/abs/1808.03668) and [official repository](https://github.com/zcakhaa/DeepLOB-Deep-Convolutional-Neural-Networks-for-Limit-Order-Books) | CNN/Inception layers learn spatial book structure; LSTM learns temporal dependencies over snapshot sequences. | Directly tests whether temporal/spatial paths add information beyond a row. | Typically top-10 price/size matrices over many snapshots. Current prepared data supports sequences of engineered aggregates, not faithful raw DeepLOB input. | Reuse the causal tensor/training ideas and ablation discipline; do not copy FI-2010 labels, normalizers, or headline accuracy. | Highly overlapping samples, label smoothing, class balancing, and benchmark-specific preprocessing can inflate results. GPU compute is medium/high. |
| [TLOB](https://arxiv.org/abs/2502.15757) and [official repository](https://github.com/LeonardoBerti00/TLOB) | Dual temporal/feature attention over LOB sequences; also shows a simple MLPLOB can rival complex models and discusses horizon-label bias and spread-aware labels. | Relevant only after simpler sequence models show incremental value; its label critique supports executable first passage. | Raw top-10 LOB sequences; not faithfully available in prepared Phase0DL aggregates. | Reuse dual-axis ablation and the lesson that simple MLPs may suffice. Do not begin at Transformer level or import its searched settings. | Large search surfaces and dataset-specific normalization create severe overfit risk. Highest compute in the proposed ladder. |
| [Sirignano & Cont, *Universal Features of Price Formation*](https://arxiv.org/abs/1803.06917) | Trains on histories across many instruments; reports path dependence and benefits from pooled universal models. | Supports testing pooled BTC/ETH representation learning and asset-held-out diagnostics, not only asset-specific fits. | Large event histories across assets; current Jan–Jul prepared set has BTC/ETH only and limited sampled days. | Reuse shared-model/asset-indicator comparison after single-asset baselines. Do not infer universality from two assets. | Cross-asset pooling can leak market identity or synchronized target moves. Split chronologically and audit asset-held-out results. High compute at paper scale, modest for our baselines. |
| [Kolm, Turiel & Westray, *Deep Order Flow Imbalance*](https://onlinelibrary.wiley.com/doi/full/10.1111/mafi.12413) | Uses stationary order-flow inputs and LSTM forecasting at multiple horizons; reports effective horizons near a few price changes. | Strongly supports comparing stationary engineered flows with raw book states and testing much shorter horizons than 600 seconds. | Granular LOB messages/OFI; Phase0DL has compatible stationary OFI/MLOFI aggregates, not all raw events. | Reuse stationary flow sequences and multi-horizon ablation. Do not assume equity horizon lengths transfer. | Horizon fishing and dense overlapping labels are key risks. Medium compute. |
| [Jha et al., *Deep Learning for Digital Asset Limit Order Books*](https://arxiv.org/abs/2010.01241) and [code](https://github.com/Globe-Research/deep-orderbook) | Temporal CNN on 100 ms, deep Coinbase BTC books with walk-forward testing. | Crypto-specific evidence that order-book history can matter over seconds and that top levels may dominate. | 50-level snapshots, reduced to useful top levels; current Phase0DL aggregates cannot reproduce its raw tensor. | Reuse walk-forward and depth-ablation ideas. Do not copy its exhaustively selected label threshold or random class downsampling. | Only nine days, searched label threshold, and downsampling limit transferability. Medium/high compute. |
| [Briola, Bartolucci & Aste, *Deep Limit Order Book Forecasting*](https://arxiv.org/abs/2403.09267) and [LOBFrame](https://github.com/financialcomputingucl/lobframe) | Benchmarks many LOB models and adds transaction/action-oriented evaluation. | Reinforces that forecast scores must be followed by executable action tests and microstructure-specific diagnostics. | LOBSTER-style full event/book data; not the current bookTicker archive. | Reuse modular processing/model/backtest separation and complete-transaction thinking. Do not port its simulator assumptions without data equivalence. | Model benchmark breadth invites multiple testing; traditional metrics may not map to trades. High compute. |
| [Cont, Cucuringu & Zhang, *Cross-Impact of OFI*](https://arxiv.org/abs/2112.13213) | Integrates multi-level OFI and finds lagged cross-asset OFI can improve short-horizon forecasts even when contemporaneous cross-impact adds little. | Gives a concrete BTC/ETH lead-lag hypothesis using lagged—not future-synchronized—flows. | Timestamped OFI for multiple assets. Historical Phase0DL BTC/ETH grids appear structurally compatible but require an explicit alignment audit. | Reuse lagged cross-OFI design and sparse baselines. Do not assume equity cross-impact or same-row alignment is causal. | Common market shocks can masquerade as leadership; evaluate lag sign, staleness, and asset-held-out/day stability. Low/medium compute. |
| [mlfinpy triple-barrier/meta-label source](https://github.com/baobach/mlfinpy/blob/main/mlfinpy/labeling/labeling.py) and [López de Prado method index](https://www.quantresearch.org/Innovations.htm) | Labels the first horizontal or vertical barrier and optionally trains a second model to accept/reject a primary side. | Supplies a pattern for path-dependent labels and a possible future act/abstain layer. | A complete future price path per event. DEV030 has executable BBO paths on consumed Phase0DL days. | Reuse “first event wins” and explicit vertical horizon. Replace close/mid returns and backward filling with two-sided executable bid/ask paths and strict invalidation. | Overlapping event labels require purging. Meta-labeling is useful only after a primary side has real OOS information. Low compute for labels. |
| [2025 crypto input-complexity review](https://arxiv.org/abs/2506.05764) | Compares simple and deep models on 100 ms BTC/USDT LOB snapshots and argues preprocessing/input choices can matter more than added layers. | Aligns with DEV030's “representation before capacity” ladder. | Deep 100 ms Bybit snapshots; not equivalent to our Binance futures aggregate features. | Reuse model-ladder philosophy only. Its filters must not be copied causally without proving past-only operation. | Single-day/search-heavy results are weak transfer evidence; centered smoothing can leak future data. Medium/high compute. |
| [hftbacktest repository and documentation](https://github.com/nkaz001/hftbacktest) | Event-driven replay with latency, queue-position, partial/no-partial fill, fee, and multi-market models. | Could improve later execution realism once full tick depth/trade and measured latency data exist. | Full L2/L3 or tick depth/trades, exchange/local timestamps, order assumptions. Current finalized bookTicker grid is insufficient. | Reuse only after a replay-equivalence data audit. Current aggressive BBO helper remains more honest for small hypothetical taker trades. | A detailed simulator with guessed queue/latency parameters creates false precision. Setup/compute cost is medium/high. |

### 7.2 Open-source review conclusions

The reviewed public repositories were TLOB, DeepLOB, Stoikov microprice,
Globe Research deep-orderbook, LOBFrame, hftbacktest, mlfinpy, and the public
mlfinlab documentation/repository surface. The reusable value is architectural:
causal tensor layouts, simple-vs-complex baselines, first-touch labeling,
purging concepts, and event-driven replay boundaries. None should be vendored
wholesale. Licenses, preprocessing, label definitions, and timestamp semantics
must be reviewed before any code reuse.

Three conclusions are sufficiently consistent to guide design:

1. path and order-flow information can matter, but its effective horizon is
   often short;
2. careful, stationary inputs and simple baselines can rival deeper models;
3. classification improvements are not proof of net executable returns.

## 8. Core DEV030 Hypothesis

The testable hypothesis is:

> Conditional on causal opportunity context, the recent temporal evolution of
> order flow and book state contains stable information about which executable
> side reaches a meaningful barrier first, beyond the information in the latest
> snapshot and beyond recent price momentum alone.

This separates seven competing explanations for prior failure:

| Explanation | DEV030 discriminator |
|---|---|
| A. Features contain little direction information | Even sequence summaries fail to beat price-only and snapshot baselines across days. |
| B. Row aggregation discarded path information | Sequence summaries/raw sequence beat the exact same features' latest-row baseline on the same support. |
| C. Terminal signed-return target was unsuitable | First-passage improves stable direction metrics while fixed-horizon, same-support labels do not. |
| D. Direction exists only in opportunity/volatility regimes | Opportunity interactions/gates improve direction consistently relative to all-row modeling. |
| E. Costs destroy measurable direction | Classification survives but bid/ask gross and conservative net expectancy do not. |
| F. 60s/600s timing was too slow | Shorter first-passage horizons/windows work while long horizons decay; report signal half-life. |
| G. Single-asset inputs miss leadership | Strictly lagged ETH features incrementally improve BTC after single-asset sequence value is established. |

A credible result should identify which explanation is supported. “Best model
accuracy increased” without these matched-support ablations is not enough.

## 9. Sequence Representation Candidates

Candidate lookbacks for later development are 8, 16, 32, and 60 seconds
(32, 64, 128, and 240 rows). They are a design search space, not frozen winners.
The initial search should stage windows rather than take their Cartesian product
with every target/model in one run.

### Family S0: snapshot controls

- exact latest Phase0DL L0/L1/L2 row;
- price-only latest returns and `rv_30m_bps`;
- opportunity probability/rank alone;
- signed heuristics: OBI L1/L5/L10, microprice-minus-mid, cumulative OFI sign,
  cumulative MLOFI sign, and short momentum.

These controls tell us whether a sequence adds anything to already-tested row
information.

### Family S1: engineered causal sequence summaries

For each eligible primitive over each candidate window, consider a deliberately
bounded catalog:

- latest and fixed lags;
- mean, median, standard deviation, minimum, maximum, and range;
- last-minus-first, OLS slope, and change in slope/acceleration;
- causal EMA and fast-minus-slow EMA;
- sign persistence, positive/negative fractions, zero crossings;
- cumulative OFI/MLOFI/trade imbalance and peak absolute imbalance;
- time since causal local maximum/minimum;
- final value's z-score/rank relative to *past values in that window*;
- short-window minus long-window contrasts;
- area-under-path and signed run length.

Normalization must be fit on training data only. Within-window transforms may
use only rows at or before the decision. No centered filter, backward fill, or
whole-day normalization is allowed.

### Family S2: lightly normalized raw sequences

Construct tensors `[sequence_length, features]` from a small primitive set,
beginning with:

- OBI L1/L5/L10;
- microprice-minus-mid and spread;
- OFI L1 and MLOFI L5/L10 at 250 ms;
- trade quantity/count imbalance at 250 ms;
- replenishment/depletion asymmetry;
- short mid returns.

Use masks or reject the sample when any required row is invalid; never encode
an invalid gap as a plausible zero. Price-level variables should be stationary
(bps from current/causal mid or changes), not raw absolute price. Training-only
robust scaling or standardization should be compared with no scaling where the
model supports it.

### Family S3: cross-feature temporal interactions

Test interactions only after their primitive sequences are understood:

- OFI trajectory conditioned on OBI level/persistence;
- trade-flow trajectory conditioned on spread and depth;
- microprice drift conditioned on queue imbalance;
- bid-minus-ask replenishment and depletion paths;
- flow shock divided by causal depth/liquidity;
- volatility-conditioned order flow;
- short/long imbalance divergence;
- disagreement between trade flow, book flow, and price response.

The ablation must compare explicit engineered interactions to models that learn
them, so an interaction block cannot hide redundancy.

## 10. First-Passage Target Design

This section defines the future label family to implement and audit. The
initial horizon and barrier grid remain development choices; the arithmetic and
edge-case rules should be invariant across that grid.

### 10.1 Executable path

For a decision timestamp `t`, reaction latency `L = 250 ms`, vertical horizon
`H`, and positive symmetric gross barrier `B` bps:

```text
e = t + L
a_e = ask(e)
b_e = bid(e)
U = {e, e+250ms, ..., e+H}

long_liquidation_bps(u)  = 10000 * log(bid(u) / a_e)
short_liquidation_bps(u) = 10000 * log(b_e / ask(u))
```

These paths assume a small marketable long enters at the future ask and can be
liquidated at a future bid; a short enters at the future bid and covers at a
future ask. Thus they already include crossing the observed spread at entry and
liquidation. Spread must not be subtracted a second time. Exchange fees,
slippage stress, and impact remain separate economic adjustments.

Define:

```text
tau_long  = first u in U with long_liquidation_bps(u)  >= B
tau_short = first u in U with short_liquidation_bps(u) >= B
```

Then:

```text
LONG_FIRST  if tau_long exists and (tau_short does not or tau_long < tau_short)
SHORT_FIRST if tau_short exists and (tau_long does not or tau_short < tau_long)
NONE        if neither barrier is reached by e+H
```

### 10.2 Exact ambiguity and validity rules

- Search timestamps in ascending 250 ms grid order. The horizon endpoint
  `e+H` is included.
- The current decision row never supplies the entry; entry is exactly the first
  row at `t+250ms`.
- If both barriers first appear in the same 250 ms row, timestamp order is not
  identifiable. Serialize `label=null`, `target_valid=false`,
  `invalid_reason="same_row_ambiguous"`, and `same_row_ambiguous=true`.
  Exclude the row from all predictive fitting and evaluation, and report it
  separately in diagnostics. Never break the tie using row column order. With
  positive symmetric barriers and valid uncrossed entry/current books, such a
  case should be structurally impossible; its occurrence is also a
  data/implementation diagnostic.
- Require a valid, finite, positive, uncrossed bid/ask at entry and every row in
  `[e, e+H]`. A missing/invalid interval makes the target invalid—not `NONE`—
  because an unobserved competing touch cannot be ruled out.
- Require the complete path to remain inside one UTC day. No prior-day or
  next-day fill, interpolation, or future backfill.
- Equality at a barrier counts as reached (`>= B`).
- No quote after `e+H` may affect the target.
- `NONE` is reserved exclusively for a fully observed, target-valid path where
  neither barrier is reached. It is never used for missing, invalid, or
  ambiguous targets.

The first-passage horizontal barriers are *labels*, not deployed take-profit or
stop-loss instructions.

### 10.3 Target diagnostics

For every candidate sample record, persist the target state:

```text
label = LONG_FIRST | SHORT_FIRST | NONE | null
target_valid = true | false
invalid_reason = null | "same_row_ambiguous" | <other explicit invalidity code>
same_row_ambiguous = true | false
```

`label` must be `null` whenever `target_valid=false`. A same-row ambiguity must
use exactly `label=null`, `target_valid=false`,
`invalid_reason="same_row_ambiguous"`, and `same_row_ambiguous=true`. Invalid
targets are excluded from all predictive fitting and evaluation but retained
in separate diagnostic counts.

For each `target_valid=true` sample, also record:

```text
time_to_first_barrier_ms = tau - e, or null
barrier_reached_timestamp_us = tau, or null
long_max_favorable_excursion_bps = max(0, max_u long_liquidation_bps(u))
long_max_adverse_excursion_bps = max(0, -min_u long_liquidation_bps(u))
short_max_favorable_excursion_bps = max(0, max_u short_liquidation_bps(u))
short_max_adverse_excursion_bps = max(0, -min_u short_liquidation_bps(u))
entry_spread_bps = 10000 * log(a_e / b_e)
```

Excursions and touch time are labels/diagnostics only and must never enter
features for the same decision.

### 10.4 Development grid, not a selection

The first target-feasibility audit may map horizons `{10, 30, 60, 120, 300,
600}` seconds and symmetric executable gross barriers `{4, 8, 12, 16, 24,
36}` bp. This is intentionally a *proposed* space, not today's winner. Before
modeling, report class counts, ambiguity, valid support, time-to-touch, spread,
and cost headroom by day. Barriers below the conservative round-trip cost can
diagnose predictability but cannot qualify as economically actionable without a
different execution mode.

To contain multiplicity, choose a small target subset after the label-only
audit using support, temporal resolution, and predeclared cost plausibility—
not model performance—then freeze that subset for model comparison.

## 11. Opportunity Conditioning Designs

The opportunity layer is retained, but conditioning is a development factor.
All designs use a training-fitted EXP024-family opportunity model and never a
validation-fitted calibration.

| Design | Direction-model population | Use of opportunity information | Main question |
|---|---|---|---|
| A: continuous | All valid rows | Raw opportunity score as one context feature | Does magnitude/rank context modulate direction without discarding support? |
| B: causal percentile | All valid rows | Rolling percentile/rank computed before inserting current score | Is regime-relative opportunity context more stable than probability scale? |
| C: gate first | Only rows above a training/causal gate | Gate grid may later include 0.70–0.95 percentiles | Is direction learnable specifically in high-opportunity states, and is support adequate? |
| D: direction first | All valid rows | Opportunity applied only to action threshold after OOS direction scoring | Does separating learning from action prevent sparse-fold failures? |
| E: interaction/mixture | All valid rows | Direction confidence × opportunity score/rank and explicit interaction terms | Does opportunity intensity change which microstructure path matters? |

EXP029 proves only that one 1399-score/q90 online policy missed one frozen gate;
it does not freeze DEV030 at q90. Any gate search must be confined to inner
chronological development folds and judged on direction/support without using
the future forward holdout.

Meta-labeling is a later option, not an assumption. Plausible structures are:

1. primary direction (`LONG_FIRST` vs `SHORT_FIRST`), secondary act/abstain;
2. primary opportunity, secondary direction;
3. primary side heuristic/model, meta-model predicting whether its executable
   outcome clears cost.

Structure 1 is appropriate only if a side model first shows stable OOS
information. Structure 2 most directly preserves EXP024. Structure 3 risks
learning the same PnL twice and should wait for enough trades. No meta-model may
be sold as a substitute for a weak primary direction model.

## 12. Cross-Asset Design

The first feasibility pairing is BTC target with causal ETH features because
both have prepared Phase0DL 250 ms data. SOL has no equivalent historical
Phase0DL rows and must remain a future option after new data has accumulated
under an authorized protocol.

For each BTC decision `t`:

1. BTC features and its sequence end at timestamp `<= t`.
2. For an ETH feature requested at BTC time `s <= t`, select the most recent
   valid ETH row with `eth_timestamp <= s` (`searchsorted(..., side="right")-1`).
3. Never use the next ETH row, symmetric interpolation, or a value whose local
   receive timestamp exceeds the BTC cutoff.
4. Record staleness `s - eth_timestamp`; reject beyond a pre-frozen tolerance.
5. Require the entire ETH sequence's own validity and continuity.
6. Fit normalization, lead/lag selection, and interactions on training only.

If the grids have exact matching timestamps, exact alignment should be the
primary implementation. An as-of join exists only for genuinely asynchronous
sources and must be past-only. Before modeling, audit timestamp equality,
staleness, gaps, and common-support loss without examining direction labels.

Candidate cross-asset families for later testing are lagged ETH OFI/MLOFI,
ETH microprice/OBI shocks, BTC-minus-ETH standardized flow, relative short
return/volatility/spread, and disagreement between leader flow and target book.
Test positive lags explicitly; same-row correlation is not evidence that ETH
leads BTC. Reverse BTC-to-ETH models can be a development diagnostic but are a
separate target population.

## 13. Model Ladder

Escalation should be evidence-driven:

| Level | Models | Representation | Promotion question |
|---|---|---|---|
| 0 | Signed OBI/microprice/OFI heuristics; momentum | Latest and simple cumulative path | Is there any transparent directional structure? |
| 1 | Multinomial/one-vs-rest LogisticRegression; regularized linear models | S0 then S1 summaries | Does sequence information add linearly on matched support? |
| 2 | HistGradientBoosting, then optionally LightGBM/XGBoost/CatBoost | Bounded S1 summaries | Are stable nonlinear interactions present after the representation proves useful? |
| 3 | Small MLP | S1 summaries | Does smooth nonlinear combination beat trees/linear across days? |
| 4 | Small causal 1D CNN or TCN | S2 tensors and masks | Does learned temporal pattern beat engineered summaries? |
| 5 | TLOB/attention-style model | Raw/light sequences, only with sufficient data | Does long-range/feature attention add stable incremental information after Level 4? |

Every level uses the same target rows, chronological folds, and primary metrics
as its matched baseline. A higher level is justified only by stable incremental
OOS value, not training loss. Complexity, inference latency, memory, and
retraining cost are recorded as metrics. A simple model that survives costs is
preferred to a complex model with marginal classification lift.

## 14. Leakage-Safe Validation

### 14.1 Development data and outer folds

Initial DEV030 development should use only the already-consumed Jan–Jul
Phase0DL BTCUSDT/ETHUSDT days with verified manifests. The natural first outer
design preserves the four expanding folds already implemented in EXP026:

1. train Jan–Mar, validate Apr;
2. train Jan–Apr, validate May;
3. train Jan–May, validate Jun;
4. train Jan–Jun, validate Jul.

No random train/test shuffle is permitted. All preprocessing, feature
selection, target subset selection, model tuning, probability/rank transforms,
opportunity gates, class weighting, and abstention thresholds must be fit or
chosen inside the training side of each outer fold.

If later development uses additional already-consumed Jan–Jul dates, it should
use day-blocked expanding or rolling walk-forward folds, with the calendar and
input hashes recorded. It must not silently combine a Phase0DH calendar with
Phase0DL rows.

### 14.2 Sample information intervals

For each sample define and retain:

```text
feature_start = t - sequence_lookback
feature_end   = t
entry_time    = t + 250ms
label_end     = entry_time + target_horizon
information_interval = [feature_start, label_end]
```

Purging is based on these intervals, not row numbers alone. A training sample
whose future label interval overlaps a validation information/label interval is
removed. When a splitter permits training after a validation block, apply an
embargo of at least the maximum target horizon plus the maximum sequence
lookback, then verify interval non-overlap explicitly. The preferred first
implementation is forward-only expanding validation, which avoids training on
later observations entirely.

The public triple-barrier implementations are useful patterns, but their
backfilled close-price alignment must not be copied. DEV030 uses exact grid
timestamps, past-only feature joins, and fully observed executable paths.

### 14.3 Nested development without holdout leakage

- **Outer fold:** estimates honest day/regime generalization.
- **Inner folds inside outer training:** choose target subset, sequence window,
  representation, model hyperparameters, and action threshold.
- **Outer validation:** evaluate the once-selected pipeline; never tune on it.
- **Final Jan–Jul development fit:** only after a design is selected and its
  OOF records are frozen; it still does not authorize Sep-01+ opening.

Search results should be logged completely, including failed trials. Use a
deterministic experiment registry keyed by feature/target/model/split hashes so
that repeated searches cannot quietly erase negative outcomes.

### 14.4 Metrics and stability

For every fold/day and pooled OOF set record:

- `LONG_FIRST`, `SHORT_FIRST`, `NONE`, invalid (`label=null`), and same-row
  ambiguity counts;
- balanced accuracy and macro F1;
- per-class precision/recall/F1, especially LONG and SHORT;
- actionable precision and recall among non-abstained predictions;
- direction accuracy conditional on action;
- coverage and abstention rate;
- confusion matrix and class-balanced null baselines;
- probability Brier/log loss only when probabilities are actually consumed;
- training/validation support and purged-row counts;
- per-day/regime metrics, positive/negative days, and dispersion;
- inference latency and model size.

Do not judge performance from pooled rows alone. Dense overlapping rows can
make one regime dominate and give a false sense of sample size. Report a
direction-independent non-overlapping view and cluster summaries by day/event.

Useful falsifications during development include time-shifting labels within
each validation day, permuting sequence time order while preserving row values,
permuting only the microstructure block while preserving price/opportunity
context, and reversing sequence order. These are diagnostics for information
location, not a license to select whichever null is easiest to beat.

## 15. Economic Evaluation

Classification is an intermediate diagnostic. A candidate advances toward a
trading policy only after a frozen OOF prediction ledger is evaluated against
executable quotes.

### 15.1 Action mapping

- Predict `LONG_FIRST`, `SHORT_FIRST`, or abstain/`NONE`.
- Enter no earlier than `t+250ms` at the observed ask for long or bid for short.
- Evaluate fixed-horizon liquidation first using the existing executable helper
  for comparability.
- Apply flat-only non-overlap and record ignored signals, clustering, holding
  time, and exposure.
- A target-aligned “exit on barrier touch” policy would be a separate execution
  hypothesis and must be frozen before economic scoring; first-passage labels
  do not themselves authorize a take-profit or stop-loss strategy.

### 15.2 Required later metrics

- gross executable bps/trade and total gross bps;
- net bps/trade and total net after actual fee assumptions;
- conservative transaction-cost/slippage stress;
- trade count, turnover, exposure, and holding-time distribution;
- win rate, profit factor, maximum drawdown, and PnL/drawdown;
- per-day expectancy, positive-day fraction, worst day/fold, and regime split;
- LONG/SHORT counts and side-specific economics;
- signal clustering and ignored signals under non-overlap;
- sensitivity to reaction latency and size assumptions.

Bid/ask crossing already present in executable returns must not be deducted
again. Fees and conservative slippage are separate. Gross expectancy must be
reported because EXP002 showed a signal can lose before fees; zero activity is
not a successful filter.

No leverage or position-size optimization belongs in DEV030-P0. If direction
and conservative unlevered economics survive, risk sizing becomes a later
layer with its own forward validation.

## 16. Execution Realism Audit

### 16.1 What current helpers model

`codex_exp004_headroom.executable_fixed_horizon` models a deterministic small
aggressive trade:

- exact 250 ms reaction delay;
- entry at observed future ask (long) or bid (short);
- exit at observed bid (long) or ask (short);
- exact fixed duration and same-day boundary;
- spread crossing and invalid-book rejection.

EXP026 adds fixed incremental cost/stress envelopes, flat-only occupancy,
profit factor, and drawdown. EXP002 separately contains a conservative passive
RiskAverse queue replay using trades, inferred cancellations, response latency,
timeouts, and partial fills.

### 16.2 What current aggressive evaluation does not model

| Component | Current support | Honest treatment now |
|---|---|---|
| Reaction latency | Fixed 250 ms | Keep as primary comparability assumption; later stress 500/1000 ms. Do not claim measured latency distribution. |
| Bid/ask spread | Exact observed BBO | Modeled reliably for a very small aggressive trade. |
| Fees | Added downstream as fixed bps | Use documented account/taker assumptions and stress; keep separate from spread. |
| Slippage beyond BBO | Not observed by fixed helper | Add conservative bps stress; cannot estimate size-dependent sweep without depth. |
| Top-of-book available size | Historical Phase0DL has quantities, helper ignores them | Add a capacity check before economic claims; reject or haircut trades exceeding displayed size. |
| Market impact | Not modeled | No claim above small hypothetical size. Requires depth and own-order experiments. |
| Partial fills | Not modeled for aggressive path | Assume only tiny IOC/marketable size until depth replay exists; otherwise invalid. |
| Queue position | Not relevant to immediate taker entry; not modeled for passive exits | Do not use passive economics unless EXP002-style or richer replay assumptions are explicitly justified. |
| Latency variation | Not modeled | Scenario analysis only until local/order latency data exist. |
| Maker/taker choice | Current direction path is taker/taker | Do not mix maker rebates with taker fill certainty. A maker policy is separate. |

This simple model is preferable to a precise-looking simulator built on
missing fields. hftbacktest becomes valuable only after full tick L2/L3 or
diff-depth plus trades, exact local/exchange timestamps, exchange sequence
integrity, quantity, and defensible latency/queue assumptions exist. Its queue
and partial-fill models still require live-vs-replay calibration.

## 17. Future Data Collection Opportunities

Do not modify EXP025 or EXP027. Keep their `bookTicker` archive as the reliable
BBO/provenance stream and add separate synchronized streams with independent
immutable manifests if approved. Binance's official USD-M Futures market-stream
specifications document
[aggregate trades](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/websocket-market-streams/Aggregate-Trade-Streams),
[partial book depth](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/websocket-market-streams/Partial-Book-Depth-Streams),
and
[diff book depth](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/websocket-market-streams/Diff-Book-Depth-Streams).
Each new stream needs sequence-gap, reconnect, clock, storage, and rollover
tests.

| Proposed additive stream | Short-horizon direction value | Queue/execution value | Priority | Reason and caution |
|---|---:|---:|---:|---|
| Aggregate trades (`aggTrade`) | Very high | High | 1 | Gives aggressor side/quantity and trade bursts needed for flow trajectories. Aggregation can hide individual fills; preserve IDs/timestamps. |
| Diff depth plus authoritative snapshot/recovery protocol | Very high | Very high | 1 | Reconstructs cancellations, replenishment, depletion, multi-level OFI, and depth. Sequence gaps must invalidate state; no historical backfill into a sealed gap. |
| Partial depth top 5/10/20 at 100 ms | High | Medium/high | 2 | Faster path to raw spatial tensors and displayed capacity. It cannot distinguish event causes or exact queue priority. |
| Individual trades, where available and semantically distinct | High | Very high | 2 | Better queue/fill matching than compressed trades, at higher storage/processing cost. |
| Existing bookTicker | Medium for direction; high for spread/microprice L1 | Medium for tiny taker execution | **KEEP** | Already robust and cheap. It cannot produce deep OFI or queue reconstruction. |
| Mark/index price and premium | Low/medium regime context | Low | 3 | Cheap contextual stream, but Phase0DJ failed incremental direction; use only as a controlled ablation. |
| Liquidations | Medium in rare stress regimes | Medium | 3 | May identify cascade direction/opportunity but is sparse and easy to overfit. |
| Open interest | Low/medium at seconds-to-minutes | Low | 4 | Slow/stateful; EXP005 gave negative incremental opportunity evidence. |
| Funding | Low at microstructure horizon | Low | 5 | Very slow-moving; useful regime metadata, unlikely primary 8–60s direction. |

The most informative new collector would combine diff depth, periodic snapshot
integrity, and trades for BTC/ETH/SOL while leaving EXP027 untouched. Start it
as an additional service/object namespace; do not replace prior raw files or
retrofit missing intervals. New data becomes usable for a hypothesis only after
that hypothesis and opening policy are frozen.

## 18. Proposed Development Search Space

No winner is selected in this document. The space is intentionally staged:

| Axis | Proposed values | Stage/control |
|---|---|---|
| Target horizon | 10, 30, 60, 120, 300, 600 seconds | Label-feasibility audit first; then freeze a small supported subset |
| Gross executable barrier | 4, 8, 12, 16, 24, 36 bp, symmetric initially | Support/cost audit only before model scoring; no asymmetric search initially |
| Sequence window | 8, 16, 32, 60 seconds | Compare S0 latest row to S1 summaries; raw S2 only after incremental evidence |
| Feature blocks | price-only; L0; L1 flow; L2 changes/queue; combined | Add blocks incrementally on identical support |
| Opportunity context | none; raw score; causal rank; interactions; inner-trained gates such as 0.70–0.95 | Treat as a separate ablation, never derive a gate from outer validation |
| Cross-asset | BTC-only; BTC + lagged ETH | Only after timestamp/support audit and single-asset baseline |
| Model | heuristic, logistic, boosting, MLP, causal CNN/TCN, attention | Escalate one level only after the prior level demonstrates sequence value |
| Action policy | ternary argmax; confidence abstention; opportunity-conditioned abstention | Tune in inner folds and record coverage/precision curves |

Search should proceed in four bounded campaigns:

1. **Target/support:** no models; choose supportable, cost-plausible targets.
2. **Representation:** one or two targets; heuristic/linear snapshot vs summary
   sequences.
3. **Conditioning/nonlinearity:** opportunity variants and boosting/MLP only on
   representations that cleared campaign 2.
4. **Raw sequence/cross-asset:** CNN/TCN, then possibly attention, plus lagged
   ETH only if earlier campaigns show stable information.

This sequential design prevents one enormous Cartesian search from producing a
winner by chance. Every campaign emits all OOF records and a trial ledger.

## 19. Ablation Plan

All comparisons use exact common support, identical folds, identical target,
and training-only tuning.

| Question | Reference | Candidate | Decisive observation |
|---|---|---|---|
| Snapshot vs sequence | Latest L0/L1/L2 row | S1 summaries of same primitives/window | Stable per-day incremental macro F1/balanced accuracy and executable direction precision identifies path value (B vs A). |
| Fixed horizon vs first passage | Existing signed fixed-horizon executable label | Same entry/horizon, first-touch executable label | Improvement isolated to target supports explanation C. |
| Without vs with opportunity conditioning | Direction model with no opportunity field/gate | Continuous score, causal rank, then inner-trained gate/interaction | Stable improvement with adequate coverage supports D; sparse success does not. |
| Single asset vs cross asset | BTC sequence only | BTC plus strictly lagged ETH sequence | Incremental OOS value after timestamp/staleness controls supports G. |
| Summary vs raw sequence | S1 engineered summaries | S2 causal tensor with same primitives/window | Raw model improvement beyond complexity-matched controls supports unmodeled path geometry. |
| Simple vs nonlinear | Regularized logistic | Boosting/MLP/CNN on same support | If nonlinear gains are unstable, choose simple; stable gains identify interactions rather than mere capacity. |
| Short vs long timing | 10/30/60s horizon/window families | 120/300/600s | Decay profile tests F and helps avoid forcing microstructure into a 10-minute target. |
| Statistical vs economic edge | Direction metrics | Same frozen actions through bid/ask + fees/stress | Positive classification but negative gross/net supports E. |
| Flow vs price | Price/return sequence | OFI/MLOFI/trade/queue additions | Isolates true microstructure value from momentum. |

Also ablate time order: shuffle rows within each sequence, reverse them, and
retain only distribution summaries. If performance survives all three, the
model is not using temporal evolution as hypothesized.

## 20. Stop / Continue Logic

These are practical development recommendations to freeze in each future run,
not academic claims or retroactive gates.

### Continue direction research when

- every outer fold has adequate LONG/SHORT/NONE support and low invalidity;
- sequence representation improves matched snapshot baselines in the median
  fold and in at least three of four outer folds;
- a provisional meaningful increment (for example `>= 0.02` absolute macro F1
  or an equivalent precision-at-coverage gain) survives time-order and block
  permutation diagnostics;
- both LONG and SHORT have useful precision/recall—not one majority side;
- the result is not concentrated in one day, one volatility bin, or a tiny
  confidence tail;
- simpler baselines cannot explain the gain.

The exact numeric promotion thresholds should be set after the target-only
support audit but before model outputs. Development flexibility allows changing
them in a new logged run, not erasing the old run.

### Advance to economics when

- direction information meets the stability conditions above;
- the action policy has enough non-overlapping trades for day-level estimates;
- small-taker executable **gross** expectancy is positive in most validation
  days and not dependent on one tail event;
- base-cost net expectancy is positive pooled and by median day, profit factor
  is plausibly above one, and stress is not catastrophic;
- latency and cost sensitivities degrade smoothly rather than flipping on one
  optimistic assumption.

A concrete later readiness template could require at least three positive of
four outer folds, pooled and median-day net expectancy above zero, PF `> 1.10`,
positive-day fraction `>= 0.60`, and sufficient trade count per fold. Those
numbers must be frozen for the relevant experiment, not applied retroactively.

### Stop or pivot when

- no sequence family beats the matched snapshot after the bounded campaigns;
- first-passage labels are too sparse/ambiguous at cost-plausible barriers;
- gains disappear under day/regime splits or causal perturbations;
- only increasingly complex models improve training/inner metrics;
- direction is measurable but gross executable returns remain negative;
- performance requires an infeasible latency, size, or fill assumption.

The corresponding pivots are informative: improve data if path features are
missing; shorten horizon if signal decays; change target if terminal labels are
the failure; or stop direction work and use the opportunity signal for a
different product/process. Do not keep changing classifiers indefinitely.

## 21. Proposed Implementation Architecture

Future code should be modular and reuse-first:

| Proposed file | Responsibility | Reuse |
|---|---|---|
| `src/multimarket/dev030_first_passage.py` | Pure executable path labels, validity, touch ordering, MFE/MAE, target audit | `DayData`, EXP004 bid/ask conventions, EXP023 JSON safety |
| `src/multimarket/dev030_sequences.py` | Valid causal tensor slicing and engineered summaries | Phase0DL names/masks; no raw data loader duplication |
| `src/multimarket/dev030_opportunity.py` | Frozen EXP024 score adapter plus development rank/gate transforms | `codex_exp004_p1`, `codex_exp024_p1`, EXP029 causal-rank primitive where suitable |
| `src/multimarket/dev030_alignment.py` | Exact/as-of past-only BTC/ETH alignment and staleness diagnostics | Existing timestamp arrays; `searchsorted(side="right")` |
| `src/multimarket/dev030_splits.py` | Information intervals, purging, embargo, expanding/rolling folds | Existing calendars and chronology guards |
| `src/multimarket/dev030_models.py` | Common estimator interface and model ladder | scikit-learn first; optional packages isolated |
| `src/multimarket/dev030_evaluation.py` | Classification, coverage, stability, falsifications, OOF ledger | sklearn metrics, EXP024 ranking helpers where exact |
| `src/multimarket/dev030_economics.py` | Frozen prediction-to-action mapping and executable accounting | EXP004 fixed-horizon, EXP026 costs/PF/DD/non-overlap |
| `src/multimarket/dev030_runner.py` | Explicit manifests, deterministic configs, nested runs, atomic artifacts | EXP023/024/026 provenance and serialization patterns |

Corresponding focused tests should use synthetic `DayData` and hand-calculated
paths. Required test families include causality/future mutation, invalid-window
rejection, same-row ties, horizon boundaries, sequence masks, train-only
normalization, purged intervals, cross-asset as-of joins, matched support,
non-overlap, cost accounting, JSON finiteness, and one-shot artifacts.

Do not expose arbitrary future-date globs. Development inputs should be an
explicit Jan–Jul manifest. A future forward runner should be a separate mode or
module that refuses unopened inventory unless a frozen protocol authorizes it.

## 22. Immediate Next Step

After human review, implement **only**
`src/multimarket/dev030_first_passage.py` and
`tests/test_dev030_first_passage.py` first.

The implementation should:

1. accept an in-memory `DayData`, explicit decision indices, horizon, barrier,
   and fixed 250 ms latency;
2. produce the exact target/diagnostic fields in Section 10;
3. prove with synthetic fixtures that no current/future mutation leaks into
   earlier features or touches; same-row ambiguity produces exactly
   `label=null`, `target_valid=false`,
   `invalid_reason="same_row_ambiguous"`, and `same_row_ambiguous=true`; the
   ambiguous row is excluded from every predictive fitting/evaluation support;
   invalid gaps do not become `NONE`; and day boundaries are rejected;
4. compare the horizon-end executable values against
   `executable_fixed_horizon` on synthetic data;
5. expose no August/future/network or arbitrary-glob interface.

Only after that code is reviewed and frozen should a **label-only feasibility
audit** run on explicit consumed Jan–Jul inputs. It should fit no direction
model. Its job is to reduce the target grid using support, validity, class
balance, touch timing, spread, and cost plausibility. Sequence construction is
the following implementation step, not part of the first change.

---

Audit guards for this design task:

```text
SEP01_OR_LATER_ANALYTICALLY_OPENED = NO
AUG30_REOPENED_FOR_DEV030 = NO
EXP029_RERUN = NO
EXP029_MODIFIED = NO
EXP025_MODIFIED = NO
EXP027_MODIFIED = NO
REAL_DEV030_MODEL_FIT_RUN = NO
```

# CODEX-EXP-002 Independent Red-Team Review

Date: 2026-08-25
Status: **reviewed before preregistration and scoring**

## Independent critics

The same frozen prompt was prepared for both requested model families. A usable local Ollama 0.32.13 runtime was discovered in Ubuntu WSL2.

- Qwen: `qwen3:30b-thinking`, Ollama ID `ad815644918f`, base blob SHA-256 `58574f2e94b99fb9e4391408b57e5aeaaaec10f6384e9a699fc2cb43a5c8eabf` — run completed.
- Llama: unavailable. No Llama model was installed in the discovered runtime and no other usable local Llama runtime/model was found. Nothing was downloaded or installed.

Artifacts are under `evidence/codex/exp002_red_team/`. Model opinions are architecture criticism, not market evidence. Decisions below are Codex decisions; there is no majority vote.

## Concern-by-concern adjudication

| Concern | Qwen view | Llama view | Codex assessment | Decision | Reason |
|---|---|---|---|---|---|
| 1. Lookahead/leakage | Called exchange-time reconstruction a blocker; required local timestamps. | Unavailable. | The “guaranteed leak” claim is unsupported, but local arrival time is the correct observer clock and was already frozen by Phase L. Equal-local-time rows must remain atomic. | **ACCEPT** | Use local timestamps exclusively and add causal/equal-arrival tests. |
| 2. Queue realism | Claimed best-price orders fill immediately and the conservative queue contradicts price-time priority. | Unavailable. | This is false. A newly arrived order joins behind prior same-price quantity; best price does not imply first queue position. MBP cannot reveal exact order rank. | **REJECT** | Retain RiskAverse semantics and forbid touch-equals-fill. |
| 3. MBP/L2 limitations | Claimed all useful L2 information is inside 50 ms and 250 ms is obsolete. | Unavailable. | The numerical claim is unsupported. MBP uncertainty and 250 ms coarseness are real limitations. The experiment tests the conservative 250 ms mechanism rather than changing to a faster rescue. | **MODIFY** | State the limitation, use 250 ms primary, 500 ms slower sensitivity only. |
| 4. Fill-model optimism | Argued that treating fills as successes ignores adverse selection. | Unavailable. | Correct distinction, although the invented “>70%” statistic is unsupported. A fill is an execution event, not a good outcome. | **ACCEPT** | Separate fill probability from conditional post-fill markout/economics. |
| 5. Adverse-selection accounting | Said a separate adversity predictor is required. | Unavailable. | Agreed in substance. The frozen architecture uses a distinct Ridge conditional gross-markout model and does not hide it inside the fill classifier. | **ACCEPT** | P1 acts on calibrated expected net value from two separate models. |
| 6. Fees | Claimed every Binance USD-M maker receives a 2 bp rebate. | Unavailable. | The universal-rebate claim is false and conflicts with the official signed account commission endpoint example, which shows a positive maker rate. Personal fees are unavailable. | **REJECT** | Freeze no-rebate 2 bp maker + 4 bp taker primary and 3 + 5 bp stress. |
| 7. Latency | Claimed 250 ms guarantees no opportunity and demanded ≤100 ms. | Unavailable. | Unsupported and internally inconsistent: if the order has not arrived, it cannot already be filled. Faster latency could create a rescue. | **REJECT** | Freeze 250 ms order/response latency and allow only slower 500 ms sensitivity. |
| 8. Cancellation/timeout | Argued cancellations ahead should improve queue position. | Unavailable. | True in MBO when cancellation rank is known, but not identifiable from MBP. Crediting unknown cancellations is precisely the optimism the primary model must avoid. | **REJECT** | Primary credits no cancellation advancement; Q50 is diagnostic only. |
| 9. Partial fills | Said partials were ignored and must be modeled or excluded. | Unavailable. | Valid. Its “>60%” statistic is unsupported, but omission would bias fills and inventory. | **ACCEPT** | Account for executed quantity; first partial triggers a latency-bearing cancel; all executed inventory exits. |
| 10. Inventory | Said passive fills create inventory and downside cannot be ignored. | Unavailable. | Valid. The proposed claim that the design had no taker exits was mistaken, but inventory must be bounded. | **ACCEPT** | Fixed small size, one candidate every 15 s, no same-symbol overlap, taker exit 10 s after fill plus response latency. |
| 11. Opportunity inflation | Warned against counting isolated profitable fills; cited invented profitability rates and EXP001 as proof. | Unavailable. | The general concern is valid; the numbers and inference from the different taker/taker hypothesis are not. | **MODIFY** | Exogenous nonoverlapping stream, ≥200 P1 completions, ≥20 per outer fold, concentration and stability gates. |
| 12. Multiple testing | Said the grid was too large and demanded one configuration. | Unavailable. | Valid direction. EXP002 freezes one lifetime, one economic horizon, two fixed model regularizations, and only three inner EV cutoffs. | **ACCEPT** | Five chronological outer folds; no outer tuning or model-family search. |
| 13. Simulator profitability | Claimed conservative queues prevent every fill, so any profit is an artifact. | Unavailable. | The premise is false; same-price trade volume can consume the displayed queue. The artifact risk is nonetheless central. | **MODIFY** | Synthetic queue/causality/no-touch tests, candidate ledger, exact raw-trade replay and conservative primary verdict. |
| 14. Cross-venue precedence | Asserted cross-venue data is the only viable path. | Unavailable. | Unsupported. Cross-venue information is a strong future hypothesis, but it cannot be declared necessary before this distinct passive mechanism is tested. | **REJECT** | Preserve cross-venue as the next hypothesis if EXP002 fails; do not import new data here. |
| 15. Falsification | Predicted zero fills and proposed abandoning after one minute. | Unavailable. | One minute is not a defensible sample and zero fills is not known in advance. The general demand for explicit falsification is correct. | **MODIFY** | Freeze hard completion, economics, stability, stress, incrementality, and conservative-queue gates. |

## Accepted design changes

- One 3 s primary lifetime and one 10 s economic exit horizon; 1/3/10 s markouts are reporting points, not a search grid.
- Deterministic 15 s alternating-side candidate stream, eliminating overlapping same-symbol orders and discretionary side selection.
- Explicit partial-fill cancellation and inventory exit.
- Separate fill and conditional-markout models.
- Q50 cancellation-credit queue and 500 ms latency are diagnostic only.
- Strong minimum-coverage, outer-fold, cost-stress, concentration, P1-over-P0, and adverse-fill gates.

## Rejected unsupported claims

The Qwen response supplied no sources and invented precise statistics about adverse fills, partial fills, profitability rates, latency, and universal maker rebates. It also misstated price-time priority. None of those claims enters the preregistration or evidence base.

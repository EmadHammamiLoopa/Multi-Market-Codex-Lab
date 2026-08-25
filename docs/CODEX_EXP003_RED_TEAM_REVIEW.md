# CODEX-EXP-003 Red-Team Review

Status: **MODIFIED AND ACCEPTED FOR PRE-SCORE FREEZE**

Date: 2026-08-25

## Review process

The design received two independent attacks before external market-data acquisition:

1. local `qwen3:30b-thinking` through Ollama, using the saved exact prompt; and
2. Codex's source/documentation/code review.

No Llama-family model was installed in the discovered local runtime. No model was downloaded, installed, or silently substituted. This limitation is recorded in `evidence/codex/exp003_red_team/CODEX_EXP003_LOCAL_MODEL_DISCOVERY_20260825.json`.

Artifacts:

- exact prompt: `evidence/codex/exp003_red_team/CODEX_EXP003_INDEPENDENT_REVIEW_PROMPT.txt`
- raw Qwen response: `evidence/codex/exp003_red_team/QWEN3_30B_THINKING_RAW_RESPONSE_20260825.md`
- run metadata: `evidence/codex/exp003_red_team/QWEN3_30B_THINKING_RUN_METADATA_20260825.json`

Model reviews are opinions, not evidence and not votes. The Qwen verdict was `ABANDON`; Codex did not adopt that verdict mechanically. Each attack was checked against the official schema, the actual frozen question, and causal-market-data semantics.

## Independent critic's strongest attacks

Qwen correctly emphasized four central risks:

- public documentation does not provide a hard cross-host clock-skew bound;
- a common collector region does not make source-to-collector network paths equivalent;
- exchange timestamps must be technically prevented from entering joins;
- gap handling is difficult because downloadable CSVs omit explicit disconnect events.

It also correctly demanded exact feature endpoints, training-only scaling, common-support comparison, explicit nonoverlap, and a no-rescue distinction between primary and diagnostics.

Several critic claims were not technically supported and were rejected:

- Different network propagation cannot make an event that arrived at a correctly synchronized collector after `t` appear to have arrived before `t`; it can make the arrival-vantage comparison conservative or venue-path-specific. The unresolved issue is collector-clock comparability, not an automatic reversal caused by distance.
- Tardis `book_snapshot_5` has one documented normalized schema and reconstruction policy across sources. The claim that one venue's public top five includes hidden orders was unsupported.
- Within-source quantity imbalance does not assume identical units: multiplying every amount by a positive contract multiplier cancels in the ratio.
- Common-news response does not invalidate incremental predictive information after conditioning on X0. It prevents a structural venue-causation claim, which this experiment does not make.
- Ordering on exchange timestamps would be less causal, not more; that suggestion conflicts with the critic's own leakage warning and the official meaning of the fields.
- A deliberate future-leak canary is a positive control. It should improve apparent prediction; failure to improve attacks diagnostic sensitivity. It is isolated and cannot enter primary selection.
- Requiring X0 to pass the 8 bp profitability gate before external data would make the new information hypothesis logically impossible after EXP-001's closed failure. EXP-003 instead requires X0 to be measured on every fold and requires XALL to beat it economically.

## Concern disposition

| Concern | Severity | Attack | Frozen disposition |
|---|---|---|---|
| Cross-host local-clock comparability | High | no published hard skew bound | restrict conclusion to Tardis collector-vantage availability; 500 ms primary, 1,000 ms stress, age audit |
| Collector/network-path confounding | High | Bybit Singapore→Tokyo differs from Binance Tokyo→Tokyo | report topology; do not infer engine leadership or co-located executability |
| Fixed 500 ms embargo | High | policy is not an estimated skew bound | label it conservative policy, not calibration; 250 ms cannot rescue; 1,000 ms reported |
| Exchange-timestamp leakage | Blocker if present | accidental sort/join can reveal or reorder events | exchange timestamp is audit-only; invariance test mutates it without changing features |
| Equal receipt timestamps | Medium | exposing intermediate rows can invent state | treat as atomic; retain final file-order full snapshot; never exchange-time tie-break |
| Omitted disconnects/stale books | High | invisible outage could be forward-filled | 2 s max age and segment break; all 3 s history must reaccumulate after a gap |
| Snapshot semantic comparability | Medium | venue feeds/update rates differ | uniform Tardis reconstruction; ratios/returns only; no raw depth comparison; topology limitation retained |
| Trade-side/unit comparability | Medium | side conventions or contract units could differ | use Tardis aggressor side; reject `unknown`; dimensionless within-source quantity/count ratios |
| Feature endpoint leakage | Blocker if present | a window can accidentally end at `t` or later | all external windows end at `c=t−500ms`; explicit as-of tests |
| Normalization leakage | Blocker if present | fitting on calibration/outer rows | explicit NumPy standardizer fitted only on base training; tested mean |
| Label/execution timing | High | mid labels or zero-latency entries inflate returns | entry at target row `t+250ms`, executable ask/bid entry and bid/ask exit |
| Multiple testing | High | source/horizon/grid search can capitalize on noise | one primary XALL track; frozen 20 combinations; X1/X2 diagnostic; strict outer/stability gates |
| XALL versus X0 support | Blocker if unequal | missing external rows can improve sample composition | all four tracks use XALL common support exactly |
| Incrementality confounded by no X0 sample | High | no measured comparator means “beat X0” is undefined | promote covered inner X0 configs even when negative; require X0 observed all five folds |
| Placebo/canary ambiguity | High | a diagnostic can be reinterpreted post hoc | freeze roles and directions before data; sign is changed on outer XALL only so it is not a retrainable reparameterization; no diagnostic can rescue primary |
| Opportunity inflation | High | overlapping 250 ms decisions are dependent | greedy nonoverlap over reaction plus selected 10/30 s horizon |
| Day-boundary leakage | Blocker if present | label or window crosses midnight | purge target labels, calibration midpoint, external segments, and file days |
| Common response vs structural cause | High | predictive ordering can reflect shared news | claim incremental information only; explicitly prohibit structural-causation language |

## Additional Codex attacks and modifications

### Outer censoring inherited from EXP-001

If EXP-003 kept EXP-001's positive-inner economics gate, X0 would likely remain unobserved, making the required XALL-versus-X0 comparison undefined. The frozen modification is to select the best configuration among candidates with at least 20 inner nonoverlapping actions even if inner economics are negative. This produces an honest outer comparator. XALL still must pass every outer economic gate. This is a prospective EXP-003 rule, not an EXP-001 rescue.

### Sample-support confounding

Allowing X0 to operate while an external source is stale would give X0 and XALL different decision universes. All tracks now use the exact common-support mask requiring valid X0, Binance Spot, and Bybit histories. Source outages reduce every track equally.

### Age versus feature horizon

A recent current book alone is insufficient after a gap. Return anchors and realized-volatility paths must share the current continuity segment. This means a new snapshot after an outage does not instantly validate a 3 s feature.

### Total-PnL comparison

Expectancy alone could improve while trade selection collapses. XALL must beat X0 in both expectancy and total PnL, have at least 100 nonoverlapping actions, and pass hour/fold concentration controls.

### Diagnostic multiplicity

The 250 ms delay, 1,000 ms delay, timestamp permutation, sign placebo, 60 s time placebo, source dropout, and future canary are named in advance. None may change the primary verdict. If diagnostics reveal a causal-pipeline flaw, the correct action is invalidation or a new experiment ID—not choosing a favorable diagnostic.

## No-rescue rules

After the frozen commit, none of the following may be changed under `CODEX-EXP-003`:

- sources, symbols, dates, or representation;
- 500 ms primary delay, 2 s age/gap limits, or 250 ms target reaction;
- feature list or amount normalization;
- X0/X1/X2/XALL definitions or common support;
- horizons, C values, thresholds, label, calibration, or nonoverlap;
- 8/12 bp costs or pass gates;
- model capacity; or
- the role of any diagnostic.

No single-source success, 250 ms success, 1,000 ms result, canary result, lower cost, midpoint result, relaxed coverage, alternate representation, or post-hoc latency correction can rescue XALL primary failure.

## Verdict

**PROCEED TO PRE-SCORE FREEZE**, with the timestamp-claim limitation made inseparable from the result.

The remaining clock/topology uncertainty prevents a universal causal or deployment claim, but it does not make a conservative collector-arrival experiment meaningless. The question is now precisely bounded, the dangerous timestamp channels are technically prohibited, and a failure remains fully informative. External market data must not be acquired until the exact code/docs commit is published and reviewed.

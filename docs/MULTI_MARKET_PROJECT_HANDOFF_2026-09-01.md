# Multi-Market Codex Lab — Project Handoff

Date: 2026-09-01
Status: Active personal quantitative-trading R&D project
Repository: EmadHammamiLoopa/Multi-Market-Codex-Lab
Current branch: research/dev030-p1-label-feasibility
Current DEV030-P1 implementation commit: 118d2049bb5061ef3adfdfc305ad8b63a9d52601
Parent first-passage commit: 024fdbe9be36db73ae7ac7f2f746a05f3f5a88a0

---

## 1. Governing project philosophy

This is a personal trading engineering/R&D project, not an academic paper.

The objective is to build a system that may eventually support economically useful short-horizon trading while avoiding self-deception, leakage, accidental reruns, and false profitability claims.

For every new design:
- review prior successes and failures,
- inspect existing code before claiming a feature or idea is new,
- use public research and published code when useful,
- iterate freely on already-consumed development data,
- preserve enough untouched forward data to test generalization,
- optimize eventual executable net expectancy rather than headline predictive metrics.

Historical frozen experiment evidence is immutable:
- consumed stays consumed,
- prior PASS/FAIL/INVALID labels are never rewritten,
- prior frozen one-shot experiments are never silently rerun under the same ID,
- frozen artifacts and their hashes remain read-only.

---

## 2. Current research question

Current question:

Can causal sequential microstructure signals, conditioned on periods of elevated executable opportunity, predict which trade direction reaches an economically meaningful executable return barrier first, with enough stability to support profitable short-horizon trading after realistic costs?

Operational chain:

Opportunity -> Direction -> First executable barrier -> Cost-adjusted edge -> Trade / Abstain -> Net expectancy

The project now explicitly separates:
1. opportunity ranking,
2. direction / first-passage outcome,
3. economic viability,
4. trade versus abstain.

A useful opportunity ranker is not automatically a direction model.
A useful direction model is not automatically profitable.
A label-feasibility audit is not a PnL backtest.

---

## 3. Frozen history and lessons

### EXP002
Passive RiskAverse failed economically.
Approximate expectancy: -6.988 bps/fill.
Total approximately -$98.58.
Gross expectancy was negative.

Lesson: execution economics can invalidate apparently useful signals.

### EXP003
Cross-venue information at 500 ms did not improve economics.

### EXP004-P1
Official frozen result: FAIL.
However ranking evidence was useful:
- AUC ~0.66996
- AP ~0.34194
- AP/prevalence ~1.696x
- top-decile lift ~2.135x
- all five outer folds had AUC > .55 and lift > 1

Lesson: volatility/opportunity ranking remained promising.

### EXP011 / EXP015
BTC options trade-flow and segmented options-flow variants did not provide reliable incremental timing information.

Lesson: do not blindly reintroduce options segmentation.

### EXP019
Official frozen result: FAIL under its gates.
Aug-01 rv_30m_bps ranking was very strong:
- AUC 0.9685934489
- AP 0.32042023
- AP/prevalence about 29.88x
- top-decile lift about 9.3267x

The old placebo design was flawed.

### EXP020 diagnostic
Important clarification:
- old training-label placebo preserved ordering almost exactly,
- proper within-test-day feature permutation degraded AUC toward 0.50,
- pooled real AUC about 0.64895,
- permutation q95 about 0.56739,
- large train/forward prevalence shift existed.

Lesson: ranking/timing information was real, but absolute probability was unstable.

### EXP021
Calibration rescue did not help.
Intercept/Platt preserved ranking but worsened Brier/logloss.

Lesson: separate ranking from calibration.

### EXP024-P1
Frozen PASS:
PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED

Artifact:
evidence/codex/exp024_p1_fresh_prospective_ranking_confirmation/PROSPECTIVE_RANKING_CONFIRMATION.json

Artifact SHA256:
0fda20d127e51e8ad792c6b949889f88b59e75ab98b437fd04ead285970e5c10

Prospective Aug-30 results:
- n 1399
- positives 93
- prevalence 0.0664760543
- AUC 0.7994368424
- AP 0.2979752230
- AP/prevalence 4.48244x
- top-decile lift 2.90115x
- top-decile precision 0.192857
- temporal-null AUC q95 0.684936
- AUC p 0.043478
- AP q95 0.115398
- AP p 0.021739

Interpretation:
prospective dense 60-second opportunity ranking was validated.
It did not validate direction, execution, or PnL.

### EXP026
Frozen FAIL:
FAIL_DIRECTION_EXECUTION_PIPELINE_NOT_READY

Reason:
a validation fold had zero executed trades.

### EXP028
Frozen FAIL/CLOSED:
FAIL_ABSTENTION_AWARE_DIRECTION_PIPELINE_NOT_READY

Reason:
active fold count 2 < required 3.
The active folds were still net-negative at 14 bp.

### Phase0D / earlier direction attempts
Several direction approaches failed or were unstable:
- fixed terminal signed-return direction,
- flow-only direction,
- longer-horizon selection,
- Ridge futures-state,
- XGBoost direction,
- dynamic execution variants.

Lesson:
the strongest evidence remains opportunity ranking, not direction.

### EXP029
Frozen result:
FAIL_CAUSAL_RANK_OPPORTUNITY_POLICY_NOT_READY

Artifact:
evidence/codex/exp029_p0_causal_rank_opportunity_readiness/HISTORICAL_SELECTION.json

Frozen artifact SHA256:
86a5c29c977ee325dc37d3a3c0d2f9b3366360fcf46734785fd25fa45f1a75ee

Key results:
- pooled n 5596
- positives 803
- prevalence 0.14349535
- AUC 0.6386203261
- AP 0.2473238636
- AP/prevalence 1.723567x
- causal eligible fraction 0.09042173
- 506 signals
- precision 0.30434783
- lift 2.12095945
- temporal-null AUC p 0.06521739: failed <= .05 gate
- AP p 0.04347826: passed

Interpretation:
useful rank/gating evidence, but the strict frozen protocol failed.
Never relabel EXP029.

---

## 4. Why DEV030 exists

Current hypothesis:

Direction may live in temporal sequence/event-time dynamics plus first-passage outcome, rather than in a single aggregated row predicting terminal signed return.

Instead of predicting only return at t + H, DEV030 asks:

After realistic entry latency, which executable side reaches an economic barrier first?

Labels:
- LONG_FIRST
- SHORT_FIRST
- NONE

This target is closer to a tradable decision.

---

## 5. Frozen DEV030 first-passage engine

File:
src/multimarket/dev030_first_passage.py

Commit:
024fdbe9be36db73ae7ac7f2f746a05f3f5a88a0

Original source SHA256:
33dbbb53dfe10cfa859037fa2a89d05010f7950e3ec74e51422135ec585d0bc7

Test file:
tests/test_dev030_first_passage.py

Original test SHA256:
f6ef31a825ffef7bfa251f6cb4ff88f5020fd64ce89753f439a72a46a6c632b0

Focused test result:
26 passed, 17 subtests passed, 0 failed.

Semantics:
- grid 250 ms
- latency exactly 250 ms
- LONG entry uses ask; future liquidation uses bid
- SHORT entry uses bid; future cover uses ask
- exact timestamps/path only
- no interpolation/fill
- full-path quote validity
- NONE only for a complete valid no-touch path
- same-row dual first touch is invalid, not NONE
- invalid target uses label null and target_valid false
- MFE/MAE stored as non-negative magnitudes

Same-row ambiguity schema:
- label = null
- target_valid = false
- invalid_reason = same_row_ambiguous
- same_row_ambiguous = true

---

## 6. DEV030-P1 purpose

DEV030-P1 is a label-only feasibility audit.

It must answer:
Which first-passage horizon/barrier geometries have enough:
- valid support,
- directional touches,
- minority-direction support,
- cross-day persistence,
- direction balance,
- plausible gross distance relative to simple cost references,
to justify later sequence-model development?

No predictive model is fitted in P1.
No PnL claim is made.

---

## 7. DEV030-P1 target grid

Horizons:
- 10 s
- 30 s
- 60 s
- 120 s
- 300 s
- 600 s

Barriers:
- 4 bp
- 8 bp
- 12 bp
- 16 bp
- 24 bp
- 36 bp

Total:
36 geometries.

Decision cadence:
60 seconds.

Latency:
250 ms.

No opportunity threshold conditioning in P1.
No model fitting in P1.
No PnL backtest in P1.

---

## 8. Authorized DEV030-P1 development data

Only the consumed Jan-Jul 2026 BTCUSDT Phase0DL finalized 250 ms files.

Root:
 /home/emadh/Multi-Market/evidence/v23/phase0dl_features250/BTCUSDT/

Frozen expected hashes:

January:
ab0c61fe9a7517cf97388300e6adb18248a37a7977aac8455a10c02b7906de98

February:
33e56c6b5b02ec124bf3a21dbed27fc8705fc572cb7fed9ff73876de87c2978e

March corrected manifest:
076067a4731047dd992004d936d962567c1d7ceed864bb6e778db05bc8c59420

April:
a803fbb8d68f4173551be4c2cccf9fe03f25d86dc6e00469c4a5ab635ade2307

May:
36015c5954d820d8b2f0505ecab9fdc96f40136247d1270365c9ef81312de2e3

June:
5e73f8dc355e3dfcceda649525b4d067ccb74d0259992a287161a71375105535

July:
aadf264ba38eac4563ebab7fd2da22b300d82752343ccd30b19809c70cd39012

March provenance correction:
The originally supplied March digest was only 62 hexadecimal characters.
System sha256sum and independent chunked Python hashlib both confirmed the corrected 64-character digest above.
The CSV itself was not modified.

All seven byte-level hashes were rechecked and matched 7/7 before the P1 implementation commit.

---

## 9. DEV030-P1 Phase A final state

Branch:
research/dev030-p1-label-feasibility

Implementation commit:
118d2049bb5061ef3adfdfc305ad8b63a9d52601

Files committed:
- src/multimarket/dev030_label_feasibility.py
- tests/test_dev030_label_feasibility.py

Source SHA256:
62f71a14ba813f3f974d1cca8c5e6b37bd4bd3e9cc381f55cc02f900825536ce

Test SHA256:
da8cf6a24d765d29a0714d525c6eb8ea4c38271e2119f5ee8200c5382e17450f

EXP029 artifact SHA256:
86a5c29c977ee325dc37d3a3c0d2f9b3366360fcf46734785fd25fa45f1a75ee

Final tests:
- label feasibility: 35 passed, 0 failed, 13 subtests passed
- frozen first-passage: 26 passed, 0 failed, 17 subtests passed
- only read-only pytest-cache warnings
- git diff --check passed
- Jan-Jul hashes: 7/7 verified

Phase-A guards:
- Jan-Jul analytically opened = NO
- Aug-30 analytically opened for DEV030 = NO
- Sep-01+ analytically opened = NO
- real audit = NO
- audit artifact = NO
- model fit = NO
- direction model = NO
- PnL backtest = NO

---

## 10. DEV030-P1 support classification

Support classes are separate from cost plausibility.

ROBUST_SUPPORT:
- valid fraction >= 0.95
- directional touches >= 150
- minority direction >= 50
- touch days >= 6
- both-direction days >= 5

USABLE_SUPPORT:
- valid fraction >= 0.90
- directional touches >= 75
- minority direction >= 25
- touch days >= 5

THIN_SUPPORT:
- directional touches >= 25 but below usable thresholds

NOT_USABLE:
- directional touches < 25
- or material validity failure

These are transparent development heuristics, not scientific significance claims.

---

## 11. Cost plausibility classification

COST_CHALLENGED:
barrier <= 8 bp

POSITIVE_AFTER_8_ONLY:
barrier > 8 and <= 12 bp

POSITIVE_AFTER_12:
barrier > 12 bp

Descriptive fields:
- margin_after_8bps = barrier - 8
- margin_after_12bps = barrier - 12

These are gross barrier-minus-reference calculations only.
They are not realized returns or profitability estimates.
Do not double-subtract spread if the first-passage executable path already embeds bid/ask execution semantics.

---

## 12. Advisory shortlist principles

The P1 shortlist must not be dominated by tiny barriers simply because they produce many labels.

Ranking/selection should account for:
- support class,
- cost class diversity,
- cross-day persistence,
- direction balance,
- median touch time,
- minority-direction support,
- total support.

Maximum shortlist target:
about six geometries.

No final target should be selected automatically from P1 alone.

---

## 13. Next immediate step: DEV030-P1 Phase B

Phase B should run only from the committed P1 implementation.

Before running:
- update the local worktree to the latest branch HEAD,
- verify clean tracked tree,
- verify source/test/design/first-passage provenance,
- verify EXP029 frozen SHA,
- verify exact Jan-Jul file hashes,
- verify output directory does not already exist.

Then run the real label-only Jan-Jul audit.

Phase B may:
- analytically open exactly the authorized Jan-Jul files,
- compute labels for all 36 geometries,
- produce per-day and pooled metrics,
- classify support,
- report cost plausibility,
- produce advisory shortlist/discards,
- create fresh non-overwriting JSON/Markdown audit artifacts.

Phase B must not:
- open Aug-30,
- open Sep-01+,
- fit a model,
- optimize opportunity threshold,
- train direction model,
- run PnL,
- claim profitability,
- use leverage.

After Phase B:
review the support geometry results before choosing sequence-model targets.

---

## 14. DEV030 model plan after P1

If P1 yields usable first-passage geometries, model sequence information.

Model ladder:
1. heuristic / linear baseline
2. boosting on engineered sequence summaries
3. small MLP
4. TCN / 1D-CNN
5. TLOB / Transformer only if simpler models fail to capture incremental value

Do not jump directly to a Transformer.

Candidate causal sequence windows:
- 8 s
- 16 s
- 32 s
- 60 s

Historical 250 ms information already includes or has tested variants of:
- spread
- microprice-minus-mid
- OBI L1/L5/L10
- OFI
- MLOFI
- trade quantity/count imbalance
- bid/ask depth
- replenishment/depletion
- short returns
- changes/interactions

Do not merely re-add OFI/MLOFI and call it a new direction design.

Potential new value:
- explicit temporal sequences,
- event-time dynamics,
- first-passage target,
- causal summaries,
- sign persistence,
- slopes,
- acceleration,
- EMA,
- ranks/z-scores,
- optional past-only cross-asset alignment.

---

## 15. Later validation plan

Use consumed Jan-Jul for development selection.

Chronological development folds:
- Jan-Mar -> Apr
- Jan-Apr -> May
- Jan-May -> Jun
- Jan-Jun -> Jul

No random shuffle.

Purging/embargo should account for full information interval:
[t - lookback, t + 250ms + H]

Later predictive metrics:
- macro-F1
- balanced accuracy
- actionable precision
- per-class support
- calibration only if useful

Later economic metrics:
- net expectancy
- trade count/frequency
- turnover
- drawdown
- hit rate
- cost sensitivity
- capital scaling
- no leverage initially

---

## 16. Holdout policy

Aug-30:
already used in EXP024 prospective opportunity validation.
Do not reopen it for DEV030 development.

Sep-01+:
currently preserved as the best fresh forward holdout.

Critical rule:
Holdout consumption is defined by market time/events, not storage source.

If Sep-01 data from abundant-love is opened analytically for target/feature/model decisions, then Sep-01 in the bucket is also consumed because it represents the same market period.

However:
SAVE / COPY / HASH / ARCHIVE is not analytical consumption.

Storage-only operations do not consume holdout status.

---

## 17. EXP025 abundant-love collector

Purpose:
independent/redundant continuous BTCUSDT, ETHUSDT, SOLUSDT Binance USD-M combined bookTicker acquisition.

Important implementation behavior:
- writes daily gzip files,
- refuses append/resume/overwrite when the daily file already exists,
- therefore a mid-day restart after a crash can fail if that day's file remains.

2026-09-01 incident:
- mounted Railway volume filled,
- writer failed with OSError Errno 28: No space left on device,
- restart then failed because Sep-01 daily files already existed,
- the user wiped only the abundant-love volume,
- abundant-love returned Online.

The wiped pre-crash local EXP025 files are no longer present on that volume.

Do not modify EXP025 as part of DEV030 commits.

---

## 18. EXP027 archive collector

Service:
exp027-archive

Purpose:
independent long-term bucket-backed acquisition.

Bucket:
market-raw-archive

Observed during the EXP025 crash:
- EXP027 remained Online,
- BTCUSDT had hourly objects at least 00-07 UTC,
- ETHUSDT had hourly objects at least 00-07 UTC,
- SOLUSDT had hourly objects at least 00-07 UTC.

Therefore the archive continued independently while abundant-love was down.

Important:
EXP027 bucket objects are not assumed to be byte-for-byte copies of EXP025 files.
They are an independent acquisition of the same market.

Do not disturb EXP027 while running DEV030.

---

## 19. Storage architecture and retention plan

Long-term authoritative raw storage:
EXP027 -> market-raw-archive bucket

Short-term hot/redundant buffer:
EXP025 abundant-love -> Railway volume

Routine full PC backup is not recommended.
It adds storage burden with limited benefit.
A PC copy is reasonable only for selected incidents/debugging.

Planned separate retention task:
1. write current UTC day locally,
2. after a day completes, verify remote EXP027 hourly coverage for BTC/ETH/SOL,
3. verify expected objects are present and non-empty,
4. record simple integrity/provenance metadata,
5. only after remote verification, delete old completed EXP025 local data,
6. never delete the active current-day files,
7. maintain enough headroom to avoid another 100% volume event,
8. never delete bucket objects as part of local retention.

Because local volume is small relative to stream rate, keep only a short buffer.
Prefer cleanup before roughly 75-80% usage rather than waiting for ENOSPC.

If the daily-file design itself creates unsafe restart behavior, consider later changing EXP025 to shorter rollover segments, but only in a separate DevOps branch/task.

---

## 20. Bucket versus volume

Do not confuse:
- Railway Bucket = object storage for long-term archive
- Railway Volume = mounted service filesystem

The Sep-01 crash was caused by the abundant-love volume, not the market-raw-archive bucket.

The bucket UI showed about 5.1 GB stored during the discussion.
That was current usage, not evidence that the bucket limit was 5 GB.

Recheck Railway current documentation before relying on plan limits/pricing in future decisions.

---

## 21. External research/code directions already considered

Previously reviewed ideas include:
- Cont/Kukanov/Stoikov OFI
- Deep OFI
- TLOB / temporal-feature attention
- Stoikov microprice
- queue imbalance literature
- cross-impact OFI
- multi-level OFI
- crypto submissions/cancellations/order-flow impact
- triple-barrier/meta-labeling concepts
- hftbacktest for later L2/L3 execution simulation
- Binance USD-M aggregate trade / partial depth / diff-depth documentation

Use public research/code to answer engineering questions.
Do not copy architectures blindly.
Require incremental evidence over simpler models.

---

## 22. Critical do-not list

Do not:
- rewrite frozen historical outcomes,
- rerun frozen one-shots under their original IDs,
- modify EXP029 frozen artifact,
- call EXP029 a pass,
- call P1 label support a profitability result,
- claim opportunity ranking proves direction,
- open Aug-30 for DEV030,
- open Sep-01+ before intentionally consuming that holdout,
- mix collector maintenance into DEV030 scientific commits,
- use leverage before a stable net-positive strategy exists,
- jump directly to a large Transformer,
- delete local EXP025 data before remote archive verification,
- assume EXP025 and EXP027 files are byte-identical.

---

## 23. Authoritative current values

DEV030-P1 implementation commit:
118d2049bb5061ef3adfdfc305ad8b63a9d52601

DEV030 first-passage parent commit:
024fdbe9be36db73ae7ac7f2f746a05f3f5a88a0

DEV030-P1 source SHA256:
62f71a14ba813f3f974d1cca8c5e6b37bd4bd3e9cc381f55cc02f900825536ce

DEV030-P1 test SHA256:
da8cf6a24d765d29a0714d525c6eb8ea4c38271e2119f5ee8200c5382e17450f

EXP029 frozen artifact SHA256:
86a5c29c977ee325dc37d3a3c0d2f9b3366360fcf46734785fd25fa45f1a75ee

Corrected March input SHA256:
076067a4731047dd992004d936d962567c1d7ceed864bb6e778db05bc8c59420

Current branch:
research/dev030-p1-label-feasibility

---

## 24. New-chat / new-agent continuation instruction

Read this file completely before changing the project.

Treat the following as authoritative unless superseded by a later committed handoff:
- frozen experiment labels and artifacts,
- EXP029 identity,
- first-passage semantics,
- P1 geometry grid and support/cost rules,
- Sep-01+ holdout policy,
- EXP025/EXP027 separation,
- retention architecture.

Before every new design:
1. review prior wins/failures,
2. inspect existing implementation,
3. use Jan-Jul consumed data for development,
4. keep Sep-01+ untouched until explicitly consumed,
5. optimize eventual executable net expectancy, not only predictive metrics,
6. preserve provenance and avoid leakage,
7. separate research-model changes from infrastructure/retention changes.

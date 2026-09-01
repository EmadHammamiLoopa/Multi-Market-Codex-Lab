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

---

## 25. DEV030-P1 Phase-B v1 operational failure and hardening

Phase-B v1 was invoked exactly once from the verified P1 implementation lineage and analytically processed the authorized Jan-Jul consumed-development inputs.

It failed after analytical computation but before output-directory/artifact creation because the execution environment returned:

`OSError: [Errno 30] Read-only file system`

for:
`/mnt/c/Users/emadh/Downloads/market-exp026/evidence/codex/dev030_p1_label_feasibility_v1`

Permanent record:
- v1 status = `STOPPED_OPERATIONAL_FAILURE_NO_ARTIFACT`
- this is NOT a scientific FAIL
- no JSON artifact was created
- no Markdown artifact was created
- no scientific metrics may be reconstructed or inferred from transient process state
- Jan-Jul were analytically opened during v1
- Aug-30 remained closed for DEV030
- Sep-01+ remained closed
- no model fit, direction model, or PnL backtest ran

A fail-fast output-parent preflight was then added so output writability is checked before `verify_input_manifest()` and before any `_load_day()`.

Hardening behavior:
- output directory must be absent
- parent must exist and be a directory
- exclusive per-output probe file is created with `O_EXCL`
- probe file is written and fsynced
- parent-directory fsync is attempted
- probe is deleted and cleanup verified
- stale probe is never overwritten
- operational write failures raise `AuditProtocolError`
- no market data is opened when this preflight fails

Hardening tests:
- DEV030-P1 feasibility suite: 40 passed, 0 failed
- frozen first-passage suite: 26 passed, 0 failed
- git diff --check passed

Hardening commit:
`7d817ca402a6244d027c4730abe0313822f0aba4`

Hardening source SHA256:
`b754e3584a1dffacf2cb4e98bc1cfdba511c8e0d306eaf1d6841353d529af330`

Hardening test SHA256:
`0e8866f808fc8373f167c0a03059b3e0f6f49882b52b0796924dd68dd37fcc25`

The actual intended `/mnt/c/.../evidence/codex` parent was probed with the new helper and correctly rejected before any analytical access:
- ACTUAL_PARENT_PREFLIGHT = FAIL
- errno = 30 / read-only filesystem
- output directory remained absent
- probe file did not remain
- no manifest verification, loader, or audit was run during this check

Therefore the next Phase-B attempt must be a controlled recovery named v2, using a separately verified writable output parent, preferably a Linux-native path. Do not reuse v1.

Before v2:
1. verify local branch includes hardening commit `7d817ca...`
2. verify worktree clean
3. probe candidate output parent only, without market-data access
4. require probe PASS
5. use a fresh v2 output directory
6. preserve v1 permanently as operational failure/no artifact

Candidate output path to test:
`/home/emadh/Multi-Market/evidence/dev030_p1_label_feasibility_v2`

Do not assume it is writable; probe it first.



---

## 26. DEV030-P1 controlled recovery v2 output preflight

After the hardening commit was pushed, the handoff-only remote update was fast-forwarded locally.

Verified local state before the v2 output-path probe:
- local HEAD = `51a28efa48e3415cd1a4a41cae55d1b180367bc4`
- hardening commit `7d817ca402a6244d027c4730abe0313822f0aba4` is in ancestry
- only change after hardening was the handoff document
- git status = CLEAN

Candidate v2 output path:
`/home/emadh/Multi-Market/evidence/dev030_p1_label_feasibility_v2`

The actual Linux-native output parent was tested using ONLY:
- `_assert_output_absent(output_directory)`
- `_assert_output_parent_writable(output_directory)`

No `verify_input_manifest()`, `_load_day()`, market-data access, audit run, or model training occurred during this test.

Result:
- V2_OUTPUT_ALREADY_EXISTS = False
- V2_PARENT_PREFLIGHT = PASS
- V2_PROBE_EXISTS_AFTER = False
- ERROR_TYPE = None
- ERROR_MESSAGE = None

This means the Linux-native parent has successfully demonstrated the exact create/write/fsync/delete/cleanup behavior required by the hardened audit before analytical loading.

### Next authorized action

The next scientific action is a controlled DEV030-P1 Phase-B recovery run named v2.

Rules for v2:
- never reuse the failed v1 output path
- use `/home/emadh/Multi-Market/evidence/dev030_p1_label_feasibility_v2`
- sync local branch to the latest documentation-only descendant first
- verify hardening commit remains in ancestry
- verify clean worktree
- re-verify frozen implementation/provenance identities and all seven Jan-Jul hashes before loading
- require the v2 output directory to remain absent before the run
- run the committed label-feasibility CLI exactly once for this recovery attempt
- Jan-Jul are authorized consumed development data
- do not open Aug-30
- do not open Sep-01 or later
- do not open abundant-love or EXP027 bucket data
- do not train any model
- do not optimize opportunity thresholds
- do not run PnL or capital simulation
- do not modify scientific geometry/first-passage semantics

Permanent provenance:
- Phase-B v1 = operational failure / no artifact / no scientific result
- Phase-B v2 = pending controlled recovery on a preflight-verified writable Linux-native output path


---

## 27. DEV030-P1 Phase-B v2 controlled recovery completed

The controlled v2 recovery was invoked exactly once after:
- syncing to the documentation-only descendant of the hardening commit,
- verifying the hardening commit remained in ancestry,
- verifying all frozen provenance identities,
- re-verifying the seven authorized Jan-Jul input hashes,
- re-running the hardened Linux-native output-parent preflight successfully.

Exact v2 output directory:
`/home/emadh/Multi-Market/evidence/dev030_p1_label_feasibility_v2`

The process completed successfully and returned:

`status = LABEL_FEASIBILITY_AUDIT_COMPLETE`

Artifact hashes reported by the committed CLI:
- audit JSON SHA256 = `3e2bdc7447290737df7f87f0e3eebce70be4e2071a54753fdc055b484f9f8a2a`
- audit summary SHA256 = `ab6db2cc8175048a0c8cc20d23f6b288180ea569f886c3bde9417f1ff944099c`

Interpretation at this point:
- v2 operational recovery succeeded
- valid immutable artifacts now exist
- v1 remains permanently recorded as operational failure/no artifact
- v1 must never be relabeled or reused
- do not rerun v2
- do not infer scientific conclusions until the artifact contents are reviewed and reported
- no model training, PnL backtest, Aug-30 opening, or Sep-01+ opening is implied by this completion status

Next step:
inspect and report the v2 JSON/Markdown artifacts, including the 36 geometry support classes, advisory shortlist, obvious discards, and requested pooled diagnostics, then stop for human review before any DEV030-P2/modeling work.


---

## 28. DEV030-P1 Phase-B v2 scientific review

The existing v2 artifacts were reviewed read-only. The audit itself was NOT rerun.

Phase-B v2 status:
`LABEL_FEASIBILITY_AUDIT_COMPLETE`

Execution head recorded by the artifact:
`794e95b816481e0bf74d29e100a1bab113826594`

Output directory:
`/home/emadh/Multi-Market/evidence/dev030_p1_label_feasibility_v2`

Artifacts:
- JSON: `LABEL_FEASIBILITY_AUDIT.json`
- Markdown: `LABEL_FEASIBILITY_SUMMARY.md`

Artifact SHA256 values:
- JSON = `3e2bdc7447290737df7f87f0e3eebce70be4e2071a54753fdc055b484f9f8a2a`
- summary = `ab6db2cc8175048a0c8cc20d23f6b288180ea569f886c3bde9417f1ff944099c`

Frozen identities remained verified:
- hardening source SHA256 = `b754e3584a1dffacf2cb4e98bc1cfdba511c8e0d306eaf1d6841353d529af330`
- hardening test SHA256 = `0e8866f808fc8373f167c0a03059b3e0f6f49882b52b0796924dd68dd37fcc25`
- first-passage source SHA256 = `33dbbb53dfe10cfa859037fa2a89d05010f7950e3ec74e51422135ec585d0bc7`
- design document SHA256 = `0c1a75bf4023c122538eac90f73b5c22e9d93239798a0952ec8bcb9b6e3ecccc`
- EXP029 frozen artifact SHA256 = `86a5c29c977ee325dc37d3a3c0d2f9b3366360fcf46734785fd25fa45f1a75ee`
- Jan-Jul hashes = 7/7 verified

### Support results

Total geometries: 36
- ROBUST_SUPPORT = 29
- USABLE_SUPPORT = 1
- THIN_SUPPORT = 3
- NOT_USABLE = 3

This is strong evidence that the first-passage LABEL FRAMEWORK is feasible on consumed Jan-Jul development data. It does NOT yet prove that direction is predictable, and it does NOT prove profitability.

### Advisory shortlist reported by the audit

1. 120s / 16 bp
- valid fraction 0.9979166667
- directional touches 1374
- directional touch fraction 0.1365940948
- LONG 684 / SHORT 690
- balance ratio 0.9913043478
- 7/7 days with both directions
- median first touch 66.25 s
- ROBUST_SUPPORT
- POSITIVE_AFTER_12
- margin after 8 bp = +8 bp
- margin after 12 bp = +4 bp

2. 300s / 12 bp
- directional touches 4932
- touch fraction 0.4913329348
- LONG 2429 / SHORT 2503
- balance ratio 0.9704354774
- 7/7 days with both directions
- median first touch 121.5 s
- ROBUST_SUPPORT
- POSITIVE_AFTER_8_ONLY
- margin after 12 bp = 0 bp

3. 60s / 8 bp
- directional touches 2460
- touch fraction 0.2443870455
- LONG 1223 / SHORT 1237
- balance ratio 0.9886822959
- median first touch 27.375 s
- ROBUST_SUPPORT
- COST_CHALLENGED
- margin after 8 bp = 0 bp
- margin after 12 bp = -4 bp

4. 300s / 24 bp
- directional touches 1704
- touch fraction 0.1697549313
- LONG 848 / SHORT 856
- balance ratio 0.9906542056
- 7/7 days with both directions
- median first touch 165.125 s
- ROBUST_SUPPORT
- POSITIVE_AFTER_12
- margin after 8 bp = +16 bp
- margin after 12 bp = +12 bp

5. 600s / 12 bp
- directional touches 6961
- touch fraction 0.6958912326
- LONG 3425 / SHORT 3536
- balance ratio 0.9686085973
- median first touch 183.5 s
- ROBUST_SUPPORT
- POSITIVE_AFTER_8_ONLY
- margin after 12 bp = 0 bp

6. 120s / 8 bp
- directional touches 4357
- touch fraction 0.4331444478
- LONG 2191 / SHORT 2166
- balance ratio 0.9885896851
- median first touch 51.5 s
- ROBUST_SUPPORT
- COST_CHALLENGED
- margin after 8 bp = 0 bp
- margin after 12 bp = -4 bp

### Obvious discards

- 30s / 36 bp: NOT_USABLE, only 18 directional touches
- 10s / 24 bp: NOT_USABLE, only 12 directional touches
- 10s / 36 bp: NOT_USABLE, only 4 directional touches

Highest invalid fraction geometry:
- 600s / 24 bp
- invalid fraction 0.0076388889
- day_boundary_crossing 70
- entry_quote_invalid 7

Most balanced directional geometry:
- 120s / 16 bp
- balance ratio 0.9913043478

Pooled median first-touch range:
- minimum 5.0 s
- maximum 327.75 s

### Recommended DEV030-P2 target strategy

Primary economic targets:
1. `120s / 16 bp`
2. `300s / 24 bp`

Why:
- both are ROBUST
- both directions are almost perfectly balanced
- both persist across all seven days
- both retain positive gross distance after the conservative 12 bp reference
- 120/16 is faster and moderately frequent
- 300/24 offers much stronger cost headroom while retaining substantial support

Secondary learnability/control targets:
3. `300s / 12 bp`
4. `600s / 12 bp`

Why:
- much higher label support
- useful to test whether sequence direction is learnable when the target is easier
- but zero margin after the 12 bp reference means they should not be treated as primary economic trading targets

The 8 bp targets should be retained only as diagnostic/learnability controls, not as primary trading candidates, because they are cost-challenged under the current references.

### Interpretation

DEV030-P1 strongly supports continuing with the first-passage formulation at the LABEL-FEASIBILITY level.

The next question is no longer "do we have enough labels?" for most geometries. The next question is:
Can causal sequence features predict LONG_FIRST versus SHORT_FIRST (and/or actionable touch versus NONE) out of sample with enough stability and economic margin?

Proceed to DEV030-P2 only after preserving the v2 artifact identities and design choices. Do not open Aug-30 or Sep-01+ during P2 development. Use consumed Jan-Jul chronological folds.

Permanent guards remain:
- Jan-Jul analytically opened = YES
- Aug-30 analytically opened = NO
- Sep-01+ analytically opened = NO
- model fit run in P1 = NO
- direction model run in P1 = NO
- PnL backtest in P1 = NO
- EXP029 rerun = NO
- EXP025 modified = NO
- EXP027 modified = NO


---

## 29. DEV030-P2 design frozen and pushed

DEV030-P2 sequence-direction design is now frozen on a dedicated branch.

Branch:
`research/dev030-p2-sequence-design`

Parent P1 head:
`20e4ab1aa3b513d763ed9a1a141d095ee522ee0d`

P2 design commit:
`160a07bd34c377f10fab73ca92f040fa97c97df2`

Design file:
`docs/DEV030_P2_SEQUENCE_DIRECTION_DESIGN.md`

Design SHA256:
`be22346db59dbb4b42e2ab269d6d943d6e30e5fcb50d2b38d8decdfa3c8335d1`

Design line count:
870

Remote/local identity after push:
- local HEAD = `160a07bd34c377f10fab73ca92f040fa97c97df2`
- remote HEAD = `160a07bd34c377f10fab73ca92f040fa97c97df2`
- push status = SUCCESS
- git status = clean

The design freezes:
- primary oracle-touch task `DIRECTION_GIVEN_TOUCH`
- later `TOUCH_VS_NONE` deployable component
- primary economic targets `120s/16bp` and `300s/24bp`
- controls `300s/12bp` and `60s/8bp`
- sequence windows `8/16/32/60s`
- exact Phase0DL feature blocks and causal information intervals
- S0 matched snapshot baseline versus S1 engineered causal sequence summaries
- M0/M1 first campaign; nonlinear/deep models stage-gated
- chronological Jan-Jul folds only
- day-local temporal nulls
- bounded-search trial ledger
- engineering-only promotion label `ELIGIBLE_FOR_NEXT_DEVELOPMENT_STAGE`
- no confirmatory claim before untouched forward evaluation

No model was fit during design.
Jan-Jul were not analytically reopened during design.
Aug-30 remained closed for DEV030.
Sep-01+ remained closed.
No PnL was run.

### Immediate next implementation step

Implement only the pure causal sequence feature engine and synthetic tests first.

Planned first implementation files:
- `src/multimarket/dev030_sequence_features.py`
- `tests/test_dev030_sequence_features.py`

This first implementation must prove:
- exact allowed-feature identity
- exact `[t-W,t]` row causality
- exact block-specific raw-source information interval
- full-window validity
- deterministic 250 ms derived return
- exact S0/S1 summary arithmetic
- exact common-support mechanics
- no filesystem scanning
- no model fitting
- no Jan-Jul analytical opening

Only after this pure feature engine is frozen should a separate task build the Jan-Jul T1 dataset.

---

## 30. Long-term multi-market roadmap

The project is not intended to remain crypto-only.

The reusable architecture should separate:

1. common research/trading core
2. market adapters
3. market-specific validation
4. portfolio/risk allocation

The core should be reused across markets rather than re-running the entire historical EXP001-EXP029 development path for every new instrument.

### Planned market families

Phase A — crypto:
- BTC
- ETH
- SOL

Phase B — highly liquid futures:
- Nasdaq futures: NQ / MNQ
- S&P futures: ES / MES
- Gold futures: GC / MGC
- Crude oil futures: CL / MCL

Phase C — major FX:
- EUR/USD
- GBP/USD
- USD/JPY

Additional markets may be considered only after the reusable core is stable.

Each market adapter should own market-specific semantics such as:
- tick size
- tick value / contract multiplier
- fees
- trading session
- bid/ask conventions
- liquidity/depth assumptions
- latency assumptions
- volatility scale
- market-specific holidays/session gaps

Do not assume BTC barrier values transfer directly to another market. Future cross-market target design should consider volatility/spread-normalized barriers where appropriate.

Multi-market expansion is intended to increase opportunity diversity and reduce concentration in one regime. It does not guarantee profit.

---

## 31. Future news, macro, and event-intelligence layer

After the core market-only direction/economic pipeline is demonstrated, add a separate event-intelligence layer.

Candidate inputs include:
- scheduled macroeconomic releases: CPI, PPI, NFP, unemployment, GDP, PMI, retail sales
- central-bank decisions, statements, minutes, and speeches: Fed/FOMC, ECB, BoE, BoJ, Norges Bank
- energy inventory and supply events: EIA, OPEC/OPEC+
- company/sector releases for equity-index/equity strategies
- exchange notices and market-structure events
- high-quality breaking-news sources
- crypto regulatory/exchange/ETF events
- later optional low-weight social/sentiment inputs

The event layer should prefer structured output such as:
- event type
- source reliability
- novelty
- actual value
- consensus/expected value when applicable
- surprise magnitude
- affected assets
- directional context
- expected horizon
- uncertainty/confidence

Do not reduce the news layer to generic positive/negative sentiment.

The LLM/news component must not have unilateral authority to trade. It should act as context/risk information that can confirm, weaken, or veto a market-derived signal under deterministic rules.

---

## 32. Future autonomous demo-trading agent roadmap

Autonomous execution is a later stage only after predictive direction, deployable composition, economics, and untouched forward validation are established.

Planned progression:

1. market-only research model
2. deployable touch + direction composition
3. executable economics
4. untouched forward confirmation
5. multi-market adapters
6. news/event intelligence
7. shadow agent that records hypothetical decisions without sending orders
8. autonomous demo-account execution
9. only much later, after separate validation, consideration of real-money execution

Suggested agent separation:

- Market Agent: opportunity/direction signals
- News/Event Agent: structured event interpretation
- Risk Agent: deterministic hard constraints and veto
- Execution Agent: order placement/cancellation/management in demo

The Risk Agent has absolute veto authority.

Future hard guards should include at minimum:
- max loss per day
- max trades per hour/day
- max gross/net exposure
- max correlated positions
- max spread
- max slippage
- max position size
- stale-data refusal
- stale-model refusal
- exchange/API-health refusal
- duplicate-order prevention
- kill switch
- position reconciliation
- fail-closed behavior when state is uncertain

No autonomous agent may bypass these deterministic constraints.

The long-term objective is a multi-market system that ranks available opportunities across markets, incorporates event context, applies correlation/risk controls, and selects only the best eligible opportunities rather than forcing activity in every market.


---

## 33. DEV030-P2A pure sequence-feature implementation authorized

The next authorized work is implementation only of the pure causal sequence-feature engine and focused synthetic tests.

Start from the current P2 design lineage:
- P2 design branch: `research/dev030-p2-sequence-design`
- P2 design commit: `160a07bd34c377f10fab73ca92f040fa97c97df2`
- current handoff descendant: this documentation-only commit
- design file: `docs/DEV030_P2_SEQUENCE_DIRECTION_DESIGN.md`
- design SHA256: `be22346db59dbb4b42e2ab269d6d943d6e30e5fcb50d2b38d8decdfa3c8335d1`

Recommended implementation branch:
`research/dev030-p2a-sequence-features`

Authorized implementation files:
- `src/multimarket/dev030_sequence_features.py`
- `tests/test_dev030_sequence_features.py`

This phase must remain a pure in-memory feature/causality implementation task.

It may inspect repository source/schema definitions and existing synthetic-test patterns, but it must NOT:
- analytically open Jan-Jul market CSVs
- open Aug-30
- open Sep-01+
- fit any model
- construct the real Jan-Jul T1 dataset
- run Campaign 1
- run PnL/economics
- modify first-passage semantics
- modify EXP025/EXP027
- add news/event/agent implementation yet

The feature engine must freeze and test:
- exact stored Phase0DL allowed-feature manifest
- exact 250 ms grid assumptions
- exact sequence windows 8/16/32/60 seconds
- representation row interval `[t-W,t]`
- block-specific underlying raw-source interval using exact `L_block`
- deterministic causal 250 ms mid log return
- full-window validity/no imputation
- S0 matched snapshot representation
- S1 exact summaries: last, mean, population std, min, max, last-first, OLS slope, and sign persistence only for frozen signed variables
- exact common-support primitives needed for later S0/S1 comparison
- no future mutation changing an earlier representation
- no filesystem scanning or model dependencies in the pure module

After implementation and synthetic tests pass, stop for human review before committing. The implementation should be committed separately only after review. Real Jan-Jul dataset construction and any model fitting belong to a later, separately authorized phase.


---

## 34. DEV030-P2A pure causal sequence-feature engine frozen and pushed

The reviewed pure sequence-feature implementation is now frozen and pushed.

Branch:
`research/dev030-p2a-sequence-features`

Parent:
`15b29c28f6376c45cb691a15b356c5c35056fafe`

Implementation commit:
`4ffed3434403b5dd0c691cf38a928a20ba52b765`

Committed files:
- `src/multimarket/dev030_sequence_features.py`
- `tests/test_dev030_sequence_features.py`

Frozen SHA256:
- source = `30952d31795d5fd88c9dfd9641a5332b662eeb32f30ec9ac283f8339d26ac11c`
- tests = `676fba5c690e69242da28a47888209c0fad4c2855522396e87bb207b2942e489`

Validation:
- sequence-feature tests = 39 passed
- first-passage regression = 26 passed + 17 subtests
- git diff/check = PASS
- worktree after commit/push = clean
- local HEAD = remote HEAD = `4ffed3434403b5dd0c691cf38a928a20ba52b765`

Frozen implementation facts:
- stored Phase0DL predictor primitives = 43
- total predictor manifest with derived 250 ms mid log return = 44
- naturally signed predictors = 33
- cumulative L_block:
  - PRICE = 250 ms
  - PRICE_BOOK = 250 ms
  - PRICE_BOOK_FLOW = 3 s
  - FULL = 3 s
- frozen sequence windows/row counts:
  - 8 s = 33
  - 16 s = 65
  - 32 s = 129
  - 60 s = 241

P2A guards remained intact:
- Jan-Jul analytically opened for P2A implementation = NO
- Aug-30 opened = NO
- Sep-01+ opened = NO
- real T1 dataset built = NO
- model fit = NO
- Campaign 1 = NO
- PnL = NO
- EXP025/EXP027 modified = NO

### Next authorized stage: DEV030-P2B real T1 dataset construction

The next stage may analytically open ONLY the already-consumed Jan-Jul 2026 BTCUSDT Phase0DL files in order to build deterministic T1 development datasets and fold/support manifests.

This stage must remain dataset construction and validation only. It must NOT fit a model or run Campaign 1.

Recommended branch:
`research/dev030-p2b-direction-dataset`

Planned implementation files:
- `src/multimarket/dev030_direction_dataset.py`
- `tests/test_dev030_direction_dataset.py`

P2B should:
- verify all seven frozen Jan-Jul input hashes before analytical loading
- verify frozen first-passage and sequence-feature source identities
- use only the four frozen P2A geometries: 120/16, 300/24, 300/12, 60/8
- use only frozen 60-second decision timestamps
- construct first-passage labels with the frozen labeler
- map T1 exactly: LONG_FIRST=1, SHORT_FIRST=0, exclude NONE/invalid/same-row
- build deterministic S0/S1 representations for frozen block/window combinations
- preserve native support and exact matched common support
- create the four frozen chronological folds:
  - Jan-Mar -> Apr
  - Jan-Apr -> May
  - Jan-May -> Jun
  - Jan-Jun -> Jul
- enforce complete raw-source information intervals at fold/data boundaries
- record deterministic support hashes/timestamps, class counts, invalid reasons, block/window/target identities, and provenance
- keep outputs JSON-safe and deterministic
- use a fresh writable Linux-native output path after preflight if immutable artifacts are written

P2B must NOT:
- select C
- fit StandardScaler
- fit LogisticRegression or any other model
- compute predictive BA/F1/MCC
- run temporal-label nulls
- choose a winning candidate
- run PnL/economics
- open Aug-30
- open Sep-01+
- touch EXP025/EXP027
- add external/news/cross-market features

P2B should stop for human review after dataset/support validation. Campaign-1 fitting is a separate later authorization.


---

## 35. DEV030-P2B implementation handoff before rate-limit boundary

A local P2B branch has been created from the synchronized P2A handoff head:

`research/dev030-p2b-direction-dataset`

Local branch starting point at creation:
`a831033dade06f7d45b8522a599391d4ea83e72a`

No P2B source patch has been applied yet.
No P2B test file has been created yet.
Jan-Jul have NOT been analytically opened for P2B.
No model, Campaign 1, predictive metric, or PnL has been run.

A reviewed source design for `src/multimarket/dev030_direction_dataset.py` is ready to apply, with two additional fail-closed provenance invariants required before any real Jan-Jul analytical load:

1. Frozen scientific source byte identities must be enforced, not merely recorded:
   - `src/multimarket/dev030_first_passage.py`
     expected SHA256 `33dbbb53dfe10cfa859037fa2a89d05010f7950e3ec74e51422135ec585d0bc7`
   - `src/multimarket/dev030_sequence_features.py`
     expected SHA256 `30952d31795d5fd88c9dfd9641a5332b662eeb32f30ec9ac283f8339d26ac11c`

2. Positional Phase0DL feature order must be proved exactly:
   `SOURCE_FEATURE_ORDER = tuple(L0_NAMES + L1_EXTRA_NAMES + L2_EXTRA_NAMES)`
   must equal `sf.ALLOWED_STORED_FEATURES`.
   A same-length reordered manifest must fail closed with a stable reason such as
   `phase0dl_feature_order_mismatch`.

Required fail-closed load order:
`frozen source SHA -> frozen feature order -> seven Jan-Jul byte hashes -> CSV schemas -> analytical row loader`

The planned source implementation also freezes:
- exactly four targets: 120/16, 300/24, 300/12, 60/8
- exact 60-second decision cadence
- T1 mapping LONG_FIRST=1, SHORT_FIRST=0; NONE/invalid/same-row excluded
- exact S0/S1 reuse through the frozen sequence engine
- exact support hashing with canonical chronological timestamp encoding
- exact four chronological outer folds
- no model/predictive metric/PnL code

Planned synthetic tests must prove:
- correct frozen source identities pass
- either frozen source mismatch prevents header and analytical loader invocation
- Jan-Jul hash mismatch prevents loader invocation
- exact Phase0DL feature order passes
- one-position reorder fails
- same-length reorder cannot silently map into X["L2"]
- all existing frozen dataset/causality/support requirements

Because this handoff commit is being added on the P2A parent branch after local P2B branch creation, before applying the P2B source patch, the local P2B branch should fetch and fast-forward to this documentation-only descendant while still clean.


---

## 36. DEV030-P2B synthetic implementation checkpoint

Local branch: `research/dev030-p2b-direction-dataset`

Parent/head before local P2B files: `a13905631e0816a23d5d7bc822d8bbb5e4f67ff5`

Uncommitted files:
- `src/multimarket/dev030_direction_dataset.py`
- `tests/test_dev030_direction_dataset.py`

Current SHA256:
- source `54e7315a12cac10413ac2017849466eb3d225282e3dcf48484615409680348c9`
- tests `5466594bfc22a8c7e10c782f1d5368b06643e50a21fb6a73e522768f8d308a32`

Validation: P2B synthetic 35 passed; sequence-feature regression 39 passed; first-passage regression 26 passed + 17 subtests; `git diff --check` PASS.

Guards remain: Jan-Jul not analytically opened for P2B; Aug-30 closed; Sep-01+ closed; archive bucket closed; no real T1 dataset; no model; no Campaign 1; no PnL; no commit; no push.

Before commit, add two strengthening tests: (1) full pre-load failure on same-length reordered Phase0DL feature order with header/loader counts remaining zero; (2) non-tautological proof that support SHA depends only on timestamp membership, not irrelevant feature values. Then rerun the three scoped suites and `git diff --check` before freezing P2B.


---

## 37. DEV030-P2B deterministic direction dataset builder frozen and pushed

Branch: `research/dev030-p2b-direction-dataset`

Parent: `2b9fc3588e46699f0f3d41dbc89ae5922588616d`

Frozen P2B implementation commit: `ee2a01b3ec0ab8a327daff90fa894238a9126ec1`

Committed files exactly:
- `src/multimarket/dev030_direction_dataset.py`
- `tests/test_dev030_direction_dataset.py`

Frozen SHA256:
- source = `54e7315a12cac10413ac2017849466eb3d225282e3dcf48484615409680348c9`
- tests = `d0e1a94ca2df0220ad91126f90e6271261fcd1f4a7b9e3311e04987bddf2a175`

Final validation before freeze:
- focused P2B synthetic suite = 36 passed
- frozen sequence-feature regression = 39 passed
- frozen first-passage regression = 26 passed + 17 subtests
- git diff --check = PASS
- remote HEAD = local HEAD = `ee2a01b3ec0ab8a327daff90fa894238a9126ec1`
- git status = clean

Frozen implementation guarantees:
- frozen first-passage source SHA enforced before analytical loading
- frozen sequence-feature source SHA enforced before analytical loading
- exact Phase0DL positional feature-order identity enforced before analytical loading
- all seven authorized Jan-Jul byte hashes verified before analytical row loading
- every CSV schema verified before first analytical row loader invocation
- S0 native support, S1 native support, and target-future-boundary validity are independent layers
- frozen first-passage target accounting preserved unchanged
- target-boundary/labeler inconsistency fails closed
- matched common support is exactly S0 AND S1
- T1 common support is common support AND directional valid frozen target AND target-future-boundary-valid
- support SHA256 commits only to deterministic chronological timestamp membership
- exact four chronological outer folds are frozen
- no model fitting, predictive metric, temporal null, PnL, or economics code exists in the P2B builder

Permanent guards at freeze:
- Jan-Jul analytically opened for P2B = NO
- Aug-30 opened = NO
- Sep-01+ opened = NO
- archive bucket opened = NO
- real T1 dataset built = NO
- model fit = NO
- Campaign 1 = NO
- PnL = NO

### Next stage

The next scientific action is controlled real materialization of the already-authorized consumed Jan-Jul BTCUSDT development data using the frozen P2B builder. It must remain dataset/support materialization only, with no model fitting and no predictive metrics.

Before any real analytical load, add a separate materialization/serialization layer with synthetic tests and output preflight rather than modifying the frozen builder. Use a fresh Linux-native output directory and preserve Aug-30 and Sep-01+ as closed.

---

## 38. DEV030-P2C deterministic materialization layer frozen and pushed

Branch:
`research/dev030-p2c-materialization`

Parent:
`9c92b694d19270e8d4edbf3f47c40bee0da57cf5`

Frozen P2C implementation commit:
`f428ed4aaf8319da61d3dc57d0f5949ca1c6837d`

Committed files exactly:
- `src/multimarket/dev030_direction_materialize.py`
- `tests/test_dev030_direction_materialize.py`

Frozen SHA256:
- source = `271a5511a00ab4d68c8524ad29c8e5bd027c0068b00ead402ce4abacc8010f9e`
- tests = `da7f85350dd693b9bd37b7e69a1526c24bfc090a7ca56e1933f6ed7bbd23a225`

Direct GitHub boundary verification after push:
- branch is exactly one commit ahead of parent
- compare base = `9c92b694d19270e8d4edbf3f47c40bee0da57cf5`
- compare head = `f428ed4aaf8319da61d3dc57d0f5949ca1c6837d`
- changed paths = exactly 2
- both paths are added
- source additions = 879
- test additions = 1113
- no other changed path is present

Final validation before freeze:
- focused P2C synthetic suite = 88 passed
- frozen P2B regression = 36 passed
- frozen sequence-feature regression = 39 passed
- frozen first-passage regression = 26 passed + 17 subtests
- `git diff --check` = PASS
- only warning = known read-only pytest-cache warning
- local HEAD = remote HEAD = `f428ed4aaf8319da61d3dc57d0f5949ca1c6837d`
- worktree after commit/push = clean

Frozen P2C guarantees:
- materialization layer emits provenance/count/support/fold JSON only; no feature matrices, model outputs, predictive metrics, or economics
- frozen P2B builder source identity must be explicitly verified; verified state cannot be fabricated by payload construction
- runtime provenance records Jan-Jul analytical-open state explicitly and keeps Aug-30, Sep-01+, archive bucket, abundant-love, model, Campaign 1, and PnL guards fail-closed
- exact 64 target × window × block candidates and deterministic order are enforced
- per-day target/support counts, common-support fraction, directional T1 subset counts, reason counts, boundary-reason subsets, and fold class counts are reconciled before serialization
- per-day and fold support hashes are validated and preserved
- public fold naming is `train_days` / `validation_day`, never month labels
- canonical JSON is deterministic, sorted, UTF-8, finite-only, and JSON-safe
- output preflight occurs before analytical loading
- write-once semantics reject existing output/final/`.part` paths
- invocation-created partial/output paths are cleaned after pre-commit failures
- once `os.replace` commits the final artifact, a later directory-fsync failure preserves the final artifact and reports the durability error
- canonical real output cannot run in synthetic/test mode
- canonical real mode forbids overrides of manifest verifier, analytical loader, candidate builder, payload builder, or builder hash function
- noncanonical `tmp_path` synthetic dependency injection remains available only for testing

Permanent guards at P2C implementation freeze:
- Jan-Jul analytically opened for P2C = NO
- Aug-30 analytically opened = NO
- Sep-01+ analytically opened = NO
- archive bucket opened = NO
- abundant-love opened = NO
- real P2C output directory created = NO
- real materialization run = NO
- model fit = NO
- Campaign 1 = NO
- PnL = NO

### Next authorized stage: controlled real P2C Jan-Jul materialization

The next action is a separate execution authorization, not another implementation edit.

It may analytically open ONLY the already-consumed BTCUSDT Jan-Jul development-day files required by the frozen P2B manifest and may create only:

`/home/emadh/Multi-Market/evidence/dev030_p2c_direction_materialization_v1/DIRECTION_DATASET_MATERIALIZATION.json`

Before execution, verify:
- current lineage includes frozen P2C commit `f428ed4aaf8319da61d3dc57d0f5949ca1c6837d`
- frozen P2C source/test hashes match the identities above
- frozen P2B builder identity remains `54e7315a12cac10413ac2017849466eb3d225282e3dcf48484615409680348c9`
- canonical output directory is absent
- canonical output parent preflight succeeds
- canonical mode uses only the production dependencies enforced by P2C

The real P2C run must remain materialization only:
- Jan-Jul consumed development days may become analytically opened = YES
- Aug-30 must remain closed
- Sep-01+ must remain closed
- archive bucket must remain closed
- abundant-love must remain closed
- no model fit
- no predictive metric selection
- no temporal-null campaign
- no Campaign 1
- no PnL/economics

After the artifact is written, freeze its byte SHA256, byte count, runtime provenance, authorized input manifest, candidate/day/fold counts, and support hashes before authorizing any modeling stage.

---

## 39. DEV030-P2C real Jan-Jul materialization authorized

Authorization status:
`AUTHORIZED_FOR_LOCAL_EXECUTION`

Frozen implementation lineage:
- P2C implementation commit = `f428ed4aaf8319da61d3dc57d0f5949ca1c6837d`
- P2C handoff descendant before this authorization = `9834c26c862dd03c5a18bb76546cb912efa9533d`
- frozen P2C source SHA256 = `271a5511a00ab4d68c8524ad29c8e5bd027c0068b00ead402ce4abacc8010f9e`
- frozen P2C tests SHA256 = `da7f85350dd693b9bd37b7e69a1526c24bfc090a7ca56e1933f6ed7bbd23a225`
- frozen P2B builder SHA256 = `54e7315a12cac10413ac2017849466eb3d225282e3dcf48484615409680348c9`

Authorized analytical scope:
- ONLY the already-consumed BTCUSDT Jan-Jul development-day Phase0DL files
- no Aug-30
- no Sep-01+
- no archive bucket
- no abundant-love
- no external/news/cross-market data

Authorized output:
`/home/emadh/Multi-Market/evidence/dev030_p2c_direction_materialization_v1/DIRECTION_DATASET_MATERIALIZATION.json`

Canonical execution entry point:
`multimarket.dev030_direction_materialize.run_materialization(...)`

Required invocation values:
- workspace = the verified DEV030-P2C repository worktree root
- output_directory = `REAL_OUTPUT_DIRECTORY`
- created_by_commit = `f428ed4aaf8319da61d3dc57d0f5949ca1c6837d`
- require_canonical_output = `True`
- do not override any production dependency

Execution contract:
- verify branch lineage contains the frozen P2C implementation commit
- verify frozen P2C source/test byte identities before running
- require canonical output directory absent
- run the frozen canonical materializer exactly once
- verify frozen P2B builder before analytical loading
- verify the seven authorized Jan-Jul input hashes and schemas before row loading
- create exactly one write-once canonical JSON artifact
- no feature-matrix dump
- no model fitting
- no predictive metrics
- no candidate selection
- no temporal null
- no Campaign 1
- no PnL/economics

Expected runtime provenance after a successful real run:
- Jan-Jul analytically opened = YES
- authorized development data analytically loaded = YES
- Aug-30 analytically opened = NO
- Sep-01+ analytically opened = NO
- archive bucket opened = NO
- abundant-love opened = NO
- model fit run = NO
- Campaign 1 run = NO
- PnL backtest run = NO

Post-run freeze requirements:
- artifact SHA256
- artifact byte count
- exact canonical output path
- runtime provenance block
- exact authorized input manifest
- candidate count and deterministic candidate ordering
- per-candidate/day/fold count summaries
- support SHA identities
- output directory contents
- confirmation that no `.part` remains
- confirmation that no other output was created
- local branch/HEAD used for execution

Important:
This section records authorization only. It does NOT claim that the local real materialization has already executed. The execution requires the user's local WSL environment because the authorized Jan-Jul files are local and are not accessible from GitHub or this ChatGPT runtime. After the local run, append a separate frozen-result section with the actual artifact identity and observed runtime provenance before authorizing any modeling stage.

---

## 40. DEV030-P2C real Jan-Jul materialization completed and frozen

Execution status:
`DIRECTION_DATASET_SUPPORT_MANIFEST_MATERIALIZED`

Execution branch:
`research/dev030-p2c-materialization`

Execution HEAD:
`f428ed4aaf8319da61d3dc57d0f5949ca1c6837d`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p2c_direction_materialization_v1/DIRECTION_DATASET_MATERIALIZATION.json`

Frozen artifact identity:
- SHA256 = `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`
- bytes = `972852`
- output directory contents = exactly `DIRECTION_DATASET_MATERIALIZATION.json`
- `.part` present = NO

The canonical run was executed exactly once with:
- `require_canonical_output=True`
- `created_by_commit=f428ed4aaf8319da61d3dc57d0f5949ca1c6837d`
- no dependency overrides
- canonical output directory absent before the run
- frozen P2C source/test byte identities verified before the run
- frozen P2C implementation commit present in branch ancestry

Observed runtime provenance:
- Jan-Jul analytically opened = YES
- authorized development scope = `BTCUSDT consumed Jan-Jul development days only`
- authorized development data analytically loaded = YES
- Aug-30 analytically opened = NO
- Sep-01+ analytically opened = NO
- archive bucket opened = NO
- abundant-love opened = NO
- model fit run = NO
- Campaign 1 run = NO
- PnL backtest run = NO

Authorized input manifest consumed by the canonical run:

| Date | Bytes | SHA256 |
| --- | ---: | --- |
| 2026-01-01 | 175947841 | `ab0c61fe9a7517cf97388300e6adb18248a37a7977aac8455a10c02b7906de98` |
| 2026-02-01 | 190143833 | `33e56c6b5b02ec124bf3a21dbed27fc8705fc572cb7fed9ff73876de87c2978e` |
| 2026-03-01 | 188927945 | `076067a4731047dd992004d936d962567c1d7ceed864bb6e778db05bc8c59420` |
| 2026-04-01 | 187654910 | `a803fbb8d68f4173551be4c2cccf9fe03f25d86dc6e00469c4a5ab635ade2307` |
| 2026-05-01 | 185174671 | `36015c5954d820d8b2f0505ecab9fdc96f40136247d1270365c9ef81312de2e3` |
| 2026-06-01 | 187421454 | `5e73f8dc355e3dfcceda649525b4d067ccb74d0259992a287161a71375105535` |
| 2026-07-01 | 189729048 | `aadf264ba38eac4563ebab7fd2da22b300d82752343ccd30b19809c70cd39012` |

Frozen candidate grid:
- candidate count = 64
- deterministic order = targets A,B,C,D → windows 8,16,32,60 → blocks PRICE, PRICE_BOOK, PRICE_BOOK_FLOW, PRICE_BOOK_FLOW_DYNAMICS

Target-level aggregate label counts:

| Target | Decisions | Valid | Invalid | Long | Short | None | Future-valid | Future-invalid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A 120s/16bp | 10080 | 10059 | 21 | 684 | 690 | 8685 | 10066 | 14 |
| B 300s/24bp | 10080 | 10038 | 42 | 848 | 856 | 8334 | 10045 | 35 |
| C 300s/12bp | 10080 | 10038 | 42 | 2429 | 2503 | 5106 | 10045 | 35 |
| D 60s/8bp | 10080 | 10066 | 14 | 1223 | 1237 | 7606 | 10073 | 7 |

Frozen invalid-target reasons:
- A: `day_boundary_crossing=14`, `entry_quote_invalid=7`
- B: `day_boundary_crossing=35`, `entry_quote_invalid=7`
- C: `day_boundary_crossing=35`, `entry_quote_invalid=7`
- D: `day_boundary_crossing=7`, `entry_quote_invalid=7`

Support summary:
- 64 candidates × 4 pooled support hashes = 256 SHA256 values preserved
- canonical ordered support-map SHA256 = `ea222f6acd3eefb653b28996ed16bfff3908a5ab2eef07ffa077bbef65a7371e`

Observed pooled support counts:

| Window | Blocks | S0 | S1/Common | T1 A | T1 B | T1 C | T1 D |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | PRICE / PRICE_BOOK | 10073 | 10073 | 1374 | 1704 | 4932 | 2460 |
| 8 | FLOW / DYNAMICS | 10073 | 10067 | 1372 | 1701 | 4927 | 2456 |
| 16 | PRICE / PRICE_BOOK | 10073 | 10073 | 1374 | 1704 | 4932 | 2460 |
| 16 | FLOW / DYNAMICS | 10073 | 10066 | 1372 | 1701 | 4926 | 2456 |
| 32 | PRICE / PRICE_BOOK | 10073 | 10073 | 1374 | 1704 | 4932 | 2460 |
| 32 | FLOW / DYNAMICS | 10073 | 10062 | 1370 | 1699 | 4923 | 2453 |
| 60 | PRICE / PRICE_BOOK | 10073 | 10066 | 1373 | 1702 | 4926 | 2459 |
| 60 | FLOW / DYNAMICS | 10073 | 10030 | 1358 | 1688 | 4897 | 2438 |

Frozen fold structure:
- Fold 1: Jan-Mar → Apr
- Fold 2: Jan-Apr → May
- Fold 3: Jan-May → Jun
- Fold 4: Jan-Jun → Jul

Across the 16 representations per target, observed train/validation T1 count ranges:

| Target | Fold 1 | Fold 2 | Fold 3 | Fold 4 |
| --- | --- | --- | --- | --- |
| A | 800–801 / 158–159 | 958–960 / 62–64 | 1020–1024 / 118–126 | 1138–1150 / 220–224 |
| B | 942–944 / 210–211 | 1152–1155 / 101–103 | 1253–1258 / 172–179 | 1425–1437 / 263–267 |
| C | 2204–2209 / 813–820 | 3017–3029 / 392–397 | 3409–3426 / 648–660 | 4057–4086 / 840–846 |
| D | 1238–1240 / 369–372 | 1607–1612 / 154–157 | 1761–1769 / 274–283 | 2035–2052 / 403–408 |

Fold support preservation:
- all 2,560 fold support hashes preserved
- canonical ordered fold-hash-map SHA256 = `70fb79a657f839a68b10255d398845e8a8377812f623d501b8523f76af8e84a4`

Interpretation:
- real P2C materialization completed successfully
- the materialized artifact is provenance/support metadata only
- no predictive evidence has been generated yet
- no candidate has been selected
- no economic or PnL conclusion has been generated
- Jan-Jul are now consumed/open for DEV030 modeling development
- Aug-30 and Sep-01+ remain closed forward data

### Next stage remains separately gated

Do NOT start model fitting automatically from this handoff update.

The next stage should be a separately reviewed DEV030-P3 / Campaign-1 modeling design that consumes only the now-frozen Jan-Jul development materialization and preserves Aug-30 and Sep-01+ as forward holdout data.

Before fitting, freeze:
- exact modeling task (T1 direction-given-touch)
- exact candidate eligibility set from the 64 materialized representations
- exact M0/M1 baseline definitions
- preprocessing fit only on each fold's training days
- bounded hyperparameter search / trial ledger
- exact primary metrics and stability gates
- exact temporal-null procedure
- exact promotion rule
- no PnL/economic gate until predictive stability is established

No model fitting is authorized merely by completion of P2C.

---

## 41. DEV030-P3 Campaign-1 modeling design frozen

Design branch:
`research/dev030-p3-campaign1-design`

Parent handoff/result commit:
`76486920594f15ea9263da093090458195dc7d20`

Design commit:
`b50b3e9f632f2142a8a2845d522a6a156a417f22`

Design file:
`docs/DEV030_P3_CAMPAIGN1_DESIGN.md`

Design line count:
`814`

Design purpose:
Test whether the frozen causal S1 sequence summaries add stable T1
LONG_FIRST-vs-SHORT_FIRST information beyond matched S0 snapshot models on
consumed Jan-Jul development data.

Key frozen P3 decisions:
- exact candidate universe = 64 = 4 targets × 4 windows × 4 blocks
- primary promotable targets = A 120s/16bp and B 300s/24bp only
- C 300s/12bp and D 60s/8bp remain learnability/cost controls only
- task = T1 DIRECTION_GIVEN_TOUCH only
- M0 deterministic controls plus M1 regularized logistic regression only
- M1 pipeline = train-only StandardScaler + L2 logistic regression
- C grid = [0.01, 0.1, 1.0, 10.0]
- current sklearn 1.9 compatibility form = l1_ratio=0.0 for L2 semantics
- exact four expanding consumed-day outer folds preserved
- exact chronological inner selection uses the final outer-training day as
  inner validation
- no random row splitting
- no class/sample weighting
- fixed probability threshold = 0.5
- primary metrics = balanced accuracy, macro F1, MCC and class-level metrics
- ROC AUC is secondary diagnostic only
- every S1-vs-S0 comparison uses exact matched common support
- deterministic OOF prediction hashes are required
- all 64 candidates remain in a complete append-only logical trial ledger
- primary temporal falsification remains day-local circular label shifts
- expensive null/temporal diagnostics may be skipped only after a candidate
  already fails mandatory precheck gates; this is computation saving without
  weakening promotion
- promotion gate remains strict: pooled S1 BA >= 0.54, stable >0.50 folds,
  S1-S0 pooled BA delta >= +0.02, positive delta in >=3/4 folds, both classes
  predicted, temporal-null pass, and leave-one-fold-out positive incremental
  delta
- only A/B may be ELIGIBLE_FOR_NEXT_DEVELOPMENT_STAGE
- if multiple A/B candidates pass, one survivor is selected by a frozen
  stability-first lexicographic ranking
- no PnL/economics, no opportunity-gate composition, no T2, no M2/MLP/CNN/TCN/
  Transformer in Campaign 1
- Aug-30 and Sep-01+ remain closed forward data

Important new pre-fit guarantee:
Before fitting any estimator, P3 must reconstruct the real 64 candidate
datasets with the frozen P2B builder and reconcile candidate/day/fold counts
and support hashes exactly against the frozen P2C artifact
`a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`.
A mismatch is a hard pre-fit failure.

Planned implementation files only:
- `src/multimarket/dev030_p3_direction.py`
- `tests/test_dev030_p3_direction.py`

Implementation/testing phase must remain synthetic:
- no Jan-Jul analytical opening during implementation tests
- no Aug-30
- no Sep-01+
- no archive bucket
- no abundant-love
- no real model fit
- no Campaign-1 execution
- no PnL

Real Campaign-1 fitting remains separately gated until the P3 implementation
and synthetic tests are frozen and all frozen regressions pass.

---

## 42. DEV030-P3 Campaign-1 implementation checkpoint

Implementation branch:
`research/dev030-p3-campaign1-implementation`

Parent design/handoff commit:
`641863ee840fa3a672c968705d801bbff15e5673`

Current implementation commits:
- `cea90bd70da9d64caf6db41ee760641504bf9f36` — initial P3 core
- `28f424ce55301d25c4c37f79bc6d9dc7fce4e433` — frozen M0 controls
- `4b0c23116062123f5a9857ceb04e5cd8baa93fa3` — safe synthetic output mode
- `09a40930992934afb2f8e6e6b414c293df356926` — synthetic Campaign-1 tests

New implementation files:
- `src/multimarket/dev030_p3_direction.py`
- `tests/test_dev030_p3_direction.py`

Implemented so far:
- frozen 64-candidate identity/order
- frozen P2B/sequence/first-passage source verification
- frozen P2C artifact identity loader
- pre-fit P2C candidate/day/fold reconciliation contract
- runtime provenance and forward/PnL guards
- M0 controls: training majority, microprice sign, OBI sign, OFI sign when present
- M1 train-only StandardScaler + L2 LogisticRegression
- frozen C grid and chronological inner selection
- exact 0.5 prediction threshold
- fold and pooled BA/macro-F1/MCC/class metrics
- diagnostic ROC AUC
- deterministic OOF prediction hashing
- matched S0/S1 candidate fitting over exact frozen outer folds
- leave-one-fold-out incremental BA stability
- day-local shared-shift temporal-label null
- promotion gates and deterministic survivor ranking
- complete 64-candidate payload contract
- deterministic canonical JSON and write-once output logic
- synthetic test-only noncanonical output mode that cannot target the real canonical path

Important:
This is an implementation checkpoint, NOT a freeze. The new P3 test suite and
all frozen regressions still need to run in the user's local WSL environment.
No real Jan-Jul model fit has run from this branch yet.

Current guards:
- Jan-Jul re-opened for P3 model fitting = NO
- Aug-30 opened = NO
- Sep-01+ opened = NO
- archive bucket opened = NO
- abundant-love opened = NO
- Campaign-1 run = NO
- PnL = NO

Next action:
Run the focused P3 synthetic suite first. If it passes, run P2C, P2B,
sequence-feature, and first-passage regressions. Any failure must be fixed
without weakening a frozen test or gate. Only after all pass should P3
implementation be frozen and the real Campaign-1 run separately authorized.

---

## 43. DEV030-P3 post-test quality hardening checkpoint

The first local P3 implementation validation passed at commit
`14d7fba2cbe8c61ffad9f4c0a656096e063158b2`:

- P3 focused tests = 44 passed
- P2C materialization regression = 88 passed
- P2B dataset regression = 36 passed
- P2A sequence-feature regression = 39 passed
- first-passage regression = 26 passed + 17 subtests
- git diff --check = PASS
- worktree = clean
- P3 source SHA256 at that checkpoint =
  `81f276a89d7ed58762b8c6772f2d18555b5776dc0bd34365eda1d9e51c4c8f4f`
- P3 test SHA256 at that checkpoint =
  `d3bda2224f466cc4d57868cd061547163dadc33a7676bd77fdd9eaa44bc8cb86`

No market data were opened and no real Campaign 1 was run.

Before freezing the implementation, an additional scientific review identified
two coverage gaps that were not exposed by the original 44-test suite:

1. M0 control coverage:
   the frozen design requires OBI as a non-tuned control on every candidate
   fold, including PRICE candidates where OBI is not part of the candidate's
   own S0 feature block. The implementation is now hardened to align an exact
   PRICE_BOOK reference by candidate T1 timestamps. OFI is similarly aligned
   from a FLOW reference when the candidate block contains FLOW.

2. Real Campaign-1 orchestration/F2:
   the implementation needed an explicit canonical orchestration path proving
   that frozen P2C reconciliation completes before the first estimator fit,
   plus the frozen F2 explanatory diagnostics for any temporal-null survivor.

Additional implementation commits after the first passing checkpoint:
- `24c9ece99f7dc5adbb5c487a39feca19ad05b77c` — canonical orchestration,
  pre-fit reconciliation hard gate, and cross-block M0 reference alignment
- `304929b41e97f579f2987213cd9f5a6c10211b8d` — sequence reversal,
  deterministic within-sequence time permutation, and incremental-block
  alignment diagnostics with unchanged fitted S1 models
- `0b736fe2172e4d5394e4ec99ec3ea8bcbd776ee7` — strengthened synthetic tests
  for the new orchestration/M0/F2 behavior

Important:
The earlier 44/88/36/39/26+17 PASS result remains valid for commit
`14d7fba2...`, but the strengthened implementation is NOT frozen until the
new source/test bytes are rerun locally.

New tests specifically require:
- PRICE M0 cannot silently omit OBI
- exact aligned BOOK reference can supply OBI on candidate support
- reversal summary arithmetic is exact
- deterministic time-permutation summary reconstruction has exact shape
- block-alignment permutation preserves earlier block columns
- a temporal-null passing candidate cannot serialize without F2 diagnostics
- a P2C reconciliation failure causes zero candidate-fitter calls

Guards remain:
- Jan-Jul reopened for real P3 fitting = NO
- Aug-30 = CLOSED
- Sep-01+ = CLOSED
- archive bucket = CLOSED
- abundant-love = CLOSED
- real Campaign 1 = NO
- real P3 output = NO
- PnL = NO

Next action:
Fetch the latest P3 implementation branch and rerun the focused P3 suite.
Only after it passes should the four frozen regression suites and
`git diff --check` be rerun. Do not freeze or authorize the real Campaign-1
run until that strengthened validation passes.

---

## 44. DEV030-P3 strengthened implementation validation and final audit hardening

Local strengthened validation at remote head
`8018ade0d43f767e4c798b5bcbacdda11b4430e7` completed successfully:

- P3 focused suite = 50 passed
- P2C materialization regression = 88 passed
- P2B dataset regression = 36 passed
- P2A sequence-feature regression = 39 passed
- first-passage regression = 26 passed + 17 subtests
- `git diff --check` = PASS
- worktree = clean
- branch = `research/dev030-p3-campaign1-implementation`
- validated source SHA256 =
  `aeec8b2331ccf278a1ce333d996c635425d7db049e34ec9045b2e79dad0443ad`
- validated test SHA256 =
  `dcf867c4bf2e296ab86b31256e2831830cc4eb7a25995234a7ad02fbc337367a`

No market data were opened. No real Campaign 1 was run. No real P3 output was
created. No PnL or forward data activity occurred.

After that PASS, one final audit-ledger hardening commit was added:

`c66f0ed81f2ccfc502329d0c55c368c534519a33`

This hardening does not alter target definitions, folds, model family, gates,
or data scope. It adds explicit reproducibility/provenance fields required by
the frozen P3 design:

- selected inner-C ledger for every fitted outer-fold representation;
- candidate support contract with per-day T1 class counts/support hashes;
- fold train/validation counts, class counts, and support hashes in each trial
  entry;
- explicit Python, NumPy, and scikit-learn version recording;
- strict full-SHA validation for the execution commit.

Important:
Because these additions changed the P3 source bytes after the 50-test PASS,
the implementation is NOT yet frozen. A final local rerun of the focused P3
suite and all four frozen regressions is required on the new head before
freeze.

Current guards remain:
- Jan-Jul reopened for real P3 fitting = NO
- Aug-30 = CLOSED
- Sep-01+ = CLOSED
- archive bucket = CLOSED
- abundant-love = CLOSED
- real Campaign 1 = NO
- real P3 output = NO
- PnL = NO

Next action:
Fetch the latest branch, run the focused P3 suite, then P2C/P2B/P2A/
first-passage regressions, `git diff --check`, source/test SHA256, branch,
HEAD, and clean status. Stop on first failure. No real data opening or model
run is authorized during this validation.

---

## 45. DEV030-P3 Campaign-1 implementation frozen

Frozen branch:
`research/dev030-p3-campaign1-implementation`

Frozen implementation/test HEAD:
`c375ed43419ca00b93ff94f608d6957c57609ff8`

Frozen P3 source:
`src/multimarket/dev030_p3_direction.py`

Frozen P3 test:
`tests/test_dev030_p3_direction.py`

Frozen byte identities:
- source SHA256 =
  `9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675`
- test SHA256 =
  `a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b`

Final local validation at the frozen head:
- P3 focused suite = 50 passed
- P2C materialization regression = 88 passed
- P2B dataset regression = 36 passed
- P2A sequence-feature regression = 39 passed
- first-passage regression = 26 passed + 17 subtests
- `git diff --check` = PASS
- git status = clean
- branch = `research/dev030-p3-campaign1-implementation`
- HEAD = `c375ed43419ca00b93ff94f608d6957c57609ff8`

Direct GitHub boundary review from the P3 design parent
`641863ee840fa3a672c968705d801bbff15e5673` to the frozen head found only:
- `src/multimarket/dev030_p3_direction.py`
- `tests/test_dev030_p3_direction.py`
- documentation-only changes to this handoff

No frozen P2C/P2B/P2A/first-passage scientific source was modified.

Frozen P3 implementation now includes:
- exact 64-candidate frozen grid/order
- exact consumed-day outer folds and chronological inner selection
- M0 majority/microprice/OBI/OFI controls with cross-block timestamp-aligned
  references when a candidate block does not itself contain the required M0
  feature
- M1 train-only StandardScaler + L2 LogisticRegression
- frozen C grid `[0.01, 0.1, 1.0, 10.0]` with deterministic tie-breaking
- fixed 0.5 decision threshold
- BA, macro-F1, MCC, class-level metrics, confusion matrix, and diagnostic ROC AUC
- deterministic OOF prediction hashes
- per-fold inner-C trial ledgers
- candidate/day/fold support contracts and hashes
- pre-fit reconstruction and exact reconciliation against the frozen real P2C
  materialization
- day-local circular-shift temporal null
- leave-one-fold-out incremental stability gate
- sequence-order reversal diagnostic
- deterministic within-sequence time-permutation diagnostic
- incremental-block alignment permutation diagnostic
- strict promotion gates
- deterministic survivor ranking
- complete 64-candidate logical trial ledger
- explicit Python/NumPy/scikit-learn version provenance
- deterministic canonical JSON and write-once output behavior
- forward-data, PnL, T2, opportunity-gate, and higher-model prohibitions

Permanent guards at implementation freeze:
- market data opened during final validation = NO
- real Campaign 1 run = NO
- real P3 output created = NO
- Aug-30 opened = NO
- Sep-01+ opened = NO
- archive bucket opened = NO
- abundant-love opened = NO
- PnL = NO

This P3 implementation is now FROZEN. Do not change the frozen source/test
bytes in response to Campaign-1 outcomes.

---

## 46. DEV030-P3 real Campaign-1 execution authorized

Authorization status:
`AUTHORIZED_FOR_LOCAL_EXECUTION`

Scientific execution commit:
`c375ed43419ca00b93ff94f608d6957c57609ff8`

Authorized analytical scope:
- ONLY the seven already-consumed BTCUSDT Jan-Jul development days
- no Aug-30
- no Sep-01+
- no archive bucket
- no abundant-love
- no ETH/SOL
- no external/news/options/DVOL/funding/OI/liquidation/on-chain data

Canonical output:
`/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/DEV030_P3_CAMPAIGN1_RESULT.json`

Execution contract:
- verify branch ancestry contains the frozen scientific execution commit
- verify frozen P3 source/test SHA256 exactly before execution
- verify frozen P2C artifact SHA256
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`
- verify canonical P3 output directory is absent
- run `run_campaign1(...)` exactly once in canonical mode
- use `execution_commit=c375ed43419ca00b93ff94f608d6957c57609ff8`
- use `require_canonical_output=True`
- do not override production dependencies
- P2C reconstruction/support reconciliation must complete before first fit
- run the complete frozen 64-candidate Campaign 1
- retain every candidate outcome/failure in the result ledger
- run temporal-null/F2 diagnostics only according to the frozen staging logic
- do not modify any source/test during the real run
- do not run PnL/economics/T2/M2/deep models
- do not open forward data

Expected runtime provenance after completion:
- Jan-Jul analytically opened = YES
- model fit run = YES
- Campaign 1 run = YES
- Aug-30 = NO
- Sep-01+ = NO
- archive bucket = NO
- abundant-love = NO
- PnL backtest = NO

Post-run freeze/report requirements:
- exact artifact path
- artifact SHA256 and bytes
- output directory contents and absence of `.part`
- runtime provenance
- environment versions
- exact candidate count/order
- complete gate outcome counts
- number of temporal-null runs/passes
- number of F2 diagnostic runs
- A/B/C/D outcome summary
- best A and best B by the frozen ranking diagnostics whether or not they pass
- selected survivor if any
- explicit Campaign-1 terminal status
- confirmation that no prohibited activity occurred

Interpretation boundary:
A passing A/B survivor means only
`ELIGIBLE_FOR_NEXT_DEVELOPMENT_STAGE` /
`SELECTED_FOR_NEXT_DEVELOPMENT_STAGE`.
It is not forward-confirmed, deployable, or profitable.
A no-survivor result is a valid scientific failure and must not trigger
post-hoc gate/model/feature changes inside this frozen campaign.

---

## 47. DEV030-P3 real Campaign-1 completed with one primary survivor

Real Campaign-1 terminal status:
`CAMPAIGN1_PRIMARY_SURVIVOR`

Scientific execution commit recorded by the artifact:
`c375ed43419ca00b93ff94f608d6957c57609ff8`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1/DEV030_P3_CAMPAIGN1_RESULT.json`

Frozen artifact identity observed after the one-shot run:
- SHA256 =
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`
- bytes = `1610856`
- output directory contents = exactly `DEV030_P3_CAMPAIGN1_RESULT.json`
- `.part` present = NO

Environment recorded in the artifact:
- Python = `3.14.4`
- NumPy = `2.5.2`
- scikit-learn = `1.9.0`

Observed runtime provenance:
- authorized development scope =
  `BTCUSDT consumed Jan-Jul development days only`
- Jan-Jul analytically opened = YES
- model fit run = YES
- Campaign 1 run = YES
- Aug-30 analytically opened = NO
- Sep-01+ analytically opened = NO
- archive bucket opened = NO
- abundant-love opened = NO
- PnL backtest run = NO

Frozen P2C dependency recorded by the result:
- path =
  `/home/emadh/Multi-Market/evidence/dev030_p2c_direction_materialization_v1/DIRECTION_DATASET_MATERIALIZATION.json`
- SHA256 =
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`

Prohibited-activity flags in the result:
- economics = NO
- forward data = NO
- M2/deep model = NO
- opportunity gate = NO
- PnL = NO
- T2 = NO

Campaign counts:
- candidate count = 64
- temporal-null runs = 1
- temporal-null passes = 1
- F2 explanatory-diagnostic runs = 1
- total eligible candidates = 1
- eligible A/B candidates = 1

Selected survivor:
- target = A
- target geometry = 120 s / 16 bp
- sequence window = 32 s
- feature block = `PRICE`
- final label =
  `SELECTED_FOR_NEXT_DEVELOPMENT_STAGE`

Target-level campaign summary:
- A: 16 candidates, 1 precheck pass, 1 temporal-null run, 1 temporal-null
  pass, 1 eligible candidate
- B: 16 candidates, 0 precheck passes, 0 temporal-null runs, 0 eligible
- C: 16 candidates, 0 precheck passes, 0 temporal-null runs, 0 eligible
- D: 16 candidates, 0 precheck passes, 0 temporal-null runs, 0 eligible

Important interpretation:
This is the first DEV030 result in which a primary economic T1 target produced
a frozen Campaign-1 survivor. The surviving configuration is the simpler
PRICE-only 32-second sequence representation on target A.

By frozen design, eligibility implies that the selected A candidate satisfied
all mandatory Campaign-1 gates, including:
- pooled S1 balanced accuracy >= 0.54
- median outer-fold S1 balanced accuracy > 0.50
- at least 3/4 outer folds above 0.50
- pooled S1-minus-S0 BA delta >= +0.02
- positive S1-minus-S0 BA delta in at least 3/4 folds
- both classes predicted in every fold
- pooled predicted-minority fraction >= 0.10
- temporal-label null observed BA > q95
- temporal-null empirical p <= 0.05
- all leave-one-fold-out S1-minus-S0 BA deltas > 0

The exact numeric fold metrics, temporal-null q95/p, and F2 diagnostic values
for the selected survivor have not yet been copied into this handoff and
should be extracted read-only from the frozen artifact before designing the
next stage.

Caution about the ad-hoc read-only summary helper:
its printed `BEST_A` was the highest raw stability-first configuration among
all A candidates without filtering to Campaign-1 eligibility. That printed
A/60s/PRICE_BOOK_FLOW_DYNAMICS configuration was NOT eligible because pooled
BA was 0.538842611754967, below the frozen 0.54 gate. It must not be confused
with the actual selected survivor A/32s/PRICE.

B did not establish a usable primary direction signal in Campaign 1. Its
reported best raw configuration was B/16s/PRICE with pooled BA
0.50208734746307 and pooled S1-minus-S0 BA delta 0.0035324341682723692,
failing the main performance/incremental-stability gates.

Scientific claim boundary:
- YES: stable incremental T1 direction information was found on one primary
  economic target under the frozen Campaign-1 development protocol.
- NO: this is not prospective forward confirmation.
- NO: T1 is not deployable standalone because it is conditioned on eventual
  touch.
- NO: no PnL, net expectancy, execution profitability, or capital result has
  been established.
- NO: Aug-30 and Sep-01+ remain unopened forward data.

Next scientific action:
Before any M2, T2 composition, opportunity-gate composition, economics, or
forward holdout use, extract and freeze the selected survivor's exact S0/S1
fold metrics, pooled metrics, selected C values, temporal-null q95/p, and all
F2 explanatory diagnostics from the existing artifact. Then review whether
the evidence justifies freezing the A/32s/PRICE representation as the sole
direction configuration for the next separately designed development stage.

---

## 48. DEV030-P3 selected survivor exact metrics and interpretation frozen

Selected Campaign-1 survivor:
- target = A
- geometry = 120 s / 16 bp
- sequence window = 32 s
- feature block = `PRICE`
- task = T1 `DIRECTION_GIVEN_TOUCH`
- model family = M1 regularized logistic regression
- status = `SELECTED_FOR_NEXT_DEVELOPMENT_STAGE`

Exact pooled matched-support result on 573 OOF T1 rows:

| Metric | S0 snapshot | S1 32s sequence | Delta |
| --- | ---: | ---: | ---: |
| Balanced accuracy | 0.4868895263 | 0.5419424831 | +0.0550529568 |
| Macro F1 | 0.4441405194 | 0.5113006397 | +0.0671601203 |
| MCC | -0.0299943335 | 0.0920119182 | +0.1220062517 |
| ROC AUC diagnostic | 0.5010787487 | 0.5367264882 | +0.0356477395 |

Pooled class counts:
- LONG = 309
- SHORT = 264

S0 pooled confusion matrix [SHORT,LONG]:
`[[193,71],[234,75]]`

S1 pooled confusion matrix [SHORT,LONG]:
`[[199,65],[207,102]]`

S1 class metrics:
- LONG precision = 0.6107784431
- LONG recall = 0.3300970874
- LONG F1 = 0.4285714286
- SHORT precision = 0.4901477833
- SHORT recall = 0.7537878788
- SHORT F1 = 0.5940298507

Outer-fold S1 balanced accuracy:
- Fold 1 = 0.5700063715
- Fold 2 = 0.6041666667
- Fold 3 = 0.4916666667
- Fold 4 = 0.5307091685

Matched S1-minus-S0 BA delta by fold:
- Fold 1 = +0.0766167569
- Fold 2 = +0.1041666667
- Fold 3 = +0.0037878788
- Fold 4 = +0.0297029703

All four fold deltas are positive, although Fold 3 absolute S1 BA is below
0.50. This distinction is important: the survivor establishes stable
incremental value versus its matched snapshot more strongly than uniformly
high absolute directional accuracy.

Leave-one-fold-out pooled S1-minus-S0 BA deltas:
- omit Fold 1 = +0.0467212922
- omit Fold 2 = +0.0400944857
- omit Fold 3 = +0.0642570281
- omit Fold 4 = +0.0725806452

All leave-one-fold-out deltas remain positive.

Training-only selected S1 C values by outer fold:
- Fold 1 = 10.0
- Fold 2 = 10.0
- Fold 3 = 0.1
- Fold 4 = 0.01

The selected regularization strength varies materially by fold. Treat this as
evidence of regime/nonstationarity sensitivity, not as a reason to retune on
outer validation.

Primary temporal-label null:
- eligible shared shifts = 45 (k = 10..54)
- observed pooled S1 BA = 0.5419424831
- null q95 = 0.5208701089
- empirical p = 0.0217391304
- pass = YES

With 45 null replicates and empirical p exactly 1/46, zero null replicate met
or exceeded the observed BA. The finite-null resolution floor is therefore
0.0217391304; do not report stronger significance than this design permits.

F2 explanatory diagnostics:

Sequence-order reversal BA / delta from original:
- Fold 1 = 0.5504937878 / -0.0195125836
- Fold 2 = 0.6333333333 / +0.0291666667
- Fold 3 = 0.5265151515 / +0.0348484848
- Fold 4 = 0.5612975932 / +0.0305884247

Within-sequence deterministic time-permutation BA / delta from original:
- Fold 1 = 0.5097961134 / -0.0602102580
- Fold 2 = 0.5708333333 / -0.0333333333
- Fold 3 = 0.5121212121 / +0.0204545455
- Fold 4 = 0.5243499960 / -0.0063591725

Incremental-block alignment permutation is not applicable because the selected
survivor is the base `PRICE` block.

F2 interpretation boundary:
- deterministic time permutation reduces BA in 3/4 folds, supporting a real
  contribution from temporal organization;
- sequence reversal improves BA in 3/4 folds, so the evidence does NOT support
  a stronger claim that the learned edge specifically depends on the true
  forward orientation of trend/end-point summaries;
- the safest claim is that the 32-second causal temporal PRICE context/summaries
  contain incremental T1 information beyond the matched snapshot;
- much of that information may be carried by distributional/order-invariant
  summaries as well as by order-sensitive summaries.

Selected-survivor T1 support by validation fold:
- Fold 1 validation = 159 (LONG 86 / SHORT 73)
- Fold 2 validation = 64 (LONG 40 / SHORT 24)
- Fold 3 validation = 126 (LONG 60 / SHORT 66)
- Fold 4 validation = 224 (LONG 123 / SHORT 101)

The Fold-2 validation set is relatively small, and absolute Fold-3 performance
is weak. These are reasons to preserve conservative claim boundaries and avoid
unnecessary model-capacity escalation.

All frozen promotion gates are TRUE for the selected survivor.

### Scientific next-stage decision

Do NOT open the forward holdout yet.

Do NOT run M2 automatically.

The highest-value missing question is deployability, not additional T1 model
capacity. T1 is oracle-touch and cannot form a trading policy by itself.

Therefore the preferred next stage is a separately frozen T2 /
`TOUCH_VS_NONE` development-and-composition design for the already-selected
A / 120s / 16bp / 32s PRICE representation.

Campaign-2 M2 is DEFERRED, not rejected. The reason is:
- M1 already passed the frozen T1 engineering gate;
- the selected representation is deliberately simple;
- C selection varies strongly by fold and one validation fold remains below
  0.50 absolute BA;
- increasing T1 capacity before proving a deployable touch/abstention layer
  adds overfitting/search risk without resolving the current deployment
  bottleneck.

Next design objective:
freeze a simple causal T2 `TOUCH_VS_NONE` baseline and a two-head composition
using the selected frozen T1 representation, still on consumed Jan-Jul only.
No confidence/action threshold, PnL, opportunity-gate composition, or forward
holdout may be introduced until that T2/composition design is reviewed and
frozen.

Scientific claim after P3:
- YES: one primary economic target exhibits stable incremental causal temporal
  direction information under the frozen development protocol.
- NO: direction is not solved uniformly across folds or targets.
- NO: the selected T1 head is not deployable standalone.
- NO: profitability, net expectancy, and prospective validity remain unproven.

---

## 49. DEV030-P4 T2/composition design frozen

Design branch:
`research/dev030-p4-t2-composition-design`

Design commit:
`f129b0d3e13607dd5699666e1a136178e6c38faa`

Design file:
`docs/DEV030_P4_T2_COMPOSITION_DESIGN.md`

Frozen P4 scope:
- selected configuration only: A / 120s / 16bp / 32s / PRICE
- task: `TOUCH_VS_NONE`
- S0 matched snapshot baseline
- S1 sequence logistic model
- exact chronological folds and training-only preprocessing
- fixed C grid `[0.01, 0.1, 1.0, 10.0]`
- AP/AUC/Brier/log-loss evaluation
- day-local temporal null
- exact reproduction of frozen T1 validation prediction hashes before composition
- two-head probability composition only after T2 promotion
- no additional target/window/block/model search
- no forward-data opening during implementation/testing

Authorized next files:
- `src/multimarket/dev030_p4_touch_composition.py`
- `tests/test_dev030_p4_touch_composition.py`

Real P4 fitting remains separately gated. Implementation and synthetic testing
only are authorized after this design freeze.

---

## 50. DEV030-P4 implementation checkpoint and post-P3 regression note

P4 implementation branch:
`research/dev030-p4-t2-composition-implementation`

Initial P4 implementation/testing commits:
- `4eaf27418120f1fb2c33b7aefa68b930e30cd5cf` — initial T2/composition core
- `ecfffcb9770b9f3795f5a655f59f7f91a7a8ae2d` — initial synthetic tests
- `a6830d8105c7e0f09e592ee5351269e648df734a` — synthetic no-data guard fix

First local validation at `a6830d8...`:
- P4 focused suite = 26 passed
- P2C materialization regression = 88 passed
- P2B dataset regression = 36 passed
- P2A sequence-feature regression = 39 passed
- first-passage regression = 26 passed + 17 subtests
- P3 suite = 49 passed, 1 failed

The single P3 failure was:
`test_real_output_cannot_enter_synthetic_mode`

Observed reason:
the test was written before the real P3 campaign and assumes
`REAL_OUTPUT_DIRECTORY` does not already exist. The successful frozen P3 real
run has now permanently created:
`/home/emadh/Multi-Market/evidence/dev030_p3_campaign1_v1`

Therefore `write_result_once()` correctly fails earlier with
`output_directory_already_exists` instead of reaching the old synthetic-mode
guard. This is a post-run environment/state interaction, not a mutation or
scientific regression in frozen P3 logic.

Do NOT edit the frozen P3 source or test bytes to accommodate this state.

For future P3 regression validation after the canonical artifact exists:
- run the P3 suite excluding only this environment-state-dependent test;
- separately verify the same synthetic-mode invariant in an isolated temporary
  path by monkeypatching the module constant in memory only;
- verify frozen P3 source/test SHA256 remain exactly:
  - source `9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675`
  - test `a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b`

Additional P4 hardening after the first 26-test PASS:
- `d36ef22fc6a137b76ce2bb8f280032bed4198150` — real P4 orchestration,
  T2/composition result gates, P2C/P3 artifact provenance, write-once output
- `dd76fd6e9244dedc2da3339c20f87bebd63a7827` — canonical dependency-loader
  override guards
- `4aa636d838fe7c2e4062c42f0979925615e0eacd` — expanded synthetic
  orchestration/provenance/write-once tests

Current P4 implementation includes:
- exact T2 mapping and support construction
- B0 prevalence, matched S0, and S1 logistic models
- AP/AUC/Brier/log-loss metrics
- chronological inner C selection
- day-local AP/AUC temporal null
- T2 promotion gates and leave-one-fold-out AP stability
- frozen T1 fold-C reconstruction
- exact frozen T1 prediction-hash reproduction requirement
- C0/C1/C2 three-class composition baselines
- two-head composition metrics/gates
- frozen P2C/P3 source/artifact provenance checks
- fail-closed canonical dependency injection
- deterministic canonical JSON and write-once output
- explicit prohibition/runtime guards for threshold optimization, PnL,
  opportunity gate, and forward data

Important:
Because P4 source/tests changed after the initial 26-test PASS, P4 is NOT yet
frozen and real P4 fitting is NOT authorized.

Next:
fetch latest implementation branch and rerun focused P4 tests, then frozen
regressions using the post-P3 regression procedure above. No market data or
real P4 run during validation.

---

## 51. DEV030-P4 implementation frozen and real P4 authorized

Frozen P4 implementation branch:
`research/dev030-p4-t2-composition-implementation`

Frozen scientific source/test HEAD:
`d7d5ec014b8394834359eafae2d778c1a7f7ce7e`

Frozen files:
- `src/multimarket/dev030_p4_touch_composition.py`
- `tests/test_dev030_p4_touch_composition.py`

Frozen SHA256:
- P4 source =
  `bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f`
- P4 test =
  `7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265`

Frozen P3 identities reverified during P4 validation:
- P3 source =
  `9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675`
- P3 test =
  `a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b`

Final local validation at the frozen P4 head:
- P4 focused suite = 33 passed
- P3 regression = 49 passed, 1 environment-state-dependent test deselected
- isolated recheck of that P3 invariant =
  `RESULT = canonical_output_requires_real_mode`
- P2C materialization regression = 88 passed
- P2B dataset regression = 36 passed
- P2A sequence-feature regression = 39 passed
- first-passage regression = 26 passed + 17 subtests
- `git diff --check` = PASS
- worktree = clean
- branch = `research/dev030-p4-t2-composition-implementation`
- HEAD = `d7d5ec014b8394834359eafae2d778c1a7f7ce7e`

GitHub boundary review from the P4 design/handoff parent
`e7878bfc4ddd7977482fa6e8e46b83b7df7fcc09` to the frozen scientific head
found only:
- new P4 source
- new P4 tests
- documentation-only handoff changes

No frozen P3/P2C/P2B/P2A/first-passage scientific source/test was modified.

The one P3 deselection is not a scientific regression. The original P3 test
expects the canonical P3 output path to be absent, while the successful real P3
run has permanently created that path. The same guard was revalidated in an
isolated temporary canonical path without modifying frozen P3 bytes.

### Real P4 authorization

Status:
`AUTHORIZED_FOR_LOCAL_EXECUTION`

Scientific execution commit:
`d7d5ec014b8394834359eafae2d778c1a7f7ce7e`

Authorized analytical scope:
- only already-consumed BTCUSDT Jan-Jul development days
- selected configuration only:
  A / 120 s / 16 bp / 32 s / PRICE
- T2 = TOUCH_VS_NONE
- frozen T1 reproduction and two-head composition only according to the frozen
  P4 design

Forbidden:
- Aug-30
- Sep-01+
- archive bucket
- abundant-love
- ETH/SOL
- threshold optimization
- opportunity-gate composition
- PnL/economics
- M2/deep models
- any source/test modification

Canonical output directory:
`/home/emadh/Multi-Market/evidence/dev030_p4_t2_composition_v1`

Canonical artifact:
`DEV030_P4_T2_COMPOSITION_RESULT.json`

Execution contract:
- verify frozen P4 source/test SHA256
- verify frozen P3 source/test SHA256
- verify frozen P2C artifact SHA256
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`
- verify frozen P3 artifact SHA256
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`
- verify canonical P4 output directory is absent
- call `run_p4(...)` exactly once in canonical mode
- use execution commit
  `d7d5ec014b8394834359eafae2d778c1a7f7ce7e`
- do not override canonical dependencies
- if T2 fails its frozen gate, composition must not run
- if T2 passes, frozen T1 prediction hashes must reproduce exactly before
  composition can proceed
- no rerun after a completed canonical artifact

Expected terminal statuses:
- `FAIL_T2_TOUCH_NOT_STABLE`
- `FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE`
- `ELIGIBLE_FOR_LATER_POLICY_DESIGN`

Interpretation boundary:
Even `ELIGIBLE_FOR_LATER_POLICY_DESIGN` is not a profitability result. It
means only that a deployable-state probability representation survived the
frozen development protocol and may enter a later separately designed
policy/economics stage.

---

## 52. DEV030-P4 real run artifact materialized

The authorized one-shot real P4 command completed and returned an
`ArtifactWriteResult`.

Canonical output directory:
`/home/emadh/Multi-Market/evidence/dev030_p4_t2_composition_v1`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p4_t2_composition_v1/DEV030_P4_T2_COMPOSITION_RESULT.json`

Observed artifact identity:
- SHA256 =
  `8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`
- bytes = `90545`

Scientific execution commit:
`d7d5ec014b8394834359eafae2d778c1a7f7ce7e`

Important:
- the canonical artifact now exists;
- do NOT rerun `run_p4`;
- terminal scientific status and exact T2/composition metrics still require
  read-only extraction from the frozen artifact;
- no interpretation should be upgraded until that read-only inspection is
  complete.

---

## 53. DEV030-P4 real result: T2 passes, two-head composition fails

Canonical P4 artifact:
`/home/emadh/Multi-Market/evidence/dev030_p4_t2_composition_v1/DEV030_P4_T2_COMPOSITION_RESULT.json`

Artifact identity:
- SHA256 =
  `8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`
- bytes = `90545`

Terminal status:
`FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE`

Scientific execution commit:
`d7d5ec014b8394834359eafae2d778c1a7f7ce7e`

Environment:
- Python = 3.14.4
- NumPy = 2.5.2
- scikit-learn = 1.9.0

Runtime/provenance:
- Jan-Jul consumed BTCUSDT development data opened = YES
- model fit = YES
- T2 run = YES
- composition run = YES
- Aug-30 = NO
- Sep-01+ = NO
- archive bucket = NO
- abundant-love = NO
- threshold optimization = NO
- opportunity gate = NO
- PnL/economics = NO
- M2/deep model = NO

Selected configuration remained exactly:
A / 120s / 16bp / 32s / PRICE.

### T2 TOUCH_VS_NONE result

T2 precheck = PASS.
T2 temporal null = PASS.
T2 eligible for composition = YES.
All frozen T2 promotion gates = TRUE.

Pooled support:
- total = 5748
- TOUCH = 573
- NONE = 5175
- TOUCH prevalence = 0.0996868476

B0 prevalence baseline:
- AP = 0.0961414912
- AUC = 0.4377276981
- Brier = 0.0941741601
- log loss = 0.3423294181

Matched S0 snapshot:
- AP = 0.0977739192
- AUC = 0.4426945224
- Brier = 0.0942580993
- log loss = 0.3425616081

S1 32s PRICE sequence:
- AP = 0.2942831079
- AUC = 0.7317547276
- Brier = 0.0882928539
- log loss = 0.3147480751
- threshold-0.5 balanced accuracy = 0.5735371930
- threshold-0.5 macro F1 = 0.5945930024
- MCC = 0.2238790271

S1 versus matched S0:
- pooled AP delta = +0.1965091887
- pooled AUC delta = +0.2890602052
- pooled Brier improvement = +0.0059652454

S1 AP lift over observed TOUCH prevalence:
- 2.9520755744x

Brier skill versus prevalence:
- +0.0624513789

Fold S1-minus-S0 AP deltas:
- +0.0815931847
- +0.1074702510
- +0.1638622717
- +0.2535218509

Fold S1-minus-S0 AUC deltas:
- +0.1506481235
- +0.2653404953
- +0.2195222355
- +0.2234019845

All leave-one-fold-out pooled AP deltas remained positive:
- +0.2545055391
- +0.2005955178
- +0.2073240841
- +0.1054060986

Temporal-label null:
- observed AP = 0.2942831079
- null AP q95 = 0.1675981527
- empirical AP p = 0.0007047216
- observed AUC = 0.7317547276
- null AUC q95 = 0.6537909637
- pass = YES

This is the strongest deployability-relevant predictive result so far in
DEV030: the same simple 32-second PRICE representation predicts whether the
16bp/120s target will be touched substantially better than prevalence and
matched snapshot baselines, with strong fold stability and temporal-null
separation.

### Frozen T1 reproduction

All four frozen P3 T1 prediction hashes reproduced exactly.

Fold 1:
`e03d233bff936b49a0452994497f32ca5ecbe52c1f490d855fe8d06dbfa9dcf4`

Fold 2:
`cd2cba0a6dcf3591ec9848b78e31aef796dad15d371bbecb8517aa2507340bdd`

Fold 3:
`19f9acf70b0065a307c0373952cad350339768607a156c9307e5192503bb1f31`

Fold 4:
`b05ee6e926d6a943e1fc89828eb3801af0863fa270bc2e5db5ed7cd93e9a4b66`

Therefore the composition failure is not attributable to failure to reproduce
the frozen T1 head.

### Two-head composition result

C1 baseline:
T2 touch probability + training-fold constant directional prior.

C2 candidate:
T2 touch probability × frozen T1 conditional-direction probability.

Pooled C1:
- multiclass log loss = 0.3842524747
- multiclass Brier = 0.1824404845
- macro OVR AP = 0.4212752424
- macro OVR AUC = 0.7228599769

Pooled C2:
- multiclass log loss = 0.3852414805
- multiclass Brier = 0.1831724380
- macro OVR AP = 0.4168787259
- macro OVR AUC = 0.7217426400

C2 minus C1 did not improve the primary probability metrics.

Fold log-loss improvement C1 - C2:
- Fold 1 = +0.0005153891
- Fold 2 = +0.0007874417
- Fold 3 = -0.0025525075
- Fold 4 = -0.0027063467

Only 2/4 folds improve, versus the frozen requirement of at least 3/4.

All leave-one-fold-out pooled log-loss improvements are negative:
- -0.0014904708
- -0.0015811551
- -0.0004678387
- -0.0004165589

All frozen composition success gates fail except exact T1 reproduction.

Argmax diagnostics improved slightly under C2:
- pooled balanced accuracy:
  C1 0.3588954765 -> C2 0.3712362332
- pooled macro F1:
  C1 0.3562572342 -> C2 0.3839229093

These argmax improvements are diagnostic only and cannot rescue failure of the
pre-frozen probability-quality gates.

### Scientific interpretation

P4 separates two conclusions cleanly:

1. TOUCH prediction is a real and substantially stronger signal than the
   original conditional-direction signal.
2. The frozen P3 T1 direction head does not add stable incremental
   probabilistic value once the strong T2 touch head is present.

Do not relabel P4 as a pass.
The official status remains:
`FAIL_TWO_HEAD_COMPOSITION_NO_INCREMENTAL_VALUE`.

Do not optimize thresholds or PnL from this failed composition.

### Preferred next scientific step

The development bottleneck has moved from touch detection to direction
conditioning.

Do NOT open forward holdout yet.

Do NOT optimize an action threshold yet.

Do NOT run PnL/economics yet.

The preferred next experiment is a separately frozen low-complexity joint
three-class model on the same already-selected representation:

`NONE / SHORT_FIRST / LONG_FIRST`

using:
- target A / 120s / 16bp
- 32s PRICE representation
- consumed Jan-Jul only
- chronological folds
- regularized multinomial logistic regression first

This is preferred before M2/deep models because it directly tests whether the
two-head factorization itself is the bottleneck while keeping model capacity
and search degrees of freedom low.

The direct three-class model must be compared against the already-frozen C1
baseline and the failed C2 composition under the same support and probability
metrics.

Only if the direct low-complexity joint model also fails should model-capacity
escalation (M2) be reconsidered.

Profitability remains unproven.

---

## 54. DEV030-P5 direct joint three-class design frozen

Design branch:
`research/dev030-p5-joint-threeclass-design`

Design commit:
`e8fd1f4669bb2c9baf073a4a134851b816907a8e`

Design file:
`docs/DEV030_P5_JOINT_THREECLASS_DESIGN.md`

Scientific motivation:
P4 produced a strong and stable T2 TOUCH_VS_NONE result, but the frozen
two-head factorization did not improve joint three-class probability quality
over C1. P5 tests whether the factorization itself is the bottleneck.

Frozen P5 configuration:
- BTCUSDT
- target A
- 120 s / 16 bp
- 32 s PRICE S1 representation
- Jan-Jul consumed development data only
- labels:
  NONE / SHORT_FIRST / LONG_FIRST

Frozen candidate model J1:
- StandardScaler, train-only
- multinomial/softmax LogisticRegression
- L2
- solver lbfgs
- class_weight None
- max_iter 1000
- random_state 20260825
- C grid [0.01, 0.1, 1.0, 10.0]
- no other model family

Inner C selection:
1. lowest multiclass log loss
2. lowest multiclass Brier
3. highest macro OVR AP
4. smaller C

Frozen baselines:
- C0 = three-class training prevalence
- C1 = frozen P4 touch probability + constant training directional prior
- C2 = frozen failed P4 two-head composition

P5 must reproduce frozen P4 baseline metrics/support exactly before evaluating
J1.

Expected pooled P4 validation support:
- total 5748
- NONE 5175
- SHORT_FIRST 264
- LONG_FIRST 309
- 1437 rows in each of four validation folds

Primary J1-vs-C1 success requirements:
- lower pooled multiclass log loss
- lower pooled multiclass Brier
- higher pooled macro OVR AP
- at least 3/4 folds improve log loss
- every leave-one-fold-out pooled log-loss improvement > 0
- at least one directional class AP improves
- mean SHORT/LONG AP delta > 0
- three-class day-local temporal-null log-loss-improvement observed > q95
- empirical null p <= 0.05
- all baseline/provenance invariants pass

P5 explicitly forbids:
- threshold tuning
- class weighting/resampling
- target/window/block search
- additional feature blocks
- PnL/economics
- opportunity-gate composition
- M2/deep models
- forward-data opening

Authorized next implementation files:
- `src/multimarket/dev030_p5_joint_threeclass.py`
- `tests/test_dev030_p5_joint_threeclass.py`

Real P5 fitting remains separately gated.

---

## 55. DEV030-P5 implementation checkpoint

Implementation branch:
`research/dev030-p5-joint-threeclass-implementation`

Design clarification commit:
`c8dd9cb281774a934dc17d224e717e4cf489b984`

The temporal null is explicitly paired:
for every shared day-local label shift, both frozen C1 probabilities and J1
probabilities are scored against the same shifted three-class labels, and the
null statistic is
`LL(C1, shifted) - LL(J1, shifted)`.

Initial implementation commits:
- `8e4b7b067f5dfa9cd900416c05336817534696e0` — P5 direct joint model,
  baseline reconstruction/reconciliation, temporal null, gates, provenance,
  write-once orchestration
- `10c2c698a5007c4dc802af281abcefb76bd0e6eb` — synthetic P5 tests

Current implementation includes:
- exact NONE / SHORT_FIRST / LONG_FIRST mapping
- exact selected A / 120s / 16bp / 32s / PRICE identity
- low-complexity multinomial LogisticRegression with frozen C grid
- chronological inner/outer splitting
- train-only StandardScaler
- proper probability metrics
- reconstruction of frozen P4 C0/C1/C2
- exact P4 baseline metric reconciliation before J1 evaluation
- expected real support contract:
  5748 pooled rows, 1437 per fold, counts 5175/264/309
- J1-vs-C1 pooled/fold/leave-one-fold-out comparisons
- directional AP safeguards
- paired three-class temporal null
- frozen dependency/artifact provenance
- explicit no-forward/no-PnL/no-threshold/no-M2 runtime guards
- deterministic canonical JSON
- atomic write-once artifact

Real P5 fitting is NOT authorized yet.

Next:
fetch the implementation branch and run only synthetic P5 tests and frozen
regressions. Do not open market data and do not run `run_p5` during this
validation.

---

## 56. DEV030-P5 synthetic AP fixture correction

Initial focused P5 validation at checkpoint
`81f8932719e764e736340cd90de885f40bcb52e7` produced:

- 28 passed
- 1 failed

Failed test:
`test_comparison_summary_detects_positive_improvement`

Observed assertion:
`pooled_macro_ap_delta_vs_c1 == 0.0`

Diagnosis:
the synthetic baseline fixture weakened J1 probabilities only by uniform convex
shrinkage toward equal class probability. That transformation preserves the
within-class probability ranking exactly, so Average Precision is unchanged
even though log loss and Brier worsen. Therefore the failing assertion exposed
a synthetic-test fixture defect, not a P5 scientific-logic defect.

Correction commit:
`2aed8c4d508ecc9c9e852b014627308fdec1b3c8`

Correction:
replace uniform shrinkage in the synthetic C1/C2 fixtures with deterministic
class-probability column cycling on fixed subsets of rows. This intentionally
changes ranking as well as proper scoring rules, without randomness or label
mutation, allowing the frozen macro-AP and directional-AP gates to be exercised.

No P5 source/scientific logic was changed by this correction.
No real market data was opened.
No real P5 run occurred.

Next:
fetch the corrected branch and rerun the focused P5 synthetic suite. If PASS,
continue the frozen regression set.

---

## 57. DEV030-P5 implementation frozen and real P5 authorized

Frozen P5 implementation branch:
`research/dev030-p5-joint-threeclass-implementation`

Frozen scientific source/test HEAD:
`b4c7a07b78b0383896f7d119a6b32dc7f77bef3a`

Frozen files:
- `src/multimarket/dev030_p5_joint_threeclass.py`
- `tests/test_dev030_p5_joint_threeclass.py`

Frozen SHA256:
- P5 source =
  `eaa250edecfdf73221fe711001b447982737f7ffd4f4dba9f6d96a79ed913214`
- P5 test =
  `b2c82bc5b2355690881029db976420bb7e0dbb8162677cc468ac924e8947e7d6`

Frozen P4 identities reverified during P5 validation:
- P4 source =
  `bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f`
- P4 test =
  `7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265`

Final local validation at the frozen P5 head:
- P5 focused suite = 29 passed
- P4 regression = 33 passed
- P3 regression = 49 passed, 1 known environment-state-dependent test deselected
- P2C materialization regression = 88 passed
- P2B dataset regression = 36 passed
- P2A sequence-feature regression = 39 passed
- first-passage regression = 26 passed + 17 subtests
- `git diff --check` = PASS
- worktree = clean
- branch = `research/dev030-p5-joint-threeclass-implementation`
- HEAD = `b4c7a07b78b0383896f7d119a6b32dc7f77bef3a`

GitHub boundary review from the P5 design/handoff parent
`4ab048c48c5d554fd8a377b94ae577d1c3ee2ddd` to the frozen scientific head
found only:
- P5 design clarification
- new P5 source
- new P5 tests
- documentation-only handoff changes

No frozen P4/P3/P2C/P2B/P2A/first-passage scientific source/test was modified.

The initial 28-pass/1-fail P5 run was caused by a synthetic AP fixture that
preserved ranking under uniform probability shrinkage. That fixture was
corrected deterministically in
`2aed8c4d508ecc9c9e852b014627308fdec1b3c8`.
No P5 scientific source logic changed as part of that correction.

### Real P5 authorization

Status:
`AUTHORIZED_FOR_LOCAL_EXECUTION`

Scientific execution commit:
`b4c7a07b78b0383896f7d119a6b32dc7f77bef3a`

Authorized analytical scope:
- only already-consumed BTCUSDT Jan-Jul development days
- exact selected configuration only:
  A / 120 s / 16 bp / 32 s / PRICE / S1
- direct three-class labels:
  NONE / SHORT_FIRST / LONG_FIRST
- frozen C0/C1/C2 reconstruction and reconciliation
- J1 direct low-complexity multinomial logistic model only
- paired three-class temporal null only if all non-null gates pass

Forbidden:
- Aug-30
- Sep-01+
- archive bucket
- abundant-love
- ETH/SOL
- target/window/block search
- class weighting
- resampling
- threshold optimization
- opportunity-gate composition
- PnL/economics
- M2/deep models
- any frozen source/test modification

Canonical output directory:
`/home/emadh/Multi-Market/evidence/dev030_p5_joint_threeclass_v1`

Canonical artifact:
`DEV030_P5_JOINT_THREECLASS_RESULT.json`

Execution contract:
- verify P5 source/test SHA256 above
- verify frozen P4 source/test SHA256 above
- verify P4 artifact SHA256
  `8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`
- verify P3 artifact SHA256
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`
- verify P2C artifact SHA256
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`
- verify canonical P5 output directory is absent
- call `run_p5(...)` exactly once in canonical mode
- use execution commit
  `b4c7a07b78b0383896f7d119a6b32dc7f77bef3a`
- do not override canonical dependencies
- no rerun after a completed canonical artifact

Expected terminal statuses:
- `FAIL_DIRECT_JOINT_THREECLASS_NO_INCREMENTAL_VALUE`
- `FAIL_DIRECT_JOINT_THREECLASS_TEMPORAL_NULL`
- `ELIGIBLE_FOR_LATER_POLICY_DESIGN`

Interpretation boundary:
Even a P5 pass is still a development-stage predictive result, not a
profitability result and not forward confirmation.

---

## 58. DEV030-P5 real-run preflight passed

Local preflight before the one-shot real P5 run:

- branch =
  `research/dev030-p5-joint-threeclass-implementation`
- scientific HEAD =
  `b4c7a07b78b0383896f7d119a6b32dc7f77bef3a`
- worktree status = clean

Frozen bytes reverified:
- P5 source =
  `eaa250edecfdf73221fe711001b447982737f7ffd4f4dba9f6d96a79ed913214`
- P5 test =
  `b2c82bc5b2355690881029db976420bb7e0dbb8162677cc468ac924e8947e7d6`
- P4 source =
  `bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f`
- P4 test =
  `7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265`

Frozen artifacts reverified:
- P2C =
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`
- P3 =
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`
- P4 =
  `8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`

Canonical P5 output directory:
`/home/emadh/Multi-Market/evidence/dev030_p5_joint_threeclass_v1`

Preflight state:
`P5_OUTPUT_ABSENT`

Conclusion:
`REAL_P5_ONE_SHOT_READY`

The next command may call `run_p5(...)` exactly once in canonical mode using
execution commit
`b4c7a07b78b0383896f7d119a6b32dc7f77bef3a`.

Do not rerun after the canonical artifact is created, regardless of terminal
status.

---

## 59. DEV030-P5 real artifact materialized

The authorized one-shot real P5 command completed successfully and returned
an `ArtifactWriteResult`.

Canonical output directory:
`/home/emadh/Multi-Market/evidence/dev030_p5_joint_threeclass_v1`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p5_joint_threeclass_v1/DEV030_P5_JOINT_THREECLASS_RESULT.json`

Observed artifact identity:
- SHA256 =
  `d9a89a1be1dc3733cd510666f9a2d717e853a8c414c2c3c943d28ebafa741c00`
- bytes = `16095`

Scientific execution commit:
`b4c7a07b78b0383896f7d119a6b32dc7f77bef3a`

Important:
- the canonical P5 artifact now exists;
- do NOT rerun `run_p5`;
- terminal scientific status and exact J1/C1/C2/null metrics still require
  read-only extraction from the frozen artifact;
- no scientific interpretation should be upgraded until that read-only
  inspection is complete.

---

## 60. DEV030-P5 real result: direct joint three-class fails

Canonical P5 artifact:
`/home/emadh/Multi-Market/evidence/dev030_p5_joint_threeclass_v1/DEV030_P5_JOINT_THREECLASS_RESULT.json`

Artifact identity:
- SHA256 =
  `d9a89a1be1dc3733cd510666f9a2d717e853a8c414c2c3c943d28ebafa741c00`
- bytes = `16095`

Terminal status:
`FAIL_DIRECT_JOINT_THREECLASS_NO_INCREMENTAL_VALUE`

Scientific execution commit:
`b4c7a07b78b0383896f7d119a6b32dc7f77bef3a`

Environment:
- Python = 3.14.4
- NumPy = 2.5.2
- scikit-learn = 1.9.0

Runtime/provenance:
- Jan-Jul consumed BTCUSDT development data opened = YES
- P5 model fit/run = YES
- Aug-30 = NO
- Sep-01+ = NO
- archive bucket = NO
- abundant-love = NO
- threshold optimization = NO
- opportunity gate = NO
- PnL/economics = NO
- M2/deep model = NO

Selected configuration remained exactly:
A / 120s / 16bp / 32s / PRICE / S1.

### Frozen P4 baseline reproduction

P4 baseline reproduction = PASS.

Pooled C0:
- log loss = 0.4118338177
- Brier = 0.1911845029
- macro OVR AP = 0.3262536668
- macro OVR AUC = 0.4397308082

Pooled C1:
- log loss = 0.3842524747
- Brier = 0.1824404845
- macro OVR AP = 0.4212752424
- macro OVR AUC = 0.7228599769

Pooled C2:
- log loss = 0.3852414805
- Brier = 0.1831724380
- macro OVR AP = 0.4168787259
- macro OVR AUC = 0.7217426400

Thus P5 compared J1 against the exact frozen P4 baselines successfully.

### J1 direct three-class result

Pooled J1:
- log loss = 0.3876694072
- Brier = 0.1832958957
- macro OVR AP = 0.4150821556
- macro OVR AUC = 0.7194335867
- argmax balanced accuracy = 0.3662501404
- argmax macro F1 = 0.3764223810

Pooled per-class AP:
- NONE = 0.9555805107
- SHORT_FIRST = 0.1153606182
- LONG_FIRST = 0.1743053379

J1 versus C1:
- pooled log-loss improvement = -0.0034169326
- pooled Brier improvement = -0.0008554111
- pooled macro-AP delta = -0.0061930868
- SHORT_FIRST AP delta = -0.0028819363
- LONG_FIRST AP delta = -0.0156146153
- mean directional AP delta = -0.0092482758

Fold J1-vs-C1 log-loss improvements:
- Fold 1 = -0.0019329645
- Fold 2 = -0.0052884792
- Fold 3 = -0.0031788400
- Fold 4 = -0.0032674466

All four folds are worse than C1.

Leave-one-fold-out pooled log-loss improvements:
- omit Fold 1 = -0.0039115886
- omit Fold 2 = -0.0027930837
- omit Fold 3 = -0.0034962968
- omit Fold 4 = -0.0034667612

All are negative.

Selected C values:
- Fold 1 = 0.01
- Fold 2 = 10.0
- Fold 3 = 0.1
- Fold 4 = 0.1

The wide C variation again indicates regime/nonstationarity sensitivity.

### Promotion decision

All non-null incremental-value gates failed:
- pooled log loss better than C1 = FALSE
- pooled Brier better than C1 = FALSE
- pooled macro AP better than C1 = FALSE
- at least 3/4 fold log-loss improvements = FALSE
- all leave-one-fold-out improvements positive = FALSE
- at least one directional AP improves = FALSE
- mean directional AP delta positive = FALSE

Baseline reproduction passed.

Because the precheck failed, the paired temporal null was correctly NOT RUN.

Final:
`ELIGIBLE_FOR_LATER_POLICY_DESIGN = FALSE`

### Scientific interpretation

P5 provides strong evidence that the P4 composition failure is not merely an
artifact of the two-head probability factorization.

A direct low-complexity three-class model on the same frozen representation is
worse than C1 in every outer fold and every pooled primary probability metric.

The strongest surviving development result remains P4 T2:
`TOUCH_VS_NONE` on A / 120s / 16bp / 32s PRICE.

The unresolved bottleneck is directional discrimination among touch events.

Do NOT relabel P5 as a pass.
Do NOT run a temporal null post hoc.
Do NOT tune thresholds or PnL from J1.
Do NOT open forward holdout.

### Preferred next scientific step

The design condition for reconsidering M2 has now been met.

The next experiment should be a separately frozen, tightly bounded M2
capacity-escalation study targeted specifically at the directional bottleneck,
while keeping:
- target A / 120s / 16bp fixed
- 32s PRICE representation fixed
- T1 directional-touch support fixed
- Jan-Jul consumed development data only
- P3 M1 as the frozen baseline
- no threshold optimization
- no PnL/economics
- no opportunity gate
- no forward holdout

The purpose is to test whether modest nonlinear capacity can add stable
directional information beyond the frozen M1 head without reopening
target/window/block search.

If this bounded M2 direction study fails, the project should stop escalating
model complexity on this representation and reconsider feature information /
market structure rather than continuing capacity search.

---

## 61. DEV030-P6 research review and bounded M2 design frozen

Research-review branch:
`research/dev030-p6-m2-direction-design`

Research note:
`docs/DEV030_P6_M2_DIRECTION_RESEARCH.md`

Research-note commit:
`14fcfa753a709cc2b6931805d4fe242b988bed93`

Frozen P6 design:
`docs/DEV030_P6_M2_DIRECTION_DESIGN.md`

Design commit:
`4c6fc4f1f0bb9cf50e25b1a9d6318b584828cd14`

### External-research conclusion

The next capacity test should NOT jump directly to an MLP/CNN/LSTM/
Transformer.

Reason:
the frozen P3 selected representation is a small 23-feature tabular problem
with only 1,374 total T1 touch rows and 573 OOF validation rows.

External tabular-model benchmarks support using a tightly regularized tree
ensemble as the next controlled capacity increment before deep neural
architectures.

Microstructure literature supports the possibility that nonlinear models can
extract directional information from stationary/order-flow-style inputs, but
the published high-performing deep setups generally operate with substantially
larger datasets and richer raw/sequential LOB information than DEV030 P6.

P6 therefore chooses exactly one M2 family:
`sklearn.ensemble.HistGradientBoostingClassifier`.

### Frozen P6 task

- BTCUSDT
- target A
- 120 s / 16 bp
- 32 s
- PRICE
- S1 representation
- T1 DIRECTION_GIVEN_TOUCH
- SHORT_FIRST = 0
- LONG_FIRST = 1
- NONE excluded
- 23 exact frozen S1 PRICE features
- consumed Jan-Jul only

No target/window/block/feature-subset search.

### Frozen M1 comparator

P6 must reproduce exact frozen P3 M1 before comparison.

Frozen P3 selected C values:
- Fold 1 = 10.0
- Fold 2 = 10.0
- Fold 3 = 0.1
- Fold 4 = 0.01

Frozen P3 prediction hashes:
- F1 `e03d233bff936b49a0452994497f32ca5ecbe52c1f490d855fe8d06dbfa9dcf4`
- F2 `cd2cba0a6dcf3591ec9848b78e31aef796dad15d371bbecb8517aa2507340bdd`
- F3 `19f9acf70b0065a307c0373952cad350339768607a156c9307e5192503bb1f31`
- F4 `b05ee6e926d6a943e1fc89828eb3801af0863fa270bc2e5db5ed7cd93e9a4b66`

Frozen support:
- pooled = 573
- LONG = 309
- SHORT = 264
- fold supports = 159 / 64 / 126 / 224

### Frozen M2 family and capacity grid

Only HistGradientBoostingClassifier.

Fixed:
- loss log_loss
- learning_rate 0.05
- min_samples_leaf 20
- l2_regularization 1.0
- max_features 1.0
- max_bins 255
- categorical_features None
- early_stopping False
- class_weight None
- random_state 20260825
- no scaler

Only four capacity points:
- H1: max_leaf_nodes 3, max_iter 50
- H2: max_leaf_nodes 3, max_iter 100
- H3: max_leaf_nodes 7, max_iter 50
- H4: max_leaf_nodes 7, max_iter 100

Inner selection:
1. lowest binary log loss
2. lowest Brier
3. highest ROC AUC
4. fewer leaves
5. fewer iterations

### Frozen primary evaluation

M2 vs exact frozen M1 on same outer support:
- binary log loss
- Brier
- ROC AUC

Threshold-0.5 BA/macro-F1/MCC remain diagnostics only.

Non-null precheck requires all:
- pooled M2 log loss < M1
- pooled M2 Brier < M1
- pooled M2 AUC > M1
- pooled M2 AUC >= 0.56
- >=3/4 folds positive log-loss improvement
- >=3/4 folds M2 AUC > .50
- >=3/4 folds M2 AUC >= M1
- every LOO pooled log-loss improvement >0
- every LOO pooled AUC delta >0
- exact support/dependency/M1 reproduction/interval-overlap invariants

Only then run paired day-local temporal-label null using
`LL(M1, shifted) - LL(M2, shifted)`.

Final labels:
- `FAIL_M2_DIRECTION_NO_STABLE_INCREMENTAL_VALUE`
- `FAIL_M2_DIRECTION_TEMPORAL_NULL`
- `ELIGIBLE_FOR_DIRECTION_CAPACITY_UPGRADE`

### Research-driven guardrail

If this bounded M2 study fails:
do NOT proceed automatically to deeper models on the same PRICE representation.

The next question becomes information/features, not additional capacity.

### Current authorization

P6 implementation + synthetic testing may begin after this design freeze.

Real Jan-Jul P6 fitting remains separately gated.

Authorized future implementation files only:
- `src/multimarket/dev030_p6_m2_direction.py`
- `tests/test_dev030_p6_m2_direction.py`

Forward holdout, threshold optimization, opportunity gate, PnL/economics,
and deep-model escalation remain forbidden.

---

## 62. DEV030-P6 implementation checkpoint

Implementation branch:
`research/dev030-p6-m2-direction-implementation`

Current implementation commits:
- `26e9bd501f765631afa4e1f8472ae18a95c22862` — initial P6 bounded-HGB core
- `397d9324d5b774baf35562d554ea7d64bc3253cb` — align frozen M1 metric
  checks to the precision recorded in the handoff/artifact summaries
- `859692ae51cdba8fc4a059a0bddc7e47943c59b5` — P6 synthetic test suite

New files:
- `src/multimarket/dev030_p6_m2_direction.py`
- `tests/test_dev030_p6_m2_direction.py`

Implemented:
- exact A / 120s / 16bp / 32s / PRICE / S1 identity
- exact 23-feature frozen PRICE summary order
- T1 SHORT_FIRST/LONG_FIRST support only; NONE excluded
- exact 573 pooled and 159/64/126/224 fold support contracts
- exact frozen P3 M1 C values and prediction-hash reproduction
- additional M1 binary log-loss/Brier/AUC evaluation
- one M2 family only: HistGradientBoostingClassifier
- exact H1-H4 bounded capacity grid
- exact frozen HGB parameters
- chronological inner capacity selection
- probability-first inner selection order
- no scaler for M2
- no class weights/resampling/calibration
- explicit outer and inner information-interval separation assertions
- paired M2-vs-M1 pooled/fold/leave-one-fold-out evaluation
- pooled M2 AUC >= 0.56 capacity-upgrade floor
- paired day-local temporal-label null
- fail-closed final gates
- deterministic support/label/M2 probability hashes
- frozen P2C/P3/P4/P5 artifact and source provenance
- runtime prohibition guards
- deterministic canonical JSON
- atomic write-once canonical artifact

No real Jan-Jul P6 fit has run.

No forward data opened.

No PnL, threshold optimization, T2 composition, opportunity gate, calibration,
alternate model family, or deep model activity occurred.

Current state:
implementation is NOT frozen until the focused P6 suite and all frozen
regressions pass locally.

Next:
fetch this branch into
`/mnt/c/Users/emadh/Downloads/market-exp026`, run the focused P6 synthetic
suite first, stop on any failure, then run the frozen P5/P4/P3/P2 regressions
and integrity/hash checks.

---

## 63. DEV030-P6 focused synthetic validation passed

Local WSL validation at implementation checkpoint:
`1ab33a4b84181115ad880abe77806a1ae7e5b074`

Focused suite:
- `tests/test_dev030_p6_m2_direction.py`
- result = `30 passed`
- elapsed = `4.08s`

Branch:
`research/dev030-p6-m2-direction-implementation`

HEAD:
`1ab33a4b84181115ad880abe77806a1ae7e5b074`

No focused P6 failure occurred.

No real Jan-Jul P6 fit has run.

No forward data opened.

No PnL/economics, threshold optimization, opportunity-gate composition,
T2 composition, calibration, alternate model family, or deep model activity
occurred.

Next:
run the frozen P5/P4/P3/P2 regressions, then `git diff --check`, source/test
SHA256, clean status, and HEAD verification. Only after all pass may the P6
implementation be frozen and the real Jan-Jul P6 run separately authorized.

---

## 64. DEV030-P6 implementation frozen and real P6 authorized

Frozen implementation branch:
`research/dev030-p6-m2-direction-implementation`

Frozen local scientific execution HEAD:
`1ab33a4b84181115ad880abe77806a1ae7e5b074`

Frozen P6 source:
`src/multimarket/dev030_p6_m2_direction.py`

Frozen P6 test:
`tests/test_dev030_p6_m2_direction.py`

Frozen SHA256:
- P6 source =
  `c47ff846e8a7bfc4edc04f5d0ce3753e850431a5bf3548841b85fcbb40dc4367`
- P6 test =
  `38ad2a1922824f45c7f702405172a06c735ea2509e9c1717025371d61e3776d3`

Frozen prior bytes reverified:
- P5 source =
  `eaa250edecfdf73221fe711001b447982737f7ffd4f4dba9f6d96a79ed913214`
- P5 test =
  `b2c82bc5b2355690881029db976420bb7e0dbb8162677cc468ac924e8947e7d6`
- P4 source =
  `bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f`
- P4 test =
  `7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265`
- P3 source =
  `9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675`
- P3 test =
  `a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b`

Final local validation at the frozen P6 head:
- P6 focused suite = 30 passed
- P5 regression = 29 passed
- P4 regression = 33 passed
- P3 regression = 49 passed, 1 known environment-state-dependent test deselected
- P2C materialization regression = 88 passed
- P2B dataset regression = 36 passed
- P2A sequence-feature regression = 39 passed
- first-passage regression = 26 passed + 17 subtests
- `git diff --check` = PASS
- local worktree = clean
- local branch =
  `research/dev030-p6-m2-direction-implementation`
- local HEAD =
  `1ab33a4b84181115ad880abe77806a1ae7e5b074`

GitHub boundary review from frozen P6 design/handoff parent
`74141365344924449b4b823eef11613c0d66ce73`
to scientific execution HEAD
`1ab33a4b84181115ad880abe77806a1ae7e5b074`
found only:
- new P6 source
- new P6 tests
- documentation-only handoff changes

No frozen P5/P4/P3/P2C/P2B/P2A/first-passage scientific source/test was modified.

### Real P6 authorization

Status:
`AUTHORIZED_FOR_LOCAL_EXECUTION`

Scientific execution commit:
`1ab33a4b84181115ad880abe77806a1ae7e5b074`

Authorized analytical scope:
- consumed BTCUSDT Jan-Jul development days only
- exact A / 120s / 16bp / 32s / PRICE / S1 T1 support
- exact frozen P3 M1 reproduction
- exact H1-H4 HistGradientBoostingClassifier capacity grid only
- paired M2-vs-M1 evaluation
- paired temporal-label null only if all non-null precheck gates pass

Forbidden:
- Aug-30
- Sep-01+
- archive bucket
- abundant-love
- ETH/SOL
- target/window/block/feature search
- class weighting
- resampling
- calibration
- threshold optimization
- T2 composition
- opportunity gate
- PnL/economics
- alternate model family
- deep model
- frozen source/test modification

Canonical output directory:
`/home/emadh/Multi-Market/evidence/dev030_p6_m2_direction_v1`

Canonical artifact:
`DEV030_P6_M2_DIRECTION_RESULT.json`

Expected terminal statuses:
- `FAIL_M2_DIRECTION_NO_STABLE_INCREMENTAL_VALUE`
- `FAIL_M2_DIRECTION_TEMPORAL_NULL`
- `ELIGIBLE_FOR_DIRECTION_CAPACITY_UPGRADE`

Important execution-state rule:
The remote branch may receive documentation-only handoff descendants after
this freeze. Do NOT pull those docs-only descendants into the local worktree
before the real P6 run. The real execution commit must remain exactly
`1ab33a4b84181115ad880abe77806a1ae7e5b074`.

Before the real one-shot:
- reverify frozen P6 source/test bytes
- reverify frozen P3/P4/P5/P2C artifact identities
- confirm worktree clean
- confirm canonical P6 output absent

Interpretation boundary:
Even `ELIGIBLE_FOR_DIRECTION_CAPACITY_UPGRADE` is still consumed-development
predictive evidence only, not forward confirmation or profitability.

---

## 65. DEV030-P6 real-run preflight passed

Local preflight immediately before the authorized one-shot P6 run:

- branch =
  `research/dev030-p6-m2-direction-implementation`
- scientific HEAD =
  `1ab33a4b84181115ad880abe77806a1ae7e5b074`
- worktree status = clean

Frozen P6 bytes:
- source =
  `c47ff846e8a7bfc4edc04f5d0ce3753e850431a5bf3548841b85fcbb40dc4367`
- test =
  `38ad2a1922824f45c7f702405172a06c735ea2509e9c1717025371d61e3776d3`

Frozen prior scientific bytes reverified:
- P5 source =
  `eaa250edecfdf73221fe711001b447982737f7ffd4f4dba9f6d96a79ed913214`
- P5 test =
  `b2c82bc5b2355690881029db976420bb7e0dbb8162677cc468ac924e8947e7d6`
- P4 source =
  `bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f`
- P4 test =
  `7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265`
- P3 source =
  `9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675`
- P3 test =
  `a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b`

Frozen artifacts reverified:
- P2C =
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`
- P3 =
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`
- P4 =
  `8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`
- P5 =
  `d9a89a1be1dc3733cd510666f9a2d717e853a8c414c2c3c943d28ebafa741c00`

Canonical P6 output directory:
`/home/emadh/Multi-Market/evidence/dev030_p6_m2_direction_v1`

Preflight state:
`P6_OUTPUT_ABSENT`

Conclusion:
`REAL_P6_ONE_SHOT_READY`

The next command may call `run_p6(...)` exactly once in canonical mode using
execution commit
`1ab33a4b84181115ad880abe77806a1ae7e5b074`.

Do not pull the docs-only descendant before running.

Do not rerun after a canonical artifact is created, regardless of terminal
status.

---

## 66. DEV030-P6 first canonical attempt failed before artifact serialization

The first authorized canonical P6 attempt at scientific execution commit

`1ab33a4b84181115ad880abe77806a1ae7e5b074`

completed the analytical/modeling path far enough to construct the result
payload, but failed before canonical JSON bytes could be produced.

Observed exception:

`P6Error: json_mapping_key_not_string`

Traceback location:
- `run_p6(...)` called `write_result_once(...)`
- `write_result_once(...)` called `canonical_json_bytes(payload)`
- `canonical_json_bytes(...)` rejected a mapping containing a non-string key

Important execution-order fact:
in `write_result_once`, canonical JSON serialization occurs before
`output.mkdir(...)`. Therefore this exception is a pre-write serialization
failure, not an artifact-write failure.

Likely deterministic defect identified from the frozen payload code:
`m1_reproduction` serializes these dictionaries with integer fold IDs as
mapping keys:
- `frozen_C_by_fold`
- `frozen_prediction_sha256_by_fold`

The canonical JSON normalizer intentionally rejects non-string mapping keys.

Scientific interpretation:
- this is an implementation/serialization defect;
- it is NOT a P6 PASS/FAIL scientific result;
- no P6 terminal scientific status should be inferred from the traceback;
- do NOT rerun yet;
- do NOT modify scientific model/gate logic in response.

Required next step:
1. inspect the canonical P6 output path read-only and confirm it is absent and
   there is no partial artifact;
2. make the smallest serialization-only correction, converting frozen fold-key
   mappings to explicit string-key JSON objects;
3. add a synthetic regression proving the canonical payload contains only
   string mapping keys;
4. rerun the focused/regression suites;
5. verify that the diff from the frozen scientific head changes only
   serialization/test/docs behavior;
6. only then decide whether a one-time replacement canonical execution is
   scientifically authorized.

---

## 67. DEV030-P6 serialization-only correction prepared

Read-only post-failure inspection confirmed:
- canonical P6 output directory = ABSENT
- local scientific HEAD remained
  `1ab33a4b84181115ad880abe77806a1ae7e5b074`
- frozen P6 source/test bytes remained unchanged locally

Therefore the first canonical attempt did not consume a canonical artifact.

A minimal serialization-only correction was prepared on the implementation
branch.

Correction commits:
- `32a8ec0b1117cb486be993bcd7bdec27b36b75ef` — convert frozen fold-ID
  mappings to explicit string-key JSON mappings at serialization boundary only
- `1265ff4576a453294e3193016354acd685cf60ee` — add regression tests for
  integer-to-string fold-key conversion and rejection of non-integer fold keys

Scientific logic unchanged:
- no data scope change
- no feature change
- no model-family change
- no H1-H4 grid change
- no M1 reproduction change
- no metric change
- no gate change
- no temporal-null change
- no threshold/PnL/composition change

Important:
do NOT rerun canonical P6 yet.

Next:
fetch the corrected implementation branch, rerun focused P6 tests and frozen
regressions, verify hashes and clean worktree, then perform a GitHub boundary
review from the original scientific execution head to ensure only
serialization/test/docs behavior changed. Only after that may a replacement
one-shot canonical P6 execution be authorized.

---

## 68. DEV030-P6 corrected implementation frozen and replacement run authorized

Post-correction local validation at
`9aa47501ca37faca7442f4e4334ad7a0bcf6b5ba`:

- P6 focused suite = 32 passed
- P5 regression = 29 passed
- P4 regression = 33 passed
- P3 regression = 49 passed, 1 known environment-state-dependent test deselected
- P2C materialization regression = 88 passed
- P2B dataset regression = 36 passed
- P2A sequence-feature regression = 39 passed
- first-passage regression = 26 passed + 17 subtests
- `git diff --check` = PASS
- local worktree = clean

Corrected P6 SHA256:
- source =
  `4e6bf7c30173e7cd470ab6088bf5229d5980bb0542803f8968e62722f567b93e`
- test =
  `1d72ba591b92b132bbcd2bf8cc2ad700eb2a181e4a0e27dfff44b43b931d7c5d`

GitHub boundary review from original scientific execution head

`1ab33a4b84181115ad880abe77806a1ae7e5b074`

to corrected local head

`9aa47501ca37faca7442f4e4334ad7a0bcf6b5ba`

found changes only in:
- `docs/MULTI_MARKET_PROJECT_HANDOFF_2026-09-01.md`
- `src/multimarket/dev030_p6_m2_direction.py`
- `tests/test_dev030_p6_m2_direction.py`

The P6 source diff is serialization-only:
- add `_json_fold_mapping(...)`;
- serialize the two frozen fold-index mappings with explicit string keys.

The P6 test diff only adds regression tests for this conversion.

No data/model/grid/metric/gate/null/provenance scientific logic changed.

Therefore the corrected implementation is frozen for the replacement canonical
execution.

Corrected scientific execution commit:
`9aa47501ca37faca7442f4e4334ad7a0bcf6b5ba`

Replacement-run authorization:
`AUTHORIZED_FOR_ONE_REPLACEMENT_CANONICAL_EXECUTION`

Rationale:
- the first attempt failed before canonical JSON serialization completed;
- canonical output remained absent;
- no artifact or terminal scientific status was produced;
- Jan-Jul is already-consumed development data;
- the correction was made without observing or adapting to scientific metrics;
- the correction affects serialization only.

Before replacement execution:
- confirm local HEAD remains exactly
  `9aa47501ca37faca7442f4e4334ad7a0bcf6b5ba`;
- confirm corrected source/test SHA256 above;
- confirm canonical P6 output remains absent;
- do not pull any docs-only descendant created after this freeze.

The replacement command must use execution commit
`9aa47501ca37faca7442f4e4334ad7a0bcf6b5ba`.

After a canonical P6 artifact is created, do not rerun regardless of status.

---

## 69. DEV030-P6 replacement canonical artifact materialized

The authorized replacement canonical P6 execution completed and returned an
`ArtifactWriteResult`.

Corrected scientific execution commit:
`9aa47501ca37faca7442f4e4334ad7a0bcf6b5ba`

Canonical output directory:
`/home/emadh/Multi-Market/evidence/dev030_p6_m2_direction_v1`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p6_m2_direction_v1/DEV030_P6_M2_DIRECTION_RESULT.json`

Observed artifact identity:
- SHA256 =
  `b7ccd3f81e7c1dac869e4b4059c11af6efa30b90761ef821e5e325f962f58c0a`
- bytes = `20806`

Important:
- the canonical P6 artifact now exists;
- do NOT rerun `run_p6`;
- the first pre-write serialization failure remains documented separately and
  produced no artifact;
- exact terminal scientific status, M1/M2 metrics, selected capacities, fold
  deltas, LOO stability, and temporal-null state still require read-only
  extraction from the canonical artifact;
- no scientific interpretation should be upgraded until that inspection is
  complete.

---

## 70. DEV030-P6 real result: bounded nonlinear capacity fails

Canonical P6 artifact:
`/home/emadh/Multi-Market/evidence/dev030_p6_m2_direction_v1/DEV030_P6_M2_DIRECTION_RESULT.json`

Artifact identity:
- SHA256 =
  `b7ccd3f81e7c1dac869e4b4059c11af6efa30b90761ef821e5e325f962f58c0a`
- bytes = `20806`

Corrected scientific execution commit:
`9aa47501ca37faca7442f4e4334ad7a0bcf6b5ba`

Official status:
`FAIL_M2_DIRECTION_NO_STABLE_INCREMENTAL_VALUE`

Environment:
- Python 3.14.4
- NumPy 2.5.2
- scikit-learn 1.9.0

Selected configuration remained exactly:
A / 120s / 16bp / 32s / PRICE / S1 / 23 features /
DIRECTION_GIVEN_TOUCH.

Runtime guards:
- Jan-Jul consumed BTCUSDT data opened = YES
- Aug-30 = NO
- Sep-01+ = NO
- archive bucket = NO
- abundant-love = NO
- calibration = NO
- class weighting/resampling = NO
- alternate model family = NO
- deep model = NO
- threshold optimization = NO
- T2 composition = NO
- opportunity gate = NO
- PnL/economics = NO

### Frozen M1 reproduction

M1 reproduction = PASS.

Pooled M1:
- binary log loss = 0.7071485069
- Brier = 0.2557125822
- ROC AUC = 0.5367264882
- balanced accuracy @0.5 = 0.5419424831
- macro F1 @0.5 = 0.5113006397
- MCC @0.5 = 0.0920119182

Support:
- pooled = 573
- LONG_FIRST = 309
- SHORT_FIRST = 264

### M2 HGB result

Pooled M2:
- binary log loss = 0.6993391009
- Brier = 0.2526503135
- ROC AUC = 0.5354332157
- balanced accuracy @0.5 = 0.5256141512
- macro F1 @0.5 = 0.5103226520
- MCC @0.5 = 0.0530477946

Pooled M2-vs-M1:
- log-loss improvement = +0.0078094060
- Brier improvement = +0.0030622687
- AUC delta = -0.0012932725

Thus M2 improves proper probability loss slightly, but does not improve
directional ranking.

Selected M2 capacities:
- Fold 1 = H1: 3 leaves / 50 iterations
- Fold 2 = H4: 7 leaves / 100 iterations
- Fold 3 = H1: 3 leaves / 50 iterations
- Fold 4 = H1: 3 leaves / 50 iterations

Fold M2 AUC:
- Fold 1 = 0.5800414145
- Fold 2 = 0.5427083333
- Fold 3 = 0.4766414141
- Fold 4 = 0.5481365210

Fold M2-vs-M1 AUC deltas:
- +0.0190347244
- -0.0708333333
- -0.0084595960
- +0.0203252033

Fold log-loss improvements:
- +0.0015932022
- -0.0436474836
- +0.0153253124
- +0.0226960718

Three of four folds improve log loss, but Fold 2 degrades materially.

Leave-one-fold-out AUC deltas:
- -0.0029347545
- +0.0077679678
- -0.0022108637
- -0.0068606109

Leave-one-fold-out log-loss improvements:
- +0.0101967886
- +0.0142794275
- +0.0056908284
- -0.0017453594

### Gate outcome

PASS:
- all invariants
- pooled Brier better than M1
- pooled log loss better than M1
- >=3/4 fold log-loss improvement
- >=3/4 folds M2 AUC > .50
- non-collapsed probabilities

FAIL:
- pooled AUC better than M1
- pooled M2 AUC >= .56
- >=3/4 folds M2 AUC >= M1
- all LOO AUC deltas positive
- all LOO log-loss improvements positive

Precheck = FAIL.

Therefore paired temporal null was correctly NOT RUN.

Final:
`ELIGIBLE_FOR_DIRECTION_CAPACITY_UPGRADE = FALSE`

### Scientific interpretation

P6 confirms that modest nonlinear capacity does not solve the DEV030
direction bottleneck on the frozen PRICE representation.

The small improvements in log loss and Brier, together with slightly worse
AUC and weaker threshold diagnostics, are consistent with probability
smoothing/regularization rather than discovery of stronger directional
ordering.

Do NOT relabel P6 as a pass.

Do NOT run a post-hoc temporal null.

Do NOT tune HGB further.

Do NOT escalate automatically to MLP/CNN/LSTM/Transformer on the same PRICE
representation.

The strongest surviving deployability-relevant signal remains P4 T2
TOUCH_VS_NONE.

### Preferred next scientific step

The pre-frozen research-driven stop rule has now triggered:
the next question is information content, not model capacity.

Recommended next DEV experiment:
a tightly pre-specified **incremental microstructure-information** study on the
same target A / 120s / 16bp / 32s T1 support.

Research motivation:
- queue imbalance has established short-horizon directional predictive value;
- order-flow-derived stationary inputs have outperformed raw book states in
  published microstructure studies;
- recent BTC evidence warns that OFI effects can be unstable across additional
  days, so fold/LOO stability remains mandatory.

Do not reopen the full P3 64-candidate search.

Preferred structure:
- keep P3 PRICE M1 as frozen baseline;
- add one research-motivated imbalance/order-flow information family at a time;
- preserve 32s and target A exactly;
- use low-complexity regularized probability models first;
- require incremental proper-score + AUC + fold/LOO stability;
- use paired temporal null only after precheck;
- no forward holdout, PnL, thresholds, opportunity gate, or deep model.

A new DEV design must freeze the exact feature family before any fit.

---

## 71. DEV030-P7 incremental L1 OFI design and implementation checkpoint

P6 stop rule triggered:
`FAIL_M2_DIRECTION_NO_STABLE_INCREMENTAL_VALUE`

Research conclusion:
the next question is information content, not additional model capacity.

### Research review

Branch:
`research/dev030-p7-ofi-incremental-design`

Research note:
`docs/DEV030_P7_OFI_INCREMENTAL_RESEARCH.md`

Research-note commit:
`c914d79850e69e89f346ba1892ecf35e703023c6`

External research reviewed before design:
- Cont/Kukanov/Stoikov on top-of-book order-flow imbalance and short-interval
  price impact;
- Gould/Bonart on queue imbalance as a probabilistic one-tick-ahead price
  predictor;
- Xu/Gould/Howison on multi-level OFI;
- Kolm/Turiel/Westray on stationary order-flow-derived inputs.

Research-driven decision:
do NOT reopen the whole PRICE_BOOK_FLOW feature block.

Freeze one compact information family only:
- `ofi_l1_250ms`
- `ofi_l1_1s`
- `ofi_l1_3s`

Each uses the already-frozen S1 statistics:
- last
- mean
- std
- minimum
- maximum
- last_minus_first
- ols_slope
- sign_persistence

Exactly 24 new OFI summaries.

### Frozen P7 design

Design file:
`docs/DEV030_P7_OFI_INCREMENTAL_DESIGN.md`

Design commit:
`f0170f39ee612bb75ed8d8345bcd878e5784a470`

Frozen task:
- BTCUSDT
- target A
- 120s / 16bp
- 32s
- T1 DIRECTION_GIVEN_TOUCH
- SHORT_FIRST=0 / LONG_FIRST=1

Primary matched-support comparison:
- C0 = 23 PRICE S1 features
- C1 = same 23 PRICE S1 + exactly 24 L1 OFI S1 features
- C1 total = 47 features

Both C0/C1:
- train-only StandardScaler
- L2 LogisticRegression
- C grid [0.01, 0.1, 1, 10]
- probability-first inner selection:
  log loss -> Brier -> ROC AUC -> smaller C

Important support rule:
P7 uses FLOW-valid T1 support for BOTH C0 and C1.
Frozen P3 M1 is reproduced separately on original P3 support for provenance,
but is not the primary incremental comparator because FLOW support can be
slightly narrower.

Promotion requires:
- pooled log loss improvement
- pooled Brier improvement
- pooled AUC improvement
- C1 pooled AUC >= 0.56
- >=3/4 fold log-loss improvements
- >=3/4 fold AUC improvements
- >=3/4 C1 fold AUC > .50
- all LOO log-loss improvements positive
- all LOO AUC deltas positive
- matched-support invariants
- paired day-local temporal null pass

No rescue search inside P7.

### Implementation checkpoint

Implementation branch:
`research/dev030-p7-ofi-incremental-implementation`

Source:
`src/multimarket/dev030_p7_ofi_incremental.py`

Source commit:
`f3fdc9a8d1a84427b666807aa98c5492a8c19c51`

Tests:
`tests/test_dev030_p7_ofi_incremental.py`

Test commit:
`23df617eb8b9a5efb19e6b9755124d5e8df3406e`

Implemented:
- exact 23/24/47 feature contracts
- extraction only of predeclared OFI summaries from frozen PRICE_BOOK_FLOW
  source container
- no MLOFI/trade-imbalance/book-depth/dynamics model input
- exact matched C0/C1 support
- generic frozen P2C reconciliation for PRICE and PRICE_BOOK_FLOW candidates
- frozen P3 M1 reproduction
- chronological outer folds and inner selection
- probability-first C selection
- paired pooled/fold/LOO evaluation
- paired temporal-label null
- forward/PnL/threshold/model-family/search guards
- deterministic prediction/support/label hashes
- deterministic canonical JSON
- atomic write-once output

Current state:
P7 implementation is NOT frozen.

No real Jan-Jul P7 fit has run.

No forward data opened.

Next:
run the focused synthetic P7 suite locally. Stop on any failure. Then inspect
and correct implementation bugs without changing the frozen P7 scientific
design.

---

## 72. DEV030-P7 focused synthetic validation passed

Local WSL validation at implementation checkpoint:
`8beee35503ca920e403ff77d544d99987f6bcff8`

Focused suite:
- `tests/test_dev030_p7_ofi_incremental.py`
- result = `29 passed`
- elapsed = `4.23s`

Branch:
`research/dev030-p7-ofi-incremental-implementation`

HEAD:
`8beee35503ca920e403ff77d544d99987f6bcff8`

GitHub boundary review from frozen P7 design commit

`f0170f39ee612bb75ed8d8345bcd878e5784a470`

to implementation checkpoint

`8beee35503ca920e403ff77d544d99987f6bcff8`

found only:
- `src/multimarket/dev030_p7_ofi_incremental.py`
- `tests/test_dev030_p7_ofi_incremental.py`
- docs-only handoff changes

No prior frozen scientific source/test was modified.

No real Jan-Jul P7 fit has run.

No forward data opened.

No PnL/economics, threshold optimization, T2 composition, opportunity gate,
feature-family search, alternate model family, class weighting/resampling,
calibration, or deep-model activity occurred.

Next:
run the frozen P6/P5/P4/P3/P2 regressions, then `git diff --check`, P7
source/test SHA256, prior frozen SHA256 checks, clean status, and HEAD
verification. Only after all pass may the P7 implementation be frozen and a
real Jan-Jul P7 one-shot separately authorized.

---

## 73. DEV030-P7 implementation frozen and real P7 authorized

Frozen scientific implementation checkpoint:
`8beee35503ca920e403ff77d544d99987f6bcff8`

Branch:
`research/dev030-p7-ofi-incremental-implementation`

Frozen files:
- `src/multimarket/dev030_p7_ofi_incremental.py`
- `tests/test_dev030_p7_ofi_incremental.py`

Frozen SHA256:
- P7 source =
  `c22820ff7afe5ea84c07634a3579dc9474e0c7c31a2ae9fdad479d8ddb806c82`
- P7 test =
  `56061f24f7eba5e8a03781e494cdf987a40e18cda80a0f586a2321af98422626`

Final focused validation:
- P7 = 29 passed

Frozen regressions:
- P6 = 32 passed
- P5 = 29 passed
- P4 = 33 passed
- P3 = 49 passed, 1 known environment-state-dependent test deselected
- P2C = 88 passed
- P2B = 36 passed
- P2A = 39 passed
- first-passage = 26 passed + 17 subtests
- `git diff --check` = PASS
- local worktree = clean
- local HEAD =
  `8beee35503ca920e403ff77d544d99987f6bcff8`

Prior frozen SHA256 reverified:
- P6 source =
  `4e6bf7c30173e7cd470ab6088bf5229d5980bb0542803f8968e62722f567b93e`
- P6 test =
  `1d72ba591b92b132bbcd2bf8cc2ad700eb2a181e4a0e27dfff44b43b931d7c5d`
- P5 source =
  `eaa250edecfdf73221fe711001b447982737f7ffd4f4dba9f6d96a79ed913214`
- P5 test =
  `b2c82bc5b2355690881029db976420bb7e0dbb8162677cc468ac924e8947e7d6`
- P4 source =
  `bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f`
- P4 test =
  `7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265`
- P3 source =
  `9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675`
- P3 test =
  `a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b`

GitHub boundary review from frozen P7 design commit
`f0170f39ee612bb75ed8d8345bcd878e5784a470`
to scientific checkpoint
`8beee35503ca920e403ff77d544d99987f6bcff8`
found only:
- new P7 source
- new P7 tests
- docs-only handoff changes

No prior frozen scientific source/test was modified.

Scientific code audit at freeze confirms:
- exactly 23 PRICE S1 baseline features;
- exactly 24 predeclared L1 OFI S1 summaries;
- exactly 47 augmented features;
- C0 and C1 share exact FLOW-valid timestamps/labels;
- no other PRICE_BOOK_FLOW column enters model fitting;
- chronological P3 outer folds are preserved;
- inner validation is the last outer-training day;
- StandardScaler is fit only on training data;
- C0/C1 use only frozen L2 logistic family and C grid;
- primary inner selection is log loss -> Brier -> AUC -> smaller C;
- pooled/fold/LOO paired deltas and 0.56 AUC floor are enforced;
- temporal null is conditional on all precheck gates;
- no threshold optimization, PnL, forward data, feature-family search,
  alternate model family, resampling/class weights, calibration, T2
  composition, or opportunity gate is permitted.

### Real P7 authorization

Status:
`AUTHORIZED_FOR_LOCAL_EXECUTION`

Scientific execution commit:
`8beee35503ca920e403ff77d544d99987f6bcff8`

Authorized scope:
- consumed BTCUSDT Jan-Jul development days only;
- exact A / 120s / 16bp / 32s T1 task;
- exact matched-support C0 PRICE vs C1 PRICE+L1-OFI comparison;
- exact frozen logistic/C-grid protocol;
- paired temporal null only if all non-null gates pass.

Canonical output directory:
`/home/emadh/Multi-Market/evidence/dev030_p7_ofi_incremental_v1`

Canonical artifact:
`DEV030_P7_OFI_INCREMENTAL_RESULT.json`

Expected terminal statuses:
- `FAIL_L1_OFI_NO_STABLE_INCREMENTAL_VALUE`
- `FAIL_L1_OFI_TEMPORAL_NULL`
- `ELIGIBLE_L1_OFI_INCREMENTAL_INFORMATION`

Important:
the remote branch may receive docs-only descendants after this freeze.
Do NOT pull them before real P7 execution.

Before the one-shot:
- confirm local HEAD remains exactly
  `8beee35503ca920e403ff77d544d99987f6bcff8`;
- confirm P7 source/test hashes;
- confirm P2C/P3/P4/P5/P6 artifact hashes;
- confirm worktree clean;
- confirm canonical P7 output is absent.

After any canonical P7 artifact is created, do not rerun regardless of status.

---

## 74. DEV030-P7 real-run preflight passed

Local read-only preflight immediately before the authorized canonical P7 run:

- branch =
  `research/dev030-p7-ofi-incremental-implementation`
- scientific HEAD =
  `8beee35503ca920e403ff77d544d99987f6bcff8`
- worktree = clean

Frozen P7 bytes:
- source =
  `c22820ff7afe5ea84c07634a3579dc9474e0c7c31a2ae9fdad479d8ddb806c82`
- test =
  `56061f24f7eba5e8a03781e494cdf987a40e18cda80a0f586a2321af98422626`

Frozen artifact identities reverified:
- P2C =
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`
- P3 =
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`
- P4 =
  `8dbe23963def1e96da78a73d206e651aa40b0aeab8ba40419716529be33b5a16`
- P5 =
  `d9a89a1be1dc3733cd510666f9a2d717e853a8c414c2c3c943d28ebafa741c00`
- P6 =
  `b7ccd3f81e7c1dac869e4b4059c11af6efa30b90761ef821e5e325f962f58c0a`

Canonical P7 output directory:
`/home/emadh/Multi-Market/evidence/dev030_p7_ofi_incremental_v1`

Preflight state:
`P7_OUTPUT_ABSENT`

Conclusion:
`REAL_P7_ONE_SHOT_READY`

The next command may call `run_p7(...)` exactly once in canonical mode using
execution commit
`8beee35503ca920e403ff77d544d99987f6bcff8`.

Do not pull the docs-only descendant before running.

Do not rerun after a canonical artifact is created, regardless of terminal
status. If an exception occurs, inspect the canonical output directory
read-only before any rerun decision.


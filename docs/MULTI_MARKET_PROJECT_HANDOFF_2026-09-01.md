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

---

## 75. DEV030-P7 canonical artifact materialized

The authorized canonical P7 execution completed successfully and returned an
`ArtifactWriteResult`.

Scientific execution commit:
`8beee35503ca920e403ff77d544d99987f6bcff8`

Canonical output directory:
`/home/emadh/Multi-Market/evidence/dev030_p7_ofi_incremental_v1`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p7_ofi_incremental_v1/DEV030_P7_OFI_INCREMENTAL_RESULT.json`

Observed artifact identity:
- SHA256 =
  `07d3f7f09dc19d771ad2d6ed9323ae3100d0054d6eb8ff37dee1453258efd85c`
- bytes = `23818`

Important:
- canonical P7 artifact now exists;
- do NOT rerun `run_p7`;
- exact terminal scientific status, matched support, C0/C1 metrics, selected
  Cs, fold/LOO deltas, and temporal-null state still require read-only
  extraction from the canonical artifact;
- no scientific interpretation should be upgraded until that inspection is
  complete.

---

## 76. DEV030-P7 real result: L1 OFI summaries fail incremental direction

Canonical P7 artifact:
`/home/emadh/Multi-Market/evidence/dev030_p7_ofi_incremental_v1/DEV030_P7_OFI_INCREMENTAL_RESULT.json`

Artifact identity:
- SHA256 =
  `07d3f7f09dc19d771ad2d6ed9323ae3100d0054d6eb8ff37dee1453258efd85c`
- bytes = `23818`

Scientific execution commit:
`8beee35503ca920e403ff77d544d99987f6bcff8`

Official status:
`FAIL_L1_OFI_NO_STABLE_INCREMENTAL_VALUE`

P3 reproduction:
PASS, with all four frozen P3 prediction hashes reproduced exactly.

Matched P7 support:
- pooled = 569
- LONG_FIRST = 305
- SHORT_FIRST = 264
- Fold 1 = 159
- Fold 2 = 63
- Fold 3 = 125
- Fold 4 = 222

Matched-support C0 PRICE-only pooled:
- log loss = 0.6950752690
- Brier = 0.2511438333
- ROC AUC = 0.5416790859
- balanced accuracy @0.5 = 0.5438835072
- macro F1 @0.5 = 0.5022227118
- MCC @0.5 = 0.1013798787

C1 PRICE + exactly 24 L1 OFI S1 summaries pooled:
- log loss = 0.7622082285
- Brier = 0.2727784755
- ROC AUC = 0.5097739692
- balanced accuracy @0.5 = 0.5044957774
- macro F1 @0.5 = 0.5025808943
- MCC @0.5 = 0.0089798526

Pooled C1-vs-C0:
- log-loss improvement = -0.0671329595
- Brier improvement = -0.0216346421
- AUC delta = -0.0319051167

Fold C1-vs-C0 AUC deltas:
- Fold 1 = +0.0011150048
- Fold 2 = +0.0053418803
- Fold 3 = -0.1158192090
- Fold 4 = +0.0099828165

Fold C1-vs-C0 log-loss improvements:
- Fold 1 = -0.0002497681
- Fold 2 = +0.0134271770
- Fold 3 = -0.3044949235
- Fold 4 = -0.0042476916

Fold 3 is the dominant instability:
- C0 AUC = 0.5133538778
- C1 AUC = 0.3975346687
- C0 log loss = 0.6983926194
- C1 log loss = 1.0028875429
- selected C1 C = 10.0

All leave-one-fold-out log-loss improvements are negative.

Leave-one-fold-out AUC deltas:
- -0.0440842478
- -0.0320332080
- +0.0014987271
- -0.0546479061

Precheck failed.

Temporal null correctly NOT RUN.

Promotion:
`ELIGIBLE_L1_OFI_INCREMENTAL_INFORMATION = FALSE`

Runtime/prohibition guards all PASS:
- no forward data
- no threshold optimization
- no PnL/economics
- no opportunity gate
- no T2 composition
- no feature-family search
- no alternate model family
- no class weighting/resampling
- no calibration
- no deep model

Scientific interpretation:
The predeclared multiscale L1 OFI S1 summary family does not provide stable
incremental conditional-direction information beyond matched-support PRICE.
The result is not merely a failure to exceed the 0.56 AUC floor: C1 is
materially worse on pooled log loss, Brier, and AUC, driven especially by a
large June/Fold-3 failure.

Do NOT:
- select only the individually best OFI horizon post hoc;
- rescue Fold 3 with a different C;
- add MLOFI/trade imbalance inside P7;
- run the temporal null post hoc;
- relabel P7 as partial success.

Preferred next scientific question:
whether additional **temporal path/shape representation**, rather than another
static summary family or larger model on the same S1 features, adds direction
information.

This follows the earlier frozen DEV030 research/design lesson that new value
should come from temporal sequence representation/event dynamics rather than
simply re-adding OFI/MLOFI.

A new DEV design is required before any such fit.

---

## 77. DEV030-P8 PRICE temporal-shape design frozen

P7 official result:
`FAIL_L1_OFI_NO_STABLE_INCREMENTAL_VALUE`

P7 canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p7_ofi_incremental_v1/DEV030_P7_OFI_INCREMENTAL_RESULT.json`

P7 SHA256:
`07d3f7f09dc19d771ad2d6ed9323ae3100d0054d6eb8ff37dee1453258efd85c`

P7 matched-support pooled:
- C0 PRICE-only AUC = 0.5416790859
- C1 PRICE+L1-OFI AUC = 0.5097739692
- AUC delta = -0.0319051167
- C0 log loss = 0.6950752690
- C1 log loss = 0.7622082285
- log-loss improvement = -0.0671329595
- C0 Brier = 0.2511438333
- C1 Brier = 0.2727784755
- Brier improvement = -0.0216346421

Fold 3 was the dominant instability:
- C0 AUC = 0.5133538778
- C1 AUC = 0.3975346687
- C0 log loss = 0.6983926194
- C1 log loss = 1.0028875429

Temporal null was correctly not run because precheck failed.

Research conclusion:
do not rescue OFI post hoc, do not select an individual OFI horizon, and do
not add another static feature family next.

### P8 research question

Test whether the frozen 32-second PRICE whole-window summaries lost useful
temporal path information.

Research note:
`docs/DEV030_P8_PRICE_TEMPORAL_SHAPE_RESEARCH.md`

Research-note commit:
`054e4aeba51b0dbc548e7525a2ddb88d9e619560`

Frozen P8 design:
`docs/DEV030_P8_PRICE_TEMPORAL_SHAPE_DESIGN.md`

Design commit:
`7ce3729bd65e016784787344a97a461a6849fcdb`

Design branch:
`research/dev030-p8-price-temporal-shape-design`

Exact P8 comparison:
- C0 = 23 frozen PRICE S1 whole-window features
- C1 = same C0 + 12 exact fixed-lag PRICE landmarks
- C1 total = 35 features

Lag landmarks:
- t-32s
- t-24s
- t-16s
- t-8s

Applied only to:
- spread_bps
- microprice_minus_mid_bps
- mid_log_return_250ms_bps

No current-t duplicate because `__last` already exists in C0.

Exact support must remain P3 PRICE T1 support:
- pooled = 573
- folds = 159, 64, 126, 224
- LONG = 309
- SHORT = 264

Any support shrink is a protocol failure.

Both C0/C1 use:
- train-only StandardScaler
- L2 LogisticRegression
- C grid [0.01, 0.1, 1, 10]
- probability-first C selection:
  log loss -> Brier -> AUC -> smaller C

Promotion requires proper-score improvement, AUC improvement, >=0.56 pooled
AUC, fold stability, LOO stability, and paired temporal-null pass.

No lag search or rescue is allowed inside P8.

No real P8 fit has run.

Next:
implement P8 source/tests only on a fresh implementation branch, then run
focused synthetic validation and frozen regressions before any Jan-Jul fit.

---

## 78. DEV030-P8 temporal-shape implementation checkpoint

Implementation branch:
`research/dev030-p8-price-temporal-shape-implementation`

P8 source:
`src/multimarket/dev030_p8_price_temporal_shape.py`

Source commit:
`93b505bb25ce9bcf19b64f925f728b3cd36055ea`

P8 tests:
`tests/test_dev030_p8_price_temporal_shape.py`

Test commit:
`871712b45bdada15c4b845fefd8d8e131b0d797b`

Implemented frozen design:
- C0 = exact 23 PRICE S1 features
- temporal-shape addition = exact 12 landmarks
- C1 = exact 35 features
- lags = 32s / 24s / 16s / 8s
- primitives = spread_bps / microprice_minus_mid_bps /
  mid_log_return_250ms_bps
- no t=0 duplicate
- exact-lag timestamp lookup only
- derived lag return uses only lag timestamp and previous 250ms midpoint
- fail-closed validity checks
- no support shrink allowed
- exact P3 support constants frozen
- P3 reproduction and P2C reconciliation
- explicit training/validation information-overlap checks
- chronological outer/inner folds
- train-only StandardScaler
- frozen L2 logistic/C grid
- probability-first C selection
- pooled/fold/LOO paired deltas
- conditional paired temporal null
- forward/search/model/PnL guards
- deterministic hashes/canonical JSON
- atomic write-once output

Synthetic tests cover:
- exact 23/12/35 feature contract
- exact lag order
- causal fixed-lag values
- causal derived-return arithmetic
- missing-lag rejection
- invalid-mask rejection
- support preservation
- nonfinite rejection
- metric/model protocol
- matched support
- exact-support gate
- temporal-null shift contract
- runtime prohibitions
- canonical JSON and atomic output
- tests do not open real data or run P8

Current state:
P8 implementation is NOT frozen.

No real Jan-Jul P8 fit has run.

No forward data opened.

Next:
fetch this implementation checkpoint locally and run only
`tests/test_dev030_p8_price_temporal_shape.py`.
Stop on any failure and correct implementation only without changing the
frozen P8 scientific design.

---

## 79. DEV030-P8 focused synthetic validation passed

Local WSL validation at implementation checkpoint:
`d102803badd2b90a62683ebd1b3bd2884ed7e52b`

Focused suite:
- `tests/test_dev030_p8_price_temporal_shape.py`
- result = `30 passed`
- elapsed = `4.29s`

Branch:
`research/dev030-p8-price-temporal-shape-implementation`

Local HEAD:
`d102803badd2b90a62683ebd1b3bd2884ed7e52b`

GitHub boundary review from frozen P8 design/handoff checkpoint

`bac42e0068ec13f996a14ee7f311a60c56398e80`

to implementation checkpoint

`d102803badd2b90a62683ebd1b3bd2884ed7e52b`

found only:
- new `src/multimarket/dev030_p8_price_temporal_shape.py`
- new `tests/test_dev030_p8_price_temporal_shape.py`
- docs-only handoff changes

No prior frozen scientific source/test was modified.

No real Jan-Jul P8 fit has run.

No forward data opened.

No lag search, feature-family search, alternate/deep model, threshold
optimization, class weighting/resampling, calibration, T2 composition,
opportunity gate, PnL, or economics activity occurred.

Next:
run P7/P6/P5/P4/P3/P2 regressions, then `git diff --check`, P8 source/test
SHA256, prior frozen SHA256 checks, clean status, and exact HEAD verification.
Only after all pass may P8 be frozen and a canonical Jan-Jul one-shot be
authorized.

---

## 80. DEV030-P8 implementation frozen and real P8 authorized

Frozen scientific implementation checkpoint:
`d102803badd2b90a62683ebd1b3bd2884ed7e52b`

Branch:
`research/dev030-p8-price-temporal-shape-implementation`

Frozen files:
- `src/multimarket/dev030_p8_price_temporal_shape.py`
- `tests/test_dev030_p8_price_temporal_shape.py`

Frozen SHA256:
- P8 source =
  `6b2ad4c0d35450b799c6cbcf303158f413227692b94512368c5853390575d6ed`
- P8 test =
  `e1ed717e63ff9201721c33a987188fad5165ba43edb04f9e86902a8e90ad82a0`

Focused validation:
- P8 = 30 passed

Frozen regressions:
- P7 = 29 passed
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
  `d102803badd2b90a62683ebd1b3bd2884ed7e52b`

Prior frozen SHA256 reverified:
- P7 source =
  `c22820ff7afe5ea84c07634a3579dc9474e0c7c31a2ae9fdad479d8ddb806c82`
- P7 test =
  `56061f24f7eba5e8a03781e494cdf987a40e18cda80a0f586a2321af98422626`
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

Final GitHub boundary review from frozen P8 design/handoff checkpoint
`bac42e0068ec13f996a14ee7f311a60c56398e80`
to scientific checkpoint
`d102803badd2b90a62683ebd1b3bd2884ed7e52b`
found only:
- new P8 source
- new P8 tests
- docs-only handoff changes

No prior frozen scientific source/test was modified.

Scientific freeze confirms:
- C0 = exact 23 PRICE S1 features
- C1 = same 23 + exact 12 fixed-lag PRICE landmarks
- lag set = 32s / 24s / 16s / 8s only
- primitives = spread / microprice-minus-mid / 250ms mid return only
- no t=0 duplicate
- exact causal lag timestamps
- no support shrink from frozen P3 support
- exact P3 support requirement = 573 pooled, folds 159/64/126/224
- chronological outer/inner splits
- train-only StandardScaler
- L2 logistic only, C grid [0.01, 0.1, 1, 10]
- probability-first C selection
- proper-score + AUC + fold/LOO gates
- temporal null only after full precheck
- no lag search, feature search, alternate/deep model, forward data,
  threshold optimization, calibration, class weighting/resampling,
  opportunity gate, T2 composition, PnL, or economics

### Real P8 authorization

Status:
`AUTHORIZED_FOR_LOCAL_EXECUTION`

Scientific execution commit:
`d102803badd2b90a62683ebd1b3bd2884ed7e52b`

Canonical output directory:
`/home/emadh/Multi-Market/evidence/dev030_p8_price_temporal_shape_v1`

Canonical artifact:
`DEV030_P8_PRICE_TEMPORAL_SHAPE_RESULT.json`

Expected terminal statuses:
- `FAIL_PRICE_TEMPORAL_SHAPE_NO_STABLE_INCREMENTAL_VALUE`
- `FAIL_PRICE_TEMPORAL_SHAPE_TEMPORAL_NULL`
- `ELIGIBLE_PRICE_TEMPORAL_SHAPE_INCREMENTAL_INFORMATION`

Important:
the remote branch may now receive docs-only descendants.
Do NOT pull them before the real P8 execution.

Before one-shot:
- confirm local HEAD remains exactly
  `d102803badd2b90a62683ebd1b3bd2884ed7e52b`;
- confirm frozen P8 source/test SHA256;
- confirm P2C/P3/P4/P5/P6/P7 artifact hashes;
- confirm worktree clean;
- confirm canonical P8 output is absent.

After any canonical P8 artifact is created, do not rerun regardless of status.
If an exception occurs, inspect canonical output state read-only before any
rerun decision.

---

## 81. DEV030-P8 real-run preflight passed

Local read-only preflight immediately before the authorized canonical P8 run:

- branch =
  `research/dev030-p8-price-temporal-shape-implementation`
- scientific HEAD =
  `d102803badd2b90a62683ebd1b3bd2884ed7e52b`
- worktree = clean

Frozen P8 bytes:
- source =
  `6b2ad4c0d35450b799c6cbcf303158f413227692b94512368c5853390575d6ed`
- test =
  `e1ed717e63ff9201721c33a987188fad5165ba43edb04f9e86902a8e90ad82a0`

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
- P7 =
  `07d3f7f09dc19d771ad2d6ed9323ae3100d0054d6eb8ff37dee1453258efd85c`

Canonical P8 output directory:
`/home/emadh/Multi-Market/evidence/dev030_p8_price_temporal_shape_v1`

Preflight state:
`P8_OUTPUT_ABSENT`

Conclusion:
`REAL_P8_ONE_SHOT_READY`

The next command may call `run_p8(...)` exactly once in canonical mode using
execution commit
`d102803badd2b90a62683ebd1b3bd2884ed7e52b`.

Do not pull the docs-only descendant before running.

Do not rerun after a canonical artifact is created, regardless of terminal
status. If an exception occurs, inspect the canonical output directory
read-only before any rerun decision.

---

## 82. DEV030-P8 canonical artifact materialized

The authorized canonical P8 execution completed successfully and returned an
`ArtifactWriteResult`.

Scientific execution commit:
`d102803badd2b90a62683ebd1b3bd2884ed7e52b`

Canonical output directory:
`/home/emadh/Multi-Market/evidence/dev030_p8_price_temporal_shape_v1`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p8_price_temporal_shape_v1/DEV030_P8_PRICE_TEMPORAL_SHAPE_RESULT.json`

Observed artifact identity:
- SHA256 =
  `34b5af8385d10ce6ab1ddb79a73752c4dd68129e2df80e624e9a19071ddd5ba0`
- bytes = `23821`

Important:
- canonical P8 artifact now exists;
- do NOT rerun `run_p8`;
- exact terminal scientific status, C0/C1 pooled/fold metrics, selected Cs,
  fold/LOO deltas, support invariants, and temporal-null state still require
  read-only extraction from the canonical artifact;
- no scientific interpretation should be upgraded until that inspection is
  complete.



---

## 83. DEV030-P9 remote recovery, implementation checkpoint, and CI validation

The original locally frozen P9 design tip
`e57584ce0ef849c481baa39c24667d1f55807e77`
never reached GitHub because the prior runtime lacked GitHub credentials. GitHub
confirmed that object was absent remotely.

Remote recovery was therefore performed from the documented parent:
`4a3723e2a6ab1684efabf7333fa297933cc1a039`.

Recovered design branch:
`research/dev030-p9-price-dense-sequence-design`

Recovered research note:
`docs/DEV030_P9_PRICE_DENSE_SEQUENCE_RESEARCH.md`

Recovered frozen design:
`docs/DEV030_P9_PRICE_DENSE_SEQUENCE_DESIGN.md`

Important lineage rule:
the recovered remote branch preserves the scientific P9 design but necessarily
has different commit identities from the lost local-only four-commit sequence.

Implementation branch:
`research/dev030-p9-price-dense-sequence-implementation`

Scientific implementation checkpoint:
`7630effcbf84b4342bd7068cd4b49b411fa18ee1`

P9 source:
`src/multimarket/dev030_p9_price_dense_sequence.py`

P9 tests:
`tests/test_dev030_p9_price_dense_sequence.py`

Implemented frozen representation:
- Target A / 120s / 16bp / 32s unchanged
- C0 = exact P8 probability-first PRICE S1 baseline contract
- dense increment = 3 PRICE channels x exact 32s..1s one-second lags
- incremental feature count = 96
- augmented feature count = 119
- channels = spread_bps / microprice_minus_mid_bps /
  mid_log_return_250ms_bps
- exact timestamp lookup only
- no interpolation or imputation
- no support shrink
- same chronological outer/inner folds
- train-only StandardScaler
- L2 logistic only with frozen C grid
- probability-first C selection
- paired pooled/fold/LOO comparison
- paired temporal null only after frozen precheck
- explicit no-search/no-forward/no-PnL runtime guards

Additional P9 invariant:
before C1 is evaluated, C0 must reproduce the frozen P8 canonical C0 exactly,
including per-fold selected C, prediction SHA256, support SHA256, label SHA256,
counts, metrics, and pooled metrics.

Frozen P8 artifact identity used for that check:
- path =
  `/home/emadh/Multi-Market/evidence/dev030_p8_price_temporal_shape_v1/DEV030_P8_PRICE_TEMPORAL_SHAPE_RESULT.json`
- SHA256 =
  `34b5af8385d10ce6ab1ddb79a73752c4dd68129e2df80e624e9a19071ddd5ba0`

CI issue discovered during recovery:
the existing workflow did not install pytest although DEV030 tests import it,
and one legacy EXP019 test expected its authorized absolute path to exist on the
GitHub runner.

CI-only correction:
- install `pytest` in the workflow;
- create only the legacy EXP019 placeholder path required for that old
  environment-invariant test;
- no frozen scientific source/test was edited for this CI repair.

Draft PR for CI/review only:
`#1 DEV030-P9 dense PRICE sequence implementation`

GitHub Actions run:
`33576707732`

Results:
- Python 3.12: 789 tests, OK
- Python 3.10: 789 tests, OK

No real P9 Jan-Jul model run occurred.
No canonical P9 artifact exists.
No Railway bucket or volume was listed, opened, downloaded, uploaded, modified,
or deleted.
No August/September forward data was opened.
No P8 rerun occurred.

Current state:
P9 implementation checkpoint is validated by CI, but real P9 execution is NOT
authorized yet.

Next:
perform implementation-freeze checks (exact source/test SHA256, frozen
dependency regressions/identities, GitHub boundary review, clean implementation
state). Only after a separate freeze may one canonical Jan-Jul P9 run be
authorized.


---

## 84. DEV030-P9 implementation freeze completed; local one-shot preflight pending

P9 scientific implementation commit:
`7630effcbf84b4342bd7068cd4b49b411fa18ee1`

Implementation-freeze document:
`docs/DEV030_P9_IMPLEMENTATION_FREEZE.md`

Freeze-document commit:
`3be9dc8160802f4174b34885eeafaa1188dba4e4`

Frozen P9 identities:
- source SHA256 =
  `773bd58bf9b5bde65aaf914a27c923157edce11572dc17c08759e1861366d7e6`
- test SHA256 =
  `ad15737278c15a58e4da3d1034e0a70b441c83d35f752fb8327d3ad233310629`

Regression/identity verification:
- every previously frozen P3-P8 source/test SHA256 matches its authoritative
  frozen value exactly at the P9 scientific commit;
- GitHub boundary review from recovered design base
  `f7f7731a29c39045b71c9034bdbc984ef83fc178`
  to scientific commit
  `7630effcbf84b4342bd7068cd4b49b411fa18ee1`
  contains only the CI workflow correction plus new P9 source and tests;
- no earlier frozen scientific source/test changed.

CI:
- GitHub Actions run `33576707732`
- Python 3.12 = 789 tests, OK
- Python 3.10 = 789 tests, OK

Storage policy reaffirmed:
- keep `market-raw-archive` online/sealed for later confirmation;
- keep `abundant-love` volume online/sealed for later confirmation;
- keep project Railway volumes sealed;
- do not list/open/download/upload/mutate/delete them during P9 development;
- they are reserved for final confirmation only after the development
  model/protocol is fully frozen.

No canonical P9 Jan-Jul run has occurred yet.

Reason:
the canonical Jan-Jul development material and prior frozen evidence artifacts
are local under `/home/emadh/Multi-Market` and are intentionally not available
through the GitHub connector. Therefore remote freeze can be completed here,
but the final read-only local preflight must execute in the WSL environment
that owns those files.

Local preflight must confirm exactly:
1. HEAD = `7630effcbf84b4342bd7068cd4b49b411fa18ee1`;
2. P9 source/test SHA256 values above;
3. frozen P2C/P3/P4/P5/P6/P7/P8 artifact SHA256 identities;
4. authorized Jan-Jul manifest unchanged;
5. canonical P9 output directory absent;
6. no August/September or Railway storage opened;
7. worktree clean.

State:
`P9_IMPLEMENTATION_FROZEN_REMOTE_CHECKS_PASS_LOCAL_PREFLIGHT_PENDING`

The real P9 one-shot becomes authorized only after that local read-only
preflight passes. It must run exactly once from the frozen scientific commit.


---

## 85. DEV030-P9 local focused validation corrected; prior freeze checkpoint superseded

Local WSL validation of the earlier candidate scientific commit
`7630effcbf84b4342bd7068cd4b49b411fa18ee1`
revealed two defects in the newly created P9 test harness:

1. the synthetic dense fixture referenced the obsolete variable name `shape`
   instead of `dense`;
2. the causal derived-return assertion retained the old sparse-P8 column index
   instead of locating the frozen P9 dense feature
   `mid_log_return_250ms_bps__lag_32s`.

These were implementation-validation defects only. No canonical Jan-Jul P9 fit
ran, no P9 artifact was created, and no scientific outcome was observed.

Therefore:
`7630effcbf84b4342bd7068cd4b49b411fa18ee1`
is SUPERSEDED as a P9 execution/freeze candidate and must never be used for the
canonical run.

Corrected candidate scientific commit:
`da40e643293bc1011f6cba2853482253e7b9a891`

Local focused validation at the corrected commit:
- Python 3.14.4
- numpy 2.5.2
- scikit-learn 1.9.0
- pytest 7.4.3
- `tests/test_dev030_p9_price_dense_sequence.py`
- result = 32 passed
- exit code = 0
- worktree remained clean
- HEAD remained exactly the corrected candidate commit

GitHub Actions run:
`33577957284`

Full CI:
- Python 3.12: 789 tests, OK
- Python 3.10: 789 tests, OK

Current state:
`P9_CORRECTED_FREEZE_CANDIDATE_LOCAL_FINAL_PREFLIGHT_PENDING`

Next:
run only the remaining read-only local freeze/preflight checks against
`da40e643293bc1011f6cba2853482253e7b9a891`: exact P9 SHA256 identities,
frozen P3-P8 file identities, frozen P2C-P8 artifact identities, Jan-Jul
authorized manifest, canonical P9 output absence, clean worktree, and exact
HEAD. Do not run the model yet.


---

## 86. DEV030-P9 final local preflight PASS; canonical Jan-Jul one-shot authorized

Final scientific execution commit:
`da40e643293bc1011f6cba2853482253e7b9a891`

The earlier candidate
`7630effcbf84b4342bd7068cd4b49b411fa18ee1`
is superseded because local validation exposed test-harness defects. It must not
be used for the real run. No scientific outcome was observed from that
superseded candidate.

Final frozen P9 file identities:
- source SHA256 =
  `773bd58bf9b5bde65aaf914a27c923157edce11572dc17c08759e1861366d7e6`
- test SHA256 =
  `abc407b89ccccc73747d5985d1886adf47f6642de0b23bd59d3cf79ed4ac1277`

Local focused P9 tests:
- 32 passed on Python 3.14.4 / numpy 2.5.2 / scikit-learn 1.9.0

Full GitHub CI on the same scientific commit:
- run `33577957284`
- Python 3.12 = 789 tests, OK
- Python 3.10 = 789 tests, OK

Final local read-only preflight:
- exact HEAD = PASS
- worktree clean = PASS
- P3-P8 source/test frozen SHA256 = PASS
- frozen dependency identities = PASS
- P2C-P8 canonical artifact SHA256 identities = PASS
- prior protocol state = PASS
- Jan-Jul authorized manifest = PASS, exactly 7 entries
- P9 frozen scientific contract = PASS
- canonical P9 output absent = PASS
- git diff check = PASS
- model fit run = FALSE
- canonical artifact created = FALSE
- Railway command executed = FALSE

Storage policy:
keep `market-raw-archive`, `abundant-love` volume, and the other Railway
volumes online/sealed for later confirmation. Do not use them in P9.

Status:
`REAL_P9_ONE_SHOT_READY`

The next permitted analytical action is exactly one canonical Jan-Jul P9 run
from scientific commit
`da40e643293bc1011f6cba2853482253e7b9a891`.

After any canonical P9 artifact is created, do not rerun regardless of terminal
PASS/FAIL status. If execution raises after output creation is possible, inspect
the canonical output directory read-only before any rerun decision.


---

## 87. DEV030-P9 first canonical attempt aborted before result; no artifact; hash-domain invariant corrected

A first canonical P9 invocation was attempted from scientific commit
`da40e643293bc1011f6cba2853482253e7b9a891`.

The run stopped before C1 evaluation and before artifact writing at:
`p8_c0_reproduction_mismatch: fold=1:prediction_sha256`.

Read-only inspection immediately afterward confirmed:
`/home/emadh/Multi-Market/evidence/dev030_p9_price_dense_sequence_v1`
did not exist.

Therefore:
- no canonical P9 artifact was created;
- no terminal P9 scientific PASS/FAIL was observed;
- this attempt is classified `ABORTED_PRE_RESULT_IMPLEMENTATION_INVARIANT`;
- the no-rerun-after-valid-artifact rule was not triggered.

Root cause:
P9 used new P9-specific hashing domains while demanding exact hash equality to
the frozen P8 C0 artifact. P8 uses:
- `DEV030-P8-OOF-PREDICTION-V1\x00`
- `DEV030-P8-LABELS-V1\x00`

Thus exact P8 C0 hash reproduction was structurally impossible even when the
underlying C0 probabilities/labels were identical.

Implementation-only correction:
commit
`d2c95858cd5020046130d054574b194ecf51f7fb`

Correction semantics:
- C0 prediction hashing preserves the frozen P8 prediction hash domain;
- label hashing preserves the frozen P8 label hash domain;
- C1 prediction hashing remains P9-specific;
- no feature, target, support, fold, model, hyperparameter grid, metric,
  promotion gate, temporal null rule, or data boundary changed.

GitHub Actions run:
`33578472281`
- Python 3.10: 789 tests, OK
- Python 3.12: 789 tests, OK

Current state:
`P9_HASH_DOMAIN_FIX_CI_PASS_LOCAL_VERIFICATION_REQUIRED`

Next permitted action:
perform local focused verification and read-only preflight on
`d2c95858cd5020046130d054574b194ecf51f7fb`.
Do not run the canonical model again until those checks pass.


---

## 88. DEV030-P9 hash-compatible execution candidate validated locally and in CI

Final corrected scientific execution candidate:
`91a8532cfb6daca7e8c0eb0a263a8cab92e0d81c`

This candidate includes the P8-compatible C0/label hash-domain correction plus
direct regression tests against frozen P8 hashing.

Local WSL validation:
- HEAD exactly `91a8532cfb6daca7e8c0eb0a263a8cab92e0d81c`
- focused P9 tests = 34 passed
- P9 test exit code = 0
- P8 C0 prediction hash == P9 C0 prediction hash = TRUE
- P8 label hash == P9 label hash = TRUE
- canonical P9 output directory absent = TRUE
- worktree clean

GitHub Actions:
- run `33578579742`
- Python 3.12: 789 tests, OK
- Python 3.10: 789 tests, OK

Code-path audit versus frozen P8 confirmed C0 identity in:
- probability-first C selection;
- StandardScaler train-only fitting;
- LogisticRegression configuration;
- outer-fold stacking/order;
- probability metrics;
- prediction serialization/hashing after the domain correction;
- label hashing.

Comparison from the prior attempted candidate `da40e643...` to
`91a8532...` changed only:
- P9 provenance/hash-domain implementation;
- P9 regression tests;
- P9 freeze/handoff documentation.
No P3-P8 frozen scientific source/test was modified.

Current state:
`P9_CORRECTED_EXECUTION_CANDIDATE_VALIDATED_FINAL_READ_ONLY_PREFLIGHT_REQUIRED`

Do not run the canonical model until the final read-only local checks confirm
the exact new source/test hashes, frozen prior artifacts, Jan-Jul manifest,
output absence, clean worktree, and exact HEAD.


---

## 89. DEV030-P9 final local checkpoint PASS; corrected canonical one-shot authorized

Scientific execution commit:
`91a8532cfb6daca7e8c0eb0a263a8cab92e0d81c`

Final frozen P9 identities on that commit:
- source SHA256:
  `0be4fa90366dfb33a08669a367efe427239b6ee8a32378d269b84e69e2c36228`
- test SHA256:
  `a7b71855ffac07afd300d96c40b3d7623665c392d5ee63c54140c69eee2e1ea9`

Final local checkpoint:
- exact HEAD = PASS
- focused P9 tests = 34 passed
- P9 test exit = 0
- P2C-P8 canonical artifact SHA256 = PASS
- authorized Jan-Jul manifest count = 7
- Jan-Jul manifest = PASS
- canonical P9 output exists = FALSE
- final dirty count = 0

GitHub CI on the same scientific commit:
- run `33578579742`
- Python 3.12: 789 tests, OK
- Python 3.10: 789 tests, OK

The previous canonical invocation from `da40e643...` remains classified
`ABORTED_PRE_RESULT_IMPLEMENTATION_INVARIANT`; read-only inspection confirmed
no canonical output directory existed afterward, so no scientific P9 result
was produced and the no-rerun-after-valid-artifact rule was not triggered.

Status:
`P9_CORRECTED_CANONICAL_ONE_SHOT_AUTHORIZED`

Only `91a8532cfb6daca7e8c0eb0a263a8cab92e0d81c` may be used for the corrected
canonical Jan-Jul P9 execution. After any artifact is created, do not rerun
regardless of terminal status.


---

## 90. DEV030-P9 canonical artifact created; terminal result inspection pending

The corrected canonical Jan-Jul P9 execution completed successfully at the
process level from scientific execution commit:
`91a8532cfb6daca7e8c0eb0a263a8cab92e0d81c`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p9_price_dense_sequence_v1/DEV030_P9_PRICE_DENSE_SEQUENCE_RESULT.json`

Artifact identity reported by the one-shot writer:
- SHA256:
  `2f1913b3ac80df5cb0dd01dc7001c333983d22e6a8514346f9cee57a3333b9dc`
- bytes:
  `29286`

The canonical writer returned normally:
`P9_CANONICAL_RUN_COMPLETE=TRUE`.

Critical rule now active:
- DEV030-P9 MUST NOT be rerun under any circumstance.
- The artifact is terminal and must be inspected read-only.
- Do not modify, delete, regenerate, or overwrite it.
- Do not use Railway, market-raw-archive, abundant-love, August, or September
  data to reinterpret or rescue this result.

At this point the internal scientific terminal status and metrics have not yet
been read from the artifact in the chat. They must be recorded exactly from the
canonical JSON before assigning PASS/FAIL/eligible interpretation.

Current state:
`P9_CANONICAL_ARTIFACT_FROZEN_READ_ONLY_INSPECTION_PENDING`


---

## 91. DEV030-P9 terminal result frozen: FAIL_PRICE_DENSE_SEQUENCE_NO_STABLE_INCREMENTAL_VALUE

Canonical scientific execution commit:
`91a8532cfb6daca7e8c0eb0a263a8cab92e0d81c`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p9_price_dense_sequence_v1/DEV030_P9_PRICE_DENSE_SEQUENCE_RESULT.json`

Artifact SHA256:
`2f1913b3ac80df5cb0dd01dc7001c333983d22e6a8514346f9cee57a3333b9dc`

Artifact bytes:
`29286`

Environment:
- Python 3.14.4
- numpy 2.5.2
- scikit-learn 1.9.0

Terminal status:
`FAIL_PRICE_DENSE_SEQUENCE_NO_STABLE_INCREMENTAL_VALUE`

Eligibility:
`eligible_price_dense_sequence_incremental_information = false`

Support integrity:
- pooled support = 573
- LONG = 309
- SHORT = 264
- fold support = [159, 64, 126, 224]
- pooled support SHA256 =
  `8b30ba4544530043ebadd323cc40a70a44861a3f00a018dbc1cc9d70fc1ff59d`
- pooled label SHA256 =
  `8af5a70b6a3ff26d22be660809cc736a8cfc0d4a0d1c887a75ca66341cf97215`

P3 reproduction:
PASS exactly on all 4 folds.

C0 pooled:
- AUC = 0.536469059527312
- log loss = 0.7066614084396725
- Brier = 0.2553342216526328
- balanced accuracy = 0.5390188290673728
- macro-F1 = 0.5002901694399254

C1 pooled:
- AUC = 0.538871726978523
- log loss = 0.7480774918377393
- Brier = 0.2664169064007604
- balanced accuracy = 0.520005884083554
- macro-F1 = 0.4967835032351161

C1 vs C0:
- pooled AUC delta = +0.0024026674512109825
- pooled log-loss improvement = -0.041416083398066794
- pooled Brier improvement = -0.01108268474812757
- fold AUC deltas =
  [+0.043963045555909686, +0.017708333333333326,
   -0.001262626262626354, -0.011349915479352712]
- fold log-loss improvements =
  [-0.008034652905497097, -0.004172525678738381,
   -0.13409630305949904, -0.023619331009741007]
- leave-one-fold-out AUC deltas =
  [-0.005282558166834872, +0.00475526641883528,
   +0.0036915338120157015, +0.009070519163533186]
- leave-one-fold-out log-loss improvements =
  [-0.054236487862604044, -0.046098966883404535,
   -0.015291457721689716, -0.052838640804900194]

Precheck gates failed because:
- pooled C1 AUC < 0.56;
- pooled log loss worsened;
- pooled Brier worsened;
- fewer than 3/4 folds improved AUC;
- 0/4 folds improved log loss;
- at least one LOO AUC delta was negative;
- all LOO log-loss improvements were negative.

Therefore:
`TEMPORAL_NULL_NOT_RUN_PRECHECK_FAILED`
as preregistered.

Important preserved positive evidence:
- C1 pooled AUC was slightly above C0 (+0.00240);
- folds 1 and 2 improved AUC;
- at least 3/4 C1 fold AUC values remained > 0.50;
- support/invariants/P3 reproduction all passed.

Scientific interpretation:
A single frozen dense 32-second PRICE sequence using
`spread_bps`, `microprice_minus_mid_bps`, and
`mid_log_return_250ms_bps` at 1-second lags did NOT add stable, calibrated,
cross-fold direction-given-touch information beyond the frozen P3/P8 PRICE
summary baseline. The small pooled AUC gain was not accompanied by probability
quality or stability and therefore must not be promoted.

Do not collapse prior successes:
- EXP024-P1 remains a strong opportunity-ranking success;
- DEV030-P3 remains the frozen direction baseline success;
- DEV030-P4 touch head remains a successful touch-vs-none component even though
  composition failed.

Runtime/prohibited-activity audit:
- Jan-Jul development data only;
- no August/September forward data opened;
- no archive bucket opened;
- no abundant-love volume opened;
- no threshold optimization;
- no lag search;
- no feature-family search;
- no calibration;
- no class weighting/resampling;
- no PnL/economic backtest;
- no opportunity-gate composition;
- no alternate/deep model family.

Hard rule:
DEV030-P9 MUST NEVER BE RERUN.

Next permitted representation experiment:
DEV030-P10 may test exactly one frozen deterministic MiniRocket-style
multivariate PRICE-only transform plus a linear classifier, only after a
separate implementation-compatibility audit and preregistration. No
architecture shopping, no new lag/channel sweep, no OFI retry, no threshold/PnL
optimization, and no holdout consumption.

Current state:
`DEV030_P9_FROZEN_FAIL_NEXT_PERMITTED_P10_AUDIT_ONLY`


---

## 93. DEV030-P10 isolated environment PASS; deterministic transform implementation staged

User-local dedicated P10 environment verified:
- Python 3.14.4
- NumPy 2.5.2
- scikit-learn 1.9.0
- pytest 7.4.3
- Numba 0.67.0
- llvmlite 0.49.0

This environment is separate from the frozen P9 environment.

P10 implementation branch:
`research/dev030-p10-minirocket-implementation`

Deterministic transform source added:
`src/multimarket/dev030_p10_minirocket_transform.py`

Initial transform implementation commit:
`d9b604449cf7b3be34160f65dcc48bf5d460a83b`

Synthetic determinism tests added:
`tests/test_dev030_p10_minirocket_transform.py`

Test commit:
`c0ff1c32924966a5fbbbf4d3356321ed728a3290`

P10-only dependency extra added:
- numba==0.67.0
- llvmlite==0.49.0

CI updated to install `.[ml,p10]` and run the focused P10 pytest file.
Current implementation tip:
`e46f36337a9f0cb5c6ba17136fec3e0c60f0edf7`

Transform determinism strategy:
- all stochastic channel-combination choices are materialized before Numba using
  a frozen RandomState(0);
- bias-instance choices are independently materialized from the same frozen seed;
- the Numba core receives only explicit arrays, avoiding hidden global RNG state;
- transform execution is single-threaded;
- parameters and transformed features have domain-separated SHA256 functions;
- no project data loader, classifier runner, or canonical P10 writer exists yet.

Synthetic gates implemented:
- exact runtime versions;
- length-32 dilation geometry [1,2,3];
- per-kernel feature allocation [60,37,22];
- exact output count 9,996;
- minimum length 9;
- exact canonical 3x32 geometry;
- repeated parameter hash equality;
- repeated transformed-feature hash equality;
- fresh-process hash equality;
- finite float32 output in [0,1];
- all channels {0,1,2} represented;
- one-channel perturbation changes output;
- transform does not mutate input;
- frozen parameter overrides rejected.

No Jan-Jul analytical data has been loaded for P10.
No P10 classifier fit has run.
No P10 artifact exists.
No August/September/Railway storage has been opened.

Current state:
`P10_TRANSFORM_IMPLEMENTED_LOCAL_SYNTHETIC_VALIDATION_PENDING`

Next permitted action:
run the focused transform tests locally in the dedicated P10 environment.
Do not load Jan-Jul until these determinism gates pass and the transform implementation is frozen.


---

## 94. DEV030-P10 local synthetic transform validation PASS

Local WSL validation was run from transform implementation commit:
`e46f36337a9f0cb5c6ba17136fec3e0c60f0edf7`

Environment:
- Python 3.14.4
- NumPy 2.5.2
- scikit-learn 1.9.0
- pytest 7.4.3
- Numba 0.67.0
- llvmlite 0.49.0

Import/protocol check:
- experiment ID = DEV030-P10
- design version = price-minirocket-multivariate-linear-v1
- requested features = 10,000
- actual features = 9,996
- dilations = [1,2,3]
- random state = 0
- exact frozen transform runtime validated

Focused transform tests:
- 11 passed
- exit code = 0

The passing suite includes same-process determinism, fresh-process determinism,
exact 9,996 output width, float32 finite PPV output in [0,1], all three channel
ids represented, one-channel perturbation sensitivity, input non-mutation,
minimum-length guard, canonical geometry guard, and frozen-parameter override
guards.

Repository state after local validation:
- HEAD remained exactly `e46f36337a9f0cb5c6ba17136fec3e0c60f0edf7`
- detached clean worktree

Draft PR #2 was opened for CI/review:
`DEV030-P10 deterministic MiniRocket transform implementation`

CI workflow run:
`33580212075`
was started on PR head `5aa8a6dc5031f09c6f0b41e2de710f80587a60ba`
(the transform implementation plus documentation-only handoff update).
At the time of this record CI was still in progress.

No Jan-Jul P10 analytical data was loaded.
No P10 classifier fit ran.
No P10 canonical artifact exists.
No August/September or Railway storage was opened.

Current state:
`P10_TRANSFORM_LOCAL_SYNTHETIC_PASS_CI_PENDING_IMPLEMENTATION_NOT_YET_FROZEN`

Next permitted action:
complete CI verification, then freeze exact transform source/test SHA256 identities
before writing the nested analytical P10 runner. Do not load Jan-Jul before that freeze.


---

## 95. DEV030-P10 transform implementation frozen; final CI PASS

Scientific transform freeze commit:
`e46f36337a9f0cb5c6ba17136fec3e0c60f0edf7`

Frozen source:
`src/multimarket/dev030_p10_minirocket_transform.py`

Source SHA256:
`56071d2cde4a189b5e1d6711aff16139c315618192e13d13d38374a9a91f384f`

Focused transform test content SHA256:
`37323512adc9b5530fc8cb77cec0ec0585110696fa2fe949b5fd1db1e8554848`

Freeze-time pyproject SHA256:
`e90e4fa9ca05d241043e72bbc7467df7564ff14446b0d797586b4684001a0403`

Local canonical validation:
- Python 3.14.4
- NumPy 2.5.2
- scikit-learn 1.9.0
- pytest 7.4.3
- Numba 0.67.0
- llvmlite 0.49.0
- focused transform tests = 11 passed
- exact HEAD = scientific transform freeze commit
- dirty count = 0

Final CI-only head:
`73f3c401ee6df4ac2fea768f4e36b74b1924ec1d`

GitHub Actions run:
`33580590326`

Final CI:
- Python 3.10 legacy unit-tests = SUCCESS
- Python 3.12 legacy unit-tests = SUCCESS
- Python 3.14 canonical P10 transform job = SUCCESS

The P10 focused test file was moved from
`tests/test_dev030_p10_minirocket_transform.py`
to
`tests/p10_test_minirocket_transform.py`
only to keep legacy unittest discovery from importing the Numba-dependent pytest
module. Test content/semantics were unchanged.

Freeze doc:
`docs/DEV030_P10_TRANSFORM_FREEZE.md`

No Jan-Jul P10 analytical load occurred.
No P10 classifier fit occurred.
No P10 artifact exists.
No August/September or Railway storage was opened.

Current state:
`P10_TRANSFORM_IMPLEMENTATION_FROZEN_RUNNER_IMPLEMENTATION_PERMITTED`

Next permitted action:
write and synthetic-test the nested P10 analytical runner. Do not execute
canonical Jan-Jul P10 until the runner itself is frozen and local preflight passes.


---

## 96. DEV030-P10 nested runner implemented; CI synthetic/guard validation PASS

Nested analytical runner source:
`src/multimarket/dev030_p10_minirocket.py`

Runner implementation commit:
`b22e209b3ad2a252b79eba2e4e03c4149aabe404`

Runner guard test:
`tests/p10_test_minirocket_runner.py`

Runner-test commit:
`d21825e17a79f17a9947131aec7471decb0b980a`

Current tested implementation/CI head:
`94c74c98f2521c21db0b2a0680c9788ef40a00b1`

GitHub Actions run:
`33580838772`

Results:
- legacy unit-tests Python 3.10 = SUCCESS
- legacy unit-tests Python 3.12 = SUCCESS
- canonical P10 Python 3.14 transform + runner tests = 22 passed

Runner design implemented:
- exact P9 sequence extraction is reused and reshaped to [N,3,32];
- per-day P10 objects store exact C0 plus raw sequence only;
- C0 is refit through the frozen P9 path and must reproduce frozen P8 exactly;
- C1 MiniRocket parameters are fitted on inner-fit only for C selection;
- a separate MiniRocket fit is performed on full outer-train only for outer
  validation;
- validation sequence data never participates in transform parameter fitting;
- downstream C selection/scaling/logistic protocol remains P9 probability-first;
- C1 prediction hashes are P10-domain-separated;
- transform parameter hashes are recorded per inner/outer fold;
- P9 artifact SHA/status is a required invariant;
- P9 promotion gates are retained and pooled BA/macro-F1 non-regression gates
  are added;
- temporal null remains conditional on all prechecks;
- canonical output remains one-write-only.

Runner tests cover:
- frozen P9 artifact identity/status;
- feature-count geometry;
- synthetic provenance does not claim data opened;
- run-without-fit rejection;
- wrong P9 status/eligibility rejection;
- BA/macro-F1 gates;
- P10-specific prediction hashing;
- one-write output guards;
- canonical override rejection before any analytical loader.

No P10 Jan-Jul analytical data has been loaded.
No P10 scientific classifier fit has run.
No P10 canonical artifact exists.
No August/September or Railway storage has been opened.

Current state:
`P10_RUNNER_CI_PASS_LOCAL_PREFREEZE_VALIDATION_PENDING`

Next permitted action:
local Python 3.14 P10 environment must fetch the tested head and run both P10
test files, record runner source/test SHA256, confirm clean tree and output
absence. Do not run canonical Jan-Jul yet.


---

## 97. DEV030-P10 nested runner implementation frozen; final local preflight next

Scientific runner freeze commit:
`94c74c98f2521c21db0b2a0680c9788ef40a00b1`

Frozen identities:
- transform source SHA256 =
  `56071d2cde4a189b5e1d6711aff16139c315618192e13d13d38374a9a91f384f`
- runner source SHA256 =
  `83eb7d142fac8906d51bb5f3343fd17840f6ccfe6108d2a20244e849b50b67a5`
- transform test SHA256 =
  `37323512adc9b5530fc8cb77cec0ec0585110696fa2fe949b5fd1db1e8554848`
- runner test SHA256 =
  `69522ee7afd61b69e52b1ca5db7bbe7f5cc6c7c82a53d03dc5eef59a1949f984`
- pyproject SHA256 =
  `e90e4fa9ca05d241043e72bbc7467df7564ff14446b0d797586b4684001a0403`
- workflow SHA256 =
  `56c428553428443dbeb0f68d2aa585bf57c4152e97bbc0e62a27743de25dd851`

Local canonical P10 environment:
Python 3.14.4 / NumPy 2.5.2 / scikit-learn 1.9.0 /
pytest 7.4.3 / Numba 0.67.0 / llvmlite 0.49.0.

Local transform + runner suite:
22 passed; exit 0.

P9 artifact SHA invariant:
PASS.

P10 canonical output:
ABSENT.

GitHub Actions run `33580838772`:
- Python 3.10 legacy: 789 tests, OK
- Python 3.12 legacy: 789 tests, OK
- Python 3.14 P10: 22 passed

Freeze document:
`docs/DEV030_P10_RUNNER_FREEZE.md`

No Jan-Jul P10 analytical campaign has run.
No P10 artifact exists.
No forward/Railway storage has been opened.

Current state:
`P10_RUNNER_IMPLEMENTATION_FROZEN_FINAL_LOCAL_PREFLIGHT_PENDING`

Next permitted action:
read-only local final preflight on the exact scientific runner freeze commit.


---

## 98. DEV030-P10 final local preflight PASS; canonical one-shot authorized

Scientific execution commit:
`94c74c98f2521c21db0b2a0680c9788ef40a00b1`

Final local preflight results:
- exact HEAD = PASS
- worktree clean = PASS
- all frozen P10 source/test/project/workflow SHA256 identities = PASS
- runtime = Python 3.14.4 / NumPy 2.5.2 / scikit-learn 1.9.0 /
  pytest 7.4.3 / Numba 0.67.0 / llvmlite 0.49.0
- focused P10 transform + runner tests = 22 passed, exit 0
- frozen dependency gate = PASS
- P2C-P9 canonical artifact SHA256 identities/statuses = PASS
- prior protocol state = PASS
- Jan-Jul manifest = PASS, exactly 7 entries
- P10 frozen protocol = PASS
- model fit run = FALSE
- canonical P10 run = FALSE
- canonical P10 output absent = PASS
- git diff check = PASS
- final HEAD = PASS
- final worktree clean = PASS
- no Railway command executed

Canonical P10 output path remains absent:
`/home/emadh/Multi-Market/evidence/dev030_p10_price_minirocket_v1`

Status:
`P10_CANONICAL_ONE_SHOT_AUTHORIZED`

Only scientific execution commit
`94c74c98f2521c21db0b2a0680c9788ef40a00b1`
may be used for the canonical Jan-Jul P10 run.

After any P10 canonical artifact is created, DEV030-P10 MUST NOT be rerun
regardless of terminal PASS/FAIL status. If an exception occurs, inspect the
canonical output directory read-only before any rerun decision.

Storage/data boundary remains:
- Jan-Jul consumed development data only;
- no August/September;
- no market-raw-archive;
- no abundant-love;
- no Railway volume/bucket use.


---

## 99. DEV030-P10 canonical artifact created; terminal result inspection pending

Canonical scientific execution commit:
`94c74c98f2521c21db0b2a0680c9788ef40a00b1`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p10_price_minirocket_v1/DEV030_P10_PRICE_MINIROCKET_RESULT.json`

Artifact identity reported by the one-shot writer:
- SHA256:
  `10ff1d422d0a06cbe3a99de873ecbfab2d21a8881145ab4d7be0754a61c5c2e9`
- bytes:
  `23785`

The canonical writer returned normally:
`P10_CANONICAL_RUN_COMPLETE=TRUE`.

Critical rule now active:
- DEV030-P10 MUST NOT be rerun under any circumstance.
- The artifact is terminal and must be inspected read-only.
- Do not modify, delete, regenerate, or overwrite it.
- Do not use Railway, market-raw-archive, abundant-love, August, or September
  data to reinterpret or rescue this result.

At this point the internal scientific terminal status and metrics have not yet
been read from the canonical artifact in the chat. They must be recorded exactly
from the canonical JSON before assigning PASS/FAIL/eligible interpretation.

Current state:
`P10_CANONICAL_ARTIFACT_FROZEN_READ_ONLY_INSPECTION_PENDING`


---

## 100. DEV030-P10 terminal result frozen: FAIL_PRICE_MINIROCKET_NO_STABLE_INCREMENTAL_VALUE

Canonical scientific execution commit:
`94c74c98f2521c21db0b2a0680c9788ef40a00b1`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev030_p10_price_minirocket_v1/DEV030_P10_PRICE_MINIROCKET_RESULT.json`

Artifact SHA256:
`10ff1d422d0a06cbe3a99de873ecbfab2d21a8881145ab4d7be0754a61c5c2e9`

Artifact bytes:
`23785`

Environment:
- Python 3.14.4
- NumPy 2.5.2
- scikit-learn 1.9.0
- Numba 0.67.0
- llvmlite 0.49.0

Terminal status:
`FAIL_PRICE_MINIROCKET_NO_STABLE_INCREMENTAL_VALUE`

Eligibility:
`eligible_price_minirocket_incremental_information = false`

Support integrity:
- pooled support = 573
- LONG = 309
- SHORT = 264
- fold support = [159, 64, 126, 224]
- pooled support SHA256 =
  `8b30ba4544530043ebadd323cc40a70a44861a3f00a018dbc1cc9d70fc1ff59d`
- pooled label SHA256 =
  `8af5a70b6a3ff26d22be660809cc736a8cfc0d4a0d1c887a75ca66341cf97215`

P3 reproduction:
PASS exactly on all 4 folds.

C0 pooled:
- AUC = 0.536469059527312
- log loss = 0.7066614084396725
- Brier = 0.2553342216526328
- balanced accuracy = 0.5390188290673728
- macro-F1 = 0.5002901694399254

C1 pooled:
- AUC = 0.47317838579974497
- log loss = 0.9822853077050103
- Brier = 0.33855833379565753
- balanced accuracy = 0.4684466019417476
- macro-F1 = 0.46595394736842105

C1 vs C0:
- pooled AUC delta = -0.06329067372756708
- pooled log-loss improvement = -0.2756238992653378
- pooled Brier improvement = -0.08322411214302472
- fold AUC deltas =
  [-0.04921949665498565, -0.1416666666666666,
   -0.06515151515151524, -0.02833454077115022]
- fold log-loss improvements =
  [-0.2598592348603421, -0.3433304194348208,
   -0.30490672820152986, -0.25099768454920957]
- leave-one-fold-out AUC deltas =
  [-0.06693588148287283, -0.04575588599752162,
   -0.0605452111476209, -0.08546078237350752]
- leave-one-fold-out log-loss improvements =
  [-0.28167844429044486, -0.2671107022302751,
   -0.26736967902829045, -0.29142983650434295]

Fold-level C1 AUC:
- fold 1 = 0.4901242433896145
- fold 2 = 0.478125
- fold 3 = 0.4199494949494949
- fold 4 = 0.4994767769459873

Every fold worsened in both AUC and log loss relative to C0.
All four LOO AUC deltas were negative.
All four LOO log-loss improvements were negative.

Additional primary gates failed:
- pooled C1 AUC < 0.56;
- pooled AUC did not improve;
- pooled log loss worsened;
- pooled Brier worsened;
- pooled balanced accuracy regressed;
- pooled macro-F1 regressed;
- fewer than 3/4 C1 folds had AUC > 0.50.

Invariant-only gates passed:
- all invariants pass;
- exact P3 support pass;
- both classes receive nonzero probability each fold.

Therefore:
`TEMPORAL_NULL_NOT_RUN_PRECHECK_FAILED`
as preregistered.

Transform ledgers were recorded for all four folds and demonstrate distinct
chronologically nested inner/outer transform fits. No validation data was used
to fit MiniRocket parameters.

Scientific interpretation:
The final bounded PRICE-only sequence representation test failed decisively.
A deterministic 9,996-feature multivariate MiniRocket-style representation of
the 32-second sequence in spread_bps, microprice_minus_mid_bps, and
mid_log_return_250ms_bps degraded direction-given-touch discrimination,
probability quality, and thresholded classification relative to the frozen
23-feature PRICE summary baseline.

This result, together with P8 and P9, closes the Jan-Jul PRICE-only temporal
sequence-representation family on the consumed development data.

Do not collapse prior successes:
- EXP024-P1 remains a strong opportunity-ranking success;
- DEV030-P3 remains the frozen direction baseline success;
- DEV030-P4 touch-vs-none remains a component success despite failed composition.

Hard rule:
DEV030-P10 MUST NEVER BE RERUN.

Frozen stop rule now active:
- no more PRICE-only architecture shopping on Jan-Jul;
- no DeepLOB/TLOB/LSTM/Transformer/InceptionTime/TCN follow-up on the same
  consumed PRICE-only representation family;
- no new lag grids, kernel counts, seeds, calibration, thresholds, subsets,
  sessions, or PnL rescue;
- no OFI retry unless the representation is genuinely different and separately
  preregistered;
- no August/September holdout consumption merely to rescue P10.

Next scientifically permitted direction must be materially different, under a
new frozen protocol, such as:
1. event-time/depth-aware raw LOB information;
2. genuinely new information family not already represented in PRICE summaries;
3. a different first-passage target geometry justified before outcome inspection;
4. later forward confirmation only after a new mechanism is frozen on development
   data.

Runtime/prohibited-activity audit:
- Jan-Jul consumed development data only;
- no August/September forward data opened;
- no archive bucket opened;
- no abundant-love volume opened;
- no threshold optimization;
- no PnL/economic backtest;
- no opportunity-gate composition;
- no kernel-count search;
- no seed search;
- no lag search;
- no feature-family search;
- no calibration;
- no class weighting/resampling;
- no deep/alternate model family.

Current state:
`DEV030_P10_FROZEN_FAIL_PRICE_ONLY_SEQUENCE_FAMILY_CLOSED`


---

## 101. DEV031-P0 raw L2 event-time/depth audit preregistered and implemented

Branch:
`research/dev031-p0-event-depth-audit`

Research preregistration:
`docs/DEV031_P0_EVENT_DEPTH_RESEARCH.md`

Research commit:
`138a9070cb83f57b149f03c63ce3fb85c607a95d`

Frozen design:
`docs/DEV031_P0_EVENT_DEPTH_DESIGN.md`

Design commit:
`ed80cb43ea929c0fffdbdd75d6501c78a3d875a7`

Auditor source:
`src/multimarket/dev031_p0_event_depth_audit.py`

Implementation commit:
`7653bdb16e7eabf597ec9be4303e1199d7866ff5`

Synthetic guard tests:
`tests/dev031_p0_test_event_depth_audit.py`

Test commit:
`fc264eb4db961f0b8c8173adf4c7f4b3e6e7cdf5`

Current tested/CI-wired branch tip:
`30e9a9e1bb6bd8c5ea9b7ce1acba77a8bd649cca`

Scientific scope:
- BTCUSDT only;
- Jan-Jul consumed development raw `incremental_book_L2` only;
- no ETH;
- no trades;
- no Aug-01;
- no Aug-30;
- no Sep-01+;
- no Railway/archive/bucket access;
- no labels;
- no model;
- no predictive metrics;
- no PnL.

Why DEV031 is materially different:
existing Phase0DL reconstruction collapses raw L2 updates into a 250 ms grid and
preserves only best bid/ask, L1 quantities, L5/L10 depth totals, spread,
microprice, and OBI. Raw incremental L2 retains event timing, same-message
groups, price-level identity, amount-zero deletions, update ordering, and depth
information that is discarded by the 250 ms aggregate representation.

P0 PASS means only:
`raw event-time/depth information exists and is structurally auditable`.

P0 does not establish direction predictability or economic value.

Current state:
`DEV031_P0_IMPLEMENTED_SYNTHETIC_LOCAL_VALIDATION_PENDING`


---

## 102. DEV031-P0 synthetic preflight PASS; canonical raw-root unresolved

Synthetic preflight commit:
`30e9a9e1bb6bd8c5ea9b7ce1acba77a8bd649cca`

Local results:
- exact HEAD = `30e9a9e1bb6bd8c5ea9b7ce1acba77a8bd649cca`
- clean detached worktree
- synthetic tests = 6 passed
- test exit = 0

Frozen local identities:
- auditor source SHA256 =
  `243e45b30aca27302ff330254f3170a383e5a27b760418eb11eed849a0bfdaa6`
- auditor test SHA256 =
  `fab4897e03020c062fbef28ba6385681dcff14fbcafecc2979db3f48b77dcb45`
- research prereg SHA256 =
  `ab141ce5b42053f6db60626c1d04e6e8a5ca82654b49102eb971d339cff9ee83`
- design SHA256 =
  `830739fdbdfad64fa88fe5a47425eee29aa1baa702394f092b912b203816c978`

The repository-relative path:
`data/v23_phase0dl_l2_raw/incremental_book_L2/BTCUSDT`
was absent in the current worktree.

All seven frozen Jan-Jul exact file existence checks at that relative root were
FALSE.

This is NOT a scientific DEV031-P0 failure and no canonical P0 artifact exists.
No raw L2 content was read during this preflight.

Historical project provenance confirms Phase 0D-L used Tardis
`incremental_book_L2` with Jan-Jul development days and Aug-01 sealed
confirmation, and the original downloader defaulted to
`data/v23_phase0dl_l2_raw` relative to the execution location. Therefore the
next task is path-resolution only.

Current state:
`DEV031_P0_SYNTHETIC_PASS_RAW_ROOT_RESOLUTION_PENDING`

Canonical P0 run is prohibited until the exact local raw root is found and
frozen before reading raw content.

Path-resolution rules:
- metadata-only;
- probe exact Jan-Jul paths only;
- do not enumerate, stat, hash, or open Aug-01 or later;
- no downloads;
- no Railway/archive access;
- do not alter the scientific audit gates.


---

## 103. DEV031-P0 canonical raw root resolved; Jan-Jul existence PASS

Resolved canonical raw root:
`/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw/incremental_book_L2/BTCUSDT`

Path-binding implementation commit:
`8dac4bfd9140ca49309e4cc16377d9990c837647`

Exact metadata-only existence checks:
- 2026-01-01 = TRUE
- 2026-02-01 = TRUE
- 2026-03-01 = TRUE
- 2026-04-01 = TRUE
- 2026-05-01 = TRUE
- 2026-06-01 = TRUE
- 2026-07-01 = TRUE

Forward/storage guards during path resolution:
- Aug-01 not checked = TRUE
- Railway not used = TRUE

This is a path-resolution success only. No raw L2 content has yet been audited
under DEV031-P0, and no canonical DEV031-P0 artifact exists.

The change from the earlier repository-relative root to the resolved absolute
local root is path-only and does not alter scientific gates or measurements.

Current state:
`DEV031_P0_RAW_ROOT_RESOLVED_LOCAL_FREEZE_CHECK_PENDING`


---

## 104. DEV031-P0 invalidated pre-run; corrected DEV031-P0A opened

DEV031-P0 never opened raw L2 content and never created a canonical artifact.

Before canonical execution, two material audit-semantic weaknesses were found:
1. `book_initialization_feasible` did not reconstruct and validate a live book.
2. `distinct_prices_touched > 10` did not prove simultaneous live depth beyond top-10.

Therefore DEV031-P0 is preserved as:
`PRE_RUN_DESIGN_INVALIDATED`

This is not a scientific PASS/FAIL and consumed no raw-content evidence.

Corrected experiment:
`DEV031-P0A`

Branch:
`research/dev031-p0a-event-depth-audit`

Research preregistration:
`docs/DEV031_P0A_EVENT_DEPTH_RESEARCH.md`

Research commit:
`a6ff8b50ead0e4fb2ff0f7a52ccdee478c7c65ad`

Frozen corrected design:
`docs/DEV031_P0A_EVENT_DEPTH_DESIGN.md`

Design commit:
`1efd760e4d80d955963829c8de06eef7aab49d1a`

Corrected auditor:
`src/multimarket/dev031_p0a_event_depth_audit.py`

Implementation commit:
`8e20e3edc41af6c58d1ad30e839fe3c8d4d0f68e`

Corrected synthetic tests:
`tests/dev031_p0a_test_event_depth_audit.py`

Test commit:
`4c69e0caf27e2490ccc2a98ce5a6d5736eb3bd6a`

CI-wired head:
`69e6469bbe2510c3956f497f70716795b323a61d`

Corrected semantics:
- rows sharing local_timestamp are one atomic update group;
- snapshot group clears and rebuilds both sides;
- valid initialization requires nonempty bids/asks and best_bid < best_ask;
- crossed/empty state invalidates until next valid snapshot;
- live simultaneous bid/ask level counts are recorded;
- depth novelty requires min(bid_levels, ask_levels) >= 11 on every day;
- touched-price counts no longer satisfy the depth-novelty gate.

Scope remains unchanged:
BTCUSDT raw incremental_book_L2 Jan-Jul only, no labels/model/metrics/PnL,
no ETH/trades/Aug/Railway/archive.

Current state:
`DEV031_P0A_SYNTHETIC_VALIDATION_PENDING`


---

## 105. DEV031-P0A auditor implementation frozen

Scientific auditor freeze commit:
`69e6469bbe2510c3956f497f70716795b323a61d`

Frozen identities:
- source SHA256 =
  `405d76a88de41adeb90d72a34d0ce5e22e668a153ad9b814f30ee801609827e1`
- test SHA256 =
  `18eee5f0c397c57dc650cd169b5e4cab8f757bded877cbc6597b76a5f28caa9f`
- research SHA256 =
  `49d5f6970a21ee9b389a80af99a35e39765828de50d817e88f5ca7b95f718b32`
- design SHA256 =
  `564f270bb75d767b18d00145e0c23c62242c9dbe96e5536c13ea0778076c3ee5`

Local preflight:
- 6 passed
- protocol PASS
- output absent
- clean detached HEAD
- git diff check 0

CI:
- PR #3 dedicated `dev031-p0a-audit` job = SUCCESS
- 6 passed
- run = `33582791747`

Canonical raw root remains:
`/home/emadh/Multi-Market/data/v23_phase0dl_l2_raw/incremental_book_L2/BTCUSDT`

No raw L2 content has yet been consumed by DEV031-P0A.
No P0A canonical artifact exists.
No forward/Railway storage has been opened.

Current state:
`DEV031_P0A_AUDITOR_IMPLEMENTATION_FROZEN_CANONICAL_AUDIT_AUTHORIZED`


---

## 106. DEV031-P0A first execution attempt throughput-limited; no artifact

During the first canonical P0A execution attempt:
- PID = `1183001`;
- elapsed observation = approximately 12 minutes;
- CPU = approximately 99.9% of one logical CPU;
- machine = 24 logical CPUs;
- open raw file at observation = BTCUSDT `2026-02-01.csv.gz`;
- canonical P0A output directory = absent;
- canonical P0A artifact = absent.

No structural gate outcome had been produced or inspected.

A throughput-only implementation amendment was therefore made:
- exact same `audit_day()` semantics;
- seven independent Jan-Jul days run as seven worker processes;
- deterministic parent aggregation restored to frozen chronological day order;
- no gate/data/model/label change.

Parallel implementation commit:
`cc36e9e281a2be9d90ae5b9048c058bf3ed29970`

Worker semantic-equivalence test commit:
`df01c1e8b0166c122ac2230c03f09ff754a65e57`

The current single-process attempt must be terminated and output absence
reverified before any parallel run is authorized.

Current state:
`DEV031_P0A_SINGLE_PROCESS_ATTEMPT_ACTIVE_ABORT_REQUIRED_NO_ARTIFACT_OBSERVED`


---

## 107. DEV031-P0A single-process attempt aborted cleanly; optimized parallel candidate PASS CI

Single-process canonical attempt:
- execution commit = `69e6469bbe2510c3956f497f70716795b323a61d`
- observed CPU = ~99.9% of one logical CPU
- machine = 24 logical CPUs
- after ~15 minutes the process was still inside February
- SIGINT was sent intentionally
- traceback ended in `KeyboardInterrupt` inside `structurally_valid()`
- canonical artifact before abort = absent
- canonical artifact after abort = absent
- canonical output directory after abort = absent

Attempt status:
`ABORTED_THROUGHPUT_NO_ARTIFACT`

This is not a scientific PASS/FAIL and is not a rerun violation because no
canonical artifact existed.

Optimized implementation:
- seven independent day workers via `ProcessPoolExecutor`
- Linux multiprocessing context pinned to `fork`
- exact same `audit_day()` semantics per day
- chronological parent aggregation preserved
- best-bid/best-ask validity check optimized from repeated full-dictionary
  max/min scans to lazy heaps with identical price-level semantics
- no scientific gate, scope, input, or label/model rule changed

Optimized implementation commit:
`f0ede1614d41ba6a8447be05f8cb9a340e06b4ee`

Full seven-worker synthetic test commit / candidate head:
`fa3b6e50b13191c4a9d31a7c2a5909da84fe08f0`

CI run:
`33584102224`

Dedicated job:
`dev031-p0a-audit`

CI result:
- SUCCESS
- 8 passed in 0.45s

The 8-test suite includes:
- valid snapshot reconstruction;
- crossed snapshot rejection;
- forward guards;
- exact Jan-Jul scope;
- canonical override rejection;
- experiment identity;
- worker/direct audit equivalence;
- full seven-day parallel `run_p0a()` execution producing a synthetic PASS artifact.

No real Jan-Jul raw content was opened by CI.

Current state:
`DEV031_P0A_OPTIMIZED_PARALLEL_CANDIDATE_CI_PASS_LOCAL_FREEZE_CHECK_PENDING`


---

## 108. DEV031-P0A optimized parallel execution frozen; canonical audit authorized

Scientific execution freeze commit:
`fa3b6e50b13191c4a9d31a7c2a5909da84fe08f0`

Frozen identities:
- source SHA256 =
  `6f33d628bd0b736c6a68abefd75fe7d52ad38818a52b73ab02ed9b0e3e91cf8a`
- test SHA256 =
  `5eaf2acede99913755d6237453fb3981f1a504994cced49609cf3f355b90d60c`
- research SHA256 =
  `49d5f6970a21ee9b389a80af99a35e39765828de50d817e88f5ca7b95f718b32`
- design SHA256 =
  `564f270bb75d767b18d00145e0c23c62242c9dbe96e5536c13ea0778076c3ee5`

Local freeze check:
- 8 passed
- test exit 0
- protocol PASS
- output absent PASS
- clean tree
- git diff check 0

CI:
- run `33584102224`
- `dev031-p0a-audit` SUCCESS
- 8 passed

Execution:
- 7 independent day workers;
- fork multiprocessing context;
- heap-based best bid/ask maintenance;
- scientific semantics unchanged.

Earlier single-process attempt remains:
`ABORTED_THROUGHPUT_NO_ARTIFACT`

Current state:
`DEV031_P0A_OPTIMIZED_PARALLEL_IMPLEMENTATION_FROZEN_CANONICAL_AUDIT_AUTHORIZED`

Once a canonical artifact is created, DEV031-P0A must never be rerun.


---

## 109. DEV031-P0A canonical artifact created — NO RERUN

Canonical scientific execution commit:
`fa3b6e50b13191c4a9d31a7c2a5909da84fe08f0`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev031_p0a_event_depth_raw_l2_v1/DEV031_P0A_EVENT_DEPTH_RAW_L2_RESULT.json`

Artifact identity:
- SHA256 =
  `97f43dccd6a119867aced5de372121a87bc912c20b26b6f032333b761c82cc01`
- bytes = `11461`

Canonical run reported:
`DEV031_P0A_CANONICAL_RUN_COMPLETE=TRUE`

The run started from:
- HEAD =
  `fa3b6e50b13191c4a9d31a7c2a5909da84fe08f0`
- DIRTY_COUNT = `0`

From this point onward:
`DEV031-P0A MUST NEVER BE RERUN`

The artifact must not be modified, deleted, regenerated, overwritten, or replaced.

Scientific terminal status is still pending read-only artifact inspection.
No result interpretation has yet been recorded from artifact contents.

Current state:
`DEV031_P0A_CANONICAL_ARTIFACT_FROZEN_READ_ONLY_INSPECTION_PENDING`


---

## 110. DEV031-P0A terminal canonical result — PASS

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev031_p0a_event_depth_raw_l2_v1/DEV031_P0A_EVENT_DEPTH_RAW_L2_RESULT.json`

Artifact identity:
- SHA256 =
  `97f43dccd6a119867aced5de372121a87bc912c20b26b6f032333b761c82cc01`
- bytes = `11461`

Scientific execution commit:
`fa3b6e50b13191c4a9d31a7c2a5909da84fe08f0`

Official terminal status:
`DATA_READY_EVENT_DEPTH_RAW_L2`

Canonical pass:
`True`

Execution provenance:
- day_workers = 7
- parallelization = `process_per_day`
- scientific_semantics_changed = false
- errors = []
- all forward/storage guards = false

Global canonical evidence across the seven exact Jan-Jul development days:
- total raw L2 rows audited = 922,305,070
- total deletion rows = 119,709,360
- total snapshot groups = 45
- total valid reconstructed book groups after snapshot = 14,703,433
- bad rows = 0 on every day
- local timestamp regressions = 0 on every day
- book integrity invalidations = 0 on every day
- failed gates = NONE
- minimum daily max simultaneous minimum-side depth = 14,847 levels
- maximum daily max simultaneous minimum-side depth = 24,694 levels

Per-day max simultaneous minimum-side live depth:
- 2026-01-01 = 17,499
- 2026-02-01 = 19,755
- 2026-03-01 = 24,694
- 2026-04-01 = 20,511
- 2026-05-01 = 22,700
- 2026-06-01 = 20,437
- 2026-07-01 = 14,847

All seven days passed:
- file nonempty
- rows nonzero
- zero bad rows
- zero local timestamp regressions
- snapshot group present
- valid book initialized after snapshot
- post-valid-initialization incremental rows present
- deletions present
- multirow 250ms buckets present
- multigroup 250ms buckets present
- simultaneous depth beyond top-10 present
- within frozen scope

Scientific interpretation:
`raw event-time/depth information exists and is structurally auditable`

This PASS establishes only data-family feasibility and structural novelty relative
to the prior 250ms PRICE/top-depth summaries. It does NOT establish direction
predictability, ranking value, economic value, profitability, or forward
generalization.

The earlier single-process attempt remains:
`ABORTED_THROUGHPUT_NO_ARTIFACT`

DEV031-P0 remains:
`PRE_RUN_DESIGN_INVALIDATED`

From this point onward:
`DEV031-P0A MUST NEVER BE RERUN`

The canonical artifact must not be modified, deleted, regenerated, overwritten,
or replaced.

Current state:
`DEV031_P0A_FROZEN_PASS_EVENT_DEPTH_RAW_L2_DATA_READY`


---

## 111. DEV031-P1A event-depth materialization design frozen

Parent canonical result:
- DEV031-P0A = `DATA_READY_EVENT_DEPTH_RAW_L2`
- artifact SHA256 =
  `97f43dccd6a119867aced5de372121a87bc912c20b26b6f032333b761c82cc01`

Successful anchors explicitly retained:
- EXP024-P1 = `PASS_PROSPECTIVE_VOLATILITY_RANKING_CONFIRMED`
- DEV030-P3 selected directional survivor =
  `A / 120s / 16bp / 32s / PRICE / S1`
- DEV030-P4 touch-vs-none head success retained
- failed composition/nonlinear/OFI/PRICE-sequence experiments remain preserved

Important separation:
- EXP024 scores/ranks/thresholds are NOT used in P1A/P1B.
- P3 is the future P1B direction comparator.
- P4 touch-head composition is deferred until direction increment is tested.

DEV031-P1A branch:
`research/dev031-p1a-event-depth-materialization`

Research preregistration:
`docs/DEV031_P1A_EVENT_DEPTH_RESEARCH.md`

Research commit:
`e648238bdfff5f38911e7d25bca520e79a424e06`

Frozen design:
`docs/DEV031_P1A_EVENT_DEPTH_DESIGN.md`

Design commit:
`20bbcedda4f5fc9a6fc8b59714619d0acee2bea5`

P1A is materialization only:
- exact P3 selected T1 timestamps/labels;
- exact P3 23 PRICE S1 features retained;
- exactly 26 preregistered raw EVENT_DEPTH features;
- no model/predictive metrics/PnL;
- no Aug/Railway/archive data.

P1A PASS status:
`EVENT_DEPTH_EXACT_P3_SUPPORT_MATERIALIZED`

Current state:
`DEV031_P1A_IMPLEMENTATION_AUTHORIZED_SYNTHETIC_ONLY`


---

## 112. DEV031-P1A implementation + synthetic semantics CI PASS

Frozen design lineage:
- research preregistration commit =
  `e648238bdfff5f38911e7d25bca520e79a424e06`
- design commit =
  `20bbcedda4f5fc9a6fc8b59714619d0acee2bea5`
- event-validity clarification =
  `9f187e4ce09f2a74d37d20f9adacee237fa6d5ea`
- inclusive rolling-window clarification =
  `d3229799001ce2fcd946cb7d431ba89b0ab725db`

Implementation files:
- `src/multimarket/dev031_p1a_event_depth_materialize.py`
- `tools/dev031_p1a_event_depth.cpp`
- `tests/test_dev031_p1a_event_depth_materialize.py`

Key implementation commits:
- sparse C++ extractor =
  `f0cd6e661938d6f4ed2923dcf2d9112384c352b5`
- Python orchestrator =
  `868051ba047ed26c9d03ab3f5ada725bd022b549`
- synthetic/known-value tests =
  `54f7df82b9ad0879173f6e5913bdeb35db3187d7`
- remove modeling/sklearn dependency =
  `96bf50bc552b248d88d022ef8ad3161eca7657c3`
- C++ typing fix / scientific code head =
  `3fa0e4bae8bbb9b839e8845dbcc393c8039e370d`

CI:
- PR #4
- run = `33586069809`
- `dev031-p1a-materialization` = SUCCESS
- focused suite = 7 passed in 2.56s
- full unit-tests Python 3.10 = SUCCESS
- full unit-tests Python 3.12 = SUCCESS
- P0 regression = SUCCESS
- P0A regression = SUCCESS
- P10 transform regression = SUCCESS

CI synthetic test includes a hand-checkable raw-L2 fixture proving:
- valid deep-book reconstruction;
- exact L20/L50 imbalance;
- exact L10/L50 concentration;
- exact 50bp-only flow contribution;
- ask deletion upward pressure;
- bid replenishment upward pressure;
- exact raw update/group intensity.

Scientific implementation properties:
- exact P3 selected configuration only:
  A / 120s / 16bp / 32s / PRICE
- reconstructs exact frozen P3 T1 support contract using DEV030 dataset code;
- compares the complete reconstructed support contract with frozen P3 artifact;
- preserves the 23 P3 PRICE S1 features;
- extracts exactly 26 EVENT_DEPTH features;
- raw hashing against frozen P0A identities before extraction;
- day-by-day P3 support reconstruction to avoid unnecessary memory use;
- seven sparse C++ raw-day extractors can run in parallel;
- no scikit-learn/model dependency in P1A;
- no predictive metric;
- no EXP024 filter/score;
- no P4 composition;
- no PnL;
- no forward/Railway/archive data.

The docs-only clarification at `d322979...` is a descendant of the fully
tested scientific code head `3fa0e4b...` and changes no source/test bytes.

Current state:
`DEV031_P1A_CI_PASS_LOCAL_FREEZE_CHECK_PENDING`

No real P1A materialization has run yet.
No canonical P1A output/artifact exists.


---

## 112. DEV031-P1A implementation candidate passes CI; local freeze check pending

Frozen design remains:
`docs/DEV031_P1A_EVENT_DEPTH_DESIGN.md`

Latest implementation candidate:
`96881948a363c259b836c319ddf5ca5b04a66730`

Implementation files:
- `tools/dev031_p1a_event_depth.cpp`
- `src/multimarket/dev031_p1a_event_depth_materialize.py`
- `tests/test_dev031_p1a_event_depth_materialize.py`

Implementation architecture:
- sparse C++ raw-L2 extractor;
- exact frozen P3 selected T1 support only;
- 26 preregistered EVENT_DEPTH features;
- seven independent day extraction jobs;
- Python orchestration for P0A/P2C/P3 provenance, support/label reconciliation,
  deterministic hashes, and write-once materialization;
- no predictive metric/model/PnL.

Important fixed semantics:
- non-snapshot event-flow/count features use only groups with a valid ready book
  immediately before the group;
- snapshot groups reset/rebuild state and never enter rolling event statistics;
- static deep-book state uses the valid post-group book at decision time.

CI:
- PR #4
- workflow run = `33586313560`
- dedicated job = `dev031-p1a-materialization`
- result = SUCCESS
- focused tests = 7 passed in 5.45s
- p10-transform = SUCCESS
- dev031-p0-audit = SUCCESS
- dev031-p0a-audit = SUCCESS
- unit-tests Python 3.10 = SUCCESS
- unit-tests Python 3.12 = SUCCESS

The initial P1A CI failure was collection-only:
`ModuleNotFoundError: No module named 'sklearn'`.
No P1A test or scientific assertion had executed.
It was fixed by installing the already-required scikit-learn dependency in the
dedicated P1A CI job only; no scientific design/source semantics changed.

No real Jan-Jul raw P1A materialization has run.

Current state:
`DEV031_P1A_IMPLEMENTATION_CI_PASS_LOCAL_SYNTHETIC_FREEZE_CHECK_PENDING`


---

## 113. DEV031-P1A local freeze check — focused PASS; known post-P3 state test requires established isolated recheck

Local validation at scientific candidate:
`96881948a363c259b836c319ddf5ca5b04a66730`

Focused P1A:
- 7 passed in 2.72s
- P1A_TEST_EXIT = 0
- P1A_PROTOCOL = PASS
- P1A_OUTPUT_ABSENT = PASS
- DIRTY_COUNT = 0
- git diff check = 0

Local candidate identities:
- `tools/dev031_p1a_event_depth.cpp`
  SHA256 =
  `a7d9db4594caea6ec67255d80ce29fb8ce1370ea7f3aecac3056a47667a9c437`
- `src/multimarket/dev031_p1a_event_depth_materialize.py`
  SHA256 =
  `8f29133a1b2663c5dc3f00ed42d11e84bbd9e979359dc5001b5c71ff7868b44b`
- `tests/test_dev031_p1a_event_depth_materialize.py`
  SHA256 =
  `2bb1afe0a6241274bea861d5abe5dbb9cd8a8d81ddbb6da97d0c73e9048bc862`
- research SHA256 =
  `54c222b1a1a0b60c72781d80848a4da1ad35b3482edbcc14a08910041a070721`
- design SHA256 =
  `f5c566ee58feb8aeb24bf1c82c6c6ddcf64b1a4c4ab0e0886b13c98b9c94c89e`

Combined regression command produced:
- 199 passed
- 1 failed
- REGRESSION_EXIT = 1

The sole failure is the already-documented post-P3 environment-state test:
`test_real_output_cannot_enter_synthetic_mode`

Observed result:
`output_directory_already_exists`
instead of:
`canonical_output_requires_real_mode`

This is expected after the frozen canonical P3 output directory permanently
exists. It is not a P1A/P3 scientific regression.

Established project procedure from §§50–51 remains authoritative:
- do not edit frozen P3 source/test bytes;
- rerun P3 excluding only this environment-state-dependent test;
- separately revalidate the synthetic-mode guard in an isolated temporary
  canonical path by monkeypatching the module constant in memory only;
- verify frozen P3 source/test SHA256.

P1A is NOT yet frozen for real materialization until that isolated recheck and
the corrected regression command pass locally.

Current state:
`DEV031_P1A_FOCUSED_LOCAL_PASS_KNOWN_P3_STATE_RECHECK_PENDING`


---

## 114. DEV031-P1A implementation frozen; canonical materialization authorized

Scientific execution freeze commit:
`96881948a363c259b836c319ddf5ca5b04a66730`

Frozen identities:
- C++ extractor SHA256 =
  `a7d9db4594caea6ec67255d80ce29fb8ce1370ea7f3aecac3056a47667a9c437`
- Python materializer SHA256 =
  `8f29133a1b2663c5dc3f00ed42d11e84bbd9e979359dc5001b5c71ff7868b44b`
- P1A test SHA256 =
  `2bb1afe0a6241274bea861d5abe5dbb9cd8a8d81ddbb6da97d0c73e9048bc862`
- research SHA256 =
  `54c222b1a1a0b60c72781d80848a4da1ad35b3482edbcc14a08910041a070721`
- design SHA256 =
  `f5c566ee58feb8aeb24bf1c82c6c6ddcf64b1a4c4ab0e0886b13c98b9c94c89e`

Final local validation:
- focused P1A = 7 passed
- P3 regression = 49 passed, 1 established state-dependent test deselected
- isolated P3 guard = PASS
- other frozen regressions = 189 passed
- frozen P3 source/test hashes = exact
- P1A canonical output = absent
- worktree = clean
- git diff check = 0

CI:
- PR #4
- run `33586313560`
- dedicated P1A job = SUCCESS
- 7 passed
- all companion regression jobs = SUCCESS

Success inheritance remains explicit:
- EXP024-P1 ranking success is preserved but not used as P1A/P1B filter/feature;
- DEV030-P3 is preserved as the future P1B directional baseline;
- DEV030-P4 touch-head success is preserved for later separately frozen
  composition work;
- prior failures remain preserved and continue to constrain search.

Current state:
`DEV031_P1A_IMPLEMENTATION_FROZEN_CANONICAL_MATERIALIZATION_AUTHORIZED`

Canonical P1A may now execute once from `96881948...`.
Once a valid canonical manifest exists: NO RERUN.


---

## 115. DEV031-P1A first canonical attempt aborted at frozen P3 provenance schema check

First canonical P1A attempt used scientific execution commit:
`96881948a363c259b836c319ddf5ca5b04a66730`

The run stopped inside:
`verify_artifacts()`

Observed exception:
`P1AMaterializationError: p3_selected_candidate_mismatch`

Observed frozen P3 selected-candidate object:
`{"block":"PRICE","target":{"barrier_bps":16,"horizon_seconds":120,"target_id":"A"},"window_seconds":32}`

Root cause:
- P1A provenance adapter expected a flat P3 candidate schema;
- frozen P3 serializes candidate identity using nested `target`, exactly as
  `dev030_p3_direction._public_spec()` defines.

Scientific/data impact:
- the attempt stopped before `verify_raw_manifest_against_p0a()`;
- no P1A raw Jan-Jul L2 file was opened by the materializer;
- no C++ extractor was launched;
- no P1A event/depth feature was materialized;
- no model/predictive metric/PnL ran;
- no canonical P1A output directory or artifact was created.

Attempt status:
`ABORTED_PROVENANCE_SCHEMA_NO_RAW_NO_ARTIFACT`

This is not a scientific PASS/FAIL and not a rerun violation.

Schema-only implementation correction:
- source commit =
  `36f219a85ca8d88d7ceb56c058f764c81bab8b95`
- nested-schema regression test commit =
  `dbcde61b378bdc9f2533ac21af72632651a52df2`

No feature definition, target, support rule, fold, gate, scope, or forward-data
boundary changed.

Current state:
`DEV031_P1A_SCHEMA_ADAPTER_FIXED_CI_PENDING`


---

## 116. DEV031-P1A nested P3 schema fix passes CI; new local freeze check required

Corrected scientific candidate:
`dbcde61b378bdc9f2533ac21af72632651a52df2`

Changes from the aborted `96881948...` candidate are schema/provenance-only:
- accept frozen P3 selected candidate in the canonical nested `target` form;
- locate the selected trial-ledger entry using the same nested schema;
- add a regression test reproducing the real frozen P3 schema.

No feature, target, label, support, fold, gate, data scope, or forward-data rule changed.

CI run:
`33620587030`

Results:
- `dev031-p1a-materialization` = SUCCESS
- focused P1A tests = 8 passed in 2.07s
- unit-tests Python 3.10 = SUCCESS
- unit-tests Python 3.12 = SUCCESS
- dev031-p0-audit = SUCCESS
- dev031-p0a-audit = SUCCESS
- p10-transform = SUCCESS

No real P1A raw materialization occurred in CI.

The earlier execution attempt remains:
`ABORTED_PROVENANCE_SCHEMA_NO_RAW_NO_ARTIFACT`

Current state:
`DEV031_P1A_SCHEMA_FIXED_CI_PASS_LOCAL_FREEZE_CHECK_REQUIRED`


---

## 117. DEV031-P1A schema-fixed implementation frozen; canonical materialization authorized

Scientific execution freeze commit:
`dbcde61b378bdc9f2533ac21af72632651a52df2`

This supersedes `96881948...` for execution only.
The earlier attempt remains:
`ABORTED_PROVENANCE_SCHEMA_NO_RAW_NO_ARTIFACT`.

Frozen identities:
- C++ extractor SHA256 =
  `a7d9db4594caea6ec67255d80ce29fb8ce1370ea7f3aecac3056a47667a9c437`
- Python materializer SHA256 =
  `4978de8c9258ecfa768ce69ad0b7c9769c796f6e5d68f284a3740a30365bc124`
- test SHA256 =
  `dbb1feca4f1eb4012fb77ae90e9d98ab1ea04b5d5b256f07435dbc7e16bc0dc8`
- research SHA256 =
  `54c222b1a1a0b60c72781d80848a4da1ad35b3482edbcc14a08910041a070721`
- design SHA256 =
  `f5c566ee58feb8aeb24bf1c82c6c6ddcf64b1a4c4ab0e0886b13c98b9c94c89e`

Local freeze:
- 8 focused tests passed
- real P0A/P2C/P3 provenance schema precheck PASS
- exact nested P3 selected trial found
- canonical P1A output absent
- clean tree
- git diff check 0

CI:
- run `33620587030`
- focused P1A 8 passed
- all companion jobs SUCCESS

Current state:
`DEV031_P1A_SCHEMA_FIXED_IMPLEMENTATION_FROZEN_CANONICAL_MATERIALIZATION_AUTHORIZED`

Canonical execution must use exactly `dbcde61b...`.
After a valid manifest exists: NO RERUN.


---

## 118. DEV031-P1A canonical materialization artifact created — NO RERUN

Scientific execution commit:
`dbcde61b378bdc9f2533ac21af72632651a52df2`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev031_p1a_event_depth_materialization_v1/DEV031_P1A_EVENT_DEPTH_MATERIALIZATION.json`

Artifact identity:
- SHA256 =
  `a8a4f89262b9f01e76fc10a1b9c54ac28dd7faec3180a1a0fac19499eb9467d8`
- bytes = `21803`

Canonical run reported:
`DEV031_P1A_CANONICAL_RUN_COMPLETE=TRUE`

Run start state:
- HEAD =
  `dbcde61b378bdc9f2533ac21af72632651a52df2`
- DIRTY_COUNT = `0`

From this point onward:
`DEV031-P1A MUST NEVER BE RERUN`

The canonical manifest and day artifacts must not be modified, regenerated,
overwritten, deleted, or replaced.

The earlier pre-raw attempt remains preserved as:
`ABORTED_PROVENANCE_SCHEMA_NO_RAW_NO_ARTIFACT`

Scientific terminal interpretation remains pending read-only inspection of the
frozen manifest.

Current state:
`DEV031_P1A_CANONICAL_ARTIFACT_FROZEN_READ_ONLY_INSPECTION_PENDING`


---

## 119. DEV031-P1A terminal canonical result — PASS

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev031_p1a_event_depth_materialization_v1/DEV031_P1A_EVENT_DEPTH_MATERIALIZATION.json`

Artifact identity:
- SHA256 =
  `a8a4f89262b9f01e76fc10a1b9c54ac28dd7faec3180a1a0fac19499eb9467d8`
- bytes = `21803`

Scientific execution commit:
`dbcde61b378bdc9f2533ac21af72632651a52df2`

Official terminal status:
`EVENT_DEPTH_EXACT_P3_SUPPORT_MATERIALIZED`

Canonical pass:
`True`

Read-only verification:
- experiment_id = `DEV031-P1A`
- design_version = `event-depth-materialization-v1`
- P3 support contract reproduced exactly = true
- frozen P3 PRICE features = 23
- preregistered EVENT_DEPTH features = 26
- future P1B augmented feature count = 49
- failed invariants = NONE
- all seven day file SHA256/byte checks = PASS
- all forward/activity guards = false

Exact T1 support across Jan-Jul:
- total = 1,374
- LONG = 684
- SHORT = 690

Per-day T1 support:
- Jan = 4 (3 LONG / 1 SHORT)
- Feb = 435 (210 / 225)
- Mar = 362 (162 / 200)
- Apr = 159 (86 / 73)
- May = 64 (40 / 24)
- Jun = 126 (60 / 66)
- Jul = 224 (123 / 101)

Frozen expanding folds:
- Fold 1 train Jan-Mar = 801; validation Apr = 159
- Fold 2 train Jan-Apr = 960; validation May = 64
- Fold 3 train Jan-May = 1,024; validation Jun = 126
- Fold 4 train Jan-Jun = 1,150; validation Jul = 224

All raw extractor stderr summaries reported:
- bad_rows = 0
- support emitted exactly equals requested support on every day

Canonical dependencies reverified:
- P0A artifact SHA256 =
  `97f43dccd6a119867aced5de372121a87bc912c20b26b6f032333b761c82cc01`
- P2C artifact SHA256 =
  `a7018684343ff771df3f31ff140b65df8f072c6659549f8af1d85747ffd1fed0`
- P3 artifact SHA256 =
  `f83fb917948835e0680a1851edf16f9107feee50ba246f2263d2652ff17d817e`
- C++ extractor SHA256 =
  `a7d9db4594caea6ec67255d80ce29fb8ce1370ea7f3aecac3056a47667a9c437`

Scientific interpretation:
The preregistered raw event-time/deep-depth family is now materialized on the
exact frozen P3 T1 support with no support shrink and no label change.

This is a representation/materialization PASS only. It does NOT establish
incremental predictive value, profitability, deployability, or forward
generalization.

Permanent rule:
`DEV031-P1A MUST NEVER BE RERUN`

Next scientific stage:
open separately preregistered `DEV031-P1B` to test incremental directional
value of the fixed 26-feature EVENT_DEPTH block above the exact frozen P3 PRICE
baseline, still on consumed Jan-Jul only.

EXP024-P1 ranking success remains preserved but must not be used as a filter,
feature, threshold, or rescue in P1B.
DEV030-P4 touch-head success also remains preserved for a later separately
frozen composition stage.

Current state:
`DEV031_P1A_FROZEN_PASS_P1B_DESIGN_AUTHORIZED`


---

## 120. DEV031-P1B incremental event/depth direction design frozen

Parent:
- DEV031-P1A = `EVENT_DEPTH_EXACT_P3_SUPPORT_MATERIALIZED`
- P1A artifact SHA256 =
  `a8a4f89262b9f01e76fc10a1b9c54ac28dd7faec3180a1a0fac19499eb9467d8`

Branch:
`research/dev031-p1b-event-depth-incremental`

Research preregistration:
`docs/DEV031_P1B_EVENT_DEPTH_RESEARCH.md`
commit:
`1d8613b5d7d924e6faae7546f78bc9a90cf31bb4`

Frozen design:
`docs/DEV031_P1B_EVENT_DEPTH_DESIGN.md`
commit:
`0d453e9858ba12c093a2c553463df28f7732daa5`

Primary comparison:
- C0 = exact frozen P3 PRICE23
- C1 = PRICE23 + frozen EVENT_DEPTH26 = 49 features
- exact same 1,374 T1 rows
- exact same four expanding folds
- StandardScaler(train-only) + L2 logistic regression
- C grid [0.01, 0.1, 1.0, 10.0]
- probability-first inner selection
- log loss/Brier/AUC primary
- temporal null only after strict precheck
- no threshold optimization
- no EXP024 filter/feature
- no P4 composition
- no PnL
- no raw L2 reopening
- no forward data

Terminal statuses:
- `FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE`
- `FAIL_EVENT_DEPTH_DIRECTION_TEMPORAL_NULL`
- `ELIGIBLE_EVENT_DEPTH_INCREMENTAL_DIRECTION_INFORMATION`

Current state:
`DEV031_P1B_IMPLEMENTATION_AUTHORIZED_SYNTHETIC_ONLY`


---

## 121. DEV031-P1B implementation candidate passes CI; local freeze check pending

Implementation candidate:
`a6cf7a3c448cbb745de8a15ca6d2d33169628b2c`

Implementation source:
`src/multimarket/dev031_p1b_event_depth_incremental.py`

Source implementation commit:
`24dcf47e6e2b54f9d961687f5deb0c28c65efa5b`

Focused synthetic test:
`tests/test_dev031_p1b_event_depth_incremental.py`

Test commit:
`1e1c2106d92b27f0a3eaca0fb46255124dbfaca3`

CI wiring commit:
`a6cf7a3c448cbb745de8a15ca6d2d33169628b2c`

CI:
- PR #5
- workflow run = `33621896878`
- `dev031-p1b-incremental` = SUCCESS
- focused P1B = 8 passed in 3.05s
- dev031-p1a-materialization = SUCCESS
- dev031-p0-audit = SUCCESS
- dev031-p0a-audit = SUCCESS
- p10-transform = SUCCESS
- unit-tests Python 3.10 = SUCCESS
- unit-tests Python 3.12 = SUCCESS

P1B implementation behavior:
- reads only frozen P1A manifest/day CSV artifacts;
- verifies frozen P1A artifact identity;
- verifies frozen P3 artifact identity and P1A->P3 provenance;
- reproduces frozen P3 PRICE23 OOF prediction hashes before comparison;
- C0 = PRICE23;
- C1 = PRICE23 + EVENT_DEPTH26 = 49;
- identical support and labels;
- same four chronological folds;
- train-only StandardScaler + L2 logistic;
- probability-first chronological inner C selection;
- paired log-loss/Brier/AUC deltas;
- leave-one-fold-out stability;
- paired day-local temporal-label null only after strict precheck;
- no raw L2 reopening;
- no EXP024 filtering;
- no P4 composition;
- no threshold tuning;
- no PnL.

No real P1B fit has run.

Current state:
`DEV031_P1B_IMPLEMENTATION_CI_PASS_LOCAL_SYNTHETIC_FREEZE_CHECK_PENDING`


---

## 122. DEV031-P1B local freeze validation scientifically PASS; only local build cache cleanup pending

Candidate:
`a6cf7a3c448cbb745de8a15ca6d2d33169628b2c`

Local validation:
- focused P1B = 8 passed in 3.28s
- P1B_TEST_EXIT = 0
- P1B_PROTOCOL = PASS
- P1A status = `EVENT_DEPTH_EXACT_P3_SUPPORT_MATERIALIZED`
- P1A support exact = true
- total T1 = 1,374
- LONG = 684
- SHORT = 690
- every day C0 shape = rows x 23
- every day C1 shape = rows x 49
- P1B real-input precheck = PASS

Frozen P3 reproduction from P1A PRICE23:
- overall = PASS
- Fold 1 actual prediction SHA256 exactly matches
  `e03d233bff936b49a0452994497f32ca5ecbe52c1f490d855fe8d06dbfa9dcf4`
- Fold 2 exactly matches
  `cd2cba0a6dcf3591ec9848b78e31aef796dad15d371bbecb8517aa2507340bdd`
- Fold 3 exactly matches
  `19f9acf70b0065a307c0373952cad350339768607a156c9307e5192503bb1f31`
- Fold 4 exactly matches
  `b05ee6e926d6a943e1fc89828eb3801af0863fa270bc2e5db5ed7cd93e9a4b66`

Canonical P1B output:
- absent = PASS

Frozen candidate file identities:
- source SHA256 =
  `46e2753744fc02385cd70162fab5ae19a094eac768fd0b708fc077ecebb2c578`
- test SHA256 =
  `ad3b1def838f3fab7797b782a5ef91d3a7a862020e51f90ffcc1dcb30ddb1a68`
- research SHA256 =
  `e327c18c536c88ad5ab77b0f98beeec9ee105554dd521f5a211868068ef40893`
- design SHA256 =
  `d40f7852f6b13edc329535ef437c22e6fad1e549eaa7a41ee400de8c769299e6`

Final tree state:
- HEAD = candidate
- git diff check = 0
- DIRTY_COUNT = 1 only because untracked `.build/`

`.build/` is a generated local compilation/cache directory from earlier
development tooling. It is not a scientific source, frozen input, canonical
artifact, or evidence directory.

No code or data correction is required.

Required final action before freeze:
delete only the untracked local `.build/` directory and verify clean worktree.

Current state:
`DEV031_P1B_SCIENTIFIC_FREEZE_CHECK_PASS_LOCAL_BUILD_CACHE_CLEANUP_PENDING`


---

## 123. DEV031-P1B implementation frozen; canonical fit authorized

Scientific execution freeze commit:
`a6cf7a3c448cbb745de8a15ca6d2d33169628b2c`

Frozen identities:
- source SHA256 =
  `46e2753744fc02385cd70162fab5ae19a094eac768fd0b708fc077ecebb2c578`
- test SHA256 =
  `ad3b1def838f3fab7797b782a5ef91d3a7a862020e51f90ffcc1dcb30ddb1a68`
- research SHA256 =
  `e327c18c536c88ad5ab77b0f98beeec9ee105554dd521f5a211868068ef40893`
- design SHA256 =
  `d40f7852f6b13edc329535ef437c22e6fad1e549eaa7a41ee400de8c769299e6`

Final local freeze:
- 8 focused P1B tests PASS
- P1A real-input precheck PASS
- exact 1,374-row support
- frozen P3 reproduction PASS hash-for-hash across all four folds
- canonical output absent
- clean detached tree
- git diff check 0

CI:
- PR #5
- run `33621896878`
- all jobs SUCCESS

Primary frozen test:
- C0 = PRICE23
- C1 = PRICE23 + EVENT_DEPTH26 = 49
- same support/folds/model family
- probability-first
- strict precheck then temporal null
- no EXP024 filtering
- no P4 composition
- no PnL
- no raw L2 reopening

Current state:
`DEV031_P1B_IMPLEMENTATION_FROZEN_CANONICAL_FIT_AUTHORIZED`

Canonical execution must use exactly `a6cf7a3c...`.
After a valid result artifact exists: NO RERUN.


---

## 124. DEV031-P1B canonical result artifact created — NO RERUN

Scientific execution commit:
`a6cf7a3c448cbb745de8a15ca6d2d33169628b2c`

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev031_p1b_event_depth_incremental_v1/DEV031_P1B_EVENT_DEPTH_INCREMENTAL_RESULT.json`

Artifact identity:
- SHA256 =
  `4e55554151b8caba588ea2ffdf7c6b1454a5eabe74f833a44f3784a980ddb56b`
- bytes = `14796`

Canonical run reported:
`DEV031_P1B_CANONICAL_RUN_COMPLETE=TRUE`

Run start state:
- HEAD =
  `a6cf7a3c448cbb745de8a15ca6d2d33169628b2c`
- DIRTY_COUNT = `0`

From this point onward:
`DEV031-P1B MUST NEVER BE RERUN`

The canonical artifact must not be modified, regenerated, overwritten, deleted,
or replaced.

Scientific terminal status is pending read-only inspection only.

Current state:
`DEV031_P1B_CANONICAL_ARTIFACT_FROZEN_READ_ONLY_INSPECTION_PENDING`


---

## 125. DEV031-P1B terminal canonical result — FAIL with preserved ranking signal

Canonical artifact:
`/home/emadh/Multi-Market/evidence/dev031_p1b_event_depth_incremental_v1/DEV031_P1B_EVENT_DEPTH_INCREMENTAL_RESULT.json`

Artifact identity:
- SHA256 =
  `4e55554151b8caba588ea2ffdf7c6b1454a5eabe74f833a44f3784a980ddb56b`
- bytes = `14796`

Scientific execution commit:
`a6cf7a3c448cbb745de8a15ca6d2d33169628b2c`

Official terminal status:
`FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE`

Read-only verification:
- P3 reproduction = PASS
- all four frozen P3 OOF prediction hashes reproduced exactly
- forward/activity guards all false
- temporal null = NOT_RUN_PRECHECK_FAILED
- canonical artifact = frozen
- NO RERUN

### Primary C0 vs C1 pooled metrics

C0 = frozen PRICE23:
- log loss = 0.7066614084
- Brier = 0.2553342217
- ROC AUC = 0.5364690595
- balanced accuracy = 0.5390188291
- macro F1 = 0.5002901694

C1 = PRICE23 + EVENT_DEPTH26:
- log loss = 0.7344602724
- Brier = 0.2597066443
- ROC AUC = 0.5764930862
- balanced accuracy = 0.5749485143
- macro F1 = 0.5685096264

Primary pooled deltas:
- log-loss improvement = -0.0277988640
- Brier improvement = -0.0043724226
- AUC delta = +0.0400240267

### Fold behavior

Fold 1:
- log-loss improvement = +0.0076400826
- Brier improvement = +0.0038708393
- AUC delta = +0.0477859191

Fold 2:
- log-loss improvement = +0.0516846860
- Brier improvement = +0.0258451342
- AUC delta = +0.0697916667

Fold 3:
- log-loss improvement = -0.0998934663
- Brier improvement = -0.0361741705
- AUC delta = -0.0174242424

Fold 4:
- log-loss improvement = -0.0351105595
- Brier improvement = -0.0009687711
- AUC delta = +0.0528857764

Leave-one-fold-out deltas:
- log-loss improvement =
  [-0.0414094739, -0.0377928663, -0.0074768955, -0.0231059705]
- Brier improvement =
  [-0.0075383131, -0.0081718797, +0.0045918285, -0.0065570013]
- AUC delta =
  [+0.0420961191, +0.0383519207, +0.0450894487, +0.0327528201]

### Failed preregistered gates

- at_least_3_of_4_fold_brier_improve = false
- at_least_3_of_4_fold_log_loss_improve = false
- loo_brier_positive = false
- loo_log_loss_positive = false
- pooled_brier_better = false
- pooled_log_loss_better = false

Passed ranking-related gates:
- pooled_auc_better = true
- pooled_c1_auc_at_least_056 = true
- at_least_3_of_4_fold_auc_improve = true
- at_least_3_of_4_fold_c1_auc_gt_050 = true
- loo_auc_positive = true
- probability_noncollapsed = true

### Scientific interpretation

P1B does NOT establish stable incremental directional probability information
because pooled and stability probability-quality gates failed.

However, the result contains a real partial success that must be preserved:
the fixed EVENT_DEPTH block improved directional ranking materially:
- pooled AUC +0.0400;
- C1 pooled AUC = 0.57649;
- AUC improved in 3/4 folds;
- every leave-one-fold-out pooled AUC delta remained positive.

Therefore:
- P1B remains an official FAIL;
- the ranking improvement is hypothesis-generating evidence, not a promoted
  claim;
- no P1B feature subset/calibration/threshold/model rescue is allowed;
- temporal null was correctly not run because the preregistered probability
  precheck failed;
- any ranking-specific follow-up must use a new experiment ID and must not
  retroactively convert P1B to PASS.

Permanent rule:
`DEV031-P1B MUST NEVER BE RERUN`

Current state:
`DEV031_P1B_FROZEN_FAIL_WITH_DIRECTION_RANKING_SIGNAL_PRESERVED`


---

## 126. DEV031-P2A forward archive metadata audit design frozen

Parent result:
- DEV031-P1B =
  `FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE`
- preserved hypothesis-generating ranking signal:
  pooled AUC +0.040024 to 0.576493,
  3/4 fold AUC improvements,
  all leave-one-fold-out AUC deltas positive.

P1B remains an official FAIL and must never be rerun.

P2A branch:
`research/dev031-p2a-forward-archive-audit`

Research preregistration:
`docs/DEV031_P2A_FORWARD_ARCHIVE_RESEARCH.md`

Research commit:
`50b3c7da1a85b77b94ec5c449a0789e32fc88725`

Frozen design:
`docs/DEV031_P2A_FORWARD_ARCHIVE_DESIGN.md`

Design commit:
`416b0f7a71a2fa08a9bb051a5b3695b79567b455`

P2A is storage-metadata feasibility only.

Authorized:
- read-only object listing metadata from Railway bucket `market-raw-archive`;
- BTCUSDT only;
- market dates >= 2026-09-01 UTC;
- keys, sizes, storage timestamps only.

Forbidden:
- GET/range-read/download object bodies;
- decompression/payload parsing;
- labels/features/models/metrics/PnL;
- EXP024/P3/P4 score usage;
- date selection based on market outcome.

Frozen forward-day selection rule:
the chronologically earliest UTC day >= 2026-09-01 with exactly one positive-
size BTCUSDT object in each hourly slot 00..23.

Metadata-only listing does not analytically consume the forward holdout.
A later P2B body read will consume the selected day and requires separate
freeze/authorization.

Current state:
`DEV031_P2A_DESIGN_FROZEN_METADATA_LISTING_AUTHORIZED`


---

## 127. DEV031-P2A forward archive audit withdrawn pre-access — holdout remains sealed

A scientific sequencing error was identified before any Railway bucket access.

Although P2A was designed as metadata-only and would not itself read market
payloads, opening a forward-confirmation path immediately after DEV031-P1B would
be scientifically premature because P1B did NOT pass its preregistered primary
incremental-probability protocol.

DEV031-P1B remains:
`FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE`

The observed AUC improvement is preserved only as hypothesis-generating partial
evidence, not as a validated model eligible for fresh forward confirmation.

Therefore DEV031-P2A is withdrawn before execution:

`PRE_RUN_WITHDRAWN_FORWARD_CONFIRMATION_PREMATURE`

Critical facts:
- no Railway bucket listing was executed under DEV031-P2A;
- no market-raw-archive metadata was opened;
- no Sep-01+ object key, size, timestamp, header, or payload was inspected;
- no object body was downloaded;
- no forward market day was selected;
- no canonical P2A artifact exists;
- Sep-01+ remains analytically and operationally sealed for model confirmation.

The P2A research/design documents remain in git as an audit trail of the
withdrawn plan. They are NOT execution authorization.

Scientific sequencing rule restored:
fresh forward holdout may be consumed only after a model/mechanism has first
demonstrated sufficient robustness on historical/development validation under a
separately frozen protocol.

Next permitted work must stay off Sep-01+ and must not rescue P1B by post-hoc
feature subset, calibration, threshold, model-family, or EXP024/P4 composition
on the same Jan-Jul outcomes.

Current state:
`DEV031_FORWARD_HOLDOUT_RESEALED_HISTORICAL_ROBUSTNESS_STAGE_REQUIRED`


---

## 128. Legacy repository relationship audit — Multi-Market is fully subsumed

Legacy repository inspected:
`EmadHammamiLoopa/Multi-Market`

Legacy main HEAD:
`1ee5d97f3ed266b9f5db5396dad5d4c11e38ff73`

Finding:
the legacy repository is a direct historical ancestor/snapshot of the current
`Multi-Market-Codex-Lab` lineage.

Exact tree comparison against current scientific lineage:
- legacy files = 260
- all 260 paths exist in current repository
- 257/260 are byte-identical
- 0 legacy-only files
- only three shared paths changed:
  - `.github/workflows/test.yml`
  - `.gitignore`
  - `pyproject.toml`
- legacy HEAD exists in current repository history
- current scientific lineage is 515 commits ahead of that legacy HEAD

Therefore:
- do not merge/copy/import files from the legacy repository;
- do not treat it as an independent source of missing implementation;
- current repository already contains all legacy scientific code/evidence plus
  the later Codex/EXP/DEV030/DEV031 lineage.

Useful historical context retained in the legacy content:
- V0/V1 causal replay/learned-model framework;
- V2/V2.1 cross-market/regime work;
- V2.2 point-in-time macro experiment;
- V2.3 cross-sectional information-diffusion experiment;
- multi-market historical evidence for BTCUSD/ETHUSD/EURUSD/XAUUSD/QQQ.

Important limitation for current DEV031:
legacy multi-market evidence is not the same data family as the current raw
Binance USD-M event-time/deep-L2 `BTCUSDT` pipeline. It does not supply an
independent ETHUSDT/SOLUSDT raw incremental_book_L2 replication dataset for the
frozen EVENT_DEPTH26 mechanism.

Current state:
`LEGACY_MULTI_MARKET_REPO_FULLY_SUBSUMED_REFERENCE_ONLY`


---

## 129. DEV032-E0 candidate census opened; Wave-1 36-strategy composition drafted

Branch:
`research/dev032-e0-candidate-census`

Purpose:
broad exploratory historical microstructure screening on already-consumed
BTCUSDT Jan-Jul development data before any independent replication or forward
confirmation.

Critical sequencing:
- DEV031-P1B remains an official FAIL.
- P1B ranking improvement remains hypothesis-generating only.
- Sep-01+ remains sealed.
- no Railway/archive access.
- no forward data.
- no DEV032 model fit has run yet.

E0 literature/candidate census:
`docs/DEV032_E0_CANDIDATE_CENSUS.md`
commit:
`43ac86a34bda91988e743ca5a966e5b74832a801`

Candidate registry:
`docs/DEV032_E0_CANDIDATE_REGISTRY.md`
corrected registry commit:
`84cc12e316db615d7f172536b510b8c953f752c9`

Registry facts:
- 88 total mechanism concepts
- 52 raw Wave-1 tags before strategy-block consolidation
- prior tested/closed ideas explicitly marked
- materially new ideas separated from duplicates
- PRICE-only sequence family remains closed

Wave-1 draft:
`docs/DEV032_E1_WAVE1_SCREEN_DRAFT.md`
commit:
`110e7226568a0e83d6a419eef389b80f20209d58`

Wave-1 strategy count:
exactly 36:
- 4 controls
- 32 materially new strategy blocks

Families:
- controls / frozen baselines
- queue/depth imbalance
- generalized microprice
- raw multi-level/stationary order flow
- book shape/geometry
- event-type pressure
- event timing/burstiness
- Hawkes/excitation-inspired fixed features
- resilience/recovery
- stationary event-flow sequence models

E1 broad-screen model policy draft:
- S00-S33 use the same train-only StandardScaler + L2 LogisticRegression
  protocol to isolate information-set value;
- S34 uses one fixed small stationary-flow MLP;
- S35 uses one fixed compact stationary-flow TCN;
- no XGBoost/HGB/Transformer model multiplication in Wave 1.

Primary screening endpoint:
directional ROC AUC and AUC delta versus S00 PRICE23.

Multiple-testing control:
paired temporal-label max-stat null across the full Wave-1 candidate set.

Strong screening survivor draft gates include:
- pooled AUC improvement vs S00;
- pooled AUC >= 0.56;
- >=3/4 positive fold AUC deltas;
- all LOO AUC deltas positive;
- observed AUC delta above q95 family-wise max-stat null;
- family-wise empirical p <= 0.05;
- all causal/support/provenance invariants pass.

Even a strong Wave-1 survivor remains exploratory.
At most 1-3 mechanisms may later proceed through adaptive refinement and then
independent historical replication.

Hard search caps:
- Wave 1 = 36
- Wave 2 <= 24
- Wave 3 <= 12
- then BTC Jan-Jul search closes regardless of outcome.

No DEV032 real data model fit is authorized yet.

Next required stage:
freeze exact mathematical feature definitions, deterministic extraction
semantics, synthetic tests, candidate hashing, and execution implementation
before any Wave-1 fit.

Current state:
`DEV032_E0_CENSUS_COMPLETE_E1_FEATURE_FORMULA_IMPLEMENTATION_PENDING`


---

## 130. DEV032 experiment checkpoint — broad historical microstructure search program

Experiment family:
`DEV032`

Current branch:
`research/dev032-e0-candidate-census`

### Scientific purpose

DEV032 is a broad but bounded exploratory search program over already-consumed
BTCUSDT Jan-Jul 2026 development data.

It exists to answer:

> Which materially different causal microstructure mechanism families, if any,
> contain robust directional ranking information beyond the frozen PRICE23
> baseline?

DEV032 does NOT replace, revise, or rescue prior experiment outcomes.

### Prior-state dependency

DEV031-P1B remains officially:

`FAIL_EVENT_DEPTH_NO_STABLE_INCREMENTAL_DIRECTION_VALUE`

Its preserved partial result:
- C0 PRICE23 pooled AUC = 0.5364690595
- C1 PRICE23 + EVENT_DEPTH26 pooled AUC = 0.5764930862
- pooled AUC delta = +0.0400240267
- 3/4 fold AUC deltas positive
- every leave-one-fold-out AUC delta positive
- probability-quality gates failed
- temporal null not run because preregistered precheck failed

Therefore the P1B AUC pattern is hypothesis-generating only.

### DEV032-E0 status

E0 is candidate census / research design only.

No DEV032 real-data model fit has run.

No new market data has been opened.

No forward holdout has been consumed.

Sep-01+ remains sealed.

E0 literature/candidate census:
`docs/DEV032_E0_CANDIDATE_CENSUS.md`

Census commit:
`43ac86a34bda91988e743ca5a966e5b74832a801`

Candidate registry:
`docs/DEV032_E0_CANDIDATE_REGISTRY.md`

Corrected registry commit:
`84cc12e316db615d7f172536b510b8c953f752c9`

Registry contains:
- 88 total mechanism concepts
- prior-tested controls
- materially new candidates
- later/refinement candidates
- duplicate/closed/forbidden candidates
- explicit preservation of P8/P9/P10 PRICE-only sequence closure

### DEV032-E1 Wave-1 composition

Draft:
`docs/DEV032_E1_WAVE1_SCREEN_DRAFT.md`

Draft commit:
`110e7226568a0e83d6a419eef389b80f20209d58`

Wave 1 contains exactly 36 strategy blocks:
- 4 controls
- 32 materially new strategy blocks

Main families:
1. frozen controls / baselines
2. queue/depth imbalance
3. generalized microprice
4. raw multi-level / stationary order flow
5. book shape / geometry
6. event-type pressure
7. event timing / burstiness
8. Hawkes / excitation-inspired fixed features
9. resilience / recovery
10. stationary event-flow sequence models

Wave-1 models:
- S00-S33:
  train-only StandardScaler + L2 LogisticRegression
- S34:
  one fixed small stationary-flow MLP
- S35:
  one fixed compact stationary-flow TCN

No XGBoost/HGB/Transformer model multiplication in Wave 1.

### Frozen scientific task for Wave 1

Planned fixed task:
- BTCUSDT
- Jan-Jul 2026 consumed development sandbox only
- T1 = DIRECTION_GIVEN_TOUCH
- target A
- horizon = 120 s
- barrier = 16 bp
- causal window = 32 s
- exact frozen first-passage/executable semantics
- exact four chronological folds:
  1. Jan-Mar -> Apr
  2. Jan-Apr -> May
  3. Jan-May -> Jun
  4. Jan-Jun -> Jul

Forbidden:
- Aug-01
- Aug-30
- Sep-01+
- Railway
- market-raw-archive
- abundant-love
- PnL
- threshold optimization
- feature-subset rescue
- post-hoc strategy deletion/addition inside the same Wave-1 run

### Primary Wave-1 endpoint

Primary:
`pooled OOF ROC AUC`

Primary incremental statistic:
`AUC(candidate) - AUC(S00 PRICE23)`

Stability diagnostics:
- per-fold AUC
- positive fold-delta count
- leave-one-fold-out pooled AUC deltas
- worst-fold AUC

Probability diagnostics retained but secondary:
- log loss
- Brier
- balanced accuracy at 0.5
- macro F1

### Multiple-testing protection

Wave 1 must use a temporal-label family-wise max-stat null.

For every eligible temporal shift:
- apply the same within-day shift;
- keep all predictions fixed;
- calculate AUC delta vs S00 for every candidate;
- record the maximum candidate AUC delta.

The resulting max-stat null controls for searching the full Wave-1 candidate set.

A candidate may not be promoted using only an uncorrected p-value.

### Draft strong-screening-survivor gates

A non-control candidate must satisfy all:
- pooled AUC > S00
- pooled AUC >= 0.56
- >=3/4 positive fold AUC deltas
- all leave-one-fold-out AUC deltas positive
- observed AUC delta > q95 of Wave-1 max-stat null
- family-wise empirical p <= 0.05
- all causality/support/provenance invariants PASS

Even this status is exploratory only:

`STRONG_SCREENING_SURVIVOR`

It is NOT historical validation and does NOT authorize forward data.

### Search-budget rule

DEV032 search is intentionally finite:

- Wave 1 = exactly 36 strategies
- Wave 2 <= 24 strategies
- Wave 3 <= 12 strategies

After Wave 3:
`BTC Jan-Jul adaptive search is CLOSED`

At most the best 1-3 scientifically distinct mechanisms may continue to
independent historical replication.

Only after an independent historical robustness PASS may Sep-01+ be considered
for one-shot forward confirmation.

### Legacy repository audit relevant to DEV032

The separate repository:
`EmadHammamiLoopa/Multi-Market`

is fully subsumed by the current repository:
- 260 legacy files
- 260/260 paths present in current repo
- 257/260 byte-identical
- 0 legacy-only files
- legacy main HEAD is a direct ancestor
- current lineage is 515 commits ahead

Therefore no code/evidence import from the legacy repo is required.

### Current exact status

`DEV032_E0_CENSUS_COMPLETE_E1_FORMULA_AND_IMPLEMENTATION_FREEZE_PENDING`

### Next authorized work only

Before any real Wave-1 fit:

1. freeze exact mathematical definition of S00-S35;
2. freeze causal source intervals and event grouping semantics;
3. freeze deterministic feature order per strategy;
4. implement extraction without predictive fitting;
5. add synthetic causality/domain tests;
6. add provenance and candidate-definition hashes;
7. add max-stat null implementation tests;
8. run CI and local freeze validation;
9. verify canonical E1 output directory absent;
10. freeze one scientific execution commit.

Only after all ten steps PASS may the single canonical DEV032-E1 Wave-1
historical screen be executed.


---

## 131. DEV032-E1A formula freeze and pure feature-core implementation checkpoint

Wave-1 model policy was simplified pre-fit:
- all S00-S35 now use the same train-only StandardScaler + L2 LogisticRegression
  in the later E1B screen;
- no MLP/TCN architecture comparison in Wave 1;
- S34/S35 are fixed temporal-shape information representations instead;
- MLP/TCN/DeepLOB/TLOB are deferred to Wave 2 only if the corresponding
  information family survives Wave 1.

This change occurred before any DEV032 predictive fit and therefore does not
respond to outcomes.

Model-policy amendment commit:
`a3850ef691796df13ebc7251741299a1a928915e`

Exact mathematical strategy formulas:
`docs/DEV032_E1A_STRATEGY_FORMULAS.md`

Formula freeze commit:
`c6db8eb1976e27ff3f3bfbdb6a0645218a6d1825`

The formula specification freezes:
- common raw-L2 atomic-group causality semantics;
- exact snapshot/depth conventions;
- S00-S35 definitions;
- exact fixed levels/windows/bands/tau values;
- edge-case zero/invalid behavior;
- fixed feature counts;
- exact support requirement;
- no matched-subset rescue.

Pure in-memory feature core:
`src/multimarket/dev032_e1a_feature_core.py`

Core implementation commit:
`f3642eb78adcb35936a7d718dfc90fb4e362c682`

Synthetic test suite:
`tests/test_dev032_e1a_feature_core.py`

Test commit:
`b2979248003edb214267aec5182319b024817311`

CI wiring commit:
`f1ddeae981fb04becb60f53e0c5b9db37acf4c01`

Draft PR:
`#6`

Pure feature-core coverage includes:
- exact 36-strategy registry and feature counts;
- queue/depth imbalance;
- weighted depth imbalance;
- generalized multi-level microprice;
- book slope and convexity;
- price-gap asymmetry;
- depth centroid and normalized entropy;
- event transition contrasts;
- inter-arrival moments;
- burstiness/Fano statistics;
- fixed exponential event intensities;
- bounded multiscale intensity ratios;
- temporal-vector cosine behavior;
- S34 stationary-flow temporal shape;
- S35 event-pressure temporal shape;
- fail-closed insufficient-depth behavior.

Important current guards:
- DEV032 Jan-Jul raw analytically opened = NO
- DEV032 P1A artifacts opened for fit = NO
- DEV032 model fit = NO
- DEV032 predictive metric = NO
- Aug-01 opened = NO
- Aug-30 opened = NO
- Sep-01+ opened = NO
- Railway/archive/bucket opened = NO
- PnL = NO

Next required work after CI PASS:
implement and freeze the raw-L2 E1A materializer that emits all frozen
strategy matrices on the exact 1,374-row P3 T1 support, with no predictive
metrics.

Current state:
`DEV032_E1A_FORMULAS_FROZEN_PURE_FEATURE_CORE_CI_PENDING`


---

## 132. DEV032-E1A pure feature core CI PASS

Latest CI run:
`33627514261`

Observed job status:
- `dev032-e1a-feature-core` = SUCCESS
- `dev031-p0-audit` = SUCCESS
- `dev031-p0a-audit` = SUCCESS
- remaining companion jobs were still in progress at this checkpoint

This establishes that the frozen DEV032-E1A mathematical core and synthetic
domain tests are green in CI.

No real DEV032 data access or predictive fit occurred.

Current state:
`DEV032_E1A_PURE_FEATURE_CORE_CI_PASS_RAW_MATERIALIZER_IMPLEMENTATION_AUTHORIZED_SYNTHETIC_ONLY`


---

## 133. DEV032-E1A formula clarification and materializer-contract checkpoint

Three pre-fit ambiguities in the initial formula freeze were identified and
resolved before any DEV032 real-data access:

1. S03 exact feature count is 12, not 13.
2. S30/S31 now have exactly six explicitly defined excitation-derived features
   each.
3. S34 stationary temporal-shape normalization is explicitly defined as
   per-band signed level flow divided by total absolute top-10 flow in that
   band.

Clarification commit:
`ca497259137c4aece655108f23f30124c6c5014a`

Pure feature-core S03 count alignment:
`60fb802ab3722ccb6fd6bbc1f1189407492cdb7a`

These are pre-fit specification corrections only; no predictive outcome existed
when they were made.

Materialization contract implementation:
`src/multimarket/dev032_e1a_materialize.py`

Implementation commit:
`c0286fddc1dfc6333abda6d1f0ee040eb278aa60`

Materializer contract freezes:
- exact S00-S35 membership and order;
- exact per-strategy feature counts;
- exact synthetic extractor CSV header order;
- exact support/label chronology checks;
- strategy-matrix finite/shape checks;
- support, label, and matrix SHA256 domains;
- deterministic canonical JSON encoding;
- no runtime forward/activity guard may be true.

Synthetic materializer tests:
`tests/test_dev032_e1a_materialize.py`

Test commit:
`d381f99bd5215ffba518cb379ac121ef6ea83be3`

CI extension commit:
`f8a1f7f6fc5a112245caa3e59e2cf5cb30c48cee`

Latest CI run containing the materializer-contract suite:
`33628367695`

At this checkpoint that run was still queued; do not call it PASS until the
DEV032 job completes successfully.

Permanent E1A support target remains:
- rows = 1374
- LONG = 684
- SHORT = 690
- support shrink = forbidden
- label change = forbidden
- nonfinite strategy value = forbidden

Important guards remain:
- DEV032 Jan-Jul raw access = NO
- DEV032 model fit = NO
- DEV032 predictive metric = NO
- Aug-01 = closed
- Aug-30 = closed
- Sep-01+ = closed
- Railway/archive/abundant-love = unopened
- PnL = NO

Next work:
implement `tools/dev032_e1a_raw_features.cpp` using the frozen atomic-group
semantics and frozen S04-S35 formulas. It must first compile and pass synthetic
known-event tests against the materializer contract before any real Jan-Jul
raw-L2 execution is authorized.

Current state:
`DEV032_E1A_MATERIALIZER_CONTRACT_IMPLEMENTED_CI_PENDING_RAW_EXTRACTOR_NEXT`


---

## 134. DEV032-E1A materializer contract CI PASS

CI run:
`33628367695`

Terminal conclusion:
`SUCCESS`

Jobs observed PASS:
- dev032-e1a-feature-core
- dev031-p0-audit
- dev031-p0a-audit
- dev031-p1a-materialization
- dev031-p1b-incremental
- p10-transform
- unit-tests Python 3.10
- unit-tests Python 3.12

Therefore the E1A pure mathematical core and materializer contract are green.

No DEV032 real-data extraction or predictive fit has occurred.

Raw extractor design boundary:
- C++ extractor will emit S04-S35 only;
- exact raw-derived feature columns = 278;
- S00-S02 will be reused from frozen P1A artifacts;
- S03 will be reconstructed from the frozen aggregated Phase0DL source under
  exact existing semantics rather than re-derived from raw L2.

Current state:
`DEV032_E1A_MATERIALIZER_CONTRACT_CI_PASS_RAW_CPP_IMPLEMENTATION_ACTIVE`


---

## 135. DEV032-E1A raw extractor implementation and synthetic-test checkpoint

Additional pre-implementation event semantics were frozen before real data:
- row-level classified event occurrences for S22-S23/S25-S31;
- S24 atomic-group dominant event transitions;
- S33 pre-group to post-group best-queue shock semantics.

Event-semantics commit:
`67e2c27ffac4b4f5a68395196f759af4919be1f1`

Raw extractor:
`tools/dev032_e1a_raw_features.cpp`

Initial implementation commit:
`30b6e833d32d9c251a9b0af5d5c7218d2bc2ca3d`

Implementation cleanup:
`a508b68c32d215736b7c6c2284d8c8e5afffc5c3`

Frozen-formula alignment for S14 and S32:
`70fc3fcee2341735646a73f13eaa4f44d77107a7`

Synthetic raw-extractor tests:
`tests/test_dev032_e1a_raw_extractor.py`

Test commit:
`c2006861e9a670878d61e621105b2937ec1c7bf8`

CI workflow extension intended to include the raw-extractor test:
`b85cb5d17b74e57002dd380a9ffd28f18ea2df4e`

Important CI interpretation:
run `33629153925` completed SUCCESS at head `c2006861...`, but that
head predates the workflow-extension commit `b85cb5d...`.
Therefore it does NOT yet establish that
`test_dev032_e1a_raw_extractor.py` ran.

Do not mark the raw extractor synthetic suite PASS until a later CI run at or
after `b85cb5d...` completes successfully.

The raw extractor contract is:
- input: frozen-format raw incremental_book_L2 gzip + exact support timestamps;
- output: S04-S35 only;
- exact raw-derived feature columns = 278;
- support row is never dropped;
- insufficient simultaneous L50 depth => feature_valid=0;
- any nonfinite/width failure => feature_valid=0;
- later Python materializer rejects any feature_valid=0 and therefore forbids
  matched-subset rescue.

No DEV032 Jan-Jul raw-L2 execution has occurred.

No DEV032 model fit or predictive metric has occurred.

Current state:
`DEV032_E1A_RAW_EXTRACTOR_IMPLEMENTED_SYNTHETIC_CI_CONFIRMATION_PENDING`


---

## 136. DEV032-E1A raw extractor synthetic CI PASS

CI run:
`33629240416`

CI head:
`b85cb5d17b74e57002dd380a9ffd28f18ea2df4e`

Terminal conclusion:
`SUCCESS`

The DEV032 CI job executed the expanded suite including:
- `tests/test_dev032_e1a_feature_core.py`
- `tests/test_dev032_e1a_materialize.py`
- `tests/test_dev032_e1a_raw_extractor.py`

Observed job status:
- `dev032-e1a-feature-core` = SUCCESS
- all DEV031/P10 regression jobs in the same run = SUCCESS
- unit tests Python 3.10/3.12 = SUCCESS

This establishes:
- C++ raw extractor compiles in CI;
- synthetic 60x60 L2 snapshot/event fixture produces exact 278 raw-derived
  columns;
- exact support timestamp is preserved;
- raw strategy values are finite under valid depth;
- known queue/depth/event families move nontrivially on the fixture;
- insufficient L50 depth fails closed through `feature_valid=0`;
- Python materializer rejects invalid support rows rather than shrinking
  support.

No DEV032 real Jan-Jul raw data has been opened or processed yet.

No predictive fitting or metric calculation has occurred.

Next authorized stage:
build the real E1A campaign runner that:
1. verifies P0A/P1A/P3 frozen provenance hashes;
2. verifies Jan-Jul raw file identities against frozen P0A manifest;
3. reconstructs exact P3 T1 support;
4. runs the now-tested C++ extractor across all seven consumed development days;
5. assembles S00-S35 matrices without any model fitting;
6. requires exact 1374 / 684 LONG / 690 SHORT support;
7. writes one canonical E1A materialization artifact only after all invariants
   pass.

Current state:
`DEV032_E1A_RAW_EXTRACTOR_SYNTHETIC_CI_PASS_REAL_MATERIALIZER_RUNNER_IMPLEMENTATION_AUTHORIZED`


---

## 137. DEV032-E1A real materialization runner implemented; CI pending

Real E1A runner:
`src/multimarket/dev032_e1a_runner.py`

Implementation commit:
`b0aea9b9a091d2aeb746ef9456457dff540626e4`

Runner assembly contract:
- S00 = exact frozen P1A/P3 PRICE23
- S01 = exact frozen P1A EVENT_DEPTH26
- S02 = exact S00+S01 concatenation
- S03 = exact frozen aggregated Phase0DL PRICE_BOOK S0 block, 12 columns
- S04-S35 = tested raw-L2 C++ extractor output

Runner verifies before any canonical output write:
- P0A/P1A/P3 artifact identities
- Jan-Jul raw identities against frozen P0A manifest
- aggregated Jan-Jul input hashes
- exact P3 support contract
- exact per-day timestamps and labels
- all 36 strategy matrix widths and finite values
- campaign total = 1374
- LONG = 684
- SHORT = 690
- no feature_valid=0
- no support shrink
- no forward/activity guard true

Heavy raw extraction is capped at two concurrent workers to reduce storage/IO
risk.

Runner guard tests:
`tests/test_dev032_e1a_runner.py`

Test commit:
`62a023ea95064101b3f1836946ea5454505a81a0`

CI wiring commit:
`ce986107661dd93e17b6b3f5e91a6b373f7b0b1e`

CI run:
`33629558538`

At this checkpoint:
`QUEUED`

Therefore:
- do NOT mark runner CI PASS yet;
- do NOT run real E1A materialization yet;
- do NOT create canonical E1A artifact yet.

Next gate after CI PASS:
- clean execution tree
- exact source/test/design hashes
- canonical output absence
- local protocol precheck
- execution-freeze document
- single canonical E1A materialization run

Current state:
`DEV032_E1A_REAL_RUNNER_IMPLEMENTED_CI_PENDING_NO_REAL_DATA_ACCESS`


---

## 138. DEV032-E1A runner CI dependency failure fixed pre-data

Runner guard CI run:
`33629558538`

Terminal result:
`FAILURE`

Failure classification:
`IMPLEMENTATION_DEPENDENCY_ONLY_NO_REAL_DATA_ACCESS`

Exact cause:
`src/multimarket/dev032_e1a_runner.py` imported
`dev031_p1b_event_depth_incremental` only to reuse `load_days()`.
That transitively imported `scikit-learn`, while the E1A materialization CI
job intentionally installs no ML dependency.

Observed error:
`ModuleNotFoundError: No module named 'sklearn'`

Scientific impact:
- none;
- no Jan-Jul raw data was opened;
- no E1A artifact was written;
- no model fit occurred;
- no predictive metric occurred;
- no canonical rerun rule was triggered.

Resolution:
E1A runner no longer imports P1B or scikit-learn.
It now reads the canonical P1A manifest/day CSVs directly and independently
verifies:
- P1A manifest SHA256;
- P1A terminal status;
- exact P3 support flag;
- per-day file SHA256/bytes;
- exact 23+26 feature header;
- exact support SHA256;
- binary labels;
- finite 49-column matrices.

Fix commit:
`daf51d544a6861f4b3ba6bc07b2c23add0fd0654`

New CI run:
`33630698148`

At this checkpoint:
`IN_PROGRESS`

Do not authorize real E1A execution until this run is green and the subsequent
execution-freeze checks pass.

Current state:
`DEV032_E1A_RUNNER_DEPENDENCY_FIXED_CI_REVALIDATION_IN_PROGRESS_NO_REAL_DATA_ACCESS`

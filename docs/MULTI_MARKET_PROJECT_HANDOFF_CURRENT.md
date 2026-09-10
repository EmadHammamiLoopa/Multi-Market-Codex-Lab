# Multi-Market Codex Lab — CURRENT Project Handoff

Updated: 2026-09-10
Purpose: authoritative continuation handoff for future ChatGPT project conversations.

This file supersedes the previous CURRENT handoff state. Historical frozen PASS/FAIL artifacts and older handoff files remain immutable references.

## 1. Current restored machine and repository state

The project was migrated from the previous laptop to a new MSI machine and the complete WSL environment/project state was restored.

Current machine:

- MSI Vector 17 HX AI A2XWJG-012NEU
- Intel Core Ultra 9 275HX
- NVIDIA GeForce RTX 5090 Laptop GPU
- VRAM: 24,463 MiB (~24 GB)
- RAM: 64 GB DDR5
- Storage: 2 TB NVMe
- Windows 11
- WSL2 Ubuntu physically stored at `D:\WSL\Ubuntu`
- Current WSL allocation approximately 47 GiB RAM + 16 GiB swap
- CUDA works inside WSL

Authoritative local worktree:

`/home/emadh/Multi-Market-d6r13-preauth-v2`

Git worktree repair completed successfully after migration.

Current exact development branch:

`research/dev045-m6-d6r26a-p2-r24-durable-context-performance-preexecution`

Current exact HEAD:

`4abe7e0c3807c97a18226fddf1ac51ed81937c85`

Verified after restore:

- `TOPLEVEL_IDENTITY=PASS`
- `BRANCH_IDENTITY=PASS`
- `HEAD_IDENTITY=PASS`
- working tree clean

Repaired `.git` worktree link:

`/home/emadh/market-parent-restored/.git/worktrees/Multi-Market-d6r13-preauth-v2`

The original migration backup remains preserved on E:.

Do NOT use stale local path `/mnt/c/Users/emadh/Downloads/market-exp026`.

Do NOT checkout/reset/clean/prune unless a specific diagnosis justifies it.

## 2. Frozen execution lineage through R24

Important frozen lineage:

- R21 GREEN HEAD: `a667c20be84a2e4496cd9d7ddb90fbba5237120b`
- R22 GREEN HEAD: `016079a5fae640b4cd5f686aebdec2f7b556a4b3`
- R23 GREEN HEAD: `124dc037b1fab545a336d830419d40ed55138c8c`
- R23A GREEN execution HEAD: `4e3e320931e896a6e479f3065eb60e118f993569`
- R24 initial durable-context design commit: `4ae4852d7519aab3d97b72cb28c5cf4ae9dc356e`
- R24 current HEAD with dedicated CI: `4abe7e0c3807c97a18226fddf1ac51ed81937c85`

R24 dedicated GitHub Actions workflow:

`dev045-d6r26a-p2-r24-durable-context-performance-preexecution`

Verified GREEN workflow run:

`34331578646`

The R23A branch/HEAD remains an immutable historical frozen readiness/execution lineage point. It must not be rewritten. R24 is now the current successor architecture and must itself be extended only through new successor branches.

This handoff is intentionally maintained on documentation branch:

`project/market-handoff-current`

Never merge documentation-only handoff commits into the experiment execution lineage merely to update documentation.

## 3. Current P2 attempt state — CRITICAL

Experiment family:

`DEV045 D6R26A P2`

Purpose: canonical Jan-Jul CONSUMED DEVELOPMENT candidate-label materialization for Gen2 conditional maker-edge research.

Frozen development days:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Original canonical campaign cardinality remains:

- 7 source days
- 40 lanes/day
- 280 lanes total
- 280 canonical Parquet partitions

Current forensic state:

- `P2_ATTEMPT_CONSUMED=NO`
- canonical attempt marker ABSENT
- canonical failure artifact ABSENT
- canonical final manifest ABSENT
- no canonical partitions written
- no historical simulator lane started
- no model fit
- no PnL

The exact attempt-consumption event remains:

`FIRST_CANONICAL_CANDIDATE_SIMULATOR_LANE_START_AFTER_EXACT_SOURCE_IDENTITY_VERIFICATION`

Therefore durable context preparation is explicitly pre-attempt and does NOT consume P2.

If the attempt marker ever exists:

- `P2_ATTEMPT_CONSUMED=YES`
- rerun forbidden
- resume forbidden
- automatic retry forbidden

Any post-marker failure becomes terminal evidence for that attempt.

## 4. Pre-attempt power-loss evidence — preserve

Two previous real starts on the old laptop were interrupted by host restart/power loss before the exact attempt marker.

Both remained pre-attempt and did NOT consume P2.

The latest partial pre-attempt January context residue is:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_canonical_scratch/2026-01-01/exchange_midpoints.bin.tmp`

Last known pre-migration forensic size:

`17825792` bytes

This was a partial R20 midpoint spool only. It is NOT a completed durable day bundle.

Rules:

- do not treat it as complete
- do not reuse it as a durable context
- do not delete it automatically
- preserve it as forensic evidence unless a later explicit cleanup/migration step first records its current identity
- after migration, do not assume its SHA without re-verification

The repeated long pre-marker R20 build motivated R24 durable context architecture.

## 5. R24 durable-context architecture — binding

Experiment:

`DEV045-D6R26A-P2-R24`

Design version:

`durable-context-performance-preexecution-v1`

R24 is PREEXECUTION_ONLY.

Binding state:

- `P2_ATTEMPT_CONSUMED=False`
- `HISTORICAL_SIMULATOR_LANE_STARTED=False`
- `DURABLE_DAY_CONTEXT_REQUIRED=True`
- `ALL_SEVEN_DURABLE_CONTEXTS_REQUIRED_BEFORE_ATTEMPT=True`
- `DURABLE_CONTEXT_BUILD_DOES_NOT_CONSUME_SIMULATOR_ATTEMPT=True`
- `COMPLETED_DAY_BUNDLE_REUSE_AFTER_REBOOT_AUTHORIZED=True`
- `PARTIAL_DAY_BUNDLE_IS_NOT_COMPLETE=True`
- `PARTIAL_DAY_BUNDLE_REUSE_FORBIDDEN=True`

Expected durable root name:

`dev045_d6r26a_p2_durable_context_v1`

Expected absolute durable root:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_durable_context_v1`

Latest restored-machine read-only audit:

`DURABLE_ROOT=MISSING`

Therefore no durable Jan-Jul bundle currently exists and no historical materialization under R24 has happened yet.

R24 freezes the exact day file identity:

- `decision_local_ns.npy`
- `best_bid_tick.npy`
- `best_ask_tick.npy`
- `feature_values.npy`
- `exchange_midpoints.bin`
- `DAY_CONTEXT_MANIFEST.json`

The manifest is written last and is the completion sentinel.

A completed durable day bundle must bind and verify:

- exact frozen source identity
- source SHA256
- file bytes + SHA256
- array shape + dtype
- R20 feed bounds and feature summary
- exact midpoint-index identity/layout

Publishing rules:

- staging directory required
- partial staging is not complete
- atomic same-filesystem final publication required
- manifest written last
- completed day may be reused after reboot without rebuilding its R20 context

Final simulator successor requirements:

- `FINAL_RUNNER_MUST_VERIFY_ALL_SEVEN_DAY_BUNDLES=True`
- `FINAL_RUNNER_RAW_CONTEXT_REBUILD_FORBIDDEN=True`
- `FINAL_RUNNER_PARTIAL_BUNDLE_ACCEPTANCE_FORBIDDEN=True`

The final simulator will still require the original raw NPY mmap as hftbacktest input. Durable contexts eliminate repeated Python R20 context extraction, not the underlying simulator source data.

## 6. Important architecture finding after R19-R24 review

The existing code already supplies the required scientific semantics. Do not redesign candidate generation or labels in the durable layer.

R17:

- derives feed bounds from the already validated event surface
- uses the exact one-second union decision grid
- allows decision exactly at final observed feed timestamp
- forbids decisions after actual feed EOF
- dense feature cache maximum is 256 MiB

R18 `DenseFeatureCache` contains exactly:

- `decision_local_ns` dtype `<i8`
- `best_bid_tick` dtype `<i8`
- `best_ask_tick` dtype `<i8`
- `values` dtype `<f8`, shape `(n, 8, 25)`

R19:

- builds eligible candidate epochs only
- preserves exact warmup/support semantics
- missing support after first eligible epoch fails closed
- provides `FeatureCacheBuildSummary`

R20:

`build_once_day_context(...)`

builds BOTH required surfaces in one Python raw-event pass:

1. R18 dense feature cache
2. file-backed exchange midpoint index

R20 result object:

`DayContextBuildResult(bounds, feature_cache, feature_summary, midpoint_index, raw_event_pass_count)`

Midpoint record layout:

- `exchange_ns` `<i8`
- `mid_tick_sum` `<i8`
- 16 bytes/record
- 65,536-record buffer = 1 MiB per spool flush

R20 midpoint spool already uses temp + fsync + atomic rename on normal completion, but host power loss may leave a partial `.tmp`.

R21 consumes `r20.DayContextBuildResult` directly for candidate execution, feature lookup and markout lookup.

Therefore a durable successor does NOT need new candidate/label semantics. It only needs to persist the exact R20 result surfaces, reopen them read-only, reconstruct an equivalent `DayContextBuildResult`, and verify identity before R21 uses it.

R22 old runner behavior remains important for simulator semantics:

- all seven source identities verified before historical source opening
- source once/day
- 40 sequential lanes/day
- fresh hftbacktest engine per lane
- stop first failure
- marker immediately before first simulator lane
- no callback between marker and first lane
- no automatic retry

However R22's old `_prepare_real_day` builds R20 context from raw events inside the simulator campaign. R24 explicitly supersedes that operational preparation pattern for the next successor: all seven contexts must exist durably BEFORE the attempt, and the final simulator successor must load/verify them instead of rebuilding R20.

## 7. Full-pass and performance caution for R26 materialization

Do not assume that increasing CPU concurrency alone makes real durable preparation safe.

There are currently several potentially full-source operations:

1. frozen source identity SHA verification
2. `m4.validate_events(...)` / event-order validation
3. R20 single Python context pass

`m4.validate_events` includes full-array checks such as `np.any(a["local_ts"] < a["exch_ts"])` plus `validate_event_order(a)`.

A naive four-day parallel materializer could therefore create large simultaneous memory bandwidth and temporary-memory pressure even on the new 64 GB machine.

R24 permits:

- `PARALLEL_DAY_CONTEXT_BUILD_AUTHORIZED=True`
- `MAX_PARALLEL_DAY_CONTEXT_BUILD_CAP=4`
- `DYNAMIC_MEMORY_ADMISSION_REQUIRED=True`

The value `4` is a hard cap, not a requirement to always run four days simultaneously.

Before R26 real materialization, freeze the exact admission policy and whether source identity/validation phases are serialized or concurrency-limited. Do not silently remove any existing scientific validation just for speed.

The new hardware may execute frozen semantics faster, but scientific semantics do not change because hardware is stronger.

## 8. Immediate successor plan — CURRENT

DO NOT launch canonical P2 yet.

The previous handoff statement that the next stage was directly `P2_CANONICAL_HISTORICAL_ONE_SHOT` is superseded by R24 and the observed pre-marker durability problem.

Current controlled successor sequence:

### R25 — generic durable bundle foundation, synthetic-only

Parent must be exact R24 HEAD:

`4abe7e0c3807c97a18226fddf1ac51ed81937c85`

R25 should implement only generic persistence/reopen/verification of an already-built R20 context.

R25 must NOT open Jan-Jul, run hftbacktest historical simulation, write the P2 attempt marker, write canonical labels, fit a model, or compute PnL.

Expected R25 capabilities:

- define a durable source identity record
- persist exact R20 cache arrays as `.npy`
- persist/copy exact R20 midpoint binary
- write completion manifest last
- stage then atomically publish completed day directory
- verify exact file set
- verify file bytes/SHA256
- verify array dtype/shape
- reopen arrays read-only with mmap
- reopen midpoint binary read-only with memmap
- reconstruct R18/R19/R20 objects exactly enough for R21 consumption
- fail closed on missing/corrupt/incomplete bundles
- synthetic R20 roundtrip tests prove parity
- completed synthetic bundle reopens without rebuilding raw context
- dedicated GitHub CI

No real historical build entrypoint needs to execute in R25 CI.

### R26 — real Jan-Jul durable materializer

Only after R25 is GitHub GREEN.

R26 will be the first successor allowed to open consumed-development Jan-Jul for durable context preparation.

R26 must freeze before execution:

- exact source identity verification order
- full validation behavior
- durable output root
- per-day completion/reuse semantics
- partial-staging cleanup/forensics semantics
- memory admission thresholds
- maximum concurrency <= 4
- whether expensive source verification/validation stages are serialized or separately admitted
- stop/failure behavior
- no simulator lane
- no canonical label/PnL

R26 durable context creation remains pre-attempt:

`P2_ATTEMPT_CONSUMED=NO`

### Later final simulator successor

Only after all seven durable bundles pass a read-only freeze/audit.

It must:

- verify all seven source identities
- verify all seven durable bundle manifests/hashes/shapes
- open raw NPY read-only for hftbacktest
- load durable R20 context instead of rebuilding it
- preserve R21/R22 sequential/fresh-engine/EOF semantics
- consume the unique attempt only immediately before first simulator lane

## 9. Exact local runtime freeze — MUST USE

Runtime root:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_exact_runtime_v1`

Canonical Python executable:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_exact_runtime_v1/py313/bin/python`

Use this exact Python path explicitly for P2-related exact-runtime validation and eventual execution.

Do NOT select Python via `command -v python`, `command -v python3`, or `/usr/bin/python3` for canonical P2.

Frozen runtime:

- CPython `3.13.15`
- uv `0.12.10`
- numpy `2.2.6`
- pyarrow `25.0.1`
- hftbacktest `2.4.4`
- pytest `9.1.1`
- rustc/cargo `1.98.1`

Recommended environment:

`PY313=/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_exact_runtime_v1/py313/bin/python`

`PYTHONPATH=/home/emadh/Multi-Market-d6r13-preauth-v2/src`

## 10. Exact hftbacktest identity

hftbacktest version:

`2.4.4`

Frozen upstream commit:

`a244a14250b42d97fc305569c93c4117cd5e1dff`

Frozen engine lineage SHA256:

`5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752`

Patch file:

`tools/patch_hftbacktest_244_safe.py`

Frozen patch SHA256:

`f505668af104febbca5f94ad17c94cabff1672b4df068d2d481dda0bb8cdc980`

Patch semantics:

- Issue-312 exact quantity cleanup
- Issue-316 partial local accounting

Patch-keyed wheel:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_exact_runtime_v1/hft244_wheels/f505668af104febbca5f94ad17c94cabff1672b4df068d2d481dda0bb8cdc980/hftbacktest-2.4.4-cp313-cp313-linux_x86_64.whl`

Never restore a stale manually hardcoded patch hash.

## 11. Frozen Jan-Jul source registry

Frozen source registry SHA256:

`97c631d621118d5cd4d294825dec545c92d85c62456403a6974ca38a70ece3f4`

Total frozen source bytes:

`63338314688`

### 2026-01-01

Path:

`/home/emadh/Multi-Market/runtime/dev045_d6r4b/output/BTCUSDT_2026-01-01.npy`

Rows: `64314723`
Bytes: `4116142528`
SHA256: `8f0a4fbd56ecdc261dbe2041ce138a09456423074925d495272716219a1d4da1`

### 2026-02-01

Path:

`/home/emadh/Multi-Market/runtime/dev045_d6r9a/output/BTCUSDT_2026-02-01.npy`

Rows: `179584138`
Bytes: `11493385088`
SHA256: `d757d2ac32a29b0ac587323e115779c466068c6c0eba4270226b9c4109254cbc`

### 2026-03-01

Path:

`/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-03-01.npy`

Rows: `150979263`
Bytes: `9662673088`
SHA256: `9e6a8b61d05e1a4938e17ffa7969241affc7c06c1d0836188e3a882c363f2d99`

### 2026-04-01

Rows: `132829759`
Bytes: `8501104832`
SHA256: `de7e0471e63631394981b301bb461d679192c37eb6241d4d8073cf0640eca7f7`

### 2026-05-01

Rows: `108328169`
Bytes: `6933003072`
SHA256: `9433dfb498070dd5dd3e8ab1633c2f19551844f2ddf0d451e120119365bb04a3`

### 2026-06-01

Rows: `172540697`
Bytes: `11042604864`
SHA256: `ac97ad27c9d58b3b3e249547b8ae7c74cf2ebfde07965103bd9c8c05d0df1160`

### 2026-07-01

Rows: `181084390`
Bytes: `11589401216`
SHA256: `85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f`

All are BTC consumed-development sources. No August, Sep-01+, or non-BTC source is authorized by R24/R25.

## 12. Memory policy

R22 canonical simulator memory policy remains binding:

- preexec MemAvailable >= `8442945536`
- runtime MemAvailable >= `4294967296`
- process swap growth => abort
- anonymous RSS growth > `536870912` bytes => abort
- total RSS is NOT a boundedness gate
- anonymous-memory baseline is captured after engine binding

Reason: the huge NPY source is mmap/file-backed; total RSS is not equivalent to owned anonymous memory.

Do not reintroduce the old total-RSS false failure.

R26 durable-context materialization requires its own explicit dynamic admission contract consistent with R24. It must respect the existing memory rationale and the maximum parallel-day-build cap of 4.

## 13. Local coding agent available

A local $0 coding-agent stack is available inside WSL.

Runtime:

- Ollama `0.34.0`
- endpoint `http://127.0.0.1:11434`
- cloud disabled with `OLLAMA_NO_CLOUD=1`

Primary local model:

`qwen3.8-27b-48k:latest`

- Qwen3.8-27B
- 27.3B parameters
- Q4_K_M
- 49,152-token context
- OpenCode output limit 16,384 tokens
- observed deep-reasoning speed ~45-46 tokens/sec on this RTX 5090
- 48K context runs 100% on GPU with no CPU offload in observed tests

Agent:

- OpenCode `1.18.30`
- path `/home/emadh/.opencode/bin/opencode`

Use the local agent only when it provides a concrete engineering advantage, e.g. repo-wide inspection, call-path tracing, candidate implementation review, static analysis, debugging, or large-diff review.

It is an engineering assistant, not scientific authority.

Current protections:

- can read/edit/grep/search/use LSP
- can run selected tests/Git inspection
- cannot git push
- cannot git reset --hard
- cannot git clean
- cannot rm -rf
- cannot sudo
- cannot web search/fetch
- asks before arbitrary shell commands

Do not weaken these protections without a concrete reason.

For current R25 generic durable bundle foundation, direct inspection of R17-R24 is already sufficient. OpenCode becomes especially useful before/during R26 for repository-wide review of source-validation, memory-admission and concurrency call paths.

## 14. Prior Gen1 economic result — immutable

DEV045 D6R24 Gen1 canonical maker economics is CLOSED.

Do not revisit or rerun it.

- 112 canonical runs complete
- engineering PASS
- economics FAIL
- approximate primary policy net economics: -5.3 to -5.86 bp/trade
- stress approximately -7.3 to -7.73 bp/trade
- 0/7 positive days

Gen1 maker policies are closed.

D6R26A is Gen2 conditional maker-edge work.

P2's purpose is candidate-label materialization, NOT PnL.

## 15. Project governance — always enforce

Consumed stays consumed.

Frozen PASS/FAIL/INVALID results are immutable.

Never rerun the same canonical experiment ID after an attempt is consumed.

No rescue tuning after seeing a result unless it becomes a new independently preregistered hypothesis/experiment.

Sep-01+ BTC remains sealed.

All other markets remain sealed until their proper transfer/validation stage.

Oracle/headroom/classifier performance is NOT profit.

No leverage or position-size optimization until unlevered non-oracle economics pass.

`UNKNOWN / MISSING / UNSUPPORTED => ABSTAIN`.

Entry gates remain conjunctive.

No forced trading quota.

No always-in behavior.

Jan-Jul may be reused only as CONSUMED DEVELOPMENT DATA for Gen2 exploration, with attempts tracked.

Final path remains:

frozen champion
→ fresh unused historical replication/bucket
→ untouched forward validation
→ live shadow/paper
→ tiny real capital
→ measure real fills/slippage
→ gradual scaling

Do not let winner's curse reach real money.

## 16. Future-chat continuation instruction

When a future ChatGPT conversation in the `market` project continues this work:

1. Read `docs/MULTI_MARKET_PROJECT_HANDOFF_CURRENT.md` from branch `project/market-handoff-current` first.
2. Confirm local worktree path `/home/emadh/Multi-Market-d6r13-preauth-v2`.
3. Current expected experiment branch/HEAD before R25 creation is R24 at `4abe7e0c3807c97a18226fddf1ac51ed81937c85`.
4. Check marker/failure/manifest state before any historical command.
5. Treat the old 17,825,792-byte January `.tmp` as forensic partial residue, never a completed durable bundle.
6. Do not launch canonical P2 until R25 foundation, R26 real durable preparation, all-seven durable audit/freeze, and final runner successor are complete and GREEN.
7. Do not use system Python for exact P2 work.
8. Do not rerun frozen GREEN R19-R24 stages.
9. Do not mutate old frozen branches to add new functionality; create successor branches.
10. No August, Sep-01+, non-BTC, model fit or PnL unless a later explicitly frozen stage authorizes it.
11. Use OpenCode/Qwen selectively for engineering leverage, with existing protections preserved.
12. Operational continuation should normally be in Arabic with code/paths/hashes/IDs in English.
13. Prefer one terminal field at a time and inspect the returned evidence before advancing.
14. Never exit the user's terminal; preserve `TERMINAL_REMAINS_OPEN=YES`.

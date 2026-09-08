# Multi-Market Codex Lab — CURRENT Project Handoff

Updated: 2026-09-08
Purpose: authoritative continuation handoff for future ChatGPT project conversations.

This file supersedes the dated 2026-09-01 handoff for CURRENT state. Historical frozen PASS/FAIL artifacts and older handoff files remain immutable references.

## 1. Authoritative repository and execution lineage

Authoritative local repository:

`/home/emadh/Multi-Market-d6r13-preauth-v2`

Canonical execution branch:

`research/dev045-m6-d6r26a-p2-r23a-execution-head-lineage-amendment-preflight`

Frozen GREEN R23A execution HEAD:

`4e3e320931e896a6e479f3065eb60e118f993569`

R23A parent R23 GREEN HEAD:

`124dc037b1fab545a336d830419d40ed55138c8c`

R23 parent R22 GREEN HEAD:

`016079a5fae640b4cd5f686aebdec2f7b556a4b3`

R22 parent R21 GREEN HEAD:

`a667c20be84a2e4496cd9d7ddb90fbba5237120b`

Do not modify the R23A execution branch before the canonical P2 one-shot. A new commit would invalidate the exact frozen execution HEAD.

This handoff itself is intentionally maintained on documentation branch:

`project/market-handoff-current`

so documentation updates do not mutate the canonical execution lineage.

## 2. Current P2 state

Experiment: DEV045 D6R26A P2 canonical Jan-Jul consumed-development candidate label materialization.

Frozen development days:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Expected campaign:

- 7 source days
- 40 lanes/day
- 280 lanes total
- 280 canonical Parquet partitions

Current status:

- `JAN_JUL_CANONICAL_P2_OPENED=NO`
- `HISTORICAL_PAYLOAD_READ=NO`
- `HISTORICAL_SOURCE_OPEN=NO`
- `ATTEMPT_MARKER_WRITTEN=NO`
- `P2_ATTEMPT_CONSUMED=NO`
- `MODEL_FIT=NO`
- `PNL=NO`

The one-shot attempt is still fully available.

## 3. Exact local runtime freeze — MUST USE FOR FUTURE P2 EXECUTION

Runtime root:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_exact_runtime_v1`

Canonical Python executable:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_exact_runtime_v1/py313/bin/python`

Use this exact Python path explicitly in every future canonical P2 command.

Do NOT select Python with `command -v python`, `command -v python3`, or `/usr/bin/python3` for canonical P2 execution.

System `/usr/bin/python3` is Python 3.14.4 and previously failed pre-attempt because the required numerical/runtime surface was absent (`ModuleNotFoundError: numpy`).

Frozen local runtime:

- CPython: `3.13.15`
- uv: `0.12.10`
- numpy: `2.2.6`
- pyarrow: `25.0.1`
- hftbacktest: `2.4.4`
- rustc: `1.98.1`
- cargo: `1.98.1`

uv path:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_exact_runtime_v1/uv/uv`

Rust is only required if the exact patched hftbacktest wheel must be rebuilt.

Recommended environment for canonical execution:

`PY313=/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_exact_runtime_v1/py313/bin/python`

`PYTHONPATH=/home/emadh/Multi-Market-d6r13-preauth-v2/src`

## 4. Exact hftbacktest identity

hftbacktest version:

`2.4.4`

Frozen upstream commit:

`a244a14250b42d97fc305569c93c4117cd5e1dff`

Frozen engine lineage SHA256:

`5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752`

Patch file:

`tools/patch_hftbacktest_244_safe.py`

Current patch SHA256 derived from exact frozen R23A checkout:

`f505668af104febbca5f94ad17c94cabff1672b4df068d2d481dda0bb8cdc980`

Patch semantics:

- Issue-312 exact quantity cleanup
- Issue-316 partial local accounting

IMPORTANT patch identity policy:

Always derive/verify the patch hash from the exact frozen Git HEAD. Do not reuse stale manually hardcoded patch hashes.

The previously used `15b6...` patch hash was stale and caused a safe pre-attempt stop. It must not be used again.

Patch-keyed local wheel:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_exact_runtime_v1/hft244_wheels/f505668af104febbca5f94ad17c94cabff1672b4df068d2d481dda0bb8cdc980/hftbacktest-2.4.4-cp313-cp313-linux_x86_64.whl`

## 5. Local validation already completed successfully

Exact engine/runtime identity passed locally:

- CPython major/minor 3.13
- actual CPython 3.13.15
- numpy 2.2.6
- pyarrow 25.0.1
- hftbacktest 2.4.4
- R5 API/order-status identity PASS

R21 local synthetic exact-engine probes:

`4 passed`

R23A real readiness:

`PASS`

Readiness report values:

- exact HEAD: `4e3e320931e896a6e479f3065eb60e118f993569`
- source metadata count: `7`
- total frozen source bytes: `63338314688`
- MemAvailable observed: `11023400960` bytes
- engine version: `2.4.4`
- historical payload read: `false`
- attempt consumed: `false`

These checks proved the local environment before spending the one-shot attempt.

## 6. Important pre-attempt failures and lessons

Two safe failures occurred before any P2 attempt consumption:

### Failure A — wrong system Python

The first attempted one-shot selected `/usr/bin/python3` = Python 3.14.4.
Import failed on missing `numpy` before any historical access.

Result:

- marker absent
- no source opened
- P2 not consumed

Permanent lesson:

Canonical P2 must use the frozen managed Python path above, never automatic system-Python discovery.

### Failure B — stale manually hardcoded patch hash

Runtime preparation initially compared the patch against an obsolete SHA (`15b6...`).
The actual patch at frozen R23A HEAD was correct; only the manually copied SHA was stale.

Result:

- stopped before uv/Python install
- no historical access
- marker absent
- P2 not consumed

Permanent lesson:

Patch identity must be derived from the exact Git HEAD, not copied from an older workflow/cache key.

## 7. P2 attempt-consumption semantics — immutable

Frozen R3 event:

`FIRST_CANONICAL_CANDIDATE_SIMULATOR_LANE_START_AFTER_EXACT_SOURCE_IDENTITY_VERIFICATION`

R22 final execution order is binding:

1. exact authorization contract
2. existing marker absent
3. output root pristine
4. preexecution memory gate
5. exact SHA/rows/bytes verification of all seven frozen sources
6. exact patched engine identity
7. first source opened read-only
8. first source validation
9. first R20 combined day context built
10. runtime memory gate
11. attempt marker written
12. first R21 simulator lane starts immediately next

No callback is allowed between marker write and first lane start.

If a failure occurs before marker:

`P2_ATTEMPT_CONSUMED=NO`

No automatic retry should be performed; diagnose first.

If marker exists:

- `P2_ATTEMPT_CONSUMED=YES`
- rerun forbidden
- resume forbidden
- automatic retry forbidden

Any post-marker failure is terminal evidence for this attempt.

## 8. Memory policy for actual canonical execution

Carry forward D6R14/R22 policy exactly:

- `PREEXEC_MIN_MEMAVAILABLE_BYTES=8442945536`
- `RUNTIME_MIN_MEMAVAILABLE_BYTES=4294967296`
- `ANON_GROWTH_ABORT_THRESHOLD_BYTES=536870912`
- process swap growth => abort
- total RSS is NOT a bounded-memory gate
- per-lane anonymous-memory baseline is captured AFTER engine binding

Reason:

The large historical NPY input is mmap/file-backed. Total RSS can approach mapped-file size and must not be misclassified as owned anonymous-state growth.

Never restore the old total-RSS memory gate.

## 9. R21/R22 behavioral constraints that remain binding

Natural EOF is valid.

Never use:

- fixed event quotas
- fixed wakeup quotas
- artificial requirement to reach a target timestamp after natural EOF
- order submit/cancel/modify calls after `EndOfData`

If an order remains working when the historical source naturally ends, it is unresolved/censored and the fresh per-lane engine is disposed safely. Do not issue a synthetic post-EOF cancel.

Execution layout:

- source opened once/day
- R20 context/raw pass once/day
- shared dense feature cache once/day
- shared file-backed midpoint index once/day
- 40 sequential lanes/day
- fresh exact hftbacktest engine per lane
- all candidates in a lane share that lane engine
- partition verified immediately after materialization
- R20 midpoint index closed before source mmap close

## 10. Canonical source and output information

Canonical output root:

`/home/emadh/Multi-Market/evidence/dev045_d6r26a_p2_candidate_labels_v1`

Canonical scratch root:

`/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_canonical_scratch`

Before the next one-shot these remain pristine and marker/failure/final manifest are absent.

R23A readiness already confirmed seven metadata records and total frozen source bytes `63338314688`.

The authoritative full SHA/rows/bytes check remains inside R22 immediately before historical preparation. Do not pre-read all ~63 GB a second time merely for convenience.

## 11. Immediate next step

NEXT STAGE:

`P2_CANONICAL_HISTORICAL_ONE_SHOT`

There is no additional design/preexecution stage required before it.

The next one-shot command must:

- execute from exact R23A HEAD `4e3e320931e896a6e479f3065eb60e118f993569`
- require clean worktree
- explicitly use `/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_exact_runtime_v1/py313/bin/python`
- prove pyarrow 25.0.1 and hftbacktest 2.4.4 identity before historical read
- rerun R23A metadata readiness locally
- invoke the frozen R22 successor runner
- verify all seven source SHA/rows/bytes before source opening
- stop on first failure
- never auto-retry

On canonical success expected:

- 7 completed source days
- 280 completed lanes
- 280 verified canonical partitions
- attempt marker present
- final manifest present
- failure artifact absent
- model fit still NO
- PnL still NO

After successful materialization the next stage is:

`P2_CANONICAL_READ_ONLY_AUDIT_FREEZE`

Only after audit/freeze may predictive-model design/fitting begin.

## 12. Future-chat continuation instruction

When a future ChatGPT conversation in the `market` project needs to continue this work:

1. Read this file first: `docs/MULTI_MARKET_PROJECT_HANDOFF_CURRENT.md` from branch `project/market-handoff-current`.
2. Treat the R23A execution branch/HEAD as immutable until the one-shot completes or fails.
3. Do not use stale local path `/mnt/c/Users/emadh/Downloads/market-exp026`.
4. Do not use system Python for canonical P2.
5. Do not rerun any frozen GREEN R19-R23A stages.
6. Check marker state before issuing any historical command.
7. If marker exists, never rerun/resume P2.
8. Preserve all historical PASS/FAIL/consumed evidence.
9. Answer operational continuation in Arabic and normally provide one terminal field at a time.
10. Never exit the user's terminal; preserve `TERMINAL_REMAINS_OPEN=YES`.

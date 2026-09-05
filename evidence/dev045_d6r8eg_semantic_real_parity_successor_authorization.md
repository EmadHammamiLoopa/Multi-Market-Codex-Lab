# DEV045 D6R8EG — Semantic Real Parity Successor Authorization

Status: **EXECUTION-READY AFTER EXACT CI GREEN; ONE LOCAL CANONICAL ATTEMPT ONLY**

Parent fix head: `eb0762ca4b3b69fd8966e20ee51d213ea5fcd301`.

Historical D6R8EF remains permanently frozen FAIL. Its canonical marker SHA256 is `f022ee78ce82f84a1d7e1fcfff376ff1fbdea988f2be3f79ef2f8886a0944cb6` and its evidence SHA256 is `4d42e51c91bc5950848c14e7f41ca576e5f64749fd512015f485cd14835d164f`. D6R8EG refuses to cross its attempt boundary unless both historical artifacts still match exactly.

The D6R8EF root cause was a deterministic upstream capacity bug: `buffer_size=128` could not hold 13,073 trade events. The fix commit reproduces the canonical stderr SHA exactly and restores the previously proven D6R2B capacities `buffer_size=496256` and `ss_buffer_size=1024`. The same fix also persists bounded child stdout/stderr diagnostics and parses the final JSON line after upstream progress messages.

D6R8EG is a separately named successor, not a rerun. It uses a new runtime root `/home/emadh/Multi-Market/runtime/dev045_d6r8eg`, marker `/home/emadh/Multi-Market/runtime/dev045_d6r8eg/ATTEMPT_STARTED.json`, and evidence `evidence/dev045_d6r8eg_semantic_real_parity.json`.

The source raw identities, exact 10-minute local-timestamp window, decompressed semantic slice identities, depth snapshot structure, upstream/old/V2 bindings, converter order, pairwise fieldwise exact NaN-equal parity, memory gates, and all downstream closed surfaces are unchanged.

CI must never open real raw data. Before local execution, exact branch/head, clean tracked worktree, pinned hftbacktest 2.4.4, minimum 8 GiB MemAvailable, absence of the D6R8EG marker/evidence, and intact frozen D6R8EF marker/evidence must all pass. The shell token `DEV045_D6R8EG_AUTHORIZE=YES_ONE_SHOT` is supplied only at the canonical attempt boundary.

The first D6R8EG result freezes PASS or FAIL. D6R8EG must never be rerun after its attempt marker exists.

Jan full-day, Feb-Jul, August, September+, non-BTC, policy replay, historical PnL, Railway, and live trading remain closed.

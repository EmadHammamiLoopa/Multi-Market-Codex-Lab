# DEV045 D6R26A P2 R22 — Final successor campaign runner/binding preauthorization

Parent R21 GREEN HEAD:

`a667c20be84a2e4496cd9d7ddb90fbba5237120b`

R22 is the final real callback binding before the separate one-shot
authorization/preflight stage.

R22 itself remains PREAUTHORIZATION ONLY and opens no Jan-Jul source.

## Exact pre-attempt order

The successor freezes:

1. authorization value validation;
2. existing marker check;
3. pristine output-root check;
4. preexecution memory gate;
5. exact SHA/bytes/rows verification of all seven frozen sources;
6. exact patched hftbacktest identity verification;
7. first source opened read-only;
8. first source input validation;
9. first R20 combined day context built;
10. runtime memory gate;
11. attempt marker written;
12. first R21 simulator lane starts immediately next.

No callback occurs between 11 and 12.

This matches R3:

`FIRST_CANONICAL_CANDIDATE_SIMULATOR_LANE_START_AFTER_EXACT_SOURCE_IDENTITY_VERIFICATION`

A first-day source/context/memory failure therefore does **not** consume P2.

## After marker

After successful marker publication:

- any failure is terminal;
- no rerun;
- no resume;
- no automatic retry;
- partial outputs remain evidence only;
- failure artifact is written.

## Daily execution

For each frozen day:

- one source mmap;
- one R20 context/raw pass;
- shared feature cache and midpoint index;
- 40 sequential lanes;
- fresh exact hftbacktest engine for each lane;
- one R21 materialization per lane;
- partition verified immediately;
- engine disposed every lane;
- midpoint memmap closed before source mmap;
- source mmap closed last.

Expected completion:

- 7 days;
- 40 lanes/day;
- 280 lanes;
- 280 verified Parquet partitions.

## EOF rule

The final R21 GREEN behavior is binding:

- natural EndOfData is valid;
- no fixed event quota;
- no fixed wakeup quota;
- no order request after EndOfData;
- final unresolved order is censored where source observability ends;
- fresh lane engine is then disposed safely.

## Memory rule

Correct D6R14 semantics are preserved:

- preexec MemAvailable >= 8,442,945,536 bytes;
- runtime MemAvailable >= 4,294,967,296 bytes;
- process swap growth aborts;
- anonymous growth > 512 MiB aborts;
- total RSS is not an abort gate.

For each lane, anonymous-memory baseline is captured **after hftbacktest engine
binding**, and checked again before engine close.

This avoids treating file-backed mmap residency as owned-state growth.

## Still sealed

R22 does not authorize:

- historical source opening;
- historical simulator execution;
- attempt-marker writing;
- canonical Jan-Jul output;
- model fit;
- model selection;
- threshold tuning;
- PnL;
- economic testing;
- live trading;
- August;
- September+;
- non-BTC.

`P2_ATTEMPT_CONSUMED=False`.

## Next

After R22 GREEN, only R23 remains before the one-shot P2 run.

R23 will be an authorization/preflight freeze. It will verify the exact R22
HEAD, worktree, file presence/size, output/scratch safety, engine identity,
memory availability, and absence of the attempt marker.

R23 itself will still not start a historical simulator lane.

# DEV045 D6R26A P2 R23 — Final one-shot readiness / authorization preflight

Parent R22 GREEN HEAD:

`016079a5fae640b4cd5f686aebdec2f7b556a4b3`

R23 is the final frozen stage before the explicit P2 one-shot historical
execution.

## R23 does not consume the attempt

R23 does not:

- call `np.load`;
- mmap any Jan-Jul source;
- hash any Jan-Jul payload;
- scan source rows;
- create the canonical scratch directory;
- write canonical Parquet;
- write the attempt marker;
- start hftbacktest on historical data;
- fit a model;
- calculate PnL.

`P2_ATTEMPT_CONSUMED=False`.

## Metadata-only source readiness

R23 checks only filesystem metadata for the seven frozen sources:

- exact path exists;
- regular file, not symlink;
- exact frozen file size.

The expensive and authoritative:

- SHA256;
- NPY row count;
- event validation

remain inside the R22 real execution path.

R22 performs them exactly once before the first source/context is prepared
and before the first simulator lane/attempt-consumption boundary.

This avoids reading roughly the full Jan-Jul payload twice.

## Repository readiness

R23 requires:

- exact R22 GREEN HEAD;
- clean worktree.

No execution is allowed from a modified or ambiguous local state.

## Output readiness

Canonical output must contain no files.

The existing P2 attempt marker must be absent.

Canonical scratch must either not exist or contain no files/symlinks.

R23 never deletes or cleans any path automatically.

## Engine readiness

R23 binds:

- hftbacktest version `2.4.4`;
- exact upstream commit
  `a244a14250b42d97fc305569c93c4117cd5e1dff`;
- frozen patched binary lineage SHA256
  `5174f486abc4b29cfef565672548798ea68ec54c0f6c04077bcbdf43f5033752`.

The runtime API/order-status identity is checked through frozen R5.

R23 does not pretend to recompute the binary SHA from an unspecified
installation artifact path; that hash remains a frozen, previously verified
lineage identity.

## Memory readiness

R23 applies the R22/D6R14 preexecution gate:

`MemAvailable >= 8,442,945,536 bytes`

No total-RSS gate is used.

Runtime swap/anonymous-memory gates remain inside R22 during the actual run.

## READY does not mean consumed

A successful R23 preflight returns:

`READY_FOR_EXPLICIT_ONE_SHOT_EXECUTION`

but still:

- no marker;
- no historical payload read;
- no historical simulator lane;
- no attempt consumption.

## Next

After R23 GREEN, the next command is the actual one-shot P2 execution.

That command will run this readiness preflight again locally immediately
before execution, then call the frozen R22 real successor hooks.

R22 will then:

1. re-verify all seven sources with exact SHA/rows/bytes;
2. verify exact engine API identity;
3. open/build the first day context;
4. perform final memory checks;
5. write the attempt marker;
6. immediately start the first historical simulator lane.

Only step 6 consumes P2 according to the frozen R3 event.

After the marker exists there is no rerun, resume, or automatic retry.

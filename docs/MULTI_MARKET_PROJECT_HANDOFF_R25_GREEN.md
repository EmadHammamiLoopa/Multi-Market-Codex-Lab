# Multi-Market Codex Lab — R25 GREEN Milestone

Updated: 2026-09-10

This milestone supplements `docs/MULTI_MARKET_PROJECT_HANDOFF_CURRENT.md` on branch `project/market-handoff-current` and records completion of the R25 stage described there.

## R25 status

Experiment:

`DEV045-D6R26A-P2-R25`

Branch:

`research/dev045-m6-d6r26a-p2-r25-durable-day-context-bundle-foundation`

Exact R25 HEAD:

`f9a2b4217f4ae291871b3fac6ff210c88187ed5b`

Exact parent R24 HEAD:

`4abe7e0c3807c97a18226fddf1ac51ed81937c85`

Dedicated GitHub Actions workflow:

`dev045-d6r26a-p2-r25-durable-day-context-bundle-foundation`

GREEN run:

`34505595313`

GREEN job:

`102966878304`

CI conclusion:

`success`

All dedicated stages passed:

- install narrow test surface
- R25 durable-bundle foundation synthetic tests
- pre-attempt/non-historical contract proof
- historical-execution surface guard

## R25 implemented surface

R25 is generic durable persistence/reopen/verification only.

It implements:

- `DurableSourceIdentity(day, path, rows, bytes, sha256)`
- exact R24 day-file set
- `.npy` persistence of R20 feature-cache arrays
- exact byte-preserving copy of R20 midpoint binary
- SHA256 + byte identity for every durable data file
- dtype + shape identity for all array files
- R20 bounds + feature-summary persistence
- unique same-filesystem staging directory
- fsync before publication
- completion manifest written last
- atomic staging-directory publication
- fail-closed behavior if final bundle already exists
- exact file-set verification
- read-only `.npy` mmap reopen
- read-only midpoint memmap reopen
- reconstruction of `r18.DenseFeatureCache`
- reconstruction of `r17.FeedBounds`
- reconstruction of `r19.FeatureCacheBuildSummary`
- reconstruction of `r20.DayContextBuildResult`
- revalidation of the reopened R20/R18 consumer surface
- explicit close that preserves durable files

Synthetic tests prove exact roundtrip parity of feature arrays, midpoint records, bounds, and feature summary. Corrupt arrays, source-identity mismatch, missing manifest, and attempted overwrite fail closed.

## Critical unchanged state

R25 did NOT open Jan-Jul historical source data.

R25 did NOT run hftbacktest historical simulation.

R25 did NOT write the P2 attempt marker.

R25 did NOT write canonical labels.

R25 did NOT fit any model.

R25 did NOT compute PnL.

Therefore:

`P2_ATTEMPT_CONSUMED=NO`

The unique P2 historical simulator attempt remains available.

No August, Sep-01+, or non-BTC data was opened.

## Immediate next stage

NEXT:

`DEV045-D6R26A-P2-R26`

R26 is the real Jan-Jul durable-context materializer successor and must be built from exact R25 HEAD:

`f9a2b4217f4ae291871b3fac6ff210c88187ed5b`

Before any R26 historical execution, freeze and test:

- exact source-registry binding and source identity verification order
- exact durable root `/home/emadh/Multi-Market/runtime/dev045_d6r26a_p2_durable_context_v1`
- existing completed-day reuse semantics
- partial/staging residue semantics
- source-validation semantics
- memory admission thresholds
- concurrency policy with hard maximum <= 4
- whether expensive SHA/validation/R20 scan phases are serialized or separately admitted
- stop-first-failure behavior
- no simulator lane
- no attempt marker
- no canonical labels
- no model fit/PnL

R26 durable context creation remains PRE-ATTEMPT. Do not launch the canonical historical simulator until all seven durable day bundles have completed and passed a read-only audit/freeze.

## Continuation rule

Future market-project chats should read both:

1. `docs/MULTI_MARKET_PROJECT_HANDOFF_CURRENT.md`
2. `docs/MULTI_MARKET_PROJECT_HANDOFF_R25_GREEN.md`

Treat R25 HEAD and GREEN run above as frozen evidence. Never rerun R25 historical work because R25 contains no historical work; any changes belong in a new successor stage. Never mutate R24/R25 frozen GREEN commits.

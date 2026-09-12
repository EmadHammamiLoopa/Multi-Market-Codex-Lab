# Multi-Market Codex Lab — R27P24 Preexecution Ready

Updated: 2026-09-12

This handoff records the current DEV045 D6R26A P2 state after the successful R27P23 January full-day RSS proof and the completed/frozen R27P24 July worst-case full-day RSS preexecution design. It is documentation only and does not consume the canonical P2 attempt.

## Binding governance

- Consumed stays consumed.
- Frozen PASS/FAIL/INVALID results are immutable.
- Do not rerun an experiment ID after its registered scientific result is consumed/frozen.
- No rescue threshold widening under the same experiment ID.
- Sep-01+ BTC remains sealed.
- Other markets remain sealed.
- No PnL, model fit, simulator lane, canonical labels, or attempt marker in R27P24.
- `P2_ATTEMPT_CONSUMED=NO` remains binding until the first canonical candidate simulator lane starts after exact source identity verification.

## R27P23 frozen scientific result

R27P23 proved the smallest full January day can be processed through the file-backed corrected context path within the preregistered 12 GiB process RSS ceiling.

Result artifact:

`evidence/dev045_d6r26a_p2_r27p23_jan_full_day_rss_result.json`

Result-frozen HEAD:

`138b7f91031f2548b1dbd486cbc4088911fd967b`

Key result:

- source day: `2026-01-01`
- rows: `64,314,723`
- source bytes: `4,116,142,528`
- source SHA256: `8f0a4fbd56ecdc261dbe2041ce138a09456423074925d495272716219a1d4da1`
- internal peak RSS: `5.951721 GiB`
- registered ceiling: `12.0 GiB`
- January full-day RSS gate: `PASS`
- simulator run: `NO`
- canonical labels: `NO`
- P2 attempt consumed: `NO`

The old shell/subshell external watchdog reading from R27P23 is explicitly invalid as worker RSS evidence and must not be reused.

## R27P24 objective

`DEV045-D6R26A-P2-R27P24` is a candidate-only PREATTEMPT memory proof on the frozen largest Jan-Jul BTC source: July.

It is designed to answer only whether the same exact file-backed corrected context path remains safely bounded on the worst frozen day before any durable Jan-Jul build is attempted.

### Exact July source

- day: `2026-07-01`
- path: `/home/emadh/Multi-Market/runtime/dev045_d6r4b/output/BTCUSDT_2026-07-01.npy`
- rows: `181,084,390`
- bytes: `11,589,401,216`
- SHA256: `85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f`
- nominal local window: `2026-07-01 00:00:00` through `2026-07-02 00:00:00` exclusive

July is the largest frozen Jan-Jul source by both rows and bytes.

### File-backed capacity and gates

- raw file-backed capacity: `181,084,390 × 265 = 47,987,363,350 bytes`
- disk gate: raw file-backed capacity + `16 GiB` headroom
- process RSS ceiling: `12 GiB`
- start admission: `MemAvailable >= 12 GiB`
- hard system-memory abort: `MemAvailable < 8 GiB`
- worker count: exactly one supervised Python worker
- watchdog poll interval: `0.25 s`
- watchdog reads the actual Python worker PID, correcting the invalid shell/subshell monitoring pattern from R27P23.

If the actual worker exceeds the preregistered process RSS ceiling or the system falls below the preregistered memory floor, that is a scientific R27P24 memory FAIL and must be frozen; the threshold must not be widened and the same R27P24 result must not be rerun as a rescue.

## Exact R27P24 lineage

Parent result-frozen R27P23:

`138b7f91031f2548b1dbd486cbc4088911fd967b`

R27P24 development branch:

`research/dev045-m6-d6r26a-p2-r27p24-july-worst-case-full-day-file-backed-rss-preexecution`

R27P24 final preexecution HEAD:

`da3eb986710b236f03a0b5b31a5d25a2c25285b8`

Dedicated GitHub Actions run:

`34695473262`

CI status:

- status: `completed`
- conclusion: `success`
- preexecution tests: `success`
- CI real-execution closure proof: `success`

Frozen preexecution branch:

`research/dev045-m6-d6r26a-p2-r27p24-july-worst-case-full-day-file-backed-rss-preexecution-frozen`

The frozen branch is exactly identical to:

`da3eb986710b236f03a0b5b31a5d25a2c25285b8`

## R27P24 forbidden surfaces

The frozen preexecution contract does not authorize:

- reference rerun
- new real parity claim
- durable context publication
- full Jan-Jul materialization
- simulator lane
- attempt marker write
- canonical candidate label write
- model fit
- PnL
- August
- Sep-01+
- non-BTC
- market raw archive

`P2_ATTEMPT_CONSUMED=NO` remains required.

## Next controlled action

Run the R27P24 authorized local July full-day supervised RSS probe from the exact frozen preexecution HEAD only.

Before execution, verify:

1. exact branch/HEAD identity,
2. clean tree,
3. exact runtime,
4. no canonical P2 marker/artifact exists,
5. scratch root does not already exist,
6. disk free satisfies the R27P24 dynamic disk gate,
7. MemAvailable satisfies the 12 GiB start gate.

Then execute the single authorized R27P24 July probe. Do not run any simulator or durable Jan-Jul materialization in the same step.

After the result:

- PASS: freeze the exact scientific result and only then decide whether full Jan-Jul durable materialization is safe to reopen.
- scientific memory FAIL: freeze the FAIL; no same-ID rescue rerun.
- engineering/precondition failure before the July worker meaningfully runs: preserve evidence, diagnose, and use a new controlled successor only if needed.

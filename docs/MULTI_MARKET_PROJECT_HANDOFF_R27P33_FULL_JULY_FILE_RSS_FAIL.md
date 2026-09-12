# Multi-Market Codex Lab — Handoff through R27P33

Updated: 2026-09-13

## Binding governance

- Historical scope remains Jan–Jul only; no August.
- `P2_ATTEMPT_CONSUMED=NO` remains binding.
- Worker RSS ceiling remains exactly 12 GiB; threshold widening is forbidden.
- No simulator, canonical labels, model fit, PnL, Sep-01+, non-BTC, or `market-raw-archive` access is authorized.
- Durable experiment outcomes are immutable and must not be rerun under the same experiment ID.
- Use narrow differential tests; do not repeat long CI parity that only re-proves frozen parent semantics.

## Frozen lineage immediately before R27P33

### R27P31 — corrected-feature window parity

- experiment: `DEV045-D6R26A-P2-R27P31`
- GREEN/frozen HEAD: `8492cca69ae6902cb6167f3e86fae44707fb6bc2`
- CI run: `34720214998`
- CI job: `103624590789`
- result: success, `3 passed in 961.47s`
- proves exact corrected feature semantics with bounded decision-output mappings and state carried across chunks.

### R27P32 — real 5M composed RSS proof

- experiment: `DEV045-D6R26A-P2-R27P32`
- preexecution HEAD: `a00be6fc5379caf0557106c93818d129e006b0b4`
- frozen result commit: `3df52a7d2a2ae98ba3757141715bc7af0eb0110d`
- classification: `ENGINEERING_5M_COMPOSED_PASS`
- rows: `5,000,000`
- peak worker RSS: `652,070,912 bytes` = `0.6072883605957031 GiB`
- min MemAvailable: `34.09589767456055 GiB`
- raw elapsed: `41.83454069799336 s`
- feature elapsed: `2.0887714279961074 s`
- worker logical elapsed: `43.92575191699143 s`
- supervisor wall elapsed: `203.63205470200046 s`
- no watchdog trip; worker rc `0`
- R27P32 rerun forbidden.

## R27P33 — immutable full-July RSS failure

Experiment: `DEV045-D6R26A-P2-R27P33`

Preexecution/frozen runner HEAD:

`eee999fe9b59d8c722085fe7fd496aecf1705877`

Frozen result branch:

`research/dev045-m6-d6r26a-p2-r27p33-full-july-composed-rss-result-frozen`

Frozen result commit:

`fb8461c7767972643f9d0e9e6faa28bb1904b147`

Frozen result artifact:

`evidence/dev045_d6r26a_p2_r27p33_full_july_composed_rss_result.json`

Classification:

`ENGINEERING_FULL_JULY_COMPOSED_FAIL`

Exact execution scope:

- frozen July source only;
- full `181,084,390` rows;
- no source rehash;
- one worker;
- 12 GiB worker RSS ceiling;
- start admission `MemAvailable >= 12 GiB`;
- hard system abort `< 8 GiB`;
- watchdog `0.25 s`;
- no P2 attempt marker, labels, simulator, model, or PnL.

Observed result:

- elapsed: `2299.0948590759945 s` = about `38.32 min`;
- peak worker RSS: `12,922,388,480 bytes` = `12.034912109375 GiB`;
- ceiling: `12,884,901,888 bytes`;
- excess: `37,486,592 bytes` = `35.75 MiB`;
- min MemAvailable: `33.07004928588867 GiB`;
- watchdog trip: `worker_rss_above_12_gib:12922388480`;
- worker rc: `-15`;
- worker result absent because watchdog terminated execution;
- `P2_ATTEMPT_CONSUMED=NO`.

Peak memory decomposition:

- `RssAnon = 157,073,408 bytes` ~= `149.8 MiB`;
- `RssFile = 12,765,315,072 bytes` ~= `11.889 GiB`;
- `RssShmem = 0`;
- smaps `Private_Clean = 12,744,617,984 bytes`;
- smaps `Private_Dirty = 157,073,408 bytes`.

### R27P33 diagnosis

This is not an anonymous-memory or algorithmic-state explosion. The failure is overwhelmingly file-backed residency.

The source `.npy` is `11,589,401,216 bytes` (~10.793 GiB). R27P33 keeps the full source `np.load(..., mmap_mode="r")` mapping open while R27P29 walks column slices. R27P29 chunks the logical kernel work and output mappings, but its API receives arrays backed by that full-file mapping. As the full day is traversed, source pages can accumulate as resident file-backed pages.

After the raw pass, R27P32/R27P33 also construct full-prefix raw `np.memmap` arrays for the R27P31 feature consumer. R27P31 processes decision chunks, but its input arrays are still full-file mappings. Therefore bounded computation/output windows do not by themselves guarantee bounded file-backed RSS.

The R27P33 memory decomposition strongly supports this diagnosis: anonymous RSS stayed near 150 MiB while file-backed RSS reached ~11.889 GiB.

R27P33 must not be rerun. The correct successor must change mapping lifetime/residency, not the 12 GiB threshold.

## Frozen source identity

- day: `2026-07-01`
- source: `/home/emadh/Multi-Market/runtime/dev045_d6r9b/output/BTCUSDT_2026-07-01.npy`
- rows: `181,084,390`
- bytes: `11,589,401,216`
- SHA256: `85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f`
- logical raw file-backed capacity: `47,987,363,350 bytes`

## Next experiment — R27P34

R27P34 must be a mapping-residency correction only. It must preserve R27P29/R27P31 semantics and exact scientific thresholds.

Required engineering changes:

1. Source input must be mapped by bounded row windows directly from the `.npy` payload, with each source window unmapped/released after the R27P29 stateful kernel consumes it. Do not keep a single full-source mmap alive through the full-day scan.
2. Corrected-feature consumption must not allow full raw-input memmaps to accumulate resident pages across the day. Use bounded input mapping/release or an explicit Linux page-release mechanism with a hard bounded-residency contract.
3. Preserve R27P29 state across source windows and R27P31 rolling state across decision windows exactly.
4. Reuse frozen parity semantics; do not run another long parent-parity CI. Add only a narrow differential synthetic proof for mapping-boundary correctness if needed.
5. Before another full-July attempt, use a short real prefix probe that proves file-backed RSS stays bounded as more source windows are traversed. A prefix substantially larger than 5M should be chosen only to test residency scaling, not scientific behavior.
6. R27P34 must remain engineering-only: `P2_ATTEMPT_CONSUMED=NO`.

## Forbidden reruns

R27P26, R27P27, R27P32 and R27P33 are immutable. Do not rerun them or widen the 12 GiB ceiling.

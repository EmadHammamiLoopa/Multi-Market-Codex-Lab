# DEV030-P9 Implementation Freeze

## Status
IMPLEMENTATION_FROZEN_REMOTE_CHECKS_PASS

Scientific execution commit:
`7630effcbf84b4342bd7068cd4b49b411fa18ee1`

Recovered frozen design base:
`f7f7731a29c39045b71c9034bdbc984ef83fc178`

## Frozen P9 files
- `src/multimarket/dev030_p9_price_dense_sequence.py`
  - SHA256: `773bd58bf9b5bde65aaf914a27c923157edce11572dc17c08759e1861366d7e6`
- `tests/test_dev030_p9_price_dense_sequence.py`
  - SHA256: `ad15737278c15a58e4da3d1034e0a70b441c83d35f752fb8327d3ad233310629`

## Frozen representation
- Target A / 120s / 16bp / 32s
- C0 = exact P8 probability-first PRICE S1 baseline
- C1 = C0 + 96 dense causal PRICE values
- 3 channels x lags 32s..1s
- total C1 feature count = 119
- exact support reproduction required
- exact P8 C0 reproduction required before C1 evaluation
- L2 logistic only, frozen C grid
- chronological outer/inner folds
- train-only scaling
- no lag/window/channel/model search
- no OFI
- no calibration
- no threshold/PnL optimization
- no forward August/September consumption

## Regression and identity checks
At the P9 scientific commit, all previously frozen DEV030 P3-P8 source/test SHA256 values were recomputed and matched exactly.

P8:
- source `6b2ad4c0d35450b799c6cbcf303158f413227692b94512368c5853390575d6ed`
- test `e1ed717e63ff9201721c33a987188fad5165ba43edb04f9e86902a8e90ad82a0`

P7:
- source `c22820ff7afe5ea84c07634a3579dc9474e0c7c31a2ae9fdad479d8ddb806c82`
- test `56061f24f7eba5e8a03781e494cdf987a40e18cda80a0f586a2321af98422626`

P6:
- source `4e6bf7c30173e7cd470ab6088bf5229d5980bb0542803f8968e62722f567b93e`
- test `1d72ba591b92b132bbcd2bf8cc2ad700eb2a181e4a0e27dfff44b43b931d7c5d`

P5:
- source `eaa250edecfdf73221fe711001b447982737f7ffd4f4dba9f6d96a79ed913214`
- test `b2c82bc5b2355690881029db976420bb7e0dbb8162677cc468ac924e8947e7d6`

P4:
- source `bcab35f909fdb732a399e40d042689de5d254c5a6372b0abe18146c81c0c522f`
- test `7fde9b155e1d441252023b94225d3ec4f540a87847fb7ee3f6ae181579d5c265`

P3:
- source `9730f62cd6e2ee2a84cb402a890629f7335eb42b730f24f69ffca971281ba675`
- test `a3d57a928d6a2dedc762111e1859fa9d290ee084412d7c613f7541398e46360b`

## GitHub boundary review
Comparison from frozen design base `f7f7731...` to scientific commit `7630eff...` contains only:
- CI workflow correction
- new P9 source
- new P9 tests

No earlier frozen scientific source/test was modified.

## CI validation
GitHub Actions run:
`33576707732`

- Python 3.12: 789 tests, OK
- Python 3.10: 789 tests, OK

## Storage seal
During P9 design/implementation/freeze:
- `market-raw-archive` remains analytically unopened
- `abundant-love` volume remains analytically unopened
- all project Railway volumes remain analytically unopened
- no listing/download/upload/mutation/deletion was performed

These assets are reserved for later confirmation only and must remain sealed until the development protocol/model is fully frozen.

## Real-run boundary
Remote implementation freeze is complete.

The canonical Jan-Jul one-shot is NOT yet executed from GitHub because the canonical development data and frozen evidence artifacts live under the local WSL `/home/emadh/Multi-Market` environment and are intentionally not uploaded to GitHub or read from Railway.

Before the one-shot, local read-only preflight must confirm:
1. checkout/HEAD exactly `7630effcbf84b4342bd7068cd4b49b411fa18ee1`;
2. P9 source/test SHA256 exactly as above;
3. frozen P2C/P3/P4/P5/P6/P7/P8 artifact SHA256 identities;
4. authorized Jan-Jul manifest unchanged;
5. canonical P9 output directory absent;
6. no August/September or Railway storage opened;
7. clean worktree.

Only after those checks pass is the canonical P9 Jan-Jul one-shot authorized.

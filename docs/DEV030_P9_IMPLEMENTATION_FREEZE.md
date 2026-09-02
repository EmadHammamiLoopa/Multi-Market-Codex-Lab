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


---

## Corrected final freeze after local WSL preflight

The earlier freeze candidate `7630effcbf84b4342bd7068cd4b49b411fa18ee1`
is superseded and MUST NOT be used for the canonical run. Local WSL validation
exposed two test-harness defects only; no model fit and no canonical artifact
were produced.

Final scientific execution commit:
`da40e643293bc1011f6cba2853482253e7b9a891`

Final P9 identities:
- source SHA256:
  `773bd58bf9b5bde65aaf914a27c923157edce11572dc17c08759e1861366d7e6`
- test SHA256:
  `abc407b89ccccc73747d5985d1886adf47f6642de0b23bd59d3cf79ed4ac1277`

Local WSL focused validation:
- Python 3.14.4
- numpy 2.5.2
- scikit-learn 1.9.0
- pytest 7.4.3
- P9 focused tests = 32 passed

GitHub Actions run:
`33577957284`
- Python 3.12 = 789 tests, OK
- Python 3.10 = 789 tests, OK

Final local read-only preflight:
- exact HEAD = PASS
- clean worktree = PASS
- P3-P8 frozen source/test identities = PASS
- frozen dependency identities = PASS
- P2C-P8 canonical artifact identities = PASS
- prior protocol state = PASS
- Jan-Jul authorized manifest = PASS, 7/7
- P9 frozen protocol contract = PASS
- canonical P9 output absent = PASS
- git diff check = PASS
- no model fit = confirmed
- no P9 artifact created = confirmed
- no Railway command executed = confirmed

Storage remains sealed for P9:
- market-raw-archive not used
- abundant-love volume not used
- project Railway volumes not used

Status:
`P9_IMPLEMENTATION_FROZEN_LOCAL_PREFLIGHT_PASS_REAL_ONE_SHOT_AUTHORIZED`

Only the commit
`da40e643293bc1011f6cba2853482253e7b9a891`
may be used for the one-shot canonical Jan-Jul P9 execution.


---

## Final corrected execution candidate after aborted pre-result attempt

Scientific execution commit:
`91a8532cfb6daca7e8c0eb0a263a8cab92e0d81c`

Reason for superseding `da40e643293bc1011f6cba2853482253e7b9a891`:
the first canonical invocation aborted before C1 evaluation and before artifact
writing because P9 used P9-specific C0/label hash domains while requiring exact
hash equality with the frozen P8 C0 artifact.

Read-only inspection after the aborted attempt confirmed the canonical output
directory did not exist. Therefore no scientific P9 result was produced and the
no-rerun-after-artifact rule was not triggered.

Correction:
- C0 prediction hash domain preserved exactly from P8;
- label hash domain preserved exactly from P8;
- C1 prediction hash remains P9-specific;
- no target, feature, support, fold, model, C grid, metric, gate, null rule,
  or data boundary changed.

Validation:
- local focused tests: 34 passed;
- local direct P8/P9 C0 prediction hash equality: TRUE;
- local direct P8/P9 label hash equality: TRUE;
- local canonical output absent: TRUE;
- GitHub Actions run `33578579742`;
- Python 3.12: 789 tests, OK;
- Python 3.10: 789 tests, OK.

Code-path audit confirms the P9 C0 path matches frozen P8 in C selection,
scaling, LogisticRegression configuration, fold order, metrics, and hashing.

Status:
`P9_FINAL_CORRECTED_EXECUTION_CANDIDATE_VALIDATED`

Only `91a8532cfb6daca7e8c0eb0a263a8cab92e0d81c` is eligible for the next
canonical Jan-Jul invocation. Documentation-only descendants are not scientific
execution commits.

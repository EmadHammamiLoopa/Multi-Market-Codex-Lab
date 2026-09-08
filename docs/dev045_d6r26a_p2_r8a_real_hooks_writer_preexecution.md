# DEV045 D6R26A P2 R8A — Real hooks/writer pre-execution

Parent R7:

- branch: `research/dev045-m6-d6r26a-p2-r7-canonical-historical-binding-preexecution`
- HEAD: `a167f39dd6bf50e43d8f2bc67feab0a60729248a`
- R7 dedicated CI: GREEN
- frozen R6 source registry: 7/7 Jan–Jul consumed-development sources
- P2 attempt consumed: NO

R8A implements the mechanical real-I/O boundary needed by the later canonical
candidate-label materialization, but it does **not** authorize or execute it.

Implemented but unbound:

1. exact source verification adapter using the frozen R6 verifier;
2. read-only bounded-memory NPY mmap opening;
3. one validation pass per opened day before creating lane engines;
4. lazy `hftbacktest 2.4.4` engine factory using the already-frozen
   GTX / risk-adverse queue / PartialFillExchange / 250 ms + 250 ms semantics;
5. zero-fee engine ledger because P2 creates labels, not economic PnL;
6. write-temp → fsync → hash verify → atomic rename-once publisher;
7. partition bytes/SHA/row-count verification;
8. canonical control-artifact write primitive;
9. R4-compatible RunnerHooks surface that is deliberately sealed.

## Critical fail-closed boundary

R8A does **not** freeze the feature/label lane executor.

`run_lane` therefore terminates with:

`FEATURE_LABEL_EXECUTOR_NOT_FROZEN`

The R8A RunnerHooks also leave `verify_source`, historical source opening,
attempt-marker writing, partition verification, failure writing, and final
manifest writing sealed.

Therefore even possession of the already-frozen R3 authorization token cannot
consume the P2 attempt through the R8A RunnerHooks.

## CI restrictions

R8A CI:

- does not install `hftbacktest`;
- does not import the simulator;
- does not open Jan–Jul historical files;
- does not hash Jan–Jul historical files;
- does not start candidate simulation;
- does not write the canonical attempt marker;
- does not write canonical labels;
- does not fit models;
- does not compute PnL;
- does not open August;
- does not open September+;
- does not open non-BTC data.

The mmap and writer implementations are tested only with temporary synthetic
fixtures.

## Next

Next is **R8B feature/label lane-executor freeze**.

R8B must freeze the exact mathematics and event-time semantics for every
P0 feature before any historical candidate lane can start. In particular it
must specify the exact causal definitions for microprice/VAMP, L1/L5
imbalance, BBO OFI, trade/add/cancel imbalance, depth changes, spread change,
realized volatility, and the candidate-price execution-state fields.

Only after R8B is GREEN and frozen may a separate execution-binding layer
combine R4 + R8A + R8B and create the one-shot Jan–Jul candidate-label
materialization authorization.

`NO ECONOMIC STRATEGY EXECUTION / NO PNL / CANDIDATE LABEL SIMULATION ONLY`

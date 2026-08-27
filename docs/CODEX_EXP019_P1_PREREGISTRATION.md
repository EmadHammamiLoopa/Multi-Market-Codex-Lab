# CODEX-EXP-019-P1 Preregistration

Status: **PREREGISTERED BEFORE ANY AUG-01 ANALYTICAL OPENING**

Date: 2026-08-27

Experiment ID: `CODEX-EXP-019-P1`

Parent preserved commit:

`00a2aca3764562d3e8c0c27d3626d93db0fc6492`

Parent frozen outcome:

`CODEX-EXP-018-P1 = INVALID`

EXP018 invalid artifact SHA-256:

`4d48612201f5597b5e6b9a0ed423f0fd131bdc31473d11238c96149749748f44`

EXP018 recorded scientific state at failure:

- sealed_aug1_analytically_opened = false
- target_scored = false
- model_fit = true
- auc_scored = false
- older_august_holdout_opened = false
- direction_scored = false
- pnl_scored = false
- network_accessed = false

Therefore the Aug-01 predictive holdout remained analytically unopened.

## Correction scope

EXP019 is an **implementation-only correction** of EXP018.

Every scientific choice from EXP018 remains unchanged:

- hypothesis
- symbol
- Jan-Jul training calendar
- Aug-01 validation day
- target
- decision grid
- entry delay
- horizon
- label threshold
- primary feature
- R diagnostic benchmark
- model
- scaling
- random seed
- timing placebo
- positive-control canary
- common support
- metrics
- non-overlap subset
- all 10 promotion gates
- status mapping
- no direction
- no PnL

The only material implementation change is the sealed-artifact access mechanism.

## Root cause being corrected

EXP018 reused `codex_research.sha256_file()` for the authorized Aug-01 validation artifact.

That generic helper calls `assert_unsealed_path()`, which rejects `2026-08-01` because it remains in the global `SEALED_DAYS` set.

EXP019 must **not modify or weaken that global seal**.

Instead, EXP019 introduces a local exact-artifact authorization mechanism.

## Exact authorized Aug-01 artifact

The only sealed predictive artifact EXP019 may open is exactly:

`/home/emadh/Multi-Market/evidence/codex/exp017_aug1_phase_l_derived/BTCUSDT/2026-08-01_FEATURES250.csv`

Expected SHA-256:

`62c72f13f7176d9b4d9bdb69ad940cdcc56858698d64b4a061cecbb4a09ec5f5`

Authorization requires **both**:

1. resolved path equals the exact frozen authorized path;
2. raw-byte SHA-256 equals the frozen expected digest.

The hash for this one file must be computed with a local opaque-byte `hashlib.sha256` reader that does not call the generic sealed-day rejection helper.

After path and hash verification pass, the exact same file may be parsed once by the frozen Phase-L loader for EXP019 validation.

No directory-level exemption is allowed.

No wildcard authorization is allowed.

No alternate Aug-01 filename is allowed.

No symlink or alternate resolved path is allowed.

## Still-forbidden August scope

EXP019 must not access:

- 2026-08-04 through 2026-08-23
- any other August day
- ETH August data
- any replacement Aug-01 artifact
- any raw August file
- network sources

The generic research seal remains unchanged for all other code and paths.

## Frozen upstream provenance

EXP019 must verify before Aug analytical parse:

### EXP018 invalid lineage

Artifact:

`evidence/codex/exp018_p1_independent_volatility_aug1/INDEPENDENT_VOLATILITY_AUG1.json`

SHA-256:

`4d48612201f5597b5e6b9a0ed423f0fd131bdc31473d11238c96149749748f44`

Required fields:

- experiment_id = `CODEX-EXP-018-P1`
- status = `INVALID`
- failure_type = `ResearchSealError`
- sealed_aug1_analytically_opened = false
- target_scored = false
- auc_scored = false

### EXP017 structural parent

Artifact:

`evidence/codex/exp017_p0_aug1_phase_l_generation/AUG1_PHASE_L_GENERATION.json`

SHA-256:

`97c76a19a34971c7cef9eb01ad6c5b39d4e2c9885ed39a41054adef397ce4561`

Required status:

`AUG1_PHASE_L_FEATURES_GENERATED_AND_INTEGRITY_PASS`

## Frozen scientific question

Does the single causal trailing realized-volatility state variable `rv_30m_bps` independently rank occurrence of the already-frozen 10-minute executable opportunity target on BTCUSDT 2026-08-01?

R remains a diagnostic benchmark only.

VOL does not need to outperform R to pass.

## Frozen symbol and calendar

Symbol:

`BTCUSDT`

Training days exactly:

- 2026-01-01
- 2026-02-01
- 2026-03-01
- 2026-04-01
- 2026-05-01
- 2026-06-01
- 2026-07-01

Validation day exactly:

`2026-08-01`

No ETH.

No other August date.

## Frozen target

Unchanged from EXP018 / EXP004:

- decision grid = 60 seconds
- entry = t + 250 ms
- exit = entry + 600 seconds
- long gross bps = `10000 * log(bid_exit / ask_entry)`
- short gross bps = `10000 * log(bid_entry / ask_exit)`
- oracle magnitude = max(long, short)
- label = oracle gross bps >= 24.0

Direction remains hidden from legitimate model inputs.

No trading PnL.

## Frozen primary feature

Primary legitimate feature:

`rv_30m_bps`

Exactly the frozen EXP004 construction:

- trailing 30 minutes
- 1-minute sampled causal mids
- log-return realized volatility
- `10000 * sqrt(sum(r^2))`
- full causal book-valid window
- no future data
- no forward fill

No additional primary feature.

## Frozen R benchmark

Use exactly the frozen EXP004 `R_FEATURE_NAMES` block.

R is diagnostic only and is not a PASS gate.

## Frozen training and models

Train only on BTCUSDT Jan-Jul consumed sandbox data.

Same model as EXP018:

- StandardScaler fit on training only
- LogisticRegression
- C = 1.0
- penalty = l2
- solver = lbfgs
- class_weight = none
- max_iter = 1000
- random_state = 20260825

Tracks:

1. VOL primary: `rv_30m_bps`
2. VOL_TIME_PLACEBO
3. R_BENCHMARK
4. CANARY_VOL positive control

No Aug fit, refit, threshold tuning, or calibration.

## Frozen timing placebo

Unchanged from EXP018.

For each Jan-Jul training day independently:

- keep VOL features fixed
- permute labels within that day only
- deterministic seed:
  `20260825|VOL_TIME_PLACEBO|BTCUSDT|YYYY-MM-DD`

August labels remain untouched.

## Frozen canary

Unchanged from EXP018.

Training inputs:

- `rv_30m_bps`
- forbidden same-decision oracle gross magnitude

Validation sensitivity control uses corresponding Aug oracle magnitude.

Canary can never be promoted.

## Frozen common support

All four tracks are scored on the exact same Aug valid-R support.

No options-flow support.

No post-hoc subset.

## Frozen metrics

Full support and deterministic non-overlap 10-minute subset:

- n
- prevalence
- ROC AUC
- average precision
- AP/prevalence
- Brier score
- Brier skill
- log loss
- top-decile precision
- top-decile lift
- top-quintile precision
- top-quintile lift
- calibration intercept/slope diagnostic

## Frozen promotion gates

PASS requires all 10 EXP018 gates unchanged:

1. VOL full-support ROC AUC >= 0.60
2. VOL AP/prevalence >= 1.30
3. VOL Brier skill > 0
4. VOL top-decile lift >= 1.50
5. VOL non-overlap ROC AUC >= 0.57
6. VOL non-overlap top-decile lift >= 1.25
7. VOL AUC - VOL_TIME_PLACEBO AUC >= 0.03
8. CANARY_VOL AUC - VOL AUC >= 0.10
9. Aug valid-R support contains both target classes
10. all implementation/provenance/causality invariants pass

No gate may be altered after output.

## Frozen status mapping

PASS:

`INDEPENDENT_VOLATILITY_REGIME_PREDICTABILITY_CONFIRMED`

Valid predictive failure:

`FAIL_INDEPENDENT_VOLATILITY_REGIME_NOT_CONFIRMED`

Implementation/provenance/causality failure:

`INVALID`

## Required corrected invariants

In addition to EXP018 invariants:

- EXP018 invalid artifact SHA exact
- EXP018 invalid state proves Aug remained analytically unopened
- EXP017 artifact SHA exact
- exact authorized Aug path match
- exact Aug FEATURES250 SHA match before parse
- global `codex_research.py` seal source remains unmodified from parent
- no generic sealed-day exemption introduced
- no older August path opened
- no network access
- no direction scored
- no PnL scored

## Scientific guards after valid predictive execution

Expected true:

- sealed_aug1_analytically_opened
- target_scored
- model_fit
- auc_scored

Must remain false:

- older_august_holdout_opened
- direction_scored
- pnl_scored
- network_accessed

## No-rescue rule

Once EXP019 output exists, never rerun EXP019.

Do not change any scientific choice inherited from EXP018.

Do not change the authorized path or digest.

Do not weaken the global seal.

Do not open Aug 04-23.

Do not score direction or PnL.

Any later hypothesis or correction requires a new Experiment ID.

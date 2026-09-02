# DEV030-P9 — PRICE Dense Sequence Research Review

## Status
Frozen research rationale for DEV030-P9. This file is a remote recovery of the locally frozen design lineage described in the authoritative 2026-09-02 handoff. The original local-only branch tip was `e57584ce0ef849c481baa39c24667d1f55807e77`; that Git object never reached GitHub, so this remote recovery preserves the scientific design but necessarily has different commit identities.

## Scientific question
Does one frozen dense causal PRICE sequence add stable direction-given-touch information beyond the successful DEV030-P3 PRICE summary baseline?

This is a representation test, not a model-family search.

## Why P9 follows P8
DEV030-P8 tested only four sparse landmarks (32s, 24s, 16s, 8s) for three PRICE primitives. It failed the frozen stability gates, but the pooled comparison moved in the favorable direction:
- C0 pooled AUC: 0.536469
- C1 pooled AUC: 0.548090
- AUC delta: +0.011621
- log-loss improvement: +0.001306
- Brier improvement: +0.000300

Only two of four folds improved, so P8 remains a frozen failure. The small pooled gain nevertheless motivates one bounded dense-sequence representation test before escalating model complexity.

## Architecture ordering
The project does not jump to LSTM, DeepLOB, Transformer/TLOB, InceptionTime, or a broad model bake-off.

Frozen ordering:
1. P9: dense causal PRICE sequence + existing regularized linear classifier.
2. If P9 fails: one bounded P10 MiniRocket-style deterministic multivariate transform + linear classifier, after dependency/license/version audit.
3. Only if sequence representation demonstrates stable value: consider one shallow causal CNN/TCN confirmation.
4. Transformer/TLOB only much later, if data depth, support size, and prior evidence justify it.

## Information families deliberately excluded
P9 does not reintroduce:
- L1 OFI summary bundles;
- opportunity/touch composition;
- calibration rescue;
- threshold/PnL optimization;
- alternate target geometries;
- alternate windows;
- alternate channel sets;
- alternate model families.

## Prior evidence preserved
- EXP024-P1 remains the opportunity-ranking success, not a direction or PnL result.
- DEV030-P3 remains the direction-given-touch baseline success.
- P4 touch head was strong, but composition failed.
- P5, P6, P7, and P8 remain frozen failures and are not rewritten.

## Data/storage boundary
P9 may use only the already-consumed Jan-Jul development material when a later canonical run is separately authorized.

The following storage assets remain prohibited during design/implementation/testing:
- market-raw-archive
- exp027-archive-volume
- abundant-love-volume
- multi-market-codex-lab-volume

No listing, opening, downloading, uploading, mutating, or deleting those assets is part of P9.

## Research conclusion
The next useful question is whether dense path representation from the same PRICE information can add stable directional ordering. P9 therefore changes representation only while holding target, support, folds, model family, regularization family, and evaluation discipline fixed.

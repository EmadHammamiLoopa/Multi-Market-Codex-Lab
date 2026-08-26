# CODEX-EXP-012-P0 Frozen Result

Status: `INVALID`

Frozen audit head:

`eda80b75e67c59a7a7cd4b1cd9ac9b2af08e192a`

Result artifact SHA-256:

`c30329af81c84a4dc1973c32fcf06a544fb91340aaadedf6ca810d29f18735fe`

## Why this run is invalid

The audit implementation parsed Deribit option symbols such as `BTC-27MAR26-...` by converting the expiry date to midnight UTC. Deribit options expire at 08:00 UTC, not 00:00 UTC. Consequently, valid expiry-day option trades occurring from 00:00 through 07:59:59 UTC were incorrectly classified as expired.

This is a construct/protocol implementation defect, not a readiness failure and not evidence against segmented options flow.

The defect was detected by the preregistered integrity gate `zero_expired_btc_vanilla_trades`, which was false on all five sandbox days. The correct frozen adjudication is therefore `INVALID`.

## Other observations (diagnostic only; cannot rescue EXP012)

All frozen raw hashes matched, no outside-day rows or parse conflicts were detected, the strictly-earlier Phase-L reference invariant passed, and all six proposed segments existed on every day.

Aggregate 1-minute constructability was above the 80% threshold on every day. The 120-minute consecutive-run readiness gate failed only on 2026-03-01 (112 minutes); because the expiry timestamp defect changes which trades are retained, this number must not be interpreted as a valid readiness result.

No target, model, AUC, direction, PnL, network access, or sealed August data were used.

## Scientific disposition

EXP012-P0 is frozen permanently as INVALID and must not be rerun.

A corrected implementation using the documented Deribit 08:00 UTC expiry timestamp requires a new Experiment ID. The next experiment should repeat only the P0 constructability/readiness question under corrected expiry semantics, with all other segmentation definitions and readiness gates preserved unchanged.

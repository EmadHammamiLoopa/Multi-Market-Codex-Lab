# CODEX-EXP-003 Timestamp and Causality Audit

Status: **PRE-SCORE AUDIT; COLLECTOR-VANTAGE CLAIM ONLY**

## Finding

The proposed data can support a conservative prospective-availability test at the Tardis collection vantage, subject to the frozen 500 ms embargo and explicit gap invalidation. It cannot prove that a Binance-co-located trader observed the same ordering, that independent collector hosts had a published hard clock-skew bound, or that a venue structurally caused a move.

Accordingly, `CODEX-EXP-003` uses “causal” in the narrow point-in-time sense: every external observation used at target decision time `t` had a Tardis `local_timestamp <= t - 500 ms`. A PASS would mean incremental out-of-sample predictive/economic information under that recorded arrival-time policy. It would not mean structural causation, exchange-engine leadership, or deployable latency from an unspecified trading location.

## Clock definitions

- `timestamp`: exchange-provided event timestamp. It may regress, be batched, reflect an exchange clock, or fall back to `local_timestamp`. It is audit-only.
- `local_timestamp`: Tardis message-arrival timestamp in microseconds. Tardis says downloadable files are split and ordered on this field.
- `t`: Binance-futures 250 ms target decision-grid timestamp inherited from the existing causal `FEATURES250` input.
- primary external cutoff: `c = t - 500,000 µs`.
- source age: `t - source_local_timestamp`.

Official schema and ordering definitions are in the Tardis [downloadable CSV documentation](https://docs.tardis.dev/downloadable-csv-files) and [data-type reference](https://docs.tardis.dev/downloadable-csv-data-types).

## Frozen eligibility algorithm

For each source independently:

1. preserve CSV file order;
2. reject a decrease in `local_timestamp`;
3. collapse equal-local-timestamp book rows as one atomic receipt group, retaining the final file-order full state;
4. compute `c = t - delay`;
5. select the final book row with `local_timestamp <= c` using a right-closed as-of search;
6. use trades only in `(c - window, c]`;
7. construct return anchors by a second local-time as-of search at `c - 250 ms`, `c - 1 s`, and `c - 3 s`;
8. require current and all anchors to be valid and in the same continuity segment;
9. require current source age between the configured delay and 2,000 ms inclusive; and
10. emit source local timestamp, source age, validity, and audit counters with every feature row.

Exchange timestamps cannot choose a row, break a tie, order a message, define a window, choose a return anchor, join a venue, or repair a regression. Changing every exchange timestamp while holding local timestamps fixed must leave every feature and validity flag unchanged; this is a mandatory synthetic test.

## Delay policy

| Delay | Role | Can determine PASS? |
|---:|---|---|
| 500 ms | primary | yes |
| 250 ms | optimistic diagnostic | no; cannot rescue any primary failure |
| 1,000 ms | extra-delay stress | reported; cannot rescue primary |
| −250 ms | explicit future-leak canary | never; isolated diagnostic namespace only |

The 500 ms buffer is a frozen conservative policy, not an empirical estimate of cross-host clock skew. The available public documentation identifies collection regions but does not publish a hard synchronization bound among collector processes. Therefore the study must preserve the collector-vantage limitation even if the result passes at 500 and 1,000 ms.

The 250 ms diagnostic may show how quickly any effect decays, but it cannot promote a failed 500 ms primary. The 1,000 ms run tests whether an apparent effect survives extra reaction time; its failure does not alter the already-frozen primary verdict but materially narrows interpretation.

## Gap, staleness, and outage policy

Tardis states that disconnect events are omitted from downloadable CSV datasets. Absence of an explicit disconnect is therefore not evidence of continuity.

Frozen controls:

- a gap over 2,000 ms between successive `book_snapshot_5` receipt timestamps starts a new segment;
- a malformed, incomplete, nonpositive, unordered, or crossed top-five row is invalid and starts a new segment;
- no current book older than 2,000 ms is eligible;
- a return or realized-volatility window cannot cross a segment boundary;
- after a gap, a new full snapshot may define the current state, but 250 ms/1 s/3 s features remain invalid until all required history has accumulated entirely in the new segment;
- no state crosses midnight; and
- zero trades inside a valid window is a valid zero imbalance, but it is usable only when the book/history validity checks pass.

This rule prevents indefinite forward fill. It cannot detect a sub-2-second disconnect that happens to be followed by a valid-looking reconstructed snapshot, so the residual risk remains an explicit limitation. If post-acquisition gap/outage diagnostics show a material or venue-asymmetric loss of common support, that is reported and can cause FAIL through selection/coverage; the threshold will not be loosened.

## Snapshot and trade atomicity

`book_snapshot_5` is a full wide row, not an incremental sequence. An equal-local-timestamp group is treated as atomically available at that receipt microsecond, and the final file-order full state is used. This avoids exposing an intermediate partial state. The code never sorts equal-time states on exchange time.

Trades with the same local timestamp are all included in the closed window endpoint. Duplicate nonempty trade IDs are removed while preserving first receipt order. Aggressor side must be exactly `buy` or `sell`; unknown-side trades cause input rejection rather than a post-hoc sign rule.

Raw amounts do not cross venues. Quantity features are within-source ratios `(buy amount - sell amount)/(buy amount + sell amount)`, so positive scaling of a source's amount unit cancels exactly. Count imbalance is also dimensionless. This avoids assuming Binance Spot base quantities and Bybit contract amounts have identical units.

## Feature endpoint audit

Every external window ends at `c`, not `t`:

```text
decision t
  external cutoff c = t - 500 ms
  book state: last local_timestamp <= c
  trade window: (c - h, c]
  source return: log(mid(c) / mid(c - h)) using local-time as-of states
```

Target-relative returns subtract the Binance-futures return over the same duration ending at target decision `t`. Target data through `t` are part of X0 and are causally available; the external leg remains embargoed through `c`. This tests whether older external movement adds information beyond the newer local futures book.

## Mandatory diagnostics and interpretation

1. **Timestamp permutation:** permute external feature rows within day with a frozen seed; material retained performance is evidence of non-temporal confounding.
2. **Extra delay:** repeat at 1,000 ms.
3. **Sign placebo:** fit/select on unmodified causal train/inner data, then reverse signed external returns/imbalances on XALL outer rows only while leaving spreads, volatility, and age unchanged. Flipping every split would be a logistic reparameterization and is explicitly not the test.
4. **Time placebo:** lag external features by 60 s without day wrap.
5. **Source dropout:** X1 and X2 are predeclared decompositions; neither can rescue XALL.
6. **Future-leak canary:** intentionally permit source receipt through `t + 250 ms` in an isolated mode. It must show detectably better discrimination or opportunity ranking than the causal primary; otherwise the audit cannot demonstrate sensitivity to the type of leakage it claims to detect. Canary output can never enter selection or PASS gates.

The canary is a positive control. Improvement is expected and demonstrates that the pipeline can detect future information; it is not evidence that the primary leaks. Conversely, a timestamp-permutation or time-placebo result that matches primary performance attacks the primary mechanism.

## Automatic invalidation conditions

The experiment cannot PASS if any of the following occurs:

- a primary row has source `local_timestamp > t - 500 ms`;
- a primary valid row has source age below 500 ms or above 2,000 ms;
- exchange timestamp changes alter eligibility or feature values;
- a local timestamp regression is repaired by sorting;
- any required 3 s feature crosses a gap, invalid row, or day boundary;
- X0 and XALL use different decision-row support;
- scaling uses calibration, selection, or outer rows;
- an August-named path is opened;
- the future canary enters a primary artifact or model; or
- the common-support sample is too sparse to select both X0 and XALL on all five folds.

## Audit conclusion

Proceeding to a frozen sandbox test is defensible only with the claim boundary above. A result must be described as “incremental information under Tardis local-arrival ordering with a 500 ms embargo.” It must not be described as proof that Bybit or Binance Spot structurally leads Binance futures, proof of a tradable co-location edge, or independent validation.

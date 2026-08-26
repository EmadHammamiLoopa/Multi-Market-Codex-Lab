# CODEX-EXP-010-P0 Frozen Result

Status: `FAIL_UNIFIED_OPTIONS_TRADE_FLOW_DATA_NOT_READY`

Frozen implementation head:

`9b9e710bf58f17fdcb15d932f1e9b01e27fcc6bd`

## Execution integrity

- raw_hashes_verified: true
- all_five_days_pass: false
- network_accessed: false
- sealed_august_opened: false
- target_scored: false
- future_return_inspected: false
- model_fit: false
- auc_scored: false
- direction_scored: false
- pnl_scored: false

Frozen audit SHA-256:

`4fa9b88dd5f9353c05ee00fcd3aa223433d9bbd2a8a100dd0fcdde976e7b709d`

## Adjudication

EXP010 reused the immutable EXP009 raw hashes and expanded the eligible Deribit option universe to include both standard inverse BTC/ETH options and official BTC_USDC/ETH_USDC linear options. This eliminated the prior parser/universe mismatch: eligible_parse_errors were zero on every frozen date, with no conflicting duplicate trade IDs and no outside-day rows.

BTC satisfied both frozen readiness gates on all five dates. Unified 1-minute support fractions were 0.906429, 0.939286, 0.883571, 0.899286, and 0.895714 for March through July, respectively; each date also passed the >=120-minute consecutive-support gate.

ETH failed both frozen gates on every date despite inclusion of USDC-linear option trades. Unified 1-minute support fractions were 0.755714, 0.763571, 0.687143, 0.678571, and 0.634286; longest consecutive complete runs were 58, 81, 62, 58, and 40 minutes.

Therefore the frozen BTC+ETH unified P0 fails. The result is now attributable to genuine ETH 1-minute trade-flow sparsity under the preregistered support definition, not to parser errors or exclusion of USDC-linear options.

No readiness threshold, window, or currency set may be changed under EXP010. A BTC-only predictive experiment requires a new Experiment ID and fresh preregistration before any target/model/AUC scoring.

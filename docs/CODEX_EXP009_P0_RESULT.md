# CODEX-EXP-009-P0 Frozen Result

Status: `FAIL_OPTIONS_TRADE_FLOW_DATA_NOT_READY`

Frozen implementation commit:

`d90480482f4c77f739e9377a775661c240699b2e`

## Execution integrity

- acquisition_ok: true
- acquisition_error: null
- raw_hashes_verified: true
- all_five_days_pass: false
- sealed_august_opened: false
- target_scored: false
- future_return_inspected: false
- model_fit: false
- auc_scored: false
- direction_scored: false
- pnl_scored: false

## Frozen artifact hashes

- `OPTIONS_TRADES_ACQUISITION_MANIFEST.json`: `852e92e7193ab2607e3b1abe60f72314eaacd54a643c5fb9a1d91ec24ade72c5`
- `OPTIONS_TRADE_FLOW_P0_AUDIT.json`: `b84f7d992c8297c72cd8473d2a7bdb41d6aac0803f5d8ea53a9d6246bccc34e4`

## Raw source artifacts

- 2026-03-01: 287689 bytes, SHA-256 `34835b3e3a022fac0e7270b3e1aca643b01e63b3bbffdab50c99c70dea9af6ba`
- 2026-04-01: 314091 bytes, SHA-256 `175b24f76bceb68b68c8b6caa04682cb4523bc2e5becc39c41fcf92456a1b605`
- 2026-05-01: 294084 bytes, SHA-256 `287aaf1a1c62b597c1d46f9f408eef9a0d7c1a73d47ef9edb809f9dc53adda78`
- 2026-06-01: 308792 bytes, SHA-256 `6076038bb1c07ed4e70a5ca696e04213a5e7e9ab9bfa835360764901925fc6a7`
- 2026-07-01: 291923 bytes, SHA-256 `02be481f94ac9b66dd43c9f185488b0c2af8f0517f7538d30c6dea565f866bc2`

## Structural support

### 2026-03-01

- BTC: 10,640 trades; 1m 1252/1400; 5m 1399/1400; 15m 1400/1400; 30m 1400/1400; all-window support 1252/1400 = 0.894286; longest run 139; 80% PASS; 120m PASS.
- ETH: 5,434 trades; 1m 1043/1400; 5m 1394/1400; 15m 1400/1400; 30m 1400/1400; all-window support 1043/1400 = 0.745; longest run 58; 80% FAIL; 120m FAIL.

### 2026-04-01

- BTC: 11,457 trades; 1m 1303/1400; 5m 1400/1400; 15m 1400/1400; 30m 1400/1400; all-window support 1303/1400 = 0.930714; longest run 279; 80% PASS; 120m PASS.
- ETH: 5,888 trades; 1m 1038/1400; 5m 1385/1400; 15m 1400/1400; 30m 1400/1400; all-window support 1038/1400 = 0.741429; longest run 81; 80% FAIL; 120m FAIL.

### 2026-05-01

- BTC: 12,234 trades; 1m 1227/1400; 5m 1394/1400; 15m 1400/1400; 30m 1400/1400; all-window support 1227/1400 = 0.876429; longest run 206; 80% PASS; 120m PASS.
- ETH: 4,184 trades; 1m 913/1400; 5m 1340/1400; 15m 1400/1400; 30m 1400/1400; all-window support 913/1400 = 0.652143; longest run 60; 80% FAIL; 120m FAIL.

### 2026-06-01

- BTC: 13,542 trades; 1m 1243/1400; 5m 1399/1400; 15m 1400/1400; 30m 1400/1400; all-window support 1243/1400 = 0.887857; longest run 344; 80% PASS; 120m PASS.
- ETH: 3,783 trades; 1m 927/1400; 5m 1357/1400; 15m 1400/1400; 30m 1400/1400; all-window support 927/1400 = 0.662143; longest run 57; 80% FAIL; 120m FAIL.

### 2026-07-01

- BTC: 11,773 trades; 1m 1227/1400; 5m 1400/1400; 15m 1400/1400; 30m 1400/1400; all-window support 1227/1400 = 0.876429; longest run 211; 80% PASS; 120m PASS.
- ETH: 3,082 trades; 1m 843/1400; 5m 1315/1400; 15m 1393/1400; 30m 1400/1400; all-window support 843/1400 = 0.602143; longest run 40; 80% FAIL; 120m FAIL.

## Adjudication

The frozen P0 fails because all ten currency-days were required to satisfy both readiness gates, and ETH fails both the 80% all-window support gate and the 120-minute consecutive-support gate on every frozen date.

BTC passes both frozen gates on all five dates. This is a descriptive result only and does not authorize scoring BTC under EXP009-P1 because the preregistered P0 required both BTC and ETH.

No threshold, window, currency set, or support gate may be changed under CODEX-EXP-009-P0. Any BTC-only or longer-window hypothesis requires a new Experiment ID and a fresh preregistration before predictive scoring.

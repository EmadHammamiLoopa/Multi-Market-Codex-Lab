# DEV045 D6R8EF — Semantic Real-Parity Runner Pre-Authorization Contract

Status: **IMPLEMENTED, REAL EXECUTION CLOSED**

Parent implementation lineage begins from D6R8EE exact GREEN head `3b6a62430df960dfe0f7e9e25eeefe6742a25aab`.

D6R8EF is the separately named successor attempt defined by D6R8ED. It is not D6R8EB and does not rerun or reinterpret the frozen D6R8EB FAIL.

The runner uses a new runtime root, attempt marker and evidence path under `dev045_d6r8ef`.

Before any converter execution the future authorized run must verify:

- exact D4 raw file byte sizes and SHA256 values;
- exact fixed Jan 1 BTCUSDT 10-minute local-timestamp window;
- exact decompressed semantic payload rows/bytes/SHA256/endpoints;
- exact depth snapshot structure.

Only after those gates pass may the runner execute three fresh subprocesses, in the frozen order:

1. upstream hftbacktest 2.4.4 oracle;
2. old bounded converter with frozen production chunk rows;
3. structurally bounded V2 converter with frozen production settings.

All three consume the same two reconstructed physical slice files. Final PASS requires exact fieldwise NaN-equal three-way parity with 64-byte event dtype. V2 peak RSS must remain within the frozen 6 GiB abort envelope.

At this commit stage `EXECUTION_AUTHORIZED=False`. CI must pass before any authorization commit is created. The authorization commit must be narrow, must bind the exact pre-authorization runner SHA, and must not change semantic, converter, parity, resource, window, or data-lineage rules.

The future canonical attempt remains exactly one. The permanent marker is written before real raw content is opened. The first PASS or FAIL freezes permanently. No rerun is permitted.

Jan full-day, Feb-Jul, August, September+, non-BTC, policy replay, historical PnL, Railway and live trading remain closed.

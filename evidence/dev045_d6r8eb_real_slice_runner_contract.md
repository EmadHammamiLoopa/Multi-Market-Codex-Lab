# DEV045 D6R8EB — One-Shot V2 Real 10-Minute Parity Runner

Status: **RUNNER FROZEN / EXECUTION NOT YET AUTHORIZED**

Parent: `bf7db4fbcaa633fea4b550592973f02a89d7819a` (D6R8EA contract, CI green).

This commit adds only the deterministic local runner and CI tests. CI uses synthetic temporary files only. No real market data is opened by this commit or its tests.

The runner is fail-closed. It creates a permanent local attempt marker before opening raw data. If that marker or the canonical evidence file already exists, the run refuses to start. Therefore a process interruption cannot silently become a second canonical attempt.

The runner may read only the two Jan 1 raw files frozen by D6R8EA and selects only `1767225600000000 <= local_timestamp < 1767226200000000`. It writes deterministic gzip slices with `mtime=0` while preserving the original header and selected row bytes. **V2 is not launched unless both extracted slice row counts and compressed SHA256 values exactly equal the frozen D6R2B identities.** If the reconstructed gzip representation differs for any reason, the first canonical result freezes FAIL before V2 execution; no alternate writer or rescue tuning is permitted.

When slice identity passes, the runner launches only `dev045_d6r8_structurally_bounded_converter` in a fresh Python subprocess with production tuning. The old converter and upstream hftbacktest oracle are never rerun. PASS requires base rows 496,224, final rows 503,934, 64-byte output dtype, exact output SHA256 `60ebc2aec273976c12526f7c49159d005368388a0f9d5993af269cc9753ffaf7`, recorded peak RSS within the frozen 6 GiB abort contract, empty converter scratch, and a normal return code.

The first PASS or FAIL is written to `evidence/dev045_d6r8eb_v2_real_10min_parity.json` and may not be rerun. Jan full-day, Feb–Jul, August, September+, non-BTC, policy replay, PnL, Railway and live trading all remain closed.

After this runner commit itself is CI GREEN, the exact commit may be checked out locally and the user may execute the one canonical D6R8EB command. No local execution is authorized before that CI gate.

# DEV045 D6R8EF — One-Shot Execution Authorization

Status: **AUTHORIZED IN CODE; LOCAL EXECUTION STILL REQUIRES EXACT CI GREEN + EXPLICIT SHELL PREFLIGHT**

Pre-authorization head: `0a204b479fd7c66b54824914be408f233a53e18e`.

The pre-authorization workflow run `33979117205` completed successfully before this authorization commit was created.

This authorization changes no slice, converter, parity, memory, source-lineage, or downstream economic semantics. It only changes the runner's static authorization boolean from false to true, records the exact pre-authorization head, and keeps the explicit environment token `DEV045_D6R8EF_AUTHORIZE=YES_ONE_SHOT` mandatory.

Before the local canonical attempt, the shell preflight must independently require the exact SHA of this authorization commit, a clean tracked worktree, exact remote branch identity, absence of the new D6R8EF attempt marker and evidence, the pinned hftbacktest 2.4.4 environment, and the frozen minimum MemAvailable gate. The environment token must be exported only at the canonical attempt boundary.

The first local D6R8EF result freezes PASS or FAIL. Rerun after the marker is created is forbidden.

D6R8EB remains permanently frozen FAIL. Jan full-day, Feb-Jul, August, September+, non-BTC, policy replay, historical PnL, Railway and live trading remain closed.

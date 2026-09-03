# DEV045-M4 Final Replay-Adapter Freeze

Status:

`DEV045_M4_GREEN_FROZEN`

Date: 2026-09-03

Final implementation identity:

`6d8113b2128206cc192e60e167d47ec0add1cdd7`

Dedicated CI:

- workflow: `dev045-m4-replay-adapter`
- run #1
- run id: `33804129136`
- conclusion: `SUCCESS`

General regression:

- workflow: `test`
- run #1249
- run id: `33804129047`
- conclusion: `SUCCESS`

M4 proved on the safety-patched simulator:

- passive-only maker submission;
- RiskAdverse no-fill then fill behavior;
- fill ledger == engine position;
- maker fee conservation;
- 100/250/500ms latency lifecycle parity;
- cancel response before replacement submission;
- forced taker flatten after inventory timeout;
- final position == zero;
- combined maker+taker fee conservation.

No historical strategy PnL was opened.

Next:

`DEV045-M5 MAKER ECONOMIC ARENA PREREGISTRATION + FEE FREEZE`

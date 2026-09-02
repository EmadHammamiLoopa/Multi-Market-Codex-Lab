# DEV031-P1B — Incremental Direction Value of Frozen Event/Depth Features

Status: `PREREGISTERED_BEFORE_IMPLEMENTATION_OR FITTING`

Parent:
- DEV031-P1A = `EVENT_DEPTH_EXACT_P3_SUPPORT_MATERIALIZED`
- canonical P1A artifact SHA256 =
  `a8a4f89262b9f01e76fc10a1b9c54ac28dd7faec3180a1a0fac19499eb9467d8`

Scientific question:

> On the exact frozen DEV030-P3 T1 direction-given-touch support, do the
> preregistered 26 raw event-time/deep-depth features add stable out-of-sample
> directional probability information beyond the frozen 23-feature PRICE S1
> representation?

P1B tests incremental information content only.

It does not test:
- profitability;
- action thresholds;
- opportunity ranking;
- touch prediction;
- joint composition;
- model-family escalation;
- forward confirmation.

Successful prior experiments remain active:
- EXP024-P1 opportunity ranking success remains preserved for a later policy
  stage, but is not used as a P1B filter/feature/threshold;
- DEV030-P3 remains the frozen direction anchor;
- DEV030-P4 touch-vs-none success remains preserved for later composition.

Failure constraints remain active:
- P7 showed aggregated L1 OFI did not add stable incremental value;
- P8/P9/P10 closed the Jan-Jul PRICE-only sequence representation family;
- P1B may not trigger feature subset search or alternate architecture rescue.

P1B consumes only the frozen P1A materialized day artifacts.
It does not reopen raw L2.

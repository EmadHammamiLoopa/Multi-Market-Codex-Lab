# DEV045 D6R26A P2 R11 — Synthetic real-engine candidate-lane lifecycle

Parent R10 HEAD: `84eabe7dcc7e57da3be18b3cc21404f2d3899a53`.

R11 binds the frozen Gen-2 candidate semantics to the exact patched `hftbacktest 2.4.4` engine on synthetic data only.

It proves:

- decision at local strategy time after 30s feature warmup;
- frozen R9 raw-event semantics and R10 bounded feature computation produce the 25 causal features;
- GTX LIMIT candidate submission under 250ms entry + 250ms response latency;
- exact post-only accepted placement semantics;
- RiskAdverse queue depletion followed by a maker fill;
- PartialFillExchange `exec_qty` is treated as the quantity of the individual fill response;
- fill exchange time comes from `order.exch_timestamp`;
- fill local response time is the simulator `current_timestamp` when the response is received, not `order.local_timestamp` (which is request time);
- P1 fill labels and markout labels are produced without redefining target semantics;
- a still-working order is canceled early enough that the cancel response arrives exactly at the frozen `t+5s` terminal boundary before the next same-lane candidate;
- no-fill cancellation is not collapsed into fill or censoring when the full horizon is observable.

Frozen synthetic timing:

- decision: `31.000s` local;
- order exchange arrival: `31.250s`;
- new-order response: `31.500s` local;
- maker fill probe exchange execution: `31.800s`;
- fill response receipt: `32.050s` local;
- cancel request for an unfilled order: `35.500s` local;
- cancel exchange receipt: `35.750s`;
- cancel response / candidate terminal boundary: `36.000s` local.

R11 does not open Jan-Jul, does not write the canonical attempt marker, does not write canonical labels, does not fit models, and does not compute PnL.

Next after R11 GREEN: bounded one-day real lane-materialization driver preexecution and final one-shot execution binding. Historical candidate simulation remains sealed until those surfaces are frozen and separately authorized.

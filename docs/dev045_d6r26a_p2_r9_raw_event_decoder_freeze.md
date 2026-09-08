# DEV045 D6R26A P2 R9 — Raw-event decoder freeze

Parent R8B HEAD: `24030d3b677449fa48042881ffb189233a7121ce`.

R9 freezes the conversion from canonical hftbacktest event arrays into the local causal book/flow history consumed by R8B and the exchange-time midpoint history consumed by the frozen P1 markout labels.

The decoder is bound to exact upstream hftbacktest commit `a244a14250b42d97fc305569c93c4117cd5e1dff` and freezes these identities: `DEPTH_EVENT=1`, `TRADE_EVENT=2`, `DEPTH_CLEAR_EVENT=3`, `DEPTH_SNAPSHOT_EVENT=4`, `DEPTH_BBO_EVENT=5`, `ADD_ORDER_EVENT=10`, `CANCEL_ORDER_EVENT=11`, `MODIFY_ORDER_EVENT=12`, `FILL_EVENT=13`, plus exact EXCH/LOCAL/BUY/SELL flag bits.

Decoder definition SHA256:

`50ddc5f01872cb6155d7ea3f8adc8e040a95407249657e2c891859d4921fdd58`

## Frozen L2 parity rules

- Only rows carrying `LOCAL_EVENT` feed local feature history.
- Only rows carrying `EXCH_EVENT` feed exchange-time midpoint history.
- `DEPTH_EVENT` is an absolute level-quantity update. Local depth deltas emit ADD/CANCEL flow.
- `DEPTH_SNAPSHOT_EVENT` updates book state but emits no ADD/CANCEL flow.
- `DEPTH_CLEAR_EVENT` follows exact HashMapMarketDepth bounded-clear semantics and emits no ADD/CANCEL flow.
- `TRADE_EVENT` emits aggressor BUY/SELL flow and does not mutate L2 depth.
- `DEPTH_BBO_EVENT`, L3 add/cancel/modify/fill event types are ignored to mirror the frozen L2 Local processor.
- Unknown low-byte event types fail closed.
- Same-local-timestamp market rows are processed in source order and coalesced to one final post-market BookObservation.
- Exchange depth rows are processed in source order and coalesced to one midpoint per exchange timestamp after the final depth mutation.

## Scope

R9 is synthetic-contract only. It does not open Jan-Jul, import the simulator, start a candidate lane, write the attempt marker, write labels, fit models, compute PnL, or open August/September+/non-BTC data.

Next after R9 GREEN: R10 real candidate lane executor preexecution, binding R9 decoder + R8B feature/label semantics + R8A engine/writer hooks under synthetic engine probes only.

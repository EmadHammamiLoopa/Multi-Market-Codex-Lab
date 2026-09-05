# DEV045 D6R8EE — Semantic Parity Runner

Status: **IMPLEMENTED, REAL EXECUTION CLOSED**

Parent: `76d6e6e38eb2ec7ed6f9955f1e30eb575d568c66` (D6R8ED semantic real-parity contract).

D6R8EE implements the reusable three-way parity core required by D6R8ED while keeping every real-data execution surface closed.

The runner accepts one pair of physical slice files and sends that same pair to:

1. hftbacktest 2.4.4 upstream `tardis.convert`;
2. the frozen old bounded converter at production chunk size 500,000;
3. the frozen V2 structurally bounded converter at its production tuning.

The outputs are compared fieldwise exactly with NaN equality. Shape and dtype must match and the final event itemsize must be 64 bytes. Any pairwise mismatch fails closed.

The module also exposes semantic gzip-payload inspection using decompressed SHA256, byte length, row count, and first/last local timestamp. This is the identity primitive D6R8EF will use before any converter launch.

CI tests use only temporary synthetic gzip CSV fixtures. They exercise the actual installed upstream oracle, old converter, and V2 converter and require exact three-way parity. They also verify semantic-identity failure, NaN-equal comparison behavior, and that real successor execution remains hard closed.

There is deliberately no binding to `/home/emadh/Multi-Market/data`, no attempt marker, and no D6R8EB runtime reuse in this module. D6R8EF must separately add the exact D4 raw preflight, semantic-slice reconstruction, one-shot marker/evidence, fresh-subprocess resource measurement, and explicit local authorization.

No Jan full day, Feb-Jul, August, September+, non-BTC, policy replay, PnL, Railway, network acquisition, or live trading is authorized by D6R8EE.

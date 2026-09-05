# DEV045 D6R9B — Canonical Mar–Jul V2 Result

Status: **FROZEN PASS / NEVER RERUN ANY CONSUMED DAY**

Execution head: `7635f57c0bf4e7c92379bcb1846d5fa105160103`.

The one-shot bulk sequence ran BTCUSDT only, in the frozen order `2026-03-01` → `2026-07-01`, using V2 only. No old converter, upstream converter, policy replay, historical PnL, Railway, live trading, August, September+, or non-BTC surface was opened.

All five canonical days passed:

| Day | Final rows | Output bytes | Peak RSS bytes | Output SHA256 |
|---|---:|---:|---:|---|
| 2026-03-01 | 150,979,263 | 9,662,673,088 | 474,935,296 | `9e6a8b61d05e1a4938e17ffa7969241affc7c06c1d0836188e3a882c363f2d99` |
| 2026-04-01 | 132,829,759 | 8,501,104,832 | 476,233,728 | `de7e0471e63631394981b301bb461d679192c37eb6241d4d8073cf0640eca7f7` |
| 2026-05-01 | 108,328,169 | 6,933,003,072 | 469,696,512 | `9433dfb498070dd5dd3e8ab1633c2f19551844f2ddf0d451e120119365bb04a3` |
| 2026-06-01 | 172,540,697 | 11,042,604,864 | 468,209,664 | `ac97ad27c9d58b3b3e249547b8ae7c74cf2ebfde07965103bd9c8c05d0df1160` |
| 2026-07-01 | 181,084,390 | 11,589,401,216 | 476,086,272 | `85f9a0a168420ce924fc9e1b746fbd9bb54bec390205c9ed9e65469ad489a83f` |

Canonical marker/evidence identities:

- Mar marker `75e81966180ed91b77e1858c51491aa8e0d1254fcb34c86ee88fbb3e7a05bbd4`; evidence `dc077571207df728666b147c4c865a51ac40e189b626b0f398585aaaff2ce221`.
- Apr marker `0449eb68c2bcedf7f5f200495f628f0998907aa868ca844ec1fc6168572dacd7`; evidence `a00918595087e55ae1dcb7d833ee11cdedbed26c6ff9ca06d5caccc36a6eacae`.
- May marker `1a052938d5cdc05b07787478a5849a3df24c0e62b7e02583d145b001b09f94b3`; evidence `abdb6a95dd9027a65386b9e4a1218fdcf3be57d94a80945a6c94919ac12a6bd5`.
- Jun marker `92312274f118866d3fde4b48d717f1a13ff3ff4d52773c87d48d54b66f174a5c`; evidence `13821ab6ba2f77820ab43ed9082a249c972a95eb11f282340cd5f6c7b853c26b`.
- Jul marker `8f50ec61a1f5db9d2ee28607bc22de898f48ee07dde7d3ae4b3adfdfe7d7f7da`; evidence `02c59ac113b71c511768724e218249d506ef38962aa3ae28770613f8dc10561c`.

Together with frozen D6R9A Feb 1, the project now has six immutable full-day V2 BTCUSDT artifacts for Feb–Jul. The next open question is feed-only hftbacktest ingestion of these new V2 artifacts under a memory guard. Historical PnL remains closed until ingestion is proven and the numeric personal risk/drawdown envelope is frozen.
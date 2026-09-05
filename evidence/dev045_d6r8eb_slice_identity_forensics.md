# DEV045 D6R8EB Slice Identity Forensics

## Frozen canonical result

D6R8EB remains permanently `FAIL` at execution commit
`014e7580b476ec8031a0e36980567884c396f819`. This investigation did not
rerun its runner, either converter, or the upstream oracle. It did not modify
the canonical evidence, the attempt marker, or either canonical slice.

## Finding

`ROOT_CAUSE=FROZEN_D6R2_SLICE_HASH_SEMANTICS_UNRECOVERABLE`

Confidence is high in that classification. D6R2B retained only SHA-256 values
of the compressed gzip files. It did not retain the slice files, a
decompressed-payload digest, a decompressed byte length, or the execution
writer. The D6R2A contract froze `mtime=0`, but did not freeze compression
level, gzip filename/header fields, OS byte, Python/zlib versions, or exact
writer behavior.

Repository-wide reachable-history and reflog searches found no D6R2 runner.
Unreachable Git objects were also searched without finding the runner or
slice bytes. No old runtime slice copy was found. Recompression of the current
payloads with Python gzip levels 0 through 9, plausible filename-header
variants, and GNU gzip levels 1 through 9 reproduced neither D6R2B digest.

## Current frozen-attempt slices

The already-created D6R8EB slices were inspected read-only:

| Kind | Compressed SHA-256 | Decompressed SHA-256 | Bytes | Rows |
| --- | --- | --- | ---: | ---: |
| trades | `c114bb26cece434d75e534cb02e606fa32c29d03bbd4bdf4c08e3020e0375c07` | `cb6a1d37e4422fa99e563969b3750487a3ca3d01956a45973085f26352a220fe` | 1,137,750 | 13,073 |
| depth | `4c6292d85e0b6867c9b938856a9f02120dfb82d9f608ada19eef39862025c5fd` | `5c5d8de09c1a38083f151f632fce568fb80b9df1485f5688d2dab20431869f93` | 39,147,846 | 483,149 |

Both have only LF line endings. Both are valid single-header gzip streams with
header `1f8b08000000000002ff`: method 8, flags 0, mtime 0, XFL 2, OS 255,
and no embedded filename. Their trailer CRC32 and ISIZE values match the
streamed decompressed payloads. Exact CSV header, first row, last row, gzip
header, and trailer values are recorded in the companion JSON evidence.

## What is and is not proven

The current D6R8EB payloads are fully characterized and internally valid.
Their row counts and first/last local timestamps agree with D6R2B. The source
file metadata also remains consistent with the frozen D4 manifest.

Exact logical payload identity with D6R2B is **not** cryptographically proven,
because neither a D6R2B decompressed digest nor D6R2B slice bytes survive.
Consequently a gzip-representation-only mismatch is also **not** proven.
Nothing found proves a logical-payload mismatch either.

## Successor decision

A new real execution successor is not yet justified. Calling this a gzip-only
mismatch would silently reinterpret the frozen D6R8EB gate without the missing
comparison artifact.

The next safe step is a contract-only identity-recovery decision. It must
either recover an independently archived D6R2B slice/writer, or explicitly
amend the lineage standard to derive logical identity from the frozen D4 raw
input identity, fixed selection bounds, exact raw-row preservation, row counts,
endpoint timestamps, and newly frozen decompressed-payload digests. That review
must happen before authorizing any new real-data attempt. It must never reopen
or rescue D6R8EB.

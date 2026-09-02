# DEV031-P0A Throughput-Only Execution Amendment

Status: `IMPLEMENTATION_AMENDMENT_BEFORE_CANONICAL_ARTIFACT`

The first canonical execution attempt of DEV031-P0A was observed running
single-process at approximately one CPU core. After roughly 12 minutes it was
still reading the February raw L2 file. At that observation time:

- PID = 1183001
- CPU = ~99.9% of one logical CPU
- machine logical CPUs = 24
- canonical P0A output directory = absent
- canonical artifact = absent

No P0A structural result or gate outcome had been produced or inspected.

To avoid an unnecessarily long implementation path, execution is amended to
parallelize the seven independent frozen days across seven worker processes.

Scientific semantics are unchanged:
- exact same seven input files;
- exact same `audit_day()` implementation per file;
- exact same row parsing;
- exact same L2 reconstruction;
- exact same gates;
- exact same output schema except execution provenance identifying seven
  process-per-day workers;
- no labels/model/predictive metrics/PnL/forward data.

The day worker is tested for exact dataclass equality against direct
`audit_day()` execution on a frozen synthetic fixture.

This is an implementation-throughput amendment, not a scientific-design change.
It is permitted because no canonical artifact existed and no P0A gate outcome
had been observed.

The active single-process attempt must be terminated and verified to have
created no artifact before the parallel candidate may be frozen and run.

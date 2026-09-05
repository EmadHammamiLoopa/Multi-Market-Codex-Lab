from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np

from multimarket import dev045_d6r8e_real_slice_parity_contract as c

RUNTIME_ROOT = Path('/home/emadh/Multi-Market/runtime/dev045_d6r8eb')
ATTEMPT_MARKER = RUNTIME_ROOT / 'ATTEMPT_STARTED.json'
SLICE_DIR = RUNTIME_ROOT / 'slice'
SCRATCH_DIR = RUNTIME_ROOT / 'scratch'
OUTPUT_DIR = RUNTIME_ROOT / 'output'
TRADE_SLICE = SLICE_DIR / 'trades_BTCUSDT_2026-01-01_0000_0010.csv.gz'
DEPTH_SLICE = SLICE_DIR / 'depth_BTCUSDT_2026-01-01_0000_0010.csv.gz'
OUTPUT_NPY = OUTPUT_DIR / 'BTCUSDT_2026-01-01_0000_0010.npy'
DEFAULT_EVIDENCE = Path('evidence/dev045_d6r8eb_v2_real_10min_parity.json')


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _memavailable_bytes() -> int:
    for line in Path('/proc/meminfo').read_text(encoding='ascii').splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1]) * 1024
    raise RuntimeError('memavailable_unavailable')


def _write_deterministic_gzip(path: Path, lines: list[bytes]) -> None:
    with path.open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, compresslevel=9, mtime=0) as gz:
            for line in lines:
                gz.write(line)


def _extract_slice(src: Path, dst: Path) -> dict[str, int | str | None]:
    if not src.is_file():
        raise RuntimeError(f'missing_raw:{src}')
    selected: list[bytes] = []
    scanned = 0
    rows_before = 0
    first_ts = None
    last_ts = None
    with gzip.open(src, 'rb') as fh:
        header = fh.readline()
        if not header:
            raise RuntimeError(f'empty_raw:{src}')
        decoded_header = next(csv.reader([header.decode('utf-8').rstrip('\r\n')]))
        try:
            local_idx = decoded_header.index(c.SELECTION_FIELD)
        except ValueError as exc:
            raise RuntimeError(f'missing_selection_field:{src}') from exc
        selected.append(header)
        for raw_line in fh:
            scanned += 1
            row = next(csv.reader([raw_line.decode('utf-8').rstrip('\r\n')]))
            ts = int(row[local_idx])
            if ts < c.WINDOW_START_LOCAL_TIMESTAMP_US:
                rows_before += 1
                continue
            if ts >= c.WINDOW_END_LOCAL_TIMESTAMP_US:
                break
            if first_ts is None:
                first_ts = ts
            last_ts = ts
            selected.append(raw_line)
    _write_deterministic_gzip(dst, selected)
    return {
        'selected_rows': len(selected) - 1,
        'scanned_rows_until_stop': scanned,
        'rows_before_window': rows_before,
        'first_selected_local_timestamp_us': first_ts,
        'last_selected_local_timestamp_us': last_ts,
        'sha256': _sha256(dst),
    }


def _child_convert() -> int:
    from multimarket import dev045_d6r8_structurally_bounded_converter as v2
    started = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result = v2.convert_tardis(
        TRADE_SLICE,
        DEPTH_SLICE,
        OUTPUT_NPY,
        scratch_dir=SCRATCH_DIR,
    )
    peak_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    payload = {
        'base_event_rows': result.base_event_rows,
        'final_event_rows': result.final_event_rows,
        'initial_sort_runs': result.initial_sort_runs,
        'exchange_merge_levels': result.exchange_merge_levels,
        'local_merge_levels': result.local_merge_levels,
        'output_sha256': result.output_sha256,
        'chunk_rows': result.chunk_rows,
        'peak_rss_kib': int(peak_kib),
        'peak_rss_bytes': int(peak_kib) * 1024,
        'starting_ru_maxrss_kib': int(started),
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


def _ensure_fresh_runtime() -> None:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    if ATTEMPT_MARKER.exists():
        raise RuntimeError('canonical_attempt_already_started')
    for path in (SLICE_DIR, SCRATCH_DIR, OUTPUT_DIR):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    if OUTPUT_NPY.exists():
        raise RuntimeError('output_exists')


def run(evidence_path: Path) -> int:
    if evidence_path.exists():
        raise RuntimeError('evidence_already_exists')
    _ensure_fresh_runtime()
    attempt = {
        'experiment_id': 'DEV045-D6R8EB',
        'canonical_attempt': 1,
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'parent_head': c.PARENT_HEAD,
    }
    ATTEMPT_MARKER.write_text(json.dumps(attempt, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    evidence = {
        **attempt,
        'schema_version': 'dev045-d6r8eb-v2-real-10min-parity-v1',
        'status': 'FAIL',
        'failure_stage': None,
        'failure_reason': None,
        'real_data_opened': False,
        'v2_executed': False,
        'old_converter_rerun': False,
        'upstream_oracle_rerun': False,
        'jan_full_day_opened': False,
        'feb_jul_opened': False,
        'aug_opened': False,
        'sep_plus_opened': False,
        'non_btc_opened': False,
        'policy_replay_run': False,
        'historical_pnl_computed': False,
        'railway_touched': False,
        'live_trading_authorized': False,
    }
    try:
        mem = _memavailable_bytes()
        evidence['mem_available_bytes'] = mem
        if mem < c.MIN_MEMAVAILABLE_BYTES:
            raise RuntimeError(f'memavailable:{mem}:{c.MIN_MEMAVAILABLE_BYTES}')

        evidence['real_data_opened'] = True
        evidence['slice'] = {
            'trades': _extract_slice(Path(c.TRADE_ABSOLUTE_PATH), TRADE_SLICE),
            'depth': _extract_slice(Path(c.DEPTH_ABSOLUTE_PATH), DEPTH_SLICE),
        }
        tr = evidence['slice']['trades']
        dp = evidence['slice']['depth']
        if tr['selected_rows'] != c.TRADE_SELECTED_ROWS or tr['sha256'] != c.TRADE_SLICE_SHA256:
            raise RuntimeError('trade_slice_identity')
        if dp['selected_rows'] != c.DEPTH_SELECTED_ROWS or dp['sha256'] != c.DEPTH_SLICE_SHA256:
            raise RuntimeError('depth_slice_identity')

        cmd = [sys.executable, '-m', 'multimarket.dev045_d6r8eb_real_slice_runner', '--child-convert']
        evidence['v2_executed'] = True
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
        evidence['v2_return_code'] = proc.returncode
        evidence['v2_stdout_sha256'] = hashlib.sha256(proc.stdout.encode()).hexdigest()
        evidence['v2_stderr_sha256'] = hashlib.sha256(proc.stderr.encode()).hexdigest()
        if proc.returncode != 0:
            raise RuntimeError(f'v2_return_code:{proc.returncode}')
        child = json.loads(proc.stdout.strip())
        evidence['v2'] = child
        if child['base_event_rows'] != c.FROZEN_OLD_BASE_EVENT_ROWS:
            raise RuntimeError('base_event_rows')
        if child['final_event_rows'] != c.FROZEN_OLD_FINAL_EVENT_ROWS:
            raise RuntimeError('final_event_rows')
        if child['output_sha256'] != c.FROZEN_OLD_OUTPUT_SHA256:
            raise RuntimeError('output_sha256')
        if child['peak_rss_bytes'] > c.V2_RUNTIME_RSS_ABORT_BYTES:
            raise RuntimeError('peak_rss_over_contract')
        arr = np.load(OUTPUT_NPY, mmap_mode='r', allow_pickle=False)
        try:
            if arr.dtype.itemsize != c.FROZEN_OLD_OUTPUT_ITEMSIZE or len(arr) != c.FROZEN_OLD_FINAL_EVENT_ROWS:
                raise RuntimeError('output_shape_dtype')
        finally:
            if getattr(arr, '_mmap', None) is not None:
                arr._mmap.close()
        if any(SCRATCH_DIR.iterdir()):
            raise RuntimeError('scratch_not_empty')
        evidence['status'] = 'PASS'
    except Exception as exc:
        evidence['failure_stage'] = 'canonical_attempt'
        evidence['failure_reason'] = f'{type(exc).__name__}:{exc}'
    finally:
        evidence['completed_at_utc'] = datetime.now(timezone.utc).isoformat()
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0 if evidence['status'] == 'PASS' else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--child-convert', action='store_true')
    parser.add_argument('--evidence', type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    if args.child_convert:
        return _child_convert()
    return run(args.evidence)


if __name__ == '__main__':
    raise SystemExit(main())

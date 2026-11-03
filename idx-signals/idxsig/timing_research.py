"""Offline latency attribution. No detector, trade permission, or performance claim.

Input is the full retained attempt queue, not a winner-selected event sample.
Outcome fields are deliberately ignored: future labels cannot change attribution.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from .runtime.data import parse_time
from .runtime.storage import read_json

STAGES = ('published_at', 'received_at', 'detected_at', 'decision_at', 'executable_at', 'fill_at')
PAIRS = tuple(zip(STAGES, STAGES[1:]))


def diagnose(records, *, as_of):
    cutoff = parse_time(as_of)
    if not isinstance(records, list):
        raise ValueError('records must be a list containing all attempts')
    seen = set()
    details = []
    samples = {f'{a}_to_{b}': [] for a, b in PAIRS}
    missing = {k: 0 for k in STAGES}
    for row in records:
        identifier = row.get('id')
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError('attempt ids must be unique and nonempty')
        seen.add(identifier)
        for key in ('detector_version', 'universe_snapshot_id', 'evidence_id'):
            if not isinstance(row.get(key), str) or not row[key]:
                raise ValueError(f'{key} required for each attempt')
        if row.get('evidence_kind') not in ('synthetic', 'recorded', 'prospective'):
            raise ValueError('explicit evidence_kind required')
        times = {}
        for key in STAGES:
            value = row.get(key)
            if value is None:
                missing[key] += 1
                continue
            times[key] = parse_time(value, key)
            if times[key] > cutoff:
                raise ValueError(f'{key} is after cutoff')
        # Publication is optional for independent tape discovery. A supplied
        # publication timestamp refers to this trigger's source, not later news.
        known = [times[k] for k in STAGES if k in times]
        if known != sorted(known):
            raise ValueError('reversed attempt chronology')
        delays = {}
        for a, b in PAIRS:
            key = f'{a}_to_{b}'
            value = (times[b] - times[a]).total_seconds() if a in times and b in times else None
            delays[key] = value
            if value is not None:
                samples[key].append(value)
        details.append({'id': identifier, 'detector_version': row['detector_version'],
                        'evidence_kind': row['evidence_kind'], 'seconds': delays,
                        'missing_stages': [k for k in STAGES if k not in times]})
    # Keep profiles and detector cohorts separate, including the headline lag.
    cohorts = []
    for kind, detector in sorted({(r['evidence_kind'], r['detector_version']) for r in details}):
        subset = [r for r in details if (r['evidence_kind'], r['detector_version']) == (kind, detector)]
        stats = {}
        for key in samples:
            values = [r['seconds'][key] for r in subset if r['seconds'][key] is not None]
            stats[key] = {'known': len(values), 'unknown': len(subset)-len(values),
                          'median_seconds': statistics.median(values) if values else None,
                          'max_seconds': max(values) if values else None}
        cohorts.append({'evidence_kind': kind, 'detector_version': detector,
                        'attempts': len(subset), 'stages': stats})
    return {'schema_version': 'KOD_TIMING_ATTRIBUTION_V1', 'as_of': as_of,
            'status': 'DESCRIPTIVE_ONLY', 'entry_permission': False,
            'attempts': len(records), 'missing_stages': missing, 'cohorts': cohorts,
            'records': details,
            'limitations': ['Input completeness is caller supplied; this tool cannot establish scan coverage.',
                            'Missing stages remain unknown; no quote/fill or arrival time is invented.',
                            'Local timestamps require independent evidence before calling a run prospective.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='JSON {as_of, records}; full retained attempt queue')
    args = parser.parse_args(argv)
    payload = read_json(args.input)
    print(json.dumps(diagnose(payload['records'], as_of=payload['as_of']), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()

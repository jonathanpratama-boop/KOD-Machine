#!/usr/bin/env python3
"""Pre-result Upbit notice inventory and pure paired-return statistics.

The events command reads archived notice JSON only. It never requests prices.
The statistics function consumes explicitly supplied outcomes; it has no I/O.
"""
import argparse
from collections import defaultdict
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import random
import re

UTC = dt.timezone.utc
KST = dt.timezone(dt.timedelta(hours=9))
FAMILY_TEXT = '마켓 디지털 자산 추가'
MARKET_LABELS = frozenset({'KRW', 'BTC', 'USDT'})


def _stamp(value):
    return value.astimezone(UTC).isoformat().replace('+00:00', 'Z')


def notice_time(value):
    if not isinstance(value, str):
        raise ValueError('first_listed_at missing or not a string')
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    # The frozen source contract declares first_listed_at to be KST.
    if parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.astimezone(UTC)


def _ticker_details(title):
    values = []
    ignored = []
    for inside in re.findall(r'\(([^()]*)\)', title):
        inside = inside.strip()
        # Ticker lists and the older "Korean name TICKER" form are in scope.
        # Explanatory swap/network annotations are not additional listing assets:
        # e.g. (T) followed by (NU <> T 스왑 사이트 추가 안내) lists T, not NU.
        if re.fullmatch(r'[A-Z0-9]+(?:\s*[,/]\s*[A-Z0-9]+)*', inside):
            tokens = re.split(r'\s*[,/]\s*', inside)
        else:
            named = re.fullmatch(r'[^A-Za-z0-9]+\s*([A-Z0-9]*[A-Z][A-Z0-9]*)', inside)
            tokens = [named.group(1)] if named and re.search(r'[가-힣]', inside) else []
            if not tokens:
                mentioned = [t for t in re.findall(r'(?<![A-Za-z0-9])([A-Z0-9]*[A-Z][A-Z0-9]*)(?![A-Za-z0-9])', inside) if t not in MARKET_LABELS]
                if mentioned:
                    ignored.append({'parenthetical': inside, 'mentioned_tokens': mentioned,
                                    'reason': 'BACKGROUND_OR_AMBIGUOUS_ANNOTATION_NOT_TICKER_LIST'})
        for token in tokens:
            if token not in MARKET_LABELS and re.search('[A-Z]', token) and token not in values:
                values.append(token)
    return values, ignored


def extract_tickers(title):
    return _ticker_details(title)[0]


def extract_markets(title):
    markets = set(re.findall(r'\b(?:KRW|BTC|USDT)\b', title))
    # Older notices use the unambiguous Korean label for the KRW market.
    if re.search(r'원화\s*마켓', title):
        markets.add('KRW')
    return sorted(markets)


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()


def _load_page(path):
    entry = {'path': str(path), 'exists': path.exists(), 'valid': False}
    if not path.exists():
        entry['error'] = 'MISSING_PAGE'
        return entry, None
    raw = path.read_bytes()
    entry['sha256'] = hashlib.sha256(raw).hexdigest()
    try:
        value = json.loads(raw)
        data = value['data']
        if value.get('success') is not True or not isinstance(data.get('notices'), list):
            raise ValueError('unsupported notice page schema')
        entry.update(valid=True, notice_count=len(data['notices']), total_count=data.get('total_count'),
                     total_pages=data.get('total_pages'))
        return entry, value
    except (ValueError, KeyError, TypeError) as exc:
        entry['error'] = 'INVALID_PAGE: ' + str(exc)
        return entry, None


def parse_archive(raw_dir):
    """Use each valid original page; repaired pages are fallback only.

    ``raw_dir`` holds upbit/ and upbit_redownload/. All raw page hashes and
    repair comparisons are retained. Material revisions of a notice are flagged,
    rather than selecting a convenient title/time. Event identity is notice ID
    plus ticker, with exact repeated identities deduplicated.
    """
    root = Path(raw_dir)
    pages = []
    revision_checks = []
    notices = []
    versions = defaultdict(list)
    selected_numbers = set()
    original_numbers = set()
    for p in (root/'upbit').glob('page_*.json'):
        match = re.fullmatch(r'page_(\d+)\.json', p.name)
        if match:
            original_numbers.add(int(match.group(1)))
    replacement_numbers = set()
    for p in (root/'upbit_redownload').glob('page_*.json'):
        match = re.fullmatch(r'page_(\d+)\.json', p.name)
        if match:
            replacement_numbers.add(int(match.group(1)))
    for number in sorted(original_numbers | replacement_numbers):
        original, original_value = _load_page(root/'upbit'/f'page_{number}.json')
        repaired, repaired_value = _load_page(root/'upbit_redownload'/f'page_{number}.json')
        chosen = original_value if original_value is not None else repaired_value
        used = original if original_value is not None else repaired
        pages.append({'page': number, 'original': original, 'replacement': repaired,
                      'chosen_path': used['path'] if chosen is not None else None,
                      'fallback_used': original_value is None and repaired_value is not None})
        if repaired['exists']:
            revision_checks.append({'page': number,
                'original_valid': original['valid'], 'replacement_valid': repaired['valid'],
                'raw_bytes_differ': original.get('sha256') != repaired.get('sha256'),
                'notice_payloads_differ': (original_value['data']['notices'] != repaired_value['data']['notices'])
                    if original_value is not None and repaired_value is not None else None,
                'replacement_used': original_value is None and repaired_value is not None})
        # Preserve alternate notice revisions for matching IDs, even when the
        # valid original remains the selected sampling page.
        for source, payload in ((original, original_value), (repaired, repaired_value)):
            if payload is None:
                continue
            for notice in payload['data']['notices']:
                if isinstance(notice, dict) and notice.get('id') is not None:
                    versions[str(notice['id'])].append({'source_path': source['path'], 'notice': notice})
        if chosen is not None:
            selected_numbers.add(number)
            for notice in chosen['data']['notices']:
                notices.append((notice, used['path']))
    expected_page_counts = {p[k].get('total_pages') for p in pages for k in ('original', 'replacement') if p[k]['valid']}
    expected_page_counts.discard(None)
    max_page = max(expected_page_counts | original_numbers | replacement_numbers, default=0)
    missing_pages = sorted(set(range(1, max_page+1)) - selected_numbers)
    declared_total_counts = sorted({p[k]['total_count'] for p in pages for k in ('original', 'replacement')
                                    if p[k]['valid'] and isinstance(p[k].get('total_count'), int)})
    events = {}
    rejected = []
    ignored_annotations = []
    unique_notice_ids = set()
    duplicate_event_occurrences = 0
    for notice, source_path in notices:
        if not isinstance(notice, dict):
            rejected.append({'source_path': source_path, 'reason': 'NOTICE_NOT_OBJECT'})
            continue
        identity = notice.get('id')
        title = notice.get('title')
        base = {'notice_id': identity, 'title': title, 'source_path': source_path}
        if identity is None:
            rejected.append({**base, 'reason': 'MISSING_NOTICE_ID'})
            continue
        unique_notice_ids.add(str(identity))
        if not isinstance(title, str) or FAMILY_TEXT not in title:
            rejected.append({**base, 'reason': 'OUTSIDE_FROZEN_TITLE_FAMILY'})
            continue
        tickers, annotations = _ticker_details(title)
        for annotation in annotations:
            record = {**base, **annotation}
            if record not in ignored_annotations:
                ignored_annotations.append(record)
        if not tickers:
            rejected.append({**base, 'reason': 'NO_UNAMBIGUOUS_TICKER'})
            continue
        try:
            at = notice_time(notice.get('first_listed_at'))
        except (ValueError, TypeError):
            rejected.append({**base, 'reason': 'INVALID_FIRST_LISTED_AT'})
            continue
        markets = extract_markets(title)
        material_versions = set()
        revision_values = []
        for value in versions[str(identity)]:
            raw_notice = value['notice']
            material_versions.add(_canonical({'title': raw_notice.get('title'),
                                              'first_listed_at': raw_notice.get('first_listed_at')}))
            if not any(_canonical(v['notice']) == _canonical(raw_notice) for v in revision_values):
                revision_values.append(value)
        review = []
        if not markets:
            review.append('UNKNOWN_MARKET_LABEL')
        if len(material_versions) > 1:
            review.append('CONFLICTING_NOTICE_REVISIONS')
        for ticker in tickers:
            event_id = f'UPBIT:{identity}:{ticker}'
            if event_id in events:
                duplicate_event_occurrences += 1
                if source_path not in events[event_id]['source_pages']:
                    events[event_id]['source_pages'].append(source_path)
                continue
            events[event_id] = {'event_id': event_id, 'notice_id': identity, 'ticker': ticker,
                'symbol': ticker+'USDT', 'title': title, 'markets': markets,
                'primary_krw': 'KRW' in markets,
                'notice_at': _stamp(at),
                'entry_at': _stamp(at.replace(minute=0, second=0, microsecond=0)+dt.timedelta(hours=1)),
                'time_basis': 'first_listed_at; timezone-naive values interpreted as source-declared KST',
                'eligible_primary': 'KRW' in markets and not review,
                'binance_notice_time_eligibility': 'NOT_YET_CHECKED',
                'review_required': review, 'source_pages': [source_path],
                'notice_revision_count': len(revision_values), 'notice_revisions': revision_values}
    ordered = sorted(events.values(), key=lambda x: (x['notice_at'], x['event_id']))
    return {'schema': 'INFO_MAGNET_NOTICE_INVENTORY_V1', 'prices_read': False,
            'frozen_title_family': FAMILY_TEXT, 'events': ordered,
            'event_count': len(ordered), 'primary_krw_events': sum(e['primary_krw'] for e in ordered),
            'eligible_primary_notice_events': sum(e['eligible_primary'] for e in ordered),
            'notice_count': len(notices), 'unique_notice_ids': len(unique_notice_ids),
            'duplicate_event_occurrences': duplicate_event_occurrences,
            'declared_total_counts': declared_total_counts, 'missing_pages': missing_pages,
            'pages': pages, 'revision_checks': revision_checks, 'rejected_notices': rejected,
            'ignored_parenthetical_annotations': ignored_annotations,
            'limitations': ['Notice eligibility is separate from Binance instrument/price eligibility.',
                            'Frozen title matching excludes later wording changes and other notice families.',
                            'Notice ID plus ticker is the event identity; one multi-market notice is not several independent events.']}


def _percentile(values, fraction):
    if not values:
        return None
    at = (len(values)-1)*fraction
    lower = math.floor(at)
    upper = math.ceil(at)
    return values[lower] + (values[upper]-values[lower])*(at-lower)


def summarize_paired(rows, *, expected_primary_count=None, unresolved_primary=0,
                     bootstrap_reps=10000, seed=20261104):
    """Descriptive primary paired test, bootstrap whole UTC notice-date clusters.

    Each supplied row is a primary event with event_id, notice_at (or notice_date),
    event_gross_return, and exactly five control_gross_returns. Returns are
    fractions. Formula fixed by addendum: event gross - mean controls - cost.
    Bootstrap samples dates equally and then computes the event-weighted mean
    across all sampled cluster members. No prices are read or outcomes mutated.
    """
    if bootstrap_reps < 1 or isinstance(bootstrap_reps, bool):
        raise ValueError('positive bootstrap_reps required')
    if unresolved_primary < 0:
        raise ValueError('unresolved_primary must be nonnegative')
    seen = set()
    valid = []
    invalid = []
    for row in rows:
        identity = row.get('event_id')
        try:
            if not identity or identity in seen:
                raise ValueError('missing or duplicate event identity')
            seen.add(identity)
            controls = row['control_gross_returns']
            values = [row['event_gross_return'], *controls]
            if len(controls) != 5 or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in values):
                raise ValueError('one finite event return and exactly five finite controls required')
            date_text = row.get('notice_at') or row.get('notice_date')
            if not isinstance(date_text, str):
                raise ValueError('notice date required')
            date = notice_time(date_text).date().isoformat() if 'T' in date_text else dt.date.fromisoformat(date_text).isoformat()
            control = sum(controls)/5
            valid.append({'event_id': identity, 'date': date, 'gross': float(values[0]),
                          'control_gross': control, 'gross_excess': float(values[0])-control})
        except (KeyError, TypeError, ValueError) as exc:
            invalid.append({'event_id': identity, 'reason': str(exc)})
    n = len(valid)
    expected = len(rows)+unresolved_primary if expected_primary_count is None else expected_primary_count
    if not isinstance(expected, int) or isinstance(expected, bool) or expected < n:
        raise ValueError('expected_primary_count cannot be less than valid outcomes')
    unresolved = max(unresolved_primary+len(invalid), expected-n)
    clusters = defaultdict(list)
    for row in valid:
        clusters[row['date']].append(row)
    summaries = [(sum(r['gross'] for r in records), sum(r['gross_excess'] for r in records), len(records))
                 for _, records in sorted(clusters.items())]
    owner_boot = []
    exploratory_boot = []
    if len(summaries) >= 2:
        rng = random.Random(seed)
        for _ in range(bootstrap_reps):
            sample = [summaries[rng.randrange(len(summaries))] for __ in summaries]
            count = sum(x[2] for x in sample)
            gross_excess = sum(x[1] for x in sample)/count
            owner_boot.append(gross_excess-.02)
            exploratory_boot.append(gross_excess-.006)
        owner_boot.sort()
        exploratory_boot.sort()
    mean_event = sum(r['gross'] for r in valid)/n if n else None
    mean_control = sum(r['control_gross'] for r in valid)/n if n else None
    mean_excess = sum(r['gross_excess'] for r in valid)/n if n else None
    def cost_summary(cost, samples):
        return {'round_trip_cost_fraction': cost,
                'mean_event_net_return': mean_event-cost if n else None,
                'mean_paired_net_excess': mean_excess-cost if n else None,
                'paired_net_excess_95_ci': [_percentile(samples,.025),_percentile(samples,.975)]}
    owner = cost_summary(.02, owner_boot)
    original = cost_summary(.006, exploratory_boot)
    lower = owner['paired_net_excess_95_ci'][0]
    checks = {'at_least_30_events': n >= 30,
              'no_unresolved_primary_outcomes': unresolved == 0,
              'positive_mean_event_net_after_owner_cost': owner['mean_event_net_return'] is not None and owner['mean_event_net_return'] > 0,
              'positive_owner_paired_excess_lower_95': lower is not None and lower > 0}
    return {'schema': 'INFO_MAGNET_PAIRED_STATS_V1', 'status': 'EXPLORATORY_RETROSPECTIVE_PILOT',
            'n': n, 'expected_primary_count': expected, 'unresolved_primary': unresolved,
            'invalid_rows': invalid, 'utc_notice_date_clusters': len(clusters),
            'mean_event_gross_return': mean_event, 'mean_control_gross_return': mean_control,
            'mean_paired_gross_excess': mean_excess, 'original_cost': original, 'owner_cost': owner,
            'bootstrap': {'reps': bootstrap_reps, 'seed': seed, 'unit': 'UTC notice-date cluster',
                          'estimator': 'event-weighted mean within sampled date clusters',
                          'interval': 'percentile 2.5 and 97.5; linear percentile interpolation',
                          'uncertainty_status': 'ESTIMATED' if len(clusters) >= 2 else 'INSUFFICIENT_DATE_CLUSTERS'},
            'gate_checks': checks, 'pass_gate': all(checks.values()),
            'formula': 'event_gross_return - mean(five_control_gross_returns) - round_trip_cost_fraction',
            'entry_permission': False,
            'limitations': ['A pass qualifies only for the owner-authorized prospective paper test, never live entry.',
                            'This pilot uses historically seen price periods and is not an untouched confirmatory holdout.',
                            'Fewer than two dates cannot estimate date-cluster uncertainty.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    events = commands.add_parser('events', help='Inventory notices without reading prices')
    events.add_argument('--raw-dir', type=Path, required=True)
    events.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    result = parse_archive(args.raw_dir)
    text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()

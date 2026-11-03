"""At most six public GETs total. No authenticated endpoints or retries."""
import hashlib
import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D, ROUND_FLOOR
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'kod-crypto-repair/idx-signals'))
from idxsig.paper_execution_feasibility import (AverageReference, BookSnapshot, FilterSnapshot,
                                               Intent, SimulatedCounts, estimate)

def save(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, default=str) + '\n')

if (HERE / 'requests.json').exists():
    raise SystemExit('One bounded capture already started; refusing to repeat.')
requests = []
save('requests.json', requests)

def get(pair, endpoint):
    if len(requests) >= 6:
        raise RuntimeError('six-request budget exhausted')
    url = f'https://data-api.binance.vision/api/v3/{endpoint}?symbol={pair}'
    if endpoint == 'depth':
        url += '&limit=100'
    started = datetime.now(timezone.utc)
    rec = {'symbol': pair, 'endpoint': endpoint, 'url': url, 'request_start_utc': started}
    requests.append(rec)
    save('requests.json', requests)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'KOD-paper-feasibility-audit/1'}), timeout=20) as resp:
            raw, code = resp.read(), resp.status
    except urllib.error.HTTPError as exc:
        raw, code = exc.read(), exc.code
    except Exception as exc:
        rec.update(error=str(exc), received_utc=datetime.now(timezone.utc))
        save('requests.json', requests)
        raise RuntimeError('capture unavailable; stopped without bypass') from exc
    received = datetime.now(timezone.utc)
    rec.update(received_utc=received, http_status=code, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    (HERE / f'{pair}-{endpoint}.json').write_bytes(raw)
    save('requests.json', requests)
    body = json.loads(raw)
    # This exact documented response means no reference ever set, not access denial.
    absent = endpoint == 'referencePrice' and code == 400 and body.get('code') == -2043
    if code != 200 and not absent:
        raise RuntimeError(f'HTTP {code}: stopped without retry or alternate host')
    return body, rec, absent

meta = json.loads((HERE.parent / 'exchangeInfo.json').read_text())
original = json.loads((HERE.parent / 'provenance.json').read_text())
info = {s['symbol']: s for s in meta['symbols']}
outcomes = []
try:
    for pair in ('BTCUSDT', 'BEAMXUSDT'):
        avg, ap, _ = get(pair, 'avgPrice')
        override, rp, absent = get(pair, 'referencePrice')
        raw, bp, _ = get(pair, 'depth')
        received, placed = bp['received_utc'], bp['request_start_utc']
        if absent or ('referencePrice' in override and override['referencePrice'] is None):
            state = 'ABSENT'
        elif override.get('referencePrice') is not None:
            state = 'PRESENT'
        else:
            state = 'UNKNOWN'
        reference = AverageReference(pair, D(avg['price']), avg['mins'], ap['received_utc'],
                                     datetime.fromtimestamp(avg['closeTime']/1000, timezone.utc), ap['url'],
                                     state, rp['received_utc'], rp['url'])
        filters = FilterSnapshot(pair, datetime.fromisoformat(original['received_utc']), original['url'], tuple(info[pair]['filters']))
        book = BookSnapshot(pair, received, bp['url'], tuple((D(p), D(q)) for p, q in raw['bids']),
                            tuple((D(p), D(q)) for p, q in raw['asks']))
        counts = SimulatedCounts(pair, placed, 0, 0)
        row = {'symbol': pair, 'reference': asdict(reference), 'simulated_counts': asdict(counts),
               'symbol_status_from_original_capture': info[pair]['status'], 'estimates': []}
        step = D(next(f['stepSize'] for f in filters.filters if f['filterType'] == 'LOT_SIZE'))
        for target in (D('100'), D('1000')):
            price = book.asks[0][0]
            qty = (target / price / step).to_integral_value(rounding=ROUND_FLOOR) * step
            intent = Intent(pair, 'BUY', qty, price, placed)
            result = estimate(intent, book, filters, now=received, max_book_age=timedelta(seconds=10),
                              max_filter_age=timedelta(minutes=10), fee_rate=D('0.001'), average=reference,
                              simulated_counts=counts, max_reference_age=timedelta(seconds=30), max_count_age=timedelta(seconds=30))
            row['estimates'].append({'target_notional_usdt': target, 'intent': asdict(intent), 'result': asdict(result)})
        outcomes.append(row)
except Exception as exc:
    outcomes.append({'capture_stopped': str(exc), 'requests_attempted': len(requests)})
save('outcomes.json', outcomes)
print(json.dumps(outcomes, indent=2, default=str))

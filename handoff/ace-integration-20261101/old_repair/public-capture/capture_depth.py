"""One bounded public-only capture; not a service, strategy or order sender."""
import hashlib
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
from dataclasses import asdict

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'kod-crypto-repair/idx-signals'))
from idxsig.paper_execution_feasibility import BookSnapshot, FilterSnapshot, Intent, estimate

def stamp():
    return datetime.now(timezone.utc)

def save(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, default=str) + '\n')

if (HERE / 'outcomes.json').exists():
    raise SystemExit('Bounded capture already completed; refusing to repeat.')
meta = json.loads((HERE / 'exchangeInfo.json').read_text())
provenance = json.loads((HERE / 'provenance.json').read_text())
observed_filters = datetime.fromisoformat(provenance['received_utc'])
symbols = {s['symbol']: s for s in meta['symbols']}
outcomes = []
for pair in ('BTCUSDT', 'ETHUSDT', 'BEAMXUSDT'):
    info = symbols.get(pair)
    if info is None:
        outcomes.append({'symbol': pair, 'status': 'UNAVAILABLE_IN_EXCHANGE_INFO'})
        continue
    url = f'https://data-api.binance.vision/api/v3/depth?symbol={pair}&limit=100'
    started = stamp()
    rec = {'symbol': pair, 'url': url, 'request_start_utc': started}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'KOD-paper-feasibility-audit/1'}), timeout=20) as response:
            raw = response.read()
            rec['http_status'] = response.status
        received = stamp()
        rec.update(received_utc=received, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        (HERE / f'{pair}-depth.json').write_bytes(raw)
        depth = json.loads(raw)
    except Exception as exc:
        rec.update(received_utc=stamp(), error_type=type(exc).__name__, error=str(exc), status='CAPTURE_FAILED_STOPPED')
        save(f'{pair}-provenance.json', rec)
        outcomes.append(rec)
        break  # No alternate host, retries, or bypass.
    save(f'{pair}-provenance.json', rec)
    known = {'PRICE_FILTER', 'LOT_SIZE', 'MIN_NOTIONAL', 'NOTIONAL'}
    # Classification is descriptive only. Every observed row is passed unchanged.
    irrelevant = {'MARKET_LOT_SIZE': 'market orders only; this is LIMIT/IOC',
                  'ICEBERG_PARTS': 'no iceberg quantity requested',
                  'TRAILING_DELTA': 'not a trailing order',
                  'MAX_NUM_ALGO_ORDERS': 'not an algo/conditional order',
                  'MAX_NUM_ICEBERG_ORDERS': 'not an iceberg order',
                  'MAX_NUM_ORDER_AMENDS': 'new intent, not an amendment',
                  'MAX_NUM_ORDER_LISTS': 'standalone intent, not an order list'}
    unsupported = [{'type': f['filterType'], 'classification': 'inapplicable_to_plain_limit_ioc' if f['filterType'] in irrelevant else 'unsupported_requires_other_evidence',
                    'detail': irrelevant.get(f['filterType'], 'Required evidence/validation unavailable; do not infer pass.')}
                   for f in info['filters'] if f['filterType'] not in known]
    fs = FilterSnapshot(pair, observed_filters, provenance['url'], tuple(info['filters']))
    book = BookSnapshot(pair, received, url,
                        tuple((D(p), D(q)) for p, q in depth['bids']),
                        tuple((D(p), D(q)) for p, q in depth['asks']))
    result = {'symbol': pair, 'exchange_status': info['status'], 'order_types': info.get('orderTypes'),
              'unsupported_filters': unsupported, 'book_levels': [len(book.bids), len(book.asks)],
              'last_update_id': depth.get('lastUpdateId'), 'estimates': []}
    for notional in (D('100'), D('1000')):
        if info['status'] != 'TRADING' or 'LIMIT' not in info.get('orderTypes', []) or not book.asks:
            result['estimates'].append({'target_notional_usdt': notional, 'status': 'REJECTED', 'reason': 'SYMBOL_STATUS_ORDER_TYPE_OR_BOOK_UNAVAILABLE'})
            continue
        # A fixed mechanical fixture, not a strategy choice or buy signal.
        limit = book.asks[0][0]
        intent = Intent(pair, 'BUY', notional / limit, limit, started)
        est = estimate(intent, book, fs, now=received, max_book_age=timedelta(seconds=10),
                       max_filter_age=timedelta(minutes=10), fee_rate=D('0.001'))
        result['estimates'].append({'target_notional_usdt': notional, 'intent': asdict(intent),
                                    'result': asdict(est), 'fee_assumption': '0.1% of consumed quote notional; hypothetical, not account-specific'})
    outcomes.append(result)
save('outcomes.json', outcomes)
print(json.dumps(outcomes, indent=2, default=str))

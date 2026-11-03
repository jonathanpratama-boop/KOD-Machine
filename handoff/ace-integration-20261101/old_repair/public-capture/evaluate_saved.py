"""Offline sizing correction against the same captured inputs; never fetches."""
import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta
from decimal import Decimal as D, ROUND_FLOOR
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'kod-crypto-repair/idx-signals'))
from idxsig.paper_execution_feasibility import BookSnapshot, FilterSnapshot, Intent, estimate

original = json.loads((HERE / 'outcomes.json').read_text())
info = {s['symbol']: s for s in json.loads((HERE / 'exchangeInfo.json').read_text())['symbols']}
meta = json.loads((HERE / 'provenance.json').read_text())
for row in original:
    pair = row['symbol']
    p = json.loads((HERE / f'{pair}-provenance.json').read_text())
    depth = json.loads((HERE / f'{pair}-depth.json').read_text())
    received, started = (datetime.fromisoformat(p[k]) for k in ('received_utc', 'request_start_utc'))
    book = BookSnapshot(pair, received, p['url'],
                        tuple((D(a), D(b)) for a, b in depth['bids']),
                        tuple((D(a), D(b)) for a, b in depth['asks']))
    fs = FilterSnapshot(pair, datetime.fromisoformat(meta['received_utc']), meta['url'], tuple(info[pair]['filters']))
    step = D(next(f['stepSize'] for f in fs.filters if f['filterType'] == 'LOT_SIZE'))
    row['estimates'] = []
    for target in (D('100'), D('1000')):
        limit = book.asks[0][0]
        qty = (target / limit / step).to_integral_value(rounding=ROUND_FLOOR) * step
        intent = Intent(pair, 'BUY', qty, limit, started)
        result = estimate(intent, book, fs, now=received, max_book_age=timedelta(seconds=10),
                          max_filter_age=timedelta(minutes=10), fee_rate=D('0.001'))
        row['estimates'].append({'target_notional_usdt': target, 'sized_notional_usdt': qty * limit,
                                'intent': asdict(intent), 'result': asdict(result),
                                'fee_assumption': '0.1% quote-notional fee, not account-specific'})
    row['evaluation_note'] = 'Initial adapter division exceeded supported Decimal scale and was rejected. Offline sizing now floors to observed lot step; same capture, all observed filters intact, no network retry.'
(HERE / 'outcomes-sized.json').write_text(json.dumps(original, indent=2, default=str) + '\n')
for row in original:
    print(row['symbol'], [(str(e['target_notional_usdt']), e['result']['reason']) for e in row['estimates']])

"""Supply receipt-timed daily history to the existing R2 comparison matcher.

The collector and its frozen engine keep running. This small input worker uses
the engine's existing transactional enqueue API; it never edits old decisions.
Exact HTTP responses and this amendment live in the existing backed-up archive.
"""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.environ.get('KOD_R2_CODE', '/opt/kod/research-r2'))
from broad_observer.store import BroadStore
from research_r2.engine import ResearchEngine, canonical, iso, stamp

DAY = 86400
PREFIX = 'comparison-daily:'
KIND = 'comparison_daily'
VERSION = 'KOD_R2_COMPARISON_INPUT_REPAIR_V1'


def daily_items(store, event):
    """Decode only closed, complete source days, available at actual receipt."""
    items = []
    for request in event['requests']:
        if request.get('status_code') != 200:
            continue
        started, received = stamp(request['request_started_at']), stamp(request['received_at'])
        cutoff = stamp(request['cutoff_exclusive'])
        if not started <= received or cutoff > math.floor(started / DAY) * DAY:
            raise ValueError('daily history cutoff or receipt is invalid')
        rows = json.loads(store.read_object(request['body_object']))
        if not isinstance(rows, list) or len(rows) != 30:
            raise ValueError('exactly 30 completed daily bars required')
        for index, row in enumerate(rows):
            opened = cutoff - (30 - index) * DAY
            volume = float(row[7])
            if (row[0] != int(opened * 1000) or row[6] != int((opened + DAY) * 1000) - 1
                    or not math.isfinite(volume) or volume < 0):
                raise ValueError('daily source grid or volume is invalid')
            items.append({'kind': 'daily', 'symbol': request['symbol'],
                          'opened': iso(opened), 'received_at': iso(received),
                          'quote_volume': row[7]})
    return items


def engine_config(state):
    # This is the exact configuration actually bound to the running ledger.
    con = sqlite3.connect('file:' + str(state / 'engine/research.sqlite') + '?mode=ro',
                          uri=True, detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        return json.loads(con.execute("SELECT payload FROM ledger WHERE id='config'").fetchone()[0])['config']
    finally:
        con.close()


def archive_amendment(store):
    code = Path(__file__).read_bytes()
    note = Path(__file__).with_name('AMENDMENT.md').read_bytes()
    name = 'comparison-input-repair-v1:' + hashlib.sha256(code + note).hexdigest()[:16]
    # Lookup only today's live segment; a persisted marker avoids later repeats.
    when = dt.datetime.now(dt.timezone.utc)
    old = store.lookup(name, when)
    if old:
        return old
    files = []
    for filename in ('comparison_inputs.py', 'AMENDMENT.md'):
        path = Path(__file__).with_name(filename)
        files.append({'name': filename, 'body': path.read_bytes()})
    return store.append_batch(name, when, 'AMENDMENT', files, {
        'version': VERSION, 'recorded_at': iso(when),
        'scope': 'Daily liquidity comparison inputs known only at actual receipt; future decisions only.',
        'old_events_rewritten': False,
        'collector_restart_required': False,
    }, kind='comparison_amendment')


def archive_ready(store):
    now = time.time()
    # The collector owns rollover and needs time to flush yesterday's buckets.
    if now % DAY < 300:
        return False
    catalog = json.loads(store.catalog_path.read_text())
    return catalog.get('active_day') == iso(now)[:10]


def open_input_queue(state, config):
    # Reuse enqueue's transaction/ledger logic without running the engine
    # constructor's schema/cache initialization beside the active worker.
    queue = ResearchEngine.__new__(ResearchEngine)
    queue.db = sqlite3.connect(str(state / 'engine/research.sqlite'), timeout=30,
        isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)
    queue.db.row_factory = sqlite3.Row
    queue.end = stamp(config['t0']) + 35 * DAY + 120
    queue.primary = tuple(sorted(row['symbol'] for row in config['primary']))
    return queue


def fetch_daily(symbol, cutoff):
    params = urllib.parse.urlencode({'symbol': symbol, 'interval': '1d',
        'startTime': int((cutoff - 30 * DAY) * 1000),
        'endTime': int(cutoff * 1000) - 1, 'limit': 30})
    url = 'https://api.binance.com/api/v3/klines?' + params
    started = dt.datetime.now(dt.timezone.utc)
    retry_at = None
    request = urllib.request.Request(url, headers={'User-Agent': 'KOD-R2-comparison-inputs/1'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw, status = response.read(256 * 1024), response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(256 * 1024), exc.code
        retry_after = exc.headers.get('Retry-After')
        try:
            retry_at = time.time() + float(retry_after) if retry_after else None
        except ValueError:
            from email.utils import parsedate_to_datetime
            retry_at = parsedate_to_datetime(retry_after).timestamp()
    received = dt.datetime.now(dt.timezone.utc)
    return {'symbol': symbol, 'url': url, 'interval': '1d', 'status_code': status,
        'request_started_at': iso(started), 'received_at': iso(received),
        'cutoff_exclusive': iso(cutoff), 'body': raw,
        'retry_at': retry_at if status == 429 else None}


def atomic_json(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(canonical(data) + '\n')
    os.replace(temp, path)


def run(state):
    folder = state / 'comparison-inputs'; folder.mkdir(exist_ok=True)
    with (folder / 'worker.lock').open('a+b') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'status': 'ALREADY_RUNNING'}
        config = engine_config(state)
        now = time.time()
        if now >= stamp(config['t0']) + 30 * DAY:
            return {'status': 'ADMISSIONS_FINISHED'}
        status_path = folder / 'HEALTH.json'
        previous = json.loads(status_path.read_text()) if status_path.exists() else {}
        if previous.get('provider_stopped'):
            return previous
        if previous.get('retry_at', 0) > now:
            return previous
        store = BroadStore(state)
        if not archive_ready(store):
            return {'status': 'WAITING_FOR_COLLECTOR_DAY_ROLLOVER'}
        if not (folder / 'AMENDMENT.json').exists():
            receipt = archive_amendment(store)
            atomic_json(folder / 'AMENDMENT.json', receipt)
        engine = open_input_queue(state, config)
        try:
            cutoff = math.floor(now / DAY) * DAY
            symbols = sorted(engine.primary)
            report = {'schema': VERSION, 'as_of': iso(now), 'cutoff_exclusive': iso(cutoff),
                'status': 'REFRESHING', 'total_symbols': len(symbols), 'queued_symbols': 0,
                'errors': [], 'collector_restarted': False, 'old_events_rewritten': False,
                'provider_stopped': False}
            for symbol in symbols:
                n = engine.db.execute('SELECT count(*) FROM daily WHERE symbol=? AND opened>=? AND opened<?',
                                      (symbol, cutoff - 30 * DAY, cutoff)).fetchone()[0]
                if n == 30:
                    continue
                # A worker retry may precede normal processing of the queued data.
                if engine.db.execute("SELECT 1 FROM pending WHERE kind='daily' AND json_extract(payload,'$.symbol')=? AND json_extract(payload,'$.opened')=? LIMIT 1",
                                     (symbol, iso(cutoff - DAY))).fetchone():
                    continue
                try:
                    attempt = fetch_daily(symbol, cutoff)
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    report['errors'].append({'symbol': symbol, 'reason': str(exc)})
                    break
                if not archive_ready(store) or math.floor(time.time() / DAY) * DAY != cutoff:
                    report['errors'].append({'symbol': symbol, 'reason': 'UTC day changed; defer to next run'})
                    break
                receipt = store.append_batch('comparison-daily:' + symbol + ':' + attempt['received_at'],
                    dt.datetime.now(dt.timezone.utc), 'OK' if attempt['status_code'] == 200 else 'HTTP_ERROR',
                    [attempt], {'version': VERSION, 'symbol': symbol,
                                'only_available_at_actual_receipt': True}, kind=KIND)
                # Resolve through the archive, so normalized inputs are reproducible.
                event = store.iter_batches(receipt['day'], after_seq=receipt['seq'], limit=1)[0]
                if attempt['status_code'] != 200:
                    report['errors'].append({'symbol': symbol, 'status_code': attempt['status_code']})
                    if attempt['status_code'] == 429:
                        report['retry_at'] = attempt.get('retry_at') or time.time() + 900
                        break
                    if attempt['status_code'] in (403, 418, 451):
                        report['provider_stopped'] = True
                        break
                    continue
                try:
                    items = daily_items(store, event)
                    engine.enqueue(PREFIX + event['hash'], items)
                    report['queued_symbols'] += 1
                except (ValueError, TypeError, IndexError, KeyError) as exc:
                    report['errors'].append({'symbol': symbol, 'reason': str(exc)})
                # Share the host with the minute/detail collectors. Spread the
                # small daily refresh instead of creating a request burst.
                time.sleep(1)
            counts = [engine.db.execute('SELECT count(*) FROM daily WHERE symbol=? AND opened>=? AND opened<?',
                      (s, cutoff - 30 * DAY, cutoff)).fetchone()[0] for s in symbols]
            report.update(as_of=iso(time.time()), daily_ready_symbols=sum(n == 30 for n in counts))
            report['status'] = ('PROVIDER_STOPPED' if report['provider_stopped'] else
                'PARTIAL' if report['errors'] else 'READY' if report['daily_ready_symbols'] == len(symbols) else 'QUEUED')
            atomic_json(status_path, report)
            return report
        finally:
            engine.close()


def input_loader_with_comparisons(store, config, warmup_manifest=None):
    """Recovery uses archived response bytes, never a new historical request."""
    from research_r2.recovery import input_loader
    original = input_loader(store, config, warmup_manifest)
    records = {}
    for day in json.loads(store.catalog_path.read_text())['days']:
        cursor = 0
        while True:
            rows = store.iter_batches(day['day'], after_seq=cursor, limit=100)
            if not rows:
                break
            for row in rows:
                if row['kind'] == KIND:
                    records[PREFIX + row['hash']] = row
            cursor = rows[-1]['seq'] + 1
    def resolve(ident):
        if ident.startswith(PREFIX):
            return daily_items(store, records[ident])
        return original(ident)
    return resolve


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, default=Path('/var/lib/kod/research-r2'))
    args = parser.parse_args()
    print(json.dumps(run(args.state), sort_keys=True))

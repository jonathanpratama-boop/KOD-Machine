"""Independent recomputation of INFO_MAGNET scored events from raw Binance archives.

Usage: python3 -I recompute.py REVIEW_DIR PRICE_DIR OUT_JSON
Reads only; writes one JSON of diagnostics to OUT_JSON.
"""
import csv, datetime as dt, hashlib, io, json, random, sys, zipfile
from pathlib import Path

UTC = dt.timezone.utc
review, price, out = map(Path, sys.argv[1:4])
EV = json.load(open(review / 'EVENTS.json'))
UNI = json.load(open(review / 'ARCHIVE-UNIVERSE.json'))
POOL = UNI['control_pool_after_frozen_exclusions']
ALL = UNI['all_historical_usdt_symbols']

def ts(v):
    n = int(v)
    if n >= 10**15:
        return dt.datetime(1970, 1, 1, tzinfo=UTC) + dt.timedelta(microseconds=n)
    return dt.datetime(1970, 1, 1, tzinfo=UTC) + dt.timedelta(milliseconds=n)

_cache = {}
def month_bars(sym, month):
    key = (sym, month)
    if key in _cache:
        return _cache[key]
    z = price / f'data/spot/monthly/klines/{sym}/1h/{sym}-1h-{month}.zip'
    if not z.exists():
        _cache[key] = None
        return None
    raw = z.read_bytes()
    chk = (z.parent / (z.name + '.CHECKSUM')).read_text().split()[0].lower()
    if hashlib.sha256(raw).hexdigest() != chk:
        raise SystemExit(f'CHECKSUM MISMATCH {z}')
    bars = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as a:
        text = a.read(a.infolist()[0].filename).decode('utf-8-sig')
    for r in csv.reader(io.StringIO(text)):
        if not r or r[0] in ('open_time', 'open_timestamp'):
            continue
        o = ts(r[0]); c = ts(r[6])
        if o.minute or o.second or o.microsecond:
            continue
        span = (c - o).total_seconds()
        if span < 3599.99:
            bars.setdefault('_bad', []).append(o.isoformat())
            continue
        bars[o] = dict(open=float(r[1]), high=float(r[2]), low=float(r[3]), close=float(r[4]),
                       vol=float(r[5]), qvol=float(r[7]), trades=int(r[8]))
    _cache[key] = bars
    return bars

def listed_months(sym):
    p = price / 'metadata' / f'months_{sym}.json'
    if not p.exists():
        return None
    keys = json.load(open(p))['keys']
    b = f'data/spot/monthly/klines/{sym}/1h/{sym}-1h-'
    return {k[len(b):-4] for k in keys if k.startswith(b) and k.endswith('.zip')}

def bar(sym, hour):
    b = month_bars(sym, hour.strftime('%Y-%m'))
    return None if b is None else b.get(hour)

def P(s):
    return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))

rows = []
mism = []
ctrl_check = []
for e in EV:
    if e['status'] != 'SCORED':
        continue
    notice = P(e['notice_at']); entry = P(e['entry_at'])
    floor = notice.replace(minute=0, second=0, microsecond=0)
    prior = floor - dt.timedelta(hours=1)
    assert entry == floor + dt.timedelta(hours=1), e['event_id']
    assert entry > notice
    # raw first_listed_at check
    raw = e['notice_revisions'][0]['notice']['first_listed_at']
    assert P(raw).astimezone(UTC) == notice, (raw, e['notice_at'])
    syms = [e['symbol'], *e['control_symbols']]
    rets = {}
    vols = {}
    for s in syms:
        o = bar(s, entry); c = bar(s, entry + dt.timedelta(hours=23)); pr = bar(s, prior)
        rets[s] = c['close'] / o['open'] - 1
        # zero-volume / frozen checks across eligibility, entry and exit window
        window = [bar(s, entry + dt.timedelta(hours=k)) for k in range(24)]
        zero_hours = sum(1 for w in window if w is not None and w['vol'] == 0)
        vols[s] = dict(prior_vol=pr['vol'], prior_trades=pr['trades'], entry_vol=o['vol'],
                       zero_vol_hours_in_window=zero_hours, flat=all(w and w['high'] == w['low'] for w in window))
    if abs(rets[e['symbol']] - e['event_gross_return']) > 1e-9:
        mism.append((e['event_id'], 'event', rets[e['symbol']], e['event_gross_return']))
    for s, v in zip(e['control_symbols'], e['control_gross_returns']):
        if abs(rets[s] - v) > 1e-9:
            mism.append((e['event_id'], s, rets[s], v))
    # spike location around the notice (target only): hourly |ret| and volume
    def hr(h):
        b = bar(e['symbol'], h)
        if b is None:
            # fall back on an adjacent month that may not be cached
            return None
        return b
    prof = {}
    for k in range(-12, 13):
        b = hr(floor + dt.timedelta(hours=k))
        if b:
            prof[k] = (b['close'] / b['open'] - 1, b['qvol'])
    base_q = [prof[k][1] for k in range(-24, -1) if k in prof] or [prof[k][1] for k in prof if k < -1]
    med_q = sorted(base_q)[len(base_q) // 2] if base_q else None
    peak_k = max(prof, key=lambda k: prof[k][1]) if prof else None
    notice_hour_ret = prof.get(0, (None,))[0]
    pre_entry_ret = None
    pb = bar(e['symbol'], prior); eb = bar(e['symbol'], entry)
    if pb and eb:
        pre_entry_ret = eb['open'] / pb['close'] - 1  # last close before notice hour -> entry open
    # control selection reproduction
    pool = [s for s in POOL if s != e['symbol']]
    seed = int.from_bytes(hashlib.sha256(('20261104|' + e['event_id']).encode()).digest(), 'big')
    random.Random(seed).shuffle(pool)
    chosen = []
    skipped = []
    unknown = []
    for cand in pool:
        lm = listed_months(cand)
        if lm is None:
            unknown.append(cand); continue
        if prior.strftime('%Y-%m') not in lm:
            skipped.append((cand, 'month_not_listed')); continue
        b = bar(cand, prior)
        if b is None:
            if month_bars(cand, prior.strftime('%Y-%m')) is None:
                unknown.append(cand); continue
            skipped.append((cand, 'bar_absent')); continue
        chosen.append(cand)
        if len(chosen) == 5:
            break
    ctrl_check.append(dict(event_id=e['event_id'], reproduced=chosen == e['control_symbols'],
                           chosen=chosen, recorded=e['control_symbols'], unknown_before=len(unknown),
                           skipped=len(skipped), probes=e.get('control_eligibility_probes')))
    rows.append(dict(event_id=e['event_id'], symbol=e['symbol'], notice_at=e['notice_at'], entry=e['entry_at'],
                     gross=rets[e['symbol']], controls=[rets[s] for s in e['control_symbols']],
                     vols=vols, notice_hour_ret=notice_hour_ret, pre_entry_ret=pre_entry_ret,
                     peak_qvol_offset=peak_k, peak_over_median=(prof[peak_k][1] / med_q) if (peak_k is not None and med_q) else None,
                     minutes_after_hour=(notice - floor).total_seconds() / 60,
                     h6=e['horizons']['6'], h72=e['horizons']['72']))

json.dump(dict(rows=rows, mismatches=mism, control_check=ctrl_check), open(out, 'w'), indent=1, default=str)
print('scored', len(rows), 'return mismatches', len(mism))
print('controls reproduced', sum(c['reproduced'] for c in ctrl_check), 'of', len(ctrl_check))
print('events with unknown-metadata candidates before 5th control', sum(1 for c in ctrl_check if c['unknown_before']))

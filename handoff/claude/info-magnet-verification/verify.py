"""Independent re-computation of the INFO_MAGNET 24h primary gate from my own
Binance spot 1h monthly archives.  Reads Codex's EVENTS.json as data only.

Usage: python -I verify.py <review_dir> <k1h_dir> <out_json>
"""
import csv
import datetime as dt
import io
import json
import statistics
import sys
import zipfile
from pathlib import Path

UTC = dt.timezone.utc
EPOCH = dt.datetime(1970, 1, 1, tzinfo=UTC)
HOUR = dt.timedelta(hours=1)
HOLD = 24
OWNER_COST = 0.02
ORIG_COST = 0.006


def to_dt(raw):
    """Binance open/close time -> aware datetime, unit decided per value."""
    n = int(raw)
    if n >= 10 ** 14:          # 16-digit microseconds (2025+ spot files)
        return EPOCH + dt.timedelta(microseconds=n), 'us'
    if n >= 10 ** 11:          # 13-digit milliseconds
        return EPOCH + dt.timedelta(milliseconds=n), 'ms'
    raise ValueError(f'unrecognised timestamp {raw}')


def parse_iso(s):
    return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(UTC)


class Bars:
    """Lazy per-symbol, per-month loader over my k1h directory."""

    def __init__(self, root):
        self.root = Path(root)
        self.cache = {}
        self.issues = []          # (symbol, month, kind, detail)
        self.have = {p.name.split('-1h-')[0] for p in self.root.glob('*-1h-*.zip')}

    def month(self, symbol, ym):
        key = (symbol, ym)
        if key in self.cache:
            return self.cache[key]
        path = self.root / f'{symbol}-1h-{ym}.zip'
        bars = None
        if path.exists():
            bars = {}
            with zipfile.ZipFile(path) as z:
                names = [n for n in z.namelist() if n.endswith('.csv')]
                if len(names) != 1:
                    self.issues.append((symbol, ym, 'zip_members', names))
                text = z.read(names[0]).decode()
            for row in csv.reader(io.StringIO(text)):
                if not row or not row[0].strip().lstrip('-').isdigit():
                    if row:
                        self.issues.append((symbol, ym, 'non_numeric_row', row[:2]))
                    continue
                o, ou = to_dt(row[0])
                c, cu = to_dt(row[6])
                span = (c - o)
                expect = HOUR - (dt.timedelta(milliseconds=1) if cu == 'ms' else dt.timedelta(microseconds=1))
                if cu == 'us' and span == HOUR - dt.timedelta(milliseconds=1):
                    # final millisecond written in a microsecond file: nominal hourly bar, flagged
                    self.issues.append((symbol, ym, 'accepted_us_file_final_ms_close', row[0], row[6]))
                    expect = span
                if ou != cu or o.minute or o.second or o.microsecond or span != expect:
                    self.issues.append((symbol, ym, 'irregular_bar_rejected', row[0], row[6]))
                    continue
                vals = dict(open=float(row[1]), high=float(row[2]), low=float(row[3]), close=float(row[4]),
                            volume=float(row[5]), unit=ou)
                if o in bars and any(bars[o][k] != vals[k] for k in ('open', 'high', 'low', 'close')):
                    self.issues.append((symbol, ym, 'conflicting_duplicate', o.isoformat()))
                bars[o] = vals
        self.cache[key] = bars
        return bars

    def bar(self, symbol, hour):
        """Returns (bar|None, reason)."""
        if symbol not in self.have:
            return None, 'SYMBOL_NOT_IN_MY_ARCHIVE'
        m = self.month(symbol, hour.strftime('%Y-%m'))
        if m is None:
            return None, 'MONTH_FILE_MISSING'
        b = m.get(hour)
        return (b, 'OK') if b else (None, 'HOUR_MISSING_IN_MONTH_FILE')


def gross(bars, symbol, entry):
    last = entry + (HOLD - 1) * HOUR
    eo, r1 = bars.bar(symbol, entry)
    ec, r2 = bars.bar(symbol, last)
    if eo is None or ec is None:
        return None, {'entry': r1, 'exit': r2}
    return ec['close'] / eo['open'] - 1, {'entry_open': eo['open'], 'exit_close': ec['close'],
                                          'entry_unit': eo['unit'], 'exit_unit': ec['unit']}


def hours_missing(bars, symbol, start, end):
    """Hours in [start, end] absent from my archive for symbol (gap check over the holding window)."""
    out, h = [], start
    while h <= end:
        b, _ = bars.bar(symbol, h)
        if b is None:
            out.append(h.isoformat())
        h += HOUR
    return out


def summary(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {'n': len(xs), 'mean': statistics.fmean(xs), 'median': statistics.median(xs),
            'min': min(xs), 'max': max(xs)}


def main():
    review, k1h, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    events = json.loads((review / 'EVENTS.json').read_text())
    result = json.loads((review / 'RESULT.json').read_text())
    bars = Bars(k1h)
    discrepancies, per_event = [], []

    scored = [e for e in events if e['status'] == 'SCORED']

    # ---- Part 1: target recompute + their serialized means ----------------------
    for e in scored:
        sym = e['symbol']
        notice = parse_iso(e['notice_at'])
        # independent notice/entry derivation from the retained KST source field
        src = e['notice_revisions'][0]['notice']['first_listed_at']
        src_utc = dt.datetime.fromisoformat(src).astimezone(UTC)
        notice_hour = notice.replace(minute=0, second=0, microsecond=0)
        entry = notice_hour + HOUR
        if src_utc != notice:
            discrepancies.append(f"{e['event_id']}: notice_at {e['notice_at']} != first_listed_at {src} in UTC")
        if parse_iso(e['entry_at']) != entry or parse_iso(e['entry_hour']) != entry:
            discrepancies.append(f"{e['event_id']}: entry_at/entry_hour {e['entry_at']} != floor(notice)+1h {entry.isoformat()}")
        if parse_iso(e['last_exit_bar_hour']) != entry + 23 * HOUR:
            discrepancies.append(f"{e['event_id']}: last_exit_bar_hour {e['last_exit_bar_hour']} != entry+23h")
        if e['symbol'] != e['ticker'] + 'USDT':
            discrepancies.append(f"{e['event_id']}: symbol {e['symbol']} != ticker+USDT")
        if len(e['notice_revisions']) != 1:
            discrepancies.append(f"{e['event_id']}: {len(e['notice_revisions'])} notice revisions")

        g, info = gross(bars, sym, entry)
        row = {'event_id': e['event_id'], 'symbol': sym, 'notice_at': e['notice_at'],
               'entry_hour': entry.isoformat(), 'their_gross': e['event_gross_return'], 'my_gross': g, **info}
        if g is not None:
            row['abs_diff'] = abs(g - e['event_gross_return'])
            gaps = hours_missing(bars, sym, entry, entry + 23 * HOUR)
            if gaps:
                row['holding_window_gaps'] = gaps

        # ---- Part 2 (descriptive, post-result): move already gone before entry ----
        prior_hour = notice_hour - HOUR          # bar whose close is the last close before the notice hour
        pb, pr = bars.bar(sym, prior_hour)
        nb, nr = bars.bar(sym, notice_hour)
        eo, _ = bars.bar(sym, entry)
        if pb and eo:
            row['prior_close'] = pb['close']
            row['pre_entry_move'] = eo['open'] / pb['close'] - 1
        else:
            row['pre_entry_reason'] = {'prior': pr}
        if pb and nb:
            row['notice_hour_high'] = nb['high']
            row['notice_hour_high_move'] = nb['high'] / pb['close'] - 1
            row['notice_hour_close_move'] = nb['close'] / pb['close'] - 1
            row['notice_minute'] = notice.minute
        if pb is None and nb is None:
            pass
        elif nb is None:
            row['notice_hour_reason'] = nr

        # ---- supplementary: their 5 controls from my archives ----------------------
        ctl = []
        for cs, theirs in zip(e['control_symbols'], e['control_gross_returns']):
            cg, cinfo = gross(bars, cs, entry)
            ctl.append({'symbol': cs, 'their': theirs, 'mine': cg,
                        'abs_diff': None if cg is None else abs(cg - theirs),
                        'reason': None if cg is not None else cinfo})
        row['controls'] = ctl

        # cross-check their own 6/72h target values where my archive covers them
        for h in ('6', '72'):
            hz = e['horizons'].get(h, {})
            if hz.get('status') == 'SCORED':
                a, _r = bars.bar(sym, entry)
                b, _r = bars.bar(sym, entry + (int(h) - 1) * HOUR)
                if a and b:
                    row[f'abs_diff_{h}h'] = abs(b['close'] / a['open'] - 1 - hz['event_gross_return'])
        per_event.append(row)

    rec = [r for r in per_event if r['my_gross'] is not None]
    not_rec = [r for r in per_event if r['my_gross'] is None]
    for r in not_rec:
        discrepancies.append(f"{r['event_id']} ({r['symbol']}): not recomputable from my archive: "
                             f"{ {k: r[k] for k in ('entry', 'exit') if k in r} }")
    for r in rec:
        if r['abs_diff'] > 1e-9:
            discrepancies.append(f"{r['event_id']}: gross differs mine {r['my_gross']:.10f} vs theirs {r['their_gross']:.10f}")
        if r.get('holding_window_gaps'):
            discrepancies.append(f"{r['event_id']}: my archive has gaps inside holding window {r['holding_window_gaps']}")

    their = [e['event_gross_return'] for e in scored]
    ctl_means = [statistics.fmean(e['control_gross_returns']) for e in scored]
    their_mean = statistics.fmean(their)
    owner_net = their_mean - OWNER_COST
    paired_gross = statistics.fmean(t - c for t, c in zip(their, ctl_means))
    paired_owner = paired_gross - OWNER_COST
    paired_orig = paired_gross - ORIG_COST
    rp = result['primary']
    for name, mine, theirs in [('mean_event_gross_return', their_mean, rp['mean_event_gross_return']),
                               ('owner mean_event_net_return', owner_net, rp['owner_cost']['mean_event_net_return']),
                               ('owner mean_paired_net_excess', paired_owner, rp['owner_cost']['mean_paired_net_excess']),
                               ('original-cost mean_paired_net_excess', paired_orig, rp['original_cost']['mean_paired_net_excess']),
                               ('mean_control_gross_return', statistics.fmean(ctl_means), rp['mean_control_gross_return'])]:
        if abs(mine - theirs) > 1e-12:
            discrepancies.append(f'RESULT.json {name}: recomputed {mine} vs serialized {theirs}')
    if len(scored) != rp['n']:
        discrepancies.append(f"RESULT.json n={rp['n']} but EVENTS.json has {len(scored)} SCORED rows")

    # duplicate event identity / duplicate (ticker, date) checks
    ids = [e['event_id'] for e in scored]
    if len(ids) != len(set(ids)):
        discrepancies.append('duplicate event_id among SCORED rows')
    sym_counts = {}
    for e in scored:
        sym_counts.setdefault(e['symbol'], []).append(e['notice_at'])
    repeated_symbols = {s: v for s, v in sym_counts.items() if len(v) > 1}

    # controls supplementary summary
    all_ctl = [c for r in per_event for c in r['controls']]
    ctl_rec = [c for c in all_ctl if c['mine'] is not None]
    ctl_missing = [{'event': r['event_id'], **c} for r in per_event for c in r['controls'] if c['mine'] is None]
    ctl_diff = [c for c in ctl_rec if c['abs_diff'] > 1e-9]

    # events whose target AND all 5 controls are recomputable: paired excess on my data
    full = [r for r in per_event if r['my_gross'] is not None and all(c['mine'] is not None for c in r['controls'])]
    my_paired_full = statistics.fmean(r['my_gross'] - statistics.fmean(c['mine'] for c in r['controls']) for r in full) if full else None

    # ---- check their UNMEASURABLE primary exclusions against my archive ---------
    exclusion_check = []
    for e in events:
        if not e['primary_krw'] or e['status'] not in ('UNMEASURABLE_NO_HISTORICAL_USDT_ARCHIVE', 'UNMEASURABLE_NO_PRE_NOTICE_HOUR'):
            continue
        notice = parse_iso(e['notice_at'])
        nh = notice.replace(minute=0, second=0, microsecond=0)
        pb, pr = bars.bar(e['symbol'], nh - HOUR)
        info = {'event_id': e['event_id'], 'symbol': e['symbol'], 'their_status': e['status'],
                'notice_at': e['notice_at'], 'my_pre_notice_bar': pr}
        if e['symbol'] in bars.have:
            months = sorted(p.name.split('-1h-')[1][:7] for p in Path(k1h).glob(f"{e['symbol']}-1h-*.zip"))
            info['my_first_month'] = months[0]
            first = min(bars.month(e['symbol'], months[0]))
            info['my_first_bar'] = first.isoformat()
        exclusion_check.append(info)
        if pb is not None:
            discrepancies.append(f"{e['event_id']}: Codex status {e['status']} but my archive HAS the pre-notice bar {(nh - HOUR).isoformat()}")

    # ---- Part 2 aggregates -------------------------------------------------------
    pre = summary([r.get('pre_entry_move') for r in per_event])
    hi = summary([r.get('notice_hour_high_move') for r in per_event])
    nclose = summary([r.get('notice_hour_close_move') for r in per_event])
    giveback = summary([(1 + r['pre_entry_move']) / (1 + r['notice_hour_high_move']) - 1
                        for r in per_event if 'pre_entry_move' in r and 'notice_hour_high_move' in r])
    neg_their = sum(1 for x in their if x < 0) / len(their)
    neg_mine = sum(1 for r in rec if r['my_gross'] < 0) / len(rec) if rec else None
    pre_pos = sum(1 for r in per_event if r.get('pre_entry_move', 0) > 0)
    hi_ge10 = sum(1 for r in per_event if r.get('notice_hour_high_move', 0) >= 0.10)
    total_from_prior = summary([(1 + r['pre_entry_move']) * (1 + r['my_gross']) - 1
                                for r in per_event if 'pre_entry_move' in r and r['my_gross'] is not None])

    out_obj = {
        'recomputed_n': len(rec),
        'scored_n': len(scored),
        'max_abs_diff': max((r['abs_diff'] for r in rec), default=None),
        'my_mean_gross': statistics.fmean(r['my_gross'] for r in rec) if rec else None,
        'their_mean_gross_over_same_events': statistics.fmean(r['their_gross'] for r in rec) if rec else None,
        'their_mean_gross': their_mean,
        'owner_net_mean': owner_net,
        'paired_gross_excess_mean': paired_gross,
        'paired_excess_mean_owner_cost': paired_owner,
        'paired_excess_mean_original_cost': paired_orig,
        'max_abs_diff_6h': max((r['abs_diff_6h'] for r in per_event if 'abs_diff_6h' in r), default=None),
        'max_abs_diff_72h': max((r['abs_diff_72h'] for r in per_event if 'abs_diff_72h' in r), default=None),
        'controls': {'total': len(all_ctl), 'recomputed': len(ctl_rec), 'differing': len(ctl_diff),
                     'max_abs_diff': max((c['abs_diff'] for c in ctl_rec), default=None),
                     'missing': ctl_missing,
                     'events_with_target_and_all_controls': len(full),
                     'my_paired_gross_excess_on_those': my_paired_full,
                     'my_paired_owner_excess_on_those': None if my_paired_full is None else my_paired_full - OWNER_COST},
        'post_result_descriptive': {
            'label': 'POST-RESULT DESCRIPTIVE ONLY; not a frozen endpoint, not a tested rule',
            'pre_entry_move_prior_close_to_entry_open': pre,
            'notice_hour_high_vs_prior_close': hi,
            'notice_hour_close_vs_prior_close': nclose,
            'entry_open_vs_notice_hour_high': giveback,
            'prior_close_to_24h_exit_total': total_from_prior,
            'events_with_positive_pre_entry_move': pre_pos,
            'events_with_notice_hour_high_ge_10pct': hi_ge10,
            'share_negative_24h_their': neg_their,
            'share_negative_24h_mine': neg_mine,
        },
        'repeated_symbols_among_scored': repeated_symbols,
        'exclusion_check': exclusion_check,
        'archive_parse_issues': [list(map(str, i)) for i in bars.issues],
        'discrepancies': discrepancies,
        'per_event': per_event,
    }
    out.write_text(json.dumps(out_obj, indent=1, default=str))
    brief = {k: v for k, v in out_obj.items() if k not in ('per_event', 'exclusion_check')}
    print(json.dumps(brief, indent=1, default=str)[:12000])


if __name__ == '__main__':
    main()

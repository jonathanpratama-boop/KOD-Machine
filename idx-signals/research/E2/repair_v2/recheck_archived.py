"""Rejudge every cited filing in the frozen v1 schedule/coverage, without network.

This is an audit of the evidence previously used, not a new exhaustive EDGAR search.
Checks archived payload hashes against committed SEC manifests before parsing any filing.
Writes new immutable v2 schedule/coverage files; the originals are never edited.
Run from idx-signals: python research/E2/repair_v2/recheck_archived.py
"""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from idxsig import us_actions as ua
from idxsig.provenance import sha256_file, utc_stamp

CACHE = ROOT/'data/raw/sec/20261008T091626Z'
SCHEDULE = ROOT/'data/corporate_actions/us_splits-20261008T093909Z.json'
COVERAGE = ROOT/'data/corporate_actions/us_splits-coverage-20261008T094836Z.json'


def main():
    expected = {}
    for pattern in ('sec_split_evidence-20261008T09*.jsonl', 'sec_split_coverage-20261008T09*.jsonl'):
        for manifest in (ROOT/'data/manifests').glob(pattern):
            for line in manifest.read_text().splitlines()[1:]:
                rec = json.loads(line)
                key = hashlib.sha256(rec['url'].encode()).hexdigest()[:32]
                expected[key] = rec['sha256']
    texts, used = {}, {}

    def document(url):
        key = hashlib.sha256(url.encode()).hexdigest()[:32]
        if key not in texts:
            p = CACHE/f'{key}.bin'
            if key not in expected or sha256_file(p) != expected[key]:
                raise RuntimeError(f'Archived filing missing or changed: {url}')
            texts[key] = ua.text_of(p.read_bytes())
            used[url] = expected[key]
        return texts[key]

    stamp = utc_stamp().replace('-', '').replace(':', '')
    audit = {'verifier_version': ua.VERSION, 'scope': 'all previously cited filings; no new SEC search',
             'built_at': utc_stamp(), 'missing_or_changed_filings': 0}
    for source, coverage in ((SCHEDULE, False), (COVERAGE, True)):
        meta = json.loads(source.read_text())
        field = 'rows' if coverage else 'schedule'
        old_path = ROOT/meta[field]
        assert sha256_file(old_path) == meta[field+'_sha256']
        old = pd.read_csv(old_path, keep_default_na=False)
        rows = []
        for i, r in enumerate(old.to_dict('records')):
            if i % 100 == 0:
                print(f'{field}: {i}/{len(old)}', flush=True)
            evidence = json.loads(r['evidence'])
            out = []
            day = date.fromisoformat(r['date'] if coverage else r['effective_session'])
            best = 'NO_SPLIT_EVIDENCE' if coverage else 'NO_EVIDENCE'
            if r['status'] in ('NOT_A_SPLIT', 'NO_CIK', 'JUMP_ON_RECORD_SESSION'):
                best = r['status']
            for ev in evidence:
                text = document(ev['url'])
                if coverage:
                    judgments = [ua.judge(text, n, d, day) for n, d in ev.get('pairs', [])]
                    dated = any(v['date_ok'] for v in judgments)
                    ratio = any(v['ratio_ok'] for v in judgments)
                    found = ('MISSING_PROVIDER_SPLIT' if dated else 'SPLIT_FILING_NEARBY' if ratio
                             else 'NO_SPLIT_EVIDENCE')
                    if dated and r['status'] == 'PROVIDER_DATE_MISMATCH':
                        found = 'PROVIDER_DATE_MISMATCH'
                    rank = ['MISSING_PROVIDER_SPLIT', 'PROVIDER_DATE_MISMATCH', 'SPLIT_FILING_NEARBY', 'NO_SPLIT_EVIDENCE']
                    excerpts = [s for v in judgments for s in v['matched_statements']]
                else:
                    v = ua.judge(text, r['numerator'], r['denominator'], day)
                    found = ('VERIFIED' if v['date_ok'] else 'RATIO_CONFIRMED' if v['ratio_ok']
                             else 'MENTION_ONLY' if v['mentions_split'] else 'NO_EVIDENCE')
                    rank = list(ua.STATUSES)
                    excerpts = v['matched_statements']
                if best in rank and rank.index(found) < rank.index(best):
                    best = found
                out.append({**{k: ev[k] for k in ('accession', 'form', 'file_date', 'url')},
                            'finding': found, 'matched_statements': excerpts[:3], 'verifier_version': ua.VERSION})
            rows.append({**r, 'previous_status': r['status'], 'status': best,
                         'evidence': json.dumps(out, sort_keys=True)})
        checked = pd.DataFrame(rows)
        name = f'us_splits-{"coverage-" if coverage else ""}reaudit-{stamp}'
        path = ROOT/'data/corporate_actions'/f'{name}.csv'
        with path.open('x') as f:
            checked.to_csv(f, index=False, lineterminator='\n')
        new = {**meta, 'version': ua.VERSION, 'built_at': utc_stamp(), field: str(path.relative_to(ROOT)),
               field+'_sha256': sha256_file(path), 'status_counts': checked.status.value_counts().to_dict(),
               'rejudged_from': {'manifest': source.name, 'sha256': sha256_file(source)},
               'evidence_scope': audit['scope']}
        if coverage:
            new['quarantine_tickers'] = sorted(set(checked.loc[checked.status.isin(ua.COVERAGE_QUARANTINE), 'ticker']))
        else:
            new['accepted_statuses'] = list(ua.ACCEPTED)
        mpath = path.with_suffix('.json')
        with mpath.open('x') as f:
            f.write(json.dumps(new, indent=2, sort_keys=True)+'\n')
        audit[field] = {'manifest': str(mpath.relative_to(ROOT)), 'sha256': sha256_file(mpath),
                        'status_counts': new['status_counts'],
                        'transitions': checked.groupby(['previous_status','status']).size().to_dict()}
        audit[field]['transitions'] = {f'{a} -> {b}': n for (a,b),n in audit[field]['transitions'].items()}
        if not coverage:
            accepted = checked.previous_status.isin(('VERIFIED','RATIO_CONFIRMED'))
            audit[field]['previously_accepted'] = int(accepted.sum())
            audit[field]['previously_accepted_now_unverified'] = int((accepted & ~checked.status.isin(ua.ACCEPTED)).sum())
        print(mpath, flush=True)
    audit['filings_checked'] = len(used)
    audit['filing_hashes'] = used
    out = Path(__file__).parent/'evidence_audit.json'
    with out.open('x') as f:
        f.write(json.dumps(audit, indent=2, sort_keys=True)+'\n')
    print(out)


if __name__ == '__main__':
    main()

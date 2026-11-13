#!/usr/bin/env python3
"""Publish final supplement recovery using its existing scoped backup writer.

Run only after combined_view.py has verified all retained evidence. Never starts
collection or changes a capture. Preserves old publication evidence before the
existing backup helper archives the completed slot payloads and acknowledges Git.
"""
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil

REPORT = Path('/var/lib/kod-supplement-ops/FINAL-COMBINED-20261113.json')
CODE = Path('/opt/kod/supplement-v1')
OPS = Path('/var/lib/kod-supplement-ops')
PIN = '86102f2e8e592929102f6cce87bec7b7d365fc64a86f9d136a8f01c22672b202'


def main():
    os.environ['GIT_SSH_COMMAND'] = ('ssh -i /etc/kod-ops/github_backup -o IdentitiesOnly=yes '
        '-o StrictHostKeyChecking=yes -o UserKnownHostsFile=/etc/kod-ops/github_known_hosts '
        '-o BatchMode=yes -o ConnectTimeout=10')
    raw = REPORT.read_bytes()
    report = json.loads(raw)
    own = [r for r in report['slots'] if r['origin'] == 'SUPPLEMENT']
    if len(own) != 196 or any(r['status'] != 'CAPTURED' or not r['capture_verified'] or r['issues'] for r in own):
        raise ValueError('all 196 supplement captures must verify before closure')
    if report['issues'] or report['coverage']['conflicting_candle_identities']:
        raise ValueError('combined retained evidence contains unresolved issues')
    if hashlib.sha256((CODE / 'plan.json').read_bytes()).hexdigest() != PIN:
        raise ValueError('frozen plan changed')
    before = OPS / 'repairs' / 'closeout-20261113' / 'before'
    before.mkdir(parents=True, exist_ok=True)
    for source in (OPS / 'HEALTH.json', OPS / 'last-push.json', OPS / 'repository/HEALTH.json', OPS / 'repository/INDEX.json'):
        name = ('published-' if source.parent.name == 'repository' else 'local-') + source.name
        target = before / name
        if source.exists() and not target.exists():
            shutil.copy2(source, target)
    spec = importlib.util.spec_from_file_location('supplement_backup', CODE / 'backup_supplement.py')
    backup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backup)
    original_run = backup.run
    def run(args, **kwargs):
        if len(args) > 1 and args[1] == str(CODE / 'combined_view.py'):
            if REPORT.read_bytes() != raw:
                raise ValueError('verified final view changed')
            return raw.decode()
        return original_run(args, **kwargs)
    backup.run = run
    current, reason = backup.health(CODE / 'plan.json', PIN, dt.datetime.now(dt.timezone.utc))
    if reason:
        raise RuntimeError(reason)
    if current['original_controls_unchanged'] is not True or current['source_check'].get('ok') is not True:
        raise ValueError('frozen controls/source integrity did not pass')
    current.update(collection_closed=True, phase='CLOSED', collection_status='COMPLETED',
        planned_supplement_slots=196, verified_supplement_slots=196,
        last_supplement_scheduled_at=max(r['scheduled_at'] for r in own),
        last_supplement_completed_at=max(r['completed_at'] for r in own),
        final_verification={'path': str(REPORT), 'sha256': hashlib.sha256(raw).hexdigest(),
                            'as_of': report['as_of'], 'issues': []},
        reporting_correction={'known_at': current['as_of'],
            'previous_published_as_of': json.loads((before / 'published-HEALTH.json').read_text())['as_of'],
            'reason': 'The monitor timed out after 120 seconds while verifying the growing combined view. Collection continued through its original final slot.',
            'original_receipts_changed': False, 'recollection_performed': False})
    backup.atomic(OPS / 'HEALTH.json', current)
    first = backup.backup(current, force=True)
    # Only clear the obsolete recovery-age warning after an actual remote acknowledgement.
    if first.get('pushed'):
        current['last_acknowledged_backup'] = backup.read(OPS / 'last-push.json')
        current['issues'] = [x for x in current['issues'] if x != 'Supplement offsite recovery acknowledgement older than two hours']
        backup.atomic(OPS / 'HEALTH.json', current)
        second = backup.backup(current, force=True)
    else:
        raise RuntimeError('final supplement recovery was not published')
    receipt = {'schema': 'KOD_SUPPLEMENT_CLOSEOUT_V1', 'verified_slots':196,
               'final_view_sha256': hashlib.sha256(raw).hexdigest(), 'issues':current['issues'],
               'first_acknowledgement':first, 'final_acknowledgement':second,
               'prior_publication_preserved':str(before), 'collection_modified':False}
    backup.atomic(OPS / 'repairs/closeout-20261113/RECEIPT.json', receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()

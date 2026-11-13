#!/usr/bin/env python3
"""Refresh source records without touching collection or replacing source clocks."""
from __future__ import annotations
import argparse
import datetime as dt
import fcntl
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile

KOD_URL = 'https://github.com/jonathanpratama-boop/KOD-Machine.git'
BACKUPS_URL = 'https://github.com/jonathanpratama-boop/KOD-Timing-Backups.git'
DATASETS = ('experiments', 'programs', 'summary', 'history', 'runs', 'run_days',
            'server', 'server_history', 'events', 'gaps', 'build')


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('snapshot destination must be regular')
    raw = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n'
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.dashboard-')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def resolve_source_ref(params, default_ref):
    value = params.get('ref')
    if value is None or value == '':
        return default_ref
    if not isinstance(value, str):
        raise ValueError('study ref must be a string')
    return value


def validate_snapshot(data):
    if not isinstance(data, dict):
        raise ValueError('source build must be an object')
    rows = data.get('build')
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise ValueError('source build metadata missing')
    if not rows[0].get('built_at') or not rows[0].get('kod_commit'):
        raise ValueError('source build time and KOD commit required')
    if not isinstance(data.get('experiments'), list) or not data['experiments']:
        raise ValueError('source experiments missing or empty')
    json.dumps(data, allow_nan=False)
    return rows[0]


def refresh_snapshot(build_callable, target_path, status_path, now):
    previous = {}
    try:
        previous = validate_snapshot(json.loads(Path(target_path).read_text()))
    except (OSError, ValueError, TypeError):
        pass
    try:
        data = build_callable()
        build = validate_snapshot(data)
        atomic_json(target_path, data)
        status = {'status': 'CURRENT', 'checked_at': now,
                  'source_built_at': build['built_at'], 'kod_commit': build['kod_commit']}
    except Exception as exc:
        status = {'status': 'STALE', 'checked_at': now, 'error': str(exc),
                  'source_built_at': previous.get('built_at'),
                  'kod_commit': previous.get('kod_commit')}
    atomic_json(status_path, status)
    return status


def render_dashboard(data, template, results, refresh=None):
    if template.count('__KOD_DATA__') != 1:
        raise ValueError('one dashboard data marker required')
    output = dict(data)
    output['cloud_results'] = results
    output['build'] = [dict(row) for row in data['build']]
    output['build'][0]['cloud_refreshed_at'] = results['as_of']
    if refresh is not None:
        output['source_refresh'] = dict(refresh)
    raw = json.dumps(output, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    raw = raw.replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    return template.replace('__KOD_DATA__', raw)


def git(path, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_TERMINAL_PROMPT='0', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
    result = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(path), *args],
                            capture_output=True, text=True, env=env, timeout=180)
    if result.returncode:
        raise RuntimeError('source Git ' + args[0] + ' failed: ' + result.stderr[-600:])
    return result.stdout.strip()


def update_mirror(path, url, shallow=False):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    if not (path / 'HEAD').exists():
        git(path, 'init', '--bare', '.')
        git(path, 'remote', 'add', 'origin', url)
        git(path, 'config', 'remote.origin.promisor', 'true')
        git(path, 'config', 'remote.origin.partialclonefilter', 'blob:none')
    if git(path, 'remote', 'get-url', 'origin') != url:
        raise ValueError('unexpected dashboard source mirror')
    args = ['fetch', '--filter=blob:none', '--prune']
    if shallow:
        args += ['--depth=1']
    git(path, *args, 'origin', '+refs/heads/*:refs/remotes/origin/*')
    remote_head = git(path, 'ls-remote', '--symref', 'origin', 'HEAD')
    lines = [line for line in remote_head.splitlines() if line.startswith('ref: refs/heads/')]
    if len(lines) != 1:
        raise ValueError('cannot identify current default source branch')
    return 'origin/' + lines[0].split()[1][len('refs/heads/'):]


def source_manifest(kod, backups, default_ref, registry):
    refs = {resolve_source_ref(entry.get('params', {}), default_ref)
            for entry in registry['experiments']}
    heads, missing = {}, []
    for ref in sorted(refs | {default_ref}):
        try:
            heads[ref] = git(kod, 'rev-parse', '--verify', ref)
        except RuntimeError:
            if ref == default_ref:
                raise
            heads[ref] = None
            missing.append(ref)
    return {'default_ref': default_ref, 'kod_refs': heads, 'missing_study_refs': missing,
            'backups_refs': git(backups, 'for-each-ref', '--format=%(refname:short)=%(objectname)',
                                'refs/remotes/origin/').splitlines(),
            'backup_history_scope': 'current branch heads; historical records remain in GitHub'}


def paper_input_health(report):
    """Retain the published input warning independently of corrected results."""
    result = {'status': None, 'message': None, 'assessed_at': None}
    section = re.search(r'^## US forecast input health\s*\n(.*?)(?=^## |^Generated |\Z)',
                        report, re.MULTILINE | re.DOTALL)
    if not section:
        return result
    banner = re.search(r'^\*\*([A-Z][A-Z0-9_]*) — (.+)\*\*$', section[1], re.MULTILINE)
    if banner:
        result['status'], result['message'] = banner.groups()
    assessed = re.search(r'^- Assessed ([^;\s]+);', section[1], re.MULTILINE)
    if assessed:
        result['assessed_at'] = assessed[1]
    return result


def paper_book_views(report, source):
    """Copy only the three published disclosure views; never recalculate returns."""
    rows = []
    for line in report.splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) == 7 and cells[0] in ('KOD', 'ALL', 'AVOIDED', 'OWNER') and cells[1] in ('As frozen', 'Known at the time', 'Corrected'):
            rows.append(cells)
    expected = {(book, view) for book in ('KOD', 'ALL', 'AVOIDED', 'OWNER')
                for view in ('As frozen', 'Known at the time', 'Corrected')}
    complete = len(rows) == 12 and {(r[0], r[1]) for r in rows} == expected
    generated = next((line.split()[1].rstrip('.') for line in report.splitlines()
                      if line.startswith('Generated ')), None)
    unresolved_match = re.search(r'(\d+) are unresolved and stay in every view', report)
    return {'status': 'PUBLISHED' if complete else 'NOT_PUBLISHED', 'source': source,
            'report_generated_at': generated, 'input_health': paper_input_health(report),
            'unresolved_count': int(unresolved_match.group(1)) if unresolved_match else None,
            'columns': ['Book', 'View', 'Positions', 'Closed', 'Wins', 'P&L', 'Average trade'],
            'rows': rows if complete else [],
            'note': 'Corrected uses later evidence. The original verdict and trading records are unchanged.'}


def build_from_mirrors(code_root, state_root, now):
    code_root, state_root = Path(code_root), Path(state_root)
    kod, backups = state_root / 'kod.git', state_root / 'backups.git'
    default_ref = update_mirror(kod, KOD_URL)
    update_mirror(backups, BACKUPS_URL, shallow=True)
    registry_path = code_root / 'tools/status/experiments.json'
    registry = json.loads(registry_path.read_text())
    manifest = source_manifest(kod, backups, default_ref, registry)
    with tempfile.TemporaryDirectory(dir=state_root, prefix='build-') as folder:
        result = subprocess.run(['python3', '-B', str(code_root / 'tools/status/build_status.py'),
            '--kod', str(kod), '--kod-ref', default_ref, '--backups', str(backups),
            '--registry', str(registry_path), '--out', folder, '--now', now],
            capture_output=True, text=True, timeout=900)
        if result.returncode:
            raise RuntimeError('dashboard builder failed: ' + (result.stderr or result.stdout)[-1000:])
        data = {name: json.loads((Path(folder) / (name + '.json')).read_text()) for name in DATASETS}
    report_path = 'idx-signals/paper/PAPER_BOOK.md'
    try:
        report = git(kod, 'show', default_ref + ':' + report_path)
        data['paper_book_views'] = paper_book_views(report, 'KOD@' + manifest['kod_refs'][default_ref] + ':' + report_path)
    except RuntimeError as exc:
        data['paper_book_views'] = {'status':'UNAVAILABLE', 'source':report_path, 'error':str(exc), 'rows':[]}
    data['build'][0]['source_manifest'] = manifest
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-root', required=True, type=Path)
    parser.add_argument('--state-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--status', required=True, type=Path)
    parser.add_argument('--interval-seconds', type=int, default=3600)
    args = parser.parse_args(argv)
    args.state_root.mkdir(parents=True, exist_ok=True)
    with (args.state_root / 'refresh.lock').open('a+b') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({'status': 'BUSY'}))
            return 0
        now = stamp()
        try:
            previous = json.loads(args.status.read_text())
            last = dt.datetime.fromisoformat(previous['checked_at'].replace('Z', '+00:00'))
            elapsed = (dt.datetime.now(dt.timezone.utc) - last).total_seconds()
            if previous['status'] == 'CURRENT' and 0 <= elapsed < args.interval_seconds:
                print(json.dumps(previous))
                return 0
        except (OSError, ValueError, KeyError, TypeError):
            pass
        result = refresh_snapshot(lambda: build_from_mirrors(args.code_root, args.state_root, now),
                                  args.output, args.status, now)
        print(json.dumps(result, sort_keys=True))
        return 0 if result['status'] == 'CURRENT' else 1


if __name__ == '__main__':
    raise SystemExit(main())

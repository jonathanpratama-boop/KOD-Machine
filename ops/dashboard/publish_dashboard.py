"""Publish two dashboard files through the existing private backup identity.

Called after the existing backup job. It reads the live research database and
never starts/stops collection, requests market data, or changes research rows.
"""
import datetime as dt
from contextlib import ExitStack
import fcntl
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), '/opt/kod/research-r2']
# The exporter is deployed beside this file; the frozen runtime lives separately.
export_results = importlib.import_module('export_results').export_results
SSH_COMMAND = importlib.import_module('research_r2.capture_service').SSH_COMMAND
GIT_SCOPED_OPTIONS = importlib.import_module('research_r2.capture_ops').GIT_SCOPED_OPTIONS
IncrementalBackup = importlib.import_module('broad_observer.backup').IncrementalBackup
render_dashboard = importlib.import_module('refresh_dashboard').render_dashboard

STATE = Path('/var/lib/kod/research-r2')
OPERATIONS = Path('/var/lib/kod-research-r2-ops')
BRANCH = 'research-r2-20261105T181200Z'
REMOTE = 'git@github.com:jonathanpratama-boop/KOD-Timing-Backups.git'
FILES = ('DASHBOARD.html', 'DASHBOARD_RESULTS.json')



def render(data, template, results, refresh=None):
    return render_dashboard(data, template, results, refresh)


def publish():
    repository = OPERATIONS/'repository'
    env = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_SSH_COMMAND=SSH_COMMAND, GIT_TERMINAL_PROMPT='0',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1')
    def git(*args, accepted=(0,)):
        p = subprocess.run(['git',*GIT_SCOPED_OPTIONS,'-C',str(repository),*args],
            capture_output=True, text=True, env=env, timeout=90)
        if p.returncode not in accepted:
            raise RuntimeError('Dashboard Git operation failed: '+args[0])
        return p
    # Same outer lock as the existing operations worker; no competing Git index.
    with ExitStack() as stack:
        lock = stack.enter_context((OPERATIONS/'health-backup.lock').open('a+b'))
        try:
            fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return {'status':'DEFERRED_BACKUP_BUSY'}
        stack.enter_context(IncrementalBackup(repository).lock())
        if git('symbolic-ref','--short','HEAD').stdout.strip() != BRANCH:
            raise ValueError('Unexpected backup branch')
        if git('remote','get-url','origin').stdout.strip() != REMOTE:
            raise ValueError('Unexpected backup destination')
        if git('diff','--cached','--name-only').stdout.strip():
            raise ValueError('Unrelated staged files; dashboard publication deferred')
        base = git('rev-parse','HEAD').stdout.strip()
        remote = git('ls-remote','--heads','origin','refs/heads/'+BRANCH).stdout.split()
        if not remote or remote[0] != base:
            return {'status':'DEFERRED_PENDING_BACKUP','reason':'Wait for the regular backup to publish its current head.'}
        results = export_results(STATE)
        data = json.loads((HERE/'dashboard_data.json').read_text())
        refresh_path = HERE/'SOURCE_REFRESH.json'
        refresh = json.loads(refresh_path.read_text()) if refresh_path.exists() else {
            'status':'STALE', 'error':'Source refresh status is missing',
            'source_built_at':data['build'][0].get('built_at')}
        signature = hashlib.sha256(json.dumps({
            'cloud':{k:results.get(k) for k in ('events','prospective_check','arms','status')},
            'source_sha256':hashlib.sha256((HERE/'dashboard_data.json').read_bytes()).hexdigest(),
            'source_refresh':refresh,
        },sort_keys=True).encode()).hexdigest()
        previous_path = HERE/'PUBLISH_HEALTH.json'
        previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
        if previous.get('signature') == signature and previous.get('as_of'):
            elapsed = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(previous['as_of'].replace('Z','+00:00'))).total_seconds()
            if 0 <= elapsed < 900:
                return dict(previous,status='UNCHANGED')
        html = render(data, (HERE/'one_page.html').read_text(), results, refresh)
        payloads = {'DASHBOARD.html':html,
                    'DASHBOARD_RESULTS.json':json.dumps(results,indent=2,sort_keys=True,allow_nan=False)+'\n'}
        for name, content in payloads.items():
            target = repository/name
            if target.is_symlink():
                raise ValueError('Dashboard destination must be regular')
            temp = repository/(name+'.tmp')
            temp.write_text(content)
            os.replace(temp,target)
        try:
            git('add','--',*FILES)
            staged = set(git('diff','--cached','--name-only').stdout.splitlines())
            if staged - set(FILES):
                raise ValueError('Unexpected staged dashboard paths')
            if staged:
                git('-c','user.name=KOD research dashboard','-c','user.email=kod-research@localhost',
                    'commit','-m','Refresh recorded study comparisons')
        finally:
            # A failed dashboard commit must not leave unrelated index entries
            # that would prevent the regular scoped backup from publishing.
            git('reset','-q','HEAD','--',*FILES)
        commit = git('rev-parse','HEAD').stdout.strip()
        remote = git('ls-remote','--heads','origin','refs/heads/'+BRANCH).stdout.split()
        if remote and git('merge-base','--is-ancestor',remote[0],commit,accepted=(0,1,128)).returncode:
            raise ValueError('Remote backup changed; no force publication')
        git('push','--no-verify','origin','HEAD:refs/heads/'+BRANCH)
        remote = git('ls-remote','--heads','origin','refs/heads/'+BRANCH).stdout.split()
        if not remote or remote[0] != commit:
            raise ValueError('Dashboard acknowledgement differs')
        return {'status':'PUBLISHED','commit':commit,'as_of':results['as_of'],
                'branch':BRANCH,'files':list(FILES),'signature':signature}


if __name__ == '__main__':
    try:
        report = publish()
    except Exception as exc:
        report = {'status':'FAILED','reason':str(exc),'checked_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    temp = HERE/'PUBLISH_HEALTH.tmp'
    temp.write_text(json.dumps(report,sort_keys=True)+'\n')
    os.replace(temp,HERE/'PUBLISH_HEALTH.json')
    print(json.dumps(report,sort_keys=True))
    raise SystemExit(1 if report['status']=='FAILED' else 0)

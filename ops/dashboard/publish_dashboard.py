"""Publish dashboard summaries through the existing private backup identity.

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
FILES = ('DASHBOARD.html', 'DASHBOARD_RESULTS.json', 'GUIDANCE_MARGIN_STATUS.json')
GUIDANCE_STATE = Path('/var/lib/kod/guidance-margin/STATUS.json')




def guidance_public_status(path):
    """Publish summary fields only; source bodies, model payloads and secrets stay private."""
    fallback = {'schema': 'guidance-margin-status/v1', 'state': 'UNAVAILABLE',
                'as_of': None, 'trial': {}, 'feed': {}, 'credits': {}}
    try:
        raw = json.loads(Path(path).read_text())
        if not isinstance(raw, dict):
            raise ValueError('not an object')
        json.dumps(raw, allow_nan=False)
    except FileNotFoundError:
        return dict(fallback, reason='The guidance runner has not published a status yet.')
    except (OSError, ValueError, TypeError):
        return dict(fallback, reason='The guidance status could not be read.')

    def fields(value, keys):
        if not isinstance(value, dict):
            return {}
        return {key: value[key] for key in keys if key in value
                and (value[key] is None or isinstance(value[key], (str, int, float, bool)))}

    output = fields(raw, ('as_of', 'state', 'started_at', 'reason'))
    output['schema'] = 'guidance-margin-status/v1'
    trial = raw.get('trial', {})
    output['trial'] = fields(trial, ('started_at', 'last_record_at', 'status', 'candidates',
        'admitted', 'informative_admissions', 'excluded', 'filled_pairs', 'closed_pairs', 'missed_entries', 'missing_terminal_outcomes',
        'conclusion', 'real_trade_permission'))
    output['trial']['policy'] = fields(trial.get('policy', {}) if isinstance(trial, dict) else {},
        ('capital_per_arm_usd', 'slot_usd', 'max_positions', 'entry_time_et',
         'hold_sessions', 'cost_per_side_fraction'))
    output['trial']['modeled_net_pnl_usd'] = fields(
        trial.get('modeled_net_pnl_usd', {}) if isinstance(trial, dict) else {},
        ('revenue', 'revenue_and_margin'))
    horizons = trial.get('horizons', {}) if isinstance(trial, dict) else {}
    output['trial']['horizons'] = {}
    for horizon in ('1', '3', '5', '20'):
        value = horizons.get(horizon, {}) if isinstance(horizons, dict) else {}
        output['trial']['horizons'][horizon] = fields(value, ('paired_events',))
        output['trial']['horizons'][horizon]['net_pnl_usd'] = fields(
            value.get('net_pnl_usd', {}) if isinstance(value, dict) else {},
            ('revenue', 'revenue_and_margin'))
    output['trial']['cohorts'] = {}
    cohorts = trial.get('cohorts', {}) if isinstance(trial, dict) else {}
    for name in ('NEW_RELEASE', 'INITIAL_RECENT'):
        cohort = cohorts.get(name) if isinstance(cohorts, dict) else None
        if not isinstance(cohort, dict):
            continue
        public = fields(cohort, ('admitted', 'filled_pairs'))
        public['horizons'] = {}
        cohort_horizons = cohort.get('horizons', {})
        for day in ('1', '3', '5', '20'):
            row = cohort_horizons.get(day, {}) if isinstance(cohort_horizons, dict) else {}
            public['horizons'][day] = fields(row, ('paired_events',))
            public['horizons'][day]['net_pnl_usd'] = fields(
                row.get('net_pnl_usd', {}) if isinstance(row, dict) else {},
                ('revenue', 'revenue_and_margin'))
        output['trial']['cohorts'][name] = public
    output['feed'] = fields(raw.get('feed', {}), ('as_of', 'status', 'started_at', 'last_success_at',
        'discovered', 'retained', 'screened', 'reviewed', 'queued', 'excluded', 'pending_review',
        'candidates', 'eligible', 'errors', 'coverage', 'source', 'model', 'api_calls',
        'estimated_cost_usd', 'credit_expires_at', 'updated_at', 'state', 'source_scope',
        'discovered_count', 'prospective_count', 'development_count', 'screened_out_count',
        'extraction_attempted_count', 'candidate_count', 'review_pending_count', 'review_closed_count', 'excluded_count',
        'fetch_error_count', 'api_estimated_usd', 'credit_expiry_at', 'credit_budget_usd',
        'api_remaining_estimate_usd', 'live_api_calls', 'replay_api_calls', 'replay_api_estimated_usd'))
    feed = raw.get('feed', {})
    pending = feed.get('pending_reviews') if isinstance(feed, dict) else None
    if isinstance(pending, list):
        public_reasons = {
            'IDENTITY_UNKNOWN': 'Confirm the issuer and its US listing.',
            'MISSING_PRIOR': 'Find an earlier forecast for the same fiscal year and accounting basis.',
            'INCOMPLETE_INVENTORY': 'Check the remaining earlier releases from this issuer.',
            'EXTRACTION_REJECTED': 'Verify the extracted figures against the release.',
            'REVIEW_PENDING': 'Check the source comparison.',
        }
        output['feed']['pending_reviews'] = [
            {'title': row['title'], 'status': row['status'], 'reason': public_reasons[row['status']]}
            for row in pending if isinstance(row, dict) and isinstance(row.get('title'), str)
            and isinstance(row.get('status'), str) and row['status'] in public_reasons
        ]
    output['credits'] = fields(raw.get('credits', {}), ('estimated_spend_usd', 'estimated_cost_usd',
        'available_usd', 'budget_usd', 'remaining_estimate_usd', 'expires_at', 'calls', 'status'))
    replay_path = Path(path).with_name('HISTORICAL_REPLAY_SUMMARY.json')
    if replay_path.is_file():
        try:
            replay = json.loads(replay_path.read_text())
            cohorts = {}
            for name in ('pilot', 'expansion'):
                if name not in replay:
                    continue
                subset = replay[name]
                public = fields(subset, ('release_count', 'issuer_count', 'revenue_signals', 'margin_signals'))
                public['primary'] = fields(subset['horizons']['20'], ('scored_pairs', 'informative_pairs',
                                         'unavailable', 'revenue_usd', 'margin_usd', 'difference_usd'))
                cohorts[name] = public
            output['historical_replay'] = cohorts
        except (OSError, ValueError, KeyError, TypeError):
            output['historical_replay'] = {'state': 'UNAVAILABLE'}
    return output


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
        guidance = guidance_public_status(GUIDANCE_STATE)
        data['guidance_margin'] = guidance
        signature = hashlib.sha256(json.dumps({
            'cloud':{k:results.get(k) for k in ('events','prospective_check','arms','status')},
            'source_sha256':hashlib.sha256((HERE/'dashboard_data.json').read_bytes()).hexdigest(),
            'template_sha256':hashlib.sha256((HERE/'one_page.html').read_bytes()).hexdigest(),
            'source_refresh':refresh,
            'guidance_margin':guidance,
        },sort_keys=True).encode()).hexdigest()
        previous_path = HERE/'PUBLISH_HEALTH.json'
        previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
        if previous.get('signature') == signature and previous.get('as_of'):
            elapsed = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(previous['as_of'].replace('Z','+00:00'))).total_seconds()
            if 0 <= elapsed < 900:
                return dict(previous,status='UNCHANGED')
        html = render(data, (HERE/'one_page.html').read_text(), results, refresh)
        payloads = {'DASHBOARD.html':html,
                    'DASHBOARD_RESULTS.json':json.dumps(results,indent=2,sort_keys=True,allow_nan=False)+'\n',
                    'GUIDANCE_MARGIN_STATUS.json':json.dumps(guidance,indent=2,sort_keys=True,allow_nan=False)+'\n'}
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

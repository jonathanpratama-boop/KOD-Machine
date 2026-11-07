"""Exercise publication against a local bare Git remote; no network or cloud."""
import contextlib
import datetime as dt
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


def load_publisher():
    service = types.ModuleType('research_r2.capture_service')
    service.SSH_COMMAND = 'false'
    operations = types.ModuleType('research_r2.capture_ops')
    operations.GIT_SCOPED_OPTIONS = ('-c', 'protocol.file.allow=always',
                                     '-c', 'core.hooksPath=/dev/null')
    backup = types.ModuleType('broad_observer.backup')
    class ExistingBackup:
        def __init__(self, root): self.root = root
        def lock(self): return contextlib.nullcontext()
    backup.IncrementalBackup = ExistingBackup
    location = Path(__file__).with_name('publish_dashboard.py')
    spec = importlib.util.spec_from_file_location('_tested_dashboard_publisher', location)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, {
        'research_r2.capture_service': service,
        'research_r2.capture_ops': operations,
        'broad_observer.backup': backup,
    }):
        spec.loader.exec_module(module)
    return module


publisher = load_publisher()


class DashboardPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.operations = self.root/'operations'; self.operations.mkdir()
        self.repository = self.operations/'repository'; self.repository.mkdir()
        self.remote = self.root/'remote.git'
        self.here = self.root/'publisher'; self.here.mkdir()
        self.branch = 'research-test'
        self.env = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
        self.env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
                        GIT_TERMINAL_PROMPT='0')
        self.command('init', '--bare', '-b', self.branch, str(self.remote), at=self.root)
        self.command('init', '-b', self.branch)
        self.identity(self.repository)
        (self.repository/'HEAD.json').write_text('{"manifest":"original"}\n')
        (self.repository/'unrelated.txt').write_text('original\n')
        self.command('add', '--', 'HEAD.json', 'unrelated.txt')
        self.command('commit', '-m', 'Existing backup')
        self.command('remote', 'add', 'origin', str(self.remote))
        self.command('push', 'origin', self.branch)
        self.original = self.command('rev-parse', 'HEAD').stdout.strip()
        self.head_blob = self.command('rev-parse', 'HEAD:HEAD.json').stdout.strip()
        (self.here/'dashboard_data.json').write_text(json.dumps({'build':[{'built_at':'old'}]}))
        (self.here/'one_page.html').write_text('<html><script id="data">__KOD_DATA__</script></html>')
        self.results = {'schema':'KOD_R2_RESULTS_V1', 'as_of':'2026-11-08T00:00:00Z',
                        'status':'RUNNING', 'events':[], 'arms':[],
                        'comparison_inputs':{'status':'READY'}, 'prospective_check':{'enabled':True}}
        self.patches = mock.patch.multiple(publisher, HERE=self.here,
            STATE=self.root/'unused-read-state', OPERATIONS=self.operations,
            BRANCH=self.branch, REMOTE=str(self.remote))
        self.patches.start()
        self.export = mock.patch.object(publisher, 'export_results', return_value=self.results)
        self.export_mock = self.export.start()

    def tearDown(self):
        self.export.stop(); self.patches.stop(); self.temporary.cleanup()

    def command(self, *args, at=None):
        result = subprocess.run(['git','-c','protocol.file.allow=always',
            '-c','core.hooksPath=/dev/null','-C',str(at or self.repository),*args],
            capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def identity(self, directory):
        self.command('config', 'user.name', 'Fixture', at=directory)
        self.command('config', 'user.email', 'fixture@localhost', at=directory)

    def remote_head(self):
        return self.command('--git-dir='+str(self.remote), 'rev-parse',
                            'refs/heads/'+self.branch, at=self.root).stdout.strip()

    def test_publishes_only_dashboard_files_and_preserves_backup_head(self):
        result = publisher.publish()
        self.assertEqual(result['status'], 'PUBLISHED')
        self.assertEqual(self.remote_head(), result['commit'])
        changed = set(self.command('diff-tree', '--no-commit-id', '--name-only',
                                  '-r', result['commit']).stdout.splitlines())
        self.assertEqual(changed, set(publisher.FILES))
        self.assertEqual(self.command('rev-parse', 'HEAD:HEAD.json').stdout.strip(), self.head_blob)
        self.assertEqual(json.loads((self.repository/'DASHBOARD_RESULTS.json').read_text()), self.results)
        rendered = (self.repository/'DASHBOARD.html').read_text()
        self.assertNotIn('__KOD_DATA__', rendered)
        self.assertIn('KOD_R2_RESULTS_V1', rendered)
        self.assertEqual(self.command('diff', '--cached', '--name-only').stdout, '')

    def test_unrelated_staged_file_is_preserved_and_publication_aborts(self):
        (self.repository/'unrelated.txt').write_text('staged backup change\n')
        self.command('add', '--', 'unrelated.txt')
        before_index = self.command('diff', '--cached').stdout
        original_run = subprocess.run
        calls = []
        def trace(args, **kwargs):
            calls.append(args)
            return original_run(args, **kwargs)
        with mock.patch.object(publisher.subprocess, 'run', side_effect=trace):
            with self.assertRaisesRegex(ValueError, 'staged'):
                publisher.publish()
        self.assertEqual(self.command('diff', '--cached').stdout, before_index)
        self.assertFalse(any('reset' in call or 'restore' in call for call in calls))
        self.assertEqual(self.command('rev-parse', 'HEAD').stdout.strip(), self.original)
        self.assertEqual(self.remote_head(), self.original)
        self.export_mock.assert_not_called()

    def test_failed_commit_cleans_own_index_without_discarding_working_files(self):
        (self.repository/'unrelated.txt').write_text('keep this working change\n')
        original_run = subprocess.run
        def fail_commit(args, **kwargs):
            if 'commit' in args:
                return subprocess.CompletedProcess(args, 1, '', 'simulated commit failure')
            return original_run(args, **kwargs)
        with mock.patch.object(publisher.subprocess, 'run', side_effect=fail_commit):
            with self.assertRaises(RuntimeError):
                publisher.publish()
        self.assertEqual(self.command('diff', '--cached', '--name-only').stdout, '')
        self.assertEqual((self.repository/'unrelated.txt').read_text(), 'keep this working change\n')
        self.assertTrue((self.repository/'DASHBOARD.html').is_file())
        self.assertEqual(self.command('rev-parse', 'HEAD').stdout.strip(), self.original)
        self.assertEqual(self.remote_head(), self.original)

    def test_unpublished_local_backup_defers_before_staging_or_export(self):
        (self.repository/'HEAD.json').write_text('{"manifest":"pending-backup"}\n')
        self.command('add', '--', 'HEAD.json'); self.command('commit', '-m', 'Pending backup')
        local = self.command('rev-parse', 'HEAD').stdout.strip()
        result = publisher.publish()
        self.assertEqual(result['status'], 'DEFERRED_PENDING_BACKUP')
        self.assertEqual(self.command('rev-parse', 'HEAD').stdout.strip(), local)
        self.assertEqual(self.remote_head(), self.original)
        self.assertFalse((self.repository/'DASHBOARD.html').exists())
        self.assertEqual(self.command('diff', '--cached', '--name-only').stdout, '')
        self.export_mock.assert_not_called()

    def test_remote_advance_defers_without_resetting_or_overwriting(self):
        other = self.root/'another-backup-writer'
        self.command('clone', str(self.remote), str(other), at=self.root)
        self.identity(other)
        (other/'HEALTH.json').write_text('{"status":"OK"}\n')
        self.command('add', '--', 'HEALTH.json', at=other)
        self.command('commit', '-m', 'Remote advanced', at=other)
        self.command('push', 'origin', self.branch, at=other)
        remote = self.remote_head()
        result = publisher.publish()
        self.assertEqual(result['status'], 'DEFERRED_PENDING_BACKUP')
        self.assertEqual(self.command('rev-parse', 'HEAD').stdout.strip(), self.original)
        self.assertEqual(self.remote_head(), remote)
        self.assertFalse((self.repository/'DASHBOARD.html').exists())
        self.export_mock.assert_not_called()

    def test_busy_backup_lock_defers_without_git_or_export(self):
        with (self.operations/'health-backup.lock').open('a+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = publisher.publish()
        self.assertEqual(result['status'], 'DEFERRED_BACKUP_BUSY')
        self.export_mock.assert_not_called()
        self.assertEqual(self.remote_head(), self.original)

    def test_unchanged_results_do_not_create_another_commit_within_fifteen_minutes(self):
        self.results['as_of'] = dt.datetime.now(dt.timezone.utc).isoformat()
        first = publisher.publish()
        (self.here/'PUBLISH_HEALTH.json').write_text(json.dumps(first))
        result = publisher.publish()
        self.assertEqual(result['status'], 'UNCHANGED')
        self.assertEqual(self.command('rev-parse', 'HEAD').stdout.strip(), first['commit'])
        self.assertEqual(self.remote_head(), first['commit'])
        self.assertEqual(self.command('diff', '--cached', '--name-only').stdout, '')

    def test_new_event_bypasses_the_unchanged_result_throttle(self):
        self.results['as_of'] = dt.datetime.now(dt.timezone.utc).isoformat()
        first = publisher.publish()
        (self.here/'PUBLISH_HEALTH.json').write_text(json.dumps(first))
        self.results['events'] = [{'event_id':'new-recorded-signal'}]
        result = publisher.publish()
        self.assertEqual(result['status'], 'PUBLISHED')
        self.assertNotEqual(result['commit'], first['commit'])
        self.assertEqual(self.remote_head(), result['commit'])
        self.assertEqual(self.command('rev-parse', 'HEAD:HEAD.json').stdout.strip(), self.head_blob)


if __name__ == '__main__': unittest.main()

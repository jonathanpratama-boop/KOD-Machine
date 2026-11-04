import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('ci_scope', ROOT / 'tools/ci_scope.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)
A, B = 'a' * 40, 'b' * 40


def event(ref='refs/heads/main'):
    return {'repository': {'full_name': 'owner/repo', 'default_branch': 'main'},
            'before': A, 'after': B, 'ref': ref}


def run(sha=B, event='pull_request', **kw):
    return dict(id=12, head_sha=sha, event=event, path=ci.WORKFLOW,
                status=kw.get('status', 'completed'), conclusion=kw.get('conclusion', 'success'))


def api(prs=(), pushes=(), jobs=None):
    def get(path):
        if '/jobs?' in path:
            return {'jobs': jobs if jobs is not None else [
                {'name': name, 'conclusion': 'success'}
                for name in ('code-tests', 'workstation')]}
        return {'workflow_runs': list(prs if 'event=pull_request' in path else pushes)}
    return get


class ScopeTests(unittest.TestCase):
    def decide(self, data=None, get=None, changes=None, name='push'):
        return ci.decide(name, data or event(), get or api(),
                         lambda a,b: changes if changes is not None else [('M', 'idx-signals/idxsig/cli.py')])[0]

    def test_pr_always_full(self):
        self.assertTrue(self.decide(name='pull_request', get=lambda p: self.fail('no API needed')))

    def test_other_event_full(self):
        self.assertTrue(self.decide(name='workflow_dispatch'))

    def test_topic_push_skips_suites_without_api(self):
        self.assertFalse(self.decide(data=event('refs/heads/topic'),get=lambda p:self.fail('no API needed')))

    def test_topic_push_still_full_on_pr(self):
        self.assertTrue(self.decide(data=event('refs/heads/topic'),name='pull_request'))

    def test_topic_push_can_request_manual_full_tests(self):
        self.assertTrue(self.decide(data=event('refs/heads/topic'),name='workflow_dispatch'))

    def test_default_code_push_runs(self):
        self.assertTrue(self.decide())

    def test_tag_always_full(self):
        self.assertTrue(self.decide(data=event('refs/tags/v1')))

    def test_forecast_with_verified_parent_can_skip(self):
        for path in ci.FORECAST_LOGS:
            with self.subTest(path=path):
                self.assertFalse(self.decide(changes=[('M',path)],get=api(pushes=[run(A,'push')])))

    def test_forecast_without_baseline_runs(self):
        self.assertTrue(self.decide(changes=[('M',next(iter(ci.FORECAST_LOGS)))]))

    def test_forecast_parent_skipped_suites_not_baseline(self):
        self.assertTrue(self.decide(changes=[('M',next(iter(ci.FORECAST_LOGS)))],
                                   get=api(pushes=[run(A,'push')],jobs=[])))

    def test_forecast_deletion_runs(self):
        self.assertTrue(self.decide(changes=[('D',next(iter(ci.FORECAST_LOGS)))],
                                   get=api(pushes=[run(A,'push')])))

    def test_unknown_and_research_paths_run(self):
        for path in ('docs/README.md','idx-signals/research/x/protocol.md',
                     'idx-signals/data/x.csv','idx-signals/paper/new.jsonl',
                     'kod-machine/registry/cards/new.json','.github/workflows/checks.yml',
                     'idx-signals/tests/fixture.json','idx-signals/paper/code.py'):
            with self.subTest(path=path):
                self.assertTrue(self.decide(changes=[('M',path)],get=api(pushes=[run(A,'push')])))

    def test_mixed_code_and_forecast_run(self):
        self.assertTrue(self.decide(changes=[('M',next(iter(ci.FORECAST_LOGS))),('M','tools/foo.py')],
                                   get=api(pushes=[run(A,'push')])))

    def test_empty_diff_runs(self):
        self.assertTrue(self.decide(changes=[],get=api(pushes=[run(A,'push')])))

    def test_api_error_runs(self):
        def fail(path): raise TimeoutError('secret must not be logged')
        selected,reason=ci.decide('push',event(),fail,lambda a,b: [('M',next(iter(ci.FORECAST_LOGS)))])
        self.assertTrue(selected)
        self.assertNotIn('secret',reason)

    def test_malformed_api_runs(self):
        self.assertTrue(self.decide(get=lambda p: {},changes=[('M',next(iter(ci.FORECAST_LOGS)))]))

    def test_wrong_parent_sha_or_workflow_runs(self):
        for field,value in (('head_sha',B),('path','.github/workflows/other.yml'),('event','pull_request')):
            r=run(A,'push')
            r[field]=value
            with self.subTest(field=field):
                self.assertTrue(self.decide(get=api(pushes=[r]),changes=[('M',next(iter(ci.FORECAST_LOGS)))]))

    def test_unsuccessful_parent_runs(self):
        for result in ('failure','cancelled','skipped','neutral','timed_out'):
            with self.subTest(result=result):
                self.assertTrue(self.decide(get=api(pushes=[run(A,'push',conclusion=result)]),changes=[('M',next(iter(ci.FORECAST_LOGS)))]))

    def test_pending_parent_runs(self):
        self.assertTrue(self.decide(get=api(pushes=[run(A,'push',status='in_progress',conclusion=None)]),changes=[('M',next(iter(ci.FORECAST_LOGS)))]))

    def test_malformed_jobs_runs(self):
        self.assertTrue(self.decide(get=api(pushes=[run(A,'push')],jobs=[{}]),changes=[('M',next(iter(ci.FORECAST_LOGS)))]))

    def test_forecast_tag_runs(self):
        self.assertTrue(self.decide(data=event('refs/tags/v1'),get=api(pushes=[run(A,'push')]),changes=[('M',next(iter(ci.FORECAST_LOGS)))]))

    def test_invalid_head_runs(self):
        e=event()
        e['after']='not-a-sha'
        self.assertTrue(self.decide(data=e))

    def test_invalid_repository_runs_without_api(self):
        e=event()
        e['repository']['full_name']='../evil'
        self.assertTrue(self.decide(data=e,get=lambda p:self.fail('invalid repository used')))

    def test_diff_error_runs(self):
        def fail(a,b): raise subprocess.CalledProcessError(1,['git'])
        self.assertTrue(ci.decide('push',event(),api(),fail)[0])

    def test_output_fails_open_on_bad_event(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            (p/'event').write_text('{')
            with patch.dict(os.environ,{'GITHUB_EVENT_PATH':str(p/'event'),'GITHUB_OUTPUT':str(p/'output')}):
                ci.main()
            self.assertEqual((p/'output').read_text(),'run-tests=true\n')

    def test_forecast_allowlist_is_append_only_protected(self):
        spec=importlib.util.spec_from_file_location('append_only',ROOT/'tools/check_append_only.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(ci.FORECAST_LOGS <= set(module.APPEND_ONLY))


class GitDiffTests(unittest.TestCase):
    def test_multi_commit_and_rename_detection(self):
        with tempfile.TemporaryDirectory() as td:
            def git(*args): return subprocess.check_output(['git','-C',td,*args],stderr=subprocess.DEVNULL).decode().strip()
            git('init')
            git('config','user.name','Test')
            git('config','user.email','test@local')
            p=Path(td)
            (p/'start').write_text('one')
            git('add','.')
            git('commit','-m','start')
            before=git('rev-parse','HEAD')
            (p/'code.py').write_text('x=1')
            git('add','.')
            git('commit','-m','code')
            (p/'start').rename(p/'renamed')
            git('add','-A')
            git('commit','-m','rename')
            after=git('rev-parse','HEAD')
            old=os.getcwd()
            try:
                os.chdir(td)
                changes=ci.changed_files(before,after)
                self.assertIn(('A','code.py'),changes)
                self.assertIn(('D','start'),changes)
                self.assertIn(('A','renamed'),changes)
                with self.assertRaises(subprocess.CalledProcessError):
                    ci.changed_files(after,before)
                with self.assertRaises(ValueError):
                    ci.changed_files('0'*40,after)
            finally:
                os.chdir(old)


if __name__ == '__main__':
    unittest.main()

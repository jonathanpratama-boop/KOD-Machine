import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from read_status import read_status

T = datetime(2026, 10, 31, 19, 2, 34, tzinfo=timezone.utc)


class Status(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name)
        self.write('protocol.json', {'pairs':['BTCUSDT','ETHUSDT','BEAMXUSDT'], 'sample_sets':60,
                                     'interval_seconds':120, 'request_timeout_seconds':20})
        self.write('status.json', {'state':'RUNNING', 'last_update_utc':T.isoformat()})
        obs = [{'slot':0,'symbol':s,'status':'OBSERVED'} for s in ('BTCUSDT','ETHUSDT','BEAMXUSDT')]
        obs.append({'slot':1,'symbol':'BTCUSDT','status':'FAILED','reason':'connection closed'})
        for file in ('attempts.jsonl','observations.jsonl'):
            (self.path/file).write_text(''.join(json.dumps(r)+'\n' for r in obs))

    def write(self, name, value):
        (self.path/name).write_text(json.dumps(value))

    def test_fresh_running_file_alone_is_unknown(self):
        self.assertEqual(read_status(self.path,now=T)['state'], 'UNKNOWN')

    def test_only_verified_live_process_and_fresh_heartbeat_is_running(self):
        self.assertEqual(read_status(self.path,now=T,process_alive=True)['state'], 'RUNNING')

    def test_midset_death_is_not_running_even_before_heartbeat_expires(self):
        out=read_status(self.path,now=T+timedelta(seconds=1),process_alive=False)
        self.assertEqual(out['state'], 'UNKNOWN')
        self.assertEqual((out['requests_attempted'],out['successful_books'],out['failed_samples'],out['missing_samples']),(4,3,1,176))

    def test_stale_heartbeat_cannot_imply_active(self):
        for alive in (None,False,True):
            self.assertEqual(read_status(self.path,now=T+timedelta(minutes=5),process_alive=alive)['state'], 'STALE')

    def test_explicit_network_termination_is_blocked(self):
        self.write('termination.json', {'kind':'NETWORK_POLICY_BLOCK','runtime_error':'Network access was blocked by policy.',
                                        'observed_at_utc':T.isoformat()})
        out=read_status(self.path,now=T+timedelta(minutes=5),process_alive=False)
        self.assertEqual(out['state'],'BLOCKED');self.assertFalse(out['resume_allowed'])
        self.assertEqual(out['missing_samples'],176)

    def test_unexplained_transport_error_does_not_invent_policy_denial(self):
        self.assertEqual(read_status(self.path,now=T,process_alive=False)['state'],'UNKNOWN')

    def test_known_exit_is_stopped(self):
        self.write('termination.json', {'kind':'PROCESS_EXIT','observed_at_utc':T.isoformat()})
        self.assertEqual(read_status(self.path,now=T)['state'],'STOPPED')

    def test_future_missing_or_naive_heartbeat_is_unknown(self):
        for stamp in (None, 'bad', (T+timedelta(days=1)).isoformat(), T.replace(tzinfo=None).isoformat()):
            self.write('status.json',{'state':'RUNNING','last_update_utc':stamp})
            self.assertEqual(read_status(self.path,now=T,process_alive=True)['state'],'UNKNOWN')

    def test_partial_journal_never_promotes_to_running(self):
        with (self.path/'attempts.jsonl').open('a') as f:f.write('{')
        out=read_status(self.path,now=T,process_alive=True)
        self.assertEqual(out['state'],'UNKNOWN');self.assertTrue(out['warnings'])


if __name__ == '__main__':unittest.main()

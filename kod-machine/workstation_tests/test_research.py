import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from kod.workstation.research import ResearchArchive, ResearchUnavailable


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'evidence'
        shutil.copytree(ResearchArchive().root, self.root)
        self.archive = ResearchArchive(self.root)

    def replace(self, name, value):
        path = self.root / (name + '.json')
        data = json.dumps(value).encode()
        path.write_bytes(data)
        manifest = self.root / 'manifest.json'
        entries = json.loads(manifest.read_text())
        for e in entries:
            if e['id'] == name:
                e['sha256'] = hashlib.sha256(data).hexdigest()
        manifest.write_text(json.dumps(entries))

    def test_catalog_navigation_only(self):
        entries = self.archive.studies()
        self.assertEqual({e['study_id'] for e in entries}, {'sequence', 'e6', 'execution'})
        self.assertTrue(all('population' not in e and 'raw' not in e for e in entries))

    def test_sequence_counts_and_uncertainty_preserved(self):
        s = self.archive.study('sequence')
        c = s['population']['shortlists']['early']['sequence']
        self.assertEqual((c['up_hits'], c['selected'], c['false_alerts_known'], c['censored_selected']), (76,1825,1722,27))
        self.assertEqual(s['population']['shortlists']['early']['summary']['up_hits'], 60)
        ci = s['uncertainty']['early']['sequence_minus_summary']
        self.assertLess(ci['lower95'], 0)
        self.assertGreater(ci['upper95'], 0)
        self.assertIn('not tested', s['execution']['status'])

    def test_e6_stays_failed(self):
        s = self.archive.study('e6')
        self.assertTrue(all(g['passed'] is False for g in s['execution']['gates'].values()))
        self.assertIn('frozen', s['execution']['status'])

    def test_execution_keeps_detection_profit_distinct(self):
        s = self.archive.study('execution')
        r = s['population']['rule_trades']
        self.assertGreater(r['hit_rate'], .5)
        self.assertLess(r['avg_net_return'], 0)
        self.assertEqual(r['liquidated'], 3)
        self.assertIn('unbounded', json.dumps(s))
        json.dumps(s, allow_nan=False)

    def test_asof_gates_capture_not_just_computation(self):
        for name in ('sequence','e6','execution'):
            s = self.archive.study(name, '2026-10-30T17:59:21Z')
            self.assertEqual(s['status'], 'withheld')
            self.assertNotIn('raw', s)
            self.assertNotIn('source', s)
            self.assertNotIn('reproduction', s)
            self.assertEqual(s['population'], {})
            self.assertEqual(s['baselines'], {})
            self.assertEqual(self.archive.study(name,'2026-10-30T17:59:22Z')['status'], 'available')

    def test_asof_after_capture_before_computation_withheld(self):
        raw = self.archive.study('sequence')['raw']
        raw['created_at'] = '2027-01-01T00:00:00Z'
        self.replace('sequence',raw)
        self.assertEqual(self.archive.study('sequence','2026-12-01T00:00:00Z')['status'],'withheld')

    def test_no_writes_or_view_state_leakage(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        s = self.archive.study('sequence')
        s['raw']['test']['tickers'] = 0
        self.assertEqual(self.archive.study('sequence')['raw']['test']['tickers'],359)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})

    def test_missing_artifact(self):
        (self.root/'sequence.json').unlink()
        with self.assertRaises(ResearchUnavailable):self.archive.study('sequence')

    def test_tampered_artifact(self):
        with (self.root/'sequence.json').open('ab') as f:f.write(b' ')
        with self.assertRaises(ResearchUnavailable):self.archive.study('sequence')

    def test_malformed_and_bad_schema(self):
        for value in ([], {}, {'created_at':'invalid'}, {'created_at':'2026-10-30T00:00:00Z','test':[]}):
            self.replace('sequence',value)
            with self.assertRaises(ResearchUnavailable):self.archive.study('sequence')

    def test_inconsistent_denominators(self):
        raw = self.archive.study('sequence')['raw']
        raw['shortlists']['early']['sequence']['false_alerts_known'] = 0
        self.replace('sequence',raw)
        with self.assertRaises(ResearchUnavailable):self.archive.study('sequence')

    def test_traversal_and_unknown(self):
        for name in ('../sequence','/tmp/sequence','sequence.json','unknown','a/b',None):
            with self.assertRaises(ResearchUnavailable):self.archive.study(name)

    def test_bad_cutoff(self):
        for cutoff in ('not a date','2026-10-30', '2026-10-30T00:00:00'):
            with self.assertRaises(ResearchUnavailable):self.archive.study('sequence',cutoff)

    def test_missing_or_duplicate_manifest(self):
        p=self.root/'manifest.json'
        entries=json.loads(p.read_text()); entries.append(entries[0]);p.write_text(json.dumps(entries))
        with self.assertRaises(ResearchUnavailable):self.archive.studies()
        p.unlink()
        with self.assertRaises(ResearchUnavailable):self.archive.studies()

    def test_symlink_escape(self):
        p=self.root/'sequence.json'; outside=Path(self.tmp.name)/'outside.json'
        outside.write_bytes(p.read_bytes());p.unlink();p.symlink_to(outside)
        with self.assertRaises(ResearchUnavailable):self.archive.study('sequence')

    def test_gate_changes_fail_closed(self):
        raw=self.archive.study('e6')['raw'];raw['gates']['P1_pressure']['passed']=True
        self.replace('e6',raw)
        with self.assertRaises(ResearchUnavailable):self.archive.study('e6')

    def test_execution_and_e6_count_bounds(self):
        raw=self.archive.study('execution')['raw'];raw['rule_trades']['scored']=1000
        self.replace('execution',raw)
        with self.assertRaises(ResearchUnavailable):self.archive.study('execution')
        raw=self.archive.study('e6')['raw'];raw['arms']['P1_pressure']['scored']=1000000
        self.replace('e6',raw)
        with self.assertRaises(ResearchUnavailable):self.archive.study('e6')

    def test_required_numeric_fields_fail_closed(self):
        from copy import deepcopy
        originals={name:self.archive.study(name)['raw'] for name in ('sequence','execution')}
        cases=[('sequence',('shortlists','early','sequence','precision_lower_bound')),
               ('sequence',('shortlists','early','summary','precision_upper_bound')),
               ('sequence',('shortlists','early','sequence','episodes_caught')),
               ('sequence',('paired_precision_differences','early','sequence_minus_summary','lower95')),
               ('sequence',('probability_metrics','sequence','log_loss')),
               ('sequence',('calibration','sequence','temperature')),
               ('execution',('rule_trades','avg_net_return')),
               ('execution',('rule_trades','median_net_return')),
               ('execution',('rule_trades','hit_rate')),
               ('execution',('rule_trades','liquidated')),
               ('execution',('random_matched','avg_net_return','random_mean'))]
        for name,path in cases:
            for value in ('DELETE',None,'invalid',float('nan'),float('inf'),True):
                with self.subTest(name=name,path=path,value=value):
                    raw=deepcopy(originals[name]);target=raw
                    for key in path[:-1]:target=target[key]
                    if value=='DELETE':del target[path[-1]]
                    else:target[path[-1]]=value
                    self.replace(name,raw)
                    with self.assertRaises(ResearchUnavailable):self.archive.study(name)

    def test_required_calibration_and_baseline_shapes(self):
        from copy import deepcopy
        original=self.archive.study('sequence')['raw']
        for key in ('calibration','probability_metrics','paired_precision_differences'):
            raw=deepcopy(original);raw[key]={};self.replace('sequence',raw)
            with self.assertRaises(ResearchUnavailable):self.archive.study('sequence')

    def test_invalid_bounds_and_episode_totals(self):
        from copy import deepcopy
        original=self.archive.study('sequence')['raw']
        for key,value in (('precision_lower_bound',.9),('precision_upper_bound',-1),('episodes_caught',999999)):
            raw=deepcopy(original);raw['shortlists']['early']['sequence'][key]=value
            self.replace('sequence',raw)
            with self.assertRaises(ResearchUnavailable):self.archive.study('sequence')

    def test_interval_conclusion_is_derived(self):
        raw=self.archive.study('sequence')['raw']
        raw['paired_precision_differences']['early']['sequence_minus_summary'].update(lower95=.001,upper95=.02)
        self.replace('sequence',raw)
        result=self.archive.study('sequence')
        self.assertIn('excludes zero',result['comparison_note'])
        self.assertNotIn('includes zero',str(result['limitations']))
        raw['paired_precision_differences']['early']['sequence_minus_summary'].update(lower95=.1,upper95=.02)
        self.replace('sequence',raw)
        with self.assertRaises(ResearchUnavailable):self.archive.study('sequence')

    def test_catalog_does_not_disclose_e6_conclusion(self):
        self.assertNotIn('failed',str(self.archive.studies()).lower())
        self.assertNotIn('failed',self.archive.study('e6','2020-01-01T00:00:00Z')['title'].lower())

if __name__ == '__main__':unittest.main()

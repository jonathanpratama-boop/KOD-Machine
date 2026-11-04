import unittest,json,sys
from pathlib import Path
root=Path(__file__).resolve().parent
excluded={'tests.test_corporate_actions.RegistryFiles.test_registry_for_another_panel_is_refused':'Requires committed data/manifests/ca_registry*.json plus hash-matching registry dataset; intentionally not fetched in source-only scope.'}
def flatten(s):
 for t in s:
  if isinstance(t,unittest.TestSuite):yield from flatten(t)
  else:yield t
suite=unittest.defaultTestLoader.discover('tests',top_level_dir='.')
tests=list(flatten(suite));selected=[t for t in tests if t.id() not in excluded]
(root/'selection.json').write_text(json.dumps({'selected':[t.id() for t in selected],'excluded':excluded},indent=2))
r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(selected))
(root/'result.json').write_text(json.dumps({'run':r.testsRun,'failures':[str(t) for t,e in r.failures],'errors':[str(t) for t,e in r.errors],'skipped':r.skipped,'excluded':excluded},indent=2))
sys.exit(not r.wasSuccessful())

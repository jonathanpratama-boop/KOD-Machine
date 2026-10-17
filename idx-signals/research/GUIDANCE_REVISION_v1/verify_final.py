"""Verify the original immutable decision plus an explicitly recorded code repair."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
sys.path.insert(0,str(ROOT.parents[1]))
from idxsig import guidance as g
from idxsig.paper import ledger_lines,verify_chain


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    policy,freeze=g.verify_freeze(ROOT)
    original=json.loads((ROOT/'IMPLEMENTATION_FREEZE.json').read_text())
    revision=json.loads((ROOT/'CALENDAR_FINAL_REPAIR.json').read_text())
    for name,expected in original['files'].items():
        if sha(ROOT/name)!=expected:raise ValueError('Original evidence changed: '+name)
    for path,key in [('idx-signals/idxsig/guidance.py','module_sha256'),('idx-signals/tests/test_guidance_revision.py','tests_sha256')]:
        old=subprocess.run(['git','show',revision['original_commit']+':'+path],cwd=REPO,check=True,capture_output=True).stdout
        if hashlib.sha256(old).hexdigest()!=original[key]:raise ValueError('Original code identity failed')
        if sha(REPO/path)!=revision['corrected_files'][path]:raise ValueError('Corrected code identity failed')
    if sha(ROOT/'verify_final.py')!=revision['verifier_sha256']:raise ValueError('Verifier changed')
    if sha(REPO/'idx-signals/requirements.txt')!=revision['requirements_sha256']:raise ValueError('Dependency constraint changed')
    spec=importlib.util.spec_from_file_location('guidance_first',ROOT/'run_first_decision.py')
    first=importlib.util.module_from_spec(spec);spec.loader.exec_module(first)
    inventory=json.loads((ROOT/'data/inventory.json').read_text())
    for row in inventory['issuers']:first.metadata_check(row,policy,freeze)
    if verify_chain(ROOT/'paper/ledger.jsonl'):raise ValueError('Ledger chain failed')
    rows=ledger_lines(ROOT/'paper/ledger.jsonl')
    result=json.loads((ROOT/'paper/DECISION.json').read_text())
    if len(rows)!=len(policy['universe']) or len({r['id'] for r in rows})!=len(rows):raise ValueError('Missing/duplicate decisions')
    if [r['record_hash'] for r in rows]!=result['record_hashes']:raise ValueError('Decision report/ledger mismatch')
    if any(r['action']!='NO_SIGNAL' or r['filled_exposure_usd']!='0' for r in rows):raise ValueError('Original cash decision changed')
    if g.digest(first.fixture())!=g.digest(json.loads((ROOT/'paper/AMD_FIXTURE.json').read_text())):raise ValueError('Source fixture changed')
    schedule=g.session_schedule('2026-10-17T07:20:00Z','2026-10-16T20:01:00Z',policy)
    if schedule['entry_session']!='2026-10-19' or schedule['time_exit_session']!='2026-11-13':raise ValueError('Corrected schedule differs from policy')
    weekend=g.session_schedule('2026-10-19T14:00:00Z','2026-10-18T20:00:00Z',policy)
    if weekend['entry_session']!='2026-10-20' or weekend['time_exit_session']!='2026-11-16':raise ValueError('Nontrading-boundary schedule failed')
    print(json.dumps({'status':'PASS','checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'original_decisions_preserved':len(rows),'policy_changed':False,'cash_decision_changed':False,
        'calendar_repair_verified':True,'historical_fixture_reproduced':True,'strategy_returns_computed':False},indent=2))


if __name__=='__main__':main()

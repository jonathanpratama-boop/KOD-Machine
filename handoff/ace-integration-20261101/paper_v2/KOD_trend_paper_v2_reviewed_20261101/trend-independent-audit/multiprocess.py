"""Two bounded real OS-process races, pipes only, no network or production files."""
import multiprocessing as mp,sys,tempfile,json,socket
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'trend_core_paper_v2_candidate_20261101'))
from paper_candidate import Ledger,account_view
from fixtures import init,quote,decision,seed_quotes

def worker(path,c,conn):
 try:
  conn.send('ready')
  if not conn.poll(10):raise TimeoutError('release not received')
  if conn.recv()!='go':raise ValueError('bad gate')
  with patch.object(socket,'create_connection',side_effect=AssertionError('network forbidden')),patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden')):
   out=Ledger(path).transact(c)
  conn.send({'status':'ok','fills':len(out['fills'])})
 except Exception as exc:conn.send({'error':repr(exc)});raise
 finally:conn.close()

def run(duplicate):
 ctx=mp.get_context('spawn')
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/'journal';l=Ledger(path);l.transact(init());seed_quotes(l);l.transact(decision());before=len(path.read_bytes().splitlines())
  symbols=['BTCUSDT','BTCUSDT' if duplicate else 'ETHUSDT'];procs=[];conns=[]
  try:
   for sym in symbols:
    a,b=ctx.Pipe();proc=ctx.Process(target=worker,args=(str(path),quote(sym,'2026-02-10T00:01:05Z'),b));proc.start();b.close();procs.append(proc);conns.append(a)
   for conn in conns:
    if not conn.poll(15):raise TimeoutError('ready')
    if conn.recv()!='ready':raise ValueError('not ready')
   for conn in conns:conn.send('go')
   outputs=[]
   for conn in conns:
    if not conn.poll(15):raise TimeoutError('completion')
    outputs.append(conn.recv())
   for proc in procs:
    proc.join(5)
    if proc.exitcode!=0:raise ValueError('child nonzero')
   st=l.state();v=account_view(st,st['clock']);expected=1 if duplicate else 2
   if len(st['fills'])!=expected or len(path.read_bytes().splitlines())!=before+expected:raise ValueError('duplicate/missing commit')
   if v['cash_available']<0 or v['gross_fraction']>1:raise ValueError('cash/exposure bound')
   return {'case':'duplicate fill observation' if duplicate else 'disjoint coin fills','child_exitcodes':[p.exitcode for p in procs],'fills':len(st['fills']),'new_rows':expected,'cash_total':str(v['cash_total']),'reserved':str(v['cash_reserved']),'gross_fraction':str(v['gross_fraction']),'workers':outputs,'replay':'verified'}
  finally:
   for proc in procs:
    if proc.is_alive():proc.terminate()
    proc.join(5)
    if proc.is_alive():proc.kill();proc.join(5)
   for conn in conns:conn.close()
if __name__=='__main__':
 for duplicate in (True,False):print(json.dumps(run(duplicate),sort_keys=True))

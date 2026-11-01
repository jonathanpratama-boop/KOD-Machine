"""Revalidate ONLY existing allowed local archives. No network or return computation."""
import calendar,csv,hashlib,io,json,zipfile
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from daily_adapter import number,sha,SYMBOLS
ALLOW_SHA='dcda45f36489eeb0b914cb8cb7ecf359178d3be386f4ac7abbc001821f72213d'
MANIFEST_SHA='6b5cbe0b8be894a82980cc5110fb7fc4a501b3b7cea3c2e3e66e1c8cc29dd629'
def checked_local(root):
 root=Path(root);allow_raw=(root/'input_allowlist.json').read_bytes()
 if hashlib.sha256(allow_raw).hexdigest()!=ALLOW_SHA:raise ValueError('allowlist changed')
 if hashlib.sha256((root/'original_spot_manifest.jsonl').read_bytes()).hexdigest()!=MANIFEST_SHA:raise ValueError('original source manifest changed')
 objects=json.loads(allow_raw)['objects'];history={s:[] for s in SYMBOLS};seen_keys=set();receipts=[]
 if len(objects)!=220:raise ValueError('exact220 objects required')
 for item in objects:
  key=item['key'];symbols=[s for s in SYMBOLS if f'/{s}/' in key]
  if len(symbols)!=1 or key in seen_keys:raise ValueError('unexpected/duplicate allowed object')
  seen_keys.add(key);symbol=symbols[0];path=(root/'raw'/key).resolve()
  if not path.is_relative_to((root/'raw').resolve()):raise ValueError('path escapes source root')
  raw=path.read_bytes()
  if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('archive integrity failure')
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   member=Path(key).stem+'.csv'
   if z.namelist()!=[member] or z.getinfo(member).file_size>=5000000:raise ValueError('unexpected archive member/size')
   rows=list(csv.reader(io.StringIO(z.read(member).decode('utf-8'))))
  month=Path(key).stem[-7:];yy,mm=map(int,month.split('-'))
  if len(rows)!=calendar.monthrange(yy,mm)[1]-(16 if month=='2017-08' else 0):raise ValueError('monthly coverage mismatch')
  for r in rows:
   if len(r)!=12 or not r[0].isdigit():raise ValueError('source schema mismatch')
   ts=int(r[0]);factor=1000000 if ts>=10**14 else 1000
   if ts%(86400*factor) or int(r[6])!=ts+86400*factor-1:raise ValueError('daily UTC timestamp mismatch')
   day=datetime.fromtimestamp(ts//factor,timezone.utc).date().isoformat()
   if not day.startswith(month):raise ValueError('archive month mismatch')
   op,hi,lo,cl=[number(v,True) for v in r[1:5]];volume=number(r[5]);number(r[7])
   if not lo<=min(op,cl)<=max(op,cl)<=hi or int(r[8])<0:raise ValueError('OHLC/trade sanity')
   history[symbol].append({'day':day,'open':str(op),'close':str(cl),'volume':str(volume)})
  receipts.append({'key':key,'sha256':item['sha256'],'bytes':len(raw),'rows':len(rows)})
 for symbol,rows in history.items():
  rows.sort(key=lambda r:r['day']);days=[r['day'] for r in rows]
  if len(rows)!=3332 or len(set(days))!=3332 or days[0]!='2017-08-17' or days[-1]!='2026-09-30':raise ValueError('history coverage differs')
  if any(date.fromisoformat(b)-date.fromisoformat(a)!=timedelta(days=1) for a,b in zip(days,days[1:])):raise ValueError('missing daily source row')
 if [r['day'] for r in history[SYMBOLS[0]]]!=[r['day'] for r in history[SYMBOLS[1]]]:raise ValueError('asset time axes differ')
 snapshot=sha({'allowlist':ALLOW_SHA,'manifest':MANIFEST_SHA,'objects':receipts})
 return history,{'status':'ALL220_LOCAL_ARCHIVES_REVALIDATED','snapshot_sha256':snapshot,'objects':receipts,'bars_per_asset':3332,'first_day':'2017-08-17','last_day':'2026-09-30','network_requests':0}

"""Independent code-only checks. All prices below are synthetic; no market data IO."""
import sys, json, hashlib
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'backtests'))
import lib
import run_t1_t5 as t1
import run_t2_t3_t4 as t234

out = {}
idx = pd.date_range('2010-01-01', periods=6, tz='UTC')
d = pd.DataFrame({'open':[100,110,121,100,100,100]}, index=idx)
p = pd.Series([1,0,0,0,0,0], index=idx)
r = lib.run_positions(d,p,.0015)
assert np.allclose(r['pos'],[0,1,0,0,0])
assert np.allclose(r['gross'],[0,.1,0,0,0])
assert np.allclose(r['cost'],[0,.0015,.0015,0,0])
out['engine_shift_costs'] = 'PASS: signal close day0 earns open day1 to day2; entry/exit fees on day1/day2'

net = pd.Series([-.6,.1], index=idx[:2])
reported = lib.stats(net)['MaxDD']
eq = np.r_[1,np.cumprod(1+net)]
correct = float(np.min(eq/np.maximum.accumulate(eq)-1))
assert reported == 0 and correct == -.6
out['initial_equity_drawdown'] = {'reported':reported,'correct':correct,'net':list(net)}

rng = np.random.default_rng(471)
idx2 = pd.date_range('2010-01-01',periods=600,tz='UTC')
c = 100*np.exp(np.cumsum(rng.normal(.001,.025,600)))
d2 = pd.DataFrame({'open':c*.999,'close':c,'high':c*1.03,'low':c*.97}, index=idx2)
variants={
 'donchian':lambda d:t1.donchian_positions(d),
 'tsmom':lambda d:t1.tsmom_positions(d),
 'sma10_40':lambda d:t1.sma_cross_positions(d),
 'sma200':lambda d:t1.sma_filter_positions(d),
 'atr_trail':lambda d:t1.donchian_positions(d,exit_mode='atr_trail'),
 'fixed_stop':lambda d:t1.donchian_positions(d,exit_mode='fixed_stop_plus_channel'),
 'time_exit':lambda d:t1.donchian_positions(d,exit_mode='time')}
for name,fn in variants.items():
 assert fn(d2).iloc[:400].equals(fn(d2.iloc[:400])),name
assert (t1.sma_cross_positions(d2).iloc[:39] == 0).all()
assert (t1.sma_filter_positions(d2).iloc[:199] == 0).all()
out['t1_t5_prefix_causality']={'pass':list(variants),'warmup':'SMA40 first39 and SMA200 first199 flat'}

idx3=pd.date_range('2010-01-01',periods=110,tz='UTC')
fixture={}
for i in range(20):
 cc=100*np.exp(np.arange(110)*(.0005+.0005*i))
 fixture[f'BASE{i:02}']=pd.DataFrame({'open':cc,'close':cc,'quote_volume':1e7},index=idx3)
cc=100*np.exp(np.arange(110)*.02)
special=pd.DataFrame({'open':cc,'close':cc,'quote_volume':1e7},index=idx3)

def run_t3_fixture(extra_len=None):
 f=fixture.copy()
 if extra_len is not None:f['NEW']=special.iloc[:extra_len]
 captured=[]
 with patch.object(lib,'list_symbols',return_value=list(f)), patch.object(lib,'load_klines',side_effect=lambda m,s,i:f[s]), patch.object(lib,'load_funding',return_value=None), patch.object(t234,'DEV',('2009-01-01','2011-01-01')), patch.object(t234,'VAL',('2009-01-01','2011-01-01')), patch.object(pd.DataFrame,'to_csv',lambda self,*a,**k:captured.append(self.copy())):
  result=t234.t3()
 return captured[0],result

a,_=run_t3_fixture(99)
b,_=run_t3_fixture(100)
first=a.index[0]
assert a.loc[first,'n_univ']==20 and b.loc[first,'n_univ']==21
assert first < idx3[99]
out['t3_future_total_length_filter']={'earlier_rebalance':str(first),'sole_new_future_bar':str(idx3[99]),'n_univ_with_99_future_lifetime_bars':int(a.loc[first,'n_univ']),'n_univ_with_100_future_lifetime_bars':int(b.loc[first,'n_univ']),'finding':'Appending one later bar changes an earlier eligible universe via len(d)<100'}

r,_=run_t3_fixture()
assert r['cost_lo'].iloc[1]==0
g1=np.exp(.0100*7); g2=np.exp(.0095*7)
w1=g1/(g1+g2); w2=g2/(g1+g2)
correct_turn=abs(.5-w1)+abs(.5-w2)
out['t3_rebalance_turnover']={'reported_second_week_fee':float(r['cost_lo'].iloc[1]),'drift_adjusted_min_fee':correct_turn*t234.PERP_SIDE,'finding':'Targets unchanged but pretrade weights drift; code compares new target to old target, not holdings'}

z=np.array([-2.5,-3.5,0,0,0,0,0,0,0,0,0,0.])
def sample(threshold):
 i=0;res=[]
 while i<len(z)-6:
  if abs(z[i])>=threshold:res.append(i);i+=5
  else:i+=1
 return res
derived=[i for i in sample(2) if abs(z[i])>=3]
standalone=sample(3)
assert derived==[] and standalone==[1]
out['t4_threshold_blocking']={'derived_z3_indices':derived,'standalone_z3_indices':standalone,'finding':'Matches code structure: z2 entry suppresses subsequent z3 entry'}

q=Path(HERE/'backtests'/'PROTOCOL.md')
pins=json.loads((HERE/'backtests'/'PINS.json').read_text())
assert hashlib.sha256(q.read_bytes()).hexdigest()==pins['PROTOCOL.md']
out['protocol_sha256']=pins['PROTOCOL.md']

j=json.loads((HERE/'backtests'/'results_t1_t5.json').read_text())
for sym in ('BTCUSDT','ETHUSDT'):
 for variant in ('T1a_donchian20_10','T1b_tsmom28_hold5','T1c_sma10_40','T1d_sma200'):
  flags=[]
  for period in ('dev','val'):
   s=j['results'][f'{sym}|{variant}|binance|{period}']
   flags.append(s['Sharpe']>s['bh_Sharpe'] and s['MaxDD']>s['bh_MaxDD'])
  v='PASS' if all(flags) else 'WEAK' if any(flags) else 'FAIL'
  assert j['T1_verdicts'][f'{sym}|{variant}']==v
out['t1_gate_recomputation_from_aggregate']='PASS: all eight published verdicts match aggregate metrics'
for sym in ('BTCUSDT','ETHUSDT'):
 s=j['results'][f'{sym}|T1c_sma10_40|etoro|val']
 out[f'{sym}_etoro_comparison']={k:s[k] for k in ('Sharpe','bh_Sharpe','MaxDD','bh_MaxDD')}
j=json.loads((HERE/'backtests'/'results_t3.json').read_text())['T3']
out['t3_positive_years']={}
for variant in ('T3a_ls_net','T3b_lo_net'):
 years={**j['dev'][variant]['by_year'],**j['val'][variant]['by_year']}
 n=sum(v>0 for v in years.values())
 out['t3_positive_years'][variant]={'positive':n,'total':len(years),'share':n/len(years),'json_share':j['share_years_positive'][variant]}

(HERE/'synthetic_results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))

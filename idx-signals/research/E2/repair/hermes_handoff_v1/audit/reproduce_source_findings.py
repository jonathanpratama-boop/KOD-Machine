"""Read-only reproductions of pure source functions using synthetic 2020 data."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent/'KOD-Machine-hermes-us-data-repair-v1'/'idx-signals'
sys.path.insert(0,str(ROOT))
from idxsig.global_panel import _finish
from idxsig import paper
from idxsig.profiles import PROFILES

rows=[]
for i in range(51):
    for j,date in enumerate(pd.date_range('2020-01-01',periods=3)):
        price=40.0 if i==0 and j==1 else 10.0
        rows.append(dict(ticker=f'T{i:03d}',date=date,source='synthetic',open=price,high=price,low=price,close=price,volume=100000.))
f=pd.DataFrame(rows);prefix,_=_finish(f[f.date<=pd.Timestamp('2020-01-02')].copy());full,_=_finish(f.copy())
old_present=bool(((prefix.ticker=='T000')&(prefix.date==pd.Timestamp('2020-01-02'))).any())
new_present=bool(((full.ticker=='T000')&(full.date==pd.Timestamp('2020-01-02'))).any())
assert old_present and not new_present

# Constant adjusted path. A two-for-one action at entry changes actual price from
# signal 30 to entry 15. No scan, append, source acquisition or ledger writes.
rows=[]
for date in pd.date_range('2020-01-01',periods=8):
    rows.append(dict(ticker='SYNTH',date=date,source='synthetic',previous=15.,open=15.,high=15.,low=15.,close=15.,volume=1000000.,value=15000000.,frequency=np.nan,listed_shares=np.nan,tradable_shares=np.nan))
m=paper._market(pd.DataFrame(rows),'US')
decision={'market':'US','instrument':{'ticker':'SYNTH'},'signal_session':'2020-01-01','plan':{'invalidation':25.5,'max_chase_price':33},'verified_price':{'close':30},'decision':'PASS','decision_id':'SYNTHETIC-NOT-A-CALL'}
out=paper.score(decision,m)
actual=out['execution']['paper_trade']['net_return']
p=PROFILES['US'];tier=float(p.per_side_cost(np.array([15.]))[0]);expected=(1-p.fee_sell-tier)/(1+p.fee_buy+tier)-1
assert not np.isclose(actual,expected)
print(json.dumps({'synthetic_only':True,'source_commit':'1420ee68ac1da2f063bfaf96a1bd374701f23a05','preprocessing':{'row_present_at_cutoff':old_present,'row_present_after_future_bar':new_present,'prefix_invariance':False},'paper_entry_split':{'actual_entry_price':15,'signal_price':30,'scorer_net':actual,'net_with_entry_date_units':expected,'scale':out['price_scale']},'historical_impact':'NOT_MEASURED'},indent=2))

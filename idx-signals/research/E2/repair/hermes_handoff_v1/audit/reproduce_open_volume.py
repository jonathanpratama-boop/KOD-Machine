"""Reproduce ex-post opening-volume dependence without market files or ledger I/O."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'KOD-Machine-hermes-us-data-repair-v1'/'idx-signals'))
import numpy as np
import pandas as pd
from idxsig.execution import Market, ExecConfig, execute, STATUS


def run(entry_volume):
    dates=pd.date_range('2020-01-01',periods=5)
    df=pd.DataFrame(dict(date=dates,ticker='SYN',source='synthetic',previous=10.,open=10.,high=10.,low=10.,close=10.,volume=100000.,value=1000000.))
    df.loc[1,'volume']=entry_volume
    df.loc[1,'value']=entry_volume*10
    m=Market.from_panel(df,price_limits=False)
    cfg=ExecConfig(holding_days=2,notional=5000.,entry_price='open',lot_size=1,ca_mode='adjusted')
    result=execute(m,np.array([0]),np.array([0]),cfg)
    return STATUS[int(result['status'][0])]

if __name__=='__main__':
    low,high=run(1000.),run(100000.)
    assert low=='SKIP_LIQUIDITY' and high=='EXITED'
    print(json.dumps({'fixture':'synthetic-2020','same_open_price':10.,'low_final_volume_status':low,'high_final_volume_status':high,'conclusion':'Opening fill classification depends on end-of-day volume; ex-post capacity filter, not causal opening execution.'},indent=2))

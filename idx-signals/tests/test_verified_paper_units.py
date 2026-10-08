"""Synthetic 2020 fixtures only; scorer must use effective-session units."""
import unittest
import numpy as np
import pandas as pd
from idxsig import paper
from idxsig.execution import Market
from idxsig.profiles import US


def fixture():
    dates=pd.date_range('2020-01-01',periods=9)
    df=pd.DataFrame(dict(date=dates,ticker='SYN',source='synthetic',previous=15.,open=15.,high=15.,low=15.,close=15.,volume=100000.,value=1500000.))
    m=Market.from_panel(df,price_limits=False)
    dec=dict(market='US',instrument={'ticker':'SYN'},signal_session='2020-01-01',verified_price={'close':30.},plan={'invalidation':24.,'max_chase_price':33.},decision='BUY ON TRIGGER',decision_id='synthetic-only')
    units=dict(convention='SPLIT_ONLY',coverage_complete=True,adjustment_reference='2020-01-09',actions=[dict(effective_session='2020-01-02',new_shares=2,old_shares=1)])
    return dec,m,units


class VerifiedPaperUnits(unittest.TestCase):
    def test_split_between_signal_entry_uses_entry_units(self):
        d,m,u=fixture()
        self.assertIn('price_units',__import__('inspect').signature(paper.score).parameters,'No verified-unit scoring path')
        out=paper.score(d,m,price_units=u)
        trade=out['execution']['paper_trade']
        tier=US.per_side_cost(np.array([15.]))[0]
        expected=(1-US.fee_sell-tier)/(1+US.fee_buy+tier)-1
        self.assertAlmostEqual(trade['net_return'],expected)
        self.assertEqual(trade['entry_price_as_traded'],15.)
        self.assertEqual(out['scoring_version'],'verified-us-units-v1')

    def test_exit_uses_its_own_cost_tier(self):
        d,m,u=fixture()
        u['actions'][0]['effective_session']='2020-01-07'
        out=paper.score(d,m,price_units=u)
        trade=out['execution']['paper_trade']
        self.assertEqual(trade['entry_price_as_traded'],30.)
        self.assertEqual(trade['exit_price_as_traded'],15.)
        self.assertAlmostEqual(trade['entry_cost_rate'],US.fee_buy+US.per_side_cost([30.])[0])
        self.assertAlmostEqual(trade['exit_cost_rate'],US.fee_sell+US.per_side_cost([15.])[0])

    def test_unreconciled_or_unknown_metadata_rejected(self):
        import copy
        d,m,u=fixture()
        for key,value in [('coverage_complete',False),('convention','TOTAL_RETURN'),('actions',[])]:
            bad=copy.deepcopy(u);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):paper.score(d,m,price_units=bad)
        original=copy.deepcopy(d)
        paper.score(d,m,price_units=u)
        self.assertEqual(d,original)

    def test_action_after_window_changes_units_not_economic_return(self):
        d,m,u=fixture()
        u['actions'][0]['effective_session']='2020-01-09'
        out=paper.score(d,m,price_units=u)
        trade=out['execution']['paper_trade']
        self.assertEqual(trade['entry_price_as_traded'],30.)
        self.assertEqual(trade['exit_price_as_traded'],30.)
        tier=US.per_side_cost([30.])[0]
        self.assertAlmostEqual(trade['net_return'],(1-US.fee_sell-tier)/(1+US.fee_buy+tier)-1)

if __name__=='__main__':unittest.main()

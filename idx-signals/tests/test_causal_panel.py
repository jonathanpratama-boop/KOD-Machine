"""Synthetic 2020 prefix regressions. No historical/holdout data accessed."""
import unittest
import pandas as pd
from idxsig import global_panel as gp


def frame():
    rows=[]
    for i in range(51):
        for d,p in zip(pd.date_range('2020-01-01',periods=3),[10.,40. if i==0 else 10.,10.]):
            rows.append(dict(ticker=f'T{i:03d}',date=d,source='synthetic',open=p,high=p,low=p,close=p,volume=100000.))
    return pd.DataFrame(rows)


class CausalPanel(unittest.TestCase):
    def test_future_reversal_cannot_rewrite_prefix(self):
        df=frame();cutoff=pd.Timestamp('2020-01-02')
        prefix,_=gp._finish(df[df.date<=cutoff].copy())
        full,_=gp._finish(df.copy())
        pd.testing.assert_frame_equal(prefix.reset_index(drop=True),full[full.date<=cutoff].reset_index(drop=True))
        self.assertEqual(full[(full.ticker=='T000')&(full.date==pd.Timestamp('2020-01-03'))]['previous'].iloc[0],40.)
    def test_large_moves_preserved_without_future_qa_in_features(self):
        panel,qa=gp._finish(frame())
        self.assertEqual(len(panel),153)
        self.assertEqual(qa['spike_rows_dropped'],0)
        self.assertEqual(qa['preprocessing_version'],'causal-close-v2')
        self.assertNotIn('spike_examples',qa)
        self.assertEqual(gp.FORMAT,'panel-global-v2')
    def test_legacy_explicit_only(self):
        self.assertTrue(hasattr(gp,'_finish_legacy_v1'))
        legacy,qa=gp._finish_legacy_v1(frame())
        self.assertEqual(qa['spike_rows_dropped'],1)
        self.assertEqual(len(legacy),152)

if __name__=='__main__':unittest.main()

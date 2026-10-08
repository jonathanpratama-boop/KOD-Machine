"""Synthetic unit contract for historical price units; no market-data access."""
import importlib.util
from pathlib import Path
import unittest
P=Path(__file__).resolve().parents[1]/'idxsig'/'price_units.py'

class PriceUnits(unittest.TestCase):
    def module(self):
        self.assertTrue(P.exists(),'Price-unit reconstruction not implemented')
        spec=importlib.util.spec_from_file_location('price_units',P)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def test_reverse_split_and_boundary(self):
        f=self.module().as_traded
        action=[{'effective_session':'2020-01-03','new_shares':1,'old_shares':10}]
        self.assertAlmostEqual(f(100,'2020-01-02',action,'2020-01-05',coverage_complete=True),10)
        self.assertEqual(f(100,'2020-01-03',action,'2020-01-05',coverage_complete=True),100)
    def test_forward_multiple_and_no_action(self):
        f=self.module().as_traded
        a=[{'effective_session':'2020-01-03','new_shares':2,'old_shares':1},{'effective_session':'2020-01-04','new_shares':3,'old_shares':1}]
        self.assertEqual(f(5,'2020-01-02',a,'2020-01-05',coverage_complete=True),30)
        self.assertEqual(f(5,'2020-01-03',a,'2020-01-05',coverage_complete=True),15)
        self.assertEqual(f(5,'2020-01-05',a,'2020-01-05',coverage_complete=True),5)
        self.assertEqual(f(5,'2020-01-02',[],'2020-01-05',coverage_complete=True),5)
    def test_fail_closed(self):
        f=self.module().as_traded
        bad=[{'effective_session':'2020-01-03','new_shares':0,'old_shares':1}]
        with self.assertRaises(ValueError):f(5,'2020-01-02',[],'2020-01-05',coverage_complete=False)
        with self.assertRaises(ValueError):f(5,'2020-01-02',bad,'2020-01-05',coverage_complete=True)
        with self.assertRaises(ValueError):f(5,'2020-01-06',[],'2020-01-05',coverage_complete=True)
        with self.assertRaises(ValueError):f(float('nan'),'2020-01-02',[],'2020-01-05',coverage_complete=True)
    def test_unknown_volume_convention_rejected(self):
        f=self.module().volume_as_traded
        with self.assertRaises(ValueError):f(1000,2,'UNKNOWN')
        self.assertEqual(f(1000,2,'SPLIT_ADJUSTED_SHARES'),500)
        self.assertEqual(f(1000,2,'AS_TRADED_SHARES'),1000)
    def test_duplicate_or_future_schedule_rejected(self):
        f=self.module().as_traded;a={'effective_session':'2020-01-03','new_shares':2,'old_shares':1}
        with self.assertRaises(ValueError):f(5,'2020-01-02',[a,a],'2020-01-05',coverage_complete=True)
        with self.assertRaises(ValueError):f(5,'2020-01-02',[a],'2020-01-02',coverage_complete=True)

if __name__=='__main__':unittest.main()

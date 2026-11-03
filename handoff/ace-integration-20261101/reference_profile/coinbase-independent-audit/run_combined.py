import sys,socket,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent.parent/'coinbase_reference_adapter_20261101'
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import test_adapter,test_run_once,test_independent,test_freshness
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in (test_adapter,test_run_once,test_independent,test_freshness))
with patch.object(socket,'create_connection',side_effect=AssertionError('network prohibited')),patch.object(socket.socket,'connect',side_effect=AssertionError('network prohibited')):
 result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())

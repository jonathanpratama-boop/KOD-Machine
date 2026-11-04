import sys,socket,unittest
from pathlib import Path
from unittest.mock import patch
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parent.parent/'historical_shared_account_replay_20261101'
sys.path[:0]=[str(root),str(root/'tests')]
import test_daily,test_independent
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in (test_daily,test_independent))
with patch.object(socket,'create_connection',side_effect=AssertionError('network prohibited')),patch.object(socket.socket,'connect',side_effect=AssertionError('network prohibited')):
 result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())

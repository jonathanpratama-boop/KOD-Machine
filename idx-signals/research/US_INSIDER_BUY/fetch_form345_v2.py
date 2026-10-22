"""US_INSIDER_BUY step 1, as actually run (see ADDENDUM_1.md): fetch_form345.py with the corrected download address. ib_lib.py is a committed record and is not edited.
Usage (from idx-signals/): KOD_SEC_CONTACT=<email> python3 research/US_INSIDER_BUY/fetch_form345_v2.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ib_lib  # noqa: E402

ib_lib.URL = "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{quarter}_form345.zip"
import fetch_form345  # noqa: E402

sys.exit(fetch_form345.main())

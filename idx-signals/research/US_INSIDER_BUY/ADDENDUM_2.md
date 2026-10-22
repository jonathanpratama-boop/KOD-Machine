# Addendum 2 (2026-10-22): a process slip before the run

After the commit of the protocol code, the download address in `ib_lib.py` was edited in place (one constant, `URL`), the edit was staged but the commit was refused by the append-only
hook, and the Stage 1 run was started from the working tree before the data, events and PINS were committed. The constant is not used by the run, the verifier or the events, so the
result is unaffected. The edit was then reverted (ib_lib.py is as committed), `fetch_form345_v2.py` carries the address override (ADDENDUM_1), and PINS.json was regenerated from the
committed code. Stage 1 results were produced once; nothing was rerun.

# moonshot-tools

Python toolkit for the Moonshot Project's scheduled runs (`msx.py`, standard library only).
It is kept on this separate branch so it never touches KOD Machine's code or ledgers.

Scheduled runs fetch this branch and run `msx.py` from it:

    git -C /home/claude/kod-machine fetch --quiet origin moonshot-tools
    git -C /home/claude/kod-machine show FETCH_HEAD:msx.py > ~/msx.py
    python3 ~/msx.py selftest

`msx.py` carries a self-hash (`SELF_SHA256`); `selftest` fails if any byte changed.
Procedures: project doc `moonshot/procedures.md` v3.0, §12–§14.

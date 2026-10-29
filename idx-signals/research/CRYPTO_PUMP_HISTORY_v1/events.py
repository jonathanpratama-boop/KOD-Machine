"""The labelled pump events: the union of three public lists, Binance BTC pairs only (SOURCES.json pins each by sha256).

An event is (symbol, UTC date) with the earliest stated time across the lists (the announced pump hour, or the first
signal message). The two unlicensed lists are read from the git-ignored cache data/raw/pumps/, fetched by build.py."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CACHE = ROOT / "data" / "raw" / "pumps"
SOURCES = json.loads((HERE / "SOURCES.json").read_text())
FILES = {"sapienza": HERE / "data" / "pump_telegram_sapienza.csv", "ardia": CACHE / "ardia.csv", "bayi_hu": CACHE / "bayi.txt"}
ALIAS = {"YOYOW": "YOYO"}  # Binance's ticker for YOYOW


def _check(name: str) -> Path:
    p = FILES[name]
    if hashlib.sha256(p.read_bytes()).hexdigest() != SOURCES[name]["sha256"]:
        raise RuntimeError(f"{p.name} differs from SOURCES.json")
    return p


def _utc(s: str) -> datetime:
    s = s.strip().replace("Z", "+00:00").replace("T", " ")
    t = datetime.fromisoformat(s)
    return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def raw() -> list[dict]:
    out = []
    for r in csv.DictReader(open(_check("sapienza"), encoding="utf-8")):
        if r["exchange"].strip().lower() == "binance":
            out.append({"symbol": r["symbol"].strip().upper(), "time": _utc(f"{r['date']} {r['hour']}:00"), "source": "sapienza",
                        "group": r["group"]})
    for r in csv.DictReader(open(_check("ardia"), encoding="utf-8")):
        if r["Exchange"].strip().lower() == "binance":
            t = r["pump_date"].strip() or r["Date"].strip()
            out.append({"symbol": r["Currency"].strip().upper(), "time": _utc(t), "source": "ardia", "group": r["Channel"]})
    for r in csv.DictReader(open(_check("bayi_hu"), encoding="utf-8"), delimiter="\t"):
        if r["exchange"].strip().lower() == "binance" and r["pair"].strip().upper() == "BTC":
            out.append({"symbol": r["coin"].strip().upper(), "time": _utc(r["timestamp"]), "source": "bayi_hu",
                        "group": r["channel_id"]})
    for e in out:
        e["symbol"] = ALIAS.get(e["symbol"], e["symbol"])
    return out


def events() -> list[dict]:
    """One event per (pair, UTC date): earliest time, the sources and groups that list it."""
    by = {}
    for e in raw():
        k = (e["symbol"] + "BTC", e["time"].date().isoformat())
        cur = by.setdefault(k, {"pair": k[0], "date": k[1], "time": e["time"], "sources": set(), "groups": set()})
        cur["time"] = min(cur["time"], e["time"])
        cur["sources"].add(e["source"]); cur["groups"].add(e["group"])
    return sorted(({**v, "sources": sorted(v["sources"]), "groups": sorted(v["groups"])} for v in by.values()),
                  key=lambda v: (v["time"], v["pair"]))

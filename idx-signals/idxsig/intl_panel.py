"""Daily panels for eToro's larger non-US stock exchanges (research/LEAD_LADDER_INTL_v1).

Universe: the stocks eToro lists on each exchange (the archived eToro instrument snapshot), mapped to Yahoo
Finance symbols. Bars: Yahoo v8 chart, daily, split-adjusted by the source, every request in a hashed manifest
(sources/yahoo.py). Panels use the global causal close-time preprocessing (global_panel._finish) and format.
Survivor-only and eToro-selected; the manifest says so.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pandas as pd

from . import global_panel
from .profiles import Profile
from .provenance import MANIFESTS, PANEL_DIR, PKG_ROOT, check_files, rel, sha256_file, utc_stamp
from .sources import yahoo

PROTOCOL = PKG_ROOT / "research" / "LEAD_LADDER_INTL_v1" / "protocol.json"
ETORO = PKG_ROOT / "data" / "raw" / "etoro" / "20261016T190421Z" / "instruments.json"


def protocol() -> dict:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def universe(market: str, proto: dict | None = None, snapshot: Path = ETORO) -> list[str]:
    """Yahoo base symbols (without suffix) of the stocks eToro lists on this market's exchanges."""
    proto = proto or protocol()
    spec = proto["markets"][market]
    if sha256_file(snapshot) != proto["etoro_snapshot"]["sha256"]:
        raise RuntimeError("the eToro snapshot does not match the protocol's hash")
    rows = json.loads(snapshot.read_text(encoding="utf-8"))["InstrumentDisplayDatas"]
    out = set()
    for r in rows:
        if r.get("InstrumentTypeID") != 5 or r.get("IsInternalInstrument") or r.get("ExchangeID") not in spec["exchange_ids"]:
            continue
        sym = r.get("SymbolFull") or ""
        if not sym.endswith(spec["etoro_suffix"]) or "-old" in sym.lower():
            continue
        base = sym[: -len(spec["etoro_suffix"])]
        if spec["yahoo_suffix"] == ".HK" and base.isdigit():
            base = f"{int(base):04d}"  # eToro writes 00001 and 1810; Yahoo wants four digits (0001.HK)
        if base:
            out.add(base)
    return sorted(out)


def profile(market: str, proto: dict | None = None) -> Profile:
    spec = (proto or protocol())["markets"][market]
    e = tuple(spec["band_edges"])
    names = (f"<{e[0]}", f"{e[0]}-{e[1]}", f"{e[1]}-{e[2]}", f">{e[2]}")
    return Profile(market, spec["currency"], 1, False, e, names, 0.0, 0.0, (), 5_000.0, "open",
                   f"eToro-listed stocks on the {market} exchange(s), Yahoo bars",
                   "no cost model: used for separation tests only (LEAD_LADDER_INTL_v1)")


def fetch(market: str, proto: dict | None = None, workers: int = 2, log=print) -> Path:
    proto = proto or protocol()
    spec = proto["markets"][market]
    return yahoo.fetch(universe(market, proto), prefix=f"yahoo_intl_{market.lower()}", suffix=spec["yahoo_suffix"],
                       start=proto["fetch_start"], workers=workers, log=log)


def build(market: str, manifest: Path, log=print) -> Path:
    problems = check_files(manifest)
    if problems:
        raise RuntimeError(f"{manifest.name}: {len(problems)} files differ from the manifest, e.g. {problems[:3]}")
    df, _ = global_panel.load_us(manifest)  # generic Yahoo chart reader (exchange gmtoffset from each response)
    panel, qa = global_panel._finish(df)
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp().replace("-", "").replace(":", "")
    path = PANEL_DIR / f"panel_intl_{market.lower()}-{stamp}.csv.gz"
    out = panel.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.10g")
    first, last = panel["date"].min().date().isoformat(), panel["date"].max().date().isoformat()
    surv = ("survivor-only and eToro-selected: the stocks eToro listed on 2026-10-16, with Yahoo history; names "
            "delisted earlier are absent")
    meta = {
        "format": global_panel.FORMAT, "market": f"INTL_{market}", "panel": rel(path), "sha256": sha256_file(path),
        "built_at": utc_stamp(), "inputs": {manifest.name: {"sha256": sha256_file(manifest), "path": rel(manifest)}},
        "rows": int(len(panel)), "tickers": int(panel["ticker"].nunique()), "sessions": int(panel["date"].nunique()),
        "first_session": first, "last_session": last, "source_boundary": last,
        "default_start": (panel["date"].min() + timedelta(days=120)).date().isoformat(),
        "survivorship": surv,
        "quality_tiers": [{"tier": f"INTL_{market}_SURVIVOR", "from": first, "to": last, "source": "yahoo",
                           "survivorship": surv, "corporate_actions": "split-adjusted by the source"}],
        "known_limitations": [surv, "prices are split-adjusted by the source, not dividend-adjusted",
                              "daily bars only", "no cost model in this panel's profile"],
        "qa": qa,
    }
    mpath = MANIFESTS / f"panel_intl_{market.lower()}-{stamp}.json"
    with mpath.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    log(f"{market} panel {rel(path)} rows {meta['rows']} tickers {meta['tickers']} sessions {meta['sessions']}")
    return mpath


def load(manifest: Path) -> tuple[pd.DataFrame, dict]:
    return global_panel.load(manifest)

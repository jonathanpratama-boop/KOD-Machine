"""BINANCE_ANN_1M step 1, counts only: which announcements are 'launch of a token's USDT-margined Binance futures perpetual'
events for a token that already trades against USDT on Binance spot, liquid enough to matter, between 2020-02-01 and
2023-12-31. An announcement counts only if the perpetual's first archived trading day (data.binance.vision, futures/um)
falls 0-7 days after the article's release: that rules out repeat launches (BUSD-, USDC- and coin-margined contracts of
a token whose main contract exists) and mis-parsed tokens by an objective external fact, not by the title.
Reads announcement titles and times, the DAILY quote volume of the existing Binance panel (age, liquidity) and the file
names of the futures archive; no minute bar and no return is read, and 2024 onward is never loaded.
Usage (from idx-signals/): python3 research/BINANCE_ANN_1M/feasibility.py
Writes feasibility/{events.csv, FEASIBILITY.json} (refuses to overwrite).
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PANEL = ROOT / "data" / "raw" / "binance" / "20261008T001212Z"
WINDOW = (pd.Timestamp("2020-02-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC"))
MIN_AGE_DAYS, ADV_DAYS, MIN_ADV_USDT = 30, 30, 1_000_000.0
LAUNCH_WITHIN_DAYS = 7
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DENY = {"USDT", "BUSD", "USD", "USDC", "COIN", "PERP_", "MARGINED", "PERPETUAL", "CONTRACT", "CONTRACTS", "UP", "TO", "WITH",
        "AND", "LEVERAGE", "BINANCE", "FUTURES", "WILL", "LAUNCH"}
STRIP = re.compile(r"USD[ⓈS]-M|USDT-Margined|Coin-Margined|COIN-M|USDⓈ-Margined|-Margined|Binance", re.I)


def is_launch(title: str) -> bool:
    return bool(re.search(r"Futures Will Launch", title)) and "Perpetual" in title and "Index" not in title


def tokens(title: str) -> list[str]:
    seg = title.split("Will Launch", 1)[1].split("Perpetual", 1)[0]
    seg = STRIP.sub(" ", seg).replace("/", " ").replace(",", " ").replace("&", " ")
    out = []
    for t in re.findall(r"\b[A-Z0-9]{2,12}\b", seg):
        if t not in DENY and t not in out:
            out.append(t)
    return out


def perp_first_date(symbol: str, retries: int = 4) -> str | None:
    """First archived daily bar of the USDT-margined perpetual `symbol` (YYYY-MM-DD), None if the archive has none."""
    url = f"{S3}?delimiter=/&prefix=data/futures/um/daily/klines/{symbol}/1d/&max-keys=4"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as r:
                keys = re.findall(r"<Key>([^<]+\.zip)</Key>", r.read().decode())
            return re.search(r"(\d{4}-\d{2}-\d{2})\.zip$", keys[0]).group(1) if keys else None
        except Exception:  # noqa: BLE001
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"archive listing failed for {symbol}")


def load_daily() -> dict[str, pd.DataFrame]:
    """symbol -> DataFrame(date, quote_volume) from the existing daily panel (USDT pairs, incl. delisted ones)."""
    info = json.loads((PANEL / "exchangeInfo.json").read_text())
    out = {}
    for s in info["symbols"]:
        if s["quoteAsset"] != "USDT":
            continue
        p = PANEL / f"{s['symbol']}.json"
        if not p.exists():
            continue
        rows = json.loads(p.read_text())
        if rows:
            df = pd.DataFrame({"date": pd.to_datetime([r[0] for r in rows], unit="ms", utc=True),
                               "qv": [float(r[7]) for r in rows]})
            out[s["symbol"]] = df
    return out


def pair_for(token: str, daily: dict) -> str | None:
    for cand in (token + "USDT", token[4:] + "USDT" if token.startswith("1000") else None):
        if cand and cand in daily:
            return cand
    return None


def main() -> int:
    out_dir = HERE / "feasibility"
    if (out_dir / "FEASIBILITY.json").exists():
        sys.exit("error: feasibility/FEASIBILITY.json exists")
    ann = pd.read_csv(HERE / "announcements.csv.gz")
    ann["t"] = pd.to_datetime(ann.release_ms, unit="ms", utc=True)
    ann = ann[ann.t < WINDOW[1]].sort_values("t")                       # 2024 onward is never used
    launches = ann[ann.title.map(is_launch)].copy()
    launches["tokens"] = launches.title.map(tokens)
    daily = load_daily()
    perp_cache: dict[str, str | None] = {}
    rows, no_token, no_pair = [], [], []
    for r in launches.itertuples():
        if not r.tokens:
            no_token.append(r.title)
        for tok in r.tokens:
            pair = pair_for(tok, daily)
            in_window = bool(WINDOW[0] <= r.t < WINDOW[1])
            perp = tok + "USDT"
            if in_window and pair is not None and perp not in perp_cache:
                perp_cache[perp] = perp_first_date(perp)
                time.sleep(0.2)
            d0 = perp_cache.get(perp)
            lag = (pd.Timestamp(d0, tz="UTC") - r.t.normalize()).days if d0 else None
            rec = {"article_id": r.id, "t_ms": r.release_ms, "t": r.t.isoformat(), "title": r.title, "token": tok,
                   "pair": pair, "perp": perp, "perp_first_day": d0, "days_to_perp": lag, "in_window": in_window}
            if pair is None:
                no_pair.append((tok, r.title))
            else:
                d = daily[pair]
                before = d[d.date < r.t.normalize()]
                rec["age_days"] = int((r.t.normalize() - d.date.iloc[0]).days)
                rec["adv30_usdt"] = float(before.qv.tail(ADV_DAYS).median()) if len(before) >= ADV_DAYS else np.nan
            rows.append(rec)
    ev = pd.DataFrame(rows)
    ev["launch_ok"] = ev.days_to_perp.between(0, LAUNCH_WITHIN_DAYS)
    ev["eligible"] = (ev.in_window & ev.launch_ok & ev.pair.notna() & (ev.age_days >= MIN_AGE_DAYS)
                      & (ev.adv30_usdt >= MIN_ADV_USDT)).fillna(False)
    out_dir.mkdir()
    ev.to_csv(out_dir / "events.csv", index=False)
    w = ev[ev.in_window]
    counts = {
        "launch_articles_before_2024": int(len(launches)), "articles_without_a_token": len(no_token),
        "token_rows_in_window": int(len(w)), "with_usdt_spot_pair": int(w.pair.notna().sum()),
        "perp_first_day_found": int(w.perp_first_day.notna().sum()),
        "perp_started_0_to_7_days_after_article": int((w.launch_ok & w.pair.notna()).sum()),
        "and_spot_age_ok": int((w.launch_ok & (w.age_days >= MIN_AGE_DAYS)).sum()),
        "eligible_events": int(ev.eligible.sum()),
        "eligible_by_year": {str(k): int(v) for k, v in
                             ev[ev.eligible].groupby(pd.to_datetime(ev[ev.eligible].t_ms, unit="ms", utc=True).dt.year).size().items()},
        "eligible_distinct_days": int(pd.to_datetime(ev[ev.eligible].t_ms, unit="ms", utc=True).dt.date.nunique()),
        "eligible_median_adv30_usdt": float(ev[ev.eligible].adv30_usdt.median()),
        "go_rule": "eligible events >= 100 (fixed before this run)",
        "rejected_by_launch_rule": sorted(set(w[w.pair.notna() & ~w.launch_ok].token)),
    }
    counts["go"] = bool(counts["eligible_events"] >= 100)
    (out_dir / "FEASIBILITY.json").write_text(json.dumps({"counts": counts, "articles_without_a_token": no_token,
                                                          "tokens_without_spot_pair_in_window": sorted({f"{t}" for t, _ in no_pair})},
                                                         indent=1) + "\n")
    print(json.dumps(counts, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

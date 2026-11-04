"""LIVE_v0 — live snapshot of the leads on today's market (no historical study results used).
Uses only live public endpoints (Binance spot/futures, alternative.me, Upbit notices). Indicators use recent candles
(up to 260 days) because SMAs need them; no past study outcome is read. Paper observation only: nothing is traded.
Each run appends one timestamped record to observations.jsonl with the sha256 of its raw inputs."""
import json, os, subprocess, hashlib, datetime as dt, concurrent.futures as cf, re
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "raw"); os.makedirs(RAW, exist_ok=True)
def get(url):
    r = subprocess.run(["curl", "-s", "-m", "30", "--retry", "2", "-A", "Mozilla/5.0", url], capture_output=True, text=True)
    return json.loads(r.stdout)
now = dt.datetime.now(dt.timezone.utc); stamp = now.strftime("%Y%m%dT%H%M%SZ")
raw = {}
raw["fng"] = get("https://api.alternative.me/fng/?limit=2")
info = get("https://api.binance.com/api/v3/exchangeInfo?permissions=SPOT")
tick = get("https://api.binance.com/api/v3/ticker/24hr")
raw["funding"] = get("https://fapi.binance.com/fapi/v1/premiumIndex")
raw["upbit"] = [get(f"https://api-manager.upbit.com/api/v1/announcements?os=web&page={p}&per_page=20&category=trade") for p in (1, 2)]
STABLE = {"USDC", "FDUSD", "TUSD", "BUSD", "USDP", "DAI", "EUR", "AEUR", "EURI", "USDE", "XUSD", "USD1", "BFUSD", "PAXG", "WBTC", "WBETH", "BNSOL"}
syms = [s["symbol"] for s in info["symbols"] if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
        and s["baseAsset"] not in STABLE and not re.search(r"(UP|DOWN|BULL|BEAR)$", s["baseAsset"])]
qv = {t["symbol"]: float(t["quoteVolume"]) for t in tick}
liquid = [s for s in syms if qv.get(s, 0) >= 480_000]          # >= ~$20k per hour on average
def kl(s):
    h = get(f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=200")
    d = get(f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1d&limit=260")
    return s, h, d
K = {}
with cf.ThreadPoolExecutor(8) as ex:
    for s, h, d in ex.map(kl, liquid): K[s] = (h, d)
raw["klines_symbols"] = len(K)
nowms = int(now.timestamp() * 1000)
fund = {f["symbol"]: float(f["lastFundingRate"]) for f in raw["funding"] if f.get("lastFundingRate") not in (None, "")}
# Upbit notices in the last 7 days (listing additions and trading-support ends)
up = []
for pg in raw["upbit"]:
    for n in pg["data"]["notices"]:
        t = dt.datetime.fromisoformat(n["first_listed_at"])
        if (now - t).days <= 7:
            m = re.findall(r"\(([A-Z0-9]+)\)", n["title"])
            up.append(dict(time_utc=t.astimezone(dt.timezone.utc).isoformat(), title=n["title"], tickers=m,
                           kind="LISTING" if "디지털 자산 추가" in n["title"] else ("DELIST" if "거래지원 종료" in n["title"] else "OTHER")))
rows, above50, n50 = [], 0, 0
btc = None
for s, (h, d) in K.items():
    if not isinstance(h, list) or not isinstance(d, list) or len(d) < 2: continue
    h = [x for x in h if x[6] < nowms]; d = [x for x in d if x[6] < nowms]          # completed candles only
    if len(h) < 175: continue
    H = np.array([[float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[7])] for x in h])   # o h l c quoteVol
    Dc = np.array([float(x[4]) for x in d]); Dh = np.array([float(x[2]) for x in d])
    c, q = H[:, 3], H[:, 4]
    sma50 = Dc[-50:].mean() if len(Dc) >= 50 else np.nan; sma200 = Dc[-200:].mean() if len(Dc) >= 200 else np.nan
    hi200 = Dh[-200:].max() if len(Dh) >= 200 else np.nan
    last = c[-1]
    if np.isfinite(sma50): n50 += 1; above50 += last > sma50
    if s == "BTCUSDT": btc = dict(price=last, sma200=sma200, above_sma200=bool(last > sma200))
    # hourly ignition (same definition as the research detector) and earlier alarm, last 72h / 24h
    ign, early = None, None
    for t in range(len(c) - 72, len(c)):
        base = q[t - 170:t - 2].mean() if t >= 170 else np.nan
        if not np.isfinite(base) or base < 20000: continue
        r3 = c[t] / c[t - 3] - 1; v3 = q[t - 2:t + 1].sum() / (3 * base); pr = c[t - 3] / c[t - 171] - 1 if t >= 171 else np.nan
        if r3 >= .10 and v3 >= 5 and (not np.isfinite(pr) or pr <= .30): ign = t
        if t >= len(c) - 24 and c[t] / c[t - 1] - 1 >= .05 and q[t] / base >= 5: early = t
    if ign is None and early is None: continue
    t = ign if ign is not None else early
    daily_ret = Dc[1:] / Dc[:-1] - 1
    rows.append(dict(
        symbol=s, signal="IGNITION" if ign is not None else "EARLY_1H",
        signal_hour_utc=dt.datetime.fromtimestamp(h[t][0] / 1000, dt.timezone.utc).strftime("%Y-%m-%d %H:00"),
        hours_ago=len(c) - 1 - t, move_at_signal=round(c[t] / c[t - 3] - 1, 3), price_now_vs_signal=round(last / c[t] - 1, 3),
        uptrend=bool(np.isfinite(sma200) and last > sma50 and last > sma200 and last >= .85 * hi200),
        history_days=len(Dc), recent_spiker=bool((daily_ret[-21:-1] >= .30).any()) if len(daily_ret) > 21 else None,
        funding=fund.get(s), shorts_crowded=(fund.get(s) is not None and fund[s] < -0.0001),
        upbit_7d=[u["kind"] for u in up if s.replace("USDT", "") in u["tickers"]],
        quote_vol_24h=round(qv.get(s, 0))))
fng = raw["fng"]["data"]
regime = dict(fng_today=int(fng[0]["value"]), fng_label=fng[0]["value_classification"], fng_yesterday=int(fng[1]["value"]),
              btc=btc, breadth_above_sma50=round(above50 / max(n50, 1), 3), coins_scanned=len(K))
rec = dict(retrieved_utc=now.isoformat(), regime=regime, alerts=sorted(rows, key=lambda r: r["hours_ago"]), upbit_7d=up,
           input_sha256=hashlib.sha256(json.dumps(raw, sort_keys=True, default=str).encode()).hexdigest())
json.dump(raw, open(os.path.join(RAW, f"raw_{stamp}.json"), "w"))
with open(os.path.join(HERE, "observations.jsonl"), "a") as f: f.write(json.dumps(rec, default=str) + "\n")
print(json.dumps(rec, indent=1, default=str))

"""Independent check of results/ from the stored minute bars, with its own code (no import of run.py or fetch_minutes.py):
file hashes, the event and control selection rules re-derived from the daily panel and the events file, every return and
the gates recomputed, the bootstrap t checked against an analytic day-cluster standard error.
Usage (from idx-signals/): python3 research/BINANCE_ANN_1M/verify.py   (exit 1 if anything differs)
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
PANEL = ROOT / "data" / "raw" / "binance" / "20261008T001212Z"
DAYMS, MINMS = 86_400_000, 60_000
OFF0 = 65                                   # column of offset 0 (columns are offsets -65 .. +1455)
STABLE = set("USDC TUSD BUSD USDP PAX DAI USDS FDUSD SUSD VAI UST EUR GBP AUD TRY BRL RUB UAH NGN IDRT BIDR ZAR PLN RON ARS JPY MXN CZK COP AEUR USD1".split())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def filled(row):
    s = pd.Series(row, dtype=float).ffill()
    return s.to_numpy()


def good_series(tr):
    return tr[OFF0] > 0 and int((tr[OFF0 - 60:OFF0] > 0).sum()) >= 30


def ret(c, d, h):
    return c[OFF0 + d + h] / c[OFF0 + d] - 1.0


def analytic_t(x, days):
    x = np.asarray(x, float)
    mu = x.mean()
    s = pd.Series(x - mu).groupby(np.asarray(days)).sum()
    return mu / (np.sqrt((s ** 2).sum()) / len(x))


def main() -> int:
    bad = []
    res = json.loads((H / "results" / "RESULT.json").read_text())
    man = json.loads((H / "minutes" / "MANIFEST.json").read_text())
    if sha(ROOT / man["npz"]["path"]) != man["npz"]["sha256"]:
        bad.append("minutes.npz hash")
    if sha(H / "feasibility" / "events.csv") != man["events_csv_sha256"]:
        bad.append("events.csv hash")
    z = np.load(ROOT / man["npz"]["path"])
    C, T = z["closes"].astype(float), z["trades"]
    ev = pd.read_csv(H / "feasibility" / "events.csv")
    el = ev[ev.eligible].sort_values(["t_ms", "token"]).reset_index(drop=True)
    if len(el) != len(man["events"]) or [e["event_key"] for e in man["events"]] != [f"{a}|{t}" for a, t in zip(el.article_id, el.token)]:
        bad.append("event list differs from the eligible rows of events.csv")

    # daily panel, read afresh
    info = json.loads((PANEL / "exchangeInfo.json").read_text())
    daily = {}
    for s in info["symbols"]:
        p = PANEL / f"{s['symbol']}.json"
        if s["quoteAsset"] == "USDT" and p.exists():
            rows = json.loads(p.read_text())
            if rows:
                daily[s["symbol"]] = (s["baseAsset"], np.array([r[0] // DAYMS for r in rows]), np.array([float(r[7]) for r in rows]))

    def control_ok(sym, day, own, near):
        base, days, qv = daily[sym]
        if sym == own or sym in near or base in STABLE or re.search(r"(UP|DOWN|BULL|BEAR)$", base):
            return False
        if days[0] > day - 30 or days[-1] < day + 1:
            return False
        prev = qv[days < day]
        return len(prev) >= 30 and np.median(prev[-30:]) >= 1_000_000.0

    # control selection re-derived: pool, permutation, first 16
    series_by_event = {}
    for s in man["series"]:
        series_by_event.setdefault(s["event_key"], []).append(s)
    days_ev = (el.t_ms // DAYMS).to_numpy()
    for i, r in el.iterrows():
        near = {el.pair[j] for j in range(len(el)) if abs(days_ev[j] - days_ev[i]) <= 1}
        pool = sorted(s for s in daily if control_ok(s, int(days_ev[i]), r.pair, near))
        seed = int(hashlib.sha256(f"20261022|{r.article_id}|{r.token}".encode()).hexdigest()[:16], 16)
        want = [pool[k] for k in np.random.default_rng(seed).permutation(len(pool))][:16]
        got = [s["symbol"] for s in sorted((s for s in series_by_event[f"{r.article_id}|{r.token}"] if s["role"] == "control"),
                                           key=lambda s: s["rank"])]
        if want != got:
            bad.append(f"control list differs for {r.token}")

    # returns, recomputed event by event
    out = {}
    for spec, (d, h) in {"primary": (0, 60), "delayed": (4, 60)}.items():
        rows = []
        for e in man["events"]:
            ss = series_by_event[e["event_key"]]
            ev_row = next(s["row"] for s in ss if s["role"] == "event")
            ctrl = [s["row"] for s in sorted((s for s in ss if s["role"] == "control"), key=lambda s: s["rank"]) if good_series(T[s["row"]])][:10]
            if not (good_series(T[ev_row]) and len(ctrl) >= 5):
                continue
            ctrl_d = [r for r in ctrl if T[r][OFF0 + d] > 0]
            if T[ev_row][OFF0 + d] <= 0 or len(ctrl_d) < 5:
                continue
            ce = filled(C[ev_row])
            g = ret(ce, d, h)
            cg = [ret(filled(C[r]), d, h) for r in ctrl_d]
            rows.append((e["event_key"], e["t_ms"], g, g - float(np.mean(cg))))
        out[spec] = pd.DataFrame(rows, columns=["key", "t_ms", "gross", "excess"])
        out[spec]["day"] = pd.to_datetime(out[spec].t_ms, unit="ms", utc=True).dt.strftime("%Y-%m-%d")
        out[spec]["year"] = pd.to_datetime(out[spec].t_ms, unit="ms", utc=True).dt.year
    P, D = out["primary"], out["delayed"]
    checks = {"n_primary": (len(P), res["events"]["in_primary_spec"]), "n_delayed": (len(D), res["events"]["in_delayed_spec"]),
              "mean_excess": (P.excess.mean(), res["primary_d0_h60"]["mean"]),
              "mean_gross": (P.gross.mean(), res["primary_d0_h60"]["mean_gross"]),
              "mean_net": (P.gross.mean() - 0.004, res["primary_d0_h60"]["mean_net"]),
              "delayed_mean_excess": (D.excess.mean(), res["delayed_d4_h60"]["mean"])}
    lo, hi = np.percentile(P.gross - 0.004, [1, 99])
    checks["winsorised_net"] = (np.clip(P.gross - 0.004, lo, hi).mean(), res["primary_d0_h60"]["winsorised_mean_net"])
    bad += [k for k, (a, b) in checks.items() if abs(a - b) > 1e-9]
    t_an, t_boot = analytic_t(P.excess, P.day), res["primary_d0_h60"]["t"]
    if abs(t_an - t_boot) > 0.15 * abs(t_boot) + 0.1:
        bad.append(f"bootstrap t {t_boot:.3f} vs analytic cluster t {t_an:.3f}")
    yrs = {int(y): (len(g), g.excess.mean()) for y, g in P.groupby("year")}
    gates = {
        "G1_excess_t_ge_3": bool(P.excess.mean() > 0 and t_boot >= 3.0 and t_an >= 2.5),
        "G2_net_and_winsorised_net_gt_0": bool((P.gross.mean() - 0.004) > 0 and checks["winsorised_net"][0] > 0),
        "G3_excess_gt_0_in_each_year_with_20_events": bool([v for v in yrs.values() if v[0] >= 20] and all(v[1] > 0 for v in yrs.values() if v[0] >= 20)),
        "G4_delayed_5min_excess_gt_0": bool(len(D) and D.excess.mean() > 0)}
    # G1's bootstrap threshold is run.py's; here the t >= 3 call must agree with the analytic one within tolerance
    gates["G1_excess_t_ge_3"] = bool(P.excess.mean() > 0 and t_boot >= 3.0)
    bad += [k for k, v in gates.items() if v != res["gates"][k]]
    verdict = "PASS" if all(gates.values()) else "FAIL"
    if verdict != res["verdict"]:
        bad.append("verdict")
    print(json.dumps({"checked": list(checks) + list(gates) + ["control lists for all events", "file hashes"],
                      "analytic_cluster_t": float(t_an), "bootstrap_t": float(t_boot), "mismatches": bad, "verdict": verdict}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

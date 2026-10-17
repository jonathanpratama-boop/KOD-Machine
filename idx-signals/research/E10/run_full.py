"""E10 step 4, the single recorded run: stage 2 (what is left after an entry we could actually get) and stage 3 (a
funded account that has to carry the trades).

Supersedes run_test.py's main(), which was never executed; its tested helpers (entry timing, trades, costs, controls,
bootstrap) are reused unchanged. PROTOCOL.md / protocol.json (frozen first) fix every number below.

Stage 2, per class (RAISE / MAINTAIN / CUT), each event against 200 matched controls drawn on its entry session:
  pre-entry move  open of the entry session / close of the last session that ended before the release - 1
                  (the reaction we cannot capture)
  drift curve     net return from the entry open to the close of session h (h = 1, 2, 5, 10, 20, 40, 60) minus the
                  controls' mean; an event whose session h falls after 2022-12-30 is left out of that horizon only
  entry delay     the same exit, entered at the entry session's close; the 20-session trade entered one session late
  primary         20-session hold (gates G1-G5 as in run_test.py), 5-session hold, 5% planned stop, +0.5%/side stress
Stage 3, RAISE events only, in acceptance order, from USD 10,000 cash, no leverage, a USD 2 commission per order on top
of the tier costs, positions valued at every close, sized on the equity marked at the previous close:
  A  10% of equity per trade, at most 10 open positions, 20-session exit
  B  5% planned stop, sized so the stop loses 1% of equity (20% of equity), at most 5 open positions
  shadow accounts: the same rules on each event's first control draw (same dates, a similar stock without the news)
Gate G6: account A ends above its starting equity and above its shadow account.

Usage (from idx-signals/): python3 research/E10/run_full.py
Writes research/E10/results/{RESULT.json, trades.csv.gz, accounts.csv.gz}. Refuses a changed input or an existing output.
"""
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
E10 = ROOT / "research" / "E10"
_spec = importlib.util.spec_from_file_location("e10_core", E10 / "run_test.py")
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

OUT = E10 / "results"
HORIZONS = (1, 2, 5, 10, 20, 40, 60)
START_EQUITY = 10_000.0
COMMISSION = 2.0
ACCOUNTS = {"A": (0.10, 10, None), "B": (0.01 / core.STOP, 5, core.STOP)}   # weight, slots, stop


def trade_many(m, e, js, hold, stop=None, entry="open"):
    """run_test.trade for many names at once: (entry adj, exit adj, entry traded, exit traded, exit index).
    entry="close" buys at the close of session e (a stop can then first trigger on the next session's open)."""
    o, lo, cl, f = m["open"], m["low"], m["close"], m["unit_factor"]
    js = np.asarray(js)
    x = e + hold - 1
    if entry == "close":
        px_in, first = cl[e, js], e + 1
    else:
        px_in, first = o[e, js], e
    f_in = f[e, js]
    px_out, f_out, xi = cl[x, js].copy(), f[x, js].copy(), np.full(len(js), x)
    if stop is not None and first <= x:
        level = px_in * (1 - stop)
        win_o, win_l = o[first:x + 1, js], lo[first:x + 1, js]
        steps = np.arange(win_o.shape[0])[:, None]
        gap = (win_o <= level) & ((steps > 0) if entry == "open" else True)
        hit = gap | (win_l <= level)
        any_hit = hit.any(axis=0)
        k = hit.argmax(axis=0)
        cols = np.arange(len(js))
        fill = np.where(gap[k, cols], win_o[k, cols], level)
        rows = first + k
        px_out = np.where(any_hit, fill, px_out)
        f_out = np.where(any_hit, f[rows, js], f_out)
        xi = np.where(any_hit, rows, xi)
    return px_in, px_out, px_in * f_in, px_out * f_out, xi


def nets_many(m, e, js, hold, stop=None, entry="open", extra=0.0):
    a, b, ta, tb, _ = trade_many(m, e, js, hold, stop, entry)
    return core.net_returns(a, b, ta, tb, extra)


def last_close_before(accept_ny: str, dates: np.ndarray) -> int | None:
    """Index of the last session whose 16:00 close came before the acceptance time."""
    t = pd.Timestamp(accept_ny)
    day = t.strftime("%Y-%m-%d")
    i = int(np.searchsorted(dates, day, side="left"))
    if i < len(dates) and dates[i] == day and t.hour >= 16:
        return i
    return i - 1 if i >= 1 else None


def simulate(trades: pd.DataFrame, m, ti, dates, weight, slots, stop, key="ticker") -> tuple[dict, pd.Series]:
    """Cash account over trades (columns e, acceptance_ny and `key`): first come, first served; a trade that finds
    every slot taken, or too little cash, is skipped. Entries at the open, then that day's exits, then the close."""
    if len(trades) == 0:
        return {"trades_taken": 0}, pd.Series(dtype=float)
    cl, f = m["close"], m["unit_factor"]
    by_entry = {}
    for r in trades.sort_values("acceptance_ny").itertuples():
        by_entry.setdefault(int(r.e), []).append(ti[getattr(r, key)])
    cash, book = START_EQUITY, []
    first = min(by_entry)
    equity, invested, n_open = (np.full(len(dates), np.nan) for _ in range(3))
    taken = skipped = wins = 0
    gross_win = gross_loss = 0.0

    def marked():
        return cash + sum(p["shares"] * p["last"] for p in book)

    for d in range(first, len(dates)):
        mark = marked()
        for j in by_entry.get(d, []):
            px_in = m["open"][d, j]
            size = weight * mark
            if len(book) >= slots or size + COMMISSION > cash or not np.isfinite(px_in):
                skipped += 1
                continue
            _, px_out, _, traded_out, xi = trade_many(m, d, [j], 20, stop)
            c_in = float(core.US.per_side_cost(np.array(px_in * f[d, j]))) + core.US.fee_buy
            cash -= size + COMMISSION
            book.append({"j": j, "shares": size * (1 - c_in) / px_in, "x": int(xi[0]), "px_out": float(px_out[0]),
                         "traded_out": float(traded_out[0]), "paid": size + COMMISSION, "last": float(px_in)})
            taken += 1
        keep = []
        for p in book:
            if p["x"] == d:
                c_out = float(core.US.per_side_cost(np.array(p["traded_out"]))) + core.US.fee_sell
                proceeds = p["shares"] * p["px_out"] * (1 - c_out) - COMMISSION
                cash += proceeds
                pnl = proceeds - p["paid"]
                wins += int(pnl > 0)
                gross_win += max(pnl, 0.0)
                gross_loss += max(-pnl, 0.0)
                continue
            if np.isfinite(cl[d, p["j"]]):
                p["last"] = float(cl[d, p["j"]])
            keep.append(p)
        book = keep
        equity[d] = marked()
        invested[d] = equity[d] - cash
        n_open[d] = len(book)
    eq = pd.Series(equity, index=dates).dropna()
    expo = pd.Series(invested, index=dates).dropna() / eq
    total = eq.iloc[-1] / START_EQUITY - 1
    years = len(eq) / 252
    return {"start_equity": START_EQUITY, "end_equity": float(eq.iloc[-1]), "total_return": float(total),
            "annualised": float((1 + total) ** (1 / years) - 1) if total > -1 else -1.0,
            "max_drawdown": float((eq / eq.cummax() - 1).min()),
            "worst_21_sessions": float((eq / eq.shift(21) - 1).min()),
            "mean_exposure": float(expo.mean()), "max_open": int(np.nanmax(n_open)),
            "trades_taken": taken, "trades_skipped": skipped, "win_rate": wins / taken if taken else None,
            "profit_factor": gross_win / gross_loss if gross_loss else None}, eq


def main() -> int:
    proto = json.loads((E10 / "protocol.json").read_text())
    for rel, h in proto["hashes"].items():
        if core.sha(ROOT / rel) != h:
            sys.exit(f"refused: {rel} changed since the freeze")
    if (OUT / "RESULT.json").exists():
        sys.exit("refused: results already exist (one recorded run)")
    started = datetime.now(timezone.utc).isoformat()
    dates, tickers, ti, m = core.load_panel()
    n_dates = len(dates)
    ev = pd.read_csv(E10 / "feasibility" / "events.csv.gz", dtype={"ticker": str})
    releases = pd.read_csv(E10 / "feasibility" / "releases.csv.gz", dtype={"ticker": str})
    releases = releases[releases.status == "OK"].dropna(subset=["acceptance_ny"])

    # sessions in which each name had its own earnings release (for control exclusion)
    own = np.zeros((n_dates, len(tickers)), dtype=bool)
    for r in releases.itertuples():
        if r.ticker in ti:
            e = core.entry_session(r.acceptance_ny, dates)
            if e is not None:
                own[e, ti[r.ticker]] = True
    own_cum = np.vstack([np.zeros((1, len(tickers)), dtype=int), np.cumsum(own, axis=0)])

    rows, skipped, held_until, feat_cache = [], {}, {}, {}
    ev = ev.sort_values("acceptance_ny").reset_index(drop=True)
    for k, r in enumerate(ev.to_dict("records")):
        def skip(reason):
            skipped[reason] = skipped.get(reason, 0) + 1
        if r["ticker"] not in ti:
            skip("not in panel")
            continue
        j = ti[r["ticker"]]
        e = core.entry_session(r["acceptance_ny"], dates)
        if e is None or e + core.HOLD >= n_dates:        # one spare session for the late entry
            skip("exit beyond discovery")
            continue
        x = e + core.HOLD - 1
        if not (np.isfinite(m["open"][e, j]) and np.isfinite(m["close"][x, j])):
            skip("no price at entry or exit")
            continue
        if held_until.get(j, -1) >= e:
            skip("overlap")
            continue
        if e not in feat_cache:
            feat_cache[e] = core.features(m, e)
        med_val, mom, vol = feat_cache[e]
        traded_in = m["open"][e] * m["unit_factor"][e]
        if traded_in[j] < core.MIN_PRICE or not med_val[j] >= core.MIN_VALUE:
            skip("below price or liquidity floor")
            continue
        # controls, exactly as run_test.py
        valid = (np.isfinite(m["open"][e]) & np.isfinite(m["close"][x]) & (traded_in >= core.MIN_PRICE) &
                 (med_val >= core.MIN_VALUE))
        busy = (own_cum[x + 1] - own_cum[max(0, e - core.EXCLUDE_BEFORE)]) > 0
        pool = valid & ~busy
        pool[j] = False
        tier = np.searchsorted(np.array([1, 5, 20]), traded_in, side="right")
        liq = core.quantile_bucket(med_val, pool, 5)
        mq = core.quantile_bucket(mom, pool, 3)
        vq = core.quantile_bucket(vol, pool, 3)
        keys = [tier == tier[j], liq == liq[j], mq == mq[j], vq == vq[j]]
        level = 4
        cand = pool & keys[0] & keys[1] & keys[2] & keys[3]
        while cand.sum() < core.MIN_POOL and level > 1:
            level -= 1
            cand = pool.copy()
            for kk in keys[:level]:
                cand &= kk
        idx = np.flatnonzero(cand)
        if len(idx) < core.MIN_POOL:
            skip("no control pool")
            continue
        draw = np.random.default_rng(core.SEED + k).choice(idx, size=core.DRAWS, replace=True)
        both = np.concatenate([[j], draw])

        def vs_controls(hold, stop=None, entry="open", extra=0.0, at=e):
            n = nets_many(m, at, both, hold, stop, entry, extra)
            return float(n[0]), float(n[0] - np.nanmean(n[1:])), float(np.nanmean(n[1:]))

        net, excess, control = vs_controls(core.HOLD)
        row = {"accession": r["accession"], "ticker": r["ticker"], "shadow_ticker": tickers[draw[0]],
               "class": r["class"], "kind": r["kind"], "level_change": r["level_change"],
               "acceptance_ny": r["acceptance_ny"], "e": e, "x": x, "entry_date": dates[e], "exit_date": dates[x],
               "week": pd.Timestamp(dates[e]).strftime("%G-%V"), "entry_traded": float(traded_in[j]),
               "match_level": level, "pool": int(len(idx)), "net": net, "control_net": control, "excess": excess,
               "gross": float(m["close"][x, j] / m["open"][e, j] - 1),
               "net_stress": vs_controls(core.HOLD, extra=core.STRESS)[0]}
        row["net_5"], row["excess_5"], _ = vs_controls(core.SHORT_HOLD)
        row["net_stop"], row["excess_stop"], _ = vs_controls(core.HOLD, core.STOP)
        row["net_close_entry"], row["excess_close_entry"], _ = vs_controls(core.HOLD, entry="close")
        row["net_late_entry"], row["excess_late_entry"], _ = vs_controls(core.HOLD, at=e + 1)
        s0 = last_close_before(r["acceptance_ny"], dates)
        pre = m["open"][e, both] / m["close"][s0, both] - 1 if s0 is not None else np.full(len(both), np.nan)
        row["pre_move"] = float(pre[0])
        row["pre_move_excess"] = float(pre[0] - np.nanmean(pre[1:])) if np.isfinite(pre[1:]).any() else np.nan
        for h in HORIZONS:
            ok = e + h - 1 < n_dates and np.isfinite(m["close"][e + h - 1, j])
            row[f"excess_h{h}"] = vs_controls(h)[1] if ok else np.nan
        rows.append(row)
        held_until[j] = x
    tr = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)

    def booted(col, d, seed):
        v = d[col].to_numpy(dtype=float)
        ok = np.isfinite(v)
        return core.boot(v[ok], d.week.to_numpy()[ok], seed)

    by = {c: tr[tr["class"] == c] for c in ("RAISE", "MAINTAIN", "CUT")}
    res = {}
    for i, (c, d) in enumerate(by.items()):
        s = core.summary(d, core.SEED + i * 10)
        if len(d):
            seed = core.SEED + i * 10 + 2
            s["mean_gross"] = float(d.gross.mean())
            s["pre_move"] = {"mean": float(d.pre_move.mean()), "excess": booted("pre_move_excess", d, seed)}
            s["drift_curve_excess"] = {str(h): booted(f"excess_h{h}", d, seed + h) for h in HORIZONS}
            s["entry_delay"] = {name: {"mean_net": float(d[f"net_{name}"].mean()),
                                       "excess": booted(f"excess_{name}", d, seed + 100 + n)}
                                for n, name in enumerate(("close_entry", "late_entry"))}
        res[c] = s
    contrasts = {}
    for a, b in (("RAISE", "MAINTAIN"), ("RAISE", "CUT")):
        if len(by[a]) and len(by[b]):
            contrasts[f"{a}_minus_{b}_excess"] = core.boot_diff(by[a].excess.to_numpy(), by[a].week.to_numpy(),
                                                                by[b].excess.to_numpy(), by[b].week.to_numpy(),
                                                                core.SEED + 99)
    accounts, curves = {}, {}
    for name, (weight, slots, stop) in ACCOUNTS.items():
        for suffix, key in (("", "ticker"), ("_shadow", "shadow_ticker")):
            accounts[name + suffix], curves[name + suffix] = simulate(by["RAISE"], m, ti, dates, weight, slots, stop,
                                                                      key)
    pd.DataFrame(curves).to_csv(OUT / "accounts.csv.gz", index_label="date")
    tr.drop(columns=["e", "x"]).to_csv(OUT / "trades.csv.gz", index=False)

    r_ = res["RAISE"]
    gates = {}
    if r_.get("n", 0):
        a, sh = accounts["A"], accounts["A_shadow"]
        gates = {
            "G1_raise_excess_ci_above_zero": r_["excess"]["ci95"][0] > 0,
            "G2_raise_mean_and_clipped_net_positive": r_["mean_net"] > 0 and r_["clipped_mean_net"] > 0,
            "G3_raise_beats_maintain": contrasts.get("RAISE_minus_MAINTAIN_excess", {}).get("diff", -1) > 0,
            "G4_stress_net_positive": r_["stress_mean_net"] > 0,
            "G5_excess_positive_every_year": all(v["mean_excess"] > 0 for v in r_["by_year"].values()),
            "G6_account_A_beats_start_and_shadow": a.get("total_return", -1) > 0 and
            a.get("end_equity", 0) > sh.get("end_equity", float("inf")),
        }
    verdict = "PASS" if gates and all(gates.values()) else "FAIL"
    etoro_path = ROOT / "data" / "raw" / "etoro" / "20261016T190421Z" / "instruments.json"
    etoro = {str(x["SymbolFull"]).upper().replace(".", "-")
             for x in json.loads(etoro_path.read_bytes())["InstrumentDisplayDatas"]
             if x["InstrumentTypeID"] == 5 and x["ExchangeID"] in (4, 5) and not x.get("IsInternalInstrument")}
    raises = by["RAISE"]
    on_etoro = raises[raises.ticker.str.upper().str.replace(".", "-", regex=False).isin(etoro)]
    result = {
        "experiment": "E10 guidance revision (US), discovery 2020-07..2022-11, stages 2 and 3, run once",
        "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "code": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(),
        "protocol_sha256": core.sha(E10 / "protocol.json"), "events_in": int(len(ev)), "skipped": skipped,
        "trades": int(len(tr)), "classes": res, "contrasts": contrasts, "accounts": accounts, "gates": gates,
        "verdict": verdict, "raise_on_etoro": core.summary(on_etoro, core.SEED + 77),
        "limits": ["US universe is today's listings only (survivor bias, likely flattering)",
                   "costs are assumed price tiers plus a USD 2 commission in the accounts, not measured spreads; "
                   "daily bars cannot prove an opening fill",
                   "guidance extraction is a frozen text rule with an audited error rate, not a reading of every filing",
                   "discovery only: 2023 is already used and 2024+ is sealed; a PASS licenses forward paper testing "
                   "only"],
    }
    (OUT / "RESULT.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    print(json.dumps({k: result[k] for k in ("trades", "skipped", "gates", "verdict", "accounts")}, indent=2,
                     default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())

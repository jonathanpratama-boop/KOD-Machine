"""PATH_HISTORY_v1 build: events, twins, outcomes and the price feature blocks (P0, P1), per protocol.json.

One row per event in results/events.csv.gz. Nothing is evaluated here, and no outcome rate is printed. evaluate.py
fits and scores.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import global_panel, learner2  # noqa: E402
from idxsig import panel as idx_panel  # noqa: E402
from idxsig import speculation as spec  # noqa: E402
from idxsig.e1 import _dense  # noqa: E402
from idxsig.execution import Market  # noqa: E402
from idxsig.provenance import sha256_file  # noqa: E402
from idxsig.rules import moonshot_e1, moonshot_g  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
PROTO = json.loads((HERE / "protocol.json").read_text())
P0 = ("s_ret1", "s_ret5", "s_ret20", "s_dd60", "log_volr", "s_cpos", "log_adv")
P1_EXTRA = ("gap", "vol20", "log_price", "spikes60", "streak", "dist_high252", "log_age", "breadth", "mkt_ret",
            "ara_streak")
SPLIT_DATE = "2022-12-31"
WINDOW = 20


def check_pins():
    for path, want in PROTO["data"]["code_pins"].items():
        got = sha256_file(ROOT / path)
        if got != want:
            raise RuntimeError(f"{path} changed since the freeze: {got} != {want}")


def segments(market: str):
    """(segment label, Market) for each allowed segment; rows outside rows_read are dropped before anything is built."""
    d = PROTO["data"][market]
    if market == "IDX":
        df, meta, _ = idx_panel.load(ROOT / d["manifest"])
    else:
        df, meta = global_panel.load(ROOT / d["manifest"])
    if meta["sha256"] != d["panel_sha256"]:
        raise RuntimeError(f"{market} panel hash differs from the protocol")
    spans = d["rows_read"] if market == "IDX" else [d["rows_read"]]
    for lo, hi in spans:
        seg = df[(df["date"] >= lo) & (df["date"] <= hi)].copy()
        if market == "IDX":
            traded = seg[seg["volume"] > 0].groupby("date")["ticker"].nunique()
            seg = seg[seg["date"].isin(traded[traded >= 50].index)]
            m = Market.from_panel(seg)
        else:
            m = Market.from_panel(seg, price_limits=False)
            if "unit_factor" in seg:
                m = m.with_units(_dense(m, seg, "unit_factor", 1.0))
        yield f"{market}:{lo}..{hi}", m
    del df


def detector(market: str, m: Market) -> tuple[str, dict, np.ndarray]:
    if market == "IDX":
        f = moonshot_e1.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.lock_up)
        name, flag = "F1_ARA", moonshot_e1.family_flags(f)["F1_ARA"]
        with np.errstate(divide="ignore", invalid="ignore"):
            f["gap"] = np.where(m.tradeable & (m.prev > 0) & (m.open > 0), m.open / m.prev - 1, np.nan)
    else:
        f = moonshot_g.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.open)
        name, flag = "G2_RET30", moonshot_g.family_flags(f)["G2_RET30"]
    return name, f, flag


def _streak(mask: np.ndarray, cap: int) -> np.ndarray:
    """Consecutive True values ending at each column, capped."""
    out = np.zeros(mask.shape, dtype=float)
    run = np.zeros(mask.shape[0])
    for j in range(mask.shape[1]):
        run = np.where(mask[:, j], np.minimum(run + 1, cap), 0)
        out[:, j] = run
    return out


def build_market(market: str, log=print) -> list[dict]:
    rows = []
    proto_spec, _ = spec.protocol()
    plan = spec.windows()["BASE5"]
    cone = proto_spec["cone"]
    for label, m in segments(market):
        name, f, flag = detector(market, m)
        n_names, n_sess = m.shape
        history = np.cumsum(m.present, axis=1)
        eligible = m.tradeable & (history > 20)
        sel = flag & eligible
        if market == "IDX":
            sel &= m.close >= 50
        event = sel.copy()
        event[:, n_sess - (WINDOW + 1):] = False
        value = np.where(m.tradeable, m.value, np.nan)
        adv = pd.DataFrame(value.T).rolling(20, min_periods=1).median().to_numpy().T
        with np.errstate(divide="ignore", invalid="ignore"):
            logret = np.where(m.present & (m.prev > 0) & (m.close > 0), np.log(m.close / m.prev), 0.0)
        level = np.where(m.present, np.exp(np.cumsum(logret, axis=1)), np.nan)
        vol20 = pd.DataFrame(np.where(m.tradeable & (m.prev > 0), logret, np.nan).T).rolling(20, min_periods=15).std().to_numpy().T
        high252 = pd.DataFrame(level.T).rolling(252, min_periods=20).max().to_numpy().T
        spikes = np.cumsum(sel, axis=1)
        up = np.nan_to_num(f["ret1"]) > 0
        streak = _streak(up & m.tradeable, 10)
        ara_streak = _streak(m.lock_up & m.tradeable, 10) if market == "IDX" else np.zeros(m.shape)
        mkt_ret = pd.DataFrame(np.where(m.tradeable, f["ret1"], np.nan)).median(axis=0).to_numpy()
        breadth = sel.sum(axis=0)
        uf = m.unit_factor if m.unit_factor is not None else None
        dates = m.dates.astype(str)
        tick = m.tickers.astype(str)
        index_of = {t: i for i, t in enumerate(tick)}
        for d in np.flatnonzero(event.any(axis=0)):
            cands = np.flatnonzero(sel[:, d])
            feats = pd.DataFrame({
                "ticker": tick, "fresh": m.present[:, d], "eligible": eligible[:, d], name: sel[:, d],
                "close": m.close[:, d], "previous": m.prev[:, d], "adv20_value": adv[:, d], "ret20": f["ret20"][:, d],
                "dd60": f["dd60"][:, d], "volr": f["volr"][:, d]})
            cand_t = [tick[i] for i in cands]
            for n in np.flatnonzero(event[:, d]):
                t = tick[n]
                seed = spec.twin_seed(f"PATH-HISTORY-v1:{market}:{dates[d]}:{t}")
                try:
                    twins, level_name = spec.draw_twins(feats, t, cand_t, name, market, seed)
                except ValueError:
                    continue
                tw_idx = [index_of[tw["ticker"]] for tw in twins]

                def quote(i):
                    if market != "CRYPTO":
                        return None
                    o = float(m.open[i, d + 1]) if d + 1 < n_sess else float("nan")
                    return o if np.isfinite(o) and o > 0 else None

                def ufun(i):
                    return (lambda k: float(uf[i, k])) if uf is not None else None

                cres = spec.simulate(m, n, d, plan, market, quote(n), ufun(n))
                tres = [spec.simulate(m, i, d, plan, market, quote(i), ufun(i)) for i in tw_idx]
                base = spec.cone_outcomes(cone, "BASE5", m, d, (n, cres), list(zip(tw_idx, tres)))
                path = spec.cone_outcomes(cone, "PATH20", m, d, (n, None), [(i, None) for i in tw_idx])
                out = {c["id"]: c for c in base + path}

                def r1(i):
                    if d + 1 >= n_sess or not m.present[i, d + 1] or not np.isfinite(level[i, d]):
                        return None
                    return float(level[i, d + 1] / level[i, d] - 1)

                sig = {"ret1": f["ret1"][n, d], "ret5": f["ret5"][n, d], "ret20": f["ret20"][n, d],
                       "dd60": f["dd60"][n, d], "volr": f["volr"][n, d], "cpos": f["cpos"][n, d],
                       "adv20_value": adv[n, d]}
                x = learner2.features({"signal": {k: (None if v is None or not np.isfinite(v) else float(v))
                                                  for k, v in sig.items()}, "market": market, "direction": 1})
                xf = dict(zip(learner2.FEATURES, x))
                price = float(m.close[n, d]) * (float(uf[n, d]) if uf is not None else 1.0)
                row = {"market": market, "segment": label, "ticker": t, "session": dates[d], "prev_session": dates[d - 1],
                       "split": "train" if dates[d] <= SPLIT_DATE else "test", "twin_level": level_name,
                       "twins": "|".join(tw["ticker"] for tw in twins), "n_twins": len(twins),
                       **{k: float(xf[k]) for k in P0},
                       "gap": _f(f["gap"][n, d]), "vol20": _f(vol20[n, d]),
                       "log_price": math.log10(max(price * learner2.FX.get(market, 1.0), 1e-6)),
                       "spikes60": float(spikes[n, d - 1] - spikes[n, max(0, d - 61)]) if d >= 1 else 0.0,
                       "streak": float(streak[n, d]), "dist_high252": _f(level[n, d] / high252[n, d] - 1),
                       "log_age": math.log(float(history[n, d])), "breadth": math.log1p(float(breadth[d])),
                       "mkt_ret": _f(mkt_ret[d]), "ara_streak": float(ara_streak[n, d]),
                       "vol_traded": _f(m.volume[n, d] / (float(uf[n, d]) if uf is not None else 1.0)),
                       "price_traded": price,
                       "revsplit12m": bool(uf is not None and np.any(uf[n, max(1, d - 251): d + 1]
                                                                    / uf[n, max(0, d - 252): d] >= 1.5)),
                       "split_dates_2y": "|".join(dates[k] for k in range(max(1, d - 503), d + 1)
                                                  if uf is not None and abs(uf[n, k] / uf[n, k - 1] - 1) > 0.01)}
                for sid in ("RUN30_5", "FADE10_5", "GAIN0_5", "BEATS_TWINS_5", "RUN30_20", "DOUBLE_20"):
                    c = out.get(sid) or {}
                    row[f"y_{sid}"] = c.get("outcome")
                    row[f"tw_{sid}"] = c.get("twins_rate")
                r = r1(n)
                tr = [v for v in (r1(i) for i in tw_idx) if v is not None]
                row["r1"] = r
                row["tw_r1_n"] = len(tr)
                row["tw_r1_median"] = float(np.median(tr)) if tr else None
                row["tw_r1_dump10"] = float(np.mean([v <= -0.10 for v in tr])) if tr else None
                row["tw_r1_run10"] = float(np.mean([v >= 0.10 for v in tr])) if tr else None
                row["entry_status"] = (cres or {}).get("status")
                rows.append(row)
        log(f"{label}: {sum(1 for r in rows if r['segment'] == label)} events built")
        del m
    return rows


def _f(v) -> float | None:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def own(happened, twins_rate):
    """learner2.own_move: False when the move did not happen; True when it did and fewer than half of the graded twins
    made it; None (ungraded) when it did and no twin was graded."""
    if happened is None:
        return None
    if not happened:
        return False
    return None if twins_rate is None or (isinstance(twins_rate, float) and math.isnan(twins_rate)) else bool(twins_rate < 0.5)


def statements(df: pd.DataFrame) -> pd.DataFrame:
    """The protocol's statements from the raw outcomes."""
    def norm(x):
        return None if x is None or (isinstance(x, float) and math.isnan(x)) else bool(x)

    def col(a, b):
        return [own(norm(x), None if t is None or (isinstance(t, float) and math.isnan(t)) else float(t))
                for x, t in zip(df[a], df[b])]

    out = pd.DataFrame(index=df.index)
    out["PUMP30_5"] = col("y_RUN30_5", "tw_RUN30_5")
    out["DUMP10_5"] = col("y_FADE10_5", "tw_FADE10_5")
    out["PUMP30_20"] = col("y_RUN30_20", "tw_RUN30_20")
    out["PUMP100_20"] = col("y_DOUBLE_20", "tw_DOUBLE_20")
    out["PUMP_AND_DUMP_5"] = [None if (a is None or b is None) else (a and b) for a, b in zip(out["PUMP30_5"], out["DUMP10_5"])]
    out["BEATS_TWINS_5"] = [None if (x is None or (isinstance(x, float) and math.isnan(x))) else bool(x) for x in df["y_BEATS_TWINS_5"]]
    nd, nr, nl = [], [], []
    for r, n, med, pd10, pr10 in zip(df["r1"], df["tw_r1_n"], df["tw_r1_median"], df["tw_r1_dump10"], df["tw_r1_run10"]):
        if r is None or (isinstance(r, float) and math.isnan(r)):
            nd.append(None), nr.append(None), nl.append(None)
            continue
        twin_ok = n is not None and not (isinstance(n, float) and math.isnan(n)) and n > 0
        nd.append(own(r <= -0.10, pd10 if twin_ok else None))
        nr.append(own(r >= 0.10, pr10 if twin_ok else None))
        nl.append(bool(r < med) if (twin_ok and n >= 3) else None)
    out["NEXT_DUMP10"], out["NEXT_RUN10"], out["NEXT_LOSES"] = nd, nr, nl
    return out


def main():
    check_pins()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for market in ("US", "CRYPTO", "IDX"):
        rows += build_market(market, log=lambda s: print(s, flush=True))
    df = pd.DataFrame(rows)
    st = statements(df)
    for c in st.columns:
        df[f"S_{c}"] = [None if v is None else int(v) for v in st[c]]
    df.to_csv(OUT / "events.csv.gz", index=False)
    print(f"events: {len(df)}; by market {df.groupby('market').size().to_dict()}; by split {df.groupby('split').size().to_dict()}")


if __name__ == "__main__":
    main()

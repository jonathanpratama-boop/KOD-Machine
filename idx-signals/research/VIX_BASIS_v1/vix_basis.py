"""VIX_BASIS_v1: sell the volatility insurance premium in VIX futures only when the futures curve pays for it.

Hypothesis (PROTOCOL.md): investors buy VIX futures and VIX-linked products as crash insurance, so VIX futures in contango
trade above the VIX they converge to. Simon and Campasano (working paper 2012, J. Derivatives 2014) found, on 2006-2011,
that the futures basis predicts futures returns, not spot VIX changes. The rule here is their published entry, short leg
only, unhedged: on a day whose daily roll (front futures minus spot VIX, per trading day to settlement; front = the
nearest monthly contract with at least 10 trading days left) exceeds 0.10 points, sell that contract at the next
session's settlement and hold it 5 trading days. Position notional 20% of equity (a 100% overnight futures jump costs
about 20% of equity; that is not a maximum loss). Costs per side: one 0.05 tick plus USD 1.50 per Mini VIX (VXM) contract.

Discovery 2006-01-03 .. 2015-12-31, validation 2016-01-04 .. 2023-12-29 (run only if discovery passes). The US/crypto
holdout 2024-01-01 .. 2026-12-31 is sealed: every row dated in it is dropped at parse time.

    python3 research/VIX_BASIS_v1/vix_basis.py --feasibility   # data checks and counts only
    python3 research/VIX_BASIS_v1/vix_basis.py --freeze
    python3 research/VIX_BASIS_v1/vix_basis.py --run
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from idxsig.provenance import sha256_file, utc_stamp

MANIFEST = ROOT / "data/manifests/cboe_vx-20261101T081634Z.jsonl"
RAW = ROOT / "data/raw"
PROTO, RUN, FEAS = HERE / "protocol.json", HERE / "run", HERE / "FEASIBILITY.json"
SEALED_FROM = "2024-01-01"
DISCOVERY = ("2006-01-03", "2015-12-31")
VALIDATION = ("2016-01-04", "2023-12-29")
RESCALE = "2007-03-26"  # Cboe rescaled VX from 10x VIX to 1x VIX on this date
# Final settlement of the two contracts whose rows after 2023-12-29 are sealed (the rule's Wednesday; no holiday shift);
# rule_expiry() must agree
SEALED_EXPIRIES = {"2024-01": "2024-01-17", "2024-02": "2024-02-14"}
# Unscheduled exchange closures: a trader deciding before them expected these sessions, so they count in days-to-
# settlement for decisions made before them (Ford's day of mourning; Hurricane Sandy)
# closure date -> the session on which it became known (announced the evening before / over the weekend): a closure
# counts in days-to-settlement only for decisions made before that
UNSCHEDULED_CLOSURES = {
    pd.Timestamp("2007-01-02"): pd.Timestamp("2006-12-28"),  # announced Thu 28 Dec 2006
    pd.Timestamp("2012-10-29"): pd.Timestamp("2012-10-29"),  # announced Sun 28 Oct 2012
    pd.Timestamp("2012-10-30"): pd.Timestamp("2012-10-29"),
}
# Dates with rows in Cboe's files that were not CFE business days: Good Friday 2015 (Cboe notice of 26 Mar 2015: trades
# from 3:30 p.m. CT Thu 2 Apr to 3:15 p.m. CT Mon 6 Apr were for business day Mon 6 Apr; no open interest changed)
NON_BUSINESS_DAYS = pd.to_datetime(["2015-04-03"])
SESSIONS_2024 = pd.bdate_range("2024-01-02", "2024-02-14").difference(
    pd.to_datetime(["2024-01-15"])
)
START_EQUITY = 10_000.0  # USD (about IDR 160m)
BOOT = {"draws": 10_000, "seed": 20261103}


@dataclass(frozen=True)
class Rule:
    entry_roll: float = 0.10  # daily roll threshold (VIX points per trading day)
    min_days: int = 10  # front = nearest contract with at least this many trading days to settlement
    hold: int = 5  # trading days per trade
    lag: int = (
        1  # signal on day d's close and settlement, trade at day d+lag's settlement
    )
    weight: float = 0.20  # notional / equity at entry
    cost_points: float = (
        0.065  # per side: one 0.05 tick + USD 1.50 / (USD 100 per point, Mini VIX VXM)
    )
    side: str = "short_only"  # "short_only", "both" (also long when roll < -entry_roll), "always_short"
    # None: fractional notional (weight x equity). A number: whole contracts of this many USD per point (VXM: 100),
    # round(weight x equity / (F x multiplier)) of them; no position when that rounds to 0 (descriptive arm only)
    multiplier: float | None = None


PRIMARY = Rule()
VARIANTS = {
    "primary": PRIMARY,
    "S1_double_costs": replace(PRIMARY, cost_points=2 * PRIMARY.cost_points),
    "S2_lag_2": replace(PRIMARY, lag=2),
    "N1_threshold_0.05": replace(PRIMARY, entry_roll=0.05),
    "N2_threshold_0.15": replace(PRIMARY, entry_roll=0.15),
    "D1_both_sides": replace(PRIMARY, side="both"),
    "B1_always_short": replace(PRIMARY, side="always_short"),
    "R1_whole_vxm_contracts": replace(PRIMARY, multiplier=100.0),
}


# ------------------------------------------------------------------------------------------------------------ data
def manifest_files() -> dict:
    lines = [json.loads(x) for x in MANIFEST.read_text().splitlines()]
    return {r.get("contract", r["kind"]): r for r in lines[1:]}


def verify_inputs() -> None:
    for r in manifest_files().values():
        if sha256_file(RAW / r["file"]) != r["sha256"]:
            sys.exit(f"error: {r['file']} differs from its manifest")


def good_friday(year: int) -> dt.date:
    """Gregorian Easter (anonymous algorithm) minus two days."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    lv = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lv) // 451
    month = (h + lv - 7 * m + 114) // 31
    day = (h + lv - 7 * m + 114) % 31 + 1
    return dt.date(year, month, day) - dt.timedelta(days=2)


def rule_expiry(contract: str) -> pd.Timestamp:
    """Cboe's VX final settlement date: 30 days before the third Friday of the following month; if that Friday is an
    exchange holiday (Good Friday), 30 days before the business day before it. Cboe's further clause (a holiday on the
    Wednesday itself moves settlement to the business day before) is not implemented: no contract 2006-01..2024-02
    hits it, and load() asserts every full contract's last row equals this date."""
    y, m = map(int, contract.split("-"))
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    d = dt.date(ny, nm, 15)
    fri = d + dt.timedelta(days=(4 - d.weekday()) % 7)
    if fri == good_friday(ny):
        fri -= dt.timedelta(days=1)
    return pd.Timestamp(fri - dt.timedelta(days=30))


def _dates(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    iso = s.str.match(r"^\d{4}-\d{2}-\d{2}")
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    out[iso] = pd.to_datetime(s[iso].str[:10], format="%Y-%m-%d")
    out[~iso] = pd.to_datetime(s[~iso], format="%m/%d/%Y")
    return out


def load() -> dict:
    """Settlements (date x contract), expiries, VIX and SPX closes, the session calendar, and data-quality counts.
    Every row dated SEALED_FROM or later is dropped as soon as its file is parsed."""
    files = manifest_files()
    cut = pd.Timestamp(SEALED_FROM)
    qa = {
        "sealed_rows_dropped": 0,
        "zero_settle_used_close": 0,
        "zero_rows_dropped": 0,
        "rescaled_10x": 0,
        "non_business_day_rows_dropped": 0,
        "idle_rows_dropped": 0,
        "implausible_rows_dropped": 0,
    }
    idx = {}
    for name in ("VIX", "SPX"):
        d = pd.read_csv(RAW / files[name]["file"])
        d["DATE"] = _dates(d["DATE"])
        qa["sealed_rows_dropped"] += int((d.DATE >= cut).sum())
        d = d[d.DATE < cut]
        idx[name] = d.set_index("DATE")["CLOSE" if name == "VIX" else "SPX"].astype(
            float
        )
    vix = idx["VIX"]
    settle, expiry = {}, {}
    for key, r in files.items():
        if r["kind"] != "VX":
            continue
        d = pd.read_csv(RAW / r["file"])
        d["date"] = _dates(d["Trade Date"])
        qa["sealed_rows_dropped"] += int((d.date >= cut).sum())
        d = d[d.date < cut]
        nb = d.date.isin(NON_BUSINESS_DAYS)
        qa["non_business_day_rows_dropped"] += int(nb.sum())
        d = d[~nb]
        s = pd.to_numeric(d["Settle"], errors="coerce")
        c = pd.to_numeric(d["Close"], errors="coerce")
        use_close = (s <= 0) & (c > 0)
        qa["zero_settle_used_close"] += int(use_close.sum())
        s = s.where(s > 0, c.where(c > 0))
        qa["zero_rows_dropped"] += int(s.isna().sum())
        d = d.assign(settle=s).dropna(subset=["settle"])
        vol = pd.to_numeric(d["Total Volume"], errors="coerce").fillna(0)
        oi = pd.to_numeric(d["Open Interest"], errors="coerce").fillna(0)
        idle = (
            (vol <= 0) & (oi <= 0)
        )  # no trade and no open position: rows before a contract's first trade or open interest (and 11 interior)
        qa["idle_rows_dropped"] += int(idle.sum())
        d = d[~idle]
        early = (d.date < pd.Timestamp(RESCALE)).to_numpy()
        if early.any():  # every quote before the rescale was at 10x VIX
            d.loc[early, "settle"] = d.loc[early, "settle"] / 10.0
            qa["rescaled_10x"] += int(early.sum())
        ratio = d.settle.to_numpy() / vix.reindex(d.date).to_numpy()
        bad = np.isfinite(ratio) & (
            (ratio < 0.2) | (ratio > 5.0)
        )  # a 10x scaling error lands far outside
        if (bad & early).any():
            raise RuntimeError(
                f"{key}: a pre-rescale settlement is implausible against VIX (rescale check)"
            )
        qa["implausible_rows_dropped"] += int(
            bad.sum()
        )  # isolated bad prints (one: a 1.0 settlement on 2008-04-21, 209 sessions before expiry)
        d = d[~bad]
        settle[key] = d.set_index("date")["settle"]
        expiry[key] = rule_expiry(key)
        if key in SEALED_EXPIRIES:
            if expiry[key] != pd.Timestamp(SEALED_EXPIRIES[key]):
                raise RuntimeError(
                    f"{key}: rule expiry differs from the declared sealed-contract expiry"
                )
        elif d.date.max() != expiry[key]:
            raise RuntimeError(
                f"{key}: last row {d.date.max().date()} is not the rule's settlement date"
            )
    panel = pd.DataFrame(settle).sort_index()
    # trading sessions = days with a VX settlement (the VIX file also lists some exchange holidays, 2022-2023)
    if panel.index.isin(list(UNSCHEDULED_CLOSURES)).any():
        raise RuntimeError("an unscheduled closure has VX rows")
    sessions = panel.index.union(
        SESSIONS_2024
    )  # closures are added per decision in front_and_roll
    qa["vix_days_not_vx_sessions"] = len(vix.index.difference(panel.index))
    return {
        "settle": panel,
        "expiry": pd.Series(expiry),
        "vix": vix,
        "spx": idx["SPX"],
        "sessions": sessions,
        "qa": qa,
    }


def front_and_roll(data: dict, min_days: int) -> pd.DataFrame:
    """Per session with a VIX close: the front contract (nearest with >= min_days trading days to settlement and a
    settlement that day), its settlement, trading days left and the daily roll (F - VIX) / days."""
    sess = data["sessions"]
    exp = data["expiry"].sort_values()
    exp_pos = np.searchsorted(
        sess.values, exp.values, side="right"
    )  # sessions up to and including each settlement
    closures = data.get("closures", UNSCHEDULED_CLOSURES)
    settle = data["settle"]
    rows = []
    for day, v in data["vix"].items():
        if day not in settle.index:
            continue
        p = int(sess.get_loc(day)) + 1  # sessions up to and including the decision day
        # closures not yet known at this decision were expected sessions
        expected = [c for c, known in closures.items() if day < known and c > day]
        row = settle.loc[day]
        future = exp.values > np.datetime64(day)
        for c, ep, e in zip(exp.index[future], exp_pos[future], exp.values[future]):
            left = int(ep) - p + sum(1 for x in expected if x <= e)
            if left >= min_days and np.isfinite(row.get(c, np.nan)):
                f = float(row[c])
                rows.append(
                    {
                        "date": day,
                        "contract": c,
                        "F": f,
                        "vix": float(v),
                        "days": left,
                        "roll": (f - float(v)) / left,
                    }
                )
                break
    return pd.DataFrame(rows).set_index("date")


# ------------------------------------------------------------------------------------------------------------ simulation
def signal(fr: pd.DataFrame, rule: Rule) -> pd.Series:
    """+1 long, -1 short, 0 flat, decided on each session's close."""
    if rule.side == "always_short":
        return pd.Series(-1, index=fr.index)
    s = pd.Series(0, index=fr.index)
    s[fr.roll > rule.entry_roll] = -1
    if rule.side == "both":
        s[fr.roll < -rule.entry_roll] = 1
    return s


def contracts(rule: Rule, equity: float, size_price: float) -> int | None:
    """Whole contracts for an arm with a multiplier (None for fractional arms), sized from a price known before the
    fill: round(weight x equity / (size_price x multiplier))."""
    if rule.multiplier is None:
        return None
    return round(rule.weight * equity / (size_price * rule.multiplier))


def _notional(rule: Rule, equity: float, n: int | None, fill: float) -> float:
    return rule.weight * equity if n is None else n * fill * rule.multiplier


def _prev_settle(settle: pd.DataFrame, contract: str, day, fallback: float) -> float:
    """The held contract's last settlement strictly before `day` (known before today's fill)."""
    px = settle[contract].loc[: day - pd.Timedelta(days=1)].dropna()
    return float(px.iloc[-1]) if len(px) else fallback


def simulate(
    data: dict, fr: pd.DataFrame, rule: Rule, start: str, end: str
) -> tuple[pd.DataFrame, pd.Series]:
    """Positions (as 5-session segments) and the daily marked-to-market equity on [start, end].

    A position decided on day d (its close) enters at the settlement `lag` sessions later in d's front contract and
    each segment exits `hold` sessions after it entered, at settlement. At a segment's exit, if the decision `lag`
    sessions earlier is the same side in the same contract, the position continues with no exit or entry cost and is
    resized to equity (fractional arms: at no cost; whole-contract arms: a change in the number of contracts pays the
    per-contract cost on the difference, and zero contracts closes the position). Otherwise it is closed with a cost
    and a new decision may open another (cost). Whole-contract counts are sized from prices known before the fill: the
    decision-day settlement for a new position, the previous session's settlement for a continuation. No position is
    opened on the window's last session; a position open at the window's end is closed at its last settlement with a
    cost. Sessions without a settlement for the held contract carry the last settlement; a position is never entered
    at a missing price, and a missing exit price delays the exit to the next settlement."""
    settle = data["settle"]
    days = fr.index[(fr.index >= pd.Timestamp(start)) & (fr.index <= pd.Timestamp(end))]
    sig = signal(fr, rule)
    cash_eq = START_EQUITY
    pos = None
    trades, curve, n_pos = [], [], 0
    last_i = len(days) - 1

    def close_segment(day, px, exit_cost, cont, extra_usd=0.0, window_end=False):
        gross = pos["side"] * (px - pos["entry"]) / pos["entry"]
        net = (
            gross
            - (pos["entry_cost"] + exit_cost) / pos["entry"]
            - extra_usd / pos["notional"]
        )
        pnl = pos["notional"] * net
        rec = {
            "entry_date": pos["entry_date"],
            "exit_date": day,
            "contract": pos["contract"],
            "side": pos["side"],
            "entry": pos["entry"],
            "exit": px,
            "notional": pos["notional"],
            "contracts": pos["n"],
            "gross_return": gross,
            "net_return": net,
            "pnl": pnl,
            "continued": cont,
            "entry_paid": pos["entry_cost"] > 0,
            "exit_paid": exit_cost > 0,
            "resize_cost_usd": extra_usd,
            "position": pos["position"],
        }
        if window_end:
            rec["closed_at_window_end"] = True
        trades.append(rec)
        return pnl

    for i, day in enumerate(days):
        d_i = i - rule.lag
        decision = days[d_i] if d_i >= 0 else None
        want = int(sig[decision]) if decision is not None else 0
        want_c = fr.contract[decision] if decision is not None else None
        if pos is not None and i == pos["exit_i"]:
            px = settle.at[day, pos["contract"]] if day in settle.index else np.nan
            if not np.isfinite(px):
                pos["exit_i"] += 1  # no settlement today: exit at the next one
            else:
                cont = want == pos["side"] and want_c == pos["contract"]
                n_new, extra = None, 0.0
                if cont:
                    gross = pos["side"] * (px - pos["entry"]) / pos["entry"]
                    eq_after = cash_eq + pos["notional"] * (
                        gross - pos["entry_cost"] / pos["entry"]
                    )
                    n_new = contracts(
                        rule,
                        eq_after,
                        _prev_settle(settle, pos["contract"], day, pos["entry"]),
                    )
                    if n_new == 0:
                        cont = False  # whole contracts: resizing to zero closes the position
                    elif n_new is not None:
                        extra = (
                            abs(n_new - pos["n"]) * rule.cost_points * rule.multiplier
                        )
                pnl = close_segment(
                    day, px, 0.0 if cont else rule.cost_points, cont, extra
                )
                cash_eq += pnl
                prev_id = pos["position"]
                pos = None
                if cont:
                    pos = {
                        "contract": want_c,
                        "side": want,
                        "entry": px,
                        "entry_cost": 0.0,
                        "n": n_new,
                        "notional": _notional(rule, cash_eq, n_new, px),
                        "exit_i": i + rule.hold,
                        "entry_date": day,
                        "position": prev_id,
                    }
                    want = 0  # already positioned
        if pos is None and want != 0 and decision is not None and i < last_i:
            px = settle.at[day, want_c] if day in settle.index else np.nan
            n = contracts(rule, cash_eq, float(fr.F[decision]))
            if np.isfinite(px) and n != 0:
                n_pos += 1
                pos = {
                    "contract": want_c,
                    "side": want,
                    "entry": px,
                    "entry_cost": rule.cost_points,
                    "n": n,
                    "notional": _notional(rule, cash_eq, n, px),
                    "exit_i": i + rule.hold,
                    "entry_date": day,
                    "position": n_pos,
                }
        mtm = cash_eq
        if pos is not None:
            px = settle[pos["contract"]].loc[:day].dropna()
            last = float(px.iloc[-1]) if len(px) else pos["entry"]
            mtm += (
                pos["notional"]
                * (pos["side"] * (last - pos["entry"]) - pos["entry_cost"])
                / pos["entry"]
            )
        curve.append((day, mtm, pos is not None))
    if (
        pos is not None
    ):  # the window ends inside a position: closed at the last settlement, with cost
        day = days[-1]
        px = float(settle[pos["contract"]].loc[:day].dropna().iloc[-1])
        cash_eq += close_segment(day, px, rule.cost_points, False, window_end=True)
        curve[-1] = (day, cash_eq, False)
    eqs = pd.DataFrame(curve, columns=["date", "equity", "in_position"]).set_index(
        "date"
    )
    return pd.DataFrame(trades), eqs


# ------------------------------------------------------------------------------------------------------------ statistics
def month_bootstrap(x: np.ndarray, months: np.ndarray) -> dict:
    x, g = np.asarray(x, float), np.asarray(months)
    uniq = np.unique(g)
    if len(uniq) < 2:
        return {"mean": float(x.mean()) if len(x) else None, "lower_one_sided_95": None}
    rng = np.random.default_rng(BOOT["seed"])
    members = [x[g == u] for u in uniq]
    d = np.array(
        [
            np.concatenate(
                [members[k] for k in rng.integers(0, len(uniq), len(uniq))]
            ).mean()
            for _ in range(BOOT["draws"])
        ]
    )
    return {
        "mean": float(x.mean()),
        "lower_one_sided_95": float(np.quantile(d, 0.05)),
        "lower95": float(np.quantile(d, 0.025)),
        "upper95": float(np.quantile(d, 0.975)),
        "clusters": len(uniq),
        **BOOT,
    }


def summarize(tr: pd.DataFrame, eq: pd.Series, rule: Rule) -> dict:
    e = eq["equity"]
    years = len(e) / 252.0
    dd = float((e / e.cummax() - 1).min()) if len(e) else 0.0
    out = {
        "trades": len(tr),
        "start": START_EQUITY,
        "end_equity": float(e.iloc[-1]) if len(e) else START_EQUITY,
    }
    out["net_return"] = out["end_equity"] / START_EQUITY - 1
    out["cagr"] = (
        (out["end_equity"] / START_EQUITY) ** (1 / years) - 1
        if years and out["end_equity"] > 0
        else None
    )
    out["max_drawdown_daily"] = dd
    out["worst_day"] = float(e.pct_change().min()) if len(e) > 1 else None
    out["exposure_days"] = float(eq["in_position"].mean()) if len(eq) else 0.0
    by_year = e.groupby(e.index.year).agg(["first", "last"])
    prev = START_EQUITY
    yr = {}
    for y, r in by_year.iterrows():
        yr[int(y)] = float(r["last"] / prev - 1)
        prev = r["last"]
    out["by_year"] = yr
    out["years_positive"] = int(sum(v > 0 for v in yr.values()))
    out["segments"] = len(tr)
    out["trades"] = 0
    if len(tr):
        # a "trade" is a position: a fresh entry and its continuations, closed with a cost. Its return is its P&L over the
        # notional it opened with (the P&L the account books; continuations are resized to equity, not reinvested)
        pos = tr.groupby("position", sort=True).agg(
            entry_date=("entry_date", "first"),
            exit_date=("exit_date", "last"),
            side=("side", "first"),
            pnl=("pnl", "sum"),
            first_notional=("notional", "first"),
            segments=("net_return", "size"),
        )
        pos["net_return"] = pos.pnl / pos.first_notional
        x = pos.net_return
        wins, losses = x[x > 0], x[x < 0]
        out.update(
            trades=len(pos),
            mean_net=float(x.mean()),
            median_net=float(x.median()),
            win_rate=float((x > 0).mean()),
            avg_win=float(wins.mean()) if len(wins) else None,
            avg_loss=float(losses.mean()) if len(losses) else None,
            payoff_ratio=float(wins.mean() / -losses.mean())
            if len(wins) and len(losses)
            else None,
            worst_trade=float(x.min()),
            best_trade=float(x.max()),
            mean_segments_per_trade=float(pos.segments.mean()),
            pnl_total=float(pos.pnl.sum()),
            pnl_without_top5=float(
                pos.pnl.sum()
                - pos.pnl.sort_values(ascending=False).head(5).clip(lower=0).sum()
            ),
            turnover_per_year=float(
                (
                    (tr.notional * tr.entry_paid).sum()
                    + (tr.notional * tr.exit_paid).sum()
                )
                / e.mean()
                / years
            )
            if years
            else None,
            cost_per_year_frac_equity=float(
                (
                    tr.notional
                    * (tr.entry_paid.astype(float) + tr.exit_paid.astype(float))
                    * rule.cost_points
                    / tr.entry
                ).sum()
                / e.mean()
                / years
            )
            if years
            else None,
            boot_net=month_bootstrap(
                x.to_numpy(),
                pd.to_datetime(pos.entry_date).dt.to_period("M").astype(str).to_numpy(),
            ),
            by_side={
                int(k): {"n": len(g), "mean_net": float(g.net_return.mean())}
                for k, g in pos.groupby("side")
            },
        )
    return out


def spx_buy_and_hold(data: dict, start: str, end: str) -> dict:
    s = data["spx"].loc[start:end]
    return {
        "from": str(s.index[0].date()),
        "to": str(s.index[-1].date()),
        "price_return": float(s.iloc[-1] / s.iloc[0] - 1),
        "max_drawdown": float((s / s.cummax() - 1).min()),
        "note": "SPX price index, no dividends, no costs",
    }


# ------------------------------------------------------------------------------------------------------------ gates
GATES = {
    "D0_sample": "discovery: at least 40 trades (positions: a fresh entry with its cost-free continuations) under the "
    "primary rule; else INCONCLUSIVE",
    "D1_account": "discovery account ends above its start and its P&L without the 5 largest winning positions is > 0",
    "D2_net": "discovery mean net position return (its P&L over the notional it opened with) > 0 and its bootstrap "
    "one-sided 95% lower bound > 0, clustering positions by the calendar month of their entry",
    "D3_drawdown": "discovery daily marked-to-market maximum drawdown shallower than -35%",
    "D4_stress": "discovery account ends above its start with doubled costs (S1) and with a two-session lag (S2)",
    "D5_not_brittle": "discovery account ends above its start with entry thresholds 0.05 (N1) and 0.15 (N2)",
    "D6_years": "the primary discovery account rises in at least 6 of the 10 calendar years 2006-2015",
    "validation": "computed only if D0-D6 all pass (otherwise the verdict is FAIL, or INCONCLUSIVE if D0 fails, and "
    "validation is never computed): V1 account ends above start; "
    "V2 mean net position return > 0; V3 daily maximum drawdown shallower than -35%; V4 account ends above start with "
    "doubled costs",
    "verdict": "FAIL if any D gate fails (INCONCLUSIVE if D0 fails); CONFIRMED if D0-D6 and V1-V4 pass; NOT_CONFIRMED "
    "if discovery passes and validation does not. CONFIRMED licenses only a prospective paper log and asking the owner "
    "whether to spend the sealed 2024-2026 holdout; never a live order. One run.",
}


def discovery_gates(r: dict) -> dict:
    p = r["primary"]
    g = {"D0_sample": "PASS" if p["trades"] >= 40 else "FAIL"}
    g["D1_account"] = (
        "PASS"
        if p["end_equity"] > START_EQUITY and (p.get("pnl_without_top5") or -1) > 0
        else "FAIL"
    )
    b = p.get("boot_net", {})
    g["D2_net"] = (
        "PASS"
        if (p.get("mean_net") or -1) > 0 and (b.get("lower_one_sided_95") or -1) > 0
        else "FAIL"
    )
    g["D3_drawdown"] = "PASS" if p["max_drawdown_daily"] > -0.35 else "FAIL"
    g["D4_stress"] = (
        "PASS"
        if all(
            r[k]["end_equity"] > START_EQUITY for k in ("S1_double_costs", "S2_lag_2")
        )
        else "FAIL"
    )
    g["D5_not_brittle"] = (
        "PASS"
        if all(
            r[k]["end_equity"] > START_EQUITY
            for k in ("N1_threshold_0.05", "N2_threshold_0.15")
        )
        else "FAIL"
    )
    g["D6_years"] = "PASS" if p["years_positive"] >= 6 else "FAIL"
    return g


def validation_gates(r: dict) -> dict:
    p = r["primary"]
    return {
        "V1_account": "PASS" if p["end_equity"] > START_EQUITY else "FAIL",
        "V2_net": "PASS" if (p.get("mean_net") or -1) > 0 else "FAIL",
        "V3_drawdown": "PASS" if p["max_drawdown_daily"] > -0.35 else "FAIL",
        "V4_costs": "PASS"
        if r["S1_double_costs"]["end_equity"] > START_EQUITY
        else "FAIL",
    }


def verdict(dg: dict, vg: dict | None) -> str:
    if dg["D0_sample"] == "FAIL":
        return "INCONCLUSIVE"
    if not all(v == "PASS" for v in dg.values()):
        return "FAIL"
    return (
        "CONFIRMED"
        if vg is not None and all(v == "PASS" for v in vg.values())
        else "NOT_CONFIRMED"
    )


# ------------------------------------------------------------------------------------------------------------ modes
PINS = (
    "research/VIX_BASIS_v1/vix_basis.py",
    "research/VIX_BASIS_v1/collect.py",
    "research/VIX_BASIS_v1/PROTOCOL.md",
    "research/VIX_BASIS_v1/FEASIBILITY.json",
    "tests/test_vix_basis.py",
    "data/manifests/cboe_vx-20261101T081634Z.jsonl",
)


def versions() -> dict:
    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }


def frozen_fields() -> dict:
    return {
        "discovery": list(DISCOVERY),
        "validation": list(VALIDATION),
        "sealed_from": SEALED_FROM,
        "rescale": RESCALE,
        "sealed_expiries": SEALED_EXPIRIES,
        "start_equity_usd": START_EQUITY,
        "variants": {k: asdict(v) for k, v in VARIANTS.items()},
        "bootstrap": BOOT,
        "gates": GATES,
        "versions": versions(),
    }


def git_clean(paths) -> None:
    for p in paths:
        if subprocess.run(
            ["git", "ls-files", "--error-unmatch", p],
            cwd=ROOT,
            capture_output=True,
            check=False,
        ).returncode:
            sys.exit(f"error: {p} is not committed")
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if dirty:
        sys.exit(f"error: uncommitted changes in pinned files:\n{dirty}")


def feasibility() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    verify_inputs()
    data = load()
    fr = front_and_roll(data, PRIMARY.min_days)
    out = {
        "study": "VIX_BASIS_v1",
        "computed_at": utc_stamp(),
        "what": "data checks and counts only; no strategy return, P&L or price statistic printed or saved",
        "qa": data["qa"],
        "contracts": int(data["settle"].shape[1]),
        "sessions_with_vix": len(data["vix"]),
        "first_vix": str(data["vix"].index[0].date()),
        "last_row_any_file": str(
            max(data["vix"].index.max(), data["settle"].index.max()).date()
        ),
    }
    # signal counts depend on prices: discovery only (validation counts were seen once before the freeze; PROTOCOL 3)
    for name, (a, b) in (("discovery", DISCOVERY), ("validation", VALIDATION)):
        w = fr.loc[a:b]
        sig = signal(w, PRIMARY) if name == "discovery" else None
        both = data["vix"].loc[a:b].index.intersection(data["settle"].index)
        out[name] = {
            "sessions_with_vx_and_vix": len(both),
            "sessions_without_a_front": len(both.difference(w.index)),
            "vix_rows_on_non_sessions": len(
                data["vix"].loc[a:b].index.difference(data["settle"].index)
            ),
            "vx_sessions_without_vix": len(
                data["settle"].loc[a:b].index.difference(data["vix"].index)
            ),
            **(
                {"short_signal_sessions": int((sig == -1).sum())}
                if sig is not None
                else {}
            ),
            "contracts_used": int(w.contract.nunique()),
        }
    shifted = [
        c
        for c in data["settle"].columns
        if rule_expiry(c).strftime("%A") != "Wednesday"
    ]
    out["expiry"] = {
        "rule": "Cboe: 30 days before the next month's third Friday, or before the business day preceding it when that "
        "Friday is Good Friday; load() asserts every full contract's last row equals it",
        "contracts_checked": int(
            sum(c not in SEALED_EXPIRIES for c in data["settle"].columns)
        ),
        "good_friday_shifted": shifted,
    }
    out["unscheduled_closures"] = {
        str(c.date()): str(k.date()) for c, k in UNSCHEDULED_CLOSURES.items()
    }
    out["non_business_days_dropped"] = [str(d.date()) for d in NON_BUSINESS_DAYS]
    FEAS.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


def freeze() -> int:
    if PROTO.exists():
        sys.exit("error: protocol.json exists")
    git_clean(PINS)
    verify_inputs()
    proto = {
        "study_id": "VIX_BASIS_v1",
        "frozen_at": utc_stamp(),
        **frozen_fields(),
        "code_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        "pins": {p: sha256_file(ROOT / p) for p in PINS},
    }
    PROTO.write_text(json.dumps(proto, indent=1) + "\n")
    print(
        json.dumps({k: proto[k] for k in ("study_id", "frozen_at", "gates")}, indent=1)
    )
    return 0


def period(data: dict, fr: pd.DataFrame, a: str, b: str) -> tuple[dict, dict]:
    res, files = {}, {}
    for name, rule in VARIANTS.items():
        frr = (
            fr
            if rule.min_days == PRIMARY.min_days
            else front_and_roll(data, rule.min_days)
        )
        tr, eq = simulate(data, frr, rule, a, b)
        res[name] = summarize(tr, eq, rule)
        files[f"trades_{name}.csv"], files[f"equity_{name}.csv"] = tr, eq
    res["spx_buy_and_hold"] = spx_buy_and_hold(data, a, b)
    res["cash"] = {
        "net_return": 0.0,
        "note": "USD cash at 0%; T-bill interest on collateral credited to neither side",
    }
    return res, files


def run() -> int:
    if RUN.exists():
        sys.exit("error: run/ exists; VIX_BASIS_v1 runs once")
    proto = json.loads(PROTO.read_text())
    git_clean([*PINS, "research/VIX_BASIS_v1/protocol.json"])
    if set(proto["pins"]) != set(PINS):
        sys.exit("error: protocol.json pins a different file set")
    for p, want in proto["pins"].items():
        if sha256_file(ROOT / p) != want:
            sys.exit(f"error: {p} changed since the freeze")
    for k, want in frozen_fields().items():
        if proto[k] != want:
            sys.exit(f"error: protocol.json '{k}' differs from this code")
    verify_inputs()
    data = load()
    fr = front_and_roll(data, PRIMARY.min_days)
    res = {
        "study": "VIX_BASIS_v1",
        "ran_at": utc_stamp(),
        "protocol_sha256": sha256_file(PROTO),
        "versions": versions(),
        "qa": data["qa"],
    }
    files = {}
    res["discovery"], f = period(data, fr, *DISCOVERY)
    files.update({f"discovery/{k}": v for k, v in f.items()})
    dg = discovery_gates(res["discovery"])
    vg = None
    if all(v == "PASS" for v in dg.values()):
        res["validation"], f = period(data, fr, *VALIDATION)
        files.update({f"validation/{k}": v for k, v in f.items()})
        vg = validation_gates(res["validation"])
    res["gates"] = {
        **dg,
        **(vg or {"validation": "not computed (discovery did not pass)"}),
    }
    res["verdict"] = verdict(dg, vg)
    res["commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    tmp = HERE / "run.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)  # a stale, interrupted write
    tmp.mkdir()
    for name, frame in files.items():
        p = tmp / name
        p.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(
            p, index=name.startswith(("validation/equity", "discovery/equity"))
        )
    (tmp / "RESULT.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    tmp.rename(RUN)  # run/ appears only complete
    print(res["verdict"], json.dumps(res["gates"], indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--feasibility", action="store_true")
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    return feasibility() if a.feasibility else freeze() if a.freeze else run()


if __name__ == "__main__":
    sys.exit(main())

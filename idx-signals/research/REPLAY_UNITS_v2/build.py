"""REPLAY_UNITS_v2, step 1 (corrects RECENT_REPLAY_v1/CORRECTION_1.md): the events and their features in AS-TRADED
units, no outcome read. The pull is split-adjusted to its retrieval date; the frame's price columns are multiplied
and its volume divided by U[n, d], the product of the name's split ratios effective after session d, so log_price,
log_turnover and the twins' price bands see the numbers the live scan would have seen that evening. Ratio features
(returns, volume ratio, gap, chart) are unit-free and unchanged.

RECENT_REPLAY_v1 docstring follows.

LEARNER v2.4 (idxsig.learner3) replayed over this year's US spikes from a price pull already on disk: every session
in the range is scanned as the live scan scans it (moonshot_g G2_RET30 on the causal frame, eligibility, the volr
ranking), each candidate's twins are drawn as the Speculation Register draws them (same seed rule as the live
decision ids), and v2.4's 33 features are computed by learner3's own functions (frame, bar, chart, EDGAR, FINRA)
as of the signal session. Nothing after the signal session is read here: no next close, no plan, no outcome.

    KOD_SEC_CONTACT=<contact> python3 build.py --manifest yahoo_us_replay-....jsonl --start 2026-04-01 --end 2026-10-28

Writes data/events.csv.gz (one row per candidate set) and data/BUILD.json (pins, counts, coverage). Refuses to
overwrite. The outcomes are read once, later, by run.py under protocol.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import learner2 as L2  # noqa: E402
from idxsig import learner3, paper  # noqa: E402
from idxsig import speculation as spec  # noqa: E402
from idxsig.provenance import MANIFESTS, RAW, sha256_file, utc_stamp  # noqa: E402
from idxsig.rules import moonshot_g  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
PINS = ("idxsig/learner3.py", "idxsig/learner2.py", "idxsig/speculation.py", "idxsig/paper.py",
        "idxsig/rules/moonshot_g.py", "idxsig/global_panel.py", "idxsig/execution.py")
SEL = "G2_RET30"


def market(manifest: Path):
    """The pull as a causal frame (scoring preprocessing: no row is removed with a later bar), the detector's
    features and flags, and the scan's eligibility."""
    df, data = paper.load_recent(manifest, "US", purpose="scoring")
    m = paper._market(df, "US")
    f = moonshot_g.features(m.close, m.prev, m.high, m.low, m.volume, m.present, m.tradeable, m.open)
    flags = moonshot_g.family_flags(f)
    history = np.cumsum(m.present, axis=1)
    eligible = m.tradeable & (history > paper.MIN_HISTORY)
    value = np.where(m.tradeable, m.value, np.nan)
    adv = pd.DataFrame(value.T).rolling(20, min_periods=1).median().to_numpy().T
    return m, data, f, flags, eligible, adv


DAILY_PULLS = "yahoo_us_recent-*.jsonl"  # the live scan's own daily pulls: as-traded truth for their last session


def _rebased_by_pull(t: str, eff: str, ratio: float, replay_close, pulls) -> bool | None:
    """True / False when a daily pull taken before `eff` shows whether the replay pull's history is re-based for the
    split (replay close / pull close near 1/ratio: re-based; near 1: not); None when no pull covers it."""
    for sess, closes in pulls:
        if sess < eff and t in closes and sess in replay_close and closes[t] > 0 and np.isfinite(replay_close[sess]):
            q = replay_close[sess] / closes[t]
            to_rebased, to_raw = abs(np.log(q) - np.log(1 / ratio)), abs(np.log(q))
            if min(to_rebased, to_raw) < np.log(1.15):
                return bool(to_rebased < to_raw)
    return None


def _rebased_by_jump(m, n: int, eff: str, ratio: float, dates) -> bool | None:
    """From the replay pull alone: a raw split jump at `eff` (close / previous close near 1/ratio) means the history
    was not re-based; a smooth series means it was. None when there is no bar on both sides."""
    if eff not in dates:
        return None
    k = dates.index(eff)
    if k == 0 or not (m.present[n, k] and m.present[n, k - 1]):
        return None
    j = m.close[n, k] / m.close[n, k - 1]
    if not (np.isfinite(j) and j > 0):
        return None
    return bool(abs(np.log(j)) < abs(np.log(j) - np.log(1 / ratio)))


def unit_factors(m, rec_of: dict, pulls=None, log=None) -> np.ndarray:
    """U[n, d]: as-traded = adjusted x U for prices, adjusted / U for volume. U is the product of the ratios
    (numerator / denominator, Yahoo's split events) of the splits effective after session d that the pull's history
    is actually re-based for. Yahoo lists some splits before re-basing and re-bases others before the effective
    session's bar, so each split is decided from the data: first against a daily pull taken before it (as-traded
    truth), else by whether the raw split jump is still in the series, else (no evidence) not applied and logged."""
    dates = list(m.dates.astype(str))
    darr = np.array(dates)
    U = np.ones(m.shape)
    decisions = []
    for n, t in enumerate(m.tickers.astype(str)):
        rc = None
        for eff, ratio in learner3._splits(rec_of.get(t, {})):
            if not ratio > 0 or eff <= dates[0]:
                continue
            if rc is None:
                rc = dict(zip(dates, m.close[n]))
            how, reb = "pull", (_rebased_by_pull(t, eff, ratio, rc, pulls) if pulls else None)
            if reb is None:
                how, reb = "jump", _rebased_by_jump(m, n, eff, ratio, dates)
            if reb is None:
                how, reb = "no evidence", False
            decisions.append({"ticker": t, "effective": eff, "ratio": ratio, "rebased": reb, "by": how})
            if reb:
                U[n, darr < eff] *= ratio
    unit_factors.decisions = decisions
    return U


def daily_pulls() -> list[tuple[str, dict]]:
    """(last session, {ticker: close}) of every live daily US pull on disk, oldest first."""
    import glob
    out = []
    for p in sorted(glob.glob(str(MANIFESTS / DAILY_PULLS))):
        try:
            df, _ = paper.load_recent(Path(p), "US", purpose="scoring")
        except Exception:  # noqa: BLE001  (an unreadable pull is simply not evidence)
            continue
        last = df["date"].max()
        out.append((str(last.date()), df[df["date"] == last].set_index("ticker")["close"].to_dict()))
    return out


def frame_at(m, f, flags, eligible, adv, d: int, U: np.ndarray) -> pd.DataFrame:
    """The scan's feature frame for session d (the columns the register and the learner read), prices and volume
    in as-traded units."""
    tick = m.tickers.astype(str)
    u = U[:, d]
    return pd.DataFrame({
        "ticker": tick, "session": str(m.dates[d]), "fresh": m.present[:, d], "eligible": eligible[:, d],
        "close": m.close[:, d] * u, "previous": m.prev[:, d] * u, "high": m.high[:, d] * u, "low": m.low[:, d] * u,
        "open": m.open[:, d] * u, "volume": m.volume[:, d] / u, "adv20_value": adv[:, d],
        **{k: f[k][:, d] for k in ("ret1", "rel1", "ret5", "ret20", "volr", "cpos", "dd60")},
        "gap": f["gap"][:, d], SEL: flags[SEL][:, d] & eligible[:, d],
    }).sort_values("ticker").reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, help="a yahoo_us_* manifest name under data/manifests")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default="events")
    args = ap.parse_args()
    out_csv, out_json = DATA / f"{args.out}.csv.gz", DATA / f"{args.out}_BUILD.json"
    if out_csv.exists() or out_json.exists():
        sys.exit(f"error: {out_csv.name} exists; the events are built once")
    manifest = MANIFESTS / args.manifest
    m, data, f, flags, eligible, adv = market(manifest)
    flag_all = flags[SEL] & m.tradeable  # learner3._market's flag (spikes60 counts these)
    _, records = paper.read_manifest(manifest)
    rec_of = {r.get("ticker"): r for r in records if r.get("ticker")}
    tickers, dates = list(m.tickers.astype(str)), list(m.dates.astype(str))
    U = unit_factors(m, rec_of, daily_pulls())
    ctx = learner3.Context("2026-10-30T00:00:00Z", log=lambda s: print(s, flush=True))
    ctx.day_dir = RAW / "sec" / "recent_replay_v1"
    rows, skipped, per_session = [], {"no_twins": 0, "features": 0}, {}
    for d, session in enumerate(dates):
        if session < args.start or session > args.end:
            continue
        frame = frame_at(m, f, flags, eligible, adv, d, U)
        chosen = frame[frame[SEL]].sort_values(["volr", "ticker"], ascending=[False, True])
        cand_t = chosen["ticker"].tolist()
        per_session[session] = {"flagged": len(cand_t), "built": 0}
        if not cand_t:
            continue
        for t in cand_t:
            seed = spec.twin_seed(f"SCAN-US-{session}-{SEL}-{t}")
            try:
                twins, level = spec.draw_twins(frame, t, cand_t, SEL, "US", seed)
            except ValueError:
                skipped["no_twins"] += 1
                continue
            row = frame[frame["ticker"] == t].iloc[0]
            sig = {k: spec._num(row[k]) for k in ("close", "previous", "high", "low", "volume", "adv20_value",
                                                  "ret1", "ret5", "ret20", "volr", "cpos", "dd60")}
            s = {"signal": sig, "ticker": t, "market": "US", "signal_session": session}
            n = tickers.index(t)
            try:
                parts = learner3.frame_features(s, frame)
                parts.update(learner3.bar_features(m, flag_all, n, d))
                splits = learner3._splits(rec_of.get(t, {}))
                filings, cik = ctx.filings(t, session)
                shares = ctx.shares(cik, session)
                short = ctx.short(t, dates[max(0, d - 20): d + 1])
                vol = float(m.volume[n, d] / U[n, d]) if np.isfinite(m.volume[n, d]) else None
                parts.update(learner3.edgar_features(filings, shares, short, session, dates[d - 1] if d else session,
                                                     vol, splits))
            except (ValueError, RuntimeError, KeyError) as exc:
                print(f"{t} {session}: features could not be read ({exc}); skipped", flush=True)
                skipped["features"] += 1
                continue
            rows.append({"set_id": f"REPLAY-SCAN-US-{session}-{SEL}-{t}", "ticker": t, "session": session,
                         "prev_session": dates[d - 1] if d else session, "cik": cik,
                         "twins": "|".join(tw["ticker"] for tw in twins), "n_twins": len(twins), "twin_level": level,
                         "signal_close": sig["close"], "unit_factor": float(U[n, d]), "ret1": sig["ret1"],
                         **{k: round(float(parts[k]), 6) for k in learner3.FEATURES}})
            per_session[session]["built"] += 1
        print(f"{session}: {per_session[session]['flagged']} flagged, {per_session[session]['built']} built", flush=True)
    DATA.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame(rows)
    out.to_csv(out_csv, index=False)
    meta = {"built_at": utc_stamp(), "manifest": manifest.name, "manifest_sha256": sha256_file(manifest),
            "pull": {"first_session": dates[0], "last_session": dates[-1], "sessions": len(dates), "names": len(tickers),
                     "preprocessing": "causal (purpose=scoring): no row removed with a later bar"},
            "range": [args.start, args.end], "events": len(out), "skipped": skipped,
            "per_session": per_session, "output": out_csv.name, "sha256": sha256_file(out_csv),
            "coverage": ({k: float(out[k].mean()) for k in ("has_edgar", "has_short", "has_shares", "filing_8k",
                                                            "offering90", "revsplit6m")} if len(out) else {}),
            "code_pins": {p: sha256_file(ROOT / p) for p in PINS},
            "sec_day_dir": str(ctx.day_dir.relative_to(ROOT)) if ctx.day_dir.is_relative_to(ROOT) else str(ctx.day_dir),
            "edgar_responses": len(ctx.responses),
            "reads": "features only: no bar after the signal session, no plan, no outcome",
            "units": "as_traded (frame prices x U, volume / U; U from split events effective after the session)",
            "events_with_later_split": int((out["unit_factor"] != 1.0).sum()) if len(out) else 0,
            "split_decisions": unit_factors.decisions}
    out_json.write_text(json.dumps(meta, indent=1) + "\n")
    print(json.dumps({k: v for k, v in meta.items() if k not in ("per_session", "code_pins")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

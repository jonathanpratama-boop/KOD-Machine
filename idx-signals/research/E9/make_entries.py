"""E9 step 1: ONE shared list of attempted G2_RET30 US entries and their matched-control entries.

Mirrors idxsig.backtest.run() step by step (this branch's harness), with E2's recorded US configuration
(results/runs/20261008T115656Z_MOONSHOT_E2_US_D1_v1) and only these changes: window 2020-07-01..2022-12-31
(discovery) and quarantine "none" (every name kept; research/E2/repair_v3/SELECTION_NOTE.md).
It saves entry and timing fields ONLY: no exit price, gross or net return is written or printed.
The comparison step later re-runs backtest.run() itself and checks that its trades equal this list.

Usage (from idx-signals/): python3 research/E9/make_entries.py
Writes research/E9/entries/{signals.csv, controls.csv.gz, entries_meta.json}. Runs once.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import backtest, global_panel  # noqa: E402

OUT = ROOT / "research" / "E9" / "entries"
PANEL = ROOT / "data" / "manifests" / "panel_us_repair-20261008T114805Z.json"
CFG = dict(rule_id="MOONSHOT_E2_US_D1", start="2020-07-01", end="2022-12-31", holding_days=5, entry_lag=1,
           notional=5000.0, max_participation=0.1, fee_buy=0.0, fee_sell=2.78e-05, overlap="skip", random_draws=200,
           seed=20261007, data_end_exit="last_close", ca_mode="adjusted", lookahead_cuts=None, controls_version="v2",
           market="US", units="as_traded", fill_model="B", quarantine="none")


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def build(cfg: backtest.RunConfig, panel_df: pd.DataFrame, meta: dict):
    """The harness's own steps (backtest.run) up to the execution of the matched controls."""
    rule = backtest.rule_registry.get(cfg.rule_id)
    profile = backtest.PROFILES[cfg.market]
    plan = backtest.resolve_plan(cfg, rule)
    ec = backtest.ExecConfig(lot_size=profile.lot_size, entry_price=profile.entry, cost_tiers=profile.cost_tiers,
                             holding_days=cfg.holding_days, entry_lag=cfg.entry_lag, notional=cfg.notional,
                             max_participation=cfg.max_participation, fees=backtest.Fees(cfg.fee_buy, cfg.fee_sell),
                             data_end_exit=cfg.data_end_exit, ca_mode=cfg.ca_mode, units=cfg.units,
                             fill_model=cfg.fill_model, **plan)
    full = backtest.Market.from_panel(panel_df, price_limits=profile.price_limits)
    full = full.with_units(backtest._dense(full, panel_df, "unit_factor", 1.0))
    lo, hi = full.bounds(cfg.start, cfg.end)
    m = full.slice(lo, hi)
    sig, lookahead = backtest.signals(rule, m, cfg.lookahead_cuts)
    evaluable = np.isfinite(sig)
    tick_idx, sig_idx = np.nonzero(sig == 1)
    trades = backtest.execute(m, tick_idx, sig_idx, ec)
    skipped = np.zeros(len(tick_idx), dtype=bool)
    held = {}
    for i, (n, s) in enumerate(zip(tick_idx, sig_idx)):  # identical to backtest.run()
        if s + cfg.entry_lag <= held.get(n, -1):
            skipped[i] = True
            continue
        if trades["exit_idx"][i] >= 0:
            held[n] = trades["exit_idx"][i]
        elif trades["status"][i] == backtest.STATUS.index("INCOMPLETE"):
            held[n] = np.iinfo(np.int64).max
    att = ~skipped
    a_tick, a_sig = tick_idx[att], sig_idx[att]
    feats = {k: v[:, lo:hi] for k, v in backtest.controls.features(full, cfg.controls_version, profile.band_edges,
                                                                   as_traded=cfg.units == "as_traded").items()}
    mt, level = backtest.controls.matched_draws(evaluable, feats, a_tick, a_sig, cfg.random_draws,
                                                np.random.default_rng(cfg.seed + 1), cfg.controls_version)
    r_sig = np.broadcast_to(a_sig, mt.shape)
    ctrl = backtest.execute(m, mt.ravel(), r_sig.ravel(), ec)
    return m, tick_idx, sig_idx, trades, skipped, mt, r_sig, level, ctrl, lookahead, ec


def frame(m, out, ticks, sigs, extra):
    st = np.asarray(backtest.STATUS)[out["status"]]
    d = m.dates.astype("datetime64[D]").astype(str)
    e, x = out["entry_idx"], out["exit_idx"]
    df = pd.DataFrame({"ticker": np.asarray(m.tickers)[ticks], "signal_date": d[sigs], "status": st,
                       "entry_date": np.where(e >= 0, d[np.maximum(e, 0)], ""),
                       "exit_date_original": np.where(x >= 0, d[np.maximum(x, 0)], ""),
                       "entry_price_adjusted": out["entry_price"],
                       "entry_price_as_traded": out.get("entry_price_as_traded", out["entry_price"]),
                       "shares_as_traded": out.get("shares_as_traded", out["shares"])})
    return pd.concat([pd.DataFrame(extra), df], axis=1)


def main() -> int:
    if OUT.exists():
        sys.exit(f"error: {OUT} exists; the entry list is built once")
    cfg = backtest.RunConfig(**CFG)
    panel_df, meta = global_panel.load(PANEL)
    m, tick_idx, sig_idx, trades, skipped, mt, r_sig, level, ctrl, lookahead, ec = build(cfg, panel_df, meta)
    j = np.full(len(tick_idx), -1)
    j[~skipped] = np.arange((~skipped).sum())
    sig_df = frame(m, trades, tick_idx, sig_idx, {"raw_index": np.arange(len(tick_idx)), "j": j,
                                                  "overlap_skipped": skipped})
    names = backtest.controls.level_names(cfg.controls_version)
    draws = mt.shape[0]
    ctrl_df = frame(m, ctrl, mt.ravel(), r_sig.ravel(),
                    {"draw": np.repeat(np.arange(draws), mt.shape[1]), "j": np.tile(np.arange(mt.shape[1]), draws),
                     "match_level": np.asarray(names, dtype=object)[np.broadcast_to(level, mt.shape).ravel()]})
    OUT.mkdir(parents=True)
    sig_df.to_csv(OUT / "signals.csv", index=False, float_format="%.12g")
    ctrl_df.to_csv(OUT / "controls.csv.gz", index=False, float_format="%.12g", compression={"method": "gzip", "mtime": 0})
    att = sig_df[sig_df.j >= 0]
    info = {"code_commit": git("rev-parse", "HEAD"), "config": CFG, "panel_manifest": PANEL.name,
            "panel_sha256": meta["sha256"], "window_sessions": [str(m.dates[0])[:10], str(m.dates[-1])[:10]],
            "lookahead": lookahead if isinstance(lookahead, (dict, list, str)) else str(lookahead),
            "hidden_until_freeze": ["exit_price", "gross_return", "net_return"],
            "counts": {"raw_signals": int(len(sig_df)), "overlap_skipped": int(skipped.sum()), "attempted": int(len(att)),
                       "attempted_by_status": att.status.value_counts().to_dict(),
                       "attempted_distinct_tickers": int(att.ticker.nunique()),
                       "attempted_by_year": att.signal_date.str[:4].value_counts().sort_index().to_dict(),
                       "control_entries": int(len(ctrl_df)), "control_by_status": ctrl_df.status.value_counts().to_dict(),
                       "match_level_used": pd.Series(level).map(dict(enumerate(names))).value_counts().to_dict()}}
    (OUT / "entries_meta.json").write_text(json.dumps(info, indent=1, default=str))
    print(json.dumps(info["counts"], indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
